# Story 15.2: Initiative Rolling & Turn Reordering

Status: ready-for-dev

## Epic

Epic 15: Combat Initiative System

## Story

As a **game engine developer**,
I want **initiative rolling logic that rolls 1d20+modifier for each PC and NPC, sorts combatants by initiative, and rebuilds the turn queue**,
So that **when the DM starts tactical combat, the turn order reflects D&D initiative rules instead of fixed alphabetical order**.

## Priority

High (Story 15-3 Combat-Aware Graph Routing depends on the initiative_order being populated)

## Estimate

Medium (tool interception in dm_turn, initiative rolling function, turn queue rewriting, comprehensive tests)

## Dependencies

- Story 15-1 (Combat State Model & Detection): **review** -- provides `CombatState`, `NpcProfile`, `dm_start_combat`, `dm_end_combat` tool schemas, persistence support. All models and schema-only tools are in place.
- Epic 8 (Character Sheets): **done** -- `CharacterSheet.initiative` field stores the DEX-based initiative modifier (models.py line 1604). `CharacterSheet.dexterity_modifier` property (line 1724) computes `(dexterity - 10) // 2`.
- `combat_mode: Literal["Narrative", "Tactical"]` on `GameConfig` (models.py line 284) gates whether initiative rolling activates.

## Acceptance Criteria

1. **Given** `dm_start_combat` is called with a `participants` list and `combat_mode` is `"Tactical"`, **When** the tool call is intercepted in `dm_turn()`, **Then** initiative is rolled for every PC in the party using `1d20 + CharacterSheet.initiative`.

2. **Given** `dm_start_combat` is called with NPC participants, **When** initiative is rolled, **Then** each NPC rolls `1d20 + NpcProfile.initiative_modifier`.

3. **Given** initiative rolls are complete, **When** results are stored, **Then** `combat_state.initiative_rolls` contains a mapping of every combatant name to their total roll (e.g., `{"shadowmere": 18, "dm:goblin_1": 14, "thorin": 12}`).

4. **Given** initiative rolls are complete, **When** the initiative order is built, **Then** combatants are sorted by total roll descending. Ties are broken by modifier descending, then alphabetically ascending.

5. **Given** the sorted initiative order, **When** it is stored in `combat_state.initiative_order`, **Then** a DM bookend entry `"dm"` is prepended at position 0, followed by the sorted combatant list (with NPC entries formatted as `"dm:npc_name"`).

6. **Given** `dm_start_combat` is intercepted, **When** processing completes, **Then** `combat_state.original_turn_queue` stores a copy of the current `turn_queue` before it is replaced.

7. **Given** combat starts successfully, **When** the state is updated, **Then** `combat_state.active = True`, `combat_state.round_number = 1`, and `combat_state.npc_profiles` is populated from the participants list.

8. **Given** `dm_start_combat` is intercepted, **When** the tool result is returned to the LLM, **Then** it includes a formatted initiative order summary (e.g., "Initiative order: Shadowmere (18), Goblin 1 (14), Thorin (12)").

9. **Given** `dm_end_combat` is called, **When** the tool call is intercepted in `dm_turn()`, **Then** `turn_queue` is restored from `combat_state.original_turn_queue` and `combat_state` is reset to defaults.

10. **Given** `combat_mode` is `"Narrative"` (default), **When** `dm_start_combat` is called, **Then** it executes as a no-op placeholder (returns the existing schema-only message) and does NOT modify combat_state or turn_queue.

11. **Given** a PC has no character sheet (edge case), **When** initiative is rolled for that PC, **Then** a default modifier of 0 is used (1d20+0).

12. **Given** `dm_start_combat` and `dm_end_combat` tools, **When** the DM agent model is built via `build_dm_agent()`, **Then** both tools are included in the `bind_tools()` list.

## Tasks / Subtasks

