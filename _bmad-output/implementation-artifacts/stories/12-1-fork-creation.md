# Story 12-1: Fork Creation

## Story

As a **user**,
I want **to create a fork (branch point) from the current game state**,
So that **I can explore alternate story paths**.

## Status

**Status:** review
**Epic:** 12 - Fork Gameplay
**Created:** 2026-02-07
**FRs Covered:** FR81 (user can create a fork from current state)
**Predecessors:** Story 4.1 (Auto-Checkpoint System) - DONE, Story 4.3 (Session Metadata) - DONE

## Acceptance Criteria

**Given** an active game session
**When** I click "Create Fork"
**Then** the current state is saved as a branch point

**Given** the fork creation
**When** prompted
**Then** I can name the fork (e.g., "Diplomacy attempt", "Fight the dragon")

**Given** a fork is created
**When** confirmed
**Then** it creates a new session directory: `campaigns/session_001/forks/fork_001/`
**And** copies the current checkpoint as the fork's starting point

**Given** I continue playing after creating a fork
**When** generating turns
**Then** the main timeline continues normally
**And** the fork is available to switch to

**Given** multiple forks
**When** created from the same point
**Then** each is tracked independently

## Context: What Already Exists

### models.py (existing)
- `GameState` TypedDict with all game state fields
- `SessionMetadata` Pydantic model for session tracking (session_id, session_number, name, created_at, updated_at, character_names, turn_count)
- `create_initial_game_state()` and `populate_game_state()` factory functions
- All Pydantic models for embedded state: `AgentMemory`, `GameConfig`, `DMConfig`, `CharacterConfig`, `AgentSecrets`, `NarrativeElementStore`, `CallbackLog`, `CharacterSheet`

### persistence.py (existing)
- `CAMPAIGNS_DIR` constant: `Path(__file__).parent / "campaigns"`
- `_validate_session_id()` for path traversal protection
- `format_session_id(session_number)` -> zero-padded string
- `get_session_dir(session_id)` -> `CAMPAIGNS_DIR / f"session_{session_id}"`
- `ensure_session_dir(session_id)` -> creates directory if needed
- `get_checkpoint_path(session_id, turn_number)` -> path to turn JSON
- `save_checkpoint(state, session_id, turn_number)` -> atomic write with temp file + rename
- `load_checkpoint(session_id, turn_number)` -> returns `GameState | None`
- `serialize_game_state(state)` / `deserialize_game_state(json_str)` for full state round-trip
- `list_checkpoints(session_id)` -> sorted list of turn numbers
- `get_latest_checkpoint(session_id)` -> latest turn number or None
- `SessionMetadata` and `save_session_metadata()` / `load_session_metadata()`
- `create_new_session()` -> creates directory + config.yaml
- `list_sessions()` -> all session IDs
- `CheckpointInfo` model for lightweight checkpoint metadata
- `get_checkpoint_info()` and `list_checkpoint_info()` for UI browser

### app.py (existing)
- Streamlit UI with sidebar controls (party panel, mode controls, game controls)
- Session state management via `st.session_state`
- Session browser for listing and loading sessions
- "Create Fork" button does not yet exist

## What Story 12.1 Changes

This story adds **fork creation** -- the ability to branch the current game state into a named fork stored in a subdirectory. Specifically:

1. **New model `ForkMetadata`** in models.py: Tracks a single fork's identity and state (id, name, parent session, branch turn, created timestamp).
2. **New model `ForkRegistry`** in models.py: Container for all forks belonging to a session, stored in `forks.yaml` in the session directory.
3. **New field `active_fork_id: str | None`** on `GameState`: Tracks whether the player is currently playing in a fork (None = main timeline).
4. **New persistence functions** in persistence.py: `create_fork()`, `get_fork_dir()`, `list_forks()`, `load_fork_registry()`, `save_fork_registry()`.
5. **UI: "Create Fork" button** in app.py sidebar: Opens a dialog to name the fork and triggers fork creation.

The fork directory structure is:
```
campaigns/session_001/
  turn_001.json
  turn_002.json
  turn_003.json          <-- branch point
  config.yaml
  forks.yaml             <-- fork registry (NEW)
  forks/
    fork_001/            <-- first fork
      turn_003.json      <-- copy of branch point
      config.yaml        <-- fork metadata
    fork_002/            <-- second fork from same or different point
      turn_005.json
      config.yaml
```

## Tasks

