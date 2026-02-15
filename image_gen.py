"""Image generation service using Google's Imagen API.

This module wraps the google-genai SDK to provide scene illustration
capabilities for the autodungeon game engine.

Story 17-2: Image Generation Service.
Story 17-4: Best Scene Scanner.

Architecture:
- ImageGenerator: Main service class for image generation
- build_scene_prompt(): Uses a fast LLM to summarize narrative into a visual prompt
- generate_scene_image(): Calls Google Imagen API and saves result as PNG
- scan_best_scene(): Analyzes session log to find the most dramatic scene
- Images stored in campaigns/session_{id}/images/{uuid}.png
"""

import asyncio
import io
import json
import logging
import re
import uuid
from datetime import datetime, timezone
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

# =============================================================================
# Best Scene Scanner Constants (Story 17-4)
# =============================================================================

# Token estimation: words * 1.3 (consistent with MEMORY.md guidance)
TOKENS_PER_WORD = 1.3

# Number of overlapping entries between adjacent chunks to avoid cutting scenes
CHUNK_OVERLAP_ENTRIES = 20

# Fill factor for chunk sizing (leave headroom for system prompt and response)
CHUNK_FILL_FACTOR = 0.8

# Scanner timeout matches Summarizer.LLM_TIMEOUT (5 minutes for large sessions)
SCANNER_LLM_TIMEOUT = 300

# System prompt instructing the LLM to identify the best visual scene
BEST_SCENE_SYSTEM_PROMPT = """\
You are analyzing a D&D session log to find the single most visually dramatic, \
memorable, or cinematic scene that would make the best illustration.

Consider these categories:
- Epic battles: Dragons, demons, massive combat encounters
- Dramatic revelations: Betrayals, identity reveals, plot twists
- Beautiful environments: Magical landscapes, ancient ruins, ethereal vistas
- Emotional character moments: Sacrifices, reunions, farewells
- Magical events: Powerful spells, divine interventions, planar travel

Each log entry is prefixed with its turn number in the format:
"[Turn N] [Speaker]: content"

You MUST respond with a JSON object containing exactly:
{
  "turn_number": <integer>,
  "rationale": "<brief explanation of why this scene is the best candidate>"
}

Select the single most visually impactful moment. Prefer scenes with:
- Clear visual elements (not just dialogue)
- Multiple characters or dramatic action
- Strong environmental or atmospheric details"""

# Prompt for final comparison across chunk winners
BEST_SCENE_CHUNK_COMPARISON_PROMPT = """\
You previously analyzed different sections of a D&D session log.
Here are the best scene candidates from each section:

{chunk_winners}

Compare these candidates and select the single most visually dramatic \
scene overall. Respond with the same JSON format:
{{
  "turn_number": <integer>,
  "rationale": "<brief explanation>"
}}"""

