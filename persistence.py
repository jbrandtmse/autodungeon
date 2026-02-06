"""Checkpoint save/load and transcript export.

This module implements checkpoint persistence for game state recovery:
- Atomic writes for crash safety (temp file + rename pattern)
- Full GameState serialization including nested Pydantic models
- Checkpoint listing and retrieval utilities
- Checkpoint metadata extraction for browser UI

Checkpoint format: campaigns/session_XXX/turn_XXX.json
Each checkpoint is self-contained (no delta encoding).
"""

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from models import (
    AgentMemory,
    AgentSecrets,
    CharacterConfig,
    CharacterSheet,
    DMConfig,
    GameConfig,
    GameState,
    ModuleInfo,
    SessionMetadata,
    TranscriptEntry,
    Whisper,
)

__all__ = [
    "CAMPAIGNS_DIR",
    "CheckpointInfo",
    "append_transcript_entry",
    "create_new_session",
    "delete_session",
    "deserialize_game_state",
    "ensure_session_dir",
    "format_session_id",
    "generate_recap_summary",
    "get_checkpoint_info",
    "get_checkpoint_path",
    "get_checkpoint_preview",
    "get_latest_checkpoint",
    "get_next_session_number",
    "get_session_dir",
    "get_transcript_download_data",
    "get_transcript_path",
    "initialize_session_with_previous_memories",
    "list_checkpoint_info",
    "list_checkpoints",
    "list_sessions",
    "list_sessions_with_metadata",
    "load_checkpoint",
    "load_session_metadata",
    "load_transcript",
    "save_checkpoint",
    "save_session_metadata",
    "serialize_game_state",
]

# Base directory for all campaigns
CAMPAIGNS_DIR = Path(__file__).parent / "campaigns"


def _validate_session_id(session_id: str) -> None:
    """Validate session_id to prevent path traversal attacks.

    Args:
        session_id: Session ID string to validate.

    Raises:
        ValueError: If session_id contains invalid characters.
    """
    if not session_id or not session_id.replace("_", "").isalnum():
        raise ValueError(
            f"Invalid session_id: {session_id!r}. "
            "Must be alphanumeric (underscores allowed)."
        )


def _validate_turn_number(turn_number: int) -> None:
    """Validate turn_number to prevent invalid file operations.

    Args:
        turn_number: Turn number to validate.

    Raises:
        ValueError: If turn_number is not a positive integer.
    """
    # Runtime check needed since Python doesn't enforce type hints
    if not isinstance(turn_number, int) or turn_number < 0:  # type: ignore[redundant-expr]
        raise ValueError(
            f"Invalid turn_number: {turn_number!r}. Must be a non-negative integer."
        )


def format_session_id(session_number: int) -> str:
    """Format session number to padded string ID.

    Args:
        session_number: Session number (e.g., 1, 42).

    Returns:
        Zero-padded session ID (e.g., "001", "042").

    Raises:
        ValueError: If session_number is not a positive integer.
    """
    # Runtime check needed since Python doesn't enforce type hints
    if not isinstance(session_number, int) or session_number < 0:  # type: ignore[redundant-expr]
        raise ValueError(
            f"Invalid session_number: {session_number!r}. "
            "Must be a non-negative integer."
        )
    return f"{session_number:03d}"


def get_session_dir(session_id: str) -> Path:
    """Get path to session directory.

    Args:
        session_id: Session ID string (e.g., "001").

    Returns:
        Path to session directory.

    Raises:
        ValueError: If session_id contains invalid characters.
    """
    _validate_session_id(session_id)
    return CAMPAIGNS_DIR / f"session_{session_id}"


def get_checkpoint_path(session_id: str, turn_number: int) -> Path:
    """Get path to checkpoint file.

    Args:
        session_id: Session ID string.
        turn_number: Turn number (1-indexed).

    Returns:
        Path to checkpoint JSON file.

    Raises:
        ValueError: If session_id or turn_number are invalid.
    """
    _validate_session_id(session_id)
    _validate_turn_number(turn_number)
    return get_session_dir(session_id) / f"turn_{turn_number:03d}.json"


