"""Tests for Story 15.9: NPC Profile Visibility in the Frontend.

Backend coverage for:
- `_get_state_snapshot()` widening: combat_state field now appears in the
  snapshot with the full NpcProfile shape (Task 2 / AC #5).
- `GET /api/sessions/{session_id}/npcs/{npc_key}` endpoint: happy path,
  404s, 400 path traversal, case-insensitive lookup, secret exposure,
  redacted-when-no-combat (Task 3 / AC #9, #12, #13).
- `NpcProfileResponse` schema parity with `models.NpcProfile`.
- `[SHEET]:` notification regression (AC #14).
- Pydantic-vs-dict snapshot serialization shape parity.

Mirrors fixture style from tests/test_story_15_7_npc_damage_tracking.py and
tests/test_api.py (Story 16-10).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from agents import _execute_npc_update
from api.engine import GameEngine
from api.main import app
from api.schemas import NpcProfileResponse
from models import (
    AgentMemory,
    CombatState,
    GameConfig,
    NpcProfile,
    SessionMetadata,
    create_initial_game_state,
)
from persistence import save_checkpoint, save_session_metadata

# =============================================================================
# Fixtures (mirror tests/test_api.py + tests/test_story_15_7)
# =============================================================================


@pytest.fixture
def temp_campaigns_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Patch CAMPAIGNS_DIR to a temp directory for test isolation."""
    temp_campaigns = tmp_path / "campaigns"
    temp_campaigns.mkdir()
    with patch("persistence.CAMPAIGNS_DIR", temp_campaigns):
        yield temp_campaigns


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Async HTTP test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_npc(
    name: str = "Goblin 1",
    hp_current: int = 10,
    hp_max: int = 15,
    ac: int = 13,
    personality: str = "Aggressive coward",
    tactics: str = "Flee at 25% HP",
    secret: str = "knows where the prisoner is held",
    conditions: list[str] | None = None,
    initiative_modifier: int = 2,
) -> NpcProfile:
    """Standard NpcProfile fixture for tests."""
    return NpcProfile(
        name=name,
        initiative_modifier=initiative_modifier,
        hp_max=hp_max,
        hp_current=hp_current,
        ac=ac,
        personality=personality,
        tactics=tactics,
        secret=secret,
        conditions=conditions or [],
    )


def _make_combat_state(
    active: bool = True,
    round_number: int = 2,
    npc_profiles: dict[str, NpcProfile] | None = None,
) -> CombatState:
    """Standard CombatState fixture."""
    if npc_profiles is None:
        npc_profiles = {
            "goblin_1": _make_npc(),
            "warg_alpha": _make_npc(
                name="Warg Alpha",
                hp_current=20,
                hp_max=22,
                ac=14,
                conditions=["bleeding"],
            ),
        }
    return CombatState(
        active=active,
        round_number=round_number,
        initiative_order=["dm", "fighter", "dm:goblin_1", "rogue", "dm:warg_alpha"],
        initiative_rolls={
            "fighter": 17,
            "dm:goblin_1": 12,
            "rogue": 14,
            "dm:warg_alpha": 10,
        },
        npc_profiles=npc_profiles,
    )


def _create_test_session(
    campaigns_dir: Path,
    session_id: str = "001",
    session_number: int = 1,
    name: str = "Test Session",
) -> SessionMetadata:
    """Mirror tests/test_api.py::_create_test_session."""
    session_dir = campaigns_dir / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC).isoformat() + "Z"
    metadata = SessionMetadata(
        session_id=session_id,
        session_number=session_number,
        name=name,
        created_at=now,
        updated_at=now,
        character_names=[],
        turn_count=0,
    )
    save_session_metadata(session_id, metadata)
    return metadata


def _create_combat_checkpoint(
    session_id: str = "001",
    turn_number: int = 1,
    combat_state: CombatState | None = None,
    game_config: GameConfig | None = None,
) -> None:
    """Create a checkpoint with an attached combat_state.

    `combat_state=None` defaults to the standard two-NPC fixture so callers
    don't accidentally save an empty CombatState. Pass an explicit empty
    `CombatState()` if you need that.
    """
    state = create_initial_game_state()
    state["session_id"] = session_id
    state["combat_state"] = (
        combat_state if combat_state is not None else _make_combat_state()
    )
    if game_config is not None:
        state["game_config"] = game_config
    save_checkpoint(state, session_id, turn_number, update_metadata=False)


