"""Tests for Story 8-4: DM Tool Calls for Sheet Updates.

Tests the update_character_sheet tool function and its integration
with the DM agent for updating character sheets during gameplay.

FR63: DM can update character sheets via tool calls
FR64: Equipment changes reflected in character data
FR65: Spell slot tracking via tool calls
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from agents import _execute_sheet_update, create_dm_agent
from models import (
    AgentMemory,
    CharacterConfig,
    CharacterSheet,
    DMConfig,
    EquipmentItem,
    GameConfig,
    GameState,
    Spell,
    SpellSlots,
    Weapon,
)
from tools import (
    _apply_equipment_updates,
    _apply_list_updates,
    apply_character_sheet_update,
    dm_update_character_sheet,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fighter_sheet() -> CharacterSheet:
    """Create a sample Fighter character sheet."""
    return CharacterSheet(
        name="Thorin",
        race="Dwarf",
        character_class="Fighter",
        level=5,
        strength=18,
        dexterity=12,
        constitution=16,
        intelligence=10,
        wisdom=14,
        charisma=8,
        armor_class=18,
        hit_points_max=52,
        hit_points_current=45,
        hit_dice="5d10",
        hit_dice_remaining=5,
        skill_proficiencies=["Athletics", "Intimidation", "Perception"],
        class_features=["Second Wind", "Action Surge", "Extra Attack"],
        weapons=[
            Weapon(
                name="Longsword",
                damage_dice="1d8",
                damage_type="slashing",
                properties=["versatile"],
            ),
        ],
        equipment=[
            EquipmentItem(name="Rope", quantity=1),
            EquipmentItem(name="Torches", quantity=5),
            EquipmentItem(name="Rations", quantity=3),
        ],
        gold=47,
        silver=10,
        copper=5,
    )


@pytest.fixture
def wizard_sheet() -> CharacterSheet:
    """Create a sample Wizard character sheet with spellcasting."""
    return CharacterSheet(
        name="Elara",
        race="Elf",
        character_class="Wizard",
        level=5,
        strength=8,
        dexterity=14,
        constitution=12,
        intelligence=18,
        wisdom=12,
        charisma=10,
        armor_class=12,
        hit_points_max=27,
        hit_points_current=27,
        hit_dice="5d6",
        hit_dice_remaining=5,
        spellcasting_ability="intelligence",
        spell_save_dc=15,
        spell_attack_bonus=7,
        cantrips=["Fire Bolt", "Mage Hand"],
        spell_slots={
            1: SpellSlots(current=4, max=4),
            2: SpellSlots(current=3, max=3),
            3: SpellSlots(current=2, max=2),
        },
        spells_known=[
            Spell(
                name="Magic Missile",
                level=1,
                school="evocation",
                casting_time="1 action",
                range="120 feet",
                description="Auto-hit force damage",
            ),
        ],
        equipment=[
            EquipmentItem(name="Spellbook", quantity=1),
        ],
        gold=120,
    )


# =============================================================================
# _apply_list_updates Tests
# =============================================================================


class TestApplyListUpdates:
    """Tests for _apply_list_updates helper."""

    def test_add_item_with_plus_prefix(self) -> None:
        result = _apply_list_updates(["poisoned"], ["+exhausted"])
        assert result == ["poisoned", "exhausted"]

    def test_add_item_without_prefix(self) -> None:
        result = _apply_list_updates([], ["poisoned"])
        assert result == ["poisoned"]

    def test_remove_item_with_minus_prefix(self) -> None:
        result = _apply_list_updates(["poisoned", "exhausted"], ["-poisoned"])
        assert result == ["exhausted"]

    def test_remove_case_insensitive(self) -> None:
        result = _apply_list_updates(["Poisoned"], ["-poisoned"])
        assert result == []

    def test_remove_nonexistent_no_error(self) -> None:
        result = _apply_list_updates(["poisoned"], ["-blinded"])
        assert result == ["poisoned"]

    def test_empty_updates(self) -> None:
        result = _apply_list_updates(["a", "b"], [])
        assert result == ["a", "b"]

    def test_empty_string_in_updates_skipped(self) -> None:
        result = _apply_list_updates(["a"], ["", " "])
        assert result == ["a"]

    def test_add_and_remove_mixed(self) -> None:
        result = _apply_list_updates(["poisoned"], ["-poisoned", "+stunned"])
        assert result == ["stunned"]

    def test_does_not_mutate_original(self) -> None:
        original = ["poisoned"]
        _apply_list_updates(original, ["+exhausted"])
        assert original == ["poisoned"]

    def test_no_duplicate_add(self) -> None:
        result = _apply_list_updates(["poisoned"], ["+poisoned"])
        assert result == ["poisoned"]

    def test_no_duplicate_add_case_insensitive(self) -> None:
        result = _apply_list_updates(["Poisoned"], ["+poisoned"])
        assert result == ["Poisoned"]


# =============================================================================
# _apply_equipment_updates Tests
# =============================================================================


class TestApplyEquipmentUpdates:
    """Tests for _apply_equipment_updates helper."""

    def test_add_equipment(self) -> None:
        result = _apply_equipment_updates([], ["+Potion of Healing"])
        assert len(result) == 1
        assert result[0].name == "Potion of Healing"

    def test_remove_equipment(self) -> None:
        items = [EquipmentItem(name="Rope"), EquipmentItem(name="Torch")]
        result = _apply_equipment_updates(items, ["-Rope"])
        assert len(result) == 1
        assert result[0].name == "Torch"

    def test_remove_case_insensitive(self) -> None:
        items = [EquipmentItem(name="Rope")]
        result = _apply_equipment_updates(items, ["-rope"])
        assert result == []

    def test_add_without_prefix(self) -> None:
        result = _apply_equipment_updates([], ["Lockpick"])
        assert len(result) == 1
        assert result[0].name == "Lockpick"

    def test_does_not_mutate_original(self) -> None:
        original = [EquipmentItem(name="Rope")]
        _apply_equipment_updates(original, ["+Torch"])
        assert len(original) == 1

    def test_no_duplicate_equipment_add(self) -> None:
        items = [EquipmentItem(name="Rope")]
        result = _apply_equipment_updates(items, ["+Rope"])
        assert len(result) == 1

    def test_no_duplicate_equipment_case_insensitive(self) -> None:
        items = [EquipmentItem(name="Rope")]
        result = _apply_equipment_updates(items, ["+rope"])
        assert len(result) == 1


# =============================================================================
# apply_character_sheet_update Tests - HP
# =============================================================================


class TestApplySheetUpdateHP:
    """Tests for HP updates."""

    def test_take_damage(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 35}
        )
        assert updated.hit_points_current == 35
        assert "HP: 45 -> 35 (-10)" in msg

    def test_heal(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 52}
        )
        assert updated.hit_points_current == 52
        assert "+7" in msg

    def test_hp_clamped_to_max(self, fighter_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 999}
        )
        assert updated.hit_points_current == 52  # max HP

    def test_hp_clamped_to_zero(self, fighter_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": -10}
        )
        assert updated.hit_points_current == 0

    def test_hp_unchanged(self, fighter_sheet: CharacterSheet) -> None:
        _, msg = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 45}
        )
        assert "unchanged" in msg

    def test_hp_invalid_type_raises(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="integer"):
            apply_character_sheet_update(
                fighter_sheet, {"hit_points_current": "full"}
            )

    def test_hp_bool_rejected(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="integer"):
            apply_character_sheet_update(
                fighter_sheet, {"hit_points_current": True}
            )

    def test_hp_with_temp_hp_clamped_to_max_plus_temp(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        fighter_sheet.hit_points_temp = 10
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 100}
        )
        # max is 52 + 10 temp = 62
        assert updated.hit_points_current == 62


class TestApplySheetUpdateTempHP:
    """Tests for temporary HP updates."""

    def test_set_temp_hp(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"hit_points_temp": 15}
        )
        assert updated.hit_points_temp == 15
        assert "Temp HP: 0 -> 15" in msg

    def test_temp_hp_clamped_to_zero(self, fighter_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"hit_points_temp": -5}
        )
        assert updated.hit_points_temp == 0


# =============================================================================
# apply_character_sheet_update Tests - Conditions
# =============================================================================


class TestApplySheetUpdateConditions:
    """Tests for condition updates."""

    def test_add_condition(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"conditions": ["+poisoned"]}
        )
        assert "poisoned" in updated.conditions
        assert "added poisoned" in msg

    def test_remove_condition(self, fighter_sheet: CharacterSheet) -> None:
        fighter_sheet.conditions = ["poisoned", "exhausted"]
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"conditions": ["-poisoned"]}
        )
        assert "poisoned" not in updated.conditions
        assert "exhausted" in updated.conditions
        assert "removed poisoned" in msg

    def test_add_and_remove_conditions(self, fighter_sheet: CharacterSheet) -> None:
        fighter_sheet.conditions = ["poisoned"]
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"conditions": ["-poisoned", "+stunned"]}
        )
        assert updated.conditions == ["stunned"]

    def test_conditions_invalid_type_raises(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="list"):
            apply_character_sheet_update(fighter_sheet, {"conditions": "poisoned"})


# =============================================================================
# apply_character_sheet_update Tests - Equipment
# =============================================================================


class TestApplySheetUpdateEquipment:
    """Tests for equipment updates."""

    def test_add_equipment(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"equipment": ["+Potion of Healing"]}
        )
        names = [e.name for e in updated.equipment]
        assert "Potion of Healing" in names
        assert "gained Potion of Healing" in msg

    def test_remove_equipment(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"equipment": ["-Rope"]}
        )
        names = [e.name for e in updated.equipment]
        assert "Rope" not in names
        assert "lost Rope" in msg

    def test_equipment_invalid_type_raises(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="list"):
            apply_character_sheet_update(fighter_sheet, {"equipment": "sword"})


# =============================================================================
# apply_character_sheet_update Tests - Currency
# =============================================================================


class TestApplySheetUpdateCurrency:
    """Tests for currency updates."""

    def test_set_gold(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(fighter_sheet, {"gold": 100})
        assert updated.gold == 100
        assert "Gold: 47 -> 100 (+53)" in msg

    def test_lose_gold(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(fighter_sheet, {"gold": 10})
        assert updated.gold == 10
        assert "(-37)" in msg

    def test_gold_clamped_to_zero(self, fighter_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(fighter_sheet, {"gold": -50})
        assert updated.gold == 0

    def test_set_silver(self, fighter_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(fighter_sheet, {"silver": 25})
        assert updated.silver == 25

    def test_set_copper(self, fighter_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(fighter_sheet, {"copper": 50})
        assert updated.copper == 50

    def test_currency_invalid_type(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="integer"):
            apply_character_sheet_update(fighter_sheet, {"gold": "lots"})

    def test_currency_bool_rejected(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="integer"):
            apply_character_sheet_update(fighter_sheet, {"gold": False})


# =============================================================================
# apply_character_sheet_update Tests - Spell Slots
# =============================================================================


class TestApplySheetUpdateSpellSlots:
    """Tests for spell slot updates."""

    def test_use_spell_slot(self, wizard_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            wizard_sheet, {"spell_slots": {"1": {"current": 3}}}
        )
        assert updated.spell_slots[1].current == 3
        assert updated.spell_slots[1].max == 4
        assert "L1: 4/4 -> 3/4" in msg

    def test_use_multiple_slot_levels(self, wizard_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            wizard_sheet,
            {"spell_slots": {"1": {"current": 2}, "3": {"current": 1}}},
        )
        assert updated.spell_slots[1].current == 2
        assert updated.spell_slots[3].current == 1
        assert "L1:" in msg
        assert "L3:" in msg

    def test_slot_clamped_to_max(self, wizard_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(
            wizard_sheet, {"spell_slots": {"1": {"current": 99}}}
        )
        assert updated.spell_slots[1].current == 4  # max is 4

    def test_slot_clamped_to_zero(self, wizard_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(
            wizard_sheet, {"spell_slots": {"1": {"current": -1}}}
        )
        assert updated.spell_slots[1].current == 0

    def test_invalid_spell_level_raises(self, wizard_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="No spell slot at level 9"):
            apply_character_sheet_update(
                wizard_sheet, {"spell_slots": {"9": {"current": 0}}}
            )

    def test_missing_current_key_raises(self, wizard_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="'current' key"):
            apply_character_sheet_update(
                wizard_sheet, {"spell_slots": {"1": {"max": 5}}}
            )

    def test_spell_slots_invalid_type_raises(self, wizard_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="dict"):
            apply_character_sheet_update(wizard_sheet, {"spell_slots": "none"})


# =============================================================================
# apply_character_sheet_update Tests - XP
# =============================================================================


class TestApplySheetUpdateXP:
    """Tests for experience point updates."""

    def test_set_xp(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"experience_points": 6500}
        )
        assert updated.experience_points == 6500
        assert "XP: 0 -> 6500" in msg

    def test_xp_clamped_to_zero(self, fighter_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"experience_points": -100}
        )
        assert updated.experience_points == 0


# =============================================================================
# apply_character_sheet_update Tests - General
# =============================================================================


class TestApplySheetUpdateGeneral:
    """General tests for apply_character_sheet_update."""

    def test_unsupported_field_raises(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="Unsupported"):
            apply_character_sheet_update(fighter_sheet, {"name": "NewName"})

    def test_empty_updates_no_changes(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(fighter_sheet, {})
        assert updated.hit_points_current == fighter_sheet.hit_points_current
        assert "No changes" in msg

    def test_multiple_updates_at_once(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            fighter_sheet,
            {
                "hit_points_current": 35,
                "gold": 100,
                "conditions": ["+poisoned"],
            },
        )
        assert updated.hit_points_current == 35
        assert updated.gold == 100
        assert "poisoned" in updated.conditions
        assert "Thorin" in msg

    def test_original_sheet_not_mutated(self, fighter_sheet: CharacterSheet) -> None:
        original_hp = fighter_sheet.hit_points_current
        apply_character_sheet_update(fighter_sheet, {"hit_points_current": 10})
        assert fighter_sheet.hit_points_current == original_hp

    def test_confirmation_includes_character_name(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        _, msg = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 40}
        )
        assert "Thorin" in msg


# =============================================================================
# _execute_sheet_update Tests
# =============================================================================


class TestExecuteSheetUpdate:
    """Tests for _execute_sheet_update integration function."""

    def test_successful_update(self, fighter_sheet: CharacterSheet) -> None:
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "Thorin", "updates": '{"hit_points_current": 35}'},
            sheets,
        )
        assert "Updated Thorin" in result
        assert sheets["Thorin"].hit_points_current == 35

    def test_missing_character_name(self, fighter_sheet: CharacterSheet) -> None:
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update({"character_name": "", "updates": "{}"}, sheets)
        assert "Error" in result

    def test_character_not_found(self, fighter_sheet: CharacterSheet) -> None:
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "Unknown", "updates": '{"gold": 100}'},
            sheets,
        )
        assert "Error" in result
        assert "Unknown" in result
        assert "Thorin" in result  # Shows available characters

    def test_invalid_json_updates(self, fighter_sheet: CharacterSheet) -> None:
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "Thorin", "updates": "not json"},
            sheets,
        )
        assert "Error" in result
        assert "JSON" in result

    def test_dict_updates_supported(self, fighter_sheet: CharacterSheet) -> None:
        """Test that dict updates work (when LLM passes dict instead of string)."""
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "Thorin", "updates": {"gold": 100}},
            sheets,
        )
        assert "Updated Thorin" in result
        assert sheets["Thorin"].gold == 100

    def test_invalid_field_returns_error(self, fighter_sheet: CharacterSheet) -> None:
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "Thorin", "updates": '{"name": "NewName"}'},
            sheets,
        )
        assert "Error" in result

    def test_sheets_updated_in_place(
        self, fighter_sheet: CharacterSheet, wizard_sheet: CharacterSheet
    ) -> None:
        sheets = {"Thorin": fighter_sheet, "Elara": wizard_sheet}
        _execute_sheet_update(
            {"character_name": "Thorin", "updates": '{"hit_points_current": 10}'},
            sheets,
        )
        assert sheets["Thorin"].hit_points_current == 10
        assert sheets["Elara"].hit_points_current == 27  # Unchanged

    def test_empty_sheets_dict(self) -> None:
        sheets: dict[str, CharacterSheet] = {}
        result = _execute_sheet_update(
            {"character_name": "Nobody", "updates": '{"gold": 100}'},
            sheets,
        )
        assert "Error" in result
        assert "none" in result

    def test_none_character_name(self, fighter_sheet: CharacterSheet) -> None:
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": None, "updates": '{"gold": 100}'},
            sheets,
        )
        assert "Error" in result


# =============================================================================
# dm_update_character_sheet Tool Tests
# =============================================================================


class TestDmUpdateCharacterSheetTool:
    """Tests for the dm_update_character_sheet LangChain tool."""

    def test_tool_is_invocable(self) -> None:
        assert hasattr(dm_update_character_sheet, "invoke")

    def test_tool_has_name(self) -> None:
        assert dm_update_character_sheet.name == "dm_update_character_sheet"

    def test_tool_in_exports(self) -> None:
        from tools import __all__

        assert "dm_update_character_sheet" in __all__
        assert "apply_character_sheet_update" in __all__


# =============================================================================
# DM Agent Integration Tests
# =============================================================================


class TestDMAgentToolBinding:
    """Tests for DM agent tool binding."""

    @patch("agents.get_llm")
    def test_dm_agent_has_sheet_update_tool(self, mock_get_llm: MagicMock) -> None:
        """Test DM agent is created with sheet update tool bound."""
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_get_llm.return_value = mock_model

        config = DMConfig(
            name="DM",
            provider="gemini",
            model="gemini-1.5-flash",
            token_limit=8000,
            color="#D4A574",
        )
        create_dm_agent(config)

        # Check that bind_tools was called with both tools
        call_args = mock_model.bind_tools.call_args
        tools = call_args[0][0]
        tool_names = [t.name for t in tools]
        assert "dm_roll_dice" in tool_names
        assert "dm_update_character_sheet" in tool_names


# =============================================================================
# dm_turn Integration Test
# =============================================================================


class TestDmTurnSheetUpdateIntegration:
    """End-to-end integration test for sheet updates through dm_turn."""

    @patch("agents.get_llm")
    def test_dm_turn_processes_sheet_update_tool_call(
        self, mock_get_llm: MagicMock, fighter_sheet: CharacterSheet
    ) -> None:
        """Test dm_turn handles sheet update tool calls and propagates changes."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn
        from models import AgentMemory, GameConfig

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter"],
            "current_turn": "dm",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(provider="gemini", model="gemini-1.5-flash"),
            "characters": {"Thorin": CharacterConfig(
                name="Thorin",
                character_class="Fighter",
                race="Dwarf",
                personality="Brave warrior",
                color="#FF0000",
                provider="gemini",
                model="gemini-1.5-flash",
            )},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "character_sheets": {"Thorin": fighter_sheet},
        }

        # First invoke returns tool call, second returns narrative
        tool_call_response = AIMessage(
            content="",
            tool_calls=[{
                "name": "dm_update_character_sheet",
                "args": {
                    "character_name": "Thorin",
                    "updates": {"hit_points_current": 35},
                },
                "id": "call_001",
            }],
        )
        final_response = AIMessage(
            content="The goblin strikes Thorin for 10 damage!",
        )

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = [tool_call_response, final_response]
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        assert result["character_sheets"]["Thorin"].hit_points_current == 35
        assert "[DM]: The goblin strikes Thorin" in result["ground_truth_log"][-1]


