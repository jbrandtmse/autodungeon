# Story 12-3: Fork Comparison View

## Story

As a **user**,
I want **to compare how forks diverged from the branch point**,
So that **I can see the consequences of different choices**.

## Status

**Status:** review
**Epic:** 12 - Fork Gameplay
**Created:** 2026-02-07
**FRs Covered:** FR83 (user can compare forks side-by-side to see divergent narratives)
**Predecessors:** Story 12.1 (Fork Creation) - DONE, Story 12.2 (Fork Management UI) - DONE

## Acceptance Criteria

1. **Given** a session with at least one fork
   **When** I click "Compare" on a fork entry in the Fork Timeline panel
   **Then** a comparison view opens showing the main timeline alongside the selected fork

2. **Given** the comparison view is active
   **When** displayed
   **Then** it shows:
   - The branch point turn (common starting content) at the top
   - Two side-by-side columns: left for the main timeline (or first selected timeline), right for the fork
   - Column headers identifying each timeline (e.g., "Main Timeline" vs "Diplomacy Attempt")
   - Turns aligned by sequence number for easy comparison

3. **Given** the comparison view
   **When** I scroll through turns after the branch point
   **Then** each turn row shows the corresponding turn from both timelines side by side
   **And** the divergence point (first turn after branch) is visually highlighted

4. **Given** one timeline is significantly longer than the other
   **When** the shorter timeline ends
   **Then** a "[Timeline ends here]" indicator appears in the shorter column
   **And** the longer timeline's remaining turns continue to display

5. **Given** the comparison view is open
   **When** I click any turn row
   **Then** it expands to show the full turn content (content is truncated by default for overview)

6. **Given** the comparison view
   **When** I want to exit
   **Then** I can close it and return to the normal game view
   **And** no game state changes occur (comparison is read-only)

7. **Given** the comparison mode session state
   **When** comparison is active
   **Then** `st.session_state["comparison_mode"]` is True
   **And** `st.session_state["comparison_left"]` and `st.session_state["comparison_right"]` track which timelines are being compared

8. **Given** a fork that was created but has no additional turns
   **When** compared to the main timeline
   **Then** the branch point turn is shown as identical in both columns
   **And** the fork column shows "[No additional turns]"

## Context: What Already Exists (Stories 12.1, 12.2)

### models.py (existing)

- `ForkMetadata` Pydantic model: `fork_id`, `name`, `parent_session_id`, `branch_turn`, `created_at`, `updated_at`, `turn_count`
- `ForkRegistry` Pydantic model: `session_id`, `forks` list, `get_fork()`, `get_forks_at_turn()`, `next_fork_id()`, `add_fork()`
- `GameState` TypedDict with `active_fork_id: str | None` field (None = main timeline)
- `NarrativeMessage` Pydantic model: `agent`, `content`, `timestamp`, `message_type` property
- `parse_log_entry(entry: str) -> NarrativeMessage` for parsing ground_truth_log entries

### persistence.py (existing)

- `load_checkpoint(session_id, turn_number)` -> loads full GameState from main timeline
- `load_fork_checkpoint(session_id, fork_id, turn_number)` -> loads full GameState from fork
- `list_checkpoints(session_id)` -> sorted list of turn numbers in main timeline
- `list_fork_checkpoints(session_id, fork_id)` -> sorted list of turn numbers in fork
- `get_latest_checkpoint(session_id)` -> latest turn number on main timeline
- `get_latest_fork_checkpoint(session_id, fork_id)` -> latest turn number in fork
- `list_forks(session_id)` -> sorted `list[ForkMetadata]`
- `load_fork_registry(session_id)` -> `ForkRegistry | None`
- `get_fork_dir(session_id, fork_id)` -> Path to fork directory

### app.py (existing)

- `render_fork_controls()` -> Fork Timeline expander with create, list, switch, rename, delete controls
- `render_narrative_messages(state)` -> Renders ground_truth_log entries with DM/PC styling
- `parse_log_entry()` / `parse_message_content()` for message parsing
- `escape_html()` utility for safe rendering
- `render_dm_message()` / `render_pc_message()` for styled message rendering
- `get_character_info(state, agent)` -> (name, class) tuple for character lookup

### UX Design Specification (reference)

- Fork Comparison View wireframe: two-column grid layout with branch point header
- CSS classes: `.comparison-container`, `.comparison-column`, `.comparison-header`, `.comparison-turn`, `.comparison-turn-number`, `.comparison-turn-content`, `.comparison-divergence`, `.comparison-ended`, `.comparison-current`
- Accessibility: `role="grid"` with column headers

