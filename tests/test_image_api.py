"""Tests for image generation API endpoints (Story 17-3).

Tests all image generation REST endpoints, schema validation,
background task error handling, and WebSocket event support.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.schemas import (
    ImageGenerateAccepted,
    ImageGenerateRequest,
    SceneImageResponse,
    WsImageReady,
)
from models import (
    SceneImage,
    SessionMetadata,
    create_initial_game_state,
)
from persistence import save_checkpoint, save_session_metadata

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _clear_image_task_state() -> Generator[None, None, None]:
    """Clear active image task tracking between tests to prevent leakage."""
    from api.routes import _active_image_tasks

    _active_image_tasks.clear()
    yield
    _active_image_tasks.clear()


@pytest.fixture
def temp_campaigns_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Patch CAMPAIGNS_DIR to a temp directory for test isolation."""
    temp_campaigns = tmp_path / "campaigns"
    temp_campaigns.mkdir()

    with patch("persistence.CAMPAIGNS_DIR", temp_campaigns):
        yield temp_campaigns


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def image_gen_enabled_config(tmp_path: Path) -> Generator[Path, None, None]:
    """Patch config so image generation is enabled."""
    defaults_path = tmp_path / "config" / "defaults.yaml"
    defaults_path.parent.mkdir(parents=True, exist_ok=True)
    config_data = {
        "image_generation": {
            "enabled": True,
            "image_provider": "gemini",
            "image_model": "imagen-4.0-generate-001",
            "scanner_provider": "gemini",
            "scanner_model": "gemini-3-flash-preview",
        }
    }
    defaults_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    with patch("config.PROJECT_ROOT", tmp_path):
        yield tmp_path


@pytest.fixture
def image_gen_disabled_config(tmp_path: Path) -> Generator[Path, None, None]:
    """Patch config so image generation is disabled."""
    defaults_path = tmp_path / "config" / "defaults.yaml"
    defaults_path.parent.mkdir(parents=True, exist_ok=True)
    config_data = {"image_generation": {"enabled": False}}
    defaults_path.write_text(yaml.safe_dump(config_data), encoding="utf-8")

    with (
        patch("config.PROJECT_ROOT", tmp_path),
        patch("config.load_user_settings", return_value={}),
        patch("api.routes.load_user_settings", return_value={}),
    ):
        yield tmp_path


def _create_test_session(
    campaigns_dir: Path,
    session_id: str = "001",
    session_number: int = 1,
    name: str = "Test Session",
    turn_count: int = 0,
    character_names: list[str] | None = None,
) -> SessionMetadata:
    """Helper to create a test session directory with metadata."""
    from datetime import UTC, datetime

    session_dir = campaigns_dir / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC).isoformat() + "Z"
    metadata = SessionMetadata(
        session_id=session_id,
        session_number=session_number,
        name=name,
        created_at=now,
        updated_at=now,
        character_names=character_names or [],
        turn_count=turn_count,
    )

    save_session_metadata(session_id, metadata)
    return metadata


def _create_test_checkpoint_with_log(
    campaigns_dir: Path,
    session_id: str,
    turn_number: int,
    log_entries: list[str] | None = None,
) -> None:
    """Helper to create a test checkpoint with a ground_truth_log."""
    state = create_initial_game_state()
    state["session_id"] = session_id
    if log_entries:
        state["ground_truth_log"] = log_entries
    save_checkpoint(state, session_id, turn_number, update_metadata=False)


def _create_image_metadata(
    campaigns_dir: Path,
    session_id: str,
    image_id: str = "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    turn_number: int = 5,
    prompt: str = "A dark dungeon corridor lit by torchlight",
    generation_mode: str = "current",
) -> dict[str, object]:
    """Helper to create a test image metadata JSON sidecar."""
    images_dir = campaigns_dir / f"session_{session_id}" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "id": image_id,
        "session_id": session_id,
        "turn_number": turn_number,
        "prompt": prompt,
        "image_path": f"session_{session_id}/images/{image_id}.png",
        "provider": "gemini",
        "model": "imagen-4.0-generate-001",
        "generation_mode": generation_mode,
        "generated_at": "2026-02-14T12:00:00Z",
    }

    json_path = images_dir / f"{image_id}.json"
    json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Also create a dummy PNG file
    png_path = images_dir / f"{image_id}.png"
    png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    return metadata


# =============================================================================
# Schema Tests
# =============================================================================


