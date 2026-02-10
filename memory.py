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

import json
import logging
import re
from typing import TypedDict

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
from models import (
    CallbackEntry,
    CallbackLog,
    CharacterFacts,
    GameState,
    NarrativeElement,
    NarrativeElementStore,
    create_callback_entry,
    create_narrative_element,
)


class ExtractionResult(TypedDict):
    """Return type for extract_narrative_elements.

    Story 11.2: Typed return for both session and campaign stores.
    Story 11.4: Callback detection log.
    """

    narrative_elements: dict[str, NarrativeElementStore]
    callback_database: NarrativeElementStore
    callback_log: CallbackLog  # Story 11.4

# Logger for error tracking (technical details logged internally)
logger = logging.getLogger("autodungeon")

__all__ = [
    "CALLBACK_MATCH_CONTEXT_LENGTH",
    "CALLBACK_NAME_MIN_LENGTH",
    "ELEMENT_EXTRACTION_PROMPT",
    "JANITOR_SYSTEM_PROMPT",
    "MemoryManager",
    "NarrativeElementExtractor",
    "Summarizer",
    "detect_callbacks",
    "estimate_tokens",
    "extract_narrative_elements",
]

# Default number of entries to retain after compression
RETAIN_AFTER_COMPRESSION = 3

# Module-level cache for Summarizer instance to avoid re-creating LLM clients
# NOTE: This cache is not thread-safe. Streamlit runs single-threaded by design,
# so this is acceptable for MVP. If async/multi-threaded compression is needed,
# consider using threading.Lock or functools.lru_cache.
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
    # Must be large enough to fit the biggest agent buffer at compression time
    # plus the existing summary. At DM token_limit=32K, buffer can reach ~26K
    # tokens (~104K chars) plus summary (~20K chars) = ~124K chars.
    MAX_BUFFER_CHARS = 250_000  # ~62k tokens - 2x headroom for largest agent

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

            # Extract content from response - handle str, list[str], and
            # list[dict] formats (Gemini returns [{'type':'text','text':'...'}])
            content = response.content
            if isinstance(content, str):
                return content
            if hasattr(content, "__iter__"):
                text_parts: list[str] = []
                for part in content:
                    if isinstance(part, str):
                        text_parts.append(part)
                    elif isinstance(part, dict) and "text" in part:
                        text_parts.append(part["text"])
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

    def get_total_context_tokens(self, agent_name: str) -> int:
        """Calculate total tokens for agent's full context.

        Story 5.5: Memory Compression System (FR16, AC #5).

        Includes:
        - long_term_summary tokens
        - short_term_buffer tokens (all entries)
        - character_facts tokens (if present)

        Args:
            agent_name: The agent to calculate for.

        Returns:
            Estimated total token count for the agent's context.
        """
        memory = self._state["agent_memories"].get(agent_name)
        if not memory:
            return 0

        total = 0

        # Long-term summary
        if memory.long_term_summary:
            total += estimate_tokens(memory.long_term_summary)

        # Short-term buffer
        if memory.short_term_buffer:
            buffer_text = "\n".join(memory.short_term_buffer)
            total += estimate_tokens(buffer_text)

        # Character facts (Story 5.4)
        if memory.character_facts:
            facts_text = format_character_facts(memory.character_facts)
            total += estimate_tokens(facts_text)

        return total

    def is_total_context_over_limit(self, agent_name: str) -> bool:
        """Check if agent's total context exceeds their token limit.

        Story 5.5: Memory Compression System (FR16, AC #5).

        This method is used for post-compression validation to ensure
        the agent's total context fits within their token_limit.

        Args:
            agent_name: The agent to check.

        Returns:
            True if total context > token_limit.
        """
        memory = self._state["agent_memories"].get(agent_name)
        if not memory:
            return False

        total_tokens = self.get_total_context_tokens(agent_name)
        return total_tokens > memory.token_limit

    def compress_long_term_summary(self, agent_name: str) -> str:
        """Re-compress the long_term_summary if it's grown too large.

        Story 5.5: Memory Compression System (FR16, AC #5).

        Uses Summarizer to create a more condensed version of the
        existing summary. This is a second-pass compression for
        extreme cases where buffer compression alone is insufficient.

        Args:
            agent_name: The agent whose summary to compress.

        Returns:
            New compressed summary, or empty string on failure.
        """
        memory = self._state["agent_memories"].get(agent_name)
        if not memory or not memory.long_term_summary:
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

        # Use Summarizer to compress the summary itself
        compressed = summarizer.generate_summary(
            agent_name,
            [memory.long_term_summary],
        )

        if compressed:
            memory.long_term_summary = compressed
        else:
            # Log warning when summarization fails (graceful degradation)
            logger.warning(
                "Long-term summary compression failed for agent %s, summary unchanged",
                agent_name,
            )

        return compressed

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


