"""Tests for Story 6.1: Configuration Modal Structure.

This module contains tests for:
- Configure button in sidebar
- Config modal dialog structure
- Tab navigation structure
- Auto-pause on modal open
- Auto-resume on modal close
- Unsaved changes detection
- Modal CSS styling
- Save/Cancel footer buttons
"""

from pathlib import Path
from typing import Any
from unittest.mock import patch


class TestConfigureButton:
    """Tests for Configure button in sidebar (Task 1)."""

    def test_configure_button_renders(self) -> None:
        """Test that Configure button is rendered in sidebar."""
        from app import render_configure_button

        # Mock st.button and st.session_state
        with patch("streamlit.button") as mock_button:
            mock_button.return_value = False
            render_configure_button()
            mock_button.assert_called_once_with(
                "Configure", key="configure_btn", use_container_width=True
            )

    def test_configure_button_click_opens_modal(self) -> None:
        """Test that clicking Configure button opens modal."""
        from app import render_configure_button

        mock_session_state: dict[str, Any] = {"config_modal_open": False}

        with (
            patch("streamlit.button", return_value=True),
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.rerun") as mock_rerun,
        ):
            render_configure_button()
            # Modal should be opened
            assert mock_session_state["config_modal_open"] is True
            mock_rerun.assert_called_once()


class TestConfigModalOpen:
    """Tests for config modal opening behavior (Task 4)."""

    def test_handle_config_modal_open_pauses_game(self) -> None:
        """Test that opening config modal pauses the game (AC #3)."""
        from app import handle_config_modal_open

        mock_session_state: dict[str, Any] = {"is_paused": False}

        with patch("streamlit.session_state", mock_session_state):
            handle_config_modal_open()
            assert mock_session_state["is_paused"] is True
            assert mock_session_state["config_modal_open"] is True

    def test_handle_config_modal_open_stores_pause_state(self) -> None:
        """Test that modal open stores pre-modal pause state."""
        from app import handle_config_modal_open

        mock_session_state: dict[str, Any] = {"is_paused": True}

        with patch("streamlit.session_state", mock_session_state):
            handle_config_modal_open()
            assert mock_session_state["pre_modal_pause_state"] is True
            assert mock_session_state["is_paused"] is True

    def test_handle_config_modal_open_stops_autopilot(self) -> None:
        """Test that opening config modal stops autopilot."""
        from app import handle_config_modal_open

        mock_session_state: dict[str, Any] = {"is_autopilot_running": True, "is_paused": False}

        with patch("streamlit.session_state", mock_session_state):
            handle_config_modal_open()
            assert mock_session_state["is_autopilot_running"] is False

    def test_handle_config_modal_open_takes_config_snapshot(self) -> None:
        """Test that modal open takes snapshot of config values."""
        from app import handle_config_modal_open

        mock_session_state: dict[str, Any] = {"is_paused": False}

        with patch("streamlit.session_state", mock_session_state):
            handle_config_modal_open()
            assert mock_session_state["config_original_values"] is not None
            assert mock_session_state["config_has_changes"] is False


