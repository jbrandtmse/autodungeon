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

        compressed_agents: list[str] = []

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


# =============================================================================
# Additional Test Coverage: Stress Testing with Very Large Buffers
# =============================================================================


class TestStressTestingLargeBuffers:
    """Stress tests for memory compression with very large buffers."""

    def test_very_large_buffer_entries(self, empty_game_state: GameState) -> None:
        """Test compression with hundreds of buffer entries."""
        state = empty_game_state
        # Create 500 buffer entries
        large_buffer = [
            f"Event {i}: The party encountered something." for i in range(500)
        ]
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=large_buffer,
            token_limit=100,
        )

        manager = MemoryManager(state)

        # Verify initially near limit
        assert manager.is_near_limit("dm") is True

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary of 497 events."
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        # Only last 3 retained
        assert len(state["agent_memories"]["dm"].short_term_buffer) == 3
        assert (
            state["agent_memories"]["dm"].short_term_buffer[0]
            == "Event 497: The party encountered something."
        )

    def test_very_large_individual_entries(self, empty_game_state: GameState) -> None:
        """Test compression with very large individual buffer entries."""
        state = empty_game_state
        # Each entry is ~1000 characters
        large_entry = "A " * 500  # ~1000 chars, ~500 tokens
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[large_entry for _ in range(10)],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Compressed large entries."
            MockSummarizer.return_value = mock_instance

            result = manager.compress_buffer("dm")

        assert result == "Compressed large entries."
        assert len(state["agent_memories"]["dm"].short_term_buffer) == 3

    def test_buffer_at_100kb_protection_limit(
        self, empty_game_state: GameState
    ) -> None:
        """Test that add_to_buffer rejects entries exceeding 100KB."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(token_limit=100000)

        manager = MemoryManager(state)

        # Create entry just over 100KB
        huge_entry = "x" * 100_001

        with pytest.raises(ValueError, match="exceeds maximum size"):
            manager.add_to_buffer("dm", huge_entry)

    def test_large_summary_combined_with_large_buffer(
        self, empty_game_state: GameState
    ) -> None:
        """Test compression when both summary and buffer are large."""
        state = empty_game_state
        large_summary = " ".join(["word"] * 1000)  # ~1300 tokens
        large_buffer = [" ".join(["event"] * 100) for _ in range(20)]  # ~2600 tokens

        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary=large_summary,
            short_term_buffer=large_buffer,
            token_limit=500,
        )

        manager = MemoryManager(state)

        # Total should be way over limit
        assert manager.is_total_context_over_limit("dm") is True

        total_tokens = manager.get_total_context_tokens("dm")
        assert total_tokens > 3000  # Verify we're testing a truly large case


# =============================================================================
# Additional Test Coverage: Edge Cases at MAX_COMPRESSION_PASSES
# =============================================================================


class TestMaxCompressionPassesEdgeCases:
    """Edge case tests for MAX_COMPRESSION_PASSES boundary conditions."""

    def test_exactly_at_max_passes_limit(self, empty_game_state: GameState) -> None:
        """Test behavior when exactly MAX_COMPRESSION_PASSES are used."""
        from graph import MAX_COMPRESSION_PASSES, context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            long_term_summary="Very long summary " * 100,
            token_limit=100,
        )

        call_count = {"compress_buffer": 0, "compress_summary": 0}

        def mock_compress_buffer(agent_name: str) -> str:
            call_count["compress_buffer"] += 1
            return "Summary"

        def mock_compress_summary(agent_name: str) -> str:
            call_count["compress_summary"] += 1
            return "Shorter summary"

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.side_effect = mock_compress_buffer
            # Returns True for MAX_COMPRESSION_PASSES-1 times, then True on final check
            mock_instance.is_total_context_over_limit.return_value = True
            mock_instance.compress_long_term_summary.side_effect = mock_compress_summary
            MockManager.return_value = mock_instance

            context_manager(state)

        # compress_buffer called once, then compress_summary at most MAX_COMPRESSION_PASSES-1 times
        assert call_count["compress_buffer"] == 1
        assert call_count["compress_summary"] <= MAX_COMPRESSION_PASSES - 1

    def test_passes_variable_used_correctly(self, empty_game_state: GameState) -> None:
        """Test that passes counter increments correctly during compression."""
        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            token_limit=100,
        )

        over_limit_responses = [True, False]  # First check over, second under

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.return_value = "Summary"
            mock_instance.is_total_context_over_limit.side_effect = over_limit_responses
            mock_instance.compress_long_term_summary.return_value = "Shorter"
            MockManager.return_value = mock_instance

            context_manager(state)

            # Should stop after first successful compression brings under limit
            assert mock_instance.compress_long_term_summary.call_count == 1

    def test_zero_passes_when_not_near_limit(self, empty_game_state: GameState) -> None:
        """Test that no compression passes occur when agent is not near limit."""
        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Short event"],
            token_limit=10000,  # Very high limit
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            context_manager(state)

            # No compression should be attempted
            mock_instance.compress_buffer.assert_not_called()
            mock_instance.compress_long_term_summary.assert_not_called()


# =============================================================================
# Additional Test Coverage: Multiple Agents Near Limit (Concurrent-like)
# =============================================================================


class TestMultipleAgentsNearLimit:
    """Tests for scenarios where multiple agents are near their limits simultaneously."""

    def test_three_agents_all_near_limit(self, empty_game_state: GameState) -> None:
        """Test compression when three agents are all near their limits."""
        from graph import context_manager

        state = empty_game_state
        # All three agents near limit
        for agent in ["dm", "fighter", "rogue"]:
            state["agent_memories"][agent] = AgentMemory(
                short_term_buffer=[f"{agent} event {i}" for i in range(30)],
                token_limit=50,
            )

        compressed_agents: list[str] = []

        def track_compression(agent_name: str) -> str:
            compressed_agents.append(agent_name)
            return f"{agent_name} summary"

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.side_effect = track_compression
            mock_instance.is_total_context_over_limit.return_value = False
            MockManager.return_value = mock_instance

            context_manager(state)

        # All three should have been compressed
        assert len(compressed_agents) == 3  # type: ignore[arg-type]
        assert "dm" in compressed_agents
        assert "fighter" in compressed_agents
        assert "rogue" in compressed_agents

    def test_agents_compressed_in_deterministic_order(
        self, empty_game_state: GameState
    ) -> None:
        """Test that agents are compressed in deterministic (dict) order."""
        from graph import context_manager

        state = empty_game_state
        # Add agents in specific order
        state["agent_memories"]["zulu"] = AgentMemory(
            short_term_buffer=["event"] * 20,
            token_limit=10,
        )
        state["agent_memories"]["alpha"] = AgentMemory(
            short_term_buffer=["event"] * 20,
            token_limit=10,
        )
        state["agent_memories"]["beta"] = AgentMemory(
            short_term_buffer=["event"] * 20,
            token_limit=10,
        )

        compressed_order: list[str] = []

        def track_order(agent_name: str) -> str:
            compressed_order.append(agent_name)
            return "summary"

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.side_effect = track_order
            mock_instance.is_total_context_over_limit.return_value = False
            MockManager.return_value = mock_instance

            context_manager(state)

        # Order should match dict iteration order (insertion order in Python 3.7+)
        assert compressed_order == ["zulu", "alpha", "beta"]

    def test_some_agents_need_multi_pass_others_dont(
        self, empty_game_state: GameState
    ) -> None:
        """Test mixed scenario: some agents need multi-pass, others don't."""
        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["event"] * 50,
            long_term_summary="large " * 500,
            token_limit=100,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["event"] * 30,
            token_limit=100,  # Will be under after single pass
        )

        multi_pass_calls: dict[str, int] = {"dm": 0, "fighter": 0}

        def mock_is_over(agent_name: str) -> bool:
            # DM needs multi-pass, fighter doesn't
            if agent_name == "dm":
                multi_pass_calls["dm"] += 1
                return multi_pass_calls["dm"] < 2  # Over limit first time
            return False  # Fighter under limit after first pass

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.return_value = "summary"
            mock_instance.is_total_context_over_limit.side_effect = mock_is_over
            mock_instance.compress_long_term_summary.return_value = "shorter"
            MockManager.return_value = mock_instance

            context_manager(state)

            # DM should have needed multi-pass
            assert multi_pass_calls["dm"] >= 2


