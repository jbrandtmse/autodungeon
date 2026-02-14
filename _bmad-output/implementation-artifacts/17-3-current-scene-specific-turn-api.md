# Story 17-3: Current Scene & Specific Turn Image API

**Epic:** 17 — AI Scene Image Generation
**Status:** review
**Depends On:** 17-2 (Image Generation Service) — DONE

---

## Story

As a **user**,
I want **API endpoints to generate images of the current scene or a specific turn**,
So that **the frontend can request scene illustrations on demand**.

---

## Acceptance Criteria

### AC1: Generate Current Scene Image

**Given** `POST /api/sessions/{session_id}/images/generate-current`
**When** called
**Then** it extracts the last N log entries (configurable, default 10), builds a scene prompt, generates an image, and returns HTTP 202 Accepted with a task ID

### AC2: Generate Specific Turn Image

**Given** `POST /api/sessions/{session_id}/images/generate-turn/{turn_number}`
**When** called with a valid turn number
**Then** it extracts log entries around that turn (context window of +/-5 entries), builds a scene prompt, generates an image, and returns HTTP 202 Accepted with a task ID

### AC3: Invalid Turn Number

**Given** an invalid turn number (out of range)
**When** the endpoint is called
**Then** it returns HTTP 400 with a clear error message

### AC4: List Session Images

**Given** `GET /api/sessions/{session_id}/images`
**When** called
**Then** it returns a list of all `SceneImage` metadata for that session

### AC5: WebSocket Image Ready Event

**Given** image generation is in progress
**When** the operation completes
**Then** a WebSocket `image_ready` event is broadcast to all connected clients with the image metadata and download URL

### AC6: Background Task Execution

**Given** image generation
**When** executed
**Then** it runs as a background task (not blocking the response) and the REST endpoint returns HTTP 202 Accepted with a task ID

### AC7: Image Generation Disabled

**Given** image generation is disabled in config
**When** any image endpoint is called
**Then** it returns HTTP 400 with message "Image generation is not enabled"

---

## Tasks / Subtasks

- [x] **Task 1: Add API schemas to `api/schemas.py`** (AC: 1, 2, 4, 5, 6)
  - [x] 1.1: Add `ImageGenerateRequest` model with optional `context_entries` field (int, default 10, ge=1, le=50)
  - [x] 1.2: Add `ImageGenerateAccepted` response model with fields: `task_id` (str, UUID), `session_id` (str), `turn_number` (int), `status` (Literal["pending"])
  - [x] 1.3: Add `SceneImageResponse` model mirroring `SceneImage` fields: `id`, `session_id`, `turn_number`, `prompt`, `image_path`, `provider`, `model`, `generation_mode`, `generated_at`, plus `download_url` (str)
  - [x] 1.4: Add `WsImageReady` WebSocket event model with fields: `type` (Literal["image_ready"]), `image` (SceneImageResponse)

- [x] **Task 2: Add image route handlers to `api/routes.py`** (AC: 1, 2, 3, 4, 6, 7)
  - [x] 2.1: Add `POST /api/sessions/{session_id}/images/generate-current` endpoint that:
    - Validates session exists and image generation is enabled
    - Loads game state from latest checkpoint
    - Extracts last N log entries (from request body or default 10)
    - Creates a UUID task ID
    - Launches background task via `asyncio.create_task`
    - Returns HTTP 202 with `ImageGenerateAccepted` response
  - [x] 2.2: Add `POST /api/sessions/{session_id}/images/generate-turn/{turn_number}` endpoint that:
    - Validates session exists, image generation is enabled, and turn number is valid
    - Loads game state from latest checkpoint
    - Validates turn_number is within log range (0 to len(log)-1)
    - Extracts context window of +/-5 entries around the turn
    - Creates a UUID task ID
    - Launches background task via `asyncio.create_task`
    - Returns HTTP 202 with `ImageGenerateAccepted` response
  - [x] 2.3: Add `GET /api/sessions/{session_id}/images` endpoint that:
    - Validates session exists
    - Scans `campaigns/session_{id}/images/` for existing images
    - Loads image metadata from JSON sidecar files
    - Returns list of `SceneImageResponse` with download URLs
  - [x] 2.4: Add helper `_check_image_generation_enabled()` that reads config and raises HTTP 400 if disabled
  - [x] 2.5: Add helper `_build_download_url(session_id, image_path)` to construct the download URL for an image