class TestConfigModalClose:
    """Tests for config modal closing behavior (Task 5)."""

    def test_handle_config_modal_close_restores_pause_state(self) -> None:
        """Test that closing config modal restores previous pause state (AC #4)."""
        from app import handle_config_modal_close

        mock_session_state: dict[str, Any] = {
            "config_modal_open": True,
            "pre_modal_pause_state": False,
            "is_paused": True,
            "show_discard_confirmation": False,
            "config_has_changes": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            handle_config_modal_close()
            assert mock_session_state["config_modal_open"] is False
            assert mock_session_state["is_paused"] is False

    def test_handle_config_modal_close_restores_paused_state(self) -> None:
        """Test that modal close restores paused state when game was paused."""
        from app import handle_config_modal_close

        mock_session_state: dict[str, Any] = {
            "config_modal_open": True,
            "pre_modal_pause_state": True,
            "is_paused": True,
            "show_discard_confirmation": False,
            "config_has_changes": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            handle_config_modal_close()
            assert mock_session_state["is_paused"] is True

    def test_handle_config_modal_close_clears_change_tracking(self) -> None:
        """Test that modal close clears change tracking state."""
        from app import handle_config_modal_close

        mock_session_state: dict[str, Any] = {
            "config_modal_open": True,
            "pre_modal_pause_state": False,
            "is_paused": True,
            "show_discard_confirmation": True,
            "config_has_changes": True,
            "config_original_values": {"api_keys": {}},
        }

        with patch("streamlit.session_state", mock_session_state):
            handle_config_modal_close()
            assert mock_session_state["config_has_changes"] is False
            assert mock_session_state["config_original_values"] is None
            assert mock_session_state["show_discard_confirmation"] is False


class TestUnsavedChangesDetection:
    """Tests for unsaved changes detection (Task 6)."""

    def test_has_unsaved_changes_returns_false_when_no_changes(self) -> None:
        """Test that has_unsaved_changes returns False when no changes."""
        from app import has_unsaved_changes

        mock_session_state: dict[str, Any] = {"config_has_changes": False}

        with patch("streamlit.session_state", mock_session_state):
            assert has_unsaved_changes() is False

    def test_has_unsaved_changes_returns_true_when_changes(self) -> None:
        """Test that has_unsaved_changes returns True when changes exist."""
        from app import has_unsaved_changes

        mock_session_state: dict[str, Any] = {"config_has_changes": True}

        with patch("streamlit.session_state", mock_session_state):
            assert has_unsaved_changes() is True

    def test_mark_config_changed_sets_flag(self) -> None:
        """Test that mark_config_changed sets the changes flag."""
        from app import mark_config_changed

        mock_session_state: dict[str, Any] = {"config_has_changes": False}

        with patch("streamlit.session_state", mock_session_state):
            mark_config_changed()
            assert mock_session_state["config_has_changes"] is True


class TestSnapshotConfigValues:
    """Tests for config value snapshotting."""

    def test_snapshot_config_values_returns_dict(self) -> None:
        """Test that snapshot_config_values returns expected structure."""
        from app import snapshot_config_values

        snapshot = snapshot_config_values()
        assert isinstance(snapshot, dict)
        assert "api_keys" in snapshot
        assert "models" in snapshot
        assert "settings" in snapshot


class TestCancelButtonBehavior:
    """Tests for Cancel button behavior (Task 8)."""

    def test_handle_config_cancel_click_shows_confirmation_when_changes(self) -> None:
        """Test that Cancel with unsaved changes shows confirmation (AC #5)."""
        from app import handle_config_cancel_click

        mock_session_state: dict[str, Any] = {
            "config_has_changes": True,
            "show_discard_confirmation": False,
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.rerun"),
        ):
            handle_config_cancel_click()
            assert mock_session_state["show_discard_confirmation"] is True

    def test_handle_config_cancel_click_closes_when_no_changes(self) -> None:
        """Test that Cancel without changes closes modal directly."""
        from app import handle_config_cancel_click

        mock_session_state: dict[str, Any] = {
            "config_has_changes": False,
            "config_modal_open": True,
            "pre_modal_pause_state": False,
            "is_paused": True,
            "show_discard_confirmation": False,
            "config_original_values": {},
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.rerun"),
        ):
            handle_config_cancel_click()
            assert mock_session_state["config_modal_open"] is False


class TestSaveButtonBehavior:
    """Tests for Save button behavior (Task 8)."""

    def test_handle_config_save_click_closes_modal(self) -> None:
        """Test that Save button closes modal."""
        from app import handle_config_save_click

        mock_session_state: dict[str, Any] = {
            "config_modal_open": True,
            "pre_modal_pause_state": False,
            "is_paused": True,
            "show_discard_confirmation": False,
            "config_has_changes": True,
            "config_original_values": {},
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.rerun"),
        ):
            handle_config_save_click()
            assert mock_session_state["config_modal_open"] is False


class TestDiscardConfirmation:
    """Tests for discard confirmation dialog."""

    def test_handle_config_discard_click_closes_modal(self) -> None:
        """Test that Discard button closes modal."""
        from app import handle_config_discard_click

        mock_session_state: dict[str, Any] = {
            "config_modal_open": True,
            "pre_modal_pause_state": False,
            "is_paused": True,
            "show_discard_confirmation": True,
            "config_has_changes": True,
            "config_original_values": {},
        }

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("streamlit.rerun"),
        ):
            handle_config_discard_click()
            assert mock_session_state["config_modal_open"] is False


class TestConfigModalCSS:
    """Tests for config modal CSS styling (Task 7)."""

    def test_css_contains_config_modal_styles(self) -> None:
        """Test that CSS file contains config modal styling (AC #6)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check for dialog theme overrides
        assert '[data-testid="stDialog"]' in css_content

    def test_css_contains_dialog_background(self) -> None:
        """Test that dialog has correct background color (#1A1612)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Dialog should use --bg-primary which is #1A1612
        assert "var(--bg-primary)" in css_content

    def test_css_contains_dialog_border(self) -> None:
        """Test that dialog has border styling (#2D2520)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Dialog should use --bg-secondary for border
        assert "var(--bg-secondary)" in css_content

    def test_css_contains_dialog_border_radius(self) -> None:
        """Test that dialog has 12px border-radius per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "border-radius: 12px" in css_content

    def test_css_contains_tab_styling(self) -> None:
        """Test that CSS contains tab styling for config modal."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Tab styling for active state
        assert '[aria-selected="true"]' in css_content
        assert "var(--accent-warm)" in css_content

    def test_css_contains_configure_button_styling(self) -> None:
        """Test that CSS contains Configure button styling."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Configure button should be styled
        assert "configure_btn" in css_content

    def test_css_contains_modal_header_title_gold_color(self) -> None:
        """Test that modal header title uses gold color (#D4A574)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Should use --color-dm which is #D4A574
        assert "var(--color-dm)" in css_content
        assert "config-modal-title" in css_content

    def test_css_contains_placeholder_styling(self) -> None:
        """Test that CSS contains tab placeholder styling."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "config-tab-placeholder" in css_content

    def test_css_contains_discard_confirmation_styling(self) -> None:
        """Test that CSS contains discard confirmation dialog styling."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "discard-confirmation" in css_content


class TestSessionStateInitialization:
    """Tests for session state initialization with config modal keys."""

    def test_initialize_session_state_includes_config_modal_keys(self) -> None:
        """Test that initialize_session_state includes config modal keys."""
        mock_session_state: dict[str, Any] = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            # Check config modal keys are initialized
            assert "config_modal_open" in mock_session_state
            assert mock_session_state["config_modal_open"] is False
            assert "config_has_changes" in mock_session_state
            assert mock_session_state["config_has_changes"] is False
            assert "config_original_values" in mock_session_state
            assert mock_session_state["config_original_values"] is None
            assert "show_discard_confirmation" in mock_session_state
            assert mock_session_state["show_discard_confirmation"] is False


class TestModeIndicatorPaused:
    """Tests for mode indicator showing Paused state when modal opens."""

    def test_mode_indicator_shows_paused_when_modal_open(self) -> None:
        """Test that mode indicator shows Paused when is_paused=True (AC #3)."""
        from app import render_mode_indicator_html

        html = render_mode_indicator_html(
            ui_mode="watch",
            is_generating=False,
            controlled_character=None,
            characters=None,
            is_paused=True,
        )

        assert "paused" in html.lower()
        assert "Paused" in html


class TestLegacyAliases:
    """Tests for backward compatibility with legacy modal functions."""

    def test_handle_modal_open_calls_config_modal_open(self) -> None:
        """Test that handle_modal_open is an alias for handle_config_modal_open."""
        from app import handle_modal_open

        mock_session_state: dict[str, Any] = {"is_paused": False}

        with patch("streamlit.session_state", mock_session_state):
            handle_modal_open()
            assert mock_session_state["config_modal_open"] is True

    def test_handle_modal_close_calls_config_modal_close(self) -> None:
        """Test that handle_modal_close is an alias for handle_config_modal_close."""
        from app import handle_modal_close

        mock_session_state: dict[str, Any] = {
            "config_modal_open": True,
            "pre_modal_pause_state": False,
            "is_paused": True,
            "show_discard_confirmation": False,
            "config_has_changes": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            handle_modal_close()
            assert mock_session_state["config_modal_open"] is False


class TestConfigModalRendering:
    """Tests for config modal rendering (Task 2, 3)."""

    def test_render_config_modal_creates_three_tabs(self) -> None:
        """Test that render_config_modal creates API Keys, Models, Settings tabs (AC #2)."""
        from app import render_config_modal

        # We verify by testing the function is decorated and callable
        # The actual rendering requires Streamlit runtime context
        # but we can verify the function exists and has the dialog decorator
        assert callable(render_config_modal)
        # st.dialog decorator adds __wrapped__ attribute
        assert hasattr(render_config_modal, "__wrapped__")

    def test_render_discard_confirmation_exists(self) -> None:
        """Test that render_discard_confirmation function exists and is callable."""
        from app import render_discard_confirmation

        assert callable(render_discard_confirmation)


class TestConfigModalEdgeCases:
    """Tests for edge cases in config modal behavior."""

    def test_config_modal_open_when_already_open(self) -> None:
        """Test handling when modal is already open."""
        from app import handle_config_modal_open

        mock_session_state: dict[str, Any] = {
            "config_modal_open": True,
            "is_paused": True,
        }

        with patch("streamlit.session_state", mock_session_state):
            # Should not raise, just set state again
            handle_config_modal_open()
            assert mock_session_state["config_modal_open"] is True

    def test_config_modal_close_when_not_open(self) -> None:
        """Test handling when modal is already closed."""
        from app import handle_config_modal_close

        mock_session_state: dict[str, Any] = {
            "config_modal_open": False,
            "pre_modal_pause_state": False,
            "is_paused": False,
            "show_discard_confirmation": False,
            "config_has_changes": False,
        }

        with patch("streamlit.session_state", mock_session_state):
            # Should not raise, just ensure state is correct
            handle_config_modal_close()
            assert mock_session_state["config_modal_open"] is False

    def test_has_unsaved_changes_when_key_missing(self) -> None:
        """Test has_unsaved_changes returns False when key is missing."""
        from app import has_unsaved_changes

        mock_session_state: dict[str, Any] = {}

        with patch("streamlit.session_state", mock_session_state):
            # Should return False, not raise KeyError
            result = has_unsaved_changes()
            assert result is False
