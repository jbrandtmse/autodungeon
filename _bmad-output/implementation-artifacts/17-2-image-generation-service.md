# Story 17-2: Image Generation Service

**Epic:** 17 — AI Scene Image Generation
**Status:** complete

---

## Story

As a **developer**,
I want **a Python module that wraps the Google text-to-image API**,
So that **the system can generate scene illustrations from text descriptions**.

---

## Acceptance Criteria

### AC1: ImageGenerator Class Interface

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

### AC2: Google GenAI SDK Integration

**Given** the `google-genai` SDK
**When** generating an image
**Then** it calls `client.aio.models.generate_images(model, prompt, config)` with the configured image model and 16:9 aspect ratio

### AC3: Image Storage

**Given** a generated image
**When** saved
**Then** it is stored as PNG in `campaigns/{session}/images/{image_id}.png`
**And** metadata is recorded in a `SceneImage` model

### AC4: SceneImage Model

**Given** the `SceneImage` model in `models.py`
**When** created
**Then** it includes: `id`, `session_id`, `turn_number`, `prompt`, `image_path`, `provider`, `model`, `generation_mode`, `generated_at`

### AC5: ImageGenerationConfig Model

**Given** the `ImageGenerationConfig` model in `models.py`
**When** created
**Then** it includes: `enabled`, `image_provider`, `image_model`, `scanner_provider`, `scanner_model`, `scanner_token_limit`

### AC6: Config Defaults Extension

**Given** `config/defaults.yaml`
**When** extended
**Then** it includes an `image_generation` section with defaults for all config fields

### AC7: API Schema Extension

**Given** `api/schemas.py`
**When** extended
**Then** `GameConfigResponse` and `GameConfigUpdateRequest` include image generation config fields

### AC8: Scene Prompt Builder

**Given** the scene prompt builder
**When** building a prompt from log entries
**Then** it uses a fast LLM (e.g., Gemini Flash) to summarize the narrative into a vivid, visual image prompt (30-50 words) suitable for fantasy art generation

### AC9: Dependency Addition

**Given** `pyproject.toml`
**When** updated
**Then** `google-genai` and `Pillow` are added as dependencies

---

## Tasks / Subtasks

- [x] **Task 1: Add SceneImage model to models.py** (AC: 4)
  - [x] 1.1: Add `SceneImage` Pydantic model with fields: `id` (str, UUID), `session_id` (str), `turn_number` (int, ge=0), `prompt` (str), `image_path` (str), `provider` (str), `model` (str), `generation_mode` (Literal["current", "best", "specific"]), `generated_at` (str, ISO timestamp)
  - [x] 1.2: Add `create_scene_image` factory function following the existing `create_user_error` / `create_whisper` pattern
  - [x] 1.3: Add `SceneImage` and `create_scene_image` to `__all__` exports

- [x] **Task 2: Add ImageGenerationConfig model to models.py** (AC: 5)
  - [x] 2.1: Add `ImageGenerationConfig` Pydantic model with fields: `enabled` (bool, default=False), `image_provider` (str, default="gemini"), `image_model` (str, default="imagen-4.0-generate-001"), `scanner_provider` (str, default="gemini"), `scanner_model` (str, default="gemini-3-flash-preview"), `scanner_token_limit` (int, default=4000, ge=1)
  - [x] 2.2: Add `ImageGenerationConfig` to `__all__` exports

- [x] **Task 3: Extend config/defaults.yaml** (AC: 6)
  - [x] 3.1: Add `image_generation` section with all default values matching the `ImageGenerationConfig` model defaults

- [x] **Task 4: Extend api/schemas.py** (AC: 7)
  - [x] 4.1: Add image generation fields to `GameConfigResponse`: `image_generation_enabled` (bool), `image_provider` (str), `image_model` (str), `image_scanner_provider` (str), `image_scanner_model` (str), `image_scanner_token_limit` (int)
  - [x] 4.2: Add corresponding optional fields to `GameConfigUpdateRequest` (all `| None` with `default=None`)
  - [x] 4.3: Update `api/routes.py` `get_session_config` and `update_session_config` handlers to include the new fields (reading from / writing to the game state or defaults)

