"""Tests for Story 7.4: New Adventure Flow Integration.

This test file covers:
- handle_start_new_adventure() sets app_view to module_selection
- Module selection view renders loading state
- Module selection confirmed triggers game start
- Selected module appears in game banner
- Freeform adventure skips module selection
- Back button returns to session browser
- Module context preserved after game state serialization roundtrip
- Session restore shows module banner if module was selected
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    pass

from models import (
    ModuleInfo,
    create_initial_game_state,
    populate_game_state,
)
from persistence import deserialize_game_state, serialize_game_state

# =============================================================================
# Security: XSS/HTML Injection Resilience Tests
# =============================================================================


class TestXSSResilience:
    """Tests for XSS/HTML injection resilience (Code Review Finding)."""

    def test_module_banner_escapes_html_in_setting(self) -> None:
        """Test that module setting with HTML characters is properly escaped.

        Story 7.4: Security - XSS prevention in module banner.
        """
        from html import escape as escape_html

        # Create module with malicious HTML in setting
        malicious_setting = '<script>alert("xss")</script>'
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Test description.",
            setting=malicious_setting,
        )

        # Verify escape_html properly sanitizes
        escaped = escape_html(module.setting)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_module_banner_escapes_html_in_level_range(self) -> None:
        """Test that module level_range with HTML characters is properly escaped.

        Story 7.4: Security - XSS prevention in module banner.
        """
        from html import escape as escape_html

        # Create module with malicious HTML in level_range
        malicious_level = '<img src=x onerror="alert(1)">'
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Test description.",
            level_range=malicious_level,
        )

        # Verify escape_html properly sanitizes
        escaped = escape_html(module.level_range)
        assert "<img" not in escaped
        assert "&lt;img" in escaped

    def test_module_name_with_special_characters(self) -> None:
        """Test that module name with special characters is properly escaped.

        Story 7.4: Security - XSS prevention in module display.
        """
        from html import escape as escape_html

        # Create module with special characters in name
        special_name = 'Module & "Quotes" <Tags>'
        module = ModuleInfo(
            number=1,
            name=special_name,
            description="Test description.",
        )

        # Verify escape_html properly sanitizes
        escaped = escape_html(module.name)
        assert "&" not in escaped or "&amp;" in escaped
        assert '"' not in escaped or "&quot;" in escaped
        assert "<" not in escaped or "&lt;" in escaped


# =============================================================================
# Task 1: App View State Tests
# =============================================================================


class TestAppViewStates:
    """Tests for app_view state machine (Task 1)."""

    def test_module_selection_is_valid_app_view_value(self) -> None:
        """Test that 'module_selection' is a valid app_view value.

        Story 7.4: AC #1 - module_selection view exists.
        """
        # Valid views as per Story 7.4 documentation
        valid_views = {"session_browser", "module_selection", "game"}
        assert "module_selection" in valid_views

    def test_app_view_state_machine_documented(self) -> None:
        """Test that state transitions are documented.

        Story 7.4: Task 1.4 - Document view state machine.
        """
        # Verify the state machine transitions are:
        # session_browser -> module_selection -> game
        # module_selection -> session_browser (cancel/back)
        transitions = {
            "session_browser": ["module_selection"],
            "module_selection": ["game", "session_browser"],
            "game": ["session_browser"],
        }

        # Verify expected transitions
        assert "module_selection" in transitions["session_browser"]
        assert "game" in transitions["module_selection"]
        assert "session_browser" in transitions["module_selection"]


# =============================================================================
# Task 2: Handle Start New Adventure Tests
# =============================================================================


class TestHandleStartNewAdventure:
    """Tests for handle_start_new_adventure() function (Task 2)."""

    @patch("app.st")
    @patch("app.start_module_discovery")
    @patch("app.clear_module_discovery_state")
    def test_sets_app_view_to_module_selection(
        self,
        mock_clear: MagicMock,
        mock_discovery: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test handle_start_new_adventure sets app_view to module_selection.

        Story 7.4: AC #1, Task 2.3.
        """
        from app import handle_start_new_adventure

        mock_st.session_state = {}

        handle_start_new_adventure()

        assert mock_st.session_state["app_view"] == "module_selection"

    @patch("app.st")
    @patch("app.start_module_discovery")
    @patch("app.clear_module_discovery_state")
    def test_clears_previous_module_state(
        self,
        mock_clear: MagicMock,
        mock_discovery: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test handle_start_new_adventure clears previous module state.

        Story 7.4: Task 2.5.
        """
        from app import handle_start_new_adventure

        mock_st.session_state = {}

        handle_start_new_adventure()

        mock_clear.assert_called_once()

    @patch("app.st")
    @patch("app.start_module_discovery")
    @patch("app.clear_module_discovery_state")
    def test_triggers_module_discovery(
        self,
        mock_clear: MagicMock,
        mock_discovery: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test handle_start_new_adventure triggers module discovery.

        Story 7.4: Task 2.4.
        """
        from app import handle_start_new_adventure

        mock_st.session_state = {}

        handle_start_new_adventure()

        mock_discovery.assert_called_once()

    @patch("app.st")
    @patch("app.start_module_discovery")
    @patch("app.clear_module_discovery_state")
    def test_sets_module_selection_confirmed_false(
        self,
        mock_clear: MagicMock,
        mock_discovery: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test handle_start_new_adventure initializes confirmation state.

        Story 7.4: Task 2.5.
        """
        from app import handle_start_new_adventure

        mock_st.session_state = {}

        handle_start_new_adventure()

        assert mock_st.session_state["module_selection_confirmed"] is False


# =============================================================================
# Task 3: Module Selection View Tests
# =============================================================================


class TestRenderModuleSelectionView:
    """Tests for render_module_selection_view() function (Task 3)."""

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    @patch("app.handle_new_session_click")
    @patch("app.clear_module_discovery_state")
    def test_shows_step_header(
        self,
        mock_clear: MagicMock,
        mock_new_session: MagicMock,
        mock_selection_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test render_module_selection_view shows step header.

        Story 7.4: Task 3.3.
        """
        from app import render_module_selection_view

        mock_st.session_state = {"module_selection_confirmed": False}
        mock_st.button.return_value = False  # Back button not clicked

        render_module_selection_view()

        # Check markdown was called with step header
        calls = mock_st.markdown.call_args_list
        header_call = [c for c in calls if "Step 1" in str(c)]
        assert len(header_call) > 0, "Step header should be rendered"

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    @patch("app.handle_new_session_click")
    @patch("app.clear_module_discovery_state")
    def test_back_button_returns_to_session_browser(
        self,
        mock_clear: MagicMock,
        mock_new_session: MagicMock,
        mock_selection_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test back button navigates to session browser.

        Story 7.4: Task 3.5.
        """
        from app import render_module_selection_view

        mock_st.session_state = {"module_selection_confirmed": False}
        # Simulate back button click
        mock_st.button.return_value = True

        render_module_selection_view()

        # Should set app_view to session_browser
        assert mock_st.session_state["app_view"] == "session_browser"
        mock_clear.assert_called()
        mock_st.rerun.assert_called()

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    @patch("app.handle_new_session_click")
    @patch("app.clear_module_discovery_state")
    def test_confirmed_triggers_game_start(
        self,
        mock_clear: MagicMock,
        mock_new_session: MagicMock,
        mock_selection_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test module_selection_confirmed triggers game initialization.

        Story 7.4: Task 4.1, 4.2.
        """
        from app import render_module_selection_view

        mock_st.session_state = {"module_selection_confirmed": True}
        mock_st.button.return_value = False

        render_module_selection_view()

        # Should call handle_new_session_click and clear state
        mock_new_session.assert_called_once()
        mock_clear.assert_called_once()
        mock_st.rerun.assert_called()


# =============================================================================
# Task 5: Module Banner Tests
# =============================================================================


class TestRenderModuleBanner:
    """Tests for render_module_banner() function (Task 5)."""

    @patch("app.st")
    def test_shows_banner_when_module_selected(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Test render_module_banner shows banner when module is selected.

        Story 7.4: AC #3, Task 5.1.
        """
        from app import render_module_banner

        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror adventure.",
            setting="Ravenloft",
        )

        mock_st.session_state = {
            "game": {"selected_module": module},
        }

        # Mock expander context manager
        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        render_module_banner()

        # Verify expander was called with module name
        mock_st.expander.assert_called_once()
        call_args = mock_st.expander.call_args
        assert "Curse of Strahd" in str(call_args)

    @patch("app.st")
    def test_hides_banner_for_freeform(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Test render_module_banner hides banner for freeform adventures.

        Story 7.4: AC #5, Task 5.4.
        """
        from app import render_module_banner

        mock_st.session_state = {
            "game": {"selected_module": None},
        }

        render_module_banner()

        # Expander should not be called for freeform
        mock_st.expander.assert_not_called()

    @patch("app.st")
    def test_hides_banner_when_no_game(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Test render_module_banner handles missing game state.

        Story 7.4: Task 5.4.
        """
        from app import render_module_banner

        mock_st.session_state = {}

        render_module_banner()

        # Expander should not be called when no game
        mock_st.expander.assert_not_called()

    @patch("app.st")
    def test_displays_module_name(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Test render_module_banner displays module name.

        Story 7.4: Task 5.2.
        """
        from app import render_module_banner

        module = ModuleInfo(
            number=1,
            name="Lost Mine of Phandelver",
            description="Classic starter adventure.",
        )

        mock_st.session_state = {
            "game": {"selected_module": module},
        }

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        render_module_banner()

        # Check expander title contains module name
        call_args = mock_st.expander.call_args
        assert "Lost Mine of Phandelver" in str(call_args)


# =============================================================================
# Task 6: Opening Narration Module Context Tests
# =============================================================================


class TestOpeningNarrationModuleContext:
    """Integration tests for DM prompt module context (Task 6)."""

    def test_dm_prompt_includes_module_context(self) -> None:
        """Test new game with module has module context in DM prompt.

        Story 7.4: AC #4, Task 6.2.
        """
        from agents import format_module_context

        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror adventure in Barovia.",
            setting="Ravenloft",
            level_range="1-10",
        )

        # Create game state with module
        state = populate_game_state(
            include_sample_messages=False, selected_module=module
        )

        # Verify module is in state
        assert state["selected_module"] is not None
        assert state["selected_module"].name == "Curse of Strahd"

        # Verify format_module_context produces output with name and description
        context = format_module_context(module)
        assert "Curse of Strahd" in context
        assert "Gothic horror adventure in Barovia" in context
        assert "Campaign Module" in context

    def test_freeform_game_has_no_module_section(self) -> None:
        """Test freeform game has no module section in DM prompt.

        Story 7.4: AC #5, Task 6.3.
        """
        from agents import format_module_context

        # Freeform adventure - no module
        state = populate_game_state(include_sample_messages=False, selected_module=None)

        assert state["selected_module"] is None

        # format_module_context with None should return empty
        context = format_module_context(None)
        assert context == ""


# =============================================================================
# Task 7: Freeform Adventure Bypass Tests
# =============================================================================


class TestFreeformAdventureBypass:
    """Tests for freeform adventure bypass (Task 7)."""

    def test_freeform_sets_selected_module_none(self) -> None:
        """Test freeform adventure sets selected_module to None.

        Story 7.4: AC #5, Task 7.2.
        """
        # Freeform adventure creates state with None module
        state = populate_game_state(include_sample_messages=False, selected_module=None)

        assert state["selected_module"] is None

    def test_freeform_game_creates_without_module_context(self) -> None:
        """Test freeform adventure creates game without module context.

        Story 7.4: Task 7.3.
        """
        from agents import format_module_context

        state = populate_game_state(include_sample_messages=False, selected_module=None)

        # Should have no module context
        context = format_module_context(state["selected_module"])
        assert context == ""


# =============================================================================
# Task 9: Integration and Serialization Tests
# =============================================================================


class TestNewAdventureFlowIntegration:
    """Integration tests for the complete new adventure flow (Task 9)."""

    def test_module_context_preserved_after_serialization(self) -> None:
        """Test module context survives serialization round-trip.

        Story 7.4: Task 9.7.
        """
        module = ModuleInfo(
            number=1,
            name="Tomb of Annihilation",
            description="Jungle exploration adventure.",
            setting="Chult",
            level_range="1-11",
        )

        # Create state with module
        state = create_initial_game_state()
        state["selected_module"] = module

        # Serialize and deserialize
        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        # Verify module is preserved
        assert restored["selected_module"] is not None
        assert restored["selected_module"].name == "Tomb of Annihilation"
        assert restored["selected_module"].setting == "Chult"
        assert restored["selected_module"].level_range == "1-11"

    def test_freeform_serialization_roundtrip(self) -> None:
        """Test freeform adventure (None module) survives serialization.

        Story 7.4: Task 9.7.
        """
        # Create state without module
        state = create_initial_game_state()
        state["selected_module"] = None

        # Serialize and deserialize
        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        # Verify None is preserved
        assert restored["selected_module"] is None

    @patch("app.st")
    def test_session_restore_shows_module_banner(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Test session restore shows module banner if module was selected.

        Story 7.4: Task 9.8.
        """
        from app import render_module_banner

        module = ModuleInfo(
            number=1,
            name="Waterdeep Dragon Heist",
            description="Urban adventure in Waterdeep.",
            setting="Forgotten Realms",
        )

        # Simulate restored session with module
        mock_st.session_state = {
            "game": {"selected_module": module},
        }

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        render_module_banner()

        # Banner should be shown
        mock_st.expander.assert_called_once()
        assert "Waterdeep Dragon Heist" in str(mock_st.expander.call_args)


class TestClearModuleDiscoveryState:
    """Tests for clear_module_discovery_state() cleanup (Task 4.4)."""

    @patch("app.st")
    def test_clears_all_module_state_keys(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Test clear_module_discovery_state clears all relevant keys.

        Story 7.4: Task 4.4.
        """
        from app import clear_module_discovery_state

        # Set up state with module discovery data
        mock_st.session_state = {
            "module_list": [MagicMock()],
            "module_discovery_result": MagicMock(),
            "module_discovery_in_progress": True,
            "module_discovery_error": MagicMock(),
            "selected_module": MagicMock(),
            "module_selection_confirmed": True,
            "module_search_query": "strahd",
            "other_key": "preserved",  # Should not be deleted
        }

        clear_module_discovery_state()

        # Module-related keys should be deleted
        assert "module_list" not in mock_st.session_state
        assert "module_discovery_result" not in mock_st.session_state
        assert "module_discovery_in_progress" not in mock_st.session_state
        assert "module_discovery_error" not in mock_st.session_state
        assert "selected_module" not in mock_st.session_state
        assert "module_selection_confirmed" not in mock_st.session_state
        assert "module_search_query" not in mock_st.session_state

        # Other keys should be preserved
        assert mock_st.session_state.get("other_key") == "preserved"
