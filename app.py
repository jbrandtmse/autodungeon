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

from config import (
    MINIMUM_TOKEN_LIMIT,
    AppConfig,
    get_api_key_source,
    get_available_models,
    get_config,
    get_effective_api_key,
    get_model_max_context,
    mask_api_key,
    validate_anthropic_api_key,
    validate_api_keys,
    validate_google_api_key,
    validate_ollama_connection,
)
from graph import run_single_round
from models import (
    CharacterConfig,
    DMConfig,
    GameConfig,
    GameState,
    SessionMetadata,
    UserError,
    ValidationResult,
    populate_game_state,
)
from persistence import (
    create_new_session,
    generate_recap_summary,
    get_latest_checkpoint,
    get_transcript_download_data,
    get_transcript_path,
    list_sessions,
    list_sessions_with_metadata,
    load_checkpoint,
)

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

    Error handling (Story 4.5):
    - If run_single_round returns an error, stores it in session state
    - Stops autopilot when error occurs
    - Does NOT update game state with corrupted data

    Returns:
        True if turn was executed successfully, False if skipped/error.
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
        result = run_single_round(game)

        # Check for error in result (Story 4.5)
        error = result.get("error")
        if error is not None and isinstance(error, UserError):
            # Store error in session state for display
            st.session_state["error"] = error
            # Stop autopilot on error (AC #7 of integration tests)
            st.session_state["is_autopilot_running"] = False
            # Do NOT update game state with potentially corrupted data
            return False

        # No error - update session state with new game state
        # Remove error key if present before storing as GameState
        if "error" in result:
            del result["error"]
        st.session_state["game"] = result

        # Clear any previous error on successful turn
        st.session_state["error"] = None
        # Reset retry count on success
        st.session_state["error_retry_count"] = 0

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


def render_summarization_indicator_html(summarization_in_progress: bool) -> str:
    """Generate HTML for summarization indicator (pure function).

    Shows a subtle indicator when memory compression is running.
    Uses campfire theme styling.

    Args:
        summarization_in_progress: Whether summarization is currently running.

    Returns:
        HTML string for summarization indicator, or empty string if not needed.
    """
    if not summarization_in_progress:
        return ""

    return (
        '<div class="summarization-indicator">'
        '<span class="summarization-text">Compressing memories...</span>'
        "</div>"
    )


def render_summarization_indicator() -> None:
    """Render summarization indicator to Streamlit when active.

    Shows a brief text indicator when memory compression is running.
    Only renders if game state has summarization_in_progress=True.
    """
    game: GameState = st.session_state.get("game", {})
    summarization_in_progress = game.get("summarization_in_progress", False)

    html = render_summarization_indicator_html(summarization_in_progress)
    if html:
        st.markdown(html, unsafe_allow_html=True)


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
    # App view routing (Story 4.3)
    if "app_view" not in st.session_state:
        # Default to session browser if sessions exist, otherwise start new session
        sessions = list_sessions()
        st.session_state["app_view"] = "session_browser" if sessions else "game"

    # Recap state (Story 4.3)
    if "show_recap" not in st.session_state:
        st.session_state["show_recap"] = False
        st.session_state["recap_text"] = ""
        st.session_state["current_session_id"] = None

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
        # Config modal state (Story 6.1)
        st.session_state["config_modal_open"] = False
        st.session_state["config_has_changes"] = False
        st.session_state["config_original_values"] = None
        st.session_state["show_discard_confirmation"] = False
        # API key management state (Story 6.2)
        st.session_state["api_key_overrides"] = {}
        st.session_state["api_key_status_google"] = None
        st.session_state["api_key_status_anthropic"] = None
        st.session_state["api_key_status_ollama"] = None
        st.session_state["api_key_validating_google"] = False
        st.session_state["api_key_validating_anthropic"] = False
        st.session_state["api_key_validating_ollama"] = False
        st.session_state["ollama_available_models"] = []
        st.session_state["show_api_key_google"] = False
        st.session_state["show_api_key_anthropic"] = False
        st.session_state["show_api_key_ollama"] = False
        # Error handling state (Story 4.5)
        st.session_state["error"] = None
        st.session_state["error_retry_count"] = 0


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


def handle_config_modal_open() -> None:
    """Handle config modal opening - auto-pause game (Story 6.1 AC #3).

    Stores current pause state to restore on close.
    Stops autopilot if running.
    Takes a snapshot of current config values for change detection.
    """
    # Store current pause state before auto-pausing
    st.session_state["pre_modal_pause_state"] = st.session_state.get("is_paused", False)
    st.session_state["is_paused"] = True
    st.session_state["config_modal_open"] = True

    # Stop autopilot if running (Story 6.1 Task 4.3)
    st.session_state["is_autopilot_running"] = False

    # Take snapshot of config values for change detection (Story 6.1 Task 6.2)
    st.session_state["config_original_values"] = snapshot_config_values()
    st.session_state["config_has_changes"] = False
    st.session_state["show_discard_confirmation"] = False


def handle_config_modal_close(save_changes: bool = False) -> None:
    """Handle config modal closing - restore previous pause state (Story 6.1 AC #4).

    Restores the pause state from before modal was opened.
    Applies changes if save_changes is True.

    Args:
        save_changes: If True, apply any pending config changes before closing.
    """
    st.session_state["config_modal_open"] = False
    st.session_state["show_discard_confirmation"] = False

    # Restore previous pause state
    prev_state = st.session_state.get("pre_modal_pause_state", False)
    st.session_state["is_paused"] = prev_state

    # Clear change tracking state
    st.session_state["config_has_changes"] = False
    st.session_state["config_original_values"] = None


def snapshot_config_values() -> dict[str, dict[str, str] | dict[str, dict[str, str]]]:
    """Take snapshot of current config values when modal opens.

    Returns:
        Dict containing current config values for change detection.
        Includes API key overrides from Story 6.2 and model overrides from Story 6.3.
    """
    # Get current API key overrides from session state
    api_overrides = st.session_state.get("api_key_overrides", {})

    # Get current agent model overrides from session state (Story 6.3)
    model_overrides = st.session_state.get("agent_model_overrides", {})

    # Get current token limit overrides from session state (Story 6.4)
    token_limit_overrides = st.session_state.get("token_limit_overrides", {})

    return {
        "api_keys": {
            "google": api_overrides.get("google", ""),
            "anthropic": api_overrides.get("anthropic", ""),
            "ollama": api_overrides.get("ollama", ""),
        },
        "models": dict(model_overrides),  # Story 6.3 - copy current overrides
        "settings": {
            "token_limits": dict(token_limit_overrides),  # Story 6.4
        },
    }


def has_unsaved_changes() -> bool:
    """Check if config modal has unsaved changes (Story 6.1 Task 6.1).

    Compares current config values against snapshot taken when modal opened.

    Returns:
        True if there are unsaved changes, False otherwise.
    """
    return st.session_state.get("config_has_changes", False)


def mark_config_changed() -> None:
    """Mark that config has unsaved changes (Story 6.1 Task 6.2).

    Call this when any config field is modified in the modal.
    """
    st.session_state["config_has_changes"] = True


# Legacy aliases for backward compatibility
def handle_modal_open() -> None:
    """Legacy alias for handle_config_modal_open.

    Also sets modal_open for backward compatibility with existing code/tests.
    """
    handle_config_modal_open()
    # Set legacy key for backward compatibility
    st.session_state["modal_open"] = True


def handle_modal_close() -> None:
    """Legacy alias for handle_config_modal_close.

    Also clears modal_open for backward compatibility with existing code/tests.
    """
    handle_config_modal_close()
    # Clear legacy key for backward compatibility
    st.session_state["modal_open"] = False


# =============================================================================
# Configuration Modal (Story 6.1)
# =============================================================================


# =============================================================================
# API Key Management UI (Story 6.2)
# =============================================================================

# Provider display configuration
PROVIDER_CONFIG = {
    "google": {
        "label": "Google (Gemini)",
        "env_var": "GOOGLE_API_KEY",
        "help": "Required for Gemini models",
        "placeholder": "Enter your Google API key...",
        "is_password": True,
    },
    "anthropic": {
        "label": "Anthropic (Claude)",
        "env_var": "ANTHROPIC_API_KEY",
        "help": "Required for Claude models",
        "placeholder": "Enter your Anthropic API key...",
        "is_password": True,
    },
    "ollama": {
        "label": "Ollama Base URL",
        "env_var": "OLLAMA_BASE_URL",
        "help": "Local Ollama server URL",
        "placeholder": "http://localhost:11434",
        "is_password": False,
    },
}


