"""GameEngine stub for the autodungeon API.

Full implementation is Story 16-2. This stub provides the class interface
so other modules can reference it during development.
"""

from __future__ import annotations

from typing import Any


class GameEngine:
    """Stub game engine that wraps a session's game loop.

    Full implementation in Story 16-2 will integrate with LangGraph
    to drive the game forward.
    """

    def __init__(self, session_id: str) -> None:
        """Initialize the engine for a session.

        Args:
            session_id: The session ID this engine manages.
        """
        self._session_id = session_id

    @property
    def session_id(self) -> str:
        """Get the session ID this engine manages."""
        return self._session_id

    async def start(self) -> None:
        """Start the game engine. Stub - not yet implemented."""

    async def stop(self) -> None:
        """Stop the game engine. Stub - not yet implemented."""

    def get_state(self) -> dict[str, Any] | None:
        """Get the current game state. Stub - returns None.

        Returns:
            GameState dict or None if no state loaded.
        """
        return None
