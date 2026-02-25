# Sprint Change Proposal — Illustration Gallery Enhancement

**Date:** 2026-02-24
**Triggered by:** Feature request — enhanced browsable illustration gallery
**Mode:** Batch
**Scope:** Minor (direct implementation by dev team)

---

## Section 1: Issue Summary

### Problem Statement

The current illustration gallery (`ImageGallery.svelte`) is a minimal 520px right-side panel with a 2-column grid of image cards. While functional for viewing a few images, it lacks the features needed for a rich browsing experience as campaigns accumulate dozens of illustrations across hundreds of turns:

1. **No full-size image viewing** — Users can only see grid-sized previews; there's no way to click into a full-size view or download from a detail view.
2. **No hover prompts** — The prompt text used to generate each image is stored in metadata but not surfaced in the gallery UI.
3. **No cross-session browsing** — The gallery is locked to the current game session. Users cannot browse illustrations from other adventures without opening each session individually.
4. **No entry point from adventures list** — The gallery is only accessible from within a running game session. Users browsing their adventure list cannot view illustrations without entering a session.
5. **Thumbnails are not optimized** — Full images are displayed at grid size, with no responsive thumbnail grid.

### Context

This feature request emerged during a 1000-turn campaign (session 012) where 30+ illustrations were generated. The user wants a gallery experience with:
- Thumbnail grid with hover-to-see-prompt
- Full-size lightbox view with download capability
- Cross-session navigation
- Entry points from both the game page and adventures list page

### Evidence

- **Gallery design doc:** `docs/gallery-enhancement-plan.md` (component architecture, keyboard shortcuts, store design)
- **Existing implementation:** `ImageGallery.svelte` (370 lines), `imageStore.ts`, `SceneImage` type, existing API endpoints for image metadata and downloads
- **Campaign context:** Session 012 has 30+ illustrations, demonstrating the need for better browsing

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| Epic 17 (AI Scene Image Generation) | Extended | Two new stories (17.7, 17.8) added to complete the gallery experience |

No other epics are affected. The gallery enhancement builds entirely on Epic 17's existing infrastructure.

### Story Impact

**New stories:**
- **Story 17.7:** Enhanced Gallery with Lightbox — Refactor `ImageGallery.svelte` into `GalleryModal` + `GalleryGrid` + `ImageLightbox` with thumbnail grid, hover prompts, and full-size lightbox view with download
- **Story 17.8:** Cross-Session Gallery & Adventures Entry Point — Add session switcher dropdown, new summary API endpoint, and gallery entry point on the adventures list page

**Existing stories:** No changes needed to stories 17.1–17.6 (all completed and working).

### Artifact Conflicts

| Artifact | Sections Affected |
|----------|-------------------|
| PRD | Add FR93-FR97, update growth features table |
| Epics (v2.1) | Add Stories 17.7 & 17.8, update Epic 17 summary table |
| Architecture | Add new API endpoint documentation |
| UX Design Spec | Add gallery modal section |
| Sprint Status | Add 17-7 and 17-8 as backlog |

### Technical Impact

- **Frontend:** Refactor `ImageGallery.svelte` (370 lines) into 3 new components; update `imageStore.ts` with new stores
- **Backend:** One new API endpoint (`GET /api/sessions/images/summary`)
- **No model/persistence changes:** No changes to `GameState`, `models.py`, `persistence.py`, or checkpoint format
- **No breaking changes:** Existing image generation, download, and gallery functionality remains intact
- **Risk:** Low. Entirely additive UI feature with one small API addition.

---

## Section 3: Recommended Approach

### Path: Direct Adjustment

Add two new stories (17.7 and 17.8) to the existing Epic 17. This is the simplest and most appropriate path because:

1. **Natural extension** — The gallery enhancement is a direct continuation of Epic 17's image generation work
2. **No conflicts** — All 6 existing stories are done; no in-progress work to coordinate around
3. **Self-contained** — Changes are limited to frontend components, one store file, and one new API endpoint
4. **Existing infrastructure** — All required API endpoints for image metadata and downloads already exist

### Effort Estimate

| Story | Effort | Details |
|-------|--------|---------|
| 17.7 (Gallery + Lightbox) | Medium | Refactor existing component into 3 new ones, add lightbox with keyboard nav |
| 17.8 (Cross-Session + Adventures) | Small-Medium | Session switcher dropdown, 1 new API endpoint, adventures list integration |

### Risk Assessment

- **Low risk.** No changes to game engine, state management, or persistence
- **No regression risk** to autopilot, WebSocket, or existing image generation
- **Frontend-only** except for one lightweight summary endpoint

---

## Section 4: Detailed Change Proposals

### Proposal 1: PRD — Add FR93-FR97

**File:** `_bmad-output/planning-artifacts/prd.md`
**Section:** Functional Requirements > AI Scene Illustration

**ADD after FR92:**

