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
    format_all_sheets_context,
    format_character_sheet_context,
)
from models import (
    AgentMemory,
    Armor,
    CharacterConfig,
    CharacterFacts,
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
# Modifier Formatting Tests (via public API)
# =============================================================================


class TestModifierFormatting:
    """Tests for modifier formatting through format_character_sheet_context."""

    def test_positive_modifier_in_ability_scores(self) -> None:
        """Test positive modifiers appear correctly in ability scores."""
        sheet = CharacterSheet(
            name="Hero", race="Human", character_class="Fighter", level=1,
            strength=18, dexterity=10, constitution=10, intelligence=10,
            wisdom=10, charisma=10, armor_class=10, hit_points_max=10,
            hit_points_current=10, hit_dice="1d10", hit_dice_remaining=1,
        )
        result = format_character_sheet_context(sheet)
        assert "(+4)" in result  # STR 18 = +4

    def test_negative_modifier_in_ability_scores(self) -> None:
        """Test negative modifiers appear correctly in ability scores."""
        sheet = CharacterSheet(
            name="Hero", race="Human", character_class="Fighter", level=1,
            strength=8, dexterity=10, constitution=10, intelligence=10,
            wisdom=10, charisma=10, armor_class=10, hit_points_max=10,
            hit_points_current=10, hit_dice="1d10", hit_dice_remaining=1,
        )
        result = format_character_sheet_context(sheet)
        assert "(-1)" in result  # STR 8 = -1

    def test_zero_modifier_in_ability_scores(self) -> None:
        """Test zero modifiers appear correctly in ability scores."""
        sheet = CharacterSheet(
            name="Hero", race="Human", character_class="Fighter", level=1,
            strength=10, dexterity=10, constitution=10, intelligence=10,
            wisdom=10, charisma=10, armor_class=10, hit_points_max=10,
            hit_points_current=10, hit_dice="1d10", hit_dice_remaining=1,
        )
        result = format_character_sheet_context(sheet)
        assert "(+0)" in result  # STR 10 = +0


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

    def test_skills_listed_with_modifiers(self, fighter_sheet: CharacterSheet) -> None:
        """Test skills are included with calculated modifiers per AC3."""
        result = format_character_sheet_context(fighter_sheet)
        # Fighter level 5: proficiency +3
        # Athletics: STR +4, prof +3 = +7
        # Intimidation: CHA -1, prof +3 = +2
        # Perception: WIS +2, prof +3 = +5
        assert "Athletics (+7)" in result
        assert "Intimidation (+2)" in result
        assert "Perception (+5)" in result

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

    def test_currency_in_inventory(self, fighter_sheet: CharacterSheet) -> None:
        """Test currency is included in the Inventory line per AC3."""
        result = format_character_sheet_context(fighter_sheet)
        assert "47 gold" in result
        # Currency should be part of Inventory line, not separate
        for line in result.split("\n"):
            if "47 gold" in line:
                assert line.startswith("Inventory:")
                break

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
        # Rogue level 1: proficiency +2, DEX +3
        # Stealth expertise: DEX +3, prof x2 = +3 + 4 = +7
        # Perception proficiency: WIS +1, prof +2 = +3
        assert "Stealth (+7)" in result
        assert "Perception (+3)" in result

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


# =============================================================================
# Additional Edge Cases for format_character_sheet_context
# =============================================================================


class TestFormatCharacterSheetContextAdditionalEdgeCases:
    """Additional edge case tests for format_character_sheet_context."""

    def test_sheet_with_only_racial_traits(self) -> None:
        """Test formatting sheet with only racial traits (no class features or feats)."""
        sheet = CharacterSheet(
            name="Elf Scout",
            race="Wood Elf",
            character_class="Ranger",
            level=1,
            strength=10,
            dexterity=16,
            constitution=12,
            intelligence=12,
            wisdom=14,
            charisma=10,
            armor_class=14,
            hit_points_max=11,
            hit_points_current=11,
            hit_dice="1d10",
            hit_dice_remaining=1,
            racial_traits=["Darkvision", "Keen Senses", "Fey Ancestry", "Mask of the Wild"],
            class_features=[],
            feats=[],
        )
        result = format_character_sheet_context(sheet)
        assert "Features:" in result
        assert "Darkvision" in result
        assert "Keen Senses" in result
        assert "Fey Ancestry" in result
        assert "Mask of the Wild" in result

    def test_sheet_with_all_three_feature_types(self) -> None:
        """Test formatting sheet with class features, racial traits, and feats."""
        sheet = CharacterSheet(
            name="Veteran",
            race="Half-Orc",
            character_class="Fighter",
            level=4,
            strength=18,
            dexterity=12,
            constitution=16,
            intelligence=10,
            wisdom=10,
            charisma=8,
            armor_class=18,
            hit_points_max=40,
            hit_points_current=40,
            hit_dice="4d10",
            hit_dice_remaining=4,
            class_features=["Second Wind", "Action Surge"],
            racial_traits=["Darkvision", "Relentless Endurance", "Savage Attacks"],
            feats=["Great Weapon Master"],
        )
        result = format_character_sheet_context(sheet)
        assert "Features:" in result
        # All features should be listed together
        assert "Second Wind" in result
        assert "Action Surge" in result
        assert "Darkvision" in result
        assert "Relentless Endurance" in result
        assert "Great Weapon Master" in result

    def test_sheet_with_multiple_armor_and_tool_proficiencies(self) -> None:
        """Test formatting with multiple armor proficiencies and tool proficiencies."""
        sheet = CharacterSheet(
            name="Artisan",
            race="Dwarf",
            character_class="Fighter",
            level=1,
            strength=16,
            dexterity=10,
            constitution=14,
            intelligence=12,
            wisdom=10,
            charisma=8,
            armor_class=16,
            hit_points_max=12,
            hit_points_current=12,
            hit_dice="1d10",
            hit_dice_remaining=1,
            armor_proficiencies=["Light armor", "Medium armor", "Heavy armor", "Shields"],
            tool_proficiencies=["Smith's tools", "Brewer's supplies", "Mason's tools"],
        )
        result = format_character_sheet_context(sheet)
        assert "Proficiencies:" in result
        assert "Light armor" in result
        assert "Heavy armor" in result
        assert "Shields" in result
        assert "Smith's tools" in result
        assert "Brewer's supplies" in result
        assert "Mason's tools" in result
        # Verify tools are in the Tools section
        assert "Tools: Smith's tools, Brewer's supplies, Mason's tools" in result

    def test_sheet_with_ranged_weapon_uses_dex(self) -> None:
        """Test ranged weapons use DEX modifier for attack bonus."""
        sheet = CharacterSheet(
            name="Archer",
            race="Human",
            character_class="Ranger",
            level=5,
            strength=10,
            dexterity=18,
            constitution=12,
            intelligence=10,
            wisdom=14,
            charisma=10,
            armor_class=15,
            hit_points_max=38,
            hit_points_current=38,
            hit_dice="5d10",
            hit_dice_remaining=5,
            weapons=[
                Weapon(
                    name="Longbow",
                    damage_dice="1d8",
                    damage_type="piercing",
                    properties=["ammunition", "heavy", "two-handed"],
                ),
            ],
        )
        result = format_character_sheet_context(sheet)
        # Level 5 proficiency +3, DEX +4 = +7
        assert "(+7, 1d8 piercing)" in result

    def test_sheet_with_no_skills(self) -> None:
        """Test formatting sheet with no skills at all."""
        sheet = CharacterSheet(
            name="Unskilled",
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
            hit_points_current=12,
            hit_dice="1d10",
            hit_dice_remaining=1,
            skill_proficiencies=[],
            skill_expertise=[],
        )
        result = format_character_sheet_context(sheet)
        assert "Skills:" not in result

    def test_sheet_with_only_expertise_skills(self) -> None:
        """Test formatting sheet with only expertise skills (no regular proficiencies)."""
        sheet = CharacterSheet(
            name="Expert Rogue",
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
            skill_proficiencies=[],
            skill_expertise=["Stealth", "Thieves' Tools"],
        )
        result = format_character_sheet_context(sheet)
        assert "Skills:" in result
        # Expertise: ability mod + proficiency * 2
        # Stealth: DEX +3, prof 2x2=4 = +7
        assert "Stealth (+7)" in result

    def test_sheet_with_multiple_conditions(self) -> None:
        """Test formatting sheet with multiple conditions."""
        sheet = CharacterSheet(
            name="Afflicted",
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
            hit_points_current=8,
            hit_dice="1d10",
            hit_dice_remaining=1,
            conditions=["poisoned", "frightened", "exhausted"],
        )
        result = format_character_sheet_context(sheet)
        assert "Conditions: poisoned, frightened, exhausted" in result

    def test_sheet_with_zero_gold_but_silver_copper(self) -> None:
        """Test formatting sheet with 0 gold but silver/copper present."""
        sheet = CharacterSheet(
            name="Poor",
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
            hit_points_current=12,
            hit_dice="1d10",
            hit_dice_remaining=1,
            gold=0,
            silver=15,
            copper=30,
        )
        result = format_character_sheet_context(sheet)
        # Gold should NOT appear since it's 0
        assert "gold" not in result.lower() or "0 gold" not in result
        assert "15 silver" in result
        assert "30 copper" in result

    def test_sheet_with_temp_hp_displayed_correctly(self) -> None:
        """Test temp HP is displayed correctly in the HP line."""
        sheet = CharacterSheet(
            name="Buffed",
            race="Human",
            character_class="Fighter",
            level=5,
            strength=16,
            dexterity=12,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=18,
            hit_points_max=44,
            hit_points_current=44,
            hit_dice="5d10",
            hit_dice_remaining=5,
            hit_points_temp=15,
        )
        result = format_character_sheet_context(sheet)
        assert "HP: 44/44 (+15 temp)" in result

    def test_sheet_at_level_1_proficiency_bonus(self) -> None:
        """Test level 1 character has +2 proficiency bonus."""
        sheet = CharacterSheet(
            name="Novice",
            race="Human",
            character_class="Fighter",
            level=1,
            strength=16,
            dexterity=10,
            constitution=14,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=16,
            hit_points_max=12,
            hit_points_current=12,
            hit_dice="1d10",
            hit_dice_remaining=1,
            skill_proficiencies=["Athletics"],
            weapons=[
                Weapon(name="Longsword", damage_dice="1d8", damage_type="slashing"),
            ],
        )
        result = format_character_sheet_context(sheet)
        # Level 1 proficiency +2, STR +3
        # Athletics: STR +3 + prof +2 = +5
        assert "Athletics (+5)" in result
        # Weapon: prof +2 + STR +3 = +5
        assert "(+5, 1d8 slashing)" in result

    def test_sheet_at_level_17_proficiency_bonus(self) -> None:
        """Test level 17 character has +6 proficiency bonus."""
        sheet = CharacterSheet(
            name="Legend",
            race="Human",
            character_class="Fighter",
            level=17,
            strength=20,
            dexterity=10,
            constitution=16,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=20,
            hit_points_max=180,
            hit_points_current=180,
            hit_dice="17d10",
            hit_dice_remaining=17,
            skill_proficiencies=["Athletics"],
            weapons=[
                Weapon(name="Greatsword", damage_dice="2d6", damage_type="slashing"),
            ],
        )
        result = format_character_sheet_context(sheet)
        # Level 17 proficiency +6, STR +5
        # Athletics: STR +5 + prof +6 = +11
        assert "Athletics (+11)" in result
        # Weapon: prof +6 + STR +5 = +11
        assert "(+11, 2d6 slashing)" in result


# =============================================================================
# Additional format_all_sheets_context Tests
# =============================================================================


class TestFormatAllSheetsContextAdditional:
    """Additional tests for format_all_sheets_context function."""

    def test_single_character_sheet(self, fighter_sheet: CharacterSheet) -> None:
        """Test format_all_sheets_context with a single character sheet."""
        sheets = {"Thorin": fighter_sheet}
        result = format_all_sheets_context(sheets)
        assert "## Party Character Sheets" in result
        assert "Thorin" in result
        # Should use DM format (not "Your Character Sheet")
        assert "## Your Character Sheet" not in result

    def test_three_or_more_sheets_sorted(self, fighter_sheet: CharacterSheet, wizard_sheet: CharacterSheet) -> None:
        """Test three or more character sheets are sorted alphabetically."""
        rogue_sheet = CharacterSheet(
            name="Shadowmere",
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
        )
        # Provide sheets in non-alphabetical order
        sheets = {
            "Thorin": fighter_sheet,
            "Shadowmere": rogue_sheet,
            "Elara": wizard_sheet,
        }
        result = format_all_sheets_context(sheets)
        # Should be sorted: Elara, Shadowmere, Thorin
        elara_pos = result.find("Elara")
        shadow_pos = result.find("Shadowmere")
        thorin_pos = result.find("Thorin")
        assert elara_pos < shadow_pos < thorin_pos

    def test_mixed_spellcasters_and_non_spellcasters(
        self, fighter_sheet: CharacterSheet, wizard_sheet: CharacterSheet
    ) -> None:
        """Test sheets with both spellcasters and non-spellcasters mixed."""
        sheets = {"Thorin": fighter_sheet, "Elara": wizard_sheet}
        result = format_all_sheets_context(sheets)
        # Fighter shouldn't have spellcasting section
        # Find Thorin's section and check no spellcasting before next header
        thorin_start = result.find("### Thorin")
        elara_start = result.find("### Elara")
        # Since Elara comes before Thorin alphabetically
        assert elara_start < thorin_start
        thorin_section = result[thorin_start:]
        # Thorin (fighter) section should NOT have "Spellcasting:"
        assert "Spellcasting:" not in thorin_section
        # Elara's section (wizard) should have spellcasting
        elara_section = result[elara_start:thorin_start]
        assert "Spellcasting:" in elara_section


# =============================================================================
# Additional _build_dm_context Integration Tests
# =============================================================================


class TestBuildDMContextWithSheetsAdditional:
    """Additional integration tests for _build_dm_context with character sheets."""

    def test_dm_context_with_sheets_and_character_facts(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Test DM context includes both character sheets AND character facts."""
        # Add character facts to fighter memory
        fighter_memory = sample_game_state_with_sheets["agent_memories"]["fighter"]
        updated_memory = fighter_memory.model_copy(
            update={
                "character_facts": CharacterFacts(
                    name="Thorin",
                    character_class="Fighter",
                    key_traits=["Brave", "Stubborn"],
                    relationships={"Elara": "Trusted ally"},
                    notable_events=["Defeated the goblin king"],
                ),
            }
        )
        sample_game_state_with_sheets["agent_memories"]["fighter"] = updated_memory

        result = _build_dm_context(sample_game_state_with_sheets)
        # Both sections should be present
        assert "## Party Character Sheets" in result
        assert "## Party Members" in result
        assert "Brave" in result
        assert "Trusted ally" in result

    def test_dm_context_with_sheets_and_long_term_summary_and_buffer(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Test DM context includes sheets, long-term summary, AND short-term buffer."""
        # Add long-term summary and buffer entries to DM memory
        dm_memory = sample_game_state_with_sheets["agent_memories"]["dm"]
        updated_dm = dm_memory.model_copy(
            update={
                "long_term_summary": "The party entered the dungeon and fought goblins.",
                "short_term_buffer": [
                    "[DM]: You enter a dark corridor.",
                    "[Thorin]: I draw my sword.",
                    "[Elara]: I cast Light.",
                ],
            }
        )
        sample_game_state_with_sheets["agent_memories"]["dm"] = updated_dm

        result = _build_dm_context(sample_game_state_with_sheets)
        assert "## Story So Far" in result
        assert "The party entered the dungeon" in result
        assert "## Recent Events" in result
        assert "dark corridor" in result
        assert "## Party Character Sheets" in result
        assert "Thorin, Dwarf Fighter" in result
        assert "Elara, Elf Wizard" in result


# =============================================================================
# Additional _build_pc_context Integration Tests
# =============================================================================


class TestBuildPCContextWithSheetsAdditional:
    """Additional integration tests for _build_pc_context with character sheets."""

    def test_pc_context_with_sheet_and_facts_and_memory(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Test PC context includes sheet AND character facts AND memory."""
        # Add character facts and memory to fighter
        fighter_memory = sample_game_state_with_sheets["agent_memories"]["fighter"]
        updated_memory = fighter_memory.model_copy(
            update={
                "character_facts": CharacterFacts(
                    name="Thorin",
                    character_class="Fighter",
                    key_traits=["Brave"],
                ),
                "long_term_summary": "We entered the dungeon yesterday.",
                "short_term_buffer": ["[DM]: A dragon appears!"],
            }
        )
        sample_game_state_with_sheets["agent_memories"]["fighter"] = updated_memory

        result = _build_pc_context(sample_game_state_with_sheets, "fighter")
        # Should have character identity section
        assert "## Character Identity" in result
        assert "Brave" in result
        # Should have memory sections
        assert "## What You Remember" in result
        assert "We entered the dungeon" in result
        assert "## Recent Events" in result
        assert "dragon appears" in result
        # Should have own character sheet
        assert "## Your Character Sheet: Thorin" in result

    def test_pc_agent_with_no_matching_character_config(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Test PC context when agent has no matching character config in state."""
        # Add a memory for an agent that isn't in characters dict
        sample_game_state_with_sheets["agent_memories"]["ranger"] = AgentMemory(
            token_limit=4000,
            short_term_buffer=["[DM]: The forest is dense."],
        )

        result = _build_pc_context(sample_game_state_with_sheets, "ranger")
        # Should not crash, but no character sheet should be present
        assert "## Your Character Sheet" not in result
        # Should still have recent events from its own memory
        assert "The forest is dense" in result

    def test_pc_cannot_see_other_pc_sheets(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Verify PC can't see other PC sheets (cross-check multiple agents)."""
        # Fighter should only see Thorin's sheet
        fighter_result = _build_pc_context(sample_game_state_with_sheets, "fighter")
        assert "Thorin" in fighter_result
        assert "Elara" not in fighter_result

        # Wizard should only see Elara's sheet
        wizard_result = _build_pc_context(sample_game_state_with_sheets, "wizard")
        assert "Elara" in wizard_result
        assert "Thorin" not in wizard_result

    def test_pc_context_with_sheet_shows_correct_format(
        self, sample_game_state_with_sheets: GameState
    ) -> None:
        """Test PC context uses 'Your Character Sheet' format for own sheet."""
        result = _build_pc_context(sample_game_state_with_sheets, "fighter")
        assert "## Your Character Sheet: Thorin, Dwarf Fighter (Level 5)" in result
        # Should NOT use the DM format (###)
        assert "### Thorin" not in result


# =============================================================================
# Spellcasting Edge Cases
# =============================================================================


class TestSpellcastingEdgeCases:
    """Edge case tests for spellcasting section in format_character_sheet_context."""

    def test_caster_with_no_spells_known_but_with_slots(self) -> None:
        """Test caster with spell slots but no spells known."""
        sheet = CharacterSheet(
            name="Forgetful Wizard",
            race="Human",
            character_class="Wizard",
            level=3,
            strength=8,
            dexterity=14,
            constitution=12,
            intelligence=16,
            wisdom=10,
            charisma=10,
            armor_class=12,
            hit_points_max=17,
            hit_points_current=17,
            hit_dice="3d6",
            hit_dice_remaining=3,
            spellcasting_ability="intelligence",
            spell_save_dc=13,
            spell_attack_bonus=5,
            spell_slots={
                1: SpellSlots(current=4, max=4),
                2: SpellSlots(current=2, max=2),
            },
            spells_known=[],
            cantrips=[],
        )
        result = format_character_sheet_context(sheet)
        assert "Spellcasting:" in result
        assert "Spell Slots:" in result
        assert "L1: 4/4" in result
        assert "L2: 2/2" in result
        # No prepared spells section since none known
        assert "Prepared Spells:" not in result

    def test_caster_with_cantrips_only(self) -> None:
        """Test caster with cantrips but no spell slots."""
        sheet = CharacterSheet(
            name="Cantrip Master",
            race="High Elf",
            character_class="Wizard",
            level=1,
            strength=8,
            dexterity=14,
            constitution=12,
            intelligence=16,
            wisdom=10,
            charisma=10,
            armor_class=12,
            hit_points_max=7,
            hit_points_current=7,
            hit_dice="1d6",
            hit_dice_remaining=1,
            spellcasting_ability="intelligence",
            spell_save_dc=13,
            spell_attack_bonus=5,
            cantrips=["Fire Bolt", "Mage Hand", "Prestidigitation"],
            spell_slots={},
            spells_known=[],
        )
        result = format_character_sheet_context(sheet)
        assert "Spellcasting:" in result
        assert "Cantrips:" in result
        assert "Fire Bolt" in result
        # No spell slots section since dict is empty
        assert "Spell Slots:" not in result

    def test_spell_attack_bonus_of_zero(self) -> None:
        """Test spell attack bonus of 0 shows '+0'."""
        sheet = CharacterSheet(
            name="Weak Caster",
            race="Human",
            character_class="Wizard",
            level=1,
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=6,
            hit_points_current=6,
            hit_dice="1d6",
            hit_dice_remaining=1,
            spellcasting_ability="intelligence",
            spell_save_dc=10,
            spell_attack_bonus=0,
            cantrips=["Fire Bolt"],
        )
        result = format_character_sheet_context(sheet)
        assert "Attack: +0" in result

    def test_empty_spell_slots_dict(self) -> None:
        """Test caster with empty spell_slots dict (no slots at all)."""
        sheet = CharacterSheet(
            name="Slotless",
            race="Human",
            character_class="Warlock",
            level=1,
            strength=10,
            dexterity=14,
            constitution=12,
            intelligence=10,
            wisdom=10,
            charisma=16,
            armor_class=12,
            hit_points_max=9,
            hit_points_current=9,
            hit_dice="1d8",
            hit_dice_remaining=1,
            spellcasting_ability="charisma",
            spell_save_dc=13,
            spell_attack_bonus=5,
            spell_slots={},
            cantrips=["Eldritch Blast"],
            spells_known=[
                Spell(
                    name="Hex",
                    level=1,
                    school="enchantment",
                    description="Curse a creature",
                ),
            ],
        )
        result = format_character_sheet_context(sheet)
        assert "Spellcasting:" in result
        assert "Spell Slots:" not in result
        assert "Prepared Spells:" in result
        assert "Hex" in result


# =============================================================================
# Boundary Tests
# =============================================================================


class TestBoundaryTests:
    """Boundary tests for character sheet context formatting."""

    def test_very_long_character_name(self) -> None:
        """Test formatting with a very long character name."""
        long_name = "Bartholomew Ignatius Cornelius Von Stravaganza III"
        sheet = CharacterSheet(
            name=long_name,
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
            hit_points_current=12,
            hit_dice="1d10",
            hit_dice_remaining=1,
        )
        result = format_character_sheet_context(sheet)
        assert long_name in result
        assert f"## Your Character Sheet: {long_name}" in result

    def test_empty_string_fields(self) -> None:
        """Test formatting with empty string fields (background, alignment)."""
        sheet = CharacterSheet(
            name="Minimal",
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
            background="",
            alignment="",
            personality_traits="",
            ideals="",
            bonds="",
            flaws="",
        )
        result = format_character_sheet_context(sheet)
        # Should not crash and should contain core info
        assert "Minimal" in result
        assert "Human Fighter" in result
        assert "HP: 10/10" in result

    def test_equipment_item_with_quantity_one_no_parentheses(self) -> None:
        """Test equipment item with quantity of exactly 1 has no parentheses."""
        sheet = CharacterSheet(
            name="Light Traveler",
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
            hit_points_current=12,
            hit_dice="1d10",
            hit_dice_remaining=1,
            equipment=[
                EquipmentItem(name="Bedroll", quantity=1),
            ],
        )
        result = format_character_sheet_context(sheet)
        assert "Bedroll" in result
        # Should NOT have parentheses for quantity 1
        assert "Bedroll (1)" not in result

    def test_equipment_item_with_quantity_greater_than_one(self) -> None:
        """Test equipment item with quantity > 1 shows parentheses."""
        sheet = CharacterSheet(
            name="Prepared",
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
            hit_points_current=12,
            hit_dice="1d10",
            hit_dice_remaining=1,
            equipment=[
                EquipmentItem(name="Healing Potion", quantity=3),
                EquipmentItem(name="Pitons", quantity=10),
                EquipmentItem(name="Waterskin", quantity=1),
            ],
        )
        result = format_character_sheet_context(sheet)
        assert "Healing Potion (3)" in result
        assert "Pitons (10)" in result
        assert "Waterskin" in result
        # Waterskin should NOT have (1)
        assert "Waterskin (1)" not in result

    def test_no_conditions_shows_none(self) -> None:
        """Test that no conditions shows 'Conditions: None'."""
        sheet = CharacterSheet(
            name="Healthy",
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
            hit_points_current=12,
            hit_dice="1d10",
            hit_dice_remaining=1,
            conditions=[],
        )
        result = format_character_sheet_context(sheet)
        assert "Conditions: None" in result

    def test_no_features_no_features_line(self) -> None:
        """Test that empty features lists produce no Features line."""
        sheet = CharacterSheet(
            name="Bare",
            race="Human",
            character_class="Commoner",
            level=1,
            strength=10,
            dexterity=10,
            constitution=10,
            intelligence=10,
            wisdom=10,
            charisma=10,
            armor_class=10,
            hit_points_max=4,
            hit_points_current=4,
            hit_dice="1d4",
            hit_dice_remaining=1,
            class_features=[],
            racial_traits=[],
            feats=[],
        )
        result = format_character_sheet_context(sheet)
        assert "Features:" not in result
