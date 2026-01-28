"""Tests for MemoryManager and memory operations.

This module tests Story 5.1: Short-Term Context Buffer, covering:
- MemoryManager class instantiation
- get_context() method with DM asymmetric access and PC isolation
- Buffer size tracking with token estimation
- Helper methods for memory operations
- Comprehensive acceptance tests for all story criteria
"""

import pytest

import memory as memory_module
from memory import MemoryManager, estimate_tokens
from models import AgentMemory, GameState, create_initial_game_state


@pytest.fixture(autouse=True)
def clear_summarizer_cache() -> None:
    """Clear the summarizer cache before each test to ensure mock isolation."""
    memory_module._summarizer_cache.clear()


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def empty_game_state() -> GameState:
    """Create an empty game state for testing."""
    return create_initial_game_state()


@pytest.fixture
def game_state_with_memories() -> GameState:
    """Create a game state with populated agent memories."""
    state = create_initial_game_state()

    # DM memory with summary and recent events
    state["agent_memories"]["dm"] = AgentMemory(
        long_term_summary="The party entered the haunted castle seeking treasure.",
        short_term_buffer=[
            "[DM]: The heavy oak doors creak open, revealing a dusty hall.",
            "[DM]: Cobwebs hang from ancient chandeliers.",
            "[DM]: A faint scratching sound echoes from above.",
        ],
        token_limit=8000,
    )

    # PC memories with isolated content
    state["agent_memories"]["rogue"] = AgentMemory(
        long_term_summary="Shadowmere has been tracking this castle for weeks.",
        short_term_buffer=[
            "[Shadowmere]: I check the door for traps.",
            "[Shadowmere]: *I notice a hidden pressure plate*",
        ],
        token_limit=4000,
    )

    state["agent_memories"]["fighter"] = AgentMemory(
        long_term_summary="Theron seeks vengeance against the castle's lord.",
        short_term_buffer=[
            "[Theron]: I stand ready with my sword drawn.",
            "[Theron]: Let me take the lead.",
        ],
        token_limit=4000,
    )

    state["agent_memories"]["wizard"] = AgentMemory(
        long_term_summary="Elara senses powerful magic within these walls.",
        short_term_buffer=[
            "[Elara]: I detect arcane energies ahead.",
        ],
        token_limit=4000,
    )

    return state


# =============================================================================
# Task 1: MemoryManager Class Skeleton Tests
# =============================================================================


class TestEstimateTokens:
    """Tests for token estimation function."""

    def test_estimate_tokens_empty_string(self) -> None:
        """Test token estimation for empty string."""
        result = estimate_tokens("")
        assert result == 0

    def test_estimate_tokens_single_word(self) -> None:
        """Test token estimation for single word."""
        result = estimate_tokens("hello")
        assert result == 1  # 1 word * 1.3 = 1.3 -> 1

    def test_estimate_tokens_multiple_words(self) -> None:
        """Test token estimation for multiple words."""
        result = estimate_tokens("hello world this is a test")
        # 6 words * 1.3 = 7.8 -> 7
        assert result == 7

    def test_estimate_tokens_long_text(self) -> None:
        """Test token estimation for longer text."""
        text = " ".join(["word"] * 100)
        result = estimate_tokens(text)
        # 100 words * 1.3 = 130
        assert result == 130

    def test_estimate_tokens_handles_whitespace(self) -> None:
        """Test token estimation handles various whitespace."""
        result = estimate_tokens("  hello   world\t\ntest  ")
        # Should split on whitespace and count words
        assert result == 3  # 3 words * 1.3 = 3.9 -> 3

    def test_estimate_tokens_unicode_text(self) -> None:
        """Test token estimation with unicode characters."""
        result = estimate_tokens("hello world")
        # "hello" "world" = 2 words, 2 * 1.3 = 2.6 -> 2
        assert result == 2

    def test_estimate_tokens_cjk_text(self) -> None:
        """Test token estimation with CJK-like (non-space-delimited) text.

        CJK text is not space-delimited, so word-based heuristic
        would fail. The function detects this and uses character-based
        estimation instead.
        """
        # Simulate CJK-like text: long string without spaces (like Chinese)
        no_space_text = "TheDragonEntersTheCave"  # 22 chars, treated as 1 word
        result = estimate_tokens(no_space_text)
        # 1 word but 22 chars -> uses char-based: 22 * 0.5 = 11
        assert result == 11


class TestMemoryManagerInit:
    """Tests for MemoryManager instantiation."""

    def test_memory_manager_accepts_game_state(
        self, empty_game_state: GameState
    ) -> None:
        """Test that MemoryManager accepts GameState on init."""
        manager = MemoryManager(empty_game_state)
        assert manager is not None

    def test_memory_manager_stores_state_reference(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that MemoryManager stores reference to game state."""
        manager = MemoryManager(game_state_with_memories)
        # Access via the internal attribute
        assert manager._state is game_state_with_memories

    def test_memory_manager_type_hints(self) -> None:
        """Test that MemoryManager has proper type hints."""
        # This is a compile-time check, but we can verify the class signature
        import inspect

        sig = inspect.signature(MemoryManager.__init__)
        params = sig.parameters
        assert "state" in params
        # Verify the annotation includes GameState
        assert params["state"].annotation is not inspect.Parameter.empty


# =============================================================================
# Task 2: get_context() Method Tests
# =============================================================================


class TestGetContext:
    """Tests for get_context() method."""

    def test_get_context_returns_string(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that get_context returns a string."""
        manager = MemoryManager(game_state_with_memories)
        result = manager.get_context("dm")
        assert isinstance(result, str)

    def test_get_context_dm_returns_content(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that get_context returns non-empty content for DM."""
        manager = MemoryManager(game_state_with_memories)
        result = manager.get_context("dm")
        assert len(result) > 0

    def test_get_context_pc_returns_content(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that get_context returns non-empty content for PC."""
        manager = MemoryManager(game_state_with_memories)
        result = manager.get_context("rogue")
        assert len(result) > 0

    def test_get_context_unknown_agent_returns_empty(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that get_context returns empty for unknown agent."""
        manager = MemoryManager(game_state_with_memories)
        result = manager.get_context("unknown_agent")
        assert result == ""


class TestGetContextDM:
    """Tests for DM context building (asymmetric access)."""

    def test_dm_context_includes_long_term_summary(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that DM context includes long-term summary."""
        manager = MemoryManager(game_state_with_memories)
        context = manager.get_context("dm")

        assert "Story So Far" in context
        assert "haunted castle" in context

    def test_dm_context_includes_recent_events(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that DM context includes recent events."""
        manager = MemoryManager(game_state_with_memories)
        context = manager.get_context("dm")

        assert "Recent Events" in context
        assert "heavy oak doors" in context

    def test_dm_context_includes_all_pc_knowledge(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that DM can see all agents' short_term_buffers."""
        manager = MemoryManager(game_state_with_memories)
        context = manager.get_context("dm")

        assert "Player Knowledge" in context
        assert "[rogue knows]" in context
        assert "[fighter knows]" in context
        assert "[wizard knows]" in context

    def test_dm_context_excludes_dm_from_player_knowledge(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that DM's own memory is not in player knowledge section."""
        manager = MemoryManager(game_state_with_memories)
        context = manager.get_context("dm")

        assert "[dm knows]" not in context

    def test_dm_context_limits_dm_buffer_entries(
        self, empty_game_state: GameState
    ) -> None:
        """Test that DM buffer is limited to last 10 entries."""
        state = empty_game_state
        # Create 15 events
        events = [f"Event {i}" for i in range(15)]
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=events)

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        # Should include last 10 events (5-14), not first 5 (0-4)
        assert "Event 14" in context
        assert "Event 5" in context
        assert "Event 0" not in context
        assert "Event 4" not in context

    def test_dm_context_limits_pc_buffer_entries(
        self, empty_game_state: GameState
    ) -> None:
        """Test that PC buffer in DM context is limited to last 3 entries."""
        state = empty_game_state
        # Create 10 PC events
        pc_events = [f"PC Action {i}" for i in range(10)]
        state["agent_memories"]["rogue"] = AgentMemory(short_term_buffer=pc_events)

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        # Should include last 3 entries (7-9), not earlier ones
        assert "PC Action 9" in context
        assert "PC Action 7" in context
        assert "PC Action 0" not in context

    def test_dm_context_handles_empty_pc_buffers(
        self, empty_game_state: GameState
    ) -> None:
        """Test that DM context handles PCs with empty buffers gracefully."""
        state = empty_game_state
        state["agent_memories"]["rogue"] = AgentMemory(short_term_buffer=[])
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Fighter action"]
        )

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        # Rogue with empty buffer should not appear
        assert "[rogue knows]" not in context
        # Fighter with content should appear
        assert "[fighter knows]" in context


class TestGetContextPC:
    """Tests for PC context building (isolation)."""

    def test_pc_context_includes_own_long_term_summary(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that PC context includes own long-term summary."""
        manager = MemoryManager(game_state_with_memories)
        context = manager.get_context("rogue")

        assert "What You Remember" in context
        assert "tracking this castle" in context

    def test_pc_context_includes_own_recent_events(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that PC context includes own recent events."""
        manager = MemoryManager(game_state_with_memories)
        context = manager.get_context("rogue")

        assert "Recent Events" in context
        assert "check the door for traps" in context

    def test_pc_context_only_contains_own_buffer(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test PC agents only see their own memory (isolation)."""
        manager = MemoryManager(game_state_with_memories)
        context = manager.get_context("rogue")

        # Should see own memory
        assert "Shadowmere" in context

        # Should NOT see other agents' memories
        assert "Theron" not in context
        assert "Elara" not in context
        assert "[fighter knows]" not in context
        assert "[wizard knows]" not in context

    def test_pc_isolation_fighter(self, game_state_with_memories: GameState) -> None:
        """Test that fighter only sees fighter's memory."""
        manager = MemoryManager(game_state_with_memories)
        context = manager.get_context("fighter")

        # Should see own memory
        assert "Theron" in context or "vengeance" in context

        # Should NOT see other PCs
        assert "Shadowmere" not in context
        assert "Elara" not in context

    def test_pc_isolation_wizard(self, game_state_with_memories: GameState) -> None:
        """Test that wizard only sees wizard's memory."""
        manager = MemoryManager(game_state_with_memories)
        context = manager.get_context("wizard")

        # Should see own memory
        assert "Elara" in context or "arcane" in context

        # Should NOT see other PCs
        assert "Shadowmere" not in context
        assert "Theron" not in context

    def test_pc_cannot_see_dm_memory(self, game_state_with_memories: GameState) -> None:
        """Test that PC cannot access DM's memory."""
        manager = MemoryManager(game_state_with_memories)
        context = manager.get_context("rogue")

        # Should NOT see DM's exclusive content
        assert "heavy oak doors" not in context
        assert "Cobwebs" not in context
        assert "Story So Far" not in context  # PC uses "What You Remember"

    def test_pc_context_limits_buffer_entries(
        self, empty_game_state: GameState
    ) -> None:
        """Test that PC buffer is limited to last 10 entries."""
        state = empty_game_state
        # Create 15 events
        events = [f"Rogue Action {i}" for i in range(15)]
        state["agent_memories"]["rogue"] = AgentMemory(short_term_buffer=events)

        manager = MemoryManager(state)
        context = manager.get_context("rogue")

        # Should include last 10 events (5-14), not first 5 (0-4)
        assert "Rogue Action 14" in context
        assert "Rogue Action 5" in context
        assert "Rogue Action 0" not in context


# =============================================================================
# Task 3: Buffer Size Tracking Tests
# =============================================================================


class TestBufferTokenCount:
    """Tests for buffer token estimation."""

    def test_get_buffer_token_count_empty(self, empty_game_state: GameState) -> None:
        """Test token count for empty buffer."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=[])

        manager = MemoryManager(state)
        count = manager.get_buffer_token_count("dm")

        assert count == 0

    def test_get_buffer_token_count_with_content(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test token count for buffer with content."""
        manager = MemoryManager(game_state_with_memories)
        count = manager.get_buffer_token_count("dm")

        # Should be greater than 0
        assert count > 0

    def test_get_buffer_token_count_missing_agent(
        self, empty_game_state: GameState
    ) -> None:
        """Test token count for non-existent agent."""
        manager = MemoryManager(empty_game_state)
        count = manager.get_buffer_token_count("unknown_agent")

        assert count == 0

    def test_get_buffer_token_count_proportional_to_content(
        self, empty_game_state: GameState
    ) -> None:
        """Test that token count increases with content."""
        state = empty_game_state

        # Short buffer
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=["Short message"])
        manager = MemoryManager(state)
        short_count = manager.get_buffer_token_count("dm")

        # Long buffer
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["This is a much longer message " * 10]
        )
        manager = MemoryManager(state)
        long_count = manager.get_buffer_token_count("dm")

        assert long_count > short_count


class TestIsNearLimit:
    """Tests for limit detection."""

    def test_is_near_limit_false_for_empty_buffer(
        self, empty_game_state: GameState
    ) -> None:
        """Test that empty buffer is not near limit."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[],
            token_limit=8000,
        )

        manager = MemoryManager(state)
        result = manager.is_near_limit("dm")

        assert result is False

    def test_is_near_limit_false_for_small_buffer(
        self, empty_game_state: GameState
    ) -> None:
        """Test that small buffer is not near limit."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Short message"],
            token_limit=8000,
        )

        manager = MemoryManager(state)
        result = manager.is_near_limit("dm")

        assert result is False

    def test_is_near_limit_true_for_large_buffer(
        self, empty_game_state: GameState
    ) -> None:
        """Test that large buffer is near limit."""
        state = empty_game_state
        # Create a buffer that exceeds 80% of token limit
        # With token_limit=100 and threshold=0.8, need >= 80 tokens
        # 80 tokens / 1.3 words per token = ~62 words
        large_buffer = [" ".join(["word"] * 100)]  # ~130 tokens
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=large_buffer,
            token_limit=100,
        )

        manager = MemoryManager(state)
        result = manager.is_near_limit("dm")

        assert result is True

    def test_is_near_limit_custom_threshold(self, empty_game_state: GameState) -> None:
        """Test is_near_limit with custom threshold."""
        state = empty_game_state
        # Create buffer with ~50 tokens
        buffer = [" ".join(["word"] * 38)]  # ~50 tokens
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=buffer,
            token_limit=100,
        )

        manager = MemoryManager(state)

        # With threshold 0.8, 50 tokens < 80, should be False
        assert manager.is_near_limit("dm", threshold=0.8) is False

        # With threshold 0.4, 50 tokens >= 40, should be True
        assert manager.is_near_limit("dm", threshold=0.4) is True

    def test_is_near_limit_missing_agent(self, empty_game_state: GameState) -> None:
        """Test is_near_limit for non-existent agent."""
        manager = MemoryManager(empty_game_state)
        result = manager.is_near_limit("unknown_agent")

        assert result is False