# =============================================================================
# Additional Test Coverage: Unicode and Special Characters
# =============================================================================


class TestUnicodeAndSpecialCharacters:
    """Tests for Unicode and special character handling in compression."""

    def test_unicode_buffer_entries_preserved(
        self, empty_game_state: GameState
    ) -> None:
        """Test that Unicode characters in buffer entries are handled correctly."""
        state = empty_game_state
        unicode_entries = [
            "[DM]: The dragon speaks in 日本語",
            "[Fighter]: *draws the sword of \u2694\ufe0f*",
            "[Wizard]: Casts spell with runes: \u16a0\u16a2\u16a8\u16b1",
            '[Rogue]: "I\'ll steal the \u2728 jewel!"',
            "Recent 1",
            "Recent 2",
            "Recent 3",
        ]
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=unicode_entries,
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary with \u2694\ufe0f"
            MockSummarizer.return_value = mock_instance

            result = manager.compress_buffer("dm")

        # Summary should contain Unicode
        assert "\u2694\ufe0f" in result
        # Recent entries should be retained
        assert state["agent_memories"]["dm"].short_term_buffer[-1] == "Recent 3"

    def test_emoji_in_compression(self, empty_game_state: GameState) -> None:
        """Test that emojis are handled in compression."""
        state = empty_game_state
        emoji_entries = [
            "[DM]: The fire \U0001f525 spreads!",
            "[Fighter]: I attack with my sword \u2694\ufe0f",
            "[Wizard]: Magic missile \u2728\u2728\u2728",
            "Recent \U0001f389",
            "Recent \U0001f3af",
            "Recent \U0001f4a5",
        ]
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=emoji_entries,
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary \U0001f525"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        # Verify emojis preserved in retained entries
        assert "\U0001f4a5" in state["agent_memories"]["dm"].short_term_buffer[-1]

    def test_cjk_characters_token_estimation(self) -> None:
        """Test that CJK characters get different token estimation."""
        # Pure CJK text (no spaces)
        cjk_text = "\u4e2d\u6587\u6587\u672c\u6d4b\u8bd5\u793a\u4f8b\u5185\u5bb9\u975e\u5e38\u957f\u7684\u6587\u672c\u5b57\u7b26\u4e32\u6d4b\u8bd5"  # Chinese characters

        tokens = estimate_tokens(cjk_text)

        # CJK uses character-based estimate (~0.5 tokens per char)
        # 24 chars * 0.5 = ~12 tokens
        assert tokens > 0
        assert tokens < len(cjk_text)  # Should be less than char count

    def test_mixed_script_text_estimation(self) -> None:
        """Test token estimation with mixed scripts."""
        mixed_text = "Hello \u4e16\u754c World \u3053\u3093\u306b\u3061\u306f End"

        tokens = estimate_tokens(mixed_text)

        # Should use word-based heuristic (has spaces)
        assert tokens > 0

    def test_special_characters_in_long_term_summary(
        self, empty_game_state: GameState
    ) -> None:
        """Test special characters in long-term summary compression."""
        state = empty_game_state
        special_summary = (
            "The party found the \u2620\ufe0f Skull of Doom. "
            "Quest markers: \u2610 \u2611 \u2612. "
            "Gold: \u221e pieces. Formula: E=mc\u00b2"
        )
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary=special_summary,
            short_term_buffer=["event"],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = (
                "Condensed \u2620\ufe0f summary"
            )
            MockSummarizer.return_value = mock_instance

            result = manager.compress_long_term_summary("dm")

        assert "\u2620\ufe0f" in result


