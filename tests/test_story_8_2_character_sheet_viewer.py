"""Tests for Story 8.2: Character Sheet Viewer UI.

This module tests character sheet viewer functions including:
- create_sample_character_sheet() factory function
- HP color coding logic (get_hp_color)
- HP bar HTML generation (render_hp_bar_html)
- Skill modifier calculation (calculate_skill_modifier)
- Spell slot visualization (render_spell_slots_html)
- HTML safety/escaping

Tests follow TDD approach - written before implementation.
"""

import pytest

from models import CharacterSheet, Spell, SpellSlots

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def fighter_sheet() -> CharacterSheet:
    """Create a sample Fighter character sheet for testing."""
    return CharacterSheet(
        name="Theron Ironforge",
        race="Human",
        character_class="Fighter",
        level=5,
        background="Soldier",
        alignment="Lawful Good",
        strength=16,
        dexterity=14,
        constitution=15,
        intelligence=10,
        wisdom=12,
        charisma=8,
        armor_class=18,
        initiative=2,
        speed=30,
        hit_points_max=44,
        hit_points_current=38,
        hit_dice="5d10",
        hit_dice_remaining=5,
        saving_throw_proficiencies=["strength", "constitution"],
        skill_proficiencies=["Athletics", "Intimidation", "Perception"],
        skill_expertise=[],
        class_features=["Second Wind", "Action Surge", "Extra Attack"],
        racial_traits=["Bonus Feat", "Bonus Skill"],
        personality_traits="I face problems head-on.",
        ideals="Responsibility. I do what I must.",
        bonds="I fight for those who cannot fight for themselves.",
        flaws="I made a terrible mistake in battle once.",
    )


@pytest.fixture
def wizard_sheet() -> CharacterSheet:
    """Create a sample Wizard character sheet with spellcasting."""
    return CharacterSheet(
        name="Elara Moonshadow",
        race="Elf",
        character_class="Wizard",
        level=5,
        background="Sage",
        alignment="Neutral Good",
        strength=8,
        dexterity=14,
        constitution=12,
        intelligence=16,
        wisdom=14,
        charisma=10,
        armor_class=12,
        initiative=2,
        speed=30,
        hit_points_max=27,
        hit_points_current=20,
        hit_dice="5d6",
        hit_dice_remaining=3,
        saving_throw_proficiencies=["intelligence", "wisdom"],
        skill_proficiencies=["Arcana", "History", "Investigation"],
        skill_expertise=[],
        spellcasting_ability="intelligence",
        spell_save_dc=14,
        spell_attack_bonus=6,
        cantrips=["Fire Bolt", "Light", "Mage Hand"],
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
        class_features=["Arcane Recovery", "Arcane Tradition"],
        racial_traits=["Darkvision", "Fey Ancestry", "Trance"],
    )


@pytest.fixture
def rogue_sheet() -> CharacterSheet:
    """Create a sample Rogue character sheet with expertise."""
    return CharacterSheet(
        name="Shadowmere",
        race="Halfling",
        character_class="Rogue",
        level=5,
        background="Criminal",
        alignment="Chaotic Neutral",
        strength=10,
        dexterity=16,
        constitution=12,
        intelligence=14,
        wisdom=12,
        charisma=14,
        armor_class=14,
        initiative=3,
        speed=25,
        hit_points_max=33,
        hit_points_current=33,
        hit_dice="5d8",
        hit_dice_remaining=5,
        saving_throw_proficiencies=["dexterity", "intelligence"],
        skill_proficiencies=["Stealth", "Sleight of Hand", "Thieves' Tools"],
        skill_expertise=["Stealth", "Thieves' Tools"],
        class_features=["Sneak Attack", "Cunning Action", "Uncanny Dodge"],
        racial_traits=["Lucky", "Brave", "Nimble"],
    )


# =============================================================================
# Sample Character Sheet Factory Tests
# =============================================================================


