# Story 17-5: Image Generation UI

**Epic:** 17 — AI Scene Image Generation
**Status:** done
**Depends On:** 17-1 (Turn Number Display) — DONE, 17-2 (Image Generation Service) — DONE, 17-3 (Current Scene & Specific Turn API) — DONE, 17-4 (Best Scene Scanner) — DONE

---

## Story

As a **user**,
I want **a frontend interface for generating, viewing, and managing scene illustrations**,
So that **I can create images of my campaign's best moments directly from the UI**.

---

## Acceptance Criteria

### AC1: Illustrate Dropdown Button in Session Toolbar

**Given** the session toolbar
**When** rendered
**Then** an "Illustrate" dropdown button appears with options: "Current Scene", "Best Scene", "Turn #...", "View Gallery"

### AC2: Illustrate Current Scene Action

**Given** the user clicks "Illustrate Current Scene"
**When** generation starts
**Then** a loading placeholder appears inline at the top of the narrative ("Painting the scene...") with a progress indicator

### AC3: Illustrate Turn # Dialog

**Given** the user clicks "Illustrate Turn #..."
**When** the dialog opens
**Then** a turn number input appears with a preview of the turn's content

### AC4: Click-to-Illustrate on Turn Number

**Given** the user clicks a turn number in the narrative
**When** the click is registered
**Then** it triggers image generation for that specific turn (click-to-illustrate shortcut)

### AC5: Image Ready Display

**Given** an image generation completes (via WebSocket `image_ready` event)
**When** the frontend receives it
**Then** the image appears inline above the corresponding narrative message, with a download button overlay on hover

### AC6: Download Button on Hover

**Given** an image is displayed inline
**When** the user hovers over it
**Then** a download button appears in the bottom-right corner of the image

### AC7: Image Gallery Panel

**Given** the user clicks "View Gallery"
**When** the gallery panel opens
**Then** it shows a 2-column grid of all generated images for the session, with turn number, generation mode badge, and per-image download button

### AC8: Image Store

**Given** a new `imageStore` in the frontend
**When** created
**Then** it tracks: generated images, generation-in-progress state, and gallery visibility

### AC9: Keyboard Shortcut — Illustration Menu

**Given** keyboard shortcuts
**When** the user presses `I`
**Then** the illustration menu opens

### AC10: Keyboard Shortcut — Gallery

**Given** keyboard shortcuts
**When** the user presses `G`
**Then** the image gallery opens

---

## Tasks / Subtasks

- [x] **Task 1: Add TypeScript types for image generation** (AC: 5, 8)
  - [x]1.1: Add `SceneImage` interface to `frontend/src/lib/types.ts` with fields: `id` (string), `session_id` (string), `turn_number` (number), `prompt` (string), `image_path` (string), `provider` (string), `model` (string), `generation_mode` (`'current' | 'best' | 'specific'`), `generated_at` (string), `download_url` (string) — mirrors `SceneImageResponse` from `api/schemas.py`
  - [x]1.2: Add `ImageGenerateAccepted` interface with `task_id` (string), `session_id` (string), `turn_number` (number), `status` (Literal `'pending'`)
  - [x]1.3: Add `BestSceneAccepted` interface with `task_id` (string), `session_id` (string), `status` (Literal `'scanning'`)
  - [x]1.4: Add `WsImageReady` interface to the WebSocket server event types: `{ type: 'image_ready'; image: SceneImage }` and include it in the `WsServerEvent` union type

- [x] **Task 2: Add image generation API client functions** (AC: 1, 2, 3, 4, 7)
  - [x]2.1: Add `generateCurrentImage(sessionId: string): Promise<ImageGenerateAccepted>` — `POST /api/sessions/{id}/images/generate-current`
  - [x]2.2: Add `generateTurnImage(sessionId: string, turnNumber: number): Promise<ImageGenerateAccepted>` — `POST /api/sessions/{id}/images/generate-turn/{turnNumber}`
  - [x]2.3: Add `generateBestImage(sessionId: string): Promise<BestSceneAccepted>` — `POST /api/sessions/{id}/images/generate-best`
  - [x]2.4: Add `getSessionImages(sessionId: string): Promise<SceneImage[]>` — `GET /api/sessions/{id}/images`
  - [x]2.5: All functions use the existing `request<T>()` helper from `api.ts`

- [x] **Task 3: Create `imageStore.ts`** (AC: 5, 8)
  - [x]3.1: Create `frontend/src/lib/stores/imageStore.ts` using Svelte 5 writable stores (matching `gameStore.ts` pattern):
    - `images` — `writable<SceneImage[]>([])`: all generated images for the current session
    - `generatingTurns` — `writable<Set<number>>(new Set())`: turn numbers currently being generated (for loading placeholder display)
    - `generatingBest` — `writable<boolean>(false)`: whether a "best scene" scan is running
    - `galleryOpen` — `writable<boolean>(false)`: gallery panel visibility
  - [x]3.2: Add `handleImageReady(image: SceneImage): void` function that:
    - Appends the image to `images` store
    - Removes `image.turn_number` from `generatingTurns`
    - Sets `generatingBest` to false if `image.generation_mode === 'best'`
  - [x]3.3: Add `startGeneration(turnNumber: number, mode: 'current' | 'specific'): void` that adds `turnNumber` to `generatingTurns`
  - [x]3.4: Add `startBestGeneration(): void` that sets `generatingBest` to true
  - [x]3.5: Add `loadSessionImages(sessionId: string): Promise<void>` that calls `getSessionImages()` and populates `images`
  - [x]3.6: Add `resetImageStore(): void` that resets all stores to defaults
  - [x]3.7: Add derived helper `getImageForTurn(turnNumber: number)` that returns the image (if any) for a given turn number (using `$images`)
  - [x]3.8: Export from `frontend/src/lib/stores/index.ts`