# Regex for fallback turn number extraction from plain text
_TURN_NUMBER_RE = re.compile(r"[Tt]urn\s*(?:#|number[:\s]*)?\s*(\d+)")


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
        """Load image generation config from defaults.yaml + user-settings.

        User-settings overrides (image_model, image_provider) take precedence
        over YAML defaults when present.

        Returns:
            Validated ImageGenerationConfig instance.
        """
        from config import _load_yaml_defaults, load_user_settings

        defaults = _load_yaml_defaults()
        raw = defaults.get("image_generation", {})
        try:
            config = ImageGenerationConfig(**raw)
        except Exception:
            logger.warning(
                "Invalid image_generation config in defaults.yaml, using defaults"
            )
            config = ImageGenerationConfig()

        # Apply user-settings overrides
        user_settings = load_user_settings()
        if "image_model" in user_settings:
            config.image_model = user_settings["image_model"]
        if "image_provider" in user_settings:
            config.image_provider = user_settings["image_provider"]
        return config

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

        # Gemini image models (e.g. gemini-2.5-flash-image) use generate_content,
        # while Imagen models (e.g. imagen-4*) use generate_images.
        is_gemini_image_model = model.startswith("gemini-")
        image_bytes: bytes

        if is_gemini_image_model:
            image_bytes = await self._generate_via_gemini(client, model, prompt)
        else:
            image_bytes = await self._generate_via_imagen(client, model, prompt, types)

        # Save as PNG -- offload blocking PIL I/O to a thread to avoid
        # blocking the FastAPI event loop
        images_dir = self._ensure_images_dir(session_id)
        image_id = str(uuid.uuid4())
        image_path = images_dir / f"{image_id}.png"

        await asyncio.to_thread(self._save_image_to_disk, image_bytes, image_path)

        # Build relative path for storage (portable across systems)
        rel_path = f"session_{session_id}/images/{image_id}.png"

        # Use the same image_id for the SceneImage so the metadata JSON
        # filename matches the PNG filename (both use image_id).
        return SceneImage(
            id=image_id,
            session_id=session_id,
            turn_number=turn_number,
            prompt=prompt,
            image_path=rel_path,
            provider=provider,
            model=model,
            generation_mode=generation_mode,
            generated_at=datetime.now(timezone.utc).isoformat() + "Z",
        )

    async def _generate_via_imagen(
        self, client: Any, model: str, prompt: str, types: Any
    ) -> bytes:
        """Generate an image using the Imagen API (generate_images).

        Args:
            client: google.genai.Client instance.
            model: Imagen model ID (e.g. "imagen-4.0-generate-001").
            prompt: Visual scene description.
            types: google.genai.types module.

        Returns:
            Raw image bytes.

        Raises:
            ImageGenerationError: On API failure or empty response.
        """
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
            logger.error("Imagen generation failed: %s", e)
            raise ImageGenerationError(f"Image generation failed: {e}") from e

        if not response.generated_images:
            raise ImageGenerationError("No images returned by the API")

        return response.generated_images[0].image.image_bytes

    async def _generate_via_gemini(
        self, client: Any, model: str, prompt: str
    ) -> bytes:
        """Generate an image using the Gemini content API (generate_content).

        Used for models like gemini-2.5-flash-image (Nano Banana) and
        gemini-3-pro-image-preview (Nano Banana Pro) that use the Gemini
        generate_content endpoint with response_modalities=["IMAGE"].

        Args:
            client: google.genai.Client instance.
            model: Gemini image model ID (e.g. "gemini-2.5-flash-image").
            prompt: Visual scene description.

        Returns:
            Raw image bytes.

        Raises:
            ImageGenerationError: On API failure or no image in response.
        """
        from google.genai import types

        try:
            response = await client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
        except Exception as e:
            logger.error("Gemini image generation failed: %s", e)
            raise ImageGenerationError(f"Image generation failed: {e}") from e

        # Extract image bytes from the Gemini response parts
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    return part.inline_data.data

        raise ImageGenerationError("No image returned in Gemini response")

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
                if not isinstance(info, dict):
                    char_desc.append(f"- {name}: Adventurer")
                    continue
                cls = info.get("character_class", "Adventurer")
                race = info.get("race", "")
                parts = [name]
                if race:
                    parts.append(race)
                parts.append(cls)
                char_desc.append(f"- {', '.join(parts)}")
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
                text_parts: list[str] = []
                for block in content:
                    if isinstance(block, str):
                        text_parts.append(block)
                    elif isinstance(block, dict) and "text" in block:
                        text_parts.append(block["text"])
                    else:
                        text_parts.append(str(block))
                return " ".join(text_parts).strip()
            return str(content).strip()
        except Exception as e:
            logger.error("Scene prompt building failed: %s", e)
            raise ImageGenerationError(f"Failed to build scene prompt: {e}") from e

    # =========================================================================
    # Best Scene Scanner (Story 17-4)
    # =========================================================================

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count from text using words * 1.3.

        This matches the project-wide convention documented in MEMORY.md.

        Args:
            text: The text to estimate tokens for.

        Returns:
            Estimated token count.
        """
        word_count = len(text.split())
        return int(word_count * TOKENS_PER_WORD)

    @staticmethod
    def _chunk_log_entries(
        log_entries: list[str], token_limit: int
    ) -> list[tuple[int, list[str]]]:
        """Split log entries into chunks that fit within the token limit.

        Each chunk targets ``token_limit * CHUNK_FILL_FACTOR`` tokens to
        leave headroom for the system prompt and LLM response. Adjacent
        chunks overlap by ``CHUNK_OVERLAP_ENTRIES`` entries so that scenes
        spanning a boundary are not missed.

        Args:
            log_entries: Full list of log entry strings.
            token_limit: Maximum tokens per chunk (from scanner config).

        Returns:
            List of ``(start_offset, entries)`` tuples. The start_offset
            is the global index of the first entry in the chunk, enabling
            callers to format turn numbers correctly.
            Returns ``[]`` for an empty log, or ``[(0, log_entries)]`` if
            everything fits in a single chunk.
        """
        if not log_entries:
            return []

        effective_limit = int(token_limit * CHUNK_FILL_FACTOR)
        chunks: list[tuple[int, list[str]]] = []
        start = 0
        total = len(log_entries)

        while start < total:
            # Greedily add entries until we hit the token budget
            end = start
            running_tokens = 0
            while end < total:
                entry_tokens = int(len(log_entries[end].split()) * TOKENS_PER_WORD)
                if running_tokens + entry_tokens > effective_limit and end > start:
                    break
                running_tokens += entry_tokens
                end += 1

            chunks.append((start, log_entries[start:end]))

            # Advance start, accounting for overlap
            next_start = end - CHUNK_OVERLAP_ENTRIES
            if next_start <= start:
                # Prevent infinite loop: always advance by at least 1
                next_start = end
            start = next_start

        return chunks

    @staticmethod
    def _parse_scanner_response(response_text: str) -> tuple[int, str]:
        """Extract turn_number and rationale from scanner LLM response.

        Tries JSON parsing first, then falls back to regex extraction.

        Args:
            response_text: Raw text response from the scanner LLM.

        Returns:
            Tuple of (turn_number, rationale).

        Raises:
            ImageGenerationError: If no turn number can be extracted.
        """
        # Strategy 1: Try JSON parsing
        # Strip markdown code fences if present
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            # Remove ```json ... ``` wrapping
            lines = cleaned.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict) and "turn_number" in data:
                turn = int(data["turn_number"])
                if turn < 0:
                    raise ValueError(f"Negative turn number: {turn}")
                rationale = str(data.get("rationale", ""))
                return (turn, rationale)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        # Strategy 2: Regex fallback
        match = _TURN_NUMBER_RE.search(response_text)
        if match:
            turn = int(match.group(1))
            # Regex only matches \d+ so turn is always >= 0
            # Use the full response as rationale since we couldn't parse JSON
            rationale = response_text.strip()
            return (turn, rationale)

        raise ImageGenerationError(
            "Scanner failed to identify a turn number from response: "
            + response_text[:200]
        )

    @staticmethod
    def _format_log_for_scanner(log_entries: list[str], start_index: int = 0) -> str:
        """Format log entries with turn numbers for scanner consumption.

        Prepends each entry with its global index as ``[Turn N]`` so the
        scanner can reference specific turns in its response.

        Args:
            log_entries: Raw log entries from ground_truth_log.
            start_index: Global index of the first entry in the list.
                Used for multi-chunk scanning so turn numbers remain
                globally consistent across chunks.

        Returns:
            Formatted string with turn-numbered entries separated by
            double newlines.

        Note:
            Log entries are user/LLM-generated content passed directly
            into the scanner prompt. Prompt injection via crafted log
            entries is possible but impractical to mitigate without
            distorting legitimate D&D narrative content.
        """
        formatted = []
        for i, entry in enumerate(log_entries):
            formatted.append(f"[Turn {start_index + i}] {entry}")
        return "\n\n".join(formatted)

    async def scan_best_scene(self, log_entries: list[str]) -> tuple[int, str]:
        """Scan the session log and identify the most visually dramatic scene.

        Uses the configured scanner LLM to analyze the full ground_truth_log.
        If the log fits within the scanner's token limit, processes in a
        single pass. Otherwise, chunks the log with overlapping windows,
        finds the best scene in each chunk, and runs a final comparison.

        Args:
            log_entries: Complete ground_truth_log for the session.

        Returns:
            Tuple of (turn_number, rationale) identifying the best scene.

        Raises:
            ImageGenerationError: If the scanner fails to identify a scene.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        from agents import get_llm

        if not log_entries:
            raise ImageGenerationError("Cannot scan empty log for best scene")

        config = self._get_image_config()
        llm = get_llm(
            config.scanner_provider,
            config.scanner_model,
            timeout=SCANNER_LLM_TIMEOUT,
        )

        # Estimate tokens on the formatted text (with [Turn N] prefixes and
        # double-newline separators) to accurately reflect what the LLM sees.
        formatted_full = self._format_log_for_scanner(log_entries)
        estimated_tokens = self._estimate_tokens(formatted_full)

        try:
            if estimated_tokens <= config.scanner_token_limit:
                # Single-pass: entire log fits in one call
                response = await llm.ainvoke(
                    [
                        SystemMessage(content=BEST_SCENE_SYSTEM_PROMPT),
                        HumanMessage(content=formatted_full),
                    ]
                )
                content = (
                    response.content
                    if isinstance(response.content, str)
                    else str(response.content)
                )
                turn_number, rationale = self._parse_scanner_response(content)
                chunked = False
            else:
                # Multi-chunk with final comparison
                chunks = self._chunk_log_entries(
                    log_entries, config.scanner_token_limit
                )
                chunk_winners: list[tuple[int, str]] = []

                for i, (chunk_offset, chunk) in enumerate(chunks):
                    formatted = self._format_log_for_scanner(
                        chunk, start_index=chunk_offset
                    )
                    response = await llm.ainvoke(
                        [
                            SystemMessage(content=BEST_SCENE_SYSTEM_PROMPT),
                            HumanMessage(content=formatted),
                        ]
                    )
                    content = (
                        response.content
                        if isinstance(response.content, str)
                        else str(response.content)
                    )
                    winner_turn, winner_rationale = self._parse_scanner_response(
                        content
                    )
                    chunk_winners.append((winner_turn, winner_rationale))
                    logger.debug(
                        "Scanner chunk %d/%d winner: Turn %d - %s",
                        i + 1,
                        len(chunks),
                        winner_turn,
                        winner_rationale[:100],
                    )

                if len(chunk_winners) == 1:
                    turn_number, rationale = chunk_winners[0]
                else:
                    # Final comparison round across chunk winners
                    winners_text = "\n".join(
                        f"- Turn {t}: {r}" for t, r in chunk_winners
                    )
                    comparison_prompt = BEST_SCENE_CHUNK_COMPARISON_PROMPT.format(
                        chunk_winners=winners_text
                    )
                    response = await llm.ainvoke(
                        [
                            SystemMessage(content=BEST_SCENE_SYSTEM_PROMPT),
                            HumanMessage(content=comparison_prompt),
                        ]
                    )
                    content = (
                        response.content
                        if isinstance(response.content, str)
                        else str(response.content)
                    )
                    turn_number, rationale = self._parse_scanner_response(content)
                chunked = True

        except ImageGenerationError:
            raise
        except Exception as e:
            logger.error("Scanner LLM failed: %s", e)
            raise ImageGenerationError(f"Scanner LLM failed: {e}") from e

        # Validate turn number against actual log length
        if turn_number < 0 or turn_number >= len(log_entries):
            logger.warning(
                "Scanner returned turn %d but log has %d entries, "
                "clamping to valid range",
                turn_number,
                len(log_entries),
            )
            turn_number = max(0, min(turn_number, len(log_entries) - 1))

        logger.info(
            "Scanner identified best scene: Turn %d (chunked=%s) - %s",
            turn_number,
            chunked,
            rationale[:150],
        )

        return (turn_number, rationale)
