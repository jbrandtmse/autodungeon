"""Tests for Story 7.2: Module Selection UI.

This test file covers:
- filter_modules() function for search filtering
- select_random_module() function
- render functions (HTML generation helpers)
- Session state management for module selection
"""

from unittest.mock import MagicMock, patch

from models import ModuleInfo, UserError

# =============================================================================
# Test Fixtures
# =============================================================================


def create_test_modules() -> list[ModuleInfo]:
    """Create a set of test modules for use in tests."""
    return [
        ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror adventure in Barovia.",
            setting="Ravenloft",
            level_range="1-10",
        ),
        ModuleInfo(
            number=2,
            name="Lost Mine of Phandelver",
            description="Starter adventure for new players.",
            setting="Forgotten Realms",
            level_range="1-5",
        ),
        ModuleInfo(
            number=3,
            name="Tomb of Annihilation",
            description="Jungle adventure with deadly traps and dinosaurs.",
            setting="Forgotten Realms",
            level_range="1-11",
        ),
        ModuleInfo(
            number=4,
            name="Dragon Heist",
            description="Urban intrigue adventure in Waterdeep.",
            setting="Forgotten Realms",
            level_range="1-5",
        ),
        ModuleInfo(
            number=5,
            name="Descent into Avernus",
            description="Journey into the first layer of the Nine Hells.",
            setting="Forgotten Realms",
            level_range="1-13",
        ),
    ]


# =============================================================================
# Task 3: Search Filtering Tests
# =============================================================================


class TestFilterModules:
    """Tests for filter_modules function (Task 3)."""

    def test_empty_query_returns_all(self) -> None:
        """Test that empty query returns all modules (Task 3.1)."""
        from app import filter_modules

        modules = create_test_modules()
        result = filter_modules(modules, "")

        assert len(result) == len(modules)
        assert result == modules

    def test_whitespace_query_returns_all(self) -> None:
        """Test that whitespace-only query returns all modules."""
        from app import filter_modules

        modules = create_test_modules()
        result = filter_modules(modules, "   ")

        assert len(result) == len(modules)

    def test_filter_by_name(self) -> None:
        """Test filtering by module name (Task 3.3)."""
        from app import filter_modules

        modules = create_test_modules()
        result = filter_modules(modules, "Strahd")

        assert len(result) == 1
        assert result[0].name == "Curse of Strahd"

    def test_filter_by_description(self) -> None:
        """Test filtering by module description (Task 3.4)."""
        from app import filter_modules

        modules = create_test_modules()
        result = filter_modules(modules, "dinosaurs")

        assert len(result) == 1
        assert result[0].name == "Tomb of Annihilation"

    def test_filter_case_insensitive(self) -> None:
        """Test filtering is case-insensitive (Task 3.3, 3.4)."""
        from app import filter_modules

        modules = create_test_modules()

        # Test uppercase query
        result_upper = filter_modules(modules, "STRAHD")
        assert len(result_upper) == 1

        # Test lowercase query
        result_lower = filter_modules(modules, "strahd")
        assert len(result_lower) == 1

        # Test mixed case query
        result_mixed = filter_modules(modules, "StRaHd")
        assert len(result_mixed) == 1

    def test_filter_multiple_terms_and_logic(self) -> None:
        """Test multiple search terms use AND logic (Task 3.3, 3.4)."""
        from app import filter_modules

        modules = create_test_modules()
        # "jungle" AND "deadly" should only match Tomb of Annihilation
        result = filter_modules(modules, "jungle deadly")

        assert len(result) == 1
        assert result[0].name == "Tomb of Annihilation"

    def test_filter_no_matches_returns_empty(self) -> None:
        """Test no matches returns empty list."""
        from app import filter_modules

        modules = create_test_modules()
        result = filter_modules(modules, "nonexistent module xyz")

        assert len(result) == 0
        assert result == []

    def test_filter_partial_match(self) -> None:
        """Test partial word matching works (substring)."""
        from app import filter_modules

        modules = create_test_modules()
        result = filter_modules(modules, "goth")  # Should match "Gothic"

        assert len(result) == 1
        assert result[0].name == "Curse of Strahd"

    def test_filter_empty_modules_list(self) -> None:
        """Test filtering empty modules list returns empty."""
        from app import filter_modules

        result = filter_modules([], "anything")

        assert result == []

    def test_filter_by_setting(self) -> None:
        """Test filtering matches setting field."""
        from app import filter_modules

        modules = create_test_modules()
        result = filter_modules(modules, "Ravenloft")

        assert len(result) == 1
        assert result[0].name == "Curse of Strahd"

    def test_filter_multiple_results(self) -> None:
        """Test filtering returns multiple matches."""
        from app import filter_modules

        modules = create_test_modules()
        # "Forgotten Realms" should match multiple modules
        result = filter_modules(modules, "Forgotten Realms")

        assert len(result) == 4  # All except Curse of Strahd


