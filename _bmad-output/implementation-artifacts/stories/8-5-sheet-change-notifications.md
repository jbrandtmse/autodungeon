# Story 8-5: Sheet Change Notifications

## Story

As a **user**,
I want **to see when character sheets change**,
So that **I know when someone takes damage, gains loot, or levels up**.

## Status

**Status:** done
**Epic:** 8 - Character Sheets
**Created:** 2026-02-04

## Acceptance Criteria

**Given** a character sheet update occurs
**When** the change is significant (HP, conditions, equipment)
**Then** a subtle notification appears in the UI

**Given** HP changes
**When** displayed
**Then** the notification shows: "Thorin: 52 HP → 35 HP (-17)"

**Given** equipment changes
**When** an item is gained
**Then** the notification shows: "Shadowmere gained: Dagger +1"

**Given** condition changes
**When** a condition is added/removed
**Then** the notification shows: "Elara is now poisoned" or "Aldric is no longer frightened"

**Given** the narrative area
**When** sheet changes occur
**Then** they can optionally be woven into the narrative display

**Given** the character sheet viewer
**When** open during changes
**Then** it updates in real-time with highlighted changes

## FRs Covered

- FR64: Sheet changes are reflected in the narrative

## Technical Notes

- Sheet change notifications should be integrated into the narrative message display
- The `apply_character_sheet_update()` in tools.py already returns a confirmation string with change details
- Notification messages should be stored in the ground_truth_log with a special format (e.g., `[SHEET]` prefix)
- Changes should be rendered in the UI with distinctive styling (different from DM/PC messages)
- The existing campfire theme CSS should have a new style for sheet notifications
- Character sheet viewer modal should show latest values (already does from Story 8-2)
- Must work alongside the dm_turn() tool call handling from Story 8-4

## Tasks

1. [x] Add sheet change entries to ground_truth_log in dm_turn()
2. [x] Add CSS styling for sheet change notifications
3. [x] Update narrative display to render sheet changes distinctively
4. [x] Add change detection for character sheet viewer highlighting
5. [x] Add tests for sheet change notification rendering
6. [x] Add tests for ground_truth_log integration

## Dev Agent Record

### Implementation Summary
- Added `[SHEET]` prefix log entries in dm_turn() for successful sheet updates
- Added `NarrativeMessage.message_type` support for `"sheet_update"` type
- Added `render_sheet_message_html()` and `render_sheet_message()` in app.py
- Added `.sheet-notification` CSS class with amber accent styling
- Updated `render_narrative_messages()` to route `[SHEET]` entries
- Fixed `create_initial_game_state()` and `populate_game_state()` to include `character_sheets`

### Files Touched
- models.py (NarrativeMessage.message_type, factory functions)
- agents.py (sheet_notifications list in dm_turn)
- app.py (render_sheet_message_html, render_sheet_message, routing)
- styles/theme.css (.sheet-notification CSS)
- tests/test_story_8_5_sheet_notifications.py (87 tests)

### Code Review Fixes
- H2: Added character_sheets={} to create_initial_game_state() and populate_game_state()
- L6: Removed dead .sheet-icon CSS rule

### Tests: 87 passing
