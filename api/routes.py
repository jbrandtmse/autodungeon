"""REST API endpoints for the autodungeon API.

Provides session management, configuration, and character listing endpoints.
All endpoints wrap existing backend functions from persistence.py, config.py,
and models.py without modifying them.
"""

from __future__ import annotations

import asyncio
import json as _json
import logging
import re as _re
import time
import uuid as _uuid
from pathlib import Path
from typing import Any, Literal

import yaml
from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from api.schemas import (
    BestSceneAccepted,
    CharacterCreateRequest,
    CharacterDetailResponse,
    CharacterResponse,
    CharacterSheetResponse,
    CharacterUpdateRequest,
    CheckpointInfoResponse,
    CheckpointPreviewResponse,
    ComparisonDataResponse,
    ComparisonTimelineResponse,
    ComparisonTurnResponse,
    ForkCreateRequest,
    ForkMetadataResponse,
    ForkRenameRequest,
    GameConfigResponse,
    GameConfigUpdateRequest,
    ImageGenerateAccepted,
    ImageGenerateRequest,
    ModelListResponse,
    ModuleDiscoveryResponse,
    ModuleInfoResponse,
    SceneImageResponse,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionResponse,
    SessionStartRequest,
    UserSettingsResponse,
    UserSettingsUpdateRequest,
)
from config import (
    PROJECT_ROOT,
    _load_yaml_defaults,
    load_character_configs,
    load_user_settings,
    save_user_settings,
)
from models import CharacterConfig, DMConfig, GameConfig
from persistence import (
    _validate_session_id,
    build_comparison_data,
    create_fork,
    create_new_session,
    delete_fork,
    delete_session,
    get_checkpoint_preview,
    get_latest_checkpoint,
    get_session_dir,
    list_checkpoint_info,
    list_forks,
    list_sessions_with_metadata,
    load_checkpoint,
    load_session_metadata,
    promote_fork,
    rename_fork,
    save_checkpoint,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# =============================================================================
# Model Listing Cache
# =============================================================================

_model_cache: dict[
    str, tuple[list[str], str, float]
] = {}  # provider -> (models, source, ts)
_CACHE_TTL = 60.0

FALLBACK_MODELS: dict[str, list[str]] = {
    "gemini": [
        "gemini-3-flash-preview",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-2.5-flash-preview-05-20",
        "gemini-2.5-pro-preview-05-06",
        "gemini-3-pro-preview",
    ],
    "anthropic": [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-haiku-20240307",
    ],
    "ollama": ["llama3", "mistral", "phi3", "qwen3:14b"],
}

_VALID_PROVIDERS = {"gemini", "anthropic", "claude", "ollama"}


# =============================================================================
# Session Endpoints
# =============================================================================


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions() -> list[SessionResponse]:
    """List all sessions sorted by updated_at descending.

    Returns:
        List of session metadata objects.
    """
    import asyncio

    try:
        # Offload blocking file I/O to thread to avoid blocking the event loop
        sessions = await asyncio.to_thread(list_sessions_with_metadata)
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list sessions: {e}"
        ) from None
    return [
        SessionResponse(
            session_id=s.session_id,
            session_number=s.session_number,
            name=s.name,
            created_at=s.created_at,
            updated_at=s.updated_at,
            character_names=s.character_names,
            turn_count=s.turn_count,
        )
        for s in sessions
    ]


@router.post("/sessions", response_model=SessionCreateResponse, status_code=201)
async def create_session(
    body: SessionCreateRequest | None = None,
) -> SessionCreateResponse:
    """Create a new session.

    Args:
        body: Optional request body with session name.

    Returns:
        Created session info with 201 status.
    """
    name = body.name if body else ""
    try:
        session_id = create_new_session(name=name)
    except (OSError, ValueError) as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {e}"
        ) from None
    # Parse session number from ID
    session_number = int(session_id)
    return SessionCreateResponse(
        session_id=session_id,
        session_number=session_number,
        name=name,
    )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """Get session details by ID.

    Args:
        session_id: Session ID string (e.g., "001").

    Returns:
        Session metadata.

    Raises:
        HTTPException: 400 for invalid session ID, 404 if not found.
    """
    try:
        _validate_session_id(session_id)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid session ID: {session_id}"
        ) from None

    metadata = load_session_metadata(session_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return SessionResponse(
        session_id=metadata.session_id,
        session_number=metadata.session_number,
        name=metadata.name,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
        character_names=metadata.character_names,
        turn_count=metadata.turn_count,
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session_endpoint(session_id: str) -> None:
    """Delete a session and all its data.

    Args:
        session_id: Session ID string (e.g., "001").

    Raises:
        HTTPException: 400 for invalid session ID, 404 if not found,
            500 if deletion fails.
    """
    try:
        _validate_session_id(session_id)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid session ID: {session_id}"
        ) from None

    metadata = load_session_metadata(session_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    try:
        deleted = delete_session(session_id)
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {e}"
        ) from None

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")


# =============================================================================
# Module Discovery Endpoint
# =============================================================================


@router.post("/modules/discover", response_model=ModuleDiscoveryResponse)
async def discover_modules_endpoint() -> ModuleDiscoveryResponse:
    """Discover available D&D modules via LLM query.

    Calls the DM's configured LLM to generate a list of known D&D
    modules/adventures. This is a potentially slow operation (5-15s)
    as it involves an LLM API call.

    Returns:
        Module discovery results with list of modules.
    """
    from agents import LLMError, discover_modules
    from config import load_dm_config

    try:
        dm_config = load_dm_config()
    except (ValueError, OSError) as e:
        return ModuleDiscoveryResponse(
            modules=[],
            provider="unknown",
            model="unknown",
            source="error",
            error=f"Failed to load DM config: {e}",
        )

    try:
        result = await asyncio.to_thread(discover_modules, dm_config)
    except LLMError as e:
        return ModuleDiscoveryResponse(
            modules=[],
            provider=dm_config.provider,
            model=dm_config.model,
            source="error",
            error=str(e),
        )
    except Exception as e:
        logger.exception("Unexpected error during module discovery")
        return ModuleDiscoveryResponse(
            modules=[],
            provider=dm_config.provider,
            model=dm_config.model,
            source="error",
            error=f"Module discovery failed: {e}",
        )

    return ModuleDiscoveryResponse(
        modules=[
            ModuleInfoResponse(
                number=m.number,
                name=m.name,
                description=m.description,
                setting=m.setting,
                level_range=m.level_range,
            )
            for m in result.modules
        ],
        provider=result.provider,
        model=result.model,
        source="llm",
    )


# =============================================================================
# Session Start Endpoint
# =============================================================================


@router.post("/sessions/{session_id}/start")
async def start_session_endpoint(
    session_id: str, request: Request, body: SessionStartRequest | None = None
) -> dict[str, str]:
    """Start a session with optional setup configuration.

    Creates a GameEngine, registers it in app state, and calls
    start_session() with the provided module and character selections.

    Args:
        session_id: Session ID to start.
        request: FastAPI request (for accessing app.state.engines).
        body: Optional setup configuration (module, characters, name).

    Returns:
        Status dict with session_id.

    Raises:
        HTTPException: 404 if session not found, 409 if already started.
    """
    from api.engine import GameEngine

    try:
        _validate_session_id(session_id)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid session ID: {session_id}"
        ) from None

    metadata = load_session_metadata(session_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    engines: dict[str, GameEngine] = request.app.state.engines

    # Check if engine already has state (already started)
    if session_id in engines and engines[session_id].state is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Session '{session_id}' is already started",
        )

    body = body or SessionStartRequest()

    # Build characters_override from selected character names
    characters_override: dict[str, object] | None = None
    if body.selected_characters:
        try:
            all_presets = load_character_configs()
        except (ValueError, OSError):
            all_presets = {}

        all_library = _load_library_characters()

        # Merge preset + library, keyed by lowercase name
        all_chars = {**all_presets, **all_library}

        # Filter to selected names
        selected = {}
        for name in body.selected_characters:
            key = name.lower()
            if key in all_chars:
                selected[key] = all_chars[key]

        if selected:
            characters_override = selected  # type: ignore[assignment]

    # Convert ModuleInfoResponse to models.ModuleInfo if provided
    selected_module = None
    if body.selected_module:
        from models import ModuleInfo

        selected_module = ModuleInfo(
            number=body.selected_module.number,
            name=body.selected_module.name,
            description=body.selected_module.description,
            setting=body.selected_module.setting,
            level_range=body.selected_module.level_range,
        )

    # Create engine and start session
    engine = GameEngine(session_id)
    engines[session_id] = engine

    try:
        await engine.start_session(
            characters_override=characters_override,
            selected_module=selected_module,
        )
    except Exception as e:
        # Clean up on failure
        engines.pop(session_id, None)
        logger.exception("Failed to start session %s", session_id)
        raise HTTPException(
            status_code=500, detail=f"Failed to start session: {e}"
        ) from None

    return {"status": "started", "session_id": session_id}


# =============================================================================
# Session Config Endpoints
# =============================================================================


