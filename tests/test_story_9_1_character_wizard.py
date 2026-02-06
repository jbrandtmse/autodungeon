"""Tests for Story 9-1: Character Creation Wizard.

Tests the multi-step character creation wizard UI functionality.
"""

from __future__ import annotations

from typing import Any

import pytest


class TestDnd5eDataLoading:
    """Tests for D&D 5e data loading from config."""

    def test_load_dnd5e_data_returns_dict(self) -> None:
        """Data loader returns a dictionary."""
        from config import load_dnd5e_data

        data = load_dnd5e_data()
        assert isinstance(data, dict)

    def test_dnd5e_data_has_required_sections(self) -> None:
        """Data contains all required sections."""
        from config import load_dnd5e_data

        data = load_dnd5e_data()

        assert "races" in data
        assert "classes" in data
        assert "backgrounds" in data
        assert "point_buy" in data
        assert "standard_array" in data
        assert "abilities" in data
        assert "skills" in data

    def test_get_dnd5e_races_returns_list(self) -> None:
        """get_dnd5e_races returns a list of race dicts."""
        from config import get_dnd5e_races

        races = get_dnd5e_races()
        assert isinstance(races, list)
        assert len(races) >= 9  # At least 9 standard races

    def test_race_has_required_fields(self) -> None:
        """Each race has required fields."""
        from config import get_dnd5e_races

        races = get_dnd5e_races()
        for race in races:
            assert "id" in race
            assert "name" in race
            assert "description" in race
            assert "ability_bonuses" in race
            assert "speed" in race

    def test_specific_races_exist(self) -> None:
        """Standard D&D 5e races are present."""
        from config import get_dnd5e_races

        races = get_dnd5e_races()
        race_ids = [r["id"] for r in races]

        expected_races = ["human", "elf", "dwarf", "halfling", "dragonborn", "gnome", "half-elf", "half-orc", "tiefling"]
        for race_id in expected_races:
            assert race_id in race_ids, f"Missing race: {race_id}"

    def test_get_dnd5e_classes_returns_list(self) -> None:
        """get_dnd5e_classes returns a list of class dicts."""
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()
        assert isinstance(classes, list)
        assert len(classes) >= 12  # All 12 standard classes

    def test_class_has_required_fields(self) -> None:
        """Each class has required fields."""
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()
        for cls in classes:
            assert "id" in cls
            assert "name" in cls
            assert "description" in cls
            assert "hit_die" in cls
            assert "primary_ability" in cls
            assert "saving_throws" in cls

    def test_specific_classes_exist(self) -> None:
        """Standard D&D 5e classes are present."""
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()
        class_ids = [c["id"] for c in classes]

        expected_classes = ["fighter", "rogue", "wizard", "cleric", "barbarian", "bard", "ranger", "paladin", "sorcerer", "warlock", "monk", "druid"]
        for class_id in expected_classes:
            assert class_id in class_ids, f"Missing class: {class_id}"

    def test_get_dnd5e_backgrounds_returns_list(self) -> None:
        """get_dnd5e_backgrounds returns a list of background dicts."""
        from config import get_dnd5e_backgrounds

        backgrounds = get_dnd5e_backgrounds()
        assert isinstance(backgrounds, list)
        assert len(backgrounds) >= 13  # At least 13 standard backgrounds

    def test_background_has_required_fields(self) -> None:
        """Each background has required fields."""
        from config import get_dnd5e_backgrounds

        backgrounds = get_dnd5e_backgrounds()
        for bg in backgrounds:
            assert "id" in bg
            assert "name" in bg
            assert "description" in bg
            assert "skill_proficiencies" in bg
            assert "feature" in bg

    def test_specific_backgrounds_exist(self) -> None:
        """Standard D&D 5e backgrounds are present."""
        from config import get_dnd5e_backgrounds

        backgrounds = get_dnd5e_backgrounds()
        bg_ids = [b["id"] for b in backgrounds]

        expected = ["acolyte", "criminal", "folk-hero", "noble", "sage", "soldier"]
        for bg_id in expected:
            assert bg_id in bg_ids, f"Missing background: {bg_id}"

    def test_get_point_buy_config(self) -> None:
        """Point buy config has budget and costs."""
        from config import get_point_buy_config

        config = get_point_buy_config()
        assert "budget" in config
        assert config["budget"] == 27

        assert "costs" in config
        costs = config["costs"]
        assert costs[8] == 0
        assert costs[15] == 9

    def test_get_standard_array(self) -> None:
        """Standard array returns correct values."""
        from config import get_standard_array

        array = get_standard_array()
        assert array == [15, 14, 13, 12, 10, 8]


