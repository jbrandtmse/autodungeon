"""Streamlit entry point for autodungeon.

This is the main application entry point. Run with:
    streamlit run app.py
"""

import re
import time
from datetime import date
from html import escape as escape_html
from pathlib import Path

import streamlit as st

from config import AppConfig, get_config, validate_api_keys
from graph import run_single_round
from models import CharacterConfig, GameState, populate_game_state

# Speed delay mappings for playback control
SPEED_DELAYS: dict[str, float] = {
    "slow": 3.0,  # 3 seconds between turns
    "normal": 1.0,  # 1 second between turns
    "fast": 0.2,  # 200ms between turns (near-instant)
}

# Module-level compiled regex for action text styling
ACTION_PATTERN = re.compile(r"\*([^*]+)\*")

# Roman numeral mappings for session numbers
_ROMAN_VALUES = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
_ROMAN_SYMBOLS = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]


def get_turn_delay() -> float:
    """Get delay in seconds based on playback_speed setting.

    Returns:
        Delay in seconds: 3.0 for slow, 1.0 for normal, 0.2 for fast.
    """
    speed = st.session_state.get("playback_speed", "normal")
    return SPEED_DELAYS.get(speed, 1.0)


def get_is_watching() -> bool:
    """Check if the game is in Watch Mode.

    Watch Mode is active when:
    - ui_mode is "watch" AND
    - human_active is False

    Returns:
        True if in Watch Mode, False if in Play Mode.
    """
    ui_mode = st.session_state.get("ui_mode", "watch")
    human_active = st.session_state.get("human_active", False)
    return ui_mode == "watch" and not human_active


def is_autopilot_available() -> bool:
    """Check if autopilot can be started.

    Autopilot can start when:
    - Game exists (has been initialized)
    - Not paused
    - Not already in human control mode

    Returns:
        True if autopilot can start, False otherwise.
    """
    if "game" not in st.session_state:
        return False
    if st.session_state.get("is_paused", False):
        return False
    if st.session_state.get("human_active", False):
        return False
    return True


def run_game_turn() -> bool:
    """Execute one game turn and update session state.

    Runs one complete round via run_single_round(), managing the
    is_generating flag, respecting pause state, and applying speed delay.

    For human-controlled characters:
    - If it's the human's turn and no pending action, skip (wait for input)
    - If pending action exists, process it through the graph

    Returns:
        True if turn was executed, False if skipped (paused/waiting for human).
    """
    if st.session_state.get("is_paused", False):
        return False

    # Check if we should wait for human input
    if st.session_state.get("human_active", False):
        game = st.session_state.get("game", {})
        current_turn = game.get("current_turn", "")
        controlled = st.session_state.get("controlled_character", "")

        # If it's the controlled character's turn and no pending action, wait
        if current_turn == controlled:
            if not st.session_state.get("human_pending_action"):
                st.session_state["waiting_for_human"] = True
                return False

    # Clear waiting flag since we're proceeding
    st.session_state["waiting_for_human"] = False

    # Set generating flag
    st.session_state["is_generating"] = True

    try:
        # Get current game state
        game = st.session_state.get("game", {})

        # Execute one round
        updated_state = run_single_round(game)

        # Update session state
        st.session_state["game"] = updated_state

        # Apply speed-based delay between turns
        delay = get_turn_delay()
        if delay > 0:
            time.sleep(delay)

        return True
    finally:
        st.session_state["is_generating"] = False


# Default maximum turns per session to prevent infinite loops
DEFAULT_MAX_TURNS_PER_SESSION = 100


def run_continuous_loop(max_turns: int = DEFAULT_MAX_TURNS_PER_SESSION) -> int:
    """Execute game turns continuously until stopped.

    Runs turns in a loop until one of these conditions is met:
    - is_paused becomes True
    - human_active becomes True
    - is_autopilot_running becomes False
    - max_turns limit is reached

    This function uses st.rerun() pattern: it executes ONE turn,
    then triggers a rerun if autopilot should continue. This respects
    Streamlit's architecture and allows UI updates between turns.

    Args:
        max_turns: Maximum turns before auto-stopping (safety limit).

    Returns:
        Number of turns executed (always 0 or 1 in Streamlit model).
    """
    # Check if autopilot should run
    if not st.session_state.get("is_autopilot_running", False):
        return 0

    # Check stopping conditions
    if st.session_state.get("is_paused", False):
        st.session_state["is_autopilot_running"] = False
        return 0

    if st.session_state.get("human_active", False):
        st.session_state["is_autopilot_running"] = False
        return 0

    # Check turn limit
    turn_count = st.session_state.get("autopilot_turn_count", 0)
    if turn_count >= max_turns:
        st.session_state["is_autopilot_running"] = False
        return 0

    # Execute one turn
    if run_game_turn():
        # Increment turn count
        st.session_state["autopilot_turn_count"] = turn_count + 1
        # Continue autopilot on next rerun
        st.rerun()

    return 1


