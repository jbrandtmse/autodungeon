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
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from models import (
    AgentMemory,
    CharacterConfig,
    DMConfig,
    GameConfig,
    GameState,
)

__all__ = [
    "CAMPAIGNS_DIR",
    "CheckpointInfo",
    "deserialize_game_state",
    "ensure_session_dir",
    "format_session_id",
    "get_checkpoint_info",
    "get_checkpoint_path",
    "get_checkpoint_preview",
    "get_latest_checkpoint",
    "get_session_dir",
    "list_checkpoint_info",
    "list_checkpoints",
    "list_sessions",
    "load_checkpoint",
    "save_checkpoint",
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
            f"Invalid turn_number: {turn_number!r}. "
            "Must be a non-negative integer."
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

    return GameState(
        ground_truth_log=data["ground_truth_log"],
        turn_queue=data["turn_queue"],
        current_turn=data["current_turn"],
        agent_memories={
            k: AgentMemory(**v) for k, v in data["agent_memories"].items()
        },
        game_config=GameConfig(**data["game_config"]),
        dm_config=DMConfig(**data["dm_config"]),
        characters={k: CharacterConfig(**v) for k, v in data["characters"].items()},
        whisper_queue=data["whisper_queue"],
        human_active=data["human_active"],
        controlled_character=data["controlled_character"],
        session_number=data["session_number"],
        session_id=data.get("session_id", "001"),
    )


def save_checkpoint(state: GameState, session_id: str, turn_number: int) -> Path:
    """Save game state checkpoint to disk.

    Uses atomic write pattern: write to temp file first, then rename.
    This ensures checkpoint is either complete or doesn't exist,
    protecting against corruption from unexpected shutdown.

    Args:
        state: Current game state to save.
        session_id: Session ID string.
        turn_number: Turn number for this checkpoint.

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
    except (json.JSONDecodeError, KeyError, TypeError, ValidationError):
        # Invalid checkpoint - return None instead of crashing
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