# =============================================================================
# Extended _apply_list_updates Edge Cases
# =============================================================================


class TestApplyListUpdatesExtended:
    """Extended edge case tests for _apply_list_updates."""

    def test_add_then_remove_same_item_in_one_call(self) -> None:
        """Adding then immediately removing should result in item absent."""
        result = _apply_list_updates([], ["+poisoned", "-poisoned"])
        assert result == []

    def test_remove_then_add_same_item_in_one_call(self) -> None:
        """Removing then adding should result in item present."""
        result = _apply_list_updates(["poisoned"], ["-poisoned", "+poisoned"])
        assert result == ["poisoned"]

    def test_add_same_item_multiple_times(self) -> None:
        """Adding duplicates should not create duplicates."""
        result = _apply_list_updates([], ["+poisoned", "+poisoned", "+poisoned"])
        assert result == ["poisoned"]

    def test_remove_from_empty_list(self) -> None:
        """Removing from an empty list should not error."""
        result = _apply_list_updates([], ["-poisoned"])
        assert result == []

    def test_add_with_only_whitespace_prefix(self) -> None:
        """Whitespace-only items should be skipped."""
        result = _apply_list_updates([], ["  ", "\t", "  \n  "])
        assert result == []

    def test_add_item_with_plus_and_whitespace(self) -> None:
        """Items like '+ stunned' (space after +) should work."""
        result = _apply_list_updates([], ["+ stunned"])
        assert result == ["stunned"]

    def test_remove_item_with_minus_and_whitespace(self) -> None:
        """Items like '- poisoned' (space after -) should work."""
        result = _apply_list_updates(["poisoned"], ["- poisoned"])
        assert result == []

    def test_many_items_add_and_remove(self) -> None:
        """Test a large batch of add/remove operations."""
        updates = [f"+item_{i}" for i in range(20)]
        result = _apply_list_updates([], updates)
        assert len(result) == 20
        # Now remove every other one
        removals = [f"-item_{i}" for i in range(0, 20, 2)]
        result = _apply_list_updates(result, removals)
        assert len(result) == 10

    def test_remove_only_first_match(self) -> None:
        """If there are manual duplicates in the list, only the first is removed."""
        # Manually construct a list with duplicates
        result = _apply_list_updates(["poisoned", "poisoned"], ["-poisoned"])
        assert result == ["poisoned"]

    def test_add_item_with_special_characters(self) -> None:
        """Items with special chars like parentheses should work."""
        result = _apply_list_updates([], ["+Exhaustion (Level 2)"])
        assert result == ["Exhaustion (Level 2)"]

    def test_remove_item_with_special_characters(self) -> None:
        result = _apply_list_updates(
            ["Exhaustion (Level 2)"], ["-Exhaustion (Level 2)"]
        )
        assert result == []