- [x] **Task 3: Implement background image generation task** (AC: 1, 2, 5, 6)
  - [x] 3.1: Create async function `_generate_image_background(session_id, task_id, log_entries, characters, turn_number, generation_mode, app)` that:
    - Instantiates `ImageGenerator`
    - Calls `build_scene_prompt()` with log entries and characters
    - Calls `generate_scene_image()` with the built prompt
    - Saves image metadata as JSON sidecar file alongside the PNG
    - Broadcasts `image_ready` WebSocket event via `ConnectionManager.broadcast()`
    - Catches and logs errors without crashing the server
  - [x] 3.2: Store image metadata as `{image_id}.json` sidecar in `campaigns/session_{id}/images/`

- [x] **Task 4: Add WebSocket `image_ready` event support** (AC: 5)
  - [x] 4.1: Add `WsImageReady` to `_engine_event_to_schema()` mapping in `api/websocket.py`
  - [x] 4.2: Import `WsImageReady` in `api/websocket.py`

- [x] **Task 5: Add static file serving for generated images** (AC: 4, 5)
  - [x] 5.1: Add `GET /api/sessions/{session_id}/images/{image_id}.png` endpoint (or mount a static file route) to serve generated image files from the `campaigns/` directory
  - [x] 5.2: Validate `image_id` format (UUID pattern) to prevent path traversal

- [x] **Task 6: Write tests** (AC: all)
  - [x] 6.1: Add `tests/test_image_api.py` with unit tests for all new endpoints:
    - Test `POST /generate-current` returns 202 with task_id
    - Test `POST /generate-current` returns 400 when image generation disabled
    - Test `POST /generate-turn/{turn}` returns 202 with valid turn
    - Test `POST /generate-turn/{turn}` returns 400 with out-of-range turn
    - Test `GET /images` returns empty list for session with no images
    - Test `GET /images` returns metadata for sessions with images
    - Test session validation (404 for non-existent session)
  - [x] 6.2: Add tests for WebSocket `image_ready` event schema
  - [x] 6.3: Add tests for `ImageGenerateAccepted` and `SceneImageResponse` schemas
  - [x] 6.4: Add tests for background task error handling (image gen failure does not crash server)
  - [x] 6.5: Run full test suite: `python -m pytest` -- no regressions

- [x] **Task 7: Verification** (AC: all)
  - [x] 7.1: Run `python -m ruff check .` -- no new violations
  - [x] 7.2: Run `python -m ruff format --check .` -- formatting passes
  - [x] 7.3: Verify endpoints appear in FastAPI docs at `http://localhost:8000/docs`
  - [x] 7.4: Manual test: POST to generate-current and verify 202 response with task_id

---

## Dev Notes

### Architecture Context

This story adds REST API endpoints that bridge the `ImageGenerator` service (Story 17-2) to the frontend. The key architectural challenge is that image generation takes 5-15 seconds, so it must run as a background task to avoid blocking the HTTP response. The flow is:

1. Client sends POST request to generate an image
2. Server validates inputs, returns HTTP 202 Accepted with a task ID immediately
3. Background `asyncio.create_task` runs `build_scene_prompt()` + `generate_scene_image()`
4. On completion, a WebSocket `image_ready` event is broadcast to all connected clients
5. Client can also poll `GET /images` to see all generated images

### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `api/schemas.py` | Modified | Add `ImageGenerateRequest`, `ImageGenerateAccepted`, `SceneImageResponse`, `WsImageReady` schemas |
| `api/routes.py` | Modified | Add image generation endpoints (3 routes + helpers) |
| `api/websocket.py` | Modified | Add `image_ready` event to `_engine_event_to_schema()` mapping |
| `api/main.py` | Modified | Mount static file serving for `campaigns/` images (if using StaticFiles approach) |
| `tests/test_image_api.py` | Created | Tests for all new endpoints |
| `tests/test_api.py` | Modified | Tests for new schemas |

### New API Schema Definitions (`api/schemas.py`)

Add these schemas after the existing `SessionStartRequest` class (at the end of the file, before the WebSocket schemas section):

```python
# =============================================================================
# Image Generation Schemas (Story 17-3)
# =============================================================================


class ImageGenerateRequest(BaseModel):
    """Optional request body for image generation endpoints."""

    context_entries: int = Field(
        default=10, ge=1, le=50,
        description="Number of log entries to use for scene context",
    )


class ImageGenerateAccepted(BaseModel):
    """Response for accepted (202) image generation requests."""

    task_id: str = Field(..., description="Background task ID (UUID)")
    session_id: str = Field(..., description="Session ID")
    turn_number: int = Field(..., ge=0, description="Turn number being illustrated")
    status: Literal["pending"] = Field(
        default="pending", description="Task status"
    )


class SceneImageResponse(BaseModel):
    """Response model for a generated scene image."""

    id: str = Field(..., description="Unique image ID (UUID)")
    session_id: str = Field(..., description="Session this image belongs to")
    turn_number: int = Field(..., ge=0, description="Turn number illustrated")
    prompt: str = Field(..., description="Text prompt used for generation")
    image_path: str = Field(
        ..., description="Relative path to image file within campaigns/"
    )
    provider: str = Field(..., description="Image generation provider")
    model: str = Field(..., description="Image generation model name")
    generation_mode: Literal["current", "best", "specific"] = Field(
        ..., description="How the image was requested"
    )
    generated_at: str = Field(..., description="ISO timestamp of generation")
    download_url: str = Field(..., description="URL to download the image")
```

Add the WebSocket event model in the WebSocket schemas section:

```python
class WsImageReady(BaseModel):
    """Image generation completed, broadcast to all connected clients."""

    type: Literal["image_ready"] = "image_ready"
    image: SceneImageResponse = Field(
        ..., description="Generated image metadata with download URL"
    )
```

### Route Handler Patterns (`api/routes.py`)

Add a new section after the Character Sheet Endpoint section. Follow the existing patterns:

**Section header:**
```python
# =============================================================================
# Image Generation Endpoints (Story 17-3)
# =============================================================================
```

**Imports to add at top of `api/routes.py`:**
```python
import uuid as _uuid  # For task_id generation (avoid conflict with uuid in models)

# Add to the from api.schemas import block:
from api.schemas import (
    ImageGenerateAccepted,
    ImageGenerateRequest,
    SceneImageResponse,
)
```

**Helper: Check image generation enabled:**
```python
def _check_image_generation_enabled() -> None:
    """Raise HTTP 400 if image generation is disabled in config.

    Reads the image_generation.enabled field from defaults.yaml.

    Raises:
        HTTPException: 400 if image generation is not enabled.
    """
    yaml_defaults = _load_yaml_defaults()
    img_cfg = yaml_defaults.get("image_generation", {})
    if not img_cfg.get("enabled", False):
        raise HTTPException(
            status_code=400,
            detail="Image generation is not enabled",
        )
```

**Helper: Build download URL:**
```python
def _build_download_url(session_id: str, image_id: str) -> str:
    """Build the download URL for a generated image.

    Args:
        session_id: Session ID string.
        image_id: Image UUID string.

    Returns:
        Relative URL path to the image file.
    """
    return f"/api/sessions/{session_id}/images/{image_id}.png"
```

