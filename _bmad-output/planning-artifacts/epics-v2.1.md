# autodungeon v2.1 - AI Scene Image Generation Epic

## Overview

This document provides the epic and story breakdown for autodungeon v2.1: AI Scene Image Generation, building on the completed v2.0 (Epics 1-16).

**Summary:** 1 New Epic, 8 Stories

## New Functional Requirements

**AI Scene Illustration (FR85-FR92):**

- FR85: User can generate an AI illustration of the current scene
- FR86: User can generate an AI illustration of the "best scene" from the entire session, using a configurable LLM to scan/analyze session history
- FR87: User can generate an AI illustration of a scene at a specific turn number
- FR88: Turn numbers are visible in the narrative display (format: "Turn N --- Name, the Class:")
- FR89: User can configure the text-to-image model (Imagen 3, Imagen 4, Gemini Flash Image)
- FR90: User can configure which LLM model scans session history for "best scene" selection
- FR91: User can download an individual generated image or bulk-download all images for a session
- FR92: Generated images are stored in the campaign directory for persistence

**Illustration Gallery (FR93-FR97):**

- FR93: User can browse all session illustrations in a modal gallery with thumbnail grid, hover-to-view prompt, and card metadata (turn number, generation mode, timestamp)
- FR94: User can click a gallery thumbnail to open a full-size lightbox view with image navigation (prev/next), metadata panel, and download button
- FR95: User can switch between sessions within the gallery modal to browse illustrations from other adventures
- FR96: User can access the illustration gallery from the adventures list page, with image count badges on session cards
- FR97: Backend provides a lightweight session image summary endpoint for gallery population and image count badges

## Epic List

| Epic | Title | Stories | FRs |
|------|-------|---------|-----|
| 17 | AI Scene Image Generation | 8 | 13 |

---

## Epic 17: AI Scene Image Generation

**Goal:** User can generate AI illustrations of D&D scenes from their campaign using Google's text-to-image models, with three modes: current scene, best scene (LLM-scanned), and specific turn.

**User Outcome:** "I'm watching an epic battle scene unfold. I click 'Illustrate Current Scene' and 10 seconds later there's a gorgeous fantasy painting of the scene right there in the narrative. I download it and send it to my D&D friends."

**FRs Covered:** FR85-FR97 (13 FRs)

**Dependencies:**
- `google-genai` Python package (new dependency)
- `Pillow` for image handling (new dependency)
- Existing `GEMINI_API_KEY` environment variable (same key used for game engine)

**Story Dependency Graph:**

```
17-1 (Turn Numbers) ---------------+
                                    +---> 17-5 (UI) ---> 17-6 (Export)
17-2 (Service) ---> 17-3 (API) ---+                          |
                +---> 17-4 (Scanner) ---> 17-5               v
                                                   17-7 (Gallery) ---> 17-8 (Cross-Session)
```

---

### Story 17.1: Turn Number Display

As a **user watching the narrative**,
I want **to see turn numbers in the narrative message headers**,
So that **I can identify specific turns when requesting image generation at a particular moment**.

**Acceptance Criteria:**

**Given** the narrative panel displaying PC messages
**When** rendered
**Then** the attribution format is "Turn N --- Name, the Class:" where N is the 1-based index in ground_truth_log

**Given** the narrative panel displaying DM messages
**When** rendered
**Then** a subtle "Turn N" label appears above the DM narration block

**Given** the turn number
**When** computed
**Then** it is derived from the message's index in the ground_truth_log array (1-based), requiring NO backend changes

**Given** a turn number in the narrative
**When** hovered
**Then** a subtle camera icon hint appears, indicating the turn can be illustrated (click-to-illustrate interaction)

**Given** the turn number styling
**When** rendered
**Then** it uses JetBrains Mono font, 11px, secondary text color at 60% opacity (per UX spec)

**Technical Notes:**
- Frontend-only change: `NarrativeMessage.svelte`
- Turn number = `message.index + 1` (already available as array index in `parseGroundTruthLog()`)
- No changes to backend log format, models, or API

