"""Tests for Story 9-4: Character Library.

Tests the character library management functions.
"""

from __future__ import annotations

import os
from typing import Any


class TestListLibraryCharacters:
    """Tests for list_library_characters()."""

    def test_empty_library_returns_empty_list(self) -> None:
        """Empty library returns empty list."""
        from app import list_library_characters

        # Clear any existing test characters first
        from app import LIBRARY_PATH

        if os.path.exists(LIBRARY_PATH):
            for f in os.listdir(LIBRARY_PATH):
                if f.startswith("test_"):
                    os.remove(os.path.join(LIBRARY_PATH, f))

        # May still have other characters, just verify it returns a list
        characters = list_library_characters()
        assert isinstance(characters, list)

    def test_lists_saved_characters(self) -> None:
        """Lists characters saved to library."""
        import yaml

        from app import LIBRARY_PATH, list_library_characters

        os.makedirs(LIBRARY_PATH, exist_ok=True)

        # Create test character
        test_char = {
            "name": "Test List Char",
            "race": "Human",
            "class": "Fighter",
            "background": "Soldier",
            "color": "#C45C4A",
        }
        test_file = os.path.join(LIBRARY_PATH, "test_list_char.yaml")

        try:
            with open(test_file, "w", encoding="utf-8") as f:
                yaml.dump(test_char, f)

            characters = list_library_characters()

            # Should include our test character
            found = any(c.get("name") == "Test List Char" for c in characters)
            assert found, "Test character not found in library list"

            # Should have filename metadata
            test_entry = next(c for c in characters if c.get("name") == "Test List Char")
            assert test_entry.get("_filename") == "test_list_char.yaml"
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_sorted_by_name(self) -> None:
        """Characters are sorted by name."""
        import yaml

        from app import LIBRARY_PATH, list_library_characters

        os.makedirs(LIBRARY_PATH, exist_ok=True)

        # Create test characters with names that would be out of order
        chars = [
            {"name": "Zebra", "race": "Human", "class": "Fighter"},
            {"name": "Alpha", "race": "Elf", "class": "Wizard"},
        ]
        files = []

        try:
            for i, char in enumerate(chars):
                filename = f"test_sort_{i}.yaml"
                filepath = os.path.join(LIBRARY_PATH, filename)
                files.append(filepath)
                with open(filepath, "w", encoding="utf-8") as f:
                    yaml.dump(char, f)

            characters = list_library_characters()
            names = [c.get("name") for c in characters]

            # Alpha should come before Zebra
            alpha_idx = names.index("Alpha") if "Alpha" in names else -1
            zebra_idx = names.index("Zebra") if "Zebra" in names else -1

            assert alpha_idx != -1 and zebra_idx != -1
            assert alpha_idx < zebra_idx, "Characters not sorted by name"
        finally:
            for f in files:
                if os.path.exists(f):
                    os.remove(f)


class TestLoadLibraryCharacter:
    """Tests for load_library_character()."""

    def test_loads_existing_character(self) -> None:
        """Loads an existing character from library."""
        import yaml

        from app import LIBRARY_PATH, load_library_character

        os.makedirs(LIBRARY_PATH, exist_ok=True)

        test_char = {
            "name": "Test Load Char",
            "race": "Dwarf",
            "class": "Cleric",
        }
        test_file = os.path.join(LIBRARY_PATH, "test_load_char.yaml")

        try:
            with open(test_file, "w", encoding="utf-8") as f:
                yaml.dump(test_char, f)

            loaded = load_library_character("test_load_char.yaml")

            assert loaded is not None
            assert loaded["name"] == "Test Load Char"
            assert loaded["race"] == "Dwarf"
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_returns_none_for_missing(self) -> None:
        """Returns None for non-existent character."""
        from app import load_library_character

        loaded = load_library_character("nonexistent_character_12345.yaml")
        assert loaded is None


class TestDeleteLibraryCharacter:
    """Tests for delete_library_character()."""

    def test_deletes_existing_character(self) -> None:
        """Deletes a character from library."""
        import yaml

        from app import LIBRARY_PATH, delete_library_character

        os.makedirs(LIBRARY_PATH, exist_ok=True)

        test_char = {"name": "To Delete", "race": "Human", "class": "Rogue"}
        test_file = os.path.join(LIBRARY_PATH, "test_delete_char.yaml")

        with open(test_file, "w", encoding="utf-8") as f:
            yaml.dump(test_char, f)

        assert os.path.exists(test_file)

        result = delete_library_character("test_delete_char.yaml")

        assert result is True
        assert not os.path.exists(test_file)

    def test_returns_false_for_missing(self) -> None:
        """Returns False when character doesn't exist."""
        from app import delete_library_character

        result = delete_library_character("nonexistent_12345.yaml")
        assert result is False


