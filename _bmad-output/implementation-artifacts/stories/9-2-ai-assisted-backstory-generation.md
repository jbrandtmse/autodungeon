# Story 9-2: AI-Assisted Backstory Generation

## Story

As a **user**,
I want **AI help writing my character's backstory**,
So that **I can have a rich history even if I'm not a creative writer**.

## Status

**Status:** done
**Epic:** 9 - Character Creation UI
**Created:** 2026-02-05
**Updated:** 2026-02-05

## Acceptance Criteria

**Given** the personality/backstory step
**When** I click "Generate with AI"
**Then** the LLM creates personality traits based on race, class, and background

**Given** the AI generation
**When** it runs
**Then** it produces:
- 2 personality traits
- 1 ideal (aligned with background)
- 1 bond (story hook)
- 1 flaw (interesting weakness)
- 2-3 paragraph backstory

**Given** the generated content
**When** displayed
**Then** I can edit any part before accepting

**Given** I don't like the generation
**When** I click "Regenerate"
**Then** new content is generated with the same inputs

**Given** I prefer to write manually
**When** I skip AI generation
**Then** I can fill in all fields by hand

## FRs Covered

- FR68: System can assist with backstory generation

## Technical Notes

- Add "Generate with AI" button to render_wizard_step_personality() in app.py
- Use existing LLM factory (agents.py get_llm()) to query the DM provider
- Create backstory generation prompt that incorporates:
  - Selected race (name, traits, cultural context)
  - Selected class (role, typical background)
  - Selected background (feature, typical personality)
- Parse LLM response to extract structured fields
- Populate wizard_data fields with generated content
- User can edit generated content in text areas before proceeding
- Add "Regenerate" button to get fresh generation
- Show loading spinner during LLM call
- Handle LLM errors gracefully with user-friendly message

## Tasks

1. [x] Create backstory generation prompt template
2. [x] Add generate_backstory() function in app.py
3. [x] Add "Generate with AI" button to personality step
4. [x] Implement LLM call using existing provider infrastructure
5. [x] Parse LLM response and populate wizard fields
6. [x] Add "Regenerate" button for fresh generation
7. [x] Add loading spinner during generation
8. [x] Handle LLM errors with user-friendly messages
9. [x] Add tests for backstory generation (19 tests)

## Dev Agent Record

### File List

- `app.py` - MODIFIED: Added backstory generation functions
  - generate_backstory_prompt() - Creates LLM prompt from character selections
  - parse_backstory_response() - Parses structured LLM response
  - generate_backstory() - Main function that calls LLM
  - render_wizard_step_personality() - Updated with AI generation buttons
- `tests/test_story_9_2_backstory_generation.py` - NEW: 19 tests for backstory generation

### Change Log

- 2026-02-05: Initial implementation of AI-assisted backstory generation