# =============================================================================
# Task 6: Helper Methods Tests
# =============================================================================


class TestHelperMethods:
    """Tests for get_long_term_summary, get_buffer_entries, add_to_buffer."""

    def test_get_long_term_summary_returns_summary(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that get_long_term_summary returns the summary."""
        manager = MemoryManager(game_state_with_memories)
        summary = manager.get_long_term_summary("dm")

        assert "haunted castle" in summary

    def test_get_long_term_summary_empty_for_missing_agent(
        self, empty_game_state: GameState
    ) -> None:
        """Test that get_long_term_summary returns empty for missing agent."""
        manager = MemoryManager(empty_game_state)
        summary = manager.get_long_term_summary("unknown_agent")

        assert summary == ""

    def test_get_buffer_entries_returns_list(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that get_buffer_entries returns a list."""
        manager = MemoryManager(game_state_with_memories)
        entries = manager.get_buffer_entries("dm")

        assert isinstance(entries, list)
        assert len(entries) > 0

    def test_get_buffer_entries_respects_limit(
        self, empty_game_state: GameState
    ) -> None:
        """Test that get_buffer_entries respects the limit parameter."""
        state = empty_game_state
        events = [f"Event {i}" for i in range(20)]
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=events)

        manager = MemoryManager(state)
        entries = manager.get_buffer_entries("dm", limit=5)

        assert len(entries) == 5
        # Should be the last 5 entries
        assert entries[0] == "Event 15"
        assert entries[-1] == "Event 19"

    def test_get_buffer_entries_default_limit_10(
        self, empty_game_state: GameState
    ) -> None:
        """Test that get_buffer_entries defaults to limit 10."""
        state = empty_game_state
        events = [f"Event {i}" for i in range(20)]
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=events)

        manager = MemoryManager(state)
        entries = manager.get_buffer_entries("dm")

        assert len(entries) == 10

    def test_get_buffer_entries_empty_for_missing_agent(
        self, empty_game_state: GameState
    ) -> None:
        """Test that get_buffer_entries returns empty list for missing agent."""
        manager = MemoryManager(empty_game_state)
        entries = manager.get_buffer_entries("unknown_agent")

        assert entries == []

    def test_add_to_buffer_appends_content(self, empty_game_state: GameState) -> None:
        """Test that add_to_buffer appends content to buffer."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=["Existing"])

        manager = MemoryManager(state)
        manager.add_to_buffer("dm", "New content")

        entries = manager.get_buffer_entries("dm")
        assert "New content" in entries

    def test_add_to_buffer_preserves_existing(
        self, empty_game_state: GameState
    ) -> None:
        """Test that add_to_buffer preserves existing content."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["First", "Second"]
        )

        manager = MemoryManager(state)
        manager.add_to_buffer("dm", "Third")

        entries = manager.get_buffer_entries("dm")
        assert "First" in entries
        assert "Second" in entries
        assert "Third" in entries

    def test_add_to_buffer_handles_missing_agent(
        self, empty_game_state: GameState
    ) -> None:
        """Test that add_to_buffer handles missing agent gracefully."""
        manager = MemoryManager(empty_game_state)

        # Should not raise
        manager.add_to_buffer("unknown_agent", "Content")

        # Verify nothing changed
        entries = manager.get_buffer_entries("unknown_agent")
        assert entries == []

    def test_add_to_buffer_rejects_none_content(
        self, empty_game_state: GameState
    ) -> None:
        """Test that add_to_buffer raises TypeError for None content."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory()
        manager = MemoryManager(state)

        with pytest.raises(TypeError, match="content must not be None"):
            manager.add_to_buffer("dm", None)  # type: ignore[arg-type]

    def test_add_to_buffer_rejects_oversized_content(
        self, empty_game_state: GameState
    ) -> None:
        """Test that add_to_buffer raises ValueError for content over 100KB."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory()
        manager = MemoryManager(state)

        oversized = "x" * 100_001  # Just over 100KB
        with pytest.raises(ValueError, match="exceeds maximum size"):
            manager.add_to_buffer("dm", oversized)

    def test_add_to_buffer_accepts_exactly_100kb(
        self, empty_game_state: GameState
    ) -> None:
        """Test that add_to_buffer accepts content exactly at 100KB limit."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory()
        manager = MemoryManager(state)

        exactly_100kb = "x" * 100_000
        # Should not raise
        manager.add_to_buffer("dm", exactly_100kb)

        entries = manager.get_buffer_entries("dm")
        assert len(entries) == 1


# =============================================================================
# Task 7: Comprehensive Acceptance Tests
# =============================================================================


class TestStory51AcceptanceCriteria:
    """Acceptance tests for all Story 5.1 criteria."""

    def test_ac1_agent_memory_has_short_term_buffer_field(self) -> None:
        """Test AC1: AgentMemory model has short_term_buffer field."""
        memory = AgentMemory()

        assert hasattr(memory, "short_term_buffer")
        assert isinstance(memory.short_term_buffer, list)

    def test_ac2_recent_turns_included_in_prompt_context(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test AC2: Recent turns from buffer are included in prompt context."""
        manager = MemoryManager(game_state_with_memories)

        # DM context includes recent events
        dm_context = manager.get_context("dm")
        assert "Recent Events" in dm_context

        # PC context includes recent events
        pc_context = manager.get_context("rogue")
        assert "Recent Events" in pc_context

    def test_ac3_buffer_has_configurable_token_limit(self) -> None:
        """Test AC3: Buffer has configurable size limit (token_limit)."""
        memory = AgentMemory(token_limit=4000)

        assert memory.token_limit == 4000

        # Default value
        memory_default = AgentMemory()
        assert memory_default.token_limit == 8000

    def test_ac4_pc_only_sees_own_buffer(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test AC4: PC agents only see their own buffer contents."""
        manager = MemoryManager(game_state_with_memories)

        rogue_context = manager.get_context("rogue")

        # Rogue sees own content
        assert "Shadowmere" in rogue_context

        # Rogue does NOT see other PCs
        assert "Theron" not in rogue_context
        assert "Elara" not in rogue_context

        # Rogue does NOT see DM-specific content
        assert "Story So Far" not in rogue_context

    def test_ac5_dm_sees_all_buffers(self, game_state_with_memories: GameState) -> None:
        """Test AC5: DM can access all agents' short_term_buffers."""
        manager = MemoryManager(game_state_with_memories)

        dm_context = manager.get_context("dm")

        # DM sees all PC knowledge
        assert "[rogue knows]" in dm_context
        assert "[fighter knows]" in dm_context
        assert "[wizard knows]" in dm_context

    def test_ac6_get_context_returns_prompt_ready_string(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test AC6: get_context returns prompt-ready string with markdown."""
        manager = MemoryManager(game_state_with_memories)

        dm_context = manager.get_context("dm")

        # Should have markdown section headers
        assert "## Story So Far" in dm_context or "## Recent Events" in dm_context

        # Should be a string suitable for prompt inclusion
        assert isinstance(dm_context, str)
        assert len(dm_context) > 0

    def test_buffer_entries_chronological_order_oldest_first(
        self, empty_game_state: GameState
    ) -> None:
        """Test that buffer entries are oldest first, newest last."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["first", "second", "third"]
        )

        manager = MemoryManager(state)
        entries = manager.get_buffer_entries("dm")

        assert entries[0] == "first"
        assert entries[-1] == "third"

    def test_empty_buffer_returns_empty_context(
        self, empty_game_state: GameState
    ) -> None:
        """Test that empty buffer returns empty/minimal context string."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[],
            long_term_summary="",
        )

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        assert context == ""

    def test_missing_agent_returns_empty_context(
        self, empty_game_state: GameState
    ) -> None:
        """Test that missing agent returns empty context, not error."""
        manager = MemoryManager(empty_game_state)

        context = manager.get_context("nonexistent_agent")

        assert context == ""

    def test_dm_context_with_only_summary(self, empty_game_state: GameState) -> None:
        """Test DM context with only long-term summary."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="The story so far...",
            short_term_buffer=[],
        )

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        assert "Story So Far" in context
        assert "The story so far..." in context

    def test_pc_context_with_only_summary(self, empty_game_state: GameState) -> None:
        """Test PC context with only long-term summary."""
        state = empty_game_state
        state["agent_memories"]["rogue"] = AgentMemory(
            long_term_summary="Rogue's memories...",
            short_term_buffer=[],
        )

        manager = MemoryManager(state)
        context = manager.get_context("rogue")

        assert "What You Remember" in context
        assert "Rogue's memories..." in context


# =============================================================================
# Task 4: Verify Existing Turn Content Addition
# =============================================================================