def render_validation_status_html(status: str, message: str, provider: str) -> str:
    """Generate HTML for validation status display.

    Args:
        status: Validation status (untested, validating, valid, invalid).
        message: Status message to display.
        provider: Provider name for key prefixing.

    Returns:
        HTML string for validation status.
    """
    if status == "untested":
        return (
            '<div class="api-key-status untested">'
            '<span class="api-key-status-icon">?</span>'
            '<span class="api-key-status-text">Not tested</span>'
            "</div>"
        )
    elif status == "validating":
        return (
            '<div class="api-key-status validating">'
            '<span class="api-key-status-spinner"></span>'
            '<span class="api-key-status-text">Validating...</span>'
            "</div>"
        )
    elif status == "valid":
        return (
            '<div class="api-key-status valid">'
            '<span class="api-key-status-icon">&#10003;</span>'
            f'<span class="api-key-status-text">{escape_html(message)}</span>'
            "</div>"
        )
    else:  # invalid
        return (
            '<div class="api-key-status invalid">'
            '<span class="api-key-status-icon">&#10007;</span>'
            f'<span class="api-key-status-text">{escape_html(message)}</span>'
            "</div>"
        )


def handle_api_key_change(provider: str, value: str) -> None:
    """Handle API key field change with validation trigger.

    Stores the new value in session state and triggers validation.

    Args:
        provider: Provider name (google, anthropic, ollama).
        value: New field value.
    """
    # Store the new value in overrides
    if "api_key_overrides" not in st.session_state:
        st.session_state["api_key_overrides"] = {}
    st.session_state["api_key_overrides"][provider] = value

    # Mark config as changed
    mark_config_changed()

    # Clear previous validation status when value changes
    st.session_state[f"api_key_status_{provider}"] = None

    # Skip validation if empty
    if not value.strip():
        return

    # Set validating flag (will trigger spinner on rerun)
    st.session_state[f"api_key_validating_{provider}"] = True


def run_api_key_validation(provider: str, value: str) -> None:
    """Run validation for an API key and store result.

    Args:
        provider: Provider name (google, anthropic, ollama).
        value: Value to validate.
    """
    if not value.strip():
        st.session_state[f"api_key_validating_{provider}"] = False
        return

    try:
        match provider:
            case "google":
                result = validate_google_api_key(value)
            case "anthropic":
                result = validate_anthropic_api_key(value)
            case "ollama":
                result = validate_ollama_connection(value)
                # Store available models for Ollama
                if result.models is not None:
                    st.session_state["ollama_available_models"] = result.models
            case _:
                result = ValidationResult(
                    valid=False, message="Unknown provider", models=None
                )

        st.session_state[f"api_key_status_{provider}"] = result
    except Exception as e:
        st.session_state[f"api_key_status_{provider}"] = ValidationResult(
            valid=False, message=f"Error: {str(e)[:40]}", models=None
        )
    finally:
        st.session_state[f"api_key_validating_{provider}"] = False


