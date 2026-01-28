# Story 5.2: Session Summary Generation

Status: complete

## Code Review

**Reviewer:** Claude Opus 4.5
**Review Date:** 2026-01-28
**Review Type:** Adversarial code review per BMAD workflow

### Issues Found and Fixed

#### Issue 1 (HIGH): Type safety issues in context_manager - dict/GameState mismatch
- **Location:** `graph.py:57-73`
- **Problem:** The `context_manager` function was using dict operations that caused pyright errors due to type mismatch with GameState TypedDict
- **Fix:** Changed from `dict(state)` to proper TypedDict spread `{**state, "summarization_in_progress": True}`
- **Status:** FIXED

#### Issue 2 (HIGH): LLM response content type handling is unsafe
- **Location:** `memory.py:144-145`
- **Problem:** The `response.content` from LangChain can be `str | list[str | dict]`. Original code could return stringified list instead of joined text
- **Fix:** Added proper handling for list content blocks (common with Claude), joining string elements and skipping non-string items
- **Status:** FIXED

#### Issue 3 (HIGH): `summarization_in_progress` field missing from GameState TypedDict
- **Location:** `models.py:382-418`
- **Problem:** Field was used in `context_manager()` and `app.py` but not defined in GameState TypedDict
- **Fix:** Added `summarization_in_progress: bool` to GameState and updated `create_initial_game_state()` and `populate_game_state()` factory functions
- **Status:** FIXED

#### Issue 4 (MEDIUM): Summarizer creates new instance on every compress_buffer call
- **Location:** `memory.py:446-450`
- **Problem:** Every `compress_buffer()` call created new Summarizer and LLM client, causing inefficiency and potential connection pooling issues
- **Fix:** Added module-level `_summarizer_cache` dict that caches Summarizer instances by (provider, model) tuple
- **Status:** FIXED

#### Issue 5 (MEDIUM): No validation of buffer content before sending to LLM
- **Location:** `memory.py:129-136`
- **Problem:** Buffer content was directly concatenated and sent to LLM without size validation, risking context overflow
- **Fix:** Added `MAX_BUFFER_CHARS = 50_000` constant with truncation and warning logging when exceeded
- **Status:** FIXED

#### Issue 6 (MEDIUM): Missing test coverage for error recovery paths
- **Location:** `tests/test_memory.py`
- **Problem:** Tests for summarization failure only checked empty string return, not state preservation or specific error types
- **Fix:** Added comprehensive tests for rate limit errors, LLM exceptions, list content responses, cache behavior, and large buffer truncation
- **Status:** FIXED - Added `TestSummarizerErrorRecovery` and `TestContextManagerTypeConsistency` test classes

### Issues Documented (LOW - No Fix Required)

#### Issue 7 (LOW): No rate limiting or timeout protection for LLM calls
- **Location:** `memory.py:138-166`
- **Problem:** The summarizer LLM call has no explicit timeout
- **Analysis:** This follows the existing pattern in `agents.py` where LLM timeouts are handled at the LangChain client level. Adding explicit timeouts would require changes across the codebase and is out of scope for this story
- **Recommendation:** Consider adding configurable timeouts in a future story

#### Issue 8 (LOW): Pre-existing pyright warnings for LangGraph/datetime types
- **Location:** `graph.py` (various), `models.py:16`
- **Problem:** LangGraph type stubs are incomplete, and `datetime.UTC` has pyright compatibility issues
- **Analysis:** These are pre-existing issues not introduced by this story
- **Status:** DOCUMENTED - Not a blocker

### Test Results After Fixes

```
============================= 234 passed in 9.08s =============================
```

(Full test suite: 1680 passed, 1 skipped)

### Quality Checks After Fixes

- **ruff check:** All checks passed
- **ruff format:** All files formatted
- **pyright:** 8 errors, 13 warnings (all pre-existing library type issues, not new regressions)

### Files Modified

1. `graph.py` - Fixed context_manager type handling
2. `memory.py` - Added response content handling, caching, truncation
3. `models.py` - Added `summarization_in_progress` field to GameState
4. `tests/test_memory.py` - Added error recovery tests and cache clearing fixture

## Story

As a **system**,
I want **to generate summaries of session events for long-term memory**,
so that **important story beats persist beyond the short-term buffer**.

## Acceptance Criteria

1. **Given** a session has progressed through multiple turns
   **When** the Context Manager triggers summarization
   **Then** a summary is generated capturing key events (FR12)

2. **Given** the summarizer uses a dedicated LLM (configurable via FR44)
   **When** generating summaries
   **Then** it uses the "Janitor" prompt that preserves:
   - Character names and relationships
   - Inventory and equipment changes
   - Quest goals and progress
   - Status effects and conditions