## What Story 12.3 Changes

This story adds a **read-only fork comparison view** that lets users see how two timelines diverged after a branch point. Specifically:

1. **Comparison data loading functions** in persistence.py: `load_timeline_turns()` and `load_fork_timeline_turns()` that return aligned lists of `(turn_number, log_entries)` for a range of turns starting from a branch point.
2. **Comparison data model** in models.py: `ComparisonTimeline` and `ComparisonData` Pydantic models to hold paired turn data for rendering.
3. **Comparison UI** in app.py: `render_comparison_view()` function that displays a side-by-side two-column layout with turn alignment, divergence highlighting, and expandable turn details.
4. **Compare button** on each fork entry in `render_fork_controls()`: triggers comparison mode.
5. **Session state tracking** for comparison mode: `comparison_mode`, `comparison_left`, `comparison_right` keys in `st.session_state`.
6. **Exit comparison** button to return to normal game view.

## Tasks

### 1. Add Comparison Data Models (models.py)

- [x] 1.1 Add `ComparisonTurn` Pydantic model
  - Fields:
    - `turn_number: int` - Turn number (same for both timelines when aligned)
    - `entries: list[str]` - Log entries for this turn (may be empty if timeline ended)
    - `is_branch_point: bool` - Whether this is the branch point turn (default False)
    - `is_ended: bool` - Whether the timeline has ended at this point (default False)
  - Docstring referencing Story 12.3, FR83

- [x] 1.2 Add `ComparisonTimeline` Pydantic model
  - Fields:
    - `label: str` - Display label (e.g., "Main Timeline" or fork name)
    - `timeline_type: Literal["main", "fork"]` - Which type of timeline
    - `fork_id: str | None` - Fork ID if this is a fork timeline, None for main
    - `turns: list[ComparisonTurn]` - Aligned turns for comparison
    - `total_turns: int` - Total number of turns in this timeline (including pre-branch)
  - Docstring referencing Story 12.3, FR83

- [x] 1.3 Add `ComparisonData` Pydantic model
  - Fields:
    - `session_id: str` - Session ID
    - `branch_turn: int` - Turn number where timelines diverge
    - `left: ComparisonTimeline` - Left column data (typically main timeline)
    - `right: ComparisonTimeline` - Right column data (typically the fork)
  - Docstring referencing Story 12.3, FR83

- [x] 1.4 Add `ComparisonTurn`, `ComparisonTimeline`, `ComparisonData` to `__all__` exports in models.py

### 2. Add Comparison Data Loading (persistence.py)

- [x] 2.1 Add `load_timeline_log_at_turn(session_id: str, turn_number: int) -> list[str] | None` function
  - Loads a checkpoint from the main timeline and returns its `ground_truth_log`
  - Returns None if checkpoint doesn't exist or is invalid
  - Uses `load_checkpoint()` internally

- [x] 2.2 Add `load_fork_log_at_turn(session_id: str, fork_id: str, turn_number: int) -> list[str] | None` function
  - Loads a checkpoint from a fork and returns its `ground_truth_log`
  - Returns None if checkpoint doesn't exist or is invalid
  - Uses `load_fork_checkpoint()` internally

- [x] 2.3 Add `build_comparison_data(session_id: str, fork_id: str) -> ComparisonData | None` function
  - Core comparison data loading logic:
    1. Load fork registry to get `ForkMetadata` (specifically `branch_turn`)
    2. Load the branch point checkpoint from the main timeline to get the shared log
    3. For the main timeline: load the latest checkpoint, extract log entries from `branch_turn` onward
    4. For the fork: load the latest fork checkpoint, extract log entries from `branch_turn` onward
    5. Build aligned `ComparisonTurn` lists:
       - First turn is the branch point (shared content, `is_branch_point=True`)
       - Subsequent turns pair entries by position (index after branch point)
       - If one timeline has more turns, the shorter one's entries are empty with `is_ended=True`
    6. Assemble `ComparisonData` with left (main) and right (fork) timelines
  - Returns None if fork not found, no checkpoints, or data loading fails
  - Strategy for extracting per-turn entries from ground_truth_log:
    - The log at turn N contains all entries from turns 1..N
    - Entries for "turn X" are the entries added between checkpoint X-1 and checkpoint X
    - For the branch point: entries are log[0..branch_turn_log_count]
    - For subsequent turns: diff consecutive checkpoints' log lengths
    - Optimization: if only latest checkpoint available, use log entry count differences

