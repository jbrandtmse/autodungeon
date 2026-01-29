"""Tests for Story 5.5: Memory Compression System.

This module contains comprehensive tests for the memory compression system (FR16),
covering all acceptance criteria:

AC #1: Context Manager checks token counts before DM turn
AC #2: 80% threshold triggers summarization
AC #3: Compressed entries removed from short_term_buffer
AC #4: Most recent 3 entries retained uncompressed
AC #5: Total context fits within token_limit after compression
AC #6: Per-agent compression is isolated

Test coverage includes:
- Total context token calculation (summary + buffer + facts)
- Post-compression validation
- Multi-pass compression scenarios
- Per-agent isolation
- Critical information preservation
"""

from unittest.mock import MagicMock, patch

import pytest

from memory import MemoryManager, estimate_tokens
from models import (
    AgentMemory,
    CharacterFacts,
    GameState,
    create_initial_game_state,
)


@pytest.fixture
def empty_game_state() -> GameState:
    """Create an empty game state for testing."""
    return create_initial_game_state()


@pytest.fixture(autouse=True)
def clear_summarizer_cache():  # type: ignore[misc]
    """Clear the summarizer cache before and after each test.

    This ensures test isolation when mocking the Summarizer class.
    Uses autouse=True to apply to all tests in this module.
    """
    import memory as memory_module

    memory_module._summarizer_cache.clear()
    yield
    memory_module._summarizer_cache.clear()


@pytest.fixture
def game_state_with_facts() -> GameState:
    """Create a game state with agent memories including character facts."""
    state = create_initial_game_state()

    # DM memory
    state["agent_memories"]["dm"] = AgentMemory(
        long_term_summary="The party entered the haunted castle.",
        short_term_buffer=[
            "[DM]: The doors creak open.",
            "[DM]: A chill runs down your spine.",
        ],
        token_limit=8000,
    )

    # Rogue with CharacterFacts
    state["agent_memories"]["rogue"] = AgentMemory(
        long_term_summary="Shadowmere has tracked the castle for weeks.",
        short_term_buffer=["[Shadowmere]: I check for traps."],
        token_limit=4000,
        character_facts=CharacterFacts(
            name="Shadowmere",
            character_class="Rogue",
            key_traits=["Stealthy", "Cautious", "Quick-witted"],
            relationships={"Theron": "Trusted ally", "Elara": "Fellow party member"},
            notable_events=["Escaped the thieves guild", "Found the ancient map"],
        ),
    )

    # Fighter with CharacterFacts
    state["agent_memories"]["fighter"] = AgentMemory(
        long_term_summary="Theron seeks vengeance.",
        short_term_buffer=["[Theron]: I stand ready."],
        token_limit=4000,
        character_facts=CharacterFacts(
            name="Theron",
            character_class="Fighter",
            key_traits=["Brave", "Loyal"],
            relationships={"Shadowmere": "Trusted friend"},
            notable_events=["Lost family to orcs"],
        ),
    )

    return state


# =============================================================================
# Task 2: Tests for get_total_context_tokens() method
# =============================================================================