@router.get("/sessions/{session_id}/config", response_model=GameConfigResponse)
async def get_session_config(session_id: str) -> GameConfigResponse:
    """Get config for a session.

    If the session has checkpoints, loads from the latest checkpoint.
    Otherwise returns default GameConfig values.

    Args:
        session_id: Session ID string.

    Returns:
        Game configuration for the session.

    Raises:
        HTTPException: 400 for invalid session ID, 404 if session not found.
    """
    try:
        _validate_session_id(session_id)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid session ID: {session_id}"
        ) from None

    # Check session exists
    metadata = load_session_metadata(session_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    # Load image generation defaults from YAML
    yaml_defaults = _load_yaml_defaults()
    img_cfg = yaml_defaults.get("image_generation", {})

    # Try loading from latest checkpoint
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is not None:
        state = load_checkpoint(session_id, latest_turn)
        if state is not None:
            game_config = state["game_config"]
            dm_config = state.get("dm_config")
            if dm_config is None:
                dm_config = DMConfig()
            return GameConfigResponse(
                combat_mode=game_config.combat_mode,
                max_combat_rounds=game_config.max_combat_rounds,
                summarizer_provider=game_config.summarizer_provider,
                summarizer_model=game_config.summarizer_model,
                extractor_provider=game_config.extractor_provider,
                extractor_model=game_config.extractor_model,
                party_size=game_config.party_size,
                narrative_display_limit=game_config.narrative_display_limit,
                dm_provider=dm_config.provider,
                dm_model=dm_config.model,
                dm_token_limit=dm_config.token_limit,
                image_generation_enabled=img_cfg.get("enabled", False),
                image_provider=img_cfg.get("image_provider", "gemini"),
                image_model=img_cfg.get("image_model", "imagen-4.0-generate-001"),
                image_scanner_provider=img_cfg.get("scanner_provider", "gemini"),
                image_scanner_model=img_cfg.get(
                    "scanner_model", "gemini-3-flash-preview"
                ),
                image_scanner_token_limit=img_cfg.get("scanner_token_limit", 4000),
            )

    # No checkpoint - return defaults
    defaults = GameConfig()
    dm_defaults = DMConfig()
    return GameConfigResponse(
        combat_mode=defaults.combat_mode,
        max_combat_rounds=defaults.max_combat_rounds,
        summarizer_provider=defaults.summarizer_provider,
        summarizer_model=defaults.summarizer_model,
        extractor_provider=defaults.extractor_provider,
        extractor_model=defaults.extractor_model,
        party_size=defaults.party_size,
        narrative_display_limit=defaults.narrative_display_limit,
        dm_provider=dm_defaults.provider,
        dm_model=dm_defaults.model,
        dm_token_limit=dm_defaults.token_limit,
        image_generation_enabled=img_cfg.get("enabled", False),
        image_provider=img_cfg.get("image_provider", "gemini"),
        image_model=img_cfg.get("image_model", "imagen-4.0-generate-001"),
        image_scanner_provider=img_cfg.get("scanner_provider", "gemini"),
        image_scanner_model=img_cfg.get("scanner_model", "gemini-3-flash-preview"),
        image_scanner_token_limit=img_cfg.get("scanner_token_limit", 4000),
    )


@router.put("/sessions/{session_id}/config", response_model=GameConfigResponse)
async def update_session_config(
    session_id: str, body: GameConfigUpdateRequest
) -> GameConfigResponse:
    """Update session config with partial data.

    Loads the latest checkpoint (or creates a minimal one), updates the
    game_config fields, and re-saves.

    Args:
        session_id: Session ID string.
        body: Partial config update fields.

    Returns:
        Updated game configuration.

    Raises:
        HTTPException: 400 for invalid session ID, 404 if session not found,
            422 for validation errors.
    """
    try:
        _validate_session_id(session_id)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid session ID: {session_id}"
        ) from None

    # Check session exists
    metadata = load_session_metadata(session_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    # Load existing state or create minimal one
    state = None
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is not None:
        state = load_checkpoint(session_id, latest_turn)

    if state is None:
        # Create minimal initial state
        from models import create_initial_game_state

        state = create_initial_game_state()
        state["session_id"] = session_id
        state["session_number"] = metadata.session_number
        latest_turn = 0

    # Separate DM fields and image generation fields from game_config fields
    update_data = body.model_dump(exclude_none=True)
    dm_fields = {}
    for key in ("dm_provider", "dm_model", "dm_token_limit"):
        if key in update_data:
            dm_fields[key] = update_data.pop(key)

    # Separate image generation fields.
    # NOTE: These are NOT persisted in GameState yet (Story 17-2 scope).
    # Values are reflected in the response for UI consistency but will
    # revert to YAML defaults on next GET. Full persistence requires
    # embedding ImageGenerationConfig in GameState (future story).
    image_gen_fields = {}
    for key in (
        "image_generation_enabled",
        "image_provider",
        "image_model",
        "image_scanner_provider",
        "image_scanner_model",
        "image_scanner_token_limit",
    ):
        if key in update_data:
            image_gen_fields[key] = update_data.pop(key)

    if image_gen_fields:
        logger.debug(
            "Image generation config fields received but not persisted: %s",
            list(image_gen_fields.keys()),
        )

    # Apply partial updates to game_config
    current_config = state["game_config"]
    config_dict = current_config.model_dump()
    config_dict.update(update_data)

    # Validate the merged config through Pydantic
    try:
        new_config = GameConfig(**config_dict)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None

    state["game_config"] = new_config

    # Apply DM config updates if present
    current_dm = state.get("dm_config")
    if current_dm is None:
        current_dm = DMConfig()
    dm_dict = current_dm.model_dump()
    if "dm_provider" in dm_fields:
        dm_dict["provider"] = dm_fields["dm_provider"]
    if "dm_model" in dm_fields:
        dm_dict["model"] = dm_fields["dm_model"]
    if "dm_token_limit" in dm_fields:
        dm_dict["token_limit"] = dm_fields["dm_token_limit"]

    try:
        new_dm = DMConfig(**dm_dict)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None

    state["dm_config"] = new_dm

    # Save
    if latest_turn is None:
        latest_turn = 0
    save_checkpoint(state, session_id, latest_turn)

    # Load image generation defaults, merge with any submitted overrides
    yaml_defaults = _load_yaml_defaults()
    img_cfg = yaml_defaults.get("image_generation", {})

    return GameConfigResponse(
        combat_mode=new_config.combat_mode,
        max_combat_rounds=new_config.max_combat_rounds,
        summarizer_provider=new_config.summarizer_provider,
        summarizer_model=new_config.summarizer_model,
        extractor_provider=new_config.extractor_provider,
        extractor_model=new_config.extractor_model,
        party_size=new_config.party_size,
        narrative_display_limit=new_config.narrative_display_limit,
        dm_provider=new_dm.provider,
        dm_model=new_dm.model,
        dm_token_limit=new_dm.token_limit,
        image_generation_enabled=image_gen_fields.get(
            "image_generation_enabled", img_cfg.get("enabled", False)
        ),
        image_provider=image_gen_fields.get(
            "image_provider", img_cfg.get("image_provider", "gemini")
        ),
        image_model=image_gen_fields.get(
            "image_model", img_cfg.get("image_model", "imagen-4.0-generate-001")
        ),
        image_scanner_provider=image_gen_fields.get(
            "image_scanner_provider", img_cfg.get("scanner_provider", "gemini")
        ),
        image_scanner_model=image_gen_fields.get(
            "image_scanner_model",
            img_cfg.get("scanner_model", "gemini-3-flash-preview"),
        ),
        image_scanner_token_limit=image_gen_fields.get(
            "image_scanner_token_limit", img_cfg.get("scanner_token_limit", 4000)
        ),
    )


# =============================================================================
# User Settings Endpoints
# =============================================================================


@router.get("/user-settings", response_model=UserSettingsResponse)
async def get_user_settings() -> UserSettingsResponse:
    """Get user settings with API key configured status (never raw keys).

    Checks both user-settings.yaml and environment variables to determine
    whether each provider's API key is configured.

    Returns:
        User settings with boolean configured flags for API keys.
    """
    from config import get_config

    settings = load_user_settings()
    api_keys = settings.get("api_keys", {})
    token_limits = settings.get("token_limit_overrides", {})

    # Check env vars as fallback
    try:
        config = get_config()
        google_env = bool(config.google_api_key)
        anthropic_env = bool(config.anthropic_api_key)
    except Exception:
        google_env = False
        anthropic_env = False

    # Image generation: user-settings overrides yaml defaults
    yaml_defaults = _load_yaml_defaults()
    img_cfg = yaml_defaults.get("image_generation", {})
    img_enabled = settings.get("image_generation_enabled", img_cfg.get("enabled", False))

    img_model = settings.get(
        "image_model", img_cfg.get("image_model", "imagen-4.0-generate-001")
    )

    return UserSettingsResponse(
        google_api_key_configured=bool(api_keys.get("google")) or google_env,
        anthropic_api_key_configured=bool(api_keys.get("anthropic")) or anthropic_env,
        ollama_url=str(api_keys.get("ollama", "")),
        token_limit_overrides={
            k: v for k, v in token_limits.items() if isinstance(v, int)
        },
        image_generation_enabled=bool(img_enabled),
        image_model=str(img_model),
    )


@router.put("/user-settings", response_model=UserSettingsResponse)
async def update_user_settings(body: UserSettingsUpdateRequest) -> UserSettingsResponse:
    """Update user settings. Partial merge into user-settings.yaml.

    API keys are written to the settings file so the Python backend can
    use them via get_effective_api_key(). Raw key values are never returned.

    Args:
        body: Partial update fields.

    Returns:
        Updated user settings (with boolean configured flags, never raw keys).
    """
    from config import get_config

    settings = load_user_settings()
    api_keys = settings.get("api_keys", {})
    token_limits = settings.get("token_limit_overrides", {})

    # Merge API key updates
    if body.google_api_key is not None:
        if body.google_api_key.strip():
            api_keys["google"] = body.google_api_key.strip()
        else:
            api_keys.pop("google", None)

    if body.anthropic_api_key is not None:
        if body.anthropic_api_key.strip():
            api_keys["anthropic"] = body.anthropic_api_key.strip()
        else:
            api_keys.pop("anthropic", None)

    if body.ollama_url is not None:
        if body.ollama_url.strip():
            api_keys["ollama"] = body.ollama_url.strip()
        else:
            api_keys.pop("ollama", None)

    # Merge token limit overrides
    if body.token_limit_overrides is not None:
        token_limits.update(body.token_limit_overrides)

    # Merge image generation settings
    if body.image_generation_enabled is not None:
        settings["image_generation_enabled"] = body.image_generation_enabled
    if body.image_model is not None:
        settings["image_model"] = body.image_model

    settings["api_keys"] = api_keys
    settings["token_limit_overrides"] = token_limits
    save_user_settings(settings)

    # Build response (never return raw keys)
    try:
        config = get_config()
        google_env = bool(config.google_api_key)
        anthropic_env = bool(config.anthropic_api_key)
    except Exception:
        google_env = False
        anthropic_env = False

    return UserSettingsResponse(
        google_api_key_configured=bool(api_keys.get("google")) or google_env,
        anthropic_api_key_configured=bool(api_keys.get("anthropic")) or anthropic_env,
        ollama_url=str(api_keys.get("ollama", "")),
        token_limit_overrides={
            k: v for k, v in token_limits.items() if isinstance(v, int)
        },
        image_generation_enabled=bool(settings.get("image_generation_enabled", False)),
        image_model=str(settings.get("image_model", "imagen-4.0-generate-001")),
    )


# =============================================================================
# Model Listing Endpoint
# =============================================================================


def _normalize_provider(provider: str) -> str:
    """Normalize provider name: 'claude' -> 'anthropic'."""
    return "anthropic" if provider.lower() == "claude" else provider.lower()


def _get_api_key_for_provider(provider: str) -> str | None:
    """Get API key for a provider from user-settings or env vars."""
    from config import get_config

    normalized = _normalize_provider(provider)
    settings = load_user_settings()
    api_keys = settings.get("api_keys", {})

    # Check user-settings first
    if normalized == "gemini" and api_keys.get("google"):
        return str(api_keys["google"])
    if normalized == "anthropic" and api_keys.get("anthropic"):
        return str(api_keys["anthropic"])
    if normalized == "ollama":
        return api_keys.get("ollama", "http://localhost:11434")

    # Fall back to env vars
    try:
        config = get_config()
        if normalized == "gemini":
            return config.google_api_key or None
        if normalized == "anthropic":
            return config.anthropic_api_key or None
        if normalized == "ollama":
            return config.ollama_base_url or "http://localhost:11434"
    except Exception:
        pass

    return None


def _fetch_models_from_api(provider: str) -> list[str]:
    """Fetch available models from a provider's API. Raises on failure."""
    normalized = _normalize_provider(provider)
    api_key = _get_api_key_for_provider(provider)

    if normalized == "gemini":
        if not api_key:
            raise ValueError("No Google API key configured")
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
            if "generateContent" in (m.supported_generation_methods or []):
                # Model name is like 'models/gemini-1.5-flash' — extract the ID
                model_id = m.name.replace("models/", "") if m.name else ""
                if model_id:
                    models.append(model_id)
        return sorted(models)

    if normalized == "anthropic":
        if not api_key:
            raise ValueError("No Anthropic API key configured")
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        result = client.models.list()
        models = [m.id for m in result.data]
        return sorted(models)

    if normalized == "ollama":
        import httpx

        base_url = api_key or "http://localhost:11434"
        resp = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]

    raise ValueError(f"Unsupported provider: {provider}")