- [x] 2.4 Add new functions to `__all__` exports in persistence.py:
  - `load_timeline_log_at_turn`, `load_fork_log_at_turn`, `build_comparison_data`

### 3. Add Comparison UI (app.py)

- [x] 3.1 Add `render_comparison_view()` function
  - Check `st.session_state.get("comparison_mode", False)` to determine if comparison is active
  - Load comparison data via `build_comparison_data()`
  - Render two-column layout using `st.columns([1, 1])`
  - Structure:
    - Header row: "Compare Timelines" title with close button
    - Timeline labels: left column header, right column header
    - Branch point turn (highlighted with `.comparison-divergence` style)
    - Subsequent aligned turns with truncated content (first 200 chars)
    - Expandable turn detail on click (using `st.expander`)
    - "[Timeline ends here]" indicator for the shorter timeline
  - Uses `parse_log_entry()` for rendering entries with agent attribution
  - Close button sets `st.session_state["comparison_mode"] = False` and triggers `st.rerun()`

- [x] 3.2 Add comparison CSS classes to `styles/theme.css`
  - `.comparison-container`: grid layout, two columns
  - `.comparison-header`: Inter font, 14px, font-weight 600
  - `.comparison-turn-number`: JetBrains Mono, 11px, secondary text color
  - `.comparison-turn-content`: Lora font, 14px, 1.5 line height
  - `.comparison-divergence`: amber tint background with left border (branch point highlight)
  - `.comparison-ended`: centered italic text, error color
  - `.comparison-current`: green tint background for current turn indicator
  - Follow existing UX specification CSS classes

- [x] 3.3 Add "Compare" button to each fork entry in `render_fork_controls()`
  - Button label: "Compare"
  - Positioned alongside existing "Switch" button in the fork list
  - Clicking sets comparison mode session state keys:
    - `st.session_state["comparison_mode"] = True`
    - `st.session_state["comparison_left"] = {"type": "main", "fork_id": None}`
    - `st.session_state["comparison_right"] = {"type": "fork", "fork_id": fork.fork_id}`
  - Calls `st.rerun()` to switch to comparison view

- [x] 3.4 Integrate `render_comparison_view()` into main app layout
  - In the main rendering flow (where `render_narrative_messages` is called), check if comparison mode is active
  - If `st.session_state.get("comparison_mode")` is True, render comparison view instead of normal narrative
  - Comparison view replaces the narrative area (not a popup/modal) for full-width display
  - Normal narrative rendering resumes when comparison mode is exited

- [x] 3.5 Add comparison mode session state initialization to `initialize_session_state()`
  - `comparison_mode: bool = False`
  - `comparison_left: dict | None = None` (timeline spec: `{"type": "main"|"fork", "fork_id": str|None}`)
  - `comparison_right: dict | None = None`

### 4. Turn Extraction Strategy (persistence.py helper)

- [x] 4.1 Add `extract_turns_from_logs(logs_by_checkpoint: dict[int, list[str]], start_turn: int) -> list[ComparisonTurn]` helper function
  - Takes a dict mapping turn_number -> ground_truth_log at that turn
  - Computes per-turn entries by diffing consecutive logs:
    - For turn N: entries = log_at_N[len(log_at_(N-1)):] (new entries added at turn N)
  - Returns a list of `ComparisonTurn` objects starting from `start_turn`
  - Marks first turn as `is_branch_point=True`
  - This helper is used by `build_comparison_data()` for both main and fork timelines

- [x] 4.2 Add simplified fallback: `extract_turns_from_single_log(log: list[str], branch_log_count: int, total_turns: int) -> list[ComparisonTurn]`
  - When only the latest checkpoint is available (most common case)
  - Divides remaining log entries (after branch point) evenly across turns
  - Simpler but less accurate: treats each log entry as one turn's content
  - Used as fallback when intermediate checkpoints are not available

### 5. Tests

- [x] 5.1 Test `ComparisonTurn` model validation
  - Valid construction with required fields
  - Default values: `is_branch_point=False`, `is_ended=False`
  - Empty entries list allowed (for ended timelines)

- [x] 5.2 Test `ComparisonTimeline` model validation
  - Valid construction with main timeline (fork_id=None)
  - Valid construction with fork timeline (fork_id="001")
  - Label and timeline_type fields populated correctly

- [x] 5.3 Test `ComparisonData` model validation
  - Valid construction with both left and right timelines
  - branch_turn matches fork metadata