```
- FR93: User can browse all session illustrations in a modal gallery with thumbnail grid, hover-to-view prompt, and card metadata (turn number, generation mode, timestamp)
- FR94: User can click a gallery thumbnail to open a full-size lightbox view with image navigation (prev/next), metadata panel, and download button
- FR95: User can switch between sessions within the gallery modal to browse illustrations from other adventures
- FR96: User can access the illustration gallery from the adventures list page, with image count badges on session cards
- FR97: Backend provides a lightweight session image summary endpoint for gallery population and image count badges
```

**Rationale:** Formally documents the 5 new functional requirements for the gallery feature, extending the existing FR85-FR92 image generation requirements.

---

### Proposal 2: PRD — Update Growth Features Table

**File:** `_bmad-output/planning-artifacts/prd.md`
**Section:** Product Scope > Growth Features table

**OLD:**
```
| AI Scene Illustration | v2.1 | AI-generated images of D&D scenes |
```

**NEW:**
```
| AI Scene Illustration & Gallery | v2.1 | AI-generated images of D&D scenes with browsable gallery, lightbox, and cross-session navigation |
```

**Rationale:** Reflects expanded scope of the image feature to include gallery browsing.

---

### Proposal 3: Epics — Add Story 17.7

**File:** `_bmad-output/planning-artifacts/epics-v2.1.md`
**Section:** Epic 17 stories

**ADD after Story 17.6:**

```markdown
### Story 17.7: Enhanced Gallery with Lightbox

As a **user browsing illustrations**,
I want **a modal gallery with thumbnail grid, hover prompts, and full-size lightbox view**,
So that **I can browse, preview, and download my campaign illustrations in a rich visual experience**.

**Acceptance Criteria:**

1. Gallery opens as centered modal overlay (80vw x 80vh) instead of side panel
2. Thumbnail grid displays 3-4 responsive columns of square-cropped image previews
3. Hovering a thumbnail shows tooltip with the generation prompt and timestamp
4. Each card shows turn number badge, generation mode badge, and formatted timestamp
5. Clicking a thumbnail opens full-screen lightbox with:
   - Large image display (max-width/max-height constrained to viewport)
   - Download button for the full-resolution PNG
   - Metadata panel (turn number, prompt, generation mode, timestamp, model)
   - Left/right arrow navigation (keyboard + click) for prev/next image
   - Close via ESC, backdrop click, or X button
6. ESC from lightbox returns to gallery grid; ESC from gallery closes it entirely
7. Left/Right arrows navigate images in lightbox; Enter opens lightbox from focused thumbnail
8. D key downloads current image when lightbox is open
9. Focus trap within modal; aria-labels on all interactive elements
10. Empty state message when session has no illustrations
11. "Download All" button retained from current implementation
12. Images sorted chronologically by turn_number ascending

**Technical Notes:**
- Refactor existing `ImageGallery.svelte` (370 lines) into: `GalleryModal.svelte` (wrapper), `GalleryGrid.svelte` (thumbnail grid + hover), `ImageLightbox.svelte` (full-size view)
- Add `lightboxIndex` store to `imageStore.ts` (number | null — index of currently viewed image)
- Reuse existing `getImageDownloadUrl()` for lightbox download button
- Existing `G` keyboard shortcut and IllustrateMenu "View Gallery" entry point remain unchanged

**FRs:** FR93, FR94

**Dependencies:** Story 17.5 (existing UI), Story 17.6 (existing export)
```

---

### Proposal 4: Epics — Add Story 17.8

**File:** `_bmad-output/planning-artifacts/epics-v2.1.md`
**Section:** Epic 17 stories

**ADD after Story 17.7:**

```markdown
### Story 17.8: Cross-Session Gallery & Adventures Entry Point

As a **user with multiple adventures**,
I want **to browse illustrations across sessions and access the gallery from the adventures list**,
So that **I can revisit campaign artwork without entering each session individually**.

**Acceptance Criteria:**

1. Gallery modal includes a session switcher dropdown at the top showing current session name
2. Dropdown lists all sessions that have at least one illustration, in format: "Session Name (N images)"
3. Selecting a different session loads its images via `loadSessionImages(newSessionId)`
4. Current session is highlighted/pre-selected in the dropdown
5. New API endpoint `GET /api/sessions/images/summary` returns `[{session_id, session_name, image_count}]` for all sessions with images
6. Adventures list page (`+page.svelte`) shows gallery icon button on each session card that has images
7. Session cards display small image count badge (e.g., "12 images")
8. Clicking the gallery icon on a session card opens the gallery modal pre-loaded with that session's images
9. Gallery modal is mountable on both the game page and adventures list page (shared component)
10. Session switcher works from both entry points

**Technical Notes:**
- Add `gallerySessionId` store (string | null) and `sessionImageSummaries` store to `imageStore.ts`
- New API endpoint in `api/routes.py`: scan `campaigns/` directory for sessions with images, return lightweight summary
- Update `SessionCard.svelte` to show gallery button + image count badge
- Import and mount `GalleryModal` on adventures list `+page.svelte`

**FRs:** FR95, FR96, FR97

**Dependencies:** Story 17.7 (enhanced gallery modal must exist first)
```

