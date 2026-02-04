"""Pydantic models for GameState, AgentMemory, and related data structures.

This module defines the core data models for the autodungeon game engine:
- AgentMemory: Per-agent memory isolation with short-term buffer and long-term summary
- CharacterConfig: Character configuration with validation
- GameConfig: Game-level settings
- GameState: TypedDict wrapper for LangGraph compatibility
- UserError: User-facing error model with friendly narrative messages

Architecture note: GameState is a TypedDict (not Pydantic) because LangGraph
requires TypedDict for state management. Pydantic models are embedded within
for validation and serialization benefits.
"""

import re
from datetime import UTC, datetime
from typing import ClassVar, Literal, TypedDict

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

__all__ = [
    "AgentMemory",
    "ApiKeyFieldState",
    "Armor",
    "CharacterConfig",
    "CharacterFacts",
    "CharacterSheet",
    "DeathSaves",
    "DMConfig",
    "EquipmentItem",
    "ERROR_TYPES",
    "GameConfig",
    "GameState",
    "ModuleDiscoveryResult",
    "ModuleInfo",
    "NarrativeMessage",
    "MessageSegment",
    "SessionMetadata",
    "Spell",
    "SpellSlots",
    "TranscriptEntry",
    "UserError",
    "ValidationResult",
    "Weapon",
    "create_agent_memory",
    "create_character_facts_from_config",
    "create_initial_game_state",
    "create_user_error",
    "populate_game_state",
    "parse_log_entry",
    "parse_message_content",
]

# Supported LLM providers (used by both CharacterConfig and DMConfig)
_SUPPORTED_PROVIDERS = frozenset(["gemini", "claude", "ollama"])

# Module-level compiled regex patterns for message parsing
# Pattern allows spaces in agent names (e.g., "brother aldric")
# Captures colon and optional space after bracket as part of prefix, not content
LOG_ENTRY_PATTERN = re.compile(r"^\[([^\]]+)\]:?\s*(.*)$")
ACTION_PATTERN = re.compile(r"\*([^*]+)\*")


