# Story 8-3: Character Sheet Context Injection

## Story

As an **agent (DM or PC)**,
I want **character sheet data in my context**,
So that **I can make decisions based on actual character capabilities**.

## Status

**Status:** done
**Epic:** 8 - Character Sheets
**Created:** 2026-02-01

## Acceptance Criteria

**Given** a PC agent
**When** building their prompt context
**Then** their own character sheet is included in a readable format

**Given** the DM agent
**When** building their prompt context
**Then** ALL party character sheets are included (DM sees all)

**Given** the character sheet context
**When** formatted for prompts
**Then** it's concise but complete:
```
## Your Character Sheet: Thorin, Dwarf Fighter (Level 5)
HP: 45/52 | AC: 18 | Speed: 25ft

STR: 18 (+4) | DEX: 12 (+1) | CON: 16 (+3)
INT: 10 (+0) | WIS: 14 (+2) | CHA: 8 (-1)

Proficiencies: All armor, shields, simple/martial weapons
Skills: Athletics (+7), Intimidation (+2), Perception (+5)

Equipment: Longsword (+7, 1d8+4), Shield, Chain Mail
Inventory: 50ft rope, torches (5), rations (3 days), 47 gold

Features: Second Wind, Action Surge, Extra Attack
Conditions: None
```

**Given** a PC agent with spellcasting
**When** their context includes spells
**Then** available spell slots and prepared spells are listed

## FRs Covered

- FR62: Character sheet data is included in agent context (DM sees all, PC sees own)

## Technical Notes

- Reuses the CharacterSheet Pydantic model from Story 8-1
- Context formatting function should be in agents.py alongside other context formatters
- PC agents receive only their own sheet via `format_character_sheet_context(sheet)`
- DM receives all sheets via `format_all_sheets_context(sheets: dict[str, CharacterSheet])`
- Sheets accessed from GameState (added in Story 8-1 as `character_sheets: dict[str, CharacterSheet]`)
- Must integrate with existing memory system in agents.py

## Tasks

1. [x] Add `format_character_sheet_context(sheet: CharacterSheet) -> str` function to agents.py
2. [x] Add `format_all_sheets_context(sheets: dict[str, CharacterSheet]) -> str` function to agents.py
3. [x] Integrate sheet context into `pc_turn()` function (own sheet only)
4. [x] Integrate sheet context into `dm_turn()` function (all sheets)
5. [x] Add spellcasting section with spell slots and prepared spells
6. [x] Add tests for context formatting functions
7. [x] Add tests for agent integration

## Dev Agent Record

### File List

| File | Changes |
|------|---------|
| agents.py | Added `_SKILL_ABILITY_MAP`, `_format_modifier()`, `format_character_sheet_context()`, `format_all_sheets_context()`; integrated sheets into `_build_dm_context()` and `_build_pc_context()`; updated `dm_turn()` and `pc_turn()` return states |
| persistence.py | Updated serialization/deserialization for `character_sheets` field; added `AttributeError` to exception handling |
| models.py | Added `character_sheets` field to `GameState` TypedDict |
| tests/test_story_8_3_context_injection.py | 42 tests covering formatting, spellcasting, DM/PC context integration, edge cases |
| tests/test_agents.py | Added new exports to expected exports set |
| tests/test_persistence.py | Updated fixture and assertions for `character_sheets` field |

### Change Log

- Implemented `format_character_sheet_context()` with HP, AC, abilities, proficiencies, skills (with calculated modifiers), equipment, weapons (with attack bonuses), inventory (with currency), features, and spellcasting sections
- Implemented `format_all_sheets_context()` for DM context (all sheets, sorted alphabetically)
- Integrated into `_build_dm_context()` - DM sees all party sheets (FR62)
- Integrated into `_build_pc_context()` - PC sees only own sheet, looked up by character name (FR62)
- Updated `dm_turn()` and `pc_turn()` to preserve `character_sheets` in returned state
- Added backward-compatible serialization in persistence.py
- Code review fixes: skill modifiers calculated per AC3, "Conditions: None" always shown, currency merged into Inventory line, removed private function imports from tests
