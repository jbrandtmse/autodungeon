# Story 17-6: Image Export & Download

**Epic:** 17 — AI Scene Image Generation
**Status:** review-complete
**Depends On:** 17-3 (Current Scene & Specific Turn API) — DONE, 17-5 (Image Generation UI) — DONE

---

## Story

As a **user**,
I want **to download individual images and bulk-export all session images**,
So that **I can share campaign illustrations with friends or use them for content**.

---

## Acceptance Criteria

### AC1: Individual Image Download Button

**Given** an image displayed inline in the narrative or gallery
**When** the user clicks the download button
**Then** a browser file download initiates for the PNG image, named `{session_name}_turn_{N}.png`

### AC2: Individual Image Download API Endpoint

**Given** `GET /api/sessions/{session_id}/images/{image_id}/download`
**When** called
**Then** it returns the image file with `Content-Disposition: attachment` header and appropriate filename

### AC3: Download All Button in Gallery

**Given** the gallery panel
**When** the user clicks "Download All"
**Then** a zip file is generated containing all session images, named `{session_name}_images.zip`

### AC4: Download All API Endpoint

**Given** `GET /api/sessions/{session_id}/images/download-all`
**When** called
**Then** it creates a zip archive of all images in `campaigns/{session}/images/` and returns it as a download

### AC5: Image Persistence in Campaign Directory

**Given** the campaign directory
**When** images are generated
**Then** they persist in `campaigns/{session}/images/` and are included when loading/restoring sessions

### AC6: Empty Session Download All

**Given** a session with no generated images
**When** the user clicks "Download All"
**Then** a message indicates "No images to download"

---

## Tasks / Subtasks

- [x] **Task 1: Add backend individual download endpoint with Content-Disposition** (AC: 1, 2)
  - [x] 1.1: Add `GET /api/sessions/{session_id}/images/{image_id}/download` route in `api/routes.py`
  - [x] 1.2: Validate `image_id` format using existing `_IMAGE_FILENAME_RE` pattern (UUID format)
  - [x] 1.3: Load session metadata to resolve session name for the filename
  - [x] 1.4: Return `FileResponse` with `Content-Disposition: attachment; filename="{session_name}_turn_{N}.png"` header
  - [x] 1.5: Load image metadata JSON sidecar to get `turn_number` for filename construction
  - [x] 1.6: Sanitize session name for filesystem safety (replace non-alphanumeric chars with underscores)

- [x] **Task 2: Add backend bulk download (zip) endpoint** (AC: 3, 4, 6)
  - [x] 2.1: Add `GET /api/sessions/{session_id}/images/download-all` route in `api/routes.py` (must be registered BEFORE the `{image_filename}` catch-all route)
  - [x] 2.2: Scan `campaigns/session_{id}/images/` for `.png` files
  - [x] 2.3: Return HTTP 404 with `detail: "No images to download"` if no PNG files found
  - [x] 2.4: Create zip archive in-memory using `zipfile.ZipFile` with `io.BytesIO`
  - [x] 2.5: For each image, load its JSON sidecar metadata to get `turn_number` and `generation_mode` for the archive filename
  - [x] 2.6: Archive filename format: `{session_name}_turn_{turn_number}_{mode}.png`
  - [x] 2.7: Return `StreamingResponse` (or `Response`) with `Content-Disposition: attachment; filename="{session_name}_images.zip"` and `media_type="application/zip"`
  - [x] 2.8: Sanitize session name for filename safety

- [x] **Task 3: Update frontend individual download to use new endpoint** (AC: 1, 2)
  - [x] 3.1: Add `getImageDownloadUrl(sessionId: string, imageId: string): string` helper in `api.ts` that returns the download endpoint URL
  - [x] 3.2: Update `SceneImage.svelte` download `<a>` tag to use the new download URL (with `Content-Disposition`) instead of the inline serve URL
  - [x] 3.3: Update `ImageGallery.svelte` per-card download button similarly
  - [x] 3.4: The `download` attribute on `<a>` combined with `Content-Disposition: attachment` ensures proper filename

