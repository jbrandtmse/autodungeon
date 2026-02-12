"""Tests for the autodungeon FastAPI API layer.

Story 16-1: API Layer Foundation.
Tests all REST endpoints using httpx.AsyncClient with ASGITransport.
Uses tmp_path fixtures for file isolation from real campaign data.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

from api.main import app
from models import (
    GameConfig,
    SessionMetadata,
    create_initial_game_state,
)
from persistence import save_checkpoint, save_session_metadata

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_campaigns_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Patch CAMPAIGNS_DIR to a temp directory for test isolation."""
    temp_campaigns = tmp_path / "campaigns"
    temp_campaigns.mkdir()

    with patch("persistence.CAMPAIGNS_DIR", temp_campaigns):
        yield temp_campaigns


@pytest.fixture
def temp_characters_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Patch PROJECT_ROOT so character configs load from temp directory."""
    # Create the characters directory structure
    chars_dir = tmp_path / "config" / "characters"
    chars_dir.mkdir(parents=True)
    library_dir = chars_dir / "library"
    library_dir.mkdir()

    # Create a preset character
    rogue_data = {
        "name": "Shadowmere",
        "class": "Rogue",
        "personality": "Sardonic wit, trust issues.",
        "color": "#6B8E6B",
        "provider": "claude",
        "model": "claude-3-haiku-20240307",
        "token_limit": 4000,
    }
    (chars_dir / "rogue.yaml").write_text(yaml.safe_dump(rogue_data), encoding="utf-8")

    # Create a DM config (should be excluded from character list)
    dm_data = {
        "name": "Dungeon Master",
        "provider": "gemini",
        "model": "gemini-1.5-flash",
        "token_limit": 8000,
        "color": "#D4A574",
    }
    (chars_dir / "dm.yaml").write_text(yaml.safe_dump(dm_data), encoding="utf-8")

    # Create a library character
    lib_data = {
        "name": "Eden",
        "class": "Warlock",
        "personality": "A mysterious adventurer.",
        "color": "#4B0082",
        "provider": "claude",
        "model": "claude-3-haiku-20240307",
        "token_limit": 4000,
        "abilities": {
            "strength": 8,
            "intelligence": 15,
            "dexterity": 16,
            "charisma": 10,
            "wisdom": 13,
            "constitution": 12,
        },
        "skills": ["History", "Arcana"],
    }
    (library_dir / "eden.yaml").write_text(yaml.safe_dump(lib_data), encoding="utf-8")

    with (
        patch("config.PROJECT_ROOT", tmp_path),
        patch("api.routes.PROJECT_ROOT", tmp_path),
    ):
        yield chars_dir


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


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


def _create_test_checkpoint(
    campaigns_dir: Path,
    session_id: str,
    turn_number: int,
    game_config: GameConfig | None = None,
) -> None:
    """Helper to create a test checkpoint with a game config."""
    state = create_initial_game_state()
    state["session_id"] = session_id
    if game_config:
        state["game_config"] = game_config
    save_checkpoint(state, session_id, turn_number, update_metadata=False)


# =============================================================================
# Health Endpoint Tests
# =============================================================================


class TestHealthEndpoint:
    """Tests for GET / health check."""

    @pytest.mark.anyio
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        """Health endpoint returns status ok and version."""
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "2.0.0-alpha"

    @pytest.mark.anyio
    async def test_health_response_shape(self, client: AsyncClient) -> None:
        """Health response contains exactly the expected keys."""
        resp = await client.get("/")
        data = resp.json()
        assert set(data.keys()) == {"status", "version"}


# =============================================================================
# Session List Endpoint Tests
# =============================================================================


class TestSessionListEndpoint:
    """Tests for GET /api/sessions."""

    @pytest.mark.anyio
    async def test_empty_session_list(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns empty list when no sessions exist."""
        resp = await client.get("/api/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.anyio
    async def test_session_list_with_sessions(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns sessions sorted by updated_at descending."""
        _create_test_session(
            temp_campaigns_dir,
            session_id="001",
            session_number=1,
            name="First Session",
            character_names=["Fighter", "Rogue"],
        )
        _create_test_session(
            temp_campaigns_dir,
            session_id="002",
            session_number=2,
            name="Second Session",
        )

        resp = await client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Both should have expected fields
        for session in data:
            assert "session_id" in session
            assert "session_number" in session
            assert "name" in session
            assert "created_at" in session
            assert "updated_at" in session
            assert "character_names" in session
            assert "turn_count" in session

    @pytest.mark.anyio
    async def test_session_list_response_fields(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Session list items contain correct field values."""
        _create_test_session(
            temp_campaigns_dir,
            session_id="001",
            session_number=1,
            name="My Adventure",
            character_names=["Fighter"],
            turn_count=5,
        )

        resp = await client.get("/api/sessions")
        data = resp.json()
        assert len(data) == 1
        session = data[0]
        assert session["session_id"] == "001"
        assert session["session_number"] == 1
        assert session["name"] == "My Adventure"
        assert session["character_names"] == ["Fighter"]
        assert session["turn_count"] == 5


# =============================================================================
# Session Create Endpoint Tests
# =============================================================================


class TestSessionCreateEndpoint:
    """Tests for POST /api/sessions."""

    @pytest.mark.anyio
    async def test_create_session_with_name(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Creates a session with the provided name."""
        resp = await client.post("/api/sessions", json={"name": "My Adventure"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Adventure"
        assert "session_id" in data
        assert "session_number" in data
        assert data["session_number"] >= 1

    @pytest.mark.anyio
    async def test_create_session_without_name(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Creates a session with auto-generated empty name when no name given."""
        resp = await client.post("/api/sessions", json={})
        assert resp.status_code == 201
        data = resp.json()
        assert "session_id" in data
        assert "session_number" in data
        assert data["name"] == ""

    @pytest.mark.anyio
    async def test_create_session_no_body(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Creates session when no JSON body is sent (content-type omitted)."""
        resp = await client.post("/api/sessions")
        # With Optional body parameter defaulting to None, no body yields 201
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == ""
        assert "session_id" in data

    @pytest.mark.anyio
    async def test_create_multiple_sessions(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Creating multiple sessions increments session numbers."""
        resp1 = await client.post("/api/sessions", json={"name": "First"})
        resp2 = await client.post("/api/sessions", json={"name": "Second"})
        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["session_number"] < resp2.json()["session_number"]

    @pytest.mark.anyio
    async def test_created_session_appears_in_list(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """A newly created session appears in the session list."""
        create_resp = await client.post(
            "/api/sessions", json={"name": "Listed Session"}
        )
        assert create_resp.status_code == 201
        sid = create_resp.json()["session_id"]

        list_resp = await client.get("/api/sessions")
        assert list_resp.status_code == 200
        session_ids = [s["session_id"] for s in list_resp.json()]
        assert sid in session_ids


# =============================================================================
# Session Detail Endpoint Tests
# =============================================================================


class TestSessionDetailEndpoint:
    """Tests for GET /api/sessions/{session_id}."""

    @pytest.mark.anyio
    async def test_get_existing_session(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns session details for an existing session."""
        _create_test_session(
            temp_campaigns_dir,
            session_id="001",
            session_number=1,
            name="Test Session",
            character_names=["Fighter", "Rogue"],
        )

        resp = await client.get("/api/sessions/001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "001"
        assert data["session_number"] == 1
        assert data["name"] == "Test Session"
        assert data["character_names"] == ["Fighter", "Rogue"]

    @pytest.mark.anyio
    async def test_get_nonexistent_session(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns 404 for a non-existent session."""
        resp = await client.get("/api/sessions/999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_get_session_invalid_id(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns 400 for an invalid session ID (special characters)."""
        resp = await client.get("/api/sessions/bad!id")
        assert resp.status_code == 400
        assert "Invalid session ID" in resp.json()["detail"]


# =============================================================================
# Session Delete Endpoint Tests
# =============================================================================


class TestSessionDeleteEndpoint:
    """Tests for DELETE /api/sessions/{session_id}."""

    @pytest.mark.anyio
    async def test_delete_existing_session(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Deleting an existing session returns 204 and removes it."""
        _create_test_session(
            temp_campaigns_dir,
            session_id="001",
            session_number=1,
            name="Doomed Session",
        )

        resp = await client.delete("/api/sessions/001")
        assert resp.status_code == 204
        assert resp.content == b""

        # Verify it no longer appears in the session list
        list_resp = await client.get("/api/sessions")
        assert list_resp.status_code == 200
        assert list_resp.json() == []

    @pytest.mark.anyio
    async def test_delete_nonexistent_session(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Deleting a non-existent session returns 404."""
        resp = await client.delete("/api/sessions/999")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_delete_invalid_session_id(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Deleting with an invalid session ID returns 400."""
        resp = await client.delete("/api/sessions/bad!id")
        assert resp.status_code == 400
        assert "Invalid session ID" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_delete_session_with_checkpoints(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Deleting a session with checkpoints removes everything."""
        _create_test_session(
            temp_campaigns_dir,
            session_id="001",
            session_number=1,
            name="Session with data",
        )
        _create_test_checkpoint(temp_campaigns_dir, "001", 1)
        _create_test_checkpoint(temp_campaigns_dir, "001", 2)

        resp = await client.delete("/api/sessions/001")
        assert resp.status_code == 204

        # Verify session is gone
        get_resp = await client.get("/api/sessions/001")
        assert get_resp.status_code == 404

    @pytest.mark.anyio
    async def test_delete_session_idempotent_check(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Deleting the same session twice returns 404 on the second call."""
        _create_test_session(
            temp_campaigns_dir,
            session_id="001",
            session_number=1,
            name="Once deleted",
        )

        resp1 = await client.delete("/api/sessions/001")
        assert resp1.status_code == 204

        resp2 = await client.delete("/api/sessions/001")
        assert resp2.status_code == 404


# =============================================================================
# Session Config Get Endpoint Tests
# =============================================================================


class TestSessionConfigGetEndpoint:
    """Tests for GET /api/sessions/{session_id}/config."""

    @pytest.mark.anyio
    async def test_get_config_default(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns default config when session has no checkpoints."""
        _create_test_session(temp_campaigns_dir, session_id="001")

        resp = await client.get("/api/sessions/001/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["combat_mode"] == "Narrative"
        assert data["party_size"] == 4
        assert data["narrative_display_limit"] == 50
        assert data["max_combat_rounds"] == 50

    @pytest.mark.anyio
    async def test_get_config_from_checkpoint(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns config from the latest checkpoint."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        custom_config = GameConfig(combat_mode="Tactical", party_size=3)
        _create_test_checkpoint(temp_campaigns_dir, "001", 1, game_config=custom_config)

        resp = await client.get("/api/sessions/001/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["combat_mode"] == "Tactical"
        assert data["party_size"] == 3

    @pytest.mark.anyio
    async def test_get_config_nonexistent_session(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns 404 for a non-existent session."""
        resp = await client.get("/api/sessions/999/config")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_get_config_all_fields_present(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Config response contains all expected fields."""
        _create_test_session(temp_campaigns_dir, session_id="001")

        resp = await client.get("/api/sessions/001/config")
        data = resp.json()
        expected_fields = {
            "combat_mode",
            "max_combat_rounds",
            "summarizer_provider",
            "summarizer_model",
            "extractor_provider",
            "extractor_model",
            "party_size",
            "narrative_display_limit",
        }
        assert set(data.keys()) == expected_fields


# =============================================================================
# Session Config Put Endpoint Tests
# =============================================================================


class TestSessionConfigPutEndpoint:
    """Tests for PUT /api/sessions/{session_id}/config."""

    @pytest.mark.anyio
    async def test_update_config_partial(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Partial update only changes specified fields."""
        _create_test_session(temp_campaigns_dir, session_id="001")

        resp = await client.put(
            "/api/sessions/001/config",
            json={"combat_mode": "Tactical", "party_size": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["combat_mode"] == "Tactical"
        assert data["party_size"] == 3
        # Other fields should remain at defaults
        assert data["narrative_display_limit"] == 50

    @pytest.mark.anyio
    async def test_update_config_persists(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Updated config persists and can be retrieved."""
        _create_test_session(temp_campaigns_dir, session_id="001")

        # Update
        await client.put(
            "/api/sessions/001/config",
            json={"party_size": 6},
        )

        # Retrieve and verify
        resp = await client.get("/api/sessions/001/config")
        assert resp.status_code == 200
        assert resp.json()["party_size"] == 6

    @pytest.mark.anyio
    async def test_update_config_invalid_party_size(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns 422 for invalid party_size."""
        _create_test_session(temp_campaigns_dir, session_id="001")

        resp = await client.put(
            "/api/sessions/001/config",
            json={"party_size": 99},
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_update_config_invalid_combat_mode(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns 422 for invalid combat_mode."""
        _create_test_session(temp_campaigns_dir, session_id="001")

        resp = await client.put(
            "/api/sessions/001/config",
            json={"combat_mode": "InvalidMode"},
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_update_config_nonexistent_session(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns 404 for a non-existent session."""
        resp = await client.put(
            "/api/sessions/999/config",
            json={"party_size": 3},
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_update_config_invalid_session_id(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns 400 for an invalid session ID."""
        resp = await client.put(
            "/api/sessions/bad!id/config",
            json={"party_size": 3},
        )
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_update_config_with_existing_checkpoint(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Updating config when checkpoint exists preserves and updates correctly."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        _create_test_checkpoint(
            temp_campaigns_dir,
            "001",
            1,
            game_config=GameConfig(combat_mode="Narrative", party_size=4),
        )

        resp = await client.put(
            "/api/sessions/001/config",
            json={"party_size": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["party_size"] == 2
        # combat_mode should remain unchanged
        assert data["combat_mode"] == "Narrative"

    @pytest.mark.anyio
    async def test_update_config_invalid_narrative_limit_low(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns 422 for narrative_display_limit below minimum."""
        _create_test_session(temp_campaigns_dir, session_id="001")

        resp = await client.put(
            "/api/sessions/001/config",
            json={"narrative_display_limit": 5},
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_update_config_invalid_narrative_limit_high(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns 422 for narrative_display_limit above maximum."""
        _create_test_session(temp_campaigns_dir, session_id="001")

        resp = await client.put(
            "/api/sessions/001/config",
            json={"narrative_display_limit": 9999},
        )
        assert resp.status_code == 422


# =============================================================================
# Character List Endpoint Tests
# =============================================================================


class TestCharacterListEndpoint:
    """Tests for GET /api/characters."""

    @pytest.mark.anyio
    async def test_list_characters_includes_presets_and_library(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Character list includes both preset and library characters."""
        resp = await client.get("/api/characters")
        assert resp.status_code == 200
        data = resp.json()
        names = [c["name"] for c in data]
        assert "Shadowmere" in names
        assert "Eden" in names

    @pytest.mark.anyio
    async def test_list_characters_excludes_dm(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Character list does not include DM config."""
        resp = await client.get("/api/characters")
        data = resp.json()
        names = [c["name"] for c in data]
        assert "Dungeon Master" not in names

    @pytest.mark.anyio
    async def test_list_characters_source_field(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Characters have correct source field."""
        resp = await client.get("/api/characters")
        data = resp.json()
        by_name = {c["name"]: c for c in data}
        assert by_name["Shadowmere"]["source"] == "preset"
        assert by_name["Eden"]["source"] == "library"

    @pytest.mark.anyio
    async def test_list_characters_response_fields(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Each character has all expected fields."""
        resp = await client.get("/api/characters")
        data = resp.json()
        expected_fields = {
            "name",
            "character_class",
            "personality",
            "color",
            "provider",
            "model",
            "source",
        }
        for char in data:
            assert set(char.keys()) == expected_fields

    @pytest.mark.anyio
    async def test_list_characters_empty(
        self, client: AsyncClient, tmp_path: Path
    ) -> None:
        """Returns empty list when no characters exist."""
        empty_dir = tmp_path / "config" / "characters"
        empty_dir.mkdir(parents=True)
        (empty_dir / "library").mkdir()

        with (
            patch("config.PROJECT_ROOT", tmp_path),
            patch("api.routes.PROJECT_ROOT", tmp_path),
        ):
            resp = await client.get("/api/characters")
            assert resp.status_code == 200
            assert resp.json() == []


# =============================================================================
# Character Detail Endpoint Tests
# =============================================================================


class TestCharacterDetailEndpoint:
    """Tests for GET /api/characters/{name}."""

    @pytest.mark.anyio
    async def test_get_preset_character(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns full details for a preset character."""
        resp = await client.get("/api/characters/shadowmere")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Shadowmere"
        assert data["character_class"] == "Rogue"
        assert data["source"] == "preset"
        assert data["token_limit"] == 4000

    @pytest.mark.anyio
    async def test_get_library_character(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns full details for a library character."""
        resp = await client.get("/api/characters/eden")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Eden"
        assert data["character_class"] == "Warlock"
        assert data["source"] == "library"
        assert data["token_limit"] == 4000

    @pytest.mark.anyio
    async def test_get_character_case_insensitive(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Character lookup is case-insensitive."""
        resp = await client.get("/api/characters/Shadowmere")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Shadowmere"

    @pytest.mark.anyio
    async def test_get_nonexistent_character(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns 404 for a non-existent character."""
        resp = await client.get("/api/characters/nonexistent")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_get_character_detail_fields(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Character detail includes token_limit and backstory fields."""
        resp = await client.get("/api/characters/shadowmere")
        data = resp.json()
        expected_fields = {
            "name",
            "character_class",
            "personality",
            "color",
            "provider",
            "model",
            "source",
            "token_limit",
            "backstory",
        }
        assert set(data.keys()) == expected_fields


# =============================================================================
# CORS Tests
# =============================================================================


class TestCORS:
    """Tests for CORS configuration."""

    @pytest.mark.anyio
    async def test_cors_headers_present(self, client: AsyncClient) -> None:
        """CORS headers are present for allowed origins."""
        resp = await client.get(
            "/",
            headers={"Origin": "http://localhost:5173"},
        )
        assert resp.status_code == 200
        assert (
            resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
        )

    @pytest.mark.anyio
    async def test_cors_sveltekit_dev_origin(self, client: AsyncClient) -> None:
        """SvelteKit dev server origin is allowed."""
        resp = await client.options(
            "/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert resp.status_code == 200
        assert (
            resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
        )

    @pytest.mark.anyio
    async def test_cors_sveltekit_preview_origin(self, client: AsyncClient) -> None:
        """SvelteKit preview server origin is allowed."""
        resp = await client.get(
            "/",
            headers={"Origin": "http://localhost:4173"},
        )
        assert (
            resp.headers.get("access-control-allow-origin") == "http://localhost:4173"
        )

    @pytest.mark.anyio
    async def test_cors_streamlit_origin(self, client: AsyncClient) -> None:
        """Streamlit origin is allowed."""
        resp = await client.get(
            "/",
            headers={"Origin": "http://localhost:8501"},
        )
        assert (
            resp.headers.get("access-control-allow-origin") == "http://localhost:8501"
        )

    @pytest.mark.anyio
    async def test_cors_disallowed_origin(self, client: AsyncClient) -> None:
        """Non-listed origins do not get CORS headers."""
        resp = await client.get(
            "/",
            headers={"Origin": "http://evil.example.com"},
        )
        # Should not have the allow-origin header for disallowed origin
        assert resp.headers.get("access-control-allow-origin") is None

    @pytest.mark.anyio
    async def test_cors_preflight_allows_methods(self, client: AsyncClient) -> None:
        """Preflight allows all methods."""
        resp = await client.options(
            "/api/sessions",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert resp.status_code == 200
        allowed = resp.headers.get("access-control-allow-methods", "")
        # Should contain at minimum POST (or *)
        assert "POST" in allowed or "*" in allowed

    @pytest.mark.anyio
    async def test_cors_credentials_allowed(self, client: AsyncClient) -> None:
        """CORS allows credentials."""
        resp = await client.get(
            "/",
            headers={"Origin": "http://localhost:5173"},
        )
        assert resp.headers.get("access-control-allow-credentials") == "true"


# =============================================================================
# OpenAPI Schema Test
# =============================================================================


class TestOpenAPI:
    """Tests for OpenAPI documentation."""

    @pytest.mark.anyio
    async def test_openapi_schema_available(self, client: AsyncClient) -> None:
        """OpenAPI schema is accessible at /openapi.json."""
        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["info"]["title"] == "autodungeon"
        assert schema["info"]["version"] == "2.0.0-alpha"

    @pytest.mark.anyio
    async def test_openapi_docs_page(self, client: AsyncClient) -> None:
        """Swagger UI docs page is accessible at /docs."""
        resp = await client.get("/docs")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_openapi_paths_defined(self, client: AsyncClient) -> None:
        """OpenAPI schema defines paths for all endpoints."""
        resp = await client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "/" in paths
        assert "/api/sessions" in paths
        assert "/api/sessions/{session_id}" in paths
        assert "/api/sessions/{session_id}/config" in paths
        assert "/api/characters" in paths
        assert "/api/characters/{name}" in paths


# =============================================================================
# Character Creation Endpoint Tests (Story 16-9)
# =============================================================================


class TestCreateCharacterEndpoint:
    """Tests for POST /api/characters."""

    @pytest.mark.anyio
    async def test_create_character_success(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Creates a new library character and returns 201."""
        body = {
            "name": "Gandalf",
            "character_class": "Wizard",
            "personality": "Wise and mysterious",
            "color": "#7B68B8",
            "provider": "gemini",
            "model": "gemini-1.5-flash",
        }
        resp = await client.post("/api/characters", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Gandalf"
        assert data["character_class"] == "Wizard"
        assert data["source"] == "library"
        assert data["token_limit"] == 4000  # default

    @pytest.mark.anyio
    async def test_create_character_file_written(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Character YAML file is created in library directory."""
        body = {
            "name": "Aria",
            "character_class": "Bard",
            "color": "#D4A574",
        }
        resp = await client.post("/api/characters", json=body)
        assert resp.status_code == 201

        # Check file exists
        library_dir = temp_characters_dir / "library"
        yaml_files = list(library_dir.glob("aria*.yaml"))
        assert len(yaml_files) == 1

        # Check file content
        content = yaml.safe_load(yaml_files[0].read_text(encoding="utf-8"))
        assert content["name"] == "Aria"
        assert content["class"] == "Bard"

    @pytest.mark.anyio
    async def test_create_character_name_required(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns 422 when name is missing."""
        body = {"character_class": "Fighter", "color": "#C45C4A"}
        resp = await client.post("/api/characters", json=body)
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_create_character_class_required(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns 422 when class is missing."""
        body = {"name": "Test", "color": "#C45C4A"}
        resp = await client.post("/api/characters", json=body)
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_create_character_duplicate_name(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns 409 when name already exists in library."""
        resp = await client.post(
            "/api/characters",
            json={
                "name": "Eden",
                "character_class": "Warlock",
                "color": "#4B0082",
            },
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_create_character_preset_name_conflict(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns 409 when name conflicts with preset character."""
        resp = await client.post(
            "/api/characters",
            json={
                "name": "Shadowmere",
                "character_class": "Rogue",
                "color": "#6B8E6B",
            },
        )
        assert resp.status_code == 409
        assert "preset" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_create_character_path_traversal(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Rejects names with path traversal patterns."""
        for bad_name in ["../evil", "foo/bar", "test\\hack", "a\x00b"]:
            resp = await client.post(
                "/api/characters",
                json={
                    "name": bad_name,
                    "character_class": "Fighter",
                    "color": "#C45C4A",
                },
            )
            assert resp.status_code == 400, f"Expected 400 for name={bad_name!r}"

    @pytest.mark.anyio
    async def test_create_character_invalid_color(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns 422 for invalid hex color."""
        resp = await client.post(
            "/api/characters",
            json={
                "name": "BadColor",
                "character_class": "Fighter",
                "color": "not-a-color",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_create_character_with_backstory(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Backstory is saved to the YAML file."""
        body = {
            "name": "Lore",
            "character_class": "Cleric",
            "backstory": "A long story...",
            "color": "#4A90A4",
        }
        resp = await client.post("/api/characters", json=body)
        assert resp.status_code == 201

        library_dir = temp_characters_dir / "library"
        yaml_file = list(library_dir.glob("lore*.yaml"))[0]
        content = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        assert content["backstory"] == "A long story..."


# =============================================================================
# Character Update Endpoint Tests (Story 16-9)
# =============================================================================


class TestUpdateCharacterEndpoint:
    """Tests for PUT /api/characters/{name}."""

    @pytest.mark.anyio
    async def test_update_character_success(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Updates a library character's personality."""
        resp = await client.put(
            "/api/characters/eden",
            json={"personality": "Updated personality"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Eden"
        assert data["personality"] == "Updated personality"
        assert data["source"] == "library"

    @pytest.mark.anyio
    async def test_update_character_partial(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Only updates provided fields, preserves others."""
        resp = await client.put(
            "/api/characters/eden",
            json={"color": "#FF0000"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["color"] == "#FF0000"
        assert data["character_class"] == "Warlock"  # unchanged
        assert data["name"] == "Eden"  # unchanged

    @pytest.mark.anyio
    async def test_update_preset_forbidden(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns 403 when trying to update a preset character."""
        resp = await client.put(
            "/api/characters/shadowmere",
            json={"personality": "Hacked"},
        )
        assert resp.status_code == 403
        assert "preset" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_update_nonexistent_character(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns 404 for a character that doesn't exist."""
        resp = await client.put(
            "/api/characters/doesnotexist",
            json={"personality": "New"},
        )
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_update_path_traversal(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Rejects path traversal in name parameter."""
        resp = await client.put(
            "/api/characters/..%2Fevil",
            json={"personality": "Hacked"},
        )
        assert resp.status_code in (400, 404)

    @pytest.mark.anyio
    async def test_update_character_invalid_color(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns 422 for invalid hex color on update."""
        resp = await client.put(
            "/api/characters/eden",
            json={"color": "bad"},
        )
        assert resp.status_code == 422

    @pytest.mark.anyio
    async def test_update_preserves_extra_fields(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Extra YAML fields (abilities, skills) are preserved on update."""
        resp = await client.put(
            "/api/characters/eden",
            json={"personality": "Still mysterious"},
        )
        assert resp.status_code == 200

        # Check the file still has abilities/skills
        library_dir = temp_characters_dir / "library"
        yaml_file = list(library_dir.glob("eden*.yaml"))[0]
        content = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        assert "abilities" in content
        assert "skills" in content


# =============================================================================
# Character Delete Endpoint Tests (Story 16-9)
# =============================================================================


class TestDeleteCharacterEndpoint:
    """Tests for DELETE /api/characters/{name}."""

    @pytest.mark.anyio
    async def test_delete_character_success(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Deletes a library character and returns 204."""
        # Verify Eden exists first
        resp = await client.get("/api/characters/eden")
        assert resp.status_code == 200

        # Delete
        resp = await client.delete("/api/characters/eden")
        assert resp.status_code == 204

        # Verify gone
        resp = await client.get("/api/characters/eden")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_delete_preset_forbidden(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns 403 when trying to delete a preset character."""
        resp = await client.delete("/api/characters/shadowmere")
        assert resp.status_code == 403
        assert "preset" in resp.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_delete_nonexistent_character(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Returns 404 for a character that doesn't exist."""
        resp = await client.delete("/api/characters/doesnotexist")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_delete_path_traversal(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Rejects path traversal in name parameter."""
        resp = await client.delete("/api/characters/..%2Fevil")
        assert resp.status_code in (400, 404)

    @pytest.mark.anyio
    async def test_delete_case_insensitive(
        self, client: AsyncClient, temp_characters_dir: Path
    ) -> None:
        """Delete is case-insensitive."""
        resp = await client.delete("/api/characters/Eden")
        assert resp.status_code == 204
