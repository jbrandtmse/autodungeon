"""Tests for Story 15.2: Initiative Rolling & Turn Reordering.

Tests for roll_initiative(), _sanitize_npc_name(), _execute_start_combat(),
_execute_end_combat(), and DM tool binding for combat tools.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from models import (
    AgentMemory,
    AgentSecrets,
    CallbackLog,
    CharacterConfig,
    CharacterSheet,
    CombatState,
    DMConfig,
    GameConfig,
    GameState,
    NarrativeElementStore,
    NpcProfile,
)
from tools import _sanitize_npc_name, roll_initiative

# =============================================================================
# Fixtures
# =============================================================================


def _make_character_sheet(initiative: int = 0, **kwargs: object) -> CharacterSheet:
    """Build a minimal CharacterSheet with the given initiative modifier."""
    defaults: dict[str, object] = {
        "name": "Test",
        "race": "Human",
        "character_class": "Fighter",
        "level": 1,
        "strength": 10,
        "dexterity": 10 + (initiative * 2),  # initiative = (dex-10)//2
        "constitution": 10,
        "intelligence": 10,
        "wisdom": 10,
        "charisma": 10,
        "armor_class": 10,
        "initiative": initiative,
        "speed": 30,
        "hit_points_max": 10,
        "hit_points_current": 10,
        "hit_dice": "1d10",
        "hit_dice_remaining": 1,
        "proficiency_bonus": 2,
        "saving_throws": [],
        "skills": [],
        "languages": ["Common"],
        "equipment": [],
        "features": [],
        "background": "Soldier",
        "alignment": "Neutral",
    }
    defaults.update(kwargs)
    return CharacterSheet(**defaults)  # type: ignore[arg-type]


def _make_game_state(
    combat_mode: str = "Tactical",
    turn_queue: list[str] | None = None,
    character_sheets: dict[str, CharacterSheet] | None = None,
    combat_state: CombatState | None = None,
) -> GameState:
    """Build a minimal GameState for combat testing."""
    if turn_queue is None:
        turn_queue = ["dm", "shadowmere", "thorin"]
    if character_sheets is None:
        character_sheets = {}
    if combat_state is None:
        combat_state = CombatState()

    return GameState(
        ground_truth_log=["[DM]: The adventure begins."],
        turn_queue=turn_queue,
        current_turn="dm",
        agent_memories={
            "dm": AgentMemory(token_limit=8000),
        },
        game_config=GameConfig(
            combat_mode=combat_mode,  # type: ignore[arg-type]
            summarizer_model="gemini-1.5-flash",
            party_size=2,
        ),
        dm_config=DMConfig(
            name="Dungeon Master",
            provider="gemini",
            model="gemini-1.5-flash",
            token_limit=8000,
            color="#D4A574",
        ),
        characters={
            "shadowmere": CharacterConfig(
                name="Shadowmere",
                character_class="Rogue",
                personality="Stealthy",
                color="#8B4513",
                provider="gemini",
                model="gemini-1.5-flash",
                token_limit=4000,
            ),
            "thorin": CharacterConfig(
                name="Thorin",
                character_class="Fighter",
                personality="Brave",
                color="#C9A45C",
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
        character_sheets=character_sheets,
        agent_secrets={"dm": AgentSecrets()},
        narrative_elements={},
        callback_database=NarrativeElementStore(),
        callback_log=CallbackLog(),
        active_fork_id=None,
        combat_state=combat_state,
    )


def _make_dice_result(total: int) -> MagicMock:
    """Create a mock DiceResult with the given total."""
    result = MagicMock()
    result.total = total
    return result


# =============================================================================
# TestSanitizeNpcName
# =============================================================================


class TestSanitizeNpcName:
    """Tests for _sanitize_npc_name() helper."""

    def test_basic_sanitization(self) -> None:
        """'Goblin 1' becomes 'goblin_1'."""
        assert _sanitize_npc_name("Goblin 1") == "goblin_1"

    def test_already_lowercase(self) -> None:
        """'wolf' stays 'wolf'."""
        assert _sanitize_npc_name("wolf") == "wolf"

    def test_multi_word(self) -> None:
        """'Bug Bear Chief' becomes 'bug_bear_chief'."""
        assert _sanitize_npc_name("Bug Bear Chief") == "bug_bear_chief"

    def test_whitespace_trimming(self) -> None:
        """Leading/trailing whitespace is stripped."""
        assert _sanitize_npc_name("  Goblin 2  ") == "goblin_2"

    def test_mixed_case(self) -> None:
        """Mixed case is lowered."""
        assert _sanitize_npc_name("DIRE Wolf") == "dire_wolf"


# =============================================================================
# TestRollInitiative
# =============================================================================


class TestRollInitiative:
    """Tests for roll_initiative() function."""

    @patch("tools.roll_dice")
    def test_basic_roll_structure(self, mock_roll: MagicMock) -> None:
        """Roll with 2 PCs and 1 NPC produces correct structure."""
        # PC rolls: 15, 10. NPC roll: 12
        mock_roll.side_effect = [
            _make_dice_result(15),
            _make_dice_result(10),
            _make_dice_result(12),
        ]
        sheets = {
            "shadowmere": _make_character_sheet(initiative=3),
            "thorin": _make_character_sheet(initiative=1),
        }
        npcs = {
            "goblin_1": NpcProfile(name="Goblin 1", initiative_modifier=2),
        }
        rolls, order = roll_initiative(["shadowmere", "thorin"], sheets, npcs)

        # Verify all combatants have roll entries
        assert "shadowmere" in rolls
        assert "thorin" in rolls
        assert "dm:goblin_1" in rolls

        # Verify totals: d20 + modifier
        assert rolls["shadowmere"] == 18  # 15 + 3
        assert rolls["thorin"] == 11  # 10 + 1
        assert rolls["dm:goblin_1"] == 14  # 12 + 2

    @patch("tools.roll_dice")
    def test_initiative_order_starts_with_dm_bookend(
        self, mock_roll: MagicMock
    ) -> None:
        """Initiative order always starts with 'dm' bookend."""
        mock_roll.side_effect = [_make_dice_result(10), _make_dice_result(10)]
        sheets = {"fighter": _make_character_sheet(initiative=0)}
        npcs = {"goblin_1": NpcProfile(name="Goblin 1")}

        _, order = roll_initiative(["fighter"], sheets, npcs)
        assert order[0] == "dm"

    @patch("tools.roll_dice")
    def test_npc_entries_use_dm_prefix(self, mock_roll: MagicMock) -> None:
        """NPC entries in initiative_order use 'dm:npc_key' format."""
        mock_roll.side_effect = [_make_dice_result(5), _make_dice_result(15)]
        npcs = {"goblin_1": NpcProfile(name="Goblin 1", initiative_modifier=2)}

        _, order = roll_initiative(["fighter"], {}, npcs)
        assert "dm:goblin_1" in order

    @patch("tools.roll_dice")
    def test_sort_order_descending_by_total(self, mock_roll: MagicMock) -> None:
        """Combatants sorted by total roll descending."""
        # Shadowmere: 20+3=23, Thorin: 5+1=6, Goblin: 15+2=17
        mock_roll.side_effect = [
            _make_dice_result(20),
            _make_dice_result(5),
            _make_dice_result(15),
        ]
        sheets = {
            "shadowmere": _make_character_sheet(initiative=3),
            "thorin": _make_character_sheet(initiative=1),
        }
        npcs = {"goblin_1": NpcProfile(name="Goblin 1", initiative_modifier=2)}

        _, order = roll_initiative(["shadowmere", "thorin"], sheets, npcs)
        # order[0] = "dm", then sorted by total desc
        assert order == ["dm", "shadowmere", "dm:goblin_1", "thorin"]

    @patch("tools.roll_dice")
    def test_tie_breaking_by_modifier(self, mock_roll: MagicMock) -> None:
        """Same total, higher modifier wins."""
        # Both roll 10. Shadowmere mod +3 (total=13), Thorin mod +1 (total=11)
        # Wait, same TOTAL means d20+mod is same. Let me set it up properly.
        # Shadowmere: d20=10, mod=3 -> total=13
        # Thorin: d20=12, mod=1 -> total=13 (same total)
        mock_roll.side_effect = [
            _make_dice_result(10),  # shadowmere d20
            _make_dice_result(12),  # thorin d20
        ]
        sheets = {
            "shadowmere": _make_character_sheet(initiative=3),
            "thorin": _make_character_sheet(initiative=1),
        }

        _, order = roll_initiative(["shadowmere", "thorin"], sheets, {})
        # Both total=13, shadowmere has higher modifier (3 > 1)
        assert order == ["dm", "shadowmere", "thorin"]

    @patch("tools.roll_dice")
    def test_tie_breaking_by_name(self, mock_roll: MagicMock) -> None:
        """Same total and same modifier, alphabetical name ascending wins."""
        # alpha: d20=10, mod=2 -> 12
        # beta:  d20=10, mod=2 -> 12
        mock_roll.side_effect = [
            _make_dice_result(10),
            _make_dice_result(10),
        ]
        sheets = {
            "alpha": _make_character_sheet(initiative=2),
            "beta": _make_character_sheet(initiative=2),
        }

        _, order = roll_initiative(["alpha", "beta"], sheets, {})
        assert order == ["dm", "alpha", "beta"]

    @patch("tools.roll_dice")
    def test_pc_with_no_character_sheet(self, mock_roll: MagicMock) -> None:
        """PC with no sheet uses modifier 0."""
        mock_roll.side_effect = [_make_dice_result(15)]

        rolls, order = roll_initiative(["unknown_pc"], {}, {})
        assert rolls["unknown_pc"] == 15  # 15 + 0
        assert order == ["dm", "unknown_pc"]

    @patch("tools.roll_dice")
    def test_empty_npc_list(self, mock_roll: MagicMock) -> None:
        """PCs only (no NPCs) still works."""
        mock_roll.side_effect = [_make_dice_result(10), _make_dice_result(15)]
        sheets = {
            "fighter": _make_character_sheet(initiative=0),
            "rogue": _make_character_sheet(initiative=3),
        }

        rolls, order = roll_initiative(["fighter", "rogue"], sheets, {})
        assert len(rolls) == 2
        assert "dm" not in rolls  # dm is bookend, not a combatant
        assert order[0] == "dm"
        # rogue: 15+3=18, fighter: 10+0=10
        assert order == ["dm", "rogue", "fighter"]

    @patch("tools.roll_dice")
    def test_empty_pc_list(self, mock_roll: MagicMock) -> None:
        """No PCs (edge case) still works with NPCs only."""
        mock_roll.side_effect = [_make_dice_result(10)]
        npcs = {"goblin_1": NpcProfile(name="Goblin 1", initiative_modifier=2)}

        rolls, order = roll_initiative([], {}, npcs)
        assert len(rolls) == 1
        assert rolls["dm:goblin_1"] == 12
        assert order == ["dm", "dm:goblin_1"]

    @patch("tools.roll_dice")
    def test_all_combatants_in_initiative_rolls(self, mock_roll: MagicMock) -> None:
        """Every combatant gets an entry in initiative_rolls dict."""
        mock_roll.side_effect = [
            _make_dice_result(10),
            _make_dice_result(12),
            _make_dice_result(8),
        ]
        sheets = {"pc1": _make_character_sheet(initiative=1)}
        npcs = {
            "npc_a": NpcProfile(name="NPC A", initiative_modifier=0),
            "npc_b": NpcProfile(name="NPC B", initiative_modifier=3),
        }

        rolls, _ = roll_initiative(["pc1"], sheets, npcs)
        assert set(rolls.keys()) == {"pc1", "dm:npc_a", "dm:npc_b"}


# =============================================================================
# TestExecuteStartCombat
# =============================================================================


class TestExecuteStartCombat:
    """Tests for _execute_start_combat() helper."""

    @patch("agents.roll_initiative")
    def test_tactical_mode_returns_active_combat_state(
        self, mock_init: MagicMock
    ) -> None:
        """Tactical mode returns CombatState with active=True, round_number=1."""
        mock_init.return_value = (
            {"shadowmere": 18, "dm:goblin_1": 14},
            ["dm", "shadowmere", "dm:goblin_1"],
        )
        state = _make_game_state(combat_mode="Tactical")
        tool_args = {
            "participants": [
                {"name": "Goblin 1", "initiative_modifier": 2, "hp": 7, "ac": 15}
            ]
        }

        from agents import _execute_start_combat

        result_str, combat_state = _execute_start_combat(tool_args, state)

        assert combat_state is not None
        assert combat_state.active is True
        assert combat_state.round_number == 1

    def test_narrative_mode_returns_none(self) -> None:
        """Narrative mode returns None for combat_state (no-op)."""
        state = _make_game_state(combat_mode="Narrative")
        tool_args = {"participants": [{"name": "Goblin 1"}]}

        from agents import _execute_start_combat

        result_str, combat_state = _execute_start_combat(tool_args, state)

        assert combat_state is None
        assert "Narrative mode" in result_str

    @patch("agents.roll_initiative")
    def test_participants_parsed_into_npc_profiles(self, mock_init: MagicMock) -> None:
        """Participants correctly parsed into NpcProfile objects."""
        mock_init.return_value = ({"dm:goblin_1": 14}, ["dm", "dm:goblin_1"])
        state = _make_game_state(
            combat_mode="Tactical",
            turn_queue=["dm"],  # no PCs for simplicity
        )
        tool_args = {
            "participants": [
                {
                    "name": "Goblin 1",
                    "initiative_modifier": 2,
                    "hp": 7,
                    "ac": 15,
                    "personality": "Cowardly",
                    "tactics": "Uses shortbow",
                    "secret": "Hidden treasure",
                }
            ]
        }

        from agents import _execute_start_combat

        _, combat_state = _execute_start_combat(tool_args, state)

        assert combat_state is not None
        assert "goblin_1" in combat_state.npc_profiles
        npc = combat_state.npc_profiles["goblin_1"]
        assert npc.name == "Goblin 1"
        assert npc.initiative_modifier == 2
        assert npc.hp_max == 7
        assert npc.hp_current == 7
        assert npc.ac == 15
        assert npc.personality == "Cowardly"
        assert npc.tactics == "Uses shortbow"
        assert npc.secret == "Hidden treasure"

    @patch("agents.roll_initiative")
    def test_hp_maps_to_both_max_and_current(self, mock_init: MagicMock) -> None:
        """NPC hp from participants maps to both hp_max and hp_current."""
        mock_init.return_value = ({"dm:wolf": 10}, ["dm", "dm:wolf"])
        state = _make_game_state(combat_mode="Tactical", turn_queue=["dm"])
        tool_args = {"participants": [{"name": "Wolf", "hp": 11}]}

        from agents import _execute_start_combat

        _, combat_state = _execute_start_combat(tool_args, state)

        assert combat_state is not None
        wolf = combat_state.npc_profiles["wolf"]
        assert wolf.hp_max == 11
        assert wolf.hp_current == 11

    @patch("agents.roll_initiative")
    def test_initiative_rolls_populated(self, mock_init: MagicMock) -> None:
        """initiative_rolls populated in returned combat_state."""
        expected_rolls = {"shadowmere": 18, "thorin": 12, "dm:goblin_1": 14}
        mock_init.return_value = (
            expected_rolls,
            ["dm", "shadowmere", "dm:goblin_1", "thorin"],
        )
        state = _make_game_state(combat_mode="Tactical")
        tool_args = {"participants": [{"name": "Goblin 1", "initiative_modifier": 2}]}

        from agents import _execute_start_combat

        _, combat_state = _execute_start_combat(tool_args, state)

        assert combat_state is not None
        assert combat_state.initiative_rolls == expected_rolls

    @patch("agents.roll_initiative")
    def test_initiative_order_populated(self, mock_init: MagicMock) -> None:
        """initiative_order populated in returned combat_state."""
        expected_order = ["dm", "shadowmere", "dm:goblin_1", "thorin"]
        mock_init.return_value = (
            {"shadowmere": 18, "thorin": 12, "dm:goblin_1": 14},
            expected_order,
        )
        state = _make_game_state(combat_mode="Tactical")
        tool_args = {"participants": [{"name": "Goblin 1", "initiative_modifier": 2}]}

        from agents import _execute_start_combat

        _, combat_state = _execute_start_combat(tool_args, state)

        assert combat_state is not None
        assert combat_state.initiative_order == expected_order

    @patch("agents.roll_initiative")
    def test_original_turn_queue_saved(self, mock_init: MagicMock) -> None:
        """original_turn_queue preserves pre-combat turn order."""
        mock_init.return_value = ({}, ["dm"])
        original_queue = ["dm", "shadowmere", "thorin"]
        state = _make_game_state(combat_mode="Tactical", turn_queue=original_queue)
        tool_args = {"participants": []}

        from agents import _execute_start_combat

        _, combat_state = _execute_start_combat(tool_args, state)

        assert combat_state is not None
        assert combat_state.original_turn_queue == original_queue

    @patch("agents.roll_initiative")
    def test_tool_result_string_contains_initiative_summary(
        self, mock_init: MagicMock
    ) -> None:
        """Tool result string includes initiative order summary."""
        mock_init.return_value = (
            {"shadowmere": 18, "dm:goblin_1": 14},
            ["dm", "shadowmere", "dm:goblin_1"],
        )
        state = _make_game_state(combat_mode="Tactical")
        tool_args = {"participants": [{"name": "Goblin 1", "initiative_modifier": 2}]}

        from agents import _execute_start_combat

        result_str, _ = _execute_start_combat(tool_args, state)

        assert (
            "Initiative order:" in result_str
            or "initiative order:" in result_str.lower()
        )
        assert "Shadowmere" in result_str
        assert "Goblin 1" in result_str
        assert "18" in result_str
        assert "14" in result_str
        assert "Round 1" in result_str


# =============================================================================
# TestExecuteEndCombat
# =============================================================================


class TestExecuteEndCombat:
    """Tests for _execute_end_combat() helper."""

    def test_active_combat_returns_reset_state(self) -> None:
        """Active combat returns reset CombatState (active=False)."""
        active_cs = CombatState(
            active=True,
            round_number=3,
            initiative_order=["dm", "fighter", "dm:goblin_1"],
            initiative_rolls={"fighter": 18, "dm:goblin_1": 12},
            original_turn_queue=["dm", "fighter"],
            npc_profiles={"goblin_1": NpcProfile(name="Goblin 1")},
        )
        state = _make_game_state(combat_state=active_cs)

        from agents import _execute_end_combat

        result_str, reset_cs = _execute_end_combat(state)

        assert reset_cs.active is False
        assert reset_cs.round_number == 0
        assert reset_cs.initiative_order == []
        assert reset_cs.initiative_rolls == {}
        assert reset_cs.original_turn_queue == []
        assert reset_cs.npc_profiles == {}
        assert "ended" in result_str.lower() or "Combat ended" in result_str

    def test_no_active_combat_returns_noop(self) -> None:
        """No active combat returns no-op message."""
        state = _make_game_state(combat_state=CombatState())

        from agents import _execute_end_combat

        result_str, reset_cs = _execute_end_combat(state)

        assert (
            "No combat" in result_str
            or "not active" in result_str.lower()
            or "No combat is currently active" in result_str
        )
        assert reset_cs.active is False

    def test_returned_combat_state_has_empty_collections(self) -> None:
        """Reset combat state has all empty default collections."""
        active_cs = CombatState(active=True, round_number=1)
        state = _make_game_state(combat_state=active_cs)

        from agents import _execute_end_combat

        _, reset_cs = _execute_end_combat(state)

        assert reset_cs == CombatState()


# =============================================================================
# TestDmTurnCombatToolBinding
# =============================================================================


class TestDmTurnCombatToolBinding:
    """Tests for combat tool binding on DM agent."""

    @patch("agents.get_llm")
    def test_dm_start_combat_in_bound_tools(self, mock_get_llm: MagicMock) -> None:
        """dm_start_combat is in the DM agent's bound tools."""
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_get_llm.return_value = mock_model

        from agents import create_dm_agent

        dm_config = DMConfig(
            name="DM",
            provider="gemini",
            model="gemini-1.5-flash",
            token_limit=8000,
            color="#D4A574",
        )
        create_dm_agent(dm_config)

        # Check that bind_tools was called and includes dm_start_combat
        call_args = mock_model.bind_tools.call_args
        tools_list = call_args[0][0]
        tool_names = [t.name for t in tools_list]
        assert "dm_start_combat" in tool_names

    @patch("agents.get_llm")
    def test_dm_end_combat_in_bound_tools(self, mock_get_llm: MagicMock) -> None:
        """dm_end_combat is in the DM agent's bound tools."""
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_get_llm.return_value = mock_model

        from agents import create_dm_agent

        dm_config = DMConfig(
            name="DM",
            provider="gemini",
            model="gemini-1.5-flash",
            token_limit=8000,
            color="#D4A574",
        )
        create_dm_agent(dm_config)

        call_args = mock_model.bind_tools.call_args
        tools_list = call_args[0][0]
        tool_names = [t.name for t in tools_list]
        assert "dm_end_combat" in tool_names


