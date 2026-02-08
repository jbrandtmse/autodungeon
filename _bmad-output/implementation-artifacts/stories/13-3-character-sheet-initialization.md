# Story 13.3: Character Sheet Initialization

Status: ready-for-dev

## Story

As a **developer**,
I want **character sheets populated in GameState when a session starts**,
So that **agents have mechanical data from turn one and all Epic 8 systems (context injection, DM tools, viewer, notifications, persistence) activate automatically**.

## Epic

Epic 13: Adventure Setup & Party Management

## Priority

High (final story in epic; completes the adventure setup flow)

## Estimate

Medium (helper functions + wiring + optional wizard enhancement + tests)

## Dependencies

- Story 13.1 (Session Naming): **done**
- Story 13.2 (Party Composition UI): **done** -- added `characters_override` parameter to `populate_game_state()`, library-to-CharacterConfig conversion in `_build_selected_characters()`
- Epic 8 (Character Sheets): **done** -- all downstream systems (context injection, DM tools, viewer, notifications, persistence) are built and activate automatically once `character_sheets` is populated in GameState

## Acceptance Criteria

1. **Given** `populate_game_state()` is called with selected characters, **When** the game initializes, **Then** `character_sheets` dict in GameState contains a `CharacterSheet` for every selected character (not empty `{}`).

2. **Given** a preset character (from `config/characters/`), **When** initializing their sheet, **Then** a level-appropriate `CharacterSheet` is auto-generated based on their class using D&D 5e defaults (reasonable ability scores, class-appropriate weapons, armor, proficiencies, spells for casters, and starting equipment).

