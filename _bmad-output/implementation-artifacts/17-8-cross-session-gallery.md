# Story 17.8: Cross-Session Gallery & Adventures Entry Point

Status: ready-for-dev

**Epic:** 17 -- AI Scene Image Generation
**Depends On:** 17-7 (Enhanced Gallery with Lightbox) -- DONE
**FRs Covered:** FR95 (cross-session switching), FR96 (adventures list entry point), FR97 (session image summary endpoint)

---

## Story

As a **user with multiple adventures**,
I want **to browse illustrations across sessions and access the gallery from the adventures list**,
So that **I can revisit campaign artwork without entering each session individually**.

---

## Acceptance Criteria

### AC1: Session Switcher Dropdown

**Given** the gallery modal header
**When** rendered
**Then** a session switcher dropdown appears showing the current session name

### AC2: Session Switcher Options

**Given** the session switcher dropdown
**When** opened
**Then** it lists all sessions that have at least one illustration, in format: "Session Name (N images)"

### AC3: Session Switcher Navigation

**Given** the session switcher dropdown
**When** a different session is selected
**Then** the gallery loads that session's images via `loadSessionImages(newSessionId)`

### AC4: Current Session Highlighted

**Given** the session switcher dropdown
**When** rendered
**Then** the current session is highlighted/pre-selected

### AC5: Session Image Summary API

**Given** the API
**When** `GET /api/sessions/images/summary` is called
**Then** it returns `[{session_id: str, session_name: str, image_count: int}]` for all sessions with images

### AC6: Adventures List Gallery Icon

**Given** the adventures list page (`+page.svelte`)
**When** rendered
**Then** each session card that has images shows a gallery icon button with small image count badge (e.g., "12 images")

### AC7: Adventures List Gallery Open

**Given** a session card on the adventures list
**When** the user clicks the gallery icon button
**Then** the gallery modal opens pre-loaded with that session's images

### AC8: Shared Gallery Component

**Given** the gallery modal component
**When** mounted
**Then** it works on both the game page and adventures list page (shared component)

### AC9: Session Switcher Cross-Page

**Given** the session switcher
**When** used from either entry point
**Then** it can navigate to any session's illustrations regardless of which page the gallery was opened from

---

## Tasks / Subtasks

- [ ] **Task 1: Add session image summary API endpoint** (AC: 5)
  - [ ] 1.1: Add `SessionImageSummaryResponse` Pydantic model to `api/schemas.py` with fields: `session_id: str`, `session_name: str`, `image_count: int`
  - [ ] 1.2: Add `GET /api/sessions/images/summary` endpoint in `api/routes.py` (sync def for threadpool execution)
  - [ ] 1.3: Endpoint scans `campaigns/` for all `session_*` directories, checks each for `images/` subdirectory containing `*.json` sidecar files, counts them
  - [ ] 1.4: Use existing `load_session_metadata()` to get session name for each session with images
  - [ ] 1.5: Return list sorted by session name alphabetically, filtered to only sessions with `image_count > 0`
  - [ ] 1.6: Write Python tests in `tests/test_api_images.py` (or add to existing image test file) for the summary endpoint

- [ ] **Task 2: Add new stores to `imageStore.ts`** (AC: 1, 3, 4)
  - [ ] 2.1: Add `gallerySessionId` writable store: `writable<string | null>(null)` -- tracks which session the gallery is currently showing
  - [ ] 2.2: Add `sessionImageSummaries` writable store: `writable<SessionImageSummary[]>([])` -- cached list of sessions with images
  - [ ] 2.3: Add `SessionImageSummary` type to `types.ts`: `{ session_id: string; session_name: string; image_count: number }`
  - [ ] 2.4: Add `loadSessionImageSummaries()` async function that calls the new API and sets the store
  - [ ] 2.5: Update `loadSessionImages()` to also set `gallerySessionId` to the session being loaded
  - [ ] 2.6: Update `resetImageStore()` to clear `gallerySessionId` and `sessionImageSummaries`
  - [ ] 2.7: Export new stores and functions from `imageStore.ts` and `stores/index.ts` barrel

- [ ] **Task 3: Add API client function** (AC: 5)
  - [ ] 3.1: Add `getSessionImageSummaries()` function to `frontend/src/lib/api.ts` that calls `GET /api/sessions/images/summary`
  - [ ] 3.2: Return type: `SessionImageSummary[]`

