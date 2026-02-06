# Story 9-3: Character Validation

## Story

As a **system**,
I want **to validate created characters against D&D 5e rules**,
So that **characters are mechanically correct**.

## Status

**Status:** done
**Epic:** 9 - Character Creation UI
**Created:** 2026-02-05
**Updated:** 2026-02-05

## Acceptance Criteria

**Given** a character is being created
**When** moving between steps
**Then** validation runs on completed sections

**Given** ability scores
**When** using point buy
**Then** total points cannot exceed the budget (27 standard)

**Given** class/race combinations
**When** selected
**Then** any restrictions are shown (e.g., some races have stat bonuses)

**Given** proficiency selections
**When** exceeding allowed count
**Then** an error prevents proceeding

**Given** the review step
**When** displayed
**Then** a validation summary shows any issues or warnings

**Given** all validation passes
**When** I click "Create Character"
**Then** the character is saved with a complete, valid sheet

## FRs Covered

- FR67: User can create new characters via a wizard UI (validation component)

## Technical Notes

- Add validation functions in app.py for each wizard step
- Validate before allowing "Next" navigation
- Show inline errors with clear messages
- Point buy validation: prevent scores below 8 or above 15 base
- Proficiency count validation: class gives N skills, background gives 2
- Review step shows validation summary with warnings/errors
- Create Character button enabled only when all validation passes
- Character saved to config/characters/ directory as YAML

## Tasks

1. [x] Create validate_wizard_step_basics() function
2. [x] Create validate_wizard_step_abilities() function
3. [x] Create validate_wizard_step_background() function
4. [x] Create validate_wizard_step_equipment() function
5. [x] Create validate_wizard_step_personality() function
6. [x] Add validation summary to render_wizard_step_review()
7. [x] Add "Create Character" button that saves to library
8. [x] Prevent "Next" navigation when validation fails
9. [x] Add tests for validation functions (32 tests)

## Dev Agent Record

### File List

- `app.py` - MODIFIED: Added validation functions and save_character_to_library()
  - validate_wizard_step_basics() - Validates name, race, class, skills
  - validate_wizard_step_abilities() - Validates point buy and standard array
  - validate_wizard_step_background() - Validates background selection
  - validate_wizard_step_equipment() - Validates equipment choices
  - validate_wizard_step_personality() - Always valid (optional fields)
  - validate_wizard_step() - Step dispatcher
  - validate_wizard_complete() - Comprehensive validation with warnings
  - save_character_to_library() - Saves character as YAML to config/characters/
  - render_wizard_step_review() - Updated with validation summary
  - render_character_creation_wizard() - Updated with validation on navigation
- `tests/test_story_9_3_character_validation.py` - NEW: 32 tests for validation

### Change Log

- 2026-02-05: Story created
- 2026-02-05: Implemented all validation functions and save to library feature