def run_autopilot_step() -> None:
    """Execute one step of autopilot and trigger rerun if continuing.

    This is the main autopilot driver. Call this during page render
    to check if autopilot is active and execute the next turn.

    Pattern:
    1. If autopilot not running, return immediately
    2. Check stopping conditions (pause, human active)
    3. Execute one turn via run_game_turn()
    4. Trigger st.rerun() to continue loop

    This respects Streamlit's execution model while providing
    continuous turn execution.
    """
    if not st.session_state.get("is_autopilot_running", False):
        return

    # Check stopping conditions
    if st.session_state.get("is_paused", False):
        st.session_state["is_autopilot_running"] = False
        return

    if st.session_state.get("human_active", False):
        st.session_state["is_autopilot_running"] = False
        return

    # Check turn limit safety
    turn_count = st.session_state.get("autopilot_turn_count", 0)
    max_turns = st.session_state.get(
        "max_turns_per_session", DEFAULT_MAX_TURNS_PER_SESSION
    )
    if turn_count >= max_turns:
        st.session_state["is_autopilot_running"] = False
        return

    # Execute one turn
    if run_game_turn():
        # Increment turn count
        st.session_state["autopilot_turn_count"] = turn_count + 1
        # Continue autopilot on next rerun
        st.rerun()


def load_css() -> str:
    """Load CSS from theme file.

    Returns:
        CSS content string, or empty string if file not found.
    """
    css_path = Path(__file__).parent / "styles" / "theme.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


def int_to_roman(num: int) -> str:
    """Convert integer to Roman numeral string.

    Args:
        num: Integer to convert (1-3999).

    Returns:
        Roman numeral string.

    Raises:
        ValueError: If num is out of valid range.
    """
    if not 1 <= num <= 3999:
        raise ValueError(f"Number {num} out of range (1-3999)")

    result = ""
    for i, v in enumerate(_ROMAN_VALUES):
        while num >= v:
            result += _ROMAN_SYMBOLS[i]
            num -= v
    return result


def render_session_header_html(session_number: int, session_info: str) -> str:
    """Generate HTML for session header with roman numeral.

    Args:
        session_number: Session number (1-3999).
        session_info: Subtitle text (e.g., "January 27, 2026 • Turn 15").

    Returns:
        HTML string for session header.
    """
    roman = int_to_roman(session_number)
    return (
        '<div class="session-header">'
        f'<h1 class="session-title">Session {escape_html(roman)}</h1>'
        f'<p class="session-subtitle">{escape_html(session_info)}</p>'
        "</div>"
    )


def get_session_subtitle(game: GameState) -> str:
    """Generate session subtitle text.

    Args:
        game: Current game state.

    Returns:
        Formatted subtitle string with date and optional turn count.
    """
    today = date.today().strftime("%B %d, %Y")
    turn_count = len(game.get("ground_truth_log", []))

    if turn_count > 0:
        return f"{today} • Turn {turn_count}"
    return today


def render_auto_scroll_indicator_html(auto_scroll_enabled: bool) -> str:
    """Generate HTML for auto-scroll resume indicator.

    Args:
        auto_scroll_enabled: Whether auto-scroll is currently enabled.

    Returns:
        HTML string for indicator when disabled, empty string when enabled.
    """
    if auto_scroll_enabled:
        return ""

    return '<div class="auto-scroll-indicator visible">↓ Resume auto-scroll</div>'


def handle_resume_auto_scroll_click() -> None:
    """Handle click on resume auto-scroll indicator."""
    st.session_state["auto_scroll_enabled"] = True


def handle_pause_auto_scroll_click() -> None:
    """Handle pause auto-scroll (when user scrolls up manually)."""
    st.session_state["auto_scroll_enabled"] = False


