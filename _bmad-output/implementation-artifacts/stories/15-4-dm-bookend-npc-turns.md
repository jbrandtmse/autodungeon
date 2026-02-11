# Story 15.4: DM Bookend & NPC Turns

Status: ready-for-dev

## Epic

Epic 15: Combat Initiative System

## Story

As a **game engine developer**,
I want **the DM node to detect whether the current combat turn is a bookend turn or an NPC turn and receive an appropriately modified system prompt with context injection**,
So that **during tactical combat the DM narrates round transitions distinctly from NPC actions, and each NPC acts with its own personality, tactics, and stats injected into the DM's prompt**.

## Priority

High (enables NPC combat behavior and round narration -- without this story, all "dm" and "dm:npc_name" turns in the initiative order produce identical generic DM narration)

## Estimate

Medium (system prompt modification, context injection, current_turn plumbing, comprehensive tests)

## Dependencies

- Story 15-1 (Combat State Model & Detection): **done** -- provides `CombatState`, `NpcProfile` models, `combat_state` field on `GameState`, `npc_profiles` dict with personality/tactics/hp/ac per NPC.
- Story 15-2 (Initiative Rolling & Turn Reordering): **done** -- provides `_execute_start_combat()` / `_execute_end_combat()` in agents.py, tool interception in `dm_turn()`, populates `combat_state.initiative_order`, `combat_state.npc_profiles`, `combat_state.round_number`.
- Story 15-3 (Combat-Aware Graph Routing): **in-dev** -- modifies `route_to_next_agent()` to follow `combat_state.initiative_order` during combat, routing all `"dm:npc_name"` entries to the DM node. Story 15-3 also handles `current_turn` lookup in `initiative_order` and round increment in `context_manager()`.
- `combat_state.initiative_order` format: `["dm", "dm:goblin_1", "shadowmere", "dm:goblin_2", "thorin", "brother_aldric", "elara"]` where `"dm"` at index 0 is the bookend turn and `"dm:npc_name"` entries are individual NPC turns.

## Acceptance Criteria

1. **Given** `combat_state.active` is `True` and `current_turn` is `"dm"` (the bookend entry at position 0 in `initiative_order`), **When** `dm_turn()` executes, **Then** the DM receives a combat bookend system prompt addendum instructing it to narrate the round opening (round number, environmental updates, battlefield summary) and NOT act for any specific NPC.

2. **Given** `combat_state.active` is `True` and `current_turn` is `"dm:goblin_1"` (an NPC initiative entry), **When** `dm_turn()` executes, **Then** the DM receives an NPC turn system prompt addendum containing the NPC's profile (name, HP, AC, personality, tactics, conditions) and instructions to narrate only that NPC's action.

3. **Given** an NPC turn (`current_turn` starts with `"dm:"`), **When** `dm_turn()` builds messages, **Then** the human message includes an NPC turn prompt with the NPC's name, initiative roll, HP/AC status, personality, tactics, and any active conditions from the `NpcProfile`.

4. **Given** `dm_turn()` completes during an NPC turn (`current_turn` starts with `"dm:"`), **When** the return `GameState` is constructed, **Then** `current_turn` is set to the full `"dm:npc_name"` value (not just `"dm"`) so that `route_to_next_agent()` can find the correct position in `initiative_order` and advance to the next entry.

5. **Given** `dm_turn()` completes during a bookend turn (`current_turn` is `"dm"` with combat active), **When** the return `GameState` is constructed, **Then** `current_turn` is set to `"dm"` (unchanged from current behavior).

6. **Given** `combat_state.active` is `False` (exploration/roleplay mode), **When** `dm_turn()` executes, **Then** the DM receives the standard system prompt with no combat-specific addendum (behavior unchanged from pre-15-4).

7. **Given** an NPC turn for an NPC not found in `combat_state.npc_profiles` (edge case), **When** `dm_turn()` looks up the NPC profile, **Then** it falls back gracefully with a minimal prompt ("It is now {npc_name}'s turn. Narrate their action.") and logs a warning.

