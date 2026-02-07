"""Tests for Story 10-2: DM Whisper Tool.

Tests the dm_whisper_to_agent tool function and its integration with
the DM agent and dm_turn() function for creating whispers during gameplay.
"""

from unittest.mock import MagicMock, patch

import pytest

from models import (
    AgentMemory,
    AgentSecrets,
    CharacterConfig,
    DMConfig,
    GameConfig,
    GameState,
    NarrativeElementStore,
    Whisper,
    create_whisper,
)
from tools import dm_whisper_to_agent

# =============================================================================
# Tool Schema Tests
# =============================================================================


class TestWhisperToolSchema:
    """Tests for the dm_whisper_to_agent tool schema and metadata."""

    def test_tool_has_correct_name(self) -> None:
        """Test tool has the expected name."""
        assert dm_whisper_to_agent.name == "dm_whisper_to_agent"

    def test_tool_has_docstring(self) -> None:
        """Test tool has a docstring for LLM guidance."""
        assert dm_whisper_to_agent.description is not None
        assert len(dm_whisper_to_agent.description) > 100  # Substantial docstring

    def test_tool_docstring_includes_usage_guidance(self) -> None:
        """Test tool docstring includes when-to-use guidance."""
        description = dm_whisper_to_agent.description
        assert "dramatic irony" in description.lower()
        assert "private" in description.lower()

    def test_tool_docstring_includes_examples(self) -> None:
        """Test tool docstring includes usage examples."""
        description = dm_whisper_to_agent.description
        assert "concealed door" in description or "notice" in description.lower()

    def test_tool_returns_confirmation_format(self) -> None:
        """Test tool returns expected confirmation format."""
        result = dm_whisper_to_agent.invoke(
            {"character_name": "Thorin", "secret_info": "Test secret"}
        )
        assert "Secret shared with Thorin" in result

    def test_tool_returns_confirmation_with_context(self) -> None:
        """Test tool returns confirmation even when context is provided."""
        result = dm_whisper_to_agent.invoke(
            {
                "character_name": "Shadowmere",
                "secret_info": "Hidden door",
                "context": "Rogue's high perception",
            }
        )
        assert "Secret shared with Shadowmere" in result

    def test_tool_is_exported(self) -> None:
        """Test tool is exported in tools.__all__."""
        import tools

        assert "dm_whisper_to_agent" in tools.__all__


# =============================================================================
# Execute Whisper Helper Tests
# =============================================================================