class TestImageSchemas:
    """Tests for image generation schema models."""

    def test_image_generate_request_defaults(self) -> None:
        """ImageGenerateRequest has correct defaults."""
        req = ImageGenerateRequest()
        assert req.context_entries == 10

    def test_image_generate_request_custom(self) -> None:
        """ImageGenerateRequest accepts custom context_entries."""
        req = ImageGenerateRequest(context_entries=25)
        assert req.context_entries == 25

    def test_image_generate_request_validation(self) -> None:
        """ImageGenerateRequest validates context_entries range."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ImageGenerateRequest(context_entries=0)

        with pytest.raises(ValidationError):
            ImageGenerateRequest(context_entries=51)

    def test_image_generate_accepted(self) -> None:
        """ImageGenerateAccepted creates correctly."""
        resp = ImageGenerateAccepted(
            task_id="abc-123",
            session_id="001",
            turn_number=5,
        )
        assert resp.task_id == "abc-123"
        assert resp.session_id == "001"
        assert resp.turn_number == 5
        assert resp.status == "pending"

    def test_scene_image_response(self) -> None:
        """SceneImageResponse creates correctly."""
        resp = SceneImageResponse(
            id="img-001",
            session_id="001",
            turn_number=5,
            prompt="A dark dungeon",
            image_path="session_001/images/img-001.png",
            provider="gemini",
            model="imagen-4.0-generate-001",
            generation_mode="current",
            generated_at="2026-02-14T12:00:00Z",
            download_url="/api/sessions/001/images/img-001.png",
        )
        assert resp.id == "img-001"
        assert resp.generation_mode == "current"
        assert resp.download_url == "/api/sessions/001/images/img-001.png"

    def test_ws_image_ready(self) -> None:
        """WsImageReady creates correctly with nested SceneImageResponse."""
        image_resp = SceneImageResponse(
            id="img-001",
            session_id="001",
            turn_number=5,
            prompt="A dark dungeon",
            image_path="session_001/images/img-001.png",
            provider="gemini",
            model="imagen-4.0-generate-001",
            generation_mode="current",
            generated_at="2026-02-14T12:00:00Z",
            download_url="/api/sessions/001/images/img-001.png",
        )
        ws_event = WsImageReady(image=image_resp)
        assert ws_event.type == "image_ready"
        assert ws_event.image.id == "img-001"

        # Verify serialization
        dumped = ws_event.model_dump()
        assert dumped["type"] == "image_ready"
        assert dumped["image"]["id"] == "img-001"


# =============================================================================
# Generate Current Scene Image Tests
# =============================================================================


class TestGenerateCurrentSceneImage:
    """Tests for POST /api/sessions/{session_id}/images/generate-current."""

    @pytest.mark.anyio
    async def test_returns_202_with_task_id(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_enabled_config: Path,
    ) -> None:
        """Returns 202 Accepted with a task ID."""
        _create_test_session(temp_campaigns_dir, "001")
        log_entries = [f"Turn {i}: Something happens." for i in range(15)]
        _create_test_checkpoint_with_log(temp_campaigns_dir, "001", 15, log_entries)

        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.add_done_callback = MagicMock()
        with patch("api.routes.asyncio.create_task", return_value=mock_task):
            resp = await client.post("/api/sessions/001/images/generate-current")

        assert resp.status_code == 202
        data = resp.json()
        assert "task_id" in data
        assert data["session_id"] == "001"
        assert data["turn_number"] == 14  # len(log) - 1
        assert data["status"] == "pending"

    @pytest.mark.anyio
    async def test_returns_400_when_disabled(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_disabled_config: Path,
    ) -> None:
        """Returns 400 when image generation is disabled."""
        _create_test_session(temp_campaigns_dir, "001")
        log_entries = ["Turn 0: The adventure begins."]
        _create_test_checkpoint_with_log(temp_campaigns_dir, "001", 1, log_entries)

        resp = await client.post("/api/sessions/001/images/generate-current")
        assert resp.status_code == 400
        assert "not enabled" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_returns_404_for_nonexistent_session(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_enabled_config: Path,
    ) -> None:
        """Returns 404 for a session that doesn't exist."""
        resp = await client.post("/api/sessions/999/images/generate-current")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_returns_400_for_empty_log(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_enabled_config: Path,
    ) -> None:
        """Returns 400 when session has no log entries."""
        _create_test_session(temp_campaigns_dir, "001")
        _create_test_checkpoint_with_log(temp_campaigns_dir, "001", 0, [])

        resp = await client.post("/api/sessions/001/images/generate-current")
        assert resp.status_code == 400
        assert "no narrative log entries" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_custom_context_entries(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_enabled_config: Path,
    ) -> None:
        """Accepts custom context_entries in request body."""
        _create_test_session(temp_campaigns_dir, "001")
        log_entries = [f"Turn {i}: Something happens." for i in range(20)]
        _create_test_checkpoint_with_log(temp_campaigns_dir, "001", 20, log_entries)

        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.add_done_callback = MagicMock()
        with patch("api.routes.asyncio.create_task", return_value=mock_task):
            resp = await client.post(
                "/api/sessions/001/images/generate-current",
                json={"context_entries": 5},
            )

        assert resp.status_code == 202

    @pytest.mark.anyio
    async def test_returns_429_when_too_many_concurrent_tasks(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_enabled_config: Path,
    ) -> None:
        """Returns 429 when concurrent image task limit is exceeded."""
        from api.routes import _MAX_CONCURRENT_IMAGE_TASKS, _active_image_tasks

        _create_test_session(temp_campaigns_dir, "001")
        log_entries = [f"Turn {i}: Something happens." for i in range(15)]
        _create_test_checkpoint_with_log(temp_campaigns_dir, "001", 15, log_entries)

        # Pre-fill active tasks to exceed limit
        fake_tasks: set[asyncio.Task[None]] = set()
        for _ in range(_MAX_CONCURRENT_IMAGE_TASKS):
            mock_task = MagicMock()
            mock_task.done.return_value = False
            fake_tasks.add(mock_task)
        _active_image_tasks["001"] = fake_tasks  # type: ignore[assignment]

        resp = await client.post("/api/sessions/001/images/generate-current")
        assert resp.status_code == 429
        assert "Too many concurrent" in resp.json()["detail"]


