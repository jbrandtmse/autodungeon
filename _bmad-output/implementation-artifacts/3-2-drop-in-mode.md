# Story 3.2: Drop-In Mode

Status: done

## Story

As a **user**,
I want **to instantly take control of any PC character with a single click**,
so that **I can participate in the story when something interesting happens**.

## Acceptance Criteria

1. **Given** I am in Watch Mode
   **When** I click a character's "Drop-In" button
   **Then** I take control of that character in under 2 seconds (FR18)
   **And** no confirmation dialog appears

2. **Given** I have dropped in as a character
   **When** the mode switches
   **Then** the mode indicator changes to "Playing as [Character Name]"
   **And** the indicator uses the character's color

3. **Given** I am controlling a character
   **When** the UI updates
   **Then** an input context bar appears showing "You are [Character Name], the [Class]"
   **And** a text input area expands for me to type my action

4. **Given** I am controlling a character
   **When** I type an action and submit
   **Then** my input is sent to the DM agent for integration
   **And** my message appears in the narrative with my character's attribution

5. **Given** `st.session_state["controlled_character"]` is set to a character name
   **When** LangGraph routes to that character's turn
   **Then** it routes to `human_intervention_node` instead of the AI node

6. **Given** I submit my action
   **When** the DM processes it
   **Then** the DM acknowledges and weaves my action into the narrative
   **And** other AI party members can respond to what I did

## Tasks / Subtasks

