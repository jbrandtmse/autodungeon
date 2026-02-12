# Story 16.3: WebSocket Game Streaming

Status: ready-for-dev

## Story

As a **developer building the real-time game interface**,
I want **a WebSocket endpoint that streams game state updates from the GameEngine to connected browser clients, accepts control commands, and supports multiple concurrent viewers**,
so that **the SvelteKit frontend (Story 16-4+) can display the game in real-time and send user commands without polling, enabling truly interactive gameplay that survives long sessions**.

## Acceptance Criteria (Given/When/Then)

### AC1: WebSocket Endpoint Accepts Connections for Valid Sessions

**Given** the FastAPI app is running and a session "001" exists in the engine registry
**When** a client connects to `ws://localhost:8000/ws/game/001`
**Then** the WebSocket connection is accepted
**And** the server sends an initial `session_state` message with the full current state snapshot
**And** the server registers the client in a per-session connection set

**Given** the FastAPI app is running and session "999" does NOT exist in the engine registry
**When** a client connects to `ws://localhost:8000/ws/game/999`
**Then** the server accepts the connection
**And** immediately sends an error message `{"type": "error", "message": "Session '999' not found", "recoverable": false}`
**And** closes the WebSocket with code 4004

**Given** the FastAPI app is running
**When** a client connects with an invalid session_id (e.g., `../etc`)
**Then** the server accepts and immediately closes with code 4000 and reason "Invalid session ID"

### AC2: Server Streams Game Events to Connected Clients

**Given** a client is connected to `ws://localhost:8000/ws/game/001`
**When** the GameEngine for session "001" broadcasts a `turn_update` event
**Then** the connected client receives a JSON message: `{"type": "turn_update", "turn": N, "agent": "dm", "content": "...", "state": {...}}`

**Given** a client is connected to `ws://localhost:8000/ws/game/001`
**When** the GameEngine broadcasts an `autopilot_started` event
**Then** the client receives `{"type": "autopilot_started"}`

**Given** a client is connected to `ws://localhost:8000/ws/game/001`
**When** the GameEngine broadcasts an `autopilot_stopped` event
**Then** the client receives `{"type": "autopilot_stopped", "reason": "user_request"}`

**Given** a client is connected to `ws://localhost:8000/ws/game/001`
**When** the GameEngine broadcasts an `error` event
**Then** the client receives `{"type": "error", "message": "...", "recoverable": true}`

### AC3: Client Can Send Control Commands via WebSocket

**Given** a client is connected to `ws://localhost:8000/ws/game/001`
**When** the client sends `{"type": "start_autopilot", "speed": "normal"}`
**Then** the server calls `engine.start_autopilot(speed="normal")`
**And** the client receives an `autopilot_started` acknowledgment via the broadcast

**Given** a client is connected and autopilot is running
**When** the client sends `{"type": "stop_autopilot"}`
**Then** the server calls `engine.stop_autopilot()`
**And** the client receives an `autopilot_stopped` event

**Given** a client is connected
**When** the client sends `{"type": "next_turn"}`
**Then** the server calls `engine.run_turn()` and the client receives the `turn_update` result

**Given** a client is connected
**When** the client sends `{"type": "drop_in", "character": "rogue"}`
**Then** the server calls `engine.drop_in("rogue")`
**And** the client receives a `drop_in` event with the character name

**Given** a client is connected with human control active
**When** the client sends `{"type": "release_control"}`
**Then** the server calls `engine.release_control()`
**And** the client receives a `release_control` event

**Given** a client is connected with human controlling "rogue"
**When** the client sends `{"type": "submit_action", "content": "I check the door for traps"}`
**Then** the server calls `engine.submit_human_action("I check the door for traps")`
**And** the client receives the resulting `turn_update`

**Given** a client is connected
**When** the client sends `{"type": "nudge", "content": "Maybe try talking to the innkeeper?"}`
**Then** the server calls `engine.submit_nudge("Maybe try talking to the innkeeper?")`
**And** the client receives `{"type": "nudge_received"}`