class TestExecuteWhisper:
    """Tests for the _execute_whisper helper function."""

    def test_execute_whisper_creates_whisper(self) -> None:
        """Test _execute_whisper creates a Whisper object."""
        from agents import _execute_whisper

        agent_secrets: dict[str, AgentSecrets] = {}
        tool_args = {
            "character_name": "Thorin",
            "secret_info": "The merchant is lying",
        }

        result = _execute_whisper(tool_args, agent_secrets, turn_number=5)

        # Confirmation uses normalized lowercase key for consistency
        assert "Secret shared with thorin" in result
        assert "thorin" in agent_secrets
        assert len(agent_secrets["thorin"].whispers) == 1

    def test_execute_whisper_sets_whisper_fields(self) -> None:
        """Test _execute_whisper sets all whisper fields correctly."""
        from agents import _execute_whisper

        agent_secrets: dict[str, AgentSecrets] = {}
        tool_args = {
            "character_name": "Shadowmere",
            "secret_info": "Trap ahead",
        }

        _execute_whisper(tool_args, agent_secrets, turn_number=10)

        whisper = agent_secrets["shadowmere"].whispers[0]
        assert whisper.from_agent == "dm"
        assert whisper.to_agent == "shadowmere"
        assert whisper.content == "Trap ahead"
        assert whisper.turn_created == 10
        assert whisper.revealed is False
        assert whisper.turn_revealed is None

    def test_execute_whisper_generates_unique_id(self) -> None:
        """Test _execute_whisper generates unique whisper IDs."""
        from agents import _execute_whisper

        agent_secrets: dict[str, AgentSecrets] = {}
        tool_args = {
            "character_name": "Fighter",
            "secret_info": "First secret",
        }

        _execute_whisper(tool_args, agent_secrets, turn_number=1)
        _execute_whisper(
            {"character_name": "Fighter", "secret_info": "Second secret"},
            agent_secrets,
            turn_number=2,
        )

        whispers = agent_secrets["fighter"].whispers
        assert len(whispers) == 2
        assert whispers[0].id != whispers[1].id

    def test_execute_whisper_creates_agent_secrets_if_missing(self) -> None:
        """Test _execute_whisper creates AgentSecrets for new agent."""
        from agents import _execute_whisper

        agent_secrets: dict[str, AgentSecrets] = {}

        _execute_whisper(
            {"character_name": "NewCharacter", "secret_info": "Secret"},
            agent_secrets,
            turn_number=1,
        )

        assert "newcharacter" in agent_secrets
        assert isinstance(agent_secrets["newcharacter"], AgentSecrets)

    def test_execute_whisper_normalizes_character_name(self) -> None:
        """Test _execute_whisper normalizes character name to lowercase."""
        from agents import _execute_whisper

        agent_secrets: dict[str, AgentSecrets] = {}

        # Mixed case name
        _execute_whisper(
            {"character_name": "THORIN", "secret_info": "Secret"},
            agent_secrets,
            turn_number=1,
        )

        # Should be stored lowercase
        assert "thorin" in agent_secrets
        assert "THORIN" not in agent_secrets
        assert agent_secrets["thorin"].whispers[0].to_agent == "thorin"

    def test_execute_whisper_adds_to_existing_secrets(self) -> None:
        """Test _execute_whisper appends to existing agent's whispers."""
        from agents import _execute_whisper

        existing_whisper = create_whisper("dm", "fighter", "First secret", 1)
        agent_secrets: dict[str, AgentSecrets] = {
            "fighter": AgentSecrets(whispers=[existing_whisper])
        }

        _execute_whisper(
            {"character_name": "Fighter", "secret_info": "Second secret"},
            agent_secrets,
            turn_number=2,
        )

        assert len(agent_secrets["fighter"].whispers) == 2
        assert agent_secrets["fighter"].whispers[0].content == "First secret"
        assert agent_secrets["fighter"].whispers[1].content == "Second secret"

    def test_execute_whisper_rejects_empty_character_name(self) -> None:
        """Test _execute_whisper returns error for empty character_name."""
        from agents import _execute_whisper

        agent_secrets: dict[str, AgentSecrets] = {}

        result = _execute_whisper(
            {"character_name": "", "secret_info": "Secret"},
            agent_secrets,
            turn_number=1,
        )

        assert "Error" in result
        assert "character_name" in result

    def test_execute_whisper_rejects_missing_character_name(self) -> None:
        """Test _execute_whisper returns error for missing character_name."""
        from agents import _execute_whisper

        agent_secrets: dict[str, AgentSecrets] = {}

        result = _execute_whisper(
            {"secret_info": "Secret"},
            agent_secrets,
            turn_number=1,
        )

        assert "Error" in result
        assert "character_name" in result

    def test_execute_whisper_rejects_empty_secret_info(self) -> None:
        """Test _execute_whisper returns error for empty secret_info."""
        from agents import _execute_whisper

        agent_secrets: dict[str, AgentSecrets] = {}

        result = _execute_whisper(
            {"character_name": "Fighter", "secret_info": ""},
            agent_secrets,
            turn_number=1,
        )

        assert "Error" in result
        assert "secret_info" in result

    def test_execute_whisper_rejects_missing_secret_info(self) -> None:
        """Test _execute_whisper returns error for missing secret_info."""
        from agents import _execute_whisper

        agent_secrets: dict[str, AgentSecrets] = {}

        result = _execute_whisper(
            {"character_name": "Fighter"},
            agent_secrets,
            turn_number=1,
        )

        assert "Error" in result
        assert "secret_info" in result

    def test_execute_whisper_handles_context_parameter(self) -> None:
        """Test _execute_whisper accepts optional context parameter."""
        from agents import _execute_whisper

        agent_secrets: dict[str, AgentSecrets] = {}

        result = _execute_whisper(
            {
                "character_name": "Rogue",
                "secret_info": "Trap detected",
                "context": "High perception roll",
            },
            agent_secrets,
            turn_number=5,
        )

        # Context is informational only - not stored in whisper
        # Confirmation uses normalized lowercase key for consistency
        assert "Secret shared with rogue" in result
        assert len(agent_secrets["rogue"].whispers) == 1

    def test_execute_whisper_is_exported(self) -> None:
        """Test _execute_whisper is exported in agents.__all__."""
        import agents

        assert "_execute_whisper" in agents.__all__

    def test_execute_whisper_warns_on_unknown_agent(self) -> None:
        """Test _execute_whisper logs warning for unknown agent names."""
        from unittest.mock import patch

        from agents import _execute_whisper

        agent_secrets: dict[str, AgentSecrets] = {}
        valid_agents = {"dm", "fighter", "rogue"}

        with patch("agents.logger") as mock_logger:
            result = _execute_whisper(
                {"character_name": "Gandalf", "secret_info": "Secret"},
                agent_secrets,
                turn_number=1,
                valid_agents=valid_agents,
            )

            # Should still succeed but log warning
            assert "Secret shared with gandalf" in result
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args
            assert "unknown agent" in call_args[0][0].lower()
            assert "gandalf" in call_args[0][1]

    def test_execute_whisper_no_warning_for_valid_agent(self) -> None:
        """Test _execute_whisper does not warn for valid agent names."""
        from unittest.mock import patch

        from agents import _execute_whisper

        agent_secrets: dict[str, AgentSecrets] = {}
        valid_agents = {"dm", "fighter", "rogue"}

        with patch("agents.logger") as mock_logger:
            result = _execute_whisper(
                {"character_name": "Fighter", "secret_info": "Secret"},
                agent_secrets,
                turn_number=1,
                valid_agents=valid_agents,
            )

            # Should succeed without warning
            assert "Secret shared with fighter" in result
            mock_logger.warning.assert_not_called()


