"""WebSocket endpoint for real-time game streaming.

Provides a ConnectionManager for multi-client WebSocket state and a
game_websocket endpoint that bridges GameEngine broadcast events to
connected browser clients and routes client commands to engine methods.

Story 16-3: WebSocket Game Streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.engine import GameEngine
from api.schemas import (
    WsAutopilotStarted,
    WsAutopilotStopped,
    WsAwaitingInput,
    WsDropIn,
    WsError,
    WsNudgeReceived,
    WsPaused,
    WsPong,
    WsReleaseControl,
    WsResumed,
    WsSessionState,
    WsSpeedChanged,
    WsTurnUpdate,
)

logger = logging.getLogger("autodungeon.websocket")

# Session ID format: alphanumeric with hyphens and underscores only
_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

# Commands that require specific fields
_REQUIRED_FIELDS: dict[str, list[str]] = {
    "drop_in": ["character"],
    "submit_action": ["content"],
    "nudge": ["content"],
    "whisper": ["content"],
    "set_speed": ["speed"],
}

# All recognized command types
_KNOWN_COMMANDS: frozenset[str] = frozenset(
    {
        "start_autopilot",
        "stop_autopilot",
        "next_turn",
        "drop_in",
        "release_control",
        "submit_action",
        "nudge",
        "whisper",
        "set_speed",
        "pause",
        "resume",
        "retry",
        "ping",
    }
)


class ConnectionManager:
    """Manages WebSocket connections per session.

    Thread-safe via per-session asyncio.Lock instances. Handles concurrent
    broadcasts and disconnects without ``set changed size during iteration``
    errors.
    """

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        """Register a WebSocket client for a session.

        Args:
            session_id: The session to join.
            websocket: The WebSocket connection to register.
        """
        if session_id not in self._connections:
            self._connections[session_id] = set()
            self._locks[session_id] = asyncio.Lock()
        self._connections[session_id].add(websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket client from a session.

        Acquires the session lock to prevent race conditions with
        concurrent broadcasts iterating the connection set.

        Args:
            session_id: The session to leave.
            websocket: The WebSocket connection to remove.
        """
        lock = self._locks.get(session_id)
        if session_id in self._connections:
            if lock is not None:
                async with lock:
                    self._connections[session_id].discard(websocket)
            else:
                self._connections[session_id].discard(websocket)
            if not self._connections[session_id]:
                del self._connections[session_id]
                self._locks.pop(session_id, None)

    async def broadcast(self, session_id: str, event: dict[str, Any]) -> None:
        """Send an event to all connected clients in a session.

        Catches per-client send errors and removes broken clients without
        affecting other connections.

        Args:
            session_id: The session to broadcast to.
            event: The event dict to send as JSON.
        """
        if session_id not in self._connections:
            return

        lock = self._locks.get(session_id)
        if lock is None:
            return

        async with lock:
            conn_set = self._connections.get(session_id)
            if conn_set is None:
                return
            broken: list[WebSocket] = []
            for ws in list(conn_set):
                try:
                    await ws.send_json(event)
                except Exception:
                    logger.debug(
                        "Removing broken WebSocket client from session %s", session_id
                    )
                    broken.append(ws)
            for ws in broken:
                conn_set.discard(ws)

    async def send_personal(
        self, websocket: WebSocket, message: dict[str, Any]
    ) -> None:
        """Send a message to a single client.

        Args:
            websocket: The target WebSocket connection.
            message: The message dict to send as JSON.
        """
        await websocket.send_json(message)

    def get_connection_count(self, session_id: str) -> int:
        """Get the number of connected clients for a session.

        Args:
            session_id: The session to check.

        Returns:
            Number of connected WebSocket clients.
        """
        return len(self._connections.get(session_id, set()))

    async def disconnect_all(self) -> None:
        """Disconnect all WebSocket clients across all sessions.

        Used during application shutdown for graceful cleanup.
        """
        for session_id in list(self._connections.keys()):
            for ws in list(self._connections.get(session_id, set())):
                try:
                    await ws.close(code=1000, reason="Server shutting down")
                except Exception:
                    pass
            self._connections.pop(session_id, None)
            self._locks.pop(session_id, None)


