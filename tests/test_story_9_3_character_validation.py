"""Tests for Story 9-3: Character Validation.

Tests the validation functions for each wizard step and character creation.
"""

from __future__ import annotations

import os
from typing import Any


class TestValidateWizardStepBasics:
    """Tests for validate_wizard_step_basics()."""

    def test_empty_wizard_data_returns_errors(self) -> None:
        """Empty wizard data returns validation errors."""
        from app import validate_wizard_step_basics

        wizard_data: dict[str, Any] = {}
        errors = validate_wizard_step_basics(wizard_data)

        assert "Character name is required" in errors
        assert "Race is required" in errors
        assert "Class is required" in errors

    def test_valid_basics_returns_no_errors(self) -> None:
        """Valid basics data returns no errors."""
        from app import validate_wizard_step_basics

        wizard_data = {
            "name": "Thorin",
            "race_id": "dwarf",
            "class_id": "fighter",
            "class_skill_proficiencies": ["Athletics", "Intimidation"],
        }
        errors = validate_wizard_step_basics(wizard_data)

        assert len(errors) == 0

    def test_name_too_short_returns_error(self) -> None:
        """Name less than 2 characters returns error."""
        from app import validate_wizard_step_basics

        wizard_data = {
            "name": "A",
            "race_id": "human",
            "class_id": "fighter",
            "class_skill_proficiencies": ["Athletics", "Intimidation"],
        }
        errors = validate_wizard_step_basics(wizard_data)

        assert any("at least 2 characters" in e for e in errors)

    def test_invalid_race_returns_error(self) -> None:
        """Invalid race ID returns error."""
        from app import validate_wizard_step_basics

        wizard_data = {
            "name": "Test",
            "race_id": "invalid_race",
            "class_id": "fighter",
            "class_skill_proficiencies": ["Athletics", "Intimidation"],
        }
        errors = validate_wizard_step_basics(wizard_data)

        assert any("Invalid race" in e for e in errors)

    def test_invalid_class_returns_error(self) -> None:
        """Invalid class ID returns error."""
        from app import validate_wizard_step_basics

        wizard_data = {
            "name": "Test",
            "race_id": "human",
            "class_id": "invalid_class",
        }
        errors = validate_wizard_step_basics(wizard_data)

        assert any("Invalid class" in e for e in errors)

    def test_missing_class_skills_returns_error(self) -> None:
        """Missing class skill selections returns error."""
        from app import validate_wizard_step_basics

        wizard_data = {
            "name": "Test",
            "race_id": "human",
            "class_id": "fighter",  # Fighter gets 2 skill choices
            "class_skill_proficiencies": [],  # None selected
        }
        errors = validate_wizard_step_basics(wizard_data)

        assert any("more class skill" in e for e in errors)