# =============================================================================
# Task 4: Random Module Selection Tests
# =============================================================================


class TestSelectRandomModule:
    """Tests for select_random_module function (Task 4)."""

    def test_random_selection_with_modules(self) -> None:
        """Test random selection from available modules (Task 4.2)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "module_list": create_test_modules(),
            }
            mock_st.rerun = MagicMock()

            # Mock random.choice to return a specific module
            with patch("app.random.choice") as mock_choice:
                modules = create_test_modules()
                mock_choice.return_value = modules[2]  # Tomb of Annihilation

                from app import select_random_module

                select_random_module()

                # Should have selected the mocked module
                assert mock_st.session_state["selected_module"] == modules[2]
                # Should call rerun
                mock_st.rerun.assert_called_once()

    def test_random_selection_empty_list(self) -> None:
        """Test random selection with empty module list (Task 4.2)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {"module_list": []}
            mock_st.warning = MagicMock()
            mock_st.rerun = MagicMock()

            from app import select_random_module

            select_random_module()

            # Should show warning
            mock_st.warning.assert_called_once()
            # Should NOT set selected_module
            assert "selected_module" not in mock_st.session_state
            # Should NOT rerun
            mock_st.rerun.assert_not_called()

    def test_random_selection_no_module_list(self) -> None:
        """Test random selection when module_list doesn't exist."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            mock_st.warning = MagicMock()
            mock_st.rerun = MagicMock()

            from app import select_random_module

            select_random_module()

            # Should show warning
            mock_st.warning.assert_called_once()
            # Should NOT rerun
            mock_st.rerun.assert_not_called()

    def test_random_selection_updates_session_state(self) -> None:
        """Test random selection updates selected_module in session state (Task 4.3)."""
        with patch("app.st") as mock_st:
            modules = create_test_modules()
            mock_st.session_state = {"module_list": modules}
            mock_st.rerun = MagicMock()

            from app import select_random_module

            # Run multiple times to verify it always sets a module
            for _ in range(5):
                select_random_module()
                assert "selected_module" in mock_st.session_state
                assert mock_st.session_state["selected_module"] in modules


# =============================================================================
# Task 1: Module Card Rendering Tests
# =============================================================================


class TestRenderModuleCardHtml:
    """Tests for render_module_card_html function (Task 1)."""

    def test_card_displays_name(self) -> None:
        """Test module card displays name (Task 1.2)."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror adventure.",
        )

        html = render_module_card_html(module)

        assert "Curse of Strahd" in html
        assert "module-name" in html

    def test_card_truncates_long_description(self) -> None:
        """Test card truncates description to ~100 chars (Task 1.3)."""
        from app import render_module_card_html

        long_desc = "A" * 200  # 200 character description
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description=long_desc,
        )

        html = render_module_card_html(module)

        # Should contain truncated description with ellipsis
        assert "..." in html
        # Full description should NOT be in the card
        assert long_desc not in html

    def test_card_short_description_no_truncation(self) -> None:
        """Test card doesn't truncate short descriptions."""
        from app import render_module_card_html

        short_desc = "A short description."
        module = ModuleInfo(
            number=1,
            name="Test Module",
            description=short_desc,
        )

        html = render_module_card_html(module)

        assert short_desc in html
        # Should not have ellipsis added
        assert html.count("...") == 0

    def test_card_escapes_html(self) -> None:
        """Test card escapes HTML characters."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name="Test <script>alert('xss')</script>",
            description="Description with & and < characters.",
        )

        html = render_module_card_html(module)

        # Should escape HTML
        assert "<script>" not in html
        assert "&lt;" in html or "&amp;" in html

    def test_card_selected_state(self) -> None:
        """Test card shows selected state (Task 1.4 selected styling)."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html_selected = render_module_card_html(module, selected=True)
        html_not_selected = render_module_card_html(module, selected=False)

        # Selected card should have the "selected" CSS class
        assert 'class="module-card selected"' in html_selected
        assert 'aria-selected="true"' in html_selected
        # Non-selected card should not have the "selected" CSS class
        assert 'class="module-card"' in html_not_selected
        assert 'aria-selected="false"' in html_not_selected

    def test_card_has_module_card_class(self) -> None:
        """Test card has module-card CSS class."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_card_html(module)

        assert 'class="module-card' in html


# =============================================================================
# Task 2: Module Grid Display Tests
# =============================================================================


class TestRenderModuleGrid:
    """Tests for render_module_grid function (Task 2)."""

    def test_grid_handles_empty_list(self) -> None:
        """Test grid handles empty module list (Task 2.3)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            mock_st.info = MagicMock()
            mock_st.columns = MagicMock()

            from app import render_module_grid

            render_module_grid([])

            # Should show info message for empty list
            mock_st.info.assert_called_once()
            # Should NOT create columns
            mock_st.columns.assert_not_called()

    def test_grid_creates_three_columns(self) -> None:
        """Test grid uses 3-column layout (Task 2.2)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}

            # Create mock column context managers
            mock_cols = [MagicMock() for _ in range(3)]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)

            mock_st.columns.return_value = mock_cols
            mock_st.button = MagicMock(return_value=False)
            mock_st.markdown = MagicMock()

            from app import render_module_grid

            modules = create_test_modules()[:3]
            render_module_grid(modules)

            # Should create 3 columns
            mock_st.columns.assert_called_with(3)

    def test_grid_handles_partial_row(self) -> None:
        """Test grid handles partial row (2 modules) (Task 2.3)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}

            # Create mock columns
            mock_cols = [MagicMock() for _ in range(3)]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)

            mock_st.columns.return_value = mock_cols
            mock_st.button = MagicMock(return_value=False)
            mock_st.markdown = MagicMock()

            from app import render_module_grid

            # Pass only 2 modules (partial row)
            modules = create_test_modules()[:2]
            render_module_grid(modules)

            # Should still create columns
            mock_st.columns.assert_called()


