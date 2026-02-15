"""Tests for the best scene scanner (Story 17-4).

Tests scanner methods on ImageGenerator (token estimation, chunking,
response parsing, full scan), the generate-best API endpoint, and
the background task error handling.
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
from api.schemas import BestSceneAccepted
from image_gen import (
    TOKENS_PER_WORD,
    ImageGenerationError,
    ImageGenerator,
)
from models import (
    ImageGenerationConfig,
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
            "scanner_token_limit": 4000,
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


@pytest.fixture
def image_generator() -> ImageGenerator:
    """Create an ImageGenerator instance for testing."""
    return ImageGenerator()


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


# =============================================================================
# _estimate_tokens Tests
# =============================================================================


class TestEstimateTokens:
    """Tests for ImageGenerator._estimate_tokens()."""

    def test_basic_word_count(self) -> None:
        """Estimates tokens as words * 1.3."""
        text = "one two three four five"  # 5 words
        result = ImageGenerator._estimate_tokens(text)
        assert result == int(5 * TOKENS_PER_WORD)

    def test_empty_string(self) -> None:
        """Empty string returns 0 tokens."""
        assert ImageGenerator._estimate_tokens("") == 0

    def test_single_word(self) -> None:
        """Single word returns int(1 * 1.3) = 1."""
        assert ImageGenerator._estimate_tokens("hello") == int(1 * TOKENS_PER_WORD)

    def test_long_text(self) -> None:
        """Longer text scales linearly with word count."""
        words = ["word"] * 100
        text = " ".join(words)
        result = ImageGenerator._estimate_tokens(text)
        assert result == int(100 * TOKENS_PER_WORD)


# =============================================================================
# _chunk_log_entries Tests
# =============================================================================


class TestChunkLogEntries:
    """Tests for ImageGenerator._chunk_log_entries()."""

    def test_empty_log_returns_empty(self) -> None:
        """Empty log returns empty list of chunks."""
        result = ImageGenerator._chunk_log_entries([], 4000)
        assert result == []

    def test_single_chunk_when_fits(self) -> None:
        """Returns single chunk when entire log fits within limit."""
        entries = ["short entry"] * 5
        result = ImageGenerator._chunk_log_entries(entries, 100000)
        assert len(result) == 1
        offset, chunk_entries = result[0]
        assert offset == 0
        assert chunk_entries == entries

    def test_multiple_chunks_with_overlap(self) -> None:
        """Splits into multiple chunks with correct overlap."""
        # Create entries with enough words/tokens to force chunking.
        # Each entry ~10 words = ~13 tokens. With 200 entries and
        # token_limit=500, effective_limit=400, each chunk holds ~30 entries.
        # Overlap of 20 means chunks share entries.
        entries = [
            f"This is entry number {i} with some extra words here" for i in range(200)
        ]
        result = ImageGenerator._chunk_log_entries(entries, 500)
        assert len(result) > 1

        # Verify overlap: last entries of chunk N should appear in chunk N+1
        for i in range(len(result) - 1):
            _, current_chunk = result[i]
            _, next_chunk = result[i + 1]
            # The next chunk should start with entries from the tail of current
            overlap = set(current_chunk) & set(next_chunk)
            assert len(overlap) > 0, (
                f"No overlap between chunk {i} (len={len(current_chunk)}) "
                f"and chunk {i + 1} (len={len(next_chunk)})"
            )

    def test_chunk_offsets_are_correct(self) -> None:
        """Chunk start offsets correctly map back to global indices."""
        entries = [
            f"This is entry number {i} with some extra words here" for i in range(200)
        ]
        result = ImageGenerator._chunk_log_entries(entries, 500)
        assert len(result) > 1

        for offset, chunk_entries in result:
            # The first entry in each chunk should match entries[offset]
            assert chunk_entries[0] == entries[offset], (
                f"Chunk at offset {offset}: first entry mismatch"
            )
            # All entries should match their global positions
            for j, entry in enumerate(chunk_entries):
                assert entry == entries[offset + j]

    def test_very_small_token_limit(self) -> None:
        """Very small token limit still makes progress (no infinite loop)."""
        entries = ["A single entry with a few words."] * 5
        # Token limit so small each entry gets its own chunk
        result = ImageGenerator._chunk_log_entries(entries, 5)
        assert len(result) >= 1
        # All entries should be covered
        all_covered = []
        for _offset, chunk in result:
            all_covered.extend(chunk)
        # Each original entry should appear at least once
        for entry in entries:
            assert entry in all_covered

    def test_all_entries_covered(self) -> None:
        """Every entry appears in at least one chunk."""
        entries = [f"Entry {i}" for i in range(50)]
        result = ImageGenerator._chunk_log_entries(entries, 50)
        covered = set()
        for _offset, chunk in result:
            for entry in chunk:
                covered.add(entry)
        for entry in entries:
            assert entry in covered


# =============================================================================
# _parse_scanner_response Tests
# =============================================================================


class TestParseScannerResponse:
    """Tests for ImageGenerator._parse_scanner_response()."""

    def test_valid_json(self) -> None:
        """Parses valid JSON with turn_number and rationale."""
        response = json.dumps(
            {
                "turn_number": 47,
                "rationale": "Epic dragon battle with fire and destruction",
            }
        )
        turn, rationale = ImageGenerator._parse_scanner_response(response)
        assert turn == 47
        assert "dragon" in rationale.lower()

    def test_json_with_markdown_fences(self) -> None:
        """Parses JSON wrapped in markdown code fences."""
        response = '```json\n{"turn_number": 12, "rationale": "Castle siege"}\n```'
        turn, rationale = ImageGenerator._parse_scanner_response(response)
        assert turn == 12
        assert "Castle siege" in rationale

    def test_regex_fallback_turn_N(self) -> None:
        """Falls back to regex for plain text with 'Turn N' pattern."""
        response = "The best scene is at Turn 23 where the party fights a dragon."
        turn, rationale = ImageGenerator._parse_scanner_response(response)
        assert turn == 23

    def test_regex_fallback_turn_number_colon(self) -> None:
        """Falls back to regex for 'turn number: N' pattern."""
        response = "I select turn number: 55 because of the dramatic reveal."
        turn, rationale = ImageGenerator._parse_scanner_response(response)
        assert turn == 55

    def test_regex_fallback_turn_hash(self) -> None:
        """Falls back to regex for 'Turn #N' pattern."""
        response = "Turn #42 has the most dramatic scene."
        turn, rationale = ImageGenerator._parse_scanner_response(response)
        assert turn == 42

    def test_raises_when_no_turn_found(self) -> None:
        """Raises ImageGenerationError when no turn number in response."""
        response = "I cannot identify any specific scene from this log."
        with pytest.raises(ImageGenerationError, match="Scanner failed to identify"):
            ImageGenerator._parse_scanner_response(response)

    def test_invalid_json_with_turn_in_text(self) -> None:
        """Falls back to regex when JSON is malformed but text has turn info."""
        response = '{"turn_number": invalid} Turn 99 has great action.'
        turn, rationale = ImageGenerator._parse_scanner_response(response)
        assert turn == 99

    def test_json_turn_number_as_string(self) -> None:
        """Handles turn_number as string in JSON (coerces to int)."""
        response = json.dumps(
            {"turn_number": "15", "rationale": "A magical portal opens"}
        )
        turn, rationale = ImageGenerator._parse_scanner_response(response)
        assert turn == 15

    def test_negative_turn_number_falls_back_to_regex(self) -> None:
        """Negative turn_number in JSON is rejected, falls back to regex."""
        response = '{"turn_number": -5, "rationale": "bad"} Turn 10 is great.'
        turn, rationale = ImageGenerator._parse_scanner_response(response)
        # Regex fallback finds Turn 10
        assert turn == 10

    def test_negative_turn_number_no_fallback_raises(self) -> None:
        """Negative turn_number with no regex fallback raises error."""
        response = json.dumps({"turn_number": -1, "rationale": "bad value"})
        with pytest.raises(ImageGenerationError, match="Scanner failed to identify"):
            ImageGenerator._parse_scanner_response(response)


# =============================================================================
# _format_log_for_scanner Tests
# =============================================================================


class TestFormatLogForScanner:
    """Tests for ImageGenerator._format_log_for_scanner()."""

    def test_prepends_turn_numbers(self) -> None:
        """Each entry gets [Turn N] prefix."""
        entries = ["Entry A", "Entry B", "Entry C"]
        result = ImageGenerator._format_log_for_scanner(entries)
        assert "[Turn 0] Entry A" in result
        assert "[Turn 1] Entry B" in result
        assert "[Turn 2] Entry C" in result

    def test_zero_indexed(self) -> None:
        """Turn numbers are 0-based."""
        entries = ["First"]
        result = ImageGenerator._format_log_for_scanner(entries)
        assert result.startswith("[Turn 0]")

    def test_entries_separated_by_double_newlines(self) -> None:
        """Entries are separated by double newlines."""
        entries = ["A", "B"]
        result = ImageGenerator._format_log_for_scanner(entries)
        assert "\n\n" in result

    def test_start_index_offsets_turn_numbers(self) -> None:
        """start_index shifts turn numbers for chunk-relative formatting."""
        entries = ["Entry A", "Entry B", "Entry C"]
        result = ImageGenerator._format_log_for_scanner(entries, start_index=100)
        assert "[Turn 100] Entry A" in result
        assert "[Turn 101] Entry B" in result
        assert "[Turn 102] Entry C" in result

    def test_start_index_default_is_zero(self) -> None:
        """Default start_index=0 produces standard 0-based numbering."""
        entries = ["X"]
        result_default = ImageGenerator._format_log_for_scanner(entries)
        result_explicit = ImageGenerator._format_log_for_scanner(entries, start_index=0)
        assert result_default == result_explicit


# =============================================================================
# scan_best_scene Tests
# =============================================================================


class TestScanBestScene:
    """Tests for ImageGenerator.scan_best_scene()."""

    @pytest.mark.anyio
    async def test_single_pass_scan(self, image_generator: ImageGenerator) -> None:
        """Single-pass scan when log fits in one chunk."""
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {"turn_number": 3, "rationale": "Dragon attack on the village"}
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with (
            patch("agents.get_llm", return_value=mock_llm),
            patch.object(
                image_generator,
                "_get_image_config",
                return_value=ImageGenerationConfig(
                    scanner_provider="gemini",
                    scanner_model="gemini-3-flash-preview",
                    scanner_token_limit=100000,  # Large limit = single pass
                ),
            ),
        ):
            turn, rationale = await image_generator.scan_best_scene(
                [
                    "[dm] The party enters.",
                    "[dm] A dragon appears!",
                    "[dm] Battle begins!",
                    "[dm] The dragon attacks!",
                ]
            )

        assert turn == 3
        assert "Dragon" in rationale
        # Single pass = only 1 LLM call
        assert mock_llm.ainvoke.call_count == 1

    @pytest.mark.anyio
    async def test_multi_chunk_scan(self, image_generator: ImageGenerator) -> None:
        """Multi-chunk scan with final comparison uses global turn indices."""
        # Create entries that will be chunked. First, figure out how many
        # chunks we'll get, then provide that many responses + 1 for comparison.
        entries = [
            f"[dm] Entry {i} with some extra words to add length." for i in range(30)
        ]
        token_limit = 50  # Very small = forces chunking

        # Pre-compute chunks so we can mock the right number of responses
        # and verify global turn numbers are used
        chunks = ImageGenerator._chunk_log_entries(entries, token_limit)
        num_chunks = len(chunks)

        # Build responses: each chunk returns a global turn number relative
        # to its offset, simulating correct LLM behavior
        chunk_responses = []
        for _i, (offset, chunk_entries) in enumerate(chunks):
            # Scanner should return global turn numbers since we format with offsets
            global_turn = offset + min(2, len(chunk_entries) - 1)
            chunk_responses.append(
                MagicMock(
                    content=json.dumps(
                        {
                            "turn_number": global_turn,
                            "rationale": f"Scene at global turn {global_turn}",
                        }
                    )
                )
            )
        # Final comparison picks turn 15 (must be in valid range)
        chunk_responses.append(
            MagicMock(
                content=json.dumps(
                    {"turn_number": 15, "rationale": "Best overall scene"}
                )
            )
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=chunk_responses)

        with (
            patch("agents.get_llm", return_value=mock_llm),
            patch.object(
                image_generator,
                "_get_image_config",
                return_value=ImageGenerationConfig(
                    scanner_provider="gemini",
                    scanner_model="gemini-3-flash-preview",
                    scanner_token_limit=token_limit,
                ),
            ),
        ):
            turn, rationale = await image_generator.scan_best_scene(entries)

        assert turn == 15
        assert "Best overall" in rationale
        # Should have num_chunks + 1 (comparison) LLM calls
        assert mock_llm.ainvoke.call_count == num_chunks + 1

        # Verify that chunk LLM calls used global turn numbers in formatting
        # by checking that the first chunk call includes [Turn 0] and later
        # chunks include higher turn numbers
        first_call_msg = mock_llm.ainvoke.call_args_list[0][0][0][1].content
        assert "[Turn 0]" in first_call_msg
        # Second chunk should NOT start at [Turn 0] -- it should use global offset
        if num_chunks > 1:
            second_call_msg = mock_llm.ainvoke.call_args_list[1][0][0][1].content
            second_offset = chunks[1][0]
            assert f"[Turn {second_offset}]" in second_call_msg
            assert "[Turn 0]" not in second_call_msg

    @pytest.mark.anyio
    async def test_scanner_llm_failure(self, image_generator: ImageGenerator) -> None:
        """Scanner LLM failure raises ImageGenerationError."""
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM timeout"))

        with (
            patch("agents.get_llm", return_value=mock_llm),
            patch.object(
                image_generator,
                "_get_image_config",
                return_value=ImageGenerationConfig(
                    scanner_provider="gemini",
                    scanner_model="gemini-3-flash-preview",
                    scanner_token_limit=100000,
                ),
            ),
            pytest.raises(ImageGenerationError, match="Scanner LLM failed"),
        ):
            await image_generator.scan_best_scene(["[dm] Entry 0"])

    @pytest.mark.anyio
    async def test_empty_log_raises_error(
        self, image_generator: ImageGenerator
    ) -> None:
        """Empty log raises ImageGenerationError."""
        with pytest.raises(ImageGenerationError, match="Cannot scan empty log"):
            await image_generator.scan_best_scene([])

    @pytest.mark.anyio
    async def test_clamps_out_of_range_turn(
        self, image_generator: ImageGenerator
    ) -> None:
        """Clamps turn number to valid range when scanner returns out-of-bounds."""
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {"turn_number": 999, "rationale": "Some scene"}
        )

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        entries = [f"[dm] Entry {i}" for i in range(5)]

        with (
            patch("agents.get_llm", return_value=mock_llm),
            patch.object(
                image_generator,
                "_get_image_config",
                return_value=ImageGenerationConfig(
                    scanner_provider="gemini",
                    scanner_model="gemini-3-flash-preview",
                    scanner_token_limit=100000,
                ),
            ),
        ):
            turn, rationale = await image_generator.scan_best_scene(entries)

        # Should clamp to max valid index (4)
        assert turn == 4


# =============================================================================
# Generate Best Scene Endpoint Tests
# =============================================================================


class TestGenerateBestSceneEndpoint:
    """Tests for POST /api/sessions/{session_id}/images/generate-best."""

    @pytest.mark.anyio
    async def test_returns_202_with_task_id(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_enabled_config: Path,
    ) -> None:
        """Returns 202 Accepted with a task ID and scanning status."""
        _create_test_session(temp_campaigns_dir, "001")
        log_entries = [f"Turn {i}: Something happens." for i in range(15)]
        _create_test_checkpoint_with_log(temp_campaigns_dir, "001", 15, log_entries)

        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.add_done_callback = MagicMock()
        with patch("api.routes.asyncio.create_task", return_value=mock_task):
            resp = await client.post("/api/sessions/001/images/generate-best")

        assert resp.status_code == 202
        data = resp.json()
        assert "task_id" in data
        assert data["session_id"] == "001"
        assert data["status"] == "scanning"

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

        resp = await client.post("/api/sessions/001/images/generate-best")
        assert resp.status_code == 400
        assert "not enabled" in resp.json()["detail"]

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

        resp = await client.post("/api/sessions/001/images/generate-best")
        assert resp.status_code == 400
        assert "no narrative log entries" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_returns_404_for_nonexistent_session(
        self,
        client: AsyncClient,
        temp_campaigns_dir: Path,
        image_gen_enabled_config: Path,
    ) -> None:
        """Returns 404 for a session that doesn't exist."""
        resp = await client.post("/api/sessions/999/images/generate-best")
        assert resp.status_code == 404

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

        resp = await client.post("/api/sessions/001/images/generate-best")
        assert resp.status_code == 429
        assert "Too many concurrent" in resp.json()["detail"]