- [x] **Task 5: Create image_gen.py module** (AC: 1, 2, 3, 8)
  - [x] 5.1: Create `image_gen.py` at project root with `ImageGenerator` class
  - [x] 5.2: Implement `__init__(self)` to lazily initialize the `genai.Client` using the effective Google API key (from `config.py` `get_effective_api_key` / `load_user_settings` pattern, matching `agents.py` `_get_effective_api_key`)
  - [x] 5.3: Implement `async def generate_scene_image(self, prompt, session_id, turn_number, generation_mode) -> SceneImage` that:
    - Calls the Google GenAI async image generation API
    - Saves the image bytes as PNG to `campaigns/session_{session_id}/images/{image_id}.png`
    - Returns a populated `SceneImage` model
  - [x] 5.4: Implement `async def build_scene_prompt(self, log_entries, characters) -> str` that:
    - Constructs a system prompt instructing the LLM to produce a 30-50 word visual scene description suitable for fantasy art
    - Calls a fast LLM (Gemini Flash via the existing `get_llm` factory) with the scene context
    - Returns the generated prompt string
  - [x] 5.5: Implement `_ensure_images_dir(self, session_id) -> Path` helper for creating `campaigns/session_{session_id}/images/` directory
  - [x] 5.6: Add error handling: wrap SDK calls in try/except, log errors, raise descriptive exceptions

- [x] **Task 6: Update pyproject.toml** (AC: 9)
  - [x] 6.1: Add `google-genai>=1.0.0` to `dependencies` list
  - [x] 6.2: Add `Pillow>=10.0.0` to `dependencies` list

- [x] **Task 7: Write tests** (AC: all)
  - [x] 7.1: Add `tests/test_image_gen.py` with unit tests for `ImageGenerator`:
    - Test `build_scene_prompt` produces a non-empty string prompt
    - Test `generate_scene_image` creates the image file and returns valid `SceneImage`
    - Test image is saved to correct path (`campaigns/session_{id}/images/{uuid}.png`)
    - Test error handling when API key is missing
    - Mock the `genai.Client` to avoid real API calls
  - [x] 7.2: Add tests for `SceneImage` model in `tests/test_models.py`:
    - Test model creation with all required fields
    - Test `create_scene_image` factory function
    - Test validation (turn_number ge=0, generation_mode literal)
  - [x] 7.3: Add tests for `ImageGenerationConfig` model:
    - Test default values
    - Test field validation (scanner_token_limit ge=1)
  - [x] 7.4: Add tests for schema extensions in `tests/test_api.py`:
    - Test `GameConfigResponse` includes image generation fields
    - Test `GameConfigUpdateRequest` accepts image generation fields
  - [x] 7.5: Run full test suite: `python -m pytest` -- no regressions

- [x] **Task 8: Verification** (AC: all)
  - [x] 8.1: Run `python -m ruff check .` -- no new violations
  - [x] 8.2: Run `python -m ruff format --check .` -- formatting passes
  - [x] 8.3: Verify `import image_gen` works and `ImageGenerator` is importable
  - [x] 8.4: Run `uv sync` to install new dependencies

---

## Dev Notes

### Architecture Context

This is a **backend-only** story that creates the image generation service layer. It does NOT include API endpoints (Story 17-3) or UI (Story 17-5). The module provides:
1. Two new Pydantic models (`SceneImage`, `ImageGenerationConfig`) in `models.py`
2. A new `image_gen.py` module with the `ImageGenerator` class
3. Config/schema extensions to support image generation settings

Story 17-3 (API endpoints) depends on this story being complete.

### google-genai SDK Usage Pattern

The project uses the `google-genai` SDK (NOT the older `google-generativeai` package). Key patterns:

```python
from google import genai
from google.genai import types

# Initialize client with API key
client = genai.Client(api_key=api_key)

# Async image generation (use client.aio for async)
response = await client.aio.models.generate_images(
    model="imagen-4.0-generate-001",
    prompt="A dramatic fantasy battle scene...",
    config=types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio="16:9",
    ),
)

# Access generated image bytes
image_bytes = response.generated_images[0].image.image_bytes

# Save as PNG
from PIL import Image
import io
image = Image.open(io.BytesIO(image_bytes))
image.save("output.png", format="PNG")
```

**Available Imagen models (as of 2026):**
- `imagen-4.0-generate-001` (standard -- use as default)
- `imagen-4.0-ultra-generate-001` (ultra quality)
- `imagen-4.0-fast-generate-001` (fast generation)

**Note:** Imagen 3 (`imagen-3.0-generate-002`) has been shut down. Use Imagen 4 variants.

**GenerateImagesConfig fields:**
- `number_of_images` (int): Number of images to generate (use 1)
- `aspect_ratio` (str): `"1:1"`, `"3:4"`, `"4:3"`, `"9:16"`, `"16:9"`
- `output_mime_type` (str): `"image/png"`, `"image/jpeg"`
- `person_generation` (str): `"allow_adult"`, `"dont_allow"`, `"allow_all"`