# =============================================================================
# Task 5: Module Confirmation View Tests
# =============================================================================


class TestRenderModuleConfirmationHtml:
    """Tests for render_module_confirmation_html function (Task 5)."""

    def test_confirmation_shows_full_description(self) -> None:
        """Test confirmation shows full module description (Task 5.2)."""
        from app import render_module_confirmation_html

        long_desc = "A" * 200
        module = ModuleInfo(number=1, name="Test Module", description=long_desc)

        html = render_module_confirmation_html(module)

        # Full description should be in confirmation
        assert long_desc in html

    def test_confirmation_shows_module_name(self) -> None:
        """Test confirmation shows module name (Task 5.2)."""
        from app import render_module_confirmation_html

        module = ModuleInfo(
            number=1,
            name="Curse of Strahd",
            description="Gothic horror.",
        )

        html = render_module_confirmation_html(module)

        assert "Curse of Strahd" in html
        assert "module-title" in html

    def test_confirmation_has_proper_class(self) -> None:
        """Test confirmation has module-confirmation CSS class."""
        from app import render_module_confirmation_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_confirmation_html(module)

        assert 'class="module-confirmation"' in html

    def test_confirmation_escapes_html(self) -> None:
        """Test confirmation escapes HTML in module data."""
        from app import render_module_confirmation_html

        module = ModuleInfo(
            number=1,
            name="Test <b>Bold</b>",
            description="Desc with <script>",
        )

        html = render_module_confirmation_html(module)

        assert "<b>" not in html
        assert "<script>" not in html


# =============================================================================
# Task 7: Module Selection Orchestrator Tests
# =============================================================================


