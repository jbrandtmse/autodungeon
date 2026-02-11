"""Tests for Story 15.1: Combat State Model & Detection.

Tests for NpcProfile, CombatState models, GameState combat_state field,
factory function updates, dm_start_combat/dm_end_combat tools,
and persistence serialization/deserialization.
"""

import json
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from models import (
    CombatState,
    NpcProfile,
    create_initial_game_state,
    populate_game_state,
)
from persistence import (
    deserialize_game_state,
    serialize_game_state,
)
from tools import dm_end_combat, dm_start_combat

# =============================================================================
# TestNpcProfile: Model construction, defaults, validation
# =============================================================================


class TestNpcProfile:
    """Tests for NpcProfile Pydantic model."""

    def test_default_construction(self) -> None:
        """NpcProfile with only required field (name) uses valid defaults."""
        npc = NpcProfile(name="Goblin 1")
        assert npc.name == "Goblin 1"
        assert npc.initiative_modifier == 0
        assert npc.hp_max == 1
        assert npc.hp_current == 1
        assert npc.ac == 10
        assert npc.personality == ""
        assert npc.tactics == ""
        assert npc.secret == ""
        assert npc.conditions == []

    def test_full_construction(self) -> None:
        """NpcProfile with all fields populated."""
        npc = NpcProfile(
            name="Klarg",
            initiative_modifier=3,
            hp_max=27,
            hp_current=27,
            ac=16,
            personality="Brutal, vain",
            tactics="Uses wolf as flanking partner, retreats below 10 HP",
            secret="Knows where Gundren was taken",
            conditions=["enraged"],
        )
        assert npc.name == "Klarg"
        assert npc.initiative_modifier == 3
        assert npc.hp_max == 27
        assert npc.hp_current == 27
        assert npc.ac == 16
        assert npc.personality == "Brutal, vain"
        assert npc.tactics == "Uses wolf as flanking partner, retreats below 10 HP"
        assert npc.secret == "Knows where Gundren was taken"
        assert npc.conditions == ["enraged"]

    def test_hp_current_can_be_zero(self) -> None:
        """hp_current=0 is valid (defeated NPC)."""
        npc = NpcProfile(name="Dead Goblin", hp_current=0)
        assert npc.hp_current == 0

    def test_hp_max_rejects_zero(self) -> None:
        """hp_max must be at least 1."""
        with pytest.raises(ValidationError):
            NpcProfile(name="Invalid", hp_max=0)

    def test_hp_max_rejects_negative(self) -> None:
        """hp_max rejects negative values."""
        with pytest.raises(ValidationError):
            NpcProfile(name="Invalid", hp_max=-1)

    def test_hp_current_rejects_negative(self) -> None:
        """hp_current rejects negative values."""
        with pytest.raises(ValidationError):
            NpcProfile(name="Invalid", hp_current=-1)

    def test_ac_rejects_negative(self) -> None:
        """ac rejects negative values."""
        with pytest.raises(ValidationError):
            NpcProfile(name="Invalid", ac=-1)

    def test_ac_can_be_zero(self) -> None:
        """ac=0 is valid."""
        npc = NpcProfile(name="Unarmored", ac=0)
        assert npc.ac == 0

    def test_name_required(self) -> None:
        """name is a required field."""
        with pytest.raises(ValidationError):
            NpcProfile()  # type: ignore[call-arg]

    def test_name_rejects_empty_string(self) -> None:
        """name must have at least 1 character."""
        with pytest.raises(ValidationError):
            NpcProfile(name="")

    def test_model_dump_round_trip(self) -> None:
        """NpcProfile can be dumped and reconstructed."""
        npc = NpcProfile(
            name="Goblin 1",
            initiative_modifier=2,
            hp_max=7,
            hp_current=5,
            ac=15,
            personality="Cowardly",
            tactics="Uses shortbow from cover",
            conditions=["frightened"],
        )
        data = npc.model_dump()
        restored = NpcProfile(**data)
        assert restored == npc


# =============================================================================
# TestCombatState: Model construction, defaults, nested NpcProfile
# =============================================================================


