# Story 7.3: Module Context Injection

Status: done

## Code Review (2026-02-01)

### Review Summary
Adversarial code review completed. Implementation is solid with proper error handling, type safety, and test coverage.

### Issues Found

| # | Severity | Issue | Resolution |
|---|----------|-------|------------|
| 1 | MEDIUM | Missing test for malformed module data during deserialization | **FIXED**: Added `test_deserialize_with_malformed_module_raises_validation_error` and `test_deserialize_with_invalid_module_number_raises_validation_error` |
| 2 | MEDIUM | Missing test for `load_checkpoint` graceful error handling with invalid module data | **FIXED**: Added `test_load_checkpoint_handles_malformed_module_gracefully` |
| 3 | LOW | No max_length validation on ModuleInfo name/description fields | Not fixed - acceptable risk as data comes from LLM, not user input |
| 4 | LOW | format_module_context does not escape markdown special characters | Not fixed - acceptable as this goes into system prompt, not rendered HTML |
| 5 | LOW | pyright warnings for datetime.UTC import | Pre-existing issue, not related to Story 7.3 |
| 6 | LOW | ruff E402 warnings in app.py | Pre-existing issue, intentional code organization |

### Tests Added
- `test_deserialize_with_malformed_module_raises_validation_error`
- `test_deserialize_with_invalid_module_number_raises_validation_error`
- `test_load_checkpoint_handles_malformed_module_gracefully`
- `test_format_module_context_with_long_description`

### Test Results
All 30 tests in `tests/test_story_7_3_module_context_injection.py` pass.

### Pre-existing Issues (Not Story 7.3)
- `test_dm_system_prompt_no_broken_continuations` test failure - pre-existing issue with double-space detection in DM_SYSTEM_PROMPT

## Story

As a **DM agent**,
I want **the selected module to be part of my system prompt**,
so that **I can run the adventure with knowledge of setting, NPCs, and plot**.

## Acceptance Criteria

1. **Given** a module has been selected
   **When** the DM agent is initialized
   **Then** the module context is injected into the DM system prompt

2. **Given** the module context injection
   **When** building the DM prompt
   **Then** it includes:
   ```
   ## Campaign Module: [Module Name]
   [Module Description]

   You are running this official D&D module. Draw upon your knowledge of:
   - The setting, locations, and atmosphere
   - Key NPCs, their motivations, and personalities
   - The main plot hooks and story beats
   - Encounters, monsters, and challenges appropriate to this module
   ```

3. **Given** the DM generates responses
   **When** running the selected module
   **Then** responses reflect knowledge of that specific adventure

4. **Given** the module context
   **When** persisted
   **Then** it's saved with the campaign config for session continuity

## Tasks / Subtasks

