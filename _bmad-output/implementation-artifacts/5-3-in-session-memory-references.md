# Story 5.3: In-Session Memory References

Status: done

## Story

As a **user watching the game**,
I want **agents to reference events from earlier in the current session**,
so that **the story feels connected and coherent**.

## Acceptance Criteria

1. **Given** an event occurred 10 turns ago in the current session
   **When** it's relevant to the current situation
   **Then** an agent may reference it naturally in their response (FR13)

2. **Given** the DM described a mysterious symbol in turn 5
   **When** a similar symbol appears in turn 25
   **Then** a PC agent might say "This looks like that marking we saw in the cave earlier..."

3. **Given** the short_term_buffer contains relevant context
   **When** an agent generates a response
   **Then** the LLM can draw connections and make callbacks

4. **Given** callback behavior
   **When** it occurs naturally
   **Then** it creates "aha moments" that delight users (UX: Memory is Magic)

5. **Given** in-session references
   **When** they occur
   **Then** they demonstrate narrative coherence without explicit prompting

## Tasks / Subtasks

- [x] Task 1: Verify existing memory mechanics enable in-session references
  - [x] 1.1 Review `short_term_buffer` content flow (turns added in agents.py dm_turn/pc_turn)
  - [x] 1.2 Verify buffer content is included in agent prompts via `_build_dm_context()` and `_build_pc_context()`
  - [x] 1.3 Confirm DM receives recent events from buffer (last 10 entries)
  - [x] 1.4 Confirm PC agents receive their own recent events (last 10 entries)
  - [x] 1.5 Document verification findings in completion notes