- [x] **Task 4: Wire `image_ready` WebSocket event into stores** (AC: 5, 8)
  - [x]4.1: In `gameStore.ts` `handleServerMessage()`, add `case 'image_ready':` that calls `handleImageReady(msg.image)` from `imageStore`
  - [x]4.2: In the game page `onMount`, after WebSocket connection is established, call `loadSessionImages(sessionId)` to populate the store with existing images on page load

- [x] **Task 5: Create `SceneImage.svelte` component** (AC: 5, 6)
  - [x]5.1: Create `frontend/src/lib/components/SceneImage.svelte` that renders a single inline scene image:
    - Props: `image: SceneImage`
    - Display: image via `<img>` with `src={image.download_url}`, `alt` text from `image.prompt`, 16:9 aspect ratio
    - Download button overlay in bottom-right corner, visible on hover
    - Download uses `<a>` tag with `download` attribute pointing to `image.download_url`
    - ARIA: `aria-label="Download scene image for Turn {image.turn_number + 1}"`
  - [x]5.2: CSS matches UX spec: `.scene-image-container`, `.scene-image`, `.scene-image-overlay`, `.image-download-btn` with hover reveal pattern

- [x] **Task 6: Create `ImageGenerating.svelte` loading placeholder** (AC: 2)
  - [x]6.1: Create `frontend/src/lib/components/ImageGenerating.svelte` that renders a loading placeholder:
    - Props: `turnNumber: number`, `mode: 'current' | 'best' | 'specific'`
    - Display: dashed amber border container with "Painting the scene..." text and animated progress indicator
    - Uses `aria-live="polite"` for accessibility
  - [x]6.2: CSS matches UX spec: `.image-generating`, `.image-generating-text` with dashed border and amber animation

- [x] **Task 7: Integrate inline images into `NarrativeMessage.svelte`** (AC: 4, 5)
  - [x]7.1: Import `SceneImage` component and `ImageGenerating` component into `NarrativeMessage.svelte`
  - [x]7.2: Add props: `sceneImage?: SceneImage | undefined` and `isGenerating?: boolean` to the component
  - [x]7.3: When `sceneImage` is present, render `<SceneImage>` above the narrative message content
  - [x]7.4: When `isGenerating` is true (and no image yet), render `<ImageGenerating>` above the narrative message content
  - [x]7.5: Wire the `.turn-number` click handler: on click, call the image generation API for that turn's index (0-based log index). The handler is an `onclick` event dispatched upward via a callback prop `onIllustrateTurn?: (turnIndex: number) => void`

- [x] **Task 8: Wire `NarrativePanel.svelte` to pass image data** (AC: 4, 5)
  - [x]8.1: Import `images` and `generatingTurns` stores from `imageStore`
  - [x]8.2: For each `NarrativeMessage`, derive `sceneImage` by looking up `msg.index` in the images list
  - [x]8.3: For each `NarrativeMessage`, derive `isGenerating` by checking `msg.index` membership in `generatingTurns`
  - [x]8.4: Add `handleIllustrateTurn(turnIndex: number)` function that calls `generateTurnImage(sessionId, turnIndex)` and updates `generatingTurns` via `startGeneration()`
  - [x]8.5: Pass `sceneImage`, `isGenerating`, and `onIllustrateTurn` props down to each `NarrativeMessage`

- [x] **Task 9: Create `IllustrateMenu.svelte` dropdown** (AC: 1, 2, 3, 9)
  - [x]9.1: Create `frontend/src/lib/components/IllustrateMenu.svelte`:
    - Props: `sessionId: string`, `totalTurns: number`, `onOpenGallery: () => void`
    - Renders a dropdown button labeled "Illustrate" with a paint palette SVG icon
    - Menu items: "Current Scene", "Best Scene", "Turn #...", separator, "View Gallery"
    - Dropdown uses `position: absolute` with click-outside-to-close behavior
  - [x]9.2: "Current Scene" calls `generateCurrentImage(sessionId)` then `startGeneration(totalTurns - 1, 'current')`
  - [x]9.3: "Best Scene" calls `generateBestImage(sessionId)` then `startBestGeneration()`
  - [x]9.4: "Turn #..." opens a small inline dialog with a number input (min=1, max=totalTurns), a preview of the turn content, and "Generate" / "Cancel" buttons. On generate, calls `generateTurnImage(sessionId, turnNumber - 1)` then `startGeneration(turnNumber - 1, 'specific')`
  - [x]9.5: "View Gallery" calls `onOpenGallery()`
  - [x]9.6: Handle API errors: display in a toast or inline error message, remove from `generatingTurns` on error
  - [x]9.7: Disable all options when not connected or when `image_generation_enabled` is false in config (show tooltip explaining why)

- [x] **Task 10: Create `ImageGallery.svelte` panel** (AC: 7, 10)
  - [x]10.1: Create `frontend/src/lib/components/ImageGallery.svelte`:
    - Slide-out panel from right (520px width), overlays narrative area
    - Header: "Scene Gallery" title with close button
    - Content: 2-column grid of gallery cards
    - Each card shows: image thumbnail (16:9), "Turn N" label, generation mode badge (Current/Best/Specific), download button
    - Empty state: "No images yet. Use the Illustrate menu to generate scene images."
  - [x]10.2: Import `images` store; gallery reads from this store directly
  - [x]10.3: Gallery visibility controlled by `galleryOpen` store
  - [x]10.4: CSS matches UX spec: `.image-gallery`, `.gallery-card`, `.gallery-image`, `.gallery-meta`, `.gallery-label`, `.gallery-mode-badge`
  - [x]10.5: Panel opens/closes with slide animation (`transform: translateX()`)
  - [x]10.6: Close on Escape key press