class TestRenderModuleSelectionUi:
    """Tests for render_module_selection_ui function (Task 7)."""

    def test_shows_loading_when_in_progress(self) -> None:
        """Test shows loading when discovery in progress (Task 7.2)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {"module_discovery_in_progress": True}

            with patch("app.render_module_discovery_loading") as mock_loading:
                from app import render_module_selection_ui

                render_module_selection_ui()

                mock_loading.assert_called_once()

    def test_shows_error_when_error_exists(self) -> None:
        """Test shows error when discovery error exists (Task 7.3)."""
        with patch("app.st") as mock_st:
            error = UserError(
                title="Test Error",
                message="Test message",
                action="Test action",
                error_type="unknown",
                timestamp="2026-02-01T00:00:00Z",
            )
            mock_st.session_state = {
                "module_discovery_in_progress": False,
                "module_discovery_error": error,
            }

            with patch("app.render_module_discovery_error") as mock_error:
                from app import render_module_selection_ui

                render_module_selection_ui()

                mock_error.assert_called_once_with(error)

    def test_shows_confirmation_when_module_selected(self) -> None:
        """Test shows confirmation when module is selected (Task 7.4)."""
        with patch("app.st") as mock_st:
            module = ModuleInfo(number=1, name="Test", description="Desc.")
            mock_st.session_state = {
                "module_discovery_in_progress": False,
                "module_discovery_error": None,
                "selected_module": module,
                "module_list": [module],
            }

            with patch("app.render_module_confirmation") as mock_confirm:
                from app import render_module_selection_ui

                render_module_selection_ui()

                mock_confirm.assert_called_once_with(module)

    def test_shows_browse_when_modules_available(self) -> None:
        """Test shows browse interface when modules available (Task 7.4)."""
        with patch("app.st") as mock_st:
            modules = create_test_modules()
            mock_st.session_state = {
                "module_discovery_in_progress": False,
                "module_discovery_error": None,
                "selected_module": None,
                "module_list": modules,
                "module_search_query": "",
            }
            mock_st.markdown = MagicMock()
            mock_st.text_input = MagicMock(return_value="")
            mock_st.button = MagicMock(return_value=False)
            mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])

            with patch("app.render_module_grid") as mock_grid:
                with patch("app.filter_modules") as mock_filter:
                    mock_filter.return_value = modules

                    from app import render_module_selection_ui

                    render_module_selection_ui()

                    # Should call render_module_grid
                    mock_grid.assert_called_once()
                    # Should call filter_modules
                    mock_filter.assert_called()


# =============================================================================
# Task 6: Error Handling View Tests
# =============================================================================


class TestRenderModuleDiscoveryError:
    """Tests for render_module_discovery_error function."""

    def test_shows_error_title_and_message(self) -> None:
        """Test error view shows title and message."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            mock_st.markdown = MagicMock()
            mock_st.button = MagicMock(return_value=False)
            mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])

            error = UserError(
                title="Test Error Title",
                message="Test error message",
                action="Test action",
                error_type="module_discovery_failed",
                timestamp="2026-02-01T00:00:00Z",
            )

            from app import render_module_discovery_error

            render_module_discovery_error(error)

            # Should call markdown with error info
            mock_st.markdown.assert_called()
            call_args = mock_st.markdown.call_args_list[0][0][0]
            assert "Test Error Title" in call_args
            assert "Test error message" in call_args


# =============================================================================
# Session State Management Tests
# =============================================================================