---

### Story 17.2: Image Generation Service

As a **developer**,
I want **a Python module that wraps the Google text-to-image API**,
So that **the system can generate scene illustrations from text descriptions**.

**Acceptance Criteria:**

**Given** a new `image_gen.py` module
**When** imported
**Then** it provides:
```python
class ImageGenerator:
    async def generate_scene_image(
        self,
        prompt: str,
        session_id: str,
        turn_number: int,
        generation_mode: Literal["current", "best", "specific"],
    ) -> SceneImage

    async def build_scene_prompt(
        self,
        log_entries: list[str],
        characters: dict[str, Any],
    ) -> str
```

**Given** the `google-genai` SDK
**When** generating an image
**Then** it calls `client.models.generate_images(model, prompt, config)` with the configured image model

**Given** a generated image
**When** saved
**Then** it is stored as PNG in `campaigns/{session}/images/{image_id}.png`
**And** metadata is recorded in a `SceneImage` model

**Given** the `SceneImage` model in `models.py`
**When** created
**Then** it includes: `id`, `session_id`, `turn_number`, `prompt`, `image_path`, `provider`, `model`, `generation_mode`, `generated_at`

**Given** the `ImageGenerationConfig` model in `models.py`
**When** created
**Then** it includes: `enabled`, `image_provider`, `image_model`, `scanner_provider`, `scanner_model`, `scanner_token_limit`

**Given** `config/defaults.yaml`
**When** extended
**Then** it includes an `image_generation` section with defaults for all config fields

**Given** `api/schemas.py`
**When** extended
**Then** `GameConfigResponse` and `GameConfigUpdateRequest` include image generation config fields

**Given** the scene prompt builder
**When** building a prompt from log entries
**Then** it uses a fast LLM (e.g., Gemini Flash) to summarize the narrative into a vivid, visual image prompt (30-50 words) suitable for fantasy art generation

**Given** `pyproject.toml`
**When** updated
**Then** `google-genai` and `Pillow` are added as dependencies

**Technical Notes:**
- Uses same `GEMINI_API_KEY` already configured for game engine
- Prompt builder uses scene context (last N entries + character descriptions) to generate art-style prompts
- Image aspect ratio: 16:9 for landscape scenes

---

### Story 17.3: Current Scene & Specific Turn Image API

As a **user**,
I want **API endpoints to generate images of the current scene or a specific turn**,
So that **the frontend can request scene illustrations on demand**.

**Acceptance Criteria:**

**Given** `POST /api/sessions/{session_id}/images/generate-current`
**When** called
**Then** it extracts the last N log entries (configurable, default 10), builds a scene prompt, generates an image, and returns the `SceneImage` metadata

**Given** `POST /api/sessions/{session_id}/images/generate-turn/{turn_number}`
**When** called with a valid turn number
**Then** it extracts log entries around that turn (context window of +/-5 entries), builds a scene prompt, generates an image, and returns the `SceneImage` metadata

**Given** an invalid turn number (out of range)
**When** the endpoint is called
**Then** it returns HTTP 400 with a clear error message

**Given** `GET /api/sessions/{session_id}/images`
**When** called
**Then** it returns a list of all `SceneImage` metadata for that session

**Given** image generation is in progress
**When** the operation completes
**Then** a WebSocket `image_ready` event is broadcast to all connected clients with the image metadata and download URL

**Given** image generation
**When** executed
**Then** it runs as a background task (not blocking the response) and the REST endpoint returns HTTP 202 Accepted with a task ID

**Given** image generation is disabled in config
**When** any image endpoint is called
**Then** it returns HTTP 400 with message "Image generation is not enabled"

**Technical Notes:**
- Image generation takes 5-15 seconds; must be async/background task
- WebSocket `image_ready` event notifies frontend when image is done
- Reuse existing `engine_registry` pattern from `api/dependencies.py`

---

### Story 17.4: Best Scene Scanner

As a **user**,
I want **the system to analyze my entire session and find the most visually dramatic scene**,
So that **I can generate an illustration of the highlight moment without manually searching**.

