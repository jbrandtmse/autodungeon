# Story 2.5: Session Header & Controls

Status: done

## Story

As a **user**,
I want **a chronicle-style session header and accessible session controls**,
so that **I know what session I'm in and can control playback**.

## Acceptance Criteria

1. **Given** the narrative area header
   **When** viewing a session
   **Then** I see a centered title like "Session VII" in Lora font (24px, gold color)
   **And** a subtitle with session date/info in secondary text

2. **Given** the sidebar header area
   **When** viewing the application
   **Then** I see a mode indicator badge showing "Watch Mode" or "Play Mode"

3. **Given** the mode indicator in Watch Mode
   **When** the story is actively generating
   **Then** a green pulsing dot animates next to "Watching"

4. **Given** the session controls in the sidebar
   **When** viewing the application
   **Then** I can access: Pause/Resume button, Speed control (for Epic 3)
   **And** controls use the established button hierarchy (secondary style)

## Tasks / Subtasks

- [x] Task 1: Implement dynamic session header with roman numerals (AC: #1)
  - [x] 1.1 Create `int_to_roman(num: int) -> str` utility function
  - [x] 1.2 Create `render_session_header_html(session_number: int, session_info: str) -> str` function
  - [x] 1.3 Add `session_number` to GameState (default 1) if not present
  - [x] 1.4 Format subtitle with current date and optional additional info
  - [x] 1.5 Update `render_main_content()` to use dynamic session number from state

- [x] Task 2: Enhance mode indicator with Watching/Playing states (AC: #2, #3)
  - [x] 2.1 Create `render_mode_indicator_html(ui_mode: str, is_generating: bool) -> str` function
  - [x] 2.2 Update mode indicator to show "Watching" (watch mode) or "Playing as [Character]" (play mode)
  - [x] 2.3 Add `is_generating` state to session_state to track active generation
  - [x] 2.4 Pulse dot shows when `is_generating=True` and mode is "watch"
  - [x] 2.5 Show character name in play mode indicator using character color

- [x] Task 3: Add session controls section to sidebar (AC: #4)
  - [x] 3.1 Create `render_session_controls()` function
  - [x] 3.2 Add `is_paused` state to session_state (default False)
  - [x] 3.3 Implement Pause/Resume button with toggle logic
  - [x] 3.4 Add speed control dropdown (Slow, Normal, Fast) storing to `playback_speed` state
  - [x] 3.5 Apply secondary button styling per button hierarchy

- [x] Task 4: Add CSS for session controls (AC: #4)
  - [x] 4.1 Add `.session-controls` container styling
  - [x] 4.2 Add `.control-button.secondary` styling
  - [x] 4.3 Add speed dropdown styling matching theme

- [x] Task 5: Write comprehensive tests
  - [x] 5.1 Test `int_to_roman()` for values 1-50 and edge cases
  - [x] 5.2 Test `render_session_header_html()` produces correct structure
  - [x] 5.3 Test `render_mode_indicator_html()` for watch/play modes
  - [x] 5.4 Test mode indicator shows character name when controlled
  - [x] 5.5 Test pause/resume state toggle logic
  - [x] 5.6 Test speed control state changes

## Dev Notes

### Existing Implementation Analysis

The current `app.py` already has a basic session header implementation:

```python
# Current implementation (app.py:369-375)
st.markdown(
    '<div class="session-header">'
    '<h1 class="session-title">Session I</h1>'
    '<p class="session-subtitle">Game will begin when started</p>'
    "</div>",
    unsafe_allow_html=True,
)
```
[Source: app.py:369-375]

**Issues with current implementation:**
1. Session number is hardcoded as "Session I"
2. Subtitle is static placeholder text
3. No connection to actual game state

### Mode Indicator (Already Exists)

The mode indicator is already implemented in `render_sidebar()`:

```python
# Current implementation (app.py:328-335)
ui_mode = st.session_state.get("ui_mode", "watch")
mode_label = "Watch Mode" if ui_mode == "watch" else "Play Mode"
mode_class = "watch" if ui_mode == "watch" else "play"
st.markdown(
    f'<div class="mode-indicator {mode_class}">'
    f'<span class="pulse-dot"></span>{mode_label}</div>',
    unsafe_allow_html=True,
)
```
[Source: app.py:328-335]

**Enhancements needed:**
1. Show "Watching" vs "Playing as [Character Name]" instead of "Watch Mode" / "Play Mode"
2. Add `is_generating` state to control pulse animation visibility
3. Apply character color to play mode indicator text

### CSS Foundation (from Story 2.2)

Session header CSS classes are already defined in `styles/theme.css`:

```css
.session-header {
    text-align: center;
    padding: var(--space-lg) 0;           /* 24px */
    border-bottom: 1px solid var(--bg-secondary);
    margin-bottom: var(--space-lg);
}

.session-title {
    font-family: Lora, Georgia, serif;
    font-size: 24px;
    font-weight: 600;
    color: var(--color-dm);               /* #D4A574 */
    letter-spacing: 0.05em;
    margin: 0;
}

.session-subtitle {
    font-family: Inter, system-ui, sans-serif;
    font-size: 13px;
    color: var(--text-secondary);         /* #B8A896 */
    margin-top: var(--space-xs);
}
```
[Source: styles/theme.css - Session Header section]

Mode indicator CSS is also defined:

```css
.mode-indicator {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);                 /* 4px */
    padding: 4px 12px;
    border-radius: 16px;
    font-family: Inter, system-ui, sans-serif;
    font-size: 12px;
    font-weight: 500;
}

.mode-indicator.watch {
    background: rgba(107, 142, 107, 0.2); /* Success green, transparent */
    color: #6B8E6B;
}

.mode-indicator.play {
    background: rgba(232, 168, 73, 0.2);  /* Accent amber, transparent */
    color: var(--accent-warm);            /* #E8A849 */
}

.mode-indicator .pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
}
```
[Source: styles/theme.css - Mode Indicator section]

### Roman Numeral Conversion

For session numbers, use roman numerals per UX spec (e.g., "Session VII" not "Session 7"):

```python
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

    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I']

    result = ""
    for i, v in enumerate(val):
        while num >= v:
            result += syms[i]
            num -= v
    return result
```

### Session State Keys

Per architecture.md, these session state keys will be used/added:

**Existing:**
- `st.session_state["game"]` - GameState object
- `st.session_state["ui_mode"]` - "watch" | "play"
- `st.session_state["controlled_character"]` - str | None

**New for this story:**
- `st.session_state["is_generating"]` - bool (default False)
- `st.session_state["is_paused"]` - bool (default False)
- `st.session_state["playback_speed"]` - "slow" | "normal" | "fast" (default "normal")

[Source: architecture.md#Streamlit Session State]

### Session Number in GameState

The GameState TypedDict should track the session number. Check if it exists:

```python
# In models.py GameState definition
class GameState(TypedDict):
    ground_truth_log: list[str]
    turn_queue: list[str]
    current_turn: str
    agent_memories: dict[str, AgentMemory]
    game_config: GameConfig | None
    characters: dict[str, CharacterConfig]
    human_active: bool
    controlled_character: str | None
    # Add if not present:
    session_number: int  # Default 1
```

If not in models.py, add it. Then update `populate_game_state()` to include it.

### Button Hierarchy (from UX Spec)

Per UX Design Specification:

| Level | Use Cases | Background | Border | Text Color |
|-------|-----------|------------|--------|------------|
| **Primary** | Save, Continue | `--accent-warm` | None | `--bg-primary` |
| **Secondary** | Pause/Resume, Configure | Transparent | 1px `--text-secondary` | `--text-primary` |

For Pause/Resume button, use secondary style.

[Source: ux-design-specification.md#Button Hierarchy]

### Speed Control Options

Per acceptance criteria, speed control should offer options for Epic 3 integration:
- Slow: Longer pause between turns for reading
- Normal: Default pacing
- Fast: Minimal pause between turns

These values will be used by Epic 3 (Human Participation) to control turn timing.

### Implementation Approach

**Recommended order:**

1. **Task 1 first** - Create roman numeral converter and session header
2. **Task 5.1-5.2** - Write tests for Task 1
3. **Task 2** - Enhance mode indicator with generation state
4. **Task 5.3-5.4** - Write tests for Task 2
5. **Task 3** - Add session controls (Pause/Resume, Speed)
6. **Task 4** - Add CSS for session controls
7. **Task 5.5-5.6** - Write remaining tests

### Session Info Format

The subtitle should show meaningful session info:

```python
# Example formats:
# New session: "January 27, 2026"
# Resumed session: "January 27, 2026 • Turn 15"
# With campaign name: "The Lost Mine • Turn 15"

def get_session_subtitle(game: GameState) -> str:
    """Generate session subtitle text.

    Args:
        game: Current game state.

    Returns:
        Formatted subtitle string.
    """
    from datetime import date

    today = date.today().strftime("%B %d, %Y")
    turn_count = len(game.get("ground_truth_log", []))

    if turn_count > 0:
        return f"{today} • Turn {turn_count}"
    return today
```

### Mode Indicator Enhancement

For play mode, show the controlled character's name and use their color:

```python
def render_mode_indicator_html(
    ui_mode: str,
    is_generating: bool,
    controlled_character: str | None,
    characters: dict[str, CharacterConfig],
) -> str:
    """Generate HTML for mode indicator badge.

    Args:
        ui_mode: "watch" or "play"
        is_generating: Whether story is actively generating
        controlled_character: Agent key of controlled character, or None
        characters: Dict of agent_key -> CharacterConfig

    Returns:
        HTML string for mode indicator.
    """
    if ui_mode == "watch":
        pulse_class = "" if not is_generating else ""  # Always show pulse in watch
        return (
            '<div class="mode-indicator watch">'
            '<span class="pulse-dot"></span>Watching</div>'
        )
    else:
        # Play mode - show character name
        char_config = characters.get(controlled_character)
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
```

### CSS Addition for Character-Colored Mode Indicator

Add to `styles/theme.css`:

```css
/* Mode indicator character colors for play mode */
.mode-indicator.play.fighter {
    background: rgba(196, 92, 74, 0.2);
    color: var(--color-fighter);
}
.mode-indicator.play.rogue {
    background: rgba(107, 142, 107, 0.2);
    color: var(--color-rogue);
}
.mode-indicator.play.wizard {
    background: rgba(123, 104, 184, 0.2);
    color: var(--color-wizard);
}
.mode-indicator.play.cleric {
    background: rgba(74, 144, 164, 0.2);
    color: var(--color-cleric);
}
```

### Session Controls CSS

Add to `styles/theme.css`:

```css
/* ==========================================================================
   Session Controls (Story 2.5)
   ========================================================================== */

.session-controls {
    margin-top: var(--space-md);
    padding: var(--space-sm);
}

.session-controls .control-row {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    margin-bottom: var(--space-sm);
}

.session-controls .control-label {
    font-family: var(--font-ui);
    font-size: var(--text-system);
    color: var(--text-secondary);
    min-width: 60px;
}

/* Secondary button style (per button hierarchy) */
.control-button-secondary {
    background: transparent;
    border: 1px solid var(--text-secondary);
    color: var(--text-primary);
    border-radius: 4px;
    padding: 6px 12px;
    font-family: var(--font-ui);
    font-size: var(--text-system);
    cursor: pointer;
    transition: all 0.15s ease;
}

.control-button-secondary:hover {
    background: var(--bg-message);
    border-color: var(--text-primary);
}

/* Speed dropdown styling */
.speed-select {
    background: var(--bg-secondary);
    border: 1px solid var(--bg-message);
    color: var(--text-primary);
    border-radius: 4px;
    padding: 6px 12px;
    font-family: var(--font-ui);
    font-size: var(--text-system);
    cursor: pointer;
}
```

### Previous Story Intelligence (from Story 2.4)

**Key Learnings:**
- HTML escaping is critical for all user/agent content
- Separate HTML generation from Streamlit rendering for testability
- Use `_html` suffix functions for pure HTML generation
- CSS classes from theme.css work correctly with `st.markdown()`
- Streamlit buttons need wrapper divs for CSS targeting
- Test classes organized by functionality

**Files Modified in Story 2.4:**
- `app.py` - Added character card rendering functions
- `styles/theme.css` - Added Streamlit button overrides
- `tests/test_app.py` - Added 28 new tests

[Source: _bmad-output/implementation-artifacts/2-4-party-panel-character-cards.md]

### Git Intelligence (Recent Commits)

**Recent commit pattern (eb93602):**
```
Implement Story 2.4: Party Panel & Character Cards with code review fixes
```

**Commit structure to follow:**
```
Implement Story 2.5: Session Header & Controls with code review fixes
```

All tests passing (389+) before this story.

### Architecture Compliance

Per architecture.md, this story:
- Keeps UI rendering logic in `app.py` (Viewer Interface primary module)
- Extends existing CSS classes from `styles/theme.css`
- Accesses state via `st.session_state` keys
- Follows PEP 8 naming conventions (snake_case functions)
- May need to update `models.py` to add `session_number` to GameState

[Source: architecture.md#FR Category to Module Mapping]

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR31 | Session controls access | Pause/Resume button, Speed control in sidebar |

[Source: prd.md#Viewer Interface, epics.md#Story 2.5]

### What This Story Does NOT Do

- Does NOT implement actual pause/resume game logic (Story 3.5: Pause, Resume & Speed Control)
- Does NOT implement speed control timing logic (Story 3.5)
- Does NOT start/stop game generation (just provides UI controls)
- Does NOT implement session management (Story 4.3: Campaign Organization)

This story creates the UI controls and visual elements. Stories 3.5 and 4.x will implement the actual functionality these controls trigger.

### Testing Strategy

Organize tests in dedicated test class within `tests/test_app.py`:

```python
class TestSessionHeader:
    """Tests for session header rendering."""

class TestRomanNumerals:
    """Tests for int_to_roman conversion."""

class TestModeIndicator:
    """Tests for mode indicator rendering."""

class TestSessionControls:
    """Tests for session controls UI."""
```

**Test Pattern (from previous stories):**
```python
def test_int_to_roman_basic():
    """Test basic roman numeral conversion."""
    assert int_to_roman(1) == "I"
    assert int_to_roman(4) == "IV"
    assert int_to_roman(9) == "IX"
    assert int_to_roman(42) == "XLII"

def test_render_session_header_html_structure():
    """Test session header produces correct HTML."""
    html = render_session_header_html(7, "January 27, 2026")
    assert 'class="session-header"' in html
    assert 'class="session-title"' in html
    assert 'Session VII' in html
    assert 'January 27, 2026' in html
```

### Security Consideration

**HTML Escaping:** All session info text must be escaped before rendering:

```python
from html import escape as escape_html

def render_session_header_html(session_number: int, session_info: str) -> str:
    roman = int_to_roman(session_number)
    return (
        '<div class="session-header">'
        f'<h1 class="session-title">Session {escape_html(roman)}</h1>'
        f'<p class="session-subtitle">{escape_html(session_info)}</p>'
        '</div>'
    )
```

### Project Structure Notes

- Session header and controls logic goes in `app.py` (rendering module)
- CSS additions go in `styles/theme.css`
- Tests go in `tests/test_app.py` (extend existing test file)
- May need to update `models.py` for `session_number` in GameState

### References

- [Source: planning-artifacts/ux-design-specification.md#Session Header] - Session header spec (CSS included)
- [Source: planning-artifacts/ux-design-specification.md#Mode Indicator] - Mode indicator spec
- [Source: planning-artifacts/ux-design-specification.md#Button Hierarchy] - Button styling hierarchy
- [Source: planning-artifacts/architecture.md#Streamlit Session State] - Session state keys
- [Source: styles/theme.css] - Existing CSS classes
- [Source: epics.md#Story 2.5] - Full acceptance criteria
- [Source: _bmad-output/implementation-artifacts/2-4-party-panel-character-cards.md] - Previous story patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

No debug issues encountered.

### Completion Notes List

- Implemented `int_to_roman()` function for roman numeral conversion (1-3999)
- Created `render_session_header_html()` for dynamic session header with roman numerals
- Added `get_session_subtitle()` to generate subtitle with date and turn count
- Added `session_number` field to GameState TypedDict in models.py
- Created `render_mode_indicator_html()` with support for watch/play modes and character colors
- Added new session state keys: `is_generating`, `is_paused`, `playback_speed`
- Implemented `handle_pause_toggle()` for pause/resume button logic
- Created `render_session_controls()` function with Pause/Resume button and Speed dropdown
- Added CSS for character-colored mode indicators (fighter/rogue/wizard/cleric)
- Added CSS for session controls (secondary button styling, speed dropdown)
- Added 49 new tests covering roman numerals, session header, mode indicator, and session controls
- All 466 tests pass with no regressions
- Pyright type checking passes with 0 errors
- Ruff linting passes for all modified Python files

### File List

**Modified:**
- app.py - Added session header, mode indicator, and session controls functions
- models.py - Added `session_number` field to GameState TypedDict
- styles/theme.css - Added CSS for character-colored mode indicators and session controls
- tests/test_app.py - Added 49 new tests for Story 2.5 functionality

### Change Log

- 2026-01-27: Implemented Story 2.5 - Session Header & Controls
  - Dynamic session header with roman numerals (AC #1)
  - Enhanced mode indicator with Watching/Playing states (AC #2, #3)
  - Session controls (Pause/Resume, Speed) in sidebar (AC #4)
  - 49 new tests, all passing (466 total)

- 2026-01-27: Code Review Fixes Applied
  - Fixed CSS sidebar button styling conflict (was overriding character card buttons)
  - Removed redundant game/controlled_character variable declarations in render_sidebar
  - Added st.rerun() to speed control dropdown for consistency
  - Renamed selectbox key from "speed_select" to "session_speed_select" (namespace collision prevention)
  - Added explicit comment documenting play mode pulse dot behavior
  - Wrapped session controls in .session-controls div to apply CSS styling
