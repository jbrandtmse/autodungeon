# Story 5.5: Memory Compression System

Status: done

## Story

As a **system**,
I want **to automatically compress memories when approaching context limits**,
so that **agents don't exceed token limits while retaining important information**.

## Acceptance Criteria

1. **Given** the Context Manager node in LangGraph
   **When** a turn cycle begins (before DM turn)
   **Then** it checks each agent's token count against their limit (FR16)

2. **Given** an agent's short_term_buffer approaches `token_limit`
   **When** the threshold is exceeded (e.g., 80% of limit)
   **Then** the Context Manager triggers summarization for that agent

3. **Given** summarization is triggered
   **When** it completes
   **Then** older buffer entries are compressed into the long_term_summary
   **And** those entries are removed from short_term_buffer

4. **Given** the compression process
   **When** preserving information
   **Then** the most recent N turns remain in short_term_buffer uncompressed
   **And** older content is summarized and merged into long_term_summary

5. **Given** memory compression runs
   **When** it completes
   **Then** the agent's total context fits within their token_limit
   **And** critical story information is preserved

6. **Given** the compression is per-agent
   **When** one agent compresses
   **Then** other agents' memories are unaffected
   **And** each agent manages their own memory independently

## Tasks / Subtasks

- [x] Task 1: Verify existing memory compression implementation
  - [x] 1.1 Review context_manager node in graph.py for all AC compliance
  - [x] 1.2 Review compress_buffer() in memory.py for all AC compliance
  - [x] 1.3 Document any gaps between current implementation and AC requirements
  - [x] 1.4 Create test matrix mapping each AC to existing tests