### 1. Add ForkMetadata Model (models.py)

1. [x] Add `ForkMetadata` Pydantic model to models.py
   - Fields:
     - `fork_id: str` - Unique fork identifier (e.g., "001", "002"), zero-padded 3 digits
     - `name: str` - User-provided fork name (e.g., "Diplomacy attempt")
     - `parent_session_id: str` - Session ID this fork belongs to
     - `branch_turn: int` - Turn number where the fork was created (the branch point)
     - `created_at: str` - ISO timestamp when fork was created
     - `updated_at: str` - ISO timestamp of last checkpoint in this fork
     - `turn_count: int` - Number of turns played in this fork (starts at 0, since the initial checkpoint is the branch point copy)
   - Validators:
     - `fork_id` must be non-empty (min_length=1)
     - `name` must be non-empty and non-whitespace
     - `branch_turn >= 0`
     - `turn_count >= 0`
   - Docstring referencing Story 12.1, FR81
2. [x] Add `ForkMetadata` to `__all__` exports in models.py

### 2. Add ForkRegistry Model (models.py)

3. [x] Add `ForkRegistry` Pydantic model to models.py
   - Fields:
     - `session_id: str` - Parent session ID
     - `forks: list[ForkMetadata]` - All forks for this session
   - Methods:
     - `get_fork(fork_id: str) -> ForkMetadata | None` - Lookup fork by ID
     - `get_forks_at_turn(turn_number: int) -> list[ForkMetadata]` - All forks branching from a specific turn
     - `next_fork_id() -> str` - Returns next available zero-padded fork ID (e.g., "001", "002")
     - `add_fork(fork: ForkMetadata) -> None` - Append a fork to the registry
   - Docstring referencing Story 12.1, FR81
4. [x] Add `ForkRegistry` to `__all__` exports in models.py

### 3. Add active_fork_id to GameState (models.py)

5. [x] Add `active_fork_id: str | None` field to `GameState` TypedDict
   - None means the player is on the main timeline
   - When set, indicates the fork currently being played
6. [x] Update `create_initial_game_state()` to initialize `active_fork_id=None`
7. [x] Update `populate_game_state()` to initialize `active_fork_id=None`

### 4. Update Serialization (persistence.py)

8. [x] Update `serialize_game_state()` to serialize `active_fork_id`
   - Pattern: `"active_fork_id": state.get("active_fork_id", None)`
9. [x] Update `deserialize_game_state()` to reconstruct `active_fork_id`
   - Backward compatible: old checkpoints without `active_fork_id` default to `None`
   - Pattern: `active_fork_id=data.get("active_fork_id", None)`
10. [x] Add `ForkMetadata`, `ForkRegistry` to imports from models in persistence.py

### 5. Add Fork Persistence Functions (persistence.py)

11. [x] Add `_validate_fork_id(fork_id: str) -> None` helper
    - Validate fork_id to prevent path traversal (alphanumeric + underscore only, matching `_validate_session_id` pattern)

12. [x] Add `get_fork_dir(session_id: str, fork_id: str) -> Path` function
    - Returns: `get_session_dir(session_id) / "forks" / f"fork_{fork_id}"`
    - Validates both session_id and fork_id

13. [x] Add `ensure_fork_dir(session_id: str, fork_id: str) -> Path` function
    - Creates `forks/fork_{fork_id}/` directory under the session directory
    - Returns the fork directory path
    - Uses `mkdir(parents=True, exist_ok=True)` pattern

14. [x] Add `get_fork_registry_path(session_id: str) -> Path` function
    - Returns: `get_session_dir(session_id) / "forks.yaml"`

15. [x] Add `save_fork_registry(session_id: str, registry: ForkRegistry) -> Path` function
    - Serialize ForkRegistry to YAML using `yaml.safe_dump()`
    - Atomic write pattern (temp file + rename), matching `save_session_metadata()` pattern
    - Returns path where registry was saved

16. [x] Add `load_fork_registry(session_id: str) -> ForkRegistry | None` function
    - Load from `forks.yaml` in session directory
    - Returns None if file doesn't exist or is invalid
    - Backward compatible: old sessions without forks.yaml return None
    - Graceful error handling (yaml errors, validation errors)

