"""Streamlit entry point for autodungeon.

This is the main application entry point. Run with:
    streamlit run app.py
"""

import re
from html import escape as escape_html
from pathlib import Path

import streamlit as st

from config import AppConfig, get_config, validate_api_keys
from models import CharacterConfig, GameState, populate_game_state

# Module-level compiled regex for action text styling
ACTION_PATTERN = re.compile(r"\*([^*]+)\*")


def load_css() -> str:
    """Load CSS from theme file.

    Returns:
        CSS content string, or empty string if file not found.
    """
    css_path = Path(__file__).parent / "styles" / "theme.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


def render_dm_message_html(content: str) -> str:
    """Generate HTML for DM narration message.

    Creates HTML structure with dm-message CSS class for gold border,
    italic Lora text styling per UX spec.

    Args:
        content: The DM narration text content.

    Returns:
        HTML string for the DM message div.
    """
    escaped_content = escape_html(content)
    return f'<div class="dm-message"><p>{escaped_content}</p></div>'


def render_dm_message(content: str) -> None:
    """Render DM narration message to Streamlit.

    Args:
        content: The DM narration text content.
    """
    st.markdown(render_dm_message_html(content), unsafe_allow_html=True)


def format_pc_content(content: str) -> str:
    """Format PC message content with action styling.

    Wraps *asterisk text* in <span class="action-text">.
    Content is HTML-escaped first, then action markers are converted.

    Args:
        content: Raw PC message content.

    Returns:
        HTML-safe content with action text styled.
    """
    escaped = escape_html(content)
    return ACTION_PATTERN.sub(r'<span class="action-text">\1</span>', escaped)


def render_pc_message_html(name: str, char_class: str, content: str) -> str:
    """Generate HTML for PC dialogue message.

    Creates HTML structure with pc-message CSS class and character-specific
    styling. Action text (*asterisk*) is wrapped in action-text spans.

    Args:
        name: Character display name (e.g., "Theron").
        char_class: Character class (e.g., "Fighter").
        content: The PC dialogue/action content.

    Returns:
        HTML string for the PC message div.
    """
    class_slug = char_class.lower()
    formatted_content = format_pc_content(content)
    return (
        f'<div class="pc-message {class_slug}">'
        f'<span class="pc-attribution {class_slug}">{escape_html(name)}, '
        f"the {escape_html(char_class)}:</span>"
        f"<p>{formatted_content}</p>"
        f"</div>"
    )


def render_pc_message(name: str, char_class: str, content: str) -> None:
    """Render PC dialogue message to Streamlit.

    Args:
        name: Character display name.
        char_class: Character class.
        content: The PC dialogue/action content.
    """
    st.markdown(
        render_pc_message_html(name, char_class, content),
        unsafe_allow_html=True,
    )


def render_character_card_html(
    name: str,
    char_class: str,
    controlled: bool = False,
) -> str:
    """Generate HTML for character card (testable without Streamlit).

    Args:
        name: Character display name (e.g., "Theron").
        char_class: Character class (e.g., "Fighter").
        controlled: Whether this character is currently controlled.

    Returns:
        HTML string for character card div.
    """
    # Escape class for CSS class attribute - only allow alphanumeric and hyphens
    class_slug = "".join(c for c in char_class.lower() if c.isalnum() or c == "-")
    controlled_class = " controlled" if controlled else ""
    return (
        f'<div class="character-card {class_slug}{controlled_class}">'
        f'<span class="character-name {class_slug}">{escape_html(name)}</span><br/>'
        f'<span class="character-class">{escape_html(char_class)}</span>'
        f"</div>"
    )


def get_drop_in_button_label(controlled: bool) -> str:
    """Get button label based on controlled state.

    Args:
        controlled: Whether this character is currently controlled.

    Returns:
        "Release" if controlled, "Drop-In" otherwise.
    """
    return "Release" if controlled else "Drop-In"


def get_party_characters(state: GameState) -> dict[str, CharacterConfig]:
    """Get party characters excluding DM.

    Args:
        state: Current game state with characters dict.

    Returns:
        Dict of agent_key -> CharacterConfig for PC characters only.
    """
    characters = state.get("characters", {})
    return {key: config for key, config in characters.items() if key != "dm"}