**Given** a client is connected
**When** the client sends `{"type": "set_speed", "speed": "fast"}`
**Then** the server calls `engine.set_speed("fast")`
**And** the client receives `{"type": "speed_changed", "speed": "fast"}`

**Given** a client is connected
**When** the client sends `{"type": "pause"}`
**Then** the server calls `engine.pause()`
**And** the client receives `{"type": "paused"}`

**Given** a client is connected
**When** the client sends `{"type": "resume"}`
**Then** the server calls `engine.resume()`
**And** the client receives `{"type": "resumed"}`

**Given** a client is connected
**When** the client sends `{"type": "retry"}`
**Then** the server calls `engine.retry_turn()`
**And** the client receives the resulting event (turn_update or error)

### AC4: Invalid Commands Return Error Messages

**Given** a client is connected
**When** the client sends invalid JSON (e.g., `not json`)
**Then** the client receives `{"type": "error", "message": "Invalid message format: ...", "recoverable": true}`
**And** the connection is NOT closed

**Given** a client is connected
**When** the client sends a JSON message without a `type` field: `{"content": "hello"}`
**Then** the client receives `{"type": "error", "message": "Missing 'type' field in message", "recoverable": true}`

**Given** a client is connected
**When** the client sends an unknown command type: `{"type": "fly_to_moon"}`
**Then** the client receives `{"type": "error", "message": "Unknown command type: fly_to_moon", "recoverable": true}`

**Given** a client is connected
**When** the client sends `{"type": "start_autopilot", "speed": "ludicrous"}`
**Then** the client receives `{"type": "error", "message": "Invalid speed ...", "recoverable": true}`
**And** autopilot is NOT started

**Given** a client sends `{"type": "drop_in", "character": "dm"}`
**When** the server processes the command
**Then** the client receives an error (cannot drop in as DM)

**Given** a client sends `{"type": "submit_action"}` (missing content)
**When** the server processes the command
**Then** the client receives `{"type": "error", "message": "Missing 'content' field ...", "recoverable": true}`

### AC5: Multiple Clients Can Watch the Same Session

**Given** clients A and B are both connected to `ws://localhost:8000/ws/game/001`
**When** the GameEngine broadcasts a `turn_update`
**Then** BOTH client A and client B receive the same event

**Given** clients A and B are connected to session "001"
**When** client A sends `{"type": "start_autopilot"}`
**Then** both A and B receive the `autopilot_started` event
**And** subsequent `turn_update` events are sent to both

**Given** clients A and B are connected to session "001"
**When** client A disconnects (closes WebSocket)
**Then** client B continues to receive events normally
**And** client A is removed from the connection set

**Given** clients A, B, and C are connected
**When** client B sends `{"type": "drop_in", "character": "rogue"}`
**Then** all three clients (A, B, C) receive the `drop_in` event

### AC6: Disconnection Cleanup Is Graceful

**Given** a client is connected to `ws://localhost:8000/ws/game/001`
**When** the client disconnects (close frame, network drop, or browser closed)
**Then** the server removes the client from the session connection set
**And** no errors are logged for normal disconnects
**And** remaining clients are unaffected

**Given** the last client disconnects from a session
**When** the connection set becomes empty
**Then** the broadcast callback remains registered on the engine (autopilot may still be running)
**And** the engine is NOT stopped (it continues independently per architecture)

**Given** a client reconnects to the same session
**When** the new connection is established
**Then** the client receives a fresh `session_state` event with the current full state
**And** the client is added to the session connection set

### AC7: Heartbeat / Ping-Pong Keeps Connections Alive

**Given** a client is connected to `ws://localhost:8000/ws/game/001`
**When** the server sends periodic ping frames (every 30 seconds)
**Then** the client responds with pong frames (handled by WebSocket protocol)
**And** the connection stays alive through idle periods

**Given** a client has not responded to a ping within 10 seconds
**When** the pong timeout expires
**Then** the server closes the connection and removes the client from the session set