- [x] 5.4 Test `load_timeline_log_at_turn()` function
  - Returns ground_truth_log from checkpoint at specified turn
  - Returns None for non-existent checkpoint
  - Returns None for invalid checkpoint data

- [x] 5.5 Test `load_fork_log_at_turn()` function
  - Returns ground_truth_log from fork checkpoint at specified turn
  - Returns None for non-existent fork checkpoint
  - Returns None for invalid fork_id

- [x] 5.6 Test `build_comparison_data()` function
  - End-to-end: create session, save checkpoints, create fork, save fork checkpoints, build comparison
  - Branch point turn appears in both timelines with same content
  - Post-branch turns are correctly aligned by index
  - Shorter timeline shows `is_ended=True` on remaining turns
  - Returns None for non-existent fork
  - Returns None for session with no checkpoints
  - Fork with no additional turns: only branch point shown, fork side shows ended

- [x] 5.7 Test `extract_turns_from_logs()` helper
  - Correctly diffs consecutive log snapshots to get per-turn entries
  - First turn marked as branch point
  - Empty dict returns empty list

- [x] 5.8 Test `extract_turns_from_single_log()` fallback
  - Distributes entries across turns correctly
  - Handles case where log has no entries after branch point

- [x] 5.9 Test comparison session state management
  - Setting `comparison_mode = True` with valid left/right specs
  - Clearing comparison mode resets to False
  - Left/right specs track timeline type and fork_id correctly

- [x] 5.10 Test comparison with multiple forks from same branch point
  - Can compare main vs fork_001
  - Can compare main vs fork_002
  - Each comparison shows correct fork's data

## Dependencies

- **Story 12.1** (done): Provides `ForkMetadata`, `ForkRegistry`, `create_fork()`, `list_forks()`, fork directory structure
- **Story 12.2** (done): Provides `load_fork_checkpoint()`, `list_fork_checkpoints()`, `get_latest_fork_checkpoint()`, fork management UI, `render_fork_controls()` pattern
- **Story 4.1** (done): Provides checkpoint save/load, serialization patterns
- **Story 2.3** (done): Provides `render_dm_message()`, `render_pc_message()`, narrative message display patterns

## Dev Notes

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `models.py` | Modify | Add `ComparisonTurn`, `ComparisonTimeline`, `ComparisonData` models, update `__all__` |
| `persistence.py` | Modify | Add `load_timeline_log_at_turn()`, `load_fork_log_at_turn()`, `build_comparison_data()`, `extract_turns_from_logs()`, `extract_turns_from_single_log()`, update `__all__` |
| `app.py` | Modify | Add `render_comparison_view()`, "Compare" button in `render_fork_controls()`, comparison mode integration in main render flow, session state initialization |
| `styles/theme.css` | Modify | Add comparison CSS classes (`.comparison-container`, `.comparison-header`, etc.) |
| `tests/test_story_12_3_fork_comparison_view.py` | Create | Unit and integration tests for comparison data loading, models, and session state |

### Code Patterns with Examples

#### 1. ComparisonTurn Model (models.py, follow existing Pydantic patterns)

```python
class ComparisonTurn(BaseModel):
    """A single turn's content for comparison alignment.

    Represents one row in the comparison grid, containing the log
    entries for a specific turn from one timeline.

    Story 12.3: Fork Comparison View.
    FR83: Compare forks side-by-side.

    Attributes:
        turn_number: Turn number (same for both timelines when aligned).
        entries: Log entries added at this turn (may be empty if timeline ended).
        is_branch_point: Whether this is the shared branch point turn.
        is_ended: Whether the timeline has no more turns after this point.
    """

    turn_number: int = Field(..., ge=0, description="Turn number for alignment")
    entries: list[str] = Field(
        default_factory=list, description="Log entries at this turn"
    )
    is_branch_point: bool = Field(
        default=False, description="Whether this is the branch point"
    )
    is_ended: bool = Field(
        default=False, description="Whether timeline ended here"
    )
```

#### 2. ComparisonTimeline Model (models.py)

```python
class ComparisonTimeline(BaseModel):
    """One side of a fork comparison (main or fork timeline).

    Story 12.3: Fork Comparison View.
    FR83: Compare forks side-by-side.

    Attributes:
        label: Display label (e.g., "Main Timeline" or fork name).
        timeline_type: Whether this is the main timeline or a fork.
        fork_id: Fork ID if this is a fork, None for main.
        turns: Aligned turns for comparison rendering.
        total_turns: Total turns in this timeline (including pre-branch).
    """

    label: str = Field(..., min_length=1, description="Display label")
    timeline_type: Literal["main", "fork"] = Field(
        ..., description="Timeline type"
    )
    fork_id: str | None = Field(
        default=None, description="Fork ID (None for main)"
    )
    turns: list[ComparisonTurn] = Field(
        default_factory=list, description="Aligned turns"
    )
    total_turns: int = Field(
        default=0, ge=0, description="Total turns in timeline"
    )
```

