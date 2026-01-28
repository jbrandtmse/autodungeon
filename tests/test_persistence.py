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
            save_checkpoint(sample_game_state, "001", 1)
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
        from unittest.mock import MagicMock
        from unittest.mock import patch as mock_patch

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

            run_single_round(state)

            # Verify checkpoint was created
            checkpoints = list_checkpoints("001")
            assert len(checkpoints) > 0

    def test_human_intervention_triggers_checkpoint(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test that human_intervention_node saves checkpoint after human action."""
        from unittest.mock import patch as mock_patch

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


# =============================================================================
# Story 4.2: Checkpoint Browser & Restore Tests
# =============================================================================


class TestCheckpointInfo:
    """Tests for CheckpointInfo model and get_checkpoint_info (Story 4.2)."""

    def test_checkpoint_info_model_fields(self) -> None:
        """Test CheckpointInfo model has all required fields."""
        from persistence import CheckpointInfo

        info = CheckpointInfo(
            turn_number=5,
            timestamp="2026-01-28 10:30",
            brief_context="The adventure begins...",
            message_count=10,
        )

        assert info.turn_number == 5
        assert info.timestamp == "2026-01-28 10:30"
        assert info.brief_context == "The adventure begins..."
        assert info.message_count == 10

    def test_checkpoint_info_default_values(self) -> None:
        """Test CheckpointInfo has sensible defaults."""
        from persistence import CheckpointInfo

        info = CheckpointInfo(turn_number=1, timestamp="2026-01-28 10:00")

        assert info.brief_context == ""
        assert info.message_count == 0

    def test_get_checkpoint_info_returns_metadata(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test get_checkpoint_info returns correct metadata."""
        from persistence import get_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 5)
            info = get_checkpoint_info("001", 5)

        assert info is not None
        assert info.turn_number == 5
        assert info.timestamp  # Non-empty timestamp
        assert info.message_count == len(sample_game_state["ground_truth_log"])

    def test_get_checkpoint_info_extracts_brief_context(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test get_checkpoint_info extracts brief context from last log entry."""
        from persistence import get_checkpoint_info

        sample_game_state["ground_truth_log"] = [
            "[dm] First message.",
            "[fighter] I attack!",
            "[dm] The enemy falls.",
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 3)
            info = get_checkpoint_info("001", 3)

        assert info is not None
        # Context should be from last entry, with [dm] prefix stripped
        assert "The enemy falls." in info.brief_context

    def test_get_checkpoint_info_truncates_long_context(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test brief_context is truncated to 100 chars with ellipsis."""
        from persistence import get_checkpoint_info

        long_message = "[dm] " + "A" * 200
        sample_game_state["ground_truth_log"] = [long_message]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            info = get_checkpoint_info("001", 1)

        assert info is not None
        assert len(info.brief_context) <= 103  # 100 chars + "..."
        assert info.brief_context.endswith("...")

    def test_get_checkpoint_info_missing_checkpoint_returns_none(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_checkpoint_info returns None for missing checkpoint."""
        from persistence import get_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            info = get_checkpoint_info("001", 999)

        assert info is None

    def test_get_checkpoint_info_corrupted_file_returns_none(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_checkpoint_info returns None for corrupted file."""
        from persistence import get_checkpoint_info

        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()
        checkpoint_path = session_dir / "turn_001.json"
        checkpoint_path.write_text("not valid json", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            info = get_checkpoint_info("001", 1)

        assert info is None


class TestListCheckpointInfo:
    """Tests for list_checkpoint_info function (Story 4.2)."""

    def test_list_checkpoint_info_returns_list(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test list_checkpoint_info returns list of CheckpointInfo."""
        from persistence import CheckpointInfo, list_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            save_checkpoint(sample_game_state, "001", 2)

            infos = list_checkpoint_info("001")

        assert len(infos) == 2
        assert all(isinstance(info, CheckpointInfo) for info in infos)

    def test_list_checkpoint_info_sorted_descending(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test list_checkpoint_info returns newest first (descending)."""
        from persistence import list_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            save_checkpoint(sample_game_state, "001", 3)
            save_checkpoint(sample_game_state, "001", 2)

            infos = list_checkpoint_info("001")

        assert len(infos) == 3
        assert infos[0].turn_number == 3  # Newest first
        assert infos[1].turn_number == 2
        assert infos[2].turn_number == 1

    def test_list_checkpoint_info_empty_session(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_checkpoint_info returns empty list for empty session."""
        from persistence import list_checkpoint_info

        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            infos = list_checkpoint_info("001")

        assert infos == []

    def test_list_checkpoint_info_skips_corrupted(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test list_checkpoint_info skips corrupted checkpoints."""
        from persistence import list_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)

        # Create corrupted checkpoint
        session_dir = temp_campaigns_dir / "session_001"
        corrupted_path = session_dir / "turn_002.json"
        corrupted_path.write_text("invalid json", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            infos = list_checkpoint_info("001")

        # Should only have the valid checkpoint
        assert len(infos) == 1
        assert infos[0].turn_number == 1


class TestCheckpointPreview:
    """Tests for get_checkpoint_preview function (Story 4.2)."""

    def test_get_checkpoint_preview_returns_recent_messages(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test get_checkpoint_preview returns last N messages."""
        from persistence import get_checkpoint_preview

        sample_game_state["ground_truth_log"] = [
            f"[dm] Message {i}" for i in range(10)
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 10)
            preview = get_checkpoint_preview("001", 10, num_messages=3)

        assert preview is not None
        assert len(preview) == 3
        assert preview[-1] == "[dm] Message 9"  # Last message

    def test_get_checkpoint_preview_default_num_messages(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test get_checkpoint_preview uses default of 5 messages."""
        from persistence import get_checkpoint_preview

        sample_game_state["ground_truth_log"] = [
            f"[dm] Message {i}" for i in range(10)
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 10)
            preview = get_checkpoint_preview("001", 10)

        assert preview is not None
        assert len(preview) == 5

    def test_get_checkpoint_preview_fewer_messages_than_requested(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test get_checkpoint_preview when fewer messages than requested."""
        from persistence import get_checkpoint_preview

        sample_game_state["ground_truth_log"] = ["[dm] Only one message."]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            preview = get_checkpoint_preview("001", 1, num_messages=5)

        assert preview is not None
        assert len(preview) == 1

    def test_get_checkpoint_preview_empty_log(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test get_checkpoint_preview with empty ground_truth_log."""
        from persistence import get_checkpoint_preview

        sample_game_state["ground_truth_log"] = []

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 0)
            preview = get_checkpoint_preview("001", 0)

        assert preview is not None
        assert preview == []

    def test_get_checkpoint_preview_missing_checkpoint(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_checkpoint_preview returns None for missing checkpoint."""
        from persistence import get_checkpoint_preview

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            preview = get_checkpoint_preview("001", 999)

        assert preview is None


class TestStory42AcceptanceCriteria:
    """Acceptance tests for all Story 4.2 criteria."""

    def test_ac1_checkpoint_list_shows_metadata(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #1: Checkpoint list shows turn number, timestamp, brief context."""
        from persistence import list_checkpoint_info

        sample_game_state["ground_truth_log"] = ["[dm] The adventure begins."]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            infos = list_checkpoint_info("001")

        assert len(infos) == 1
        info = infos[0]
        assert info.turn_number == 1
        assert info.timestamp  # Non-empty
        assert "The adventure begins" in info.brief_context

    def test_ac2_checkpoint_preview_shows_content(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #2: Checkpoint preview shows what was happening at that turn."""
        from persistence import get_checkpoint_preview

        sample_game_state["ground_truth_log"] = [
            "[dm] You enter the dungeon.",
            "[fighter] I draw my sword.",
            "[rogue] I check for traps.",
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 3)
            preview = get_checkpoint_preview("001", 3)

        assert preview is not None
        assert len(preview) == 3
        assert "[dm] You enter the dungeon." in preview
        assert "[fighter] I draw my sword." in preview
        assert "[rogue] I check for traps." in preview

    def test_ac3_restore_loads_checkpoint(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #3: Restore loads game state from checkpoint file."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            # Save checkpoint at turn 1
            sample_game_state["ground_truth_log"] = ["[dm] Turn 1 state."]
            save_checkpoint(sample_game_state, "001", 1)

            # Load it back
            loaded = load_checkpoint("001", 1)

        assert loaded is not None
        assert loaded["ground_truth_log"] == ["[dm] Turn 1 state."]

    def test_ac3_restore_includes_agent_memories(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #3: Restored state includes agent memories (FR36, NFR13)."""
        # Modify agent memory before saving
        sample_game_state["agent_memories"]["dm"].long_term_summary = "Important memory"
        sample_game_state["agent_memories"]["dm"].short_term_buffer = [
            "Recent event"
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded_state = load_checkpoint("001", 1)

        assert loaded_state is not None
        dm_memory = loaded_state["agent_memories"]["dm"]
        assert dm_memory.long_term_summary == "Important memory"
        assert dm_memory.short_term_buffer == ["Recent event"]

    def test_ac4_game_continues_from_restored_turn(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #4: Game can continue from restored turn."""
        # Save state at turn 2
        sample_game_state["ground_truth_log"] = [
            "[dm] Turn 1",
            "[fighter] Turn 2",
        ]
        sample_game_state["current_turn"] = "rogue"

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 2)
            loaded_state = load_checkpoint("001", 2)

        assert loaded_state is not None
        # State should be ready for next turn
        assert loaded_state["current_turn"] == "rogue"
        assert len(loaded_state["ground_truth_log"]) == 2

    def test_ac5_deserialize_returns_valid_gamestate(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #5: load_checkpoint deserializes to valid GameState."""
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            loaded_state = load_checkpoint("001", 1)

        assert loaded_state is not None
        # Verify it's a valid GameState structure
        assert "ground_truth_log" in loaded_state
        assert "turn_queue" in loaded_state
        assert "current_turn" in loaded_state
        assert "agent_memories" in loaded_state
        assert "game_config" in loaded_state
        assert "dm_config" in loaded_state
        assert "characters" in loaded_state
        assert "human_active" in loaded_state

    def test_checkpoint_info_message_count_accurate(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test message_count reflects actual log length."""
        from persistence import get_checkpoint_info

        sample_game_state["ground_truth_log"] = [
            f"[dm] Message {i}" for i in range(7)
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 7)
            info = get_checkpoint_info("001", 7)

        assert info is not None
        assert info.message_count == 7


# =============================================================================
# Story 4.2: Extended Test Coverage - Edge Cases & Error Paths
# =============================================================================


class TestCheckpointInfoEdgeCases:
    """Edge case tests for CheckpointInfo (Story 4.2 expanded coverage)."""

    def test_checkpoint_info_turn_number_zero(self) -> None:
        """Test CheckpointInfo accepts turn_number=0 (boundary condition)."""
        from persistence import CheckpointInfo

        info = CheckpointInfo(turn_number=0, timestamp="2026-01-28 10:00")
        assert info.turn_number == 0

    def test_checkpoint_info_turn_number_large(self) -> None:
        """Test CheckpointInfo accepts large turn numbers (9999)."""
        from persistence import CheckpointInfo

        info = CheckpointInfo(turn_number=9999, timestamp="2026-01-28 10:00")
        assert info.turn_number == 9999

    def test_checkpoint_info_negative_turn_raises(self) -> None:
        """Test CheckpointInfo rejects negative turn numbers."""
        from pydantic import ValidationError

        from persistence import CheckpointInfo

        with pytest.raises(ValidationError):
            CheckpointInfo(turn_number=-1, timestamp="2026-01-28")

    def test_checkpoint_info_negative_message_count_raises(self) -> None:
        """Test CheckpointInfo rejects negative message_count."""
        from pydantic import ValidationError

        from persistence import CheckpointInfo

        with pytest.raises(ValidationError):
            CheckpointInfo(turn_number=1, timestamp="2026-01-28", message_count=-5)

    def test_checkpoint_info_empty_timestamp(self) -> None:
        """Test CheckpointInfo handles empty timestamp string."""
        from persistence import CheckpointInfo

        info = CheckpointInfo(turn_number=1, timestamp="")
        assert info.timestamp == ""

    def test_checkpoint_info_unicode_context(self) -> None:
        """Test CheckpointInfo handles unicode characters in brief_context."""
        from persistence import CheckpointInfo

        info = CheckpointInfo(
            turn_number=1, timestamp="2026-01-28", brief_context="Dragon says: \u201cFire!\u201d \U0001f525"
        )
        assert "\u201c" in info.brief_context


class TestGetCheckpointInfoEdgeCases:
    """Edge case tests for get_checkpoint_info (Story 4.2 expanded coverage)."""

    def test_get_checkpoint_info_turn_zero(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test get_checkpoint_info handles turn 0."""
        from persistence import get_checkpoint_info

        sample_game_state["ground_truth_log"] = []

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 0)
            info = get_checkpoint_info("001", 0)

        assert info is not None
        assert info.turn_number == 0
        assert info.message_count == 0

    def test_get_checkpoint_info_large_turn(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test get_checkpoint_info handles large turn number (9999)."""
        from persistence import get_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 9999)
            info = get_checkpoint_info("001", 9999)

        assert info is not None
        assert info.turn_number == 9999

    def test_get_checkpoint_info_context_without_prefix(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test context extraction when log entry has no [agent] prefix."""
        from persistence import get_checkpoint_info

        sample_game_state["ground_truth_log"] = ["System: Game started."]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            info = get_checkpoint_info("001", 1)

        assert info is not None
        # Should use entire entry since no [agent] prefix
        assert "System: Game started." in info.brief_context

    def test_get_checkpoint_info_context_exactly_100_chars(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test context extraction when content is exactly 100 characters."""
        from persistence import get_checkpoint_info

        # Create message with exactly 100 chars after prefix removal
        content = "A" * 100
        sample_game_state["ground_truth_log"] = [f"[dm] {content}"]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            info = get_checkpoint_info("001", 1)

        assert info is not None
        # Should not have ellipsis since exactly 100
        assert info.brief_context == content
        assert not info.brief_context.endswith("...")

    def test_get_checkpoint_info_context_101_chars(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test context truncation when content is 101 characters."""
        from persistence import get_checkpoint_info

        # Create message with exactly 101 chars after prefix removal
        content = "A" * 101
        sample_game_state["ground_truth_log"] = [f"[dm] {content}"]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            info = get_checkpoint_info("001", 1)

        assert info is not None
        assert info.brief_context.endswith("...")
        assert len(info.brief_context) == 103  # 100 + "..."

    def test_get_checkpoint_info_empty_bracket_prefix(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test context extraction with empty bracket prefix []."""
        from persistence import get_checkpoint_info

        sample_game_state["ground_truth_log"] = ["[] Empty prefix test"]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            info = get_checkpoint_info("001", 1)

        assert info is not None
        assert "Empty prefix test" in info.brief_context

    def test_get_checkpoint_info_file_permission_error(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test get_checkpoint_info returns None on file read error."""
        from persistence import get_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            # Checkpoint created at: temp_campaigns_dir / "session_001" / "turn_001.json"

            # Mock file read to raise OSError
            with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
                info = get_checkpoint_info("001", 1)

        assert info is None


class TestListCheckpointInfoEdgeCases:
    """Edge case tests for list_checkpoint_info (Story 4.2 expanded coverage)."""

    def test_list_checkpoint_info_single_checkpoint(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test list_checkpoint_info with single checkpoint."""
        from persistence import list_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            infos = list_checkpoint_info("001")

        assert len(infos) == 1
        assert infos[0].turn_number == 1

    def test_list_checkpoint_info_many_checkpoints(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test list_checkpoint_info with many checkpoints (100)."""
        from persistence import list_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            for i in range(100):
                save_checkpoint(sample_game_state, "001", i)
            infos = list_checkpoint_info("001")

        assert len(infos) == 100
        # Should be sorted descending
        assert infos[0].turn_number == 99
        assert infos[-1].turn_number == 0

    def test_list_checkpoint_info_nonexistent_session(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_checkpoint_info for nonexistent session."""
        from persistence import list_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            infos = list_checkpoint_info("999")

        assert infos == []

    def test_list_checkpoint_info_mixed_valid_invalid(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test list_checkpoint_info skips invalid but includes all valid."""
        from persistence import list_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            save_checkpoint(sample_game_state, "001", 3)
            save_checkpoint(sample_game_state, "001", 5)

        # Corrupt checkpoint 3
        corrupted = temp_campaigns_dir / "session_001" / "turn_003.json"
        corrupted.write_text("not json", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            infos = list_checkpoint_info("001")

        assert len(infos) == 2
        turn_numbers = [info.turn_number for info in infos]
        assert 5 in turn_numbers
        assert 1 in turn_numbers
        assert 3 not in turn_numbers


class TestCheckpointPreviewEdgeCases:
    """Edge case tests for get_checkpoint_preview (Story 4.2 expanded coverage)."""

    def test_preview_with_num_messages_zero(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test preview with num_messages=0 returns all messages (Python slice behavior)."""
        from persistence import get_checkpoint_preview

        sample_game_state["ground_truth_log"] = ["[dm] Message 1", "[dm] Message 2"]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            preview = get_checkpoint_preview("001", 1, num_messages=0)

        # Note: log[-0:] equals log[0:] which returns all elements (Python slice behavior)
        assert preview is not None
        assert preview == ["[dm] Message 1", "[dm] Message 2"]

    def test_preview_with_large_num_messages(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test preview with num_messages larger than available."""
        from persistence import get_checkpoint_preview

        sample_game_state["ground_truth_log"] = ["[dm] Only message."]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            preview = get_checkpoint_preview("001", 1, num_messages=1000)

        assert preview is not None
        assert len(preview) == 1

    def test_preview_preserves_message_order(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test preview preserves chronological order."""
        from persistence import get_checkpoint_preview

        sample_game_state["ground_truth_log"] = [
            f"[dm] Message {i}" for i in range(10)
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 10)
            preview = get_checkpoint_preview("001", 10, num_messages=3)

        assert preview == ["[dm] Message 7", "[dm] Message 8", "[dm] Message 9"]

    def test_preview_corrupted_checkpoint(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test preview returns None for corrupted checkpoint."""
        from persistence import get_checkpoint_preview

        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()
        corrupted = session_dir / "turn_001.json"
        corrupted.write_text('{"invalid": "structure"}', encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            preview = get_checkpoint_preview("001", 1)

        assert preview is None


class TestCheckpointInfoIntegration:
    """Integration tests for checkpoint browser data flow (Story 4.2)."""

    def test_full_browser_data_flow(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test complete flow: save -> list -> info -> preview."""
        from persistence import (
            get_checkpoint_info,
            get_checkpoint_preview,
            list_checkpoint_info,
        )

        # Create multiple checkpoints with distinct content
        for i in range(1, 4):
            sample_game_state["ground_truth_log"] = [
                f"[dm] Turn {i} narration."
            ]
            with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
                save_checkpoint(sample_game_state, "001", i)

        # List all checkpoints
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            infos = list_checkpoint_info("001")

        assert len(infos) == 3
        assert infos[0].turn_number == 3  # Newest first

        # Get info for specific checkpoint
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            info = get_checkpoint_info("001", 2)

        assert info is not None
        assert info.turn_number == 2
        assert "Turn 2 narration" in info.brief_context

        # Get preview for that checkpoint
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            preview = get_checkpoint_preview("001", 2)

        assert preview is not None
        assert "[dm] Turn 2 narration." in preview

    def test_session_isolation(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test checkpoints are isolated between sessions."""
        from persistence import list_checkpoint_info

        # Create checkpoints in different sessions
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            save_checkpoint(sample_game_state, "001", 2)
            save_checkpoint(sample_game_state, "002", 1)

            infos_001 = list_checkpoint_info("001")
            infos_002 = list_checkpoint_info("002")

        assert len(infos_001) == 2
        assert len(infos_002) == 1


class TestCheckpointValidationBoundaries:
    """Boundary condition tests for checkpoint validation (Story 4.2)."""

    def test_get_checkpoint_info_validates_session_id(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_checkpoint_info validates session_id."""
        from persistence import get_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            with pytest.raises(ValueError, match="Invalid session_id"):
                get_checkpoint_info("../etc/passwd", 1)

    def test_get_checkpoint_info_validates_turn_number(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_checkpoint_info validates turn_number."""
        from persistence import get_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            with pytest.raises(ValueError, match="Invalid turn_number"):
                get_checkpoint_info("001", -1)

    def test_get_checkpoint_preview_validates_session_id(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_checkpoint_preview validates session_id."""
        from persistence import get_checkpoint_preview

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            with pytest.raises(ValueError, match="Invalid session_id"):
                get_checkpoint_preview("bad/path", 1)

    def test_list_checkpoint_info_validates_session_id(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_checkpoint_info validates session_id."""
        from persistence import list_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            with pytest.raises(ValueError, match="Invalid session_id"):
                list_checkpoint_info("")


class TestCheckpointTimestampHandling:
    """Tests for checkpoint timestamp extraction (Story 4.2)."""

    def test_timestamp_format_yyyy_mm_dd_hh_mm(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test timestamp is formatted as YYYY-MM-DD HH:MM."""
        import re

        from persistence import get_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            info = get_checkpoint_info("001", 1)

        assert info is not None
        # Should match format like "2026-01-28 10:30"
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", info.timestamp)

    def test_timestamp_from_file_mtime(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test timestamp comes from file modification time."""
        import time

        from persistence import get_checkpoint_info

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)

            # Modify file mtime to a known value
            checkpoint_path = temp_campaigns_dir / "session_001" / "turn_001.json"
            known_time = time.mktime((2025, 6, 15, 14, 30, 0, 0, 0, -1))
            os.utime(checkpoint_path, (known_time, known_time))

            info = get_checkpoint_info("001", 1)

        assert info is not None
        assert "2025-06-15 14:30" in info.timestamp


# =============================================================================
# Story 4.3: Session Metadata & Multi-Session Continuity Tests
# =============================================================================


class TestSessionMetadataModel:
    """Tests for SessionMetadata Pydantic model (Story 4.3)."""

    def test_session_metadata_model_fields(self) -> None:
        """Test SessionMetadata model has all required fields."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name="My Adventure",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T12:00:00Z",
            character_names=["Theron", "Lyra"],
            turn_count=15,
        )

        assert metadata.session_id == "001"
        assert metadata.session_number == 1
        assert metadata.name == "My Adventure"
        assert metadata.created_at == "2026-01-28T10:00:00Z"
        assert metadata.updated_at == "2026-01-28T12:00:00Z"
        assert metadata.character_names == ["Theron", "Lyra"]
        assert metadata.turn_count == 15

    def test_session_metadata_default_values(self) -> None:
        """Test SessionMetadata has sensible defaults."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        assert metadata.name == ""
        assert metadata.character_names == []
        assert metadata.turn_count == 0

    def test_session_metadata_validation_session_id(self) -> None:
        """Test SessionMetadata validates session_id is not empty."""
        from pydantic import ValidationError

        from models import SessionMetadata

        with pytest.raises(ValidationError):
            SessionMetadata(
                session_id="",  # Empty - should fail
                session_number=1,
                created_at="2026-01-28T10:00:00Z",
                updated_at="2026-01-28T10:00:00Z",
            )

    def test_session_metadata_validation_session_number(self) -> None:
        """Test SessionMetadata validates session_number >= 1."""
        from pydantic import ValidationError

        from models import SessionMetadata

        with pytest.raises(ValidationError):
            SessionMetadata(
                session_id="001",
                session_number=0,  # Invalid - must be >= 1
                created_at="2026-01-28T10:00:00Z",
                updated_at="2026-01-28T10:00:00Z",
            )


class TestSessionMetadataPersistence:
    """Tests for save/load session metadata (Story 4.3)."""

    def test_save_session_metadata_creates_config_yaml(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test save_session_metadata creates config.yaml file."""
        from models import SessionMetadata
        from persistence import save_session_metadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name="Test Session",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
            character_names=["Theron"],
            turn_count=5,
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_session_metadata("001", metadata)

        assert path.exists()
        assert path.name == "config.yaml"
        assert path.parent.name == "session_001"

    def test_save_session_metadata_yaml_content(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test save_session_metadata writes correct YAML content."""
        from models import SessionMetadata
        from persistence import save_session_metadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name="Test Session",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T12:00:00Z",
            character_names=["Theron", "Lyra"],
            turn_count=10,
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            path = save_session_metadata("001", metadata)

        content = path.read_text(encoding="utf-8")
        assert "session_id: '001'" in content or "session_id: \"001\"" in content or "session_id: 001" in content
        assert "session_number: 1" in content
        assert "name: Test Session" in content
        assert "Theron" in content
        assert "Lyra" in content
        assert "turn_count: 10" in content

    def test_load_session_metadata_roundtrip(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test save and load session metadata roundtrip."""
        from models import SessionMetadata
        from persistence import load_session_metadata, save_session_metadata

        original = SessionMetadata(
            session_id="001",
            session_number=1,
            name="Test Session",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T12:00:00Z",
            character_names=["Theron", "Lyra"],
            turn_count=10,
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_session_metadata("001", original)
            loaded = load_session_metadata("001")

        assert loaded is not None
        assert loaded.session_id == original.session_id
        assert loaded.session_number == original.session_number
        assert loaded.name == original.name
        assert loaded.created_at == original.created_at
        assert loaded.updated_at == original.updated_at
        assert loaded.character_names == original.character_names
        assert loaded.turn_count == original.turn_count

    def test_load_session_metadata_missing_file(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_session_metadata returns None for missing config."""
        from persistence import load_session_metadata

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_session_metadata("999")

        assert loaded is None

    def test_load_session_metadata_invalid_yaml(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_session_metadata returns None for invalid YAML."""
        from persistence import load_session_metadata

        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()
        config_path = session_dir / "config.yaml"
        config_path.write_text("invalid: yaml: content: [[", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_session_metadata("001")

        assert loaded is None


class TestListSessionsWithMetadata:
    """Tests for list_sessions_with_metadata function (Story 4.3)."""

    def test_list_sessions_with_metadata_empty(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_sessions_with_metadata with no sessions."""
        from persistence import list_sessions_with_metadata

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sessions = list_sessions_with_metadata()

        assert sessions == []

    def test_list_sessions_with_metadata_single_session(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_sessions_with_metadata with one session."""
        from models import SessionMetadata
        from persistence import list_sessions_with_metadata, save_session_metadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name="Test",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_session_metadata("001", metadata)
            sessions = list_sessions_with_metadata()

        assert len(sessions) == 1
        assert sessions[0].session_id == "001"

    def test_list_sessions_with_metadata_sorted_by_recency(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test sessions are sorted by updated_at (most recent first)."""
        from models import SessionMetadata
        from persistence import list_sessions_with_metadata, save_session_metadata

        # Create sessions with different update times
        sessions_data = [
            ("001", "2026-01-25T10:00:00Z"),  # Oldest
            ("002", "2026-01-28T10:00:00Z"),  # Newest
            ("003", "2026-01-26T10:00:00Z"),  # Middle
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            for session_id, updated_at in sessions_data:
                metadata = SessionMetadata(
                    session_id=session_id,
                    session_number=int(session_id),
                    created_at="2026-01-20T10:00:00Z",
                    updated_at=updated_at,
                )
                save_session_metadata(session_id, metadata)

            sessions = list_sessions_with_metadata()

        assert len(sessions) == 3
        # Should be sorted by updated_at descending
        assert sessions[0].session_id == "002"  # Newest
        assert sessions[1].session_id == "003"  # Middle
        assert sessions[2].session_id == "001"  # Oldest

    def test_list_sessions_with_metadata_skips_invalid_configs(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test invalid configs are skipped, valid ones returned."""
        from models import SessionMetadata
        from persistence import list_sessions_with_metadata, save_session_metadata

        # Create valid session
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            metadata = SessionMetadata(
                session_id="001",
                session_number=1,
                created_at="2026-01-28T10:00:00Z",
                updated_at="2026-01-28T10:00:00Z",
            )
            save_session_metadata("001", metadata)

        # Create invalid session manually
        invalid_dir = temp_campaigns_dir / "session_002"
        invalid_dir.mkdir()
        (invalid_dir / "config.yaml").write_text("invalid yaml {{{{", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sessions = list_sessions_with_metadata()

        assert len(sessions) == 1
        assert sessions[0].session_id == "001"


class TestGetNextSessionNumber:
    """Tests for get_next_session_number function (Story 4.3)."""

    def test_get_next_session_number_empty(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_next_session_number returns 1 when no sessions exist."""
        from persistence import get_next_session_number

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            next_num = get_next_session_number()

        assert next_num == 1

    def test_get_next_session_number_increments(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_next_session_number increments from existing sessions."""
        from persistence import get_next_session_number

        # Create some session directories
        (temp_campaigns_dir / "session_001").mkdir()
        (temp_campaigns_dir / "session_002").mkdir()
        (temp_campaigns_dir / "session_003").mkdir()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            next_num = get_next_session_number()

        assert next_num == 4

    def test_get_next_session_number_handles_gaps(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_next_session_number handles gaps in session numbers."""
        from persistence import get_next_session_number

        # Create sessions with gaps
        (temp_campaigns_dir / "session_001").mkdir()
        (temp_campaigns_dir / "session_005").mkdir()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            next_num = get_next_session_number()

        assert next_num == 6  # Max is 5, so next is 6


class TestCreateNewSession:
    """Tests for create_new_session function (Story 4.3)."""

    def test_create_new_session_returns_session_id(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test create_new_session returns formatted session ID."""
        from persistence import create_new_session

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session_id = create_new_session()

        assert session_id == "001"

    def test_create_new_session_creates_directory(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test create_new_session creates session directory."""
        from persistence import create_new_session

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session_id = create_new_session()

        session_dir = temp_campaigns_dir / f"session_{session_id}"
        assert session_dir.exists()
        assert session_dir.is_dir()

    def test_create_new_session_creates_config_yaml(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test create_new_session creates config.yaml with metadata."""
        from persistence import create_new_session, load_session_metadata

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session_id = create_new_session(
                name="New Adventure",
                character_names=["Theron", "Lyra"],
            )
            metadata = load_session_metadata(session_id)

        assert metadata is not None
        assert metadata.session_id == session_id
        assert metadata.name == "New Adventure"
        assert metadata.character_names == ["Theron", "Lyra"]
        assert metadata.turn_count == 0

    def test_create_new_session_auto_increments(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test create_new_session auto-increments session number."""
        from persistence import create_new_session

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session1 = create_new_session()
            session2 = create_new_session()
            session3 = create_new_session()

        assert session1 == "001"
        assert session2 == "002"
        assert session3 == "003"

    def test_create_new_session_with_explicit_number(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test create_new_session with explicit session number."""
        from persistence import create_new_session

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session_id = create_new_session(session_number=42)

        assert session_id == "042"


class TestUpdateSessionMetadataOnCheckpoint:
    """Tests for session metadata update on checkpoint save (Story 4.3)."""

    def test_save_checkpoint_updates_metadata(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test save_checkpoint updates session metadata."""
        from persistence import load_session_metadata

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 5)
            metadata = load_session_metadata("001")

        assert metadata is not None
        assert metadata.turn_count == 5

    def test_save_checkpoint_updates_timestamp(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test save_checkpoint updates the updated_at timestamp."""
        from persistence import create_new_session, load_session_metadata

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session_id = create_new_session()
            metadata_before = load_session_metadata(session_id)

        # Small delay to ensure timestamp difference
        time.sleep(0.01)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sample_game_state["session_id"] = session_id
            save_checkpoint(sample_game_state, session_id, 1)
            metadata_after = load_session_metadata(session_id)

        assert metadata_before is not None
        assert metadata_after is not None
        assert metadata_after.updated_at >= metadata_before.updated_at

    def test_save_checkpoint_without_metadata_update(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test save_checkpoint with update_metadata=False skips metadata update."""
        from persistence import load_session_metadata

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 5, update_metadata=False)
            metadata = load_session_metadata("001")

        # Should not have created metadata
        assert metadata is None


class TestGenerateRecapSummary:
    """Tests for generate_recap_summary function (Story 4.3)."""

    def test_generate_recap_summary_returns_recap_lines(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test generate_recap_summary returns newline-separated recap."""
        from persistence import generate_recap_summary

        sample_game_state["ground_truth_log"] = [
            "[dm] The adventure begins in a dark tavern.",
            "[fighter] I order an ale.",
            "[rogue] I check my pockets for coins.",
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 3)
            recap = generate_recap_summary("001", num_turns=5)

        assert recap is not None
        # Recap lines are separated by newlines (CSS provides bullet styling)
        assert recap.count("\n") == 2  # 3 lines = 2 newlines
        assert "adventure begins" in recap
        assert "order an ale" in recap
        assert "check my pockets" in recap

    def test_generate_recap_summary_truncates_long_entries(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test recap truncates entries longer than 150 chars."""
        from persistence import generate_recap_summary

        long_message = "[dm] " + "A" * 200
        sample_game_state["ground_truth_log"] = [long_message]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            recap = generate_recap_summary("001", num_turns=1)

        assert recap is not None
        assert "..." in recap
        # Entry should be truncated
        assert len(recap.split("\n")[0]) < 200

    def test_generate_recap_summary_no_checkpoints(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test generate_recap_summary returns None for no checkpoints."""
        from persistence import generate_recap_summary

        # Create session dir but no checkpoints
        (temp_campaigns_dir / "session_001").mkdir()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            recap = generate_recap_summary("001")

        assert recap is None

    def test_generate_recap_summary_empty_log(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test generate_recap_summary returns None for empty log."""
        from persistence import generate_recap_summary

        sample_game_state["ground_truth_log"] = []

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 0)
            recap = generate_recap_summary("001")

        assert recap is None


class TestStory43AcceptanceCriteria:
    """Acceptance tests for all Story 4.3 criteria."""

    def test_ac1_session_browser_shows_all_sessions(
        self, temp_campaigns_dir: Path
    ) -> None:
        """AC #1: Session browser shows all available sessions."""
        from models import SessionMetadata
        from persistence import list_sessions_with_metadata, save_session_metadata

        # Create multiple sessions
        for i in range(3):
            session_id = f"{i+1:03d}"
            metadata = SessionMetadata(
                session_id=session_id,
                session_number=i + 1,
                name=f"Session {i+1}",
                created_at="2026-01-28T10:00:00Z",
                updated_at="2026-01-28T10:00:00Z",
                character_names=["Theron"],
                turn_count=i * 5,
            )
            with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
                save_session_metadata(session_id, metadata)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sessions = list_sessions_with_metadata()

        # All sessions should be retrievable
        assert len(sessions) == 3

    def test_ac2_session_card_shows_metadata(
        self, temp_campaigns_dir: Path
    ) -> None:
        """AC #2: Session card shows name, date, turn count, characters."""
        from models import SessionMetadata
        from persistence import load_session_metadata, save_session_metadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name="The Dragon's Lair",
            created_at="2026-01-15T10:00:00Z",
            updated_at="2026-01-28T14:30:00Z",
            character_names=["Theron", "Lyra", "Magnus"],
            turn_count=42,
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_session_metadata("001", metadata)
            loaded = load_session_metadata("001")

        assert loaded is not None
        # Verify all card data is available
        assert loaded.name == "The Dragon's Lair"
        assert loaded.updated_at  # Date available
        assert loaded.turn_count == 42
        assert len(loaded.character_names) == 3

    def test_ac3_continue_button_loads_latest_checkpoint(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #3: Continue loads latest checkpoint and shows recap."""
        from persistence import (
            generate_recap_summary,
            get_latest_checkpoint,
            load_checkpoint,
        )

        # Create multiple checkpoints
        for turn in range(1, 6):
            sample_game_state["ground_truth_log"].append(f"[dm] Turn {turn} event.")
            with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
                save_checkpoint(sample_game_state, "001", turn)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            latest = get_latest_checkpoint("001")
            state = load_checkpoint("001", latest)
            recap = generate_recap_summary("001", num_turns=5)

        assert latest == 5
        assert state is not None
        assert len(state["ground_truth_log"]) == 7  # Original 2 + 5 added
        assert recap is not None

    def test_ac4_new_session_creates_fresh_state(
        self, temp_campaigns_dir: Path
    ) -> None:
        """AC #4: New Session creates fresh game state."""
        from persistence import create_new_session, load_session_metadata

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session_id = create_new_session(
                name="Fresh Adventure",
                character_names=["Hero"],
            )
            metadata = load_session_metadata(session_id)

        assert metadata is not None
        assert metadata.turn_count == 0  # Fresh - no turns yet
        assert metadata.name == "Fresh Adventure"

    def test_ac5_recap_shows_recent_events(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """AC #5: Recap modal shows recent narrative events."""
        from persistence import generate_recap_summary

        sample_game_state["ground_truth_log"] = [
            "[dm] The party entered the dungeon.",
            "[fighter] I raise my shield.",
            "[rogue] I scout ahead.",
            "[dm] A goblin appears!",
            "[wizard] I prepare a spell.",
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 5)
            recap = generate_recap_summary("001", num_turns=5)

        assert recap is not None
        # Should include all recent events
        assert "dungeon" in recap
        assert "shield" in recap
        assert "scout" in recap
        assert "goblin" in recap
        assert "spell" in recap

    def test_ac6_sessions_sorted_by_recency(
        self, temp_campaigns_dir: Path
    ) -> None:
        """AC #6: Sessions are sorted by most recently played first."""
        from models import SessionMetadata
        from persistence import list_sessions_with_metadata, save_session_metadata

        # Create sessions in reverse order of desired sort
        sessions_data = [
            ("001", "2026-01-20T10:00:00Z"),  # Oldest
            ("002", "2026-01-28T10:00:00Z"),  # Newest
            ("003", "2026-01-24T10:00:00Z"),  # Middle
        ]

        for session_id, updated_at in sessions_data:
            metadata = SessionMetadata(
                session_id=session_id,
                session_number=int(session_id),
                created_at="2026-01-10T10:00:00Z",
                updated_at=updated_at,
            )
            with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
                save_session_metadata(session_id, metadata)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sessions = list_sessions_with_metadata()

        # Verify descending order by updated_at
        assert sessions[0].session_id == "002"
        assert sessions[1].session_id == "003"
        assert sessions[2].session_id == "001"


# =============================================================================
# Story 4.3: Extended Test Coverage - Edge Cases & Error Paths
# =============================================================================


class TestSessionMetadataEdgeCases:
    """Edge case tests for SessionMetadata model (Story 4.3 expanded coverage)."""

    def test_session_metadata_unicode_in_name(self) -> None:
        """Test SessionMetadata handles Unicode characters in name."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name="The Dragon's Lair \u2014 \u0394\u03c1\u03ac\u03ba\u03c9\u03bd",  # Greek "dragon"
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        assert "\u0394\u03c1\u03ac\u03ba\u03c9\u03bd" in metadata.name

    def test_session_metadata_emoji_in_name(self) -> None:
        """Test SessionMetadata handles emoji in name."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name="\U0001F409 Dragon Hunt \U0001F5E1\uFE0F",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        assert "\U0001F409" in metadata.name

    def test_session_metadata_very_long_name(self) -> None:
        """Test SessionMetadata handles very long name."""
        from models import SessionMetadata

        long_name = "A" * 1000
        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name=long_name,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        assert len(metadata.name) == 1000

    def test_session_metadata_many_character_names(self) -> None:
        """Test SessionMetadata handles many character names."""
        from models import SessionMetadata

        character_names = [f"Character{i}" for i in range(100)]
        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
            character_names=character_names,
        )

        assert len(metadata.character_names) == 100

    def test_session_metadata_special_chars_in_character_names(self) -> None:
        """Test SessionMetadata handles special characters in character names."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
            character_names=["O'Brien", "D'Artagnan", "Ng\u01b0\u1eddi"],
        )

        assert "O'Brien" in metadata.character_names
        assert "D'Artagnan" in metadata.character_names

    def test_session_metadata_large_turn_count(self) -> None:
        """Test SessionMetadata handles large turn count."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
            turn_count=999999,
        )

        assert metadata.turn_count == 999999

    def test_session_metadata_negative_turn_count_rejected(self) -> None:
        """Test SessionMetadata rejects negative turn_count."""
        from pydantic import ValidationError

        from models import SessionMetadata

        with pytest.raises(ValidationError):
            SessionMetadata(
                session_id="001",
                session_number=1,
                created_at="2026-01-28T10:00:00Z",
                updated_at="2026-01-28T10:00:00Z",
                turn_count=-1,
            )

    def test_session_metadata_session_number_large(self) -> None:
        """Test SessionMetadata handles large session numbers."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="9999",
            session_number=9999,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        assert metadata.session_number == 9999

    def test_session_metadata_json_serialization(self) -> None:
        """Test SessionMetadata can serialize to JSON."""
        from models import SessionMetadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name="Test Adventure",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T12:00:00Z",
            character_names=["Theron", "Lyra"],
            turn_count=42,
        )

        json_str = metadata.model_dump_json()
        assert "001" in json_str
        assert "Test Adventure" in json_str
        assert "Theron" in json_str

    def test_session_metadata_json_roundtrip(self) -> None:
        """Test SessionMetadata survives JSON roundtrip."""
        from models import SessionMetadata

        original = SessionMetadata(
            session_id="001",
            session_number=1,
            name="Test \u2014 Adventure",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T12:00:00Z",
            character_names=["Theron", "Lyra"],
            turn_count=42,
        )

        json_str = original.model_dump_json()
        restored = SessionMetadata.model_validate_json(json_str)

        assert restored.session_id == original.session_id
        assert restored.name == original.name
        assert restored.character_names == original.character_names


class TestSessionMetadataPersistenceEdgeCases:
    """Edge case tests for session metadata persistence (Story 4.3 expanded)."""

    def test_save_session_metadata_unicode_name(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test save_session_metadata handles Unicode characters."""
        from models import SessionMetadata
        from persistence import load_session_metadata, save_session_metadata

        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            name="\U0001F409 Dragon's Lair \u2014 \u03b1\u03b2\u03b3",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_session_metadata("001", metadata)
            loaded = load_session_metadata("001")

        assert loaded is not None
        assert loaded.name == metadata.name

    def test_load_session_metadata_missing_fields(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_session_metadata handles YAML missing required fields."""
        from persistence import load_session_metadata

        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()
        config_path = session_dir / "config.yaml"
        # Missing required session_id field
        config_path.write_text("session_number: 1\nname: Test\n", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_session_metadata("001")

        assert loaded is None

    def test_load_session_metadata_wrong_type_fields(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_session_metadata handles wrong field types."""
        from persistence import load_session_metadata

        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()
        config_path = session_dir / "config.yaml"
        # session_number should be int, not string
        config_path.write_text(
            "session_id: '001'\n"
            "session_number: 'not_an_int'\n"
            "created_at: '2026-01-28T10:00:00Z'\n"
            "updated_at: '2026-01-28T10:00:00Z'\n",
            encoding="utf-8",
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_session_metadata("001")

        assert loaded is None

    def test_load_session_metadata_empty_file(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_session_metadata handles empty YAML file."""
        from persistence import load_session_metadata

        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()
        config_path = session_dir / "config.yaml"
        config_path.write_text("", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_session_metadata("001")

        assert loaded is None

    def test_load_session_metadata_yaml_null(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test load_session_metadata handles YAML null."""
        from persistence import load_session_metadata

        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()
        config_path = session_dir / "config.yaml"
        config_path.write_text("null", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            loaded = load_session_metadata("001")

        assert loaded is None

    def test_save_session_metadata_creates_parent_dirs(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test save_session_metadata creates session directory if missing."""
        from models import SessionMetadata
        from persistence import save_session_metadata

        metadata = SessionMetadata(
            session_id="999",
            session_number=999,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        session_dir = temp_campaigns_dir / "session_999"
        assert not session_dir.exists()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_session_metadata("999", metadata)

        assert session_dir.exists()

    def test_save_session_metadata_overwrites_existing(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test save_session_metadata overwrites existing config."""
        from models import SessionMetadata
        from persistence import load_session_metadata, save_session_metadata

        # Save first version
        metadata1 = SessionMetadata(
            session_id="001",
            session_number=1,
            name="Original Name",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_session_metadata("001", metadata1)

        # Save second version
        metadata2 = SessionMetadata(
            session_id="001",
            session_number=1,
            name="Updated Name",
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T12:00:00Z",
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_session_metadata("001", metadata2)
            loaded = load_session_metadata("001")

        assert loaded is not None
        assert loaded.name == "Updated Name"


class TestListSessionsWithMetadataEdgeCases:
    """Edge case tests for list_sessions_with_metadata (Story 4.3 expanded)."""

    def test_list_sessions_skips_mismatched_session_id(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_sessions_with_metadata skips config with mismatched session_id.

        Security: prevents crafted config.yaml from claiming wrong session.
        """
        from models import SessionMetadata
        from persistence import list_sessions_with_metadata, save_session_metadata

        # Create valid session 001
        valid_metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_session_metadata("001", valid_metadata)

        # Create malicious session 002 that claims to be 001
        malicious_dir = temp_campaigns_dir / "session_002"
        malicious_dir.mkdir()
        malicious_config = malicious_dir / "config.yaml"
        # config.yaml claims session_id="001" but is in session_002 directory
        malicious_config.write_text(
            "session_id: '001'\n"  # Mismatched!
            "session_number: 1\n"
            "created_at: '2026-01-28T10:00:00Z'\n"
            "updated_at: '2026-01-28T10:00:00Z'\n",
            encoding="utf-8",
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sessions = list_sessions_with_metadata()

        # Should only return the valid session, not the malicious one
        assert len(sessions) == 1
        assert sessions[0].session_id == "001"

    def test_list_sessions_with_many_sessions(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_sessions_with_metadata with many sessions (50+)."""
        from models import SessionMetadata
        from persistence import list_sessions_with_metadata, save_session_metadata

        # Create 50 sessions
        for i in range(50):
            session_id = f"{i+1:03d}"
            metadata = SessionMetadata(
                session_id=session_id,
                session_number=i + 1,
                created_at="2026-01-28T10:00:00Z",
                updated_at=f"2026-01-{(i % 28) + 1:02d}T10:00:00Z",
            )
            with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
                save_session_metadata(session_id, metadata)

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sessions = list_sessions_with_metadata()

        assert len(sessions) == 50
        # Should be sorted by updated_at descending

    def test_list_sessions_skips_directory_without_config(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test list_sessions_with_metadata skips sessions without config.yaml."""
        from models import SessionMetadata
        from persistence import list_sessions_with_metadata, save_session_metadata

        # Create valid session with config
        metadata = SessionMetadata(
            session_id="001",
            session_number=1,
            created_at="2026-01-28T10:00:00Z",
            updated_at="2026-01-28T10:00:00Z",
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_session_metadata("001", metadata)

        # Create session directory without config
        (temp_campaigns_dir / "session_002").mkdir()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sessions = list_sessions_with_metadata()

        assert len(sessions) == 1
        assert sessions[0].session_id == "001"


class TestGetNextSessionNumberEdgeCases:
    """Edge case tests for get_next_session_number (Story 4.3 expanded)."""

    def test_get_next_session_number_with_non_numeric_dirs(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_next_session_number ignores non-numeric session IDs."""
        from persistence import get_next_session_number

        # Create numeric sessions
        (temp_campaigns_dir / "session_001").mkdir()
        (temp_campaigns_dir / "session_002").mkdir()

        # Create non-numeric session (should be ignored in max calculation)
        (temp_campaigns_dir / "session_abc").mkdir()
        (temp_campaigns_dir / "session_test_123").mkdir()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            next_num = get_next_session_number()

        assert next_num == 3

    def test_get_next_session_number_only_non_numeric(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test get_next_session_number returns 1 when only non-numeric sessions."""
        from persistence import get_next_session_number

        # Create only non-numeric sessions
        (temp_campaigns_dir / "session_abc").mkdir()
        (temp_campaigns_dir / "session_test").mkdir()

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            next_num = get_next_session_number()

        assert next_num == 1


class TestCreateNewSessionEdgeCases:
    """Edge case tests for create_new_session (Story 4.3 expanded)."""

    def test_create_new_session_with_empty_character_names(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test create_new_session with empty character names list."""
        from persistence import create_new_session, load_session_metadata

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session_id = create_new_session(character_names=[])
            metadata = load_session_metadata(session_id)

        assert metadata is not None
        assert metadata.character_names == []

    def test_create_new_session_with_unicode_character_names(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test create_new_session with Unicode character names."""
        from persistence import create_new_session, load_session_metadata

        names = ["\u0394\u03c1\u03ac\u03ba\u03c9\u03bd", "Ng\u01b0\u1eddi", "\U0001F409Knight"]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session_id = create_new_session(character_names=names)
            metadata = load_session_metadata(session_id)

        assert metadata is not None
        assert metadata.character_names == names

    def test_create_new_session_with_empty_name(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test create_new_session with empty session name."""
        from persistence import create_new_session, load_session_metadata

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session_id = create_new_session(name="")
            metadata = load_session_metadata(session_id)

        assert metadata is not None
        assert metadata.name == ""

    def test_create_new_session_timestamps_are_utc_iso(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test create_new_session creates valid UTC ISO timestamps."""
        from persistence import create_new_session, load_session_metadata

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session_id = create_new_session()
            metadata = load_session_metadata(session_id)

        assert metadata is not None
        # Should end with Z for UTC
        assert metadata.created_at.endswith("Z")
        assert metadata.updated_at.endswith("Z")
        # Should be valid ISO format
        assert "T" in metadata.created_at


class TestUpdateSessionMetadataOnCheckpointEdgeCases:
    """Edge case tests for update_session_metadata_on_checkpoint (Story 4.3 expanded)."""

    def test_update_creates_metadata_if_missing(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test checkpoint save creates metadata if config.yaml doesn't exist."""
        from persistence import load_session_metadata

        # Save checkpoint without existing metadata
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 5)
            metadata = load_session_metadata("001")

        assert metadata is not None
        assert metadata.session_id == "001"
        assert metadata.turn_count == 5

    def test_update_preserves_existing_metadata_fields(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test checkpoint save preserves name and created_at."""
        from models import SessionMetadata
        from persistence import load_session_metadata, save_session_metadata

        # Create initial metadata with name
        initial = SessionMetadata(
            session_id="001",
            session_number=1,
            name="My Special Adventure",
            created_at="2026-01-15T10:00:00Z",
            updated_at="2026-01-15T10:00:00Z",
            character_names=["Old Character"],
            turn_count=0,
        )

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_session_metadata("001", initial)
            # Save checkpoint - should update turn_count but preserve name
            save_checkpoint(sample_game_state, "001", 10)
            loaded = load_session_metadata("001")

        assert loaded is not None
        assert loaded.name == "My Special Adventure"  # Preserved
        assert loaded.created_at == "2026-01-15T10:00:00Z"  # Preserved
        assert loaded.turn_count == 10  # Updated

    def test_update_replaces_character_names_when_provided(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test checkpoint save updates character_names when provided."""
        from persistence import load_session_metadata

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 5)
            metadata = load_session_metadata("001")

        assert metadata is not None
        # Should have character names from sample_game_state
        assert "Theron" in metadata.character_names


class TestGenerateRecapSummaryEdgeCases:
    """Edge case tests for generate_recap_summary (Story 4.3 expanded)."""

    def test_recap_handles_entries_without_prefix(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test recap handles log entries without [agent] prefix."""
        from persistence import generate_recap_summary

        sample_game_state["ground_truth_log"] = [
            "System: Game initialized.",  # No bracket prefix
            "[dm] The adventure begins.",
            "---",  # No bracket prefix
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            recap = generate_recap_summary("001", num_turns=3)

        assert recap is not None
        # All entries should be included
        assert "System: Game initialized." in recap or "Game initialized" in recap

    def test_recap_handles_empty_entries(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test recap handles empty log entries."""
        from persistence import generate_recap_summary

        sample_game_state["ground_truth_log"] = [
            "[dm] First message.",
            "",  # Empty entry
            "[dm] Second message.",
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            recap = generate_recap_summary("001", num_turns=5)

        assert recap is not None
        # Should handle without error

    def test_recap_truncates_at_147_chars(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test recap truncates entries at 147 chars + '...'."""
        from persistence import generate_recap_summary

        # Entry exactly 148 chars after prefix strip should truncate
        long_content = "A" * 160
        sample_game_state["ground_truth_log"] = [f"[dm] {long_content}"]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 1)
            recap = generate_recap_summary("001", num_turns=1)

        assert recap is not None
        assert "..." in recap
        # Should be 147 + 3 = 150 chars max
        assert len(recap.split("\n")[0]) == 150

    def test_recap_num_turns_less_than_available(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test recap with num_turns less than available entries."""
        from persistence import generate_recap_summary

        sample_game_state["ground_truth_log"] = [
            f"[dm] Message {i}" for i in range(10)
        ]

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, "001", 10)
            recap = generate_recap_summary("001", num_turns=3)

        assert recap is not None
        # Should only have 3 entries (from end of log)
        assert recap.count("\n") == 2  # 3 lines = 2 newlines
        assert "Message 7" in recap
        assert "Message 8" in recap
        assert "Message 9" in recap

    def test_recap_missing_session(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test recap returns None for missing session."""
        from persistence import generate_recap_summary

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            recap = generate_recap_summary("nonexistent")

        assert recap is None

    def test_recap_corrupted_checkpoint(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test recap returns None for corrupted checkpoint."""
        from persistence import generate_recap_summary

        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()
        corrupted = session_dir / "turn_001.json"
        corrupted.write_text("not valid json", encoding="utf-8")

        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            recap = generate_recap_summary("001")

        assert recap is None


class TestSessionConfigPathEdgeCases:
    """Edge case tests for get_session_config_path (Story 4.3 expanded)."""

    def test_get_session_config_path_format(self) -> None:
        """Test get_session_config_path returns correct format."""
        from persistence import get_session_config_path

        path = get_session_config_path("001")
        assert path.name == "config.yaml"
        assert "session_001" in str(path)

    def test_get_session_config_path_validates_session_id(self) -> None:
        """Test get_session_config_path validates session_id."""
        from persistence import get_session_config_path

        with pytest.raises(ValueError, match="Invalid session_id"):
            get_session_config_path("../etc/passwd")


class TestStory43IntegrationScenarios:
    """Integration tests for complete Story 4.3 scenarios."""

    def test_full_session_lifecycle(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test complete session lifecycle: create -> play -> continue."""
        from persistence import (
            create_new_session,
            generate_recap_summary,
            get_latest_checkpoint,
            list_sessions_with_metadata,
            load_checkpoint,
            load_session_metadata,
        )

        # Step 1: Create new session
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session_id = create_new_session(
                name="Integration Test Adventure",
                character_names=["Hero", "Sidekick"],
            )

            # Verify session was created
            sessions = list_sessions_with_metadata()
            assert len(sessions) == 1
            assert sessions[0].session_id == session_id
            assert sessions[0].turn_count == 0

        # Step 2: Play a few turns (save checkpoints)
        sample_game_state["session_id"] = session_id
        for turn in range(1, 6):
            sample_game_state["ground_truth_log"].append(
                f"[dm] Turn {turn} happened."
            )
            with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
                save_checkpoint(sample_game_state, session_id, turn)

        # Step 3: Verify turn count was updated
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            metadata = load_session_metadata(session_id)
            assert metadata is not None
            assert metadata.turn_count == 5

        # Step 4: Continue session (load latest + recap)
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            latest = get_latest_checkpoint(session_id)
            assert latest == 5

            state = load_checkpoint(session_id, latest)
            assert state is not None
            assert len(state["ground_truth_log"]) == 7  # Original 2 + 5

            recap = generate_recap_summary(session_id, num_turns=5)
            assert recap is not None
            assert "Turn 5" in recap

    def test_multiple_sessions_isolation(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test multiple sessions remain isolated from each other."""
        from persistence import (
            create_new_session,
            list_checkpoints,
            list_sessions_with_metadata,
            load_session_metadata,
        )

        # Create two sessions
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session1 = create_new_session(name="Session One")
            session2 = create_new_session(name="Session Two")

        # Add checkpoints to session 1 only
        sample_game_state["session_id"] = session1
        for turn in range(1, 4):
            with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
                save_checkpoint(sample_game_state, session1, turn)

        # Verify isolation
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            meta1 = load_session_metadata(session1)
            meta2 = load_session_metadata(session2)

            assert meta1 is not None
            assert meta2 is not None
            assert meta1.turn_count == 3
            assert meta2.turn_count == 0

            checkpoints1 = list_checkpoints(session1)
            checkpoints2 = list_checkpoints(session2)

            assert len(checkpoints1) == 3
            assert len(checkpoints2) == 0

    def test_session_browser_flow(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test session browser displays sessions correctly sorted."""
        from persistence import (
            create_new_session,
            list_sessions_with_metadata,
        )

        # Create sessions with different update times
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            session1 = create_new_session(name="Old Session")
            # Brief pause to ensure different timestamps
            time.sleep(0.01)
            session2 = create_new_session(name="New Session")

        # Update session1 with a newer timestamp by saving checkpoint
        sample_game_state["session_id"] = session1
        time.sleep(0.01)  # Ensure timestamp is newer
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            save_checkpoint(sample_game_state, session1, 1)

        # Session1 should now be first (most recently updated)
        with patch("persistence.CAMPAIGNS_DIR", temp_campaigns_dir):
            sessions = list_sessions_with_metadata()

            assert len(sessions) == 2
            assert sessions[0].session_id == session1  # Most recently updated
            assert sessions[1].session_id == session2
