# Story 1.4: Dice Rolling System

Status: done

## Story

As a **player or DM agent**,
I want **a dice rolling function that supports standard D&D notation**,
so that **game mechanics can be resolved with random outcomes**.

## Acceptance Criteria

1. **Given** the tools.py module with `roll_dice(notation: str)` function
   **When** I call `roll_dice("1d20")`
   **Then** it returns a result between 1 and 20 inclusive
   **And** the result includes the notation, individual rolls, and total

2. **Given** a notation with modifiers like "1d20+5"
   **When** I call `roll_dice("1d20+5")`
   **Then** the modifier is added to the total correctly

3. **Given** a multi-dice notation like "3d6"
   **When** I call `roll_dice("3d6")`
   **Then** it rolls 3 separate d6 dice and sums them
   **And** the result includes each individual roll

4. **Given** complex notation like "2d6+1d4+3"
   **When** I call `roll_dice("2d6+1d4+3")`
   **Then** it handles multiple dice types and modifiers correctly

5. **Given** invalid notation like "abc" or "d"
   **When** I call `roll_dice()` with it
   **Then** it raises a ValueError with a helpful message

## Tasks / Subtasks

- [x] Task 1: Create DiceResult model (AC: #1)
  - [x] 1.1 Create `DiceResult` Pydantic model in tools.py with fields: notation, rolls, modifier, total
  - [x] 1.2 Add `__str__` method for human-readable output (e.g., "3d6+2: [4, 2, 5] + 2 = 13")
  - [x] 1.3 Export in `__all__`

- [x] Task 2: Implement `roll_dice` function (AC: #1, #2, #3, #4)
  - [x] 2.1 Create `roll_dice(notation: str) -> DiceResult` function
  - [x] 2.2 Parse standard dice notation: `NdS` (N dice of S sides)
  - [x] 2.3 Handle optional modifiers: `+M` or `-M`
  - [x] 2.4 Handle complex notation with multiple dice groups: `2d6+1d4+3`
  - [x] 2.5 Use Python's `random.randint` for each die roll
  - [x] 2.6 Return DiceResult with all individual rolls and computed total

- [x] Task 3: Implement validation (AC: #5)
  - [x] 3.1 Validate notation format with regex
  - [x] 3.2 Raise ValueError for empty/None input
  - [x] 3.3 Raise ValueError for invalid notation with message showing the invalid input
  - [x] 3.4 Validate die sides > 0 and count > 0
  - [x] 3.5 Add reasonable limits (e.g., max 100 dice, max 1000 sides) to prevent abuse

- [x] Task 4: Write comprehensive tests
  - [x] 4.1 Test basic rolls: 1d20, 1d6, 1d4, 1d8, 1d10, 1d12, 1d100
  - [x] 4.2 Test modifiers: 1d20+5, 1d20-2, 2d6+3
  - [x] 4.3 Test multi-dice: 3d6, 4d6, 8d6
  - [x] 4.4 Test complex notation: 2d6+1d4+3, 1d20+1d4
  - [x] 4.5 Test invalid inputs raise ValueError
  - [x] 4.6 Test edge cases: d20 (implicit 1), 1d20+0
  - [x] 4.7 Test result bounds are correct
  - [x] 4.8 Mock random.randint to test deterministic outcomes

## Dev Notes

### Architecture Compliance (MANDATORY)

**Module Location (CRITICAL)**

Per architecture.md, dice rolling belongs in `tools.py`:

```
tools.py   # Function tools (dice rolling, scene gen)
```

[Source: architecture.md#Project Structure]

**Transcript Format Integration**

Per architecture.md, tool calls are logged in transcripts:

```json
{
  "turn": 42,
  "timestamp": "2026-01-25T14:35:22Z",
  "agent": "rogue",
  "content": "I check the door for traps.",
  "tool_calls": [{"name": "roll_dice", "args": {"notation": "1d20+7"}, "result": 18}]
}
```

[Source: architecture.md#Transcript Format]

**FR Coverage**

- FR54: DM Agent can use dice roll results to inform narrative outcomes
- FR55: System can execute dice rolls with standard D&D notation

[Source: prd.md#Agent Behavior, epics.md#Story 1.4]

### Implementation Decision: Custom vs Library

**Decision: Custom Implementation (No External Library)**

While the `d20` library exists and is excellent for complex D&D mechanics, this project should use a custom implementation because:

1. **Minimal Dependencies** - The project already has many LLM-related dependencies
2. **Simple Requirements** - We only need basic `NdS+M` notation, not advanced features like `4d6kh3` (keep highest)
3. **Full Control** - Custom implementation allows exact output format for transcript logging
4. **Architecture Alignment** - tools.py is meant for function tools, keeping it self-contained
5. **Learning/Research Value** - This is a passion project with research goals

**If advanced features needed later** (advantage rolls, drop lowest, etc.), consider migrating to `d20` library.

### Dice Notation Grammar

Standard D&D notation to support:

```
<roll> ::= <dice_group> ( ("+" | "-") <dice_group_or_mod> )*
<dice_group> ::= [<count>] "d" <sides>
<dice_group_or_mod> ::= <dice_group> | <modifier>
<count> ::= <positive_integer>  (defaults to 1 if omitted)
<sides> ::= <positive_integer>
<modifier> ::= <integer>
```

**Examples:**
- `1d20` - Roll one 20-sided die
- `d20` - Same as 1d20 (implicit count)
- `3d6` - Roll three 6-sided dice, sum them
- `1d20+5` - Roll d20 and add 5
- `2d6+1d4+3` - Roll 2d6 + 1d4 + 3
- `1d20-2` - Roll d20 and subtract 2

### DiceResult Model Design

```python
from pydantic import BaseModel, Field

class DiceResult(BaseModel):
    """Result of a dice roll with full breakdown.

    Attributes:
        notation: The original dice notation (e.g., "2d6+3")
        rolls: List of individual die results grouped by dice type
               e.g., {"2d6": [4, 2], "1d4": [3]} for "2d6+1d4"
        modifier: The total modifier (can be negative)
        total: The final computed total
    """
    notation: str
    rolls: dict[str, list[int]] = Field(default_factory=dict)
    modifier: int = 0
    total: int

    def __str__(self) -> str:
        """Human-readable format for narrative display."""
        parts = []
        for dice, values in self.rolls.items():
            parts.append(f"{dice}: {values}")
        roll_str = ", ".join(parts)
        if self.modifier > 0:
            return f"{self.notation}: [{roll_str}] + {self.modifier} = {self.total}"
        elif self.modifier < 0:
            return f"{self.notation}: [{roll_str}] - {abs(self.modifier)} = {self.total}"
        else:
            return f"{self.notation}: [{roll_str}] = {self.total}"
```

### Regex Pattern for Parsing

```python
import re

# Pattern to match dice notation components
DICE_PATTERN = re.compile(
    r"(\d*)d(\d+)",  # Match NdS where N is optional
    re.IGNORECASE
)

# Pattern to validate full notation
NOTATION_PATTERN = re.compile(
    r"^(\d*d\d+)([+-](\d*d\d+|\d+))*$",
    re.IGNORECASE
)
```

### Randomness Implementation

```python
import random

def _roll_single_die(sides: int) -> int:
    """Roll a single die with the given number of sides."""
    return random.randint(1, sides)

def _roll_dice_group(count: int, sides: int) -> list[int]:
    """Roll multiple dice and return individual results."""
    return [_roll_single_die(sides) for _ in range(count)]
```

### Safety Limits

To prevent abuse (e.g., `999999d999999`):

```python
MAX_DICE_COUNT = 100      # Maximum dice in a single group
MAX_DICE_SIDES = 1000     # Maximum sides on a die
MAX_TOTAL_DICE = 100      # Maximum total dice across all groups

class DiceValidationError(ValueError):
    """Raised when dice notation exceeds safety limits."""
    pass
```

### Integration with Future Stories

**Story 1.5 (DM Agent):** Will use `roll_dice` when narrating combat or skill checks:
```python
result = roll_dice("1d20+5")
narrative = f"The rogue attempts to pick the lock... {result}"
```

**Story 1.6 (PC Agents):** PC agents will call `roll_dice` via LangGraph tool binding:
```python
from langchain_core.tools import tool

@tool
def roll_dice_tool(notation: str) -> str:
    """Roll dice using standard D&D notation."""
    result = roll_dice(notation)
    return str(result)
```

### Testing Strategy

**Deterministic Testing with Mock:**

```python
from unittest.mock import patch

def test_roll_dice_1d20_deterministic():
    """Test 1d20 with mocked random for deterministic result."""
    with patch("tools.random.randint", return_value=15):
        result = roll_dice("1d20")
        assert result.total == 15
        assert result.rolls == {"1d20": [15]}
```

**Bounds Testing:**

```python
def test_roll_dice_bounds():
    """Test that rolls are within valid bounds."""
    for _ in range(100):
        result = roll_dice("1d20")
        assert 1 <= result.total <= 20
```

**Error Testing:**

```python
import pytest

@pytest.mark.parametrize("invalid_notation", [
    "",
    "abc",
    "d",
    "1d",
    "d0",
    "0d6",
    "-1d6",
    "1d-6",
])
def test_roll_dice_invalid_notation(invalid_notation):
    """Test that invalid notations raise ValueError."""
    with pytest.raises(ValueError):
        roll_dice(invalid_notation)
```

### Project Structure Notes

- tools.py is in flat project root (per architecture)
- Import as: `from tools import roll_dice, DiceResult`
- Export via `__all__` for explicit public API
- Follows established patterns from agents.py and models.py

### Previous Story Intelligence

**From Story 1.3 (LLM Provider Integration):**
- Used `__all__` exports consistently
- Custom exception class pattern: `LLMConfigurationError`
- Case-insensitive input handling (`.lower()` normalization)
- Comprehensive test coverage with mocking
- Type hints using Python 3.10+ syntax (`str | None` not `Optional`)

**From Story 1.2 (Core Game State Models):**
- Pydantic models with Field() and validators
- Docstrings on all public classes/functions
- Factory functions pattern (`create_agent_memory`)

**From Story 1.1 (Project Foundation):**
- Test patterns in tests/ directory
- Ruff for linting, Pyright for type checking
- All tests must pass before commit

### Git Intelligence

Recent commits show consistent patterns:
- ac0c393: Story 1.3 - LLM factory with match/case
- b4434b4: Story 1.2 - Pydantic models
- 341b9df: Story 1.1 - Config foundation

Files to modify:
- `tools.py` - Currently just a docstring placeholder
- `tests/test_tools.py` - New file for tool tests

### What NOT To Do

- Do NOT use external dice libraries (keep dependencies minimal)
- Do NOT add LangGraph tool binding yet (that's Story 1.5/1.6)
- Do NOT add narrative formatting beyond basic __str__ (UI handles that)
- Do NOT support advanced notation like `4d6kh3` (keep highest) for MVP
- Do NOT use `Optional[str]` syntax (use `str | None`)
- Do NOT forget to validate edge cases (d20 without count, 0d6, etc.)

### References

- [architecture.md#Project Structure] - tools.py location
- [architecture.md#Transcript Format] - tool_calls logging format
- [prd.md#Agent Behavior] - FR54, FR55 dice requirements
- [epics.md#Story 1.4] - Full acceptance criteria
- [agents.py] - Pattern for exports, exceptions, validation
- [models.py] - Pydantic model patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No issues encountered during implementation.

### Completion Notes List

- Implemented `DiceResult` Pydantic model with notation, rolls, modifier, and total fields
- Added `__str__` method for human-readable output (e.g., "3d6+2: [3d6: [4, 2, 5]] + 2 = 13")
- Implemented `roll_dice(notation: str | None) -> DiceResult` function with full D&D notation support
- Supports: basic rolls (1d20), modifiers (+5, -2), multi-dice (3d6), complex notation (2d6+1d4+3)
- Validation: regex pattern matching, empty/None checks, helpful error messages
- Safety limits: MAX_DICE_COUNT=100, MAX_DICE_SIDES=1000, MAX_TOTAL_DICE=100
- Added 70 comprehensive tests in test_tools.py covering all acceptance criteria
- All 126 project tests pass
- Code passes ruff linting and pyright type checking

### File List

- tools.py (modified) - Added DiceResult model, roll_dice function, validation, safety limits
- tests/test_tools.py (created) - 70 tests for dice rolling functionality

## Change Log

- 2026-01-25: Implemented Story 1.4 Dice Rolling System - all ACs satisfied
- 2026-01-25: Code Review Fixes (AI):
  - Fixed dict key collision bug when same dice type appears twice (1d6+1d6)
  - Added whitespace handling in notation (e.g., "1d20 + 5" now works)
  - Added 4 new tests: duplicate dice type, duplicate multi-dice, whitespace, negative total