#### 3. ComparisonData Model (models.py)

```python
class ComparisonData(BaseModel):
    """Complete comparison data for two timelines.

    Story 12.3: Fork Comparison View.
    FR83: Compare forks side-by-side.

    Attributes:
        session_id: Session ID.
        branch_turn: Turn number where timelines diverge.
        left: Left column timeline data.
        right: Right column timeline data.
    """

    session_id: str = Field(..., min_length=1, description="Session ID")
    branch_turn: int = Field(..., ge=0, description="Branch point turn number")
    left: ComparisonTimeline = Field(..., description="Left column timeline")
    right: ComparisonTimeline = Field(..., description="Right column timeline")
```

#### 4. build_comparison_data (persistence.py)

```python
def build_comparison_data(
    session_id: str, fork_id: str
) -> ComparisonData | None:
    """Build comparison data between main timeline and a fork.

    Story 12.3: Fork Comparison View.
    FR83: Compare forks side-by-side.

    Loads checkpoint data from both timelines, extracts per-turn entries
    starting from the branch point, and aligns them for rendering.

    Args:
        session_id: Session ID string.
        fork_id: Fork ID to compare against main timeline.

    Returns:
        ComparisonData with aligned turns, or None if data cannot be loaded.
    """
    _validate_session_id(session_id)
    _validate_fork_id(fork_id)

    # Load fork metadata for branch_turn
    registry = load_fork_registry(session_id)
    if registry is None:
        return None

    fork_meta = registry.get_fork(fork_id)
    if fork_meta is None:
        return None

    branch_turn = fork_meta.branch_turn

    # Load main timeline's latest checkpoint for the log
    main_latest = get_latest_checkpoint(session_id)
    if main_latest is None:
        return None
    main_state = load_checkpoint(session_id, main_latest)
    if main_state is None:
        return None
    main_log = main_state.get("ground_truth_log", [])

    # Load branch point checkpoint for shared log baseline
    branch_state = load_checkpoint(session_id, branch_turn)
    branch_log_count = 0
    if branch_state is not None:
        branch_log_count = len(branch_state.get("ground_truth_log", []))

    # Load fork's latest checkpoint for the log
    fork_latest = get_latest_fork_checkpoint(session_id, fork_id)
    if fork_latest is None:
        # Fork exists but has no checkpoints (shouldn't happen, but handle gracefully)
        return None
    fork_state = load_fork_checkpoint(session_id, fork_id, fork_latest)
    if fork_state is None:
        return None
    fork_log = fork_state.get("ground_truth_log", [])

    # Extract branch point entries (shared between both timelines)
    branch_entries = main_log[:branch_log_count]

    # Extract post-branch entries for main timeline
    main_post_branch = main_log[branch_log_count:]

    # Extract post-branch entries for fork
    fork_post_branch = fork_log[branch_log_count:]

    # Build aligned turn lists
    # Branch point turn
    branch_point_turn = ComparisonTurn(
        turn_number=branch_turn,
        entries=branch_entries,
        is_branch_point=True,
    )

    # Determine max post-branch length for alignment
    max_post_turns = max(len(main_post_branch), len(fork_post_branch))

    main_turns: list[ComparisonTurn] = [branch_point_turn]
    fork_turns: list[ComparisonTurn] = [
        ComparisonTurn(
            turn_number=branch_turn,
            entries=branch_entries,
            is_branch_point=True,
        )
    ]

    # Align subsequent turns by index
    for i in range(max_post_turns):
        turn_num = branch_turn + i + 1

        # Main timeline entry
        if i < len(main_post_branch):
            main_turns.append(
                ComparisonTurn(
                    turn_number=turn_num,
                    entries=[main_post_branch[i]],
                )
            )
        else:
            main_turns.append(
                ComparisonTurn(
                    turn_number=turn_num,
                    entries=[],
                    is_ended=True,
                )
            )

        # Fork entry
        if i < len(fork_post_branch):
            fork_turns.append(
                ComparisonTurn(
                    turn_number=turn_num,
                    entries=[fork_post_branch[i]],
                )
            )
        else:
            fork_turns.append(
                ComparisonTurn(
                    turn_number=turn_num,
                    entries=[],
                    is_ended=True,
                )
            )

    # Build comparison timelines
    left = ComparisonTimeline(
        label="Main Timeline",
        timeline_type="main",
        fork_id=None,
        turns=main_turns,
        total_turns=len(main_log),
    )

    right = ComparisonTimeline(
        label=fork_meta.name,
        timeline_type="fork",
        fork_id=fork_id,
        turns=fork_turns,
        total_turns=len(fork_log),
    )

    return ComparisonData(
        session_id=session_id,
        branch_turn=branch_turn,
        left=left,
        right=right,
    )
```

