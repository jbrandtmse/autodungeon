"""Tests for the image generation service.

Story 17-2: Image Generation Service.
Tests ImageGenerator class with mocked google-genai API calls.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from image_gen import ImageGenerationError, ImageGenerator
from models import ImageGenerationConfig

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def image_generator() -> ImageGenerator:
    """Create an ImageGenerator instance for testing."""
    return ImageGenerator()


@pytest.fixture
def mock_genai_client() -> MagicMock:
    """Create a mock google genai client with async image generation."""
    # Create a minimal PNG image in memory for the mock response
    from PIL import Image

    img = Image.new("RGB", (100, 56), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()

    # Build mock response structure
    mock_image = MagicMock()
    mock_image.image_bytes = png_bytes

    mock_generated = MagicMock()
    mock_generated.image = mock_image

    mock_response = MagicMock()
    mock_response.generated_images = [mock_generated]

    # Build async client mock
    mock_aio_models = AsyncMock()
    mock_aio_models.generate_images = AsyncMock(return_value=mock_response)

    mock_aio = MagicMock()
    mock_aio.models = mock_aio_models

    mock_client = MagicMock()
    mock_client.aio = mock_aio

    return mock_client


@pytest.fixture
def temp_campaigns_dir(tmp_path: Path) -> Path:
    """Create a temporary campaigns directory."""
    campaigns = tmp_path / "campaigns"
    campaigns.mkdir()
    return campaigns


# =============================================================================
# ImageGenerator._get_api_key Tests
# =============================================================================


class TestImageGeneratorApiKey:
    """Tests for API key resolution."""

    def test_api_key_from_user_settings(self, image_generator: ImageGenerator) -> None:
        """API key from user-settings.yaml takes priority."""
        with patch(
            "config.load_user_settings",
            return_value={"api_keys": {"google": "user-key-123"}},
        ):
            key = image_generator._get_api_key()
            assert key == "user-key-123"

    def test_api_key_from_env(self, image_generator: ImageGenerator) -> None:
        """Falls back to environment variable when user settings empty."""
        mock_config = MagicMock()
        mock_config.google_api_key = "env-key-456"

        with (
            patch("config.load_user_settings", return_value={}),
            patch("config.get_config", return_value=mock_config),
        ):
            key = image_generator._get_api_key()
            assert key == "env-key-456"

    def test_api_key_missing_raises_error(
        self, image_generator: ImageGenerator
    ) -> None:
        """Raises ImageGenerationError when no API key is configured."""
        mock_config = MagicMock()
        mock_config.google_api_key = None

        with (
            patch("config.load_user_settings", return_value={}),
            patch("config.get_config", return_value=mock_config),
            pytest.raises(ImageGenerationError, match="GOOGLE_API_KEY not configured"),
        ):
            image_generator._get_api_key()


# =============================================================================
# ImageGenerator.generate_scene_image Tests
# =============================================================================


class TestGenerateSceneImage:
    """Tests for generate_scene_image method."""

    @pytest.mark.anyio
    async def test_generates_and_saves_image(
        self,
        image_generator: ImageGenerator,
        mock_genai_client: MagicMock,
        temp_campaigns_dir: Path,
    ) -> None:
        """Generates an image and saves it as PNG to the correct path."""
        image_generator._client = mock_genai_client
        image_generator._client_api_key = "test-key"

        # Create session directory
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        with (
            patch("image_gen.get_session_dir", return_value=session_dir),
            patch.object(image_generator, "_get_api_key", return_value="test-key"),
        ):
            result = await image_generator.generate_scene_image(
                prompt="A dark dungeon corridor with torches",
                session_id="001",
                turn_number=5,
                generation_mode="current",
            )

        # Verify SceneImage model
        assert result.session_id == "001"
        assert result.turn_number == 5
        assert result.generation_mode == "current"
        assert result.prompt == "A dark dungeon corridor with torches"
        assert result.provider == "gemini"
        assert result.image_path.startswith("session_001/images/")
        assert result.image_path.endswith(".png")

        # Verify file was created
        images_dir = session_dir / "images"
        assert images_dir.exists()
        png_files = list(images_dir.glob("*.png"))
        assert len(png_files) == 1

    @pytest.mark.anyio
    async def test_uses_configured_model(
        self,
        image_generator: ImageGenerator,
        mock_genai_client: MagicMock,
        temp_campaigns_dir: Path,
    ) -> None:
        """Uses the configured image model from defaults.yaml."""
        image_generator._client = mock_genai_client
        image_generator._client_api_key = "test-key"

        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        with (
            patch("image_gen.get_session_dir", return_value=session_dir),
            patch.object(image_generator, "_get_api_key", return_value="test-key"),
            patch.object(
                image_generator,
                "_get_image_config",
                return_value=ImageGenerationConfig(
                    image_model="imagen-4.0-ultra-generate-001",
                    image_provider="gemini",
                ),
            ),
        ):
            result = await image_generator.generate_scene_image(
                prompt="test",
                session_id="001",
                turn_number=0,
                generation_mode="current",
            )

        assert result.model == "imagen-4.0-ultra-generate-001"

    @pytest.mark.anyio
    async def test_api_failure_raises_error(
        self,
        image_generator: ImageGenerator,
        mock_genai_client: MagicMock,
    ) -> None:
        """Wraps SDK exceptions in ImageGenerationError."""
        mock_genai_client.aio.models.generate_images = AsyncMock(
            side_effect=RuntimeError("API quota exceeded")
        )
        image_generator._client = mock_genai_client
        image_generator._client_api_key = "test-key"

        with (
            patch.object(image_generator, "_get_api_key", return_value="test-key"),
            pytest.raises(ImageGenerationError, match="API quota exceeded"),
        ):
            await image_generator.generate_scene_image(
                prompt="test",
                session_id="001",
                turn_number=0,
                generation_mode="current",
            )

    @pytest.mark.anyio
    async def test_no_images_returned_raises_error(
        self,
        image_generator: ImageGenerator,
        mock_genai_client: MagicMock,
    ) -> None:
        """Raises error when API returns empty image list."""
        mock_response = MagicMock()
        mock_response.generated_images = []
        mock_genai_client.aio.models.generate_images = AsyncMock(
            return_value=mock_response
        )
        image_generator._client = mock_genai_client
        image_generator._client_api_key = "test-key"

        with (
            patch.object(image_generator, "_get_api_key", return_value="test-key"),
            pytest.raises(ImageGenerationError, match="No images returned"),
        ):
            await image_generator.generate_scene_image(
                prompt="test",
                session_id="001",
                turn_number=0,
                generation_mode="current",
            )

    @pytest.mark.anyio
    async def test_creates_images_directory(
        self,
        image_generator: ImageGenerator,
        mock_genai_client: MagicMock,
        temp_campaigns_dir: Path,
    ) -> None:
        """Creates the images/ subdirectory if it doesn't exist."""
        image_generator._client = mock_genai_client
        image_generator._client_api_key = "test-key"

        session_dir = temp_campaigns_dir / "session_002"
        session_dir.mkdir()

        with (
            patch("image_gen.get_session_dir", return_value=session_dir),
            patch.object(image_generator, "_get_api_key", return_value="test-key"),
        ):
            await image_generator.generate_scene_image(
                prompt="test",
                session_id="002",
                turn_number=1,
                generation_mode="specific",
            )

        assert (session_dir / "images").exists()