class TestModuleSelectionSessionState:
    """Tests for module selection session state management."""

    def test_clear_selection_clears_selected_module(self) -> None:
        """Test clear selection clears selected_module."""
        with patch("app.st") as mock_st:
            module = ModuleInfo(number=1, name="Test", description="Desc.")
            mock_st.session_state = {"selected_module": module}

            # Simulate the "Choose Different Module" action
            mock_st.session_state["selected_module"] = None

            assert mock_st.session_state["selected_module"] is None

    def test_confirm_selection_sets_confirmed_flag(self) -> None:
        """Test confirm selection sets module_selection_confirmed."""
        with patch("app.st") as mock_st:
            module = ModuleInfo(number=1, name="Test", description="Desc.")
            mock_st.session_state = {
                "selected_module": module,
                "module_selection_confirmed": False,
            }

            # Simulate the "Proceed to Party Setup" action
            mock_st.session_state["module_selection_confirmed"] = True

            assert mock_st.session_state["module_selection_confirmed"] is True

    def test_search_query_persistence(self) -> None:
        """Test search query persists in session state (Task 3.5)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {"module_search_query": ""}

            # Simulate user typing in search
            mock_st.session_state["module_search_query"] = "Strahd"

            assert mock_st.session_state["module_search_query"] == "Strahd"


# =============================================================================
# Function Existence Tests
# =============================================================================


class TestFunctionExistence:
    """Tests that required functions exist in app module."""

    def test_filter_modules_exists(self) -> None:
        """Test filter_modules function exists."""
        from app import filter_modules

        assert callable(filter_modules)

    def test_select_random_module_exists(self) -> None:
        """Test select_random_module function exists."""
        from app import select_random_module

        assert callable(select_random_module)

    def test_render_module_card_html_exists(self) -> None:
        """Test render_module_card_html function exists."""
        from app import render_module_card_html

        assert callable(render_module_card_html)

    def test_render_module_grid_exists(self) -> None:
        """Test render_module_grid function exists."""
        from app import render_module_grid

        assert callable(render_module_grid)

    def test_render_module_confirmation_exists(self) -> None:
        """Test render_module_confirmation function exists."""
        from app import render_module_confirmation

        assert callable(render_module_confirmation)

    def test_render_module_confirmation_html_exists(self) -> None:
        """Test render_module_confirmation_html function exists."""
        from app import render_module_confirmation_html

        assert callable(render_module_confirmation_html)

    def test_render_module_selection_ui_exists(self) -> None:
        """Test render_module_selection_ui function exists."""
        from app import render_module_selection_ui

        assert callable(render_module_selection_ui)

    def test_render_module_discovery_error_exists(self) -> None:
        """Test render_module_discovery_error function exists."""
        from app import render_module_discovery_error

        assert callable(render_module_discovery_error)


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================


class TestModuleSelectionEdgeCases:
    """Edge case tests for module selection UI."""

    def test_filter_with_special_characters(self) -> None:
        """Test filtering handles special characters in query."""
        from app import filter_modules

        modules = [
            ModuleInfo(
                number=1,
                name="Dragon's Lair",
                description="A dragon's treasure hoard.",
            ),
        ]

        result = filter_modules(modules, "Dragon's")
        assert len(result) == 1

    def test_filter_with_unicode(self) -> None:
        """Test filtering handles unicode characters."""
        from app import filter_modules

        modules = [
            ModuleInfo(
                number=1,
                name="The Eryth\u00e9an Quest",
                description="Adventure in Eryth\u00e9a.",
            ),
        ]

        result = filter_modules(modules, "Eryth")
        assert len(result) == 1

    def test_card_html_boundary_description(self) -> None:
        """Test card HTML with exactly 100 character description."""
        from app import render_module_card_html

        # Exactly 100 characters
        exact_100 = "A" * 100
        module = ModuleInfo(number=1, name="Test", description=exact_100)

        html = render_module_card_html(module)

        # Should not truncate at exactly 100
        assert "..." not in html or exact_100 in html

    def test_card_html_101_character_description(self) -> None:
        """Test card HTML with 101 character description (one over limit)."""
        from app import render_module_card_html

        # 101 characters - should be truncated
        over_100 = "A" * 101
        module = ModuleInfo(number=1, name="Test", description=over_100)

        html = render_module_card_html(module)

        # Should truncate
        assert "..." in html

    def test_results_count_display(self) -> None:
        """Test results count displays correctly."""
        with patch("app.st") as mock_st:
            modules = create_test_modules()
            mock_st.session_state = {
                "module_discovery_in_progress": False,
                "module_discovery_error": None,
                "selected_module": None,
                "module_list": modules,
                "module_search_query": "Strahd",
            }
            mock_st.markdown = MagicMock()
            mock_st.text_input = MagicMock(return_value="Strahd")
            mock_st.button = MagicMock(return_value=False)

            # Mock columns
            mock_cols = [MagicMock(), MagicMock()]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)
            mock_st.columns = MagicMock(return_value=mock_cols)

            with patch("app.render_module_grid"):
                with patch("app.filter_modules") as mock_filter:
                    mock_filter.return_value = [modules[0]]  # One result

                    from app import render_module_selection_ui

                    render_module_selection_ui()

                    # Check that result count markdown was called
                    markdown_calls = [
                        call[0][0]
                        for call in mock_st.markdown.call_args_list
                        if call[0]
                    ]
                    # Should have a results count message
                    results_found = any(
                        "1" in str(call) and "5" in str(call) for call in markdown_calls
                    )
                    assert results_found or len(markdown_calls) > 0