class TestCreateSampleCharacterSheet:
    """Tests for create_sample_character_sheet factory function."""

    def test_create_fighter_sheet(self) -> None:
        """Test creating a sample Fighter sheet."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Fighter", "Test Fighter")
        assert sheet.name == "Test Fighter"
        assert sheet.character_class == "Fighter"
        assert sheet.level == 5
        assert sheet.strength >= 14  # Fighters should have decent STR
        assert isinstance(sheet, CharacterSheet)

    def test_create_rogue_sheet(self) -> None:
        """Test creating a sample Rogue sheet."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Rogue", "Test Rogue")
        assert sheet.name == "Test Rogue"
        assert sheet.character_class == "Rogue"
        assert sheet.dexterity >= 14  # Rogues should have decent DEX
        assert "Stealth" in sheet.skill_proficiencies

    def test_create_wizard_sheet(self) -> None:
        """Test creating a sample Wizard sheet."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Wizard", "Test Wizard")
        assert sheet.name == "Test Wizard"
        assert sheet.character_class == "Wizard"
        assert sheet.intelligence >= 14  # Wizards should have decent INT
        assert sheet.spellcasting_ability == "intelligence"
        assert len(sheet.cantrips) > 0

    def test_create_cleric_sheet(self) -> None:
        """Test creating a sample Cleric sheet."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Cleric", "Test Cleric")
        assert sheet.name == "Test Cleric"
        assert sheet.character_class == "Cleric"
        assert sheet.wisdom >= 14  # Clerics should have decent WIS
        assert sheet.spellcasting_ability == "wisdom"

    def test_create_unknown_class_defaults_to_fighter(self) -> None:
        """Test creating a sheet for unknown class defaults to Fighter stats."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("UnknownClass", "Test Unknown")
        assert sheet.name == "Test Unknown"
        assert sheet.character_class == "UnknownClass"
        # Should use Fighter-like stats as fallback
        assert sheet.strength >= 14

    def test_sample_sheet_is_valid(self) -> None:
        """Test that sample sheet passes all validation."""
        from app import create_sample_character_sheet

        for char_class in ["Fighter", "Rogue", "Wizard", "Cleric"]:
            sheet = create_sample_character_sheet(char_class, f"Test {char_class}")
            # Validation happens in Pydantic - if we get here, it's valid
            assert sheet.hit_points_current <= sheet.hit_points_max
            assert sheet.hit_dice_remaining <= sheet.level
            assert sheet.proficiency_bonus >= 2


# =============================================================================
# HP Color Coding Tests
# =============================================================================


class TestHPColorCoding:
    """Tests for HP bar color coding logic."""

    def test_hp_color_green_above_50_percent(self) -> None:
        """Test HP color is green when above 50%."""
        from app import get_hp_color

        # 60% HP
        assert get_hp_color(60, 100) == "#6B8E6B"
        # 51% HP
        assert get_hp_color(51, 100) == "#6B8E6B"
        # 100% HP
        assert get_hp_color(100, 100) == "#6B8E6B"

    def test_hp_color_yellow_25_to_50_percent(self) -> None:
        """Test HP color is yellow/amber when between 25% and 50%."""
        from app import get_hp_color

        # Exactly 50%
        assert get_hp_color(50, 100) == "#E8A849"
        # 26% HP
        assert get_hp_color(26, 100) == "#E8A849"
        # 40% HP
        assert get_hp_color(40, 100) == "#E8A849"

    def test_hp_color_red_below_25_percent(self) -> None:
        """Test HP color is red when below 25%."""
        from app import get_hp_color

        # Exactly 25%
        assert get_hp_color(25, 100) == "#C45C4A"
        # 10% HP
        assert get_hp_color(10, 100) == "#C45C4A"
        # 0 HP
        assert get_hp_color(0, 100) == "#C45C4A"

    def test_hp_color_with_zero_max(self) -> None:
        """Test HP color handles zero max HP (edge case)."""
        from app import get_hp_color

        # Should return red for invalid state
        assert get_hp_color(0, 0) == "#C45C4A"

    def test_hp_color_with_non_standard_max(self) -> None:
        """Test HP color with non-100 max HP values."""
        from app import get_hp_color

        # 22/44 = 50% -> yellow
        assert get_hp_color(22, 44) == "#E8A849"
        # 30/44 = ~68% -> green
        assert get_hp_color(30, 44) == "#6B8E6B"
        # 10/44 = ~22.7% -> red
        assert get_hp_color(10, 44) == "#C45C4A"


class TestHPBarHTMLRendering:
    """Tests for HP bar HTML generation."""

    def test_hp_bar_structure(self) -> None:
        """Test HP bar HTML has correct structure."""
        from app import render_hp_bar_html

        html = render_hp_bar_html(50, 100)
        assert 'class="hp-container"' in html
        assert 'class="hp-bar-bg"' in html
        assert 'class="hp-bar-fill"' in html
        assert 'class="hp-text"' in html
        assert "50/100" in html
        assert "HP" in html

    def test_hp_bar_percentage_width(self) -> None:
        """Test HP bar width percentage is correct."""
        from app import render_hp_bar_html

        html = render_hp_bar_html(75, 100)
        assert "width: 75.0%" in html or "width: 75%" in html

    def test_hp_bar_color_applied(self) -> None:
        """Test HP bar has correct color applied."""
        from app import render_hp_bar_html

        # Green for high HP
        html_green = render_hp_bar_html(80, 100)
        assert "#6B8E6B" in html_green

        # Yellow for medium HP
        html_yellow = render_hp_bar_html(40, 100)
        assert "#E8A849" in html_yellow

        # Red for low HP
        html_red = render_hp_bar_html(20, 100)
        assert "#C45C4A" in html_red

    def test_hp_bar_with_temp_hp(self) -> None:
        """Test HP bar shows temporary HP when present."""
        from app import render_hp_bar_html

        html = render_hp_bar_html(50, 100, temp=10)
        assert "(+10)" in html
        assert "50/100" in html

    def test_hp_bar_no_temp_hp_display_when_zero(self) -> None:
        """Test HP bar doesn't show temp HP when zero."""
        from app import render_hp_bar_html

        html = render_hp_bar_html(50, 100, temp=0)
        assert "(+" not in html

    def test_hp_bar_capped_at_100_percent(self) -> None:
        """Test HP bar width doesn't exceed 100%."""
        from app import render_hp_bar_html

        # Current > max (shouldn't happen but handle it)
        html = render_hp_bar_html(120, 100)
        assert "width: 100%" in html


