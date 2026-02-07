# Story 11-4: Callback Detection

## Story

As a **system**,
I want **to detect when callbacks occur**,
So that **the story's interconnectedness can be tracked and celebrated**.

## Status

**Status:** review
**Epic:** 11 - Callback Tracker (Chekhov's Gun)
**Created:** 2026-02-06
**FRs Covered:** FR79 (detect when callbacks occur)
**Predecessors:** Story 11-1 (Narrative Element Extraction) - DONE, Story 11-2 (Callback Database) - DONE, Story 11-3 (DM Callback Suggestions) - DONE

## Acceptance Criteria

**Given** a turn's content
**When** it references a stored narrative element
**Then** the system detects the callback

**Given** callback detection
**When** running
**Then** it uses fuzzy matching on:
- Named entities (NPCs, locations, items)
- Semantic similarity to stored element descriptions

**Given** a callback is detected
**When** confirmed
**Then** the element's reference count increments
**And** the callback is logged with context

**Given** the callback log
**When** maintained
**Then** it tracks: element, turn used, how it was referenced

**Given** a particularly good callback (20+ turns gap)
**When** detected
**Then** it's flagged as a "story moment" for research metrics

## Context: What Stories 11-1, 11-2, and 11-3 Built

### models.py (existing)
- `NarrativeElement` model with fields: `id`, `element_type`, `name`, `description`, `turn_introduced`, `session_introduced`, `turns_referenced` (list[int]), `characters_involved`, `resolved`, `times_referenced`, `last_referenced_turn`, `potential_callbacks` (list[str]), `dormant`
- `NarrativeElementStore` with methods: `get_active()`, `get_by_type()`, `find_by_name()`, `add_element()`, `record_reference()`, `update_dormancy()`, `get_dormant()`, `get_active_non_dormant()`, `get_by_relevance(limit)`, `get_all()`
- `create_narrative_element()` factory function with `potential_callbacks` parameter
- `GameState` has `narrative_elements: dict[str, NarrativeElementStore]` keyed by session_id
- `GameState` has `callback_database: NarrativeElementStore` (campaign-level, Story 11.2)

### memory.py (existing)
- `NarrativeElementExtractor` class with lazy LLM initialization
- `extract_narrative_elements()` returns `ExtractionResult` with both session and campaign stores
- `_parse_extraction_response()` helper for JSON parsing
- `ELEMENT_EXTRACTION_PROMPT` constant
- `_extractor_cache` for instance caching

### agents.py (existing)
- `dm_turn()` calls `extract_narrative_elements()` after DM response
- `pc_turn()` calls `extract_narrative_elements()` after PC response
- Both gracefully handle extraction failures
- `score_callback_relevance()` and `format_callback_suggestions()` for DM context
- `_build_dm_context()` includes callback suggestions section

### persistence.py (existing)
- `serialize_game_state()` / `deserialize_game_state()` handle `callback_database`
- `initialize_session_with_previous_memories()` carries over `callback_database`

## What Story 11.4 Changes

This story adds **callback detection** -- the ability to detect when a turn's content references a previously-stored narrative element. Specifically:

1. **New model `CallbackEntry`** in models.py: Records a single detected callback with element reference, turn context, match type, and "story moment" flag.
2. **New model `CallbackLog`** in models.py: Container for all detected callbacks with query methods.
3. **New field `callback_log: CallbackLog`** on `GameState`: Tracks all callbacks across the campaign.
4. **New function `detect_callbacks()`** in memory.py: Scans turn content against all active narrative elements using name matching and description similarity.
5. **Integration into `extract_narrative_elements()`** in memory.py: After element extraction, run callback detection on the same turn content against the callback database.
6. **Persistence** for the callback log in persistence.py.
7. **"Story moment" flagging**: Callbacks with a 20+ turn gap between introduction and reference are flagged for research metrics.

The detection uses two matching strategies:
- **Name matching** (exact and fuzzy): Case-insensitive substring matching for entity names (NPCs, locations, items). Handles partial matches (e.g., "Skrix" matches "Skrix the Goblin") and word-boundary-aware matching.
- **Description keyword matching**: Extracts significant keywords from element descriptions and checks if they appear in the turn content. This provides lightweight semantic similarity without requiring embedding models or additional LLM calls.

## Tasks

### 1. Add CallbackEntry Model (models.py)

1. [x]Add `CallbackEntry` Pydantic model to models.py
   - Fields:
     - `id: str` - Unique identifier (UUID hex, matching Whisper/NarrativeElement pattern)
     - `element_id: str` - ID of the NarrativeElement that was referenced
     - `element_name: str` - Name of the element (denormalized for display)
     - `element_type: str` - Type of the element (denormalized for display)
     - `turn_detected: int` - Turn number where callback was detected
     - `turn_gap: int` - Gap between element's `last_referenced_turn` and `turn_detected`
     - `match_type: Literal["name_exact", "name_fuzzy", "description_keyword"]` - How the callback was matched
     - `match_context: str` - Excerpt from turn content showing the reference (max 200 chars)
     - `is_story_moment: bool` - True if turn_gap >= 20 (Chekhov's Gun payoff)
     - `session_detected: int` - Session number when callback was detected
   - Docstring referencing Story 11.4, FR79
   - Validator: `turn_detected >= 0`, `turn_gap >= 0`
2. [x]Add `CallbackEntry` to `__all__` exports in models.py

### 2. Add CallbackLog Model (models.py)

3. [x]Add `CallbackLog` Pydantic model to models.py
   - Fields:
     - `entries: list[CallbackEntry]` - All detected callback entries
   - Methods:
     - `add_entry(entry: CallbackEntry) -> None` - Append a new entry
     - `get_by_element(element_id: str) -> list[CallbackEntry]` - Filter by element
     - `get_story_moments() -> list[CallbackEntry]` - Return entries where `is_story_moment=True`
     - `get_by_turn(turn_number: int) -> list[CallbackEntry]` - Filter by turn
     - `get_recent(limit: int = 10) -> list[CallbackEntry]` - Most recent entries
   - `STORY_MOMENT_THRESHOLD: ClassVar[int] = 20` - Class constant for the gap threshold
   - Docstring referencing Story 11.4, FR79
4. [x]Add `CallbackLog` to `__all__` exports in models.py

### 3. Add Factory Function (models.py)

5. [x]Add `create_callback_entry()` factory function
   - Accepts: `element: NarrativeElement`, `turn_detected: int`, `match_type`, `match_context: str`, `session_detected: int`
   - Computes `turn_gap` from `element.last_referenced_turn` and `turn_detected`
   - Computes `is_story_moment` from `turn_gap >= CallbackLog.STORY_MOMENT_THRESHOLD`
   - Generates UUID for `id`
   - Denormalizes `element_name` and `element_type` from the element
   - Returns `CallbackEntry`
6. [x]Add `create_callback_entry` to `__all__` exports in models.py

### 4. Update GameState (models.py)

7. [x]Add `callback_log: CallbackLog` field to `GameState` TypedDict
8. [x]Update `create_initial_game_state()` to initialize `callback_log=CallbackLog()`
9. [x]Update `populate_game_state()` to initialize `callback_log=CallbackLog()`

### 5. Add Callback Detection Logic (memory.py)

10. [x]Add `CALLBACK_NAME_MIN_LENGTH` constant to memory.py
    - Value: `3` (skip name matching for very short names to avoid false positives)
11. [x]Add `CALLBACK_MATCH_CONTEXT_LENGTH` constant to memory.py
    - Value: `200` (max chars of surrounding context to capture for match_context)
12. [x]Add `_normalize_text()` helper function to memory.py
    - Lowercase, strip punctuation, collapse whitespace
    - Used for consistent text comparison in both name and keyword matching
13. [x]Add `_extract_match_context()` helper function to memory.py
    - Given full turn text and a matched substring position, extract surrounding context
    - Returns up to `CALLBACK_MATCH_CONTEXT_LENGTH` chars centered around the match
    - Adds "..." ellipsis if truncated
14. [x]Add `_detect_name_match()` function to memory.py
    - Accepts: `element: NarrativeElement`, `normalized_content: str`, `raw_content: str`
    - Performs case-insensitive matching of element name against turn content
    - Match strategies (in order of priority):
      1. **Exact match**: Full element name appears in content (case-insensitive)
      2. **Fuzzy/partial match**: For multi-word names, check if the most distinctive word (longest word in name, min 3 chars) appears as a standalone word in content
    - Skips elements with names shorter than `CALLBACK_NAME_MIN_LENGTH`
    - Returns `tuple[str, str] | None` - `(match_type, match_context)` or None if no match
    - match_type is "name_exact" or "name_fuzzy"
15. [x]Add `_detect_description_match()` function to memory.py
    - Accepts: `element: NarrativeElement`, `normalized_content: str`, `raw_content: str`
    - Extracts significant keywords from element description (words >= 4 chars, excluding stop words)
    - Checks if 2+ significant keywords appear in turn content
    - Returns `tuple[str, str] | None` - `("description_keyword", match_context)` or None
    - Stop words list: common D&D/English words that would cause false positives (the, and, that, with, from, they, their, this, have, been, were, will, into, when, then, about, some, what, more, also, very, just, like, only, back, over, such, after, each, most, also, much)
16. [x]Add `detect_callbacks()` function to memory.py
    - Signature: `detect_callbacks(turn_content: str, turn_number: int, session_number: int, callback_database: NarrativeElementStore) -> list[CallbackEntry]`
    - Gets active (non-resolved) elements from callback_database
    - For each element, tries name matching first, then description matching
    - Skips elements introduced on the current turn (self-references)
    - Skips elements that were already referenced on this turn in `turns_referenced` (avoid double-counting from extraction)
    - Creates `CallbackEntry` for each detected callback via `create_callback_entry()`
    - Logs story moments at INFO level ("Story moment detected: {element_name} referenced after {turn_gap} turns!")
    - Returns list of `CallbackEntry` (empty list if no callbacks detected)
    - Wrapped in try/except for graceful degradation (never raises)
17. [x]Add `detect_callbacks` to `__all__` exports in memory.py

### 6. Integrate Detection into Extraction Pipeline (memory.py)

18. [x]Update `ExtractionResult` TypedDict to include `callback_log: CallbackLog`
19. [x]Update `extract_narrative_elements()` to run callback detection
    - After extracting elements and merging into callback_database, run `detect_callbacks()` on the turn content against the updated callback_database
    - For each detected callback, call `callback_database.record_reference()` to increment the element's reference count
    - Merge detected callbacks into a copy of the existing `callback_log` from state
    - Include updated `callback_log` in the returned `ExtractionResult`
20. [x]Handle the callback_log in the fallback path (when extraction fails)

### 7. Update Agent Integration (agents.py)

21. [x]Update `dm_turn()` to propagate `callback_log` from extraction result into returned state
    - Extract `updated_callback_log` from `extraction_result["callback_log"]`
    - Include in returned `GameState` constructor
    - Handle fallback (extraction failure): use `state.get("callback_log", CallbackLog())`
22. [x]Update `pc_turn()` with same pattern as dm_turn for callback_log propagation
23. [x]Add `CallbackEntry`, `CallbackLog` to the imports from models in agents.py

### 8. Update Persistence (persistence.py)

24. [x]Update `serialize_game_state()` to serialize `callback_log`
    - Pattern: `"callback_log": state.get("callback_log", CallbackLog()).model_dump()`
25. [x]Update `deserialize_game_state()` to reconstruct `CallbackLog`
    - Backward compatible: old checkpoints without `callback_log` get empty `CallbackLog()`
    - Reconstruct `CallbackEntry` objects from raw dicts
26. [x]Add `CallbackLog`, `CallbackEntry` to imports from models in persistence.py
27. [x]Update `initialize_session_with_previous_memories()` to carry over `callback_log`
    - Copy callback_log from previous session to new session (cross-session tracking)

### 9. Tests

28. [x]Test `CallbackEntry` model validation
    - Valid construction with all fields
    - Default values correct (is_story_moment=False)
    - turn_detected >= 0 validation
    - turn_gap >= 0 validation
    - match_type restricted to literal values
29. [x]Test `CallbackLog` model and methods
    - `add_entry()` appends to entries list
    - `get_by_element()` filters correctly by element_id
    - `get_story_moments()` returns only entries with is_story_moment=True
    - `get_by_turn()` filters by turn number
    - `get_recent()` returns most recent entries with limit
    - Empty log returns empty lists for all queries
30. [x]Test `create_callback_entry()` factory function
    - Generates unique UUID id
    - Computes turn_gap correctly
    - Flags story moment when turn_gap >= 20
    - Does not flag story moment when turn_gap < 20
    - Denormalizes element_name and element_type from element
31. [x]Test `_normalize_text()` helper
    - Lowercase conversion
    - Punctuation stripping
    - Whitespace collapsing
32. [x]Test `_extract_match_context()` helper
    - Extracts surrounding context around match position
    - Respects max length
    - Adds ellipsis when truncated
    - Handles match at beginning/end of text
33. [x]Test `_detect_name_match()` function
    - Exact name match (case-insensitive) detected
    - Fuzzy partial match (longest distinctive word) detected
    - Short names (< 3 chars) skipped
    - Name not present returns None
    - Multi-word name: distinctive word match vs common word not matching
    - Returns correct match_type and match_context
34. [x]Test `_detect_description_match()` function
    - 2+ significant keywords present: match detected
    - Only 1 keyword present: no match (threshold not met)
    - Stop words excluded from keyword extraction
    - Empty description returns None
    - Short description (no significant keywords) returns None
    - Returns "description_keyword" match type
35. [x]Test `detect_callbacks()` function
    - Detects name-based callback on active element
    - Detects description-keyword callback on active element
    - Skips resolved elements
    - Skips elements introduced on current turn (self-reference)
    - Skips elements already referenced on this turn (no double-count)
    - Name match takes priority over description match (no duplicates)
    - Story moment flagged for 20+ turn gap
    - Story moment not flagged for < 20 turn gap
    - Empty content returns empty list
    - Empty callback_database returns empty list
    - Graceful degradation on error (returns empty list, no exception)
36. [x]Test `extract_narrative_elements()` integration with callback detection
    - Extraction result includes updated callback_log with detected callbacks
    - record_reference called on callback_database for detected callbacks
    - Callback log accumulates across multiple calls
    - Detection failure does not block extraction
37. [x]Test `dm_turn()` propagates callback_log in returned state
    - callback_log included in returned GameState
    - Extraction failure fallback includes callback_log from existing state
38. [x]Test `pc_turn()` propagates callback_log in returned state
    - Same pattern as dm_turn
39. [x]Test persistence round-trip for callback_log
    - serialize -> deserialize preserves all CallbackEntry fields
    - Backward compatibility: old checkpoints without callback_log
40. [x]Test cross-session carry-over of callback_log
    - `initialize_session_with_previous_memories()` carries over callback_log
41. [x]Test end-to-end callback detection scenario
    - Create elements at turn 5, content at turn 30 references element name
    - Verify callback detected, story moment flagged (gap=25), reference count incremented

## Dependencies

- **Story 11-1** (done): Provides `NarrativeElement`, `NarrativeElementStore` models, extraction pipeline
- **Story 11-2** (done): Provides `callback_database` on `GameState`, `record_reference()`, `add_element()`, dormancy tracking
- **Story 11-3** (done): Provides callback scoring/formatting pattern (read-only, this story modifies state)
- **Story 4.1** (done): Provides checkpoint serialization patterns
- **Story 5.4** (done): Provides `initialize_session_with_previous_memories()` for cross-session carry-over

## Dev Notes

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `models.py` | Modify | Add `CallbackEntry`, `CallbackLog` models, `create_callback_entry()` factory, add `callback_log` to `GameState`, update factory functions, update `__all__` |
| `memory.py` | Modify | Add `detect_callbacks()`, name/description matching helpers, `_normalize_text()`, `_extract_match_context()`, integrate into `extract_narrative_elements()`, update `ExtractionResult`, update `__all__` |
| `agents.py` | Modify | Update `dm_turn()` and `pc_turn()` to propagate `callback_log`, add `CallbackLog` import |
| `persistence.py` | Modify | Add `callback_log` serialization/deserialization, update cross-session carry-over, add `CallbackLog`/`CallbackEntry` imports |
| `tests/test_story_11_4_callback_detection.py` | Create | Comprehensive unit and integration tests |

### Code Patterns to Follow

#### 1. CallbackEntry Model (follow Whisper pattern in models.py)

```python
class CallbackEntry(BaseModel):
    """A detected callback where turn content references a stored narrative element.

    Story 11.4: Callback Detection.
    FR79: System can detect when callbacks occur.

    Attributes:
        id: Unique identifier (UUID hex string).
        element_id: ID of the NarrativeElement that was referenced.
        element_name: Name of the element (denormalized for display).
        element_type: Type of the element (denormalized for display).
        turn_detected: Turn number where callback was detected.
        turn_gap: Number of turns between last reference and this detection.
        match_type: How the callback was matched.
        match_context: Excerpt from turn content showing the reference.
        is_story_moment: True if turn_gap >= 20 (Chekhov's Gun payoff).
        session_detected: Session number when callback was detected.
    """

    id: str = Field(..., min_length=1, description="Unique entry ID (UUID hex)")
    element_id: str = Field(..., min_length=1, description="Referenced NarrativeElement ID")
    element_name: str = Field(..., min_length=1, description="Element name (denormalized)")
    element_type: str = Field(..., description="Element type (denormalized)")
    turn_detected: int = Field(..., ge=0, description="Turn when callback detected")
    turn_gap: int = Field(..., ge=0, description="Turns since element last referenced")
    match_type: Literal["name_exact", "name_fuzzy", "description_keyword"] = Field(
        ..., description="How the callback was matched"
    )
    match_context: str = Field(
        default="", description="Excerpt from turn content showing reference"
    )
    is_story_moment: bool = Field(
        default=False, description="True if turn_gap >= 20 (Chekhov's Gun)"
    )
    session_detected: int = Field(
        default=1, ge=1, description="Session when callback was detected"
    )
```

Use `uuid.uuid4().hex` for ID generation in factory function, matching `create_whisper()` pattern.

#### 2. CallbackLog Model (follow NarrativeElementStore/AgentSecrets pattern)

```python
class CallbackLog(BaseModel):
    """Container for detected callback entries.

    Tracks all detected callbacks across the campaign for research
    metrics and UI display.

    Story 11.4: Callback Detection.
    FR79: System can detect when callbacks occur.

    Attributes:
        entries: List of all detected callback entries.
    """

    STORY_MOMENT_THRESHOLD: ClassVar[int] = 20  # Turn gap for "story moment"

    entries: list[CallbackEntry] = Field(
        default_factory=list, description="All detected callback entries"
    )

    def add_entry(self, entry: CallbackEntry) -> None:
        """Append a new callback entry."""
        self.entries.append(entry)

    def get_by_element(self, element_id: str) -> list[CallbackEntry]:
        """Get all callbacks for a specific element."""
        return [e for e in self.entries if e.element_id == element_id]

    def get_story_moments(self) -> list[CallbackEntry]:
        """Get callbacks flagged as story moments (20+ turn gap)."""
        return [e for e in self.entries if e.is_story_moment]

    def get_by_turn(self, turn_number: int) -> list[CallbackEntry]:
        """Get callbacks detected at a specific turn."""
        return [e for e in self.entries if e.turn_detected == turn_number]

    def get_recent(self, limit: int = 10) -> list[CallbackEntry]:
        """Get most recent callback entries."""
        sorted_entries = sorted(
            self.entries, key=lambda e: e.turn_detected, reverse=True
        )
        return sorted_entries[:limit]
```

#### 3. GameState Enhancement (models.py)

Add `callback_log` field to `GameState` TypedDict, following the `callback_database` pattern:

```python
class GameState(TypedDict):
    # ... existing fields ...
    callback_database: "NarrativeElementStore"
    callback_log: "CallbackLog"  # Story 11.4: Detected callback log
```

Update factory functions:

```python
# In create_initial_game_state():
callback_log=CallbackLog(),

# In populate_game_state():
callback_log=CallbackLog(),
```

#### 4. Name Matching Detection (memory.py)

```python
import re

CALLBACK_NAME_MIN_LENGTH = 3  # Skip very short names to avoid false positives
CALLBACK_MATCH_CONTEXT_LENGTH = 200  # Max chars for match context excerpt

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

    # Exact match: full name appears in content
    if normalized_name in normalized_content:
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
        distinctive_words = sorted(
            [w for w in words if len(w) >= CALLBACK_NAME_MIN_LENGTH],
            key=len,
            reverse=True,
        )
        for word in distinctive_words:
            # Word boundary matching to avoid substring false positives
            pattern = r"\b" + re.escape(word) + r"\b"
            match = re.search(pattern, normalized_content)
            if match:
                pos = match.start()
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

    # Extract significant keywords (>= 4 chars, not stop words)
    desc_words = _normalize_text(element.description).split()
    keywords = [
        w for w in desc_words
        if len(w) >= 4 and w not in _DESCRIPTION_STOP_WORDS
    ]

    if len(keywords) < 2:
        return None  # Not enough keywords to match against

    # Check how many keywords appear in content
    matched_keywords: list[str] = []
    first_match_pos = -1
    for keyword in keywords:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        match = re.search(pattern, normalized_content)
        if match:
            matched_keywords.append(keyword)
            if first_match_pos == -1:
                first_match_pos = match.start()

    # Require 2+ keyword matches for confidence
    if len(matched_keywords) >= 2:
        context = _extract_match_context(raw_content, max(0, first_match_pos))
        return ("description_keyword", context)

    return None
```

#### 5. detect_callbacks() Function (memory.py)

```python
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
        from models import create_callback_entry

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
                match_type, match_context = match_result
                entry = create_callback_entry(
                    element=element,
                    turn_detected=turn_number,
                    match_type=match_type,
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
```

#### 6. Updated extract_narrative_elements (memory.py)

Update `ExtractionResult` and `extract_narrative_elements()`:

```python
class ExtractionResult(TypedDict):
    """Return type for extract_narrative_elements.

    Story 11.2: Session and campaign stores.
    Story 11.4: Callback detection log.
    """
    narrative_elements: dict[str, NarrativeElementStore]
    callback_database: NarrativeElementStore
    callback_log: CallbackLog  # Story 11.4


def extract_narrative_elements(
    state: GameState, turn_content: str, turn_number: int
) -> ExtractionResult:
    # ... existing extraction code ...

    # Detect callbacks in turn content (Story 11.4)
    session_number = ...  # Extract from session_id
    detected_callbacks = detect_callbacks(
        turn_content, turn_number, session_number, callback_db_copy
    )

    # Record references for detected callbacks in callback_database
    for cb_entry in detected_callbacks:
        callback_db_copy.record_reference(cb_entry.element_id, turn_number)

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
```

#### 7. Agent Turn Integration (agents.py)

Update dm_turn() and pc_turn() to propagate callback_log:

```python
# In dm_turn() and pc_turn(), extraction result handling:
    extraction_result = extract_narrative_elements(state, response_content, turn_number)
    updated_narrative = extraction_result["narrative_elements"]
    updated_callback_db = extraction_result["callback_database"]
    updated_callback_log = extraction_result["callback_log"]

# And in the fallback:
except Exception as e:
    logger.warning("Narrative element extraction failed: %s", e)
    updated_narrative = state.get("narrative_elements", {})
    updated_callback_db = state.get("callback_database", NarrativeElementStore())
    updated_callback_log = state.get("callback_log", CallbackLog())

# Include in returned GameState:
    callback_log=updated_callback_log,
```

#### 8. Persistence (persistence.py)

Extend serialization following the `callback_database` pattern:

```python
# In serialize_game_state():
"callback_log": state.get("callback_log", CallbackLog()).model_dump(),

# In deserialize_game_state():
callback_log_raw = data.get("callback_log", {"entries": []})
if isinstance(callback_log_raw, dict):
    cb_entries = [
        CallbackEntry(**e) for e in callback_log_raw.get("entries", [])
    ]
    callback_log = CallbackLog(entries=cb_entries)
else:
    callback_log = CallbackLog()
```

Cross-session carry-over:

```python
# In initialize_session_with_previous_memories():
prev_callback_log = prev_state.get("callback_log", CallbackLog())
new_state["callback_log"] = CallbackLog(
    entries=list(prev_callback_log.entries)
)
```

### Key Design Decisions

1. **No LLM calls for detection:** Callback detection uses purely heuristic matching (name matching + keyword matching). This is fast, deterministic, and free -- no API calls needed. The LLM is already used for element extraction (Story 11.1), and that output provides the structured data for detection. Using a second LLM call for detection would double the latency and cost per turn with marginal accuracy improvement.

2. **Name matching with fuzzy fallback:** Exact name matching catches "Skrix the Goblin" directly. Fuzzy matching catches when content mentions just "Skrix" without the full title. The longest distinctive word strategy avoids matching on common words like "the" or "old" that might appear in a name like "The Old Bridge".

3. **Description keyword matching as secondary strategy:** When name matching fails, keywords from the element description can still detect thematic callbacks. For example, if an element has description "befriended goblin who promised cave information" and the turn mentions "goblin" and "cave" and "promise", that suggests a callback even without the exact name. The 2-keyword threshold prevents false positives from single common words.

4. **Story moment threshold matches dormancy threshold (20 turns):** This is intentional per the epic AC. A callback with a 20+ turn gap is both a "story moment" (impressive callback) and would re-awaken a dormant element. These are the Chekhov's Gun payoffs -- a detail planted early that fires much later.

5. **Denormalized element_name and element_type in CallbackEntry:** The entry stores copies of the element's name and type rather than just the element_id. This avoids needing to look up the element every time a callback is displayed, and preserves the name even if the element is later resolved or modified.

6. **One match per element per turn:** If both name and description matching would fire for the same element in the same turn, only the name match (higher confidence) is recorded. This prevents inflating the reference count.

7. **Skips self-references and already-counted turns:** Elements introduced on the current turn are skipped (the extraction in Story 11.1 already handled the introduction). Elements already referenced on this turn in `turns_referenced` are also skipped to prevent double-counting between extraction and detection.

8. **Graceful degradation:** Like all non-critical subsystems, detection failure logs a warning and returns an empty list. It never blocks the game loop.

9. **No new dependencies:** Uses only Python standard library (`re`, `uuid`) and existing Pydantic/models infrastructure. No embedding models, no similarity libraries, no new packages.

10. **Callback log carried across sessions:** Like `callback_database`, the `callback_log` is carried over via `initialize_session_with_previous_memories()`. This enables viewing the full callback history across a campaign.

### Test Strategy

**Test file:** `tests/test_story_11_4_callback_detection.py`

**Unit Tests:**

- `CallbackEntry` model: valid construction, default values, validators
- `CallbackLog` model: add_entry, get_by_element, get_story_moments, get_by_turn, get_recent, empty log behavior
- `create_callback_entry()`: UUID generation, turn_gap computation, story moment flagging
- `_normalize_text()`: lowercase, punctuation, whitespace
- `_extract_match_context()`: centered extraction, ellipsis, edge positions
- `_detect_name_match()`: exact match, fuzzy match, short name skip, no match
- `_detect_description_match()`: 2+ keywords match, 1 keyword no match, stop words, empty description
- `detect_callbacks()`: full detection pipeline with various scenarios

**Integration Tests:**

- `extract_narrative_elements()` with callback detection included
- `dm_turn()`/`pc_turn()` propagate callback_log
- Serialization round-trip (callback_log preservation)
- Cross-session carry-over
- End-to-end scenario (create element, later turn references it, verify callback + story moment)

**Mock Pattern (follow existing test patterns):**

```python
from models import (
    CallbackEntry,
    CallbackLog,
    NarrativeElement,
    NarrativeElementStore,
    create_callback_entry,
    create_narrative_element,
)

# Create test element
element = create_narrative_element(
    element_type="character",
    name="Skrix the Goblin",
    description="Befriended by party, promised cave information",
    turn_introduced=5,
    session_introduced=1,
    characters_involved=["Shadowmere"],
)

# Build test store
store = NarrativeElementStore(elements=[element])

# Test detection
from memory import detect_callbacks
callbacks = detect_callbacks(
    "The party spots Skrix the Goblin waving from the cave entrance.",
    turn_number=30,
    session_number=1,
    callback_database=store,
)
assert len(callbacks) == 1
assert callbacks[0].match_type == "name_exact"
assert callbacks[0].is_story_moment  # gap = 25 >= 20
assert callbacks[0].element_name == "Skrix the Goblin"
```

No LLM mocking needed for callback detection since all matching is purely heuristic. LLM mocking is only needed if testing the full `extract_narrative_elements()` pipeline (which calls the extractor LLM).

### Important Constraints

- **Never block the game loop:** Detection failures must be silent (logged but not raised)
- **No new dependencies:** Uses only existing imports (re, uuid, Pydantic models)
- **Immutable state:** Return new copies from turn functions; never mutate input state in LangGraph nodes
- **Backward compatibility:** Old checkpoints without `callback_log` must load without errors (empty `CallbackLog()` default)
- **No UI changes:** The UI for viewing callbacks is Story 11.5. This story is pure model/logic/persistence
- **Performance:** Detection is O(n*m) where n = active elements and m = content length. For typical games (< 100 elements, < 10K chars per turn), this is fast (< 1ms). No optimization needed for MVP
- **No false positive inflation:** One detection per element per turn, skip self-references and already-counted turns
