# Story 16.2: Game Engine Extraction

Status: review

## Story

As a **developer building the FastAPI backend**,
I want **game orchestration extracted from app.py into a standalone GameEngine service class in api/engine.py**,
so that **the game loop runs independently of any UI framework, autopilot operates as an asyncio background task, and the API/WebSocket layer (Stories 16-3+) can drive games without Streamlit**.

## Acceptance Criteria (Given/When/Then)

### AC1: GameEngine Class Manages Session Lifecycle

**Given** the `GameEngine` class in `api/engine.py`
**When** I call `engine = GameEngine(session_id="001")`
**Then** the engine is initialized with session_id, empty state, and default config
**And** `engine.session_id` returns "001"
**And** `engine.state` returns None (not yet loaded)
**And** `engine.is_running` returns False

### AC2: Start and Stop Session

**Given** a GameEngine instance for session "001"
**When** I call `await engine.start_session()`
**Then** the engine loads the latest checkpoint via `persistence.load_checkpoint()` or creates initial state via `models.populate_game_state()`
**And** `engine.state` returns a valid GameState
**And** the engine is ready to execute turns
**When** I call `await engine.stop_session()`
**Then** autopilot is stopped if running
**And** the engine state is saved as a checkpoint
**And** `engine.state` returns None

### AC3: Run Single Turn

**Given** a started GameEngine with loaded state
**When** I call `await engine.run_turn()`
**Then** one complete round is executed via `graph.run_single_round()`
**And** the engine's internal state is updated with the result
**And** if an error occurs, the state is NOT corrupted and a `UserError` is returned
**And** a list of callbacks (for WebSocket broadcast) is returned with turn data

### AC4: Autopilot as Asyncio Background Task

**Given** a started GameEngine with loaded state
**When** I call `await engine.start_autopilot(speed="normal")`
**Then** an `asyncio.Task` is created that runs turns in a loop
**And** `engine.is_running` returns True
**And** turns execute with the appropriate delay (3.0s slow, 1.0s normal, 0.2s fast)
**And** each completed turn invokes a broadcast callback (for WebSocket in 16-3)
**When** I call `await engine.stop_autopilot()`
**Then** the background task is cancelled gracefully
**And** `engine.is_running` returns False
**And** the current turn is allowed to complete before stopping

### AC5: Pause and Resume

**Given** autopilot is running
**When** I call `engine.pause()`
**Then** `engine.is_paused` returns True
**And** autopilot loop skips turn execution while paused (but task stays alive)
**When** I call `engine.resume()`
**Then** `engine.is_paused` returns False
**And** autopilot resumes executing turns

### AC6: Set Speed During Autopilot

**Given** autopilot is running at "normal" speed
**When** I call `engine.set_speed("fast")`
**Then** `engine.speed` returns "fast"
**And** the next turn delay uses 0.2s instead of 1.0s
**And** autopilot is NOT interrupted (speed change is seamless)

### AC7: Drop-In / Release Human Control

**Given** a started GameEngine with autopilot running
**When** I call `engine.drop_in(character="rogue")`
**Then** autopilot is stopped
**And** `engine.human_active` returns True
**And** `engine.controlled_character` returns "rogue"
**And** the GameState's `human_active` and `controlled_character` fields are updated
**When** I call `engine.release_control()`
**Then** `engine.human_active` returns False
**And** `engine.controlled_character` returns None
**And** the GameState fields are cleared

### AC8: Submit Human Action

**Given** a human has dropped in as "rogue"
**When** I call `await engine.submit_human_action("I check the door for traps")`
**Then** the action is fed into the LangGraph human_intervention_node
**And** the game continues processing turns
**And** the result includes the human action in ground_truth_log

### AC9: Nudge System

**Given** a started GameEngine
**When** I call `engine.submit_nudge("Maybe try talking to the innkeeper?")`
**Then** the nudge is stored for the DM's next turn context
**And** the nudge is accessible via `engine.pending_nudge`

### AC10: Error Handling and Retry

**Given** a GameEngine where `run_single_round()` returns an error
**When** the autopilot encounters the error
**Then** autopilot stops
**And** the error is stored as `engine.last_error` (a UserError)
**And** the GameState is NOT corrupted
**When** I call `await engine.retry_turn()`
**Then** the failed turn is re-attempted
**And** if successful, `engine.last_error` is cleared
**And** retry count is tracked and MAX_RETRY_ATTEMPTS (3) is enforced

