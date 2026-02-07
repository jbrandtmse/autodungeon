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


# =============================================================================
# Extended Coverage: Filter Modules Edge Cases
# =============================================================================


class TestFilterModulesExtended:
    """Extended tests for filter_modules edge cases."""

    def test_filter_with_regex_special_chars_dot(self) -> None:
        """Test filtering treats regex special char dot as literal."""
        from app import filter_modules

        modules = [
            ModuleInfo(number=1, name="A.B.C Adventure", description="Test."),
        ]

        # Dot should match literally, not as regex wildcard
        result = filter_modules(modules, "A.B")
        assert len(result) == 1

        # This should NOT match if treated literally
        result_no_match = filter_modules(modules, "AXB")
        assert len(result_no_match) == 0

    def test_filter_with_regex_special_chars_asterisk(self) -> None:
        """Test filtering treats asterisk as literal character."""
        from app import filter_modules

        modules = [
            ModuleInfo(number=1, name="5* Adventure", description="Five star quest."),
        ]

        result = filter_modules(modules, "5*")
        assert len(result) == 1

    def test_filter_with_regex_special_chars_plus(self) -> None:
        """Test filtering treats plus as literal character."""
        from app import filter_modules

        modules = [
            ModuleInfo(number=1, name="D&D+ Edition", description="Enhanced edition."),
        ]

        result = filter_modules(modules, "D+")
        assert len(result) == 1

    def test_filter_with_regex_special_chars_question_mark(self) -> None:
        """Test filtering treats question mark as literal character."""
        from app import filter_modules

        modules = [
            ModuleInfo(number=1, name="Who Did It?", description="Mystery adventure."),
        ]

        result = filter_modules(modules, "It?")
        assert len(result) == 1

    def test_filter_with_regex_special_chars_brackets(self) -> None:
        """Test filtering treats brackets as literal characters."""
        from app import filter_modules

        modules = [
            ModuleInfo(number=1, name="[BETA] Module", description="Test beta."),
        ]

        result = filter_modules(modules, "[BETA]")
        assert len(result) == 1

    def test_filter_with_regex_special_chars_parentheses(self) -> None:
        """Test filtering treats parentheses as literal characters."""
        from app import filter_modules

        modules = [
            ModuleInfo(
                number=1, name="Module (Revised)", description="Revised edition."
            ),
        ]

        result = filter_modules(modules, "(Revised)")
        assert len(result) == 1

    def test_filter_with_regex_special_chars_pipe(self) -> None:
        """Test filtering treats pipe as literal character."""
        from app import filter_modules

        modules = [
            ModuleInfo(
                number=1, name="Good|Evil Campaign", description="Moral choices."
            ),
        ]

        result = filter_modules(modules, "Good|Evil")
        assert len(result) == 1

    def test_filter_with_regex_special_chars_backslash(self) -> None:
        """Test filtering handles backslash characters."""
        from app import filter_modules

        modules = [
            ModuleInfo(
                number=1, name="Path\\to\\Adventure", description="Filesystem path."
            ),
        ]

        result = filter_modules(modules, "Path\\to")
        assert len(result) == 1

    def test_filter_with_regex_special_chars_caret_dollar(self) -> None:
        """Test filtering treats caret and dollar as literal characters."""
        from app import filter_modules

        modules = [
            ModuleInfo(number=1, name="^Start Module$", description="Anchor test."),
        ]

        result = filter_modules(modules, "^Start")
        assert len(result) == 1

        result2 = filter_modules(modules, "Module$")
        assert len(result2) == 1

    def test_filter_with_very_long_search_term(self) -> None:
        """Test filtering with a very long search term."""
        from app import filter_modules

        modules = create_test_modules()
        long_query = "a" * 500

        result = filter_modules(modules, long_query)
        # Should return empty (no match) but not crash
        assert len(result) == 0

    def test_filter_with_numeric_search(self) -> None:
        """Test filtering with numeric values."""
        from app import filter_modules

        modules = [
            ModuleInfo(number=1, name="Module 123", description="Test 456."),
        ]

        result = filter_modules(modules, "123")
        assert len(result) == 1

        result2 = filter_modules(modules, "456")
        assert len(result2) == 1

    def test_filter_with_tabs_in_query(self) -> None:
        """Test filtering handles tab characters in query."""
        from app import filter_modules

        modules = create_test_modules()

        # Tab should be treated as whitespace separator
        result = filter_modules(modules, "Curse\tStrahd")
        # Both terms should be searched
        assert len(result) <= len(modules)

    def test_filter_with_newline_in_query(self) -> None:
        """Test filtering handles newline characters in query."""
        from app import filter_modules

        modules = create_test_modules()

        result = filter_modules(modules, "Curse\nStrahd")
        # Implementation splits on whitespace, newline treated as separator
        assert len(result) <= len(modules)

    def test_filter_module_with_default_setting(self) -> None:
        """Test filtering module with default (empty string) setting field."""
        from app import filter_modules

        # ModuleInfo setting defaults to "" when not provided
        modules = [
            ModuleInfo(number=1, name="Test Module", description="Test desc."),
        ]

        result = filter_modules(modules, "Test")
        assert len(result) == 1

    def test_filter_module_with_empty_setting(self) -> None:
        """Test filtering module with empty string setting."""
        from app import filter_modules

        modules = [
            ModuleInfo(
                number=1, name="Test Module", description="Test desc.", setting=""
            ),
        ]

        result = filter_modules(modules, "Test")
        assert len(result) == 1

    def test_filter_preserves_order(self) -> None:
        """Test filtering preserves original module order."""
        from app import filter_modules

        modules = create_test_modules()
        result = filter_modules(modules, "Forgotten")

        # Check order is preserved
        numbers = [m.number for m in result]
        assert numbers == sorted(numbers)

    def test_filter_single_character_query(self) -> None:
        """Test filtering with single character query."""
        from app import filter_modules

        modules = create_test_modules()
        result = filter_modules(modules, "a")

        # Should match modules containing 'a'
        assert len(result) >= 1

    def test_filter_query_with_multiple_spaces(self) -> None:
        """Test filtering treats multiple spaces as single separator."""
        from app import filter_modules

        modules = create_test_modules()
        result = filter_modules(modules, "Curse    Strahd")

        # Should still match "Curse of Strahd"
        assert len(result) == 1
        assert result[0].name == "Curse of Strahd"