# =============================================================================
# Skill Modifier Calculation Tests
# =============================================================================


class TestSkillModifierCalculation:
    """Tests for skill modifier calculation."""

    def test_base_skill_modifier(self, fighter_sheet: CharacterSheet) -> None:
        """Test skill modifier for non-proficient skill."""
        from app import calculate_skill_modifier

        # Arcana uses Intelligence, Fighter not proficient
        # INT 10 = +0 modifier, no proficiency
        modifier = calculate_skill_modifier(fighter_sheet, "Arcana", "intelligence")
        assert modifier == 0  # (10-10)//2 = 0

    def test_proficient_skill_modifier(self, fighter_sheet: CharacterSheet) -> None:
        """Test skill modifier for proficient skill."""
        from app import calculate_skill_modifier

        # Athletics uses Strength, Fighter is proficient
        # STR 16 = +3 modifier, +3 proficiency (level 5)
        modifier = calculate_skill_modifier(fighter_sheet, "Athletics", "strength")
        assert modifier == 6  # +3 (ability) + 3 (proficiency)

    def test_expertise_skill_modifier(self, rogue_sheet: CharacterSheet) -> None:
        """Test skill modifier with expertise (double proficiency)."""
        from app import calculate_skill_modifier

        # Stealth uses Dexterity, Rogue has expertise
        # DEX 16 = +3 modifier, +6 proficiency (level 5, doubled)
        modifier = calculate_skill_modifier(rogue_sheet, "Stealth", "dexterity")
        assert modifier == 9  # +3 (ability) + 6 (expertise = 2 * proficiency)

    def test_skill_modifier_negative_ability(self) -> None:
        """Test skill modifier with negative ability modifier."""
        # Create a character with low strength
        sheet = CharacterSheet(
            name="Weakling",
            race="Human",
            character_class="Wizard",
            level=1,
            strength=8,  # -1 modifier
            dexterity=10,
            constitution=10,
            intelligence=16,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=6,
            hit_points_current=6,
            hit_dice="1d6",
            hit_dice_remaining=1,
            skill_proficiencies=[],
        )
        from app import calculate_skill_modifier

        modifier = calculate_skill_modifier(sheet, "Athletics", "strength")
        assert modifier == -1  # (8-10)//2 = -1


# =============================================================================
# Spell Slot Visualization Tests
# =============================================================================