@router.get("/models/{provider}", response_model=ModelListResponse)
async def list_models(provider: str) -> ModelListResponse:
    """List available models for a provider.

    Queries the provider's API for available models, with an in-memory
    cache (60s TTL). Falls back to a static list if the API call fails.

    Args:
        provider: Provider name (gemini, anthropic, claude, ollama).

    Returns:
        Model list with source indicator.
    """
    if provider.lower() not in _VALID_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {provider}. Must be one of: {', '.join(sorted(_VALID_PROVIDERS))}",
        )

    normalized = _normalize_provider(provider)

    # Check cache
    if normalized in _model_cache:
        models, source, ts = _model_cache[normalized]
        if time.time() - ts < _CACHE_TTL:
            return ModelListResponse(
                provider=normalized, models=models, source=source, error=None
            )

    # Try live API
    try:
        models = _fetch_models_from_api(provider)
        _model_cache[normalized] = (models, "api", time.time())
        return ModelListResponse(
            provider=normalized, models=models, source="api", error=None
        )
    except Exception as e:
        error_msg = str(e)
        logger.warning("Failed to fetch models for %s: %s", normalized, error_msg)
        fallback = FALLBACK_MODELS.get(normalized, [])
        _model_cache[normalized] = (fallback, "fallback", time.time())
        return ModelListResponse(
            provider=normalized, models=fallback, source="fallback", error=error_msg
        )


# =============================================================================
# Character Endpoints
# =============================================================================


def _load_library_characters() -> dict[str, CharacterConfig]:
    """Load characters from the library directory.

    Returns:
        Dict of CharacterConfig keyed by lowercase name.
    """
    library_dir = PROJECT_ROOT / "config" / "characters" / "library"
    configs: dict[str, CharacterConfig] = {}

    if not library_dir.exists():
        return configs

    for yaml_file in library_dir.glob("*.yaml"):
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError:
            continue

        if data is None:
            continue

        # Map YAML 'class' to Pydantic 'character_class' if needed
        if "class" in data and "character_class" not in data:
            data["character_class"] = data.pop("class")

        try:
            config = CharacterConfig(**data)
        except (ValidationError, ValueError):
            continue

        configs[config.name.lower()] = config

    return configs


def _load_library_backstory(name_lower: str) -> str:
    """Load the backstory field from a library character's YAML file.

    Args:
        name_lower: Lowercased character name to look up.

    Returns:
        Backstory string, or empty string if not found.
    """
    library_dir = PROJECT_ROOT / "config" / "characters" / "library"
    if not library_dir.exists():
        return ""

    for yaml_file in library_dir.glob("*.yaml"):
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError:
            continue
        if data and data.get("name", "").lower() == name_lower:
            return str(data.get("backstory", ""))

    return ""


@router.get("/characters", response_model=list[CharacterResponse])
async def list_characters() -> list[CharacterResponse]:
    """List all available characters from presets and library.

    Excludes DM config. Combines preset characters from
    config/characters/*.yaml with library characters from
    config/characters/library/*.yaml.

    Returns:
        List of character objects with source indicated.
    """
    characters: list[CharacterResponse] = []

    # Load preset characters
    try:
        preset_configs = load_character_configs()
    except (ValueError, OSError):
        preset_configs = {}
    for config in preset_configs.values():
        characters.append(
            CharacterResponse(
                name=config.name,
                character_class=config.character_class,
                personality=config.personality,
                color=config.color,
                provider=config.provider,
                model=config.model,
                source="preset",
            )
        )

    # Load library characters
    library_configs = _load_library_characters()
    for config in library_configs.values():
        characters.append(
            CharacterResponse(
                name=config.name,
                character_class=config.character_class,
                personality=config.personality,
                color=config.color,
                provider=config.provider,
                model=config.model,
                source="library",
            )
        )

    return characters


@router.get("/characters/{name}", response_model=CharacterDetailResponse)
async def get_character(name: str) -> CharacterDetailResponse:
    """Get character details by name (case-insensitive).

    Searches presets first, then library.

    Args:
        name: Character name (lowercase match).

    Returns:
        Full character details including token_limit.

    Raises:
        HTTPException: 404 if character not found.
    """
    lookup = name.lower()

    # Check presets first
    try:
        preset_configs = load_character_configs()
    except (ValueError, OSError):
        preset_configs = {}
    if lookup in preset_configs:
        config = preset_configs[lookup]
        return CharacterDetailResponse(
            name=config.name,
            character_class=config.character_class,
            personality=config.personality,
            color=config.color,
            provider=config.provider,
            model=config.model,
            source="preset",
            token_limit=config.token_limit,
        )

    # Check library
    library_configs = _load_library_characters()
    if lookup in library_configs:
        config = library_configs[lookup]
        backstory = _load_library_backstory(lookup)
        return CharacterDetailResponse(
            name=config.name,
            character_class=config.character_class,
            personality=config.personality,
            color=config.color,
            provider=config.provider,
            model=config.model,
            source="library",
            token_limit=config.token_limit,
            backstory=backstory,
        )

    raise HTTPException(status_code=404, detail=f"Character '{name}' not found")


# =============================================================================
# Character Mutation Endpoints
# =============================================================================


def _sanitize_character_name(name: str) -> str:
    """Sanitize a character name for use as a YAML filename.

    Validates against path traversal and produces a safe filename.

    Args:
        name: Raw character name.

    Returns:
        Sanitized lowercase filename stem (without extension).

    Raises:
        HTTPException: 400 if name contains dangerous characters.
    """
    # Reject path traversal patterns
    if any(c in name for c in ("/", "\\", "\x00")) or ".." in name:
        raise HTTPException(
            status_code=400,
            detail="Character name contains invalid characters",
        )

    # Build safe filename: lowercase, spaces to hyphens, strip non-alnum/hyphen
    safe = name.strip().lower().replace(" ", "-")
    safe = "".join(c for c in safe if c.isalnum() or c == "-")
    safe = safe.strip("-")

    if not safe:
        raise HTTPException(
            status_code=400,
            detail="Character name must contain at least one alphanumeric character",
        )

    return safe


def _is_preset_character(name: str) -> bool:
    """Check if a character name matches a preset character.

    Args:
        name: Character name (case-insensitive).

    Returns:
        True if the character is a preset.
    """
    try:
        preset_configs = load_character_configs()
    except (ValueError, OSError):
        preset_configs = {}
    return name.lower() in preset_configs


def _find_preset_yaml(name: str) -> Path | None:
    """Locate the preset YAML file for a character by name.

    Args:
        name: Character name (case-insensitive).

    Returns:
        Path to the YAML file, or None if not found.
    """

    chars_dir = PROJECT_ROOT / "config" / "characters"
    if not chars_dir.exists():
        return None

    lookup = name.lower()
    for yaml_file in chars_dir.glob("*.yaml"):
        if yaml_file.name == "dm.yaml":
            continue
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError:
            continue
        if data and data.get("name", "").lower() == lookup:
            return yaml_file

    return None