**Given** a client sends a ping frame
**When** the server receives it
**Then** the server responds with a pong frame (per WebSocket protocol)

### AC8: Broadcast Callback Integration with GameEngine

**Given** the WebSocket handler for session "001"
**When** the first client connects
**Then** the handler registers a broadcast callback via `engine.set_broadcast_callback()`
**And** the callback sends events to all connected clients for that session

**Given** the broadcast callback is registered
**When** the engine emits any event (turn_update, error, autopilot_started, autopilot_stopped, drop_in, release_control, session_state)
**Then** the callback serializes the event to JSON and sends it to every connected WebSocket in the session's connection set

**Given** a connected client has a broken/slow connection
**When** the broadcast callback tries to send to that client and fails
**Then** the error is caught and logged
**And** the broken client is removed from the connection set
**And** other clients continue receiving events normally

### AC9: WebSocket Message Schemas Are Defined in schemas.py

**Given** the `api/schemas.py` module
**When** inspected
**Then** it contains Pydantic models for all WebSocket message types:
  - Server-to-client: `WsTurnUpdate`, `WsAutopilotStarted`, `WsAutopilotStopped`, `WsError`, `WsSessionState`, `WsDropIn`, `WsReleaseControl`, `WsNudgeReceived`, `WsSpeedChanged`, `WsPaused`, `WsResumed`
  - Client-to-server: `WsCommand` (discriminated union or base with type field)
**And** all message types have a `type` string literal discriminator field

### AC10: Comprehensive Test Coverage

**Given** the test file `tests/test_websocket.py` exists
**When** I run `pytest tests/test_websocket.py`
**Then** all WebSocket scenarios have tests:
  - Connection acceptance for valid session
  - Connection rejection for missing/invalid session
  - Receiving initial session_state on connect
  - Sending each command type and receiving the correct response/broadcast
  - Invalid JSON handling
  - Unknown command type handling
  - Missing fields handling
  - Multi-client broadcast (2+ clients receive same events)
  - Client disconnect cleanup
  - Broadcast callback error resilience (broken client does not crash others)
  - Engine method error propagation (e.g., start_autopilot when already running)
**And** tests use FastAPI's `WebSocketTestSession` (via `httpx` or `starlette.testclient`)
**And** tests mock `GameEngine` methods (no real LLM calls)
**And** target: 45-65 tests

## Tasks / Subtasks

- [ ] **Task 1: Define WebSocket message schemas in `api/schemas.py`** (AC: 9)
  - [ ] 1.1: Add server-to-client message models:
    - `WsTurnUpdate(type="turn_update", turn: int, agent: str, content: str, state: dict)`
    - `WsAutopilotStarted(type="autopilot_started")`
    - `WsAutopilotStopped(type="autopilot_stopped", reason: str)`
    - `WsError(type="error", message: str, recoverable: bool)`
    - `WsSessionState(type="session_state", state: dict)`
    - `WsDropIn(type="drop_in", character: str)`
    - `WsReleaseControl(type="release_control")`
    - `WsAwaitingInput(type="awaiting_input", character: str)`
    - `WsNudgeReceived(type="nudge_received")`
    - `WsSpeedChanged(type="speed_changed", speed: str)`
    - `WsPaused(type="paused")`
    - `WsResumed(type="resumed")`
  - [ ] 1.2: Add client-to-server command model:
    - `WsCommand` base with `type: str` discriminator
    - Specific variants: `StartAutopilot(speed)`, `StopAutopilot`, `NextTurn`, `DropIn(character)`, `ReleaseControl`, `SubmitAction(content)`, `Nudge(content)`, `SetSpeed(speed)`, `Pause`, `Resume`, `Retry`
  - [ ] 1.3: All models should inherit from `BaseModel` and use `Literal` type for the `type` field

