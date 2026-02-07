# Story 12-2: Fork Management UI

## Story

As a **user**,
I want **to view, switch between, and manage forks**,
So that **I can explore multiple storylines**.

## Status

**Status:** review
**Epic:** 12 - Fork Gameplay
**Created:** 2026-02-07
**FRs Covered:** FR82 (system can manage multiple active forks with distinct GameState branches)
**Predecessors:** Story 12.1 (Fork Creation) - DONE

## Acceptance Criteria

**Given** the session has forks
**When** viewing the Session History panel
**Then** forks are shown as branches off the main timeline

**Given** the fork list
**When** displayed
**Then** each fork shows: name, turn created, current turn, last played

**Given** I want to play a fork
**When** I click "Switch to Fork"
**Then** the game state loads from that fork's latest checkpoint
**And** the mode indicator shows "Fork: [Fork Name]"

**Given** I'm playing in a fork
**When** I want to return to main timeline
**Then** I can click "Return to Main"
**And** the fork's progress is saved

**Given** fork management
**When** I right-click or access options
**Then** I can: Rename, Delete, or "Make Primary" (promote fork to main)

## Context: What Already Exists (Story 12.1)

### models.py (existing)

- `ForkMetadata` Pydantic model: `fork_id`, `name`, `parent_session_id`, `branch_turn`, `created_at`, `updated_at`, `turn_count`
- `ForkRegistry` Pydantic model: `session_id`, `forks` list, `get_fork()`, `get_forks_at_turn()`, `next_fork_id()`, `add_fork()`
- `GameState` TypedDict with `active_fork_id: str | None` field (None = main timeline)
- `create_initial_game_state()` and `populate_game_state()` both set `active_fork_id=None`

### persistence.py (existing)

- `create_fork(state, session_id, fork_name, turn_number)` -> creates fork directory, copies checkpoint, saves registry
- `get_fork_dir(session_id, fork_id)` -> `campaigns/session_XXX/forks/fork_XXX/`
- `ensure_fork_dir(session_id, fork_id)` -> creates directory tree
- `list_forks(session_id)` -> sorted `list[ForkMetadata]`
- `save_fork_registry(session_id, registry)` / `load_fork_registry(session_id)` -> YAML round-trip
- `get_fork_registry_path(session_id)` -> path to `forks.yaml`
- `_validate_fork_id(fork_id)` -> path traversal prevention
- `serialize_game_state()` / `deserialize_game_state()` -> handle `active_fork_id`
- `save_checkpoint(state, session_id, turn_number)` -> saves to session dir (main timeline only currently)
- `load_checkpoint(session_id, turn_number)` -> loads from session dir

### app.py (existing)

- `render_fork_controls()` -> "Fork Timeline" expander in sidebar with fork name input, "Create Fork" button, fork count indicator
- Fork creation flow already works: creates directory, copies checkpoint, saves registry

### graph.py (existing)

- `run_single_round()` calls `save_checkpoint(result, session_id, turn_number)` after each round
- This currently always saves to main timeline directory -- needs fork-aware routing

### Directory Structure (from Story 12.1)
```
campaigns/session_001/
  turn_001.json
  turn_002.json
  turn_003.json          <-- branch point
  config.yaml
  forks.yaml             <-- fork registry
  forks/
    fork_001/            <-- first fork
      turn_003.json      <-- copy of branch point
    fork_002/
      turn_005.json
```

## What Story 12.2 Changes

This story adds **fork management UI and fork-aware game loop** -- the ability to list forks, switch between them, return to main, and manage fork metadata. Specifically:

1. **Fork list display** in the sidebar Fork Timeline expander: shows all forks with metadata (name, branch turn, current turn, last played timestamp).
2. **Switch to fork**: loads the fork's latest checkpoint, sets `active_fork_id` on GameState, updates UI indicator.
3. **Return to main**: saves current fork progress, clears `active_fork_id`, reloads main timeline's latest checkpoint.
4. **Fork mode indicator**: shows "Fork: [name]" badge when playing in a fork, visible in the sidebar session header area.
5. **Fork management actions**: Rename (updates ForkRegistry), Delete (removes fork directory and registry entry).
6. **Fork-aware checkpoint saving**: when `active_fork_id` is set, `save_checkpoint` routes writes to the fork directory instead of the main session directory.
7. **"Make Primary" placeholder button**: visible in management UI but shows "Coming in Story 12.4" message. Full promotion logic deferred to Story 12.4.

## Tasks

### 1. Fork-Aware Checkpoint Persistence (persistence.py)

- [x] 1.1 Add `save_fork_checkpoint(state, session_id, fork_id, turn_number)` function
  - Saves checkpoint to `forks/fork_{fork_id}/turn_{NNN}.json` within the session directory
  - Uses same atomic write pattern as `save_checkpoint()` (temp file + rename)
  - Updates `ForkMetadata.updated_at` and `ForkMetadata.turn_count` in the registry
  - Calls `save_fork_registry()` after updating metadata

- [x] 1.2 Add `load_fork_checkpoint(session_id, fork_id, turn_number)` function
  - Loads checkpoint from `forks/fork_{fork_id}/turn_{NNN}.json`
  - Returns `GameState | None` (None if not found or invalid)
  - Uses `deserialize_game_state()` for reconstruction

- [x] 1.3 Add `list_fork_checkpoints(session_id, fork_id)` function
  - Lists all turn numbers in a fork directory, sorted ascending
  - Same glob pattern as `list_checkpoints()` but scoped to fork dir

- [x] 1.4 Add `get_latest_fork_checkpoint(session_id, fork_id)` function
  - Returns latest turn number in the fork, or None if empty
  - Delegates to `list_fork_checkpoints()`

- [x] 1.5 Add `rename_fork(session_id, fork_id, new_name)` function
  - Validates new_name is non-empty, non-whitespace
  - Loads fork registry, finds fork by ID, updates name
  - Saves updated registry
  - Returns updated `ForkMetadata` or raises `ValueError` if fork not found

- [x] 1.6 Add `delete_fork(session_id, fork_id)` function
  - Validates fork_id
  - Removes fork directory (`shutil.rmtree`)
  - Removes fork from registry and saves updated registry
  - Returns `True` if deleted, `False` if fork not found
  - Safety: refuses to delete if `active_fork_id == fork_id` (cannot delete the fork you are playing)

- [x] 1.7 Update `__all__` exports in persistence.py with new functions:
  - `save_fork_checkpoint`, `load_fork_checkpoint`, `list_fork_checkpoints`, `get_latest_fork_checkpoint`, `rename_fork`, `delete_fork`

### 2. Fork-Aware Game Loop (graph.py)

- [x] 2.1 Update `run_single_round()` to route checkpoint saves based on `active_fork_id`
  - If `state["active_fork_id"]` is not None, call `save_fork_checkpoint()` instead of `save_checkpoint()`
  - Import `save_fork_checkpoint` alongside `save_checkpoint`
  - Pass `active_fork_id` from state to determine save target

### 3. Fork List Display (app.py)

- [x] 3.1 Expand `render_fork_controls()` to display fork list below the create-fork form
  - For each fork, display:
    - Fork name (bold)
    - "Branched at turn {branch_turn}"
    - "Turns played: {turn_count}" (or "Current turn: {branch_turn + turn_count}")
    - "Last played: {updated_at}" (formatted human-readable, e.g., "2026-02-07 14:30")
  - Use `st.container()` for each fork entry with visual separation
  - Highlight the currently active fork (if `active_fork_id` matches)

- [x] 3.2 Add "Switch to Fork" button on each fork entry
  - Only shown when NOT currently playing that fork
  - Calls `handle_switch_to_fork(session_id, fork_id)` on click
  - Button disabled during LLM generation (`is_generating` flag)

- [x] 3.3 Add "Return to Main" button
  - Only shown when `active_fork_id` is not None (currently playing a fork)
  - Calls `handle_return_to_main(session_id)` on click
  - Displayed prominently at top of Fork Timeline section
  - Button disabled during LLM generation