8. **Given** a bookend turn, **When** the DM narrates, **Then** the ground truth log entry is prefixed with `[DM]:` (standard DM attribution, same as non-combat DM turns).

9. **Given** an NPC turn for `"dm:goblin_1"`, **When** the DM narrates, **Then** the ground truth log entry is prefixed with `[DM]:` (DM attribution, since the DM is acting for the NPC -- NPC identity is conveyed through the narrative text, not the log prefix).

10. **Given** an NPC turn, **When** `dm_turn()` appends to the DM's memory buffer, **Then** the buffer entry uses `[DM]:` prefix (same as bookend turns -- DM memory tracks all DM-generated content uniformly).

11. **Given** `dm_turn()` is called and needs to determine its turn type, **When** it reads `current_turn` from the state, **Then** it determines the turn type as: (a) non-combat if `combat_state.active` is False, (b) bookend if `current_turn == "dm"` and combat is active, (c) NPC turn if `current_turn.startswith("dm:")` and combat is active.

12. **Given** the bookend prompt addendum, **When** the DM generates a response, **Then** the addendum includes the current `round_number`, a reminder to summarize the battlefield, and optionally a list of combatants with their HP/status for environmental awareness.

13. **Given** `dm_turn()` is currently hardcoded to return `current_turn="dm"` (agents.py line 1791), **When** this story is implemented, **Then** the return `current_turn` is set dynamically: to the incoming `state["current_turn"]` value during combat (preserving `"dm"` for bookend or `"dm:npc_name"` for NPC turns), or `"dm"` for non-combat turns.

## Tasks / Subtasks