**Acceptance Criteria:**

**Given** `POST /api/sessions/{session_id}/images/generate-best`
**When** called
**Then** it uses the configured scanner LLM to analyze the session's ground_truth_log and identify the most visually dramatic/memorable scene

**Given** the scanner LLM
**When** analyzing the session
**Then** it receives a prompt like:
```
Analyze this D&D session log and identify the single most visually dramatic,
memorable, or cinematic scene. Consider: epic battles, dramatic revelations,
beautiful environments, emotional character moments, or magical events.

Return the turn number and a brief description of why this scene is the best
candidate for illustration.
```

**Given** a session with more tokens than the scanner model's context limit
**When** the scanner runs
**Then** it analyzes the log in chunks and selects the best scene from each chunk, then does a final comparison across chunk winners

**Given** the scanner identifies a turn
**When** the best scene is selected
**Then** it passes that turn number to the standard image generation pipeline (same as Story 17.3 specific-turn flow)

**Given** the scanner configuration
**When** set by the user
**Then** they can choose the scanner provider/model (e.g., Gemini 2.5 Pro for its large context window) independently of the text-to-image model

**Given** scanner analysis
**When** running
**Then** it executes as a background task and notifies via WebSocket when complete

**Technical Notes:**
- The scanner is the most complex piece; large context models (Gemini 2.5 Pro at 1M tokens) can handle most sessions in one pass
- For sessions exceeding context limits, chunk into overlapping windows
- Scanner result includes both turn number and rationale (for user transparency)

---

### Story 17.5: Image Generation UI

As a **user**,
I want **a frontend interface for generating, viewing, and managing scene illustrations**,
So that **I can create images of my campaign's best moments directly from the UI**.

**Acceptance Criteria:**

**Given** the session toolbar
**When** rendered
**Then** an "Illustrate" dropdown button appears with options: "Current Scene", "Best Scene", "Turn #...", "View Gallery"

**Given** the user clicks "Illustrate Current Scene"
**When** generation starts
**Then** a loading placeholder appears inline at the top of the narrative ("Painting the scene...") with a progress indicator

**Given** the user clicks "Illustrate Turn #..."
**When** the dialog opens
**Then** a turn number input appears with a preview of the turn's content

**Given** the user clicks a turn number in the narrative
**When** the click is registered
**Then** it triggers image generation for that specific turn (click-to-illustrate shortcut)

**Given** an image generation completes (via WebSocket `image_ready` event)
**When** the frontend receives it
**Then** the image appears inline above the corresponding narrative message, with a download button overlay on hover

**Given** an image is displayed inline
**When** the user hovers over it
**Then** a download button appears in the bottom-right corner of the image

**Given** the user clicks "View Gallery"
**When** the gallery panel opens
**Then** it shows a 2-column grid of all generated images for the session, with turn number, generation mode badge, and per-image download button

**Given** a new `imageStore` in the frontend
**When** created
**Then** it tracks: generated images, generation-in-progress state, and gallery visibility

**Given** keyboard shortcuts
**When** the user presses `I`
**Then** the illustration menu opens

**Given** keyboard shortcuts
**When** the user presses `G`
**Then** the image gallery opens

**Technical Notes:**
- `imageStore` subscribes to WebSocket `image_ready` events
- Images displayed via `<img src="/api/sessions/{id}/images/{image_id}/download">`
- Loading state uses dashed border + amber animation (per UX spec)

---

### Story 17.6: Image Export & Download

As a **user**,
I want **to download individual images and bulk-export all session images**,
So that **I can share campaign illustrations with friends or use them for content**.

**Acceptance Criteria:**

**Given** an image displayed inline in the narrative or gallery
**When** the user clicks the download button
**Then** a browser file download initiates for the PNG image, named `{session_name}_turn_{N}.png`

**Given** `GET /api/sessions/{session_id}/images/{image_id}/download`
**When** called
**Then** it returns the image file with `Content-Disposition: attachment` header and appropriate filename

