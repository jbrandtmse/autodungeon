# Story 11-3: DM Callback Suggestions

## Story

As a **DM agent**,
I want **suggestions for callbacks in my context**,
So that **I can weave earlier story threads into current narrative**.

## Status

**Status:** review
**Epic:** 11 - Callback Tracker (Chekhov's Gun)
**Created:** 2026-02-06
**FRs Covered:** FR78 (DM context includes callback suggestions)
**Predecessors:** Story 11-1 (Narrative Element Extraction) - DONE, Story 11-2 (Callback Database) - DONE

## Acceptance Criteria

**Given** the DM's prompt context
**When** built
**Then** a "Callback Opportunities" section is included

**Given** callback suggestions
**When** formatted
**Then** they appear as:
```
## Callback Opportunities
Consider weaving in these earlier story elements:

1. **Skrix the Goblin** (Turn 15, Session 2)
   The party befriended this goblin who promised cave information.
   Potential use: He could appear with the promised info, or be in danger.

2. **The Broken Amulet** (Turn 42, Session 3)
   Elara found half an amulet. The other half's location is unknown.
   Potential use: A merchant could have the other half.
```

**Given** callback suggestions
**When** selected
**Then** they prioritize:
- High relevance to current scene
- Longer time since last reference (more impactful callback)
- Character involvement (if that character is active)

**Given** the DM uses a callback
**When** generating response
**Then** it doesn't have to use suggestions (just inspiration)

**Given** no callback-worthy elements exist
**When** the context is built
**Then** the "Callback Opportunities" section is omitted entirely (no empty section)

**Given** the callback suggestions section
**When** added to DM context
**Then** it does not cause the DM context to exceed reasonable token bounds (limit to top N suggestions)

## Context: What Stories 11-1 and 11-2 Built

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
- `MemoryManager._build_dm_context()` builds DM memory context (in memory.py)
- `MemoryManager` class with `get_context()` dispatching to `_build_dm_context()` or `_build_pc_context()`

### agents.py (existing)
- `_build_dm_context(state)` at line 1078: builds full DM context string with sections for Story So Far, Recent Events, Party Members, Character Sheets, Player Knowledge, Active Secrets, Player Suggestion, Player Whisper
- `dm_turn(state)` at line 1239: builds system prompt, appends context, invokes DM LLM
- `DM_SYSTEM_PROMPT` at line 93: includes "Narrative Continuity" section encouraging callbacks

### persistence.py (existing)
- `serialize_game_state()` / `deserialize_game_state()` handle `callback_database`

## What Story 11.3 Changes

This story adds a **callback suggestions section** to the DM's prompt context. Specifically:

1. **New function `format_callback_suggestions()`** in agents.py: Takes the `callback_database` from state, scores and ranks elements for callback potential, and formats them into a markdown section matching the epic AC format.
2. **New scoring function `score_callback_relevance()`** in agents.py: Computes a callback score based on time since last reference, character involvement, and element importance. This extends the simple `get_by_relevance()` scoring from Story 11.2 with scene-aware prioritization.
3. **Integration into `_build_dm_context()`** in agents.py: Adds the formatted callback suggestions section after the existing sections (Player Knowledge, Active Secrets, etc.).
4. **Configuration constants** for max suggestions count and minimum score threshold.

The DM is explicitly told these are optional inspiration -- it is free to use or ignore them.

## Tasks

### 1. Add Callback Suggestion Scoring (agents.py)

1. [x] Add `MAX_CALLBACK_SUGGESTIONS` constant to agents.py
   - Value: `5` (limit context bloat; top 5 most relevant callbacks)
   - Add to `__all__` exports
2. [x] Add `MIN_CALLBACK_SCORE` constant to agents.py
   - Value: `0.0` (include all scored elements; filtering is by limit not threshold for MVP)
   - Add to `__all__` exports
3. [x] Add `score_callback_relevance()` function to agents.py
   - Signature: `score_callback_relevance(element: NarrativeElement, current_turn: int, active_characters: list[str]) -> float`
   - Scoring formula (higher = better callback candidate):
     - **Recency gap bonus**: `min((current_turn - element.last_referenced_turn) / 10.0, 5.0)` -- Elements unreferenced for longer are more impactful when called back (capped at 5.0 to prevent dormant elements from dominating)
     - **Character involvement bonus**: `+2.0` if any of the element's `characters_involved` are in `active_characters` (the current party members)
     - **Importance bonus**: `element.times_referenced * 0.5` -- More-referenced elements are more established in the narrative
     - **Has potential callbacks bonus**: `+1.0` if `element.potential_callbacks` is non-empty (AI already suggested uses)
     - **Dormancy penalty**: `-3.0` if `element.dormant` is True (still included but deprioritized)
   - Returns float score
   - Elements with `resolved=True` are excluded before scoring (handled by caller)
4. [x] Add `score_callback_relevance` to `__all__` exports

### 2. Add Callback Suggestion Formatting (agents.py)

5. [x] Add `format_callback_suggestions()` function to agents.py
   - Signature: `format_callback_suggestions(callback_database: NarrativeElementStore, current_turn: int, active_characters: list[str]) -> str`
   - Gets active (non-resolved) elements from callback_database via `get_active()`
   - Scores each element using `score_callback_relevance()`
   - Sorts by score descending
   - Takes top `MAX_CALLBACK_SUGGESTIONS` elements
   - Returns empty string if no elements qualify (no empty section)
   - Formats output matching epic AC:
     ```
     ## Callback Opportunities
     Consider weaving in these earlier story elements:

     1. **Skrix the Goblin** (Turn 15, Session 2)
        The party befriended this goblin who promised cave information.
        Potential use: He could appear with the promised info, or be in danger.
     ```
   - Each entry includes: name (bold), turn_introduced, session_introduced, description, and first `potential_callbacks` entry as "Potential use:" line (or omits if none)
6. [x] Add `format_callback_suggestions` to `__all__` exports

### 3. Integrate into DM Context Builder (agents.py)

7. [x] Update `_build_dm_context(state)` function in agents.py
   - After the existing "Active Secrets" section (around line 1139), add callback suggestions
   - Extract `callback_database` from state: `state.get("callback_database", NarrativeElementStore())`
   - Determine `current_turn` from `len(state.get("ground_truth_log", []))`
   - Determine `active_characters` from `state["turn_queue"]` (all agents except "dm")
   - Call `format_callback_suggestions(callback_database, current_turn, active_characters)`
   - If non-empty result, append to `context_parts`
   - Import `NarrativeElementStore` from models at the top of agents.py (add to existing imports)
8. [x] Add `NarrativeElementStore` to the imports in agents.py
   - Add to the `from models import (...)` block at top of file

### 4. Update DM System Prompt for Callback Awareness (agents.py)

9. [x] Add a brief note to the "Narrative Continuity" section of `DM_SYSTEM_PROMPT`
   - After the existing bullet points about referencing earlier events, add:
     ```
     - Check the "Callback Opportunities" section in your context for specific story threads to weave in
     - These suggestions are optional inspiration - use them when they fit naturally, ignore when they don't
     ```
   - This tells the DM where to look and that the suggestions are non-binding

### 5. Tests

10. [x] Add unit tests for `score_callback_relevance()`
    - Element with high recency gap scores higher than recent element
    - Element with active character involvement gets +2.0 bonus
    - Element referenced many times gets importance bonus
    - Element with potential_callbacks gets +1.0 bonus
    - Dormant element gets -3.0 penalty
    - Resolved elements should not be passed in (tested at caller level)
    - Edge case: current_turn equals last_referenced_turn (score 0 for recency)
    - Edge case: empty active_characters list (no character bonus)
11. [x] Add unit tests for `format_callback_suggestions()`
    - Empty callback_database returns empty string
    - Single element formats correctly with name, turn, session, description
    - Multiple elements sorted by score (highest first)
    - Respects MAX_CALLBACK_SUGGESTIONS limit (top N only)
    - Element with potential_callbacks includes "Potential use:" line
    - Element without potential_callbacks omits "Potential use:" line
    - All resolved elements filtered out (returns empty string)
    - Dormant elements included but scored lower
    - Format matches epic AC example structure
12. [x] Add unit tests for `_build_dm_context()` callback integration
    - State with callback_database: context includes "Callback Opportunities" section
    - State with empty callback_database: context does NOT include "Callback Opportunities"
    - State without callback_database key: gracefully defaults to empty (no crash)
    - Callback section appears after Active Secrets section (ordering check)
    - Verify active_characters correctly excludes "dm" from turn_queue
13. [x] Add integration test for end-to-end DM context with callbacks
    - Create a state with populated callback_database (3+ elements of varying types)
    - Verify full DM context string contains formatted callback section
    - Verify elements are ordered by relevance score
    - Verify format matches epic AC template

## Dependencies

- **Story 11-1** (done): Provides `NarrativeElement`, `NarrativeElementStore` models
- **Story 11-2** (done): Provides `callback_database` on `GameState`, `get_active()`, `get_by_relevance()`, `potential_callbacks` field, dormancy tracking
- **Story 5.1** (done): Provides `_build_dm_context()` pattern for context building
- **Story 10.3** (done): Provides `format_all_secrets_context()` pattern for DM context sections

## Dev Notes

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `agents.py` | Modify | Add `score_callback_relevance()`, `format_callback_suggestions()`, update `_build_dm_context()`, update `DM_SYSTEM_PROMPT`, add `NarrativeElementStore` import, add constants |
| `tests/test_story_11_3_dm_callback_suggestions.py` | Create | Comprehensive unit and integration tests |

### Code Patterns to Follow

#### 1. Callback Relevance Scoring (agents.py)

Follow the simple scoring pattern established in `NarrativeElementStore.get_by_relevance()` (models.py line 717-738), but extend it with scene-aware dimensions:

```python
def score_callback_relevance(
    element: NarrativeElement,
    current_turn: int,
    active_characters: list[str],
) -> float:
    """Score a narrative element for callback suggestion relevance.

    Higher scores indicate better candidates for DM callback suggestions.
    The scoring considers:
    - How long since the element was last referenced (longer gap = more impactful)
    - Whether involved characters are currently active
    - How established the element is in the narrative
    - Whether AI-suggested callback uses exist
    - Whether the element is dormant (penalty)

    Story 11.3: DM Callback Suggestions.
    FR78: DM context includes callback suggestions.

    Args:
        element: The NarrativeElement to score.
        current_turn: Current turn number for recency calculation.
        active_characters: List of currently active character names (from turn_queue).

    Returns:
        Float score (higher = better callback candidate).
    """
    score = 0.0

    # Recency gap bonus: elements unreferenced longer are more impactful callbacks
    # Capped at 5.0 to prevent ancient dormant elements from dominating
    turns_since_reference = current_turn - element.last_referenced_turn
    score += min(turns_since_reference / 10.0, 5.0)

    # Character involvement: bonus if involved characters are in active party
    active_lower = [c.lower() for c in active_characters]
    if any(c.lower() in active_lower for c in element.characters_involved):
        score += 2.0

    # Importance: more-referenced elements are more established
    score += element.times_referenced * 0.5

    # Potential callbacks: bonus if AI already suggested uses
    if element.potential_callbacks:
        score += 1.0

    # Dormancy penalty: still available but deprioritized
    if element.dormant:
        score -= 3.0

    return score
```

This function is intentionally simple and stateless -- it takes all inputs as parameters and returns a float. No LLM calls, no state mutation.

#### 2. Callback Suggestion Formatting (agents.py)

Follow the pattern of `format_all_secrets_context()` (agents.py line 1046-1075) and `format_all_sheets_context()` (agents.py line 992-1016) for building DM context sections:

```python
# Constants for callback suggestions
MAX_CALLBACK_SUGGESTIONS = 5  # Max suggestions to include in DM context
MIN_CALLBACK_SCORE = 0.0  # Minimum score threshold (0.0 = include all scored)


def format_callback_suggestions(
    callback_database: NarrativeElementStore,
    current_turn: int,
    active_characters: list[str],
) -> str:
    """Format callback suggestions for DM context injection.

    Scores active narrative elements by callback relevance, selects
    the top candidates, and formats them into a markdown section
    matching the epic AC format.

    Story 11.3: DM Callback Suggestions.
    FR78: DM context includes callback suggestions.

    Args:
        callback_database: Campaign-level NarrativeElementStore.
        current_turn: Current turn number.
        active_characters: List of active character names from turn_queue.

    Returns:
        Formatted markdown section, or empty string if no suggestions.
    """
    # Get active (non-resolved) elements
    active_elements = callback_database.get_active()
    if not active_elements:
        return ""

    # Score and rank elements
    scored: list[tuple[float, NarrativeElement]] = []
    for element in active_elements:
        element_score = score_callback_relevance(
            element, current_turn, active_characters
        )
        if element_score >= MIN_CALLBACK_SCORE:
            scored.append((element_score, element))

    if not scored:
        return ""

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top N
    top_suggestions = scored[:MAX_CALLBACK_SUGGESTIONS]

    # Format output matching epic AC
    lines = [
        "## Callback Opportunities",
        "Consider weaving in these earlier story elements:",
        "",
    ]

    for idx, (_score, element) in enumerate(top_suggestions, 1):
        # Header: name, turn, session
        lines.append(
            f"{idx}. **{element.name}** (Turn {element.turn_introduced}, Session {element.session_introduced})"
        )
        # Description
        if element.description:
            lines.append(f"   {element.description}")
        # Potential use (first suggestion only, for brevity)
        if element.potential_callbacks:
            lines.append(f"   Potential use: {element.potential_callbacks[0]}")
        # Blank line between entries
        lines.append("")

    return "\n".join(lines).rstrip()
```

#### 3. DM Context Integration (agents.py)

Insert the callback suggestions section into `_build_dm_context()` after the Active Secrets section. Follow the exact same pattern used for secrets and player suggestions:

```python
def _build_dm_context(state: GameState) -> str:
    # ... existing code through Active Secrets section ...

    # Add callback suggestions from campaign database (Story 11.3 - FR78)
    callback_database = state.get("callback_database", NarrativeElementStore())
    if callback_database.elements:
        current_turn = len(state.get("ground_truth_log", []))
        # Active characters are all agents except DM
        active_characters = [name for name in state["turn_queue"] if name != "dm"]
        callback_context = format_callback_suggestions(
            callback_database, current_turn, active_characters
        )
        if callback_context:
            context_parts.append(callback_context)

    # ... existing Player Suggestion and Player Whisper code ...
```

The placement after Active Secrets but before Player Suggestion/Player Whisper is intentional: callback suggestions are persistent context (like secrets), while nudges and whispers are single-use ephemeral context. This ordering groups persistent context together.

#### 4. DM System Prompt Update (agents.py)

Add callback awareness to the existing "Narrative Continuity" section of `DM_SYSTEM_PROMPT`:

```python
## Narrative Continuity

Reference earlier events naturally to maintain immersion:
- Mention consequences of past player decisions
- Weave plot threads from earlier scenes into current narration
- Acknowledge character growth and relationships
- Reward callbacks to earlier details with meaningful payoffs
- Check the "Callback Opportunities" section in your context for specific story threads to weave in
- These suggestions are optional inspiration - use them when they fit naturally, ignore when they don't
```

This is a minimal, non-disruptive change. The DM already has instructions about narrative continuity; we're just pointing it to the new context section.

#### 5. Import Addition (agents.py)

Add `NarrativeElementStore` to the existing imports from models:

```python
from models import (
    AgentMemory,
    AgentSecrets,
    CharacterConfig,
    CharacterFacts,
    CharacterSheet,
    DMConfig,
    GameState,
    ModuleDiscoveryResult,
    ModuleInfo,
    NarrativeElement,        # New: Story 11.3
    NarrativeElementStore,   # New: Story 11.3
)
```

### Key Design Decisions

1. **Scoring is purely heuristic (no LLM call):** The scoring function uses simple arithmetic based on element metadata. This is fast (no API calls), deterministic (same inputs = same score), and sufficient for ranking. The LLM-generated `potential_callbacks` field (from Story 11.2) provides the "smart" aspect.

2. **MAX_CALLBACK_SUGGESTIONS = 5:** Limits context bloat. Each suggestion is approximately 3-4 lines (~40-60 tokens), so 5 suggestions add ~200-300 tokens to the DM context. This is well within the DM's token limit (default 8000) and a small fraction of the total context.

3. **Suggestions are "optional inspiration":** The system prompt explicitly tells the DM these are non-binding. This avoids the DM feeling forced to use every suggestion, which would make the narrative feel mechanical. The epic AC explicitly states: "it doesn't have to use suggestions (just inspiration)."

4. **Scoring dimensions chosen for narrative impact:**
   - **Recency gap** is the primary factor because callbacks are most impressive when they reference elements from far in the past (Chekhov's Gun payoff).
   - **Character involvement** ensures suggestions are relevant to the current scene.
   - **Times referenced** surfaces established elements over one-off mentions.
   - **Potential callbacks** boosts elements that already have AI-suggested uses.
   - **Dormancy penalty** deprioritizes stale elements without removing them entirely.

5. **No new state fields or persistence changes:** This story only adds read-only formatting of existing data. The `callback_database` (from Story 11.2) is read but not modified. No changes to `GameState`, `models.py`, `persistence.py`, or `memory.py`.

6. **Placement in DM context ordering:** Callback suggestions appear after Active Secrets but before Player Suggestion/Player Whisper. This groups persistent narrative context (story history, character info, secrets, callbacks) separately from ephemeral single-use inputs (nudges, whispers).

7. **Format matches epic AC exactly:** The output format uses bold names, parenthetical turn/session info, description, and "Potential use:" lines -- exactly matching the format specified in the epic's acceptance criteria.

### Test Strategy

**Test file:** `tests/test_story_11_3_dm_callback_suggestions.py`

**Unit Tests:**

- `score_callback_relevance()`:
  - Recency gap scoring (various gaps, capped at 5.0)
  - Character involvement bonus (+2.0 when match)
  - No character bonus when no match
  - Importance bonus (times_referenced * 0.5)
  - Potential callbacks bonus (+1.0 when present)
  - Dormancy penalty (-3.0)
  - Combined scoring with multiple factors
  - Edge cases (turn 0, empty characters, dormant + involved)

- `format_callback_suggestions()`:
  - Empty database returns empty string
  - Single element returns properly formatted section
  - Multiple elements sorted by score (verify ordering)
  - Respects MAX_CALLBACK_SUGGESTIONS limit
  - Includes "Potential use:" when potential_callbacks present
  - Omits "Potential use:" when potential_callbacks empty
  - All resolved elements filtered out
  - Dormant elements included but lower ranked
  - Format matches epic AC example

- `_build_dm_context()` integration:
  - State with populated callback_database includes "Callback Opportunities" section
  - State with empty callback_database omits section
  - State without `callback_database` key does not crash
  - Section order: after "Active Secrets", before "Player Suggestion"

**Mock Pattern (follow existing test patterns):**

```python
from models import (
    NarrativeElement,
    NarrativeElementStore,
    create_narrative_element,
)

# Create test elements directly
element = create_narrative_element(
    element_type="character",
    name="Skrix the Goblin",
    description="Befriended by party, promised cave information",
    turn_introduced=15,
    session_introduced=2,
    characters_involved=["Shadowmere", "Aldric"],
    potential_callbacks=["Could appear with promised info", "Might be in danger"],
)

# Build test store
store = NarrativeElementStore(elements=[element])

# Test scoring
score = score_callback_relevance(element, current_turn=50, active_characters=["shadowmere"])

# Test formatting
result = format_callback_suggestions(store, current_turn=50, active_characters=["shadowmere"])
assert "## Callback Opportunities" in result
assert "Skrix the Goblin" in result
```

No LLM mocking is needed for this story since all functions are purely computational (no LLM calls).

### Important Constraints

- **No LLM calls in this story:** All scoring and formatting is deterministic heuristic logic. The only LLM-generated content is the `potential_callbacks` field populated in Story 11.2 during extraction.
- **Read-only access to callback_database:** This story reads from the campaign-level `callback_database` in state but never modifies it. No state mutation.
- **No new dependencies:** Uses only existing imports (Pydantic models from models.py).
- **No UI changes:** The UI for viewing callbacks is Story 11.5. This story only affects the DM's prompt context (invisible to the user).
- **Token budget awareness:** MAX_CALLBACK_SUGGESTIONS limits the context growth. At 5 suggestions of ~60 tokens each, the addition is ~300 tokens maximum.
- **Backward compatibility:** If `callback_database` is missing from state (old checkpoints), `_build_dm_context()` gracefully defaults to an empty store and omits the section entirely.
