# Story 11-2: Callback Database

## Story

As a **system**,
I want **to store narrative elements with full context**,
So that **they can be surfaced for callbacks later**.

## Status

**Status:** ready-for-dev
**Epic:** 11 - Callback Tracker (Chekhov's Gun)
**Created:** 2026-02-06
**FRs Covered:** FR77 (store in callback database), FR78 (partial: potential_callbacks field)
**Predecessor:** Story 11-1 (Narrative Element Extraction) - DONE

## Acceptance Criteria

**Given** extracted narrative elements
**When** stored
**Then** each element has:
```python
class NarrativeElement(BaseModel):
    id: str
    element_type: str  # npc, location, item, plot_hook, backstory
    name: str
    description: str
    turn_introduced: int
    session_introduced: int
    characters_involved: list[str]
    times_referenced: int = 1
    last_referenced_turn: int
    potential_callbacks: list[str] = []  # AI-suggested uses
```

**Given** the callback database
**When** persisted
**Then** it's saved with the campaign (not just session)

**Given** elements are referenced again
**When** detected
**Then** `times_referenced` increments and `last_referenced_turn` updates

**Given** the database grows
**When** elements haven't been referenced in 20+ turns
**Then** they're marked as "dormant" (still available but lower priority)

## Context: What Story 11-1 Built

Story 11-1 established the foundation. The following already exist in the codebase:

### models.py (existing)
- `NarrativeElement` model with fields: `id`, `element_type`, `name`, `description`, `turn_introduced`, `session_introduced`, `turns_referenced` (list[int]), `characters_involved`, `resolved`
- `NarrativeElementStore` with methods: `get_active()`, `get_by_type()`, `find_by_name()`
- `create_narrative_element()` factory function
- `GameState` has `narrative_elements: dict[str, NarrativeElementStore]` keyed by session_id
- Both `create_initial_game_state()` and `populate_game_state()` initialize empty narrative_elements

### memory.py (existing)
- `NarrativeElementExtractor` class with lazy LLM initialization
- `extract_narrative_elements()` function that merges into state
- `_parse_extraction_response()` helper for JSON parsing
- `ELEMENT_EXTRACTION_PROMPT` constant
- `_extractor_cache` for instance caching

### agents.py (existing)
- `dm_turn()` calls `extract_narrative_elements()` after DM response
- `pc_turn()` calls `extract_narrative_elements()` after PC response
- Both gracefully handle extraction failures

### persistence.py (existing)
- `serialize_game_state()` handles `narrative_elements` serialization
- `deserialize_game_state()` handles reconstruction with backward compatibility

### config.py / defaults.yaml (existing)
- `extractor` agent config in `AgentsConfig`
- Extractor defaults in `config/defaults.yaml`

## What Story 11-2 Changes

This story ENHANCES the existing models and store with new capabilities:

1. **New fields on NarrativeElement**: `times_referenced` (int counter), `last_referenced_turn` (int), `potential_callbacks` (list[str]), `dormant` (bool) status
2. **Enhanced NarrativeElementStore**: Reference tracking methods, dormancy management, campaign-level persistence, duplicate detection/merging
3. **Campaign-level persistence**: Store keyed by campaign (not just session), with cross-session carry-over
4. **Reference detection**: When an element is re-mentioned, increment `times_referenced` and update `last_referenced_turn`
5. **Dormancy**: Elements unreferenced for 20+ turns are marked dormant

## Tasks

### 1. Enhance NarrativeElement Model (models.py)

1. [ ] Add `times_referenced: int` field to `NarrativeElement`
   - `Field(default=1, ge=1, description="Number of times element has been referenced")`
   - Starts at 1 (the turn it was introduced counts as first reference)
2. [ ] Add `last_referenced_turn: int` field to `NarrativeElement`
   - `Field(default=0, ge=0, description="Turn number when element was last referenced")`
   - Defaults to `turn_introduced` value via model_validator
3. [ ] Add `potential_callbacks: list[str]` field to `NarrativeElement`
   - `Field(default_factory=list, description="AI-suggested callback uses for this element")`
   - Empty by default; populated by extraction or later by DM callback suggestions (Story 11.3)
4. [ ] Add `dormant: bool` field to `NarrativeElement`
   - `Field(default=False, description="Whether element is dormant (unreferenced 20+ turns)")`
   - Dormant elements are still available but lower priority for callback suggestions
5. [ ] Add `model_validator` for `last_referenced_turn` defaulting
   - If `last_referenced_turn` is 0 and `turn_introduced` > 0, set `last_referenced_turn = turn_introduced`
   - This ensures backward compatibility with elements created by story 11-1 that lack this field
6. [ ] Update docstring for `NarrativeElement` to reflect Story 11.2 enhancements

### 2. Enhance NarrativeElementStore (models.py)

7. [ ] Add `DORMANT_THRESHOLD: ClassVar[int] = 20` class constant
   - Number of turns without reference before an element becomes dormant
8. [ ] Add `add_element()` method to `NarrativeElementStore`
   - Accepts a `NarrativeElement`
   - Checks for existing element with same name (case-insensitive) via `find_by_name()`
   - If duplicate found: merges by incrementing `times_referenced`, updating `last_referenced_turn`, appending new `characters_involved`, merging `potential_callbacks`
   - If new: appends to elements list
   - Returns the element (merged or new)
9. [ ] Add `record_reference()` method to `NarrativeElementStore`
   - Accepts `element_id: str` and `turn_number: int`
   - Finds element by ID, increments `times_referenced`, sets `last_referenced_turn = turn_number`
   - Appends turn_number to `turns_referenced` if not already present
   - If element was dormant, sets `dormant = False` (re-awakened)
   - Returns the updated element or None if not found
10. [ ] Add `update_dormancy()` method to `NarrativeElementStore`
    - Accepts `current_turn: int`
    - Iterates all active (non-resolved) elements
    - For each: if `current_turn - last_referenced_turn >= DORMANT_THRESHOLD`, sets `dormant = True`
    - Returns count of newly dormant elements
11. [ ] Add `get_dormant()` method to `NarrativeElementStore`
    - Returns list of dormant elements (dormant=True and not resolved)
12. [ ] Add `get_active_non_dormant()` method to `NarrativeElementStore`
    - Returns elements that are active (not resolved) AND not dormant
    - This is the primary query for DM callback suggestions (Story 11.3)
13. [ ] Add `get_by_relevance()` method to `NarrativeElementStore`
    - Returns all active elements sorted by relevance score
    - Relevance = `times_referenced * 2 + (1 if not dormant else 0)` (simple scoring)
    - Non-dormant elements ranked higher; more-referenced elements ranked higher
    - Accepts optional `limit: int` parameter
14. [ ] Add `get_all()` method to `NarrativeElementStore` (if not already present)
    - Returns all elements including dormant and resolved
15. [ ] Update `add_element` to also set `potential_callbacks` from extraction if provided
16. [ ] Update docstring for `NarrativeElementStore` to reflect Story 11.2 enhancements

### 3. Update create_narrative_element Factory (models.py)

17. [ ] Update `create_narrative_element()` to accept optional `potential_callbacks: list[str]`
18. [ ] Update `create_narrative_element()` to set `last_referenced_turn = turn_introduced` by default
19. [ ] Ensure `times_referenced` defaults to 1 in factory

### 4. Campaign-Level Persistence (persistence.py)

20. [ ] Update `serialize_game_state()` to include a campaign-level `callback_database` key
    - The `callback_database` is a merged `NarrativeElementStore` across all sessions
    - Serialize as `state.get("callback_database", NarrativeElementStore()).model_dump()`
21. [ ] Update `deserialize_game_state()` to reconstruct `callback_database`
    - Backward compatible: old checkpoints without `callback_database` get an empty store
    - Reconstruct `NarrativeElement` objects from raw dicts, handling missing new fields
22. [ ] Add `callback_database: NarrativeElementStore` field to `GameState` TypedDict
    - This is the campaign-level database (distinct from per-session `narrative_elements`)
23. [ ] Update `create_initial_game_state()` to initialize empty `callback_database`
24. [ ] Update `populate_game_state()` to initialize empty `callback_database`

### 5. Merge Extraction into Callback Database (memory.py)

25. [ ] Update `extract_narrative_elements()` to also merge into `callback_database`
    - After extracting elements and storing in per-session store, also add to campaign-level database
    - Use `NarrativeElementStore.add_element()` for dedup/merge logic
    - Return both `narrative_elements` dict AND `callback_database` store
26. [ ] Update return type of `extract_narrative_elements()` to return a dict with both stores
    - Return `{"narrative_elements": dict, "callback_database": NarrativeElementStore}`
    - Or return a NamedTuple/dataclass for type safety

### 6. Update Agent Integration (agents.py)

27. [ ] Update `dm_turn()` to pass `callback_database` into returned state
    - After `extract_narrative_elements()`, include updated `callback_database` in return dict
28. [ ] Update `pc_turn()` to pass `callback_database` into returned state
    - Same pattern as dm_turn
29. [ ] After extraction, call `callback_database.update_dormancy(turn_number)` to manage dormant elements

### 7. Update Extraction Prompt for potential_callbacks (memory.py)

30. [ ] Enhance `ELEMENT_EXTRACTION_PROMPT` to also request `potential_callbacks`
    - Add to the JSON response format: `"potential_callbacks": ["Could return as ally", "Might betray party"]`
    - These are AI-suggested ways the element could be called back later
31. [ ] Update `_parse_extraction_response()` to extract `potential_callbacks` from response
    - Pass through to `create_narrative_element()` if present
    - Default to empty list if not provided (graceful degradation)

### 8. Cross-Session Carry-Over (persistence.py)

32. [ ] Update `initialize_session_with_previous_memories()` to carry over `callback_database`
    - Load `callback_database` from previous session's latest checkpoint
    - Carry it forward into the new session's state
    - This enables cross-session callback tracking (Chekhov's gun planted in session 1 fires in session 3)

### 9. Tests

33. [ ] Test `NarrativeElement` new fields (times_referenced, last_referenced_turn, potential_callbacks, dormant)
    - Default values correct (times_referenced=1, dormant=False, etc.)
    - model_validator sets last_referenced_turn from turn_introduced
    - Backward compatibility: elements without new fields deserialize correctly
34. [ ] Test `NarrativeElementStore.add_element()` dedup/merge
    - New element added to store
    - Duplicate name detected and merged (times_referenced incremented, characters merged)
    - Case-insensitive name matching
35. [ ] Test `NarrativeElementStore.record_reference()`
    - times_referenced increments
    - last_referenced_turn updates
    - turns_referenced list updated
    - Dormant element re-awakened on reference
    - Non-existent ID returns None
36. [ ] Test `NarrativeElementStore.update_dormancy()`
    - Element unreferenced for 20+ turns becomes dormant
    - Element referenced within 20 turns stays active
    - Already dormant elements remain dormant
    - Resolved elements are not made dormant
37. [ ] Test `NarrativeElementStore.get_dormant()` and `get_active_non_dormant()`
    - Correct filtering by dormant status
38. [ ] Test `NarrativeElementStore.get_by_relevance()`
    - Sorted by relevance score
    - limit parameter works
    - Non-dormant elements ranked higher
39. [ ] Test `create_narrative_element()` with new optional parameters
40. [ ] Test campaign-level persistence (callback_database serialization round-trip)
    - serialize -> deserialize preserves all fields including new ones
    - Backward compatibility: old checkpoints without callback_database
41. [ ] Test `extract_narrative_elements()` merges into callback_database
42. [ ] Test dormancy management in agent turn integration
43. [ ] Test cross-session carry-over of callback_database
44. [ ] Test `_parse_extraction_response()` with potential_callbacks in response

## Dependencies

- **Story 11-1** (done): Provides base NarrativeElement, NarrativeElementStore, extraction logic
- **Epic 10** (done): Provides patterns for state integration (agent_secrets)
- **Story 5.4** (done): Provides `initialize_session_with_previous_memories()` pattern for cross-session carry-over
- **Story 4.1** (done): Provides checkpoint serialization patterns

## Dev Notes

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `models.py` | Modify | Add new fields to `NarrativeElement`, enhance `NarrativeElementStore` with methods, add `callback_database` to `GameState`, update factory functions |
| `memory.py` | Modify | Update `extract_narrative_elements()` to merge into campaign database, update prompt and parser for `potential_callbacks` |
| `agents.py` | Modify | Update `dm_turn()` and `pc_turn()` to propagate `callback_database`, call `update_dormancy()` |
| `persistence.py` | Modify | Add `callback_database` serialization/deserialization, update cross-session carry-over |
| `tests/test_story_11_2_callback_database.py` | Create | Comprehensive unit and integration tests |

### Code Patterns to Follow

#### 1. NarrativeElement Enhancements (models.py)

Add new fields after existing ones, preserving backward compatibility with defaults:

```python
class NarrativeElement(BaseModel):
    """Extracted narrative element for callback tracking.

    Story 11.1: Narrative Element Extraction.
    Story 11.2: Callback Database - Enhanced with reference tracking and dormancy.
    FRs: FR76 (extract elements), FR77 (store with context).

    Attributes:
        id: Unique identifier (UUID hex string).
        element_type: Category of narrative element.
        name: Name of the element (e.g., NPC name, location name).
        description: Context description of the element.
        turn_introduced: Turn number when first extracted.
        session_introduced: Session number when first extracted.
        turns_referenced: List of turn numbers where element was referenced.
        characters_involved: List of character names involved with this element.
        resolved: Whether this element has been resolved/concluded.
        times_referenced: Count of times this element has been referenced.
        last_referenced_turn: Turn number when element was last referenced.
        potential_callbacks: AI-suggested ways this element could be called back.
        dormant: Whether element is dormant (unreferenced for 20+ turns).
    """
    # ... existing fields unchanged ...

    # Story 11.2: Callback Database enhancements
    times_referenced: int = Field(
        default=1, ge=1, description="Number of times element has been referenced"
    )
    last_referenced_turn: int = Field(
        default=0, ge=0, description="Turn number when last referenced"
    )
    potential_callbacks: list[str] = Field(
        default_factory=list, description="AI-suggested callback uses"
    )
    dormant: bool = Field(
        default=False, description="Whether element is dormant (unreferenced 20+ turns)"
    )

    @model_validator(mode="after")
    def default_last_referenced(self) -> "NarrativeElement":
        """Default last_referenced_turn to turn_introduced if not set."""
        if self.last_referenced_turn == 0 and self.turn_introduced > 0:
            self.last_referenced_turn = self.turn_introduced
        return self
```

Note: The `model_validator` ensures backward compatibility. Elements created by Story 11-1 (which lack `last_referenced_turn`) will have it auto-set to `turn_introduced`. This is safe because `mode="after"` runs after field defaults.

#### 2. NarrativeElementStore Enhancements (models.py)

Add methods below the existing ones. Follow the pattern of existing methods:

```python
class NarrativeElementStore(BaseModel):
    """Container for narrative elements.

    Story 11.1: Basic storage and query.
    Story 11.2: Enhanced with reference tracking, dormancy, and relevance scoring.
    """

    DORMANT_THRESHOLD: ClassVar[int] = 20  # Turns without reference before dormancy

    elements: list[NarrativeElement] = Field(
        default_factory=list, description="All narrative elements"
    )

    # ... existing methods (get_active, get_by_type, find_by_name) unchanged ...

    def add_element(self, element: NarrativeElement) -> NarrativeElement:
        """Add element with duplicate detection and merging.

        If an element with the same name exists (case-insensitive),
        merges reference data. Otherwise adds as new.

        Args:
            element: The NarrativeElement to add.

        Returns:
            The element (merged or newly added).
        """
        existing = self.find_by_name(element.name)
        if existing is not None:
            # Merge: increment references, update turn, merge involved characters
            existing.times_referenced += 1
            existing.last_referenced_turn = max(
                existing.last_referenced_turn, element.turn_introduced
            )
            if element.turn_introduced not in existing.turns_referenced:
                existing.turns_referenced.append(element.turn_introduced)
            for char in element.characters_involved:
                if char not in existing.characters_involved:
                    existing.characters_involved.append(char)
            for cb in element.potential_callbacks:
                if cb not in existing.potential_callbacks:
                    existing.potential_callbacks.append(cb)
            # Re-awaken if dormant
            if existing.dormant:
                existing.dormant = False
            return existing
        else:
            self.elements.append(element)
            return element

    def record_reference(self, element_id: str, turn_number: int) -> NarrativeElement | None:
        """Record that an element was referenced in a turn.

        Args:
            element_id: ID of the element to update.
            turn_number: Turn number where reference occurred.

        Returns:
            Updated element, or None if not found.
        """
        for element in self.elements:
            if element.id == element_id:
                element.times_referenced += 1
                element.last_referenced_turn = turn_number
                if turn_number not in element.turns_referenced:
                    element.turns_referenced.append(turn_number)
                if element.dormant:
                    element.dormant = False
                return element
        return None

    def update_dormancy(self, current_turn: int) -> int:
        """Mark elements as dormant if unreferenced for DORMANT_THRESHOLD turns.

        Args:
            current_turn: Current turn number.

        Returns:
            Number of elements newly marked as dormant.
        """
        newly_dormant = 0
        for element in self.elements:
            if element.resolved or element.dormant:
                continue
            if current_turn - element.last_referenced_turn >= self.DORMANT_THRESHOLD:
                element.dormant = True
                newly_dormant += 1
        return newly_dormant

    def get_dormant(self) -> list[NarrativeElement]:
        """Return dormant, non-resolved elements."""
        return [e for e in self.elements if e.dormant and not e.resolved]

    def get_active_non_dormant(self) -> list[NarrativeElement]:
        """Return active, non-dormant elements (primary for callback suggestions)."""
        return [e for e in self.elements if not e.resolved and not e.dormant]

    def get_by_relevance(self, limit: int | None = None) -> list[NarrativeElement]:
        """Return active elements sorted by relevance score.

        Relevance = times_referenced * 2 + (1 if not dormant else 0)

        Args:
            limit: Maximum number of elements to return.

        Returns:
            Elements sorted by relevance (highest first).
        """
        active = [e for e in self.elements if not e.resolved]
        scored = sorted(
            active,
            key=lambda e: e.times_referenced * 2 + (1 if not e.dormant else 0),
            reverse=True,
        )
        if limit is not None:
            return scored[:limit]
        return scored
```

#### 3. GameState Enhancement (models.py)

Add `callback_database` field to the `GameState` TypedDict, following the `agent_secrets` pattern:

```python
class GameState(TypedDict):
    # ... existing fields ...
    narrative_elements: dict[str, "NarrativeElementStore"]
    callback_database: "NarrativeElementStore"  # Story 11.2: Campaign-level database
```

Update factory functions:

```python
# In create_initial_game_state():
callback_database=NarrativeElementStore(),

# In populate_game_state():
callback_database=NarrativeElementStore(),
```

#### 4. Campaign-Level Persistence (persistence.py)

Extend serialization following the `agent_secrets` pattern:

```python
# In serialize_game_state():
"callback_database": state.get(
    "callback_database", NarrativeElementStore()
).model_dump(),

# In deserialize_game_state():
# Handle callback_database (Story 11.2)
# Backward compatible: old checkpoints without callback_database get empty store
callback_db_raw = data.get("callback_database", {"elements": []})
if isinstance(callback_db_raw, dict):
    cb_elements = [
        NarrativeElement(**e) for e in callback_db_raw.get("elements", [])
    ]
    callback_database = NarrativeElementStore(elements=cb_elements)
else:
    callback_database = NarrativeElementStore()
```

#### 5. Cross-Session Carry-Over (persistence.py)

Update `initialize_session_with_previous_memories()`:

```python
def initialize_session_with_previous_memories(
    previous_session_id: str,
    new_session_id: str,
    new_state: GameState,
) -> GameState:
    # ... existing memory carry-over code ...

    # Carry over callback_database (Story 11.2)
    prev_callback_db = prev_state.get("callback_database", NarrativeElementStore())
    new_state["callback_database"] = prev_callback_db

    return new_state
```

#### 6. Updated extract_narrative_elements (memory.py)

```python
def extract_narrative_elements(
    state: GameState, turn_content: str, turn_number: int
) -> dict[str, Any]:
    """Extract narrative elements and merge into both session store and campaign database.

    Returns dict with:
    - "narrative_elements": Updated per-session dict
    - "callback_database": Updated campaign-level store
    """
    # ... existing extraction code ...

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

    return {
        "narrative_elements": narrative_elements,
        "callback_database": callback_db_copy,
    }
```

#### 7. Agent Turn Integration (agents.py)

Update the extraction result handling in both `dm_turn()` and `pc_turn()`:

```python
# In dm_turn() and pc_turn(), replace:
#   updated_narrative = extract_narrative_elements(state, response_content, turn_number)
# With:
    extraction_result = extract_narrative_elements(state, response_content, turn_number)
    updated_narrative = extraction_result["narrative_elements"]
    updated_callback_db = extraction_result["callback_database"]

# And include in return dict:
    "callback_database": updated_callback_db,
```

The fallback on exception should also handle callback_database:

```python
except Exception as e:
    logger.warning("Narrative element extraction failed: %s", e)
    updated_narrative = state.get("narrative_elements", {})
    updated_callback_db = state.get("callback_database", NarrativeElementStore())
```

#### 8. Extraction Prompt Enhancement (memory.py)

Add `potential_callbacks` to the JSON format in the prompt:

```python
ELEMENT_EXTRACTION_PROMPT = """You are a narrative analysis assistant for a D&D game.

...existing prompt text...

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
```

Update `_parse_extraction_response()` to pass `potential_callbacks`:

```python
# In _parse_extraction_response(), when building element:
raw_callbacks = item.get("potential_callbacks", [])
if isinstance(raw_callbacks, list):
    potential_callbacks = [str(cb) for cb in raw_callbacks if cb]
elif isinstance(raw_callbacks, str):
    potential_callbacks = [raw_callbacks] if raw_callbacks else []
else:
    potential_callbacks = []

element = create_narrative_element(
    element_type=element_type,
    name=str(item.get("name", "")),
    description=str(item.get("context", item.get("description", ""))),
    turn_introduced=turn_number,
    session_introduced=session_number,
    characters_involved=characters_involved,
    potential_callbacks=potential_callbacks,
)
```

### Key Design Decisions

1. **Campaign-level `callback_database` vs per-session `narrative_elements`:** The epic AC explicitly states "saved with the campaign (not just session)." The per-session `narrative_elements` dict (keyed by session_id) from Story 11-1 is retained for per-session tracking. A new top-level `callback_database` field on `GameState` provides a unified, campaign-spanning view. Elements are merged into both stores during extraction.

2. **Duplicate detection by name (case-insensitive):** When the same NPC or location appears in multiple turns, `add_element()` merges them rather than creating duplicates. This uses the existing `find_by_name()` method which is already case-insensitive.

3. **Dormancy threshold of 20 turns:** Matching the epic AC exactly. This means an element introduced in turn 5 that hasn't been referenced by turn 25 becomes dormant. Dormant elements are not deleted -- they remain available for re-awakening if referenced again.

4. **Immutable state pattern:** Following the existing codebase pattern, `extract_narrative_elements()` returns new copies of the stores rather than mutating state in place. This is critical for LangGraph compatibility.

5. **Backward compatibility everywhere:** All new fields have defaults, all deserialization handles missing fields. Old checkpoints from Story 11-1 (or earlier) will work seamlessly.

6. **Relevance scoring is simple:** `times_referenced * 2 + (1 if not dormant else 0)` is intentionally simple for MVP. Story 11.3 (DM Callback Suggestions) may need more sophisticated scoring, but this provides a useful foundation.

7. **`potential_callbacks` populated during extraction:** The LLM is asked to suggest callback uses at extraction time. This is cheap (already making an LLM call) and provides Story 11.3 with initial callback suggestions without additional API calls.

### Test Strategy

**Test file:** `tests/test_story_11_2_callback_database.py`

**Unit Tests:**
- NarrativeElement new field defaults and validation
- NarrativeElement model_validator (last_referenced_turn defaults to turn_introduced)
- NarrativeElement backward compat (deserialize without new fields)
- NarrativeElementStore.add_element() with new and duplicate elements
- NarrativeElementStore.record_reference() incrementing and re-awakening
- NarrativeElementStore.update_dormancy() threshold behavior
- NarrativeElementStore.get_dormant() and get_active_non_dormant() filtering
- NarrativeElementStore.get_by_relevance() sorting and limit
- create_narrative_element() with potential_callbacks parameter
- _parse_extraction_response() with potential_callbacks in JSON

**Integration Tests:**
- extract_narrative_elements() merges into both session and campaign stores
- Serialization round-trip with callback_database (new field)
- Backward compatibility with old checkpoints (no callback_database)
- Cross-session carry-over of callback_database
- dm_turn/pc_turn propagate callback_database in returned state

**Mock Pattern (follow Story 11-1):**
```python
# Mock the extractor LLM to avoid real API calls
with patch.object(NarrativeElementExtractor, '_get_llm') as mock_llm:
    mock_response = MagicMock()
    mock_response.content = '[{"type": "npc", "name": "Skrix", "context": "...", "potential_callbacks": ["ally", "betrayal"]}]'
    mock_llm.return_value.invoke.return_value = mock_response
```

### Important Constraints

- **Never block the game loop:** All callback database operations must be non-blocking. Extraction failures return unchanged state.
- **Immutable state:** Return new copies from turn functions; never mutate input state in LangGraph nodes.
- **Backward compatibility:** Old checkpoints must load without errors. New fields must have safe defaults.
- **No new dependencies:** Uses existing Pydantic, LangChain, and Python standard library only.
- **No UI changes:** The UI for viewing callback data is Story 11.5. This story is pure model/logic/persistence.