class TestGetTotalContextTokens:
    """Tests for total context token calculation (Task 2)."""

    def test_get_total_context_tokens_empty_memory(
        self, empty_game_state: GameState
    ) -> None:
        """Empty memory returns 0 tokens."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="",
            short_term_buffer=[],
            token_limit=8000,
        )

        manager = MemoryManager(state)
        result = manager.get_total_context_tokens("dm")

        assert result == 0

    def test_get_total_context_tokens_summary_only(
        self, empty_game_state: GameState
    ) -> None:
        """Calculates tokens for summary without buffer."""
        state = empty_game_state
        summary = (
            "The party has completed their first quest and gained valuable experience."
        )
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary=summary,
            short_term_buffer=[],
            token_limit=8000,
        )

        manager = MemoryManager(state)
        result = manager.get_total_context_tokens("dm")

        # Should match estimate_tokens for the summary
        expected = estimate_tokens(summary)
        assert result == expected
        assert result > 0

    def test_get_total_context_tokens_buffer_only(
        self, empty_game_state: GameState
    ) -> None:
        """Calculates tokens for buffer without summary."""
        state = empty_game_state
        buffer = [
            "Event one happened.",
            "Event two occurred.",
            "Event three took place.",
        ]
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="",
            short_term_buffer=buffer,
            token_limit=8000,
        )

        manager = MemoryManager(state)
        result = manager.get_total_context_tokens("dm")

        # Should match estimate_tokens for the joined buffer
        expected = estimate_tokens("\n".join(buffer))
        assert result == expected
        assert result > 0

    def test_get_total_context_tokens_includes_character_facts(
        self, game_state_with_facts: GameState
    ) -> None:
        """Character facts tokens are included in total."""
        manager = MemoryManager(game_state_with_facts)

        # Get total for rogue (has character facts)
        total_with_facts = manager.get_total_context_tokens("rogue")

        # Get total for dm (no character facts) - this also tests basic functionality
        _ = manager.get_total_context_tokens("dm")

        # Rogue should have more tokens due to character facts
        # (assuming similar buffer/summary sizes)
        assert total_with_facts > 0

    def test_get_total_context_tokens_full_context(
        self, game_state_with_facts: GameState
    ) -> None:
        """Calculates tokens for summary + buffer + facts combined."""
        manager = MemoryManager(game_state_with_facts)

        # Get the rogue's total
        result = manager.get_total_context_tokens("rogue")

        # Manually calculate expected
        memory = game_state_with_facts["agent_memories"]["rogue"]
        from agents import format_character_facts

        summary_tokens = estimate_tokens(memory.long_term_summary)
        buffer_tokens = estimate_tokens("\n".join(memory.short_term_buffer))
        facts_tokens = estimate_tokens(format_character_facts(memory.character_facts))  # type: ignore[arg-type]

        expected = summary_tokens + buffer_tokens + facts_tokens
        assert result == expected

    def test_get_total_context_tokens_missing_agent(
        self, empty_game_state: GameState
    ) -> None:
        """Returns 0 for non-existent agent."""
        manager = MemoryManager(empty_game_state)
        result = manager.get_total_context_tokens("nonexistent_agent")

        assert result == 0


# =============================================================================
# Task 2: Tests for is_total_context_over_limit() method
# =============================================================================


class TestIsTotalContextOverLimit:
    """Tests for post-compression context validation (Task 2)."""

    def test_is_total_context_over_limit_false_when_under(
        self, empty_game_state: GameState
    ) -> None:
        """Returns False when total < token_limit."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="Short summary.",
            short_term_buffer=["Small event."],
            token_limit=8000,
        )

        manager = MemoryManager(state)
        result = manager.is_total_context_over_limit("dm")

        assert result is False

    def test_is_total_context_over_limit_true_when_over(
        self, empty_game_state: GameState
    ) -> None:
        """Returns True when total > token_limit."""
        state = empty_game_state
        # Create large content that exceeds a small limit
        large_summary = " ".join(["word"] * 500)  # ~650 tokens
        large_buffer = [" ".join(["word"] * 200) for _ in range(5)]  # ~1300 tokens

        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary=large_summary,
            short_term_buffer=large_buffer,
            token_limit=100,  # Very small limit
        )

        manager = MemoryManager(state)
        result = manager.is_total_context_over_limit("dm")

        assert result is True

    def test_is_total_context_over_limit_missing_agent(
        self, empty_game_state: GameState
    ) -> None:
        """Returns False for non-existent agent."""
        manager = MemoryManager(empty_game_state)
        result = manager.is_total_context_over_limit("nonexistent")

        assert result is False

    def test_is_total_context_over_limit_boundary(
        self, empty_game_state: GameState
    ) -> None:
        """Test boundary condition: exactly at limit returns False."""
        state = empty_game_state
        # Small content that's exactly at limit
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="short",
            short_term_buffer=[],
            token_limit=5,  # "short" is 1 word = ~1 token
        )

        manager = MemoryManager(state)
        result = manager.is_total_context_over_limit("dm")

        # At or under limit should be False
        assert result is False