- [ ] **Task 4: Add session switcher to GalleryModal** (AC: 1, 2, 3, 4, 9)
  - [ ] 4.1: Import `gallerySessionId`, `sessionImageSummaries`, `loadSessionImageSummaries`, `loadSessionImages` in `GalleryModal.svelte`
  - [ ] 4.2: Add `$effect` that loads session image summaries when gallery opens (call `loadSessionImageSummaries()` once, cache in store)
  - [ ] 4.3: Add `<select>` dropdown in the gallery header between the title and action buttons
  - [ ] 4.4: Populate dropdown options from `$sessionImageSummaries`, format: `"SessionName (N images)"`
  - [ ] 4.5: Set `<select>` value to `$gallerySessionId` (pre-selects current session)
  - [ ] 4.6: On dropdown change, call `loadSessionImages(newSessionId)` -- this sets both `images` and `gallerySessionId`
  - [ ] 4.7: Close lightbox (`lightboxIndex.set(null)`) when switching sessions to avoid stale index
  - [ ] 4.8: Update "Download All" button href to use `$gallerySessionId` instead of deriving from `$images[0]`
  - [ ] 4.9: Style the dropdown to match the campfire dark theme (dark background, warm accent border, font-ui)

- [ ] **Task 5: Add gallery icon + badge to SessionCard** (AC: 6, 7)
  - [ ] 5.1: Add `imageCount` prop to `SessionCard.svelte` Props interface: `imageCount?: number`
  - [ ] 5.2: Add `onOpenGallery` callback prop: `onOpenGallery?: (sessionId: string) => void`
  - [ ] 5.3: Render gallery icon button in `card-header` (next to delete button) only when `imageCount > 0`
  - [ ] 5.4: Show image count badge text (e.g., "12") inside or next to the icon
  - [ ] 5.5: On click, call `onOpenGallery(session.session_id)` with `e.stopPropagation()` to prevent card navigation
  - [ ] 5.6: Style the gallery button and badge to match the card's existing delete button pattern (small, icon-only, hover effect)

- [ ] **Task 6: Mount GalleryModal on adventures list page** (AC: 7, 8)
  - [ ] 6.1: Import `GalleryModal` in `frontend/src/routes/+page.svelte`
  - [ ] 6.2: Import `galleryOpen`, `loadSessionImages`, `resetImageStore`, `loadSessionImageSummaries`, `sessionImageSummaries` from image stores
  - [ ] 6.3: Fetch session image summaries on mount (`loadSessionImageSummaries()`)
  - [ ] 6.4: Create lookup map from summaries: `Map<string, number>` (session_id -> image_count)
  - [ ] 6.5: Pass `imageCount={imageCounts.get(session.session_id) ?? 0}` to each `<SessionCard>`
  - [ ] 6.6: Pass `onOpenGallery` callback that calls `loadSessionImages(sessionId)` then `galleryOpen.set(true)`
  - [ ] 6.7: Add `<GalleryModal />` to the page template (after `<ConfirmDialog />`)
  - [ ] 6.8: Clean up image store on page destroy (`onDestroy` -> `resetImageStore()`)

- [ ] **Task 7: Write frontend tests** (AC: all)
  - [ ] 7.1: Add `imageStore.test.ts` tests for `gallerySessionId`, `sessionImageSummaries`, `loadSessionImageSummaries()`, and updated `resetImageStore()`
  - [ ] 7.2: Add `GalleryModal.test.ts` tests for session switcher dropdown rendering, option population, session switching behavior
  - [ ] 7.3: Add `SessionCard.test.ts` tests for gallery icon rendering when imageCount > 0, not rendering when 0, click callback
  - [ ] 7.4: Run `cd frontend && npm run test` -- no regressions
  - [ ] 7.5: Run `cd frontend && npm run check` -- no type errors

- [ ] **Task 8: Write Python API tests** (AC: 5)
  - [ ] 8.1: Test `GET /api/sessions/images/summary` returns empty list when no sessions have images
  - [ ] 8.2: Test returns correct counts when sessions have images
  - [ ] 8.3: Test excludes sessions with 0 images
  - [ ] 8.4: Test returns correct session names from metadata

