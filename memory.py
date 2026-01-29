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
Story 5.2: Session Summary Generation - Summarizer and compression.
Story 5.3: In-Session Memory References - Buffer enables narrative callbacks.

In-Session Memory References (Story 5.3)
----------------------------------------
The short_term_buffer enables in-session callbacks and references by:

1. **Content Accumulation**: Each turn appends to the buffer with attribution
   (e.g., "[DM]: ...", "[Shadowmere]: ..."), preserving who said/did what.

2. **Context Building**: The get_context() method includes the last 10 buffer
   entries in the "Recent Events" section of agent prompts.

3. **Callback Capability**: LLMs naturally draw connections when given sufficient
   context. If an event from turn 5 (e.g., "mysterious symbol on the wall") is
   still in the buffer at turn 15, the LLM can reference it when a similar
   symbol appears ("This looks like that marking we saw earlier...").

4. **Chronological Order**: Buffer entries maintain insertion order (oldest first),
   allowing LLMs to understand event sequences for cause-effect relationships.

This architecture means callbacks "just work" when:
- Events are within the 10-entry context window (see DM_CONTEXT_RECENT_EVENTS_LIMIT
  and PC_CONTEXT_RECENT_EVENTS_LIMIT constants in agents.py)
- The DM/PC prompts encourage narrative continuity (see agents.py)
- LLMs recognize patterns in the provided context
"""

import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from agents import (
    DM_CONTEXT_PLAYER_ENTRIES_LIMIT,
    DM_CONTEXT_RECENT_EVENTS_LIMIT,
    PC_CONTEXT_RECENT_EVENTS_LIMIT,
    LLMError,
    categorize_error,
    format_character_facts,
    get_llm,
)
from config import get_config
from models import CharacterFacts, GameState

# Logger for error tracking (technical details logged internally)
logger = logging.getLogger("autodungeon")

__all__ = [
    "JANITOR_SYSTEM_PROMPT",
    "MemoryManager",
    "Summarizer",
    "estimate_tokens",
]

# Default number of entries to retain after compression
RETAIN_AFTER_COMPRESSION = 3

# Module-level cache for Summarizer instance to avoid re-creating LLM clients
_summarizer_cache: dict[tuple[str, str], "Summarizer"] = {}

# Janitor System Prompt for memory compression (Story 5.2, AC #2, #3)
JANITOR_SYSTEM_PROMPT = """You are a memory compression assistant for a D&D game.

Your task is to condense session events into a concise summary that preserves essential story information.

## PRESERVE (Include in summary):
- Character names and their relationships (allies, rivals, friends)
- Inventory changes (items gained, lost, or used)
- Quest goals and progress (accepted, completed, failed)
- Status effects and conditions (curses, blessings, injuries)
- Key plot points and discoveries
- Location changes and notable places visited
- NPC names and their significance

## DISCARD (Omit from summary):
- Verbatim dialogue (keep only the gist of important conversations)
- Detailed dice roll mechanics (e.g., "rolled 15 on d20")
- Repetitive environmental descriptions
- Combat blow-by-blow (summarize outcomes instead)
- Timestamps and turn markers