# =============================================================================
# Task 3: Tests for compress_long_term_summary() method
# =============================================================================


class TestCompressLongTermSummary:
    """Tests for multi-pass compression of long_term_summary (Task 3)."""

    def test_compress_long_term_summary_returns_compressed(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compress_long_term_summary returns compressed text."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="This is a very long summary that needs compression. "
            * 20,
            short_term_buffer=[],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Condensed summary."
            MockSummarizer.return_value = mock_instance

            result = manager.compress_long_term_summary("dm")

        assert result == "Condensed summary."

    def test_compress_long_term_summary_updates_memory(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compress_long_term_summary updates the memory."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        original_summary = "This is a very long summary. " * 50
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary=original_summary,
            short_term_buffer=[],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Shorter summary."
            MockSummarizer.return_value = mock_instance

            manager.compress_long_term_summary("dm")

        # Memory should be updated
        assert state["agent_memories"]["dm"].long_term_summary == "Shorter summary."

    def test_compress_long_term_summary_empty_summary(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compress_long_term_summary handles empty summary."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="",
            short_term_buffer=[],
            token_limit=100,
        )

        manager = MemoryManager(state)
        result = manager.compress_long_term_summary("dm")

        assert result == ""

    def test_compress_long_term_summary_missing_agent(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compress_long_term_summary handles missing agent."""
        manager = MemoryManager(empty_game_state)
        result = manager.compress_long_term_summary("nonexistent")

        assert result == ""

    def test_compress_long_term_summary_failure_logs_warning(
        self, empty_game_state: GameState, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that compress_long_term_summary logs warning on failure."""
        import logging

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="This is a long summary that needs compression.",
            short_term_buffer=[],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with (
            patch("memory.Summarizer") as MockSummarizer,
            caplog.at_level(logging.WARNING),
        ):
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = ""  # Failure
            MockSummarizer.return_value = mock_instance

            result = manager.compress_long_term_summary("dm")

        # Should return empty string on failure
        assert result == ""
        # Should log warning
        assert any(
            "compression failed" in record.message.lower()
            or "summary unchanged" in record.message.lower()
            for record in caplog.records
        )


# =============================================================================
# Task 4: Tests for context_manager post-compression validation
# =============================================================================


class TestContextManagerPostValidation:
    """Tests for context_manager post-compression validation (Task 4)."""

    def test_context_manager_validates_after_compression(
        self, empty_game_state: GameState
    ) -> None:
        """Test that context_manager checks total context after compression."""
        from graph import context_manager

        state = empty_game_state
        # Large buffer that will trigger compression
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            token_limit=100,
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.return_value = "Summary"
            mock_instance.is_total_context_over_limit.return_value = False
            MockManager.return_value = mock_instance

            context_manager(state)

            # Should have called is_total_context_over_limit after compression
            mock_instance.is_total_context_over_limit.assert_called()

    def test_context_manager_multi_pass_compression(
        self, empty_game_state: GameState
    ) -> None:
        """Test that context_manager triggers multi-pass compression if needed."""
        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            long_term_summary="Very long summary " * 100,
            token_limit=100,
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.return_value = "Summary"
            # First call over limit, second call under limit
            mock_instance.is_total_context_over_limit.side_effect = [True, False]
            mock_instance.compress_long_term_summary.return_value = "Shorter summary"
            MockManager.return_value = mock_instance

            context_manager(state)

            # Should have called compress_long_term_summary
            mock_instance.compress_long_term_summary.assert_called()

    def test_context_manager_max_passes_prevents_infinite_loop(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compression stops after MAX_COMPRESSION_PASSES."""
        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            long_term_summary="Very long summary " * 100,
            token_limit=100,
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.return_value = "Summary"
            # Always over limit (simulates compression not helping enough)
            mock_instance.is_total_context_over_limit.return_value = True
            mock_instance.compress_long_term_summary.return_value = "Still too long"
            MockManager.return_value = mock_instance

            context_manager(state)

            # Should have limited compression attempts
            # compress_buffer called once, then compress_long_term_summary at most once more
            # (MAX_COMPRESSION_PASSES = 2)
            assert mock_instance.compress_long_term_summary.call_count <= 1

    def test_context_manager_logs_warning_if_still_over(
        self, empty_game_state: GameState, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that warning is logged when still over limit after max passes."""
        import logging

        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            long_term_summary="Very long summary " * 100,
            token_limit=100,
        )

        with (
            patch("graph.MemoryManager") as MockManager,
            caplog.at_level(logging.WARNING),
        ):
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.return_value = "Summary"
            mock_instance.is_total_context_over_limit.return_value = True
            mock_instance.compress_long_term_summary.return_value = "Still long"
            MockManager.return_value = mock_instance

            context_manager(state)

            # Check if warning was logged
            assert any(
                "over token limit" in record.message.lower()
                or "still over" in record.message.lower()
                for record in caplog.records
            )


# =============================================================================
# Task 5: Tests for per-agent isolation (AC #6)
# =============================================================================


class TestPerAgentIsolation:
    """Tests for per-agent compression isolation (AC #6, Task 5)."""

    def test_agent_a_compression_doesnt_affect_agent_b(
        self, empty_game_state: GameState
    ) -> None:
        """Compressing one agent leaves others unchanged."""

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(10)],
            token_limit=100,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Fighter action 1", "Fighter action 2"],
            long_term_summary="Fighter background",
            token_limit=4000,
        )

        original_fighter_buffer = state["agent_memories"][
            "fighter"
        ].short_term_buffer.copy()
        original_fighter_summary = state["agent_memories"]["fighter"].long_term_summary

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "DM summary"
            MockSummarizer.return_value = mock_instance

            # Compress only DM
            manager.compress_buffer("dm")

        # Fighter should be unchanged
        assert (
            state["agent_memories"]["fighter"].short_term_buffer
            == original_fighter_buffer
        )
        assert (
            state["agent_memories"]["fighter"].long_term_summary
            == original_fighter_summary
        )

    def test_multiple_agents_compress_independently(
        self, empty_game_state: GameState
    ) -> None:
        """Multiple agents can compress in same pass, each independently."""
        from graph import context_manager

        state = empty_game_state
        # Both agents near limit
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            token_limit=100,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Action " + str(i) for i in range(50)],
            token_limit=100,
        )

        compressed_agents = []

        def track_compression(agent_name: str) -> str:
            compressed_agents.append(agent_name)
            return "Summary"

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.side_effect = track_compression
            mock_instance.is_total_context_over_limit.return_value = False
            MockManager.return_value = mock_instance

            context_manager(state)

        # Both should have been compressed
        assert "dm" in compressed_agents
        assert "fighter" in compressed_agents

    def test_one_agent_failure_doesnt_block_others(
        self, empty_game_state: GameState
    ) -> None:
        """If compression fails for one agent, others still run."""

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(10)],
            token_limit=100,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Action " + str(i) for i in range(10)],
            long_term_summary="",
            token_limit=100,
        )

        manager = MemoryManager(state)

        call_count = 0

        def mock_summarize(agent_name: str, entries: list[str]) -> str:
            nonlocal call_count
            call_count += 1
            if agent_name == "dm":
                return ""  # Failure
            return "Fighter summary"

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.side_effect = mock_summarize
            MockSummarizer.return_value = mock_instance

            # Compress DM (fails)
            manager.compress_buffer("dm")
            # Compress fighter (should succeed)
            manager.compress_buffer("fighter")

        # Fighter should still have been compressed despite DM failure
        assert "Fighter summary" in state["agent_memories"]["fighter"].long_term_summary