# Module-level singleton
manager = ConnectionManager()

router = APIRouter()


def _validate_session_id_format(session_id: str) -> bool:
    """Validate session ID format (alphanumeric, hyphens, underscores).

    Args:
        session_id: The session ID to validate.

    Returns:
        True if valid, False otherwise.
    """
    return bool(_SESSION_ID_RE.match(session_id))


def _parse_command(raw: str) -> dict[str, Any] | None:
    """Parse a raw JSON string into a command dict.

    Args:
        raw: Raw JSON string from the client.

    Returns:
        Parsed dict, or None if parsing failed (error sent separately).
    """
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        return data
    except (json.JSONDecodeError, ValueError):
        return None


def _validate_command(cmd: dict[str, Any]) -> str | None:
    """Validate a parsed command dict has required fields.

    Args:
        cmd: The parsed command dict.

    Returns:
        Error message string if invalid, None if valid.
    """
    cmd_type = cmd.get("type")
    if cmd_type is None:
        return "Missing 'type' field in message"

    if cmd_type not in _KNOWN_COMMANDS:
        return f"Unknown command type: {cmd_type}"

    required = _REQUIRED_FIELDS.get(cmd_type, [])
    for field in required:
        if field not in cmd or cmd[field] is None:
            return f"Missing '{field}' field for command '{cmd_type}'"

    return None


def _engine_event_to_schema(event: dict[str, Any]) -> dict[str, Any]:
    """Convert an engine broadcast event dict to a schema-validated dict.

    The engine broadcasts raw dicts. This function maps them to the
    appropriate Pydantic schema model and back to ensure consistent
    serialization.

    Args:
        event: Raw event dict from the engine.

    Returns:
        Schema-validated event dict.
    """
    event_type = event.get("type", "")

    if event_type == "session_state":
        return WsSessionState(state=event.get("state", {})).model_dump()
    elif event_type == "turn_update":
        return WsTurnUpdate(
            turn=event.get("turn", 0),
            agent=event.get("agent", ""),
            content=event.get("content", ""),
            state=event.get("state", {}),
        ).model_dump()
    elif event_type == "autopilot_started":
        return WsAutopilotStarted().model_dump()
    elif event_type == "autopilot_stopped":
        return WsAutopilotStopped(reason=event.get("reason", "unknown")).model_dump()
    elif event_type == "error":
        return WsError(
            message=event.get("message", "Unknown error"),
            recoverable=event.get("recoverable", True),
        ).model_dump()
    elif event_type == "drop_in":
        return WsDropIn(character=event.get("character", "")).model_dump()
    elif event_type == "release_control":
        return WsReleaseControl().model_dump()
    elif event_type == "awaiting_input":
        return WsAwaitingInput(character=event.get("character", "")).model_dump()
    else:
        # Pass through unknown event types with a warning
        logger.warning(
            "Unrecognized engine event type %r passed through without schema validation",
            event_type,
        )
        return event