class TestValidateWizardStepAbilities:
    """Tests for validate_wizard_step_abilities()."""

    def test_default_abilities_valid(self) -> None:
        """Default all-8s point buy is valid."""
        from app import get_default_wizard_data, validate_wizard_step_abilities

        wizard_data = get_default_wizard_data()
        errors = validate_wizard_step_abilities(wizard_data)

        # All 8s costs 0 points, which is valid (under budget)
        assert len(errors) == 0

    def test_over_budget_point_buy_returns_error(self) -> None:
        """Over-budget point buy returns error."""
        from app import validate_wizard_step_abilities

        wizard_data = {
            "ability_method": "point_buy",
            "abilities": {
                "strength": 15,
                "dexterity": 15,
                "constitution": 15,
                "intelligence": 15,
                "wisdom": 15,
                "charisma": 15,
            },
        }
        errors = validate_wizard_step_abilities(wizard_data)

        assert any("exceeded" in e for e in errors)

    def test_valid_point_buy_no_errors(self) -> None:
        """Valid point buy returns no errors."""
        from app import validate_wizard_step_abilities

        # 15 (9) + 14 (7) + 13 (5) + 12 (4) + 10 (2) + 8 (0) = 27
        wizard_data = {
            "ability_method": "point_buy",
            "abilities": {
                "strength": 15,
                "dexterity": 14,
                "constitution": 13,
                "intelligence": 12,
                "wisdom": 10,
                "charisma": 8,
            },
        }
        errors = validate_wizard_step_abilities(wizard_data)

        assert len(errors) == 0

    def test_incomplete_standard_array_returns_error(self) -> None:
        """Incomplete standard array assignment returns error."""
        from app import validate_wizard_step_abilities

        wizard_data = {
            "ability_method": "standard_array",
            "standard_array_assignment": {
                "strength": 15,
                "dexterity": 14,
                # Missing 4 assignments
            },
        }
        errors = validate_wizard_step_abilities(wizard_data)

        assert any("6 ability scores" in e for e in errors)

    def test_complete_standard_array_no_errors(self) -> None:
        """Complete standard array assignment returns no errors."""
        from app import validate_wizard_step_abilities

        wizard_data = {
            "ability_method": "standard_array",
            "standard_array_assignment": {
                "strength": 15,
                "dexterity": 14,
                "constitution": 13,
                "intelligence": 12,
                "wisdom": 10,
                "charisma": 8,
            },
        }
        errors = validate_wizard_step_abilities(wizard_data)

        assert len(errors) == 0


class TestValidateWizardStepBackground:
    """Tests for validate_wizard_step_background()."""

    def test_missing_background_returns_error(self) -> None:
        """Missing background returns error."""
        from app import validate_wizard_step_background

        wizard_data: dict[str, Any] = {}
        errors = validate_wizard_step_background(wizard_data)

        assert "Background is required" in errors

    def test_invalid_background_returns_error(self) -> None:
        """Invalid background ID returns error."""
        from app import validate_wizard_step_background

        wizard_data = {"background_id": "invalid_bg"}
        errors = validate_wizard_step_background(wizard_data)

        assert any("Invalid background" in e for e in errors)

    def test_valid_background_no_errors(self) -> None:
        """Valid background returns no errors."""
        from app import validate_wizard_step_background

        wizard_data = {"background_id": "acolyte"}
        errors = validate_wizard_step_background(wizard_data)

        assert len(errors) == 0


class TestValidateWizardStepEquipment:
    """Tests for validate_wizard_step_equipment()."""

    def test_missing_class_returns_error(self) -> None:
        """Missing class selection returns error."""
        from app import validate_wizard_step_equipment

        wizard_data: dict[str, Any] = {}
        errors = validate_wizard_step_equipment(wizard_data)

        assert any("Class must be selected" in e for e in errors)

    def test_incomplete_equipment_choices_returns_error(self) -> None:
        """Incomplete equipment choices returns error."""
        from app import validate_wizard_step_equipment

        wizard_data = {
            "class_id": "fighter",  # Fighter has equipment choices
            "equipment_choices": {},  # None made
        }
        errors = validate_wizard_step_equipment(wizard_data)

        assert any("equipment choice" in e for e in errors)

    def test_complete_equipment_choices_no_errors(self) -> None:
        """Complete equipment choices returns no errors."""
        from app import validate_wizard_step_equipment
        from config import get_dnd5e_classes

        # Get actual number of choices for fighter
        classes = get_dnd5e_classes()
        fighter = next(c for c in classes if c["id"] == "fighter")
        starting_equipment = fighter.get("starting_equipment", [])
        num_choices = sum(
            1 for item in starting_equipment
            if isinstance(item, dict) and "choice" in item
        )

        # Make all required choices
        equipment_choices = {
            f"equipment_choice_{i+1}": f"Choice {i+1}"
            for i in range(num_choices)
        }

        wizard_data = {
            "class_id": "fighter",
            "equipment_choices": equipment_choices,
        }
        errors = validate_wizard_step_equipment(wizard_data)

        assert len(errors) == 0


