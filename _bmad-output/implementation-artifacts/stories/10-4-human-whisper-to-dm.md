# Story 10-4: Human Whisper to DM

## Story

As a **human player**,
I want **to whisper privately to the DM**,
So that **I can suggest secrets or ask for private information**.

## Status

**Status:** done
**Epic:** 10 - DM Whisper & Secrets System
**Created:** 2026-02-05
**Implemented:** 2026-02-05
**Reviewed:** 2026-02-05

## Acceptance Criteria

**Given** the existing nudge system
**When** extended
**Then** there's a "Whisper to DM" option separate from nudge

**Given** the whisper input
**When** I type a message
**Then** it's marked as private and only the DM sees it

**Given** a human whisper
**When** sent
**Then** it appears in the DM's context as:
```
## Player Whisper
The human player privately asks: "Can my rogue notice if the merchant is lying?"
```

**Given** the DM processes a human whisper
**When** responding
**Then** it may whisper back information or incorporate it into narrative

**Given** human whispers
**When** logged
**Then** they're tracked in the whisper history but not in public transcript

## FRs Covered

- FR73: Human can whisper to DM (extends existing nudge)
- FR75: Whisper history is tracked per agent (partially - human whisper tracking)

## Technical Notes

### Distinction from Nudge System

The existing nudge system (Story 3.4) allows the human to send general suggestions to the DM. Human whispers are different:

| Feature | Nudge | Human Whisper |
|---------|-------|---------------|
| Purpose | General game suggestions | Private questions/secrets |
| Visibility | Could be incorporated into public narrative | Private DM-only communication |
| Tracking | Single-use, not persisted | Persisted in whisper history |
| Context Format | `## Player Suggestion` | `## Player Whisper` |
| Response | DM may incorporate | DM may whisper back or act privately |

### Existing Nudge Implementation

The nudge system is implemented in `app.py`:

1. **UI**: `render_nudge_input()` renders a text area in the sidebar (visible in Watch Mode only)
2. **Handler**: `handle_nudge_submit(nudge)` stores the nudge in `st.session_state["pending_nudge"]`
3. **Context Injection**: `_build_dm_context()` in `agents.py` includes the nudge as `## Player Suggestion`
4. **Clearing**: `dm_turn()` clears `pending_nudge` after reading

### Human Whisper Implementation Approach

Extend the nudge UI to include a separate whisper option:

```python
# In app.py - extend render_nudge_input() or add render_whisper_input()

def render_human_whisper_input() -> None:
    """Render human whisper to DM input in the sidebar.

    Separate from nudge - for private questions/secrets to DM.
    """
    if st.session_state.get("human_active"):
        return  # Don't show if controlling a character

    st.markdown(
        '<div class="whisper-input-container">'
        '<div class="whisper-label">Whisper to DM</div>'
        '<p class="whisper-hint">Ask the DM something privately...</p>'
        "</div>",
        unsafe_allow_html=True
    )

    whisper = st.text_area(
        "Whisper input",
        key="human_whisper_input",
        placeholder="e.g., 'Can my rogue tell if the merchant is lying?'",
        label_visibility="collapsed",
        height=60,
    )

    if st.button("Send Whisper", key="whisper_submit_btn", use_container_width=True):
        handle_human_whisper_submit(whisper)
        if "human_whisper_input" in st.session_state:
            del st.session_state["human_whisper_input"]
        st.rerun()

    if st.session_state.get("whisper_submitted"):
        st.success("Whisper sent - the DM will respond privately", icon="...")
        st.session_state["whisper_submitted"] = False
```

### Session State Keys

Add new session state keys for human whispers:

- `pending_human_whisper: str | None` - Current whisper awaiting DM processing
- `whisper_submitted: bool` - Flag for showing confirmation toast
- `human_whisper_history: list[Whisper]` - Persisted history of human whispers

### Whisper Storage Model

Human whispers use the existing `Whisper` model with `from_agent="human"`:

```python
from models import create_whisper

whisper = create_whisper(
    from_agent="human",
    to_agent="dm",  # Human whispers go to DM
    content="Can my rogue tell if the merchant is lying?",
    turn_created=current_turn_number,
)
```