# =============================================================================
# Extended _apply_equipment_updates Edge Cases
# =============================================================================


class TestApplyEquipmentUpdatesExtended:
    """Extended edge case tests for _apply_equipment_updates."""

    def test_add_equipment_with_special_characters(self) -> None:
        """Equipment names with apostrophes and commas."""
        result = _apply_equipment_updates([], ["+Dragon's Tooth"])
        assert len(result) == 1
        assert result[0].name == "Dragon's Tooth"

    def test_add_equipment_with_parentheses(self) -> None:
        result = _apply_equipment_updates([], ["+Rope (50 feet)"])
        assert result[0].name == "Rope (50 feet)"

    def test_add_equipment_with_numbers(self) -> None:
        result = _apply_equipment_updates([], ["+Potion x3"])
        assert result[0].name == "Potion x3"

    def test_remove_equipment_with_special_characters(self) -> None:
        items = [EquipmentItem(name="Dragon's Tooth")]
        result = _apply_equipment_updates(items, ["-Dragon's Tooth"])
        assert result == []

    def test_add_many_equipment_items(self) -> None:
        """Add a large batch of equipment items."""
        updates = [f"+Item_{i}" for i in range(50)]
        result = _apply_equipment_updates([], updates)
        assert len(result) == 50

    def test_add_then_remove_same_equipment(self) -> None:
        result = _apply_equipment_updates([], ["+Torch", "-Torch"])
        assert result == []

    def test_remove_then_add_same_equipment(self) -> None:
        items = [EquipmentItem(name="Torch")]
        result = _apply_equipment_updates(items, ["-Torch", "+Torch"])
        assert len(result) == 1
        assert result[0].name == "Torch"

    def test_empty_string_in_equipment_updates(self) -> None:
        result = _apply_equipment_updates([], ["", "  ", "+Rope"])
        assert len(result) == 1
        assert result[0].name == "Rope"

    def test_does_not_add_duplicate_without_prefix(self) -> None:
        items = [EquipmentItem(name="Rope")]
        result = _apply_equipment_updates(items, ["Rope"])
        assert len(result) == 1

    def test_whitespace_only_items_skipped(self) -> None:
        result = _apply_equipment_updates([], ["   ", "\t"])
        assert result == []

    def test_equipment_with_unicode(self) -> None:
        result = _apply_equipment_updates([], ["+Staff of Cha\u00f1a"])
        assert len(result) == 1
        assert result[0].name == "Staff of Cha\u00f1a"

    def test_add_equipment_with_plus_in_name(self) -> None:
        """Equipment like '+1 Longsword' starts with + which is the add prefix."""
        result = _apply_equipment_updates([], ["++1 Longsword"])
        assert len(result) == 1
        assert result[0].name == "+1 Longsword"


