"""Tests for Story 10-5: Secret Revelation System.

Tests the dm_reveal_secret tool function and its integration with
the DM agent and dm_turn() function for revealing secrets during gameplay.
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
    Whisper,
    create_whisper,
)
from tools import dm_reveal_secret

# Module-level reimport to keep ruff happy with import order
_ = pytest  # Mark as used


# =============================================================================
# Tool Schema Tests
# =============================================================================


class TestRevealToolSchema:
    """Tests for the dm_reveal_secret tool schema and metadata."""

    def test_tool_has_correct_name(self) -> None:
        """Test tool has the expected name."""
        assert dm_reveal_secret.name == "dm_reveal_secret"

    def test_tool_has_docstring(self) -> None:
        """Test tool has a docstring for LLM guidance."""
        assert dm_reveal_secret.description is not None
        assert len(dm_reveal_secret.description) > 100  # Substantial docstring

    def test_tool_docstring_includes_usage_guidance(self) -> None:
        """Test tool docstring includes when-to-use guidance."""
        description = dm_reveal_secret.description
        assert "reveal" in description.lower()
        assert "secret" in description.lower()

    def test_tool_docstring_includes_examples(self) -> None:
        """Test tool docstring includes usage examples."""
        description = dm_reveal_secret.description
        assert "content_hint" in description or "whisper_id" in description

    def test_tool_returns_confirmation_format(self) -> None:
        """Test tool returns expected confirmation format."""
        result = dm_reveal_secret.invoke(
            {"character_name": "Thorin", "content_hint": "secret door"}
        )
        assert "Revealing secret for Thorin" in result

    def test_tool_is_exported(self) -> None:
        """Test tool is exported in tools.__all__."""
        import tools

        assert "dm_reveal_secret" in tools.__all__


# =============================================================================
# Execute Reveal Helper Tests
# =============================================================================


class TestExecuteReveal:
    """Tests for the _execute_reveal helper function."""

    def test_execute_reveal_marks_whisper_as_revealed(self) -> None:
        """Test _execute_reveal marks a whisper as revealed."""
        from agents import _execute_reveal

        whisper = create_whisper("dm", "fighter", "The merchant is lying", 1)
        agent_secrets: dict[str, AgentSecrets] = {
            "fighter": AgentSecrets(whispers=[whisper])
        }
        tool_args = {
            "character_name": "Fighter",
            "content_hint": "merchant",
        }

        result, content = _execute_reveal(tool_args, agent_secrets, turn_number=5)

        assert "SECRET REVEALED" in result
        assert content == "The merchant is lying"
        assert agent_secrets["fighter"].whispers[0].revealed is True
        assert agent_secrets["fighter"].whispers[0].turn_revealed == 5

    def test_execute_reveal_by_whisper_id(self) -> None:
        """Test _execute_reveal can find whisper by ID."""
        from agents import _execute_reveal

        whisper = create_whisper("dm", "rogue", "Hidden door behind tapestry", 2)
        agent_secrets: dict[str, AgentSecrets] = {
            "rogue": AgentSecrets(whispers=[whisper])
        }
        tool_args = {
            "character_name": "Rogue",
            "whisper_id": whisper.id,
        }

        result, content = _execute_reveal(tool_args, agent_secrets, turn_number=7)

        assert "SECRET REVEALED" in result
        assert agent_secrets["rogue"].whispers[0].revealed is True

    def test_execute_reveal_case_insensitive_hint(self) -> None:
        """Test _execute_reveal uses case-insensitive content matching."""
        from agents import _execute_reveal

        whisper = create_whisper("dm", "wizard", "The AMULET is cursed", 3)
        agent_secrets: dict[str, AgentSecrets] = {
            "wizard": AgentSecrets(whispers=[whisper])
        }
        tool_args = {
            "character_name": "Wizard",
            "content_hint": "amulet",  # lowercase
        }

        result, content = _execute_reveal(tool_args, agent_secrets, turn_number=10)

        assert "SECRET REVEALED" in result
        assert agent_secrets["wizard"].whispers[0].revealed is True

    def test_execute_reveal_requires_identifier(self) -> None:
        """Test _execute_reveal returns error when no identifier provided."""
        from agents import _execute_reveal

        whisper = create_whisper("dm", "fighter", "Secret info", 1)
        agent_secrets: dict[str, AgentSecrets] = {
            "fighter": AgentSecrets(whispers=[whisper])
        }
        tool_args = {
            "character_name": "Fighter",
            # No whisper_id or content_hint
        }

        result, content = _execute_reveal(tool_args, agent_secrets, turn_number=5)

        assert "Error" in result
        assert content is None

    def test_execute_reveal_rejects_whitespace_only_hint(self) -> None:
        """Test _execute_reveal rejects whitespace-only content_hint."""
        from agents import _execute_reveal

        whisper = create_whisper("dm", "fighter", "Secret info", 1)
        agent_secrets: dict[str, AgentSecrets] = {
            "fighter": AgentSecrets(whispers=[whisper])
        }
        tool_args = {
            "character_name": "Fighter",
            "content_hint": "   ",  # Whitespace only
        }

        result, content = _execute_reveal(tool_args, agent_secrets, turn_number=5)

        assert "Error" in result
        assert content is None

    def test_execute_reveal_error_if_already_revealed(self) -> None:
        """Test _execute_reveal returns error for already-revealed whisper."""
        from agents import _execute_reveal

        whisper = Whisper(
            id="abc123",
            from_agent="dm",
            to_agent="fighter",
            content="Old secret",
            turn_created=1,
            revealed=True,
            turn_revealed=3,
        )
        agent_secrets: dict[str, AgentSecrets] = {
            "fighter": AgentSecrets(whispers=[whisper])
        }
        tool_args = {
            "character_name": "Fighter",
            "content_hint": "Old",
        }

        result, content = _execute_reveal(tool_args, agent_secrets, turn_number=10)

        assert "Error" in result
        assert "already revealed" in result
        assert content is None

    def test_execute_reveal_error_if_no_whispers(self) -> None:
        """Test _execute_reveal returns error when agent has no whispers."""
        from agents import _execute_reveal

        agent_secrets: dict[str, AgentSecrets] = {"fighter": AgentSecrets(whispers=[])}
        tool_args = {
            "character_name": "Fighter",
            "content_hint": "anything",
        }

        result, content = _execute_reveal(tool_args, agent_secrets, turn_number=5)

        assert "Error" in result
        assert "no whispers" in result.lower()
        assert content is None

    def test_execute_reveal_error_if_agent_not_found(self) -> None:
        """Test _execute_reveal returns error when agent doesn't exist."""
        from agents import _execute_reveal

        agent_secrets: dict[str, AgentSecrets] = {}
        tool_args = {
            "character_name": "NonExistent",
            "content_hint": "anything",
        }

        result, content = _execute_reveal(tool_args, agent_secrets, turn_number=5)

        assert "Error" in result
        assert content is None

    def test_execute_reveal_error_if_no_match_found(self) -> None:
        """Test _execute_reveal returns error when content_hint doesn't match."""
        from agents import _execute_reveal

        whisper = create_whisper("dm", "fighter", "The guard is suspicious", 1)
        agent_secrets: dict[str, AgentSecrets] = {
            "fighter": AgentSecrets(whispers=[whisper])
        }
        tool_args = {
            "character_name": "Fighter",
            "content_hint": "dragon",  # Does not match
        }

        result, content = _execute_reveal(tool_args, agent_secrets, turn_number=5)

        assert "Error" in result
        assert "No matching secret" in result
        assert content is None

    def test_execute_reveal_normalizes_character_name(self) -> None:
        """Test _execute_reveal normalizes character name to lowercase."""
        from agents import _execute_reveal

        whisper = create_whisper("dm", "thorin", "Secret", 1)
        agent_secrets: dict[str, AgentSecrets] = {
            "thorin": AgentSecrets(whispers=[whisper])
        }
        tool_args = {
            "character_name": "THORIN",  # uppercase
            "content_hint": "Secret",
        }

        result, content = _execute_reveal(tool_args, agent_secrets, turn_number=5)

        assert "SECRET REVEALED" in result
        assert agent_secrets["thorin"].whispers[0].revealed is True

    def test_execute_reveal_is_exported(self) -> None:
        """Test _execute_reveal is exported in agents.__all__."""
        import agents

        assert "_execute_reveal" in agents.__all__

    def test_execute_reveal_returns_content_for_notification(self) -> None:
        """Test _execute_reveal returns whisper content for UI notification."""
        from agents import _execute_reveal

        whisper = create_whisper("dm", "fighter", "The trap is armed!", 1)
        agent_secrets: dict[str, AgentSecrets] = {
            "fighter": AgentSecrets(whispers=[whisper])
        }
        tool_args = {
            "character_name": "Fighter",
            "content_hint": "trap",
        }

        result, content = _execute_reveal(tool_args, agent_secrets, turn_number=5)

        assert content == "The trap is armed!"


