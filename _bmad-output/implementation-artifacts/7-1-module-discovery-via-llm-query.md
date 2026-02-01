# Story 7.1: Module Discovery via LLM Query

Status: code-review-complete

## Story

As a **user starting a new adventure**,
I want **to ask the DM LLM what D&D modules it knows**,
so that **I can choose from adventures the AI can run authentically**.

## Acceptance Criteria

1. **Given** the user clicks "New Adventure"
   **When** the module discovery phase begins
   **Then** the system queries the DM LLM with: "You are the dungeon master in a dungeons and dragons game. What dungeons and dragons modules do you know from your training?"

2. **Given** the LLM query
   **When** requesting modules
   **Then** the prompt requests exactly 100 modules in JSON format with: number, name, description

3. **Given** the LLM response
   **When** parsed
   **Then** each module has:
   ```json
   {
     "number": 1,
     "name": "Curse of Strahd",
     "description": "Gothic horror adventure in the haunted realm of Barovia..."
   }
   ```

4. **Given** the module list is retrieved
   **When** cached
   **Then** it's stored in session state for the duration of adventure creation

5. **Given** the LLM fails to return valid JSON
   **When** parsing fails
   **Then** the system retries with a more explicit JSON schema instruction

## Tasks / Subtasks

- [x] Task 1: Add ModuleInfo model to models.py (AC: #3)
  - [x] 1.1 Add ModuleInfo Pydantic model as defined in architecture.md
  - [x] 1.2 Add ModuleDiscoveryResult model to wrap list of modules with metadata
  - [x] 1.3 Write unit tests for ModuleInfo validation
  - [x] 1.4 Write unit tests for JSON serialization/deserialization

- [x] Task 2: Create module discovery function in agents.py (AC: #1, #2, #5)
  - [x] 2.1 Create `discover_modules(dm_config: DMConfig) -> ModuleDiscoveryResult` function
  - [x] 2.2 Construct LLM prompt requesting exactly 100 modules in JSON format
  - [x] 2.3 Include explicit JSON schema in prompt for reliable parsing
  - [x] 2.4 Parse LLM response and extract JSON array
  - [x] 2.5 Implement retry logic with more explicit schema on parse failure
  - [x] 2.6 Handle LLM errors gracefully using existing LLMError pattern
  - [x] 2.7 Write unit tests with mocked LLM responses (valid JSON, invalid JSON, empty response)
  - [x] 2.8 Write unit tests for retry logic

- [x] Task 3: Implement session state caching (AC: #4)
  - [x] 3.1 Add `module_list` key to session state storage pattern
  - [x] 3.2 Add `module_discovery_in_progress` flag for UI loading state
  - [x] 3.3 Add `module_discovery_error` for error state
  - [x] 3.4 Ensure module list persists across Streamlit reruns during adventure creation
  - [x] 3.5 Clear cache on adventure creation completion or cancellation
  - [x] 3.6 Write integration tests for session state persistence

- [x] Task 4: Integrate module discovery into app.py (AC: #1, #4)
  - [x] 4.1 Add module discovery trigger point in new adventure flow
  - [x] 4.2 Create `start_module_discovery()` function that initiates discovery
  - [x] 4.3 Add loading UI showing "Consulting the Dungeon Master's Library..."
  - [x] 4.4 Handle discovery completion and store results in session state
  - [x] 4.5 Handle discovery errors with user-friendly messaging (campfire style)
  - [x] 4.6 Write integration tests for discovery flow

- [x] Task 5: Write comprehensive acceptance tests
  - [x] 5.1 Test: LLM query includes correct prompt text (AC #1)
  - [x] 5.2 Test: Prompt requests exactly 100 modules in JSON format (AC #2)
  - [x] 5.3 Test: Response parsing extracts module data correctly (AC #3)
  - [x] 5.4 Test: Module list stored in session state after discovery (AC #4)
  - [x] 5.5 Test: Retry with explicit schema on JSON parse failure (AC #5)
  - [x] 5.6 Test: Multiple parse failures lead to graceful error handling
  - [x] 5.7 Test: Discovery works with all supported providers (Gemini, Claude, Ollama)

## Dev Notes

### Implementation Strategy

This story implements the first phase of Epic 7 (Module Selection & Campaign Setup). The module discovery feature queries the DM LLM for D&D modules it knows from training, caches the response, and prepares it for the selection UI (Story 7.2).

Key design decisions:
1. **Use existing get_llm factory** - Leverages the established LLM provider pattern
2. **Session state caching** - Modules are cached during adventure creation only
3. **Retry with explicit schema** - More verbose JSON instructions on parse failure
4. **Graceful degradation** - If discovery fails, user can still proceed with freeform adventure

### ModuleInfo Model (from architecture.md)

The architecture document already defines the ModuleInfo model:

```python
# models.py - Add to existing models
class ModuleInfo(BaseModel):
    """D&D module information from LLM knowledge."""
    number: int = Field(..., ge=1, le=100, description="Module number (1-100)")
    name: str = Field(..., min_length=1, description="Module name")
    description: str = Field(..., min_length=1, description="Brief module description")
    setting: str = Field(default="", description="Campaign setting (e.g., Forgotten Realms)")
    level_range: str = Field(default="", description="Recommended level range (e.g., 1-5)")
```

**Additional Model for Discovery Result:**

```python
class ModuleDiscoveryResult(BaseModel):
    """Result of module discovery LLM query."""
    modules: list[ModuleInfo] = Field(default_factory=list)
    provider: str = Field(..., description="Provider used for discovery")
    model: str = Field(..., description="Model used for discovery")
    timestamp: str = Field(..., description="ISO timestamp of discovery")
    retry_count: int = Field(default=0, ge=0, description="Number of retries needed")
```

### LLM Prompt Design

**Initial Prompt (standard query):**

```python
MODULE_DISCOVERY_PROMPT = """You are the dungeon master in a dungeons and dragons game.

What dungeons and dragons modules do you know from your training?

Return exactly 100 modules in JSON format. Each module must have:
- number: Integer from 1 to 100
- name: The official module name
- description: A 1-2 sentence description of the adventure

Example format:
```json
[
  {"number": 1, "name": "Curse of Strahd", "description": "Gothic horror adventure in the haunted realm of Barovia, where players must defeat the vampire lord Strahd von Zarovich."},
  {"number": 2, "name": "Lost Mine of Phandelver", "description": "Starter adventure set in the Sword Coast where heroes discover a lost dwarven mine and its magical forge."}
]
```

Include modules from different editions (AD&D, 2e, 3e, 4e, 5e) and various campaign settings (Forgotten Realms, Greyhawk, Dragonlance, Ravenloft, Eberron, etc.).

Return ONLY the JSON array, no additional text."""
```

**Retry Prompt (more explicit schema):**

```python
MODULE_DISCOVERY_RETRY_PROMPT = """Your previous response could not be parsed as valid JSON.

Please return exactly 100 D&D modules as a valid JSON array. Each object must have these exact keys:
- "number": integer (1-100)
- "name": string (module name)
- "description": string (brief description)

The response must:
1. Start with [ and end with ]
2. Use double quotes for strings
3. Separate objects with commas
4. Have no trailing commas
5. Contain no text before or after the JSON array

Example of valid format:
[
  {"number": 1, "name": "Curse of Strahd", "description": "Gothic horror in Barovia."},
  {"number": 2, "name": "Lost Mine of Phandelver", "description": "Starter adventure in the Sword Coast."}
]

Return ONLY the JSON array now:"""
```

### Module Discovery Function

```python
# agents.py - Add to module

import json
import re
from datetime import UTC, datetime
from typing import Any

from models import ModuleInfo, ModuleDiscoveryResult

# Maximum retry attempts for module discovery
MODULE_DISCOVERY_MAX_RETRIES = 2

def discover_modules(dm_config: DMConfig) -> ModuleDiscoveryResult:
    """Query the DM LLM for known D&D modules.

    Uses the configured DM provider and model to ask what D&D modules
    the LLM knows from training. Returns a structured list of modules.

    Args:
        dm_config: DM configuration with provider and model settings.

    Returns:
        ModuleDiscoveryResult containing list of ModuleInfo objects.

    Raises:
        LLMError: If the LLM API call fails after retries.
    """
    llm = get_llm(dm_config.provider, dm_config.model)
    retry_count = 0

    for attempt in range(MODULE_DISCOVERY_MAX_RETRIES + 1):
        try:
            # Use standard prompt on first attempt, retry prompt on subsequent
            prompt = (
                MODULE_DISCOVERY_PROMPT if attempt == 0
                else MODULE_DISCOVERY_RETRY_PROMPT
            )

            # Invoke LLM
            messages = [HumanMessage(content=prompt)]
            response = llm.invoke(messages)

            # Extract response text
            response_text = _extract_response_text(response)

            # Parse JSON from response
            modules = _parse_module_json(response_text)

            return ModuleDiscoveryResult(
                modules=modules,
                provider=dm_config.provider,
                model=dm_config.model,
                timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                retry_count=retry_count,
            )

        except json.JSONDecodeError as e:
            retry_count += 1
            if attempt == MODULE_DISCOVERY_MAX_RETRIES:
                # Log error and return empty result
                logger.error(
                    "Module discovery JSON parse failed after %d retries: %s",
                    retry_count, str(e)
                )
                raise LLMError(
                    provider=dm_config.provider,
                    agent="dm",
                    error_type="invalid_response",
                    original_error=e,
                ) from e
            logger.warning(
                "Module discovery JSON parse failed (attempt %d), retrying...",
                attempt + 1
            )

    # Should not reach here, but safety return
    return ModuleDiscoveryResult(
        modules=[],
        provider=dm_config.provider,
        model=dm_config.model,
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        retry_count=retry_count,
    )


def _parse_module_json(response_text: str) -> list[ModuleInfo]:
    """Parse JSON array of modules from LLM response text.

    Handles common LLM response quirks:
    - JSON wrapped in markdown code blocks
    - Leading/trailing whitespace
    - Extra text before/after JSON

    Args:
        response_text: Raw text from LLM response.

    Returns:
        List of validated ModuleInfo objects.

    Raises:
        json.JSONDecodeError: If JSON parsing fails.
        ValueError: If parsed data doesn't match expected structure.
    """
    # Strip whitespace
    text = response_text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    # Try to find JSON array in response
    # Look for first [ and last ]
    start_idx = text.find("[")
    end_idx = text.rfind("]")

    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
        raise json.JSONDecodeError(
            "No JSON array found in response", text, 0
        )

    json_text = text[start_idx:end_idx + 1]

    # Parse JSON
    data = json.loads(json_text)

    if not isinstance(data, list):
        raise ValueError("Expected JSON array, got: " + type(data).__name__)

    # Validate and convert to ModuleInfo objects
    modules: list[ModuleInfo] = []
    for item in data:
        if not isinstance(item, dict):
            continue  # Skip invalid items

        try:
            module = ModuleInfo(
                number=item.get("number", len(modules) + 1),
                name=str(item.get("name", "")).strip(),
                description=str(item.get("description", "")).strip(),
                setting=str(item.get("setting", "")).strip(),
                level_range=str(item.get("level_range", "")).strip(),
            )
            modules.append(module)
        except Exception as e:
            logger.warning("Skipping invalid module entry: %s", e)
            continue

    return modules
```

### Session State Keys

| Key | Type | Purpose |
|-----|------|---------|
| `module_list` | `list[ModuleInfo]` | Cached module list from discovery |
| `module_discovery_result` | `ModuleDiscoveryResult` | Full discovery result with metadata |
| `module_discovery_in_progress` | `bool` | True while discovery is running |
| `module_discovery_error` | `UserError \| None` | Error from failed discovery |
| `selected_module` | `ModuleInfo \| None` | User's selected module (for Story 7.2) |

### Session State Lifecycle

```
1. User clicks "New Adventure"
   -> module_discovery_in_progress = True
   -> module_list = None
   -> module_discovery_error = None

2. Discovery completes successfully
   -> module_discovery_in_progress = False
   -> module_list = [ModuleInfo, ...]
   -> module_discovery_result = ModuleDiscoveryResult(...)

3. Discovery fails
   -> module_discovery_in_progress = False
   -> module_discovery_error = UserError(...)
   -> User can retry or proceed to freeform adventure

4. User cancels adventure creation
   -> Clear all module_* session state keys

5. Adventure starts
   -> selected_module persists to campaign config
   -> module_list can be cleared (no longer needed)
```

### Integration with app.py

```python
# app.py - Add to module

def start_module_discovery() -> None:
    """Initiate module discovery from DM LLM.

    Sets session state flags and triggers discovery. The discovery
    runs synchronously (blocking) for MVP simplicity.

    UI should show loading indicator while in_progress is True.
    """
    st.session_state["module_discovery_in_progress"] = True
    st.session_state["module_discovery_error"] = None
    st.session_state["module_list"] = None

    try:
        # Get DM config (use defaults if no game exists yet)
        game: GameState | None = st.session_state.get("game")
        if game:
            dm_config = game["dm_config"]
        else:
            from config import load_dm_config
            dm_config = load_dm_config()

        # Run discovery
        result = discover_modules(dm_config)

        # Store results
        st.session_state["module_discovery_result"] = result
        st.session_state["module_list"] = result.modules

    except LLMError as e:
        # Convert to UserError for display
        error = create_user_error(
            error_type=e.error_type,
            provider=e.provider,
            agent=e.agent,
        )
        st.session_state["module_discovery_error"] = error

    finally:
        st.session_state["module_discovery_in_progress"] = False


def clear_module_discovery_state() -> None:
    """Clear all module discovery session state.

    Called when adventure creation is cancelled or completed.
    """
    keys_to_clear = [
        "module_list",
        "module_discovery_result",
        "module_discovery_in_progress",
        "module_discovery_error",
        "selected_module",
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
```

### Loading UI Component

```python
# app.py - Add to render functions

def render_module_discovery_loading() -> None:
    """Render loading state during module discovery."""
    st.markdown("""
    <div class="module-discovery-loading">
        <div class="loading-icon">&#128214;</div>
        <p class="loading-text">Consulting the Dungeon Master's Library...</p>
        <p class="loading-subtext">Gathering tales of adventure from across the realms</p>
    </div>
    """, unsafe_allow_html=True)

    # Streamlit spinner as backup/accessibility
    with st.spinner(""):
        pass  # Just show spinner animation
```

### CSS Styling for Loading State

```css
/* styles/theme.css - Add module discovery styles */

.module-discovery-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-2xl);
    text-align: center;
}

.module-discovery-loading .loading-icon {
    font-size: 48px;
    margin-bottom: var(--space-lg);
    animation: book-pulse 2s ease-in-out infinite;
}

.module-discovery-loading .loading-text {
    font-family: var(--font-narrative);
    font-size: 20px;
    font-style: italic;
    color: var(--text-primary);
    margin-bottom: var(--space-sm);
}

.module-discovery-loading .loading-subtext {
    font-family: var(--font-ui);
    font-size: 14px;
    color: var(--text-secondary);
}

@keyframes book-pulse {
    0%, 100% { opacity: 0.7; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.1); }
}
```

### Error Handling (Campfire Style)

For module discovery errors, add a new error type:

```python
# models.py - Add to ERROR_TYPES

ERROR_TYPES["module_discovery_failed"] = {
    "title": "The Dungeon Master's library is unreachable...",
    "message": "Could not retrieve the list of known adventures. The tomes are shrouded in magical mist.",
    "action": "Try again, or start a freeform adventure without a specific module.",
}
```

### Architecture Compliance

| Pattern | Compliance | Notes |
|---------|------------|-------|
| Use existing get_llm factory | YES | `get_llm(dm_config.provider, dm_config.model)` |
| Session state for UI state | YES | Module list cached in session state |
| Pydantic models | YES | ModuleInfo and ModuleDiscoveryResult |
| LLMError for errors | YES | Raises LLMError on failure |
| UserError for display | YES | Converted for UI display |
| Campfire error messages | YES | Narrative-style error text |

### Testing Strategy

**Unit Tests (pytest):**

```python
# tests/test_story_7_1_module_discovery.py

class TestModuleInfo:
    def test_valid_module_info(self): ...
    def test_invalid_number_range(self): ...
    def test_empty_name_validation(self): ...
    def test_json_serialization(self): ...

class TestModuleDiscoveryResult:
    def test_empty_modules_list(self): ...
    def test_full_result_with_metadata(self): ...

class TestParseModuleJson:
    def test_valid_json_array(self): ...
    def test_json_in_code_block(self): ...
    def test_json_with_extra_text(self): ...
    def test_invalid_json_raises_error(self): ...
    def test_handles_missing_fields(self): ...
    def test_skips_invalid_entries(self): ...

class TestDiscoverModules:
    def test_successful_discovery_first_attempt(self): ...
    def test_retry_on_parse_failure(self): ...
    def test_max_retries_exceeded(self): ...
    def test_llm_error_handling(self): ...
    def test_works_with_gemini(self): ...
    def test_works_with_claude(self): ...
    def test_works_with_ollama(self): ...

class TestSessionStateCaching:
    def test_module_list_stored_on_success(self): ...
    def test_error_stored_on_failure(self): ...
    def test_in_progress_flag_management(self): ...
    def test_clear_state_removes_all_keys(self): ...
```

**Integration Tests:**

```python
class TestModuleDiscoveryFlow:
    def test_discovery_triggered_on_new_adventure(self): ...
    def test_loading_state_shown_during_discovery(self): ...
    def test_modules_displayed_after_discovery(self): ...
    def test_error_display_on_failure(self): ...
    def test_retry_button_triggers_new_discovery(self): ...
    def test_freeform_option_available_on_error(self): ...
```

### Edge Cases

1. **Empty response from LLM** - Return empty module list, log warning
2. **Partial JSON (LLM stopped mid-response)** - Parse what's available, log warning
3. **LLM returns < 100 modules** - Accept whatever is returned, don't force count
4. **LLM returns > 100 modules** - Accept all, UI will paginate (Story 7.2)
5. **Duplicate module numbers** - Accept as-is, UI handles display
6. **Unicode/special characters in names** - Pydantic handles encoding
7. **Very long descriptions** - Accept as-is, UI will truncate display

### Performance Considerations

- Module discovery is a one-time operation per adventure creation
- LLM call may take 10-30 seconds depending on model and network
- Results cached in session state, not persisted to disk (yet)
- No rate limiting concerns for single discovery per session

### What This Story Implements

1. **ModuleInfo Pydantic model** - Validated data structure for module data
2. **discover_modules() function** - LLM query with retry logic
3. **JSON parsing with fallbacks** - Handles common LLM response formats
4. **Session state caching** - Module list persists during adventure creation
5. **Error handling** - Campfire-style errors for failed discovery

### What This Story Does NOT Implement

- Module selection UI (Story 7.2)
- Module context injection into DM prompt (Story 7.3)
- Full new adventure flow integration (Story 7.4)
- Persistent module cache (future optimization)
- Module search/filter (Story 7.2)

### Dependencies

- Story 1.3 (LLM Provider Integration) - COMPLETE
- Story 4.5 (Error Handling & Recovery) - COMPLETE
- agents.py get_llm() factory - EXISTS
- models.py Pydantic patterns - EXISTS

### Files to Modify

| File | Changes |
|------|---------|
| `models.py` | Add ModuleInfo, ModuleDiscoveryResult models. Add module_discovery_failed to ERROR_TYPES. |
| `agents.py` | Add MODULE_DISCOVERY_PROMPT, MODULE_DISCOVERY_RETRY_PROMPT, discover_modules(), _parse_module_json() functions. Add to __all__ exports. |
| `app.py` | Add start_module_discovery(), clear_module_discovery_state(), render_module_discovery_loading() functions. |
| `styles/theme.css` | Add .module-discovery-loading styles. |

### Files to Create

| File | Purpose |
|------|---------|
| `tests/test_story_7_1_module_discovery.py` | Comprehensive test suite for module discovery |

### FR/NFR Coverage

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| FR56 | Query DM LLM for known D&D modules | discover_modules() function |

### References

- [Source: planning-artifacts/architecture.md#v1.1 Extension Architecture] - ModuleInfo model definition
- [Source: planning-artifacts/epics-v1.1.md#Story 7.1] - Detailed story requirements
- [Source: planning-artifacts/prd.md#FR56] - Module query requirement
- [Source: agents.py#get_llm] - LLM factory pattern
- [Source: agents.py#LLMError] - Error handling pattern
- [Source: models.py#ERROR_TYPES] - Campfire error messages
- [Source: app.py#session_state] - Session state patterns

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No debugging issues encountered during implementation.

### Completion Notes List

1. **ModuleInfo Model** - Added to models.py with full Pydantic validation (number 1-100, required name/description, optional setting/level_range)
2. **ModuleDiscoveryResult Model** - Wrapper model storing discovery metadata (provider, model, timestamp, retry_count)
3. **discover_modules() Function** - Added to agents.py with TDD approach:
   - Uses existing get_llm() factory for provider flexibility
   - LLM prompt requests exactly 100 modules in JSON format
   - JSON parsing handles markdown code blocks, extra text, and malformed entries
   - Retry logic with explicit schema on parse failure (max 2 retries)
   - Raises LLMError on exhausted retries or API errors
4. **Session State Caching** - Added helper functions to app.py:
   - `start_module_discovery()` - Initiates discovery and stores results
   - `clear_module_discovery_state()` - Cleans up state on cancel/completion
   - `render_module_discovery_loading()` - Loading UI component
5. **CSS Styles** - Added module-discovery-loading styles to theme.css with book-pulse animation
6. **Error Handling** - Added module_discovery_failed error type to ERROR_TYPES with campfire narrative style
7. **Comprehensive Tests** - 66 unit and integration tests covering all acceptance criteria

### File List

| File | Changes |
|------|---------|
| `models.py` | Added ModuleInfo, ModuleDiscoveryResult models. Added module_discovery_failed to ERROR_TYPES. Added exports to __all__. |
| `agents.py` | Added MODULE_DISCOVERY_PROMPT, MODULE_DISCOVERY_RETRY_PROMPT, MODULE_DISCOVERY_MAX_RETRIES, discover_modules(), _parse_module_json(). Added exports to __all__. |
| `app.py` | Added start_module_discovery(), clear_module_discovery_state(), render_module_discovery_loading(). Added imports from agents and models. |
| `styles/theme.css` | Added .module-discovery-loading styles with book-pulse animation, error state styles. |
| `tests/test_story_7_1_module_discovery.py` | New file with 66 comprehensive tests covering models, discovery function, session state caching, and all acceptance criteria. |

---

## Code Review

### Review Date

2026-02-01

### Reviewer

Claude Opus 4.5 (Adversarial Code Review)

### Review Summary

**Total Issues Found: 9**
- HIGH: 2 (auto-fixed)
- MEDIUM: 5 (auto-fixed)
- LOW: 2 (documented only)

All acceptance criteria are met. Test suite passes with 69 tests (68 original + 1 export test fix + 2 new tests added).

### Issues Found and Resolved

#### Issue 1: MEDIUM - Missing input validation for empty response_text

**File:** `agents.py` (line 1232)

**Problem:** The `_parse_module_json` function didn't validate if `response_text` is empty or None before processing. An empty string would raise a confusing `JSONDecodeError` message.

**Fix Applied:** Added early validation check:
```python
if not response_text or not response_text.strip():
    raise json.JSONDecodeError("Empty response text", response_text or "", 0)
```

**Status:** FIXED

#### Issue 2: MEDIUM - Unsanitized error message in logging

**File:** `agents.py` (line 1340)

**Problem:** Error messages from exceptions were logged directly without truncation. LLM responses could contain extremely long strings that could affect log file integrity.

**Fix Applied:** Added message truncation:
```python
error_msg = str(e)[:200] if len(str(e)) > 200 else str(e)
```

**Status:** FIXED

#### Issue 3: HIGH - Incorrect error type used for module discovery failures

**File:** `app.py` (line 3863)

**Problem:** When an `LLMError` was caught in `start_module_discovery()`, the code used `e.error_type` (generic error like `invalid_response`) instead of the specific `module_discovery_failed` error type that was explicitly created for campfire-style messaging.

**Fix Applied:** Changed to use `module_discovery_failed` error type:
```python
error = create_user_error(
    error_type="module_discovery_failed",  # Changed from e.error_type
    provider=e.provider,
    agent=e.agent,
)
```

**Status:** FIXED

#### Issue 4: MEDIUM - Incomplete test assertion

**File:** `tests/test_story_7_1_module_discovery.py` (line 461)

**Problem:** Test `test_parse_skips_invalid_entries` had weak assertion (`assert len(modules) >= 1`) that didn't validate actual behavior.

**Fix Applied:** Added specific assertions to verify correct entries are kept:
```python
assert modules[0].name == "Valid"
assert modules[0].number == 1
if len(modules) >= 2:
    assert modules[1].name == "Also Valid"
```

**Status:** FIXED

#### Issue 5: MEDIUM - Missing test for empty response handling

**File:** `tests/test_story_7_1_module_discovery.py`

**Problem:** No test case validated behavior when empty string or whitespace-only value is passed to `_parse_module_json()`.

**Fix Applied:** Added two new tests:
- `test_parse_empty_response_text_raises_error`
- `test_parse_whitespace_only_response_raises_error`

**Status:** FIXED

#### Issue 6: LOW - CSS animation specificity

**File:** `styles/theme.css`

**Problem:** The `@keyframes book-pulse` animation name could potentially conflict with future animations if reused elsewhere. This is a minor maintainability concern.

**Status:** DOCUMENTED (no fix required)

#### Issue 7: HIGH - Missing exception handling for config loading

**File:** `app.py` (line 3849)

**Problem:** The `load_dm_config()` call inside `start_module_discovery()` could raise exceptions (missing config, invalid YAML) that wouldn't be caught by the `LLMError` handler, causing confusing error propagation.

**Fix Applied:** Added generic exception handler:
```python
except Exception as e:
    logger.error("Module discovery failed with unexpected error: %s", str(e)[:200])
    error = create_user_error(
        error_type="module_discovery_failed",
        provider="unknown",
        agent="dm",
    )
    st.session_state["module_discovery_error"] = error
```

Also added logger initialization in `app.py`:
```python
logger = logging.getLogger("autodungeon.app")
```

**Status:** FIXED

#### Issue 8: LOW - Ineffective spinner pattern

**File:** `app.py` (lines 3911-3913)

**Problem:** The `with st.spinner(""): pass` pattern is a no-op that doesn't provide actual spinner functionality. The comment says "backup/accessibility" but it doesn't provide visible accessibility functionality.

**Status:** DOCUMENTED (no fix required - does not affect functionality)

#### Issue 9: MEDIUM - Missing module exports test update

**File:** `tests/test_agents.py` (line 294)

**Problem:** The `test_all_public_symbols_exported` test in the existing test file didn't include the new exports from story 7.1.

**Fix Applied:** Added new exports to expected set:
```python
# Story 7.1: Module Discovery
"MODULE_DISCOVERY_PROMPT",
"MODULE_DISCOVERY_RETRY_PROMPT",
"MODULE_DISCOVERY_MAX_RETRIES",
"discover_modules",
"_parse_module_json",
```

**Status:** FIXED

### Test Results

```
tests/test_story_7_1_module_discovery.py: 68 passed
tests/test_agents.py::TestModuleExports: 1 passed
Total: 69 tests passed
```

### Code Quality Checks

- **ruff check:** Pre-existing E402 warnings (intentional logging pattern), no new issues
- **ruff format:** All files formatted
- **pyright:** Pre-existing type warnings (LangChain typing, mocked session_state), no new issues

### Pre-existing Issues (Not Story 7.1 Related)

The working copy contains uncommitted changes from other work that cause 2 test failures:
- `test_dm_system_prompt_contains_dice_rolling_guidance` - prompt text changed from "dice rolling tool" to "dm_roll_dice tool"
- `test_pc_system_prompt_template_contains_dice_instructions` - similar change

These are NOT related to story 7.1 and should be addressed separately.

### Acceptance Criteria Verification

| AC | Description | Status |
|----|-------------|--------|
| #1 | System queries DM LLM with correct prompt | PASS |
| #2 | Prompt requests 100 modules in JSON format | PASS |
| #3 | Each module has number, name, description | PASS |
| #4 | Module list stored in session state | PASS |
| #5 | Retry with explicit schema on parse failure | PASS |

### Architecture Compliance

| Pattern | Compliance |
|---------|------------|
| Use existing get_llm factory | PASS |
| Session state for UI state | PASS |
| Pydantic models | PASS |
| LLMError for errors | PASS |
| UserError for display | PASS |
| Campfire error messages | PASS |

### Recommendation

**APPROVED** - Story 7.1 implementation is complete and passes all acceptance criteria. All HIGH and MEDIUM severity issues have been resolved. The code follows established patterns and is well-tested.