async def _update_preset_character(
    name: str, update_data: dict[str, object]
) -> CharacterDetailResponse:
    """Update LLM config fields on a preset character.

    Args:
        name: Character name (case-insensitive).
        update_data: Dict with provider/model/token_limit fields.

    Returns:
        Updated character detail response.

    Raises:
        HTTPException: 404 if YAML file not found, 500 on write error.
    """
    yaml_file = _find_preset_yaml(name)
    if yaml_file is None:
        raise HTTPException(
            status_code=404,
            detail=f"Preset character file for '{name}' not found",
        )

    try:
        with open(yaml_file, encoding="utf-8") as f:
            file_data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to read character file: {e}"
        ) from None

    # Apply allowed updates
    for key, value in update_data.items():
        file_data[key] = value

    try:
        with open(yaml_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(file_data, f, default_flow_style=False, allow_unicode=True)
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update character: {e}"
        ) from None

    # Map YAML 'class' to character_class
    char_class = file_data.get("character_class", file_data.get("class", ""))

    return CharacterDetailResponse(
        name=file_data.get("name", name),
        character_class=char_class,
        personality=file_data.get("personality", ""),
        color=file_data.get("color", "#808080"),
        provider=file_data.get("provider", "gemini"),
        model=file_data.get("model", ""),
        source="preset",
        token_limit=file_data.get("token_limit", 4000),
        backstory=str(file_data.get("backstory", "")),
    )


@router.post("/characters", response_model=CharacterDetailResponse, status_code=201)
async def create_character(body: CharacterCreateRequest) -> CharacterDetailResponse:
    """Create a new custom character and save to the library.

    Args:
        body: Character creation data.

    Returns:
        Created character details with 201 status.

    Raises:
        HTTPException: 400 for invalid name, 409 if name already exists.
    """
    safe_filename = _sanitize_character_name(body.name)
    library_dir = PROJECT_ROOT / "config" / "characters" / "library"
    library_dir.mkdir(parents=True, exist_ok=True)

    # Check for name collision with presets
    if _is_preset_character(body.name):
        raise HTTPException(
            status_code=409,
            detail=f"A preset character named '{body.name}' already exists",
        )

    # Check for name collision with existing library characters
    library_configs = _load_library_characters()
    if body.name.lower() in library_configs:
        raise HTTPException(
            status_code=409,
            detail=f"A library character named '{body.name}' already exists",
        )

    # Check for filename collision (different names can sanitize to the same filename)
    filepath = library_dir / f"{safe_filename}.yaml"
    if filepath.exists():
        raise HTTPException(
            status_code=409,
            detail=f"A character file '{safe_filename}.yaml' already exists",
        )

    # Validate through CharacterConfig model
    try:
        config = CharacterConfig(
            name=body.name,
            character_class=body.character_class,
            personality=body.personality or f"A {body.character_class} adventurer.",
            color=body.color,
            provider=body.provider,
            model=body.model,
            token_limit=body.token_limit,
        )
    except (ValidationError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from None

    # Build YAML data — use 'class' key for file compatibility
    yaml_data: dict[str, object] = {
        "name": config.name,
        "class": config.character_class,
        "personality": config.personality,
        "color": config.color,
        "provider": config.provider,
        "model": config.model,
        "token_limit": config.token_limit,
    }
    if body.backstory:
        yaml_data["backstory"] = body.backstory

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.safe_dump(yaml_data, f, default_flow_style=False, allow_unicode=True)
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save character: {e}"
        ) from None

    return CharacterDetailResponse(
        name=config.name,
        character_class=config.character_class,
        personality=config.personality,
        color=config.color,
        provider=config.provider,
        model=config.model,
        source="library",
        token_limit=config.token_limit,
        backstory=body.backstory or "",
    )


@router.put("/characters/{name}", response_model=CharacterDetailResponse)
async def update_character(
    name: str, body: CharacterUpdateRequest
) -> CharacterDetailResponse:
    """Update an existing library character.

    Only library characters can be updated; presets are read-only.

    Args:
        name: Character name (case-insensitive lookup).
        body: Partial update fields.

    Returns:
        Updated character details.

    Raises:
        HTTPException: 400 for path traversal, 403 for presets, 404 if not found.
    """
    # Validate the path parameter
    if any(c in name for c in ("/", "\\", "\x00")) or ".." in name:
        raise HTTPException(
            status_code=400,
            detail="Character name contains invalid characters",
        )

    lookup = name.lower()

    # Preset characters: only allow LLM config fields
    if _is_preset_character(name):
        _PRESET_ALLOWED_FIELDS = {"provider", "model", "token_limit"}
        update_data = body.model_dump(exclude_none=True)
        disallowed = set(update_data.keys()) - _PRESET_ALLOWED_FIELDS
        if disallowed:
            raise HTTPException(
                status_code=403,
                detail=f"Cannot modify {', '.join(sorted(disallowed))} on preset characters. "
                f"Only {', '.join(sorted(_PRESET_ALLOWED_FIELDS))} can be changed.",
            )
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No fields to update",
            )
        return await _update_preset_character(name, update_data)

    # Find existing library character
    library_dir = PROJECT_ROOT / "config" / "characters" / "library"
    library_configs = _load_library_characters()

    if lookup not in library_configs:
        raise HTTPException(
            status_code=404,
            detail=f"Library character '{name}' not found",
        )

    existing = library_configs[lookup]

    # Apply partial updates
    update_data = body.model_dump(exclude_none=True)
    merged = {
        "name": update_data.get("name", existing.name),
        "character_class": update_data.get("character_class", existing.character_class),
        "personality": update_data.get("personality", existing.personality),
        "color": update_data.get("color", existing.color),
        "provider": update_data.get("provider", existing.provider),
        "model": update_data.get("model", existing.model),
        "token_limit": update_data.get("token_limit", existing.token_limit),
    }

    # Validate through CharacterConfig
    try:
        config = CharacterConfig(**merged)
    except (ValidationError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from None

    # If name changed, check for collisions
    if config.name.lower() != lookup:
        if _is_preset_character(config.name):
            raise HTTPException(
                status_code=409,
                detail=f"A preset character named '{config.name}' already exists",
            )
        if config.name.lower() in library_configs:
            raise HTTPException(
                status_code=409,
                detail=f"A library character named '{config.name}' already exists",
            )

    # Find the existing YAML file
    existing_file = None
    for yaml_file in library_dir.glob("*.yaml"):
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError:
            continue
        if data and data.get("name", "").lower() == lookup:
            existing_file = yaml_file
            break

    if existing_file is None:
        raise HTTPException(
            status_code=404,
            detail=f"Library character file for '{name}' not found",
        )

    # Read existing file data to preserve extra fields (abilities, skills, etc.)
    try:
        with open(existing_file, encoding="utf-8") as f:
            file_data = yaml.safe_load(f) or {}
    except yaml.YAMLError:
        file_data = {}

    # Update the standard fields
    file_data["name"] = config.name
    file_data["class"] = config.character_class
    file_data["personality"] = config.personality
    file_data["color"] = config.color
    file_data["provider"] = config.provider
    file_data["model"] = config.model
    file_data["token_limit"] = config.token_limit

    # Remove 'character_class' key if present (we use 'class' in YAML)
    file_data.pop("character_class", None)

    # Handle backstory
    if body.backstory is not None:
        if body.backstory:
            file_data["backstory"] = body.backstory
        else:
            file_data.pop("backstory", None)

    # If name changed, use a new filename
    if config.name.lower() != lookup:
        new_safe = _sanitize_character_name(config.name)
        new_file = library_dir / f"{new_safe}.yaml"
        try:
            with open(new_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    file_data, f, default_flow_style=False, allow_unicode=True
                )
        except OSError as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update character: {e}"
            ) from None
        try:
            existing_file.unlink()
        except OSError:
            # Clean up the new file to avoid duplicates
            new_file.unlink(missing_ok=True)
            raise HTTPException(
                status_code=500,
                detail="Failed to remove old character file after rename",
            ) from None
    else:
        try:
            with open(existing_file, "w", encoding="utf-8") as f:
                yaml.safe_dump(
                    file_data, f, default_flow_style=False, allow_unicode=True
                )
        except OSError as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update character: {e}"
            ) from None

    return CharacterDetailResponse(
        name=config.name,
        character_class=config.character_class,
        personality=config.personality,
        color=config.color,
        provider=config.provider,
        model=config.model,
        source="library",
        token_limit=config.token_limit,
        backstory=str(file_data.get("backstory", "")),
    )


@router.delete("/characters/{name}", status_code=204)
async def delete_character(name: str) -> None:
    """Delete a library character.

    Only library characters can be deleted; presets are protected.

    Args:
        name: Character name (case-insensitive lookup).

    Raises:
        HTTPException: 400 for path traversal, 403 for presets, 404 if not found.
    """
    # Validate the path parameter
    if any(c in name for c in ("/", "\\", "\x00")) or ".." in name:
        raise HTTPException(
            status_code=400,
            detail="Character name contains invalid characters",
        )

    # Reject deletion of presets
    if _is_preset_character(name):
        raise HTTPException(
            status_code=403,
            detail="Preset characters cannot be deleted",
        )

    lookup = name.lower()
    library_dir = PROJECT_ROOT / "config" / "characters" / "library"

    # Find the YAML file
    found_file = None
    if library_dir.exists():
        for yaml_file in library_dir.glob("*.yaml"):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except yaml.YAMLError:
                continue
            if data and data.get("name", "").lower() == lookup:
                found_file = yaml_file
                break

    if found_file is None:
        raise HTTPException(
            status_code=404,
            detail=f"Library character '{name}' not found",
        )

    try:
        found_file.unlink()
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete character: {e}"
        ) from None


# =============================================================================
# Fork Management Endpoints (Story 16-10)
# =============================================================================


def _validate_and_check_session(session_id: str) -> None:
    """Validate session_id format and check session exists.

    Args:
        session_id: Session ID string.

    Raises:
        HTTPException: 400 for invalid format, 404 if not found.
    """
    try:
        _validate_session_id(session_id)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid session ID: {session_id}"
        ) from None

    metadata = load_session_metadata(session_id)
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")


def _validate_fork_id_param(fork_id: str) -> None:
    """Validate fork_id path parameter at the API boundary.

    Rejects fork_ids containing path traversal characters before they
    reach persistence functions. This is defense-in-depth alongside
    persistence._validate_fork_id().

    Args:
        fork_id: Fork ID from URL path parameter.

    Raises:
        HTTPException: 400 if fork_id contains invalid characters.
    """
    if not fork_id or not fork_id.replace("_", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid fork ID: {fork_id!r}. Must be alphanumeric (underscores allowed).",
        )


