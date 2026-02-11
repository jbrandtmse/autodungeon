"""Tests for Story 15.3: Combat-Aware Routing.

Tests for route_to_next_agent() combat/non-combat routing, round increment
in context_manager(), recursion limit adjustments in run_single_round(),
combat_state passthrough in node functions, and post-combat routing restoration.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from langgraph.graph import END

from graph import (
    context_manager,
    create_game_workflow,
    human_intervention_node,
    route_to_next_agent,
    run_single_round,
)
from models import (
    AgentMemory,
    AgentSecrets,
    CallbackLog,
    CharacterConfig,
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


def _make_game_state(
    turn_queue: list[str] | None = None,
    current_turn: str = "dm",
    human_active: bool = False,
    controlled_character: str | None = None,
    combat_state: CombatState | None = None,
) -> GameState:
    """Build a minimal GameState for combat routing tests."""
    if turn_queue is None:
        turn_queue = ["dm", "shadowmere", "thorin"]
    if combat_state is None:
        combat_state = CombatState()

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
            party_size=len(turn_queue) - 1,
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
        human_active=human_active,
        controlled_character=controlled_character,
        session_number=1,
        session_id="001",
        summarization_in_progress=False,
        selected_module=None,
        character_sheets={},
        agent_secrets={"dm": AgentSecrets()},
        narrative_elements={},
        callback_database=NarrativeElementStore(),
        callback_log=CallbackLog(),
        active_fork_id=None,
        combat_state=combat_state,
    )


def _active_combat_state(
    initiative_order: list[str] | None = None,
    round_number: int = 1,
) -> CombatState:
    """Build an active CombatState with the given initiative order."""
    if initiative_order is None:
        initiative_order = [
            "dm",
            "dm:goblin_1",
            "shadowmere",
            "dm:goblin_2",
            "thorin",
        ]
    return CombatState(
        active=True,
        round_number=round_number,
        initiative_order=initiative_order,
        initiative_rolls={},
        original_turn_queue=["dm", "shadowmere", "thorin"],
        npc_profiles={},
    )


# =============================================================================
# TestRouteToNextAgentNonCombat
# =============================================================================


class TestRouteToNextAgentNonCombat:
    """Verify all existing non-combat routing behavior is preserved."""

    def test_dm_routes_to_first_pc(self) -> None:
        """DM routes to first PC in turn_queue."""
        state = _make_game_state(current_turn="dm")
        assert route_to_next_agent(state) == "shadowmere"

    def test_pc_routes_to_next_pc(self) -> None:
        """First PC routes to second PC."""
        state = _make_game_state(current_turn="shadowmere")
        assert route_to_next_agent(state) == "thorin"

    def test_last_pc_returns_end(self) -> None:
        """Last PC in turn_queue returns END."""
        state = _make_game_state(current_turn="thorin")
        assert route_to_next_agent(state) == END

    def test_combat_state_at_defaults_uses_turn_queue(self) -> None:
        """CombatState with active=False uses turn_queue (no behavior change)."""
        state = _make_game_state(
            current_turn="dm",
            combat_state=CombatState(),
        )
        assert route_to_next_agent(state) == "shadowmere"

    def test_combat_state_inactive_uses_turn_queue(self) -> None:
        """Explicit inactive combat state still uses turn_queue."""
        state = _make_game_state(
            current_turn="dm",
            combat_state=CombatState(active=False, initiative_order=["dm", "thorin"]),
        )
        assert route_to_next_agent(state) == "shadowmere"

    def test_combat_state_active_but_empty_order_uses_turn_queue(self) -> None:
        """Active combat with empty initiative_order falls back to turn_queue."""
        state = _make_game_state(
            current_turn="dm",
            combat_state=CombatState(active=True, initiative_order=[]),
        )
        assert route_to_next_agent(state) == "shadowmere"

    def test_unknown_current_turn_defaults_to_dm(self) -> None:
        """Unknown current_turn defaults to 'dm'."""
        state = _make_game_state(current_turn="nobody")
        assert route_to_next_agent(state) == "dm"

    def test_human_intervention_in_non_combat(self) -> None:
        """Human intervention works in non-combat mode."""
        state = _make_game_state(
            current_turn="shadowmere",
            human_active=True,
            controlled_character="shadowmere",
        )
        assert route_to_next_agent(state) == "human"

    def test_human_intervention_does_not_trigger_for_dm(self) -> None:
        """Human intervention does not trigger when current is DM."""
        state = _make_game_state(
            current_turn="dm",
            human_active=True,
            controlled_character="shadowmere",
        )
        # current="dm" is blocked by `current != "dm"` check
        # Routes normally to next in turn_queue
        assert route_to_next_agent(state) == "shadowmere"

    def test_human_intervention_not_active(self) -> None:
        """When human_active=False, no human routing even with controlled_character."""
        state = _make_game_state(
            current_turn="shadowmere",
            human_active=False,
            controlled_character="shadowmere",
        )
        assert route_to_next_agent(state) == "thorin"


# =============================================================================
# TestRouteToNextAgentCombat
# =============================================================================


class TestRouteToNextAgentCombat:
    """Combat routing with initiative_order."""

    def test_dm_bookend_routes_to_next_in_initiative(self) -> None:
        """DM bookend (position 0) routes to next initiative entry."""
        combat = _active_combat_state()
        state = _make_game_state(current_turn="dm", combat_state=combat)
        # Next after dm is dm:goblin_1, which routes to "dm"
        assert route_to_next_agent(state) == "dm"

    def test_npc_routes_to_next_pc(self) -> None:
        """NPC entry routes to next entry (a PC)."""
        combat = _active_combat_state()
        state = _make_game_state(current_turn="dm:goblin_1", combat_state=combat)
        # Next after dm:goblin_1 is shadowmere
        assert route_to_next_agent(state) == "shadowmere"

    def test_pc_routes_to_next_npc(self) -> None:
        """PC routes to next NPC entry (routed to 'dm')."""
        combat = _active_combat_state()
        state = _make_game_state(current_turn="shadowmere", combat_state=combat)
        # Next after shadowmere is dm:goblin_2 -> routes to "dm"
        assert route_to_next_agent(state) == "dm"

    def test_last_entry_returns_end(self) -> None:
        """Last entry in initiative_order returns END."""
        combat = _active_combat_state()
        state = _make_game_state(current_turn="thorin", combat_state=combat)
        assert route_to_next_agent(state) == END

    def test_initiative_order_with_only_pcs(self) -> None:
        """Initiative order with only PCs (no NPCs) works correctly."""
        combat = _active_combat_state(
            initiative_order=["dm", "shadowmere", "thorin"]
        )
        state = _make_game_state(current_turn="dm", combat_state=combat)
        assert route_to_next_agent(state) == "shadowmere"

    def test_initiative_order_with_only_npcs(self) -> None:
        """Edge case: initiative order with only NPCs (all route to 'dm')."""
        combat = _active_combat_state(
            initiative_order=["dm", "dm:goblin_1", "dm:goblin_2"]
        )
        state = _make_game_state(current_turn="dm", combat_state=combat)
        assert route_to_next_agent(state) == "dm"

    def test_mid_order_pc_routing(self) -> None:
        """PC in middle of initiative order advances correctly."""
        combat = _active_combat_state(
            initiative_order=["dm", "shadowmere", "thorin", "dm:wolf"]
        )
        state = _make_game_state(current_turn="shadowmere", combat_state=combat)
        assert route_to_next_agent(state) == "thorin"

    def test_unknown_current_in_combat_defaults_to_dm(self) -> None:
        """Unknown current_turn during combat defaults to 'dm'."""
        combat = _active_combat_state()
        state = _make_game_state(current_turn="unknown_agent", combat_state=combat)
        assert route_to_next_agent(state) == "dm"


# =============================================================================
# TestRouteToNextAgentNpcRouting
# =============================================================================


class TestRouteToNextAgentNpcRouting:
    """NPC entries route to 'dm' node."""

    def test_dm_colon_goblin_routes_to_dm(self) -> None:
        """'dm:goblin_1' as next entry returns 'dm'."""
        combat = _active_combat_state(
            initiative_order=["dm", "dm:goblin_1", "shadowmere"]
        )
        state = _make_game_state(current_turn="dm", combat_state=combat)
        assert route_to_next_agent(state) == "dm"

    def test_dm_colon_wolf_routes_to_dm(self) -> None:
        """'dm:wolf' as next entry returns 'dm'."""
        combat = _active_combat_state(
            initiative_order=["dm", "dm:wolf", "shadowmere"]
        )
        state = _make_game_state(current_turn="dm", combat_state=combat)
        assert route_to_next_agent(state) == "dm"

    def test_npc_first_after_bookend(self) -> None:
        """NPC immediately after DM bookend routes to 'dm'."""
        combat = _active_combat_state(
            initiative_order=["dm", "dm:skeleton", "thorin"]
        )
        state = _make_game_state(current_turn="dm", combat_state=combat)
        assert route_to_next_agent(state) == "dm"

    def test_npc_in_middle(self) -> None:
        """NPC in middle of order routes to 'dm'."""
        combat = _active_combat_state(
            initiative_order=["dm", "shadowmere", "dm:ogre", "thorin"]
        )
        state = _make_game_state(current_turn="shadowmere", combat_state=combat)
        assert route_to_next_agent(state) == "dm"

    def test_npc_last_before_end(self) -> None:
        """NPC as last entry returns END (not 'dm')."""
        combat = _active_combat_state(
            initiative_order=["dm", "shadowmere", "dm:dragon"]
        )
        state = _make_game_state(current_turn="dm:dragon", combat_state=combat)
        assert route_to_next_agent(state) == END

    def test_consecutive_npcs(self) -> None:
        """Consecutive NPC entries both route to 'dm'."""
        combat = _active_combat_state(
            initiative_order=["dm", "dm:goblin_1", "dm:goblin_2", "shadowmere"]
        )
        # After dm bookend, next is dm:goblin_1 -> routes to "dm"
        state = _make_game_state(current_turn="dm", combat_state=combat)
        assert route_to_next_agent(state) == "dm"

        # After dm:goblin_1, next is dm:goblin_2 -> routes to "dm"
        state2 = _make_game_state(current_turn="dm:goblin_1", combat_state=combat)
        assert route_to_next_agent(state2) == "dm"


# =============================================================================
# TestRouteToNextAgentHumanIntervention
# =============================================================================


class TestRouteToNextAgentHumanIntervention:
    """Human override works in combat routing."""

    def test_human_override_during_combat_for_controlled_character(self) -> None:
        """Human override triggers when controlled character just acted in combat."""
        combat = _active_combat_state(
            initiative_order=["dm", "dm:goblin_1", "shadowmere", "thorin"]
        )
        state = _make_game_state(
            current_turn="shadowmere",
            human_active=True,
            controlled_character="shadowmere",
            combat_state=combat,
        )
        # Current is shadowmere == controlled_character, and current != "dm"
        assert route_to_next_agent(state) == "human"

    def test_human_override_does_not_trigger_for_next_agent(self) -> None:
        """Human override does NOT trigger based on next agent identity.

        Human override only triggers when current == controlled_character.
        The human node runs AFTER the controlled character's AI turn.
        """
        combat = _active_combat_state(
            initiative_order=["dm", "dm:goblin_1", "shadowmere", "thorin"]
        )
        state = _make_game_state(
            current_turn="dm:goblin_1",
            human_active=True,
            controlled_character="shadowmere",
            combat_state=combat,
        )
        # current="dm:goblin_1" != controlled_character, so normal routing
        # Next is shadowmere (a PC, not NPC), so return "shadowmere"
        assert route_to_next_agent(state) == "shadowmere"

    def test_human_override_does_not_trigger_for_npc_turns(self) -> None:
        """Human override does NOT trigger for NPC turns."""
        combat = _active_combat_state(
            initiative_order=["dm", "dm:goblin_1", "shadowmere", "thorin"]
        )
        state = _make_game_state(
            current_turn="dm",
            human_active=True,
            controlled_character="thorin",
            combat_state=combat,
        )
        # current="dm", next is "dm:goblin_1" which is NPC, not controlled_character
        # Should route to "dm" (NPC turn)
        assert route_to_next_agent(state) == "dm"

    def test_human_override_does_not_trigger_for_dm_bookend(self) -> None:
        """Human override does NOT trigger during DM bookend turn."""
        combat = _active_combat_state(
            initiative_order=["dm", "shadowmere", "thorin"]
        )
        state = _make_game_state(
            current_turn="dm",
            human_active=True,
            controlled_character="dm",
            combat_state=combat,
        )
        # current="dm" is blocked by `current != "dm"` check
        assert route_to_next_agent(state) == "shadowmere"

    def test_human_override_controlled_char_not_in_initiative(self) -> None:
        """Human override gracefully handles controlled char not in initiative."""
        combat = _active_combat_state(
            initiative_order=["dm", "dm:goblin_1", "thorin"]
        )
        state = _make_game_state(
            current_turn="dm",
            human_active=True,
            controlled_character="shadowmere",  # Not in initiative_order
            combat_state=combat,
        )
        # Next is dm:goblin_1 which is not controlled_character -> routes to "dm"
        assert route_to_next_agent(state) == "dm"


# =============================================================================
# TestRouteToNextAgentRoundCompletion
# =============================================================================


class TestRouteToNextAgentRoundCompletion:
    """END signal at last initiative entry."""

    def test_end_at_last_in_initiative_order(self) -> None:
        """END returned when current is last in initiative_order."""
        combat = _active_combat_state(
            initiative_order=["dm", "shadowmere", "thorin"]
        )
        state = _make_game_state(current_turn="thorin", combat_state=combat)
        assert route_to_next_agent(state) == END

    def test_end_at_last_in_turn_queue_non_combat(self) -> None:
        """END returned when current is last in turn_queue (non-combat)."""
        state = _make_game_state(current_turn="thorin")
        assert route_to_next_agent(state) == END

    def test_single_entry_initiative_order(self) -> None:
        """Single entry in initiative_order returns END immediately."""
        combat = _active_combat_state(initiative_order=["dm"])
        state = _make_game_state(current_turn="dm", combat_state=combat)
        assert route_to_next_agent(state) == END

    def test_end_after_npc_last(self) -> None:
        """END returned when last entry is NPC and current is that NPC."""
        combat = _active_combat_state(
            initiative_order=["dm", "shadowmere", "dm:goblin_1"]
        )
        state = _make_game_state(current_turn="dm:goblin_1", combat_state=combat)
        assert route_to_next_agent(state) == END


# =============================================================================
# TestCombatRoundIncrement
# =============================================================================


class TestCombatRoundIncrement:
    """Round_number increments in context_manager during combat."""

    def test_increments_round_number_when_combat_active(self) -> None:
        """context_manager increments round_number when combat active."""
        combat = _active_combat_state(round_number=1)
        state = _make_game_state(combat_state=combat)
        result = context_manager(state)
        assert result["combat_state"].round_number == 2

    def test_does_not_increment_when_combat_inactive(self) -> None:
        """context_manager does NOT increment when combat inactive."""
        state = _make_game_state(combat_state=CombatState())
        result = context_manager(state)
        assert result["combat_state"].round_number == 0

    def test_round_number_1_to_2(self) -> None:
        """Round_number goes from 1 to 2 on second round."""
        combat = _active_combat_state(round_number=1)
        state = _make_game_state(combat_state=combat)
        result = context_manager(state)
        assert result["combat_state"].round_number == 2

    def test_round_number_sequence(self) -> None:
        """Round_number sequence: 1 -> 2 -> 3 over multiple rounds."""
        combat = _active_combat_state(round_number=1)
        state = _make_game_state(combat_state=combat)

        # Round 1 -> 2
        result1 = context_manager(state)
        assert result1["combat_state"].round_number == 2

        # Round 2 -> 3
        result2 = context_manager(result1)
        assert result2["combat_state"].round_number == 3

    def test_does_not_modify_other_combat_state_fields(self) -> None:
        """context_manager does not modify other combat_state fields."""
        combat = _active_combat_state(round_number=1)
        combat_with_data = combat.model_copy(
            update={
                "initiative_rolls": {"shadowmere": 15, "thorin": 10},
                "npc_profiles": {"goblin_1": NpcProfile(name="Goblin 1")},
            }
        )
        state = _make_game_state(combat_state=combat_with_data)
        result = context_manager(state)

        result_combat = result["combat_state"]
        assert result_combat.round_number == 2
        assert result_combat.active is True
        assert result_combat.initiative_order == combat_with_data.initiative_order
        assert result_combat.initiative_rolls == {"shadowmere": 15, "thorin": 10}
        assert "goblin_1" in result_combat.npc_profiles
        assert result_combat.original_turn_queue == combat_with_data.original_turn_queue

    def test_does_not_increment_round_0(self) -> None:
        """Round 0 (not started) is not incremented even with active=True."""
        combat = CombatState(active=True, round_number=0, initiative_order=["dm"])
        state = _make_game_state(combat_state=combat)
        result = context_manager(state)
        # round_number=0 and >=1 is False, so no increment
        assert result["combat_state"].round_number == 0


# =============================================================================
# TestRunSingleRoundRecursionLimit
# =============================================================================


class TestRunSingleRoundRecursionLimit:
    """Recursion limit adjusts for combat."""

    @patch("graph.create_game_workflow")
    @patch("persistence.get_latest_checkpoint", return_value=0)
    def test_uses_turn_queue_length_without_combat(
        self, mock_checkpoint: MagicMock, mock_create: MagicMock
    ) -> None:
        """Recursion limit uses turn_queue length when no combat."""
        state = _make_game_state()
        mock_workflow = MagicMock()
        mock_workflow.invoke.return_value = state
        mock_create.return_value = mock_workflow

        run_single_round(state)

        # turn_queue has 3 items: ["dm", "shadowmere", "thorin"]
        mock_workflow.invoke.assert_called_once()
        call_config = mock_workflow.invoke.call_args[1]["config"]
        assert call_config["recursion_limit"] == 5  # 3 + 2

    @patch("graph.create_game_workflow")
    @patch("persistence.get_latest_checkpoint", return_value=0)
    def test_uses_initiative_order_length_when_combat_active(
        self, mock_checkpoint: MagicMock, mock_create: MagicMock
    ) -> None:
        """Recursion limit uses initiative_order length when combat active."""
        combat = _active_combat_state(
            initiative_order=["dm", "dm:goblin_1", "shadowmere", "dm:goblin_2", "thorin"]
        )
        state = _make_game_state(combat_state=combat)
        mock_workflow = MagicMock()
        mock_workflow.invoke.return_value = state
        mock_create.return_value = mock_workflow

        run_single_round(state)

        mock_workflow.invoke.assert_called_once()
        call_config = mock_workflow.invoke.call_args[1]["config"]
        # initiative_order has 5 items, turn_queue has 3 -> max(3, 5) + 2 = 7
        assert call_config["recursion_limit"] == 7

    @patch("graph.create_game_workflow")
    @patch("persistence.get_latest_checkpoint", return_value=0)
    def test_uses_max_of_turn_queue_and_initiative(
        self, mock_checkpoint: MagicMock, mock_create: MagicMock
    ) -> None:
        """Recursion limit uses max of turn_queue and initiative_order."""
        # initiative_order shorter than turn_queue
        combat = _active_combat_state(initiative_order=["dm", "thorin"])
        state = _make_game_state(combat_state=combat)
        mock_workflow = MagicMock()
        mock_workflow.invoke.return_value = state
        mock_create.return_value = mock_workflow

        run_single_round(state)

        mock_workflow.invoke.assert_called_once()
        call_config = mock_workflow.invoke.call_args[1]["config"]
        # turn_queue has 3 items, initiative has 2 -> max(3, 2) + 2 = 5
        assert call_config["recursion_limit"] == 5


# =============================================================================
# TestCombatStatePassthrough
# =============================================================================


class TestCombatStatePassthrough:
    """dm_turn and pc_turn preserve combat_state."""

    @patch("agents.create_dm_agent")
    @patch("agents._build_dm_context", return_value="context")
    @patch("agents._extract_response_text", return_value="The adventure continues.")
    @patch("memory.extract_narrative_elements")
    def test_dm_turn_returns_combat_state(
        self,
        mock_extract: MagicMock,
        mock_text: MagicMock,
        mock_context: MagicMock,
        mock_agent: MagicMock,
    ) -> None:
        """dm_turn return includes combat_state."""
        from agents import dm_turn

        mock_extract.return_value = {
            "narrative_elements": {},
            "callback_database": NarrativeElementStore(),
            "callback_log": CallbackLog(),
        }
        mock_response = MagicMock()
        mock_response.tool_calls = None
        mock_response.content = "The adventure continues."
        mock_agent.return_value.invoke.return_value = mock_response

        combat = _active_combat_state(round_number=2)
        state = _make_game_state(combat_state=combat)

        with patch("agents.st", create=True):
            result = dm_turn(state)

        assert "combat_state" in result
        assert result["combat_state"].active is True
        assert result["combat_state"].round_number == 2

    @patch("agents.create_pc_agent")
    @patch("agents._build_pc_context", return_value="context")
    @patch("agents.build_pc_system_prompt", return_value="system prompt")
    @patch("agents._extract_response_text", return_value="I swing my sword.")
    @patch("agents._build_pc_turn_prompt", return_value="What do you do?")
    @patch("tools.resolve_inline_dice_notation", side_effect=lambda x: x)
    @patch("memory.extract_narrative_elements")
    def test_pc_turn_returns_combat_state(
        self,
        mock_extract: MagicMock,
        mock_resolve: MagicMock,
        mock_turn_prompt: MagicMock,
        mock_text: MagicMock,
        mock_sys_prompt: MagicMock,
        mock_context: MagicMock,
        mock_agent: MagicMock,
    ) -> None:
        """pc_turn return includes combat_state."""
        from agents import pc_turn

        mock_extract.return_value = {
            "narrative_elements": {},
            "callback_database": NarrativeElementStore(),
            "callback_log": CallbackLog(),
        }
        mock_response = MagicMock()
        mock_response.tool_calls = None
        mock_response.content = "I swing my sword."
        mock_agent.return_value.invoke.return_value = mock_response

        combat = _active_combat_state(round_number=3)
        state = _make_game_state(combat_state=combat)

        result = pc_turn(state, "shadowmere")

        assert "combat_state" in result
        assert result["combat_state"].active is True
        assert result["combat_state"].round_number == 3

    @patch("graph.st", create=True)
    def test_human_intervention_node_returns_combat_state(
        self, mock_st: MagicMock
    ) -> None:
        """human_intervention_node return includes combat_state."""
        combat = _active_combat_state(round_number=2)
        state = _make_game_state(
            current_turn="shadowmere",
            human_active=True,
            controlled_character="shadowmere",
            combat_state=combat,
        )

        # No pending action -> returns state as-is
        mock_st.session_state = {"human_pending_action": None}

        result = human_intervention_node(state)
        assert "combat_state" in result
        assert result["combat_state"].active is True
        assert result["combat_state"].round_number == 2

    def test_context_manager_returns_combat_state(self) -> None:
        """context_manager return includes combat_state."""
        combat = _active_combat_state(round_number=1)
        state = _make_game_state(combat_state=combat)

        result = context_manager(state)
        assert "combat_state" in result
        assert result["combat_state"].active is True
        # round_number was 1, context_manager increments to 2
        assert result["combat_state"].round_number == 2

    def test_context_manager_preserves_inactive_combat_state(self) -> None:
        """context_manager preserves inactive combat_state without modification."""
        state = _make_game_state(combat_state=CombatState())

        result = context_manager(state)
        assert "combat_state" in result
        assert result["combat_state"].active is False
        assert result["combat_state"].round_number == 0


# =============================================================================
# TestCombatEndRestoresRouting
# =============================================================================


class TestCombatEndRestoresRouting:
    """After end_combat, routing uses turn_queue again."""

    def test_routing_uses_turn_queue_after_combat_ends(self) -> None:
        """Routing uses turn_queue after combat_state.active becomes False."""
        # Simulate post-combat: active=False, initiative_order still populated
        combat = CombatState(
            active=False,
            round_number=5,
            initiative_order=["dm", "dm:goblin_1", "shadowmere", "thorin"],
            original_turn_queue=["dm", "shadowmere", "thorin"],
        )
        state = _make_game_state(current_turn="dm", combat_state=combat)
        # Should use turn_queue since active=False
        assert route_to_next_agent(state) == "shadowmere"

    def test_routing_uses_turn_queue_after_reset_to_defaults(self) -> None:
        """Routing uses turn_queue after combat_state is reset to defaults."""
        state = _make_game_state(
            current_turn="dm",
            combat_state=CombatState(),
        )
        assert route_to_next_agent(state) == "shadowmere"

    def test_end_combat_and_next_round(self) -> None:
        """After combat ends mid-round, next round uses turn_queue."""
        # Combat just ended: active=False
        combat = CombatState(active=False)
        state = _make_game_state(current_turn="shadowmere", combat_state=combat)
        # Should follow turn_queue: shadowmere -> thorin
        assert route_to_next_agent(state) == "thorin"


# =============================================================================
# TestCreateGameWorkflowCombat
# =============================================================================


class TestCreateGameWorkflowCombat:
    """Workflow creation handles combat routing."""

    def test_workflow_compiles_with_standard_turn_queue(self) -> None:
        """Workflow compiles normally (no combat-specific nodes needed)."""
        workflow = create_game_workflow(["dm", "shadowmere", "thorin"])
        assert hasattr(workflow, "invoke")

    def test_route_only_returns_valid_node_names(self) -> None:
        """route_to_next_agent only returns valid node names."""
        combat = _active_combat_state(
            initiative_order=[
                "dm",
                "dm:goblin_1",
                "shadowmere",
                "dm:goblin_2",
                "thorin",
            ]
        )
        valid_returns = {"dm", "shadowmere", "thorin", "human", END}

        # Test each position in initiative_order
        for entry in combat.initiative_order:
            state = _make_game_state(current_turn=entry, combat_state=combat)
            result = route_to_next_agent(state)
            assert result in valid_returns, f"Unexpected return '{result}' for current_turn='{entry}'"

    def test_npc_entries_never_returned_as_routing_target(self) -> None:
        """'dm:npc_name' is never returned by route_to_next_agent."""
        combat = _active_combat_state(
            initiative_order=[
                "dm",
                "dm:goblin_1",
                "dm:goblin_2",
                "shadowmere",
                "dm:wolf",
                "thorin",
            ]
        )

        for entry in combat.initiative_order:
            state = _make_game_state(current_turn=entry, combat_state=combat)
            result = route_to_next_agent(state)
            assert not (isinstance(result, str) and result.startswith("dm:")), (
                f"NPC entry '{result}' leaked as routing target from current_turn='{entry}'"
            )

    def test_workflow_routing_map_includes_dm(self) -> None:
        """Workflow routing map includes 'dm' for NPC turn routing."""
        workflow = create_game_workflow(["dm", "shadowmere", "thorin"])
        graph = workflow.get_graph()
        # DM node should exist
        assert "dm" in graph.nodes
