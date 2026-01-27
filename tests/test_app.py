"""Tests for Streamlit app entry point."""

import os
from pathlib import Path
from unittest.mock import patch


class TestAppEntryPoint:
    """Tests for app.py functionality."""

    def test_app_loads_config(self) -> None:
        """Test that the app module can load configuration."""
        from config import get_config

        config = get_config()
        assert config is not None
        assert hasattr(config, "default_provider")

    def test_get_api_key_status_all_missing(self) -> None:
        """Test API key status when all keys are missing."""
        with patch.dict(os.environ, {}, clear=True):
            from app import get_api_key_status
            from config import AppConfig

            config = AppConfig()
            status = get_api_key_status(config)

            assert "Gemini" in status
            assert "Claude" in status
            assert "Ollama" in status
            # All should show as not configured or available (Ollama has default URL)

    def test_get_api_key_status_with_keys(self) -> None:
        """Test API key status when keys are set."""
        with patch.dict(
            os.environ,
            {
                "GOOGLE_API_KEY": "test-google-key",
                "ANTHROPIC_API_KEY": "test-anthropic-key",
            },
            clear=False,
        ):
            from app import get_api_key_status
            from config import AppConfig

            config = AppConfig()
            status = get_api_key_status(config)

            # Should indicate keys are configured
            assert "Gemini" in status
            assert "Claude" in status


class TestCSSThemeFile:
    """Tests for CSS theme file (Task 5.1)."""

    def test_css_file_exists(self) -> None:
        """Test that styles/theme.css exists."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        assert css_path.exists(), f"CSS file not found at {css_path}"

    def test_css_contains_required_variables(self) -> None:
        """Test that CSS file contains required CSS variables."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Background colors from UX spec
        assert "--bg-primary: #1A1612" in css_content
        assert "--bg-secondary: #2D2520" in css_content
        assert "--bg-message: #3D3530" in css_content

        # Text colors
        assert "--text-primary: #F5E6D3" in css_content
        assert "--text-secondary: #B8A896" in css_content

        # Accent
        assert "--accent-warm: #E8A849" in css_content

        # Character identity colors
        assert "--color-dm: #D4A574" in css_content
        assert "--color-fighter: #C45C4A" in css_content
        assert "--color-rogue: #6B8E6B" in css_content
        assert "--color-wizard: #7B68B8" in css_content
        assert "--color-cleric: #4A90A4" in css_content

        # Font stacks
        assert "--font-narrative:" in css_content
        assert "'Lora'" in css_content
        assert "--font-ui:" in css_content
        assert "'Inter'" in css_content
        assert "--font-mono:" in css_content

        # Font sizes
        assert "--text-dm: 18px" in css_content
        assert "--text-pc: 17px" in css_content
        assert "--text-name: 14px" in css_content
        assert "--text-ui: 14px" in css_content
        assert "--text-system: 13px" in css_content

    def test_css_contains_sidebar_width(self) -> None:
        """Test that CSS file contains 240px sidebar width rule (Task 5.3)."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check for sidebar width variable
        assert "--sidebar-width: 240px" in css_content

        # Check for actual usage in sidebar styling
        assert "width: var(--sidebar-width)" in css_content

    def test_css_contains_viewport_warning(self) -> None:
        """Test that CSS file contains viewport warning styles for <1024px."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check for viewport warning class
        assert ".viewport-warning" in css_content

        # Check for media query at 1023px breakpoint
        assert "@media (max-width: 1023px)" in css_content


class TestLoadCss:
    """Tests for load_css function."""

    def test_load_css_returns_content(self) -> None:
        """Test that load_css returns CSS content when file exists."""
        from app import load_css

        css = load_css()
        assert css, "CSS content should not be empty"
        assert "--bg-primary" in css, "CSS should contain CSS variables"

    def test_load_css_empty_when_no_file(self) -> None:
        """Test that load_css returns empty string when file doesn't exist."""
        from app import load_css

        with patch("pathlib.Path.exists", return_value=False):
            css = load_css()
            assert css == "", "Should return empty string when file not found"


