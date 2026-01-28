"""MemoryManager and summarization logic.

This module provides the MemoryManager class for managing agent memory
and context building with proper isolation rules:
- PC agents only see their own AgentMemory (strict isolation)
- DM agent has read access to ALL agent memories (asymmetric access)

The MemoryManager provides a clean interface for:
- Building prompt-ready context strings via get_context()
- Tracking buffer sizes relative to token limits
- Managing memory operations (add, get)

Story 5.1: Short-Term Context Buffer implementation.
"""

from agents import (
    DM_CONTEXT_PLAYER_ENTRIES_LIMIT,
    DM_CONTEXT_RECENT_EVENTS_LIMIT,
    PC_CONTEXT_RECENT_EVENTS_LIMIT,
)
from models import GameState

__all__ = [
    "MemoryManager",
    "estimate_tokens",
]


def estimate_tokens(text: str) -> int:
    """Estimate token count using word-based heuristic.

    Uses a simple approximation: ~1.3 tokens per word for English text.
    This is faster than calling a tokenizer and accurate enough for
    buffer management decisions.

    NOTE: This heuristic is calibrated for English/Latin-script text where
    words are space-delimited. For CJK (Chinese, Japanese, Korean) or other
    non-space-delimited languages, this will significantly underestimate.
    Consider using a proper tokenizer (like tiktoken) for multilingual support.

    Args:
        text: Text to estimate tokens for.

    Returns:
        Estimated token count. Returns character-based estimate for
        non-space-delimited text (detected by low word count).
    """
    if not text:
        return 0
    # Split on whitespace, count words
    word_count = len(text.split())

    # If text has very few words but many characters, it's likely CJK or similar
    # Use character-based estimate instead (~0.5 tokens per character for CJK)
    # Threshold: fewer than 2 words and at least 20 chars suggests non-English
    char_count = len(text)
    if word_count < 2 and char_count > 20:
        # Likely non-space-delimited text, use character estimate
        return int(char_count * 0.5)

    # Standard English heuristic: ~1.3 tokens per word
    return int(word_count * 1.3)