**Maximum prompt length:** 480 tokens

### SceneImage Model Definition

Add to `models.py` following the existing Pydantic model patterns (e.g., `SessionMetadata`, `TranscriptEntry`):

```python
class SceneImage(BaseModel):
    """Metadata for a generated scene illustration.

    Tracks the generated image and its provenance for display,
    export, and re-generation.

    Attributes:
        id: Unique image identifier (UUID).
        session_id: Session this image belongs to.
        turn_number: Turn number the image illustrates.
        prompt: The text prompt used for generation.
        image_path: Relative path to the image file within campaigns/.
        provider: Image generation provider (e.g., "gemini").
        model: Image generation model name.
        generation_mode: How the image was requested.
        generated_at: ISO timestamp when image was generated.
    """

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
```

Factory function (following `create_whisper` / `create_user_error` pattern):

```python
def create_scene_image(
    session_id: str,
    turn_number: int,
    prompt: str,
    image_path: str,
    provider: str,
    model: str,
    generation_mode: Literal["current", "best", "specific"],
) -> SceneImage:
    """Create a SceneImage with auto-generated ID and timestamp."""
    return SceneImage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        turn_number=turn_number,
        prompt=prompt,
        image_path=image_path,
        provider=provider,
        model=model,
        generation_mode=generation_mode,
        generated_at=datetime.now(UTC).isoformat() + "Z",
    )
```

### ImageGenerationConfig Model Definition

```python
class ImageGenerationConfig(BaseModel):
    """Configuration for AI scene image generation.

    Controls which models are used for image generation and
    the LLM scanner that selects "best scene" candidates.

    Attributes:
        enabled: Whether image generation is available.
        image_provider: Provider for image generation (currently only "gemini").
        image_model: Model name for image generation.
        scanner_provider: LLM provider for scene scanning / prompt building.
        scanner_model: LLM model for scene scanning / prompt building.
        scanner_token_limit: Token limit for the scanner LLM context.
    """

    enabled: bool = Field(
        default=False, description="Whether image generation is enabled"
    )
    image_provider: str = Field(
        default="gemini", description="Provider for image generation"
    )
    image_model: str = Field(
        default="imagen-4.0-generate-001",
        description="Model for image generation",
    )
    scanner_provider: str = Field(
        default="gemini",
        description="LLM provider for scene scanning and prompt building",
    )
    scanner_model: str = Field(
        default="gemini-3-flash-preview",
        description="LLM model for scene scanning and prompt building",
    )
    scanner_token_limit: int = Field(
        default=4000,
        ge=1,
        description="Token limit for the scanner LLM context",
    )
```

### config/defaults.yaml Extension

Add at the end of the file:

```yaml
# Image generation defaults
image_generation:
  enabled: false
  image_provider: gemini
  image_model: imagen-4.0-generate-001
  scanner_provider: gemini
  scanner_model: gemini-3-flash-preview
  scanner_token_limit: 4000
```

### API Schema Extension (api/schemas.py)

Add fields to `GameConfigResponse`:

```python
# Image generation settings (Story 17-2)
image_generation_enabled: bool = Field(
    default=False, description="Whether image generation is enabled"
)
image_provider: str = Field(
    default="gemini", description="Provider for image generation"
)
image_model: str = Field(
    default="imagen-4.0-generate-001", description="Image generation model"
)
image_scanner_provider: str = Field(
    default="gemini", description="LLM provider for scene scanning"
)
image_scanner_model: str = Field(
    default="gemini-3-flash-preview", description="LLM model for scene scanning"
)
image_scanner_token_limit: int = Field(
    default=4000, ge=1, description="Token limit for scene scanner"
)
```

Add corresponding optional fields to `GameConfigUpdateRequest`:

```python
# Image generation settings (Story 17-2)
image_generation_enabled: bool | None = Field(
    default=None, description="Whether image generation is enabled"
)
image_provider: str | None = Field(
    default=None, description="Provider for image generation"
)
image_model: str | None = Field(
    default=None, description="Image generation model"
)
image_scanner_provider: str | None = Field(
    default=None, description="LLM provider for scene scanning"
)
image_scanner_model: str | None = Field(
    default=None, description="LLM model for scene scanning"
)
image_scanner_token_limit: int | None = Field(
    default=None, ge=1, description="Token limit for scene scanner"
)
```

