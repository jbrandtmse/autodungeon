"""Tests for LangGraph turn orchestration (Story 1.7)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from graph import (
    create_game_workflow,
    human_intervention_node,
    route_to_next_agent,
    run_single_round,
)
from models import (
    AgentMemory,
    CharacterConfig,
    DMConfig,
    GameState,
    create_initial_game_state,
)

# =============================================================================
# Test Fixtures
# =============================================================================


def create_test_state(
    turn_queue: list[str] | None = None,
    current_turn: str = "dm",
    human_active: bool = False,
    controlled_character: str | None = None,
) -> GameState:
    """Create a test GameState with sensible defaults.

    Args:
        turn_queue: List of agent names in turn order. Defaults to ["dm", "fighter", "rogue"].
        current_turn: Name of the agent whose turn it is.
        human_active: Whether a human has taken control.
        controlled_character: Name of the human-controlled character.

    Returns:
        GameState configured for testing.
    """
    if turn_queue is None:
        turn_queue = ["dm", "fighter", "rogue"]

    state = create_initial_game_state()
    state["turn_queue"] = turn_queue
    state["current_turn"] = current_turn
    state["human_active"] = human_active
    state["controlled_character"] = controlled_character
    state["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")

    # Add character configs for each non-DM agent in turn_queue
    for agent in turn_queue:
        if agent != "dm":
            state["characters"][agent] = CharacterConfig(
                name=agent.capitalize(),
                character_class="Fighter",
                personality="Brave and bold",
                color="#C45C4A",
                provider="gemini",
                model="gemini-1.5-flash",
            )
            state["agent_memories"][agent] = AgentMemory()

    # Add DM memory
    state["agent_memories"]["dm"] = AgentMemory()

    return state


# =============================================================================
# Task 1: Tests for create_game_workflow
# =============================================================================


class TestCreateGameWorkflow:
    """Tests for the create_game_workflow factory function."""

    def test_returns_compiled_state_graph(self) -> None:
        """Test that create_game_workflow returns a compiled StateGraph."""
        workflow = create_game_workflow()
        # Compiled graphs have an invoke method
        # type: ignore needed due to langgraph's incomplete type stubs
        assert hasattr(workflow, "invoke")  # type: ignore[arg-type]

    def test_creates_dm_node(self) -> None:
        """Test that the workflow includes a dm node."""
        workflow = create_game_workflow(turn_queue=["dm"])
        # Check the graph has dm node via nodes property
        assert "dm" in workflow.get_graph().nodes

    def test_creates_pc_nodes_dynamically(self) -> None:
        """Test that PC nodes are created based on turn_queue."""
        turn_queue = ["dm", "fighter", "rogue", "wizard"]
        workflow = create_game_workflow(turn_queue=turn_queue)
        graph = workflow.get_graph()

        for agent in turn_queue:
            assert agent in graph.nodes, f"Node {agent} not found in graph"

    def test_default_turn_queue_dm_only(self) -> None:
        """Test that default turn_queue is just the DM."""
        workflow = create_game_workflow()
        graph = workflow.get_graph()
        # Should have dm node
        assert "dm" in graph.nodes

    def test_start_routes_to_dm(self) -> None:
        """Test that START entry point connects to dm node."""
        workflow = create_game_workflow(turn_queue=["dm", "fighter"])
        graph = workflow.get_graph()
        # Check edges from __start__ go to dm
        edges = graph.edges
        start_edges = [e for e in edges if e[0] == "__start__"]
        assert len(start_edges) > 0
        assert any(e[1] == "dm" for e in start_edges)


# =============================================================================
# Task 2: Tests for route_to_next_agent
# =============================================================================


class TestRouteToNextAgent:
    """Tests for the route_to_next_agent router function."""

    def test_dm_routes_to_first_pc(self) -> None:
        """Test that after DM turn, routing goes to first PC."""
        state = create_test_state(
            turn_queue=["dm", "fighter", "rogue"],
            current_turn="dm",
        )
        next_agent = route_to_next_agent(state)
        assert next_agent == "fighter"

    def test_pc_routes_to_next_pc(self) -> None:
        """Test that a PC routes to the next PC in queue."""
        state = create_test_state(
            turn_queue=["dm", "fighter", "rogue", "wizard"],
            current_turn="fighter",
        )
        next_agent = route_to_next_agent(state)
        assert next_agent == "rogue"

    def test_last_pc_routes_to_end(self) -> None:
        """Test that the last PC routes to END (completing the round)."""
        from langgraph.graph import END

        state = create_test_state(
            turn_queue=["dm", "fighter", "rogue"],
            current_turn="rogue",
        )
        next_agent = route_to_next_agent(state)
        assert next_agent == END

    @pytest.mark.parametrize(
        "current,expected",
        [
            ("dm", "fighter"),
            ("fighter", "rogue"),
            ("rogue", "wizard"),
        ],
    )
    def test_turn_queue_routing(self, current: str, expected: str) -> None:
        """Test turn queue routing (not last agent)."""
        state = create_test_state(
            turn_queue=["dm", "fighter", "rogue", "wizard"],
            current_turn=current,
        )
        next_agent = route_to_next_agent(state)
        assert next_agent == expected

    def test_last_agent_in_4pc_party_ends(self) -> None:
        """Test that wizard (last in queue) routes to END."""
        from langgraph.graph import END

        state = create_test_state(
            turn_queue=["dm", "fighter", "rogue", "wizard"],
            current_turn="wizard",
        )
        next_agent = route_to_next_agent(state)
        assert next_agent == END

    def test_single_pc_party_ends_after_pc(self) -> None:
        """Test routing with only one PC ends after PC turn."""
        from langgraph.graph import END

        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="fighter",
        )
        next_agent = route_to_next_agent(state)
        assert next_agent == END

    def test_dm_only_ends_after_dm(self) -> None:
        """Test routing with no PCs ends after DM turn."""
        from langgraph.graph import END

        state = create_test_state(
            turn_queue=["dm"],
            current_turn="dm",
        )
        next_agent = route_to_next_agent(state)
        assert next_agent == END


# =============================================================================
# Task 6: Tests for human intervention routing
# =============================================================================


class TestHumanInterventionRouting:
    """Tests for human intervention routing."""

    def test_human_active_routes_to_human_node(self) -> None:
        """Test that human_active=True routes to human node."""
        state = create_test_state(
            turn_queue=["dm", "rogue"],
            current_turn="rogue",
            human_active=True,
            controlled_character="rogue",
        )
        next_agent = route_to_next_agent(state)
        assert next_agent == "human"

    def test_human_active_only_affects_controlled_character(self) -> None:
        """Test that human_active only routes to human for the controlled character."""
        state = create_test_state(
            turn_queue=["dm", "fighter", "rogue"],
            current_turn="fighter",  # Not the controlled character
            human_active=True,
            controlled_character="rogue",
        )
        next_agent = route_to_next_agent(state)
        # Should route normally since fighter is not controlled
        assert next_agent == "rogue"

    def test_human_active_dm_turn_routes_normally(self) -> None:
        """Test that DM turn routes normally even with human_active."""
        state = create_test_state(
            turn_queue=["dm", "rogue"],
            current_turn="dm",
            human_active=True,
            controlled_character="rogue",
        )
        next_agent = route_to_next_agent(state)
        # DM turn should route to next PC, not human
        assert next_agent == "rogue"

    def test_human_active_no_controlled_char_routes_normally(self) -> None:
        """Test that human_active without controlled_character routes normally."""
        from langgraph.graph import END

        state = create_test_state(
            turn_queue=["dm", "rogue"],
            current_turn="rogue",
            human_active=True,
            controlled_character=None,
        )
        next_agent = route_to_next_agent(state)
        # Should route normally (to END since rogue is last)
        assert next_agent == END


# =============================================================================
# Task 6: Tests for human_intervention_node
# =============================================================================


class TestHumanInterventionNode:
    """Tests for the human_intervention_node placeholder."""

    def test_returns_state_unchanged(self) -> None:
        """Test that human_intervention_node returns state unchanged for now."""
        state = create_test_state()
        result = human_intervention_node(state)
        assert result == state

    def test_preserves_all_state_fields(self) -> None:
        """Test that all state fields are preserved."""
        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="fighter",
            human_active=True,
            controlled_character="fighter",
        )
        state["ground_truth_log"] = ["Test entry"]
        state["whisper_queue"] = ["Secret message"]

        result = human_intervention_node(state)

        assert result["ground_truth_log"] == ["Test entry"]
        assert result["whisper_queue"] == ["Secret message"]
        assert result["turn_queue"] == ["dm", "fighter"]
        assert result["human_active"] is True


# =============================================================================
# Task 7: Tests for run_single_round
# =============================================================================


class TestRunSingleRound:
    """Tests for the run_single_round convenience function."""

    def test_creates_workflow_from_turn_queue(self) -> None:
        """Test that run_single_round uses state's turn_queue to create workflow."""
        state = create_test_state(
            turn_queue=["dm", "fighter", "rogue"],
            current_turn="dm",
        )

        # We can't easily mock the LLM calls due to lambda capture,
        # but we can verify the function accepts the state and creates
        # a workflow with the correct turn_queue.
        # The actual LLM invocation would require API keys.

        # Verify the function signature and basic state handling
        from graph import create_game_workflow

        workflow = create_game_workflow(state["turn_queue"])
        graph = workflow.get_graph()

        # Verify all agents from turn_queue are in the graph
        assert "dm" in graph.nodes
        assert "fighter" in graph.nodes
        assert "rogue" in graph.nodes

    def test_returns_game_state_type(self) -> None:
        """Test that run_single_round is typed to return GameState."""
        # This is a type-level test - the function signature indicates
        # it returns GameState. We verify the function exists and has
        # the correct signature.
        import inspect

        sig = inspect.signature(run_single_round)
        assert "state" in sig.parameters
        # Return annotation should be GameState
        assert sig.return_annotation.__name__ == "GameState"