# =============================================================================
# DM Agent Binding Tests
# =============================================================================


class TestDMAgentBinding:
    """Tests for whisper tool binding to DM agent."""

    def test_dm_agent_has_whisper_tool(self) -> None:
        """Test DM agent has whisper tool bound."""
        from agents import create_dm_agent

        dm_config = DMConfig(provider="gemini", model="gemini-1.5-flash")

        # Mock the LLM to avoid actual API calls
        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.bind_tools = MagicMock(return_value=mock_llm)
            mock_get_llm.return_value = mock_llm

            create_dm_agent(dm_config)

            # Verify bind_tools was called with the whisper tool
            bind_tools_call = mock_llm.bind_tools.call_args
            tools = bind_tools_call[0][0]  # First positional argument
            tool_names = [t.name for t in tools]

            assert "dm_whisper_to_agent" in tool_names

    def test_dm_agent_has_all_dm_tools(self) -> None:
        """Test DM agent has all expected tools bound."""
        from agents import create_dm_agent

        dm_config = DMConfig(provider="gemini", model="gemini-1.5-flash")

        with patch("agents.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.bind_tools = MagicMock(return_value=mock_llm)
            mock_get_llm.return_value = mock_llm

            create_dm_agent(dm_config)

            bind_tools_call = mock_llm.bind_tools.call_args
            tools = bind_tools_call[0][0]
            tool_names = [t.name for t in tools]

            assert "dm_roll_dice" in tool_names
            assert "dm_update_character_sheet" in tool_names
            assert "dm_whisper_to_agent" in tool_names


# =============================================================================
# DM System Prompt Tests
# =============================================================================


class TestDMSystemPrompt:
    """Tests for whisper guidance in DM system prompt."""

    def test_dm_prompt_includes_whisper_section(self) -> None:
        """Test DM_SYSTEM_PROMPT includes Private Whispers section."""
        from agents import DM_SYSTEM_PROMPT

        assert "Private Whispers" in DM_SYSTEM_PROMPT

    def test_dm_prompt_includes_whisper_tool_name(self) -> None:
        """Test DM_SYSTEM_PROMPT mentions the tool name."""
        from agents import DM_SYSTEM_PROMPT

        assert "dm_whisper_to_agent" in DM_SYSTEM_PROMPT

    def test_dm_prompt_includes_use_cases(self) -> None:
        """Test DM_SYSTEM_PROMPT includes whisper use cases."""
        from agents import DM_SYSTEM_PROMPT

        assert (
            "Perception" in DM_SYSTEM_PROMPT or "perception" in DM_SYSTEM_PROMPT.lower()
        )
        assert "background" in DM_SYSTEM_PROMPT.lower()
        assert (
            "divine" in DM_SYSTEM_PROMPT.lower()
            or "magical" in DM_SYSTEM_PROMPT.lower()
        )

    def test_dm_prompt_includes_examples(self) -> None:
        """Test DM_SYSTEM_PROMPT includes whisper examples."""
        from agents import DM_SYSTEM_PROMPT

        # Should have example whisper scenarios
        assert (
            "rogue" in DM_SYSTEM_PROMPT.lower() or "fighter" in DM_SYSTEM_PROMPT.lower()
        )


# =============================================================================
# dm_turn Integration Tests
# =============================================================================


class TestDmTurnWhisperIntegration:
    """Tests for whisper tool execution in dm_turn()."""

    @pytest.fixture
    def basic_game_state(self) -> GameState:
        """Create a minimal game state for testing."""
        return GameState(
            ground_truth_log=["[DM]: The adventure begins."],
            turn_queue=["dm", "fighter"],
            current_turn="dm",
            agent_memories={
                "dm": AgentMemory(token_limit=8000),
                "fighter": AgentMemory(token_limit=4000),
            },
            game_config=GameConfig(),
            dm_config=DMConfig(provider="gemini", model="gemini-1.5-flash"),
            characters={
                "fighter": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    personality="Brave and loyal",
                    color="#8B4513",
                    provider="gemini",
                    model="gemini-1.5-flash",
                )
            },
            whisper_queue=[],
            human_active=False,
            controlled_character=None,
            session_number=1,
            session_id="001",
            summarization_in_progress=False,
            selected_module=None,
            character_sheets={},
            agent_secrets={
                "dm": AgentSecrets(),
                "fighter": AgentSecrets(),
            },
            narrative_elements={},
            callback_database=NarrativeElementStore(),
        )

    def test_dm_turn_handles_whisper_tool_call(
        self, basic_game_state: GameState
    ) -> None:
        """Test dm_turn correctly handles whisper tool calls."""
        from agents import dm_turn

        # Mock the DM agent to return a response with a whisper tool call
        mock_response = MagicMock()
        mock_response.tool_calls = [
            {
                "name": "dm_whisper_to_agent",
                "args": {
                    "character_name": "Thorin",
                    "secret_info": "You notice the guard is lying",
                },
                "id": "call_123",
            }
        ]
        mock_response.content = "The guard speaks nervously."

        mock_agent = MagicMock()
        # First call returns tool call, second returns final response
        final_response = MagicMock()
        final_response.tool_calls = None
        final_response.content = "The guard speaks nervously."
        mock_agent.invoke = MagicMock(side_effect=[mock_response, final_response])

        # Create mock streamlit module
        mock_streamlit = MagicMock()
        mock_streamlit.session_state = {}

        with patch("agents.create_dm_agent", return_value=mock_agent):
            with patch.dict("sys.modules", {"streamlit": mock_streamlit}):
                result = dm_turn(basic_game_state)

        # Should have updated agent_secrets
        assert "thorin" in result["agent_secrets"]
        assert len(result["agent_secrets"]["thorin"].whispers) == 1

        whisper = result["agent_secrets"]["thorin"].whispers[0]
        assert whisper.content == "You notice the guard is lying"
        assert whisper.from_agent == "dm"

    def test_dm_turn_preserves_existing_secrets(
        self, basic_game_state: GameState
    ) -> None:
        """Test dm_turn preserves existing whispers when adding new ones."""
        from agents import dm_turn

        # Add an existing whisper
        existing_whisper = create_whisper("dm", "fighter", "Old secret", 1)
        basic_game_state["agent_secrets"]["fighter"] = AgentSecrets(
            whispers=[existing_whisper]
        )

        # Mock tool call for new whisper
        mock_response = MagicMock()
        mock_response.tool_calls = [
            {
                "name": "dm_whisper_to_agent",
                "args": {
                    "character_name": "Thorin",
                    "secret_info": "New secret",
                },
                "id": "call_456",
            }
        ]

        final_response = MagicMock()
        final_response.tool_calls = None
        final_response.content = "The DM narrates."

        mock_agent = MagicMock()
        mock_agent.invoke = MagicMock(side_effect=[mock_response, final_response])

        # Create mock streamlit module
        mock_streamlit = MagicMock()
        mock_streamlit.session_state = {}

        with patch("agents.create_dm_agent", return_value=mock_agent):
            with patch.dict("sys.modules", {"streamlit": mock_streamlit}):
                result = dm_turn(basic_game_state)

        # Should have both old and new whispers
        # Note: "Thorin" -> "thorin" and "fighter" is the agent key
        # The new whisper goes to "thorin" (normalized from character name)
        assert "thorin" in result["agent_secrets"]
        assert len(result["agent_secrets"]["thorin"].whispers) == 1

        # Original fighter secrets preserved
        assert "fighter" in result["agent_secrets"]
        assert len(result["agent_secrets"]["fighter"].whispers) == 1

    def test_dm_turn_logs_whisper_action(self, basic_game_state: GameState) -> None:
        """Test dm_turn logs whisper actions."""
        from agents import dm_turn

        mock_response = MagicMock()
        mock_response.tool_calls = [
            {
                "name": "dm_whisper_to_agent",
                "args": {
                    "character_name": "Fighter",
                    "secret_info": "Secret message",
                },
                "id": "call_789",
            }
        ]

        final_response = MagicMock()
        final_response.tool_calls = None
        final_response.content = "Narrative text."

        mock_agent = MagicMock()
        mock_agent.invoke = MagicMock(side_effect=[mock_response, final_response])

        # Create mock streamlit module
        mock_streamlit = MagicMock()
        mock_streamlit.session_state = {}

        with patch("agents.create_dm_agent", return_value=mock_agent):
            with patch.dict("sys.modules", {"streamlit": mock_streamlit}):
                with patch("agents.logger") as mock_logger:
                    dm_turn(basic_game_state)

                    # Verify logging
                    mock_logger.info.assert_any_call(
                        "DM whispered to agent: %s", "Fighter"
                    )

    def test_dm_turn_uses_log_length_for_turn_number(
        self, basic_game_state: GameState
    ) -> None:
        """Test dm_turn uses ground_truth_log length for whisper turn_created."""
        from agents import dm_turn

        # Set specific log length
        basic_game_state["ground_truth_log"] = [f"Entry {i}" for i in range(7)]

        mock_response = MagicMock()
        mock_response.tool_calls = [
            {
                "name": "dm_whisper_to_agent",
                "args": {
                    "character_name": "Fighter",
                    "secret_info": "Turn-specific secret",
                },
                "id": "call_000",
            }
        ]

        final_response = MagicMock()
        final_response.tool_calls = None
        final_response.content = "Narrative."

        mock_agent = MagicMock()
        mock_agent.invoke = MagicMock(side_effect=[mock_response, final_response])

        # Create mock streamlit module
        mock_streamlit = MagicMock()
        mock_streamlit.session_state = {}

        with patch("agents.create_dm_agent", return_value=mock_agent):
            with patch.dict("sys.modules", {"streamlit": mock_streamlit}):
                result = dm_turn(basic_game_state)

        whisper = result["agent_secrets"]["fighter"].whispers[0]
        assert whisper.turn_created == 7  # Length of log at time of whisper

    def test_dm_turn_returns_agent_secrets_in_state(
        self, basic_game_state: GameState
    ) -> None:
        """Test dm_turn returns agent_secrets in the returned GameState."""
        from agents import dm_turn

        # No tool calls - just verify secrets are passed through
        mock_response = MagicMock()
        mock_response.tool_calls = None
        mock_response.content = "The adventure continues."

        mock_agent = MagicMock()
        mock_agent.invoke = MagicMock(return_value=mock_response)

        # Create mock streamlit module
        mock_streamlit = MagicMock()
        mock_streamlit.session_state = {}

        with patch("agents.create_dm_agent", return_value=mock_agent):
            with patch.dict("sys.modules", {"streamlit": mock_streamlit}):
                result = dm_turn(basic_game_state)

        assert "agent_secrets" in result
        assert isinstance(result["agent_secrets"], dict)