- [ ] Task 1: Add `roll_initiative()` function to `tools.py` (AC: #1, #2, #3, #4, #5)
  - [ ] 1.1: Define `roll_initiative(pc_names: list[str], character_sheets: dict[str, CharacterSheet], npc_profiles: dict[str, NpcProfile]) -> tuple[dict[str, int], list[str]]` (returns initiative_rolls dict and sorted initiative_order list)
  - [ ] 1.2: For each PC, roll `1d20` using `roll_dice("1d20")` and add `CharacterSheet.initiative` modifier (default 0 if no sheet)
  - [ ] 1.3: For each NPC, roll `1d20` using `roll_dice("1d20")` and add `NpcProfile.initiative_modifier`
  - [ ] 1.4: Store results in `initiative_rolls` dict keyed by agent name (PCs) or `"dm:npc_key"` (NPCs)
  - [ ] 1.5: Sort combatants by total roll descending, then modifier descending, then name ascending
  - [ ] 1.6: Prepend `"dm"` bookend at position 0 of the sorted order
  - [ ] 1.7: Add `roll_initiative` to `__all__` exports

- [ ] Task 2: Add `_execute_start_combat()` helper to `agents.py` (AC: #1, #6, #7, #8, #10)
  - [ ] 2.1: Define `_execute_start_combat(tool_args: dict, state: GameState) -> tuple[str, CombatState]` private helper
  - [ ] 2.2: Check `game_config.combat_mode` -- if `"Narrative"`, return placeholder string and unchanged combat_state
  - [ ] 2.3: Parse `participants` list from `tool_args`, build `NpcProfile` objects, key by sanitized name
  - [ ] 2.4: Extract PC names from `turn_queue` (all entries except `"dm"`)
  - [ ] 2.5: Retrieve `character_sheets` from state for initiative modifiers
  - [ ] 2.6: Call `roll_initiative()` to get rolls and order
  - [ ] 2.7: Save current `turn_queue` into `original_turn_queue`
  - [ ] 2.8: Build and return new `CombatState` with `active=True`, `round_number=1`, populated `initiative_rolls`, `initiative_order`, `npc_profiles`, `original_turn_queue`
  - [ ] 2.9: Format tool result string with initiative order summary

- [ ] Task 3: Add `_execute_end_combat()` helper to `agents.py` (AC: #9)
  - [ ] 3.1: Define `_execute_end_combat(state: GameState) -> tuple[str, CombatState, list[str]]` private helper (returns message, reset combat_state, restored turn_queue)
  - [ ] 3.2: Retrieve `original_turn_queue` from `combat_state`
  - [ ] 3.3: Return reset `CombatState()` (defaults) and restored turn_queue
  - [ ] 3.4: If combat was not active, return a no-op message

- [ ] Task 4: Wire tool interception in `dm_turn()` (AC: #1, #8, #9, #12)
  - [ ] 4.1: Import `dm_start_combat`, `dm_end_combat` from tools in agents.py imports block
  - [ ] 4.2: Add `dm_start_combat` and `dm_end_combat` to the `bind_tools()` list in `build_dm_agent()`
  - [ ] 4.3: Add `elif tool_name == "dm_start_combat":` branch in the dm_turn tool_call loop
  - [ ] 4.4: Call `_execute_start_combat()`, store returned `CombatState` for state update
  - [ ] 4.5: Add `elif tool_name == "dm_end_combat":` branch in the dm_turn tool_call loop
  - [ ] 4.6: Call `_execute_end_combat()`, store returned values for state update
  - [ ] 4.7: At the end of `dm_turn()`, include `combat_state` and (if changed) `turn_queue` in the returned GameState update dict

- [ ] Task 5: Write tests in `tests/test_story_15_2_initiative_rolling.py` (AC: #1-#12)
  - [ ] 5.1: `class TestRollInitiative` -- unit tests for `roll_initiative()` function
  - [ ] 5.2: `class TestExecuteStartCombat` -- tests for `_execute_start_combat()` helper
  - [ ] 5.3: `class TestExecuteEndCombat` -- tests for `_execute_end_combat()` helper
  - [ ] 5.4: `class TestDmTurnCombatTools` -- integration tests for tool interception in `dm_turn()`
  - [ ] 5.5: `class TestInitiativeEdgeCases` -- tie-breaking, missing sheets, Narrative mode no-op

## Dev Notes

### Initiative Rolling Logic (`roll_initiative()`)

Place this function in `tools.py` after the `dm_end_combat` tool (after line 728). It is NOT a `@tool`-decorated function -- it is a plain utility function called by `_execute_start_combat()` in agents.py.

```python
def roll_initiative(
    pc_names: list[str],
    character_sheets: dict[str, "CharacterSheet"],
    npc_profiles: dict[str, "NpcProfile"],
) -> tuple[dict[str, int], list[str]]:
    """Roll initiative for all combatants and build sorted turn order.

    Rolls 1d20 + modifier for each PC and NPC. PCs use CharacterSheet.initiative
    (DEX modifier), NPCs use NpcProfile.initiative_modifier. Results are sorted
    highest-first with ties broken by modifier descending, then name ascending.

    Args:
        pc_names: List of PC agent names (e.g., ["shadowmere", "thorin"]).
        character_sheets: Current character sheets keyed by name.
        npc_profiles: NPC profiles keyed by sanitized name.

    Returns:
        Tuple of (initiative_rolls dict, initiative_order list).
        initiative_order has "dm" bookend at index 0, followed by sorted combatants.
        NPC entries use "dm:npc_key" format.
    """
```

Key implementation details:
- Use `roll_dice("1d20")` from the same module to get the d20 roll. Access `result.total` for the raw d20 value (before adding modifier).
- For PCs: modifier = `character_sheets[name].initiative` if sheet exists, else `0`
- For NPCs: modifier = `npc_profiles[key].initiative_modifier`
- Total = d20 roll + modifier. Store in `initiative_rolls` dict.
- NPC keys in `initiative_rolls` use `"dm:npc_key"` format (same as in `initiative_order`)
- Sort by: `(-total, -modifier, name)` using Python's tuple sort
- Prepend `"dm"` as first element of `initiative_order` (DM bookend turn)

### NPC Name Sanitization

NPC names from the DM's `participants` list need to be sanitized to lowercase-underscore format for use as dict keys and in `initiative_order`. Follow the same pattern used for character names throughout the codebase:

```python
def _sanitize_npc_name(name: str) -> str:
    """Convert NPC name to lowercase key format: 'Goblin 1' -> 'goblin_1'."""
    return name.strip().lower().replace(" ", "_")
```

Place this as a module-level helper in `tools.py` (not exported in `__all__`). The sanitized name is used as:
- Key in `npc_profiles` dict: `{"goblin_1": NpcProfile(name="Goblin 1", ...)}`
- Entry in `initiative_order`: `"dm:goblin_1"`
- Key in `initiative_rolls`: `"dm:goblin_1"`

### Tool Interception in `dm_turn()` -- `_execute_start_combat()`

The `_execute_start_combat()` helper function belongs in `agents.py` alongside the existing `_execute_sheet_update()` (line ~1480) and `_execute_whisper()` (line ~1420) helpers. Follow their pattern exactly:

```python
def _execute_start_combat(
    tool_args: dict[str, Any],
    state: GameState,
) -> tuple[str, CombatState | None]:
    """Process dm_start_combat tool call.

    Returns:
        Tuple of (tool_result_string, new_combat_state_or_None).
        Returns None for combat_state when combat_mode is Narrative (no-op).
    """
```

Steps:
1. Check `state["game_config"].combat_mode` -- if `"Narrative"`, return placeholder and `None`
2. Parse `participants` from `tool_args["participants"]`
3. Build `NpcProfile` objects from participant dicts. Map `"hp"` -> `hp_max` and `hp_current`, `"ac"` -> `ac`. Key by sanitized name.
4. Get PC names: `[name for name in state["turn_queue"] if name != "dm"]`
5. Get character sheets: `state.get("character_sheets", {})`
6. Call `roll_initiative(pc_names, character_sheets, npc_profiles)`
7. Build `CombatState(active=True, round_number=1, initiative_order=order, initiative_rolls=rolls, original_turn_queue=list(state["turn_queue"]), npc_profiles=npc_profiles)`
8. Format result string listing initiative order with rolls

**IMPORTANT**: The `_execute_start_combat` returns the new `CombatState` object. The caller in `dm_turn()` must store it and include it in the returned state dict. The `turn_queue` should NOT be modified here -- that is Story 15-3's responsibility (combat-aware routing). For now, the initiative_order is stored in `combat_state.initiative_order` and Story 15-3 will use it to override routing.

Wait -- actually, per the sprint change proposal Section 3 "Dynamic Turn Queue (Recommended)", the turn_queue IS supposed to be replaced with the initiative order. Let me re-examine...

The sprint change proposal says:
> "When combat starts, replace turn_queue with initiative-sorted order"
> "route_to_next_agent() already reads from turn_queue - just reorder it"

However, Story 15-3 is specifically "Combat-Aware Graph Routing" which modifies `route_to_next_agent()`. The cleanest boundary is:

- **Story 15-2 (this story)**: Computes initiative, populates `combat_state` fields (initiative_order, initiative_rolls, npc_profiles, original_turn_queue, active, round_number). Does NOT modify `turn_queue` directly.
- **Story 15-3**: Modifies `route_to_next_agent()` to read from `combat_state.initiative_order` when `combat_state.active` is True, instead of `turn_queue`.

This keeps the stories cleanly separated: 15-2 does data, 15-3 does routing.

### Tool Interception in `dm_turn()` -- `_execute_end_combat()`

```python
def _execute_end_combat(
    state: GameState,
) -> tuple[str, CombatState]:
    """Process dm_end_combat tool call.

    Returns:
        Tuple of (tool_result_string, reset_combat_state).
    """
```

Steps:
1. Get current `combat_state` from state
2. If not active, return "No combat is active." and existing combat_state
3. Return confirmation message and `CombatState()` (reset to defaults)

Note: The `original_turn_queue` restoration to `turn_queue` is also a Story 15-3 concern (routing). This story just resets the `CombatState` back to defaults when combat ends.

### Wiring in `dm_turn()` Tool Call Loop

In the tool call loop (agents.py ~line 1572), add two new branches after the existing `dm_reveal_secret` branch and before the `else` catch-all:

```python
# Execute the start combat tool (Story 15.2)
elif tool_name == "dm_start_combat":
    tool_result, new_combat_state = _execute_start_combat(
        tool_args, state
    )
    if new_combat_state is not None:
        updated_combat_state = new_combat_state
    logger.info("DM started combat: %s", tool_result)

# Execute the end combat tool (Story 15.2)
elif tool_name == "dm_end_combat":
    tool_result, reset_combat_state = _execute_end_combat(state)
    updated_combat_state = reset_combat_state
    logger.info("DM ended combat: %s", tool_result)
```

Initialize `updated_combat_state: CombatState | None = None` at the top of the function alongside `dice_results`, `updated_sheets`, etc.

At the end of `dm_turn()` where the return dict is built, add:
```python
if updated_combat_state is not None:
    result["combat_state"] = updated_combat_state
```

### Binding Tools to DM Agent

In `build_dm_agent()` (agents.py line 696), add the two new tools to the bind_tools list:

```python
return base_model.bind_tools([
    dm_roll_dice,
    dm_update_character_sheet,
    dm_whisper_to_agent,
    dm_reveal_secret,
    dm_start_combat,   # Story 15.2
    dm_end_combat,     # Story 15.2
])
```

Also update the import block at the top of agents.py (line 38-45) to include:
```python
from tools import (
    apply_character_sheet_update,
    dm_end_combat,       # Story 15.2
    dm_reveal_secret,
    dm_roll_dice,
    dm_start_combat,     # Story 15.2
    dm_update_character_sheet,
    dm_whisper_to_agent,
    pc_roll_dice,
    roll_initiative,     # Story 15.2
)
```

### NpcProfile Construction from Participant Dicts

The DM provides participants as a list of dicts. Map fields carefully:

```python
npc_profiles: dict[str, NpcProfile] = {}
for p in participants:
    name = p.get("name", "Unknown")
    key = _sanitize_npc_name(name)
    hp = p.get("hp", 1)
    npc_profiles[key] = NpcProfile(
        name=name,
        initiative_modifier=p.get("initiative_modifier", 0),
        hp_max=hp,
        hp_current=hp,
        ac=p.get("ac", 10),
        personality=p.get("personality", ""),
        tactics=p.get("tactics", ""),
        secret=p.get("secret", ""),
    )
```

Note: `hp` from the DM maps to both `hp_max` and `hp_current` (NPCs start at full HP).

### Tie-Breaking Rules

D&D 5e typically breaks initiative ties with a DEX check or DM ruling. For this implementation, use a deterministic approach:

1. **Primary**: Total roll (descending -- highest goes first)
2. **Secondary**: Modifier (descending -- higher DEX/modifier wins ties)
3. **Tertiary**: Name (ascending -- alphabetical for full determinism)

This is implemented as a sort key: `sorted(combatants, key=lambda c: (-c.total, -c.modifier, c.name))`

### Files to Modify

1. **`tools.py`** -- Add `_sanitize_npc_name()` helper, `roll_initiative()` function, update `__all__`
2. **`agents.py`** -- Import new tools + `roll_initiative`, bind combat tools to DM agent, add `_execute_start_combat()` and `_execute_end_combat()` helpers, wire tool interception in `dm_turn()`, include `combat_state` in return dict
3. **`tests/test_story_15_2_initiative_rolling.py`** -- **NEW** test file

### Files NOT to Modify

- **`models.py`** -- No changes. CombatState and NpcProfile already defined (Story 15-1).
- **`graph.py`** -- No changes. Combat-aware routing is Story 15-3.
- **`persistence.py`** -- No changes. CombatState serialization already handled (Story 15-1).
- **`app.py`** -- No changes. Combat UI is Story 15-5.
- **`config.py`** -- No changes.
- **`memory.py`** -- No changes.

### Test Approach

Create `tests/test_story_15_2_initiative_rolling.py`. Use class-based test organization:

**`class TestRollInitiative`:**
- Test basic roll with 2 PCs and 1 NPC produces correct structure
- Test all combatants get entries in initiative_rolls dict
- Test initiative_order starts with "dm" bookend
- Test NPC entries use "dm:npc_key" format
- Test sort order is descending by total roll (mock `roll_dice` to control results)
- Test tie-breaking by modifier (same total, different modifiers)
- Test tie-breaking by name (same total, same modifier, different names)
- Test PC with no character sheet uses modifier 0
- Test empty NPC list (PCs only)
- Test empty PC list (edge case, though unlikely)

**`class TestSanitizeNpcName`:**
- Test basic sanitization: "Goblin 1" -> "goblin_1"
- Test already lowercase: "wolf" -> "wolf"
- Test multi-word: "Bug Bear Chief" -> "bug_bear_chief"
- Test whitespace trimming

**`class TestExecuteStartCombat`:**
- Test Tactical mode: returns CombatState with active=True, round_number=1
- Test Narrative mode: returns None for combat_state (no-op)
- Test participants correctly parsed into NpcProfile objects
- Test initiative_rolls populated in returned combat_state
- Test initiative_order populated in returned combat_state
- Test original_turn_queue saved
- Test tool result string contains initiative order summary
- Test hp maps to both hp_max and hp_current in NpcProfile

**`class TestExecuteEndCombat`:**
- Test combat active: returns reset CombatState (active=False)
- Test combat not active: returns no-op message
- Test returned combat_state has empty collections (default)

**`class TestDmTurnCombatToolBinding`:**
- Test dm_start_combat is in the DM agent's bound tools
- Test dm_end_combat is in the DM agent's bound tools

**`class TestInitiativeEdgeCases`:**
- Test single PC vs single NPC
- Test large party (6+ combatants)
- Test NPC with negative initiative modifier
- Test all combatants roll same total (alphabetical tie-break)

Mock `roll_dice` in most tests to produce deterministic results. Use `unittest.mock.patch("tools.roll_dice")` for `roll_initiative` tests.

For `_execute_start_combat` tests, build a minimal `GameState` dict with `game_config`, `turn_queue`, and `character_sheets`. Mock `roll_initiative` to avoid randomness.

### Existing Patterns to Follow

- **Helper function naming**: `_execute_sheet_update()`, `_execute_whisper()`, `_execute_reveal()` -- follow with `_execute_start_combat()`, `_execute_end_combat()`
- **Tool interception pattern**: `elif tool_name == "dm_start_combat":` in the existing for loop
- **Logger usage**: `logger.info("DM started combat: %s", tool_result)` -- same pattern as other tools
- **Test file naming**: `tests/test_story_15_2_initiative_rolling.py`
- **Test organization**: Class-based grouping matching project convention

### Import Notes

In `tools.py`, add the `CharacterSheet` and `NpcProfile` type imports for the `roll_initiative` function signature. Use `TYPE_CHECKING` to avoid circular imports:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import CharacterSheet, NpcProfile
```

Check if `tools.py` already uses `from __future__ import annotations` -- if not, add it. If it does, just add the TYPE_CHECKING block.

### Project Structure Notes

- All source in flat layout (no `src/` directory)
- Tests in `tests/` with `test_story_{epic}_{story}_{name}.py` naming
- Uses `python -m pytest` and `python -m ruff` (uv not on PATH in MINGW64)
- Ruff E402 errors in app.py are pre-existing -- ignore
- pyright strict mode enabled

### References

- [Source: models.py#CombatState ~line 853] - CombatState model with initiative_order, initiative_rolls, npc_profiles fields
- [Source: models.py#NpcProfile ~line 822] - NPC profile with initiative_modifier field
- [Source: models.py#CharacterSheet ~line 1565] - CharacterSheet with initiative field (line 1604)
- [Source: models.py#CharacterSheet.dexterity_modifier ~line 1724] - DEX modifier property
- [Source: models.py#GameConfig.combat_mode ~line 284] - Literal["Narrative", "Tactical"] gate
- [Source: tools.py#roll_dice ~line 99] - Dice rolling function to reuse for initiative rolls
- [Source: tools.py#DiceResult ~line 57] - Result model with .total attribute
- [Source: tools.py#dm_start_combat ~line 686] - Schema-only tool to intercept
- [Source: tools.py#dm_end_combat ~line 717] - Schema-only tool to intercept
- [Source: agents.py#build_dm_agent ~line 696] - Tool binding list to extend
- [Source: agents.py#dm_turn ~line 1484] - DM turn function with tool call loop
- [Source: agents.py#_execute_sheet_update] - Pattern for private tool execution helper
- [Source: agents.py#_execute_whisper] - Pattern for private tool execution helper
- [Source: agents.py#imports ~line 38] - Import block to extend
- [Source: graph.py#route_to_next_agent ~line 113] - Current routing (NOT modified in this story)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-10.md#Story 15-2] - Design specification
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-10.md#Section 3] - Architecture decisions (Dynamic Turn Queue)
- [Source: _bmad-output/implementation-artifacts/stories/15-1-combat-state-model.md] - Previous story context

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