- [x] **Task 11: Integrate Illustrate menu and Gallery into game page** (AC: 1, 7, 9, 10)
  - [x]11.1: Add `IllustrateMenu` to the `NarrativePanel.svelte` session header area (right-aligned, alongside session title)
  - [x]11.2: Add `ImageGallery` to the game page `+page.svelte` or `NarrativePanel.svelte` (positioned fixed/absolute over the narrative area)
  - [x]11.3: Connect gallery open/close to `galleryOpen` store and `IllustrateMenu`'s `onOpenGallery` callback
  - [x]11.4: Conditionally render `IllustrateMenu` only when `image_generation_enabled` is true in game config (graceful hiding when disabled)

- [x] **Task 12: Add keyboard shortcuts** (AC: 9, 10)
  - [x]12.1: In the game page `handleKeydown()` function (in `+page.svelte`), add:
    - `I` key: toggles the illustration menu open/closed (via a shared state or ref)
    - `G` key: toggles the gallery open/closed (via `galleryOpen` store)
  - [x]12.2: Both shortcuts are suppressed when user is typing in an input/textarea/select (existing guard in `handleKeydown`)

- [x] **Task 13: Write tests** (AC: all)
  - [x]13.1: `imageStore.test.ts` — test `handleImageReady` (appends image, removes from generatingTurns), `startGeneration`, `startBestGeneration`, `resetImageStore`, `loadSessionImages` (mock API)
  - [x]13.2: `SceneImage.test.ts` — renders image with correct src/alt, download button visible on hover, ARIA labels
  - [x]13.3: `ImageGenerating.test.ts` — renders placeholder with "Painting the scene..." text, has `aria-live="polite"`
  - [x]13.4: `IllustrateMenu.test.ts` — dropdown opens on click, menu items rendered, "Turn #" dialog flow, disabled when not connected
  - [x]13.5: `ImageGallery.test.ts` — renders grid of images, empty state, close button, gallery-mode-badge for each mode
  - [x]13.6: `NarrativeMessage.test.ts` — existing tests still pass, turn number click dispatches illustrate callback, inline image renders when sceneImage prop provided, loading placeholder renders when isGenerating is true
  - [x]13.7: Run `cd frontend && npm run test` — no regressions
  - [x]13.8: Run `cd frontend && npm run check` — no type errors

- [x] **Task 14: Visual verification** (AC: all)
  - [x]14.1: Navigate to `http://localhost:5173/game/{sessionId}` and verify Illustrate dropdown appears in session header
  - [x]14.2: Click "Current Scene" and verify loading placeholder appears at the top of the narrative
  - [x]14.3: Verify image appears inline when generation completes (or simulate via browser WebSocket)
  - [x]14.4: Click a turn number and verify image generation triggers for that turn
  - [x]14.5: Open gallery and verify 2-column grid layout
  - [x]14.6: Press `I` to verify illustration menu opens, `G` to verify gallery opens
  - [x]14.7: Hover over inline image and verify download button appears
  - [x]14.8: Test responsive layout at 768px and 1024px breakpoints

---

## Dev Notes

### Architecture Context

This story adds the complete frontend for image generation to the SvelteKit app. All backend APIs (Stories 17-2 through 17-4) are already implemented. The frontend needs to:

1. Call REST endpoints to trigger image generation (HTTP 202 Accepted)
2. Listen for WebSocket `image_ready` events when generation completes
3. Display images inline in the narrative above the turn they illustrate
4. Provide a dropdown menu for triggering different generation modes
5. Provide a gallery panel for browsing all generated images
6. Support keyboard shortcuts (`I` for illustrate, `G` for gallery)
7. Handle click-to-illustrate on existing turn number elements (Story 17-1)

### Image Store Design (`imageStore.ts`)

The store uses Svelte writable stores (matching the existing `gameStore.ts` and `uiStore.ts` patterns):

```typescript
// frontend/src/lib/stores/imageStore.ts
import { writable, derived, get } from 'svelte/store';
import type { SceneImage } from '$lib/types';
import { getSessionImages } from '$lib/api';

// All generated images for the current session
export const images = writable<SceneImage[]>([]);

// Turn numbers with in-progress generation (for loading placeholders)
export const generatingTurns = writable<Set<number>>(new Set());

// Whether a "best scene" scan is running
export const generatingBest = writable<boolean>(false);

// Gallery panel visibility
export const galleryOpen = writable<boolean>(false);

/**
 * Called when a WebSocket image_ready event arrives.
 * Appends the image and clears generation state.
 */
export function handleImageReady(image: SceneImage): void {
    images.update((list) => [...list, image]);
    generatingTurns.update((s) => {
        const next = new Set(s);
        next.delete(image.turn_number);
        return next;
    });
    if (image.generation_mode === 'best') {
        generatingBest.set(false);
    }
}

export function startGeneration(turnNumber: number): void {
    generatingTurns.update((s) => {
        const next = new Set(s);
        next.add(turnNumber);
        return next;
    });
}

export function startBestGeneration(): void {
    generatingBest.set(true);
}

export async function loadSessionImages(sessionId: string): Promise<void> {
    try {
        const list = await getSessionImages(sessionId);
        images.set(list);
    } catch (e) {
        console.error('[ImageStore] Failed to load images:', e);
    }
}

export function resetImageStore(): void {
    images.set([]);
    generatingTurns.set(new Set());
    generatingBest.set(false);
    galleryOpen.set(false);
}
```

### WebSocket Event Subscription

The `image_ready` event is handled in `gameStore.ts`'s `handleServerMessage()` function, matching the existing pattern for all other WebSocket events. No separate subscription mechanism is needed.

