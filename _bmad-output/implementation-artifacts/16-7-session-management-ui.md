# Story 16.7: Session Management UI

Status: ready-for-dev

## Story

As a **user opening the autodungeon application**,
I want **a session management page at the home route (`/`) that lets me browse existing sessions, create new sessions, search/filter by name, resume a session by navigating to its game page, and delete sessions with confirmation**,
so that **I can manage my adventures from a single home screen without needing the legacy Streamlit session browser**.

## Acceptance Criteria (Given/When/Then)

### AC1: Session List Loads and Displays on Home Page

**Given** the user navigates to the home page (`/`)
**When** the page loads
**Then** the API endpoint `GET /api/sessions` is called to fetch all sessions
**And** a heading "Your Adventures" is displayed in Lora font, 28px, `--color-dm` color
**And** sessions are displayed as a list of cards sorted by `updated_at` descending (most recent first)
**And** while the API call is in flight, a loading skeleton or spinner is shown
**And** if the API call fails, an error message is shown with a "Retry" button

### AC2: Session Card Component

**Given** a list of sessions is returned from the API
**When** each session card renders
**Then** it displays:
  - Session title in the format "Session {RomanNumeral}" (e.g., "Session VII") in Lora font, 18px, `--text-primary`
  - Session name (user-given name or "Unnamed Adventure") in Inter 14px, `--text-secondary`
  - Last played date formatted as "MMM DD, YYYY" (e.g., "Feb 11, 2026") in Inter 13px, `--text-secondary`
  - Turn count displayed as "{N} turns" in Inter 13px, `--text-secondary`
  - Character names as a comma-separated list (truncated to first 3 with "+N more" if >3) in Inter 13px, `--text-secondary`
**And** the card has `--bg-secondary` background, `--border-radius-md` (8px) border-radius, 3px `--color-dm` left border
**And** the card has hover effect: `--bg-message` background, subtle translate or shadow shift
**And** clicking the card body navigates to `/game/{session_id}` (resume)

### AC3: Create New Session

**Given** the user is on the home page
**When** they click the "+ New Adventure" button
**Then** a session creation form appears (inline or as a simple modal/dialog)
**And** the form contains:
  - A text input for session name (placeholder: "Name your adventure...", optional)
  - A "Create" button (primary style: `--accent-warm` background)
  - A "Cancel" button (secondary style)
**When** the user clicks "Create" (with or without a name)
**Then** `POST /api/sessions` is called with `{ name: "..." }`
**And** a loading spinner shows on the Create button while the request is in flight
**And** on success, the user is navigated to `/game/{new_session_id}`
**And** on failure, an error message is shown inline

### AC4: Resume Session (Navigate to Game)

**Given** a session card is displayed with `turn_count > 0`
**When** the user clicks on the session card or its "Continue" button
**Then** the browser navigates to `/game/{session_id}`
**And** no additional API calls are made from the home page (the game page handles loading)

**Given** a session card has `turn_count === 0` (newly created, no checkpoints)
**When** the user clicks the card
**Then** the browser still navigates to `/game/{session_id}` (the game page handles the empty state)

### AC5: Delete Session with Confirmation

**Given** a session card is displayed
**When** the user clicks the delete button (trash icon) on the card
**Then** a confirmation dialog appears: "Delete this adventure? This cannot be undone."
**And** the dialog has "Delete" (danger style: `--color-error` background) and "Cancel" buttons
**When** the user clicks "Delete"
**Then** `DELETE /api/sessions/{session_id}` is called
**And** on success, the session card is removed from the list with a fade-out transition
**And** a brief success message "Adventure deleted" appears for 3 seconds
**When** the user clicks "Cancel"
**Then** the confirmation dialog closes and no deletion occurs

### AC6: Delete Session API Endpoint

**Given** the backend API in `api/routes.py`
**When** a `DELETE /api/sessions/{session_id}` request is received
**Then** the endpoint calls `persistence.delete_session(session_id)` to remove the session directory
**And** returns 204 No Content on success
**And** returns 400 for invalid session ID format
**And** returns 404 if the session does not exist