# =============================================================================
# Generate Turn Image Tests
# =============================================================================


class TestGenerateTurnImage:
    """Tests for POST /api/sessions/{session_id}/images/generate-turn/{turn_number}."""

    @pytest.mark.anyio
    async def test_returns_202_with_valid_turn(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_enabled_config: Path,
    ) -> None:
        """Returns 202 Accepted with a valid turn number."""
        _create_test_session(temp_campaigns_dir, "001")
        log_entries = [f"Turn {i}: Something happens." for i in range(20)]
        _create_test_checkpoint_with_log(temp_campaigns_dir, "001", 20, log_entries)

        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.add_done_callback = MagicMock()
        with patch("api.routes.asyncio.create_task", return_value=mock_task):
            resp = await client.post("/api/sessions/001/images/generate-turn/10")

        assert resp.status_code == 202
        data = resp.json()
        assert data["turn_number"] == 10
        assert data["status"] == "pending"

    @pytest.mark.anyio
    async def test_returns_400_for_out_of_range_turn(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_enabled_config: Path,
    ) -> None:
        """Returns 400 for a turn number out of range."""
        _create_test_session(temp_campaigns_dir, "001")
        log_entries = [f"Turn {i}: Something happens." for i in range(10)]
        _create_test_checkpoint_with_log(temp_campaigns_dir, "001", 10, log_entries)

        resp = await client.post("/api/sessions/001/images/generate-turn/50")
        assert resp.status_code == 400
        assert "out of range" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_returns_400_for_negative_turn(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_enabled_config: Path,
    ) -> None:
        """Returns 400 for a negative turn number."""
        _create_test_session(temp_campaigns_dir, "001")
        log_entries = ["Turn 0: Start."]
        _create_test_checkpoint_with_log(temp_campaigns_dir, "001", 1, log_entries)

        resp = await client.post("/api/sessions/001/images/generate-turn/-1")
        # FastAPI will reject negative path param as 422 or we handle as 400
        assert resp.status_code in (400, 422)

    @pytest.mark.anyio
    async def test_returns_400_when_disabled(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_disabled_config: Path,
    ) -> None:
        """Returns 400 when image generation is disabled."""
        _create_test_session(temp_campaigns_dir, "001")
        log_entries = ["Turn 0: Start."]
        _create_test_checkpoint_with_log(temp_campaigns_dir, "001", 1, log_entries)

        resp = await client.post("/api/sessions/001/images/generate-turn/0")
        assert resp.status_code == 400
        assert "not enabled" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_returns_404_for_nonexistent_session(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_enabled_config: Path,
    ) -> None:
        """Returns 404 for a session that doesn't exist."""
        resp = await client.post("/api/sessions/999/images/generate-turn/0")
        assert resp.status_code == 404


# =============================================================================
# List Session Images Tests
# =============================================================================