#### 5. render_comparison_view (app.py)

```python
def render_comparison_view() -> None:
    """Render side-by-side fork comparison view.

    Story 12.3: Fork Comparison View (FR83).
    Replaces the normal narrative area when comparison mode is active.
    """
    if not st.session_state.get("comparison_mode"):
        return

    comparison_right = st.session_state.get("comparison_right", {})
    fork_id = comparison_right.get("fork_id")

    if not fork_id:
        st.error("No fork selected for comparison")
        st.session_state["comparison_mode"] = False
        return

    game: GameState = st.session_state.get("game", {})
    session_id = game.get("session_id", "001")

    # Load comparison data
    data = build_comparison_data(session_id, fork_id)
    if data is None:
        st.error("Could not load comparison data")
        st.session_state["comparison_mode"] = False
        return

    # Header with close button
    header_col, close_col = st.columns([5, 1])
    with header_col:
        st.markdown("### Compare Timelines")
        st.caption(
            f"**{escape_html(data.left.label)}** vs "
            f"**{escape_html(data.right.label)}** "
            f"(branched at turn {data.branch_turn})"
        )
    with close_col:
        if st.button("Close", key="close_comparison"):
            st.session_state["comparison_mode"] = False
            st.rerun()

    st.markdown("---")

    # Column headers
    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown(f"**{escape_html(data.left.label)}**")
    with right_col:
        st.markdown(f"**{escape_html(data.right.label)}**")

    # Render aligned turns
    max_turns = max(len(data.left.turns), len(data.right.turns))
    for i in range(max_turns):
        left_turn = data.left.turns[i] if i < len(data.left.turns) else None
        right_turn = data.right.turns[i] if i < len(data.right.turns) else None

        left_col, right_col = st.columns(2)

        with left_col:
            _render_comparison_turn(left_turn, data.left.label, i)
        with right_col:
            _render_comparison_turn(right_turn, data.right.label, i)


def _render_comparison_turn(
    turn: ComparisonTurn | None,
    timeline_label: str,
    index: int,
) -> None:
    """Render a single turn in the comparison grid.

    Args:
        turn: The ComparisonTurn to render, or None if no data.
        timeline_label: Label for this timeline (for unique keys).
        index: Index for generating unique Streamlit keys.
    """
    if turn is None:
        return

    # Sanitize label for use in Streamlit keys
    safe_label = timeline_label.replace(" ", "_").lower()[:20]

    if turn.is_branch_point:
        st.markdown(
            f'<div class="comparison-divergence">'
            f'<span class="comparison-turn-number">'
            f"Turn {turn.turn_number} (Branch Point)"
            f"</span></div>",
            unsafe_allow_html=True,
        )
    elif turn.is_ended:
        st.markdown(
            '<div class="comparison-ended">[Timeline ends here]</div>',
            unsafe_allow_html=True,
        )
        return
    else:
        st.markdown(
            f'<span class="comparison-turn-number">'
            f"Turn {turn.turn_number}</span>",
            unsafe_allow_html=True,
        )

    # Render entries (truncated for overview)
    if turn.entries:
        with st.expander(
            _truncate_entry(turn.entries[0], 150),
            expanded=turn.is_branch_point,
        ):
            for entry in turn.entries:
                st.markdown(escape_html(entry))
    elif not turn.is_ended:
        st.caption("[No entries]")
```

#### 6. Compare button in render_fork_controls (app.py)

```python
# Inside the fork list display loop, alongside the existing "Switch" button:
with col2:
    if not is_active:
        if st.button(
            "Switch",
            key=f"switch_fork_{fork.fork_id}",
            disabled=is_generating,
        ):
            handle_switch_to_fork(session_id, fork.fork_id)
            st.rerun()
    # Compare button (Story 12.3)
    if st.button(
        "Compare",
        key=f"compare_fork_{fork.fork_id}",
        disabled=is_generating,
    ):
        st.session_state["comparison_mode"] = True
        st.session_state["comparison_left"] = {
            "type": "main",
            "fork_id": None,
        }
        st.session_state["comparison_right"] = {
            "type": "fork",
            "fork_id": fork.fork_id,
        }
        st.rerun()
```