- [ ] **Task 2: Implement ConnectionManager for multi-client WebSocket state** (AC: 5, 6, 8)
  - [ ] 2.1: Create `ConnectionManager` class in `api/websocket.py` with:
    - `_connections: dict[str, set[WebSocket]]` — maps session_id to connected clients
    - `async connect(session_id: str, websocket: WebSocket) -> None` — accept and register
    - `async disconnect(session_id: str, websocket: WebSocket) -> None` — remove from set
    - `async broadcast(session_id: str, event: dict) -> None` — send to all clients in session
    - `get_connection_count(session_id: str) -> int` — for monitoring/testing
  - [ ] 2.2: Broadcast method must catch per-client send errors, log them, and remove broken clients without affecting others
  - [ ] 2.3: Use a module-level singleton `manager = ConnectionManager()` for the router to reference
  - [ ] 2.4: Thread safety: use `asyncio.Lock` per session to protect the connection set during concurrent broadcasts and disconnects

- [ ] **Task 3: Implement WebSocket endpoint handler** (AC: 1, 2, 3, 4, 7)
  - [ ] 3.1: Replace the stub in `api/websocket.py` with full `game_websocket()` implementation
  - [ ] 3.2: Connection phase:
    - Validate `session_id` format (reject with 4000 if invalid)
    - Accept the WebSocket connection
    - Look up GameEngine from `request.app.state.engines`
    - If engine not found, send error message and close with code 4004
    - If engine has no state loaded, call `await engine.start_session()`
    - Register broadcast callback on engine via `engine.set_broadcast_callback()`
    - Add client to `ConnectionManager`
    - Send initial `session_state` message with current state snapshot
  - [ ] 3.3: Message receive loop:
    - `while True:` receive text messages from client
    - Parse JSON; on parse error, send error response (do not close)
    - Validate `type` field exists; on missing, send error response
    - Route to command handler based on `type`
    - Catch all exceptions in handler, send error response to client
  - [ ] 3.4: Command routing — dispatch each command type to the appropriate engine method:
    - `start_autopilot` -> `engine.start_autopilot(speed=msg.get("speed", "normal"))`
    - `stop_autopilot` -> `engine.stop_autopilot()`
    - `next_turn` -> `engine.run_turn()`
    - `drop_in` -> `engine.drop_in(character=msg["character"])`
    - `release_control` -> `engine.release_control()`
    - `submit_action` -> `engine.submit_human_action(content=msg["content"])`
    - `nudge` -> `engine.submit_nudge(content=msg["content"])` + send `nudge_received`
    - `set_speed` -> `engine.set_speed(speed=msg["speed"])` + send `speed_changed`
    - `pause` -> `engine.pause()` + send `paused`
    - `resume` -> `engine.resume()` + send `resumed`
    - `retry` -> `engine.retry_turn()`
  - [ ] 3.5: Disconnection handling:
    - Catch `WebSocketDisconnect` exception from receive loop
    - Remove client from `ConnectionManager`
    - If connection set for session is now empty, optionally log but do NOT stop the engine
  - [ ] 3.6: Ping/pong support:
    - FastAPI/Starlette handles WebSocket ping/pong at the protocol level
    - Set `websocket.accept()` with appropriate parameters if needed
    - For custom keepalive: spawn a background task that sends a ping every 30 seconds
    - On pong timeout (10s), close the connection

- [ ] **Task 4: Wire broadcast callback from ConnectionManager to GameEngine** (AC: 8)
  - [ ] 4.1: When a client connects, create a session-specific broadcast closure:
    ```python
    async def broadcast_to_session(event: dict) -> None:
        await manager.broadcast(session_id, event)
    ```
  - [ ] 4.2: Register via `engine.set_broadcast_callback(broadcast_to_session)`
  - [ ] 4.3: Only register the callback once per session (first client connection). Subsequent connections join the existing broadcast.
  - [ ] 4.4: The callback must handle the case where the connection set is empty (engine may still be running with no viewers)