class TestValidateWizardStepPersonality:
    """Tests for validate_wizard_step_personality()."""

    def test_empty_personality_is_valid(self) -> None:
        """Empty personality fields are valid (optional)."""
        from app import validate_wizard_step_personality

        wizard_data: dict[str, Any] = {}
        errors = validate_wizard_step_personality(wizard_data)

        assert len(errors) == 0


class TestValidateWizardStep:
    """Tests for validate_wizard_step() dispatcher."""

    def test_validates_each_step(self) -> None:
        """Dispatcher validates each step correctly."""
        from app import validate_wizard_step

        # Step 0 (basics) with missing data should return errors
        errors = validate_wizard_step(0, {})
        assert len(errors) > 0

        # Step 4 (personality) is always valid
        errors = validate_wizard_step(4, {})
        assert len(errors) == 0

    def test_invalid_step_returns_empty(self) -> None:
        """Invalid step index returns empty errors."""
        from app import validate_wizard_step

        errors = validate_wizard_step(99, {})
        assert len(errors) == 0


class TestValidateWizardComplete:
    """Tests for validate_wizard_complete()."""

    def test_empty_data_returns_errors(self) -> None:
        """Empty wizard data returns multiple errors."""
        from app import validate_wizard_complete

        errors, warnings = validate_wizard_complete({})

        assert len(errors) > 0
        assert "Character name is required" in errors

    def test_complete_data_no_errors(self) -> None:
        """Complete wizard data returns no errors."""
        from app import validate_wizard_complete
        from config import get_dnd5e_classes

        # Get fighter's equipment choices count
        classes = get_dnd5e_classes()
        fighter = next(c for c in classes if c["id"] == "fighter")
        starting_equipment = fighter.get("starting_equipment", [])
        num_choices = sum(
            1 for item in starting_equipment
            if isinstance(item, dict) and "choice" in item
        )

        wizard_data = {
            "name": "Test Hero",
            "race_id": "human",
            "class_id": "fighter",
            "background_id": "soldier",
            "ability_method": "point_buy",
            "abilities": {
                "strength": 15,
                "dexterity": 14,
                "constitution": 13,
                "intelligence": 12,
                "wisdom": 10,
                "charisma": 8,
            },
            "class_skill_proficiencies": ["Athletics", "Intimidation"],
            "equipment_choices": {
                f"equipment_choice_{i+1}": f"Item {i+1}"
                for i in range(num_choices)
            },
            "personality_traits": "Brave and bold",
            "backstory": "A hero's journey",
        }

        errors, warnings = validate_wizard_complete(wizard_data)

        assert len(errors) == 0

    def test_warnings_for_unspent_points(self) -> None:
        """Unspent point buy points generate warning."""
        from app import validate_wizard_complete
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()
        fighter = next(c for c in classes if c["id"] == "fighter")
        starting_equipment = fighter.get("starting_equipment", [])
        num_choices = sum(
            1 for item in starting_equipment
            if isinstance(item, dict) and "choice" in item
        )

        wizard_data = {
            "name": "Test Hero",
            "race_id": "human",
            "class_id": "fighter",
            "background_id": "soldier",
            "ability_method": "point_buy",
            "abilities": {  # All 8s = 0 points spent, 27 unspent
                "strength": 8,
                "dexterity": 8,
                "constitution": 8,
                "intelligence": 8,
                "wisdom": 8,
                "charisma": 8,
            },
            "class_skill_proficiencies": ["Athletics", "Intimidation"],
            "equipment_choices": {
                f"equipment_choice_{i+1}": f"Item {i+1}"
                for i in range(num_choices)
            },
        }

        errors, warnings = validate_wizard_complete(wizard_data)

        assert any("unspent" in w for w in warnings)

    def test_warnings_for_missing_personality(self) -> None:
        """Missing personality traits generate warning."""
        from app import validate_wizard_complete
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()
        fighter = next(c for c in classes if c["id"] == "fighter")
        starting_equipment = fighter.get("starting_equipment", [])
        num_choices = sum(
            1 for item in starting_equipment
            if isinstance(item, dict) and "choice" in item
        )

        wizard_data = {
            "name": "Test Hero",
            "race_id": "human",
            "class_id": "fighter",
            "background_id": "soldier",
            "ability_method": "point_buy",
            "abilities": {
                "strength": 15,
                "dexterity": 14,
                "constitution": 13,
                "intelligence": 12,
                "wisdom": 10,
                "charisma": 8,
            },
            "class_skill_proficiencies": ["Athletics", "Intimidation"],
            "equipment_choices": {
                f"equipment_choice_{i+1}": f"Item {i+1}"
                for i in range(num_choices)
            },
            "personality_traits": "",  # Empty
            "backstory": "",  # Empty
        }

        errors, warnings = validate_wizard_complete(wizard_data)

        assert any("personality" in w.lower() for w in warnings)
        assert any("backstory" in w.lower() for w in warnings)