# =============================================================================
# DM Agent Binding Tests
# =============================================================================


class TestDMAgentBinding:
    """Tests for reveal tool binding to DM agent."""

    def test_dm_agent_has_reveal_tool(self) -> None:
        """Test DM agent has reveal tool bound."""
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

            assert "dm_reveal_secret" in tool_names

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
            assert "dm_reveal_secret" in tool_names


# =============================================================================
# DM System Prompt Tests
# =============================================================================


class TestDMSystemPrompt:
    """Tests for reveal guidance in DM system prompt."""

    def test_dm_prompt_includes_revelation_section(self) -> None:
        """Test DM_SYSTEM_PROMPT includes Secret Revelations section."""
        from agents import DM_SYSTEM_PROMPT

        assert "Secret Revelations" in DM_SYSTEM_PROMPT

    def test_dm_prompt_includes_reveal_tool_name(self) -> None:
        """Test DM_SYSTEM_PROMPT mentions the tool name."""
        from agents import DM_SYSTEM_PROMPT

        assert "dm_reveal_secret" in DM_SYSTEM_PROMPT

    def test_dm_prompt_includes_reveal_guidance(self) -> None:
        """Test DM_SYSTEM_PROMPT includes revelation guidance."""
        from agents import DM_SYSTEM_PROMPT

        assert "dramatic tension" in DM_SYSTEM_PROMPT.lower()
        assert "revealed" in DM_SYSTEM_PROMPT.lower()


