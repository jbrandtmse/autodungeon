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
    "NarrativeMessage",
    "MessageSegment",
    "SessionMetadata",
    "create_agent_memory",
    "create_initial_game_state",
    "populate_game_state",
    "parse_log_entry",
    "parse_message_content",
]

# Supported LLM providers (used by both CharacterConfig and DMConfig)
_SUPPORTED_PROVIDERS = frozenset(["gemini", "claude", "ollama"])

# Module-level compiled regex patterns for message parsing
# Pattern allows spaces in agent names (e.g., "brother aldric")
LOG_ENTRY_PATTERN = re.compile(r"^\[([^\]]+)\]\s*(.*)$")
ACTION_PATTERN = re.compile(r"\*([^*]+)\*")


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
    def message_type(self) -> Literal["dm_narration", "pc_dialogue"]:
        """Determine message type based on agent name.

        Returns:
            "dm_narration" if agent is "dm", otherwise "pc_dialogue"
        """
        return "dm_narration" if self.agent == "dm" else "pc_dialogue"


def parse_log_entry(entry: str) -> NarrativeMessage:
    """Parse a ground_truth_log entry into a NarrativeMessage.

    Entry format: "[agent_name] message content"

    Handles edge cases:
    - Entry without brackets → treat as DM narration
    - Empty agent `[]` → use fallback "unknown"
    - Only parses first [agent] at start of string

    Args:
        entry: A raw log entry string

    Returns:
        NarrativeMessage with agent and content extracted
    """
    match = LOG_ENTRY_PATTERN.match(entry)
    if match:
        agent = match.group(1) or "unknown"
        content = match.group(2)
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
        session_number=1,
        session_id="001",
    )


def populate_game_state(include_sample_messages: bool = True) -> GameState:
    """Factory function to create a fully populated game state from config files.

    Loads character configs from YAML files in config/characters/, builds the
    turn queue with DM first followed by PC agents, and initializes agent
    memories with appropriate token limits.

    Args:
        include_sample_messages: If True, includes sample messages in ground_truth_log
            to demonstrate message styling. Set to False for clean game starts.

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
