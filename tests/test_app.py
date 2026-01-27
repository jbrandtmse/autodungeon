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