# =============================================================================
# Extended HP / Temp HP Boundary Tests
# =============================================================================


class TestApplySheetUpdateHPBoundary:
    """Boundary condition tests for HP clamping with temp HP."""

    def test_hp_exact_max(self, fighter_sheet: CharacterSheet) -> None:
        """Setting HP to exact max should work without clamping."""
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 52}
        )
        assert updated.hit_points_current == 52

    def test_hp_one_over_max(self, fighter_sheet: CharacterSheet) -> None:
        """Setting HP to max+1 should clamp to max."""
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 53}
        )
        assert updated.hit_points_current == 52

    def test_hp_zero(self, fighter_sheet: CharacterSheet) -> None:
        """Setting HP to exactly 0."""
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 0}
        )
        assert updated.hit_points_current == 0
        assert "HP:" in msg

    def test_hp_negative_one_clamps_to_zero(self, fighter_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": -1}
        )
        assert updated.hit_points_current == 0

    def test_temp_hp_changes_effective_max(self, fighter_sheet: CharacterSheet) -> None:
        """With temp HP=10, effective max is 62, so 55 should stay 55."""
        fighter_sheet.hit_points_temp = 10
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 55}
        )
        assert updated.hit_points_current == 55

    def test_temp_hp_exact_effective_max(self, fighter_sheet: CharacterSheet) -> None:
        """Setting HP to exact effective max (max + temp)."""
        fighter_sheet.hit_points_temp = 10
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 62}
        )
        assert updated.hit_points_current == 62

    def test_temp_hp_over_effective_max(self, fighter_sheet: CharacterSheet) -> None:
        """Over effective max should clamp to max + temp."""
        fighter_sheet.hit_points_temp = 10
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 63}
        )
        assert updated.hit_points_current == 62

    def test_temp_hp_zero_does_not_change_max(self, fighter_sheet: CharacterSheet) -> None:
        """With temp HP 0, max stays at hit_points_max."""
        fighter_sheet.hit_points_temp = 0
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 100}
        )
        assert updated.hit_points_current == 52

    def test_very_large_hp(self, fighter_sheet: CharacterSheet) -> None:
        """Very large HP value should clamp to max."""
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": 999999}
        )
        assert updated.hit_points_current == 52

    def test_very_negative_hp(self, fighter_sheet: CharacterSheet) -> None:
        """Very negative HP value should clamp to 0."""
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"hit_points_current": -999999}
        )
        assert updated.hit_points_current == 0

    def test_temp_hp_large_value(self, fighter_sheet: CharacterSheet) -> None:
        """Setting temp HP to a large value should be accepted as-is (no upper clamp)."""
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"hit_points_temp": 1000}
        )
        assert updated.hit_points_temp == 1000
        assert "Temp HP: 0 -> 1000" in msg

    def test_temp_hp_bool_rejected(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="integer"):
            apply_character_sheet_update(
                fighter_sheet, {"hit_points_temp": True}
            )

    def test_hp_float_rejected(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="integer"):
            apply_character_sheet_update(
                fighter_sheet, {"hit_points_current": 30.5}
            )

    def test_temp_hp_float_rejected(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="integer"):
            apply_character_sheet_update(
                fighter_sheet, {"hit_points_temp": 5.5}
            )