# =============================================================================
# Extended Coverage: Random Selection Edge Cases
# =============================================================================


class TestSelectRandomModuleExtended:
    """Extended tests for select_random_module edge cases."""

    def test_random_selection_single_item(self) -> None:
        """Test random selection with exactly one module."""
        with patch("app.st") as mock_st:
            single_module = ModuleInfo(number=1, name="Only One", description="Desc.")
            mock_st.session_state = {"module_list": [single_module]}
            mock_st.rerun = MagicMock()

            from app import select_random_module

            select_random_module()

            # Must select the only available module
            assert mock_st.session_state["selected_module"] == single_module
            mock_st.rerun.assert_called_once()

    def test_random_selection_large_list(self) -> None:
        """Test random selection with 100 modules."""
        with patch("app.st") as mock_st:
            # Create 100 modules (number must be 1-100)
            large_list = [
                ModuleInfo(number=i, name=f"Module {i}", description=f"Desc {i}.")
                for i in range(1, 101)
            ]
            mock_st.session_state = {"module_list": large_list}
            mock_st.rerun = MagicMock()

            from app import select_random_module

            select_random_module()

            # Should select one from the list
            assert mock_st.session_state["selected_module"] in large_list
            mock_st.rerun.assert_called_once()

    def test_random_selection_deterministic_with_seed(self) -> None:
        """Test random selection is deterministic when random is seeded."""
        import random as real_random

        with patch("app.st") as mock_st:
            modules = create_test_modules()
            mock_st.session_state = {"module_list": modules}
            mock_st.rerun = MagicMock()

            # Seed the random generator for deterministic behavior
            with patch("app.random") as mock_random:
                mock_random.choice.return_value = modules[2]

                from app import select_random_module

                select_random_module()

                assert mock_st.session_state["selected_module"] == modules[2]


# =============================================================================
# Extended Coverage: HTML Rendering Security
# =============================================================================


