# Story 5.4: Cross-Session Memory & Character Facts

Status: done

## Code Review (2026-01-28)

### Review Summary

ADVERSARIAL code review completed. Found **7 issues**: 6 fixed, 1 documented (LOW).

### Issues Found and Fixed

#### Issue 1 (HIGH - AUTO-FIXED): Missing `summarization_in_progress` in `dm_turn()` GameState
- **Location:** `agents.py` line 728
- **Problem:** GameState construction missing `summarization_in_progress` field, causing pyright errors and potential state loss.
- **Fix:** Added `summarization_in_progress=state.get("summarization_in_progress", False)` to return statement.

#### Issue 2 (HIGH - AUTO-FIXED): Missing `summarization_in_progress` in `pc_turn()` GameState
- **Location:** `agents.py` line 838
- **Problem:** Same issue as Issue 1 for PC agents.
- **Fix:** Added `summarization_in_progress=state.get("summarization_in_progress", False)` to return statement.

#### Issue 3 (HIGH - AUTO-FIXED): Missing `summarization_in_progress` in `deserialize_game_state()`
- **Location:** `persistence.py` line 232
- **Problem:** Deserialized GameState missing field, causing type errors.
- **Fix:** Added `summarization_in_progress=data.get("summarization_in_progress", False)` to return statement.

#### Issue 4 (MEDIUM - AUTO-FIXED): CharacterFacts has no validation for list/dict size limits
- **Location:** `models.py` lines 52-81
- **Problem:** `key_traits`, `relationships`, and `notable_events` had no size limits, risking unbounded growth across sessions.
- **Fix:** Added `ClassVar` constants and Pydantic validation:
  - `MAX_KEY_TRAITS = 10` with `max_length` constraint
  - `MAX_RELATIONSHIPS = 20` with `field_validator`
  - `MAX_NOTABLE_EVENTS = 20` with `max_length` constraint
  - Added `min_length=1` to `name` and `character_class` fields for consistency

#### Issue 5 (MEDIUM - AUTO-FIXED): Missing `summarization_in_progress` in `serialize_game_state()`
- **Location:** `persistence.py` lines 181-197
- **Problem:** Serialization did not include `summarization_in_progress`, losing state during save/load.
- **Fix:** Added `"summarization_in_progress": state.get("summarization_in_progress", False)` to serializable dict.

#### Issue 6 (MEDIUM - AUTO-FIXED): Missing test for corrupted CharacterFacts during cross-session load
- **Location:** `tests/test_story_5_4_acceptance.py`
- **Problem:** No test verifying graceful handling of corrupted previous session data.
- **Fix:** Added `test_corrupted_previous_session_returns_new_state_unchanged()` test case.

#### Issue 7 (LOW - DOCUMENTED): Test GameState objects missing `summarization_in_progress`
- **Location:** Various test files
- **Problem:** Many tests construct GameState dicts without `summarization_in_progress` field. Works due to `.get()` fallbacks but technically incomplete.
- **Status:** Documented only - fixing would require many test changes across files with minimal impact since tests pass.

### Files Modified
1. `agents.py` - Added `summarization_in_progress` to `dm_turn()` and `pc_turn()` returns
2. `persistence.py` - Added `summarization_in_progress` to serialize/deserialize functions
3. `models.py` - Added size limits and validation to `CharacterFacts` model
4. `tests/test_story_5_4_acceptance.py` - Added corrupted data edge case test
5. `tests/test_persistence.py` - Updated expected keys test

### Test Results
- All 1874 tests passing
- Ruff lint: All checks passed
- Ruff format: 21 files already formatted

## Story

As a **user returning to a campaign**,
I want **agents to remember events from previous sessions**,
so that **my ongoing story has real continuity**.

## Acceptance Criteria

1. **Given** a campaign spans multiple sessions
   **When** a new session starts
   **Then** each agent's `long_term_summary` is loaded from the previous session (FR14)

