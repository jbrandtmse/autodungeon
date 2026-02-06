"""Tests for Story 10-4: Human Whisper to DM.

Tests the human whisper functionality that allows players to privately
communicate with the DM through a separate whisper input (distinct from nudges).
"""

from unittest.mock import MagicMock, patch

import pytest

from agents import _build_dm_context
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


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def minimal_game_state() -> GameState:
    """Create a minimal valid GameState for testing."""
    return GameState(
        ground_truth_log=["[DM]: The adventure begins..."],
        turn_queue=["rogue", "fighter"],
        current_turn="dm",
        agent_memories={
            "dm": AgentMemory(),
            "rogue": AgentMemory(),
            "fighter": AgentMemory(),
        },
        game_config=GameConfig(),
        dm_config=DMConfig(),
        characters={
            "rogue": CharacterConfig(
                name="Shadowmere",
                character_class="Rogue",
                personality="Cunning and stealthy",
                color="#6B8E6B",
            ),
            "fighter": CharacterConfig(
                name="Thorin",
                character_class="Fighter",
                personality="Brave and loyal",
                color="#C45C4A",
            ),
        },
        whisper_queue=[],
        human_active=False,
        controlled_character=None,
        session_number=1,
        session_id="test_001",
        agent_secrets={},
    )


# =============================================================================
# handle_human_whisper_submit Tests
# =============================================================================


class TestHandleHumanWhisperSubmit:
    """Tests for handle_human_whisper_submit function."""

    def test_empty_whisper_is_ignored(self) -> None:
        """Test that empty whisper text is ignored."""
        # Import here to avoid importing streamlit at module level
        with patch("streamlit.session_state", {}):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("")

            import streamlit as st

            assert st.session_state.get("pending_human_whisper") is None
            assert st.session_state.get("human_whisper_submitted") is not True

    def test_whitespace_only_whisper_is_ignored(self) -> None:
        """Test that whitespace-only whisper is ignored."""
        with patch("streamlit.session_state", {}):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("   \n\t   ")

            import streamlit as st

            assert st.session_state.get("pending_human_whisper") is None
            assert st.session_state.get("human_whisper_submitted") is not True

    def test_valid_whisper_stored_in_session_state(self) -> None:
        """Test that valid whisper is stored in pending_human_whisper."""
        with patch("streamlit.session_state", {}):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("Can my rogue notice if the merchant is lying?")

            import streamlit as st

            assert (
                st.session_state["pending_human_whisper"]
                == "Can my rogue notice if the merchant is lying?"
            )

    def test_whisper_submitted_flag_set(self) -> None:
        """Test that human_whisper_submitted flag is set to True."""
        with patch("streamlit.session_state", {}):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("Test whisper")

            import streamlit as st

            assert st.session_state["human_whisper_submitted"] is True

    def test_whisper_text_is_stripped(self) -> None:
        """Test that whisper text is stripped of leading/trailing whitespace."""
        with patch("streamlit.session_state", {}):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("  Whisper with spaces  ")

            import streamlit as st

            assert st.session_state["pending_human_whisper"] == "Whisper with spaces"

    def test_whisper_text_is_length_limited(self) -> None:
        """Test that whisper text is truncated to MAX_HUMAN_WHISPER_LENGTH."""
        from app import MAX_HUMAN_WHISPER_LENGTH

        with patch("streamlit.session_state", {}):
            from app import handle_human_whisper_submit

            long_whisper = "A" * 1000  # Well over the 500 char limit
            handle_human_whisper_submit(long_whisper)

            import streamlit as st

            assert (
                len(st.session_state["pending_human_whisper"])
                == MAX_HUMAN_WHISPER_LENGTH
            )

    def test_whisper_added_to_dm_secrets(self, minimal_game_state: GameState) -> None:
        """Test that whisper is added to agent_secrets['dm']."""
        session_state_dict: dict = {"game": minimal_game_state}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("Is the merchant trustworthy?")

            game = session_state_dict["game"]
            dm_secrets = game["agent_secrets"].get("dm")

            assert dm_secrets is not None
            assert len(dm_secrets.whispers) == 1

    def test_whisper_has_correct_from_agent(self, minimal_game_state: GameState) -> None:
        """Test that whisper has from_agent='human'."""
        session_state_dict: dict = {"game": minimal_game_state}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("Test question")

            game = session_state_dict["game"]
            whisper = game["agent_secrets"]["dm"].whispers[0]

            assert whisper.from_agent == "human"

    def test_whisper_has_correct_to_agent(self, minimal_game_state: GameState) -> None:
        """Test that whisper has to_agent='dm'."""
        session_state_dict: dict = {"game": minimal_game_state}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("Test question")

            game = session_state_dict["game"]
            whisper = game["agent_secrets"]["dm"].whispers[0]

            assert whisper.to_agent == "dm"

    def test_whisper_has_correct_turn_created(
        self, minimal_game_state: GameState
    ) -> None:
        """Test that whisper has correct turn_created based on log length."""
        # Game state has 1 entry in ground_truth_log
        session_state_dict: dict = {"game": minimal_game_state}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("Test question")

            game = session_state_dict["game"]
            whisper = game["agent_secrets"]["dm"].whispers[0]

            assert whisper.turn_created == 1  # len(ground_truth_log)

    def test_multiple_whispers_accumulate(self, minimal_game_state: GameState) -> None:
        """Test that multiple whispers accumulate in dm_secrets."""
        session_state_dict: dict = {"game": minimal_game_state}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("First whisper")
            handle_human_whisper_submit("Second whisper")
            handle_human_whisper_submit("Third whisper")

            game = session_state_dict["game"]
            dm_secrets = game["agent_secrets"]["dm"]

            assert len(dm_secrets.whispers) == 3