**Given** the gallery panel
**When** the user clicks "Download All"
**Then** a zip file is generated containing all session images, named `{session_name}_images.zip`

**Given** `GET /api/sessions/{session_id}/images/download-all`
**When** called
**Then** it creates a zip archive of all images in `campaigns/{session}/images/` and returns it as a download

**Given** the campaign directory
**When** images are generated
**Then** they persist in `campaigns/{session}/images/` and are included when loading/restoring sessions

**Given** a session with no generated images
**When** the user clicks "Download All"
**Then** a message indicates "No images to download"

**Technical Notes:**
- Use `zipfile` module for bulk export
- Filename format: `{session_name}_turn_{turn_number}_{mode}.png`
- Images are static files; serve via FastAPI's `FileResponse`

---

### Story 17.7: Enhanced Gallery with Lightbox

As a **user browsing illustrations**,
I want **a modal gallery with thumbnail grid, hover prompts, and full-size lightbox view**,
So that **I can browse, preview, and download my campaign illustrations in a rich visual experience**.

**Acceptance Criteria:**

**Given** the gallery is opened (via `G` shortcut or IllustrateMenu "View Gallery")
**When** displayed
**Then** it opens as a centered modal overlay (80vw x 80vh) with dark backdrop, replacing the current 520px side panel

**Given** the gallery modal body
**When** rendered
**Then** it displays a responsive thumbnail grid (3-4 columns) of square-cropped image previews sorted by turn_number ascending

**Given** a thumbnail in the gallery grid
**When** hovered
**Then** a tooltip appears showing the generation prompt text and formatted timestamp

**Given** a thumbnail card in the gallery grid
**When** rendered
**Then** it shows turn number badge, generation mode badge (current/best/specific), and formatted timestamp

**Given** a thumbnail in the gallery grid
**When** clicked (or Enter pressed while focused)
**Then** a full-screen lightbox overlay opens above the gallery modal with:
- Large image display (max-width/max-height constrained to viewport)
- Download button for the full-resolution PNG
- Metadata panel showing turn number, prompt text, generation mode, timestamp, and model
- Left/right arrow navigation (keyboard arrows + clickable buttons) for prev/next image
- Close via ESC key, backdrop click, or X button

**Given** the lightbox is open
**When** user presses ESC
**Then** the lightbox closes, returning to the gallery grid (not closing the gallery entirely)

**Given** the lightbox is open
**When** user presses Left/Right arrow keys
**Then** the previous/next image is displayed

**Given** the lightbox is open
**When** user presses `D`
**Then** the current image downloads as a full-resolution PNG

**Given** the gallery modal
**When** rendered
**Then** focus is trapped within the modal; all interactive elements have aria-labels

**Given** a session with no illustrations
**When** the gallery opens
**Then** a friendly empty state message is displayed

**Given** the gallery modal header
**When** rendered
**Then** the "Download All" button is present (retained from current implementation)

**Technical Notes:**
- Refactor existing `ImageGallery.svelte` (370 lines) into: `GalleryModal.svelte` (modal wrapper + header), `GalleryGrid.svelte` (thumbnail grid + hover tooltips), `ImageLightbox.svelte` (full-size view + navigation)
- Add `lightboxIndex` store to `imageStore.ts` (number | null — index of currently viewed image, null = lightbox closed)
- Reuse existing `getImageDownloadUrl()` for lightbox download button
- Existing `G` keyboard shortcut and IllustrateMenu "View Gallery" entry point remain unchanged

**FRs:** FR93, FR94

**Dependencies:** Story 17.5 (existing UI), Story 17.6 (existing export)

---

### Story 17.8: Cross-Session Gallery & Adventures Entry Point

As a **user with multiple adventures**,
I want **to browse illustrations across sessions and access the gallery from the adventures list**,
So that **I can revisit campaign artwork without entering each session individually**.

**Acceptance Criteria:**

**Given** the gallery modal header
**When** rendered
**Then** a session switcher dropdown appears showing the current session name

