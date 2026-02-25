# Illustration Gallery Enhancement — Implementation Plan

## Overview

Enhance the existing illustration gallery into a full-featured browsable gallery with thumbnails, hover prompts, full-size lightbox view with download, and cross-session navigation. Add a second entry point on the adventures list page.

## What Already Exists

- **`ImageGallery.svelte`** — Right-side overlay panel (520px), 2-column grid, turn number + generation mode badges, "Download All" button, ESC/focus-trap accessibility
- **`imageStore.ts`** — `images`, `galleryOpen` stores, `loadSessionImages(sessionId)` function
- **`SceneImage` type** — `id`, `session_id`, `turn_number`, `prompt`, `generation_mode`, `generated_at`, `download_url`
- **API** — `GET /api/sessions/{id}/images` returns all image metadata; individual PNG serving and download endpoints exist
- **Keyboard shortcut** — `G` toggles gallery from game page

## Proposed Changes

### 1. Enhanced Gallery Modal (`ImageGallery.svelte`)

**Current:** 520px right panel, 2-column grid, basic cards with turn/mode badges.

**Enhanced:**
- **Wider modal** — Center-screen overlay (80vw x 80vh) instead of side panel, to accommodate thumbnails + lightbox
- **Thumbnail grid** — 3-4 column responsive grid of square-cropped thumbnails
- **Hover tooltip** — Shows the prompt text used to generate the image, plus timestamp
- **Card metadata** — Turn number badge, generation mode badge (current/best/specific), formatted timestamp
- **Chronological order** — Sorted by `turn_number` ascending
- **Empty state** — Friendly message when session has no illustrations
- **Download All** — Retained from current implementation

### 2. Full-Size Lightbox View (New: `ImageLightbox.svelte`)

**Triggered by:** Clicking any thumbnail in the gallery grid.

**Features:**
- Full-screen overlay (z-index above gallery)
- Large image display (max-width/max-height constrained to viewport)
- **Download button** — Downloads the full-res PNG (reuses existing `getImageDownloadUrl()`)
- **Metadata panel** — Turn number, prompt text, generation mode, timestamp, model used
- **Navigation** — Left/right arrows (keyboard + click) to browse prev/next image
- **Close** — ESC key, click backdrop, or X button
- **Accessibility** — Focus trap, aria-labels

### 3. Session Switcher (Within Gallery Modal)

**Features:**
- Dropdown/select at top of gallery showing current session name
- Lists all sessions that have at least one illustration
- Selecting a different session loads its images via `loadSessionImages(newSessionId)`
- Current session highlighted/pre-selected
- Session display format: `"Session Name (N images)"`

**Backend addition needed:**
- New endpoint `GET /api/sessions/images/summary` — Returns `[{session_id, session_name, image_count}]` for all sessions with images. This avoids loading full image metadata for every session just to populate the dropdown.

### 4. Entry Point: Game Side Panel

**Location:** `NarrativePanel.svelte` header area (near existing Illustrate menu)

**Current:** "View Gallery" is already item #4 in the `IllustrateMenu` dropdown. The `G` keyboard shortcut also works.

**Enhancement:** Keep existing entry points. Optionally add a small gallery icon button in the side panel (`Sidebar.svelte`) for discoverability — shows image count badge.

### 5. Entry Point: Adventures List Page

**Location:** `SessionCard.svelte` on the `+page.svelte` (adventures list)

**Features:**
- Gallery icon button on each session card (only visible if session has images)
- Small image count badge (e.g., "12 images")
- Clicking opens the gallery modal overlay on the adventures list page
- Gallery opens pre-loaded with that session's images
- User can switch sessions via the session switcher within the gallery

**Requires:**
- Session list API already returns metadata; may need to add `image_count` field to session metadata response, or use the new summary endpoint
- Gallery modal component must be mountable on the adventures list page (not just game page)

### 6. Component Architecture

```
+page.svelte (Adventures List)
├── SessionCard.svelte          — Add gallery icon + image count
└── GalleryModal.svelte         — NEW: Shared gallery modal wrapper
    ├── GalleryHeader.svelte    — Session switcher dropdown + Download All + Close
    ├── GalleryGrid.svelte      — Thumbnail grid with hover tooltips
    └── ImageLightbox.svelte    — NEW: Full-size view with download + nav

game/[sessionId]/+page.svelte
├── NarrativePanel.svelte       — Existing IllustrateMenu "View Gallery" entry point
├── Sidebar.svelte              — Optional: gallery shortcut button
└── GalleryModal.svelte         — Same shared component, pre-loaded with current session
```

**Refactoring note:** The existing `ImageGallery.svelte` (370 lines) should be refactored into the new `GalleryModal` + `GalleryGrid` + `ImageLightbox` structure rather than trying to bolt everything onto the existing component.

### 7. Store Changes (`imageStore.ts`)

**Current stores:**
- `images` — `SceneImage[]` for current session
- `galleryOpen` — boolean

**New/modified stores:**
- `gallerySessionId` — `string | null` — Which session the gallery is showing (allows viewing other sessions' images)
- `galleryImages` — Renamed from `images` or separate store for gallery-specific image list (decoupled from the game session's images)
- `lightboxIndex` — `number | null` — Index of currently viewed image in lightbox (null = closed)
- `sessionImageSummaries` — `{session_id, session_name, image_count}[]` — For session switcher dropdown

### 8. API Changes

**New endpoint:**
```
GET /api/sessions/images/summary
Response: [{session_id: str, session_name: str, image_count: int}]
```
Returns lightweight summary of all sessions with images. Used by:
- Session switcher dropdown in gallery
- Image count badges on adventure list cards

**Existing endpoints (no changes needed):**
- `GET /api/sessions/{id}/images` — Full image list for a session
- `GET /api/sessions/{id}/images/{id}/download` — Individual download
- `GET /api/sessions/{id}/images/download-all` — Zip download

### 9. Accessibility & Keyboard

| Key | Context | Action |
|-----|---------|--------|
| `G` | Game page | Toggle gallery open/close |
| `ESC` | Gallery open | Close gallery (or close lightbox first) |
| `ESC` | Lightbox open | Close lightbox, return to grid |
| `←` / `→` | Lightbox open | Previous / next image |
| `Tab` | Gallery | Focus trap within modal |
| `Enter` | Thumbnail focused | Open lightbox |
| `D` | Lightbox open | Download current image |

### 10. Estimation

| Component | Effort |
|-----------|--------|
| `GalleryModal.svelte` (refactor from existing) | Medium |
| `GalleryGrid.svelte` (thumbnail grid + hover) | Medium |
| `ImageLightbox.svelte` (new) | Medium |
| Store changes (`imageStore.ts`) | Small |
| Session switcher + API endpoint | Small-Medium |
| Adventures list integration (`SessionCard`) | Small |
| Tests (Vitest component tests) | Medium |
| **Total** | ~1-2 stories |

### 11. Out of Scope

- Thumbnail generation (serve full PNGs, let browser scale — images are ~1.5MB each, acceptable for a local app)
- Image deletion from gallery
- Image re-generation from gallery
- Cross-session "all images" flat view
- Image tagging or search
