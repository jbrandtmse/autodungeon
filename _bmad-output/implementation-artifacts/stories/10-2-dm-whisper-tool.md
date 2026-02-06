# Story 10-2: DM Whisper Tool

## Story

As a **DM agent**,
I want **a tool to send private information to individual characters**,
So that **I can create dramatic irony and secrets**.

## Status

**Status:** done
**Epic:** 10 - DM Whisper & Secrets System
**Created:** 2026-02-05
**Implemented:** 2026-02-05
**Reviewed:** 2026-02-05

## Acceptance Criteria

**Given** the tools.py module
**When** I examine DM tools
**Then** there's a `whisper_to_agent()` function

**Given** the whisper tool
**When** called by DM
**Then** it accepts:
```python
def whisper_to_agent(
    character_name: str,
    secret_info: str,
    context: str = ""  # When/why this becomes relevant
) -> str:
    """Send private information to a character that others don't know."""
```

**Given** the DM wants to create a secret
**When** generating a response
**Then** it can call: `whisper_to_agent("Shadowmere", "You notice a concealed door behind the tapestry")`

**Given** a whisper is sent
**When** confirmed
**Then** the tool returns: "Secret shared with Shadowmere"

**Given** the whisper system prompt
**When** DM is initialized
**Then** it includes guidance on using whispers for dramatic effect

## FRs Covered

- FR71: DM can send private information to individual agents
- FR75: Whisper history is tracked per agent (partially - tracking happens, this story enables creation)

## Technical Notes

### Tool Implementation Pattern

Follow the existing tool pattern from `dm_roll_dice` and `dm_update_character_sheet`:

1. **Tool Decorator**: Use `@tool` decorator from `langchain_core.tools`
2. **Schema Binding**: The `@tool` decorator creates the schema for LangChain
3. **Execution Intercept**: Like `dm_update_character_sheet`, the actual execution happens in `dm_turn()` which has access to game state

```python
# In tools.py
@tool
def dm_whisper_to_agent(
    character_name: str,
    secret_info: str,
    context: str = ""
) -> str:
    """Send private information to a character that others don't know.

    Use this tool when:
    - A character alone notices something others don't
    - You want to create dramatic irony (character knows something)
    - A character receives private information from an NPC
    - You want to set up future plot reveals

    IMPORTANT: Whispers are private - only the target character will know.
    Other characters and players watching won't see the whisper content
    until it's dramatically revealed.

    Args:
        character_name: The character's name (e.g., "Thorin", "Shadowmere").
        secret_info: The private information to share with this character.
        context: Optional context about when/why this becomes relevant.

    Returns:
        Confirmation message.

    Examples:
        - whisper_to_agent("Shadowmere", "You notice a concealed door behind the tapestry")
        - whisper_to_agent("Thorin", "The merchant's ring bears the mark of the Thieves Guild", "Thorin's background as a guard")
        - whisper_to_agent("Elara", "Your divine sense tingles - something undead lurks nearby")
    """
    # Tool schema only - execution intercepted in dm_turn()
    return f"Secret shared with {character_name}"
```

### Agent Binding

Add the whisper tool to the DM agent in `agents.py`:

```python
def create_dm_agent(config: DMConfig) -> Runnable:
    base_model = get_llm(config.provider, config.model)
    return base_model.bind_tools([dm_roll_dice, dm_update_character_sheet, dm_whisper_to_agent])
```

### Tool Execution in dm_turn()

Add whisper handling in the tool call loop in `dm_turn()`:

```python
elif tool_name == "dm_whisper_to_agent":
    tool_result = _execute_whisper(
        tool_args,
        state.get("agent_secrets", {}),
        state.get("session_number", 1)  # for turn_created
    )
    logger.info("DM whispered to agent: %s", tool_args.get("character_name"))
```

### Whisper Execution Helper

Add helper function in `agents.py`:

```python
def _execute_whisper(
    tool_args: dict[str, object],
    agent_secrets: dict[str, "AgentSecrets"],
    turn_number: int,
) -> str:
    """Execute a whisper from DM to agent.

    Creates a new Whisper object and adds it to the target agent's secrets.

    Args:
        tool_args: Tool call arguments with character_name, secret_info, context.
        agent_secrets: Mutable dict of agent secrets (updated in place).
        turn_number: Current turn number for turn_created.

    Returns:
        Confirmation or error message string.
    """
    from models import AgentSecrets, create_whisper

    character_name = tool_args.get("character_name", "")
    secret_info = tool_args.get("secret_info", "")
    context = tool_args.get("context", "")

    # Validate inputs
    if not character_name or not isinstance(character_name, str):
        return "Error: character_name is required and must be a string."
    if not secret_info or not isinstance(secret_info, str):
        return "Error: secret_info is required and must be a string."

    # Normalize character name to lowercase for agent key lookup
    agent_key = character_name.lower()

    # Create the whisper
    whisper = create_whisper(
        from_agent="dm",
        to_agent=agent_key,
        content=secret_info,
        turn_created=turn_number,
    )

    # Optionally store context in whisper (could add as notes field later)
    # For now, context is informational for DM but not stored

    # Add to agent's secrets
    if agent_key not in agent_secrets:
        agent_secrets[agent_key] = AgentSecrets()

    # Create new whispers list with this whisper added
    current_secrets = agent_secrets[agent_key]
    new_whispers = current_secrets.whispers.copy()
    new_whispers.append(whisper)
    agent_secrets[agent_key] = current_secrets.model_copy(update={"whispers": new_whispers})

    return f"Secret shared with {character_name}"
```

### DM System Prompt Update

Add whisper guidance to `DM_SYSTEM_PROMPT` in agents.py:

```python
## Private Whispers

Use the dm_whisper_to_agent tool to send private information to individual characters:

- **Perception checks**: When one character notices something others don't
- **Background knowledge**: When a character's history gives them unique insight
- **Secret communications**: When an NPC whispers to a specific character
- **Divine/magical senses**: When a character's abilities reveal hidden information

Examples:
- "You notice the barkeep slipping a note under the counter" (to the observant rogue)
- "Your training as a city guard recognizes these as counterfeit coins" (to the fighter)
- "Your divine sense detects a faint aura of undeath from the cellar" (to the paladin)

Whispers create dramatic irony and player engagement. The whispered character can choose
when and how to share (or hide) this information from the party.
```

### GameState Updates

The `dm_turn()` function must update the returned GameState with modified `agent_secrets`:

```python
return GameState(
    # ... existing fields ...
    agent_secrets=updated_secrets,  # Add this
)
```

### Exports

Add to `__all__` in tools.py:
- `dm_whisper_to_agent`

Add to `__all__` in agents.py:
- `_execute_whisper` (for testing)

## Tasks

1. [x] Add `dm_whisper_to_agent` @tool function to tools.py with docstring
2. [x] Add `dm_whisper_to_agent` to `__all__` exports in tools.py
3. [x] Bind `dm_whisper_to_agent` to DM agent in `create_dm_agent()`
4. [x] Add `_execute_whisper()` helper function in agents.py
5. [x] Add `_execute_whisper` to `__all__` exports in agents.py
6. [x] Add whisper tool call handling in `dm_turn()` tool loop
7. [x] Update dm_turn() to track and return modified agent_secrets
8. [x] Update DM_SYSTEM_PROMPT with whisper guidance section
9. [x] Add unit tests for `dm_whisper_to_agent` tool schema
10. [x] Add unit tests for `_execute_whisper()` helper
11. [x] Add unit tests for input validation (empty name, empty secret)
12. [x] Add unit tests for whisper creation and storage
13. [x] Add integration test for DM agent invoking whisper tool
14. [x] Add test for agent_secrets state update in dm_turn()
15. [x] Verify whispers persist through checkpoint save/load (already covered by Story 10.1 tests)

## Dependencies

- **Story 10.1** (done): Provides Whisper, AgentSecrets models and create_whisper() factory
- **Story 8.4** (done): Provides pattern for tool execution interception in dm_turn()

## Test Approach

### Unit Tests (test_story_10_2_dm_whisper_tool.py)

1. **Tool Schema Tests**
   - Tool has correct name and parameters
   - Tool docstring exists
   - Tool returns expected format

2. **Execute Whisper Tests**
   - Valid whisper creates Whisper object
   - Whisper added to correct agent's secrets
   - Agent secrets created if not exists
   - Input validation (empty character_name, empty secret_info)
   - Character name normalized to lowercase

3. **Integration Tests**
   - DM agent has whisper tool bound
   - dm_turn handles whisper tool calls
   - agent_secrets updated in returned state
   - Multiple whispers to same agent accumulate

### Manual Verification

Run the app and verify DM can use whispers:
```bash
streamlit run app.py
# Start new adventure, observe DM creating secrets
```

## Implementation Notes

### Files Modified

1. **tools.py**
   - Added `dm_whisper_to_agent` @tool function with comprehensive docstring
   - Added to `__all__` exports