# =============================================================================
# Callback Detection (Story 11.4)
# =============================================================================

CALLBACK_NAME_MIN_LENGTH = 3  # Skip very short names to avoid false positives
CALLBACK_MATCH_CONTEXT_LENGTH = 200  # Max chars for match context excerpt

# Stop words to exclude from fuzzy name matching (common short words in NPC titles)
_FUZZY_NAME_STOP_WORDS = frozenset({"the", "and", "for", "but", "not", "was", "are"})

# Common English/D&D stop words to exclude from description keyword matching
_DESCRIPTION_STOP_WORDS = frozenset({
    "the", "and", "that", "with", "from", "they", "their", "this",
    "have", "been", "were", "will", "into", "when", "then", "about",
    "some", "what", "more", "also", "very", "just", "like", "only",
    "back", "over", "such", "after", "each", "most", "much", "could",
    "would", "should", "which", "there", "where", "other", "than",
    "them", "these", "those", "your", "said", "says", "here",
    "does", "doing", "done", "being", "make", "made",
    "party", "character", "player",  # D&D generic terms
})


def _normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    # Replace punctuation with spaces (preserves word boundaries)
    text = re.sub(r"[^\w\s]", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_match_context(
    raw_content: str, match_position: int, max_length: int = CALLBACK_MATCH_CONTEXT_LENGTH
) -> str:
    """Extract surrounding context around a match position.

    Args:
        raw_content: The full turn content.
        match_position: Character position of the match in raw_content.
        max_length: Maximum characters for the context excerpt.

    Returns:
        Context string with ellipsis if truncated.
    """
    half = max_length // 2
    start = max(0, match_position - half)
    end = min(len(raw_content), match_position + half)

    context = raw_content[start:end]
    if start > 0:
        context = "..." + context
    if end < len(raw_content):
        context = context + "..."

    return context


def _detect_name_match(
    element: NarrativeElement,
    normalized_content: str,
    raw_content: str,
) -> tuple[str, str] | None:
    """Detect if element name appears in turn content.

    Tries exact match first, then fuzzy (distinctive word) match.

    Args:
        element: NarrativeElement to check for.
        normalized_content: Lowercased, punctuation-stripped turn content.
        raw_content: Original turn content for context extraction.

    Returns:
        (match_type, match_context) tuple, or None if no match.
    """
    name = element.name
    if len(name) < CALLBACK_NAME_MIN_LENGTH:
        return None

    normalized_name = _normalize_text(name)

    # Exact match: full name appears in content (word-boundary aware)
    exact_pattern = r"\b" + re.escape(normalized_name) + r"\b"
    exact_match = re.search(exact_pattern, normalized_content)
    if exact_match:
        # Find position in raw content for context extraction
        pos = raw_content.lower().find(name.lower())
        if pos == -1:
            pos = 0
        context = _extract_match_context(raw_content, pos)
        return ("name_exact", context)

    # Fuzzy match: longest distinctive word (>= 3 chars) appears as standalone word
    words = normalized_name.split()
    if len(words) > 1:
        # Sort by length descending, take the longest as most distinctive
        # Exclude common words that would cause false positives
        distinctive_words = sorted(
            [
                w for w in words
                if len(w) >= CALLBACK_NAME_MIN_LENGTH and w not in _FUZZY_NAME_STOP_WORDS
            ],
            key=len,
            reverse=True,
        )
        for word in distinctive_words:
            # Word boundary matching to avoid substring false positives
            pattern = r"\b" + re.escape(word) + r"\b"
            match = re.search(pattern, normalized_content)
            if match:
                # Find position in raw content for accurate context extraction
                raw_match = re.search(
                    r"\b" + re.escape(word) + r"\b", raw_content, re.IGNORECASE
                )
                pos = raw_match.start() if raw_match else 0
                context = _extract_match_context(raw_content, pos)
                return ("name_fuzzy", context)

    return None


def _detect_description_match(
    element: NarrativeElement,
    normalized_content: str,
    raw_content: str,
) -> tuple[str, str] | None:
    """Detect if element description keywords appear in turn content.

    Extracts significant keywords from description and checks if
    2+ appear in the turn content.

    Args:
        element: NarrativeElement to check for.
        normalized_content: Lowercased, punctuation-stripped turn content.
        raw_content: Original turn content for context extraction.

    Returns:
        ("description_keyword", match_context) tuple, or None if no match.
    """
    if not element.description:
        return None

    # Extract significant keywords (>= 4 chars, not stop words, deduplicated)
    desc_words = _normalize_text(element.description).split()
    keywords = list(dict.fromkeys(
        w for w in desc_words
        if len(w) >= 4 and w not in _DESCRIPTION_STOP_WORDS
    ))

    if len(keywords) < 2:
        return None  # Not enough unique keywords to match against

    # Check how many keywords appear in content
    matched_keywords: list[str] = []
    first_raw_match_pos = -1
    for keyword in keywords:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        match = re.search(pattern, normalized_content)
        if match:
            matched_keywords.append(keyword)
            if first_raw_match_pos == -1:
                # Find position in raw content for accurate context extraction
                raw_match = re.search(
                    r"\b" + re.escape(keyword) + r"\b", raw_content, re.IGNORECASE
                )
                first_raw_match_pos = raw_match.start() if raw_match else 0

    # Require 2+ unique keyword matches for confidence
    if len(matched_keywords) >= 2:
        context = _extract_match_context(raw_content, max(0, first_raw_match_pos))
        return ("description_keyword", context)

    return None


def detect_callbacks(
    turn_content: str,
    turn_number: int,
    session_number: int,
    callback_database: NarrativeElementStore,
) -> list[CallbackEntry]:
    """Detect callbacks in turn content against stored narrative elements.

    Scans turn content for references to previously-stored elements using
    name matching and description keyword matching.

    Story 11.4: Callback Detection.
    FR79: System can detect when callbacks occur.

    Args:
        turn_content: The text content of the turn to analyze.
        turn_number: Current turn number.
        session_number: Current session number.
        callback_database: Campaign-level NarrativeElementStore to match against.

    Returns:
        List of detected CallbackEntry objects. Empty list on failure.
    """
    if not turn_content or not turn_content.strip():
        return []

    try:
        active_elements = callback_database.get_active()
        if not active_elements:
            return []

        normalized = _normalize_text(turn_content)
        detected: list[CallbackEntry] = []
        matched_element_ids: set[str] = set()  # Prevent duplicate detections

        for element in active_elements:
            # Skip self-references (element introduced this turn)
            if element.turn_introduced == turn_number:
                continue

            # Skip if already referenced this turn (avoid double-count from extraction)
            if turn_number in element.turns_referenced:
                continue

            # Skip if already matched (one match per element per turn)
            if element.id in matched_element_ids:
                continue

            # Try name match first (higher confidence)
            match_result = _detect_name_match(element, normalized, turn_content)
            if match_result is None:
                # Try description keyword match
                match_result = _detect_description_match(element, normalized, turn_content)

            if match_result is not None:
                match_type_str, match_context = match_result
                entry = create_callback_entry(
                    element=element,
                    turn_detected=turn_number,
                    match_type=match_type_str,  # type: ignore[arg-type]
                    match_context=match_context,
                    session_detected=session_number,
                )
                detected.append(entry)
                matched_element_ids.add(element.id)

                # Log story moments at INFO level
                if entry.is_story_moment:
                    logger.info(
                        "Story moment detected: %s referenced after %d turns!",
                        element.name,
                        entry.turn_gap,
                    )

        return detected

    except Exception as e:
        logger.warning("Callback detection failed: %s", e)
        return []


# =============================================================================
# Narrative Element Extraction (Story 11.1)
# =============================================================================

# Module-level cache for NarrativeElementExtractor instances
# Keyed by (provider, model) tuple, matching _summarizer_cache pattern.
_extractor_cache: dict[tuple[str, str], "NarrativeElementExtractor"] = {}

# Type aliases for normalizing LLM-returned element types to valid Literal values.
# LLMs often return "npc" instead of "character", "place" instead of "location", etc.
_ELEMENT_TYPE_ALIASES: dict[str, str] = {
    "npc": "character",
    "person": "character",
    "creature": "character",
    "monster": "character",
    "place": "location",
    "area": "location",
    "region": "location",
    "object": "item",
    "weapon": "item",
    "artifact": "item",
    "deal": "promise",
    "agreement": "promise",
    "commitment": "promise",
    "oath": "promise",
    "danger": "threat",
    "warning": "threat",
    "discovery": "event",
    "plot": "event",
    "quest": "event",
}
_VALID_ELEMENT_TYPES = frozenset(
    {"character", "item", "location", "event", "promise", "threat"}
)

# Extraction prompt for LLM to identify narrative elements from turn content
ELEMENT_EXTRACTION_PROMPT = """You are a narrative analysis assistant for a D&D game.

Your task is to extract significant narrative elements from the following game turn content.

## Extract These Element Types:
- **character**: Named NPCs introduced or significantly featured (not PCs)
- **item**: Notable items mentioned, especially unique or magical ones
- **location**: Named or described locations
- **event**: Significant plot events or discoveries
- **promise**: Promises, deals, or commitments made
- **threat**: Threats, warnings, or dangers introduced

## Rules:
- Only extract genuinely significant elements (not every noun)
- Focus on elements that could be referenced or called back to later
- Include context about why the element matters
- List characters involved (PC names)
- Suggest potential callbacks: ways the element could be referenced or used later
- Return an empty array if no significant elements are found

## Response Format:
Return ONLY a JSON array:
```json
[
  {
    "type": "character",
    "name": "Skrix the Goblin",
    "context": "Befriended by party, promised to share info about the caves",
    "characters_involved": ["Shadowmere", "Aldric"],
    "potential_callbacks": ["Could return as ally in cave exploration", "Might betray party for goblin tribe"]
  }
]
```

Return ONLY the JSON array, no additional text."""


def _parse_extraction_response(
    response_text: str, turn_number: int, session_number: int
) -> list[NarrativeElement]:
    """Parse JSON array of narrative elements from LLM response.

    Handles common LLM response quirks:
    - JSON wrapped in markdown code blocks
    - Leading/trailing whitespace
    - Extra text before/after JSON
    - Mixed valid and invalid elements (valid kept, invalid skipped)

    Args:
        response_text: Raw text from LLM response.
        turn_number: Turn number for element attribution.
        session_number: Session number for element attribution.

    Returns:
        List of validated NarrativeElement objects.
        Returns empty list on parse failure (graceful degradation).
    """
    if not response_text or not response_text.strip():
        return []

    # Strip markdown code blocks (same pattern as agents.py _parse_module_json)
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Find JSON array in response
    start_idx = text.find("[")
    end_idx = text.rfind("]")
    if start_idx == -1 or end_idx == -1:
        return []

    # Parse JSON
    try:
        data = json.loads(text[start_idx : end_idx + 1])
    except json.JSONDecodeError:
        logger.warning("Failed to parse narrative extraction JSON response")
        return []

    if not isinstance(data, list):
        return []

    # Validate and convert to NarrativeElement objects
    elements: list[NarrativeElement] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            # Normalize element_type: map aliases and default to "event"
            raw_type = str(item.get("type", "event")).lower().strip()
            element_type = _ELEMENT_TYPE_ALIASES.get(raw_type, raw_type)
            if element_type not in _VALID_ELEMENT_TYPES:
                element_type = "event"

            # Validate characters_involved is a list of strings
            raw_involved = item.get("characters_involved", [])
            if isinstance(raw_involved, list):
                characters_involved = [str(c) for c in raw_involved if c]
            elif isinstance(raw_involved, str):
                # LLM returned a single string instead of list
                characters_involved = [raw_involved] if raw_involved else []
            else:
                characters_involved = []

            # Extract potential_callbacks (Story 11.2)
            raw_callbacks = item.get("potential_callbacks", [])
            if isinstance(raw_callbacks, list):
                potential_callbacks = [str(cb) for cb in raw_callbacks if cb]
            elif isinstance(raw_callbacks, str):
                potential_callbacks = [raw_callbacks] if raw_callbacks else []
            else:
                potential_callbacks = []

            element = create_narrative_element(
                element_type=element_type,  # type: ignore[arg-type]
                name=str(item.get("name", "")),
                description=str(item.get("context", item.get("description", ""))),
                turn_introduced=turn_number,
                session_introduced=session_number,
                characters_involved=characters_involved,
                potential_callbacks=potential_callbacks,
            )
            elements.append(element)
        except Exception as e:
            logger.warning("Skipping invalid narrative element: %s", e)

    return elements


class NarrativeElementExtractor:
    """Extracts narrative elements from turn content using LLM.

    Uses a lightweight (fast) model to extract significant narrative
    elements without slowing down gameplay.

    Story 11.1: Narrative Element Extraction.

    Attributes:
        provider: LLM provider name (gemini, claude, ollama).
        model: Model name to use for extraction.
        _llm: The LangChain chat model instance (lazily initialized).
    """

    MAX_CONTENT_CHARS = 10_000  # Max chars for extraction input

    def __init__(self, provider: str, model: str) -> None:
        """Initialize NarrativeElementExtractor with LLM provider and model.

        The LLM client is lazily initialized on first use to allow
        instantiation in tests without requiring API keys.

        Args:
            provider: LLM provider name (gemini, claude, ollama).
            model: Model name to use for extraction.
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

    def extract_elements(
        self, turn_content: str, turn_number: int, session_id: str
    ) -> list[NarrativeElement]:
        """Extract narrative elements from turn content.

        Invokes the LLM with the extraction prompt and turn content,
        then parses the response into NarrativeElement objects.

        Args:
            turn_content: The text content of the turn to analyze.
            turn_number: Turn number for element attribution.
            session_id: Session ID for session number extraction.

        Returns:
            List of NarrativeElement objects. Empty list on failure
            (graceful degradation - never raises).
        """
        if not turn_content or not turn_content.strip():
            return []

        # Truncate content if too large
        content = turn_content
        if len(content) > self.MAX_CONTENT_CHARS:
            logger.warning(
                "Extraction content truncated from %d to %d chars",
                len(content),
                self.MAX_CONTENT_CHARS,
            )
            content = content[: self.MAX_CONTENT_CHARS]

        # Extract session number from session_id
        try:
            session_number = int(session_id)
        except (ValueError, TypeError):
            session_number = 1

        try:
            llm = self._get_llm()
            messages: list[BaseMessage] = [
                SystemMessage(content=ELEMENT_EXTRACTION_PROMPT),
                HumanMessage(
                    content=f"Extract narrative elements from this turn:\n\n{content}"
                ),
            ]
            response = llm.invoke(messages)

            # Extract text from response - handle str, list[str], and
            # list[dict] formats (Gemini returns [{'type':'text','text':'...'}])
            response_content = response.content
            if isinstance(response_content, str):
                response_text = response_content
            elif hasattr(response_content, "__iter__"):
                text_parts: list[str] = []
                for part in response_content:
                    if isinstance(part, str):
                        text_parts.append(part)
                    elif isinstance(part, dict) and "text" in part:
                        text_parts.append(part["text"])
                response_text = "".join(text_parts)
            else:
                response_text = str(response_content) if response_content else ""

            return _parse_extraction_response(
                response_text, turn_number, session_number
            )

        except Exception as e:
            # Graceful degradation: log and return empty list
            error_type = categorize_error(e)
            llm_error = LLMError(
                provider=self.provider,
                agent="extractor",
                error_type=error_type,
                original_error=e,
            )
            logger.warning(
                "Narrative element extraction failed",
                extra={
                    "provider": llm_error.provider,
                    "agent": llm_error.agent,
                    "error_type": llm_error.error_type,
                    "original_error": str(e),
                },
            )
            return []


def extract_narrative_elements(
    state: GameState, turn_content: str, turn_number: int
) -> ExtractionResult:
    """Extract narrative elements and merge into both session store and campaign database.

    Gets extractor config from AppConfig, extracts elements from the
    turn content, and merges them into the state's NarrativeElementStore
    and the campaign-level callback_database.

    Story 11.1: Basic extraction and session store.
    Story 11.2: Campaign-level callback database integration.
    Story 11.4: Callback detection integration.

    Args:
        state: Current game state.
        turn_content: The text content of the turn to analyze.
        turn_number: Turn number for element attribution.

    Returns:
        ExtractionResult with:
        - "narrative_elements": Updated per-session dict
        - "callback_database": Updated campaign-level store
        - "callback_log": Updated callback log with detected callbacks
    """
    config = get_config()

    # Use extractor config (defaults to summarizer settings for lightweight extraction)
    provider = config.agents.extractor.provider
    model = config.agents.extractor.model

    # Get or create cached extractor instance
    cache_key = (provider, model)
    if cache_key not in _extractor_cache:
        _extractor_cache[cache_key] = NarrativeElementExtractor(
            provider=provider,
            model=model,
        )
    extractor = _extractor_cache[cache_key]

    # Get session ID from state
    session_id = state.get("session_id", "001")

    # Extract elements
    new_elements = extractor.extract_elements(turn_content, turn_number, session_id)

    # Merge into existing narrative elements store
    narrative_elements = dict(state.get("narrative_elements", {}))

    if session_id not in narrative_elements:
        narrative_elements[session_id] = NarrativeElementStore()

    store = narrative_elements[session_id]
    # Create new store with merged elements
    merged_elements = list(store.elements) + new_elements
    narrative_elements[session_id] = NarrativeElementStore(elements=merged_elements)

    # Also merge into campaign-level callback database (Story 11.2)
    callback_db = state.get("callback_database", NarrativeElementStore())
    # Create a copy to avoid mutating state
    callback_db_copy = NarrativeElementStore(
        elements=[e.model_copy() for e in callback_db.elements]
    )
    for element in new_elements:
        callback_db_copy.add_element(element.model_copy())

    # Update dormancy
    callback_db_copy.update_dormancy(turn_number)

    # Detect callbacks in turn content (Story 11.4)
    try:
        session_number = int(session_id)
    except (ValueError, TypeError):
        session_number = 1

    try:
        detected_callbacks = detect_callbacks(
            turn_content, turn_number, session_number, callback_db_copy
        )

        # Record references for detected callbacks in callback_database
        for cb_entry in detected_callbacks:
            callback_db_copy.record_reference(cb_entry.element_id, turn_number)
    except Exception as e:
        logger.warning("Callback detection in extraction pipeline failed: %s", e)
        detected_callbacks = []

    # Merge into callback log
    existing_log = state.get("callback_log", CallbackLog())
    new_log = CallbackLog(entries=list(existing_log.entries))
    for cb_entry in detected_callbacks:
        new_log.add_entry(cb_entry)

    return {
        "narrative_elements": narrative_elements,
        "callback_database": callback_db_copy,
        "callback_log": new_log,
    }
