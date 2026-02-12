"""Shared FastAPI dependency functions for the autodungeon API."""

from __future__ import annotations

from fastapi import Request

from api.engine import GameEngine
from config import AppConfig


def get_config(request: Request) -> AppConfig:
    """Get the loaded AppConfig from app state.

    Args:
        request: FastAPI request object.

    Returns:
        The application configuration.
    """
    config: AppConfig = request.app.state.config
    return config


def get_engine_registry(request: Request) -> dict[str, GameEngine]:
    """Get the engine registry dict from app state.

    Args:
        request: FastAPI request object.

    Returns:
        Dict mapping session_id -> GameEngine instances.
    """
    engines: dict[str, GameEngine] = request.app.state.engines
    return engines


def get_or_create_engine(request: Request, session_id: str) -> GameEngine:
    """Get an existing engine or create a new one for the session.

    If an engine already exists for the given session_id, returns it.
    Otherwise creates a new GameEngine, registers it, and returns it.

    Args:
        request: FastAPI request object.
        session_id: Session ID to get or create engine for.

    Returns:
        The GameEngine for the session.

    Raises:
        ValueError: If session_id contains invalid characters (propagated
            from GameEngine constructor validation).
    """
    engines = get_engine_registry(request)
    if session_id not in engines:
        # GameEngine constructor validates session_id format
        engines[session_id] = GameEngine(session_id)
    return engines[session_id]