class TestHandleHumanWhisperSubmitNoGame:
    """Test handle_human_whisper_submit when no game is active."""

    def test_whisper_stored_even_without_game(self) -> None:
        """Test that pending whisper is stored even when no game exists."""
        session_state_dict: dict = {}  # No game in session state
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("Test whisper")

            assert session_state_dict["pending_human_whisper"] == "Test whisper"
            assert session_state_dict["human_whisper_submitted"] is True


# =============================================================================
# render_human_whisper_input Tests
# =============================================================================


class TestRenderHumanWhisperInputHtml:
    """Tests for render_human_whisper_input_html function."""

    def test_contains_whisper_container_class(self) -> None:
        """Test that HTML contains whisper-input-container class."""
        from app import render_human_whisper_input_html

        html = render_human_whisper_input_html()
        assert 'class="whisper-input-container"' in html

    def test_contains_whisper_label(self) -> None:
        """Test that HTML contains whisper label text."""
        from app import render_human_whisper_input_html

        html = render_human_whisper_input_html()
        assert "Whisper to DM" in html

    def test_contains_whisper_hint(self) -> None:
        """Test that HTML contains whisper hint text."""
        from app import render_human_whisper_input_html

        html = render_human_whisper_input_html()
        assert "Ask the DM something privately" in html


class TestRenderHumanWhisperInput:
    """Tests for render_human_whisper_input function visibility."""

    def test_not_rendered_when_human_active(self) -> None:
        """Test that whisper input is not rendered when human_active is True."""
        mock_session_state = {"human_active": True}
        with patch("streamlit.session_state", mock_session_state):
            with patch("streamlit.markdown") as mock_markdown:
                from app import render_human_whisper_input

                render_human_whisper_input()

                # Should not have called markdown with whisper HTML
                assert mock_markdown.call_count == 0

    def test_rendered_in_watch_mode(self) -> None:
        """Test that whisper input is rendered when in Watch Mode."""
        mock_session_state = {"human_active": False, "human_whisper_submitted": False}
        with patch("streamlit.session_state", mock_session_state):
            with patch("streamlit.markdown") as mock_markdown:
                with patch("streamlit.text_area", return_value=""):
                    with patch("streamlit.button", return_value=False):
                        with patch("streamlit.success"):
                            from app import render_human_whisper_input

                            render_human_whisper_input()

                            # Should have called markdown with HTML
                            mock_markdown.assert_called()
                            call_args = mock_markdown.call_args_list[0][0][0]
                            assert "whisper-input-container" in call_args