- [x] Task 1: Add module storage to GameState (AC: #4)
  - [x] 1.1 Add `selected_module: ModuleInfo | None` to GameState TypedDict in models.py
  - [x] 1.2 Update `create_initial_game_state()` to include `selected_module=None`
  - [x] 1.3 Update `populate_game_state()` to handle selected_module parameter
  - [x] 1.4 Ensure Pyright strict mode passes

- [x] Task 2: Update persistence layer for module storage (AC: #4)
  - [x] 2.1 Update `serialize_game_state()` in persistence.py to include selected_module
  - [x] 2.2 Update `deserialize_game_state()` to reconstruct ModuleInfo from saved data
  - [x] 2.3 Handle None case gracefully (freeform mode with no module)
  - [x] 2.4 Add tests for round-trip serialization with module

- [x] Task 3: Create module context formatting function (AC: #2)
  - [x] 3.1 Create `format_module_context(module: ModuleInfo) -> str` in agents.py
  - [x] 3.2 Implement exact prompt format from AC#2 specification
  - [x] 3.3 Include module.name and module.description in formatted output
  - [x] 3.4 Handle edge cases (empty description, special characters)
  - [x] 3.5 Add unit tests for format_module_context()

- [x] Task 4: Inject module context into DM prompt (AC: #1, #3)
  - [x] 4.1 Modify DM system prompt builder in agents.py to accept module parameter
  - [x] 4.2 Append module context section after base DM instructions
  - [x] 4.3 Wire up module from GameState to DM prompt in dm_turn function (agents.py)
  - [ ] 4.4 Verify DM responses reference module content (manual testing)

- [x] Task 5: Wire module from UI to GameState (AC: #1)
  - [x] 5.1 Pass `selected_module` from session_state to game initialization in app.py
  - [x] 5.2 Update `handle_new_session_click()` to accept ModuleInfo
  - [x] 5.3 Ensure module flows through: UI selection -> GameState -> DM prompt
  - [x] 5.4 Handle freeform mode (selected_module=None)

- [x] Task 6: Write comprehensive tests (AC: #1-4)
  - [x] 6.1 Test GameState with and without selected_module
  - [x] 6.2 Test serialization/deserialization preserves module
  - [x] 6.3 Test format_module_context produces correct output
  - [x] 6.4 Test DM prompt includes module context when present
  - [x] 6.5 Test DM prompt omits module section when None
  - [x] 6.6 Integration test: module selection -> game start -> DM prompt contains module

## Dev Notes

### Implementation Strategy

This story connects the module selection UI (Story 7.2) to the DM agent's behavior. The module context needs to flow through three layers:

1. **UI Layer** (app.py) - User selects module, stored in `st.session_state["selected_module"]`
2. **State Layer** (models.py, persistence.py) - Module stored in GameState for persistence
3. **Agent Layer** (agents.py, graph.py) - Module context injected into DM system prompt

### GameState Changes

Add `selected_module` to GameState TypedDict:

```python
# models.py - Add to GameState TypedDict
class GameState(TypedDict):
    # ... existing fields ...
    selected_module: ModuleInfo | None  # NEW: Module for DM context injection
```

### Persistence Changes

The existing serialize/deserialize pattern handles Pydantic models via `.model_dump()`. Extend for ModuleInfo:

```python
# persistence.py - serialize_game_state()
serializable: dict[str, Any] = {
    # ... existing fields ...
    "selected_module": (
        state["selected_module"].model_dump()
        if state.get("selected_module") is not None
        else None
    ),
}

# persistence.py - deserialize_game_state()
# Handle optional ModuleInfo reconstruction
selected_module_data = data.get("selected_module")
selected_module = (
    ModuleInfo(**selected_module_data)
    if selected_module_data is not None
    else None
)
```

### Module Context Format (Exact Specification)

```python
# agents.py
def format_module_context(module: ModuleInfo) -> str:
    """Format module info for DM system prompt injection.

    Args:
        module: The selected ModuleInfo object.

    Returns:
        Formatted markdown section for DM prompt.
    """
    return f"""## Campaign Module: {module.name}
{module.description}

You are running this official D&D module. Draw upon your knowledge of:
- The setting, locations, and atmosphere
- Key NPCs, their motivations, and personalities
- The main plot hooks and story beats
- Encounters, monsters, and challenges appropriate to this module
"""
```

### DM Prompt Integration

The DM system prompt is built in `agents.py`. The module context should be appended after the base instructions but before memory/context sections:

```python
# agents.py - In the DM prompt building section
def build_dm_system_prompt(
    game_config: GameConfig,
    agent_memories: dict[str, AgentMemory],
    characters: dict[str, CharacterConfig],
    selected_module: ModuleInfo | None = None,  # NEW parameter
) -> str:
    """Build complete DM system prompt with optional module context."""

    # 1. Base DM instructions (existing)
    prompt_parts = [DM_BASE_INSTRUCTIONS]

    # 2. Module context (NEW - insert before memory section)
    if selected_module is not None:
        prompt_parts.append(format_module_context(selected_module))

    # 3. Memory and context (existing)
    prompt_parts.append(format_memory_context(agent_memories))

    # 4. Character context (existing)
    prompt_parts.append(format_character_context(characters))

    return "\n\n".join(prompt_parts)
```

### Graph.py Integration

Pass module from GameState to DM prompt builder:

```python
# graph.py - dm_turn node
def dm_turn(state: GameState) -> GameState:
    """Execute DM turn with module context if available."""
    selected_module = state.get("selected_module")

    # Build prompt with module context
    system_prompt = build_dm_system_prompt(
        game_config=state["game_config"],
        agent_memories=state["agent_memories"],
        characters=state["characters"],
        selected_module=selected_module,  # Pass module
    )
    # ... rest of turn execution
```

### UI Wiring

When starting a new game, pass the selected module to GameState initialization:

```python
# app.py - In game start flow
def start_game_with_module():
    """Start game with optional module selection."""
    selected_module = st.session_state.get("selected_module")

    # Create game state with module
    game_state = create_initial_game_state()
    game_state["selected_module"] = selected_module

    # ... continue with game initialization
```

### Session State Flow

```
1. User selects module (Story 7.2)
   -> st.session_state["selected_module"] = ModuleInfo(...)

2. User starts game
   -> selected_module passed to game initialization
   -> GameState["selected_module"] = ModuleInfo(...)

3. Checkpoint saved
   -> selected_module serialized to JSON in turn_XXX.json

4. Session resumed
   -> selected_module deserialized from checkpoint
   -> DM continues with same module context

5. DM turn executes
   -> selected_module read from GameState
   -> Module context injected into DM system prompt
   -> DM generates response with module knowledge
```

### Freeform Mode Handling

When user clicks "Skip - Start Freeform Adventure" in Story 7.2:
- `st.session_state["selected_module"]` = None
- `GameState["selected_module"]` = None
- DM prompt omits the module context section entirely
- DM improvises without specific module guidance

### Testing Strategy

**Unit Tests:**

```python
# tests/test_story_7_3_module_context_injection.py

class TestFormatModuleContext:
    def test_includes_module_name(self):
        module = ModuleInfo(number=1, name="Curse of Strahd", description="Gothic horror")
        result = format_module_context(module)
        assert "## Campaign Module: Curse of Strahd" in result

    def test_includes_module_description(self):
        module = ModuleInfo(number=1, name="Test", description="A test adventure")
        result = format_module_context(module)
        assert "A test adventure" in result

    def test_includes_guidance_bullets(self):
        module = ModuleInfo(number=1, name="Test", description="Desc")
        result = format_module_context(module)
        assert "- The setting, locations, and atmosphere" in result
        assert "- Key NPCs, their motivations" in result

class TestGameStateSerialization:
    def test_serialize_with_module(self):
        state = create_initial_game_state()
        state["selected_module"] = ModuleInfo(
            number=42,
            name="Lost Mine of Phandelver",
            description="Classic starter adventure"
        )
        json_str = serialize_game_state(state)
        data = json.loads(json_str)
        assert data["selected_module"]["name"] == "Lost Mine of Phandelver"

    def test_serialize_without_module(self):
        state = create_initial_game_state()
        state["selected_module"] = None
        json_str = serialize_game_state(state)
        data = json.loads(json_str)
        assert data["selected_module"] is None

    def test_round_trip_preserves_module(self):
        state = create_initial_game_state()
        state["selected_module"] = ModuleInfo(
            number=1,
            name="Test Module",
            description="Test description",
            setting="Forgotten Realms",
            level_range="1-5"
        )
        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)
        assert restored["selected_module"].name == "Test Module"
        assert restored["selected_module"].setting == "Forgotten Realms"

class TestDMPromptWithModule:
    def test_prompt_includes_module_when_present(self):
        module = ModuleInfo(number=1, name="Tomb of Annihilation", description="Jungle death curse")
        prompt = build_dm_system_prompt(
            game_config=GameConfig(),
            agent_memories={},
            characters={},
            selected_module=module,
        )
        assert "Campaign Module: Tomb of Annihilation" in prompt
        assert "Jungle death curse" in prompt

    def test_prompt_omits_module_when_none(self):
        prompt = build_dm_system_prompt(
            game_config=GameConfig(),
            agent_memories={},
            characters={},
            selected_module=None,
        )
        assert "Campaign Module" not in prompt
```

### Edge Cases

1. **Module with empty description** - Still include header and guidance bullets
2. **Module with special characters** - Names like "Hoard of the Dragon Queen" work correctly
3. **Long descriptions** - No truncation in DM prompt (full context needed)
4. **Session restore after module changes** - Use persisted module, ignore session state
5. **Backward compatibility** - Old checkpoints without selected_module field deserialize correctly

### Architecture Compliance

| Pattern | Compliance | Notes |
|---------|------------|-------|
| TypedDict for GameState | YES | ModuleInfo | None follows pattern |
| Pydantic for nested models | YES | ModuleInfo is Pydantic BaseModel |
| Atomic checkpoint writes | YES | Module serialized with full state |
| Asymmetric memory (DM sees all) | YES | Only DM gets module context |
| LLM factory pattern | N/A | No new LLM calls needed |

### Files to Modify

| File | Changes |
|------|---------|
| `models.py` | Add `selected_module: ModuleInfo \| None` to GameState TypedDict. Update `create_initial_game_state()` and `populate_game_state()`. |
| `persistence.py` | Update `serialize_game_state()` and `deserialize_game_state()` to handle selected_module field. |
| `agents.py` | Add `format_module_context(module: ModuleInfo) -> str` function. Modify DM system prompt builder to accept and include module context. |
| `graph.py` | Pass `selected_module` from GameState to DM prompt builder in dm_turn node. |
| `app.py` | Wire `st.session_state["selected_module"]` to game initialization when starting new game. |

### Files to Create

| File | Purpose |
|------|---------|
| `tests/test_story_7_3_module_context_injection.py` | Comprehensive test suite for module context injection |

### FR/NFR Coverage

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| FR59 | Selected module context can be injected into the DM's system prompt for campaign guidance | `format_module_context()` + DM prompt integration |

### Dependencies

- Story 7.1 (Module Discovery) - DONE - provides ModuleInfo model
- Story 7.2 (Module Selection UI) - DONE - provides `st.session_state["selected_module"]`
- Epic 2 (Message Display) - DONE - DM prompt building pattern exists in agents.py
- Epic 4 (Persistence) - DONE - serialize/deserialize pattern exists in persistence.py

### What This Story Implements

1. **GameState module storage** - Store selected module in game state
2. **Persistence layer updates** - Save/load module with checkpoints
3. **Module context formatting** - Standard format for DM prompt injection
4. **DM prompt integration** - Include module context when building DM prompts
5. **UI to GameState wiring** - Flow module selection to game initialization

### What This Story Does NOT Implement

- Module discovery (Story 7.1 - DONE)
- Module selection UI (Story 7.2 - DONE)
- Module-specific encounter tables (future enhancement)
- Module progress tracking (future enhancement)
- Multiple simultaneous modules (out of scope)

### References

- [Source: planning-artifacts/epics-v1.1.md#Story 7.3] - Story requirements
- [Source: planning-artifacts/prd.md#FR59] - Module context injection requirement
- [Source: agents.py] - DM system prompt building patterns
- [Source: persistence.py#serialize_game_state] - Serialization pattern
- [Source: models.py#GameState] - TypedDict pattern with Pydantic models
- [Source: implementation-artifacts/7-1-module-discovery-via-llm-query.md] - ModuleInfo model
- [Source: implementation-artifacts/7-2-module-selection-ui.md] - Session state keys for selected_module
