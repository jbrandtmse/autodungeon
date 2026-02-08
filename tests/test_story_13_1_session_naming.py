"""Tests for Story 13.1: Session Naming.

This test file covers:
- Session name text input stored in session state (AC #1)
- handle_new_session_click() passes name to create_new_session() (AC #2)
- Blank name preserved as empty string / default behavior (AC #3)
- Session name cleared on back navigation (AC #1)
- Session card displays custom name (AC #4)
- Session card displays "Unnamed Adventure" for blank name (AC #4)
- XSS resilience: HTML in session name is escaped in session card (Security)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    pass


# =============================================================================
# Task 5.1: Test session name input stored in session state
# =============================================================================


class TestSessionNameInput:
    """Tests for session name text input in party setup view (Task 1).

    Story 13.2 moved the session name input from module selection to party setup.
    """

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_text_input_rendered_in_party_setup_view(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test that st.text_input is rendered in render_party_setup_view().

        Story 13.1: AC #1 - Text input for naming session.
        Story 13.2: Moved to party setup view.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.button.return_value = False
        mock_st.text_input.return_value = ""
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        # Verify text_input was called with correct parameters
        mock_st.text_input.assert_called_once()
        call_kwargs = mock_st.text_input.call_args
        assert (
            call_kwargs[0][0] == "Adventure Name"
            or call_kwargs[1].get("label") == "Adventure Name"
        )

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_text_input_has_placeholder(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test that text input has the correct placeholder text.

        Story 13.1: AC #1 - Placeholder: "Name your adventure (optional)".
        Story 13.2: Moved to party setup view.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.button.return_value = False
        mock_st.text_input.return_value = ""
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        call_kwargs = mock_st.text_input.call_args
        # Check placeholder is set
        placeholder = call_kwargs[1].get("placeholder", "")
        assert "Name your adventure" in placeholder

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_text_input_has_max_chars(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test that text input has max_chars to prevent overly long names.

        Story 13.1: Edge case - maximum length.
        Story 13.2: Moved to party setup view.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.button.return_value = False
        mock_st.text_input.return_value = ""
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        call_kwargs = mock_st.text_input.call_args
        max_chars = call_kwargs[1].get("max_chars")
        assert max_chars is not None
        assert max_chars == 100

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_session_name_stored_in_session_state(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test that entered session name is stored in st.session_state.

        Story 13.1: AC #1 - Session name stored in session state.
        Story 13.2: Moved to party setup view.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.button.return_value = False
        mock_st.text_input.return_value = "My Custom Adventure"
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        # Session name should be stored in session state
        assert mock_st.session_state["new_session_name"] == "My Custom Adventure"

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_text_input_uses_existing_session_state_value(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test that text input pre-fills from existing session state value.

        Story 13.1: AC #1 - Persistence across reruns.
        Story 13.2: Moved to party setup view.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {"new_session_name": "Previously Entered"}
        mock_st.button.return_value = False
        mock_st.text_input.return_value = "Previously Entered"
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        call_kwargs = mock_st.text_input.call_args
        value = call_kwargs[1].get("value", "")
        assert value == "Previously Entered"


# =============================================================================
# Task 5.2: Test handle_new_session_click() passes name to create_new_session()
# =============================================================================


class TestHandleNewSessionClickSessionName:
    """Tests for session name wiring in handle_new_session_click (Task 2)."""

    def test_passes_name_to_create_new_session(self, tmp_path: Path) -> None:
        """Test handle_new_session_click passes session name to create_new_session.

        Story 13.1: AC #2 - Name passed to create_new_session(name=...).
        """
        mock_session_state: dict = {
            "new_session_name": "Curse of Strahd - Attempt 2",
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path / "campaigns"),
            patch("app.create_new_session", return_value="001") as mock_create,
            patch("app.populate_game_state") as mock_populate,
        ):
            mock_populate.return_value = {
                "characters": {},
                "ground_truth_log": [],
                "agent_memories": {},
                "turn_queue": [],
            }

            from app import handle_new_session_click

            handle_new_session_click()

        # Verify create_new_session was called with name parameter
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args
        assert call_kwargs[1].get("name") == "Curse of Strahd - Attempt 2" or (
            len(call_kwargs[0]) > 0
            and call_kwargs[0][0] == "Curse of Strahd - Attempt 2"
        )

    def test_clears_session_name_after_creation(self, tmp_path: Path) -> None:
        """Test handle_new_session_click clears new_session_name from state after use.

        Story 13.1: AC #2 - Clear session name state after session creation.
        """
        mock_session_state: dict = {
            "new_session_name": "My Adventure",
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path / "campaigns"),
            patch("app.create_new_session", return_value="001"),
            patch("app.populate_game_state") as mock_populate,
        ):
            mock_populate.return_value = {
                "characters": {},
                "ground_truth_log": [],
                "agent_memories": {},
                "turn_queue": [],
            }

            from app import handle_new_session_click

            handle_new_session_click()

        # Session name should be cleared from state
        assert "new_session_name" not in mock_session_state

    def test_strips_whitespace_from_name(self, tmp_path: Path) -> None:
        """Test handle_new_session_click strips whitespace from session name.

        Story 13.1: Edge case - whitespace-only names treated as blank.
        """
        mock_session_state: dict = {
            "new_session_name": "   ",
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path / "campaigns"),
            patch("app.create_new_session", return_value="001") as mock_create,
            patch("app.populate_game_state") as mock_populate,
        ):
            mock_populate.return_value = {
                "characters": {},
                "ground_truth_log": [],
                "agent_memories": {},
                "turn_queue": [],
            }

            from app import handle_new_session_click

            handle_new_session_click()

        # Whitespace-only name should be stripped to empty string
        call_kwargs = mock_create.call_args
        name_arg = call_kwargs[1].get("name", "NOT_FOUND")
        assert name_arg == ""


# =============================================================================
# Task 5.3: Test blank name preserved as empty string (default behavior)
# =============================================================================


class TestBlankNameDefault:
    """Tests for blank name default behavior (Task 3)."""

    def test_empty_name_passes_empty_string(self, tmp_path: Path) -> None:
        """Test that blank name passes empty string to create_new_session.

        Story 13.1: AC #3 - Empty string flows through (not None).
        """
        mock_session_state: dict = {
            "new_session_name": "",
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path / "campaigns"),
            patch("app.create_new_session", return_value="001") as mock_create,
            patch("app.populate_game_state") as mock_populate,
        ):
            mock_populate.return_value = {
                "characters": {},
                "ground_truth_log": [],
                "agent_memories": {},
                "turn_queue": [],
            }

            from app import handle_new_session_click

            handle_new_session_click()

        call_kwargs = mock_create.call_args
        name_arg = call_kwargs[1].get("name")
        assert name_arg == ""
        assert name_arg is not None  # Must be empty string, not None

    def test_missing_session_name_key_defaults_to_empty(self, tmp_path: Path) -> None:
        """Test that missing new_session_name key defaults to empty string.

        Story 13.1: AC #3 - Default behavior when key not in session state.
        """
        mock_session_state: dict = {}  # No new_session_name key

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path / "campaigns"),
            patch("app.create_new_session", return_value="001") as mock_create,
            patch("app.populate_game_state") as mock_populate,
        ):
            mock_populate.return_value = {
                "characters": {},
                "ground_truth_log": [],
                "agent_memories": {},
                "turn_queue": [],
            }

            from app import handle_new_session_click

            handle_new_session_click()

        call_kwargs = mock_create.call_args
        name_arg = call_kwargs[1].get("name")
        assert name_arg == ""


# =============================================================================
# Task 5.4: Test session name cleared on back navigation
# =============================================================================


class TestSessionNameNavigationCleanup:
    """Tests for session name state cleanup on navigation (Task 4)."""

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    @patch("app.handle_new_session_click")
    @patch("app.clear_module_discovery_state")
    def test_back_button_clears_session_name(
        self,
        mock_clear: MagicMock,
        mock_new_session: MagicMock,
        mock_render_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test that back button triggers clear_module_discovery_state which clears session name.

        Story 13.1: AC #1 - Session name cleared on navigation.
        """
        from app import render_module_selection_view

        mock_st.session_state = {"new_session_name": "My Adventure"}
        # Simulate back button pressed
        mock_st.button.return_value = True
        mock_st.text_input.return_value = "My Adventure"

        render_module_selection_view()

        # clear_module_discovery_state should be called
        mock_clear.assert_called()

    def test_clear_module_discovery_state_includes_session_name(self) -> None:
        """Test that clear_module_discovery_state clears new_session_name key.

        Story 13.1: AC #1 - Session name included in cleanup keys.
        """
        mock_session_state: dict = {
            "module_list": ["some module"],
            "new_session_name": "My Adventure",
            "selected_module": "test",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import clear_module_discovery_state

            clear_module_discovery_state()

        assert "new_session_name" not in mock_session_state

    def test_clear_module_discovery_state_no_error_when_key_missing(self) -> None:
        """Test that clear_module_discovery_state does not error when new_session_name absent.

        Story 13.1: Robustness - No KeyError when key doesn't exist.
        """
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import clear_module_discovery_state

            # Should not raise
            clear_module_discovery_state()


# =============================================================================
# Task 5.5: Test session card displays custom name
# =============================================================================


class TestSessionCardDisplaysName:
    """Tests for session card displaying custom name (Task 3/AC #4)."""

    def test_session_card_displays_custom_name(self) -> None:
        """Test that session card shows the user-provided session name.

        Story 13.1: AC #4 - Session card displays custom name.
        """
        from app import render_session_card_html
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name="Curse of Strahd - Attempt 2",
            created_at="2026-02-08T10:00:00Z",
            updated_at="2026-02-08T14:30:00Z",
            character_names=["Theron", "Lyra"],
            turn_count=10,
        )

        html = render_session_card_html(metadata)

        assert "Curse of Strahd - Attempt 2" in html
        assert "Unnamed Adventure" not in html