def ensure_session_dir(session_id: str) -> Path:
    """Ensure session directory exists, create if needed.

    Args:
        session_id: Session ID string.

    Returns:
        Path to session directory.
    """
    session_dir = get_session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def serialize_game_state(state: GameState) -> str:
    """Serialize GameState to JSON string.

    Handles the TypedDict + Pydantic hybrid by converting
    Pydantic models to dicts before JSON serialization.

    Args:
        state: The GameState to serialize.

    Returns:
        JSON string representation of the state.
    """
    # Handle selected_module serialization (Story 7.3)
    selected_module = state.get("selected_module")
    selected_module_data = (
        selected_module.model_dump() if selected_module is not None else None
    )

    # Convert Pydantic models to dicts
    serializable: dict[str, Any] = {
        "ground_truth_log": state["ground_truth_log"],
        "turn_queue": state["turn_queue"],
        "current_turn": state["current_turn"],
        "agent_memories": {
            k: v.model_dump() for k, v in state["agent_memories"].items()
        },
        "game_config": state["game_config"].model_dump(),
        "dm_config": state["dm_config"].model_dump(),
        "characters": {k: v.model_dump() for k, v in state["characters"].items()},
        "whisper_queue": state["whisper_queue"],
        "human_active": state["human_active"],
        "controlled_character": state["controlled_character"],
        "session_number": state["session_number"],
        "session_id": state.get("session_id", "001"),
        "summarization_in_progress": state.get("summarization_in_progress", False),
        "selected_module": selected_module_data,
        # Story 8.3: Character sheets persistence
        "character_sheets": {
            k: v.model_dump() for k, v in state.get("character_sheets", {}).items()
        },
        # Story 10.1: Agent secrets persistence
        "agent_secrets": {
            k: v.model_dump() for k, v in state.get("agent_secrets", {}).items()
        },
    }
    return json.dumps(serializable, indent=2)


def deserialize_game_state(json_str: str) -> GameState:
    """Deserialize JSON string to GameState.

    Reconstructs Pydantic models from their dict representations.

    Args:
        json_str: JSON string representation of GameState.

    Returns:
        Reconstructed GameState.

    Raises:
        json.JSONDecodeError: If JSON is invalid.
        KeyError: If required fields are missing.
        TypeError: If field types are invalid.
        ValidationError: If Pydantic model validation fails.
    """
    data = json.loads(json_str)

    # Handle selected_module deserialization (Story 7.3)
    # Backward compatible: old checkpoints may not have this field
    selected_module_data = data.get("selected_module")
    selected_module = (
        ModuleInfo(**selected_module_data) if selected_module_data is not None else None
    )

    # Handle character_sheets deserialization (Story 8.3)
    # Backward compatible: old checkpoints may not have this field
    character_sheets_data = data.get("character_sheets", {})
    character_sheets = {
        k: CharacterSheet(**v) for k, v in character_sheets_data.items()
    }

    # Handle agent_secrets deserialization (Story 10.1)
    # Backward compatible: old checkpoints may not have this field
    agent_secrets_data = data.get("agent_secrets", {})
    agent_secrets: dict[str, AgentSecrets] = {}
    for agent_name, secrets_data in agent_secrets_data.items():
        # Reconstruct whispers list with Whisper objects
        whispers = [Whisper(**w) for w in secrets_data.get("whispers", [])]
        agent_secrets[agent_name] = AgentSecrets(whispers=whispers)

    return GameState(
        ground_truth_log=data["ground_truth_log"],
        turn_queue=data["turn_queue"],
        current_turn=data["current_turn"],
        agent_memories={k: AgentMemory(**v) for k, v in data["agent_memories"].items()},
        game_config=GameConfig(**data["game_config"]),
        dm_config=DMConfig(**data["dm_config"]),
        characters={k: CharacterConfig(**v) for k, v in data["characters"].items()},
        whisper_queue=data["whisper_queue"],
        human_active=data["human_active"],
        controlled_character=data["controlled_character"],
        session_number=data["session_number"],
        session_id=data.get("session_id", "001"),
        summarization_in_progress=data.get("summarization_in_progress", False),
        selected_module=selected_module,
        character_sheets=character_sheets,
        agent_secrets=agent_secrets,
    )