**Endpoint: Generate current scene image (HTTP 202 pattern):**
```python
@router.post(
    "/sessions/{session_id}/images/generate-current",
    response_model=ImageGenerateAccepted,
    status_code=202,
)
async def generate_current_scene_image(
    session_id: str,
    request: Request,
    body: ImageGenerateRequest | None = None,
) -> ImageGenerateAccepted:
    """Generate an image of the current scene.

    Extracts the last N log entries from the game state, builds a scene
    prompt via LLM, and generates an image. Runs as a background task.

    Args:
        session_id: Session ID string.
        request: FastAPI request (for accessing app state).
        body: Optional request with context_entries override.

    Returns:
        202 Accepted with task ID.
    """
    _validate_and_check_session(session_id)
    _check_image_generation_enabled()

    # Load game state
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is None:
        raise HTTPException(
            status_code=400, detail="Session has no checkpoints"
        )

    state = load_checkpoint(session_id, latest_turn)
    if state is None:
        raise HTTPException(
            status_code=500, detail="Failed to load latest checkpoint"
        )

    log = state.get("ground_truth_log", [])
    if not log:
        raise HTTPException(
            status_code=400, detail="Session has no narrative log entries"
        )

    context_entries = (body.context_entries if body else 10)
    entries = list(log[-context_entries:])
    turn_number = len(log) - 1

    characters = state.get("characters", {})
    char_dict = {
        k: v.model_dump() if hasattr(v, "model_dump") else v
        for k, v in characters.items()
    }

    task_id = str(_uuid.uuid4())

    # Launch background task
    asyncio.create_task(
        _generate_image_background(
            session_id=session_id,
            task_id=task_id,
            log_entries=entries,
            characters=char_dict,
            turn_number=turn_number,
            generation_mode="current",
            app=request.app,
        )
    )

    return ImageGenerateAccepted(
        task_id=task_id,
        session_id=session_id,
        turn_number=turn_number,
    )
```

**Endpoint: Generate specific turn image:**
```python
@router.post(
    "/sessions/{session_id}/images/generate-turn/{turn_number}",
    response_model=ImageGenerateAccepted,
    status_code=202,
)
async def generate_turn_image(
    session_id: str,
    turn_number: int,
    request: Request,
) -> ImageGenerateAccepted:
    """Generate an image for a specific turn.

    Extracts log entries around the given turn (+/-5 context window),
    builds a scene prompt, and generates an image as a background task.

    Args:
        session_id: Session ID string.
        turn_number: Turn number to illustrate.
        request: FastAPI request (for accessing app state).

    Returns:
        202 Accepted with task ID.
    """
    _validate_and_check_session(session_id)
    _check_image_generation_enabled()

    # Load game state
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is None:
        raise HTTPException(
            status_code=400, detail="Session has no checkpoints"
        )

    state = load_checkpoint(session_id, latest_turn)
    if state is None:
        raise HTTPException(
            status_code=500, detail="Failed to load latest checkpoint"
        )

    log = state.get("ground_truth_log", [])
    if not log:
        raise HTTPException(
            status_code=400, detail="Session has no narrative log entries"
        )

    # Validate turn_number range
    if turn_number < 0 or turn_number >= len(log):
        raise HTTPException(
            status_code=400,
            detail=f"Turn number {turn_number} is out of range. "
            f"Valid range: 0 to {len(log) - 1}",
        )

    # Extract context window: +/-5 entries around the turn
    start = max(0, turn_number - 5)
    end = min(len(log), turn_number + 6)  # +6 because slice is exclusive
    entries = list(log[start:end])

    characters = state.get("characters", {})
    char_dict = {
        k: v.model_dump() if hasattr(v, "model_dump") else v
        for k, v in characters.items()
    }

    task_id = str(_uuid.uuid4())

    asyncio.create_task(
        _generate_image_background(
            session_id=session_id,
            task_id=task_id,
            log_entries=entries,
            characters=char_dict,
            turn_number=turn_number,
            generation_mode="specific",
            app=request.app,
        )
    )

    return ImageGenerateAccepted(
        task_id=task_id,
        session_id=session_id,
        turn_number=turn_number,
    )
```