17. [x] Add `create_fork(state: GameState, session_id: str, fork_name: str, turn_number: int | None = None) -> ForkMetadata` function
    - Core fork creation logic:
      1. Load or create ForkRegistry for the session
      2. Generate next fork_id via `registry.next_fork_id()`
      3. Determine branch turn: use `turn_number` if provided, otherwise use `get_latest_checkpoint(session_id)` or current turn from state
      4. Create ForkMetadata with name, parent_session_id, branch_turn, timestamps
      5. Create fork directory via `ensure_fork_dir()`
      6. Copy the branch point checkpoint into the fork directory (load it and save as `turn_{branch_turn}.json` in fork dir)
      7. Add fork to registry and save registry
      8. Return the ForkMetadata
    - Raises ValueError if session has no checkpoints to branch from
    - Raises ValueError if fork_name is empty/whitespace

18. [x] Add `list_forks(session_id: str) -> list[ForkMetadata]` function
    - Load fork registry and return all forks, sorted by creation time
    - Returns empty list if no forks exist

19. [x] Add new functions to `__all__` exports in persistence.py:
    - `create_fork`, `get_fork_dir`, `ensure_fork_dir`, `list_forks`, `load_fork_registry`, `save_fork_registry`, `get_fork_registry_path`

### 6. Add "Create Fork" UI (app.py)

20. [x] Add "Create Fork" button in the sidebar game controls section
    - Only visible when a game session is active (`"game" in st.session_state`)
    - Button label: "Create Fork" with a branch/fork icon indicator
    - Clicking opens a dialog/form for naming the fork

21. [x] Add fork creation dialog
    - Text input for fork name with placeholder: "e.g., Diplomacy attempt"
    - "Create" and "Cancel" buttons
    - On "Create":
      1. Validate fork name is not empty
      2. Get current game state and session_id from `st.session_state`
      3. Determine current turn number from the game state or latest checkpoint
      4. Call `create_fork()` from persistence
      5. Show success message: "Fork '[name]' created at turn [N]"
    - On "Cancel": dismiss the dialog
    - Error handling: show error message if fork creation fails

22. [x] Add fork indicator in sidebar
    - When forks exist for the current session, show a small "Forks: N" badge near the session info
    - This is a lightweight indicator; full fork management UI is Story 12.2

### 7. Tests

23. [x] Test `ForkMetadata` model validation
    - Valid construction with all required fields
    - Default values correct (turn_count=0)
    - Empty name rejected (min_length=1 + whitespace validator)
    - fork_id min_length=1 validation
    - branch_turn >= 0 validation
    - turn_count >= 0 validation

24. [x] Test `ForkRegistry` model and methods
    - `get_fork()` returns correct fork by ID, None for missing
    - `get_forks_at_turn()` filters forks by branch turn
    - `next_fork_id()` returns "001" for empty registry, "002" after one fork, etc.
    - `add_fork()` appends to forks list
    - Empty registry returns empty lists for queries

25. [x] Test `active_fork_id` on GameState
    - `create_initial_game_state()` has `active_fork_id=None`
    - `populate_game_state()` has `active_fork_id=None`
    - Serialization round-trip preserves `active_fork_id`
    - Backward compatibility: old checkpoints without `active_fork_id` default to None

26. [x] Test `_validate_fork_id()` helper
    - Valid IDs pass: "001", "002", "abc_123"
    - Path traversal rejected: "../etc", "..", "", special characters

27. [x] Test `get_fork_dir()` path construction
    - Returns correct path: `campaigns/session_001/forks/fork_001/`
    - Validates both session_id and fork_id

28. [x] Test `ensure_fork_dir()` directory creation
    - Creates directory if it doesn't exist
    - No error if directory already exists
    - Creates intermediate `forks/` parent directory

29. [x] Test `save_fork_registry()` / `load_fork_registry()` round-trip
    - Save and load preserves all ForkMetadata fields
    - Load returns None for missing file
    - Load returns None for invalid YAML
    - Load returns None for invalid schema (ValidationError)

30. [x] Test `create_fork()` function
    - Creates fork directory under `forks/fork_001/`
    - Copies branch point checkpoint into fork directory
    - Fork checkpoint is a valid, loadable GameState
    - ForkMetadata has correct fields (name, branch_turn, timestamps)
    - Registry is updated with new fork
    - Multiple forks get sequential IDs: "001", "002", "003"
    - Error on empty/whitespace fork name
    - Error on session with no checkpoints
    - Fork from specific turn number (not just latest)
    - Original session files are not modified (main timeline unaffected)