### Context Injection

Update `_build_dm_context()` in `agents.py` to include human whispers:

```python
# After the existing nudge section
pending_human_whisper = st.session_state.get("pending_human_whisper")
if pending_human_whisper:
    sanitized = str(pending_human_whisper).strip()
    if sanitized:
        context_parts.append(
            f"## Player Whisper\nThe human player privately asks: \"{sanitized}\""
        )
```

Note: Human whispers use a different format than nudges:
- Nudge: `## Player Suggestion\nThe player offers this thought: ...`
- Whisper: `## Player Whisper\nThe human player privately asks: "..."`

### Whisper History Tracking

Human whispers should be persisted in the whisper history:

1. Create a dedicated storage location for human-to-DM whispers
2. Option A: Store in `agent_secrets["dm"]` (DM as recipient)
3. Option B: Store in a separate `human_whispers: list[Whisper]` in GameState

**Recommended: Option A** - Use existing `agent_secrets["dm"]` to store whispers TO the DM. This is consistent with the Whisper model where `to_agent` is the recipient.

```python
def handle_human_whisper_submit(whisper_text: str) -> None:
    """Handle submission of human whisper to DM.

    Stores the whisper for DM context and persists in whisper history.
    """
    sanitized = whisper_text.strip()[:MAX_WHISPER_LENGTH]

    if sanitized:
        # Store for immediate DM context
        st.session_state["pending_human_whisper"] = sanitized
        st.session_state["whisper_submitted"] = True

        # Create whisper for history tracking
        game = st.session_state.get("game")
        if game:
            current_turn = len(game.get("ground_truth_log", []))
            whisper = create_whisper(
                from_agent="human",
                to_agent="dm",
                content=sanitized,
                turn_created=current_turn,
            )

            # Add to DM's secrets (DM is the recipient)
            agent_secrets = game.get("agent_secrets", {})
            dm_secrets = agent_secrets.get("dm", AgentSecrets())
            new_whispers = dm_secrets.whispers.copy()
            new_whispers.append(whisper)
            agent_secrets["dm"] = dm_secrets.model_copy(update={"whispers": new_whispers})
            game["agent_secrets"] = agent_secrets
```

### Transcript Exclusion

Human whispers should NOT appear in the public transcript (Story 4.4 - Transcript Export):

```python
# In persistence.py append_to_transcript() or equivalent
# Filter out entries that are whispers
if entry.get("is_whisper") or entry.get("type") == "human_whisper":
    return  # Don't add to public transcript
```

Alternative: Mark whispers in ground_truth_log but exclude when exporting transcript.

### DM Response to Whispers

The DM system prompt should include guidance on responding to human whispers:

```python
# Add to DM_SYSTEM_PROMPT in agents.py

## Player Whispers

When you receive a "Player Whisper", the human player is privately asking you something:

- Answer their question through your narration or by whispering back to their character
- If they ask about perception/insight, consider having them roll or just incorporate the answer
- You can use dm_whisper_to_agent to send private information back to their character
- Keep the private nature - don't explicitly reveal in public narration that they asked

Example responses:
- Player whispers: "Can my rogue notice if the merchant is lying?"
  - You could whisper back: "Your keen eyes catch the merchant's tell - his left eye twitches when he mentions the price"
  - Or narrate: "As you study the merchant, something feels off about his demeanor..."
```

### Clearing Human Whispers

Like nudges, human whispers should be cleared after DM processes them:

```python
# In dm_turn() in agents.py, after building context
st.session_state["pending_human_whisper"] = None
```

### UI Layout

The whisper input should appear separately from the nudge input in the sidebar:

```
[Sidebar]
├── Party Panel
├── Session Controls
├── [Divider]
├── Suggest Something (Nudge)
│   └── [Text area + Send Nudge button]
├── [Divider]
├── Whisper to DM (NEW)
│   └── [Text area + Send Whisper button]
```

Alternatively, use tabs or an expander to group both input types:

```
[Sidebar]
├── Party Panel
├── Session Controls
├── [Divider]
├── [Tabs: Suggest | Whisper to DM]
│   └── [Selected tab content]
```

