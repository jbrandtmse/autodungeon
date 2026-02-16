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
    dm_provider: str = Field(default="gemini", description="DM agent LLM provider")
    dm_model: str = Field(default="gemini-1.5-flash", description="DM agent model name")
    dm_token_limit: int = Field(
        default=8000, ge=1, description="DM agent context token limit"
    )
    # Image generation settings (Story 17-2)
    image_generation_enabled: bool = Field(
        default=False, description="Whether image generation is enabled"
    )
    image_provider: str = Field(
        default="gemini", description="Provider for image generation"
    )
    image_model: str = Field(
        default="imagen-4.0-generate-001", description="Image generation model"
    )
    image_scanner_provider: str = Field(
        default="gemini", description="LLM provider for scene scanning"
    )
    image_scanner_model: str = Field(
        default="gemini-3-flash-preview", description="LLM model for scene scanning"
    )
    image_scanner_token_limit: int = Field(
        default=4000, ge=1, description="Token limit for scene scanner"
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
    dm_provider: str | None = Field(default=None, description="DM agent LLM provider")
    dm_model: str | None = Field(default=None, description="DM agent model name")
    dm_token_limit: int | None = Field(
        default=None, ge=1, description="DM agent context token limit"
    )
    # Image generation settings (Story 17-2)
    image_generation_enabled: bool | None = Field(
        default=None, description="Whether image generation is enabled"
    )
    image_provider: str | None = Field(
        default=None, description="Provider for image generation"
    )
    image_model: str | None = Field(default=None, description="Image generation model")
    image_scanner_provider: str | None = Field(
        default=None, description="LLM provider for scene scanning"
    )
    image_scanner_model: str | None = Field(
        default=None, description="LLM model for scene scanning"
    )
    image_scanner_token_limit: int | None = Field(
        default=None, ge=1, description="Token limit for scene scanner"
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
    backstory: str = Field(default="", description="Character backstory")


class CharacterCreateRequest(BaseModel):
    """Request body for creating a new library character."""

    name: str = Field(..., min_length=1, max_length=50, description="Character name")
    character_class: str = Field(
        ..., min_length=1, max_length=50, description="D&D class (e.g., Fighter, Rogue)"
    )
    personality: str = Field(
        default="", max_length=2000, description="Personality traits"
    )
    backstory: str = Field(
        default="", max_length=5000, description="Character backstory"
    )
    color: str = Field(default="#808080", description="Hex color for UI")
    provider: str = Field(default="gemini", description="LLM provider")
    model: str = Field(default="gemini-1.5-flash", description="Model name")
    token_limit: int = Field(default=4000, ge=1, description="Context token limit")


class CharacterUpdateRequest(BaseModel):
    """Request body for updating a library character. All fields optional for partial update."""

    name: str | None = Field(
        default=None, min_length=1, max_length=50, description="Character name"
    )
    character_class: str | None = Field(
        default=None, min_length=1, max_length=50, description="D&D class"
    )
    personality: str | None = Field(
        default=None, max_length=2000, description="Personality traits"
    )
    backstory: str | None = Field(
        default=None, max_length=5000, description="Character backstory"
    )
    color: str | None = Field(default=None, description="Hex color for UI")
    provider: str | None = Field(default=None, description="LLM provider")
    model: str | None = Field(default=None, description="Model name")
    token_limit: int | None = Field(
        default=None, ge=1, description="Context token limit"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Error description")


# =============================================================================
# Fork Management Schemas (Story 16-10)
# =============================================================================


class ForkCreateRequest(BaseModel):
    """Request body for creating a new fork."""

    name: str = Field(
        ..., min_length=1, max_length=200, description="Name for the fork"
    )


class ForkRenameRequest(BaseModel):
    """Request body for renaming a fork."""

    name: str = Field(..., min_length=1, max_length=200, description="New fork name")


class ForkMetadataResponse(BaseModel):
    """Response for fork metadata, mirrors ForkMetadata model."""

    fork_id: str = Field(..., description="Fork identifier (zero-padded)")
    name: str = Field(..., description="User-provided fork name")
    parent_session_id: str = Field(..., description="Parent session ID")
    branch_turn: int = Field(..., ge=0, description="Turn number at branch point")
    created_at: str = Field(..., description="ISO timestamp when fork was created")
    updated_at: str = Field(..., description="ISO timestamp of last checkpoint")
    turn_count: int = Field(default=0, ge=0, description="Turns beyond branch point")


class ComparisonTurnResponse(BaseModel):
    """A single turn's content for comparison alignment."""

    turn_number: int = Field(..., ge=0, description="Turn number for alignment")
    entries: list[str] = Field(
        default_factory=list, description="Log entries at this turn"
    )
    is_branch_point: bool = Field(
        default=False, description="Whether this is the branch point"
    )
    is_ended: bool = Field(default=False, description="Whether timeline ended here")


class ComparisonTimelineResponse(BaseModel):
    """One side of a fork comparison (main or fork timeline)."""

    label: str = Field(..., description="Display label")
    timeline_type: Literal["main", "fork"] = Field(..., description="Timeline type")
    fork_id: str | None = Field(default=None, description="Fork ID (None for main)")
    turns: list[ComparisonTurnResponse] = Field(
        default_factory=list, description="Aligned turns"
    )
    total_turns: int = Field(default=0, ge=0, description="Total turns in timeline")


class ComparisonDataResponse(BaseModel):
    """Complete comparison data for two timelines."""

    session_id: str = Field(..., description="Session ID")
    branch_turn: int = Field(..., ge=0, description="Branch point turn number")
    left: ComparisonTimelineResponse = Field(
        ..., description="Left column (main) timeline"
    )
    right: ComparisonTimelineResponse = Field(
        ..., description="Right column (fork) timeline"
    )


# =============================================================================
# Checkpoint Schemas (Story 16-10)
# =============================================================================


class CheckpointInfoResponse(BaseModel):
    """Response for checkpoint metadata."""

    turn_number: int = Field(..., ge=0, description="Checkpoint turn number")
    timestamp: str = Field(..., description="When checkpoint was saved")
    brief_context: str = Field(default="", description="Preview of last log entry")
    message_count: int = Field(default=0, ge=0, description="Number of log messages")


class CheckpointPreviewResponse(BaseModel):
    """Response for checkpoint preview with log entries."""

    turn_number: int = Field(..., ge=0, description="Checkpoint turn number")
    entries: list[str] = Field(default_factory=list, description="Recent log entries")


# =============================================================================
# Character Sheet Schema (Story 16-10)
# =============================================================================


class WeaponResponse(BaseModel):
    """Weapon data for character sheet."""

    name: str = Field(..., description="Weapon name")
    damage_dice: str = Field(..., description="Damage dice notation")
    damage_type: str = Field(default="slashing", description="Damage type")
    properties: list[str] = Field(default_factory=list, description="Weapon properties")
    attack_bonus: int = Field(default=0, description="Magic/other attack bonus")
    is_equipped: bool = Field(default=False, description="Whether weapon is equipped")


class ArmorResponse(BaseModel):
    """Armor data for character sheet."""

    name: str = Field(..., description="Armor name")
    armor_class: int = Field(..., ge=0, description="Base AC")
    armor_type: str = Field(..., description="Armor category")
    strength_requirement: int = Field(default=0, description="Minimum STR")
    stealth_disadvantage: bool = Field(
        default=False, description="Stealth disadvantage"
    )
    is_equipped: bool = Field(default=True, description="Whether worn")


class EquipmentItemResponse(BaseModel):
    """Equipment item for character sheet."""

    name: str = Field(..., description="Item name")
    quantity: int = Field(default=1, ge=1, description="Quantity")
    description: str = Field(default="", description="Item description")
    weight: float = Field(default=0.0, ge=0, description="Weight in pounds")


class SpellResponse(BaseModel):
    """Spell data for character sheet."""

    name: str = Field(..., description="Spell name")
    level: int = Field(..., ge=0, le=9, description="Spell level (0 = cantrip)")
    school: str = Field(default="", description="School of magic")
    casting_time: str = Field(default="1 action", description="Casting time")
    range: str = Field(default="Self", description="Spell range")
    components: list[str] = Field(default_factory=list, description="V/S/M components")
    duration: str = Field(default="Instantaneous", description="Duration")
    description: str = Field(default="", description="Spell description")
    is_prepared: bool = Field(default=True, description="Whether prepared")


class SpellSlotsResponse(BaseModel):
    """Spell slot tracking for a single level."""

    max: int = Field(..., ge=0, description="Maximum slots")
    current: int = Field(..., ge=0, description="Current available slots")


class DeathSavesResponse(BaseModel):
    """Death saving throw tracking."""

    successes: int = Field(default=0, ge=0, le=3, description="Successful saves")
    failures: int = Field(default=0, ge=0, le=3, description="Failed saves")


class CharacterSheetResponse(BaseModel):
    """Full D&D 5e character sheet response."""

    # Basic Info
    name: str = Field(..., description="Character name")
    race: str = Field(..., description="Character race")
    character_class: str = Field(..., description="Character class")
    level: int = Field(default=1, ge=1, le=20, description="Character level")
    background: str = Field(default="", description="Character background")
    alignment: str = Field(default="", description="Alignment")
    experience_points: int = Field(default=0, ge=0, description="XP total")

    # Ability Scores
    strength: int = Field(..., ge=1, le=30, description="STR score")
    dexterity: int = Field(..., ge=1, le=30, description="DEX score")
    constitution: int = Field(..., ge=1, le=30, description="CON score")
    intelligence: int = Field(..., ge=1, le=30, description="INT score")
    wisdom: int = Field(..., ge=1, le=30, description="WIS score")
    charisma: int = Field(..., ge=1, le=30, description="CHA score")

    # Computed Modifiers
    strength_modifier: int = Field(..., description="STR modifier")
    dexterity_modifier: int = Field(..., description="DEX modifier")
    constitution_modifier: int = Field(..., description="CON modifier")
    intelligence_modifier: int = Field(..., description="INT modifier")
    wisdom_modifier: int = Field(..., description="WIS modifier")
    charisma_modifier: int = Field(..., description="CHA modifier")
    proficiency_bonus: int = Field(..., description="Proficiency bonus")

    # Combat Stats
    armor_class: int = Field(..., ge=1, description="Armor Class")
    initiative: int = Field(default=0, description="Initiative modifier")
    speed: int = Field(default=30, ge=0, description="Speed in feet")
    hit_points_max: int = Field(..., ge=1, description="Maximum HP")
    hit_points_current: int = Field(..., ge=0, description="Current HP")
    hit_points_temp: int = Field(default=0, ge=0, description="Temporary HP")
    hit_dice: str = Field(..., description="Hit dice (e.g., 5d10)")
    hit_dice_remaining: int = Field(..., ge=0, description="Remaining hit dice")

    # Saving Throws
    saving_throw_proficiencies: list[str] = Field(
        default_factory=list, description="Abilities proficient in saves"
    )

    # Skills
    skill_proficiencies: list[str] = Field(
        default_factory=list, description="Skills with proficiency"
    )
    skill_expertise: list[str] = Field(
        default_factory=list, description="Skills with expertise"
    )

    # Proficiencies
    armor_proficiencies: list[str] = Field(default_factory=list)
    weapon_proficiencies: list[str] = Field(default_factory=list)
    tool_proficiencies: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)

    # Features & Traits
    class_features: list[str] = Field(default_factory=list)
    racial_traits: list[str] = Field(default_factory=list)
    feats: list[str] = Field(default_factory=list)

    # Equipment
    weapons: list[WeaponResponse] = Field(default_factory=list)
    armor: ArmorResponse | None = Field(default=None)
    equipment: list[EquipmentItemResponse] = Field(default_factory=list)
    gold: int = Field(default=0, ge=0)
    silver: int = Field(default=0, ge=0)
    copper: int = Field(default=0, ge=0)

    # Spellcasting
    spellcasting_ability: str | None = Field(default=None)
    spell_save_dc: int | None = Field(default=None)
    spell_attack_bonus: int | None = Field(default=None)
    cantrips: list[str] = Field(default_factory=list)
    spells_known: list[SpellResponse] = Field(default_factory=list)
    spell_slots: dict[str, SpellSlotsResponse] = Field(default_factory=dict)

    # Personality
    personality_traits: str = Field(default="")
    ideals: str = Field(default="")
    bonds: str = Field(default="")
    flaws: str = Field(default="")
    backstory: str = Field(default="")

    # Conditions & Status
    conditions: list[str] = Field(default_factory=list)
    death_saves: DeathSavesResponse = Field(default_factory=DeathSavesResponse)


# =============================================================================
# User Settings Schemas
# =============================================================================


class UserSettingsResponse(BaseModel):
    """Response for GET /api/user-settings. Never exposes raw API key values."""

    google_api_key_configured: bool = Field(
        default=False, description="Whether a Google API key is configured"
    )
    anthropic_api_key_configured: bool = Field(
        default=False, description="Whether an Anthropic API key is configured"
    )
    ollama_url: str = Field(default="", description="Ollama base URL (not secret)")
    token_limit_overrides: dict[str, int] = Field(
        default_factory=dict,
        description="Token limit overrides keyed by agent name",
    )
    image_generation_enabled: bool = Field(
        default=False, description="Whether image generation is enabled"
    )
    image_model: str = Field(
        default="imagen-4.0-generate-001", description="Image generation model"
    )


class UserSettingsUpdateRequest(BaseModel):
    """Request body for PUT /api/user-settings. Partial update."""

    google_api_key: str | None = Field(
        default=None, description="Google API key (empty string = clear)"
    )
    anthropic_api_key: str | None = Field(
        default=None, description="Anthropic API key (empty string = clear)"
    )
    ollama_url: str | None = Field(
        default=None, description="Ollama base URL (empty string = clear)"
    )
    token_limit_overrides: dict[str, int] | None = Field(
        default=None,
        description="Token limit overrides keyed by agent name",
    )
    image_generation_enabled: bool | None = Field(
        default=None, description="Whether image generation is enabled"
    )
    image_model: str | None = Field(
        default=None, description="Image generation model"
    )


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
    new_entries: list[str] = Field(
        default_factory=list,
        description="New log entries added this round (delta)",
    )
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


class WsImageReady(BaseModel):
    """Image generation completed, broadcast to all connected clients."""

    type: Literal["image_ready"] = "image_ready"
    image: SceneImageResponse = Field(
        ..., description="Generated image metadata with download URL"
    )


class WsCommandAck(BaseModel):
    """Acknowledgment that a command was received and processed."""

    type: Literal["command_ack"] = "command_ack"
    command: str = Field(..., description="The command type that was acknowledged")


# =============================================================================
# Model Listing Schema
# =============================================================================


class ModelListResponse(BaseModel):
    """Response for GET /api/models/{provider}."""

    provider: str = Field(..., description="Provider name")
    models: list[str] = Field(default_factory=list, description="Available model IDs")
    source: Literal["api", "fallback"] = Field(
        ..., description="Whether models came from live API or static fallback"
    )
    error: str | None = Field(
        default=None, description="Error message if API call failed"
    )


# =============================================================================
# Module Discovery Schemas
# =============================================================================


class ModuleInfoResponse(BaseModel):
    """Single D&D module from LLM discovery."""

    number: int = Field(..., ge=1, description="Module number for ordering")
    name: str = Field(..., description="Module name (e.g., 'Curse of Strahd')")
    description: str = Field(..., description="Brief module description")
    setting: str = Field(default="", description="Campaign setting")
    level_range: str = Field(default="", description="Recommended level range")


class ModuleDiscoveryResponse(BaseModel):
    """Response for POST /api/modules/discover."""

    modules: list[ModuleInfoResponse] = Field(
        default_factory=list, description="Discovered modules"
    )
    provider: str = Field(..., description="LLM provider used")
    model: str = Field(..., description="Model used")
    source: Literal["llm", "error"] = Field(
        ..., description="Whether modules came from LLM or an error occurred"
    )
    error: str | None = Field(
        default=None, description="Error message if discovery failed"
    )


class SessionStartRequest(BaseModel):
    """Request body for starting a session with setup config."""

    selected_module: ModuleInfoResponse | None = Field(
        default=None, description="Selected adventure module (None for freeform)"
    )
    selected_characters: list[str] | None = Field(
        default=None, description="Character names to include in party"
    )
    adventure_name: str = Field(default="", description="Optional adventure name")


# =============================================================================
# Image Generation Schemas (Story 17-3)
# =============================================================================


class ImageGenerateRequest(BaseModel):
    """Optional request body for image generation endpoints."""

    context_entries: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of log entries to use for scene context",
    )


class ImageGenerateAccepted(BaseModel):
    """Response for accepted (202) image generation requests."""

    task_id: str = Field(..., description="Background task ID (UUID)")
    session_id: str = Field(..., description="Session ID")
    turn_number: int = Field(..., ge=0, description="Turn number being illustrated")
    status: Literal["pending"] = Field(default="pending", description="Task status")


class BestSceneAccepted(BaseModel):
    """Response for accepted (202) best-scene scan + generate requests.

    Uses ``status="scanning"`` to differentiate from direct image generation,
    indicating the two-phase nature (scan first, then generate).

    Story 17-4: Best Scene Scanner.
    """

    task_id: str = Field(..., description="Background task ID (UUID)")
    session_id: str = Field(..., description="Session ID")
    status: Literal["scanning"] = Field(
        default="scanning",
        description="Task status (scanning phase before generation)",
    )


class SceneImageResponse(BaseModel):
    """Response model for a generated scene image."""

    id: str = Field(..., description="Unique image ID (UUID)")
    session_id: str = Field(..., description="Session this image belongs to")
    turn_number: int = Field(..., ge=0, description="Turn number illustrated")
    prompt: str = Field(..., description="Text prompt used for generation")
    image_path: str = Field(
        ..., description="Relative path to image file within campaigns/"
    )
    provider: str = Field(..., description="Image generation provider")
    model: str = Field(..., description="Image generation model name")
    generation_mode: Literal["current", "best", "specific"] = Field(
        ..., description="How the image was requested"
    )
    generated_at: str = Field(..., description="ISO timestamp of generation")
    download_url: str = Field(..., description="URL to download the image")