31. [x] Test `list_forks()` function
    - Returns empty list for session with no forks
    - Returns all forks sorted by creation time
    - Returns empty list for non-existent session

32. [x] Test serialization backward compatibility
    - Deserializing old checkpoint (no `active_fork_id`) yields `active_fork_id=None`
    - Serializing state with `active_fork_id=None` produces valid JSON
    - Serializing state with `active_fork_id="001"` round-trips correctly

33. [x] Test fork isolation
    - Creating a fork does not modify the main timeline's checkpoints
    - Main session continues saving checkpoints normally after fork creation
    - Fork checkpoint is an independent copy (modifying it does not affect source)

## Dependencies

- **Story 4.1** (done): Provides checkpoint save/load, serialization patterns, atomic writes
- **Story 4.3** (done): Provides SessionMetadata, session management patterns
- **Story 4.2** (done): Provides CheckpointInfo for checkpoint metadata

## Dev Notes

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `models.py` | Modify | Add `ForkMetadata`, `ForkRegistry` models, add `active_fork_id` to `GameState`, update factory functions, update `__all__` |
| `persistence.py` | Modify | Add fork persistence functions: `create_fork()`, `get_fork_dir()`, `ensure_fork_dir()`, `list_forks()`, `save_fork_registry()`, `load_fork_registry()`, fork_id validation, update serialization for `active_fork_id`, update `__all__` |
| `app.py` | Modify | Add "Create Fork" button and dialog in sidebar, fork count indicator |
| `tests/test_story_12_1_fork_creation.py` | Create | Comprehensive unit and integration tests |

### Code Patterns to Follow

#### 1. ForkMetadata Model (follow SessionMetadata pattern in models.py)

```python
class ForkMetadata(BaseModel):
    """Metadata for a game state fork (alternate timeline).

    Tracks a single fork's identity and state within a session.
    Forks branch from a specific turn and maintain independent
    checkpoint histories.

    Story 12.1: Fork Creation.
    FR81: User can create a fork from current state.

    Attributes:
        fork_id: Unique fork identifier (zero-padded, e.g., "001").
        name: User-provided fork name (e.g., "Diplomacy attempt").
        parent_session_id: Session ID this fork belongs to.
        branch_turn: Turn number where the fork was created.
        created_at: ISO timestamp when fork was created.
        updated_at: ISO timestamp of last fork checkpoint.
        turn_count: Number of turns played in this fork beyond branch point.
    """

    fork_id: str = Field(..., min_length=1, description="Fork identifier (zero-padded)")
    name: str = Field(..., min_length=1, description="User-provided fork name")
    parent_session_id: str = Field(
        ..., min_length=1, description="Parent session ID"
    )
    branch_turn: int = Field(..., ge=0, description="Turn number at branch point")
    created_at: str = Field(..., description="ISO timestamp when fork was created")
    updated_at: str = Field(..., description="ISO timestamp of last checkpoint")
    turn_count: int = Field(
        default=0, ge=0, description="Turns played beyond branch point"
    )

    @field_validator("name")
    @classmethod
    def name_not_whitespace(cls, v: str) -> str:
        """Validate that name is not empty or whitespace-only."""
        if not v.strip():
            raise ValueError("name must not be empty or whitespace-only")
        return v
```

#### 2. ForkRegistry Model (follow container patterns like NarrativeElementStore)

```python
class ForkRegistry(BaseModel):
    """Registry of all forks for a game session.

    Stored as forks.yaml in the session directory. Tracks all
    alternate timelines branching from the main session.

    Story 12.1: Fork Creation.
    FR81: User can create a fork from current state.

    Attributes:
        session_id: Parent session ID.
        forks: List of all fork metadata for this session.
    """

    session_id: str = Field(..., min_length=1, description="Parent session ID")
    forks: list[ForkMetadata] = Field(
        default_factory=list, description="All forks for this session"
    )

    def get_fork(self, fork_id: str) -> ForkMetadata | None:
        """Lookup a fork by its ID."""
        for fork in self.forks:
            if fork.fork_id == fork_id:
                return fork
        return None

    def get_forks_at_turn(self, turn_number: int) -> list[ForkMetadata]:
        """Get all forks branching from a specific turn."""
        return [f for f in self.forks if f.branch_turn == turn_number]

    def next_fork_id(self) -> str:
        """Return the next available zero-padded fork ID."""
        if not self.forks:
            return "001"
        max_id = max(int(f.fork_id) for f in self.forks)
        return f"{max_id + 1:03d}"

    def add_fork(self, fork: ForkMetadata) -> None:
        """Add a fork to the registry."""
        self.forks.append(fork)
```

