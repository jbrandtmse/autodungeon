# Story 16-10: Advanced Features UI

**Epic:** 16 — UI Framework Migration (FastAPI + SvelteKit)
**Status:** ready-for-dev

---

## Story

As a **user playing autodungeon in the SvelteKit frontend**,
I want **fork management controls, a whisper system panel, character sheet viewer, story threads (callback) panel, and a checkpoint browser integrated into the game page and sidebar**,
so that **I can access all the advanced features of the game engine (alternate timelines, private DM communication, character details, narrative tracking, and game history) without needing the legacy Streamlit UI**.

---

## Acceptance Criteria

### AC1: Fork Management — Create Fork

**Given** the user is on the game page (`/game/{sessionId}`) with an active session
**When** they expand the "Fork Timeline" section in the sidebar
**Then** a text input labeled "Fork name" with placeholder "e.g., Diplomacy attempt" is shown
**And** a "Create Fork" button is shown below the input
**When** the user enters a name and clicks "Create Fork"
**Then** `POST /api/sessions/{sessionId}/forks` is called with `{ name: "..." }`
**And** on success, a toast shows "Fork '{name}' created at turn {N}"
**And** the fork appears in the fork list below
**When** the user clicks "Create Fork" with an empty name
**Then** a validation message "Please enter a fork name" is shown inline

### AC2: Fork Management — Fork List & Switch

**Given** the session has one or more forks
**When** the "Fork Timeline" section renders
**Then** each fork is displayed as a card showing:
  - Fork name in bold
  - "(active)" badge if this fork is currently loaded
  - Metadata: "Branched at turn {N} | Turns: {N} | Last: {date}"
**And** each non-active fork has a "Switch" button
**When** the user clicks "Switch" on a fork
**Then** `POST /api/sessions/{sessionId}/forks/{forkId}/switch` is called
**And** the game state reloads with the fork's state
**And** the sidebar shows "Playing fork: {name}" with a "Return to Main" button

### AC3: Fork Management — Return to Main

**Given** the user is playing in a fork (active_fork_id is set)
**When** they click "Return to Main"
**Then** `POST /api/sessions/{sessionId}/forks/return-to-main` is called
**And** the game state reloads from the main timeline
**And** the "Playing fork" indicator disappears

### AC4: Fork Management — Compare, Rename, Delete, Promote

**Given** a fork exists in the fork list
**When** the user clicks "Compare"
**Then** `GET /api/sessions/{sessionId}/forks/{forkId}/compare` is called
**And** a comparison overlay replaces the narrative area, showing side-by-side turns
**And** a "Close" button in the comparison header exits comparison mode

**Given** a fork's overflow menu ("...") is open
**When** the user enters a new name and clicks "Save"
**Then** `PUT /api/sessions/{sessionId}/forks/{forkId}` is called with `{ name: "..." }`
**And** the fork name updates in the list

**When** the user clicks "Delete" on a non-active fork
**Then** a confirmation dialog appears: "Delete '{name}'? Cannot be undone."
**And** on confirm, `DELETE /api/sessions/{sessionId}/forks/{forkId}` is called
**And** the fork is removed from the list

**When** the user clicks "Make Primary"
**Then** a confirmation dialog explains the promotion consequences
**And** on confirm, `POST /api/sessions/{sessionId}/forks/{forkId}/promote` is called
**And** the page reloads with the promoted fork as the main timeline

### AC5: Whisper System — Send Whisper

**Given** the user is on the game page in Watch Mode (not controlling a character)
**When** they look at the sidebar below the Human Controls section
**Then** a "Whisper to DM" section is visible with a text area and "Send Whisper" button
**When** the user enters text and clicks "Send Whisper"
**Then** the whisper is sent via WebSocket command `{ type: "whisper", content: "..." }`
**And** a success toast shows "Whisper sent - the DM will respond privately"
**And** the text area clears

**Given** the user is controlling a character (human_active is true)
**Then** the whisper input section is hidden

### AC6: Whisper System — Whisper History

**Given** the session has whispers in the game state (agent_secrets with whispers)
**When** the user expands the "Whisper History" section in the sidebar
**Then** whispers are grouped by character name
**And** each whisper shows:
  - A status badge ("Active" in amber or "Revealed" in green)
  - Turn info: "Turn {N}" or "Turn {N} (Revealed turn {M})"
  - The whisper content text
**And** revealed whispers have a dimmed visual style compared to active whispers

### AC7: Character Sheet Viewer — Open from Party Panel

**Given** the user clicks a character name or a "View Sheet" button on a character card in the party panel
**When** the character sheet modal opens
**Then** `GET /api/sessions/{sessionId}/character-sheets/{characterName}` is called
**And** a modal overlay displays the full character sheet with:
  - Header: name, race, class, level, background, alignment
  - Two-column layout:
    - Left: Ability scores (6 stats with modifiers), Combat stats (AC, HP, speed, initiative), Equipment (collapsible)
    - Right: Skills (collapsible), Spellcasting (if applicable, expanded by default), Features & Traits (collapsible), Personality (collapsible)
**And** ability score modifiers are displayed in JetBrains Mono font
**And** the modal uses `--bg-secondary` background with campfire theme styling
**And** the modal can be closed via X button, Escape key, or backdrop click

### AC8: Story Threads (Callback) Panel — Element List

