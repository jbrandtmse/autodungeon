# Story 12-4: Fork Resolution

## Story

As a **user**,
I want **to promote a fork to become the main timeline or clean up forks I no longer need**,
So that **I can choose my canonical timeline**.

## Status

**Status:** review
**Epic:** 12 - Fork Gameplay
**Created:** 2026-02-07
**FRs Covered:** FR84 (user can merge or abandon forks)
**Predecessors:** Story 12.1 (Fork Creation) - DONE, Story 12.2 (Fork Management UI) - DONE, Story 12.3 (Fork Comparison View) - DONE

## Acceptance Criteria

1. **Given** I've explored a fork and decide it's the "true" path
   **When** I click "Make Primary" on that fork
   **Then** a confirmation dialog explains what will happen:
   - "The fork's content will replace the main timeline from turn [branch_turn] onward."
   - "The old main timeline's post-branch content will be preserved as a new fork."

2. **Given** I confirm the promotion
   **When** the promotion completes
   **Then** the fork's checkpoints are copied into the main session directory
   **And** the old main timeline's post-branch checkpoints are moved into a new fork (named "Pre-[fork_name] main")
   **And** the promoted fork entry is removed from the registry
   **And** `active_fork_id` is cleared to `None` (user is now on the main timeline)

3. **Given** the promotion is complete
   **When** the UI refreshes
   **Then** the user is on the main timeline with the fork's content
   **And** a toast message confirms: "Fork '[name]' promoted to main timeline"
   **And** the old main's post-branch content is available as a new fork for reference

4. **Given** the "Collapse to Single Timeline" action
   **When** I click it
   **Then** a confirmation asks: "Delete ALL forks and keep only the main timeline? This cannot be undone."
   **And** on confirm, all fork directories and the fork registry are removed
   **And** the main timeline checkpoints are untouched

5. **Given** a session without forks
   **When** using the application
   **Then** no fork-related UI or behavior changes occur (backward compatibility)

6. **Given** promotion is in progress
   **When** autopilot or LLM generation is running
   **Then** the "Make Primary" button is disabled
   **And** promotion cannot be triggered during active gameplay