2. **Given** the `long_term_summary` contains "The party befriended a goblin named Skrix"
   **When** goblins are encountered again
   **Then** an agent might reference Skrix or that previous encounter

3. **Given** character facts (name, class, key traits, relationships)
   **When** stored in AgentMemory
   **Then** they persist across sessions (FR15)
   **And** are always included in the agent's context

4. **Given** the rogue established a rivalry with a merchant in session 2
   **When** that merchant appears in session 5
   **Then** the rogue's response reflects that history

5. **Given** cross-session memory loading
   **When** a session resumes
   **Then** the "While you were away..." summary draws from these memories
   **And** agents can reference past sessions naturally

## Tasks / Subtasks

- [x] Task 1: Add CharacterFacts model for persistent character identity
  - [x] 1.1 Create `CharacterFacts` Pydantic model in models.py with fields: name, character_class, key_traits, relationships, notable_events
  - [x] 1.2 Add `character_facts: CharacterFacts | None` field to AgentMemory model
  - [x] 1.3 Update `create_agent_memory()` factory to optionally accept CharacterFacts
  - [x] 1.4 Write unit tests for CharacterFacts model validation
  - [x] 1.5 Write tests for AgentMemory serialization with character_facts

- [x] Task 2: Update persistence to save/load cross-session memory
  - [x] 2.1 Modify `serialize_game_state()` to include character_facts in agent_memories serialization
  - [x] 2.2 Modify `deserialize_game_state()` to restore character_facts from checkpoint
  - [x] 2.3 Add `initialize_session_with_previous_memories()` function to load memories from previous session
  - [x] 2.4 Write tests for cross-session memory serialization/deserialization
  - [x] 2.5 Write tests for loading memories from previous session

- [x] Task 3: Implement memory initialization on session start
  - [x] 3.1 Create `initialize_session_with_previous_memories()` function in persistence.py
  - [x] 3.2 Find latest checkpoint from previous session (if any)
  - [x] 3.3 Extract long_term_summary and character_facts from previous session state
  - [x] 3.4 Initialize new session agent memories with carried-over data
  - [x] 3.5 Ensure short_term_buffer starts empty for new session
  - [x] 3.6 Write tests for memory initialization from previous session
  - [x] 3.7 Write tests for first session (no previous memories)

- [x] Task 4: Populate CharacterFacts from character configs
  - [x] 4.1 Add `create_character_facts_from_config(config: CharacterConfig) -> CharacterFacts` function
  - [x] 4.2 Extract name, character_class from config
  - [x] 4.3 Initialize empty relationships list (populated during gameplay)
  - [x] 4.4 Update `populate_game_state()` to create CharacterFacts for each agent
  - [x] 4.5 Write tests for CharacterFacts creation from config

- [x] Task 5: Include CharacterFacts in agent context building
  - [x] 5.1 Update `_build_dm_context()` in agents.py to include all agents' character_facts
  - [x] 5.2 Update `_build_pc_context()` in agents.py to include PC's own character_facts
  - [x] 5.3 Create `format_character_facts()` helper for prompt-ready formatting
  - [x] 5.4 Add character_facts to "Character Identity" section for PCs
  - [x] 5.5 Add character_facts to "Party Members" section for DM
  - [x] 5.6 Write tests for context building with character_facts

- [x] Task 6: Update MemoryManager for cross-session context
  - [x] 6.1 Add `get_character_facts(agent_name: str) -> CharacterFacts | None` method
  - [x] 6.2 Update `get_context()` to include character_facts in returned context
  - [x] 6.3 Add `get_cross_session_summary()` method for recap generation
  - [x] 6.4 Write tests for MemoryManager cross-session methods