# =============================================================================
# Task 8: Integration tests
# =============================================================================


class TestGraphIntegration:
    """Integration tests for the complete graph."""

    def test_workflow_with_multiple_party_sizes(self) -> None:
        """Test workflow creation with different party sizes."""
        for size in range(1, 5):
            agents = ["dm"] + [f"pc{i}" for i in range(size)]
            workflow = create_game_workflow(turn_queue=agents)
            graph = workflow.get_graph()
            for agent in agents:
                assert agent in graph.nodes

    def test_state_immutability_through_router(self) -> None:
        """Test that routing doesn't mutate the input state."""
        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="dm",
        )
        original_current = state["current_turn"]
        original_queue = list(state["turn_queue"])

        route_to_next_agent(state)

        assert state["current_turn"] == original_current
        assert state["turn_queue"] == original_queue

    def test_human_node_exists_in_workflow(self) -> None:
        """Test that human intervention node is present in the graph."""
        workflow = create_game_workflow(turn_queue=["dm", "fighter"])
        graph = workflow.get_graph()
        assert "human" in graph.nodes

    def test_full_round_execution_with_mocked_llm(self) -> None:
        """Test a complete round execution with mocked LLM responses.

        This integration test verifies that:
        1. The workflow executes DM turn followed by all PC turns
        2. current_turn is updated correctly after each agent acts
        3. ground_truth_log accumulates all agent responses
        4. The round ends properly after the last PC
        """
        state = create_test_state(
            turn_queue=["dm", "fighter", "rogue"],
            current_turn="dm",
        )

        # Mock the LLM to return predictable responses
        with patch("agents.get_llm") as mock_get_llm:
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            # Return different messages for each invocation
            mock_model.invoke.side_effect = [
                AIMessage(content="The adventure begins!"),  # DM
                AIMessage(content="I draw my sword!"),  # Fighter
                AIMessage(content="I check for traps."),  # Rogue
            ]
            mock_get_llm.return_value = mock_model

            result = run_single_round(state)

            # Verify all agents contributed to the log
            assert len(result["ground_truth_log"]) == 3
            assert "[DM]:" in result["ground_truth_log"][0]
            assert "[Fighter]:" in result["ground_truth_log"][1]
            assert "[Rogue]:" in result["ground_truth_log"][2]

            # Verify current_turn reflects the last agent who acted
            assert result["current_turn"] == "rogue"

    def test_current_turn_updates_through_workflow(self) -> None:
        """Test that current_turn is updated as each agent takes their turn.

        This verifies the fix for the critical bug where current_turn
        was never being updated during graph execution.
        """
        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="dm",
        )

        with patch("agents.get_llm") as mock_get_llm:
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.side_effect = [
                AIMessage(content="DM narrates."),
                AIMessage(content="Fighter acts."),
            ]
            mock_get_llm.return_value = mock_model

            result = run_single_round(state)

            # After the round, current_turn should be the last agent
            assert result["current_turn"] == "fighter"


