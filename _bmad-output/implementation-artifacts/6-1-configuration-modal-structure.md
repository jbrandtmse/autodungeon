# Story 6.1: Configuration Modal Structure

Status: done

## Story

As a **user**,
I want **a settings modal with organized tabs for different configuration areas**,
so that **I can access all settings in one place without leaving my session**.

## Acceptance Criteria

1. **Given** the sidebar
   **When** I click the "Configure" button
   **Then** a modal dialog opens centered on screen

2. **Given** the configuration modal
   **When** it opens
   **Then** it displays three tabs: "API Keys", "Models", "Settings"
   **And** uses the established dark theme styling (#1A1612 background, #2D2520 surfaces)

3. **Given** an active game session
   **When** I open the configuration modal
   **Then** the game automatically pauses (per UX flow)
   **And** the mode indicator shows "Paused"

4. **Given** the configuration modal is open
   **When** I close it (X button, Escape key, or click outside)
   **Then** the game automatically resumes
   **And** any saved changes take effect

5. **Given** I have unsaved changes in the modal
   **When** I attempt to close it
   **Then** a confirmation appears: "Discard changes?"
   **And** I can choose to save or discard

6. **Given** the modal styling
   **When** displayed
   **Then** it matches the campfire aesthetic with warm colors and Inter font

## Tasks / Subtasks

- [x] Task 1: Create Configure button in sidebar
  - [x] 1.1 Add "Configure" button to sidebar below "LLM Status" expander
  - [x] 1.2 Style button using secondary button styling (outline, matches theme)
  - [x] 1.3 Add click handler that calls `handle_config_modal_open()`
  - [x] 1.4 Write unit test for button rendering

- [x] Task 2: Implement config modal dialog structure
  - [x] 2.1 Create `render_config_modal()` function in app.py
  - [x] 2.2 Use `st.dialog` decorator pattern for modal container
  - [x] 2.3 Add modal header with title "Configuration" and close (X) button
  - [x] 2.4 Implement centered modal positioning via CSS
  - [x] 2.5 Set max-width to 600px per UX spec
  - [x] 2.6 Write unit test for modal rendering

- [x] Task 3: Implement tab navigation structure
  - [x] 3.1 Create three tabs using `st.tabs`: "API Keys", "Models", "Settings"
  - [x] 3.2 Add placeholder content in each tab for future story implementation
  - [x] 3.3 Style tabs with active/inactive states using CSS
  - [x] 3.4 Tab styling: Inter font, 14px, gold underline for active tab
  - [x] 3.5 Write unit test for tab structure

- [x] Task 4: Implement auto-pause on modal open (AC #3)
  - [x] 4.1 Update `handle_config_modal_open()` to store pre-modal pause state
  - [x] 4.2 Set `st.session_state["is_paused"] = True` when modal opens
  - [x] 4.3 Stop autopilot if running when modal opens
  - [x] 4.4 Verify mode indicator shows "Paused" via existing styling
  - [x] 4.5 Write integration test for auto-pause behavior

- [x] Task 5: Implement auto-resume on modal close (AC #4)
  - [x] 5.1 Update `handle_config_modal_close()` to restore pre-modal pause state
  - [x] 5.2 Handle close via X button click
  - [x] 5.3 Handle close via clicking outside modal (overlay click)
  - [x] 5.4 Add keyboard listener for Escape key to close modal
  - [x] 5.5 Write integration test for auto-resume behavior

- [x] Task 6: Implement unsaved changes detection (AC #5)
  - [x] 6.1 Add `st.session_state["config_has_changes"]` flag
  - [x] 6.2 Track changes to any config field within modal
  - [x] 6.3 Create `render_discard_confirmation()` function
  - [x] 6.4 Show confirmation dialog when closing with unsaved changes
  - [x] 6.5 Add "Save" and "Discard" buttons to confirmation
  - [x] 6.6 Write unit test for change detection logic

- [x] Task 7: Add modal CSS styling (AC #6)
  - [x] 7.1 Add `.config-modal` CSS class to theme.css
  - [x] 7.2 Style background: #1A1612, border: 1px solid #2D2520, border-radius: 12px
  - [x] 7.3 Add modal header styling with gold (#D4A574) title color
  - [x] 7.4 Style close button as ghost button with hover state
  - [x] 7.5 Add overlay styling: rgba(0,0,0,0.6) per UX spec
  - [x] 7.6 Add tab styling: active tab with amber underline, inactive muted
  - [x] 7.7 Write visual verification tests using chrome-devtools MCP

- [x] Task 8: Add Save/Cancel footer buttons
  - [x] 8.1 Create modal footer with "Save" and "Cancel" buttons
  - [x] 8.2 Style "Save" as primary button (amber background)
  - [x] 8.3 Style "Cancel" as secondary button (outline)
  - [x] 8.4 "Save" commits changes and closes modal
  - [x] 8.5 "Cancel" discards changes and closes modal (or triggers confirmation if changes)
  - [x] 8.6 Write unit tests for button behaviors

- [x] Task 9: Write acceptance tests
  - [x] 9.1 Test: Configure button visible in sidebar
  - [x] 9.2 Test: Modal opens centered when button clicked (AC #1)
  - [x] 9.3 Test: Modal displays three tabs (AC #2)
  - [x] 9.4 Test: Game pauses when modal opens (AC #3)
  - [x] 9.5 Test: Game resumes when modal closes (AC #4)
  - [x] 9.6 Test: Confirmation appears with unsaved changes (AC #5)
  - [x] 9.7 Test: Modal uses correct theme styling (AC #6)

## Dev Notes

### Implementation Strategy

This is the **foundation story** for Epic 6. It creates the modal structure that subsequent stories (6.2 API Keys, 6.3 Model Selection, 6.4 Context Limits) will populate with actual functionality.

**Key Decision:** Focus on modal infrastructure, not content. The tabs should have clear placeholder content indicating what will be implemented (e.g., "API key configuration coming in Story 6.2").

### Existing Foundation

**Auto-pause/resume already partially implemented (Story 3.5):**

```python
# app.py lines 1067-1088 - already exist
def handle_modal_open() -> None:
    """Handle config modal opening - auto-pause game."""
    st.session_state["pre_modal_pause_state"] = st.session_state.get("is_paused", False)
    st.session_state["is_paused"] = True
    st.session_state["modal_open"] = True

def handle_modal_close() -> None:
    """Handle config modal closing - restore previous pause state."""
    st.session_state["modal_open"] = False
    prev_state = st.session_state.get("pre_modal_pause_state", False)
    st.session_state["is_paused"] = prev_state
```

These handlers are already created but not wired to any UI. This story wires them up and adds the modal itself.

**Mode indicator paused state already styled (Story 3.5):**

```css
/* theme.css lines 502-517 */
.mode-indicator.paused {
  background: rgba(232, 168, 73, 0.2);
  color: var(--accent-warm);
}

.pause-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent-warm);
  /* No animation - static to differentiate from active states */
}
```

### Streamlit Dialog Pattern

Streamlit 1.40+ supports `st.dialog` decorator for modal dialogs:

```python
@st.dialog("Configuration", width="large")
def config_modal():
    """Render the configuration modal content."""
    # Tab structure
    tab1, tab2, tab3 = st.tabs(["API Keys", "Models", "Settings"])

    with tab1:
        st.markdown("API key configuration (Story 6.2)")
        # Placeholder for API key management

    with tab2:
        st.markdown("Model selection (Story 6.3)")
        # Placeholder for per-agent model selection

    with tab3:
        st.markdown("Settings (Stories 6.4, 6.5)")
        # Placeholder for context limits, etc.

    # Footer buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancel"):
            # Handle cancel with unsaved changes check
            pass
    with col2:
        if st.button("Save", type="primary"):
            # Handle save
            pass
```

**Note:** `st.dialog` creates a modal overlay automatically. Width options: "small", "large", or pixel value.

### Modal Behavior Requirements (from UX Spec)

| Behavior | Implementation |
|----------|----------------|
| Opens centered | Default `st.dialog` behavior |
| Dark overlay | `rgba(0,0,0,0.6)` via CSS |
| Traps focus | Default `st.dialog` behavior |
| Escape closes | Must implement via JavaScript |
| Click outside closes | Must implement via JavaScript (if changes, show confirmation) |

### Session State Keys

**New keys for this story:**

| Key | Type | Purpose |
|-----|------|---------|
| `config_modal_open` | bool | Whether config modal is displayed |
| `config_has_changes` | bool | Whether user has made unsaved changes |
| `config_original_values` | dict | Snapshot of config values when modal opened |

**Existing keys used:**

| Key | Type | Purpose |
|-----|------|---------|
| `is_paused` | bool | Game pause state |
| `pre_modal_pause_state` | bool | Pause state before modal opened |
| `modal_open` | bool | Generic modal open flag |
| `is_autopilot_running` | bool | Autopilot state |

### CSS Classes to Create

Add to `styles/theme.css`:

```css
/* Configuration Modal (Story 6.1) */
.config-modal {
    background: var(--bg-primary);        /* #1A1612 */
    border: 1px solid var(--bg-secondary);
    border-radius: 12px;
    max-width: 600px;
}

.config-modal-header {
    padding: var(--space-lg);
    border-bottom: 1px solid var(--bg-secondary);
}

.config-modal-title {
    font-family: var(--font-ui);
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
}

.config-modal-close {
    background: transparent;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 20px;
}

.config-modal-close:hover {
    color: var(--text-primary);
}

.config-tab {
    font-family: var(--font-ui);
    font-size: 14px;
    color: var(--text-secondary);
    padding: var(--space-md);
    border-bottom: 2px solid transparent;
}

.config-tab.active {
    color: var(--accent-warm);
    border-bottom-color: var(--accent-warm);
}

.config-modal-footer {
    padding: var(--space-lg);
    border-top: 1px solid var(--bg-secondary);
    display: flex;
    justify-content: flex-end;
    gap: var(--space-md);
}

/* Streamlit dialog overrides for theme consistency */
[data-testid="stDialog"] > div {
    background: var(--bg-primary) !important;
    border: 1px solid var(--bg-secondary) !important;
    border-radius: 12px !important;
}

[data-testid="stDialog"] [data-testid="stVerticalBlock"] {
    background: transparent !important;
}

/* Tab styling within config modal */
[data-testid="stDialog"] .stTabs [data-baseweb="tab-list"] {
    background: transparent;
    border-bottom: 1px solid var(--bg-secondary);
}

[data-testid="stDialog"] .stTabs [data-baseweb="tab"] {
    color: var(--text-secondary);
    font-family: var(--font-ui);
    font-size: 14px;
}

[data-testid="stDialog"] .stTabs [aria-selected="true"] {
    color: var(--accent-warm);
    border-bottom: 2px solid var(--accent-warm);
}
```

### Escape Key & Click Outside Handling

Streamlit's `st.dialog` doesn't natively support Escape key close or click-outside close with confirmation. Need JavaScript injection:

```python
def get_modal_close_script() -> str:
    """Generate JavaScript for modal close handling."""
    return """
    <script>
    (function() {
        // Only attach once
        if (window._configModalListenerAttached) return;
        window._configModalListenerAttached = true;

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                e.preventDefault();
                // Trigger close via URL param
                const url = new URL(window.location);
                url.searchParams.set('modal_action', 'close');
                window.location.href = url.toString();
            }
        });

        // Note: Click outside is handled by Streamlit's dialog backdrop
        // We intercept it via the close action
    })();
    </script>
    """
```

### Unsaved Changes Detection Pattern

```python
def has_unsaved_changes() -> bool:
    """Check if config modal has unsaved changes."""
    if not st.session_state.get("config_original_values"):
        return False

    original = st.session_state["config_original_values"]
    current = get_current_config_values()  # To be implemented in later stories

    return original != current


def snapshot_config_values() -> dict:
    """Take snapshot of current config values when modal opens."""
    # Placeholder - will be populated as Epic 6 progresses
    return {
        "api_keys": {},  # Story 6.2
        "models": {},    # Story 6.3
        "settings": {},  # Story 6.4/6.5
    }
```

### Discard Confirmation Dialog

Use nested `st.dialog` or warning container:

```python
def render_discard_confirmation() -> bool:
    """Render confirmation when closing with unsaved changes.

    Returns:
        True if user chose to discard, False if cancelled.
    """
    st.warning("You have unsaved changes. Discard them?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Discard", key="discard_btn"):
            return True
    with col2:
        if st.button("Keep Editing", key="keep_editing_btn"):
            return False

    return False
```

### Architecture Compliance

| Pattern | Compliance | Notes |
|---------|------------|-------|
| Session state for UI state | YES | Uses st.session_state for modal/config state |
| CSS via theme.css | YES | All styling in centralized stylesheet |
| Functions with docstrings | YES | All public functions documented |
| No inline styles | YES | All CSS in theme.css |
| Friendly narrative errors | YES | "Discard changes?" not technical |

### Performance Considerations

- Modal should not re-render on every keystroke (use form pattern if needed)
- Config values snapshot taken once on modal open, not continuously
- JavaScript event listeners attached once (guard with flag)

### Edge Cases

1. **Modal open during generation:** Auto-pause stops generation mid-turn safely
2. **Escape key while typing in input:** Disable Escape shortcut when focus in input field
3. **Rapid open/close:** Debounce modal state changes
4. **Session expires while modal open:** Handle gracefully with error message
5. **No API keys configured:** Modal should still open (first-time user flow)

### What This Story Implements

1. "Configure" button in sidebar
2. Modal dialog structure with `st.dialog`
3. Three-tab navigation (API Keys, Models, Settings)
4. Auto-pause/resume on modal open/close
5. Unsaved changes detection and confirmation
6. CSS styling for campfire aesthetic
7. Keyboard (Escape) and mouse (X button) close handling

### What This Story Does NOT Implement

- Actual API key entry fields (Story 6.2)
- Model selection dropdowns (Story 6.3)
- Context limit configuration (Story 6.4)
- Mid-campaign provider switching logic (Story 6.5)
- API key validation (Story 6.2)
- Model availability checking (Story 6.3)

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR42 | Select DM LLM provider | Modal structure with Models tab (content in 6.3) |
| FR43 | Select PC LLM providers | Modal structure with Models tab (content in 6.3) |
| FR44 | Select summarization model | Modal structure with Models tab (content in 6.3) |
| FR45 | Configure context limits | Modal structure with Settings tab (content in 6.4) |
| FR47 | Override API keys in UI | Modal structure with API Keys tab (content in 6.2) |

### Testing Strategy

**Unit Tests (pytest):**
- Button rendering
- Modal open/close handlers
- Session state management
- Unsaved changes detection logic

**Integration Tests (pytest + mock):**
- Auto-pause on modal open
- Auto-resume on modal close
- Tab navigation

**Visual Tests (chrome-devtools MCP):**
- Modal centered on screen
- Correct colors (#1A1612, #2D2520, #D4A574)
- Tab styling matches spec
- Button styling matches hierarchy

### Files to Modify

| File | Changes |
|------|---------|
| `app.py` | Add Configure button, modal render functions, handlers |
| `styles/theme.css` | Add config modal CSS classes |

### Files to Create

None - all code goes in existing files.

### Dependencies

- Streamlit 1.40.0+ (for `st.dialog` support)
- Existing auto-pause handlers from Story 3.5 (lines 1067-1088 in app.py)
- Existing mode indicator paused styling from Story 3.5 (theme.css)

### References

- [Source: planning-artifacts/prd.md#LLM Configuration FR42-FR47]
- [Source: planning-artifacts/architecture.md#LLM Provider Abstraction]
- [Source: planning-artifacts/ux-design-specification.md#Flow 5: Configuration Setup]
- [Source: planning-artifacts/ux-design-specification.md#Component Strategy - Config Modal]
- [Source: planning-artifacts/epics.md#Story 6.1]
- [Source: app.py#handle_modal_open] - Existing auto-pause handler
- [Source: styles/theme.css#Mode Indicator Paused] - Existing paused styling

---

## Code Review

**Review Date:** 2026-01-28
**Reviewer:** Claude Opus 4.5 (BMAD code-review workflow)
**Status:** PASSED

### Issues Found and Resolved

| Severity | Issue | Location | Resolution |
|----------|-------|----------|------------|
| HIGH | Unused variable `col1` in render_session_browser() | app.py:2413 | Renamed to `_col1` to indicate intentional non-use |
| HIGH | Missing type annotations on dict variables causing pyright errors | tests/test_story_6_1_config_modal.py (multiple) | Added `dict[str, Any]` type annotations |
| MEDIUM | Missing `from typing import Any` import | tests/test_story_6_1_config_modal.py:1-15 | Added import statement |
| MEDIUM | Duplicate assignment `css_content = css_content = ...` | tests/test_story_6_1_config_modal.py:358 | Fixed to single assignment |
| MEDIUM | Missing test for render_config_modal function | tests/test_story_6_1_config_modal.py | Added TestConfigModalRendering class with tests |
| MEDIUM | Missing edge case tests | tests/test_story_6_1_config_modal.py | Added TestConfigModalEdgeCases class with 3 tests |

### Verification

- All 35 story-specific tests pass
- All 2017 project tests pass (no regressions)
- Ruff linting: All checks passed
- Pyright type checking: 0 errors, 0 warnings, 0 informations

### Low Severity Notes (Not Fixed)

- Escape key handling during input focus is documented in Dev Notes but relies on JavaScript implementation that cannot be unit tested. Visual verification recommended in Stories 6.2-6.5.

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-28 | Story created via create-story workflow | Claude Opus 4.5 |
| 2026-01-28 | Code review completed, 6 issues fixed, status: PASSED | Claude Opus 4.5 |
