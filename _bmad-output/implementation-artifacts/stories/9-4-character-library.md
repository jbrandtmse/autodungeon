# Story 9-4: Character Library

## Story

As a **user**,
I want **to save created characters to a library**,
So that **I can reuse them in different campaigns**.

## Status

**Status:** done
**Epic:** 9 - Character Creation UI
**Created:** 2026-02-05
**Updated:** 2026-02-05

## Acceptance Criteria

**Given** a character is created
**When** saved
**Then** it's stored in `config/characters/library/[name].yaml`

**Given** the character library
**When** accessed from party setup
**Then** I see all saved characters with quick stats

**Given** a library character
**When** adding to a party
**Then** a copy is made (original preserved for other campaigns)

**Given** the library view
**When** managing characters
**Then** I can: view, edit, duplicate, or delete characters

**Given** the party setup flow
**When** creating a party
**Then** I can mix library characters with preset characters

## FRs Covered

- FR67: User can create new characters via a wizard UI (library component)

## Technical Notes

- Create config/characters/library/ directory for user-created characters
- Update save_character_to_library() to use library/ subdirectory
- Add render_character_library() UI in app.py
- Show character cards with name, race, class, level (1 for new)
- Add "View", "Edit", "Duplicate", "Delete" buttons per character
- "Edit" reopens wizard with character data pre-filled
- "Duplicate" creates a copy with modified name
- "Delete" removes file after confirmation
- Integrate with party setup - show library characters alongside presets

## Tasks

1. [x] Create config/characters/library/ directory
2. [x] Update save_character_to_library() to use library/ path
3. [x] Add list_library_characters() function
4. [x] Add load_library_character() function
5. [x] Add delete_library_character() function
6. [x] Add duplicate_library_character() function
7. [x] Create render_character_library() UI component
8. [x] Add character card rendering with quick stats
9. [x] Add View/Edit/Duplicate/Delete buttons
10. [x] Integrate library into session browser
11. [x] Add tests for library functions (14 tests)

## Dev Agent Record

### File List

- `app.py` - MODIFIED: Added character library functions and UI
  - LIBRARY_PATH constant for config/characters/library/
  - list_library_characters() - Lists all library characters
  - load_library_character() - Loads character by filename
  - delete_library_character() - Deletes character file
  - duplicate_library_character() - Creates copy with new name
  - convert_character_to_wizard_data() - Converts for editing
  - render_character_library_card() - Character card UI
  - render_character_detail_view() - Full character view
  - render_character_library() - Main library UI
  - render_session_browser() - Added "Character Library" button
  - main() - Added character_library app view routing
  - save_character_to_library() - Updated to use library/ path
- `tests/test_story_9_4_character_library.py` - NEW: 14 tests for library

### Change Log

- 2026-02-05: Story created
- 2026-02-05: Implemented character library with full CRUD operations
