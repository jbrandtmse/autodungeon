# Story 3.6: Keyboard Shortcuts

Status: review

## Story

As a **user**,
I want **keyboard shortcuts for quick Drop-In and Release actions**,
so that **I can participate instantly without reaching for the mouse**.

## Acceptance Criteria

1. **Given** I am in Watch Mode
   **When** I press the `1` key
   **Then** I drop in as the first party member (e.g., Fighter)

2. **Given** I am in Watch Mode
   **When** I press `2`, `3`, or `4`
   **Then** I drop in as the second, third, or fourth party member respectively

3. **Given** I am controlling any character
   **When** I press the `Escape` key
   **Then** I release control and return to Watch Mode

4. **Given** keyboard shortcuts are active
   **When** I am typing in an input field
   **Then** the shortcuts are disabled to prevent accidental triggers

5. **Given** the keyboard shortcuts
   **When** displayed in a help tooltip or sidebar
   **Then** users can discover them: "Press 1-4 to drop in, Escape to release"

## Tasks / Subtasks

- [x] Task 1: Implement keyboard event listener infrastructure (AC: #1, #2, #3, #4)
  - [x] 1.1 Create `get_keyboard_shortcut_script() -> str` function that returns JavaScript for key event handling
  - [x] 1.2 Handle keydown events for keys `1`, `2`, `3`, `4`, and `Escape`
  - [x] 1.3 Add guard to ignore shortcuts when focus is on input/textarea elements (AC #4)
  - [x] 1.4 Use `st.components.v1.html` to inject the script
  - [x] 1.5 Write tests for script generation and key filtering logic

- [x] Task 2: Create keyboard action handler functions (AC: #1, #2, #3)
  - [x] 2.1 Create `handle_keyboard_drop_in(party_index: int) -> None` handler
  - [x] 2.2 Create `handle_keyboard_release() -> None` handler
  - [x] 2.3 Map numeric keys to party character indices (1=index 0, 2=index 1, etc.)
  - [x] 2.4 Validate party_index is within bounds of available characters
  - [x] 2.5 Write tests for handler functions

- [x] Task 3: Implement Streamlit-JavaScript communication (AC: #1, #2, #3)
  - [x] 3.1 Use `st.session_state` + `st.query_params` pattern for cross-boundary communication
  - [x] 3.2 Create `keyboard_action` query param to receive action from JavaScript
  - [x] 3.3 Add `process_keyboard_action()` function to check and process pending actions
  - [x] 3.4 Clear query param after processing to prevent re-triggering
  - [x] 3.5 Write tests for action processing flow

- [x] Task 4: Integrate keyboard handling into main app (AC: #1, #2, #3)
  - [x] 4.1 Call `inject_keyboard_shortcut_script()` in `render_main_content()` or `main()`
  - [x] 4.2 Call `process_keyboard_action()` early in the render cycle
  - [x] 4.3 Verify shortcuts work in watch mode and controlled character release
  - [x] 4.4 Verify existing `handle_drop_in_click()` is reused for actual state changes
  - [x] 4.5 Write integration tests for full keyboard shortcut flow

- [x] Task 5: Add keyboard shortcuts help display (AC: #5)
  - [x] 5.1 Create `render_keyboard_shortcuts_help_html() -> str` function
  - [x] 5.2 Add help text to sidebar: "Press 1-4 to drop in, Escape to release"
  - [x] 5.3 Style help text with subtle appearance matching theme
  - [x] 5.4 Write tests for help text rendering

- [x] Task 6: Add CSS for keyboard shortcuts help (AC: #5)
  - [x] 6.1 Add `.keyboard-shortcuts-help` CSS class to theme.css
  - [x] 6.2 Style with secondary text color and small font
  - [x] 6.3 Add subtle `<kbd>` tag styling for key indicators

- [x] Task 7: Write comprehensive acceptance tests
  - [x] 7.1 Test key `1` drops in as first party member
  - [x] 7.2 Test key `2`, `3`, `4` drop in as subsequent party members
  - [x] 7.3 Test `Escape` releases character control
  - [x] 7.4 Test shortcuts disabled when typing in text input
  - [x] 7.5 Test shortcuts disabled when typing in text area
  - [x] 7.6 Test help text displays in sidebar
  - [x] 7.7 Test shortcut when already controlling (should switch characters)
  - [x] 7.8 Test shortcut for non-existent party member (out of bounds)
  - [x] 7.9 Integration test: full keyboard shortcut workflow

## Dev Agent Record

### Agent Model
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References
None - implementation completed without debugging issues.

### Completion Notes
All acceptance criteria implemented and tested:
- AC #1: Keys 1-4 map to party member indices 0-3 for quick drop-in
- AC #2: JavaScript keydown listener handles number keys 1-4
- AC #3: Escape key releases character control via handle_keyboard_release()
- AC #4: Input field guard checks tagName for 'input' and 'textarea'
- AC #5: Help text rendered in sidebar with styled kbd tags

Additional features:
- Quick Switch: Pressing different number while controlling switches characters
- Toggle behavior: Pressing same number while controlling releases control
- Autopilot integration: Keyboard drop-in stops autopilot (like button click)
- Paused state: Shortcuts work when game is paused (intentional)
- DM exclusion: DM agent excluded from party character keys
- Bounds validation: Out-of-bounds indices handled gracefully

### File List
Modified files:
- `app.py` - Added keyboard shortcut functions (get_keyboard_shortcut_script, inject_keyboard_shortcut_script, get_party_character_keys, handle_keyboard_drop_in, handle_keyboard_release, process_keyboard_action, render_keyboard_shortcuts_help_html, render_keyboard_shortcuts_help), integrated into main() and render_sidebar()
- `styles/theme.css` - Added .keyboard-shortcuts-help and kbd styling
- `tests/test_app.py` - Added 50+ tests across 9 test classes

### Change Log
1. Added get_keyboard_shortcut_script() - JavaScript keydown listener with input guard
2. Added inject_keyboard_shortcut_script() - Injects script via st.components.v1.html
3. Added get_party_character_keys() - Returns ordered party member keys (excludes DM)
4. Added handle_keyboard_drop_in(party_index) - Maps key to party member, calls handle_drop_in_click
5. Added handle_keyboard_release() - Releases current character if controlling
6. Added process_keyboard_action() - Processes keyboard_action query param, clears after use
7. Added render_keyboard_shortcuts_help_html() - Generates help text HTML with kbd tags
8. Added render_keyboard_shortcuts_help() - Renders help in sidebar
9. Modified main() - Added process_keyboard_action() call early, inject_keyboard_shortcut_script() at end
10. Modified render_sidebar() - Added render_keyboard_shortcuts_help() after party panel
11. Added CSS for .keyboard-shortcuts-help and kbd styling

### Test Results
- 557 tests passing (50 new keyboard shortcut tests)
- ruff check: All checks passed
- ruff format: Applied
- pyright: 0 errors, 0 warnings

## Dev Notes

### Existing Infrastructure Analysis

The codebase has excellent infrastructure for keyboard shortcuts:

**Drop-In Handler (app.py:920-956):**
```python
def handle_drop_in_click(agent_key: str) -> None:
    """Handle Drop-In/Release button click."""
    controlled = st.session_state.get("controlled_character")
    if controlled == agent_key:
        # Release control
        st.session_state["controlled_character"] = None
        st.session_state["ui_mode"] = "watch"
        st.session_state["human_active"] = False
        st.session_state["human_pending_action"] = None
        st.session_state["waiting_for_human"] = False
    else:
        # Take control - stop autopilot first
        st.session_state["is_autopilot_running"] = False
        st.session_state["human_pending_action"] = None
        st.session_state["waiting_for_human"] = False
        st.session_state["controlled_character"] = agent_key
        st.session_state["ui_mode"] = "play"
        st.session_state["human_active"] = True
```

**Party Characters Access (app.py:680-690):**
```python
def get_party_characters(state: GameState) -> dict[str, CharacterConfig]:
    """Get party characters excluding DM."""
    characters = state.get("characters", {})
    return {key: config for key, config in characters.items() if key != "dm"}
```

**JavaScript Injection Pattern (app.py:356-367):**
```python
def inject_auto_scroll_script() -> None:
    """Inject JavaScript for auto-scroll behavior."""
    import streamlit.components.v1 as components
    auto_scroll_enabled = st.session_state.get("auto_scroll_enabled", True)
    if auto_scroll_enabled:
        components.html(get_auto_scroll_script(), height=0)
```

### Architecture Compliance

Per architecture.md:

| Decision | Compliance |
|----------|------------|
| State lives in `st.session_state` | Following - all state in session_state |
| Session state keys use underscore | `keyboard_action` will follow pattern |
| Execution is synchronous | Following - JS posts, Streamlit processes on rerun |
| UI responsive during LLM calls | Following - shortcuts work independently |

[Source: architecture.md#Streamlit Integration]

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR18 | Take control of any PC at any time | Keyboard shortcuts 1-4 enable instant drop-in |
| FR19 | Release control and return to AI | Escape key enables instant release |
| FR30 | Access Drop-In controls per character | Keyboard shortcuts as alternative to buttons |

[Source: epics.md#Story 3.6, prd.md#Human Interaction]

### UX Spec Alignment

Per UX design specification:

**Keyboard Shortcuts (Section: Character Interaction Patterns):**
- `1-4` keys map to party members for quick drop-in
- `Escape` releases current character
- No confirmation dialogs for reversible actions

**Interaction Rules:**
- Quick Switch: Pressing a different number while controlling switches characters
- Shortcuts disabled when typing in input fields

**Keyboard Navigation (Section: Accessibility):**
| Key | Action |
|-----|--------|
| `1-4` | Quick drop-in to party members |
| `Escape` | Release character / Close modal |

[Source: ux-design-specification.md#Character Interaction Patterns, #Keyboard Navigation]

### What This Story Does NOT Do

- Does NOT implement keyboard shortcuts for pause/resume (potential future enhancement)
- Does NOT implement keyboard shortcuts for speed control
- Does NOT implement keyboard shortcuts for nudge feature
- Does NOT implement modal closing via Escape (Epic 6 - config modal)
- Does NOT add custom key binding configuration
- Does NOT implement keyboard navigation for other UI elements (arrows, tab order)

### Previous Story Intelligence (from Story 3.5)

**Key Learnings:**
- Mode indicator paused state already implemented (app.py:407-457)
- Session controls render cleanly in sidebar (app.py:877-917)
- CSS transitions used for smooth state changes (theme.css:289-292)
- Tests organized by functional area in dedicated classes

**Files Modified in Story 3.5:**
- `app.py` - Mode indicator paused state, modal handlers
- `styles/theme.css` - Paused mode indicator CSS
- `tests/test_app.py` - 50+ new tests

**Pattern to follow:**
```
Implement Story 3.6: Keyboard Shortcuts with code review fixes
```

All tests passing (462+) before this story.

[Source: _bmad-output/implementation-artifacts/3-5-pause-resume-speed-control.md]

### Git Intelligence (Last 5 Commits)

```
1b03c46 Implement Stories 3.2 & 3.3: Drop-In Mode & Release Control with code review fixes
ca4cf72 Implement Story 3.1: Watch Mode & Autopilot with code review fixes
4bcc3ea Implement Stories 2.5 & 2.6: Session Header Controls & Real-time Narrative Flow with code review fixes
eb93602 Implement Story 2.4: Party Panel & Character Cards with code review fixes
9dfd9fa Implement Story 2.3: Narrative Message Display with code review fixes
```

**Pattern observed:** Stories are committed with "with code review fixes" suffix indicating adversarial review is run before commit.

### Implementation Details

#### JavaScript Keyboard Script (app.py)

Create a function to generate the keyboard event listener script:

```python
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
                // Skip if typing in input/textarea
                const activeElement = document.activeElement;
                const tagName = activeElement ? activeElement.tagName.toLowerCase() : '';
                if (tagName === 'input' || tagName === 'textarea') {
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
```

#### Keyboard Action Handlers (app.py)

Add handler functions for keyboard actions:

```python
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
```

#### Process Keyboard Action (app.py)

Add function to process keyboard actions from query params:

```python
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
```

#### Inject Script Function (app.py)

```python
def inject_keyboard_shortcut_script() -> None:
    """Inject JavaScript for keyboard shortcut handling.

    Adds event listeners for:
    - 1-4 keys: Quick drop-in to party members
    - Escape: Release character control
    """
    import streamlit.components.v1 as components
    components.html(get_keyboard_shortcut_script(), height=0)
```

#### Help Text Rendering (app.py)

```python
def render_keyboard_shortcuts_help_html() -> str:
    """Generate HTML for keyboard shortcuts help text.

    Returns:
        HTML string with keyboard shortcut hints.
    """
    return (
        '<div class="keyboard-shortcuts-help">'
        '<span class="help-text">Press </span>'
        '<kbd>1</kbd><kbd>2</kbd><kbd>3</kbd><kbd>4</kbd>'
        '<span class="help-text"> to drop in, </span>'
        '<kbd>Esc</kbd>'
        '<span class="help-text"> to release</span>'
        '</div>'
    )


def render_keyboard_shortcuts_help() -> None:
    """Render keyboard shortcuts help in sidebar."""
    st.markdown(render_keyboard_shortcuts_help_html(), unsafe_allow_html=True)
```

#### Sidebar Integration (app.py)

Modify `render_sidebar()` to include help text after party panel (around line 1139):

```python
# After party panel section, before divider
render_keyboard_shortcuts_help()
```

#### Main App Integration (app.py)

Modify `main()` to process keyboard actions and inject script:

```python
def main() -> None:
    """Main Streamlit application entry point."""
    # ... existing page config and CSS ...

    # Initialize session state
    initialize_session_state()

    # Process keyboard actions early (before render)
    if process_keyboard_action():
        st.rerun()

    # ... rest of main() ...

    # Inject keyboard shortcut script (at end, after render)
    inject_keyboard_shortcut_script()
```

#### CSS Styling (styles/theme.css)

Add at end of file:

```css
/* ==========================================================================
   Keyboard Shortcuts Help (Story 3.6)
   ========================================================================== */

.keyboard-shortcuts-help {
  font-family: var(--font-ui);
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: var(--space-sm);
  margin-bottom: var(--space-sm);
  text-align: center;
}

.keyboard-shortcuts-help .help-text {
  color: var(--text-secondary);
}

.keyboard-shortcuts-help kbd {
  display: inline-block;
  padding: 2px 6px;
  margin: 0 2px;
  font-family: var(--font-mono);
  font-size: 10px;
  background: var(--bg-message);
  border: 1px solid var(--bg-secondary);
  border-radius: 3px;
  color: var(--text-primary);
}
```

### Testing Strategy

Organize tests in dedicated test classes within `tests/test_app.py`:

```python
class TestKeyboardShortcutScript:
    """Tests for keyboard shortcut JavaScript generation."""

class TestKeyboardDropInHandler:
    """Tests for handle_keyboard_drop_in() function."""

class TestKeyboardReleaseHandler:
    """Tests for handle_keyboard_release() function."""

class TestProcessKeyboardAction:
    """Tests for process_keyboard_action() function."""

class TestKeyboardShortcutsHelp:
    """Tests for keyboard shortcuts help rendering."""

class TestStory36AcceptanceCriteria:
    """Integration tests for full Story 3.6 acceptance criteria."""
```

**Key Test Cases:**

```python
def test_keyboard_script_includes_number_keys():
    """Test that script handles keys 1-4 for drop-in."""
    script = get_keyboard_shortcut_script()
    assert "e.key >= '1'" in script
    assert "e.key <= '4'" in script

def test_keyboard_script_includes_escape():
    """Test that script handles Escape for release."""
    script = get_keyboard_shortcut_script()
    assert "e.key === 'Escape'" in script

def test_keyboard_script_skips_input_fields():
    """Test that script ignores shortcuts in input/textarea (AC #4)."""
    script = get_keyboard_shortcut_script()
    assert "tagName === 'input'" in script
    assert "tagName === 'textarea'" in script

def test_keyboard_drop_in_first_character():
    """Test key 1 drops in as first party member (AC #1)."""
    # Set up party with known order
    st.session_state["game"] = create_game_with_party(["fighter", "rogue", "wizard"])
    st.session_state["human_active"] = False

    handle_keyboard_drop_in(0)

    assert st.session_state.get("controlled_character") == "fighter"
    assert st.session_state.get("human_active") is True

def test_keyboard_drop_in_out_of_bounds():
    """Test that out-of-bounds index is handled safely (AC #2 edge case)."""
    st.session_state["game"] = create_game_with_party(["fighter", "rogue"])

    handle_keyboard_drop_in(5)  # Out of bounds

    assert st.session_state.get("controlled_character") is None  # No change

def test_keyboard_release_from_controlled():
    """Test Escape releases character control (AC #3)."""
    st.session_state["controlled_character"] = "fighter"
    st.session_state["human_active"] = True

    handle_keyboard_release()

    assert st.session_state.get("controlled_character") is None
    assert st.session_state.get("human_active") is False

def test_keyboard_release_when_not_controlling():
    """Test Escape does nothing when not controlling."""
    st.session_state["controlled_character"] = None

    handle_keyboard_release()

    assert st.session_state.get("controlled_character") is None  # Still None

def test_process_keyboard_action_drop_in():
    """Test processing drop_in_N action from query params."""
    st.query_params["keyboard_action"] = "drop_in_0"
    st.session_state["game"] = create_game_with_party(["fighter"])

    result = process_keyboard_action()

    assert result is True
    assert "keyboard_action" not in st.query_params  # Cleared
    assert st.session_state.get("controlled_character") == "fighter"

def test_process_keyboard_action_release():
    """Test processing release action from query params."""
    st.query_params["keyboard_action"] = "release"
    st.session_state["controlled_character"] = "fighter"

    result = process_keyboard_action()

    assert result is True
    assert "keyboard_action" not in st.query_params  # Cleared
    assert st.session_state.get("controlled_character") is None

def test_keyboard_shortcuts_help_html():
    """Test help text contains all shortcut keys (AC #5)."""
    html = render_keyboard_shortcuts_help_html()
    assert "<kbd>1</kbd>" in html
    assert "<kbd>2</kbd>" in html
    assert "<kbd>3</kbd>" in html
    assert "<kbd>4</kbd>" in html
    assert "<kbd>Esc</kbd>" in html
    assert "drop in" in html.lower()
    assert "release" in html.lower()

def test_keyboard_switch_character():
    """Test pressing different number switches characters (AC #1, #2)."""
    st.session_state["game"] = create_game_with_party(["fighter", "rogue", "wizard"])
    st.session_state["controlled_character"] = "fighter"
    st.session_state["human_active"] = True

    handle_keyboard_drop_in(1)  # Press '2' for rogue

    assert st.session_state.get("controlled_character") == "rogue"
    assert st.session_state.get("human_active") is True
```

### Security Considerations

- **No User Input to Script:** JavaScript script is static, no dynamic content interpolated
- **Query Param Sanitization:** Only predefined action strings are accepted
- **Index Validation:** Party index is validated before accessing character list
- **No XSS Risk:** Help text uses static HTML, no user-provided content

### Edge Cases

1. **No Party Members:** Shortcuts 1-4 should do nothing gracefully
2. **Fewer Than 4 Party Members:** Shortcuts for non-existent members should be ignored
3. **Already Controlling Same Character:** Pressing same number should release (toggle behavior)
4. **Pressing Number While Controlling Different Character:** Should switch to new character
5. **Escape When Not Controlling:** Should do nothing (no-op)
6. **Multiple Rapid Key Presses:** Query param clearing prevents double-processing
7. **Key Press During Generation:** Should still work (shortcuts don't block)
8. **Key Press While Paused:** Should still work (pause doesn't disable shortcuts)
9. **Focus on Streamlit Widgets:** Should NOT trigger shortcuts (input guard)

### CSS Variables Reference

Existing variables from theme.css:
```css
--font-ui: 'Inter', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', monospace;
--text-primary: #F5E6D3;
--text-secondary: #B8A896;
--bg-message: #3D3530;
--bg-secondary: #2D2520;
--space-sm: 8px;
```

### Project Structure Notes

- Keyboard script: `app.py` (get_keyboard_shortcut_script, inject_keyboard_shortcut_script)
- Action handlers: `app.py` (handle_keyboard_drop_in, handle_keyboard_release)
- Action processing: `app.py` (process_keyboard_action)
- Help rendering: `app.py` (render_keyboard_shortcuts_help_html, render_keyboard_shortcuts_help)
- Sidebar integration: `app.py` (render_sidebar)
- Main app integration: `app.py` (main)
- CSS: `styles/theme.css`
- Tests: `tests/test_app.py`

### Alternative Implementation Approach

If the query_params approach proves problematic with Streamlit's execution model, an alternative is to use `streamlit-js-eval` or maintain state in `st.session_state["pending_keyboard_action"]` with a hidden HTML form submission pattern. However, the query_params approach is preferred as it's native to Streamlit and doesn't require additional dependencies.

### References

- [Source: planning-artifacts/prd.md#Human Interaction FR17-FR24] - Functional requirements
- [Source: planning-artifacts/architecture.md#Streamlit Integration] - State management patterns
- [Source: planning-artifacts/ux-design-specification.md#Keyboard Navigation, #Character Interaction Patterns] - UX requirements
- [Source: planning-artifacts/epics.md#Story 3.6] - Full acceptance criteria
- [Source: app.py:920-956] - handle_drop_in_click() handler
- [Source: app.py:680-690] - get_party_characters() function
- [Source: app.py:356-367] - JavaScript injection pattern
- [Source: styles/theme.css] - CSS variables and theme
- [Source: _bmad-output/implementation-artifacts/3-5-pause-resume-speed-control.md] - Previous story patterns