def save_checkpoint(
    state: GameState, session_id: str, turn_number: int, update_metadata: bool = True
) -> Path:
    """Save game state checkpoint to disk.

    Uses atomic write pattern: write to temp file first, then rename.
    This ensures checkpoint is either complete or doesn't exist,
    protecting against corruption from unexpected shutdown.

    Also updates session metadata (config.yaml) with turn count and timestamp
    unless update_metadata is False (Story 4.3).

    Args:
        state: Current game state to save.
        session_id: Session ID string.
        turn_number: Turn number for this checkpoint.
        update_metadata: Whether to update session metadata (default True).

    Returns:
        Path where checkpoint was saved.

    Raises:
        OSError: If write fails (permissions, disk full, etc.).
    """
    # Ensure session directory exists
    session_dir = ensure_session_dir(session_id)
    checkpoint_path = get_checkpoint_path(session_id, turn_number)

    # Serialize state
    json_content = serialize_game_state(state)

    # Atomic write: temp file then rename
    # This protects against partial writes during crash
    temp_fd, temp_path = tempfile.mkstemp(dir=session_dir, suffix=".json.tmp")
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            f.write(json_content)
        # Atomic rename (on POSIX; Windows uses copy+delete if needed)
        Path(temp_path).replace(checkpoint_path)
    except Exception:
        # Clean up temp file on error
        Path(temp_path).unlink(missing_ok=True)
        raise

    # Update session metadata (Story 4.3)
    if update_metadata:
        # Extract character names from state
        characters = state.get("characters", {})
        character_names = [
            config.name for key, config in characters.items() if key != "dm"
        ]
        update_session_metadata_on_checkpoint(session_id, turn_number, character_names)

    return checkpoint_path


def load_checkpoint(session_id: str, turn_number: int) -> GameState | None:
    """Load game state from checkpoint file.

    Args:
        session_id: Session ID string.
        turn_number: Turn number to load.

    Returns:
        Loaded GameState, or None if checkpoint doesn't exist or is invalid.
    """
    checkpoint_path = get_checkpoint_path(session_id, turn_number)

    if not checkpoint_path.exists():
        return None

    try:
        json_content = checkpoint_path.read_text(encoding="utf-8")
        return deserialize_game_state(json_content)
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError, ValidationError):
        # Invalid checkpoint - return None instead of crashing
        # AttributeError handles cases where JSON is null or array instead of object
        return None


def list_sessions() -> list[str]:
    """List all available session IDs.

    Returns:
        List of session ID strings, sorted.
    """
    if not CAMPAIGNS_DIR.exists():
        return []

    sessions: list[str] = []
    for path in CAMPAIGNS_DIR.iterdir():
        if path.is_dir() and path.name.startswith("session_"):
            session_id = path.name.replace("session_", "")
            sessions.append(session_id)

    return sorted(sessions)


def list_checkpoints(session_id: str) -> list[int]:
    """List all checkpoint turn numbers for a session.

    Args:
        session_id: Session ID string.

    Returns:
        List of turn numbers, sorted ascending.
    """
    session_dir = get_session_dir(session_id)

    if not session_dir.exists():
        return []

    turns: list[int] = []
    for path in session_dir.glob("turn_*.json"):
        # Extract turn number from filename
        try:
            turn_str = path.stem.replace("turn_", "")
            turn_num = int(turn_str)
            turns.append(turn_num)
        except ValueError:
            continue

    return sorted(turns)


def get_latest_checkpoint(session_id: str) -> int | None:
    """Get the most recent checkpoint turn number.

    Args:
        session_id: Session ID string.

    Returns:
        Latest turn number, or None if no checkpoints.
    """
    turns = list_checkpoints(session_id)
    return turns[-1] if turns else None


# =============================================================================
# Checkpoint Metadata (Story 4.2)
# =============================================================================