class TestCombatState:
    """Tests for CombatState Pydantic model."""

    def test_default_construction(self) -> None:
        """CombatState() defaults to inactive combat with empty collections."""
        cs = CombatState()
        assert cs.active is False
        assert cs.round_number == 0
        assert cs.initiative_order == []
        assert cs.initiative_rolls == {}
        assert cs.original_turn_queue == []
        assert cs.npc_profiles == {}

    def test_populated_combat_state(self) -> None:
        """CombatState with all fields populated including NpcProfile."""
        npc1 = NpcProfile(name="Goblin 1", initiative_modifier=2, hp_max=7, ac=15)
        npc2 = NpcProfile(name="Goblin 2", initiative_modifier=2, hp_max=7, ac=15)
        cs = CombatState(
            active=True,
            round_number=3,
            initiative_order=["fighter", "dm:goblin_1", "rogue", "dm:goblin_2"],
            initiative_rolls={
                "fighter": 18,
                "goblin_1": 15,
                "rogue": 12,
                "goblin_2": 8,
            },
            original_turn_queue=["dm", "fighter", "rogue"],
            npc_profiles={"goblin_1": npc1, "goblin_2": npc2},
        )
        assert cs.active is True
        assert cs.round_number == 3
        assert len(cs.initiative_order) == 4
        assert len(cs.npc_profiles) == 2
        assert cs.npc_profiles["goblin_1"].name == "Goblin 1"
        assert cs.npc_profiles["goblin_2"].hp_max == 7

    def test_round_number_rejects_negative(self) -> None:
        """round_number must be >= 0."""
        with pytest.raises(ValidationError):
            CombatState(round_number=-1)

    def test_round_number_zero_valid(self) -> None:
        """round_number=0 is valid (combat not started)."""
        cs = CombatState(round_number=0)
        assert cs.round_number == 0

    def test_model_dump_with_npc_profiles(self) -> None:
        """CombatState with NpcProfile objects can be dumped to dict."""
        npc = NpcProfile(name="Klarg", hp_max=27, ac=16)
        cs = CombatState(active=True, npc_profiles={"klarg": npc})
        data = cs.model_dump()
        assert data["active"] is True
        assert "klarg" in data["npc_profiles"]
        assert data["npc_profiles"]["klarg"]["name"] == "Klarg"

    def test_model_dump_round_trip(self) -> None:
        """CombatState can be dumped and reconstructed with nested NpcProfile."""
        npc = NpcProfile(
            name="Goblin 1",
            initiative_modifier=2,
            hp_max=7,
            hp_current=3,
            ac=15,
            conditions=["prone"],
        )
        cs = CombatState(
            active=True,
            round_number=2,
            initiative_order=["fighter", "dm:goblin_1"],
            initiative_rolls={"fighter": 18, "goblin_1": 12},
            original_turn_queue=["dm", "fighter"],
            npc_profiles={"goblin_1": npc},
        )
        data = cs.model_dump()
        # Reconstruct nested NpcProfile manually (like deserialization does)
        npc_data = data.pop("npc_profiles")
        npc_profiles = {k: NpcProfile(**v) for k, v in npc_data.items()}
        restored = CombatState(**data, npc_profiles=npc_profiles)
        assert restored.active is True
        assert restored.round_number == 2
        assert restored.npc_profiles["goblin_1"].hp_current == 3
        assert restored.npc_profiles["goblin_1"].conditions == ["prone"]


# =============================================================================
# TestGameStateCombatField: TypedDict integration
# =============================================================================


class TestGameStateCombatField:
    """Tests for combat_state field on GameState TypedDict."""

    def test_game_state_accepts_combat_state(self) -> None:
        """GameState TypedDict includes combat_state field."""
        state = create_initial_game_state()
        assert "combat_state" in state
        assert isinstance(state["combat_state"], CombatState)

    def test_game_state_combat_state_default_inactive(self) -> None:
        """Default combat_state is inactive."""
        state = create_initial_game_state()
        cs = state["combat_state"]
        assert cs.active is False
        assert cs.round_number == 0
        assert cs.initiative_order == []
        assert cs.npc_profiles == {}


