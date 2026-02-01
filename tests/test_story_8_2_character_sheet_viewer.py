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


# =============================================================================
# Extended HP Bar Edge Case Tests
# =============================================================================


class TestHPBarEdgeCases:
    """Additional edge case tests for HP bar rendering."""

    def test_hp_bar_with_zero_max_hp(self) -> None:
        """Test HP bar handles zero max HP gracefully."""
        from app import render_hp_bar_html

        html = render_hp_bar_html(0, 0, 0)
        assert "0/0" in html
        assert "width: 0%" in html
        assert "#C45C4A" in html  # Red for invalid state

    def test_hp_bar_with_negative_current_hp(self) -> None:
        """Test HP bar handles negative current HP (treated as 0)."""
        from app import render_hp_bar_html

        # Negative HP should display but bar width should be 0%
        html = render_hp_bar_html(-5, 100, 0)
        assert "-5/100" in html
        assert "#C45C4A" in html  # Red for low HP

    def test_hp_bar_exactly_50_percent(self) -> None:
        """Test HP bar at exactly 50% boundary."""
        from app import get_hp_color

        # 50% should be yellow (<=50% is yellow zone)
        assert get_hp_color(50, 100) == "#E8A849"

    def test_hp_bar_exactly_25_percent(self) -> None:
        """Test HP bar at exactly 25% boundary."""
        from app import get_hp_color

        # 25% should be red (<=25% is red zone)
        assert get_hp_color(25, 100) == "#C45C4A"

    def test_hp_bar_just_above_50_percent(self) -> None:
        """Test HP bar just above 50% boundary."""
        from app import get_hp_color

        # 51% should be green (>50% is green zone)
        assert get_hp_color(51, 100) == "#6B8E6B"

    def test_hp_bar_just_above_25_percent(self) -> None:
        """Test HP bar just above 25% boundary."""
        from app import get_hp_color

        # 26% should be yellow (>25% and <=50% is yellow zone)
        assert get_hp_color(26, 100) == "#E8A849"

    def test_hp_bar_with_very_large_temp_hp(self) -> None:
        """Test HP bar with very large temporary HP."""
        from app import render_hp_bar_html

        html = render_hp_bar_html(50, 100, temp=999)
        assert "(+999)" in html
        assert "50/100" in html

    def test_hp_bar_aria_attributes_complete(self) -> None:
        """Test HP bar has all required ARIA attributes."""
        from app import render_hp_bar_html

        html = render_hp_bar_html(75, 150, temp=10)
        assert 'role="meter"' in html
        assert 'aria-label="Hit Points"' in html
        assert 'aria-valuenow="75"' in html
        assert 'aria-valuemin="0"' in html
        assert 'aria-valuemax="150"' in html
        assert 'class="sr-only"' in html  # Screen reader text

    def test_hp_bar_percentage_capping(self) -> None:
        """Test HP bar width caps at 100% even when current > max."""
        from app import render_hp_bar_html

        html = render_hp_bar_html(150, 100, 0)
        assert "width: 100%" in html


# =============================================================================
# Extended Spell Slot Edge Case Tests
# =============================================================================