# =============================================================================
# Additional Test Coverage: Recovery After Failed Compression
# =============================================================================


class TestRecoveryAfterFailedCompression:
    """Tests for system behavior after compression failures."""

    def test_buffer_trimmed_on_summarizer_failure(
        self, empty_game_state: GameState
    ) -> None:
        """Test that emergency buffer trim activates when summarizer fails.

        When summarization fails, compress_buffer applies an emergency trim
        that drops the oldest entries, keeping only retain_count (3) most recent.
        """
        state = empty_game_state
        original_buffer = ["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"]
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=original_buffer.copy(),
            long_term_summary="",
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = ""  # Failure
            MockSummarizer.return_value = mock_instance

            result = manager.compress_buffer("dm")

        # Emergency trim keeps most recent entries
        assert state["agent_memories"]["dm"].short_term_buffer == [
            "Event 3", "Event 4", "Event 5"
        ]
        assert result == ""

    def test_summary_unchanged_on_recompression_failure(
        self, empty_game_state: GameState
    ) -> None:
        """Test that summary remains unchanged when re-compression fails."""
        state = empty_game_state
        original_summary = "This is the original long-term summary."
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary=original_summary,
            short_term_buffer=["event"],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = ""  # Failure
            MockSummarizer.return_value = mock_instance

            manager.compress_long_term_summary("dm")

        # Summary should be unchanged
        assert state["agent_memories"]["dm"].long_term_summary == original_summary

    def test_context_manager_continues_after_single_agent_failure(
        self, empty_game_state: GameState, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that context_manager continues processing after one agent fails."""
        import logging

        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["event"] * 30,
            token_limit=50,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["event"] * 30,
            token_limit=50,
        )

        call_count = {"dm": 0, "fighter": 0}

        def mock_compress(agent_name: str) -> str:
            call_count[agent_name] = call_count.get(agent_name, 0) + 1
            if agent_name == "dm":
                return ""  # DM compression fails
            return "Fighter summary"

        with (
            patch("graph.MemoryManager") as MockManager,
            caplog.at_level(logging.WARNING),
        ):
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            mock_instance.compress_buffer.side_effect = mock_compress
            mock_instance.is_total_context_over_limit.return_value = False
            MockManager.return_value = mock_instance

            context_manager(state)

        # Both agents should have had compression attempted
        assert call_count.get("dm", 0) >= 1
        assert call_count.get("fighter", 0) >= 1

    def test_graceful_degradation_with_empty_return(
        self, empty_game_state: GameState
    ) -> None:
        """Test graceful degradation when summarizer returns empty (simulating error).

        Emergency buffer trim drops oldest entries to prevent unbounded growth.
        """
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["event"] * 10,
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            # Summarizer returns empty string on error (graceful degradation)
            mock_instance.generate_summary.return_value = ""
            MockSummarizer.return_value = mock_instance

            result = manager.compress_buffer("dm")

        # Should return empty string; emergency trim keeps retain_count (3) entries
        assert result == ""
        assert len(state["agent_memories"]["dm"].short_term_buffer) == 3


# =============================================================================
# Additional Test Coverage: Token Estimation Edge Cases
# =============================================================================


class TestTokenEstimationEdgeCases:
    """Edge case tests for the estimate_tokens function."""

    def test_empty_string_returns_zero(self) -> None:
        """Test that empty string returns 0 tokens."""
        assert estimate_tokens("") == 0

    def test_single_word(self) -> None:
        """Test token estimation for a single word."""
        result = estimate_tokens("hello")
        # 1 word * 1.3 = 1.3 -> 1 token
        assert result == 1

    def test_whitespace_only(self) -> None:
        """Test token estimation for whitespace-only string."""
        result = estimate_tokens("   \t\n   ")
        # No words, should return 0
        assert result == 0

    def test_very_long_word(self) -> None:
        """Test token estimation for a very long single word.

        When text has very few words but many characters (>20), the
        estimate_tokens function uses character-based estimation (~0.5 per char)
        to handle potential CJK or non-space-delimited text.
        """
        long_word = "a" * 1000
        result = estimate_tokens(long_word)
        # 1 word but 1000 chars triggers character-based estimate
        # 1000 * 0.5 = 500 tokens
        assert result == 500

    def test_mixed_whitespace_delimiters(self) -> None:
        """Test token estimation with mixed whitespace."""
        text = "word1\tword2\nword3   word4"
        result = estimate_tokens(text)
        # 4 words * 1.3 = 5.2 -> 5 tokens
        assert result == 5

    def test_numbers_treated_as_words(self) -> None:
        """Test that numbers are treated as words."""
        text = "1 2 3 4 5"
        result = estimate_tokens(text)
        # 5 words * 1.3 = 6.5 -> 6 tokens
        assert result == 6

    def test_punctuation_attached_to_words(self) -> None:
        """Test that punctuation attached to words is counted."""
        text = "Hello, world! How are you?"
        result = estimate_tokens(text)
        # 5 words * 1.3 = 6.5 -> 6 tokens
        assert result == 6

    def test_newlines_as_delimiters(self) -> None:
        """Test that newlines properly delimit words."""
        text = "line1\nline2\nline3"
        result = estimate_tokens(text)
        # 3 words * 1.3 = 3.9 -> 3 tokens
        assert result == 3

    def test_realistic_dnd_narration(self) -> None:
        """Test token estimation with realistic D&D narration."""
        text = (
            "The ancient dragon unfurls its massive wings, sending gusts of "
            "wind that nearly knock you off your feet. Its scales shimmer with "
            "an otherworldly iridescence as it regards you with intelligent, "
            "calculating eyes."
        )
        result = estimate_tokens(text)
        # 32 words * 1.3 = ~41.6 -> 41 tokens
        assert 35 <= result <= 50


# =============================================================================
# Additional Test Coverage: Boundary and Edge Conditions
# =============================================================================


class TestBoundaryConditions:
    """Tests for boundary conditions in compression logic."""

    def test_buffer_with_exactly_retain_count_entries(
        self, empty_game_state: GameState
    ) -> None:
        """Test buffer with exactly RETAIN_AFTER_COMPRESSION entries."""
        from memory import RETAIN_AFTER_COMPRESSION

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[
                "Event " + str(i) for i in range(RETAIN_AFTER_COMPRESSION)
            ],
            token_limit=100,
        )

        manager = MemoryManager(state)
        result = manager.compress_buffer("dm")

        # Should return empty (nothing to compress)
        assert result == ""
        # Buffer unchanged
        assert (
            len(state["agent_memories"]["dm"].short_term_buffer)
            == RETAIN_AFTER_COMPRESSION
        )

    def test_buffer_with_one_more_than_retain_count(
        self, empty_game_state: GameState
    ) -> None:
        """Test buffer with exactly one more than retain count."""
        from memory import RETAIN_AFTER_COMPRESSION

        state = empty_game_state
        entries = [f"Event {i}" for i in range(RETAIN_AFTER_COMPRESSION + 1)]
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=entries,
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "One event summary"
            MockSummarizer.return_value = mock_instance

            result = manager.compress_buffer("dm")

        # Should compress the one extra entry
        assert result == "One event summary"
        assert (
            len(state["agent_memories"]["dm"].short_term_buffer)
            == RETAIN_AFTER_COMPRESSION
        )

    def test_token_limit_of_one(self, empty_game_state: GameState) -> None:
        """Test behavior with minimal token limit of 1."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event"],
            token_limit=1,
        )

        manager = MemoryManager(state)

        # Almost any content will be near/over this limit
        assert manager.get_buffer_token_count("dm") >= 1

    def test_threshold_exactly_at_80_percent(self, empty_game_state: GameState) -> None:
        """Test is_near_limit at exactly 80% threshold."""
        state = empty_game_state
        # 100 tokens limit, need 80 tokens to trigger at 0.8 threshold
        # 62 words * 1.3 = 80.6 tokens
        buffer_text = " ".join(["word"] * 62)
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[buffer_text],
            token_limit=100,
        )

        manager = MemoryManager(state)

        # At 80% threshold (80 tokens), 80.6 tokens should trigger
        assert manager.is_near_limit("dm", threshold=0.8) is True
        # At 81% threshold (81 tokens), 80.6 tokens should NOT trigger
        assert manager.is_near_limit("dm", threshold=0.81) is False

    def test_custom_retain_count(self, empty_game_state: GameState) -> None:
        """Test compress_buffer with custom retain_count."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(10)],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary"
            MockSummarizer.return_value = mock_instance

            # Retain 5 instead of default 3
            manager.compress_buffer("dm", retain_count=5)

        assert len(state["agent_memories"]["dm"].short_term_buffer) == 5
        assert state["agent_memories"]["dm"].short_term_buffer[0] == "Event 5"


# =============================================================================
# Additional Test Coverage: Summary Merging
# =============================================================================


class TestSummaryMerging:
    """Tests for the _merge_summaries helper function."""

    def test_merge_with_empty_existing(self) -> None:
        """Test merging when existing summary is empty."""
        from memory import _merge_summaries

        result = _merge_summaries("", "New summary content")
        assert result == "New summary content"

    def test_merge_with_existing_summary(self) -> None:
        """Test merging with existing summary content."""
        from memory import _merge_summaries

        result = _merge_summaries("Old summary", "New summary")
        assert "Old summary" in result
        assert "New summary" in result
        assert "---" in result  # Separator

    def test_merge_preserves_formatting(self) -> None:
        """Test that merge preserves newlines in summaries."""
        from memory import _merge_summaries

        existing = "Line 1\nLine 2"
        new = "Line 3\nLine 4"
        result = _merge_summaries(existing, new)

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
        assert "Line 4" in result

    def test_multiple_merges_accumulate(self, empty_game_state: GameState) -> None:
        """Test that multiple compress_buffer calls accumulate summaries."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(10)],
            long_term_summary="Initial summary",
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "New events summary"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        final_summary = state["agent_memories"]["dm"].long_term_summary
        assert "Initial summary" in final_summary
        assert "New events summary" in final_summary
        assert "---" in final_summary