def _make_engine_with_combat(
    combat_state: CombatState | None = None,
    session_id: str = "test-001",
) -> GameEngine:
    """Build a GameEngine with pre-loaded state including combat_state."""
    if combat_state is None:
        combat_state = _make_combat_state()
    eng = GameEngine(session_id=session_id)
    state = create_initial_game_state()
    state["session_id"] = session_id
    state["turn_queue"] = ["dm", "fighter", "rogue"]
    state["current_turn"] = "dm"
    state["agent_memories"] = {
        "dm": AgentMemory(token_limit=8000),
        "fighter": AgentMemory(token_limit=4000),
    }
    state["combat_state"] = combat_state
    eng._state = state
    return eng


# =============================================================================
# Task 2 / AC #5: _get_state_snapshot widening with combat_state
# =============================================================================


class TestStateSnapshotIncludesCombatState:
    """Snapshot exposes combat_state with full NpcProfile shape."""

    def test_snapshot_contains_combat_state_key(self) -> None:
        """AC #5: snapshot dict has top-level `combat_state` key."""
        eng = _make_engine_with_combat()
        snapshot = eng._get_state_snapshot()
        assert "combat_state" in snapshot

    def test_combat_state_has_all_nine_npc_profile_fields(self) -> None:
        """Each NPC entry contains all 9 fields from `NpcProfile`."""
        eng = _make_engine_with_combat()
        snapshot = eng._get_state_snapshot()
        combat = snapshot["combat_state"]
        assert combat is not None
        profile = combat["npc_profiles"]["goblin_1"]
        expected_fields = {
            "name",
            "initiative_modifier",
            "hp_max",
            "hp_current",
            "ac",
            "personality",
            "tactics",
            "secret",
            "conditions",
        }
        assert set(profile.keys()) == expected_fields

    def test_combat_state_npc_profiles_are_dicts(self) -> None:
        """`model_dump()` recurses → nested NpcProfile becomes a plain dict."""
        eng = _make_engine_with_combat()
        snapshot = eng._get_state_snapshot()
        combat = snapshot["combat_state"]
        for key, profile in combat["npc_profiles"].items():
            assert isinstance(profile, dict), f"profile {key} should be a dict"

    def test_combat_state_is_none_when_state_has_none(self) -> None:
        """If `_state['combat_state']` is None, snapshot returns None."""
        eng = _make_engine_with_combat()
        # Explicitly set to None to simulate exploration-only sessions
        assert eng._state is not None
        eng._state["combat_state"] = None  # type: ignore[typeddict-item]
        snapshot = eng._get_state_snapshot()
        assert snapshot["combat_state"] is None

    def test_combat_state_active_false_still_in_snapshot(self) -> None:
        """Even with active=False, combat_state is serialized (UI gates on active flag)."""
        cs = _make_combat_state(active=False)
        eng = _make_engine_with_combat(combat_state=cs)
        snapshot = eng._get_state_snapshot()
        assert snapshot["combat_state"]["active"] is False

    def test_hp_mutation_reflected_in_snapshot(self) -> None:
        """After _execute_npc_update, snapshot shows the new hp_current."""
        eng = _make_engine_with_combat()
        assert eng._state is not None
        original = eng._state["combat_state"]
        assert isinstance(original, CombatState)
        # Apply -3 damage to goblin_1
        _, new_combat = _execute_npc_update(
            {"npc_name": "goblin_1", "hp_change": -3},
            original,
        )
        eng._state["combat_state"] = new_combat
        snapshot = eng._get_state_snapshot()
        assert snapshot["combat_state"]["npc_profiles"]["goblin_1"]["hp_current"] == 7


# =============================================================================
# Task 10.2 / TestCombatStateInSnapshotPydanticDump
# =============================================================================


class TestCombatStateInSnapshotPydanticDump:
    """Snapshot handles both Pydantic CombatState and pre-deserialized dict."""

    def test_pydantic_combat_state_dumps_via_model_dump(self) -> None:
        eng = _make_engine_with_combat()
        snapshot = eng._get_state_snapshot()
        combat = snapshot["combat_state"]
        assert combat["round_number"] == 2
        assert "warg_alpha" in combat["npc_profiles"]

    def test_dict_combat_state_passes_through_unchanged(self) -> None:
        """If state already contains a plain dict, snapshot returns dict copy."""
        eng = _make_engine_with_combat()
        assert eng._state is not None
        # Simulate dict shape (e.g., after a partial deserialization)
        raw_dict = {
            "active": True,
            "round_number": 9,
            "initiative_order": [],
            "initiative_rolls": {},
            "npc_profiles": {
                "imp": {
                    "name": "Imp",
                    "initiative_modifier": 3,
                    "hp_max": 10,
                    "hp_current": 5,
                    "ac": 13,
                    "personality": "",
                    "tactics": "",
                    "secret": "",
                    "conditions": [],
                }
            },
        }
        eng._state["combat_state"] = raw_dict  # type: ignore[typeddict-item]
        snapshot = eng._get_state_snapshot()
        assert snapshot["combat_state"]["round_number"] == 9
        assert snapshot["combat_state"]["npc_profiles"]["imp"]["hp_current"] == 5