def get_character_info(state: GameState, agent_name: str) -> tuple[str, str] | None:
    """Get character info (name, class) for a PC agent.

    Args:
        state: Current game state with characters dict.
        agent_name: Agent key (e.g., "rogue", "fighter", "dm").

    Returns:
        (character_name, character_class) tuple, or None if DM.
    """
    if agent_name == "dm":
        return None  # DM uses implicit narrator styling
    char_config = state.get("characters", {}).get(agent_name)
    if char_config:
        return (char_config.name, char_config.character_class)
    return ("Unknown", "Adventurer")  # Fallback for unknown agents


def render_narrative_messages(state: GameState) -> None:
    """Render all messages from ground_truth_log.

    Iterates through the log, parses each entry, determines message type,
    and routes to appropriate renderer (DM or PC).

    Args:
        state: Current game state with ground_truth_log.
    """
    from models import parse_log_entry

    log = state.get("ground_truth_log", [])

    if not log:
        # Show placeholder when no messages
        st.markdown(
            '<p class="narrative-placeholder">'
            "The adventure awaits... Start a new game to begin."
            "</p>",
            unsafe_allow_html=True,
        )
        return

    for entry in log:
        message = parse_log_entry(entry)

        if message.message_type == "dm_narration":
            render_dm_message(message.content)
        else:
            # PC dialogue - look up character info
            char_info = get_character_info(state, message.agent)
            if char_info:
                name, char_class = char_info
            else:
                # Fallback for unknown agents
                name = message.agent.title()
                char_class = "Adventurer"
            render_pc_message(name, char_class, message.content)


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


def handle_drop_in_click(agent_key: str) -> None:
    """Handle Drop-In/Release button click.

    Toggles control of a character. If not controlling, takes control.
    If already controlling this character, releases control.

    Args:
        agent_key: The agent key (e.g., "fighter", "rogue").
    """
    controlled = st.session_state.get("controlled_character")
    if controlled == agent_key:
        # Release control
        st.session_state["controlled_character"] = None
        st.session_state["ui_mode"] = "watch"
    else:
        # Take control
        st.session_state["controlled_character"] = agent_key
        st.session_state["ui_mode"] = "play"


def render_character_card(
    agent_key: str, char_config: CharacterConfig, controlled: bool
) -> None:
    """Render a single character card with Drop-In button.

    Uses a wrapper div with character-specific classes to enable CSS targeting
    of both the card content and the Streamlit button that follows it.

    Args:
        agent_key: The agent key (e.g., "fighter", "rogue").
        char_config: CharacterConfig object with name and character_class.
        controlled: Whether this character is currently controlled.
    """
    # Get the class slug for CSS styling
    class_slug = "".join(
        c for c in char_config.character_class.lower() if c.isalnum() or c == "-"
    )
    controlled_class = " controlled" if controlled else ""

    # Open a wrapper div that will contain both the card info and the button
    # This wrapper has the character class for CSS targeting of child elements
    st.markdown(
        f'<div class="character-card-wrapper {class_slug}{controlled_class}">'
        f'<div class="character-card {class_slug}{controlled_class}">'
        f'<span class="character-name {class_slug}">'
        f"{escape_html(char_config.name)}</span><br/>"
        f'<span class="character-class">'
        f"{escape_html(char_config.character_class)}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Render the functional Streamlit button (styled via CSS targeting the wrapper)
    button_label = get_drop_in_button_label(controlled)
    if st.button(button_label, key=f"drop_in_{agent_key}"):
        handle_drop_in_click(agent_key)
        st.rerun()

    # Close the wrapper div
    st.markdown("</div>", unsafe_allow_html=True)


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

        # Party panel (Story 2.4)
        st.markdown("### Party")

        game: GameState = st.session_state.get("game", {})
        party_characters = get_party_characters(game)
        controlled_character = st.session_state.get("controlled_character")

        if party_characters:
            for agent_key, char_config in party_characters.items():
                is_controlled = controlled_character == agent_key
                render_character_card(agent_key, char_config, is_controlled)
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

    # Narrative container with messages (Story 2.3)
    st.markdown('<div class="narrative-container">', unsafe_allow_html=True)

    # Render messages from ground_truth_log
    game: GameState = st.session_state.get("game", {})
    render_narrative_messages(game)

    st.markdown("</div>", unsafe_allow_html=True)


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