class MemoryManager:
    """Manages agent memory and context building.

    Encapsulates the memory isolation rules:
    - PC agents only see their own AgentMemory (strict isolation)
    - DM agent has read access to ALL agent memories (asymmetric access)

    This class provides a clean interface for:
    - Building prompt-ready context strings
    - Tracking buffer sizes relative to token limits
    - Managing memory operations

    Attributes:
        _state: Reference to the current GameState.
    """

    def __init__(self, state: GameState) -> None:
        """Initialize MemoryManager with game state.

        Args:
            state: Current game state containing agent_memories.
        """
        self._state = state

    def get_context(self, agent_name: str) -> str:
        """Get prompt-ready context string for an agent.

        Respects memory isolation rules:
        - DM: Returns context with all agent memories (asymmetric access)
        - PC: Returns context with only that PC's memory (strict isolation)

        Args:
            agent_name: The agent to build context for (e.g., "dm", "rogue").

        Returns:
            Formatted markdown string suitable for inclusion in agent prompt.
            Returns empty string if agent has no memory or doesn't exist.
        """
        if agent_name == "dm":
            return self._build_dm_context()
        return self._build_pc_context(agent_name)

    def _build_dm_context(self) -> str:
        """Build context for DM with access to all agent memories.

        The DM has asymmetric memory access - can read ALL agent memories
        to enable dramatic irony and maintain narrative coherence.

        Returns:
            Formatted markdown context string with all relevant memory info.
        """
        context_parts: list[str] = []

        # Add DM's own long-term summary if available
        dm_memory = self._state["agent_memories"].get("dm")
        if dm_memory:
            if dm_memory.long_term_summary:
                context_parts.append(f"## Story So Far\n{dm_memory.long_term_summary}")
            # Add recent events from DM's short-term buffer
            if dm_memory.short_term_buffer:
                recent_events = "\n".join(
                    dm_memory.short_term_buffer[-DM_CONTEXT_RECENT_EVENTS_LIMIT:]
                )
                context_parts.append(f"## Recent Events\n{recent_events}")

        # DM reads ALL agent memories (asymmetric access per architecture)
        agent_knowledge: list[str] = []
        for name, memory in self._state["agent_memories"].items():
            if name == "dm":
                continue  # Already handled above
            if memory.short_term_buffer:
                recent = memory.short_term_buffer[-DM_CONTEXT_PLAYER_ENTRIES_LIMIT:]
                agent_knowledge.append(f"[{name} knows]: {'; '.join(recent)}")

        if agent_knowledge:
            context_parts.append("## Player Knowledge\n" + "\n".join(agent_knowledge))

        return "\n\n".join(context_parts)

    def _build_pc_context(self, agent_name: str) -> str:
        """Build context for PC with only their own memory.

        PC agents have strict memory isolation - they can ONLY see their own
        AgentMemory. This is the opposite of the DM's asymmetric access.

        Args:
            agent_name: The name of the PC agent (lowercase).

        Returns:
            Formatted markdown context string with only this PC's memory.
            Returns empty string if agent has no memory or doesn't exist.
        """
        context_parts: list[str] = []

        # PC agents ONLY access their own memory - strict isolation
        pc_memory = self._state["agent_memories"].get(agent_name)
        if pc_memory:
            # Add long-term summary if available
            if pc_memory.long_term_summary:
                context_parts.append(
                    f"## What You Remember\n{pc_memory.long_term_summary}"
                )

            # Add recent events from short-term buffer
            if pc_memory.short_term_buffer:
                recent = "\n".join(
                    pc_memory.short_term_buffer[-PC_CONTEXT_RECENT_EVENTS_LIMIT:]
                )
                context_parts.append(f"## Recent Events\n{recent}")

        return "\n\n".join(context_parts)

    def get_buffer_token_count(self, agent_name: str) -> int:
        """Get estimated token count of an agent's short_term_buffer.

        Args:
            agent_name: The agent to check.

        Returns:
            Estimated token count, or 0 if agent not found.
        """
        memory = self._state["agent_memories"].get(agent_name)
        if not memory or not memory.short_term_buffer:
            return 0
        buffer_text = "\n".join(memory.short_term_buffer)
        return estimate_tokens(buffer_text)

    def is_near_limit(self, agent_name: str, threshold: float = 0.8) -> bool:
        """Check if agent's buffer is approaching token limit.

        Args:
            agent_name: The agent to check.
            threshold: Fraction of token_limit to trigger (default 0.8 = 80%).

        Returns:
            True if buffer tokens >= threshold * token_limit.
        """
        memory = self._state["agent_memories"].get(agent_name)
        if not memory:
            return False
        current_tokens = self.get_buffer_token_count(agent_name)
        limit = int(memory.token_limit * threshold)
        return current_tokens >= limit

    def get_long_term_summary(self, agent_name: str) -> str:
        """Get an agent's long-term summary.

        Args:
            agent_name: The agent to get summary for.

        Returns:
            Long-term summary string, or empty string if not found.
        """
        memory = self._state["agent_memories"].get(agent_name)
        return memory.long_term_summary if memory else ""

    def get_buffer_entries(self, agent_name: str, limit: int = 10) -> list[str]:
        """Get recent entries from an agent's buffer.

        Args:
            agent_name: The agent to get entries for.
            limit: Maximum number of entries to return (most recent).

        Returns:
            List of buffer entries (oldest first, newest last within the limit),
            or empty list if not found.
        """
        memory = self._state["agent_memories"].get(agent_name)
        if not memory or not memory.short_term_buffer:
            return []
        return memory.short_term_buffer[-limit:]

    def add_to_buffer(self, agent_name: str, content: str | None) -> None:
        """Add content to an agent's short-term buffer.

        WARNING: This modifies the state in-place. DO NOT use in LangGraph nodes!
        In LangGraph nodes, use the immutable pattern with model_copy() instead:

            new_buffer = memory.short_term_buffer.copy()
            new_buffer.append(content)
            new_memory = memory.model_copy(update={"short_term_buffer": new_buffer})

        This method is intended for testing and non-LangGraph contexts only.

        Args:
            agent_name: The agent to add content to.
            content: The content to append to the buffer. Must not be None.

        Raises:
            TypeError: If content is None.
            ValueError: If content exceeds 100KB (memory protection).
        """
        if content is None:
            raise TypeError("content must not be None")
        if len(content) > 100_000:  # 100KB limit for memory protection
            raise ValueError(
                f"content exceeds maximum size (100KB): got {len(content)} chars"
            )
        memory = self._state["agent_memories"].get(agent_name)
        if memory:
            memory.short_term_buffer.append(content)