def _validate_turn_param(turn: int) -> None:
    """Validate turn number path parameter.

    Args:
        turn: Turn number from URL path parameter.

    Raises:
        HTTPException: 400 if turn is negative.
    """
    if turn < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid turn number: {turn}. Must be non-negative.",
        )


@router.get("/sessions/{session_id}/forks", response_model=list[ForkMetadataResponse])
async def list_session_forks(
    session_id: str,
) -> list[ForkMetadataResponse]:
    """List all forks for a session, sorted by creation time.

    Args:
        session_id: Session ID string.

    Returns:
        List of fork metadata objects.
    """
    _validate_and_check_session(session_id)

    try:
        forks = list_forks(session_id)
    except (OSError, ValueError) as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list forks: {e}"
        ) from None

    return [
        ForkMetadataResponse(
            fork_id=f.fork_id,
            name=f.name,
            parent_session_id=f.parent_session_id,
            branch_turn=f.branch_turn,
            created_at=f.created_at,
            updated_at=f.updated_at,
            turn_count=f.turn_count,
        )
        for f in forks
    ]


@router.post(
    "/sessions/{session_id}/forks",
    response_model=ForkMetadataResponse,
    status_code=201,
)
async def create_session_fork(
    session_id: str, body: ForkCreateRequest
) -> ForkMetadataResponse:
    """Create a new fork from the latest checkpoint.

    Args:
        session_id: Session ID string.
        body: Fork creation data with name.

    Returns:
        Created fork metadata with 201 status.
    """
    _validate_and_check_session(session_id)

    # Load latest checkpoint to get game state
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is None:
        raise HTTPException(
            status_code=400,
            detail="Session has no checkpoints to fork from",
        )

    state = load_checkpoint(session_id, latest_turn)
    if state is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to load latest checkpoint",
        )

    try:
        fork_meta = create_fork(state=state, session_id=session_id, fork_name=body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create fork: {e}"
        ) from None

    return ForkMetadataResponse(
        fork_id=fork_meta.fork_id,
        name=fork_meta.name,
        parent_session_id=fork_meta.parent_session_id,
        branch_turn=fork_meta.branch_turn,
        created_at=fork_meta.created_at,
        updated_at=fork_meta.updated_at,
        turn_count=fork_meta.turn_count,
    )


@router.put(
    "/sessions/{session_id}/forks/{fork_id}",
    response_model=ForkMetadataResponse,
)
async def rename_session_fork(
    session_id: str, fork_id: str, body: ForkRenameRequest
) -> ForkMetadataResponse:
    """Rename a fork.

    Args:
        session_id: Session ID string.
        fork_id: Fork ID to rename.
        body: New fork name.

    Returns:
        Updated fork metadata.
    """
    _validate_and_check_session(session_id)
    _validate_fork_id_param(fork_id)

    try:
        fork_meta = rename_fork(session_id, fork_id, body.name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to rename fork: {e}"
        ) from None

    return ForkMetadataResponse(
        fork_id=fork_meta.fork_id,
        name=fork_meta.name,
        parent_session_id=fork_meta.parent_session_id,
        branch_turn=fork_meta.branch_turn,
        created_at=fork_meta.created_at,
        updated_at=fork_meta.updated_at,
        turn_count=fork_meta.turn_count,
    )


@router.delete("/sessions/{session_id}/forks/{fork_id}", status_code=204)
async def delete_session_fork(session_id: str, fork_id: str) -> None:
    """Delete a fork and its checkpoint data.

    Args:
        session_id: Session ID string.
        fork_id: Fork ID to delete.
    """
    _validate_and_check_session(session_id)
    _validate_fork_id_param(fork_id)

    try:
        deleted = delete_fork(session_id, fork_id, active_fork_id=None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete fork: {e}"
        ) from None

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Fork '{fork_id}' not found in session '{session_id}'",
        )


@router.post("/sessions/{session_id}/forks/{fork_id}/switch", status_code=200)
async def switch_to_fork(session_id: str, fork_id: str) -> dict[str, str]:
    """Switch to a fork timeline.

    Loads the fork's latest checkpoint. The frontend should reconnect
    its WebSocket to get the updated state.

    Args:
        session_id: Session ID string.
        fork_id: Fork ID to switch to.

    Returns:
        Success message with fork ID.
    """
    from persistence import get_latest_fork_checkpoint, load_fork_checkpoint

    _validate_and_check_session(session_id)
    _validate_fork_id_param(fork_id)

    latest_turn = get_latest_fork_checkpoint(session_id, fork_id)
    if latest_turn is None:
        raise HTTPException(
            status_code=404,
            detail=f"Fork '{fork_id}' not found or has no checkpoints",
        )

    state = load_fork_checkpoint(session_id, fork_id, latest_turn)
    if state is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to load fork checkpoint",
        )

    # Tag the state with the active fork so the engine and UI know which
    # timeline is loaded.  Do NOT overwrite the main timeline's checkpoints
    # -- the fork data lives in its own directory and can be loaded via
    # get_latest_fork_checkpoint / load_fork_checkpoint.
    state["active_fork_id"] = fork_id  # type: ignore[literal-required]

    return {"status": "ok", "fork_id": fork_id}


@router.post("/sessions/{session_id}/forks/{fork_id}/promote", status_code=200)
async def promote_session_fork(session_id: str, fork_id: str) -> dict[str, object]:
    """Promote a fork to become the main timeline.

    Args:
        session_id: Session ID string.
        fork_id: Fork ID to promote.

    Returns:
        Success message with new latest turn number.
    """
    _validate_and_check_session(session_id)
    _validate_fork_id_param(fork_id)

    try:
        latest_turn = promote_fork(session_id, fork_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to promote fork: {e}"
        ) from None

    return {"status": "ok", "latest_turn": latest_turn}


@router.post("/sessions/{session_id}/forks/return-to-main", status_code=200)
async def return_to_main_timeline(
    session_id: str,
) -> dict[str, str]:
    """Return from a fork to the main timeline.

    Loads the latest main timeline checkpoint. The frontend should
    reconnect its WebSocket to get the updated state.

    Args:
        session_id: Session ID string.

    Returns:
        Success message.
    """
    _validate_and_check_session(session_id)

    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is None:
        raise HTTPException(
            status_code=400,
            detail="Session has no main timeline checkpoints",
        )

    state = load_checkpoint(session_id, latest_turn)
    if state is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to load main timeline checkpoint",
        )

    return {"status": "ok"}


@router.get(
    "/sessions/{session_id}/forks/{fork_id}/compare",
    response_model=ComparisonDataResponse,
)
async def compare_fork(session_id: str, fork_id: str) -> ComparisonDataResponse:
    """Get comparison data between main timeline and a fork.

    Args:
        session_id: Session ID string.
        fork_id: Fork ID to compare against main.

    Returns:
        Comparison data with aligned turns from both timelines.
    """
    _validate_and_check_session(session_id)
    _validate_fork_id_param(fork_id)

    try:
        comparison = build_comparison_data(session_id, fork_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to build comparison data: {e}",
        ) from None

    if comparison is None:
        raise HTTPException(
            status_code=404,
            detail=f"Cannot build comparison for fork '{fork_id}' — fork or checkpoint data not found",
        )

    return ComparisonDataResponse(
        session_id=comparison.session_id,
        branch_turn=comparison.branch_turn,
        left=ComparisonTimelineResponse(
            label=comparison.left.label,
            timeline_type=comparison.left.timeline_type,
            fork_id=comparison.left.fork_id,
            turns=[
                ComparisonTurnResponse(
                    turn_number=t.turn_number,
                    entries=t.entries,
                    is_branch_point=t.is_branch_point,
                    is_ended=t.is_ended,
                )
                for t in comparison.left.turns
            ],
            total_turns=comparison.left.total_turns,
        ),
        right=ComparisonTimelineResponse(
            label=comparison.right.label,
            timeline_type=comparison.right.timeline_type,
            fork_id=comparison.right.fork_id,
            turns=[
                ComparisonTurnResponse(
                    turn_number=t.turn_number,
                    entries=t.entries,
                    is_branch_point=t.is_branch_point,
                    is_ended=t.is_ended,
                )
                for t in comparison.right.turns
            ],
            total_turns=comparison.right.total_turns,
        ),
    )


# =============================================================================
# Checkpoint Endpoints (Story 16-10)
# =============================================================================


@router.get(
    "/sessions/{session_id}/checkpoints",
    response_model=list[CheckpointInfoResponse],
)
async def list_session_checkpoints(
    session_id: str,
) -> list[CheckpointInfoResponse]:
    """List all checkpoints for a session, newest first.

    Args:
        session_id: Session ID string.

    Returns:
        List of checkpoint info objects sorted by turn number descending.
    """
    _validate_and_check_session(session_id)

    try:
        infos = list_checkpoint_info(session_id)
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list checkpoints: {e}"
        ) from None

    return [
        CheckpointInfoResponse(
            turn_number=info.turn_number,
            timestamp=info.timestamp,
            brief_context=info.brief_context,
            message_count=info.message_count,
        )
        for info in infos
    ]


@router.get(
    "/sessions/{session_id}/checkpoints/{turn}/preview",
    response_model=CheckpointPreviewResponse,
)
async def preview_checkpoint(session_id: str, turn: int) -> CheckpointPreviewResponse:
    """Get a preview of log entries from a specific checkpoint.

    Args:
        session_id: Session ID string.
        turn: Turn number to preview.

    Returns:
        Last few log entries from the checkpoint.
    """
    _validate_and_check_session(session_id)
    _validate_turn_param(turn)

    try:
        entries = get_checkpoint_preview(session_id, turn)
    except OSError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load checkpoint preview: {e}"
        ) from None

    if entries is None:
        raise HTTPException(
            status_code=404,
            detail=f"Checkpoint at turn {turn} not found",
        )

    return CheckpointPreviewResponse(turn_number=turn, entries=entries)


