# Story 10-1: Whisper Data Model

## Story

As a **developer**,
I want **a data model for private whispers between DM and agents**,
So that **secrets can be tracked and managed**.

## Status

**Status:** done
**Epic:** 10 - DM Whisper & Secrets System
**Created:** 2026-02-05
**Reviewed:** 2026-02-05

## Acceptance Criteria

**Given** the models.py module
**When** I import Whisper and AgentSecrets
**Then** they define:
```python
class Whisper(BaseModel):
    id: str
    from_agent: str  # "dm" or "human"
    to_agent: str    # character name
    content: str
    turn_created: int
    revealed: bool = False
    turn_revealed: Optional[int] = None

class AgentSecrets(BaseModel):
    whispers: list[Whisper] = []

    def active_whispers(self) -> list[Whisper]:
        return [w for w in self.whispers if not w.revealed]
```

**Given** the GameState
**When** extended
**Then** it includes `agent_secrets: dict[str, AgentSecrets]`

**Given** whispers
**When** serialized with checkpoints
**Then** they persist and can be restored

## FRs Covered

- FR71: DM can send private information to individual agents
- FR75: Whisper history is tracked per agent

## Technical Notes

### Data Model Design

- `Whisper.id` should use UUID for unique identification (use `uuid.uuid4().hex` or similar)
- `from_agent` can be "dm" for DM-initiated whispers or "human" for player-initiated whispers to DM
- `to_agent` is the character name (lowercase, matching agent keys like "shadowmere", "thorin")
- `turn_created` references the turn number when the whisper was created
- `revealed` tracks whether the secret has been dramatically revealed in narrative
- `turn_revealed` is only set when `revealed=True`, tracking when the reveal occurred

### GameState Integration

- Add `agent_secrets: dict[str, AgentSecrets]` to the `GameState` TypedDict
- Keys are agent names (character names or "dm" for human whispers to DM)
- Initialize empty `AgentSecrets` for each agent in `create_initial_game_state()` and `populate_game_state()`

### Serialization

- Extend `serialize_game_state()` in persistence.py to handle `agent_secrets`
- Use `.model_dump()` pattern consistent with existing models (agent_memories, character_sheets)
- Extend `deserialize_game_state()` to reconstruct `AgentSecrets` with `Whisper` objects

### Validation

- Whisper fields should have appropriate validators:
  - `id` must be non-empty
  - `from_agent` should be "dm" or "human"
  - `to_agent` should be non-empty (actual agent validation deferred to runtime)
  - `content` must be non-empty
  - `turn_created` must be >= 0
  - `turn_revealed` must be >= `turn_created` when set

### Export to __all__

- Add `Whisper` and `AgentSecrets` to the `__all__` list in models.py

## Tasks

1. [x] Add `Whisper` Pydantic model to models.py with all fields and validators
2. [x] Add `AgentSecrets` Pydantic model with `active_whispers()` method
3. [x] Add `agent_secrets` field to GameState TypedDict
4. [x] Update `create_initial_game_state()` to initialize empty agent_secrets
5. [x] Update `populate_game_state()` to initialize agent_secrets for each agent
6. [x] Update `serialize_game_state()` to serialize agent_secrets
7. [x] Update `deserialize_game_state()` to deserialize agent_secrets
8. [x] Add factory function `create_whisper()` for convenient whisper creation
9. [x] Add Whisper and AgentSecrets to __all__ exports
10. [x] Add unit tests for Whisper model validation
11. [x] Add unit tests for AgentSecrets.active_whispers() method
12. [x] Add unit tests for serialization/deserialization round-trip
13. [x] Add integration tests for checkpoint save/restore with whispers

## Dev Agent Record

### Implementation Date
2026-02-05

### Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `models.py` | Modified | Added Whisper, AgentSecrets models, create_whisper factory, updated GameState TypedDict and factory functions |
| `persistence.py` | Modified | Extended serialize/deserialize functions to handle agent_secrets |
| `tests/test_story_10_1_whisper_data_model.py` | Created | 43 comprehensive unit and integration tests |
| `tests/test_persistence.py` | Modified | Updated expected_keys and sample_game_state fixture to include agent_secrets |

### Implementation Details

#### Whisper Model (models.py lines 359-424)
- Full Pydantic model with all required fields
- VALID_SOURCES class variable for allowed from_agent values ("dm", "human")
- field_validator for from_agent normalization to lowercase
- model_validator to ensure turn_revealed consistency:
  - Must be set when revealed=True
  - Must be None when revealed=False
  - Must be >= turn_created when set

#### AgentSecrets Model (models.py lines 427-449)
- Container model for whispers list
- active_whispers() method returns unrevealed whispers

#### Factory Function (models.py lines 452-474)
- create_whisper() generates UUID hex ID automatically
- Takes from_agent, to_agent, content, turn_created

#### GameState Integration (models.py)
- Added agent_secrets to TypedDict definition
- create_initial_game_state() initializes with empty dict
- populate_game_state() creates AgentSecrets for each agent in turn_queue

#### Serialization (persistence.py)
- serialize_game_state() uses .model_dump() pattern
- deserialize_game_state() reconstructs Whisper objects from dicts
- Backward compatible: handles old checkpoints without agent_secrets

### Test Coverage
- 47 new tests in test_story_10_1_whisper_data_model.py (updated after code review)
- All validation scenarios covered
- Serialization roundtrip tests
- Checkpoint save/load integration tests
- Backward compatibility test for old checkpoints

### Verification

```bash
# All tests pass
python -m pytest tests/test_story_10_1_whisper_data_model.py -v  # 47 passed
python -m pytest tests/test_models.py -v  # 75 passed
python -m pytest tests/test_persistence.py -v  # 338 passed
python -m ruff check models.py persistence.py  # All checks passed
```

## Code Review Record

### Review Date
2026-02-05

### Reviewer
Claude Opus 4.5 (BMAD Code Review Workflow)

### Issues Found and Fixed

| # | Severity | Issue | Location | Resolution |
|---|----------|-------|----------|------------|
| 1 | MEDIUM | Missing `to_agent` normalization to lowercase | `models.py` line 380-382 | Added `to_agent_normalized` field validator that converts input to lowercase, matching the documented behavior of "Target agent name (lowercase, matching agent keys)" |
| 2 | MEDIUM | Missing test for factory function normalization | `tests/test_story_10_1_whisper_data_model.py` | Added `test_create_whisper_normalizes_to_agent` and `test_create_whisper_normalizes_from_agent` tests |
| 3 | MEDIUM | Missing whitespace-only content validation | `models.py` Whisper.content field | Added `content_not_whitespace_only` field validator that rejects empty or whitespace-only content |
| 4 | MEDIUM | Missing test for whitespace-only content | `tests/test_story_10_1_whisper_data_model.py` | Added `test_whisper_whitespace_only_content_raises` test |
| 5 | LOW | Documentation gap - no helper method for whisper reveal | N/A | Documented as acceptable - Pydantic models use immutable pattern; users create new objects with `revealed=True` |
| 6 | LOW | No docstring for VALID_SOURCES class variable | `models.py` line 376 | Acceptable - documented in class docstring |

### Files Modified During Code Review
- `models.py`: Added `to_agent_normalized` and `content_not_whitespace_only` validators
- `tests/test_story_10_1_whisper_data_model.py`: Added 4 new tests (total now 47)

### Post-Review Verification
```bash
python -m pytest tests/test_story_10_1_whisper_data_model.py -v  # 47 passed
python -m pytest tests/test_models.py tests/test_persistence.py --tb=short  # 413 passed
python -m ruff check models.py tests/test_story_10_1_whisper_data_model.py  # All checks passed
```