- [ ] **Task 9: Visual verification** (AC: all)
  - [ ] 9.1: Open gallery on game page -- session switcher dropdown visible in header
  - [ ] 9.2: Dropdown shows current session pre-selected
  - [ ] 9.3: Switching sessions loads new images, lightbox closes if open
  - [ ] 9.4: Navigate to adventures list -- session cards with images show gallery icon + count
  - [ ] 9.5: Click gallery icon on adventures list -- gallery opens with that session's images
  - [ ] 9.6: Session switcher works from adventures list gallery
  - [ ] 9.7: "Download All" button downloads correct session's images after switching

---

## Dev Notes

### Architecture Overview

This story adds two capabilities to the existing gallery system built in Story 17-7:

1. **Session switching within the gallery** -- A dropdown in the GalleryModal header that lets the user browse any session's illustrations without leaving the gallery
2. **Adventures list entry point** -- A gallery icon on each SessionCard that opens the gallery modal pre-loaded with that session's images

The key design constraint is that `GalleryModal` must work identically on both the game page (`/game/[sessionId]`) and the adventures list page (`/`). This is already partially satisfied because the modal reads from global stores (`images`, `galleryOpen`, `lightboxIndex`) rather than accepting props.

### File-by-File Implementation Guide

#### 1. `api/schemas.py` (MODIFY)

Add one new response model at the end of the Image Generation Schemas section (after `SceneImageResponse`):

```python
class SessionImageSummaryResponse(BaseModel):
    """Lightweight summary of a session's images for gallery population."""

    session_id: str = Field(..., description="Session ID string")
    session_name: str = Field(default="", description="User-friendly session name")
    image_count: int = Field(..., ge=0, description="Number of generated images")
```

Add `SessionImageSummaryResponse` to the imports used in `routes.py`.

#### 2. `api/routes.py` (MODIFY)

Add a new endpoint after the existing `list_session_images` endpoint (around line 3037). **Use sync def** (not async) so FastAPI runs it in a threadpool, consistent with the pattern used by `list_session_images` and `list_sessions`.

```python
@router.get(
    "/sessions/images/summary",
    response_model=list[SessionImageSummaryResponse],
)
def list_session_image_summaries() -> list[SessionImageSummaryResponse]:
    """Return lightweight image count summaries for all sessions with images.

    Scans all session directories for images/ subdirectories and counts
    JSON sidecar files. Uses sync def for threadpool execution.

    Returns:
        List of session image summaries, only including sessions with images.
    """
    from persistence import CAMPAIGNS_DIR, load_session_metadata

    results: list[SessionImageSummaryResponse] = []

    if not CAMPAIGNS_DIR.exists():
        return results

    for session_dir in sorted(CAMPAIGNS_DIR.iterdir()):
        if not session_dir.is_dir() or not session_dir.name.startswith("session_"):
            continue

        images_dir = session_dir / "images"
        if not images_dir.exists():
            continue

        json_count = len(list(images_dir.glob("*.json")))
        if json_count == 0:
            continue

        session_id = session_dir.name.removeprefix("session_")
        metadata = load_session_metadata(session_id)
        session_name = metadata.name if metadata and metadata.name else f"Session {session_id}"

        results.append(
            SessionImageSummaryResponse(
                session_id=session_id,
                session_name=session_name,
                image_count=json_count,
            )
        )

    return results
```

**CRITICAL ROUTE ORDERING:** This endpoint's path `/sessions/images/summary` could conflict with the existing `/sessions/{session_id}/images` route if FastAPI tries to match `images` as a `session_id`. To prevent this, the new endpoint MUST be registered BEFORE the `/{session_id}/images` endpoints. Place it right after the `list_sessions` endpoint (around line 265) OR use a prefix that avoids ambiguity. The safest approach is to add it near the top of the sessions section (before any `{session_id}` routes) since FastAPI matches routes in registration order.

**Alternative safe approach:** If the dev agent is unsure about route ordering, an equally valid path would be `/api/image-summaries` or `/api/sessions-images-summary` to completely avoid path parameter conflicts. However, the `/sessions/images/summary` path is the approved design and WILL work correctly as long as it is defined before the `{session_id}` wildcard routes in the router.

Import the new schema at the top of `routes.py`:

```python
from api.schemas import (
    ...
    SessionImageSummaryResponse,
)
```

#### 3. `frontend/src/lib/types.ts` (MODIFY)

Add the new type after `BestSceneAccepted`:

```typescript
export interface SessionImageSummary {
  session_id: string;
  session_name: string;
  image_count: number;
}
```

