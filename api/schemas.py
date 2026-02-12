"""API request/response schemas for the autodungeon REST + WebSocket API.

These Pydantic v2 models define the HTTP API contract (request/response shapes)
and the WebSocket message protocol. They are separate from the game engine
models in models.py.
"""

from __future__ import annotations

from typing import Any, Literal

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


# =============================================================================
# WebSocket Server-to-Client Messages
# =============================================================================


class WsSessionState(BaseModel):
    """Full game state snapshot sent on connection and state changes."""

    type: Literal["session_state"] = "session_state"
    state: dict[str, Any] = Field(..., description="Full state snapshot")


class WsTurnUpdate(BaseModel):
    """Turn completion event with updated state."""

    type: Literal["turn_update"] = "turn_update"
    turn: int = Field(..., description="Turn number")
    agent: str = Field(..., description="Agent that acted")
    content: str = Field(..., description="Turn content text")
    state: dict[str, Any] = Field(..., description="Updated state snapshot")


class WsAutopilotStarted(BaseModel):
    """Autopilot has started running."""

    type: Literal["autopilot_started"] = "autopilot_started"


class WsAutopilotStopped(BaseModel):
    """Autopilot has stopped."""

    type: Literal["autopilot_stopped"] = "autopilot_stopped"
    reason: str = Field(..., description="Why autopilot stopped")


class WsError(BaseModel):
    """Error event from the engine or WebSocket handler."""

    type: Literal["error"] = "error"
    message: str = Field(..., description="Error description")
    recoverable: bool = Field(True, description="Whether the error is recoverable")


class WsDropIn(BaseModel):
    """Human has taken control of a character."""

    type: Literal["drop_in"] = "drop_in"
    character: str = Field(..., description="Character name")


class WsReleaseControl(BaseModel):
    """Human has released character control."""

    type: Literal["release_control"] = "release_control"


class WsAwaitingInput(BaseModel):
    """Engine is waiting for human player input."""

    type: Literal["awaiting_input"] = "awaiting_input"
    character: str = Field(..., description="Character awaiting input")


class WsNudgeReceived(BaseModel):
    """Nudge suggestion was received by the engine."""

    type: Literal["nudge_received"] = "nudge_received"


class WsSpeedChanged(BaseModel):
    """Autopilot speed has been changed."""

    type: Literal["speed_changed"] = "speed_changed"
    speed: str = Field(..., description="New speed setting")


class WsPaused(BaseModel):
    """Autopilot has been paused."""

    type: Literal["paused"] = "paused"


class WsResumed(BaseModel):
    """Autopilot has been resumed."""

    type: Literal["resumed"] = "resumed"


class WsPong(BaseModel):
    """Pong response to client ping."""

    type: Literal["pong"] = "pong"


class WsCommandAck(BaseModel):
    """Acknowledgment that a command was received and processed."""

    type: Literal["command_ack"] = "command_ack"
    command: str = Field(..., description="The command type that was acknowledged")
