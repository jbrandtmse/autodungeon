"""FastAPI application for the autodungeon API.

This is the entry point for the API server. Run with:
    uvicorn api.main:app --reload

The API wraps existing backend functions (persistence, config, models)
without modifying them. Streamlit app.py continues to work independently.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from api.schemas import HealthResponse
from api.websocket import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager.

    Startup: Load config and initialize empty engine registry.
    Shutdown: Gracefully stop all active engine sessions.
    """
    from config import get_config

    app.state.config = get_config()
    app.state.engines = {}  # session_id -> GameEngine
    yield
    # Shutdown: gracefully stop each engine session
    for engine in list(app.state.engines.values()):
        try:
            await engine.stop_session()
        except Exception:
            pass  # Best-effort cleanup
    app.state.engines.clear()


app = FastAPI(
    title="autodungeon",
    version="2.0.0-alpha",
    lifespan=lifespan,
)

# CORS middleware for local dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        Status and version info.
    """
    return HealthResponse(status="ok", version="2.0.0-alpha")