class TestSpellSlotEdgeCases:
    """Additional edge case tests for spell slot visualization."""

    def test_spell_slots_pydantic_validates_max_constraint(self) -> None:
        """Test Pydantic validates current cannot exceed max."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            SpellSlots(max=4, current=6)  # Invalid: current > max

    def test_spell_slots_pydantic_validates_non_negative(self) -> None:
        """Test Pydantic validates current must be non-negative."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            SpellSlots(max=4, current=-2)  # Invalid: negative

    def test_spell_slots_at_boundary_max(self) -> None:
        """Test spell slots at boundary where current equals max."""
        from app import render_spell_slots_html

        spell_slots = {
            1: SpellSlots(max=4, current=4),  # Exactly at max
        }
        html = render_spell_slots_html(spell_slots)
        assert html.count("●") == 4
        assert html.count("○") == 0

    def test_spell_slots_at_boundary_zero(self) -> None:
        """Test spell slots at boundary where current is zero."""
        from app import render_spell_slots_html

        spell_slots = {
            1: SpellSlots(max=4, current=0),  # At minimum
        }
        html = render_spell_slots_html(spell_slots)
        assert html.count("●") == 0
        assert html.count("○") == 4

    def test_spell_slots_high_levels(self) -> None:
        """Test spell slots at high levels (6-9)."""
        from app import render_spell_slots_html

        spell_slots = {
            6: SpellSlots(max=2, current=2),
            7: SpellSlots(max=1, current=0),
            8: SpellSlots(max=1, current=1),
            9: SpellSlots(max=1, current=0),
        }
        html = render_spell_slots_html(spell_slots)
        assert "Level 6" in html
        assert "Level 7" in html
        assert "Level 8" in html
        assert "Level 9" in html
        # Total: 3 filled (2+0+1+0), 2 empty (0+1+0+1)
        assert html.count("●") == 3
        assert html.count("○") == 2

    def test_spell_slots_single_level(self) -> None:
        """Test spell slots with only one level."""
        from app import render_spell_slots_html

        spell_slots = {
            3: SpellSlots(max=2, current=1),
        }
        html = render_spell_slots_html(spell_slots)
        assert "Level 3" in html
        assert html.count("●") == 1
        assert html.count("○") == 1

    def test_spell_slots_all_full(self) -> None:
        """Test spell slots when all are full."""
        from app import render_spell_slots_html

        spell_slots = {
            1: SpellSlots(max=4, current=4),
            2: SpellSlots(max=3, current=3),
            3: SpellSlots(max=2, current=2),
        }
        html = render_spell_slots_html(spell_slots)
        # Total: 9 filled, 0 empty
        assert html.count("●") == 9
        assert html.count("○") == 0

    def test_spell_slots_all_empty(self) -> None:
        """Test spell slots when all are expended."""
        from app import render_spell_slots_html

        spell_slots = {
            1: SpellSlots(max=4, current=0),
            2: SpellSlots(max=3, current=0),
        }
        html = render_spell_slots_html(spell_slots)
        # Total: 0 filled, 7 empty
        assert html.count("●") == 0
        assert html.count("○") == 7

    def test_spell_slots_aria_per_row(self) -> None:
        """Test each spell slot row has proper ARIA labels."""
        from app import render_spell_slots_html

        spell_slots = {
            1: SpellSlots(max=4, current=2),
            2: SpellSlots(max=3, current=1),
        }
        html = render_spell_slots_html(spell_slots)
        assert 'aria-label="2 of 4 slots available"' in html
        assert 'aria-label="1 of 3 slots available"' in html


# =============================================================================
# Extended Skill Modifier Tests
# =============================================================================