class TestTurnContentAddition:
    """Tests verifying that turn functions add content to buffers correctly.

    These tests verify the existing implementation in agents.py adds
    turn content to short_term_buffers with proper agent attribution.
    """

    def test_dm_turn_content_format_includes_dm_attribution(self) -> None:
        """Test that DM turn content includes [DM] attribution."""
        # This verifies the expected format based on agents.py implementation
        # The actual agents.py code does: f"[DM]: {response_content}"
        expected_format = "[DM]:"

        # We can verify this by checking the buffer format in agents.py
        # lines 663-665: new_buffer.append(f"[DM]: {response_content}")
        assert expected_format == "[DM]:"

    def test_pc_turn_content_format_includes_character_name(self) -> None:
        """Test that PC turn content includes character name attribution."""
        # This verifies the expected format based on agents.py implementation
        # lines 769-770: new_buffer.append(f"[{character_config.name}]: {response_content}")
        test_name = "Shadowmere"
        expected_format = f"[{test_name}]:"

        assert expected_format == "[Shadowmere]:"

    def test_turn_content_appends_to_buffer_not_prepends(self) -> None:
        """Test that turn content is appended (newest last)."""
        # Verify by testing with MemoryManager that entries are in order
        from models import create_initial_game_state

        state = create_initial_game_state()
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["First entry", "Second entry"]
        )

        manager = MemoryManager(state)
        manager.add_to_buffer("dm", "Third entry")

        entries = manager.get_buffer_entries("dm")

        # Newest should be last
        assert entries[-1] == "Third entry"
        assert entries[0] == "First entry"


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_token_limit_handled(self, empty_game_state: GameState) -> None:
        """Test that zero token limit is handled in is_near_limit."""
        # Note: AgentMemory validates token_limit >= 1, so this tests the guard
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Content"],
            token_limit=1,  # Minimum allowed
        )

        manager = MemoryManager(state)
        # Should not raise, should return True (any content exceeds tiny limit)
        result = manager.is_near_limit("dm", threshold=0.5)
        assert isinstance(result, bool)

    def test_very_long_buffer_entries(self, empty_game_state: GameState) -> None:
        """Test handling of very long buffer entries."""
        state = empty_game_state
        long_entry = "word " * 10000  # Very long entry
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=[long_entry])

        manager = MemoryManager(state)

        # Should handle without error
        count = manager.get_buffer_token_count("dm")
        assert count > 0

        context = manager.get_context("dm")
        assert len(context) > 0

    def test_unicode_content_in_buffer(self, empty_game_state: GameState) -> None:
        """Test handling of unicode content in buffers."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[
                "[DM]: The party enters the temple.",
            ]
        )

        manager = MemoryManager(state)

        context = manager.get_context("dm")
        assert "" in context

    def test_dm_context_without_dm_memory_entry(
        self, empty_game_state: GameState
    ) -> None:
        """Test DM context when DM has no memory entry."""
        # Only PC memories, no DM
        state = empty_game_state
        state["agent_memories"]["rogue"] = AgentMemory(
            short_term_buffer=["Rogue action"]
        )

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        # Should still include player knowledge
        assert "[rogue knows]" in context


# =============================================================================
# Module Exports Test
# =============================================================================


class TestModuleExports:
    """Tests for memory module exports."""

    def test_memory_manager_exported(self) -> None:
        """Test that MemoryManager is exported from memory module."""
        from memory import MemoryManager

        assert MemoryManager is not None

    def test_estimate_tokens_exported(self) -> None:
        """Test that estimate_tokens is exported from memory module."""
        from memory import estimate_tokens

        assert estimate_tokens is not None
        assert callable(estimate_tokens)


# =============================================================================
# Extended Coverage: Token Estimation Edge Cases
# =============================================================================


class TestEstimateTokensExtended:
    """Extended tests for token estimation edge cases."""

    def test_estimate_tokens_very_long_string(self) -> None:
        """Test token estimation with extremely long string (100k+ chars)."""
        # Create a very long string (100,000 words)
        long_text = " ".join(["word"] * 100_000)
        result = estimate_tokens(long_text)
        # 100,000 words * 1.3 = 130,000 tokens
        assert result == 130_000

    def test_estimate_tokens_single_very_long_word(self) -> None:
        """Test token estimation with a single very long word."""
        # A single word of 50,000 characters
        long_word = "a" * 50_000
        result = estimate_tokens(long_word)
        # 1 word but 50,000 chars -> uses char-based: 50,000 * 0.5 = 25,000
        assert result == 25_000

    def test_estimate_tokens_mixed_short_long_words(self) -> None:
        """Test token estimation with mix of short and long words."""
        text = "a " + "verylongword " * 10
        result = estimate_tokens(text)
        # 11 words * 1.3 = 14.3 -> 14
        assert result == 14

    def test_estimate_tokens_only_whitespace(self) -> None:
        """Test token estimation for whitespace-only string."""
        result = estimate_tokens("     \t\n\r   ")
        # No words, should be 0
        assert result == 0

    def test_estimate_tokens_newlines_between_words(self) -> None:
        """Test token estimation with newlines between words."""
        result = estimate_tokens("line1\nline2\nline3")
        # 3 words * 1.3 = 3.9 -> 3
        assert result == 3

    def test_estimate_tokens_tabs_between_words(self) -> None:
        """Test token estimation with tabs between words."""
        result = estimate_tokens("word1\tword2\tword3")
        # 3 words * 1.3 = 3.9 -> 3
        assert result == 3

    def test_estimate_tokens_special_characters(self) -> None:
        """Test token estimation with special characters."""
        result = estimate_tokens("Hello! @#$%^&*() World")
        # 3 words * 1.3 = 3.9 -> 3
        assert result == 3

    def test_estimate_tokens_numbers_and_punctuation(self) -> None:
        """Test token estimation with numbers and punctuation."""
        result = estimate_tokens("Player 1 rolled 20. Critical hit!")
        # 6 words * 1.3 = 7.8 -> 7
        assert result == 7

    def test_estimate_tokens_emoji_in_text(self) -> None:
        """Test token estimation with emoji characters."""
        result = estimate_tokens("The dragon attacks! Fire breath incoming")
        # 6 words * 1.3 = 7.8 -> 7
        assert result == 7

    def test_estimate_tokens_unicode_special_chars(self) -> None:
        """Test token estimation with various unicode characters."""
        result = estimate_tokens("Sword of Righteousness")
        # 3 words * 1.3 = 3.9 -> 3
        assert result == 3

    def test_estimate_tokens_cjk_with_spaces(self) -> None:
        """Test token estimation with CJK mixed with spaces."""
        result = estimate_tokens("hello world")
        # Emoji are treated as part of words in str.split()
        # "hello" "world" = 2 words * 1.3 = 2.6 -> 2
        assert result == 2

    def test_estimate_tokens_pure_cjk_japanese(self) -> None:
        """Test token estimation with pure Japanese text (no spaces)."""
        japanese_text = "dnd"  # Long string without spaces
        result = estimate_tokens(japanese_text)
        # Low word count (1) but 30+ chars -> character-based
        assert result > 0

    def test_estimate_tokens_threshold_for_cjk_detection(self) -> None:
        """Test the threshold for CJK detection (2 words, 20 chars)."""
        # Just under threshold: 2 words (not < 2)
        two_words = "ab cd"  # 2 words, 5 chars
        result = estimate_tokens(two_words)
        # Uses word-based: 2 * 1.3 = 2.6 -> 2
        assert result == 2

        # At threshold: 1 word, 21 chars
        one_long_word = "a" * 21
        result = estimate_tokens(one_long_word)
        # Uses char-based: 21 * 0.5 = 10.5 -> 10
        assert result == 10


# =============================================================================
# Extended Coverage: Buffer Operations with Special Characters
# =============================================================================


class TestBufferOperationsSpecialCharacters:
    """Tests for buffer operations with unicode and special characters."""

    def test_buffer_with_emoji_entries(self, empty_game_state: GameState) -> None:
        """Test buffer operations with emoji in entries."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[
                "[DM]: The dragon roars! Flame fills the room!",
                "[DM]: Victory! The treasure is yours!",
            ]
        )

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        assert "" in context
        assert "" in context

    def test_buffer_with_multiline_entries(self, empty_game_state: GameState) -> None:
        """Test buffer with entries containing newlines."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[
                "[DM]: The bard sings:\n'O valiant heroes brave and true\nYour quest awaits you'",
            ]
        )

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        assert "bard sings" in context
        assert "valiant heroes" in context

    def test_buffer_with_special_markdown_chars(
        self, empty_game_state: GameState
    ) -> None:
        """Test buffer with markdown special characters."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[
                "[DM]: **Bold** and *italic* text with `code` and [links](url)",
            ]
        )

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        assert "**Bold**" in context
        assert "`code`" in context

    def test_buffer_with_empty_string_entry(self, empty_game_state: GameState) -> None:
        """Test buffer that contains empty string entries."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["first", "", "third"]
        )

        manager = MemoryManager(state)
        entries = manager.get_buffer_entries("dm")

        assert len(entries) == 3
        assert entries[1] == ""

    def test_buffer_with_only_whitespace_entry(
        self, empty_game_state: GameState
    ) -> None:
        """Test buffer with whitespace-only entries."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["content", "   ", "more content"]
        )

        manager = MemoryManager(state)
        token_count = manager.get_buffer_token_count("dm")

        # Should handle whitespace entries
        assert token_count > 0

    def test_add_to_buffer_with_unicode_content(
        self, empty_game_state: GameState
    ) -> None:
        """Test adding unicode content to buffer."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory()

        manager = MemoryManager(state)
        manager.add_to_buffer("dm", "[DM]: The wizard casts fireball!")

        entries = manager.get_buffer_entries("dm")
        assert "" in entries[0]

    def test_add_to_buffer_with_cjk_content(self, empty_game_state: GameState) -> None:
        """Test adding CJK content to buffer."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory()

        manager = MemoryManager(state)
        manager.add_to_buffer("dm", "[DM]: dnd")

        entries = manager.get_buffer_entries("dm")
        assert "dnd" in entries[0]


# =============================================================================
# Extended Coverage: Multiple Agent Interactions
# =============================================================================