### CSS Styling

Add whisper-specific styles to `styles/theme.css`:

```css
.whisper-input-container {
    margin-bottom: 8px;
}

.whisper-label {
    font-family: var(--font-ui);
    font-size: 14px;
    font-weight: 600;
    color: var(--color-primary-text);
    margin-bottom: 4px;
}

.whisper-hint {
    font-family: var(--font-ui);
    font-size: 12px;
    color: var(--color-secondary-text);
    margin: 0 0 8px 0;
    font-style: italic;
}
```

## Tasks

1. [x] Add `pending_human_whisper` and `human_whisper_submitted` to session state initialization in app.py
2. [x] Create `render_human_whisper_input()` function in app.py
3. [x] Create `handle_human_whisper_submit()` function in app.py
4. [x] Add whisper input CSS styles to styles/theme.css
5. [x] Call `render_human_whisper_input()` in sidebar rendering (after nudge input)
6. [x] Update `_build_dm_context()` in agents.py to include `## Player Whisper` section
7. [x] Clear `pending_human_whisper` after DM reads it in dm_turn()
8. [x] Add human whisper to `agent_secrets["dm"]` for history tracking
9. [x] Update DM_SYSTEM_PROMPT with guidance on responding to player whispers
10. [x] Add unit tests for `handle_human_whisper_submit()` function
11. [x] Add unit tests for `render_human_whisper_input()` HTML generation
12. [x] Add unit tests for DM context including player whisper section
13. [x] Add unit tests for whisper history tracking (stored in agent_secrets["dm"])
14. [x] Add integration test verifying human whisper appears in DM context
15. [x] Add integration test verifying whisper clearing after DM turn
16. [x] Add test verifying whisper/nudge distinction (separate keys and formats)
17. [x] Add test for whisper format matching acceptance criteria
18. [ ] Manual UI verification: whisper input visible in Watch Mode
19. [ ] Manual UI verification: whisper confirmation toast appears
20. [ ] Manual UI verification: DM responds appropriately to whispers

## Implementation Notes

### Files Modified

- **app.py**: Added `render_human_whisper_input()`, `render_human_whisper_input_html()`, `handle_human_whisper_submit()`, `MAX_HUMAN_WHISPER_LENGTH` constant, and session state initialization for `pending_human_whisper` and `human_whisper_submitted`
- **agents.py**: Updated `_build_dm_context()` to include `## Player Whisper` section, updated `dm_turn()` to clear `pending_human_whisper` after reading, added player whisper guidance to `DM_SYSTEM_PROMPT`
- **styles/theme.css**: Added CSS styles for `.whisper-input-container`, `.whisper-label`, `.whisper-hint` with purple accent color (var(--color-wizard)) to distinguish from nudge (green)

### Test Coverage

Created `tests/test_story_10_4_human_whisper_to_dm.py` with 31 passing tests:
- TestHandleHumanWhisperSubmit (11 tests)
- TestHandleHumanWhisperSubmitNoGame (1 test)
- TestRenderHumanWhisperInputHtml (3 tests)
- TestRenderHumanWhisperInput (2 tests)
- TestDmContextWithPlayerWhisper (6 tests)
- TestWhisperHistoryTracking (3 tests)
- TestSessionStateInitialization (1 test)
- TestWhisperVsNudgeDistinction (3 tests)
- TestWhisperClearingAfterDmTurn (1 test)

## Dependencies

- **Story 10.1** (done): Provides Whisper model with `from_agent="human"` support
- **Story 10.2** (done): Provides DM whisper tool for responding back to player
- **Story 10.3** (done): Context injection pattern for secrets
- **Story 3.4** (done): Nudge system UI pattern to extend

## Test Approach

### Unit Tests (test_story_10_4_human_whisper_to_dm.py)

1. **handle_human_whisper_submit Tests**
   - Empty whisper is ignored
   - Whitespace-only whisper is ignored
   - Valid whisper stored in `pending_human_whisper`
   - `whisper_submitted` flag set to True
   - Whisper text sanitized (stripped, length limited)
   - Whisper added to `agent_secrets["dm"]`
   - Whisper has correct `from_agent="human"` and `to_agent="dm"`