- [x] Task 7: Enhance generate_recap_summary for cross-session content
  - [x] 7.1 Update `generate_recap_summary()` in persistence.py to include long_term_summary
  - [x] 7.2 Format recap with character relationships and key events
  - [x] 7.3 Add include_cross_session parameter for multi-session recaps
  - [x] 7.4 Limit recap length while preserving key narrative threads
  - [x] 7.5 Write tests for enhanced recap generation

- [x] Task 8: Integrate with session continuation flow
  - [x] 8.1 Update `app.py` session loading to use include_cross_session=True for recap
  - [x] 8.2 Ensure "While you were away..." draws from cross-session memories
  - [x] 8.3 CharacterFacts automatically populated via populate_game_state()
  - [x] 8.4 Write integration tests for session continuation with memory

- [x] Task 9: Extract and persist notable events and relationships
  - [x] 9.1 Add `update_character_facts()` method to MemoryManager
  - [x] 9.2 Method supports adding key_traits, relationships, and notable_events
  - [x] 9.3 Method merges/appends to existing CharacterFacts
  - [x] 9.4 CharacterFacts persists to agent memory automatically via Pydantic
  - [x] 9.5 Write tests for update_character_facts method

- [x] Task 10: Write comprehensive acceptance tests
  - [x] 10.1 Test: long_term_summary persists across session boundaries
  - [x] 10.2 Test: Character facts preserved from session 1 to session 2
  - [x] 10.3 Test: Agents can reference events from previous sessions
  - [x] 10.4 Test: DM context includes all character facts
  - [x] 10.5 Test: PC context includes only own character facts
  - [x] 10.6 Test: "While you were away" includes cross-session summary
  - [x] 10.7 Test: Relationships established in session 2 affect session 5
  - [x] 10.8 Test: First session works correctly with no previous memories

## Dev Notes

### Existing Infrastructure Analysis

**AgentMemory (models.py) - Story 5.1/5.2:**
```python
class AgentMemory(BaseModel):
    long_term_summary: str = Field(default="", description="Compressed history from the summarizer")
    short_term_buffer: list[str] = Field(default_factory=list, description="Recent turns, newest at the end")
    token_limit: int = Field(default=8000, ge=1, description="Maximum tokens for this agent's context")
```

The `long_term_summary` field already exists and is populated by Story 5.2's summarization system. Story 5.4 needs to ensure this field persists across sessions.

**SessionMetadata (models.py) - Story 4.3:**
```python
class SessionMetadata(BaseModel):
    session_id: str = Field(..., min_length=1, description="Session ID string")
    session_number: int = Field(..., ge=1, description="Numeric session number")
    # ... other fields
```

Used to track session numbers and ordering for continuity.

**persistence.py Functions:**
```python
def load_checkpoint(session_id: str, turn_number: int) -> GameState | None
def list_sessions() -> list[str]
def get_latest_checkpoint(session_id: str) -> int | None
def generate_recap_summary(session_id: str, num_turns: int = 5) -> str | None
```

These functions provide the foundation for cross-session memory loading.

**Context Building (agents.py):**
```python
def _build_dm_context(state: GameState) -> str:
    """Build context for DM with asymmetric memory access."""
    # Includes long_term_summary in "Story So Far" section

def _build_pc_context(state: GameState, agent_name: str) -> str:
    """Build context for PC with only their own memory."""
    # Includes long_term_summary in "What You Remember" section
```

These already include long_term_summary but need character_facts integration.

### CharacterFacts Model Design

```python
class CharacterFacts(BaseModel):
    """Persistent character identity that carries across sessions.

    This model captures the essential facts about a character that should
    persist between sessions and always be included in agent context.

    Attributes:
        name: Character's name (e.g., "Shadowmere")
        character_class: D&D class (e.g., "Rogue")
        key_traits: Core personality traits and quirks
        relationships: Dict of character name -> relationship description
        notable_events: List of significant events involving this character
    """
    name: str
    character_class: str
    key_traits: list[str] = Field(default_factory=list)
    relationships: dict[str, str] = Field(default_factory=dict)
    notable_events: list[str] = Field(default_factory=list)
```