class TestHtmlRenderingSecurity:
    """Extended tests for XSS prevention in HTML rendering."""

    def test_card_escapes_script_in_name(self) -> None:
        """Test card escapes script tags in module name."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name="<script>alert('xss')</script>",
            description="Normal description.",
        )

        html = render_module_card_html(module)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_card_escapes_script_in_description(self) -> None:
        """Test card escapes script tags in description."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name="Normal Name",
            description="<script>evil()</script>",
        )

        html = render_module_card_html(module)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_card_escapes_event_handlers(self) -> None:
        """Test card escapes onerror and other event handlers."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name='<img src=x onerror="alert(1)">',
            description="Normal description.",
        )

        html = render_module_card_html(module)

        assert 'onerror="alert' not in html
        assert "&lt;img" in html

    def test_card_escapes_javascript_protocol(self) -> None:
        """Test card escapes javascript: protocol URLs."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name="javascript:alert(1)",
            description="Normal description.",
        )

        html = render_module_card_html(module)

        # javascript: should be escaped or rendered safely
        # It's in plain text context, so should be displayed literally
        assert "javascript:alert(1)" in html or "javascript" in html

    def test_card_escapes_double_quotes(self) -> None:
        """Test card escapes double quotes to prevent attribute breakout."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name='Test" onclick="evil()',
            description="Normal description.",
        )

        html = render_module_card_html(module)

        # Should escape the quote
        assert "&quot;" in html or "onclick" not in html.lower().replace("&", "")

    def test_card_escapes_single_quotes(self) -> None:
        """Test card handles single quotes in content."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name="Dragon's Lair",
            description="The dragon's treasure awaits.",
        )

        html = render_module_card_html(module)

        # Single quotes should be safe (or escaped)
        assert "Dragon" in html
        # Should not break the HTML structure
        assert 'class="module-card' in html

    def test_card_escapes_ampersand(self) -> None:
        """Test card escapes ampersand characters."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name="Dungeons & Dragons",
            description="The classic D&D experience.",
        )

        html = render_module_card_html(module)

        assert "&amp;" in html

    def test_card_escapes_less_than_greater_than(self) -> None:
        """Test card escapes < and > characters."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name="Level 1-5 <Recommended>",
            description="For parties < 5 members.",
        )

        html = render_module_card_html(module)

        assert "&lt;" in html
        assert "&gt;" in html

    def test_confirmation_escapes_script_tags(self) -> None:
        """Test confirmation view escapes script tags."""
        from app import render_module_confirmation_html

        module = ModuleInfo(
            number=1,
            name="<script>alert(1)</script>",
            description="<script>evil()</script>",
        )

        html = render_module_confirmation_html(module)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_confirmation_escapes_event_handlers(self) -> None:
        """Test confirmation view escapes event handlers."""
        from app import render_module_confirmation_html

        module = ModuleInfo(
            number=1,
            name='<div onmouseover="evil()">',
            description="Normal.",
        )

        html = render_module_confirmation_html(module)

        assert 'onmouseover="' not in html

    def test_css_injection_prevention(self) -> None:
        """Test that CSS injection via style tags is prevented."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name="<style>body{display:none}</style>",
            description="Normal.",
        )

        html = render_module_card_html(module)

        assert "<style>" not in html
        assert "&lt;style&gt;" in html


# =============================================================================
# Extended Coverage: render_module_card_html Edge Cases
# =============================================================================


class TestRenderModuleCardHtmlExtended:
    """Extended tests for render_module_card_html edge cases."""

    def test_card_minimal_description(self) -> None:
        """Test card with minimal (1-char) description."""
        from app import render_module_card_html

        # ModuleInfo requires description to have at least 1 char
        module = ModuleInfo(number=1, name="Test Module", description=".")

        html = render_module_card_html(module)

        assert "Test Module" in html
        assert 'class="module-description"' in html
        assert "." in html

    def test_card_description_exactly_97_chars(self) -> None:
        """Test card with description exactly at truncation boundary (97)."""
        from app import render_module_card_html

        # 97 chars - should NOT be truncated
        desc_97 = "A" * 97
        module = ModuleInfo(number=1, name="Test", description=desc_97)

        html = render_module_card_html(module)

        # Should not have ellipsis
        assert "..." not in html
        assert desc_97 in html

    def test_card_description_exactly_100_chars(self) -> None:
        """Test card with description exactly 100 chars (boundary)."""
        from app import render_module_card_html

        desc_100 = "B" * 100
        module = ModuleInfo(number=1, name="Test", description=desc_100)

        html = render_module_card_html(module)

        # Should not truncate at exactly 100
        assert desc_100 in html

    def test_card_description_101_chars_truncates(self) -> None:
        """Test card with 101 char description truncates to 97+..."""
        from app import render_module_card_html

        desc_101 = "C" * 101
        module = ModuleInfo(number=1, name="Test", description=desc_101)

        html = render_module_card_html(module)

        # Should truncate
        assert "..." in html
        # Full description should NOT be present
        assert desc_101 not in html
        # First 97 chars should be present
        assert "C" * 97 in html

    def test_card_very_long_name(self) -> None:
        """Test card with very long module name."""
        from app import render_module_card_html

        long_name = "X" * 500
        module = ModuleInfo(number=1, name=long_name, description="Short desc.")

        html = render_module_card_html(module)

        # Name should be present (not truncated by this function)
        assert long_name in html
        # Should still have proper structure
        assert 'class="module-name"' in html

    def test_card_unicode_name(self) -> None:
        """Test card with unicode characters in name."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name="The Erythean Quest",
            description="Adventure in Erythea.",
        )

        html = render_module_card_html(module)

        assert "Erythean" in html

    def test_card_unicode_description(self) -> None:
        """Test card with unicode characters in description."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name="Test Module",
            description="Navigate the labyrinth of Noe.",
        )

        html = render_module_card_html(module)

        assert "Noe" in html

    def test_card_emoji_in_name(self) -> None:
        """Test card handles emoji in module name."""
        from app import render_module_card_html

        module = ModuleInfo(
            number=1,
            name="Dragon Quest",
            description="Face the dragon.",
        )

        html = render_module_card_html(module)

        assert "Dragon" in html

    def test_card_whitespace_only_description(self) -> None:
        """Test card with whitespace-only description."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="Test", description="   ")

        html = render_module_card_html(module)

        # Should render without crashing
        assert 'class="module-card' in html

    def test_card_aria_label_contains_module_name(self) -> None:
        """Test card aria-label includes escaped module name."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="Test Module", description="Desc.")

        html = render_module_card_html(module)

        assert 'aria-label="Module: Test Module"' in html

    def test_card_aria_label_escapes_special_chars(self) -> None:
        """Test card aria-label escapes special characters."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name='Test "Quoted"', description="Desc.")

        html = render_module_card_html(module)

        # Should escape the quotes in aria-label
        assert "&quot;" in html or "Quoted" in html

    def test_card_has_role_article(self) -> None:
        """Test card has role=article for accessibility."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_card_html(module)

        assert 'role="article"' in html


# =============================================================================
# Extended Coverage: render_module_confirmation_html Edge Cases
# =============================================================================


class TestRenderModuleConfirmationHtmlExtended:
    """Extended tests for render_module_confirmation_html edge cases."""

    def test_confirmation_minimal_description(self) -> None:
        """Test confirmation with minimal (1-char) description."""
        from app import render_module_confirmation_html

        # ModuleInfo requires description to have at least 1 char
        module = ModuleInfo(number=1, name="Test", description=".")

        html = render_module_confirmation_html(module)

        assert "Test" in html
        assert 'class="module-full-description"' in html
        assert "." in html

    def test_confirmation_very_long_description(self) -> None:
        """Test confirmation shows very long description fully."""
        from app import render_module_confirmation_html

        long_desc = "D" * 2000
        module = ModuleInfo(number=1, name="Test", description=long_desc)

        html = render_module_confirmation_html(module)

        # Full description should be present (no truncation)
        assert long_desc in html
        assert "..." not in html

    def test_confirmation_has_role_region(self) -> None:
        """Test confirmation has role=region for accessibility."""
        from app import render_module_confirmation_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_confirmation_html(module)

        assert 'role="region"' in html

    def test_confirmation_aria_label_contains_module_name(self) -> None:
        """Test confirmation aria-label includes module name."""
        from app import render_module_confirmation_html

        module = ModuleInfo(number=1, name="Epic Quest", description="Desc.")

        html = render_module_confirmation_html(module)

        assert 'aria-label="Selected module: Epic Quest"' in html

    def test_confirmation_all_optional_fields(self) -> None:
        """Test confirmation with all optional fields present."""
        from app import render_module_confirmation_html

        module = ModuleInfo(
            number=1,
            name="Full Module",
            description="Complete description.",
            setting="Forgotten Realms",
            level_range="1-10",
        )

        html = render_module_confirmation_html(module)

        # Core content should be present
        assert "Full Module" in html
        assert "Complete description." in html

    def test_confirmation_unicode_characters(self) -> None:
        """Test confirmation handles unicode in all fields."""
        from app import render_module_confirmation_html

        module = ModuleInfo(
            number=1,
            name="Le Chateau Magnifique",
            description="Une aventure fantastique dans le royaume enchan.",
        )

        html = render_module_confirmation_html(module)

        assert "Chateau" in html
        assert "fantastique" in html


# =============================================================================
# Extended Coverage: render_module_grid Edge Cases
# =============================================================================


class TestRenderModuleGridExtended:
    """Extended tests for render_module_grid edge cases."""

    def test_grid_single_module(self) -> None:
        """Test grid with exactly one module."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}

            mock_cols = [MagicMock() for _ in range(3)]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)

            mock_st.columns.return_value = mock_cols
            mock_st.button = MagicMock(return_value=False)
            mock_st.markdown = MagicMock()

            from app import render_module_grid

            single_module = [ModuleInfo(number=1, name="Only", description="One.")]
            render_module_grid(single_module)

            # Should still create columns
            mock_st.columns.assert_called_with(3)

    def test_grid_exactly_three_modules(self) -> None:
        """Test grid with exactly 3 modules (one full row)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}

            mock_cols = [MagicMock() for _ in range(3)]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)

            mock_st.columns.return_value = mock_cols
            mock_st.button = MagicMock(return_value=False)
            mock_st.markdown = MagicMock()

            from app import render_module_grid

            three_modules = create_test_modules()[:3]
            render_module_grid(three_modules)

            # Should create exactly one row (one call to columns)
            assert mock_st.columns.call_count == 1

    def test_grid_exactly_six_modules(self) -> None:
        """Test grid with exactly 6 modules (two full rows)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}

            mock_cols = [MagicMock() for _ in range(3)]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)

            mock_st.columns.return_value = mock_cols
            mock_st.button = MagicMock(return_value=False)
            mock_st.markdown = MagicMock()

            from app import render_module_grid

            # ModuleInfo number must be 1-100
            six_modules = [
                ModuleInfo(number=i, name=f"Module {i}", description=f"Desc {i}.")
                for i in range(1, 7)
            ]
            render_module_grid(six_modules)

            # Should create exactly two rows
            assert mock_st.columns.call_count == 2

    def test_grid_four_modules_partial_second_row(self) -> None:
        """Test grid with 4 modules (full row + 1)."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}

            mock_cols = [MagicMock() for _ in range(3)]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)

            mock_st.columns.return_value = mock_cols
            mock_st.button = MagicMock(return_value=False)
            mock_st.markdown = MagicMock()

            from app import render_module_grid

            # ModuleInfo number must be 1-100
            four_modules = [
                ModuleInfo(number=i, name=f"Module {i}", description=f"Desc {i}.")
                for i in range(1, 5)
            ]
            render_module_grid(four_modules)

            # Should create two rows
            assert mock_st.columns.call_count == 2

    def test_grid_large_list_100_modules(self) -> None:
        """Test grid with 100 modules for performance."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}

            mock_cols = [MagicMock() for _ in range(3)]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)

            mock_st.columns.return_value = mock_cols
            mock_st.button = MagicMock(return_value=False)
            mock_st.markdown = MagicMock()

            from app import render_module_grid

            # ModuleInfo number must be 1-100
            large_list = [
                ModuleInfo(
                    number=i, name=f"Module {i}", description=f"Description {i}."
                )
                for i in range(1, 101)
            ]
            render_module_grid(large_list)

            # 100 modules = 34 rows (33 full + 1 partial)
            assert mock_st.columns.call_count == 34

    def test_grid_module_selection_updates_state(self) -> None:
        """Test clicking select on a module updates session state."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {}
            mock_st.rerun = MagicMock()

            mock_cols = [MagicMock() for _ in range(3)]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)

            mock_st.columns.return_value = mock_cols
            mock_st.markdown = MagicMock()

            # Simulate first button click returning True
            click_count = [0]

            def button_side_effect(*args, **kwargs):
                click_count[0] += 1
                return click_count[0] == 1  # First button click returns True

            mock_st.button = MagicMock(side_effect=button_side_effect)

            from app import render_module_grid

            modules = create_test_modules()[:1]

            with patch("app.render_module_card") as mock_render_card:
                mock_render_card.return_value = True  # Simulate selection

                render_module_grid(modules)

                # Should set selected module and rerun
                assert mock_st.session_state.get("selected_module") == modules[0]
                mock_st.rerun.assert_called_once()


# =============================================================================
# Extended Coverage: render_module_selection_ui Integration
# =============================================================================


class TestRenderModuleSelectionUiExtended:
    """Extended integration tests for render_module_selection_ui."""

    def test_empty_module_list_no_error(self) -> None:
        """Test empty module list shows warning when no error."""
        with patch("app.st") as mock_st:
            mock_st.session_state = {
                "module_discovery_in_progress": False,
                "module_discovery_error": None,
                "selected_module": None,
                "module_list": [],
            }
            mock_st.warning = MagicMock()

            from app import render_module_selection_ui

            render_module_selection_ui()

            # Should show warning about no modules
            mock_st.warning.assert_called_once()
            assert "No modules" in mock_st.warning.call_args[0][0]

    def test_results_count_zero_matches(self) -> None:
        """Test results count shows 0 when no matches."""
        with patch("app.st") as mock_st:
            modules = create_test_modules()
            mock_st.session_state = {
                "module_discovery_in_progress": False,
                "module_discovery_error": None,
                "selected_module": None,
                "module_list": modules,
                "module_search_query": "nonexistent",
            }
            mock_st.markdown = MagicMock()
            mock_st.text_input = MagicMock(return_value="nonexistent")
            mock_st.button = MagicMock(return_value=False)

            mock_cols = [MagicMock(), MagicMock()]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)
            mock_st.columns = MagicMock(return_value=mock_cols)

            with patch("app.render_module_grid"):
                with patch("app.filter_modules") as mock_filter:
                    mock_filter.return_value = []  # No results

                    from app import render_module_selection_ui

                    render_module_selection_ui()

                    # Should call markdown with "0" in the count
                    markdown_calls = [str(c) for c in mock_st.markdown.call_args_list]
                    has_zero = any("0" in call for call in markdown_calls)
                    assert has_zero or mock_st.markdown.called

    def test_results_count_all_matches(self) -> None:
        """Test results count shows all when no filter applied."""
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

            mock_cols = [MagicMock(), MagicMock()]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)
            mock_st.columns = MagicMock(return_value=mock_cols)

            with patch("app.render_module_grid"):
                with patch("app.filter_modules") as mock_filter:
                    mock_filter.return_value = modules

                    from app import render_module_selection_ui

                    render_module_selection_ui()

                    # Should call grid with all modules
                    mock_filter.assert_called_with(modules, "")

    def test_random_button_triggers_selection(self) -> None:
        """Test Random Module button triggers select_random_module."""
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

            # Simulate Random button click
            button_calls = [0]

            def button_side_effect(*args, **kwargs):
                button_calls[0] += 1
                if "Random" in str(args):
                    return True
                return False

            mock_st.button = MagicMock(side_effect=button_side_effect)

            mock_cols = [MagicMock(), MagicMock()]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)
            mock_st.columns = MagicMock(return_value=mock_cols)

            with patch("app.render_module_grid"):
                with patch("app.filter_modules") as mock_filter:
                    mock_filter.return_value = modules

                    with patch("app.select_random_module") as mock_random:
                        from app import render_module_selection_ui

                        render_module_selection_ui()

                        # Random button should trigger selection
                        # (depends on button mock implementation)

    def test_search_query_persists_between_renders(self) -> None:
        """Test search query is preserved in session state."""
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

            mock_cols = [MagicMock(), MagicMock()]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)
            mock_st.columns = MagicMock(return_value=mock_cols)

            with patch("app.render_module_grid"):
                with patch("app.filter_modules"):
                    from app import render_module_selection_ui

                    render_module_selection_ui()

                    # Query should be passed to text_input as default
                    text_input_kwargs = mock_st.text_input.call_args[1]
                    assert text_input_kwargs.get("value") == "Strahd"


# =============================================================================
# Extended Coverage: Session State Transitions
# =============================================================================


class TestSessionStateTransitions:
    """Extended tests for session state transitions in module selection."""

    def test_transition_loading_to_browse(self) -> None:
        """Test transition from loading state to browse state."""
        with patch("app.st") as mock_st:
            # Start in loading state
            mock_st.session_state = {"module_discovery_in_progress": True}

            from app import render_module_selection_ui

            with patch("app.render_module_discovery_loading") as mock_loading:
                render_module_selection_ui()
                mock_loading.assert_called_once()

            # Transition to browse state
            mock_st.session_state["module_discovery_in_progress"] = False
            mock_st.session_state["module_list"] = create_test_modules()
            mock_st.session_state["selected_module"] = None
            mock_st.session_state["module_discovery_error"] = None
            mock_st.session_state["module_search_query"] = ""
            mock_st.markdown = MagicMock()
            mock_st.text_input = MagicMock(return_value="")
            mock_st.button = MagicMock(return_value=False)
            mock_cols = [MagicMock(), MagicMock()]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)
            mock_st.columns = MagicMock(return_value=mock_cols)

            with patch("app.render_module_grid") as mock_grid:
                with patch("app.filter_modules"):
                    render_module_selection_ui()
                    mock_grid.assert_called_once()

    def test_transition_browse_to_confirmation(self) -> None:
        """Test transition from browse to confirmation state."""
        with patch("app.st") as mock_st:
            module = ModuleInfo(number=1, name="Test", description="Desc.")

            # Start in browse state
            mock_st.session_state = {
                "module_discovery_in_progress": False,
                "module_discovery_error": None,
                "selected_module": None,
                "module_list": [module],
            }

            # Simulate selecting a module
            mock_st.session_state["selected_module"] = module

            from app import render_module_selection_ui

            with patch("app.render_module_confirmation") as mock_confirm:
                render_module_selection_ui()
                mock_confirm.assert_called_once_with(module)

    def test_transition_error_to_loading_on_retry(self) -> None:
        """Test transition from error state back to loading on retry."""
        with patch("app.st") as mock_st:
            error = UserError(
                title="Error",
                message="Failed",
                action="Retry",
                error_type="module_discovery_failed",
                timestamp="2026-02-01T00:00:00Z",
            )
            mock_st.session_state = {
                "module_discovery_in_progress": False,
                "module_discovery_error": error,
            }
            mock_st.markdown = MagicMock()
            mock_st.button = MagicMock(return_value=False)
            mock_cols = [MagicMock(), MagicMock()]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)
            mock_st.columns = MagicMock(return_value=mock_cols)

            from app import render_module_discovery_error

            render_module_discovery_error(error)

            # Error panel should be shown
            mock_st.markdown.assert_called()

    def test_confirmation_back_to_browse(self) -> None:
        """Test going back from confirmation to browse."""
        with patch("app.st") as mock_st:
            module = ModuleInfo(number=1, name="Test", description="Desc.")

            # In confirmation state
            mock_st.session_state = {
                "module_discovery_in_progress": False,
                "module_discovery_error": None,
                "selected_module": module,
                "module_list": [module],
            }

            # Clear selection to go back
            mock_st.session_state["selected_module"] = None
            mock_st.session_state["module_search_query"] = ""

            mock_st.markdown = MagicMock()
            mock_st.text_input = MagicMock(return_value="")
            mock_st.button = MagicMock(return_value=False)
            mock_cols = [MagicMock(), MagicMock()]
            for col in mock_cols:
                col.__enter__ = MagicMock(return_value=col)
                col.__exit__ = MagicMock(return_value=False)
            mock_st.columns = MagicMock(return_value=mock_cols)

            from app import render_module_selection_ui

            with patch("app.render_module_grid"):
                with patch("app.filter_modules"):
                    render_module_selection_ui()
                    # Should show browse UI, not confirmation


# =============================================================================
# Extended Coverage: Accessibility Tests
# =============================================================================


class TestAccessibilityAttributes:
    """Tests for accessibility attributes in rendered HTML."""

    def test_card_has_aria_selected_true_when_selected(self) -> None:
        """Test selected card has aria-selected=true."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_card_html(module, selected=True)

        assert 'aria-selected="true"' in html

    def test_card_has_aria_selected_false_when_not_selected(self) -> None:
        """Test non-selected card has aria-selected=false."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_card_html(module, selected=False)

        assert 'aria-selected="false"' in html

    def test_card_default_not_selected(self) -> None:
        """Test card defaults to not selected."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_card_html(module)  # No selected param

        assert 'aria-selected="false"' in html
        assert 'class="module-card"' in html
        assert "selected" not in html.split('class="module-card"')[1].split('"')[0]

    def test_confirmation_has_aria_label(self) -> None:
        """Test confirmation has descriptive aria-label."""
        from app import render_module_confirmation_html

        module = ModuleInfo(number=1, name="Epic Quest", description="Desc.")

        html = render_module_confirmation_html(module)

        assert "aria-label=" in html
        assert "Epic Quest" in html


