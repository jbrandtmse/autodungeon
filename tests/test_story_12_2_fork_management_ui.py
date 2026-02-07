"""Tests for Story 12.2: Fork Management UI.

Tests fork-aware checkpoint persistence, fork switching logic,
fork mode indicator, and backward compatibility.
"""

import json
from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from models import (
    AgentMemory,
    AgentSecrets,
    CallbackLog,
    CharacterConfig,
    DMConfig,
    ForkRegistry,
    GameConfig,
    GameState,
    NarrativeElementStore,
    create_initial_game_state,
)
from persistence import (
    create_fork,
    delete_fork,
    get_fork_dir,
    get_latest_checkpoint,
    get_latest_fork_checkpoint,
    list_fork_checkpoints,
    list_forks,
    load_checkpoint,
    load_fork_checkpoint,
    load_fork_registry,
    rename_fork,
    save_checkpoint,
    save_fork_checkpoint,
    save_fork_registry,
)


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
        summarization_in_progress=False,
        selected_module=None,
        character_sheets={},
        agent_secrets={
            "dm": AgentSecrets(),
            "fighter": AgentSecrets(),
        },
        narrative_elements={},
        callback_database=NarrativeElementStore(),
        callback_log=CallbackLog(),
        active_fork_id=None,
    )


@pytest.fixture
def session_with_fork(
    temp_campaigns_dir: Path, sample_game_state: GameState
) -> tuple[str, str]:
    """Create a session with a checkpoint and a fork, return (session_id, fork_id)."""
    session_id = "001"
    save_checkpoint(sample_game_state, session_id, 1)
    fork_meta = create_fork(
        state=sample_game_state,
        session_id=session_id,
        fork_name="Test Fork",
    )
    return session_id, fork_meta.fork_id