2. **render_human_whisper_input Tests**
   - Not rendered when `human_active` is True
   - Rendered when in Watch Mode
   - Contains expected HTML structure
   - Contains placeholder text

3. **DM Context Integration Tests**
   - `pending_human_whisper` included in DM context
   - Format matches: `## Player Whisper\nThe human player privately asks: "..."`
   - Empty/None whisper not included
   - Whisper cleared after dm_turn reads it

4. **Whisper History Tests**
   - Human whisper stored in `agent_secrets["dm"]`
   - Multiple whispers accumulate
   - Whisper persists through checkpoint save/load

5. **Transcript Exclusion Tests**
   - Human whispers not in public transcript export
   - Whisper history still accessible separately

### Manual Verification

```bash
streamlit run app.py
# 1. Start new adventure, stay in Watch Mode
# 2. Find "Whisper to DM" input in sidebar
# 3. Type "Can my rogue notice if the barkeeper is lying?"
# 4. Click "Send Whisper"
# 5. Verify confirmation toast appears
# 6. Observe DM response - may include private info or narration
# 7. Check that whisper is NOT in public narrative
```

## Implementation Notes

### Constants

Add to app.py:

```python
# Maximum human whisper text length
MAX_WHISPER_LENGTH = 500
```

### Session State Initialization

Update `init_session_state()` in app.py:

```python
if "pending_human_whisper" not in st.session_state:
    st.session_state["pending_human_whisper"] = None
if "whisper_submitted" not in st.session_state:
    st.session_state["whisper_submitted"] = False
```

### Order of Sidebar Elements

The whisper input should appear AFTER the nudge input to maintain the existing UI hierarchy:

1. Party Panel (character cards)
2. Session Controls (pause, speed)
3. Nudge input (existing)
4. Human Whisper input (NEW)

### Error Handling

Handle edge cases:
- No active game when submitting whisper
- Whisper submission during character control (should be hidden)
- Very long whisper text (truncate)

### Future Considerations

- **Whisper History UI**: A future story could add a UI to view human whisper history
- **DM Whisper Back**: The DM can already use `dm_whisper_to_agent` to send secrets back
- **Controlled Character Whispers**: When controlling a character, the human might want to whisper as that character (different from human-to-DM whispers)

---

## Code Review Record

### Review Date: 2026-02-05

**Reviewer:** Developer (AI-assisted adversarial review)

**Status:** APPROVED with fixes applied

### Issues Found and Fixed

| # | Severity | Issue | Resolution |
|---|----------|-------|------------|
| 1 | HIGH | Missing transcript exclusion tests (AC5) | Added TestWhisperTranscriptExclusion class with 3 tests |
| 2 | HIGH | Emoji used in toast notification violating CLAUDE.md | Removed emoji icon from st.success() call |
| 3 | HIGH | Missing quote sanitization in whisper context | Added quote escaping (double to single quotes) in _build_dm_context |
| 4 | MEDIUM | Test coverage gap for quote handling | Added test_whisper_quotes_escaped test |

### Files Modified During Review

- **app.py**: Removed emoji from whisper confirmation toast (line 840)
- **agents.py**: Added quote escaping for whisper content in _build_dm_context (line 1142)
- **tests/test_story_10_4_human_whisper_to_dm.py**: Added TestWhisperTranscriptExclusion class (3 tests) and test_whisper_quotes_escaped test

### Test Results After Fixes

```
35 passed in 8.01s
```

### Remaining Notes

1. **Manual verification tasks (18-20)** remain incomplete - these require running the app and visually verifying UI behavior
2. **Duplicate session state initialization** (MEDIUM) was documented but not fixed as it follows existing codebase patterns
3. **CSS selector specificity** (MEDIUM) was documented as a known trade-off in the codebase

### Verification Checklist

- [x] All automated tests pass
- [x] Acceptance Criteria 1-4 verified via tests
- [x] AC5 (transcript exclusion) now has dedicated test coverage
- [x] No regressions in existing functionality
- [x] Code follows project patterns (CLAUDE.md compliance)
- [ ] Manual UI verification pending