async def _handle_command(
    engine: GameEngine,
    websocket: WebSocket,
    session_id: str,
    raw: str,
) -> None:
    """Parse and route a client command to the appropriate engine method.

    Sends error messages back to the client on validation or execution
    failure. Does NOT close the connection on command errors.

    Args:
        engine: The GameEngine for the session.
        websocket: The client's WebSocket connection.
        session_id: The session ID.
        raw: Raw JSON string from the client.
    """
    # Parse JSON
    cmd = _parse_command(raw)
    if cmd is None:
        await websocket.send_json(
            WsError(
                message="Invalid message format: expected JSON object",
                recoverable=True,
            ).model_dump()
        )
        return

    # Validate required fields
    error_msg = _validate_command(cmd)
    if error_msg is not None:
        await websocket.send_json(
            WsError(message=error_msg, recoverable=True).model_dump()
        )
        return

    cmd_type = cmd["type"]

    # Handle ping/pong at the WebSocket layer (not routed to engine)
    if cmd_type == "ping":
        await websocket.send_json(WsPong().model_dump())
        return

    # Route to engine method
    try:
        if cmd_type == "start_autopilot":
            speed = cmd.get("speed", "normal")
            await engine.start_autopilot(speed=speed)

        elif cmd_type == "stop_autopilot":
            await engine.stop_autopilot()

        elif cmd_type == "next_turn":
            await engine.run_turn()

        elif cmd_type == "drop_in":
            await engine.drop_in(character=cmd["character"])

        elif cmd_type == "release_control":
            await engine.release_control()

        elif cmd_type == "submit_action":
            await engine.submit_human_action(cmd["content"])

        elif cmd_type == "nudge":
            engine.submit_nudge(cmd["content"])
            # Direct broadcast ack for nudge
            await manager.broadcast(session_id, WsNudgeReceived().model_dump())

        elif cmd_type == "whisper":
            engine.submit_whisper(cmd["content"])

        elif cmd_type == "set_speed":
            engine.set_speed(cmd["speed"])
            # Direct broadcast ack for speed change
            await manager.broadcast(
                session_id,
                WsSpeedChanged(speed=cmd["speed"]).model_dump(),
            )

        elif cmd_type == "pause":
            engine.pause()
            # Direct broadcast ack for pause
            await manager.broadcast(session_id, WsPaused().model_dump())

        elif cmd_type == "resume":
            engine.resume()
            # Direct broadcast ack for resume
            await manager.broadcast(session_id, WsResumed().model_dump())

        elif cmd_type == "retry":
            await engine.retry_turn()

    except (ValueError, RuntimeError) as e:
        await websocket.send_json(
            WsError(message=str(e), recoverable=True).model_dump()
        )
    except Exception as e:
        logger.exception("Unexpected error handling command '%s'", cmd_type)
        await websocket.send_json(
            WsError(
                message=f"Internal error: {e}",
                recoverable=True,
            ).model_dump()
        )


@router.websocket("/ws/game/{session_id}")
async def game_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for real-time game streaming.

    Handles the full connection lifecycle:
    1. Validates session_id format
    2. Accepts the WebSocket connection
    3. Looks up the GameEngine for the session
    4. Registers broadcast callback (first client for session)
    5. Adds client to ConnectionManager
    6. Sends initial session_state snapshot
    7. Enters receive loop for client commands
    8. Cleans up on disconnect

    Args:
        websocket: The WebSocket connection.
        session_id: The session to stream.
    """
    # 1. Validate session_id format
    if not _validate_session_id_format(session_id):
        await websocket.accept()
        await websocket.send_json(
            WsError(
                message="Invalid session ID format",
                recoverable=False,
            ).model_dump()
        )
        await websocket.close(code=4000, reason="Invalid session ID")
        return

    # 2. Accept the WebSocket connection
    await websocket.accept()

    # 3. Look up engine from app state, auto-create if missing
    engines: dict[str, GameEngine] = websocket.app.state.engines
    if session_id not in engines:
        try:
            engine = GameEngine(session_id)
            engines[session_id] = engine
            await engine.start_session()  # Loads from checkpoint or creates default
        except Exception as e:
            logger.warning(
                "Failed to auto-create engine for session %s: %s", session_id, e
            )
            await websocket.send_json(
                WsError(
                    message=f"Failed to load session '{session_id}': {e}",
                    recoverable=False,
                ).model_dump()
            )
            await websocket.close(code=4004, reason="Session not found")
            return

    engine = engines[session_id]

    # 4. Register broadcast callback (overwrites any previous one)
    async def broadcast_to_session(event: dict[str, Any]) -> None:
        schema_event = _engine_event_to_schema(event)
        await manager.broadcast(session_id, schema_event)

    engine.set_broadcast_callback(broadcast_to_session)

    # 5. Add client to ConnectionManager
    await manager.connect(session_id, websocket)

    # 6. Send initial session_state snapshot
    try:
        snapshot = engine._get_state_snapshot()
        await websocket.send_json(WsSessionState(state=snapshot).model_dump())
    except Exception:
        logger.exception("Failed to send initial state snapshot")

    # 7. Enter receive loop
    try:
        while True:
            raw = await websocket.receive_text()
            await _handle_command(engine, websocket, session_id, raw)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error for session %s", session_id)
    finally:
        # 8. Cleanup: remove from ConnectionManager
        await manager.disconnect(session_id, websocket)