- [x] **Task 4: Add "Download All" button to ImageGallery.svelte** (AC: 3, 6)
  - [x] 4.1: Add a "Download All" button in the gallery header, next to the gallery title
  - [x] 4.2: Button triggers a direct download via `window.location.href` or `<a>` pointing to `/api/sessions/{id}/images/download-all`
  - [x] 4.3: Show loading state while zip is being generated (disable button, show spinner text)
  - [x] 4.4: Handle the "no images" case: if `$images.length === 0`, disable the button with tooltip "No images to download"
  - [x] 4.5: Handle HTTP 404 response from download-all endpoint gracefully (show inline error message)
  - [x] 4.6: Style button to match gallery header design (`.gallery-download-all-btn`)

- [x] **Task 5: Add frontend API function for download-all** (AC: 3, 4)
  - [x] 5.1: Add `getDownloadAllUrl(sessionId: string): string` helper in `api.ts` that returns the bulk download endpoint URL
  - [x] 5.2: This is a URL builder only (not a `request<T>()` call) because file downloads use native browser fetch via `<a>` or `window.location`

- [x] **Task 6: Write backend tests** (AC: 2, 4, 6)
  - [x] 6.1: Test individual download endpoint returns `Content-Disposition: attachment` header
  - [x] 6.2: Test individual download with valid image_id returns PNG file
  - [x] 6.3: Test individual download with invalid image_id returns 400
  - [x] 6.4: Test individual download with non-existent image_id returns 404
  - [x] 6.5: Test bulk download endpoint returns zip file with correct content type
  - [x] 6.6: Test bulk download with images returns zip containing all PNGs with correct filenames
  - [x] 6.7: Test bulk download with no images returns 404 with "No images to download"
  - [x] 6.8: Test filename sanitization (session names with spaces, special characters)
  - [x] 6.9: Run `python -m pytest tests/` — no regressions

- [x] **Task 7: Write frontend tests** (AC: 1, 3, 6)
  - [x] 7.1: Update `ImageGallery.test.ts` — "Download All" button rendered, disabled when no images
  - [x] 7.2: Update `SceneImage.test.ts` — download button uses download endpoint URL
  - [x] 7.3: Test `getImageDownloadUrl()` and `getDownloadAllUrl()` URL builders
  - [x] 7.4: Run `cd frontend && npm run test` — no regressions
  - [x] 7.5: Run `cd frontend && npm run check` — no type errors

- [x] **Task 8: Visual verification** (AC: all)
  - [x] 8.1: Navigate to a session with generated images and verify download button on inline images triggers download with correct filename
  - [x] 8.2: Open gallery and verify per-image download buttons work
  - [x] 8.3: Click "Download All" in gallery and verify a zip file downloads with all session images
  - [x] 8.4: Open an empty session gallery and verify "Download All" is disabled
  - [x] 8.5: Verify zip file contents have correct filenames matching `{session_name}_turn_{N}_{mode}.png`

---

## Dev Notes

### Architecture Context

This story adds export/download capabilities to the existing image generation system. Stories 17-2 through 17-5 established:
- Image generation service (`image_gen.py`) saving PNGs to `campaigns/session_{id}/images/{uuid}.png`
- JSON sidecar metadata files at `campaigns/session_{id}/images/{uuid}.json`
- Inline image serve endpoint at `GET /api/sessions/{id}/images/{uuid}.png` (returns `FileResponse` without `Content-Disposition`)
- Frontend `SceneImage.svelte` with a hover-reveal download button using `<a href={image.download_url} download>`
- Frontend `ImageGallery.svelte` with per-image download buttons

The current download behavior relies on the browser's `download` attribute on `<a>` tags pointing to the inline serve URL. This has two problems:
1. The filename defaults to `{uuid}.png` (not user-friendly)
2. Some browsers ignore the `download` attribute for cross-origin or API-served URLs