7. **Given** I promote a fork while currently playing in that fork
   **When** the promotion completes
   **Then** `active_fork_id` is cleared (I'm now on the newly-promoted main timeline)
   **And** the game state continues seamlessly

8. **Given** I promote a fork while on the main timeline
   **When** the promotion completes
   **Then** the game state reloads to show the promoted fork's latest content
   **And** I am on the main timeline

## Context: What Already Exists (Stories 12.1, 12.2, 12.3)

### models.py (existing)

- `ForkMetadata` Pydantic model: `fork_id`, `name`, `parent_session_id`, `branch_turn`, `created_at`, `updated_at`, `turn_count`
- `ForkRegistry` Pydantic model: `session_id`, `forks` list, `get_fork()`, `get_forks_at_turn()`, `next_fork_id()`, `add_fork()`
- `GameState` TypedDict with `active_fork_id: str | None` field (None = main timeline)

### persistence.py (existing)

- `create_fork(state, session_id, fork_name, turn_number)` -> creates fork directory, copies checkpoint, saves registry
- `get_fork_dir(session_id, fork_id)` -> `campaigns/session_XXX/forks/fork_XXX/`
- `ensure_fork_dir(session_id, fork_id)` -> creates directory tree
- `list_forks(session_id)` -> sorted `list[ForkMetadata]`
- `save_fork_registry(session_id, registry)` / `load_fork_registry(session_id)` -> YAML round-trip
- `save_fork_checkpoint(state, session_id, fork_id, turn_number)` -> saves to fork directory
- `load_fork_checkpoint(session_id, fork_id, turn_number)` -> loads from fork directory
- `list_fork_checkpoints(session_id, fork_id)` -> sorted turn numbers in fork
- `get_latest_fork_checkpoint(session_id, fork_id)` -> latest turn in fork
- `rename_fork(session_id, fork_id, new_name)` -> updates name in registry
- `delete_fork(session_id, fork_id, active_fork_id)` -> removes fork directory and registry entry
- `list_checkpoints(session_id)` -> sorted turn numbers on main timeline
- `get_latest_checkpoint(session_id)` -> latest turn on main timeline
- `save_checkpoint(state, session_id, turn_number)` -> saves to main session directory
- `load_checkpoint(session_id, turn_number)` -> loads from main session directory
- `get_session_dir(session_id)` -> `campaigns/session_XXX/`
- `_validate_session_id()`, `_validate_fork_id()`, `_validate_turn_number()` -> input validation

### app.py (existing)

- `render_fork_controls()` -> Fork Timeline expander with create, list, switch, compare, rename, delete controls
- "Make Primary" button exists as placeholder (lines 7322-7330):
  ```python
  # Make Primary (placeholder for Story 12.4)
  if st.button("Make Primary", key=f"promote_fork_{fork.fork_id}"):
      st.info("Promote to main timeline (coming in Story 12.4)")
  ```
- `handle_switch_to_fork(session_id, fork_id)` -> loads fork state, sets `active_fork_id`
- `handle_return_to_main(session_id)` -> saves fork, loads main state, clears `active_fork_id`
- `escape_html()` utility for safe rendering

### graph.py (existing)

- `run_single_round()` routes checkpoint saves via `active_fork_id`:
  ```python
  active_fork_id = result.get("active_fork_id")
  if active_fork_id is not None:
      save_fork_checkpoint(result, session_id, active_fork_id, turn_number)
  else:
      save_checkpoint(result, session_id, turn_number)
  ```
- `human_intervention_node()` also routes saves fork-aware (lines 255-261)

### Directory Structure (from Stories 12.1, 12.2)

```
campaigns/session_001/
  turn_001.json          <-- shared pre-branch checkpoints
  turn_002.json
  turn_003.json          <-- branch point
  turn_004.json          <-- main timeline post-branch
  turn_005.json          <-- main timeline post-branch
  config.yaml
  forks.yaml             <-- fork registry
  forks/
    fork_001/            <-- fork with alternate content
      turn_003.json      <-- copy of branch point
      turn_004.json      <-- fork post-branch content
      turn_005.json      <-- fork post-branch content
      turn_006.json      <-- fork may be longer
```

## What Story 12.4 Changes

This story implements the **fork resolution** workflow -- the ability to promote a fork to become the main timeline, and to clean up forks. Specifically:

1. **`promote_fork()` function** in persistence.py: Core logic that swaps a fork's post-branch content with the main timeline's post-branch content. The old main's post-branch checkpoints are archived into a new fork, then the promoted fork's checkpoints overwrite the main timeline.
2. **`collapse_all_forks()` function** in persistence.py: Removes all fork directories and the fork registry, keeping only the main timeline.
3. **`handle_promote_fork()` handler** in app.py: UI handler that shows a confirmation, calls `promote_fork()`, updates session state, and refreshes the UI.
4. **Replace the "Make Primary" placeholder** in `render_fork_controls()`: Connects the existing button to the new promotion handler with a confirmation dialog.
5. **"Collapse to Single Timeline" button** in `render_fork_controls()`: Below the fork list, offers a way to delete all forks at once.

### Promotion Algorithm

The `promote_fork()` function performs these steps atomically:

1. Load fork registry to get `ForkMetadata` (specifically `branch_turn`).
2. Identify main timeline checkpoints after `branch_turn` (these will be archived).
3. Create a new "archive" fork from the main's post-branch checkpoints (named "Pre-[fork_name] main").
4. Delete the main timeline's post-branch checkpoint files (turn > branch_turn).
5. Copy the promoted fork's post-branch checkpoint files into the main session directory.
6. Remove the promoted fork from the registry (and its directory).
7. Save the updated registry.
8. Return the latest checkpoint turn number on the new main timeline.

After promotion:
```
campaigns/session_001/
  turn_001.json          <-- unchanged (pre-branch)
  turn_002.json          <-- unchanged (pre-branch)
  turn_003.json          <-- unchanged (branch point)
  turn_004.json          <-- now from fork_001 (promoted)
  turn_005.json          <-- now from fork_001 (promoted)
  turn_006.json          <-- now from fork_001 (promoted, fork was longer)
  config.yaml
  forks.yaml             <-- updated: fork_001 removed, archive fork added
  forks/
    fork_002/            <-- archive of old main post-branch content
      turn_004.json      <-- old main's turn_004 (archived)
      turn_005.json      <-- old main's turn_005 (archived)
```

## Tasks

### 1. Add promote_fork() Function (persistence.py)

- [x] 1.1 Add `promote_fork(session_id: str, fork_id: str) -> int` function
  - Core promotion logic:
    1. Validate session_id and fork_id
    2. Load fork registry, get `ForkMetadata` for fork_id (raise ValueError if not found)
    3. Get `branch_turn` from fork metadata
    4. List main timeline checkpoints after `branch_turn`: `[t for t in list_checkpoints(session_id) if t > branch_turn]`
    5. If main has post-branch checkpoints, archive them:
       a. Create a new fork via the registry (name: `"Pre-{fork_name} main"`, branch_turn same)
       b. Move (copy + delete) each post-branch main checkpoint into the archive fork directory
       c. Update archive fork's `turn_count` based on moved files
    6. List fork checkpoints after `branch_turn`: `[t for t in list_fork_checkpoints(session_id, fork_id) if t > branch_turn]`
    7. Copy each post-branch fork checkpoint into the main session directory (overwrite if exists)
    8. Remove the promoted fork from the registry
    9. Delete the promoted fork's directory (`shutil.rmtree`)
    10. Save the updated registry
    11. Return the latest turn number on the new main timeline
  - Raises ValueError if fork_id not found in registry
  - Raises ValueError if fork has no checkpoints beyond branch point
  - Uses atomic write pattern for checkpoint copies
  - Preserves all pre-branch checkpoints on the main timeline

- [x] 1.2 Add `collapse_all_forks(session_id: str) -> int` function
  - Removes all fork directories and the fork registry file
  - Returns the number of forks deleted
  - Steps:
    1. Load fork registry (return 0 if None)
    2. Count forks
    3. For each fork, remove its directory (`shutil.rmtree`, with `ignore_errors=True`)
    4. Remove the `forks/` parent directory if empty
    5. Delete the `forks.yaml` file
    6. Return the number of forks removed
  - Does not modify main timeline checkpoints
  - Safe to call when no forks exist (returns 0)

- [x] 1.3 Add `promote_fork`, `collapse_all_forks` to `__all__` exports in persistence.py

### 2. Add Promotion UI Handler (app.py)

- [x] 2.1 Add `handle_promote_fork(session_id: str, fork_id: str) -> None` function
  - Stop autopilot if running (`st.session_state["is_autopilot_running"] = False`)
  - Call `promote_fork()` from persistence
  - Load the new main timeline's latest checkpoint
  - Clear `active_fork_id` on the loaded state (set to None)
  - Update `st.session_state["game"]` with the new main state
  - Show success toast: "Fork '[name]' promoted to main timeline"
  - Error handling: catch ValueError and OSError, show `st.error()`

- [x] 2.2 Add `handle_collapse_all_forks(session_id: str) -> None` function
  - Stop autopilot if running
  - If currently in a fork (`active_fork_id is not None`), switch to main first via `handle_return_to_main()`
  - Call `collapse_all_forks()` from persistence
  - Show success toast: "All forks removed ([count] forks deleted)"
  - Call `st.rerun()` to refresh UI
  - Error handling: catch OSError, show `st.error()`

### 3. Replace "Make Primary" Placeholder (app.py)

- [x] 3.1 Replace the placeholder "Make Primary" button logic in `render_fork_controls()`
  - Remove the `st.info("Promote to main timeline (coming in Story 12.4)")` placeholder
  - Add a confirmation dialog using `st.session_state` flag pattern (matching delete confirmation):
    ```python
    if st.button("Make Primary", key=f"promote_fork_{fork.fork_id}", disabled=is_generating):
        st.session_state[f"confirm_promote_{fork.fork_id}"] = True
    if st.session_state.get(f"confirm_promote_{fork.fork_id}"):
        # Show confirmation with explanation
        st.warning(
            f"Promote '{escape_html(fork.name)}' to main timeline?\n\n"
            f"The main timeline's content after turn {fork.branch_turn} "
            "will be archived as a new fork."
        )
        if st.button("Confirm Promote", key=f"confirm_promo_{fork.fork_id}"):
            handle_promote_fork(session_id, fork.fork_id)
            st.session_state[f"confirm_promote_{fork.fork_id}"] = False
            st.rerun()
    ```
  - Disable "Make Primary" button when `is_generating` is True (no promotion during LLM generation)

- [x] 3.2 Add "Collapse to Single Timeline" button at the bottom of the fork list
  - Only visible when forks exist (`len(forks) > 0`)
  - Button label: "Collapse to Single Timeline"
  - Uses same confirmation pattern:
    ```python
    if st.button("Collapse to Single Timeline", key="collapse_forks_btn", disabled=is_generating):
        st.session_state["confirm_collapse_forks"] = True
    if st.session_state.get("confirm_collapse_forks"):
        st.warning(
            f"Delete ALL {len(forks)} fork(s) and keep only the main timeline? "
            "This cannot be undone."
        )
        if st.button("Confirm Collapse", key="confirm_collapse_btn"):
            handle_collapse_all_forks(session_id)
            st.session_state["confirm_collapse_forks"] = False
            st.rerun()
    ```
  - Positioned after the fork list, before the expander closes
  - Uses `type="secondary"` styling to distinguish from primary actions

### 4. Tests

- [x] 4.1 Test `promote_fork()` basic flow
  - Create session with 5 checkpoints (turns 1-5)
  - Create fork at turn 3
  - Save 2 fork checkpoints (turns 4-5 with different content)
  - Promote fork
  - Verify: main timeline checkpoints at turns 4-5 now contain fork's content
  - Verify: turns 1-3 unchanged (pre-branch preserved)
  - Verify: promoted fork removed from registry
  - Verify: promoted fork directory removed
  - Verify: archive fork created with name "Pre-[fork_name] main"
  - Verify: archive fork contains old main's turns 4-5

- [x] 4.2 Test `promote_fork()` when fork is longer than main
  - Main has turns 1-4 (branch at turn 3, 1 post-branch turn)
  - Fork has turns 3-6 (3 post-branch turns)
  - Promote fork
  - Verify: main now has turns 1-3 + fork's turns 4-6
  - Verify: archive fork has only old main's turn 4

- [x] 4.3 Test `promote_fork()` when main is longer than fork
  - Main has turns 1-7 (branch at turn 3, 4 post-branch turns)
  - Fork has turns 3-4 (1 post-branch turn)
  - Promote fork
  - Verify: main now has turns 1-4 (turn 4 is fork's content)
  - Verify: main's turns 5-7 are removed
  - Verify: archive fork has old main's turns 4-7

- [x] 4.4 Test `promote_fork()` when main has no post-branch checkpoints
  - Main has turns 1-3 (branch at turn 3, 0 post-branch turns)
  - Fork has turns 3-5 (2 post-branch turns)
  - Promote fork
  - Verify: main now has turns 1-5 (turns 4-5 from fork)
  - Verify: no archive fork created (nothing to archive)
  - Verify: promoted fork removed from registry

- [x] 4.5 Test `promote_fork()` error cases
  - Non-existent fork_id: raises ValueError
  - Fork with no checkpoints beyond branch: raises ValueError
  - Invalid session_id: raises ValueError
  - Invalid fork_id format: raises ValueError

- [x] 4.6 Test `promote_fork()` with multiple forks
  - Create two forks (fork_001 and fork_002) from same branch point
  - Promote fork_001
  - Verify: fork_001 removed from registry, fork_002 still present
  - Verify: archive fork added to registry
  - Verify: fork_002's checkpoints untouched

- [x] 4.7 Test `promote_fork()` preserves checkpoint content integrity
  - Load promoted main checkpoint and verify it matches original fork checkpoint content
  - Load archive fork checkpoint and verify it matches original main checkpoint content
  - Verify `ground_truth_log` entries are different between main and archive

- [x] 4.8 Test `collapse_all_forks()` function
  - Create session with 3 forks
  - Call `collapse_all_forks()`
  - Verify: all fork directories removed
  - Verify: `forks.yaml` removed
  - Verify: `forks/` parent directory removed (if empty)
  - Verify: main timeline checkpoints untouched
  - Verify: returns 3 (number of forks deleted)
  - Returns 0 for session with no forks
  - Returns 0 for non-existent session (no crash)

- [x] 4.9 Test `collapse_all_forks()` when currently in a fork
  - Verify that calling collapse when `active_fork_id` is set does not crash
  - (The UI handler takes care of switching to main first; the persistence function itself does not check `active_fork_id`)

- [x] 4.10 Test promotion then continued gameplay
  - After `promote_fork()`, save a new checkpoint on the main timeline
  - Verify it saves correctly to the main session directory
  - Verify the game loop (`active_fork_id=None`) routes saves to main

- [x] 4.11 Test backward compatibility
  - Sessions without forks: `promote_fork()` raises ValueError (no fork registry)
  - Sessions without forks: `collapse_all_forks()` returns 0
  - Old game states without `active_fork_id` continue to work

- [x] 4.12 Test confirmation state management
  - Verify `st.session_state[f"confirm_promote_{fork_id}"]` is set on button click
  - Verify flag is cleared after promotion or cancel
  - Verify `st.session_state["confirm_collapse_forks"]` is set/cleared correctly

## Dependencies

- **Story 12.1** (done): Provides `ForkMetadata`, `ForkRegistry`, `create_fork()`, fork directory structure, `active_fork_id` field
- **Story 12.2** (done): Provides `save_fork_checkpoint()`, `load_fork_checkpoint()`, `list_fork_checkpoints()`, `delete_fork()`, `rename_fork()`, fork-aware checkpoint routing, `handle_switch_to_fork()`, `handle_return_to_main()`
- **Story 12.3** (done): Provides `build_comparison_data()`, fork comparison UI (read-only reference for users deciding which fork to promote)
- **Story 4.1** (done): Provides checkpoint save/load, serialization patterns, atomic writes

## Dev Notes

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `persistence.py` | Modify | Add `promote_fork()`, `collapse_all_forks()`, update `__all__` |
| `app.py` | Modify | Add `handle_promote_fork()`, `handle_collapse_all_forks()`, replace "Make Primary" placeholder, add "Collapse to Single Timeline" button |
| `tests/test_story_12_4_fork_resolution.py` | Create | Unit and integration tests for promotion, collapse, and UI state management |

### Code Patterns with Examples

#### 1. promote_fork (persistence.py)

```python
def promote_fork(session_id: str, fork_id: str) -> int:
    """Promote a fork to become the main timeline.

    Story 12.4: Fork Resolution.
    FR84: User can merge or abandon forks.

    The promoted fork's post-branch checkpoints replace the main timeline's
    post-branch checkpoints. The old main's post-branch checkpoints are
    archived into a new fork for reference.

    Algorithm:
    1. Load fork metadata to determine branch_turn
    2. Archive main timeline's post-branch checkpoints into a new fork
    3. Delete main timeline's post-branch checkpoint files
    4. Copy promoted fork's post-branch checkpoints to main directory
    5. Remove promoted fork from registry and delete its directory
    6. Return latest turn number on new main timeline

    Args:
        session_id: Session ID string.
        fork_id: Fork ID to promote.

    Returns:
        Latest turn number on the new main timeline after promotion.

    Raises:
        ValueError: If fork_id not found, fork has no post-branch content,
                    or session_id is invalid.
    """
    import shutil

    _validate_session_id(session_id)
    _validate_fork_id(fork_id)

    # Load fork registry
    registry = load_fork_registry(session_id)
    if registry is None:
        raise ValueError(f"No fork registry found for session {session_id!r}")

    fork_meta = registry.get_fork(fork_id)
    if fork_meta is None:
        raise ValueError(f"Fork {fork_id!r} not found in session {session_id!r}")

    branch_turn = fork_meta.branch_turn
    fork_name = fork_meta.name

    # Get fork's post-branch checkpoints
    fork_checkpoints = list_fork_checkpoints(session_id, fork_id)
    post_branch_fork_turns = [t for t in fork_checkpoints if t > branch_turn]
    if not post_branch_fork_turns:
        raise ValueError(
            f"Fork {fork_id!r} has no checkpoints beyond branch point "
            f"(turn {branch_turn})"
        )

    # Get main timeline's post-branch checkpoints
    main_checkpoints = list_checkpoints(session_id)
    post_branch_main_turns = [t for t in main_checkpoints if t > branch_turn]

    session_dir = get_session_dir(session_id)

    # Step 1: Archive main's post-branch checkpoints (if any)
    if post_branch_main_turns:
        archive_id = registry.next_fork_id()
        archive_dir = ensure_fork_dir(session_id, archive_id)

        now = datetime.now(UTC).isoformat() + "Z"
        archive_meta = ForkMetadata(
            fork_id=archive_id,
            name=f"Pre-{fork_name} main",
            parent_session_id=session_id,
            branch_turn=branch_turn,
            created_at=now,
            updated_at=now,
            turn_count=len(post_branch_main_turns),
        )

        # Also copy the branch point checkpoint to the archive
        # so it is self-contained
        branch_src = session_dir / f"turn_{branch_turn:03d}.json"
        if branch_src.exists():
            branch_dst = archive_dir / f"turn_{branch_turn:03d}.json"
            shutil.copy2(str(branch_src), str(branch_dst))

        # Move post-branch main checkpoints into archive fork
        for turn in post_branch_main_turns:
            src = session_dir / f"turn_{turn:03d}.json"
            dst = archive_dir / f"turn_{turn:03d}.json"
            if src.exists():
                shutil.copy2(str(src), str(dst))
                src.unlink()

        registry.add_fork(archive_meta)

    # Step 2: Copy fork's post-branch checkpoints to main directory
    fork_dir = get_fork_dir(session_id, fork_id)
    for turn in post_branch_fork_turns:
        src = fork_dir / f"turn_{turn:03d}.json"
        dst = session_dir / f"turn_{turn:03d}.json"
        if src.exists():
            shutil.copy2(str(src), str(dst))

    # Step 3: Remove promoted fork from registry
    registry.forks = [f for f in registry.forks if f.fork_id != fork_id]

    # Step 4: Delete promoted fork's directory
    if fork_dir.exists():
        shutil.rmtree(fork_dir)

    # Step 5: Save updated registry
    save_fork_registry(session_id, registry)

    # Return latest checkpoint on new main timeline
    latest = get_latest_checkpoint(session_id)
    return latest if latest is not None else branch_turn
```

#### 2. collapse_all_forks (persistence.py)

```python
def collapse_all_forks(session_id: str) -> int:
    """Remove all forks for a session, keeping only the main timeline.

    Story 12.4: Fork Resolution.
    FR84: User can merge or abandon forks.

    Deletes all fork directories and the fork registry file.
    Main timeline checkpoints are not modified.

    Args:
        session_id: Session ID string.

    Returns:
        Number of forks deleted.
    """
    import shutil

    _validate_session_id(session_id)

    registry = load_fork_registry(session_id)
    if registry is None:
        return 0

    fork_count = len(registry.forks)
    if fork_count == 0:
        return 0

    # Delete each fork's directory
    for fork in registry.forks:
        fork_dir = get_fork_dir(session_id, fork.fork_id)
        if fork_dir.exists():
            shutil.rmtree(fork_dir, ignore_errors=True)

    # Remove the forks/ parent directory if empty
    forks_parent = get_session_dir(session_id) / "forks"
    if forks_parent.exists():
        try:
            forks_parent.rmdir()  # Only removes if empty
        except OSError:
            pass  # Not empty (unexpected files), leave it

    # Delete forks.yaml
    registry_path = get_fork_registry_path(session_id)
    if registry_path.exists():
        registry_path.unlink()

    return fork_count
```

#### 3. handle_promote_fork (app.py)

```python
def handle_promote_fork(session_id: str, fork_id: str) -> None:
    """Promote a fork to become the main timeline.

    Story 12.4: Fork Resolution (FR84).
    Stops autopilot, promotes the fork, reloads the main timeline state.

    Args:
        session_id: Session ID string.
        fork_id: Fork ID to promote.
    """
    # Stop autopilot
    st.session_state["is_autopilot_running"] = False

    # Get fork name for display before promotion removes it
    registry = load_fork_registry(session_id)
    fork_name = "Unknown"
    if registry:
        fork_meta = registry.get_fork(fork_id)
        if fork_meta:
            fork_name = fork_meta.name

    try:
        # Promote the fork
        latest_turn = promote_fork(session_id, fork_id)

        # Load the new main timeline state
        main_state = load_checkpoint(session_id, latest_turn)
        if main_state is None:
            st.error(f"Failed to load promoted main timeline at turn {latest_turn}")
            return

        # Clear active_fork_id (we're now on main)
        main_state["active_fork_id"] = None

        # Update session state
        st.session_state["game"] = main_state
        safe_name = escape_html(fork_name)
        st.toast(f"Fork '{safe_name}' promoted to main timeline")

    except ValueError as e:
        st.error(str(e))
    except OSError as e:
        st.error(f"Failed to promote fork: {e}")
```

#### 4. handle_collapse_all_forks (app.py)

```python
def handle_collapse_all_forks(session_id: str) -> None:
    """Remove all forks for the current session.

    Story 12.4: Fork Resolution (FR84).
    If currently in a fork, returns to main first.

    Args:
        session_id: Session ID string.
    """
    # Stop autopilot
    st.session_state["is_autopilot_running"] = False

    # If currently in a fork, return to main first
    game: GameState = st.session_state.get("game", {})
    if game.get("active_fork_id") is not None:
        handle_return_to_main(session_id)

    try:
        count = collapse_all_forks(session_id)
        st.toast(f"All forks removed ({count} fork(s) deleted)")
    except OSError as e:
        st.error(f"Failed to collapse forks: {e}")
```

#### 5. Updated render_fork_controls "Make Primary" section (app.py)

Replace the existing placeholder (lines 7322-7330):

```python
# Make Primary (Story 12.4: Fork Resolution)
if st.button(
    "Make Primary",
    key=f"promote_fork_{fork.fork_id}",
    disabled=is_generating,
):
    st.session_state[f"confirm_promote_{fork.fork_id}"] = True
if st.session_state.get(f"confirm_promote_{fork.fork_id}"):
    st.warning(
        f"Promote '{escape_html(fork.name)}' to main timeline?\n\n"
        f"Main timeline content after turn {fork.branch_turn} "
        "will be archived as a new fork."
    )
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button(
            "Confirm",
            key=f"confirm_promo_{fork.fork_id}",
        ):
            handle_promote_fork(session_id, fork.fork_id)
            st.session_state[f"confirm_promote_{fork.fork_id}"] = False
            st.rerun()
    with col_cancel:
        if st.button(
            "Cancel",
            key=f"cancel_promo_{fork.fork_id}",
        ):
            st.session_state[f"confirm_promote_{fork.fork_id}"] = False
            st.rerun()
```

#### 6. "Collapse to Single Timeline" button (app.py)

Add at the end of the fork list section in `render_fork_controls()`:

```python
# Collapse all forks (Story 12.4)
if forks:
    st.markdown("---")
    if st.button(
        "Collapse to Single Timeline",
        key="collapse_forks_btn",
        type="secondary",
        disabled=is_generating,
    ):
        st.session_state["confirm_collapse_forks"] = True
    if st.session_state.get("confirm_collapse_forks"):
        st.warning(
            f"Delete ALL {len(forks)} fork(s) and keep only the "
            "main timeline? This cannot be undone."
        )
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("Confirm", key="confirm_collapse_btn"):
                handle_collapse_all_forks(session_id)
                st.session_state["confirm_collapse_forks"] = False
                st.rerun()
        with col_cancel:
            if st.button("Cancel", key="cancel_collapse_btn"):
                st.session_state["confirm_collapse_forks"] = False
                st.rerun()
```

### Key Design Decisions

1. **Archive, don't discard:** When promoting a fork, the old main timeline's post-branch content is preserved as a new fork (named "Pre-[fork_name] main"). This matches the epic AC: "the old main timeline becomes a fork (preserved, not deleted)." Users can delete this archive fork later if they don't need it.

2. **Copy-based promotion, not renaming:** Checkpoints are copied (via `shutil.copy2`) rather than using filesystem rename/hardlinks. This is safer across filesystems and avoids edge cases with Path.rename() on Windows. The cost is disk I/O but checkpoints are small (~100KB each).

3. **Branch point checkpoint is shared:** The checkpoint at `branch_turn` is NOT moved or modified during promotion. It exists in the main directory and serves as the common ancestor. The archive fork gets a copy of it for self-containment.

4. **Confirmation before destructive actions:** Both "Make Primary" and "Collapse to Single Timeline" require explicit confirmation. The confirmation message explains what will happen. This follows the existing delete confirmation pattern in `render_fork_controls()` (using `st.session_state` flags).

5. **Autopilot stops during promotion:** Promotion changes the entire game state and checkpoint layout. Autopilot must be stopped to prevent the old state from being used after promotion. Same pattern as `handle_switch_to_fork()`.

6. **`active_fork_id` cleared after promotion:** After promoting, the user is on the main timeline. `active_fork_id` is set to `None` so subsequent game turns save to the main directory. This is critical for the game loop routing in `graph.py`.

7. **No LLM calls:** Fork resolution is purely a persistence/state management and UI operation. No LLM involvement needed.

8. **Collapse removes forks.yaml:** After collapsing all forks, the `forks.yaml` file and `forks/` directory are cleaned up. The session behaves exactly like a session that never had forks.

9. **Disable buttons during generation:** "Make Primary" and "Collapse" buttons are disabled when `is_generating` is True, preventing race conditions with checkpoint saves. This matches the existing pattern for "Switch" and "Compare" buttons.

10. **`promote_fork()` raises on empty fork:** If a fork has no checkpoints beyond the branch point (turn_count=0, only the copied branch checkpoint), it cannot be promoted. The function raises a ValueError with a clear message. Users must play some turns in the fork before promoting.

### Test Strategy

**Test file:** `tests/test_story_12_4_fork_resolution.py`

**Fixture pattern (follow existing test_persistence.py):**

```python
import pytest
from pathlib import Path
from collections.abc import Generator
from unittest.mock import patch
import shutil

from models import (
    ForkMetadata,
    ForkRegistry,
    GameState,
    create_initial_game_state,
)
from persistence import (
    CAMPAIGNS_DIR,
    collapse_all_forks,
    create_fork,
    get_fork_dir,
    get_session_dir,
    get_latest_checkpoint,
    list_checkpoints,
    list_fork_checkpoints,
    list_forks,
    load_checkpoint,
    load_fork_checkpoint,
    load_fork_registry,
    promote_fork,
    save_checkpoint,
    save_fork_checkpoint,
    serialize_game_state,
    deserialize_game_state,
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
def session_with_fork_and_content(
    temp_campaigns_dir: Path, sample_game_state: GameState
) -> tuple[str, str]:
    """Create a session with divergent main and fork content.

    Returns (session_id, fork_id).
    Sets up:
    - Main timeline: turns 1-5 with log entries
    - Fork: branched at turn 3, then turns 4-6 with different content
    """
    session_id = "001"

    # Build main timeline
    state = {**sample_game_state}
    for i in range(1, 6):
        state["ground_truth_log"] = [
            f"[dm] Main timeline entry {j}" for j in range(1, i + 1)
        ]
        save_checkpoint(state, session_id, i)

    # Create fork at turn 3
    fork_meta = create_fork(
        state=state,
        session_id=session_id,
        fork_name="Diplomacy Attempt",
        turn_number=3,
    )
    fork_id = fork_meta.fork_id

    # Build fork content (turns 4-6)
    fork_state = {**sample_game_state}
    fork_state["active_fork_id"] = fork_id
    for i in range(4, 7):
        fork_state["ground_truth_log"] = [
            f"[dm] Main timeline entry {j}" for j in range(1, 4)
        ] + [f"[dm] Fork entry {j}" for j in range(4, i + 1)]
        save_fork_checkpoint(fork_state, session_id, fork_id, i)

    return session_id, fork_id
```

**Unit Tests:**

- `promote_fork()` basic flow: checkpoints moved correctly, registry updated, archive created
- `promote_fork()` fork longer than main: extra turns appear on main
- `promote_fork()` main longer than fork: excess main turns removed, archived
- `promote_fork()` no post-branch main: no archive created, fork content promoted
- `promote_fork()` error cases: missing fork, empty fork, invalid IDs
- `promote_fork()` with multiple forks: only promoted fork affected, others preserved
- `promote_fork()` content integrity: verify actual log content is preserved
- `collapse_all_forks()` removes all forks and registry
- `collapse_all_forks()` with no forks returns 0
- `collapse_all_forks()` preserves main timeline

**Integration Tests:**

- Full promotion flow: create session -> play -> fork -> play fork -> promote -> verify main contains fork content
- Post-promotion gameplay: promote, then save new checkpoints to main, verify routing
- Promote while in fork: `active_fork_id` was set, verify it's cleared after promotion
- Collapse with active fork: handler switches to main first, then collapses

**Edge Cases:**

- Fork at turn 1 (branch_turn=1): only turn 1 is shared
- Fork with same content as main (identical logs)
- Promote the archive fork (yes, users could promote the archive of a previous promotion)
- Session with many forks (10+): collapse all handles gracefully
- Concurrent save during promotion: disabled via `is_generating` flag

### Important Constraints

- **Scope boundary:** This story covers fork promotion and collapse only. It does not support "merge" (combining content from two timelines), which was mentioned in the epic but deemed impractical for narrative content. Instead, the comparison view (Story 12.3) provides a read-only reference.
- **No LLM calls:** Fork resolution is purely a persistence/state management operation. No LLM involvement needed.
- **No new dependencies:** Uses only existing imports (shutil, Path, Pydantic, YAML, Streamlit).
- **Backward compatibility:** Sessions without forks are unaffected. All new functions handle the "no forks" case gracefully.
- **Atomic safety:** Individual checkpoint copies use `shutil.copy2()`. The promotion as a whole is NOT fully atomic (if the process crashes mid-promotion, some checkpoints may be partially moved). However, since both the archive fork and the promoted fork's source exist during the copy phase, no data is lost. The worst case is duplicate checkpoints in both locations, which is harmless.
- **Disk space:** During promotion, checkpoints temporarily exist in both locations (source and destination) until the source fork is deleted. This doubles the space briefly (~200KB per checkpoint). Acceptable for user-triggered operations.
- **Path security:** Fork IDs and session IDs continue to be validated with existing functions for path traversal prevention.
- **No migration needed:** Existing sessions, forks, and checkpoints continue to work unchanged. The new functions are additive.
- **graph.py not modified:** The game loop's checkpoint routing (`active_fork_id` check) already works correctly. After promotion clears `active_fork_id`, saves go to the main directory. No changes needed.
