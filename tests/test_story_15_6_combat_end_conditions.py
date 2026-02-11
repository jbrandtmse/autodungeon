"""Tests for Story 15.6: Combat End Conditions.

Tests for turn queue restoration in _execute_end_combat(), max_combat_rounds
config option, round limit enforcement in context_manager(), routing after
combat ends, and persistence backward compatibility.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

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


def _make_character_sheet(initiative: int = 0, **kwargs: object) -> CharacterSheet:
    """Build a minimal CharacterSheet with the given initiative modifier."""
    defaults: dict[str, object] = {
        "name": "Test",
        "race": "Human",
        "character_class": "Fighter",
        "level": 1,
        "strength": 10,
        "dexterity": 10 + (initiative * 2),
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
    game_config: GameConfig | None = None,
    ground_truth_log: list[str] | None = None,
) -> GameState:
    """Build a minimal GameState for combat end condition testing."""
    if turn_queue is None:
        turn_queue = ["dm", "fighter", "rogue", "wizard"]
    if character_sheets is None:
        character_sheets = {}
    if combat_state is None:
        combat_state = CombatState()
    if game_config is None:
        game_config = GameConfig(
            combat_mode=combat_mode,  # type: ignore[arg-type]
            summarizer_model="gemini-1.5-flash",
            party_size=3,
        )
    if ground_truth_log is None:
        ground_truth_log = ["[DM]: The adventure begins."]

    return GameState(
        ground_truth_log=ground_truth_log,
        turn_queue=turn_queue,
        current_turn="dm",
        agent_memories={
            "dm": AgentMemory(token_limit=8000),
        },
        game_config=game_config,
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
                personality="Brave",
                color="#C9A45C",
                provider="gemini",
                model="gemini-1.5-flash",
                token_limit=4000,
            ),
            "rogue": CharacterConfig(
                name="Shadowmere",
                character_class="Rogue",
                personality="Stealthy",
                color="#8B4513",
                provider="gemini",
                model="gemini-1.5-flash",
                token_limit=4000,
            ),
            "wizard": CharacterConfig(
                name="Gandalf",
                character_class="Wizard",
                personality="Wise",
                color="#4169E1",
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


def _make_active_combat_state(
    round_number: int = 3,
    original_turn_queue: list[str] | None = None,
    npcs: dict[str, NpcProfile] | None = None,
) -> CombatState:
    """Build a realistic active CombatState for testing."""
    if original_turn_queue is None:
        original_turn_queue = ["dm", "fighter", "rogue", "wizard"]
    if npcs is None:
        npcs = {
            "goblin_1": NpcProfile(
                name="Goblin 1", hp_max=7, hp_current=3, ac=13
            ),
            "goblin_2": NpcProfile(
                name="Goblin 2", hp_max=7, hp_current=0, ac=13
            ),
        }
    return CombatState(
        active=True,
        round_number=round_number,
        initiative_order=[
            "fighter",
            "dm:goblin_1",
            "rogue",
            "dm:goblin_2",
            "wizard",
            "dm",
        ],
        initiative_rolls={
            "fighter": 18,
            "dm:goblin_1": 15,
            "rogue": 12,
            "dm:goblin_2": 10,
            "wizard": 8,
        },
        original_turn_queue=original_turn_queue,
        npc_profiles=npcs,
    )


# =============================================================================
# TestMaxCombatRoundsConfig
# =============================================================================


class TestMaxCombatRoundsConfig:
    """Tests for max_combat_rounds field on GameConfig (AC #6, #10)."""

    def test_default_is_50(self) -> None:
        """GameConfig has max_combat_rounds field with default 50."""
        config = GameConfig()
        assert config.max_combat_rounds == 50

    def test_zero_is_valid_unlimited(self) -> None:
        """max_combat_rounds=0 is valid (unlimited)."""
        config = GameConfig(max_combat_rounds=0)
        assert config.max_combat_rounds == 0

    def test_negative_raises_validation_error(self) -> None:
        """max_combat_rounds=-1 raises ValidationError (ge=0)."""
        with pytest.raises(ValidationError):
            GameConfig(max_combat_rounds=-1)

    def test_custom_limit_100(self) -> None:
        """max_combat_rounds=100 is valid (custom limit)."""
        config = GameConfig(max_combat_rounds=100)
        assert config.max_combat_rounds == 100

    def test_no_keyword_uses_default(self) -> None:
        """GameConfig() with no max_combat_rounds keyword uses default 50."""
        config = GameConfig(combat_mode="Tactical")
        assert config.max_combat_rounds == 50

    def test_low_value_1_is_valid(self) -> None:
        """max_combat_rounds=1 is valid (combat ends after first round increment)."""
        config = GameConfig(max_combat_rounds=1)
        assert config.max_combat_rounds == 1


# =============================================================================
# TestExecuteEndCombatTurnQueueRestoration
# =============================================================================


class TestExecuteEndCombatTurnQueueRestoration:
    """Tests for turn queue restoration in _execute_end_combat (AC #1, #2, #13)."""

    def test_returns_three_element_tuple(self) -> None:
        """_execute_end_combat returns (str, CombatState, list | None)."""
        from agents import _execute_end_combat

        combat = _make_active_combat_state()
        state = _make_game_state(combat_state=combat)

        result = _execute_end_combat(state)

        assert len(result) == 3
        assert isinstance(result[0], str)
        assert isinstance(result[1], CombatState)
        assert isinstance(result[2], list) or result[2] is None

    def test_restored_turn_queue_matches_original(self) -> None:
        """Restored turn queue matches original_turn_queue when combat active."""
        from agents import _execute_end_combat

        original_queue = ["dm", "fighter", "rogue", "wizard", "cleric"]
        combat = _make_active_combat_state(original_turn_queue=original_queue)
        state = _make_game_state(combat_state=combat)

        _, _, restored_queue = _execute_end_combat(state)

        assert restored_queue == original_queue

    def test_combat_state_reset_to_defaults(self) -> None:
        """Returned CombatState is reset to defaults (AC #2)."""
        from agents import _execute_end_combat

        combat = _make_active_combat_state()
        state = _make_game_state(combat_state=combat)

        _, reset_cs, _ = _execute_end_combat(state)

        assert reset_cs == CombatState()
        assert reset_cs.active is False
        assert reset_cs.round_number == 0
        assert reset_cs.initiative_order == []
        assert reset_cs.initiative_rolls == {}
        assert reset_cs.original_turn_queue == []
        assert reset_cs.npc_profiles == {}

    def test_restored_queue_is_copy_not_reference(self) -> None:
        """Restored turn queue is a copy, not a reference to the original list."""
        from agents import _execute_end_combat

        original_queue = ["dm", "fighter", "rogue"]
        combat = _make_active_combat_state(original_turn_queue=original_queue)
        state = _make_game_state(combat_state=combat)

        _, _, restored_queue = _execute_end_combat(state)

        assert restored_queue is not combat.original_turn_queue
        assert restored_queue == combat.original_turn_queue

    def test_realistic_five_member_party(self) -> None:
        """Works with realistic 5-member party original_turn_queue."""
        from agents import _execute_end_combat

        original_queue = ["dm", "fighter", "rogue", "wizard", "cleric", "bard"]
        combat = _make_active_combat_state(original_turn_queue=original_queue)
        state = _make_game_state(combat_state=combat)

        result_str, reset_cs, restored_queue = _execute_end_combat(state)

        assert restored_queue == original_queue
        assert "ended" in result_str.lower() or "Combat ended" in result_str
        assert reset_cs.active is False

    def test_result_string_indicates_end(self) -> None:
        """Result string indicates combat ended."""
        from agents import _execute_end_combat

        combat = _make_active_combat_state()
        state = _make_game_state(combat_state=combat)

        result_str, _, _ = _execute_end_combat(state)

        assert "ended" in result_str.lower() or "Combat ended" in result_str


# =============================================================================
# TestExecuteEndCombatEdgeCases
# =============================================================================


class TestExecuteEndCombatEdgeCases:
    """Tests for edge cases in _execute_end_combat (AC #4, #5)."""

    def test_combat_not_active_returns_noop(self) -> None:
        """Combat not active returns None for turn queue and no-op message (AC #5)."""
        from agents import _execute_end_combat

        state = _make_game_state(combat_state=CombatState())

        result_str, reset_cs, restored_queue = _execute_end_combat(state)

        assert "No combat is currently active" in result_str
        assert reset_cs.active is False
        assert restored_queue is None

    def test_empty_original_turn_queue_returns_none_and_logs_warning(self) -> None:
        """Empty original_turn_queue returns None and logs warning (AC #4)."""
        from agents import _execute_end_combat

        combat = CombatState(
            active=True,
            round_number=2,
            initiative_order=["fighter", "dm:goblin_1"],
            original_turn_queue=[],  # empty backup
        )
        state = _make_game_state(combat_state=combat)

        with patch("agents.logger") as mock_logger:
            _, _, restored_queue = _execute_end_combat(state)

            assert restored_queue is None
            mock_logger.warning.assert_called_once()
            assert "original_turn_queue" in mock_logger.warning.call_args[0][0].lower()

    def test_combat_state_missing_from_state(self) -> None:
        """Missing combat_state returns None for turn queue."""
        from agents import _execute_end_combat

        state = _make_game_state()
        # Remove combat_state to simulate old state format
        del state["combat_state"]  # type: ignore[misc]

        result_str, reset_cs, restored_queue = _execute_end_combat(state)

        assert "No combat is currently active" in result_str
        assert restored_queue is None
        assert reset_cs.active is False

    def test_double_end_combat_second_is_noop(self) -> None:
        """Calling _execute_end_combat twice: second is a no-op."""
        from agents import _execute_end_combat

        combat = _make_active_combat_state()
        state = _make_game_state(combat_state=combat)

        # First call ends combat
        _, reset_cs, restored_queue = _execute_end_combat(state)
        assert restored_queue is not None
        assert reset_cs.active is False

        # Update state with reset combat
        state["combat_state"] = reset_cs

        # Second call is a no-op
        result_str2, _, restored_queue2 = _execute_end_combat(state)
        assert "No combat is currently active" in result_str2
        assert restored_queue2 is None


# =============================================================================
# TestDmTurnEndCombatIntegration
# =============================================================================


class TestDmTurnEndCombatIntegration:
    """Tests for dm_turn() end combat integration (AC #3, #14)."""

    @patch("agents.get_llm")
    def test_dm_turn_returns_restored_turn_queue(
        self, mock_get_llm: MagicMock
    ) -> None:
        """dm_turn returns state with restored turn_queue after end combat (AC #3)."""
        # Setup mock LLM to return an end combat tool call
        mock_model = MagicMock()
        mock_bound = MagicMock()
        mock_model.bind_tools.return_value = mock_bound

        # First invocation: tool call to end combat
        tool_call_response = MagicMock()
        tool_call_response.tool_calls = [
            {
                "name": "dm_end_combat",
                "args": {},
                "id": "call_1",
            }
        ]
        tool_call_response.content = ""

        # Second invocation: final narrative
        final_response = MagicMock()
        final_response.tool_calls = []
        final_response.content = "The combat has ended. The goblins flee!"

        mock_bound.invoke = MagicMock(
            side_effect=[tool_call_response, final_response]
        )
        mock_get_llm.return_value = mock_model

        # Build state with active combat
        original_queue = ["dm", "fighter", "rogue", "wizard"]
        combat = _make_active_combat_state(original_turn_queue=original_queue)
        state = _make_game_state(
            combat_state=combat,
            turn_queue=["dm", "fighter", "rogue", "wizard"],
        )

        from agents import dm_turn

        result = dm_turn(state)

        assert result["turn_queue"] == original_queue

    @patch("agents.get_llm")
    def test_dm_turn_returns_reset_combat_state(
        self, mock_get_llm: MagicMock
    ) -> None:
        """dm_turn returns state with reset combat_state after end combat (AC #14)."""
        mock_model = MagicMock()
        mock_bound = MagicMock()
        mock_model.bind_tools.return_value = mock_bound

        tool_call_response = MagicMock()
        tool_call_response.tool_calls = [
            {"name": "dm_end_combat", "args": {}, "id": "call_1"}
        ]
        tool_call_response.content = ""

        final_response = MagicMock()
        final_response.tool_calls = []
        final_response.content = "The battle is over."

        mock_bound.invoke = MagicMock(
            side_effect=[tool_call_response, final_response]
        )
        mock_get_llm.return_value = mock_model

        combat = _make_active_combat_state()
        state = _make_game_state(combat_state=combat)

        from agents import dm_turn

        result = dm_turn(state)

        result_combat = result["combat_state"]
        assert result_combat.active is False
        assert result_combat.round_number == 0
        assert result_combat.initiative_order == []
        assert result_combat.npc_profiles == {}

    @patch("agents.get_llm")
    def test_dm_turn_no_combat_turn_queue_unchanged(
        self, mock_get_llm: MagicMock
    ) -> None:
        """dm_turn turn_queue unchanged when no end combat (no-op)."""
        mock_model = MagicMock()
        mock_bound = MagicMock()
        mock_model.bind_tools.return_value = mock_bound

        # No tool calls - just a normal narrative response
        response = MagicMock()
        response.tool_calls = []
        response.content = "The adventurers continue exploring."

        mock_bound.invoke = MagicMock(return_value=response)
        mock_get_llm.return_value = mock_model

        original_queue = ["dm", "fighter", "rogue", "wizard"]
        state = _make_game_state(turn_queue=original_queue)

        from agents import dm_turn

        result = dm_turn(state)

        assert result["turn_queue"] == original_queue


# =============================================================================
# TestContextManagerMaxRoundEnforcement
# =============================================================================


class TestContextManagerMaxRoundEnforcement:
    """Tests for max round limit enforcement in context_manager (AC #7, #8, #9)."""

    def test_force_ends_combat_when_exceeds_max(self) -> None:
        """Force-ends combat when round_number+1 > max_combat_rounds (AC #7)."""
        from graph import context_manager

        config = GameConfig(max_combat_rounds=5)
        combat = _make_active_combat_state(round_number=5)  # will become 6 > 5
        state = _make_game_state(combat_state=combat, game_config=config)

        result = context_manager(state)

        assert result["combat_state"].active is False
        assert result["combat_state"].round_number == 0

    def test_restores_turn_queue_on_force_end(self) -> None:
        """Restores turn_queue from original_turn_queue on force-end (AC #7)."""
        from graph import context_manager

        original_queue = ["dm", "fighter", "rogue", "wizard"]
        config = GameConfig(max_combat_rounds=3)
        combat = _make_active_combat_state(
            round_number=3, original_turn_queue=original_queue
        )
        state = _make_game_state(
            combat_state=combat,
            game_config=config,
            turn_queue=["dm", "fighter", "rogue", "wizard"],
        )

        result = context_manager(state)

        assert result["turn_queue"] == original_queue

    def test_resets_combat_state_to_defaults_on_force_end(self) -> None:
        """Resets combat_state to defaults on force-end."""
        from graph import context_manager

        config = GameConfig(max_combat_rounds=2)
        combat = _make_active_combat_state(round_number=2)
        state = _make_game_state(combat_state=combat, game_config=config)

        result = context_manager(state)

        assert result["combat_state"] == CombatState()

    def test_appends_system_log_on_force_end(self) -> None:
        """Appends system log entry on force-end (AC #8)."""
        from graph import context_manager

        config = GameConfig(max_combat_rounds=5)
        combat = _make_active_combat_state(round_number=5)
        state = _make_game_state(combat_state=combat, game_config=config)

        result = context_manager(state)

        log = result["ground_truth_log"]
        assert any(
            "[System]:" in entry and "maximum round limit" in entry
            for entry in log
        )

    def test_emits_warning_log_on_force_end(self, caplog: pytest.LogCaptureFixture) -> None:
        """Emits logger warning on force-end (AC #9)."""
        from graph import context_manager

        config = GameConfig(max_combat_rounds=3)
        combat = _make_active_combat_state(round_number=3)
        state = _make_game_state(combat_state=combat, game_config=config)

        with caplog.at_level(logging.WARNING, logger="autodungeon"):
            context_manager(state)

        assert any(
            "force-ended" in record.message.lower() or "exceeded" in record.message.lower()
            for record in caplog.records
        )

    def test_does_not_force_end_within_limit(self) -> None:
        """Does NOT force-end when round_number+1 <= max_combat_rounds."""
        from graph import context_manager

        config = GameConfig(max_combat_rounds=10)
        combat = _make_active_combat_state(round_number=5)  # will become 6 <= 10
        state = _make_game_state(combat_state=combat, game_config=config)

        result = context_manager(state)

        assert result["combat_state"].active is True
        assert result["combat_state"].round_number == 6

    def test_combat_state_fields_all_reset(self) -> None:
        """All combat_state fields reset on force-end."""
        from graph import context_manager

        config = GameConfig(max_combat_rounds=1)
        combat = _make_active_combat_state(round_number=1)
        state = _make_game_state(combat_state=combat, game_config=config)

        result = context_manager(state)

        cs = result["combat_state"]
        assert cs.active is False
        assert cs.round_number == 0
        assert cs.initiative_order == []
        assert cs.initiative_rolls == {}
        assert cs.original_turn_queue == []
        assert cs.npc_profiles == {}

    def test_force_end_at_exact_boundary(self) -> None:
        """Force-ends at exact boundary (round 5+1=6 > max 5)."""
        from graph import context_manager

        config = GameConfig(max_combat_rounds=5)
        combat = _make_active_combat_state(round_number=5)
        state = _make_game_state(combat_state=combat, game_config=config)

        result = context_manager(state)
        assert result["combat_state"].active is False

    def test_does_not_force_end_at_max_equals_round(self) -> None:
        """Does not force-end when round+1 == max (still within limit)."""
        from graph import context_manager

        config = GameConfig(max_combat_rounds=6)
        combat = _make_active_combat_state(round_number=5)  # will become 6 == 6
        state = _make_game_state(combat_state=combat, game_config=config)

        result = context_manager(state)
        # 6 is NOT > 6, so combat continues
        assert result["combat_state"].active is True
        assert result["combat_state"].round_number == 6

    def test_force_end_empty_original_queue_preserves_turn_queue(self) -> None:
        """Force-end with empty original_turn_queue preserves current turn_queue."""
        from graph import context_manager

        config = GameConfig(max_combat_rounds=2)
        combat = CombatState(
            active=True,
            round_number=2,
            initiative_order=["fighter", "dm:goblin_1"],
            original_turn_queue=[],  # empty backup
        )
        current_queue = ["dm", "fighter", "rogue"]
        state = _make_game_state(
            combat_state=combat,
            game_config=config,
            turn_queue=current_queue,
        )

        result = context_manager(state)

        assert result["combat_state"].active is False
        # turn_queue should be unchanged since original_turn_queue was empty
        assert result["turn_queue"] == current_queue


# =============================================================================
# TestContextManagerMaxRoundDisabled
# =============================================================================


class TestContextManagerMaxRoundDisabled:
    """Tests for max_combat_rounds=0 disabling the limit (AC #10)."""

    def test_zero_skips_limit_check(self) -> None:
        """max_combat_rounds=0 skips the limit check entirely."""
        from graph import context_manager

        config = GameConfig(max_combat_rounds=0)
        combat = _make_active_combat_state(round_number=99)
        state = _make_game_state(combat_state=combat, game_config=config)

        result = context_manager(state)

        # Combat should still be active (round 100)
        assert result["combat_state"].active is True
        assert result["combat_state"].round_number == 100

    def test_combat_continues_past_100_rounds(self) -> None:
        """Combat continues past round 100 when max_combat_rounds=0."""
        from graph import context_manager

        config = GameConfig(max_combat_rounds=0)
        combat = _make_active_combat_state(round_number=200)
        state = _make_game_state(combat_state=combat, game_config=config)

        result = context_manager(state)

        assert result["combat_state"].active is True
        assert result["combat_state"].round_number == 201


# =============================================================================
# TestCombatEndRoutingRestoration
# =============================================================================


class TestCombatEndRoutingRestoration:
    """Tests for routing after combat ends (AC #12)."""

    def test_route_uses_turn_queue_after_combat_ends(self) -> None:
        """route_to_next_agent uses turn_queue after combat_state is reset (AC #12)."""
        from graph import route_to_next_agent

        state = _make_game_state(
            turn_queue=["dm", "fighter", "rogue", "wizard"],
            combat_state=CombatState(),  # reset / not active
        )
        state["current_turn"] = "dm"

        next_agent = route_to_next_agent(state)

        assert next_agent == "fighter"

    def test_route_does_not_use_initiative_order_after_end(self) -> None:
        """route_to_next_agent does not use initiative_order after combat ends."""
        from graph import route_to_next_agent

        # CombatState is inactive with leftover data (shouldn't happen but defensive)
        combat = CombatState(
            active=False,
            initiative_order=["wizard", "rogue", "fighter", "dm"],
        )
        state = _make_game_state(
            turn_queue=["dm", "fighter", "rogue", "wizard"],
            combat_state=combat,
        )
        state["current_turn"] = "dm"

        next_agent = route_to_next_agent(state)

        # Should follow turn_queue, not initiative_order
        assert next_agent == "fighter"

    def test_full_round_routing_after_combat_end(self) -> None:
        """Full round of routing uses turn_queue after combat ends."""
        from langgraph.graph import END

        from graph import route_to_next_agent

        turn_queue = ["dm", "fighter", "rogue", "wizard"]
        state = _make_game_state(
            turn_queue=turn_queue,
            combat_state=CombatState(),
        )

        # Walk through the entire turn queue
        state["current_turn"] = "dm"
        assert route_to_next_agent(state) == "fighter"

        state["current_turn"] = "fighter"
        assert route_to_next_agent(state) == "rogue"

        state["current_turn"] = "rogue"
        assert route_to_next_agent(state) == "wizard"

        state["current_turn"] = "wizard"
        assert route_to_next_agent(state) == END


# =============================================================================
# TestCombatEndStateClear
# =============================================================================


class TestCombatEndStateClear:
    """Tests for complete combat state reset after end combat (AC #2, #11)."""

    def test_all_fields_at_defaults(self) -> None:
        """All CombatState fields are at defaults after end combat."""
        from agents import _execute_end_combat

        combat = _make_active_combat_state()
        state = _make_game_state(combat_state=combat)

        _, reset_cs, _ = _execute_end_combat(state)

        assert reset_cs == CombatState()

    def test_npc_profiles_empty_dead_npc_cleanup(self) -> None:
        """npc_profiles is empty -- dead NPC cleanup (AC #11)."""
        from agents import _execute_end_combat

        npcs = {
            "goblin_1": NpcProfile(name="Goblin 1", hp_max=7, hp_current=0),
            "goblin_2": NpcProfile(name="Goblin 2", hp_max=7, hp_current=0),
        }
        combat = _make_active_combat_state(npcs=npcs)
        state = _make_game_state(combat_state=combat)

        _, reset_cs, _ = _execute_end_combat(state)

        assert reset_cs.npc_profiles == {}

    def test_initiative_order_empty(self) -> None:
        """initiative_order is empty after end combat."""
        from agents import _execute_end_combat

        combat = _make_active_combat_state()
        state = _make_game_state(combat_state=combat)

        _, reset_cs, _ = _execute_end_combat(state)
        assert reset_cs.initiative_order == []

    def test_initiative_rolls_empty(self) -> None:
        """initiative_rolls is empty after end combat."""
        from agents import _execute_end_combat

        combat = _make_active_combat_state()
        state = _make_game_state(combat_state=combat)

        _, reset_cs, _ = _execute_end_combat(state)
        assert reset_cs.initiative_rolls == {}

    def test_original_turn_queue_empty(self) -> None:
        """original_turn_queue is empty after end combat."""
        from agents import _execute_end_combat

        combat = _make_active_combat_state()
        state = _make_game_state(combat_state=combat)

        _, reset_cs, _ = _execute_end_combat(state)
        assert reset_cs.original_turn_queue == []

    def test_active_is_false(self) -> None:
        """active is False after end combat."""
        from agents import _execute_end_combat

        combat = _make_active_combat_state()
        state = _make_game_state(combat_state=combat)

        _, reset_cs, _ = _execute_end_combat(state)
        assert reset_cs.active is False

    def test_round_number_is_zero(self) -> None:
        """round_number is 0 after end combat."""
        from agents import _execute_end_combat

        combat = _make_active_combat_state()
        state = _make_game_state(combat_state=combat)

        _, reset_cs, _ = _execute_end_combat(state)
        assert reset_cs.round_number == 0


# =============================================================================
# TestPersistenceBackwardCompat
# =============================================================================


class TestPersistenceBackwardCompat:
    """Tests for backward compatibility with max_combat_rounds (AC #6)."""

    def test_old_config_without_max_combat_rounds_gets_default(self) -> None:
        """Old GameConfig JSON without max_combat_rounds deserializes with default 50."""
        old_data = {
            "combat_mode": "Tactical",
            "summarizer_provider": "gemini",
            "summarizer_model": "gemini-1.5-flash",
            "extractor_provider": "gemini",
            "extractor_model": "gemini-3-flash-preview",
            "party_size": 4,
            "narrative_display_limit": 50,
        }
        config = GameConfig(**old_data)
        assert config.max_combat_rounds == 50

    def test_config_with_max_combat_rounds_roundtrip(self) -> None:
        """GameConfig with max_combat_rounds serializes and deserializes correctly."""
        config = GameConfig(max_combat_rounds=25)
        data = config.model_dump()
        restored = GameConfig(**data)
        assert restored.max_combat_rounds == 25

    def test_config_with_zero_max_combat_rounds_roundtrip(self) -> None:
        """GameConfig with max_combat_rounds=0 round-trips correctly."""
        config = GameConfig(max_combat_rounds=0)
        data = config.model_dump()
        restored = GameConfig(**data)
        assert restored.max_combat_rounds == 0

    def test_model_dump_includes_max_combat_rounds(self) -> None:
        """model_dump() includes max_combat_rounds field."""
        config = GameConfig(max_combat_rounds=30)
        data = config.model_dump()
        assert "max_combat_rounds" in data
        assert data["max_combat_rounds"] == 30