### AC11: Broadcast Callback Mechanism

**Given** a GameEngine with a registered broadcast callback
**When** a turn completes (autopilot or manual)
**Then** the callback is invoked with a dict containing: `type`, `turn_number`, `agent`, `content`, `state_snapshot`
**And** errors also invoke the callback with `type: "error"`
**And** state changes (pause, resume, drop_in, release) invoke the callback with appropriate types
**This** callback mechanism enables Story 16-3 WebSocket broadcasting without coupling the engine to WebSocket

### AC12: Zero Streamlit Dependency

**Given** the `api/engine.py` module
**When** I inspect its imports
**Then** there is NO import of `streamlit` anywhere in the module
**And** there is NO reference to `st.session_state`
**And** the module can be imported and used without Streamlit installed

### AC13: Comprehensive Test Coverage

**Given** the test file `tests/test_engine.py` exists
**When** I run `pytest tests/test_engine.py`
**Then** all GameEngine methods have at least one happy-path and one error-path test
**And** tests do not require running LLMs (mock `run_single_round`)
**And** tests verify autopilot task lifecycle (start, stop, pause, resume, speed change)
**And** tests verify human intervention flow (drop_in, submit_action, release)
**And** tests verify error handling and retry
**And** target: 40-60 tests

## Tasks / Subtasks

- [ ] **Task 1: Define GameEngine class with state management** (AC: 1, 2, 12)
  - [ ] 1.1: Replace stub in `api/engine.py` with full class definition
  - [ ] 1.2: Constructor: `__init__(self, session_id: str)` initializing `_session_id`, `_state: GameState | None`, `_task: asyncio.Task | None`, `_is_paused: bool`, `_speed: str`, `_human_active: bool`, `_controlled_character: str | None`, `_pending_nudge: str | None`, `_last_error: UserError | None`, `_retry_count: int`, `_broadcast_callback: Callable | None`, `_lock: asyncio.Lock`
  - [ ] 1.3: Properties: `session_id`, `state`, `is_running`, `is_paused`, `speed`, `human_active`, `controlled_character`, `pending_nudge`, `last_error`
  - [ ] 1.4: `async start_session(characters_override=None, selected_module=None, library_data=None)` — loads latest checkpoint or creates new state via `populate_game_state()`
  - [ ] 1.5: `async stop_session()` — stops autopilot, saves checkpoint, clears state

- [ ] **Task 2: Implement turn execution** (AC: 3, 10)
  - [ ] 2.1: `async run_turn() -> dict` — wraps `run_single_round()` in `asyncio.to_thread()` (since graph.py is synchronous), updates internal state, handles errors, invokes broadcast callback, returns turn data dict
  - [ ] 2.2: Error handling: if result contains "error" key, store in `_last_error`, do NOT update state
  - [ ] 2.3: `async retry_turn() -> dict` — re-executes turn with retry tracking, enforces MAX_RETRY_ATTEMPTS

- [ ] **Task 3: Implement autopilot as asyncio background task** (AC: 4, 5, 6)
  - [ ] 3.1: `async start_autopilot(speed: str = "normal")` — creates `asyncio.Task` running `_autopilot_loop()`
  - [ ] 3.2: `async stop_autopilot()` — cancels the task, waits for graceful shutdown
  - [ ] 3.3: `async _autopilot_loop()` — loop that calls `run_turn()`, applies speed delay via `asyncio.sleep()`, checks pause/stop flags, handles errors (stops on error)
  - [ ] 3.4: `pause()` / `resume()` — toggle `_is_paused` flag (synchronous, no await needed)
  - [ ] 3.5: `set_speed(speed: str)` — validates and sets `_speed` (synchronous)

- [ ] **Task 4: Implement human intervention** (AC: 7, 8, 9)
  - [ ] 4.1: `drop_in(character: str)` — stops autopilot, sets human_active + controlled_character on both engine and GameState
  - [ ] 4.2: `release_control()` — clears human_active + controlled_character on both engine and GameState
  - [ ] 4.3: `async submit_human_action(action: str)` — sets `human_pending_action` on state, runs turn to process it
  - [ ] 4.4: `submit_nudge(nudge: str)` — stores sanitized nudge for DM context

