# Story 11-1: Narrative Element Extraction

## Story

As a **system**,
I want **to extract significant narrative elements from each turn**,
So that **potential callback material is identified and stored**.

## Status

**Status:** ready-for-dev
**Epic:** 11 - Callback Tracker (Chekhov's Gun)
**Created:** 2026-02-06
**FRs Covered:** FR76, FR77

## Acceptance Criteria

**Given** each turn's content
**When** processed
**Then** an LLM extracts notable elements:
- Named NPCs introduced
- Locations described
- Items mentioned (especially unique ones)
- Plot hooks or unresolved threads
- Character backstory references
- Promises or threats made

**Given** the extraction prompt
**When** run after each DM turn
**Then** it returns structured data:
```json
{
  "elements": [
    {
      "type": "npc",
      "name": "Skrix the Goblin",
      "context": "Befriended by party, promised to share info about the caves",
      "characters_involved": ["Shadowmere", "Aldric"]
    }
  ]
}
```

**Given** the extraction
**When** run
**Then** it's lightweight (fast model) to not slow down gameplay

## Tasks

### Data Model (models.py)

1. [ ] Add `NarrativeElement` Pydantic model to models.py
   - Fields: `id`, `element_type`, `name`, `description`, `turn_introduced`, `turns_referenced`, `resolved`, `characters_involved`, `session_introduced`
   - `element_type` uses `Literal["character", "item", "location", "event", "promise", "threat"]`
   - `id` defaults to `uuid.uuid4().hex` (matching Whisper pattern)
   - Validators: `name` must be non-empty, `turn_introduced` >= 0
2. [ ] Add `NarrativeElementStore` Pydantic model to models.py
   - Contains `elements: list[NarrativeElement]` field
   - Add `get_active()` method returning unresolved elements
   - Add `get_by_type(element_type)` filter method
   - Add `find_by_name(name)` lookup method (case-insensitive)
3. [ ] Add `narrative_elements: dict[str, NarrativeElementStore]` field to `GameState` TypedDict
   - Keyed by session_id for cross-session tracking
4. [ ] Update `create_initial_game_state()` to initialize empty `narrative_elements`
5. [ ] Update `populate_game_state()` to initialize empty `NarrativeElementStore` for the session
6. [ ] Add `NarrativeElement`, `NarrativeElementStore` to `__all__` exports in models.py
7. [ ] Add `create_narrative_element()` factory function to models.py

### Extraction Logic (memory.py)

8. [ ] Add `ELEMENT_EXTRACTION_PROMPT` constant to memory.py
   - System prompt instructs LLM to extract narrative elements from turn content
   - Requests structured JSON output matching `NarrativeElement` fields
   - Lists the 6 element types with examples for each
   - Emphasizes extracting only genuinely significant elements (not every noun)
9. [ ] Add `NarrativeElementExtractor` class to memory.py
   - Constructor takes `provider: str`, `model: str` (uses lightweight model)
   - Lazy LLM initialization pattern matching `Summarizer._get_llm()`
   - `MAX_CONTENT_CHARS` class constant for input truncation (like `Summarizer.MAX_BUFFER_CHARS`)
10. [ ] Add `extract_elements()` method to `NarrativeElementExtractor`
    - Accepts `turn_content: str`, `turn_number: int`, `session_id: str`
    - Invokes LLM with extraction prompt + turn content
    - Parses JSON response into list of `NarrativeElement` objects
    - Returns `list[NarrativeElement]` (empty list on failure for graceful degradation)
    - Logs errors but does not raise (non-blocking per AC)
11. [ ] Add `_parse_extraction_response()` helper function
    - Handles markdown code block stripping (matching `_parse_module_json` pattern from agents.py)
    - Extracts JSON array from response text
    - Validates each element against `NarrativeElement` model
    - Skips invalid elements with warning log (matching module discovery pattern)
12. [ ] Add module-level `_extractor_cache` dict for caching extractor instances
    - Keyed by `(provider, model)` tuple (matching `_summarizer_cache` pattern)

### Integration with Game Loop (graph.py / agents.py)

13. [ ] Add `extract_narrative_elements()` function to memory.py
    - Accepts `state: GameState` and the latest turn content
    - Gets extractor config from `AppConfig` (uses summarizer provider/model for lightweight extraction)
    - Calls `NarrativeElementExtractor.extract_elements()`
    - Merges extracted elements into state's `NarrativeElementStore`
    - Returns updated `narrative_elements` dict
14. [ ] Integrate element extraction into `dm_turn()` in agents.py
    - After DM generates response, call extraction on the new DM content
    - Update returned GameState with extracted elements
    - Extraction runs synchronously but uses fast model for minimal latency
15. [ ] Integrate element extraction into `pc_turn()` in agents.py
    - After PC generates response, call extraction on the new PC content
    - Update returned GameState with extracted elements

### Serialization (persistence.py)

16. [ ] Update `serialize_game_state()` to serialize `narrative_elements`
    - Use `.model_dump()` pattern matching agent_secrets serialization
17. [ ] Update `deserialize_game_state()` to reconstruct `NarrativeElementStore` with `NarrativeElement` objects
    - Include backward compatibility for old checkpoints without narrative_elements
18. [ ] Verify checkpoint save/restore preserves narrative_elements

### Configuration

19. [ ] Add `extractor` field to `AgentsConfig` in config.py
    - Uses `AgentConfig` with default fast model settings
    - Default: same provider/model as summarizer (lightweight)
20. [ ] Update `config/defaults.yaml` to include extractor agent config

### Tests

21. [ ] Add unit tests for `NarrativeElement` model validation
    - Valid construction with all fields
    - Default values (id generation, empty turns_referenced, resolved=False)
    - Name must be non-empty
    - Invalid element_type rejected
    - turn_introduced >= 0
22. [ ] Add unit tests for `NarrativeElementStore` methods
    - `get_active()` returns only unresolved elements
    - `get_by_type()` filters correctly
    - `find_by_name()` is case-insensitive
    - Empty store returns empty lists
23. [ ] Add unit tests for `create_narrative_element()` factory function
24. [ ] Add unit tests for `ELEMENT_EXTRACTION_PROMPT` format and content
25. [ ] Add unit tests for `_parse_extraction_response()`
    - Valid JSON array with multiple elements
    - JSON wrapped in markdown code blocks
    - Empty response returns empty list
    - Malformed JSON returns empty list (graceful degradation)
    - Mixed valid and invalid elements (valid kept, invalid skipped)
26. [ ] Add unit tests for `NarrativeElementExtractor.extract_elements()` with mocked LLM
    - Successful extraction returns NarrativeElement list
    - LLM failure returns empty list (no exception raised)
    - Empty content returns empty list
    - Content truncation at MAX_CONTENT_CHARS
27. [ ] Add unit tests for `extract_narrative_elements()` state integration
    - Elements merged into existing NarrativeElementStore
    - New store created if session not present
28. [ ] Add serialization round-trip tests for narrative_elements
    - serialize -> deserialize preserves all fields
    - Backward compatibility with old checkpoints (no narrative_elements key)
29. [ ] Add integration test for dm_turn producing narrative_elements
30. [ ] Add integration test for pc_turn producing narrative_elements

## Dependencies

- **Epic 10** (done): Provides patterns for state integration (agent_secrets field in GameState)
- **Story 5.2** (done): Provides Summarizer pattern to follow for LLM calls
- **Story 7.1** (done): Provides JSON parsing pattern (`_parse_module_json`)
- No blocking dependencies within Epic 11 (this is the first story)

## Dev Notes

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `models.py` | Modify | Add `NarrativeElement`, `NarrativeElementStore` models, factory function, update `GameState`, update `create_initial_game_state()`, `populate_game_state()`, `__all__` |
| `memory.py` | Modify | Add `ELEMENT_EXTRACTION_PROMPT`, `NarrativeElementExtractor` class, `extract_narrative_elements()` function, `_parse_extraction_response()` helper, `_extractor_cache` |
| `agents.py` | Modify | Integrate extraction calls into `dm_turn()` and `pc_turn()` return statements |
| `persistence.py` | Modify | Extend `serialize_game_state()` and `deserialize_game_state()` for narrative_elements |
| `config.py` | Modify | Add `extractor` agent config to `AgentsConfig` |
| `config/defaults.yaml` | Modify | Add extractor agent defaults |
| `tests/test_story_11_1_narrative_element_extraction.py` | Create | Comprehensive unit and integration tests |

### Code Patterns to Follow

#### 1. NarrativeElement Model (follow Whisper pattern in models.py)

```python
class NarrativeElement(BaseModel):
    """Extracted narrative element for callback tracking.

    Story 11.1: Narrative Element Extraction.
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
    """
    id: str = Field(..., min_length=1, description="Unique element ID (UUID hex)")
    element_type: Literal["character", "item", "location", "event", "promise", "threat"] = Field(
        ..., description="Category of narrative element"
    )
    name: str = Field(..., min_length=1, description="Element name")
    description: str = Field(default="", description="Context description")
    turn_introduced: int = Field(..., ge=0, description="Turn when first extracted")
    session_introduced: int = Field(default=1, ge=1, description="Session when introduced")
    turns_referenced: list[int] = Field(default_factory=list, description="Turns where referenced")
    characters_involved: list[str] = Field(default_factory=list, description="Characters involved")
    resolved: bool = Field(default=False, description="Whether element is resolved")
```

Use `uuid.uuid4().hex` for ID generation in factory function, matching `create_whisper()` at line 474 of models.py.

#### 2. NarrativeElementExtractor Class (follow Summarizer pattern in memory.py)

```python
class NarrativeElementExtractor:
    """Extracts narrative elements from turn content using LLM.

    Uses a lightweight (fast) model to extract significant narrative
    elements without slowing down gameplay.

    Story 11.1: Narrative Element Extraction.
    """

    MAX_CONTENT_CHARS = 10_000  # Max chars for extraction input

    def __init__(self, provider: str, model: str) -> None:
        self.provider = provider
        self.model = model
        self._llm: BaseChatModel | None = None

    def _get_llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm(self.provider, self.model)
        return self._llm

    def extract_elements(
        self, turn_content: str, turn_number: int, session_id: str
    ) -> list[NarrativeElement]:
        # ... implementation
```

This mirrors the `Summarizer` class pattern (memory.py lines 106-221) with lazy LLM initialization, error handling that returns empty results, and the `_get_llm()` method.

#### 3. JSON Response Parsing (follow _parse_module_json in agents.py)

```python
def _parse_extraction_response(response_text: str, turn_number: int, session_number: int) -> list[NarrativeElement]:
    """Parse JSON array of narrative elements from LLM response."""
    # Strip markdown code blocks (same pattern as agents.py line 2009-2015)
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Find JSON array
    start_idx = text.find("[")
    end_idx = text.rfind("]")
    if start_idx == -1 or end_idx == -1:
        return []

    # Parse and validate
    data = json.loads(text[start_idx:end_idx + 1])
    elements = []
    for item in data:
        try:
            element = create_narrative_element(
                element_type=item.get("type", "event"),
                name=str(item.get("name", "")),
                description=str(item.get("context", item.get("description", ""))),
                turn_introduced=turn_number,
                session_introduced=session_number,
                characters_involved=item.get("characters_involved", []),
            )
            elements.append(element)
        except Exception as e:
            logger.warning("Skipping invalid narrative element: %s", e)
    return elements
```

#### 4. GameState Integration (follow agent_secrets pattern)

The `narrative_elements` field follows the same pattern as `agent_secrets` in the GameState TypedDict (models.py line 1156):

```python
class GameState(TypedDict):
    # ... existing fields ...
    narrative_elements: dict[str, "NarrativeElementStore"]
```

Initialize in factory functions:

```python
# In create_initial_game_state()
narrative_elements={},

# In populate_game_state()
narrative_elements={session_id: NarrativeElementStore()},
```

#### 5. Agent Turn Integration (follow sheet update pattern in dm_turn)

In `dm_turn()` (agents.py ~line 1467), after building the new state, extract elements:

```python
# Extract narrative elements from DM response (Story 11.1)
try:
    from memory import extract_narrative_elements
    updated_narrative = extract_narrative_elements(
        new_state_dict, response_content, turn_number
    )
except Exception as e:
    logger.warning("Narrative element extraction failed: %s", e)
    updated_narrative = state.get("narrative_elements", {})
```

The same pattern applies in `pc_turn()`. Extraction failure must not block the game loop.

#### 6. Serialization (follow agent_secrets pattern in persistence.py)

Extend `serialize_game_state()`:
```python
"narrative_elements": {
    session_id: store.model_dump()
    for session_id, store in state.get("narrative_elements", {}).items()
}
```

Extend `deserialize_game_state()` with backward compatibility:
```python
narrative_elements_raw = data.get("narrative_elements", {})
narrative_elements = {}
for session_id, store_data in narrative_elements_raw.items():
    if isinstance(store_data, dict):
        elements = [NarrativeElement(**e) for e in store_data.get("elements", [])]
        narrative_elements[session_id] = NarrativeElementStore(elements=elements)
```

#### 7. Extraction Prompt Design

The prompt should request JSON matching the epic's AC format:

```python
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
- Return an empty array if no significant elements are found

## Response Format:
Return ONLY a JSON array:
```json
[
  {
    "type": "character",
    "name": "Skrix the Goblin",
    "context": "Befriended by party, promised to share info about the caves",
    "characters_involved": ["Shadowmere", "Aldric"]
  }
]
```

Return ONLY the JSON array, no additional text."""
```

#### 8. Configuration Integration

Add extractor to `AgentsConfig` in config.py following the summarizer pattern:

```python
class AgentsConfig(BaseSettings):
    dm: AgentConfig = Field(default_factory=AgentConfig)
    summarizer: AgentConfig = Field(default_factory=lambda: AgentConfig(token_limit=4000))
    extractor: AgentConfig = Field(
        default_factory=lambda: AgentConfig(token_limit=4000)
    )
```

### Key Design Decisions

1. **Extraction runs after every turn (DM and PC):** The architecture says "after each agent turn." This captures both DM narration (introduces NPCs, locations, events) and PC actions (promises, backstory references). The extraction is non-blocking -- failures are logged and return empty lists.

2. **Uses fast/lightweight model:** The extractor defaults to the same provider/model as the summarizer (typically `gemini-1.5-flash`), which is fast and cheap. This prevents gameplay slowdown per the AC requirement.

3. **Graceful degradation everywhere:** Following the Summarizer pattern, all LLM calls in the extractor are wrapped in try/except blocks. Failures log warnings but never raise exceptions that would interrupt gameplay.

4. **NarrativeElementStore keyed by session_id:** This supports cross-session tracking as required by Story 11.2 (Callback Database). The store accumulates elements across turns and persists via checkpoints.

5. **JSON field mapping:** The epic AC uses `"type"` and `"context"` in the JSON response, but the model uses `element_type` and `description`. The parser maps between these: `item.get("type")` -> `element_type`, `item.get("context")` -> `description`.

6. **No UI changes in this story:** The UI for viewing narrative elements is Story 11.5 (Callback UI & History). This story focuses purely on extraction and storage.

### Test Strategy

**Test file:** `tests/test_story_11_1_narrative_element_extraction.py`

**Unit Tests:**
- NarrativeElement model validation (valid, defaults, invalid type, empty name)
- NarrativeElementStore methods (get_active, get_by_type, find_by_name)
- Factory function (create_narrative_element generates valid UUID ID)
- `_parse_extraction_response()` with valid JSON, code blocks, empty, malformed
- `NarrativeElementExtractor.extract_elements()` with mocked LLM (success, failure)
- `extract_narrative_elements()` state integration

**Integration Tests:**
- dm_turn/pc_turn produce narrative_elements in returned state (with mocked LLM)
- Serialization round-trip preserves all NarrativeElement fields
- Backward compatibility (old checkpoints without narrative_elements)

**Mock Pattern:**
```python
# Mock the extractor LLM to avoid real API calls
with patch.object(NarrativeElementExtractor, '_get_llm') as mock_llm:
    mock_response = MagicMock()
    mock_response.content = '[{"type": "npc", "name": "Skrix", ...}]'
    mock_llm.return_value.invoke.return_value = mock_response
```

### Important Constraints

- **Never block the game loop:** Extraction failures must be silent (logged but not raised)
- **Token efficiency:** The extraction prompt should be concise; input content is truncated at `MAX_CONTENT_CHARS`
- **Immutable state:** Follow the existing pattern of returning new GameState dicts from turn functions, never mutating input state
- **No new dependencies:** Uses existing `get_llm()` factory and LangChain message types