**Endpoint: List session images:**
```python
@router.get(
    "/sessions/{session_id}/images",
    response_model=list[SceneImageResponse],
)
async def list_session_images(
    session_id: str,
) -> list[SceneImageResponse]:
    """List all generated images for a session.

    Scans the session's images directory for JSON sidecar files
    and returns image metadata with download URLs.

    Args:
        session_id: Session ID string.

    Returns:
        List of image metadata objects.
    """
    _validate_and_check_session(session_id)

    images_dir = get_session_dir(session_id) / "images"
    if not images_dir.exists():
        return []

    results: list[SceneImageResponse] = []
    for json_file in sorted(images_dir.glob("*.json")):
        try:
            import json as _json
            data = _json.loads(json_file.read_text(encoding="utf-8"))
            image_id = data.get("id", json_file.stem)
            results.append(
                SceneImageResponse(
                    id=data["id"],
                    session_id=data["session_id"],
                    turn_number=data["turn_number"],
                    prompt=data["prompt"],
                    image_path=data["image_path"],
                    provider=data["provider"],
                    model=data["model"],
                    generation_mode=data["generation_mode"],
                    generated_at=data["generated_at"],
                    download_url=_build_download_url(session_id, image_id),
                )
            )
        except (KeyError, ValueError, OSError) as e:
            logger.warning("Skipping invalid image metadata %s: %s", json_file, e)
            continue

    return results
```

**Image file serving endpoint:**
```python
@router.get("/sessions/{session_id}/images/{image_filename}")
async def serve_session_image(session_id: str, image_filename: str):
    """Serve a generated image file.

    Args:
        session_id: Session ID string.
        image_filename: Image filename (e.g., "uuid.png").

    Returns:
        The image file as a FileResponse.
    """
    import re
    from fastapi.responses import FileResponse

    _validate_and_check_session(session_id)

    # Validate filename format: UUID.png only
    if not re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.png$", image_filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid image filename format",
        )

    image_path = get_session_dir(session_id) / "images" / image_filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(str(image_path), media_type="image/png")
```

### Background Task Pattern

The background task function should be defined in `api/routes.py` as a module-level async function (not a method). It uses `asyncio.create_task()` rather than FastAPI's `BackgroundTasks` dependency because `BackgroundTasks` runs after the response is sent but blocks the ASGI send -- `asyncio.create_task` is truly non-blocking and allows the WebSocket broadcast to happen independently.