3. **Given** a library character created via the wizard, **When** initializing their sheet, **Then** their saved `CharacterSheet` data is loaded from the library YAML file (preserving the user's exact ability scores, skills, and equipment choices).

4. **Given** a library character whose YAML has ability scores, skills, and equipment but NOT full CharacterSheet data, **When** initializing their sheet, **Then** a `CharacterSheet` is generated from the available data (abilities, skills, equipment used; class defaults fill any gaps).

5. **Given** character sheets are populated at game start, **When** the DM agent builds context, **Then** `format_all_sheets_context()` returns all party character sheets (DM context injection from Story 8.3 activates automatically).

6. **Given** character sheets are populated at game start, **When** a PC agent builds context, **Then** `format_character_sheet_context()` returns their own character sheet (PC context injection from Story 8.3 activates automatically).

7. **Given** the character sheet viewer in the sidebar, **When** a user clicks a character name during an active game, **Then** the viewer shows real sheet data from `GameState["character_sheets"]` instead of sample fallbacks.

8. **Given** the DM agent during gameplay, **When** it calls `dm_update_character_sheet()`, **Then** the existing Epic 8 tool call system modifies the populated sheets (works automatically because sheets exist).

9. **Given** character sheets are populated with current HP equal to max HP, **When** the game starts, **Then** all characters begin at full health (not the "damaged" values used in the sample sheets).

## Tasks / Subtasks

- [ ] Task 1: Create `generate_character_sheet_from_config()` helper in `models.py` (AC: #2, #9)
  - [ ] 1.1: Define function signature: `generate_character_sheet_from_config(config: CharacterConfig) -> CharacterSheet`
  - [ ] 1.2: Build a `CLASS_DEFAULTS` dictionary mapping class names (Fighter, Rogue, Wizard, Cleric, Warlock, etc.) to D&D 5e defaults: ability scores, HD, saving throw proficiencies, skill proficiencies, weapon/armor proficiencies, class features, starting weapons/armor, spellcasting data
  - [ ] 1.3: Use the existing `create_sample_character_sheet()` in `app.py:4102-4361` as reference for class-specific data structures (Weapon, Armor, Spell, SpellSlots instances), but generate proper starting values (full HP, level 1, no damage)
  - [ ] 1.4: Calculate derived stats: `hit_points_max` = HD max + CON modifier, `armor_class` from armor + DEX, `initiative` = DEX modifier, `hit_dice` = `"1d{HD}"`, `hit_dice_remaining` = level
  - [ ] 1.5: Set `hit_points_current = hit_points_max` (characters start at full health)
  - [ ] 1.6: Use `config.name` for sheet name, `config.character_class` for class
  - [ ] 1.7: Default race to "Human", background to "Adventurer", alignment to "Neutral Good" (preset configs don't include these)
  - [ ] 1.8: Populate personality_traits from `config.personality`, leave ideals/bonds/flaws/backstory as sensible defaults
  - [ ] 1.9: Add a generic fallback for unknown classes (use Fighter defaults as base)
  - [ ] 1.10: Support Warlock class (library character Eden is a Warlock) with charisma-based spellcasting

- [ ] Task 2: Create `load_character_sheet_from_library()` helper in `models.py` (AC: #3, #4)
  - [ ] 2.1: Define function signature: `load_character_sheet_from_library(lib_data: dict[str, Any], config: CharacterConfig) -> CharacterSheet`
  - [ ] 2.2: Check if `lib_data` contains a `"character_sheet"` key with full serialized CharacterSheet data (CP-5 format); if so, deserialize with `CharacterSheet.model_validate()` and return
  - [ ] 2.3: If no full sheet data, build a CharacterSheet from partial library data: extract `abilities` dict (strength, dexterity, etc.), `skills` list, `equipment` list, `race`, `background` from `lib_data`
  - [ ] 2.4: Use `generate_character_sheet_from_config()` as the base, then overlay library-specific data (abilities, skills, equipment)
  - [ ] 2.5: Convert library `equipment` list (strings like "light crossbow with 20 bolts") to `EquipmentItem` instances
  - [ ] 2.6: Convert library `skills` list to `skill_proficiencies`
  - [ ] 2.7: Use library `race` and `background` if present (instead of defaults)
  - [ ] 2.8: Handle missing/malformed library data gracefully (fall back to `generate_character_sheet_from_config()`)

- [ ] Task 3: Modify `populate_game_state()` to initialize character sheets (AC: #1, #5, #6)
  - [ ] 3.1: After building the `characters` dict (line ~2039), iterate over all characters
  - [ ] 3.2: For each character, check if it came from a library source (need to thread library data through)
  - [ ] 3.3: Add optional `library_data` parameter to `populate_game_state()`: `library_data: dict[str, dict[str, Any]] | None = None` -- keyed by lowercase character name, containing raw library YAML data
  - [ ] 3.4: For each character: if `library_data` has an entry, call `load_character_sheet_from_library()`; otherwise call `generate_character_sheet_from_config()`
  - [ ] 3.5: Store result in `character_sheets` dict keyed by character NAME (e.g., "Thorin", not "fighter") -- this matches the key convention used by `format_character_sheet_context()` in agents.py and `get_character_sheet()` in app.py
  - [ ] 3.6: Replace `character_sheets={}` with `character_sheets=initialized_sheets` in the returned GameState

- [ ] Task 4: Wire library data through `handle_new_session_click()` and `_build_selected_characters()` (AC: #1, #3)
  - [ ] 4.1: Modify `_build_selected_characters()` to also return library raw data for selected library characters: change return type to `tuple[dict[str, CharacterConfig], dict[str, dict[str, Any]]]`
  - [ ] 4.2: The second dict maps lowercase character name to raw library YAML data (needed for sheet initialization)
  - [ ] 4.3: In `handle_new_session_click()`, pass the library data through to `populate_game_state(library_data=...)`
  - [ ] 4.4: Update callers to handle the new return tuple

- [ ] Task 5: Update `get_character_sheet()` to check GameState first (AC: #7)
  - [ ] 5.1: In `get_character_sheet()` at `app.py:4740`, add a check for `game["character_sheets"]` BEFORE falling back to sample sheet creation
  - [ ] 5.2: After the existing `st.session_state.get("character_sheets", {})` check, add: `game_sheets = game.get("character_sheets", {})` and check for character name there (try exact, lowercase, and name-search)
  - [ ] 5.3: If found in game state, return that sheet directly (no sample creation)
  - [ ] 5.4: Keep the sample sheet fallback as a last resort for backward compatibility

- [ ] Task 6: (Optional, CP-5) Save CharacterSheet data in wizard library save (AC: #3)
  - [ ] 6.1: In the wizard save function, after saving CharacterConfig YAML, also generate and save a `CharacterSheet` from the wizard data
  - [ ] 6.2: Add a `character_sheet` key to the library YAML with the full serialized sheet data (using `model_dump()`)
  - [ ] 6.3: This enables Task 2.2 to load exact user choices on future game starts
  - [ ] 6.4: If this is deferred, Task 2.3-2.7 handles the partial-data path

- [ ] Task 7: Write tests (AC: #1-9)
  - [ ] 7.1: Test `generate_character_sheet_from_config()` for Fighter -- verify ability scores, weapons, armor, proficiencies, full HP
  - [ ] 7.2: Test `generate_character_sheet_from_config()` for Rogue -- verify DEX-based stats, finesse weapons, expertise
  - [ ] 7.3: Test `generate_character_sheet_from_config()` for Wizard -- verify spellcasting fields populated, no armor
  - [ ] 7.4: Test `generate_character_sheet_from_config()` for Cleric -- verify WIS-based spellcasting, heavy armor
  - [ ] 7.5: Test `generate_character_sheet_from_config()` for Warlock -- verify CHA-based spellcasting
  - [ ] 7.6: Test `generate_character_sheet_from_config()` for unknown class -- verify fallback to Fighter defaults
  - [ ] 7.7: Test `generate_character_sheet_from_config()` produces valid CharacterSheet (all validators pass)
  - [ ] 7.8: Test `generate_character_sheet_from_config()` sets `hit_points_current == hit_points_max` (full health at start)
  - [ ] 7.9: Test `load_character_sheet_from_library()` with full CharacterSheet data (CP-5 path)
  - [ ] 7.10: Test `load_character_sheet_from_library()` with partial data (abilities, skills, equipment only)
  - [ ] 7.11: Test `load_character_sheet_from_library()` with missing/malformed data falls back gracefully
  - [ ] 7.12: Test `load_character_sheet_from_library()` preserves user's exact ability scores from library YAML
  - [ ] 7.13: Test `load_character_sheet_from_library()` converts equipment strings to EquipmentItem list
  - [ ] 7.14: Test `populate_game_state()` returns non-empty `character_sheets` dict
  - [ ] 7.15: Test `populate_game_state()` with preset characters generates sheets for each
  - [ ] 7.16: Test `populate_game_state()` with library data uses `load_character_sheet_from_library()`
  - [ ] 7.17: Test `populate_game_state()` character_sheets keyed by character NAME (not agent key)
  - [ ] 7.18: Test `get_character_sheet()` returns sheet from `game["character_sheets"]` when available
  - [ ] 7.19: Test `get_character_sheet()` falls back to sample when no game sheets exist (backward compat)
  - [ ] 7.20: Test end-to-end: `_build_selected_characters()` + `populate_game_state()` -> character_sheets populated
  - [ ] 7.21: Test context injection activates: `format_all_sheets_context()` returns content when sheets populated
  - [ ] 7.22: Test context injection activates: `format_character_sheet_context()` returns content for PC

## Dev Notes

### Key Insight: Downstream Systems Activate Automatically

Once `character_sheets` in GameState is populated (not `{}`), ALL of the following Epic 8 systems work without any modifications:

| System | Location | How It Activates |
|--------|----------|-----------------|
| DM context injection | `agents.py:1257-1261` | `format_all_sheets_context(character_sheets)` -- already checks `if character_sheets:` |
| PC context injection | `agents.py:1373-1379` | `format_character_sheet_context(sheet)` -- already looks up sheet by character name |
| DM tool: update sheet | `agents.py:1495-1498` + `tools.py:359` | `apply_character_sheet_update()` -- works on any valid CharacterSheet |
| Sheet change notifications | `agents.py:1460-1463` | `dict(state.get("character_sheets", {}))` -- already iterates sheets |
| Character sheet persistence | `persistence.py` | `serialize_game_state()` / `deserialize_game_state()` -- already handle CharacterSheet |
| Character sheet viewer | `app.py:4740-4783` | `get_character_sheet()` -- needs minor fix (Task 5) to check GameState first |

**This story's core job is ONLY to populate the sheets at game start.** The only downstream fix needed is `get_character_sheet()` (Task 5).

### Existing `create_sample_character_sheet()` as Reference

`app.py:4102-4361` contains `create_sample_character_sheet()` which already has:
- Class-specific ability score arrays for Fighter, Rogue, Wizard, Cleric
- Class-specific combat configs (weapons, armor, hit dice, saving throws, skills, features)
- Spellcasting data for Wizard and Cleric (cantrips, spells, spell slots)
- Common equipment list

**Important differences for Story 13.3:**
- `create_sample_character_sheet()` sets `hit_points_current` BELOW max (simulating damage) -- the new helper should set `hit_points_current = hit_points_max` (fresh start)
- `create_sample_character_sheet()` hardcodes level 5 -- the new helper should default to level 1 (or configurable)
- `create_sample_character_sheet()` lives in `app.py` (UI layer) -- the new helper belongs in `models.py` (data layer) since `populate_game_state()` is there

### Library Character Data Format

From `config/characters/library/eden.yaml`:
```yaml
name: Eden
race: Elf
class: Warlock
background: Sage
personality: A mysterious adventurer.
color: '#4B0082'
provider: claude
model: claude-3-haiku-20240307
token_limit: 4000
abilities:
  strength: 8
  intelligence: 15
  dexterity: 16
  charisma: 10
  wisdom: 13
  constitution: 12
skills:
- History
- Arcana
- Deception
equipment:
- light crossbow with 20 bolts
- component pouch
- scholar's pack
```

Key observations:
- Has `abilities` dict with exact scores from wizard
- Has `skills` list (skill proficiencies)
- Has `equipment` as string list (not structured Weapon/Armor/EquipmentItem)
- Has `race` and `background` (preset configs do NOT have these)
- Uses `class` key (not `character_class`) -- already handled by `_build_selected_characters()`
- Does NOT have full CharacterSheet data yet (CP-5 would add this)

### CharacterSheet Key Convention

Character sheets in GameState are keyed by **character name** (e.g., `"Thorin"`, `"Shadowmere"`, `"Eden"`), NOT by agent key (e.g., `"fighter"`, `"rogue"`). This is confirmed by:
- `agents.py:1376-1377`: `sheet = character_sheets.get(character_config.name)`
- `agents.py:1022`: `for _name, sheet in sorted(sheets.items())`
- `get_character_sheet()` in `app.py:4753`: looks up by character name

### Preset Character Configs (What's Available)

Preset characters have ONLY these CharacterConfig fields:
- `name`, `character_class`, `personality`, `color`, `provider`, `model`, `token_limit`
- NO ability scores, NO race, NO background, NO equipment

All sheet data must be generated from class defaults for preset characters.

### Files to Modify

1. **`models.py`** (primary -- new helpers + populate_game_state modification)
   - Add `generate_character_sheet_from_config()` function
   - Add `load_character_sheet_from_library()` function
   - Modify `populate_game_state()` signature and body
   - Add `library_data` parameter

2. **`app.py`** (wiring + viewer fix)
   - Modify `_build_selected_characters()` to return library data alongside CharacterConfig
   - Modify `handle_new_session_click()` to pass library data through
   - Fix `get_character_sheet()` to check GameState character_sheets

3. **`tests/test_story_13_3_character_sheet_initialization.py`** (new test file)

### Files NOT to Modify

- **`agents.py`**: Context injection already works when sheets are populated
- **`tools.py`**: `apply_character_sheet_update()` and `dm_update_character_sheet()` already work
- **`persistence.py`**: Serialization/deserialization already handles CharacterSheet
- **`config.py`**: No changes needed to character config loading
- **`styles/theme.css`**: No UI styling changes

### D&D 5e Class Defaults Reference

For `generate_character_sheet_from_config()`, use these level 1 defaults:

| Class | HD | Primary | Save Profs | Key Skills | Armor | Weapon | Spellcasting |
|-------|-----|---------|-----------|------------|-------|--------|-------------|
| Fighter | d10 | STR/DEX | STR, CON | Athletics, Perception | All + shields | Simple + Martial | None |
| Rogue | d8 | DEX | DEX, INT | Stealth, Acrobatics, Perception, Sleight of Hand | Light | Simple + rapier/shortsword | None |
| Wizard | d6 | INT | INT, WIS | Arcana, Investigation | None | Dagger, dart, sling, quarterstaff | INT |
| Cleric | d8 | WIS | WIS, CHA | Medicine, Religion | Light + Medium + shields | Simple | WIS |
| Warlock | d8 | CHA | WIS, CHA | Arcana, Deception | Light | Simple | CHA |

### Handling `_build_selected_characters()` Return Change

Current signature:
```python
def _build_selected_characters(
    party_selection: dict[str, bool],
    preset_characters: dict[str, CharacterConfig],
    library_characters: list[dict[str, Any]],
) -> dict[str, CharacterConfig]:
```

New signature:
```python
def _build_selected_characters(
    party_selection: dict[str, bool],
    preset_characters: dict[str, CharacterConfig],
    library_characters: list[dict[str, Any]],
) -> tuple[dict[str, CharacterConfig], dict[str, dict[str, Any]]]:
```

The second element maps lowercase character name to raw library YAML data. This data is needed by `load_character_sheet_from_library()` to access abilities, skills, equipment that are NOT in CharacterConfig.

Update the caller in `render_party_setup_view()`:
```python
# Before:
selected_characters = _build_selected_characters(...)
handle_new_session_click(selected_characters=selected_characters)

# After:
selected_characters, library_data = _build_selected_characters(...)
handle_new_session_click(selected_characters=selected_characters, library_data=library_data)
```

### `handle_new_session_click()` Signature Change

Current:
```python
def handle_new_session_click(
    selected_characters: dict[str, CharacterConfig] | None = None,
) -> None:
```

New:
```python
def handle_new_session_click(
    selected_characters: dict[str, CharacterConfig] | None = None,
    library_data: dict[str, dict[str, Any]] | None = None,
) -> None:
```

Pass `library_data` through to `populate_game_state()`.

### `populate_game_state()` Signature Change

Current:
```python
def populate_game_state(
    include_sample_messages: bool = True,
    selected_module: ModuleInfo | None = None,
    characters_override: dict[str, CharacterConfig] | None = None,
) -> GameState:
```

New:
```python
def populate_game_state(
    include_sample_messages: bool = True,
    selected_module: ModuleInfo | None = None,
    characters_override: dict[str, CharacterConfig] | None = None,
    library_data: dict[str, dict[str, Any]] | None = None,
) -> GameState:
```

### Edge Cases

- **Unknown class**: If `character_class` is not in the defaults table (e.g., "Paladin", "Ranger"), use Fighter defaults as fallback. The DM will adapt the narrative regardless.
- **Library character with no abilities**: Fall back to `generate_character_sheet_from_config()` entirely.
- **Library character with partial abilities**: Use provided scores, fill missing with 10.
- **Equipment string parsing**: Library equipment is stored as simple strings ("light crossbow with 20 bolts"). Convert to `EquipmentItem(name=string)` rather than trying to parse into `Weapon` objects. The DM tools can modify equipment during gameplay.
- **Name collision**: Two characters could theoretically have the same name. The `character_sheets` dict uses name as key, so the later one would overwrite. This is an unlikely edge case given the party setup UI.

## Test Guidance

### Test File

Create `tests/test_story_13_3_character_sheet_initialization.py` following the project naming convention.

### Test Patterns

Reference test patterns from:
- `tests/test_story_8_1_character_sheet.py` -- CharacterSheet construction and validation
- `tests/test_story_13_2_party_composition_ui.py` -- `_build_selected_characters()`, `populate_game_state()` mocking
- `tests/test_story_13_1_session_naming.py` -- mocking Streamlit session state

### Key Test Categories

**Unit tests for `generate_character_sheet_from_config()`:**
- Verify each supported class produces a valid CharacterSheet (passes all Pydantic validators)
- Verify `hit_points_current == hit_points_max` (full health)
- Verify `hit_dice_remaining == level`
- Verify class-appropriate weapons, armor, proficiencies
- Verify spellcasting fields set for caster classes, None for martial classes
- Verify unknown class falls back gracefully
- Verify `config.name` used as sheet name
- Verify `config.personality` used in personality_traits

**Unit tests for `load_character_sheet_from_library()`:**
- Full CharacterSheet data in library (CP-5 path) -- direct deserialization
- Partial data (abilities + skills + equipment) -- merged with class defaults
- Abilities from library override default ability scores
- Skills from library become skill_proficiencies
- Equipment strings become EquipmentItem list
- Race and background from library used when present
- Missing/empty library data falls back to generate_from_config
- Malformed ability data handled gracefully

**Integration tests for `populate_game_state()`:**
- Returns non-empty `character_sheets` dict
- Each character in `characters` has a corresponding sheet in `character_sheets`
- Sheets keyed by character NAME
- With `library_data` parameter, library characters get library-based sheets
- Without `library_data`, all characters get config-based sheets

**Viewer integration test:**
- `get_character_sheet()` returns sheet from `game["character_sheets"]` when populated
- `get_character_sheet()` still falls back to sample when game sheets empty

**Context injection integration tests:**
- `format_all_sheets_context()` returns non-empty string when sheets populated
- `format_character_sheet_context()` returns content for each PC

### Mocking Strategy

- `generate_character_sheet_from_config()` and `load_character_sheet_from_library()` are pure functions -- test directly without mocking
- For `populate_game_state()`, mock `load_character_configs()` and `load_dm_config()` (existing pattern from test_models.py)
- For `get_character_sheet()`, mock `st.session_state` with a game dict containing `character_sheets`
- For `_build_selected_characters()`, provide test fixture data directly

## References

- [Source: models.py#CharacterSheet ~line 1475] - CharacterSheet model definition
- [Source: models.py#CharacterConfig ~line 165] - CharacterConfig model
- [Source: models.py#populate_game_state ~line 2007] - Game state factory to modify
- [Source: models.py#Weapon ~line 1326] - Weapon model
- [Source: models.py#Armor ~line 1352] - Armor model
- [Source: models.py#EquipmentItem ~line 1382] - EquipmentItem model
- [Source: models.py#Spell ~line 1400] - Spell model
- [Source: models.py#SpellSlots ~line 1428] - SpellSlots model
- [Source: app.py#create_sample_character_sheet ~line 4102] - Reference implementation for class-specific sheets
- [Source: app.py#get_character_sheet ~line 4740] - Viewer sheet lookup to fix
- [Source: app.py#_build_selected_characters ~line 8521] - Party selection builder to modify
- [Source: app.py#handle_new_session_click ~line 8570] - Session creation to modify
- [Source: agents.py#format_character_sheet_context ~line 823] - PC context injection (no changes needed)
- [Source: agents.py#format_all_sheets_context ~line 1002] - DM context injection (no changes needed)
- [Source: agents.py#build_dm_context ~line 1257] - DM context builder checks character_sheets
- [Source: agents.py#build_pc_context ~line 1373] - PC context builder checks character_sheets
- [Source: tools.py#apply_character_sheet_update ~line 359] - Sheet update tool (no changes needed)
- [Source: config/characters/library/eden.yaml] - Library character data format reference
- [Source: config/characters/fighter.yaml] - Preset character format (name, class, personality only)
- [Source: _bmad-output/planning-artifacts/epics-v1.1.md#Story 13.3] - Epic requirements
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-08.md#CP-4] - Change proposal: game state initialization
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-08.md#CP-5] - Change proposal: library sheet storage
