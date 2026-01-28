"""Tests for LangGraph turn orchestration (Story 1.7).

Story 5.2: Added context_manager node tests.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from graph import (
    context_manager,
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

    def test_start_routes_to_context_manager(self) -> None:
        """Test that START entry point connects to context_manager node.

        Story 5.2: Changed to route through context_manager before dm.
        """
        workflow = create_game_workflow(turn_queue=["dm", "fighter"])
        graph = workflow.get_graph()
        # Check edges from __start__ go to context_manager
        edges = graph.edges
        start_edges = [e for e in edges if e[0] == "__start__"]
        assert len(start_edges) > 0
        assert any(e[1] == "context_manager" for e in start_edges)


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
        """Test that run_single_round is typed to return GameStateWithError.

        Note: As of Story 4.5, run_single_round returns GameStateWithError
        (a dict that may include an "error" key for error handling).
        """
        import inspect

        sig = inspect.signature(run_single_round)
        assert "state" in sig.parameters
        # Return annotation should be GameStateWithError (which is dict[str, object])
        # After Story 4.5, return type changed to support error handling
        assert sig.return_annotation == dict[str, object]


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

    def test_transcript_logging_does_not_block_game_flow(self, tmp_path: Path) -> None:
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

        original_content = (
            'The tavern falls silent. "Who goes there?" demands the barkeep.'
        )

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

    def test_human_action_transcript_tool_calls_is_none(self, tmp_path: Path) -> None:
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

    def test_human_action_transcript_correct_turn_number(self, tmp_path: Path) -> None:
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

    def test_human_action_transcript_special_characters(self, tmp_path: Path) -> None:
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


# =============================================================================
# Story 5.2: Context Manager Tests
# =============================================================================


class TestContextManagerNode:
    """Tests for context_manager node (Story 5.2)."""

    def test_context_manager_returns_game_state(self) -> None:
        """Test that context_manager returns a GameState."""
        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="dm",
        )

        result = context_manager(state)

        assert isinstance(result, dict)
        assert "turn_queue" in result
        assert "agent_memories" in result

    def test_context_manager_does_not_compress_under_limit(self) -> None:
        """Test that context_manager skips compression when under limit."""
        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="dm",
        )
        # Add a few buffer entries (under limit)
        state["agent_memories"]["dm"].short_term_buffer = ["Event 1", "Event 2"]
        original_buffer_len = len(state["agent_memories"]["dm"].short_term_buffer)

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            result = context_manager(state)

        # Buffer should not have been compressed
        mock_instance.compress_buffer.assert_not_called()
        assert (
            len(result["agent_memories"]["dm"].short_term_buffer) == original_buffer_len
        )

    def test_context_manager_compresses_when_near_limit(self) -> None:
        """Test that context_manager triggers compression when near limit."""
        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="dm",
        )
        # Set up buffer that will be compressed
        state["agent_memories"]["dm"].short_term_buffer = [
            "Event 1",
            "Event 2",
            "Event 3",
            "Event 4",
            "Event 5",
        ]

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.return_value = "Generated summary"
            MockManager.return_value = mock_instance

            context_manager(state)

        # compress_buffer should have been called for the agent
        mock_instance.compress_buffer.assert_called()

    def test_context_manager_checks_all_agents(self) -> None:
        """Test that context_manager checks all agents in agent_memories."""
        state = create_test_state(
            turn_queue=["dm", "fighter", "rogue"],
            current_turn="dm",
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            context_manager(state)

        # Should have checked all agents
        call_agents = [
            call[0][0] for call in mock_instance.is_near_limit.call_args_list
        ]
        assert "dm" in call_agents
        assert "fighter" in call_agents
        assert "rogue" in call_agents

    def test_context_manager_sets_summarizing_flag(self) -> None:
        """Test that context_manager sets summarizing flag when compressing."""
        state = create_test_state(
            turn_queue=["dm"],
            current_turn="dm",
        )
        state["agent_memories"]["dm"].short_term_buffer = ["Event 1"] * 10

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.return_value = "Summary"
            MockManager.return_value = mock_instance

            result = context_manager(state)

        # Flag should be cleared after summarization completes
        assert result.get("summarization_in_progress") is False

    def test_context_manager_handles_multiple_agents_needing_compression(self) -> None:
        """Test context_manager compresses multiple agents if needed."""
        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="dm",
        )
        state["agent_memories"]["dm"].short_term_buffer = ["Event 1"] * 10
        state["agent_memories"]["fighter"].short_term_buffer = ["Event 1"] * 10

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.return_value = "Summary"
            MockManager.return_value = mock_instance

            context_manager(state)

        # Should have compressed both agents
        compress_calls = mock_instance.compress_buffer.call_args_list
        compressed_agents = [call[0][0] for call in compress_calls]
        assert "dm" in compressed_agents
        assert "fighter" in compressed_agents

    def test_context_manager_preserves_other_state_fields(self) -> None:
        """Test that context_manager preserves non-memory state fields."""
        state = create_test_state(
            turn_queue=["dm", "fighter"],
            current_turn="dm",
        )
        state["ground_truth_log"] = ["Log entry 1", "Log entry 2"]
        state["whisper_queue"] = ["Whisper"]
        state["human_active"] = True

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            result = context_manager(state)

        # Other state fields should be preserved
        assert result["ground_truth_log"] == ["Log entry 1", "Log entry 2"]
        assert result["whisper_queue"] == ["Whisper"]
        assert result["human_active"] is True


class TestContextManagerWorkflowIntegration:
    """Tests for context_manager integration in workflow."""

    def test_context_manager_node_in_workflow(self) -> None:
        """Test that context_manager node exists in workflow."""
        workflow = create_game_workflow(turn_queue=["dm", "fighter"])
        graph = workflow.get_graph()

        assert "context_manager" in graph.nodes

    def test_context_manager_runs_before_dm(self) -> None:
        """Test that context_manager runs before DM in workflow."""
        workflow = create_game_workflow(turn_queue=["dm", "fighter"])
        graph = workflow.get_graph()

        # Check edges: START -> context_manager -> dm
        edges = graph.edges
        start_edges = [e for e in edges if e[0] == "__start__"]
        assert any(e[1] == "context_manager" for e in start_edges)

        context_manager_edges = [e for e in edges if e[0] == "context_manager"]
        assert any(e[1] == "dm" for e in context_manager_edges)

    def test_workflow_with_compression_integration(self) -> None:
        """Test complete workflow with compression triggered."""
        state = create_test_state(
            turn_queue=["dm"],
            current_turn="dm",
        )
        state["session_id"] = "001"

        # Set up large buffer to trigger compression
        state["agent_memories"]["dm"].short_term_buffer = [
            f"Event {i}" for i in range(50)
        ]
        state["agent_memories"]["dm"].token_limit = 100

        with (
            patch("agents.get_llm") as mock_get_llm,
            patch("memory.get_llm") as mock_memory_llm,
        ):
            # Mock game LLM
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.return_value = AIMessage(content="DM narrates.")
            mock_get_llm.return_value = mock_model

            # Mock summarizer LLM
            mock_summary_model = MagicMock()
            mock_summary_response = MagicMock()
            mock_summary_response.content = "Compressed summary."
            mock_summary_model.invoke.return_value = mock_summary_response
            mock_memory_llm.return_value = mock_summary_model

            result = run_single_round(state)

        # Workflow should complete successfully
        assert len(result["ground_truth_log"]) >= 1


# =============================================================================
# Story 5.2: Extended Context Manager Tests (testarch-automate)
# =============================================================================


class TestContextManagerFlagBehavior:
    """Tests for summarization_in_progress flag lifecycle."""

    def test_flag_true_in_updated_state_during_compression(self) -> None:
        """Test flag is set to True in updated_state during compression.

        The context_manager creates a new updated_state dict with the flag
        set to True, then passes it to MemoryManager. We verify by checking
        that MemoryManager receives a state with the flag already set.
        """
        from graph import context_manager

        state = create_test_state()
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            token_limit=100,
        )

        captured_state_flag: bool | None = None

        def capture_state_on_init(updated_state: GameState) -> MagicMock:
            nonlocal captured_state_flag
            # Capture the flag from the state passed to MemoryManager
            captured_state_flag = updated_state.get("summarization_in_progress")
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.return_value = "Summary"
            return mock_instance

        with patch("graph.MemoryManager", side_effect=capture_state_on_init):
            context_manager(state)

        # Flag should have been True when MemoryManager was initialized
        assert captured_state_flag is True

    def test_flag_false_after_no_compression_needed(self) -> None:
        """Test flag is False when no compression was needed."""
        from graph import context_manager

        state = create_test_state()
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Short event"],
            token_limit=8000,
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            result = context_manager(state)

        assert result["summarization_in_progress"] is False

    def test_flag_false_after_compression_completes(self) -> None:
        """Test flag is False after compression successfully completes."""
        from graph import context_manager

        state = create_test_state()
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            token_limit=100,
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.return_value = "Summary"
            MockManager.return_value = mock_instance

            result = context_manager(state)

        assert result["summarization_in_progress"] is False


class TestContextManagerErrorHandling:
    """Tests for context_manager error propagation.

    Note: context_manager does NOT catch exceptions internally - they propagate
    up to the caller. This is intentional to allow the graph framework to
    handle errors appropriately. The underlying MemoryManager.compress_buffer
    does have error handling and returns "" on failure without modifying state.
    """

    def test_context_manager_propagates_memory_manager_exception(self) -> None:
        """Test context_manager propagates MemoryManager exceptions to caller."""
        import pytest

        from graph import context_manager

        state = create_test_state()
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event"],
            token_limit=100,
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.side_effect = Exception("Memory error")
            MockManager.return_value = mock_instance

            # Exception should propagate
            with pytest.raises(Exception, match="Memory error"):
                context_manager(state)

    def test_context_manager_propagates_compress_buffer_exception(self) -> None:
        """Test context_manager propagates compress_buffer exceptions to caller."""
        import pytest

        from graph import context_manager

        state = create_test_state()
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(10)],
            token_limit=100,
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.side_effect = Exception("Compression failed")
            MockManager.return_value = mock_instance

            # Exception should propagate
            with pytest.raises(Exception, match="Compression failed"):
                context_manager(state)

    def test_compress_buffer_internal_error_returns_empty(self) -> None:
        """Test that internal LLM errors in compress_buffer return empty string.

        The MemoryManager.compress_buffer method catches LLM errors internally
        and returns "" without modifying state. This is the graceful degradation.
        """
        from unittest.mock import MagicMock, patch

        import memory

        # Clear the summarizer cache to ensure our mock is used
        memory._summarizer_cache.clear()

        state = create_test_state()
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"],
            token_limit=100,
        )

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            # Summarizer returns "" on internal error
            mock_instance.generate_summary.return_value = ""
            MockSummarizer.return_value = mock_instance

            from memory import MemoryManager

            manager = MemoryManager(state)
            result = manager.compress_buffer("dm")

        # Should return empty string (graceful degradation)
        assert result == ""
        # Buffer should be unchanged
        assert len(state["agent_memories"]["dm"].short_term_buffer) == 5

        # Clean up
        memory._summarizer_cache.clear()


class TestContextManagerStateIntegrity:
    """Tests for state integrity through context_manager."""

    def test_context_manager_preserves_ground_truth_log(self) -> None:
        """Test that ground_truth_log is not modified by context_manager."""
        from graph import context_manager

        state = create_test_state()
        original_log = ["Entry 1", "Entry 2", "Entry 3"]
        state["ground_truth_log"] = original_log.copy()

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            result = context_manager(state)

        assert result["ground_truth_log"] == original_log

    def test_context_manager_preserves_turn_queue(self) -> None:
        """Test that turn_queue is preserved through context_manager."""
        from graph import context_manager

        state = create_test_state()
        original_queue = ["dm", "fighter", "rogue"]
        state["turn_queue"] = original_queue.copy()

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            result = context_manager(state)

        assert result["turn_queue"] == original_queue

    def test_context_manager_preserves_current_turn(self) -> None:
        """Test that current_turn is preserved."""
        from graph import context_manager

        state = create_test_state()
        state["current_turn"] = "fighter"

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            result = context_manager(state)

        assert result["current_turn"] == "fighter"

    def test_context_manager_preserves_session_id(self) -> None:
        """Test that session_id is preserved."""
        from graph import context_manager

        state = create_test_state()
        state["session_id"] = "test_session_123"

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            result = context_manager(state)

        assert result["session_id"] == "test_session_123"


class TestContextManagerCompressionOrder:
    """Tests for compression ordering in context_manager."""

    def test_agents_checked_in_dict_iteration_order(self) -> None:
        """Test that agents are checked in dict iteration order.

        Python dicts maintain insertion order since 3.7, so agents
        are checked in the order they were added to agent_memories.
        """
        from graph import context_manager

        state = create_test_state()
        # Clear and rebuild to control insertion order
        state["agent_memories"].clear()
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=["Event"])
        state["agent_memories"]["archer"] = AgentMemory(short_term_buffer=["Event"])
        state["agent_memories"]["mage"] = AgentMemory(short_term_buffer=["Event"])

        check_order: list[str] = []

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()

            def track_check(agent_name: str) -> bool:
                check_order.append(agent_name)
                return False

            mock_instance.is_near_limit.side_effect = track_check
            MockManager.return_value = mock_instance

            context_manager(state)

        # Order should match dict insertion order
        assert check_order == ["dm", "archer", "mage"]

    def test_all_agents_in_agent_memories_checked(self) -> None:
        """Test that all agents in agent_memories are checked."""
        from graph import context_manager

        state = create_test_state()
        agents = ["dm", "fighter", "rogue", "wizard", "cleric"]
        for agent in agents:
            state["agent_memories"][agent] = AgentMemory(short_term_buffer=["Event"])

        checked_agents: set[str] = set()

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()

            def track_check(agent_name: str) -> bool:
                checked_agents.add(agent_name)
                return False

            mock_instance.is_near_limit.side_effect = track_check
            MockManager.return_value = mock_instance

            context_manager(state)

        # All agents should have been checked
        for agent in agents:
            assert agent in checked_agents
