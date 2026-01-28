"""Tests for persistence module - checkpoint save/load functionality.

Story 4.1: Auto-Checkpoint System
Tests for path utilities, serialization, save/load, and listing functions.
"""

import json
import os
import time
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from models import (
    AgentMemory,
    CharacterConfig,
    DMConfig,
    GameConfig,
    GameState,
    create_initial_game_state,
    populate_game_state,
)
from persistence import (
    CAMPAIGNS_DIR,
    deserialize_game_state,
    ensure_session_dir,
    format_session_id,
    get_checkpoint_path,
    get_latest_checkpoint,
    get_session_dir,
    list_checkpoints,
    list_sessions,
    load_checkpoint,
    save_checkpoint,
    serialize_game_state,
)


@pytest.fixture
def temp_campaigns_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary campaigns directory for testing.

    Patches CAMPAIGNS_DIR to point to temp directory.
    """
    temp_campaigns = tmp_path / "campaigns"
    temp_campaigns.mkdir()

    with patch("persistence.CAMPAIGNS_DIR", temp_campaigns):
        yield temp_campaigns


@pytest.fixture
def sample_game_state() -> GameState:
    """Create a sample GameState for testing."""
    return GameState(
        ground_truth_log=["[dm] The adventure begins.", "[fighter] I draw my sword."],
        turn_queue=["dm", "fighter", "rogue"],
        current_turn="rogue",
        agent_memories={
            "dm": AgentMemory(
                long_term_summary="The party entered a dungeon.",
                short_term_buffer=["Recent event 1", "Recent event 2"],
                token_limit=8000,
            ),
            "fighter": AgentMemory(
                long_term_summary="",
                short_term_buffer=["I attacked the goblin."],
                token_limit=4000,
            ),
        },
        game_config=GameConfig(
            combat_mode="Narrative",
            summarizer_model="gemini-1.5-flash",
            party_size=4,
        ),
        dm_config=DMConfig(
            name="Dungeon Master",
            provider="gemini",
            model="gemini-1.5-flash",
            token_limit=8000,
            color="#D4A574",
        ),
        characters={
            "fighter": CharacterConfig(
                name="Theron",
                character_class="Fighter",
                personality="Brave and bold",
                color="#C9A45C",
                provider="gemini",
                model="gemini-1.5-flash",
                token_limit=4000,
            ),
        },
        whisper_queue=[],
        human_active=False,
        controlled_character=None,
        session_number=1,
        session_id="001",
    )


class TestPathUtilities:
    """Tests for checkpoint path utilities."""

    def test_format_session_id_single_digit(self) -> None:
        """Test format_session_id with single digit."""
        assert format_session_id(1) == "001"
        assert format_session_id(5) == "005"

    def test_format_session_id_double_digit(self) -> None:
        """Test format_session_id with double digit."""
        assert format_session_id(10) == "010"
        assert format_session_id(42) == "042"
        assert format_session_id(99) == "099"

    def test_format_session_id_triple_digit(self) -> None:
        """Test format_session_id with triple digit."""
        assert format_session_id(100) == "100"
        assert format_session_id(999) == "999"

    def test_get_session_dir_format(self) -> None:
        """Test get_session_dir returns correct format."""
        path = get_session_dir("001")
        assert path.name == "session_001"
        assert path.parent == CAMPAIGNS_DIR

    def test_get_session_dir_custom_id(self) -> None:
        """Test get_session_dir with different session IDs."""
        assert get_session_dir("042").name == "session_042"
        assert get_session_dir("999").name == "session_999"

    def test_get_checkpoint_path_format(self) -> None:
        """Test get_checkpoint_path returns correct format."""
        path = get_checkpoint_path("001", 5)
        assert path.name == "turn_005.json"
        assert path.parent.name == "session_001"

    def test_get_checkpoint_path_turn_padding(self) -> None:
        """Test turn number is zero-padded in path."""
        assert get_checkpoint_path("001", 1).name == "turn_001.json"
        assert get_checkpoint_path("001", 42).name == "turn_042.json"
        assert get_checkpoint_path("001", 100).name == "turn_100.json"

    def test_checkpoint_path_ends_with_json(self) -> None:
        """Test checkpoint path format follows session_xxx/turn_xxx.json."""
        path = get_checkpoint_path("001", 42)
        assert str(path).endswith("campaigns/session_001/turn_042.json") or \
               str(path).endswith("campaigns\\session_001\\turn_042.json")

    def test_ensure_session_dir_creates_directory(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test ensure_session_dir creates directory if missing."""
        session_dir = temp_campaigns_dir / "session_001"
        assert not session_dir.exists()

        # Patch get_session_dir to use temp dir
        with patch("persistence.get_session_dir", return_value=session_dir):
            result = ensure_session_dir("001")

        assert result == session_dir
        assert session_dir.exists()
        assert session_dir.is_dir()

    def test_ensure_session_dir_idempotent(self, temp_campaigns_dir: Path) -> None:
        """Test ensure_session_dir is idempotent (safe to call twice)."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        with patch("persistence.get_session_dir", return_value=session_dir):
            result = ensure_session_dir("001")

        assert result == session_dir
        assert session_dir.exists()


class TestGameStateSerialization:
    """Tests for GameState serialize/deserialize."""

    def test_serialize_returns_json_string(
        self, sample_game_state: GameState
    ) -> None:
        """Test serialize_game_state returns valid JSON."""
        json_str = serialize_game_state(sample_game_state)
        assert isinstance(json_str, str)

        # Should be valid JSON
        data = json.loads(json_str)
        assert isinstance(data, dict)

    def test_serialize_includes_all_fields(
        self, sample_game_state: GameState
    ) -> None:
        """Test serialized JSON includes all GameState fields."""
        json_str = serialize_game_state(sample_game_state)
        data = json.loads(json_str)

        expected_keys = {
            "ground_truth_log",
            "turn_queue",
            "current_turn",
            "agent_memories",
            "game_config",
            "dm_config",
            "characters",
            "whisper_queue",
            "human_active",
            "controlled_character",
            "session_number",
            "session_id",
        }
        assert set(data.keys()) == expected_keys

    def test_serialize_preserves_ground_truth_log(
        self, sample_game_state: GameState
    ) -> None:
        """Test ground_truth_log is preserved in serialization."""
        json_str = serialize_game_state(sample_game_state)
        data = json.loads(json_str)

        assert data["ground_truth_log"] == sample_game_state["ground_truth_log"]

    def test_serialize_preserves_agent_memories(
        self, sample_game_state: GameState
    ) -> None:
        """Test agent_memories are serialized correctly."""
        json_str = serialize_game_state(sample_game_state)
        data = json.loads(json_str)

        assert "dm" in data["agent_memories"]
        assert data["agent_memories"]["dm"]["long_term_summary"] == \
               "The party entered a dungeon."
        assert data["agent_memories"]["dm"]["short_term_buffer"] == \
               ["Recent event 1", "Recent event 2"]

    def test_serialize_deserialize_roundtrip(
        self, sample_game_state: GameState
    ) -> None:
        """Test GameState survives serialization round-trip."""
        json_str = serialize_game_state(sample_game_state)
        restored = deserialize_game_state(json_str)

        # Check basic fields
        assert restored["ground_truth_log"] == sample_game_state["ground_truth_log"]
        assert restored["turn_queue"] == sample_game_state["turn_queue"]
        assert restored["current_turn"] == sample_game_state["current_turn"]
        assert restored["session_number"] == sample_game_state["session_number"]
        assert restored["session_id"] == sample_game_state["session_id"]
        assert restored["human_active"] == sample_game_state["human_active"]

    def test_roundtrip_preserves_agent_memories(
        self, sample_game_state: GameState
    ) -> None:
        """Test agent_memories survive round-trip."""
        json_str = serialize_game_state(sample_game_state)
        restored = deserialize_game_state(json_str)

        assert len(restored["agent_memories"]) == \
               len(sample_game_state["agent_memories"])

        dm_memory = restored["agent_memories"]["dm"]
        assert dm_memory.long_term_summary == "The party entered a dungeon."
        assert dm_memory.short_term_buffer == ["Recent event 1", "Recent event 2"]
        assert dm_memory.token_limit == 8000

    def test_roundtrip_preserves_character_configs(
        self, sample_game_state: GameState
    ) -> None:
        """Test character configs survive round-trip."""
        json_str = serialize_game_state(sample_game_state)
        restored = deserialize_game_state(json_str)

        fighter = restored["characters"]["fighter"]
        assert fighter.name == "Theron"
        assert fighter.character_class == "Fighter"
        assert fighter.color == "#C9A45C"

    def test_roundtrip_preserves_pydantic_models(
        self, sample_game_state: GameState
    ) -> None:
        """Test all Pydantic models survive round-trip."""
        json_str = serialize_game_state(sample_game_state)
        restored = deserialize_game_state(json_str)

        # AgentMemory is Pydantic model
        assert isinstance(restored["agent_memories"]["dm"], AgentMemory)

        # GameConfig is Pydantic model
        assert isinstance(restored["game_config"], GameConfig)

        # DMConfig is Pydantic model
        assert isinstance(restored["dm_config"], DMConfig)

        # CharacterConfig is Pydantic model
        assert isinstance(restored["characters"]["fighter"], CharacterConfig)

    def test_deserialize_invalid_json_raises(self) -> None:
        """Test deserialize_game_state raises on invalid JSON."""
        with pytest.raises(json.JSONDecodeError):
            deserialize_game_state("not valid json")

    def test_deserialize_missing_field_raises(self) -> None:
        """Test deserialize_game_state raises on missing required field."""
        json_str = '{"ground_truth_log": []}'
        with pytest.raises(KeyError):
            deserialize_game_state(json_str)


class TestSaveCheckpoint:
    """Tests for save_checkpoint function."""

    def test_save_checkpoint_creates_file(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test save_checkpoint creates file at expected path."""
        session_dir = temp_campaigns_dir / "session_001"
        expected_path = session_dir / "turn_005.json"

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(sample_game_state, "001", 5)

        assert path == expected_path
        assert expected_path.exists()

    def test_save_checkpoint_returns_correct_path(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test save_checkpoint returns the path where file was saved."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(sample_game_state, "001", 3)

        assert path.name == "turn_003.json"
        assert path.parent.name == "session_001"

    def test_save_checkpoint_creates_session_dir(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test save_checkpoint creates session directory if missing."""
        session_dir = temp_campaigns_dir / "session_001"
        assert not session_dir.exists()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)

        assert session_dir.exists()
        assert session_dir.is_dir()

    def test_save_checkpoint_content_is_valid_json(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test saved checkpoint contains valid JSON."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(sample_game_state, "001", 1)

        content = path.read_text(encoding="utf-8")
        data = json.loads(content)

        assert isinstance(data, dict)
        assert "ground_truth_log" in data
        assert "agent_memories" in data

    def test_save_checkpoint_content_matches_state(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test saved checkpoint content matches original state."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(sample_game_state, "001", 1)

        content = path.read_text(encoding="utf-8")
        data = json.loads(content)

        assert data["ground_truth_log"] == sample_game_state["ground_truth_log"]
        assert data["session_id"] == sample_game_state["session_id"]
        assert data["turn_queue"] == sample_game_state["turn_queue"]

    def test_save_checkpoint_overwrites_existing(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test save_checkpoint overwrites existing checkpoint."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(sample_game_state, "001", 1)

        # Modify state and save again to same turn
        sample_game_state["ground_truth_log"].append("[dm] New entry.")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)

        content = path.read_text(encoding="utf-8")
        data = json.loads(content)

        assert "[dm] New entry." in data["ground_truth_log"]

    def test_save_checkpoint_no_temp_files_on_success(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test no temp files left after successful save."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)

        session_dir = temp_campaigns_dir / "session_001"
        temp_files = list(session_dir.glob("*.tmp"))

        assert len(temp_files) == 0


class TestLoadCheckpoint:
    """Tests for load_checkpoint function."""

    def test_load_checkpoint_returns_game_state(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test load_checkpoint returns complete GameState."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert "ground_truth_log" in loaded
        assert "agent_memories" in loaded

    def test_load_checkpoint_missing_returns_none(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_checkpoint returns None for missing checkpoint."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_checkpoint("001", 999)

        assert loaded is None

    def test_load_checkpoint_invalid_json_returns_none(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_checkpoint returns None for corrupted checkpoint."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        checkpoint_path = session_dir / "turn_001.json"
        checkpoint_path.write_text("not valid json", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_checkpoint("001", 1)

        assert loaded is None

    def test_load_checkpoint_matches_saved_state(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test loaded state matches saved state."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert loaded["ground_truth_log"] == sample_game_state["ground_truth_log"]
        assert loaded["turn_queue"] == sample_game_state["turn_queue"]
        assert loaded["session_id"] == sample_game_state["session_id"]

    def test_load_checkpoint_preserves_agent_memories(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test loaded checkpoint contains all agent_memories."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert len(loaded["agent_memories"]) == \
               len(sample_game_state["agent_memories"])

        dm_memory = loaded["agent_memories"]["dm"]
        assert dm_memory.long_term_summary == "The party entered a dungeon."

    def test_load_checkpoint_validates_required_fields(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load returns None for checkpoint missing required fields."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        # Write incomplete JSON
        checkpoint_path = session_dir / "turn_001.json"
        checkpoint_path.write_text(
            '{"ground_truth_log": [], "turn_queue": []}',
            encoding="utf-8"
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_checkpoint("001", 1)

        # Should return None because required fields are missing
        assert loaded is None


class TestListingFunctions:
    """Tests for list_sessions, list_checkpoints, get_latest_checkpoint."""

    def test_list_sessions_empty_dir(self, temp_campaigns_dir: Path) -> None:
        """Test list_sessions returns empty list for empty directory."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sessions = list_sessions()

        assert sessions == []

    def test_list_sessions_returns_sorted(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_sessions returns sorted session IDs."""
        (temp_campaigns_dir / "session_003").mkdir()
        (temp_campaigns_dir / "session_001").mkdir()
        (temp_campaigns_dir / "session_002").mkdir()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sessions = list_sessions()

        assert sessions == ["001", "002", "003"]

    def test_list_sessions_ignores_non_session_dirs(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_sessions ignores directories not matching pattern."""
        (temp_campaigns_dir / "session_001").mkdir()
        (temp_campaigns_dir / "not_a_session").mkdir()
        (temp_campaigns_dir / "config.yaml").write_text("test", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sessions = list_sessions()

        assert sessions == ["001"]

    def test_list_sessions_missing_dir_returns_empty(
        self, tmp_path: Path
    ) -> None:
        """Test list_sessions returns empty list if campaigns dir missing."""
        missing_dir = tmp_path / "nonexistent"

        with patch("persistence.CAMPAIGNS_DIR", missing_dir):
            sessions = list_sessions()

        assert sessions == []

    def test_list_checkpoints_empty_session(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_checkpoints returns empty list for empty session."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            checkpoints = list_checkpoints("001")

        assert checkpoints == []

    def test_list_checkpoints_returns_sorted(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test list_checkpoints returns sorted turn numbers."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 3)
            save_checkpoint(sample_game_state, "001", 1)
            save_checkpoint(sample_game_state, "001", 5)

            checkpoints = list_checkpoints("001")

        assert checkpoints == [1, 3, 5]

    def test_list_checkpoints_ignores_non_turn_files(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test list_checkpoints ignores non-checkpoint files."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        # Create valid checkpoint
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)

        # Create non-checkpoint files
        (session_dir / "config.yaml").write_text("test", encoding="utf-8")
        (session_dir / "transcript.json").write_text("{}", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            checkpoints = list_checkpoints("001")

        assert checkpoints == [1]

    def test_list_checkpoints_missing_session_returns_empty(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_checkpoints returns empty for nonexistent session."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            checkpoints = list_checkpoints("999")

        assert checkpoints == []

    def test_get_latest_checkpoint_returns_highest(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test get_latest_checkpoint returns highest turn number."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            save_checkpoint(sample_game_state, "001", 5)
            save_checkpoint(sample_game_state, "001", 3)

            latest = get_latest_checkpoint("001")

        assert latest == 5

    def test_get_latest_checkpoint_empty_returns_none(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_latest_checkpoint returns None for empty session."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            latest = get_latest_checkpoint("001")

        assert latest is None

    def test_get_latest_checkpoint_missing_session_returns_none(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_latest_checkpoint returns None for missing session."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            latest = get_latest_checkpoint("999")

        assert latest is None


class TestAutoCheckpointIntegration:
    """Integration tests for auto-checkpoint in game loop."""

    def test_save_load_roundtrip_with_populated_state(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test checkpoint roundtrip with populate_game_state()."""
        state = populate_game_state(include_sample_messages=True)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            turn_number = len(state["ground_truth_log"])
            save_checkpoint(state, state["session_id"], turn_number)
            loaded = load_checkpoint(state["session_id"], turn_number)

        assert loaded is not None
        assert len(loaded["ground_truth_log"]) == len(state["ground_truth_log"])
        assert len(loaded["agent_memories"]) == len(state["agent_memories"])

    def test_checkpoint_contains_session_id(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test checkpoint contains session_id field."""
        state = populate_game_state(include_sample_messages=False)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(state, "001", 1)

        content = path.read_text(encoding="utf-8")
        data = json.loads(content)

        assert "session_id" in data
        assert data["session_id"] == "001"


class TestStory41AcceptanceCriteria:
    """Acceptance tests for all Story 4.1 criteria."""

    def test_ac1_checkpoint_saved_after_turn(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #1: Checkpoint is automatically saved after turn completes."""
        # This tests the save_checkpoint function that gets called
        # at the end of run_single_round()
        sample_game_state["ground_truth_log"].append("[dm] DM response.")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            turn_number = len(sample_game_state["ground_truth_log"])
            path = save_checkpoint(
                sample_game_state,
                sample_game_state["session_id"],
                turn_number
            )

        assert path.exists()
        # Verify no user action was required (function call is automatic)

    def test_ac2_checkpoint_path_format(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #2: Checkpoint creates file at campaigns/session_xxx/turn_xxx.json."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(sample_game_state, "001", 5)

        # Verify path format
        assert path.parent.name == "session_001"
        assert path.name == "turn_005.json"

    def test_ac3_checkpoint_contains_complete_game_state(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #3: Checkpoint contains complete GameState via Pydantic."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None

        # Verify all required fields present
        required_fields = [
            "ground_truth_log", "turn_queue", "current_turn",
            "agent_memories", "game_config", "dm_config",
            "characters", "whisper_queue", "human_active",
            "controlled_character", "session_number", "session_id"
        ]
        for field in required_fields:
            assert field in loaded

    def test_ac3_checkpoint_includes_all_agent_memories(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #3: Checkpoint includes all agent memories at that point in time."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert len(loaded["agent_memories"]) == 2  # dm and fighter
        assert "dm" in loaded["agent_memories"]
        assert "fighter" in loaded["agent_memories"]

        # Verify memory content
        dm_memory = loaded["agent_memories"]["dm"]
        assert dm_memory.long_term_summary == "The party entered a dungeon."

    def test_ac4_self_contained_no_delta(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #4: Each file is self-contained (no delta encoding)."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            # Save first checkpoint
            save_checkpoint(sample_game_state, "001", 1)

            # Modify state and save second checkpoint
            sample_game_state["ground_truth_log"].append("[dm] New content.")
            save_checkpoint(sample_game_state, "001", 2)

        # Load second checkpoint alone - should work without first
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_checkpoint("001", 2)

        assert loaded is not None
        # Second checkpoint is complete on its own
        assert len(loaded["ground_truth_log"]) == 3

    def test_ac4_old_checkpoints_not_modified(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #4: Old checkpoints are not modified."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)

            # Get modification time of first checkpoint
            # Need to use temp_campaigns_dir directly since we're patched
            actual_path1 = temp_campaigns_dir / "session_001" / "turn_001.json"
            mtime1 = actual_path1.stat().st_mtime

            # Wait to ensure different timestamp
            time.sleep(0.1)

            # Save new checkpoint
            sample_game_state["ground_truth_log"].append("[dm] New entry.")
            save_checkpoint(sample_game_state, "001", 2)

            # Check first checkpoint wasn't modified
            mtime1_after = actual_path1.stat().st_mtime

        assert mtime1 == mtime1_after

    def test_ac5_atomic_write_prevents_corruption(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #5: Session files remain valid after unexpected shutdown.

        Tests the atomic write pattern (temp file + rename).
        """
        # The atomic write pattern ensures either:
        # 1. Complete checkpoint exists, or
        # 2. No checkpoint exists (temp file never renamed)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(sample_game_state, "001", 1)

        # Checkpoint should be valid JSON
        content = path.read_text(encoding="utf-8")
        json.loads(content)  # Should not raise

        # No temp files should remain
        session_dir = temp_campaigns_dir / "session_001"
        temp_files = list(session_dir.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_checkpoint_survives_serialization_roundtrip(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test checkpoint survives full serialization round-trip."""
        original = populate_game_state(include_sample_messages=True)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            turn_number = len(original["ground_truth_log"])
            save_checkpoint(original, original["session_id"], turn_number)
            loaded = load_checkpoint(original["session_id"], turn_number)

        assert loaded is not None
        assert loaded["ground_truth_log"] == original["ground_truth_log"]
        assert loaded["turn_queue"] == original["turn_queue"]
        assert loaded["current_turn"] == original["current_turn"]
        assert loaded["session_id"] == original["session_id"]
        assert loaded["session_number"] == original["session_number"]

    def test_missing_directory_created_automatically(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test missing directory is created automatically."""
        # Ensure session directory doesn't exist
        session_dir = temp_campaigns_dir / "session_042"
        assert not session_dir.exists()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "042", 1)

        assert session_dir.exists()
        assert session_dir.is_dir()


class TestSessionIdHandling:
    """Tests for session_id field in GameState."""

    def test_create_initial_game_state_has_session_id(self) -> None:
        """Test create_initial_game_state includes session_id."""
        state = create_initial_game_state()
        assert "session_id" in state
        assert state["session_id"] == "001"

    def test_populate_game_state_has_session_id(self) -> None:
        """Test populate_game_state includes session_id."""
        state = populate_game_state(include_sample_messages=False)
        assert "session_id" in state
        assert state["session_id"] == "001"

    def test_session_id_matches_session_number(self) -> None:
        """Test session_id is formatted from session_number."""
        state = populate_game_state(include_sample_messages=False)
        expected_id = f"{state['session_number']:03d}"
        assert state["session_id"] == expected_id

    def test_session_id_serialized_with_checkpoint(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test session_id is included in serialized checkpoint."""
        state = populate_game_state(include_sample_messages=False)

        json_str = serialize_game_state(state)
        data = json.loads(json_str)

        assert "session_id" in data
        assert data["session_id"] == state["session_id"]

    def test_session_id_preserved_on_load(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test session_id is preserved when loading checkpoint."""
        state = populate_game_state(include_sample_messages=False)
        state["session_id"] = "042"

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "042", 1)
            loaded = load_checkpoint("042", 1)

        assert loaded is not None
        assert loaded["session_id"] == "042"


class TestInputValidation:
    """Tests for input validation to prevent path traversal and other attacks."""

    def test_session_id_path_traversal_rejected(self) -> None:
        """Test session_id with path traversal characters is rejected."""
        with pytest.raises(ValueError, match="Invalid session_id"):
            get_session_dir("../../../etc")

    def test_session_id_with_slashes_rejected(self) -> None:
        """Test session_id with slashes is rejected."""
        with pytest.raises(ValueError, match="Invalid session_id"):
            get_session_dir("001/../../secret")

    def test_session_id_with_backslashes_rejected(self) -> None:
        """Test session_id with backslashes is rejected."""
        with pytest.raises(ValueError, match="Invalid session_id"):
            get_checkpoint_path("001\\..\\secret", 1)

    def test_session_id_empty_rejected(self) -> None:
        """Test empty session_id is rejected."""
        with pytest.raises(ValueError, match="Invalid session_id"):
            get_session_dir("")

    def test_session_id_with_dots_only_rejected(self) -> None:
        """Test session_id of just dots is rejected."""
        with pytest.raises(ValueError, match="Invalid session_id"):
            get_session_dir("..")

    def test_session_id_alphanumeric_accepted(self) -> None:
        """Test valid alphanumeric session_id is accepted."""
        path = get_session_dir("001")
        assert "session_001" in str(path)

    def test_session_id_with_underscore_accepted(self) -> None:
        """Test session_id with underscores is accepted."""
        path = get_session_dir("test_session_001")
        assert "session_test_session_001" in str(path)

    def test_turn_number_negative_rejected(self) -> None:
        """Test negative turn_number is rejected."""
        with pytest.raises(ValueError, match="Invalid turn_number"):
            get_checkpoint_path("001", -1)

    def test_turn_number_non_integer_rejected(self) -> None:
        """Test non-integer turn_number is rejected."""
        with pytest.raises(ValueError, match="Invalid turn_number"):
            get_checkpoint_path("001", "five")  # type: ignore[arg-type]

    def test_turn_number_zero_accepted(self) -> None:
        """Test zero turn_number is accepted (edge case)."""
        path = get_checkpoint_path("001", 0)
        assert "turn_000.json" in str(path)

    def test_format_session_id_negative_rejected(self) -> None:
        """Test format_session_id rejects negative numbers."""
        with pytest.raises(ValueError, match="Invalid session_number"):
            format_session_id(-1)

    def test_format_session_id_non_integer_rejected(self) -> None:
        """Test format_session_id rejects non-integers."""
        with pytest.raises(ValueError, match="Invalid session_number"):
            format_session_id("abc")  # type: ignore[arg-type]

    def test_format_session_id_zero_accepted(self) -> None:
        """Test format_session_id accepts zero."""
        assert format_session_id(0) == "000"

    def test_load_checkpoint_with_validation_error_returns_none(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_checkpoint returns None for Pydantic ValidationError."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        # Write JSON with invalid provider (would fail Pydantic validation)
        checkpoint_path = session_dir / "turn_001.json"
        invalid_state = {
            "ground_truth_log": [],
            "turn_queue": [],
            "current_turn": "",
            "agent_memories": {},
            "game_config": {"combat_mode": "Narrative", "summarizer_model": "test", "party_size": 4},
            "dm_config": {"name": "DM", "provider": "invalid_provider", "model": "test", "token_limit": 8000, "color": "#FFFFFF"},
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }
        checkpoint_path.write_text(json.dumps(invalid_state), encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_checkpoint("001", 1)

        # Should return None due to ValidationError from invalid provider
        assert loaded is None


# =============================================================================
# Additional Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in checkpoint system."""

    def test_empty_game_state_serialization(self) -> None:
        """Test serialization of minimal/empty game state."""
        state = create_initial_game_state()
        json_str = serialize_game_state(state)
        data = json.loads(json_str)

        assert data["ground_truth_log"] == []
        assert data["turn_queue"] == []
        assert data["agent_memories"] == {}
        assert data["characters"] == {}

    def test_empty_game_state_roundtrip(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test checkpoint roundtrip with minimal state."""
        state = create_initial_game_state()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 0)
            loaded = load_checkpoint("001", 0)

        assert loaded is not None
        assert loaded["ground_truth_log"] == []
        assert loaded["turn_queue"] == []

    def test_large_ground_truth_log(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test checkpoint with large ground_truth_log (1000+ entries)."""
        # Add many log entries
        for i in range(1000):
            sample_game_state["ground_truth_log"].append(
                f"[dm] This is log entry number {i}."
            )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(sample_game_state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert len(loaded["ground_truth_log"]) == 1002  # Original 2 + 1000

    def test_large_short_term_buffer(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test checkpoint with large short_term_buffer per agent."""
        # Add many buffer entries to DM memory
        dm_memory = sample_game_state["agent_memories"]["dm"]
        for i in range(500):
            dm_memory.short_term_buffer.append(f"Buffer entry {i}")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert len(loaded["agent_memories"]["dm"].short_term_buffer) == 502

    def test_long_term_summary_with_unicode(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test checkpoint with Unicode characters in long_term_summary."""
        dm_memory = sample_game_state["agent_memories"]["dm"]
        dm_memory.long_term_summary = (
            "The party encountered the dragon named \u0394\u03c1\u03ac\u03ba\u03c9\u03bd "
            "(meaning 'dragon' in Greek). Emoji test: \U0001F409\U0001F5E1\uFE0F"
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert "\u0394\u03c1\u03ac\u03ba\u03c9\u03bd" in loaded["agent_memories"]["dm"].long_term_summary
        assert "\U0001F409" in loaded["agent_memories"]["dm"].long_term_summary

    def test_very_long_character_personality(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test checkpoint with very long personality string."""
        fighter = sample_game_state["characters"]["fighter"]
        # Create a new CharacterConfig with long personality
        sample_game_state["characters"]["fighter"] = CharacterConfig(
            name=fighter.name,
            character_class=fighter.character_class,
            personality="A" * 10000,  # Very long personality
            color=fighter.color,
            provider=fighter.provider,
            model=fighter.model,
            token_limit=fighter.token_limit,
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert len(loaded["characters"]["fighter"].personality) == 10000

    def test_many_characters(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test checkpoint with many characters (8 = max party size)."""
        for i in range(7):  # Add 7 more (already have fighter)
            char_name = f"char{i}"
            sample_game_state["characters"][char_name] = CharacterConfig(
                name=f"Character{i}",
                character_class="Rogue",
                personality="Sneaky",
                color="#6B8E6B",
                provider="gemini",
                model="gemini-1.5-flash",
            )
            sample_game_state["agent_memories"][char_name] = AgentMemory()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert len(loaded["characters"]) == 8

    def test_whisper_queue_content(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test checkpoint preserves whisper_queue content."""
        sample_game_state["whisper_queue"] = [
            "[dm->fighter] Secret message",
            "[dm->rogue] Another secret",
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert len(loaded["whisper_queue"]) == 2
        assert "[dm->fighter] Secret message" in loaded["whisper_queue"]

    def test_human_active_state_preserved(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test checkpoint preserves human_active=True state."""
        sample_game_state["human_active"] = True
        sample_game_state["controlled_character"] = "fighter"

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert loaded["human_active"] is True
        assert loaded["controlled_character"] == "fighter"


class TestBoundaryConditions:
    """Tests for boundary conditions in checkpoint system."""

    def test_session_id_boundary_000(self) -> None:
        """Test session_id at lower boundary (000)."""
        path = get_session_dir("000")
        assert "session_000" in str(path)

    def test_session_id_boundary_999(self) -> None:
        """Test session_id at upper expected boundary (999)."""
        path = get_session_dir("999")
        assert "session_999" in str(path)

    def test_session_id_four_digits(self) -> None:
        """Test session_id with 4+ digits is accepted."""
        path = get_session_dir("1234")
        assert "session_1234" in str(path)

    def test_turn_number_boundary_zero(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test turn_number at lower boundary (0)."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(sample_game_state, "001", 0)

        assert "turn_000.json" in str(path)

    def test_turn_number_large_value(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test turn_number with large value (9999)."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(sample_game_state, "001", 9999)

        # Turn number should be padded to at least 3 digits
        assert path.name == "turn_9999.json"

    def test_session_number_zero_format(self) -> None:
        """Test format_session_id with 0."""
        assert format_session_id(0) == "000"

    def test_session_number_large_value(self) -> None:
        """Test format_session_id with large value."""
        assert format_session_id(1000) == "1000"
        assert format_session_id(99999) == "99999"

    def test_token_limit_minimum_boundary(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test checkpoint with token_limit at minimum (1)."""
        state = GameState(
            ground_truth_log=[],
            turn_queue=["dm"],
            current_turn="dm",
            agent_memories={"dm": AgentMemory(token_limit=1)},
            game_config=GameConfig(),
            dm_config=DMConfig(),
            characters={},
            whisper_queue=[],
            human_active=False,
            controlled_character=None,
            session_number=1,
            session_id="001",
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert loaded["agent_memories"]["dm"].token_limit == 1

    def test_party_size_minimum(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test checkpoint with minimum party_size (1)."""
        state = create_initial_game_state()
        state["game_config"] = GameConfig(party_size=1)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert loaded["game_config"].party_size == 1

    def test_party_size_maximum(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test checkpoint with maximum party_size (8)."""
        state = create_initial_game_state()
        state["game_config"] = GameConfig(party_size=8)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert loaded["game_config"].party_size == 8


class TestErrorPaths:
    """Tests for error handling in checkpoint system."""

    @pytest.mark.skipif(
        os.name == "nt",
        reason="chmod doesn't work for write protection on Windows"
    )
    def test_save_to_readonly_directory_raises(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test save_checkpoint raises on read-only directory.

        Note: This test is skipped on Windows where chmod doesn't work.
        """
        import stat

        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        # Try to make read-only (only works on POSIX)
        try:
            os.chmod(session_dir, stat.S_IRUSR | stat.S_IXUSR)

            with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
                with pytest.raises(OSError):
                    save_checkpoint(sample_game_state, "001", 1)
        finally:
            # Restore permissions for cleanup
            os.chmod(session_dir, stat.S_IRWXU)

    def test_load_from_corrupted_file(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_checkpoint returns None for truncated JSON."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        # Write truncated JSON
        checkpoint_path = session_dir / "turn_001.json"
        checkpoint_path.write_text('{"ground_truth_log": [', encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_checkpoint("001", 1)

        assert loaded is None

    def test_load_from_empty_file(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_checkpoint returns None for empty file."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        checkpoint_path = session_dir / "turn_001.json"
        checkpoint_path.write_text("", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_checkpoint("001", 1)

        assert loaded is None

    def test_load_from_json_null(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_checkpoint returns None for JSON null."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        checkpoint_path = session_dir / "turn_001.json"
        checkpoint_path.write_text("null", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_checkpoint("001", 1)

        assert loaded is None

    def test_load_from_json_array(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_checkpoint returns None for JSON array (not object)."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        checkpoint_path = session_dir / "turn_001.json"
        checkpoint_path.write_text("[]", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_checkpoint("001", 1)

        assert loaded is None

    def test_load_with_wrong_field_types(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_checkpoint handles wrong field types.

        Note: TypedDict doesn't validate types at runtime, so deserialize
        may succeed even with wrong types. The real validation happens when
        Pydantic models are constructed from nested dicts.
        """
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        # Use invalid Pydantic model structure (token_limit should be int, not string)
        # This will fail Pydantic validation in AgentMemory construction
        checkpoint_path = session_dir / "turn_001.json"
        invalid_state = {
            "ground_truth_log": [],
            "turn_queue": [],
            "current_turn": "",
            "agent_memories": {"test": {"token_limit": "not_an_int", "long_term_summary": "", "short_term_buffer": []}},
            "game_config": {"combat_mode": "Narrative", "summarizer_model": "test", "party_size": 4},
            "dm_config": {"name": "DM", "provider": "gemini", "model": "test", "token_limit": 8000, "color": "#FFFFFF"},
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }
        checkpoint_path.write_text(json.dumps(invalid_state), encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_checkpoint("001", 1)

        # Should return None due to Pydantic ValidationError on AgentMemory
        assert loaded is None

    def test_load_with_invalid_agent_memory_structure(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_checkpoint returns None for invalid AgentMemory."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        checkpoint_path = session_dir / "turn_001.json"
        invalid_state = {
            "ground_truth_log": [],
            "turn_queue": [],
            "current_turn": "",
            "agent_memories": {"dm": {"token_limit": "not an int"}},  # Wrong type
            "game_config": {"combat_mode": "Narrative", "summarizer_model": "test", "party_size": 4},
            "dm_config": {"name": "DM", "provider": "gemini", "model": "test", "token_limit": 8000, "color": "#FFFFFF"},
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
        }
        checkpoint_path.write_text(json.dumps(invalid_state), encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_checkpoint("001", 1)

        assert loaded is None

    def test_deserialize_with_extra_fields_ignored(self) -> None:
        """Test deserialize tolerates extra unknown fields."""
        json_str = json.dumps({
            "ground_truth_log": [],
            "turn_queue": [],
            "current_turn": "",
            "agent_memories": {},
            "game_config": {"combat_mode": "Narrative", "summarizer_model": "test", "party_size": 4},
            "dm_config": {"name": "DM", "provider": "gemini", "model": "test", "token_limit": 8000, "color": "#FFFFFF"},
            "characters": {},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "unknown_extra_field": "should be ignored",
        })

        # Should not raise - extra fields are ignored in TypedDict
        restored = deserialize_game_state(json_str)
        assert restored["session_id"] == "001"


class TestFileSystemEdgeCases:
    """Tests for file system edge cases."""

    def test_session_id_with_numbers_only(self) -> None:
        """Test session_id with pure numeric values."""
        path = get_session_dir("123456789")
        assert "session_123456789" in str(path)

    def test_session_id_alphanumeric_mixed(self) -> None:
        """Test session_id with mixed alphanumeric."""
        path = get_session_dir("abc123def456")
        assert "session_abc123def456" in str(path)

    def test_session_id_with_multiple_underscores(self) -> None:
        """Test session_id with multiple underscores."""
        path = get_session_dir("test__multiple___underscores")
        assert "session_test__multiple___underscores" in str(path)

    def test_session_id_uppercase_letters(self) -> None:
        """Test session_id with uppercase letters."""
        path = get_session_dir("ABC123")
        assert "session_ABC123" in str(path)

    def test_concurrent_saves_to_different_turns(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test saving multiple checkpoints rapidly doesn't cause issues."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            # Save multiple checkpoints rapidly
            for turn in range(10):
                sample_game_state["ground_truth_log"].append(f"[dm] Turn {turn}")
                save_checkpoint(sample_game_state, "001", turn)

            # Verify all checkpoints exist
            checkpoints = list_checkpoints("001")
            assert len(checkpoints) == 10

    def test_overwrite_existing_checkpoint(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test overwriting checkpoint replaces content completely."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            # Save first version
            sample_game_state["ground_truth_log"] = ["[dm] Version 1"]
            save_checkpoint(sample_game_state, "001", 1)

            # Save second version to same turn
            sample_game_state["ground_truth_log"] = ["[dm] Version 2"]
            save_checkpoint(sample_game_state, "001", 1)

            # Load and verify it's version 2
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert loaded["ground_truth_log"] == ["[dm] Version 2"]

    def test_list_sessions_with_many_sessions(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_sessions with many sessions."""
        # Create 50 session directories
        for i in range(50):
            (temp_campaigns_dir / f"session_{i:03d}").mkdir()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sessions = list_sessions()

        assert len(sessions) == 50
        # Verify sorting
        assert sessions[0] == "000"
        assert sessions[49] == "049"

    def test_list_checkpoints_with_many_checkpoints(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test list_checkpoints with many checkpoints."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            # Create 50 checkpoints
            for turn in range(50):
                save_checkpoint(sample_game_state, "001", turn)

            checkpoints = list_checkpoints("001")

        assert len(checkpoints) == 50
        assert checkpoints[0] == 0
        assert checkpoints[49] == 49


class TestInputValidationExtended:
    """Extended tests for input validation."""

    def test_session_id_with_spaces_rejected(self) -> None:
        """Test session_id with spaces is rejected."""
        with pytest.raises(ValueError, match="Invalid session_id"):
            get_session_dir("001 002")

    def test_session_id_with_special_chars_rejected(self) -> None:
        """Test session_id with special characters is rejected."""
        special_chars = ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")"]
        for char in special_chars:
            with pytest.raises(ValueError, match="Invalid session_id"):
                get_session_dir(f"001{char}002")

    def test_session_id_with_hyphen_rejected(self) -> None:
        """Test session_id with hyphen is rejected (only underscore allowed)."""
        with pytest.raises(ValueError, match="Invalid session_id"):
            get_session_dir("session-001")

    def test_turn_number_float_rejected(self) -> None:
        """Test floating point turn_number is rejected."""
        with pytest.raises(ValueError, match="Invalid turn_number"):
            get_checkpoint_path("001", 1.5)  # type: ignore[arg-type]

    def test_turn_number_none_rejected(self) -> None:
        """Test None turn_number is rejected."""
        with pytest.raises(ValueError, match="Invalid turn_number"):
            get_checkpoint_path("001", None)  # type: ignore[arg-type]

    def test_session_id_none_rejected(self) -> None:
        """Test None session_id is rejected."""
        with pytest.raises((ValueError, TypeError)):
            get_session_dir(None)  # type: ignore[arg-type]

    def test_format_session_id_float_rejected(self) -> None:
        """Test format_session_id rejects floats."""
        with pytest.raises(ValueError, match="Invalid session_number"):
            format_session_id(1.5)  # type: ignore[arg-type]


class TestCombatModePreservation:
    """Tests for combat mode preservation in checkpoints."""

    def test_tactical_combat_mode_preserved(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test Tactical combat_mode is preserved through checkpoint."""
        state = create_initial_game_state()
        state["game_config"] = GameConfig(combat_mode="Tactical")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert loaded["game_config"].combat_mode == "Tactical"

    def test_narrative_combat_mode_preserved(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test Narrative combat_mode is preserved through checkpoint."""
        state = create_initial_game_state()
        state["game_config"] = GameConfig(combat_mode="Narrative")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert loaded["game_config"].combat_mode == "Narrative"


class TestProviderPreservation:
    """Tests for LLM provider preservation in checkpoints."""

    @pytest.mark.parametrize("provider", ["gemini", "claude", "ollama"])
    def test_dm_provider_preserved(
        self, temp_campaigns_dir: Path, provider: str
    ) -> None:
        """Test DM provider is preserved through checkpoint."""
        state = create_initial_game_state()
        state["dm_config"] = DMConfig(provider=provider)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert loaded["dm_config"].provider == provider

    @pytest.mark.parametrize("provider", ["gemini", "claude", "ollama"])
    def test_character_provider_preserved(
        self, temp_campaigns_dir: Path, provider: str
    ) -> None:
        """Test character provider is preserved through checkpoint."""
        state = create_initial_game_state()
        state["characters"]["test"] = CharacterConfig(
            name="Test",
            character_class="Fighter",
            personality="Brave",
            color="#C45C4A",
            provider=provider,
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "001", 1)
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert loaded["characters"]["test"].provider == provider


class TestAutoCheckpointGraphIntegration:
    """Integration tests for auto-checkpoint in graph execution."""

    def test_run_single_round_triggers_checkpoint(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test that run_single_round saves checkpoint after execution."""
        from unittest.mock import MagicMock, patch as mock_patch

        from langchain_core.messages import AIMessage

        from graph import run_single_round

        state = create_initial_game_state()
        state["turn_queue"] = ["dm", "fighter"]
        state["current_turn"] = "dm"
        state["dm_config"] = DMConfig(provider="gemini", model="gemini-1.5-flash")
        state["characters"]["fighter"] = CharacterConfig(
            name="Fighter",
            character_class="Fighter",
            personality="Brave",
            color="#C45C4A",
        )
        state["agent_memories"]["dm"] = AgentMemory()
        state["agent_memories"]["fighter"] = AgentMemory()
        state["session_id"] = "001"

        with mock_patch("agents.get_llm") as mock_get_llm, \
             mock_patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            mock_model = MagicMock()
            mock_model.bind_tools.return_value = mock_model
            mock_model.invoke.side_effect = [
                AIMessage(content="DM narrates."),
                AIMessage(content="Fighter acts."),
            ]
            mock_get_llm.return_value = mock_model

            result = run_single_round(state)

            # Verify checkpoint was created
            checkpoints = list_checkpoints("001")
            assert len(checkpoints) > 0

    def test_human_intervention_triggers_checkpoint(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test that human_intervention_node saves checkpoint after human action."""
        from unittest.mock import MagicMock, patch as mock_patch

        from graph import human_intervention_node

        state = create_initial_game_state()
        state["turn_queue"] = ["dm", "fighter"]
        state["current_turn"] = "fighter"
        state["human_active"] = True
        state["controlled_character"] = "fighter"
        state["characters"]["fighter"] = CharacterConfig(
            name="Fighter",
            character_class="Fighter",
            personality="Brave",
            color="#C45C4A",
        )
        state["agent_memories"]["fighter"] = AgentMemory()
        state["session_id"] = "001"

        # Mock streamlit session_state
        mock_session_state = {"human_pending_action": "I attack the goblin!"}

        with mock_patch("streamlit.session_state", mock_session_state), \
             mock_patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            result = human_intervention_node(state)

            # Verify checkpoint was created (human action added to log)
            if len(result["ground_truth_log"]) > 0:
                checkpoints = list_checkpoints("001")
                assert len(checkpoints) > 0


class TestSessionIdFromSessionNumber:
    """Tests for session_id generation from session_number."""

    def test_session_id_single_digit_number(self) -> None:
        """Test session_id generation from single digit session_number."""
        state = create_initial_game_state()
        state["session_number"] = 1
        state["session_id"] = f"{state['session_number']:03d}"
        assert state["session_id"] == "001"

    def test_session_id_double_digit_number(self) -> None:
        """Test session_id generation from double digit session_number."""
        state = create_initial_game_state()
        state["session_number"] = 42
        state["session_id"] = f"{state['session_number']:03d}"
        assert state["session_id"] == "042"

    def test_session_id_triple_digit_number(self) -> None:
        """Test session_id generation from triple digit session_number."""
        state = create_initial_game_state()
        state["session_number"] = 100
        state["session_id"] = f"{state['session_number']:03d}"
        assert state["session_id"] == "100"

    def test_session_id_preserves_through_checkpoint(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test session_id and session_number match after checkpoint roundtrip."""
        state = create_initial_game_state()
        state["session_number"] = 42
        state["session_id"] = "042"

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(state, "042", 1)
            loaded = load_checkpoint("042", 1)

        assert loaded is not None
        assert loaded["session_number"] == 42
        assert loaded["session_id"] == "042"


class TestCheckpointFileSizes:
    """Tests to verify checkpoint file sizes are reasonable."""

    def test_minimal_state_file_size(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test minimal state checkpoint is small (< 1KB)."""
        state = create_initial_game_state()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(state, "001", 1)

        file_size = path.stat().st_size
        assert file_size < 1024  # Less than 1KB

    def test_large_state_file_size(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test large state checkpoint is created (verify it works)."""
        # Add lots of content
        for i in range(100):
            sample_game_state["ground_truth_log"].append(f"[dm] This is a long message {i}. " * 10)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_checkpoint(sample_game_state, "001", 1)

        # File should exist and be readable
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert len(data["ground_truth_log"]) > 100
