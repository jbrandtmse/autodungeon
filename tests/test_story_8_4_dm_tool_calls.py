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