- [ ] Task 1: Add combat turn type detection helper to `agents.py` (AC: #11)
  - [ ] 1.1: Define `_get_combat_turn_type(state: GameState) -> Literal["non_combat", "bookend", "npc_turn"]` helper function
  - [ ] 1.2: Check `combat_state.active` -- if False (or combat_state missing), return `"non_combat"`
  - [ ] 1.3: Check `state["current_turn"]` -- if `"dm"`, return `"bookend"`; if starts with `"dm:"`, return `"npc_turn"`; else return `"non_combat"` (defensive fallback)

- [ ] Task 2: Add bookend prompt builder to `agents.py` (AC: #1, #5, #8, #12)
  - [ ] 2.1: Define `_build_combat_bookend_prompt(state: GameState) -> str` function
  - [ ] 2.2: Include `combat_state.round_number` in the prompt ("Round {N} begins.")
  - [ ] 2.3: Include a combatant summary listing all entries in `initiative_order` with their HP/status (PCs from character_sheets, NPCs from npc_profiles)
  - [ ] 2.4: Instruct the DM to narrate the round opening, describe environmental changes, and set the scene
  - [ ] 2.5: Explicitly instruct the DM NOT to act for any specific NPC (that happens on their individual turns)

- [ ] Task 3: Add NPC turn prompt builder to `agents.py` (AC: #2, #3, #7)
  - [ ] 3.1: Define `_build_npc_turn_prompt(state: GameState, npc_key: str) -> str` function
  - [ ] 3.2: Look up `npc_key` in `combat_state.npc_profiles`. If not found, log warning and return minimal fallback prompt.
  - [ ] 3.3: Include NPC name, HP (current/max), AC, initiative roll (from `initiative_rolls`), personality, tactics, conditions
  - [ ] 3.4: Instruct the DM to narrate ONLY this NPC's action (attack, movement, ability use, etc.)
  - [ ] 3.5: Instruct the DM to stay in character for the NPC using its personality and tactics

- [ ] Task 4: Modify `dm_turn()` to inject combat-specific prompts (AC: #1, #2, #3, #6, #8, #9, #10)
  - [ ] 4.1: After building the base `system_prompt_parts`, call `_get_combat_turn_type(state)`
  - [ ] 4.2: If `"bookend"`, append `_build_combat_bookend_prompt(state)` to `system_prompt_parts`
  - [ ] 4.3: If `"npc_turn"`, extract `npc_key` from `current_turn` (split on `":"`, take index 1), append `_build_npc_turn_prompt(state, npc_key)` to `system_prompt_parts`
  - [ ] 4.4: If `"non_combat"`, no changes (standard DM prompt)
  - [ ] 4.5: For NPC turns, replace the generic "Continue the adventure." human message with the NPC-specific turn prompt from `_build_npc_turn_prompt()`

- [ ] Task 5: Update `dm_turn()` return to set `current_turn` dynamically (AC: #4, #5, #13)
  - [ ] 5.1: Change the hardcoded `current_turn="dm"` (line 1791) to `current_turn=state["current_turn"]` when combat is active
  - [ ] 5.2: For non-combat turns, keep `current_turn="dm"` (existing behavior)
  - [ ] 5.3: The logic: if `combat_state.active` is True, set `current_turn=state["current_turn"]` (which preserves `"dm"` for bookend or `"dm:goblin_1"` for NPC turns); else set `current_turn="dm"`

- [ ] Task 6: Add combat prompt constants to `agents.py` (AC: #1, #2)
  - [ ] 6.1: Define `DM_COMBAT_BOOKEND_PROMPT_TEMPLATE` constant with placeholders for round_number and combatant_summary
  - [ ] 6.2: Define `DM_NPC_TURN_PROMPT_TEMPLATE` constant with placeholders for npc_name, hp_current, hp_max, ac, initiative_roll, personality, tactics, conditions

- [ ] Task 7: Write tests in `tests/test_story_15_4_dm_bookend_npc_turns.py` (AC: #1-#13)
  - [ ] 7.1: `class TestGetCombatTurnType` -- turn type detection
  - [ ] 7.2: `class TestBuildCombatBookendPrompt` -- bookend prompt builder
  - [ ] 7.3: `class TestBuildNpcTurnPrompt` -- NPC turn prompt builder
  - [ ] 7.4: `class TestDmTurnBookend` -- dm_turn integration with bookend turn
  - [ ] 7.5: `class TestDmTurnNpcTurn` -- dm_turn integration with NPC turn
  - [ ] 7.6: `class TestDmTurnNonCombat` -- dm_turn unchanged for non-combat
  - [ ] 7.7: `class TestDmTurnCurrentTurnReturn` -- current_turn set correctly in return state
  - [ ] 7.8: `class TestNpcTurnEdgeCases` -- missing NPC profile, empty conditions, etc.

## Dev Notes

### Turn Type Detection

The key challenge is that `dm_turn()` is called for THREE distinct purposes during combat:
1. **Non-combat turn**: `combat_state.active == False`. Standard DM narration (exploration/roleplay).
2. **Bookend turn**: `combat_state.active == True` and `current_turn == "dm"`. Round transition narration.
3. **NPC turn**: `combat_state.active == True` and `current_turn.startswith("dm:")`. DM acts as a specific NPC.

The detection helper should be placed near the top of agents.py alongside other helper functions:

```python
def _get_combat_turn_type(
    state: GameState,
) -> Literal["non_combat", "bookend", "npc_turn"]:
    """Determine the type of DM turn based on combat state.

    Args:
        state: Current game state.

    Returns:
        "non_combat" if no active combat,
        "bookend" if DM round-start narration turn,
        "npc_turn" if DM is acting for a specific NPC.
    """
    combat = state.get("combat_state")
    if not combat or not isinstance(combat, CombatState) or not combat.active:
        return "non_combat"

    current = state.get("current_turn", "dm")
    if current.startswith("dm:"):
        return "npc_turn"
    return "bookend"
```

### Bookend Prompt Template

```python
DM_COMBAT_BOOKEND_PROMPT_TEMPLATE = """
## Combat Round {round_number}

You are narrating the start of combat round {round_number}. Your role is to set the scene for this round.

**Your task:**
- Summarize the battlefield state and any changes from the previous round
- Describe environmental details, ongoing effects, or dramatic tension
- Set the stage for the combatants who will act this round
- Do NOT act for any specific NPC or monster -- their turns will come individually

**Current Combatants:**
{combatant_summary}

Keep this narration concise (2-4 sentences). Focus on atmosphere and tactical awareness.
"""
```

### NPC Turn Prompt Template

```python
DM_NPC_TURN_PROMPT_TEMPLATE = """
## NPC Turn: {npc_name}

You are now acting as **{npc_name}** for their combat turn.

**{npc_name}'s Status:**
- HP: {hp_current}/{hp_max} | AC: {ac} | Initiative: {initiative_roll}
- Personality: {personality}
- Tactics: {tactics}
{conditions_line}

**Your task:**
- Narrate {npc_name}'s action this round (attack, movement, ability, etc.)
- Stay in character using {npc_name}'s personality and tactics
- Focus ONLY on {npc_name}'s action -- do not narrate other combatants' turns
- Describe the action dramatically and with tactical detail

Respond as the DM narrating {npc_name}'s action in third person.
"""
```

### Combatant Summary for Bookend Turn

The bookend prompt should include a quick status overview of all combatants. Build this from `initiative_order`, `character_sheets`, and `npc_profiles`:

```python
def _build_combatant_summary(state: GameState) -> str:
    """Build a brief combatant status summary for the DM bookend prompt."""
    combat = state.get("combat_state")
    if not combat:
        return ""

    lines: list[str] = []
    character_sheets = state.get("character_sheets", {})

    for entry in combat.initiative_order:
        if entry == "dm":
            continue  # Skip bookend entry itself
        if entry.startswith("dm:"):
            npc_key = entry.split(":", 1)[1]
            npc = combat.npc_profiles.get(npc_key)
            if npc:
                roll = combat.initiative_rolls.get(entry, "?")
                status = f"HP {npc.hp_current}/{npc.hp_max}"
                if npc.conditions:
                    status += f" [{', '.join(npc.conditions)}]"
                lines.append(f"- {npc.name} (Init {roll}): {status}")
            else:
                lines.append(f"- {npc_key} (Init ?): Unknown NPC")
        else:
            # PC entry
            sheet = character_sheets.get(entry)
            roll = combat.initiative_rolls.get(entry, "?")
            if sheet:
                status = f"HP {sheet.hp_current}/{sheet.hp_max}"
                if hasattr(sheet, "conditions") and sheet.conditions:
                    status += f" [{', '.join(sheet.conditions)}]"
                lines.append(f"- {sheet.name} (Init {roll}): {status}")
            else:
                lines.append(f"- {entry} (Init {roll})")

    return "\n".join(lines) if lines else "No combatants listed."
```

### Modifying `dm_turn()` -- Prompt Injection Point

The combat-specific prompt addendum should be appended to `system_prompt_parts` (agents.py line 1553-1557), AFTER the module context and BEFORE the messages list is built. This ensures the combat instructions are part of the system prompt:

```python
# Build system prompt with optional module context (Story 7.3)
system_prompt_parts: list[str] = [DM_SYSTEM_PROMPT]
selected_module = state.get("selected_module")
if selected_module is not None:
    system_prompt_parts.append(format_module_context(selected_module))

# Add combat-specific prompt addendum (Story 15.4)
combat_turn_type = _get_combat_turn_type(state)
if combat_turn_type == "bookend":
    system_prompt_parts.append(_build_combat_bookend_prompt(state))
elif combat_turn_type == "npc_turn":
    npc_key = state["current_turn"].split(":", 1)[1]
    system_prompt_parts.append(_build_npc_turn_prompt(state, npc_key))

full_system_prompt = "\n\n".join(system_prompt_parts)
```

### Modifying `dm_turn()` -- Human Message Override for NPC Turns

For NPC turns, the generic "Continue the adventure." human message should be replaced with a more specific prompt:

```python
# Build messages for the model
messages: list[BaseMessage] = [SystemMessage(content=full_system_prompt)]
if context:
    messages.append(HumanMessage(content=f"Current game context:\n\n{context}"))

# Story 15.4: Use turn-type-specific human message
if combat_turn_type == "npc_turn":
    npc_key = state["current_turn"].split(":", 1)[1]
    npc = state.get("combat_state", CombatState()).npc_profiles.get(npc_key)
    npc_name = npc.name if npc else npc_key
    messages.append(HumanMessage(
        content=f"It is now {npc_name}'s turn in combat. Narrate their action."
    ))
elif combat_turn_type == "bookend":
    combat = state.get("combat_state", CombatState())
    messages.append(HumanMessage(
        content=f"Begin round {combat.round_number} of combat. Set the scene."
    ))
else:
    messages.append(HumanMessage(content="Continue the adventure."))
```

### Modifying `dm_turn()` -- `current_turn` Return Value

Currently, `dm_turn()` hardcodes `current_turn="dm"` at line 1791. This must be changed so that `route_to_next_agent()` (modified in Story 15-3) can find the correct position in `initiative_order`:

```python
# Story 15.4: Set current_turn dynamically for combat routing
combat_state_for_return = (
    updated_combat_state
    if updated_combat_state is not None
    else state.get("combat_state", CombatState())
)
if combat_state_for_return.active:
    return_current_turn = state["current_turn"]  # Preserve "dm" or "dm:npc_name"
else:
    return_current_turn = "dm"

return GameState(
    ...
    current_turn=return_current_turn,
    ...
)
```

**CRITICAL**: This change is essential for Story 15-3's routing to work correctly. Without it, every DM/NPC turn would set `current_turn="dm"`, and `route_to_next_agent()` would always find position 0 (the bookend) in `initiative_order`, causing an infinite loop.

### NPC Key Extraction

The NPC key is extracted from `current_turn` by splitting on `":"`:

```python
npc_key = state["current_turn"].split(":", 1)[1]
# "dm:goblin_1" -> "goblin_1"
# "dm:klarg" -> "klarg"
```

Use `split(":", 1)` (maxsplit=1) to handle edge cases where NPC names might contain colons (unlikely but defensive).

### Log Entry Format

Both bookend and NPC turns use `[DM]:` prefix in the ground truth log (agents.py line 1755). This is unchanged from current behavior because the DM agent generates all this content. The NPC's identity is conveyed through the narrative text itself (e.g., "[DM]: Goblin 1 draws its rusty scimitar and slashes at Thorin...").

This matches tabletop D&D where the DM describes all NPC actions from the DM's perspective.

### Memory Buffer Entries

Both bookend and NPC turn responses are appended to the DM's memory buffer with `[DM]:` prefix (agents.py line 1766). This is correct because the DM's memory should track all content it generated, regardless of whether it was a bookend narration or an NPC action.

### Files to Modify

1. **`agents.py`** -- Add `_get_combat_turn_type()`, `_build_combat_bookend_prompt()`, `_build_npc_turn_prompt()`, `_build_combatant_summary()` helper functions; add `DM_COMBAT_BOOKEND_PROMPT_TEMPLATE` and `DM_NPC_TURN_PROMPT_TEMPLATE` constants; modify `dm_turn()` to inject combat prompts and set `current_turn` dynamically
2. **`tests/test_story_15_4_dm_bookend_npc_turns.py`** -- **NEW** test file

### Files NOT to Modify

- **`models.py`** -- No changes. `CombatState` and `NpcProfile` already defined (Story 15-1).
- **`tools.py`** -- No changes. Initiative rolling and combat tools are Story 15-1/15-2.
- **`graph.py`** -- No changes. Combat-aware routing is Story 15-3. The `current_turn` plumbing in this story ensures Story 15-3's routing works correctly.
- **`persistence.py`** -- No changes. `CombatState` serialization already handled (Story 15-1).
- **`app.py`** -- No changes. Combat UI is Story 15-5.
- **`config.py`** -- No changes.
- **`memory.py`** -- No changes.
- **`styles/theme.css`** -- No changes.

### Test Approach

Create `tests/test_story_15_4_dm_bookend_npc_turns.py`. Use class-based test organization matching project convention.

**`class TestGetCombatTurnType`:**
- Test returns `"non_combat"` when `combat_state.active` is False
- Test returns `"non_combat"` when `combat_state` is missing from state
- Test returns `"non_combat"` when `combat_state` is a plain dict (defensive)
- Test returns `"bookend"` when `combat_state.active` is True and `current_turn == "dm"`
- Test returns `"npc_turn"` when `combat_state.active` is True and `current_turn == "dm:goblin_1"`
- Test returns `"npc_turn"` for various NPC names (`"dm:wolf"`, `"dm:klarg"`, `"dm:bug_bear_chief"`)
- Test returns `"bookend"` when `current_turn` is unexpected PC name during active combat (defensive fallback)

**`class TestBuildCombatBookendPrompt`:**
- Test includes round_number in output
- Test includes combatant summary with NPC and PC entries
- Test handles empty initiative_order gracefully
- Test includes PC HP from character_sheets
- Test includes NPC HP from npc_profiles
- Test includes NPC conditions in summary
- Test skips "dm" bookend entry from combatant list

**`class TestBuildNpcTurnPrompt`:**
- Test includes NPC name, HP, AC, initiative roll
- Test includes personality and tactics
- Test includes conditions when present
- Test handles empty personality/tactics gracefully
- Test falls back gracefully when NPC key not found in npc_profiles
- Test logs warning when NPC not found

**`class TestDmTurnBookend`:**
- Test DM receives bookend system prompt addendum during combat
- Test bookend prompt includes round number
- Test human message is "Begin round N of combat. Set the scene."
- Test `current_turn` is `"dm"` in return state
- Test ground truth log entry uses `[DM]:` prefix
- Test DM memory buffer entry uses `[DM]:` prefix
- Mock the LLM to avoid real API calls

**`class TestDmTurnNpcTurn`:**
- Test DM receives NPC turn system prompt addendum during combat
- Test NPC prompt includes NPC profile data
- Test human message mentions the NPC name
- Test `current_turn` is `"dm:goblin_1"` in return state (not just "dm")
- Test ground truth log entry uses `[DM]:` prefix
- Test NPC turn with goblin profile
- Test NPC turn with boss monster profile (different personality/tactics)
- Mock the LLM to avoid real API calls

**`class TestDmTurnNonCombat`:**
- Test DM receives standard system prompt (no combat addendum)
- Test human message is "Continue the adventure."
- Test `current_turn` is `"dm"` in return state
- Test behavior unchanged from pre-15-4

**`class TestDmTurnCurrentTurnReturn`:**
- Test `current_turn="dm"` when combat is not active
- Test `current_turn="dm"` when combat is active and turn type is bookend
- Test `current_turn="dm:goblin_1"` when combat is active and turn type is NPC
- Test `current_turn="dm"` when `_execute_end_combat()` just deactivated combat (updated_combat_state.active is False)

**`class TestNpcTurnEdgeCases`:**
- Test NPC key not found in npc_profiles (fallback prompt)
- Test NPC with empty personality and tactics strings
- Test NPC with multiple conditions
- Test NPC at 0 HP (still gets a turn -- Story 15-6 handles skipping)
- Test NPC key extraction with simple name ("dm:wolf" -> "wolf")
- Test NPC key extraction with underscore name ("dm:goblin_1" -> "goblin_1")

Build minimal `GameState` dicts for testing. Mock `create_dm_agent` and the LLM `invoke()` to avoid real API calls. Use `unittest.mock.patch` for the DM agent creation.

### Integration with Story 15-3

This story has a critical interaction with Story 15-3 (Combat-Aware Graph Routing):

**Story 15-3** expects that after a `"dm:goblin_1"` turn, `current_turn` is set to `"dm:goblin_1"` so that `route_to_next_agent()` can look up position in `initiative_order` and advance. Without this story's change to `current_turn` in the `dm_turn()` return, routing would break.

If Story 15-3 is implemented BEFORE this story, the routing will be correct in structure but `current_turn` will always be `"dm"` (from the hardcoded return), causing the routing to always find position 0 and loop. Story 15-4's `current_turn` fix completes the routing chain.

### Prompt Constants Location

Place the new prompt template constants after `DM_SYSTEM_PROMPT` (agents.py ~line 249) alongside the other prompt constants. Add them to `__all__` for testability:
- `"DM_COMBAT_BOOKEND_PROMPT_TEMPLATE"`
- `"DM_NPC_TURN_PROMPT_TEMPLATE"`

### Helper Function Location

Place the new helper functions in agents.py after the existing `_build_dm_context()` function (~line 1370) and before `dm_turn()` (~line 1501). This groups all DM context/prompt building functions together:
- `_get_combat_turn_type()` -- ~line 1370
- `_build_combatant_summary()` -- ~line 1390
- `_build_combat_bookend_prompt()` -- ~line 1430
- `_build_npc_turn_prompt()` -- ~line 1460

### Edge Case: Combat Starts and Ends in Same Turn

If the DM calls `dm_start_combat` and `dm_end_combat` in the same turn (unusual but possible), the `updated_combat_state` will be the reset state (from `_execute_end_combat`). The `current_turn` logic should check the FINAL `combat_state` (after tool calls), not the initial state. So the check at return time should use `combat_state_for_return.active`.

### Edge Case: `dm_start_combat` Called During NPC Turn

This should not happen (combat tools are only meaningful during the bookend or non-combat DM turns), but if it does, the tool interception in `dm_turn()` will handle it normally since tool interception is independent of turn type.

### Existing Patterns to Follow

- **Helper function naming**: `_build_dm_context()`, `_build_pc_context()`, `_build_pc_turn_prompt()` -- follow with `_build_combat_bookend_prompt()`, `_build_npc_turn_prompt()`
- **System prompt building**: `system_prompt_parts` list pattern (line 1553-1557) already supports appending additional context sections
- **Prompt template constants**: `DM_SYSTEM_PROMPT`, `PC_SYSTEM_PROMPT_TEMPLATE` -- follow with combat-specific templates
- **Test file naming**: `tests/test_story_15_4_dm_bookend_npc_turns.py`
- **Test organization**: Class-based grouping matching project convention

### References

- [Source: agents.py#DM_SYSTEM_PROMPT ~line 108] - Base DM system prompt (combat section at line 124)
- [Source: agents.py#_build_dm_context ~line 1248] - DM context builder (asymmetric memory access)
- [Source: agents.py#dm_turn ~line 1501] - DM turn function to modify
- [Source: agents.py#dm_turn system_prompt_parts ~line 1553] - Prompt injection point
- [Source: agents.py#dm_turn messages ~line 1560] - Messages list with "Continue the adventure." prompt
- [Source: agents.py#dm_turn current_turn="dm" ~line 1791] - Hardcoded current_turn to make dynamic
- [Source: agents.py#dm_turn return GameState ~line 1788] - Return state construction
- [Source: agents.py#create_dm_agent ~line 689] - DM agent factory (tool bindings)
- [Source: agents.py#_execute_start_combat ~line 2100] - Combat start helper (Story 15-2)
- [Source: agents.py#_execute_end_combat ~line 2160] - Combat end helper (Story 15-2)
- [Source: models.py#CombatState ~line 853] - CombatState with initiative_order, round_number, npc_profiles
- [Source: models.py#NpcProfile ~line 822] - NPC profile with name, hp, ac, personality, tactics, conditions
- [Source: models.py#CharacterSheet ~line 1565] - CharacterSheet with hp_current, hp_max
- [Source: graph.py#route_to_next_agent ~line 113] - Routing function that depends on correct current_turn
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-10.md#Story 15-4] - Design specification
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-10.md#Section 3 Option D1] - Rich NPC Context Injection architecture decision
- [Source: _bmad-output/implementation-artifacts/stories/15-1-combat-state-model.md] - Story 15-1 context (CombatState, NpcProfile)
- [Source: _bmad-output/implementation-artifacts/stories/15-2-initiative-rolling.md] - Story 15-2 context (tool interception, initiative rolling)
- [Source: _bmad-output/implementation-artifacts/stories/15-3-combat-aware-routing.md] - Story 15-3 context (routing dependency)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