- [ ] **Task 5: Implement broadcast callback mechanism** (AC: 11)
  - [ ] 5.1: `set_broadcast_callback(callback: Callable[[dict], Awaitable[None]] | None)` — register/unregister callback
  - [ ] 5.2: `async _broadcast(event: dict)` — invokes callback if registered, catches and logs exceptions
  - [ ] 5.3: Broadcast events for: turn_update, error, autopilot_started, autopilot_stopped, paused, resumed, drop_in, release_control, awaiting_input, session_state

- [ ] **Task 6: Update `api/dependencies.py` and `api/main.py` for engine registry** (AC: 1)
  - [ ] 6.1: Update `get_engine_registry()` type hint from `dict[str, Any]` to `dict[str, GameEngine]`
  - [ ] 6.2: Update `api/main.py` lifespan shutdown to call `await engine.stop_session()` for each active engine
  - [ ] 6.3: Add `get_or_create_engine(session_id)` helper to dependencies.py

- [ ] **Task 7: Decouple Streamlit session_state access from graph.py and agents.py** (AC: 12)
  - [ ] 7.1: Add three new fields to GameState TypedDict in `models.py`: `human_pending_action: str | None`, `pending_nudge: str | None`, `pending_human_whisper: str | None`
  - [ ] 7.2: Update `create_initial_game_state()` and `populate_game_state()` to include all three new fields (default None)
  - [ ] 7.3: Modify `graph.py:human_intervention_node()` (L239) to read `human_pending_action` from `state.get("human_pending_action")` instead of `st.session_state`; clear in state dict after processing
  - [ ] 7.4: Modify `agents.py` DM context building (L1376) to read `pending_nudge` from state dict first, fall back to st.session_state
  - [ ] 7.5: Modify `agents.py` dm_turn nudge clear (L1719) to clear from state dict AND st.session_state
  - [ ] 7.6: Modify `agents.py` DM context building (L1394) to read `pending_human_whisper` from state dict first, fall back to st.session_state
  - [ ] 7.7: Modify `agents.py` dm_turn whisper clear (L1729) to clear from state dict AND st.session_state
  - [ ] 7.8: Update `app.py:handle_human_action_submit()` (L3769) to also set `game["human_pending_action"]`
  - [ ] 7.9: Update `app.py:handle_nudge_submit()` (L3708) to also set `game["pending_nudge"]`
  - [ ] 7.10: Update `app.py:handle_human_whisper_submit()` (L3724) to also set `game["pending_human_whisper"]`
  - [ ] 7.11: Verify all existing tests still pass (backward compat via try/except fallbacks)

- [ ] **Task 8: Write tests** (AC: 13)
  - [ ] 8.1: Create `tests/test_engine.py`
  - [ ] 8.2: Test construction and properties (session_id, initial state, is_running)
  - [ ] 8.3: Test start_session with checkpoint loading (mock persistence)
  - [ ] 8.4: Test start_session with fresh state (mock populate_game_state)
  - [ ] 8.5: Test stop_session saves checkpoint and clears state
  - [ ] 8.6: Test run_turn success path (mock run_single_round)
  - [ ] 8.7: Test run_turn error path (mock run_single_round returning error)
  - [ ] 8.8: Test start_autopilot creates background task
  - [ ] 8.9: Test stop_autopilot cancels task gracefully
  - [ ] 8.10: Test autopilot respects speed delay
  - [ ] 8.11: Test pause/resume toggles flag and affects autopilot loop
  - [ ] 8.12: Test set_speed during autopilot
  - [ ] 8.13: Test drop_in stops autopilot and sets human state
  - [ ] 8.14: Test release_control clears human state
  - [ ] 8.15: Test submit_human_action feeds into turn execution
  - [ ] 8.16: Test submit_nudge stores for DM context
  - [ ] 8.17: Test retry_turn with success and failure
  - [ ] 8.18: Test retry_turn enforces MAX_RETRY_ATTEMPTS
  - [ ] 8.19: Test broadcast callback invoked on turn completion
  - [ ] 8.20: Test broadcast callback invoked on state changes
  - [ ] 8.21: Test broadcast callback error handling (callback raises, engine continues)
  - [ ] 8.22: Test no Streamlit imports in engine module

- [ ] **Task 9: Verify lint, type-check, and existing tests** (AC: 12, 13)
  - [ ] 9.1: Run `python -m ruff check .` — fix any new violations
  - [ ] 9.2: Run `python -m ruff format .` — fix formatting
  - [ ] 9.3: Run `python -m pytest` — confirm no regressions in existing ~4100 tests
  - [ ] 9.4: Verify `human_intervention_node` changes don't break graph.py tests