def render_auto_scroll_indicator() -> None:
    """Render auto-scroll resume indicator when auto-scroll is paused."""
    auto_scroll_enabled = st.session_state.get("auto_scroll_enabled", True)

    html = render_auto_scroll_indicator_html(auto_scroll_enabled)
    if html:
        st.markdown(html, unsafe_allow_html=True)
        if st.button("Resume", key="resume_auto_scroll_btn"):
            handle_resume_auto_scroll_click()
            st.rerun()


def get_auto_scroll_script() -> str:
    """Generate JavaScript for auto-scroll behavior.

    Returns:
        JavaScript code string that scrolls narrative container to bottom.
    """
    return """
        <script>
        (function() {
            // Find the narrative container in parent document
            const container = parent.document.querySelector('.narrative-container');
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        })();
        </script>
    """


def inject_auto_scroll_script() -> None:
    """Inject JavaScript for auto-scroll behavior.

    Scrolls the narrative container to the bottom when auto_scroll_enabled
    is True. Uses st.components.v1.html for reliable script execution.
    """
    import streamlit.components.v1 as components

    auto_scroll_enabled = st.session_state.get("auto_scroll_enabled", True)

    if auto_scroll_enabled:
        components.html(get_auto_scroll_script(), height=0)


def get_keyboard_shortcut_script() -> str:
    """Generate JavaScript for keyboard shortcut handling.

    Handles:
    - Keys 1-4: Drop-in as party member
    - Escape: Release character control

    Shortcuts are disabled when focus is on input/textarea elements.

    Returns:
        JavaScript code string for keyboard event handling.
    """
    return """
        <script>
        (function() {
            // Only attach once
            if (window._autodungeonKeyboardListenerAttached) return;
            window._autodungeonKeyboardListenerAttached = true;

            document.addEventListener('keydown', function(e) {
                // Skip if typing in input/textarea/select or contenteditable element
                const activeElement = document.activeElement;
                const tagName = activeElement ? activeElement.tagName.toLowerCase() : '';
                if (tagName === 'input' || tagName === 'textarea' || tagName === 'select') {
                    return;
                }
                // Also skip if element has contenteditable attribute
                if (activeElement && activeElement.getAttribute('contenteditable') === 'true') {
                    return;
                }

                // Handle number keys 1-4 for drop-in
                if (e.key >= '1' && e.key <= '4') {
                    e.preventDefault();
                    const index = parseInt(e.key) - 1;
                    // Update URL with action parameter
                    const url = new URL(window.location);
                    url.searchParams.set('keyboard_action', 'drop_in_' + index);
                    window.location.href = url.toString();
                    return;
                }

                // Handle Escape for release
                if (e.key === 'Escape') {
                    e.preventDefault();
                    const url = new URL(window.location);
                    url.searchParams.set('keyboard_action', 'release');
                    window.location.href = url.toString();
                    return;
                }
            });
        })();
        </script>
    """


def inject_keyboard_shortcut_script() -> None:
    """Inject JavaScript for keyboard shortcut handling.

    Adds event listeners for:
    - 1-4 keys: Quick drop-in to party members
    - Escape: Release character control
    """
    import streamlit.components.v1 as components

    components.html(get_keyboard_shortcut_script(), height=0)


def get_party_character_keys() -> list[str]:
    """Get ordered list of party character keys.

    Returns party member agent keys in consistent order for keyboard mapping.

    Returns:
        List of agent keys (e.g., ["fighter", "rogue", "wizard", "cleric"]).
    """
    game: GameState = st.session_state.get("game", {})
    party_chars = get_party_characters(game)
    return list(party_chars.keys())


def handle_keyboard_drop_in(party_index: int) -> None:
    """Handle keyboard drop-in for party member by index.

    Maps keyboard key (1-4) to party member index (0-3).

    Args:
        party_index: Zero-based index of party member.
    """
    party_keys = get_party_character_keys()

    if 0 <= party_index < len(party_keys):
        agent_key = party_keys[party_index]
        handle_drop_in_click(agent_key)


def handle_keyboard_release() -> None:
    """Handle keyboard release (Escape key).

    Releases control of current character and returns to watch mode.
    Only acts if currently controlling a character.
    """
    controlled = st.session_state.get("controlled_character")
    if controlled:
        handle_drop_in_click(controlled)  # Toggle off


