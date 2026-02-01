"""Tests for Story 8-3: Character Sheet Context Injection.

Tests the context injection functionality for character sheets into
agent prompts. PC agents see only their own sheet, while the DM sees
all party sheets.

FR62: Character sheet data is included in agent context (DM sees all, PC sees own)
"""

from __future__ import annotations

import pytest

from agents import (
    _build_dm_context,
    _build_pc_context,
    _format_modifier,
    format_all_sheets_context,
    format_character_sheet_context,
)
from models import (
    AgentMemory,
    Armor,
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
        armor_proficiencies=["All armor", "Shields"],
        weapon_proficiencies=["Simple weapons", "Martial weapons"],
        skill_proficiencies=["Athletics", "Intimidation", "Perception"],
        class_features=["Second Wind", "Action Surge", "Extra Attack"],
        weapons=[
            Weapon(
                name="Longsword",
                damage_dice="1d8",
                damage_type="slashing",
                properties=["versatile"],
            ),
            Weapon(
                name="Handaxe",
                damage_dice="1d6",
                damage_type="slashing",
                properties=["light", "thrown"],
            ),
        ],
        armor=Armor(name="Chain Mail", armor_class=16, armor_type="heavy"),
        equipment=[
            EquipmentItem(name="Rope", quantity=1, description="50ft hemp rope"),
            EquipmentItem(name="Torches", quantity=5),
            EquipmentItem(name="Rations", quantity=3, description="Trail rations"),
        ],
        gold=47,
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
        skill_proficiencies=["Arcana", "History", "Investigation"],
        class_features=["Arcane Recovery", "Evocation Savant", "Sculpt Spells"],
        racial_traits=["Darkvision", "Fey Ancestry", "Trance"],
        weapons=[
            Weapon(name="Quarterstaff", damage_dice="1d6", damage_type="bludgeoning"),
        ],
        equipment=[
            EquipmentItem(name="Spellbook", quantity=1),
            EquipmentItem(name="Component Pouch", quantity=1),
        ],
        gold=120,
        spellcasting_ability="intelligence",
        spell_save_dc=15,
        spell_attack_bonus=7,
        cantrips=["Fire Bolt", "Mage Hand", "Prestidigitation", "Light"],
        spell_slots={
            1: SpellSlots(current=3, max=4),
            2: SpellSlots(current=2, max=3),
            3: SpellSlots(current=1, max=2),
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
            Spell(
                name="Fireball",
                level=3,
                school="evocation",
                casting_time="1 action",
                range="150 feet",
                description="Area fire damage",
            ),
            Spell(
                name="Shield",
                level=1,
                school="abjuration",
                casting_time="1 reaction",
                range="self",
                description="+5 AC until next turn",
            ),
        ],
    )


@pytest.fixture
def sample_game_state_with_sheets(
    fighter_sheet: CharacterSheet, wizard_sheet: CharacterSheet
) -> GameState:
    """Create a GameState with character sheets for testing."""
    return GameState(
        ground_truth_log=["[DM]: The adventure begins."],
        turn_queue=["dm", "fighter", "wizard"],
        current_turn="dm",
        agent_memories={
            "dm": AgentMemory(token_limit=8000),
            "fighter": AgentMemory(token_limit=4000),
            "wizard": AgentMemory(token_limit=4000),
        },
        game_config=GameConfig(
            combat_mode="Narrative",
            summarizer_model="gemini-1.5-flash",
            party_size=4,
        ),
        dm_config=DMConfig(
            name="Dungeon Master",
            provider="gemini",
            model="gemini-1.5-flash",
            token_limit=8000,
            color="#D4A574",
        ),
        characters={
            "fighter": CharacterConfig(
                name="Thorin",
                character_class="Fighter",
                personality="Brave and bold",
                color="#C9A45C",
                provider="gemini",
                model="gemini-1.5-flash",
                token_limit=4000,
            ),
            "wizard": CharacterConfig(
                name="Elara",
                character_class="Wizard",
                personality="Curious and scholarly",
                color="#7B68EE",
                provider="gemini",
                model="gemini-1.5-flash",
                token_limit=4000,
            ),
        },
        whisper_queue=[],
        human_active=False,
        controlled_character=None,
        session_number=1,
        session_id="001",
        summarization_in_progress=False,
        selected_module=None,
        character_sheets={
            "Thorin": fighter_sheet,
            "Elara": wizard_sheet,
        },
    )