### API Routes Extension (api/routes.py)

The `get_session_config` and `update_session_config` handlers need to pass the new image generation fields. Since `ImageGenerationConfig` is a new model not yet embedded in `GameState`, the initial implementation should:

1. Read defaults from `config/defaults.yaml` via the `image_generation` section
2. When a game state exists, check for an `image_generation_config` field (future stories may embed it in GameState)
3. For now, always return defaults from the YAML config since the config is not yet persisted in GameState

This means `get_session_config` returns default image gen config values, and `update_session_config` can accept and store them (storage in GameState is a future concern -- for now the endpoint should accept the fields without error but the values are ephemeral until GameState integration).

### image_gen.py Module Structure

```python
"""Image generation service using Google's Imagen API.

This module wraps the google-genai SDK to provide scene illustration
capabilities for the autodungeon game engine.
"""

import io
import logging
from pathlib import Path
from typing import Any, Literal

from PIL import Image

from config import get_config, load_user_settings
from models import SceneImage, create_scene_image
from persistence import CAMPAIGNS_DIR, get_session_dir

logger = logging.getLogger("autodungeon")

# Scene prompt builder system prompt
SCENE_PROMPT_SYSTEM = """You are an art director for a fantasy tabletop RPG.
Given narrative log entries from a D&D session, write a vivid visual scene
description in 30-50 words suitable as a prompt for AI image generation.
Focus on: setting, lighting, character poses, dramatic action, atmosphere.
Style: digital fantasy painting, dramatic lighting, rich colors.
Do NOT include character names. Describe what is visually happening."""

# Maximum log entries to include in scene context
SCENE_CONTEXT_ENTRIES = 10


class ImageGenerationError(Exception):
    """Raised when image generation fails."""
    pass


class ImageGenerator:
    """Service for generating scene illustrations from narrative text."""

    def __init__(self) -> None:
        self._client = None  # Lazy initialization

    def _get_client(self):
        """Get or create the genai client (lazy init)."""
        if self._client is None:
            from google import genai
            api_key = self._get_api_key()
            self._client = genai.Client(api_key=api_key)
        return self._client

    def _get_api_key(self) -> str:
        """Get the effective Google API key."""
        # Follow agents.py _get_effective_api_key pattern
        user_settings = load_user_settings()
        api_keys = user_settings.get("api_keys", {})
        key = api_keys.get("google")
        if key:
            return key
        config = get_config()
        if config.google_api_key:
            return config.google_api_key
        raise ImageGenerationError(
            "GOOGLE_API_KEY not configured. Set it in .env or user settings."
        )

    def _get_image_config(self) -> dict[str, Any]:
        """Load image generation config from defaults.yaml."""
        from config import _load_yaml_defaults
        defaults = _load_yaml_defaults()
        return defaults.get("image_generation", {})

    def _ensure_images_dir(self, session_id: str) -> Path:
        """Ensure the images directory exists for a session."""
        images_dir = get_session_dir(session_id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        return images_dir

    async def generate_scene_image(
        self,
        prompt: str,
        session_id: str,
        turn_number: int,
        generation_mode: Literal["current", "best", "specific"],
    ) -> SceneImage:
        """Generate a scene image from a text prompt."""
        from google.genai import types

        img_config = self._get_image_config()
        model = img_config.get("image_model", "imagen-4.0-generate-001")
        provider = img_config.get("image_provider", "gemini")

        client = self._get_client()

        try:
            response = await client.aio.models.generate_images(
                model=model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                ),
            )
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise ImageGenerationError(f"Image generation failed: {e}") from e

        if not response.generated_images:
            raise ImageGenerationError("No images returned by the API")

        image_bytes = response.generated_images[0].image.image_bytes

        # Save as PNG
        images_dir = self._ensure_images_dir(session_id)
        import uuid
        image_id = str(uuid.uuid4())
        image_path = images_dir / f"{image_id}.png"

        image = Image.open(io.BytesIO(image_bytes))
        image.save(str(image_path), format="PNG")

        # Build relative path for storage
        rel_path = f"session_{session_id}/images/{image_id}.png"

        return create_scene_image(
            session_id=session_id,
            turn_number=turn_number,
            prompt=prompt,
            image_path=rel_path,
            provider=provider,
            model=model,
            generation_mode=generation_mode,
        )

    async def build_scene_prompt(
        self,
        log_entries: list[str],
        characters: dict[str, Any],
    ) -> str:
        """Build an image generation prompt from narrative context."""
        from agents import get_llm

        img_config = self._get_image_config()
        scanner_provider = img_config.get("scanner_provider", "gemini")
        scanner_model = img_config.get("scanner_model", "gemini-3-flash-preview")

        # Build context from log entries and characters
        context_parts = []
        recent = log_entries[-SCENE_CONTEXT_ENTRIES:]
        context_parts.append("Recent narrative:\n" + "\n".join(recent))

        if characters:
            char_desc = []
            for name, info in characters.items():
                cls = info.get("character_class", "Adventurer")
                char_desc.append(f"- {name}: {cls}")
            context_parts.append("Characters:\n" + "\n".join(char_desc))

        user_message = "\n\n".join(context_parts)

        llm = get_llm(scanner_provider, scanner_model)
        from langchain_core.messages import HumanMessage, SystemMessage
        messages = [
            SystemMessage(content=SCENE_PROMPT_SYSTEM),
            HumanMessage(content=user_message),
        ]
        response = await llm.ainvoke(messages)
        return response.content.strip()
```