### 4. Fork Switching Logic (app.py)

- [x] 4.1 Add `handle_switch_to_fork(session_id, fork_id)` function
  - Stop autopilot if running (`is_autopilot_running = False`)
  - Load fork registry to get `ForkMetadata`
  - Get latest fork checkpoint via `get_latest_fork_checkpoint()`
  - Load checkpoint via `load_fork_checkpoint()`
  - Set `active_fork_id` on the loaded state
  - Update `st.session_state["game"]` with the loaded state
  - Show success toast: "Switched to fork: [name]"
  - Call `st.rerun()` to refresh UI
  - Error handling: show `st.error()` if fork or checkpoint not found

- [x] 4.2 Add `handle_return_to_main(session_id)` function
  - Stop autopilot if running
  - Save current fork's progress: call `save_fork_checkpoint()` with current state
  - Load main timeline's latest checkpoint via `get_latest_checkpoint()` + `load_checkpoint()`
  - Clear `active_fork_id` on the loaded state (set to None)
  - Update `st.session_state["game"]` with main timeline state
  - Show success toast: "Returned to main timeline"
  - Call `st.rerun()` to refresh UI
  - Error handling: if main timeline has no checkpoints, show error

### 5. Fork Mode Indicator (app.py)

- [x] 5.1 Add fork mode indicator to sidebar session header area
  - When `active_fork_id` is not None, display a styled badge: "Fork: [Fork Name]"
  - Use a distinctive visual treatment (colored background, border) to make it obvious
  - Position near the session number / session info at the top of the sidebar
  - Load fork name from registry using `active_fork_id`

- [x] 5.2 Update `render_session_header_html()` or equivalent to include fork badge
  - Pass `active_fork_id` and fork name through to the header renderer
  - Badge disappears when on main timeline (`active_fork_id is None`)

### 6. Fork Management Actions (app.py)

- [x] 6.1 Add fork management popover/expander on each fork entry
  - Use `st.popover` or inline buttons for management actions
  - Actions: Rename, Delete, Make Primary (placeholder)

- [x] 6.2 Implement Rename action
  - Text input pre-filled with current fork name
  - "Save" button calls `rename_fork()` from persistence
  - Success: update display, show toast "Fork renamed to '[new_name]'"
  - Validation: reject empty/whitespace names

- [x] 6.3 Implement Delete action
  - Confirmation step: "Delete fork '[name]'? This cannot be undone."
  - Call `delete_fork()` from persistence
  - Cannot delete the fork currently being played (`active_fork_id` check)
  - Success: remove from list, show toast "Fork '[name]' deleted"

- [x] 6.4 Add "Make Primary" placeholder button
  - Button visible but shows info message: "Promote to main timeline (coming soon)"
  - Deferred to Story 12.4 (Fork Resolution)
  - This satisfies the AC while keeping scope bounded

### 7. Tests

- [x] 7.1 Test `save_fork_checkpoint()` / `load_fork_checkpoint()` round-trip
  - Saves to correct fork directory path
  - Loaded state matches saved state
  - Updates `ForkMetadata.updated_at` and `turn_count` in registry
  - Returns None for missing checkpoint file

- [x] 7.2 Test `list_fork_checkpoints()` and `get_latest_fork_checkpoint()`
  - Returns sorted turn numbers from fork directory
  - Returns empty list / None for empty fork directory
  - Ignores non-checkpoint files in fork directory

- [x] 7.3 Test `rename_fork()` function
  - Renames fork in registry, persists to forks.yaml
  - Rejects empty/whitespace names
  - Returns ValueError for non-existent fork_id
  - Preserves other forks in registry

- [x] 7.4 Test `delete_fork()` function
  - Removes fork directory and registry entry
  - Returns False for non-existent fork_id
  - Refuses to delete active fork (when `active_fork_id` matches)
  - Preserves other forks and main timeline files

