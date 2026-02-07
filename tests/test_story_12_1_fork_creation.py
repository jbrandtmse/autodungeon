"""Tests for Story 12.1: Fork Creation.

Tests for ForkMetadata, ForkRegistry models, active_fork_id on GameState,
fork persistence functions, and serialization backward compatibility.
"""

import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from models import ForkMetadata, ForkRegistry, GameState, create_initial_game_state
from persistence import (
    create_fork,
    deserialize_game_state,
    ensure_fork_dir,
    get_fork_dir,
    get_fork_registry_path,
    list_forks,
    load_checkpoint,
    load_fork_registry,
    save_checkpoint,
    save_fork_registry,
    serialize_game_state,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_campaigns_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary campaigns directory for testing."""
    temp_campaigns = tmp_path / "campaigns"
    temp_campaigns.mkdir()
    with patch("persistence.CAMPAIGNS_DIR", temp_campaigns):
        yield temp_campaigns


@pytest.fixture
def sample_game_state() -> GameState:
    """Create a sample GameState for testing."""
    return create_initial_game_state()


# =============================================================================
# Task 23: Test ForkMetadata model validation
# =============================================================================


class TestForkMetadata:
    """Tests for ForkMetadata Pydantic model."""

    def test_valid_construction(self) -> None:
        """Valid construction with all required fields."""
        fork = ForkMetadata(
            fork_id="001",
            name="Fight the dragon",
            parent_session_id="001",
            branch_turn=5,
            created_at="2026-02-07T12:00:00Z",
            updated_at="2026-02-07T12:00:00Z",
        )
        assert fork.fork_id == "001"
        assert fork.name == "Fight the dragon"
        assert fork.parent_session_id == "001"
        assert fork.branch_turn == 5
        assert fork.turn_count == 0

    def test_default_turn_count(self) -> None:
        """Default turn_count is 0."""
        fork = ForkMetadata(
            fork_id="001",
            name="Test",
            parent_session_id="001",
            branch_turn=0,
            created_at="2026-02-07T12:00:00Z",
            updated_at="2026-02-07T12:00:00Z",
        )
        assert fork.turn_count == 0

    def test_empty_name_rejected(self) -> None:
        """Empty name is rejected (min_length=1)."""
        with pytest.raises(ValidationError):
            ForkMetadata(
                fork_id="001",
                name="",
                parent_session_id="001",
                branch_turn=0,
                created_at="2026-02-07T12:00:00Z",
                updated_at="2026-02-07T12:00:00Z",
            )

    def test_whitespace_name_rejected(self) -> None:
        """Whitespace-only name is rejected by validator."""
        with pytest.raises(ValidationError, match="whitespace"):
            ForkMetadata(
                fork_id="001",
                name="   ",
                parent_session_id="001",
                branch_turn=0,
                created_at="2026-02-07T12:00:00Z",
                updated_at="2026-02-07T12:00:00Z",
            )

    def test_fork_id_min_length(self) -> None:
        """fork_id must have min_length=1."""
        with pytest.raises(ValidationError):
            ForkMetadata(
                fork_id="",
                name="Test",
                parent_session_id="001",
                branch_turn=0,
                created_at="2026-02-07T12:00:00Z",
                updated_at="2026-02-07T12:00:00Z",
            )

    def test_branch_turn_ge_zero(self) -> None:
        """branch_turn must be >= 0."""
        with pytest.raises(ValidationError):
            ForkMetadata(
                fork_id="001",
                name="Test",
                parent_session_id="001",
                branch_turn=-1,
                created_at="2026-02-07T12:00:00Z",
                updated_at="2026-02-07T12:00:00Z",
            )

    def test_turn_count_ge_zero(self) -> None:
        """turn_count must be >= 0."""
        with pytest.raises(ValidationError):
            ForkMetadata(
                fork_id="001",
                name="Test",
                parent_session_id="001",
                branch_turn=0,
                created_at="2026-02-07T12:00:00Z",
                updated_at="2026-02-07T12:00:00Z",
                turn_count=-1,
            )


# =============================================================================
# Task 24: Test ForkRegistry model and methods
# =============================================================================


class TestForkRegistry:
    """Tests for ForkRegistry Pydantic model and methods."""

    def _make_fork(self, fork_id: str = "001", branch_turn: int = 1) -> ForkMetadata:
        """Helper to create a ForkMetadata for testing."""
        return ForkMetadata(
            fork_id=fork_id,
            name=f"Fork {fork_id}",
            parent_session_id="001",
            branch_turn=branch_turn,
            created_at="2026-02-07T12:00:00Z",
            updated_at="2026-02-07T12:00:00Z",
        )

    def test_get_fork_found(self) -> None:
        """get_fork() returns correct fork by ID."""
        fork = self._make_fork("001")
        registry = ForkRegistry(session_id="001", forks=[fork])
        result = registry.get_fork("001")
        assert result is not None
        assert result.fork_id == "001"

    def test_get_fork_not_found(self) -> None:
        """get_fork() returns None for missing ID."""
        registry = ForkRegistry(session_id="001", forks=[])
        assert registry.get_fork("999") is None

    def test_get_forks_at_turn(self) -> None:
        """get_forks_at_turn() filters forks by branch turn."""
        f1 = self._make_fork("001", branch_turn=3)
        f2 = self._make_fork("002", branch_turn=5)
        f3 = self._make_fork("003", branch_turn=3)
        registry = ForkRegistry(session_id="001", forks=[f1, f2, f3])

        result = registry.get_forks_at_turn(3)
        assert len(result) == 2
        assert all(f.branch_turn == 3 for f in result)

    def test_get_forks_at_turn_none(self) -> None:
        """get_forks_at_turn() returns empty list when no forks at that turn."""
        registry = ForkRegistry(session_id="001", forks=[])
        assert registry.get_forks_at_turn(5) == []

    def test_next_fork_id_empty(self) -> None:
        """next_fork_id() returns '001' for empty registry."""
        registry = ForkRegistry(session_id="001")
        assert registry.next_fork_id() == "001"

    def test_next_fork_id_after_one(self) -> None:
        """next_fork_id() returns '002' after one fork."""
        f1 = self._make_fork("001")
        registry = ForkRegistry(session_id="001", forks=[f1])
        assert registry.next_fork_id() == "002"

    def test_next_fork_id_sequential(self) -> None:
        """next_fork_id() returns sequential IDs."""
        f1 = self._make_fork("001")
        f2 = self._make_fork("002")
        f3 = self._make_fork("003")
        registry = ForkRegistry(session_id="001", forks=[f1, f2, f3])
        assert registry.next_fork_id() == "004"

    def test_add_fork(self) -> None:
        """add_fork() appends to forks list."""
        registry = ForkRegistry(session_id="001")
        assert len(registry.forks) == 0
        fork = self._make_fork("001")
        registry.add_fork(fork)
        assert len(registry.forks) == 1
        assert registry.forks[0].fork_id == "001"

    def test_empty_registry_queries(self) -> None:
        """Empty registry returns empty lists for queries."""
        registry = ForkRegistry(session_id="001")
        assert registry.get_fork("001") is None
        assert registry.get_forks_at_turn(1) == []
        assert registry.next_fork_id() == "001"


# =============================================================================
# Task 25: Test active_fork_id on GameState
# =============================================================================


class TestActiveForkId:
    """Tests for active_fork_id on GameState."""

    def test_create_initial_game_state_has_none(self) -> None:
        """create_initial_game_state() has active_fork_id=None."""
        state = create_initial_game_state()
        assert state["active_fork_id"] is None

    def test_populate_game_state_has_none(self) -> None:
        """populate_game_state() has active_fork_id=None."""
        from models import populate_game_state

        state = populate_game_state(include_sample_messages=False)
        assert state["active_fork_id"] is None

    def test_serialization_roundtrip_none(self) -> None:
        """Serialization round-trip preserves active_fork_id=None."""
        state = create_initial_game_state()
        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)
        assert restored["active_fork_id"] is None

    def test_serialization_roundtrip_with_fork_id(self) -> None:
        """Serialization round-trip preserves active_fork_id='001'."""
        state = create_initial_game_state()
        state["active_fork_id"] = "001"
        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)
        assert restored["active_fork_id"] == "001"

    def test_backward_compatibility_no_active_fork_id(self) -> None:
        """Old checkpoint without active_fork_id deserializes to None."""
        state = create_initial_game_state()
        json_str = serialize_game_state(state)
        # Remove active_fork_id from JSON to simulate old checkpoint
        data = json.loads(json_str)
        data.pop("active_fork_id", None)
        old_json = json.dumps(data)
        restored = deserialize_game_state(old_json)
        assert restored["active_fork_id"] is None


# =============================================================================
# Task 26: Test _validate_fork_id() helper
# =============================================================================


class TestValidateForkId:
    """Tests for _validate_fork_id() helper."""

    def test_valid_ids(self) -> None:
        """Valid IDs pass validation."""
        from persistence import _validate_fork_id

        # Should not raise
        _validate_fork_id("001")
        _validate_fork_id("002")
        _validate_fork_id("abc_123")
        _validate_fork_id("test")

    def test_path_traversal_rejected(self) -> None:
        """Path traversal patterns rejected."""
        from persistence import _validate_fork_id

        with pytest.raises(ValueError, match="Invalid fork_id"):
            _validate_fork_id("../etc")

        with pytest.raises(ValueError, match="Invalid fork_id"):
            _validate_fork_id("..")

        with pytest.raises(ValueError, match="Invalid fork_id"):
            _validate_fork_id("")

    def test_special_characters_rejected(self) -> None:
        """Special characters rejected."""
        from persistence import _validate_fork_id

        with pytest.raises(ValueError, match="Invalid fork_id"):
            _validate_fork_id("foo/bar")

        with pytest.raises(ValueError, match="Invalid fork_id"):
            _validate_fork_id("foo bar")


# =============================================================================
# Task 27: Test get_fork_dir() path construction
# =============================================================================


class TestGetForkDir:
    """Tests for get_fork_dir() path construction."""

    def test_correct_path(self, temp_campaigns_dir: Path) -> None:
        """Returns correct path structure."""
        fork_dir = get_fork_dir("001", "001")
        expected = temp_campaigns_dir / "session_001" / "forks" / "fork_001"
        assert fork_dir == expected

    def test_validates_session_id(self) -> None:
        """Validates session_id."""
        with pytest.raises(ValueError, match="Invalid session_id"):
            get_fork_dir("../bad", "001")

    def test_validates_fork_id(self, temp_campaigns_dir: Path) -> None:
        """Validates fork_id."""
        with pytest.raises(ValueError, match="Invalid fork_id"):
            get_fork_dir("001", "../bad")


# =============================================================================
# Task 28: Test ensure_fork_dir() directory creation
# =============================================================================


class TestEnsureForkDir:
    """Tests for ensure_fork_dir() directory creation."""

    def test_creates_directory(self, temp_campaigns_dir: Path) -> None:
        """Creates directory if it doesn't exist."""
        fork_dir = ensure_fork_dir("001", "001")
        assert fork_dir.exists()
        assert fork_dir.is_dir()

    def test_no_error_if_exists(self, temp_campaigns_dir: Path) -> None:
        """No error if directory already exists."""
        ensure_fork_dir("001", "001")
        # Call again - should not raise
        fork_dir = ensure_fork_dir("001", "001")
        assert fork_dir.exists()

    def test_creates_intermediate_forks_dir(self, temp_campaigns_dir: Path) -> None:
        """Creates intermediate forks/ parent directory."""
        fork_dir = ensure_fork_dir("001", "001")
        forks_parent = fork_dir.parent
        assert forks_parent.name == "forks"
        assert forks_parent.exists()


# =============================================================================
# Task 29: Test save_fork_registry() / load_fork_registry() round-trip
# =============================================================================


class TestForkRegistryPersistence:
    """Tests for save_fork_registry() / load_fork_registry()."""

    def _make_fork(self, fork_id: str = "001") -> ForkMetadata:
        return ForkMetadata(
            fork_id=fork_id,
            name=f"Fork {fork_id}",
            parent_session_id="001",
            branch_turn=3,
            created_at="2026-02-07T12:00:00Z",
            updated_at="2026-02-07T12:00:00Z",
            turn_count=0,
        )

    def test_save_and_load_roundtrip(self, temp_campaigns_dir: Path) -> None:
        """Save and load preserves all ForkMetadata fields."""
        fork = self._make_fork("001")
        registry = ForkRegistry(session_id="001", forks=[fork])
        save_fork_registry("001", registry)

        loaded = load_fork_registry("001")
        assert loaded is not None
        assert loaded.session_id == "001"
        assert len(loaded.forks) == 1
        assert loaded.forks[0].fork_id == "001"
        assert loaded.forks[0].name == "Fork 001"
        assert loaded.forks[0].parent_session_id == "001"
        assert loaded.forks[0].branch_turn == 3
        assert loaded.forks[0].turn_count == 0

    def test_load_missing_file_returns_none(self, temp_campaigns_dir: Path) -> None:
        """Load returns None for missing file."""
        from persistence import ensure_session_dir

        ensure_session_dir("001")
        result = load_fork_registry("001")
        assert result is None

    def test_load_invalid_yaml_returns_none(self, temp_campaigns_dir: Path) -> None:
        """Load returns None for invalid YAML."""
        from persistence import ensure_session_dir

        ensure_session_dir("001")
        registry_path = get_fork_registry_path("001")
        registry_path.write_text("{{invalid yaml: [", encoding="utf-8")
        result = load_fork_registry("001")
        assert result is None

    def test_load_invalid_schema_returns_none(self, temp_campaigns_dir: Path) -> None:
        """Load returns None for invalid schema (ValidationError)."""
        from persistence import ensure_session_dir

        ensure_session_dir("001")
        registry_path = get_fork_registry_path("001")
        # Valid YAML but invalid schema (missing required fields)
        registry_path.write_text("foo: bar\n", encoding="utf-8")
        result = load_fork_registry("001")
        assert result is None


# =============================================================================
# Task 30: Test create_fork() function
# =============================================================================


class TestCreateFork:
    """Tests for create_fork() function."""

    def test_basic_fork_creation(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Creates fork directory under forks/fork_001/."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        fork = create_fork(
            state=sample_game_state,
            session_id=session_id,
            fork_name="Fight the dragon",
        )

        assert fork.fork_id == "001"
        assert fork.name == "Fight the dragon"
        assert fork.branch_turn == 1
        assert fork.parent_session_id == session_id

        # Verify fork directory exists
        fork_dir = get_fork_dir(session_id, "001")
        assert fork_dir.exists()

    def test_fork_copies_checkpoint(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Copies branch point checkpoint into fork directory."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        create_fork(
            state=sample_game_state,
            session_id=session_id,
            fork_name="Test fork",
        )

        fork_dir = get_fork_dir(session_id, "001")
        fork_checkpoint = fork_dir / "turn_001.json"
        assert fork_checkpoint.exists()

    def test_fork_checkpoint_is_valid(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Fork checkpoint is a valid, loadable GameState."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        create_fork(
            state=sample_game_state,
            session_id=session_id,
            fork_name="Test fork",
        )

        fork_dir = get_fork_dir(session_id, "001")
        fork_checkpoint = fork_dir / "turn_001.json"
        json_content = fork_checkpoint.read_text(encoding="utf-8")
        restored = deserialize_game_state(json_content)
        assert restored["current_turn"] == sample_game_state["current_turn"]

    def test_fork_metadata_correct(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """ForkMetadata has correct fields (name, branch_turn, timestamps)."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        fork = create_fork(
            state=sample_game_state,
            session_id=session_id,
            fork_name="Diplomacy attempt",
        )

        assert fork.name == "Diplomacy attempt"
        assert fork.branch_turn == 1
        assert fork.created_at.endswith("Z")
        assert fork.updated_at.endswith("Z")
        assert fork.turn_count == 0

    def test_registry_updated(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Registry is updated with new fork."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        create_fork(
            state=sample_game_state,
            session_id=session_id,
            fork_name="Test",
        )

        registry = load_fork_registry(session_id)
        assert registry is not None
        assert len(registry.forks) == 1
        assert registry.forks[0].name == "Test"

    def test_multiple_forks_sequential_ids(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Multiple forks get sequential IDs: '001', '002', '003'."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        f1 = create_fork(sample_game_state, session_id, "Fork A")
        f2 = create_fork(sample_game_state, session_id, "Fork B")
        f3 = create_fork(sample_game_state, session_id, "Fork C")

        assert f1.fork_id == "001"
        assert f2.fork_id == "002"
        assert f3.fork_id == "003"

    def test_error_empty_name(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Error on empty fork name."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        with pytest.raises(ValueError, match="empty"):
            create_fork(sample_game_state, session_id, "")

    def test_error_whitespace_name(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Error on whitespace-only fork name."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        with pytest.raises(ValueError, match="empty"):
            create_fork(sample_game_state, session_id, "   ")

    def test_error_no_checkpoints(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Error on session with no checkpoints."""
        from persistence import ensure_session_dir

        session_id = "001"
        ensure_session_dir(session_id)

        with pytest.raises(ValueError, match="no checkpoints"):
            create_fork(sample_game_state, session_id, "Test fork")

    def test_fork_from_specific_turn(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Fork from specific turn number (not just latest)."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)
        sample_game_state["ground_truth_log"].append("[dm] Turn 2 content")
        save_checkpoint(sample_game_state, session_id, 2)

        # Fork from turn 1, not the latest (turn 2)
        fork = create_fork(
            sample_game_state, session_id, "From turn 1", turn_number=1
        )

        assert fork.branch_turn == 1
        fork_dir = get_fork_dir(session_id, "001")
        fork_checkpoint = fork_dir / "turn_001.json"
        assert fork_checkpoint.exists()

    def test_original_session_unmodified(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Original session files are not modified (main timeline unaffected)."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        # Record original checkpoint content
        from persistence import get_checkpoint_path

        original_path = get_checkpoint_path(session_id, 1)
        original_content = original_path.read_text(encoding="utf-8")

        create_fork(sample_game_state, session_id, "Test fork")

        # Verify original checkpoint unchanged
        assert original_path.read_text(encoding="utf-8") == original_content


# =============================================================================
# Task 31: Test list_forks() function
# =============================================================================


class TestListForks:
    """Tests for list_forks() function."""

    def test_empty_list_no_forks(self, temp_campaigns_dir: Path) -> None:
        """Returns empty list for session with no forks."""
        from persistence import ensure_session_dir

        ensure_session_dir("001")
        assert list_forks("001") == []

    def test_returns_sorted_forks(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Returns all forks sorted by creation time."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        create_fork(sample_game_state, session_id, "First fork")
        create_fork(sample_game_state, session_id, "Second fork")

        forks = list_forks(session_id)
        assert len(forks) == 2
        assert forks[0].name == "First fork"
        assert forks[1].name == "Second fork"
        assert forks[0].created_at <= forks[1].created_at

    def test_empty_list_nonexistent_session(self, temp_campaigns_dir: Path) -> None:
        """Returns empty list for non-existent session."""
        assert list_forks("999") == []


# =============================================================================
# Task 32: Test serialization backward compatibility
# =============================================================================


class TestSerializationBackwardCompat:
    """Tests for serialization backward compatibility."""

    def test_old_checkpoint_no_active_fork_id(self) -> None:
        """Deserializing old checkpoint yields active_fork_id=None."""
        state = create_initial_game_state()
        json_str = serialize_game_state(state)
        data = json.loads(json_str)
        del data["active_fork_id"]
        old_json = json.dumps(data)
        restored = deserialize_game_state(old_json)
        assert restored["active_fork_id"] is None

    def test_serialize_with_none_produces_valid_json(self) -> None:
        """Serializing state with active_fork_id=None produces valid JSON."""
        state = create_initial_game_state()
        json_str = serialize_game_state(state)
        data = json.loads(json_str)
        assert "active_fork_id" in data
        assert data["active_fork_id"] is None

    def test_roundtrip_with_fork_id_set(self) -> None:
        """Serializing state with active_fork_id='001' round-trips correctly."""
        state = create_initial_game_state()
        state["active_fork_id"] = "001"
        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)
        assert restored["active_fork_id"] == "001"


# =============================================================================
# Task 33: Test fork isolation
# =============================================================================


class TestForkIsolation:
    """Tests for fork isolation."""

    def test_fork_does_not_modify_main_timeline(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Creating a fork does not modify the main timeline's checkpoints."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        from persistence import get_checkpoint_path

        original_path = get_checkpoint_path(session_id, 1)
        original_content = original_path.read_text(encoding="utf-8")

        create_fork(sample_game_state, session_id, "Test fork")

        # Main timeline checkpoint should be identical
        assert original_path.read_text(encoding="utf-8") == original_content

    def test_main_session_continues_normally(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Main session continues saving checkpoints normally after fork creation."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        create_fork(sample_game_state, session_id, "Test fork")

        # Save another checkpoint on main timeline
        sample_game_state["ground_truth_log"].append("[dm] The story continues")
        save_checkpoint(sample_game_state, session_id, 2)

        # Verify main timeline has both checkpoints
        restored = load_checkpoint(session_id, 2)
        assert restored is not None
        assert "[dm] The story continues" in restored["ground_truth_log"]

    def test_fork_checkpoint_is_independent_copy(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Fork checkpoint is an independent copy (modifying it does not affect source)."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)

        create_fork(sample_game_state, session_id, "Test fork")

        # Modify the fork's checkpoint file
        fork_dir = get_fork_dir(session_id, "001")
        fork_checkpoint = fork_dir / "turn_001.json"
        fork_data = json.loads(fork_checkpoint.read_text(encoding="utf-8"))
        fork_data["ground_truth_log"].append("[dm] Fork-only content")
        fork_checkpoint.write_text(json.dumps(fork_data), encoding="utf-8")

        # Verify original checkpoint is unaffected
        original = load_checkpoint(session_id, 1)
        assert original is not None
        assert "[dm] Fork-only content" not in original["ground_truth_log"]