# =============================================================================
# TestFactoryFunctions: create_initial_game_state, populate_game_state
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory function combat_state inclusion."""

    def test_create_initial_game_state_has_combat_state(self) -> None:
        """create_initial_game_state() includes combat_state=CombatState()."""
        state = create_initial_game_state()
        assert "combat_state" in state
        cs = state["combat_state"]
        assert isinstance(cs, CombatState)
        assert cs.active is False
        assert cs.round_number == 0

    def test_populate_game_state_has_combat_state(self) -> None:
        """populate_game_state() includes combat_state=CombatState()."""
        from models import CharacterConfig, DMConfig

        mock_chars = {
            "fighter": CharacterConfig(
                name="Thorin",
                character_class="Fighter",
                personality="Brave",
                color="#C9A45C",
                provider="gemini",
                model="gemini-1.5-flash",
            ),
        }
        mock_dm = DMConfig(
            name="DM",
            provider="gemini",
            model="gemini-1.5-flash",
        )

        with (
            patch("config.load_character_configs", return_value=mock_chars),
            patch("config.load_dm_config", return_value=mock_dm),
        ):
            state = populate_game_state(include_sample_messages=False)

        assert "combat_state" in state
        cs = state["combat_state"]
        assert isinstance(cs, CombatState)
        assert cs.active is False


# =============================================================================
# TestCombatTools: dm_start_combat, dm_end_combat schema and returns
# =============================================================================


class TestCombatTools:
    """Tests for dm_start_combat and dm_end_combat tool functions."""

    def test_dm_start_combat_exists_and_callable(self) -> None:
        """dm_start_combat is a tool with an invoke method."""
        assert hasattr(dm_start_combat, "invoke")

    def test_dm_start_combat_returns_placeholder_string(self) -> None:
        """dm_start_combat returns placeholder with participant count."""
        result = dm_start_combat.invoke(
            {"participants": [{"name": "Goblin 1"}, {"name": "Goblin 2"}]}
        )
        assert "2" in result
        assert "NPC" in result

    def test_dm_start_combat_single_participant(self) -> None:
        """dm_start_combat with one participant."""
        result = dm_start_combat.invoke(
            {
                "participants": [
                    {"name": "Klarg", "initiative_modifier": 3, "hp": 27, "ac": 16}
                ]
            }
        )
        assert "1" in result
        assert "NPC" in result

    def test_dm_start_combat_empty_participants(self) -> None:
        """dm_start_combat with empty list."""
        result = dm_start_combat.invoke({"participants": []})
        assert "0" in result

    def test_dm_end_combat_exists_and_callable(self) -> None:
        """dm_end_combat is a tool with an invoke method."""
        assert hasattr(dm_end_combat, "invoke")

    def test_dm_end_combat_returns_placeholder_string(self) -> None:
        """dm_end_combat returns confirmation string."""
        result = dm_end_combat.invoke({})
        assert "Combat ended" in result
        assert "exploration" in result.lower() or "Restoring" in result

    def test_dm_start_combat_in_tools_all(self) -> None:
        """dm_start_combat is in tools.__all__ exports."""
        from tools import __all__ as tools_all

        assert "dm_start_combat" in tools_all

    def test_dm_end_combat_in_tools_all(self) -> None:
        """dm_end_combat is in tools.__all__ exports."""
        from tools import __all__ as tools_all

        assert "dm_end_combat" in tools_all


# =============================================================================
# TestPersistence: Serialize/deserialize round-trip, backward compatibility
# =============================================================================


class TestPersistence:
    """Tests for combat_state persistence in serialize/deserialize."""

    def test_serialize_includes_combat_state_key(self) -> None:
        """serialize_game_state includes combat_state in JSON output."""
        state = create_initial_game_state()
        json_str = serialize_game_state(state)
        data = json.loads(json_str)
        assert "combat_state" in data

    def test_serialize_default_combat_state(self) -> None:
        """Default CombatState serializes correctly."""
        state = create_initial_game_state()
        json_str = serialize_game_state(state)
        data = json.loads(json_str)
        cs_data = data["combat_state"]
        assert cs_data["active"] is False
        assert cs_data["round_number"] == 0
        assert cs_data["initiative_order"] == []
        assert cs_data["initiative_rolls"] == {}
        assert cs_data["original_turn_queue"] == []
        assert cs_data["npc_profiles"] == {}

    def test_serialize_active_combat_with_npcs(self) -> None:
        """Non-default CombatState with NPCs serializes correctly."""
        state = create_initial_game_state()
        npc = NpcProfile(
            name="Goblin 1",
            initiative_modifier=2,
            hp_max=7,
            hp_current=5,
            ac=15,
            personality="Cowardly",
            tactics="Uses shortbow",
            conditions=["frightened"],
        )
        state["combat_state"] = CombatState(
            active=True,
            round_number=2,
            initiative_order=["fighter", "dm:goblin_1"],
            initiative_rolls={"fighter": 18, "goblin_1": 12},
            original_turn_queue=["dm", "fighter"],
            npc_profiles={"goblin_1": npc},
        )
        json_str = serialize_game_state(state)
        data = json.loads(json_str)
        cs_data = data["combat_state"]
        assert cs_data["active"] is True
        assert cs_data["round_number"] == 2
        assert "goblin_1" in cs_data["npc_profiles"]
        assert cs_data["npc_profiles"]["goblin_1"]["name"] == "Goblin 1"
        assert cs_data["npc_profiles"]["goblin_1"]["hp_current"] == 5
        assert cs_data["npc_profiles"]["goblin_1"]["conditions"] == ["frightened"]

    def test_deserialize_round_trip(self) -> None:
        """CombatState round-trips through serialize/deserialize."""
        state = create_initial_game_state()
        npc = NpcProfile(
            name="Klarg",
            initiative_modifier=3,
            hp_max=27,
            hp_current=20,
            ac=16,
            personality="Brutal",
            tactics="Retreats below 10 HP",
            secret="Knows prisoner location",
            conditions=["enraged"],
        )
        state["combat_state"] = CombatState(
            active=True,
            round_number=4,
            initiative_order=["fighter", "dm:klarg", "rogue"],
            initiative_rolls={"fighter": 18, "klarg": 15, "rogue": 12},
            original_turn_queue=["dm", "fighter", "rogue"],
            npc_profiles={"klarg": npc},
        )

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        cs = restored["combat_state"]
        assert isinstance(cs, CombatState)
        assert cs.active is True
        assert cs.round_number == 4
        assert cs.initiative_order == ["fighter", "dm:klarg", "rogue"]
        assert cs.initiative_rolls == {"fighter": 18, "klarg": 15, "rogue": 12}
        assert cs.original_turn_queue == ["dm", "fighter", "rogue"]
        assert "klarg" in cs.npc_profiles
        klarg = cs.npc_profiles["klarg"]
        assert isinstance(klarg, NpcProfile)
        assert klarg.name == "Klarg"
        assert klarg.hp_current == 20
        assert klarg.personality == "Brutal"
        assert klarg.secret == "Knows prisoner location"
        assert klarg.conditions == ["enraged"]

    def test_deserialize_backward_compatible_missing_combat_state(self) -> None:
        """Old checkpoints without combat_state deserialize to default CombatState()."""
        state = create_initial_game_state()
        json_str = serialize_game_state(state)
        data = json.loads(json_str)

        # Simulate old checkpoint by removing combat_state key
        del data["combat_state"]
        old_json = json.dumps(data)

        restored = deserialize_game_state(old_json)
        cs = restored["combat_state"]
        assert isinstance(cs, CombatState)
        assert cs.active is False
        assert cs.round_number == 0
        assert cs.initiative_order == []
        assert cs.npc_profiles == {}

    def test_deserialize_reconstructs_nested_npc_profiles(self) -> None:
        """Deserialization properly reconstructs NpcProfile objects from dicts."""
        state = create_initial_game_state()
        npc1 = NpcProfile(name="Goblin 1", hp_max=7, ac=15)
        npc2 = NpcProfile(name="Goblin 2", hp_max=7, ac=15, conditions=["prone"])
        state["combat_state"] = CombatState(
            active=True,
            npc_profiles={"goblin_1": npc1, "goblin_2": npc2},
        )

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        cs = restored["combat_state"]
        assert len(cs.npc_profiles) == 2
        assert isinstance(cs.npc_profiles["goblin_1"], NpcProfile)
        assert isinstance(cs.npc_profiles["goblin_2"], NpcProfile)
        assert cs.npc_profiles["goblin_1"].name == "Goblin 1"
        assert cs.npc_profiles["goblin_2"].conditions == ["prone"]


# =============================================================================
# TestModelExports: __all__ exports
# =============================================================================


class TestModelExports:
    """Tests for model and tool __all__ exports."""

    def test_combat_state_in_models_all(self) -> None:
        """CombatState is exported from models.__all__."""
        from models import __all__ as models_all

        assert "CombatState" in models_all

    def test_npc_profile_in_models_all(self) -> None:
        """NpcProfile is exported from models.__all__."""
        from models import __all__ as models_all

        assert "NpcProfile" in models_all