This story adds proper `Content-Disposition: attachment` headers with descriptive filenames and a bulk zip export.

### Backend: Individual Image Download Endpoint

Add a new route that wraps the existing image serve logic but adds `Content-Disposition: attachment`:

```python
# api/routes.py — NEW endpoint

@router.get("/sessions/{session_id}/images/{image_id}/download")
async def download_session_image(session_id: str, image_id: str) -> Any:
    """Download a generated image with a descriptive filename.

    Returns the PNG file with Content-Disposition: attachment header
    so the browser initiates a file download with a user-friendly filename.

    Args:
        session_id: Session ID string.
        image_id: Image UUID string (without .png extension).

    Returns:
        FileResponse with attachment disposition.
    """
    from fastapi.responses import FileResponse

    _validate_and_check_session(session_id)

    # Validate image_id format (UUID without extension)
    if not _IMAGE_ID_RE.match(image_id):
        raise HTTPException(status_code=400, detail="Invalid image ID format")

    images_dir = get_session_dir(session_id) / "images"
    image_path = images_dir / f"{image_id}.png"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    # Load metadata sidecar for turn number and mode
    metadata_path = images_dir / f"{image_id}.json"
    turn_number = 0
    generation_mode = "scene"
    if metadata_path.exists():
        try:
            data = _json.loads(metadata_path.read_text(encoding="utf-8"))
            turn_number = data.get("turn_number", 0)
            generation_mode = data.get("generation_mode", "scene")
        except (KeyError, ValueError, OSError):
            pass  # Use defaults

    # Build descriptive filename
    session_name = _get_safe_session_name(session_id)
    filename = f"{session_name}_turn_{turn_number + 1}_{generation_mode}.png"

    return FileResponse(
        str(image_path),
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

A new regex constant for image ID validation (UUID without `.png` extension):

```python
_IMAGE_ID_RE = _re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
```

### Backend: Session Name Sanitization Helper

```python
def _get_safe_session_name(session_id: str) -> str:
    """Get a filesystem-safe session name for download filenames.

    Loads session metadata name; falls back to "session_{id}".
    Replaces non-alphanumeric characters (except hyphens/underscores) with underscores.
    Truncates to 50 characters to prevent overly long filenames.

    Args:
        session_id: Session ID string.

    Returns:
        Sanitized session name string.
    """
    metadata = load_session_metadata(session_id)
    name = (metadata.name if metadata and metadata.name else f"session_{session_id}")
    # Replace unsafe filesystem characters
    safe = _re.sub(r"[^\w\-]", "_", name)
    # Collapse multiple underscores
    safe = _re.sub(r"_+", "_", safe).strip("_")
    return safe[:50] if safe else f"session_{session_id}"
```

### Backend: Bulk Download (Zip) Endpoint

```python
# api/routes.py — NEW endpoint
# IMPORTANT: This route MUST be registered BEFORE the
# "/sessions/{session_id}/images/{image_filename}" catch-all route
# to prevent FastAPI from matching "download-all" as an {image_filename}.

@router.get("/sessions/{session_id}/images/download-all")
async def download_all_session_images(session_id: str) -> Any:
    """Download all generated images for a session as a zip archive.

    Creates an in-memory zip file containing all PNG images from the
    session's images directory, with descriptive filenames derived from
    the JSON sidecar metadata.

    Args:
        session_id: Session ID string.

    Returns:
        Response with zip file as attachment.
    """
    import io
    import zipfile

    from fastapi.responses import Response

    _validate_and_check_session(session_id)

    images_dir = get_session_dir(session_id) / "images"
    if not images_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="No images to download",
        )

    png_files = sorted(images_dir.glob("*.png"))
    if not png_files:
        raise HTTPException(
            status_code=404,
            detail="No images to download",
        )

    session_name = _get_safe_session_name(session_id)
    zip_filename = f"{session_name}_images.zip"

    # Build zip in memory
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for png_path in png_files:
            # Derive archive filename from sidecar metadata
            image_id = png_path.stem
            metadata_path = images_dir / f"{image_id}.json"

            turn_number = 0
            generation_mode = "scene"
            if metadata_path.exists():
                try:
                    data = _json.loads(
                        metadata_path.read_text(encoding="utf-8")
                    )
                    turn_number = data.get("turn_number", 0)
                    generation_mode = data.get("generation_mode", "scene")
                except (KeyError, ValueError, OSError):
                    pass

            # Filename inside the zip: session_turn_N_mode.png
            archive_name = (
                f"{session_name}_turn_{turn_number + 1}_{generation_mode}.png"
            )
            zf.write(str(png_path), archive_name)

    buffer.seek(0)

    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"',
        },
    )