# =============================================================================
# Task 10.2 / TestNpcProfileResponseSchema
# =============================================================================


class TestNpcProfileResponseSchema:
    """NpcProfileResponse mirrors models.NpcProfile field-for-field."""

    def test_field_parity_with_npc_profile_model(self) -> None:
        """All NpcProfile fields are present on the response schema."""
        npc_fields = set(NpcProfile.model_fields.keys())
        response_fields = set(NpcProfileResponse.model_fields.keys())
        assert npc_fields == response_fields, (
            f"NpcProfile fields not mirrored in NpcProfileResponse:\n"
            f"  only in NpcProfile: {npc_fields - response_fields}\n"
            f"  only in Response:   {response_fields - npc_fields}"
        )

    def test_roundtrip_serialization(self) -> None:
        """NpcProfile.model_dump() → NpcProfileResponse → .model_dump() is stable."""
        original = _make_npc(
            name="Lich",
            hp_current=180,
            hp_max=200,
            ac=18,
            secret="phylactery hidden in the crypt",
            conditions=["concentrating"],
        )
        as_dict = original.model_dump()
        response = NpcProfileResponse(**as_dict)
        re_dumped = response.model_dump()
        assert re_dumped == as_dict

    def test_secret_field_exposed_on_response(self) -> None:
        """`secret` is intentionally part of the response schema (player visibility)."""
        assert "secret" in NpcProfileResponse.model_fields


# =============================================================================
# Task 3 / TestGetNpcProfileEndpoint
# =============================================================================