class TestWizardSteps:
    """Tests for wizard step definitions."""

    def test_wizard_steps_defined(self) -> None:
        """WIZARD_STEPS constant is defined with 6 steps."""
        from app import WIZARD_STEPS

        assert len(WIZARD_STEPS) == 6

    def test_wizard_steps_structure(self) -> None:
        """Each step has required fields."""
        from app import WIZARD_STEPS

        for step in WIZARD_STEPS:
            assert "id" in step
            assert "name" in step
            assert "description" in step

    def test_wizard_step_ids(self) -> None:
        """Steps have expected IDs in order."""
        from app import WIZARD_STEPS

        expected_ids = ["basics", "abilities", "background", "equipment", "personality", "review"]
        actual_ids = [s["id"] for s in WIZARD_STEPS]
        assert actual_ids == expected_ids


class TestWizardDataStructure:
    """Tests for wizard data initialization."""

    def test_get_default_wizard_data_returns_dict(self) -> None:
        """Default wizard data is a dict."""
        from app import get_default_wizard_data

        data = get_default_wizard_data()
        assert isinstance(data, dict)

    def test_default_wizard_data_has_required_fields(self) -> None:
        """Default wizard data has all required fields."""
        from app import get_default_wizard_data

        data = get_default_wizard_data()

        assert "name" in data
        assert "race_id" in data
        assert "class_id" in data
        assert "background_id" in data
        assert "ability_method" in data
        assert "abilities" in data
        assert "standard_array_assignment" in data
        assert "skill_proficiencies" in data
        assert "equipment_choices" in data
        assert "personality_traits" in data
        assert "ideals" in data
        assert "bonds" in data
        assert "flaws" in data
        assert "backstory" in data

    def test_default_abilities_all_eight(self) -> None:
        """Default abilities all start at 8."""
        from app import get_default_wizard_data

        data = get_default_wizard_data()
        abilities = data["abilities"]

        expected_abilities = ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]
        for ability in expected_abilities:
            assert ability in abilities
            assert abilities[ability] == 8

    def test_default_ability_method_is_point_buy(self) -> None:
        """Default ability method is point buy."""
        from app import get_default_wizard_data

        data = get_default_wizard_data()
        assert data["ability_method"] == "point_buy"


class TestPointBuyCalculation:
    """Tests for point buy cost calculation."""

    def test_calculate_point_buy_cost_all_eights(self) -> None:
        """All 8s costs 0 points."""
        from app import calculate_point_buy_cost

        abilities = {
            "strength": 8,
            "dexterity": 8,
            "constitution": 8,
            "intelligence": 8,
            "wisdom": 8,
            "charisma": 8,
        }
        cost = calculate_point_buy_cost(abilities)
        assert cost == 0

    def test_calculate_point_buy_cost_standard_spread(self) -> None:
        """Standard spread costs 27 points."""
        from app import calculate_point_buy_cost

        # A common spread: 15, 15, 15, 8, 8, 8 costs 27
        abilities = {
            "strength": 15,
            "dexterity": 15,
            "constitution": 15,
            "intelligence": 8,
            "wisdom": 8,
            "charisma": 8,
        }
        cost = calculate_point_buy_cost(abilities)
        # 15 costs 9, so 9*3 = 27
        assert cost == 27

    def test_calculate_point_buy_cost_mixed(self) -> None:
        """Mixed scores calculate correctly."""
        from app import calculate_point_buy_cost

        abilities = {
            "strength": 14,  # 7 points
            "dexterity": 14,  # 7 points
            "constitution": 14,  # 7 points
            "intelligence": 10,  # 2 points
            "wisdom": 10,  # 2 points
            "charisma": 10,  # 2 points
        }
        cost = calculate_point_buy_cost(abilities)
        # 7*3 + 2*3 = 21 + 6 = 27
        assert cost == 27

    def test_get_point_buy_remaining_full_budget(self) -> None:
        """Full budget remaining with all 8s."""
        from app import get_point_buy_remaining

        abilities = {
            "strength": 8,
            "dexterity": 8,
            "constitution": 8,
            "intelligence": 8,
            "wisdom": 8,
            "charisma": 8,
        }
        remaining = get_point_buy_remaining(abilities)
        assert remaining == 27

    def test_get_point_buy_remaining_zero(self) -> None:
        """Zero remaining when fully spent."""
        from app import get_point_buy_remaining

        abilities = {
            "strength": 15,
            "dexterity": 15,
            "constitution": 15,
            "intelligence": 8,
            "wisdom": 8,
            "charisma": 8,
        }
        remaining = get_point_buy_remaining(abilities)
        assert remaining == 0

    def test_get_point_buy_remaining_negative(self) -> None:
        """Negative remaining when over budget."""
        from app import get_point_buy_remaining

        abilities = {
            "strength": 15,
            "dexterity": 15,
            "constitution": 15,
            "intelligence": 15,
            "wisdom": 8,
            "charisma": 8,
        }
        remaining = get_point_buy_remaining(abilities)
        # 9*4 = 36, over by 9
        assert remaining == -9


