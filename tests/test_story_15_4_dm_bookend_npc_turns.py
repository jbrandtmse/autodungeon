"""Tests for Story 15.4: DM Bookend & NPC Turns.

Tests for combat turn type detection, bookend/NPC prompt building,
dm_turn() integration with combat prompts, current_turn dynamic
return value, and edge cases for NPC turns.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agents import (
    DM_COMBAT_BOOKEND_PROMPT_TEMPLATE,
    DM_NPC_TURN_PROMPT_TEMPLATE,
    _build_combat_bookend_prompt,
    _build_combatant_summary,
    _build_npc_turn_prompt,
    _get_combat_turn_type,
    dm_turn,
)
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

# =============================================================================
# Fixtures
# =============================================================================


def _make_npc_profiles() -> dict[str, NpcProfile]:
    """Create standard NPC profiles for testing."""
    return {
        "goblin_1": NpcProfile(
            name="Goblin 1",
            initiative_modifier=2,
            hp_max=7,
            hp_current=7,
            ac=15,
            personality="Cowardly and opportunistic",
            tactics="Attacks weakest target, flees when outnumbered",
        ),
        "goblin_2": NpcProfile(
            name="Goblin 2",
            initiative_modifier=2,
            hp_max=7,
            hp_current=5,
            ac=15,
            personality="Reckless and aggressive",
            tactics="Charges the nearest enemy",
            conditions=["poisoned"],
        ),
    }


def _make_combat_state(
    active: bool = True,
    round_number: int = 1,
    npc_profiles: dict[str, NpcProfile] | None = None,
    initiative_order: list[str] | None = None,
    initiative_rolls: dict[str, int] | None = None,
) -> CombatState:
    """Build a CombatState for testing."""
    if npc_profiles is None:
        npc_profiles = _make_npc_profiles()
    if initiative_order is None:
        initiative_order = [
            "dm",
            "dm:goblin_1",
            "shadowmere",
            "dm:goblin_2",
            "thorin",
        ]
    if initiative_rolls is None:
        initiative_rolls = {
            "dm:goblin_1": 18,
            "shadowmere": 15,
            "dm:goblin_2": 12,
            "thorin": 8,
        }
    return CombatState(
        active=active,
        round_number=round_number,
        initiative_order=initiative_order,
        initiative_rolls=initiative_rolls,
        original_turn_queue=["dm", "shadowmere", "thorin"],
        npc_profiles=npc_profiles,
    )


def _make_character_sheet(
    name: str = "Shadowmere",
    hp_current: int = 30,
    hp_max: int = 30,
) -> CharacterSheet:
    """Create a minimal CharacterSheet for testing."""
    return CharacterSheet(
        name=name,
        race="Half-Elf",
        character_class="Rogue",
        level=3,
        strength=10,
        dexterity=16,
        constitution=12,
        intelligence=14,
        wisdom=10,
        charisma=14,
        armor_class=14,
        hit_points_max=hp_max,
        hit_points_current=hp_current,
        hit_dice="3d8",
        hit_dice_remaining=3,
    )


def _make_game_state(
    current_turn: str = "dm",
    combat_state: CombatState | None = None,
    character_sheets: dict[str, CharacterSheet] | None = None,
) -> GameState:
    """Build a minimal GameState for story 15.4 tests."""
    if combat_state is None:
        combat_state = CombatState()
    if character_sheets is None:
        character_sheets = {}

    turn_queue = ["dm", "shadowmere", "thorin"]
    characters: dict[str, CharacterConfig] = {}
    agent_memories: dict[str, AgentMemory] = {"dm": AgentMemory(token_limit=8000)}

    for name in turn_queue:
        if name != "dm":
            characters[name] = CharacterConfig(
                name=name.title(),
                character_class="Fighter",
                personality="Brave",
                color="#C9A45C",
                provider="gemini",
                model="gemini-1.5-flash",
                token_limit=4000,
            )
            agent_memories[name] = AgentMemory(token_limit=4000)

    return GameState(
        ground_truth_log=["[DM]: The adventure begins."],
        turn_queue=turn_queue,
        current_turn=current_turn,
        agent_memories=agent_memories,
        game_config=GameConfig(
            combat_mode="Tactical",  # type: ignore[arg-type]
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
        characters=characters,
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


def _mock_dm_response(text: str = "The goblins snarl.") -> MagicMock:
    """Create a mock LLM response with the given text content."""
    mock_response = MagicMock()
    mock_response.content = text
    mock_response.tool_calls = None
    return mock_response


# =============================================================================
# TestGetCombatTurnType
# =============================================================================


class TestGetCombatTurnType:
    """Tests for _get_combat_turn_type() helper."""

    def test_non_combat_when_active_false(self) -> None:
        state = _make_game_state(
            combat_state=CombatState(active=False),
        )
        assert _get_combat_turn_type(state) == "non_combat"

    def test_non_combat_when_combat_state_missing(self) -> None:
        state = _make_game_state()
        # Default CombatState has active=False
        assert _get_combat_turn_type(state) == "non_combat"

    def test_non_combat_when_combat_state_is_plain_dict(self) -> None:
        state = _make_game_state()
        state["combat_state"] = {}  # type: ignore[typeddict-item]
        assert _get_combat_turn_type(state) == "non_combat"

    def test_bookend_when_active_and_current_turn_dm(self) -> None:
        state = _make_game_state(
            current_turn="dm",
            combat_state=_make_combat_state(active=True),
        )
        assert _get_combat_turn_type(state) == "bookend"

    def test_npc_turn_when_active_and_current_turn_dm_goblin(self) -> None:
        state = _make_game_state(
            current_turn="dm:goblin_1",
            combat_state=_make_combat_state(active=True),
        )
        assert _get_combat_turn_type(state) == "npc_turn"

    def test_npc_turn_for_various_npc_names(self) -> None:
        for npc_name in ["dm:wolf", "dm:klarg", "dm:bug_bear_chief"]:
            state = _make_game_state(
                current_turn=npc_name,
                combat_state=_make_combat_state(active=True),
            )
            assert _get_combat_turn_type(state) == "npc_turn", f"Failed for {npc_name}"

    def test_bookend_for_unexpected_pc_name_during_combat(self) -> None:
        """Defensive: PC name during combat falls through to bookend."""
        state = _make_game_state(
            current_turn="shadowmere",
            combat_state=_make_combat_state(active=True),
        )
        assert _get_combat_turn_type(state) == "bookend"


# =============================================================================
# TestBuildCombatantSummary
# =============================================================================


class TestBuildCombatantSummary:
    """Tests for _build_combatant_summary() helper."""

    def test_includes_npc_entries(self) -> None:
        state = _make_game_state(
            combat_state=_make_combat_state(),
        )
        result = _build_combatant_summary(state)
        assert "Goblin 1" in result
        assert "Goblin 2" in result

    def test_includes_npc_hp(self) -> None:
        state = _make_game_state(
            combat_state=_make_combat_state(),
        )
        result = _build_combatant_summary(state)
        assert "HP 7/7" in result
        assert "HP 5/7" in result

    def test_includes_npc_conditions(self) -> None:
        state = _make_game_state(
            combat_state=_make_combat_state(),
        )
        result = _build_combatant_summary(state)
        assert "poisoned" in result

    def test_includes_initiative_rolls(self) -> None:
        state = _make_game_state(
            combat_state=_make_combat_state(),
        )
        result = _build_combatant_summary(state)
        assert "Init 18" in result
        assert "Init 12" in result

    def test_skips_dm_bookend_entry(self) -> None:
        state = _make_game_state(
            combat_state=_make_combat_state(),
        )
        result = _build_combatant_summary(state)
        lines = result.strip().split("\n")
        # Should not have a line for just "dm"
        for line in lines:
            assert not line.startswith("- dm (")

    def test_includes_pc_from_character_sheets(self) -> None:
        sheets = {
            "shadowmere": _make_character_sheet("Shadowmere", 28, 30),
        }
        state = _make_game_state(
            combat_state=_make_combat_state(),
            character_sheets=sheets,
        )
        result = _build_combatant_summary(state)
        assert "Shadowmere" in result
        assert "HP 28/30" in result

    def test_pc_without_sheet_shows_name_only(self) -> None:
        state = _make_game_state(
            combat_state=_make_combat_state(),
        )
        result = _build_combatant_summary(state)
        # thorin has no sheet, should still appear
        assert "thorin" in result

    def test_empty_initiative_order(self) -> None:
        combat = _make_combat_state()
        combat = combat.model_copy(update={"initiative_order": []})
        state = _make_game_state(combat_state=combat)
        result = _build_combatant_summary(state)
        assert result == "No combatants listed."

    def test_unknown_npc_in_initiative(self) -> None:
        combat = _make_combat_state()
        combat = combat.model_copy(
            update={"initiative_order": ["dm", "dm:unknown_monster"]}
        )
        state = _make_game_state(combat_state=combat)
        result = _build_combatant_summary(state)
        assert "unknown_monster" in result
        assert "Unknown NPC" in result

    def test_no_combat_state_returns_no_combatants(self) -> None:
        """Default CombatState with empty initiative_order returns fallback text."""
        state = _make_game_state()
        result = _build_combatant_summary(state)
        assert result == "No combatants listed."


# =============================================================================
# TestBuildCombatBookendPrompt
# =============================================================================


class TestBuildCombatBookendPrompt:
    """Tests for _build_combat_bookend_prompt() helper."""

    def test_includes_round_number(self) -> None:
        state = _make_game_state(
            combat_state=_make_combat_state(round_number=3),
        )
        result = _build_combat_bookend_prompt(state)
        assert "Round 3" in result

    def test_includes_combatant_summary(self) -> None:
        state = _make_game_state(
            combat_state=_make_combat_state(),
        )
        result = _build_combat_bookend_prompt(state)
        assert "Goblin 1" in result
        assert "Goblin 2" in result

    def test_includes_do_not_act_instruction(self) -> None:
        state = _make_game_state(
            combat_state=_make_combat_state(),
        )
        result = _build_combat_bookend_prompt(state)
        assert "Do NOT act for any specific NPC" in result

    def test_includes_pc_hp_from_sheets(self) -> None:
        sheets = {"shadowmere": _make_character_sheet("Shadowmere", 25, 30)}
        state = _make_game_state(
            combat_state=_make_combat_state(),
            character_sheets=sheets,
        )
        result = _build_combat_bookend_prompt(state)
        assert "HP 25/30" in result

    def test_uses_template(self) -> None:
        state = _make_game_state(
            combat_state=_make_combat_state(round_number=1),
        )
        result = _build_combat_bookend_prompt(state)
        # Should contain key phrases from the template
        assert "Combat Round 1" in result
        assert "narrating the start of combat round 1" in result


# =============================================================================
# TestBuildNpcTurnPrompt
# =============================================================================


class TestBuildNpcTurnPrompt:
    """Tests for _build_npc_turn_prompt() helper."""

    def test_includes_npc_name(self) -> None:
        state = _make_game_state(combat_state=_make_combat_state())
        result = _build_npc_turn_prompt(state, "goblin_1")
        assert "Goblin 1" in result

    def test_includes_hp_and_ac(self) -> None:
        state = _make_game_state(combat_state=_make_combat_state())
        result = _build_npc_turn_prompt(state, "goblin_1")
        assert "HP: 7/7" in result
        assert "AC: 15" in result

    def test_includes_initiative_roll(self) -> None:
        state = _make_game_state(combat_state=_make_combat_state())
        result = _build_npc_turn_prompt(state, "goblin_1")
        assert "Initiative: 18" in result

    def test_includes_personality_and_tactics(self) -> None:
        state = _make_game_state(combat_state=_make_combat_state())
        result = _build_npc_turn_prompt(state, "goblin_1")
        assert "Cowardly and opportunistic" in result
        assert "Attacks weakest target" in result

    def test_includes_conditions_when_present(self) -> None:
        state = _make_game_state(combat_state=_make_combat_state())
        result = _build_npc_turn_prompt(state, "goblin_2")
        assert "poisoned" in result

    def test_no_conditions_line_when_empty(self) -> None:
        state = _make_game_state(combat_state=_make_combat_state())
        result = _build_npc_turn_prompt(state, "goblin_1")
        # goblin_1 has no conditions, so no "Conditions:" line
        assert "Conditions:" not in result

    def test_fallback_for_missing_npc(self) -> None:
        state = _make_game_state(combat_state=_make_combat_state())
        result = _build_npc_turn_prompt(state, "nonexistent_npc")
        assert "nonexistent_npc" in result
        assert "Narrate their action" in result

    def test_logs_warning_for_missing_npc(self) -> None:
        """Verify warning is logged and fallback returned for missing NPC."""
        import logging as _logging

        state = _make_game_state(combat_state=_make_combat_state())
        logger = _logging.getLogger("autodungeon")

        import io

        handler = _logging.StreamHandler(io.StringIO())
        handler.setLevel(_logging.WARNING)
        logger.addHandler(handler)
        try:
            result = _build_npc_turn_prompt(state, "nonexistent_npc")
            assert "nonexistent_npc" in result
        finally:
            logger.removeHandler(handler)

    def test_empty_personality_and_tactics(self) -> None:
        profiles = {
            "bland_npc": NpcProfile(
                name="Bland NPC",
                hp_max=5,
                hp_current=5,
                ac=10,
                personality="",
                tactics="",
            )
        }
        combat = _make_combat_state(npc_profiles=profiles)
        state = _make_game_state(combat_state=combat)
        result = _build_npc_turn_prompt(state, "bland_npc")
        assert "Bland NPC" in result
        assert "None specified" in result

    def test_uses_template(self) -> None:
        state = _make_game_state(combat_state=_make_combat_state())
        result = _build_npc_turn_prompt(state, "goblin_1")
        assert "NPC Turn: Goblin 1" in result
        assert "acting as **Goblin 1**" in result


# =============================================================================
# TestDmTurnBookend
# =============================================================================


class TestDmTurnBookend:
    """Tests for dm_turn() with bookend (round-start) turn type."""

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_system_prompt_contains_bookend_addendum(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Round begins!")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm",
            combat_state=_make_combat_state(round_number=2),
        )
        dm_turn(state)

        # Check system prompt includes bookend template content
        call_args = mock_agent.invoke.call_args[0][0]
        system_msg = call_args[0]
        assert "Combat Round 2" in system_msg.content

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_human_message_mentions_round(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Round 2 begins.")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm",
            combat_state=_make_combat_state(round_number=2),
        )
        dm_turn(state)

        call_args = mock_agent.invoke.call_args[0][0]
        # Find the last HumanMessage (the turn-specific one)
        human_msgs = [m for m in call_args if hasattr(m, "content") and "round" in m.content.lower()]
        assert len(human_msgs) >= 1
        assert "round 2" in human_msgs[-1].content.lower()

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_current_turn_is_dm_in_return(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("The battle rages.")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm",
            combat_state=_make_combat_state(),
        )
        result = dm_turn(state)
        assert result["current_turn"] == "dm"

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_ground_truth_log_uses_dm_prefix(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("The goblins ready.")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm",
            combat_state=_make_combat_state(),
        )
        result = dm_turn(state)
        last_entry = result["ground_truth_log"][-1]
        assert last_entry.startswith("[DM]:")

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_dm_memory_uses_dm_prefix(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Round narration.")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm",
            combat_state=_make_combat_state(),
        )
        result = dm_turn(state)
        dm_buffer = result["agent_memories"]["dm"].short_term_buffer
        assert dm_buffer[-1].startswith("[DM]:")


# =============================================================================
# TestDmTurnNpcTurn
# =============================================================================


class TestDmTurnNpcTurn:
    """Tests for dm_turn() with NPC turn type."""

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_system_prompt_contains_npc_addendum(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Goblin attacks!")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm:goblin_1",
            combat_state=_make_combat_state(),
        )
        dm_turn(state)

        call_args = mock_agent.invoke.call_args[0][0]
        system_msg = call_args[0]
        assert "NPC Turn: Goblin 1" in system_msg.content

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_npc_prompt_includes_profile_data(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Goblin slashes!")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm:goblin_1",
            combat_state=_make_combat_state(),
        )
        dm_turn(state)

        call_args = mock_agent.invoke.call_args[0][0]
        system_msg = call_args[0]
        assert "HP: 7/7" in system_msg.content
        assert "Cowardly and opportunistic" in system_msg.content

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_human_message_mentions_npc_name(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Goblin swings!")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm:goblin_1",
            combat_state=_make_combat_state(),
        )
        dm_turn(state)

        call_args = mock_agent.invoke.call_args[0][0]
        human_msgs = [
            m
            for m in call_args
            if hasattr(m, "content") and "Goblin 1" in m.content
        ]
        assert len(human_msgs) >= 1

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_current_turn_preserves_npc_key(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Goblin attacks!")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm:goblin_1",
            combat_state=_make_combat_state(),
        )
        result = dm_turn(state)
        assert result["current_turn"] == "dm:goblin_1"

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_ground_truth_log_uses_dm_prefix_for_npc(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Goblin 1 slashes.")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm:goblin_1",
            combat_state=_make_combat_state(),
        )
        result = dm_turn(state)
        last_entry = result["ground_truth_log"][-1]
        assert last_entry.startswith("[DM]:")

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_npc_turn_with_different_npc(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Goblin 2 charges.")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm:goblin_2",
            combat_state=_make_combat_state(),
        )
        dm_turn(state)

        call_args = mock_agent.invoke.call_args[0][0]
        system_msg = call_args[0]
        assert "NPC Turn: Goblin 2" in system_msg.content
        assert "Reckless and aggressive" in system_msg.content

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_current_turn_preserves_goblin_2(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Goblin 2 charges.")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm:goblin_2",
            combat_state=_make_combat_state(),
        )
        result = dm_turn(state)
        assert result["current_turn"] == "dm:goblin_2"


# =============================================================================
# TestDmTurnNonCombat
# =============================================================================


class TestDmTurnNonCombat:
    """Tests for dm_turn() with no active combat (standard behavior)."""

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_no_combat_addendum_in_system_prompt(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("The path winds on.")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm",
            combat_state=CombatState(active=False),
        )
        dm_turn(state)

        call_args = mock_agent.invoke.call_args[0][0]
        system_msg = call_args[0]
        assert "Combat Round" not in system_msg.content
        assert "NPC Turn:" not in system_msg.content

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_human_message_is_continue(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("The path winds on.")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm",
            combat_state=CombatState(active=False),
        )
        dm_turn(state)

        call_args = mock_agent.invoke.call_args[0][0]
        # Last message should be "Continue the adventure."
        last_human = [
            m for m in call_args if hasattr(m, "content") and "Continue" in m.content
        ]
        assert len(last_human) >= 1
        assert "Continue the adventure." in last_human[-1].content

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_current_turn_is_dm(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Exploring...")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm",
            combat_state=CombatState(active=False),
        )
        result = dm_turn(state)
        assert result["current_turn"] == "dm"


# =============================================================================
# TestDmTurnCurrentTurnReturn
# =============================================================================


class TestDmTurnCurrentTurnReturn:
    """Tests for current_turn return value in various scenarios."""

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_dm_when_no_combat(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Peaceful.")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm",
            combat_state=CombatState(active=False),
        )
        result = dm_turn(state)
        assert result["current_turn"] == "dm"

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_dm_when_bookend(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Round starts.")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm",
            combat_state=_make_combat_state(),
        )
        result = dm_turn(state)
        assert result["current_turn"] == "dm"

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_dm_npc_name_when_npc_turn(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("Goblin strikes.")
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm:goblin_1",
            combat_state=_make_combat_state(),
        )
        result = dm_turn(state)
        assert result["current_turn"] == "dm:goblin_1"

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_dm_when_end_combat_deactivates(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        """When dm_end_combat is called, combat deactivates; return 'dm'."""
        mock_response = MagicMock()
        mock_response.content = "The battle ends."
        # First call returns tool call, second returns final response
        mock_tool_response = MagicMock()
        mock_tool_response.content = ""
        mock_tool_response.tool_calls = [
            {"name": "dm_end_combat", "args": {}, "id": "call_1"}
        ]
        mock_final = MagicMock()
        mock_final.content = "The battle ends."
        mock_final.tool_calls = None

        mock_agent = MagicMock()
        mock_agent.invoke.side_effect = [mock_tool_response, mock_final]
        mock_create.return_value = mock_agent

        state = _make_game_state(
            current_turn="dm",
            combat_state=_make_combat_state(),
        )
        result = dm_turn(state)
        # After end_combat, combat is no longer active, so current_turn should be "dm"
        assert result["current_turn"] == "dm"
        assert result["combat_state"].active is False


# =============================================================================
# TestNpcTurnEdgeCases
# =============================================================================


class TestNpcTurnEdgeCases:
    """Edge case tests for NPC turn handling."""

    def test_npc_key_not_in_profiles_fallback(self) -> None:
        state = _make_game_state(combat_state=_make_combat_state())
        result = _build_npc_turn_prompt(state, "nonexistent")
        assert "nonexistent" in result
        assert "Narrate their action" in result

    def test_npc_with_empty_personality(self) -> None:
        profiles = {
            "blank": NpcProfile(
                name="Blank NPC",
                hp_max=10,
                hp_current=10,
                ac=12,
                personality="",
                tactics="",
            )
        }
        combat = _make_combat_state(npc_profiles=profiles)
        state = _make_game_state(combat_state=combat)
        result = _build_npc_turn_prompt(state, "blank")
        assert "None specified" in result

    def test_npc_with_multiple_conditions(self) -> None:
        profiles = {
            "sick_goblin": NpcProfile(
                name="Sick Goblin",
                hp_max=7,
                hp_current=3,
                ac=12,
                personality="Miserable",
                tactics="Tries to flee",
                conditions=["poisoned", "prone", "frightened"],
            )
        }
        combat = _make_combat_state(npc_profiles=profiles)
        state = _make_game_state(combat_state=combat)
        result = _build_npc_turn_prompt(state, "sick_goblin")
        assert "poisoned" in result
        assert "prone" in result
        assert "frightened" in result

    def test_npc_at_zero_hp_still_gets_prompt(self) -> None:
        profiles = {
            "dying_goblin": NpcProfile(
                name="Dying Goblin",
                hp_max=7,
                hp_current=0,
                ac=12,
                personality="Desperate",
                tactics="Last stand",
            )
        }
        combat = _make_combat_state(npc_profiles=profiles)
        state = _make_game_state(combat_state=combat)
        result = _build_npc_turn_prompt(state, "dying_goblin")
        assert "HP: 0/7" in result
        assert "Dying Goblin" in result

    def test_npc_key_extraction_simple(self) -> None:
        """'dm:wolf' -> 'wolf'."""
        key = "dm:wolf".split(":", 1)[1]
        assert key == "wolf"

    def test_npc_key_extraction_underscore(self) -> None:
        """'dm:goblin_1' -> 'goblin_1'."""
        key = "dm:goblin_1".split(":", 1)[1]
        assert key == "goblin_1"

    @patch("agents.create_dm_agent")
    @patch("agents.extract_narrative_elements", create=True)
    def test_missing_npc_still_runs_dm_turn(
        self, _mock_extract: MagicMock, mock_create: MagicMock
    ) -> None:
        """dm_turn with NPC not in profiles should gracefully fallback."""
        mock_agent = MagicMock()
        mock_agent.invoke.return_value = _mock_dm_response("The creature acts.")
        mock_create.return_value = mock_agent

        combat = _make_combat_state()
        combat = combat.model_copy(
            update={
                "initiative_order": ["dm", "dm:unknown_beast", "shadowmere"],
            }
        )
        state = _make_game_state(
            current_turn="dm:unknown_beast",
            combat_state=combat,
        )
        result = dm_turn(state)
        # Should complete without error
        assert result["current_turn"] == "dm:unknown_beast"
        assert "[DM]:" in result["ground_truth_log"][-1]

    def test_npc_fallback_prompt_logs_warning(self) -> None:
        """Verify warning is logged for missing NPC profile."""
        import logging as _logging

        state = _make_game_state(combat_state=_make_combat_state())
        logger = _logging.getLogger("autodungeon")
        original_level = logger.level
        logger.setLevel(_logging.WARNING)

        import io

        stream = io.StringIO()
        handler = _logging.StreamHandler(stream)
        handler.setLevel(_logging.WARNING)
        logger.addHandler(handler)
        try:
            _build_npc_turn_prompt(state, "nonexistent_npc")
            output = stream.getvalue()
            assert "nonexistent_npc" in output
        finally:
            logger.removeHandler(handler)
            logger.setLevel(original_level)


# =============================================================================
# TestPromptConstants
# =============================================================================


class TestPromptConstants:
    """Tests that prompt template constants exist and have expected placeholders."""

    def test_bookend_template_has_round_number_placeholder(self) -> None:
        assert "{round_number}" in DM_COMBAT_BOOKEND_PROMPT_TEMPLATE

    def test_bookend_template_has_combatant_summary_placeholder(self) -> None:
        assert "{combatant_summary}" in DM_COMBAT_BOOKEND_PROMPT_TEMPLATE

    def test_npc_template_has_npc_name_placeholder(self) -> None:
        assert "{npc_name}" in DM_NPC_TURN_PROMPT_TEMPLATE

    def test_npc_template_has_hp_placeholders(self) -> None:
        assert "{hp_current}" in DM_NPC_TURN_PROMPT_TEMPLATE
        assert "{hp_max}" in DM_NPC_TURN_PROMPT_TEMPLATE

    def test_npc_template_has_ac_placeholder(self) -> None:
        assert "{ac}" in DM_NPC_TURN_PROMPT_TEMPLATE

    def test_npc_template_has_personality_placeholder(self) -> None:
        assert "{personality}" in DM_NPC_TURN_PROMPT_TEMPLATE

    def test_npc_template_has_tactics_placeholder(self) -> None:
        assert "{tactics}" in DM_NPC_TURN_PROMPT_TEMPLATE

    def test_npc_template_has_conditions_line_placeholder(self) -> None:
        assert "{conditions_line}" in DM_NPC_TURN_PROMPT_TEMPLATE

    def test_npc_template_has_initiative_roll_placeholder(self) -> None:
        assert "{initiative_roll}" in DM_NPC_TURN_PROMPT_TEMPLATE
