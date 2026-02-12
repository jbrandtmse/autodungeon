# Story 16-9: Character Creation & Library

**Epic:** 16 — UI Framework Migration (FastAPI + SvelteKit)
**Status:** in-progress
**Created:** 2026-02-11

---

## User Story

As a **player**,
I want **to browse, create, edit, and delete custom characters through the SvelteKit UI**,
So that **I can build and manage a library of characters for my D&D adventures**.

---

## Acceptance Criteria

### AC1: Character Library Browser
- **Given** the user navigates to `/characters`
- **When** the page loads
- **Then** all preset and library characters are displayed in a card grid
- **And** each card shows name, class, personality snippet, source badge ("Preset" or "Custom"), and class-colored accent
- **And** a search input filters characters by name or class

### AC2: Character Detail View
- **Given** a user clicks a character card
- **When** the detail view opens
- **Then** the full character information is displayed (name, class, personality, provider, model, color, token limit)
- **And** preset characters show a "Preset" badge and no edit/delete controls
- **And** library characters show "Custom" badge with Edit and Delete buttons

### AC3: Character Creation Wizard
- **Given** a user clicks "Create Character"
- **When** the creation wizard opens
- **Then** a multi-step form guides through: Name/Class -> Personality/Backstory -> Provider/Model/Color -> Review
- **And** the Name field is required (validation error if empty)
- **And** the Class field is required (validation error if empty)
- **And** on submit, the character is saved to `config/characters/library/` via POST API
- **And** the user is returned to the library with the new character visible

### AC4: Character Editing
- **Given** a user clicks Edit on a library character
- **When** the edit wizard opens
- **Then** all fields are pre-populated with the existing character data
- **And** on submit, the character is updated via PUT API
- **And** the user is returned to the library with updated data visible

### AC5: Character Deletion
- **Given** a user clicks Delete on a library character
- **When** a confirmation dialog appears and the user confirms
- **Then** the character YAML file is deleted via DELETE API
- **And** the character is removed from the library view
- **And** preset characters cannot be deleted (no delete button shown)

### AC6: API Endpoints
- `POST /api/characters` — creates a new library character YAML file
- `PUT /api/characters/{name}` — updates an existing library character
- `DELETE /api/characters/{name}` — deletes a library character (rejects presets)
- All endpoints include path traversal protection on name parameters
- Character names are sanitized to safe filesystem characters for filenames

### AC7: Content Sanitization
- All user-provided text content is sanitized before rendering
- YAML files use `yaml.safe_dump` for writing
- Character names are validated against injection patterns

---

## Implementation Plan

### Backend (Python)

1. **api/schemas.py** — Add `CharacterCreateRequest`, `CharacterUpdateRequest` Pydantic models
2. **api/routes.py** — Add POST, PUT, DELETE `/api/characters` endpoints
   - Path traversal protection: reject names with `/`, `\`, `..`, or null bytes
   - Filename sanitization: lowercase, replace spaces with hyphens
   - Library-only mutations: reject edits/deletes on preset characters
   - YAML serialization with `yaml.safe_dump`

### Frontend (SvelteKit + Svelte 5)

1. **types.ts** — Add `CharacterCreateRequest`, `CharacterUpdateRequest` interfaces
2. **api.ts** — Add `createCharacter`, `updateCharacter`, `deleteCharacter` functions
3. **CharacterLibrary.svelte** — Card grid with search, create button
4. **CharacterDetail.svelte** — Full character view with edit/delete actions
5. **CharacterCreator.svelte** — Multi-step wizard form (create + edit modes)
6. **routes/characters/+page.svelte** — Route page composing all components
7. **+layout.svelte** — Add Characters nav link

### Tests

- Backend: pytest tests for all 3 new endpoints + validation + path traversal
- Frontend: `npm run build && npm run check` for type safety

---

## Technical Notes

- Svelte 5 runes only (`$state`, `$derived`, `$effect`, `$props`)
- Character class colors: Fighter `#C45C4A`, Rogue `#6B8E6B`, Wizard `#7B68B8`, Cleric `#4A90A4`
- Default color for unknown classes: `#808080`
- Campfire dark theme throughout
- No AI-assisted backstory generation (stays in Streamlit until cutover)
- Character YAML format preserved as per existing files in config/characters/

---

## Dependencies

- Story 16-1 (API Foundation) — done
- Story 16-4 (SvelteKit Scaffold) — done
- Story 16-7 (Session Management UI) — done (pattern reference)