def process_keyboard_action() -> bool:
    """Process pending keyboard action from URL query params.

    Checks for 'keyboard_action' query param and processes it:
    - 'drop_in_N': Drop in as Nth party member (0-indexed)
    - 'release': Release current character

    Returns:
        True if action was processed, False otherwise.
    """
    params = st.query_params
    action = params.get("keyboard_action")

    if not action:
        return False

    # Clear the action param to prevent re-triggering
    del st.query_params["keyboard_action"]

    if action.startswith("drop_in_"):
        try:
            index = int(action.split("_")[-1])
            handle_keyboard_drop_in(index)
            return True
        except ValueError:
            return False

    if action == "release":
        handle_keyboard_release()
        return True

    return False


def render_keyboard_shortcuts_help_html() -> str:
    """Generate HTML for keyboard shortcuts help text.

    Returns:
        HTML string with keyboard shortcut hints.
    """
    return (
        '<div class="keyboard-shortcuts-help">'
        '<span class="help-text">Press </span>'
        "<kbd>1</kbd><kbd>2</kbd><kbd>3</kbd><kbd>4</kbd>"
        '<span class="help-text"> to drop in, </span>'
        "<kbd>Esc</kbd>"
        '<span class="help-text"> to release</span>'
        "</div>"
    )


def render_keyboard_shortcuts_help() -> None:
    """Render keyboard shortcuts help in sidebar."""
    st.markdown(render_keyboard_shortcuts_help_html(), unsafe_allow_html=True)


def render_thinking_indicator_html(is_generating: bool, is_paused: bool) -> str:
    """Generate HTML for thinking indicator (pure function).

    The indicator has a 500ms CSS delay before appearing, per NFR3.

    Args:
        is_generating: Whether the LLM is currently generating a response.
        is_paused: Whether game playback is paused.

    Returns:
        HTML string for thinking indicator, or empty string if not needed.
    """
    if not is_generating or is_paused:
        return ""

    return (
        '<div class="thinking-indicator">'
        '<span class="thinking-dot"></span>'
        '<span class="thinking-text">The story unfolds...</span>'
        "</div>"
    )


def render_thinking_indicator() -> None:
    """Render thinking indicator to Streamlit when generating.

    Shows a "The story unfolds..." indicator with a 500ms CSS delay,
    per NFR3 requirement for spinner appearance after delay.
    """
    is_generating = st.session_state.get("is_generating", False)
    is_paused = st.session_state.get("is_paused", False)

    html = render_thinking_indicator_html(is_generating, is_paused)
    if html:
        st.markdown(html, unsafe_allow_html=True)


def render_mode_indicator_html(
    ui_mode: str,
    is_generating: bool,
    controlled_character: str | None = None,
    characters: dict[str, CharacterConfig] | None = None,
    is_paused: bool = False,
) -> str:
    """Generate HTML for mode indicator badge.

    In watch mode, the pulse dot is always visible to indicate the game
    is ready and observing (AC #1: pulsing green dot).

    States (in priority order):
    - Paused: Static amber dot + "Paused" (highest priority, Story 3.5)
    - Watch: Pulsing green dot + "Watching"
    - Play: Pulsing character-color dot + "Playing as [Name]"

    Args:
        ui_mode: "watch" or "play"
        is_generating: Whether story is actively generating (unused in watch mode)
        controlled_character: Agent key of controlled character, or None
        characters: Dict of agent_key -> CharacterConfig
        is_paused: Whether game playback is paused (Story 3.5 AC #1)

    Returns:
        HTML string for mode indicator.
    """
    # Paused state takes priority (Story 3.5 AC #1)
    if is_paused:
        return '<div class="mode-indicator paused"><span class="pause-dot"></span>Paused</div>'

    if ui_mode == "watch":
        # Always show pulse dot in watch mode (AC #1: pulsing green dot)
        pulse_html = '<span class="pulse-dot"></span>'
        return f'<div class="mode-indicator watch">{pulse_html}Watching</div>'
    else:
        # Play mode - show character name with character color
        # Pulse dot always shown in play mode (active player control indicator)
        characters = characters or {}
        char_config = characters.get(controlled_character or "")
        if char_config:
            name = char_config.name
            class_slug = char_config.character_class.lower()
        else:
            name = controlled_character or "Unknown"
            class_slug = ""

        return (
            f'<div class="mode-indicator play {class_slug}">'
            f'<span class="pulse-dot"></span>Playing as {escape_html(name)}</div>'
        )


def render_nudge_input_html() -> str:
    """Generate HTML for nudge input label and hint.

    Returns:
        HTML string for nudge input container.
    """
    return (
        '<div class="nudge-input-container">'
        '<div class="nudge-label">Suggest Something</div>'
        '<p class="nudge-hint">Whisper a suggestion to the DM...</p>'
        "</div>"
    )


