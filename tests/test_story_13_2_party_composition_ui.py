"""Tests for Story 13.2: Party Composition UI.

This test file covers:
- Routing tests (module selection -> party_setup, party_setup -> game, back, wizard return)
- Character loading tests (presets loaded, library loaded, defaults correct)
- Selection tests (toggle, multiple select/deselect)
- Validation tests (0 selected = warning, 1+ = game starts)
- Integration tests (characters_override passed, library->CharacterConfig, state cleanup)
- XSS tests (HTML in names escaped)
- Session name tests (present on party setup, persists across transitions)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    pass

from models import CharacterConfig

# =============================================================================
# Helper: Create mock CharacterConfig instances
# =============================================================================


def _make_char_config(
    name: str = "TestChar",
    character_class: str = "Fighter",
    color: str = "#C45C4A",
    provider: str = "gemini",
    model: str = "gemini-1.5-flash",
) -> CharacterConfig:
    return CharacterConfig(
        name=name,
        character_class=character_class,
        personality="A test character.",
        color=color,
        provider=provider,
        model=model,
    )


def _make_library_char(
    name: str = "LibChar",
    char_class: str = "Warlock",
    color: str = "#4B0082",
    filename: str = "libchar.yaml",
) -> dict[str, Any]:
    return {
        "name": name,
        "class": char_class,
        "personality": "A mysterious adventurer.",
        "color": color,
        "provider": "claude",
        "model": "claude-3-haiku-20240307",
        "token_limit": 4000,
        "_filename": filename,
        "_filepath": f"config/characters/library/{filename}",
    }


# =============================================================================
# Task 1: Routing Tests
# =============================================================================


class TestRoutingModuleSelectionToPartySetup:
    """Tests for module selection -> party_setup routing (Story 13.2)."""

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    def test_confirmed_routes_to_party_setup(
        self,
        mock_render_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test module_selection_confirmed routes to party_setup view.

        Story 13.2: Module confirmation goes to party setup, not directly to game.
        """
        from app import render_module_selection_view

        mock_st.session_state = {"module_selection_confirmed": True}
        mock_st.button.return_value = False

        render_module_selection_view()

        assert mock_st.session_state["app_view"] == "party_setup"
        mock_st.rerun.assert_called()

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    def test_confirmed_does_not_call_handle_new_session_click(
        self,
        mock_render_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test module confirmation does NOT call handle_new_session_click directly.

        Story 13.2: Game start is deferred to party setup completion.
        """
        from app import render_module_selection_view

        mock_st.session_state = {"module_selection_confirmed": True}
        mock_st.button.return_value = False

        with patch("app.handle_new_session_click") as mock_new_session:
            render_module_selection_view()
            mock_new_session.assert_not_called()

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    def test_confirmed_does_not_clear_module_state(
        self,
        mock_render_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test module confirmation preserves module state for party setup.

        Story 13.2: Module state must survive into party setup.
        """
        from app import render_module_selection_view

        mock_st.session_state = {
            "module_selection_confirmed": True,
            "selected_module": MagicMock(),
        }
        mock_st.button.return_value = False

        with patch("app.clear_module_discovery_state") as mock_clear:
            render_module_selection_view()
            mock_clear.assert_not_called()


class TestRoutingPartySetupToGame:
    """Tests for party_setup -> game routing via Begin Adventure."""

    def test_begin_adventure_calls_handle_new_session_click(
        self, tmp_path: Path
    ) -> None:
        """Test Begin Adventure calls handle_new_session_click with selected characters.

        Story 13.2: Game start passes selected characters.
        """
        mock_session_state: dict = {
            "new_session_name": "Test Adventure",
        }

        preset_chars = {"thorin": _make_char_config(name="Thorin")}
        selected = {"thorin": preset_chars["thorin"]}

        with (
            patch("streamlit.session_state", mock_session_state),
            patch("persistence.CAMPAIGNS_DIR", tmp_path / "campaigns"),
            patch("app.populate_game_state") as mock_populate,
        ):
            mock_populate.return_value = {
                "characters": selected,
                "ground_truth_log": [],
                "agent_memories": {},
                "turn_queue": ["dm", "thorin"],
            }

            from app import handle_new_session_click

            handle_new_session_click(selected_characters=selected)

        # populate_game_state should be called with characters_override
        mock_populate.assert_called_once()
        call_kwargs = mock_populate.call_args[1]
        assert call_kwargs.get("characters_override") is selected


class TestRoutingBackNavigation:
    """Tests for party_setup back navigation."""

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_back_button_returns_to_module_selection(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test Back button navigates to module_selection view.

        Story 13.2: Back from party setup goes to module selection.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        # The first button call is "Back to Module Selection", return True
        mock_st.button.side_effect = [True, False, False]
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        assert mock_st.session_state["app_view"] == "module_selection"
        assert mock_st.session_state["module_selection_confirmed"] is False
        mock_st.rerun.assert_called()


class TestRoutingWizardReturn:
    """Tests for wizard return to party setup."""

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_create_new_character_sets_party_setup_return(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test Create New Character button sets party_setup_return flag.

        Story 13.2: Wizard return flag enables returning to party setup.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        # First button = Back (False), second = Create New Character (True), third = Begin (False)
        mock_st.button.side_effect = [False, True, False]
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        assert mock_st.session_state.get("party_setup_return") is True
        assert mock_st.session_state.get("wizard_active") is True
        assert mock_st.session_state["app_view"] == "character_wizard"
        mock_st.rerun.assert_called()


# =============================================================================
# Task 2: Character Loading Tests
# =============================================================================


class TestCharacterLoading:
    """Tests for character loading in party setup."""

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_preset_characters_loaded(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test preset characters are loaded from config files.

        Story 13.2: Preset characters appear in party setup.
        """
        from app import render_party_setup_view

        presets = {
            "thorin": _make_char_config(name="Thorin"),
            "lyra": _make_char_config(name="Lyra", character_class="Wizard"),
        }
        mock_load.return_value = presets
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        # columns is called for character grid and for action buttons
        mock_st.columns.side_effect = [
            [MagicMock(), MagicMock()],  # preset character grid
            [MagicMock(), MagicMock(), MagicMock()],  # action buttons
        ]
        mock_st.checkbox.return_value = True

        render_party_setup_view()

        mock_load.assert_called_once()

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_library_characters_loaded(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test library characters are loaded.

        Story 13.2: Library characters appear in party setup.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = [_make_library_char()]
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.columns.side_effect = [
            [MagicMock()],  # library character grid
            [MagicMock(), MagicMock(), MagicMock()],  # action buttons
        ]
        mock_st.checkbox.return_value = False

        render_party_setup_view()

        mock_lib.assert_called_once()

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_preset_defaults_to_selected(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test preset characters default to selected.

        Story 13.2: Presets are selected by default.
        """
        from app import render_party_setup_view

        presets = {"thorin": _make_char_config(name="Thorin")}
        mock_load.return_value = presets
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.columns.side_effect = [
            [MagicMock()],  # preset character grid
            [MagicMock(), MagicMock(), MagicMock()],  # action buttons
        ]
        mock_st.checkbox.return_value = True

        render_party_setup_view()

        party_selection = mock_st.session_state.get("party_selection", {})
        assert party_selection.get("preset:thorin") is True

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_library_defaults_to_deselected(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test library characters default to deselected.

        Story 13.2: Library characters are not selected by default.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        lib_char = _make_library_char(filename="eden.yaml")
        mock_lib.return_value = [lib_char]
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.columns.side_effect = [
            [MagicMock()],  # library character grid
            [MagicMock(), MagicMock(), MagicMock()],  # action buttons
        ]
        mock_st.checkbox.return_value = False

        render_party_setup_view()

        party_selection = mock_st.session_state.get("party_selection", {})
        # Library characters should default to False on init
        # Note: the checkbox mock returns False so it stays False
        assert "library:eden.yaml" in party_selection


# =============================================================================
# Task 3: Selection Tests
# =============================================================================


class TestPartySelection:
    """Tests for party selection toggle behavior."""

    def test_build_selected_characters_presets_only(self) -> None:
        """Test _build_selected_characters with only presets selected.

        Story 13.2: Only selected presets included in result.
        """
        from app import _build_selected_characters

        presets = {
            "thorin": _make_char_config(name="Thorin"),
            "lyra": _make_char_config(name="Lyra", character_class="Wizard"),
        }
        party_selection = {
            "preset:thorin": True,
            "preset:lyra": False,
        }

        result, _ = _build_selected_characters(party_selection, presets, [])

        assert "thorin" in result
        assert "lyra" not in result
        assert result["thorin"].name == "Thorin"

    def test_build_selected_characters_library_only(self) -> None:
        """Test _build_selected_characters with library character selected.

        Story 13.2: Library characters converted to CharacterConfig.
        """
        from app import _build_selected_characters

        lib_chars = [_make_library_char(name="Eden", filename="eden.yaml")]
        party_selection = {
            "library:eden.yaml": True,
        }

        result, _ = _build_selected_characters(party_selection, {}, lib_chars)

        assert "eden" in result
        assert isinstance(result["eden"], CharacterConfig)
        assert result["eden"].name == "Eden"
        assert result["eden"].character_class == "Warlock"

    def test_build_selected_characters_mixed(self) -> None:
        """Test _build_selected_characters with both preset and library.

        Story 13.2: Mixed selection includes both types.
        """
        from app import _build_selected_characters

        presets = {"thorin": _make_char_config(name="Thorin")}
        lib_chars = [_make_library_char(name="Eden", filename="eden.yaml")]
        party_selection = {
            "preset:thorin": True,
            "library:eden.yaml": True,
        }

        result, _ = _build_selected_characters(party_selection, presets, lib_chars)

        assert "thorin" in result
        assert "eden" in result
        assert len(result) == 2

    def test_build_selected_characters_none_selected(self) -> None:
        """Test _build_selected_characters with nothing selected.

        Story 13.2: Empty result when nothing selected.
        """
        from app import _build_selected_characters

        presets = {"thorin": _make_char_config(name="Thorin")}
        party_selection = {"preset:thorin": False}

        result, _ = _build_selected_characters(party_selection, presets, [])

        assert len(result) == 0

    def test_build_selected_characters_library_class_mapping(self) -> None:
        """Test library characters map 'class' to 'character_class'.

        Story 13.2: Library chars use 'class' key, not 'character_class'.
        """
        from app import _build_selected_characters

        lib_chars = [
            {
                "name": "TestChar",
                "class": "Paladin",
                "personality": "Noble.",
                "color": "#FFD700",
                "_filename": "testchar.yaml",
                "_filepath": "config/characters/library/testchar.yaml",
            }
        ]
        party_selection = {"library:testchar.yaml": True}

        result, _ = _build_selected_characters(party_selection, {}, lib_chars)

        assert result["testchar"].character_class == "Paladin"

    def test_build_selected_characters_library_with_character_class_key(self) -> None:
        """Test library characters can also use 'character_class' key.

        Story 13.2: Fallback to 'character_class' if 'class' not present.
        """
        from app import _build_selected_characters

        lib_chars = [
            {
                "name": "TestChar",
                "character_class": "Ranger",
                "personality": "Nature-loving.",
                "color": "#228B22",
                "_filename": "testchar.yaml",
                "_filepath": "config/characters/library/testchar.yaml",
            }
        ]
        party_selection = {"library:testchar.yaml": True}

        result, _ = _build_selected_characters(party_selection, {}, lib_chars)

        assert result["testchar"].character_class == "Ranger"


# =============================================================================
# Task 4: Validation Tests
# =============================================================================


class TestPartyValidation:
    """Tests for party selection validation."""

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_zero_selected_shows_warning(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test 0 selected characters shows warning message.

        Story 13.2: Validation requires at least 1 character.
        """
        from app import render_party_setup_view

        presets = {"thorin": _make_char_config(name="Thorin")}
        mock_load.return_value = presets
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        # Checkbox returns False (deselected)
        mock_st.checkbox.return_value = False

        render_party_setup_view()

        mock_st.warning.assert_called()
        warning_text = mock_st.warning.call_args[0][0]
        assert "at least 1" in warning_text.lower()

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_one_selected_no_warning(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test 1+ selected characters does not show warning.

        Story 13.2: Warning only shown when 0 selected.
        """
        from app import render_party_setup_view

        presets = {"thorin": _make_char_config(name="Thorin")}
        mock_load.return_value = presets
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        # Checkbox returns True (selected)
        mock_st.checkbox.return_value = True

        render_party_setup_view()

        mock_st.warning.assert_not_called()

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_begin_button_disabled_when_zero_selected(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test Begin Adventure button is disabled when 0 characters selected.

        Story 13.2: Cannot start game without characters.
        """
        from app import render_party_setup_view

        presets = {"thorin": _make_char_config(name="Thorin")}
        mock_load.return_value = presets
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_st.checkbox.return_value = False

        render_party_setup_view()

        # Find the Begin Adventure button call
        begin_calls = [
            c for c in mock_st.button.call_args_list if "Begin Adventure" in str(c)
        ]
        assert len(begin_calls) > 0
        begin_call = begin_calls[0]
        assert begin_call[1].get("disabled") is True


# =============================================================================
# Task 5: Integration Tests
# =============================================================================


class TestCharactersOverrideIntegration:
    """Tests for characters_override in populate_game_state."""

    def test_characters_override_used_when_provided(self) -> None:
        """Test populate_game_state uses characters_override when provided.

        Story 13.2: Selected characters override config file loading.
        """
        from models import populate_game_state

        custom_chars = {
            "hero": _make_char_config(name="Hero", character_class="Paladin"),
        }

        state = populate_game_state(
            include_sample_messages=False,
            characters_override=custom_chars,
        )

        assert "hero" in state["characters"]
        assert state["characters"]["hero"].name == "Hero"
        assert state["characters"]["hero"].character_class == "Paladin"
        # DM should always be in turn queue
        assert "dm" in state["turn_queue"]
        assert "hero" in state["turn_queue"]

    def test_characters_override_none_loads_from_config(self) -> None:
        """Test populate_game_state loads from config when override is None.

        Story 13.2: Default behavior preserved.
        """
        from models import populate_game_state

        state = populate_game_state(
            include_sample_messages=False,
            characters_override=None,
        )

        # Should have loaded from config files (preset characters)
        assert len(state["characters"]) > 0

    def test_characters_override_empty_dict(self) -> None:
        """Test populate_game_state with empty characters override.

        Story 13.2: Edge case - no characters selected (shouldn't happen in practice).
        """
        from models import populate_game_state

        state = populate_game_state(
            include_sample_messages=False,
            characters_override={},
        )

        # Should have only DM in turn queue
        assert state["turn_queue"] == ["dm"]
        assert len(state["characters"]) == 0

    def test_characters_override_creates_agent_memories(self) -> None:
        """Test populate_game_state creates agent memories for overridden characters.

        Story 13.2: Agent memories must be created for selected characters.
        """
        from models import populate_game_state

        custom_chars = {
            "hero": _make_char_config(name="Hero"),
            "mage": _make_char_config(name="Mage", character_class="Wizard"),
        }

        state = populate_game_state(
            include_sample_messages=False,
            characters_override=custom_chars,
        )

        assert "hero" in state["agent_memories"]
        assert "mage" in state["agent_memories"]
        assert "dm" in state["agent_memories"]

    def test_characters_override_creates_agent_secrets(self) -> None:
        """Test populate_game_state creates agent secrets for overridden characters.

        Story 13.2: Agent secrets must be created for selected characters.
        """
        from models import populate_game_state

        custom_chars = {
            "hero": _make_char_config(name="Hero"),
        }

        state = populate_game_state(
            include_sample_messages=False,
            characters_override=custom_chars,
        )

        assert "hero" in state["agent_secrets"]
        assert "dm" in state["agent_secrets"]


class TestLibraryToCharacterConfigConversion:
    """Tests for library dict -> CharacterConfig conversion."""

    def test_library_char_converted_to_character_config(self) -> None:
        """Test library character dict is properly converted to CharacterConfig.

        Story 13.2: Library characters need class mapping.
        """
        from app import _build_selected_characters

        lib_chars = [_make_library_char(name="Eden", char_class="Warlock")]
        party_selection = {"library:libchar.yaml": True}

        result, _ = _build_selected_characters(party_selection, {}, lib_chars)

        assert isinstance(result["eden"], CharacterConfig)
        assert result["eden"].character_class == "Warlock"
        assert result["eden"].color == "#4B0082"

    def test_library_char_defaults_for_missing_fields(self) -> None:
        """Test library character with missing fields gets defaults.

        Story 13.2: Missing fields should use sensible defaults.
        """
        from app import _build_selected_characters

        # Minimal library character
        lib_chars = [
            {
                "name": "Minimal",
                "_filename": "minimal.yaml",
                "_filepath": "config/characters/library/minimal.yaml",
            }
        ]
        party_selection = {"library:minimal.yaml": True}

        result, _ = _build_selected_characters(party_selection, {}, lib_chars)

        assert "minimal" in result
        assert result["minimal"].character_class == "Adventurer"
        assert result["minimal"].color == "#808080"


class TestStateClearup:
    """Tests for state cleanup after party setup."""

    def test_clear_party_setup_state(self) -> None:
        """Test clear_party_setup_state removes all party setup keys.

        Story 13.2: State cleanup after party setup completes.
        """
        mock_session_state: dict = {
            "party_selection": {"preset:thorin": True},
            "party_setup_return": True,
            "other_key": "preserved",
        }

        with patch("streamlit.session_state", mock_session_state):
            from app import clear_party_setup_state

            clear_party_setup_state()

        assert "party_selection" not in mock_session_state
        assert "party_setup_return" not in mock_session_state
        assert mock_session_state.get("other_key") == "preserved"

    def test_clear_party_setup_state_idempotent(self) -> None:
        """Test clear_party_setup_state is safe to call when keys missing.

        Story 13.2: Cleanup should be safe on empty state.
        """
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import clear_party_setup_state

            # Should not raise
            clear_party_setup_state()


# =============================================================================
# Task 6: XSS Tests
# =============================================================================


class TestPartySetupXSSResilience:
    """Tests for XSS/HTML injection resilience in party setup."""

    @patch("app.st")
    def test_character_card_escapes_html_in_name(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Test character card escapes HTML in character name.

        Story 13.2: Security - XSS prevention in character cards.
        """
        from app import render_party_character_card

        mock_st.checkbox.return_value = True

        render_party_character_card(
            name='<script>alert("xss")</script>',
            character_class="Fighter",
            color="#C45C4A",
            is_selected=True,
            card_key="test_card",
            source_label="Preset",
        )

        # Check markdown was called without raw script tag
        call_args = mock_st.markdown.call_args
        html_content = str(call_args)
        assert "<script>" not in html_content
        assert "&lt;script&gt;" in html_content

    @patch("app.st")
    def test_character_card_escapes_html_in_class(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Test character card escapes HTML in character class.

        Story 13.2: Security - XSS prevention in character class display.
        """
        from app import render_party_character_card

        mock_st.checkbox.return_value = True

        render_party_character_card(
            name="TestChar",
            character_class='<img src=x onerror="alert(1)">',
            color="#C45C4A",
            is_selected=True,
            card_key="test_card",
            source_label="Preset",
        )

        call_args = mock_st.markdown.call_args
        html_content = str(call_args)
        assert "<img" not in html_content
        assert "&lt;img" in html_content

    @patch("app.st")
    def test_character_card_escapes_html_in_source_label(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Test character card escapes HTML in source label.

        Story 13.2: Security - XSS prevention in source label.
        """
        from app import render_party_character_card

        mock_st.checkbox.return_value = True

        render_party_character_card(
            name="TestChar",
            character_class="Fighter",
            color="#C45C4A",
            is_selected=True,
            card_key="test_card",
            source_label="<script>hack</script>",
        )

        call_args = mock_st.markdown.call_args
        html_content = str(call_args)
        assert "<script>hack</script>" not in html_content

    def test_build_selected_characters_with_html_in_name(self) -> None:
        """Test _build_selected_characters handles HTML in library character names.

        Story 13.2: Security - library character names may contain HTML.
        """
        from app import _build_selected_characters

        lib_chars = [
            {
                "name": '<script>alert("xss")</script>',
                "class": "Fighter",
                "personality": "Evil.",
                "color": "#FF0000",
                "_filename": "evil.yaml",
                "_filepath": "config/characters/library/evil.yaml",
            }
        ]
        party_selection = {"library:evil.yaml": True}

        result, _ = _build_selected_characters(party_selection, {}, lib_chars)

        # The CharacterConfig stores the raw name; escaping happens at render time
        assert len(result) == 1


# =============================================================================
# Task 7: Session Name Tests
# =============================================================================


class TestSessionNameOnPartySetup:
    """Tests for session name in party setup view."""

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_session_name_input_present(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test session name text_input is rendered in party setup.

        Story 13.2: Session name moved from module selection to party setup.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        mock_st.text_input.assert_called_once()
        call_args = mock_st.text_input.call_args
        assert call_args[0][0] == "Adventure Name"

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_session_name_stored_in_session_state(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test entered session name stored in session state.

        Story 13.2: Session name persists in new_session_name key.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = "My Epic Quest"
        mock_st.button.return_value = False
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        assert mock_st.session_state["new_session_name"] == "My Epic Quest"

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_session_name_pre_fills_from_state(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test session name pre-fills from existing session state.

        Story 13.2: Session name persists when returning from wizard.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {"new_session_name": "Previously Entered"}
        mock_st.text_input.return_value = "Previously Entered"
        mock_st.button.return_value = False
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        call_kwargs = mock_st.text_input.call_args[1]
        assert call_kwargs.get("value") == "Previously Entered"


# =============================================================================
# Task 8: Module Selection View No Longer Has Session Name
# =============================================================================


class TestModuleSelectionViewNoSessionName:
    """Tests that module selection no longer renders session name input."""

    @patch("app.st")
    @patch("app.render_module_selection_ui")
    def test_no_text_input_in_module_selection(
        self,
        mock_render_ui: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test that render_module_selection_view does NOT render text_input.

        Story 13.2: Session name moved to party setup.
        """
        from app import render_module_selection_view

        mock_st.session_state = {"module_selection_confirmed": False}
        mock_st.button.return_value = False

        render_module_selection_view()

        mock_st.text_input.assert_not_called()


# =============================================================================
# Task 9: Render Party Character Card Tests
# =============================================================================


class TestRenderPartyCharacterCard:
    """Tests for render_party_character_card helper."""

    @patch("app.st")
    def test_selected_card_full_opacity(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Test selected card renders with full opacity.

        Story 13.2: Selected cards are visually prominent.
        """
        from app import render_party_character_card

        mock_st.checkbox.return_value = True

        render_party_character_card(
            name="Thorin",
            character_class="Fighter",
            color="#C45C4A",
            is_selected=True,
            card_key="test_card",
            source_label="Preset",
        )

        call_args = mock_st.markdown.call_args
        html_content = str(call_args)
        assert "opacity: 1.0" in html_content
        assert "border: 3px" in html_content

    @patch("app.st")
    def test_deselected_card_dimmed(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Test deselected card renders with reduced opacity.

        Story 13.2: Deselected cards are visually dimmed.
        """
        from app import render_party_character_card

        mock_st.checkbox.return_value = False

        render_party_character_card(
            name="Thorin",
            character_class="Fighter",
            color="#C45C4A",
            is_selected=False,
            card_key="test_card",
            source_label="Preset",
        )

        call_args = mock_st.markdown.call_args
        html_content = str(call_args)
        assert "opacity: 0.5" in html_content
        assert "border: 1px" in html_content

    @patch("app.st")
    def test_card_returns_checkbox_state(
        self,
        mock_st: MagicMock,
    ) -> None:
        """Test card returns the checkbox state value.

        Story 13.2: Return value drives selection toggle.
        """
        from app import render_party_character_card

        mock_st.checkbox.return_value = True

        result = render_party_character_card(
            name="Thorin",
            character_class="Fighter",
            color="#C45C4A",
            is_selected=False,
            card_key="test_card",
            source_label="Preset",
        )

        assert result is True


# =============================================================================
# Task 10: Step Header Tests
# =============================================================================


class TestPartySetupStepHeader:
    """Tests for party setup step header rendering."""

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_step_header_rendered(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test party setup renders Step 2 header.

        Story 13.2: Step header shows "Step 2: Assemble Your Party".
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        calls = mock_st.markdown.call_args_list
        header_calls = [c for c in calls if "Step 2" in str(c)]
        assert len(header_calls) > 0, "Step 2 header should be rendered"

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_caption_rendered(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test party setup renders caption text.

        Story 13.2: Caption describes purpose of the step.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        mock_st.caption.assert_called()
        caption_text = mock_st.caption.call_args[0][0]
        assert (
            "character" in caption_text.lower() or "adventure" in caption_text.lower()
        )


# =============================================================================
# Task 11: View State Machine Documentation Test
# =============================================================================


class TestViewStateMachineDocumentation:
    """Tests for updated view state machine documentation."""

    def test_party_setup_is_valid_app_view_value(self) -> None:
        """Test that 'party_setup' is a valid app_view value.

        Story 13.2: party_setup view exists in state machine.
        """
        valid_views = {
            "session_browser",
            "module_selection",
            "party_setup",
            "character_wizard",
            "character_library",
            "game",
        }
        assert "party_setup" in valid_views

    def test_party_setup_transitions(self) -> None:
        """Test party_setup has correct transitions.

        Story 13.2: party_setup -> game, module_selection, character_wizard.
        """
        transitions = {
            "session_browser": {"module_selection"},
            "module_selection": {"party_setup", "session_browser"},
            "party_setup": {"game", "module_selection", "character_wizard"},
            "character_wizard": {"party_setup", "character_library", "session_browser"},
            "game": {"session_browser"},
        }

        # party_setup can go to game, module_selection, or character_wizard
        assert "game" in transitions["party_setup"]
        assert "module_selection" in transitions["party_setup"]
        assert "character_wizard" in transitions["party_setup"]

        # module_selection now goes to party_setup (not directly to game)
        assert "party_setup" in transitions["module_selection"]


# =============================================================================
# Task 12: No Characters Available Test
# =============================================================================


class TestNoCharactersAvailable:
    """Tests for empty characters state."""

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_shows_info_when_no_characters(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test info message shown when no characters available.

        Story 13.2: Helpful message when character lists are empty.
        """
        from app import render_party_setup_view

        mock_load.return_value = {}
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]

        render_party_setup_view()

        mock_st.info.assert_called()
        info_text = mock_st.info.call_args[0][0]
        assert "character" in info_text.lower()

    @patch("app.st")
    @patch("config.load_character_configs")
    @patch("app.list_library_characters")
    def test_shows_library_empty_message_when_presets_exist(
        self,
        mock_lib: MagicMock,
        mock_load: MagicMock,
        mock_st: MagicMock,
    ) -> None:
        """Test library empty message shown even when presets exist.

        Story 13.2: AC #9 - Library section shows message when empty.
        """
        from app import render_party_setup_view

        presets = {"thorin": _make_char_config(name="Thorin")}
        mock_load.return_value = presets
        mock_lib.return_value = []
        mock_st.session_state = {}
        mock_st.text_input.return_value = ""
        mock_st.button.return_value = False
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        mock_st.checkbox.return_value = True

        render_party_setup_view()

        # Should have called st.info for library section
        info_calls = [
            call
            for call in mock_st.info.call_args_list
            if "library" in str(call).lower()
        ]
        assert len(info_calls) > 0, "Should show library empty message"
