"""Tests for Story 13.3: Character Sheet Initialization.

This test file covers:
- generate_character_sheet_from_config for Fighter, Rogue, Wizard, Cleric, Warlock, unknown class
- Full HP at start (current == max)
- load_character_sheet_from_library with full sheet data, partial data, missing data
- populate_game_state returns non-empty character_sheets
- Sheets keyed by character NAME
- get_character_sheet checks game state first
- Backward compat (get_character_sheet falls back to sample)
- Context injection functions work with populated sheets
- _build_selected_characters returns library_data tuple
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from models import (
    CharacterConfig,
    CharacterSheet,
    generate_character_sheet_from_config,
    load_character_sheet_from_library,
    populate_game_state,
)

# =============================================================================
# Helper: Create CharacterConfig instances for testing
# =============================================================================


def _make_config(
    name: str = "TestHero",
    character_class: str = "Fighter",
    personality: str = "Brave and bold.",
    color: str = "#C45C4A",
) -> CharacterConfig:
    return CharacterConfig(
        name=name,
        character_class=character_class,
        personality=personality,
        color=color,
    )


# =============================================================================
# Task 1: generate_character_sheet_from_config tests
# =============================================================================


class TestGenerateFromConfigFighter:
    """Tests for Fighter character sheet generation."""

    def test_fighter_basic_info(self) -> None:
        """Test Fighter sheet has correct name, class, level."""
        config = _make_config(name="Thorin", character_class="Fighter")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.name == "Thorin"
        assert sheet.character_class == "Fighter"
        assert sheet.level == 1

    def test_fighter_ability_scores(self) -> None:
        """Test Fighter has STR-focused ability scores."""
        config = _make_config(character_class="Fighter")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.strength == 16
        assert sheet.constitution == 15

    def test_fighter_hp_full(self) -> None:
        """Test Fighter starts with full HP (current == max)."""
        config = _make_config(character_class="Fighter")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.hit_points_current == sheet.hit_points_max
        # HP = hit_die(10) + CON mod((15-10)//2 = 2) = 12
        assert sheet.hit_points_max == 12

    def test_fighter_armor_class(self) -> None:
        """Test Fighter AC from heavy armor (no DEX bonus)."""
        config = _make_config(character_class="Fighter")
        sheet = generate_character_sheet_from_config(config)

        # Chain Mail = 16 AC, heavy armor (no DEX)
        assert sheet.armor_class == 16

    def test_fighter_weapons(self) -> None:
        """Test Fighter has Longsword and Javelin."""
        config = _make_config(character_class="Fighter")
        sheet = generate_character_sheet_from_config(config)

        weapon_names = [w.name for w in sheet.weapons]
        assert "Longsword" in weapon_names
        assert "Javelin" in weapon_names

    def test_fighter_saving_throws(self) -> None:
        """Test Fighter proficient in STR and CON saves."""
        config = _make_config(character_class="Fighter")
        sheet = generate_character_sheet_from_config(config)

        assert "strength" in sheet.saving_throw_proficiencies
        assert "constitution" in sheet.saving_throw_proficiencies

    def test_fighter_no_spellcasting(self) -> None:
        """Test Fighter has no spellcasting ability."""
        config = _make_config(character_class="Fighter")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.spellcasting_ability is None
        assert sheet.spell_save_dc is None
        assert sheet.spell_attack_bonus is None
        assert len(sheet.cantrips) == 0
        assert len(sheet.spells_known) == 0

    def test_fighter_hit_dice(self) -> None:
        """Test Fighter has 1d10 hit dice at level 1."""
        config = _make_config(character_class="Fighter")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.hit_dice == "1d10"
        assert sheet.hit_dice_remaining == 1

    def test_fighter_class_features(self) -> None:
        """Test Fighter has level-1 class features."""
        config = _make_config(character_class="Fighter")
        sheet = generate_character_sheet_from_config(config)

        assert "Second Wind" in sheet.class_features
        assert "Fighting Style" in sheet.class_features


class TestGenerateFromConfigRogue:
    """Tests for Rogue character sheet generation."""

    def test_rogue_basic_info(self) -> None:
        """Test Rogue sheet has correct class."""
        config = _make_config(name="Shadow", character_class="Rogue")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.character_class == "Rogue"

    def test_rogue_dex_focused(self) -> None:
        """Test Rogue has DEX-focused ability scores."""
        config = _make_config(character_class="Rogue")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.dexterity == 16

    def test_rogue_hp_full(self) -> None:
        """Test Rogue starts with full HP."""
        config = _make_config(character_class="Rogue")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.hit_points_current == sheet.hit_points_max
        # HP = hit_die(8) + CON mod((12-10)//2 = 1) = 9
        assert sheet.hit_points_max == 9

    def test_rogue_ac_light_armor(self) -> None:
        """Test Rogue AC from light armor + DEX."""
        config = _make_config(character_class="Rogue")
        sheet = generate_character_sheet_from_config(config)

        # Leather Armor(11) + DEX mod((16-10)//2 = 3) = 14
        assert sheet.armor_class == 14

    def test_rogue_expertise(self) -> None:
        """Test Rogue has expertise in skills."""
        config = _make_config(character_class="Rogue")
        sheet = generate_character_sheet_from_config(config)

        assert len(sheet.skill_expertise) > 0
        assert "Stealth" in sheet.skill_expertise

    def test_rogue_hit_dice(self) -> None:
        """Test Rogue has 1d8 hit dice."""
        config = _make_config(character_class="Rogue")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.hit_dice == "1d8"

    def test_rogue_no_spellcasting(self) -> None:
        """Test Rogue has no spellcasting."""
        config = _make_config(character_class="Rogue")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.spellcasting_ability is None


class TestGenerateFromConfigWizard:
    """Tests for Wizard character sheet generation."""

    def test_wizard_basic_info(self) -> None:
        """Test Wizard sheet has correct class."""
        config = _make_config(name="Gandalf", character_class="Wizard")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.character_class == "Wizard"

    def test_wizard_int_focused(self) -> None:
        """Test Wizard has INT-focused ability scores."""
        config = _make_config(character_class="Wizard")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.intelligence == 16

    def test_wizard_hp_full(self) -> None:
        """Test Wizard starts with full HP."""
        config = _make_config(character_class="Wizard")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.hit_points_current == sheet.hit_points_max
        # HP = hit_die(6) + CON mod((12-10)//2 = 1) = 7
        assert sheet.hit_points_max == 7

    def test_wizard_unarmored_ac(self) -> None:
        """Test Wizard AC unarmored (10 + DEX)."""
        config = _make_config(character_class="Wizard")
        sheet = generate_character_sheet_from_config(config)

        # Unarmored: 10 + DEX mod((14-10)//2 = 2) = 12
        assert sheet.armor_class == 12
        assert sheet.armor is None

    def test_wizard_spellcasting(self) -> None:
        """Test Wizard has spellcasting ability set."""
        config = _make_config(character_class="Wizard")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.spellcasting_ability == "intelligence"
        assert sheet.spell_save_dc is not None
        assert sheet.spell_attack_bonus is not None
        # DC = 8 + prof(2) + INT mod((16-10)//2 = 3) = 13
        assert sheet.spell_save_dc == 13
        assert sheet.spell_attack_bonus == 5

    def test_wizard_cantrips_and_spells(self) -> None:
        """Test Wizard has cantrips and level-1 spells."""
        config = _make_config(character_class="Wizard")
        sheet = generate_character_sheet_from_config(config)

        assert len(sheet.cantrips) > 0
        assert "Fire Bolt" in sheet.cantrips
        assert len(sheet.spells_known) > 0
        assert any(s.name == "Magic Missile" for s in sheet.spells_known)

    def test_wizard_spell_slots(self) -> None:
        """Test Wizard has level-1 spell slots."""
        config = _make_config(character_class="Wizard")
        sheet = generate_character_sheet_from_config(config)

        assert 1 in sheet.spell_slots
        assert sheet.spell_slots[1].max == 2
        assert sheet.spell_slots[1].current == 2

    def test_wizard_hit_dice(self) -> None:
        """Test Wizard has 1d6 hit dice."""
        config = _make_config(character_class="Wizard")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.hit_dice == "1d6"


class TestGenerateFromConfigCleric:
    """Tests for Cleric character sheet generation."""

    def test_cleric_basic_info(self) -> None:
        """Test Cleric sheet has correct class."""
        config = _make_config(name="Aldric", character_class="Cleric")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.character_class == "Cleric"

    def test_cleric_wis_focused(self) -> None:
        """Test Cleric has WIS-focused ability scores."""
        config = _make_config(character_class="Cleric")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.wisdom == 16

    def test_cleric_hp_full(self) -> None:
        """Test Cleric starts with full HP."""
        config = _make_config(character_class="Cleric")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.hit_points_current == sheet.hit_points_max
        # HP = hit_die(8) + CON mod((14-10)//2 = 2) = 10
        assert sheet.hit_points_max == 10

    def test_cleric_spellcasting(self) -> None:
        """Test Cleric has wisdom-based spellcasting."""
        config = _make_config(character_class="Cleric")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.spellcasting_ability == "wisdom"
        # DC = 8 + prof(2) + WIS mod((16-10)//2 = 3) = 13
        assert sheet.spell_save_dc == 13
        assert sheet.spell_attack_bonus == 5

    def test_cleric_cantrips(self) -> None:
        """Test Cleric has healing-related cantrips."""
        config = _make_config(character_class="Cleric")
        sheet = generate_character_sheet_from_config(config)

        assert "Sacred Flame" in sheet.cantrips
        assert "Spare the Dying" in sheet.cantrips

    def test_cleric_medium_armor(self) -> None:
        """Test Cleric has medium armor."""
        config = _make_config(character_class="Cleric")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.armor is not None
        assert sheet.armor.armor_type == "medium"


class TestGenerateFromConfigWarlock:
    """Tests for Warlock character sheet generation."""

    def test_warlock_basic_info(self) -> None:
        """Test Warlock sheet has correct class."""
        config = _make_config(name="Eden", character_class="Warlock")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.character_class == "Warlock"

    def test_warlock_cha_focused(self) -> None:
        """Test Warlock has CHA-focused ability scores."""
        config = _make_config(character_class="Warlock")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.charisma == 16

    def test_warlock_hp_full(self) -> None:
        """Test Warlock starts with full HP."""
        config = _make_config(character_class="Warlock")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.hit_points_current == sheet.hit_points_max
        # HP = hit_die(8) + CON mod((14-10)//2 = 2) = 10
        assert sheet.hit_points_max == 10

    def test_warlock_spellcasting(self) -> None:
        """Test Warlock has charisma-based spellcasting."""
        config = _make_config(character_class="Warlock")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.spellcasting_ability == "charisma"
        # DC = 8 + prof(2) + CHA mod((16-10)//2 = 3) = 13
        assert sheet.spell_save_dc == 13
        assert sheet.spell_attack_bonus == 5

    def test_warlock_eldritch_blast(self) -> None:
        """Test Warlock has Eldritch Blast cantrip."""
        config = _make_config(character_class="Warlock")
        sheet = generate_character_sheet_from_config(config)

        assert "Eldritch Blast" in sheet.cantrips

    def test_warlock_pact_magic(self) -> None:
        """Test Warlock has Pact Magic class feature."""
        config = _make_config(character_class="Warlock")
        sheet = generate_character_sheet_from_config(config)

        assert "Pact Magic" in sheet.class_features

    def test_warlock_light_armor(self) -> None:
        """Test Warlock has light armor."""
        config = _make_config(character_class="Warlock")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.armor is not None
        assert sheet.armor.armor_type == "light"

    def test_warlock_ac_light_armor(self) -> None:
        """Test Warlock AC from light armor + DEX."""
        config = _make_config(character_class="Warlock")
        sheet = generate_character_sheet_from_config(config)

        # Leather Armor(11) + DEX mod((14-10)//2 = 2) = 13
        assert sheet.armor_class == 13


class TestGenerateFromConfigUnknown:
    """Tests for unknown character class sheet generation."""

    def test_unknown_class_falls_back_to_fighter(self) -> None:
        """Test unknown class uses Fighter defaults."""
        config = _make_config(character_class="Bard")
        sheet = generate_character_sheet_from_config(config)

        # Should use Fighter stats and config
        assert sheet.strength == 16
        assert sheet.character_class == "Bard"  # keeps the class name

    def test_unknown_class_hp(self) -> None:
        """Test unknown class gets Fighter-like HP."""
        config = _make_config(character_class="Paladin")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.hit_points_current == sheet.hit_points_max
        # Uses Fighter stats: hit_die(10) + CON mod((15-10)//2 = 2) = 12
        assert sheet.hit_points_max == 12

    def test_unknown_class_has_weapons(self) -> None:
        """Test unknown class has Fighter weapons as fallback."""
        config = _make_config(character_class="Barbarian")
        sheet = generate_character_sheet_from_config(config)

        assert len(sheet.weapons) > 0


class TestGenerateFromConfigCommon:
    """Tests for common properties across all generated sheets."""

    def test_all_classes_full_hp(self) -> None:
        """Test all classes start with full HP (current == max)."""
        for cls in ["Fighter", "Rogue", "Wizard", "Cleric", "Warlock"]:
            config = _make_config(character_class=cls)
            sheet = generate_character_sheet_from_config(config)
            assert sheet.hit_points_current == sheet.hit_points_max, (
                f"{cls}: current({sheet.hit_points_current}) != max({sheet.hit_points_max})"
            )

    def test_all_classes_level_1(self) -> None:
        """Test all classes start at level 1."""
        for cls in ["Fighter", "Rogue", "Wizard", "Cleric", "Warlock"]:
            config = _make_config(character_class=cls)
            sheet = generate_character_sheet_from_config(config)
            assert sheet.level == 1, f"{cls} not level 1"

    def test_all_classes_have_equipment(self) -> None:
        """Test all classes get standard adventuring equipment."""
        for cls in ["Fighter", "Rogue", "Wizard", "Cleric", "Warlock"]:
            config = _make_config(character_class=cls)
            sheet = generate_character_sheet_from_config(config)
            equipment_names = [e.name for e in sheet.equipment]
            assert "Backpack" in equipment_names, f"{cls} missing Backpack"
            assert "Bedroll" in equipment_names, f"{cls} missing Bedroll"

    def test_personality_from_config(self) -> None:
        """Test personality_traits comes from config.personality."""
        config = _make_config(personality="Grumpy and sarcastic.")
        sheet = generate_character_sheet_from_config(config)

        assert sheet.personality_traits == "Grumpy and sarcastic."

    def test_initiative_matches_dex_mod(self) -> None:
        """Test initiative equals DEX modifier."""
        config = _make_config(character_class="Fighter")
        sheet = generate_character_sheet_from_config(config)

        expected_init = (sheet.dexterity - 10) // 2
        assert sheet.initiative == expected_init

    def test_proficiency_bonus_at_level_1(self) -> None:
        """Test proficiency bonus is +2 at level 1."""
        config = _make_config()
        sheet = generate_character_sheet_from_config(config)

        assert sheet.proficiency_bonus == 2

    def test_xp_zero_at_level_1(self) -> None:
        """Test XP is 0 at level 1."""
        config = _make_config()
        sheet = generate_character_sheet_from_config(config)

        assert sheet.experience_points == 0

    def test_no_conditions_at_start(self) -> None:
        """Test no conditions at game start."""
        config = _make_config()
        sheet = generate_character_sheet_from_config(config)

        assert sheet.conditions == []

    def test_returns_valid_character_sheet(self) -> None:
        """Test the returned object is a valid CharacterSheet."""
        config = _make_config()
        sheet = generate_character_sheet_from_config(config)

        assert isinstance(sheet, CharacterSheet)


# =============================================================================
# Task 2: load_character_sheet_from_library tests
# =============================================================================


class TestLoadFromLibraryFullSheet:
    """Tests for loading a full character sheet from library YAML."""

    def test_full_sheet_deserialized(self) -> None:
        """Test full character_sheet key is deserialized directly."""
        config = _make_config(name="TestChar", character_class="Fighter")
        lib_data: dict[str, Any] = {
            "character_sheet": {
                "name": "TestChar",
                "race": "Dwarf",
                "character_class": "Fighter",
                "level": 1,
                "strength": 18,
                "dexterity": 12,
                "constitution": 16,
                "intelligence": 8,
                "wisdom": 10,
                "charisma": 8,
                "armor_class": 16,
                "hit_points_max": 13,
                "hit_points_current": 13,
                "hit_dice": "1d10",
                "hit_dice_remaining": 1,
            }
        }

        sheet = load_character_sheet_from_library(config, lib_data)

        assert sheet.name == "TestChar"
        assert sheet.race == "Dwarf"
        assert sheet.strength == 18

    def test_invalid_full_sheet_falls_back(self) -> None:
        """Test invalid character_sheet data falls back to generation."""
        config = _make_config(name="TestChar", character_class="Rogue")
        lib_data: dict[str, Any] = {
            "character_sheet": {"invalid_field": "bad_data"},
        }

        sheet = load_character_sheet_from_library(config, lib_data)

        # Should fall back to generated sheet
        assert isinstance(sheet, CharacterSheet)
        assert sheet.name == "TestChar"


class TestLoadFromLibraryPartialData:
    """Tests for loading partial library data with overlay."""

    def test_race_overlay(self) -> None:
        """Test library race overrides default."""
        config = _make_config(name="Eden", character_class="Warlock")
        lib_data: dict[str, Any] = {"race": "Elf"}

        sheet = load_character_sheet_from_library(config, lib_data)

        assert sheet.race == "Elf"

    def test_background_overlay(self) -> None:
        """Test library background overrides default."""
        config = _make_config(name="Eden", character_class="Warlock")
        lib_data: dict[str, Any] = {"background": "Sage"}

        sheet = load_character_sheet_from_library(config, lib_data)

        assert sheet.background == "Sage"

    def test_abilities_overlay(self) -> None:
        """Test library abilities override defaults."""
        config = _make_config(name="Eden", character_class="Warlock")
        lib_data: dict[str, Any] = {
            "abilities": {
                "strength": 8,
                "intelligence": 15,
                "dexterity": 16,
                "charisma": 10,
                "wisdom": 13,
                "constitution": 12,
            }
        }

        sheet = load_character_sheet_from_library(config, lib_data)

        assert sheet.strength == 8
        assert sheet.intelligence == 15
        assert sheet.dexterity == 16
        assert sheet.charisma == 10

    def test_abilities_overlay_recalculates_hp(self) -> None:
        """Test ability overlay recalculates HP from new CON."""
        config = _make_config(name="Eden", character_class="Warlock")
        lib_data: dict[str, Any] = {
            "abilities": {
                "constitution": 16,  # CON mod = +3
            }
        }

        sheet = load_character_sheet_from_library(config, lib_data)

        # Warlock hit_die=8, CON mod = (16-10)//2 = 3 -> HP = 8 + 3 = 11
        assert sheet.hit_points_max == 11
        assert sheet.hit_points_current == 11

    def test_abilities_overlay_recalculates_ac(self) -> None:
        """Test ability overlay recalculates AC from new DEX."""
        config = _make_config(name="Eden", character_class="Rogue")
        lib_data: dict[str, Any] = {
            "abilities": {
                "dexterity": 18,  # DEX mod = +4
            }
        }

        sheet = load_character_sheet_from_library(config, lib_data)

        # Rogue light armor(11) + DEX mod(4) = 15
        assert sheet.armor_class == 15

    def test_skills_overlay(self) -> None:
        """Test library skills override defaults."""
        config = _make_config(name="Eden", character_class="Warlock")
        lib_data: dict[str, Any] = {"skills": ["History", "Arcana", "Deception"]}

        sheet = load_character_sheet_from_library(config, lib_data)

        assert "History" in sheet.skill_proficiencies
        assert "Arcana" in sheet.skill_proficiencies
        assert "Deception" in sheet.skill_proficiencies

    def test_equipment_string_to_item(self) -> None:
        """Test equipment strings are converted to EquipmentItem."""
        config = _make_config(name="Eden", character_class="Warlock")
        lib_data: dict[str, Any] = {
            "equipment": ["light crossbow with 20 bolts", "component pouch"]
        }

        sheet = load_character_sheet_from_library(config, lib_data)

        equip_names = [e.name for e in sheet.equipment]
        assert "light crossbow with 20 bolts" in equip_names
        assert "component pouch" in equip_names

    def test_equipment_dict_to_item(self) -> None:
        """Test equipment dicts are converted to EquipmentItem."""
        config = _make_config(name="Eden", character_class="Warlock")
        lib_data: dict[str, Any] = {
            "equipment": [{"name": "Potion of Healing", "quantity": 2}]
        }

        sheet = load_character_sheet_from_library(config, lib_data)

        equip_names = [e.name for e in sheet.equipment]
        assert "Potion of Healing" in equip_names

    def test_eden_yaml_data(self) -> None:
        """Test with actual eden.yaml-like data."""
        config = _make_config(name="Eden", character_class="Warlock", color="#4B0082")
        lib_data: dict[str, Any] = {
            "name": "Eden",
            "race": "Elf",
            "class": "Warlock",
            "background": "Sage",
            "personality": "A mysterious adventurer.",
            "abilities": {
                "strength": 8,
                "intelligence": 15,
                "dexterity": 16,
                "charisma": 10,
                "wisdom": 13,
                "constitution": 12,
            },
            "skills": ["History", "Arcana", "Deception"],
            "equipment": [
                "light crossbow with 20 bolts",
                "component pouch",
                "scholar's pack",
            ],
        }

        sheet = load_character_sheet_from_library(config, lib_data)

        assert sheet.name == "Eden"
        assert sheet.race == "Elf"
        assert sheet.background == "Sage"
        assert sheet.strength == 8
        assert sheet.dexterity == 16
        assert "History" in sheet.skill_proficiencies
        assert sheet.hit_points_current == sheet.hit_points_max


class TestLoadFromLibraryMissingData:
    """Tests for loading when library data is missing or malformed."""

    def test_empty_lib_data(self) -> None:
        """Test empty library data falls back to generated sheet."""
        config = _make_config(name="TestChar", character_class="Fighter")
        lib_data: dict[str, Any] = {}

        sheet = load_character_sheet_from_library(config, lib_data)

        assert isinstance(sheet, CharacterSheet)
        assert sheet.name == "TestChar"
        assert sheet.character_class == "Fighter"

    def test_none_abilities(self) -> None:
        """Test None abilities value is handled gracefully."""
        config = _make_config(name="TestChar", character_class="Fighter")
        lib_data: dict[str, Any] = {"abilities": None}

        sheet = load_character_sheet_from_library(config, lib_data)

        assert isinstance(sheet, CharacterSheet)

    def test_invalid_ability_values(self) -> None:
        """Test non-numeric ability values are handled gracefully."""
        config = _make_config(name="TestChar", character_class="Fighter")
        lib_data: dict[str, Any] = {"abilities": {"strength": "not_a_number"}}

        sheet = load_character_sheet_from_library(config, lib_data)

        assert isinstance(sheet, CharacterSheet)
        # Should keep the generated default since the overlay failed for STR
        assert sheet.strength == 16  # Fighter default


# =============================================================================
# Task 3: populate_game_state tests
# =============================================================================


class TestPopulateGameStateCharacterSheets:
    """Tests for populate_game_state character sheet initialization."""

    def test_character_sheets_populated(self) -> None:
        """Test populate_game_state returns non-empty character_sheets."""
        game = populate_game_state(include_sample_messages=False)

        assert len(game["character_sheets"]) > 0

    def test_sheets_keyed_by_name(self) -> None:
        """Test character sheets are keyed by character NAME (not key)."""
        game = populate_game_state(include_sample_messages=False)

        # All keys should be character names (title case), not lowercase keys
        for sheet_name, sheet in game["character_sheets"].items():
            assert sheet.name == sheet_name

    def test_sheets_match_characters(self) -> None:
        """Test each character has a corresponding sheet."""
        game = populate_game_state(include_sample_messages=False)
        characters = game["characters"]

        # Every character should have a sheet
        for _key, char_config in characters.items():
            assert char_config.name in game["character_sheets"], (
                f"Missing sheet for {char_config.name}"
            )

    def test_sheets_level_1(self) -> None:
        """Test all sheets are level 1."""
        game = populate_game_state(include_sample_messages=False)

        for _name, sheet in game["character_sheets"].items():
            assert sheet.level == 1

    def test_sheets_full_hp(self) -> None:
        """Test all sheets have full HP."""
        game = populate_game_state(include_sample_messages=False)

        for _name, sheet in game["character_sheets"].items():
            assert sheet.hit_points_current == sheet.hit_points_max

    def test_characters_override_generates_sheets(self) -> None:
        """Test character sheets generated for override characters."""
        override = {
            "hero": _make_config(name="Hero", character_class="Wizard"),
        }

        game = populate_game_state(
            include_sample_messages=False,
            characters_override=override,
        )

        assert "Hero" in game["character_sheets"]
        assert game["character_sheets"]["Hero"].character_class == "Wizard"

    def test_library_data_used_for_sheets(self) -> None:
        """Test library_data parameter is used for sheet generation."""
        override = {
            "eden": _make_config(
                name="Eden", character_class="Warlock", color="#4B0082"
            ),
        }
        lib_data = {
            "eden": {
                "race": "Elf",
                "background": "Sage",
                "abilities": {
                    "strength": 8,
                    "dexterity": 16,
                    "constitution": 12,
                    "intelligence": 15,
                    "wisdom": 13,
                    "charisma": 10,
                },
            }
        }

        game = populate_game_state(
            include_sample_messages=False,
            characters_override=override,
            library_data=lib_data,
        )

        assert "Eden" in game["character_sheets"]
        sheet = game["character_sheets"]["Eden"]
        assert sheet.race == "Elf"
        assert sheet.background == "Sage"
        assert sheet.strength == 8

    def test_backward_compat_no_library_data(self) -> None:
        """Test backward compat: no library_data still generates sheets."""
        game = populate_game_state(include_sample_messages=False)

        # Should still have sheets even without library_data
        assert len(game["character_sheets"]) > 0


# =============================================================================
# Task 4: get_character_sheet tests (app.py)
# =============================================================================


class TestGetCharacterSheetGameState:
    """Tests for get_character_sheet checking game state first."""

    @patch("app.st")
    def test_checks_game_state_first(self, mock_st: MagicMock) -> None:
        """Test get_character_sheet checks game['character_sheets'] first."""
        from app import get_character_sheet

        # Create a mock game state with a character sheet
        test_sheet = generate_character_sheet_from_config(
            _make_config(name="Thorin", character_class="Fighter")
        )
        mock_st.session_state = {
            "game": {
                "character_sheets": {"Thorin": test_sheet},
                "characters": {},
            }
        }

        result = get_character_sheet("Thorin")

        assert result is test_sheet

    @patch("app.st")
    def test_case_insensitive_game_state_lookup(self, mock_st: MagicMock) -> None:
        """Test game state lookup is case-insensitive."""
        from app import get_character_sheet

        test_sheet = generate_character_sheet_from_config(
            _make_config(name="Thorin", character_class="Fighter")
        )
        mock_st.session_state = {
            "game": {
                "character_sheets": {"Thorin": test_sheet},
                "characters": {},
            }
        }

        result = get_character_sheet("thorin")

        assert result is test_sheet

    @patch("app.st")
    def test_falls_back_to_session_state_cache(self, mock_st: MagicMock) -> None:
        """Test falls back to session state cache when not in game state."""
        from app import get_character_sheet

        test_sheet = generate_character_sheet_from_config(
            _make_config(name="Thorin", character_class="Fighter")
        )
        mock_st.session_state = {
            "game": {
                "character_sheets": {},
                "characters": {},
            },
            "character_sheets": {"Thorin": test_sheet},
        }

        result = get_character_sheet("Thorin")

        assert result is test_sheet

    @patch("app.st")
    def test_falls_back_to_sample_creation(self, mock_st: MagicMock) -> None:
        """Test creates sample sheet when not in game or session state."""
        from app import get_character_sheet

        mock_st.session_state = {
            "game": {
                "character_sheets": {},
                "characters": {
                    "thorin": CharacterConfig(
                        name="Thorin",
                        character_class="Fighter",
                        personality="Bold.",
                        color="#C45C4A",
                    )
                },
            },
        }

        result = get_character_sheet("thorin")

        assert result is not None
        assert isinstance(result, CharacterSheet)
        assert result.name == "Thorin"

    @patch("app.st")
    def test_returns_none_when_not_found(self, mock_st: MagicMock) -> None:
        """Test returns None when character not found anywhere."""
        from app import get_character_sheet

        mock_st.session_state = {
            "game": {
                "character_sheets": {},
                "characters": {},
            },
        }

        result = get_character_sheet("NonExistent")

        assert result is None


# =============================================================================
# Task 5: _build_selected_characters returns library_data
# =============================================================================


class TestBuildSelectedCharactersLibraryData:
    """Tests for _build_selected_characters returning library data tuple."""

    def test_returns_tuple(self) -> None:
        """Test _build_selected_characters returns a tuple."""
        from app import _build_selected_characters

        presets = {"thorin": _make_config(name="Thorin")}
        party_selection = {"preset:thorin": True}

        result = _build_selected_characters(party_selection, presets, [])

        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_library_data_for_library_chars(self) -> None:
        """Test library data returned for selected library characters."""
        from app import _build_selected_characters

        lib_chars = [
            {
                "name": "Eden",
                "class": "Warlock",
                "personality": "Mysterious.",
                "color": "#4B0082",
                "race": "Elf",
                "abilities": {"strength": 8},
                "_filename": "eden.yaml",
                "_filepath": "config/characters/library/eden.yaml",
            }
        ]
        party_selection = {"library:eden.yaml": True}

        _selected, library_data = _build_selected_characters(
            party_selection, {}, lib_chars
        )

        assert "eden" in library_data
        assert library_data["eden"]["race"] == "Elf"
        assert library_data["eden"]["abilities"]["strength"] == 8

    def test_no_library_data_for_presets(self) -> None:
        """Test preset characters do not produce library data."""
        from app import _build_selected_characters

        presets = {"thorin": _make_config(name="Thorin")}
        party_selection = {"preset:thorin": True}

        _selected, library_data = _build_selected_characters(
            party_selection, presets, []
        )

        assert len(library_data) == 0

    def test_empty_library_data_when_none_selected(self) -> None:
        """Test empty library data when no library chars selected."""
        from app import _build_selected_characters

        lib_chars = [
            {
                "name": "Eden",
                "class": "Warlock",
                "personality": "Mysterious.",
                "color": "#4B0082",
                "_filename": "eden.yaml",
                "_filepath": "config/characters/library/eden.yaml",
            }
        ]
        party_selection = {"library:eden.yaml": False}

        _selected, library_data = _build_selected_characters(
            party_selection, {}, lib_chars
        )

        assert len(library_data) == 0


# =============================================================================
# Task 6: Context injection integration tests
# =============================================================================


class TestContextInjectionWithPopulatedSheets:
    """Tests that agents.py context functions work with populated sheets."""

    def test_format_character_sheet_context_works(self) -> None:
        """Test format_character_sheet_context works with generated sheets."""
        from agents import format_character_sheet_context

        config = _make_config(name="Thorin", character_class="Fighter")
        sheet = generate_character_sheet_from_config(config)

        result = format_character_sheet_context(sheet)

        assert "Thorin" in result
        assert "Fighter" in result
        assert "HP:" in result

    def test_format_all_sheets_context_works(self) -> None:
        """Test format_all_sheets_context works with populated sheets dict."""
        from agents import format_all_sheets_context

        sheets: dict[str, CharacterSheet] = {}
        for cls in ["Fighter", "Rogue", "Wizard"]:
            config = _make_config(name=f"Test{cls}", character_class=cls)
            sheets[config.name] = generate_character_sheet_from_config(config)

        result = format_all_sheets_context(sheets)

        assert "Party Character Sheets" in result
        assert "TestFighter" in result
        assert "TestRogue" in result
        assert "TestWizard" in result

    def test_format_all_sheets_context_empty_sheets(self) -> None:
        """Test format_all_sheets_context returns empty string for no sheets."""
        from agents import format_all_sheets_context

        result = format_all_sheets_context({})

        assert result == ""

    def test_populated_game_state_sheets_work_with_context(self) -> None:
        """Test sheets from populate_game_state work with context functions."""
        from agents import format_all_sheets_context, format_character_sheet_context

        game = populate_game_state(include_sample_messages=False)
        sheets = game["character_sheets"]

        # Each individual sheet should format correctly
        for _name, sheet in sheets.items():
            result = format_character_sheet_context(sheet)
            assert len(result) > 0
            assert sheet.name in result

        # All sheets together should format correctly
        all_result = format_all_sheets_context(sheets)
        assert len(all_result) > 0
