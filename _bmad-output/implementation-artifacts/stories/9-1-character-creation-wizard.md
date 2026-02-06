# Story 9-1: Character Creation Wizard

## Story

As a **user**,
I want **a step-by-step wizard to create new characters**,
So that **I can build valid D&D characters without knowing all the rules**.

## Status

**Status:** done
**Epic:** 9 - Character Creation UI
**Created:** 2026-02-05
**Updated:** 2026-02-05

## Acceptance Criteria

**Given** I access character creation (from party setup or library)
**When** the wizard starts
**Then** I see a multi-step form with progress indicator

**Given** the wizard steps
**When** progressing through
**Then** the steps are:
1. Basics: Name, Race, Class
2. Abilities: Point buy or standard array
3. Background: Select background, get proficiencies
4. Equipment: Starting equipment choices
5. Personality: Traits, ideals, bonds, flaws
6. Review: Complete sheet preview

**Given** step 1 (Basics)
**When** selecting race and class
**Then** dropdowns show all standard D&D 5e options with brief descriptions

**Given** step 2 (Abilities)
**When** assigning scores
**Then** point-buy calculator shows remaining points
**Or** standard array (15,14,13,12,10,8) can be assigned

**Given** step 3 (Background)
**When** selecting a background
**Then** associated proficiencies and equipment are auto-added

**Given** any step
**When** I want to go back
**Then** I can navigate to previous steps without losing data

## FRs Covered

- FR67: User can create new characters via a wizard UI

## Technical Notes

- Wizard UI in app.py using Streamlit's session_state for multi-step form
- D&D 5e race/class/background data stored in config/dnd5e_data.yaml
- Point buy calculator: 27 points, costs vary by score level
- Standard array: 15, 14, 13, 12, 10, 8 (assignable to any ability)
- Step navigation using session_state["wizard_step"]
- Wizard data accumulated in session_state["wizard_data"]
- Final output: Wizard data dict (CharacterSheet creation deferred to Story 9.4)
- Wizard accessible from session browser "Create Character" button

## Tasks

1. [x] Create config/dnd5e_data.yaml with races, classes, backgrounds
2. [x] Add D&D 5e data loader to config.py
3. [x] Create wizard UI framework in app.py with step navigation
4. [x] Implement Step 1: Basics (name, race, class selection)
5. [x] Implement Step 2: Abilities (point buy and standard array)
6. [x] Implement Step 3: Background selection with proficiencies
7. [x] Implement Step 4: Equipment (starting gear choices)
8. [x] Implement Step 5: Personality traits input
9. [x] Implement Step 6: Review with full CharacterSheet preview
10. [x] Add tests for wizard steps and data validation (57 tests)

## Dev Agent Record

### File List

- `config/dnd5e_data.yaml` - NEW: D&D 5e races, classes, backgrounds, abilities, skills, point buy config
- `config.py` - MODIFIED: Added D&D 5e data loader functions (load_dnd5e_data, get_dnd5e_races, etc.)
- `app.py` - MODIFIED: Added character creation wizard UI (~600 lines)
  - WIZARD_STEPS constant
  - get_default_wizard_data(), init_wizard_state()
  - calculate_point_buy_cost(), get_point_buy_remaining()
  - render_wizard_progress()
  - render_wizard_step_basics() - with class skill selection
  - render_wizard_step_abilities() - point buy and standard array
  - render_wizard_step_background()
  - render_wizard_step_equipment()
  - render_wizard_step_personality()
  - render_wizard_step_review() - validation and preview
  - render_character_creation_wizard() - main wizard renderer
  - render_session_browser() - added "Create Character" button
  - main() - added character_wizard app view routing
- `tests/test_story_9_1_character_wizard.py` - NEW: 52 tests for wizard functionality

### Change Log

- 2026-02-05: Initial implementation of character creation wizard
- 2026-02-05: Code review fixes (H1, M1-M4)
  - Fixed story AC typo (step 3)
  - Added class skill selection UI
  - Fixed equipment review to show fixed items
  - Added unspent points warning in review
  - Added Dev Agent Record section