## Dev Notes

### Architecture Context

This story extracts the game orchestration logic currently embedded in `app.py` (~9000 lines of mixed Streamlit UI + game logic) into a standalone `GameEngine` service class in `api/engine.py`. The GameEngine is the bridge between the pure game engine layer (graph.py, agents.py, memory.py, persistence.py) and the API layer (routes.py, websocket.py).

**Key Architecture Principle:** "UI interactions send commands. Backend processes commands and streams updates. No coupling between UI rendering and game engine execution."

The GameEngine class must have ZERO knowledge of HTTP, WebSocket, Streamlit, or any UI framework. It exposes a pure Python async API that the WebSocket endpoint (Story 16-3) will consume.

### Functions to Extract from app.py (with Line References)

These are the game-logic functions in `app.py` that contain the orchestration logic the GameEngine must replicate. Do NOT copy Streamlit-specific code -- only extract the core logic patterns.

| Function | app.py Line | What to Extract | GameEngine Equivalent |
|----------|------------|----------------|----------------------|
| `SPEED_DELAYS` | L100-104 | Speed-to-delay mapping | Class constant `SPEED_DELAYS` |
| `get_turn_delay()` | L114-121 | Delay lookup by speed | `_get_turn_delay()` using `self._speed` |
| `is_autopilot_available()` | L139-156 | Pre-conditions check | Internal check in `start_autopilot()` |
| `run_game_turn()` | L159-233 | Core turn execution with error handling | `async run_turn()` |
| `DEFAULT_MAX_TURNS_PER_SESSION` | L237 | Safety limit constant | Class constant |
| `run_continuous_loop()` | L240-289 | Continuous execution loop | `_autopilot_loop()` as asyncio task |
| `run_autopilot_step()` | L292-337 | Autopilot step with stopping conditions | `_autopilot_loop()` internals |
| `handle_autopilot_toggle()` | L3577-3594 | Start/stop logic | `start_autopilot()` / `stop_autopilot()` |
| `handle_pause_toggle()` | L1857-1859 | Pause flag toggle | `pause()` / `resume()` |
| `handle_drop_in_click()` | L3659-3695 | Drop-in/release state management | `drop_in()` / `release_control()` |
| `handle_nudge_submit()` | L3708-3721 | Nudge storage | `submit_nudge()` |
| `handle_human_action_submit()` | L3769-3782 | Human action storage | Part of `submit_human_action()` |
| `handle_retry_click()` | L3815-3874 | Retry with count tracking | `retry_turn()` |
| `handle_error_restore_click()` | L3877-3907 | Checkpoint restore on error | `restore_checkpoint()` |
| `MAX_RETRY_ATTEMPTS` | L3790 | Retry limit (3) | Class constant |
| `MAX_ACTION_LENGTH` | L3699 | Input sanitization limit | Class constant |
| `MAX_NUDGE_LENGTH` | L3702 | Nudge limit | Class constant |

### Key Session State Keys in app.py (Replace with Engine Fields)

These `st.session_state` keys in app.py map to GameEngine instance variables:

| st.session_state key | GameEngine field | Type |
|---------------------|-----------------|------|
| `game` | `self._state` | `GameState \| None` |
| `is_autopilot_running` | `self._task is not None and not self._task.done()` | computed |
| `is_paused` | `self._is_paused` | `bool` |
| `playback_speed` | `self._speed` | `str` |
| `human_active` | `self._human_active` | `bool` |
| `controlled_character` | `self._controlled_character` | `str \| None` |
| `human_pending_action` | In GameState dict directly | `str \| None` |
| `waiting_for_human` | Computed from state | `bool` |
| `pending_nudge` | `self._pending_nudge` | `str \| None` |
| `nudge_submitted` | N/A (just presence of nudge) | removed |
| `error` | `self._last_error` | `UserError \| None` |
| `error_retry_count` | `self._retry_count` | `int` |
| `autopilot_turn_count` | `self._turn_count` | `int` |
| `max_turns_per_session` | `self._max_turns` | `int` |
| `is_generating` | `self._is_generating` | `bool` |

### Critical: Streamlit Session State Decoupling (Task 7)

Three locations in the game engine read directly from `st.session_state` and MUST be decoupled. All use the same pattern: add the field to GameState TypedDict, read from state first, fall back to st.session_state for backward compatibility.