### AC7: Empty State

**Given** no sessions exist (the API returns an empty array)
**When** the home page renders
**Then** an empty state is shown with:
  - A decorative icon or illustration (using existing campfire color palette)
  - Text: "No adventures yet" in Lora font, 20px, `--text-secondary`
  - Subtitle: "Start your first adventure and let the story unfold." in Inter 14px, `--text-secondary`
  - A prominent "+ New Adventure" button (primary style)
**And** the empty state is vertically centered in the content area

### AC8: Search/Filter Sessions by Name

**Given** the user has multiple sessions
**When** they type in the search input above the session list
**Then** the session list is filtered client-side to show only sessions whose `name` or `session_id` contains the search text (case-insensitive)
**And** the search input has placeholder "Search adventures..." with a search icon
**And** if no sessions match the filter, a message "No matching adventures" is shown
**And** clearing the search input restores the full list
**And** the search input is hidden when there are 0 sessions (empty state shown instead)

### AC9: Loading States

**Given** the home page is loading sessions
**When** the API call is in flight
**Then** 3-4 skeleton card placeholders are shown (pulsing `--bg-secondary` blocks)
**And** the skeleton cards match the approximate dimensions of real session cards

**Given** a create or delete operation is in progress
**When** the API call is in flight
**Then** the triggering button shows a spinner and is disabled
**And** other interactive elements remain usable

### AC10: API Client Extension for Delete

**Given** the frontend API client in `frontend/src/lib/api.ts`
**When** the session management page needs to delete a session
**Then** a `deleteSession(sessionId: string): Promise<void>` function is exported
**And** it calls `DELETE /api/sessions/{encodeURIComponent(sessionId)}`
**And** for 204 responses (no body), the function resolves without parsing JSON

### AC11: Roman Numeral Formatting

**Given** sessions have a `session_number` field
**When** rendering the session card title
**Then** the session number is formatted as a Roman numeral (1 = "I", 4 = "IV", 9 = "IX", etc.)
**And** the formatting function is a pure utility that can be unit tested

### AC12: Responsive Layout

**Given** the session list is displayed
**When** the viewport width changes:
  - Above 1024px: session cards fill the content area with comfortable padding, max-width 800px centered
  - Between 768px and 1024px: cards use full width with reduced padding
  - Below 768px: cards stack vertically with compact padding, sidebar hidden (layout handles this)
**And** the "+ New Adventure" button and search input remain accessible at all viewport widths

## Tasks / Subtasks

- [ ] **Task 1: Add DELETE session endpoint to backend API** (AC: 6)
  - [ ] 1.1: Add `DeleteSessionResponse` or use 204 No Content convention in `api/routes.py`
  - [ ] 1.2: Add route handler:
    ```python
    @router.delete("/sessions/{session_id}", status_code=204)
    async def delete_session_endpoint(session_id: str) -> None:
        try:
            _validate_session_id(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid session ID: {session_id}")

        metadata = load_session_metadata(session_id)
        if metadata is None:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

        delete_session(session_id)
    ```
  - [ ] 1.3: Import `delete_session` from `persistence` in `api/routes.py` (already imported but unused -- verify)
  - [ ] 1.4: Add backend test for the delete endpoint (204 success, 400 invalid, 404 not found)