```python
async def _generate_image_background(
    session_id: str,
    task_id: str,
    log_entries: list[str],
    characters: dict[str, Any],
    turn_number: int,
    generation_mode: str,
    app: Any,
) -> None:
    """Background task for image generation.

    Builds a scene prompt, generates an image, saves metadata,
    and broadcasts a WebSocket event on completion.

    This function MUST NOT raise exceptions -- all errors are caught
    and logged to prevent crashing the event loop.

    Args:
        session_id: Session ID.
        task_id: Unique task identifier for tracking.
        log_entries: Narrative log entries for scene context.
        characters: Character info dict.
        turn_number: Turn number being illustrated.
        generation_mode: "current" or "specific".
        app: FastAPI app instance (for WebSocket broadcast access).
    """
    from image_gen import ImageGenerationError, ImageGenerator

    try:
        generator = ImageGenerator()

        # Step 1: Build scene prompt via LLM
        prompt = await generator.build_scene_prompt(log_entries, characters)

        # Step 2: Generate image via Imagen API
        scene_image = await generator.generate_scene_image(
            prompt=prompt,
            session_id=session_id,
            turn_number=turn_number,
            generation_mode=generation_mode,
        )

        # Step 3: Save metadata as JSON sidecar
        import json as _json
        from persistence import get_session_dir

        images_dir = get_session_dir(session_id) / "images"
        metadata_path = images_dir / f"{scene_image.id}.json"
        metadata_path.write_text(
            _json.dumps(scene_image.model_dump(), indent=2),
            encoding="utf-8",
        )

        # Step 4: Broadcast WebSocket event
        from api.websocket import manager

        download_url = f"/api/sessions/{session_id}/images/{scene_image.id}.png"
        await manager.broadcast(session_id, {
            "type": "image_ready",
            "image": {
                "id": scene_image.id,
                "session_id": scene_image.session_id,
                "turn_number": scene_image.turn_number,
                "prompt": scene_image.prompt,
                "image_path": scene_image.image_path,
                "provider": scene_image.provider,
                "model": scene_image.model,
                "generation_mode": scene_image.generation_mode,
                "generated_at": scene_image.generated_at,
                "download_url": download_url,
            },
        })

        logger.info(
            "Image generated for session %s turn %d (task %s): %s",
            session_id, turn_number, task_id, scene_image.id,
        )

    except ImageGenerationError as e:
        logger.error(
            "Image generation failed for session %s turn %d (task %s): %s",
            session_id, turn_number, task_id, e,
        )
        # Broadcast error to connected clients
        from api.websocket import manager

        await manager.broadcast(session_id, {
            "type": "error",
            "message": f"Image generation failed: {e}",
            "recoverable": True,
        })

    except Exception as e:
        logger.exception(
            "Unexpected error in image generation background task "
            "(session=%s, turn=%d, task=%s)",
            session_id, turn_number, task_id,
        )
        # Broadcast generic error
        from api.websocket import manager

        await manager.broadcast(session_id, {
            "type": "error",
            "message": f"Image generation failed unexpectedly: {e}",
            "recoverable": True,
        })
```

### WebSocket Event Support (`api/websocket.py`)

Add the `image_ready` event type to the `_engine_event_to_schema()` function. Since the background task broadcasts directly via `ConnectionManager.broadcast()` using a raw dict (not going through the engine), the `image_ready` event will pass through the existing fallback path in `_engine_event_to_schema()`. However, for completeness and type safety, add explicit handling:

**In the imports section:**
```python
from api.schemas import (
    # ... existing imports ...
    WsImageReady,
    SceneImageResponse,
)
```

**In `_engine_event_to_schema()`:**
```python
elif event_type == "image_ready":
    image_data = event.get("image", {})
    return WsImageReady(
        image=SceneImageResponse(**image_data),
    ).model_dump()
```

Note: Since the background task in `api/routes.py` broadcasts directly to `ConnectionManager.broadcast()` (bypassing `_engine_event_to_schema`), the schema conversion happens at the broadcast site. The mapping in `_engine_event_to_schema()` serves as defense-in-depth for any future code path that routes `image_ready` through the engine broadcast callback.

### Image Metadata Storage Pattern

Each generated image is stored as two files:
```
campaigns/session_001/images/
├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.png   # Image file (from ImageGenerator)
├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.json  # Metadata sidecar (from this story)
```

The JSON sidecar file contains the `SceneImage` model data (serialized via `model_dump()`). This approach:
- Keeps metadata co-located with images for easy cleanup
- Does not require a database
- Follows the existing file-based persistence pattern used by checkpoints
- Makes the `GET /images` endpoint a simple directory scan

### Import Dependencies

The `_generate_image_background` function uses deferred imports to avoid circular dependencies:
- `from image_gen import ImageGenerator, ImageGenerationError` -- deferred because image_gen.py imports from config/models
- `from api.websocket import manager` -- deferred to avoid import cycle between routes and websocket modules
- `from persistence import get_session_dir` -- can be top-level (already imported in routes.py)

### Security Considerations