@router.post("/sessions/{session_id}/checkpoints/{turn}/restore", status_code=200)
async def restore_checkpoint(session_id: str, turn: int) -> dict[str, object]:
    """Restore game state to a specific checkpoint.

    Loads the checkpoint and saves it as the current state.
    Callers should stop autopilot before calling this endpoint
    to avoid race conditions with the running engine.

    Args:
        session_id: Session ID string.
        turn: Turn number to restore.

    Returns:
        Success message with restored turn number.
    """
    _validate_and_check_session(session_id)
    _validate_turn_param(turn)

    state = load_checkpoint(session_id, turn)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Checkpoint at turn {turn} not found",
        )

    # Save restored state as current
    try:
        save_checkpoint(state, session_id, turn, update_metadata=False)
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restore checkpoint: {e}",
        ) from None

    return {"status": "ok", "turn": turn}


# =============================================================================
# Character Sheet Endpoint (Story 16-10)
# =============================================================================


@router.get(
    "/sessions/{session_id}/character-sheets/{character_name}",
    response_model=CharacterSheetResponse,
)
async def get_character_sheet(
    session_id: str, character_name: str
) -> CharacterSheetResponse:
    """Get the full character sheet for a character in a session.

    Loads the latest game state and extracts the character sheet.

    Args:
        session_id: Session ID string.
        character_name: Character name (case-insensitive lookup).

    Returns:
        Full character sheet data.
    """
    _validate_and_check_session(session_id)

    # Validate character_name to reject path traversal patterns
    if any(c in character_name for c in ("/", "\\", "\x00")) or ".." in character_name:
        raise HTTPException(
            status_code=400,
            detail="Character name contains invalid characters",
        )

    # Load latest checkpoint
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is None:
        raise HTTPException(
            status_code=404,
            detail="Session has no checkpoints",
        )

    state = load_checkpoint(session_id, latest_turn)
    if state is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to load latest checkpoint",
        )

    # Find character sheet from state
    character_sheets = state.get("character_sheets", {})
    if not character_sheets:
        raise HTTPException(
            status_code=404,
            detail="No character sheets found in session",
        )

    # Case-insensitive lookup by key or character name
    sheet = None
    lookup = character_name.lower()
    for key, s in character_sheets.items():
        if key.lower() == lookup:
            sheet = s
            break
        # Also check by the sheet's name field if it's a CharacterSheet model
        if hasattr(s, "name") and s.name.lower() == lookup:
            sheet = s
            break

    if sheet is None:
        raise HTTPException(
            status_code=404,
            detail=f"Character sheet for '{character_name}' not found",
        )

    # If sheet is a dict-like object (from deserialization), try to access as attributes
    # If it's a Pydantic model (CharacterSheet), use its properties
    from api.schemas import (
        ArmorResponse,
        DeathSavesResponse,
        EquipmentItemResponse,
        SpellResponse,
        SpellSlotsResponse,
        WeaponResponse,
    )

    # Handle both dict and model access patterns
    def _get(obj: object, attr: str, default: object = None) -> object:
        if hasattr(obj, attr):
            return getattr(obj, attr)
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return default

    # Build response
    weapons_raw = _get(sheet, "weapons", [])
    weapons_resp = []
    for w in weapons_raw:  # type: ignore[union-attr]
        weapons_resp.append(
            WeaponResponse(
                name=_get(w, "name", ""),  # type: ignore[arg-type]
                damage_dice=_get(w, "damage_dice", "1d4"),  # type: ignore[arg-type]
                damage_type=_get(w, "damage_type", "slashing"),  # type: ignore[arg-type]
                properties=_get(w, "properties", []),  # type: ignore[arg-type]
                attack_bonus=_get(w, "attack_bonus", 0),  # type: ignore[arg-type]
                is_equipped=_get(w, "is_equipped", False),  # type: ignore[arg-type]
            )
        )

    armor_raw = _get(sheet, "armor")
    armor_resp = None
    if armor_raw is not None:
        armor_resp = ArmorResponse(
            name=_get(armor_raw, "name", ""),  # type: ignore[arg-type]
            armor_class=_get(armor_raw, "armor_class", 10),  # type: ignore[arg-type]
            armor_type=_get(armor_raw, "armor_type", "light"),  # type: ignore[arg-type]
            strength_requirement=_get(armor_raw, "strength_requirement", 0),  # type: ignore[arg-type]
            stealth_disadvantage=_get(armor_raw, "stealth_disadvantage", False),  # type: ignore[arg-type]
            is_equipped=_get(armor_raw, "is_equipped", True),  # type: ignore[arg-type]
        )

    equipment_raw = _get(sheet, "equipment", [])
    equipment_resp = []
    for e in equipment_raw:  # type: ignore[union-attr]
        equipment_resp.append(
            EquipmentItemResponse(
                name=_get(e, "name", ""),  # type: ignore[arg-type]
                quantity=_get(e, "quantity", 1),  # type: ignore[arg-type]
                description=_get(e, "description", ""),  # type: ignore[arg-type]
                weight=_get(e, "weight", 0.0),  # type: ignore[arg-type]
            )
        )

    spells_raw = _get(sheet, "spells_known", [])
    spells_resp = []
    for s in spells_raw:  # type: ignore[union-attr]
        spells_resp.append(
            SpellResponse(
                name=_get(s, "name", ""),  # type: ignore[arg-type]
                level=_get(s, "level", 0),  # type: ignore[arg-type]
                school=_get(s, "school", ""),  # type: ignore[arg-type]
                casting_time=_get(s, "casting_time", "1 action"),  # type: ignore[arg-type]
                range=_get(s, "range", "Self"),  # type: ignore[arg-type]
                components=_get(s, "components", []),  # type: ignore[arg-type]
                duration=_get(s, "duration", "Instantaneous"),  # type: ignore[arg-type]
                description=_get(s, "description", ""),  # type: ignore[arg-type]
                is_prepared=_get(s, "is_prepared", True),  # type: ignore[arg-type]
            )
        )

    slots_raw = _get(sheet, "spell_slots", {})
    slots_resp: dict[str, SpellSlotsResponse] = {}
    for lvl, slot in (slots_raw or {}).items():  # type: ignore[union-attr]
        slots_resp[str(lvl)] = SpellSlotsResponse(
            max=_get(slot, "max", 0),  # type: ignore[arg-type]
            current=_get(slot, "current", 0),  # type: ignore[arg-type]
        )

    death_raw = _get(sheet, "death_saves")
    death_resp = DeathSavesResponse()
    if death_raw is not None:
        death_resp = DeathSavesResponse(
            successes=_get(death_raw, "successes", 0),  # type: ignore[arg-type]
            failures=_get(death_raw, "failures", 0),  # type: ignore[arg-type]
        )

    return CharacterSheetResponse(
        name=_get(sheet, "name", ""),  # type: ignore[arg-type]
        race=_get(sheet, "race", ""),  # type: ignore[arg-type]
        character_class=_get(sheet, "character_class", ""),  # type: ignore[arg-type]
        level=_get(sheet, "level", 1),  # type: ignore[arg-type]
        background=_get(sheet, "background", ""),  # type: ignore[arg-type]
        alignment=_get(sheet, "alignment", ""),  # type: ignore[arg-type]
        experience_points=_get(sheet, "experience_points", 0),  # type: ignore[arg-type]
        strength=_get(sheet, "strength", 10),  # type: ignore[arg-type]
        dexterity=_get(sheet, "dexterity", 10),  # type: ignore[arg-type]
        constitution=_get(sheet, "constitution", 10),  # type: ignore[arg-type]
        intelligence=_get(sheet, "intelligence", 10),  # type: ignore[arg-type]
        wisdom=_get(sheet, "wisdom", 10),  # type: ignore[arg-type]
        charisma=_get(sheet, "charisma", 10),  # type: ignore[arg-type]
        strength_modifier=_get(sheet, "strength_modifier", 0),  # type: ignore[arg-type]
        dexterity_modifier=_get(sheet, "dexterity_modifier", 0),  # type: ignore[arg-type]
        constitution_modifier=_get(sheet, "constitution_modifier", 0),  # type: ignore[arg-type]
        intelligence_modifier=_get(sheet, "intelligence_modifier", 0),  # type: ignore[arg-type]
        wisdom_modifier=_get(sheet, "wisdom_modifier", 0),  # type: ignore[arg-type]
        charisma_modifier=_get(sheet, "charisma_modifier", 0),  # type: ignore[arg-type]
        proficiency_bonus=_get(sheet, "proficiency_bonus", 2),  # type: ignore[arg-type]
        armor_class=_get(sheet, "armor_class", 10),  # type: ignore[arg-type]
        initiative=_get(sheet, "initiative", 0),  # type: ignore[arg-type]
        speed=_get(sheet, "speed", 30),  # type: ignore[arg-type]
        hit_points_max=_get(sheet, "hit_points_max", 10),  # type: ignore[arg-type]
        hit_points_current=_get(sheet, "hit_points_current", 10),  # type: ignore[arg-type]
        hit_points_temp=_get(sheet, "hit_points_temp", 0),  # type: ignore[arg-type]
        hit_dice=_get(sheet, "hit_dice", "1d10"),  # type: ignore[arg-type]
        hit_dice_remaining=_get(sheet, "hit_dice_remaining", 1),  # type: ignore[arg-type]
        saving_throw_proficiencies=_get(sheet, "saving_throw_proficiencies", []),  # type: ignore[arg-type]
        skill_proficiencies=_get(sheet, "skill_proficiencies", []),  # type: ignore[arg-type]
        skill_expertise=_get(sheet, "skill_expertise", []),  # type: ignore[arg-type]
        armor_proficiencies=_get(sheet, "armor_proficiencies", []),  # type: ignore[arg-type]
        weapon_proficiencies=_get(sheet, "weapon_proficiencies", []),  # type: ignore[arg-type]
        tool_proficiencies=_get(sheet, "tool_proficiencies", []),  # type: ignore[arg-type]
        languages=_get(sheet, "languages", []),  # type: ignore[arg-type]
        class_features=_get(sheet, "class_features", []),  # type: ignore[arg-type]
        racial_traits=_get(sheet, "racial_traits", []),  # type: ignore[arg-type]
        feats=_get(sheet, "feats", []),  # type: ignore[arg-type]
        weapons=weapons_resp,
        armor=armor_resp,
        equipment=equipment_resp,
        gold=_get(sheet, "gold", 0),  # type: ignore[arg-type]
        silver=_get(sheet, "silver", 0),  # type: ignore[arg-type]
        copper=_get(sheet, "copper", 0),  # type: ignore[arg-type]
        spellcasting_ability=_get(sheet, "spellcasting_ability"),  # type: ignore[arg-type]
        spell_save_dc=_get(sheet, "spell_save_dc"),  # type: ignore[arg-type]
        spell_attack_bonus=_get(sheet, "spell_attack_bonus"),  # type: ignore[arg-type]
        cantrips=_get(sheet, "cantrips", []),  # type: ignore[arg-type]
        spells_known=spells_resp,
        spell_slots=slots_resp,
        personality_traits=_get(sheet, "personality_traits", ""),  # type: ignore[arg-type]
        ideals=_get(sheet, "ideals", ""),  # type: ignore[arg-type]
        bonds=_get(sheet, "bonds", ""),  # type: ignore[arg-type]
        flaws=_get(sheet, "flaws", ""),  # type: ignore[arg-type]
        backstory=_get(sheet, "backstory", ""),  # type: ignore[arg-type]
        conditions=_get(sheet, "conditions", []),  # type: ignore[arg-type]
        death_saves=death_resp,
    )