# =============================================================================
# Multiple Whispers Tests
# =============================================================================


class TestMultipleWhispers:
    """Tests for handling multiple whispers in a single turn."""

    @pytest.fixture
    def game_state_with_party(self) -> GameState:
        """Create game state with multiple characters."""
        return GameState(
            ground_truth_log=[],
            turn_queue=["dm", "fighter", "rogue", "wizard"],
            current_turn="dm",
            agent_memories={
                "dm": AgentMemory(),
                "fighter": AgentMemory(),
                "rogue": AgentMemory(),
                "wizard": AgentMemory(),
            },
            game_config=GameConfig(),
            dm_config=DMConfig(),
            characters={
                "fighter": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    personality="Brave",
                    color="#8B4513",
                ),
                "rogue": CharacterConfig(
                    name="Shadowmere",
                    character_class="Rogue",
                    personality="Cunning",
                    color="#4A4A4A",
                ),
                "wizard": CharacterConfig(
                    name="Elara",
                    character_class="Wizard",
                    personality="Wise",
                    color="#4169E1",
                ),
            },
            whisper_queue=[],
            human_active=False,
            controlled_character=None,
            session_number=1,
            session_id="001",
            summarization_in_progress=False,
            selected_module=None,
            character_sheets={},
            agent_secrets={
                "dm": AgentSecrets(),
                "fighter": AgentSecrets(),
                "rogue": AgentSecrets(),
                "wizard": AgentSecrets(),
            },
            narrative_elements={},
            callback_database=NarrativeElementStore(),
        )

    def test_multiple_whispers_to_same_agent(
        self, game_state_with_party: GameState
    ) -> None:
        """Test multiple whispers accumulate for same agent."""
        from agents import _execute_whisper

        agent_secrets = game_state_with_party["agent_secrets"]

        _execute_whisper(
            {"character_name": "Shadowmere", "secret_info": "First secret"},
            agent_secrets,
            turn_number=1,
        )
        _execute_whisper(
            {"character_name": "Shadowmere", "secret_info": "Second secret"},
            agent_secrets,
            turn_number=2,
        )
        _execute_whisper(
            {"character_name": "Shadowmere", "secret_info": "Third secret"},
            agent_secrets,
            turn_number=3,
        )

        assert len(agent_secrets["shadowmere"].whispers) == 3
        assert agent_secrets["shadowmere"].whispers[0].content == "First secret"
        assert agent_secrets["shadowmere"].whispers[1].content == "Second secret"
        assert agent_secrets["shadowmere"].whispers[2].content == "Third secret"

    def test_whispers_to_different_agents(
        self, game_state_with_party: GameState
    ) -> None:
        """Test whispers to different agents are isolated."""
        from agents import _execute_whisper

        agent_secrets = game_state_with_party["agent_secrets"]

        _execute_whisper(
            {"character_name": "Thorin", "secret_info": "Fighter's secret"},
            agent_secrets,
            turn_number=1,
        )
        _execute_whisper(
            {"character_name": "Shadowmere", "secret_info": "Rogue's secret"},
            agent_secrets,
            turn_number=1,
        )
        _execute_whisper(
            {"character_name": "Elara", "secret_info": "Wizard's secret"},
            agent_secrets,
            turn_number=1,
        )

        assert len(agent_secrets["thorin"].whispers) == 1
        assert len(agent_secrets["shadowmere"].whispers) == 1
        assert len(agent_secrets["elara"].whispers) == 1

        assert agent_secrets["thorin"].whispers[0].content == "Fighter's secret"
        assert agent_secrets["shadowmere"].whispers[0].content == "Rogue's secret"
        assert agent_secrets["elara"].whispers[0].content == "Wizard's secret"

    def test_active_whispers_query(self, game_state_with_party: GameState) -> None:
        """Test active_whispers returns only unrevealed whispers."""
        from agents import _execute_whisper

        agent_secrets = game_state_with_party["agent_secrets"]

        # Add some whispers
        _execute_whisper(
            {"character_name": "Rogue", "secret_info": "Active 1"},
            agent_secrets,
            turn_number=1,
        )
        _execute_whisper(
            {"character_name": "Rogue", "secret_info": "Active 2"},
            agent_secrets,
            turn_number=2,
        )

        # Mark one as revealed
        revealed_whisper = Whisper(
            id="revealed",
            from_agent="dm",
            to_agent="rogue",
            content="Revealed secret",
            turn_created=3,
            revealed=True,
            turn_revealed=5,
        )
        current_whispers = agent_secrets["rogue"].whispers.copy()
        current_whispers.append(revealed_whisper)
        agent_secrets["rogue"] = AgentSecrets(whispers=current_whispers)

        # Query active whispers
        active = agent_secrets["rogue"].active_whispers()

        assert len(active) == 2
        assert all(not w.revealed for w in active)