---

### Proposal 5: Epics — Update Epic 17 Summary Table

**File:** `_bmad-output/planning-artifacts/epics-v2.1.md`
**Section:** Epic List table

**OLD:**
```
| 17 | AI Scene Image Generation | 6 | 8 |
```

**NEW:**
```
| 17 | AI Scene Image Generation | 8 | 13 |
```

Also update the **FRs Covered** line in the Epic 17 description:

**OLD:**
```
**FRs Covered:** FR85-FR92 (8 FRs)
```

**NEW:**
```
**FRs Covered:** FR85-FR97 (13 FRs)
```

And update the **Summary** line:

**OLD:**
```
**Summary:** 1 New Epic, 6 Stories
```

**NEW:**
```
**Summary:** 1 New Epic, 8 Stories
```

---

### Proposal 6: Architecture — Add Summary Endpoint

**File:** `_bmad-output/planning-artifacts/architecture.md`
**Section:** API endpoint documentation

**ADD** to the image generation endpoints section:

```
GET /api/sessions/images/summary
  → [{session_id: str, session_name: str, image_count: int}]
  Lightweight summary of all sessions with images. Used by gallery session
  switcher and adventures list image count badges.
```

**Rationale:** Documents the one new backend endpoint needed for gallery feature.

---

### Proposal 7: UX Design Spec — Add Gallery Section

**File:** `_bmad-output/planning-artifacts/ux-design-specification.md`
**Section:** Add new subsection under Image Generation UI

**ADD:**

```markdown
### Illustration Gallery

**Gallery Modal (GalleryModal)**
- Centered overlay, 80vw x 80vh, dark backdrop
- Header: session switcher dropdown (left), "Download All" button, close (X) button (right)
- Body: responsive thumbnail grid (3-4 columns)

**Thumbnail Grid (GalleryGrid)**
- Square-cropped thumbnails with turn number + generation mode badges
- Hover: tooltip showing prompt text and formatted timestamp
- Click: opens lightbox for that image

**Lightbox (ImageLightbox)**
- Full-screen overlay above gallery modal
- Large image centered, constrained to viewport
- Left panel or bottom bar: turn number, prompt, generation mode, timestamp, model
- Left/right arrow buttons + keyboard navigation
- Download button (full-res PNG)
- Close via ESC, backdrop click, or X button

**Entry Points:**
- Game page: existing `G` shortcut + IllustrateMenu "View Gallery" + optional sidebar icon
- Adventures list: gallery icon button on session cards with image count badge

**Keyboard Shortcuts:**
| Key | Context | Action |
|-----|---------|--------|
| G | Game page | Toggle gallery |
| ESC | Gallery | Close (lightbox first, then gallery) |
| ← / → | Lightbox | Prev / next image |
| Enter | Thumbnail focused | Open lightbox |
| D | Lightbox | Download current image |
| Tab | Gallery | Focus trap within modal |
```

**Rationale:** Documents the gallery UX patterns and keyboard interactions for implementation reference.

---

### Proposal 8: Sprint Status — Add New Stories

**File:** `_bmad-output/implementation-artifacts/sprint-status.yaml`
**Section:** Epic 17 entries

**Change epic-17 status:**
```yaml
  epic-17: in-progress
```

**ADD after `17-6-image-export-download: done`:**
```yaml
  17-7-enhanced-gallery-lightbox: backlog
  17-8-cross-session-gallery: backlog
```

**Rationale:** Tracks the two new stories in the sprint status file. Epic 17 moves back to `in-progress` since it now has incomplete work.

---

## Section 5: Implementation Handoff

### Scope Classification: Minor

This change can be implemented directly by the development team. No backlog reorganization or architectural replanning is needed.

### Handoff: Development Team (Dev Agent)

**Responsibilities:**
1. Apply all artifact updates (PRD, Epics, Architecture, UX Spec, Sprint Status) per proposals 1-8
2. Create story files for 17.7 and 17.8 via `create-story` workflow
3. Implement stories via `dev-story` → `code-review` → commit cycle
4. Story 17.7 must be completed before 17.8 (dependency)

### Success Criteria

1. Gallery modal opens from game page (`G` shortcut, IllustrateMenu) and adventures list (session card icon)
2. Thumbnail grid displays all session images with hover prompts and metadata badges
3. Clicking a thumbnail opens lightbox with full-size image, download button, and prev/next navigation
4. Session switcher dropdown allows browsing other sessions' illustrations
5. Adventures list shows image count badges on sessions with illustrations
6. All keyboard shortcuts work per the specification
7. Accessibility: focus trap, aria-labels, screen reader support
8. All existing image generation, download, and gallery functionality continues to work
9. Frontend tests (Vitest) cover new components
10. Python tests cover the new summary API endpoint

### Story Execution Order

```
17.7 (Enhanced Gallery with Lightbox) → 17.8 (Cross-Session Gallery)
```

Story 17.8 depends on 17.7's refactored component architecture being in place.