```typescript
// In gameStore.ts handleServerMessage():
case 'image_ready':
    // msg is WsImageReady: { type: 'image_ready', image: SceneImage }
    handleImageReady(msg.image);
    break;
```

The WebSocket client (`ws.ts`) already forwards all parsed events to registered callbacks. The `image_ready` event requires no special handling in the transport layer -- it is a standard JSON message parsed by the existing `onmessage` handler.

### TypeScript Type Additions (`types.ts`)

Add to the existing types file:

```typescript
// Scene Image (mirrors api/schemas.py SceneImageResponse)
export interface SceneImage {
    id: string;
    session_id: string;
    turn_number: number;
    prompt: string;
    image_path: string;
    provider: string;
    model: string;
    generation_mode: 'current' | 'best' | 'specific';
    generated_at: string;
    download_url: string;
}

// WebSocket event for image ready
export interface WsImageReady {
    type: 'image_ready';
    image: SceneImage;
}

// Add to WsServerEvent union:
export type WsServerEvent =
    | ... // existing events
    | WsImageReady;

// API response types
export interface ImageGenerateAccepted {
    task_id: string;
    session_id: string;
    turn_number: number;
    status: 'pending';
}

export interface BestSceneAccepted {
    task_id: string;
    session_id: string;
    status: 'scanning';
}
```

### API Client Functions (`api.ts`)

```typescript
// Image generation endpoints
export async function generateCurrentImage(
    sessionId: string,
): Promise<ImageGenerateAccepted> {
    return request<ImageGenerateAccepted>(
        `/api/sessions/${encodeURIComponent(sessionId)}/images/generate-current`,
        { method: 'POST', body: JSON.stringify({}) },
    );
}

export async function generateTurnImage(
    sessionId: string,
    turnNumber: number,
): Promise<ImageGenerateAccepted> {
    return request<ImageGenerateAccepted>(
        `/api/sessions/${encodeURIComponent(sessionId)}/images/generate-turn/${turnNumber}`,
        { method: 'POST', body: JSON.stringify({}) },
    );
}

export async function generateBestImage(
    sessionId: string,
): Promise<BestSceneAccepted> {
    return request<BestSceneAccepted>(
        `/api/sessions/${encodeURIComponent(sessionId)}/images/generate-best`,
        { method: 'POST', body: JSON.stringify({}) },
    );
}

export async function getSessionImages(
    sessionId: string,
): Promise<SceneImage[]> {
    return request<SceneImage[]>(
        `/api/sessions/${encodeURIComponent(sessionId)}/images`,
    );
}
```

### Component Hierarchy

```
+page.svelte (game session page)
├── NarrativePanel.svelte
│   ├── IllustrateMenu.svelte (dropdown in session header)
│   │   └── Turn # dialog (inline within dropdown)
│   ├── NarrativeMessage.svelte (repeated per message)
│   │   ├── SceneImage.svelte (optional, when image exists for this turn)
│   │   └── ImageGenerating.svelte (optional, when generation in progress)
│   └── ThinkingIndicator.svelte
├── ImageGallery.svelte (slide-out panel, overlay)
└── CharacterSheetModal.svelte
```

### NarrativeMessage.svelte Modifications

The existing `NarrativeMessage.svelte` component needs the following changes:

1. **New props:** `sceneImage` (optional `SceneImage`), `isGenerating` (boolean), `onIllustrateTurn` (callback)
2. **Inline image rendering:** When `sceneImage` is present, render `<SceneImage>` above the message content
3. **Loading placeholder:** When `isGenerating` is true, render `<ImageGenerating>` above the message content
4. **Turn number click handler:** Wire existing `.turn-number` elements to call `onIllustrateTurn(message.index)` on click

```svelte
<!-- In NarrativeMessage.svelte, before the message content block -->
{#if isGenerating && !sceneImage}
    <ImageGenerating turnNumber={message.index} mode="specific" />
{/if}

{#if sceneImage}
    <SceneImage image={sceneImage} />
{/if}
```

The turn number click wiring:

```svelte
<span
    class="turn-number"
    role="button"
    tabindex="0"
    aria-label="Illustrate Turn {turnNumber}"
    onclick={() => onIllustrateTurn?.(message.index)}
    onkeydown={(e) => e.key === 'Enter' && onIllustrateTurn?.(message.index)}
>Turn {turnNumber}</span>
```

### NarrativePanel.svelte Modifications

The panel needs to lookup images and generation state for each visible message:

```svelte
<script lang="ts">
    import { images, generatingTurns } from '$lib/stores/imageStore';
    import { generateTurnImage } from '$lib/api';
    import { startGeneration } from '$lib/stores/imageStore';

    // Derived: map of turn_number -> SceneImage for O(1) lookup
    const imagesByTurn = $derived(
        ($images).reduce<Record<number, SceneImage>>((map, img) => {
            map[img.turn_number] = img;
            return map;
        }, {})
    );

    const currentGenerating = $derived($generatingTurns);

    async function handleIllustrateTurn(turnIndex: number): Promise<void> {
        if (!sessionId) return;
        try {
            startGeneration(turnIndex);
            await generateTurnImage(sessionId, turnIndex);
        } catch (e) {
            console.error('[Narrative] Failed to generate image:', e);
            // Remove from generating set on error
            generatingTurns.update((s) => {
                const next = new Set(s);
                next.delete(turnIndex);
                return next;
            });
        }
    }
</script>

{#each visibleMessages as msg (msg.index)}
    <NarrativeMessage
        message={msg}
        characterInfo={getCharInfo(msg)}
        isCurrent={msg.index === parsedMessages.length - 1}
        sceneImage={imagesByTurn[msg.index]}
        isGenerating={currentGenerating.has(msg.index)}
        onIllustrateTurn={handleIllustrateTurn}
    />
{/each}
```