**Example:**
```python
CharacterFacts(
    name="Shadowmere",
    character_class="Rogue",
    key_traits=["Sardonic wit", "Trust issues", "Observant"],
    relationships={
        "Theros": "Trusted party member, saved my life in the goblin cave",
        "Marcus the Merchant": "Rival - tried to cheat me in session 2"
    },
    notable_events=[
        "Discovered the hidden passage in Thornwood Tower",
        "Stole the enchanted dagger from Lord Blackwood"
    ]
)
```

### Cross-Session Memory Loading Flow

```
Session 2 starts:
1. User selects "Continue Campaign" or starts new session
2. System finds previous session (session 1)
3. Load latest checkpoint from session 1
4. Extract agent_memories from checkpoint
5. For each agent:
   - Copy long_term_summary to new session
   - Copy character_facts to new session
   - Initialize empty short_term_buffer (fresh session)
6. Create new GameState with initialized memories
7. Save initial checkpoint for session 2
8. Display "While you were away..." with cross-session context
```

**Implementation:**
```python
def initialize_session_with_previous_memories(
    previous_session_id: str,
    new_session_id: str,
    state: GameState
) -> GameState:
    """Initialize new session with memories from previous session.

    Args:
        previous_session_id: The session to load memories from.
        new_session_id: The new session being created.
        state: Base GameState with characters configured.

    Returns:
        GameState with agent memories initialized from previous session.
    """
    # Load previous session's final checkpoint
    latest_turn = get_latest_checkpoint(previous_session_id)
    if latest_turn is None:
        return state  # No previous memories to load

    prev_state = load_checkpoint(previous_session_id, latest_turn)
    if prev_state is None:
        return state

    # Copy memories to new session
    new_memories: dict[str, AgentMemory] = {}
    for agent_name, memory in state["agent_memories"].items():
        prev_memory = prev_state["agent_memories"].get(agent_name)
        if prev_memory:
            new_memories[agent_name] = AgentMemory(
                long_term_summary=prev_memory.long_term_summary,
                character_facts=prev_memory.character_facts,
                short_term_buffer=[],  # Start fresh
                token_limit=memory.token_limit
            )
        else:
            new_memories[agent_name] = memory

    return {**state, "agent_memories": new_memories}
```

### Context Building with CharacterFacts

**For PC agents (strict isolation):**
```python
def _build_pc_context(state: GameState, agent_name: str) -> str:
    context_parts: list[str] = []

    pc_memory = state["agent_memories"].get(agent_name)
    if pc_memory:
        # Character facts (always included)
        if pc_memory.character_facts:
            facts = format_character_facts(pc_memory.character_facts)
            context_parts.append(f"## Who You Are\n{facts}")

        # Long-term summary (cross-session memory)
        if pc_memory.long_term_summary:
            context_parts.append(f"## What You Remember\n{pc_memory.long_term_summary}")

        # Recent events (in-session memory)
        if pc_memory.short_term_buffer:
            recent = "\n".join(pc_memory.short_term_buffer[-10:])
            context_parts.append(f"## Recent Events\n{recent}")

    return "\n\n".join(context_parts)
```

**For DM (asymmetric access):**
```python
def _build_dm_context(state: GameState) -> str:
    context_parts: list[str] = []

    # DM's own long-term summary
    dm_memory = state["agent_memories"].get("dm")
    if dm_memory and dm_memory.long_term_summary:
        context_parts.append(f"## Story So Far\n{dm_memory.long_term_summary}")

    # Character facts for all party members
    party_facts: list[str] = []
    for agent_name, memory in state["agent_memories"].items():
        if agent_name == "dm":
            continue
        if memory.character_facts:
            facts = format_character_facts_brief(memory.character_facts)
            party_facts.append(f"**{memory.character_facts.name}**: {facts}")

    if party_facts:
        context_parts.append("## Party Facts\n" + "\n".join(party_facts))

    # ... rest of DM context building
```