# =============================================================================
# ImageGenerator.build_scene_prompt Tests
# =============================================================================


class TestBuildScenePrompt:
    """Tests for build_scene_prompt method."""

    @pytest.mark.anyio
    async def test_builds_non_empty_prompt(
        self, image_generator: ImageGenerator
    ) -> None:
        """Produces a non-empty string prompt from log entries."""
        mock_response = MagicMock()
        mock_response.content = "A dimly lit tavern with flickering candles and adventurers gathered around a worn oak table"

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
                ),
            ),
        ):
            result = await image_generator.build_scene_prompt(
                log_entries=[
                    "[dm] The party enters the tavern.",
                    "[fighter] I look around the room cautiously.",
                ],
                characters={"fighter": {"character_class": "Fighter"}},
            )

        assert isinstance(result, str)
        assert len(result) > 0
        assert "tavern" in result.lower()

    @pytest.mark.anyio
    async def test_handles_empty_characters(
        self, image_generator: ImageGenerator
    ) -> None:
        """Works correctly when characters dict is empty."""
        mock_response = MagicMock()
        mock_response.content = "A mysterious forest path"

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
                ),
            ),
        ):
            result = await image_generator.build_scene_prompt(
                log_entries=["[dm] The forest looms ahead."],
                characters={},
            )

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.anyio
    async def test_limits_log_entries(self, image_generator: ImageGenerator) -> None:
        """Only passes the last SCENE_CONTEXT_ENTRIES log entries."""
        mock_response = MagicMock()
        mock_response.content = "test prompt"

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        # Create more entries than SCENE_CONTEXT_ENTRIES (10)
        entries = [f"[dm] Entry {i}" for i in range(20)]

        with (
            patch("agents.get_llm", return_value=mock_llm),
            patch.object(
                image_generator,
                "_get_image_config",
                return_value=ImageGenerationConfig(
                    scanner_provider="gemini",
                    scanner_model="gemini-3-flash-preview",
                ),
            ),
        ):
            await image_generator.build_scene_prompt(
                log_entries=entries,
                characters={},
            )

        # Verify the LLM was called
        mock_llm.ainvoke.assert_called_once()
        # Check the message content includes only the last 10 entries
        call_args = mock_llm.ainvoke.call_args[0][0]
        user_msg = call_args[1].content
        assert "Entry 10" in user_msg
        assert "Entry 19" in user_msg
        # Entry 0-9 should not be included
        assert "Entry 0\n" not in user_msg

    @pytest.mark.anyio
    async def test_llm_failure_raises_error(
        self, image_generator: ImageGenerator
    ) -> None:
        """Wraps LLM errors in ImageGenerationError."""
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
                ),
            ),
            pytest.raises(ImageGenerationError, match="Failed to build scene prompt"),
        ):
            await image_generator.build_scene_prompt(
                log_entries=["[dm] test"],
                characters={},
            )

    @pytest.mark.anyio
    async def test_includes_character_classes(
        self, image_generator: ImageGenerator
    ) -> None:
        """Character classes are included in the prompt context."""
        mock_response = MagicMock()
        mock_response.content = "test prompt"

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
                ),
            ),
        ):
            await image_generator.build_scene_prompt(
                log_entries=["[dm] The battle rages on."],
                characters={
                    "Thorin": {"character_class": "Fighter"},
                    "Elara": {"character_class": "Wizard"},
                },
            )

        call_args = mock_llm.ainvoke.call_args[0][0]
        user_msg = call_args[1].content
        assert "Fighter" in user_msg
        assert "Wizard" in user_msg


