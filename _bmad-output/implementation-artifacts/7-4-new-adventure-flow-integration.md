# Story 7.4: New Adventure Flow Integration

Status: complete

## Story

As a **user**,
I want **module selection integrated into the new adventure flow**,
so that **starting a new game is a smooth, guided experience**.

## Acceptance Criteria

1. **Given** I click "New Adventure" on the home screen
   **When** the creation flow starts
   **Then** the steps are:
   1. Module Selection (new)
   2. Party Setup (existing)
   3. Adventure Begins

2. **Given** the module selection step
   **When** modules are loading
   **Then** a loading indicator shows "Consulting the Dungeon Master's Library..."

3. **Given** I complete module selection
   **When** proceeding to party setup
   **Then** the selected module is displayed in a header/banner

4. **Given** the full adventure creation completes
   **When** the game starts
   **Then** the DM's opening narration reflects the selected module's setting

5. **Given** I want to skip module selection
   **When** offered the option
   **Then** I can choose "Freeform Adventure" for an unstructured campaign

## Tasks / Subtasks

- [x] Task 1: Add new app_view states for adventure creation flow (AC: #1)
  - [x] 1.1 Add `"module_selection"` to app_view state values in initialize_session_state()
  - [x] 1.2 Add `"party_setup"` to app_view state values (placeholder for future expansion) - Documented in state machine, placeholder exists
  - [x] 1.3 Update main() routing to handle new `module_selection` view
  - [x] 1.4 Document view state machine in code comments

- [x] Task 2: Modify "New Adventure" button to trigger module discovery (AC: #1, #2)
  - [x] 2.1 Update render_session_browser() to change button behavior
  - [x] 2.2 Create `handle_start_new_adventure()` function to replace direct `handle_new_session_click()` call
  - [x] 2.3 Set `app_view = "module_selection"` instead of immediately starting game
  - [x] 2.4 Trigger `start_module_discovery()` to begin loading modules
  - [x] 2.5 Clear any previous module selection state

- [x] Task 3: Create module selection view integration (AC: #1, #2, #5)
  - [x] 3.1 Create `render_module_selection_view()` wrapper function
  - [x] 3.2 Integrate existing `render_module_selection_ui()` from Story 7.2
  - [x] 3.3 Add page header: "Step 1: Choose Your Adventure"
  - [x] 3.4 Ensure loading state shows "Consulting the Dungeon Master's Library..." (uses Story 7.1 component)
  - [x] 3.5 Add "Back to Sessions" button for cancellation
  - [x] 3.6 Handle `module_selection_confirmed` to proceed to game start

- [x] Task 4: Wire module selection confirmation to game initialization (AC: #1, #3)
  - [x] 4.1 Detect when `module_selection_confirmed = True` in module_selection view
  - [x] 4.2 Call `handle_new_session_click()` which already passes selected_module to GameState (Story 7.3)
  - [x] 4.3 Ensure proper session state cleanup after game starts
  - [x] 4.4 Clear module discovery state after successful game start

- [x] Task 5: Display selected module header in game view (AC: #3)
  - [x] 5.1 Create `render_module_banner(module: ModuleInfo) -> None` function
  - [x] 5.2 Show module name in a subtle banner/header above narrative area
  - [x] 5.3 Add collapsible description on click/hover
  - [x] 5.4 Handle None case (freeform adventure - no banner shown)
  - [x] 5.5 Add CSS styling for .module-banner component

- [x] Task 6: Add opening narration module context (AC: #4)
  - [x] 6.1 Verify DM system prompt includes module context (already done in Story 7.3)
  - [x] 6.2 Create integration test: new game with module -> verify DM prompt contains module
  - [x] 6.3 Create integration test: freeform game -> verify DM prompt has no module section
  - [x] 6.4 Manual verification: start game with module, observe DM opening narration references setting

- [x] Task 7: Implement freeform adventure bypass (AC: #5)
  - [x] 7.1 Verify "Skip - Start Freeform Adventure" button works from Story 7.2
  - [x] 7.2 Ensure freeform sets `selected_module = None` and `module_selection_confirmed = True`
  - [x] 7.3 Test freeform adventure creates game without module context
  - [x] 7.4 Verify no module banner appears in freeform game view

- [x] Task 8: Add CSS styles for new adventure flow (AC: #3)
  - [x] 8.1 Add .module-selection-view container styles
  - [x] 8.2 Add .step-header styles for "Step 1: Choose Your Adventure"
  - [x] 8.3 Add .module-banner styles for game view header
  - [x] 8.4 Add .module-banner-collapsed and .module-banner-expanded states
  - [x] 8.5 Ensure responsive behavior for module banner

- [x] Task 9: Write comprehensive tests (AC: #1-5)
  - [x] 9.1 Test: New Adventure button sets app_view to module_selection
  - [x] 9.2 Test: Module selection view renders loading state
  - [x] 9.3 Test: Module selection confirmed triggers game start
  - [x] 9.4 Test: Selected module appears in game banner
  - [x] 9.5 Test: Freeform adventure skips module selection
  - [x] 9.6 Test: Back button returns to session browser
  - [x] 9.7 Test: Module context preserved after game state serialization round-trip
  - [x] 9.8 Test: Session restore shows module banner if module was selected

## Dev Notes

### Implementation Strategy

This story completes Epic 7 by integrating module selection into the main application flow. It connects the three previous stories:

1. **Story 7.1 (Module Discovery)** - Provides `start_module_discovery()`, `render_module_discovery_loading()`
2. **Story 7.2 (Module Selection UI)** - Provides `render_module_selection_ui()`, `filter_modules()`, module grid/cards
3. **Story 7.3 (Module Context Injection)** - Provides `format_module_context()`, GameState module storage, persistence

The key architectural change is introducing a multi-step "new adventure" flow where clicking "New Adventure" no longer immediately starts a game, but instead:

1. Shows module selection (with loading state)
2. User selects module OR chooses freeform
3. Game initializes with module context

### App View State Machine

Current state machine:
```
session_browser -> game (direct)
```

New state machine:
```
session_browser -> module_selection -> game
                        |
                        +-> session_browser (cancel/back)
```

App view values:
- `"session_browser"` - List of sessions, "New Adventure" button
- `"module_selection"` - Module discovery loading, grid selection UI
- `"game"` - Active game view with narrative, controls, etc.

### Session State Keys (New)

| Key | Type | Purpose | Set By |
|-----|------|---------|--------|
| `app_view` | `str` | Current view (session_browser, module_selection, game) | Navigation |
| `module_list` | `list[ModuleInfo]` | Cached modules from discovery | Story 7.1 |
| `module_discovery_in_progress` | `bool` | Loading flag | Story 7.1 |
| `selected_module` | `ModuleInfo \| None` | User's selection | Story 7.2 |
| `module_selection_confirmed` | `bool` | User confirmed and ready to proceed | Story 7.2 |

### New Adventure Flow Handler

```python
def handle_start_new_adventure() -> None:
    """Handle "New Adventure" button click.

    Initiates the new adventure flow:
    1. Clear any previous module selection state
    2. Set app_view to module_selection
    3. Trigger module discovery

    Story 7.4: AC #1 - New adventure flow integration.
    """
    # Clear previous state
    clear_module_discovery_state()

    # Navigate to module selection
    st.session_state["app_view"] = "module_selection"
    st.session_state["module_selection_confirmed"] = False

    # Start module discovery (Story 7.1)
    start_module_discovery()
```

### Module Selection View Wrapper

```python
def render_module_selection_view() -> None:
    """Render the module selection step of new adventure creation.

    Wraps render_module_selection_ui() with:
    - Step header
    - Back button navigation
    - Confirmation handling to proceed to game

    Story 7.4: AC #1-5.
    """
    # Step header
    st.markdown('<h1 class="step-header">Step 1: Choose Your Adventure</h1>',
                unsafe_allow_html=True)
    st.caption("Select a D&D module to guide the Dungeon Master's storytelling.")

    # Back button
    if st.button("<- Back to Adventures"):
        st.session_state["app_view"] = "session_browser"
        clear_module_discovery_state()
        st.rerun()

    # Check if user confirmed selection (from Story 7.2 buttons)
    if st.session_state.get("module_selection_confirmed"):
        # Proceed to game initialization
        handle_new_session_click()  # Already handles selected_module (Story 7.3)
        clear_module_discovery_state()  # Cleanup
        st.rerun()
        return

    # Render the module selection UI (Story 7.2)
    render_module_selection_ui()
```

### Module Banner Component

```python
def render_module_banner() -> None:
    """Render selected module banner in game view.

    Shows module name with collapsible description.
    Hidden for freeform adventures (no module selected).

    Story 7.4: AC #3.
    """
    game: GameState | None = st.session_state.get("game")
    if not game:
        return

    selected_module = game.get("selected_module")
    if selected_module is None:
        # Freeform adventure - no banner
        return

    # Expandable banner with module info
    with st.expander(
        f"Campaign Module: {selected_module.name}",
        expanded=False,
    ):
        st.markdown(
            f'<p class="module-banner-description">{escape_html(selected_module.description)}</p>',
            unsafe_allow_html=True,
        )
        if selected_module.setting:
            st.markdown(f"**Setting:** {selected_module.setting}")
        if selected_module.level_range:
            st.markdown(f"**Levels:** {selected_module.level_range}")
```

### CSS Styles

```css
/* ==========================================================================
   New Adventure Flow (Story 7.4)
   ========================================================================== */

/* Step header for multi-step flow */
.step-header {
    font-family: var(--font-narrative);
    font-size: 28px;
    color: var(--accent-warm);
    margin-bottom: var(--space-sm);
}

/* Module selection view container */
.module-selection-view {
    padding: var(--space-lg);
    max-width: 1200px;
    margin: 0 auto;
}

/* Module banner in game view */
.module-banner {
    background: var(--bg-secondary);
    border-left: 3px solid var(--accent-warm);
    padding: var(--space-sm) var(--space-md);
    margin-bottom: var(--space-md);
    border-radius: 0 6px 6px 0;
}

.module-banner-title {
    font-family: var(--font-narrative);
    font-size: 16px;
    color: var(--accent-warm);
    font-weight: 600;
}

.module-banner-description {
    font-family: var(--font-narrative);
    font-size: 14px;
    color: var(--text-secondary);
    font-style: italic;
    line-height: 1.5;
    margin-top: var(--space-sm);
}
```

### Main Function Routing Update

```python
# In main() function, update routing:

app_view = st.session_state.get("app_view", "session_browser")

if app_view == "session_browser":
    st.title("autodungeon")
    st.caption("Multi-agent D&D game engine")
    render_session_browser()

elif app_view == "module_selection":
    st.title("autodungeon")
    render_module_selection_view()

else:  # app_view == "game"
    # Existing game view code...
    if st.session_state.get("show_recap"):
        render_recap_modal(...)
    else:
        render_module_banner()  # NEW: Show module header if selected
        render_sidebar(config)
        render_main_content()
        # ... rest of game view
```

### Session Browser Update

```python
# In render_session_browser(), update "New Adventure" button:

# Instead of:
if st.button("+ New Adventure", key="new_session_btn"):
    handle_new_session_click()
    st.rerun()

# Change to:
if st.button("+ New Adventure", key="new_session_btn"):
    handle_start_new_adventure()
    st.rerun()
```

### Edge Cases

1. **Module discovery fails** - Error UI from Story 7.2 shows retry/freeform options
2. **User clicks back during loading** - Cancel discovery, return to session browser
3. **Session restore with module** - Module banner shown, module context in DM prompt
4. **Session restore without module** - No banner, DM uses freeform prompting
5. **Rapid navigation** - Session state cleared properly on each transition

### Testing Strategy

**Unit Tests:**

```python
# tests/test_story_7_4_new_adventure_flow.py

class TestHandleStartNewAdventure:
    def test_sets_app_view_to_module_selection(self): ...
    def test_clears_previous_module_state(self): ...
    def test_triggers_module_discovery(self): ...

class TestRenderModuleSelectionView:
    def test_shows_step_header(self): ...
    def test_back_button_returns_to_session_browser(self): ...
    def test_confirmed_triggers_game_start(self): ...

class TestRenderModuleBanner:
    def test_shows_banner_when_module_selected(self): ...
    def test_hides_banner_for_freeform(self): ...
    def test_displays_module_name(self): ...
    def test_expander_shows_description(self): ...

class TestNewAdventureFlowIntegration:
    def test_full_flow_with_module_selection(self): ...
    def test_full_flow_with_freeform(self): ...
    def test_session_restore_preserves_module_banner(self): ...
```

### Architecture Compliance

| Pattern | Compliance | Notes |
|---------|------------|-------|
| Session state for UI state | YES | app_view, module states all in session_state |
| Pydantic models | YES | Uses ModuleInfo from Story 7.1 |
| Campfire CSS styling | YES | Follows existing theme patterns |
| Component composition | YES | Wraps Story 7.2 components |
| Escape HTML | YES | All user-visible text escaped |

### Files to Modify

| File | Changes |
|------|---------|
| `app.py` | Add `handle_start_new_adventure()`, `render_module_selection_view()`, `render_module_banner()`. Update `render_session_browser()` to use new handler. Update `main()` routing for module_selection view. |
| `styles/theme.css` | Add .step-header, .module-selection-view, .module-banner, .module-banner-title, .module-banner-description styles. |

### Files to Create

| File | Purpose |
|------|---------|
| `tests/test_story_7_4_new_adventure_flow.py` | Comprehensive test suite for new adventure flow integration |

### Dependencies

- Story 7.1 (Module Discovery) - DONE - provides `start_module_discovery()`, `render_module_discovery_loading()`, `clear_module_discovery_state()`
- Story 7.2 (Module Selection UI) - DONE - provides `render_module_selection_ui()`, `filter_modules()`, module cards/grid
- Story 7.3 (Module Context Injection) - DONE - provides `format_module_context()`, GameState module storage, `handle_new_session_click()` wiring

### What This Story Implements

1. **Multi-step new adventure flow** - Module selection before game start
2. **App view routing for module_selection** - New view state in main()
3. **Module banner in game view** - Shows selected module name/description
4. **Integration wiring** - Connects Stories 7.1-7.3 into cohesive flow
5. **Freeform bypass option** - Skip module selection (uses existing Story 7.2 button)

### What This Story Does NOT Implement

- Party setup customization (future story)
- Character creation UI (Epic 9)
- Module-specific encounter tables (future enhancement)
- Multiple module selection (out of scope)

### Performance Considerations

- Module discovery runs once per "New Adventure" click
- Results cached in session state for the selection UI
- No redundant LLM calls during navigation within flow
- Module banner renders from GameState (no additional API calls)

### FR/NFR Coverage

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| FR56 | Query DM for available modules | Triggered on "New Adventure" click |
| FR57 | Present module list | Module selection view integration |
| FR58 | Select specific or random module | Uses Story 7.2 UI |
| FR59 | Module context in DM prompt | Uses Story 7.3 injection |

### References

- [Source: planning-artifacts/epics-v1.1.md#Story 7.4] - Story requirements
- [Source: planning-artifacts/prd.md#FR56-FR59] - Module selection requirements
- [Source: app.py#main] - App view routing pattern
- [Source: app.py#render_session_browser] - Session browser implementation
- [Source: app.py#handle_new_session_click] - Game initialization flow
- [Source: implementation-artifacts/7-1-module-discovery-via-llm-query.md] - Module discovery functions
- [Source: implementation-artifacts/7-2-module-selection-ui.md] - Module selection UI components
- [Source: implementation-artifacts/7-3-module-context-injection.md] - Module context injection

---

## Code Review

### Review Date
2026-02-01

### Reviewer
Claude Opus 4.5 (BMAD Code Review Workflow)

### Review Summary

Adversarial code review completed. **6 issues** identified, **3 auto-fixed** (HIGH and MEDIUM severity).

### Issues Found

| # | Severity | Category | File | Description | Status |
|---|----------|----------|------|-------------|--------|
| 1 | HIGH | Security | app.py:3700-3703 | XSS vulnerability: `selected_module.setting` and `selected_module.level_range` rendered without `escape_html()` in `render_module_banner()`. Inconsistent with `render_module_confirmation()` which properly escapes the same fields. | FIXED |
| 2 | MEDIUM | Test Coverage | tests/test_story_7_4_new_adventure_flow.py | Missing XSS/HTML injection resilience tests for module fields with special characters (`<`, `>`, `&`, `"`). | FIXED |
| 3 | MEDIUM | Code Quality | tests/test_story_7_4_new_adventure_flow.py:22-27 | Ruff `I001` import sorting violation. | FIXED |
| 4 | LOW | Test Coverage | tests/test_story_7_4_new_adventure_flow.py | Missing tests for module discovery error state handling (error->retry, error->freeform paths). | Documented |
| 5 | LOW | Accessibility | app.py:3691-3703 | Module banner expander lacks `aria-label` for screen reader accessibility. | Documented |
| 6 | LOW | Style | app.py:3682 | Verbose union syntax `GameState \| None` when `.get()` already returns Optional. Minor style issue. | Documented |

### Fixes Applied

**Issue 1 - XSS Vulnerability (HIGH)**
```diff
- if selected_module.setting:
-     st.markdown(f"**Setting:** {selected_module.setting}")
- if selected_module.level_range:
-     st.markdown(f"**Levels:** {selected_module.level_range}")
+ if selected_module.setting:
+     st.markdown(f"**Setting:** {escape_html(selected_module.setting)}")
+ if selected_module.level_range:
+     st.markdown(f"**Levels:** {escape_html(selected_module.level_range)}")
```

**Issue 2 - Missing XSS Tests (MEDIUM)**
Added `TestXSSResilience` class with 3 tests:
- `test_module_banner_escapes_html_in_setting`
- `test_module_banner_escapes_html_in_level_range`
- `test_module_name_with_special_characters`

**Issue 3 - Import Sorting (MEDIUM)**
Applied `ruff check --fix` to sort imports per project standards.

### Test Results After Fixes

```
tests/test_story_7_4_new_adventure_flow.py: 24 passed in 7.67s
```

All 24 tests pass (21 original + 3 new XSS tests).

### Checklist Compliance

| Category | Status | Notes |
|----------|--------|-------|
| Security: XSS Prevention | PASS | All user-visible module fields now properly escaped |
| Type Safety | PASS | No pyright errors in story-related code |
| Error Handling | PASS | Module discovery errors handled gracefully |
| Test Coverage | PASS | 24 tests covering all acceptance criteria + XSS |
| Code Quality | PASS | Ruff check passes (E402 pre-existing, not story-related) |
| Architecture Compliance | PASS | Follows session state, Pydantic, CSS patterns |

### Recommendation

**APPROVED** - All HIGH and MEDIUM issues resolved. LOW issues documented for future consideration.

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None

### Completion Notes List

1. Added `module_selection` app_view state with full state machine documentation
2. Created `handle_start_new_adventure()` function that triggers module discovery flow
3. Created `render_module_selection_view()` wrapper that integrates Story 7.2 UI with navigation
4. Created `render_module_banner()` to show selected module in game view (collapsible expander)
5. Updated `main()` routing to handle all three views: session_browser, module_selection, game
6. Updated `render_session_browser()` to use new adventure flow handler
7. Extended `clear_module_discovery_state()` to include `module_selection_confirmed` and `module_search_query`
8. Fixed `format_module_context()` in agents.py to handle None for freeform adventures
9. Added comprehensive CSS styles for step header, module banner, and responsive behavior
10. Created 21 unit/integration tests covering all acceptance criteria

### File List

- `app.py` - Added handle_start_new_adventure(), render_module_selection_view(), render_module_banner(), updated main() routing, updated session browser button
- `agents.py` - Fixed format_module_context() to handle None module (freeform adventures)
- `styles/theme.css` - Added .step-header, .module-selection-view, .module-banner, .module-banner-collapsed, .module-banner-expanded, responsive styles
- `tests/test_story_7_4_new_adventure_flow.py` - 24 comprehensive tests covering all acceptance criteria (21 original + 3 XSS tests from code review)