**Given** the session switcher dropdown
**When** opened
**Then** it lists all sessions that have at least one illustration, in format: "Session Name (N images)"

**Given** the session switcher dropdown
**When** a different session is selected
**Then** the gallery loads that session's images via `loadSessionImages(newSessionId)`

**Given** the session switcher dropdown
**When** rendered
**Then** the current session is highlighted/pre-selected

**Given** the API
**When** `GET /api/sessions/images/summary` is called
**Then** it returns `[{session_id: str, session_name: str, image_count: int}]` for all sessions with images

**Given** the adventures list page (`+page.svelte`)
**When** rendered
**Then** each session card that has images shows a gallery icon button with small image count badge (e.g., "12 images")

**Given** a session card on the adventures list
**When** the user clicks the gallery icon button
**Then** the gallery modal opens pre-loaded with that session's images

**Given** the gallery modal component
**When** mounted
**Then** it works on both the game page and adventures list page (shared component)

**Given** the session switcher
**When** used from either entry point
**Then** it can navigate to any session's illustrations regardless of which page the gallery was opened from

**Technical Notes:**
- Add `gallerySessionId` store (string | null) and `sessionImageSummaries` store to `imageStore.ts`
- New API endpoint in `api/routes.py`: scan `campaigns/` directory for sessions with images subdirectory, count JSON metadata files, return lightweight summary
- Update `SessionCard.svelte` to show gallery button + image count badge (conditionally, only when image_count > 0)
- Import and mount `GalleryModal` on adventures list `+page.svelte`
- Session summary data can be fetched once when gallery opens and cached in the store

**FRs:** FR95, FR96, FR97

**Dependencies:** Story 17.7 (enhanced gallery modal must exist first)

---

## Implementation Priority

**Recommended Order:**

1. **Story 17.1** (Turn Number Display) — Frontend-only, no dependencies, quick win
2. **Story 17.2** (Image Generation Service) — Backend foundation, no dependencies
3. **Story 17.3** (Current Scene & Specific Turn API) — Depends on 17.2
4. **Story 17.4** (Best Scene Scanner) — Depends on 17.2
5. **Story 17.5** (Image Generation UI) — Depends on 17.1, 17.3, 17.4
6. **Story 17.6** (Image Export & Download) — Depends on 17.5
7. **Story 17.7** (Enhanced Gallery with Lightbox) — Depends on 17.5, 17.6
8. **Story 17.8** (Cross-Session Gallery & Adventures Entry Point) — Depends on 17.7

**Notes:**
- Stories 17.1 and 17.2 can be developed in parallel
- Stories 17.3 and 17.4 can be developed in parallel (both depend on 17.2)
- Stories 17.7 and 17.8 must be sequential (17.8 builds on 17.7's refactored components)

---

## File Summary

| File | Changes |
|------|---------|
| `image_gen.py` | NEW — Image generation service (google-genai SDK wrapper, prompt builder, scanner) |
| `models.py` | Add `SceneImage`, `ImageGenerationConfig` models |
| `api/routes.py` | Add image generation, listing, download, bulk download endpoints |
| `api/schemas.py` | Extend config models with image generation fields |
| `api/websocket.py` | Add `image_ready` WebSocket event type |
| `config/defaults.yaml` | Add `image_generation` config section |
| `pyproject.toml` | Add `google-genai`, `Pillow` dependencies |
| `frontend/src/lib/components/NarrativeMessage.svelte` | Add turn number to attribution header |
| `frontend/src/lib/components/ImageGenControls.svelte` | NEW — Illustration dropdown menu |
| `frontend/src/lib/components/SceneImage.svelte` | NEW — Inline image display with download |
| `frontend/src/lib/components/ImageGallery.svelte` | NEW — Gallery panel |
| `frontend/src/lib/stores/imageStore.ts` | NEW — Image state management |
| `frontend/src/lib/narrative.ts` | Extend `ParsedMessage` with turn number |
| `tests/test_image_gen.py` | NEW — Image generation service tests (mocked API) |
| `frontend/src/lib/components/__tests__/` | New tests for image components |