#### 3. GameState Enhancement (models.py)

Add `active_fork_id` field to `GameState` TypedDict:

```python
class GameState(TypedDict):
    # ... existing fields ...
    callback_log: "CallbackLog"
    active_fork_id: str | None  # Story 12.1: None = main timeline
```

Update factory functions:

```python
# In create_initial_game_state():
active_fork_id=None,

# In populate_game_state():
active_fork_id=None,
```

#### 4. Fork Persistence (persistence.py)

Follow the existing patterns in persistence.py for session management:

```python
def _validate_fork_id(fork_id: str) -> None:
    """Validate fork_id to prevent path traversal attacks."""
    if not fork_id or not fork_id.replace("_", "").isalnum():
        raise ValueError(
            f"Invalid fork_id: {fork_id!r}. "
            "Must be alphanumeric (underscores allowed)."
        )


def get_fork_dir(session_id: str, fork_id: str) -> Path:
    """Get path to fork directory."""
    _validate_session_id(session_id)
    _validate_fork_id(fork_id)
    return get_session_dir(session_id) / "forks" / f"fork_{fork_id}"


def ensure_fork_dir(session_id: str, fork_id: str) -> Path:
    """Ensure fork directory exists, create if needed."""
    fork_dir = get_fork_dir(session_id, fork_id)
    fork_dir.mkdir(parents=True, exist_ok=True)
    return fork_dir


def get_fork_registry_path(session_id: str) -> Path:
    """Get path to fork registry (forks.yaml) for a session."""
    return get_session_dir(session_id) / "forks.yaml"


def save_fork_registry(session_id: str, registry: ForkRegistry) -> Path:
    """Save fork registry to forks.yaml in session directory.

    Uses atomic write pattern (temp file + rename).
    """
    ensure_session_dir(session_id)
    registry_path = get_fork_registry_path(session_id)

    data = registry.model_dump()
    yaml_content = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)

    # Atomic write pattern (matching save_session_metadata)
    temp_path = registry_path.with_suffix(".yaml.tmp")
    try:
        temp_path.write_text(yaml_content, encoding="utf-8")
        temp_path.replace(registry_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return registry_path


def load_fork_registry(session_id: str) -> ForkRegistry | None:
    """Load fork registry from forks.yaml.

    Returns None if file doesn't exist or is invalid.
    Backward compatible: old sessions without forks return None.
    """
    registry_path = get_fork_registry_path(session_id)

    if not registry_path.exists():
        return None

    try:
        yaml_content = registry_path.read_text(encoding="utf-8")
        data = yaml.safe_load(yaml_content)
        return ForkRegistry(**data)
    except (yaml.YAMLError, TypeError, ValidationError):
        return None


def create_fork(
    state: GameState,
    session_id: str,
    fork_name: str,
    turn_number: int | None = None,
) -> ForkMetadata:
    """Create a fork (branch point) from the current game state.

    Story 12.1: Fork Creation.
    FR81: User can create a fork from current state.

    1. Loads or creates ForkRegistry for the session
    2. Generates next fork_id
    3. Determines branch turn
    4. Creates fork directory
    5. Copies branch checkpoint into fork directory
    6. Saves registry

    Args:
        state: Current game state.
        session_id: Session ID to fork from.
        fork_name: User-provided name for the fork.
        turn_number: Specific turn to branch from (default: latest checkpoint).

    Returns:
        ForkMetadata for the created fork.

    Raises:
        ValueError: If fork_name is empty or session has no checkpoints.
    """
    # Validate fork name
    if not fork_name or not fork_name.strip():
        raise ValueError("Fork name must not be empty or whitespace-only")

    # Determine branch turn
    if turn_number is None:
        turn_number = get_latest_checkpoint(session_id)
        if turn_number is None:
            raise ValueError(
                f"Session {session_id!r} has no checkpoints to branch from"
            )

    # Load or create fork registry
    registry = load_fork_registry(session_id)
    if registry is None:
        registry = ForkRegistry(session_id=session_id)

    # Generate fork ID
    fork_id = registry.next_fork_id()

    # Create fork directory
    ensure_fork_dir(session_id, fork_id)

    # Copy branch point checkpoint into fork directory
    # Load the source checkpoint
    source_state = load_checkpoint(session_id, turn_number)
    if source_state is None:
        raise ValueError(
            f"Checkpoint at turn {turn_number} not found in session {session_id!r}"
        )

    # Save as the starting checkpoint in the fork directory
    fork_dir = get_fork_dir(session_id, fork_id)
    fork_checkpoint_path = fork_dir / f"turn_{turn_number:03d}.json"
    json_content = serialize_game_state(source_state)

    # Atomic write
    temp_fd, temp_path_str = tempfile.mkstemp(dir=fork_dir, suffix=".json.tmp")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(json_content)
        Path(temp_path_str).replace(fork_checkpoint_path)
    except Exception:
        Path(temp_path_str).unlink(missing_ok=True)
        raise

    # Create fork metadata
    now = datetime.now(UTC).isoformat() + "Z"
    fork_metadata = ForkMetadata(
        fork_id=fork_id,
        name=fork_name.strip(),
        parent_session_id=session_id,
        branch_turn=turn_number,
        created_at=now,
        updated_at=now,
        turn_count=0,
    )

    # Update and save registry
    registry.add_fork(fork_metadata)
    save_fork_registry(session_id, registry)

    return fork_metadata


def list_forks(session_id: str) -> list[ForkMetadata]:
    """List all forks for a session, sorted by creation time.

    Returns empty list if no forks exist.
    """
    registry = load_fork_registry(session_id)
    if registry is None:
        return []
    return sorted(registry.forks, key=lambda f: f.created_at)
```