**Given** the game state has a `callback_database` with narrative elements
**When** the user expands "Story Threads" in the sidebar (replacing the placeholder)
**Then** a summary bar shows: "{N} Active | {N} Dormant | {N} Story Moments"
**And** active (non-dormant) elements are listed first, sorted by relevance
**And** dormant elements are listed after, visually dimmed
**And** each element card shows:
  - Element type icon/badge (character, item, location, event, promise, threat)
  - Element name in bold
  - Description snippet (truncated to ~80 chars)
  - Reference count: "Referenced {N} times"
  - Characters involved as comma-separated names

### AC9: Story Threads — Element Detail & Callback Timeline

**Given** the user clicks on a story element card
**When** the detail expands
**Then** the full description is shown
**And** potential callbacks are listed if any exist
**And** a "Callback Timeline" section shows:
  - "Introduced in Turn {N}, Session {M}" as the first entry
  - Each callback entry with turn number, match type label, context snippet
  - Story moment entries (20+ turn gap) highlighted with special styling and gap label
**And** the match type is displayed as human-readable text: "exact name match", "fuzzy name match", "keyword match"

### AC10: Checkpoint Browser — List and Preview

**Given** the user expands "Session History" in the sidebar
**When** the section renders
**Then** `GET /api/sessions/{sessionId}/checkpoints` is called
**And** checkpoints are displayed in reverse order (newest first)
**And** each checkpoint shows: turn number, timestamp, brief context preview
**When** the user clicks "Preview" on a checkpoint
**Then** `GET /api/sessions/{sessionId}/checkpoints/{turn}/preview` is called
**And** the last few log entries from that checkpoint are shown inline in italic
**And** a "Close" button collapses the preview

### AC11: Checkpoint Browser — Restore

**Given** a checkpoint is shown that is older than the current game state
**When** the user clicks "Restore"
**Then** a confirmation dialog appears: "Restore to Turn {N}? This will undo {M} turn(s)."
**When** the user confirms
**Then** `POST /api/sessions/{sessionId}/checkpoints/{turn}/restore` is called
**And** the game state reloads from the restored checkpoint
**And** a toast shows "Restored to Turn {N}"
**And** autopilot stops if running

### AC12: New API Endpoints Required