class TestRaceAbilityBonuses:
    """Tests for race ability bonuses."""

    def test_human_has_all_bonuses(self) -> None:
        """Human gets +1 to all abilities."""
        from config import get_dnd5e_races

        races = get_dnd5e_races()
        human = next(r for r in races if r["id"] == "human")

        bonuses = human["ability_bonuses"]
        for ability in ["strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"]:
            assert bonuses.get(ability) == 1

    def test_elf_has_dexterity_bonus(self) -> None:
        """Elf gets +2 DEX."""
        from config import get_dnd5e_races

        races = get_dnd5e_races()
        elf = next(r for r in races if r["id"] == "elf")

        assert elf["ability_bonuses"]["dexterity"] == 2

    def test_dwarf_has_constitution_bonus(self) -> None:
        """Dwarf gets +2 CON."""
        from config import get_dnd5e_races

        races = get_dnd5e_races()
        dwarf = next(r for r in races if r["id"] == "dwarf")

        assert dwarf["ability_bonuses"]["constitution"] == 2


class TestClassStartingEquipment:
    """Tests for class starting equipment choices."""

    def test_fighter_has_equipment_choices(self) -> None:
        """Fighter has starting equipment with choices."""
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()
        fighter = next(c for c in classes if c["id"] == "fighter")

        equipment = fighter.get("starting_equipment", [])
        assert len(equipment) > 0

        # Should have at least one choice
        choices = [e for e in equipment if isinstance(e, dict) and "choice" in e]
        assert len(choices) > 0

    def test_rogue_has_thieves_tools(self) -> None:
        """Rogue gets thieves' tools."""
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()
        rogue = next(c for c in classes if c["id"] == "rogue")

        equipment = rogue.get("starting_equipment", [])
        fixed_items = [e.get("item") for e in equipment if isinstance(e, dict) and "item" in e]

        assert "thieves' tools" in fixed_items


class TestBackgroundProficiencies:
    """Tests for background skill proficiencies."""

    def test_acolyte_skills(self) -> None:
        """Acolyte has Insight and Religion."""
        from config import get_dnd5e_backgrounds

        backgrounds = get_dnd5e_backgrounds()
        acolyte = next(b for b in backgrounds if b["id"] == "acolyte")

        skills = acolyte["skill_proficiencies"]
        assert "Insight" in skills
        assert "Religion" in skills

    def test_criminal_skills(self) -> None:
        """Criminal has Deception and Stealth."""
        from config import get_dnd5e_backgrounds

        backgrounds = get_dnd5e_backgrounds()
        criminal = next(b for b in backgrounds if b["id"] == "criminal")

        skills = criminal["skill_proficiencies"]
        assert "Deception" in skills
        assert "Stealth" in skills

    def test_sage_skills(self) -> None:
        """Sage has Arcana and History."""
        from config import get_dnd5e_backgrounds

        backgrounds = get_dnd5e_backgrounds()
        sage = next(b for b in backgrounds if b["id"] == "sage")

        skills = sage["skill_proficiencies"]
        assert "Arcana" in skills
        assert "History" in skills


