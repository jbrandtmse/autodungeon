"""GameEngine service class for the autodungeon API.

Provides a standalone game orchestration layer that wraps graph.py execution,
manages session lifecycle, autopilot as asyncio background tasks, and human
intervention -- all without any Streamlit dependency.

Story 16-2: Game Engine Extraction.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from models import GameState, UserError, create_user_error

logger = logging.getLogger("autodungeon.engine")


class GameEngine:
    """Standalone game engine that drives the LangGraph game loop.

    Wraps synchronous graph.run_single_round() calls in asyncio.to_thread()
    for non-blocking async execution. Manages autopilot as an asyncio.Task,
    human drop-in/release, nudge injection, error handling with retry,
    and a broadcast callback mechanism for downstream consumers (WebSocket).

    This class has ZERO Streamlit dependencies. It is the bridge between
    the pure game engine layer (graph.py, agents.py, memory.py, persistence.py)
    and the API layer (routes.py, websocket.py).
    """

    SPEED_DELAYS: dict[str, float] = {
        "slow": 3.0,
        "normal": 1.0,
        "fast": 0.2,
    }
    MAX_RETRY_ATTEMPTS: int = 3
    DEFAULT_MAX_TURNS: int = 100
    MAX_ACTION_LENGTH: int = 2000
    MAX_NUDGE_LENGTH: int = 1000
    VALID_SPEEDS: frozenset[str] = frozenset({"slow", "normal", "fast"})

    def __init__(self, session_id: str) -> None:
        """Initialize the engine for a session.

        Args:
            session_id: The session ID this engine manages. Must be
                alphanumeric (underscores allowed) to prevent path
                traversal in persistence operations.

        Raises:
            ValueError: If session_id is empty or contains invalid characters.
        """
        if not session_id or not session_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                f"Invalid session_id: {session_id!r}. "
                "Must be alphanumeric (hyphens and underscores allowed)."
            )
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
        self._broadcast_callback: Callable[[dict[str, Any]], Awaitable[None]] | None = (
            None
        )
        self._lock = asyncio.Lock()

    # -------------------------------------------------------------------------
    # Properties
    # -------------------------------------------------------------------------

    @property
    def session_id(self) -> str:
        """Get the session ID this engine manages."""
        return self._session_id

    @property
    def state(self) -> GameState | None:
        """Get the current game state, or None if not loaded."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Whether autopilot is currently running."""
        return self._task is not None and not self._task.done()

    @property
    def is_paused(self) -> bool:
        """Whether autopilot is paused."""
        return self._is_paused

    @property
    def speed(self) -> str:
        """Current autopilot speed setting."""
        return self._speed

    @property
    def human_active(self) -> bool:
        """Whether a human has taken control of a character."""
        return self._human_active

    @property
    def controlled_character(self) -> str | None:
        """Name of the character the human controls, or None."""
        return self._controlled_character

    @property
    def pending_nudge(self) -> str | None:
        """The pending nudge text for the DM, or None."""
        return self._pending_nudge

    @property
    def last_error(self) -> UserError | None:
        """The last error that occurred, or None."""
        return self._last_error

    @property
    def turn_count(self) -> int:
        """Number of turns executed in this autopilot session."""
        return self._turn_count

    @property
    def is_generating(self) -> bool:
        """Whether a turn is currently being generated."""
        return self._is_generating

    # -------------------------------------------------------------------------
    # Session Lifecycle
    # -------------------------------------------------------------------------

    async def start_session(
        self,
        characters_override: dict[str, Any] | None = None,
        selected_module: Any | None = None,
        library_data: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        """Start the game session by loading or creating state.

        Attempts to load the latest checkpoint for this session. If none
        exists, creates fresh state via populate_game_state().

        Args:
            characters_override: Optional character configs to use instead
                of loading from YAML files.
            selected_module: Optional module for DM context injection.
            library_data: Optional library data for character sheet generation.
        """
        from persistence import get_latest_checkpoint, load_checkpoint

        # Try to load existing checkpoint
        latest_turn = get_latest_checkpoint(self._session_id)
        if latest_turn is not None:
            loaded = load_checkpoint(self._session_id, latest_turn)
            if loaded is not None:
                self._state = loaded
                # Sync human state from loaded state
                self._human_active = bool(loaded.get("human_active", False))
                self._controlled_character = loaded.get("controlled_character")
                await self._broadcast(
                    {"type": "session_state", "state": self._get_state_snapshot()}
                )
                return

        # No checkpoint -- create fresh state
        from models import populate_game_state

        self._state = populate_game_state(
            include_sample_messages=False,
            selected_module=selected_module,
            characters_override=characters_override,
            library_data=library_data,
        )
        # Update session_id in the state
        self._state["session_id"] = self._session_id

        await self._broadcast(
            {"type": "session_state", "state": self._get_state_snapshot()}
        )

    async def stop_session(self) -> None:
        """Stop the game session.

        Stops autopilot if running, saves a checkpoint, and clears state.
        """
        if self.is_running:
            await self.stop_autopilot()

        if self._state is not None:
            from persistence import save_checkpoint

            turn_number = len(self._state.get("ground_truth_log", []))
            try:
                save_checkpoint(self._state, self._session_id, turn_number)
            except OSError:
                logger.exception("Failed to save checkpoint on stop_session")

        self._state = None
        self._human_active = False
        self._controlled_character = None
        self._pending_nudge = None
        self._last_error = None
        self._retry_count = 0
        self._turn_count = 0
        self._is_generating = False

    # -------------------------------------------------------------------------
    # Turn Execution
    # -------------------------------------------------------------------------

    async def run_turn(self) -> dict[str, Any]:
        """Execute a single game turn.

        Wraps graph.run_single_round() in asyncio.to_thread() since it is
        synchronous. Updates internal state and invokes broadcast callback.

        Returns:
            Dict with turn result data including type, turn_number, agent,
            content. On error, returns error info instead.

        Raises:
            RuntimeError: If no state is loaded (session not started).
        """
        if self._state is None:
            raise RuntimeError("No game state loaded. Call start_session() first.")

        async with self._lock:
            return await self._execute_turn()

    async def _execute_turn(self) -> dict[str, Any]:
        """Internal turn execution (must be called under lock).

        Returns:
            Turn result dict.
        """
        from graph import run_single_round

        if self._state is None:
            raise RuntimeError("No game state loaded.")

        self._is_generating = True
        try:
            # Inject pending nudge into state before running turn
            if self._pending_nudge is not None:
                self._state["pending_nudge"] = self._pending_nudge  # type: ignore[literal-required]

            # Run the synchronous graph in a thread to avoid blocking
            result = await asyncio.to_thread(run_single_round, self._state)

            # Check for error in result
            error = result.get("error")
            if error is not None:
                self._last_error = error  # type: ignore[assignment]
                error_event: dict[str, Any] = {
                    "type": "error",
                    "message": str(error.message)
                    if hasattr(error, "message")
                    else str(error),
                    "recoverable": True,
                }
                await self._broadcast(error_event)
                return error_event

            # Success -- update state
            # Remove error key if present in result (it's a GameStateWithError)
            clean_result: dict[str, Any] = {
                k: v for k, v in result.items() if k != "error"
            }
            self._state = clean_result  # type: ignore[assignment]

            # Clear consumed nudge
            self._pending_nudge = None

            # Clear error on success
            self._last_error = None
            self._retry_count = 0

            # Build turn event
            log = self._state.get("ground_truth_log", [])
            turn_number = len(log)
            current_turn = self._state.get("current_turn", "dm")
            last_entry = log[-1] if log else ""

            turn_event: dict[str, Any] = {
                "type": "turn_update",
                "turn": turn_number,
                "agent": current_turn,
                "content": last_entry,
                "state": self._get_state_snapshot(),
            }
            await self._broadcast(turn_event)
            return turn_event

        except Exception as e:
            logger.exception("Turn execution failed")
            user_error = create_user_error(
                error_type="unknown",
                provider="unknown",
                agent="unknown",
                retry_count=self._retry_count,
                detail_message=str(e),
            )
            self._last_error = user_error
            error_event = {
                "type": "error",
                "message": user_error.message,
                "recoverable": True,
            }
            await self._broadcast(error_event)
            return error_event
        finally:
            self._is_generating = False

    async def retry_turn(self) -> dict[str, Any]:
        """Retry a failed turn.

        Re-executes the turn with retry tracking. Enforces MAX_RETRY_ATTEMPTS.

        Returns:
            Turn result dict.

        Raises:
            RuntimeError: If no state loaded or max retries exceeded.
        """
        if self._state is None:
            raise RuntimeError("No game state loaded. Call start_session() first.")

        if self._retry_count >= self.MAX_RETRY_ATTEMPTS:
            raise RuntimeError(
                f"Max retry attempts ({self.MAX_RETRY_ATTEMPTS}) exceeded."
            )

        self._retry_count += 1
        async with self._lock:
            result = await self._execute_turn()
            return result

    # -------------------------------------------------------------------------
    # Autopilot
    # -------------------------------------------------------------------------

    async def start_autopilot(self, speed: str = "normal") -> None:
        """Start autopilot as an asyncio background task.

        Args:
            speed: Autopilot speed ("slow", "normal", or "fast").

        Raises:
            RuntimeError: If no state loaded or autopilot already running.
            ValueError: If speed is invalid.
        """
        if self._state is None:
            raise RuntimeError("No game state loaded. Call start_session() first.")

        if self.is_running:
            raise RuntimeError("Autopilot is already running.")

        if speed not in self.VALID_SPEEDS:
            raise ValueError(
                f"Invalid speed '{speed}'. Must be one of: {', '.join(sorted(self.VALID_SPEEDS))}"
            )

        self._speed = speed
        self._is_paused = False
        self._turn_count = 0
        self._task = asyncio.create_task(self._autopilot_loop())

        await self._broadcast({"type": "autopilot_started"})

    async def stop_autopilot(self, _reason: str = "user_request") -> None:
        """Stop the autopilot background task gracefully.

        Waits for the current turn to complete before stopping.

        Args:
            _reason: Internal stop reason for broadcast event. Callers
                should not set this directly; use drop_in() for human
                takeover which passes the correct reason automatically.
        """
        if self._task is None or self._task.done():
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        self._is_paused = False

        await self._broadcast({"type": "autopilot_stopped", "reason": _reason})

    async def _autopilot_loop(self) -> None:
        """Background loop that executes turns continuously.

        Respects pause flag, speed delay, turn limit, and error conditions.
        Stops on error so the user can inspect and retry.
        """
        try:
            while True:
                # Check pause
                if self._is_paused:
                    await asyncio.sleep(0.1)
                    continue

                # Check turn limit
                if self._turn_count >= self._max_turns:
                    await self._broadcast(
                        {"type": "autopilot_stopped", "reason": "turn_limit"}
                    )
                    break

                # Execute a turn
                async with self._lock:
                    result = await self._execute_turn()

                self._turn_count += 1

                # Stop on error
                if result.get("type") == "error":
                    await self._broadcast(
                        {"type": "autopilot_stopped", "reason": "error"}
                    )
                    break

                # Wait for speed delay
                await asyncio.sleep(self._get_turn_delay())

        except asyncio.CancelledError:
            # Graceful shutdown -- the cancellation is expected
            raise
        except Exception:
            # Defense-in-depth: catch unexpected exceptions so the task
            # does not die silently without broadcasting a stop event.
            logger.exception("Unexpected error in autopilot loop")
            await self._broadcast(
                {"type": "autopilot_stopped", "reason": "error"}
            )

    def pause(self) -> None:
        """Pause autopilot execution.

        The background task stays alive but skips turn execution.
        """
        self._is_paused = True

    def resume(self) -> None:
        """Resume autopilot execution after a pause."""
        self._is_paused = False

    def set_speed(self, speed: str) -> None:
        """Change autopilot speed without interrupting execution.

        Args:
            speed: New speed setting ("slow", "normal", or "fast").

        Raises:
            ValueError: If speed is invalid.
        """
        if speed not in self.VALID_SPEEDS:
            raise ValueError(
                f"Invalid speed '{speed}'. Must be one of: {', '.join(sorted(self.VALID_SPEEDS))}"
            )
        self._speed = speed

    # -------------------------------------------------------------------------
    # Human Intervention
    # -------------------------------------------------------------------------

    async def drop_in(self, character: str) -> None:
        """Take human control of a character.

        Stops autopilot if running and sets human control state on both
        the engine and the GameState.

        Args:
            character: Name (key) of the character to control.

        Raises:
            ValueError: If character is not in the turn queue.
        """
        # Validate character exists in turn_queue
        if self._state is not None:
            turn_queue = self._state.get("turn_queue", [])
            if character not in turn_queue or character == "dm":
                raise ValueError(
                    f"Cannot drop in as '{character}'. "
                    f"Must be a PC in the turn queue."
                )

        if self.is_running:
            await self.stop_autopilot(_reason="human_drop_in")

        self._human_active = True
        self._controlled_character = character

        if self._state is not None:
            self._state["human_active"] = True
            self._state["controlled_character"] = character

        await self._broadcast({"type": "drop_in", "character": character})

    async def release_control(self) -> None:
        """Release human control of a character.

        Clears human control state on both the engine and the GameState.
        """
        self._human_active = False
        self._controlled_character = None

        if self._state is not None:
            self._state["human_active"] = False
            self._state["controlled_character"] = None

        await self._broadcast({"type": "release_control"})

    async def submit_human_action(self, action: str) -> dict[str, Any]:
        """Submit a human player's action for processing.

        Sanitizes the input, stores it in GameState, and runs a turn
        so the human_intervention_node processes it.

        Args:
            action: The human player's action text.

        Returns:
            Turn result dict.

        Raises:
            RuntimeError: If no state loaded or human not active.
        """
        if self._state is None:
            raise RuntimeError("No game state loaded.")

        if not self._human_active:
            raise RuntimeError("Human control is not active. Call drop_in() first.")

        # Sanitize
        sanitized = action.strip()[: self.MAX_ACTION_LENGTH]
        if not sanitized:
            raise ValueError("Action text cannot be empty.")

        # Store in GameState for human_intervention_node to pick up
        self._state["human_pending_action"] = sanitized  # type: ignore[literal-required]

        # Run a turn to process the action
        result = await self.run_turn()
        return result

    def submit_nudge(self, nudge: str) -> None:
        """Submit a nudge suggestion for the DM's next turn.

        Args:
            nudge: The suggestion text for the DM.

        Raises:
            ValueError: If nudge text is empty after sanitization.
        """
        sanitized = nudge.strip()[: self.MAX_NUDGE_LENGTH]
        if not sanitized:
            raise ValueError("Nudge text cannot be empty.")

        self._pending_nudge = sanitized

        if self._state is not None:
            self._state["pending_nudge"] = sanitized  # type: ignore[literal-required]

    MAX_WHISPER_LENGTH: int = 2000

    def submit_whisper(self, content: str) -> None:
        """Submit a private whisper from the human to the DM.

        Stores the whisper in the game state's ``pending_human_whisper``
        field, which the DM agent reads on the next turn (mirroring the
        Streamlit implementation in app.py).

        Args:
            content: The whisper text from the human player.

        Raises:
            ValueError: If content is empty after sanitization.
        """
        sanitized = content.strip()[: self.MAX_WHISPER_LENGTH]
        if not sanitized:
            raise ValueError("Whisper text cannot be empty.")

        if self._state is not None:
            self._state["pending_human_whisper"] = sanitized  # type: ignore[literal-required]

    # -------------------------------------------------------------------------
    # Broadcast Callback
    # -------------------------------------------------------------------------

    def set_broadcast_callback(
        self,
        callback: Callable[[dict[str, Any]], Awaitable[None]] | None,
    ) -> None:
        """Register or unregister a broadcast callback.

        The callback is invoked on state changes (turn completion, errors,
        autopilot state changes, human intervention events). Story 16-3
        will register a WebSocket broadcaster as the callback.

        Args:
            callback: Async callable that receives event dicts, or None
                to unregister.
        """
        self._broadcast_callback = callback

    async def _broadcast(self, event: dict[str, Any]) -> None:
        """Invoke the registered broadcast callback with an event.

        Catches and logs any exceptions from the callback to prevent
        callback errors from disrupting engine operation.

        Args:
            event: Event dict to broadcast.
        """
        if self._broadcast_callback is not None:
            try:
                await self._broadcast_callback(event)
            except Exception:
                logger.exception("Broadcast callback error")

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_state_snapshot(self) -> dict[str, Any]:
        """Build a lightweight state snapshot for broadcast events.

        Returns:
            Dict with key state fields for consumers.
        """
        if self._state is None:
            return {}

        log = self._state.get("ground_truth_log", [])
        return {
            "session_id": self._session_id,
            "turn_number": len(log),
            "current_turn": self._state.get("current_turn", ""),
            "human_active": self._human_active,
            "controlled_character": self._controlled_character,
            "is_paused": self._is_paused,
            "speed": self._speed,
            "message_count": len(log),
            "ground_truth_log": list(log),
            "characters": {
                k: v.model_dump() if hasattr(v, "model_dump") else v
                for k, v in self._state.get("characters", {}).items()
            },
        }

    def _get_turn_delay(self) -> float:
        """Get the delay between turns based on current speed.

        Returns:
            Delay in seconds.
        """
        return self.SPEED_DELAYS.get(self._speed, 1.0)