#### 4. `frontend/src/lib/api.ts` (MODIFY)

Add the API client function after the existing image API functions:

```typescript
import type { ..., SessionImageSummary } from './types';

export async function getSessionImageSummaries(): Promise<SessionImageSummary[]> {
  return request<SessionImageSummary[]>('/api/sessions/images/summary');
}
```

#### 5. `frontend/src/lib/stores/imageStore.ts` (MODIFY)

Add two new stores and two new functions:

```typescript
import type { SceneImage, SessionImageSummary } from '$lib/types';
import { getSessionImages, getSessionImageSummaries } from '$lib/api';

/** Which session the gallery is currently showing (null = not set). */
export const gallerySessionId = writable<string | null>(null);

/** Cached session image summaries for session switcher dropdown. */
export const sessionImageSummaries = writable<SessionImageSummary[]>([]);
```

Update `loadSessionImages` to also set `gallerySessionId`:

```typescript
export async function loadSessionImages(sessionId: string): Promise<void> {
    try {
        const list = await getSessionImages(sessionId);
        images.set(list);
        gallerySessionId.set(sessionId);  // NEW: track which session gallery shows
    } catch (e) {
        console.error('[ImageStore] Failed to load images:', e);
    }
}
```

Add a new function for loading summaries:

```typescript
export async function loadSessionImageSummaries(): Promise<void> {
    try {
        const summaries = await getSessionImageSummaries();
        sessionImageSummaries.set(summaries);
    } catch (e) {
        console.error('[ImageStore] Failed to load image summaries:', e);
    }
}
```

Update `resetImageStore`:

```typescript
export function resetImageStore(): void {
    images.set([]);
    generatingTurns.set(new Set());
    generatingBest.set(false);
    galleryOpen.set(false);
    lightboxIndex.set(null);
    gallerySessionId.set(null);           // NEW
    sessionImageSummaries.set([]);        // NEW
}
```

#### 6. `frontend/src/lib/stores/index.ts` (MODIFY)

Add new exports to barrel:

```typescript
export {
    images,
    generatingTurns,
    generatingBest,
    galleryOpen,
    lightboxIndex,
    compareImages,
    handleImageReady,
    startGeneration,
    startBestGeneration,
    loadSessionImages,
    loadSessionImageSummaries,    // NEW
    resetImageStore,
    gallerySessionId,             // NEW
    sessionImageSummaries,        // NEW
} from './imageStore';
```

#### 7. `frontend/src/lib/components/GalleryModal.svelte` (MODIFY)

This is the core UI change. Add the session switcher dropdown to the gallery header.

**Script changes:**

```typescript
import {
    images,
    galleryOpen,
    lightboxIndex,
    gallerySessionId,
    sessionImageSummaries,
    loadSessionImageSummaries,
    loadSessionImages,
} from '$lib/stores/imageStore';
import { getDownloadAllUrl } from '$lib/api';
import GalleryGrid from './GalleryGrid.svelte';
import ImageLightbox from './ImageLightbox.svelte';

// Use gallerySessionId for Download All URL (not derived from images[0])
const downloadAllSessionId = $derived($gallerySessionId ?? '');
const hasImages = $derived($images.length > 0);

// Load summaries when gallery opens
$effect(() => {
    if ($galleryOpen) {
        loadSessionImageSummaries();
    }
});

function handleSessionSwitch(e: Event): void {
    const select = e.target as HTMLSelectElement;
    const newSessionId = select.value;
    if (newSessionId && newSessionId !== $gallerySessionId) {
        lightboxIndex.set(null); // Close lightbox when switching sessions
        loadSessionImages(newSessionId);
    }
}
```

**Template changes -- add session switcher in header:**