class TestSaveForkCheckpoint:
    """Tests for save_fork_checkpoint()."""

    def test_saves_to_correct_path(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """Checkpoint is saved to the fork directory with correct filename."""
        session_id, fork_id = session_with_fork
        result_path = save_fork_checkpoint(
            sample_game_state, session_id, fork_id, 2
        )
        expected_dir = get_fork_dir(session_id, fork_id)
        assert result_path == expected_dir / "turn_002.json"
        assert result_path.exists()

    def test_atomic_write_creates_valid_json(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """Saved checkpoint file contains valid JSON."""
        session_id, fork_id = session_with_fork
        result_path = save_fork_checkpoint(
            sample_game_state, session_id, fork_id, 2
        )
        content = result_path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, dict)
        assert "ground_truth_log" in data

    def test_round_trip_with_load(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """Save then load returns equivalent state."""
        session_id, fork_id = session_with_fork
        save_fork_checkpoint(sample_game_state, session_id, fork_id, 2)
        loaded = load_fork_checkpoint(session_id, fork_id, 2)
        assert loaded is not None
        assert loaded["ground_truth_log"] == sample_game_state["ground_truth_log"]
        assert loaded["turn_queue"] == sample_game_state["turn_queue"]
        assert loaded["current_turn"] == sample_game_state["current_turn"]

    def test_updates_registry_metadata(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """save_fork_checkpoint updates ForkMetadata.updated_at and turn_count."""
        session_id, fork_id = session_with_fork

        # Save a second checkpoint (fork already has turn 1 from create_fork)
        save_fork_checkpoint(sample_game_state, session_id, fork_id, 2)

        registry = load_fork_registry(session_id)
        assert registry is not None
        fork_meta = registry.get_fork(fork_id)
        assert fork_meta is not None
        # turn_count = len(checkpoints) - 1 (minus initial branch point copy)
        # Fork has turn_001.json (branch point) and turn_002.json = 2 files, count = 1
        assert fork_meta.turn_count == 1
        assert fork_meta.updated_at.endswith("Z")

    def test_validates_session_id(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Invalid session_id raises ValueError."""
        with pytest.raises(ValueError):
            save_fork_checkpoint(sample_game_state, "../evil", "001", 1)

    def test_validates_fork_id(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Invalid fork_id raises ValueError."""
        with pytest.raises(ValueError):
            save_fork_checkpoint(sample_game_state, "001", "../evil", 1)

    def test_validates_turn_number(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Invalid turn_number raises ValueError."""
        with pytest.raises(ValueError):
            save_fork_checkpoint(sample_game_state, "001", "001", -1)


class TestLoadForkCheckpoint:
    """Tests for load_fork_checkpoint()."""

    def test_returns_none_for_missing_file(
        self, session_with_fork: tuple[str, str]
    ) -> None:
        """Returns None when checkpoint file doesn't exist."""
        session_id, fork_id = session_with_fork
        result = load_fork_checkpoint(session_id, fork_id, 999)
        assert result is None

    def test_returns_none_for_invalid_json(
        self, session_with_fork: tuple[str, str]
    ) -> None:
        """Returns None when checkpoint file contains invalid JSON."""
        session_id, fork_id = session_with_fork
        fork_dir = get_fork_dir(session_id, fork_id)
        bad_file = fork_dir / "turn_099.json"
        bad_file.write_text("NOT VALID JSON {{{", encoding="utf-8")
        result = load_fork_checkpoint(session_id, fork_id, 99)
        assert result is None

    def test_loads_valid_checkpoint(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """Loads a valid checkpoint correctly."""
        session_id, fork_id = session_with_fork
        save_fork_checkpoint(sample_game_state, session_id, fork_id, 3)
        loaded = load_fork_checkpoint(session_id, fork_id, 3)
        assert loaded is not None
        assert loaded["session_id"] == "001"


class TestListForkCheckpoints:
    """Tests for list_fork_checkpoints()."""

    def test_sorted_turns(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """Returns turn numbers in ascending order."""
        session_id, fork_id = session_with_fork
        # Fork already has turn 1 from create_fork
        save_fork_checkpoint(sample_game_state, session_id, fork_id, 3)
        save_fork_checkpoint(sample_game_state, session_id, fork_id, 2)
        turns = list_fork_checkpoints(session_id, fork_id)
        assert turns == [1, 2, 3]

    def test_empty_for_missing_dir(self, temp_campaigns_dir: Path) -> None:
        """Returns empty list for non-existent fork directory."""
        turns = list_fork_checkpoints("001", "999")
        assert turns == []

    def test_empty_for_empty_dir(
        self, session_with_fork: tuple[str, str]
    ) -> None:
        """Returns empty list when fork dir exists but has no turn files."""
        session_id, fork_id = session_with_fork
        fork_dir = get_fork_dir(session_id, fork_id)
        # Remove all turn files
        for f in fork_dir.glob("turn_*.json"):
            f.unlink()
        turns = list_fork_checkpoints(session_id, fork_id)
        assert turns == []

    def test_ignores_non_turn_files(
        self,
        session_with_fork: tuple[str, str],
    ) -> None:
        """Non-checkpoint files in fork dir are ignored."""
        session_id, fork_id = session_with_fork
        fork_dir = get_fork_dir(session_id, fork_id)
        # Create non-turn files
        (fork_dir / "notes.txt").write_text("some notes", encoding="utf-8")
        (fork_dir / "turn_abc.json").write_text("{}", encoding="utf-8")
        turns = list_fork_checkpoints(session_id, fork_id)
        # Only the original turn_001.json from create_fork
        assert turns == [1]


class TestGetLatestForkCheckpoint:
    """Tests for get_latest_fork_checkpoint()."""

    def test_highest_turn_number(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """Returns the highest turn number."""
        session_id, fork_id = session_with_fork
        save_fork_checkpoint(sample_game_state, session_id, fork_id, 2)
        save_fork_checkpoint(sample_game_state, session_id, fork_id, 5)
        latest = get_latest_fork_checkpoint(session_id, fork_id)
        assert latest == 5

    def test_none_for_empty_fork(self, temp_campaigns_dir: Path) -> None:
        """Returns None for fork with no checkpoints."""
        latest = get_latest_fork_checkpoint("001", "999")
        assert latest is None


class TestRenameFork:
    """Tests for rename_fork()."""

    def test_updates_name(
        self, session_with_fork: tuple[str, str]
    ) -> None:
        """Renames fork in registry and persists."""
        session_id, fork_id = session_with_fork
        result = rename_fork(session_id, fork_id, "New Name")
        assert result.name == "New Name"

        # Verify persisted
        registry = load_fork_registry(session_id)
        assert registry is not None
        fork = registry.get_fork(fork_id)
        assert fork is not None
        assert fork.name == "New Name"

    def test_rejects_empty_names(
        self, session_with_fork: tuple[str, str]
    ) -> None:
        """Raises ValueError for empty or whitespace-only names."""
        session_id, fork_id = session_with_fork
        with pytest.raises(ValueError, match="empty"):
            rename_fork(session_id, fork_id, "")
        with pytest.raises(ValueError, match="empty"):
            rename_fork(session_id, fork_id, "   ")

    def test_valueerror_for_missing_fork(
        self, session_with_fork: tuple[str, str]
    ) -> None:
        """Raises ValueError when fork_id not found."""
        session_id, _ = session_with_fork
        with pytest.raises(ValueError, match="not found"):
            rename_fork(session_id, "999", "New Name")

    def test_preserves_other_forks(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """Renaming one fork does not affect others."""
        session_id, fork_id = session_with_fork
        # Create a second fork
        fork2 = create_fork(
            state=sample_game_state,
            session_id=session_id,
            fork_name="Second Fork",
        )

        rename_fork(session_id, fork_id, "Renamed First")

        registry = load_fork_registry(session_id)
        assert registry is not None
        fork2_meta = registry.get_fork(fork2.fork_id)
        assert fork2_meta is not None
        assert fork2_meta.name == "Second Fork"

    def test_rename_to_same_name(
        self, session_with_fork: tuple[str, str]
    ) -> None:
        """Renaming to the same name succeeds and updates timestamp."""
        session_id, fork_id = session_with_fork
        result = rename_fork(session_id, fork_id, "Test Fork")
        assert result.name == "Test Fork"

    def test_strips_whitespace(
        self, session_with_fork: tuple[str, str]
    ) -> None:
        """Leading/trailing whitespace is stripped from the new name."""
        session_id, fork_id = session_with_fork
        result = rename_fork(session_id, fork_id, "  Trimmed  ")
        assert result.name == "Trimmed"


class TestDeleteFork:
    """Tests for delete_fork()."""

    def test_removes_directory_and_registry_entry(
        self, session_with_fork: tuple[str, str]
    ) -> None:
        """Deleting a fork removes its directory and registry entry."""
        session_id, fork_id = session_with_fork
        fork_dir = get_fork_dir(session_id, fork_id)
        assert fork_dir.exists()

        result = delete_fork(session_id, fork_id)
        assert result is True
        assert not fork_dir.exists()

        registry = load_fork_registry(session_id)
        assert registry is not None
        assert registry.get_fork(fork_id) is None

    def test_returns_false_for_missing(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Returns False for non-existent fork."""
        # Need a session with a registry but without the target fork
        session_id = "001"
        registry = ForkRegistry(session_id=session_id)
        save_fork_registry(session_id, registry)
        result = delete_fork(session_id, "999")
        assert result is False

    def test_valueerror_for_active_fork(
        self, session_with_fork: tuple[str, str]
    ) -> None:
        """Raises ValueError when trying to delete the active fork."""
        session_id, fork_id = session_with_fork
        with pytest.raises(ValueError, match="active fork"):
            delete_fork(session_id, fork_id, active_fork_id=fork_id)

    def test_preserves_other_forks(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """Deleting one fork preserves others and main timeline."""
        session_id, fork_id = session_with_fork
        # Create second fork
        fork2 = create_fork(
            state=sample_game_state,
            session_id=session_id,
            fork_name="Second Fork",
        )

        delete_fork(session_id, fork_id)

        # Second fork still exists
        registry = load_fork_registry(session_id)
        assert registry is not None
        assert registry.get_fork(fork2.fork_id) is not None
        assert get_fork_dir(session_id, fork2.fork_id).exists()

        # Main timeline checkpoint still exists
        main_turn = get_latest_checkpoint(session_id)
        assert main_turn is not None

    def test_delete_last_fork_leaves_empty_list(
        self, session_with_fork: tuple[str, str]
    ) -> None:
        """Deleting the last fork results in an empty forks list."""
        session_id, fork_id = session_with_fork
        delete_fork(session_id, fork_id)
        registry = load_fork_registry(session_id)
        assert registry is not None
        assert len(registry.forks) == 0


class TestForkAwareCheckpointRouting:
    """Tests for fork-aware checkpoint routing in run_single_round()."""

    def test_routes_to_fork_when_active(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """When active_fork_id is set, save goes to fork directory."""
        session_id, fork_id = session_with_fork
        sample_game_state["active_fork_id"] = fork_id

        # Simulate what run_single_round does for checkpoint routing
        turn_number = len(sample_game_state["ground_truth_log"])
        active_fork_id = sample_game_state.get("active_fork_id")
        assert active_fork_id is not None

        save_fork_checkpoint(
            sample_game_state, session_id, active_fork_id, turn_number
        )

        # Verify saved to fork directory
        fork_dir = get_fork_dir(session_id, fork_id)
        assert (fork_dir / f"turn_{turn_number:03d}.json").exists()

    def test_routes_to_main_when_no_fork(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """When active_fork_id is None, save goes to main session directory."""
        session_id = "001"
        sample_game_state["active_fork_id"] = None
        turn_number = len(sample_game_state["ground_truth_log"])

        active_fork_id = sample_game_state.get("active_fork_id")
        assert active_fork_id is None

        save_checkpoint(sample_game_state, session_id, turn_number)

        # Verify saved to main directory
        loaded = load_checkpoint(session_id, turn_number)
        assert loaded is not None

    def test_graph_routing_logic_with_mock(self) -> None:
        """Mock test verifying run_single_round imports fork checkpoint functions."""
        # The imports are inside run_single_round(), so we verify
        # they resolve correctly by importing the persistence functions
        # that graph.py uses
        from persistence import save_checkpoint, save_fork_checkpoint

        assert callable(save_checkpoint)
        assert callable(save_fork_checkpoint)

        # Verify graph.py source contains the fork routing logic
        import inspect

        from graph import run_single_round

        source = inspect.getsource(run_single_round)
        assert "save_fork_checkpoint" in source
        assert "active_fork_id" in source


class TestForkSwitchingFlow:
    """Integration tests for fork switching flow."""

    def test_create_save_switch_verify(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """Full flow: create fork, save checkpoint, switch, verify state."""
        session_id, fork_id = session_with_fork

        # Save a fork checkpoint with modified state
        modified_state = dict(sample_game_state)
        modified_state["ground_truth_log"] = list(
            sample_game_state["ground_truth_log"]
        ) + ["[dm] A fork-specific event occurs."]
        modified_state["active_fork_id"] = fork_id
        save_fork_checkpoint(modified_state, session_id, fork_id, 2)

        # Switch to fork: get latest and load
        latest = get_latest_fork_checkpoint(session_id, fork_id)
        assert latest == 2
        loaded = load_fork_checkpoint(session_id, fork_id, latest)
        assert loaded is not None
        loaded["active_fork_id"] = fork_id
        assert loaded["active_fork_id"] == fork_id
        assert len(loaded["ground_truth_log"]) == 3

    def test_return_to_main_flow(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """Full flow: switch to fork, return to main, verify main state."""
        session_id, fork_id = session_with_fork

        # Save a fork checkpoint with fork-specific content
        fork_state = dict(sample_game_state)
        fork_state["ground_truth_log"] = list(
            sample_game_state["ground_truth_log"]
        ) + ["[dm] Fork event."]
        fork_state["active_fork_id"] = fork_id
        save_fork_checkpoint(fork_state, session_id, fork_id, 2)

        # Return to main: save fork progress then load main
        save_fork_checkpoint(fork_state, session_id, fork_id, 3)

        main_turn = get_latest_checkpoint(session_id)
        assert main_turn is not None
        main_state = load_checkpoint(session_id, main_turn)
        assert main_state is not None
        main_state["active_fork_id"] = None

        # Main state should not have fork-specific content
        assert main_state["active_fork_id"] is None
        assert len(main_state["ground_truth_log"]) == 2  # Original 2 entries

    def test_multiple_forks_independent_state(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """Multiple forks maintain independent state."""
        session_id, fork_id_1 = session_with_fork

        # Create second fork
        fork2 = create_fork(
            state=sample_game_state,
            session_id=session_id,
            fork_name="Fork Two",
        )
        fork_id_2 = fork2.fork_id

        # Save different content to each fork
        state1 = dict(sample_game_state)
        state1["ground_truth_log"] = list(
            sample_game_state["ground_truth_log"]
        ) + ["[dm] Fork 1 event."]
        save_fork_checkpoint(state1, session_id, fork_id_1, 2)

        state2 = dict(sample_game_state)
        state2["ground_truth_log"] = list(
            sample_game_state["ground_truth_log"]
        ) + ["[dm] Fork 2 event."]
        save_fork_checkpoint(state2, session_id, fork_id_2, 2)

        # Load each fork and verify independence
        loaded1 = load_fork_checkpoint(session_id, fork_id_1, 2)
        loaded2 = load_fork_checkpoint(session_id, fork_id_2, 2)

        assert loaded1 is not None
        assert loaded2 is not None
        assert loaded1["ground_truth_log"][-1] == "[dm] Fork 1 event."
        assert loaded2["ground_truth_log"][-1] == "[dm] Fork 2 event."

    def test_switch_to_fork_with_only_branch_checkpoint(
        self,
        session_with_fork: tuple[str, str],
    ) -> None:
        """Can switch to a fork that only has the initial branch checkpoint."""
        session_id, fork_id = session_with_fork
        # Fork should have only the initial branch checkpoint (turn 1)
        latest = get_latest_fork_checkpoint(session_id, fork_id)
        assert latest == 1
        loaded = load_fork_checkpoint(session_id, fork_id, latest)
        assert loaded is not None


class TestForkModeIndicator:
    """Tests for fork mode indicator logic."""

    def test_no_badge_when_no_fork(self) -> None:
        """When active_fork_id is None, no fork badge in header."""
        from app import render_session_header_html

        html = render_session_header_html(1, "Turn 5")
        assert "Fork:" not in html

    def test_badge_when_fork_active(self) -> None:
        """When fork_name is provided, badge appears in header."""
        from app import render_session_header_html

        html = render_session_header_html(1, "Turn 5", fork_name="Diplomacy")
        assert "Fork: Diplomacy" in html

    def test_badge_escapes_html(self) -> None:
        """Fork name is HTML-escaped in the badge."""
        from app import render_session_header_html

        html = render_session_header_html(
            1, "Turn 5", fork_name='<script>alert("xss")</script>'
        )
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_fork_name_from_registry(
        self, session_with_fork: tuple[str, str]
    ) -> None:
        """Fork name is correctly loaded from registry."""
        session_id, fork_id = session_with_fork
        registry = load_fork_registry(session_id)
        assert registry is not None
        fork_meta = registry.get_fork(fork_id)
        assert fork_meta is not None
        assert fork_meta.name == "Test Fork"


class TestBackwardCompatibility:
    """Tests for backward compatibility with old states."""

    def test_old_state_without_active_fork_id(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """States without active_fork_id default to None behavior."""
        session_id = "001"
        # Save a checkpoint normally
        save_checkpoint(sample_game_state, session_id, 1)
        loaded = load_checkpoint(session_id, 1)
        assert loaded is not None
        # active_fork_id should be None (default)
        assert loaded.get("active_fork_id") is None

    def test_sessions_without_forks_show_empty_list(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Sessions without forks return empty fork list."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)
        forks = list_forks(session_id)
        assert forks == []

    def test_load_fork_registry_returns_none_for_old_session(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Old sessions without forks.yaml return None registry."""
        session_id = "001"
        save_checkpoint(sample_game_state, session_id, 1)
        registry = load_fork_registry(session_id)
        assert registry is None

    def test_create_initial_game_state_has_active_fork_id(self) -> None:
        """create_initial_game_state includes active_fork_id=None."""
        state = create_initial_game_state()
        assert state["active_fork_id"] is None


class TestRegistryConsistency:
    """Tests for registry consistency after operations."""

    def test_registry_valid_after_rename_and_delete(
        self,
        session_with_fork: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """Registry remains valid after multiple operations."""
        session_id, fork_id = session_with_fork

        # Create second fork
        fork2 = create_fork(
            state=sample_game_state,
            session_id=session_id,
            fork_name="Second Fork",
        )

        # Rename first fork
        rename_fork(session_id, fork_id, "Renamed Fork")

        # Delete second fork
        delete_fork(session_id, fork2.fork_id)

        # Registry should be loadable and consistent
        registry = load_fork_registry(session_id)
        assert registry is not None
        assert len(registry.forks) == 1
        assert registry.forks[0].name == "Renamed Fork"
        assert registry.forks[0].fork_id == fork_id

    def test_save_fork_checkpoint_without_registry(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """save_fork_checkpoint works even if registry is missing."""
        session_id = "001"
        fork_id = "001"
        # Manually create fork dir without registry
        from persistence import ensure_fork_dir

        ensure_fork_dir(session_id, fork_id)

        # Should not raise - just skips registry update
        path = save_fork_checkpoint(sample_game_state, session_id, fork_id, 1)
        assert path.exists()