#### 5. Serialization Updates (persistence.py)

Extend serialization following existing patterns:

```python
# In serialize_game_state():
"active_fork_id": state.get("active_fork_id", None),

# In deserialize_game_state():
active_fork_id=data.get("active_fork_id", None),
```

#### 6. UI Integration (app.py)

The "Create Fork" button should appear in the sidebar controls when a game is active. Use Streamlit's `st.popover` or `st.expander` for the naming dialog:

```python
# In sidebar game controls section:
if "game" in st.session_state:
    with st.expander("Fork Timeline"):
        fork_name = st.text_input(
            "Fork name",
            placeholder="e.g., Diplomacy attempt",
            key="fork_name_input",
        )
        if st.button("Create Fork", key="create_fork_btn"):
            if fork_name and fork_name.strip():
                game = st.session_state["game"]
                session_id = game.get("session_id", "001")
                try:
                    fork_meta = create_fork(
                        state=game,
                        session_id=session_id,
                        fork_name=fork_name,
                    )
                    st.success(
                        f"Fork '{fork_meta.name}' created at turn {fork_meta.branch_turn}"
                    )
                except ValueError as e:
                    st.error(str(e))
            else:
                st.warning("Please enter a fork name")

        # Show fork count indicator
        forks = list_forks(game.get("session_id", "001"))
        if forks:
            st.caption(f"Forks: {len(forks)}")
```

### Key Design Decisions

1. **Fork as a subdirectory, not a separate session:** Forks live inside the parent session's directory (`session_001/forks/fork_001/`). This keeps the relationship explicit and avoids polluting the top-level session list. The fork has its own checkpoint files but shares the parent's identity.

