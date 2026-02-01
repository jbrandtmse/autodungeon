# Story 8.1: Character Sheet Data Model

Status: done

## Story

As a **developer**,
I want **a comprehensive Pydantic model for D&D 5e character sheets**,
so that **all character data is validated, serializable, and type-safe**.

## Acceptance Criteria

1. **Given** the models.py module
   **When** I import CharacterSheet
   **Then** it includes all D&D 5e character sheet fields as specified in the epics documentation

2. **Given** the CharacterSheet model
   **When** serialized
   **Then** it can be converted to/from JSON for persistence

3. **Given** ability scores
   **When** accessing modifiers
   **Then** computed properties return the modifier: `(score - 10) // 2`

4. **Given** proficiency bonus
   **When** calculated
   **Then** it's derived from level per D&D 5e rules: `(level - 1) // 4 + 2`

5. **Given** supporting models (Weapon, Armor, EquipmentItem, Spell, SpellSlots, DeathSaves)
   **When** imported from models.py
   **Then** they are properly defined with validation and type hints

6. **Given** a CharacterSheet instance with invalid data
   **When** I attempt to create it
   **Then** Pydantic raises a ValidationError with a clear message

## Tasks / Subtasks

- [x] Task 1: Create supporting equipment models (AC: #5)
  - [x] 1.1 Add Weapon Pydantic model with name, damage_dice, damage_type, properties, attack_bonus fields
  - [x] 1.2 Add Armor Pydantic model with name, armor_class, armor_type, stealth_disadvantage fields
  - [x] 1.3 Add EquipmentItem Pydantic model with name, quantity, description, weight fields
  - [x] 1.4 Add validation tests for equipment models

- [x] Task 2: Create spell-related models (AC: #5)
  - [x] 2.1 Add Spell Pydantic model with name, level, school, casting_time, range, components, duration, description fields
  - [x] 2.2 Add SpellSlots Pydantic model with max, current fields
  - [x] 2.3 Add validation tests for spell models

- [x] Task 3: Create DeathSaves model (AC: #5)
  - [x] 3.1 Add DeathSaves Pydantic model with successes (0-3) and failures (0-3) fields
  - [x] 3.2 Add computed property is_stable and is_dead
  - [x] 3.3 Add validation tests for DeathSaves

- [x] Task 4: Create CharacterSheet model with basic info (AC: #1, #6)
  - [x] 4.1 Add basic info fields: name, race, character_class, level, background, alignment, experience_points
  - [x] 4.2 Add ability score fields: strength, dexterity, constitution, intelligence, wisdom, charisma
  - [x] 4.3 Add field validators for level (1-20), ability scores (1-30), experience_points (>= 0)

- [x] Task 5: Add combat stats to CharacterSheet (AC: #1)
  - [x] 5.1 Add combat fields: armor_class, initiative, speed, hit_points_max, hit_points_current, hit_points_temp, hit_dice, hit_dice_remaining
  - [x] 5.2 Add validation for hit_points fields (non-negative, current <= max + temp)

- [x] Task 6: Add proficiencies and skills to CharacterSheet (AC: #1)
  - [x] 6.1 Add saving_throw_proficiencies as list[str]
  - [x] 6.2 Add skill_proficiencies and skill_expertise as list[str]
  - [x] 6.3 Add armor_proficiencies, weapon_proficiencies, tool_proficiencies, languages as list[str]

- [x] Task 7: Add features and traits to CharacterSheet (AC: #1)
  - [x] 7.1 Add class_features, racial_traits, feats as list[str]

- [x] Task 8: Add equipment and inventory to CharacterSheet (AC: #1)
  - [x] 8.1 Add weapons as list[Weapon]
  - [x] 8.2 Add armor as Optional[Armor]
  - [x] 8.3 Add equipment as list[EquipmentItem]
  - [x] 8.4 Add currency: gold, silver, copper as int fields

- [x] Task 9: Add spellcasting to CharacterSheet (AC: #1)
  - [x] 9.1 Add spellcasting_ability as Optional[str]
  - [x] 9.2 Add spell_save_dc and spell_attack_bonus as Optional[int]
  - [x] 9.3 Add cantrips as list[str], spells_known as list[Spell]
  - [x] 9.4 Add spell_slots as dict[int, SpellSlots] (level -> slots)

- [x] Task 10: Add personality section to CharacterSheet (AC: #1)
  - [x] 10.1 Add personality_traits, ideals, bonds, flaws, backstory as str fields

- [x] Task 11: Add conditions and status to CharacterSheet (AC: #1)
  - [x] 11.1 Add conditions as list[str]
  - [x] 11.2 Add death_saves as DeathSaves with default factory

- [x] Task 12: Add computed properties for ability modifiers (AC: #3)
  - [x] 12.1 Add @property for strength_modifier: `(strength - 10) // 2`
  - [x] 12.2 Add @property for dexterity_modifier, constitution_modifier, intelligence_modifier, wisdom_modifier, charisma_modifier
  - [x] 12.3 Add helper method get_ability_modifier(ability_name: str) -> int

- [x] Task 13: Add computed property for proficiency bonus (AC: #4)
  - [x] 13.1 Add @property proficiency_bonus: `(level - 1) // 4 + 2`
  - [x] 13.2 Write tests verifying proficiency bonus at levels 1-4 (2), 5-8 (3), 9-12 (4), 13-16 (5), 17-20 (6)

- [x] Task 14: Add JSON serialization tests (AC: #2)
  - [x] 14.1 Test CharacterSheet.model_dump_json() produces valid JSON
  - [x] 14.2 Test CharacterSheet.model_validate_json(json_str) reconstructs model
  - [x] 14.3 Test round-trip serialization preserves all field values
  - [x] 14.4 Test serialization with nested equipment models

- [x] Task 15: Update models.py exports and run quality checks
  - [x] 15.1 Add all new models to __all__ exports
  - [x] 15.2 Run ruff check and fix any lint errors
  - [x] 15.3 Run ruff format
  - [x] 15.4 Run pyright and address type errors

## Dev Notes

### Implementation Strategy

This story creates the foundational data model for D&D 5e character sheets. The CharacterSheet model will be used by:
- Story 8.2: Character sheet viewer UI
- Story 8.3: Character sheet context injection for agents
- Story 8.4: DM tool calls for sheet updates
- Story 8.5: Sheet change notifications

All models follow existing patterns in models.py with Pydantic v2 validation.

### Supporting Models (Add to models.py)

**Weapon Model:**

```python
class Weapon(BaseModel):
    """A weapon in character inventory.

    Attributes:
        name: Weapon name (e.g., "Longsword").
        damage_dice: Damage dice notation (e.g., "1d8").
        damage_type: Type of damage (e.g., "slashing", "piercing", "bludgeoning").
        properties: List of weapon properties (e.g., ["versatile", "finesse"]).
        attack_bonus: Additional attack bonus from magic or other sources.
        is_equipped: Whether the weapon is currently equipped.
    """
    name: str = Field(..., min_length=1, description="Weapon name")
    damage_dice: str = Field(..., pattern=r"^\d+d\d+$", description="Damage dice notation")
    damage_type: str = Field(default="slashing", description="Damage type")
    properties: list[str] = Field(default_factory=list, description="Weapon properties")
    attack_bonus: int = Field(default=0, description="Magic/other attack bonus")
    is_equipped: bool = Field(default=False, description="Whether weapon is equipped")
```

**Armor Model:**

```python
class Armor(BaseModel):
    """Armor worn by a character.

    Attributes:
        name: Armor name (e.g., "Chain Mail").
        armor_class: Base AC provided by armor.
        armor_type: Category (light, medium, heavy, shield).
        strength_requirement: Minimum STR required (0 if none).
        stealth_disadvantage: Whether armor imposes disadvantage on Stealth.
        is_equipped: Whether the armor is currently worn.
    """
    name: str = Field(..., min_length=1, description="Armor name")
    armor_class: int = Field(..., ge=10, le=20, description="Base AC provided")
    armor_type: Literal["light", "medium", "heavy", "shield"] = Field(..., description="Armor category")
    strength_requirement: int = Field(default=0, ge=0, description="Minimum STR required")
    stealth_disadvantage: bool = Field(default=False, description="Imposes Stealth disadvantage")
    is_equipped: bool = Field(default=True, description="Whether armor is worn")
```

**EquipmentItem Model:**

```python
class EquipmentItem(BaseModel):
    """A non-weapon, non-armor item in inventory.

    Attributes:
        name: Item name (e.g., "Rope, 50 feet").
        quantity: Number of this item (default 1).
        description: Optional description or notes.
        weight: Weight in pounds (optional).
    """
    name: str = Field(..., min_length=1, description="Item name")
    quantity: int = Field(default=1, ge=1, description="Quantity")
    description: str = Field(default="", description="Item description")
    weight: float = Field(default=0.0, ge=0, description="Weight in pounds")
```

**Spell Model:**

```python
class Spell(BaseModel):
    """A spell known or prepared by a character.

    Attributes:
        name: Spell name (e.g., "Fireball").
        level: Spell level (0 for cantrips, 1-9 for leveled spells).
        school: School of magic (e.g., "evocation", "abjuration").
        casting_time: Time required (e.g., "1 action", "1 minute").
        range: Spell range (e.g., "120 feet", "Self").
        components: Required components (e.g., ["V", "S", "M"]).
        duration: How long effect lasts (e.g., "Instantaneous", "1 hour").
        description: Brief spell description.
        is_prepared: Whether spell is currently prepared (for prepared casters).
    """
    name: str = Field(..., min_length=1, description="Spell name")
    level: int = Field(..., ge=0, le=9, description="Spell level (0 = cantrip)")
    school: str = Field(default="", description="School of magic")
    casting_time: str = Field(default="1 action", description="Casting time")
    range: str = Field(default="Self", description="Spell range")
    components: list[str] = Field(default_factory=list, description="V/S/M components")
    duration: str = Field(default="Instantaneous", description="Duration")
    description: str = Field(default="", description="Spell description")
    is_prepared: bool = Field(default=True, description="Whether prepared")
```

**SpellSlots Model:**

```python
class SpellSlots(BaseModel):
    """Spell slot tracking for a single spell level.

    Attributes:
        max: Maximum number of slots at this level.
        current: Current available slots (may be less if expended).
    """
    max: int = Field(..., ge=0, le=4, description="Maximum slots")
    current: int = Field(..., ge=0, description="Current available slots")

    @field_validator("current")
    @classmethod
    def current_not_exceeds_max(cls, v: int, info: ValidationInfo) -> int:
        """Ensure current slots don't exceed max."""
        max_val = info.data.get("max", 4)
        if v > max_val:
            raise ValueError(f"current ({v}) cannot exceed max ({max_val})")
        return v
```

**DeathSaves Model:**

```python
class DeathSaves(BaseModel):
    """Death saving throw tracking.

    Attributes:
        successes: Number of successful death saves (0-3).
        failures: Number of failed death saves (0-3).
    """
    successes: int = Field(default=0, ge=0, le=3, description="Successful saves")
    failures: int = Field(default=0, ge=0, le=3, description="Failed saves")

    @property
    def is_stable(self) -> bool:
        """Character stabilized with 3 successes."""
        return self.successes >= 3

    @property
    def is_dead(self) -> bool:
        """Character died with 3 failures."""
        return self.failures >= 3
```

### CharacterSheet Model (Full Implementation)

```python
class CharacterSheet(BaseModel):
    """Complete D&D 5e character sheet with all standard fields.

    This model represents a full player character sheet including
    basic info, abilities, combat stats, proficiencies, equipment,
    spells, and personality traits.

    Story 8.1: Character Sheet Data Model.
    FRs: FR60, FR61, FR62, FR65, FR66.

    Attributes:
        (See individual field descriptions below)
    """

    # ==========================================================================
    # Basic Info
    # ==========================================================================
    name: str = Field(..., min_length=1, description="Character name")
    race: str = Field(..., min_length=1, description="Character race")
    character_class: str = Field(..., min_length=1, description="Character class")
    level: int = Field(default=1, ge=1, le=20, description="Character level (1-20)")
    background: str = Field(default="", description="Character background")
    alignment: str = Field(default="", description="Alignment (e.g., Neutral Good)")
    experience_points: int = Field(default=0, ge=0, description="XP total")

    # ==========================================================================
    # Ability Scores (raw scores, modifiers computed)
    # ==========================================================================
    strength: int = Field(..., ge=1, le=30, description="STR score")
    dexterity: int = Field(..., ge=1, le=30, description="DEX score")
    constitution: int = Field(..., ge=1, le=30, description="CON score")
    intelligence: int = Field(..., ge=1, le=30, description="INT score")
    wisdom: int = Field(..., ge=1, le=30, description="WIS score")
    charisma: int = Field(..., ge=1, le=30, description="CHA score")

    # ==========================================================================
    # Combat Stats
    # ==========================================================================
    armor_class: int = Field(..., ge=1, description="Armor Class")
    initiative: int = Field(default=0, description="Initiative modifier")
    speed: int = Field(default=30, ge=0, description="Speed in feet")
    hit_points_max: int = Field(..., ge=1, description="Maximum HP")
    hit_points_current: int = Field(..., description="Current HP")
    hit_points_temp: int = Field(default=0, ge=0, description="Temporary HP")
    hit_dice: str = Field(..., pattern=r"^\d+d\d+$", description="Hit dice (e.g., 5d10)")
    hit_dice_remaining: int = Field(..., ge=0, description="Remaining hit dice")

    # ==========================================================================
    # Saving Throws
    # ==========================================================================
    saving_throw_proficiencies: list[str] = Field(
        default_factory=list,
        description="Abilities proficient in saves (e.g., ['strength', 'constitution'])"
    )

    # ==========================================================================
    # Skills
    # ==========================================================================
    skill_proficiencies: list[str] = Field(
        default_factory=list,
        description="Skills with proficiency"
    )
    skill_expertise: list[str] = Field(
        default_factory=list,
        description="Skills with expertise (double proficiency)"
    )

    # ==========================================================================
    # Proficiencies
    # ==========================================================================
    armor_proficiencies: list[str] = Field(
        default_factory=list,
        description="Armor types proficient with"
    )
    weapon_proficiencies: list[str] = Field(
        default_factory=list,
        description="Weapon types proficient with"
    )
    tool_proficiencies: list[str] = Field(
        default_factory=list,
        description="Tools proficient with"
    )
    languages: list[str] = Field(
        default_factory=list,
        description="Languages known"
    )

    # ==========================================================================
    # Features & Traits
    # ==========================================================================
    class_features: list[str] = Field(
        default_factory=list,
        description="Class features (e.g., Second Wind, Sneak Attack)"
    )
    racial_traits: list[str] = Field(
        default_factory=list,
        description="Racial traits (e.g., Darkvision, Fey Ancestry)"
    )
    feats: list[str] = Field(
        default_factory=list,
        description="Feats taken"
    )

    # ==========================================================================
    # Equipment & Inventory
    # ==========================================================================
    weapons: list[Weapon] = Field(
        default_factory=list,
        description="Weapons in inventory"
    )
    armor: Armor | None = Field(
        default=None,
        description="Armor worn (None if unarmored)"
    )
    equipment: list[EquipmentItem] = Field(
        default_factory=list,
        description="Other equipment and items"
    )
    gold: int = Field(default=0, ge=0, description="Gold pieces")
    silver: int = Field(default=0, ge=0, description="Silver pieces")
    copper: int = Field(default=0, ge=0, description="Copper pieces")

    # ==========================================================================
    # Spellcasting (optional, None for non-casters)
    # ==========================================================================
    spellcasting_ability: str | None = Field(
        default=None,
        description="Spellcasting ability (e.g., 'intelligence', 'wisdom', 'charisma')"
    )
    spell_save_dc: int | None = Field(
        default=None,
        ge=1,
        description="Spell save DC"
    )
    spell_attack_bonus: int | None = Field(
        default=None,
        description="Spell attack modifier"
    )
    cantrips: list[str] = Field(
        default_factory=list,
        description="Known cantrip names"
    )
    spells_known: list[Spell] = Field(
        default_factory=list,
        description="Full spell data for known/prepared spells"
    )
    spell_slots: dict[int, SpellSlots] = Field(
        default_factory=dict,
        description="Spell slots by level (1-9)"
    )

    # ==========================================================================
    # Personality
    # ==========================================================================
    personality_traits: str = Field(default="", description="Personality traits")
    ideals: str = Field(default="", description="Ideals")
    bonds: str = Field(default="", description="Bonds")
    flaws: str = Field(default="", description="Flaws")
    backstory: str = Field(default="", description="Character backstory")

    # ==========================================================================
    # Conditions & Status
    # ==========================================================================
    conditions: list[str] = Field(
        default_factory=list,
        description="Active conditions (poisoned, exhausted, etc.)"
    )
    death_saves: DeathSaves = Field(
        default_factory=DeathSaves,
        description="Death saving throw status"
    )

    # ==========================================================================
    # Computed Properties
    # ==========================================================================

    @property
    def strength_modifier(self) -> int:
        """Calculate STR modifier from score."""
        return (self.strength - 10) // 2

    @property
    def dexterity_modifier(self) -> int:
        """Calculate DEX modifier from score."""
        return (self.dexterity - 10) // 2

    @property
    def constitution_modifier(self) -> int:
        """Calculate CON modifier from score."""
        return (self.constitution - 10) // 2

    @property
    def intelligence_modifier(self) -> int:
        """Calculate INT modifier from score."""
        return (self.intelligence - 10) // 2

    @property
    def wisdom_modifier(self) -> int:
        """Calculate WIS modifier from score."""
        return (self.wisdom - 10) // 2

    @property
    def charisma_modifier(self) -> int:
        """Calculate CHA modifier from score."""
        return (self.charisma - 10) // 2

    @property
    def proficiency_bonus(self) -> int:
        """Calculate proficiency bonus from level per D&D 5e rules.

        Levels 1-4: +2
        Levels 5-8: +3
        Levels 9-12: +4
        Levels 13-16: +5
        Levels 17-20: +6
        """
        return (self.level - 1) // 4 + 2

    def get_ability_modifier(self, ability: str) -> int:
        """Get modifier for a named ability.

        Args:
            ability: Ability name (strength, dexterity, etc.)

        Returns:
            The ability modifier.

        Raises:
            ValueError: If ability name is not recognized.
        """
        ability_lower = ability.lower()
        abilities = {
            "strength": self.strength_modifier,
            "dexterity": self.dexterity_modifier,
            "constitution": self.constitution_modifier,
            "intelligence": self.intelligence_modifier,
            "wisdom": self.wisdom_modifier,
            "charisma": self.charisma_modifier,
            # Short forms
            "str": self.strength_modifier,
            "dex": self.dexterity_modifier,
            "con": self.constitution_modifier,
            "int": self.intelligence_modifier,
            "wis": self.wisdom_modifier,
            "cha": self.charisma_modifier,
        }
        if ability_lower not in abilities:
            raise ValueError(f"Unknown ability: {ability}")
        return abilities[ability_lower]

    @field_validator("hit_dice_remaining")
    @classmethod
    def hit_dice_remaining_valid(cls, v: int, info: ValidationInfo) -> int:
        """Ensure remaining hit dice doesn't exceed level."""
        level = info.data.get("level", 1)
        if v > level:
            raise ValueError(
                f"hit_dice_remaining ({v}) cannot exceed level ({level})"
            )
        return v
```

### D&D 5e Reference Data

**Standard Ability Score Modifiers:**
| Score | Modifier |
|-------|----------|
| 1 | -5 |
| 2-3 | -4 |
| 4-5 | -3 |
| 6-7 | -2 |
| 8-9 | -1 |
| 10-11 | 0 |
| 12-13 | +1 |
| 14-15 | +2 |
| 16-17 | +3 |
| 18-19 | +4 |
| 20-21 | +5 |
| 22-23 | +6 |
| 24-25 | +7 |
| 26-27 | +8 |
| 28-29 | +9 |
| 30 | +10 |

**Proficiency Bonus by Level:**
| Levels | Bonus |
|--------|-------|
| 1-4 | +2 |
| 5-8 | +3 |
| 9-12 | +4 |
| 13-16 | +5 |
| 17-20 | +6 |

**Standard Skills (18):**
- STR: Athletics
- DEX: Acrobatics, Sleight of Hand, Stealth
- INT: Arcana, History, Investigation, Nature, Religion
- WIS: Animal Handling, Insight, Medicine, Perception, Survival
- CHA: Deception, Intimidation, Performance, Persuasion

**Conditions (D&D 5e Standard):**
- Blinded, Charmed, Deafened, Exhausted, Frightened, Grappled
- Incapacitated, Invisible, Paralyzed, Petrified, Poisoned
- Prone, Restrained, Stunned, Unconscious

### Architecture Compliance

| Pattern | Compliance | Notes |
|---------|------------|-------|
| Pydantic models in models.py | YES | All new models go in models.py |
| Model naming (no suffix) | YES | `CharacterSheet`, not `CharacterSheetModel` |
| Field validators | YES | Using @field_validator for constraints |
| Type hints | YES | All fields have proper type hints |
| Serialization | YES | Pydantic v2 model_dump_json/model_validate_json |
| __all__ exports | YES | Add all new models to exports |

### Testing Strategy

**Unit Tests (pytest):**

```python
# tests/test_story_8_1_character_sheet.py

class TestWeapon:
    def test_valid_weapon_creation(self): ...
    def test_invalid_damage_dice_format(self): ...
    def test_empty_name_validation(self): ...
    def test_json_serialization(self): ...

class TestArmor:
    def test_valid_armor_creation(self): ...
    def test_armor_class_bounds(self): ...
    def test_armor_type_literal(self): ...

class TestEquipmentItem:
    def test_valid_equipment_item(self): ...
    def test_quantity_minimum(self): ...

class TestSpell:
    def test_valid_spell_creation(self): ...
    def test_spell_level_bounds(self): ...
    def test_cantrip_is_level_zero(self): ...

class TestSpellSlots:
    def test_valid_spell_slots(self): ...
    def test_current_cannot_exceed_max(self): ...

class TestDeathSaves:
    def test_default_values(self): ...
    def test_successes_bound(self): ...
    def test_failures_bound(self): ...
    def test_is_stable_with_three_successes(self): ...
    def test_is_dead_with_three_failures(self): ...

class TestCharacterSheetBasicInfo:
    def test_valid_character_creation(self): ...
    def test_level_bounds(self): ...
    def test_ability_score_bounds(self): ...
    def test_empty_name_validation(self): ...

class TestCharacterSheetAbilityModifiers:
    def test_strength_modifier(self): ...
    def test_dexterity_modifier(self): ...
    def test_constitution_modifier(self): ...
    def test_intelligence_modifier(self): ...
    def test_wisdom_modifier(self): ...
    def test_charisma_modifier(self): ...
    def test_modifier_at_score_10_is_zero(self): ...
    def test_modifier_at_score_20_is_five(self): ...
    def test_modifier_at_score_8_is_negative_one(self): ...
    def test_get_ability_modifier_by_name(self): ...
    def test_get_ability_modifier_short_form(self): ...
    def test_get_ability_modifier_invalid_raises(self): ...

class TestCharacterSheetProficiencyBonus:
    def test_proficiency_at_level_1(self): ...
    def test_proficiency_at_level_4(self): ...
    def test_proficiency_at_level_5(self): ...
    def test_proficiency_at_level_8(self): ...
    def test_proficiency_at_level_9(self): ...
    def test_proficiency_at_level_12(self): ...
    def test_proficiency_at_level_13(self): ...
    def test_proficiency_at_level_16(self): ...
    def test_proficiency_at_level_17(self): ...
    def test_proficiency_at_level_20(self): ...

class TestCharacterSheetCombat:
    def test_hit_points_validation(self): ...
    def test_hit_dice_format_validation(self): ...
    def test_hit_dice_remaining_cannot_exceed_level(self): ...

class TestCharacterSheetSerialization:
    def test_model_dump_json(self): ...
    def test_model_validate_json(self): ...
    def test_round_trip_serialization(self): ...
    def test_nested_equipment_serialization(self): ...
    def test_spell_slots_dict_serialization(self): ...

class TestCharacterSheetExports:
    def test_all_models_in_exports(self): ...
```

### Files to Modify

| File | Changes |
|------|---------|
| `models.py` | Add Weapon, Armor, EquipmentItem, Spell, SpellSlots, DeathSaves, CharacterSheet models. Add all to __all__ exports. |

### Files to Create

| File | Purpose |
|------|---------|
| `tests/test_story_8_1_character_sheet.py` | Comprehensive test suite for all character sheet models |

### Edge Cases

1. **Non-caster characters** - spellcasting_ability is None, spell_slots empty
2. **Unarmored characters** - armor is None, AC calculated from DEX + other sources
3. **Level 1 characters** - hit_dice_remaining should equal 1
4. **Maximum stats** - ability scores can reach 30 with magic items
5. **Negative HP not tracked** - hit_points_current can be 0, death_saves track unconscious state
6. **Empty proficiency lists** - Valid for some builds (e.g., languages: [])
7. **Multiclass characters** - Out of scope for MVP, single class assumed

### What This Story Implements

1. **Supporting equipment models** - Weapon, Armor, EquipmentItem, Spell, SpellSlots, DeathSaves
2. **CharacterSheet Pydantic model** - All D&D 5e standard fields
3. **Computed ability modifiers** - Properties for each ability's modifier
4. **Computed proficiency bonus** - Property based on level
5. **JSON serialization** - Full round-trip capability
6. **Validation** - Level bounds, ability score bounds, hit dice format

### What This Story Does NOT Implement

- Character sheet viewer UI (Story 8.2)
- Context injection for agents (Story 8.3)
- DM tool for sheet updates (Story 8.4)
- Sheet change notifications (Story 8.5)
- Multiclass support (future enhancement)
- Auto-calculation of derived stats like AC from armor (future enhancement)

### Dependencies

- Story 1.2 (Core Game State Models) - COMPLETE
- models.py Pydantic patterns - EXISTS

### FR/NFR Coverage

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| FR60 | Each PC has complete D&D 5e character sheet | CharacterSheet model with all fields |
| FR61 | Sheets include spells, spell slots, class features | spells_known, spell_slots, class_features fields |
| FR62 | Sheets include personality traits, ideals, bonds, flaws | personality_traits, ideals, bonds, flaws, backstory fields |
| FR65 | Character sheet data can be injected into agent context | Model provides JSON serialization for context building (implemented in 8.3) |

### References

- [Source: planning-artifacts/architecture.md#v1.1 Extension Architecture] - CharacterSheet model skeleton
- [Source: planning-artifacts/epics-v1.1.md#Story 8.1] - Detailed story requirements and acceptance criteria
- [Source: planning-artifacts/prd.md#FR60-FR66] - Character sheet functional requirements
- [Source: models.py] - Existing Pydantic patterns and __all__ exports

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- All 7 character sheet models implemented: Weapon, Armor, EquipmentItem, Spell, SpellSlots, DeathSaves, CharacterSheet
- Computed properties for ability modifiers and proficiency bonus follow D&D 5e rules exactly
- JSON serialization round-trip fully tested
- 98 tests covering all validation, serialization, and computed properties

### File List

| File | Changes |
|------|---------|
| `models.py` | Added Weapon, Armor, EquipmentItem, Spell, SpellSlots, DeathSaves, CharacterSheet models (lines 574-954). Added model_validator import. All models added to __all__ exports. |
| `tests/test_story_8_1_character_sheet.py` | New file - 98 comprehensive tests covering all models, validation, computed properties, and serialization |

---

## Senior Developer Review (AI)

**Review Date:** 2026-02-01
**Reviewer:** Claude Opus 4.5 (Adversarial Code Review)

### Review Summary

**Issues Found:** 4 HIGH, 2 MEDIUM, 2 LOW (total 8 issues)
**Issues Fixed:** 4 HIGH, 2 MEDIUM (6 issues auto-fixed)
**Outcome:** APPROVED - All HIGH and MEDIUM issues resolved

### Issues Identified and Resolutions

#### HIGH Severity (All Fixed)

1. **[FIXED] Missing validation - hit_points_current could be negative**
   - D&D 5e: HP can't go negative (you die at 0 or fall unconscious)
   - Original: `hit_points_current: int = Field(..., description="Current HP")` - no lower bound
   - Fix: Added `ge=0` constraint to hit_points_current field

2. **[FIXED] Missing validation - hit_points_current > hit_points_max + hit_points_temp**
   - Story task 5.2 specified: "validation for hit_points fields (non-negative, current <= max + temp)"
   - This cross-field validation was NOT implemented
   - Fix: Added `@model_validator(mode="after")` to validate this constraint

3. **[FIXED] Tasks marked incomplete but implementation done**
   - All 15 tasks were unchecked `[ ]` but implementation was complete
   - Fix: Updated all tasks to `[x]` to reflect actual completion state

4. **[FIXED] Empty Dev Agent Record - File List**
   - Story's File List section was empty, violating transparency requirements
   - Fix: Populated File List with actual modified files

#### MEDIUM Severity (All Fixed)

5. **[FIXED] Armor.armor_class bounds too restrictive for shields**
   - Original: `ge=10, le=20` - shields provide +2 bonus, not base AC
   - Fix: Changed to `ge=0, le=20` with updated description
   - Updated tests to match new bounds

6. **[FIXED] Weapon.damage_dice pattern too restrictive**
   - Original: `r"^\d+d\d+$"` only matches simple dice
   - D&D 5e: Magic weapons often have modifiers (e.g., "1d8+2")
   - Fix: Extended pattern to `r"^\d+d\d+([+-]\d+)?$"`
   - Added test for damage dice with modifiers

#### LOW Severity (Documented Only)

7. **[NOT FIXED] Spell.school could use Literal validation**
   - D&D 5e has exactly 8 schools of magic
   - Current implementation uses `str` for flexibility
   - Decision: Keep as-is for flexibility with homebrew content

8. **[NOT FIXED] Test file has extensive boilerplate**
   - Many tests create full CharacterSheet with same fields
   - Could use helper fixtures more extensively
   - Decision: Tests are comprehensive and correct; not blocking

### Test Results

```
98 passed in 0.26s
```

### Quality Checks

- **ruff check**: All checks passed
- **ruff format**: 2 files reformatted
- **pyright**: 0 errors, 0 warnings (after fixing type annotations in tests)

### AC Validation

| AC | Status | Evidence |
|----|--------|----------|
| AC1 - CharacterSheet includes all D&D 5e fields | PASS | models.py:719-866 |
| AC2 - JSON serialization round-trip | PASS | Tests: TestCharacterSheetSerialization (6 tests) |
| AC3 - Ability modifiers: (score - 10) // 2 | PASS | models.py:872-900, test_ability_modifier_table |
| AC4 - Proficiency bonus: (level - 1) // 4 + 2 | PASS | models.py:902-912, test_proficiency_bonus_all_levels |
| AC5 - Supporting models defined | PASS | Weapon, Armor, EquipmentItem, Spell, SpellSlots, DeathSaves |
| AC6 - ValidationError for invalid data | PASS | 30+ validation tests |

### Final Status: APPROVED FOR MERGE