# =============================================================================
# Image Generation Endpoints (Story 17-3)
# =============================================================================

# UUID filename pattern for path traversal prevention
_IMAGE_FILENAME_RE = _re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.png$"
)

# UUID without extension — used by the individual download endpoint
_IMAGE_ID_RE = _re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)

# Valid generation_mode values for filename sanitization.
_VALID_GENERATION_MODES = frozenset({"current", "best", "specific", "scene"})

# Track active image generation tasks per session to prevent concurrent overload.
# Maps session_id -> set of asyncio.Task references (also keeps strong refs to tasks).
_active_image_tasks: dict[str, set[asyncio.Task[None]]] = {}
_MAX_CONCURRENT_IMAGE_TASKS = 3


def _check_image_generation_enabled() -> None:
    """Raise HTTP 400 if image generation is disabled in config.

    Checks user-settings.yaml first (UI toggle), then falls back to
    defaults.yaml for the default value.

    Raises:
        HTTPException: 400 if image generation is not enabled.
    """
    settings = load_user_settings()
    if "image_generation_enabled" in settings:
        if settings["image_generation_enabled"]:
            return
    else:
        yaml_defaults = _load_yaml_defaults()
        img_cfg = yaml_defaults.get("image_generation", {})
        if img_cfg.get("enabled", False):
            return
    raise HTTPException(
        status_code=400,
        detail="Image generation is not enabled. Enable it in Settings.",
    )


def _build_download_url(session_id: str, image_id: str) -> str:
    """Build the download URL for a generated image.

    Args:
        session_id: Session ID string.
        image_id: Image UUID string.

    Returns:
        Relative URL path to the image file.
    """
    return f"/api/sessions/{session_id}/images/{image_id}.png"


def _get_safe_session_name(session_id: str) -> str:
    """Get a filesystem-safe session name for download filenames.

    Loads session metadata name; falls back to ``session_{id}``.
    Replaces non-alphanumeric characters (except hyphens/underscores) with
    underscores and truncates to 50 characters.

    Args:
        session_id: Session ID string.

    Returns:
        Sanitized session name string.
    """
    metadata = load_session_metadata(session_id)
    name = metadata.name if metadata and metadata.name else f"session_{session_id}"
    # Replace non-ASCII and unsafe filesystem characters (ASCII alphanumeric,
    # hyphens, and underscores only — avoids Unicode passing through \w)
    safe = _re.sub(r"[^A-Za-z0-9_\-]", "_", name)
    # Collapse multiple underscores
    safe = _re.sub(r"_+", "_", safe).strip("_")
    return safe[:50] if safe else f"session_{session_id}"


async def _generate_image_background(
    session_id: str,
    task_id: str,
    log_entries: list[str],
    characters: dict[str, Any],
    turn_number: int,
    generation_mode: Literal["current", "best", "specific"],
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
        generation_mode: How the image was requested.
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
        # Ensure images dir exists (defensive -- generate_scene_image creates
        # it for the PNG, but we must guarantee it exists for the sidecar)
        images_dir = get_session_dir(session_id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = images_dir / f"{scene_image.id}.json"
        metadata_path.write_text(
            _json.dumps(scene_image.model_dump(), indent=2),
            encoding="utf-8",
        )

        # Step 4: Broadcast WebSocket event using schema for validation
        from api.schemas import SceneImageResponse, WsImageReady
        from api.websocket import manager

        download_url = _build_download_url(session_id, scene_image.id)
        ws_event = WsImageReady(
            image=SceneImageResponse(
                id=scene_image.id,
                session_id=scene_image.session_id,
                turn_number=scene_image.turn_number,
                prompt=scene_image.prompt,
                image_path=scene_image.image_path,
                provider=scene_image.provider,
                model=scene_image.model,
                generation_mode=scene_image.generation_mode,
                generated_at=scene_image.generated_at,
                download_url=download_url,
            ),
        )
        await manager.broadcast(session_id, ws_event.model_dump())

        logger.info(
            "Image generated for session %s turn %d (task %s): %s",
            session_id,
            turn_number,
            task_id,
            scene_image.id,
        )

    except ImageGenerationError as e:
        logger.error(
            "Image generation failed for session %s turn %d (task %s): %s",
            session_id,
            turn_number,
            task_id,
            e,
        )
        # Broadcast error to connected clients
        from api.websocket import manager

        await manager.broadcast(
            session_id,
            {
                "type": "error",
                "message": f"Image generation failed: {e}",
                "recoverable": True,
            },
        )

    except Exception as e:
        logger.exception(
            "Unexpected error in image generation background task "
            "(session=%s, turn=%d, task=%s)",
            session_id,
            turn_number,
            task_id,
        )
        # Broadcast generic error
        from api.websocket import manager

        await manager.broadcast(
            session_id,
            {
                "type": "error",
                "message": f"Image generation failed unexpectedly: {e}",
                "recoverable": True,
            },
        )


@router.post(
    "/sessions/{session_id}/images/generate-current",
    response_model=ImageGenerateAccepted,
    status_code=202,
)
async def generate_current_scene_image(
    session_id: str,
    body: ImageGenerateRequest | None = None,
) -> ImageGenerateAccepted:
    """Generate an image of the current scene.

    Extracts the last N log entries from the game state, builds a scene
    prompt via LLM, and generates an image. Runs as a background task.

    Args:
        session_id: Session ID string.
        body: Optional request with context_entries override.

    Returns:
        202 Accepted with task ID.
    """
    _validate_and_check_session(session_id)
    _check_image_generation_enabled()

    # Guard against too many concurrent image tasks for this session
    active = _active_image_tasks.get(session_id, set())
    # Prune completed tasks
    active = {t for t in active if not t.done()}
    _active_image_tasks[session_id] = active
    if len(active) >= _MAX_CONCURRENT_IMAGE_TASKS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many concurrent image generation requests "
            f"(max {_MAX_CONCURRENT_IMAGE_TASKS}). Please wait for "
            f"current tasks to complete.",
        )

    # Load game state
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is None:
        raise HTTPException(status_code=400, detail="Session has no checkpoints")

    state = load_checkpoint(session_id, latest_turn)
    if state is None:
        raise HTTPException(status_code=500, detail="Failed to load latest checkpoint")

    log = state.get("ground_truth_log", [])
    if not log:
        raise HTTPException(
            status_code=400, detail="Session has no narrative log entries"
        )

    context_entries = body.context_entries if body else 10
    entries = list(log[-context_entries:])
    turn_number = len(log) - 1

    characters = state.get("characters", {})
    char_dict = {
        k: v.model_dump() if hasattr(v, "model_dump") else v
        for k, v in characters.items()
    }

    # Merge race/gender from character sheets into char_dict for image prompts
    sheets = state.get("character_sheets", {})
    for name, sheet in sheets.items():
        sheet_data = sheet.model_dump() if hasattr(sheet, "model_dump") else sheet
        if name in char_dict:
            for field in ("race", "gender"):
                if field not in char_dict[name] and field in sheet_data:
                    char_dict[name][field] = sheet_data[field]
        else:
            char_dict[name] = sheet_data

    task_id = str(_uuid.uuid4())

    # Launch background task and store reference to prevent GC
    task = asyncio.create_task(
        _generate_image_background(
            session_id=session_id,
            task_id=task_id,
            log_entries=entries,
            characters=char_dict,
            turn_number=turn_number,
            generation_mode="current",
        )
    )
    active.add(task)
    task.add_done_callback(lambda t: active.discard(t))

    return ImageGenerateAccepted(
        task_id=task_id,
        session_id=session_id,
        turn_number=turn_number,
    )


@router.post(
    "/sessions/{session_id}/images/generate-turn/{turn_number}",
    response_model=ImageGenerateAccepted,
    status_code=202,
)
async def generate_turn_image(
    session_id: str,
    turn_number: int,
) -> ImageGenerateAccepted:
    """Generate an image for a specific turn.

    Extracts log entries around the given turn (+/-5 context window),
    builds a scene prompt, and generates an image as a background task.

    Args:
        session_id: Session ID string.
        turn_number: Turn number to illustrate.

    Returns:
        202 Accepted with task ID.
    """
    _validate_and_check_session(session_id)
    _check_image_generation_enabled()

    # Guard against too many concurrent image tasks for this session
    active = _active_image_tasks.get(session_id, set())
    # Prune completed tasks
    active = {t for t in active if not t.done()}
    _active_image_tasks[session_id] = active
    if len(active) >= _MAX_CONCURRENT_IMAGE_TASKS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many concurrent image generation requests "
            f"(max {_MAX_CONCURRENT_IMAGE_TASKS}). Please wait for "
            f"current tasks to complete.",
        )

    # Load game state
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is None:
        raise HTTPException(status_code=400, detail="Session has no checkpoints")

    state = load_checkpoint(session_id, latest_turn)
    if state is None:
        raise HTTPException(status_code=500, detail="Failed to load latest checkpoint")

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

    # Merge race/gender from character sheets into char_dict for image prompts
    sheets = state.get("character_sheets", {})
    for name, sheet in sheets.items():
        sheet_data = sheet.model_dump() if hasattr(sheet, "model_dump") else sheet
        if name in char_dict:
            for field in ("race", "gender"):
                if field not in char_dict[name] and field in sheet_data:
                    char_dict[name][field] = sheet_data[field]
        else:
            char_dict[name] = sheet_data

    task_id = str(_uuid.uuid4())

    # Launch background task and store reference to prevent GC
    task = asyncio.create_task(
        _generate_image_background(
            session_id=session_id,
            task_id=task_id,
            log_entries=entries,
            characters=char_dict,
            turn_number=turn_number,
            generation_mode="specific",
        )
    )
    active.add(task)
    task.add_done_callback(lambda t: active.discard(t))

    return ImageGenerateAccepted(
        task_id=task_id,
        session_id=session_id,
        turn_number=turn_number,
    )