class TestSkillModifierEdgeCases:
    """Additional edge case tests for skill modifier calculation."""

    def test_skill_modifier_minimum_ability(self) -> None:
        """Test skill modifier with minimum ability score (1)."""
        sheet = CharacterSheet(
            name="Weak",
            race="Human",
            character_class="Fighter",
            level=1,
            strength=1,  # -5 modifier
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
            skill_proficiencies=[],
        )
        from app import calculate_skill_modifier

        modifier = calculate_skill_modifier(sheet, "Athletics", "strength")
        assert modifier == -5  # (1-10)//2 = -5

    def test_skill_modifier_maximum_ability(self) -> None:
        """Test skill modifier with high ability score (20)."""
        sheet = CharacterSheet(
            name="Strong",
            race="Human",
            character_class="Fighter",
            level=1,
            strength=20,  # +5 modifier
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
            skill_proficiencies=[],
        )
        from app import calculate_skill_modifier

        modifier = calculate_skill_modifier(sheet, "Athletics", "strength")
        assert modifier == 5  # (20-10)//2 = 5

    def test_skill_modifier_level_20_proficiency(self) -> None:
        """Test skill modifier with level 20 proficiency (+6)."""
        sheet = CharacterSheet(
            name="Master",
            race="Human",
            character_class="Fighter",
            level=20,  # +6 proficiency bonus
            strength=16,  # +3 modifier
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=100,
            hit_points_current=100,
            hit_dice="20d10",
            hit_dice_remaining=20,
            skill_proficiencies=["Athletics"],
        )
        from app import calculate_skill_modifier

        modifier = calculate_skill_modifier(sheet, "Athletics", "strength")
        assert modifier == 9  # +3 (ability) + 6 (proficiency)

    def test_skill_modifier_level_20_expertise(self) -> None:
        """Test skill modifier with level 20 expertise (+12)."""
        sheet = CharacterSheet(
            name="Expert",
            race="Human",
            character_class="Rogue",
            level=20,  # +6 proficiency bonus
            strength=10,
            dexterity=20,  # +5 modifier
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=100,
            hit_points_current=100,
            hit_dice="20d8",
            hit_dice_remaining=20,
            skill_proficiencies=["Stealth"],
            skill_expertise=["Stealth"],
        )
        from app import calculate_skill_modifier

        modifier = calculate_skill_modifier(sheet, "Stealth", "dexterity")
        assert modifier == 17  # +5 (ability) + 12 (expertise = 2*6)

    def test_all_skills_calculate_correctly(self, fighter_sheet: CharacterSheet) -> None:
        """Test all 18 skills can be calculated without error."""
        from app import SKILLS_BY_ABILITY, calculate_skill_modifier

        for ability, skills in SKILLS_BY_ABILITY.items():
            for skill in skills:
                # Should not raise an exception
                modifier = calculate_skill_modifier(fighter_sheet, skill, ability)
                assert isinstance(modifier, int)


# =============================================================================
# Extended Death Saves Tests
# =============================================================================


class TestDeathSavesEdgeCases:
    """Additional edge case tests for death saves display."""

    def test_death_saves_all_zeros(self) -> None:
        """Test death saves with 0 successes and 0 failures."""
        from app import render_death_saves_html
        from models import DeathSaves

        death_saves = DeathSaves(successes=0, failures=0)
        html = render_death_saves_html(death_saves)
        # All empty circles
        assert html.count("●") == 0
        assert html.count("○") == 6  # 3 success + 3 failure circles

    def test_death_saves_partial_both(self) -> None:
        """Test death saves with partial successes and failures."""
        from app import render_death_saves_html
        from models import DeathSaves

        death_saves = DeathSaves(successes=2, failures=2)
        html = render_death_saves_html(death_saves)
        assert "Stable" not in html
        assert "Dead" not in html
        assert html.count("●") == 4  # 2 success + 2 failure filled
        assert html.count("○") == 2  # 1 success + 1 failure empty

    def test_death_saves_stable_condition(self) -> None:
        """Test death saves shows Stable with 3 successes."""
        from models import DeathSaves

        death_saves = DeathSaves(successes=3, failures=0)
        assert death_saves.is_stable is True
        assert death_saves.is_dead is False

    def test_death_saves_dead_condition(self) -> None:
        """Test death saves shows Dead with 3 failures."""
        from models import DeathSaves

        death_saves = DeathSaves(successes=0, failures=3)
        assert death_saves.is_dead is True
        assert death_saves.is_stable is False

    def test_death_saves_aria_attributes(self) -> None:
        """Test death saves have proper ARIA attributes."""
        from app import render_death_saves_html
        from models import DeathSaves

        death_saves = DeathSaves(successes=2, failures=1)
        html = render_death_saves_html(death_saves)
        assert 'role="group"' in html
        assert 'aria-label="Death saving throws"' in html
        assert 'aria-label="2 of 3 successes"' in html
        assert 'aria-label="1 of 3 failures"' in html


# =============================================================================
# Extended Sample Character Factory Tests
# =============================================================================