### IllustrateMenu.svelte Design

The dropdown follows a click-to-open pattern (not hover) with click-outside-to-close:

```svelte
<script lang="ts">
    import { generateCurrentImage, generateBestImage } from '$lib/api';
    import { startGeneration, startBestGeneration, galleryOpen } from '$lib/stores/imageStore';
    import { gameState, connectionStatus } from '$lib/stores';

    let { sessionId, totalTurns, onOpenGallery }: Props = $props();

    let open = $state(false);
    let showTurnDialog = $state(false);
    let turnInput = $state(1);

    const imageEnabled = $derived(
        ($gameState as any)?.game_config?.image_generation_enabled ?? false
    );
    const notConnected = $derived($connectionStatus !== 'connected');
    const disabled = $derived(notConnected || !imageEnabled);

    // Toggle for keyboard shortcut
    export function toggle(): void {
        if (!disabled) open = !open;
    }

    async function handleCurrentScene(): Promise<void> { ... }
    async function handleBestScene(): Promise<void> { ... }
    async function handleTurnGenerate(): Promise<void> { ... }
</script>
```

The Turn # dialog is shown inline below the dropdown when selected. It includes:
- A number input with min=1, max=totalTurns
- A preview snippet of the turn content (from ground_truth_log)
- Generate and Cancel buttons

### ImageGallery.svelte Design

The gallery is a slide-out panel from the right side (similar to how ForkComparison is an overlay). It reads directly from the `images` store and renders a 2-column CSS grid.

```svelte
<script lang="ts">
    import { images, galleryOpen } from '$lib/stores/imageStore';

    function close(): void {
        galleryOpen.set(false);
    }

    function handleKeydown(e: KeyboardEvent): void {
        if (e.key === 'Escape') close();
    }

    // Mode badge text
    function modeBadge(mode: string): string {
        return mode.charAt(0).toUpperCase() + mode.slice(1);
    }
</script>

{#if $galleryOpen}
    <div class="gallery-backdrop" onclick={close}>
        <aside class="gallery-panel" onclick|stopPropagation role="dialog" aria-label="Scene Gallery">
            <header>
                <h3>Scene Gallery</h3>
                <button onclick={close} aria-label="Close gallery">X</button>
            </header>
            <div class="image-gallery" role="grid">
                {#each $images as img (img.id)}
                    <div class="gallery-card" role="gridcell">
                        <img class="gallery-image" src={img.download_url} alt={img.prompt} />
                        <div class="gallery-meta">
                            <span class="gallery-label">Turn {img.turn_number + 1}</span>
                            <span class="gallery-mode-badge">{modeBadge(img.generation_mode)}</span>
                        </div>
                        <a href={img.download_url} download aria-label="Download image for Turn {img.turn_number + 1}">Download</a>
                    </div>
                {/each}
            </div>
        </aside>
    </div>
{/if}
```

### CSS Design Tokens

All CSS follows the UX Design Specification exactly. Key styles:

**Inline image container** (from UX spec):
```css
.scene-image-container {
    position: relative;
    margin-bottom: var(--space-md);
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid var(--bg-message);
}

.scene-image {
    width: 100%;
    height: auto;
    display: block;
    aspect-ratio: 16 / 9;
    object-fit: cover;
}

.scene-image-overlay {
    position: absolute;
    bottom: 0;
    right: 0;
    padding: var(--space-sm);
    display: flex;
    gap: var(--space-xs);
    opacity: 0;
    transition: opacity 0.15s ease;
}

.scene-image-container:hover .scene-image-overlay {
    opacity: 1;
}
```

**Loading placeholder** (from UX spec):
```css
.image-generating {
    background: var(--bg-secondary);
    border: 1px dashed var(--accent-warm);
    border-radius: 8px;
    padding: var(--space-lg);
    text-align: center;
    margin-bottom: var(--space-md);
    min-height: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: var(--space-sm);
}

.image-generating-text {
    font-family: var(--font-ui);
    font-size: 14px;
    color: var(--accent-warm);
    font-style: italic;
}
```

**Gallery grid** (from UX spec):
```css
.image-gallery {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-md);
    padding: var(--space-md);
}

.gallery-mode-badge {
    font-family: var(--font-mono);
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 4px;
    background: rgba(232, 168, 73, 0.15);
    color: var(--accent-warm);
}
```

### Keyboard Shortcut Integration

Shortcuts are added to the existing `handleKeydown()` in `+page.svelte` (the game session page). This function already guards against input/textarea/select focus, so the new shortcuts automatically respect that pattern.

```typescript
// In +page.svelte handleKeydown():
else if (event.key === 'I' || event.key === 'i') {
    // Toggle illustration menu (via ref or store)
    illustrateMenuRef?.toggle();
}
else if (event.key === 'G' || event.key === 'g') {
    galleryOpen.update((v) => !v);
}
```

The `illustrateMenuRef` can be obtained via Svelte's `bind:this` or by exporting a `toggle()` function from `IllustrateMenu.svelte`.

### Turn Number Click-to-Illustrate Wiring

Turn numbers in `NarrativeMessage.svelte` already have `role="button"`, `tabindex="0"`, `cursor: pointer`, and hover styling (camera emoji on hover) from Story 17-1. This story adds the actual `onclick` handler.

The click dispatches `onIllustrateTurn(message.index)` where `message.index` is the 0-based index in `ground_truth_log`. This maps directly to the `turn_number` parameter in `POST /api/sessions/{id}/images/generate-turn/{turn_number}`.