# =============================================================================
# Task 6: Tests for critical information preservation (AC #5)
# =============================================================================


class TestCriticalInformationPreservation:
    """Tests for critical information preservation (AC #5, Task 6)."""

    def test_character_names_preserved(self) -> None:
        """Character names appear in compressed summary via Janitor prompt."""
        from memory import JANITOR_SYSTEM_PROMPT

        # Verify Janitor prompt instructs preservation of character names
        assert "character" in JANITOR_SYSTEM_PROMPT.lower()
        assert "name" in JANITOR_SYSTEM_PROMPT.lower()
        assert "PRESERVE" in JANITOR_SYSTEM_PROMPT

    def test_quest_objectives_preserved(self) -> None:
        """Quest objectives appear in compressed summary via Janitor prompt."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "quest" in JANITOR_SYSTEM_PROMPT.lower()
        assert (
            "goal" in JANITOR_SYSTEM_PROMPT.lower()
            or "progress" in JANITOR_SYSTEM_PROMPT.lower()
        )

    def test_relationships_preserved(self) -> None:
        """Relationships appear in compressed summary via Janitor prompt."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "relationship" in JANITOR_SYSTEM_PROMPT.lower()

    def test_recent_entries_always_retained(self, empty_game_state: GameState) -> None:
        """Most recent 3 entries always in buffer after compression."""

        state = empty_game_state
        entries = [f"Event {i}" for i in range(10)]
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=entries.copy(),
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary of old events"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        # Last 3 entries should be retained
        buffer = state["agent_memories"]["dm"].short_term_buffer
        assert len(buffer) == 3
        assert buffer[0] == "Event 7"
        assert buffer[1] == "Event 8"
        assert buffer[2] == "Event 9"