- [x] 7.5 Test fork-aware checkpoint routing in `run_single_round()`
  - When `active_fork_id` is set, checkpoint saves to fork directory
  - When `active_fork_id` is None, checkpoint saves to main session directory
  - Mocked test to verify routing logic without running full LLM pipeline

- [x] 7.6 Test fork switching flow (integration)
  - Create fork, save additional checkpoints to fork, switch to fork, verify state loaded correctly
  - Verify `active_fork_id` is set on loaded state
  - Switch back to main, verify `active_fork_id` is None
  - Verify fork progress was saved before switching back

- [x] 7.7 Test fork mode indicator logic
  - When `active_fork_id` is None, no fork badge displayed
  - When `active_fork_id` is set, badge shows correct fork name
  - Fork name loaded from registry

- [x] 7.8 Test backward compatibility
  - Old game states without `active_fork_id` default to None (main timeline behavior)
  - Sessions without forks show no fork list (empty state)

## Dependencies

- **Story 12.1** (done): Provides `ForkMetadata`, `ForkRegistry`, `create_fork()`, `list_forks()`, fork directory structure, `active_fork_id` field
- **Story 4.1** (done): Provides checkpoint save/load patterns, atomic writes
- **Story 4.3** (done): Provides session metadata patterns

## Dev Notes

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `persistence.py` | Modify | Add `save_fork_checkpoint()`, `load_fork_checkpoint()`, `list_fork_checkpoints()`, `get_latest_fork_checkpoint()`, `rename_fork()`, `delete_fork()`, update `__all__` |
| `graph.py` | Modify | Update `run_single_round()` to route checkpoint saves based on `active_fork_id` |
| `app.py` | Modify | Expand `render_fork_controls()` with fork list, switch/return buttons, mode indicator, management actions. Add `handle_switch_to_fork()`, `handle_return_to_main()` handlers |
| `tests/test_story_12_2_fork_management_ui.py` | Create | Unit and integration tests for all new persistence functions and switching logic |

### Code Patterns with Examples

#### 1. save_fork_checkpoint (persistence.py, follow save_checkpoint pattern)

```python
def save_fork_checkpoint(
    state: GameState,
    session_id: str,
    fork_id: str,
    turn_number: int,
) -> Path:
    """Save game state checkpoint to a fork's directory.

    Story 12.2: Fork Management UI (FR82).
    Routes checkpoint writes to the fork subdirectory instead of
    the main session directory.

    Uses atomic write pattern: write to temp file first, then rename.

    Args:
        state: Current game state to save.
        session_id: Session ID string.
        fork_id: Fork ID string.
        turn_number: Turn number for this checkpoint.

    Returns:
        Path where checkpoint was saved.

    Raises:
        OSError: If write fails.
        ValueError: If session_id or fork_id are invalid.
    """
    _validate_session_id(session_id)
    _validate_fork_id(fork_id)
    _validate_turn_number(turn_number)

    # Ensure fork directory exists
    fork_dir = ensure_fork_dir(session_id, fork_id)
    checkpoint_path = fork_dir / f"turn_{turn_number:03d}.json"

    # Serialize state
    json_content = serialize_game_state(state)

    # Atomic write: temp file then rename
    temp_fd, temp_path = tempfile.mkstemp(dir=fork_dir, suffix=".json.tmp")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(json_content)
        Path(temp_path).replace(checkpoint_path)
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        raise

    # Update fork metadata in registry
    registry = load_fork_registry(session_id)
    if registry is not None:
        fork_meta = registry.get_fork(fork_id)
        if fork_meta is not None:
            fork_meta.updated_at = datetime.now(UTC).isoformat() + "Z"
            # turn_count = turns beyond branch point
            fork_checkpoints = list_fork_checkpoints(session_id, fork_id)
            fork_meta.turn_count = max(0, len(fork_checkpoints) - 1)
            save_fork_registry(session_id, registry)

    return checkpoint_path
```

#### 2. load_fork_checkpoint (persistence.py, follow load_checkpoint pattern)