class CharacterFacts(BaseModel):
    """Persistent character identity that carries across sessions.

    This model captures the essential facts about a character that should
    persist between sessions and always be included in agent context.
    Story 5.4: Cross-Session Memory & Character Facts.

    Attributes:
        name: Character's name (e.g., "Shadowmere").
        character_class: D&D class (e.g., "Rogue").
        key_traits: Core personality traits and quirks (max 10).
        relationships: Dict of character name -> relationship description (max 20).
        notable_events: List of significant events involving this character (max 20).
    """

    # Limits to prevent unbounded growth across sessions
    MAX_KEY_TRAITS: ClassVar[int] = 10
    MAX_RELATIONSHIPS: ClassVar[int] = 20
    MAX_NOTABLE_EVENTS: ClassVar[int] = 20

    name: str = Field(..., min_length=1, description="Character's name")
    character_class: str = Field(..., min_length=1, description="D&D class")
    key_traits: list[str] = Field(
        default_factory=list,
        max_length=MAX_KEY_TRAITS,
        description="Core personality traits and quirks (max 10)",
    )
    relationships: dict[str, str] = Field(
        default_factory=dict,
        description="Character name -> relationship description (max 20)",
    )
    notable_events: list[str] = Field(
        default_factory=list,
        max_length=MAX_NOTABLE_EVENTS,
        description="Significant events involving this character (max 20)",
    )

    @field_validator("relationships")
    @classmethod
    def relationships_max_size(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate that relationships dict doesn't exceed max size."""
        if len(v) > cls.MAX_RELATIONSHIPS:
            raise ValueError(
                f"relationships cannot have more than {cls.MAX_RELATIONSHIPS} entries, "
                f"got {len(v)}"
            )
        return v


class AgentMemory(BaseModel):
    """Per-agent memory for context management.

    The memory system supports asymmetric information:
    - PC agents only see their own AgentMemory (strict isolation)
    - DM agent has read access to ALL agent memories (enables dramatic irony)

    Attributes:
        long_term_summary: Compressed history from the summarizer agent.
            Contains key events, character facts, and narrative threads.
        short_term_buffer: Recent turns, candidates for compression when
            approaching token_limit. Newest entries at the end.
        token_limit: Maximum tokens for this agent's context window.
            Context Manager node checks this before each turn.
        character_facts: Persistent character identity (Story 5.4).
            Carries across sessions and is always included in context.
    """

    long_term_summary: str = Field(
        default="",
        description="Compressed history from the summarizer",
    )
    short_term_buffer: list[str] = Field(
        default_factory=list,
        description="Recent turns, newest at the end",
    )
    token_limit: int = Field(
        default=8000,
        ge=1,
        description="Maximum tokens for this agent's context",
    )
    character_facts: CharacterFacts | None = Field(
        default=None,
        description="Persistent character identity (Story 5.4)",
    )


class CharacterConfig(BaseModel):
    """Configuration for a player character.

    Defines the character's identity, personality, visual appearance,
    and LLM provider settings. Loaded from YAML character files.

    Attributes:
        name: Character name (e.g., "Shadowmere"). Must not be empty.
        character_class: D&D class (e.g., "Rogue", "Fighter").
        personality: Personality traits for roleplay guidance.
        color: Hex color for UI display (e.g., "#6B8E6B").
        provider: LLM provider: "gemini", "claude", or "ollama".
        model: Model name (e.g., "gemini-1.5-flash").
        token_limit: Context limit for this character's agent.
    """

    name: str = Field(..., min_length=1, description="Character name")
    character_class: str = Field(..., description="D&D class")
    personality: str = Field(..., description="Personality traits")
    color: str = Field(..., description="Hex color for UI (e.g., #6B8E6B)")
    provider: str = Field(default="gemini", description="LLM provider")
    model: str = Field(default="gemini-1.5-flash", description="Model name")
    token_limit: int = Field(
        default=4000,
        ge=1,
        description="Context limit for this character",
    )

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Validate that name is not empty or whitespace."""
        if not v.strip():
            raise ValueError("name must not be empty or whitespace")
        return v

    @field_validator("color")
    @classmethod
    def color_is_hex(cls, v: str) -> str:
        """Validate that color is a valid hex color format."""
        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        if not hex_pattern.match(v):
            raise ValueError(
                f"color must be a valid hex color (e.g., #6B8E6B), got: {v}"
            )
        return v

    @field_validator("provider")
    @classmethod
    def provider_is_supported(cls, v: str) -> str:
        """Validate that provider is a supported LLM provider."""
        normalized = v.lower()
        if normalized not in _SUPPORTED_PROVIDERS:
            supported = ", ".join(sorted(_SUPPORTED_PROVIDERS))
            raise ValueError(f"provider must be one of: {supported}, got: {v}")
        return normalized


class DMConfig(BaseModel):
    """Configuration for the Dungeon Master agent.

    Defines the DM's display settings and LLM provider configuration.
    The DM orchestrates the game, narrates scenes, and controls NPCs.

    Attributes:
        name: Display name for the DM (default: "Dungeon Master").
        provider: LLM provider: "gemini", "claude", or "ollama".
        model: Model name (e.g., "gemini-1.5-flash").
        token_limit: Context limit for the DM's memory window.
        color: Hex color for UI display (gold/amber tone).
    """

    name: str = Field(default="Dungeon Master", description="DM display name")
    provider: str = Field(default="gemini", description="LLM provider")
    model: str = Field(default="gemini-1.5-flash", description="Model name")
    token_limit: int = Field(
        default=8000,
        ge=1,
        description="Context limit for DM",
    )
    color: str = Field(default="#D4A574", description="Hex color for UI")

    @field_validator("provider")
    @classmethod
    def provider_is_supported(cls, v: str) -> str:
        """Validate that provider is a supported LLM provider."""
        normalized = v.lower()
        if normalized not in _SUPPORTED_PROVIDERS:
            supported = ", ".join(sorted(_SUPPORTED_PROVIDERS))
            raise ValueError(f"provider must be one of: {supported}, got: {v}")
        return normalized

    @field_validator("color")
    @classmethod
    def color_is_hex(cls, v: str) -> str:
        """Validate that color is a valid hex color format."""
        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        if not hex_pattern.match(v):
            raise ValueError(
                f"color must be a valid hex color (e.g., #D4A574), got: {v}"
            )
        return v


class GameConfig(BaseModel):
    """Game-level configuration settings.

    Attributes:
        combat_mode: How combat is handled - "Narrative" for story-focused
            or "Tactical" for detailed mechanics.
        summarizer_provider: LLM provider for memory compression (Story 6.3).
        summarizer_model: Model used for memory compression.
        party_size: Number of player characters in the party.
    """

    combat_mode: Literal["Narrative", "Tactical"] = Field(
        default="Narrative",
        description="Combat handling mode",
    )
    summarizer_provider: str = Field(
        default="gemini",
        description="Provider for memory compression (Story 6.3)",
    )
    summarizer_model: str = Field(
        default="gemini-1.5-flash",
        description="Model for memory compression",
    )
    party_size: int = Field(
        default=4,
        ge=1,
        le=8,
        description="Number of player characters",
    )


class SessionMetadata(BaseModel):
    """Metadata for a game session stored in config.yaml.

    This model tracks session-level information for the session browser UI
    and multi-session continuity (Story 4.3).

    Attributes:
        session_id: Session ID string (e.g., "001").
        session_number: Numeric session number.
        name: Optional user-friendly session name.
        created_at: ISO timestamp when session was created.
        updated_at: ISO timestamp of last checkpoint.
        character_names: List of PC character names for display.
        turn_count: Number of turns/checkpoints in session.
    """

    session_id: str = Field(..., min_length=1, description="Session ID string")
    session_number: int = Field(..., ge=1, description="Numeric session number")
    name: str = Field(default="", description="User-friendly session name")
    created_at: str = Field(..., description="ISO timestamp when session was created")
    updated_at: str = Field(..., description="ISO timestamp of last checkpoint")
    character_names: list[str] = Field(
        default_factory=list, description="List of PC character names for display"
    )
    turn_count: int = Field(default=0, ge=0, description="Number of turns in session")


class TranscriptEntry(BaseModel):
    """A single entry in the session transcript for research export.

    Captures everything needed for research analysis (Story 4.4):
    - Turn number for sequence ordering
    - ISO timestamp for timing analysis
    - Agent name for character differentiation
    - Full content for coherence scoring
    - Tool calls for mechanic analysis

    Transcript Schema Documentation for Researchers:
    - turn: Turn number (1-indexed), used for sequencing entries
    - timestamp: ISO 8601 format (e.g., "2026-01-25T14:35:22Z")
    - agent: Agent key who generated this content (e.g., "dm", "rogue", "fighter")
    - content: Full message content (never truncated, supports coherence analysis)
    - tool_calls: List of tool call records with name, args, and result fields

    Attributes:
        turn: Turn number (1-indexed).
        timestamp: ISO format timestamp (e.g., "2026-01-25T14:35:22Z").
        agent: Agent key who generated this content (e.g., "dm", "rogue").
        content: Full message content (not truncated).
        tool_calls: List of tool call records, or None if no tools used.
    """

    turn: int = Field(..., ge=1, description="Turn number (1-indexed)")
    timestamp: str = Field(..., description="ISO format timestamp")
    agent: str = Field(..., min_length=1, description="Agent key")
    content: str = Field(..., description="Full message content")
    tool_calls: list[dict[str, object]] | None = Field(
        default=None, description="Tool calls made during this turn"
    )


# =============================================================================
# Module Discovery (Story 7.1)
# =============================================================================


class ModuleInfo(BaseModel):
    """D&D module information from LLM knowledge.

    Represents a single D&D module/adventure that the LLM knows from its
    training data. Used in the module selection UI during new adventure setup.

    Story 7.1: Module Discovery via LLM Query.

    Attributes:
        number: Module number (1-100) for ordering in the list.
        name: Official module name (e.g., "Curse of Strahd").
        description: Brief 1-2 sentence description of the adventure.
        setting: Campaign setting (e.g., "Forgotten Realms", "Ravenloft").
        level_range: Recommended level range (e.g., "1-5", "5-10").
    """

    number: int = Field(..., ge=1, le=100, description="Module number (1-100)")
    name: str = Field(..., min_length=1, description="Module name")
    description: str = Field(..., min_length=1, description="Brief module description")
    setting: str = Field(
        default="", description="Campaign setting (e.g., Forgotten Realms)"
    )
    level_range: str = Field(
        default="", description="Recommended level range (e.g., 1-5)"
    )


class ModuleDiscoveryResult(BaseModel):
    """Result of module discovery LLM query.

    Wraps the list of discovered modules with metadata about the discovery
    process (which provider/model was used, timestamp, retry count).

    Story 7.1: Module Discovery via LLM Query.

    Attributes:
        modules: List of discovered ModuleInfo objects.
        provider: LLM provider used for discovery (e.g., "gemini").
        model: Model name used for discovery (e.g., "gemini-1.5-flash").
        timestamp: ISO timestamp when discovery completed.
        retry_count: Number of retries needed to get valid JSON response.
    """

    modules: list[ModuleInfo] = Field(default_factory=list)
    provider: str = Field(..., description="Provider used for discovery")
    model: str = Field(..., description="Model used for discovery")
    timestamp: str = Field(..., description="ISO timestamp of discovery")
    retry_count: int = Field(default=0, ge=0, description="Number of retries needed")


# =============================================================================
# Error Handling (Story 4.5)
# =============================================================================

# Error type definitions with campfire-narrative style messages
ERROR_TYPES: dict[str, dict[str, str]] = {
    "timeout": {
        "title": "The magical connection was interrupted...",
        "message": "The spirits took too long to respond. The astral plane may be congested.",
        "action": "Try again or restore to your last checkpoint.",
    },
    "rate_limit": {
        "title": "The spirits need rest...",
        "message": "Too many requests have been made. Wait a moment before continuing.",
        "action": "Wait a few seconds, then try again.",
    },
    "auth_error": {
        "title": "The magical seal is broken...",
        "message": "Your credentials could not be verified. Check your API keys.",
        "action": "Check your API configuration in LLM Status.",
    },
    "network_error": {
        "title": "The connection to the realm has been severed...",
        "message": "Unable to reach the spirit realm. Check your internet connection.",
        "action": "Check your connection, or try Ollama for offline play.",
    },
    "invalid_response": {
        "title": "The spirits speak in riddles...",
        "message": "The response could not be understood. This may be temporary.",
        "action": "Try again or restore to your last checkpoint.",
    },
    "unknown": {
        "title": "Something unexpected happened...",
        "message": "An unknown error occurred in the magical realm.",
        "action": "Try again or restore to your last checkpoint.",
    },
    "module_discovery_failed": {
        "title": "The Dungeon Master's library is unreachable...",
        "message": "Could not retrieve the list of known adventures. The tomes are shrouded in magical mist.",
        "action": "Try again, or start a freeform adventure without a specific module.",
    },
}


class UserError(BaseModel):
    """User-facing error with friendly narrative-style messages.

    This model represents errors shown to users in the UI, following the
    campfire aesthetic with narrative-style messaging. Technical details
    are logged separately and never exposed to users.

    Attributes:
        title: Friendly title explaining what happened (e.g., "The magical connection was interrupted...").
        message: User-friendly explanation of the error.
        action: Suggested action for the user to take.
        error_type: Internal error category (timeout, rate_limit, auth_error, network_error, invalid_response, unknown).
        timestamp: ISO format timestamp when error occurred.
        provider: LLM provider that caused the error (for internal tracking).
        agent: Agent that was executing when error occurred (for internal tracking).
        retry_count: Number of retry attempts made (max 3).
        last_checkpoint_turn: Turn number of last successful checkpoint for recovery.
    """

    title: str = Field(..., description="Friendly narrative-style title")
    message: str = Field(..., description="User-friendly explanation")
    action: str = Field(..., description="Suggested action for user")
    error_type: str = Field(..., description="Internal error category")
    timestamp: str = Field(..., description="ISO format timestamp")
    provider: str = Field(default="", description="LLM provider that caused error")
    agent: str = Field(default="", description="Agent that was executing")
    retry_count: int = Field(default=0, ge=0, le=3, description="Retry attempts made")
    last_checkpoint_turn: int | None = Field(
        default=None, description="Last successful checkpoint turn number"
    )


def create_user_error(
    error_type: str,
    provider: str = "",
    agent: str = "",
    retry_count: int = 0,
    last_checkpoint_turn: int | None = None,
) -> UserError:
    """Factory function to create a UserError with appropriate messages.

    Looks up the error_type in ERROR_TYPES to get friendly narrative-style
    title, message, and action text. Falls back to "unknown" error type
    if the provided type is not recognized.

    Args:
        error_type: Error category (timeout, rate_limit, auth_error, network_error, invalid_response, unknown).
        provider: LLM provider name (e.g., "gemini", "claude", "ollama").
        agent: Agent name that was executing (e.g., "dm", "fighter").
        retry_count: Number of retry attempts already made.
        last_checkpoint_turn: Turn number of last successful checkpoint.

    Returns:
        UserError with friendly messages populated from ERROR_TYPES.
    """
    # Fall back to unknown if error_type not recognized
    error_info = ERROR_TYPES.get(error_type, ERROR_TYPES["unknown"])

    return UserError(
        title=error_info["title"],
        message=error_info["message"],
        action=error_info["action"],
        error_type=error_type if error_type in ERROR_TYPES else "unknown",
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        provider=provider,
        agent=agent,
        retry_count=retry_count,
        last_checkpoint_turn=last_checkpoint_turn,
    )


# =============================================================================
# API Key Validation (Story 6.2)
# =============================================================================


class ValidationResult(BaseModel):
    """Result of API key or connection validation.

    Used by the API Keys tab in the configuration modal to show
    validation status after testing provider credentials.

    Attributes:
        valid: Whether the validation passed.
        message: Human-readable status message.
        models: List of available models if valid, None otherwise.
    """

    valid: bool = Field(..., description="Whether the validation passed")
    message: str = Field(..., description="Human-readable status message")
    models: list[str] | None = Field(
        default=None, description="List of available models if valid"
    )


class ApiKeyFieldState(BaseModel):
    """State tracking for an API key input field.

    Tracks the current value, source (where it came from), and validation
    status for display in the configuration modal.

    Attributes:
        value: Current field value (may be masked for display).
        source: Where the value comes from: "empty", "environment", or "ui_override".
        validation_status: Current validation status: "untested", "validating", "valid", or "invalid".
        validation_message: Message from last validation attempt.
        show_value: Whether to show the actual value (vs masked).
    """

    value: str = Field(default="", description="Current field value")
    source: Literal["empty", "environment", "ui_override"] = Field(
        default="empty", description="Where the value comes from"
    )
    validation_status: Literal["untested", "validating", "valid", "invalid"] = Field(
        default="untested", description="Current validation status"
    )
    validation_message: str = Field(
        default="", description="Message from last validation"
    )
    show_value: bool = Field(
        default=False, description="Whether to show actual value vs masked"
    )


# =============================================================================
# Character Sheet Models (Story 8.1)
# =============================================================================


class Weapon(BaseModel):
    """A weapon in character inventory.

    Story 8.1: Character Sheet Data Model.

    Attributes:
        name: Weapon name (e.g., "Longsword").
        damage_dice: Damage dice notation (e.g., "1d8").
        damage_type: Type of damage (e.g., "slashing", "piercing", "bludgeoning").
        properties: List of weapon properties (e.g., ["versatile", "finesse"]).
        attack_bonus: Additional attack bonus from magic or other sources.
        is_equipped: Whether the weapon is currently equipped.
    """

    name: str = Field(..., min_length=1, description="Weapon name")
    damage_dice: str = Field(
        ...,
        pattern=r"^\d+d\d+([+-]\d+)?$",
        description="Damage dice notation (e.g., 1d8, 2d6+2, 1d10-1)",
    )
    damage_type: str = Field(default="slashing", description="Damage type")
    properties: list[str] = Field(default_factory=list, description="Weapon properties")
    attack_bonus: int = Field(default=0, description="Magic/other attack bonus")
    is_equipped: bool = Field(default=False, description="Whether weapon is equipped")


class Armor(BaseModel):
    """Armor worn by a character.

    Story 8.1: Character Sheet Data Model.

    Attributes:
        name: Armor name (e.g., "Chain Mail").
        armor_class: Base AC provided by armor.
        armor_type: Category (light, medium, heavy, shield).
        strength_requirement: Minimum STR required (0 if none).
        stealth_disadvantage: Whether armor imposes disadvantage on Stealth.
        is_equipped: Whether the armor is currently worn.
    """

    name: str = Field(..., min_length=1, description="Armor name")
    armor_class: int = Field(
        ..., ge=0, le=20, description="Base AC or bonus (shields use +2)"
    )
    armor_type: Literal["light", "medium", "heavy", "shield"] = Field(
        ..., description="Armor category"
    )
    strength_requirement: int = Field(
        default=0, ge=0, description="Minimum STR required"
    )
    stealth_disadvantage: bool = Field(
        default=False, description="Imposes Stealth disadvantage"
    )
    is_equipped: bool = Field(default=True, description="Whether armor is worn")


class EquipmentItem(BaseModel):
    """A non-weapon, non-armor item in inventory.

    Story 8.1: Character Sheet Data Model.

    Attributes:
        name: Item name (e.g., "Rope, 50 feet").
        quantity: Number of this item (default 1).
        description: Optional description or notes.
        weight: Weight in pounds (optional).
    """

    name: str = Field(..., min_length=1, description="Item name")
    quantity: int = Field(default=1, ge=1, description="Quantity")
    description: str = Field(default="", description="Item description")
    weight: float = Field(default=0.0, ge=0, description="Weight in pounds")


class Spell(BaseModel):
    """A spell known or prepared by a character.

    Story 8.1: Character Sheet Data Model.

    Attributes:
        name: Spell name (e.g., "Fireball").
        level: Spell level (0 for cantrips, 1-9 for leveled spells).
        school: School of magic (e.g., "evocation", "abjuration").
        casting_time: Time required (e.g., "1 action", "1 minute").
        range: Spell range (e.g., "120 feet", "Self").
        components: Required components (e.g., ["V", "S", "M"]).
        duration: How long effect lasts (e.g., "Instantaneous", "1 hour").
        description: Brief spell description.
        is_prepared: Whether spell is currently prepared (for prepared casters).
    """

    name: str = Field(..., min_length=1, description="Spell name")
    level: int = Field(..., ge=0, le=9, description="Spell level (0 = cantrip)")
    school: str = Field(default="", description="School of magic")
    casting_time: str = Field(default="1 action", description="Casting time")
    range: str = Field(default="Self", description="Spell range")
    components: list[str] = Field(default_factory=list, description="V/S/M components")
    duration: str = Field(default="Instantaneous", description="Duration")
    description: str = Field(default="", description="Spell description")
    is_prepared: bool = Field(default=True, description="Whether prepared")


class SpellSlots(BaseModel):
    """Spell slot tracking for a single spell level.

    Story 8.1: Character Sheet Data Model.

    Attributes:
        max: Maximum number of slots at this level.
        current: Current available slots (may be less if expended).
    """

    max: int = Field(..., ge=0, le=4, description="Maximum slots")
    current: int = Field(..., ge=0, description="Current available slots")

    @field_validator("current")
    @classmethod
    def current_not_exceeds_max(cls, v: int, info: ValidationInfo) -> int:
        """Ensure current slots don't exceed max."""
        max_val = info.data.get("max", 4)
        if v > max_val:
            raise ValueError(f"current ({v}) cannot exceed max ({max_val})")
        return v


class DeathSaves(BaseModel):
    """Death saving throw tracking.

    Story 8.1: Character Sheet Data Model.

    Attributes:
        successes: Number of successful death saves (0-3).
        failures: Number of failed death saves (0-3).
    """

    successes: int = Field(default=0, ge=0, le=3, description="Successful saves")
    failures: int = Field(default=0, ge=0, le=3, description="Failed saves")

    @property
    def is_stable(self) -> bool:
        """Character stabilized with 3 successes."""
        return self.successes >= 3

    @property
    def is_dead(self) -> bool:
        """Character died with 3 failures."""
        return self.failures >= 3


class CharacterSheet(BaseModel):
    """Complete D&D 5e character sheet with all standard fields.

    This model represents a full player character sheet including
    basic info, abilities, combat stats, proficiencies, equipment,
    spells, and personality traits.

    Story 8.1: Character Sheet Data Model.
    FRs: FR60, FR61, FR62, FR65, FR66.

    Attributes:
        (See individual field descriptions below)
    """

    # ==========================================================================
    # Basic Info
    # ==========================================================================
    name: str = Field(..., min_length=1, description="Character name")
    race: str = Field(..., min_length=1, description="Character race")
    character_class: str = Field(..., min_length=1, description="Character class")
    level: int = Field(default=1, ge=1, le=20, description="Character level (1-20)")
    background: str = Field(default="", description="Character background")
    alignment: str = Field(default="", description="Alignment (e.g., Neutral Good)")
    experience_points: int = Field(default=0, ge=0, description="XP total")

    # ==========================================================================
    # Ability Scores (raw scores, modifiers computed)
    # ==========================================================================
    strength: int = Field(..., ge=1, le=30, description="STR score")
    dexterity: int = Field(..., ge=1, le=30, description="DEX score")
    constitution: int = Field(..., ge=1, le=30, description="CON score")
    intelligence: int = Field(..., ge=1, le=30, description="INT score")
    wisdom: int = Field(..., ge=1, le=30, description="WIS score")
    charisma: int = Field(..., ge=1, le=30, description="CHA score")

    # ==========================================================================
    # Combat Stats
    # ==========================================================================
    armor_class: int = Field(..., ge=1, description="Armor Class")
    initiative: int = Field(default=0, description="Initiative modifier")
    speed: int = Field(default=30, ge=0, description="Speed in feet")
    hit_points_max: int = Field(..., ge=1, description="Maximum HP")
    hit_points_current: int = Field(..., ge=0, description="Current HP")
    hit_points_temp: int = Field(default=0, ge=0, description="Temporary HP")
    hit_dice: str = Field(
        ..., pattern=r"^\d+d\d+$", description="Hit dice (e.g., 5d10)"
    )
    hit_dice_remaining: int = Field(..., ge=0, description="Remaining hit dice")

    # ==========================================================================
    # Saving Throws
    # ==========================================================================
    saving_throw_proficiencies: list[str] = Field(
        default_factory=list,
        description="Abilities proficient in saves (e.g., ['strength', 'constitution'])",
    )

    # ==========================================================================
    # Skills
    # ==========================================================================
    skill_proficiencies: list[str] = Field(
        default_factory=list, description="Skills with proficiency"
    )
    skill_expertise: list[str] = Field(
        default_factory=list, description="Skills with expertise (double proficiency)"
    )

    # ==========================================================================
    # Proficiencies
    # ==========================================================================
    armor_proficiencies: list[str] = Field(
        default_factory=list, description="Armor types proficient with"
    )
    weapon_proficiencies: list[str] = Field(
        default_factory=list, description="Weapon types proficient with"
    )
    tool_proficiencies: list[str] = Field(
        default_factory=list, description="Tools proficient with"
    )
    languages: list[str] = Field(default_factory=list, description="Languages known")

    # ==========================================================================
    # Features & Traits
    # ==========================================================================
    class_features: list[str] = Field(
        default_factory=list,
        description="Class features (e.g., Second Wind, Sneak Attack)",
    )
    racial_traits: list[str] = Field(
        default_factory=list,
        description="Racial traits (e.g., Darkvision, Fey Ancestry)",
    )
    feats: list[str] = Field(default_factory=list, description="Feats taken")

    # ==========================================================================
    # Equipment & Inventory
    # ==========================================================================
    weapons: list[Weapon] = Field(
        default_factory=list, description="Weapons in inventory"
    )
    armor: Armor | None = Field(
        default=None, description="Armor worn (None if unarmored)"
    )
    equipment: list[EquipmentItem] = Field(
        default_factory=list, description="Other equipment and items"
    )
    gold: int = Field(default=0, ge=0, description="Gold pieces")
    silver: int = Field(default=0, ge=0, description="Silver pieces")
    copper: int = Field(default=0, ge=0, description="Copper pieces")

    # ==========================================================================
    # Spellcasting (optional, None for non-casters)
    # ==========================================================================
    spellcasting_ability: str | None = Field(
        default=None,
        description="Spellcasting ability (e.g., 'intelligence', 'wisdom', 'charisma')",
    )
    spell_save_dc: int | None = Field(default=None, ge=1, description="Spell save DC")
    spell_attack_bonus: int | None = Field(
        default=None, description="Spell attack modifier"
    )
    cantrips: list[str] = Field(default_factory=list, description="Known cantrip names")
    spells_known: list[Spell] = Field(
        default_factory=list, description="Full spell data for known/prepared spells"
    )
    spell_slots: dict[int, SpellSlots] = Field(
        default_factory=dict, description="Spell slots by level (1-9)"
    )

    # ==========================================================================
    # Personality
    # ==========================================================================
    personality_traits: str = Field(default="", description="Personality traits")
    ideals: str = Field(default="", description="Ideals")
    bonds: str = Field(default="", description="Bonds")
    flaws: str = Field(default="", description="Flaws")
    backstory: str = Field(default="", description="Character backstory")

    # ==========================================================================
    # Conditions & Status
    # ==========================================================================
    conditions: list[str] = Field(
        default_factory=list,
        description="Active conditions (poisoned, exhausted, etc.)",
    )
    death_saves: DeathSaves = Field(
        default_factory=DeathSaves, description="Death saving throw status"
    )

    # ==========================================================================
    # Computed Properties
    # ==========================================================================

    @property
    def strength_modifier(self) -> int:
        """Calculate STR modifier from score."""
        return (self.strength - 10) // 2

    @property
    def dexterity_modifier(self) -> int:
        """Calculate DEX modifier from score."""
        return (self.dexterity - 10) // 2

    @property
    def constitution_modifier(self) -> int:
        """Calculate CON modifier from score."""
        return (self.constitution - 10) // 2

    @property
    def intelligence_modifier(self) -> int:
        """Calculate INT modifier from score."""
        return (self.intelligence - 10) // 2

    @property
    def wisdom_modifier(self) -> int:
        """Calculate WIS modifier from score."""
        return (self.wisdom - 10) // 2

    @property
    def charisma_modifier(self) -> int:
        """Calculate CHA modifier from score."""
        return (self.charisma - 10) // 2

    @property
    def proficiency_bonus(self) -> int:
        """Calculate proficiency bonus from level per D&D 5e rules.

        Levels 1-4: +2
        Levels 5-8: +3
        Levels 9-12: +4
        Levels 13-16: +5
        Levels 17-20: +6
        """
        return (self.level - 1) // 4 + 2

    def get_ability_modifier(self, ability: str) -> int:
        """Get modifier for a named ability.

        Args:
            ability: Ability name (strength, dexterity, etc.) or short form (str, dex)

        Returns:
            The ability modifier.

        Raises:
            ValueError: If ability name is not recognized.
        """
        ability_lower = ability.lower()
        abilities = {
            "strength": self.strength_modifier,
            "dexterity": self.dexterity_modifier,
            "constitution": self.constitution_modifier,
            "intelligence": self.intelligence_modifier,
            "wisdom": self.wisdom_modifier,
            "charisma": self.charisma_modifier,
            # Short forms
            "str": self.strength_modifier,
            "dex": self.dexterity_modifier,
            "con": self.constitution_modifier,
            "int": self.intelligence_modifier,
            "wis": self.wisdom_modifier,
            "cha": self.charisma_modifier,
        }
        if ability_lower not in abilities:
            raise ValueError(f"Unknown ability: {ability}")
        return abilities[ability_lower]

    @field_validator("hit_dice_remaining")
    @classmethod
    def hit_dice_remaining_valid(cls, v: int, info: ValidationInfo) -> int:
        """Ensure remaining hit dice doesn't exceed level."""
        level = info.data.get("level", 1)
        if v > level:
            raise ValueError(f"hit_dice_remaining ({v}) cannot exceed level ({level})")
        return v

    @model_validator(mode="after")
    def validate_hit_points(self) -> "CharacterSheet":
        """Ensure current HP doesn't exceed max HP + temp HP."""
        max_allowed = self.hit_points_max + self.hit_points_temp
        if self.hit_points_current > max_allowed:
            raise ValueError(
                f"hit_points_current ({self.hit_points_current}) cannot exceed "
                f"hit_points_max + hit_points_temp ({self.hit_points_max} + {self.hit_points_temp} = {max_allowed})"
            )
        return self


class GameState(TypedDict):
    """LangGraph-compatible state container for the game.

    This is a TypedDict (NOT Pydantic) because LangGraph requires TypedDict
    for state management. Pydantic models are embedded for their validation
    and serialization benefits.

    Attributes:
        ground_truth_log: Append-only complete history of all game events.
            Used for transcript export and debugging.
        turn_queue: List of agent names in turn order (e.g., ["dm", "fighter", "rogue"]).
        current_turn: Name of the agent whose turn it currently is.
        agent_memories: Per-agent memory with isolated context.
            Keys are agent names, values are AgentMemory instances.
        game_config: Game-level settings.
        dm_config: Dungeon Master agent configuration.
        characters: Character configurations keyed by lowercase agent name.
            Used by pc_turn to access CharacterConfig during turn execution.
        whisper_queue: Private messages between agents (DM-to-player hints).
        human_active: Whether a human has taken control.
        controlled_character: Name of the character the human controls, or None.
        session_number: Current session number for display (default 1).
        session_id: Unique session identifier for persistence (e.g., "001").
        summarization_in_progress: True while memory compression is running.
            Used by UI to show summarization indicator.
        selected_module: Module for DM context injection (Story 7.3).
            None for freeform adventures without a specific module.
        character_sheets: Character sheets keyed by character name (Story 8.3).
            Used for context injection into agent prompts.
    """

    ground_truth_log: list[str]
    turn_queue: list[str]
    current_turn: str
    agent_memories: dict[str, AgentMemory]
    game_config: GameConfig
    dm_config: DMConfig
    characters: dict[str, CharacterConfig]
    whisper_queue: list[str]
    human_active: bool
    controlled_character: str | None
    session_number: int
    session_id: str
    summarization_in_progress: bool
    selected_module: ModuleInfo | None
    character_sheets: dict[str, "CharacterSheet"]


class MessageSegment(BaseModel):
    """A segment of parsed message content with its type.

    Used by parse_message_content() to break down PC messages into
    typed segments for rendering with appropriate styling.

    Attributes:
        segment_type: Type of segment - "dialogue", "action", or "narration"
        text: The text content of this segment
    """

    segment_type: Literal["dialogue", "action", "narration"]
    text: str


class NarrativeMessage(BaseModel):
    """A parsed message from the ground_truth_log.

    Represents a single message extracted from the game log with
    agent attribution and parsed content ready for rendering.

    Attributes:
        agent: The agent key (e.g., "dm", "fighter", "rogue")
        content: The raw message content
        timestamp: Optional timestamp (reserved for future use)
    """

    agent: str
    content: str
    timestamp: str | None = None

    @property
    def message_type(self) -> Literal["dm_narration", "pc_dialogue", "sheet_update"]:
        """Determine message type based on agent name.

        Returns:
            "dm_narration" if agent is "dm" or "DM",
            "sheet_update" if agent is "SHEET",
            otherwise "pc_dialogue"
        """
        if self.agent.lower() == "dm":
            return "dm_narration"
        if self.agent.upper() == "SHEET":
            return "sheet_update"
        return "pc_dialogue"


def parse_log_entry(entry: str) -> NarrativeMessage:
    """Parse a ground_truth_log entry into a NarrativeMessage.

    Entry format: "[agent_name]: message content"

    Handles edge cases:
    - Entry without brackets → treat as DM narration
    - Empty agent `[]` → use fallback "unknown"
    - Only parses first [agent] at start of string
    - Strips duplicate agent prefix if LLM echoed the format (e.g., "[DM]: [DM]: text")

    Args:
        entry: A raw log entry string

    Returns:
        NarrativeMessage with agent and content extracted
    """
    # Use simple string parsing for reliability (regex had caching issues)
    if entry.startswith("["):
        bracket_end = entry.find("]")
        if bracket_end > 0:
            agent = entry[1:bracket_end] or "unknown"
            content = entry[bracket_end + 1 :]
            # Strip ": " or just ":" or whitespace from start of content
            content = content.lstrip(": ")
            # Handle duplicate prefix: LLM sometimes echoes "[agent]:" in response
            if content.startswith(f"[{agent}]"):
                content = content[len(agent) + 2 :].lstrip(": ")
            return NarrativeMessage(agent=agent, content=content)
    # No brackets at start - treat as DM narration
    return NarrativeMessage(agent="dm", content=entry)


def parse_message_content(content: str) -> list[MessageSegment]:
    """Parse message content into typed segments.

    Identifies dialogue (quoted text) and actions (*asterisk text*)
    for rendering with appropriate styling.

    Args:
        content: Raw message content string

    Returns:
        List of MessageSegment with type and text for each segment
    """
    segments: list[MessageSegment] = []
    pos = 0

    while pos < len(content):
        # Look for next special marker
        action_start = content.find("*", pos)
        quote_start = content.find('"', pos)

        # Determine which comes first
        if action_start == -1 and quote_start == -1:
            # No more special markers - rest is narration
            remaining = content[pos:]
            if remaining:
                segments.append(
                    MessageSegment(segment_type="narration", text=remaining)
                )
            break

        # Find the nearest marker
        if action_start == -1:
            next_marker = quote_start
            marker_type = "quote"
        elif quote_start == -1:
            next_marker = action_start
            marker_type = "action"
        elif action_start < quote_start:
            next_marker = action_start
            marker_type = "action"
        else:
            next_marker = quote_start
            marker_type = "quote"

        # Add any narration before the marker
        if next_marker > pos:
            segments.append(
                MessageSegment(segment_type="narration", text=content[pos:next_marker])
            )

        if marker_type == "action":
            # Find closing asterisk
            action_end = content.find("*", next_marker + 1)
            if action_end == -1:
                # No closing asterisk - treat as narration
                segments.append(
                    MessageSegment(segment_type="narration", text=content[next_marker:])
                )
                break
            action_text = content[next_marker + 1 : action_end]
            segments.append(MessageSegment(segment_type="action", text=action_text))
            pos = action_end + 1
        else:
            # Find closing quote
            quote_end = content.find('"', next_marker + 1)
            if quote_end == -1:
                # No closing quote - treat as narration
                segments.append(
                    MessageSegment(segment_type="narration", text=content[next_marker:])
                )
                break
            dialogue_text = content[next_marker + 1 : quote_end]
            segments.append(MessageSegment(segment_type="dialogue", text=dialogue_text))
            pos = quote_end + 1

    # Filter out empty segments (e.g., from ** double asterisks **)
    return [s for s in segments if s.text]


def create_agent_memory(
    token_limit: int = 8000, character_facts: CharacterFacts | None = None
) -> AgentMemory:
    """Factory function to create a new AgentMemory instance.

    Args:
        token_limit: Maximum tokens for this agent's context window.
        character_facts: Optional CharacterFacts for persistent identity (Story 5.4).

    Returns:
        A new AgentMemory with empty summary and buffer.
    """
    return AgentMemory(token_limit=token_limit, character_facts=character_facts)


def create_character_facts_from_config(config: "CharacterConfig") -> CharacterFacts:
    """Create CharacterFacts from a CharacterConfig.

    This factory function initializes CharacterFacts with the character's
    name and class from the config. Other fields (key_traits, relationships,
    notable_events) start empty and are populated during gameplay.

    Story 5.4: Cross-Session Memory & Character Facts.

    Args:
        config: The CharacterConfig to extract identity from.

    Returns:
        A new CharacterFacts with name and class from config.
    """
    return CharacterFacts(
        name=config.name,
        character_class=config.character_class,
    )


def create_initial_game_state() -> GameState:
    """Factory function to create an empty initial game state.

    Creates a valid, checkpoint-ready GameState with all required fields
    initialized to empty/default values. Use this at the start of a new
    game session before populating with character data.

    Returns:
        A new GameState ready for initialization.
    """
    return GameState(
        ground_truth_log=[],
        turn_queue=[],
        current_turn="",
        agent_memories={},
        game_config=GameConfig(),
        dm_config=DMConfig(),
        characters={},
        whisper_queue=[],
        human_active=False,
        controlled_character=None,
        session_number=1,
        session_id="001",
        summarization_in_progress=False,
        selected_module=None,
    )


def populate_game_state(
    include_sample_messages: bool = True,
    selected_module: ModuleInfo | None = None,
) -> GameState:
    """Factory function to create a fully populated game state from config files.

    Loads character configs from YAML files in config/characters/, builds the
    turn queue with DM first followed by PC agents, and initializes agent
    memories with appropriate token limits.

    Args:
        include_sample_messages: If True, includes sample messages in ground_truth_log
            to demonstrate message styling. Set to False for clean game starts.
        selected_module: Optional module for DM context injection (Story 7.3).
            None for freeform adventures without a specific module.

    Returns:
        A GameState populated with characters, turn queue, and agent memories.
    """
    # Import here to avoid circular import
    from config import load_character_configs, load_dm_config

    # Load configs from YAML files
    dm_config = load_dm_config()
    characters = load_character_configs()

    # Build turn queue: DM first, then PCs (sorted for deterministic order)
    turn_queue = ["dm"] + sorted(characters.keys())

    # Initialize agent memories with appropriate token limits
    # PC agents get CharacterFacts, DM does not (Story 5.4)
    agent_memories: dict[str, AgentMemory] = {}
    agent_memories["dm"] = AgentMemory(token_limit=dm_config.token_limit)
    for char_name, char_config in characters.items():
        facts = create_character_facts_from_config(char_config)
        agent_memories[char_name] = AgentMemory(
            token_limit=char_config.token_limit, character_facts=facts
        )

    # Sample messages demonstrating different message types and styling
    sample_messages: list[str] = []
    if include_sample_messages:
        sample_messages = _get_sample_messages(characters)

    # Generate session_id from session_number
    session_number = 1
    session_id = f"{session_number:03d}"

    return GameState(
        ground_truth_log=sample_messages,
        turn_queue=turn_queue,
        current_turn="dm",
        agent_memories=agent_memories,
        game_config=GameConfig(),
        dm_config=dm_config,
        characters=characters,
        whisper_queue=[],
        human_active=False,
        controlled_character=None,
        session_number=session_number,
        session_id=session_id,
        summarization_in_progress=False,
        selected_module=selected_module,
    )


def _get_sample_messages(characters: dict[str, CharacterConfig]) -> list[str]:
    """Generate sample messages for demonstrating message styling.

    Creates a sequence of DM and PC messages that showcase:
    - DM narration (gold border, italic)
    - PC dialogue with attribution (colored by class)
    - Mixed dialogue and action text (*italicized*)

    Args:
        characters: Character configs keyed by lowercase name.

    Returns:
        List of log entries in "[agent] content" format.
    """
    # Find character names by class for sample messages
    fighter_name = None
    rogue_name = None
    wizard_name = None
    cleric_name = None

    for name, config in characters.items():
        char_class = config.character_class.lower()
        if char_class == "fighter":
            fighter_name = name
        elif char_class == "rogue":
            rogue_name = name
        elif char_class == "wizard":
            wizard_name = name
        elif char_class == "cleric":
            cleric_name = name

    messages = [
        (
            "[dm] The tavern falls silent as the stranger enters, her cloak "
            "dripping with rain. The firelight catches the glint of steel "
            "beneath her traveling cloak."
        ),
    ]

    if fighter_name:
        messages.append(
            f'[{fighter_name}] "Stand ready," *{characters[fighter_name].name} '
            f'mutters, his hand moving to his sword hilt.* "Something feels '
            'wrong about this."'
        )

    if rogue_name:
        messages.append(
            f"[{rogue_name}] *{characters[rogue_name].name} melts into the "
            f'shadows near the bar, her eyes never leaving the newcomer.* "Let '
            'her make the first move."'
        )

    if wizard_name:
        messages.append(
            f"[{wizard_name}] *{characters[wizard_name].name} sets down her "
            f"wine glass, arcane symbols flickering briefly in her eyes.* "
            '"She carries powerful enchantments. Be cautious."'
        )

    if cleric_name:
        messages.append(
            f'[{cleric_name}] "Peace, friends." *{characters[cleric_name].name} '
            f'raises a calming hand.* "Perhaps she merely seeks shelter from '
            'the storm."'
        )

    messages.append(
        "[dm] The stranger approaches the bar, her boots leaving wet prints "
        "on the worn wooden floor. She speaks to the barkeep in hushed tones, "
        "then turns to survey the room. Her gaze lingers on your table."
    )

    return messages