The session switcher `<select>` goes between the gallery title and the header actions div. Only render it when `$sessionImageSummaries.length > 1` (no need for a dropdown if there's only one session with images).

```svelte
<header class="gallery-header">
    <h3 class="gallery-title">Illustration Gallery</h3>

    {#if $sessionImageSummaries.length > 1}
        <select
            class="session-switcher"
            value={$gallerySessionId ?? ''}
            onchange={handleSessionSwitch}
            aria-label="Switch gallery session"
        >
            {#each $sessionImageSummaries as summary (summary.session_id)}
                <option value={summary.session_id}>
                    {summary.session_name} ({summary.image_count} {summary.image_count === 1 ? 'image' : 'images'})
                </option>
            {/each}
        </select>
    {/if}

    <div class="gallery-header-actions">
        <!-- Download All button uses downloadAllSessionId -->
        {#if hasImages}
            <a href={getDownloadAllUrl(downloadAllSessionId)} download ...>
                Download All
            </a>
        {:else}
            <span class="gallery-download-all-btn disabled">Download All</span>
        {/if}
        <button class="gallery-close-btn" onclick={close} ...>X</button>
    </div>
</header>
```

**CSS additions for session switcher:**

```css
.session-switcher {
    font-family: var(--font-ui);
    font-size: 13px;
    color: var(--text-primary);
    background: var(--bg-primary);
    border: 1px solid rgba(184, 168, 150, 0.3);
    border-radius: var(--border-radius-sm);
    padding: 4px 8px;
    cursor: pointer;
    max-width: 300px;
    text-overflow: ellipsis;
}

.session-switcher:focus-visible {
    outline: 2px solid var(--accent-warm);
    outline-offset: 2px;
}

.session-switcher option {
    background: var(--bg-primary);
    color: var(--text-primary);
}
```

#### 8. `frontend/src/lib/components/SessionCard.svelte` (MODIFY)

Add new props and gallery icon button.

**Script changes:**

```typescript
interface Props {
    session: Session;
    deleting?: boolean;
    onDelete: (sessionId: string) => void;
    imageCount?: number;                           // NEW
    onOpenGallery?: (sessionId: string) => void;   // NEW
}

let { session, deleting = false, onDelete, imageCount = 0, onOpenGallery }: Props = $props();
```

**Template changes -- add gallery icon button in card-header, before delete button:**

```svelte
<div class="card-header">
    <h3 class="session-title">Session {toRomanNumeral(session.session_number)}</h3>
    <div class="card-actions">
        {#if imageCount > 0 && onOpenGallery}
            <button
                class="gallery-btn"
                onclick={(e) => { e.stopPropagation(); onOpenGallery(session.session_id); }}
                aria-label="View {imageCount} illustrations for {displayName}"
                title="{imageCount} illustrations"
            >
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                    <circle cx="8.5" cy="8.5" r="1.5" />
                    <polyline points="21 15 16 10 5 21" />
                </svg>
                <span class="gallery-badge">{imageCount}</span>
            </button>
        {/if}
        <button class="delete-btn" ... >
            <!-- existing delete icon -->
        </button>
    </div>
</div>
```

**Note:** Wrap delete button and new gallery button in a `<div class="card-actions">` container for proper flex alignment. Update existing CSS from `.delete-btn` direct child of `.card-header` to be inside `.card-actions`.

**CSS additions:**

```css
.card-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
}

.gallery-btn {
    display: flex;
    align-items: center;
    gap: 2px;
    background: transparent;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 4px;
    border-radius: var(--border-radius-sm);
    transition: color var(--transition-fast), background var(--transition-fast);
    font-family: var(--font-mono);
    font-size: 11px;
}

.gallery-btn:hover {
    color: var(--accent-warm);
    background: rgba(232, 168, 73, 0.1);
}

.gallery-btn:focus-visible {
    outline: 2px solid var(--accent-warm);
    outline-offset: 2px;
}

.gallery-badge {
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--accent-warm);
}
```

#### 9. `frontend/src/routes/+page.svelte` (MODIFY)

Mount `GalleryModal` on the adventures list page and wire up the image count data.

**Script additions:**

```typescript
import GalleryModal from '$lib/components/GalleryModal.svelte';
import {
    galleryOpen,
    loadSessionImages,
    loadSessionImageSummaries,
    sessionImageSummaries,
    resetImageStore,
} from '$lib/stores/imageStore';
import type { SessionImageSummary } from '$lib/types';

// Image count lookup map, derived from session summaries
let imageCounts = $derived(
    new Map($sessionImageSummaries.map((s) => [s.session_id, s.image_count]))
);

function openGalleryForSession(sessionId: string): void {
    loadSessionImages(sessionId);
    galleryOpen.set(true);
}

// Load session image summaries on mount
onMount(() => {
    loadSessions();
    loadSessionImageSummaries();
});

onDestroy(() => {
    if (successTimer) clearTimeout(successTimer);
    resetImageStore();
});
```

**Template changes:**

Pass new props to SessionCard:

```svelte
<SessionCard
    {session}
    deleting={deletingId === session.session_id}
    onDelete={requestDelete}
    imageCount={imageCounts.get(session.session_id) ?? 0}
    onOpenGallery={openGalleryForSession}
/>
```

Add GalleryModal after the ConfirmDialog:

```svelte
<ConfirmDialog ... />
<GalleryModal />
```

### Keyboard Interaction Notes

No new keyboard shortcuts are added. Existing shortcuts work as before:
- `G` on game page: toggles gallery (unchanged)
- `ESC`: closes lightbox first, then gallery (unchanged)
- `Left/Right` in lightbox: navigate (unchanged)
- `D` in lightbox: download (unchanged)

The session switcher `<select>` is a standard HTML element that responds to native keyboard interaction (arrow keys to change option, Enter to confirm).

### Route Ordering Critical Path

The new `/sessions/images/summary` endpoint MUST be defined in `routes.py` BEFORE any endpoint with `{session_id}` path parameter. Otherwise, FastAPI will try to match `"images"` as a `session_id` value. Check the existing route order:

```
GET /sessions                        -- list_sessions (line 238)
POST /sessions                       -- create_session (line 267)
GET /sessions/images/summary         -- NEW: must be HERE, before {session_id} routes
GET /sessions/{session_id}           -- get_session (line 295)
GET /sessions/{session_id}/images    -- list_session_images (line 2989)
...
```

If the dev agent places the new endpoint after the `{session_id}` routes, the endpoint will never match and `GET /sessions/images/summary` will hit `get_session(session_id="images")` and return a 400 error.

### Data Flow

```
Adventures list page loads:
  1. loadSessions() -> sessions[] (existing)
  2. loadSessionImageSummaries() -> sessionImageSummaries[] (NEW)
  3. Build imageCounts Map from summaries
  4. Pass imageCount to each SessionCard

User clicks gallery icon on SessionCard:
  1. openGalleryForSession(sessionId) called
  2. loadSessionImages(sessionId) -> images[], gallerySessionId set
  3. galleryOpen.set(true) -> GalleryModal renders
  4. $effect in GalleryModal loads sessionImageSummaries (if not cached)
  5. Session switcher dropdown populated

User switches session in dropdown:
  1. handleSessionSwitch(e) fires
  2. lightboxIndex.set(null) clears any open lightbox
  3. loadSessionImages(newSessionId) replaces images[] and gallerySessionId
  4. GalleryGrid re-renders with new images
```

### Existing Code to Reuse (DO NOT Reinvent)

| Existing | Location | Reuse |
|----------|----------|-------|
| `loadSessionImages()` | `imageStore.ts` | Session switching -- already loads images for a session |
| `getDownloadAllUrl()` | `api.ts` | Download All button -- pass `gallerySessionId` instead of `$images[0].session_id` |
| `getImageDownloadUrl()` | `api.ts` | Per-image download in grid/lightbox -- works with any session_id |
| `load_session_metadata()` | `persistence.py` | Backend: get session names for summary endpoint |
| `CAMPAIGNS_DIR` | `persistence.py` | Backend: scan for session directories |
| `list_sessions_with_metadata()` | `persistence.py` | Pattern reference for scanning campaigns/ directory |
| `_validate_session_id()` | `persistence.py` | Pattern reference, but NOT needed for summary (we iterate dirs) |
| `galleryOpen` store | `imageStore.ts` | GalleryModal visibility -- already used by both entry points |
| `lightboxIndex` store | `imageStore.ts` | Lightbox state -- must be cleared on session switch |
| `compareImages()` | `imageStore.ts` | Shared sort comparator -- works regardless of session |
| `formatSessionDate()` | `format.ts` | Not directly needed but follows existing patterns |

### Common Pitfalls to Avoid

1. **Route parameter conflict.** `GET /sessions/images/summary` will be swallowed by `GET /sessions/{session_id}` if registered after it. FastAPI matches routes in definition order. Place the new endpoint BEFORE any `{session_id}` routes.

2. **Stale `lightboxIndex` on session switch.** When the user switches sessions via the dropdown, `images` changes but `lightboxIndex` might point to an image that no longer exists in the new set. Always call `lightboxIndex.set(null)` BEFORE calling `loadSessionImages()`.

3. **`gallerySessionId` vs `$images[0].session_id`.** The old GalleryModal derived `sessionId` from `$images[0].session_id`. This breaks when `images` is empty (no images in session). The new `gallerySessionId` store explicitly tracks the selected session, even when it has 0 images. Use `$gallerySessionId` for the Download All URL, not `$images[0].session_id`.

4. **Event propagation on SessionCard gallery button.** The gallery icon click MUST call `e.stopPropagation()`. Without it, the click propagates to the card's `onclick` handler, which calls `goto('/game/...')` and navigates away from the adventures list.

5. **Duplicate `GalleryModal` mounting.** `GalleryModal` is already mounted on the game page (`/game/[sessionId]/+page.svelte`). When adding it to the adventures list page, ensure there's no shared layout that would double-mount it. Each page mounts its own instance. Since `galleryOpen` is a global store, both instances would render simultaneously if two pages were mounted. This is not an issue because SvelteKit only mounts one page at a time.

6. **`resetImageStore()` on page destroy.** The adventures list page MUST call `resetImageStore()` in `onDestroy`. Otherwise, navigating from the adventures list (where gallery was opened) to a game page would show stale gallery state.

7. **Svelte 5 runes syntax.** All new code MUST use `$state`, `$derived`, `$effect`, `$props`. Do NOT use `$:` reactive declarations, `export let` props, or `<script context="module">`. The project is Svelte 5 with runes.

8. **`<select>` element value binding with Svelte 5.** Use `value={$gallerySessionId ?? ''}` and `onchange={handleSessionSwitch}` rather than `bind:value`. The store-backed value should be set via the handler function to coordinate with `loadSessionImages()`.

9. **SessionCard props must remain backward compatible.** The existing game page does NOT use `imageCount` or `onOpenGallery`. These props are optional (`imageCount = 0`, `onOpenGallery?: ...`). The SessionCard MUST work identically when these props are not provided.

10. **Summary endpoint performance.** The endpoint scans all session directories and counts JSON files. For a user with many sessions (e.g., 50+), this involves multiple `glob()` calls. This is acceptable for a local app. The endpoint is sync def (threadpool), so it won't block the event loop. Results are cached in the `sessionImageSummaries` store on the frontend side.

11. **Turn numbers in gallery remain 1-based.** `SceneImage.turn_number` is 0-based. The UI always shows `turn_number + 1`. This convention is unchanged by this story.

12. **Don't modify the `G` keyboard shortcut on the adventures list page.** The `G` shortcut only works on the game page (defined in `game/[sessionId]/+page.svelte`). The adventures list page does NOT add a `G` shortcut -- gallery is opened via the icon button on each session card.

### Project Structure Notes

```
api/
  schemas.py                          -- MODIFY: Add SessionImageSummaryResponse
  routes.py                           -- MODIFY: Add GET /sessions/images/summary endpoint

frontend/src/lib/
  types.ts                            -- MODIFY: Add SessionImageSummary interface
  api.ts                              -- MODIFY: Add getSessionImageSummaries()
  stores/
    imageStore.ts                     -- MODIFY: Add gallerySessionId, sessionImageSummaries, loadSessionImageSummaries()
    index.ts                          -- MODIFY: Add new exports to barrel
  components/
    GalleryModal.svelte               -- MODIFY: Add session switcher dropdown, update Download All URL
    SessionCard.svelte                -- MODIFY: Add gallery icon + badge, new props

frontend/src/routes/
  +page.svelte                        -- MODIFY: Mount GalleryModal, pass imageCount/onOpenGallery to SessionCard

tests/
  test_api_images.py                  -- MODIFY or NEW: Tests for summary endpoint

frontend/src/lib/stores/
  imageStore.test.ts                  -- MODIFY: Tests for new stores and functions
frontend/src/lib/components/
  GalleryModal.test.ts                -- MODIFY: Tests for session switcher
  SessionCard.test.ts                 -- MODIFY: Tests for gallery icon
```

No new files are created (all modifications to existing files).

### Test Strategy

**Python API tests (`tests/test_api_images.py`):**
- Test `GET /api/sessions/images/summary` with no sessions -> empty list
- Test with sessions that have images -> correct counts and names
- Test that sessions with 0 images are excluded
- Test session_name falls back to `"Session {id}"` when metadata has no name
- Mock the campaigns directory structure (use `tmp_path` fixture)

**Frontend store tests (`imageStore.test.ts`):**
- `gallerySessionId`: default null, set/get, reset clears it
- `sessionImageSummaries`: default empty array, set/get, reset clears it
- `loadSessionImages()`: sets both `images` and `gallerySessionId`
- `loadSessionImageSummaries()`: calls API and sets store
- `resetImageStore()`: clears all stores including new ones

**GalleryModal tests (`GalleryModal.test.ts`):**
- Session switcher dropdown renders when summaries have > 1 session
- Dropdown does NOT render when summaries have 0 or 1 session
- Dropdown options show "SessionName (N images)" format
- Selecting a different session calls `loadSessionImages` (mock)
- Current session is pre-selected in dropdown

**SessionCard tests (`SessionCard.test.ts`):**
- Gallery icon renders when `imageCount > 0`
- Gallery icon does NOT render when `imageCount = 0` or `imageCount` not provided
- Gallery icon shows correct count
- Clicking gallery icon calls `onOpenGallery` with session_id
- Clicking gallery icon does NOT trigger card navigation (stopPropagation)

### References

- [Source: `frontend/src/lib/components/GalleryModal.svelte` -- current gallery modal (Story 17-7)]
- [Source: `frontend/src/lib/components/GalleryGrid.svelte` -- thumbnail grid component]
- [Source: `frontend/src/lib/components/ImageLightbox.svelte` -- lightbox overlay component]
- [Source: `frontend/src/lib/stores/imageStore.ts` -- image stores: images, galleryOpen, lightboxIndex, compareImages]
- [Source: `frontend/src/lib/stores/index.ts` -- barrel exports for stores]
- [Source: `frontend/src/lib/types.ts` -- SceneImage, Session types]
- [Source: `frontend/src/lib/api.ts` -- getSessionImages, getImageDownloadUrl, getDownloadAllUrl]
- [Source: `frontend/src/routes/+page.svelte` -- adventures list page]
- [Source: `frontend/src/lib/components/SessionCard.svelte` -- session card component]
- [Source: `frontend/src/routes/game/[sessionId]/+page.svelte` -- game page with GalleryModal mount]
- [Source: `api/routes.py` -- image endpoints (lines 2989-3037), list_sessions (line 238), route ordering]
- [Source: `api/schemas.py` -- SceneImageResponse, SessionResponse schemas]
- [Source: `persistence.py` -- CAMPAIGNS_DIR, get_session_dir, list_sessions_with_metadata, load_session_metadata]
- [Source: `docs/gallery-enhancement-plan.md` -- full design doc with component architecture]
- [Source: `_bmad-output/planning-artifacts/epics-v2.1.md#Story 17.8` -- acceptance criteria]
- [Source: `_bmad-output/implementation-artifacts/17-7-enhanced-gallery-lightbox.md` -- previous story patterns and code review fixes]

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

| File | Action | Description |
|------|--------|-------------|
| `api/schemas.py` | Modified | Add `SessionImageSummaryResponse` model |
| `api/routes.py` | Modified | Add `GET /sessions/images/summary` endpoint (BEFORE `{session_id}` routes) |
| `frontend/src/lib/types.ts` | Modified | Add `SessionImageSummary` interface |
| `frontend/src/lib/api.ts` | Modified | Add `getSessionImageSummaries()` function |
| `frontend/src/lib/stores/imageStore.ts` | Modified | Add `gallerySessionId`, `sessionImageSummaries` stores; `loadSessionImageSummaries()` function; update `loadSessionImages()` and `resetImageStore()` |
| `frontend/src/lib/stores/index.ts` | Modified | Add new exports to barrel |
| `frontend/src/lib/components/GalleryModal.svelte` | Modified | Add session switcher dropdown, update Download All URL source |
| `frontend/src/lib/components/SessionCard.svelte` | Modified | Add `imageCount` and `onOpenGallery` props; gallery icon with badge |
| `frontend/src/routes/+page.svelte` | Modified | Mount GalleryModal, load image summaries, pass imageCount/onOpenGallery to SessionCard |
| `tests/test_api_images.py` | Modified/New | Python tests for session image summary endpoint |
| `frontend/src/lib/stores/imageStore.test.ts` | Modified | Tests for new stores and functions |
| `frontend/src/lib/components/GalleryModal.test.ts` | Modified | Tests for session switcher dropdown |
| `frontend/src/lib/components/SessionCard.test.ts` | Modified/New | Tests for gallery icon and badge |