class TestGetNpcProfileEndpoint:
    """Tests for GET /api/sessions/{id}/npcs/{npc_key}."""

    @pytest.mark.anyio
    async def test_happy_path_returns_full_profile(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Returns 200 with all 9 NpcProfile fields."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        _create_combat_checkpoint(session_id="001")

        resp = await client.get("/api/sessions/001/npcs/goblin_1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Goblin 1"
        assert data["hp_current"] == 10
        assert data["hp_max"] == 15
        assert data["ac"] == 13
        assert data["personality"] == "Aggressive coward"
        assert data["tactics"] == "Flee at 25% HP"
        assert data["secret"] == "knows where the prisoner is held"
        assert data["conditions"] == []
        assert data["initiative_modifier"] == 2

    @pytest.mark.anyio
    async def test_returns_404_for_unknown_npc(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """AC #12: unknown npc_key returns 404 with clear detail."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        _create_combat_checkpoint(session_id="001")

        resp = await client.get("/api/sessions/001/npcs/nonexistent")
        assert resp.status_code == 404
        assert "nonexistent" in resp.json()["detail"]
        assert "not found" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_returns_404_when_combat_state_default(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """AC #13: a default (never-started) CombatState (active=False, no npcs) → 404."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        # Checkpoint with the default empty CombatState (active=False)
        # — this is the "exploration-only" state shape.
        state = create_initial_game_state()
        state["session_id"] = "001"
        state["combat_state"] = CombatState()
        save_checkpoint(state, "001", 1, update_metadata=False)

        resp = await client.get("/api/sessions/001/npcs/anything")
        assert resp.status_code == 404
        assert "No active combat" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_returns_404_when_combat_inactive(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """AC #13: combat_state.active=False → 404."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        _create_combat_checkpoint(
            session_id="001",
            combat_state=_make_combat_state(active=False),
        )

        resp = await client.get("/api/sessions/001/npcs/goblin_1")
        assert resp.status_code == 404
        assert "No active combat" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_returns_404_when_npc_profiles_empty(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Empty npc_profiles → 404 (no combat)."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        empty_combat = _make_combat_state(active=True, npc_profiles={})
        _create_combat_checkpoint(session_id="001", combat_state=empty_combat)

        resp = await client.get("/api/sessions/001/npcs/anything")
        assert resp.status_code == 404
        assert "No active combat" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_path_traversal_rejected(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """AC: '..' in npc_key returns 400."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        _create_combat_checkpoint(session_id="001")

        resp = await client.get("/api/sessions/001/npcs/..evil")
        assert resp.status_code == 400
        assert "invalid characters" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_null_byte_rejected(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Null byte in npc_key returns 400."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        _create_combat_checkpoint(session_id="001")

        resp = await client.get("/api/sessions/001/npcs/foo%00bar")
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_backslash_rejected(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Backslash in npc_key returns 400."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        _create_combat_checkpoint(session_id="001")

        resp = await client.get("/api/sessions/001/npcs/foo%5Cbar")
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_case_insensitive_lookup(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Lookup matches keys case-insensitively (mirror PC sheet endpoint)."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        _create_combat_checkpoint(session_id="001")

        resp = await client.get("/api/sessions/001/npcs/GOBLIN_1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Goblin 1"

    @pytest.mark.anyio
    async def test_invalid_session_id(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Bad session ID format returns 400."""
        resp = await client.get("/api/sessions/bad!id/npcs/goblin_1")
        assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_nonexistent_session(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Non-existent session returns 404."""
        resp = await client.get("/api/sessions/999/npcs/goblin_1")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_no_checkpoints(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Session exists but has no checkpoints → 404."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        resp = await client.get("/api/sessions/001/npcs/goblin_1")
        assert resp.status_code == 404
        assert "checkpoints" in resp.json()["detail"]

    @pytest.mark.anyio
    async def test_secret_field_exposed_unredacted(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Per approved proposal §6: `secret` is player-visible."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        npc = _make_npc(secret="phylactery hidden in the crypt")
        _create_combat_checkpoint(
            session_id="001",
            combat_state=_make_combat_state(npc_profiles={"goblin_1": npc}),
        )

        resp = await client.get("/api/sessions/001/npcs/goblin_1")
        assert resp.status_code == 200
        assert resp.json()["secret"] == "phylactery hidden in the crypt"

    @pytest.mark.anyio
    async def test_conditions_returned_as_list(
        self, client: AsyncClient, temp_campaigns_dir: Path
    ) -> None:
        """Conditions list is preserved verbatim."""
        _create_test_session(temp_campaigns_dir, session_id="001")
        npc = _make_npc(conditions=["poisoned", "bleeding"])
        _create_combat_checkpoint(
            session_id="001",
            combat_state=_make_combat_state(npc_profiles={"goblin_1": npc}),
        )

        resp = await client.get("/api/sessions/001/npcs/goblin_1")
        assert resp.status_code == 200
        assert resp.json()["conditions"] == ["poisoned", "bleeding"]


# =============================================================================
# Task 10.2 / TestSheetNotificationsRegression (AC #14)
# =============================================================================


class TestSheetNotificationsRegression:
    """AC #14: Story 15-7's [SHEET]: notification emission is untouched."""

    def test_execute_npc_update_still_returns_confirmation(self) -> None:
        """_execute_npc_update returns a confirmation string used by Story 15-7's pipeline."""
        cs = _make_combat_state()
        result, new_cs = _execute_npc_update(
            {"npc_name": "goblin_1", "hp_change": -5},
            cs,
        )
        assert isinstance(result, str)
        assert "Updated" in result or "HP" in result or "goblin" in result.lower()
        # State mutation also confirmed (regression — Story 15-7 behavior preserved)
        assert new_cs.npc_profiles["goblin_1"].hp_current == 5

    def test_execute_npc_update_zero_hp_still_clamps(self) -> None:
        """Over-damage clamps to 0 (defeated) — Story 15-7 contract preserved."""
        cs = _make_combat_state()
        _, new_cs = _execute_npc_update(
            {"npc_name": "goblin_1", "hp_change": -999},
            cs,
        )
        assert new_cs.npc_profiles["goblin_1"].hp_current == 0


# =============================================================================
# Schema field type assertions (defensive)
# =============================================================================


class TestNpcProfileResponseFieldTypes:
    """Type-level guards: response field types match NpcProfile."""

    def test_string_fields(self) -> None:
        """String-typed fields are str on the response."""
        instance = NpcProfileResponse(
            name="Goblin",
            initiative_modifier=2,
            hp_max=10,
            hp_current=10,
            ac=13,
            personality="cowardly",
            tactics="flee",
            secret="hidden",
            conditions=["prone"],
        )
        assert isinstance(instance.name, str)
        assert isinstance(instance.personality, str)
        assert isinstance(instance.tactics, str)
        assert isinstance(instance.secret, str)

    def test_numeric_fields(self) -> None:
        """Int-typed fields are int."""
        instance = NpcProfileResponse(
            name="Goblin",
            initiative_modifier=2,
            hp_max=10,
            hp_current=7,
            ac=13,
        )
        assert isinstance(instance.hp_max, int)
        assert isinstance(instance.hp_current, int)
        assert isinstance(instance.ac, int)
        assert isinstance(instance.initiative_modifier, int)

    def test_conditions_list_default(self) -> None:
        """conditions defaults to empty list."""
        instance = NpcProfileResponse(name="Goblin", hp_max=10, hp_current=10)
        assert instance.conditions == []

    def test_secret_default_empty(self) -> None:
        """secret defaults to empty string."""
        instance = NpcProfileResponse(name="Goblin", hp_max=10, hp_current=10)
        assert instance.secret == ""


# =============================================================================
# anyio backend marker — keeps the file aligned with tests/test_api.py
# =============================================================================


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