2. **agents.py**
   - Imported `dm_whisper_to_agent` from tools
   - Bound tool to DM agent in `create_dm_agent()`
   - Added `_execute_whisper()` helper function
   - Added `_execute_whisper` to `__all__` exports
   - Added whisper tool handling in `dm_turn()` tool loop
   - Added tracking for `updated_secrets` in dm_turn()
   - Updated returned GameState to include `agent_secrets`
   - Added "Private Whispers" section to `DM_SYSTEM_PROMPT`

3. **tests/test_story_10_2_dm_whisper_tool.py** (new)
   - 37 unit tests covering:
     - Tool schema validation (7 tests)
     - _execute_whisper helper function (14 tests) - including unknown agent warnings
     - DM agent binding (2 tests)
     - DM system prompt (4 tests)
     - dm_turn() integration (5 tests)
     - Multiple whispers handling (3 tests)
     - pc_turn agent_secrets preservation (2 tests) - verifies critical bug fix

### Design Decisions

1. **Turn Number**: Used `len(ground_truth_log)` as turn_number for whisper creation (consistent with game progression tracking)

2. **Character Name Normalization**: Character names are normalized to lowercase for agent key lookup, matching the existing pattern for agent keys

3. **Context Parameter**: The optional `context` parameter is accepted but not stored in the Whisper - it's informational guidance for the DM

4. **Immutable State Updates**: Used Pydantic's `model_copy(update=...)` pattern to maintain immutability when adding whispers to agent secrets

### Test Results

All 37 tests pass (after code review fixes):
```
tests/test_story_10_2_dm_whisper_tool.py: 37 passed in ~7.5s
```

Existing Story 10.1 tests verified (47 passed).

## Code Review (2026-02-05)

### Issues Found and Fixed

**ISSUE 1: CRITICAL - pc_turn() Does Not Propagate agent_secrets** (HIGH - AUTO-FIXED)
- **Location:** `agents.py`, lines 1626-1642 (pc_turn return statement)
- **Problem:** The `pc_turn()` function returned a new `GameState` but did NOT include the `agent_secrets` field. This would cause whispers to disappear from state after any PC turn.
- **Fix:** Added `agent_secrets=state.get("agent_secrets", {})` to the returned GameState.
- **Tests Added:** `TestPcTurnAgentSecrets` class with 2 tests verifying pc_turn preserves agent_secrets.

**ISSUE 2: Missing Validation for Unknown Agent Names** (MEDIUM - AUTO-FIXED)
- **Location:** `agents.py`, `_execute_whisper()` function
- **Problem:** The whisper tool accepted any character name, even if it didn't exist in the game.
- **Fix:** Added optional `valid_agents` parameter to `_execute_whisper()`. When provided, whispers to unknown agents log a warning but still proceed (LLM may use character names).
- **Tests Added:** `test_execute_whisper_warns_on_unknown_agent` and `test_execute_whisper_no_warning_for_valid_agent`.

**ISSUE 3: Inconsistent Confirmation Message** (MEDIUM - AUTO-FIXED)
- **Location:** `agents.py`, `_execute_whisper()` function
- **Problem:** Confirmation message used original character name case ("Thorin") while storage used lowercase key ("thorin"), causing inconsistency.
- **Fix:** Changed confirmation to use normalized agent key: `f"Secret shared with {agent_key}"` for consistency.
- **Tests Updated:** Modified assertions to expect lowercase in confirmation messages.

### Issues Documented (LOW - Not Auto-Fixed)

**ISSUE 5: No Length Limit on secret_info Content** (LOW)
- **Location:** `agents.py`, `_execute_whisper()` and `tools.py` `dm_whisper_to_agent`
- **Problem:** No validation on the length of `secret_info` string. An LLM could send very long whispers.
- **Impact:** Minor - potential for resource inefficiency but not critical.
- **Recommendation:** Consider adding max length validation in future iteration.

**ISSUE 6: Minor Type Annotation Improvements Possible** (LOW)
- **Location:** `tools.py`, `dm_whisper_to_agent()` function
- **Problem:** Return type annotation could be more explicit about confirmation format.
- **Impact:** Documentation quality only.

### Summary

- **Issues Found:** 6 (1 HIGH, 3 MEDIUM, 2 LOW)
- **Issues Auto-Fixed:** 3 (1 HIGH, 2 MEDIUM)
- **Issues Documented:** 2 (LOW - deferred)
- **New Tests Added:** 4
- **Final Test Count:** 37 tests (up from 33)
- **All Tests Pass:** Yes
