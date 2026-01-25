# Story 1.2: Core Game State Models

Status: done

## Story

As a **developer**,
I want **type-safe Pydantic models for game state, agent memory, and character configuration**,
so that **the application has validated, serializable data structures**.

## Acceptance Criteria

1. **Given** the models.py module
   **When** I import GameState
   **Then** it includes: ground_truth_log (list[str]), turn_queue (list[str]), current_turn (str), agent_memories (dict), game_config, human_active (bool), controlled_character (str | None)

2. **Given** the models.py module
   **When** I import AgentMemory
   **Then** it includes: long_term_summary (str), short_term_buffer (list[str]), token_limit (int)
   **And** it can serialize to JSON via `.model_dump_json()`

3. **Given** the models.py module
   **When** I import CharacterConfig
   **Then** it includes: name, character_class, personality, color, provider, model, token_limit
   **And** all fields have appropriate type hints and validation

4. **Given** a CharacterConfig instance with invalid data (e.g., empty name)
   **When** I attempt to create it
   **Then** Pydantic raises a ValidationError with a clear message

## Tasks / Subtasks

- [x] Task 1: Implement AgentMemory model (AC: #2)
  - [x] 1.1 Create AgentMemory Pydantic model with long_term_summary, short_term_buffer, token_limit
  - [x] 1.2 Add default values (empty summary, empty buffer, 8000 token limit)
  - [x] 1.3 Verify JSON serialization works with .model_dump_json()
  - [x] 1.4 Add docstrings explaining memory system purpose

- [x] Task 2: Implement CharacterConfig model (AC: #3, #4)
  - [x] 2.1 Create CharacterConfig Pydantic model with all required fields
  - [x] 2.2 Add field validators for non-empty name, valid color format
  - [x] 2.3 Add sensible defaults (provider="gemini", model="gemini-1.5-flash", token_limit=4000)
  - [x] 2.4 Ensure ValidationError messages are clear and actionable

- [x] Task 3: Implement GameConfig model (dependency for GameState)
  - [x] 3.1 Create GameConfig model for game-level settings
  - [x] 3.2 Include fields: combat_mode (Literal), summarizer_model, party_size
  - [x] 3.3 Add defaults matching architecture specification

- [x] Task 4: Implement GameState TypedDict (AC: #1)
  - [x] 4.1 Create GameState as TypedDict (NOT Pydantic - per architecture)
  - [x] 4.2 Include all required fields with proper type hints
  - [x] 4.3 Ensure agent_memories is dict[str, AgentMemory]
  - [x] 4.4 Add comprehensive docstring explaining LangGraph integration

- [x] Task 5: Create factory functions for state initialization
  - [x] 5.1 Add create_initial_game_state() function
  - [x] 5.2 Add create_agent_memory() factory function
  - [x] 5.3 Ensure factories produce valid, checkpoint-ready state

- [x] Task 6: Write comprehensive tests
  - [x] 6.1 Test AgentMemory creation and serialization
  - [x] 6.2 Test CharacterConfig validation (valid and invalid cases)
  - [x] 6.3 Test GameState structure and type hints
  - [x] 6.4 Test factory functions produce expected output
  - [x] 6.5 Test serialization roundtrip (model_dump_json → model_validate_json)

## Dev Notes

### Architecture Compliance (MANDATORY)

**State Schema: Pydantic in TypedDict (CRITICAL)**

Per architecture.md: "Complex domain objects (AgentMemory, GameConfig, CharacterConfig) are defined as Pydantic models for validation, serialization, and type safety. These are wrapped in a TypedDict for LangGraph compatibility."

```python
# models.py - EXACT PATTERN from architecture.md
class AgentMemory(BaseModel):
    long_term_summary: str
    short_term_buffer: list[str]
    token_limit: int

class GameConfig(BaseModel):
    combat_mode: Literal["Narrative", "Tactical"]
    summarizer_model: str

# TypedDict wrapper for LangGraph
class GameState(TypedDict):
    ground_truth_log: list[str]
    turn_queue: list[str]
    current_turn: str
    agent_memories: dict[str, AgentMemory]
    game_config: GameConfig
    whisper_queue: list[str]
    human_active: bool
    controlled_character: str | None
```

[Source: architecture.md#LangGraph State Machine Architecture]

**Why TypedDict for GameState (NOT Pydantic)?**
LangGraph requires TypedDict for state. Pydantic models are embedded for their validation/serialization benefits.

### Model Naming Conventions

| Convention | Rule | Example |
|------------|------|---------|
| Class names | PascalCase, no suffix | `GameState`, NOT `GameStateModel` |
| Field names | snake_case | `ground_truth_log`, NOT `groundTruthLog` |
| Type hints | Modern Python 3.10+ | `str | None`, NOT `Optional[str]` |

[Source: architecture.md#Implementation Patterns & Consistency Rules]

### CharacterConfig Fields (from epics.md)

```python
class CharacterConfig(BaseModel):
    name: str                    # Character name, e.g., "Shadowmere"
    character_class: str         # D&D class, e.g., "Rogue"
    personality: str             # Personality traits, e.g., "Sardonic wit, trust issues"
    color: str                   # Hex color for UI, e.g., "#6B8E6B"
    provider: str                # LLM provider: "gemini", "claude", "ollama"
    model: str                   # Model name, e.g., "gemini-1.5-flash"
    token_limit: int             # Context limit for this character
```

Note: Use `character_class` NOT `class` (reserved keyword).

[Source: epics.md#Story 1.8 - Character Configuration System]

### Character Color Constants (from UX Design)

```python
# Standard character colors for validation/reference
CHARACTER_COLORS = {
    "dm": "#D4A574",      # Gold
    "fighter": "#C45C4A", # Red
    "rogue": "#6B8E6B",   # Green
    "wizard": "#7B68B8",  # Purple
    "cleric": "#4A90A4",  # Blue
}
```

[Source: prd.md#From UX Design - Visual Identity]

### AgentMemory System Design

Per architecture.md, the memory system has these characteristics:

- **short_term_buffer**: Recent turns, candidates for compression when approaching token_limit
- **long_term_summary**: Compressed history from the "Janitor" summarizer
- **token_limit**: Per-agent limit, checked by Context Manager node

Memory Isolation:
- PC agents only see their own AgentMemory (strict isolation)
- DM agent has read access to ALL agent memories

[Source: architecture.md#Memory System Architecture]

### Serialization Requirements

For checkpoint/restore functionality (Story 4.1), all Pydantic models MUST serialize correctly:

```python
# Serialization
json_str = agent_memory.model_dump_json()

# Deserialization
restored = AgentMemory.model_validate_json(json_str)
```

[Source: architecture.md#Persistence Strategy]

### Existing Code Context

**From Story 1.1:**
- `config.py` has `AgentConfig` and `AgentsConfig` models - DO NOT DUPLICATE
- `models.py` exists but is empty (just docstring)
- All code uses Python 3.10+ type hints (`str | None`, not `Optional`)

**Integration Points:**
- GameState will be used by `graph.py` (Story 1.7)
- AgentMemory will be used by `memory.py` (Story 5.x)
- CharacterConfig will be loaded from YAML by `config.py` (Story 1.8)

### Project Structure Notes

- All models go in `models.py` (per architecture: single file until >500 lines)
- Import from models.py: `from models import GameState, AgentMemory, CharacterConfig`
- Export via `__all__` for explicit public API

### Validation Requirements

**CharacterConfig Validation:**

```python
# These should FAIL with clear messages:
CharacterConfig(name="", ...)           # Empty name
CharacterConfig(color="red", ...)       # Invalid hex format
CharacterConfig(token_limit=-100, ...)  # Negative limit
```

Use Pydantic's `@field_validator` decorator for custom validation.

### References

- [architecture.md#LangGraph State Machine Architecture]
- [architecture.md#Memory System Architecture]
- [architecture.md#Implementation Patterns & Consistency Rules]
- [epics.md#Story 1.2 - Core Game State Models]
- [epics.md#Story 1.8 - Character Configuration System]
- [prd.md#From UX Design - Visual Identity]

### What NOT To Do

- Do NOT make GameState a Pydantic model (must be TypedDict for LangGraph)
- Do NOT use `Optional[str]` syntax (use `str | None`)
- Do NOT duplicate AgentConfig from config.py (different purpose)
- Do NOT add ORM mappings or database concerns (file storage only)
- Do NOT add complex business logic to models (keep them as data containers)
- Do NOT use `class` as a field name (use `character_class`)

### Git Intelligence (from Story 1.1)

Files created in previous story:
- `models.py` - Empty placeholder, now needs implementation
- `config.py` - Has `AgentConfig`, `AgentsConfig`, `AppConfig`
- `tests/test_config.py` - Testing patterns to follow

Key patterns established:
- Pydantic Settings for config
- `__all__` exports in all modules
- Type hints on all functions
- Docstrings on all public classes/functions

### Testing Patterns (from Story 1.1)

Follow the patterns from `tests/test_config.py`:
- Use pytest fixtures for reusable test data
- Test both happy path and error cases
- Verify serialization roundtrips
- Use clear test function names (`test_<thing>_<condition>_<expected>`)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - Implementation completed without issues.

### Completion Notes List

- Implemented all 4 Pydantic models (AgentMemory, CharacterConfig, GameConfig) and 1 TypedDict (GameState)
- AgentMemory: Per-agent memory with long_term_summary, short_term_buffer, token_limit (default 8000)
- CharacterConfig: Character definition with name, character_class, personality, color (hex validated), provider, model, token_limit
- GameConfig: Game settings with combat_mode (Literal["Narrative", "Tactical"]), summarizer_model, party_size
- GameState: TypedDict wrapper for LangGraph with all fields per architecture.md specification
- Factory functions: create_agent_memory() and create_initial_game_state() produce checkpoint-ready state
- All field validators implemented: empty name, invalid hex color, negative token_limit
- Comprehensive docstrings on all models explaining purpose and LangGraph integration
- 25 unit tests covering creation, validation, serialization, roundtrips, and factory functions
- All 36 tests pass (including existing tests - no regressions)
- Ruff linting: All checks passed
- Pyright type checking: 0 errors, 0 warnings

### File List

- models.py (modified) - Core game state models implementation
- tests/test_models.py (created) - Comprehensive test suite for models

### Change Log

- 2026-01-25: Initial implementation of Story 1.2 - Core Game State Models
- 2026-01-25: Code review fixes - Added 7 missing tests for serialization roundtrips and boundary conditions (18→25 tests)