2. **ForkRegistry in YAML, not JSON:** Using YAML (like SessionMetadata's `config.yaml`) for consistency with the existing metadata pattern. The registry is a lightweight file that lists all forks for a session. YAML is human-readable and easy to inspect.

3. **Copy checkpoint, don't symlink:** The branch point checkpoint is physically copied into the fork directory. This ensures fork isolation -- modifying the fork's checkpoint history does not affect the main timeline. The cost is disk space, but checkpoints are small (typically < 100KB).

4. **active_fork_id on GameState:** Adding this field to GameState makes it trivial to know whether the current game is running in a fork or on the main timeline. Story 12.2 (Fork Management UI) will use this to show a "Fork: [name]" indicator and enable "Return to Main" functionality. For this story, it defaults to None and is not set during fork creation (creating a fork does not switch to it).

5. **Sequential fork IDs:** Fork IDs are zero-padded sequential numbers ("001", "002", "003"), matching the session ID pattern. This is simple, deterministic, and avoids collisions.

6. **Fork creation does not switch context:** When a fork is created, the user stays on the main timeline. The fork is available to switch to (Story 12.2). This matches the AC: "the main timeline continues normally and the fork is available to switch to."

7. **Branch turn flexibility:** `create_fork()` accepts an optional `turn_number` parameter. By default it uses the latest checkpoint, but callers can specify a specific turn to branch from. This supports future use cases like branching from history.

8. **Validation follows existing patterns:** `_validate_fork_id()` mirrors `_validate_session_id()` for path traversal prevention. The same alphanumeric-with-underscores rule applies.

9. **Backward compatibility:** Old checkpoints without `active_fork_id` deserialize to `None`. Old sessions without `forks.yaml` return `None` from `load_fork_registry()`. No migration needed.

10. **No LLM calls:** Fork creation is purely a persistence/state management operation. No LLM involvement needed.

### Test Strategy

**Test file:** `tests/test_story_12_1_fork_creation.py`

**Unit Tests:**

- `ForkMetadata` model: valid construction, default values, name validation (whitespace rejection), field constraints
- `ForkRegistry` model: `get_fork()`, `get_forks_at_turn()`, `next_fork_id()`, `add_fork()`, empty registry behavior
- `active_fork_id` on GameState: factory functions, serialization round-trip, backward compatibility

**Integration Tests (with temp directory):**

- `get_fork_dir()` path construction
- `ensure_fork_dir()` creates directory tree
- `save_fork_registry()` / `load_fork_registry()` round-trip
- `load_fork_registry()` returns None for missing/invalid files
- `create_fork()` end-to-end: directory creation, checkpoint copy, registry update
- `create_fork()` with multiple forks: sequential IDs, independent tracking
- `create_fork()` error cases: empty name, no checkpoints
- `list_forks()` returns sorted forks, empty list for no forks
- Fork isolation: main timeline checkpoints unaffected
- Fork checkpoint is independently loadable via `load_checkpoint`-style pattern

**Mock Pattern (follow existing test patterns):**

```python
import pytest
from pathlib import Path
from unittest.mock import patch
from collections.abc import Generator

from models import (
    ForkMetadata,
    ForkRegistry,
    create_initial_game_state,
)
from persistence import (
    CAMPAIGNS_DIR,
    create_fork,
    get_fork_dir,
    ensure_fork_dir,
    list_forks,
    load_fork_registry,
    save_fork_registry,
    save_checkpoint,
    load_checkpoint,
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
    """Reuse the existing sample_game_state pattern from test_persistence.py."""
    return create_initial_game_state()


def test_create_fork_basic(temp_campaigns_dir, sample_game_state):
    """Test basic fork creation flow."""
    session_id = "001"
    # Save a checkpoint first (need something to branch from)
    save_checkpoint(sample_game_state, session_id, 1)

    # Create fork
    fork = create_fork(
        state=sample_game_state,
        session_id=session_id,
        fork_name="Fight the dragon",
    )

    assert fork.fork_id == "001"
    assert fork.name == "Fight the dragon"
    assert fork.branch_turn == 1
    assert fork.parent_session_id == session_id

    # Verify fork directory exists
    fork_dir = get_fork_dir(session_id, "001")
    assert fork_dir.exists()

    # Verify checkpoint was copied
    fork_checkpoint = fork_dir / "turn_001.json"
    assert fork_checkpoint.exists()

    # Verify registry was saved
    registry = load_fork_registry(session_id)
    assert registry is not None
    assert len(registry.forks) == 1
    assert registry.forks[0].name == "Fight the dragon"
```

### Important Constraints

- **Scope boundary:** This story covers fork CREATION only. Fork switching, comparison, management UI, and resolution are Stories 12.2, 12.3, and 12.4 respectively.
- **Never block the game loop:** Fork creation is a user-initiated action (button click), not part of the turn pipeline. It should not affect turn generation or autopilot.
- **Immutable state:** `create_fork()` does not modify the input `state`. It reads it for serialization and copies the checkpoint. The returned `ForkMetadata` is a new object.
- **Backward compatibility:** Old sessions without fork support must continue to work. No migration needed.
- **No new dependencies:** Uses only existing imports (Path, yaml, json, os, tempfile, datetime, Pydantic).
- **Atomic writes:** All file operations use the temp file + rename pattern for crash safety, matching existing persistence patterns.
- **Path security:** Fork IDs are validated with the same rigor as session IDs to prevent path traversal attacks.
- **Disk space:** Checkpoints are typically < 100KB. Copying one per fork is negligible. If disk space becomes a concern, a future optimization could use hard links or delta encoding, but that is out of scope.