**Given** the backend in `api/routes.py`
**Then** the following NEW endpoints are added:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/sessions/{id}/forks` | List forks for a session |
| POST | `/api/sessions/{id}/forks` | Create a new fork |
| PUT | `/api/sessions/{id}/forks/{forkId}` | Rename a fork |
| DELETE | `/api/sessions/{id}/forks/{forkId}` | Delete a fork |
| POST | `/api/sessions/{id}/forks/{forkId}/switch` | Switch to a fork |
| POST | `/api/sessions/{id}/forks/{forkId}/promote` | Promote fork to main |
| POST | `/api/sessions/{id}/forks/return-to-main` | Return from fork to main |
| GET | `/api/sessions/{id}/forks/{forkId}/compare` | Get comparison data |
| GET | `/api/sessions/{id}/checkpoints` | List checkpoints |
| GET | `/api/sessions/{id}/checkpoints/{turn}/preview` | Preview a checkpoint |
| POST | `/api/sessions/{id}/checkpoints/{turn}/restore` | Restore to checkpoint |
| GET | `/api/sessions/{id}/character-sheets/{name}` | Get full character sheet |

All endpoints wrap existing `persistence.py` functions. All endpoints validate `session_id` format and check session existence.

### AC13: TypeScript Types for New Features

**Given** the frontend `types.ts`
**Then** new interfaces are added for:
  - `ForkMetadata` (fork_id, name, parent_session_id, branch_turn, created_at, updated_at, turn_count)
  - `ComparisonData` (session_id, branch_turn, left: ComparisonTimeline, right: ComparisonTimeline)
  - `ComparisonTimeline` (label, timeline_type, fork_id, turns: ComparisonTurn[], total_turns)
  - `ComparisonTurn` (turn_number, entries: string[], is_branch_point, is_ended)
  - `Whisper` (id, from_agent, to_agent, content, turn_created, revealed, turn_revealed)
  - `CharacterSheetFull` (all CharacterSheet fields from models.py)
  - `NarrativeElement` (id, element_type, name, description, turn_introduced, etc.)
  - `CallbackEntry` (id, element_id, element_name, element_type, turn_detected, turn_gap, match_type, match_context, is_story_moment)
  - `CheckpointInfo` (turn_number, timestamp, brief_context, message_count)

### AC14: No Python Backend Modifications Beyond API Endpoints

**Given** this story adds API endpoints
**Then** NO modifications are made to `models.py`, `persistence.py`, `graph.py`, `agents.py`, `memory.py`, `tools.py`, or `config.py`
**And** only `api/routes.py`, `api/schemas.py`, and `sprint-status.yaml` are modified on the Python side

---

## Tasks / Subtasks

- [ ] **Task 1: Add Fork API endpoints to backend** (AC: 12, 14)
  - [ ] 1.1: Add fork-related Pydantic schemas to `api/schemas.py`:
    - `ForkCreateRequest(name: str)`
    - `ForkRenameRequest(name: str)`
    - `ForkMetadataResponse` (mirrors `ForkMetadata` model)
    - `ComparisonDataResponse` (mirrors `ComparisonData` model)
  - [ ] 1.2: Add `GET /api/sessions/{id}/forks` — calls `list_forks(session_id)`, returns list of `ForkMetadataResponse`
  - [ ] 1.3: Add `POST /api/sessions/{id}/forks` — calls `create_fork(state, session_id, fork_name)`, needs to load latest state from checkpoint first
  - [ ] 1.4: Add `PUT /api/sessions/{id}/forks/{fork_id}` — calls `rename_fork(session_id, fork_id, new_name)`
  - [ ] 1.5: Add `DELETE /api/sessions/{id}/forks/{fork_id}` — calls `delete_fork(session_id, fork_id, active_fork_id=None)`
  - [ ] 1.6: Add `POST /api/sessions/{id}/forks/{fork_id}/switch` — calls `switch_to_fork(session_id, fork_id)`, returns updated state
  - [ ] 1.7: Add `POST /api/sessions/{id}/forks/{fork_id}/promote` — calls `promote_fork(session_id, fork_id)`
  - [ ] 1.8: Add `POST /api/sessions/{id}/forks/return-to-main` — loads main timeline state from checkpoint
  - [ ] 1.9: Add `GET /api/sessions/{id}/forks/{fork_id}/compare` — calls `build_comparison_data(session_id, fork_id)`
  - [ ] 1.10: Add backend tests for all fork endpoints

- [ ] **Task 2: Add Checkpoint API endpoints to backend** (AC: 12, 14)
  - [ ] 2.1: Add checkpoint-related Pydantic schemas to `api/schemas.py`:
    - `CheckpointInfoResponse(turn_number, timestamp, brief_context, message_count)`
    - `CheckpointPreviewResponse(turn_number, entries: list[str])`
  - [ ] 2.2: Add `GET /api/sessions/{id}/checkpoints` — calls `list_checkpoint_info(session_id)`
  - [ ] 2.3: Add `GET /api/sessions/{id}/checkpoints/{turn}/preview` — calls `get_checkpoint_preview(session_id, turn_number)`
  - [ ] 2.4: Add `POST /api/sessions/{id}/checkpoints/{turn}/restore` — calls `load_checkpoint(session_id, turn_number)`, persists as current state
  - [ ] 2.5: Add backend tests for checkpoint endpoints

- [ ] **Task 3: Add Character Sheet API endpoint to backend** (AC: 12, 14)
  - [ ] 3.1: Add `CharacterSheetResponse` schema to `api/schemas.py` — mirrors full `CharacterSheet` model fields
  - [ ] 3.2: Add `GET /api/sessions/{id}/character-sheets/{name}` — loads game state, finds character sheet from `character_sheets` dict in state
  - [ ] 3.3: Add backend test for character sheet endpoint

- [ ] **Task 4: Add TypeScript types for new features** (AC: 13)
  - [ ] 4.1: Add `ForkMetadata`, `ComparisonData`, `ComparisonTimeline`, `ComparisonTurn` interfaces to `types.ts`
  - [ ] 4.2: Add `Whisper`, `WhisperHistory` interfaces to `types.ts`
  - [ ] 4.3: Add `CharacterSheetFull` interface to `types.ts` with all D&D 5e fields (ability scores, combat stats, skills, spells, equipment, personality)
  - [ ] 4.4: Add `NarrativeElement`, `CallbackEntry`, `StoryThreadsSummary` interfaces to `types.ts`
  - [ ] 4.5: Add `CheckpointInfo`, `CheckpointPreview` interfaces to `types.ts`

- [ ] **Task 5: Extend frontend API client** (AC: 12)
  - [ ] 5.1: Add fork API functions to `api.ts`:
    ```typescript
    export async function getForks(sessionId: string): Promise<ForkMetadata[]>
    export async function createFork(sessionId: string, name: string): Promise<ForkMetadata>
    export async function renameFork(sessionId: string, forkId: string, name: string): Promise<ForkMetadata>
    export async function deleteFork(sessionId: string, forkId: string): Promise<void>
    export async function switchFork(sessionId: string, forkId: string): Promise<void>
    export async function promoteFork(sessionId: string, forkId: string): Promise<void>
    export async function returnToMain(sessionId: string): Promise<void>
    export async function getComparison(sessionId: string, forkId: string): Promise<ComparisonData>
    ```
  - [ ] 5.2: Add checkpoint API functions to `api.ts`:
    ```typescript
    export async function getCheckpoints(sessionId: string): Promise<CheckpointInfo[]>
    export async function getCheckpointPreview(sessionId: string, turn: number): Promise<CheckpointPreview>
    export async function restoreCheckpoint(sessionId: string, turn: number): Promise<void>
    ```
  - [ ] 5.3: Add character sheet API function to `api.ts`:
    ```typescript
    export async function getCharacterSheet(sessionId: string, name: string): Promise<CharacterSheetFull>
    ```
  - [ ] 5.4: Use `fetch` directly for 204 No Content responses (deleteFork), same pattern as existing `deleteSession`

- [ ] **Task 6: Create ForkPanel.svelte** (AC: 1, 2, 3, 4)
  - [ ] 6.1: Create `frontend/src/lib/components/ForkPanel.svelte`
  - [ ] 6.2: Define props: `sessionId: string`
  - [ ] 6.3: State management:
    ```typescript
    let forks = $state<ForkMetadata[]>([]);
    let forkNameInput = $state('');
    let creating = $state(false);
    let loading = $state(true);
    ```
  - [ ] 6.4: Load forks via `getForks(sessionId)` on mount and after mutations
  - [ ] 6.5: "Playing fork" banner with "Return to Main" button when `activeForkId` is set (derived from game state)
  - [ ] 6.6: Create fork form with input + button
  - [ ] 6.7: Fork list rendering with Switch, Compare buttons
  - [ ] 6.8: Overflow menu ("...") with Rename, Delete, Make Primary actions
  - [ ] 6.9: Delete confirmation via ConfirmDialog
  - [ ] 6.10: Promote confirmation with explanation text via ConfirmDialog
  - [ ] 6.11: Scoped CSS using `<details>` collapsible pattern matching Story Threads styling

- [ ] **Task 7: Create ForkComparison.svelte** (AC: 4)
  - [ ] 7.1: Create `frontend/src/lib/components/ForkComparison.svelte`
  - [ ] 7.2: Define props: `sessionId: string, forkId: string, onClose: () => void`
  - [ ] 7.3: Load comparison data via `getComparison(sessionId, forkId)`
  - [ ] 7.4: Render header with timeline labels, branch turn info, and "Close" button
  - [ ] 7.5: Render side-by-side grid of aligned turns
  - [ ] 7.6: Branch point turn highlighted with special styling
  - [ ] 7.7: "[Timeline ends here]" marker for shorter timelines
  - [ ] 7.8: Each turn's entries collapsible (truncated first entry as summary)
  - [ ] 7.9: Position as overlay on the narrative area (conditionally rendered in game page)

- [ ] **Task 8: Create WhisperPanel.svelte** (AC: 5, 6)
  - [ ] 8.1: Create `frontend/src/lib/components/WhisperPanel.svelte`
  - [ ] 8.2: Whisper input section:
    - Label: "Whisper to DM"
    - Hint text: "Ask the DM something privately..."
    - Text area with placeholder
    - "Send Whisper" button
    - Hidden when `human_active` is true (user controlling a character)
  - [ ] 8.3: Send whisper via WebSocket command `{ type: "whisper", content: "..." }`
  - [ ] 8.4: Success toast on send, clear input
  - [ ] 8.5: Whisper History section:
    - Collapsible `<details>` element
    - Whispers grouped by character name
    - Each whisper: status badge (Active/Revealed), turn info, content
    - Revealed whispers dimmed with `opacity: 0.6`
    - Active whispers styled with amber accent
  - [ ] 8.6: Derive whisper data from `gameState.agent_secrets` (or from game state's whisper-related fields)

- [ ] **Task 9: Create CharacterSheetModal.svelte** (AC: 7)
  - [ ] 9.1: Create `frontend/src/lib/components/CharacterSheetModal.svelte`
  - [ ] 9.2: Define props: `open: boolean, sessionId: string, characterName: string, onClose: () => void`
  - [ ] 9.3: Load character sheet via `getCharacterSheet(sessionId, characterName)` when opened
  - [ ] 9.4: Loading state while fetching
  - [ ] 9.5: Header section: name, race, class, level, background, alignment
  - [ ] 9.6: Two-column layout:
    - Left column:
      - Ability scores grid (6 stats with score and modifier in JetBrains Mono)
      - Combat stats (AC, HP bar with current/max/temp, speed, initiative, hit dice)
      - Equipment section (collapsible): weapons, armor, items, currency
    - Right column:
      - Skills section (collapsible): list with proficiency/expertise markers
      - Spellcasting section (if spellcasting_ability is set, expanded by default): spell save DC, attack bonus, slots, cantrips, spell list
      - Features & Traits (collapsible): class features, racial traits, feats
      - Personality (collapsible): personality traits, ideals, bonds, flaws, backstory
  - [ ] 9.7: HP bar component: green/amber/red coloring based on percentage
  - [ ] 9.8: Modal overlay with `--bg-secondary` background, 12px radius, max-width 800px
  - [ ] 9.9: Close via X button, Escape key, backdrop click
  - [ ] 9.10: Scoped CSS matching campfire theme

- [ ] **Task 10: Create StoryThreadsPanel.svelte** (AC: 8, 9)
  - [ ] 10.1: Create `frontend/src/lib/components/StoryThreadsPanel.svelte`
  - [ ] 10.2: Replace the "Coming soon..." placeholder in Sidebar.svelte
  - [ ] 10.3: Summary bar: "N Active | N Dormant | N Story Moments"
  - [ ] 10.4: Element card component with:
    - Type badge (character, item, location, event, promise, threat) with distinct colors/icons
    - Name in bold, description snippet, reference count
    - Characters involved
  - [ ] 10.5: Expandable detail on click:
    - Full description
    - Potential callbacks list
    - Callback timeline (chronological entries)
  - [ ] 10.6: Timeline entry rendering:
    - "Introduced in Turn N, Session M" as first entry
    - Callback entries with turn, match type label, context snippet
    - Story moment entries highlighted (amber border, turn gap label)
  - [ ] 10.7: Match type label mapping: name_exact -> "exact name match", name_fuzzy -> "fuzzy name match", description_keyword -> "keyword match"
  - [ ] 10.8: Active elements sorted by relevance first, dormant elements below with dimmed styling
  - [ ] 10.9: Derive data from `$gameState.callback_database` and `$gameState.callback_log`

- [ ] **Task 11: Create CheckpointBrowser.svelte** (AC: 10, 11)
  - [ ] 11.1: Create `frontend/src/lib/components/CheckpointBrowser.svelte`
  - [ ] 11.2: Define props: `sessionId: string`
  - [ ] 11.3: Load checkpoints via `getCheckpoints(sessionId)` on mount
  - [ ] 11.4: Checkpoint list (reverse chronological):
    - Each entry: turn number, timestamp, brief context
    - "Preview" button → loads and displays log entry preview inline
    - "Restore" button (only for checkpoints older than current state)
  - [ ] 11.5: Preview rendering: italic log entries from `getCheckpointPreview()`, with "Close" button
  - [ ] 11.6: Restore confirmation via ConfirmDialog: "Restore to Turn {N}? This will undo {M} turn(s)."
  - [ ] 11.7: On restore success: reload game state, show toast, stop autopilot via WebSocket command
  - [ ] 11.8: Empty state: "No checkpoints available yet"
  - [ ] 11.9: Use `<details>` collapsible pattern matching sidebar section styling

- [ ] **Task 12: Integrate components into Sidebar and Game Page** (AC: all)
  - [ ] 12.1: Update `Sidebar.svelte`:
    - Import and render `ForkPanel` (in new collapsible section)
    - Import and render `WhisperPanel` (below HumanControls)
    - Replace Story Threads placeholder with `StoryThreadsPanel`
    - Import and render `CheckpointBrowser` (in "Session History" collapsible section)
    - Pass `sessionId` prop through (derived from page params or game state)
  - [ ] 12.2: Update `+page.svelte` (game page):
    - Conditionally render `ForkComparison` overlay when comparison mode is active
    - Add comparison mode state (`comparisonMode`, `comparisonForkId`)
  - [ ] 12.3: Update `PartyPanel.svelte` or `CharacterCard.svelte`:
    - Add "View Sheet" button/clickable name to open CharacterSheetModal
  - [ ] 12.4: Render `CharacterSheetModal` in game page (or layout) with portal-like positioning
  - [ ] 12.5: Wire up the session ID for all sidebar components:
    - Derive from `$gameState?.session_id` or from `$page.params.sessionId`
    - Components should gracefully handle null/undefined sessionId (hide or show empty state)

- [ ] **Task 13: Add WebSocket whisper command support** (AC: 5)
  - [ ] 13.1: Add `WsCmdWhisper` type to `types.ts`:
    ```typescript
    export interface WsCmdWhisper {
      type: 'whisper';
      content: string;
    }
    ```
  - [ ] 13.2: Add `WsCmdWhisper` to the `WsCommand` union type
  - [ ] 13.3: Verify `sendCommand` in the connection store works for the whisper command

- [ ] **Task 14: Verification and polish** (all ACs)
  - [ ] 14.1: Start backend: `uvicorn api.main:app --reload --port 8000`
  - [ ] 14.2: Start frontend: `cd frontend && npm run dev`
  - [ ] 14.3: Navigate to a game session with existing data
  - [ ] 14.4: Verify Fork Panel: create fork, switch, compare, rename, delete, promote, return to main
  - [ ] 14.5: Verify Whisper Panel: send whisper, view whisper history (if data exists)
  - [ ] 14.6: Verify Character Sheet: click character name in party panel, modal opens with sheet data
  - [ ] 14.7: Verify Story Threads: expand panel, see elements, expand element detail, see timeline
  - [ ] 14.8: Verify Checkpoint Browser: expand, list checkpoints, preview, restore
  - [ ] 14.9: Use chrome-devtools MCP to take screenshots verifying campfire theme consistency
  - [ ] 14.10: Run `cd frontend && npm run check` — TypeScript passes
  - [ ] 14.11: Run `cd frontend && npm run build` — production build succeeds

- [ ] **Task 15: Verify no Python backend regressions** (AC: 14)
  - [ ] 15.1: Run `python -m ruff check .` from project root — no new violations
  - [ ] 15.2: Run `python -m pytest` from project root — no regressions
  - [ ] 15.3: Verify `uvicorn api.main:app` — no import errors
  - [ ] 15.4: Update `sprint-status.yaml`

---

## Dev Notes

### Architecture Context

This story builds the **advanced features UI** for the SvelteKit frontend. It ports five Streamlit feature areas to SvelteKit components:

| Feature | Streamlit Source | SvelteKit Component |
|---------|-----------------|-------------------|
| Fork Management | `render_fork_controls()` (app.py:7495), `render_comparison_view()` (app.py:7374) | `ForkPanel.svelte`, `ForkComparison.svelte` |
| Whisper System | `render_human_whisper_input()` (app.py:845), `render_whisper_history()` (app.py:1432) | `WhisperPanel.svelte` |
| Character Sheet | `render_character_sheet_modal()` (app.py:4943) | `CharacterSheetModal.svelte` |
| Story Threads | `render_story_threads()` (app.py:1146), `render_callback_timeline_html()` (app.py:1071) | `StoryThreadsPanel.svelte` |
| Checkpoint Browser | `render_checkpoint_browser()` (app.py:5165), `render_checkpoint_preview()` (app.py:5099) | `CheckpointBrowser.svelte` |

The Streamlit implementations call `persistence.py` functions directly. The SvelteKit frontend must go through REST API endpoints, so this story creates those endpoints as thin wrappers around existing persistence functions.

### Component Hierarchy

```
+page.svelte (/game/[sessionId])
  ├── ForkComparison.svelte (overlay, conditional)
  ├── CharacterSheetModal.svelte (modal, conditional)
  └── NarrativePanel.svelte (existing)

