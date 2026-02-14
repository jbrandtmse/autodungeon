# Sprint Change Proposal — AI Scene Image Generation

**Date:** 2026-02-14
**Author:** John (PM Agent)
**Triggered by:** New feature request (post v2.0 completion)
**Scope Classification:** Moderate
**Approval Status:** Approved (2026-02-14)

---

## 1. Issue Summary

**Problem Statement:** Developer wants AI-generated illustrations of D&D scenes to enhance the autodungeon experience. Three generation modes are required:

- **(a) Current Scene:** Generate an image of the scene as it stands right now
- **(b) Best Scene:** Use a configurable LLM to scan/analyze the entire session history and identify the most visually dramatic or memorable scene, then generate an image of it
- **(c) Specific Turn:** Generate an image of a scene at a particular turn number

**Supporting Requirements:**

- Turn numbers must be visible in the narrative display to support mode (c) — format: "Turn N — Name, the Class:"
- Configuration options for both the text-to-image model and the session-scanning LLM
- Individual image download (single PNG) and bulk session export (zip)
- Images stored persistently in campaign directory

**Category:** New requirement — additive feature. No existing functionality is broken, blocked, or needs rollback.

**Evidence/Rationale:** Google's `google-genai` Python SDK provides production-ready text-to-image via:

- **Imagen 3** (`imagen-3.0-generate-002`) — state-of-the-art quality
- **Imagen 4** (`imagen-4.0-generate-001`) — latest generation
- **Gemini 2.5 Flash Image** ("Nano Banana") — fast alternative

The API is straightforward: `client.models.generate_images(model, prompt, config)`. Uses the same `GEMINI_API_KEY` already configured for the game engine's Gemini LLM calls.

This feature aligns with:

- The **Content Creation** user journey (Alex the streamer — shareable visual moments)
- The **Research Observability** goals (visual snapshots of emergent narrative moments)
- The **"Phone a Friend" success metric** (images are inherently shareable)

---

## 2. Impact Analysis

### 2.1 Epic Impact

| Check | Finding |
|-------|---------|
| Current epics | All 16 epics are **done**. No current work is affected. |
| Required changes | **New Epic 17** — "AI Scene Image Generation" (5-6 stories) |
| Future epics | No planned epics are impacted |
| Invalidated epics | None |
| Priority/ordering | Epic 17 is additive, no resequencing needed |

### 2.2 Artifact Impact

#### PRD

**No conflicts** with existing requirements. MVP shipped in v1.0. This is a **v2.1** additive feature.

**New Functional Requirements:**

| FR | Description |
|----|-------------|
| FR85 | User can generate an AI illustration of the current scene |
| FR86 | User can generate an AI illustration of the "best scene" from the entire session, using a configurable LLM to scan/analyze session history |
| FR87 | User can generate an AI illustration of a scene at a specific turn number |
| FR88 | Turn numbers are visible in the narrative display (format: "Turn N — Name, the Class:") |
| FR89 | User can configure the text-to-image model (Imagen 3, Imagen 4, Gemini Flash Image) |
| FR90 | User can configure which LLM model scans session history for "best scene" selection |
| FR91 | User can download an individual generated image or bulk-download all images for a session |
| FR92 | Generated images are stored in the campaign directory for persistence |

**PRD Sections to Update:**

- Growth Features table: Add "AI Scene Illustration" under v2.1
- Functional Requirements: Add FR85-FR92
- LLM Configuration: Add image generation provider/model config

#### Architecture

**New data models** (`models.py`):

```python
class SceneImage(BaseModel):
    """A generated scene illustration."""
    id: str  # UUID
    session_id: str
    turn_number: int  # Which turn this illustrates
    prompt: str  # The text-to-image prompt used
    image_path: str  # Relative path within campaign directory
    provider: str  # "gemini"
    model: str  # "imagen-3.0-generate-002"
    generation_mode: Literal["current", "best", "specific"]
    generated_at: datetime

class ImageGenerationConfig(BaseModel):
    """Configuration for AI scene image generation."""
    enabled: bool = False
    image_provider: str = "gemini"
    image_model: str = "imagen-3.0-generate-002"
    scanner_provider: str = "gemini"
    scanner_model: str = "gemini-2.5-pro"
    scanner_token_limit: int = 128000
```

**New Python module** — `image_gen.py`:

- Wraps `google-genai` SDK (`client.models.generate_images()`)
- Scene-to-prompt pipeline: extract recent log entries → LLM summarizes into a vivid image prompt → generate image
- "Best scene" scanner: chunked analysis of full session history using configurable LLM
- Image storage to `campaigns/{session}/images/{image_id}.png`

**New API endpoints** (`api/routes.py`):

```
POST /api/sessions/{session_id}/images/generate-current
POST /api/sessions/{session_id}/images/generate-best
POST /api/sessions/{session_id}/images/generate-turn/{turn_number}
GET  /api/sessions/{session_id}/images
GET  /api/sessions/{session_id}/images/{image_id}/download
GET  /api/sessions/{session_id}/images/download-all  (zip)
```

**Config extension** (`config/defaults.yaml` + `api/schemas.py`):

```yaml
image_generation:
  enabled: false
  image_provider: gemini
  image_model: imagen-3.0-generate-002
  scanner_provider: gemini
  scanner_model: gemini-2.5-pro
  scanner_token_limit: 128000
```

**WebSocket extension**: Add `image_ready` event type for async notification when generation completes:

```json
{
  "type": "image_ready",
  "image_id": "abc-123",
  "turn_number": 42,
  "generation_mode": "current",
  "image_url": "/api/sessions/{session_id}/images/abc-123/download"
}
```