class TestSessionStateInitialization:
    """Tests for session state initialization (Task 5.2)."""

    def test_initialize_session_state_creates_game(self) -> None:
        """Test that initialize_session_state creates GameState."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            assert "game" in mock_session_state
            game = mock_session_state["game"]

            # Verify GameState structure
            assert "ground_truth_log" in game
            assert "turn_queue" in game
            assert "current_turn" in game
            assert "agent_memories" in game
            assert "game_config" in game
            assert "dm_config" in game
            assert "characters" in game
            assert "human_active" in game
            assert "controlled_character" in game

    def test_initialize_session_state_sets_ui_mode(self) -> None:
        """Test that initialize_session_state sets ui_mode to 'watch'."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            assert mock_session_state["ui_mode"] == "watch"

    def test_initialize_session_state_sets_controlled_character(self) -> None:
        """Test that initialize_session_state sets controlled_character to None."""
        mock_session_state: dict = {}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            assert mock_session_state["controlled_character"] is None

    def test_initialize_session_state_idempotent(self) -> None:
        """Test that initialize_session_state doesn't overwrite existing game."""
        mock_session_state = {"game": {"existing": True}}

        with patch("streamlit.session_state", mock_session_state):
            from app import initialize_session_state

            initialize_session_state()

            # Should NOT overwrite existing game
            assert mock_session_state["game"] == {"existing": True}

    def test_populate_game_state_loads_characters(self) -> None:
        """Test that populate_game_state loads characters from config."""
        from models import populate_game_state

        game = populate_game_state()

        # Should have DM in turn_queue
        assert "dm" in game["turn_queue"]

        # Should have agent memories for DM
        assert "dm" in game["agent_memories"]

        # Current turn should start with DM
        assert game["current_turn"] == "dm"


class TestDMMessageStyling:
    """Tests for DM message CSS styling (Story 2.2, Task 1)."""

    def test_dm_message_class_exists(self) -> None:
        """Test that .dm-message class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".dm-message" in css_content

    def test_dm_message_has_gold_border(self) -> None:
        """Test that DM message has gold border-left."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check DM message uses --color-dm variable for border
        assert "var(--color-dm)" in css_content

    def test_dm_message_has_italic_text(self) -> None:
        """Test that DM message uses italic font style."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "font-style: italic" in css_content

    def test_dm_message_uses_lora_font(self) -> None:
        """Test that DM message uses Lora font for narrative feel."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Check dm-message section uses font-narrative (Lora)
        assert "var(--font-narrative)" in css_content

    def test_dm_message_border_width_is_4px(self) -> None:
        """Test that DM message has 4px border-left per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Find the .dm-message block and verify 4px border
        assert "border-left: 4px solid var(--color-dm)" in css_content

    def test_dm_message_p_has_italic_and_justify(self) -> None:
        """Test that .dm-message p has italic text and justify alignment."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Verify both properties exist (they should be in .dm-message p block)
        assert "font-style: italic" in css_content
        assert "text-align: justify" in css_content


class TestPCMessageStyling:
    """Tests for PC message CSS styling (Story 2.2, Task 1)."""

    def test_pc_message_class_exists(self) -> None:
        """Test that .pc-message class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".pc-message" in css_content

    def test_pc_message_character_classes_exist(self) -> None:
        """Test that PC message classes exist for all characters."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        for char in ["fighter", "rogue", "wizard", "cleric"]:
            assert f".pc-message.{char}" in css_content, f"Missing .pc-message.{char}"

    def test_pc_attribution_class_exists(self) -> None:
        """Test that .pc-attribution class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".pc-attribution" in css_content

    def test_pc_attribution_character_classes_exist(self) -> None:
        """Test that PC attribution classes exist for all characters."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        for char in ["fighter", "rogue", "wizard", "cleric"]:
            assert f".pc-attribution.{char}" in css_content, (
                f"Missing .pc-attribution.{char}"
            )

    def test_action_text_class_exists(self) -> None:
        """Test that action text styling class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".action-text" in css_content


class TestSessionHeaderStyling:
    """Tests for session header CSS styling (Story 2.2, Task 2)."""

    def test_session_title_class_exists(self) -> None:
        """Test that .session-title class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".session-title" in css_content

    def test_session_subtitle_class_exists(self) -> None:
        """Test that .session-subtitle class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".session-subtitle" in css_content

    def test_session_title_has_gold_color(self) -> None:
        """Test that session title uses DM gold color per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Session title should use --color-dm (gold)
        assert "color: var(--color-dm)" in css_content

    def test_session_title_has_24px_font(self) -> None:
        """Test that session title uses 24px font size per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "font-size: 24px" in css_content

    def test_session_header_has_border_bottom(self) -> None:
        """Test that session header has border-bottom separator."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "border-bottom: 1px solid var(--bg-secondary)" in css_content


