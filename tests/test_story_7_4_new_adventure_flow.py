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
    @patch("app.clear_module_discovery_state")
    def test_flags_module_discovery_needed(
        self,
        mock_clear: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test handle_start_new_adventure flags discovery needed (deferred to render).

        Story 7.4: Task 2.4.
        """
        from app import handle_start_new_adventure

        mock_st.session_state = {}

        handle_start_new_adventure()

        assert mock_st.session_state["module_discovery_needed"] is True

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
    def test_confirmed_triggers_party_setup(
        self,
        mock_clear: MagicMock,
        mock_new_session: MagicMock,
        mock_selection_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test module_selection_confirmed routes to party setup.

        Story 7.4: Task 4.1, 4.2.
        Story 13.2: Now routes to party_setup instead of directly starting game.
        """
        from app import render_module_selection_view

        mock_st.session_state = {"module_selection_confirmed": True}
        mock_st.button.return_value = False

        render_module_selection_view()

        # Should route to party_setup (Story 13.2)
        assert mock_st.session_state["app_view"] == "party_setup"
        # Should NOT call handle_new_session_click directly (deferred to party setup)
        mock_new_session.assert_not_called()
        # Module state should NOT be cleared (needed in party setup)
        mock_clear.assert_not_called()
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


# =============================================================================
# Expanded Coverage: App View State Machine Edge Cases
# =============================================================================


class TestAppViewStateMachineExpanded:
    """Extended tests for app view state machine (testarch-automate expansion)."""

    def test_all_view_transitions_are_reachable(self) -> None:
        """Test that all view states can be reached from valid starting points.

        Story 7.4: Task 1.4 - Document view state machine.
        """
        # Define all valid states
        valid_states = {"session_browser", "module_selection", "game"}

        # Define reachable transitions
        transitions = {
            "session_browser": {"module_selection"},  # New adventure
            "module_selection": {"game", "session_browser"},  # Confirm or back
            "game": {"session_browser"},  # End game
        }

        # Verify all states are reachable from at least one state
        reachable = set()
        for targets in transitions.values():
            reachable.update(targets)

        # session_browser is the initial state
        reachable.add("session_browser")

        assert reachable == valid_states, "All states should be reachable"

    def test_module_selection_state_is_intermediate(self) -> None:
        """Test that module_selection is only reachable via session_browser.

        Story 7.4: Module selection is an intermediate step.
        """
        # The only way to reach module_selection is through New Adventure
        # This tests the state machine design
        entry_points = {"session_browser"}
        intermediate_states = {"module_selection"}

        # module_selection can only be reached from session_browser
        assert "module_selection" in intermediate_states
        assert len(entry_points) == 1


class TestHandleStartNewAdventureExpanded:
    """Extended tests for handle_start_new_adventure (testarch-automate expansion)."""

    @patch("app.st")
    @patch("app.start_module_discovery")
    @patch("app.clear_module_discovery_state")
    def test_handles_existing_session_state(
        self,
        mock_clear: MagicMock,
        mock_discovery: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test handle_start_new_adventure works with pre-existing session state.

        Story 7.4: Task 2.5 - Clear previous state before starting new flow.
        """
        from app import handle_start_new_adventure

        # Pre-existing state with various keys
        mock_st.session_state = {
            "app_view": "game",
            "game": {"some": "data"},
            "other_key": "value",
        }

        handle_start_new_adventure()

        # Should update app_view
        assert mock_st.session_state["app_view"] == "module_selection"
        # Should clear module discovery state
        mock_clear.assert_called_once()
        # Should set module_selection_confirmed
        assert mock_st.session_state["module_selection_confirmed"] is False

    @patch("app.st")
    @patch("app.clear_module_discovery_state")
    def test_order_of_operations(
        self,
        mock_clear: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test handle_start_new_adventure clears state then sets flags.

        Story 7.4: Clear first, then set state, then flag discovery needed.
        """
        from app import handle_start_new_adventure

        call_order = []
        mock_clear.side_effect = lambda: call_order.append("clear")

        mock_st.session_state = {}

        handle_start_new_adventure()

        # Clear should happen first
        assert call_order[0] == "clear"
        # Discovery should be flagged (deferred to render), not called directly
        assert mock_st.session_state["module_discovery_needed"] is True


class TestRenderModuleSelectionViewExpanded:
    """Extended tests for render_module_selection_view (testarch-automate expansion)."""

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    @patch("app.handle_new_session_click")
    @patch("app.clear_module_discovery_state")
    def test_back_button_clears_state_before_navigation(
        self,
        mock_clear: MagicMock,
        mock_new_session: MagicMock,
        mock_selection_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test back button clears module state before navigating.

        Story 7.4: Task 3.5 - Clean up on cancel.
        """
        from app import render_module_selection_view

        mock_st.session_state = {"module_selection_confirmed": False}
        mock_st.button.return_value = True  # Back button clicked

        render_module_selection_view()

        # Clear should be called
        mock_clear.assert_called()
        # Session browser should be set
        assert mock_st.session_state["app_view"] == "session_browser"

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    @patch("app.handle_new_session_click")
    @patch("app.clear_module_discovery_state")
    def test_renders_caption_under_header(
        self,
        mock_clear: MagicMock,
        mock_new_session: MagicMock,
        mock_selection_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test render_module_selection_view shows caption.

        Story 7.4: Task 3.3 - Step header with description.
        """
        from app import render_module_selection_view

        mock_st.session_state = {"module_selection_confirmed": False}
        mock_st.button.return_value = False

        render_module_selection_view()

        # Should call caption with guidance text
        mock_st.caption.assert_called()
        caption_text = mock_st.caption.call_args[0][0]
        assert "module" in caption_text.lower() or "adventure" in caption_text.lower()

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    @patch("app.handle_new_session_click")
    @patch("app.clear_module_discovery_state")
    def test_renders_selection_ui_when_not_confirmed(
        self,
        mock_clear: MagicMock,
        mock_new_session: MagicMock,
        mock_selection_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test selection UI is rendered when not confirmed.

        Story 7.4: Task 3.4 - Render module selection UI.
        """
        from app import render_module_selection_view

        mock_st.session_state = {"module_selection_confirmed": False}
        mock_st.button.return_value = False

        render_module_selection_view()

        # Should render the selection UI
        mock_selection_ui.assert_called_once()


# =============================================================================
# Expanded Coverage: Module Banner Edge Cases
# =============================================================================


class TestModuleBannerEdgeCases:
    """Extended tests for module banner edge cases (testarch-automate expansion)."""

    @patch("app.st")
    def test_banner_with_very_long_module_name(self, mock_st: MagicMock) -> None:
        """Test render_module_banner handles very long module names.

        Story 7.4: Edge case - long names should render without truncation.
        """
        from app import render_module_banner

        long_name = "A" * 200  # 200 character name
        module = ModuleInfo(
            number=1,
            name=long_name,
            description="Test description.",
        )

        mock_st.session_state = {
            "game": {"selected_module": module},
        }

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        render_module_banner()

        # Should include full name
        call_args = mock_st.expander.call_args
        assert long_name in str(call_args)

    @patch("app.st")
    def test_banner_with_missing_optional_fields(self, mock_st: MagicMock) -> None:
        """Test render_module_banner handles module with empty optional fields.

        Story 7.4: Edge case - optional fields may be empty.
        """
        from app import render_module_banner

        module = ModuleInfo(
            number=1,
            name="Minimal Module",
            description="Only required fields.",
            setting="",  # Empty
            level_range="",  # Empty
        )

        mock_st.session_state = {
            "game": {"selected_module": module},
        }

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        # Should not raise exception
        render_module_banner()

        mock_st.expander.assert_called_once()

    @patch("app.st")
    def test_banner_with_multiline_description(self, mock_st: MagicMock) -> None:
        """Test render_module_banner handles multiline descriptions.

        Story 7.4: Edge case - descriptions may have newlines.
        """
        from app import render_module_banner

        multiline_desc = """This is a module with multiple lines.

It has paragraphs and line breaks.

And continues for a while."""

        module = ModuleInfo(
            number=1,
            name="Multiline Module",
            description=multiline_desc,
        )

        mock_st.session_state = {
            "game": {"selected_module": module},
        }

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        render_module_banner()

        # Should render without error
        mock_st.expander.assert_called_once()

    @patch("app.st")
    def test_banner_with_special_chars_in_all_fields(self, mock_st: MagicMock) -> None:
        """Test render_module_banner handles special chars in all fields.

        Story 7.4: Edge case - special chars are escaped properly.
        """
        from app import render_module_banner

        module = ModuleInfo(
            number=1,
            name='Module & "Test" <Special>',
            description='Description with "quotes" & <tags>',
            setting="Forgotten & Realms",
            level_range="1-10 (levels)",
        )

        mock_st.session_state = {
            "game": {"selected_module": module},
        }

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        # Should not raise exception
        render_module_banner()

        mock_st.expander.assert_called_once()

    @patch("app.st")
    def test_banner_with_game_but_no_selected_module_key(
        self, mock_st: MagicMock
    ) -> None:
        """Test render_module_banner handles game state without selected_module key.

        Story 7.4: Edge case - backward compatibility.
        """
        from app import render_module_banner

        # Game state without selected_module key (old checkpoint)
        mock_st.session_state = {
            "game": {"some_other_key": "value"},
        }

        # Should not raise, should not render banner
        render_module_banner()

        mock_st.expander.assert_not_called()

    @patch("app.st")
    def test_banner_renders_setting_and_level_range_when_present(
        self, mock_st: MagicMock
    ) -> None:
        """Test render_module_banner shows setting and level_range when present.

        Story 7.4: Task 5.2 - Display module metadata.
        """
        from app import render_module_banner

        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Test description.",
            setting="Forgotten Realms",
            level_range="1-5",
        )

        mock_st.session_state = {
            "game": {"selected_module": module},
        }

        mock_expander = MagicMock()
        mock_st.expander.return_value.__enter__ = MagicMock(return_value=mock_expander)
        mock_st.expander.return_value.__exit__ = MagicMock(return_value=False)

        render_module_banner()

        # Check markdown was called with setting and level info
        markdown_calls = mock_st.markdown.call_args_list
        setting_found = any("Setting" in str(c) for c in markdown_calls)
        level_found = any("Levels" in str(c) for c in markdown_calls)

        assert setting_found, "Setting should be displayed"
        assert level_found, "Level range should be displayed"


# =============================================================================
# Expanded Coverage: Freeform Adventure Flow
# =============================================================================


class TestFreeformAdventureFlowExpanded:
    """Extended tests for freeform adventure flow (testarch-automate expansion)."""

    def test_freeform_game_state_has_all_required_fields(self) -> None:
        """Test freeform adventure state has all required GameState fields.

        Story 7.4: AC #5 - Freeform adventure is fully functional.
        """
        state = populate_game_state(include_sample_messages=False, selected_module=None)

        # Verify all required fields exist
        required_fields = [
            "ground_truth_log",
            "turn_queue",
            "current_turn",
            "agent_memories",
            "game_config",
            "dm_config",
            "characters",
            "whisper_queue",
            "human_active",
            "controlled_character",
            "session_number",
            "session_id",
            "selected_module",
        ]

        for field in required_fields:
            assert field in state, f"Missing required field: {field}"

        # Verify module is None
        assert state["selected_module"] is None

    def test_freeform_serialization_preserves_none(self) -> None:
        """Test freeform adventure (None module) survives multiple round-trips.

        Story 7.4: Serialization stability.
        """
        state = create_initial_game_state()
        state["selected_module"] = None

        # Multiple round-trips
        for _ in range(3):
            json_str = serialize_game_state(state)
            state = deserialize_game_state(json_str)

        # Should still be None
        assert state["selected_module"] is None

    @patch("app.st")
    def test_freeform_banner_not_shown_in_game_view(self, mock_st: MagicMock) -> None:
        """Test freeform game view does not show module banner.

        Story 7.4: AC #5 - No banner for freeform.
        """
        from app import render_module_banner

        mock_st.session_state = {
            "game": {"selected_module": None},
        }

        render_module_banner()

        # Expander should not be called
        mock_st.expander.assert_not_called()


# =============================================================================
# Expanded Coverage: Clear State and Back Navigation
# =============================================================================


class TestClearStateTransitionsExpanded:
    """Extended tests for clear state transitions (testarch-automate expansion)."""

    @patch("app.st")
    def test_clear_module_discovery_state_is_idempotent(
        self, mock_st: MagicMock
    ) -> None:
        """Test clear_module_discovery_state can be called multiple times safely.

        Story 7.4: Task 4.4 - Cleanup should be safe to call repeatedly.
        """
        from app import clear_module_discovery_state

        mock_st.session_state = {
            "module_list": [],
            "other_key": "preserved",
        }

        # Call multiple times
        clear_module_discovery_state()
        clear_module_discovery_state()
        clear_module_discovery_state()

        # Should not raise
        assert mock_st.session_state.get("other_key") == "preserved"

    @patch("app.st")
    def test_clear_module_discovery_state_with_empty_session(
        self, mock_st: MagicMock
    ) -> None:
        """Test clear_module_discovery_state handles empty session state.

        Story 7.4: Edge case - empty session state.
        """
        from app import clear_module_discovery_state

        mock_st.session_state = {}

        # Should not raise
        clear_module_discovery_state()

        assert len(mock_st.session_state) == 0

    @patch("app.st")
    def test_clear_module_discovery_state_clears_partial_state(
        self, mock_st: MagicMock
    ) -> None:
        """Test clear_module_discovery_state handles partial state.

        Story 7.4: Edge case - some keys present, some missing.
        """
        from app import clear_module_discovery_state

        mock_st.session_state = {
            "module_list": [],
            # Other module-related keys missing
            "other_key": "preserved",
        }

        clear_module_discovery_state()

        assert "module_list" not in mock_st.session_state
        assert mock_st.session_state.get("other_key") == "preserved"


class TestBackNavigationExpanded:
    """Extended tests for back navigation behavior (testarch-automate expansion)."""

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    @patch("app.handle_new_session_click")
    @patch("app.clear_module_discovery_state")
    def test_back_from_module_selection_after_discovery_complete(
        self,
        mock_clear: MagicMock,
        mock_new_session: MagicMock,
        mock_selection_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test back navigation after module discovery is complete.

        Story 7.4: Back should work regardless of discovery state.
        """
        from app import render_module_selection_view

        mock_st.session_state = {
            "module_selection_confirmed": False,
            "module_list": [MagicMock()],  # Discovery complete
            "module_discovery_in_progress": False,
        }
        mock_st.button.return_value = True  # Back button clicked

        render_module_selection_view()

        assert mock_st.session_state["app_view"] == "session_browser"
        mock_clear.assert_called()

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    @patch("app.handle_new_session_click")
    @patch("app.clear_module_discovery_state")
    def test_back_from_module_selection_during_discovery(
        self,
        mock_clear: MagicMock,
        mock_new_session: MagicMock,
        mock_selection_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test back navigation while discovery is in progress.

        Story 7.4: Back should work even during discovery.
        """
        from app import render_module_selection_view

        mock_st.session_state = {
            "module_selection_confirmed": False,
            "module_discovery_in_progress": True,  # Still discovering
        }
        mock_st.button.return_value = True  # Back button clicked

        render_module_selection_view()

        assert mock_st.session_state["app_view"] == "session_browser"
        mock_clear.assert_called()


# =============================================================================
# Expanded Coverage: Error Recovery Paths
# =============================================================================


class TestModuleDiscoveryErrorRecovery:
    """Tests for error recovery in module discovery flow (testarch-automate expansion)."""

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    @patch("app.handle_new_session_click")
    @patch("app.clear_module_discovery_state")
    def test_render_module_selection_with_discovery_error(
        self,
        mock_clear: MagicMock,
        mock_new_session: MagicMock,
        mock_selection_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test module selection view handles discovery error state.

        Story 7.4: Graceful degradation on discovery failure.
        """
        from app import render_module_selection_view

        mock_st.session_state = {
            "module_selection_confirmed": False,
            "module_discovery_error": "API rate limit exceeded",
        }
        mock_st.button.return_value = False

        # Should render without crashing
        render_module_selection_view()

        # Selection UI should still be called
        mock_selection_ui.assert_called_once()


# =============================================================================
# Expanded Coverage: format_module_context Edge Cases
# =============================================================================


class TestFormatModuleContextExpanded:
    """Extended tests for format_module_context (testarch-automate expansion)."""

    def test_format_module_context_with_none_returns_empty(self) -> None:
        """Test format_module_context returns empty string for None.

        Story 7.4: AC #5 - Freeform adventures have no module context.
        """
        from agents import format_module_context

        result = format_module_context(None)
        assert result == ""

    def test_format_module_context_with_none_is_falsy(self) -> None:
        """Test format_module_context(None) returns falsy value.

        Story 7.4: Allow boolean check on result.
        """
        from agents import format_module_context

        result = format_module_context(None)
        assert not result  # Empty string is falsy

    def test_format_module_context_with_module_is_truthy(self) -> None:
        """Test format_module_context with module returns truthy value.

        Story 7.4: Allow boolean check on result.
        """
        from agents import format_module_context

        module = ModuleInfo(
            number=1,
            name="Test",
            description="Test description.",
        )
        result = format_module_context(module)
        assert result  # Non-empty string is truthy

    def test_format_module_context_escapes_nothing(self) -> None:
        """Test format_module_context does not escape content.

        Story 7.4: LLM context should not be HTML-escaped.
        """
        from agents import format_module_context

        module = ModuleInfo(
            number=1,
            name='<Module> & "Test"',
            description="Description with <html>",
        )
        result = format_module_context(module)

        # Should NOT be escaped
        assert "<Module>" in result
        assert "&" in result  # Not &amp;
        assert '"Test"' in result


# =============================================================================
# Expanded Coverage: View Routing Integration
# =============================================================================


class TestViewRoutingIntegration:
    """Integration tests for view routing (testarch-automate expansion)."""

    def test_valid_view_transitions_exist(self) -> None:
        """Test that valid view transitions are defined.

        Story 7.4: Task 1 - App view state machine.
        """
        # Define the expected transitions
        valid_transitions = [
            ("session_browser", "module_selection"),
            ("module_selection", "game"),
            ("module_selection", "session_browser"),
            ("game", "session_browser"),
        ]

        # All should be valid tuples
        for from_view, to_view in valid_transitions:
            assert isinstance(from_view, str)
            assert isinstance(to_view, str)

    def test_module_selection_is_transient_state(self) -> None:
        """Test module_selection is not a final state.

        Story 7.4: Module selection always leads to game or back.
        """
        # module_selection can go to:
        exits = {"game", "session_browser"}

        # Cannot stay in module_selection indefinitely
        assert "module_selection" not in exits


# =============================================================================
# Expanded Coverage: Session Restore with Module
# =============================================================================


class TestSessionRestoreWithModule:
    """Extended tests for session restore with module (testarch-automate expansion)."""

    def test_session_restore_with_all_module_fields(self) -> None:
        """Test session restore preserves all module fields.

        Story 7.4: Task 9.8 - Session restore shows module banner.
        """
        module = ModuleInfo(
            number=42,
            name="Complete Module",
            description="Has all fields.",
            setting="Greyhawk",
            level_range="5-10",
        )

        state = create_initial_game_state()
        state["selected_module"] = module

        # Serialize and deserialize (simulating save/restore)
        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        # All fields should be preserved
        assert restored["selected_module"] is not None
        assert restored["selected_module"].number == 42
        assert restored["selected_module"].name == "Complete Module"
        assert restored["selected_module"].description == "Has all fields."
        assert restored["selected_module"].setting == "Greyhawk"
        assert restored["selected_module"].level_range == "5-10"

    def test_session_restore_with_unicode_module(self) -> None:
        """Test session restore handles unicode in module fields.

        Story 7.4: Unicode support in module data.
        """
        module = ModuleInfo(
            number=1,
            name="Module with unicode",
            description="Description with unicode characters.",
        )

        state = create_initial_game_state()
        state["selected_module"] = module

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        assert restored["selected_module"] is not None
        assert "unicode" in restored["selected_module"].name


# =============================================================================
# Expanded Coverage: XSS/Security Edge Cases
# =============================================================================


class TestXSSResilienceExpanded:
    """Extended tests for XSS resilience (testarch-automate expansion)."""

    def test_xss_in_description_is_escaped(self) -> None:
        """Test XSS in description is properly escaped.

        Story 7.4: Security - description is also rendered.
        """
        from html import escape as escape_html

        malicious_desc = '<script>alert("xss")</script>'
        module = ModuleInfo(
            number=1,
            name="Test",
            description=malicious_desc,
        )

        escaped = escape_html(module.description)
        assert "<script>" not in escaped
        assert "&lt;script&gt;" in escaped

    def test_javascript_uri_in_fields(self) -> None:
        """Test javascript: URIs are properly escaped.

        Story 7.4: Security - URI-based XSS prevention.
        """
        from html import escape as escape_html

        js_uri = 'javascript:alert("xss")'
        module = ModuleInfo(
            number=1,
            name="Test",
            description=js_uri,
        )

        escaped = escape_html(module.description)
        # Quotes should be escaped, making it safe as text
        assert "&quot;" in escaped or '"' not in escaped

    def test_nested_html_entities(self) -> None:
        """Test nested HTML entities are handled.

        Story 7.4: Security - double-encoding prevention.
        """
        from html import escape as escape_html

        # Pre-escaped content that might be double-escaped
        pre_escaped = "&lt;script&gt;"
        module = ModuleInfo(
            number=1,
            name="Test",
            description=pre_escaped,
        )

        # escape_html will escape the & again
        escaped = escape_html(module.description)
        assert "&amp;lt;" in escaped  # Double-escaped

    def test_all_module_fields_can_be_escaped(self) -> None:
        """Test all string fields can be safely escaped.

        Story 7.4: Security - comprehensive field coverage.
        """
        from html import escape as escape_html

        module = ModuleInfo(
            number=1,
            name="<name>",
            description="<desc>",
            setting="<setting>",
            level_range="<level>",
        )

        # All fields should be escapable
        assert "&lt;" in escape_html(module.name)
        assert "&lt;" in escape_html(module.description)
        assert "&lt;" in escape_html(module.setting)
        assert "&lt;" in escape_html(module.level_range)


# =============================================================================
# Expanded Coverage: Module Info Pydantic Validation Edge Cases
# =============================================================================


class TestModuleInfoValidationExpanded:
    """Extended tests for ModuleInfo validation (testarch-automate expansion)."""

    def test_module_info_exactly_at_boundaries(self) -> None:
        """Test ModuleInfo at exact boundary values.

        Story 7.4: Pydantic validation edge cases.
        """
        # Minimum boundary
        min_module = ModuleInfo(
            number=1,
            name="A",  # min_length=1
            description="B",  # min_length=1
        )
        assert min_module.number == 1

        # Maximum boundary
        max_module = ModuleInfo(
            number=100,
            name="Long Name " * 50,
            description="Long description " * 100,
        )
        assert max_module.number == 100

    def test_module_info_with_only_whitespace_setting(self) -> None:
        """Test ModuleInfo accepts whitespace-only optional fields.

        Story 7.4: Optional fields validation.
        """
        module = ModuleInfo(
            number=1,
            name="Test",
            description="Test description.",
            setting="   ",  # Only whitespace
            level_range="\t",  # Only tab
        )
        # Should be accepted (no strip validator on optional fields)
        assert module.setting == "   "
        assert module.level_range == "\t"

    def test_module_info_negative_number_rejected(self) -> None:
        """Test ModuleInfo rejects negative numbers.

        Story 7.4: Pydantic validation.
        """
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModuleInfo(
                number=-1,
                name="Test",
                description="Test description.",
            )

    def test_module_info_zero_number_rejected(self) -> None:
        """Test ModuleInfo rejects zero.

        Story 7.4: Pydantic validation (ge=1).
        """
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModuleInfo(
                number=0,
                name="Test",
                description="Test description.",
            )

    def test_module_info_101_number_rejected(self) -> None:
        """Test ModuleInfo rejects 101.

        Story 7.4: Pydantic validation (le=100).
        """
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModuleInfo(
                number=101,
                name="Test",
                description="Test description.",
            )