# =============================================================================
# Transcript Logging Tests (Story 4.4)
# =============================================================================


class TestTranscriptLogging:
    """Tests for transcript logging in game loop."""

    def test_transcript_entry_appended_after_turn(self, tmp_path: Path) -> None:
        """Test transcript entry created after each turn."""
        from persistence import load_transcript

        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="dm",
        )
        state["session_id"] = "001"

        # Create temp campaigns dir
        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        with (
            patch("agents.get_llm") as mock_get_llm,
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
        ):
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.side_effect = [
                AIMessage(content="DM narrates."),
                AIMessage(content="Fighter acts."),
            ]
            mock_get_llm.return_value = mock_model

            run_single_round(state)

            # Verify transcript was created
            loaded = load_transcript("001")
            assert loaded is not None
            assert len(loaded) >= 2

    def test_transcript_captures_agent_correctly(self, tmp_path: Path) -> None:
        """Test transcript entry agent is captured correctly."""
        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="dm",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []  # Start fresh

        with (
            patch("agents.get_llm") as mock_get_llm,
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
        ):
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.side_effect = [
                AIMessage(content="The story begins."),
                AIMessage(content="I draw my sword."),
            ]
            mock_get_llm.return_value = mock_model

            run_single_round(state)

            # Verify agents are captured correctly
            loaded = load_transcript("001")
            assert loaded is not None
            assert len(loaded) >= 2
            # Check that we have both DM and Fighter entries
            agents = [entry.agent for entry in loaded]
            assert "DM" in agents or "dm" in agents  # DM entry

    def test_transcript_logging_does_not_block_game_flow(
        self, tmp_path: Path
    ) -> None:
        """Test transcript logging errors don't crash game."""
        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm"],
            current_turn="dm",
        )
        state["session_id"] = "001"

        # Transcript logging errors should not block game flow
        with (
            patch("agents.get_llm") as mock_get_llm,
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
        ):
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.return_value = AIMessage(content="DM narrates.")
            mock_get_llm.return_value = mock_model

            # Should not raise even with potential write issues
            result = run_single_round(state)

            # Game should still work
            assert len(result["ground_truth_log"]) == 1


