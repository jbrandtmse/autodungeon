# Story 3.1: Watch Mode & Autopilot

Status: done

## Story

As a **user**,
I want **to observe the game running autonomously without needing to intervene**,
so that **I can enjoy the story passively like watching a show**.

## Acceptance Criteria

1. **Given** the application starts with a session
   **When** I take no action
   **Then** the game runs in Watch Mode by default (FR17)
   **And** the mode indicator shows "Watching" with a pulsing green dot

2. **Given** Watch Mode is active
   **When** turns are generated
   **Then** the DM and PC agents take turns automatically
   **And** the narrative updates without any user input required

3. **Given** no human has dropped in
   **When** the game is running
   **Then** it operates in full Autopilot Mode (FR24)
   **And** can run indefinitely without human intervention

4. **Given** `st.session_state["human_active"]` is False
   **When** the LangGraph executes
   **Then** all PC nodes use AI agents, not human input

5. **Given** I am in Watch Mode
   **When** I want to participate
   **Then** Drop-In buttons are visible and accessible in the party panel

## Tasks / Subtasks

- [x] Task 1: Implement continuous game loop for autopilot (AC: #2, #3)
  - [x] 1.1 Create `run_continuous_loop()` function that runs turns until paused or human drops in
  - [x] 1.2 Add `is_autopilot_running` session state flag for loop management
  - [x] 1.3 Implement loop termination on `is_paused=True` or `human_active=True`
  - [x] 1.4 Add configurable turn limit safety (max_turns_per_session) to prevent infinite loops
  - [x] 1.5 Integrate with existing `run_game_turn()` for single-turn execution

- [x] Task 2: Implement Watch Mode state management (AC: #1, #4)
  - [x] 2.1 Ensure `ui_mode="watch"` is default on session start (already in place)
  - [x] 2.2 Verify `human_active=False` default state (already in place)
  - [x] 2.3 Add `get_is_watching()` helper to check both `ui_mode` and `human_active`
  - [x] 2.4 Create `is_autopilot_available()` to check if autopilot can start

- [x] Task 3: Add Autopilot toggle control in sidebar (AC: #1, #3)
  - [x] 3.1 Create `render_autopilot_toggle()` function with Start/Stop button
  - [x] 3.2 Implement `handle_autopilot_toggle()` click handler
  - [x] 3.3 Add visual feedback for autopilot state (running indicator)
  - [x] 3.4 Integrate toggle with existing session controls section
  - [x] 3.5 Disable autopilot toggle when human is controlling a character

- [x] Task 4: Verify LangGraph routing respects human_active flag (AC: #4)
  - [x] 4.1 Review `route_to_next_agent()` in graph.py - confirms routing logic
  - [x] 4.2 Add test cases for routing when `human_active=False`
  - [x] 4.3 Verify PC nodes use AI agents when not controlled
  - [x] 4.4 Test that setting `human_active=True` interrupts the loop

- [x] Task 5: Ensure Drop-In buttons remain visible and accessible (AC: #5)
  - [x] 5.1 Verify `render_character_card()` renders buttons during autopilot
  - [x] 5.2 Add test that buttons are enabled when `is_autopilot_running=True`
  - [x] 5.3 Verify clicking Drop-In stops autopilot and sets `human_active=True`
  - [x] 5.4 Update `handle_drop_in_click()` to stop autopilot if running

- [x] Task 6: Write comprehensive tests
  - [x] 6.1 Test `run_continuous_loop()` executes multiple rounds
  - [x] 6.2 Test loop stops when `is_paused=True`
  - [x] 6.3 Test loop stops when `human_active=True`
  - [x] 6.4 Test autopilot toggle state management
  - [x] 6.5 Test mode indicator shows "Watching" with pulse in autopilot
  - [x] 6.6 Test Drop-In buttons accessible during autopilot
  - [x] 6.7 Test routing uses AI agents when `human_active=False`

## Dev Notes

### Existing Implementation Analysis

Story 2.6 already provides the foundation for this story:

**Session State Keys (from Story 2.5/2.6):**
```python
# app.py:525-534
if "game" not in st.session_state:
    st.session_state["game"] = populate_game_state()
    st.session_state["ui_mode"] = "watch"  # Already defaults to watch
    st.session_state["controlled_character"] = None
    st.session_state["is_generating"] = False
    st.session_state["is_paused"] = False
    st.session_state["playback_speed"] = "normal"
    st.session_state["auto_scroll_enabled"] = True
```
[Source: app.py:525-534]

**Single Turn Execution (from Story 2.6):**
```python
# app.py:44-76
def run_game_turn() -> bool:
    """Execute one game turn and update session state."""
    if st.session_state.get("is_paused", False):
        return False
    st.session_state["is_generating"] = True
    try:
        game = st.session_state.get("game", {})
        updated_state = run_single_round(game)
        st.session_state["game"] = updated_state
        delay = get_turn_delay()
        if delay > 0:
            time.sleep(delay)
        return True
    finally:
        st.session_state["is_generating"] = False
```
[Source: app.py:44-76]

**LangGraph Routing (from Story 1.7):**
```python
# graph.py:27-71
def route_to_next_agent(state: GameState) -> str:
    """Route to the next agent based on turn_queue position."""
    current = state["current_turn"]
    turn_queue = state["turn_queue"]

    # Handle human override - only when it's the controlled character's turn
    if state["human_active"] and state["controlled_character"]:
        if current != "dm" and current == state["controlled_character"]:
            return "human"
    # ... rest of routing logic
```
[Source: graph.py:27-71]

### Continuous Loop Implementation Strategy

The key challenge is implementing a continuous loop within Streamlit's execution model. Streamlit reruns the entire script on each interaction, so we need a pattern that:

1. Runs multiple turns between reruns
2. Stops gracefully when pause/drop-in occurs
3. Updates UI after each turn (not just at the end)

**Recommended Approach: Single-turn with auto-rerun**

Rather than a true loop, trigger `st.rerun()` after each turn while `is_autopilot_running=True`:

```python
def run_autopilot_step() -> None:
    """Execute one turn of autopilot and trigger rerun if continuing."""
    if not st.session_state.get("is_autopilot_running", False):
        return

    if st.session_state.get("is_paused", False):
        st.session_state["is_autopilot_running"] = False
        return

    if st.session_state.get("human_active", False):
        st.session_state["is_autopilot_running"] = False
        return

    # Execute one turn
    if run_game_turn():
        # Continue autopilot on next rerun
        st.rerun()
```

This pattern:
- Respects Streamlit's architecture
- Updates UI after each turn
- Can be stopped at any point
- Allows Drop-In to interrupt immediately

**Alternative: Background Thread (Not Recommended)**

Using threads with Streamlit is complex and can cause state synchronization issues. The auto-rerun pattern is cleaner.

### Mode Indicator Enhancement

The mode indicator already shows "Watching" with a pulse dot when generating (Story 2.5):

```python
# app.py:261-297
def render_mode_indicator_html(ui_mode: str, is_generating: bool, ...):
    if ui_mode == "watch":
        pulse_html = '<span class="pulse-dot"></span>' if is_generating else ""
        return f'<div class="mode-indicator watch">{pulse_html}Watching</div>'
```
[Source: app.py:261-297]

For autopilot, the pulse should show continuously while `is_autopilot_running=True`, not just during generation:

```python
def render_mode_indicator_html(ui_mode: str, is_generating: bool,
                                is_autopilot: bool = False, ...):
    if ui_mode == "watch":
        # Show pulse for autopilot OR generating
        pulse_html = '<span class="pulse-dot"></span>' if (is_generating or is_autopilot) else ""
        return f'<div class="mode-indicator watch">{pulse_html}Watching</div>'
```

### Autopilot Toggle Design

Add to session controls (existing in sidebar):

```python
def render_autopilot_toggle() -> None:
    """Render autopilot start/stop toggle button."""
    is_running = st.session_state.get("is_autopilot_running", False)
    human_active = st.session_state.get("human_active", False)

    # Disable if human is controlling
    disabled = human_active

    button_label = "Stop Autopilot" if is_running else "Start Autopilot"

    if st.button(button_label, key="autopilot_toggle", disabled=disabled):
        handle_autopilot_toggle()
        st.rerun()

def handle_autopilot_toggle() -> None:
    """Toggle autopilot state."""
    current = st.session_state.get("is_autopilot_running", False)
    st.session_state["is_autopilot_running"] = not current
```

### Drop-In Stops Autopilot

Update `handle_drop_in_click()` to stop autopilot:

```python
def handle_drop_in_click(agent_key: str) -> None:
    """Handle Drop-In/Release button click."""
    controlled = st.session_state.get("controlled_character")

    if controlled == agent_key:
        # Release control
        st.session_state["controlled_character"] = None
        st.session_state["ui_mode"] = "watch"
        st.session_state["human_active"] = False  # NEW: Clear human_active
    else:
        # Take control - stop autopilot first
        st.session_state["is_autopilot_running"] = False  # NEW
        st.session_state["controlled_character"] = agent_key
        st.session_state["ui_mode"] = "play"
        st.session_state["human_active"] = True  # NEW: Set human_active
```

### Architecture Compliance

Per architecture.md:

| Decision | Compliance |
|----------|------------|
| State lives in `st.session_state["game"]` | Following this pattern |
| Execution is synchronous (blocking) | Using single-turn + rerun |
| `human_active` controls routing | Already implemented in graph.py |
| PC nodes isolated, DM sees all | Existing memory architecture |

[Source: architecture.md#LangGraph State Machine Architecture]

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR17 | Watch Mode observation | `ui_mode="watch"` default, no input required |
| FR24 | Autopilot Mode | `is_autopilot_running` flag with continuous loop |

[Source: epics.md#Story 3.1, prd.md#Human Interaction]

### What This Story Does NOT Do

- Does NOT implement Drop-In Mode (Story 3.2)
- Does NOT implement human input handling (Story 3.2)
- Does NOT implement Release Control (Story 3.3)
- Does NOT implement Nudge System (Story 3.4)
- Does NOT implement Speed Control delays during autopilot (Story 3.5)
- Does NOT implement keyboard shortcuts (Story 3.6)

This story creates the Watch Mode infrastructure. Subsequent stories add human intervention capabilities.

### Previous Story Intelligence (from Story 2.6)

**Key Learnings:**
- Use `st.rerun()` for state-driven UI updates
- Single-turn execution with flag management works well
- CSS animations for delayed UI elements (500ms thinking indicator)
- Separate HTML generation from Streamlit rendering for testability
- Speed delays via `time.sleep()` after turn execution

**Files Modified in Story 2.6:**
- `app.py` - Game execution loop, auto-scroll, thinking indicator
- `styles/theme.css` - CSS for thinking indicator, current turn highlight
- `tests/test_app.py` - 43 new tests

**Commit pattern to follow:**
```
Implement Story 3.1: Watch Mode & Autopilot with code review fixes
```

All tests passing (509) before this story.

[Source: _bmad-output/implementation-artifacts/2-6-real-time-narrative-flow.md]

### Git Intelligence (Last 5 Commits)

```
4bcc3ea Implement Stories 2.5 & 2.6: Session Header Controls & Real-time Narrative Flow with code review fixes
eb93602 Implement Story 2.4: Party Panel & Character Cards with code review fixes
9dfd9fa Implement Story 2.3: Narrative Message Display with code review fixes
a17944e Implement Story 2.2: Campfire Theme & CSS Foundation with code review fixes
4699962 Implement Stories 1.6, 1.8, and 2.1 with code review fixes
```

**Pattern observed:** Stories are committed with "with code review fixes" suffix indicating adversarial review is run before commit. Follow this pattern.

### Testing Strategy

Organize tests in dedicated test classes within `tests/test_app.py`:

```python
class TestAutopilotLoop:
    """Tests for continuous autopilot loop."""

class TestWatchModeState:
    """Tests for Watch Mode state management."""

class TestAutopilotToggle:
    """Tests for autopilot toggle button."""

class TestDropInStopsAutopilot:
    """Tests for Drop-In interrupting autopilot."""
```

**Test Pattern (from previous stories):**
```python
def test_autopilot_runs_until_paused(mock_game_state):
    """Test autopilot loop stops when is_paused becomes True."""
    st.session_state["is_autopilot_running"] = True
    st.session_state["is_paused"] = False

    # Simulate one step
    run_autopilot_step()

    # Should continue
    assert st.session_state.get("is_autopilot_running") is True

    # Now pause
    st.session_state["is_paused"] = True
    run_autopilot_step()

    # Should stop
    assert st.session_state.get("is_autopilot_running") is False

def test_drop_in_stops_autopilot():
    """Test that clicking Drop-In stops autopilot."""
    st.session_state["is_autopilot_running"] = True
    st.session_state["controlled_character"] = None

    handle_drop_in_click("rogue")

    assert st.session_state.get("is_autopilot_running") is False
    assert st.session_state.get("controlled_character") == "rogue"
    assert st.session_state.get("human_active") is True
```

### Security Consideration

**No new security concerns** - this story uses existing patterns for HTML escaping and doesn't introduce new user input handling.

### Project Structure Notes

- Autopilot loop logic goes in `app.py` (UI module)
- No changes needed to `graph.py` (routing already supports `human_active`)
- No changes needed to `models.py`
- CSS additions go in `styles/theme.css` (minimal - reuse existing indicators)
- Tests go in `tests/test_app.py`

### Implementation Approach

**Recommended order:**

1. **Task 2** - Verify Watch Mode state defaults (should pass already)
2. **Task 4** - Verify LangGraph routing with tests
3. **Task 1** - Implement autopilot loop (`run_autopilot_step()`)
4. **Task 6.1-6.3** - Write loop tests
5. **Task 3** - Add autopilot toggle to sidebar
6. **Task 6.4-6.5** - Write toggle tests
7. **Task 5** - Update Drop-In to stop autopilot
8. **Task 6.6-6.7** - Write remaining tests

This order verifies existing infrastructure first, then adds new functionality incrementally.

### CSS Additions Needed

Minimal - reuse existing mode indicator styles. Optionally add autopilot-specific styling:

```css
/* ==========================================================================
   Autopilot Mode (Story 3.1)
   ========================================================================== */

/* Autopilot toggle button styling */
.autopilot-toggle {
    width: 100%;
    margin: var(--space-sm) 0;
}

/* Running state for autopilot button */
.autopilot-toggle.running button {
    background: var(--accent-warm);
    color: var(--bg-primary);
}
```

### References

- [Source: planning-artifacts/ux-design-specification.md#Core User Experience] - Watch Mode flow
- [Source: planning-artifacts/architecture.md#Human Intervention Flow] - State management
- [Source: planning-artifacts/prd.md#Human Interaction FR17-FR24] - Functional requirements
- [Source: epics.md#Story 3.1] - Full acceptance criteria
- [Source: graph.py:27-71] - `route_to_next_agent()` function
- [Source: app.py:44-76] - `run_game_turn()` function
- [Source: app.py:525-534] - Session state initialization
- [Source: _bmad-output/implementation-artifacts/2-6-real-time-narrative-flow.md] - Previous story patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- All 544 tests pass (255 in test_app.py, 289 in other test files)
- Linting passes with no errors
- Type checking passes with 0 errors, 0 warnings

### Completion Notes List

✅ Implemented Watch Mode & Autopilot functionality:

1. **Autopilot Loop Implementation** (Task 1):
   - Created `run_continuous_loop()` and `run_autopilot_step()` functions
   - Uses Streamlit's `st.rerun()` pattern for continuous execution
   - Respects pause state, human_active flag, and max turn limits
   - Added `is_autopilot_running`, `autopilot_turn_count`, `max_turns_per_session` session state flags

2. **Watch Mode State Management** (Task 2):
   - Verified `ui_mode="watch"` and `human_active=False` defaults already in place
   - Added `get_is_watching()` helper function
   - Added `is_autopilot_available()` helper function

3. **Autopilot Toggle Control** (Task 3):
   - Created `render_autopilot_toggle()` with Start/Stop button
   - Created `handle_autopilot_toggle()` click handler
   - Integrated into session controls sidebar
   - Button disabled when human is controlling a character

4. **LangGraph Routing Verification** (Task 4):
   - Verified `route_to_next_agent()` correctly routes to human when `human_active=True` and it's controlled character's turn
   - Routes to AI agents when `human_active=False`
   - Added comprehensive test coverage

5. **Drop-In Button Integration** (Task 5):
   - Updated `handle_drop_in_click()` to stop autopilot when dropping in
   - Sets `human_active=True` when taking control
   - Clears `human_active` when releasing control

6. **Mode Indicator Enhancement**:
   - Mode indicator always shows pulse dot in Watch Mode (AC #1: pulsing green dot)
   - Simplified function signature - removed unused `is_autopilot` parameter

7. **Comprehensive Tests** (Task 6):
   - 33 new tests covering all acceptance criteria
   - Test classes: TestWatchModeState, TestAutopilotLoop, TestAutopilotToggle, TestDropInStopsAutopilot, TestModeIndicatorAutopilot, TestLangGraphRoutingWithHumanActive, TestStory31AcceptanceCriteria

### File List

- `app.py` - Added autopilot loop, toggle, state management, mode indicator enhancement
- `styles/theme.css` - Added explicit pulse dot colors for watch/play modes
- `tests/test_app.py` - Added 33 new tests for Story 3.1, updated mode indicator tests

### Change Log

- 2026-01-27: Story 3.1 implementation complete - Watch Mode & Autopilot with all acceptance criteria satisfied
- 2026-01-27: Fixed pulse dot visibility - now always shows green pulsing dot in Watch Mode (AC #1)
- 2026-01-27: Code review fixes applied:
  - Added explicit `human_active=False` initialization to `initialize_session_state()`
  - Removed unused `is_autopilot` parameter from `render_mode_indicator_html()`
  - Added test for explicit `human_active` initialization
  - Updated tests to match simplified function signature