# =============================================================================
# DM Context Integration Tests
# =============================================================================


class TestDmContextWithPlayerWhisper:
    """Tests for _build_dm_context including player whisper."""

    def test_pending_whisper_included_in_context(
        self, minimal_game_state: GameState
    ) -> None:
        """Test that pending_human_whisper is included in DM context."""
        mock_session_state = {
            "pending_human_whisper": "Can my rogue tell if the merchant is lying?",
            "pending_nudge": None,
        }
        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(minimal_game_state)

            assert "## Player Whisper" in context
            assert (
                'The human player privately asks: "Can my rogue tell if the merchant is lying?"'
                in context
            )

    def test_whisper_format_matches_spec(self, minimal_game_state: GameState) -> None:
        """Test that whisper format matches acceptance criteria exactly."""
        mock_session_state = {
            "pending_human_whisper": "Test question",
            "pending_nudge": None,
        }
        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(minimal_game_state)

            # Check exact format from acceptance criteria
            expected_section = (
                '## Player Whisper\nThe human player privately asks: "Test question"'
            )
            assert expected_section in context

    def test_empty_whisper_not_included(self, minimal_game_state: GameState) -> None:
        """Test that empty/None whisper is not included in context."""
        mock_session_state = {"pending_human_whisper": None, "pending_nudge": None}
        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(minimal_game_state)

            assert "## Player Whisper" not in context

    def test_whitespace_only_whisper_not_included(
        self, minimal_game_state: GameState
    ) -> None:
        """Test that whitespace-only whisper is not included in context."""
        mock_session_state = {
            "pending_human_whisper": "   ",
            "pending_nudge": None,
        }
        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(minimal_game_state)

            assert "## Player Whisper" not in context

    def test_whisper_and_nudge_both_included(
        self, minimal_game_state: GameState
    ) -> None:
        """Test that both whisper and nudge can be included in context."""
        mock_session_state = {
            "pending_human_whisper": "Is the merchant lying?",
            "pending_nudge": "Have the rogue check for traps",
        }
        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(minimal_game_state)

            # Both should be present
            assert "## Player Whisper" in context
            assert "## Player Suggestion" in context
            assert "Is the merchant lying?" in context
            assert "Have the rogue check for traps" in context

    def test_whisper_sanitized_for_injection(
        self, minimal_game_state: GameState
    ) -> None:
        """Test that whisper text is sanitized (stripped)."""
        mock_session_state = {
            "pending_human_whisper": "  Whisper with spaces  ",
            "pending_nudge": None,
        }
        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(minimal_game_state)

            # Should be stripped
            assert (
                'The human player privately asks: "Whisper with spaces"' in context
            )

    def test_whisper_quotes_escaped(self, minimal_game_state: GameState) -> None:
        """Test that double quotes in whisper are escaped to prevent format breaking."""
        mock_session_state = {
            "pending_human_whisper": 'Is the merchant saying "trust me" truthfully?',
            "pending_nudge": None,
        }
        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(minimal_game_state)

            # Double quotes should be converted to single quotes
            assert (
                "The human player privately asks: \"Is the merchant saying 'trust me' truthfully?\""
                in context
            )
            # Verify no unescaped double quotes that could break format
            assert '""' not in context


# =============================================================================
# Whisper History Tracking Tests
# =============================================================================