# =============================================================================
# _format_modifier Tests
# =============================================================================


class TestFormatModifier:
    """Tests for _format_modifier helper function."""

    def test_positive_modifier(self) -> None:
        """Test positive modifier formatting."""
        assert _format_modifier(5) == "+5"
        assert _format_modifier(1) == "+1"
        assert _format_modifier(10) == "+10"

    def test_negative_modifier(self) -> None:
        """Test negative modifier formatting."""
        assert _format_modifier(-2) == "-2"
        assert _format_modifier(-1) == "-1"
        assert _format_modifier(-5) == "-5"

    def test_zero_modifier(self) -> None:
        """Test zero modifier formatting."""
        assert _format_modifier(0) == "+0"


# =============================================================================
# format_character_sheet_context Tests
# =============================================================================


class TestFormatCharacterSheetContext:
    """Tests for format_character_sheet_context function."""

    def test_header_for_own_character(self, fighter_sheet: CharacterSheet) -> None:
        """Test header format when for_own_character is True."""
        result = format_character_sheet_context(fighter_sheet, for_own_character=True)
        assert "## Your Character Sheet: Thorin, Dwarf Fighter (Level 5)" in result

    def test_header_for_other_character(self, fighter_sheet: CharacterSheet) -> None:
        """Test header format when for_own_character is False."""
        result = format_character_sheet_context(fighter_sheet, for_own_character=False)
        assert "### Thorin, Dwarf Fighter (Level 5)" in result
        assert "## Your Character Sheet" not in result

    def test_hp_line_format(self, fighter_sheet: CharacterSheet) -> None:
        """Test HP, AC, and Speed are formatted correctly."""
        result = format_character_sheet_context(fighter_sheet)
        assert "HP: 45/52" in result
        assert "AC: 18" in result
        assert "Speed: 30ft" in result

    def test_hp_with_temp_hp(self, fighter_sheet: CharacterSheet) -> None:
        """Test temp HP is shown when present."""
        fighter_sheet.hit_points_temp = 10
        result = format_character_sheet_context(fighter_sheet)
        assert "(+10 temp)" in result

    def test_conditions_displayed(self, fighter_sheet: CharacterSheet) -> None:
        """Test conditions are displayed when present."""
        fighter_sheet.conditions = ["poisoned", "exhausted"]
        result = format_character_sheet_context(fighter_sheet)
        assert "Conditions: poisoned, exhausted" in result

    def test_ability_scores_formatted(self, fighter_sheet: CharacterSheet) -> None:
        """Test ability scores are formatted with modifiers."""
        result = format_character_sheet_context(fighter_sheet)
        assert "STR: 18 (+4)" in result
        assert "DEX: 12 (+1)" in result
        assert "CON: 16 (+3)" in result
        assert "INT: 10 (+0)" in result
        assert "WIS: 14 (+2)" in result
        assert "CHA: 8 (-1)" in result

    def test_proficiencies_listed(self, fighter_sheet: CharacterSheet) -> None:
        """Test proficiencies are included."""
        result = format_character_sheet_context(fighter_sheet)
        assert "Proficiencies:" in result
        assert "All armor" in result
        assert "Simple weapons" in result

    def test_skills_listed(self, fighter_sheet: CharacterSheet) -> None:
        """Test skills are included."""
        result = format_character_sheet_context(fighter_sheet)
        assert "Skills: Athletics, Intimidation, Perception" in result

    def test_equipment_listed(self, fighter_sheet: CharacterSheet) -> None:
        """Test weapons and armor are included."""
        result = format_character_sheet_context(fighter_sheet)
        assert "Longsword" in result
        assert "1d8 slashing" in result
        assert "Chain Mail" in result

    def test_weapon_attack_bonus_calculated(self, fighter_sheet: CharacterSheet) -> None:
        """Test weapon attack bonus is calculated correctly."""
        # Fighter level 5: proficiency +3, STR +4 = +7
        result = format_character_sheet_context(fighter_sheet)
        assert "(+7, 1d8 slashing)" in result

    def test_finesse_weapon_uses_higher_modifier(self) -> None:
        """Test finesse weapons use higher of STR/DEX."""
        sheet = CharacterSheet(
            name="Rogue",
            race="Halfling",
            character_class="Rogue",
            level=5,
            strength=10,
            dexterity=18,
            constitution=12,
            intelligence=14,
            wisdom=12,
            charisma=14,
            armor_class=15,
            hit_points_max=33,
            hit_points_current=33,
            hit_dice="5d8",
            hit_dice_remaining=5,
            weapons=[
                Weapon(
                    name="Rapier",
                    damage_dice="1d8",
                    damage_type="piercing",
                    properties=["finesse"],
                ),
            ],
        )
        result = format_character_sheet_context(sheet)
        # Level 5 proficiency +3, DEX +4 (higher than STR +0) = +7
        assert "(+7, 1d8 piercing)" in result

    def test_inventory_listed(self, fighter_sheet: CharacterSheet) -> None:
        """Test inventory items are included."""
        result = format_character_sheet_context(fighter_sheet)
        assert "Inventory:" in result
        assert "Rope" in result
        assert "Torches (5)" in result
        assert "Rations (3)" in result

    def test_currency_listed(self, fighter_sheet: CharacterSheet) -> None:
        """Test currency is included."""
        result = format_character_sheet_context(fighter_sheet)
        assert "47 gold" in result

    def test_features_listed(self, fighter_sheet: CharacterSheet) -> None:
        """Test class features are included."""
        result = format_character_sheet_context(fighter_sheet)
        assert "Features:" in result
        assert "Second Wind" in result
        assert "Action Surge" in result
        assert "Extra Attack" in result


