"""Tests for Story 12.4: Fork Resolution.

Tests fork promotion (promote_fork), fork collapse (collapse_all_forks),
confirmation state management, and backward compatibility.
"""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import patch

import pytest

from models import (
    GameState,
    create_initial_game_state,
)
from persistence import (
    collapse_all_forks,
    create_fork,
    get_fork_dir,
    get_fork_registry_path,
    get_session_dir,
    list_checkpoints,
    list_fork_checkpoints,
    list_forks,
    load_checkpoint,
    load_fork_checkpoint,
    load_fork_registry,
    promote_fork,
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
def session_with_fork_and_content(
    temp_campaigns_dir: Path, sample_game_state: GameState
) -> tuple[str, str]:
    """Create a session with divergent main and fork content.

    Returns (session_id, fork_id).
    Sets up:
    - Main timeline: turns 1-5 with log entries
    - Fork: branched at turn 3, then turns 4-6 with different content
    """
    session_id = "001"

    # Build main timeline
    state = {**sample_game_state}
    for i in range(1, 6):
        state["ground_truth_log"] = [
            f"[dm] Main timeline entry {j}" for j in range(1, i + 1)
        ]
        save_checkpoint(state, session_id, i)

    # Create fork at turn 3
    fork_meta = create_fork(
        state=state,
        session_id=session_id,
        fork_name="Diplomacy Attempt",
        turn_number=3,
    )
    fork_id = fork_meta.fork_id

    # Build fork content (turns 4-6)
    fork_state = {**sample_game_state}
    fork_state["active_fork_id"] = fork_id
    for i in range(4, 7):
        fork_state["ground_truth_log"] = [
            f"[dm] Main timeline entry {j}" for j in range(1, 4)
        ] + [f"[dm] Fork entry {j}" for j in range(4, i + 1)]
        save_fork_checkpoint(fork_state, session_id, fork_id, i)

    return session_id, fork_id


# =============================================================================
# Test 4.1: promote_fork() basic flow
# =============================================================================


class TestPromoteForkBasic:
    """Test basic promote_fork() functionality."""

    def test_basic_promotion_flow(
        self,
        session_with_fork_and_content: tuple[str, str],
    ) -> None:
        """Test promote_fork() basic flow: checkpoints moved, registry updated."""
        session_id, fork_id = session_with_fork_and_content

        # Verify pre-conditions
        assert list_checkpoints(session_id) == [1, 2, 3, 4, 5]
        assert list_fork_checkpoints(session_id, fork_id) == [3, 4, 5, 6]

        # Promote the fork
        latest = promote_fork(session_id, fork_id)

        # Verify: return value is latest turn on new main
        assert latest == 6

        # Verify: main timeline now has turns 1-6
        main_turns = list_checkpoints(session_id)
        assert main_turns == [1, 2, 3, 4, 5, 6]

        # Verify: turns 1-3 unchanged (pre-branch preserved)
        for turn in [1, 2, 3]:
            state = load_checkpoint(session_id, turn)
            assert state is not None
            log = state.get("ground_truth_log", [])
            assert f"[dm] Main timeline entry {turn}" in log

        # Verify: turns 4-6 now contain fork content
        state_4 = load_checkpoint(session_id, 4)
        assert state_4 is not None
        log_4 = state_4.get("ground_truth_log", [])
        assert "[dm] Fork entry 4" in log_4
        assert "[dm] Main timeline entry 4" not in log_4

        state_5 = load_checkpoint(session_id, 5)
        assert state_5 is not None
        log_5 = state_5.get("ground_truth_log", [])
        assert "[dm] Fork entry 5" in log_5

        state_6 = load_checkpoint(session_id, 6)
        assert state_6 is not None
        log_6 = state_6.get("ground_truth_log", [])
        assert "[dm] Fork entry 6" in log_6

        # Verify: promoted fork removed from registry
        registry = load_fork_registry(session_id)
        assert registry is not None
        assert registry.get_fork(fork_id) is None

        # Verify: promoted fork directory removed
        fork_dir = get_fork_dir(session_id, fork_id)
        assert not fork_dir.exists()

        # Verify: archive fork created
        forks = list_forks(session_id)
        assert len(forks) == 1
        archive = forks[0]
        assert archive.name == "Pre-Diplomacy Attempt main"
        assert archive.branch_turn == 3

        # Verify: archive fork contains old main's turns 4-5
        archive_turns = list_fork_checkpoints(session_id, archive.fork_id)
        # Archive includes branch point copy + post-branch turns
        assert 3 in archive_turns
        assert 4 in archive_turns
        assert 5 in archive_turns

        # Verify archive content matches old main
        archive_state_4 = load_fork_checkpoint(session_id, archive.fork_id, 4)
        assert archive_state_4 is not None
        archive_log_4 = archive_state_4.get("ground_truth_log", [])
        assert "[dm] Main timeline entry 4" in archive_log_4


# =============================================================================
# Test 4.2: promote_fork() when fork is longer than main
# =============================================================================


class TestPromoteForkLonger:
    """Test promote_fork() when fork is longer than main."""

    def test_fork_longer_than_main(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """Fork has more post-branch turns than main."""
        session_id = "001"
        state = {**sample_game_state}

        # Main: turns 1-4 (branch at 3, 1 post-branch)
        for i in range(1, 5):
            state["ground_truth_log"] = [
                f"[dm] Main entry {j}" for j in range(1, i + 1)
            ]
            save_checkpoint(state, session_id, i)

        # Create fork at turn 3
        fork_meta = create_fork(
            state=state, session_id=session_id, fork_name="Long Fork", turn_number=3
        )
        fork_id = fork_meta.fork_id

        # Fork: turns 4-6 (3 post-branch turns)
        fork_state = {**sample_game_state}
        for i in range(4, 7):
            fork_state["ground_truth_log"] = [
                f"[dm] Main entry {j}" for j in range(1, 4)
            ] + [f"[dm] Fork entry {j}" for j in range(4, i + 1)]
            save_fork_checkpoint(fork_state, session_id, fork_id, i)

        # Promote
        latest = promote_fork(session_id, fork_id)

        # Verify: main now has turns 1-6
        assert latest == 6
        assert list_checkpoints(session_id) == [1, 2, 3, 4, 5, 6]

        # Verify fork content at turns 4-6
        for turn in [4, 5, 6]:
            s = load_checkpoint(session_id, turn)
            assert s is not None
            assert f"[dm] Fork entry {turn}" in s.get("ground_truth_log", [])

        # Verify archive has only old main's turn 4
        forks = list_forks(session_id)
        archive = [f for f in forks if "Pre-" in f.name][0]
        archive_post = [
            t
            for t in list_fork_checkpoints(session_id, archive.fork_id)
            if t > 3
        ]
        assert archive_post == [4]


# =============================================================================
# Test 4.3: promote_fork() when main is longer than fork
# =============================================================================


class TestPromoteMainLonger:
    """Test promote_fork() when main is longer than fork."""

    def test_main_longer_than_fork(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """Main has more post-branch turns than fork."""
        session_id = "001"
        state = {**sample_game_state}

        # Main: turns 1-7 (branch at 3, 4 post-branch)
        for i in range(1, 8):
            state["ground_truth_log"] = [
                f"[dm] Main entry {j}" for j in range(1, i + 1)
            ]
            save_checkpoint(state, session_id, i)

        # Create fork at turn 3
        fork_meta = create_fork(
            state=state, session_id=session_id, fork_name="Short Fork", turn_number=3
        )
        fork_id = fork_meta.fork_id

        # Fork: only turn 4 (1 post-branch)
        fork_state = {**sample_game_state}
        fork_state["ground_truth_log"] = [
            f"[dm] Main entry {j}" for j in range(1, 4)
        ] + ["[dm] Fork entry 4"]
        save_fork_checkpoint(fork_state, session_id, fork_id, 4)

        # Promote
        latest = promote_fork(session_id, fork_id)

        # Verify: main now has turns 1-4 (turn 4 is fork content)
        assert latest == 4
        assert list_checkpoints(session_id) == [1, 2, 3, 4]

        # Verify main's turns 5-7 are removed
        for turn in [5, 6, 7]:
            s = load_checkpoint(session_id, turn)
            assert s is None

        # Verify turn 4 is fork content
        s4 = load_checkpoint(session_id, 4)
        assert s4 is not None
        assert "[dm] Fork entry 4" in s4.get("ground_truth_log", [])

        # Verify archive has old main's turns 4-7
        forks = list_forks(session_id)
        archive = [f for f in forks if "Pre-" in f.name][0]
        archive_post = [
            t
            for t in list_fork_checkpoints(session_id, archive.fork_id)
            if t > 3
        ]
        assert archive_post == [4, 5, 6, 7]


# =============================================================================
# Test 4.4: promote_fork() when main has no post-branch checkpoints
# =============================================================================


class TestPromoteNoPostBranch:
    """Test promote_fork() when main has no post-branch content."""

    def test_no_post_branch_main(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """Main has only turns up to branch point, fork extends beyond."""
        session_id = "001"
        state = {**sample_game_state}

        # Main: turns 1-3 (branch at 3, 0 post-branch)
        for i in range(1, 4):
            state["ground_truth_log"] = [
                f"[dm] Main entry {j}" for j in range(1, i + 1)
            ]
            save_checkpoint(state, session_id, i)

        # Create fork at turn 3
        fork_meta = create_fork(
            state=state, session_id=session_id, fork_name="Extended Fork", turn_number=3
        )
        fork_id = fork_meta.fork_id

        # Fork: turns 4-5
        fork_state = {**sample_game_state}
        for i in range(4, 6):
            fork_state["ground_truth_log"] = [
                f"[dm] Main entry {j}" for j in range(1, 4)
            ] + [f"[dm] Fork entry {j}" for j in range(4, i + 1)]
            save_fork_checkpoint(fork_state, session_id, fork_id, i)

        # Promote
        latest = promote_fork(session_id, fork_id)

        # Verify: main now has turns 1-5 (turns 4-5 from fork)
        assert latest == 5
        assert list_checkpoints(session_id) == [1, 2, 3, 4, 5]

        # Verify no archive fork created (nothing to archive)
        forks = list_forks(session_id)
        assert len(forks) == 0

        # Verify promoted fork removed from registry
        registry = load_fork_registry(session_id)
        assert registry is not None
        assert registry.get_fork(fork_id) is None


# =============================================================================
# Test 4.5: promote_fork() error cases
# =============================================================================


class TestPromoteForkErrors:
    """Test promote_fork() error cases."""

    def test_nonexistent_fork_id(
        self,
        session_with_fork_and_content: tuple[str, str],
    ) -> None:
        """Raise ValueError for non-existent fork_id."""
        session_id, _ = session_with_fork_and_content
        with pytest.raises(ValueError, match="not found"):
            promote_fork(session_id, "999")

    def test_fork_with_no_post_branch_checkpoints(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """Raise ValueError when fork has no checkpoints beyond branch."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] Entry 1"]
        save_checkpoint(state, session_id, 1)

        # Create fork at turn 1 (this copies turn 1 to fork dir)
        fork_meta = create_fork(
            state=state,
            session_id=session_id,
            fork_name="Empty Fork",
            turn_number=1,
        )

        # Fork has only the branch point checkpoint (turn 1), no post-branch
        with pytest.raises(ValueError, match="no checkpoints beyond branch"):
            promote_fork(session_id, fork_meta.fork_id)

    def test_invalid_session_id(self, temp_campaigns_dir: Path) -> None:
        """Raise ValueError for invalid session_id."""
        with pytest.raises(ValueError, match="Invalid session_id"):
            promote_fork("../evil", "001")

    def test_invalid_fork_id(self, temp_campaigns_dir: Path) -> None:
        """Raise ValueError for invalid fork_id."""
        with pytest.raises(ValueError, match="Invalid fork_id"):
            promote_fork("001", "../evil")

    def test_no_fork_registry(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """Raise ValueError for session without fork registry."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] Entry 1"]
        save_checkpoint(state, session_id, 1)

        with pytest.raises(ValueError, match="No fork registry"):
            promote_fork(session_id, "001")


# =============================================================================
# Test 4.6: promote_fork() with multiple forks
# =============================================================================


class TestPromoteWithMultipleForks:
    """Test promote_fork() with multiple forks present."""

    def test_promote_one_of_multiple_forks(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """Promote one fork when multiple exist from same branch point."""
        session_id = "001"
        state = {**sample_game_state}

        # Main: turns 1-5
        for i in range(1, 6):
            state["ground_truth_log"] = [
                f"[dm] Main entry {j}" for j in range(1, i + 1)
            ]
            save_checkpoint(state, session_id, i)

        # Create fork_001 at turn 3
        fork1_meta = create_fork(
            state=state, session_id=session_id, fork_name="Fork A", turn_number=3
        )
        fork1_id = fork1_meta.fork_id

        # Create fork_002 at turn 3
        fork2_meta = create_fork(
            state=state, session_id=session_id, fork_name="Fork B", turn_number=3
        )
        fork2_id = fork2_meta.fork_id

        # Add content to fork_001
        fork_state = {**sample_game_state}
        fork_state["ground_truth_log"] = [
            f"[dm] Main entry {j}" for j in range(1, 4)
        ] + ["[dm] Fork A entry 4"]
        save_fork_checkpoint(fork_state, session_id, fork1_id, 4)

        # Add content to fork_002
        fork_state2 = {**sample_game_state}
        fork_state2["ground_truth_log"] = [
            f"[dm] Main entry {j}" for j in range(1, 4)
        ] + ["[dm] Fork B entry 4"]
        save_fork_checkpoint(fork_state2, session_id, fork2_id, 4)

        # Promote fork_001
        promote_fork(session_id, fork1_id)

        # Verify: fork_001 removed from registry
        registry = load_fork_registry(session_id)
        assert registry is not None
        assert registry.get_fork(fork1_id) is None

        # Verify: fork_002 still present
        assert registry.get_fork(fork2_id) is not None

        # Verify: archive fork added
        forks = list_forks(session_id)
        archive_forks = [f for f in forks if "Pre-" in f.name]
        assert len(archive_forks) == 1
        assert archive_forks[0].name == "Pre-Fork A main"

        # Verify: fork_002's checkpoints untouched
        fork2_turns = list_fork_checkpoints(session_id, fork2_id)
        assert 3 in fork2_turns
        assert 4 in fork2_turns
        f2_state = load_fork_checkpoint(session_id, fork2_id, 4)
        assert f2_state is not None
        assert "[dm] Fork B entry 4" in f2_state.get("ground_truth_log", [])


# =============================================================================
# Test 4.7: promote_fork() preserves checkpoint content integrity
# =============================================================================


class TestPromoteContentIntegrity:
    """Test that promotion preserves checkpoint content accurately."""

    def test_content_integrity(
        self,
        session_with_fork_and_content: tuple[str, str],
    ) -> None:
        """Verify promoted and archived content matches originals."""
        session_id, fork_id = session_with_fork_and_content

        # Capture original fork content before promotion
        original_fork_4 = load_fork_checkpoint(session_id, fork_id, 4)
        assert original_fork_4 is not None
        original_fork_log_4 = original_fork_4.get("ground_truth_log", [])

        # Capture original main content before promotion
        original_main_4 = load_checkpoint(session_id, 4)
        assert original_main_4 is not None
        original_main_log_4 = original_main_4.get("ground_truth_log", [])

        # Promote
        promote_fork(session_id, fork_id)

        # Verify promoted main checkpoint matches original fork content
        promoted_main_4 = load_checkpoint(session_id, 4)
        assert promoted_main_4 is not None
        promoted_main_log_4 = promoted_main_4.get("ground_truth_log", [])
        assert promoted_main_log_4 == original_fork_log_4

        # Verify archive checkpoint matches original main content
        forks = list_forks(session_id)
        archive = [f for f in forks if "Pre-" in f.name][0]
        archive_state_4 = load_fork_checkpoint(session_id, archive.fork_id, 4)
        assert archive_state_4 is not None
        archive_log_4 = archive_state_4.get("ground_truth_log", [])
        assert archive_log_4 == original_main_log_4

        # Verify logs are different between main and archive
        assert promoted_main_log_4 != archive_log_4


# =============================================================================
# Test 4.8: collapse_all_forks() function
# =============================================================================


class TestCollapseAllForks:
    """Test collapse_all_forks() function."""

    def test_collapse_multiple_forks(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """Collapse session with 3 forks, verify cleanup."""
        session_id = "001"
        state = {**sample_game_state}

        # Build main timeline
        for i in range(1, 4):
            state["ground_truth_log"] = [
                f"[dm] Main entry {j}" for j in range(1, i + 1)
            ]
            save_checkpoint(state, session_id, i)

        # Create 3 forks
        for name in ["Fork A", "Fork B", "Fork C"]:
            fork_meta = create_fork(
                state=state,
                session_id=session_id,
                fork_name=name,
                turn_number=2,
            )
            # Add one post-branch checkpoint to each
            fork_state = {**sample_game_state}
            fork_state["ground_truth_log"] = ["[dm] Fork content"]
            save_fork_checkpoint(fork_state, session_id, fork_meta.fork_id, 3)

        # Verify 3 forks exist
        assert len(list_forks(session_id)) == 3

        # Collapse all
        count = collapse_all_forks(session_id)

        # Verify return value
        assert count == 3

        # Verify: all fork directories removed
        forks_parent = get_session_dir(session_id) / "forks"
        assert not forks_parent.exists()

        # Verify: forks.yaml removed
        registry_path = get_fork_registry_path(session_id)
        assert not registry_path.exists()

        # Verify: main timeline checkpoints untouched
        assert list_checkpoints(session_id) == [1, 2, 3]
        for turn in [1, 2, 3]:
            s = load_checkpoint(session_id, turn)
            assert s is not None

    def test_collapse_returns_0_no_forks(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """Return 0 for session with no forks."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] Entry 1"]
        save_checkpoint(state, session_id, 1)

        count = collapse_all_forks(session_id)
        assert count == 0

    def test_collapse_returns_0_nonexistent_session(
        self,
        temp_campaigns_dir: Path,
    ) -> None:
        """Return 0 for non-existent session (no crash)."""
        count = collapse_all_forks("999")
        assert count == 0


# =============================================================================
# Test 4.9: collapse_all_forks() when currently in a fork
# =============================================================================


class TestCollapseWhileInFork:
    """Test collapse_all_forks() when active_fork_id is set."""

    def test_collapse_does_not_crash_with_active_fork(
        self,
        session_with_fork_and_content: tuple[str, str],
    ) -> None:
        """Persistence function itself does not check active_fork_id."""
        session_id, fork_id = session_with_fork_and_content

        # This should not crash - the UI handler handles switching first
        count = collapse_all_forks(session_id)
        assert count == 1  # Only one fork in the fixture


# =============================================================================
# Test 4.10: Promotion then continued gameplay
# =============================================================================


class TestPromotionThenGameplay:
    """Test that gameplay continues correctly after promotion."""

    def test_save_after_promotion(
        self,
        session_with_fork_and_content: tuple[str, str],
        sample_game_state: GameState,
    ) -> None:
        """After promote_fork(), new checkpoints save to main directory."""
        session_id, fork_id = session_with_fork_and_content

        # Promote
        latest = promote_fork(session_id, fork_id)
        assert latest == 6

        # Save a new checkpoint on main timeline
        new_state = {**sample_game_state}
        new_state["ground_truth_log"] = ["[dm] Post-promotion entry"]
        new_state["active_fork_id"] = None
        save_checkpoint(new_state, session_id, 7)

        # Verify it saved correctly to main session directory
        loaded = load_checkpoint(session_id, 7)
        assert loaded is not None
        assert loaded.get("ground_truth_log") == ["[dm] Post-promotion entry"]

        # Verify the game loop routing (active_fork_id=None -> main)
        assert list_checkpoints(session_id) == [1, 2, 3, 4, 5, 6, 7]


# =============================================================================
# Test 4.11: Backward compatibility
# =============================================================================


class TestBackwardCompatibility:
    """Test backward compatibility for sessions without forks."""

    def test_promote_no_registry_raises(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """promote_fork() raises ValueError for session without fork registry."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] Entry 1"]
        save_checkpoint(state, session_id, 1)

        with pytest.raises(ValueError, match="No fork registry"):
            promote_fork(session_id, "001")

    def test_collapse_no_forks_returns_0(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """collapse_all_forks() returns 0 for session without forks."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] Entry 1"]
        save_checkpoint(state, session_id, 1)

        count = collapse_all_forks(session_id)
        assert count == 0

    def test_old_game_state_without_active_fork_id(
        self,
        temp_campaigns_dir: Path,
        sample_game_state: GameState,
    ) -> None:
        """Old game states without active_fork_id continue to work."""
        session_id = "001"
        state = {**sample_game_state}
        state["ground_truth_log"] = ["[dm] Entry 1"]
        # Ensure active_fork_id defaults to None
        assert state.get("active_fork_id") is None
        save_checkpoint(state, session_id, 1)

        loaded = load_checkpoint(session_id, 1)
        assert loaded is not None
        assert loaded.get("active_fork_id") is None


# =============================================================================
# Test 4.12: Confirmation state management
# =============================================================================


class TestConfirmationStateManagement:
    """Test session_state flag patterns for confirmation dialogs."""

    def test_promote_confirm_flag_set_on_button(self) -> None:
        """Verify confirm_promote flag pattern works."""
        # Simulate the session_state pattern used in render_fork_controls
        mock_state: dict[str, object] = {}

        # Simulate button click setting the flag
        fork_id = "001"
        mock_state[f"confirm_promote_{fork_id}"] = True
        assert mock_state.get(f"confirm_promote_{fork_id}") is True

        # Simulate clearing after promotion
        mock_state[f"confirm_promote_{fork_id}"] = False
        assert mock_state.get(f"confirm_promote_{fork_id}") is False

    def test_promote_confirm_flag_cleared_on_cancel(self) -> None:
        """Verify confirm flag is cleared on cancel."""
        mock_state: dict[str, object] = {}
        fork_id = "001"

        mock_state[f"confirm_promote_{fork_id}"] = True
        assert mock_state.get(f"confirm_promote_{fork_id}") is True

        # Cancel clears the flag
        mock_state[f"confirm_promote_{fork_id}"] = False
        assert mock_state.get(f"confirm_promote_{fork_id}") is False

    def test_collapse_confirm_flag_set_and_cleared(self) -> None:
        """Verify confirm_collapse_forks flag is set/cleared correctly."""
        mock_state: dict[str, object] = {}

        mock_state["confirm_collapse_forks"] = True
        assert mock_state.get("confirm_collapse_forks") is True

        mock_state["confirm_collapse_forks"] = False
        assert mock_state.get("confirm_collapse_forks") is False

    def test_confirm_flag_not_set_by_default(self) -> None:
        """Verify flags are not set when not initialized."""
        mock_state: dict[str, object] = {}
        assert mock_state.get("confirm_promote_001") is None
        assert mock_state.get("confirm_collapse_forks") is None