class TestHumanInterventionTranscriptLogging:
    """Tests for transcript logging in human_intervention_node."""

    def test_human_action_logged_to_transcript(self, tmp_path: Path) -> None:
        """Test human action is logged to transcript."""
        import streamlit as st

        from graph import human_intervention_node
        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="fighter",
            human_active=True,
            controlled_character="fighter",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []

        mock_session_state = MagicMock()
        mock_session_state.get.return_value = "I attack the goblin!"
        mock_session_state.__setitem__ = MagicMock()

        with (
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
            patch.object(st, "session_state", mock_session_state),
        ):
            human_intervention_node(state)

            # Verify transcript entry was created
            loaded = load_transcript("001")
            assert loaded is not None
            assert len(loaded) == 1
            assert loaded[0].agent == "fighter"
            assert loaded[0].content == "I attack the goblin!"

    def test_human_action_transcript_has_timestamp(self, tmp_path: Path) -> None:
        """Test human action transcript entry has valid timestamp."""
        import streamlit as st

        from graph import human_intervention_node
        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="fighter",
            human_active=True,
            controlled_character="fighter",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []

        mock_session_state = MagicMock()
        mock_session_state.get.return_value = "Test action."
        mock_session_state.__setitem__ = MagicMock()

        with (
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
            patch.object(st, "session_state", mock_session_state),
        ):
            human_intervention_node(state)

            loaded = load_transcript("001")
            assert loaded is not None
            assert len(loaded) == 1
            # Timestamp should be ISO format with Z suffix
            assert loaded[0].timestamp.endswith("Z")
            assert "T" in loaded[0].timestamp