### Enhanced Recap Summary

```python
def generate_recap_summary(session_id: str, num_turns: int = 5) -> str | None:
    """Generate a 'While you were away' summary with cross-session context.

    Draws from:
    1. Recent turns from current session (if any)
    2. long_term_summary from previous session
    3. Character facts and relationships
    """
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is None:
        # First session - check for previous session
        session_ids = list_sessions()
        if len(session_ids) <= 1:
            return None  # Truly first session

        # Find previous session
        current_idx = session_ids.index(session_id) if session_id in session_ids else -1
        if current_idx <= 0:
            return None

        prev_session_id = session_ids[current_idx - 1]
        prev_turn = get_latest_checkpoint(prev_session_id)
        if prev_turn is None:
            return None

        prev_state = load_checkpoint(prev_session_id, prev_turn)
        if prev_state is None:
            return None

        # Build recap from previous session's long_term_summary
        recap_lines: list[str] = []
        recap_lines.append("*From your previous adventures...*")

        dm_memory = prev_state["agent_memories"].get("dm")
        if dm_memory and dm_memory.long_term_summary:
            # Take first 200 words of summary
            words = dm_memory.long_term_summary.split()[:200]
            summary_excerpt = " ".join(words)
            if len(dm_memory.long_term_summary.split()) > 200:
                summary_excerpt += "..."
            recap_lines.append(summary_excerpt)

        return "\n\n".join(recap_lines) if recap_lines else None

    # Continue with existing recap logic for in-session recap...
```

### Architecture Compliance

Per architecture.md:

| Decision | Status | Notes |
|----------|--------|-------|
| Memory isolation | DONE | PCs see own, DM sees all (Story 5.1) |
| long_term_summary | DONE | Already exists and is populated (Story 5.2) |
| Checkpoint persistence | DONE | Full state serialization (Story 4.1) |
| Cross-session continuity | TODO | **This Story** |
| Character facts | TODO | **This Story** |

**Memory System Architecture (architecture.md):**
> - `long_term_summary`: Compressed history from the summarizer agent.
>   Contains key events, character facts, and narrative threads.

This confirms that long_term_summary should contain character-relevant information that persists.

### Serialization Updates

The `serialize_game_state()` and `deserialize_game_state()` functions in persistence.py already handle AgentMemory serialization. Since CharacterFacts will be a field of AgentMemory, Pydantic's `.model_dump()` will automatically serialize it:

```python
def serialize_game_state(state: GameState) -> str:
    serializable: dict[str, Any] = {
        # ...
        "agent_memories": {
            k: v.model_dump() for k, v in state["agent_memories"].items()
        },
        # ...
    }
    return json.dumps(serializable, indent=2)
```

The `model_dump()` call will include `character_facts` automatically.

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR14 | Reference events from previous sessions via summaries | Cross-session long_term_summary loading |
| FR15 | Character facts persist across sessions | CharacterFacts model in AgentMemory |

### Dependencies

**Stories 5.1-5.3 (All DONE):**
- Story 5.1: Short-term context buffer - provides buffer management
- Story 5.2: Session summary generation - populates long_term_summary
- Story 5.3: In-session memory references - context building patterns

**Story 4.3 (DONE):**
- Campaign organization and multi-session continuity
- Session metadata and continuation flow
- "While you were away..." infrastructure

### Testing Strategy