1. **Path traversal prevention:** The `serve_session_image` endpoint validates the image filename against a strict UUID.png regex pattern. This prevents `../../etc/passwd` style attacks.
2. **Session validation:** All endpoints validate the session_id using the existing `_validate_and_check_session()` helper.
3. **Turn number validation:** The `generate-turn` endpoint validates that `turn_number` is within the valid range of the ground_truth_log.
4. **Background task error isolation:** The background task catches all exceptions and logs them, preventing unhandled errors from crashing the event loop.

### Existing Patterns Followed

| Pattern | Source | Usage Here |
|---------|--------|-----------|
| Session validation | `_validate_and_check_session()` in routes.py | All image endpoints |
| HTTP 202 Accepted | Standard REST pattern | generate-current, generate-turn |
| `asyncio.create_task` background work | `engine._autopilot_loop` in engine.py | Image generation background task |
| WebSocket broadcast | `manager.broadcast()` in websocket.py | image_ready event |
| File-based metadata | Checkpoint JSON files in persistence.py | Image metadata JSON sidecars |
| Path traversal validation | `_validate_fork_id_param()` in routes.py | Image filename validation |
| Deferred imports | `from api.engine import GameEngine` in routes.py | ImageGenerator import |
| `_load_yaml_defaults()` for config | Used in `get_session_config()` in routes.py | `_check_image_generation_enabled()` |

### What This Story Does NOT Do

- **No "best scene" scanner logic.** The scanner that analyzes full session history is in Story 17-4.
- **No UI.** The image generation UI panel is in Story 17-5.
- **No image download/export/gallery.** Full export is Story 17-6.
- **No task status polling endpoint.** The frontend relies on the WebSocket `image_ready` event for completion notification. A task status endpoint can be added in a future story if needed.
- **No image deletion endpoint.** Can be added when the UI requires it.

### Common Pitfalls to Avoid

1. **Do NOT use `FastAPI.BackgroundTasks`.** Use `asyncio.create_task()` instead. `BackgroundTasks` blocks the ASGI send and cannot broadcast WebSocket events during execution.
2. **Do NOT let exceptions escape the background task.** Unhandled exceptions in `asyncio.create_task` callbacks cause unobserved exception warnings and silently fail. Wrap everything in try/except.
3. **Do NOT import `image_gen` at module level in routes.py.** Use deferred imports inside functions to avoid import-time side effects (API key resolution, SDK initialization).
4. **Do NOT use `StaticFiles` mount for image serving.** A dedicated endpoint with path traversal validation is safer and provides session-level access control.
5. **Do NOT forget to save the JSON sidecar.** The `GET /images` endpoint depends on sidecar files for metadata. Without them, images are invisible to the listing endpoint.
6. **Do NOT block on `build_scene_prompt()` in the request handler.** Both `build_scene_prompt()` and `generate_scene_image()` are async but can take 5-15 seconds. They must run in the background task.
7. **Do NOT hardcode image model/provider.** The `ImageGenerator` already reads config from `defaults.yaml`. Let it handle model selection.

### References

- [Source: `api/routes.py` — Existing route patterns, session validation helpers]
- [Source: `api/websocket.py` — ConnectionManager.broadcast(), WsEvent schemas, _engine_event_to_schema()]
- [Source: `api/engine.py` — GameEngine class, _get_state_snapshot(), asyncio.create_task pattern]
- [Source: `api/dependencies.py` — get_engine_registry, get_or_create_engine patterns]
- [Source: `api/schemas.py` — Response/request model conventions, WebSocket event schemas]
- [Source: `image_gen.py` — ImageGenerator class, build_scene_prompt(), generate_scene_image()]
- [Source: `models.py` — SceneImage, ImageGenerationConfig, create_scene_image()]
- [Source: `persistence.py` — get_session_dir(), CAMPAIGNS_DIR]
- [Source: `_bmad-output/implementation-artifacts/17-2-image-generation-service.md` — Predecessor story]
- [Source: `_bmad-output/planning-artifacts/epics-v2.1.md` — Epic 17 story definitions]