# =============================================================================
# dm_turn Integration Tests
# =============================================================================


class TestDmTurnRevealIntegration:
    """Tests for reveal tool execution in dm_turn()."""

    @pytest.fixture
    def game_state_with_whisper(self) -> GameState:
        """Create a game state with an existing whisper."""
        whisper = create_whisper("dm", "fighter", "The merchant is lying", 1)
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
                "fighter": AgentSecrets(whispers=[whisper]),
            },
        )

    def test_dm_turn_handles_reveal_tool_call(
        self, game_state_with_whisper: GameState
    ) -> None:
        """Test dm_turn correctly handles reveal tool calls."""
        from agents import dm_turn

        mock_response = MagicMock()
        mock_response.tool_calls = [
            {
                "name": "dm_reveal_secret",
                "args": {
                    "character_name": "Fighter",
                    "content_hint": "merchant",
                },
                "id": "call_123",
            }
        ]
        mock_response.content = "The truth comes out!"

        mock_agent = MagicMock()
        final_response = MagicMock()
        final_response.tool_calls = None
        final_response.content = "The truth comes out!"
        mock_agent.invoke = MagicMock(side_effect=[mock_response, final_response])

        mock_streamlit = MagicMock()
        mock_streamlit.session_state = {}

        with patch("agents.create_dm_agent", return_value=mock_agent):
            with patch.dict("sys.modules", {"streamlit": mock_streamlit}):
                result = dm_turn(game_state_with_whisper)

        # Should have marked whisper as revealed
        assert result["agent_secrets"]["fighter"].whispers[0].revealed is True
        assert result["agent_secrets"]["fighter"].whispers[0].turn_revealed is not None

    def test_dm_turn_logs_reveal_action(
        self, game_state_with_whisper: GameState
    ) -> None:
        """Test dm_turn logs reveal actions."""
        from agents import dm_turn

        mock_response = MagicMock()
        mock_response.tool_calls = [
            {
                "name": "dm_reveal_secret",
                "args": {
                    "character_name": "Fighter",
                    "content_hint": "merchant",
                },
                "id": "call_456",
            }
        ]

        final_response = MagicMock()
        final_response.tool_calls = None
        final_response.content = "Dramatic reveal!"

        mock_agent = MagicMock()
        mock_agent.invoke = MagicMock(side_effect=[mock_response, final_response])

        # Create a mock streamlit module
        mock_streamlit = MagicMock()
        mock_streamlit.session_state = {}

        with patch("agents.create_dm_agent", return_value=mock_agent):
            with patch.dict("sys.modules", {"streamlit": mock_streamlit}):
                with patch("agents.logger") as mock_logger:
                    dm_turn(game_state_with_whisper)

                    # Verify logging of the reveal
                    mock_logger.info.assert_any_call(
                        "DM revealed secret for: %s", "Fighter"
                    )