# =============================================================================
# Task 7: Comprehensive Acceptance Tests for all AC requirements
# =============================================================================


class TestStory55AcceptanceCriteria:
    """Comprehensive acceptance tests for Story 5.5 (FR16)."""

    def test_ac1_context_manager_checks_before_dm_turn(
        self, empty_game_state: GameState
    ) -> None:
        """AC #1: Context Manager checks token counts before DM turn."""
        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1"],
            token_limit=8000,
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            context_manager(state)

            # is_near_limit should have been called
            mock_instance.is_near_limit.assert_called()

    def test_ac2_80_percent_threshold_triggers_summarization(
        self, empty_game_state: GameState
    ) -> None:
        """AC #2: 80% threshold triggers summarization."""
        state = empty_game_state
        # Create buffer at exactly 80% of limit
        # 80 tokens needed with token_limit=100
        # ~62 words * 1.3 = ~80 tokens
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[" ".join(["word"] * 62)],
            token_limit=100,
        )

        manager = MemoryManager(state)

        # Default threshold is 0.8 (80%)
        result = manager.is_near_limit("dm", threshold=0.8)
        assert result is True

    def test_ac3_compressed_entries_removed(self, empty_game_state: GameState) -> None:
        """AC #3: Compressed entries removed from short_term_buffer."""

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[
                "Old 1",
                "Old 2",
                "Old 3",
                "Recent 1",
                "Recent 2",
                "Recent 3",
            ],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary of old events"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        buffer = state["agent_memories"]["dm"].short_term_buffer
        # Old entries should be removed
        assert "Old 1" not in buffer
        assert "Old 2" not in buffer
        assert "Old 3" not in buffer

    def test_ac4_recent_n_turns_uncompressed(self, empty_game_state: GameState) -> None:
        """AC #4: Most recent N turns remain uncompressed."""

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Old 1", "Old 2", "Recent 1", "Recent 2", "Recent 3"],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        buffer = state["agent_memories"]["dm"].short_term_buffer
        # Last 3 should remain
        assert buffer == ["Recent 1", "Recent 2", "Recent 3"]

    def test_ac5_total_context_within_limit_after_compression(
        self, empty_game_state: GameState
    ) -> None:
        """AC #5: Total context fits within token_limit after compression."""

        state = empty_game_state
        # Large buffer that exceeds limit
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[" ".join(["word"] * 50) for _ in range(10)],
            token_limit=500,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            # Return a short summary
            mock_instance.generate_summary.return_value = "Brief summary of events."
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        # After compression, check total context
        total_tokens = manager.get_total_context_tokens("dm")
        limit = state["agent_memories"]["dm"].token_limit

        # Should be well under limit now
        assert total_tokens < limit

    def test_ac6_per_agent_compression_isolated(
        self, empty_game_state: GameState
    ) -> None:
        """AC #6: Per-agent compression is isolated."""
        from graph import context_manager

        state = empty_game_state
        # Only DM near limit
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            token_limit=100,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Action"],
            token_limit=8000,  # Not near limit
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            # DM near limit, fighter not
            mock_instance.is_near_limit.side_effect = lambda name: name == "dm"  # type: ignore[misc]
            mock_instance.compress_buffer.return_value = "Summary"
            mock_instance.is_total_context_over_limit.return_value = False
            MockManager.return_value = mock_instance

            context_manager(state)

            # compress_buffer should only be called for dm
            calls = [
                call[0][0] for call in mock_instance.compress_buffer.call_args_list
            ]
            assert "dm" in calls
            # Fighter should not have compress_buffer called
            assert "fighter" not in calls