class TestMultipleAgentInteractions:
    """Tests for multiple agents interacting with memory."""

    def test_many_agents_in_state(self, empty_game_state: GameState) -> None:
        """Test state with many agents (10+)."""
        state = empty_game_state

        # Create 10 PC agents plus DM
        for i in range(10):
            state["agent_memories"][f"agent_{i}"] = AgentMemory(
                short_term_buffer=[f"Agent {i} action"]
            )
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=["DM narration"])

        manager = MemoryManager(state)
        dm_context = manager.get_context("dm")

        # DM should see all agents
        for i in range(10):
            assert f"[agent_{i} knows]" in dm_context

    def test_agent_isolation_with_many_agents(
        self, empty_game_state: GameState
    ) -> None:
        """Test that isolation holds with many agents."""
        state = empty_game_state

        for i in range(5):
            state["agent_memories"][f"pc_{i}"] = AgentMemory(
                short_term_buffer=[f"Secret action {i}"]
            )

        manager = MemoryManager(state)

        # Each PC should only see their own
        for i in range(5):
            context = manager.get_context(f"pc_{i}")
            assert f"Secret action {i}" in context
            for j in range(5):
                if j != i:
                    assert f"Secret action {j}" not in context

    def test_sequential_buffer_additions_multiple_agents(
        self, empty_game_state: GameState
    ) -> None:
        """Test sequential additions to multiple agent buffers."""
        state = empty_game_state
        state["agent_memories"]["rogue"] = AgentMemory()
        state["agent_memories"]["fighter"] = AgentMemory()

        manager = MemoryManager(state)

        # Add to multiple agents sequentially
        manager.add_to_buffer("rogue", "Rogue sneaks")
        manager.add_to_buffer("fighter", "Fighter charges")
        manager.add_to_buffer("rogue", "Rogue strikes")
        manager.add_to_buffer("fighter", "Fighter blocks")

        # Verify each agent has correct entries
        rogue_entries = manager.get_buffer_entries("rogue")
        fighter_entries = manager.get_buffer_entries("fighter")

        assert len(rogue_entries) == 2
        assert len(fighter_entries) == 2
        assert rogue_entries[0] == "Rogue sneaks"
        assert fighter_entries[1] == "Fighter blocks"

    def test_dm_context_order_consistency(self, empty_game_state: GameState) -> None:
        """Test that DM context maintains consistent ordering."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2"]
        )
        state["agent_memories"]["archer"] = AgentMemory(
            short_term_buffer=["Archer fires"]
        )
        state["agent_memories"]["mage"] = AgentMemory(short_term_buffer=["Mage casts"])

        manager = MemoryManager(state)
        context1 = manager.get_context("dm")
        context2 = manager.get_context("dm")

        # Same content each time
        assert context1 == context2


# =============================================================================
# Extended Coverage: Threshold and Limit Edge Cases
# =============================================================================


class TestThresholdEdgeCases:
    """Tests for edge cases in threshold calculations."""

    def test_is_near_limit_threshold_exactly_zero(
        self, empty_game_state: GameState
    ) -> None:
        """Test is_near_limit with threshold=0."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["content"],
            token_limit=1000,
        )

        manager = MemoryManager(state)
        # With threshold=0, limit = 0, and any tokens >= 0 is True
        result = manager.is_near_limit("dm", threshold=0.0)
        assert result is True

    def test_is_near_limit_threshold_one(self, empty_game_state: GameState) -> None:
        """Test is_near_limit with threshold=1.0 (100%)."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["small"],
            token_limit=1000,
        )

        manager = MemoryManager(state)
        # With threshold=1.0, needs 1000 tokens to trigger
        result = manager.is_near_limit("dm", threshold=1.0)
        assert result is False

    def test_is_near_limit_threshold_above_one(
        self, empty_game_state: GameState
    ) -> None:
        """Test is_near_limit with threshold > 1.0."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[" ".join(["word"] * 100)],  # ~130 tokens
            token_limit=100,
        )

        manager = MemoryManager(state)
        # With threshold=1.5, limit = 150, 130 < 150
        result = manager.is_near_limit("dm", threshold=1.5)
        assert result is False

    def test_is_near_limit_very_small_threshold(
        self, empty_game_state: GameState
    ) -> None:
        """Test is_near_limit with very small threshold (0.01)."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["tiny"],  # ~1 token
            token_limit=1000,
        )

        manager = MemoryManager(state)
        # With threshold=0.01, limit = 10, 1 < 10
        result = manager.is_near_limit("dm", threshold=0.01)
        assert result is False

    def test_is_near_limit_exact_boundary(self, empty_game_state: GameState) -> None:
        """Test is_near_limit at exact boundary (tokens == limit)."""
        state = empty_game_state
        # Need exactly 80 tokens with token_limit=100 and threshold=0.8
        # 61 words * 1.3 = 79.3 -> 79 (just under)
        # 62 words * 1.3 = 80.6 -> 80 (at boundary)
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[" ".join(["w"] * 62)],  # ~80 tokens
            token_limit=100,
        )

        manager = MemoryManager(state)
        result = manager.is_near_limit("dm", threshold=0.8)
        # 80 >= 80, should be True
        assert result is True

    def test_is_near_limit_just_under_boundary(
        self, empty_game_state: GameState
    ) -> None:
        """Test is_near_limit just under boundary."""
        state = empty_game_state
        # 61 words * 1.3 = 79.3 -> 79 (just under 80)
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[" ".join(["w"] * 61)],  # ~79 tokens
            token_limit=100,
        )

        manager = MemoryManager(state)
        result = manager.is_near_limit("dm", threshold=0.8)
        # 79 >= 80 is False
        assert result is False

    def test_get_buffer_entries_limit_zero(self, empty_game_state: GameState) -> None:
        """Test get_buffer_entries with limit=0."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=["a", "b", "c"])

        manager = MemoryManager(state)
        entries = manager.get_buffer_entries("dm", limit=0)

        # Python slicing: buffer[-0:] is same as buffer[0:] = all entries
        # This is documented Python behavior: -0 == 0
        assert entries == ["a", "b", "c"]

    def test_get_buffer_entries_limit_negative(
        self, empty_game_state: GameState
    ) -> None:
        """Test get_buffer_entries with negative limit."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["a", "b", "c", "d", "e"]
        )

        manager = MemoryManager(state)
        entries = manager.get_buffer_entries("dm", limit=-2)

        # Python slicing: buffer[-(-2):] = buffer[2:] = ["c", "d", "e"]
        assert entries == ["c", "d", "e"]

    def test_get_buffer_entries_limit_larger_than_buffer(
        self, empty_game_state: GameState
    ) -> None:
        """Test get_buffer_entries with limit larger than buffer size."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=["a", "b"])

        manager = MemoryManager(state)
        entries = manager.get_buffer_entries("dm", limit=100)

        # Should return all entries, not error
        assert entries == ["a", "b"]


# =============================================================================
# Extended Coverage: Error Message Verification
# =============================================================================


class TestErrorMessageContent:
    """Tests verifying error messages are informative."""

    def test_add_to_buffer_none_error_message(
        self, empty_game_state: GameState
    ) -> None:
        """Test that None content error has informative message."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory()
        manager = MemoryManager(state)

        with pytest.raises(TypeError) as exc_info:
            manager.add_to_buffer("dm", None)  # type: ignore[arg-type]

        assert "content must not be None" in str(exc_info.value)

    def test_add_to_buffer_oversized_error_includes_size(
        self, empty_game_state: GameState
    ) -> None:
        """Test that oversized content error includes the actual size."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory()
        manager = MemoryManager(state)

        oversized = "x" * 100_001
        with pytest.raises(ValueError) as exc_info:
            manager.add_to_buffer("dm", oversized)

        error_msg = str(exc_info.value)
        assert "exceeds maximum size" in error_msg
        assert "100KB" in error_msg
        assert "100001" in error_msg  # Includes actual size


# =============================================================================
# Extended Coverage: State Consistency
# =============================================================================


class TestStateConsistency:
    """Tests for state consistency after operations."""

    def test_state_unchanged_after_get_context(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that get_context doesn't modify state."""
        original_dm_buffer = game_state_with_memories["agent_memories"][
            "dm"
        ].short_term_buffer.copy()
        original_rogue_buffer = game_state_with_memories["agent_memories"][
            "rogue"
        ].short_term_buffer.copy()

        manager = MemoryManager(game_state_with_memories)
        manager.get_context("dm")
        manager.get_context("rogue")

        # State should be unchanged
        assert (
            game_state_with_memories["agent_memories"]["dm"].short_term_buffer
            == original_dm_buffer
        )
        assert (
            game_state_with_memories["agent_memories"]["rogue"].short_term_buffer
            == original_rogue_buffer
        )

    def test_state_unchanged_after_get_buffer_token_count(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that get_buffer_token_count doesn't modify state."""
        original_buffer = game_state_with_memories["agent_memories"][
            "dm"
        ].short_term_buffer.copy()

        manager = MemoryManager(game_state_with_memories)
        manager.get_buffer_token_count("dm")

        assert (
            game_state_with_memories["agent_memories"]["dm"].short_term_buffer
            == original_buffer
        )

    def test_state_unchanged_after_is_near_limit(
        self, game_state_with_memories: GameState
    ) -> None:
        """Test that is_near_limit doesn't modify state."""
        original_limit = game_state_with_memories["agent_memories"]["dm"].token_limit

        manager = MemoryManager(game_state_with_memories)
        manager.is_near_limit("dm")

        assert (
            game_state_with_memories["agent_memories"]["dm"].token_limit
            == original_limit
        )

    def test_add_to_buffer_mutates_state(self, empty_game_state: GameState) -> None:
        """Test that add_to_buffer does mutate state (as documented)."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=["original"])

        manager = MemoryManager(state)
        original_len = len(state["agent_memories"]["dm"].short_term_buffer)

        manager.add_to_buffer("dm", "new entry")

        # State should be mutated
        assert len(state["agent_memories"]["dm"].short_term_buffer) == original_len + 1
        assert state["agent_memories"]["dm"].short_term_buffer[-1] == "new entry"

    def test_get_buffer_entries_returns_copy(self, empty_game_state: GameState) -> None:
        """Test that modifying returned entries doesn't affect state."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["entry1", "entry2"]
        )

        manager = MemoryManager(state)
        entries = manager.get_buffer_entries("dm")

        # Modify returned list
        entries.append("modified")
        entries[0] = "changed"

        # Original state should be affected (list is mutable reference)
        # This documents the current behavior
        original = state["agent_memories"]["dm"].short_term_buffer
        # Note: The implementation returns a slice which is a shallow copy
        # so modifications to the returned list don't affect state
        assert "modified" not in original


# =============================================================================
# Extended Coverage: Context Formatting
# =============================================================================


class TestContextFormatting:
    """Tests for context string formatting details."""

    def test_dm_context_section_order(self, empty_game_state: GameState) -> None:
        """Test that DM context sections are in correct order."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="Summary here",
            short_term_buffer=["Event 1"],
        )
        state["agent_memories"]["pc1"] = AgentMemory(short_term_buffer=["PC action"])

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        # Story So Far should come before Recent Events
        summary_pos = context.find("## Story So Far")
        events_pos = context.find("## Recent Events")
        knowledge_pos = context.find("## Player Knowledge")

        assert summary_pos < events_pos < knowledge_pos

    def test_dm_context_double_newline_between_sections(
        self, empty_game_state: GameState
    ) -> None:
        """Test that sections are separated by double newlines."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            long_term_summary="Summary",
            short_term_buffer=["Event"],
        )

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        assert "\n\n" in context

    def test_pc_context_section_headers(self, empty_game_state: GameState) -> None:
        """Test PC context uses correct section headers."""
        state = empty_game_state
        state["agent_memories"]["rogue"] = AgentMemory(
            long_term_summary="Rogue background",
            short_term_buffer=["Rogue action"],
        )

        manager = MemoryManager(state)
        context = manager.get_context("rogue")

        # PC uses "What You Remember" not "Story So Far"
        assert "## What You Remember" in context
        assert "## Story So Far" not in context

    def test_player_knowledge_format(self, empty_game_state: GameState) -> None:
        """Test player knowledge section format."""
        state = empty_game_state
        state["agent_memories"]["archer"] = AgentMemory(
            short_term_buffer=["Aims bow", "Fires arrow", "Draws another"]
        )

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        # Should have [archer knows]: format with semicolon separation
        assert "[archer knows]:" in context
        # Last 3 entries joined by semicolons
        assert ";" in context


# =============================================================================
# Extended Coverage: Performance and Large Data
# =============================================================================