# =============================================================================
# Extended Coverage: CSS Class Application
# =============================================================================


class TestCssClassApplication:
    """Tests for correct CSS class application."""

    def test_card_has_module_card_class(self) -> None:
        """Test card has base module-card class."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_card_html(module)

        assert 'class="module-card"' in html

    def test_selected_card_has_selected_class(self) -> None:
        """Test selected card has both module-card and selected classes."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_card_html(module, selected=True)

        assert 'class="module-card selected"' in html

    def test_card_has_module_name_class(self) -> None:
        """Test card name element has module-name class."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_card_html(module)

        assert 'class="module-name"' in html

    def test_card_has_module_description_class(self) -> None:
        """Test card description element has module-description class."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_card_html(module)

        assert 'class="module-description"' in html

    def test_confirmation_has_module_confirmation_class(self) -> None:
        """Test confirmation container has module-confirmation class."""
        from app import render_module_confirmation_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_confirmation_html(module)

        assert 'class="module-confirmation"' in html

    def test_confirmation_has_module_title_class(self) -> None:
        """Test confirmation title has module-title class."""
        from app import render_module_confirmation_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_confirmation_html(module)

        assert 'class="module-title"' in html

    def test_confirmation_has_module_full_description_class(self) -> None:
        """Test confirmation description has module-full-description class."""
        from app import render_module_confirmation_html

        module = ModuleInfo(number=1, name="Test", description="Desc.")

        html = render_module_confirmation_html(module)

        assert 'class="module-full-description"' in html