# =============================================================================
# Extended Spell Slot Edge Cases
# =============================================================================


class TestApplySheetUpdateSpellSlotsExtended:
    """Extended edge case tests for spell slot updates."""

    def test_non_numeric_level_key_raises(self, wizard_sheet: CharacterSheet) -> None:
        """A level key like 'cantrip' that cannot be parsed as int."""
        with pytest.raises(ValueError):
            apply_character_sheet_update(
                wizard_sheet, {"spell_slots": {"cantrip": {"current": 0}}}
            )

    def test_float_level_key_raises(self, wizard_sheet: CharacterSheet) -> None:
        """A level key like '1.5' that is not a valid level."""
        with pytest.raises(ValueError):
            apply_character_sheet_update(
                wizard_sheet, {"spell_slots": {"1.5": {"current": 0}}}
            )

    def test_empty_string_level_key_raises(self, wizard_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError):
            apply_character_sheet_update(
                wizard_sheet, {"spell_slots": {"": {"current": 0}}}
            )

    def test_slot_current_bool_rejected(self, wizard_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="int"):
            apply_character_sheet_update(
                wizard_sheet, {"spell_slots": {"1": {"current": True}}}
            )

    def test_slot_current_string_rejected(self, wizard_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="int"):
            apply_character_sheet_update(
                wizard_sheet, {"spell_slots": {"1": {"current": "full"}}}
            )

    def test_slot_update_without_dict_raises(self, wizard_sheet: CharacterSheet) -> None:
        """Passing a non-dict like an int for a slot level."""
        with pytest.raises(ValueError, match="'current' key"):
            apply_character_sheet_update(
                wizard_sheet, {"spell_slots": {"1": 3}}
            )

    def test_update_all_slot_levels_at_once(self, wizard_sheet: CharacterSheet) -> None:
        """Update all three spell levels in a single call."""
        updated, msg = apply_character_sheet_update(
            wizard_sheet,
            {
                "spell_slots": {
                    "1": {"current": 0},
                    "2": {"current": 0},
                    "3": {"current": 0},
                }
            },
        )
        assert updated.spell_slots[1].current == 0
        assert updated.spell_slots[2].current == 0
        assert updated.spell_slots[3].current == 0
        assert "L1:" in msg
        assert "L2:" in msg
        assert "L3:" in msg

    def test_restore_spell_slot_to_max(self, wizard_sheet: CharacterSheet) -> None:
        """Restoring a slot to max after using it."""
        wizard_sheet.spell_slots[1] = SpellSlots(current=1, max=4)
        updated, msg = apply_character_sheet_update(
            wizard_sheet, {"spell_slots": {"1": {"current": 4}}}
        )
        assert updated.spell_slots[1].current == 4
        assert "L1: 1/4 -> 4/4" in msg

    def test_slot_unchanged(self, wizard_sheet: CharacterSheet) -> None:
        """Setting slot to the same current value should still produce output."""
        updated, msg = apply_character_sheet_update(
            wizard_sheet, {"spell_slots": {"1": {"current": 4}}}
        )
        assert updated.spell_slots[1].current == 4
        assert "L1: 4/4 -> 4/4" in msg

    def test_negative_level_key(self, wizard_sheet: CharacterSheet) -> None:
        """Negative level numbers should raise an error."""
        with pytest.raises(ValueError, match="No spell slot at level"):
            apply_character_sheet_update(
                wizard_sheet, {"spell_slots": {"-1": {"current": 0}}}
            )

    def test_zero_level_key(self, wizard_sheet: CharacterSheet) -> None:
        """Level 0 is not a valid spell level (cantrips don't use slots)."""
        with pytest.raises(ValueError, match="No spell slot at level"):
            apply_character_sheet_update(
                wizard_sheet, {"spell_slots": {"0": {"current": 0}}}
            )