class TestSpellSlotVisualization:
    """Tests for spell slot visualization."""

    def test_spell_slots_filled_dots(self) -> None:
        """Test spell slots show correct number of filled dots."""
        from app import render_spell_slots_html

        spell_slots = {
            1: SpellSlots(max=4, current=4),  # All filled
        }
        html = render_spell_slots_html(spell_slots)
        # 4 filled dots for level 1
        assert html.count("●") == 4
        assert html.count("○") == 0

    def test_spell_slots_empty_dots(self) -> None:
        """Test spell slots show correct number of empty dots."""
        from app import render_spell_slots_html

        spell_slots = {
            1: SpellSlots(max=4, current=0),  # All expended
        }
        html = render_spell_slots_html(spell_slots)
        # 4 empty dots for level 1
        assert html.count("●") == 0
        assert html.count("○") == 4

    def test_spell_slots_mixed(self) -> None:
        """Test spell slots with mix of filled and empty."""
        from app import render_spell_slots_html

        spell_slots = {
            1: SpellSlots(max=4, current=2),  # 2 filled, 2 empty
            2: SpellSlots(max=3, current=1),  # 1 filled, 2 empty
        }
        html = render_spell_slots_html(spell_slots)
        # Total: 3 filled (2+1), 4 empty (2+2)
        assert html.count("●") == 3
        assert html.count("○") == 4

    def test_spell_slots_shows_levels(self) -> None:
        """Test spell slots display shows level labels."""
        from app import render_spell_slots_html

        spell_slots = {
            1: SpellSlots(max=4, current=2),
            3: SpellSlots(max=2, current=1),
        }
        html = render_spell_slots_html(spell_slots)
        assert "Level 1" in html
        assert "Level 3" in html

    def test_empty_spell_slots_returns_empty(self) -> None:
        """Test empty spell slots dict returns empty string."""
        from app import render_spell_slots_html

        html = render_spell_slots_html({})
        assert html == ""

    def test_spell_slots_skips_zero_max(self) -> None:
        """Test spell slots with max=0 are skipped."""
        from app import render_spell_slots_html

        spell_slots = {
            1: SpellSlots(max=4, current=2),
            2: SpellSlots(max=0, current=0),  # No slots at this level
        }
        html = render_spell_slots_html(spell_slots)
        assert "Level 1" in html
        assert "Level 2" not in html


# =============================================================================
# HTML Safety Tests
# =============================================================================