def render_nudge_input() -> None:
    """Render nudge input in the sidebar.

    Only visible in Watch Mode (when not controlling a character).
    Shows a text area for suggestions and a submit button.
    """
    if st.session_state.get("human_active"):
        return  # Don't show nudge if already controlling a character

    st.markdown(render_nudge_input_html(), unsafe_allow_html=True)

    nudge = st.text_area(
        "Nudge input",
        key="nudge_input",
        placeholder="e.g., 'The rogue should check for traps'",
        label_visibility="collapsed",
        height=60,
    )

    if st.button("Send Nudge", key="nudge_submit_btn", use_container_width=True):
        handle_nudge_submit(nudge)
        # Clear the input field by deleting its key from session_state
        # This ensures the text area is empty on the next render (AC #4)
        if "nudge_input" in st.session_state:
            del st.session_state["nudge_input"]
        st.rerun()

    # Show confirmation toast
    if st.session_state.get("nudge_submitted"):
        st.success("Nudge sent - the DM will consider your suggestion", icon="✨")
        st.session_state["nudge_submitted"] = False


def render_input_context_bar_html(name: str, char_class: str) -> str:
    """Generate HTML for input context bar.

    Shows "You are [Name], the [Class]" with character-colored left border.
    Displayed above the human input area when controlling a character.

    Args:
        name: Character display name (e.g., "Shadowmere").
        char_class: Character class (e.g., "Rogue").

    Returns:
        HTML string for context bar.
    """
    class_slug = char_class.lower()
    return (
        f'<div class="input-context {class_slug}">'
        f'<span class="input-context-text">You are </span>'
        f'<span class="input-context-character">{escape_html(name)}</span>'
        f'<span class="input-context-text">, the {escape_html(char_class)}</span>'
        "</div>"
    )


def render_dm_message_html(content: str, is_current: bool = False) -> str:
    """Generate HTML for DM narration message.

    Creates HTML structure with dm-message CSS class for gold border,
    italic Lora text styling per UX spec.

    Args:
        content: The DM narration text content.
        is_current: If True, adds current-turn class for highlight animation.

    Returns:
        HTML string for the DM message div.
    """
    escaped_content = escape_html(content)
    current_class = " current-turn" if is_current else ""
    return f'<div class="dm-message{current_class}"><p>{escaped_content}</p></div>'


def render_dm_message(content: str, is_current: bool = False) -> None:
    """Render DM narration message to Streamlit.

    Args:
        content: The DM narration text content.
        is_current: If True, adds current-turn class for highlight animation.
    """
    st.markdown(render_dm_message_html(content, is_current), unsafe_allow_html=True)


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


def render_pc_message_html(
    name: str, char_class: str, content: str, is_current: bool = False
) -> str:
    """Generate HTML for PC dialogue message.

    Creates HTML structure with pc-message CSS class and character-specific
    styling. Action text (*asterisk*) is wrapped in action-text spans.

    Args:
        name: Character display name (e.g., "Theron").
        char_class: Character class (e.g., "Fighter").
        content: The PC dialogue/action content.
        is_current: If True, adds current-turn class for highlight animation.

    Returns:
        HTML string for the PC message div.
    """
    class_slug = char_class.lower()
    current_class = " current-turn" if is_current else ""
    formatted_content = format_pc_content(content)
    return (
        f'<div class="pc-message {class_slug}{current_class}">'
        f'<span class="pc-attribution {class_slug}">{escape_html(name)}, '
        f"the {escape_html(char_class)}:</span>"
        f"<p>{formatted_content}</p>"
        f"</div>"
    )