### Image Storage Pattern

Images are stored alongside session checkpoints:

```
campaigns/session_001/
├── config.yaml
├── turn_001.json
├── turn_002.json
├── transcript.json
├── images/                  # NEW - image storage directory
│   ├── a1b2c3d4-....png     # UUID-named PNG files
│   └── e5f6g7h8-....png
└── forks/
```

This follows the existing `persistence.py` pattern where `get_session_dir(session_id)` returns `campaigns/session_{session_id}/`. The `images/` subdirectory is created on demand by `_ensure_images_dir()`.

### API Key Resolution

The `ImageGenerator` resolves the Google API key using the same priority chain as `agents.py`:
1. User settings (`user-settings.yaml` -> `api_keys.google`)
2. Environment variable (`GOOGLE_API_KEY` from `.env`)
3. Raise `ImageGenerationError` if neither is set

This matches the `_get_effective_api_key("google")` pattern in `agents.py` (line ~660).

### Prompt Builder LLM Usage

The `build_scene_prompt` method uses the existing `get_llm` factory from `agents.py` to create a LangChain chat model for the scanner/prompt-builder. This reuses the proven LLM infrastructure rather than creating a parallel path. The scanner LLM settings (provider, model) are configurable independently from the game engine LLMs.

### pyproject.toml Changes

Add two new dependencies to the `dependencies` list (after the existing `httpx` entry):

```toml
"google-genai>=1.0.0",
"Pillow>=10.0.0",
```

### What This Story Does NOT Do

- **No API endpoints.** REST endpoints for triggering image generation are in Story 17-3.
- **No "best scene" scanner logic.** The scanner that analyzes full session history is in Story 17-4. This story only provides the `build_scene_prompt` method that converts log entries into an art prompt.
- **No UI.** The image generation UI panel is in Story 17-5.
- **No image download/export.** That is Story 17-6.
- **No GameState integration.** `ImageGenerationConfig` is defined as a model but NOT yet embedded in `GameState` (the TypedDict). That integration happens when API endpoints need to persist config per-session.

### Common Pitfalls to Avoid

1. **Do NOT use `google-generativeai` (the old SDK).** This project uses `google-genai` (the newer SDK). The import is `from google import genai`, NOT `import google.generativeai as genai`.
2. **Do NOT use Imagen 3.** The `imagen-3.0-generate-002` model has been shut down. Use `imagen-4.0-generate-001` as the default.
3. **Do NOT use synchronous `client.models.generate_images()`.** Use `client.aio.models.generate_images()` for async compatibility with FastAPI.
4. **Do NOT hardcode the API key.** Follow the `agents.py` key resolution pattern (user settings -> env var).
5. **Do NOT store absolute paths in `SceneImage.image_path`.** Store relative paths within the `campaigns/` directory for portability.
6. **Do NOT call `_load_yaml_defaults` at module scope.** Call it lazily in methods to avoid import-time side effects.
7. **Do NOT forget to create the `images/` subdirectory.** Use `mkdir(parents=True, exist_ok=True)` to handle first-time creation.

### References