3. **Given** the "Janitor" summarizer
   **When** compressing content
   **Then** it discards:
   - Verbatim dialogue (keeps gist)
   - Detailed dice mechanics
   - Repetitive descriptions

4. **Given** a summary is generated
   **When** stored in AgentMemory
   **Then** it updates the `long_term_summary` field
   **And** the summary is serialized with checkpoints

5. **Given** the summary generation
   **When** complete
   **Then** it runs synchronously (blocking) as per Architecture decision
   **And** the UI shows a brief indicator if it takes time

## Tasks / Subtasks

- [x] Task 1: Create summarizer infrastructure in memory.py
  - [x] 1.1 Create `Summarizer` class with `__init__(provider: str, model: str)`
  - [x] 1.2 Implement `get_summarizer_llm()` factory function using `get_llm()` from agents.py
  - [x] 1.3 Add type hints and docstrings following project patterns
  - [x] 1.4 Write unit tests for Summarizer instantiation

- [x] Task 2: Implement "Janitor" system prompt (AC: #2, #3)
  - [x] 2.1 Create `JANITOR_SYSTEM_PROMPT` constant with preservation rules
  - [x] 2.2 Include instructions to preserve: names, relationships, inventory, quests, status effects
  - [x] 2.3 Include instructions to discard: verbatim dialogue, dice mechanics, repetitive descriptions
  - [x] 2.4 Format prompt for clear structured output (markdown sections)
  - [x] 2.5 Write tests validating prompt structure and content

- [x] Task 3: Implement summary generation method (AC: #1, #4)
  - [x] 3.1 Add `generate_summary(agent_name: str, buffer_entries: list[str]) -> str` method
  - [x] 3.2 Build prompt with Janitor system message and buffer content
  - [x] 3.3 Invoke LLM synchronously (blocking per architecture)
  - [x] 3.4 Handle LLM errors with categorization (reuse from agents.py)
  - [x] 3.5 Return generated summary text
  - [x] 3.6 Write tests with mocked LLM responses

- [x] Task 4: Add MemoryManager.compress_buffer() method (AC: #1, #4)
  - [x] 4.1 Implement `compress_buffer(agent_name: str) -> str` method
  - [x] 4.2 Get buffer entries for agent using existing `get_buffer_entries()`
  - [x] 4.3 Call Summarizer.generate_summary() with buffer content
  - [x] 4.4 Update agent's `long_term_summary` field (merge with existing)
  - [x] 4.5 Clear compressed entries from `short_term_buffer`
  - [x] 4.6 Retain most recent N entries in buffer (configurable, default 3)
  - [x] 4.7 Write tests for buffer compression flow
  - [x] 4.8 Write tests for summary merging with existing long_term_summary

- [x] Task 5: Implement context_manager node in graph.py (AC: #1)
  - [x] 5.1 Create `context_manager(state: GameState) -> GameState` node function
  - [x] 5.2 Iterate through all agents in `agent_memories`
  - [x] 5.3 Check `MemoryManager.is_near_limit(agent_name)` for each agent
  - [x] 5.4 If near limit, call `compress_buffer()` for that agent
  - [x] 5.5 Return updated state with compressed memories
  - [x] 5.6 Write tests for context_manager triggering compression

- [x] Task 6: Integrate context_manager into game workflow (AC: #1)
  - [x] 6.1 Add `context_manager` node to workflow in `create_game_workflow()`
  - [x] 6.2 Add edge from START to context_manager (runs before DM)
  - [x] 6.3 Add edge from context_manager to DM
  - [x] 6.4 Update routing map if needed
  - [x] 6.5 Write integration tests for full workflow with compression

- [x] Task 7: Add UI indicator for summarization (AC: #5)
  - [x] 7.1 Add session_state flag `summarization_in_progress` in app.py
  - [x] 7.2 Display brief indicator (text or spinner) when flag is True
  - [x] 7.3 Ensure indicator uses campfire theme styling
  - [x] 7.4 Test indicator appears during long-running summarization

- [x] Task 8: Make summarizer configurable via FR44
  - [x] 8.1 Verify `GameConfig.summarizer_model` field exists in models.py
  - [x] 8.2 Verify `AgentsConfig.summarizer` in config.py provides provider/model
  - [x] 8.3 Wire summarizer to use config values from GameState or AppConfig
  - [x] 8.4 Write tests for config-driven summarizer model selection

- [x] Task 9: Write comprehensive acceptance tests
  - [x] 9.1 Test: Summarization triggered when buffer approaches limit
  - [x] 9.2 Test: Summary preserves character names and relationships
  - [x] 9.3 Test: Summary discards verbatim dialogue (keeps gist)
  - [x] 9.4 Test: Summary stored in long_term_summary field
  - [x] 9.5 Test: Summary serialized with checkpoint
  - [x] 9.6 Test: Summarization runs synchronously (blocks)
  - [x] 9.7 Test: Multiple agents can be compressed in same context_manager pass

## Dev Notes

### Existing Infrastructure Analysis

**MemoryManager (memory.py) - Story 5.1:**
```python
class MemoryManager:
    def is_near_limit(self, agent_name: str, threshold: float = 0.8) -> bool:
        """Check if agent's buffer is approaching token limit."""
        memory = self._state["agent_memories"].get(agent_name)
        if not memory:
            return False
        current_tokens = self.get_buffer_token_count(agent_name)
        limit = int(memory.token_limit * threshold)
        return current_tokens >= limit
```

This method already exists and triggers at 80% capacity. Story 5.2 needs to call this in context_manager and invoke summarization.

**AgentMemory (models.py):**
```python
class AgentMemory(BaseModel):
    long_term_summary: str = Field(default="", description="Compressed history from the summarizer")
    short_term_buffer: list[str] = Field(default_factory=list, description="Recent turns, newest at the end")
    token_limit: int = Field(default=8000, ge=1, description="Maximum tokens for this agent's context")
```

The `long_term_summary` field is ready for use.

**get_llm Factory (agents.py):**
```python
def get_llm(provider: str, model: str) -> BaseChatModel:
    """Create an LLM client for the specified provider and model."""
    # Supports gemini, claude, ollama
```

Reuse this factory for creating the summarizer LLM.

**Summarizer Config (config.py):**
```python
class AgentsConfig(BaseSettings):
    dm: AgentConfig = Field(default_factory=AgentConfig)
    summarizer: AgentConfig = Field(
        default_factory=lambda: AgentConfig(token_limit=4000)
    )
```

The summarizer configuration already exists with default settings.

**GameConfig (models.py):**
```python
class GameConfig(BaseModel):
    summarizer_model: str = Field(default="gemini-1.5-flash", description="Model for memory compression")
```

Already has summarizer_model field for FR44 compliance.

### Architecture Compliance

Per architecture.md:

| Decision | Status | Notes |
|----------|--------|-------|
| Context Manager node | TODO | Runs once per cycle before DM turn |
| Token-based threshold | DONE | is_near_limit() at 80% |
| Synchronous execution | TODO | Blocking per architecture |
| "Janitor" prompt | TODO | Preserve names/inventory/quests, discard dialogue/dice |
| long_term_summary field | DONE | Already exists in AgentMemory |

**Memory System Architecture (architecture.md):**
> Context Manager node runs once per cycle (before DM turn)
> Checks token count for each agent's short_term_buffer
> If threshold exceeded, invokes summarizer_model synchronously
> Updates long_term_summary, clears compressed messages from buffer

**Summarizer Prompt (architecture.md):**
> Uses the "Janitor" system prompt from original vision - preserves names, inventory, quest goals, status effects; discards verbatim dialogue, dice mechanics, repetitive descriptions.

### Janitor System Prompt Design

```python
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
```

### Workflow Integration

Current workflow (graph.py):
```
START -> dm_turn -> [pc_turns...] -> END
```

After Story 5.2:
```
START -> context_manager -> dm_turn -> [pc_turns...] -> END
```

The context_manager node:
1. Runs before DM turn (once per round)
2. Checks each agent's buffer against token limit
3. If any agent is near limit, triggers summarization
4. Returns updated state with compressed memories
5. DM turn then proceeds with cleaned-up memory

### Error Handling

Reuse error handling patterns from Story 4.5:
- Wrap LLM calls in try/except
- Categorize errors using `categorize_error()`
- Create LLMError with provider/agent/error_type
- Log internally, never expose to users
- If summarization fails, continue without compression (graceful degradation)

### Summary Merging Strategy

When compressing buffer with existing long_term_summary:
```python
def merge_summaries(existing: str, new_summary: str) -> str:
    """Merge new summary with existing long-term summary."""
    if not existing:
        return new_summary
    # Append new summary as continuation
    return f"{existing}\n\n---\n\n{new_summary}"
```

Alternatively, could re-summarize both together for more coherent result (at cost of additional LLM call).

### Buffer Retention

When compressing, retain most recent entries:
```python
RETAIN_AFTER_COMPRESSION = 3  # Keep last 3 entries in buffer

def compress_buffer(self, agent_name: str) -> str:
    """Compress buffer and update long_term_summary."""
    memory = self._state["agent_memories"].get(agent_name)
    if not memory:
        return ""

    # Get all but most recent entries for compression
    entries_to_compress = memory.short_term_buffer[:-RETAIN_AFTER_COMPRESSION]
    entries_to_keep = memory.short_term_buffer[-RETAIN_AFTER_COMPRESSION:]

    if not entries_to_compress:
        return ""  # Nothing to compress

    # Generate summary
    summary = self.summarizer.generate_summary(agent_name, entries_to_compress)

    # Merge with existing summary
    new_summary = merge_summaries(memory.long_term_summary, summary)

    # Update memory (immutably for LangGraph)
    # ... return updated state
```

### UI Indicator

Simple indicator in app.py:
```python
if st.session_state.get("summarization_in_progress"):
    st.info("Compressing memories...")
```

Set flag before compression, clear after. Indicator uses campfire theme (amber color).

### Testing Strategy

Organize tests in `tests/test_memory.py` (extend existing):

```python
class TestSummarizer:
    """Tests for Summarizer class."""

class TestJanitorPrompt:
    """Tests for Janitor system prompt content."""

class TestCompressBuffer:
    """Tests for MemoryManager.compress_buffer()."""

class TestContextManagerNode:
    """Tests for context_manager workflow node."""

class TestSummaryMerging:
    """Tests for merging new summaries with existing."""

class TestStory52AcceptanceCriteria:
    """Acceptance tests for all Story 5.2 criteria."""
```

**Key Test Cases:**

```python
def test_summarization_triggered_at_threshold():
    """Test context_manager triggers compression at 80% limit."""

def test_janitor_preserves_character_names():
    """Test summary includes character names."""

def test_janitor_discards_dice_mechanics():
    """Test summary omits dice roll details."""

def test_summary_stored_in_long_term_summary():
    """Test compressed content ends up in long_term_summary field."""

def test_buffer_entries_cleared_after_compression():
    """Test short_term_buffer is reduced after compression."""

def test_recent_entries_retained_after_compression():
    """Test most recent N entries remain in buffer."""

def test_summarization_runs_synchronously():
    """Test compression blocks until complete."""
```

### What This Story Implements

1. `Summarizer` class with LLM integration
2. `JANITOR_SYSTEM_PROMPT` constant
3. `generate_summary()` method
4. `MemoryManager.compress_buffer()` method
5. `context_manager` node in graph.py
6. Workflow integration (context_manager -> dm_turn)
7. UI indicator for summarization
8. Configuration integration (FR44)

### What This Story Does NOT Do

- Does NOT implement in-session memory references (Story 5.3)
- Does NOT implement cross-session memory (Story 5.4)
- Does NOT implement full memory compression system (Story 5.5 - handles multiple passes)
- Does NOT add UI configuration for summarizer model (Epic 6)

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR12 | Generate session summaries for long-term memory | Summarizer + compress_buffer() |
| FR44 | Configurable summarization model | GameConfig.summarizer_model + AgentsConfig.summarizer |

[Source: epics.md#Story 5.2, prd.md#Memory & Context Management, architecture.md#Memory System Architecture]

### Performance Considerations

- Summarization is O(1) LLM calls per agent per compression trigger
- context_manager runs once per round (before DM)
- Synchronous blocking is acceptable per architecture (up to 2 min timeout)
- Token estimation is already implemented in Story 5.1

### Security Considerations

- LLM responses are sanitized (content comes from our prompts)
- No file system access during summarization
- API key handling reuses existing secure patterns from agents.py

### Edge Cases

1. **Empty buffer:** Don't trigger compression, return empty summary
2. **Very short buffer:** If fewer than RETAIN_AFTER_COMPRESSION entries, skip compression
3. **LLM failure:** Log error, continue without compression (graceful degradation)
4. **Multiple agents at limit:** Compress each independently in same pass
5. **Existing long_term_summary:** Merge appropriately, don't overwrite
6. **Unicode/special characters:** Handle in summary generation

### Previous Story Intelligence (from Story 5.1)

**Key Learnings:**
- Token estimation with word-based heuristic (1.3 tokens/word)
- CJK text fallback for non-space-delimited languages
- is_near_limit() already implemented with 80% threshold
- MemoryManager provides clean abstraction layer

**Patterns to Follow:**
- Wrap LLM calls in try/except with error categorization
- Use immutable state patterns for LangGraph compatibility
- Add comprehensive docstrings and type hints
- Organize tests by functional area

### References

- [Source: planning-artifacts/prd.md#Memory & Context Management FR12, FR44]
- [Source: planning-artifacts/architecture.md#Memory System Architecture]
- [Source: planning-artifacts/epics.md#Story 5.2]
- [Source: memory.py#MemoryManager] - Story 5.1 implementation
- [Source: agents.py#get_llm] - LLM factory function
- [Source: agents.py#LLMError] - Error handling patterns
- [Source: config.py#AgentsConfig] - Summarizer configuration
- [Source: models.py#AgentMemory] - long_term_summary field
- [Source: models.py#GameConfig] - summarizer_model field