class TestCharacterCardEnhancement:
    """Tests for enhanced character card CSS styling (Story 2.2, Task 3)."""

    def test_character_card_character_classes_exist(self) -> None:
        """Test that character card classes exist for all characters."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        for char in ["fighter", "rogue", "wizard", "cleric"]:
            assert f".character-card.{char}" in css_content, (
                f"Missing .character-card.{char}"
            )

    def test_character_card_controlled_state(self) -> None:
        """Test that controlled state class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-card.controlled" in css_content

    def test_character_name_class_exists(self) -> None:
        """Test that .character-name class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".character-name" in css_content


class TestDropInButtonStyling:
    """Tests for Drop-In button CSS styling (Story 2.2, Task 4)."""

    def test_drop_in_button_class_exists(self) -> None:
        """Test that .drop-in-button class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".drop-in-button" in css_content

    def test_drop_in_button_hover_state(self) -> None:
        """Test that Drop-In button has hover state."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".drop-in-button:hover" in css_content

    def test_drop_in_button_active_state(self) -> None:
        """Test that Drop-In button has active state."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".drop-in-button.active" in css_content

    def test_drop_in_button_character_classes(self) -> None:
        """Test that Drop-In button has character-specific classes."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        for char in ["fighter", "rogue", "wizard", "cleric"]:
            assert f".drop-in-button.{char}" in css_content, (
                f"Missing .drop-in-button.{char}"
            )


class TestModeIndicatorEnhancement:
    """Tests for enhanced mode indicator CSS styling (Story 2.2, Task 5)."""

    def test_mode_indicator_watch_class(self) -> None:
        """Test that .mode-indicator.watch class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".mode-indicator.watch" in css_content

    def test_mode_indicator_play_class(self) -> None:
        """Test that .mode-indicator.play class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".mode-indicator.play" in css_content

    def test_pulse_animation_defined(self) -> None:
        """Test that pulse animation keyframes are defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "@keyframes pulse" in css_content

    def test_pulse_dot_class_exists(self) -> None:
        """Test that .pulse-dot class is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".pulse-dot" in css_content

    def test_mode_indicator_watch_has_green_background(self) -> None:
        """Test that watch mode has green-tinted background per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Watch mode should use green (rogue color) with transparency
        assert "rgba(107, 142, 107, 0.2)" in css_content

    def test_mode_indicator_play_has_amber_background(self) -> None:
        """Test that play mode has amber-tinted background per UX spec."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        # Play mode should use amber with transparency
        assert "rgba(232, 168, 73, 0.2)" in css_content

    def test_pulse_dot_uses_animation(self) -> None:
        """Test that pulse-dot uses the pulse animation."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "animation: pulse 2s ease-in-out infinite" in css_content


class TestStreamlitWidgetOverrides:
    """Tests for Streamlit widget theme overrides (Story 2.2, Task 6)."""

    def test_text_input_styling(self) -> None:
        """Test that text input styling is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".stTextInput" in css_content

    def test_text_area_styling(self) -> None:
        """Test that text area styling is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".stTextArea" in css_content

    def test_button_styling(self) -> None:
        """Test that button styling is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".stButton" in css_content

    def test_selectbox_styling(self) -> None:
        """Test that selectbox styling is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert ".stSelectbox" in css_content

    def test_expander_styling(self) -> None:
        """Test that expander styling is defined."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "expanderHeader" in css_content


class TestFontsImport:
    """Tests for font imports (Story 2.2, Task 7)."""

    def test_lora_font_imported(self) -> None:
        """Test that Lora font is imported."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "Lora" in css_content
        assert "@import" in css_content
        assert "fonts.googleapis.com" in css_content

    def test_inter_font_imported(self) -> None:
        """Test that Inter font is imported."""
        css_path = Path(__file__).parent.parent / "styles" / "theme.css"
        css_content = css_path.read_text(encoding="utf-8")

        assert "Inter" in css_content
