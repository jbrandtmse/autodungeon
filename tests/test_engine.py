"""Tests for the GameEngine service class.

Story 16-2: Game Engine Extraction.
Tests cover all GameEngine methods: lifecycle, turn execution, autopilot,
pause/resume, speed, drop-in/release, nudge, retry, broadcast callbacks,
and error handling. Uses mocked run_single_round() -- no real LLM calls.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from api.engine import GameEngine
from models import (
    AgentMemory,
    GameState,
    create_initial_game_state,
    create_user_error,
)

# =============================================================================
# Fixtures
# =============================================================================


def _make_game_state(**overrides: Any) -> GameState:
    """Create a minimal GameState for testing.

    Uses create_initial_game_state() as a base and applies overrides.
    """
    state = create_initial_game_state()
    state["turn_queue"] = ["dm", "fighter", "rogue"]
    state["current_turn"] = "dm"
    state["session_id"] = "001"
    state["ground_truth_log"] = ["[dm]: The adventure begins."]
    state["agent_memories"] = {
        "dm": AgentMemory(token_limit=8000),
        "fighter": AgentMemory(token_limit=4000),
        "rogue": AgentMemory(token_limit=4000),
    }
    for k, v in overrides.items():
        state[k] = v  # type: ignore[literal-required]
    return state


def _make_result_state(
    state: GameState, extra_log: str = "[dm]: A new dawn."
) -> dict[str, Any]:
    """Create a successful run_single_round result from a base state."""
    result = dict(state)
    log = list(result.get("ground_truth_log", []))
    log.append(extra_log)
    result["ground_truth_log"] = log
    return result


def _make_error_result(state: GameState) -> dict[str, Any]:
    """Create a run_single_round result with an error key."""
    result = dict(state)
    result["error"] = create_user_error(
        error_type="timeout",
        provider="gemini",
        agent="dm",
    )
    return result


@pytest.fixture
def temp_campaigns_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Patch CAMPAIGNS_DIR to a temp directory for test isolation."""
    temp_campaigns = tmp_path / "campaigns"
    temp_campaigns.mkdir()
    with patch("persistence.CAMPAIGNS_DIR", temp_campaigns):
        yield temp_campaigns


@pytest.fixture
def engine() -> GameEngine:
    """Create a fresh GameEngine for testing."""
    return GameEngine(session_id="test-001")


@pytest.fixture
def started_engine() -> GameEngine:
    """Create a GameEngine with pre-loaded state (no I/O)."""
    eng = GameEngine(session_id="test-001")
    eng._state = _make_game_state()
    return eng


@pytest.fixture
def broadcast_events() -> list[dict[str, Any]]:
    """Collector for broadcast events."""
    return []


@pytest.fixture
def engine_with_broadcast(
    started_engine: GameEngine, broadcast_events: list[dict[str, Any]]
) -> GameEngine:
    """Engine with a broadcast callback that collects events."""

    async def collector(event: dict[str, Any]) -> None:
        broadcast_events.append(event)

    started_engine.set_broadcast_callback(collector)
    return started_engine


# =============================================================================
# Test Construction and Properties (AC1)
# =============================================================================


class TestConstruction:
    """Test GameEngine initialization and property defaults."""

    def test_session_id(self, engine: GameEngine) -> None:
        """session_id property returns the ID set in constructor."""
        assert engine.session_id == "test-001"

    def test_initial_state_is_none(self, engine: GameEngine) -> None:
        """State is None before start_session."""
        assert engine.state is None

    def test_is_running_false_initially(self, engine: GameEngine) -> None:
        """is_running is False before autopilot is started."""
        assert engine.is_running is False

    def test_is_paused_false_initially(self, engine: GameEngine) -> None:
        """is_paused is False by default."""
        assert engine.is_paused is False

    def test_default_speed(self, engine: GameEngine) -> None:
        """Default speed is 'normal'."""
        assert engine.speed == "normal"

    def test_human_active_false_initially(self, engine: GameEngine) -> None:
        """human_active is False by default."""
        assert engine.human_active is False

    def test_controlled_character_none_initially(self, engine: GameEngine) -> None:
        """controlled_character is None by default."""
        assert engine.controlled_character is None

    def test_pending_nudge_none_initially(self, engine: GameEngine) -> None:
        """pending_nudge is None by default."""
        assert engine.pending_nudge is None

    def test_last_error_none_initially(self, engine: GameEngine) -> None:
        """last_error is None by default."""
        assert engine.last_error is None

    def test_turn_count_zero_initially(self, engine: GameEngine) -> None:
        """turn_count is 0 by default."""
        assert engine.turn_count == 0

    def test_is_generating_false_initially(self, engine: GameEngine) -> None:
        """is_generating is False by default."""
        assert engine.is_generating is False


# =============================================================================
# Test Session Lifecycle (AC2)
# =============================================================================