- [x] Task 1: Implement Input Context Bar (AC: #3)
  - [x] 1.1 Create `render_input_context_bar_html()` function with character-colored left border
  - [x] 1.2 Add `input-context` CSS styling to theme.css per UX spec
  - [x] 1.3 Create `render_input_context_bar()` that shows "You are [Name], the [Class]"
  - [x] 1.4 Display context bar only when `ui_mode="play"` and `controlled_character` is set
  - [x] 1.5 Position context bar above the text input area

- [x] Task 2: Implement Text Input Area for Human Actions (AC: #3, #4)
  - [x] 2.1 Create `render_human_input_area()` function with text input and submit button
  - [x] 2.2 Add text input area styling (expandable, character-themed border) to theme.css
  - [x] 2.3 Create `handle_human_action_submit()` to capture user input
  - [x] 2.4 Store submitted action in session state for processing
  - [x] 2.5 Clear input field after submission
  - [x] 2.6 Disable submit button while generating (is_generating=True)

- [x] Task 3: Implement Human Intervention Node (AC: #4, #5, #6)
  - [x] 3.1 Update `human_intervention_node()` in graph.py to process human input
  - [x] 3.2 Read human action from session state (human_pending_action)
  - [x] 3.3 Add human's action to ground_truth_log with character attribution
  - [x] 3.4 Format entry as "[agent_key]: {content}" matching PC message format
  - [x] 3.5 Return updated state to continue game flow
  - [x] 3.6 Clear human_pending_action after processing

- [x] Task 4: Integrate Human Input with Game Loop (AC: #4, #6)
  - [x] 4.1 Update `run_game_turn()` to wait for human input when human_active=True
  - [x] 4.2 Add `human_pending_action` session state key for storing pending input
  - [x] 4.3 Skip turn execution if human's turn and no pending action
  - [x] 4.4 Trigger game turn when human submits action
  - [x] 4.5 Resume normal flow after human action is processed

- [x] Task 5: Verify Mode Indicator Updates (AC: #1, #2)
  - [x] 5.1 Verify mode indicator already shows "Playing as [Name]" from Story 3.1
  - [x] 5.2 Verify character color is applied via CSS class
  - [x] 5.3 Verify pulse dot shows in play mode
  - [x] 5.4 Add tests for mode indicator in play mode with character info

- [x] Task 6: Verify LangGraph Routing (AC: #5)
  - [x] 6.1 Verify `route_to_next_agent()` routes to "human" when human_active=True
  - [x] 6.2 Add test: routing to human node when controlled character's turn
  - [x] 6.3 Add test: routing to AI node when NOT controlled character's turn
  - [x] 6.4 Verify human node routes to next agent after processing

- [x] Task 7: Verify Drop-In Transition Speed (AC: #1)
  - [x] 7.1 Verify `handle_drop_in_click()` executes in under 2 seconds
  - [x] 7.2 Verify no confirmation dialogs in drop-in flow
  - [x] 7.3 Add performance test for drop-in transition

- [x] Task 8: Write Comprehensive Tests
  - [x] 8.1 Test `render_input_context_bar_html()` with character data
  - [x] 8.2 Test input area visibility based on ui_mode
  - [x] 8.3 Test `handle_human_action_submit()` captures and stores input
  - [x] 8.4 Test `human_intervention_node()` adds action to log
  - [x] 8.5 Test game loop waits for human input when human_active=True
  - [x] 8.6 Test human action appears in narrative with character attribution
  - [x] 8.7 Test DM responds to human action
  - [x] 8.8 Test full Drop-In flow end-to-end

## Dev Notes

### Existing Implementation Analysis

Story 3.1 established the foundation for Drop-In Mode:

**Session State Keys (from Story 3.1):**
```python
# app.py:655-668
st.session_state["ui_mode"] = "watch"  # or "play"
st.session_state["controlled_character"] = None  # or agent_key
st.session_state["human_active"] = False  # or True
st.session_state["is_generating"] = False
st.session_state["is_autopilot_running"] = False
```
[Source: app.py:655-668]

**Drop-In Click Handler (from Story 3.1):**
```python
# app.py:787-817
def handle_drop_in_click(agent_key: str) -> None:
    """Handle Drop-In/Release button click."""
    controlled = st.session_state.get("controlled_character")
    if controlled == agent_key:
        # Release control
        st.session_state["controlled_character"] = None
        st.session_state["ui_mode"] = "watch"
        st.session_state["human_active"] = False
    else:
        # Take control - stop autopilot first
        st.session_state["is_autopilot_running"] = False
        st.session_state["controlled_character"] = agent_key
        st.session_state["ui_mode"] = "play"
        st.session_state["human_active"] = True
```
[Source: app.py:787-817]

**Mode Indicator (from Story 3.1):**
```python
# app.py:388-427
def render_mode_indicator_html(...):
    if ui_mode == "watch":
        return f'<div class="mode-indicator watch">{pulse_html}Watching</div>'
    else:
        # Play mode - show character name with character color
        return f'<div class="mode-indicator play {class_slug}">Playing as {name}</div>'
```
[Source: app.py:388-427]

**LangGraph Routing (from Story 1.7):**
```python
# graph.py:27-71
def route_to_next_agent(state: GameState) -> str:
    # Handle human override - only when it's the controlled character's turn
    if state["human_active"] and state["controlled_character"]:
        if current != "dm" and current == state["controlled_character"]:
            return "human"
    # ... rest of routing logic
```
[Source: graph.py:27-71]

**Human Intervention Node (placeholder from Story 1.7):**
```python
# graph.py:74-91
def human_intervention_node(state: GameState) -> GameState:
    """Placeholder for human input handling.
    For now, just return state unchanged.
    """
    # TODO: Implement in Story 3.2 (Drop-In Mode)
    return state
```
[Source: graph.py:74-91]

### Implementation Strategy

**Key Challenge:** Coordinating Streamlit's rerun model with LangGraph's graph execution.

The human intervention flow must:
1. Pause the graph when it's the human's turn
2. Render input UI in Streamlit
3. Wait for user submission (via button click + rerun)
4. Process the input and continue the graph

**Recommended Approach: Session State Coordination**

Rather than true async waiting (which Streamlit doesn't support well), use session state flags:

```python
# New session state keys needed:
st.session_state["human_pending_action"] = None  # str when action submitted
st.session_state["waiting_for_human"] = False    # True when it's human's turn

# Flow:
# 1. Game turn starts, human_active=True, controlled_character="rogue"
# 2. When graph routes to human node, it's the human's turn
# 3. Set waiting_for_human=True, return without executing turn
# 4. UI renders input area because waiting_for_human=True
# 5. User types and submits → human_pending_action = "I check for traps"
# 6. st.rerun() triggers
# 7. On next render, detect pending action, execute turn
# 8. human_intervention_node reads pending_action, adds to log
# 9. Clear flags, continue graph execution
```

### Input Context Bar Design

Per UX spec (ux-design-specification.md:1320-1340):

```css
/* Input Context Bar */
.input-context {
    background: var(--bg-secondary);      /* #2D2520 */
    border-left: 3px solid var(--character-color);
    padding: var(--space-sm) var(--space-md); /* 8px 16px */
    margin-bottom: var(--space-sm);
    border-radius: 0 4px 4px 0;
}

.input-context-text {
    font-family: Inter, system-ui, sans-serif;
    font-size: 13px;
    color: var(--text-secondary);
}

.input-context-character {
    color: var(--character-color);
    font-weight: 500;
}
```
[Source: ux-design-specification.md:1320-1340]

**Implementation:**

```python
def render_input_context_bar_html(name: str, char_class: str) -> str:
    """Generate HTML for input context bar.

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
        '</div>'
    )
```

### Human Input Area Design

The input area should be visible only in Play Mode:

```python
def render_human_input_area() -> None:
    """Render text input and submit button for human actions.

    Only renders when ui_mode="play" and controlled_character is set.
    """
    if st.session_state.get("ui_mode") != "play":
        return

    controlled = st.session_state.get("controlled_character")
    if not controlled:
        return

    game = st.session_state.get("game", {})
    char_config = game.get("characters", {}).get(controlled)

    if char_config:
        # Render context bar
        st.markdown(
            render_input_context_bar_html(char_config.name, char_config.character_class),
            unsafe_allow_html=True
        )

    # Text input area
    action = st.text_area(
        "Your action:",
        key="human_action_input",
        placeholder="What does your character do? (e.g., 'I check the door for traps.')",
        label_visibility="collapsed"
    )

    # Submit button (disabled while generating)
    is_generating = st.session_state.get("is_generating", False)
    if st.button("Send", key="human_action_submit", disabled=is_generating):
        if action.strip():
            handle_human_action_submit(action.strip())
            st.rerun()
```

### Human Intervention Node Implementation

```python
# graph.py
def human_intervention_node(state: GameState) -> GameState:
    """Process human input and add to game log.

    Reads the pending human action from session state,
    formats it as a log entry, and adds to ground_truth_log.

    Args:
        state: Current game state.

    Returns:
        Updated game state with human action added.
    """
    import streamlit as st

    # Get pending action from session state
    pending_action = st.session_state.get("human_pending_action")

    if not pending_action:
        # No action submitted yet - this shouldn't happen if flow is correct
        return state

    # Get controlled character
    controlled = state.get("controlled_character")
    if not controlled:
        return state

    # Format log entry like PC messages: "[agent_key]: content"
    log_entry = f"[{controlled}]: {pending_action}"

    # Add to ground truth log
    new_log = list(state.get("ground_truth_log", []))
    new_log.append(log_entry)

    # Clear the pending action
    st.session_state["human_pending_action"] = None

    # Return updated state
    return {
        **state,
        "ground_truth_log": new_log,
    }
```

### Game Loop Integration

Update the game turn flow to handle human input:

```python
# app.py
def run_game_turn() -> bool:
    """Execute one game turn and update session state.

    For human-controlled characters:
    - If it's human's turn and no pending action, skip (wait for input)
    - If pending action exists, process it through the graph
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

    # Rest of existing implementation...
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

### CSS Additions Needed

Add to `styles/theme.css`:

```css
/* ==========================================================================
   Drop-In Mode Input Area (Story 3.2)
   ========================================================================== */

/* Input Context Bar */
.input-context {
    background: var(--bg-secondary);
    border-left: 3px solid var(--accent-warm);
    padding: var(--space-sm) var(--space-md);
    margin-bottom: var(--space-sm);
    border-radius: 0 4px 4px 0;
}

.input-context-text {
    font-family: Inter, system-ui, sans-serif;
    font-size: 13px;
    color: var(--text-secondary);
}

.input-context-character {
    font-weight: 500;
}

/* Character-specific context bar colors */
.input-context.fighter {
    border-left-color: var(--color-fighter);
}
.input-context.fighter .input-context-character {
    color: var(--color-fighter);
}

.input-context.rogue {
    border-left-color: var(--color-rogue);
}
.input-context.rogue .input-context-character {
    color: var(--color-rogue);
}

.input-context.wizard {
    border-left-color: var(--color-wizard);
}
.input-context.wizard .input-context-character {
    color: var(--color-wizard);
}

.input-context.cleric {
    border-left-color: var(--color-cleric);
}
.input-context.cleric .input-context-character {
    color: var(--color-cleric);
}

/* Human Input Area */
.human-input-area {
    background: var(--bg-secondary);
    border-radius: 8px;
    padding: var(--space-md);
    margin-top: var(--space-md);
}

/* Text area styling for human input */
.human-input-area textarea {
    background: var(--bg-message) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--bg-message) !important;
    border-radius: 4px;
    font-family: Lora, Georgia, serif;
    font-size: 16px;
    line-height: 1.6;
    min-height: 80px;
}

.human-input-area textarea:focus {
    border-color: var(--accent-warm) !important;
    box-shadow: 0 0 0 1px var(--accent-warm);
}

/* Submit button styling */
.human-input-area button[kind="primary"] {
    background: var(--accent-warm) !important;
    color: var(--bg-primary) !important;
    border: none !important;
    font-weight: 500;
}

.human-input-area button[kind="primary"]:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
```

### Architecture Compliance

Per architecture.md:

| Decision | Compliance |
|----------|------------|
| State lives in `st.session_state["game"]` | Following - adding human_pending_action to session_state |
| Execution is synchronous (blocking) | Following - using flag-based coordination |
| `human_active` controls routing | Already implemented in graph.py |
| Log format: `[agent_key]: content` | Following for human entries |
| Human intervention via dedicated node | Following - updating human_intervention_node |

[Source: architecture.md#Human Intervention Flow]

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR18 | Drop-In Mode character control | Click handler + UI updates in < 2 seconds |
| FR30 | Drop-In controls per character | Already implemented in Story 2.4 |

[Source: epics.md#Story 3.2, prd.md#Human Interaction]

### What This Story Does NOT Do

- Does NOT implement Release Control UI polish (Story 3.3)
- Does NOT implement quick character switching (Story 3.3)
- Does NOT implement Nudge System (Story 3.4)
- Does NOT implement Pause/Resume during human control (Story 3.5)
- Does NOT implement keyboard shortcuts (Story 3.6)

This story focuses on the core Drop-In interaction: taking control, seeing input UI, submitting actions, and having them processed by the DM.

### Previous Story Intelligence (from Story 3.1)

**Key Learnings:**
- Use `st.rerun()` for state-driven UI updates
- Single-turn execution with flag management works well
- CSS animations handled via keyframes in theme.css
- Separate HTML generation from Streamlit rendering for testability
- `handle_drop_in_click()` already sets `human_active=True`

**Files Modified in Story 3.1:**
- `app.py` - Autopilot loop, toggle, mode indicator, drop-in handler updates
- `styles/theme.css` - Pulse dot colors for watch/play modes
- `tests/test_app.py` - 33 new tests

**Commit pattern to follow:**
```
Implement Story 3.2: Drop-In Mode with code review fixes
```

All tests passing (544) before this story.

[Source: _bmad-output/implementation-artifacts/3-1-watch-mode-autopilot.md]

### Git Intelligence (Last 5 Commits)

```
ca4cf72 Implement Story 3.1: Watch Mode & Autopilot with code review fixes
4bcc3ea Implement Stories 2.5 & 2.6: Session Header Controls & Real-time Narrative Flow with code review fixes
eb93602 Implement Story 2.4: Party Panel & Character Cards with code review fixes
9dfd9fa Implement Story 2.3: Narrative Message Display with code review fixes
a17944e Implement Story 2.2: Campfire Theme & CSS Foundation with code review fixes
```

**Pattern observed:** Stories are committed with "with code review fixes" suffix indicating adversarial review is run before commit. Follow this pattern.

### Testing Strategy

Organize tests in dedicated test classes within `tests/test_app.py`:

```python
class TestInputContextBar:
    """Tests for input context bar rendering."""

class TestHumanInputArea:
    """Tests for human action input area."""

class TestHumanInterventionNode:
    """Tests for human intervention in graph."""

class TestDropInModeIntegration:
    """Integration tests for full Drop-In flow."""
```

**Test Pattern (from previous stories):**

```python
def test_input_context_bar_shows_character_info():
    """Test context bar displays character name and class."""
    html = render_input_context_bar_html("Shadowmere", "Rogue")

    assert "You are" in html
    assert "Shadowmere" in html
    assert "Rogue" in html
    assert "input-context" in html
    assert "rogue" in html  # class slug for styling

def test_human_input_area_visible_in_play_mode():
    """Test input area only renders in play mode."""
    st.session_state["ui_mode"] = "play"
    st.session_state["controlled_character"] = "rogue"
    st.session_state["game"] = {"characters": {"rogue": mock_char_config}}

    # Input area should render
    # (test via checking render function doesn't return early)

def test_human_action_added_to_log():
    """Test human action is added to ground_truth_log."""
    state = {
        "controlled_character": "rogue",
        "ground_truth_log": [],
        "turn_queue": ["dm", "rogue"],
        "current_turn": "rogue",
        "human_active": True,
    }
    st.session_state["human_pending_action"] = "I check for traps."

    result = human_intervention_node(state)

    assert len(result["ground_truth_log"]) == 1
    assert "[rogue]: I check for traps." in result["ground_truth_log"][0]

def test_drop_in_flow_end_to_end():
    """Test complete Drop-In flow from click to action processing."""
    # 1. Click Drop-In
    handle_drop_in_click("rogue")
    assert st.session_state["ui_mode"] == "play"
    assert st.session_state["controlled_character"] == "rogue"
    assert st.session_state["human_active"] is True

    # 2. Submit action
    handle_human_action_submit("I search the room.")
    assert st.session_state["human_pending_action"] == "I search the room."

    # 3. Process through graph (mocked)
    # Verify action appears in log
```

### Security Considerations

- HTML escape all user input before adding to log
- Sanitize action text to prevent XSS in narrative display
- Limit action text length to prevent abuse (e.g., 2000 chars max)

```python
def handle_human_action_submit(action: str) -> None:
    """Handle submission of human action.

    Args:
        action: The user's action text.
    """
    # Limit action length for safety
    MAX_ACTION_LENGTH = 2000
    sanitized = action.strip()[:MAX_ACTION_LENGTH]

    if sanitized:
        st.session_state["human_pending_action"] = sanitized
```

### Project Structure Notes

- Input context bar and human input functions go in `app.py` (UI module)
- Human intervention node update goes in `graph.py`
- No changes needed to `models.py`
- CSS additions go in `styles/theme.css`
- Tests go in `tests/test_app.py`

### Implementation Approach

**Recommended order:**

1. **Task 5** - Verify mode indicator already works (should pass)
2. **Task 6** - Verify LangGraph routing works (should mostly pass)
3. **Task 1** - Implement input context bar HTML/CSS
4. **Task 2** - Implement text input area
5. **Task 8.1-8.3** - Write input area tests
6. **Task 3** - Implement human_intervention_node
7. **Task 8.4** - Write node tests
8. **Task 4** - Integrate with game loop
9. **Task 8.5-8.8** - Write integration tests
10. **Task 7** - Verify performance (should pass naturally)

This order builds on verified existing infrastructure, then adds new UI, then adds processing logic.

### Known Edge Cases

1. **User submits empty action**: Button should be disabled or ignore empty input
2. **User submits while generating**: Submit button disabled during generation
3. **Human drops out mid-turn**: Clear pending action, return to watch mode
4. **Rapid submit clicks**: Debounce or disable during processing
5. **Very long action text**: Truncate at reasonable limit (2000 chars)

### References

- [Source: planning-artifacts/ux-design-specification.md#Input Context Bar] - UI design spec
- [Source: planning-artifacts/architecture.md#Human Intervention Flow] - State management
- [Source: planning-artifacts/prd.md#Human Interaction FR17-FR24] - Functional requirements
- [Source: epics.md#Story 3.2] - Full acceptance criteria
- [Source: graph.py:74-91] - `human_intervention_node()` placeholder
- [Source: graph.py:27-71] - `route_to_next_agent()` routing logic
- [Source: app.py:787-817] - `handle_drop_in_click()` function
- [Source: app.py:388-427] - `render_mode_indicator_html()` function
- [Source: _bmad-output/implementation-artifacts/3-1-watch-mode-autopilot.md] - Previous story patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No blocking issues encountered.

### Completion Notes List

- Implemented `render_input_context_bar_html()` function with character-colored left border styling
- Added character-specific CSS classes for input context bar (fighter, rogue, wizard, cleric)
- Implemented `render_input_context_bar()` Streamlit wrapper for UI rendering
- Implemented `render_human_input_area()` with text input and styled submit button
- Implemented `handle_human_action_submit()` with 2000 character limit and sanitization
- Updated `human_intervention_node()` in graph.py to process human input and add to log
- Updated `run_game_turn()` to wait for human input when it's controlled character's turn
- Added `human_pending_action` and `waiting_for_human` session state keys
- Updated `handle_drop_in_click()` to clear pending action when releasing control
- Added CSS styling for human input area in theme.css
- All 28 new tests pass, full suite (572 tests) passes with no regressions

### File List

- app.py (modified) - Added render_input_context_bar_html, render_input_context_bar, handle_human_action_submit, render_human_input_area functions; Updated run_game_turn for human input waiting; Updated initialize_session_state with new keys; Updated handle_drop_in_click to clear pending action on release
- graph.py (modified) - Updated human_intervention_node to process human actions and add to game log; **Code Review Fix:** Now also updates character's agent_memories for consistency with PC turn behavior
- styles/theme.css (modified) - Added character-specific input context bar colors and human input area styling
- tests/test_app.py (modified) - Added 28 new tests across 7 test classes for Story 3.2 functionality; **Code Review Fix:** Added 8 additional tests (36 total) for memory updates and wrapper function coverage

### Change Log

- 2026-01-27: Implemented Story 3.2 Drop-In Mode - human can now take control of a character, see input context bar, submit actions, and have them processed by the game
- 2026-01-27: **Code Review Fixes Applied:**
  - MEDIUM-2: Updated `human_intervention_node()` to add human actions to character's `agent_memories` for memory consistency
  - LOW-1: Added tests for `render_input_context_bar()` wrapper function conditional logic
  - LOW-2: Added tests for `render_human_input_area()` wrapper function conditional logic
  - Total tests: 580 (8 new tests added during review)