---

## File List

| File | Action | Description |
|------|--------|-------------|
| `api/schemas.py` | Modified | Added `ImageGenerateRequest`, `ImageGenerateAccepted`, `SceneImageResponse`, `WsImageReady` schemas |
| `api/routes.py` | Modified | Added 4 image endpoints (`generate-current`, `generate-turn`, list images, serve image) + `_generate_image_background` task + `_check_image_generation_enabled` and `_build_download_url` helpers |
| `api/websocket.py` | Modified | Added `image_ready` event to `_engine_event_to_schema()` mapping + imported `WsImageReady`, `SceneImageResponse` |
| `tests/test_image_api.py` | Created | 35 tests covering all endpoints, schemas, background task error handling, WebSocket events, helper functions, and concurrent request guard |

---

## Code Review

**Reviewer:** Claude Opus 4.6
**Date:** 2026-02-14
**Status:** PASS (with fixes applied)

### Issues Found and Resolved

| # | Severity | Issue | Resolution |
|---|----------|-------|------------|
| 1 | HIGH | `generation_mode` parameter typed as `str` instead of `Literal["current", "best", "specific"]` in `_generate_image_background()`, allowing any string to bypass type checking and reach `generate_scene_image()` which expects the Literal type | Changed parameter type to `Literal["current", "best", "specific"]` |
| 2 | HIGH | `asyncio.create_task()` return value discarded in both `generate_current_scene_image` and `generate_turn_image`, allowing task to be garbage collected while running and producing unobserved exception warnings | Store task references in `_active_image_tasks` dict with `add_done_callback` for cleanup |
| 3 | HIGH | `_generate_image_background` does not ensure images directory exists before writing JSON sidecar at line 2333, relying on `generate_scene_image` to have created it | Added `images_dir.mkdir(parents=True, exist_ok=True)` before writing sidecar |
| 4 | MEDIUM | Unused `app: Any` parameter in `_generate_image_background` -- passed from both call sites but never referenced in function body (dead code) | Removed `app` parameter from function signature and both call sites |
| 5 | MEDIUM | `list_session_images` performs blocking synchronous `json_file.read_text()` in async endpoint, potentially blocking event loop for directories with many images | Documented as known limitation; consistent with existing codebase patterns for checkpoint loading. The number of images per session is typically small (<20) |
| 6 | MEDIUM | Background task constructs raw dict for `image_ready` WebSocket event instead of using `WsImageReady`/`SceneImageResponse` Pydantic schemas, bypassing schema validation and violating defense-in-depth pattern | Refactored to construct `WsImageReady(image=SceneImageResponse(...))` and broadcast via `.model_dump()` |
| 7 | MEDIUM | No concurrent request guard -- clients can spam image generation endpoints and create unlimited parallel `asyncio.create_task` calls overwhelming LLM and image APIs | Added `_active_image_tasks` tracking dict with `_MAX_CONCURRENT_IMAGE_TASKS=3` limit, returning HTTP 429 when exceeded |
| 8 | LOW | `_check_image_generation_enabled()` reads and parses YAML from disk on every call with no caching | Not fixed -- consistent with existing `_load_yaml_defaults()` usage patterns elsewhere in routes.py |
| 9 | LOW | Test `test_handles_image_generation_error` patches `image_gen.ImageGenerator` at module level rather than at the deferred import site -- fragile mock that could silently break if import path changes | Not fixed -- mock works correctly due to Python module caching; documenting for awareness |

### Test Results After Fixes

- `tests/test_image_api.py`: **35 passed** (was 33, added concurrent guard test + autouse cleanup fixture)
- `tests/test_api.py`: **145 passed** (no regressions)
- `ruff check`: All checks passed
- `ruff format`: All files formatted
