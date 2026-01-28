"""Tests for persistence module - checkpoint save/load functionality.

Story 4.1: Auto-Checkpoint System
Tests for path utilities, serialization, save/load, and listing functions.
"""

import json
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