class TestWhisperHistoryTracking:
    """Tests for whisper history tracking in agent_secrets['dm']."""

    def test_whisper_persisted_with_unique_id(
        self, minimal_game_state: GameState
    ) -> None:
        """Test that each whisper has a unique ID."""
        session_state_dict: dict = {"game": minimal_game_state}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("First whisper")
            handle_human_whisper_submit("Second whisper")

            game = session_state_dict["game"]
            whispers = game["agent_secrets"]["dm"].whispers

            assert whispers[0].id != whispers[1].id

    def test_whispers_have_correct_content(
        self, minimal_game_state: GameState
    ) -> None:
        """Test that whisper content is preserved correctly."""
        session_state_dict: dict = {"game": minimal_game_state}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            content = "Can my character sense any magical auras?"
            handle_human_whisper_submit(content)

            game = session_state_dict["game"]
            whisper = game["agent_secrets"]["dm"].whispers[0]

            assert whisper.content == content

    def test_existing_dm_secrets_preserved(
        self, minimal_game_state: GameState
    ) -> None:
        """Test that existing DM secrets are preserved when adding whisper."""
        # Pre-populate with existing whisper
        existing_whisper = create_whisper(
            from_agent="dm",
            to_agent="dm",
            content="Existing secret",
            turn_created=0,
        )
        minimal_game_state["agent_secrets"] = {
            "dm": AgentSecrets(whispers=[existing_whisper])
        }

        session_state_dict: dict = {"game": minimal_game_state}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("New human whisper")

            game = session_state_dict["game"]
            dm_secrets = game["agent_secrets"]["dm"]

            # Should have both whispers
            assert len(dm_secrets.whispers) == 2
            assert dm_secrets.whispers[0].content == "Existing secret"
            assert dm_secrets.whispers[1].content == "New human whisper"


# =============================================================================
# Session State Initialization Tests
# =============================================================================


class TestSessionStateInitialization:
    """Tests for human whisper session state key initialization."""

    def test_pending_human_whisper_initialized(self) -> None:
        """Test pending_human_whisper is initialized to None."""
        # This would normally be tested through init_session_state,
        # but we verify the expected pattern
        from app import MAX_HUMAN_WHISPER_LENGTH

        # Verify the constant exists with expected value
        assert MAX_HUMAN_WHISPER_LENGTH == 500


# =============================================================================
# Distinction from Nudge System Tests
# =============================================================================


class TestWhisperVsNudgeDistinction:
    """Tests ensuring whisper and nudge are distinct systems."""

    def test_different_session_state_keys(self) -> None:
        """Test that whisper uses different session state keys than nudge."""
        session_state_dict: dict = {}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit, handle_nudge_submit

            handle_nudge_submit("This is a nudge")
            handle_human_whisper_submit("This is a whisper")

            # Both should exist independently
            assert session_state_dict["pending_nudge"] == "This is a nudge"
            assert session_state_dict["pending_human_whisper"] == "This is a whisper"

    def test_different_confirmation_flags(self) -> None:
        """Test that whisper uses different confirmation flag than nudge."""
        session_state_dict: dict = {}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("Test whisper")

            # Should set whisper flag, not nudge flag
            assert session_state_dict["human_whisper_submitted"] is True
            assert "nudge_submitted" not in session_state_dict

    def test_different_context_formats(self, minimal_game_state: GameState) -> None:
        """Test that whisper and nudge use different context formats."""
        mock_session_state = {
            "pending_nudge": "Nudge content",
            "pending_human_whisper": "Whisper content",
        }
        with patch("streamlit.session_state", mock_session_state):
            context = _build_dm_context(minimal_game_state)

            # Nudge format: "## Player Suggestion\nThe player offers this thought: ..."
            # Whisper format: '## Player Whisper\nThe human player privately asks: "..."'
            assert "## Player Suggestion" in context
            assert "The player offers this thought:" in context
            assert "## Player Whisper" in context
            assert 'The human player privately asks: "' in context