Sidebar.svelte
  ├── ModeIndicator (existing)
  ├── GameControls (existing)
  ├── PartyPanel (existing, modified for sheet link)
  │     └── CharacterCard (existing, add "View Sheet" button)
  ├── CombatInitiative (existing)
  ├── HumanControls (existing)
  ├── WhisperPanel.svelte (NEW — whisper input + history)
  ├── ForkPanel.svelte (NEW — create/switch/manage forks)
  ├── StoryThreadsPanel.svelte (NEW — replaces placeholder)
  ├── CheckpointBrowser.svelte (NEW — list/preview/restore)
  ├── ConnectionStatus (existing)
  └── Settings button (existing)
```

### API Endpoint Design

All new endpoints follow the established patterns in `routes.py`:
1. Validate `session_id` format via `_validate_session_id()`
2. Check session exists via `load_session_metadata()`
3. Call the appropriate `persistence.py` function
4. Return response or appropriate HTTP error

**Fork endpoints** wrap these `persistence.py` functions:
- `list_forks(session_id)` — returns `list[ForkMetadata]`
- `create_fork(state, session_id, fork_name)` — returns `ForkMetadata`
- `rename_fork(session_id, fork_id, new_name)` — returns `ForkMetadata`
- `delete_fork(session_id, fork_id, active_fork_id)` — returns `bool`
- `promote_fork(session_id, fork_id)` — returns turn count
- `build_comparison_data(session_id, fork_id)` — returns `ComparisonData | None`

Note: `create_fork` requires a `GameState` (not just `session_id`). The endpoint must load the latest checkpoint first:
```python
latest_turn = get_latest_checkpoint(session_id)
state = load_checkpoint(session_id, latest_turn)
fork_meta = create_fork(state=state, session_id=session_id, fork_name=body.name)
```

**Switch to fork** and **return to main** need to load fork/main state respectively. The Streamlit app used `handle_switch_to_fork()` and `handle_return_to_main()` in `app.py`. For the REST API, these endpoints should load the appropriate state and return it (or return a redirect/success signal, and the frontend reloads state via WebSocket reconnection).

**Checkpoint endpoints** wrap:
- `list_checkpoint_info(session_id)` — returns `list[CheckpointInfo]`
- `get_checkpoint_preview(session_id, turn_number)` — returns `list[str] | None`
- `load_checkpoint(session_id, turn_number)` — returns `GameState | None`

**Character sheet endpoint** must load the latest game state and extract the `CharacterSheet` from `state["character_sheets"]`. The `get_character_sheet()` function in `app.py:4884` does this lookup using character name matching against the character config keys.

### Whisper System — WebSocket vs REST

Whisper sending uses WebSocket (not REST) because the Streamlit app sends whispers via `st.session_state["pending_human_whisper"]` which the game loop picks up during the next turn. In the SvelteKit model, the WebSocket handler already processes various command types. A new `whisper` command type should be added:

```python
# In api/websocket.py message handler:
elif cmd_type == "whisper":
    content = data.get("content", "")
    if content.strip():
        engine.submit_whisper(content)