- [ ] **Task 2: Extend frontend API client** (AC: 10)
  - [ ] 2.1: Add `deleteSession` function to `frontend/src/lib/api.ts`:
    ```typescript
    export async function deleteSession(sessionId: string): Promise<void> {
      const response = await fetch(`${BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        const body = await response.text();
        let message: string;
        try {
          const json = JSON.parse(body);
          message = json.detail || json.message || body;
        } catch {
          message = body || response.statusText;
        }
        throw new ApiError(response.status, response.statusText, message);
      }
      // 204 No Content — no body to parse
    }
    ```
  - [ ] 2.2: Verify `getSessions` and `createSession` are already exported (they are)

- [ ] **Task 3: Create Roman numeral utility** (AC: 11)
  - [ ] 3.1: Create `frontend/src/lib/format.ts` with:
    ```typescript
    export function toRomanNumeral(num: number): string {
      const values = [1000,900,500,400,100,90,50,40,10,9,5,4,1];
      const symbols = ['M','CM','D','CD','C','XC','L','XL','X','IX','V','IV','I'];
      let result = '';
      let remaining = Math.max(1, Math.floor(num));
      for (let i = 0; i < values.length; i++) {
        while (remaining >= values[i]) {
          result += symbols[i];
          remaining -= values[i];
        }
      }
      return result;
    }

    export function formatSessionDate(isoTimestamp: string): string {
      try {
        const date = new Date(isoTimestamp);
        return date.toLocaleDateString('en-US', {
          month: 'short', day: 'numeric', year: 'numeric'
        });
      } catch {
        return 'Unknown date';
      }
    }
    ```

- [ ] **Task 4: Create SessionCard component** (AC: 2, 4)
  - [ ] 4.1: Create `frontend/src/lib/components/SessionCard.svelte`
  - [ ] 4.2: Define props:
    ```typescript
    interface Props {
      session: Session;
      onDelete: (sessionId: string) => void;
    }
    ```
  - [ ] 4.3: Render card layout:
    - Clickable card area that navigates to `/game/{session.session_id}` using `goto()`
    - Title: "Session {romanNumeral}" in Lora 18px
    - Name: session name or "Unnamed Adventure" in Inter 14px `--text-secondary`
    - Metadata row: last played date + turn count
    - Character names row (truncated at 3)
    - Delete button (trash icon, positioned top-right, stops event propagation)
  - [ ] 4.4: Add scoped CSS:
    - Card: `--bg-secondary` bg, 8px radius, 3px `--color-dm` left border
    - Hover: `--bg-message` bg, `cursor: pointer`, subtle `translateY(-1px)` shift
    - Delete button: small, transparent bg, `--text-secondary` color, `--color-error` on hover
    - Transition: `background var(--transition-fast), transform var(--transition-fast)`
  - [ ] 4.5: Import and use `toRomanNumeral` and `formatSessionDate` from `format.ts`

- [ ] **Task 5: Create ConfirmDialog component** (AC: 5)
  - [ ] 5.1: Create `frontend/src/lib/components/ConfirmDialog.svelte`
  - [ ] 5.2: Define props:
    ```typescript
    interface Props {
      open: boolean;
      title: string;
      message: string;
      confirmLabel?: string;
      confirmDanger?: boolean;
      onConfirm: () => void;
      onCancel: () => void;
    }
    ```
  - [ ] 5.3: Render modal overlay with dialog box:
    - Backdrop: `rgba(0,0,0,0.6)`, click to cancel
    - Dialog: `--bg-secondary` bg, 12px radius, max-width 400px, centered
    - Title in Inter 16px weight 600
    - Message in Inter 14px `--text-secondary`
    - Button row: Cancel (secondary), Confirm (danger style if `confirmDanger`)
    - Escape key closes dialog
  - [ ] 5.4: Add enter/exit transitions (fade backdrop, scale dialog)
  - [ ] 5.5: Add `role="dialog"`, `aria-modal="true"`, focus trap to confirm button on open

- [ ] **Task 6: Create SessionBrowser page component** (AC: 1, 3, 7, 8, 9, 12)
  - [ ] 6.1: Replace the placeholder content in `frontend/src/routes/+page.svelte` with the full session browser
  - [ ] 6.2: Import `getSessions`, `createSession`, `deleteSession` from `$lib/api`
  - [ ] 6.3: Implement state management:
    ```typescript
    let sessions = $state<Session[]>([]);
    let loading = $state(true);
    let error = $state<string | null>(null);
    let searchQuery = $state('');
    let showCreateForm = $state(false);
    let newSessionName = $state('');
    let creating = $state(false);
    let deletingId = $state<string | null>(null);
    let confirmDeleteSession = $state<Session | null>(null);
    ```
  - [ ] 6.4: Implement `loadSessions()` function called on mount:
    ```typescript
    async function loadSessions() {
      loading = true;
      error = null;
      try {
        sessions = await getSessions();
      } catch (e) {
        error = e instanceof ApiError ? e.message : 'Failed to load sessions';
      } finally {
        loading = false;
      }
    }
    ```
  - [ ] 6.5: Implement filtered sessions derived state:
    ```typescript
    let filteredSessions = $derived(
      searchQuery.trim()
        ? sessions.filter(s =>
            s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            s.session_id.includes(searchQuery)
          )
        : sessions
    );
    ```
  - [ ] 6.6: Implement `handleCreate()`:
    - Call `createSession(newSessionName)`
    - On success: navigate to `/game/{sessionId}` via `goto()`
    - On failure: show inline error
  - [ ] 6.7: Implement `handleDelete(sessionId)`:
    - Call `deleteSession(sessionId)`
    - On success: remove from `sessions` array, close dialog, show brief success toast
    - On failure: show error in dialog
  - [ ] 6.8: Render page structure:
    ```
    <div class="session-browser">
      <header>
        <h2>Your Adventures</h2>
        <button>+ New Adventure</button>
      </header>
      {#if loading}
        <SkeletonCards />
      {:else if error}
        <ErrorState />
      {:else if sessions.length === 0}
        <EmptyState />
      {:else}
        <SearchInput />
        {#each filteredSessions as session (session.session_id)}
          <SessionCard />
        {/each}
        {#if filteredSessions.length === 0}
          <p>No matching adventures</p>
        {/if}
      {/if}
    </div>
    ```
  - [ ] 6.9: Implement create form (toggle visibility):
    - Text input bound to `newSessionName`
    - Create button calls `handleCreate()`
    - Cancel button hides form
    - Enter key in input submits
  - [ ] 6.10: Implement skeleton loading cards (3-4 pulsing placeholder cards)
  - [ ] 6.11: Implement empty state (centered, with icon text and create button)
  - [ ] 6.12: Implement delete confirmation via `ConfirmDialog`

- [ ] **Task 7: Style the session browser page** (AC: 1, 2, 7, 8, 9, 12)
  - [ ] 7.1: Add scoped CSS for the page layout:
    - Content area: `max-width: var(--max-content-width)`, centered with auto margins
    - Header: flex row with title left and button right
    - Session list: flex column with `--space-md` gap
  - [ ] 7.2: Style the search input:
    - `--bg-secondary` background, `--text-primary` text color
    - `--border-radius-sm` border radius, `--space-sm` padding
    - Search icon (inline SVG or CSS) on the left
    - Focus: `--accent-warm` outline
  - [ ] 7.3: Style the create form:
    - Slide-down reveal animation (max-height transition)
    - Input and buttons in a row or stacked on mobile
  - [ ] 7.4: Style skeleton cards:
    - `@keyframes pulse` animation (opacity 0.3 -> 0.7)
    - Match approximate card dimensions
  - [ ] 7.5: Style empty state:
    - Centered vertically in content area
    - Lora font for heading, Inter for body
    - Generous spacing (`--space-2xl`)
  - [ ] 7.6: Add responsive breakpoints:
    - 1024px+: max-width 800px, comfortable padding
    - 768-1024px: full width, reduced padding
    - <768px: compact cards, stacked layout
  - [ ] 7.7: Style success/error toasts (brief inline messages, 3-second auto-dismiss)

- [ ] **Task 8: Handle navigation from sidebar back to home** (AC: 4)
  - [ ] 8.1: Add an "Adventures" or home link in the sidebar header area (`+layout.svelte`):
    - The `app-title` "autodungeon" text in the sidebar header should be an `<a href="/">` link
    - Styled the same as current (Lora 20px, `--color-dm`), no underline
    - Hover: subtle color shift
  - [ ] 8.2: This provides navigation from game view back to the session browser

- [ ] **Task 9: Verify integration and visual fidelity** (AC: all)
  - [ ] 9.1: Start backend: `uvicorn api.main:app --reload --port 8000`
  - [ ] 9.2: Start frontend: `cd frontend && npm run dev`
  - [ ] 9.3: Navigate to `http://localhost:5173/`
  - [ ] 9.4: Verify empty state renders correctly when no sessions exist
  - [ ] 9.5: Create a session via the UI, verify navigation to `/game/{id}`
  - [ ] 9.6: Navigate back to `/`, verify the new session appears in the list
  - [ ] 9.7: Verify search/filter works (type in search, sessions filter)
  - [ ] 9.8: Verify delete flow (click trash, confirmation dialog, confirm, session removed)
  - [ ] 9.9: Use chrome-devtools MCP to take screenshots at various viewports:
    - Desktop (1440x900): full session browser with cards
    - Small desktop (1024x768): compressed layout
    - Mobile (375x812): stacked compact layout
  - [ ] 9.10: Run `cd frontend && npm run check` -- TypeScript passes
  - [ ] 9.11: Run `cd frontend && npm run build` -- production build succeeds

- [ ] **Task 10: Verify no Python backend regressions** (AC: 6)
  - [ ] 10.1: Run `python -m ruff check .` from project root -- no new violations
  - [ ] 10.2: Run `python -m pytest` from project root -- no regressions from the new DELETE endpoint
  - [ ] 10.3: Verify `uvicorn api.main:app` -- no import errors or startup failures

## Dev Notes

### Architecture Context

This story builds the **session management home page** for the autodungeon SvelteKit frontend. It replaces the Streamlit `render_session_browser()` function (app.py:9040-9139) and its supporting functions: `render_session_card_html()`, `handle_session_continue()`, `handle_new_session_click()`, `handle_back_to_sessions_click()`, `format_session_date()`, and the delete confirmation flow.

Unlike the game page (`/game/[sessionId]`) which uses WebSocket for real-time updates, the session browser is a REST-only page. It uses standard HTTP requests to list, create, and delete sessions. No WebSocket connection is needed on the home page.

### Component Hierarchy

```
+page.svelte (/)
  ├── Header ("Your Adventures" + "+ New Adventure" button)
  ├── SearchInput (when sessions exist)
  ├── CreateSessionForm (toggleable)
  ├── {#each} SessionCard.svelte
  │     ├── Session title (Roman numeral)
  │     ├── Session name
  │     ├── Metadata (date, turns, characters)
  │     └── Delete button (trash icon)
  ├── ConfirmDialog.svelte (for delete confirmation)
  ├── EmptyState (when no sessions)
  └── SkeletonCards (while loading)
```

### Backend: Missing DELETE Endpoint

The Streamlit app calls `persistence.delete_session(session_id)` directly. The REST API in `api/routes.py` does not currently have a DELETE endpoint for sessions. This story must add one. The `delete_session` function from `persistence.py` already exists and handles removing the entire session directory. It is already imported in `routes.py` (via the `persistence` import block -- verify the exact import name; it may need to be added to the import list).

The endpoint follows the same validation pattern as `get_session`:
1. Validate session ID format (`_validate_session_id`)
2. Check session exists (`load_session_metadata`)
3. Delete (`delete_session`)
4. Return 204 No Content

### Frontend: API Client Delete

The existing `request<T>()` helper in `api.ts` always calls `response.json()`. For 204 No Content responses, there is no body to parse. The `deleteSession` function must handle this differently -- either by using `fetch` directly (bypassing the `request` helper) or by checking the status code before parsing. The simplest approach is a standalone function that uses `fetch` directly for the DELETE call.

### Roman Numeral Formatting

The Streamlit app uses `int_to_roman()` (app.py:662) for session card titles. This needs to be ported to TypeScript. The algorithm is standard: iterate through value/symbol pairs from largest to smallest, subtracting values and appending symbols.

### Session Card Click Navigation

Session cards should use `goto()` from `$app/navigation` for SPA navigation. The delete button inside the card must call `event.stopPropagation()` to prevent the card click from also firing.

### Search/Filter

Search is client-side only. The full session list is fetched once on page load, and filtering is done via a `$derived` value. This is appropriate because the number of sessions is expected to be small (tens, not thousands). If session count grows, server-side search could be added to the API later.

### Create Session Flow

The Streamlit app has a complex flow: New Adventure -> Module Selection -> Party Setup -> Game. For this story, the SvelteKit create flow is simplified:
1. User clicks "+ New Adventure"
2. User enters an optional name
3. Session is created via API
4. User is navigated to `/game/{sessionId}`

Module selection and party setup will be handled in Story 16-9 (Character Creation & Library) or as part of the game page experience. The current story focuses on the session browser and basic create/resume/delete.

### Sidebar Navigation

The `app-title` "autodungeon" text in the sidebar header (`+layout.svelte`) should be converted from an `<h1>` to an `<a href="/">` link so users can navigate back to the session browser from any game page. The link should be styled identically to the current heading.

### Date Formatting

The Streamlit `format_session_date()` uses Python's `strftime("%b %d, %Y")`. In the SvelteKit frontend, use JavaScript's `Date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })` for equivalent output. Dates come from the API as ISO strings (e.g., `"2026-02-11T14:35:22Z"`).

### Confirmation Dialog

Rather than using `window.confirm()` (which breaks the campfire aesthetic), implement a custom `ConfirmDialog` component. This component is reusable and will be needed again in later stories (fork deletion, character deletion, etc.). Keep it generic with configurable title, message, and button labels.

### Loading Skeletons

Skeleton loading cards provide better perceived performance than a spinner. Create 3-4 placeholder cards with pulsing animation that approximate the dimensions of real session cards. Use CSS `@keyframes` for the pulse effect.

### Svelte 5 Patterns Used

| Pattern | Usage |
|---------|-------|
| `$state()` | Local reactive state (sessions, loading, error, searchQuery, etc.) |
| `$derived()` | Computed filtered sessions based on search query |
| `$effect()` | Load sessions on mount, auto-dismiss toasts |
| `$props()` | Component props (SessionCard, ConfirmDialog) |
| `{#if}` | Conditional rendering (loading, empty, error states) |
| `{#each ... (key)}` | Keyed iteration over session cards |
| `class:name={condition}` | Dynamic CSS classes (hover, deleting) |
| `transition:fade` | Card removal animation |
| `transition:slide` | Create form reveal |
| `onclick` | Button click handlers |
| `bind:value` | Two-way binding for text inputs |
| `goto()` | Programmatic navigation |

### Existing Code Reference (Streamlit -> SvelteKit Port)

| Streamlit (app.py) | SvelteKit | What to Port |
|---------------------|-----------|-------------|
| `render_session_browser()` (app.py:9040) | `+page.svelte` | Session list, empty state, action buttons |
| `render_session_card_html()` (app.py:8021) | `SessionCard.svelte` | Card layout: title, name, date, turns, characters |
| `format_session_date()` (app.py:8001) | `format.ts` | ISO date -> "MMM DD, YYYY" |
| `int_to_roman()` (app.py:662) | `format.ts` | Session number -> Roman numeral |
| `handle_new_session_click()` (app.py:8921) | `+page.svelte` | Create session + navigate |
| `handle_session_continue()` (app.py:8059) | `SessionCard.svelte` | Click card -> navigate to game |
| `handle_back_to_sessions_click()` (app.py:8999) | `+layout.svelte` | Sidebar title link -> navigate home |
| `delete_session()` confirmation (app.py:9074-9087) | `ConfirmDialog.svelte` | Confirm + delete via API |

### File Structure Created/Modified by This Story

```
api/
  routes.py                              # Modified: add DELETE /api/sessions/{id} endpoint

frontend/src/
├── lib/
│   ├── api.ts                           # Modified: add deleteSession()
│   ├── format.ts                        # NEW: toRomanNumeral(), formatSessionDate()
│   └── components/
│       ├── SessionCard.svelte           # NEW: session card with metadata + delete
│       └── ConfirmDialog.svelte         # NEW: reusable confirmation dialog
└── routes/
    ├── +page.svelte                     # Modified: full session browser (replace placeholder)
    └── +layout.svelte                   # Modified: app-title becomes <a href="/"> link
```

### Common Pitfalls to Avoid

1. **Do NOT call `response.json()` on 204 No Content responses.** The delete endpoint returns no body. The `deleteSession` API function must handle this.
2. **Do NOT forget `event.stopPropagation()` on the delete button.** The delete button is inside a clickable card. Without stopping propagation, clicking delete will also navigate to the game page.
3. **Do NOT use `window.confirm()` for delete confirmation.** Use the custom `ConfirmDialog` component to maintain the campfire aesthetic.
4. **Do NOT make the search server-side.** Session count is small enough for client-side filtering. Keep it simple.
5. **Do NOT hardcode date formats.** Use `toLocaleDateString` with explicit locale and options for consistent formatting.
6. **Do NOT modify any WebSocket or game engine code.** This is a REST-only page. The sidebar renders in the layout but the session browser does not interact with the game store or WebSocket.
7. **Do NOT add module selection or party setup to this story.** Keep the create flow simple (name + create). Advanced setup flows come in later stories.
8. **Do NOT forget to handle the `$app/navigation` import.** Use `goto` from `$app/navigation` for SPA-style navigation.
9. **Do NOT use `{@html}` for session card content.** Session data is from the API and should be rendered with Svelte template syntax, not raw HTML injection.
10. **Do NOT break existing sidebar components.** The sidebar renders on every page via the layout. Ensure the sidebar gracefully handles being on the home page where there is no WebSocket connection (controls should be hidden or disabled).

### Development Workflow

```bash
# Terminal 1: Backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
# Opens http://localhost:5173

# Navigate to http://localhost:5173/ (home page)
# The session browser should render
```

For visual verification, use the chrome-devtools MCP:
```
navigate_page -> http://localhost:5173/
take_screenshot -> verify session browser layout, cards, empty state
resize_page -> verify responsive behavior (1440, 1024, 768, 375 widths)
take_snapshot -> inspect accessibility tree for ARIA attributes
```

### References

- [Source: app.py:662-688 -- `int_to_roman()` -- Roman numeral conversion]
- [Source: app.py:8001-8018 -- `format_session_date()` -- Date formatting]
- [Source: app.py:8021-8056 -- `render_session_card_html()` -- Card HTML structure]
- [Source: app.py:8059-8081 -- `handle_session_continue()` -- Resume session logic]
- [Source: app.py:8921-8996 -- `handle_new_session_click()` -- Create session logic]
- [Source: app.py:8999-9003 -- `handle_back_to_sessions_click()` -- Back to browser]
- [Source: app.py:9040-9139 -- `render_session_browser()` -- Full session browser]
- [Source: api/routes.py:43-67 -- `list_sessions()` -- GET /api/sessions]
- [Source: api/routes.py:70-95 -- `create_session()` -- POST /api/sessions]
- [Source: api/routes.py:98-130 -- `get_session()` -- GET /api/sessions/{id}]
- [Source: api/schemas.py:22-33 -- `SessionResponse` -- Session schema]
- [Source: api/schemas.py:36-47 -- `SessionCreateRequest/Response` -- Create schemas]
- [Source: persistence.py:810-820 -- `delete_session()` -- Delete session function]
- [Source: frontend/src/lib/api.ts -- REST API client (getSessions, createSession)]
- [Source: frontend/src/lib/types.ts:4-12 -- `Session` TypeScript interface]
- [Source: frontend/src/routes/+page.svelte -- Current placeholder (to replace)]
- [Source: frontend/src/routes/+layout.svelte -- Root layout (sidebar + main content)]
- [Source: frontend/src/app.css -- CSS custom properties (design tokens)]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md:814-846 -- First Session Flow]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md:885-908 -- Session Continuity Flow]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-11.md:389 -- Story 16-7 scope]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
