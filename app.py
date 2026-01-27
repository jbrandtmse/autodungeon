"""Streamlit entry point for autodungeon.

This is the main application entry point. Run with:
    streamlit run app.py
"""

from pathlib import Path

import streamlit as st

from config import AppConfig, get_config, validate_api_keys
from models import GameState, populate_game_state


def load_css() -> str:
    """Load CSS from theme file.

    Returns:
        CSS content string, or empty string if file not found.
    """
    css_path = Path(__file__).parent / "styles" / "theme.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


def initialize_session_state() -> None:
    """Initialize game state in session state if not present."""
    if "game" not in st.session_state:
        st.session_state["game"] = populate_game_state()
        st.session_state["ui_mode"] = "watch"
        st.session_state["controlled_character"] = None


def get_api_key_status(config: AppConfig) -> str:
    """Generate a formatted string showing API key configuration status.

    Args:
        config: The application configuration.

    Returns:
        Formatted string showing which API keys are configured.
    """
    lines: list[str] = []

    # Google/Gemini status
    if config.google_api_key:
        lines.append("- Gemini: Configured")
    else:
        lines.append("- Gemini: Not configured")

    # Anthropic/Claude status
    if config.anthropic_api_key:
        lines.append("- Claude: Configured")
    else:
        lines.append("- Claude: Not configured")

    # Ollama status (always has a default URL)
    lines.append("- Ollama: Available")

    return "\n".join(lines)


def render_sidebar(config: AppConfig) -> None:
    """Render the sidebar with mode indicator, party panel, and config status.

    Args:
        config: The application configuration.
    """
    with st.sidebar:
        # Mode indicator placeholder (4.1)
        ui_mode = st.session_state.get("ui_mode", "watch")
        mode_label = "Watch Mode" if ui_mode == "watch" else "Play Mode"
        mode_class = "watch" if ui_mode == "watch" else "play"
        st.markdown(
            f'<div class="mode-indicator {mode_class}">'
            f'<span class="pulse-dot"></span>{mode_label}</div>',
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Party panel placeholder (4.2)
        st.markdown("### Party")

        game: GameState = st.session_state.get("game", {})
        characters = game.get("characters", {})

        if characters:
            for _char_name, char_config in characters.items():
                # Convert class to lowercase slug for CSS class matching
                class_slug = char_config.character_class.lower()
                st.markdown(
                    f'<div class="character-card {class_slug}">'
                    f'<span class="character-name {class_slug}">'
                    f"{char_config.name}</span><br/>"
                    f'<span class="character-class">'
                    f"{char_config.character_class}</span>"
                    f'<button class="drop-in-button {class_slug}">Drop-In</button>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No characters loaded")

        st.markdown("---")

        # Configuration status (condensed, moved from main area) (2.5)
        with st.expander("LLM Status", expanded=False):
            st.markdown(get_api_key_status(config))

            # Show warnings for missing API keys
            warnings = validate_api_keys(config)
            if warnings:
                for warning in warnings:
                    st.warning(warning, icon="⚠️")


def render_main_content() -> None:
    """Render the main narrative area with session header and narrative container."""
    # Session header placeholder (4.3)
    st.markdown(
        '<div class="session-header">'
        '<h1 class="session-title">Session I</h1>'
        '<p class="session-subtitle">Game will begin when started</p>'
        "</div>",
        unsafe_allow_html=True,
    )

    # Narrative container placeholder (4.4)
    st.markdown(
        '<div class="narrative-container">'
        '<p class="narrative-placeholder">'
        "The adventure awaits... Start a new game to begin."
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_viewport_warning() -> None:
    """Render the viewport warning message for narrow screens."""
    st.markdown(
        '<div class="viewport-warning">'
        "<h2>Viewport Too Narrow</h2>"
        "<p>Please use a wider browser window for the best experience</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    """Main Streamlit application entry point."""
    # Page config (kept from existing - 2.1)
    st.set_page_config(
        page_title="autodungeon",
        page_icon="🎲",
        layout="wide",
    )

    # CSS injection (2.2)
    css = load_css()
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    # Viewport warning for narrow screens (AC #5)
    render_viewport_warning()

    # Initialize session state (Task 3)
    initialize_session_state()

    # Load configuration
    config = get_config()

    # Wrap content in app-content div for responsive hiding
    st.markdown('<div class="app-content">', unsafe_allow_html=True)

    # Title
    st.title("autodungeon")
    st.caption("Multi-agent D&D game engine")

    # Render sidebar (Task 2.3, 2.5, 4.1, 4.2)
    render_sidebar(config)

    # Main narrative area (Task 2.4, 4.3, 4.4)
    render_main_content()

    # Close app-content div
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
