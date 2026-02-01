"""Tests for Story 8.1: Character Sheet Data Model.

This module tests all character sheet models including:
- Weapon, Armor, EquipmentItem (equipment models)
- Spell, SpellSlots (spell-related models)
- DeathSaves (death saving throw tracking)
- CharacterSheet (complete D&D 5e character sheet)

Tests cover:
- Model creation and validation
- Field constraints and bounds
- Computed properties (ability modifiers, proficiency bonus)
- JSON serialization and deserialization
- Error handling for invalid data
"""

import json

import pytest
from pydantic import ValidationError

from models import (
    Armor,
    CharacterSheet,
    DeathSaves,
    EquipmentItem,
    Spell,
    SpellSlots,
    Weapon,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_weapon() -> Weapon:
    """Create a sample weapon for testing."""
    return Weapon(
        name="Longsword",
        damage_dice="1d8",
        damage_type="slashing",
        properties=["versatile"],
        attack_bonus=0,
        is_equipped=True,
    )


@pytest.fixture
def sample_armor() -> Armor:
    """Create sample armor for testing."""
    return Armor(
        name="Chain Mail",
        armor_class=16,
        armor_type="heavy",
        strength_requirement=13,
        stealth_disadvantage=True,
        is_equipped=True,
    )


@pytest.fixture
def sample_equipment() -> EquipmentItem:
    """Create sample equipment item for testing."""
    return EquipmentItem(
        name="Rope, 50 feet",
        quantity=1,
        description="Hempen rope",
        weight=10.0,
    )


@pytest.fixture
def sample_spell() -> Spell:
    """Create a sample spell for testing."""
    return Spell(
        name="Fireball",
        level=3,
        school="evocation",
        casting_time="1 action",
        range="150 feet",
        components=["V", "S", "M"],
        duration="Instantaneous",
        description="A bright streak flashes from your pointing finger...",
        is_prepared=True,
    )


@pytest.fixture
def sample_character_sheet(
    sample_weapon: Weapon, sample_armor: Armor, sample_equipment: EquipmentItem
) -> CharacterSheet:
    """Create a sample character sheet for testing."""
    return CharacterSheet(
        name="Thorn Ironbark",
        race="Human",
        character_class="Fighter",
        level=5,
        background="Soldier",
        alignment="Lawful Good",
        experience_points=6500,
        strength=16,
        dexterity=14,
        constitution=15,
        intelligence=10,
        wisdom=12,
        charisma=8,
        armor_class=16,
        initiative=2,
        speed=30,
        hit_points_max=44,
        hit_points_current=38,
        hit_points_temp=0,
        hit_dice="5d10",
        hit_dice_remaining=5,
        saving_throw_proficiencies=["strength", "constitution"],
        skill_proficiencies=["athletics", "intimidation"],
        armor_proficiencies=["light", "medium", "heavy", "shields"],
        weapon_proficiencies=["simple", "martial"],
        languages=["Common", "Dwarvish"],
        class_features=["Second Wind", "Action Surge", "Extra Attack"],
        weapons=[sample_weapon],
        armor=sample_armor,
        equipment=[sample_equipment],
        gold=50,
        silver=25,
        copper=10,
        personality_traits="I face problems head-on.",
        ideals="Responsibility. I do what I must.",
        bonds="I fight for those who cannot fight for themselves.",
        flaws="I made a terrible mistake in battle once.",
    )


# =============================================================================
# Weapon Model Tests
# =============================================================================


class TestWeapon:
    """Tests for the Weapon model."""

    def test_valid_weapon_creation(self) -> None:
        """Test creating a valid weapon with all fields."""
        weapon = Weapon(
            name="Greatsword",
            damage_dice="2d6",
            damage_type="slashing",
            properties=["heavy", "two-handed"],
            attack_bonus=1,
            is_equipped=True,
        )
        assert weapon.name == "Greatsword"
        assert weapon.damage_dice == "2d6"
        assert weapon.damage_type == "slashing"
        assert weapon.properties == ["heavy", "two-handed"]
        assert weapon.attack_bonus == 1
        assert weapon.is_equipped is True

    def test_weapon_minimal_fields(self) -> None:
        """Test creating weapon with only required fields."""
        weapon = Weapon(name="Dagger", damage_dice="1d4")
        assert weapon.name == "Dagger"
        assert weapon.damage_dice == "1d4"
        assert weapon.damage_type == "slashing"  # default
        assert weapon.properties == []  # default
        assert weapon.attack_bonus == 0  # default
        assert weapon.is_equipped is False  # default

    def test_invalid_damage_dice_format(self) -> None:
        """Test that invalid damage dice format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Weapon(name="Broken", damage_dice="invalid")
        assert "damage_dice" in str(exc_info.value)

    def test_damage_dice_various_valid_formats(self) -> None:
        """Test various valid damage dice formats."""
        valid_formats = ["1d4", "1d6", "1d8", "1d10", "1d12", "2d6", "3d8", "10d10"]
        for dice in valid_formats:
            weapon = Weapon(name="Test", damage_dice=dice)
            assert weapon.damage_dice == dice

    def test_damage_dice_with_modifiers(self) -> None:
        """Test damage dice with +/- modifiers (magic weapons)."""
        valid_formats = ["1d8+2", "2d6+3", "1d10-1", "1d4+5"]
        for dice in valid_formats:
            weapon = Weapon(name="Magic Weapon", damage_dice=dice)
            assert weapon.damage_dice == dice

    def test_empty_name_validation(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Weapon(name="", damage_dice="1d8")
        assert "name" in str(exc_info.value)

    def test_json_serialization(self, sample_weapon: Weapon) -> None:
        """Test weapon JSON serialization."""
        json_str = sample_weapon.model_dump_json()
        data = json.loads(json_str)
        assert data["name"] == "Longsword"
        assert data["damage_dice"] == "1d8"

    def test_json_round_trip(self, sample_weapon: Weapon) -> None:
        """Test weapon JSON round-trip serialization."""
        json_str = sample_weapon.model_dump_json()
        restored = Weapon.model_validate_json(json_str)
        assert restored == sample_weapon


# =============================================================================
# Armor Model Tests
# =============================================================================


class TestArmor:
    """Tests for the Armor model."""

    def test_valid_armor_creation(self) -> None:
        """Test creating valid armor with all fields."""
        armor = Armor(
            name="Plate Armor",
            armor_class=18,
            armor_type="heavy",
            strength_requirement=15,
            stealth_disadvantage=True,
            is_equipped=True,
        )
        assert armor.name == "Plate Armor"
        assert armor.armor_class == 18
        assert armor.armor_type == "heavy"
        assert armor.strength_requirement == 15
        assert armor.stealth_disadvantage is True
        assert armor.is_equipped is True

    def test_armor_minimal_fields(self) -> None:
        """Test creating armor with only required fields."""
        armor = Armor(name="Leather Armor", armor_class=11, armor_type="light")
        assert armor.name == "Leather Armor"
        assert armor.armor_class == 11
        assert armor.armor_type == "light"
        assert armor.strength_requirement == 0  # default
        assert armor.stealth_disadvantage is False  # default
        assert armor.is_equipped is True  # default

    def test_armor_class_lower_bound(self) -> None:
        """Test armor class minimum value validation."""
        # AC can now be 0+ to support shields (+2 bonus)
        with pytest.raises(ValidationError) as exc_info:
            Armor(name="Bad Armor", armor_class=-1, armor_type="light")
        assert "armor_class" in str(exc_info.value)

    def test_armor_class_upper_bound(self) -> None:
        """Test armor class maximum value validation."""
        with pytest.raises(ValidationError) as exc_info:
            Armor(name="Super Armor", armor_class=21, armor_type="heavy")
        assert "armor_class" in str(exc_info.value)

    def test_armor_class_bounds_valid(self) -> None:
        """Test valid armor class values at boundaries."""
        armor_min = Armor(
            name="Shield", armor_class=2, armor_type="shield"
        )  # Shields use +2
        armor_max = Armor(name="Strong", armor_class=20, armor_type="heavy")
        assert armor_min.armor_class == 2
        assert armor_max.armor_class == 20

    def test_armor_type_literal(self) -> None:
        """Test armor type must be one of the allowed values."""
        with pytest.raises(ValidationError) as exc_info:
            Armor(name="Bad", armor_class=12, armor_type="invalid")  # type: ignore
        assert "armor_type" in str(exc_info.value)

    def test_valid_armor_types(self) -> None:
        """Test all valid armor types."""
        from typing import Literal, get_args

        ArmorType = Literal["light", "medium", "heavy", "shield"]
        for armor_type in get_args(ArmorType):
            armor = Armor(
                name=f"{armor_type} armor", armor_class=12, armor_type=armor_type
            )
            assert armor.armor_type == armor_type

    def test_empty_name_validation(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Armor(name="", armor_class=12, armor_type="light")
        assert "name" in str(exc_info.value)

    def test_json_serialization(self, sample_armor: Armor) -> None:
        """Test armor JSON serialization."""
        json_str = sample_armor.model_dump_json()
        data = json.loads(json_str)
        assert data["name"] == "Chain Mail"
        assert data["armor_class"] == 16

    def test_json_round_trip(self, sample_armor: Armor) -> None:
        """Test armor JSON round-trip serialization."""
        json_str = sample_armor.model_dump_json()
        restored = Armor.model_validate_json(json_str)
        assert restored == sample_armor


# =============================================================================
# EquipmentItem Model Tests
# =============================================================================


class TestEquipmentItem:
    """Tests for the EquipmentItem model."""

    def test_valid_equipment_item(self) -> None:
        """Test creating a valid equipment item."""
        item = EquipmentItem(
            name="Backpack",
            quantity=1,
            description="A leather backpack with multiple compartments",
            weight=5.0,
        )
        assert item.name == "Backpack"
        assert item.quantity == 1
        assert item.description == "A leather backpack with multiple compartments"
        assert item.weight == 5.0

    def test_equipment_minimal_fields(self) -> None:
        """Test creating equipment with only required fields."""
        item = EquipmentItem(name="Torch")
        assert item.name == "Torch"
        assert item.quantity == 1  # default
        assert item.description == ""  # default
        assert item.weight == 0.0  # default

    def test_quantity_minimum(self) -> None:
        """Test quantity must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            EquipmentItem(name="Nothing", quantity=0)
        assert "quantity" in str(exc_info.value)

    def test_quantity_negative_invalid(self) -> None:
        """Test negative quantity is invalid."""
        with pytest.raises(ValidationError) as exc_info:
            EquipmentItem(name="Negative", quantity=-1)
        assert "quantity" in str(exc_info.value)

    def test_weight_non_negative(self) -> None:
        """Test weight cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            EquipmentItem(name="Negative Weight", weight=-1.0)
        assert "weight" in str(exc_info.value)

    def test_empty_name_validation(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EquipmentItem(name="")
        assert "name" in str(exc_info.value)

    def test_json_serialization(self, sample_equipment: EquipmentItem) -> None:
        """Test equipment JSON serialization."""
        json_str = sample_equipment.model_dump_json()
        data = json.loads(json_str)
        assert data["name"] == "Rope, 50 feet"
        assert data["quantity"] == 1

    def test_json_round_trip(self, sample_equipment: EquipmentItem) -> None:
        """Test equipment JSON round-trip serialization."""
        json_str = sample_equipment.model_dump_json()
        restored = EquipmentItem.model_validate_json(json_str)
        assert restored == sample_equipment


# =============================================================================
# Spell Model Tests
# =============================================================================


class TestSpell:
    """Tests for the Spell model."""

    def test_valid_spell_creation(self) -> None:
        """Test creating a valid spell with all fields."""
        spell = Spell(
            name="Magic Missile",
            level=1,
            school="evocation",
            casting_time="1 action",
            range="120 feet",
            components=["V", "S"],
            duration="Instantaneous",
            description="You create three glowing darts of magical force.",
            is_prepared=True,
        )
        assert spell.name == "Magic Missile"
        assert spell.level == 1
        assert spell.school == "evocation"
        assert spell.components == ["V", "S"]
        assert spell.is_prepared is True

    def test_spell_minimal_fields(self) -> None:
        """Test creating spell with only required fields."""
        spell = Spell(name="Fire Bolt", level=0)
        assert spell.name == "Fire Bolt"
        assert spell.level == 0
        assert spell.school == ""  # default
        assert spell.casting_time == "1 action"  # default
        assert spell.range == "Self"  # default
        assert spell.components == []  # default
        assert spell.duration == "Instantaneous"  # default
        assert spell.description == ""  # default
        assert spell.is_prepared is True  # default

    def test_spell_level_bounds(self) -> None:
        """Test spell level must be 0-9."""
        # Valid bounds
        cantrip = Spell(name="Cantrip", level=0)
        ninth = Spell(name="Wish", level=9)
        assert cantrip.level == 0
        assert ninth.level == 9

        # Invalid: too low
        with pytest.raises(ValidationError) as exc_info:
            Spell(name="Invalid", level=-1)
        assert "level" in str(exc_info.value)

        # Invalid: too high
        with pytest.raises(ValidationError) as exc_info:
            Spell(name="Invalid", level=10)
        assert "level" in str(exc_info.value)

    def test_cantrip_is_level_zero(self) -> None:
        """Test that cantrips are represented as level 0."""
        cantrip = Spell(name="Prestidigitation", level=0, school="transmutation")
        assert cantrip.level == 0

    def test_empty_name_validation(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Spell(name="", level=1)
        assert "name" in str(exc_info.value)

    def test_json_serialization(self, sample_spell: Spell) -> None:
        """Test spell JSON serialization."""
        json_str = sample_spell.model_dump_json()
        data = json.loads(json_str)
        assert data["name"] == "Fireball"
        assert data["level"] == 3

    def test_json_round_trip(self, sample_spell: Spell) -> None:
        """Test spell JSON round-trip serialization."""
        json_str = sample_spell.model_dump_json()
        restored = Spell.model_validate_json(json_str)
        assert restored == sample_spell


# =============================================================================
# SpellSlots Model Tests
# =============================================================================


class TestSpellSlots:
    """Tests for the SpellSlots model."""

    def test_valid_spell_slots(self) -> None:
        """Test creating valid spell slots."""
        slots = SpellSlots(max=4, current=3)
        assert slots.max == 4
        assert slots.current == 3

    def test_current_cannot_exceed_max(self) -> None:
        """Test that current slots cannot exceed max."""
        with pytest.raises(ValidationError) as exc_info:
            SpellSlots(max=2, current=3)
        assert "current" in str(exc_info.value)

    def test_current_equals_max_valid(self) -> None:
        """Test that current can equal max."""
        slots = SpellSlots(max=4, current=4)
        assert slots.current == slots.max

    def test_zero_slots_valid(self) -> None:
        """Test that zero slots is valid (for exhausted casters)."""
        slots = SpellSlots(max=4, current=0)
        assert slots.current == 0

    def test_max_slot_upper_bound(self) -> None:
        """Test max slots upper bound (4 per D&D 5e rules)."""
        with pytest.raises(ValidationError) as exc_info:
            SpellSlots(max=5, current=5)
        assert "max" in str(exc_info.value)

    def test_max_slot_zero_valid(self) -> None:
        """Test max=0 is valid (non-caster at that level)."""
        slots = SpellSlots(max=0, current=0)
        assert slots.max == 0
        assert slots.current == 0

    def test_json_serialization(self) -> None:
        """Test spell slots JSON serialization."""
        slots = SpellSlots(max=4, current=2)
        json_str = slots.model_dump_json()
        data = json.loads(json_str)
        assert data["max"] == 4
        assert data["current"] == 2

    def test_json_round_trip(self) -> None:
        """Test spell slots JSON round-trip serialization."""
        slots = SpellSlots(max=3, current=1)
        json_str = slots.model_dump_json()
        restored = SpellSlots.model_validate_json(json_str)
        assert restored == slots


# =============================================================================
# DeathSaves Model Tests
# =============================================================================


class TestDeathSaves:
    """Tests for the DeathSaves model."""

    def test_default_values(self) -> None:
        """Test DeathSaves default values."""
        saves = DeathSaves()
        assert saves.successes == 0
        assert saves.failures == 0

    def test_successes_bound(self) -> None:
        """Test successes must be 0-3."""
        # Valid bounds
        saves_min = DeathSaves(successes=0)
        saves_max = DeathSaves(successes=3)
        assert saves_min.successes == 0
        assert saves_max.successes == 3

        # Invalid: too high
        with pytest.raises(ValidationError) as exc_info:
            DeathSaves(successes=4)
        assert "successes" in str(exc_info.value)

        # Invalid: negative
        with pytest.raises(ValidationError) as exc_info:
            DeathSaves(successes=-1)
        assert "successes" in str(exc_info.value)

    def test_failures_bound(self) -> None:
        """Test failures must be 0-3."""
        # Valid bounds
        saves_min = DeathSaves(failures=0)
        saves_max = DeathSaves(failures=3)
        assert saves_min.failures == 0
        assert saves_max.failures == 3

        # Invalid: too high
        with pytest.raises(ValidationError) as exc_info:
            DeathSaves(failures=4)
        assert "failures" in str(exc_info.value)

        # Invalid: negative
        with pytest.raises(ValidationError) as exc_info:
            DeathSaves(failures=-1)
        assert "failures" in str(exc_info.value)

    def test_is_stable_with_three_successes(self) -> None:
        """Test character is stable with 3 successes."""
        saves = DeathSaves(successes=3, failures=2)
        assert saves.is_stable is True
        assert saves.is_dead is False

    def test_is_stable_with_less_than_three_successes(self) -> None:
        """Test character is not stable with less than 3 successes."""
        for successes in [0, 1, 2]:
            saves = DeathSaves(successes=successes, failures=0)
            assert saves.is_stable is False

    def test_is_dead_with_three_failures(self) -> None:
        """Test character is dead with 3 failures."""
        saves = DeathSaves(successes=2, failures=3)
        assert saves.is_dead is True
        assert saves.is_stable is False

    def test_is_dead_with_less_than_three_failures(self) -> None:
        """Test character is not dead with less than 3 failures."""
        for failures in [0, 1, 2]:
            saves = DeathSaves(successes=0, failures=failures)
            assert saves.is_dead is False

    def test_json_serialization(self) -> None:
        """Test death saves JSON serialization."""
        saves = DeathSaves(successes=2, failures=1)
        json_str = saves.model_dump_json()
        data = json.loads(json_str)
        assert data["successes"] == 2
        assert data["failures"] == 1

    def test_json_round_trip(self) -> None:
        """Test death saves JSON round-trip serialization."""
        saves = DeathSaves(successes=1, failures=2)
        json_str = saves.model_dump_json()
        restored = DeathSaves.model_validate_json(json_str)
        assert restored.successes == saves.successes
        assert restored.failures == saves.failures


# =============================================================================
# CharacterSheet Basic Info Tests
# =============================================================================


class TestCharacterSheetBasicInfo:
    """Tests for CharacterSheet basic info fields."""

    def test_valid_character_creation(
        self, sample_character_sheet: CharacterSheet
    ) -> None:
        """Test creating a valid character sheet."""
        assert sample_character_sheet.name == "Thorn Ironbark"
        assert sample_character_sheet.race == "Human"
        assert sample_character_sheet.character_class == "Fighter"
        assert sample_character_sheet.level == 5
        assert sample_character_sheet.background == "Soldier"
        assert sample_character_sheet.alignment == "Lawful Good"
        assert sample_character_sheet.experience_points == 6500

    def test_level_bounds(self) -> None:
        """Test level must be 1-20."""
        # Valid bounds
        level_1 = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Fighter",
            level=1,
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=10,
            hit_points_current=10,
            hit_dice="1d10",
            hit_dice_remaining=1,
        )
        level_20 = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Fighter",
            level=20,
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=10,
            hit_points_current=10,
            hit_dice="20d10",
            hit_dice_remaining=20,
        )
        assert level_1.level == 1
        assert level_20.level == 20

        # Invalid: level 0
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                race="Human",
                character_class="Fighter",
                level=0,
                strength=10,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=10,
                hit_points_max=10,
                hit_points_current=10,
                hit_dice="1d10",
                hit_dice_remaining=0,
            )
        assert "level" in str(exc_info.value)

        # Invalid: level 21
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                race="Human",
                character_class="Fighter",
                level=21,
                strength=10,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=10,
                hit_points_max=10,
                hit_points_current=10,
                hit_dice="21d10",
                hit_dice_remaining=21,
            )
        assert "level" in str(exc_info.value)

    def test_ability_score_bounds(self) -> None:
        """Test ability scores must be 1-30."""
        # Test valid bounds for strength (representative ability)
        for score in [1, 10, 20, 30]:
            char = CharacterSheet(
                name="Test",
                race="Human",
                character_class="Fighter",
                strength=score,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=10,
                hit_points_max=10,
                hit_points_current=10,
                hit_dice="1d10",
                hit_dice_remaining=1,
            )
            assert char.strength == score

        # Invalid: score 0
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                race="Human",
                character_class="Fighter",
                strength=0,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=10,
                hit_points_max=10,
                hit_points_current=10,
                hit_dice="1d10",
                hit_dice_remaining=1,
            )
        assert "strength" in str(exc_info.value)

        # Invalid: score 31
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                race="Human",
                character_class="Fighter",
                strength=31,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=10,
                hit_points_max=10,
                hit_points_current=10,
                hit_dice="1d10",
                hit_dice_remaining=1,
            )
        assert "strength" in str(exc_info.value)

    def test_empty_name_validation(self) -> None:
        """Test that empty name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="",
                race="Human",
                character_class="Fighter",
                strength=10,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=10,
                hit_points_max=10,
                hit_points_current=10,
                hit_dice="1d10",
                hit_dice_remaining=1,
            )
        assert "name" in str(exc_info.value)

    def test_experience_points_non_negative(self) -> None:
        """Test experience points must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                race="Human",
                character_class="Fighter",
                experience_points=-100,
                strength=10,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=10,
                hit_points_max=10,
                hit_points_current=10,
                hit_dice="1d10",
                hit_dice_remaining=1,
            )
        assert "experience_points" in str(exc_info.value)


# =============================================================================
# CharacterSheet Ability Modifier Tests
# =============================================================================


class TestCharacterSheetAbilityModifiers:
    """Tests for CharacterSheet ability modifier computed properties."""

    def test_strength_modifier(self, sample_character_sheet: CharacterSheet) -> None:
        """Test strength modifier calculation."""
        # sample_character_sheet has STR 16 -> modifier (16-10)//2 = 3
        assert sample_character_sheet.strength_modifier == 3

    def test_dexterity_modifier(self, sample_character_sheet: CharacterSheet) -> None:
        """Test dexterity modifier calculation."""
        # sample_character_sheet has DEX 14 -> modifier (14-10)//2 = 2
        assert sample_character_sheet.dexterity_modifier == 2

    def test_constitution_modifier(
        self, sample_character_sheet: CharacterSheet
    ) -> None:
        """Test constitution modifier calculation."""
        # sample_character_sheet has CON 15 -> modifier (15-10)//2 = 2
        assert sample_character_sheet.constitution_modifier == 2

    def test_intelligence_modifier(
        self, sample_character_sheet: CharacterSheet
    ) -> None:
        """Test intelligence modifier calculation."""
        # sample_character_sheet has INT 10 -> modifier (10-10)//2 = 0
        assert sample_character_sheet.intelligence_modifier == 0

    def test_wisdom_modifier(self, sample_character_sheet: CharacterSheet) -> None:
        """Test wisdom modifier calculation."""
        # sample_character_sheet has WIS 12 -> modifier (12-10)//2 = 1
        assert sample_character_sheet.wisdom_modifier == 1

    def test_charisma_modifier(self, sample_character_sheet: CharacterSheet) -> None:
        """Test charisma modifier calculation."""
        # sample_character_sheet has CHA 8 -> modifier (8-10)//2 = -1
        assert sample_character_sheet.charisma_modifier == -1

    def test_modifier_at_score_10_is_zero(self) -> None:
        """Test that score 10 gives modifier 0."""
        char = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Fighter",
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=10,
            hit_points_current=10,
            hit_dice="1d10",
            hit_dice_remaining=1,
        )
        assert char.strength_modifier == 0
        assert char.dexterity_modifier == 0
        assert char.constitution_modifier == 0
        assert char.intelligence_modifier == 0
        assert char.wisdom_modifier == 0
        assert char.charisma_modifier == 0

    def test_modifier_at_score_20_is_five(self) -> None:
        """Test that score 20 gives modifier +5."""
        char = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Fighter",
            strength=20,
            dexterity=20,
            constitution=20,
            intelligence=20,
            wisdom=20,
            charisma=20,
            armor_class=10,
            hit_points_max=10,
            hit_points_current=10,
            hit_dice="1d10",
            hit_dice_remaining=1,
        )
        assert char.strength_modifier == 5
        assert char.dexterity_modifier == 5

    def test_modifier_at_score_8_is_negative_one(self) -> None:
        """Test that score 8 gives modifier -1."""
        char = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Fighter",
            strength=8,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=10,
            hit_points_current=10,
            hit_dice="1d10",
            hit_dice_remaining=1,
        )
        assert char.strength_modifier == -1

    def test_modifier_at_score_1_is_negative_five(self) -> None:
        """Test that score 1 gives modifier -5."""
        char = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Fighter",
            strength=1,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=10,
            hit_points_current=10,
            hit_dice="1d10",
            hit_dice_remaining=1,
        )
        assert char.strength_modifier == -5

    def test_modifier_at_score_30_is_ten(self) -> None:
        """Test that score 30 gives modifier +10."""
        char = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Fighter",
            strength=30,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=10,
            hit_points_current=10,
            hit_dice="1d10",
            hit_dice_remaining=1,
        )
        assert char.strength_modifier == 10

    def test_get_ability_modifier_by_name(
        self, sample_character_sheet: CharacterSheet
    ) -> None:
        """Test get_ability_modifier with full ability names."""
        assert sample_character_sheet.get_ability_modifier("strength") == 3
        assert sample_character_sheet.get_ability_modifier("dexterity") == 2
        assert sample_character_sheet.get_ability_modifier("constitution") == 2
        assert sample_character_sheet.get_ability_modifier("intelligence") == 0
        assert sample_character_sheet.get_ability_modifier("wisdom") == 1
        assert sample_character_sheet.get_ability_modifier("charisma") == -1

    def test_get_ability_modifier_case_insensitive(
        self, sample_character_sheet: CharacterSheet
    ) -> None:
        """Test get_ability_modifier is case-insensitive."""
        assert sample_character_sheet.get_ability_modifier("STRENGTH") == 3
        assert sample_character_sheet.get_ability_modifier("Strength") == 3
        assert sample_character_sheet.get_ability_modifier("STR") == 3

    def test_get_ability_modifier_short_form(
        self, sample_character_sheet: CharacterSheet
    ) -> None:
        """Test get_ability_modifier with short ability names."""
        assert sample_character_sheet.get_ability_modifier("str") == 3
        assert sample_character_sheet.get_ability_modifier("dex") == 2
        assert sample_character_sheet.get_ability_modifier("con") == 2
        assert sample_character_sheet.get_ability_modifier("int") == 0
        assert sample_character_sheet.get_ability_modifier("wis") == 1
        assert sample_character_sheet.get_ability_modifier("cha") == -1

    def test_get_ability_modifier_invalid_raises(
        self, sample_character_sheet: CharacterSheet
    ) -> None:
        """Test get_ability_modifier raises ValueError for invalid ability."""
        with pytest.raises(ValueError) as exc_info:
            sample_character_sheet.get_ability_modifier("invalid")
        assert "Unknown ability" in str(exc_info.value)

    def test_ability_modifier_table(self) -> None:
        """Test ability modifier calculation matches D&D 5e table."""
        expected_modifiers = [
            (1, -5),
            (2, -4),
            (3, -4),
            (4, -3),
            (5, -3),
            (6, -2),
            (7, -2),
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
            (19, 4),
            (20, 5),
            (21, 5),
            (22, 6),
            (23, 6),
            (24, 7),
            (25, 7),
            (26, 8),
            (27, 8),
            (28, 9),
            (29, 9),
            (30, 10),
        ]
        for score, expected_mod in expected_modifiers:
            char = CharacterSheet(
                name="Test",
                race="Human",
                character_class="Fighter",
                strength=score,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=10,
                hit_points_max=10,
                hit_points_current=10,
                hit_dice="1d10",
                hit_dice_remaining=1,
            )
            assert char.strength_modifier == expected_mod, (
                f"Score {score} expected {expected_mod}, got {char.strength_modifier}"
            )


# =============================================================================
# CharacterSheet Proficiency Bonus Tests
# =============================================================================


class TestCharacterSheetProficiencyBonus:
    """Tests for CharacterSheet proficiency bonus computed property."""

    def _make_char(self, level: int) -> CharacterSheet:
        """Helper to create a character at a specific level."""
        return CharacterSheet(
            name="Test",
            race="Human",
            character_class="Fighter",
            level=level,
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=10,
            hit_points_current=10,
            hit_dice=f"{level}d10",
            hit_dice_remaining=level,
        )

    def test_proficiency_at_level_1(self) -> None:
        """Test proficiency bonus at level 1 is +2."""
        char = self._make_char(1)
        assert char.proficiency_bonus == 2

    def test_proficiency_at_level_4(self) -> None:
        """Test proficiency bonus at level 4 is +2."""
        char = self._make_char(4)
        assert char.proficiency_bonus == 2

    def test_proficiency_at_level_5(self) -> None:
        """Test proficiency bonus at level 5 is +3."""
        char = self._make_char(5)
        assert char.proficiency_bonus == 3

    def test_proficiency_at_level_8(self) -> None:
        """Test proficiency bonus at level 8 is +3."""
        char = self._make_char(8)
        assert char.proficiency_bonus == 3

    def test_proficiency_at_level_9(self) -> None:
        """Test proficiency bonus at level 9 is +4."""
        char = self._make_char(9)
        assert char.proficiency_bonus == 4

    def test_proficiency_at_level_12(self) -> None:
        """Test proficiency bonus at level 12 is +4."""
        char = self._make_char(12)
        assert char.proficiency_bonus == 4

    def test_proficiency_at_level_13(self) -> None:
        """Test proficiency bonus at level 13 is +5."""
        char = self._make_char(13)
        assert char.proficiency_bonus == 5

    def test_proficiency_at_level_16(self) -> None:
        """Test proficiency bonus at level 16 is +5."""
        char = self._make_char(16)
        assert char.proficiency_bonus == 5

    def test_proficiency_at_level_17(self) -> None:
        """Test proficiency bonus at level 17 is +6."""
        char = self._make_char(17)
        assert char.proficiency_bonus == 6

    def test_proficiency_at_level_20(self) -> None:
        """Test proficiency bonus at level 20 is +6."""
        char = self._make_char(20)
        assert char.proficiency_bonus == 6

    def test_proficiency_bonus_all_levels(self) -> None:
        """Test proficiency bonus for all levels 1-20."""
        expected = {
            1: 2,
            2: 2,
            3: 2,
            4: 2,
            5: 3,
            6: 3,
            7: 3,
            8: 3,
            9: 4,
            10: 4,
            11: 4,
            12: 4,
            13: 5,
            14: 5,
            15: 5,
            16: 5,
            17: 6,
            18: 6,
            19: 6,
            20: 6,
        }
        for level, expected_bonus in expected.items():
            char = self._make_char(level)
            assert char.proficiency_bonus == expected_bonus, (
                f"Level {level} expected +{expected_bonus}, got +{char.proficiency_bonus}"
            )


# =============================================================================
# CharacterSheet Combat Stats Tests
# =============================================================================


class TestCharacterSheetCombat:
    """Tests for CharacterSheet combat-related fields."""

    def test_hit_points_validation(self) -> None:
        """Test hit points field constraints."""
        # Valid: current less than max
        char = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Fighter",
            level=5,
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=50,
            hit_points_current=30,
            hit_dice="5d10",
            hit_dice_remaining=5,
        )
        assert char.hit_points_max == 50
        assert char.hit_points_current == 30

    def test_hit_points_current_at_zero(self) -> None:
        """Test hit points can be zero (unconscious)."""
        char = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Fighter",
            level=5,
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=50,
            hit_points_current=0,
            hit_dice="5d10",
            hit_dice_remaining=5,
        )
        assert char.hit_points_current == 0

    def test_hit_points_temp(self) -> None:
        """Test temporary hit points."""
        char = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Fighter",
            level=5,
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=50,
            hit_points_current=50,
            hit_points_temp=10,
            hit_dice="5d10",
            hit_dice_remaining=5,
        )
        assert char.hit_points_temp == 10

    def test_hit_dice_format_validation(self) -> None:
        """Test hit dice format must be valid dice notation."""
        # Invalid format
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                race="Human",
                character_class="Fighter",
                strength=10,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=10,
                hit_points_max=10,
                hit_points_current=10,
                hit_dice="invalid",
                hit_dice_remaining=1,
            )
        assert "hit_dice" in str(exc_info.value)

    def test_hit_dice_remaining_cannot_exceed_level(self) -> None:
        """Test hit dice remaining cannot exceed level."""
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                race="Human",
                character_class="Fighter",
                level=5,
                strength=10,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=10,
                hit_points_max=10,
                hit_points_current=10,
                hit_dice="5d10",
                hit_dice_remaining=6,  # More than level 5
            )
        assert "hit_dice_remaining" in str(exc_info.value)

    def test_armor_class_minimum(self) -> None:
        """Test armor class must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                race="Human",
                character_class="Fighter",
                strength=10,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=0,
                hit_points_max=10,
                hit_points_current=10,
                hit_dice="1d10",
                hit_dice_remaining=1,
            )
        assert "armor_class" in str(exc_info.value)

    def test_hit_points_current_non_negative(self) -> None:
        """Test hit points current cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                race="Human",
                character_class="Fighter",
                strength=10,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=10,
                hit_points_max=50,
                hit_points_current=-5,
                hit_dice="1d10",
                hit_dice_remaining=1,
            )
        assert "hit_points_current" in str(exc_info.value)

    def test_hit_points_current_cannot_exceed_max_plus_temp(self) -> None:
        """Test current HP cannot exceed max HP + temp HP."""
        with pytest.raises(ValidationError) as exc_info:
            CharacterSheet(
                name="Test",
                race="Human",
                character_class="Fighter",
                strength=10,
                dexterity=10,
                constitution=10,
                intelligence=10,
                wisdom=10,
                charisma=10,
                armor_class=10,
                hit_points_max=50,
                hit_points_current=70,  # More than max + temp (50 + 0)
                hit_points_temp=0,
                hit_dice="1d10",
                hit_dice_remaining=1,
            )
        assert "hit_points_current" in str(exc_info.value)

    def test_hit_points_current_valid_with_temp_hp(self) -> None:
        """Test current HP can equal max + temp."""
        char = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Fighter",
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=50,
            hit_points_current=60,  # Valid: 50 max + 10 temp
            hit_points_temp=10,
            hit_dice="1d10",
            hit_dice_remaining=1,
        )
        assert char.hit_points_current == 60


# =============================================================================
# CharacterSheet Serialization Tests
# =============================================================================


class TestCharacterSheetSerialization:
    """Tests for CharacterSheet JSON serialization."""

    def test_model_dump_json(self, sample_character_sheet: CharacterSheet) -> None:
        """Test CharacterSheet.model_dump_json() produces valid JSON."""
        json_str = sample_character_sheet.model_dump_json()
        # Should be valid JSON
        data = json.loads(json_str)
        assert data["name"] == "Thorn Ironbark"
        assert data["level"] == 5
        assert data["strength"] == 16

    def test_model_validate_json(self, sample_character_sheet: CharacterSheet) -> None:
        """Test CharacterSheet.model_validate_json() reconstructs model."""
        json_str = sample_character_sheet.model_dump_json()
        restored = CharacterSheet.model_validate_json(json_str)
        assert restored.name == sample_character_sheet.name
        assert restored.level == sample_character_sheet.level
        assert restored.strength == sample_character_sheet.strength

    def test_round_trip_serialization(
        self, sample_character_sheet: CharacterSheet
    ) -> None:
        """Test round-trip serialization preserves all field values."""
        json_str = sample_character_sheet.model_dump_json()
        restored = CharacterSheet.model_validate_json(json_str)

        # Compare all basic fields
        assert restored.name == sample_character_sheet.name
        assert restored.race == sample_character_sheet.race
        assert restored.character_class == sample_character_sheet.character_class
        assert restored.level == sample_character_sheet.level
        assert restored.background == sample_character_sheet.background
        assert restored.alignment == sample_character_sheet.alignment
        assert restored.experience_points == sample_character_sheet.experience_points

        # Ability scores
        assert restored.strength == sample_character_sheet.strength
        assert restored.dexterity == sample_character_sheet.dexterity
        assert restored.constitution == sample_character_sheet.constitution
        assert restored.intelligence == sample_character_sheet.intelligence
        assert restored.wisdom == sample_character_sheet.wisdom
        assert restored.charisma == sample_character_sheet.charisma

        # Combat stats
        assert restored.armor_class == sample_character_sheet.armor_class
        assert restored.hit_points_max == sample_character_sheet.hit_points_max
        assert restored.hit_points_current == sample_character_sheet.hit_points_current

        # Proficiencies
        assert (
            restored.saving_throw_proficiencies
            == sample_character_sheet.saving_throw_proficiencies
        )
        assert (
            restored.skill_proficiencies == sample_character_sheet.skill_proficiencies
        )

        # Currency
        assert restored.gold == sample_character_sheet.gold
        assert restored.silver == sample_character_sheet.silver
        assert restored.copper == sample_character_sheet.copper

    def test_nested_equipment_serialization(
        self, sample_character_sheet: CharacterSheet
    ) -> None:
        """Test serialization with nested equipment models."""
        json_str = sample_character_sheet.model_dump_json()
        data = json.loads(json_str)

        # Check weapons are serialized
        assert len(data["weapons"]) == 1
        assert data["weapons"][0]["name"] == "Longsword"
        assert data["weapons"][0]["damage_dice"] == "1d8"

        # Check armor is serialized
        assert data["armor"]["name"] == "Chain Mail"
        assert data["armor"]["armor_class"] == 16

        # Check equipment is serialized
        assert len(data["equipment"]) == 1
        assert data["equipment"][0]["name"] == "Rope, 50 feet"

        # Restore and verify nested objects
        restored = CharacterSheet.model_validate_json(json_str)
        assert len(restored.weapons) == 1
        assert restored.weapons[0].name == "Longsword"
        assert restored.armor is not None
        assert restored.armor.name == "Chain Mail"

    def test_spell_slots_dict_serialization(self) -> None:
        """Test serialization with spell_slots dictionary."""
        char = CharacterSheet(
            name="Test Wizard",
            race="Human",
            character_class="Wizard",
            level=5,
            strength=8,
            dexterity=14,
            constitution=14,
            intelligence=16,
            wisdom=12,
            charisma=10,
            armor_class=12,
            hit_points_max=28,
            hit_points_current=28,
            hit_dice="5d6",
            hit_dice_remaining=5,
            spellcasting_ability="intelligence",
            spell_save_dc=14,
            spell_attack_bonus=6,
            cantrips=["Fire Bolt", "Prestidigitation", "Mage Hand"],
            spells_known=[
                Spell(name="Magic Missile", level=1, school="evocation"),
                Spell(name="Shield", level=1, school="abjuration"),
                Spell(name="Fireball", level=3, school="evocation"),
            ],
            spell_slots={
                1: SpellSlots(max=4, current=2),
                2: SpellSlots(max=3, current=3),
                3: SpellSlots(max=2, current=1),
            },
        )

        json_str = char.model_dump_json()
        data = json.loads(json_str)

        # Check spell_slots serialization
        assert "1" in data["spell_slots"]  # JSON keys are strings
        assert data["spell_slots"]["1"]["max"] == 4
        assert data["spell_slots"]["1"]["current"] == 2
        assert data["spell_slots"]["3"]["current"] == 1

        # Check round-trip
        restored = CharacterSheet.model_validate_json(json_str)
        assert 1 in restored.spell_slots
        assert restored.spell_slots[1].max == 4
        assert restored.spell_slots[1].current == 2
        assert len(restored.spells_known) == 3

    def test_serialization_with_null_armor(self) -> None:
        """Test serialization when armor is None (unarmored character)."""
        char = CharacterSheet(
            name="Test Monk",
            race="Human",
            character_class="Monk",
            level=4,
            strength=10,
            dexterity=16,
            constitution=14,
            intelligence=10,
            wisdom=16,
            charisma=8,
            armor_class=16,  # Unarmored Defense
            hit_points_max=30,
            hit_points_current=30,
            hit_dice="4d8",
            hit_dice_remaining=4,
            armor=None,  # Monks typically don't wear armor
        )

        json_str = char.model_dump_json()
        data = json.loads(json_str)
        assert data["armor"] is None

        restored = CharacterSheet.model_validate_json(json_str)
        assert restored.armor is None


# =============================================================================
# CharacterSheet Exports Tests
# =============================================================================


class TestCharacterSheetExports:
    """Tests for models.py exports."""

    def test_all_models_in_exports(self) -> None:
        """Test that all new models are in __all__ exports."""
        import models

        expected_exports = [
            "Weapon",
            "Armor",
            "EquipmentItem",
            "Spell",
            "SpellSlots",
            "DeathSaves",
            "CharacterSheet",
        ]

        for export in expected_exports:
            assert export in models.__all__, f"{export} not in models.__all__"
            assert hasattr(models, export), f"models.{export} not accessible"