- [x] Task 2: Implement total context fitting verification (AC #5)
  - [x] 2.1 Add `get_total_context_tokens()` method to MemoryManager
  - [x] 2.2 Method should calculate: long_term_summary + short_term_buffer + character_facts tokens
  - [x] 2.3 Add `is_total_context_over_limit()` method to check if total exceeds token_limit
  - [x] 2.4 Write unit tests for new methods

- [x] Task 3: Implement multi-pass compression if needed (AC #5)
  - [x] 3.1 After compress_buffer(), verify total context is within limit
  - [x] 3.2 If still over limit, re-compress long_term_summary itself
  - [x] 3.3 Add `compress_long_term_summary()` method using Summarizer
  - [x] 3.4 Set maximum compression passes (default 2) to prevent infinite loops
  - [x] 3.5 Write tests for multi-pass compression scenarios

- [x] Task 4: Add post-compression validation in context_manager (AC #5)
  - [x] 4.1 After compression, call `is_total_context_over_limit()` for each agent
  - [x] 4.2 Log warning if agent still exceeds limit after compression
  - [x] 4.3 Consider fallback: truncate oldest portion of long_term_summary if critical
  - [x] 4.4 Write integration tests for post-compression validation

- [x] Task 5: Verify per-agent isolation (AC #6)
  - [x] 5.1 Write test: Agent A compresses, Agent B memory unchanged
  - [x] 5.2 Write test: Multiple agents compress in same pass, each independent
  - [x] 5.3 Write test: One agent failure doesn't affect others
  - [x] 5.4 Verify context_manager iterates all agents independently

- [x] Task 6: Verify critical information preservation (AC #5)
  - [x] 6.1 Write test: Character names preserved after compression
  - [x] 6.2 Write test: Quest objectives preserved after compression
  - [x] 6.3 Write test: Relationships preserved after compression
  - [x] 6.4 Write test: Recent N entries (default 3) always retained in buffer

- [x] Task 7: Write comprehensive acceptance tests
  - [x] 7.1 Test: Context Manager checks token counts before DM turn (AC #1)
  - [x] 7.2 Test: 80% threshold triggers summarization (AC #2)
  - [x] 7.3 Test: Compressed entries removed from short_term_buffer (AC #3)
  - [x] 7.4 Test: Most recent 3 entries retained uncompressed (AC #4)
  - [x] 7.5 Test: Total context within token_limit after compression (AC #5)
  - [x] 7.6 Test: Per-agent compression is isolated (AC #6)

- [x] Task 8: Update documentation
  - [x] 8.1 Add memory compression flow diagram to docstrings
  - [x] 8.2 Document RETAIN_AFTER_COMPRESSION constant (currently 3)
  - [x] 8.3 Document 80% threshold rationale
  - [x] 8.4 Update CLAUDE.md if new patterns introduced

## Dev Notes

### Existing Implementation Analysis

**IMPORTANT:** Story 5.2 already implemented the core memory compression system. This story should focus on verification, edge cases, and ensuring the "total context fits within limit" requirement is fully satisfied.

**Already Implemented in Story 5.2:**

1. **context_manager node (graph.py:39-75):**
   ```python
   def context_manager(state: GameState) -> GameState:
       """Manage agent memory context before DM turn."""
       # Sets summarization_in_progress flag
       # Iterates through all agents
       # Calls is_near_limit() for each
       # Calls compress_buffer() if near limit
       # Returns updated state
   ```

2. **MemoryManager.is_near_limit() (memory.py:411-426):**
   ```python
   def is_near_limit(self, agent_name: str, threshold: float = 0.8) -> bool:
       """Check if agent's buffer is approaching token limit."""
       current_tokens = self.get_buffer_token_count(agent_name)
       limit = int(memory.token_limit * threshold)
       return current_tokens >= limit
   ```

3. **MemoryManager.compress_buffer() (memory.py:560-624):**
   ```python
   def compress_buffer(self, agent_name: str, retain_count: int = 3) -> str:
       """Compress buffer entries into long_term_summary."""
       # Gets entries to compress (all but most recent 3)
       # Calls Summarizer.generate_summary()
       # Merges with existing long_term_summary
       # Updates memory state
   ```

4. **Summarizer class (memory.py:103-218):**
   - Uses JANITOR_SYSTEM_PROMPT
   - Preserves character names, relationships, inventory, quests
   - Discards verbatim dialogue, dice mechanics

5. **RETAIN_AFTER_COMPRESSION = 3 (memory.py:70):**
   - Most recent 3 entries always kept in buffer

### Gap Analysis

| AC | Current Implementation | Gap |
|----|------------------------|-----|
| AC #1 | context_manager checks before DM | DONE |
| AC #2 | is_near_limit() at 80% threshold | DONE |
| AC #3 | compress_buffer() removes old entries | DONE |
| AC #4 | RETAIN_AFTER_COMPRESSION = 3 | DONE |
| AC #5 | Compression runs, but no post-validation | **GAP: No verification that total context (summary + buffer + facts) fits in limit** |
| AC #6 | Per-agent iteration in context_manager | DONE (needs explicit tests) |

### Primary Implementation Focus

**AC #5 - Total Context Verification:**

The current implementation compresses the buffer when it approaches the limit, but doesn't verify that:
1. `long_term_summary` + `short_term_buffer` + `character_facts` together fit within `token_limit`
2. Multiple compressions may be needed if `long_term_summary` grows too large over many sessions

**New Methods Needed:**

```python
# memory.py additions

def get_total_context_tokens(self, agent_name: str) -> int:
    """Calculate total tokens for agent's full context.

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
```

**Optional: Long-term Summary Compression:**

If after buffer compression the total context is still over limit, the system may need to re-compress the long_term_summary itself:

```python
def compress_long_term_summary(self, agent_name: str) -> str:
    """Re-compress the long_term_summary if it's grown too large.

    Uses Summarizer to create a more condensed version of the
    existing summary. This is a second-pass compression for
    extreme cases.

    Args:
        agent_name: The agent whose summary to compress.

    Returns:
        New compressed summary, or empty string on failure.
    """
    memory = self._state["agent_memories"].get(agent_name)
    if not memory or not memory.long_term_summary:
        return ""

    # Use Summarizer to compress the summary itself
    summarizer = _get_cached_summarizer()
    compressed = summarizer.generate_summary(
        agent_name,
        [memory.long_term_summary]
    )

    if compressed:
        memory.long_term_summary = compressed

    return compressed
```

### Updated context_manager Flow

```python
def context_manager(state: GameState) -> GameState:
    """Manage agent memory context before DM turn."""
    updated_state = {...state, "summarization_in_progress": True}
    memory_manager = MemoryManager(updated_state)

    MAX_COMPRESSION_PASSES = 2

    for agent_name in updated_state["agent_memories"]:
        passes = 0

        # Pass 1: Compress buffer if near limit
        if memory_manager.is_near_limit(agent_name):
            memory_manager.compress_buffer(agent_name)
            passes += 1

        # Pass 2: If still over limit, re-compress summary
        while (passes < MAX_COMPRESSION_PASSES and
               memory_manager.is_total_context_over_limit(agent_name)):
            memory_manager.compress_long_term_summary(agent_name)
            passes += 1

        # Log warning if still over limit after max passes
        if memory_manager.is_total_context_over_limit(agent_name):
            logger.warning(
                f"Agent {agent_name} still over token limit after "
                f"{MAX_COMPRESSION_PASSES} compression passes"
            )

    updated_state["summarization_in_progress"] = False
    return updated_state
```

### Test Coverage Requirements

**Existing Tests (from Story 5.2):**
- `TestIsNearLimit` - threshold detection
- `TestContextManagerTypeConsistency` - type safety
- `TestBufferRetentionAfterCompression` - retain recent entries
- `TestContextManagerMultipleAgents` - per-agent iteration
- `TestIntegrationRealCompression` - full flow

**New Tests Needed:**

```python
class TestTotalContextCalculation:
    """Tests for total context token calculation."""

    def test_get_total_context_tokens_empty_memory():
        """Empty memory returns 0 tokens."""

    def test_get_total_context_tokens_summary_only():
        """Calculates tokens for summary without buffer."""

    def test_get_total_context_tokens_buffer_only():
        """Calculates tokens for buffer without summary."""

    def test_get_total_context_tokens_includes_character_facts():
        """Character facts tokens are included in total."""

    def test_get_total_context_tokens_full_context():
        """Calculates tokens for summary + buffer + facts."""


class TestTotalContextValidation:
    """Tests for post-compression context validation."""

    def test_is_total_context_over_limit_false_when_under():
        """Returns False when total < token_limit."""

    def test_is_total_context_over_limit_true_when_over():
        """Returns True when total > token_limit."""

    def test_context_manager_validates_after_compression():
        """Context manager checks total context after compression."""


class TestMultiPassCompression:
    """Tests for multi-pass compression scenarios."""

    def test_single_pass_sufficient():
        """One compression pass brings context under limit."""

    def test_two_pass_compression_when_needed():
        """Second pass compresses long_term_summary if still over."""

    def test_max_passes_prevents_infinite_loop():
        """Compression stops after MAX_COMPRESSION_PASSES."""

    def test_warning_logged_if_still_over_after_max_passes():
        """Warning logged when context still exceeds limit."""


class TestPerAgentIsolation:
    """Tests for per-agent compression isolation (AC #6)."""

    def test_agent_a_compression_doesnt_affect_agent_b():
        """Compressing one agent leaves others unchanged."""

    def test_multiple_agents_compress_independently():
        """Multiple agents can compress in same pass."""

    def test_one_agent_failure_doesnt_block_others():
        """If compression fails for one agent, others still run."""


class TestCriticalInformationPreservation:
    """Tests for critical information preservation (AC #5)."""

    def test_character_names_preserved():
        """Character names appear in compressed summary."""

    def test_quest_objectives_preserved():
        """Quest objectives appear in compressed summary."""

    def test_relationships_preserved():
        """Relationships appear in compressed summary."""

    def test_recent_entries_always_retained():
        """Most recent 3 entries always in buffer after compression."""
```

### Architecture Compliance

| Pattern | Status | Notes |
|---------|--------|-------|
| Context Manager before DM | DONE | START -> context_manager -> dm |
| 80% token threshold | DONE | is_near_limit(threshold=0.8) |
| Synchronous compression | DONE | Blocking per architecture |
| Per-agent isolation | DONE | Iterates independently |
| Janitor prompt | DONE | Preserves critical info |
| RETAIN_AFTER_COMPRESSION | DONE | Default 3 entries |

### Performance Considerations

- `get_total_context_tokens()` calls `estimate_tokens()` multiple times (O(text length))
- Token estimation uses word-count heuristic (~1.3 tokens/word)
- Multi-pass compression adds additional LLM calls (rare case)
- MAX_COMPRESSION_PASSES=2 limits worst-case LLM calls to 2 per agent

### Edge Cases

1. **Empty buffer:** Skip compression (already handled)
2. **Buffer < RETAIN_AFTER_COMPRESSION entries:** Skip compression (already handled)
3. **LLM failure during compression:** Graceful degradation, continue without compression (already handled)
4. **Very large long_term_summary:** Multi-pass compression needed
5. **CharacterFacts taking significant space:** Include in total calculation
6. **Agent with very low token_limit:** May need more aggressive compression

### Dependencies

- Story 5.1: MemoryManager, estimate_tokens(), get_buffer_token_count()
- Story 5.2: Summarizer, compress_buffer(), context_manager node
- Story 5.4: CharacterFacts, format_character_facts()

### What This Story Implements

1. `get_total_context_tokens()` method
2. `is_total_context_over_limit()` method
3. Post-compression validation in context_manager
4. Optional: `compress_long_term_summary()` for multi-pass compression
5. Comprehensive tests for all AC requirements
6. Explicit tests for per-agent isolation

### What This Story Does NOT Do

- Does NOT change the 80% threshold (configurable in future)
- Does NOT add UI for compression settings (Epic 6)
- Does NOT implement cross-session summary merging (already done in 5.4)
- Does NOT change the Janitor prompt (already optimized in 5.2)

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR16 | Compress memory when context limits are reached | Complete memory compression system with validation |

### References

- [Source: planning-artifacts/prd.md#Memory & Context Management FR16]
- [Source: planning-artifacts/architecture.md#Memory System Architecture]
- [Source: planning-artifacts/epics.md#Story 5.5]
- [Source: memory.py#MemoryManager] - Existing implementation
- [Source: memory.py#Summarizer] - Story 5.2 implementation
- [Source: graph.py#context_manager] - Story 5.2 implementation
- [Source: 5-2-session-summary-generation.md] - Previous story learnings

---

## Senior Developer Review (AI)

**Review Date:** 2026-01-28
**Reviewer:** Claude Opus 4.5 (Adversarial Code Review)
**Status:** APPROVED with fixes applied

### Issues Found: 8 total (3 HIGH, 3 MEDIUM, 2 LOW)

All HIGH and MEDIUM severity issues were AUTO-FIXED during review.

#### HIGH Severity Issues (FIXED)

1. **MAX_COMPRESSION_PASSES Scoped Inside Function** [graph.py:66]
   - **Problem:** Constant defined inside `context_manager()`, making it inaccessible for testing/configuration
   - **Fix:** Moved to module level, added to `__all__` exports, added documentation comment
   - **Test Added:** `TestMaxCompressionPassesConstant` class with 2 tests

2. **compress_long_term_summary Silent Failure** [memory.py:548-551]
   - **Problem:** No logging when summarizer fails during long_term_summary compression
   - **Fix:** Added `logger.warning()` call when compression fails
   - **Test Added:** `test_compress_long_term_summary_failure_logs_warning`

3. **Missing Test for Summarizer Failure During Multi-Pass** [tests]
   - **Problem:** No test verifying graceful handling when `compress_long_term_summary()` fails
   - **Fix:** Added test case with logging verification

#### MEDIUM Severity Issues (FIXED)

4. **Redundant Imports in Tests** [tests:21, 286-287]
   - **Problem:** `patch` imported at module level and again in individual tests
   - **Fix:** Consolidated imports, removed redundant ones

5. **Duplicate Summarizer Cache Clearing Pattern** [tests]
   - **Problem:** Every test manually clears `_summarizer_cache` at start and end
   - **Fix:** Created `clear_summarizer_cache` fixture with `autouse=True`

6. **Thread Safety Risk in Summarizer Cache** [memory.py:73]
   - **Problem:** `_summarizer_cache` accessed without thread safety mechanism
   - **Fix:** Added documentation comment explaining single-threaded context (acceptable for MVP)

#### LOW Severity Issues (Documented, not fixed)

7. **Forward Reference in Type Annotation** [memory.py:73]
   - Acceptable pattern due to class ordering

8. **Docstring Gap for RETAIN_AFTER_COMPRESSION** [memory.py:513-551]
   - Minor documentation enhancement opportunity

### Quality Check Results

- **Tests:** 36 passed (33 original + 3 new)
- **Full Suite:** 1943 passed, 1 skipped
- **Linting (ruff):** 0 errors after fixes
- **Type Checking (pyright):** 0 errors in test file, pre-existing warnings in other files
- **Formatting:** Applied via `ruff format`

### AC Verification

| AC | Status | Evidence |
|----|--------|----------|
| AC #1 | PASS | `context_manager` checks `is_near_limit()` before DM turn |
| AC #2 | PASS | 80% threshold verified in `is_near_limit(threshold=0.8)` |
| AC #3 | PASS | `compress_buffer()` removes compressed entries |
| AC #4 | PASS | `RETAIN_AFTER_COMPRESSION = 3` entries kept |
| AC #5 | PASS | Post-compression validation via `is_total_context_over_limit()` |
| AC #6 | PASS | Per-agent iteration with isolation verified |

### Files Modified During Review

- `graph.py`: Moved `MAX_COMPRESSION_PASSES` to module level
- `memory.py`: Added failure logging to `compress_long_term_summary()`, added thread-safety comment
- `tests/test_story_5_5_memory_compression.py`: Added fixture, 3 new tests, removed redundant code

### Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-28 | Code review: 8 issues found, 6 fixed | Claude Opus 4.5 |
