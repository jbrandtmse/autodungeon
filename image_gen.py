"""Image generation service using Google's Imagen API.

This module wraps the google-genai SDK to provide scene illustration
capabilities for the autodungeon game engine.

Story 17-2: Image Generation Service.

Architecture:
- ImageGenerator: Main service class for image generation
- build_scene_prompt(): Uses a fast LLM to summarize narrative into a visual prompt
- generate_scene_image(): Calls Google Imagen API and saves result as PNG
- Images stored in campaigns/session_{id}/images/{uuid}.png
"""

import asyncio
import io
import logging
import uuid
from pathlib import Path
from typing import Any, Literal

from models import ImageGenerationConfig, SceneImage, create_scene_image
from persistence import get_session_dir

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

# Imagen API maximum prompt length in characters (480 tokens ~ 1920 chars).
# We use a conservative character limit for safety.
MAX_PROMPT_CHARS = 1900


class ImageGenerationError(Exception):
    """Raised when image generation fails."""


class ImageGenerator:
    """Service for generating scene illustrations from narrative text.

    Uses Google's Imagen API for image generation and a fast LLM
    (via the existing get_llm factory) for prompt building.

    The client is lazily initialized on first use to avoid import-time
    side effects and API key resolution at module load.

    Story 17-2: Image Generation Service.
    """

    def __init__(self) -> None:
        self._client: Any = None  # Lazy initialization
        self._client_api_key: str | None = None  # Track key for staleness detection

    def _get_client(self) -> Any:
        """Get or create the genai client (lazy init).

        On first call, resolves the API key and creates the client.
        On subsequent calls, checks if the API key has changed and
        recreates the client if so (handles user updating settings via UI).

        Returns:
            A google.genai.Client instance configured with the effective API key.

        Raises:
            ImageGenerationError: If the API key is not configured.
        """
        if self._client is None:
            api_key = self._get_api_key()
            from google import genai

            self._client = genai.Client(api_key=api_key)
            self._client_api_key = api_key
        else:
            # Check if API key has changed since client was created
            try:
                current_key = self._get_api_key()
            except ImageGenerationError:
                # Key removed -- invalidate cached client and re-raise
                self._client = None
                self._client_api_key = None
                raise
            if current_key != self._client_api_key:
                from google import genai

                self._client = genai.Client(api_key=current_key)
                self._client_api_key = current_key
        return self._client

    def _get_api_key(self) -> str:
        """Get the effective Google API key.

        Follows the same priority chain as agents.py _get_effective_api_key:
        1. User settings (user-settings.yaml -> api_keys.google)
        2. Environment variable (GOOGLE_API_KEY from .env)
        3. Raise ImageGenerationError if neither is set

        Returns:
            The Google API key string.

        Raises:
            ImageGenerationError: If no API key is configured.
        """
        from config import get_config, load_user_settings

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

    def _get_image_config(self) -> ImageGenerationConfig:
        """Load image generation config from defaults.yaml.

        Parses raw YAML dict through the ImageGenerationConfig Pydantic model
        for validation and type safety, falling back to model defaults if the
        YAML section is missing or has invalid values.

        Returns:
            Validated ImageGenerationConfig instance.
        """
        from config import _load_yaml_defaults

        defaults = _load_yaml_defaults()
        raw = defaults.get("image_generation", {})
        try:
            return ImageGenerationConfig(**raw)
        except Exception:
            logger.warning(
                "Invalid image_generation config in defaults.yaml, using defaults"
            )
            return ImageGenerationConfig()

    def _ensure_images_dir(self, session_id: str) -> Path:
        """Ensure the images directory exists for a session.

        Creates campaigns/session_{session_id}/images/ if it doesn't exist.

        Args:
            session_id: Session ID string (e.g., "001").

        Returns:
            Path to the images directory.
        """
        images_dir = get_session_dir(session_id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        return images_dir

    @staticmethod
    def _save_image_to_disk(image_bytes: bytes, image_path: Path) -> None:
        """Save raw image bytes as PNG to disk (synchronous, for thread offload).

        Args:
            image_bytes: Raw image data from the API.
            image_path: Destination file path.
        """
        from PIL import Image

        image = Image.open(io.BytesIO(image_bytes))
        image.save(str(image_path), format="PNG")

    async def generate_scene_image(
        self,
        prompt: str,
        session_id: str,
        turn_number: int,
        generation_mode: Literal["current", "best", "specific"],
    ) -> SceneImage:
        """Generate a scene image from a text prompt.

        Calls the Google GenAI async image generation API with the configured
        model and 16:9 aspect ratio. Saves the result as PNG.

        Args:
            prompt: The text prompt describing the scene to generate.
            session_id: Session ID for image storage.
            turn_number: Turn number the image illustrates.
            generation_mode: How the image was requested.

        Returns:
            A SceneImage model with metadata about the generated image.

        Raises:
            ImageGenerationError: If image generation fails, returns no images,
                or if the prompt exceeds the maximum length.
        """
        from google.genai import types

        # Validate prompt length before sending to API (Imagen limit: ~480 tokens)
        if len(prompt) > MAX_PROMPT_CHARS:
            logger.warning(
                "Prompt length %d exceeds max %d chars, truncating",
                len(prompt),
                MAX_PROMPT_CHARS,
            )
            prompt = prompt[:MAX_PROMPT_CHARS]

        img_config = self._get_image_config()
        model = img_config.image_model
        provider = img_config.image_provider

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
            logger.error("Image generation failed: %s", e)
            raise ImageGenerationError(f"Image generation failed: {e}") from e

        if not response.generated_images:
            raise ImageGenerationError("No images returned by the API")

        image_bytes = response.generated_images[0].image.image_bytes

        # Save as PNG -- offload blocking PIL I/O to a thread to avoid
        # blocking the FastAPI event loop
        images_dir = self._ensure_images_dir(session_id)
        image_id = str(uuid.uuid4())
        image_path = images_dir / f"{image_id}.png"

        await asyncio.to_thread(self._save_image_to_disk, image_bytes, image_path)

        # Build relative path for storage (portable across systems)
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
        """Build an image generation prompt from narrative context.

        Uses a fast LLM (e.g., Gemini Flash) to analyze recent narrative
        log entries and character information, producing a concise 30-50 word
        visual scene description suitable for AI image generation.

        Args:
            log_entries: Recent narrative log entries from the game.
            characters: Dict of character name -> info (with character_class key).

        Returns:
            A 30-50 word visual scene description string.

        Raises:
            ImageGenerationError: If prompt building fails.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from agents import get_llm

        img_config = self._get_image_config()
        scanner_provider = img_config.scanner_provider
        scanner_model = img_config.scanner_model

        # Build context from log entries and characters
        context_parts: list[str] = []
        recent = log_entries[-SCENE_CONTEXT_ENTRIES:]
        context_parts.append("Recent narrative:\n" + "\n".join(recent))

        if characters:
            char_desc: list[str] = []
            for name, info in characters.items():
                cls = (
                    info.get("character_class", "Adventurer")
                    if isinstance(info, dict)
                    else "Adventurer"
                )
                char_desc.append(f"- {name}: {cls}")
            context_parts.append("Characters:\n" + "\n".join(char_desc))

        user_message = "\n\n".join(context_parts)

        try:
            llm = get_llm(scanner_provider, scanner_model)
            messages = [
                SystemMessage(content=SCENE_PROMPT_SYSTEM),
                HumanMessage(content=user_message),
            ]
            response = await llm.ainvoke(messages)
            content = response.content
            if isinstance(content, str):
                return content.strip()
            # Handle list-type content (some providers return list of blocks)
            if isinstance(content, list):
                text_parts = [
                    block if isinstance(block, str) else str(block) for block in content
                ]
                return " ".join(text_parts).strip()
            return str(content).strip()
        except Exception as e:
            logger.error("Scene prompt building failed: %s", e)
            raise ImageGenerationError(f"Failed to build scene prompt: {e}") from e