# =============================================================================
# pc_turn Agent Secrets Preservation Tests
# =============================================================================


class TestPcTurnAgentSecrets:
    """Tests for pc_turn preserving agent_secrets in state."""

    @pytest.fixture
    def game_state_with_secrets(self) -> GameState:
        """Create a game state with pre-existing whispers."""
        whisper = create_whisper("dm", "fighter", "Fighter's secret", 1)
        return GameState(
            ground_truth_log=["[DM]: The adventure begins."],
            turn_queue=["dm", "fighter"],
            current_turn="fighter",
            agent_memories={
                "dm": AgentMemory(token_limit=8000),
                "fighter": AgentMemory(token_limit=4000),
            },
            game_config=GameConfig(),
            dm_config=DMConfig(provider="gemini", model="gemini-1.5-flash"),
            characters={
                "fighter": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    personality="Brave and loyal",
                    color="#8B4513",
                    provider="gemini",
                    model="gemini-1.5-flash",
                )
            },
            whisper_queue=[],
            human_active=False,
            controlled_character=None,
            session_number=1,
            session_id="001",
            summarization_in_progress=False,
            selected_module=None,
            character_sheets={},
            agent_secrets={
                "dm": AgentSecrets(),
                "fighter": AgentSecrets(whispers=[whisper]),
            },
            narrative_elements={},
            callback_database=NarrativeElementStore(),
        )

    def test_pc_turn_preserves_agent_secrets(
        self, game_state_with_secrets: GameState
    ) -> None:
        """Test pc_turn returns agent_secrets in state (critical bug fix)."""
        from agents import pc_turn

        # Mock the PC agent
        mock_response = MagicMock()
        mock_response.tool_calls = None
        mock_response.content = "I draw my sword and charge!"

        mock_agent = MagicMock()
        mock_agent.invoke = MagicMock(return_value=mock_response)

        with patch("agents.create_pc_agent", return_value=mock_agent):
            result = pc_turn(game_state_with_secrets, "fighter")

        # Verify agent_secrets is preserved in returned state
        assert "agent_secrets" in result
        assert "fighter" in result["agent_secrets"]
        assert len(result["agent_secrets"]["fighter"].whispers) == 1
        assert result["agent_secrets"]["fighter"].whispers[0].content == "Fighter's secret"

    def test_pc_turn_preserves_all_agent_secrets(
        self, game_state_with_secrets: GameState
    ) -> None:
        """Test pc_turn preserves all agents' secrets, not just the acting agent."""
        from agents import pc_turn

        # Add whisper to DM's secrets too
        dm_whisper = create_whisper("human", "dm", "Human hint", 0)
        game_state_with_secrets["agent_secrets"]["dm"] = AgentSecrets(
            whispers=[dm_whisper]
        )

        mock_response = MagicMock()
        mock_response.tool_calls = None
        mock_response.content = "I stand ready."

        mock_agent = MagicMock()
        mock_agent.invoke = MagicMock(return_value=mock_response)

        with patch("agents.create_pc_agent", return_value=mock_agent):
            result = pc_turn(game_state_with_secrets, "fighter")

        # Both agents' secrets should be preserved
        assert len(result["agent_secrets"]["fighter"].whispers) == 1
        assert len(result["agent_secrets"]["dm"].whispers) == 1
        assert result["agent_secrets"]["dm"].whispers[0].content == "Human hint"