class TestHTMLSafety:
    """Tests for HTML escaping and XSS prevention."""

    def test_name_html_escaped(self) -> None:
        """Test character name is HTML escaped."""
        from app import render_sheet_header_html

        # Name with HTML injection attempt
        sheet = CharacterSheet(
            name='<script>alert("XSS")</script>',
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
        html = render_sheet_header_html(sheet)
        # Check that the script tag is escaped
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_equipment_html_escaped(self) -> None:
        """Test equipment names are HTML escaped."""
        from app import render_equipment_section_html
        from models import EquipmentItem

        equipment = [
            EquipmentItem(name='<img src=x onerror="alert(1)">', quantity=1),
        ]
        html = render_equipment_section_html(equipment)
        assert "<img" not in html
        assert "&lt;img" in html


# =============================================================================
# Character Sheet Section Rendering Tests
# =============================================================================


class TestCharacterSheetSections:
    """Tests for individual character sheet section rendering."""

    def test_render_sheet_header(self, fighter_sheet: CharacterSheet) -> None:
        """Test sheet header renders required info."""
        from app import render_sheet_header_html

        html = render_sheet_header_html(fighter_sheet)
        assert "Theron Ironforge" in html
        assert "Human" in html
        assert "Fighter" in html
        assert "Level 5" in html or "5" in html

    def test_render_ability_scores(self, fighter_sheet: CharacterSheet) -> None:
        """Test ability scores section renders all abilities."""
        from app import render_ability_scores_html

        html = render_ability_scores_html(fighter_sheet)
        assert "STR" in html or "Strength" in html
        assert "DEX" in html or "Dexterity" in html
        assert "CON" in html or "Constitution" in html
        assert "INT" in html or "Intelligence" in html
        assert "WIS" in html or "Wisdom" in html
        assert "CHA" in html or "Charisma" in html
        # Check some values
        assert "16" in html  # STR score
        assert "+3" in html  # STR modifier

    def test_render_combat_stats(self, fighter_sheet: CharacterSheet) -> None:
        """Test combat stats section renders AC, HP, etc."""
        from app import render_combat_stats_html

        html = render_combat_stats_html(fighter_sheet)
        assert "18" in html  # AC
        assert "38" in html or "44" in html  # HP current or max
        assert "30" in html  # Speed

    def test_render_spellcasting_section_for_caster(
        self, wizard_sheet: CharacterSheet
    ) -> None:
        """Test spellcasting section renders for casters."""
        from app import render_spellcasting_section_html

        html = render_spellcasting_section_html(wizard_sheet)
        assert html != ""  # Should have content
        assert "Fire Bolt" in html or "Fireball" in html
        assert "●" in html or "○" in html  # Spell slots

    def test_render_spellcasting_section_for_noncaster(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Test spellcasting section is empty for non-casters."""
        from app import render_spellcasting_section_html

        html = render_spellcasting_section_html(fighter_sheet)
        # Non-casters should have no spellcasting section content
        assert html == "" or "No spellcasting" in html


# =============================================================================
# Death Saves Display Tests (Story 8.2 Code Review Fix)
# =============================================================================


class TestDeathSavesDisplay:
    """Tests for death saves display when character is at 0 HP."""

    def test_death_saves_display_at_zero_hp(self) -> None:
        """Test death saves are shown when HP is 0."""
        from app import render_combat_stats_html
        from models import DeathSaves

        # Create character at 0 HP
        sheet = CharacterSheet(
            name="Dying Hero",
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
            hit_points_current=0,  # At 0 HP
            hit_dice="1d10",
            hit_dice_remaining=1,
            death_saves=DeathSaves(successes=1, failures=2),
        )
        html = render_combat_stats_html(sheet)
        assert "death-saves" in html
        assert "Successes" in html
        assert "Failures" in html

    def test_death_saves_not_shown_when_hp_above_zero(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Test death saves are not shown when HP is above 0."""
        from app import render_combat_stats_html

        html = render_combat_stats_html(fighter_sheet)
        assert "death-saves" not in html

    def test_death_saves_shows_stable_status(self) -> None:
        """Test death saves shows 'Stable' when character has 3 successes."""
        from app import render_death_saves_html
        from models import DeathSaves

        death_saves = DeathSaves(successes=3, failures=1)
        html = render_death_saves_html(death_saves)
        assert "Stable" in html

    def test_death_saves_shows_dead_status(self) -> None:
        """Test death saves shows 'Dead' when character has 3 failures."""
        from app import render_death_saves_html
        from models import DeathSaves

        death_saves = DeathSaves(successes=1, failures=3)
        html = render_death_saves_html(death_saves)
        assert "Dead" in html


# =============================================================================
# SKILLS_BY_ABILITY Constant Test
# =============================================================================


class TestSkillsByAbility:
    """Tests for SKILLS_BY_ABILITY mapping."""

    def test_all_18_skills_mapped(self) -> None:
        """Test all 18 D&D 5e skills are present."""
        from app import SKILLS_BY_ABILITY

        all_skills = []
        for skills in SKILLS_BY_ABILITY.values():
            all_skills.extend(skills)
        assert len(all_skills) == 18

    def test_correct_ability_mappings(self) -> None:
        """Test skills are mapped to correct abilities."""
        from app import SKILLS_BY_ABILITY

        # Spot check some mappings
        assert "Athletics" in SKILLS_BY_ABILITY["strength"]
        assert "Stealth" in SKILLS_BY_ABILITY["dexterity"]
        assert "Arcana" in SKILLS_BY_ABILITY["intelligence"]
        assert "Perception" in SKILLS_BY_ABILITY["wisdom"]
        assert "Persuasion" in SKILLS_BY_ABILITY["charisma"]


# =============================================================================
# Accessibility Tests (Story 8.2 Code Review Fix)
# =============================================================================


class TestAccessibility:
    """Tests for accessibility features."""

    def test_ability_scores_have_aria_labels(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Test ability scores have proper ARIA labels."""
        from app import render_ability_scores_html

        html = render_ability_scores_html(fighter_sheet)
        assert 'role="list"' in html
        assert 'aria-label="Ability scores"' in html
        assert 'role="listitem"' in html

    def test_hp_bar_has_meter_role(self, fighter_sheet: CharacterSheet) -> None:
        """Test HP bar has proper meter role for accessibility."""
        from app import render_hp_bar_html

        html = render_hp_bar_html(38, 44, 0)
        assert 'role="meter"' in html
        assert 'aria-valuenow="38"' in html
        assert 'aria-valuemax="44"' in html

    def test_spell_slots_have_aria_labels(self, wizard_sheet: CharacterSheet) -> None:
        """Test spell slots have proper ARIA labels."""
        from app import render_spell_slots_html

        html = render_spell_slots_html(wizard_sheet.spell_slots)
        assert 'role="list"' in html
        assert 'aria-label="Spell slots"' in html