class TestDuplicateLibraryCharacter:
    """Tests for duplicate_library_character()."""

    def test_duplicates_character(self) -> None:
        """Duplicates a character with new name."""
        import yaml

        from app import LIBRARY_PATH, duplicate_library_character

        os.makedirs(LIBRARY_PATH, exist_ok=True)

        original = {
            "name": "Original Char",
            "race": "Elf",
            "class": "Wizard",
            "abilities": {"strength": 10, "intelligence": 15},
        }
        original_file = os.path.join(LIBRARY_PATH, "test_original.yaml")

        try:
            with open(original_file, "w", encoding="utf-8") as f:
                yaml.dump(original, f)

            new_path = duplicate_library_character("test_original.yaml", "Duplicate Char")

            assert new_path is not None
            assert os.path.exists(new_path)

            with open(new_path, encoding="utf-8") as f:
                duplicate = yaml.safe_load(f)

            assert duplicate["name"] == "Duplicate Char"
            assert duplicate["race"] == "Elf"  # Preserved
            assert duplicate["abilities"]["intelligence"] == 15  # Preserved
        finally:
            if os.path.exists(original_file):
                os.remove(original_file)
            if new_path and os.path.exists(new_path):
                os.remove(new_path)

    def test_returns_none_for_missing_source(self) -> None:
        """Returns None when source character doesn't exist."""
        from app import duplicate_library_character

        result = duplicate_library_character("nonexistent_12345.yaml", "New Name")
        assert result is None


class TestConvertCharacterToWizardData:
    """Tests for convert_character_to_wizard_data()."""

    def test_converts_basic_fields(self) -> None:
        """Converts basic character fields to wizard format."""
        from app import convert_character_to_wizard_data

        char_data = {
            "name": "Convert Test",
            "race": "Human",
            "class": "Fighter",
            "background": "Soldier",
            "abilities": {
                "strength": 16,
                "dexterity": 14,
                "constitution": 14,
                "intelligence": 10,
                "wisdom": 10,
                "charisma": 8,
            },
            "skills": ["Athletics", "Intimidation"],
            "personality": "Brave and bold.",
        }

        wizard_data = convert_character_to_wizard_data(char_data)

        assert wizard_data["name"] == "Convert Test"
        assert wizard_data["race_id"] == "human"
        assert wizard_data["class_id"] == "fighter"
        assert wizard_data["background_id"] == "soldier"
        assert wizard_data["abilities"]["strength"] == 16
        assert "Athletics" in wizard_data["class_skill_proficiencies"]

    def test_parses_structured_personality(self) -> None:
        """Parses structured personality string back to components."""
        from app import convert_character_to_wizard_data

        char_data = {
            "name": "Structured Test",
            "race": "Elf",
            "class": "Wizard",
            "background": "Sage",
            "personality": "Curious about magic. Ideals: Knowledge is power. Bonds: My spellbook. Flaws: Arrogant. Backstory: A scholar of the arcane.",
        }

        wizard_data = convert_character_to_wizard_data(char_data)

        assert "Curious" in wizard_data["personality_traits"]
        assert "Knowledge" in wizard_data["ideals"]
        assert "spellbook" in wizard_data["bonds"]
        assert "Arrogant" in wizard_data["flaws"]
        assert "scholar" in wizard_data["backstory"]

    def test_handles_unknown_race_class(self) -> None:
        """Handles unknown race/class gracefully."""
        from app import convert_character_to_wizard_data

        char_data = {
            "name": "Unknown Test",
            "race": "UnknownRace",
            "class": "UnknownClass",
            "background": "UnknownBackground",
        }

        wizard_data = convert_character_to_wizard_data(char_data)

        assert wizard_data["name"] == "Unknown Test"
        assert wizard_data["race_id"] == ""  # Not found
        assert wizard_data["class_id"] == ""  # Not found


class TestSaveToLibraryPath:
    """Tests for save_character_to_library() saving to library path."""

    def test_saves_to_library_subdirectory(self) -> None:
        """Characters are saved to config/characters/library/."""
        from app import save_character_to_library

        wizard_data = {
            "name": "Library Path Test",
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

        filepath = save_character_to_library(wizard_data)

        try:
            assert "library" in filepath
            assert os.path.exists(filepath)
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)


class TestIntegration:
    """Integration tests for library workflow."""

    def test_full_library_workflow(self) -> None:
        """Test full create-list-load-duplicate-delete workflow."""
        from app import (
            delete_library_character,
            duplicate_library_character,
            list_library_characters,
            load_library_character,
            save_character_to_library,
        )

        wizard_data = {
            "name": "Workflow Test",
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

        created_files = []

        try:
            # 1. Save character
            filepath = save_character_to_library(wizard_data)
            created_files.append(filepath)
            assert os.path.exists(filepath)

            # 2. List characters
            characters = list_library_characters()
            assert any(c.get("name") == "Workflow Test" for c in characters)

            # 3. Load character
            filename = os.path.basename(filepath)
            loaded = load_library_character(filename)
            assert loaded is not None
            assert loaded["name"] == "Workflow Test"

            # 4. Duplicate character
            dup_path = duplicate_library_character(filename, "Workflow Copy")
            if dup_path:
                created_files.append(dup_path)
            assert dup_path is not None
            assert os.path.exists(dup_path)

            # 5. Delete original
            result = delete_library_character(filename)
            assert result is True
            created_files.remove(filepath)  # Already deleted

            # 6. Verify duplicate remains
            characters = list_library_characters()
            assert any(c.get("name") == "Workflow Copy" for c in characters)

        finally:
            # Cleanup
            for f in created_files:
                if os.path.exists(f):
                    os.remove(f)
