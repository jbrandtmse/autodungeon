# Story 1.5: DM Agent Implementation

Status: done

## Story

As a **user watching the game**,
I want **a DM agent that narrates scenes, describes environments, and manages encounters**,
so that **the story unfolds with engaging narration**.

## Acceptance Criteria

1. **Given** a DM agent with a system prompt incorporating improv principles ("Yes, and...")
   **When** the DM's turn occurs
   **Then** it generates narrative text describing the scene, NPCs, or situation
   **And** the response acknowledges and builds on previous player actions

2. **Given** a combat encounter is active
   **When** the DM generates a response
   **Then** it can describe NPC actions and request dice rolls from players

3. **Given** a roleplay encounter is active
   **When** the DM generates NPC dialogue
   **Then** the NPC voices are distinct and consistent with their described personalities

4. **Given** the DM receives dice roll results
   **When** generating the next response
   **Then** the narrative incorporates those results meaningfully (FR54)

5. **Given** the game transitions between encounter types (combat -> roleplay -> exploration)
   **When** the DM narrates
   **Then** the transitions feel natural and the pacing varies appropriately

## Tasks / Subtasks

- [x] Task 1: Create DM system prompt template (AC: #1, #3, #5)
  - [x] 1.1 Create `DM_SYSTEM_PROMPT` constant in agents.py with improv principles ("Yes, and...")
  - [x] 1.2 Include encounter mode awareness (combat, roleplay, exploration)
  - [x] 1.3 Add NPC voice distinctiveness guidelines
  - [x] 1.4 Add pacing and tension management instructions
  - [x] 1.5 Include callback instructions (reference earlier events from context)

- [x] Task 2: Create DMConfig model (AC: #1)
  - [x] 2.1 Add `DMConfig` Pydantic model to models.py with: provider, model, token_limit, name, color
  - [x] 2.2 Set defaults per architecture: provider="gemini", model="gemini-1.5-flash"
  - [x] 2.3 Add DMConfig to GameState TypedDict
  - [x] 2.4 Update `create_initial_game_state()` factory to include dm_config

- [x] Task 3: Implement `create_dm_agent` factory (AC: #1, #4)
  - [x] 3.1 Create `create_dm_agent(config: DMConfig) -> Runnable` in agents.py
  - [x] 3.2 Use existing `get_llm()` factory to get the base model
  - [x] 3.3 Bind dice rolling tool to the model for requesting rolls
  - [x] 3.4 Export in `__all__`

- [x] Task 4: Implement `dm_turn` node function (AC: #1, #2, #3, #4, #5)
  - [x] 4.1 Create `dm_turn(state: GameState) -> GameState` in agents.py
  - [x] 4.2 Build prompt from: system prompt + DM's long_term_summary + short_term_buffer context
  - [x] 4.3 DM reads ALL agent memories (asymmetric access per architecture)
  - [x] 4.4 Invoke model with built prompt
  - [x] 4.5 Parse tool calls (dice rolls) from response if present
  - [x] 4.6 Append DM response to ground_truth_log with "[DM]:" prefix
  - [x] 4.7 Update DM's short_term_buffer with response
  - [x] 4.8 Return updated GameState (never mutate input)

- [x] Task 5: Create dice roll tool binding (AC: #2, #4)
  - [x] 5.1 Create `@tool` decorated `dm_roll_dice` function in tools.py
  - [x] 5.2 Wrapper calls existing `roll_dice()` and returns formatted string
  - [x] 5.3 Tool description guides when/how DM should call for rolls
  - [x] 5.4 Export in tools.py `__all__`

- [x] Task 6: Write comprehensive tests
  - [x] 6.1 Test DM system prompt contains improv principles
  - [x] 6.2 Test `create_dm_agent` returns valid Runnable with tools bound
  - [x] 6.3 Test `dm_turn` appends to ground_truth_log
  - [x] 6.4 Test `dm_turn` updates DM's short_term_buffer
  - [x] 6.5 Test DM has read access to all agent memories
  - [x] 6.6 Test `dm_turn` returns new state (doesn't mutate input)
  - [x] 6.7 Test dice roll tool integration
  - [x] 6.8 Mock LLM calls for deterministic testing

## Dev Notes

### Architecture Compliance (MANDATORY)

**Module Locations (CRITICAL)**

Per architecture.md:
- `agents.py` - Agent definitions, LLM factory, `dm_turn` node function
- `tools.py` - Function tools (dice rolling tool binding)
- `models.py` - Pydantic models (DMConfig)

[Source: architecture.md#Project Structure]

**Node Naming Convention**

Per architecture.md, node functions follow `{agent}_turn` pattern:
```python
def dm_turn(state: GameState) -> GameState: ...
```

Node IDs are lowercase: `"dm"`

[Source: architecture.md#Naming Patterns]

**Memory System - Asymmetric Access**

CRITICAL: DM agent has read access to ALL agent memories:
```python
# DM sees all memories (enables dramatic irony, secrets)
for agent_name, memory in state["agent_memories"].items():
    dm_context += f"\n[{agent_name} knows]: {memory.short_term_buffer}"
```

PC agents only see their own AgentMemory (strict isolation).

[Source: architecture.md#Memory Isolation]

**State Management Pattern**

Per architecture.md, node functions:
1. Take GameState as input
2. Return NEW GameState dict (never mutate input)
3. Use Pydantic models for complex structures

```python
def dm_turn(state: GameState) -> GameState:
    # Create copies, modify, return new state
    new_log = state["ground_truth_log"].copy()
    new_log.append(f"[DM]: {response}")
    return {**state, "ground_truth_log": new_log}
```

[Source: architecture.md#LangGraph State Machine Architecture]

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR2 | DM narrates scenes, describes environments | `dm_turn` with system prompt |
| FR3 | DM controls NPC dialogue and behavior | NPC voice guidelines in prompt |
| FR4 | DM manages encounter flow | Encounter mode awareness |
| FR51 | DM incorporates improv principles | "Yes, and..." in system prompt |
| FR54 | DM uses dice results in narrative | Tool call processing |

[Source: prd.md#Agent Behavior, epics.md#Story 1.5]

### DM System Prompt Design

The DM prompt should incorporate:

**1. Improv Principles ("Yes, and...")**
```
You are a Dungeon Master running a D&D adventure. Follow these improv principles:
- "Yes, and..." - Accept player actions and build on them
- Never deny player creativity outright
- Add unexpected details that enhance the story
```

**2. Encounter Mode Awareness**
```
Encounter types and pacing:
- COMBAT: Action-focused, clear initiative, describe attacks vividly
- ROLEPLAY: Character-driven, distinct NPC voices, emotional beats
- EXPLORATION: Environmental details, discovery, foreshadowing
```

**3. NPC Voice Distinctiveness**
```
When voicing NPCs:
- Give each NPC a unique speech pattern
- Maintain consistency across scenes
- Use descriptive tags: "the merchant says nervously..."
```

**4. Callback Instructions**
```
Reference earlier events naturally:
- Mention consequences of past player decisions
- Weave plot threads from earlier scenes
- Reward player attention to detail
```

### LangGraph Tool Binding (2025/2026 Best Practices)

Per latest LangGraph patterns, bind tools to the model:

```python
from langchain_core.tools import tool

@tool
def dm_roll_dice(notation: str) -> str:
    """Roll dice for a skill check, attack, or saving throw.

    Use this when:
    - A player attempts something with uncertain outcome
    - Combat attacks or damage
    - Saving throws against effects

    Args:
        notation: D&D dice notation (e.g., "1d20+5", "2d6+3")

    Returns:
        Formatted roll result for narrative integration
    """
    result = roll_dice(notation)
    return str(result)

# Bind to model
model_with_tools = model.bind_tools([dm_roll_dice])
```

[Source: LangGraph 0.2 documentation, web research]

### Message Flow Pattern

Per architecture.md transcript format:
```json
{
  "turn": 1,
  "timestamp": "2026-01-25T14:35:22Z",
  "agent": "dm",
  "content": "The tavern door creaks open...",
  "tool_calls": []
}
```

DM responses are prefixed with `[DM]:` in ground_truth_log for clarity.

### Previous Story Intelligence

**From Story 1.4 (Dice Rolling System):**
- `roll_dice(notation: str) -> DiceResult` is available in tools.py
- DiceResult has `__str__` for human-readable output
- Safety limits in place (MAX_DICE_COUNT, MAX_DICE_SIDES)
- All tests pass (126 total project tests)

**From Story 1.3 (LLM Provider Integration):**
- `get_llm(provider, model) -> BaseChatModel` is available
- LLMConfigurationError for missing credentials
- Case-insensitive provider handling
- Supports gemini, claude, ollama

**From Story 1.2 (Core Game State Models):**
- GameState TypedDict with Pydantic models
- AgentMemory with long_term_summary and short_term_buffer
- CharacterConfig model pattern to follow for DMConfig
- `create_initial_game_state()` factory pattern

### Code Patterns to Follow

**Pydantic Model Pattern (from CharacterConfig):**
```python
class DMConfig(BaseModel):
    """Configuration for the Dungeon Master agent."""

    name: str = Field(default="Dungeon Master", description="DM display name")
    provider: str = Field(default="gemini", description="LLM provider")
    model: str = Field(default="gemini-1.5-flash", description="Model name")
    token_limit: int = Field(default=8000, ge=1, description="Context limit")
    color: str = Field(default="#D4A574", description="Gold color for UI")
```

**Export Pattern (from agents.py):**
```python
__all__ = [
    # ... existing exports
    "DMConfig",
    "DM_SYSTEM_PROMPT",
    "create_dm_agent",
    "dm_turn",
]
```

**Factory Function Pattern:**
```python
def create_dm_agent(config: DMConfig) -> BaseChatModel:
    """Create a DM agent with tool bindings.

    Args:
        config: DM configuration

    Returns:
        Configured chat model with dice rolling tool bound
    """
    base_model = get_llm(config.provider, config.model)
    return base_model.bind_tools([dm_roll_dice])
```

### Testing Strategy

**Mock LLM for Deterministic Tests:**
```python
from unittest.mock import MagicMock, patch

def test_dm_turn_appends_to_log():
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="The tavern is quiet...")

    with patch("agents.create_dm_agent", return_value=mock_model):
        state = create_initial_game_state()
        state["agent_memories"]["dm"] = create_agent_memory()

        new_state = dm_turn(state)

        assert len(new_state["ground_truth_log"]) == 1
        assert "[DM]:" in new_state["ground_truth_log"][0]
```

**Test State Immutability:**
```python
def test_dm_turn_does_not_mutate_input():
    state = create_initial_game_state()
    original_log_len = len(state["ground_truth_log"])

    new_state = dm_turn(state)

    # Original state unchanged
    assert len(state["ground_truth_log"]) == original_log_len
    # New state has updates
    assert len(new_state["ground_truth_log"]) > original_log_len
```

### Project Structure Notes

- All new code goes in existing files (agents.py, models.py, tools.py)
- No new files needed for this story
- Tests go in tests/test_agents.py (expand existing)
- Follow flat project layout per architecture

### What NOT To Do

- Do NOT create separate dm.py file (keep in agents.py)
- Do NOT implement PC agents yet (that's Story 1.6)
- Do NOT implement LangGraph workflow yet (that's Story 1.7)
- Do NOT add streaming/async (architecture says synchronous for MVP)
- Do NOT use Optional[str] syntax (use str | None)
- Do NOT mutate GameState input in dm_turn
- Do NOT forget to bind tools to the model

### Dependencies

This story depends on:
- Story 1.2: GameState, AgentMemory models (done)
- Story 1.3: get_llm() factory (done)
- Story 1.4: roll_dice() function (done)

This story enables:
- Story 1.6: PC Agent Implementation (uses same patterns)
- Story 1.7: LangGraph Turn Orchestration (uses dm_turn node)

### References

- [architecture.md#LangGraph State Machine Architecture] - State patterns
- [architecture.md#Memory System Architecture] - Asymmetric memory access
- [architecture.md#Naming Patterns] - Node function naming
- [prd.md#Agent Behavior] - FR51-FR54 requirements
- [epics.md#Story 1.5] - Full acceptance criteria
- [agents.py] - Existing LLM factory patterns
- [models.py] - Pydantic model patterns
- [tools.py] - Dice rolling implementation

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - implementation went smoothly

### Completion Notes List

1. **DM_SYSTEM_PROMPT**: Created comprehensive prompt with improv principles ("Yes, and..."), encounter mode awareness (combat/roleplay/exploration), NPC voice guidelines, and narrative continuity instructions.

2. **DMConfig model**: Added to models.py with defaults: name="Dungeon Master", provider="gemini", model="gemini-1.5-flash", token_limit=8000, color="#D4A574". Includes hex color validation.

3. **create_dm_agent factory**: Returns `Runnable` (not `BaseChatModel`) since `bind_tools()` wraps the model. Uses existing `get_llm()` factory.

4. **dm_turn node function**: Implements asymmetric memory access (DM reads all agent memories). Creates new state without mutation. Handles missing DM memory gracefully.

5. **dm_roll_dice tool**: LangChain `@tool` decorated function that wraps `roll_dice()` and returns human-readable formatted string.

6. **Type annotations**: Some LangChain types are incomplete in stubs, requiring `type: ignore` comments in specific places. This is expected behavior with LangChain's type system.

7. **Tests**: Added 26 new tests covering DM system prompt, create_dm_agent, dm_turn, DMConfig, and dm_roll_dice. Total project tests: 152 (all passing).

### File List

- `agents.py` - Added DM_SYSTEM_PROMPT, create_dm_agent, _build_dm_context, dm_turn, DM_CONTEXT_RECENT_EVENTS_LIMIT, DM_CONTEXT_PLAYER_ENTRIES_LIMIT constants
- `models.py` - Added DMConfig model with provider validation, updated GameState TypedDict, updated create_initial_game_state
- `tools.py` - Added dm_roll_dice LangChain tool
- `tests/test_agents.py` - Added TestDMSystemPrompt, TestCreateDMAgent, TestDMTurn, TestBuildDMContext, TestDMSystemPromptSerialization classes
- `tests/test_models.py` - Added TestDMConfig class with provider validation tests, updated GameState tests
- `tests/test_tools.py` - Added TestDMRollDice class

### Code Review Fixes Applied

1. **[MEDIUM] Added comprehensive tests for `_build_dm_context`** - 8 new tests covering empty state, DM memory, PC memory aggregation, buffer limits, and edge cases
2. **[MEDIUM] Added DM_SYSTEM_PROMPT serialization tests** - 3 tests verifying JSON serialization, markdown structure preservation, and no broken continuations
3. **[LOW] Replaced magic numbers with constants** - Added `DM_CONTEXT_RECENT_EVENTS_LIMIT=10` and `DM_CONTEXT_PLAYER_ENTRIES_LIMIT=3`
4. **[LOW] Added provider validation to DMConfig** - Now validates provider is one of gemini/claude/ollama and normalizes to lowercase

Total tests after review: 166 (all passing)