class TestSaveCharacterToLibrary:
    """Tests for save_character_to_library()."""

    def test_saves_character_yaml_file(self) -> None:
        """Character is saved as YAML file."""
        from app import save_character_to_library

        wizard_data = {
            "name": "Save Test Hero",
            "race_id": "human",
            "class_id": "fighter",
            "background_id": "soldier",
            "ability_method": "point_buy",
            "abilities": {
                "strength": 15,
                "dexterity": 14,
                "constitution": 13,
                "intelligence": 12,
                "wisdom": 10,
                "charisma": 8,
            },
            "skill_proficiencies": ["Athletics"],
            "class_skill_proficiencies": ["Intimidation"],
            "equipment_choices": {"equipment_choice_1": "Longsword"},
            "personality_traits": "Brave",
            "ideals": "Honor",
            "bonds": "My family",
            "flaws": "Too trusting",
            "backstory": "A hero's journey",
        }

        filepath = save_character_to_library(wizard_data)

        try:
            assert os.path.exists(filepath)
            assert filepath.endswith(".yaml")
        finally:
            # Clean up
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_saved_character_has_required_fields(self) -> None:
        """Saved character file has all required fields."""
        import yaml

        from app import save_character_to_library

        wizard_data = {
            "name": "Validation Test",
            "race_id": "elf",
            "class_id": "wizard",
            "background_id": "sage",
            "ability_method": "point_buy",
            "abilities": {
                "strength": 8,
                "dexterity": 14,
                "constitution": 12,
                "intelligence": 15,
                "wisdom": 13,
                "charisma": 10,
            },
            "skill_proficiencies": ["Arcana", "History"],
            "class_skill_proficiencies": ["Investigation"],
            "equipment_choices": {},
            "personality_traits": "Curious",
            "backstory": "A scholar",
        }

        filepath = save_character_to_library(wizard_data)

        try:
            assert os.path.exists(filepath)

            with open(filepath, encoding="utf-8") as f:
                saved_data = yaml.safe_load(f)

            assert saved_data["name"] == "Validation Test"
            assert saved_data["race"] == "Elf"
            assert saved_data["class"] == "Wizard"
            assert saved_data["background"] == "Sage"
            assert "personality" in saved_data
            assert "color" in saved_data
            assert "abilities" in saved_data
            assert "skills" in saved_data
        finally:
            # Clean up
            if os.path.exists(filepath):
                os.remove(filepath)

    def test_handles_duplicate_names(self) -> None:
        """Duplicate character names get numbered suffixes."""
        from app import save_character_to_library

        wizard_data = {
            "name": "Duplicate Test",
            "race_id": "human",
            "class_id": "fighter",
            "background_id": "soldier",
            "ability_method": "point_buy",
            "abilities": {
                "strength": 15,
                "dexterity": 14,
                "constitution": 13,
                "intelligence": 12,
                "wisdom": 10,
                "charisma": 8,
            },
            "skill_proficiencies": [],
            "class_skill_proficiencies": [],
            "equipment_choices": {},
        }

        filepath1 = save_character_to_library(wizard_data)
        filepath2 = save_character_to_library(wizard_data)

        try:
            assert os.path.exists(filepath1)
            assert os.path.exists(filepath2)
            assert filepath1 != filepath2
            assert "_1" in filepath2 or filepath2 != filepath1
        finally:
            # Clean up
            for fp in [filepath1, filepath2]:
                if os.path.exists(fp):
                    os.remove(fp)

    def test_applies_racial_ability_bonuses(self) -> None:
        """Racial ability bonuses are applied to saved character."""
        import yaml

        from app import save_character_to_library

        wizard_data = {
            "name": "Bonus Test",
            "race_id": "dwarf",  # Dwarf gets +2 CON
            "class_id": "fighter",
            "background_id": "soldier",
            "ability_method": "point_buy",
            "abilities": {
                "strength": 15,
                "dexterity": 10,
                "constitution": 14,  # Base 14 + 2 racial = 16
                "intelligence": 10,
                "wisdom": 10,
                "charisma": 8,
            },
            "skill_proficiencies": [],
            "class_skill_proficiencies": [],
            "equipment_choices": {},
        }

        filepath = save_character_to_library(wizard_data)

        try:
            with open(filepath, encoding="utf-8") as f:
                saved_data = yaml.safe_load(f)

            # Constitution should include racial bonus
            assert saved_data["abilities"]["constitution"] == 16
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