```python
def load_fork_checkpoint(
    session_id: str, fork_id: str, turn_number: int
) -> GameState | None:
    """Load game state from a fork's checkpoint file.

    Story 12.2: Fork Management UI (FR82).

    Args:
        session_id: Session ID string.
        fork_id: Fork ID string.
        turn_number: Turn number to load.

    Returns:
        Loaded GameState, or None if checkpoint doesn't exist or is invalid.
    """
    _validate_session_id(session_id)
    _validate_fork_id(fork_id)
    _validate_turn_number(turn_number)

    fork_dir = get_fork_dir(session_id, fork_id)
    checkpoint_path = fork_dir / f"turn_{turn_number:03d}.json"

    if not checkpoint_path.exists():
        return None

    try:
        json_content = checkpoint_path.read_text(encoding="utf-8")
        return deserialize_game_state(json_content)
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError, ValidationError):
        return None
```

#### 3. Fork-aware save routing (graph.py, modify run_single_round)

```python
# In run_single_round(), replace the existing save_checkpoint call:

# Auto-checkpoint: save after each round (FR33, NFR11)
if turn_number > 0:
    active_fork_id = result.get("active_fork_id")
    if active_fork_id is not None:
        # Fork-aware save: route to fork directory
        save_fork_checkpoint(result, session_id, active_fork_id, turn_number)
    else:
        # Main timeline save
        save_checkpoint(result, session_id, turn_number)
```

#### 4. Fork switching handler (app.py)

```python
def handle_switch_to_fork(session_id: str, fork_id: str) -> None:
    """Switch from current timeline to a fork.

    Story 12.2: Fork Management UI.
    Stops autopilot, loads fork's latest checkpoint, sets active_fork_id.

    Args:
        session_id: Session ID string.
        fork_id: Fork ID to switch to.
    """
    # Stop autopilot
    st.session_state["is_autopilot_running"] = False

    # Load fork metadata for display
    registry = load_fork_registry(session_id)
    if registry is None:
        st.error("Fork registry not found")
        return

    fork_meta = registry.get_fork(fork_id)
    if fork_meta is None:
        st.error(f"Fork '{fork_id}' not found")
        return

    # Get latest fork checkpoint
    latest_turn = get_latest_fork_checkpoint(session_id, fork_id)
    if latest_turn is None:
        st.error(f"Fork '{fork_meta.name}' has no checkpoints")
        return

    # Load the fork's state
    fork_state = load_fork_checkpoint(session_id, fork_id, latest_turn)
    if fork_state is None:
        st.error(f"Failed to load fork checkpoint at turn {latest_turn}")
        return

    # Set active_fork_id on the loaded state
    fork_state["active_fork_id"] = fork_id

    # Update session state
    st.session_state["game"] = fork_state
    safe_name = escape_html(fork_meta.name)
    st.toast(f"Switched to fork: {safe_name}")
```

#### 5. Return to main handler (app.py)

```python
def handle_return_to_main(session_id: str) -> None:
    """Return from a fork to the main timeline.

    Story 12.2: Fork Management UI.
    Saves fork progress, loads main timeline's latest checkpoint.

    Args:
        session_id: Session ID string.
    """
    # Stop autopilot
    st.session_state["is_autopilot_running"] = False

    game: GameState = st.session_state["game"]
    active_fork_id = game.get("active_fork_id")

    if active_fork_id is None:
        st.warning("Already on main timeline")
        return

    # Save current fork progress
    turn_number = len(game.get("ground_truth_log", []))
    if turn_number > 0:
        save_fork_checkpoint(game, session_id, active_fork_id, turn_number)

    # Load main timeline's latest checkpoint
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is None:
        st.error("Main timeline has no checkpoints")
        return

    main_state = load_checkpoint(session_id, latest_turn)
    if main_state is None:
        st.error(f"Failed to load main timeline checkpoint at turn {latest_turn}")
        return

    # Clear active_fork_id
    main_state["active_fork_id"] = None

    # Update session state
    st.session_state["game"] = main_state
    st.toast("Returned to main timeline")
```

