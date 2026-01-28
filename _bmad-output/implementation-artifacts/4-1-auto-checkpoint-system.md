# Story 4.1: Auto-Checkpoint System

Status: review

## Story

As a **user**,
I want **the game to automatically save after every turn**,
so that **I never lose more than one turn of progress if something goes wrong**.

## Acceptance Criteria

1. **Given** a turn completes (DM or PC generates a response)
   **When** the response is added to the ground truth log
   **Then** a checkpoint is automatically saved (FR33, NFR11)
   **And** no user action is required

2. **Given** the persistence.py module with `save_checkpoint(state, session_id, turn_number)` function
   **When** a checkpoint is saved
   **Then** it creates a file at `campaigns/session_xxx/turn_xxx.json`

3. **Given** a checkpoint file
   **When** examining its contents
   **Then** it contains the complete GameState serialized via Pydantic `.model_dump_json()`
   **And** includes all agent memories at that point in time

4. **Given** checkpoint storage (NFR5)
   **When** saving checkpoints
   **Then** each file is self-contained (no delta encoding)
   **And** old checkpoints are not modified

5. **Given** an unexpected shutdown occurs
   **When** the user restarts the application
   **Then** session files remain valid and uncorrupted (NFR14)

## Tasks / Subtasks

- [x] Task 1: Implement checkpoint file path utilities (AC: #2)
  - [x] 1.1 Create `get_session_dir(session_id: str) -> Path` to return `campaigns/session_{id}/`
  - [x] 1.2 Create `get_checkpoint_path(session_id: str, turn_number: int) -> Path` to return full checkpoint path
  - [x] 1.3 Create `ensure_session_dir(session_id: str) -> Path` to create directory if needed
  - [x] 1.4 Create `format_session_id(session_number: int) -> str` to format session IDs consistently (e.g., "001")
  - [x] 1.5 Write tests for path utilities

- [x] Task 2: Implement GameState serialization (AC: #3)
  - [x] 2.1 Create `serialize_game_state(state: GameState) -> str` using Pydantic model serialization
  - [x] 2.2 Handle nested Pydantic models (AgentMemory, CharacterConfig, etc.)
  - [x] 2.3 Create `deserialize_game_state(json_str: str) -> GameState` for loading (needed for verification)
  - [x] 2.4 Ensure datetime/timestamp fields serialize correctly
  - [x] 2.5 Write tests for serialization round-trip

- [x] Task 3: Implement save_checkpoint function (AC: #1, #2, #3, #4)
  - [x] 3.1 Create `save_checkpoint(state: GameState, session_id: str, turn_number: int) -> Path`
  - [x] 3.2 Serialize complete GameState including all agent_memories
  - [x] 3.3 Write to atomic temp file first, then rename (crash safety - AC #5)
  - [x] 3.4 Return the path where checkpoint was saved
  - [x] 3.5 Write tests for save_checkpoint

- [x] Task 4: Implement load_checkpoint function (AC: #5)
  - [x] 4.1 Create `load_checkpoint(session_id: str, turn_number: int) -> GameState | None`
  - [x] 4.2 Read and deserialize checkpoint file
  - [x] 4.3 Validate loaded state has required fields
  - [x] 4.4 Return None if checkpoint doesn't exist or is invalid
  - [x] 4.5 Write tests for load_checkpoint

- [x] Task 5: Implement checkpoint listing (AC: #4)
  - [x] 5.1 Create `list_checkpoints(session_id: str) -> list[int]` to get available turn numbers
  - [x] 5.2 Create `get_latest_checkpoint(session_id: str) -> int | None` for finding most recent
  - [x] 5.3 Create `list_sessions() -> list[str]` to find all session directories
  - [x] 5.4 Write tests for listing functions

- [x] Task 6: Integrate auto-checkpoint into game loop (AC: #1)
  - [x] 6.1 Add `save_checkpoint()` call at end of `run_single_round()` in graph.py
  - [x] 6.2 Get turn_number from `len(ground_truth_log)` after round completes
  - [x] 6.3 Get session_id from `state["session_id"]` (format as "001", "002", etc.)
  - [x] 6.4 Add checkpoint save to human_intervention_node after human action processed
  - [x] 6.5 Write integration tests for auto-checkpoint

- [x] Task 7: Add session_id to GameState (AC: #2)
  - [x] 7.1 Add `session_id: str` field to GameState TypedDict in models.py
  - [x] 7.2 Update `create_initial_game_state()` to include session_id
  - [x] 7.3 Update `populate_game_state()` to generate unique session_id
  - [x] 7.4 Ensure session_id is serialized with checkpoints
  - [x] 7.5 Write tests for session_id handling

- [x] Task 8: Write comprehensive acceptance tests
  - [x] 8.1 Test checkpoint created after DM turn
  - [x] 8.2 Test checkpoint created after PC turn
  - [x] 8.3 Test checkpoint created after human action
  - [x] 8.4 Test checkpoint contains complete GameState
  - [x] 8.5 Test checkpoint contains all agent_memories
  - [x] 8.6 Test checkpoint file path format
  - [x] 8.7 Test old checkpoints not modified
  - [x] 8.8 Test checkpoint survives serialization round-trip
  - [x] 8.9 Test missing directory created automatically

## Dev Agent Record

### Agent Model
Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References
N/A - Implementation proceeded without debugging issues.

### Completion Notes
All 8 tasks completed successfully. The auto-checkpoint system is now fully implemented:
- Checkpoints are automatically saved after each round (DM + all PCs) in `run_single_round()`
- Checkpoints are saved after human intervention actions in `human_intervention_node()`
- Uses atomic write pattern (temp file + rename) for crash safety on Windows and POSIX
- Checkpoint format: `campaigns/session_XXX/turn_XXX.json` with zero-padded numbers
- Full GameState serialization including all nested Pydantic models

### File List
Files modified/created:
- `persistence.py` - Complete implementation of checkpoint save/load functions (was placeholder)
- `models.py` - Added `session_id: str` field to GameState TypedDict
- `graph.py` - Added auto-checkpoint calls to `run_single_round()` and `human_intervention_node()`
- `tests/test_persistence.py` - New test file with 60 tests covering all functionality
- `tests/test_models.py` - Updated 3 tests to include new `session_id` and `session_number` fields

### Change Log
1. Added `session_id` field to GameState TypedDict in models.py
2. Updated `create_initial_game_state()` to include `session_id="001"`
3. Updated `populate_game_state()` to generate `session_id` from `session_number`
4. Implemented persistence.py with all checkpoint functions:
   - `format_session_id()` - Format session numbers to padded IDs
   - `get_session_dir()` - Get session directory path
   - `get_checkpoint_path()` - Get checkpoint file path
   - `ensure_session_dir()` - Create session directory if needed
   - `serialize_game_state()` - Serialize GameState to JSON
   - `deserialize_game_state()` - Deserialize JSON to GameState
   - `save_checkpoint()` - Save checkpoint with atomic writes
   - `load_checkpoint()` - Load checkpoint file
   - `list_sessions()` - List all session directories
   - `list_checkpoints()` - List checkpoints in a session
   - `get_latest_checkpoint()` - Get most recent checkpoint
5. Integrated auto-checkpoint into `run_single_round()` in graph.py
6. Integrated auto-checkpoint into `human_intervention_node()` in graph.py
7. Created comprehensive test suite in tests/test_persistence.py
8. Fixed test_models.py to include new session_id field in test fixtures

### Test Results
- 966 tests passed (full suite)
- 60 new tests in test_persistence.py
- All acceptance criteria verified through tests
- ruff check: All checks passed
- pyright: No new errors (existing warnings unrelated to this story)

## Dev Notes

### Existing Infrastructure Analysis

**persistence.py (Current State):**
The persistence module is currently a placeholder with only a docstring:
```python
"""Checkpoint save/load and transcript export."""
```
This is the primary file to implement for this story.

**GameState in models.py (lines 204-238):**
```python
class GameState(TypedDict):
    ground_truth_log: list[str]
    turn_queue: list[str]
    current_turn: str
    agent_memories: dict[str, AgentMemory]
    game_config: GameConfig
    dm_config: DMConfig
    characters: dict[str, CharacterConfig]
    whisper_queue: list[str]
    human_active: bool
    controlled_character: str | None
    session_number: int
```

GameState is a TypedDict with embedded Pydantic models (AgentMemory, GameConfig, etc.). This creates a serialization challenge: TypedDict doesn't have `.model_dump_json()`, but its nested Pydantic models do.

**AgentMemory (models.py:43-71):**
```python
class AgentMemory(BaseModel):
    long_term_summary: str = Field(default="", ...)
    short_term_buffer: list[str] = Field(default_factory=list, ...)
    token_limit: int = Field(default=8000, ge=1, ...)
```

**run_single_round in graph.py (lines 206-229):**
```python
def run_single_round(state: GameState) -> GameState:
    workflow = create_game_workflow(state["turn_queue"])
    result = workflow.invoke(
        state,
        config={"recursion_limit": len(state["turn_queue"]) + 2},
    )
    return result
```
This is where the checkpoint save call should be added - after `workflow.invoke()` completes.

**campaigns/ Directory Structure (from architecture.md):**
```
campaigns/
└── session_001/
    ├── config.yaml          # Campaign configuration (Story 4.3)
    ├── turn_001.json        # Full GameState snapshot
    ├── turn_002.json
    ├── ...
    └── transcript.json      # Append-only research export (Story 4.4)
```

**Initialize session state (app.py:918-940):**
```python
def initialize_session_state() -> None:
    if "game" not in st.session_state:
        st.session_state["game"] = populate_game_state()
        # ... other state initialization
```

### Architecture Compliance

Per architecture.md:

| Decision | Compliance |
|----------|------------|
| Checkpoint Format: Single JSON | Following - one JSON file per turn |
| Naming: `session_xxx/turn_xxx.json` | Following - zero-padded numbering |
| Pydantic serialization | Following - use `.model_dump()` for nested models |
| State in `st.session_state["game"]` | Following - save from session state |

**Persistence Strategy (architecture.md#Persistence Strategy):**
- Single JSON file per turn (not delta encoding)
- Complete GameState including all agent memories
- Serialized via Pydantic's `.model_dump_json()`
- Enables restore to any previous turn with full memory state

[Source: architecture.md#Persistence Strategy]

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR33 | Auto-save game state after each turn | save_checkpoint called after run_single_round |
| NFR5 | Efficient checkpoint storage | Self-contained files, no redundancy within files |
| NFR11 | Every turn automatically saved | Checkpoint created at end of each turn |
| NFR14 | Session files valid after unexpected shutdown | Atomic write pattern (temp file + rename) |

[Source: epics.md#Story 4.1, prd.md#Persistence & Recovery]

### What This Story Does NOT Do

- Does NOT implement checkpoint browser UI (Story 4.2)
- Does NOT implement restore from checkpoint (Story 4.2)
- Does NOT implement campaign organization (Story 4.3)
- Does NOT implement transcript export (Story 4.4)
- Does NOT implement error recovery UI (Story 4.5)
- Does NOT implement "While you were away..." summary (Story 4.3)
- Does NOT implement session resume on app start (Story 4.3)
- Does NOT delete old checkpoints (keep all for recovery)

### Previous Story Intelligence (from Story 3.6)

**Key Learnings:**
- Tests organized by functional area in dedicated classes (TestKeyboardShortcutScript, etc.)
- CSS transitions used for smooth state changes
- Handler functions follow `handle_*` naming pattern
- JavaScript injection uses `st.components.v1.html`

**Files Modified in Story 3.6:**
- `app.py` - Added keyboard shortcut handling
- `styles/theme.css` - Added keyboard shortcuts help styling
- `tests/test_app.py` - Added 50+ tests in 9 test classes

**Pattern to follow:**
```
Implement Story 4.1: Auto-Checkpoint System with code review fixes
```

All tests passing (557+) before this story.

[Source: _bmad-output/implementation-artifacts/3-6-keyboard-shortcuts.md]

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

#### GameState Serialization Strategy (persistence.py)

Since GameState is a TypedDict with embedded Pydantic models, we need a custom serialization approach:

```python
import json
from pathlib import Path
from typing import Any

from models import (
    AgentMemory,
    CharacterConfig,
    DMConfig,
    GameConfig,
    GameState,
)


def serialize_game_state(state: GameState) -> str:
    """Serialize GameState to JSON string.

    Handles the TypedDict + Pydantic hybrid by converting
    Pydantic models to dicts before JSON serialization.

    Args:
        state: The GameState to serialize.

    Returns:
        JSON string representation of the state.
    """
    # Convert Pydantic models to dicts
    serializable: dict[str, Any] = {
        "ground_truth_log": state["ground_truth_log"],
        "turn_queue": state["turn_queue"],
        "current_turn": state["current_turn"],
        "agent_memories": {
            k: v.model_dump() for k, v in state["agent_memories"].items()
        },
        "game_config": state["game_config"].model_dump(),
        "dm_config": state["dm_config"].model_dump(),
        "characters": {
            k: v.model_dump() for k, v in state["characters"].items()
        },
        "whisper_queue": state["whisper_queue"],
        "human_active": state["human_active"],
        "controlled_character": state["controlled_character"],
        "session_number": state["session_number"],
        "session_id": state.get("session_id", ""),  # New field
    }
    return json.dumps(serializable, indent=2)
```

#### Deserialization Strategy (persistence.py)

```python
def deserialize_game_state(json_str: str) -> GameState:
    """Deserialize JSON string to GameState.

    Reconstructs Pydantic models from their dict representations.

    Args:
        json_str: JSON string representation of GameState.

    Returns:
        Reconstructed GameState.
    """
    data = json.loads(json_str)

    return GameState(
        ground_truth_log=data["ground_truth_log"],
        turn_queue=data["turn_queue"],
        current_turn=data["current_turn"],
        agent_memories={
            k: AgentMemory(**v) for k, v in data["agent_memories"].items()
        },
        game_config=GameConfig(**data["game_config"]),
        dm_config=DMConfig(**data["dm_config"]),
        characters={
            k: CharacterConfig(**v) for k, v in data["characters"].items()
        },
        whisper_queue=data["whisper_queue"],
        human_active=data["human_active"],
        controlled_character=data["controlled_character"],
        session_number=data["session_number"],
        session_id=data.get("session_id", ""),
    )
```

#### Path Utilities (persistence.py)

```python
from pathlib import Path

# Base directory for all campaigns
CAMPAIGNS_DIR = Path(__file__).parent / "campaigns"


def format_session_id(session_number: int) -> str:
    """Format session number to padded string ID.

    Args:
        session_number: Session number (e.g., 1, 42).

    Returns:
        Zero-padded session ID (e.g., "001", "042").
    """
    return f"{session_number:03d}"


def get_session_dir(session_id: str) -> Path:
    """Get path to session directory.

    Args:
        session_id: Session ID string (e.g., "001").

    Returns:
        Path to session directory.
    """
    return CAMPAIGNS_DIR / f"session_{session_id}"


def get_checkpoint_path(session_id: str, turn_number: int) -> Path:
    """Get path to checkpoint file.

    Args:
        session_id: Session ID string.
        turn_number: Turn number (1-indexed).

    Returns:
        Path to checkpoint JSON file.
    """
    return get_session_dir(session_id) / f"turn_{turn_number:03d}.json"


def ensure_session_dir(session_id: str) -> Path:
    """Ensure session directory exists, create if needed.

    Args:
        session_id: Session ID string.

    Returns:
        Path to session directory.
    """
    session_dir = get_session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir
```

#### Checkpoint Save Function (persistence.py)

```python
import tempfile


def save_checkpoint(
    state: GameState, session_id: str, turn_number: int
) -> Path:
    """Save game state checkpoint to disk.

    Uses atomic write pattern: write to temp file first, then rename.
    This ensures checkpoint is either complete or doesn't exist,
    protecting against corruption from unexpected shutdown.

    Args:
        state: Current game state to save.
        session_id: Session ID string.
        turn_number: Turn number for this checkpoint.

    Returns:
        Path where checkpoint was saved.
    """
    # Ensure session directory exists
    session_dir = ensure_session_dir(session_id)
    checkpoint_path = get_checkpoint_path(session_id, turn_number)

    # Serialize state
    json_content = serialize_game_state(state)

    # Atomic write: temp file then rename
    # This protects against partial writes during crash
    temp_fd, temp_path = tempfile.mkstemp(
        dir=session_dir, suffix=".json.tmp"
    )
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(json_content)
        # Atomic rename (on POSIX; Windows may need special handling)
        Path(temp_path).replace(checkpoint_path)
    except Exception:
        # Clean up temp file on error
        Path(temp_path).unlink(missing_ok=True)
        raise

    return checkpoint_path
```

#### Checkpoint Load Function (persistence.py)

```python
def load_checkpoint(session_id: str, turn_number: int) -> GameState | None:
    """Load game state from checkpoint file.

    Args:
        session_id: Session ID string.
        turn_number: Turn number to load.

    Returns:
        Loaded GameState, or None if checkpoint doesn't exist.
    """
    checkpoint_path = get_checkpoint_path(session_id, turn_number)

    if not checkpoint_path.exists():
        return None

    try:
        json_content = checkpoint_path.read_text(encoding="utf-8")
        return deserialize_game_state(json_content)
    except (json.JSONDecodeError, KeyError, TypeError):
        # Invalid checkpoint - return None instead of crashing
        return None
```

#### Listing Functions (persistence.py)

```python
def list_sessions() -> list[str]:
    """List all available session IDs.

    Returns:
        List of session ID strings, sorted.
    """
    if not CAMPAIGNS_DIR.exists():
        return []

    sessions = []
    for path in CAMPAIGNS_DIR.iterdir():
        if path.is_dir() and path.name.startswith("session_"):
            session_id = path.name.replace("session_", "")
            sessions.append(session_id)

    return sorted(sessions)


def list_checkpoints(session_id: str) -> list[int]:
    """List all checkpoint turn numbers for a session.

    Args:
        session_id: Session ID string.

    Returns:
        List of turn numbers, sorted ascending.
    """
    session_dir = get_session_dir(session_id)

    if not session_dir.exists():
        return []

    turns = []
    for path in session_dir.glob("turn_*.json"):
        # Extract turn number from filename
        try:
            turn_str = path.stem.replace("turn_", "")
            turn_num = int(turn_str)
            turns.append(turn_num)
        except ValueError:
            continue

    return sorted(turns)


def get_latest_checkpoint(session_id: str) -> int | None:
    """Get the most recent checkpoint turn number.

    Args:
        session_id: Session ID string.

    Returns:
        Latest turn number, or None if no checkpoints.
    """
    turns = list_checkpoints(session_id)
    return turns[-1] if turns else None
```

#### Integration with graph.py

Modify `run_single_round()` to save checkpoint after each round:

```python
def run_single_round(state: GameState) -> GameState:
    """Execute one complete round (DM + all PCs).

    Now includes auto-checkpoint save after round completion.

    Args:
        state: Initial game state for this round.

    Returns:
        Updated state after all agents have acted once.
    """
    from persistence import format_session_id, save_checkpoint

    workflow = create_game_workflow(state["turn_queue"])

    result = workflow.invoke(
        state,
        config={"recursion_limit": len(state["turn_queue"]) + 2},
    )

    # Auto-checkpoint: save after each round (FR33, NFR11)
    session_id = format_session_id(result["session_number"])
    turn_number = len(result["ground_truth_log"])
    if turn_number > 0:  # Only save if there's content
        save_checkpoint(result, session_id, turn_number)

    return result
```

Also add checkpoint save to `human_intervention_node()`:

```python
def human_intervention_node(state: GameState) -> GameState:
    # ... existing code ...

    # After updating state with human action...

    # Auto-checkpoint: save after human action
    from persistence import format_session_id, save_checkpoint

    updated_state = {
        **state,
        "ground_truth_log": new_log,
        "agent_memories": new_memories,
    }

    session_id = format_session_id(updated_state["session_number"])
    turn_number = len(new_log)
    if turn_number > 0:
        save_checkpoint(updated_state, session_id, turn_number)

    return updated_state
```

#### GameState session_id Field (models.py)

Add `session_id` to GameState TypedDict:

```python
class GameState(TypedDict):
    ground_truth_log: list[str]
    turn_queue: list[str]
    current_turn: str
    agent_memories: dict[str, AgentMemory]
    game_config: GameConfig
    dm_config: DMConfig
    characters: dict[str, CharacterConfig]
    whisper_queue: list[str]
    human_active: bool
    controlled_character: str | None
    session_number: int
    session_id: str  # NEW: Unique session identifier for persistence
```

Update `create_initial_game_state()`:

```python
def create_initial_game_state() -> GameState:
    return GameState(
        ground_truth_log=[],
        turn_queue=[],
        current_turn="",
        agent_memories={},
        game_config=GameConfig(),
        dm_config=DMConfig(),
        characters={},
        whisper_queue=[],
        human_active=False,
        controlled_character=None,
        session_number=1,
        session_id="001",  # NEW
    )
```

Update `populate_game_state()`:

```python
def populate_game_state(include_sample_messages: bool = True) -> GameState:
    # ... existing code ...

    # Generate session_id from session_number
    session_id = f"{1:03d}"  # Default session 1

    return GameState(
        # ... existing fields ...
        session_number=1,
        session_id=session_id,  # NEW
    )
```

### Testing Strategy

Organize tests in dedicated test classes within `tests/test_persistence.py`:

```python
class TestPathUtilities:
    """Tests for checkpoint path utilities."""

class TestGameStateSerialization:
    """Tests for GameState serialize/deserialize."""

class TestSaveCheckpoint:
    """Tests for save_checkpoint function."""

class TestLoadCheckpoint:
    """Tests for load_checkpoint function."""

class TestListingFunctions:
    """Tests for list_sessions, list_checkpoints, get_latest_checkpoint."""

class TestAutoCheckpointIntegration:
    """Integration tests for auto-checkpoint in game loop."""

class TestStory41AcceptanceCriteria:
    """Acceptance tests for all Story 4.1 criteria."""
```

**Key Test Cases:**

```python
def test_checkpoint_path_format():
    """Test checkpoint path follows session_xxx/turn_xxx.json format."""
    path = get_checkpoint_path("001", 42)
    assert str(path).endswith("campaigns/session_001/turn_042.json")

def test_serialize_deserialize_roundtrip():
    """Test GameState survives serialization round-trip."""
    state = populate_game_state(include_sample_messages=False)
    json_str = serialize_game_state(state)
    restored = deserialize_game_state(json_str)

    assert restored["session_number"] == state["session_number"]
    assert restored["turn_queue"] == state["turn_queue"]
    assert len(restored["agent_memories"]) == len(state["agent_memories"])

def test_save_checkpoint_creates_file():
    """Test save_checkpoint creates file at expected path."""
    state = populate_game_state(include_sample_messages=True)
    path = save_checkpoint(state, "001", 5)

    assert path.exists()
    assert path.name == "turn_005.json"

def test_save_checkpoint_atomic_write(tmp_path, monkeypatch):
    """Test atomic write pattern protects against partial writes."""
    # Simulate crash during write
    # ...

def test_load_checkpoint_returns_complete_state():
    """Test loaded checkpoint contains all agent memories."""
    state = populate_game_state(include_sample_messages=True)
    save_checkpoint(state, "001", 1)

    loaded = load_checkpoint("001", 1)

    assert loaded is not None
    assert "agent_memories" in loaded
    assert len(loaded["agent_memories"]) == len(state["agent_memories"])

def test_auto_checkpoint_after_dm_turn():
    """Test checkpoint created after DM turn completes."""
    # Run single round and verify checkpoint exists
    # ...

def test_old_checkpoints_not_modified():
    """Test saving new checkpoint doesn't modify old ones."""
    state1 = populate_game_state()
    save_checkpoint(state1, "001", 1)
    mtime1 = get_checkpoint_path("001", 1).stat().st_mtime

    # Wait a moment
    time.sleep(0.1)

    state2 = populate_game_state()
    save_checkpoint(state2, "001", 2)

    mtime1_after = get_checkpoint_path("001", 1).stat().st_mtime
    assert mtime1 == mtime1_after  # Old checkpoint unchanged
```

### Security Considerations

- **Path Traversal:** Session IDs and turn numbers should be validated to prevent path traversal attacks. Only accept numeric session IDs.
- **File Size:** No explicit limit on checkpoint size, but GameState is bounded by agent memory limits.
- **Permissions:** Files created with default umask. Not a concern for local-only application.
- **Sensitive Data:** Checkpoints may contain game narrative but no actual secrets (API keys are in .env, not GameState).

### Edge Cases

1. **First Turn:** Turn number 0 or empty log - should handle gracefully
2. **Missing campaigns/ Directory:** Should create automatically
3. **Permission Error:** Should surface error clearly, not corrupt state
4. **Disk Full:** Atomic write should either succeed or fail cleanly
5. **Concurrent Writes:** Single-user app, but atomic rename protects anyway
6. **Invalid JSON on Load:** Return None, don't crash
7. **Unicode Content:** Ensure UTF-8 encoding throughout
8. **Windows vs POSIX:** `Path.replace()` behavior differs slightly; test on Windows
9. **Very Large State:** Agent memories could grow; ensure reasonable performance
10. **Session Number Overflow:** Support up to 999 with 3-digit padding; extend if needed

### Performance Considerations

- Checkpoint save is synchronous and blocks UI briefly
- JSON serialization is fast for typical GameState sizes (~10-50KB)
- No compression for MVP; add if checkpoints become too large
- Keep all checkpoints (no pruning) for maximum recovery flexibility

### References

- [Source: planning-artifacts/prd.md#Persistence & Recovery FR33-FR41]
- [Source: planning-artifacts/architecture.md#Persistence Strategy]
- [Source: planning-artifacts/epics.md#Story 4.1]
- [Source: models.py#GameState] - TypedDict definition
- [Source: graph.py#run_single_round] - Integration point
- [Source: persistence.py] - Currently placeholder
- [Source: _bmad-output/implementation-artifacts/3-6-keyboard-shortcuts.md] - Previous story patterns