**Decoupling Point 1: human_pending_action (graph.py L239)**
```python
# Current: pending_action = st.session_state.get("human_pending_action")
# New: pending_action = state.get("human_pending_action")
```

**Decoupling Point 2: pending_nudge (agents.py L1376, L1719)**
```python
# Current (read): pending_nudge = st.session_state.get("pending_nudge")
# New (read): pending_nudge = state.get("pending_nudge") or st.session_state fallback
# Current (clear): st.session_state["pending_nudge"] = None
# New (clear): state["pending_nudge"] = None; st.session_state fallback
```

**Decoupling Point 3: pending_human_whisper (agents.py L1394, L1729)**
```python
# Current (read): pending_whisper = st.session_state.get("pending_human_whisper")
# New (read): pending_whisper = state.get("pending_human_whisper") or st.session_state fallback
# Current (clear): st.session_state["pending_human_whisper"] = None
# New (clear): state["pending_human_whisper"] = None; st.session_state fallback
```

**New GameState fields (models.py):**
```python
class GameState(TypedDict):
    # ... existing fields ...
    human_pending_action: str | None  # For human_intervention_node
    pending_nudge: str | None         # For DM context injection
    pending_human_whisper: str | None # For DM whisper context
```

**agents.py decoupling pattern** (nudge example, whisper is identical):
```python
# Read: try state first, fall back to st.session_state
pending_nudge = state.get("pending_nudge")
if pending_nudge is None:
    try:
        import streamlit as st
        pending_nudge = st.session_state.get("pending_nudge")
    except (ImportError, AttributeError):
        pass

# Clear: clear both locations
state["pending_nudge"] = None
try:
    import streamlit as st
    st.session_state["pending_nudge"] = None
except (ImportError, AttributeError, KeyError):
    pass
```

**app.py dual-write** (backward compat):
```python
# In handle_human_action_submit(), handle_nudge_submit(), handle_human_whisper_submit():
st.session_state["pending_nudge"] = sanitized  # Existing
game = st.session_state.get("game")
if game:
    game["pending_nudge"] = sanitized  # NEW: also set in GameState
```

**Files to change for Task 7:**
- `models.py` — Add 3 fields to GameState TypedDict + update both factory functions
- `graph.py` — Change `human_intervention_node` to read from state dict
- `agents.py` — Change nudge + whisper reads to use state-first pattern
- `app.py` — Add dual-write in 3 handler functions
- `persistence.py` — No changes needed (simple str|None fields auto-serialize)

### run_single_round is Synchronous — Use asyncio.to_thread()

`graph.py:run_single_round()` is synchronous (blocking). It calls `workflow.invoke()` which blocks during LLM API calls. The GameEngine must wrap it in `asyncio.to_thread()` to avoid blocking the event loop:

```python
async def run_turn(self) -> dict:
    result = await asyncio.to_thread(run_single_round, self._state)
    # ... handle result
```

### Broadcast Callback Pattern

The engine uses a callback pattern (not WebSocket directly) to notify listeners of state changes. Story 16-3 will register a WebSocket broadcaster as the callback.

```python
# Engine side (this story)
async def _broadcast(self, event: dict) -> None:
    if self._broadcast_callback:
        try:
            await self._broadcast_callback(event)
        except Exception:
            logger.exception("Broadcast callback error")

# WebSocket side (Story 16-3, NOT this story)
async def ws_broadcaster(event: dict) -> None:
    for ws in connected_clients[session_id]:
        await ws.send_json(event)
engine.set_broadcast_callback(ws_broadcaster)
```

Event types to broadcast (matching architecture doc WebSocket protocol):
```python
{"type": "turn_update", "turn": 42, "agent": "dm", "content": "...", "state": {...}}
{"type": "error", "message": "...", "recoverable": True}
{"type": "autopilot_started"}
{"type": "autopilot_stopped", "reason": "user_request" | "error" | "turn_limit" | "human_drop_in"}
{"type": "paused"}
{"type": "resumed"}
{"type": "awaiting_input", "character": "rogue"}
{"type": "session_state", "state": {...}}  # Full state on start/load
```

### asyncio.Lock for Thread Safety

Since autopilot runs as a background task and commands can arrive concurrently (from WebSocket in 16-3), use `asyncio.Lock` to prevent concurrent state mutations:

```python
async def run_turn(self) -> dict:
    async with self._lock:
        result = await asyncio.to_thread(run_single_round, self._state)
        # update state...
```

### Existing Code to Reuse (DO NOT Reinvent)

| Need | Existing Function | Location |
|------|------------------|----------|
| Execute one round | `run_single_round(state)` | `graph.py:450` |
| Create game workflow | `create_game_workflow(turn_queue)` | `graph.py:317` |
| Populate fresh state | `populate_game_state(...)` | `models.py:2600` |
| Create empty state | `create_initial_game_state()` | `models.py:2565` |
| Save checkpoint | `save_checkpoint(state, session_id, turn)` | `persistence.py` |
| Load checkpoint | `load_checkpoint(session_id, turn)` | `persistence.py` |
| Get latest checkpoint | `get_latest_checkpoint(session_id)` | `persistence.py` |
| Fork-aware save | `save_fork_checkpoint(state, session_id, fork_id, turn)` | `persistence.py` |
| Error creation | `create_user_error(...)` | `models.py` |
| UserError model | `UserError` class | `models.py` |
| Speed delays | `SPEED_DELAYS` dict | `app.py:100` (copy the values) |
| LLM error class | `LLMError` | `agents.py` |

### GameEngine Class Skeleton

```python
class GameEngine:
    SPEED_DELAYS = {"slow": 3.0, "normal": 1.0, "fast": 0.2}
    MAX_RETRY_ATTEMPTS = 3
    DEFAULT_MAX_TURNS = 100
    MAX_ACTION_LENGTH = 2000
    MAX_NUDGE_LENGTH = 1000

    def __init__(self, session_id: str) -> None:
        self._session_id = session_id
        self._state: GameState | None = None
        self._task: asyncio.Task[None] | None = None
        self._is_paused: bool = False
        self._speed: str = "normal"
        self._human_active: bool = False
        self._controlled_character: str | None = None
        self._pending_nudge: str | None = None
        self._last_error: UserError | None = None
        self._retry_count: int = 0
        self._turn_count: int = 0
        self._max_turns: int = self.DEFAULT_MAX_TURNS
        self._is_generating: bool = False
        self._broadcast_callback: Callable | None = None
        self._lock = asyncio.Lock()

    # Properties (session_id, state, is_running, is_paused, speed, ...)
    # Session lifecycle (start_session, stop_session)
    # Turn execution (run_turn, retry_turn)
    # Autopilot (start_autopilot, stop_autopilot, _autopilot_loop, pause, resume, set_speed)
    # Human intervention (drop_in, release_control, submit_human_action, submit_nudge)
    # Broadcast (set_broadcast_callback, _broadcast)
```

### Nudge Integration with DM Context

The nudge system works by storing the nudge text so the DM agent picks it up on its next turn. In `app.py`, nudges are passed via `st.session_state["pending_nudge"]`. The DM agent in `agents.py` reads this from session state.

For the GameEngine, the nudge should be stored as `self._pending_nudge`. The DM agent integration is addressed by setting `state["pending_nudge"]` before running the turn. Check how `agents.py:dm_turn()` accesses the nudge -- if it reads from `st.session_state`, that will need a similar decoupling fix. However, if the dm_turn reads from the state dict, it already works.

**CONFIRMED: agents.py reads nudge AND whisper from st.session_state.** Three decoupling points in `agents.py`:

1. **Nudge read** (agents.py L1376): `st.session_state.get("pending_nudge")` in DM context building
2. **Nudge clear** (agents.py L1719): `st.session_state["pending_nudge"] = None` in `dm_turn()`
3. **Whisper read** (agents.py L1394): `st.session_state.get("pending_human_whisper")` in DM context building
4. **Whisper clear** (agents.py L1729): `st.session_state["pending_human_whisper"] = None` in `dm_turn()`

All four locations use try/except ImportError with fallback, so they already work when Streamlit is not available. The fix is to add `pending_nudge: str | None` and `pending_human_whisper: str | None` to GameState TypedDict, then have agents.py read from the state dict FIRST, falling back to st.session_state for backward compatibility. This is the same pattern as Task 7's `human_pending_action` decoupling.

### Testing Strategy