#### 6. Fork list display in render_fork_controls (app.py)

```python
def render_fork_controls() -> None:
    """Render fork creation and management controls in the sidebar.

    Story 12.1: Fork Creation (FR81).
    Story 12.2: Fork Management UI (FR82).
    """
    if "game" not in st.session_state:
        return

    game: GameState = st.session_state["game"]
    session_id = game.get("session_id", "001")
    active_fork_id = game.get("active_fork_id")

    with st.expander("Fork Timeline", expanded=active_fork_id is not None):
        # "Return to Main" button (shown when playing in a fork)
        if active_fork_id is not None:
            registry = load_fork_registry(session_id)
            fork_name = "Unknown"
            if registry:
                fork_meta = registry.get_fork(active_fork_id)
                if fork_meta:
                    fork_name = fork_meta.name
            st.info(f"Playing fork: **{escape_html(fork_name)}**")
            if st.button("Return to Main", key="return_to_main_btn"):
                handle_return_to_main(session_id)
                st.rerun()
            st.markdown("---")

        # Create fork form (from Story 12.1)
        fork_name_input = st.text_input(
            "Fork name",
            placeholder="e.g., Diplomacy attempt",
            key="fork_name_input",
        )
        if st.button("Create Fork", key="create_fork_btn"):
            # ... existing create fork logic ...
            pass

        # Fork list display
        forks = list_forks(session_id)
        if forks:
            st.markdown("---")
            st.caption(f"**Forks ({len(forks)})**")
            for fork in forks:
                is_active = active_fork_id == fork.fork_id
                # Visual highlight for active fork
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        label = f"**{escape_html(fork.name)}**"
                        if is_active:
                            label += " (active)"
                        st.markdown(label)
                        st.caption(
                            f"Branched at turn {fork.branch_turn} | "
                            f"Turns: {fork.turn_count} | "
                            f"Last: {fork.updated_at[:16].replace('T', ' ')}"
                        )
                    with col2:
                        if not is_active:
                            if st.button(
                                "Switch",
                                key=f"switch_fork_{fork.fork_id}",
                            ):
                                handle_switch_to_fork(session_id, fork.fork_id)
                                st.rerun()

                    # Management actions
                    with st.popover("...", use_container_width=False):
                        # Rename
                        new_name = st.text_input(
                            "Rename",
                            value=fork.name,
                            key=f"rename_fork_{fork.fork_id}",
                        )
                        if st.button("Save", key=f"save_rename_{fork.fork_id}"):
                            try:
                                rename_fork(session_id, fork.fork_id, new_name)
                                st.toast(f"Fork renamed to '{escape_html(new_name)}'")
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))

                        # Delete
                        if not is_active:
                            if st.button(
                                "Delete",
                                key=f"delete_fork_{fork.fork_id}",
                                type="secondary",
                            ):
                                st.session_state[f"confirm_delete_{fork.fork_id}"] = True
                            if st.session_state.get(f"confirm_delete_{fork.fork_id}"):
                                st.warning(f"Delete '{fork.name}'? Cannot be undone.")
                                if st.button("Confirm Delete", key=f"confirm_del_{fork.fork_id}"):
                                    delete_fork(session_id, fork.fork_id)
                                    st.toast(f"Fork '{fork.name}' deleted")
                                    st.rerun()
                        else:
                            st.caption("Cannot delete active fork")

                        # Make Primary (placeholder for Story 12.4)
                        if st.button("Make Primary", key=f"promote_fork_{fork.fork_id}"):
                            st.info("Promote to main timeline (coming in Story 12.4)")
```

#### 7. rename_fork and delete_fork (persistence.py)