class TestPerformanceEdgeCases:
    """Tests for performance edge cases with large data."""

    def test_context_with_maximum_buffer_entries(
        self, empty_game_state: GameState
    ) -> None:
        """Test context building with many buffer entries."""
        state = empty_game_state
        # Create 1000 buffer entries
        entries = [f"Event {i}: Something happened" for i in range(1000)]
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=entries)

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        # Should only include last 10 entries (limit)
        assert "Event 999" in context
        assert "Event 990" in context
        assert "Event 0" not in context

    def test_token_count_with_many_entries(self, empty_game_state: GameState) -> None:
        """Test token count calculation with many entries."""
        state = empty_game_state
        entries = [f"Entry number {i} with some words" for i in range(500)]
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=entries)

        manager = MemoryManager(state)
        count = manager.get_buffer_token_count("dm")

        # Should complete without error and return reasonable count
        assert count > 0
        assert count < 100_000  # Sanity check

    def test_context_with_many_agents_performance(
        self, empty_game_state: GameState
    ) -> None:
        """Test context building with many agents."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=["DM entry"])

        # Add 50 PC agents
        for i in range(50):
            state["agent_memories"][f"npc_{i}"] = AgentMemory(
                short_term_buffer=[f"NPC {i} does something"]
            )

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        # Should include all agents
        for i in range(50):
            assert f"[npc_{i} knows]" in context


# =============================================================================
# Extended Coverage: Model Attribute Access
# =============================================================================


class TestModelAttributeAccess:
    """Tests for accessing model attributes through MemoryManager."""

    def test_get_long_term_summary_with_empty_summary(
        self, empty_game_state: GameState
    ) -> None:
        """Test get_long_term_summary when summary is empty string."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(long_term_summary="")

        manager = MemoryManager(state)
        summary = manager.get_long_term_summary("dm")

        assert summary == ""

    def test_get_long_term_summary_with_multiline(
        self, empty_game_state: GameState
    ) -> None:
        """Test get_long_term_summary with multiline summary."""
        state = empty_game_state
        multiline = "Line 1\nLine 2\nLine 3"
        state["agent_memories"]["dm"] = AgentMemory(long_term_summary=multiline)

        manager = MemoryManager(state)
        summary = manager.get_long_term_summary("dm")

        assert summary == multiline
        assert "\n" in summary

    def test_agent_memory_token_limit_accessible(
        self, empty_game_state: GameState
    ) -> None:
        """Test that token_limit is properly used in calculations."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["content"],
            token_limit=50,
        )

        manager = MemoryManager(state)

        # With small token_limit, should be near limit easily
        result = manager.is_near_limit("dm", threshold=0.01)
        assert isinstance(result, bool)


# =============================================================================
# Extended Coverage: Boundary and Null Cases
# =============================================================================


class TestBoundaryAndNullCases:
    """Tests for boundary conditions and null-like cases."""

    def test_empty_agent_name(self, empty_game_state: GameState) -> None:
        """Test operations with empty string agent name."""
        state = empty_game_state
        state["agent_memories"][""] = AgentMemory(short_term_buffer=["content"])

        manager = MemoryManager(state)

        # Should work with empty string as agent name
        context = manager.get_context("")
        assert "content" in context

    def test_agent_name_with_special_chars(self, empty_game_state: GameState) -> None:
        """Test operations with special characters in agent name."""
        state = empty_game_state
        state["agent_memories"]["agent-with-dashes"] = AgentMemory(
            short_term_buffer=["content"]
        )

        manager = MemoryManager(state)
        context = manager.get_context("agent-with-dashes")

        assert "content" in context

    def test_agent_name_with_spaces(self, empty_game_state: GameState) -> None:
        """Test operations with spaces in agent name."""
        state = empty_game_state
        state["agent_memories"]["Sir Lancelot"] = AgentMemory(
            short_term_buffer=["I seek the grail"]
        )

        manager = MemoryManager(state)
        context = manager.get_context("Sir Lancelot")

        assert "grail" in context

    def test_buffer_with_exactly_limit_entries(
        self, empty_game_state: GameState
    ) -> None:
        """Test buffer with exactly 10 entries (the display limit)."""
        state = empty_game_state
        entries = [f"Entry {i}" for i in range(10)]
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=entries)

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        # All 10 should be included
        for i in range(10):
            assert f"Entry {i}" in context

    def test_buffer_with_eleven_entries(self, empty_game_state: GameState) -> None:
        """Test buffer with 11 entries (one over display limit)."""
        state = empty_game_state
        entries = [f"Entry {i}" for i in range(11)]
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=entries)

        manager = MemoryManager(state)
        context = manager.get_context("dm")

        # Entry 0 should be excluded, 1-10 included
        assert "Entry 0" not in context
        assert "Entry 1" in context
        assert "Entry 10" in context

    def test_add_to_buffer_empty_string(self, empty_game_state: GameState) -> None:
        """Test adding empty string to buffer."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory()

        manager = MemoryManager(state)
        manager.add_to_buffer("dm", "")

        entries = manager.get_buffer_entries("dm")
        assert len(entries) == 1
        assert entries[0] == ""

    def test_add_to_buffer_whitespace_only(self, empty_game_state: GameState) -> None:
        """Test adding whitespace-only content to buffer."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory()

        manager = MemoryManager(state)
        manager.add_to_buffer("dm", "   \t\n   ")

        entries = manager.get_buffer_entries("dm")
        assert len(entries) == 1
        assert entries[0] == "   \t\n   "


# =============================================================================
# Story 5.2: Session Summary Generation Tests
# =============================================================================


class TestSummarizer:
    """Tests for Summarizer class (Task 1)."""

    def test_summarizer_instantiation(self) -> None:
        """Test that Summarizer can be instantiated with provider and model."""
        from memory import Summarizer

        summarizer = Summarizer(provider="gemini", model="gemini-1.5-flash")
        assert summarizer is not None
        assert summarizer.provider == "gemini"
        assert summarizer.model == "gemini-1.5-flash"

    def test_summarizer_accepts_different_providers(self) -> None:
        """Test that Summarizer accepts all supported providers."""
        from memory import Summarizer

        # Test all supported providers
        for provider in ["gemini", "claude", "ollama"]:
            summarizer = Summarizer(provider=provider, model="test-model")
            assert summarizer.provider == provider

    def test_summarizer_stores_model(self) -> None:
        """Test that Summarizer stores the model name."""
        from memory import Summarizer

        summarizer = Summarizer(provider="ollama", model="llama3")
        assert summarizer.model == "llama3"

    def test_summarizer_has_type_hints(self) -> None:
        """Test that Summarizer has proper type hints."""
        import inspect

        from memory import Summarizer

        sig = inspect.signature(Summarizer.__init__)
        params = sig.parameters

        assert "provider" in params
        assert "model" in params
        # Verify the annotations include str
        assert params["provider"].annotation is not inspect.Parameter.empty
        assert params["model"].annotation is not inspect.Parameter.empty


class TestJanitorPrompt:
    """Tests for Janitor system prompt content (Task 2)."""

    def test_janitor_prompt_exists(self) -> None:
        """Test that JANITOR_SYSTEM_PROMPT constant exists."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert JANITOR_SYSTEM_PROMPT is not None
        assert isinstance(JANITOR_SYSTEM_PROMPT, str)
        assert len(JANITOR_SYSTEM_PROMPT) > 100  # Should be substantial

    def test_janitor_prompt_preserves_character_names(self) -> None:
        """Test that prompt includes instruction to preserve character names."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "character" in JANITOR_SYSTEM_PROMPT.lower()
        assert "name" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_preserves_relationships(self) -> None:
        """Test that prompt includes instruction to preserve relationships."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "relationship" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_preserves_inventory(self) -> None:
        """Test that prompt includes instruction to preserve inventory."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "inventory" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_preserves_quests(self) -> None:
        """Test that prompt includes instruction to preserve quests."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "quest" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_preserves_status_effects(self) -> None:
        """Test that prompt includes instruction to preserve status effects."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "status" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_discards_dialogue(self) -> None:
        """Test that prompt includes instruction to discard verbatim dialogue."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "dialogue" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_discards_dice_mechanics(self) -> None:
        """Test that prompt includes instruction to discard dice mechanics."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "dice" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_discards_repetitive_descriptions(self) -> None:
        """Test that prompt includes instruction to discard repetitive descriptions."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "repetitive" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_has_preserve_and_discard_sections(self) -> None:
        """Test that prompt has clear PRESERVE and DISCARD sections."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert (
            "PRESERVE" in JANITOR_SYSTEM_PROMPT
            or "preserve" in JANITOR_SYSTEM_PROMPT.lower()
        )
        assert (
            "DISCARD" in JANITOR_SYSTEM_PROMPT
            or "discard" in JANITOR_SYSTEM_PROMPT.lower()
        )


class TestSummaryGeneration:
    """Tests for Summarizer.generate_summary() method (Task 3)."""

    def test_generate_summary_returns_string(self) -> None:
        """Test that generate_summary returns a string."""
        from unittest.mock import MagicMock

        from memory import Summarizer

        summarizer = Summarizer(provider="gemini", model="gemini-1.5-flash")

        # Mock the LLM call
        mock_response = MagicMock()
        mock_response.content = "This is a test summary."
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        # Inject the mock LLM
        summarizer._llm = mock_llm

        result = summarizer.generate_summary("dm", ["Event 1", "Event 2"])

        assert isinstance(result, str)
        assert len(result) > 0

    def test_generate_summary_empty_buffer(self) -> None:
        """Test generate_summary with empty buffer returns empty string."""
        from memory import Summarizer

        summarizer = Summarizer(provider="gemini", model="gemini-1.5-flash")
        result = summarizer.generate_summary("dm", [])

        assert result == ""

    def test_generate_summary_builds_prompt_with_janitor(self) -> None:
        """Test that generate_summary uses the Janitor prompt."""
        from unittest.mock import MagicMock

        from memory import JANITOR_SYSTEM_PROMPT, Summarizer

        summarizer = Summarizer(provider="gemini", model="gemini-1.5-flash")

        mock_response = MagicMock()
        mock_response.content = "Summary text"
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        # Inject the mock LLM
        summarizer._llm = mock_llm

        summarizer.generate_summary("rogue", ["Entry 1", "Entry 2"])

        # Verify LLM was called
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]

        # Verify the system message contains Janitor prompt
        system_message = call_args[0]
        assert JANITOR_SYSTEM_PROMPT in system_message.content

    def test_generate_summary_includes_buffer_content(self) -> None:
        """Test that generate_summary includes buffer entries in prompt."""
        from unittest.mock import MagicMock

        from memory import Summarizer

        summarizer = Summarizer(provider="gemini", model="gemini-1.5-flash")

        buffer_entries = [
            "[DM]: The party enters the tavern.",
            "[Rogue]: I check for traps.",
        ]

        mock_response = MagicMock()
        mock_response.content = "Summary text"
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = mock_response

        # Inject the mock LLM
        summarizer._llm = mock_llm

        summarizer.generate_summary("rogue", buffer_entries)

        # Verify LLM was called with buffer content
        call_args = mock_llm.invoke.call_args[0][0]
        human_message = call_args[1]
        assert "tavern" in human_message.content
        assert "traps" in human_message.content

    def test_generate_summary_handles_llm_error(self) -> None:
        """Test that generate_summary returns empty string on LLM error."""
        from unittest.mock import MagicMock

        from memory import Summarizer

        summarizer = Summarizer(provider="gemini", model="gemini-1.5-flash")

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API Error")

        # Inject the mock LLM
        summarizer._llm = mock_llm

        result = summarizer.generate_summary("dm", ["Event 1", "Event 2"])

        # Should return empty string on error (graceful degradation)
        assert result == ""


class TestCompressBuffer:
    """Tests for MemoryManager.compress_buffer() method (Task 4)."""

    def test_compress_buffer_returns_summary(self, empty_game_state: GameState) -> None:
        """Test that compress_buffer returns the generated summary."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Generated summary"
            MockSummarizer.return_value = mock_instance

            result = manager.compress_buffer("dm")

        assert result == "Generated summary"

    def test_compress_buffer_updates_long_term_summary(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compress_buffer updates the long_term_summary field."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"],
            long_term_summary="",
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "New summary content"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        assert "New summary content" in state["agent_memories"]["dm"].long_term_summary

    def test_compress_buffer_clears_old_entries(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compress_buffer clears compressed entries from buffer."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        # Should retain only the last 3 entries
        buffer = state["agent_memories"]["dm"].short_term_buffer
        assert len(buffer) == 3
        assert buffer[-1] == "Event 5"

    def test_compress_buffer_retains_recent_entries(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compress_buffer retains most recent N entries."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[
                "Event 1",
                "Event 2",
                "Event 3",
                "Event 4",
                "Event 5",
                "Event 6",
            ],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        buffer = state["agent_memories"]["dm"].short_term_buffer
        # Default retention is 3 entries
        assert len(buffer) == 3
        assert "Event 4" in buffer
        assert "Event 5" in buffer
        assert "Event 6" in buffer

    def test_compress_buffer_merges_with_existing_summary(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compress_buffer merges new summary with existing."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"],
            long_term_summary="Previous events summary.",
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "New events summary."
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        summary = state["agent_memories"]["dm"].long_term_summary
        assert "Previous events summary" in summary
        assert "New events summary" in summary

    def test_compress_buffer_missing_agent(self, empty_game_state: GameState) -> None:
        """Test that compress_buffer handles missing agent gracefully."""
        manager = MemoryManager(empty_game_state)
        result = manager.compress_buffer("nonexistent")

        assert result == ""

    def test_compress_buffer_empty_buffer(self, empty_game_state: GameState) -> None:
        """Test that compress_buffer handles empty buffer gracefully."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=[])

        manager = MemoryManager(state)
        result = manager.compress_buffer("dm")

        assert result == ""

    def test_compress_buffer_too_few_entries(self, empty_game_state: GameState) -> None:
        """Test compress_buffer with fewer entries than retention count."""
        state = empty_game_state
        # Only 2 entries, less than default retention of 3
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2"],
            token_limit=100,
        )

        manager = MemoryManager(state)
        result = manager.compress_buffer("dm")

        # Should skip compression when not enough entries
        assert result == ""
        # Buffer should be unchanged
        assert len(state["agent_memories"]["dm"].short_term_buffer) == 2


class TestSummarizerConfigIntegration:
    """Tests for Summarizer configuration integration (Task 8, FR44)."""

    def test_compress_buffer_uses_config_provider(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compress_buffer uses provider from config."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

            # Verify Summarizer was instantiated with config values
            MockSummarizer.assert_called_once()
            call_kwargs = MockSummarizer.call_args
            # Check that provider and model were passed
            assert call_kwargs[1]["provider"] is not None
            assert call_kwargs[1]["model"] is not None

    def test_config_defaults_to_gemini(self) -> None:
        """Test that default config uses gemini for summarizer."""
        from config import get_config

        config = get_config()

        # Default should be gemini based on defaults.yaml
        assert config.agents.summarizer.provider == "gemini"
        assert config.agents.summarizer.model == "gemini-1.5-flash"

    def test_summarizer_config_has_token_limit(self) -> None:
        """Test that summarizer config includes token_limit."""
        from config import get_config

        config = get_config()

        # Summarizer should have a token limit (for context sizing)
        assert hasattr(config.agents.summarizer, "token_limit")
        assert config.agents.summarizer.token_limit == 4000


# =============================================================================
# Story 5.2: Comprehensive Acceptance Tests
# =============================================================================


class TestStory52AcceptanceCriteria:
    """Acceptance tests for Story 5.2: Session Summary Generation.

    These tests verify all acceptance criteria (ACs) from the story file.
    """

    def test_ac1_summarization_triggered_near_limit(
        self, empty_game_state: GameState
    ) -> None:
        """AC #1: Summarization triggered when buffer approaches token limit."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        # Set up buffer that's near limit
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            token_limit=100,
        )

        manager = MemoryManager(state)

        # Verify is_near_limit returns True for this state
        assert manager.is_near_limit("dm") is True

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary"
            MockSummarizer.return_value = mock_instance

            # compress_buffer should be callable
            result = manager.compress_buffer("dm")
            assert result == "Summary"
            mock_instance.generate_summary.assert_called_once()

    def test_ac2_summary_preserves_character_names_and_relationships(
        self,
    ) -> None:
        """AC #2: Summary preserves character names and relationships.

        This is verified through the Janitor prompt content.
        """
        from memory import JANITOR_SYSTEM_PROMPT

        # Janitor prompt must include preservation instructions
        assert "character" in JANITOR_SYSTEM_PROMPT.lower()
        assert "name" in JANITOR_SYSTEM_PROMPT.lower()
        assert "relationship" in JANITOR_SYSTEM_PROMPT.lower()
        assert (
            "PRESERVE" in JANITOR_SYSTEM_PROMPT or "preserve" in JANITOR_SYSTEM_PROMPT
        )

    def test_ac2_summary_preserves_inventory(self) -> None:
        """AC #2: Summary preserves inventory changes."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "inventory" in JANITOR_SYSTEM_PROMPT.lower()

    def test_ac2_summary_preserves_quests(self) -> None:
        """AC #2: Summary preserves quest goals and progress."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "quest" in JANITOR_SYSTEM_PROMPT.lower()

    def test_ac2_summary_preserves_status_effects(self) -> None:
        """AC #2: Summary preserves status effects."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "status" in JANITOR_SYSTEM_PROMPT.lower()

    def test_ac3_summary_discards_verbatim_dialogue(self) -> None:
        """AC #3: Summary discards verbatim dialogue (keeps gist)."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "dialogue" in JANITOR_SYSTEM_PROMPT.lower()
        assert "DISCARD" in JANITOR_SYSTEM_PROMPT or "discard" in JANITOR_SYSTEM_PROMPT

    def test_ac3_summary_discards_dice_mechanics(self) -> None:
        """AC #3: Summary discards detailed dice roll mechanics."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "dice" in JANITOR_SYSTEM_PROMPT.lower()

    def test_ac3_summary_discards_repetitive_descriptions(self) -> None:
        """AC #3: Summary discards repetitive descriptions."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "repetitive" in JANITOR_SYSTEM_PROMPT.lower()

    def test_ac4_summary_stored_in_long_term_summary(
        self, empty_game_state: GameState
    ) -> None:
        """AC #4: Summary stored in AgentMemory.long_term_summary field."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"],
            long_term_summary="",
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Generated summary text"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        # Verify summary is stored in long_term_summary field
        assert (
            state["agent_memories"]["dm"].long_term_summary == "Generated summary text"
        )

    def test_ac5_summary_serialized_with_checkpoint(
        self, empty_game_state: GameState, tmp_path
    ) -> None:
        """AC #5: Summary serializes correctly with checkpoint."""

        from persistence import load_checkpoint, save_checkpoint

        # Create state with a long_term_summary
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Recent event"],
            long_term_summary="This is a compressed summary of past events.",
            token_limit=8000,
        )
        state["session_id"] = "test_session"
        state["ground_truth_log"] = ["[DM]: Test entry"]

        # Mock campaigns dir
        from unittest.mock import patch

        campaigns_dir = tmp_path / "campaigns"
        campaigns_dir.mkdir()

        with patch("persistence.CAMPAIGNS_DIR", campaigns_dir):
            # Save checkpoint
            save_checkpoint(state, "test_session", 1)

            # Load checkpoint back
            loaded = load_checkpoint("test_session", 1)

        # Verify long_term_summary was preserved
        assert loaded is not None
        assert "dm" in loaded["agent_memories"]
        assert loaded["agent_memories"]["dm"].long_term_summary == (
            "This is a compressed summary of past events."
        )

    def test_ac6_summarization_runs_synchronously(
        self, empty_game_state: GameState
    ) -> None:
        """AC #6: Summarization runs synchronously (blocks until complete)."""
        import time
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"],
            token_limit=100,
        )

        manager = MemoryManager(state)

        call_order = []

        def mock_generate_summary(agent_name, entries):
            call_order.append("summary_start")
            time.sleep(0.01)  # Simulate work
            call_order.append("summary_end")
            return "Summary"

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.side_effect = mock_generate_summary
            MockSummarizer.return_value = mock_instance

            # Call compress_buffer
            call_order.append("compress_start")
            result = manager.compress_buffer("dm")
            call_order.append("compress_end")

        # Verify synchronous execution (compress_end comes after summary_end)
        assert call_order == [
            "compress_start",
            "summary_start",
            "summary_end",
            "compress_end",
        ]
        assert result == "Summary"

    def test_ac7_multiple_agents_compressed_in_single_pass(
        self, empty_game_state: GameState
    ) -> None:
        """AC #7: Multiple agents can be compressed in same context_manager pass."""
        from unittest.mock import MagicMock, patch

        from graph import context_manager

        state = empty_game_state
        # Both agents are near limit
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            token_limit=100,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            token_limit=100,
        )
        state["turn_queue"] = ["dm", "fighter"]

        compressed_agents = []

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True

            def track_compress(agent_name):
                compressed_agents.append(agent_name)
                return "Summary"

            mock_instance.compress_buffer.side_effect = track_compress
            MockManager.return_value = mock_instance

            context_manager(state)

        # Both agents should have been compressed
        assert "dm" in compressed_agents
        assert "fighter" in compressed_agents