- Use `pytest-anyio` (already installed from 16-1) for async test support
- Mock `run_single_round` to return predictable state dicts (do NOT run real LLMs)
- Mock `persistence.load_checkpoint`, `save_checkpoint`, `get_latest_checkpoint`
- Mock `models.populate_game_state` to return a known state
- For autopilot tests, use short delays and `asyncio.sleep()` assertions
- Test the lock by verifying concurrent run_turn calls are serialized
- Test broadcast callback with a simple list-appending async function
- Verify no `import streamlit` in `api/engine.py` by inspecting module imports

### Common Pitfalls to Avoid

1. **Do NOT import streamlit in api/engine.py.** Zero Streamlit dependency is a hard requirement.
2. **Do NOT call run_single_round() directly in async code.** It is synchronous and will block the event loop. Use `asyncio.to_thread()`.
3. **Do NOT modify agents.py, memory.py, or tools.py** unless absolutely necessary for nudge/pending_action decoupling.
4. **Do NOT break app.py.** It must continue working with Streamlit during the migration. All changes to graph.py and models.py must maintain backward compatibility.
5. **Do NOT add WebSocket code.** The engine uses a callback pattern. WebSocket integration is Story 16-3.
6. **Do NOT skip the asyncio.Lock.** Concurrent access from autopilot task + API commands will cause race conditions.
7. **GameState is a TypedDict, not a Pydantic model.** Adding fields requires updating the TypedDict class AND both factory functions (`create_initial_game_state`, `populate_game_state`).
8. **Persistence auto-serialization:** New simple-type fields (str, int, None) in GameState auto-serialize via the existing JSON checkpoint system. Complex types need explicit handling.
9. **Test isolation:** Do NOT leave asyncio tasks running between tests. Use proper cleanup fixtures.
10. **The `human_intervention_node` clears `st.session_state["human_pending_action"] = None` (graph.py L274).** After decoupling, it must clear `state["human_pending_action"] = None` instead AND the app.py code must set both locations.

### Project Structure Notes

**Files created by this story:**
```
tests/test_engine.py          # GameEngine unit tests (40-60 tests)
```

**Files modified by this story:**
```
api/engine.py                  # Stub -> full GameEngine implementation
api/dependencies.py            # Update type hint, add get_or_create_engine
api/main.py                    # Update lifespan shutdown for engine cleanup
models.py                      # Add 3 new fields to GameState TypedDict + update factories
graph.py                       # Decouple human_intervention_node from st.session_state
agents.py                      # Decouple pending_nudge + pending_human_whisper reads from st.session_state
app.py                         # Add dual-write for all three fields (backward compat)
```

**Files NOT modified:**
```
memory.py, tools.py, persistence.py, config.py
```

### Previous Story Intelligence (16-1)

From the 16-1 story completion notes:
- `api/` package structure is established with __init__.py, main.py, routes.py, schemas.py, dependencies.py, engine.py (stub), websocket.py (stub)
- FastAPI app uses lifespan context manager with `app.state.engines = {}` dict ready for GameEngine instances
- `dependencies.py` has `get_engine_registry()` returning `dict[str, Any]` (needs type update to `dict[str, GameEngine]`)
- Test pattern uses `httpx.AsyncClient` with `ASGITransport` and `pytest-anyio`
- 46 tests in test_api.py, all passing
- Dependencies already installed: fastapi, uvicorn[standard], httpx, anyio, pytest-anyio

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#API Layer & Frontend Integration]
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural Boundaries — "GameEngine service class wraps graph execution"]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns — "Access game state via GameEngine service"]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-11.md#Story 16-2]
- [Source: graph.py:450 — run_single_round() synchronous implementation]
- [Source: graph.py:210 — human_intervention_node() with st.session_state coupling]
- [Source: app.py:100-104 — SPEED_DELAYS constant]
- [Source: app.py:159-233 — run_game_turn() core logic]
- [Source: app.py:292-337 — run_autopilot_step() loop]
- [Source: app.py:3577-3594 — handle_autopilot_toggle()]
- [Source: app.py:3659-3695 — handle_drop_in_click()]
- [Source: app.py:3708-3721 — handle_nudge_submit()]
- [Source: app.py:3769-3782 — handle_human_action_submit()]
- [Source: app.py:3815-3874 — handle_retry_click()]
- [Source: app.py:1690-1789 — initialize_session_state() keys]
- [Source: models.py:1818-1873 — GameState TypedDict]
- [Source: models.py:2565-2597 — create_initial_game_state()]
- [Source: models.py:2600-2664 — populate_game_state()]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