- [ ] **Task 5: Handle command validation and error responses** (AC: 4)
  - [ ] 5.1: Create `_parse_command(raw: str) -> dict` helper that:
    - Parses JSON (returns error dict on failure)
    - Validates `type` field exists
    - Returns parsed dict or error dict
  - [ ] 5.2: Create `_validate_command(cmd: dict) -> str | None` helper that:
    - Checks required fields per command type (e.g., `drop_in` requires `character`, `submit_action` requires `content`)
    - Returns error message string if invalid, None if valid
  - [ ] 5.3: For engine method errors (ValueError, RuntimeError), catch and return as `{"type": "error", "message": "...", "recoverable": true}` without closing the connection

- [ ] **Task 6: Update `api/main.py` lifespan for WebSocket cleanup** (AC: 6)
  - [ ] 6.1: On shutdown, close all WebSocket connections gracefully via `ConnectionManager`
  - [ ] 6.2: Import and use the `manager` singleton from `api/websocket.py`

- [ ] **Task 7: Write tests** (AC: 10)
  - [ ] 7.1: Create `tests/test_websocket.py`
  - [ ] 7.2: Test fixtures:
    - Mock `GameEngine` with configurable state and method mocks
    - `app.state.engines` pre-populated with mock engines
    - Use `starlette.testclient.TestClient` for WebSocket testing (sync) or `httpx` async WebSocket support
  - [ ] 7.3: Connection tests:
    - Valid session: connection accepted, receives `session_state`
    - Invalid session_id format: connection closed with 4000
    - Missing session (no engine): error message + close with 4004
  - [ ] 7.4: Command tests (one test per command type, happy path):
    - `start_autopilot` with default and explicit speed
    - `stop_autopilot`
    - `next_turn`
    - `drop_in` with valid character
    - `release_control`
    - `submit_action` with content
    - `nudge` with content
    - `set_speed` with valid speed
    - `pause`
    - `resume`
    - `retry`
  - [ ] 7.5: Error handling tests:
    - Invalid JSON
    - Missing `type` field
    - Unknown command type
    - Missing required field (e.g., `drop_in` without `character`)
    - Engine raises ValueError (invalid speed, invalid character)
    - Engine raises RuntimeError (no state loaded, autopilot already running)
  - [ ] 7.6: Multi-client tests:
    - Two clients connected, both receive broadcast
    - One client disconnects, other still receives events
    - Client disconnect does not stop engine
  - [ ] 7.7: Broadcast callback tests:
    - Callback registered on engine when first client connects
    - Callback sends to all connected clients
    - Broken client removed during broadcast (does not crash others)
  - [ ] 7.8: ConnectionManager unit tests:
    - connect/disconnect modify connection set correctly
    - broadcast sends to all clients in session
    - broadcast handles per-client errors gracefully
    - get_connection_count returns correct count

- [ ] **Task 8: Verify lint, type-check, and existing tests pass** (AC: 10)
  - [ ] 8.1: Run `python -m ruff check .` -- fix any new violations
  - [ ] 8.2: Run `python -m ruff format .` -- fix formatting
  - [ ] 8.3: Run `python -m pytest` -- confirm no regressions in existing ~4100 tests
  - [ ] 8.4: Verify existing `tests/test_api.py` WebSocket stub test is updated or removed

## Dev Notes

### Architecture Context

This story connects the GameEngine (Story 16-2) to browser clients via WebSocket. It is the real-time bridge between backend game execution and frontend display. The architecture specifies a single WebSocket endpoint per session (`/ws/game/{session_id}`) that carries both server-to-client state updates and client-to-server control commands.

**Key Architecture Principle:** "Autopilot runs as an asyncio background task, independent of client connections." The WebSocket layer is a *consumer* of the GameEngine's broadcast callback -- it does not drive the game loop. If all clients disconnect, the engine keeps running.

**Key Architecture Principle:** "UI interactions send commands via WebSocket. Backend processes commands and streams updates. No coupling between UI rendering and game engine execution."

### WebSocket Message Protocol (from Architecture Doc)

The architecture document defines the complete message protocol. This story must implement it exactly.