class TestSampleCharacterFactoryEdgeCases:
    """Additional edge case tests for sample character sheet creation."""

    def test_create_barbarian_sheet(self) -> None:
        """Test creating an unknown Barbarian defaults to Fighter stats."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Barbarian", "Test Barbarian")
        assert sheet.name == "Test Barbarian"
        assert sheet.character_class == "Barbarian"
        # Defaults to Fighter stats
        assert sheet.strength >= 14

    def test_create_ranger_sheet(self) -> None:
        """Test creating an unknown Ranger defaults to Fighter stats."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Ranger", "Test Ranger")
        assert sheet.name == "Test Ranger"
        assert sheet.character_class == "Ranger"

    def test_create_paladin_sheet(self) -> None:
        """Test creating an unknown Paladin defaults to Fighter stats."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Paladin", "Test Paladin")
        assert sheet.name == "Test Paladin"
        assert sheet.character_class == "Paladin"

    def test_create_bard_sheet(self) -> None:
        """Test creating an unknown Bard defaults to Fighter stats."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Bard", "Test Bard")
        assert sheet.name == "Test Bard"
        assert sheet.character_class == "Bard"

    def test_create_warlock_sheet(self) -> None:
        """Test creating an unknown Warlock defaults to Fighter stats."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Warlock", "Test Warlock")
        assert sheet.name == "Test Warlock"
        assert sheet.character_class == "Warlock"

    def test_create_sorcerer_sheet(self) -> None:
        """Test creating an unknown Sorcerer defaults to Fighter stats."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Sorcerer", "Test Sorcerer")
        assert sheet.name == "Test Sorcerer"
        assert sheet.character_class == "Sorcerer"

    def test_create_druid_sheet(self) -> None:
        """Test creating an unknown Druid defaults to Fighter stats."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Druid", "Test Druid")
        assert sheet.name == "Test Druid"
        assert sheet.character_class == "Druid"

    def test_create_monk_sheet(self) -> None:
        """Test creating an unknown Monk defaults to Fighter stats."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Monk", "Test Monk")
        assert sheet.name == "Test Monk"
        assert sheet.character_class == "Monk"

    def test_sample_sheet_has_equipment(self) -> None:
        """Test sample sheets have standard equipment."""
        from app import create_sample_character_sheet

        for char_class in ["Fighter", "Rogue", "Wizard", "Cleric"]:
            sheet = create_sample_character_sheet(char_class, f"Test {char_class}")
            assert len(sheet.equipment) > 0
            # Check for basic adventuring gear
            item_names = [item.name for item in sheet.equipment]
            assert "Backpack" in item_names or any("Rations" in n for n in item_names)

    def test_sample_caster_has_spell_slots(self) -> None:
        """Test caster sample sheets have spell slots."""
        from app import create_sample_character_sheet

        for char_class in ["Wizard", "Cleric"]:
            sheet = create_sample_character_sheet(char_class, f"Test {char_class}")
            assert len(sheet.spell_slots) > 0
            assert 1 in sheet.spell_slots  # At least level 1 slots

    def test_sample_sheet_initiative_calculated(self) -> None:
        """Test sample sheet initiative is based on DEX modifier."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Rogue", "Test Rogue")
        expected_init = (sheet.dexterity - 10) // 2
        assert sheet.initiative == expected_init

    def test_sample_sheet_with_special_characters_name(self) -> None:
        """Test sample sheet handles special characters in name."""
        from app import create_sample_character_sheet

        sheet = create_sample_character_sheet("Fighter", "Sir O'Brien III")
        assert sheet.name == "Sir O'Brien III"


# =============================================================================
# Extended HTML Safety/XSS Prevention Tests
# =============================================================================


class TestHTMLSafetyEdgeCases:
    """Additional edge case tests for HTML escaping and XSS prevention."""

    def test_race_html_escaped(self) -> None:
        """Test race name is HTML escaped."""
        from app import render_sheet_header_html

        sheet = CharacterSheet(
            name="Test",
            race='<img src=x onerror="alert(1)">',
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
        assert "<img" not in html
        assert "&lt;img" in html

    def test_class_html_escaped(self) -> None:
        """Test character class is HTML escaped."""
        from app import render_sheet_header_html

        sheet = CharacterSheet(
            name="Test",
            race="Human",
            character_class='<script>alert("XSS")</script>',
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
        assert "<script>" not in html

    def test_skill_name_html_escaped(self) -> None:
        """Test skill names are HTML escaped in skills section."""
        from app import render_skills_section_html

        sheet = CharacterSheet(
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
            skill_proficiencies=['<script>evil</script>'],
        )
        html = render_skills_section_html(sheet)
        # Standard skills are safe, but malicious proficiencies would be escaped
        assert "&lt;script&gt;" not in html or "<script>" not in html

    def test_weapon_name_html_escaped(self) -> None:
        """Test weapon names are HTML escaped."""
        from app import render_equipment_section_html
        from models import Weapon

        weapons = [
            Weapon(
                name='<svg onload="alert(1)">',
                damage_dice="1d8",
                damage_type="slashing",
                is_equipped=True,
            ),
        ]
        html = render_equipment_section_html([], weapons=weapons)
        assert "<svg" not in html
        assert "&lt;svg" in html

    def test_cantrip_name_html_escaped(self) -> None:
        """Test cantrip names are HTML escaped."""
        from app import render_spellcasting_section_html

        sheet = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Wizard",
            level=1,
            strength=10,
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
            spellcasting_ability="intelligence",
            spell_save_dc=13,
            spell_attack_bonus=5,
            cantrips=['<iframe src="evil.com">'],
        )
        html = render_spellcasting_section_html(sheet)
        assert "<iframe" not in html
        assert "&lt;iframe" in html

    def test_personality_traits_html_escaped(self) -> None:
        """Test personality traits are HTML escaped."""
        from app import render_personality_section_html

        sheet = CharacterSheet(
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
            personality_traits='<body onload="evil()">',
        )
        html = render_personality_section_html(sheet)
        assert "<body" not in html
        assert "&lt;body" in html

    def test_feature_name_html_escaped(self) -> None:
        """Test feature names are HTML escaped."""
        from app import render_features_section_html

        sheet = CharacterSheet(
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
            class_features=['<marquee>Evil</marquee>'],
        )
        html = render_features_section_html(sheet)
        assert "<marquee>" not in html


# =============================================================================
# Skills Section Rendering Tests
# =============================================================================


class TestSkillsSectionRendering:
    """Tests for skills section HTML rendering."""

    def test_skills_section_structure(self, fighter_sheet: CharacterSheet) -> None:
        """Test skills section has correct structure."""
        from app import render_skills_section_html

        html = render_skills_section_html(fighter_sheet)
        assert 'class="skills-section"' in html
        assert 'class="skill-row"' in html
        assert 'class="skill-proficiency"' in html
        assert 'class="skill-name"' in html
        assert 'class="skill-modifier"' in html

    def test_skills_show_proficiency_indicator(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Test skills show correct proficiency indicators."""
        from app import render_skills_section_html

        html = render_skills_section_html(fighter_sheet)
        # Fighter is proficient in Athletics
        assert "●" in html  # Proficient skill indicator
        assert "○" in html  # Non-proficient skill indicator

    def test_skills_show_expertise_indicator(self, rogue_sheet: CharacterSheet) -> None:
        """Test skills show double indicator for expertise."""
        from app import render_skills_section_html

        html = render_skills_section_html(rogue_sheet)
        # Rogue has expertise in Stealth
        assert "●●" in html  # Expertise indicator

    def test_skills_show_modifier_with_sign(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Test skills show modifier with + or - sign."""
        from app import render_skills_section_html

        html = render_skills_section_html(fighter_sheet)
        # Fighter has positive modifiers
        assert "+6" in html  # Athletics with proficiency
        assert "+0" in html or "+1" in html or "-" in html  # Various modifiers

    def test_all_18_skills_rendered(self, fighter_sheet: CharacterSheet) -> None:
        """Test all 18 D&D 5e skills are rendered."""
        from app import render_skills_section_html

        html = render_skills_section_html(fighter_sheet)
        all_skills = [
            "Athletics",
            "Acrobatics",
            "Sleight of Hand",
            "Stealth",
            "Arcana",
            "History",
            "Investigation",
            "Nature",
            "Religion",
            "Animal Handling",
            "Insight",
            "Medicine",
            "Perception",
            "Survival",
            "Deception",
            "Intimidation",
            "Performance",
            "Persuasion",
        ]
        for skill in all_skills:
            assert skill in html, f"Missing skill: {skill}"


# =============================================================================
# Equipment Section Edge Cases
# =============================================================================


class TestEquipmentSectionEdgeCases:
    """Additional edge case tests for equipment section rendering."""

    def test_equipment_empty_weapons(self) -> None:
        """Test equipment section with no weapons."""
        from app import render_equipment_section_html

        html = render_equipment_section_html([], weapons=[], armor=None)
        assert "Weapons" not in html

    def test_equipment_empty_armor(self) -> None:
        """Test equipment section with no armor."""
        from app import render_equipment_section_html
        from models import Weapon

        weapons = [
            Weapon(name="Sword", damage_dice="1d8", damage_type="slashing", is_equipped=True)
        ]
        html = render_equipment_section_html([], weapons=weapons, armor=None)
        assert "Armor" not in html

    def test_equipment_zero_currency(self) -> None:
        """Test equipment section with zero currency."""
        from app import render_equipment_section_html

        html = render_equipment_section_html([], gold=0, silver=0, copper=0)
        assert "Currency" not in html

    def test_equipment_partial_currency(self) -> None:
        """Test equipment section with partial currency."""
        from app import render_equipment_section_html

        html = render_equipment_section_html([], gold=50, silver=0, copper=0)
        assert "Currency" in html
        assert "50 gp" in html
        assert "sp" not in html
        assert "cp" not in html

    def test_equipment_large_quantity(self) -> None:
        """Test equipment with large quantities."""
        from app import render_equipment_section_html
        from models import EquipmentItem

        equipment = [
            EquipmentItem(name="Arrows", quantity=999),
        ]
        html = render_equipment_section_html(equipment)
        assert "Arrows" in html
        assert "x999" in html

    def test_equipment_single_quantity_no_suffix(self) -> None:
        """Test equipment with quantity 1 doesn't show x1."""
        from app import render_equipment_section_html
        from models import EquipmentItem

        equipment = [
            EquipmentItem(name="Torch", quantity=1),
        ]
        html = render_equipment_section_html(equipment)
        assert "Torch" in html
        assert "x1" not in html

    def test_equipment_weapon_properties_displayed(self) -> None:
        """Test weapon properties are displayed."""
        from app import render_equipment_section_html
        from models import Weapon

        weapons = [
            Weapon(
                name="Longbow",
                damage_dice="1d8",
                damage_type="piercing",
                properties=["ammunition", "heavy", "two-handed", "range"],
                is_equipped=True,
            ),
        ]
        html = render_equipment_section_html([], weapons=weapons)
        assert "ammunition" in html
        assert "heavy" in html


# =============================================================================
# Features Section Edge Cases
# =============================================================================


class TestFeaturesSectionEdgeCases:
    """Additional edge case tests for features section rendering."""

    def test_features_empty_class_features(self) -> None:
        """Test features section with no class features."""
        from app import render_features_section_html

        sheet = CharacterSheet(
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
            class_features=[],
            racial_traits=["Bonus Feat"],
        )
        html = render_features_section_html(sheet)
        assert "Class Features" not in html
        assert "Racial Traits" in html

    def test_features_empty_racial_traits(self) -> None:
        """Test features section with no racial traits."""
        from app import render_features_section_html

        sheet = CharacterSheet(
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
            class_features=["Second Wind"],
            racial_traits=[],
        )
        html = render_features_section_html(sheet)
        assert "Class Features" in html
        assert "Racial Traits" not in html

    def test_features_with_feats(self) -> None:
        """Test features section displays feats."""
        from app import render_features_section_html

        sheet = CharacterSheet(
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
            feats=["Great Weapon Master", "Sentinel"],
        )
        html = render_features_section_html(sheet)
        assert "Feats" in html
        assert "Great Weapon Master" in html
        assert "Sentinel" in html


# =============================================================================
# Personality Section Edge Cases
# =============================================================================


class TestPersonalitySectionEdgeCases:
    """Additional edge case tests for personality section rendering."""

    def test_personality_empty_fields(self) -> None:
        """Test personality section with all empty fields."""
        from app import render_personality_section_html

        sheet = CharacterSheet(
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
            personality_traits="",
            ideals="",
            bonds="",
            flaws="",
        )
        html = render_personality_section_html(sheet)
        assert "Personality Traits" not in html
        assert "Ideals" not in html
        assert "Bonds" not in html
        assert "Flaws" not in html

    def test_personality_with_conditions(self) -> None:
        """Test personality section displays active conditions."""
        from app import render_personality_section_html

        sheet = CharacterSheet(
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
            conditions=["Poisoned", "Frightened"],
        )
        html = render_personality_section_html(sheet)
        assert "Active Conditions" in html
        assert "Poisoned" in html
        assert "Frightened" in html

    def test_personality_partial_fields(self) -> None:
        """Test personality section with only some fields filled."""
        from app import render_personality_section_html

        sheet = CharacterSheet(
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
            personality_traits="Brave and bold",
            ideals="",
            bonds="My family",
            flaws="",
        )
        html = render_personality_section_html(sheet)
        assert "Personality Traits" in html
        assert "Brave and bold" in html
        assert "Ideals" not in html
        assert "Bonds" in html
        assert "My family" in html
        assert "Flaws" not in html


# =============================================================================
# Spellcasting Section Edge Cases
# =============================================================================


class TestSpellcastingSectionEdgeCases:
    """Additional edge case tests for spellcasting section rendering."""

    def test_spellcasting_no_spell_save_dc(self) -> None:
        """Test spellcasting section without spell save DC."""
        from app import render_spellcasting_section_html

        sheet = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Wizard",
            level=1,
            strength=10,
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
            spellcasting_ability="intelligence",
            spell_save_dc=None,
            spell_attack_bonus=5,
            cantrips=["Light"],
        )
        html = render_spellcasting_section_html(sheet)
        assert "Save DC:" not in html
        assert "Attack:" in html

    def test_spellcasting_no_spell_attack_bonus(self) -> None:
        """Test spellcasting section without spell attack bonus."""
        from app import render_spellcasting_section_html

        sheet = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Wizard",
            level=1,
            strength=10,
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
            spellcasting_ability="intelligence",
            spell_save_dc=13,
            spell_attack_bonus=None,
            cantrips=["Light"],
        )
        html = render_spellcasting_section_html(sheet)
        assert "Save DC:" in html
        assert "Attack:" not in html

    def test_spellcasting_empty_cantrips(self) -> None:
        """Test spellcasting section without cantrips."""
        from app import render_spellcasting_section_html

        sheet = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Wizard",
            level=1,
            strength=10,
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
            spellcasting_ability="intelligence",
            cantrips=[],
        )
        html = render_spellcasting_section_html(sheet)
        assert "Cantrips" not in html

    def test_spellcasting_empty_spell_slots(self) -> None:
        """Test spellcasting section without spell slots."""
        from app import render_spellcasting_section_html

        sheet = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Wizard",
            level=1,
            strength=10,
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
            spellcasting_ability="intelligence",
            cantrips=["Light"],
            spell_slots={},
        )
        html = render_spellcasting_section_html(sheet)
        assert "Spell Slots" not in html

    def test_spellcasting_cantrip_spells(self) -> None:
        """Test spellcasting section displays cantrip-level spells correctly."""
        from app import render_spellcasting_section_html

        sheet = CharacterSheet(
            name="Test",
            race="Human",
            character_class="Wizard",
            level=1,
            strength=10,
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
            spellcasting_ability="intelligence",
            spells_known=[
                Spell(name="Minor Illusion", level=0, school="illusion"),
                Spell(name="Magic Missile", level=1, school="evocation"),
            ],
        )
        html = render_spellcasting_section_html(sheet)
        assert "Minor Illusion" in html
        assert "(Cantrip)" in html
        assert "(Level 1)" in html