class CheckpointInfo(BaseModel):
    """Metadata about a checkpoint for display in the browser.

    Provides lightweight checkpoint information without loading the full
    GameState, suitable for displaying in the checkpoint browser UI.

    Attributes:
        turn_number: The turn number for this checkpoint.
        timestamp: When the checkpoint was saved (human-readable format).
        brief_context: First 100 chars of the last log entry for preview.
        message_count: Number of messages in ground_truth_log.
    """

    turn_number: int = Field(..., ge=0)
    timestamp: str = Field(...)
    brief_context: str = Field(default="")
    message_count: int = Field(default=0, ge=0)


def get_checkpoint_info(session_id: str, turn_number: int) -> CheckpointInfo | None:
    """Get metadata for a specific checkpoint.

    Extracts metadata without loading the full GameState for efficiency.
    Uses file mtime for timestamp since it's not stored in the checkpoint.

    Args:
        session_id: Session ID string.
        turn_number: Turn number to get info for.

    Returns:
        CheckpointInfo with metadata, or None if checkpoint doesn't exist.
    """
    checkpoint_path = get_checkpoint_path(session_id, turn_number)

    if not checkpoint_path.exists():
        return None

    try:
        # Get file modification time for timestamp
        mtime = checkpoint_path.stat().st_mtime
        timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

        # Load just enough to get context
        json_content = checkpoint_path.read_text(encoding="utf-8")
        data = json.loads(json_content)

        log = data.get("ground_truth_log", [])
        message_count = len(log)

        # Get brief context from last log entry
        brief_context = ""
        if log:
            last_entry = log[-1]
            # Remove agent prefix [agent] if present
            if last_entry.startswith("["):
                bracket_end = last_entry.find("]")
                if bracket_end > 0:
                    last_entry = last_entry[bracket_end + 1 :].strip()
            # Truncate to 100 chars with ellipsis if needed
            if len(last_entry) > 100:
                brief_context = last_entry[:100] + "..."
            else:
                brief_context = last_entry

        return CheckpointInfo(
            turn_number=turn_number,
            timestamp=timestamp,
            brief_context=brief_context,
            message_count=message_count,
        )
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def list_checkpoint_info(session_id: str) -> list[CheckpointInfo]:
    """List all checkpoints with metadata for a session.

    Args:
        session_id: Session ID string.

    Returns:
        List of CheckpointInfo, sorted by turn number descending (newest first).
    """
    turn_numbers = list_checkpoints(session_id)

    infos: list[CheckpointInfo] = []
    for turn in turn_numbers:
        info = get_checkpoint_info(session_id, turn)
        if info:
            infos.append(info)

    # Sort descending (newest first) for display
    return sorted(infos, key=lambda x: x.turn_number, reverse=True)


def get_checkpoint_preview(
    session_id: str, turn_number: int, num_messages: int = 5
) -> list[str] | None:
    """Get the last N log entries from a checkpoint for preview.

    Args:
        session_id: Session ID string.
        turn_number: Turn number to preview.
        num_messages: Number of recent messages to return (default 5).

    Returns:
        List of log entries (most recent last), or None if checkpoint doesn't exist.
    """
    state = load_checkpoint(session_id, turn_number)
    if state is None:
        return None

    log = state.get("ground_truth_log", [])
    return log[-num_messages:] if log else []


# =============================================================================
# Session Metadata (Story 4.3)
# =============================================================================


def get_session_config_path(session_id: str) -> Path:
    """Get path to session config.yaml file.

    Args:
        session_id: Session ID string.

    Returns:
        Path to config.yaml file in session directory.
    """
    return get_session_dir(session_id) / "config.yaml"