# =============================================================================
# BestSceneAccepted Schema Tests
# =============================================================================


class TestBestSceneAcceptedSchema:
    """Tests for BestSceneAccepted schema model."""

    def test_creates_correctly(self) -> None:
        """BestSceneAccepted creates with correct defaults."""
        resp = BestSceneAccepted(
            task_id="abc-123",
            session_id="001",
        )
        assert resp.task_id == "abc-123"
        assert resp.session_id == "001"
        assert resp.status == "scanning"

    def test_serialization(self) -> None:
        """BestSceneAccepted serializes correctly."""
        resp = BestSceneAccepted(
            task_id="task-xyz",
            session_id="002",
        )
        dumped = resp.model_dump()
        assert dumped["task_id"] == "task-xyz"
        assert dumped["session_id"] == "002"
        assert dumped["status"] == "scanning"


# =============================================================================
# Background Task Tests
# =============================================================================


class TestScanAndGenerateBestImageBackground:
    """Tests for _scan_and_generate_best_image background task."""

    @pytest.mark.anyio
    async def test_scanner_failure_broadcasts_error(self) -> None:
        """Scanner failure broadcasts error event via WebSocket."""
        from api.routes import _scan_and_generate_best_image

        mock_manager = AsyncMock()

        with (
            patch("image_gen.ImageGenerator") as mock_gen_cls,
            patch("api.websocket.manager", mock_manager),
        ):
            mock_gen = mock_gen_cls.return_value
            mock_gen.scan_best_scene = AsyncMock(
                side_effect=ImageGenerationError("Scanner timeout")
            )

            # Should NOT raise -- errors caught internally
            await _scan_and_generate_best_image(
                session_id="001",
                task_id="task-123",
                log_entries=["Turn 1: Test."],
                characters={},
            )

        # Verify error was broadcast
        mock_manager.broadcast.assert_called()
        call_args = mock_manager.broadcast.call_args
        assert call_args[0][0] == "001"
        event = call_args[0][1]
        assert event["type"] == "error"
        assert "Scanner timeout" in event["message"]
        assert event["recoverable"] is True

    @pytest.mark.anyio
    async def test_image_gen_failure_after_scan_broadcasts_error(self) -> None:
        """Image generation failure after successful scan broadcasts error."""
        from api.routes import _scan_and_generate_best_image

        mock_manager = AsyncMock()

        with (
            patch("image_gen.ImageGenerator") as mock_gen_cls,
            patch("api.websocket.manager", mock_manager),
        ):
            mock_gen = mock_gen_cls.return_value
            mock_gen.scan_best_scene = AsyncMock(return_value=(5, "Epic battle"))
            mock_gen.build_scene_prompt = AsyncMock(return_value="test prompt")
            mock_gen.generate_scene_image = AsyncMock(
                side_effect=ImageGenerationError("Imagen API failed")
            )

            await _scan_and_generate_best_image(
                session_id="001",
                task_id="task-456",
                log_entries=[f"Entry {i}" for i in range(20)],
                characters={},
            )

        mock_manager.broadcast.assert_called()
        event = mock_manager.broadcast.call_args[0][1]
        assert event["type"] == "error"
        assert "Imagen API failed" in event["message"]

    @pytest.mark.anyio
    async def test_unexpected_error_broadcasts_error(self) -> None:
        """Unexpected exception broadcasts error event."""
        from api.routes import _scan_and_generate_best_image

        mock_manager = AsyncMock()

        with (
            patch("image_gen.ImageGenerator") as mock_gen_cls,
            patch("api.websocket.manager", mock_manager),
        ):
            mock_gen = mock_gen_cls.return_value
            mock_gen.scan_best_scene = AsyncMock(
                side_effect=RuntimeError("Unexpected boom")
            )

            await _scan_and_generate_best_image(
                session_id="001",
                task_id="task-789",
                log_entries=["Entry 0"],
                characters={},
            )

        mock_manager.broadcast.assert_called()
        event = mock_manager.broadcast.call_args[0][1]
        assert event["type"] == "error"
        assert event["recoverable"] is True

    @pytest.mark.anyio
    async def test_success_broadcasts_image_ready(self) -> None:
        """Successful flow broadcasts image_ready event with generation_mode=best."""
        from api.routes import _scan_and_generate_best_image

        mock_manager = AsyncMock()

        mock_scene_image = MagicMock(spec=SceneImage)
        mock_scene_image.id = "img-best-123"
        mock_scene_image.session_id = "001"
        mock_scene_image.turn_number = 7
        mock_scene_image.prompt = "An epic dragon battle"
        mock_scene_image.image_path = "session_001/images/img-best-123.png"
        mock_scene_image.provider = "gemini"
        mock_scene_image.model = "imagen-4.0-generate-001"
        mock_scene_image.generation_mode = "best"
        mock_scene_image.generated_at = "2026-02-14T12:00:00Z"
        mock_scene_image.model_dump.return_value = {
            "id": "img-best-123",
            "session_id": "001",
            "turn_number": 7,
            "prompt": "An epic dragon battle",
            "image_path": "session_001/images/img-best-123.png",
            "provider": "gemini",
            "model": "imagen-4.0-generate-001",
            "generation_mode": "best",
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
            mock_gen.scan_best_scene = AsyncMock(return_value=(7, "Epic dragon battle"))
            mock_gen.build_scene_prompt = AsyncMock(
                return_value="An epic dragon battle"
            )
            mock_gen.generate_scene_image = AsyncMock(return_value=mock_scene_image)
            mock_session_dir.return_value.__truediv__ = MagicMock(
                return_value=mock_images_dir
            )

            await _scan_and_generate_best_image(
                session_id="001",
                task_id="task-success",
                log_entries=[f"Entry {i}" for i in range(20)],
                characters={"Fighter": {"character_class": "Fighter"}},
            )

        # Verify WebSocket broadcast with image_ready
        mock_manager.broadcast.assert_called_once()
        call_args = mock_manager.broadcast.call_args
        assert call_args[0][0] == "001"
        event = call_args[0][1]
        assert event["type"] == "image_ready"
        assert event["image"]["id"] == "img-best-123"
        assert event["image"]["generation_mode"] == "best"
        assert event["image"]["turn_number"] == 7
        assert (
            event["image"]["download_url"]
            == "/api/sessions/001/images/img-best-123.png"
        )

    @pytest.mark.anyio
    async def test_context_window_extraction(self) -> None:
        """Background task extracts correct context window around identified turn."""
        from api.routes import _scan_and_generate_best_image

        mock_manager = AsyncMock()

        mock_scene_image = MagicMock(spec=SceneImage)
        mock_scene_image.id = "img-ctx-123"
        mock_scene_image.session_id = "001"
        mock_scene_image.turn_number = 10
        mock_scene_image.prompt = "test"
        mock_scene_image.image_path = "session_001/images/img-ctx-123.png"
        mock_scene_image.provider = "gemini"
        mock_scene_image.model = "imagen-4.0-generate-001"
        mock_scene_image.generation_mode = "best"
        mock_scene_image.generated_at = "2026-02-14T12:00:00Z"
        mock_scene_image.model_dump.return_value = {}

        mock_images_dir = MagicMock()
        mock_images_dir.__truediv__ = MagicMock(return_value=MagicMock())
        mock_images_dir.mkdir = MagicMock()

        log_entries = [f"Entry {i}" for i in range(20)]

        with (
            patch("image_gen.ImageGenerator") as mock_gen_cls,
            patch("api.websocket.manager", mock_manager),
            patch("api.routes.get_session_dir") as mock_session_dir,
        ):
            mock_gen = mock_gen_cls.return_value
            mock_gen.scan_best_scene = AsyncMock(return_value=(10, "Some scene"))
            mock_gen.build_scene_prompt = AsyncMock(return_value="test")
            mock_gen.generate_scene_image = AsyncMock(return_value=mock_scene_image)
            mock_session_dir.return_value.__truediv__ = MagicMock(
                return_value=mock_images_dir
            )

            await _scan_and_generate_best_image(
                session_id="001",
                task_id="task-ctx",
                log_entries=log_entries,
                characters={},
            )

        # Verify build_scene_prompt was called with context window entries 5-15
        call_args = mock_gen.build_scene_prompt.call_args
        context_entries = call_args[0][0]
        # Turn 10 with +/-5 = entries[5:16] = 11 entries
        assert len(context_entries) == 11
        assert context_entries[0] == "Entry 5"
        assert context_entries[-1] == "Entry 15"