#### 7. Comparison CSS (styles/theme.css)

```css
/* Fork Comparison View (Story 12.3) */
.comparison-divergence {
    background: rgba(232, 168, 73, 0.1);
    border-left: 2px solid var(--accent-warm);
    padding-left: var(--space-sm);
    padding: var(--space-sm);
    margin-bottom: var(--space-md);
    border-radius: 4px;
}

.comparison-turn-number {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--text-secondary);
    margin-bottom: var(--space-xs);
}

.comparison-ended {
    text-align: center;
    padding: var(--space-lg);
    color: var(--color-error);
    font-family: Inter, sans-serif;
    font-style: italic;
}

.comparison-current {
    text-align: center;
    padding: var(--space-sm);
    background: rgba(107, 142, 107, 0.15);
    border-radius: 4px;
    color: var(--color-success);
    font-family: Inter, sans-serif;
    font-size: 12px;
}
```

### Key Design Decisions

1. **Read-only comparison:** The comparison view is strictly read-only. It does not modify any game state, checkpoints, or fork data. It simply loads data from existing checkpoints and displays it. This keeps the scope focused and avoids complex state management.

2. **Main vs fork comparison (not fork vs fork):** For this story, comparison is always between the main timeline and a single fork. Fork-vs-fork comparison could be added later, but main-vs-fork covers the primary use case ("what happened differently?"). The data model supports fork-vs-fork via the `timeline_type` and `fork_id` fields for future extensibility.

3. **Comparison replaces the narrative area:** Rather than using a modal or popup (which would be cramped for side-by-side content), the comparison view replaces the main narrative panel. This gives maximum screen width for the two-column layout. The user clicks "Close" to return to normal view.

4. **Per-entry alignment (not per-turn-cycle):** Each log entry (one DM narration or one PC response) is treated as one unit for alignment. This is simpler than trying to align full turn cycles (DM + all PCs) and maps directly to `ground_truth_log` entries. Post-branch entries are aligned by their index in the log (entry 1 after branch vs entry 1 after branch).

5. **Truncated entries with expandable detail:** By default, entries are truncated to ~150 characters for a high-level overview. Users can click to expand and see the full text. This prevents the comparison from being overwhelmed by long DM narrations.

6. **Branch point checkpoint as baseline:** The branch point turn's log (from the main timeline checkpoint at that turn) establishes the shared baseline. Post-branch entries are computed by subtracting the branch point log count from the latest checkpoint's log.

7. **Session state for comparison mode:** Using `st.session_state` keys (`comparison_mode`, `comparison_left`, `comparison_right`) follows the existing pattern for mode tracking (like `human_active`, `is_autopilot_running`). This is checked early in the render flow to swap out the narrative panel.

8. **No LLM calls:** Like fork creation and management, comparison is purely a data display operation. No LLM involvement needed.

9. **Graceful handling of edge cases:** Forks with no additional turns (only branch point) show the branch point as identical and indicate no further content. Missing checkpoints or data errors result in "Could not load comparison data" rather than crashes.

10. **CSS follows UX specification:** The CSS classes match the UX design specification exactly (`.comparison-divergence`, `.comparison-ended`, `.comparison-current`, etc.) for consistency with the design system.

### Test Strategy

**Test file:** `tests/test_story_12_3_fork_comparison_view.py`

**Fixture pattern (follow existing test_persistence.py):**