def save_session_metadata(session_id: str, metadata: SessionMetadata) -> Path:
    """Save session metadata to config.yaml.

    Args:
        session_id: Session ID string.
        metadata: SessionMetadata object to save.

    Returns:
        Path where config was saved.
    """
    ensure_session_dir(session_id)
    config_path = get_session_config_path(session_id)

    # Convert Pydantic model to dict for YAML serialization
    data = metadata.model_dump()

    # Use safe_dump for security
    yaml_content = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)

    # Atomic write pattern
    temp_path = config_path.with_suffix(".yaml.tmp")
    try:
        temp_path.write_text(yaml_content, encoding="utf-8")
        temp_path.replace(config_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return config_path


def load_session_metadata(session_id: str) -> SessionMetadata | None:
    """Load session metadata from config.yaml.

    Args:
        session_id: Session ID string.

    Returns:
        SessionMetadata object, or None if config doesn't exist or is invalid.
    """
    config_path = get_session_config_path(session_id)

    if not config_path.exists():
        return None

    try:
        yaml_content = config_path.read_text(encoding="utf-8")
        data = yaml.safe_load(yaml_content)
        return SessionMetadata(**data)
    except (yaml.YAMLError, TypeError, ValidationError):
        # Invalid config - return None instead of crashing
        return None


def list_sessions_with_metadata() -> list[SessionMetadata]:
    """List all sessions with their metadata.

    Returns sessions sorted by updated_at (most recently played first).
    Sessions without valid config.yaml are skipped.
    Sessions where metadata.session_id doesn't match directory are skipped
    (security: prevents crafted config.yaml from claiming wrong session).

    Returns:
        List of SessionMetadata objects sorted by recency.
    """
    session_ids = list_sessions()
    sessions: list[SessionMetadata] = []

    for session_id in session_ids:
        metadata = load_session_metadata(session_id)
        if metadata:
            # Security: verify metadata.session_id matches directory name
            # Prevents crafted config.yaml from claiming wrong session
            if metadata.session_id == session_id:
                sessions.append(metadata)

    # Sort by updated_at descending (most recent first)
    return sorted(sessions, key=lambda x: x.updated_at, reverse=True)


def get_next_session_number() -> int:
    """Get the next available session number.

    Returns:
        Next session number (1 if no sessions exist).
    """
    session_ids = list_sessions()

    if not session_ids:
        return 1

    # Parse session IDs to numbers and find max
    max_num = 0
    for session_id in session_ids:
        try:
            num = int(session_id)
            if num > max_num:
                max_num = num
        except ValueError:
            continue

    return max_num + 1


def create_new_session(
    session_number: int | None = None,
    name: str = "",
    character_names: list[str] | None = None,
) -> str:
    """Create a new session with directory and config.yaml.

    Args:
        session_number: Session number (auto-incremented if None).
        name: Optional user-friendly session name.
        character_names: List of character names for display.

    Returns:
        Session ID string (e.g., "001").
    """
    if session_number is None:
        session_number = get_next_session_number()

    session_id = format_session_id(session_number)

    # Create session directory
    ensure_session_dir(session_id)

    # Create session metadata
    now = datetime.now(UTC).isoformat() + "Z"
    metadata = SessionMetadata(
        session_id=session_id,
        session_number=session_number,
        name=name,
        created_at=now,
        updated_at=now,
        character_names=character_names or [],
        turn_count=0,
    )

    # Save config.yaml
    save_session_metadata(session_id, metadata)

    return session_id


def delete_session(session_id: str) -> bool:
    """Delete a session and all its files.

    Removes the entire session directory including checkpoints,
    transcript, and metadata.

    Args:
        session_id: Session ID string (e.g., "001").

    Returns:
        True if session was deleted, False if it didn't exist.

    Raises:
        ValueError: If session_id contains invalid characters.
        OSError: If deletion fails (permissions, etc.).
    """
    import shutil

    _validate_session_id(session_id)
    session_dir = get_session_dir(session_id)

    if not session_dir.exists():
        return False

    # Remove the entire session directory
    shutil.rmtree(session_dir)
    return True


def update_session_metadata_on_checkpoint(
    session_id: str, turn_count: int, character_names: list[str] | None = None
) -> None:
    """Update session metadata when a checkpoint is saved.

    Args:
        session_id: Session ID string.
        turn_count: Current turn count.
        character_names: Optional list of character names to update.
    """
    metadata = load_session_metadata(session_id)

    if metadata is None:
        # Create new metadata if missing
        try:
            session_number = int(session_id)
        except ValueError:
            session_number = 1

        now = datetime.now(UTC).isoformat() + "Z"
        metadata = SessionMetadata(
            session_id=session_id,
            session_number=session_number,
            name="",
            created_at=now,
            updated_at=now,
            character_names=character_names or [],
            turn_count=turn_count,
        )
    else:
        # Update existing metadata
        metadata.updated_at = datetime.now(UTC).isoformat() + "Z"
        metadata.turn_count = turn_count
        if character_names:
            metadata.character_names = character_names

    save_session_metadata(session_id, metadata)


def generate_recap_summary(
    session_id: str, num_turns: int = 5, include_cross_session: bool = False
) -> str | None:
    """Generate a "While you were away" summary from recent turns.

    Story 5.4: Cross-Session Memory & Character Facts - Enhanced to include
    cross-session context when continuing a previous session.

    Args:
        session_id: Session ID string.
        num_turns: Number of recent turns to summarize.
        include_cross_session: If True, include long_term_summary and
            character relationships from agent memories.

    Returns:
        Recap summary string, or None if no checkpoints exist.
    """
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is None:
        return None

    state = load_checkpoint(session_id, latest_turn)
    if state is None:
        return None

    recap_sections: list[str] = []

    # Include cross-session context if requested (Story 5.4)
    if include_cross_session:
        agent_memories = state.get("agent_memories", {})

        # Add DM's story summary if available
        dm_memory = agent_memories.get("dm")
        if dm_memory and dm_memory.long_term_summary:
            recap_sections.append(
                f"**Story So Far:**\n{dm_memory.long_term_summary[:300]}"
            )

        # Add key relationships from character facts
        relationships_parts: list[str] = []
        for agent_name, memory in agent_memories.items():
            if agent_name == "dm":
                continue
            if memory.character_facts and memory.character_facts.relationships:
                for name, desc in memory.character_facts.relationships.items():
                    relationships_parts.append(f"- {name}: {desc}")

        if relationships_parts:
            recap_sections.append(
                "**Key Relationships:**\n" + "\n".join(relationships_parts[:5])
            )

    log = state.get("ground_truth_log", [])
    if not log and not recap_sections:
        return None

    # Get last N entries from ground truth log
    if log:
        recent_entries = log[-num_turns:] if len(log) >= num_turns else log

        # Format recap entries (CSS provides bullet styling via .recap-item)
        summary_lines: list[str] = []
        for entry in recent_entries:
            # Strip agent prefix for cleaner display
            if entry.startswith("["):
                bracket_end = entry.find("]")
                if bracket_end > 0:
                    content = entry[bracket_end + 1 :]
                    # Strip leading colon and whitespace (format is "[agent]: content")
                    content = content.lstrip(": ").strip()
                    # Handle duplicate prefix: LLM sometimes echoes "[agent]:" in response
                    if content.startswith("["):
                        inner_bracket_end = content.find("]")
                        if inner_bracket_end > 0:
                            content = (
                                content[inner_bracket_end + 1 :].lstrip(": ").strip()
                            )
                else:
                    content = entry
            else:
                content = entry

            # Skip empty entries (from empty LLM responses)
            if not content:
                continue

            # Truncate long entries
            if len(content) > 150:
                content = content[:147] + "..."

            summary_lines.append(content)

        if summary_lines:
            recap_sections.append("**Recent Events:**\n" + "\n".join(summary_lines))

    return "\n\n".join(recap_sections) if recap_sections else None


# =============================================================================
# Cross-Session Memory Initialization (Story 5.4)
# =============================================================================


def initialize_session_with_previous_memories(
    previous_session_id: str,
    new_session_id: str,
    new_state: GameState,
) -> GameState:
    """Initialize a new session carrying over memories from a previous session.

    This function copies long_term_summary and character_facts from the previous
    session's agent memories to the new session, while keeping short_term_buffer
    empty for a fresh start.

    Story 5.4: Cross-Session Memory & Character Facts.

    Args:
        previous_session_id: Session ID to load memories from.
        new_session_id: New session ID (for logging/context).
        new_state: The new GameState to initialize.

    Returns:
        The new_state with memories carried over from previous session.
        If previous session doesn't exist, returns new_state unchanged.
    """
    # Try to load the latest checkpoint from previous session
    latest_turn = get_latest_checkpoint(previous_session_id)
    if latest_turn is None:
        return new_state

    prev_state = load_checkpoint(previous_session_id, latest_turn)
    if prev_state is None:
        return new_state

    prev_memories = prev_state.get("agent_memories", {})
    new_memories = new_state.get("agent_memories", {})

    # Copy long_term_summary and character_facts from previous session
    # while preserving token_limit from new state
    for agent_name, new_memory in new_memories.items():
        if agent_name in prev_memories:
            prev_memory = prev_memories[agent_name]

            # Build new memory with:
            # - long_term_summary from previous session
            # - character_facts from previous session
            # - token_limit from new session (may have changed)
            # - empty short_term_buffer (fresh start)
            new_memories[agent_name] = AgentMemory(
                long_term_summary=prev_memory.long_term_summary,
                short_term_buffer=[],  # Fresh start for new session
                token_limit=new_memory.token_limit,
                character_facts=prev_memory.character_facts,
            )

    return new_state


# =============================================================================
# Transcript Export (Story 4.4)
# =============================================================================


def get_transcript_path(session_id: str) -> Path:
    """Get path to session transcript.json file.

    Args:
        session_id: Session ID string.

    Returns:
        Path to transcript.json file in session directory.

    Raises:
        ValueError: If session_id contains invalid characters.
    """
    _validate_session_id(session_id)
    return get_session_dir(session_id) / "transcript.json"


def append_transcript_entry(session_id: str, entry: TranscriptEntry) -> None:
    """Append entry to transcript.json using atomic write pattern.

    The transcript is an append-only JSON array. We:
    1. Load existing entries (or empty list if new)
    2. Append the new entry
    3. Write atomically via temp file + rename

    This is simpler than true append (which would require JSONL format)
    while maintaining JSON array structure for easy parsing.

    Args:
        session_id: Session ID string.
        entry: TranscriptEntry to append.

    Raises:
        OSError: If write fails (permissions, disk full, etc.).
    """
    # Ensure session directory exists
    ensure_session_dir(session_id)
    transcript_path = get_transcript_path(session_id)

    # Load existing entries
    entries: list[dict[str, object]] = []
    if transcript_path.exists():
        try:
            content = transcript_path.read_text(encoding="utf-8")
            loaded = json.loads(content)
            if isinstance(loaded, list):
                entries = loaded
            # else: corrupted file (not a list), start fresh
        except (json.JSONDecodeError, OSError):
            # Corrupted file - start fresh but log warning (handled gracefully)
            entries = []

    # Append new entry
    entries.append(entry.model_dump())

    # Atomic write via temp file + rename
    temp_path = transcript_path.with_suffix(".json.tmp")
    try:
        temp_path.write_text(
            json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temp_path.replace(transcript_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def load_transcript(session_id: str) -> list[TranscriptEntry] | None:
    """Load transcript entries from transcript.json.

    Args:
        session_id: Session ID string.

    Returns:
        List of TranscriptEntry objects, or None if transcript doesn't exist.
        Returns empty list if transcript file exists but is empty or corrupted.
    """
    transcript_path = get_transcript_path(session_id)

    if not transcript_path.exists():
        return None

    try:
        content = transcript_path.read_text(encoding="utf-8")
        data = json.loads(content)

        if not isinstance(data, list):
            # Corrupted: not a list - return empty list
            return []

        entries: list[TranscriptEntry] = []
        for item in data:
            try:
                entries.append(TranscriptEntry(**item))
            except (TypeError, ValidationError):
                # Skip invalid entries (graceful handling of corrupted data)
                continue

        return entries
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        # File exists but unreadable/corrupted - return empty list
        return []


def get_transcript_download_data(session_id: str) -> str | None:
    """Generate formatted JSON string for transcript download.

    Args:
        session_id: Session ID string.

    Returns:
        Pretty-printed JSON string for download, or None if no transcript exists.
    """
    transcript_path = get_transcript_path(session_id)

    if not transcript_path.exists():
        return None

    try:
        content = transcript_path.read_text(encoding="utf-8")
        data = json.loads(content)

        if not isinstance(data, list):
            return None

        if not data:
            # Empty transcript - return empty array
            return "[]"

        # Pretty-print for readability
        return json.dumps(data, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, OSError):
        return None