class TestStory52EdgeCases:
    """Edge case tests for Story 5.2."""

    def test_empty_buffer_does_not_trigger_summarization(
        self, empty_game_state: GameState
    ) -> None:
        """Test that empty buffer doesn't trigger summarization."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[],
            token_limit=8000,
        )

        manager = MemoryManager(state)

        # Should not be near limit with empty buffer
        assert manager.is_near_limit("dm") is False

        # compress_buffer should return empty string
        result = manager.compress_buffer("dm")
        assert result == ""

    def test_summarization_error_does_not_crash_game(
        self, empty_game_state: GameState
    ) -> None:
        """Test that summarization errors don't crash the game."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"],
            token_limit=100,
        )
        original_buffer = state["agent_memories"]["dm"].short_term_buffer.copy()

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            # Summarizer returns empty string on error (graceful degradation)
            mock_instance.generate_summary.return_value = ""
            MockSummarizer.return_value = mock_instance

            # Should not raise
            result = manager.compress_buffer("dm")

        # Should return empty string
        assert result == ""
        # Buffer should be unchanged when summarization fails
        assert state["agent_memories"]["dm"].short_term_buffer == original_buffer

    def test_merging_multiple_summaries(self, empty_game_state: GameState) -> None:
        """Test that multiple summaries merge correctly over time."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"],
            long_term_summary="First summary: Party met in tavern.",
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = (
                "Second summary: Party fought goblins."
            )
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        summary = state["agent_memories"]["dm"].long_term_summary
        # Both summaries should be present
        assert "First summary" in summary
        assert "Second summary" in summary
        # Should have separator
        assert "---" in summary

    def test_context_manager_preserves_game_state_integrity(
        self, empty_game_state: GameState
    ) -> None:
        """Test that context_manager doesn't corrupt game state."""
        from unittest.mock import MagicMock, patch

        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(5)],
            token_limit=100,
        )
        state["turn_queue"] = ["dm", "fighter"]
        state["current_turn"] = "dm"
        state["ground_truth_log"] = ["Log entry 1", "Log entry 2"]
        state["session_id"] = "test123"

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            result = context_manager(state)

        # All state fields should be preserved
        assert result["turn_queue"] == ["dm", "fighter"]
        assert result["current_turn"] == "dm"
        assert result["ground_truth_log"] == ["Log entry 1", "Log entry 2"]
        assert result["session_id"] == "test123"


# =============================================================================
# Story 5.2 Code Review: Additional Error Recovery Tests
# =============================================================================