# =============================================================================
# Task 5.6: Test session card displays "Unnamed Adventure" for blank name
# =============================================================================


class TestSessionCardUnnamedDefault:
    """Tests for session card unnamed default display (Task 3/AC #4)."""

    def test_session_card_shows_unnamed_for_empty_name(self) -> None:
        """Test session card shows 'Unnamed Adventure' when name is empty.

        Story 13.1: AC #3/4 - Default display for blank name.
        """
        from app import render_session_card_html
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name="",
            created_at="2026-02-08T10:00:00Z",
            updated_at="2026-02-08T10:00:00Z",
        )

        html = render_session_card_html(metadata)
        assert "Unnamed Adventure" in html


# =============================================================================
# Task 5.7: Test XSS resilience
# =============================================================================


class TestSessionNameXSSResilience:
    """Tests for XSS/HTML injection resilience in session naming (Security)."""

    def test_session_card_escapes_html_in_name(self) -> None:
        """Test that HTML characters in session name are escaped in card output.

        Story 13.1: Security - XSS prevention in session card display.
        """
        from app import render_session_card_html
        from models import SessionMetadata

        malicious_name = '<script>alert("xss")</script>'
        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name=malicious_name,
            created_at="2026-02-08T10:00:00Z",
            updated_at="2026-02-08T10:00:00Z",
        )

        html = render_session_card_html(metadata)

        # Raw script tag must NOT appear in output
        assert "<script>" not in html
        # Escaped version should be present
        assert "&lt;script&gt;" in html

    def test_session_card_escapes_quotes_in_name(self) -> None:
        """Test that quote characters in session name are escaped.

        Story 13.1: Security - XSS prevention via attribute injection.
        """
        from app import render_session_card_html
        from models import SessionMetadata

        name_with_quotes = 'Adventure "with" quotes & <tags>'
        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name=name_with_quotes,
            created_at="2026-02-08T10:00:00Z",
            updated_at="2026-02-08T10:00:00Z",
        )

        html = render_session_card_html(metadata)

        # Raw angle brackets must not appear unescaped
        assert "<tags>" not in html
        assert "&lt;tags&gt;" in html

    def test_session_card_escapes_img_onerror_in_name(self) -> None:
        """Test that img onerror XSS vector is escaped in session name.

        Story 13.1: Security - Common XSS vector prevention.
        """
        from app import render_session_card_html
        from models import SessionMetadata

        xss_name = '<img src=x onerror="alert(1)">'
        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name=xss_name,
            created_at="2026-02-08T10:00:00Z",
            updated_at="2026-02-08T10:00:00Z",
        )

        html = render_session_card_html(metadata)

        assert "<img" not in html
        assert "&lt;img" in html


