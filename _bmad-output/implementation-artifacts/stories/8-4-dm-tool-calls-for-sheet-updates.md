# Story 8-4: DM Tool Calls for Sheet Updates

## Story

As a **DM agent**,
I want **tool calls to update character sheets**,
So that **game mechanics are reflected in character data**.

## Status

**Status:** done
**Epic:** 8 - Character Sheets
**Created:** 2026-02-04

## Acceptance Criteria

**Given** the tools.py module
**When** I examine DM tools
**Then** there's an `update_character_sheet()` function

**Given** the update_character_sheet tool
**When** called
**Then** it accepts:
```python
def update_character_sheet(
    character_name: str,
    updates: dict[str, Any]
) -> str:
    """
    Update a character's sheet.

    Examples:
    - {"hit_points_current": 35}  # Take damage
    - {"gold": 100, "equipment": ["+Potion of Healing"]}  # Loot
    - {"conditions": ["+poisoned"]}  # Add condition
    - {"spell_slots": {"1": {"current": 2}}}  # Use spell slot
    """
```

**Given** the DM narrates damage
**When** processing the turn
**Then** the DM calls `update_character_sheet("Thorin", {"hit_points_current": 35})`

**Given** equipment changes (loot, loss, purchase)
**When** the DM narrates them
**Then** the tool updates the equipment list

**Given** spell slot usage
**When** a caster uses a spell
**Then** the DM updates remaining slots

**Given** an invalid update
**When** the tool is called
**Then** it returns an error message and the sheet remains unchanged

## FRs Covered

- FR63: DM can update character sheets via tool calls
- FR64: Equipment changes reflected in character data
- FR65: Spell slot tracking via tool calls

## Technical Notes

- Tool function goes in tools.py alongside existing dice rolling tools
- Must be bound to DM agent in agents.py (like dm_roll_dice)
- Updates must validate against CharacterSheet model constraints
- Uses "+" prefix for adding items/conditions, "-" prefix for removing
- Tool returns confirmation string (like dice roll results)
- Character sheets stored in GameState["character_sheets"] dict
- Tool needs access to game state to find and update sheets
- Must handle: HP changes, equipment add/remove, condition add/remove, spell slot updates, gold/currency changes

## Tasks

1. [x] Add `update_character_sheet()` tool function to tools.py
2. [x] Implement HP update logic (with validation against max HP)
3. [x] Implement equipment add/remove with +/- prefix
4. [x] Implement condition add/remove with +/- prefix
5. [x] Implement spell slot update logic
6. [x] Implement currency (gold/silver/copper) updates
7. [x] Bind tool to DM agent in agents.py
8. [x] Integrate tool call handling in dm_turn() loop
9. [x] Add tests for update tool
10. [x] Add tests for DM agent integration

## Dev Agent Record

### Implementation Summary
- Added `apply_character_sheet_update()` core logic with full validation in tools.py
- Added `_apply_list_updates()` and `_apply_equipment_updates()` helpers with duplicate protection
- Added `dm_update_character_sheet` @tool with dict schema for LangChain binding
- Added `_execute_sheet_update()` integration function in agents.py
- Modified `dm_turn()` to handle sheet update tool calls alongside dice rolls
- Increased max_tool_iterations from 3 to 5

### Files Touched
- tools.py (add sheet update functions)
- agents.py (DM agent binding + dm_turn integration)
- tests/test_story_8_4_dm_tool_calls.py (157 tests)
- tests/test_agents.py (export test update)

### Code Review Fixes
- H1: Changed tool updates param from str to dict[str, Any]
- H2: Added bool rejection in integer validation
- M1: Added duplicate protection for conditions/equipment
- M2: Validated character_name is actually a string
- M3: Added dm_turn end-to-end integration test

### Tests: 157 passing