```

### Route Registration Order

The `download-all` and `{image_id}/download` routes MUST be registered BEFORE the existing `{image_filename}` catch-all route in `api/routes.py`. FastAPI matches routes in registration order, and `download-all` would otherwise be captured by `{image_filename}`.

Current order:
```
POST /sessions/{session_id}/images/generate-current
POST /sessions/{session_id}/images/generate-turn/{turn_number}
POST /sessions/{session_id}/images/generate-best
GET  /sessions/{session_id}/images                       # list
GET  /sessions/{session_id}/images/{image_filename}       # serve inline
```

New order:
```
POST /sessions/{session_id}/images/generate-current
POST /sessions/{session_id}/images/generate-turn/{turn_number}
POST /sessions/{session_id}/images/generate-best
GET  /sessions/{session_id}/images                       # list
GET  /sessions/{session_id}/images/download-all           # NEW: bulk zip
GET  /sessions/{session_id}/images/{image_id}/download    # NEW: individual
GET  /sessions/{session_id}/images/{image_filename}       # serve inline (catch-all)
```

### Frontend: Download URL Helpers (`api.ts`)

These are URL builders (not `request<T>()` calls) since file downloads use native browser mechanisms:

```typescript
// api.ts — NEW functions

/**
 * Build the URL for downloading an individual image with Content-Disposition.
 * Used as href for download <a> tags.
 */
export function getImageDownloadUrl(sessionId: string, imageId: string): string {
    return `/api/sessions/${encodeURIComponent(sessionId)}/images/${encodeURIComponent(imageId)}/download`;
}

/**
 * Build the URL for downloading all session images as a zip archive.
 * Used as href for the "Download All" button.
 */
export function getDownloadAllUrl(sessionId: string): string {
    return `/api/sessions/${encodeURIComponent(sessionId)}/images/download-all`;
}
```

### Frontend: SceneImage.svelte Update

Change the download `<a>` tag to use the new download endpoint URL instead of the inline serve URL:

```svelte
<!-- Before (serves image inline, browser guesses filename): -->
<a href={image.download_url} download ...>

<!-- After (backend sets Content-Disposition with proper filename): -->
<a href={getImageDownloadUrl(image.session_id, image.id)} download ...>
```

Import `getImageDownloadUrl` from `$lib/api`.

### Frontend: ImageGallery.svelte Update — "Download All" Button

Add a "Download All" button to the gallery header:

```svelte
<script lang="ts">
    import { getImageDownloadUrl, getDownloadAllUrl } from '$lib/api';
    // ... existing imports

    // Derive session_id from images (all images share the same session_id)
    const sessionId = $derived($images.length > 0 ? $images[0].session_id : '');
    const hasImages = $derived($images.length > 0);
</script>