# =============================================================================
# Integration: End-to-end session naming flow
# =============================================================================


class TestSessionNamingIntegration:
    """Integration tests for session naming end-to-end flow."""

    def test_named_session_persists_name_in_metadata(self, tmp_path: Path) -> None:
        """Test that a session created with a name has that name in metadata.

        Story 13.1: AC #2 - Name persisted in SessionMetadata.
        """
        from persistence import create_new_session, load_session_metadata

        with patch("persistence.CAMPAIGNS_DIR", tmp_path / "campaigns"):
            session_id = create_new_session(
                name="Epic Dungeon Crawl",
                character_names=["Fighter", "Wizard"],
            )
            metadata = load_session_metadata(session_id)

        assert metadata is not None
        assert metadata.name == "Epic Dungeon Crawl"
        assert metadata.session_id == session_id

    def test_unnamed_session_has_empty_name_in_metadata(self, tmp_path: Path) -> None:
        """Test that a session created without a name has empty string name.

        Story 13.1: AC #3 - Default behavior preserved.
        """
        from persistence import create_new_session, load_session_metadata

        with patch("persistence.CAMPAIGNS_DIR", tmp_path / "campaigns"):
            session_id = create_new_session(character_names=["Fighter"])
            metadata = load_session_metadata(session_id)

        assert metadata is not None
        assert metadata.name == ""

    def test_handle_new_session_click_full_flow_with_name(self, tmp_path: Path) -> None:
        """Test full handle_new_session_click flow preserves session name.

        Story 13.1: AC #2 - Integration test for complete flow.
        """
        from persistence import load_session_metadata

        mock_session_state: dict = {
            "new_session_name": "My Named Adventure",
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path / "campaigns"),
        ):
            from app import handle_new_session_click

            handle_new_session_click()

            # Get session ID that was created
            session_id = mock_session_state.get("current_session_id")
            assert session_id is not None

            metadata = load_session_metadata(session_id)

        assert metadata is not None
        assert metadata.name == "My Named Adventure"
        # Session name should be cleared from state
        assert "new_session_name" not in mock_session_state

    def test_error_recovery_flow_uses_empty_name(self, tmp_path: Path) -> None:
        """Test that error recovery flow (no text input shown) defaults to empty name.

        Story 13.1: Edge case - handle_error_new_session_click delegates
        to handle_new_session_click without new_session_name in state.
        """
        mock_session_state: dict = {
            "error": "Some error",
            "error_retry_count": 1,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path / "campaigns"),
            patch("app.create_new_session", return_value="001") as mock_create_session,
            patch("app.populate_game_state") as mock_populate,
        ):
            mock_populate.return_value = {
                "characters": {},
                "ground_truth_log": [],
                "agent_memories": {},
                "turn_queue": [],
            }

            from app import handle_error_new_session_click

            handle_error_new_session_click()

        call_kwargs = mock_create_session.call_args
        name_arg = call_kwargs[1].get("name")
        assert name_arg == ""