```python
class TestCharacterFacts:
    """Tests for CharacterFacts model."""

    def test_create_character_facts(self):
        """Test CharacterFacts creation with all fields."""

    def test_character_facts_serialization(self):
        """Test Pydantic serialization/deserialization."""

    def test_character_facts_from_config(self):
        """Test creating CharacterFacts from CharacterConfig."""

class TestCrossSessionMemory:
    """Tests for cross-session memory persistence."""

    def test_long_term_summary_persists_across_sessions(self):
        """Test summary from session 1 loads into session 2."""

    def test_character_facts_persist_across_sessions(self):
        """Test facts from session 1 available in session 2."""

    def test_short_term_buffer_resets_on_new_session(self):
        """Test buffer starts empty in new session."""

    def test_first_session_has_no_previous_memories(self):
        """Test graceful handling of first session."""

class TestContextBuildingWithFacts:
    """Tests for context building with character facts."""

    def test_pc_context_includes_own_facts(self):
        """Test PC context includes their character facts."""

    def test_dm_context_includes_all_facts(self):
        """Test DM context includes all party facts."""

    def test_facts_appear_before_summary_in_context(self):
        """Test facts are positioned correctly in context."""

class TestEnhancedRecap:
    """Tests for enhanced recap with cross-session content."""

    def test_recap_includes_previous_session_summary(self):
        """Test recap draws from previous session."""

    def test_recap_includes_character_relationships(self):
        """Test recap mentions key relationships."""

    def test_recap_limited_length(self):
        """Test recap doesn't exceed reasonable length."""

class TestStory54AcceptanceCriteria:
    """Acceptance tests for all Story 5.4 criteria."""

    def test_ac1_long_term_summary_loaded_from_previous_session(self):
        """AC1: long_term_summary loaded on session start."""

    def test_ac2_agent_references_previous_encounter(self):
        """AC2: Agent can reference Skrix from previous session."""

    def test_ac3_character_facts_persist_across_sessions(self):
        """AC3: Facts persist and are included in context."""

    def test_ac4_relationship_affects_future_responses(self):
        """AC4: Rivalry from session 2 affects session 5."""

    def test_ac5_recap_draws_from_cross_session_memories(self):
        """AC5: While you were away includes cross-session data."""
```

### Edge Cases

1. **First session ever:** No previous memories to load, start fresh
2. **Empty previous session:** Previous session had no turns, no summary to load
3. **Missing agent in previous session:** Character added mid-campaign
4. **Character removed between sessions:** Character no longer in party
5. **Corrupted previous checkpoint:** Graceful degradation, start fresh
6. **Very large long_term_summary:** May need truncation for context limits
7. **Session gap (missing session 2):** Handle non-consecutive sessions
8. **Same character name, different config:** Match by agent key, not name

### Performance Considerations

- Cross-session loading happens once at session start (O(1) checkpoint load)
- CharacterFacts add small overhead to context (~100-200 tokens)
- No impact on turn-by-turn performance
- Memory serialization already handles large states efficiently (Story 4.1)

### Security Considerations

- All data comes from trusted checkpoint files
- No external input in cross-session loading
- Path traversal prevented by existing session_id validation
- No LLM calls during memory loading

### What This Story Implements

1. `CharacterFacts` model for persistent identity
2. Cross-session `long_term_summary` loading
3. `character_facts` field in `AgentMemory`
4. Enhanced context building with facts
5. Cross-session recap generation
6. Session continuation with memory initialization

### What This Story Does NOT Do

- Does NOT implement memory compression triggering (Story 5.5)
- Does NOT add UI for editing character facts (future enhancement)
- Does NOT implement character fact extraction from gameplay (partial - hooks only)
- Does NOT change how summarization works (Story 5.2)

### References

- [Source: planning-artifacts/prd.md#Memory & Context Management FR14, FR15]
- [Source: planning-artifacts/architecture.md#Memory System Architecture]
- [Source: planning-artifacts/epics.md#Story 5.4]
- [Source: persistence.py] - Checkpoint save/load, session management
- [Source: models.py#AgentMemory] - Memory model with long_term_summary
- [Source: agents.py#_build_dm_context] - Context building for DM
- [Source: agents.py#_build_pc_context] - Context building for PCs
- [Source: memory.py#MemoryManager] - Memory management interface
