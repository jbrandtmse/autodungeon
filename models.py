"""Pydantic models for GameState, AgentMemory, and related data structures.

This module defines the core data models for the autodungeon game engine:
- AgentMemory: Per-agent memory isolation with short-term buffer and long-term summary
- CharacterConfig: Character configuration with validation
- GameConfig: Game-level settings
- GameState: TypedDict wrapper for LangGraph compatibility

Architecture note: GameState is a TypedDict (not Pydantic) because LangGraph
requires TypedDict for state management. Pydantic models are embedded within
for validation and serialization benefits.
"""

import re
from typing import Literal, TypedDict

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "AgentMemory",
    "CharacterConfig",
    "DMConfig",
    "GameConfig",
    "GameState",
    "create_agent_memory",
    "create_initial_game_state",
    "populate_game_state",
]

# Supported LLM providers (used by both CharacterConfig and DMConfig)
_SUPPORTED_PROVIDERS = frozenset(["gemini", "claude", "ollama"])


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
        summarizer_model: Model used for memory compression.
        party_size: Number of player characters in the party.
    """

    combat_mode: Literal["Narrative", "Tactical"] = Field(
        default="Narrative",
        description="Combat handling mode",
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


def create_agent_memory(token_limit: int = 8000) -> AgentMemory:
    """Factory function to create a new AgentMemory instance.

    Args:
        token_limit: Maximum tokens for this agent's context window.

    Returns:
        A new AgentMemory with empty summary and buffer.
    """
    return AgentMemory(token_limit=token_limit)


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
    )


def populate_game_state() -> GameState:
    """Factory function to create a fully populated game state from config files.

    Loads character configs from YAML files in config/characters/, builds the
    turn queue with DM first followed by PC agents, and initializes agent
    memories with appropriate token limits.

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
    agent_memories: dict[str, AgentMemory] = {}
    agent_memories["dm"] = AgentMemory(token_limit=dm_config.token_limit)
    for char_name, char_config in characters.items():
        agent_memories[char_name] = AgentMemory(token_limit=char_config.token_limit)

    return GameState(
        ground_truth_log=[],
        turn_queue=turn_queue,
        current_turn="dm",
        agent_memories=agent_memories,
        game_config=GameConfig(),
        dm_config=dm_config,
        characters=characters,
        whisper_queue=[],
        human_active=False,
        controlled_character=None,
    )