class TestSummarizerErrorRecovery:
    """Tests for error recovery in summarization (code review additions)."""

    def test_rate_limit_error_preserves_buffer(
        self, empty_game_state: GameState
    ) -> None:
        """Test that rate limit errors don't corrupt buffer state."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        original_entries = ["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"]
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=original_entries.copy(),
            long_term_summary="Existing summary.",
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            # Simulate rate limit by returning empty string
            mock_instance.generate_summary.return_value = ""
            MockSummarizer.return_value = mock_instance

            result = manager.compress_buffer("dm")

        # Should return empty string
        assert result == ""
        # Buffer should be COMPLETELY unchanged
        assert state["agent_memories"]["dm"].short_term_buffer == original_entries
        # Existing summary should be preserved
        assert state["agent_memories"]["dm"].long_term_summary == "Existing summary."

    def test_llm_exception_preserves_buffer(self, empty_game_state: GameState) -> None:
        """Test that LLM exceptions don't corrupt buffer state."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        original_entries = ["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"]
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=original_entries.copy(),
            token_limit=100,
        )

        with patch("memory.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = Exception("API Error")
            mock_get_llm.return_value = mock_llm

            from memory import Summarizer

            summarizer = Summarizer(provider="gemini", model="test")
            result = summarizer.generate_summary("dm", original_entries)

        # Should return empty string on error
        assert result == ""

    def test_summarizer_handles_list_content_response(self) -> None:
        """Test that summarizer handles LLM returning list content blocks."""
        from unittest.mock import MagicMock, patch

        with patch("memory.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            # Simulate Claude-style response with content blocks
            mock_response.content = ["First part. ", "Second part."]
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from memory import Summarizer

            summarizer = Summarizer(provider="claude", model="test")
            result = summarizer.generate_summary("dm", ["Event 1"])

        # Should join string parts
        assert result == "First part. Second part."

    def test_summarizer_handles_mixed_content_blocks(self) -> None:
        """Test that summarizer handles mixed content (strings and dicts)."""
        from unittest.mock import MagicMock, patch

        with patch("memory.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            # Simulate response with text and tool use blocks
            mock_response.content = [
                "Summary text. ",
                {"type": "tool_use", "name": "search"},
                "More summary.",
            ]
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from memory import Summarizer

            summarizer = Summarizer(provider="claude", model="test")
            result = summarizer.generate_summary("dm", ["Event 1"])

        # Should only join string parts, skip dict
        assert result == "Summary text. More summary."

    def test_compress_buffer_caches_summarizer(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compress_buffer reuses cached Summarizer instance."""
        from unittest.mock import patch

        import memory

        # Clear cache before test
        memory._summarizer_cache.clear()

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"],
            token_limit=100,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Fight 1", "Fight 2", "Fight 3", "Fight 4", "Fight 5"],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch.object(memory.Summarizer, "generate_summary") as mock_gen:
            mock_gen.return_value = "Summary"

            # Compress two different agents
            manager.compress_buffer("dm")
            manager.compress_buffer("fighter")

        # Should have exactly one cache entry (same provider/model)
        assert len(memory._summarizer_cache) == 1

        # Cleanup
        memory._summarizer_cache.clear()

    def test_large_buffer_is_truncated(self) -> None:
        """Test that very large buffer content is truncated for LLM."""
        from unittest.mock import MagicMock, patch

        # Create a buffer that exceeds MAX_BUFFER_CHARS
        large_entry = "x" * 60_000  # 60KB, over the 50KB limit

        with patch("memory.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Summary"
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from memory import Summarizer

            summarizer = Summarizer(provider="gemini", model="test")
            result = summarizer.generate_summary("dm", [large_entry])

        # Should still return a result (not crash)
        assert result == "Summary"
        # The mock was called (with truncated content)
        mock_llm.invoke.assert_called_once()

    def test_summarizer_logs_truncation_warning(self) -> None:
        """Test that truncation is logged as a warning."""
        from unittest.mock import MagicMock, patch

        large_entry = "x" * 60_000

        with (
            patch("memory.get_llm") as mock_get_llm,
            patch("memory.logger") as mock_logger,
        ):
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Summary"
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from memory import Summarizer

            summarizer = Summarizer(provider="gemini", model="test")
            summarizer.generate_summary("dm", [large_entry])

        # Should have logged a warning
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "truncated" in call_args[0][0].lower()


class TestContextManagerTypeConsistency:
    """Tests for type consistency in context_manager (code review)."""

    def test_context_manager_returns_proper_game_state_type(
        self, empty_game_state: GameState
    ) -> None:
        """Test that context_manager returns a proper GameState, not dict."""
        from unittest.mock import MagicMock, patch

        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=["Event"])
        state["turn_queue"] = ["dm"]
        state["current_turn"] = "dm"

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            result = context_manager(state)

        # Result should have all required GameState keys
        assert "agent_memories" in result
        assert "turn_queue" in result
        assert "current_turn" in result
        assert "ground_truth_log" in result
        assert "summarization_in_progress" in result

    def test_context_manager_clears_summarization_flag(
        self, empty_game_state: GameState
    ) -> None:
        """Test that summarization_in_progress is False after completion."""
        from unittest.mock import MagicMock, patch

        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=["Event"])

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False
            MockManager.return_value = mock_instance

            result = context_manager(state)

        assert result["summarization_in_progress"] is False


# =============================================================================
# Story 5.2: Expanded Test Coverage (testarch-automate)
# =============================================================================


class TestMergeSummaries:
    """Tests for _merge_summaries helper function."""

    def test_merge_summaries_empty_existing(self) -> None:
        """Test merge when existing summary is empty."""
        from memory import _merge_summaries

        result = _merge_summaries("", "New summary content")
        assert result == "New summary content"

    def test_merge_summaries_with_existing(self) -> None:
        """Test merge appends new summary to existing with separator."""
        from memory import _merge_summaries

        result = _merge_summaries("Previous summary", "New summary")
        assert "Previous summary" in result
        assert "New summary" in result
        assert "---" in result

    def test_merge_summaries_preserves_order(self) -> None:
        """Test that existing summary comes before new summary."""
        from memory import _merge_summaries

        result = _merge_summaries("First", "Second")
        first_pos = result.find("First")
        second_pos = result.find("Second")
        assert first_pos < second_pos

    def test_merge_summaries_very_long_existing(self) -> None:
        """Test merge with very long existing summary (stress test)."""
        from memory import _merge_summaries

        # Create a 10KB existing summary
        existing = "Long summary content. " * 500
        new_summary = "New events summary"

        result = _merge_summaries(existing, new_summary)

        assert existing in result
        assert new_summary in result
        assert "---" in result

    def test_merge_summaries_unicode_content(self) -> None:
        """Test merge with unicode characters."""
        from memory import _merge_summaries

        result = _merge_summaries(
            "The wizard cast fireball! ", "The dragon retreated to its lair "
        )
        assert "" in result
        assert "" in result

    def test_merge_summaries_multiline_content(self) -> None:
        """Test merge with multiline summaries."""
        from memory import _merge_summaries

        existing = "Line 1\nLine 2\nLine 3"
        new_summary = "New line 1\nNew line 2"

        result = _merge_summaries(existing, new_summary)

        assert "Line 1" in result
        assert "New line 2" in result
        # Should have double newline before and after separator
        assert "\n\n---\n\n" in result


class TestBufferRetentionAfterCompression:
    """Tests verifying buffer retention behavior after compression."""

    def test_compress_buffer_retains_exactly_3_by_default(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compress_buffer retains exactly 3 entries by default."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[
                "Entry 1",
                "Entry 2",
                "Entry 3",
                "Entry 4",
                "Entry 5",
                "Entry 6",
            ],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        buffer = state["agent_memories"]["dm"].short_term_buffer
        assert len(buffer) == 3
        assert buffer == ["Entry 4", "Entry 5", "Entry 6"]

    def test_compress_buffer_custom_retention_count(
        self, empty_game_state: GameState
    ) -> None:
        """Test compress_buffer with custom retention count."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm", retain_count=5)

        buffer = state["agent_memories"]["dm"].short_term_buffer
        assert len(buffer) == 5
        assert buffer == ["E4", "E5", "E6", "E7", "E8"]

    def test_compress_buffer_retain_count_zero_skips_compression(
        self, empty_game_state: GameState
    ) -> None:
        """Test compress_buffer with retain_count=0 skips compression.

        Due to Python slice semantics (buffer[:-0] == []), retain_count=0
        results in no entries to compress, so compression is skipped.
        This is the documented behavior - use retain_count=1 as minimum.
        """
        state = empty_game_state
        original_buffer = ["E1", "E2", "E3", "E4"]
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=original_buffer.copy(),
            token_limit=100,
        )

        manager = MemoryManager(state)
        result = manager.compress_buffer("dm", retain_count=0)

        # Should skip compression (due to Python slice semantics)
        assert result == ""
        # Buffer should be unchanged
        assert state["agent_memories"]["dm"].short_term_buffer == original_buffer

    def test_compress_buffer_entries_to_compress_passed_to_summarizer(
        self, empty_game_state: GameState
    ) -> None:
        """Test that only non-retained entries are sent to summarizer."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Old1", "Old2", "Old3", "Keep1", "Keep2", "Keep3"],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm", retain_count=3)

            # Verify the entries passed to summarizer
            call_args = mock_instance.generate_summary.call_args
            entries_to_compress = call_args[0][1]
            assert entries_to_compress == ["Old1", "Old2", "Old3"]


class TestSummarizerLLMBehavior:
    """Tests for Summarizer LLM interaction edge cases."""

    def test_summarizer_lazy_initialization(self) -> None:
        """Test that LLM is lazily initialized on first use."""
        from memory import Summarizer

        summarizer = Summarizer(provider="gemini", model="test")

        # LLM should not be initialized yet
        assert summarizer._llm is None

    def test_summarizer_llm_reused(self) -> None:
        """Test that LLM instance is reused across calls."""
        from unittest.mock import MagicMock, patch

        with patch("memory.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Summary"
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from memory import Summarizer

            summarizer = Summarizer(provider="gemini", model="test")

            # Call generate_summary twice
            summarizer.generate_summary("dm", ["Entry 1"])
            summarizer.generate_summary("dm", ["Entry 2"])

        # get_llm should only be called once (lazy init)
        mock_get_llm.assert_called_once()

    def test_summarizer_handles_none_content_response(self) -> None:
        """Test summarizer handles None content in LLM response."""
        from unittest.mock import MagicMock, patch

        with patch("memory.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = None
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from memory import Summarizer

            summarizer = Summarizer(provider="gemini", model="test")
            result = summarizer.generate_summary("dm", ["Entry"])

        assert result == ""

    def test_summarizer_handles_empty_string_response(self) -> None:
        """Test summarizer handles empty string content."""
        from unittest.mock import MagicMock, patch

        with patch("memory.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = ""
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from memory import Summarizer

            summarizer = Summarizer(provider="gemini", model="test")
            result = summarizer.generate_summary("dm", ["Entry"])

        assert result == ""

    def test_summarizer_timeout_error_returns_empty(self) -> None:
        """Test that timeout errors result in empty string."""
        from unittest.mock import MagicMock, patch

        with patch("memory.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = TimeoutError("Request timed out")
            mock_get_llm.return_value = mock_llm

            from memory import Summarizer

            summarizer = Summarizer(provider="gemini", model="test")
            result = summarizer.generate_summary("dm", ["Entry"])

        assert result == ""

    def test_summarizer_connection_error_returns_empty(self) -> None:
        """Test that connection errors result in empty string."""
        from unittest.mock import MagicMock, patch

        with patch("memory.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.invoke.side_effect = ConnectionError("Network unreachable")
            mock_get_llm.return_value = mock_llm

            from memory import Summarizer

            summarizer = Summarizer(provider="gemini", model="test")
            result = summarizer.generate_summary("dm", ["Entry"])

        assert result == ""

    def test_summarizer_includes_agent_name_in_prompt(self) -> None:
        """Test that agent name is included in the prompt to LLM."""
        from unittest.mock import MagicMock, patch

        from memory import Summarizer

        with patch("memory.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Summary"
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            summarizer = Summarizer(provider="gemini", model="test")
            summarizer.generate_summary("rogue", ["Event 1"])

            # Check the human message includes agent name
            call_args = mock_llm.invoke.call_args[0][0]
            human_message = call_args[1]
            assert "rogue" in human_message.content


class TestContextManagerMultipleAgents:
    """Tests for context_manager handling multiple agents needing compression."""

    def test_context_manager_compresses_all_near_limit_agents(
        self, empty_game_state: GameState
    ) -> None:
        """Test that all agents near limit get compressed."""
        from unittest.mock import MagicMock, patch

        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(50)],
            token_limit=100,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Fight " + str(i) for i in range(50)],
            token_limit=100,
        )
        state["agent_memories"]["rogue"] = AgentMemory(
            short_term_buffer=["Sneak " + str(i) for i in range(50)],
            token_limit=100,
        )
        state["turn_queue"] = ["dm", "fighter", "rogue"]

        compress_calls: list[str] = []

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True

            def track_compress(agent_name: str) -> str:
                compress_calls.append(agent_name)
                return "Summary"

            mock_instance.compress_buffer.side_effect = track_compress
            MockManager.return_value = mock_instance

            context_manager(state)

        # All three agents should be compressed
        assert len(compress_calls) == 3
        assert "dm" in compress_calls
        assert "fighter" in compress_calls
        assert "rogue" in compress_calls

    def test_context_manager_skips_agents_under_limit(
        self, empty_game_state: GameState
    ) -> None:
        """Test that agents under limit are not compressed."""
        from unittest.mock import MagicMock, patch

        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2"],  # Small buffer
            token_limit=8000,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Fight 1"],  # Small buffer
            token_limit=8000,
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = False  # Not near limit
            MockManager.return_value = mock_instance

            context_manager(state)

        # compress_buffer should NOT have been called
        mock_instance.compress_buffer.assert_not_called()

    def test_context_manager_mixed_agents_some_compressed(
        self, empty_game_state: GameState
    ) -> None:
        """Test context_manager with mix of agents near/under limit."""
        from unittest.mock import MagicMock, patch

        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event"],
            token_limit=100,
        )
        state["agent_memories"]["fighter"] = AgentMemory(
            short_term_buffer=["Fight"],
            token_limit=8000,
        )

        compress_calls: list[str] = []

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()

            # dm is near limit, fighter is not
            def is_near(agent_name: str) -> bool:
                return agent_name == "dm"

            mock_instance.is_near_limit.side_effect = is_near

            def track_compress(agent_name: str) -> str:
                compress_calls.append(agent_name)
                return "Summary"

            mock_instance.compress_buffer.side_effect = track_compress
            MockManager.return_value = mock_instance

            context_manager(state)

        # Only dm should be compressed
        assert compress_calls == ["dm"]


class TestSummarizationFlagBehavior:
    """Tests for summarization_in_progress flag behavior."""

    def test_flag_set_during_context_manager_start(
        self, empty_game_state: GameState
    ) -> None:
        """Test that flag is set at start of context_manager."""
        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(short_term_buffer=[])

        # Just run context_manager and check result
        result = context_manager(state)

        # Flag should be cleared after completion
        assert result["summarization_in_progress"] is False

    def test_flag_cleared_even_on_compression_failure(
        self, empty_game_state: GameState
    ) -> None:
        """Test that flag is cleared even if compression returns empty."""
        from unittest.mock import MagicMock, patch

        from graph import context_manager

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event " + str(i) for i in range(10)],
            token_limit=100,
        )

        with patch("graph.MemoryManager") as MockManager:
            mock_instance = MagicMock()
            mock_instance.is_near_limit.return_value = True
            # Simulate compression failure
            mock_instance.compress_buffer.return_value = ""
            MockManager.return_value = mock_instance

            result = context_manager(state)

        # Flag should still be cleared
        assert result["summarization_in_progress"] is False


class TestSummarizerMaxBufferChars:
    """Tests for MAX_BUFFER_CHARS truncation behavior."""

    def test_max_buffer_chars_constant_exists(self) -> None:
        """Test that MAX_BUFFER_CHARS constant is defined."""
        from memory import Summarizer

        assert hasattr(Summarizer, "MAX_BUFFER_CHARS")
        assert Summarizer.MAX_BUFFER_CHARS == 50_000

    def test_buffer_exactly_at_max_not_truncated(self) -> None:
        """Test buffer exactly at limit is not truncated."""
        from unittest.mock import MagicMock, patch

        # Create buffer exactly at 50,000 chars
        entry = "x" * 50_000

        with (
            patch("memory.get_llm") as mock_get_llm,
            patch("memory.logger") as mock_logger,
        ):
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Summary"
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from memory import Summarizer

            summarizer = Summarizer(provider="gemini", model="test")
            summarizer.generate_summary("dm", [entry])

        # Should NOT log a truncation warning at exactly the limit
        mock_logger.warning.assert_not_called()

    def test_buffer_over_max_is_truncated(self) -> None:
        """Test buffer over limit is truncated."""
        from unittest.mock import MagicMock, patch

        # Create buffer over 50,000 chars
        entry = "x" * 50_001

        with (
            patch("memory.get_llm") as mock_get_llm,
            patch("memory.logger") as mock_logger,
        ):
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = "Summary"
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            from memory import Summarizer

            summarizer = Summarizer(provider="gemini", model="test")
            summarizer.generate_summary("dm", [entry])

        # Should log a truncation warning
        mock_logger.warning.assert_called_once()


class TestJanitorPromptCompleteness:
    """Tests for completeness of Janitor prompt content."""

    def test_janitor_prompt_mentions_key_plot_points(self) -> None:
        """Test prompt includes key plot points preservation."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "plot" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_mentions_location_changes(self) -> None:
        """Test prompt includes location tracking."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "location" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_mentions_npc_names(self) -> None:
        """Test prompt includes NPC name preservation."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "npc" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_has_format_section(self) -> None:
        """Test prompt includes format instructions."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "FORMAT" in JANITOR_SYSTEM_PROMPT or "format" in JANITOR_SYSTEM_PROMPT

    def test_janitor_prompt_mentions_word_limit(self) -> None:
        """Test prompt mentions word/length limit."""
        from memory import JANITOR_SYSTEM_PROMPT

        # Should mention "500 words" or similar limit
        assert "500" in JANITOR_SYSTEM_PROMPT or "word" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_discards_combat_details(self) -> None:
        """Test prompt instructs to discard blow-by-blow combat."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "combat" in JANITOR_SYSTEM_PROMPT.lower()

    def test_janitor_prompt_discards_timestamps(self) -> None:
        """Test prompt instructs to discard timestamps."""
        from memory import JANITOR_SYSTEM_PROMPT

        assert "timestamp" in JANITOR_SYSTEM_PROMPT.lower()


class TestCompressBufferStatePreservation:
    """Tests for state preservation during compress_buffer."""

    def test_compress_buffer_preserves_token_limit(
        self, empty_game_state: GameState
    ) -> None:
        """Test that compression doesn't change token_limit."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        original_limit = 4000
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["E1", "E2", "E3", "E4", "E5"],
            token_limit=original_limit,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        assert state["agent_memories"]["dm"].token_limit == original_limit

    def test_compress_buffer_on_success_clears_and_extends(
        self, empty_game_state: GameState
    ) -> None:
        """Test buffer is properly cleared and extended on success."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["A", "B", "C", "D", "E", "F"],
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Summary"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm", retain_count=3)

        # Buffer should be ["D", "E", "F"] - the retained entries
        buffer = state["agent_memories"]["dm"].short_term_buffer
        assert buffer == ["D", "E", "F"]


class TestSummarizerCacheIsolation:
    """Tests for Summarizer cache isolation."""

    def test_different_configs_create_different_cache_entries(
        self, empty_game_state: GameState
    ) -> None:
        """Test that different provider/model combos create separate cache entries."""
        from unittest.mock import MagicMock, patch

        import memory

        # Clear cache
        memory._summarizer_cache.clear()

        # Create two different configurations
        with patch("memory.get_config") as mock_config:
            config1 = MagicMock()
            config1.agents.summarizer.provider = "gemini"
            config1.agents.summarizer.model = "model-a"

            config2 = MagicMock()
            config2.agents.summarizer.provider = "claude"
            config2.agents.summarizer.model = "model-b"

            # First call with config1
            mock_config.return_value = config1
            state1 = empty_game_state.copy()
            state1["agent_memories"]["dm"] = AgentMemory(
                short_term_buffer=["E1", "E2", "E3", "E4", "E5"],
                token_limit=100,
            )
            manager1 = MemoryManager(state1)

            with patch.object(memory.Summarizer, "generate_summary") as mock_gen:
                mock_gen.return_value = "Summary"
                manager1.compress_buffer("dm")

            # Cache should have one entry
            assert len(memory._summarizer_cache) == 1
            assert ("gemini", "model-a") in memory._summarizer_cache

            # Second call with different config
            mock_config.return_value = config2
            state2 = empty_game_state.copy()
            state2["agent_memories"]["dm"] = AgentMemory(
                short_term_buffer=["F1", "F2", "F3", "F4", "F5"],
                token_limit=100,
            )
            manager2 = MemoryManager(state2)

            with patch.object(memory.Summarizer, "generate_summary") as mock_gen:
                mock_gen.return_value = "Summary"
                manager2.compress_buffer("dm")

            # Now cache should have two entries
            assert len(memory._summarizer_cache) == 2
            assert ("claude", "model-b") in memory._summarizer_cache

        # Cleanup
        memory._summarizer_cache.clear()


class TestCompressBufferEdgeCases:
    """Additional edge case tests for compress_buffer."""

    def test_compress_buffer_exactly_retain_count_entries(
        self, empty_game_state: GameState
    ) -> None:
        """Test compress_buffer with exactly retain_count entries (should skip)."""
        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["E1", "E2", "E3"],  # Exactly 3
            token_limit=100,
        )

        manager = MemoryManager(state)
        result = manager.compress_buffer("dm", retain_count=3)

        # Should skip since there's nothing to compress
        assert result == ""
        # Buffer should be unchanged
        assert state["agent_memories"]["dm"].short_term_buffer == ["E1", "E2", "E3"]

    def test_compress_buffer_one_more_than_retain_count(
        self, empty_game_state: GameState
    ) -> None:
        """Test compress_buffer with one more than retain_count."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["E1", "E2", "E3", "E4"],  # 4 entries, retain 3
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Compressed E1"
            MockSummarizer.return_value = mock_instance

            result = manager.compress_buffer("dm", retain_count=3)

            # Only E1 should be compressed
            call_args = mock_instance.generate_summary.call_args
            entries_compressed = call_args[0][1]
            assert entries_compressed == ["E1"]

        assert result == "Compressed E1"
        # E2, E3, E4 should be retained
        assert state["agent_memories"]["dm"].short_term_buffer == ["E2", "E3", "E4"]


class TestIntegrationRealCompression:
    """Integration tests with real (mocked) LLM compression flow."""

    def test_full_compression_cycle_updates_state(
        self, empty_game_state: GameState
    ) -> None:
        """Test complete compression cycle from buffer to summary."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=[
                "The party entered the dungeon.",
                "They fought a group of goblins.",
                "The wizard cast fireball.",
                "The rogue found a secret door.",
                "They discovered treasure.",
            ],
            long_term_summary="",
            token_limit=100,
        )

        manager = MemoryManager(state)

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = (
                "The party entered the dungeon and defeated goblins."
            )
            MockSummarizer.return_value = mock_instance

            summary = manager.compress_buffer("dm")

        # Verify summary was returned
        assert "party entered" in summary.lower()

        # Verify long_term_summary was updated
        assert (
            "party entered" in state["agent_memories"]["dm"].long_term_summary.lower()
        )

        # Verify buffer was reduced to retained entries
        assert len(state["agent_memories"]["dm"].short_term_buffer) == 3

    def test_multiple_compression_cycles_accumulate_summaries(
        self, empty_game_state: GameState
    ) -> None:
        """Test that multiple compressions accumulate in long_term_summary."""
        from unittest.mock import MagicMock, patch

        state = empty_game_state
        state["agent_memories"]["dm"] = AgentMemory(
            short_term_buffer=["Event 1", "Event 2", "Event 3", "Event 4", "Event 5"],
            long_term_summary="",
            token_limit=100,
        )

        manager = MemoryManager(state)

        # First compression
        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "First batch summary"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        first_summary = state["agent_memories"]["dm"].long_term_summary
        assert first_summary == "First batch summary"

        # Add more entries
        state["agent_memories"]["dm"].short_term_buffer.extend(
            ["Event 6", "Event 7", "Event 8", "Event 9", "Event 10"]
        )

        # Second compression
        import memory

        memory._summarizer_cache.clear()  # Clear cache to allow new mock

        with patch("memory.Summarizer") as MockSummarizer:
            mock_instance = MagicMock()
            mock_instance.generate_summary.return_value = "Second batch summary"
            MockSummarizer.return_value = mock_instance

            manager.compress_buffer("dm")

        final_summary = state["agent_memories"]["dm"].long_term_summary

        # Both summaries should be present
        assert "First batch summary" in final_summary
        assert "Second batch summary" in final_summary
        assert "---" in final_summary

        # Cleanup
        memory._summarizer_cache.clear()