def render_pc_message(
    name: str, char_class: str, content: str, is_current: bool = False
) -> None:
    """Render PC dialogue message to Streamlit.

    Args:
        name: Character display name.
        char_class: Character class.
        content: The PC dialogue/action content.
        is_current: If True, adds current-turn class for highlight animation.
    """
    st.markdown(
        render_pc_message_html(name, char_class, content, is_current),
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


def get_start_button_label(game: GameState) -> str:
    """Get button label based on game state.

    Args:
        game: Current game state.

    Returns:
        "Start Game" if no messages, "Next Turn" otherwise.
    """
    log = game.get("ground_truth_log", [])
    return "Start Game" if len(log) == 0 else "Next Turn"


def is_start_button_disabled() -> bool:
    """Check if start/next turn button should be disabled.

    Returns:
        True if button should be disabled (game is generating).
    """
    return st.session_state.get("is_generating", False)


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
    and routes to appropriate renderer (DM or PC). The last message receives
    a current-turn highlight class for visual emphasis.

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

    last_index = len(log) - 1

    for i, entry in enumerate(log):
        message = parse_log_entry(entry)
        is_current = i == last_index

        if message.message_type == "dm_narration":
            render_dm_message(message.content, is_current)
        else:
            # PC dialogue - look up character info
            char_info = get_character_info(state, message.agent)
            if char_info:
                name, char_class = char_info
            else:
                # Fallback for unknown agents
                name = message.agent.title()
                char_class = "Adventurer"
            render_pc_message(name, char_class, message.content, is_current)


def initialize_session_state() -> None:
    """Initialize game state in session state if not present."""
    if "game" not in st.session_state:
        st.session_state["game"] = populate_game_state()
        st.session_state["ui_mode"] = "watch"
        st.session_state["controlled_character"] = None
        st.session_state["human_active"] = False  # Explicit initialization (Story 3.1)
        st.session_state["is_generating"] = False
        st.session_state["is_paused"] = False
        st.session_state["playback_speed"] = "normal"
        st.session_state["auto_scroll_enabled"] = True
        st.session_state["is_autopilot_running"] = False
        st.session_state["autopilot_turn_count"] = 0
        st.session_state["max_turns_per_session"] = DEFAULT_MAX_TURNS_PER_SESSION
        # Human intervention state (Story 3.2)
        st.session_state["human_pending_action"] = None
        st.session_state["waiting_for_human"] = False
        # Nudge system state (Story 3.4)
        st.session_state["pending_nudge"] = None
        st.session_state["nudge_submitted"] = False
        # Config modal auto-pause state (Story 3.5)
        st.session_state["modal_open"] = False
        st.session_state["pre_modal_pause_state"] = False


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


def handle_pause_toggle() -> None:
    """Toggle the pause state for game playback."""
    st.session_state["is_paused"] = not st.session_state.get("is_paused", False)


def handle_modal_open() -> None:
    """Handle config modal opening - auto-pause game.

    Stores current pause state to restore on close (Story 3.5 AC #6).
    This is a placeholder for future Epic 6 config modal integration.
    """
    # Store current pause state before auto-pausing
    st.session_state["pre_modal_pause_state"] = st.session_state.get("is_paused", False)
    st.session_state["is_paused"] = True
    st.session_state["modal_open"] = True


def handle_modal_close() -> None:
    """Handle config modal closing - restore previous pause state.

    Restores the pause state from before modal was opened (Story 3.5 AC #6).
    This is a placeholder for future Epic 6 config modal integration.
    """
    st.session_state["modal_open"] = False
    # Restore previous pause state
    prev_state = st.session_state.get("pre_modal_pause_state", False)
    st.session_state["is_paused"] = prev_state


def handle_autopilot_toggle() -> None:
    """Toggle autopilot state.

    When starting autopilot:
    - Sets is_autopilot_running to True
    - Resets autopilot_turn_count to 0

    When stopping autopilot:
    - Sets is_autopilot_running to False
    """
    current = st.session_state.get("is_autopilot_running", False)
    if current:
        # Stop autopilot
        st.session_state["is_autopilot_running"] = False
    else:
        # Start autopilot
        st.session_state["is_autopilot_running"] = True
        st.session_state["autopilot_turn_count"] = 0


def render_autopilot_toggle() -> None:
    """Render autopilot start/stop toggle button.

    Shows a button to start or stop autopilot mode.
    Disabled when human is controlling a character.
    """
    is_running = st.session_state.get("is_autopilot_running", False)
    human_active = st.session_state.get("human_active", False)

    # Disable if human is controlling
    disabled = human_active

    button_label = "⏹ Stop Autopilot" if is_running else "▶ Start Autopilot"

    if st.button(button_label, key="autopilot_toggle", disabled=disabled):
        handle_autopilot_toggle()
        st.rerun()


def render_session_controls() -> None:
    """Render session playback controls in the sidebar.

    Includes Autopilot toggle, Pause/Resume button, and Speed control dropdown.
    These controls enable Watch Mode and Human Participation (Epic 3).
    """
    st.markdown('<div class="session-controls">', unsafe_allow_html=True)
    st.markdown("### Session Controls")

    # Autopilot toggle (Story 3.1)
    render_autopilot_toggle()

    # Pause/Resume button
    is_paused = st.session_state.get("is_paused", False)
    button_label = "Resume" if is_paused else "Pause"
    if st.button(button_label, key="pause_resume_btn"):
        handle_pause_toggle()
        st.rerun()

    # Speed control dropdown
    speed_options = ["Slow", "Normal", "Fast"]
    current_speed = st.session_state.get("playback_speed", "normal")
    # Convert internal value to display value
    speed_display = current_speed.capitalize()
    default_index = (
        speed_options.index(speed_display) if speed_display in speed_options else 1
    )

    selected_speed = st.selectbox(
        "Speed",
        speed_options,
        index=default_index,
        key="session_speed_select",
    )

    # Update session state if speed changed and trigger rerun for consistency
    if selected_speed and selected_speed.lower() != current_speed:
        st.session_state["playback_speed"] = selected_speed.lower()
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def handle_drop_in_click(agent_key: str) -> None:
    """Handle Drop-In/Release button click.

    Toggles control of a character. If not controlling, takes control.
    If already controlling this character, releases control.

    When taking control (Drop-In):
    - Stops autopilot if running
    - Sets human_active to True
    - Updates controlled_character and ui_mode

    When releasing control:
    - Clears human_active
    - Clears controlled_character
    - Returns to watch mode

    Args:
        agent_key: The agent key (e.g., "fighter", "rogue").
    """
    controlled = st.session_state.get("controlled_character")
    if controlled == agent_key:
        # Release control - clear any pending action
        st.session_state["controlled_character"] = None
        st.session_state["ui_mode"] = "watch"
        st.session_state["human_active"] = False
        st.session_state["human_pending_action"] = None
        st.session_state["waiting_for_human"] = False
    else:
        # Take control - stop autopilot first
        st.session_state["is_autopilot_running"] = False
        # Clear any pending state from previous character (character switching)
        st.session_state["human_pending_action"] = None
        st.session_state["waiting_for_human"] = False
        # Set new controlled character
        st.session_state["controlled_character"] = agent_key
        st.session_state["ui_mode"] = "play"
        st.session_state["human_active"] = True


# Maximum action text length for safety
MAX_ACTION_LENGTH = 2000

# Maximum nudge text length (Story 3.4)
MAX_NUDGE_LENGTH = 1000


def handle_nudge_submit(nudge: str) -> None:
    """Handle submission of nudge suggestion.

    Stores the nudge in session state for the DM's next turn context.
    Shows confirmation toast and clears input.

    Args:
        nudge: The user's suggestion text.
    """
    sanitized = nudge.strip()[:MAX_NUDGE_LENGTH]

    if sanitized:
        st.session_state["pending_nudge"] = sanitized
        st.session_state["nudge_submitted"] = True


def handle_human_action_submit(action: str) -> None:
    """Handle submission of human action.

    Stores the submitted action in session state for processing
    by the human_intervention_node in the game loop.

    Args:
        action: The user's action text.
    """
    # Limit action length for safety
    sanitized = action.strip()[:MAX_ACTION_LENGTH]

    if sanitized:
        st.session_state["human_pending_action"] = sanitized


def render_input_context_bar(controlled_character: str | None = None) -> None:
    """Render input context bar showing which character the human controls.

    Only renders when ui_mode="play" and controlled_character is set.
    Shows "You are [Name], the [Class]" with character-colored styling.

    Args:
        controlled_character: Agent key of controlled character, or None.
    """
    if st.session_state.get("ui_mode") != "play":
        return

    controlled = controlled_character or st.session_state.get("controlled_character")
    if not controlled:
        return

    game: GameState = st.session_state.get("game", {})
    characters = game.get("characters", {})
    char_config = characters.get(controlled)

    if char_config:
        html = render_input_context_bar_html(
            char_config.name, char_config.character_class
        )
        st.markdown(html, unsafe_allow_html=True)


def render_human_input_area() -> None:
    """Render text input and submit button for human actions.

    Only renders when ui_mode="play" and controlled_character is set.
    Includes the input context bar above the text input.
    """
    if st.session_state.get("ui_mode") != "play":
        return

    controlled = st.session_state.get("controlled_character")
    if not controlled:
        return

    # Render context bar first
    render_input_context_bar(controlled)

    # Wrap input area in styled container
    st.markdown('<div class="human-input-area">', unsafe_allow_html=True)

    # Text input area
    action = st.text_area(
        "Your action:",
        key="human_action_input",
        placeholder="What does your character do? (e.g., 'I check the door for traps.')",
        label_visibility="collapsed",
    )

    # Submit button (disabled while generating)
    is_generating = st.session_state.get("is_generating", False)
    if st.button("Send", key="human_action_submit", disabled=is_generating):
        if action and action.strip():
            handle_human_action_submit(action.strip())
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


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
    # Disabled during generation for UX consistency (Story 3.3 code review fix)
    button_label = get_drop_in_button_label(controlled)
    is_generating = st.session_state.get("is_generating", False)
    if st.button(button_label, key=f"drop_in_{agent_key}", disabled=is_generating):
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
        # Mode indicator with dynamic Watching/Playing/Paused states (Story 2.5, 3.5)
        ui_mode = st.session_state.get("ui_mode", "watch")
        is_generating = st.session_state.get("is_generating", False)
        is_paused = st.session_state.get("is_paused", False)
        controlled_character = st.session_state.get("controlled_character")
        game: GameState = st.session_state.get("game", {})
        characters = game.get("characters", {})

        st.markdown(
            render_mode_indicator_html(
                ui_mode, is_generating, controlled_character, characters, is_paused
            ),
            unsafe_allow_html=True,
        )

        st.markdown("---")

        # Party panel (Story 2.4)
        st.markdown("### Party")

        party_characters = get_party_characters(game)

        if party_characters:
            for agent_key, char_config in party_characters.items():
                is_controlled = controlled_character == agent_key
                render_character_card(agent_key, char_config, is_controlled)
        else:
            st.caption("No characters loaded")

        # Keyboard shortcuts help (Story 3.6)
        render_keyboard_shortcuts_help()

        st.markdown("---")

        # Session controls (Story 2.5)
        render_session_controls()

        st.markdown("---")

        # Nudge System (Story 3.4)
        render_nudge_input()

        st.markdown("---")

        # Configuration status (condensed, moved from main area) (2.5)
        with st.expander("LLM Status", expanded=False):
            st.markdown(get_api_key_status(config))

            # Show warnings for missing API keys
            warnings = validate_api_keys(config)
            if warnings:
                for warning in warnings:
                    st.warning(warning, icon="⚠️")


def handle_start_game_click() -> None:
    """Handle Start Game / Next Turn button click.

    Executes one game turn and triggers a rerun to update the UI.
    """
    if run_game_turn():
        st.rerun()


def render_game_controls() -> None:
    """Render game control buttons (Start Game / Next Turn).

    Displays a button to trigger game execution. Button label changes
    based on whether the game has started, and is disabled during
    LLM generation.
    """
    game: GameState = st.session_state.get("game", {})
    label = get_start_button_label(game)
    disabled = is_start_button_disabled()

    st.markdown('<div class="game-controls">', unsafe_allow_html=True)

    if st.button(label, key="start_game_btn", disabled=disabled):
        handle_start_game_click()

    # Show thinking indicator when generating
    render_thinking_indicator()

    st.markdown("</div>", unsafe_allow_html=True)


def render_main_content() -> None:
    """Render the main narrative area with session header and narrative container."""
    # Get game state for dynamic session header
    game: GameState = st.session_state.get("game", {})

    # Session header with dynamic session number (Story 2.5)
    session_number = game.get("session_number", 1)
    session_info = get_session_subtitle(game)
    st.markdown(
        render_session_header_html(session_number, session_info),
        unsafe_allow_html=True,
    )

    # Game controls (Start Game / Next Turn button) (Story 2.6)
    render_game_controls()

    # Narrative container with messages (Story 2.3, 2.6)
    st.markdown('<div class="narrative-container">', unsafe_allow_html=True)

    # Render messages from ground_truth_log
    render_narrative_messages(game)

    # Auto-scroll indicator for resuming after manual scroll (Story 2.6)
    render_auto_scroll_indicator()

    st.markdown("</div>", unsafe_allow_html=True)

    # Inject auto-scroll JavaScript when enabled (Story 2.6)
    inject_auto_scroll_script()

    # Human input area - only shown in play mode (Story 3.2)
    render_human_input_area()


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

    # Process keyboard actions early (before render) (Story 3.6)
    if process_keyboard_action():
        st.rerun()

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

    # Inject keyboard shortcut script (Story 3.6)
    inject_keyboard_shortcut_script()

    # Run autopilot step if active (Story 3.1)
    # This executes at end of render to trigger next turn
    run_autopilot_step()


if __name__ == "__main__":
    main()