class TestListSessionImages:
    """Tests for GET /api/sessions/{session_id}/images."""

    @pytest.mark.anyio
    async def test_returns_empty_list_no_images(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns empty list for session with no images."""
        _create_test_session(temp_campaigns_dir, "001")

        resp = await client.get("/api/sessions/001/images")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_returns_metadata_with_images(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns image metadata for sessions with images."""
        _create_test_session(temp_campaigns_dir, "001")
        image_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id=image_id,
            turn_number=5,
        )

        resp = await client.get("/api/sessions/001/images")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == image_id
        assert data[0]["turn_number"] == 5
        assert data[0]["download_url"] == f"/api/sessions/001/images/{image_id}.png"

    @pytest.mark.anyio
    async def test_returns_multiple_images_sorted(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns multiple images sorted by filename."""
        _create_test_session(temp_campaigns_dir, "001")
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id="a0000000-0000-0000-0000-000000000001",
            turn_number=1,
        )
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id="a0000000-0000-0000-0000-000000000002",
            turn_number=10,
        )

        resp = await client.get("/api/sessions/001/images")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    @pytest.mark.anyio
    async def test_returns_404_for_nonexistent_session(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns 404 for a session that doesn't exist."""
        resp = await client.get("/api/sessions/999/images")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_skips_invalid_metadata(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Skips JSON files with invalid/incomplete metadata."""
        _create_test_session(temp_campaigns_dir, "001")
        images_dir = temp_campaigns_dir / "session_001" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON sidecar (missing required fields)
        bad_json = images_dir / "bad-metadata.json"
        bad_json.write_text('{"id": "bad"}', encoding="utf-8")

        # Also add one good metadata file
        _create_image_metadata(temp_campaigns_dir, "001")

        resp = await client.get("/api/sessions/001/images")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1  # Only the good one


# =============================================================================
# Serve Session Image Tests
# =============================================================================


class TestServeSessionImage:
    """Tests for GET /api/sessions/{session_id}/images/{image_filename}."""

    @pytest.mark.anyio
    async def test_serves_existing_image(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Serves an existing image file."""
        _create_test_session(temp_campaigns_dir, "001")
        image_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        _create_image_metadata(temp_campaigns_dir, "001", image_id=image_id)

        resp = await client.get(f"/api/sessions/001/images/{image_id}.png")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"

    @pytest.mark.anyio
    async def test_rejects_invalid_filename_format(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Rejects non-UUID filename format (path traversal prevention)."""
        _create_test_session(temp_campaigns_dir, "001")

        resp = await client.get("/api/sessions/001/images/../../etc/passwd.png")
        assert resp.status_code in (400, 404)

    @pytest.mark.anyio
    async def test_rejects_traversal_attempt(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Rejects path traversal attempts."""
        _create_test_session(temp_campaigns_dir, "001")

        resp = await client.get("/api/sessions/001/images/not-a-uuid.png")
        assert resp.status_code == 400
        assert "Invalid image filename format" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_returns_404_for_missing_image(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns 404 when image file doesn't exist."""
        _create_test_session(temp_campaigns_dir, "001")

        resp = await client.get(
            "/api/sessions/001/images/a1b2c3d4-e5f6-7890-abcd-ef1234567890.png"
        )
        assert resp.status_code == 404


# =============================================================================
# Background Task Error Handling Tests
# =============================================================================


class TestBackgroundTaskErrorHandling:
    """Tests for _generate_image_background error handling."""

    @pytest.mark.anyio
    async def test_handles_image_generation_error(self) -> None:
        """Background task catches ImageGenerationError and broadcasts error."""
        from api.routes import _generate_image_background

        mock_manager = AsyncMock()

        with (
            patch("image_gen.ImageGenerator") as mock_gen_cls,
            patch("api.websocket.manager", mock_manager),
        ):
            from image_gen import ImageGenerationError

            mock_gen = mock_gen_cls.return_value
            mock_gen.build_scene_prompt = AsyncMock(return_value="test prompt")
            mock_gen.generate_scene_image = AsyncMock(
                side_effect=ImageGenerationError("API failed")
            )

            # Should NOT raise -- errors caught internally
            await _generate_image_background(
                session_id="001",
                task_id="task-123",
                log_entries=["Turn 1: Test."],
                characters={},
                turn_number=1,
                generation_mode="current",
            )

        # Verify error was broadcast
        mock_manager.broadcast.assert_called()
        call_args = mock_manager.broadcast.call_args
        assert call_args[0][0] == "001"
        event = call_args[0][1]
        assert event["type"] == "error"
        assert "failed" in event["message"].lower()

    @pytest.mark.anyio
    async def test_handles_unexpected_error(self) -> None:
        """Background task catches unexpected exceptions and broadcasts error."""
        from api.routes import _generate_image_background

        mock_manager = AsyncMock()

        with (
            patch("image_gen.ImageGenerator") as mock_gen_cls,
            patch("api.websocket.manager", mock_manager),
        ):
            mock_gen = mock_gen_cls.return_value
            mock_gen.build_scene_prompt = AsyncMock(
                side_effect=RuntimeError("Unexpected boom")
            )

            # Should NOT raise
            await _generate_image_background(
                session_id="001",
                task_id="task-456",
                log_entries=["Turn 1: Test."],
                characters={},
                turn_number=1,
                generation_mode="current",
            )

        # Verify error was broadcast
        mock_manager.broadcast.assert_called()
        event = mock_manager.broadcast.call_args[0][1]
        assert event["type"] == "error"
        assert event["recoverable"] is True

    @pytest.mark.anyio
    async def test_success_saves_metadata_and_broadcasts(self) -> None:
        """Background task saves metadata and broadcasts image_ready on success."""
        from api.routes import _generate_image_background

        mock_manager = AsyncMock()

        mock_scene_image = MagicMock(spec=SceneImage)
        mock_scene_image.id = "img-uuid-123"
        mock_scene_image.session_id = "001"
        mock_scene_image.turn_number = 5
        mock_scene_image.prompt = "A dark corridor"
        mock_scene_image.image_path = "session_001/images/img-uuid-123.png"
        mock_scene_image.provider = "gemini"
        mock_scene_image.model = "imagen-4.0-generate-001"
        mock_scene_image.generation_mode = "current"
        mock_scene_image.generated_at = "2026-02-14T12:00:00Z"
        mock_scene_image.model_dump.return_value = {
            "id": "img-uuid-123",
            "session_id": "001",
            "turn_number": 5,
            "prompt": "A dark corridor",
            "image_path": "session_001/images/img-uuid-123.png",
            "provider": "gemini",
            "model": "imagen-4.0-generate-001",
            "generation_mode": "current",
            "generated_at": "2026-02-14T12:00:00Z",
        }

        mock_images_dir = MagicMock()
        mock_metadata_path = MagicMock()
        mock_images_dir.__truediv__ = MagicMock(return_value=mock_metadata_path)
        mock_images_dir.mkdir = MagicMock()

        with (
            patch("image_gen.ImageGenerator") as mock_gen_cls,
            patch("api.websocket.manager", mock_manager),
            patch("api.routes.get_session_dir") as mock_session_dir,
        ):
            mock_gen = mock_gen_cls.return_value
            mock_gen.build_scene_prompt = AsyncMock(return_value="A dark corridor")
            mock_gen.generate_scene_image = AsyncMock(return_value=mock_scene_image)
            mock_session_dir.return_value.__truediv__ = MagicMock(
                return_value=mock_images_dir
            )

            await _generate_image_background(
                session_id="001",
                task_id="task-789",
                log_entries=["Turn 5: Enter the dungeon."],
                characters={"Rogue": {"character_class": "Rogue"}},
                turn_number=5,
                generation_mode="current",
            )

        # Verify WebSocket broadcast was called with image_ready
        mock_manager.broadcast.assert_called_once()
        call_args = mock_manager.broadcast.call_args
        assert call_args[0][0] == "001"
        event = call_args[0][1]
        assert event["type"] == "image_ready"
        assert event["image"]["id"] == "img-uuid-123"
        assert (
            event["image"]["download_url"]
            == "/api/sessions/001/images/img-uuid-123.png"
        )


# =============================================================================
# WebSocket Event Schema Tests
# =============================================================================


class TestWebSocketImageReadyEvent:
    """Tests for image_ready event in _engine_event_to_schema()."""

    def test_engine_event_to_schema_image_ready(self) -> None:
        """_engine_event_to_schema handles image_ready events."""
        from api.websocket import _engine_event_to_schema

        event = {
            "type": "image_ready",
            "image": {
                "id": "img-001",
                "session_id": "001",
                "turn_number": 5,
                "prompt": "A dark dungeon",
                "image_path": "session_001/images/img-001.png",
                "provider": "gemini",
                "model": "imagen-4.0-generate-001",
                "generation_mode": "current",
                "generated_at": "2026-02-14T12:00:00Z",
                "download_url": "/api/sessions/001/images/img-001.png",
            },
        }

        result = _engine_event_to_schema(event)
        assert result["type"] == "image_ready"
        assert result["image"]["id"] == "img-001"
        assert result["image"]["turn_number"] == 5


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestImageHelpers:
    """Tests for image-related helper functions."""

    def test_build_download_url(self) -> None:
        """_build_download_url constructs correct URL."""
        from api.routes import _build_download_url

        url = _build_download_url("001", "abc-123-def")
        assert url == "/api/sessions/001/images/abc-123-def.png"

    def test_check_image_generation_enabled_raises_when_disabled(
        self,
        image_gen_disabled_config: Path,
    ) -> None:
        """_check_image_generation_enabled raises HTTPException when disabled."""
        from fastapi import HTTPException

        from api.routes import _check_image_generation_enabled

        with pytest.raises(HTTPException) as exc_info:
            _check_image_generation_enabled()
        assert exc_info.value.status_code == 400
        assert "not enabled" in str(exc_info.value.detail)

    def test_check_image_generation_enabled_passes_when_enabled(
        self,
        image_gen_enabled_config: Path,
    ) -> None:
        """_check_image_generation_enabled does not raise when enabled."""
        from api.routes import _check_image_generation_enabled

        # Should not raise
        _check_image_generation_enabled()

    def test_check_image_generation_enabled_raises_when_no_config(
        self,
        tmp_path: Path,
    ) -> None:
        """_check_image_generation_enabled raises when no config section exists."""
        from fastapi import HTTPException

        from api.routes import _check_image_generation_enabled

        defaults_path = tmp_path / "config" / "defaults.yaml"
        defaults_path.parent.mkdir(parents=True, exist_ok=True)
        defaults_path.write_text(yaml.safe_dump({}), encoding="utf-8")

        with (
            patch("config.PROJECT_ROOT", tmp_path),
            patch("api.routes.load_user_settings", return_value={}),
        ):
            with pytest.raises(HTTPException) as exc_info:
                _check_image_generation_enabled()
            assert exc_info.value.status_code == 400

    def test_image_id_re(self) -> None:
        """_IMAGE_ID_RE matches UUID without .png extension."""
        from api.routes import _IMAGE_ID_RE

        assert _IMAGE_ID_RE.match("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        assert not _IMAGE_ID_RE.match("a1b2c3d4-e5f6-7890-abcd-ef1234567890.png")
        assert not _IMAGE_ID_RE.match("not-a-uuid")
        assert not _IMAGE_ID_RE.match("")

    def test_get_safe_session_name_with_name(
        self,
        temp_campaigns_dir: Path,
    ) -> None:
        """_get_safe_session_name returns sanitized session name."""
        from api.routes import _get_safe_session_name

        _create_test_session(temp_campaigns_dir, "001", name="Curse of Strahd!")
        result = _get_safe_session_name("001")
        assert result == "Curse_of_Strahd"
        # No spaces, exclamation marks, etc.
        assert " " not in result
        assert "!" not in result

    def test_get_safe_session_name_fallback(
        self,
        temp_campaigns_dir: Path,
    ) -> None:
        """_get_safe_session_name falls back to session_id when name is empty."""
        from api.routes import _get_safe_session_name

        _create_test_session(temp_campaigns_dir, "001", name="")
        result = _get_safe_session_name("001")
        assert result == "session_001"

    def test_get_safe_session_name_special_chars(
        self,
        temp_campaigns_dir: Path,
    ) -> None:
        """_get_safe_session_name sanitizes special characters."""
        from api.routes import _get_safe_session_name

        _create_test_session(temp_campaigns_dir, "001", name="A/B\\C:D*E?F")
        result = _get_safe_session_name("001")
        # All special chars replaced with underscore, collapsed
        assert "/" not in result
        assert "\\" not in result
        assert ":" not in result
        assert "*" not in result
        assert "?" not in result

    def test_get_safe_session_name_truncates(
        self,
        temp_campaigns_dir: Path,
    ) -> None:
        """_get_safe_session_name truncates long names to 50 chars."""
        from api.routes import _get_safe_session_name

        _create_test_session(temp_campaigns_dir, "001", name="A" * 100)
        result = _get_safe_session_name("001")
        assert len(result) <= 50


# =============================================================================
# Individual Image Download Endpoint Tests (Story 17-6)
# =============================================================================


class TestDownloadSessionImage:
    """Tests for GET /api/sessions/{session_id}/images/{image_id}/download."""

    @pytest.mark.anyio
    async def test_downloads_image_with_content_disposition(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns image file with Content-Disposition: attachment header."""
        _create_test_session(temp_campaigns_dir, "001", name="Test Session")
        image_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id=image_id,
            turn_number=5,
            generation_mode="current",
        )

        resp = await client.get(f"/api/sessions/001/images/{image_id}/download")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        content_disp = resp.headers["content-disposition"]
        assert "attachment" in content_disp
        assert "Test_Session_turn_6_current.png" in content_disp

    @pytest.mark.anyio
    async def test_download_filename_uses_1_based_turn(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Filename uses 1-based turn number (turn_number + 1)."""
        _create_test_session(temp_campaigns_dir, "001", name="My Campaign")
        image_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id=image_id,
            turn_number=0,
            generation_mode="best",
        )

        resp = await client.get(f"/api/sessions/001/images/{image_id}/download")
        assert resp.status_code == 200
        content_disp = resp.headers["content-disposition"]
        assert "My_Campaign_turn_1_best.png" in content_disp

    @pytest.mark.anyio
    async def test_download_invalid_image_id_returns_400(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns 400 for invalid image ID format."""
        _create_test_session(temp_campaigns_dir, "001")

        resp = await client.get("/api/sessions/001/images/not-a-uuid/download")
        assert resp.status_code == 400
        assert "Invalid image ID format" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_download_nonexistent_image_returns_404(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns 404 when image file doesn't exist."""
        _create_test_session(temp_campaigns_dir, "001")

        resp = await client.get(
            "/api/sessions/001/images/a1b2c3d4-e5f6-7890-abcd-ef1234567890/download"
        )
        assert resp.status_code == 404
        assert "Image not found" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_download_nonexistent_session_returns_404(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns 404 for a session that doesn't exist."""
        resp = await client.get(
            "/api/sessions/999/images/a1b2c3d4-e5f6-7890-abcd-ef1234567890/download"
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_download_without_metadata_uses_defaults(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """When JSON sidecar is missing, defaults to turn 1 and 'scene' mode."""
        _create_test_session(temp_campaigns_dir, "001", name="Test")
        image_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

        # Create only the PNG file, no JSON sidecar
        images_dir = temp_campaigns_dir / "session_001" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        png_path = images_dir / f"{image_id}.png"
        png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        resp = await client.get(f"/api/sessions/001/images/{image_id}/download")
        assert resp.status_code == 200
        content_disp = resp.headers["content-disposition"]
        assert "Test_turn_1_scene.png" in content_disp


# =============================================================================
# Bulk Download (Zip) Endpoint Tests (Story 17-6)
# =============================================================================


class TestDownloadAllSessionImages:
    """Tests for GET /api/sessions/{session_id}/images/download-all."""

    @pytest.mark.anyio
    async def test_download_all_returns_zip(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns a zip file with correct content type."""
        import zipfile
        from io import BytesIO

        _create_test_session(temp_campaigns_dir, "001", name="Test Session")
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id="a0000000-0000-0000-0000-000000000001",
            turn_number=1,
            generation_mode="current",
        )
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id="a0000000-0000-0000-0000-000000000002",
            turn_number=5,
            generation_mode="best",
        )

        resp = await client.get("/api/sessions/001/images/download-all")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        content_disp = resp.headers["content-disposition"]
        assert "attachment" in content_disp
        assert "Test_Session_images.zip" in content_disp

        # Verify zip contents
        zf = zipfile.ZipFile(BytesIO(resp.content))
        names = zf.namelist()
        assert len(names) == 2
        assert "Test_Session_turn_2_current.png" in names
        assert "Test_Session_turn_6_best.png" in names
        zf.close()

    @pytest.mark.anyio
    async def test_download_all_empty_session_returns_404(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns 404 with message when session has no images."""
        _create_test_session(temp_campaigns_dir, "001")

        resp = await client.get("/api/sessions/001/images/download-all")
        assert resp.status_code == 404
        assert "No images to download" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_download_all_no_images_dir_returns_404(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns 404 when images directory doesn't exist."""
        _create_test_session(temp_campaigns_dir, "001")

        resp = await client.get("/api/sessions/001/images/download-all")
        assert resp.status_code == 404
        assert "No images to download" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_download_all_nonexistent_session_returns_404(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns 404 for a session that doesn't exist."""
        resp = await client.get("/api/sessions/999/images/download-all")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_download_all_sanitizes_session_name(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Zip filename uses sanitized session name."""
        _create_test_session(
            temp_campaigns_dir, "001", name="My Campaign: Part 2!"
        )
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id="a0000000-0000-0000-0000-000000000001",
            turn_number=0,
        )

        resp = await client.get("/api/sessions/001/images/download-all")
        assert resp.status_code == 200
        content_disp = resp.headers["content-disposition"]
        assert "My_Campaign_Part_2_images.zip" in content_disp

    @pytest.mark.anyio
    async def test_download_all_without_metadata_uses_defaults(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Images without JSON sidecar use default turn_number=0 and mode=scene."""
        import zipfile
        from io import BytesIO

        _create_test_session(temp_campaigns_dir, "001", name="Test")
        images_dir = temp_campaigns_dir / "session_001" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)

        # Create a PNG without JSON sidecar
        image_id = "a0000000-0000-0000-0000-000000000001"
        png_path = images_dir / f"{image_id}.png"
        png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        resp = await client.get("/api/sessions/001/images/download-all")
        assert resp.status_code == 200

        zf = zipfile.ZipFile(BytesIO(resp.content))
        names = zf.namelist()
        assert len(names) == 1
        assert "Test_turn_1_scene.png" in names
        zf.close()

    @pytest.mark.anyio
    async def test_download_all_deduplicates_filenames(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Zip deduplicates filenames when multiple images share turn+mode."""
        import zipfile
        from io import BytesIO

        _create_test_session(temp_campaigns_dir, "001", name="Test")
        # Two images with the same turn_number and generation_mode
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id="a0000000-0000-0000-0000-000000000001",
            turn_number=3,
            generation_mode="current",
        )
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id="a0000000-0000-0000-0000-000000000002",
            turn_number=3,
            generation_mode="current",
        )

        resp = await client.get("/api/sessions/001/images/download-all")
        assert resp.status_code == 200

        zf = zipfile.ZipFile(BytesIO(resp.content))
        names = zf.namelist()
        assert len(names) == 2  # Both images should be included
        assert "Test_turn_4_current.png" in names
        assert "Test_turn_4_current_2.png" in names
        zf.close()

    @pytest.mark.anyio
    async def test_download_all_route_not_caught_by_filename_pattern(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """The download-all route is not captured by {image_filename} catch-all."""
        _create_test_session(temp_campaigns_dir, "001")

        # This should hit download_all_session_images, not serve_session_image
        resp = await client.get("/api/sessions/001/images/download-all")
        # Should get 404 (no images) not 400 (invalid filename format)
        assert resp.status_code == 404
        assert "No images to download" in resp.json()["detail"]


# =============================================================================
# Session Image Summary Endpoint Tests (Story 17-8)
# =============================================================================


class TestListSessionImageSummaries:
    """Tests for GET /api/sessions/images/summary."""

    @pytest.mark.anyio
    async def test_returns_empty_list_when_no_sessions(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns empty list when no sessions have images."""
        resp = await client.get("/api/sessions/images/summary")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_returns_empty_when_sessions_exist_but_no_images(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns empty list when sessions exist but none have images."""
        _create_test_session(temp_campaigns_dir, "001", name="Session A")
        _create_test_session(temp_campaigns_dir, "002", name="Session B")

        resp = await client.get("/api/sessions/images/summary")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_returns_correct_counts(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Returns correct image counts for sessions with images."""
        _create_test_session(temp_campaigns_dir, "001", name="Adventure Alpha")
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id="a0000000-0000-0000-0000-000000000001",
            turn_number=1,
        )
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id="a0000000-0000-0000-0000-000000000002",
            turn_number=5,
        )

        _create_test_session(temp_campaigns_dir, "002", name="Adventure Beta")
        _create_image_metadata(
            temp_campaigns_dir,
            "002",
            image_id="b0000000-0000-0000-0000-000000000001",
            turn_number=3,
        )

        resp = await client.get("/api/sessions/images/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        # Sorted alphabetically by session_name
        assert data[0]["session_id"] == "001"
        assert data[0]["session_name"] == "Adventure Alpha"
        assert data[0]["image_count"] == 2
        assert data[1]["session_id"] == "002"
        assert data[1]["session_name"] == "Adventure Beta"
        assert data[1]["image_count"] == 1

    @pytest.mark.anyio
    async def test_excludes_sessions_with_zero_images(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Sessions with 0 images are excluded from results."""
        _create_test_session(temp_campaigns_dir, "001", name="Has Images")
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id="a0000000-0000-0000-0000-000000000001",
            turn_number=1,
        )

        _create_test_session(temp_campaigns_dir, "002", name="No Images")
        # session_002 has no images directory

        resp = await client.get("/api/sessions/images/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["session_id"] == "001"

    @pytest.mark.anyio
    async def test_returns_correct_session_name_from_metadata(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Uses session name from metadata when available."""
        _create_test_session(
            temp_campaigns_dir, "001", name="Curse of Strahd"
        )
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id="a0000000-0000-0000-0000-000000000001",
            turn_number=1,
        )

        resp = await client.get("/api/sessions/images/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["session_name"] == "Curse of Strahd"

    @pytest.mark.anyio
    async def test_falls_back_to_session_id_when_no_name(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Falls back to 'Session {id}' when metadata has no name."""
        _create_test_session(temp_campaigns_dir, "001", name="")
        _create_image_metadata(
            temp_campaigns_dir,
            "001",
            image_id="a0000000-0000-0000-0000-000000000001",
            turn_number=1,
        )

        resp = await client.get("/api/sessions/images/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["session_name"] == "Session 001"

    @pytest.mark.anyio
    async def test_empty_images_dir_excluded(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """Sessions with empty images/ directory are excluded."""
        _create_test_session(temp_campaigns_dir, "001", name="Empty")
        images_dir = temp_campaigns_dir / "session_001" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        # No JSON files inside

        resp = await client.get("/api/sessions/images/summary")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_route_not_caught_by_session_id_wildcard(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
    ) -> None:
        """The /sessions/images/summary route is not swallowed by /sessions/{session_id}."""
        # This is the critical route ordering test.
        # If the route is registered AFTER {session_id}, FastAPI would treat
        # "images" as a session_id and return 400/404 from get_session.
        resp = await client.get("/api/sessions/images/summary")
        assert resp.status_code == 200
        # Should be a list, not an error response
        assert isinstance(resp.json(), list)