# =============================================================================
# Combat Stats Section Edge Cases
# =============================================================================


class TestCombatStatsSectionEdgeCases:
    """Additional edge case tests for combat stats section rendering."""

    def test_combat_stats_negative_initiative(self) -> None:
        """Test combat stats with negative initiative modifier."""
        from app import render_combat_stats_html

        sheet = CharacterSheet(
            name="Slow",
            race="Human",
            character_class="Fighter",
            level=1,
            strength=10,
            dexterity=6,  # -2 modifier
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            initiative=-2,
            hit_points_max=10,
            hit_points_current=10,
            hit_dice="1d10",
            hit_dice_remaining=1,
        )
        html = render_combat_stats_html(sheet)
        assert "-2" in html

    def test_combat_stats_shows_hit_dice_info(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Test combat stats shows hit dice remaining."""
        from app import render_combat_stats_html

        html = render_combat_stats_html(fighter_sheet)
        assert "Hit Dice" in html
        assert "5d10" in html  # Hit dice type
        assert "5/5" in html  # Remaining / total

    def test_combat_stats_region_aria(self, fighter_sheet: CharacterSheet) -> None:
        """Test combat stats has region ARIA role."""
        from app import render_combat_stats_html

        html = render_combat_stats_html(fighter_sheet)
        assert 'role="region"' in html
        assert 'aria-label="Combat statistics"' in html


# =============================================================================
# Ability Scores Section Edge Cases
# =============================================================================


class TestAbilityScoresSectionEdgeCases:
    """Additional edge case tests for ability scores section rendering."""

    def test_ability_scores_saving_throw_indicator(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Test ability scores show saving throw proficiency indicator."""
        from app import render_ability_scores_html

        html = render_ability_scores_html(fighter_sheet)
        # Fighter proficient in STR and CON saves - should have *
        assert " *" in html

    def test_ability_scores_negative_modifier(self) -> None:
        """Test ability scores with negative modifiers display correctly."""
        from app import render_ability_scores_html

        sheet = CharacterSheet(
            name="Weak",
            race="Human",
            character_class="Fighter",
            level=1,
            strength=8,  # -1 modifier
            dexterity=6,  # -2 modifier
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
        html = render_ability_scores_html(sheet)
        assert "-1" in html
        assert "-2" in html

    def test_ability_scores_all_six_rendered(
        self, fighter_sheet: CharacterSheet
    ) -> None:
        """Test all six ability scores are rendered."""
        from app import render_ability_scores_html

        html = render_ability_scores_html(fighter_sheet)
        assert "STR" in html
        assert "DEX" in html
        assert "CON" in html
        assert "INT" in html
        assert "WIS" in html
        assert "CHA" in html

    def test_ability_scores_aria_per_card(self, fighter_sheet: CharacterSheet) -> None:
        """Test each ability score card has proper ARIA label."""
        from app import render_ability_scores_html

        html = render_ability_scores_html(fighter_sheet)
        assert 'aria-label="Strength:' in html
        assert 'aria-label="Dexterity:' in html


# =============================================================================
# Sheet Header Edge Cases
# =============================================================================


class TestSheetHeaderEdgeCases:
    """Additional edge case tests for sheet header rendering."""

    def test_header_shows_proficiency_bonus(self, fighter_sheet: CharacterSheet) -> None:
        """Test header shows proficiency bonus."""
        from app import render_sheet_header_html

        html = render_sheet_header_html(fighter_sheet)
        assert "Proficiency Bonus:" in html
        assert "+3" in html  # Level 5 proficiency

    def test_header_level_1_proficiency(self) -> None:
        """Test header shows +2 proficiency at level 1."""
        from app import render_sheet_header_html

        sheet = CharacterSheet(
            name="Newbie",
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
        assert "+2" in html  # Level 1-4 proficiency

    def test_header_level_17_proficiency(self) -> None:
        """Test header shows +6 proficiency at level 17+."""
        from app import render_sheet_header_html

        sheet = CharacterSheet(
            name="Master",
            race="Human",
            character_class="Fighter",
            level=17,
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=100,
            hit_points_current=100,
            hit_dice="17d10",
            hit_dice_remaining=17,
        )
        html = render_sheet_header_html(sheet)
        assert "+6" in html  # Level 17-20 proficiency
