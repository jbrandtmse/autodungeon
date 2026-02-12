"""WebSocket stub for the autodungeon API.

Full implementation is Story 16-3. This stub provides a placeholder
endpoint that accepts connections and immediately closes them.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/ws/game/{session_id}")
async def game_websocket(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for real-time game streaming.

    Stub implementation - accepts the connection and immediately closes
    with a message indicating the feature is not yet implemented.

    Args:
        websocket: The WebSocket connection.
        session_id: The session to stream.
    """
    await websocket.accept()
    await websocket.close(code=1000, reason="Not yet implemented")