<header class="gallery-header">
    <h3 class="gallery-title">Scene Gallery</h3>
    <div class="gallery-header-actions">
        {#if hasImages}
            <a
                class="gallery-download-all-btn"
                href={getDownloadAllUrl(sessionId)}
                download
                aria-label="Download all images as zip"
            >
                <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
                    <path d="M8 1v10M4 8l4 4 4-4M2 14h12" stroke="currentColor"
                        stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
                        fill="none" />
                </svg>
                Download All
            </a>
        {:else}
            <span class="gallery-download-all-btn disabled" title="No images to download">
                Download All
            </span>
        {/if}
        <button class="gallery-close-btn" onclick={close} aria-label="Close gallery">
            ...
        </button>
    </div>
</header>
```

Also update per-card download button to use the proper download URL:

```svelte
<a
    class="gallery-download-btn"
    href={getImageDownloadUrl(img.session_id, img.id)}
    download
    aria-label="Download image for Turn {img.turn_number + 1}"
>
```

### CSS for Download All Button

```css
.gallery-header-actions {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
}

.gallery-download-all-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    background: rgba(232, 168, 73, 0.15);
    color: var(--accent-warm);
    border: 1px solid rgba(232, 168, 73, 0.3);
    border-radius: var(--border-radius-sm);
    font-family: var(--font-ui);
    font-size: 12px;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
    transition: background var(--transition-fast), border-color var(--transition-fast);
}

.gallery-download-all-btn:hover {
    background: rgba(232, 168, 73, 0.25);
    border-color: rgba(232, 168, 73, 0.5);
    text-decoration: none;
}

.gallery-download-all-btn:focus-visible {
    outline: 2px solid var(--accent-warm);
    outline-offset: 2px;
}