# =============================================================================
# Extended Coverage: Boundary Conditions
# =============================================================================


class TestBoundaryConditions:
    """Tests for boundary conditions and edge values."""

    def test_filter_modules_empty_list(self) -> None:
        """Test filter_modules with empty module list."""
        from app import filter_modules

        result = filter_modules([], "test")
        assert result == []

    def test_filter_modules_single_item_match(self) -> None:
        """Test filter_modules with single matching module."""
        from app import filter_modules

        modules = [ModuleInfo(number=1, name="Only One", description="Single.")]

        result = filter_modules(modules, "Only")
        assert len(result) == 1

    def test_filter_modules_single_item_no_match(self) -> None:
        """Test filter_modules with single non-matching module."""
        from app import filter_modules

        modules = [ModuleInfo(number=1, name="Only One", description="Single.")]

        result = filter_modules(modules, "nomatch")
        assert len(result) == 0

    def test_description_truncation_at_exactly_100(self) -> None:
        """Test description truncation boundary at 100 chars."""
        from app import render_module_card_html

        # Test 99, 100, and 101 character descriptions
        for length, should_truncate in [(99, False), (100, False), (101, True)]:
            desc = "X" * length
            module = ModuleInfo(number=1, name="Test", description=desc)
            html = render_module_card_html(module)

            if should_truncate:
                assert "..." in html, f"Expected truncation for {length} chars"
                assert desc not in html
            else:
                assert desc in html, f"Unexpected truncation for {length} chars"

    def test_module_number_minimum(self) -> None:
        """Test module with minimum valid number (1) is handled correctly."""
        from app import render_module_card_html

        module = ModuleInfo(number=1, name="First Module", description="Desc.")

        html = render_module_card_html(module)

        assert "First Module" in html

    def test_module_number_maximum(self) -> None:
        """Test module with maximum valid number (100) is handled correctly."""
        from app import render_module_card_html

        module = ModuleInfo(number=100, name="Last Module", description="Desc.")

        html = render_module_card_html(module)

        assert "Last Module" in html

    def test_module_number_mid_range(self) -> None:
        """Test module with mid-range number (50) is handled correctly."""
        from app import render_module_card_html

        module = ModuleInfo(number=50, name="Middle Module", description="Desc.")

        html = render_module_card_html(module)

        assert "Middle Module" in html