```python
def rename_fork(session_id: str, fork_id: str, new_name: str) -> ForkMetadata:
    """Rename a fork in the registry.

    Story 12.2: Fork Management UI (FR82).

    Args:
        session_id: Session ID string.
        fork_id: Fork ID to rename.
        new_name: New fork name.

    Returns:
        Updated ForkMetadata.

    Raises:
        ValueError: If new_name is empty/whitespace or fork not found.
    """
    if not new_name or not new_name.strip():
        raise ValueError("Fork name must not be empty or whitespace-only")

    registry = load_fork_registry(session_id)
    if registry is None:
        raise ValueError(f"No fork registry found for session {session_id!r}")

    fork = registry.get_fork(fork_id)
    if fork is None:
        raise ValueError(f"Fork {fork_id!r} not found in session {session_id!r}")

    fork.name = new_name.strip()
    fork.updated_at = datetime.now(UTC).isoformat() + "Z"
    save_fork_registry(session_id, registry)

    return fork


def delete_fork(
    session_id: str, fork_id: str, active_fork_id: str | None = None
) -> bool:
    """Delete a fork's directory and remove it from the registry.

    Story 12.2: Fork Management UI (FR82).

    Args:
        session_id: Session ID string.
        fork_id: Fork ID to delete.
        active_fork_id: Currently active fork ID (safety check).

    Returns:
        True if fork was deleted, False if not found.

    Raises:
        ValueError: If attempting to delete the currently active fork.
    """
    import shutil

    _validate_session_id(session_id)
    _validate_fork_id(fork_id)

    if active_fork_id is not None and active_fork_id == fork_id:
        raise ValueError("Cannot delete the currently active fork")

    registry = load_fork_registry(session_id)
    if registry is None:
        return False

    fork = registry.get_fork(fork_id)
    if fork is None:
        return False

    # Remove fork directory
    fork_dir = get_fork_dir(session_id, fork_id)
    if fork_dir.exists():
        shutil.rmtree(fork_dir)

    # Remove from registry
    registry.forks = [f for f in registry.forks if f.fork_id != fork_id]
    save_fork_registry(session_id, registry)

    return True
```

### Key Design Decisions

1. **Fork-aware checkpoint routing in graph.py:** The most critical change is making `run_single_round()` check `active_fork_id` to determine where to save checkpoints. This is a one-line conditional that routes to `save_fork_checkpoint()` vs `save_checkpoint()`. This keeps the fork mechanism transparent to the rest of the game loop.

2. **Separate save/load functions for forks:** Rather than overloading `save_checkpoint()` / `load_checkpoint()` with fork logic, dedicated `save_fork_checkpoint()` / `load_fork_checkpoint()` functions keep the API explicit and avoid changing the signatures of functions used everywhere.

3. **Fork switching stops autopilot:** Switching forks is a disruptive operation that changes the entire game state. Autopilot must be stopped to prevent the old state from being used after the switch. The user can restart autopilot after switching.

4. **Save before returning to main:** When the user clicks "Return to Main", the current fork's progress is saved first. This ensures no work is lost. The fork's latest checkpoint is always up-to-date.

5. **Delete safety check:** Cannot delete a fork while it is the active fork. The user must return to main first. This prevents the game from being in an inconsistent state (playing a fork that no longer exists).

6. **Make Primary is a placeholder:** The "Make Primary" button is visible (to satisfy the AC about fork management options) but deferred to Story 12.4. It shows an informational message rather than being hidden, so users know the feature is coming.

7. **Popover for management actions:** Using `st.popover` (Streamlit 1.40+) for Rename/Delete/Make Primary keeps the fork list clean. The "..." button opens a popover with contextual actions. This is a Streamlit-native pattern that avoids right-click menus (which Streamlit does not support).

8. **ForkMetadata.turn_count updated on save:** Each `save_fork_checkpoint()` recalculates `turn_count` from the actual number of checkpoint files in the fork directory (minus 1 for the initial branch point copy). This is more reliable than incrementing a counter, which could drift if saves fail.

9. **Fork Timeline expander auto-expands when in fork:** When `active_fork_id` is set, the Fork Timeline expander opens by default. This makes the "Return to Main" button immediately visible and reinforces that the user is in a fork.

10. **Fork indicator near session header:** The fork mode badge ("Fork: [name]") should be prominently displayed near the session info area at the top of the sidebar, not buried inside an expander. This ensures the user always knows they are in a fork.

