"""REST API endpoints for the autodungeon API.

Provides session management, configuration, and character listing endpoints.
All endpoints wrap existing backend functions from persistence.py, config.py,
and models.py without modifying them.
"""

from __future__ import annotations

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from api.schemas import (
    CharacterCreateRequest,
    CharacterDetailResponse,
    CharacterResponse,
    CharacterUpdateRequest,
    GameConfigResponse,
    GameConfigUpdateRequest,
    SessionCreateRequest,
    SessionCreateResponse,
    SessionResponse,
)
from config import PROJECT_ROOT, load_character_configs
from models import CharacterConfig, GameConfig
from persistence import (
    _validate_session_id,
    create_new_session,
    delete_session,
    get_latest_checkpoint,
    list_sessions_with_metadata,
    load_checkpoint,
    load_session_metadata,
    save_checkpoint,
)

router = APIRouter(prefix="/api")


# =============================================================================
# Session Endpoints
# =============================================================================


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions() -> list[SessionResponse]:
    """List all sessions sorted by updated_at descending.

    Returns:
        List of session metadata objects.
    """
    try:
        sessions = list_sessions_with_metadata()
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

    # Try loading from latest checkpoint
    latest_turn = get_latest_checkpoint(session_id)
    if latest_turn is not None:
        state = load_checkpoint(session_id, latest_turn)
        if state is not None:
            game_config = state["game_config"]
            return GameConfigResponse(
                combat_mode=game_config.combat_mode,
                max_combat_rounds=game_config.max_combat_rounds,
                summarizer_provider=game_config.summarizer_provider,
                summarizer_model=game_config.summarizer_model,
                extractor_provider=game_config.extractor_provider,
                extractor_model=game_config.extractor_model,
                party_size=game_config.party_size,
                narrative_display_limit=game_config.narrative_display_limit,
            )

    # No checkpoint - return defaults
    defaults = GameConfig()
    return GameConfigResponse(
        combat_mode=defaults.combat_mode,
        max_combat_rounds=defaults.max_combat_rounds,
        summarizer_provider=defaults.summarizer_provider,
        summarizer_model=defaults.summarizer_model,
        extractor_provider=defaults.extractor_provider,
        extractor_model=defaults.extractor_model,
        party_size=defaults.party_size,
        narrative_display_limit=defaults.narrative_display_limit,
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

    # Apply partial updates to game_config
    current_config = state["game_config"]
    update_data = body.model_dump(exclude_none=True)

    # Build new config dict from current + updates
    config_dict = current_config.model_dump()
    config_dict.update(update_data)

    # Validate the merged config through Pydantic
    try:
        new_config = GameConfig(**config_dict)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None

    # Update state and save
    state["game_config"] = new_config
    if latest_turn is None:
        latest_turn = 0
    save_checkpoint(state, session_id, latest_turn)

    return GameConfigResponse(
        combat_mode=new_config.combat_mode,
        max_combat_rounds=new_config.max_combat_rounds,
        summarizer_provider=new_config.summarizer_provider,
        summarizer_model=new_config.summarizer_model,
        extractor_provider=new_config.extractor_provider,
        extractor_model=new_config.extractor_model,
        party_size=new_config.party_size,
        narrative_display_limit=new_config.narrative_display_limit,
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

    # Reject updates to presets
    if _is_preset_character(name):
        raise HTTPException(
            status_code=403,
            detail="Preset characters cannot be modified",
        )

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