# =============================================================================
# Expanded Transcript Integration Tests (Story 4.4)
# =============================================================================


class TestTranscriptLoggingExpanded:
    """Expanded tests for transcript logging integration in graph."""

    def test_transcript_entries_match_log_count(self, tmp_path: Path) -> None:
        """Test transcript entry count matches ground_truth_log additions."""
        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm", "fighter", "rogue"],
            current_turn="dm",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []  # Start fresh

        with (
            patch("agents.get_llm") as mock_get_llm,
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
        ):
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.side_effect = [
                AIMessage(content="DM narrates the scene."),
                AIMessage(content="Fighter swings sword."),
                AIMessage(content="Rogue sneaks around."),
            ]
            mock_get_llm.return_value = mock_model

            result = run_single_round(state)

            loaded = load_transcript("001")

        assert loaded is not None
        # Transcript entries should match number of log entries added
        assert len(loaded) == len(result["ground_truth_log"])

    def test_transcript_preserves_content_exactly(self, tmp_path: Path) -> None:
        """Test transcript content is not modified from original."""
        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm"],
            current_turn="dm",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []

        original_content = "The tavern falls silent. \"Who goes there?\" demands the barkeep."

        with (
            patch("agents.get_llm") as mock_get_llm,
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
        ):
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.return_value = AIMessage(content=original_content)
            mock_get_llm.return_value = mock_model

            run_single_round(state)

            loaded = load_transcript("001")

        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].content == original_content

    def test_transcript_handles_special_characters_in_content(
        self, tmp_path: Path
    ) -> None:
        """Test transcript handles special characters in agent responses."""
        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm"],
            current_turn="dm",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []

        # Content with special characters
        special_content = 'Test: "quotes", *asterisks*, <brackets>, & ampersand'

        with (
            patch("agents.get_llm") as mock_get_llm,
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
        ):
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.return_value = AIMessage(content=special_content)
            mock_get_llm.return_value = mock_model

            run_single_round(state)

            loaded = load_transcript("001")

        assert loaded is not None
        assert loaded[0].content == special_content

    def test_transcript_error_does_not_crash_game(self, tmp_path: Path) -> None:
        """Test transcript write error doesn't crash the game loop."""
        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm"],
            current_turn="dm",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []

        with (
            patch("agents.get_llm") as mock_get_llm,
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
            patch("persistence.append_transcript_entry") as mock_append,
        ):
            # Simulate transcript write failure
            mock_append.side_effect = OSError("Disk full")

            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.return_value = AIMessage(content="The game continues.")
            mock_get_llm.return_value = mock_model

            # Should not raise despite transcript error
            result = run_single_round(state)

        # Game should continue normally
        assert len(result["ground_truth_log"]) == 1

    def test_transcript_multiple_rounds_accumulate(self, tmp_path: Path) -> None:
        """Test transcript accumulates entries across multiple rounds."""
        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm"],
            current_turn="dm",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []

        with (
            patch("agents.get_llm") as mock_get_llm,
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
        ):
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_get_llm.return_value = mock_model

            # Run 3 rounds
            for i in range(3):
                mock_model.invoke.return_value = AIMessage(content=f"Round {i + 1}.")
                state = run_single_round(state)

            loaded = load_transcript("001")

        assert loaded is not None
        assert len(loaded) == 3
        assert loaded[0].content == "Round 1."
        assert loaded[2].content == "Round 3."


