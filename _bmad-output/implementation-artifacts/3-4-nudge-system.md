# Story 3.4: Nudge System

Status: review

## Story

As a **user**,
I want **to send suggestions to influence the game without taking full control**,
so that **I can guide the story subtly while staying in observation mode**.

## Acceptance Criteria

1. **Given** I am in Watch Mode
   **When** I access the Nudge feature
   **Then** a lightweight input appears for typing a suggestion (FR20)

2. **Given** I type a nudge like "The rogue should check for traps"
   **When** I submit it
   **Then** the suggestion is added to the DM's context for the next turn
   **And** I remain in Watch Mode (not controlling any character)

3. **Given** a nudge has been submitted
   **When** the DM generates the next response
   **Then** it may incorporate the suggestion naturally
   **And** the nudge is not shown directly in the narrative

4. **Given** I send a nudge
   **When** it's processed
   **Then** a subtle toast notification confirms "Nudge sent"
   **And** the nudge input clears

5. **Given** the Nudge feature
   **When** compared to Drop-In
   **Then** Nudge is less intrusive - I don't control a specific character
   **And** the DM has discretion on whether/how to incorporate it

## Tasks / Subtasks

- [x] Task 1: Add session state for nudge system (AC: #1, #2)
  - [x] 1.1 Add `pending_nudge: str | None` to `initialize_session_state()` in app.py
  - [x] 1.2 Add `nudge_submitted: bool` flag for toast notification state
  - [x] 1.3 Add type hints to models.py if needed for GameState nudge handling (not needed - session state only)
  - [x] 1.4 Write tests for session state initialization

- [x] Task 2: Create nudge handler function (AC: #2, #4)
  - [x] 2.1 Create `handle_nudge_submit(nudge: str) -> None` in app.py
  - [x] 2.2 Sanitize input (strip whitespace, max 1000 chars)
  - [x] 2.3 Store sanitized nudge in `st.session_state["pending_nudge"]`
  - [x] 2.4 Set `nudge_submitted = True` for toast display
  - [x] 2.5 Write tests for handler validation and state updates

- [x] Task 3: Create nudge input UI component (AC: #1)
  - [x] 3.1 Create `render_nudge_input_html() -> str` for HTML structure
  - [x] 3.2 Create `render_nudge_input() -> None` Streamlit wrapper
  - [x] 3.3 Add guard condition: only show when NOT controlling a character
  - [x] 3.4 Style with text_area + button matching existing patterns
  - [x] 3.5 Write tests for conditional rendering based on human_active state

- [x] Task 4: Add CSS styling for nudge widget (AC: #1)
  - [x] 4.1 Add `.nudge-input-container` styling to theme.css
  - [x] 4.2 Add `.nudge-label` and `.nudge-hint` typography
  - [x] 4.3 Style text area with campfire aesthetic (green accent for suggestions)
  - [x] 4.4 Ensure visual distinction from Drop-In controls

- [x] Task 5: Integrate nudge into sidebar (AC: #1)
  - [x] 5.1 Add `render_nudge_input()` call in `render_sidebar()` after session controls
  - [x] 5.2 Add separator (st.markdown("---")) before nudge section
  - [x] 5.3 Test sidebar layout with nudge widget

- [x] Task 6: Integrate nudge into DM context (AC: #2, #3)
  - [x] 6.1 Modify `_build_dm_context()` in agents.py to read pending_nudge
  - [x] 6.2 Add "Player Suggestion" section to context when nudge present
  - [x] 6.3 Use neutral framing: "The player offers this thought: {nudge}"
  - [x] 6.4 Write tests for DM context building with/without nudge

- [x] Task 7: Clear nudge after DM processes it (AC: #3)
  - [x] 7.1 Clear `pending_nudge` in `dm_turn()` after context is built
  - [x] 7.2 Ensure nudge is single-use (consumed after one DM turn)
  - [x] 7.3 Write tests for nudge clearing lifecycle

- [x] Task 8: Implement toast notification (AC: #4)
  - [x] 8.1 Add toast display after nudge submission in render_nudge_input()
  - [x] 8.2 Use `st.success()` with appropriate icon and message
  - [x] 8.3 Clear `nudge_submitted` flag after displaying toast
  - [x] 8.4 Write tests for toast notification flow

- [x] Task 9: Write comprehensive acceptance tests
  - [x] 9.1 Test full nudge flow: type -> submit -> DM receives -> cleared
  - [x] 9.2 Test nudge visibility only in Watch Mode
  - [x] 9.3 Test nudge does NOT change ui_mode or human_active
  - [x] 9.4 Test nudge input validation (empty, whitespace, max length)
  - [x] 9.5 Test nudge overwrite behavior (new nudge replaces old)
  - [x] 9.6 Test nudge with paused game state (nudge stored, processed when resumed)
  - [x] 9.7 Integration test: nudge flow end-to-end

## Dev Notes

### Existing Infrastructure Analysis

The codebase has excellent existing infrastructure for this feature:

**Session State Pattern (app.py:697-714):**
- Uses `st.session_state["key"] = value` consistently
- Related state: `human_active`, `controlled_character`, `ui_mode`
- Add: `pending_nudge`, `nudge_submitted`

**Handler Pattern (app.py:832-869):**
```python
def handle_[action]() -> None:
    """Handle [action]."""
    # Validate
    # Update session state
    # Clean up related state
```

**Render Pattern (app.py:449-469):**
```python
def render_[component]_html(...) -> str:
    """Generate HTML for [component]."""
    return f'<div class="...">{content}</div>'

def render_[component](...) -> None:
    """Render [component] to Streamlit."""
    st.markdown(html, unsafe_allow_html=True)
```

**DM Context Building (agents.py:331-369):**
- `_build_dm_context()` constructs context_parts list
- Sections: Long-term summary, Recent events, Player knowledge
- **Integration point: Add "Player Suggestion" section here**

### Key Differences from Drop-In

| Aspect | Drop-In | Nudge |
|--------|---------|-------|
| Control level | Full character control | Suggestion only |
| ui_mode change | watch -> play | No change (stay in watch) |
| human_active | True | False (unchanged) |
| controlled_character | Set to agent key | None (unchanged) |
| Input area | Large, character-specific | Small, generic |
| Toast | Mode indicator changes | "Nudge sent" toast |
| Effect on narrative | Player's action logged | DM incorporates naturally |
| DM discretion | None - player acts | Full - may ignore |

### Architecture Compliance

Per architecture.md:

| Decision | Compliance |
|----------|------------|
| State lives in `st.session_state["game"]` | Following - nudge in session_state |
| Session state keys use underscore | `pending_nudge`, `nudge_submitted` |
| Execution is synchronous (blocking) | Following - instant state change |
| DM context via `_build_dm_context()` | Integration point identified |

[Source: architecture.md#Streamlit Integration, #LangGraph State Machine]

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR20 | Send suggestions without full control | Nudge input + DM context integration |
| FR17 | Watch Mode observation | Nudge preserves Watch Mode |

[Source: epics.md#Story 3.4, prd.md#Human Interaction]

### UX Spec Alignment

Per UX design specification:

**Nudge Feature:**
- Lightweight input that doesn't interrupt flow
- Subtle confirmation (toast, not modal)
- User remains in passive observation mode
- DM has discretion on incorporation

**Anti-Patterns to Avoid:**
- No confirmation dialogs for nudge
- No mode switch required
- No character selection needed

[Source: ux-design-specification.md#Nudge Feature, #Anti-Patterns to Avoid]

### What This Story Does NOT Do

- Does NOT implement Pause/Resume controls (Story 3.5)
- Does NOT implement keyboard shortcuts (Story 3.6)
- Does NOT change Drop-In functionality
- Does NOT add nudge history/log in narrative
- Does NOT allow multiple queued nudges (overwrite behavior)

### Previous Story Intelligence (from Story 3.3)

**Key Learnings:**
- `handle_drop_in_click()` pattern is clean and reusable
- Session state flags are well-established
- CSS classes follow `{component}-{modifier}` naming
- Tests use dedicated classes per feature area

**Files Modified in Story 3.3:**
- `app.py` - Handler functions, character card HTML
- `styles/theme.css` - Controlled state CSS
- `tests/test_app.py` - 49 new tests

**Pattern to follow:**
```
Implement Story 3.4: Nudge System with code review fixes
```

All tests passing (652) before this story.

[Source: _bmad-output/implementation-artifacts/3-3-release-control-character-switching.md]

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

#### Required Session State (app.py)

Add to `initialize_session_state()` after line 713:
```python
st.session_state["pending_nudge"] = None
st.session_state["nudge_submitted"] = False
```

#### Handler Function (app.py)

Create near line 832 (after handle_drop_in_click):
```python
def handle_nudge_submit(nudge: str) -> None:
    """Handle submission of nudge suggestion.

    Stores the nudge in session state for the DM's next turn context.
    Shows confirmation toast and clears input.
    """
    sanitized = nudge.strip()[:1000]  # Max 1000 chars

    if sanitized:
        st.session_state["pending_nudge"] = sanitized
        st.session_state["nudge_submitted"] = True
```

#### Render Functions (app.py)

Create near line 449 (with other render_ functions):
```python
def render_nudge_input_html() -> str:
    """Generate HTML for nudge input label and hint."""
    return '''
    <div class="nudge-input-container">
        <div class="nudge-label">Suggest Something</div>
        <p class="nudge-hint">Whisper a suggestion to the DM...</p>
    </div>
    '''


def render_nudge_input() -> None:
    """Render nudge input in the sidebar.

    Only visible in Watch Mode (when not controlling a character).
    """
    if st.session_state.get("human_active"):
        return  # Don't show nudge if already controlling

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
        st.rerun()

    # Show confirmation toast
    if st.session_state.get("nudge_submitted"):
        st.success("Nudge sent - the DM will consider your suggestion", icon="✨")
        st.session_state["nudge_submitted"] = False
```

#### Sidebar Integration (app.py)

Add to `render_sidebar()` after session controls section (near line 1035):
```python
    st.markdown("---")

    # Nudge System (Story 3.4)
    render_nudge_input()
```

#### DM Context Integration (agents.py)

Modify `_build_dm_context()` after line 366 (after Player Knowledge section):
```python
    # Player nudge/suggestion (Story 3.4 - Nudge System)
    import streamlit as st
    pending_nudge = st.session_state.get("pending_nudge")
    if pending_nudge:
        context_parts.append(
            f"## Player Suggestion\nThe player offers this thought: {pending_nudge}"
        )
```

#### Clear Nudge After Processing (agents.py)

Modify `dm_turn()` after context is built (after line 422):
```python
    # Clear nudge after reading (single-use)
    import streamlit as st
    st.session_state["pending_nudge"] = None
```

#### CSS Styling (styles/theme.css)

Add after existing sidebar styles:
```css
/* ==========================================================================
   Nudge Input Widget (Story 3.4)
   ========================================================================== */

.nudge-input-container {
  margin-top: var(--space-md);
  padding-top: var(--space-md);
}

.nudge-label {
  display: block;
  font-family: var(--font-ui);
  font-size: var(--text-system);
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: var(--space-xs);
}

.nudge-hint {
  font-family: var(--font-ui);
  font-size: 12px;
  color: var(--text-secondary);
  margin: var(--space-xs) 0 var(--space-sm) 0;
  font-style: italic;
}

/* Nudge text area - subtle green accent (suggestion/nature theme) */
[data-testid="stSidebar"] .nudge-input-container + div textarea {
  background: var(--bg-message) !important;
  border: 1px solid var(--bg-message) !important;
}

[data-testid="stSidebar"] .nudge-input-container + div textarea:focus {
  border-color: var(--color-rogue) !important;  /* Green for suggestions */
}
```

### Testing Strategy

Organize tests in dedicated test classes within `tests/test_app.py`:

```python
class TestNudgeSessionState:
    """Tests for nudge session state initialization."""

class TestNudgeHandler:
    """Tests for handle_nudge_submit() function."""

class TestNudgeInput:
    """Tests for nudge input rendering."""

class TestNudgeDMContext:
    """Tests for nudge integration in DM context."""

class TestNudgeToast:
    """Tests for nudge confirmation toast."""

class TestStory34AcceptanceCriteria:
    """Integration tests for full Story 3.4 acceptance criteria."""
```

**Test Patterns:**

```python
def test_nudge_initializes_as_none():
    """Test that pending_nudge initializes as None."""
    initialize_session_state()
    assert st.session_state.get("pending_nudge") is None
    assert st.session_state.get("nudge_submitted") is False

def test_handle_nudge_submit_stores_sanitized():
    """Test that nudge handler stores sanitized input."""
    handle_nudge_submit("  The rogue should check for traps  ")
    assert st.session_state.get("pending_nudge") == "The rogue should check for traps"
    assert st.session_state.get("nudge_submitted") is True

def test_nudge_hidden_when_controlling_character():
    """Test that nudge input is hidden in Play Mode."""
    st.session_state["human_active"] = True
    # render_nudge_input() should return early
    # Verify no nudge container in rendered output

def test_nudge_visible_in_watch_mode():
    """Test that nudge input appears in Watch Mode."""
    st.session_state["human_active"] = False
    # render_nudge_input() should render
    # Verify nudge container present

def test_nudge_does_not_change_ui_mode():
    """Test that submitting nudge keeps user in Watch Mode."""
    st.session_state["ui_mode"] = "watch"
    st.session_state["human_active"] = False

    handle_nudge_submit("Check for traps")

    assert st.session_state.get("ui_mode") == "watch"
    assert st.session_state.get("human_active") is False

def test_dm_context_includes_nudge():
    """Test that DM context includes pending nudge."""
    st.session_state["pending_nudge"] = "The wizard should cast detect magic"
    state = create_test_game_state()

    context = _build_dm_context(state)

    assert "Player Suggestion" in context
    assert "detect magic" in context

def test_nudge_cleared_after_dm_turn():
    """Test that nudge is cleared after DM processes it."""
    st.session_state["pending_nudge"] = "Check for traps"
    state = create_test_game_state()

    dm_turn(state)

    assert st.session_state.get("pending_nudge") is None

def test_nudge_max_length_truncation():
    """Test that nudge is truncated to 1000 chars."""
    long_nudge = "x" * 1500

    handle_nudge_submit(long_nudge)

    assert len(st.session_state.get("pending_nudge")) == 1000

def test_empty_nudge_not_stored():
    """Test that empty/whitespace nudge is not stored."""
    handle_nudge_submit("   ")

    assert st.session_state.get("pending_nudge") is None

def test_nudge_overwrite_behavior():
    """Test that new nudge overwrites previous."""
    handle_nudge_submit("First suggestion")
    assert st.session_state.get("pending_nudge") == "First suggestion"

    handle_nudge_submit("Second suggestion")
    assert st.session_state.get("pending_nudge") == "Second suggestion"
```

### Security Considerations

- **Input Sanitization:** Strip whitespace, limit to 1000 characters
- **No HTML Rendering:** Nudge text goes to DM context only, not rendered in UI narrative
- **No XSS Risk:** Using `st.text_area` which handles escaping
- **Single Nudge:** Overwrite behavior prevents queue overflow

### Edge Cases

1. **Empty/Whitespace Nudge:** Don't store, don't show toast
2. **Very Long Nudge:** Truncate to 1000 characters
3. **Nudge While Game Paused:** Allow - nudge will be processed when resumed
4. **Nudge During Generation:** Allow - queued for next DM turn
5. **Multiple Rapid Nudges:** New nudge overwrites previous (no queue)
6. **Nudge Then Drop-In:** Pending nudge should remain, processed by DM
7. **Drop-In Then Nudge:** Nudge input hidden, can't submit
8. **Game Not Started:** Nudge input should still work (stored for first DM turn)

### CSS Variables Reference

Existing variables from theme.css:
```css
--color-rogue: #6B8E6B;         /* Green - used for suggestion accent */
--bg-message: #3D3530;          /* Input background */
--text-primary: #F5E6D3;        /* Primary text */
--text-secondary: #B8A896;      /* Secondary/hint text */
--space-xs: 4px;
--space-sm: 8px;
--space-md: 16px;
--font-ui: 'Inter', sans-serif;
--text-system: 13px;
```

### Project Structure Notes

- Handler function: `app.py` (near handle_drop_in_click)
- Render functions: `app.py` (with other render_ functions)
- Sidebar integration: `app.py` (render_sidebar)
- DM context: `agents.py` (_build_dm_context)
- Nudge clearing: `agents.py` (dm_turn)
- CSS: `styles/theme.css`
- Tests: `tests/test_app.py`

### References

- [Source: planning-artifacts/prd.md#Human Interaction FR17-FR24] - Functional requirements
- [Source: planning-artifacts/architecture.md#Streamlit Integration] - State management patterns
- [Source: planning-artifacts/ux-design-specification.md#Nudge Feature] - UX requirements
- [Source: planning-artifacts/epics.md#Story 3.4] - Full acceptance criteria
- [Source: app.py:697-714] - Session state initialization pattern
- [Source: app.py:832-869] - Handler function pattern
- [Source: agents.py:331-369] - DM context building
- [Source: agents.py:404-466] - DM turn execution
- [Source: _bmad-output/implementation-artifacts/3-3-release-control-character-switching.md] - Previous story patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - implementation completed without issues.

### Completion Notes List

- ✅ Implemented full Nudge System for Story 3.4
- ✅ Added `pending_nudge` and `nudge_submitted` session state variables
- ✅ Created `handle_nudge_submit()` with input sanitization (strip whitespace, max 1000 chars)
- ✅ Created `render_nudge_input_html()` and `render_nudge_input()` UI components
- ✅ Added CSS styling with green accent (--color-rogue) for suggestion theme
- ✅ Integrated nudge input into sidebar after session controls
- ✅ Modified `_build_dm_context()` to include "Player Suggestion" section when nudge present
- ✅ Added nudge clearing in `dm_turn()` to ensure single-use consumption
- ✅ Implemented toast notification with ✨ icon showing "Nudge sent"
- ✅ Added 28 comprehensive tests (23 in test_app.py, 5 in test_agents.py)
- ✅ All 680 tests pass with no regressions
- ✅ Ruff lint check passes

### File List

**Modified:**
- `app.py` - Added session state init, handle_nudge_submit(), render_nudge_input_html(), render_nudge_input(), sidebar integration
- `agents.py` - Added nudge reading in _build_dm_context(), nudge clearing in dm_turn()
- `styles/theme.css` - Added nudge widget CSS styling (container, label, hint, textarea, button)
- `tests/test_app.py` - Added 23 tests for nudge functionality
- `tests/test_agents.py` - Added 5 tests for DM context nudge integration

### Change Log

- 2026-01-28: Implemented Story 3.4 Nudge System - all tasks complete, 28 tests added, 680 total tests passing