### Test Strategy

**Test file:** `tests/test_story_12_2_fork_management_ui.py`

**Fixture pattern (follow existing test_persistence.py):**

```python
import pytest
from pathlib import Path
from collections.abc import Generator
from unittest.mock import patch

from models import (
    ForkMetadata,
    ForkRegistry,
    GameState,
    create_initial_game_state,
)
from persistence import (
    CAMPAIGNS_DIR,
    create_fork,
    delete_fork,
    get_fork_dir,
    get_latest_fork_checkpoint,
    list_fork_checkpoints,
    list_forks,
    load_fork_checkpoint,
    load_fork_registry,
    rename_fork,
    save_checkpoint,
    save_fork_checkpoint,
    save_fork_registry,
    load_checkpoint,
    get_latest_checkpoint,
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
def session_with_fork(
    temp_campaigns_dir: Path, sample_game_state: GameState
) -> tuple[str, str]:
    """Create a session with a checkpoint and a fork, return (session_id, fork_id)."""
    session_id = "001"
    save_checkpoint(sample_game_state, session_id, 1)
    fork_meta = create_fork(
        state=sample_game_state,
        session_id=session_id,
        fork_name="Test Fork",
    )
    return session_id, fork_meta.fork_id
```

**Unit Tests:**

- `save_fork_checkpoint()`: saves to correct path, atomic write, round-trip with `load_fork_checkpoint()`, updates registry metadata
- `load_fork_checkpoint()`: returns None for missing file, returns None for invalid JSON, loads valid checkpoint correctly
- `list_fork_checkpoints()`: returns sorted turns, empty list for empty/missing dir, ignores non-turn files
- `get_latest_fork_checkpoint()`: returns highest turn number, None for empty fork
- `rename_fork()`: updates name in registry, rejects empty names, ValueError for missing fork
- `delete_fork()`: removes directory and registry entry, returns False for missing fork, raises ValueError for active fork, preserves other forks

**Integration Tests:**

- Full switching flow: create fork -> save fork checkpoint -> switch to fork -> verify state -> return to main -> verify main state restored
- Fork-aware game loop routing: mock `run_single_round` to verify save goes to fork dir when `active_fork_id` set
- Multiple forks: create two forks, switch between them, verify each maintains independent state
- Registry consistency: after rename, delete, and save operations, registry remains valid and loadable

**Edge Cases:**

- Switch to fork with only the initial branch checkpoint (turn_count=0)
- Return to main when fork has unsaved changes
- Delete last fork: forks.yaml should have empty list
- Rename to same name (should succeed, just update timestamp)

### Important Constraints

- **Scope boundary:** This story covers fork switching, return to main, list display, rename, delete, and mode indicator. Fork comparison (side-by-side) is Story 12.3. Fork promotion/resolution is Story 12.4.
- **Make Primary is a placeholder only:** The button exists to satisfy the AC about management options, but the implementation is deferred. It shows an info message, not an error.
- **Autopilot must stop on switch:** Fork switching changes the entire game state. Running autopilot during or after a switch with stale state would cause data corruption.
- **No new dependencies:** Uses only existing imports (Streamlit, Path, yaml, json, shutil, datetime, Pydantic).
- **Backward compatibility:** Sessions without forks continue to work. The `active_fork_id is None` path in `run_single_round()` is the existing behavior.
- **Atomic writes:** All checkpoint saves (both main and fork) use the temp file + rename pattern for crash safety.
- **Path security:** Fork IDs continue to be validated with `_validate_fork_id()` for path traversal prevention.
- **Streamlit session state:** All fork state lives in `st.session_state["game"]["active_fork_id"]`. No additional session state keys needed for tracking fork context (fork info is derived from the game state and registry).
- **graph.py changes are minimal:** Only the checkpoint save routing changes. The graph nodes, agent logic, and turn pipeline are unaware of forks. This is by design -- forks are a persistence/UI concern, not a game logic concern.
