"""Shared FastAPI dependency functions for the autodungeon API."""

from __future__ import annotations

from typing import Any

from fastapi import Request

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


def get_engine_registry(request: Request) -> dict[str, Any]:
    """Get the engine registry dict from app state.

    Args:
        request: FastAPI request object.

    Returns:
        Dict mapping session_id -> GameEngine instances.
    """
    engines: dict[str, Any] = request.app.state.engines
    return engines