class TestAbilityModifierCalculation:
    """Tests for ability modifier calculation (score - 10) // 2."""

    @pytest.mark.parametrize(
        "score,expected_modifier",
        [
            (8, -1),
            (9, -1),
            (10, 0),
            (11, 0),
            (12, 1),
            (13, 1),
            (14, 2),
            (15, 2),
            (16, 3),
            (17, 3),
            (18, 4),
            (20, 5),
        ],
    )
    def test_ability_modifier_formula(self, score: int, expected_modifier: int) -> None:
        """Verify standard D&D ability modifier formula."""
        modifier = (score - 10) // 2
        assert modifier == expected_modifier


class TestSkillsData:
    """Tests for skills data."""

    def test_skills_list_complete(self) -> None:
        """All 18 skills are present."""
        from config import load_dnd5e_data

        data = load_dnd5e_data()
        skills = data.get("skills", [])

        assert len(skills) == 18

    def test_skills_have_abilities(self) -> None:
        """Each skill has an associated ability."""
        from config import load_dnd5e_data

        data = load_dnd5e_data()
        skills = data.get("skills", [])

        valid_abilities = {"strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"}
        for skill in skills:
            assert "ability" in skill
            assert skill["ability"] in valid_abilities


class TestClassSkillSelection:
    """Tests for class skill selection feature (M1 fix)."""

    def test_class_has_skill_choices_and_options(self) -> None:
        """Classes have skill_choices count and skill_options list."""
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()
        for cls in classes:
            # All classes should have these fields
            assert "skill_choices" in cls, f"{cls['id']} missing skill_choices"
            assert "skill_options" in cls, f"{cls['id']} missing skill_options"
            assert cls["skill_choices"] >= 0

    def test_rogue_gets_four_skill_choices(self) -> None:
        """Rogue gets 4 skill choices (most of any class)."""
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()
        rogue = next(c for c in classes if c["id"] == "rogue")

        assert rogue["skill_choices"] == 4
        assert len(rogue["skill_options"]) >= 10  # Rogue has many options

    def test_bard_gets_any_skill(self) -> None:
        """Bard can choose from any skill."""
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()
        bard = next(c for c in classes if c["id"] == "bard")

        assert bard["skill_options"] == ["any"]

    def test_fighter_has_limited_skill_options(self) -> None:
        """Fighter has specific skill options."""
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()
        fighter = next(c for c in classes if c["id"] == "fighter")

        assert fighter["skill_choices"] == 2
        assert "Athletics" in fighter["skill_options"]


class TestWizardDataWithClassSkills:
    """Tests for wizard data including class skills."""

    def test_default_wizard_data_has_class_skill_proficiencies(self) -> None:
        """Default wizard data includes class_skill_proficiencies field."""
        from app import get_default_wizard_data

        data = get_default_wizard_data()
        assert "class_skill_proficiencies" in data
        assert data["class_skill_proficiencies"] == []


class TestDnd5eDataYamlValidity:
    """Tests for YAML data file validity."""

    def test_yaml_loads_without_error(self) -> None:
        """YAML file loads without errors."""
        from config import load_dnd5e_data

        # Should not raise
        data = load_dnd5e_data()
        assert data is not None

    def test_no_duplicate_race_ids(self) -> None:
        """No duplicate race IDs."""
        from config import get_dnd5e_races

        races = get_dnd5e_races()
        ids = [r["id"] for r in races]
        assert len(ids) == len(set(ids))

    def test_no_duplicate_class_ids(self) -> None:
        """No duplicate class IDs."""
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()
        ids = [c["id"] for c in classes]
        assert len(ids) == len(set(ids))

    def test_no_duplicate_background_ids(self) -> None:
        """No duplicate background IDs."""
        from config import get_dnd5e_backgrounds

        backgrounds = get_dnd5e_backgrounds()
        ids = [b["id"] for b in backgrounds]
        assert len(ids) == len(set(ids))