.gallery-download-all-btn.disabled {
    opacity: 0.4;
    cursor: not-allowed;
    pointer-events: none;
}
```

### Filename Conventions

| Context | Format | Example |
|---------|--------|---------|
| Individual download | `{session_name}_turn_{N}_{mode}.png` | `Curse_of_Strahd_turn_42_current.png` |
| Zip archive name | `{session_name}_images.zip` | `Curse_of_Strahd_images.zip` |
| Files inside zip | `{session_name}_turn_{N}_{mode}.png` | `Curse_of_Strahd_turn_42_current.png` |

Turn number `N` is 1-based (display number), matching the UI convention throughout the project. The backend converts from 0-based `turn_number` stored in metadata via `turn_number + 1`.

Session name is derived from `SessionMetadata.name`. If empty/blank, falls back to `session_{id}` (e.g., `session_001`).

### Image Persistence (AC5)

This AC is already satisfied by the existing implementation from Story 17-2/17-3. Images are saved to `campaigns/session_{id}/images/{uuid}.png` with JSON sidecar metadata. Session load/restore preserves the images directory. No additional work needed for this AC.

### Error Handling

| Scenario | HTTP Status | Response |
|----------|-------------|----------|
| Invalid `image_id` format | 400 | `"Invalid image ID format"` |
| Image not found | 404 | `"Image not found"` |
| Session not found | 404 | `"Session '{id}' not found"` |
| No images for download-all | 404 | `"No images to download"` |
| Invalid session ID format | 400 | `"Invalid session ID: {id}"` |

Frontend handles the "no images" case proactively by disabling the "Download All" button when `$images.length === 0`, so users should not normally hit the 404 from the API. The API check is a defensive backend guard.

### Zip Archive Considerations

- **In-memory zip creation:** Uses `io.BytesIO` buffer. Session image sets are typically small (< 50 images, < 100MB total). For extremely large sessions, a streaming approach with `tempfile` could be used, but in-memory is simpler and sufficient for expected usage.
- **Compression:** `ZIP_DEFLATED` provides compression. PNGs are already compressed, so the zip overhead is minimal, but the zip format adds the convenience of a single-file download.
- **Duplicate filenames:** If two images have the same turn number and mode (e.g., user regenerated an image), the zip will only contain the last one. This is acceptable since the UUID-based storage prevents actual data loss -- both images remain on disk.
- **Thread safety:** The endpoint reads files synchronously within an async handler. For very large sessions, consider offloading to `asyncio.to_thread()`. For typical usage (< 50 images), this is not necessary.

### Common Pitfalls to Avoid

1. **Route registration order is critical.** The `download-all` route MUST be registered before `{image_filename}` in `routes.py`. Otherwise FastAPI will match `download-all` as a filename parameter and return 400 (invalid image filename format). Verify by checking that `GET /api/sessions/001/images/download-all` hits the zip endpoint, not the serve endpoint.
2. **Do NOT confuse `image_id` (UUID without extension) with `image_filename` (UUID.png with extension).** The new download endpoint takes `image_id` (no `.png`), while the existing serve endpoint takes `image_filename` (with `.png`).
3. **Turn numbers in filenames are 1-based.** The metadata stores 0-based `turn_number`. Always add 1 for display/filenames: `turn_number + 1`.
4. **Sanitize session names for filenames.** Session names may contain spaces, quotes, slashes, and Unicode. The `_get_safe_session_name()` helper replaces unsafe characters with underscores.
5. **Do NOT use `StreamingResponse` for zip download.** Since the zip is built in-memory (need to seek back to start), use `Response` with the buffer's bytes. `StreamingResponse` expects an iterator/generator and would not work with the completed BytesIO buffer without extra wrapping.
6. **The `download` attribute on `<a>` tags is still useful** even with `Content-Disposition: attachment`. It signals the browser that this is a download link (not navigation), and some browsers use it as a filename hint. Keep both mechanisms for maximum compatibility.

### References

- [Source: `api/routes.py` — `serve_session_image()`, `list_session_images()`, `_build_download_url()`, `_IMAGE_FILENAME_RE`, `_validate_and_check_session()`]
- [Source: `api/schemas.py` — `SceneImageResponse`]
- [Source: `persistence.py` — `get_session_dir()`, `load_session_metadata()`, `SessionMetadata`]
- [Source: `image_gen.py` — `generate_scene_image()` saves PNGs to `images/` subdir, `_save_image_to_disk()`]
- [Source: `models.py` — `SceneImage`, `SessionMetadata`]
- [Source: `frontend/src/lib/components/SceneImage.svelte` — existing download button using `<a download>`]
- [Source: `frontend/src/lib/components/ImageGallery.svelte` — gallery panel with per-image download buttons]
- [Source: `frontend/src/lib/api.ts` — `getSessionImages()`, `request<T>()` helper]
- [Source: `frontend/src/lib/stores/imageStore.ts` — `images` store]
- [Source: `_bmad-output/implementation-artifacts/17-5-image-generation-ui.md` — Story format reference]

---

## File List

| File | Action | Description |
|------|--------|-------------|
| `api/routes.py` | Modified | Add `download_session_image()` and `download_all_session_images()` endpoints, `_IMAGE_ID_RE` constant, `_get_safe_session_name()` helper; reorder image routes |
| `frontend/src/lib/api.ts` | Modified | Add `getImageDownloadUrl()` and `getDownloadAllUrl()` URL builder functions |
| `frontend/src/lib/components/SceneImage.svelte` | Modified | Update download button href to use download endpoint URL via `getImageDownloadUrl()` |
| `frontend/src/lib/components/ImageGallery.svelte` | Modified | Add "Download All" button in header; update per-card download hrefs; add `.gallery-download-all-btn` and `.gallery-header-actions` CSS |
| `tests/test_image_api.py` | Modified | Add `TestDownloadSessionImage` (6 tests), `TestDownloadAllSessionImages` (7 tests), helper tests for `_IMAGE_ID_RE` and `_get_safe_session_name` (4 tests) |
| `frontend/src/lib/components/ImageGallery.test.ts` | Modified | Add tests for "Download All" button rendering, disabled state, download URL, and header actions container |
| `frontend/src/lib/components/SceneImage.test.ts` | Modified | Update download button test to verify new download endpoint URL |
| `frontend/src/lib/api.test.ts` | Modified | Add tests for `getImageDownloadUrl()` and `getDownloadAllUrl()` URL builders |

---

## Code Review

**Reviewer:** Claude Opus 4.6 (adversarial review)
**Date:** 2026-02-14
**Result:** PASS with fixes applied (7 issues found, 5 HIGH/MEDIUM auto-resolved, 2 LOW documented)

### Issues Found

#### Issue 1: [HIGH] Duplicate filenames in zip silently overwrite entries — FIXED
- **File:** `api/routes.py` (download_all_session_images)
- **Problem:** When multiple images share the same turn_number and generation_mode, they produce identical archive filenames. `zipfile.ZipFile.write()` silently overwrites earlier entries, causing data loss in the zip.
- **Fix:** Added `used_names: set[str]` tracker with deduplication counter (appends `_2`, `_3`, etc.) when collisions occur. Added test `test_download_all_deduplicates_filenames`.

#### Issue 2: [HIGH] Session name sanitizer allows Unicode through `\w` — FIXED
- **File:** `api/routes.py` (_get_safe_session_name)
- **Problem:** Python's `\w` in regex matches Unicode word characters (accented letters, CJK, etc.), which would pass through unsanitized into Content-Disposition `filename=` parameter without RFC 5987 encoding. Non-ASCII filenames in the basic `filename=` parameter violate HTTP standards and cause interoperability issues across browsers.
- **Fix:** Changed regex from `[^\w\-]` to `[^A-Za-z0-9_\-]` to restrict to ASCII-only characters.

#### Issue 3: [MEDIUM] Synchronous file I/O blocks event loop in async handler — FIXED
- **File:** `api/routes.py` (download_all_session_images)
- **Problem:** The `async def` handler performs synchronous operations (glob, read_text, zipfile.write) directly on the event loop. FastAPI only auto-wraps `def` handlers in threads, not `async def`. For sessions with many images, this blocks the event loop.
- **Fix:** Extracted zip-building logic into a `_build_zip()` closure and wrapped it with `await asyncio.to_thread(_build_zip)`.

#### Issue 4: [MEDIUM] generation_mode from metadata not validated before filename use — FIXED
- **File:** `api/routes.py` (both download endpoints)
- **Problem:** `generation_mode` is read from JSON sidecar metadata and interpolated directly into filenames and Content-Disposition headers without validation. Corrupted or manually-edited metadata could inject arbitrary strings.
- **Fix:** Added `_VALID_GENERATION_MODES` frozenset constant and validation in both endpoints: unknown modes fall back to "scene".

#### Issue 5: [MEDIUM] turn_number from metadata not type-validated — FIXED
- **File:** `api/routes.py` (both download endpoints)
- **Problem:** `data.get("turn_number", 0)` returns whatever type is in JSON (could be string, null, float). The subsequent `+ 1` arithmetic would raise `TypeError` for non-numeric values. The default `0` only applies when the key is absent, not for non-integer values.
- **Fix:** Wrapped with `int()` cast and added `TypeError` to exception handlers.

#### Issue 6: [LOW] No test for invalid generation_mode fallback — NOT FIXED (test gap, low priority)
- **File:** `tests/test_image_api.py`
- **Problem:** No test verifies that an unrecognized `generation_mode` in metadata falls back to "scene". The validation logic was added but not test-covered.

#### Issue 7: [LOW] ZIP_DEFLATED on already-compressed PNGs adds CPU overhead with no size benefit — NOT FIXED (acceptable)
- **File:** `api/routes.py` (download_all_session_images)
- **Problem:** PNG files are already compressed. Using `ZIP_DEFLATED` wastes CPU cycles attempting to re-compress them. `ZIP_STORED` would be faster with identical final size.
- **Impact:** Negligible for typical session sizes (<50 images). Would matter for very large sessions.

### Test Results After Fixes
- **Backend:** `python -m pytest tests/test_image_api.py -v` -- 53 passed (including new deduplication test)
- **Frontend:** `npx vitest run` -- 189 passed across 19 test files
