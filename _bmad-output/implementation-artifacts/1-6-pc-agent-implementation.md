# Story 1.6: PC Agent Implementation

Status: complete

## Story

As a **user watching the game**,
I want **PC agents that respond in-character with distinct, consistent personalities**,
so that **each character feels like a unique individual**.

## Acceptance Criteria

1. **Given** a PC agent configured with name "Shadowmere", class "Rogue", personality "Sardonic wit, trust issues"
   **When** the PC's turn occurs
   **Then** it responds in first person as that character
   **And** the response reflects the sardonic, distrustful personality

2. **Given** multiple PC agents in the party
   **When** they each take turns
   **Then** their voices and decision-making styles are noticeably different

3. **Given** a PC agent with class "Wizard"
   **When** approaching a problem
   **Then** they suggest solutions appropriate to their class (e.g., magic, knowledge)

4. **Given** a PC agent receives dialogue from the DM or another PC
   **When** responding
   **Then** they can engage in natural conversation and react to what was said (FR7)

5. **Given** a situation requiring action
   **When** a PC responds
   **Then** they take actions appropriate to their character class and personality (FR6)

## Tasks / Subtasks

- [x] Task 1: Create PC system prompt template (AC: #1, #2, #3, #5)
  - [x] 1.1 Create `PC_SYSTEM_PROMPT_TEMPLATE` constant in agents.py with personality injection placeholders
  - [x] 1.2 Include first-person roleplay instructions
  - [x] 1.3 Add class-appropriate behavior guidelines (fighter: direct action, rogue: cunning, wizard: magic/knowledge, cleric: support/faith)
  - [x] 1.4 Add personality consistency instructions
  - [x] 1.5 Include collaborative storytelling guidelines (don't contradict established facts)

- [x] Task 2: Implement `create_pc_agent` factory (AC: #1, #2)
  - [x] 2.1 Create `create_pc_agent(config: CharacterConfig) -> Runnable` in agents.py
  - [x] 2.2 Use existing `get_llm()` factory to get the base model
  - [x] 2.3 Bind dice rolling tool to the model for skill checks
  - [x] 2.4 Export in `__all__`

- [x] Task 3: Implement `build_pc_system_prompt` helper (AC: #1, #2, #3)
  - [x] 3.1 Create `build_pc_system_prompt(config: CharacterConfig) -> str` function
  - [x] 3.2 Inject character name, class, and personality into template
  - [x] 3.3 Add class-specific guidance based on character_class field
  - [x] 3.4 Export in `__all__`

- [x] Task 4: Implement `_build_pc_context` helper (AC: #4, #5)
  - [x] 4.1 Create `_build_pc_context(state: GameState, agent_name: str) -> str` function
  - [x] 4.2 PC agents ONLY see their own AgentMemory (strict isolation per architecture)
  - [x] 4.3 Include character's long_term_summary if present
  - [x] 4.4 Include recent entries from character's short_term_buffer
  - [x] 4.5 Add context limit constants (similar to DM)

- [x] Task 5: Implement `pc_turn` node function (AC: #1, #2, #3, #4, #5)
  - [x] 5.1 Create `pc_turn(state: GameState, agent_name: str) -> GameState` in agents.py
  - [x] 5.2 Get CharacterConfig from state (need to add characters dict to GameState)
  - [x] 5.3 Build prompt from: system prompt + PC's own memory context only
  - [x] 5.4 Invoke model with built prompt
  - [x] 5.5 Parse tool calls (dice rolls) from response if present
  - [x] 5.6 Append PC response to ground_truth_log with "[CharacterName]:" prefix
  - [x] 5.7 Update PC's short_term_buffer with response
  - [x] 5.8 Return updated GameState (never mutate input)

- [x] Task 6: Add `characters` dict to GameState (AC: #1, #2)
  - [x] 6.1 Add `characters: dict[str, CharacterConfig]` to GameState TypedDict in models.py
  - [x] 6.2 Update `create_initial_game_state()` to include empty characters dict
  - [x] 6.3 Update type hints throughout

- [x] Task 7: Create `pc_roll_dice` tool (AC: #5)
  - [x] 7.1 Create `@tool` decorated `pc_roll_dice` function in tools.py
  - [x] 7.2 Tool description guides PC when/how to request skill checks
  - [x] 7.3 Export in tools.py `__all__`

- [x] Task 8: Write comprehensive tests
  - [x] 8.1 Test PC system prompt template contains personality placeholders
  - [x] 8.2 Test `build_pc_system_prompt` injects character details correctly
  - [x] 8.3 Test `create_pc_agent` returns valid Runnable with tools bound
  - [x] 8.4 Test `pc_turn` appends to ground_truth_log with character name
  - [x] 8.5 Test `pc_turn` updates PC's own short_term_buffer
  - [x] 8.6 Test PC ONLY has access to their own memory (isolation)
  - [x] 8.7 Test `pc_turn` returns new state (doesn't mutate input)
  - [x] 8.8 Test different character classes produce appropriate system prompts
  - [x] 8.9 Mock LLM calls for deterministic testing

## Dev Notes

### Architecture Compliance (MANDATORY)

**Module Locations (CRITICAL)**

Per architecture.md:
- `agents.py` - Agent definitions, `pc_turn` node function, `create_pc_agent` factory
- `tools.py` - Function tools (pc_roll_dice tool binding)
- `models.py` - GameState TypedDict updates (add characters dict)

[Source: architecture.md#Project Structure]

**Node Naming Convention**

Per architecture.md, node functions follow `{agent}_turn` pattern:
```python
def pc_turn(state: GameState, agent_name: str) -> GameState: ...
```

Node IDs are lowercase agent names: `"fighter"`, `"rogue"`, `"wizard"`, `"cleric"`

Note: `pc_turn` takes an extra `agent_name` parameter to identify which PC is acting. This will be wrapped in lambdas or partial functions when added to LangGraph (Story 1.7).

[Source: architecture.md#Naming Patterns]

**Memory System - PC Isolation (CRITICAL)**

PC agents ONLY see their own AgentMemory (strict isolation):
```python
def _build_pc_context(state: GameState, agent_name: str) -> str:
    # ONLY access this PC's memory - strict isolation
    pc_memory = state["agent_memories"].get(agent_name)
    # NEVER access other agent memories for PC context
```

This is the opposite of DM access. Per architecture:
- DM sees ALL memories (enables dramatic irony, secrets)
- PC agents are isolated (each only knows their own experiences)

[Source: architecture.md#Memory Isolation]

**State Management Pattern**

Per architecture.md, node functions:
1. Take GameState as input
2. Return NEW GameState dict (never mutate input)
3. Use Pydantic models for complex structures

```python
def pc_turn(state: GameState, agent_name: str) -> GameState:
    # Create copies, modify, return new state
    new_log = state["ground_truth_log"].copy()
    new_log.append(f"[{character_name}]: {response}")
    return {**state, "ground_truth_log": new_log}
```

[Source: architecture.md#LangGraph State Machine Architecture]

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR5 | PC Agents can respond in-character | First-person roleplay in system prompt |
| FR6 | PC Agents take class-appropriate actions | Class-specific guidance in prompt |
| FR7 | PC Agents engage in dialogue | Conversational instructions in prompt |
| FR52 | PC Agents exhibit distinct personalities | Personality injection in prompt template |

[Source: prd.md#Agent Behavior, epics.md#Story 1.6]

### PC System Prompt Design

The PC prompt should be a TEMPLATE with placeholders for character-specific content:

```python
PC_SYSTEM_PROMPT_TEMPLATE = '''You are {name}, a {character_class}.

## Your Personality
{personality}

## Roleplay Guidelines

You are playing this character in a D&D adventure. Follow these guidelines:

- **First person only** - Always speak and act as {name}, using "I" and "me"
- **Stay in character** - Your responses should reflect your personality traits
- **Be consistent** - Remember your character's motivations and relationships
- **Collaborate** - Build on what others say and do; don't contradict established facts

## Class Behavior

{class_guidance}

## Actions and Dialogue

When responding:
- Describe your character's actions in first person: "I draw my sword and..."
- Use direct dialogue with quotation marks: "Stay back!" I warn them.
- Express your character's emotions and internal thoughts
- React authentically to what's happening around you

## Dice Rolling

Use the dice rolling tool when:
- You attempt something with uncertain outcome
- You want to make a skill check (Perception, Stealth, etc.)
- The DM hasn't already rolled for you

Keep responses focused - you're one character in a party, not the narrator.
'''
```

### Class-Specific Guidance

Based on character_class, inject appropriate behavior guidance:

```python
CLASS_GUIDANCE = {
    "Fighter": """As a Fighter, you:
- Prefer direct action and combat solutions
- Protect your allies and hold the front line
- Value honor, courage, and martial prowess
- Speak plainly and act decisively""",

    "Rogue": """As a Rogue, you:
- Look for clever solutions and hidden angles
- Prefer stealth, deception, and precision over brute force
- Keep an eye on valuables and escape routes
- Are naturally suspicious and observant""",

    "Wizard": """As a Wizard, you:
- Approach problems with knowledge and arcane insight
- Value learning, research, and magical solutions
- Think before acting, considering magical implications
- Reference your spellbook and arcane studies""",

    "Cleric": """As a Cleric, you:
- Support and protect your allies
- Channel divine power through faith
- Consider the moral and spiritual aspects of situations
- Offer guidance, healing, and wisdom""",
}
```

Default fallback for unknown classes:
```python
"default": """As a {character_class}, you:
- Act according to your class abilities and training
- Make decisions consistent with your background
- Support your party with your unique skills"""
```

### LangGraph Tool Binding (2025/2026 Best Practices)

Same pattern as DM, but with PC-appropriate descriptions:

```python
from langchain_core.tools import tool

@tool
def pc_roll_dice(notation: str) -> str:
    """Roll dice for a skill check or action.

    Use this when:
    - You attempt something risky (climbing, sneaking, persuading)
    - You want to check your perception or investigation
    - You make an attack or use an ability

    Args:
        notation: D&D dice notation (e.g., "1d20+5", "1d20+3")

    Returns:
        Formatted roll result
    """
    result = roll_dice(notation)
    return str(result)

# Bind to model
model_with_tools = model.bind_tools([pc_roll_dice])
```

[Source: LangGraph 0.2 documentation, Story 1.5 implementation]

### Message Flow Pattern

Per architecture.md transcript format, PC responses should use character name:
```json
{
  "turn": 3,
  "timestamp": "2026-01-25T14:36:15Z",
  "agent": "shadowmere",
  "content": "I check the door for traps, running my fingers along the frame...",
  "tool_calls": [{"name": "pc_roll_dice", "args": {"notation": "1d20+7"}, "result": "18"}]
}
```

In ground_truth_log, prefix with character name: `[Shadowmere]: I check the door...`

### Previous Story Intelligence

**From Story 1.5 (DM Agent Implementation):**
- `dm_turn` node function pattern to follow
- `_build_dm_context` helper pattern (invert for PC isolation)
- `create_dm_agent` factory pattern
- `DM_SYSTEM_PROMPT` structure to adapt
- State immutability pattern established
- 166 total project tests (all passing)

**Key Differences from DM:**
1. PC uses TEMPLATE with placeholders; DM uses static prompt
2. PC context is ISOLATED (only own memory); DM reads ALL memories
3. PC response prefixed with character name; DM prefixed with "[DM]:"
4. Need to add `characters` dict to GameState for CharacterConfig access

**From Story 1.4 (Dice Rolling System):**
- `roll_dice(notation: str) -> DiceResult` is available in tools.py
- DiceResult has `__str__` for human-readable output
- Can reuse pattern for `pc_roll_dice` tool

**From Story 1.3 (LLM Provider Integration):**
- `get_llm(provider, model) -> BaseChatModel` is available
- LLMConfigurationError for missing credentials

**From Story 1.2 (Core Game State Models):**
- CharacterConfig model is already defined with all needed fields
- GameState TypedDict pattern established
- AgentMemory model for memory management

### Code Patterns to Follow

**System Prompt Template Pattern (new for PC):**
```python
PC_SYSTEM_PROMPT_TEMPLATE = '''You are {name}, a {character_class}.
...
{class_guidance}
...
'''

def build_pc_system_prompt(config: CharacterConfig) -> str:
    """Build a personalized system prompt for a PC agent."""
    class_guidance = CLASS_GUIDANCE.get(
        config.character_class,
        CLASS_GUIDANCE["default"].format(character_class=config.character_class)
    )
    return PC_SYSTEM_PROMPT_TEMPLATE.format(
        name=config.name,
        character_class=config.character_class,
        personality=config.personality,
        class_guidance=class_guidance,
    )
```

**PC Context Building (isolated):**
```python
PC_CONTEXT_RECENT_EVENTS_LIMIT = 10  # Consistent with DM

def _build_pc_context(state: GameState, agent_name: str) -> str:
    """Build context for a PC - only their own memory (strict isolation)."""
    context_parts: list[str] = []

    pc_memory = state["agent_memories"].get(agent_name)
    if pc_memory:
        if pc_memory.long_term_summary:
            context_parts.append(f"## What You Remember\n{pc_memory.long_term_summary}")
        if pc_memory.short_term_buffer:
            recent = "\n".join(pc_memory.short_term_buffer[-PC_CONTEXT_RECENT_EVENTS_LIMIT:])
            context_parts.append(f"## Recent Events\n{recent}")

    return "\n\n".join(context_parts)
```

**Factory Function Pattern:**
```python
def create_pc_agent(config: CharacterConfig) -> Runnable:
    """Create a PC agent with tool bindings.

    Args:
        config: Character configuration

    Returns:
        Configured chat model with dice rolling tool bound
    """
    base_model = get_llm(config.provider, config.model)
    return base_model.bind_tools([pc_roll_dice])
```

**Export Pattern (expand existing in agents.py):**
```python
__all__ = [
    # ... existing exports
    "PC_SYSTEM_PROMPT_TEMPLATE",
    "CLASS_GUIDANCE",
    "PC_CONTEXT_RECENT_EVENTS_LIMIT",
    "build_pc_system_prompt",
    "create_pc_agent",
    "_build_pc_context",
    "pc_turn",
]
```

### GameState Update Required

Add `characters` dict to GameState to access CharacterConfig during pc_turn:

```python
# In models.py
class GameState(TypedDict):
    ground_truth_log: list[str]
    turn_queue: list[str]
    current_turn: str
    agent_memories: dict[str, AgentMemory]
    game_config: GameConfig
    dm_config: DMConfig
    characters: dict[str, CharacterConfig]  # NEW: Add this
    whisper_queue: list[str]
    human_active: bool
    controlled_character: str | None

def create_initial_game_state() -> GameState:
    return GameState(
        ground_truth_log=[],
        turn_queue=[],
        current_turn="",
        agent_memories={},
        game_config=GameConfig(),
        dm_config=DMConfig(),
        characters={},  # NEW: Add this
        whisper_queue=[],
        human_active=False,
        controlled_character=None,
    )
```

### Testing Strategy

**Mock LLM for Deterministic Tests:**
```python
from unittest.mock import MagicMock, patch

def test_pc_turn_appends_to_log():
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="I draw my sword...")

    with patch("agents.create_pc_agent", return_value=mock_model):
        state = create_test_state_with_character("shadowmere")
        new_state = pc_turn(state, "shadowmere")

        assert len(new_state["ground_truth_log"]) == 1
        assert "[Shadowmere]:" in new_state["ground_truth_log"][0]
```

**Test PC Memory Isolation:**
```python
def test_pc_only_sees_own_memory():
    state = create_initial_game_state()
    state["agent_memories"] = {
        "shadowmere": AgentMemory(short_term_buffer=["I am Shadowmere"]),
        "thor": AgentMemory(short_term_buffer=["I am Thor"]),
    }

    context = _build_pc_context(state, "shadowmere")

    assert "Shadowmere" in context
    assert "Thor" not in context  # MUST NOT see other PC's memory
```

**Test Class-Specific Prompts:**
```python
@pytest.mark.parametrize("class_name,expected_text", [
    ("Fighter", "protect your allies"),
    ("Rogue", "stealth, deception"),
    ("Wizard", "arcane insight"),
    ("Cleric", "divine power"),
])
def test_class_guidance_injection(class_name, expected_text):
    config = CharacterConfig(
        name="Test",
        character_class=class_name,
        personality="Test personality",
        color="#000000",
    )
    prompt = build_pc_system_prompt(config)
    assert expected_text in prompt.lower()
```

### Project Structure Notes

- All new code goes in existing files (agents.py, models.py, tools.py)
- No new files needed for this story
- Tests expand existing test files (tests/test_agents.py, tests/test_models.py)
- Follow flat project layout per architecture

### What NOT To Do

- Do NOT create separate pc.py file (keep in agents.py)
- Do NOT let PC agents read other agents' memories (STRICT ISOLATION)
- Do NOT implement LangGraph workflow yet (that's Story 1.7)
- Do NOT add streaming/async (architecture says synchronous for MVP)
- Do NOT use Optional[str] syntax (use str | None)
- Do NOT mutate GameState input in pc_turn
- Do NOT forget to bind tools to the model
- Do NOT hardcode character names - use CharacterConfig

### Dependencies

This story depends on:
- Story 1.2: GameState, AgentMemory, CharacterConfig models (done)
- Story 1.3: get_llm() factory (done)
- Story 1.4: roll_dice() function (done)
- Story 1.5: dm_turn pattern to follow (done)

This story enables:
- Story 1.7: LangGraph Turn Orchestration (uses pc_turn nodes)
- Story 1.8: Character Configuration System (uses CharacterConfig loading)

### References

- [architecture.md#LangGraph State Machine Architecture] - State patterns
- [architecture.md#Memory System Architecture] - PC memory isolation
- [architecture.md#Naming Patterns] - Node function naming
- [prd.md#Agent Behavior] - FR5, FR6, FR7, FR52 requirements
- [epics.md#Story 1.6] - Full acceptance criteria
- [agents.py] - Existing dm_turn patterns to follow
- [models.py] - CharacterConfig model definition
- [tools.py] - Dice rolling implementation

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Implemented PC_SYSTEM_PROMPT_TEMPLATE with placeholders for name, class, personality, and class_guidance
- Created CLASS_GUIDANCE dict with Fighter, Rogue, Wizard, Cleric guidance text
- Implemented build_pc_system_prompt() that personalizes the template
- Implemented create_pc_agent() factory that binds pc_roll_dice tool
- Implemented _build_pc_context() with strict memory isolation (PC only sees own memory)
- Implemented pc_turn() node function following dm_turn patterns
- Added characters dict to GameState and create_initial_game_state()
- Created pc_roll_dice tool with PC-appropriate description
- Added 45 new tests covering all acceptance criteria
- All 211 tests pass, ruff passes, pyright has 0 errors (19 warnings from LangChain stubs)

### File List

- agents.py - Added PC_SYSTEM_PROMPT_TEMPLATE, CLASS_GUIDANCE, PC_CONTEXT_RECENT_EVENTS_LIMIT, build_pc_system_prompt(), create_pc_agent(), _build_pc_context(), pc_turn()
- models.py - Added characters dict to GameState TypedDict and create_initial_game_state()
- tools.py - Added pc_roll_dice tool
- tests/test_agents.py - Added comprehensive PC agent tests
- tests/test_tools.py - Added pc_roll_dice tests
- tests/test_models.py - Added GameState characters field tests