# =============================================================================
# TestInitiativeEdgeCases
# =============================================================================


class TestInitiativeEdgeCases:
    """Edge case tests for initiative rolling."""

    @patch("tools.roll_dice")
    def test_single_pc_vs_single_npc(self, mock_roll: MagicMock) -> None:
        """Minimal combat: one PC vs one NPC."""
        mock_roll.side_effect = [_make_dice_result(15), _make_dice_result(10)]
        sheets = {"fighter": _make_character_sheet(initiative=2)}
        npcs = {"goblin_1": NpcProfile(name="Goblin 1", initiative_modifier=1)}

        rolls, order = roll_initiative(["fighter"], sheets, npcs)

        assert rolls["fighter"] == 17  # 15 + 2
        assert rolls["dm:goblin_1"] == 11  # 10 + 1
        assert order == ["dm", "fighter", "dm:goblin_1"]

    @patch("tools.roll_dice")
    def test_large_party(self, mock_roll: MagicMock) -> None:
        """Large party with 6+ combatants sorts correctly."""
        # 4 PCs + 3 NPCs = 7 combatants
        mock_roll.side_effect = [
            _make_dice_result(10),  # pc1
            _make_dice_result(15),  # pc2
            _make_dice_result(8),  # pc3
            _make_dice_result(20),  # pc4
            _make_dice_result(12),  # npc1
            _make_dice_result(5),  # npc2
            _make_dice_result(18),  # npc3
        ]
        sheets = {
            "pc1": _make_character_sheet(initiative=0),
            "pc2": _make_character_sheet(initiative=2),
            "pc3": _make_character_sheet(initiative=1),
            "pc4": _make_character_sheet(initiative=3),
        }
        npcs = {
            "npc_a": NpcProfile(name="NPC A", initiative_modifier=1),
            "npc_b": NpcProfile(name="NPC B", initiative_modifier=0),
            "npc_c": NpcProfile(name="NPC C", initiative_modifier=2),
        }

        rolls, order = roll_initiative(["pc1", "pc2", "pc3", "pc4"], sheets, npcs)

        # Totals: pc1=10, pc2=17, pc3=9, pc4=23, npc_a=13, npc_b=5, npc_c=20
        assert rolls["pc4"] == 23
        assert rolls["dm:npc_c"] == 20
        assert rolls["pc2"] == 17
        assert rolls["dm:npc_a"] == 13
        assert rolls["pc1"] == 10
        assert rolls["pc3"] == 9
        assert rolls["dm:npc_b"] == 5

        assert order[0] == "dm"  # bookend
        assert order[1] == "pc4"  # 23
        assert order[2] == "dm:npc_c"  # 20
        assert order[3] == "pc2"  # 17
        assert order[4] == "dm:npc_a"  # 13
        assert order[5] == "pc1"  # 10
        assert order[6] == "pc3"  # 9
        assert order[7] == "dm:npc_b"  # 5

    @patch("tools.roll_dice")
    def test_npc_with_negative_modifier(self, mock_roll: MagicMock) -> None:
        """NPC with negative initiative modifier works correctly."""
        mock_roll.side_effect = [_make_dice_result(10)]
        npcs = {"zombie": NpcProfile(name="Zombie", initiative_modifier=-2)}

        rolls, order = roll_initiative([], {}, npcs)

        assert rolls["dm:zombie"] == 8  # 10 + (-2)
        assert order == ["dm", "dm:zombie"]

    @patch("tools.roll_dice")
    def test_all_same_total_alphabetical_tiebreak(self, mock_roll: MagicMock) -> None:
        """All combatants with same total and modifier sorted alphabetically."""
        # All roll 10, all modifier 0 -> total = 10 for everyone
        mock_roll.side_effect = [
            _make_dice_result(10),
            _make_dice_result(10),
            _make_dice_result(10),
        ]
        sheets = {
            "charlie": _make_character_sheet(initiative=0),
            "alpha": _make_character_sheet(initiative=0),
            "bravo": _make_character_sheet(initiative=0),
        }

        _, order = roll_initiative(["charlie", "alpha", "bravo"], sheets, {})
        # All same total and modifier, so alphabetical
        assert order == ["dm", "alpha", "bravo", "charlie"]

    @patch("tools.roll_dice")
    def test_npc_and_pc_tie_alphabetical(self, mock_roll: MagicMock) -> None:
        """NPC and PC with same total and modifier use name ordering."""
        # Both roll 10, both modifier 0
        mock_roll.side_effect = [_make_dice_result(10), _make_dice_result(10)]
        sheets = {"zephyr": _make_character_sheet(initiative=0)}
        npcs = {"aardvark": NpcProfile(name="Aardvark", initiative_modifier=0)}

        _, order = roll_initiative(["zephyr"], sheets, npcs)
        # "dm:aardvark" < "zephyr" alphabetically
        assert order == ["dm", "dm:aardvark", "zephyr"]

    @patch("agents.roll_initiative")
    def test_start_combat_empty_participants(self, mock_init: MagicMock) -> None:
        """Start combat with empty participants list still works."""
        mock_init.return_value = (
            {"shadowmere": 15, "thorin": 10},
            ["dm", "shadowmere", "thorin"],
        )
        state = _make_game_state(combat_mode="Tactical")
        tool_args = {"participants": []}

        from agents import _execute_start_combat

        result_str, combat_state = _execute_start_combat(tool_args, state)

        assert combat_state is not None
        assert combat_state.active is True
        assert combat_state.npc_profiles == {}

    @patch("agents.roll_initiative")
    def test_start_combat_with_character_sheets(self, mock_init: MagicMock) -> None:
        """Start combat uses character sheets for PC modifiers."""
        mock_init.return_value = (
            {"shadowmere": 20},
            ["dm", "shadowmere"],
        )
        sheets = {
            "shadowmere": _make_character_sheet(initiative=5, name="Shadowmere"),
        }
        state = _make_game_state(
            combat_mode="Tactical",
            turn_queue=["dm", "shadowmere"],
            character_sheets=sheets,
        )
        tool_args = {"participants": []}

        from agents import _execute_start_combat

        _execute_start_combat(tool_args, state)

        # Verify roll_initiative was called with the correct character_sheets
        call_args = mock_init.call_args
        assert "shadowmere" in call_args[0][1]  # character_sheets dict