## FORMAT:
Write a concise narrative summary in third person past tense.
Use bullet points for lists of items or status effects.
Keep the summary under 500 words.
Focus on what would be important for the character to remember."""


class Summarizer:
    """Summarizer class for generating memory compression summaries.

    Uses the Janitor system prompt to compress game events into
    concise summaries that preserve essential narrative elements.

    Attributes:
        provider: LLM provider name (gemini, claude, ollama).
        model: Model name to use for summarization.
        _llm: The LangChain chat model instance (lazily initialized).
    """

    def __init__(self, provider: str, model: str) -> None:
        """Initialize Summarizer with LLM provider and model.

        The LLM client is lazily initialized on first use to allow
        instantiation in tests without requiring API keys.

        Args:
            provider: LLM provider name (gemini, claude, ollama).
            model: Model name to use for summarization.
        """
        self.provider = provider
        self.model = model
        self._llm: BaseChatModel | None = None

    def _get_llm(self) -> BaseChatModel:
        """Get or create the LLM client.

        Lazily initializes the LLM on first access.

        Returns:
            The LangChain chat model instance.
        """
        if self._llm is None:
            self._llm = get_llm(self.provider, self.model)
        return self._llm

    # Maximum characters to send to summarizer to prevent context overflow
    MAX_BUFFER_CHARS = 50_000  # ~12k tokens for most models

    def generate_summary(self, agent_name: str, buffer_entries: list[str]) -> str:
        """Generate a summary from buffer entries.

        Uses the Janitor system prompt to compress events into
        a concise summary preserving essential story information.

        Note: Buffer content comes from trusted sources (DM and PC agents)
        so prompt injection is not a concern here.

        Args:
            agent_name: Name of the agent whose memory is being compressed.
            buffer_entries: List of buffer entries to summarize.

        Returns:
            Generated summary string, or empty string if buffer is empty
            or on error.
        """
        if not buffer_entries:
            return ""

        # Build the prompt - truncate if too large to prevent context overflow
        buffer_text = "\n".join(buffer_entries)
        if len(buffer_text) > self.MAX_BUFFER_CHARS:
            logger.warning(
                "Buffer text truncated for summarization",
                extra={
                    "agent": agent_name,
                    "original_chars": len(buffer_text),
                    "truncated_to": self.MAX_BUFFER_CHARS,
                },
            )
            buffer_text = buffer_text[: self.MAX_BUFFER_CHARS]
        messages: list[BaseMessage] = [
            SystemMessage(content=JANITOR_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Please summarize these events for {agent_name}:\n\n{buffer_text}"
            ),
        ]

        try:
            # Invoke LLM synchronously (blocking per architecture)
            llm = self._get_llm()
            response = llm.invoke(messages)

            # Extract content from response - handle both str and list[str] cases
            content = response.content
            if isinstance(content, str):
                return content
            # LangChain may return list of content blocks (e.g., Claude)
            # Join string elements, skip non-string items (like tool use blocks)
            if hasattr(content, "__iter__"):
                text_parts = [part for part in content if isinstance(part, str)]
                return "".join(text_parts)
            # Fallback for unexpected types
            return str(content) if content else ""

        except Exception as e:
            # Categorize and log error, return empty string for graceful degradation
            error_type = categorize_error(e)
            llm_error = LLMError(
                provider=self.provider,
                agent=f"summarizer-{agent_name}",
                error_type=error_type,
                original_error=e,
            )
            logger.error(
                "Summarization failed",
                extra={
                    "provider": llm_error.provider,
                    "agent": llm_error.agent,
                    "error_type": llm_error.error_type,
                    "original_error": str(e),
                },
            )
            return ""


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

        The context includes recent buffer entries (up to 10) in a "Recent Events"
        section. This enables in-session memory references (Story 5.3) - LLMs can
        recognize patterns and make callbacks to earlier events when they see
        sufficient context (e.g., "This symbol looks like the one we saw in the
        cave earlier...").

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

        # Add CharacterFacts for all PC agents (Story 5.4)
        character_facts_parts: list[str] = []
        for name, memory in self._state["agent_memories"].items():
            if name == "dm":
                continue  # DM doesn't have character facts
            if memory.character_facts:
                character_facts_parts.append(
                    format_character_facts(memory.character_facts)
                )

        if character_facts_parts:
            context_parts.append(
                "## Party Members\n" + "\n\n".join(character_facts_parts)
            )

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
            # Add CharacterFacts first - who am I? (Story 5.4)
            if pc_memory.character_facts:
                context_parts.append(
                    f"## Character Identity\n{format_character_facts(pc_memory.character_facts)}"
                )

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

    def get_character_facts(self, agent_name: str) -> CharacterFacts | None:
        """Get an agent's CharacterFacts.

        Story 5.4: Cross-Session Memory & Character Facts.

        Args:
            agent_name: The agent to get character facts for.

        Returns:
            CharacterFacts if present, None otherwise.
        """
        memory = self._state["agent_memories"].get(agent_name)
        return memory.character_facts if memory else None

    def get_cross_session_summary(self, agent_name: str) -> str:
        """Get an agent's cross-session summary (alias for long_term_summary).

        Story 5.4: Cross-Session Memory & Character Facts.

        Args:
            agent_name: The agent to get summary for.

        Returns:
            Long-term summary string, or empty string if not found.
        """
        return self.get_long_term_summary(agent_name)

    def update_character_facts(
        self,
        agent_name: str,
        key_traits: list[str] | None = None,
        relationships: dict[str, str] | None = None,
        notable_events: list[str] | None = None,
    ) -> None:
        """Update an agent's CharacterFacts with new information.

        This method merges new information into existing CharacterFacts:
        - key_traits are appended to the existing list
        - relationships are merged (updates existing, adds new)
        - notable_events are appended to the existing list

        Story 5.4: Cross-Session Memory & Character Facts.

        WARNING: This modifies the state in-place. In LangGraph nodes, consider
        using immutable patterns with model_copy() instead.

        Args:
            agent_name: The agent to update facts for.
            key_traits: New traits to add (optional).
            relationships: New relationships to merge (optional).
            notable_events: New events to add (optional).
        """
        memory = self._state["agent_memories"].get(agent_name)
        if not memory or not memory.character_facts:
            return

        facts = memory.character_facts

        # Append new key traits
        if key_traits:
            for trait in key_traits:
                if trait not in facts.key_traits:
                    facts.key_traits.append(trait)

        # Merge relationships (update existing, add new)
        if relationships:
            facts.relationships.update(relationships)

        # Append new notable events
        if notable_events:
            for event in notable_events:
                if event not in facts.notable_events:
                    facts.notable_events.append(event)

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

    def compress_buffer(
        self, agent_name: str, retain_count: int = RETAIN_AFTER_COMPRESSION
    ) -> str:
        """Compress buffer entries into long_term_summary.

        Gets buffer entries for the agent, generates a summary using the
        Summarizer, updates the agent's long_term_summary field, and
        clears compressed entries while retaining the most recent ones.

        WARNING: This modifies the state in-place. For LangGraph nodes,
        use the immutable version that returns an updated state copy.

        Args:
            agent_name: The agent whose buffer to compress.
            retain_count: Number of recent entries to keep in buffer (default 3).

        Returns:
            Generated summary string, or empty string if nothing to compress
            or on error.
        """
        memory = self._state["agent_memories"].get(agent_name)
        if not memory:
            return ""

        buffer = memory.short_term_buffer
        if not buffer:
            return ""

        # Skip if not enough entries to compress
        if len(buffer) <= retain_count:
            return ""

        # Get entries to compress (all but the most recent)
        entries_to_compress = buffer[:-retain_count]
        entries_to_keep = buffer[-retain_count:]

        if not entries_to_compress:
            return ""

        # Get summarizer configuration from config (cached for efficiency)
        config = get_config()
        cache_key = (config.agents.summarizer.provider, config.agents.summarizer.model)
        if cache_key not in _summarizer_cache:
            _summarizer_cache[cache_key] = Summarizer(
                provider=config.agents.summarizer.provider,
                model=config.agents.summarizer.model,
            )
        summarizer = _summarizer_cache[cache_key]

        # Generate summary
        summary = summarizer.generate_summary(agent_name, entries_to_compress)

        if not summary:
            # Summarization failed, don't modify state
            return ""

        # Merge with existing summary
        new_summary = _merge_summaries(memory.long_term_summary, summary)

        # Update memory state in-place (for non-LangGraph contexts)
        memory.long_term_summary = new_summary
        memory.short_term_buffer.clear()
        memory.short_term_buffer.extend(entries_to_keep)

        return summary


def _merge_summaries(existing: str, new_summary: str) -> str:
    """Merge new summary with existing long-term summary.

    Args:
        existing: The existing long_term_summary content.
        new_summary: The newly generated summary to append.

    Returns:
        Merged summary string.
    """
    if not existing:
        return new_summary
    # Append new summary as continuation with separator
    return f"{existing}\n\n---\n\n{new_summary}"