**Client to Server (commands):**
```
{"type": "start_autopilot", "speed": "normal"}
{"type": "stop_autopilot"}
{"type": "next_turn"}
{"type": "drop_in", "character": "rogue"}
{"type": "release_control"}
{"type": "submit_action", "content": "I check the door for traps."}
{"type": "nudge", "content": "Maybe try talking to the innkeeper?"}
{"type": "set_speed", "speed": "fast"}
{"type": "pause"}
{"type": "resume"}
{"type": "retry"}
```

**Server to Client (events):**
```
{"type": "turn_update", "turn": 42, "agent": "dm", "content": "...", "state": {...}}
{"type": "awaiting_input", "character": "rogue"}
{"type": "autopilot_started"}
{"type": "autopilot_stopped", "reason": "user_request"}
{"type": "error", "message": "LLM API timeout", "recoverable": true}
{"type": "session_state", "state": {...}}
{"type": "drop_in", "character": "rogue"}
{"type": "release_control"}
{"type": "nudge_received"}
{"type": "speed_changed", "speed": "fast"}
{"type": "paused"}
{"type": "resumed"}
```

### GameEngine API to Invoke (from api/engine.py)

All these methods are already implemented in Story 16-2. The WebSocket handler calls them:

| Command | Engine Method | Notes |
|---------|-------------|-------|
| `start_autopilot` | `await engine.start_autopilot(speed)` | Raises RuntimeError if already running, ValueError if invalid speed |
| `stop_autopilot` | `await engine.stop_autopilot()` | No-op if not running |
| `next_turn` | `await engine.run_turn()` | Raises RuntimeError if no state loaded |
| `drop_in` | `await engine.drop_in(character)` | Raises ValueError if invalid character |
| `release_control` | `await engine.release_control()` | No-op if not controlling |
| `submit_action` | `await engine.submit_human_action(content)` | Raises RuntimeError if not in drop-in, ValueError if empty |
| `nudge` | `engine.submit_nudge(content)` | Synchronous. Raises ValueError if empty |
| `set_speed` | `engine.set_speed(speed)` | Synchronous. Raises ValueError if invalid |
| `pause` | `engine.pause()` | Synchronous |
| `resume` | `engine.resume()` | Synchronous |
| `retry` | `await engine.retry_turn()` | Raises RuntimeError if max retries exceeded |

### Broadcast Callback Registration Pattern

The GameEngine provides `set_broadcast_callback()` which accepts an `async Callable[[dict], Awaitable[None]]`. The WebSocket handler creates a closure that sends to all connected clients for a session.

```python
# In game_websocket() handler:
async def broadcast_to_session(event: dict[str, Any]) -> None:
    await manager.broadcast(session_id, event)

engine.set_broadcast_callback(broadcast_to_session)
```

The engine already broadcasts events for: `turn_update`, `error`, `autopilot_started`, `autopilot_stopped`, `drop_in`, `release_control`, `session_state`. See `api/engine.py:_broadcast()`. Some commands (nudge, set_speed, pause, resume) produce *acknowledgment* events that the WebSocket handler sends directly to the requesting client (or broadcasts to all).

### ConnectionManager Design

```python
class ConnectionManager:
    """Manages WebSocket connections per session."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        if session_id not in self._connections:
            self._connections[session_id] = set()
            self._locks[session_id] = asyncio.Lock()
        self._connections[session_id].add(websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        if session_id in self._connections:
            self._connections[session_id].discard(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]
                del self._locks[session_id]

    async def broadcast(self, session_id: str, event: dict) -> None:
        if session_id not in self._connections:
            return
        async with self._locks[session_id]:
            broken: list[WebSocket] = []
            for ws in self._connections[session_id]:
                try:
                    await ws.send_json(event)
                except Exception:
                    broken.append(ws)
            for ws in broken:
                self._connections[session_id].discard(ws)

    def get_connection_count(self, session_id: str) -> int:
        return len(self._connections.get(session_id, set()))
```

### WebSocket Close Codes

Use custom close codes for application-level errors:

| Code | Meaning | When |
|------|---------|------|
| 1000 | Normal closure | Client or server initiated graceful close |
| 4000 | Invalid session ID | session_id fails format validation |
| 4004 | Session not found | No engine exists for the session_id |
| 4008 | Pong timeout | Client did not respond to ping |