# =============================================================================
# Best Scene Scanner (Story 17-4)
# =============================================================================


async def _scan_and_generate_best_image(
    session_id: str,
    task_id: str,
    log_entries: list[str],
    characters: dict[str, Any],
) -> None:
    """Background task that scans for the best scene, then generates an image.

    Combines the scanner phase (LLM analysis of full log) with the image
    generation phase (prompt building + Imagen API call) in a single task.

    This function MUST NOT raise exceptions -- all errors are caught
    and broadcast as WebSocket error events.

    Args:
        session_id: Session ID.
        task_id: Unique task identifier for tracking.
        log_entries: Complete ground_truth_log entries.
        characters: Character info dict.
    """
    from image_gen import ImageGenerationError, ImageGenerator

    try:
        generator = ImageGenerator()

        # Phase 1: Scan for best scene
        turn_number, rationale = await generator.scan_best_scene(log_entries)

        logger.info(
            "Best scene scan complete for session %s (task %s): Turn %d - %s",
            session_id,
            task_id,
            turn_number,
            rationale[:150],
        )

        # Phase 2: Extract context window around identified turn (+/-5 entries)
        start = max(0, turn_number - 5)
        end = min(len(log_entries), turn_number + 6)
        context_entries = list(log_entries[start:end])

        # Phase 3: Build scene prompt
        prompt = await generator.build_scene_prompt(context_entries, characters)

        # Phase 4: Generate image
        scene_image = await generator.generate_scene_image(
            prompt=prompt,
            session_id=session_id,
            turn_number=turn_number,
            generation_mode="best",
        )

        # Phase 5: Save metadata as JSON sidecar
        images_dir = get_session_dir(session_id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = images_dir / f"{scene_image.id}.json"
        metadata_path.write_text(
            _json.dumps(scene_image.model_dump(), indent=2),
            encoding="utf-8",
        )

        # Phase 6: Broadcast WebSocket event
        from api.schemas import SceneImageResponse as _SceneImageResponse
        from api.schemas import WsImageReady as _WsImageReady
        from api.websocket import manager

        download_url = _build_download_url(session_id, scene_image.id)
        ws_event = _WsImageReady(
            image=_SceneImageResponse(
                id=scene_image.id,
                session_id=scene_image.session_id,
                turn_number=scene_image.turn_number,
                prompt=scene_image.prompt,
                image_path=scene_image.image_path,
                provider=scene_image.provider,
                model=scene_image.model,
                generation_mode=scene_image.generation_mode,
                generated_at=scene_image.generated_at,
                download_url=download_url,
            ),
        )
        await manager.broadcast(session_id, ws_event.model_dump())

        logger.info(
            "Best scene image generated for session %s turn %d (task %s): %s",
            session_id,
            turn_number,
            task_id,
            scene_image.id,
        )

    except ImageGenerationError as e:
        logger.error(
            "Best scene generation failed for session %s (task %s): %s",
            session_id,
            task_id,
            e,
        )
        from api.websocket import manager

        await manager.broadcast(
            session_id,
            {
                "type": "error",
                "message": f"Best scene generation failed: {e}",
                "recoverable": True,
            },
        )

    except Exception as e:
        logger.exception(
            "Unexpected error in best scene generation background task "
            "(session=%s, task=%s)",
            session_id,
            task_id,
        )
        from api.websocket import manager

        await manager.broadcast(
            session_id,
            {
                "type": "error",
                "message": f"Best scene generation failed unexpectedly: {e}",
                "recoverable": True,
            },
        )


@router.post(
    "/sessions/{session_id}/images/generate-best",
    response_model=BestSceneAccepted,
    status_code=202,
)
async def generate_best_scene_image(
    session_id: str,
) -> BestSceneAccepted:
    """Generate an image of the most visually dramatic scene in the session.

    Uses an LLM scanner to analyze the entire ground_truth_log, identify the
    most visually dramatic scene, and then generate an illustration of it.
    Runs as a background task with WebSocket notification on completion.

    Story 17-4: Best Scene Scanner.

    Args:
        session_id: Session ID string.

    Returns:
        202 Accepted with task ID and scanning status.
    """
    _validate_and_check_session(session_id)
    _check_image_generation_enabled()

    # Guard against too many concurrent image tasks for this session
    active = _active_image_tasks.get(session_id, set())
    # Prune completed tasks
    active = {t for t in active if not t.done()}
    _active_image_tasks[session_id] = active
    if len(active) >= _MAX_CONCURRENT_IMAGE_TASKS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many concurrent image generation requests "
            f"(max {_MAX_CONCURRENT_IMAGE_TASKS}). Please wait for "
            f"current tasks to complete.",
        )

    # Load game state
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is None:
        raise HTTPException(status_code=400, detail="Session has no checkpoints")

    state = load_checkpoint(session_id, latest_turn)
    if state is None:
        raise HTTPException(status_code=500, detail="Failed to load latest checkpoint")

    log = state.get("ground_truth_log", [])
    if not log:
        raise HTTPException(
            status_code=400, detail="Session has no narrative log entries"
        )

    # Extract complete log (entire session history)
    all_entries = list(log)

    characters = state.get("characters", {})
    char_dict = {
        k: v.model_dump() if hasattr(v, "model_dump") else v
        for k, v in characters.items()
    }

    # Merge race/gender from character sheets into char_dict for image prompts
    sheets = state.get("character_sheets", {})
    for name, sheet in sheets.items():
        sheet_data = sheet.model_dump() if hasattr(sheet, "model_dump") else sheet
        if name in char_dict:
            for field in ("race", "gender"):
                if field not in char_dict[name] and field in sheet_data:
                    char_dict[name][field] = sheet_data[field]
        else:
            char_dict[name] = sheet_data

    task_id = str(_uuid.uuid4())

    # Launch background task and store reference to prevent GC
    task = asyncio.create_task(
        _scan_and_generate_best_image(
            session_id=session_id,
            task_id=task_id,
            log_entries=all_entries,
            characters=char_dict,
        )
    )
    active.add(task)
    task.add_done_callback(lambda t: active.discard(t))

    return BestSceneAccepted(
        task_id=task_id,
        session_id=session_id,
    )


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

    def _build_zip() -> bytes:
        """Build zip archive synchronously (run via to_thread)."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            used_names: set[str] = set()
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
                        turn_number = int(data.get("turn_number", 0))
                        raw_mode = data.get("generation_mode", "scene")
                        generation_mode = (
                            raw_mode
                            if raw_mode in _VALID_GENERATION_MODES
                            else "scene"
                        )
                    except (KeyError, ValueError, OSError, TypeError):
                        pass

                # Filename inside the zip: session_turn_N_mode.png
                archive_name = (
                    f"{session_name}_turn_{turn_number + 1}_{generation_mode}.png"
                )
                # Deduplicate: append counter if name already used
                if archive_name in used_names:
                    counter = 2
                    base = f"{session_name}_turn_{turn_number + 1}_{generation_mode}"
                    while f"{base}_{counter}.png" in used_names:
                        counter += 1
                    archive_name = f"{base}_{counter}.png"
                used_names.add(archive_name)
                zf.write(str(png_path), archive_name)

        return buf.getvalue()

    # Offload synchronous zip building to a thread to avoid blocking the
    # event loop for sessions with many images.
    zip_bytes = await asyncio.to_thread(_build_zip)

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"',
        },
    )


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
            turn_number = int(data.get("turn_number", 0))
            raw_mode = data.get("generation_mode", "scene")
            generation_mode = (
                raw_mode if raw_mode in _VALID_GENERATION_MODES else "scene"
            )
        except (KeyError, ValueError, OSError, TypeError):
            pass  # Use defaults

    # Build descriptive filename
    session_name = _get_safe_session_name(session_id)
    filename = f"{session_name}_turn_{turn_number + 1}_{generation_mode}.png"

    return FileResponse(
        str(image_path),
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sessions/{session_id}/images/{image_filename}")
async def serve_session_image(session_id: str, image_filename: str) -> Any:
    """Serve a generated image file.

    Args:
        session_id: Session ID string.
        image_filename: Image filename (e.g., "uuid.png").

    Returns:
        The image file as a FileResponse.
    """
    from fastapi.responses import FileResponse

    _validate_and_check_session(session_id)

    # Validate filename format: UUID.png only
    if not _IMAGE_FILENAME_RE.match(image_filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid image filename format",
        )

    image_path = get_session_dir(session_id) / "images" / image_filename
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(str(image_path), media_type="image/png")