```python
import pytest
from pathlib import Path
from collections.abc import Generator
from unittest.mock import patch

from models import (
    ComparisonData,
    ComparisonTimeline,
    ComparisonTurn,
    ForkMetadata,
    ForkRegistry,
    GameState,
    create_initial_game_state,
)
from persistence import (
    CAMPAIGNS_DIR,
    build_comparison_data,
    create_fork,
    load_fork_log_at_turn,
    load_timeline_log_at_turn,
    save_checkpoint,
    save_fork_checkpoint,
)


@pytest.fixture
def temp_campaigns_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary campaigns directory for testing."""
    temp_campaigns = tmp_path / "campaigns"
    temp_campaigns.mkdir()
    with patch("persistence.CAMPAIGNS_DIR", temp_campaigns):
        yield temp_campaigns


@pytest.fixture
def sample_game_state() -> GameState:
    """Create a sample GameState for testing."""
    return create_initial_game_state()


@pytest.fixture
def session_with_forked_content(
    temp_campaigns_dir: Path, sample_game_state: GameState
) -> tuple[str, str]:
    """Create a session with divergent content in main and fork.

    Returns (session_id, fork_id).
    Sets up:
    - Main timeline: 3 turns with log entries
    - Fork: branched at turn 1, then 2 additional turns with different content
    """
    session_id = "001"

    # Turn 1: shared content (branch point)
    state = {**sample_game_state}
    state["ground_truth_log"] = [
        "[dm] The dragon descends from the mountain peak.",
    ]
    save_checkpoint(state, session_id, 1)

    # Create fork from turn 1
    fork_meta = create_fork(
        state=state,
        session_id=session_id,
        fork_name="Diplomacy Attempt",
        turn_number=1,
    )
    fork_id = fork_meta.fork_id

    # Main timeline: turn 2 (fight path)
    state["ground_truth_log"].append(
        "[fighter] Thorin charges forward, sword raised!"
    )
    save_checkpoint(state, session_id, 2)

    # Main timeline: turn 3
    state["ground_truth_log"].append(
        "[dm] The dragon's breath engulfs the fighter."
    )
    save_checkpoint(state, session_id, 3)

    # Fork: turn 2 (diplomacy path)
    fork_state = {**sample_game_state}
    fork_state["ground_truth_log"] = [
        "[dm] The dragon descends from the mountain peak.",
        "[cleric] Aldric steps forward, hands raised in peace.",
    ]
    fork_state["active_fork_id"] = fork_id
    save_fork_checkpoint(fork_state, session_id, fork_id, 2)

    # Fork: turn 3
    fork_state["ground_truth_log"].append(
        "[dm] The dragon pauses, curious about this bold mortal."
    )
    save_fork_checkpoint(fork_state, session_id, fork_id, 3)

    # Fork: turn 4 (fork is longer than main)
    fork_state["ground_truth_log"].append(
        '[dm] "Speak, tiny one..." the dragon rumbles.'
    )
    save_fork_checkpoint(fork_state, session_id, fork_id, 4)

    return session_id, fork_id
```

**Unit Tests:**

- `ComparisonTurn`: valid construction, defaults, empty entries
- `ComparisonTimeline`: main vs fork types, label validation
- `ComparisonData`: construction with both timelines, branch_turn
- `load_timeline_log_at_turn()`: returns log, None for missing checkpoint
- `load_fork_log_at_turn()`: returns fork log, None for missing
- `extract_turns_from_logs()`: correct diffs, branch point marking
- `extract_turns_from_single_log()`: fallback distribution

**Integration Tests:**

- `build_comparison_data()` end-to-end with fixture `session_with_forked_content`
- Verify branch point appears identically in both timelines
- Verify post-branch entries are different (fight vs diplomacy)
- Verify shorter timeline shows `is_ended=True`
- Verify longer timeline continues past shorter one
- Returns None for non-existent fork
- Returns None for session with no checkpoints
- Fork with no additional turns beyond branch point

**Edge Cases:**

- Fork created at turn 0 (empty game state)
- Fork with same content as main (identical logs)
- Very long logs (100+ entries) - performance sanity check
- Fork whose checkpoints were partially deleted (missing intermediate)

### Important Constraints

- **Scope boundary:** This story covers comparison VIEW only. It does not support editing, merging, or promoting forks (Story 12.4). The comparison is read-only.
- **No fork-vs-fork comparison yet:** Only main-vs-fork is implemented. The data model supports fork-vs-fork for future extension but the UI only offers comparing against main.
- **No LLM calls:** Comparison is purely a data loading and display operation.
- **No new dependencies:** Uses only existing imports (Streamlit, Path, json, Pydantic).
- **Backward compatibility:** Sessions without forks are unaffected. The comparison button only appears when forks exist.
- **Performance:** Loading two full checkpoints (latest main + latest fork) is the main cost. For very long sessions, this may be up to ~200KB per checkpoint. This is acceptable for a user-triggered action (not automatic).
- **Streamlit columns limitation:** Streamlit's `st.columns` does not support truly synchronized scrolling between columns. Each column scrolls independently as part of the page. This is acceptable given Streamlit's constraints.
- **CSS variables:** Comparison CSS uses existing CSS custom properties (variables) from `styles/theme.css` for colors and spacing, ensuring consistency with the campfire theme.