# =============================================================================
# Extended Currency Tests
# =============================================================================


class TestApplySheetUpdateCurrencyExtended:
    """Extended currency edge case tests."""

    def test_very_large_gold(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"gold": 1_000_000}
        )
        assert updated.gold == 1_000_000
        assert "+999953" in msg

    def test_gold_unchanged(self, fighter_sheet: CharacterSheet) -> None:
        _, msg = apply_character_sheet_update(fighter_sheet, {"gold": 47})
        assert "unchanged" in msg

    def test_silver_clamped_to_zero(self, fighter_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(fighter_sheet, {"silver": -100})
        assert updated.silver == 0

    def test_copper_clamped_to_zero(self, fighter_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(fighter_sheet, {"copper": -100})
        assert updated.copper == 0

    def test_silver_float_rejected(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="integer"):
            apply_character_sheet_update(fighter_sheet, {"silver": 3.5})

    def test_copper_float_rejected(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="integer"):
            apply_character_sheet_update(fighter_sheet, {"copper": 2.5})

    def test_all_currencies_at_once(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"gold": 100, "silver": 50, "copper": 200}
        )
        assert updated.gold == 100
        assert updated.silver == 50
        assert updated.copper == 200
        assert "Gold:" in msg
        assert "Silver:" in msg
        assert "Copper:" in msg


# =============================================================================
# Extended Conditions Tests
# =============================================================================


class TestApplySheetUpdateConditionsExtended:
    """Extended condition edge case tests."""

    def test_add_and_remove_same_condition_simultaneously(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Adding and removing the same condition in one update."""
        fighter_sheet.conditions = ["poisoned"]
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"conditions": ["+poisoned", "-poisoned"]}
        )
        # + poisoned is no-op (already exists), then - poisoned removes it
        assert "poisoned" not in updated.conditions

    def test_add_new_and_remove_same_in_one_call(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Adding new condition then immediately removing it."""
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"conditions": ["+stunned", "-stunned"]}
        )
        assert "stunned" not in updated.conditions

    def test_many_conditions(self, fighter_sheet: CharacterSheet) -> None:
        """Add many conditions at once."""
        conditions = [
            "+blinded", "+charmed", "+deafened", "+frightened",
            "+grappled", "+incapacitated", "+invisible", "+paralyzed",
            "+petrified", "+poisoned", "+prone", "+restrained",
            "+stunned", "+unconscious",
        ]
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"conditions": conditions}
        )
        assert len(updated.conditions) == 14

    def test_conditions_with_integer_values_raises(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Conditions list should only contain strings."""
        with pytest.raises((ValueError, AttributeError)):
            apply_character_sheet_update(
                fighter_sheet, {"conditions": [1, 2, 3]}
            )


# =============================================================================
# Extended Equipment Tests
# =============================================================================


class TestApplySheetUpdateEquipmentExtended:
    """Extended equipment edge case tests."""

    def test_add_many_equipment_items(self, fighter_sheet: CharacterSheet) -> None:
        updates = [f"+Item_{i}" for i in range(25)]
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"equipment": updates}
        )
        names = [e.name for e in updated.equipment]
        assert "Item_0" in names
        assert "Item_24" in names
        # Original 3 + 25 new
        assert len(updated.equipment) == 28

    def test_equipment_with_comma_in_name(self, fighter_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"equipment": ["+Rope, 50 feet"]}
        )
        names = [e.name for e in updated.equipment]
        assert "Rope, 50 feet" in names

    def test_equipment_with_unicode(self, fighter_sheet: CharacterSheet) -> None:
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"equipment": ["+M\u00f6bius Ring"]}
        )
        names = [e.name for e in updated.equipment]
        assert "M\u00f6bius Ring" in names

    def test_remove_nonexistent_equipment_no_error(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Removing equipment that doesn't exist should not error."""
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"equipment": ["-Nonexistent Widget"]}
        )
        assert len(updated.equipment) == 3  # Original items unchanged
        assert "lost Nonexistent Widget" in msg

    def test_add_equipment_empty_string_skipped(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Empty strings in equipment updates should be skipped."""
        updated, _ = apply_character_sheet_update(
            fighter_sheet, {"equipment": ["", "  ", "+Lantern"]}
        )
        names = [e.name for e in updated.equipment]
        assert "Lantern" in names
        # Should be original 3 + 1 new = 4
        assert len(updated.equipment) == 4


# =============================================================================
# Extended XP Tests
# =============================================================================


class TestApplySheetUpdateXPExtended:
    """Extended XP edge case tests."""

    def test_xp_very_large(self, fighter_sheet: CharacterSheet) -> None:
        updated, msg = apply_character_sheet_update(
            fighter_sheet, {"experience_points": 355000}
        )
        assert updated.experience_points == 355000
        assert "XP: 0 -> 355000" in msg

    def test_xp_bool_rejected(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="integer"):
            apply_character_sheet_update(
                fighter_sheet, {"experience_points": True}
            )

    def test_xp_float_rejected(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="integer"):
            apply_character_sheet_update(
                fighter_sheet, {"experience_points": 100.5}
            )

    def test_xp_string_rejected(self, fighter_sheet: CharacterSheet) -> None:
        with pytest.raises(ValueError, match="integer"):
            apply_character_sheet_update(
                fighter_sheet, {"experience_points": "1000"}
            )

    def test_xp_unchanged(self, fighter_sheet: CharacterSheet) -> None:
        _, msg = apply_character_sheet_update(
            fighter_sheet, {"experience_points": 0}
        )
        assert "XP: 0 -> 0" in msg


# =============================================================================
# Extended General / Multi-Update Tests
# =============================================================================


class TestApplySheetUpdateGeneralExtended:
    """Extended general tests for apply_character_sheet_update."""

    def test_all_supported_fields_at_once(
        self, wizard_sheet: CharacterSheet
    ) -> None:
        """Update every supported field type in a single call."""
        wizard_sheet.conditions = ["frightened"]
        updated, msg = apply_character_sheet_update(
            wizard_sheet,
            {
                "hit_points_current": 20,
                "hit_points_temp": 5,
                "conditions": ["-frightened", "+charmed"],
                "equipment": ["+Staff of Power"],
                "gold": 200,
                "silver": 30,
                "copper": 10,
                "spell_slots": {"1": {"current": 2}},
                "experience_points": 10000,
            },
        )
        assert updated.hit_points_current == 20
        assert updated.hit_points_temp == 5
        assert "charmed" in updated.conditions
        assert "frightened" not in updated.conditions
        names = [e.name for e in updated.equipment]
        assert "Staff of Power" in names
        assert updated.gold == 200
        assert updated.silver == 30
        assert updated.copper == 10
        assert updated.spell_slots[1].current == 2
        assert updated.experience_points == 10000
        assert "Elara" in msg

    def test_multiple_unsupported_fields_first_one_raises(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """First unsupported field should raise immediately."""
        with pytest.raises(ValueError, match="Unsupported"):
            apply_character_sheet_update(
                fighter_sheet, {"name": "Bad", "level": 10}
            )

    def test_mixed_valid_and_invalid_field_raises(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """A mix of valid and invalid fields - should raise on the invalid one."""
        with pytest.raises(ValueError, match="Unsupported"):
            apply_character_sheet_update(
                fighter_sheet,
                {"hit_points_current": 40, "name": "Bad"},
            )

    def test_original_conditions_not_mutated(self, fighter_sheet: CharacterSheet) -> None:
        fighter_sheet.conditions = ["poisoned"]
        original_conditions = fighter_sheet.conditions.copy()
        apply_character_sheet_update(
            fighter_sheet, {"conditions": ["+stunned"]}
        )
        assert fighter_sheet.conditions == original_conditions

    def test_original_equipment_not_mutated(self, fighter_sheet: CharacterSheet) -> None:
        original_count = len(fighter_sheet.equipment)
        apply_character_sheet_update(
            fighter_sheet, {"equipment": ["+New Item"]}
        )
        assert len(fighter_sheet.equipment) == original_count

    def test_original_spell_slots_not_mutated(
        self, wizard_sheet: CharacterSheet
    ) -> None:
        original_current = wizard_sheet.spell_slots[1].current
        apply_character_sheet_update(
            wizard_sheet, {"spell_slots": {"1": {"current": 0}}}
        )
        assert wizard_sheet.spell_slots[1].current == original_current


# =============================================================================
# Extended _execute_sheet_update Edge Cases
# =============================================================================


class TestExecuteSheetUpdateExtended:
    """Extended edge case tests for _execute_sheet_update."""

    def test_updates_as_list_returns_error(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """updates passed as a list should return an error."""
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "Thorin", "updates": [1, 2, 3]},
            sheets,
        )
        assert "Error" in result

    def test_updates_as_int_returns_error(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "Thorin", "updates": 42},
            sheets,
        )
        assert "Error" in result

    def test_character_name_case_sensitive(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Character name lookup is case-sensitive."""
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "thorin", "updates": '{"gold": 100}'},
            sheets,
        )
        assert "Error" in result

    def test_empty_json_object_updates(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """An empty JSON object should produce no changes."""
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "Thorin", "updates": "{}"},
            sheets,
        )
        assert "No changes" in result

    def test_sequential_updates_same_character(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Multiple sequential updates to the same character accumulate."""
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        _execute_sheet_update(
            {"character_name": "Thorin", "updates": '{"hit_points_current": 40}'},
            sheets,
        )
        assert sheets["Thorin"].hit_points_current == 40

        _execute_sheet_update(
            {"character_name": "Thorin", "updates": '{"gold": 100}'},
            sheets,
        )
        assert sheets["Thorin"].gold == 100
        # HP should remain from previous update
        assert sheets["Thorin"].hit_points_current == 40

    def test_sequential_updates_different_characters(
        self, fighter_sheet: CharacterSheet, wizard_sheet: CharacterSheet
    ) -> None:
        """Updates to different characters don't interfere."""
        sheets = {"Thorin": fighter_sheet, "Elara": wizard_sheet}
        result1 = _execute_sheet_update(
            {"character_name": "Thorin", "updates": '{"hit_points_current": 30}'},
            sheets,
        )
        result2 = _execute_sheet_update(
            {"character_name": "Elara", "updates": '{"hit_points_current": 20}'},
            sheets,
        )
        assert "Updated Thorin" in result1
        assert "Updated Elara" in result2
        assert sheets["Thorin"].hit_points_current == 30
        assert sheets["Elara"].hit_points_current == 20

    def test_updates_json_string_with_whitespace(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """JSON string with extra whitespace should still parse."""
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "Thorin", "updates": '  { "gold" :  100 }  '},
            sheets,
        )
        assert "Updated Thorin" in result
        assert sheets["Thorin"].gold == 100

    def test_invalid_field_in_json_returns_error(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "Thorin", "updates": '{"level": 10}'},
            sheets,
        )
        assert "Error" in result
        # Sheet should remain unchanged
        assert sheets["Thorin"].level == 5

    def test_missing_updates_key_uses_default(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """If 'updates' key is missing, should default to empty dict string."""
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "Thorin"},
            sheets,
        )
        assert "No changes" in result

    def test_none_updates(self, fighter_sheet: CharacterSheet) -> None:
        """If updates is None, should return an error."""
        sheets: dict[str, CharacterSheet] = {"Thorin": fighter_sheet}
        result = _execute_sheet_update(
            {"character_name": "Thorin", "updates": None},
            sheets,
        )
        assert "Error" in result