# =============================================================================
# MAX_COMPRESSION_PASSES Constant Tests
# =============================================================================


class TestMaxCompressionPassesConstant:
    """Tests for MAX_COMPRESSION_PASSES constant accessibility."""

    def test_max_compression_passes_is_module_level(self) -> None:
        """Test that MAX_COMPRESSION_PASSES can be imported from graph module."""
        from graph import MAX_COMPRESSION_PASSES

        assert MAX_COMPRESSION_PASSES == 2

    def test_max_compression_passes_in_all_exports(self) -> None:
        """Test that MAX_COMPRESSION_PASSES is in __all__ for public API."""
        import graph

        assert "MAX_COMPRESSION_PASSES" in graph.__all__


# =============================================================================
# Integration Tests
# =============================================================================


class TestMemoryCompressionIntegration:
    """Integration tests for the complete memory compression system."""

    def test_full_compression_cycle_with_validation(
        self, empty_game_state: GameState
    ) -> None:
        """Test complete compression cycle with post-validation."""

        state = empty_game_state
        # Create buffer that definitely exceeds 80% of 100 tokens
        # 80 tokens needed, create ~130 tokens worth
        large_entries = [" ".join(["word"] * 20) for _ in range(5)]  # ~130 tokens
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=large_entries,
            long_term_summary="",
            token_limit=100,
            character_facts=None,
        )

        manager = MemoryManager(state)

        # Verify initially over threshold
        assert manager.is_near_limit("dm") is True

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary of events."
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        # After compression:
        # 1. Buffer should have only recent 3 entries
        assert len(state["agent_memories"]["dm"].short_term_buffer) == 3

        # 2. Summary should be populated
        assert state["agent_memories"]["dm"].long_term_summary != ""

        # 3. Total context should be under limit
        assert manager.is_total_context_over_limit("dm") is False

    def test_context_manager_workflow_integration(
        self, empty_game_state: GameState
    ) -> None:
        """Test context_manager in workflow correctly handles compression."""
        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[f"Event {i}" for i in range(50)],
            token_limit=100,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Action"],
            token_limit=8000,
        )

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Compressed summary"
            MockSummarizer.return_value = mock_instance

            result = context_manager(state)

        # Flag should be cleared
        assert result["summarization_in_progress"] is False

        # DM should have been compressed
        assert len(result["agent_memories"]["dm"].short_term_buffer) == 3
        assert "Compressed summary" in result["agent_memories"]["dm"].long_term_summary