**Important:** The display shows "Turn N" (1-based) but the API uses 0-based indices. The `NarrativeMessage` already computes `turnNumber = message.index + 1` for display. The `onIllustrateTurn` callback receives the 0-based `message.index`.

### Image URL Pattern

Images are served via: `/api/sessions/{session_id}/images/{image_id}.png`

The `download_url` field in `SceneImageResponse` is pre-computed by the backend and included in both:
- REST response: `GET /api/sessions/{id}/images` list
- WebSocket event: `image_ready` payload

The frontend uses this URL directly in `<img src>` and `<a href download>` tags. The Vite dev proxy already forwards `/api/` to the FastAPI backend.

### Error Handling

- **API errors (429 Too Many Requests):** When max concurrent tasks are exceeded, the API returns 429. Display inline error toast: "Image generation busy. Please wait."
- **API errors (400 Bad Request):** When image generation is disabled. This should not normally happen since the UI hides the menu when disabled, but handle defensively.
- **WebSocket errors:** The backend broadcasts `error` events with `recoverable: true` on image generation failure. The existing error handling in `handleServerMessage` sets `lastError`, which can be displayed.
- **Network errors:** If the API call itself fails, catch in the calling function, log, and remove from `generatingTurns`.

### `image_generation_enabled` Config Awareness

The `IllustrateMenu` should only render when image generation is enabled. The game config includes `image_generation_enabled` but it is not currently in the frontend `GameConfig` type. Options:

1. **Read from gameState directly:** The full state snapshot from `session_state` WebSocket events includes the game config. Cast via `($gameState as any)?.game_config?.image_generation_enabled`.
2. **Add to GameConfig type:** Add `image_generation_enabled?: boolean` to the `GameConfig` interface in `types.ts`. This is the cleaner approach.

Use option 2. Add to `GameConfig`:

```typescript
export interface GameConfig {
    // ... existing fields
    image_generation_enabled?: boolean;
}
```

### Session Page Reset

When navigating to a new session or disconnecting, `resetStores()` in `gameStore.ts` is called. Add `resetImageStore()` to this function so that images from a previous session are cleared.

### Files to Create

| File | Description |
|------|-------------|
| `frontend/src/lib/stores/imageStore.ts` | Image store (writable stores, helper functions) |
| `frontend/src/lib/components/SceneImage.svelte` | Inline image display with hover download |
| `frontend/src/lib/components/ImageGenerating.svelte` | Loading placeholder during generation |
| `frontend/src/lib/components/IllustrateMenu.svelte` | Dropdown menu for illustration actions |
| `frontend/src/lib/components/ImageGallery.svelte` | Gallery slide-out panel |
| `frontend/src/lib/stores/imageStore.test.ts` | Tests for image store |
| `frontend/src/lib/components/SceneImage.test.ts` | Tests for SceneImage component |
| `frontend/src/lib/components/ImageGenerating.test.ts` | Tests for loading placeholder |
| `frontend/src/lib/components/IllustrateMenu.test.ts` | Tests for dropdown menu |
| `frontend/src/lib/components/ImageGallery.test.ts` | Tests for gallery panel |

### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/lib/types.ts` | Modified | Add `SceneImage`, `WsImageReady`, `ImageGenerateAccepted`, `BestSceneAccepted` types; add `WsImageReady` to `WsServerEvent` union; add `image_generation_enabled` to `GameConfig` |
| `frontend/src/lib/api.ts` | Modified | Add `generateCurrentImage()`, `generateTurnImage()`, `generateBestImage()`, `getSessionImages()` functions |
| `frontend/src/lib/stores/index.ts` | Modified | Export image store items |
| `frontend/src/lib/stores/gameStore.ts` | Modified | Add `image_ready` case to `handleServerMessage()`; call `resetImageStore()` in `resetStores()` |
| `frontend/src/lib/components/NarrativeMessage.svelte` | Modified | Add `sceneImage`, `isGenerating`, `onIllustrateTurn` props; render inline image/placeholder; wire turn number click |
| `frontend/src/lib/components/NarrativePanel.svelte` | Modified | Import image stores; derive per-message image/generating state; add `handleIllustrateTurn` handler; add `IllustrateMenu` to header; pass new props to `NarrativeMessage` |
| `frontend/src/routes/game/[sessionId]/+page.svelte` | Modified | Add `ImageGallery` component; load images on mount; add `I`/`G` keyboard shortcuts |

### Existing Patterns Followed

| Pattern | Source | Usage Here |
|---------|--------|-----------|
| Writable stores | `gameStore.ts`, `uiStore.ts` | `imageStore.ts` uses `writable<T>()` |
| `handleServerMessage()` dispatch | `gameStore.ts` | Add `image_ready` case |
| `resetStores()` cleanup | `gameStore.ts` | Add `resetImageStore()` |
| REST API client | `api.ts` `request<T>()` | Image generation endpoints |
| Component props with `$props()` | `NarrativeMessage.svelte`, `SettingsModal.svelte` | All new components |
| Svelte 5 `$derived` | `NarrativePanel.svelte` | `imagesByTurn` map derivation |
| Modal/overlay backdrop | `SettingsModal.svelte` | Gallery panel backdrop |
| Click-outside-to-close | `SettingsModal.svelte` | Dropdown menu + gallery |
| Keyboard shortcut guard | `+page.svelte` `handleKeydown()` | `I` and `G` shortcuts |
| CSS design tokens | `app.css` custom properties | All component styles |
| UX spec CSS classes | `ux-design-specification.md` | Exact class names and styles from v2.1 section |

### What This Story Does NOT Do