### Ping/Pong Implementation

FastAPI/Starlette's WebSocket handles the protocol-level ping/pong automatically. For application-level keepalive (to detect zombie connections through proxies/load balancers), implement a background task per connection:

```python
async def _keepalive(websocket: WebSocket) -> None:
    """Send periodic pings to keep the connection alive."""
    try:
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break
    except asyncio.CancelledError:
        pass
```

The frontend (Story 16-4) will respond with `{"type": "pong"}` to these application-level pings. Alternatively, rely solely on protocol-level ping/pong if Starlette handles it well enough for 12+ hour sessions.

### Existing Code to Reuse (DO NOT Reinvent)

| Need | Existing Code | Location |
|------|--------------|----------|
| GameEngine class | Full implementation | `api/engine.py` |
| Engine registry | `app.state.engines` dict | `api/main.py` lifespan |
| Get/create engine | `get_or_create_engine()` | `api/dependencies.py` |
| Session ID validation | `_validate_session_id()` | `persistence.py` |
| State snapshot | `engine._get_state_snapshot()` | `api/engine.py:618` |
| Broadcast callback | `engine.set_broadcast_callback()` | `api/engine.py:583` |
| API schemas base | Existing Pydantic models | `api/schemas.py` |

### Testing Strategy

**WebSocket testing with FastAPI:**

FastAPI uses Starlette's `TestClient` for WebSocket testing. This provides a synchronous context manager:

```python
from starlette.testclient import TestClient
from api.main import app

def test_ws_connect():
    client = TestClient(app)
    with client.websocket_connect("/ws/game/001") as ws:
        data = ws.receive_json()
        assert data["type"] == "session_state"
```

For multi-client tests, open multiple `websocket_connect()` sessions in the same test.

**Mocking pattern:**

```python
@pytest.fixture
def mock_engine():
    engine = MagicMock(spec=GameEngine)
    engine.session_id = "001"
    engine.state = _make_game_state()
    engine.is_running = False
    engine.is_paused = False
    engine.speed = "normal"
    engine.human_active = False
    engine.controlled_character = None
    # Mock async methods
    engine.start_autopilot = AsyncMock()
    engine.stop_autopilot = AsyncMock()
    engine.run_turn = AsyncMock(return_value={"type": "turn_update", ...})
    engine.drop_in = AsyncMock()
    engine.release_control = AsyncMock()
    engine.submit_human_action = AsyncMock(return_value={"type": "turn_update", ...})
    return engine

@pytest.fixture
def app_with_engine(mock_engine):
    app.state.engines = {"001": mock_engine}
    yield app
    app.state.engines = {}
```

**Important:** Use `starlette.testclient.TestClient` (synchronous) for WebSocket tests, NOT `httpx.AsyncClient`. Starlette's TestClient has first-class WebSocket support; httpx's WebSocket support is limited.

### WebSocket Handler Structure

```python
@router.websocket("/ws/game/{session_id}")
async def game_websocket(websocket: WebSocket, session_id: str) -> None:
    # 1. Validate session_id
    # 2. Accept connection
    # 3. Look up engine
    # 4. Register broadcast callback (if first client)
    # 5. Add to ConnectionManager
    # 6. Send initial session_state
    # 7. Start keepalive task
    # 8. Enter receive loop
    try:
        while True:
            raw = await websocket.receive_text()
            await _handle_command(engine, websocket, session_id, raw)
    except WebSocketDisconnect:
        pass
    finally:
        # 9. Cancel keepalive task
        # 10. Remove from ConnectionManager
        # 11. Cleanup
```

### Commands That Need Direct Ack vs Broadcast

Some commands produce responses through the engine's broadcast callback (broadcast to all clients). Others need a direct acknowledgment to the requesting client only.

