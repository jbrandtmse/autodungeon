"""Tests for the WebSocket game streaming endpoint and ConnectionManager.

Story 16-3: WebSocket Game Streaming.
Tests cover connection lifecycle, all 11 command types, multi-client broadcast,
ConnectionManager unit tests, invalid message handling, heartbeat ping/pong,
and error propagation from engine to client.

Uses Starlette's TestClient for synchronous WebSocket testing with mocked
GameEngine instances (no real LLM calls).
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.testclient import TestClient

from api.engine import GameEngine
from api.main import app
from api.websocket import ConnectionManager, manager

# =============================================================================
# Helpers
# =============================================================================


def _make_state_snapshot(**overrides: Any) -> dict[str, Any]:
    """Create a minimal state snapshot dict for testing."""
    snapshot: dict[str, Any] = {
        "session_id": "001",
        "turn_number": 1,
        "current_turn": "dm",
        "human_active": False,
        "controlled_character": None,
        "is_paused": False,
        "speed": "normal",
        "message_count": 1,
    }
    snapshot.update(overrides)
    return snapshot


def _make_mock_engine(session_id: str = "001", **overrides: Any) -> MagicMock:
    """Create a mock GameEngine with sensible defaults.

    All async methods are AsyncMock. Synchronous methods are plain MagicMock.
    """
    engine = MagicMock(spec=GameEngine)
    engine.session_id = session_id
    engine.state = {"ground_truth_log": ["[dm]: The adventure begins."]}
    engine.is_running = False
    engine.is_paused = False
    engine.speed = "normal"
    engine.human_active = False
    engine.controlled_character = None
    engine.pending_nudge = None
    engine.last_error = None
    engine.turn_count = 0
    engine.is_generating = False

    # Async methods
    engine.start_autopilot = AsyncMock()
    engine.stop_autopilot = AsyncMock()
    engine.run_turn = AsyncMock(
        return_value={
            "type": "turn_update",
            "turn": 2,
            "agent": "dm",
            "content": "[dm]: A new dawn.",
            "state": _make_state_snapshot(),
        }
    )
    engine.drop_in = AsyncMock()
    engine.release_control = AsyncMock()
    engine.submit_human_action = AsyncMock(
        return_value={
            "type": "turn_update",
            "turn": 3,
            "agent": "rogue",
            "content": "[rogue]: I check for traps.",
            "state": _make_state_snapshot(),
        }
    )
    engine.retry_turn = AsyncMock(
        return_value={
            "type": "turn_update",
            "turn": 2,
            "agent": "dm",
            "content": "[dm]: Retry succeeded.",
            "state": _make_state_snapshot(),
        }
    )
    engine.start_session = AsyncMock()
    engine.stop_session = AsyncMock()

    # Sync methods
    engine.submit_nudge = MagicMock()
    engine.set_speed = MagicMock()
    engine.pause = MagicMock()
    engine.resume = MagicMock()
    engine.set_broadcast_callback = MagicMock()

    # State snapshot helper
    engine._get_state_snapshot = MagicMock(return_value=_make_state_snapshot())

    for k, v in overrides.items():
        setattr(engine, k, v)

    return engine


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_engine() -> MagicMock:
    """Create a mock GameEngine for session '001'."""
    return _make_mock_engine("001")


@pytest.fixture
def client_with_engine(mock_engine: MagicMock) -> Generator[TestClient, None, None]:
    """TestClient with a mock engine registered for session '001'.

    Resets the ConnectionManager singleton state between tests.
    """
    # Store original state and set up test engines
    original_engines = getattr(app.state, "engines", {})
    app.state.engines = {"001": mock_engine}

    # Clear ConnectionManager state
    manager._connections.clear()
    manager._locks.clear()

    client = TestClient(app)
    yield client

    # Restore
    app.state.engines = original_engines
    manager._connections.clear()
    manager._locks.clear()


@pytest.fixture
def empty_client() -> Generator[TestClient, None, None]:
    """TestClient with no engines registered (empty registry)."""
    original_engines = getattr(app.state, "engines", {})
    app.state.engines = {}

    manager._connections.clear()
    manager._locks.clear()

    client = TestClient(app)
    yield client

    app.state.engines = original_engines
    manager._connections.clear()
    manager._locks.clear()


# =============================================================================
# Connection Lifecycle Tests (AC1, AC6)
# =============================================================================


class TestConnectionLifecycle:
    """Test WebSocket connection acceptance, rejection, and cleanup."""

    def test_connect_valid_session(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Valid session ID connects and receives initial session_state."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            data = ws.receive_json()
            assert data["type"] == "session_state"
            assert "state" in data

    def test_connect_sends_state_snapshot(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Initial session_state contains expected snapshot fields."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            data = ws.receive_json()
            assert data["type"] == "session_state"
            state = data["state"]
            assert state["session_id"] == "001"
            assert "turn_number" in state
            assert "current_turn" in state

    def test_connect_registers_broadcast_callback(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Connecting registers a broadcast callback on the engine."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()  # consume session_state
            mock_engine.set_broadcast_callback.assert_called_once()

    def test_connect_invalid_session_id_format(
        self, client_with_engine: TestClient
    ) -> None:
        """Invalid session ID format (special chars) closes with 4000."""
        with client_with_engine.websocket_connect("/ws/game/bad!id") as ws:
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Invalid session ID" in data["message"]
            assert data["recoverable"] is False

    def test_connect_session_auto_creates_engine(self, empty_client: TestClient) -> None:
        """Connecting to a session with no engine auto-creates one."""
        with empty_client.websocket_connect("/ws/game/999") as ws:
            data = ws.receive_json()
            # Auto-create sends initial session_state, not an error
            assert data["type"] == "session_state"

    def test_connect_registers_in_connection_manager(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Connected client is tracked in ConnectionManager."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()  # consume session_state
            assert manager.get_connection_count("001") == 1

    def test_disconnect_removes_from_connection_manager(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Disconnecting removes client from ConnectionManager."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
        # After context manager exits, client is disconnected
        assert manager.get_connection_count("001") == 0

    def test_disconnect_does_not_stop_engine(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Disconnecting the last client does NOT stop the engine."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
        # Engine stop_session should NOT have been called
        mock_engine.stop_session.assert_not_called()

    def test_reconnect_receives_fresh_state(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Reconnecting sends a fresh session_state snapshot."""
        # First connection
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            data1 = ws.receive_json()
            assert data1["type"] == "session_state"

        # Second connection
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            data2 = ws.receive_json()
            assert data2["type"] == "session_state"


