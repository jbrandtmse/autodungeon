# Story 4.2: Checkpoint Browser & Restore

Status: review

## Story

As a **user**,
I want **to view available checkpoints and restore to any previous turn**,
so that **I can recover from errors or revisit earlier points in the story**.

## Acceptance Criteria

1. **Given** the session history view in the UI
   **When** I access it
   **Then** I see a list of available checkpoints for the current session (FR34)
   **And** each checkpoint shows: turn number, timestamp, brief context

2. **Given** the checkpoint list
   **When** I select a checkpoint
   **Then** I see a preview of what was happening at that turn

3. **Given** I want to restore to a previous checkpoint
   **When** I click "Restore" on a checkpoint
   **Then** the game state is loaded from that checkpoint file (FR35)
   **And** all agent memories are restored to that exact state (FR36, NFR13)

4. **Given** a restore operation completes
   **When** the game resumes
   **Then** it continues from the restored turn
   **And** all turns after that checkpoint are effectively "undone"

5. **Given** the `load_checkpoint(session_id, turn_number)` function
   **When** called
   **Then** it deserializes the JSON file back into a valid GameState
   **And** populates `st.session_state["game"]` with the restored state

## Tasks / Subtasks

- [x] Task 1: Extend checkpoint metadata capture (AC: #1)
  - [x] 1.1 Add timestamp field to checkpoint serialization in persistence.py
  - [x] 1.2 Add brief_context field (first 100 chars of last log entry)
  - [x] 1.3 Create `CheckpointInfo` Pydantic model with turn_number, timestamp, brief_context
  - [x] 1.4 Create `get_checkpoint_info(session_id, turn_number) -> CheckpointInfo | None`
  - [x] 1.5 Create `list_checkpoint_info(session_id) -> list[CheckpointInfo]`
  - [x] 1.6 Write tests for checkpoint metadata functions

- [x] Task 2: Implement checkpoint browser UI component (AC: #1, #2)
  - [x] 2.1 Create `render_checkpoint_browser()` function in app.py
  - [x] 2.2 Add expander section in sidebar for "Session History"
  - [x] 2.3 Display checkpoint list with turn number, timestamp, and context preview
  - [x] 2.4 Use campfire aesthetic styling (warm colors, Lora font for context)
  - [x] 2.5 Add loading state indicator while fetching checkpoint list (handled via Streamlit rerun pattern)
  - [x] 2.6 Write tests for checkpoint browser rendering

- [x] Task 3: Implement checkpoint preview (AC: #2)
  - [x] 3.1 Create `get_checkpoint_preview(session_id, turn_number) -> list[str] | None`
  - [x] 3.2 Preview shows last 5 log entries from that checkpoint (configurable)
  - [x] 3.3 Add "Preview" button on each checkpoint entry
  - [x] 3.4 Display preview in expanded section with close button
  - [x] 3.5 Write tests for checkpoint preview functionality

- [x] Task 4: Implement restore functionality (AC: #3, #4, #5)
  - [x] 4.1 Create `handle_checkpoint_restore(session_id, turn_number)` in app.py
  - [x] 4.2 Load checkpoint using existing `load_checkpoint()` function
  - [x] 4.3 Update `st.session_state["game"]` with restored GameState
  - [x] 4.4 Reset UI state (ui_mode, human_active, controlled_character, etc.)
  - [x] 4.5 Show confirmation toast: "Restored to Turn X"
  - [x] 4.6 Trigger st.rerun() to refresh UI with restored state
  - [x] 4.7 Write tests for restore functionality

- [x] Task 5: Add restore confirmation dialog (AC: #3)
  - [x] 5.1 Create `render_restore_confirmation(session_id, turn_number)` function
  - [x] 5.2 Show warning: "This will undo X turn(s)"
  - [x] 5.3 Add "Confirm Restore" and "Cancel" buttons
  - [x] 5.4 Style confirmation using warning colors (amber)
  - [x] 5.5 Write tests for confirmation dialog

- [x] Task 6: Add CSS styling for checkpoint browser (AC: #1, #2)
  - [x] 6.1 Add `.checkpoint-list` container styles to theme.css
  - [x] 6.2 Add `.checkpoint-entry` styles with hover effect and border-left accent
  - [x] 6.3 Add `.checkpoint-timestamp` secondary text styling
  - [x] 6.4 Add `.checkpoint-context` preview text styling (italic, truncated)
  - [x] 6.5 Add restore/preview button styling in sidebar context
  - [x] 6.6 Add `.restore-confirmation` styling
  - [x] 6.7 Write CSS class existence tests

- [x] Task 7: Handle edge cases (AC: #3, #4, #5)
  - [x] 7.1 Handle empty checkpoint list (shows "No checkpoints available yet")
  - [x] 7.2 Handle invalid/corrupted checkpoint files gracefully (skip in list)
  - [x] 7.3 Handle restore during active generation (button disabled)
  - [x] 7.4 Handle restore when autopilot is running (stop autopilot first)
  - [x] 7.5 Handle message_count check to only show restore for past checkpoints
  - [x] 7.6 Write edge case tests

- [x] Task 8: Integration and acceptance tests
  - [x] 8.1 Test checkpoint list displays correctly with multiple checkpoints
  - [x] 8.2 Test checkpoint preview shows correct content
  - [x] 8.3 Test restore updates game state completely
  - [x] 8.4 Test agent memories are fully restored
  - [x] 8.5 Test UI state resets after restore
  - [x] 8.6 Test confirmation dialog appears before restore
  - [x] 8.7 Test game can continue after restore (via current_turn preservation)
  - [x] 8.8 Test deserialize returns valid GameState

## Dev Agent Record

### Agent Model
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References
N/A - Implementation completed without issues

### Completion Notes
Story 4.2 implementation completed successfully. All acceptance criteria met:

1. **AC #1**: Checkpoint list shows turn number, timestamp, brief context via `list_checkpoint_info()` and `render_checkpoint_entry_html()`
2. **AC #2**: Preview functionality implemented via `get_checkpoint_preview()` and `render_checkpoint_preview()` showing last 5 log entries
3. **AC #3**: Restore loads checkpoint via `handle_checkpoint_restore()` using existing `load_checkpoint()` function, with confirmation dialog
4. **AC #4**: Game continues from restored turn - current_turn preserved in GameState, UI state reset to watch mode
5. **AC #5**: `load_checkpoint()` deserializes JSON back to valid GameState and populates session state

Key implementation decisions:
- Used file mtime for timestamp (avoids modifying checkpoint format)
- Confirmation dialog shows turns that will be "undone"
- Restore button disabled during generation
- Autopilot automatically stopped on restore
- Checkpoint preview expands inline with close button
- Brief context strips agent prefix and truncates to 100 chars

### File List
- `persistence.py` - Added CheckpointInfo model, get_checkpoint_info(), list_checkpoint_info(), get_checkpoint_preview()
- `app.py` - Added render_checkpoint_entry_html(), handle_checkpoint_restore(), render_checkpoint_preview(), render_restore_confirmation(), render_checkpoint_browser()
- `styles/theme.css` - Added checkpoint-list, checkpoint-entry, checkpoint-header, checkpoint-turn, checkpoint-timestamp, checkpoint-context, checkpoint-preview, restore-confirmation, checkpoint-empty CSS classes
- `tests/test_persistence.py` - Added TestCheckpointInfo, TestListCheckpointInfo, TestCheckpointPreview, TestStory42AcceptanceCriteria test classes (23 tests)
- `tests/test_app.py` - Added TestCheckpointBrowserCSS, TestRenderCheckpointEntryHtml, TestHandleCheckpointRestore, TestCheckpointBrowserUI test classes (21 tests)

### Change Log
1. Added `CheckpointInfo` Pydantic model with turn_number, timestamp, brief_context, message_count fields
2. Added `get_checkpoint_info()` function extracting metadata without full GameState load
3. Added `list_checkpoint_info()` function returning checkpoints sorted newest-first
4. Added `get_checkpoint_preview()` function returning last N log entries
5. Added `render_checkpoint_entry_html()` generating HTML for checkpoint list entries
6. Added `handle_checkpoint_restore()` managing state update and UI reset
7. Added `render_checkpoint_preview()` displaying checkpoint preview with close button
8. Added `render_restore_confirmation()` showing confirmation dialog with turn count
9. Added `render_checkpoint_browser()` composing full browser UI in sidebar expander
10. Added comprehensive CSS styling for checkpoint browser matching campfire theme
11. Added 44 tests covering all functionality and acceptance criteria

### Test Results
```
====================== 1081 passed, 1 skipped in 14.67s =======================
```

All 1081 tests pass including:
- 23 new tests in test_persistence.py (Story 4.2)
- 21 new tests in test_app.py (Story 4.2)
- All existing tests continue to pass

## Dev Notes

### Existing Infrastructure Analysis

**persistence.py (Current State):**
The persistence module already has the core checkpoint functions implemented from Story 4.1:

```python
# Path utilities
format_session_id(session_number: int) -> str
get_session_dir(session_id: str) -> Path
get_checkpoint_path(session_id: str, turn_number: int) -> Path
ensure_session_dir(session_id: str) -> Path

# Serialization
serialize_game_state(state: GameState) -> str
deserialize_game_state(json_str: str) -> GameState

# Core functions
save_checkpoint(state: GameState, session_id: str, turn_number: int) -> Path
load_checkpoint(session_id: str, turn_number: int) -> GameState | None

# Listing
list_sessions() -> list[str]
list_checkpoints(session_id: str) -> list[int]
get_latest_checkpoint(session_id: str) -> int | None
```

Key observations:
- `load_checkpoint()` already returns a fully deserialized `GameState` or `None`
- `list_checkpoints()` returns turn numbers but no metadata (timestamp, context)
- Checkpoint files are stored at `campaigns/session_XXX/turn_XXX.json`

**Current checkpoint file format (from serialize_game_state):**
```json
{
  "ground_truth_log": [...],
  "turn_queue": [...],
  "current_turn": "...",
  "agent_memories": {...},
  "game_config": {...},
  "dm_config": {...},
  "characters": {...},
  "whisper_queue": [...],
  "human_active": false,
  "controlled_character": null,
  "session_number": 1,
  "session_id": "001"
}
```

**Missing for Story 4.2:**
- No timestamp in checkpoint files (need to add or derive from file mtime)
- No metadata extraction function for quick listing
- No preview/context extraction function

**app.py (Current State - UI Patterns):**
The app has established UI patterns from previous stories:

Sidebar sections pattern:
```python
def render_sidebar(config: AppConfig) -> None:
    with st.sidebar:
        # Mode indicator
        st.markdown(render_mode_indicator_html(...), unsafe_allow_html=True)
        st.markdown("---")

        # Party panel
        st.markdown("### Party")
        # ... character cards
        st.markdown("---")

        # Session controls
        render_session_controls()
        st.markdown("---")

        # LLM Status expander
        with st.expander("LLM Status", expanded=False):
            # ...
```

Handler pattern for user actions:
```python
def handle_drop_in_click(agent_key: str) -> None:
    # Update session state
    st.session_state["controlled_character"] = agent_key
    # ... state changes

# Then in render function:
if st.button(label, key=f"drop_in_{agent_key}"):
    handle_drop_in_click(agent_key)
    st.rerun()
```

HTML rendering pattern:
```python
def render_checkpoint_entry_html(turn: int, timestamp: str, context: str) -> str:
    """Generate HTML for a single checkpoint entry."""
    return (
        f'<div class="checkpoint-entry">'
        f'<span class="checkpoint-turn">Turn {turn}</span>'
        f'<span class="checkpoint-timestamp">{escape_html(timestamp)}</span>'
        f'<p class="checkpoint-context">{escape_html(context)}</p>'
        f'</div>'
    )
```

**Session State Keys (from initialize_session_state):**
```python
st.session_state["game"]                  # GameState object
st.session_state["ui_mode"]               # "watch" | "play"
st.session_state["controlled_character"]  # str | None
st.session_state["human_active"]          # bool
st.session_state["is_generating"]         # bool
st.session_state["is_paused"]             # bool
st.session_state["playback_speed"]        # "slow" | "normal" | "fast"
st.session_state["auto_scroll_enabled"]   # bool
st.session_state["is_autopilot_running"]  # bool
st.session_state["autopilot_turn_count"]  # int
st.session_state["human_pending_action"]  # str | None
st.session_state["waiting_for_human"]     # bool
st.session_state["pending_nudge"]         # str | None
st.session_state["nudge_submitted"]       # bool
st.session_state["modal_open"]            # bool
st.session_state["pre_modal_pause_state"] # bool
```

### Architecture Compliance

Per architecture.md:

| Decision | Compliance |
|----------|------------|
| Checkpoint Format: Single JSON | Following - reading existing format |
| Naming: `session_xxx/turn_xxx.json` | Following - using existing path functions |
| State in `st.session_state["game"]` | Following - restore updates session state |
| UI theming: Campfire aesthetic | Following - warm colors, Lora font |
| Button styling hierarchy | Following - match existing button patterns |

**UI/UX Requirements (from UX design spec):**
- Sidebar width: 240px fixed
- Expander sections for secondary content
- Warm color palette: #1A1612 background, #2D2520 surfaces, #F5E6D3 text
- Secondary text: #B8A896
- Warning/caution: Amber (#E8A849)

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR34 | View list of available checkpoints | render_checkpoint_browser(), list_checkpoint_info() |
| FR35 | Restore game state from checkpoint | handle_checkpoint_restore(), load_checkpoint() |
| FR36 | Restore agent memories to checkpoint state | load_checkpoint() already handles this |
| NFR12 | Recovery granularity - any previous turn | Full turn list displayed, any selectable |
| NFR13 | State consistency - complete agent memory state | GameState includes agent_memories |

[Source: epics.md#Story 4.2, prd.md#Persistence & Recovery]

### What This Story Does NOT Do

- Does NOT implement campaign selection/switching (Story 4.3)
- Does NOT implement "While you were away" summary (Story 4.3)
- Does NOT implement transcript export (Story 4.4)
- Does NOT implement error recovery dialogs (Story 4.5)
- Does NOT delete checkpoints after restore (keep all for flexibility)
- Does NOT implement checkpoint comparison/diff view

### Previous Story Intelligence (from Story 4.1)

**Key Learnings:**
- Checkpoint serialization handles nested Pydantic models correctly
- Atomic write pattern ensures crash safety
- session_id field added to GameState for persistence
- Tests organized in dedicated classes (TestPathUtilities, TestSaveCheckpoint, etc.)

**Pattern to follow:**
```
Implement Story 4.2: Checkpoint Browser & Restore with code review fixes
```

All Story 4.1 tests passing (60 tests in test_persistence.py) before this story.

[Source: _bmad-output/implementation-artifacts/4-1-auto-checkpoint-system.md]

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

#### Checkpoint Metadata Model (persistence.py)

```python
from datetime import datetime
from pydantic import BaseModel, Field


class CheckpointInfo(BaseModel):
    """Metadata about a checkpoint for display in the browser.

    Attributes:
        turn_number: The turn number for this checkpoint.
        timestamp: When the checkpoint was saved (ISO format or file mtime).
        brief_context: First 100 chars of the last log entry for preview.
        message_count: Number of messages in ground_truth_log.
    """
    turn_number: int = Field(..., ge=0)
    timestamp: str = Field(...)
    brief_context: str = Field(default="")
    message_count: int = Field(default=0, ge=0)
```

#### Metadata Extraction Functions (persistence.py)

```python
def get_checkpoint_info(session_id: str, turn_number: int) -> CheckpointInfo | None:
    """Get metadata for a specific checkpoint.

    Extracts metadata without loading the full GameState for efficiency.
    Uses file mtime for timestamp if not stored in checkpoint.

    Args:
        session_id: Session ID string.
        turn_number: Turn number to get info for.

    Returns:
        CheckpointInfo with metadata, or None if checkpoint doesn't exist.
    """
    checkpoint_path = get_checkpoint_path(session_id, turn_number)

    if not checkpoint_path.exists():
        return None

    try:
        # Get file modification time for timestamp
        mtime = checkpoint_path.stat().st_mtime
        timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

        # Load just enough to get context
        json_content = checkpoint_path.read_text(encoding="utf-8")
        data = json.loads(json_content)

        log = data.get("ground_truth_log", [])
        message_count = len(log)

        # Get brief context from last log entry
        brief_context = ""
        if log:
            last_entry = log[-1]
            # Remove agent prefix [agent] if present
            if last_entry.startswith("["):
                bracket_end = last_entry.find("]")
                if bracket_end > 0:
                    last_entry = last_entry[bracket_end + 1:].strip()
            brief_context = last_entry[:100] + ("..." if len(last_entry) > 100 else "")

        return CheckpointInfo(
            turn_number=turn_number,
            timestamp=timestamp,
            brief_context=brief_context,
            message_count=message_count,
        )
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def list_checkpoint_info(session_id: str) -> list[CheckpointInfo]:
    """List all checkpoints with metadata for a session.

    Args:
        session_id: Session ID string.

    Returns:
        List of CheckpointInfo, sorted by turn number descending (newest first).
    """
    turn_numbers = list_checkpoints(session_id)

    infos: list[CheckpointInfo] = []
    for turn in turn_numbers:
        info = get_checkpoint_info(session_id, turn)
        if info:
            infos.append(info)

    # Sort descending (newest first) for display
    return sorted(infos, key=lambda x: x.turn_number, reverse=True)
```

#### Checkpoint Preview Function (persistence.py)

```python
def get_checkpoint_preview(
    session_id: str, turn_number: int, num_messages: int = 5
) -> list[str] | None:
    """Get the last N log entries from a checkpoint for preview.

    Args:
        session_id: Session ID string.
        turn_number: Turn number to preview.
        num_messages: Number of recent messages to return (default 5).

    Returns:
        List of log entries (most recent last), or None if checkpoint doesn't exist.
    """
    state = load_checkpoint(session_id, turn_number)
    if state is None:
        return None

    log = state.get("ground_truth_log", [])
    return log[-num_messages:] if log else []
```

#### Checkpoint Browser UI (app.py)

```python
def render_checkpoint_entry_html(info: "CheckpointInfo") -> str:
    """Generate HTML for a single checkpoint list entry.

    Args:
        info: CheckpointInfo with turn metadata.

    Returns:
        HTML string for checkpoint entry.
    """
    return (
        f'<div class="checkpoint-entry">'
        f'<div class="checkpoint-header">'
        f'<span class="checkpoint-turn">Turn {info.turn_number}</span>'
        f'<span class="checkpoint-timestamp">{escape_html(info.timestamp)}</span>'
        f'</div>'
        f'<p class="checkpoint-context">{escape_html(info.brief_context)}</p>'
        f'</div>'
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

    return True


def render_checkpoint_browser() -> None:
    """Render checkpoint browser section in sidebar.

    Shows list of available checkpoints with preview and restore options.
    """
    from persistence import list_checkpoint_info

    game: GameState = st.session_state.get("game", {})
    session_id = game.get("session_id", "001")

    with st.expander("Session History", expanded=False):
        checkpoints = list_checkpoint_info(session_id)

        if not checkpoints:
            st.caption("No checkpoints available yet")
            return

        st.markdown('<div class="checkpoint-list">', unsafe_allow_html=True)

        for info in checkpoints:
            # Display checkpoint info
            st.markdown(
                render_checkpoint_entry_html(info),
                unsafe_allow_html=True
            )

            # Restore button
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Preview", key=f"preview_{info.turn_number}"):
                    st.session_state[f"show_preview_{info.turn_number}"] = True
                    st.rerun()

            with col2:
                # Disable during generation
                is_generating = st.session_state.get("is_generating", False)
                current_turn = len(game.get("ground_truth_log", []))

                # Don't show restore for current turn
                if info.turn_number < current_turn:
                    if st.button(
                        "Restore",
                        key=f"restore_{info.turn_number}",
                        disabled=is_generating
                    ):
                        st.session_state["pending_restore"] = info.turn_number
                        st.rerun()

            # Show preview if expanded
            if st.session_state.get(f"show_preview_{info.turn_number}"):
                render_checkpoint_preview(session_id, info.turn_number)

            st.markdown("---")

        st.markdown('</div>', unsafe_allow_html=True)

        # Handle pending restore with confirmation
        pending_restore = st.session_state.get("pending_restore")
        if pending_restore is not None:
            render_restore_confirmation(session_id, pending_restore)


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
        # Simple rendering - just show the text
        st.markdown(f"_{escape_html(entry)}_")

    st.markdown('</div>', unsafe_allow_html=True)

    # Close preview button
    if st.button("Close", key=f"close_preview_{turn_number}"):
        st.session_state[f"show_preview_{turn_number}"] = False
        st.rerun()


def render_restore_confirmation(session_id: str, turn_number: int) -> None:
    """Render restore confirmation dialog.

    Args:
        session_id: Session ID string.
        turn_number: Turn number to restore to.
    """
    game: GameState = st.session_state.get("game", {})
    current_turn = len(game.get("ground_truth_log", []))
    turns_to_undo = current_turn - turn_number

    st.warning(
        f"Restore to Turn {turn_number}? "
        f"This will undo {turns_to_undo} turn(s).",
        icon="⚠️"
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Confirm Restore", key="confirm_restore"):
            if handle_checkpoint_restore(session_id, turn_number):
                st.session_state["pending_restore"] = None
                st.success(f"Restored to Turn {turn_number}")
                st.rerun()
            else:
                st.error("Failed to restore checkpoint")

    with col2:
        if st.button("Cancel", key="cancel_restore"):
            st.session_state["pending_restore"] = None
            st.rerun()
```

#### CSS Styles for Checkpoint Browser (styles/theme.css)

```css
/* Checkpoint Browser Styles */
.checkpoint-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.checkpoint-entry {
    background: var(--background-secondary);
    border-radius: 8px;
    padding: 12px;
    border-left: 3px solid var(--accent);
}

.checkpoint-entry:hover {
    background: var(--background-tertiary);
}

.checkpoint-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}

.checkpoint-turn {
    font-family: var(--font-ui);
    font-weight: 600;
    color: var(--text-primary);
}

.checkpoint-timestamp {
    font-family: var(--font-ui);
    font-size: 12px;
    color: var(--text-secondary);
}

.checkpoint-context {
    font-family: var(--font-narrative);
    font-size: 14px;
    font-style: italic;
    color: var(--text-secondary);
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.checkpoint-preview {
    background: var(--background-primary);
    border-radius: 4px;
    padding: 8px;
    margin: 8px 0;
    border-left: 2px solid var(--text-secondary);
}

.checkpoint-preview p {
    font-family: var(--font-narrative);
    font-size: 13px;
    color: var(--text-secondary);
    margin: 4px 0;
}
```

### Integration with render_sidebar

Add the checkpoint browser to the sidebar after session controls:

```python
def render_sidebar(config: AppConfig) -> None:
    with st.sidebar:
        # ... existing code ...

        # Session controls (Story 2.5)
        render_session_controls()

        st.markdown("---")

        # Checkpoint Browser (Story 4.2) - NEW
        render_checkpoint_browser()

        st.markdown("---")

        # Nudge System (Story 3.4)
        render_nudge_input()

        # ... rest of sidebar ...
```

### Testing Strategy

Organize tests in dedicated test classes:

```python
# tests/test_persistence.py additions
class TestCheckpointInfo:
    """Tests for CheckpointInfo model and get_checkpoint_info."""

class TestListCheckpointInfo:
    """Tests for list_checkpoint_info function."""

class TestCheckpointPreview:
    """Tests for get_checkpoint_preview function."""


# tests/test_app.py additions
class TestCheckpointBrowser:
    """Tests for checkpoint browser UI rendering."""

class TestCheckpointRestore:
    """Tests for checkpoint restore functionality."""

class TestRestoreConfirmation:
    """Tests for restore confirmation dialog."""

class TestStory42AcceptanceCriteria:
    """Acceptance tests for all Story 4.2 criteria."""
```

**Key Test Cases:**

```python
def test_get_checkpoint_info_returns_metadata():
    """Test checkpoint info includes turn, timestamp, context."""
    # Save a checkpoint
    state = populate_game_state(include_sample_messages=True)
    save_checkpoint(state, "001", 5)

    # Get info
    info = get_checkpoint_info("001", 5)

    assert info is not None
    assert info.turn_number == 5
    assert info.timestamp  # Non-empty
    assert info.brief_context  # Non-empty
    assert info.message_count > 0


def test_list_checkpoint_info_sorted_descending():
    """Test checkpoint list is sorted newest first."""
    state = populate_game_state()
    save_checkpoint(state, "001", 1)
    save_checkpoint(state, "001", 2)
    save_checkpoint(state, "001", 3)

    infos = list_checkpoint_info("001")

    assert len(infos) == 3
    assert infos[0].turn_number == 3  # Newest first
    assert infos[1].turn_number == 2
    assert infos[2].turn_number == 1


def test_restore_updates_game_state():
    """Test restore loads checkpoint into session state."""
    # Create two different states
    state1 = populate_game_state(include_sample_messages=True)
    state1["ground_truth_log"].append("[dm] First checkpoint")
    save_checkpoint(state1, "001", 1)

    state2 = populate_game_state(include_sample_messages=True)
    state2["ground_truth_log"].extend(["[dm] First", "[dm] Second"])
    save_checkpoint(state2, "001", 2)

    # Set current state to state2
    st.session_state["game"] = state2

    # Restore to state1
    result = handle_checkpoint_restore("001", 1)

    assert result is True
    restored = st.session_state["game"]
    assert len(restored["ground_truth_log"]) == len(state1["ground_truth_log"])


def test_restore_resets_ui_state():
    """Test restore clears UI control state."""
    st.session_state["human_active"] = True
    st.session_state["controlled_character"] = "rogue"
    st.session_state["is_autopilot_running"] = True

    state = populate_game_state()
    save_checkpoint(state, "001", 1)

    handle_checkpoint_restore("001", 1)

    assert st.session_state["human_active"] is False
    assert st.session_state["controlled_character"] is None
    assert st.session_state["is_autopilot_running"] is False


def test_restore_during_generation_disabled():
    """Test restore button is disabled while generating."""
    # This is a UI test - verify button has disabled=True
    pass


def test_checkpoint_preview_shows_recent_messages():
    """Test preview returns last N messages."""
    state = populate_game_state()
    state["ground_truth_log"] = [f"[dm] Message {i}" for i in range(10)]
    save_checkpoint(state, "001", 10)

    preview = get_checkpoint_preview("001", 10, num_messages=3)

    assert preview is not None
    assert len(preview) == 3
    assert preview[-1] == "[dm] Message 9"  # Last message
```

### Security Considerations

- **Path Traversal:** Already protected by `_validate_session_id()` from Story 4.1
- **Input Validation:** Turn numbers validated as integers in existing functions
- **State Tampering:** Checkpoint files on local disk, same trust model as Story 4.1
- **UI Injection:** All user-visible content HTML-escaped via `escape_html()`

### Edge Cases

1. **Empty checkpoint list:** Show "No checkpoints available yet" message
2. **Corrupted checkpoint:** `get_checkpoint_info()` returns None, skip in list
3. **Restore during generation:** Button disabled via `is_generating` flag
4. **Restore with autopilot:** Stop autopilot before restoring
5. **Restore to current turn:** Don't show restore button for current turn
6. **Preview of deleted checkpoint:** Handle gracefully with error message
7. **Rapid restore clicks:** Button disabled after first click via st.rerun()
8. **Very long context text:** Truncate to 100 chars with ellipsis

### Performance Considerations

- `list_checkpoint_info()` reads each checkpoint file's first few KB
- For sessions with many checkpoints (100+), consider lazy loading
- File mtime used for timestamp avoids full checkpoint parsing
- Preview loads full checkpoint but only returns last N entries

### References

- [Source: planning-artifacts/prd.md#Persistence & Recovery FR33-FR41]
- [Source: planning-artifacts/architecture.md#Persistence Strategy]
- [Source: planning-artifacts/epics.md#Story 4.2]
- [Source: persistence.py] - Existing checkpoint functions
- [Source: app.py] - UI patterns and session state
- [Source: _bmad-output/implementation-artifacts/4-1-auto-checkpoint-system.md] - Previous story patterns