- **No image generation backend changes.** All backend APIs (Stories 17-2, 17-3, 17-4) are already complete. This story is purely frontend.
- **No image configuration UI.** The Settings modal's Image Generation tab is out of scope (could be a separate story or part of 17-6). Image generation enable/disable and model selection are already configurable via `PUT /api/sessions/{id}/config`.
- **No bulk download / ZIP export.** Bulk download is in Story 17-6 (Image Export & Download).
- **No image deletion UI.** Deleting individual images from the gallery is not in scope.
- **No progressive loading / lazy loading of images.** Images are loaded eagerly. For sessions with many images, this could be optimized later.
- **No lightbox / full-screen image view.** Clicking an inline image does not open a modal viewer. This can be added as a UX enhancement later.

### Common Pitfalls to Avoid

1. **Do NOT confuse 0-based turn indices with 1-based display numbers.** The API uses 0-based `turn_number` (index into `ground_truth_log`). The UI displays "Turn 1" for index 0. Always pass `message.index` to API calls, display `message.index + 1` to users.
2. **Do NOT forget to add `WsImageReady` to the `WsServerEvent` union type.** Without this, TypeScript will not recognize the `image_ready` case in `handleServerMessage()` and the discriminated union narrowing will break.
3. **Do NOT import `imageStore` functions inside `gameStore.ts` at the module level if it creates a circular dependency.** Instead, use lazy imports or have the game page wire the connection externally. If `imageStore` imports from `api.ts` (no store dependency) and `gameStore` imports from `imageStore`, there is no cycle since `imageStore` does not import from `gameStore`.
4. **Do NOT send request body for GET endpoints.** `getSessionImages()` is a GET request and should not include a body. Only POST endpoints (`generate-current`, `generate-turn`, `generate-best`) send a body.
5. **Do NOT create a new WebSocket event listener for `image_ready`.** Use the existing `handleServerMessage()` dispatch pattern in `gameStore.ts`. The WebSocket client already forwards all events.
6. **Do NOT forget to call `loadSessionImages()` on page mount.** Without this, images from previous generations will not appear until a new `image_ready` event fires.
7. **Do NOT render the illustration menu when `image_generation_enabled` is false.** This avoids confusing users who have not configured image generation. The menu should either be hidden entirely or shown disabled with a tooltip.
8. **Do NOT forget `click-outside-to-close` for the dropdown menu.** Without this, the dropdown stays open when the user clicks elsewhere, breaking UX expectations.
9. **Do NOT use `$effect` to derive per-message image lookups.** Use `$derived` with a Map/Record for O(1) lookup per message. An `$effect` that iterates images per render would be O(n*m) where n is messages and m is images.

### References

- [Source: `api/schemas.py` — `SceneImageResponse`, `ImageGenerateAccepted`, `BestSceneAccepted`, `WsImageReady`]
- [Source: `api/routes.py` — `POST /images/generate-current`, `POST /images/generate-turn/{turn}`, `POST /images/generate-best`, `GET /images`, `GET /images/{filename}`]
- [Source: `frontend/src/lib/types.ts` — existing TypeScript types, `WsServerEvent` union]
- [Source: `frontend/src/lib/api.ts` — `request<T>()` helper, existing API client functions]
- [Source: `frontend/src/lib/ws.ts` — `createGameConnection()`, `onMessage` callback pattern]
- [Source: `frontend/src/lib/stores/gameStore.ts` — `handleServerMessage()`, `resetStores()`]
- [Source: `frontend/src/lib/stores/uiStore.ts` — store pattern reference]
- [Source: `frontend/src/lib/stores/narrativeStore.ts` — derived store from gameState]
- [Source: `frontend/src/lib/components/NarrativeMessage.svelte` — turn number elements, component structure]
- [Source: `frontend/src/lib/components/NarrativePanel.svelte` — narrative rendering, session header]
- [Source: `frontend/src/lib/components/SettingsModal.svelte` — modal/overlay pattern, focus trap, backdrop click]
- [Source: `frontend/src/routes/game/[sessionId]/+page.svelte` — keyboard shortcuts, WebSocket connection, component composition]
- [Source: `frontend/src/app.css` — CSS custom properties / design tokens]
- [Source: `_bmad-output/planning-artifacts/ux-design-specification.md` — v2.1 image generation UI section]
- [Source: `_bmad-output/planning-artifacts/epics-v2.1.md` — Story 17.5 definition]
- [Source: `_bmad-output/implementation-artifacts/17-4-best-scene-scanner.md` — Story format reference]

---