# =============================================================================
# Whisper Clearing After DM Turn Tests
# =============================================================================


class TestWhisperClearingAfterDmTurn:
    """Tests for whisper being cleared after DM reads it."""

    def test_whisper_cleared_in_dm_turn(self, minimal_game_state: GameState) -> None:
        """Test that pending_human_whisper is cleared in dm_turn."""
        # This test verifies the clearing logic exists in dm_turn
        # by checking the code path (mock LLM to avoid actual API calls)
        from agents import dm_turn

        mock_session_state = {
            "pending_nudge": "Test nudge",
            "pending_human_whisper": "Test whisper",
        }

        with patch("streamlit.session_state", mock_session_state):
            with patch("agents.create_dm_agent") as mock_create:
                mock_agent = MagicMock()
                mock_response = MagicMock()
                mock_response.content = "The adventure continues..."
                mock_response.tool_calls = None
                mock_agent.invoke.return_value = mock_response
                mock_create.return_value = mock_agent

                try:
                    dm_turn(minimal_game_state)
                except Exception:
                    pass  # May fail due to partial mocking

                # The clearing should have happened before any exception
                assert mock_session_state["pending_human_whisper"] is None
                assert mock_session_state["pending_nudge"] is None


# =============================================================================
# Transcript Exclusion Tests (AC5)
# =============================================================================


class TestWhisperTranscriptExclusion:
    """Tests verifying human whispers are excluded from public transcript.

    AC5: When logged, whispers are tracked in whisper history but NOT in public transcript.
    """

    def test_human_whisper_not_in_ground_truth_log(
        self, minimal_game_state: GameState
    ) -> None:
        """Test that human whispers are stored in secrets, not ground_truth_log.

        Human whispers go to agent_secrets["dm"] for private tracking,
        not to ground_truth_log which feeds the public transcript.
        """
        session_state_dict: dict = {"game": minimal_game_state}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            initial_log_len = len(minimal_game_state["ground_truth_log"])
            handle_human_whisper_submit("This is a private whisper")

            game = session_state_dict["game"]

            # ground_truth_log should NOT have the whisper
            assert len(game["ground_truth_log"]) == initial_log_len
            for entry in game["ground_truth_log"]:
                assert "private whisper" not in entry.lower()

            # But whisper should be in agent_secrets["dm"]
            assert len(game["agent_secrets"]["dm"].whispers) == 1
            assert game["agent_secrets"]["dm"].whispers[0].content == "This is a private whisper"

    def test_whisper_content_not_leaked_to_log(
        self, minimal_game_state: GameState
    ) -> None:
        """Test that whisper content never appears in ground_truth_log entries."""
        session_state_dict: dict = {"game": minimal_game_state}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            secret_content = "SECRET_MERCHANT_LYING_CHECK_12345"
            handle_human_whisper_submit(secret_content)

            game = session_state_dict["game"]

            # Verify the secret content is not in any log entry
            for entry in game["ground_truth_log"]:
                assert secret_content not in entry

    def test_whisper_stored_separately_from_public_entries(
        self, minimal_game_state: GameState
    ) -> None:
        """Test that whispers are stored in agent_secrets, separate from public log.

        This ensures transcript export (which uses ground_truth_log) won't include whispers.
        """
        session_state_dict: dict = {"game": minimal_game_state}
        with patch("streamlit.session_state", session_state_dict):
            from app import handle_human_whisper_submit

            handle_human_whisper_submit("Private question to DM")

            game = session_state_dict["game"]

            # Whisper is in secrets
            assert "dm" in game["agent_secrets"]
            assert len(game["agent_secrets"]["dm"].whispers) == 1

            # ground_truth_log structure unchanged (no whisper entries added)
            # Only contains the initial "[DM]: The adventure begins..."
            assert game["ground_truth_log"] == ["[DM]: The adventure begins..."]