**Engine broadcasts (all clients receive):**
- `start_autopilot` -> engine broadcasts `autopilot_started`
- `stop_autopilot` -> engine broadcasts `autopilot_stopped`
- `next_turn` -> engine broadcasts `turn_update`
- `drop_in` -> engine broadcasts `drop_in`
- `release_control` -> engine broadcasts `release_control`
- `submit_action` -> engine broadcasts `turn_update`
- `retry` -> engine broadcasts `turn_update` or `error`

**Direct ack from WebSocket handler (broadcast to all for state consistency):**
- `nudge` -> handler broadcasts `nudge_received`
- `set_speed` -> handler broadcasts `speed_changed`
- `pause` -> handler broadcasts `paused`
- `resume` -> handler broadcasts `resumed`

Broadcast these acknowledgments to all clients so every viewer stays in sync.

### Common Pitfalls to Avoid

1. **Do NOT import `streamlit` anywhere in `api/websocket.py`.** Zero Streamlit dependency.
2. **Do NOT stop the engine when the last client disconnects.** Autopilot runs independently per architecture.
3. **Do NOT close the WebSocket on command errors.** Only close on connection-level failures (invalid session, pong timeout). All command errors are sent as `{"type": "error"}` messages while keeping the connection open.
4. **Do NOT use `httpx.AsyncClient` for WebSocket tests.** Use `starlette.testclient.TestClient` which has native WebSocket testing support via `client.websocket_connect()`.
5. **Do NOT modify `api/engine.py`.** The engine's broadcast callback API is already implemented. This story only *consumes* it.
6. **Handle `WebSocketDisconnect` in the receive loop.** Starlette raises this when the client disconnects. Catch it, clean up, and return -- do not let it propagate.
7. **Lock per session in ConnectionManager.** Without locks, concurrent broadcasts and disconnects can cause `set changed size during iteration` errors.
8. **Test cleanup:** Ensure WebSocket connections are closed in test teardown. Dangling connections cause flaky tests.
9. **JSON serialization:** Use `websocket.send_json()` which handles serialization. For Pydantic models, call `.model_dump()` first if needed.
10. **Import paths:** Flat layout -- `from persistence import _validate_session_id`, `from api.engine import GameEngine`, etc.

### File Structure After This Story

```
api/
├── __init__.py          # Unchanged
├── main.py              # Updated: shutdown closes WebSocket connections
├── routes.py            # Unchanged
├── websocket.py         # REPLACED: stub -> full WebSocket handler + ConnectionManager
├── engine.py            # Unchanged (from Story 16-2)
├── dependencies.py      # Unchanged
└── schemas.py           # UPDATED: add WebSocket message schemas

tests/
├── test_api.py          # UPDATED: remove/update stub WebSocket test
├── test_engine.py       # Unchanged
└── test_websocket.py    # NEW: WebSocket handler + ConnectionManager tests
```

### Dependencies

No new dependencies required. FastAPI includes WebSocket support via Starlette. The `websockets` library may already be installed as a transitive dependency of `uvicorn[standard]`. If not present, add it:
```bash
uv add websockets
```

### References

- [Source: _bmad-output/planning-artifacts/architecture.md -- "API Layer & Frontend Integration" section, WebSocket Message Protocol]
- [Source: _bmad-output/planning-artifacts/architecture.md -- "Architectural Boundaries" section, "API Layer <-> Frontend"]
- [Source: _bmad-output/planning-artifacts/architecture.md -- "Decision Summary" table, "State Sync: WebSocket streaming"]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-11.md -- Section 4.4, Story 16-3 scope]
- [Source: api/engine.py -- GameEngine.set_broadcast_callback(), _broadcast(), _get_state_snapshot()]
- [Source: api/engine.py -- All engine methods: start_autopilot, stop_autopilot, run_turn, drop_in, release_control, submit_human_action, submit_nudge, set_speed, pause, resume, retry_turn]
- [Source: api/main.py -- lifespan manager, engine registry]
- [Source: api/dependencies.py -- get_or_create_engine()]
- [Source: _bmad-output/implementation-artifacts/16-2-game-engine-extraction.md -- AC11 Broadcast Callback Mechanism]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
