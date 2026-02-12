"""API request/response schemas for the autodungeon REST API.

These Pydantic v2 models define the HTTP API contract (request/response shapes).
They are separate from the game engine models in models.py.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response for the health check endpoint."""

    status: str = Field(..., description="Server status")
    version: str = Field(..., description="API version")


class SessionResponse(BaseModel):
    """Response for session list and detail endpoints."""

    session_id: str = Field(..., description="Session ID string (e.g., '001')")
    session_number: int = Field(..., ge=1, description="Numeric session number")
    name: str = Field(default="", description="User-friendly session name")
    created_at: str = Field(..., description="ISO timestamp when session was created")
    updated_at: str = Field(..., description="ISO timestamp of last checkpoint")
    character_names: list[str] = Field(
        default_factory=list, description="List of PC character names"
    )
    turn_count: int = Field(default=0, ge=0, description="Number of turns in session")


class SessionCreateRequest(BaseModel):
    """Request body for creating a new session."""

    name: str = Field(default="", description="Optional session name")


class SessionCreateResponse(BaseModel):
    """Response for session creation."""

    session_id: str = Field(..., description="New session ID")
    session_number: int = Field(..., ge=1, description="Session number")
    name: str = Field(default="", description="Session name")


class GameConfigResponse(BaseModel):
    """Response for session config endpoint."""

    combat_mode: Literal["Narrative", "Tactical"] = Field(
        default="Narrative", description="Combat handling mode"
    )
    max_combat_rounds: int = Field(
        default=50,
        ge=0,
        description="Maximum combat rounds before auto-termination",
    )
    summarizer_provider: str = Field(
        default="gemini", description="Provider for memory compression"
    )
    summarizer_model: str = Field(
        default="gemini-1.5-flash", description="Model for memory compression"
    )
    extractor_provider: str = Field(
        default="gemini", description="Provider for narrative extraction"
    )
    extractor_model: str = Field(
        default="gemini-3-flash-preview", description="Model for narrative extraction"
    )
    party_size: int = Field(
        default=4, ge=1, le=8, description="Number of player characters"
    )
    narrative_display_limit: int = Field(
        default=50,
        ge=10,
        le=1000,
        description="Max messages to render in narrative area",
    )


class GameConfigUpdateRequest(BaseModel):
    """Request body for updating session config. All fields optional for partial update."""

    combat_mode: Literal["Narrative", "Tactical"] | None = Field(
        default=None, description="Combat handling mode"
    )
    max_combat_rounds: int | None = Field(
        default=None,
        ge=0,
        description="Maximum combat rounds before auto-termination",
    )
    summarizer_provider: str | None = Field(
        default=None, description="Provider for memory compression"
    )
    summarizer_model: str | None = Field(
        default=None, description="Model for memory compression"
    )
    extractor_provider: str | None = Field(
        default=None, description="Provider for narrative extraction"
    )
    extractor_model: str | None = Field(
        default=None, description="Model for narrative extraction"
    )
    party_size: int | None = Field(
        default=None, ge=1, le=8, description="Number of player characters"
    )
    narrative_display_limit: int | None = Field(
        default=None,
        ge=10,
        le=1000,
        description="Max messages to render in narrative area",
    )


class CharacterResponse(BaseModel):
    """Response for character list endpoint."""

    name: str = Field(..., description="Character name")
    character_class: str = Field(..., description="D&D class")
    personality: str = Field(..., description="Personality traits")
    color: str = Field(..., description="Hex color for UI")
    provider: str = Field(..., description="LLM provider")
    model: str = Field(..., description="Model name")
    source: Literal["preset", "library"] = Field(
        ..., description="Whether from preset or library"
    )


class CharacterDetailResponse(CharacterResponse):
    """Response for character detail endpoint, extends CharacterResponse."""

    token_limit: int = Field(..., ge=1, description="Context limit for character")


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Error description")