- [Source: models.py — Existing Pydantic model patterns (SessionMetadata, TranscriptEntry, Whisper)]
- [Source: agents.py — get_llm factory, _get_effective_api_key pattern]
- [Source: config.py — AppConfig, _load_yaml_defaults, load_user_settings]
- [Source: config/defaults.yaml — Current config structure to extend]
- [Source: api/schemas.py — GameConfigResponse, GameConfigUpdateRequest patterns]
- [Source: persistence.py — CAMPAIGNS_DIR, get_session_dir, ensure_session_dir patterns]
- [Source: pyproject.toml — Current dependency list]
- [Source: _bmad-output/planning-artifacts/epics-v2.1.md — Epic 17 story definitions]
- [Docs: https://ai.google.dev/gemini-api/docs/imagen — Google Imagen API documentation]
- [Docs: https://googleapis.github.io/python-genai/ — google-genai Python SDK reference]

---

## File List

| File | Action | Description |
|------|--------|-------------|
| `models.py` | Modified | Add `SceneImage` model, `create_scene_image` factory, `ImageGenerationConfig` model |
| `image_gen.py` | Created | New module with `ImageGenerator` class wrapping google-genai SDK |
| `config/defaults.yaml` | Modified | Add `image_generation` section with default config values |
| `api/schemas.py` | Modified | Add image generation fields to `GameConfigResponse` and `GameConfigUpdateRequest` |
| `api/routes.py` | Modified | Pass image generation config fields in `get_session_config` and `update_session_config` |
| `pyproject.toml` | Modified | Add `google-genai` and `Pillow` dependencies |
| `tests/test_image_gen.py` | Created | Unit tests for `ImageGenerator` class |
| `tests/test_models.py` | Modified | Tests for `SceneImage` and `ImageGenerationConfig` models |
| `tests/test_api.py` | Modified | Tests for schema extensions |

---

## Code Review

**Reviewer:** Claude Opus 4.6 (adversarial review)
**Date:** 2026-02-14
**Result:** PASS with fixes applied (7 issues found, 5 auto-resolved)

### Issues Found

| # | Severity | Issue | Resolution |
|---|----------|-------|------------|
| 1 | HIGH | **Blocking I/O in async method**: `generate_scene_image` called `Image.open()` and `image.save()` synchronously inside an `async` method, blocking the FastAPI event loop during PIL decode/write. | **FIXED**: Extracted `_save_image_to_disk` static method and wrapped with `await asyncio.to_thread()` to offload blocking PIL operations to a thread. |
| 2 | MEDIUM | **Stale cached genai Client**: `_get_client()` cached the `genai.Client` forever. If a user updated their Google API key via the Settings UI, the `ImageGenerator` would continue using the old key. `agents.py` `get_llm()` avoids this by creating fresh instances. | **FIXED**: Added `_client_api_key` tracking field. `_get_client()` now checks if the effective API key has changed and recreates the client if so. |
| 3 | MEDIUM | **No prompt length validation**: Imagen API has a ~480 token limit. Passing a very long prompt would produce an opaque API error instead of a clear message. | **FIXED**: Added `MAX_PROMPT_CHARS = 1900` constant. `generate_scene_image()` now truncates prompts exceeding this limit with a warning log. |
| 4 | MEDIUM | **`update_session_config` silently discards image gen changes**: Image generation fields are extracted from the update request, reflected in the response, but never persisted. A subsequent GET returns YAML defaults, not the user's values. | **FIXED**: Added explicit code comments explaining the ephemeral behavior (intentional per story scope) and a `logger.debug()` call when image gen fields are received but not persisted. |
| 5 | MEDIUM | **`_get_image_config()` returned raw dict with no type safety**: Callers used `.get()` with scattered fallback defaults. A misspelled YAML key would silently fall back without any validation. | **FIXED**: Changed `_get_image_config()` to return `ImageGenerationConfig` (Pydantic model) instead of `dict[str, Any]`. YAML values are now validated through the model with graceful fallback on parse errors. Updated all callers to use typed attribute access. |
| 6 | LOW | **`_load_yaml_defaults` is a private function imported cross-module**: `image_gen.py` imports `config._load_yaml_defaults` (a private function). While `api/routes.py` establishes this precedent, it's a code smell. | Documented only. The established codebase pattern accepts this, and refactoring `_load_yaml_defaults` to be public would touch many files beyond this story's scope. |
| 7 | LOW | **`_get_image_config()` re-reads YAML on every call**: No caching for the YAML config read. Not a performance concern since image generation is not on the hot path. | Documented only. Acceptable for the current usage pattern. |

### Tests After Fixes

- `tests/test_image_gen.py`: 17 passed (all)
- `tests/test_models.py`: 101 passed, 1 pre-existing failure (DM token_limit 32000 vs test expecting 8000 -- unrelated to this story)
- `tests/test_api.py`: 128 passed (all, including 5 image generation schema tests)
- Ruff lint: all checks passed
- Ruff format: all files formatted