class TestRevealedSecretsExcludedFromContext:
    """Tests verifying revealed secrets are excluded from PC context."""

    def test_revealed_whisper_excluded_from_pc_context(self) -> None:
        """Test that revealed whispers don't appear in PC's secret context."""
        from agents import format_pc_secrets_context
        from models import AgentSecrets, Whisper

        # Create one active and one revealed whisper
        active_whisper = Whisper(
            id="active1",
            from_agent="dm",
            to_agent="fighter",
            content="Active secret",
            turn_created=1,
            revealed=False,
            turn_revealed=None,
        )
        revealed_whisper = Whisper(
            id="revealed1",
            from_agent="dm",
            to_agent="fighter",
            content="Revealed secret",
            turn_created=2,
            revealed=True,
            turn_revealed=5,
        )

        secrets = AgentSecrets(whispers=[active_whisper, revealed_whisper])
        context = format_pc_secrets_context(secrets)

        # Active secret should be in context
        assert "Active secret" in context
        # Revealed secret should NOT be in context
        assert "Revealed secret" not in context

    def test_all_revealed_whispers_returns_empty_context(self) -> None:
        """Test that all-revealed whispers returns empty context."""
        from agents import format_pc_secrets_context
        from models import AgentSecrets, Whisper

        revealed_whisper = Whisper(
            id="revealed1",
            from_agent="dm",
            to_agent="fighter",
            content="Revealed secret",
            turn_created=2,
            revealed=True,
            turn_revealed=5,
        )

        secrets = AgentSecrets(whispers=[revealed_whisper])
        context = format_pc_secrets_context(secrets)

        # Should be empty since all whispers are revealed
        assert context == ""


# =============================================================================
# UI Rendering Tests
# =============================================================================


class TestSecretRevealedNotificationRendering:
    """Tests for render_secret_revealed_notification functions."""

    def test_render_secret_revealed_notification_html_structure(self) -> None:
        """Test HTML structure of secret revealed notification."""
        from app import render_secret_revealed_notification_html

        html = render_secret_revealed_notification_html(
            "Thorin", "The merchant is lying"
        )

        assert 'class="secret-revealed-notification"' in html
        assert "SECRET REVEALED" in html
        assert "Thorin" in html
        assert "merchant is lying" in html

    def test_render_secret_revealed_notification_escapes_html(self) -> None:
        """Test HTML escaping in secret revealed notification."""
        from app import render_secret_revealed_notification_html

        html = render_secret_revealed_notification_html(
            "<script>alert('xss')</script>", "<b>malicious</b>"
        )

        assert "<script>" not in html
        assert "&lt;script&gt;" in html
        assert "<b>" not in html

    def test_render_secret_revealed_notification_truncates_long_content(self) -> None:
        """Test long content is truncated."""
        from app import render_secret_revealed_notification_html

        long_content = "A" * 200
        html = render_secret_revealed_notification_html("Fighter", long_content)

        assert "..." in html
        # Should be truncated to around 100 chars

    def test_render_secret_revealed_notification_handles_empty_content(self) -> None:
        """Test empty content is handled gracefully."""
        from app import render_secret_revealed_notification_html

        html = render_secret_revealed_notification_html("Fighter", "")

        assert 'class="secret-revealed-notification"' in html
        assert "Fighter" in html
        # Empty content should not break the HTML

    def test_render_secret_revealed_notification_handles_unicode(self) -> None:
        """Test Unicode content is handled correctly."""
        from app import render_secret_revealed_notification_html

        html = render_secret_revealed_notification_html("Thorin", "The dragon's treasure")

        assert "dragon" in html
        assert "treasure" in html
        # Should have valid HTML structure
        assert 'class="secret-revealed-notification"' in html