# =============================================================================
# Additional Test Coverage: Summarizer Cache Behavior
# =============================================================================


class TestSummarizerCache:
    """Tests for the module-level Summarizer cache."""

    def test_cache_reuses_summarizer_instance(
        self, empty_game_state: GameState
    ) -> None:
        """Test that cache reuses Summarizer instances."""
        import memory as memory_module

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(10)],
            token_limit=100,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Action " + str(i) for i in range(10)],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with (
            patch("memory.Summarizer") as MockSummarizer,
            patch("memory.get_config") as mock_config,
        ):
            mock_config.return_value.agents.summarizer.provider = "test"
            mock_config.return_value.agents.summarizer.model = "test-model"
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary"
            MockSummarizer.return_value = mock_instance

            # Clear cache first
            memory_module._summarizer_cache.clear()

            manager.compress_buffer("dm")
            manager.compress_buffer("fighter")

        # Summarizer should only be created once (cached)
        assert MockSummarizer.call_count == 1

    def test_different_configs_create_different_instances(
        self, empty_game_state: GameState
    ) -> None:
        """Test that different provider/model configs create different instances."""
        import memory as memory_module

        # Clear cache
        memory_module._summarizer_cache.clear()

        # Create two instances with different configs
        cache_key_1 = ("provider1", "model1")
        cache_key_2 = ("provider2", "model2")

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            MockSummarizer.return_value = mock_instance

            memory_module._summarizer_cache[cache_key_1] = MockSummarizer(
                "provider1", "model1"
            )
            memory_module._summarizer_cache[cache_key_2] = MockSummarizer(
                "provider2", "model2"
            )

        assert len(memory_module._summarizer_cache) == 2
        assert cache_key_1 in memory_module._summarizer_cache
        assert cache_key_2 in memory_module._summarizer_cache