class TestFormatCharacterSheetContextSpellcasting:
    """Tests for spellcasting section in format_character_sheet_context."""

    def test_spellcasting_section_present(self, wizard_sheet: CharacterSheet) -> None:
        """Test spellcasting section is present for casters."""
        result = format_character_sheet_context(wizard_sheet)
        assert "Spellcasting:" in result

    def test_spellcasting_ability_shown(self, wizard_sheet: CharacterSheet) -> None:
        """Test spellcasting ability is shown."""
        result = format_character_sheet_context(wizard_sheet)
        assert "Intelligence" in result

    def test_spell_save_dc_shown(self, wizard_sheet: CharacterSheet) -> None:
        """Test spell save DC is shown."""
        result = format_character_sheet_context(wizard_sheet)
        assert "DC: 15" in result

    def test_spell_attack_bonus_shown(self, wizard_sheet: CharacterSheet) -> None:
        """Test spell attack bonus is shown."""
        result = format_character_sheet_context(wizard_sheet)
        assert "Attack: +7" in result

    def test_cantrips_listed(self, wizard_sheet: CharacterSheet) -> None:
        """Test cantrips are listed."""
        result = format_character_sheet_context(wizard_sheet)
        assert "Cantrips:" in result
        assert "Fire Bolt" in result
        assert "Mage Hand" in result

    def test_spell_slots_listed(self, wizard_sheet: CharacterSheet) -> None:
        """Test spell slots are listed."""
        result = format_character_sheet_context(wizard_sheet)
        assert "Spell Slots:" in result
        assert "L1: 3/4" in result
        assert "L2: 2/3" in result
        assert "L3: 1/2" in result

    def test_prepared_spells_listed(self, wizard_sheet: CharacterSheet) -> None:
        """Test prepared spells are listed."""
        result = format_character_sheet_context(wizard_sheet)
        assert "Prepared Spells:" in result
        assert "Magic Missile" in result
        assert "Fireball" in result
        assert "Shield" in result

    def test_no_spellcasting_for_non_caster(self, fighter_sheet: CharacterSheet) -> None:
        """Test no spellcasting section for non-casters."""
        result = format_character_sheet_context(fighter_sheet)
        assert "Spellcasting:" not in result
        assert "Cantrips:" not in result
        assert "Spell Slots:" not in result