class TestIntegrationValidation:
    """Integration tests for validation flow."""

    def test_validation_prevents_invalid_character_creation(self) -> None:
        """Validation correctly identifies invalid characters."""
        from app import validate_wizard_complete

        # Character missing critical data
        invalid_data = {
            "name": "",  # Required
            "race_id": "human",
            "class_id": "fighter",
            "background_id": "",  # Required
        }

        errors, _ = validate_wizard_complete(invalid_data)

        assert len(errors) > 0
        assert any("name" in e.lower() for e in errors)
        assert any("background" in e.lower() for e in errors)

    def test_all_races_validate_correctly(self) -> None:
        """All races pass basic validation."""
        from app import validate_wizard_step_basics
        from config import get_dnd5e_races

        races = get_dnd5e_races()

        for race in races:
            wizard_data = {
                "name": "Test",
                "race_id": race["id"],
                "class_id": "fighter",
                "class_skill_proficiencies": ["Athletics", "Intimidation"],
            }
            errors = validate_wizard_step_basics(wizard_data)
            assert not any("Invalid race" in e for e in errors), f"Race {race['id']} failed validation"

    def test_all_classes_validate_correctly(self) -> None:
        """All classes pass basic validation."""
        from app import validate_wizard_step_basics
        from config import get_dnd5e_classes

        classes = get_dnd5e_classes()

        for cls in classes:
            # Get required skill count for this class
            skill_choices = cls.get("skill_choices", 0)
            skill_options = cls.get("skill_options", [])

            # Handle "any" skill option
            if skill_options == ["any"]:
                from config import load_dnd5e_data
                dnd_data = load_dnd5e_data()
                skill_options = [s["name"] for s in dnd_data.get("skills", [])]

            # Select required number of skills
            selected_skills = skill_options[:skill_choices] if skill_options else []

            wizard_data = {
                "name": "Test",
                "race_id": "human",
                "class_id": cls["id"],
                "class_skill_proficiencies": selected_skills,
            }
            errors = validate_wizard_step_basics(wizard_data)
            assert not any("Invalid class" in e for e in errors), f"Class {cls['id']} failed validation"

    def test_all_backgrounds_validate_correctly(self) -> None:
        """All backgrounds pass validation."""
        from app import validate_wizard_step_background
        from config import get_dnd5e_backgrounds

        backgrounds = get_dnd5e_backgrounds()

        for bg in backgrounds:
            wizard_data = {"background_id": bg["id"]}
            errors = validate_wizard_step_background(wizard_data)
            assert len(errors) == 0, f"Background {bg['id']} failed validation"