# =============================================================================
# Command Tests - Happy Path (AC3)
# =============================================================================


class TestCommandStartAutopilot:
    """Test start_autopilot command."""

    def test_start_autopilot_default_speed(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """start_autopilot with default speed calls engine correctly."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()  # session_state
            ws.send_json({"type": "start_autopilot"})
        mock_engine.start_autopilot.assert_awaited_once_with(speed="normal")

    def test_start_autopilot_explicit_speed(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """start_autopilot with explicit speed passes it to engine."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "start_autopilot", "speed": "fast"})
        mock_engine.start_autopilot.assert_awaited_once_with(speed="fast")


class TestCommandStopAutopilot:
    """Test stop_autopilot command."""

    def test_stop_autopilot(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """stop_autopilot calls engine.stop_autopilot()."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "stop_autopilot"})
        mock_engine.stop_autopilot.assert_awaited_once()


class TestCommandNextTurn:
    """Test next_turn command."""

    def test_next_turn(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """next_turn calls engine.run_turn()."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "next_turn"})
        mock_engine.run_turn.assert_awaited_once()


class TestCommandDropIn:
    """Test drop_in command."""

    def test_drop_in(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """drop_in with character calls engine.drop_in()."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "drop_in", "character": "rogue"})
        mock_engine.drop_in.assert_awaited_once_with(character="rogue")


class TestCommandReleaseControl:
    """Test release_control command."""

    def test_release_control(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """release_control calls engine.release_control()."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "release_control"})
        mock_engine.release_control.assert_awaited_once()


class TestCommandSubmitAction:
    """Test submit_action command."""

    def test_submit_action(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """submit_action passes content to engine."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "submit_action", "content": "I check for traps"})
        mock_engine.submit_human_action.assert_awaited_once_with("I check for traps")


class TestCommandNudge:
    """Test nudge command."""

    def test_nudge(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """nudge passes content to engine and broadcasts nudge_received."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()  # session_state
            ws.send_json({"type": "nudge", "content": "Try the tavern"})
            data = ws.receive_json()
            assert data["type"] == "nudge_received"
        mock_engine.submit_nudge.assert_called_once_with("Try the tavern")


class TestCommandSetSpeed:
    """Test set_speed command."""

    def test_set_speed(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """set_speed calls engine and broadcasts speed_changed."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "set_speed", "speed": "fast"})
            data = ws.receive_json()
            assert data["type"] == "speed_changed"
            assert data["speed"] == "fast"
        mock_engine.set_speed.assert_called_once_with("fast")


class TestCommandPause:
    """Test pause command."""

    def test_pause(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """pause calls engine and broadcasts paused."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "pause"})
            data = ws.receive_json()
            assert data["type"] == "paused"
        mock_engine.pause.assert_called_once()


class TestCommandResume:
    """Test resume command."""

    def test_resume(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """resume calls engine and broadcasts resumed."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "resume"})
            data = ws.receive_json()
            assert data["type"] == "resumed"
        mock_engine.resume.assert_called_once()


class TestCommandRetry:
    """Test retry command."""

    def test_retry(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """retry calls engine.retry_turn()."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "retry"})
        mock_engine.retry_turn.assert_awaited_once()


# =============================================================================
# Heartbeat Tests (AC7)
# =============================================================================


class TestHeartbeat:
    """Test ping/pong heartbeat mechanism."""

    def test_ping_returns_pong(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Client ping gets server pong response."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()  # session_state
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_ping_does_not_invoke_engine(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Ping command does not call any engine methods."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "ping"})
            ws.receive_json()  # pong
        # No engine methods should be called
        mock_engine.run_turn.assert_not_awaited()
        mock_engine.start_autopilot.assert_not_awaited()


# =============================================================================
# Error Handling Tests (AC4)
# =============================================================================


class TestInvalidMessages:
    """Test handling of malformed client messages."""

    def test_invalid_json(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Invalid JSON sends error but keeps connection open."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()  # session_state
            ws.send_text("not json at all")
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Invalid message format" in data["message"]
            assert data["recoverable"] is True
            # Connection should still work
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"

    def test_missing_type_field(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """JSON without 'type' field sends error."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"content": "hello"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Missing 'type'" in data["message"]
            assert data["recoverable"] is True

    def test_unknown_command_type(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Unknown command type sends error."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "fly_to_moon"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Unknown command type: fly_to_moon" in data["message"]
            assert data["recoverable"] is True

    def test_drop_in_missing_character(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """drop_in without character field sends error."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "drop_in"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "character" in data["message"]
            assert data["recoverable"] is True

    def test_submit_action_missing_content(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """submit_action without content field sends error."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "submit_action"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "content" in data["message"]

    def test_nudge_missing_content(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """nudge without content field sends error."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "nudge"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "content" in data["message"]

    def test_set_speed_missing_speed(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """set_speed without speed field sends error."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "set_speed"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "speed" in data["message"]


# =============================================================================
# Engine Error Propagation Tests (AC4)
# =============================================================================


class TestEngineErrors:
    """Test that engine exceptions are caught and sent as error messages."""

    def test_start_autopilot_already_running(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """RuntimeError from start_autopilot is sent as error message."""
        mock_engine.start_autopilot = AsyncMock(
            side_effect=RuntimeError("Autopilot is already running.")
        )
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "start_autopilot"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "already running" in data["message"]
            assert data["recoverable"] is True

    def test_start_autopilot_invalid_speed(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """ValueError from start_autopilot is sent as error message."""
        mock_engine.start_autopilot = AsyncMock(
            side_effect=ValueError("Invalid speed 'ludicrous'.")
        )
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "start_autopilot", "speed": "ludicrous"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Invalid speed" in data["message"]

    def test_drop_in_invalid_character(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """ValueError from drop_in (e.g., 'dm') is sent as error."""
        mock_engine.drop_in = AsyncMock(
            side_effect=ValueError("Cannot drop in as 'dm'.")
        )
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "drop_in", "character": "dm"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "dm" in data["message"]

    def test_run_turn_no_state(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """RuntimeError from run_turn (no state) is sent as error."""
        mock_engine.run_turn = AsyncMock(
            side_effect=RuntimeError("No game state loaded.")
        )
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "next_turn"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "No game state" in data["message"]

    def test_retry_max_attempts(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """RuntimeError from retry_turn (max retries) is sent as error."""
        mock_engine.retry_turn = AsyncMock(
            side_effect=RuntimeError("Max retry attempts (3) exceeded.")
        )
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "retry"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Max retry" in data["message"]

    def test_submit_action_not_active(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """RuntimeError from submit_human_action (not active) is sent as error."""
        mock_engine.submit_human_action = AsyncMock(
            side_effect=RuntimeError("Human control is not active.")
        )
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "submit_action", "content": "I attack"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "not active" in data["message"]

    def test_nudge_empty_raises(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """ValueError from submit_nudge (empty text) is sent as error."""
        mock_engine.submit_nudge = MagicMock(
            side_effect=ValueError("Nudge text cannot be empty.")
        )
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "nudge", "content": "   "})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "empty" in data["message"]

    def test_set_speed_invalid(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """ValueError from set_speed is sent as error."""
        mock_engine.set_speed = MagicMock(
            side_effect=ValueError("Invalid speed 'warp'.")
        )
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "set_speed", "speed": "warp"})
            data = ws.receive_json()
            assert data["type"] == "error"
            assert "Invalid speed" in data["message"]

    def test_error_keeps_connection_open(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Engine errors do NOT close the WebSocket connection."""
        mock_engine.run_turn = AsyncMock(
            side_effect=RuntimeError("No game state loaded.")
        )
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            ws.send_json({"type": "next_turn"})
            error = ws.receive_json()
            assert error["type"] == "error"
            # Connection should still be alive -- send ping
            ws.send_json({"type": "ping"})
            pong = ws.receive_json()
            assert pong["type"] == "pong"


# =============================================================================
# Multi-Client Tests (AC5)
# =============================================================================


class TestMultiClient:
    """Test multiple clients connected to the same session."""

    def test_two_clients_both_receive_ack(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Two clients both receive broadcast acknowledgments."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws1:
            ws1.receive_json()  # session_state
            with client_with_engine.websocket_connect("/ws/game/001") as ws2:
                ws2.receive_json()  # session_state
                assert manager.get_connection_count("001") == 2

                # Client 1 sends pause -- both should receive
                ws1.send_json({"type": "pause"})
                data1 = ws1.receive_json()
                data2 = ws2.receive_json()
                assert data1["type"] == "paused"
                assert data2["type"] == "paused"

    def test_client_disconnect_does_not_affect_other(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """When one client disconnects, the other still receives events."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws1:
            ws1.receive_json()
            with client_with_engine.websocket_connect("/ws/game/001") as ws2:
                ws2.receive_json()
                assert manager.get_connection_count("001") == 2
            # ws2 disconnected
            assert manager.get_connection_count("001") == 1
            # ws1 should still work
            ws1.send_json({"type": "ping"})
            pong = ws1.receive_json()
            assert pong["type"] == "pong"

    def test_two_clients_nudge_broadcast(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Nudge from one client broadcasts nudge_received to all."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws1:
            ws1.receive_json()
            with client_with_engine.websocket_connect("/ws/game/001") as ws2:
                ws2.receive_json()
                ws1.send_json({"type": "nudge", "content": "Talk to innkeeper"})
                # Both should receive nudge_received
                data1 = ws1.receive_json()
                data2 = ws2.receive_json()
                assert data1["type"] == "nudge_received"
                assert data2["type"] == "nudge_received"

    def test_two_clients_speed_change_broadcast(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Speed change from one client broadcasts to all."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws1:
            ws1.receive_json()
            with client_with_engine.websocket_connect("/ws/game/001") as ws2:
                ws2.receive_json()
                ws2.send_json({"type": "set_speed", "speed": "slow"})
                data1 = ws1.receive_json()
                data2 = ws2.receive_json()
                assert data1["type"] == "speed_changed"
                assert data1["speed"] == "slow"
                assert data2["type"] == "speed_changed"

    def test_two_clients_resume_broadcast(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Resume from one client broadcasts to all."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws1:
            ws1.receive_json()
            with client_with_engine.websocket_connect("/ws/game/001") as ws2:
                ws2.receive_json()
                ws1.send_json({"type": "resume"})
                data1 = ws1.receive_json()
                data2 = ws2.receive_json()
                assert data1["type"] == "resumed"
                assert data2["type"] == "resumed"

    def test_connection_count(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Connection count tracks clients accurately."""
        assert manager.get_connection_count("001") == 0
        with client_with_engine.websocket_connect("/ws/game/001") as ws1:
            ws1.receive_json()
            assert manager.get_connection_count("001") == 1
            with client_with_engine.websocket_connect("/ws/game/001") as ws2:
                ws2.receive_json()
                assert manager.get_connection_count("001") == 2
            assert manager.get_connection_count("001") == 1
        assert manager.get_connection_count("001") == 0


# =============================================================================
# ConnectionManager Unit Tests
# =============================================================================


class TestConnectionManager:
    """Unit tests for the ConnectionManager class."""

    @pytest.mark.anyio
    async def test_connect_adds_to_set(self) -> None:
        """connect() adds WebSocket to session's connection set."""
        mgr = ConnectionManager()
        ws = MagicMock()
        await mgr.connect("sess1", ws)
        assert mgr.get_connection_count("sess1") == 1

    @pytest.mark.anyio
    async def test_connect_multiple_sessions(self) -> None:
        """Connections in different sessions are independent."""
        mgr = ConnectionManager()
        ws1 = MagicMock()
        ws2 = MagicMock()
        await mgr.connect("sess1", ws1)
        await mgr.connect("sess2", ws2)
        assert mgr.get_connection_count("sess1") == 1
        assert mgr.get_connection_count("sess2") == 1

    @pytest.mark.anyio
    async def test_disconnect_removes_from_set(self) -> None:
        """disconnect() removes WebSocket from session's connection set."""
        mgr = ConnectionManager()
        ws = MagicMock()
        await mgr.connect("sess1", ws)
        await mgr.disconnect("sess1", ws)
        assert mgr.get_connection_count("sess1") == 0

    @pytest.mark.anyio
    async def test_disconnect_last_cleans_up(self) -> None:
        """Disconnecting the last client cleans up internal data structures."""
        mgr = ConnectionManager()
        ws = MagicMock()
        await mgr.connect("sess1", ws)
        await mgr.disconnect("sess1", ws)
        assert "sess1" not in mgr._connections
        assert "sess1" not in mgr._locks

    @pytest.mark.anyio
    async def test_disconnect_nonexistent_session(self) -> None:
        """disconnect() for unknown session is a no-op."""
        mgr = ConnectionManager()
        ws = MagicMock()
        await mgr.disconnect("unknown", ws)  # Should not raise

    @pytest.mark.anyio
    async def test_broadcast_sends_to_all(self) -> None:
        """broadcast() sends to all clients in the session."""
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await mgr.connect("sess1", ws1)
        await mgr.connect("sess1", ws2)

        event = {"type": "test", "data": "hello"}
        await mgr.broadcast("sess1", event)

        ws1.send_json.assert_awaited_once_with(event)
        ws2.send_json.assert_awaited_once_with(event)

    @pytest.mark.anyio
    async def test_broadcast_empty_session(self) -> None:
        """broadcast() to an empty/unknown session is a no-op."""
        mgr = ConnectionManager()
        await mgr.broadcast("unknown", {"type": "test"})  # Should not raise

    @pytest.mark.anyio
    async def test_broadcast_removes_broken_client(self) -> None:
        """broadcast() removes clients that raise on send."""
        mgr = ConnectionManager()
        good_ws = AsyncMock()
        bad_ws = AsyncMock()
        bad_ws.send_json.side_effect = RuntimeError("Connection lost")

        await mgr.connect("sess1", good_ws)
        await mgr.connect("sess1", bad_ws)
        assert mgr.get_connection_count("sess1") == 2

        await mgr.broadcast("sess1", {"type": "test"})

        # Good client received the message
        good_ws.send_json.assert_awaited_once()
        # Bad client was removed
        assert mgr.get_connection_count("sess1") == 1

    @pytest.mark.anyio
    async def test_broadcast_broken_client_does_not_crash_others(self) -> None:
        """A broken client does not prevent others from receiving events."""
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()
        ws2.send_json.side_effect = RuntimeError("Broken pipe")

        await mgr.connect("sess1", ws1)
        await mgr.connect("sess1", ws2)
        await mgr.connect("sess1", ws3)

        await mgr.broadcast("sess1", {"type": "hello"})

        ws1.send_json.assert_awaited_once()
        ws3.send_json.assert_awaited_once()

    @pytest.mark.anyio
    async def test_get_connection_count_unknown_session(self) -> None:
        """get_connection_count returns 0 for unknown session."""
        mgr = ConnectionManager()
        assert mgr.get_connection_count("nonexistent") == 0

    @pytest.mark.anyio
    async def test_disconnect_all(self) -> None:
        """disconnect_all() closes all connections and clears state."""
        mgr = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await mgr.connect("sess1", ws1)
        await mgr.connect("sess2", ws2)

        await mgr.disconnect_all()

        assert mgr.get_connection_count("sess1") == 0
        assert mgr.get_connection_count("sess2") == 0
        assert len(mgr._connections) == 0
        assert len(mgr._locks) == 0

    @pytest.mark.anyio
    async def test_disconnect_all_handles_close_error(self) -> None:
        """disconnect_all() handles errors from ws.close() gracefully."""
        mgr = ConnectionManager()
        ws = AsyncMock()
        ws.close.side_effect = RuntimeError("Already closed")
        await mgr.connect("sess1", ws)

        await mgr.disconnect_all()  # Should not raise
        assert len(mgr._connections) == 0

    @pytest.mark.anyio
    async def test_send_personal(self) -> None:
        """send_personal() sends message to a single client."""
        mgr = ConnectionManager()
        ws = AsyncMock()
        msg = {"type": "test", "data": "personal"}
        await mgr.send_personal(ws, msg)
        ws.send_json.assert_awaited_once_with(msg)


# =============================================================================
# Broadcast Callback Integration Tests (AC8)
# =============================================================================


class TestBroadcastCallbackIntegration:
    """Test the broadcast callback wiring between engine and WebSocket."""

    def test_callback_registered_on_connect(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Broadcast callback is registered when client connects."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws:
            ws.receive_json()
            mock_engine.set_broadcast_callback.assert_called_once()
            callback = mock_engine.set_broadcast_callback.call_args[0][0]
            assert callable(callback)

    def test_callback_registered_once_per_session_connect(
        self, client_with_engine: TestClient, mock_engine: MagicMock
    ) -> None:
        """Each connection registers a callback (latest wins)."""
        with client_with_engine.websocket_connect("/ws/game/001") as ws1:
            ws1.receive_json()
            with client_with_engine.websocket_connect("/ws/game/001") as ws2:
                ws2.receive_json()
        # Two connections = two callback registrations (each overwrites)
        assert mock_engine.set_broadcast_callback.call_count == 2


# =============================================================================
# Schema Validation Tests (AC9)
# =============================================================================


class TestSchemaValidation:
    """Test that WebSocket message schemas are correctly defined."""

    def test_ws_session_state_schema(self) -> None:
        """WsSessionState has correct type literal and state field."""
        from api.schemas import WsSessionState

        msg = WsSessionState(state={"session_id": "001"})
        dumped = msg.model_dump()
        assert dumped["type"] == "session_state"
        assert dumped["state"]["session_id"] == "001"

    def test_ws_turn_update_schema(self) -> None:
        """WsTurnUpdate has correct fields."""
        from api.schemas import WsTurnUpdate

        msg = WsTurnUpdate(turn=1, agent="dm", content="Hello", state={})
        dumped = msg.model_dump()
        assert dumped["type"] == "turn_update"
        assert dumped["turn"] == 1
        assert dumped["agent"] == "dm"

    def test_ws_autopilot_started_schema(self) -> None:
        """WsAutopilotStarted has correct type."""
        from api.schemas import WsAutopilotStarted

        msg = WsAutopilotStarted()
        assert msg.model_dump()["type"] == "autopilot_started"

    def test_ws_autopilot_stopped_schema(self) -> None:
        """WsAutopilotStopped has correct type and reason."""
        from api.schemas import WsAutopilotStopped

        msg = WsAutopilotStopped(reason="user_request")
        dumped = msg.model_dump()
        assert dumped["type"] == "autopilot_stopped"
        assert dumped["reason"] == "user_request"

    def test_ws_error_schema(self) -> None:
        """WsError has correct fields."""
        from api.schemas import WsError

        msg = WsError(message="Something broke", recoverable=False)
        dumped = msg.model_dump()
        assert dumped["type"] == "error"
        assert dumped["message"] == "Something broke"
        assert dumped["recoverable"] is False

    def test_ws_drop_in_schema(self) -> None:
        """WsDropIn has correct type and character."""
        from api.schemas import WsDropIn

        msg = WsDropIn(character="rogue")
        assert msg.model_dump()["character"] == "rogue"

    def test_ws_release_control_schema(self) -> None:
        """WsReleaseControl has correct type."""
        from api.schemas import WsReleaseControl

        msg = WsReleaseControl()
        assert msg.model_dump()["type"] == "release_control"

    def test_ws_nudge_received_schema(self) -> None:
        """WsNudgeReceived has correct type."""
        from api.schemas import WsNudgeReceived

        msg = WsNudgeReceived()
        assert msg.model_dump()["type"] == "nudge_received"

    def test_ws_speed_changed_schema(self) -> None:
        """WsSpeedChanged has correct type and speed."""
        from api.schemas import WsSpeedChanged

        msg = WsSpeedChanged(speed="fast")
        dumped = msg.model_dump()
        assert dumped["type"] == "speed_changed"
        assert dumped["speed"] == "fast"

    def test_ws_paused_schema(self) -> None:
        """WsPaused has correct type."""
        from api.schemas import WsPaused

        assert WsPaused().model_dump()["type"] == "paused"

    def test_ws_resumed_schema(self) -> None:
        """WsResumed has correct type."""
        from api.schemas import WsResumed

        assert WsResumed().model_dump()["type"] == "resumed"

    def test_ws_pong_schema(self) -> None:
        """WsPong has correct type."""
        from api.schemas import WsPong

        assert WsPong().model_dump()["type"] == "pong"

    def test_ws_command_ack_schema(self) -> None:
        """WsCommandAck has correct type and command."""
        from api.schemas import WsCommandAck

        msg = WsCommandAck(command="start_autopilot")
        dumped = msg.model_dump()
        assert dumped["type"] == "command_ack"
        assert dumped["command"] == "start_autopilot"

    def test_ws_awaiting_input_schema(self) -> None:
        """WsAwaitingInput has correct type and character."""
        from api.schemas import WsAwaitingInput

        msg = WsAwaitingInput(character="rogue")
        dumped = msg.model_dump()
        assert dumped["type"] == "awaiting_input"
        assert dumped["character"] == "rogue"


# =============================================================================
# No Streamlit Dependency Tests
# =============================================================================


class TestNoStreamlitDependency:
    """Verify api/websocket.py has no Streamlit imports."""

    def test_no_streamlit_import_in_source(self) -> None:
        """websocket.py source contains no 'import streamlit' references."""
        import inspect

        import api.websocket as ws_mod

        source = inspect.getsource(ws_mod)
        assert "import streamlit" not in source
        assert "st.session_state" not in source