# =============================================================================
# format_all_sheets_context Tests
# =============================================================================


class TestFormatAllSheetsContext:
    """Tests for format_all_sheets_context function."""

    def test_empty_sheets_returns_empty(self) -> None:
        """Test empty sheets dict returns empty string."""
        result = format_all_sheets_context({})
        assert result == ""

    def test_header_present(
        self, fighter_sheet: CharacterSheet, wizard_sheet: CharacterSheet
    ) -> None:
        """Test party header is present."""
        sheets = {"Thorin": fighter_sheet, "Elara": wizard_sheet}
        result = format_all_sheets_context(sheets)
        assert "## Party Character Sheets" in result

    def test_all_characters_included(
        self, fighter_sheet: CharacterSheet, wizard_sheet: CharacterSheet
    ) -> None:
        """Test all characters are included."""
        sheets = {"Thorin": fighter_sheet, "Elara": wizard_sheet}
        result = format_all_sheets_context(sheets)
        assert "Thorin" in result
        assert "Elara" in result

    def test_sheets_formatted_for_dm(
        self, fighter_sheet: CharacterSheet, wizard_sheet: CharacterSheet
    ) -> None:
        """Test sheets use DM format (not 'Your Character Sheet')."""
        sheets = {"Thorin": fighter_sheet, "Elara": wizard_sheet}
        result = format_all_sheets_context(sheets)
        assert "## Your Character Sheet" not in result
        assert "### Thorin, Dwarf Fighter" in result
        assert "### Elara, Elf Wizard" in result

    def test_sheets_sorted_alphabetically(
        self, fighter_sheet: CharacterSheet, wizard_sheet: CharacterSheet
    ) -> None:
        """Test sheets are sorted by name."""
        # Pass in reverse alphabetical order
        sheets = {"Thorin": fighter_sheet, "Elara": wizard_sheet}
        result = format_all_sheets_context(sheets)
        # Elara should appear before Thorin
        elara_pos = result.find("Elara")
        thorin_pos = result.find("Thorin")
        assert elara_pos < thorin_pos


# =============================================================================
# _build_dm_context Integration Tests
# =============================================================================