class TestSessionLifecycle:
    """Test start_session and stop_session."""

    @pytest.mark.anyio
    async def test_start_session_fresh_state(self, engine: GameEngine) -> None:
        """start_session creates fresh state when no checkpoint exists."""
        with (
            patch("persistence.get_latest_checkpoint", return_value=None),
            patch("models.populate_game_state", return_value=_make_game_state()),
        ):
            await engine.start_session()

        assert engine.state is not None
        assert engine.state["session_id"] == "test-001"

    @pytest.mark.anyio
    async def test_start_session_loads_checkpoint(self, engine: GameEngine) -> None:
        """start_session loads latest checkpoint when available."""
        saved_state = _make_game_state()
        saved_state["ground_truth_log"] = ["[dm]: Saved game."]

        with (
            patch("persistence.get_latest_checkpoint", return_value=5),
            patch("persistence.load_checkpoint", return_value=saved_state),
        ):
            await engine.start_session()

        assert engine.state is not None
        assert engine.state["ground_truth_log"] == ["[dm]: Saved game."]

    @pytest.mark.anyio
    async def test_start_session_checkpoint_corrupt_falls_back(
        self, engine: GameEngine
    ) -> None:
        """start_session creates fresh state when checkpoint is corrupt."""
        with (
            patch("persistence.get_latest_checkpoint", return_value=5),
            patch("persistence.load_checkpoint", return_value=None),
            patch("models.populate_game_state", return_value=_make_game_state()),
        ):
            await engine.start_session()

        assert engine.state is not None

    @pytest.mark.anyio
    async def test_start_session_syncs_human_state(self, engine: GameEngine) -> None:
        """start_session syncs human_active/controlled_character from checkpoint."""
        saved_state = _make_game_state(human_active=True, controlled_character="rogue")
        with (
            patch("persistence.get_latest_checkpoint", return_value=1),
            patch("persistence.load_checkpoint", return_value=saved_state),
        ):
            await engine.start_session()

        assert engine.human_active is True
        assert engine.controlled_character == "rogue"

    @pytest.mark.anyio
    async def test_start_session_broadcasts_state(self, engine: GameEngine) -> None:
        """start_session broadcasts a session_state event."""
        events: list[dict[str, Any]] = []

        async def collector(event: dict[str, Any]) -> None:
            events.append(event)

        engine.set_broadcast_callback(collector)

        with (
            patch("persistence.get_latest_checkpoint", return_value=None),
            patch("models.populate_game_state", return_value=_make_game_state()),
        ):
            await engine.start_session()

        assert len(events) == 1
        assert events[0]["type"] == "session_state"

    @pytest.mark.anyio
    async def test_stop_session_saves_checkpoint(
        self, started_engine: GameEngine, temp_campaigns_dir: Path
    ) -> None:
        """stop_session saves a checkpoint before clearing state."""
        mock_save = MagicMock()
        with patch("persistence.save_checkpoint", mock_save):
            await started_engine.stop_session()

        mock_save.assert_called_once()
        assert started_engine.state is None

    @pytest.mark.anyio
    async def test_stop_session_clears_all_fields(
        self, started_engine: GameEngine
    ) -> None:
        """stop_session resets all engine fields."""
        started_engine._human_active = True
        started_engine._controlled_character = "rogue"
        started_engine._pending_nudge = "hello"
        started_engine._last_error = create_user_error("unknown")
        started_engine._retry_count = 2
        started_engine._turn_count = 10

        with patch("persistence.save_checkpoint"):
            await started_engine.stop_session()

        assert started_engine.state is None
        assert started_engine.human_active is False
        assert started_engine.controlled_character is None
        assert started_engine.pending_nudge is None
        assert started_engine.last_error is None
        assert started_engine.turn_count == 0

    @pytest.mark.anyio
    async def test_stop_session_stops_autopilot(
        self, started_engine: GameEngine
    ) -> None:
        """stop_session stops autopilot if it's running."""
        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.start_autopilot()
            assert started_engine.is_running

        with patch("persistence.save_checkpoint"):
            await started_engine.stop_session()

        assert started_engine.is_running is False

    @pytest.mark.anyio
    async def test_stop_session_handles_save_error(
        self, started_engine: GameEngine
    ) -> None:
        """stop_session handles checkpoint save failure gracefully."""
        with patch("persistence.save_checkpoint", side_effect=OSError("disk full")):
            await started_engine.stop_session()  # Should not raise

        assert started_engine.state is None


# =============================================================================
# Test Turn Execution (AC3, AC10)
# =============================================================================