- [x] Task 2: Review and enhance DM system prompt for narrative callbacks (AC: #1, #2)
  - [x] 2.1 Verify DM_SYSTEM_PROMPT includes "Narrative Continuity" section
  - [x] 2.2 Verify prompt mentions referencing earlier events and plot threads
  - [x] 2.3 Verify prompt encourages callbacks to earlier details
  - [x] 2.4 Assess if any prompt enhancements would improve callback frequency
  - [x] 2.5 If enhancement needed: update DM_SYSTEM_PROMPT with stronger callback guidance
  - [x] 2.6 Document prompt analysis in completion notes

- [x] Task 3: Review and enhance PC system prompt for character memory (AC: #3, #4)
  - [x] 3.1 Review PC_SYSTEM_PROMPT_TEMPLATE for memory-related guidance
  - [x] 3.2 Assess if prompts encourage characters to reference past events
  - [x] 3.3 If enhancement needed: add guidance for characters to make callbacks naturally
  - [x] 3.4 Consider adding "Remember your recent experiences" guidance
  - [x] 3.5 Document prompt analysis and any changes in completion notes

- [x] Task 4: Write tests demonstrating in-session memory reference capability (AC: #1-5)
  - [x] 4.1 Create test fixture with multi-turn session history containing referenceable events
  - [x] 4.2 Test: DM context includes relevant historical events from buffer
  - [x] 4.3 Test: PC context includes relevant historical events from own buffer
  - [x] 4.4 Test: Buffer entries maintain chronological order for coherent reference
  - [x] 4.5 Test: Events from 10+ turns ago remain accessible in buffer (within token limits)
  - [x] 4.6 Test: Context formatting allows LLM to identify and reference specific past events

- [x] Task 5: Write integration tests with mocked LLM for callback behavior
  - [x] 5.1 Create test scenario: DM describes symbol, later similar symbol appears
  - [x] 5.2 Mock LLM to return response that references earlier event
  - [x] 5.3 Verify response format is correct (appears in ground_truth_log)
  - [x] 5.4 Test demonstrates that buffer context enables callback generation

- [x] Task 6: Add acceptance tests for Story 5.3 criteria
  - [x] 6.1 Test: Agent context contains events from multiple turns ago
  - [x] 6.2 Test: Context format allows for natural event referencing
  - [x] 6.3 Test: Buffer correctly preserves event details for reference
  - [x] 6.4 Test: DM has access to all agents' recent events for weaving plot threads
  - [x] 6.5 Test: PC isolation still maintained (only references own experiences)

- [x] Task 7: Document in-session memory reference behavior
  - [x] 7.1 Add docstrings explaining how buffer enables callbacks
  - [x] 7.2 Document the expected callback behavior in code comments
  - [x] 7.3 Update completion notes with implementation summary

## Completion Notes

### Implementation Summary

Story 5.3 is primarily a **verification and testing story**. The core insight is that the existing infrastructure from Stories 5.1 and 5.2 already provides all the mechanics needed for in-session memory references.

### Verification Findings (Task 1)

The existing implementation fully supports in-session callbacks:

1. **Buffer Content Flow**: `dm_turn()` and `pc_turn()` in agents.py append content to the short_term_buffer with `[AgentName]:` attribution
2. **Context Building**: `_build_dm_context()` and `_build_pc_context()` include buffer entries in the "Recent Events" section
3. **Limits**: DM_CONTEXT_RECENT_EVENTS_LIMIT = 10 and PC_CONTEXT_RECENT_EVENTS_LIMIT = 10 ensure the last 10 events are visible
4. **DM Access**: DM also sees "Player Knowledge" with each PC's last 3 buffer entries

### Prompt Analysis (Tasks 2-3)

**DM System Prompt** (agents.py lines 99-105) already includes excellent callback guidance:
```
## Narrative Continuity
Reference earlier events naturally to maintain immersion:
- Mention consequences of past player decisions
- Weave plot threads from earlier scenes into current narration
- Acknowledge character growth and relationships
- Reward callbacks to earlier details with meaningful payoffs
```

**PC System Prompt** was enhanced with one additional guideline:
```
- **Reference the past** - When something reminds you of earlier events, mention it naturally
```

### Test Coverage (Tasks 4-6)

Added comprehensive tests in `tests/test_memory.py`:

- `TestInSessionMemoryReferences` - 4 tests verifying buffer accumulation, chronological order, event accessibility
- `TestBufferContentPreservation` - 3 tests verifying exact content, special characters, dialogue preservation
- `TestContextEnablesCallbacks` - 3 tests verifying DM/PC context formats support callbacks
- `TestStory53AcceptanceCriteria` - 7 tests covering all 5 ACs plus DM access and PC isolation
- `TestCallbackIntegrationScenarios` - 3 tests for end-to-end callback scenarios
- `TestInSessionMemoryEdgeCases` - 4 tests for edge cases (short sessions, overflow, empty buffer)

Total: 24 new tests, all passing (244 total in test_memory.py)

### Documentation (Task 7)

Updated `memory.py` module docstring with comprehensive explanation of how the buffer enables in-session callbacks:

1. Content accumulation with attribution
2. Context building includes recent events
3. Callback capability through pattern recognition
4. Chronological order for cause-effect relationships

### Files Modified

- `agents.py` - Added one line to PC_SYSTEM_PROMPT_TEMPLATE for callback guidance
- `memory.py` - Enhanced module docstring explaining Story 5.3 implementation
- `tests/test_memory.py` - Added 24 new tests (6 test classes)

### Why Callbacks "Just Work"

The architecture enables callbacks because:
1. **Sufficient Context**: 10 recent turns provide enough history for pattern recognition
2. **Chronological Order**: Events are ordered, allowing LLMs to understand sequence
3. **Clear Attribution**: `[AgentName]:` prefixes help LLMs track who said/did what
4. **DM Prompt Guidance**: Explicit "Narrative Continuity" section encourages callbacks
5. **LLM Capability**: Modern LLMs (Gemini, Claude) naturally make connections when given sufficient context

### Test Results

```
pytest tests/test_memory.py - 247 passed
pytest (full suite) - All passed
ruff check . - All checks passed
```

## Senior Developer Review (AI)

**Review Date:** 2026-01-28
**Reviewer:** Claude Opus 4.5
**Review Type:** Adversarial Code Review (BMAD Workflow)
**Outcome:** APPROVED with fixes applied

### Issues Found and Resolved

| # | Severity | Issue | Resolution |
|---|----------|-------|------------|
| 1 | MEDIUM | Test file docstring only mentioned Story 5.1, not 5.2/5.3 | Updated docstring to document all stories covered |
| 2 | MEDIUM | Weak test assertion in `test_ac4_callback_format_enables_aha_moments` used OR fallback | Fixed test data and strengthened assertion to exact count |
| 3 | MEDIUM | Missing test for PC isolation with cross-character mentions | Added `test_pc_isolation_with_cross_character_mentions` |
| 4 | LOW | Missing edge case test for empty string entries in buffer | Added `test_buffer_with_empty_string_entries` |
| 5 | MEDIUM | Documentation in memory.py didn't reference constant names | Added reference to DM_CONTEXT_RECENT_EVENTS_LIMIT and PC_CONTEXT_RECENT_EVENTS_LIMIT |
| 6 | LOW | Test docstring for AC#2 didn't clarify it tests context enablement | Improved docstring to explain test scope |
| 7 | LOW | Missing edge case test for whitespace-only entries | Added `test_buffer_with_whitespace_only_entries` |

### Files Modified During Review

- `tests/test_memory.py` - Updated docstring, added 3 tests, strengthened assertion
- `memory.py` - Enhanced docstring with constant references

### Verification

- All 247 tests in test_memory.py pass (3 new tests added)
- ruff check: All checks passed
- ruff format: All files properly formatted
- No breaking changes to existing functionality

### Review Summary

Story 5.3 implementation was primarily verification and testing work, which was appropriate given the existing infrastructure from Stories 5.1 and 5.2. The code review found and fixed 7 issues (3 MEDIUM, 4 LOW severity) related to:

1. **Test quality** - Assertions were strengthened and edge cases added
2. **Documentation completeness** - Module docstrings updated to reflect all stories
3. **Test coverage gaps** - Added tests for cross-character mentions and edge cases

All issues were auto-resolved during review. The story is ready for completion.

## Dev Notes

### Core Insight: This May Already Work

The key realization is that **most of this functionality should already work** based on Stories 5.1 and 5.2 implementation. The short_term_buffer already:

1. Accumulates turn content with agent attribution
2. Gets included in prompts via `_build_dm_context()` and `_build_pc_context()`
3. Provides the "Recent Events" section that LLMs use for coherence

The primary work for this story is:
1. **Verification** - Confirm existing mechanics work correctly
2. **Testing** - Write tests that demonstrate the callback capability
3. **Enhancement** - Potentially improve prompts to encourage callbacks

### Existing Infrastructure Analysis

**Buffer Addition (agents.py):**

```python
# dm_turn() - lines 663-665
new_buffer = dm_memory.short_term_buffer.copy()
new_buffer.append(f"[DM]: {response_content}")
new_memories["dm"] = dm_memory.model_copy(update={"short_term_buffer": new_buffer})

# pc_turn() - lines 769-773
new_buffer = pc_memory.short_term_buffer.copy()
new_buffer.append(f"[{character_config.name}]: {response_content}")
new_memories[agent_name] = pc_memory.model_copy(update={"short_term_buffer": new_buffer})
```

Every turn appends content to the agent's buffer with attribution. This means:
- All DM narration is preserved with `[DM]:` prefix
- All PC actions/dialogue preserved with `[CharName]:` prefix
- Events accumulate chronologically (oldest first, newest last)

**Context Building (agents.py):**

```python
# _build_dm_context() - DM sees all (lines 503-508)
recent_events = "\n".join(dm_memory.short_term_buffer[-DM_CONTEXT_RECENT_EVENTS_LIMIT:])
context_parts.append(f"## Recent Events\n{recent_events}")

# _build_pc_context() - PC sees own only (lines 567-570)
recent = "\n".join(pc_memory.short_term_buffer[-PC_CONTEXT_RECENT_EVENTS_LIMIT:])
context_parts.append(f"## Recent Events\n{recent}")
```

With `DM_CONTEXT_RECENT_EVENTS_LIMIT = 10` and `PC_CONTEXT_RECENT_EVENTS_LIMIT = 10`, agents see their last 10 buffer entries. This provides the historical context needed for callbacks.

**DM System Prompt (agents.py lines 99-106):**

```python
## Narrative Continuity

Reference earlier events naturally to maintain immersion:
- Mention consequences of past player decisions
- Weave plot threads from earlier scenes into current narration
- Acknowledge character growth and relationships
- Reward callbacks to earlier details with meaningful payoffs
```

This guidance already exists and encourages the DM to make narrative callbacks.

**PC System Prompt Template (agents.py lines 137-140):**

```python
## Roleplay Guidelines

- **Be consistent** - Remember your character's motivations and relationships
- **Collaborate** - Build on what others say and do; don't contradict established facts
```

PCs have some guidance about consistency and building on established facts, but could potentially benefit from more explicit "reference past events" guidance.

### Why Callbacks Should "Just Work"

The existing architecture enables callbacks because:

1. **Sufficient Context**: 10 recent turns provide enough history for pattern recognition
2. **Chronological Order**: Events are ordered, allowing LLMs to understand sequence
3. **Clear Attribution**: `[AgentName]:` prefixes help LLMs track who said/did what
4. **DM Prompt Guidance**: Explicit "Narrative Continuity" section encourages callbacks
5. **LLM Capability**: Modern LLMs (Gemini, Claude) naturally make connections when given sufficient context

### Potential Enhancements

If testing reveals callbacks are too infrequent, consider:

1. **Stronger PC Prompt Guidance**:
```python
## Your Memory
Reference your recent experiences when relevant. If you notice something similar
to a past event, mention the connection naturally in character.
```

2. **More Specific DM Callback Instruction**:
```python
## Callbacks and Foreshadowing
When introducing new elements, consider if they connect to earlier events.
Make these connections explicit in your narration when dramatically appropriate.
```

3. **Context Formatting**:
   - Currently uses flat list of entries
   - Could add turn numbers for explicit temporal reference
   - Could highlight "notable events" with markers

However, these enhancements should only be made if testing shows the current system is insufficient.

### Testing Strategy

The tests for this story are primarily **verification tests** - proving that the existing system enables the desired behavior.

**Test File Location:** `tests/test_memory.py` (extend existing)

**Test Classes:**

```python
class TestInSessionMemoryReferences:
    """Tests for Story 5.3: In-Session Memory References."""

class TestBufferContentPreservation:
    """Tests verifying buffer correctly preserves events for reference."""

class TestContextEnablesCallbacks:
    """Tests verifying context format allows LLMs to make callbacks."""

class TestStory53AcceptanceCriteria:
    """Acceptance tests for all Story 5.3 criteria."""
```

**Key Test Scenarios:**

1. **Multi-turn History Test:**
   - Create state with 15 turns of varied content
   - Verify buffer contains events from turns 5-15 (within 10-entry limit)
   - Verify context formatting is coherent

2. **DM Cross-Reference Test:**
   - Populate DM buffer with "mysterious symbol in cave" entry
   - Add several turns of other content
   - Verify symbol event is still in context at turn 10

3. **PC Memory Isolation Test:**
   - PC A discovers a secret (in their buffer)
   - PC B's context should NOT contain PC A's secret
   - DM's context SHOULD contain PC A's secret

4. **Callback-Enabling Context Test:**
   - Create buffer with referenceable event ("old rusted sword")
   - Verify context passed to LLM contains the event
   - Verify attribution is clear enough for LLM to reference

### What This Story Implements

1. **Verification** - Confirm buffer mechanics work for in-session references
2. **Tests** - Comprehensive tests proving callback capability exists
3. **Documentation** - Clear explanation of how callbacks work
4. **Enhancement (if needed)** - Prompt improvements to encourage callbacks

### What This Story Does NOT Do

- Does NOT change the fundamental memory architecture
- Does NOT implement cross-session memory (Story 5.4)
- Does NOT implement memory compression (Story 5.5)
- Does NOT guarantee LLMs will make callbacks (emergent behavior)
- Does NOT add UI for memory display (could be future enhancement)

### Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Story 5.1: Short-Term Context Buffer | DONE | Provides buffer mechanics |
| Story 5.2: Session Summary Generation | DONE | Provides compression infrastructure |
| agents.py dm_turn/pc_turn | DONE | Buffer addition logic |
| agents.py _build_dm/pc_context | DONE | Context building with buffer |

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR13 | Agents can reference events from previous turns within same session | short_term_buffer + context building |
| FR53 | Agents can make callbacks to earlier events in narrative | DM prompt + buffer context |

[Source: epics.md#Story 5.3, prd.md#Memory & Context Management, prd.md#Agent Behavior]

### Architecture Compliance

Per architecture.md:
- **PC isolation**: PC agents ONLY see their own memory (enforced by `_build_pc_context()`)
- **DM sees all**: DM reads ALL agent memories (implemented in `_build_dm_context()`)
- **Buffer-based context**: Recent events from buffer included in prompts

### Edge Cases

1. **Very Short Session**: < 10 turns means all turns visible in context
2. **Buffer Overflow**: When buffer approaches token limit, compression kicks in (Story 5.2)
3. **Empty Buffer**: New session start - no history to reference
4. **Rapid Turns**: Many turns in quick succession - older events pushed out of 10-entry window
5. **Long Entries**: Single turn with very long content - could dominate context

### Performance Considerations

- Context building is O(1) - just slicing last N entries
- No additional LLM calls needed for this story
- Buffer operations are in-memory, fast
- No database queries

### Security Considerations

- PC isolation rules prevent information leakage between characters
- Buffer content comes from LLM responses (already trusted)
- No new attack vectors introduced

### Previous Story Intelligence (from Story 5.2)

**Key Learnings:**
- Summarizer caching improves efficiency
- Error handling with graceful degradation is important
- Type consistency with GameState is critical
- Tests for error paths are valuable

**Patterns to Follow:**
- Use existing test patterns from test_memory.py
- Comprehensive docstrings with type hints
- Verify before implementing (much may already work)

### References

- [Source: planning-artifacts/prd.md#Memory & Context Management FR13]
- [Source: planning-artifacts/prd.md#Agent Behavior FR53]
- [Source: planning-artifacts/architecture.md#Memory System Architecture]
- [Source: planning-artifacts/epics.md#Story 5.3]
- [Source: planning-artifacts/ux-design-specification.md#Memory is Magic]
- [Source: agents.py#DM_SYSTEM_PROMPT] - Narrative Continuity section
- [Source: agents.py#PC_SYSTEM_PROMPT_TEMPLATE] - Roleplay Guidelines
- [Source: agents.py#_build_dm_context] - DM context building with buffer
- [Source: agents.py#_build_pc_context] - PC context building with buffer
- [Source: memory.py#MemoryManager] - Memory abstraction layer