# =============================================================================
# ImageGenerator._ensure_images_dir Tests
# =============================================================================


class TestEnsureImagesDir:
    """Tests for _ensure_images_dir helper."""

    def test_creates_images_directory(
        self, image_generator: ImageGenerator, temp_campaigns_dir: Path
    ) -> None:
        """Creates the images/ subdirectory."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        with patch("image_gen.get_session_dir", return_value=session_dir):
            result = image_generator._ensure_images_dir("001")

        assert result.exists()
        assert result == session_dir / "images"

    def test_idempotent(
        self, image_generator: ImageGenerator, temp_campaigns_dir: Path
    ) -> None:
        """Calling multiple times doesn't raise errors."""
        session_dir = temp_campaigns_dir / "session_001"
        session_dir.mkdir()

        with patch("image_gen.get_session_dir", return_value=session_dir):
            result1 = image_generator._ensure_images_dir("001")
            result2 = image_generator._ensure_images_dir("001")

        assert result1 == result2
        assert result1.exists()


# =============================================================================
# ImageGenerator._get_image_config Tests
# =============================================================================


class TestGetImageConfig:
    """Tests for _get_image_config helper."""

    def test_loads_from_yaml(self, image_generator: ImageGenerator) -> None:
        """Loads image generation config from defaults.yaml."""
        mock_defaults = {
            "image_generation": {
                "enabled": True,
                "image_model": "imagen-4.0-fast-generate-001",
            }
        }
        with patch("config._load_yaml_defaults", return_value=mock_defaults):
            config = image_generator._get_image_config()

        assert isinstance(config, ImageGenerationConfig)
        assert config.enabled is True
        assert config.image_model == "imagen-4.0-fast-generate-001"

    def test_returns_defaults_when_missing(
        self, image_generator: ImageGenerator
    ) -> None:
        """Returns default ImageGenerationConfig when YAML section is missing."""
        with patch("config._load_yaml_defaults", return_value={}):
            config = image_generator._get_image_config()

        assert isinstance(config, ImageGenerationConfig)
        assert config.enabled is False
        assert config.image_model == "imagen-4.0-generate-001"