class TestTurnExecution:
    """Test run_turn() and error handling."""

    @pytest.mark.anyio
    async def test_run_turn_success(self, started_engine: GameEngine) -> None:
        """run_turn returns turn_update on success."""
        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            result = await started_engine.run_turn()

        assert result["type"] == "turn_update"
        assert result["turn"] == 2  # Original had 1, now 2

    @pytest.mark.anyio
    async def test_run_turn_updates_state(self, started_engine: GameEngine) -> None:
        """run_turn updates engine state with result."""
        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.run_turn()

        assert started_engine.state is not None
        assert len(started_engine.state["ground_truth_log"]) == 2

    @pytest.mark.anyio
    async def test_run_turn_clears_error_on_success(
        self, started_engine: GameEngine
    ) -> None:
        """Successful turn clears last_error and retry_count."""
        started_engine._last_error = create_user_error("timeout")
        started_engine._retry_count = 2

        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.run_turn()

        assert started_engine.last_error is None
        assert started_engine._retry_count == 0

    @pytest.mark.anyio
    async def test_run_turn_error_in_result(self, started_engine: GameEngine) -> None:
        """run_turn handles error in result without corrupting state."""
        mock_result = _make_error_result(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            result = await started_engine.run_turn()

        assert result["type"] == "error"
        assert started_engine.last_error is not None
        # State should NOT be updated with error result
        assert len(started_engine.state["ground_truth_log"]) == 1  # type: ignore[index]

    @pytest.mark.anyio
    async def test_run_turn_exception(self, started_engine: GameEngine) -> None:
        """run_turn handles unexpected exception."""
        with patch("graph.run_single_round", side_effect=RuntimeError("kaboom")):
            result = await started_engine.run_turn()

        assert result["type"] == "error"
        assert started_engine.last_error is not None

    @pytest.mark.anyio
    async def test_run_turn_no_state_raises(self, engine: GameEngine) -> None:
        """run_turn raises RuntimeError if no state loaded."""
        with pytest.raises(RuntimeError, match="No game state loaded"):
            await engine.run_turn()

    @pytest.mark.anyio
    async def test_run_turn_broadcasts_turn_update(
        self,
        engine_with_broadcast: GameEngine,
        broadcast_events: list[dict[str, Any]],
    ) -> None:
        """run_turn broadcasts turn_update event on success."""
        mock_result = _make_result_state(engine_with_broadcast._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await engine_with_broadcast.run_turn()

        turn_events = [e for e in broadcast_events if e["type"] == "turn_update"]
        assert len(turn_events) == 1

    @pytest.mark.anyio
    async def test_run_turn_broadcasts_error(
        self,
        engine_with_broadcast: GameEngine,
        broadcast_events: list[dict[str, Any]],
    ) -> None:
        """run_turn broadcasts error event on failure."""
        mock_result = _make_error_result(engine_with_broadcast._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await engine_with_broadcast.run_turn()

        error_events = [e for e in broadcast_events if e["type"] == "error"]
        assert len(error_events) == 1

    @pytest.mark.anyio
    async def test_run_turn_injects_nudge(self, started_engine: GameEngine) -> None:
        """run_turn injects pending nudge into state before executing."""
        started_engine._pending_nudge = "Try the tavern"

        injected_state: dict[str, Any] = {}

        def capture_state(state: Any) -> dict[str, Any]:
            injected_state.update(dict(state))
            return _make_result_state(state)

        with patch("graph.run_single_round", side_effect=capture_state):
            await started_engine.run_turn()

        assert injected_state.get("pending_nudge") == "Try the tavern"
        # Nudge should be cleared after successful turn
        assert started_engine.pending_nudge is None

    @pytest.mark.anyio
    async def test_is_generating_during_turn(self, started_engine: GameEngine) -> None:
        """is_generating is True while turn is executing."""
        was_generating = False

        def check_generating(state: Any) -> dict[str, Any]:
            nonlocal was_generating
            was_generating = started_engine.is_generating
            return _make_result_state(state)

        with patch("graph.run_single_round", side_effect=check_generating):
            await started_engine.run_turn()

        assert was_generating is True
        assert started_engine.is_generating is False


# =============================================================================
# Test Retry (AC10)
# =============================================================================


class TestRetry:
    """Test retry_turn behavior."""

    @pytest.mark.anyio
    async def test_retry_success(self, started_engine: GameEngine) -> None:
        """retry_turn re-executes and clears error on success."""
        started_engine._last_error = create_user_error("timeout")

        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            result = await started_engine.retry_turn()

        assert result["type"] == "turn_update"
        assert started_engine.last_error is None

    @pytest.mark.anyio
    async def test_retry_increments_count(self, started_engine: GameEngine) -> None:
        """retry_turn increments retry_count (tracks even on subsequent errors)."""
        # Use an error result so _retry_count is NOT reset by success path
        mock_result = _make_error_result(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.retry_turn()
        assert started_engine._retry_count == 1

    @pytest.mark.anyio
    async def test_retry_enforces_max_attempts(
        self, started_engine: GameEngine
    ) -> None:
        """retry_turn raises RuntimeError after MAX_RETRY_ATTEMPTS."""
        started_engine._retry_count = GameEngine.MAX_RETRY_ATTEMPTS

        with pytest.raises(RuntimeError, match="Max retry attempts"):
            await started_engine.retry_turn()

    @pytest.mark.anyio
    async def test_retry_no_state_raises(self, engine: GameEngine) -> None:
        """retry_turn raises RuntimeError if no state loaded."""
        with pytest.raises(RuntimeError, match="No game state loaded"):
            await engine.retry_turn()

    @pytest.mark.anyio
    async def test_retry_preserves_state_on_error(
        self, started_engine: GameEngine
    ) -> None:
        """retry_turn preserves state when the retry also fails."""
        original_log_len = len(started_engine._state.get("ground_truth_log", []))  # type: ignore[union-attr]
        mock_result = _make_error_result(started_engine._state)  # type: ignore[arg-type]

        with patch("graph.run_single_round", return_value=mock_result):
            result = await started_engine.retry_turn()

        assert result["type"] == "error"
        assert len(started_engine.state["ground_truth_log"]) == original_log_len  # type: ignore[index]


# =============================================================================
# Test Autopilot (AC4, AC5, AC6)
# =============================================================================


class TestAutopilot:
    """Test autopilot lifecycle: start, stop, pause, resume, speed."""

    @pytest.mark.anyio
    async def test_start_autopilot_creates_task(
        self, started_engine: GameEngine
    ) -> None:
        """start_autopilot creates an asyncio task."""
        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.start_autopilot()
            assert started_engine.is_running

            # Clean up
            await started_engine.stop_autopilot()

    @pytest.mark.anyio
    async def test_start_autopilot_sets_speed(self, started_engine: GameEngine) -> None:
        """start_autopilot uses the given speed."""
        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.start_autopilot(speed="fast")
            assert started_engine.speed == "fast"
            await started_engine.stop_autopilot()

    @pytest.mark.anyio
    async def test_start_autopilot_invalid_speed(
        self, started_engine: GameEngine
    ) -> None:
        """start_autopilot rejects invalid speed values."""
        with pytest.raises(ValueError, match="Invalid speed"):
            await started_engine.start_autopilot(speed="ludicrous")

    @pytest.mark.anyio
    async def test_start_autopilot_no_state_raises(self, engine: GameEngine) -> None:
        """start_autopilot raises RuntimeError if no state."""
        with pytest.raises(RuntimeError, match="No game state loaded"):
            await engine.start_autopilot()

    @pytest.mark.anyio
    async def test_start_autopilot_already_running_raises(
        self, started_engine: GameEngine
    ) -> None:
        """start_autopilot raises if already running."""
        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.start_autopilot()
            with pytest.raises(RuntimeError, match="already running"):
                await started_engine.start_autopilot()
            await started_engine.stop_autopilot()

    @pytest.mark.anyio
    async def test_stop_autopilot_cancels_task(
        self, started_engine: GameEngine
    ) -> None:
        """stop_autopilot cancels the background task."""
        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.start_autopilot()
            await started_engine.stop_autopilot()

        assert started_engine.is_running is False

    @pytest.mark.anyio
    async def test_stop_autopilot_clears_pause(
        self, started_engine: GameEngine
    ) -> None:
        """stop_autopilot clears the pause flag."""
        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.start_autopilot()
            started_engine.pause()
            assert started_engine.is_paused
            await started_engine.stop_autopilot()

        assert started_engine.is_paused is False

    @pytest.mark.anyio
    async def test_stop_autopilot_noop_when_not_running(
        self, started_engine: GameEngine
    ) -> None:
        """stop_autopilot is a no-op when not running."""
        await started_engine.stop_autopilot()  # Should not raise

    @pytest.mark.anyio
    async def test_autopilot_broadcasts_started(
        self,
        engine_with_broadcast: GameEngine,
        broadcast_events: list[dict[str, Any]],
    ) -> None:
        """start_autopilot broadcasts autopilot_started event."""
        mock_result = _make_result_state(engine_with_broadcast._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await engine_with_broadcast.start_autopilot()
            await engine_with_broadcast.stop_autopilot()

        started = [e for e in broadcast_events if e["type"] == "autopilot_started"]
        assert len(started) == 1

    @pytest.mark.anyio
    async def test_autopilot_broadcasts_stopped(
        self,
        engine_with_broadcast: GameEngine,
        broadcast_events: list[dict[str, Any]],
    ) -> None:
        """stop_autopilot broadcasts autopilot_stopped event."""
        mock_result = _make_result_state(engine_with_broadcast._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await engine_with_broadcast.start_autopilot()
            await engine_with_broadcast.stop_autopilot()

        stopped = [e for e in broadcast_events if e["type"] == "autopilot_stopped"]
        assert len(stopped) == 1
        assert stopped[0]["reason"] == "user_request"

    @pytest.mark.anyio
    async def test_autopilot_executes_turns(self, started_engine: GameEngine) -> None:
        """Autopilot executes multiple turns before being stopped."""
        call_count = 0

        def counting_round(state: Any) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return _make_result_state(state)

        with patch("graph.run_single_round", side_effect=counting_round):
            await started_engine.start_autopilot(speed="fast")
            # Let it run a few turns
            await asyncio.sleep(0.5)
            await started_engine.stop_autopilot()

        assert call_count >= 1

    @pytest.mark.anyio
    async def test_autopilot_stops_on_error(self, started_engine: GameEngine) -> None:
        """Autopilot stops after MAX_RETRY_ATTEMPTS consecutive errors."""
        # Reduce retry delay for test speed by patching sleep
        mock_result = _make_error_result(started_engine._state)  # type: ignore[arg-type]
        original_sleep = asyncio.sleep

        async def fast_sleep(delay: float) -> None:
            # Collapse backoff delays to near-zero for testing
            await original_sleep(min(delay, 0.01))

        with (
            patch("graph.run_single_round", return_value=mock_result),
            patch("asyncio.sleep", side_effect=fast_sleep),
        ):
            await started_engine.start_autopilot(speed="fast")
            # Wait for autopilot to exhaust retries and stop
            await original_sleep(0.5)

        assert started_engine.is_running is False

    @pytest.mark.anyio
    async def test_autopilot_respects_turn_limit(
        self, started_engine: GameEngine
    ) -> None:
        """Autopilot stops after reaching max turns."""
        started_engine._max_turns = 2

        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.start_autopilot(speed="fast")
            await asyncio.sleep(0.5)

        assert started_engine.is_running is False
        assert started_engine.turn_count >= 2

    def test_pause(self, started_engine: GameEngine) -> None:
        """pause() sets is_paused to True."""
        started_engine.pause()
        assert started_engine.is_paused is True

    def test_resume(self, started_engine: GameEngine) -> None:
        """resume() sets is_paused to False."""
        started_engine.pause()
        started_engine.resume()
        assert started_engine.is_paused is False

    @pytest.mark.anyio
    async def test_pause_prevents_turn_execution(
        self, started_engine: GameEngine
    ) -> None:
        """Paused autopilot does not execute turns."""
        call_count = 0

        def counting_round(state: Any) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return _make_result_state(state)

        with patch("graph.run_single_round", side_effect=counting_round):
            await started_engine.start_autopilot(speed="fast")
            started_engine.pause()
            before = call_count
            await asyncio.sleep(0.3)
            after = call_count
            await started_engine.stop_autopilot()

        # While paused, no new turns should execute
        assert after == before

    def test_set_speed_valid(self, started_engine: GameEngine) -> None:
        """set_speed changes the speed setting."""
        started_engine.set_speed("fast")
        assert started_engine.speed == "fast"

    def test_set_speed_invalid(self, started_engine: GameEngine) -> None:
        """set_speed raises ValueError for invalid speed."""
        with pytest.raises(ValueError, match="Invalid speed"):
            started_engine.set_speed("warp")

    @pytest.mark.anyio
    async def test_set_speed_during_autopilot(self, started_engine: GameEngine) -> None:
        """Changing speed during autopilot does not interrupt it."""
        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.start_autopilot(speed="normal")
            started_engine.set_speed("fast")
            assert started_engine.speed == "fast"
            assert started_engine.is_running
            await started_engine.stop_autopilot()


# =============================================================================
# Test Human Intervention (AC7, AC8, AC9)
# =============================================================================


class TestHumanIntervention:
    """Test drop-in, release, submit_human_action, submit_nudge."""

    @pytest.mark.anyio
    async def test_drop_in_sets_human_state(self, started_engine: GameEngine) -> None:
        """drop_in sets human_active and controlled_character."""
        await started_engine.drop_in("rogue")

        assert started_engine.human_active is True
        assert started_engine.controlled_character == "rogue"

    @pytest.mark.anyio
    async def test_drop_in_updates_game_state(self, started_engine: GameEngine) -> None:
        """drop_in updates GameState fields."""
        await started_engine.drop_in("rogue")

        assert started_engine.state["human_active"] is True  # type: ignore[index]
        assert started_engine.state["controlled_character"] == "rogue"  # type: ignore[index]

    @pytest.mark.anyio
    async def test_drop_in_stops_autopilot(self, started_engine: GameEngine) -> None:
        """drop_in stops autopilot if running."""
        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.start_autopilot()
            assert started_engine.is_running

            await started_engine.drop_in("rogue")

        assert started_engine.is_running is False
        assert started_engine.human_active is True

    @pytest.mark.anyio
    async def test_drop_in_broadcasts_events(
        self,
        engine_with_broadcast: GameEngine,
        broadcast_events: list[dict[str, Any]],
    ) -> None:
        """drop_in broadcasts drop_in event."""
        await engine_with_broadcast.drop_in("rogue")

        drop_events = [e for e in broadcast_events if e["type"] == "drop_in"]
        assert len(drop_events) == 1
        assert drop_events[0]["character"] == "rogue"

    @pytest.mark.anyio
    async def test_release_control_clears_state(
        self, started_engine: GameEngine
    ) -> None:
        """release_control clears human state."""
        await started_engine.drop_in("rogue")
        await started_engine.release_control()

        assert started_engine.human_active is False
        assert started_engine.controlled_character is None

    @pytest.mark.anyio
    async def test_release_control_clears_game_state(
        self, started_engine: GameEngine
    ) -> None:
        """release_control clears GameState fields."""
        await started_engine.drop_in("rogue")
        await started_engine.release_control()

        assert started_engine.state["human_active"] is False  # type: ignore[index]
        assert started_engine.state["controlled_character"] is None  # type: ignore[index]

    @pytest.mark.anyio
    async def test_release_control_broadcasts(
        self,
        engine_with_broadcast: GameEngine,
        broadcast_events: list[dict[str, Any]],
    ) -> None:
        """release_control broadcasts release_control event."""
        await engine_with_broadcast.drop_in("rogue")
        await engine_with_broadcast.release_control()

        release_events = [e for e in broadcast_events if e["type"] == "release_control"]
        assert len(release_events) == 1

    @pytest.mark.anyio
    async def test_submit_human_action_success(
        self, started_engine: GameEngine
    ) -> None:
        """submit_human_action feeds action into turn execution."""
        await started_engine.drop_in("rogue")

        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            result = await started_engine.submit_human_action("I check for traps")

        assert result["type"] == "turn_update"

    @pytest.mark.anyio
    async def test_submit_human_action_stores_in_state(
        self, started_engine: GameEngine
    ) -> None:
        """submit_human_action stores the action in GameState."""
        await started_engine.drop_in("rogue")

        stored_action: str | None = None

        def capture_action(state: Any) -> dict[str, Any]:
            nonlocal stored_action
            stored_action = state.get("human_pending_action")
            return _make_result_state(state)

        with patch("graph.run_single_round", side_effect=capture_action):
            await started_engine.submit_human_action("I open the door")

        assert stored_action == "I open the door"

    @pytest.mark.anyio
    async def test_submit_human_action_sanitizes(
        self, started_engine: GameEngine
    ) -> None:
        """submit_human_action strips whitespace and enforces length limit."""
        await started_engine.drop_in("rogue")

        stored_action: str | None = None

        def capture_action(state: Any) -> dict[str, Any]:
            nonlocal stored_action
            stored_action = state.get("human_pending_action")
            return _make_result_state(state)

        with patch("graph.run_single_round", side_effect=capture_action):
            await started_engine.submit_human_action("  trimmed  ")

        assert stored_action == "trimmed"

    @pytest.mark.anyio
    async def test_submit_human_action_no_state_raises(
        self, engine: GameEngine
    ) -> None:
        """submit_human_action raises if no state loaded."""
        with pytest.raises(RuntimeError, match="No game state loaded"):
            await engine.submit_human_action("hello")

    @pytest.mark.anyio
    async def test_submit_human_action_not_active_raises(
        self, started_engine: GameEngine
    ) -> None:
        """submit_human_action raises if human not controlling a character."""
        with pytest.raises(RuntimeError, match="Human control is not active"):
            await started_engine.submit_human_action("hello")

    @pytest.mark.anyio
    async def test_submit_human_action_empty_raises(
        self, started_engine: GameEngine
    ) -> None:
        """submit_human_action raises on empty text."""
        await started_engine.drop_in("rogue")
        with pytest.raises(ValueError, match="empty"):
            await started_engine.submit_human_action("   ")

    def test_submit_nudge_stores(self, started_engine: GameEngine) -> None:
        """submit_nudge stores the nudge text."""
        started_engine.submit_nudge("Try the tavern")
        assert started_engine.pending_nudge == "Try the tavern"

    def test_submit_nudge_stores_in_state(self, started_engine: GameEngine) -> None:
        """submit_nudge also sets the nudge in GameState."""
        started_engine.submit_nudge("Talk to the innkeeper")
        assert started_engine.state.get("pending_nudge") == "Talk to the innkeeper"  # type: ignore[union-attr]

    def test_submit_nudge_sanitizes(self, started_engine: GameEngine) -> None:
        """submit_nudge strips whitespace."""
        started_engine.submit_nudge("  cleaned  ")
        assert started_engine.pending_nudge == "cleaned"

    def test_submit_nudge_empty_raises(self, started_engine: GameEngine) -> None:
        """submit_nudge raises ValueError on empty text."""
        with pytest.raises(ValueError, match="empty"):
            started_engine.submit_nudge("   ")

    def test_submit_nudge_enforces_length(self, started_engine: GameEngine) -> None:
        """submit_nudge truncates to MAX_NUDGE_LENGTH."""
        long_nudge = "x" * (GameEngine.MAX_NUDGE_LENGTH + 100)
        started_engine.submit_nudge(long_nudge)
        assert len(started_engine.pending_nudge) == GameEngine.MAX_NUDGE_LENGTH  # type: ignore[arg-type]


# =============================================================================
# Test Broadcast Callback (AC11)
# =============================================================================


class TestBroadcastCallback:
    """Test broadcast callback mechanism."""

    @pytest.mark.anyio
    async def test_set_broadcast_callback(self, started_engine: GameEngine) -> None:
        """set_broadcast_callback registers the callback."""
        events: list[dict[str, Any]] = []

        async def collector(event: dict[str, Any]) -> None:
            events.append(event)

        started_engine.set_broadcast_callback(collector)

        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.run_turn()

        assert len(events) > 0

    @pytest.mark.anyio
    async def test_unregister_callback(self, started_engine: GameEngine) -> None:
        """Setting callback to None unregisters it."""
        events: list[dict[str, Any]] = []

        async def collector(event: dict[str, Any]) -> None:
            events.append(event)

        started_engine.set_broadcast_callback(collector)
        started_engine.set_broadcast_callback(None)

        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await started_engine.run_turn()

        assert len(events) == 0

    @pytest.mark.anyio
    async def test_callback_error_does_not_crash_engine(
        self, started_engine: GameEngine
    ) -> None:
        """Broadcast callback errors are caught and logged."""

        async def bad_callback(event: dict[str, Any]) -> None:
            raise RuntimeError("Callback exploded")

        started_engine.set_broadcast_callback(bad_callback)

        mock_result = _make_result_state(started_engine._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            # Should not raise despite callback error
            result = await started_engine.run_turn()

        assert result["type"] == "turn_update"

    @pytest.mark.anyio
    async def test_broadcast_without_callback(self, started_engine: GameEngine) -> None:
        """_broadcast is a no-op when no callback registered."""
        # Should not raise
        await started_engine._broadcast({"type": "test"})

    @pytest.mark.anyio
    async def test_turn_update_event_shape(
        self,
        engine_with_broadcast: GameEngine,
        broadcast_events: list[dict[str, Any]],
    ) -> None:
        """turn_update events have the expected fields."""
        mock_result = _make_result_state(engine_with_broadcast._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await engine_with_broadcast.run_turn()

        turn_events = [e for e in broadcast_events if e["type"] == "turn_update"]
        assert len(turn_events) == 1
        event = turn_events[0]
        assert "turn" in event
        assert "agent" in event
        assert "content" in event
        assert "new_entries" in event
        assert isinstance(event["new_entries"], list)
        assert "state" in event

    @pytest.mark.anyio
    async def test_error_event_shape(
        self,
        engine_with_broadcast: GameEngine,
        broadcast_events: list[dict[str, Any]],
    ) -> None:
        """error events have message and recoverable fields."""
        mock_result = _make_error_result(engine_with_broadcast._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await engine_with_broadcast.run_turn()

        error_events = [e for e in broadcast_events if e["type"] == "error"]
        assert len(error_events) == 1
        event = error_events[0]
        assert "message" in event
        assert "recoverable" in event


# =============================================================================
# Test Zero Streamlit Dependency (AC12)
# =============================================================================


class TestNoStreamlitDependency:
    """Verify api/engine.py has no Streamlit imports."""

    def test_no_streamlit_import_in_source(self) -> None:
        """engine.py source contains no 'import streamlit' references."""
        import api.engine as engine_mod

        source = inspect.getsource(engine_mod)
        assert "import streamlit" not in source
        assert "st.session_state" not in source

    def test_module_can_import_without_streamlit(self) -> None:
        """engine module imports without Streamlit being available."""
        # This test inherently passes if we reach here, since conftest
        # does not mock streamlit
        from api.engine import GameEngine as GE

        assert GE is not None


# =============================================================================
# Test Constants
# =============================================================================


class TestConstants:
    """Test class constants match expected values."""

    def test_speed_delays(self) -> None:
        """SPEED_DELAYS has correct mapping."""
        assert GameEngine.SPEED_DELAYS == {"slow": 3.0, "normal": 1.0, "fast": 0.2}

    def test_max_retry_attempts(self) -> None:
        """MAX_RETRY_ATTEMPTS is 3."""
        assert GameEngine.MAX_RETRY_ATTEMPTS == 3

    def test_default_max_turns(self) -> None:
        """DEFAULT_MAX_TURNS is 100."""
        assert GameEngine.DEFAULT_MAX_TURNS == 100

    def test_max_action_length(self) -> None:
        """MAX_ACTION_LENGTH is 2000."""
        assert GameEngine.MAX_ACTION_LENGTH == 2000

    def test_max_nudge_length(self) -> None:
        """MAX_NUDGE_LENGTH is 1000."""
        assert GameEngine.MAX_NUDGE_LENGTH == 1000

    def test_valid_speeds(self) -> None:
        """VALID_SPEEDS contains expected values."""
        assert GameEngine.VALID_SPEEDS == frozenset({"slow", "normal", "fast"})


# =============================================================================
# Test State Snapshot Helper
# =============================================================================


class TestStateSnapshot:
    """Test _get_state_snapshot helper."""

    def test_snapshot_with_state(self, started_engine: GameEngine) -> None:
        """_get_state_snapshot returns expected fields."""
        snapshot = started_engine._get_state_snapshot()
        assert snapshot["session_id"] == "test-001"
        assert "turn_number" in snapshot
        assert "current_turn" in snapshot
        assert "human_active" in snapshot
        assert "message_count" in snapshot

    def test_snapshot_without_state(self, engine: GameEngine) -> None:
        """_get_state_snapshot returns empty dict when no state."""
        snapshot = engine._get_state_snapshot()
        assert snapshot == {}


# =============================================================================
# Test Dependencies Integration
# =============================================================================


class TestDependencies:
    """Test api/dependencies.py integration."""

    def test_get_or_create_engine_creates(self) -> None:
        """get_or_create_engine creates engine for unknown session."""
        from api.dependencies import get_or_create_engine

        mock_request = MagicMock()
        mock_request.app.state.engines = {}

        engine = get_or_create_engine(mock_request, "new-session")
        assert engine.session_id == "new-session"
        assert "new-session" in mock_request.app.state.engines

    def test_get_or_create_engine_returns_existing(self) -> None:
        """get_or_create_engine returns existing engine for known session."""
        from api.dependencies import get_or_create_engine

        existing = GameEngine("existing")
        mock_request = MagicMock()
        mock_request.app.state.engines = {"existing": existing}

        result = get_or_create_engine(mock_request, "existing")
        assert result is existing

    def test_get_engine_registry_type(self) -> None:
        """get_engine_registry returns dict[str, GameEngine]."""
        from api.dependencies import get_engine_registry

        mock_request = MagicMock()
        mock_request.app.state.engines = {"001": GameEngine("001")}

        registry = get_engine_registry(mock_request)
        assert isinstance(registry["001"], GameEngine)


# =============================================================================
# Test GameState New Fields
# =============================================================================


class TestGameStateNewFields:
    """Test that new GameState fields are correctly initialized."""

    def test_initial_state_has_new_fields(self) -> None:
        """create_initial_game_state includes new fields."""
        state = create_initial_game_state()
        assert state.get("human_pending_action") is None
        assert state.get("pending_nudge") is None
        assert state.get("pending_human_whisper") is None

    def test_populate_game_state_has_new_fields(self) -> None:
        """populate_game_state includes new fields."""
        with (
            patch("config.load_character_configs", return_value={}),
            patch("config.load_dm_config"),
        ):
            from models import populate_game_state

            state = populate_game_state(include_sample_messages=False)
            assert state.get("human_pending_action") is None
            assert state.get("pending_nudge") is None
            assert state.get("pending_human_whisper") is None


# =============================================================================
# Test Session ID Validation (security)
# =============================================================================


class TestSessionIdValidation:
    """Test that GameEngine validates session_id to prevent path traversal."""

    def test_rejects_empty_session_id(self) -> None:
        """Empty session_id is rejected."""
        with pytest.raises(ValueError, match="Invalid session_id"):
            GameEngine("")

    def test_rejects_path_traversal(self) -> None:
        """Path traversal characters are rejected."""
        with pytest.raises(ValueError, match="Invalid session_id"):
            GameEngine("../../etc")

    def test_rejects_slash(self) -> None:
        """Slashes are rejected."""
        with pytest.raises(ValueError, match="Invalid session_id"):
            GameEngine("foo/bar")

    def test_accepts_alphanumeric(self) -> None:
        """Normal alphanumeric session IDs are accepted."""
        engine = GameEngine("001")
        assert engine.session_id == "001"

    def test_accepts_hyphens(self) -> None:
        """Hyphens are accepted in session IDs."""
        engine = GameEngine("test-001")
        assert engine.session_id == "test-001"

    def test_accepts_underscores(self) -> None:
        """Underscores are accepted in session IDs."""
        engine = GameEngine("test_001")
        assert engine.session_id == "test_001"


# =============================================================================
# Test Character Validation in drop_in
# =============================================================================


class TestDropInValidation:
    """Test drop_in validates the character name."""

    @pytest.mark.anyio
    async def test_drop_in_rejects_nonexistent_character(
        self, started_engine: GameEngine
    ) -> None:
        """drop_in rejects a character not in turn_queue."""
        with pytest.raises(ValueError, match="Cannot drop in"):
            await started_engine.drop_in("wizard")

    @pytest.mark.anyio
    async def test_drop_in_rejects_dm(self, started_engine: GameEngine) -> None:
        """drop_in rejects 'dm' as a character to control."""
        with pytest.raises(ValueError, match="Cannot drop in"):
            await started_engine.drop_in("dm")

    @pytest.mark.anyio
    async def test_drop_in_single_autopilot_stopped_event(
        self,
        engine_with_broadcast: GameEngine,
        broadcast_events: list[dict[str, Any]],
    ) -> None:
        """drop_in sends exactly one autopilot_stopped with reason=human_drop_in."""
        mock_result = _make_result_state(engine_with_broadcast._state)  # type: ignore[arg-type]
        with patch("graph.run_single_round", return_value=mock_result):
            await engine_with_broadcast.start_autopilot()
            await engine_with_broadcast.drop_in("rogue")

        stopped = [e for e in broadcast_events if e["type"] == "autopilot_stopped"]
        # Must be exactly ONE autopilot_stopped event (not two)
        assert len(stopped) == 1
        assert stopped[0]["reason"] == "human_drop_in"