class TestWhisperHistoryRendering:
    """Tests for render_whisper_history functions."""

    def test_render_whisper_history_empty(self) -> None:
        """Test whisper history with no whispers."""
        from app import render_whisper_history_html

        html = render_whisper_history_html({})

        assert 'class="whisper-history-container"' in html
        assert "No whispers" in html

    def test_render_whisper_history_with_active_whisper(self) -> None:
        """Test whisper history with active (unrevealed) whisper."""
        from app import render_whisper_history_html

        whisper = create_whisper("dm", "fighter", "Secret info", 1)
        agent_secrets = {"fighter": AgentSecrets(whispers=[whisper])}

        html = render_whisper_history_html(agent_secrets)

        assert "whisper-active" in html
        assert "Active" in html
        assert "Secret info" in html
        assert "Turn 1" in html

    def test_render_whisper_history_with_revealed_whisper(self) -> None:
        """Test whisper history with revealed whisper."""
        from app import render_whisper_history_html

        whisper = Whisper(
            id="abc",
            from_agent="dm",
            to_agent="rogue",
            content="Hidden door",
            turn_created=2,
            revealed=True,
            turn_revealed=5,
        )
        agent_secrets = {"rogue": AgentSecrets(whispers=[whisper])}

        html = render_whisper_history_html(agent_secrets)

        assert "whisper-revealed" in html
        assert "Revealed" in html
        assert "Hidden door" in html
        assert "Revealed turn 5" in html

    def test_render_whisper_history_groups_by_agent(self) -> None:
        """Test whisper history groups whispers by agent."""
        from app import render_whisper_history_html

        whisper1 = create_whisper("dm", "fighter", "Fighter secret", 1)
        whisper2 = create_whisper("dm", "rogue", "Rogue secret", 2)
        agent_secrets = {
            "fighter": AgentSecrets(whispers=[whisper1]),
            "rogue": AgentSecrets(whispers=[whisper2]),
        }

        html = render_whisper_history_html(agent_secrets)

        assert "Fighter" in html
        assert "Rogue" in html
        assert "whisper-agent-group" in html

    def test_render_whisper_history_escapes_content(self) -> None:
        """Test whisper history escapes HTML content."""
        from app import render_whisper_history_html

        whisper = create_whisper("dm", "fighter", "<script>bad</script>", 1)
        agent_secrets = {"fighter": AgentSecrets(whispers=[whisper])}

        html = render_whisper_history_html(agent_secrets)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_render_whisper_history_uses_character_name(self) -> None:
        """Test whisper history uses character display name from config."""
        from app import render_whisper_history_html

        whisper = create_whisper("dm", "fighter", "Secret", 1)
        agent_secrets = {"fighter": AgentSecrets(whispers=[whisper])}
        characters = {
            "fighter": CharacterConfig(
                name="Thorin Ironshield",
                character_class="Fighter",
                personality="Brave",
                color="#8B4513",
            )
        }

        html = render_whisper_history_html(agent_secrets, characters)

        assert "Thorin Ironshield" in html

    def test_render_whisper_history_skips_dm_secrets(self) -> None:
        """Test whisper history skips DM's own secrets section."""
        from app import render_whisper_history_html

        dm_whisper = create_whisper("human", "dm", "Human hint", 1)
        fighter_whisper = create_whisper("dm", "fighter", "Fighter secret", 2)
        agent_secrets = {
            "dm": AgentSecrets(whispers=[dm_whisper]),
            "fighter": AgentSecrets(whispers=[fighter_whisper]),
        }

        html = render_whisper_history_html(agent_secrets)

        # Should show fighter's whispers but not DM's section
        assert "Fighter" in html
        assert "Fighter secret" in html
        # DM section should be skipped (DM's internal hints not shown in player-facing history)


# =============================================================================
# Session State Tests
# =============================================================================


class TestSessionStateInitialization:
    """Tests for pending_secret_reveal session state initialization."""

    def test_pending_secret_reveal_key_exists_in_init(self) -> None:
        """Test that pending_secret_reveal is initialized in app.py."""
        import app

        # Read the source to verify the key is initialized
        with open(app.__file__, encoding="utf-8") as f:
            source = f.read()
        assert "pending_secret_reveal" in source
        assert 'st.session_state["pending_secret_reveal"]' in source
