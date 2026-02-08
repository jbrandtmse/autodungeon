# Story 13.1: Session Naming

Status: review

## Story

As a **user starting a new adventure**,
I want **to name my session during the adventure creation flow**,
So that **I can identify it later in the session browser instead of seeing "Unnamed Adventure"**.

## Acceptance Criteria

1. **Given** the new adventure flow (after module selection), **When** I reach the point before game creation, **Then** I see a text input for naming my session.

2. **Given** I enter a session name (e.g., "Curse of Strahd - Attempt 2"), **When** the session is created, **Then** the name is passed to `create_new_session(name=...)` and persisted in `SessionMetadata`.

3. **Given** I leave the name blank, **When** the session is created, **Then** the session defaults to "Unnamed Adventure" (existing behavior preserved).

4. **Given** a named session exists, **When** I view the session browser, **Then** the session card displays my chosen name instead of "Unnamed Adventure".

## Tasks / Subtasks

- [x] Task 1: Add session name text input to the module selection view (AC: #1)
  - [x] 1.1: Add `st.text_input` for session name in `render_module_selection_view()` after step header / before module grid
  - [x] 1.2: Store the entered name in `st.session_state["new_session_name"]`
  - [x] 1.3: Add placeholder text: "Name your adventure (optional)"
- [x] Task 2: Wire session name to `handle_new_session_click()` (AC: #2)
  - [x] 2.1: Read `st.session_state.get("new_session_name", "")` in `handle_new_session_click()`
  - [x] 2.2: Pass `name=session_name` to `create_new_session()` call at line ~8236
  - [x] 2.3: Clear `new_session_name` from session state after session creation
- [x] Task 3: Preserve blank-name default behavior (AC: #3)
  - [x] 3.1: Ensure empty string from text_input flows through as `name=""` (no `None` or missing param)
  - [x] 3.2: Verify `render_session_card_html()` at line ~7639 still shows "Unnamed Adventure" for `name=""`
- [x] Task 4: Clear session name state on navigation (AC: #1)
  - [x] 4.1: Add `"new_session_name"` to the `clear_module_discovery_state()` keys list at line ~7793
  - [x] 4.2: Ensure back-button from module selection clears session name state
- [x] Task 5: Write tests (AC: #1-4)
  - [x] 5.1: Test session name input stored in session state
  - [x] 5.2: Test `handle_new_session_click()` passes name to `create_new_session()`
  - [x] 5.3: Test blank name preserved as empty string (default behavior)
  - [x] 5.4: Test session name cleared on back navigation
  - [x] 5.5: Test session card displays custom name
  - [x] 5.6: Test session card displays "Unnamed Adventure" for blank name
  - [x] 5.7: Test XSS resilience: HTML in session name is escaped in session card

## Dev Notes

### Key Constraint: This is a MINIMAL story

The backend already fully supports session naming. `create_new_session(name="...")` in `persistence.py:738-776` accepts an optional `name` parameter and stores it in `SessionMetadata`. Session cards in `app.py:7639` already display the name (showing "Unnamed Adventure" when empty). The ONLY gap is: **no UI text input for users to enter a name** and the `handle_new_session_click()` function does not pass a name.

### Files to Modify

1. **`app.py`** (primary changes)
   - `render_module_selection_view()` at line ~8181: Add `st.text_input` for session name
   - `handle_new_session_click()` at line ~8216: Read session name from state and pass to `create_new_session()`
   - `clear_module_discovery_state()` at line ~7793: Add `"new_session_name"` to cleanup keys

2. **`styles/theme.css`** (optional/minimal)
   - May need minor styling for the session name input placement in the adventure flow

3. **`tests/test_story_13_1_session_naming.py`** (new file)
   - Test file following existing convention: `test_story_{epic}_{story}_{name}.py`

### Files NOT to Modify (already working)

- **`persistence.py`**: `create_new_session(name="...")` already works. Do NOT change.
- **`models.py`**: `SessionMetadata.name` field already exists at line 318. Do NOT change.
- **`app.py` render_session_card_html()**: Already shows `metadata.name` or "Unnamed Adventure" at line 7639. Do NOT change this function.

### Implementation Details

**Adding the text input in `render_module_selection_view()`** (app.py ~line 8181):

The text input should be placed BEFORE the module selection grid, after the step header and caption. The current flow is:
```
Step header ("Step 1: Choose Your Adventure")
Caption
Back button
[module_selection_confirmed check]
render_module_selection_ui()
```

Add the session name input after the caption, before the back button:
```python
# Session name input (Story 13.1)
session_name = st.text_input(
    "Adventure Name",
    value=st.session_state.get("new_session_name", ""),
    placeholder="Name your adventure (optional)",
    key="session_name_input",
)
st.session_state["new_session_name"] = session_name
```

**Important Streamlit behavior**: `st.text_input` returns the current value. Store it in session state so it persists across reruns. Use a separate session state key (`new_session_name`) from the widget key (`session_name_input`) to avoid Streamlit widget key conflicts.

**Wiring the name in `handle_new_session_click()`** (app.py ~line 8236):

Current code:
```python
session_id = create_new_session(character_names=character_names)
```

Change to:
```python
session_name = st.session_state.get("new_session_name", "")
session_id = create_new_session(name=session_name, character_names=character_names)
# Clear the session name from state after use
st.session_state.pop("new_session_name", None)
```

**Cleanup in `clear_module_discovery_state()`** (app.py ~line 7793):

Add `"new_session_name"` to the `keys_to_clear` list so navigating away clears stale state.

### Security Considerations

- The `render_session_card_html()` function at line 7639 already uses `escape_html(metadata.name)` for XSS protection. No additional escaping needed.
- The `st.text_input` Streamlit widget handles input sanitization.
- Add a test verifying HTML characters in session name are escaped in card output.

### Testing Strategy

Follow the project test convention (`tests/test_story_13_1_session_naming.py`). Reference patterns from `test_story_7_4_new_adventure_flow.py` for mocking Streamlit session state.

Key test patterns:
- Mock `st.session_state` as a dict
- Mock `st.text_input` to return desired values
- Mock `create_new_session` to verify it receives the `name` parameter
- Use `from app import handle_new_session_click, render_session_card_html`
- Use `from models import SessionMetadata`
- Test the `escape_html` behavior for XSS resilience (existing pattern from 7.4 tests)

### Edge Cases

- **Maximum length**: Streamlit `text_input` has no default max length. Consider adding `max_chars=100` to prevent extremely long names.
- **Whitespace-only names**: A name of `"   "` should be treated as blank. Consider `.strip()` before passing to `create_new_session()`.
- **Unicode support**: Session names should support Unicode characters (verified by existing test `test_render_session_card_html_unicode_name` in test_app.py).
- **Error flow recovery**: `handle_error_new_session_click()` at line 3790 also calls `handle_new_session_click()`. Session name will be `""` in this path (no text input was shown), which is correct default behavior.

### Adventure Flow Context

The current new adventure flow is:
1. User clicks "New Adventure" on session browser
2. `handle_start_new_adventure()` sets `app_view = "module_selection"`
3. `render_module_selection_view()` shows module discovery/selection
4. User selects a module (or "Freeform Adventure")
5. `module_selection_confirmed` is set to `True`
6. `handle_new_session_click()` creates session and starts game

Story 13.2 will add a Party Setup step between steps 4 and 6. For Story 13.1, the session name input goes in the `render_module_selection_view()` function (step 3 above), which is the first screen users see. This is a natural placement since users name their adventure as they choose their module.

### Project Structure Notes

- All changes are in the flat layout root files (`app.py`, `styles/theme.css`)
- New test file follows naming convention: `tests/test_story_13_1_session_naming.py`
- No new Pydantic models needed (SessionMetadata.name already exists)
- No new dependencies needed

### References

- [Source: app.py#render_module_selection_view ~line 8181] - Where to add text input
- [Source: app.py#handle_new_session_click ~line 8216] - Where to wire name parameter
- [Source: app.py#clear_module_discovery_state ~line 7793] - Where to add cleanup key
- [Source: app.py#render_session_card_html ~line 7620] - Session card display (no changes needed)
- [Source: persistence.py#create_new_session ~line 738] - Backend already supports name (no changes needed)
- [Source: models.py#SessionMetadata ~line 300] - Name field already exists (no changes needed)
- [Source: tests/test_story_7_4_new_adventure_flow.py] - Reference test patterns
- [Source: tests/test_app.py#test_render_session_card_html_empty_name ~line 10896] - Existing empty name test
- [Source: _bmad-output/planning-artifacts/epics-v1.1.md#Story 13.1] - Epic requirements

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- Initial test run: 3 integration tests failed due to using `list_sessions()` (returns strings) instead of `load_session_metadata()` (returns SessionMetadata). Fixed by switching to correct API.
- Ruff F841 lint fix: renamed unused `mock_create` variable in error recovery test to `mock_create_session` and removed unused assignment in clears-after-creation test.

### Completion Notes List

- Added `st.text_input` for "Adventure Name" in `render_module_selection_view()` with placeholder "Name your adventure (optional)" and `max_chars=100`
- Session name stored in `st.session_state["new_session_name"]` and persists across Streamlit reruns
- `handle_new_session_click()` reads session name from state, strips whitespace, passes `name=` to `create_new_session()`, then clears state
- Added `"new_session_name"` to `clear_module_discovery_state()` cleanup keys for back-button navigation
- Whitespace-only names treated as blank via `.strip()` (edge case from Dev Notes)
- No changes needed to `persistence.py`, `models.py`, or `render_session_card_html()` - backend already supports naming
- Existing XSS protection via `escape_html()` in `render_session_card_html()` verified by tests
- 22 new tests: 5 input tests, 3 wiring tests, 2 blank-name tests, 3 navigation cleanup tests, 1 custom name display, 1 unnamed default display, 3 XSS resilience tests, 4 integration tests
- Full regression suite: 4082 passed, 1 failed (pre-existing LLM timeout), 3 skipped

### File List

- `app.py` (modified) - Added session name text input, wired name to create_new_session, added state cleanup
- `tests/test_story_13_1_session_naming.py` (new) - 22 tests covering all acceptance criteria
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified) - Status updated
- `_bmad-output/implementation-artifacts/stories/13-1-session-naming.md` (modified) - Story file updated

### Change Log

- 2026-02-08: Implemented session naming feature - added text input to module selection view, wired session name to session creation, preserved default blank-name behavior, added navigation state cleanup, and wrote 22 comprehensive tests covering all ACs and XSS resilience.