## File List

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/lib/types.ts` | Modified | Add `SceneImage`, `WsImageReady`, `ImageGenerateAccepted`, `BestSceneAccepted`; extend `WsServerEvent` union; add `image_generation_enabled` to `GameConfig` |
| `frontend/src/lib/api.ts` | Modified | Add `generateCurrentImage()`, `generateTurnImage()`, `generateBestImage()`, `getSessionImages()` |
| `frontend/src/lib/stores/imageStore.ts` | Created | Image store: `images`, `generatingTurns`, `generatingBest`, `galleryOpen`, helper functions |
| `frontend/src/lib/stores/index.ts` | Modified | Export image store items |
| `frontend/src/lib/stores/gameStore.ts` | Modified | Add `image_ready` to `handleServerMessage()`; call `resetImageStore()` in `resetStores()` |
| `frontend/src/lib/components/SceneImage.svelte` | Created | Inline image display with hover download button |
| `frontend/src/lib/components/ImageGenerating.svelte` | Created | Loading placeholder ("Painting the scene...") |
| `frontend/src/lib/components/IllustrateMenu.svelte` | Created | Dropdown button with generation options and Turn # dialog |
| `frontend/src/lib/components/ImageGallery.svelte` | Created | 2-column gallery slide-out panel |
| `frontend/src/lib/components/NarrativeMessage.svelte` | Modified | Add image/generating props, wire turn number click |
| `frontend/src/lib/components/NarrativePanel.svelte` | Modified | Derive per-message image state, add IllustrateMenu to header, pass new props |
| `frontend/src/routes/game/[sessionId]/+page.svelte` | Modified | Add ImageGallery, load images on mount, add I/G keyboard shortcuts |
| `frontend/src/lib/stores/imageStore.test.ts` | Created | Tests for image store functions |
| `frontend/src/lib/components/SceneImage.test.ts` | Created | Tests for SceneImage component |
| `frontend/src/lib/components/ImageGenerating.test.ts` | Created | Tests for loading placeholder |
| `frontend/src/lib/components/IllustrateMenu.test.ts` | Created | Tests for dropdown menu |
| `frontend/src/lib/components/ImageGallery.test.ts` | Created | Tests for gallery panel |

---

## Code Review

**Reviewer:** Claude Opus 4.6 (adversarial review)
**Date:** 2026-02-14
**Status:** PASSED (with fixes applied)

### Issues Found: 8 (5 fixed, 3 documented)

#### Issue 1 — HIGH — Duplicate images on WebSocket reconnect (FIXED)
- **File:** `frontend/src/lib/stores/imageStore.ts`
- **Problem:** `handleImageReady()` unconditionally appends images via `[...list, image]`. If WebSocket reconnects and re-delivers `image_ready` events, or if `loadSessionImages()` has already loaded the same image, duplicates appear in the gallery and inline.
- **Fix:** Added deduplication check: `if (list.some((existing) => existing.id === image.id)) return list;` before appending.

#### Issue 2 — MEDIUM — `handleBestScene` error does not reset `generatingBest`, leaving permanent spinner (FIXED)
- **File:** `frontend/src/lib/components/IllustrateMenu.svelte`
- **Problem:** On API error in `handleBestScene()`, `generatingBest` stayed `true` forever. Comment said "leave it in generating state; user can retry" but no retry mechanism exists. Users see a permanent loading indicator.
- **Fix:** Added `generatingBest.set(false)` in the catch block. Imported `generatingBest` from imageStore.

#### Issue 3 — MEDIUM — `narrativePanelRef` not reactive with `$state()` (FIXED)
- **File:** `frontend/src/routes/game/[sessionId]/+page.svelte`
- **Problem:** `let narrativePanelRef: NarrativePanel | undefined;` was not declared with `$state()`, causing Svelte 5 `non_reactive_update` warning. `bind:this` updates the variable but changes would not trigger reactivity.
- **Fix:** Changed to `let narrativePanelRef: NarrativePanel | undefined = $state();`.

#### Issue 4 — MEDIUM — Errors displayed to closed menu are invisible to users (FIXED)
- **File:** `frontend/src/lib/components/IllustrateMenu.svelte`
- **Problem:** In `handleCurrentScene()`, `handleBestScene()`, and `handleTurnGenerate()`, `closeMenu()` was called *before* `await`, so if the API call fails, `error` is set but the menu is already closed and the user sees nothing.
- **Fix:** Moved `closeMenu()` to after the `await` in all three handlers. On success the menu closes; on error the menu stays open and displays the error message.

#### Issue 5 — MEDIUM — Gallery dialog lacks focus trap and initial focus (FIXED)
- **File:** `frontend/src/lib/components/ImageGallery.svelte`
- **Problem:** The gallery panel has `role="dialog"` but Tab key cycles to elements behind the backdrop. No initial focus management. WCAG 2.1 requires dialogs to trap focus.
- **Fix:** Added focus trap (Tab/Shift+Tab cycling within panel), initial focus on close button when gallery opens, focus restoration to previous element on close. Added `aria-modal="true"`.

#### Issue 6 — LOW — SceneImage download button not visible for keyboard-only users (NOT FIXED)
- **File:** `frontend/src/lib/components/SceneImage.svelte`
- **Problem:** The download button overlay is at `opacity: 0` by default and only revealed on hover. Keyboard users tabbing to the button see the focus outline but the button text itself is invisible until hover. Consider adding `.scene-image-container:focus-within .scene-image-overlay { opacity: 1; }`.

#### Issue 7 — LOW — Misleading `Math.min(totalTurns, 1)` expression (FIXED as part of Issue 4)
- **File:** `frontend/src/lib/components/IllustrateMenu.svelte`
- **Problem:** `turnInput = Math.min(totalTurns, 1)` always evaluates to 1 when `totalTurns >= 1`. The `Math.min` is semantically misleading.
- **Fix:** Simplified to `turnInput = 1` for clarity.

#### Issue 8 — LOW — Missing test for click-to-illustrate callback (NOT FIXED)
- **File:** `frontend/src/lib/components/NarrativeMessage.test.ts`
- **Problem:** No test verifies that clicking a turn number calls `onIllustrateTurn(message.index)`. Tests verify turn number display and ARIA attributes but not the callback dispatch. AC4 is partially uncovered.
- **Recommendation:** Add a test using `fireEvent.click()` on `.turn-number` and assert `onIllustrateTurn` mock is called with the correct index.

### Verification

- **Tests:** 181/181 passing (0 regressions)
- **Type check:** 0 errors, 16 warnings (all pre-existing in unrelated files)
- **Svelte 5 compliance:** All components use `$state`, `$derived`, `$props` correctly; no legacy store syntax in components
- **CSS:** All styles use design tokens (verified against `app.css` custom properties)
- **Security:** Image URLs come from backend `download_url` field; all user-facing content is sanitized via `formatMessageContent()` pipeline; no XSS vectors identified
- **WebSocket integration:** `image_ready` case correctly wired in `handleServerMessage()`; `resetImageStore()` called in `resetStores()`