# =============================================================================
# Multiple Tool Calls in dm_turn Integration
# =============================================================================


class TestDmTurnMultipleToolCalls:
    """Tests for multiple sequential tool calls through dm_turn."""

    @patch("agents.get_llm")
    def test_dm_turn_processes_two_sheet_updates(
        self, mock_get_llm: MagicMock, fighter_sheet: CharacterSheet, wizard_sheet: CharacterSheet
    ) -> None:
        """Test dm_turn handles multiple sheet update tool calls in one turn."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn
        from models import AgentMemory, GameConfig

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter", "wizard"],
            "current_turn": "dm",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(provider="gemini", model="gemini-1.5-flash"),
            "characters": {
                "Thorin": CharacterConfig(
                    name="Thorin",
                    character_class="Fighter",
                    race="Dwarf",
                    personality="Brave warrior",
                    color="#FF0000",
                    provider="gemini",
                    model="gemini-1.5-flash",
                ),
                "Elara": CharacterConfig(
                    name="Elara",
                    character_class="Wizard",
                    race="Elf",
                    personality="Scholarly mage",
                    color="#0000FF",
                    provider="gemini",
                    model="gemini-1.5-flash",
                ),
            },
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "character_sheets": {"Thorin": fighter_sheet, "Elara": wizard_sheet},
        }

        # First response: two tool calls in one message
        tool_call_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "dm_update_character_sheet",
                    "args": {
                        "character_name": "Thorin",
                        "updates": {"hit_points_current": 30},
                    },
                    "id": "call_001",
                },
                {
                    "name": "dm_update_character_sheet",
                    "args": {
                        "character_name": "Elara",
                        "updates": {"spell_slots": {"1": {"current": 2}}},
                    },
                    "id": "call_002",
                },
            ],
        )
        final_response = AIMessage(
            content="The battle rages on! Thorin takes a hit and Elara expends a spell.",
        )

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = [tool_call_response, final_response]
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        assert result["character_sheets"]["Thorin"].hit_points_current == 30
        assert result["character_sheets"]["Elara"].spell_slots[1].current == 2
        assert "[DM]: The battle rages on" in result["ground_truth_log"][-1]

    @patch("agents.get_llm")
    def test_dm_turn_dice_and_sheet_update(
        self, mock_get_llm: MagicMock, fighter_sheet: CharacterSheet
    ) -> None:
        """Test dm_turn handles a dice roll followed by a sheet update."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn
        from models import AgentMemory, GameConfig

        state: GameState = {
            "ground_truth_log": [],
            "turn_queue": ["dm", "fighter"],
            "current_turn": "dm",
            "agent_memories": {"dm": AgentMemory()},
            "game_config": GameConfig(),
            "dm_config": DMConfig(provider="gemini", model="gemini-1.5-flash"),
            "characters": {"Thorin": CharacterConfig(
                name="Thorin",
                character_class="Fighter",
                race="Dwarf",
                personality="Brave warrior",
                color="#FF0000",
                provider="gemini",
                model="gemini-1.5-flash",
            )},
            "whisper_queue": [],
            "human_active": False,
            "controlled_character": None,
            "session_number": 1,
            "session_id": "001",
            "character_sheets": {"Thorin": fighter_sheet},
        }

        # First call: dice + sheet update
        tool_call_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "dm_roll_dice",
                    "args": {"notation": "1d6"},
                    "id": "call_dice",
                },
                {
                    "name": "dm_update_character_sheet",
                    "args": {
                        "character_name": "Thorin",
                        "updates": {"hit_points_current": 40},
                    },
                    "id": "call_sheet",
                },
            ],
        )
        final_response = AIMessage(
            content="The trap springs! Thorin takes damage.",
        )

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = [tool_call_response, final_response]
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        assert result["character_sheets"]["Thorin"].hit_points_current == 40
        assert "[DM]: The trap springs" in result["ground_truth_log"][-1]