```

The engine may need a `submit_whisper` method or the WebSocket handler can set the appropriate state directly. Check `api/engine.py` and `api/websocket.py` for the existing command handling pattern to determine the best approach.

**Important:** If `engine.py` does not yet have a whisper submission method, the WebSocket handler can set the whisper on the game state directly (similar to how nudges work). The game loop will pick it up on the next turn.

Whisper history reads from the game state's `agent_secrets` field, which is streamed via the `session_state` WebSocket event. The frontend derives whisper history from `$gameState` — no separate REST endpoint needed.

### Story Threads — Data Source

Story threads data comes from two game state fields:
- `callback_database: NarrativeElementStore` — the database of tracked narrative elements
- `callback_log: CallbackLog` — the log of detected callback entries

Both are streamed in the `session_state` WebSocket event. The frontend derives all story thread data from `$gameState` — no separate REST endpoint is needed for this feature.

The sidebar component subscribes to `$gameState` and derives:
```typescript
let elements = $derived($gameState?.callback_database?.elements ?? []);
let callbackEntries = $derived($gameState?.callback_log?.entries ?? []);
let activeElements = $derived(elements.filter(e => !e.dormant && !e.resolved));
let dormantElements = $derived(elements.filter(e => e.dormant));
let storyMoments = $derived(callbackEntries.filter(e => e.is_story_moment));
```

### Fork Comparison — Overlay Architecture

The comparison view replaces the narrative area temporarily. In the Streamlit app, `render_comparison_view()` replaces the normal narrative render. In SvelteKit:

```svelte
<!-- In +page.svelte -->
{#if comparisonMode}
  <ForkComparison sessionId={sessionId} forkId={comparisonForkId} onClose={() => comparisonMode = false} />
{:else}
  <NarrativePanel />
{/if}
```

The comparison mode state is local to the game page (not in a global store) since it only applies to the game view.

### Character Sheet — Modal Pattern

Reuse the modal overlay pattern from `ConfirmDialog.svelte` and `SettingsModal.svelte`:
- Backdrop: `rgba(0,0,0,0.6)`, click to close
- Dialog: `--bg-secondary` bg, 12px radius, max-width 800px
- Escape key closes
- Focus trap

The character sheet modal is larger than confirmation dialogs and uses a two-column grid layout for the D&D sheet sections.

### Collapsible Sidebar Sections

Several new sidebar components use the collapsible `<details>` element pattern already established by the Story Threads placeholder in Sidebar.svelte:

```svelte
<details class="sidebar-section">
  <summary class="sidebar-section-summary">Section Title</summary>
  <div class="sidebar-section-content">
    <!-- Content -->
  </div>
</details>
```

Use the same CSS styling from the existing `.story-threads-summary` pattern:
- Uppercase text, 0.08em letter spacing
- Custom triangle marker via `::before` pseudo-element
- Rotate on open

### Svelte 5 Patterns Used

| Pattern | Usage |
|---------|-------|
| `$state()` | Local component state (forks, checkpoints, loading flags, form inputs) |
| `$derived()` | Computed values from gameState (whisper history, story elements, active fork) |
| `$effect()` | Load data on mount, reload after mutations |
| `$props()` | Component props (sessionId, characterName, open, onClose, etc.) |
| `{#if}` | Conditional rendering (comparison mode, modal open, loading states) |
| `{#each ... (key)}` | Keyed iteration (forks, checkpoints, elements, whispers) |
| `transition:slide` | Collapsible section animations |
| `transition:fade` | Modal backdrop fade |
| `bind:open` | Two-way binding on `<details>` elements |
| `onclick` | Button handlers |

### File Structure Created/Modified by This Story

```
api/
  routes.py                                # MODIFIED: add fork, checkpoint, character-sheet endpoints
  schemas.py                               # MODIFIED: add request/response schemas for new endpoints

frontend/src/
├── lib/
│   ├── types.ts                           # MODIFIED: add Fork, Whisper, CharacterSheet, etc. types
│   ├── api.ts                             # MODIFIED: add fork, checkpoint, character-sheet API functions
│   └── components/
│       ├── ForkPanel.svelte               # NEW: fork create/list/manage sidebar panel
│       ├── ForkComparison.svelte          # NEW: side-by-side comparison overlay
│       ├── WhisperPanel.svelte            # NEW: whisper input + history sidebar panel
│       ├── CharacterSheetModal.svelte     # NEW: full character sheet modal
│       ├── StoryThreadsPanel.svelte       # NEW: callback/narrative element tracker
│       ├── CheckpointBrowser.svelte       # NEW: checkpoint list/preview/restore
│       ├── Sidebar.svelte                 # MODIFIED: integrate new panels
│       ├── PartyPanel.svelte              # MODIFIED: add "View Sheet" trigger
│       └── CharacterCard.svelte           # MODIFIED: add clickable name for sheet
└── routes/
    └── game/
        └── [sessionId]/
            └── +page.svelte               # MODIFIED: add ForkComparison overlay, CharacterSheetModal
```

### Common Pitfalls to Avoid

1. **Do NOT modify `models.py`, `persistence.py`, `graph.py`, `agents.py`, `memory.py`, `tools.py`, or `config.py`.** Only `api/routes.py`, `api/schemas.py`, and `sprint-status.yaml` change on the Python side.
2. **Do NOT call `response.json()` on 204 No Content responses.** The `deleteFork` API function must use the same pattern as `deleteSession` — use `fetch` directly and skip JSON parsing.
3. **Do NOT use `window.confirm()`.** Use the existing `ConfirmDialog.svelte` component for all confirmation flows (delete fork, promote fork, restore checkpoint).
4. **Do NOT use Svelte 4 reactive syntax** (`$:`, `export let`). Use Svelte 5 runes only: `$state`, `$derived`, `$effect`, `$props`.
5. **Do NOT add inline styles.** Use scoped CSS with campfire theme CSS custom properties (`--bg-secondary`, `--text-primary`, `--accent-warm`, etc.).
6. **Do NOT forget session_id validation in API endpoints.** Every new endpoint must call `_validate_session_id()` and check session exists via `load_session_metadata()`.
7. **Do NOT render whisper input when user is controlling a character.** The whisper section must check `human_active` from game state and hide accordingly.
8. **Do NOT forget event.stopPropagation() on nested buttons.** The fork list cards and checkpoint entries have multiple clickable elements inside them.
9. **Do NOT load comparison data until the user clicks "Compare".** Comparison data can be large — load on demand, not eagerly.
10. **Do NOT forget to sanitize user content.** Fork names, whisper content, and any user-provided text must be HTML-escaped before rendering. Use Svelte template syntax (not `{@html}`) for all user content.
11. **Fork create requires loading game state.** The `create_fork()` persistence function needs the full `GameState` as its first argument. The API endpoint must load the latest checkpoint to get this state.
12. **Character sheet data may not exist.** Not all sessions will have character sheets initialized. The endpoint and component must handle the case where `character_sheets` is empty or the specific character is not found (return 404).
13. **Story Threads and Whisper History derive from gameState.** These features do NOT need separate REST endpoints — they read from the WebSocket-streamed `$gameState` store. Only Fork and Checkpoint features need new REST endpoints because they involve loading different states from disk.

### Development Workflow

```bash
# Terminal 1: Backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
# Opens http://localhost:5173

# Navigate to http://localhost:5173/game/{sessionId}
# The game page should show sidebar with all new panels
```

For visual verification, use the chrome-devtools MCP:
```
navigate_page -> http://localhost:5173/game/{sessionId}
take_screenshot -> verify sidebar panels render correctly
take_snapshot -> inspect accessibility tree for ARIA attributes
```

### References

- [Source: app.py:845-877 — `render_human_whisper_input()` — Whisper input UI]
- [Source: app.py:1071-1143 — `render_callback_timeline_html()` — Callback timeline rendering]
- [Source: app.py:1146-1360 — `render_story_threads()` — Story Threads panel]
- [Source: app.py:1364-1447 — `render_whisper_history_html/render_whisper_history()` — Whisper history]
- [Source: app.py:4943-5019 — `render_character_sheet_modal()` — Character sheet modal]
- [Source: app.py:5026-5230 — Checkpoint browser (render_checkpoint_entry_html, handle_checkpoint_restore, render_checkpoint_preview, render_restore_confirmation, render_checkpoint_browser)]
- [Source: app.py:7374-7492 — `render_comparison_view()` — Fork comparison view]
- [Source: app.py:7495-7689 — `render_fork_controls()` — Fork management sidebar]
- [Source: models.py:389-434 — `Whisper` model]
- [Source: models.py:522-600 — `NarrativeElement`, `NarrativeElementStore` models]
- [Source: models.py:894-977 — `CallbackEntry`, `CallbackLog` models]
- [Source: models.py:1023-1089 — `ForkMetadata`, `ForkRegistry` models]
- [Source: models.py:1120-1185 — `ComparisonTurn`, `ComparisonTimeline`, `ComparisonData` models]
- [Source: models.py:1570-1763 — `CharacterSheet` model (full D&D 5e sheet)]
- [Source: persistence.py:487-525 — `list_checkpoints()`, `get_latest_checkpoint()`]
- [Source: persistence.py:532-547 — `CheckpointInfo` model]
- [Source: persistence.py:606-680 — `list_checkpoint_info()`, `get_checkpoint_preview()`]
- [Source: persistence.py:1306-1655 — Fork operations (create, list, rename, delete, promote)]
- [Source: persistence.py:1982 — `build_comparison_data()`]
- [Source: api/routes.py — Existing endpoint patterns for validation, error handling]
- [Source: api/schemas.py — Existing schema patterns]
- [Source: frontend/src/lib/api.ts — Existing API client patterns]
- [Source: frontend/src/lib/types.ts — Existing TypeScript type patterns]
- [Source: frontend/src/lib/components/Sidebar.svelte — Current sidebar structure with Story Threads placeholder]
- [Source: frontend/src/lib/components/ConfirmDialog.svelte — Reusable confirmation dialog]
- [Source: frontend/src/lib/components/SettingsModal.svelte — Modal overlay pattern]
- [Source: frontend/src/routes/game/[sessionId]/+page.svelte — Game page structure]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- Fixed Ruff I001 (import sort) in tests/test_api.py via `ruff check --fix`
- Fixed Svelte `{@const}` invalid placement in StoryThreadsPanel.svelte (moved from inside `<div>` to inside `{#if}` block)
- Fixed TypeScript type casting error in ForkPanel.svelte (`$gameState as Record<string, unknown>` replaced with `$gameState?.active_fork_id`)
- Removed unused CSS selector `.story-threads-placeholder` from Sidebar.svelte

### Completion Notes List

- All 15 tasks implemented across 5 feature areas (Fork Management, Whisper System, Character Sheet, Story Threads, Checkpoint Browser)
- 12 REST API endpoints added to api/routes.py with corresponding Pydantic schemas
- 6 new Svelte 5 components created (ForkPanel, ForkComparison, WhisperPanel, CharacterSheetModal, StoryThreadsPanel, CheckpointBrowser)
- WebSocket whisper command support added (engine.submit_whisper + ws handler routing)
- UiState store extended with comparisonForkId and characterSheetName for cross-component communication
- CharacterCard "Sheet" button opens modal via uiState store
- ForkComparison overlay replaces NarrativePanel when active
- 29 new Python API tests (16 fork + 8 checkpoint + 5 character sheet)
- All 282 Python tests pass (ruff clean)
- Frontend: 0 errors, build succeeds, only pre-existing warnings remain

### File List

**Python (Modified):**
- api/routes.py — 12 new endpoints (fork CRUD, checkpoint list/preview/restore, character sheet)
- api/schemas.py — 16 new Pydantic request/response schemas
- api/engine.py — Added submit_whisper() method
- api/websocket.py — Added whisper command to known commands and routing
- tests/test_api.py — 29 new tests (TestForkEndpoints, TestCheckpointEndpoints, TestCharacterSheetEndpoint)

**Frontend (Created):**
- frontend/src/lib/components/ForkPanel.svelte
- frontend/src/lib/components/ForkComparison.svelte
- frontend/src/lib/components/WhisperPanel.svelte
- frontend/src/lib/components/CharacterSheetModal.svelte
- frontend/src/lib/components/StoryThreadsPanel.svelte
- frontend/src/lib/components/CheckpointBrowser.svelte

**Frontend (Modified):**
- frontend/src/lib/types.ts — 20+ new TypeScript interfaces, GameState extensions
- frontend/src/lib/api.ts — 12 new API client functions
- frontend/src/lib/stores/uiStore.ts — Added characterSheetName, comparisonForkId fields
- frontend/src/lib/components/Sidebar.svelte — Integrated all new panels, store-based comparison
- frontend/src/lib/components/CharacterCard.svelte — Added "Sheet" button via uiState
- frontend/src/routes/game/[sessionId]/+page.svelte — Added ForkComparison overlay, CharacterSheetModal