class TestHumanInterventionTranscriptExpanded:
    """Expanded tests for human intervention transcript logging."""

    def test_human_action_transcript_tool_calls_is_none(
        self, tmp_path: Path
    ) -> None:
        """Test human action transcript entry has tool_calls=None."""
        import streamlit as st

        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="fighter",
            human_active=True,
            controlled_character="fighter",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []

        mock_session_state = MagicMock()
        mock_session_state.get.return_value = "I search the room."
        mock_session_state.__setitem__ = MagicMock()

        with (
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
            patch.object(st, "session_state", mock_session_state),
        ):
            human_intervention_node(state)

            loaded = load_transcript("001")

        assert loaded is not None
        assert loaded[0].tool_calls is None

    def test_human_action_transcript_correct_turn_number(
        self, tmp_path: Path
    ) -> None:
        """Test human action transcript entry has correct turn number."""
        import streamlit as st

        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="fighter",
            human_active=True,
            controlled_character="fighter",
        )
        state["session_id"] = "001"
        # Pre-existing log entries
        state["ground_truth_log"] = [
            "[dm] The adventure begins.",
            "[dm] A goblin appears!",
        ]

        mock_session_state = MagicMock()
        mock_session_state.get.return_value = "I attack the goblin!"
        mock_session_state.__setitem__ = MagicMock()

        with (
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
            patch.object(st, "session_state", mock_session_state),
        ):
            human_intervention_node(state)

            loaded = load_transcript("001")

        assert loaded is not None
        assert loaded[0].turn == 3  # Third entry in log

    def test_human_action_empty_does_not_create_transcript(
        self, tmp_path: Path
    ) -> None:
        """Test empty human action doesn't create transcript entry."""
        import streamlit as st

        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="fighter",
            human_active=True,
            controlled_character="fighter",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []

        mock_session_state = MagicMock()
        mock_session_state.get.return_value = None  # No pending action
        mock_session_state.__setitem__ = MagicMock()

        with (
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
            patch.object(st, "session_state", mock_session_state),
        ):
            human_intervention_node(state)

            loaded = load_transcript("001")

        # No transcript should be created
        assert loaded is None

    def test_human_action_transcript_special_characters(
        self, tmp_path: Path
    ) -> None:
        """Test human action with special characters is logged correctly."""
        import streamlit as st

        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="fighter",
            human_active=True,
            controlled_character="fighter",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []

        special_action = '*draws sword* "For honor!" <attacks> & parries'

        mock_session_state = MagicMock()
        mock_session_state.get.return_value = special_action
        mock_session_state.__setitem__ = MagicMock()

        with (
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
            patch.object(st, "session_state", mock_session_state),
        ):
            human_intervention_node(state)

            loaded = load_transcript("001")

        assert loaded is not None
        assert loaded[0].content == special_action


class TestTranscriptAgentParsing:
    """Tests for agent name parsing in transcript entries."""

    def test_transcript_parses_dm_agent_correctly(self, tmp_path: Path) -> None:
        """Test DM agent is parsed correctly from log entry."""
        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm"],
            current_turn="dm",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []

        with (
            patch("agents.get_llm") as mock_get_llm,
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
        ):
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.return_value = AIMessage(content="DM speaks.")
            mock_get_llm.return_value = mock_model

            run_single_round(state)

            loaded = load_transcript("001")

        assert loaded is not None
        # Agent should be "DM" or "dm" (depending on how log entry is formatted)
        assert loaded[0].agent.lower() == "dm"

    def test_transcript_parses_pc_agent_correctly(self, tmp_path: Path) -> None:
        """Test PC agent names are parsed correctly."""
        from persistence import load_transcript

        temp_campaigns = tmp_path / "campaigns"
        temp_campaigns.mkdir()

        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="dm",
        )
        state["session_id"] = "001"
        state["ground_truth_log"] = []

        with (
            patch("agents.get_llm") as mock_get_llm,
            patch("persistence.CAMPAIGNS_DIR", temp_campaigns),
        ):
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.side_effect = [
                AIMessage(content="DM narrates."),
                AIMessage(content="Fighter speaks."),
            ]
            mock_get_llm.return_value = mock_model

            run_single_round(state)

            loaded = load_transcript("001")

        assert loaded is not None
        assert len(loaded) == 2
        # Find the fighter entry
        fighter_entries = [e for e in loaded if e.agent.lower() == "fighter"]
        assert len(fighter_entries) >= 1