**Turn number in narrative**: Turn number = 1-based index in `ground_truth_log`. Computed in frontend from array index. No backend log format change needed.

#### UI/UX

**Narrative display changes:**

- `NarrativeMessage.svelte`: Change header from `"Thorgrim, the Fighter:"` to `"Turn 42 — Thorgrim, the Fighter:"`
- Add inline image display when an image is associated with a turn
- Per-image download button overlay

**New UI controls:**

- Image generation button/menu in session controls area with 3 options:
  - "Illustrate Current Scene" (mode a)
  - "Illustrate Best Scene" (mode b)
  - "Illustrate Turn #..." (mode c — with turn number input or click-to-generate on a specific message)
- Loading indicator during generation (Imagen takes ~5-15 seconds)
- Image gallery/history panel (optional, accessible from session details)

**Frontend stores:**

- New `imageStore` for tracking generated images and generation state
- Extend `ParsedMessage` interface with optional `imageUrl: string | null`

#### Other Artifacts

| Artifact | Impact |
|----------|--------|
| `pyproject.toml` | Add `google-genai` and `Pillow` dependencies |
| `.env.example` | Already has `GEMINI_API_KEY` — same key works for Imagen |
| Tests | New `test_image_gen.py`; mock Imagen API calls |
| Frontend tests | Test image display in NarrativeMessage, image generation UI |
| `sprint-status.yaml` | Add Epic 17 with stories |

---

## 3. Recommended Approach

**Selected: Direct Adjustment — New Epic 17**

| Option | Viable? | Rationale |
|--------|---------|-----------|
| **Direct Adjustment** | **Yes (Selected)** | Clean additive feature, new epic, no rollback needed |
| Rollback | No | Nothing to roll back — all existing work is complete |
| MVP Review | No | MVP shipped months ago, this is a v2.1 enhancement |

**Justification:**

- All 16 epics are done — this is a clean greenfield addition
- Uses the same Google API key already configured for Gemini
- Follows established patterns (new module + API routes + frontend components)
- Turn number display is a small, isolated frontend change
- "Best scene" scanner is the most complex piece (needs chunked LLM analysis for long sessions)

**Effort:** Medium (5-6 stories)
**Risk:** Low — text-to-image APIs are stable; turn number display is trivial; scanner LLM for best-scene has minor uncertainty around token limits for very long sessions (mitigated by chunked analysis)

---

## 4. Detailed Change Proposals

### Epic 17: AI Scene Image Generation (v2.1)

| Story | Title | Description | Dependencies |
|-------|-------|-------------|--------------|
| **17-1** | Turn Number Display | Add "Turn N —" prefix to narrative message headers in `NarrativeMessage.svelte`. Compute from `ground_truth_log` array index (1-based). No backend changes. Frontend-only. | None |
| **17-2** | Image Generation Service | New `image_gen.py` module: `google-genai` SDK integration, scene-to-prompt LLM pipeline, image storage to `campaigns/{session}/images/`. `SceneImage` + `ImageGenerationConfig` models in `models.py`. Config fields in `defaults.yaml` + `schemas.py`. Add `google-genai` and `Pillow` to `pyproject.toml`. | None |
| **17-3** | Current Scene & Specific Turn Image API | REST endpoints for generating image of current scene (last N log entries summarized into prompt) and specific turn. WebSocket `image_ready` notification. Background task for async generation. | 17-2 |
| **17-4** | Best Scene Scanner | Configurable LLM (e.g., Gemini 2.5 Pro) scans session history to identify the most visually dramatic/memorable scene. Chunked analysis for sessions exceeding scanner model's context window. May need tool-use pattern for very long sessions. REST endpoint. | 17-2 |
| **17-5** | Image Generation UI | Frontend: generation controls (3 modes), inline image display in narrative, loading/progress states, image gallery panel. Turn-click-to-generate interaction. New `imageStore`. | 17-1, 17-3 |
| **17-6** | Image Export & Download | Per-image download button (single click saves PNG). Bulk export of all session images as zip via `GET /api/sessions/{id}/images/download-all`. Images persisted in `campaigns/{session}/images/` directory. | 17-5 |

### Story Dependency Graph

```
17-1 (Turn Numbers) ──────────────┐
                                   ├──→ 17-5 (UI) ──→ 17-6 (Export)
17-2 (Service) ──→ 17-3 (API) ───┘
                └──→ 17-4 (Scanner) ──→ 17-5
```

---

## 5. Implementation Handoff

**Scope:** Moderate — backlog addition, no fundamental replan needed.

| Role | Responsibility |
|------|---------------|
| **Architect** | Review and approve architecture changes (new module, API endpoints, data models, WebSocket protocol extension) |
| **PM** | Update PRD with FR85-FR92, update Growth Features table |
| **SM** | Create story files from epic, update sprint-status.yaml |
| **Dev** | Implement stories 17-1 through 17-6 |
| **TEA** | Test coverage for image generation (mocked API calls), frontend image display |

**Key Dependencies:**

- `google-genai` Python package (new dependency)
- `Pillow` for image handling (new dependency)
- Existing `GEMINI_API_KEY` environment variable (already configured)
- Stories 17-1 and 17-2 are prerequisites; 17-3 through 17-6 build on them

**Timeline Impact:** None on existing work. Additive epic estimated at 5-6 stories.

**Success Criteria:**

- User can generate scene illustrations in all three modes
- Turn numbers are visible in narrative display
- Images persist in campaign directory across sessions
- Individual and bulk download work correctly
- Configuration UI allows model selection for both image generation and session scanning