def render_api_key_field(provider: str) -> None:
    """Render an API key input field with validation status.

    Handles three states:
    - Empty: Shows placeholder prompting for input
    - Environment: Shows "Set via environment" with masked preview
    - UI Override: Shows user-entered value with validation status

    Args:
        provider: Provider name (google, anthropic, ollama).
    """
    pconfig = PROVIDER_CONFIG.get(provider, {})
    label = str(pconfig.get("label", provider.title()))
    help_text = str(pconfig.get("help", ""))
    placeholder = str(pconfig.get("placeholder", ""))
    is_password = bool(pconfig.get("is_password", True))

    # Get current values
    overrides = st.session_state.get("api_key_overrides", {})
    source = get_api_key_source(provider, overrides)
    effective_value = get_effective_api_key(provider, overrides)
    current_override = overrides.get(provider, "")

    # Render field container (provider sanitized for HTML attribute safety)
    safe_provider = escape_html(provider)
    st.markdown(
        f'<div class="api-key-field" data-provider="{safe_provider}">',
        unsafe_allow_html=True,
    )

    # Label and help text
    st.markdown(
        f'<div class="api-key-label">{escape_html(label)}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="api-key-help">{escape_html(help_text)}</div>',
        unsafe_allow_html=True,
    )

    # Source badge
    if source == "environment" and not current_override:
        masked = mask_api_key(effective_value or "") if effective_value else ""
        st.markdown(
            f'<div class="api-key-source-badge environment">'
            f"Set via environment ({masked})"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Get show/hide state
    show_key = f"show_api_key_{provider}"
    show_value = st.session_state.get(show_key, False)

    # Input field with columns for show/hide toggle
    col1, col2 = st.columns([4, 1])

    with col1:
        # Determine input type
        input_type = "default" if (not is_password or show_value) else "password"

        # For Ollama, always show as text
        if provider == "ollama":
            input_type = "default"

        # Create input field
        new_value = st.text_input(
            f"{label} input",
            value=current_override,
            placeholder=placeholder,
            key=f"api_key_input_{provider}",
            type=input_type,
            label_visibility="collapsed",
        )

        # Handle value change
        if new_value is not None and new_value != current_override:
            handle_api_key_change(provider, new_value)

    with col2:
        # Show/Hide toggle for password fields (not for Ollama)
        if is_password:
            toggle_label = "Hide" if show_value else "Show"
            if st.button(toggle_label, key=f"toggle_show_{provider}"):
                st.session_state[show_key] = not show_value
                st.rerun()

    # Check if we need to run validation
    if st.session_state.get(f"api_key_validating_{provider}", False):
        with st.spinner("Validating..."):
            run_api_key_validation(provider, new_value or current_override)
            st.rerun()

    # Validation status display
    validation_result: ValidationResult | None = st.session_state.get(
        f"api_key_status_{provider}"
    )
    is_validating = st.session_state.get(f"api_key_validating_{provider}", False)

    if is_validating:
        status_html = render_validation_status_html("validating", "", provider)
    elif validation_result is not None:
        status = "valid" if validation_result.valid else "invalid"
        status_html = render_validation_status_html(
            status, validation_result.message, provider
        )
    elif source == "environment" and not current_override:
        # Environment key set but not validated yet
        status_html = render_validation_status_html(
            "untested", "Environment key - click Validate to test", provider
        )
    elif not current_override and source == "empty":
        status_html = ""  # No status for empty fields
    else:
        status_html = render_validation_status_html("untested", "", provider)

    if status_html:
        st.markdown(status_html, unsafe_allow_html=True)

    # Validate button for environment keys or entered values
    effective = effective_value or current_override
    if effective and not is_validating:
        if st.button("Validate", key=f"validate_{provider}"):
            st.session_state[f"api_key_validating_{provider}"] = True
            st.rerun()

    # Close field container
    st.markdown("</div>", unsafe_allow_html=True)


def render_ollama_models_list() -> None:
    """Render the list of available Ollama models if connected."""
    models = st.session_state.get("ollama_available_models", [])
    validation_result: ValidationResult | None = st.session_state.get(
        "api_key_status_ollama"
    )

    if validation_result and validation_result.valid and models:
        with st.expander("Available Models", expanded=False):
            st.markdown('<div class="ollama-models">', unsafe_allow_html=True)
            for model in models:
                st.markdown(
                    f'<div class="ollama-model-item">{escape_html(model)}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)


def render_api_keys_tab() -> None:
    """Render the API Keys tab content in the config modal.

    Shows entry fields for Google (Gemini), Anthropic (Claude),
    and Ollama with validation and status display.
    """
    # Section header
    st.markdown(
        '<h4 class="api-keys-section-header">Provider API Keys</h4>',
        unsafe_allow_html=True,
    )

    # Provider fields in order: Gemini, Claude, Ollama
    render_api_key_field("google")
    st.markdown("---")

    render_api_key_field("anthropic")
    st.markdown("---")

    render_api_key_field("ollama")
    render_ollama_models_list()


def apply_api_key_overrides() -> None:
    """Apply API key overrides to the config system.

    Called when Save is clicked in the config modal.

    Note: API key overrides are stored in session state only (not persisted
    to disk). This is by design - users who want persistent keys should use
    environment variables or .env files. The overrides in session state are
    already set by handle_api_key_change(), so this function currently just
    logs that save was applied.

    This hook exists for future expansion (e.g., optional .env file writing
    with explicit user consent in a later story).
    """
    # Overrides are already in session state via handle_api_key_change
    # Mark as saved (no-op for now since changes are already applied)
    st.session_state["config_has_changes"] = False


# =============================================================================
# Models Tab - Per-Agent Model Selection (Story 6.3)
# =============================================================================

# Provider display names and mappings
# PROVIDER_OPTIONS: UI dropdown options (display names)
# PROVIDER_KEYS: Maps display names to internal provider keys
# PROVIDER_DISPLAY: Maps internal provider keys to display names (inverse of PROVIDER_KEYS)
PROVIDER_OPTIONS: list[str] = ["Gemini", "Claude", "Ollama"]
PROVIDER_KEYS: dict[str, str] = {
    "Gemini": "gemini",
    "Claude": "claude",
    "Ollama": "ollama",
}
PROVIDER_DISPLAY: dict[str, str] = {
    "gemini": "Gemini",
    "claude": "Claude",
    "ollama": "Ollama",
}


def get_agent_status(agent_key: str) -> str:
    """Determine status for an agent.

    Args:
        agent_key: The agent key to check status for (e.g., "dm", "theron", "summarizer").
            Must be a non-empty string.

    Returns:
        "Active" if this agent's turn
        "You" if human controls this agent
        "AI" otherwise
    """
    if not agent_key or not isinstance(agent_key, str):
        return "AI"

    controlled = st.session_state.get("controlled_character")
    if controlled and controlled.lower() == agent_key.lower():
        return "You"

    game: GameState | None = st.session_state.get("game")
    if game and game.get("current_turn", "").lower() == agent_key.lower():
        return "Active"

    return "AI"


def get_class_from_character_key(agent_key: str) -> str:
    """Get character class from character key.

    Args:
        agent_key: The agent key (lowercase character name).

    Returns:
        Character class string or empty string if not found.
    """
    game: GameState | None = st.session_state.get("game")
    if not game:
        return ""

    characters = game.get("characters", {})
    char_config = characters.get(agent_key)
    if char_config:
        return char_config.character_class.lower()
    return ""


def get_class_css_name(character_class: str) -> str:
    """Convert character class to CSS class name.

    Args:
        character_class: Full class name (e.g., "Fighter").

    Returns:
        Lowercase CSS class name (e.g., "fighter").
    """
    if not character_class:
        return ""
    return character_class.lower()


def get_current_agent_model(agent_key: str) -> tuple[str, str]:
    """Get current provider/model for an agent.

    Checks overrides first, then falls back to game state.

    Args:
        agent_key: Agent key ("dm", character name, or "summarizer").
            Must be a non-empty string.

    Returns:
        Tuple of (provider, model). Returns default ("gemini", "gemini-1.5-flash")
        if agent_key is invalid or not found.
    """
    # Validate input
    if not agent_key or not isinstance(agent_key, str):
        return "gemini", "gemini-1.5-flash"

    # Check overrides first
    overrides = st.session_state.get("agent_model_overrides", {})
    if agent_key in overrides:
        override = overrides[agent_key]
        return override.get("provider", "gemini"), override.get("model", "")

    # Fall back to game state
    game: GameState | None = st.session_state.get("game")
    if not game:
        return "gemini", "gemini-1.5-flash"

    if agent_key == "dm":
        dm_config = game.get("dm_config")
        if dm_config:
            return dm_config.provider, dm_config.model
        return "gemini", "gemini-1.5-flash"

    if agent_key == "summarizer":
        game_config = game.get("game_config")
        if game_config:
            return game_config.summarizer_provider, game_config.summarizer_model
        return "gemini", "gemini-1.5-flash"

    # PC character
    characters = game.get("characters", {})
    char_config = characters.get(agent_key)
    if char_config:
        return char_config.provider, char_config.model
    return "gemini", "gemini-1.5-flash"


def handle_provider_change(agent_key: str) -> None:
    """Handle provider dropdown change.

    Resets model to first available for the new provider.

    Args:
        agent_key: Agent key to update. Must be a non-empty string.
    """
    # Validate input
    if not agent_key or not isinstance(agent_key, str):
        return

    # Get the new provider from session state key
    select_key = f"provider_select_{agent_key}"
    new_provider_display = st.session_state.get(select_key, "Gemini")
    new_provider = PROVIDER_KEYS.get(new_provider_display, "gemini")

    # Get first available model for new provider
    models = get_available_models(new_provider)
    # Fallback to known default if models list is empty
    if models:
        default_model = models[0]
    else:
        # Use a safe default based on provider
        from agents import DEFAULT_MODELS

        default_model = DEFAULT_MODELS.get(new_provider, "gemini-1.5-flash")

    # Update overrides
    overrides = st.session_state.get("agent_model_overrides", {})
    overrides[agent_key] = {"provider": new_provider, "model": default_model}
    st.session_state["agent_model_overrides"] = overrides

    mark_config_changed()


def handle_model_change(agent_key: str) -> None:
    """Handle model dropdown change.

    Args:
        agent_key: Agent key to update. Must be a non-empty string.
    """
    # Validate input
    if not agent_key or not isinstance(agent_key, str):
        return

    # Get the new model from session state key
    select_key = f"model_select_{agent_key}"
    new_model = st.session_state.get(select_key, "")

    # Get current provider
    current_provider, _ = get_current_agent_model(agent_key)

    # Update overrides
    overrides = st.session_state.get("agent_model_overrides", {})
    if agent_key not in overrides:
        overrides[agent_key] = {"provider": current_provider, "model": new_model}
    else:
        overrides[agent_key]["model"] = new_model
    st.session_state["agent_model_overrides"] = overrides

    mark_config_changed()


def render_status_badge(status: str) -> str:
    """Generate HTML for status badge.

    Args:
        status: Status string ("Active", "AI", or "You").

    Returns:
        HTML string for the badge.
    """
    css_class = status.lower()
    return f'<span class="agent-status-badge {css_class}">{escape_html(status)}</span>'


def render_pending_change_badge() -> str:
    """Generate HTML for pending change badge.

    Story 6.5: Task 7 - Visual indicator for pending changes.

    Returns:
        HTML string for the pending change badge.
    """
    return '<span class="pending-change-badge">(pending)</span>'


def render_provider_unavailable_warning() -> str:
    """Generate HTML for provider unavailable warning.

    Story 6.5: AC #4 - Show warning when provider unavailable.

    Returns:
        HTML string for the provider unavailable warning.
    """
    return '<span class="provider-unavailable-warning">Provider unavailable</span>'


def render_agent_model_row(
    agent_key: str,
    agent_name: str,
    css_class: str,
    is_dm: bool = False,
    is_summarizer: bool = False,
) -> None:
    """Render a single agent row in the Models tab.

    Story 6.5 enhancements:
    - Shows pending change badge when agent has uncommitted override
    - Shows provider unavailable warning when current provider is down

    Args:
        agent_key: Agent key for state management.
        agent_name: Display name for the agent.
        css_class: CSS class for styling (dm, fighter, rogue, wizard, cleric, summarizer).
        is_dm: True if this is the DM row.
        is_summarizer: True if this is the Summarizer row.
    """
    # Sanitize css_class to prevent injection - only allow alphanumeric and hyphens
    safe_css_class = "".join(c for c in css_class if c.isalnum() or c == "-").lower()
    if not safe_css_class:
        safe_css_class = "default"

    # Get current provider/model
    current_provider, current_model = get_current_agent_model(agent_key)

    # Get available models for current provider
    available_models = get_available_models(current_provider)

    # Ensure current model is in the list
    if current_model and current_model not in available_models:
        available_models.insert(0, current_model)

    # Get status (not applicable for summarizer)
    status = "" if is_summarizer else get_agent_status(agent_key)

    # Story 6.5: Check for pending changes and provider availability
    pending = has_pending_change(agent_key)
    provider_unavailable = is_agent_provider_unavailable(agent_key)

    # Start row container
    st.markdown(
        f'<div class="agent-model-row {safe_css_class}">',
        unsafe_allow_html=True,
    )

    # Agent name with status badge, pending indicator, and availability warning
    name_html = f'<span class="agent-model-name {safe_css_class}">{escape_html(agent_name)}</span>'
    if status:
        name_html += render_status_badge(status)
    # Story 6.5: Add pending change badge
    if pending:
        name_html += render_pending_change_badge()
    st.markdown(name_html, unsafe_allow_html=True)

    # Story 6.5: Show provider unavailable warning
    if provider_unavailable:
        st.markdown(render_provider_unavailable_warning(), unsafe_allow_html=True)

    # Provider and model dropdowns
    col1, col2 = st.columns([1, 2])

    with col1:
        provider_display = PROVIDER_DISPLAY.get(current_provider, "Gemini")
        provider_index = (
            PROVIDER_OPTIONS.index(provider_display)
            if provider_display in PROVIDER_OPTIONS
            else 0
        )
        st.selectbox(
            "Provider",
            PROVIDER_OPTIONS,
            index=provider_index,
            key=f"provider_select_{agent_key}",
            on_change=handle_provider_change,
            args=(agent_key,),
            label_visibility="collapsed",
        )

    with col2:
        model_index = (
            available_models.index(current_model)
            if current_model in available_models
            else 0
        )
        st.selectbox(
            "Model",
            available_models,
            index=model_index,
            key=f"model_select_{agent_key}",
            on_change=handle_model_change,
            args=(agent_key,),
            label_visibility="collapsed",
        )

    # Help text for summarizer
    if is_summarizer:
        st.markdown(
            '<p class="model-help-text">Model used for memory compression</p>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def handle_copy_dm_to_pcs() -> None:
    """Copy DM's provider/model to all PC agents."""
    overrides = st.session_state.get("agent_model_overrides", {})
    dm_provider, dm_model = get_current_agent_model("dm")
    dm_config = {"provider": dm_provider, "model": dm_model}

    # Get PC agent keys from game state
    game: GameState | None = st.session_state.get("game")
    if not game:
        return

    characters = game.get("characters", {})
    for agent_key in characters.keys():
        overrides[agent_key] = dm_config.copy()

    # Also update DM if not already in overrides
    if "dm" not in overrides:
        overrides["dm"] = dm_config.copy()

    st.session_state["agent_model_overrides"] = overrides
    mark_config_changed()


def handle_reset_model_defaults() -> None:
    """Reset all agents to YAML defaults."""
    # Clear all overrides
    st.session_state["agent_model_overrides"] = {}
    mark_config_changed()


def apply_model_config_changes() -> None:
    """Apply model config overrides to game state.

    Changes take effect on the NEXT turn, not immediately.
    This is by design - we don't want to switch models mid-turn.
    """
    overrides = st.session_state.get("agent_model_overrides", {})
    game: GameState | None = st.session_state.get("game")

    if not game or not overrides:
        return

    # Update DM config
    if "dm" in overrides:
        dm_override = overrides["dm"]
        old_dm = game.get("dm_config") or DMConfig()
        game["dm_config"] = old_dm.model_copy(
            update={
                "provider": dm_override.get("provider", old_dm.provider),
                "model": dm_override.get("model", old_dm.model),
            }
        )

    # Update character configs
    for agent_key, config in game.get("characters", {}).items():
        if agent_key in overrides:
            char_override = overrides[agent_key]
            game["characters"][agent_key] = config.model_copy(
                update={
                    "provider": char_override.get("provider", config.provider),
                    "model": char_override.get("model", config.model),
                }
            )

    # Update summarizer config
    if "summarizer" in overrides:
        summ_override = overrides["summarizer"]
        old_game_config = game.get("game_config") or GameConfig()
        game["game_config"] = old_game_config.model_copy(
            update={
                "summarizer_provider": summ_override.get(
                    "provider", old_game_config.summarizer_provider
                ),
                "summarizer_model": summ_override.get(
                    "model", old_game_config.summarizer_model
                ),
            }
        )

    st.session_state["game"] = game
    st.session_state["model_config_changed"] = True


# =============================================================================
# Mid-Campaign Provider Switching (Story 6.5)
# =============================================================================


def generate_model_change_messages() -> list[str]:
    """Generate specific change messages for each agent that changed.

    Story 6.5: AC #5 - Confirmation messages for provider switch.

    Returns:
        List of messages like "Dungeon Master will use Claude/claude-3-haiku starting next turn"
    """
    messages: list[str] = []
    overrides = st.session_state.get("agent_model_overrides", {})
    game: GameState | None = st.session_state.get("game")

    if not game or not overrides:
        return messages

    for agent_key, override in overrides.items():
        # Defensive: skip malformed overrides missing required keys
        if not isinstance(override, dict):
            continue
        provider_val = override.get("provider")
        model_val = override.get("model")
        if not provider_val or not model_val:
            continue
        # Type narrowing: we know these are truthy strings at this point
        provider: str = str(provider_val)
        model: str = str(model_val)

        # Get agent display name
        if agent_key == "dm":
            display_name = "Dungeon Master"
        elif agent_key == "summarizer":
            display_name = "Summarizer"
        else:
            char_config = game.get("characters", {}).get(agent_key)
            display_name = char_config.name if char_config else agent_key.title()

        provider_display = PROVIDER_DISPLAY.get(provider, provider)

        messages.append(
            f"{display_name} will use {provider_display}/{model} starting next turn"
        )

    return messages


def get_provider_availability_status() -> dict[str, bool]:
    """Get availability status for each provider.

    Story 6.5: AC #4 - Handle provider unavailability gracefully.

    Returns:
        Dict mapping provider key to availability (True = available).
    """
    status: dict[str, bool] = {}

    # Check Google/Gemini - has API key?
    config = get_config()
    status["gemini"] = bool(config.google_api_key)

    # Check Anthropic/Claude - has API key?
    status["claude"] = bool(config.anthropic_api_key)

    # Check Ollama - attempt connection with short timeout
    try:
        import requests

        resp = requests.get(f"{config.ollama_base_url}/api/tags", timeout=2)
        status["ollama"] = resp.status_code == 200
    except Exception:
        status["ollama"] = False

    return status


def has_pending_change(agent_key: str) -> bool:
    """Check if agent has uncommitted model override.

    Story 6.5: Task 7 - Pending change visual indicator.

    Args:
        agent_key: Agent key to check.

    Returns:
        True if agent has pending override, False otherwise.
    """
    overrides = st.session_state.get("agent_model_overrides", {})
    return agent_key in overrides


def is_provider_available(provider: str) -> bool:
    """Check if a specific provider is available.

    Story 6.5: AC #4 - Handle provider unavailability.

    Args:
        provider: Provider key ("gemini", "claude", "ollama").

    Returns:
        True if provider is available, False otherwise.
    """
    # Use cached status if available and recent
    cached_status = st.session_state.get("provider_availability", {})
    if provider in cached_status:
        return cached_status[provider]

    # Otherwise check and cache
    status = get_provider_availability_status()
    st.session_state["provider_availability"] = status
    return status.get(provider, False)


def get_agent_current_provider(agent_key: str) -> str:
    """Get the current provider for an agent from game state.

    Args:
        agent_key: Agent key to look up.

    Returns:
        Provider key or "gemini" as default.
    """
    game: GameState | None = st.session_state.get("game")
    if not game:
        return "gemini"

    if agent_key == "dm":
        dm_config = game.get("dm_config")
        return dm_config.provider if dm_config else "gemini"

    if agent_key == "summarizer":
        game_config = game.get("game_config")
        return game_config.summarizer_provider if game_config else "gemini"

    # Character
    characters = game.get("characters", {})
    char_config = characters.get(agent_key)
    return char_config.provider if char_config else "gemini"


def is_agent_provider_unavailable(agent_key: str) -> bool:
    """Check if agent's current provider is unavailable.

    Story 6.5: AC #4 - Show warning when current provider unavailable.

    Args:
        agent_key: Agent key to check.

    Returns:
        True if agent's provider is unavailable, False if available.
    """
    # Check if there's an override - use override provider
    overrides = st.session_state.get("agent_model_overrides", {})
    if agent_key in overrides:
        provider = overrides[agent_key].get("provider", "gemini")
    else:
        provider = get_agent_current_provider(agent_key)

    return not is_provider_available(provider)


# =============================================================================
# Token Limit Configuration (Story 6.4)
# =============================================================================


def get_effective_token_limit(agent_key: str) -> int:
    """Get effective token limit for an agent.

    Checks overrides first, then falls back to game state config.

    Args:
        agent_key: Agent key ("dm", character name, or "summarizer").

    Returns:
        Token limit for the agent. Returns default (4000) if not found.
    """
    # Check UI override first
    overrides = st.session_state.get("token_limit_overrides", {})
    if agent_key in overrides:
        return overrides[agent_key]

    # Fall back to game state
    game: GameState | None = st.session_state.get("game")
    if not game:
        return 4000  # Default fallback

    if agent_key == "dm":
        dm_config = game.get("dm_config")
        return dm_config.token_limit if dm_config else 8000

    if agent_key == "summarizer":
        # Summarizer uses default from config
        config = get_config()
        return config.agents.summarizer.token_limit

    # Character agent
    characters = game.get("characters", {})
    if agent_key in characters:
        return characters[agent_key].token_limit

    return 4000  # Default fallback


def get_token_limit_warning(value: int) -> str | None:
    """Get warning message for low token limit.

    Args:
        value: Token limit value to check.

    Returns:
        Warning text if value < MINIMUM_TOKEN_LIMIT, else None.
    """
    if value < MINIMUM_TOKEN_LIMIT:
        return "Low limit may affect memory quality"
    return None


def validate_token_limit(agent_key: str, value: int) -> tuple[int, str | None]:
    """Validate token limit value and return adjusted value with message.

    Clamps value to model maximum if exceeded.

    Args:
        agent_key: Agent key for model lookup.
        value: User-entered token limit.

    Returns:
        Tuple of (adjusted_value, info_message or None)
    """
    # Get current model for this agent
    _, model = get_current_agent_model(agent_key)
    max_context = get_model_max_context(model)

    # Clamp to model maximum
    if value > max_context:
        return max_context, f"Adjusted to model maximum ({max_context:,} tokens)"

    return value, None


def handle_token_limit_change(agent_key: str) -> None:
    """Handle token limit field change.

    Stores the new value in overrides and validates against model max.

    Args:
        agent_key: Agent key to update.
    """
    # Get value from widget
    widget_key = f"token_limit_{agent_key}"
    new_value = st.session_state.get(widget_key)

    if new_value is None:
        return

    # Validate and potentially clamp
    adjusted_value, info_msg = validate_token_limit(agent_key, int(new_value))

    # Store override
    overrides = st.session_state.get("token_limit_overrides", {})
    overrides[agent_key] = adjusted_value
    st.session_state["token_limit_overrides"] = overrides

    # Store info message for display
    if info_msg:
        st.session_state[f"token_limit_info_{agent_key}"] = info_msg
    else:
        # Clear any previous info message
        st.session_state.pop(f"token_limit_info_{agent_key}", None)

    mark_config_changed()


def apply_token_limit_changes() -> None:
    """Apply token limit overrides to game state.

    Updates token_limit in:
    - dm_config
    - character configs
    - agent_memories (for compression threshold)

    Does NOT trigger retroactive compression - only future turns affected.
    """
    overrides = st.session_state.get("token_limit_overrides", {})
    game: GameState | None = st.session_state.get("game")

    if not game or not overrides:
        return

    # Update DM config and memory
    if "dm" in overrides:
        old_dm = game.get("dm_config") or DMConfig()
        game["dm_config"] = old_dm.model_copy(update={"token_limit": overrides["dm"]})
        # Also update agent memory
        if "dm" in game.get("agent_memories", {}):
            dm_memory = game["agent_memories"]["dm"]
            game["agent_memories"]["dm"] = dm_memory.model_copy(
                update={"token_limit": overrides["dm"]}
            )

    # Update character configs and memories
    for agent_key, config in game.get("characters", {}).items():
        if agent_key in overrides:
            game["characters"][agent_key] = config.model_copy(
                update={"token_limit": overrides[agent_key]}
            )
            # Also update agent memory
            if agent_key in game.get("agent_memories", {}):
                agent_memory = game["agent_memories"][agent_key]
                game["agent_memories"][agent_key] = agent_memory.model_copy(
                    update={"token_limit": overrides[agent_key]}
                )

    # Summarizer doesn't have a persistent config in game state
    # Its token limit is used internally by the Summarizer class

    st.session_state["game"] = game
    st.session_state["token_limit_changed"] = True


def render_models_tab() -> None:
    """Render the Models tab content in the config modal.

    Shows agent rows for DM, PCs, and Summarizer with provider/model selection.
    Story 6.3: Per-Agent Model Selection.
    """
    # Section header
    st.markdown(
        '<h4 class="models-section-header">Agent Models</h4>',
        unsafe_allow_html=True,
    )

    # Initialize overrides if needed
    if "agent_model_overrides" not in st.session_state:
        st.session_state["agent_model_overrides"] = {}

    st.markdown('<div class="agent-model-grid">', unsafe_allow_html=True)

    # DM row (gold color, no class)
    render_agent_model_row(
        agent_key="dm",
        agent_name="Dungeon Master",
        css_class="dm",
        is_dm=True,
    )

    # PC rows - get from game state
    game: GameState | None = st.session_state.get("game")
    if game:
        characters = game.get("characters", {})
        # Sort by class for consistent ordering
        sorted_chars = sorted(
            characters.items(),
            key=lambda x: ["fighter", "rogue", "wizard", "cleric"].index(
                x[1].character_class.lower()
            )
            if x[1].character_class.lower() in ["fighter", "rogue", "wizard", "cleric"]
            else 99,
        )
        for agent_key, char_config in sorted_chars:
            css_class = get_class_css_name(char_config.character_class)
            render_agent_model_row(
                agent_key=agent_key,
                agent_name=char_config.name,
                css_class=css_class,
            )
    else:
        # Fallback: show default PC classes
        default_pcs = [
            ("fighter", "Fighter", "fighter"),
            ("rogue", "Rogue", "rogue"),
            ("wizard", "Wizard", "wizard"),
            ("cleric", "Cleric", "cleric"),
        ]
        for agent_key, name, css_class in default_pcs:
            render_agent_model_row(
                agent_key=agent_key,
                agent_name=name,
                css_class=css_class,
            )

    # Separator
    st.markdown('<div class="model-separator"></div>', unsafe_allow_html=True)

    # Summarizer row
    render_agent_model_row(
        agent_key="summarizer",
        agent_name="Summarizer",
        css_class="summarizer",
        is_summarizer=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # Quick actions
    st.markdown('<div class="model-quick-actions">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Copy DM to all PCs", key="copy_dm_to_pcs_btn"):
            handle_copy_dm_to_pcs()
            st.rerun()

    with col2:
        if st.button("Reset to defaults", key="reset_model_defaults_btn"):
            handle_reset_model_defaults()
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# Settings Tab (Story 6.4)
# =============================================================================


def render_token_limit_row(
    agent_key: str,
    agent_name: str,
    css_class: str,
) -> None:
    """Render a token limit configuration row.

    Args:
        agent_key: Agent key for state management.
        agent_name: Display name for the agent.
        css_class: CSS class for styling (e.g., "dm", "fighter", "summarizer").
    """
    # Get current values
    current_limit = get_effective_token_limit(agent_key)
    _, model = get_current_agent_model(agent_key)
    max_context = get_model_max_context(model)

    # Ensure safe CSS class
    safe_css_class = escape_html(css_class)

    # Row container with character-colored border
    st.markdown(
        f'<div class="token-limit-row {safe_css_class}">',
        unsafe_allow_html=True,
    )

    # Agent name with color
    st.markdown(
        f'<span class="agent-model-name {safe_css_class}">{escape_html(agent_name)}</span>',
        unsafe_allow_html=True,
    )

    # Token limit input with columns
    col1, col2 = st.columns([2, 1])

    with col1:
        # Number input for token limit
        # Use min_value of 100 to allow low values but not zero
        st.number_input(
            f"Token limit for {agent_name}",
            min_value=100,
            max_value=max_context,
            value=current_limit,
            step=1000,
            key=f"token_limit_{agent_key}",
            on_change=handle_token_limit_change,
            args=(agent_key,),
            label_visibility="collapsed",
        )

    with col2:
        # Model max hint
        # Format large numbers with K/M suffix for readability
        if max_context >= 1_000_000:
            max_display = f"{max_context // 1_000_000}M"
        elif max_context >= 1_000:
            max_display = f"{max_context // 1_000}K"
        else:
            max_display = f"{max_context:,}"

        st.markdown(
            f'<span class="token-limit-hint">Max: {max_display} for {escape_html(model)}</span>',
            unsafe_allow_html=True,
        )

    # Check for warning (low limit)
    warning = get_token_limit_warning(current_limit)
    if warning:
        st.markdown(
            f'<span class="token-limit-warning">\u26a0\ufe0f {escape_html(warning)}</span>',
            unsafe_allow_html=True,
        )

    # Show info message if clamped
    info_msg = st.session_state.get(f"token_limit_info_{agent_key}")
    if info_msg:
        st.markdown(
            f'<span class="token-limit-info">{escape_html(info_msg)}</span>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def render_settings_tab() -> None:
    """Render the Settings tab content in the config modal.

    Shows token limit configuration for each agent.
    Story 6.4: Context Limit Configuration.
    """
    # Section header
    st.markdown(
        '<h4 class="settings-section-header">Context Limits</h4>',
        unsafe_allow_html=True,
    )

    # Initialize overrides if needed
    if "token_limit_overrides" not in st.session_state:
        st.session_state["token_limit_overrides"] = {}

    # DM row
    render_token_limit_row(
        agent_key="dm",
        agent_name="Dungeon Master",
        css_class="dm",
    )

    # PC rows (from game state)
    game: GameState | None = st.session_state.get("game")
    if game:
        characters = game.get("characters", {})
        # Sort by class for consistent ordering
        sorted_chars = sorted(
            characters.items(),
            key=lambda x: ["fighter", "rogue", "wizard", "cleric"].index(
                x[1].character_class.lower()
            )
            if x[1].character_class.lower() in ["fighter", "rogue", "wizard", "cleric"]
            else 99,
        )
        for agent_key, char_config in sorted_chars:
            css_class = get_class_css_name(char_config.character_class)
            render_token_limit_row(
                agent_key=agent_key,
                agent_name=char_config.name,
                css_class=css_class,
            )
    else:
        # Fallback: show default PC classes
        default_pcs = [
            ("fighter", "Fighter", "fighter"),
            ("rogue", "Rogue", "rogue"),
            ("wizard", "Wizard", "wizard"),
            ("cleric", "Cleric", "cleric"),
        ]
        for agent_key, name, css_class in default_pcs:
            render_token_limit_row(
                agent_key=agent_key,
                agent_name=name,
                css_class=css_class,
            )

    # Separator
    st.markdown('<div class="token-limit-separator"></div>', unsafe_allow_html=True)

    # Summarizer row
    render_token_limit_row(
        agent_key="summarizer",
        agent_name="Summarizer",
        css_class="summarizer",
    )


@st.dialog("Configuration", width="large")
def render_config_modal() -> None:
    """Render the configuration modal with tabs for API Keys, Models, and Settings.

    Uses st.dialog decorator for modal container.
    Implements Story 6.1 AC #2: three tabs with campfire theme styling.
    Story 6.2: API Keys tab with provider configuration.
    """
    # Tab structure (Story 6.1 Task 3)
    tab1, tab2, tab3 = st.tabs(["API Keys", "Models", "Settings"])

    with tab1:
        # API Keys tab content (Story 6.2)
        render_api_keys_tab()

    with tab2:
        # Models tab content (Story 6.3)
        render_models_tab()

    with tab3:
        # Settings tab content (Story 6.4)
        render_settings_tab()

    # Show discard confirmation if needed (Story 6.1 AC #5)
    if st.session_state.get("show_discard_confirmation"):
        render_discard_confirmation()
    else:
        # Footer buttons (Story 6.1 Task 8)
        st.markdown("---")
        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("Cancel", key="config_cancel_btn", use_container_width=True):
                handle_config_cancel_click()

        with col2:
            if st.button(
                "Save", key="config_save_btn", type="primary", use_container_width=True
            ):
                handle_config_save_click()


def render_discard_confirmation() -> None:
    """Render confirmation dialog when closing with unsaved changes (Story 6.1 AC #5).

    Shows a warning message with Discard and Keep Editing buttons.
    """
    st.markdown(
        '<div class="discard-confirmation">'
        '<p class="discard-confirmation-text">'
        "You have unsaved changes. Discard them?"
        "</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Discard", key="discard_btn", use_container_width=True):
            handle_config_discard_click()

    with col2:
        if st.button("Keep Editing", key="keep_editing_btn", use_container_width=True):
            st.session_state["show_discard_confirmation"] = False
            st.rerun()


def handle_config_save_click() -> None:
    """Handle Save button click in config modal (Story 6.1 Task 8.4).

    Commits any pending config changes and closes the modal.
    Shows confirmation toast if model configs changed (Story 6.3 AC #7).
    Shows confirmation toast if token limits changed (Story 6.4 AC #5).
    Story 6.5: Shows specific change messages per agent (AC #5).
    """
    # Story 6.5: Generate specific change messages BEFORE applying
    # (since applying clears the overrides for next time)
    model_overrides = st.session_state.get("agent_model_overrides", {})
    model_change_messages = generate_model_change_messages() if model_overrides else []

    # Apply model config changes (Story 6.3)
    if model_overrides:
        apply_model_config_changes()

    # Apply token limit changes (Story 6.4)
    token_limit_overrides = st.session_state.get("token_limit_overrides", {})
    if token_limit_overrides:
        apply_token_limit_changes()

    # Apply API key overrides (Story 6.2)
    apply_api_key_overrides()

    # Story 6.5: Show specific change messages (AC #5)
    # Format: "[Character] will use [Provider/Model] starting next turn"
    if model_change_messages:
        # Show each change message as a separate toast for visibility
        for msg in model_change_messages:
            st.toast(msg, icon="\u2705")
        # Store messages for potential future use
        st.session_state["last_model_change_messages"] = model_change_messages
    elif token_limit_overrides:
        # Fallback: show generic message for token limit changes only
        st.toast("Token limits updated - changes will apply on next turn", icon="\u2705")

    # Clear provider availability cache after save (fresh check on next modal open)
    st.session_state["provider_availability"] = {}

    handle_config_modal_close(save_changes=True)
    st.rerun()


def handle_config_cancel_click() -> None:
    """Handle Cancel button click in config modal (Story 6.1 Task 8.5).

    If there are unsaved changes, shows confirmation dialog.
    Otherwise, closes the modal directly.
    """
    if has_unsaved_changes():
        st.session_state["show_discard_confirmation"] = True
        st.rerun()
    else:
        handle_config_modal_close(save_changes=False)
        st.rerun()


def handle_config_discard_click() -> None:
    """Handle Discard button click in confirmation dialog.

    Discards any unsaved changes and closes the modal.
    """
    handle_config_modal_close(save_changes=False)
    st.rerun()


def render_configure_button() -> None:
    """Render the Configure button in the sidebar (Story 6.1 Task 1).

    Opens the configuration modal when clicked.
    """
    if st.button("Configure", key="configure_btn", use_container_width=True):
        handle_config_modal_open()
        st.rerun()


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


# =============================================================================
# Error Handling & Recovery (Story 4.5)
# =============================================================================

# Maximum retry attempts before giving up
MAX_RETRY_ATTEMPTS = 3


def render_error_panel_html(error: UserError) -> str:
    """Generate HTML for error panel with campfire styling.

    Creates an error panel with friendly title, message, action suggestion,
    and styled buttons for recovery options.

    Args:
        error: UserError instance with title, message, and action fields.

    Returns:
        HTML string for error panel.
    """
    retry_disabled = (
        'disabled="disabled"' if error.retry_count >= MAX_RETRY_ATTEMPTS else ""
    )
    retry_class = "disabled" if error.retry_count >= MAX_RETRY_ATTEMPTS else ""

    # Show retry count if there have been attempts
    retry_text = "Retry"
    if error.retry_count > 0:
        retry_text = f"Retry ({MAX_RETRY_ATTEMPTS - error.retry_count} left)"

    return (
        '<div class="error-panel">'
        f'<h3 class="error-panel-title">{escape_html(error.title)}</h3>'
        f'<p class="error-panel-message">{escape_html(error.message)}</p>'
        f'<p class="error-panel-action">{escape_html(error.action)}</p>'
        '<div class="error-panel-actions">'
        f'<button class="error-retry-btn {retry_class}" {retry_disabled}>{retry_text}</button>'
        '<button class="error-restore-btn">Restore from Checkpoint</button>'
        '<button class="error-new-session-btn">Start New Session</button>'
        "</div>"
        "</div>"
    )


def handle_retry_click() -> None:
    """Handle retry button click on error panel.

    Increments retry count, clears error, and attempts to re-execute
    the failed turn. If retry succeeds, game continues normally.
    If retry fails again, error panel will be shown with updated count.

    Enforces MAX_RETRY_ATTEMPTS limit (AC #4, Task 6.6).
    """
    # Get current retry count
    retry_count = st.session_state.get("error_retry_count", 0)

    if retry_count >= MAX_RETRY_ATTEMPTS:
        # Too many retries - update error message (only if not already updated)
        current_error: UserError | None = st.session_state.get("error")
        if (
            current_error
            and "(Maximum retry attempts reached)" not in current_error.message
        ):
            st.session_state["error"] = UserError(
                title=current_error.title,
                message=current_error.message + " (Maximum retry attempts reached)",
                action="Restore from checkpoint or start a new session.",
                error_type=current_error.error_type,
                timestamp=current_error.timestamp,
                provider=current_error.provider,
                agent=current_error.agent,
                retry_count=MAX_RETRY_ATTEMPTS,
                last_checkpoint_turn=current_error.last_checkpoint_turn,
            )
        return

    # Increment retry count
    new_retry_count = retry_count + 1
    st.session_state["error_retry_count"] = new_retry_count

    # Clear error to allow retry
    st.session_state["error"] = None

    # Re-execute turn
    if run_game_turn():
        # Success - reset retry count
        st.session_state["error_retry_count"] = 0
    else:
        # If failed again and error was set, update retry count in error
        current_error = st.session_state.get("error")
        if current_error:
            st.session_state["error"] = UserError(
                title=current_error.title,
                message=current_error.message,
                action=current_error.action,
                error_type=current_error.error_type,
                timestamp=current_error.timestamp,
                provider=current_error.provider,
                agent=current_error.agent,
                retry_count=new_retry_count,
                last_checkpoint_turn=current_error.last_checkpoint_turn,
            )


def handle_error_restore_click() -> None:
    """Handle restore from checkpoint button on error panel.

    Gets the last successful checkpoint from the error and restores to it.
    Clears error state after successful restore.
    Shows toast confirmation with turn number.
    """
    current_error: UserError | None = st.session_state.get("error")
    if not current_error:
        return

    # Get game state for session_id
    game: GameState = st.session_state.get("game", {})
    session_id = game.get("session_id", "001")

    # Get turn number to restore to
    turn_number = current_error.last_checkpoint_turn
    if turn_number is None:
        # No checkpoint available - show error
        st.error("No checkpoint available to restore from.")
        return

    # Reuse existing restore logic (Task 7.3)
    if handle_checkpoint_restore(session_id, turn_number):
        # Clear error state after successful restore (Task 7.4)
        st.session_state["error"] = None
        st.session_state["error_retry_count"] = 0
        # Show toast confirmation (Task 7.5)
        st.toast(f"Restored to Turn {turn_number}", icon="✅")
    else:
        st.error("Failed to restore checkpoint")


def handle_error_new_session_click() -> None:
    """Handle start new session button on error panel.

    Creates a new session, clearing the error state.
    Reuses existing new session logic.
    """
    # Clear error state
    st.session_state["error"] = None
    st.session_state["error_retry_count"] = 0

    # Delegate to existing new session handler
    handle_new_session_click()


def render_error_panel() -> None:
    """Render error panel if an error is present in session state.

    Displays the error panel with friendly narrative-style message
    and action buttons (Retry, Restore, New Session).

    Only renders if st.session_state["error"] contains a UserError.
    """
    error: UserError | None = st.session_state.get("error")
    if error is None:
        return

    # Render the error panel HTML
    st.markdown(render_error_panel_html(error), unsafe_allow_html=True)

    # Render functional Streamlit buttons (styled via CSS)
    col1, col2, col3 = st.columns(3)

    with col1:
        retry_disabled = error.retry_count >= MAX_RETRY_ATTEMPTS
        if st.button(
            "Retry",
            key="error_retry_btn",
            disabled=retry_disabled,
        ):
            handle_retry_click()
            st.rerun()

    with col2:
        restore_disabled = error.last_checkpoint_turn is None
        if st.button(
            "Restore",
            key="error_restore_btn",
            disabled=restore_disabled,
        ):
            handle_error_restore_click()
            st.rerun()

    with col3:
        if st.button("New Session", key="error_new_session_btn"):
            handle_error_new_session_click()
            st.rerun()


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


# =============================================================================
# Checkpoint Browser (Story 4.2)
# =============================================================================


def render_checkpoint_entry_html(
    turn_number: int, timestamp: str, brief_context: str
) -> str:
    """Generate HTML for a single checkpoint list entry.

    Args:
        turn_number: Turn number for this checkpoint.
        timestamp: Human-readable timestamp string.
        brief_context: Brief preview of checkpoint content.

    Returns:
        HTML string for checkpoint entry.
    """
    return (
        '<div class="checkpoint-entry">'
        '<div class="checkpoint-header">'
        f'<span class="checkpoint-turn">Turn {turn_number}</span>'
        f'<span class="checkpoint-timestamp">{escape_html(timestamp)}</span>'
        "</div>"
        f'<p class="checkpoint-context">{escape_html(brief_context)}</p>'
        "</div>"
    )


def handle_checkpoint_restore(session_id: str, turn_number: int) -> bool:
    """Handle checkpoint restore request.

    Loads the checkpoint, updates session state, and resets UI state.

    Args:
        session_id: Session ID to restore from.
        turn_number: Turn number to restore to.

    Returns:
        True if restore succeeded, False otherwise.
    """
    from persistence import load_checkpoint

    # Stop autopilot if running
    st.session_state["is_autopilot_running"] = False

    # Load the checkpoint
    state = load_checkpoint(session_id, turn_number)
    if state is None:
        return False

    # Update game state
    st.session_state["game"] = state

    # Reset UI state to defaults
    st.session_state["ui_mode"] = "watch"
    st.session_state["controlled_character"] = None
    st.session_state["human_active"] = False
    st.session_state["is_generating"] = False
    st.session_state["is_paused"] = False
    st.session_state["human_pending_action"] = None
    st.session_state["waiting_for_human"] = False
    st.session_state["pending_nudge"] = None
    st.session_state["nudge_submitted"] = False
    st.session_state["autopilot_turn_count"] = 0

    # Clean up any lingering preview state keys
    keys_to_remove = [k for k in st.session_state if k.startswith("show_preview_")]
    for key in keys_to_remove:
        del st.session_state[key]

    return True


def render_checkpoint_preview(session_id: str, turn_number: int) -> None:
    """Render preview of a checkpoint's recent messages.

    Args:
        session_id: Session ID string.
        turn_number: Turn number to preview.
    """
    from persistence import get_checkpoint_preview

    preview = get_checkpoint_preview(session_id, turn_number)

    if preview is None:
        st.warning("Could not load preview")
        return

    st.markdown('<div class="checkpoint-preview">', unsafe_allow_html=True)

    for entry in preview:
        # HTML escape entry content to prevent XSS/markdown injection
        escaped_entry = escape_html(entry)
        st.markdown(f"<p><em>{escaped_entry}</em></p>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Close preview button
    if st.button("Close", key=f"close_preview_{turn_number}"):
        st.session_state[f"show_preview_{turn_number}"] = False
        st.rerun()


def render_restore_confirmation(session_id: str, turn_number: int) -> None:
    """Render restore confirmation dialog.

    Shows a warning about turns that will be undone and provides
    Confirm/Cancel buttons.

    Args:
        session_id: Session ID string.
        turn_number: Turn number to restore to.
    """
    game: GameState = st.session_state.get("game", {})
    current_turn = len(game.get("ground_truth_log", []))
    turns_to_undo = current_turn - turn_number

    st.warning(
        f"Restore to Turn {turn_number}? This will undo {turns_to_undo} turn(s).",
        icon="⚠️",
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Confirm Restore", key="confirm_restore"):
            if handle_checkpoint_restore(session_id, turn_number):
                st.session_state["pending_restore"] = None
                st.toast(f"Restored to Turn {turn_number}", icon="✅")
                st.rerun()
            else:
                st.error("Failed to restore checkpoint")

    with col2:
        if st.button("Cancel", key="cancel_restore"):
            st.session_state["pending_restore"] = None
            st.rerun()


def render_checkpoint_browser() -> None:
    """Render checkpoint browser section in sidebar.

    Shows list of available checkpoints with preview and restore options.
    Only shows checkpoints for the current session.
    """
    from persistence import list_checkpoint_info

    game: GameState = st.session_state.get("game", {})
    session_id = game.get("session_id", "001")

    with st.expander("Session History", expanded=False):
        # Handle pending restore confirmation first
        pending_restore = st.session_state.get("pending_restore")
        if pending_restore is not None:
            render_restore_confirmation(session_id, pending_restore)
            return  # Don't render list while showing confirmation

        checkpoints = list_checkpoint_info(session_id)

        if not checkpoints:
            st.caption("No checkpoints available yet")
            return

        st.markdown('<div class="checkpoint-list">', unsafe_allow_html=True)

        current_message_count = len(game.get("ground_truth_log", []))

        for info in checkpoints:
            # Display checkpoint info
            st.markdown(
                render_checkpoint_entry_html(
                    info.turn_number, info.timestamp, info.brief_context
                ),
                unsafe_allow_html=True,
            )

            # Show preview if expanded
            if st.session_state.get(f"show_preview_{info.turn_number}"):
                render_checkpoint_preview(session_id, info.turn_number)
            else:
                # Action buttons row
                col1, col2 = st.columns([1, 1])

                with col1:
                    if st.button("Preview", key=f"preview_{info.turn_number}"):
                        st.session_state[f"show_preview_{info.turn_number}"] = True
                        st.rerun()

                with col2:
                    # Disable during generation
                    is_generating = st.session_state.get("is_generating", False)

                    # Only show restore for past checkpoints (not current state)
                    if info.message_count < current_message_count:
                        if st.button(
                            "Restore",
                            key=f"restore_{info.turn_number}",
                            disabled=is_generating,
                        ):
                            st.session_state["pending_restore"] = info.turn_number
                            st.rerun()

            st.markdown("---")

        st.markdown("</div>", unsafe_allow_html=True)


# =============================================================================
# Export Transcript Button (Story 4.4)
# =============================================================================


def render_export_transcript_button() -> None:
    """Render transcript export download button in sidebar.

    Shows a download button for the session transcript JSON file.
    Button is disabled if no transcript exists.
    Uses st.download_button for direct file download.
    """
    from datetime import datetime

    game: GameState = st.session_state.get("game", {})
    session_id = game.get("session_id", "001")

    # Check if transcript exists
    transcript_path = get_transcript_path(session_id)
    has_transcript = transcript_path.exists()

    if not has_transcript:
        # No transcript - show disabled button with help text
        st.button(
            "Export Transcript",
            key="export_transcript_btn",
            disabled=True,
            help="No transcript available - play some turns first",
        )
        return

    # Get transcript data for download
    transcript_data = get_transcript_download_data(session_id)

    if transcript_data is None:
        # Transcript file exists but couldn't be read
        st.button(
            "Export Transcript",
            key="export_transcript_btn",
            disabled=True,
            help="Transcript file could not be read",
        )
        return

    # Generate filename with timestamp
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"transcript_session_{session_id}_{ts}.json"

    # Render download button
    st.download_button(
        label="Export Transcript",
        data=transcript_data,
        file_name=filename,
        mime="application/json",
        key="export_transcript_btn",
        help="Download session transcript as JSON",
    )


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

        # Checkpoint Browser (Story 4.2)
        render_checkpoint_browser()

        st.markdown("---")

        # Export Transcript (Story 4.4)
        render_export_transcript_button()

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

        # Configure button (Story 6.1 Task 1)
        render_configure_button()

        st.markdown("---")

        # Back to Sessions button (Story 4.3)
        if st.button("Back to Sessions", key="back_to_sessions_btn"):
            handle_back_to_sessions_click()
            st.rerun()


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

    # Show summarization indicator when compressing memories (Story 5.2)
    render_summarization_indicator()

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

    # Error panel - shown when error is present (Story 4.5)
    # Renders above narrative area with recovery options
    render_error_panel()

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


# =============================================================================
# Session Browser (Story 4.3)
# =============================================================================


def format_session_date(iso_timestamp: str) -> str:
    """Format ISO timestamp for display.

    Args:
        iso_timestamp: ISO format timestamp string.

    Returns:
        Human-readable date string.
    """
    try:
        # Parse ISO format (handles both with and without Z suffix)
        ts = iso_timestamp.rstrip("Z")
        from datetime import datetime as dt

        parsed = dt.fromisoformat(ts)
        return parsed.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return "Unknown date"


def render_session_card_html(metadata: SessionMetadata) -> str:
    """Generate HTML for a session card.

    Args:
        metadata: Session metadata for the card.

    Returns:
        HTML string for the session card.
    """
    # Format session number as Roman numeral
    roman = int_to_roman(metadata.session_number)

    # Format last played date
    last_played = format_session_date(metadata.updated_at)

    # Format character names (truncate if too many)
    char_display = ", ".join(metadata.character_names[:3])
    if len(metadata.character_names) > 3:
        char_display += f" +{len(metadata.character_names) - 3} more"

    # Session name or default
    session_name = escape_html(metadata.name) if metadata.name else "Unnamed Adventure"

    return (
        '<div class="session-card">'
        f'<div class="session-card-header">'
        f'<span class="session-card-title">Session {escape_html(roman)}</span>'
        f"</div>"
        f'<div class="session-card-name">{session_name}</div>'
        f'<div class="session-card-meta">'
        f'<span class="session-card-date">Last played: {escape_html(last_played)}</span>'
        f'<span class="session-card-turns">{metadata.turn_count} turns</span>'
        f"</div>"
        f'<div class="session-card-characters">{escape_html(char_display)}</div>'
        f"</div>"
    )


def handle_session_continue(session_id: str) -> bool:
    """Handle continue session button click.

    Loads the latest checkpoint and sets up the game state.

    Args:
        session_id: Session ID to continue.

    Returns:
        True if session was loaded successfully, False otherwise.
    """
    # Get latest checkpoint
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is None:
        return False

    # Load the checkpoint
    state = load_checkpoint(session_id, latest_turn)
    if state is None:
        return False

    # Update session state
    st.session_state["game"] = state
    st.session_state["current_session_id"] = session_id
    st.session_state["app_view"] = "game"

    # Reset UI state
    st.session_state["ui_mode"] = "watch"
    st.session_state["controlled_character"] = None
    st.session_state["human_active"] = False
    st.session_state["is_generating"] = False
    st.session_state["is_paused"] = False
    st.session_state["human_pending_action"] = None
    st.session_state["waiting_for_human"] = False
    st.session_state["pending_nudge"] = None
    st.session_state["nudge_submitted"] = False
    st.session_state["is_autopilot_running"] = False
    st.session_state["autopilot_turn_count"] = 0

    # Generate recap if there are turns (Story 5.4: include cross-session content)
    if latest_turn > 0:
        recap = generate_recap_summary(
            session_id, num_turns=5, include_cross_session=True
        )
        if recap:
            st.session_state["show_recap"] = True
            st.session_state["recap_text"] = recap

    return True


def handle_new_session_click() -> None:
    """Handle new session button click.

    Creates a new session and initializes fresh game state.
    """
    # Create fresh game state
    game = populate_game_state(include_sample_messages=False)

    # Get character names from game state
    characters = game.get("characters", {})
    character_names = [config.name for key, config in characters.items() if key != "dm"]

    # Create new session
    session_id = create_new_session(character_names=character_names)

    # Update game state with session info
    try:
        session_number = int(session_id)
    except ValueError:
        session_number = 1

    game["session_id"] = session_id
    game["session_number"] = session_number

    # Update session state
    st.session_state["game"] = game
    st.session_state["current_session_id"] = session_id
    st.session_state["app_view"] = "game"
    st.session_state["show_recap"] = False
    st.session_state["recap_text"] = ""

    # Reset UI state
    st.session_state["ui_mode"] = "watch"
    st.session_state["controlled_character"] = None
    st.session_state["human_active"] = False
    st.session_state["is_generating"] = False
    st.session_state["is_paused"] = False
    st.session_state["is_autopilot_running"] = False
    st.session_state["autopilot_turn_count"] = 0


def handle_back_to_sessions_click() -> None:
    """Handle back to sessions button click."""
    st.session_state["app_view"] = "session_browser"
    st.session_state["show_recap"] = False
    st.session_state["recap_text"] = ""


def render_recap_modal(recap_text: str) -> None:
    """Render the "While you were away" recap modal.

    Args:
        recap_text: Recap summary text to display.
    """
    st.markdown('<div class="recap-modal">', unsafe_allow_html=True)

    st.markdown(
        '<h2 class="recap-header">While you were away...</h2>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="recap-content">', unsafe_allow_html=True)

    # Render each recap line
    for line in recap_text.split("\n"):
        if line.strip():
            st.markdown(
                f'<p class="recap-item">{escape_html(line)}</p>',
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)

    # Continue button
    if st.button("Continue Adventure", key="recap_continue_btn"):
        st.session_state["show_recap"] = False
        st.session_state["recap_text"] = ""
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_session_browser() -> None:
    """Render the session browser view.

    Shows list of available sessions with Continue buttons and
    a New Session button.
    """
    st.markdown('<div class="session-browser">', unsafe_allow_html=True)

    st.markdown(
        '<h2 class="session-browser-header">Your Adventures</h2>',
        unsafe_allow_html=True,
    )

    # Get sessions with metadata
    sessions = list_sessions_with_metadata()

    if sessions:
        for metadata in sessions:
            # Render session card
            st.markdown(
                render_session_card_html(metadata),
                unsafe_allow_html=True,
            )

            # Check if session has checkpoints (turn 0 is valid)
            latest_turn = get_latest_checkpoint(metadata.session_id)
            has_checkpoints = latest_turn is not None

            # Continue button
            _col1, col2 = st.columns([3, 1])
            with col2:
                if st.button(
                    "Continue",
                    key=f"continue_{metadata.session_id}",
                    disabled=not has_checkpoints,
                ):
                    if handle_session_continue(metadata.session_id):
                        st.rerun()
                    else:
                        st.error("Failed to load session")

            st.markdown("---")
    else:
        st.markdown(
            '<p class="session-browser-empty">'
            "No adventures yet. Start your first adventure!"
            "</p>",
            unsafe_allow_html=True,
        )

    # New Session button
    st.markdown('<div class="new-session-container">', unsafe_allow_html=True)
    if st.button("+ New Adventure", key="new_session_btn"):
        handle_new_session_click()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


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

    # App view routing (Story 4.3)
    app_view = st.session_state.get("app_view", "session_browser")

    if app_view == "session_browser":
        # Session browser view
        render_session_browser()
    else:
        # Game view
        # Show recap modal if needed
        if st.session_state.get("show_recap"):
            render_recap_modal(st.session_state.get("recap_text", ""))
        else:
            # Process keyboard actions (Story 3.6)
            if process_keyboard_action():
                st.rerun()

            # Render sidebar (Task 2.3, 2.5, 4.1, 4.2)
            render_sidebar(config)

            # Main narrative area (Task 2.4, 4.3, 4.4)
            render_main_content()

            # Inject keyboard shortcut script (Story 3.6)
            inject_keyboard_shortcut_script()

            # Show config modal if open (Story 6.1)
            if st.session_state.get("config_modal_open"):
                render_config_modal()

            # Run autopilot step if active (Story 3.1)
            # This executes at end of render to trigger next turn
            run_autopilot_step()

    # Close app-content div
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