class TestBuildDMContextWithSheets:
    """Tests for _build_dm_context with character sheets."""

    def test_dm_context_includes_all_sheets(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Test DM context includes all party character sheets."""
        result = _build_dm_context(sample_game_state_with_sheets)
        assert "## Party Character Sheets" in result
        assert "Thorin" in result
        assert "Elara" in result

    def test_dm_context_empty_sheets(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Test DM context handles empty character_sheets."""
        sample_game_state_with_sheets["character_sheets"] = {}
        result = _build_dm_context(sample_game_state_with_sheets)
        assert "## Party Character Sheets" not in result

    def test_dm_context_missing_sheets(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Test DM context handles missing character_sheets key."""
        # Simulate old state without character_sheets
        del sample_game_state_with_sheets["character_sheets"]  # type: ignore
        result = _build_dm_context(sample_game_state_with_sheets)
        # Should not crash
        assert "## Party Character Sheets" not in result


# =============================================================================
# _build_pc_context Integration Tests
# =============================================================================


class TestBuildPCContextWithSheets:
    """Tests for _build_pc_context with character sheets."""

    def test_pc_context_includes_own_sheet(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Test PC context includes only their own sheet."""
        result = _build_pc_context(sample_game_state_with_sheets, "fighter")
        assert "## Your Character Sheet: Thorin" in result
        assert "Elara" not in result

    def test_pc_context_wizard_sees_own_sheet(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Test wizard PC sees their own sheet."""
        result = _build_pc_context(sample_game_state_with_sheets, "wizard")
        assert "## Your Character Sheet: Elara" in result
        assert "Thorin" not in result

    def test_pc_context_empty_sheets(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Test PC context handles empty character_sheets."""
        sample_game_state_with_sheets["character_sheets"] = {}
        result = _build_pc_context(sample_game_state_with_sheets, "fighter")
        assert "## Your Character Sheet" not in result

    def test_pc_context_missing_character_sheet(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Test PC context handles missing character sheet for agent."""
        # Remove just Thorin's sheet
        del sample_game_state_with_sheets["character_sheets"]["Thorin"]
        result = _build_pc_context(sample_game_state_with_sheets, "fighter")
        assert "## Your Character Sheet" not in result


# =============================================================================
# Edge Cases
# =============================================================================


class TestCharacterSheetContextEdgeCases:
    """Edge case tests for character sheet context injection."""

    def test_sheet_with_no_equipment(self) -> None:
        """Test formatting sheet with no equipment."""
        sheet = CharacterSheet(
            name="Monk",
            race="Human",
            character_class="Monk",
            level=1,
            strength=10,
            dexterity=16,
            constitution=12,
            intelligence=10,
            wisdom=14,
            charisma=10,
            armor_class=15,
            hit_points_max=9,
            hit_points_current=9,
            hit_dice="1d8",
            hit_dice_remaining=1,
            weapons=[],
            equipment=[],
        )
        result = format_character_sheet_context(sheet)
        # Should not crash and should not have empty Equipment line
        assert "Monk" in result
        assert result.count("Equipment:") == 0

    def test_sheet_with_all_currency_types(self) -> None:
        """Test formatting sheet with gold, silver, and copper."""
        sheet = CharacterSheet(
            name="Merchant",
            race="Human",
            character_class="Fighter",
            level=1,
            strength=14,
            dexterity=10,
            constitution=12,
            intelligence=12,
            wisdom=10,
            charisma=14,
            armor_class=16,
            hit_points_max=12,
            hit_points_current=12,
            hit_dice="1d10",
            hit_dice_remaining=1,
            gold=100,
            silver=50,
            copper=25,
        )
        result = format_character_sheet_context(sheet)
        assert "100 gold" in result
        assert "50 silver" in result
        assert "25 copper" in result

    def test_sheet_with_expertise(self) -> None:
        """Test formatting sheet with skill expertise."""
        sheet = CharacterSheet(
            name="Expert",
            race="Human",
            character_class="Rogue",
            level=1,
            strength=10,
            dexterity=16,
            constitution=10,
            intelligence=14,
            wisdom=12,
            charisma=12,
            armor_class=14,
            hit_points_max=8,
            hit_points_current=8,
            hit_dice="1d8",
            hit_dice_remaining=1,
            skill_proficiencies=["Stealth", "Perception"],
            skill_expertise=["Stealth"],
        )
        result = format_character_sheet_context(sheet)
        assert "Stealth (expertise)" in result

    def test_sheet_with_magic_weapon(self) -> None:
        """Test formatting sheet with magic weapon bonus."""
        sheet = CharacterSheet(
            name="Hero",
            race="Human",
            character_class="Fighter",
            level=5,
            strength=18,
            dexterity=10,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=18,
            hit_points_max=44,
            hit_points_current=44,
            hit_dice="5d10",
            hit_dice_remaining=5,
            weapons=[
                Weapon(
                    name="Flametongue",
                    damage_dice="1d8+2",
                    damage_type="slashing",
                    attack_bonus=2,
                ),
            ],
        )
        result = format_character_sheet_context(sheet)
        # Level 5 proficiency +3, STR +4, magic +2 = +9
        assert "(+9, 1d8+2 slashing)" in result

    def test_sheet_with_zero_current_hp(self) -> None:
        """Test formatting sheet with 0 HP (unconscious)."""
        sheet = CharacterSheet(
            name="Fallen",
            race="Human",
            character_class="Fighter",
            level=1,
            strength=14,
            dexterity=10,
            constitution=12,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=16,
            hit_points_max=12,
            hit_points_current=0,
            hit_dice="1d10",
            hit_dice_remaining=1,
        )
        result = format_character_sheet_context(sheet)
        assert "HP: 0/12" in result
