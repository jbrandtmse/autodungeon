"""Tests for Story 12.3: Fork Comparison View.

Tests comparison data models, comparison data loading functions,
turn extraction helpers, and session state management for comparison mode.
"""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from models import (
    ComparisonData,
    ComparisonTimeline,
    ComparisonTurn,
    GameState,
    create_initial_game_state,
)
from persistence import (
    build_comparison_data,
    create_fork,
    extract_turns_from_logs,
    extract_turns_from_single_log,
    load_fork_log_at_turn,
    load_timeline_log_at_turn,
    save_checkpoint,
    save_fork_checkpoint,
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


@pytest.fixture
def session_with_forked_content(
    temp_campaigns_dir: Path, sample_game_state: GameState
) -> tuple[str, str]:
    """Create a session with divergent content in main and fork.

    Returns (session_id, fork_id).
    Sets up:
    - Main timeline: 3 turns with log entries
    - Fork: branched at turn 1, then 2 additional turns with different content
    - Fork extends to turn 4 (longer than main)
    """
    session_id = "001"

    # Turn 1: shared content (branch point)
    state = {**sample_game_state}
    state["ground_truth_log"] = [
        "[dm] The dragon descends from the mountain peak.",
    ]
    save_checkpoint(state, session_id, 1)

    # Create fork from turn 1
    fork_meta = create_fork(
        state=state,
        session_id=session_id,
        fork_name="Diplomacy Attempt",
        turn_number=1,
    )
    fork_id = fork_meta.fork_id

    # Main timeline: turn 2 (fight path)
    state["ground_truth_log"].append("[fighter] Thorin charges forward, sword raised!")
    save_checkpoint(state, session_id, 2)

    # Main timeline: turn 3
    state["ground_truth_log"].append("[dm] The dragon's breath engulfs the fighter.")
    save_checkpoint(state, session_id, 3)

    # Fork: turn 2 (diplomacy path)
    fork_state = {**sample_game_state}
    fork_state["ground_truth_log"] = [
        "[dm] The dragon descends from the mountain peak.",
        "[cleric] Aldric steps forward, hands raised in peace.",
    ]
    fork_state["active_fork_id"] = fork_id
    save_fork_checkpoint(fork_state, session_id, fork_id, 2)

    # Fork: turn 3
    fork_state["ground_truth_log"].append(
        "[dm] The dragon pauses, curious about this bold mortal."
    )
    save_fork_checkpoint(fork_state, session_id, fork_id, 3)

    # Fork: turn 4 (fork is longer than main)
    fork_state["ground_truth_log"].append(
        '[dm] "Speak, tiny one..." the dragon rumbles.'
    )
    save_fork_checkpoint(fork_state, session_id, fork_id, 4)

    return session_id, fork_id


# =============================================================================
# Task 5.1: Test ComparisonTurn model validation
# =============================================================================


class TestComparisonTurn:
    """Tests for ComparisonTurn Pydantic model."""

    def test_valid_construction_with_required_fields(self) -> None:
        """Test valid construction with required fields only."""
        turn = ComparisonTurn(turn_number=1)
        assert turn.turn_number == 1
        assert turn.entries == []
        assert turn.is_branch_point is False
        assert turn.is_ended is False

    def test_valid_construction_with_all_fields(self) -> None:
        """Test valid construction with all fields populated."""
        turn = ComparisonTurn(
            turn_number=3,
            entries=["[dm] Something happened.", "[fighter] I attack!"],
            is_branch_point=True,
            is_ended=False,
        )
        assert turn.turn_number == 3
        assert len(turn.entries) == 2
        assert turn.is_branch_point is True
        assert turn.is_ended is False

    def test_default_values(self) -> None:
        """Test default values for is_branch_point and is_ended."""
        turn = ComparisonTurn(turn_number=0)
        assert turn.is_branch_point is False
        assert turn.is_ended is False

    def test_empty_entries_allowed(self) -> None:
        """Test that empty entries list is allowed (for ended timelines)."""
        turn = ComparisonTurn(turn_number=5, entries=[], is_ended=True)
        assert turn.entries == []
        assert turn.is_ended is True

    def test_turn_number_zero_allowed(self) -> None:
        """Test that turn_number 0 is valid."""
        turn = ComparisonTurn(turn_number=0)
        assert turn.turn_number == 0

    def test_negative_turn_number_rejected(self) -> None:
        """Test that negative turn_number is rejected."""
        with pytest.raises(ValidationError):
            ComparisonTurn(turn_number=-1)


# =============================================================================
# Task 5.2: Test ComparisonTimeline model validation
# =============================================================================


class TestComparisonTimeline:
    """Tests for ComparisonTimeline Pydantic model."""

    def test_valid_main_timeline(self) -> None:
        """Test valid construction with main timeline (fork_id=None)."""
        timeline = ComparisonTimeline(
            label="Main Timeline",
            timeline_type="main",
            fork_id=None,
            turns=[],
            total_turns=5,
        )
        assert timeline.label == "Main Timeline"
        assert timeline.timeline_type == "main"
        assert timeline.fork_id is None
        assert timeline.turns == []
        assert timeline.total_turns == 5

    def test_valid_fork_timeline(self) -> None:
        """Test valid construction with fork timeline (fork_id="001")."""
        timeline = ComparisonTimeline(
            label="Diplomacy Attempt",
            timeline_type="fork",
            fork_id="001",
            turns=[ComparisonTurn(turn_number=1)],
            total_turns=3,
        )
        assert timeline.timeline_type == "fork"
        assert timeline.fork_id == "001"
        assert len(timeline.turns) == 1

    def test_label_and_type_populated(self) -> None:
        """Test that label and timeline_type fields are correctly populated."""
        timeline = ComparisonTimeline(
            label="Test Label",
            timeline_type="main",
        )
        assert timeline.label == "Test Label"
        assert timeline.timeline_type == "main"

    def test_empty_label_rejected(self) -> None:
        """Test that empty label is rejected."""
        with pytest.raises(ValidationError):
            ComparisonTimeline(
                label="",
                timeline_type="main",
            )

    def test_invalid_timeline_type_rejected(self) -> None:
        """Test that invalid timeline_type is rejected."""
        with pytest.raises(ValidationError):
            ComparisonTimeline(
                label="Test",
                timeline_type="invalid",  # type: ignore[arg-type]
            )

    def test_default_values(self) -> None:
        """Test default values for optional fields."""
        timeline = ComparisonTimeline(
            label="Test",
            timeline_type="main",
        )
        assert timeline.fork_id is None
        assert timeline.turns == []
        assert timeline.total_turns == 0


# =============================================================================
# Task 5.3: Test ComparisonData model validation
# =============================================================================


class TestComparisonData:
    """Tests for ComparisonData Pydantic model."""

    def test_valid_construction(self) -> None:
        """Test valid construction with both left and right timelines."""
        left = ComparisonTimeline(
            label="Main Timeline",
            timeline_type="main",
            total_turns=5,
        )
        right = ComparisonTimeline(
            label="Diplomacy Attempt",
            timeline_type="fork",
            fork_id="001",
            total_turns=3,
        )
        data = ComparisonData(
            session_id="001",
            branch_turn=2,
            left=left,
            right=right,
        )
        assert data.session_id == "001"
        assert data.branch_turn == 2
        assert data.left.label == "Main Timeline"
        assert data.right.label == "Diplomacy Attempt"

    def test_branch_turn_matches_metadata(self) -> None:
        """Test that branch_turn is set correctly."""
        left = ComparisonTimeline(label="Main", timeline_type="main")
        right = ComparisonTimeline(label="Fork", timeline_type="fork", fork_id="001")
        data = ComparisonData(
            session_id="001",
            branch_turn=5,
            left=left,
            right=right,
        )
        assert data.branch_turn == 5

    def test_empty_session_id_rejected(self) -> None:
        """Test that empty session_id is rejected."""
        left = ComparisonTimeline(label="Main", timeline_type="main")
        right = ComparisonTimeline(label="Fork", timeline_type="fork")
        with pytest.raises(ValidationError):
            ComparisonData(
                session_id="",
                branch_turn=1,
                left=left,
                right=right,
            )


# =============================================================================
# Task 5.4: Test load_timeline_log_at_turn()
# =============================================================================


class TestLoadTimelineLogAtTurn:
    """Tests for load_timeline_log_at_turn function."""

    def test_returns_log_from_checkpoint(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test that it returns ground_truth_log from checkpoint at specified turn."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] Hello", "[fighter] I attack!"]
        save_checkpoint(state, session_id, 1)

        log = load_timeline_log_at_turn(session_id, 1)
        assert log is not None
        assert len(log) == 2
        assert log[0] == "[dm] Hello"
        assert log[1] == "[fighter] I attack!"

    def test_returns_none_for_nonexistent_checkpoint(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test that it returns None for a non-existent checkpoint."""
        log = load_timeline_log_at_turn("001", 999)
        assert log is None

    def test_returns_none_for_invalid_checkpoint(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Test that it returns None for an invalid/corrupt checkpoint."""
        # Create a session directory with an invalid checkpoint file
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()
        bad_file = session_dir / "turn_001.json"
        bad_file.write_text("NOT VALID JSON", encoding="utf-8")

        log = load_timeline_log_at_turn("001", 1)
        assert log is None


# =============================================================================
# Task 5.5: Test load_fork_log_at_turn()
# =============================================================================


class TestLoadForkLogAtTurn:
    """Tests for load_fork_log_at_turn function."""

    def test_returns_fork_log(
        self, session_with_forked_content: tuple[str, str]
    ) -> None:
        """Test that it returns ground_truth_log from fork checkpoint."""
        session_id, fork_id = session_with_forked_content
        log = load_fork_log_at_turn(session_id, fork_id, 2)
        assert log is not None
        assert len(log) == 2
        assert "[cleric]" in log[1]

    def test_returns_none_for_nonexistent_fork_checkpoint(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test that it returns None for a non-existent fork checkpoint."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] Hello"]
        save_checkpoint(state, session_id, 1)

        fork_meta = create_fork(
            state=state,
            session_id=session_id,
            fork_name="Test Fork",
            turn_number=1,
        )

        # Try to load a turn that doesn't exist in the fork
        log = load_fork_log_at_turn(session_id, fork_meta.fork_id, 999)
        assert log is None

    def test_returns_none_for_invalid_fork_id(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test that it returns None for an invalid fork_id."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] Hello"]
        save_checkpoint(state, session_id, 1)

        log = load_fork_log_at_turn(session_id, "nonexistent", 1)
        assert log is None


# =============================================================================
# Task 5.6: Test build_comparison_data()
# =============================================================================


class TestBuildComparisonData:
    """Tests for build_comparison_data function."""

    def test_end_to_end_comparison(
        self, session_with_forked_content: tuple[str, str]
    ) -> None:
        """End-to-end: build comparison from session with fork."""
        session_id, fork_id = session_with_forked_content
        data = build_comparison_data(session_id, fork_id)

        assert data is not None
        assert data.session_id == session_id
        assert data.branch_turn == 1

    def test_branch_point_same_in_both(
        self, session_with_forked_content: tuple[str, str]
    ) -> None:
        """Branch point turn appears in both timelines with same content."""
        session_id, fork_id = session_with_forked_content
        data = build_comparison_data(session_id, fork_id)
        assert data is not None

        # Both timelines should have the branch point as first turn
        left_branch = data.left.turns[0]
        right_branch = data.right.turns[0]

        assert left_branch.is_branch_point is True
        assert right_branch.is_branch_point is True
        assert left_branch.turn_number == right_branch.turn_number
        assert left_branch.entries == right_branch.entries

    def test_post_branch_turns_correctly_aligned(
        self, session_with_forked_content: tuple[str, str]
    ) -> None:
        """Post-branch turns are correctly aligned by index."""
        session_id, fork_id = session_with_forked_content
        data = build_comparison_data(session_id, fork_id)
        assert data is not None

        # After the branch point, main has 2 entries, fork has 3 entries
        # Main: turn 2 (fighter charges), turn 3 (dragon breath)
        # Fork: turn 2 (cleric peace), turn 3 (dragon pauses), turn 4 (dragon speaks)

        # Turn index 1 = first post-branch
        left_turn_2 = data.left.turns[1]
        right_turn_2 = data.right.turns[1]

        assert left_turn_2.turn_number == 2
        assert right_turn_2.turn_number == 2
        assert "[fighter]" in left_turn_2.entries[0]
        assert "[cleric]" in right_turn_2.entries[0]

    def test_shorter_timeline_shows_ended(
        self, session_with_forked_content: tuple[str, str]
    ) -> None:
        """Shorter timeline shows is_ended=True on remaining turns."""
        session_id, fork_id = session_with_forked_content
        data = build_comparison_data(session_id, fork_id)
        assert data is not None

        # Main timeline is shorter (3 turns of log entries: 1 branch + 2 post)
        # Fork has 1 branch + 3 post, so main should show ended at the last position

        # The fork has 4 post-branch entries but main has only 2
        # So at index 3 (turn 4), main should be ended
        left_turn_4 = data.left.turns[3]
        assert left_turn_4.is_ended is True
        assert left_turn_4.entries == []

    def test_longer_timeline_continues(
        self, session_with_forked_content: tuple[str, str]
    ) -> None:
        """Longer timeline continues past shorter one."""
        session_id, fork_id = session_with_forked_content
        data = build_comparison_data(session_id, fork_id)
        assert data is not None

        # Fork is longer, its turn at index 3 (turn 4) should still have content
        right_turn_4 = data.right.turns[3]
        assert right_turn_4.is_ended is False
        assert len(right_turn_4.entries) > 0

    def test_returns_none_for_nonexistent_fork(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Returns None for non-existent fork."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] Hello"]
        save_checkpoint(state, session_id, 1)

        data = build_comparison_data(session_id, "nonexistent_fork")
        assert data is None

    def test_returns_none_for_session_with_no_checkpoints(
        self, temp_campaigns_dir: Path
    ) -> None:
        """Returns None for session with no checkpoints."""
        data = build_comparison_data("001", "001")
        assert data is None

    def test_fork_with_no_additional_turns(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Fork with no additional turns: only branch point shown, fork side shows ended."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = [
            "[dm] The dragon descends.",
        ]
        save_checkpoint(state, session_id, 1)

        # Create fork but don't add any turns to it
        fork_meta = create_fork(
            state=state,
            session_id=session_id,
            fork_name="Empty Fork",
            turn_number=1,
        )

        # Add more entries to main timeline
        state["ground_truth_log"].append("[fighter] I charge!")
        save_checkpoint(state, session_id, 2)

        data = build_comparison_data(session_id, fork_meta.fork_id)
        assert data is not None

        # Both timelines should have the branch point
        assert data.left.turns[0].is_branch_point is True
        assert data.right.turns[0].is_branch_point is True

        # Main has a post-branch turn, fork should show ended
        assert len(data.left.turns) > 1
        assert data.left.turns[1].is_ended is False

        # Fork should show ended for the post-branch turn
        assert data.right.turns[1].is_ended is True

    def test_timeline_labels(
        self, session_with_forked_content: tuple[str, str]
    ) -> None:
        """Test that timeline labels are correct."""
        session_id, fork_id = session_with_forked_content
        data = build_comparison_data(session_id, fork_id)
        assert data is not None

        assert data.left.label == "Main Timeline"
        assert data.left.timeline_type == "main"
        assert data.left.fork_id is None

        assert data.right.label == "Diplomacy Attempt"
        assert data.right.timeline_type == "fork"
        assert data.right.fork_id == fork_id


# =============================================================================
# Task 5.7: Test extract_turns_from_logs() helper
# =============================================================================


class TestExtractTurnsFromLogs:
    """Tests for extract_turns_from_logs helper function."""

    def test_correctly_diffs_consecutive_logs(self) -> None:
        """Test correct diffing of consecutive log snapshots."""
        logs_by_checkpoint = {
            1: ["[dm] Start"],
            2: ["[dm] Start", "[fighter] Attack!"],
            3: ["[dm] Start", "[fighter] Attack!", "[dm] Dragon roars"],
        }
        turns = extract_turns_from_logs(logs_by_checkpoint, 1)

        assert len(turns) == 3
        # Turn 1: all entries at branch point
        assert turns[0].entries == ["[dm] Start"]
        # Turn 2: new entry added
        assert turns[1].entries == ["[fighter] Attack!"]
        # Turn 3: new entry added
        assert turns[2].entries == ["[dm] Dragon roars"]

    def test_first_turn_marked_as_branch_point(self) -> None:
        """Test that first turn is marked as branch point."""
        logs_by_checkpoint = {
            5: ["[dm] Entry"],
        }
        turns = extract_turns_from_logs(logs_by_checkpoint, 5)

        assert len(turns) == 1
        assert turns[0].is_branch_point is True
        assert turns[0].turn_number == 5

    def test_subsequent_turns_not_branch_point(self) -> None:
        """Test that subsequent turns are not marked as branch point."""
        logs_by_checkpoint = {
            1: ["[dm] Start"],
            2: ["[dm] Start", "[fighter] Attack!"],
        }
        turns = extract_turns_from_logs(logs_by_checkpoint, 1)

        assert turns[1].is_branch_point is False

    def test_empty_dict_returns_empty_list(self) -> None:
        """Test that empty dict returns empty list."""
        turns = extract_turns_from_logs({}, 0)
        assert turns == []

    def test_filters_to_start_turn(self) -> None:
        """Test that only turns >= start_turn are included."""
        logs_by_checkpoint = {
            1: ["[dm] A"],
            2: ["[dm] A", "[dm] B"],
            3: ["[dm] A", "[dm] B", "[dm] C"],
        }
        turns = extract_turns_from_logs(logs_by_checkpoint, 2)

        # Should only include turns 2 and 3
        assert len(turns) == 2
        assert turns[0].turn_number == 2
        assert turns[0].is_branch_point is True
        assert turns[1].turn_number == 3


# =============================================================================
# Task 5.8: Test extract_turns_from_single_log() fallback
# =============================================================================


class TestExtractTurnsFromSingleLog:
    """Tests for extract_turns_from_single_log fallback function."""

    def test_distributes_entries_correctly(self) -> None:
        """Test that entries are distributed across turns."""
        log = [
            "[dm] Branch point entry",
            "[fighter] Post branch 1",
            "[dm] Post branch 2",
            "[cleric] Post branch 3",
        ]
        branch_log_count = 1  # First entry is branch point
        turns = extract_turns_from_single_log(log, branch_log_count, 3)

        # Should have 3 turns from the 3 post-branch entries
        assert len(turns) == 3
        assert turns[0].entries == ["[fighter] Post branch 1"]
        assert turns[1].entries == ["[dm] Post branch 2"]
        assert turns[2].entries == ["[cleric] Post branch 3"]

    def test_no_entries_after_branch_point(self) -> None:
        """Test handling when log has no entries after branch point."""
        log = ["[dm] Only entry"]
        turns = extract_turns_from_single_log(log, 1, 0)
        assert turns == []

    def test_empty_log(self) -> None:
        """Test handling of empty log."""
        turns = extract_turns_from_single_log([], 0, 0)
        assert turns == []


# =============================================================================
# Task 5.9: Test comparison session state management
# =============================================================================


class TestComparisonSessionState:
    """Tests for comparison mode session state keys."""

    def test_comparison_mode_true_with_valid_specs(self) -> None:
        """Test setting comparison_mode = True with valid left/right specs."""
        # Simulate session state dict
        state: dict[str, object] = {}
        state["comparison_mode"] = True
        state["comparison_left"] = {"type": "main", "fork_id": None}
        state["comparison_right"] = {"type": "fork", "fork_id": "001"}

        assert state["comparison_mode"] is True
        left = state["comparison_left"]
        assert isinstance(left, dict)
        assert left["type"] == "main"
        assert left["fork_id"] is None

        right = state["comparison_right"]
        assert isinstance(right, dict)
        assert right["type"] == "fork"
        assert right["fork_id"] == "001"

    def test_clearing_comparison_mode(self) -> None:
        """Test that clearing comparison mode resets to False."""
        state: dict[str, object] = {
            "comparison_mode": True,
            "comparison_left": {"type": "main", "fork_id": None},
            "comparison_right": {"type": "fork", "fork_id": "001"},
        }

        # Clear comparison mode
        state["comparison_mode"] = False

        assert state["comparison_mode"] is False

    def test_left_right_track_timeline_type_and_fork_id(self) -> None:
        """Test that left/right specs track timeline type and fork_id correctly."""
        state: dict[str, object] = {}

        # Main vs fork_001
        state["comparison_left"] = {"type": "main", "fork_id": None}
        state["comparison_right"] = {"type": "fork", "fork_id": "001"}

        left = state["comparison_left"]
        right = state["comparison_right"]
        assert isinstance(left, dict)
        assert isinstance(right, dict)
        assert left["type"] == "main"
        assert right["type"] == "fork"
        assert right["fork_id"] == "001"

        # Switch to a different fork
        state["comparison_right"] = {"type": "fork", "fork_id": "002"}
        right = state["comparison_right"]
        assert isinstance(right, dict)
        assert right["fork_id"] == "002"


# =============================================================================
# Task 5.10: Test comparison with multiple forks from same branch point
# =============================================================================


class TestMultipleForkComparison:
    """Tests for comparing main timeline against different forks."""

    def test_compare_main_vs_fork_001(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Can compare main vs fork_001."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] The dragon appears."]
        save_checkpoint(state, session_id, 1)

        fork_1 = create_fork(
            state=state,
            session_id=session_id,
            fork_name="Fork One",
            turn_number=1,
        )

        # Add content to main
        state["ground_truth_log"].append("[fighter] I fight!")
        save_checkpoint(state, session_id, 2)

        # Add content to fork 1
        fork_state = {**sample_game_state}
        fork_state["ground_truth_log"] = [
            "[dm] The dragon appears.",
            "[cleric] I pray for guidance.",
        ]
        fork_state["active_fork_id"] = fork_1.fork_id
        save_fork_checkpoint(fork_state, session_id, fork_1.fork_id, 2)

        data = build_comparison_data(session_id, fork_1.fork_id)
        assert data is not None
        assert data.right.label == "Fork One"
        assert data.right.fork_id == fork_1.fork_id

    def test_compare_main_vs_fork_002(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Can compare main vs fork_002."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] The dragon appears."]
        save_checkpoint(state, session_id, 1)

        # Create two forks
        create_fork(
            state=state,
            session_id=session_id,
            fork_name="Fork One",
            turn_number=1,
        )
        fork_2 = create_fork(
            state=state,
            session_id=session_id,
            fork_name="Fork Two",
            turn_number=1,
        )

        # Add content to main
        state["ground_truth_log"].append("[fighter] I fight!")
        save_checkpoint(state, session_id, 2)

        # Add content to fork 2
        fork_state = {**sample_game_state}
        fork_state["ground_truth_log"] = [
            "[dm] The dragon appears.",
            "[rogue] I sneak around.",
        ]
        fork_state["active_fork_id"] = fork_2.fork_id
        save_fork_checkpoint(fork_state, session_id, fork_2.fork_id, 2)

        data = build_comparison_data(session_id, fork_2.fork_id)
        assert data is not None
        assert data.right.label == "Fork Two"
        assert data.right.fork_id == fork_2.fork_id
        # Verify fork 2's content, not fork 1's
        assert "[rogue]" in data.right.turns[1].entries[0]

    def test_each_comparison_shows_correct_fork_data(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Each comparison shows the correct fork's data."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] The dragon appears."]
        save_checkpoint(state, session_id, 1)

        fork_1 = create_fork(
            state=state,
            session_id=session_id,
            fork_name="Fight Path",
            turn_number=1,
        )
        fork_2 = create_fork(
            state=state,
            session_id=session_id,
            fork_name="Flee Path",
            turn_number=1,
        )

        # Main adds a turn
        state["ground_truth_log"].append("[dm] Main continues...")
        save_checkpoint(state, session_id, 2)

        # Fork 1 content
        f1_state = {**sample_game_state}
        f1_state["ground_truth_log"] = [
            "[dm] The dragon appears.",
            "[fighter] CHARGE!",
        ]
        f1_state["active_fork_id"] = fork_1.fork_id
        save_fork_checkpoint(f1_state, session_id, fork_1.fork_id, 2)

        # Fork 2 content
        f2_state = {**sample_game_state}
        f2_state["ground_truth_log"] = [
            "[dm] The dragon appears.",
            "[rogue] RUN AWAY!",
        ]
        f2_state["active_fork_id"] = fork_2.fork_id
        save_fork_checkpoint(f2_state, session_id, fork_2.fork_id, 2)

        # Compare against fork 1
        data1 = build_comparison_data(session_id, fork_1.fork_id)
        assert data1 is not None
        assert data1.right.label == "Fight Path"
        assert "[fighter] CHARGE!" in data1.right.turns[1].entries[0]

        # Compare against fork 2
        data2 = build_comparison_data(session_id, fork_2.fork_id)
        assert data2 is not None
        assert data2.right.label == "Flee Path"
        assert "[rogue] RUN AWAY!" in data2.right.turns[1].entries[0]


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests for comparison functionality."""

    def test_fork_created_at_turn_zero(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Fork created at turn 0 (empty game state)."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = []
        save_checkpoint(state, session_id, 0)

        fork_meta = create_fork(
            state=state,
            session_id=session_id,
            fork_name="Early Fork",
            turn_number=0,
        )

        # Add content to main
        state["ground_truth_log"].append("[dm] The adventure begins.")
        save_checkpoint(state, session_id, 1)

        # Add content to fork
        fork_state = {**sample_game_state}
        fork_state["ground_truth_log"] = [
            "[dm] A different beginning.",
        ]
        fork_state["active_fork_id"] = fork_meta.fork_id
        save_fork_checkpoint(fork_state, session_id, fork_meta.fork_id, 1)

        data = build_comparison_data(session_id, fork_meta.fork_id)
        assert data is not None
        assert data.branch_turn == 0
        assert data.left.turns[0].is_branch_point is True

    def test_fork_with_identical_content(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Fork with same content as main (identical logs)."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] The dragon appears."]
        save_checkpoint(state, session_id, 1)

        fork_meta = create_fork(
            state=state,
            session_id=session_id,
            fork_name="Mirror Fork",
            turn_number=1,
        )

        # Add same content to both
        state["ground_truth_log"].append("[fighter] I attack the dragon.")
        save_checkpoint(state, session_id, 2)

        fork_state = {**sample_game_state}
        fork_state["ground_truth_log"] = [
            "[dm] The dragon appears.",
            "[fighter] I attack the dragon.",
        ]
        fork_state["active_fork_id"] = fork_meta.fork_id
        save_fork_checkpoint(fork_state, session_id, fork_meta.fork_id, 2)

        data = build_comparison_data(session_id, fork_meta.fork_id)
        assert data is not None

        # Branch point should be identical
        assert data.left.turns[0].entries == data.right.turns[0].entries

        # Post-branch should also be identical content
        assert data.left.turns[1].entries == data.right.turns[1].entries

    def test_long_logs_performance(
        self, temp_campaigns_dir: Path, sample_game_state: GameState
    ) -> None:
        """Test with 100+ log entries for performance sanity."""
        session_id = "001"
        state = {**sample_game_state}

        # Build a log with 100 entries
        state["ground_truth_log"] = [f"[dm] Entry {i}" for i in range(100)]
        save_checkpoint(state, session_id, 1)

        fork_meta = create_fork(
            state=state,
            session_id=session_id,
            fork_name="Long Fork",
            turn_number=1,
        )

        # Add 50 more to main
        for i in range(100, 150):
            state["ground_truth_log"].append(f"[dm] Main entry {i}")
        save_checkpoint(state, session_id, 2)

        # Add 50 different to fork
        fork_state = {**sample_game_state}
        fork_state["ground_truth_log"] = [f"[dm] Entry {i}" for i in range(100)]
        for i in range(100, 150):
            fork_state["ground_truth_log"].append(f"[dm] Fork entry {i}")
        fork_state["active_fork_id"] = fork_meta.fork_id
        save_fork_checkpoint(fork_state, session_id, fork_meta.fork_id, 2)

        data = build_comparison_data(session_id, fork_meta.fork_id)
        assert data is not None
        # Branch point should have 100 entries
        assert len(data.left.turns[0].entries) == 100
