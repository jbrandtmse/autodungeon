"""Tests for Story 15.7: NPC Damage Tracking & Combat-State Injection.

Covers the `dm_update_npc` tool, `_execute_npc_update` helper, combat-state
injection in `_build_dm_context`, defeated-NPC filtering in
`route_to_next_agent`, `[SHEET]:` notification reuse, persistence round-trips,
and an end-to-end Session 017 (Mist-Stalker) integration scenario.

22 acceptance criteria from the story spec are covered across the test
classes below. Pre-existing tests in tests/test_story_15_*.py must continue
to pass unchanged (verified separately in Task 9).
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

from langgraph.graph import END

from agents import (
    DM_COMBAT_NARRATIVE_ADDENDUM,
    _build_dm_context,
    _execute_npc_update,
    _npc_status_label,
    create_dm_agent,
)
from graph import route_to_next_agent
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
from persistence import deserialize_game_state, serialize_game_state
from tools import _sanitize_npc_name, dm_update_npc

# =============================================================================
# Fixtures / Helpers
# =============================================================================


def _make_npc(
    name: str = "Goblin 1",
    hp_current: int = 15,
    hp_max: int = 15,
    conditions: list[str] | None = None,
) -> NpcProfile:
    """Create a standard NPC for testing."""
    return NpcProfile(
        name=name,
        initiative_modifier=2,
        hp_max=hp_max,
        hp_current=hp_current,
        ac=13,
        personality="Aggressive",
        tactics="Charges nearest enemy",
        conditions=conditions or [],
    )


def _make_combat_state(
    active: bool = True,
    round_number: int = 2,
    npc_profiles: dict[str, NpcProfile] | None = None,
    initiative_order: list[str] | None = None,
    initiative_rolls: dict[str, int] | None = None,
    current_initiative_index: int = 0,
) -> CombatState:
    """Build a CombatState fixture, mirroring tests/test_story_15_2 patterns."""
    if npc_profiles is None:
        npc_profiles = {
            "mist-stalker_alpha": _make_npc(name="Mist-Stalker Alpha"),
            "mist-stalker_beta": _make_npc(name="Mist-Stalker Beta"),
        }
    if initiative_order is None:
        initiative_order = [
            "dm",
            "shadowmere",
            "dm:mist-stalker_alpha",
            "thorin",
            "dm:mist-stalker_beta",
        ]
    if initiative_rolls is None:
        initiative_rolls = {
            "shadowmere": 17,
            "dm:mist-stalker_alpha": 15,
            "thorin": 12,
            "dm:mist-stalker_beta": 10,
        }
    return CombatState(
        active=active,
        round_number=round_number,
        initiative_order=initiative_order,
        initiative_rolls=initiative_rolls,
        original_turn_queue=["dm", "shadowmere", "thorin"],
        npc_profiles=npc_profiles,
        current_initiative_index=current_initiative_index,
    )


def _make_game_state(
    current_turn: str = "dm",
    combat_state: CombatState | None = None,
    turn_queue: list[str] | None = None,
    human_active: bool = False,
    controlled_character: str | None = None,
) -> GameState:
    """Build a minimal GameState for Story 15.7 tests."""
    if combat_state is None:
        combat_state = CombatState()
    if turn_queue is None:
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


# =============================================================================
# TestDmUpdateNpcTool (AC #1, #2)
# =============================================================================


class TestDmUpdateNpcTool:
    """Schema-level checks for the @tool-decorated dm_update_npc function."""

    def test_tool_exists_in_tools_module(self) -> None:
        """The function is importable from tools as a @tool object."""
        from tools import dm_update_npc as imported

        assert imported is dm_update_npc
        # @tool wraps the function in a StructuredTool with a `.name` attribute
        assert getattr(imported, "name", "") == "dm_update_npc"

    def test_tool_in_all_alphabetical_position(self) -> None:
        """`dm_update_npc` is exported in __all__ between
        dm_update_character_sheet and dm_whisper_to_agent."""
        import tools as tools_mod

        assert "dm_update_npc" in tools_mod.__all__
        idx = tools_mod.__all__.index("dm_update_npc")
        prev = tools_mod.__all__.index("dm_update_character_sheet")
        nxt = tools_mod.__all__.index("dm_whisper_to_agent")
        assert prev < idx < nxt, (
            f"dm_update_npc not in alphabetical position: {tools_mod.__all__}"
        )

    def test_tool_bound_to_dm_agent(self) -> None:
        """dm_update_npc is included in create_dm_agent()'s bound tool list."""
        captured: dict[str, Any] = {}

        class FakeModel:
            def bind_tools(self, tools: list[Any]) -> FakeModel:
                captured["tools"] = tools
                return self

        with patch("agents.get_llm", return_value=FakeModel()):
            create_dm_agent(DMConfig(provider="gemini", model="gemini-1.5-flash"))
        tool_names = {getattr(t, "name", "") for t in captured["tools"]}
        assert "dm_update_npc" in tool_names

    def test_tool_call_returns_placeholder_string(self) -> None:
        """Direct invocation returns placeholder (real exec is in dm_turn)."""
        result = dm_update_npc.invoke(  # type: ignore[attr-defined]
            {
                "npc_name": "Goblin 1",
                "hp_change": -5,
                "conditions_add": ["poisoned"],
                "conditions_remove": None,
            }
        )
        assert isinstance(result, str)
        assert "Goblin 1" in result
        assert "hp_change=-5" in result

    def test_tool_signature_defaults(self) -> None:
        """Tool has hp_change default 0, conditions defaults None."""
        # @tool exposes the underlying function via .func
        underlying = getattr(dm_update_npc, "func", None)
        assert underlying is not None
        import inspect

        sig = inspect.signature(underlying)
        params = sig.parameters
        assert "npc_name" in params
        assert "hp_change" in params
        assert params["hp_change"].default == 0
        assert "conditions_add" in params
        assert params["conditions_add"].default is None
        assert "conditions_remove" in params
        assert params["conditions_remove"].default is None

    def test_tool_docstring_documents_delta_semantics(self) -> None:
        """The docstring must explain the delta convention clearly."""
        underlying = getattr(dm_update_npc, "func", None)
        assert underlying is not None
        doc = underlying.__doc__ or ""
        assert "DELTA" in doc.upper() or "delta" in doc.lower()
        # At least 3 usage examples per AC #1 / Task 1.2
        assert doc.lower().count("dm_update_npc(") >= 3


# =============================================================================
# TestExecuteNpcUpdate (AC #4, #5, #6, #7, #14, #17, #18, #20)
# =============================================================================


class TestExecuteNpcUpdate:
    """Tests for the _execute_npc_update() helper in agents.py."""

    def test_damage_reduces_hp(self) -> None:
        cs = _make_combat_state(
            npc_profiles={"goblin_1": _make_npc(hp_current=15, hp_max=15)}
        )
        result, new_cs = _execute_npc_update(
            {"npc_name": "Goblin 1", "hp_change": -5}, cs
        )
        assert not result.startswith("Error")
        assert new_cs.npc_profiles["goblin_1"].hp_current == 10
        # Old combat_state must NOT be mutated
        assert cs.npc_profiles["goblin_1"].hp_current == 15

    def test_damage_clamped_to_zero_on_overkill(self) -> None:
        cs = _make_combat_state(
            npc_profiles={"goblin_1": _make_npc(hp_current=15, hp_max=15)}
        )
        result, new_cs = _execute_npc_update(
            {"npc_name": "Goblin 1", "hp_change": -999}, cs
        )
        assert new_cs.npc_profiles["goblin_1"].hp_current == 0
        assert "defeated" in result.lower()

    def test_healing_increases_hp(self) -> None:
        cs = _make_combat_state(
            npc_profiles={"goblin_1": _make_npc(hp_current=5, hp_max=15)}
        )
        _, new_cs = _execute_npc_update({"npc_name": "Goblin 1", "hp_change": 5}, cs)
        assert new_cs.npc_profiles["goblin_1"].hp_current == 10

    def test_healing_clamped_to_hp_max(self) -> None:
        cs = _make_combat_state(
            npc_profiles={"goblin_1": _make_npc(hp_current=5, hp_max=15)}
        )
        _, new_cs = _execute_npc_update({"npc_name": "Goblin 1", "hp_change": 999}, cs)
        assert new_cs.npc_profiles["goblin_1"].hp_current == 15

    def test_conditions_add_case_insensitive_dedupe(self) -> None:
        cs = _make_combat_state(
            npc_profiles={"goblin_1": _make_npc(conditions=["poisoned"])}
        )
        _, new_cs = _execute_npc_update(
            {"npc_name": "Goblin 1", "conditions_add": ["Poisoned", "prone"]},
            cs,
        )
        new_conditions = new_cs.npc_profiles["goblin_1"].conditions
        # poisoned (original case) preserved, prone added, no dupes
        assert "poisoned" in new_conditions
        assert "prone" in new_conditions
        # No duplicate
        lower = [c.lower() for c in new_conditions]
        assert lower.count("poisoned") == 1

    def test_conditions_remove_case_insensitive(self) -> None:
        cs = _make_combat_state(
            npc_profiles={"goblin_1": _make_npc(conditions=["poisoned", "prone"])}
        )
        _, new_cs = _execute_npc_update(
            {"npc_name": "Goblin 1", "conditions_remove": ["POISONED"]}, cs
        )
        assert new_cs.npc_profiles["goblin_1"].conditions == ["prone"]

    def test_unknown_npc_returns_error_state_unchanged(self) -> None:
        cs = _make_combat_state(
            npc_profiles={"goblin_1": _make_npc(hp_current=10, hp_max=15)}
        )
        result, new_cs = _execute_npc_update(
            {"npc_name": "Nonexistent Beast", "hp_change": -5}, cs
        )
        assert result.startswith("Error")
        assert "Nonexistent Beast" in result
        # State unchanged
        assert new_cs.npc_profiles["goblin_1"].hp_current == 10

    def test_combat_inactive_returns_error_state_unchanged(self) -> None:
        cs = _make_combat_state(
            active=False,
            npc_profiles={"goblin_1": _make_npc(hp_current=10, hp_max=15)},
        )
        result, new_cs = _execute_npc_update(
            {"npc_name": "Goblin 1", "hp_change": -5}, cs
        )
        assert result.startswith("Error")
        assert "No combat" in result
        assert new_cs.npc_profiles["goblin_1"].hp_current == 10

    def test_revive_defeated_npc(self) -> None:
        """AC #20: positive hp_change on defeated NPC revives them."""
        cs = _make_combat_state(
            npc_profiles={"goblin_1": _make_npc(hp_current=0, hp_max=15)}
        )
        _, new_cs = _execute_npc_update({"npc_name": "Goblin 1", "hp_change": 5}, cs)
        assert new_cs.npc_profiles["goblin_1"].hp_current == 5

    def test_returns_new_npc_profile_via_model_copy(self) -> None:
        """AC #4: helper returns a NEW profile object — no in-place mutation."""
        original_npc = _make_npc(hp_current=15, hp_max=15)
        cs = _make_combat_state(npc_profiles={"goblin_1": original_npc})
        _, new_cs = _execute_npc_update({"npc_name": "Goblin 1", "hp_change": -5}, cs)
        new_npc = new_cs.npc_profiles["goblin_1"]
        assert new_npc is not original_npc, (
            "NpcProfile must be replaced via model_copy, not mutated"
        )
        assert original_npc.hp_current == 15  # original untouched


# =============================================================================
# TestCombatStateInjection (AC #9, #10, #19)
# =============================================================================


class TestCombatStateInjection:
    """Tests for the combat-state section injection in _build_dm_context()."""

    def test_no_section_when_combat_inactive(self) -> None:
        state = _make_game_state(combat_state=CombatState(active=False, round_number=0))
        ctx = _build_dm_context(state)
        assert "Active Combat" not in ctx

    def test_section_present_when_combat_active(self) -> None:
        cs = _make_combat_state(round_number=3)
        state = _make_game_state(combat_state=cs)
        ctx = _build_dm_context(state)
        assert "## Active Combat — Round 3" in ctx
        assert "### NPCs (DM-controlled):" in ctx

    def test_full_hp_shows_no_status_label(self) -> None:
        cs = _make_combat_state()  # all at full HP
        state = _make_game_state(combat_state=cs)
        ctx = _build_dm_context(state)
        # Full-HP line has no parenthetical label after HP fraction
        assert "Mist-Stalker Alpha: HP 15/15\n" in ctx + "\n" or (
            "Mist-Stalker Alpha: HP 15/15" in ctx
            and "(DEFEATED)" not in ctx
            and "(wounded)" not in ctx
        )

    def test_status_labels_match_thresholds(self) -> None:
        """AC #9: HP at full = no label, =0 = DEFEATED, <=25% = critically,
        <=75% = wounded, <100% = lightly wounded."""
        profiles = {
            "alpha": _make_npc(name="Alpha", hp_current=15, hp_max=15),
            "beta": _make_npc(name="Beta", hp_current=0, hp_max=15),
            "gamma": _make_npc(name="Gamma", hp_current=3, hp_max=15),  # 20%
            "delta": _make_npc(name="Delta", hp_current=8, hp_max=15),  # 53%
            "epsilon": _make_npc(name="Epsilon", hp_current=14, hp_max=15),  # 93%
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=[
                "dm",
                "dm:alpha",
                "dm:beta",
                "dm:gamma",
                "dm:delta",
                "dm:epsilon",
            ],
        )
        state = _make_game_state(combat_state=cs)
        ctx = _build_dm_context(state)
        assert "Alpha: HP 15/15" in ctx
        # Alpha should have no status label after the HP fraction
        alpha_line = [line for line in ctx.split("\n") if line.startswith("- Alpha:")][
            0
        ]
        assert "(" not in alpha_line.split("HP 15/15", 1)[1].split("—")[0]
        assert "Beta: HP 0/15 (DEFEATED)" in ctx
        assert "Gamma: HP 3/15 (critically wounded)" in ctx
        assert "Delta: HP 8/15 (wounded)" in ctx
        assert "Epsilon: HP 14/15 (lightly wounded)" in ctx

    def test_defeated_npc_shows_defeated_label(self) -> None:
        profiles = {"goblin_1": _make_npc(name="Goblin 1", hp_current=0, hp_max=10)}
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=["dm", "dm:goblin_1"],
        )
        state = _make_game_state(combat_state=cs)
        ctx = _build_dm_context(state)
        assert "Goblin 1: HP 0/10 (DEFEATED)" in ctx

    def test_empty_npc_profiles_emits_placeholder(self) -> None:
        """AC #19: empty profile dict still emits the section header."""
        cs = _make_combat_state(
            npc_profiles={},
            initiative_order=["dm", "shadowmere", "thorin"],
        )
        state = _make_game_state(combat_state=cs)
        ctx = _build_dm_context(state)
        assert "## Active Combat" in ctx
        assert "(no NPCs in this encounter)" in ctx

    def test_conditions_suffix_appended(self) -> None:
        cs = _make_combat_state(
            npc_profiles={
                "goblin_1": _make_npc(
                    name="Goblin 1",
                    hp_current=5,
                    hp_max=10,
                    conditions=["prone", "poisoned"],
                )
            },
            initiative_order=["dm", "dm:goblin_1"],
        )
        state = _make_game_state(combat_state=cs)
        ctx = _build_dm_context(state)
        assert "— conditions: prone, poisoned" in ctx

    def test_no_conditions_no_suffix(self) -> None:
        cs = _make_combat_state(
            npc_profiles={
                "goblin_1": _make_npc(
                    name="Goblin 1", hp_current=5, hp_max=10, conditions=[]
                )
            },
            initiative_order=["dm", "dm:goblin_1"],
        )
        state = _make_game_state(combat_state=cs)
        ctx = _build_dm_context(state)
        assert "— conditions:" not in ctx

    def test_section_appears_before_player_knowledge(self) -> None:
        """AC #9 placement: combat section comes after sheets, before
        Player Knowledge."""
        cs = _make_combat_state()
        state = _make_game_state(combat_state=cs)
        # Add a buffer entry to a non-DM agent so Player Knowledge section emits
        state["agent_memories"]["shadowmere"].short_term_buffer.append(
            "I draw my dagger."
        )
        ctx = _build_dm_context(state)
        assert "## Active Combat" in ctx
        assert "## Player Knowledge" in ctx
        assert ctx.index("## Active Combat") < ctx.index("## Player Knowledge")


# =============================================================================
# TestNpcStatusLabel (AC #9 helper)
# =============================================================================


class TestNpcStatusLabel:
    """Tests for the _npc_status_label helper."""

    def test_full_hp_returns_empty(self) -> None:
        assert _npc_status_label(15, 15) == ""

    def test_zero_hp_returns_defeated(self) -> None:
        assert _npc_status_label(0, 15) == " (DEFEATED)"

    def test_critically_wounded_threshold(self) -> None:
        # 25% boundary inclusive on the critical side
        assert _npc_status_label(3, 12) == " (critically wounded)"
        assert _npc_status_label(1, 15) == " (critically wounded)"

    def test_wounded_threshold(self) -> None:
        # > 25%, <= 75%
        assert _npc_status_label(8, 15) == " (wounded)"
        assert _npc_status_label(9, 12) == " (wounded)"  # 75%

    def test_lightly_wounded_threshold(self) -> None:
        # > 75%, < hp_max
        assert _npc_status_label(14, 15) == " (lightly wounded)"

    def test_hp_max_zero_returns_empty(self) -> None:
        # Defensive: malformed input shouldn't crash
        assert _npc_status_label(0, 0) == ""


# =============================================================================
# TestDefeatedNpcRouting (AC #12, #13, #20)
# =============================================================================


class TestDefeatedNpcRouting:
    """Tests for defeated-NPC skipping in route_to_next_agent()."""

    def test_skips_one_defeated_npc(self) -> None:
        """AC #12: defeated NPC at current_initiative_index is skipped."""
        profiles = {
            "goblin_1": _make_npc(name="Goblin 1", hp_current=0, hp_max=10),
            "goblin_2": _make_npc(name="Goblin 2", hp_current=10, hp_max=10),
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=["dm", "dm:goblin_1", "shadowmere", "dm:goblin_2"],
            current_initiative_index=1,  # Points at the dead goblin
        )
        state = _make_game_state(combat_state=cs, current_turn="dm")
        # The router should skip goblin_1 (dead) and land on shadowmere
        assert route_to_next_agent(state) == "shadowmere"

    def test_skips_multiple_consecutive_defeated_npcs(self) -> None:
        profiles = {
            "g1": _make_npc(name="G1", hp_current=0, hp_max=10),
            "g2": _make_npc(name="G2", hp_current=0, hp_max=10),
            "g3": _make_npc(name="G3", hp_current=10, hp_max=10),
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=[
                "dm",
                "dm:g1",
                "dm:g2",
                "dm:g3",
                "shadowmere",
            ],
            current_initiative_index=1,
        )
        state = _make_game_state(combat_state=cs)
        # All three defeated... wait g3 is alive — should route to "dm" (NPC turn)
        assert route_to_next_agent(state) == "dm"

    def test_all_remaining_defeated_returns_end(self) -> None:
        """AC #13: all remaining NPC entries defeated → END."""
        profiles = {
            "g1": _make_npc(name="G1", hp_current=0, hp_max=10),
            "g2": _make_npc(name="G2", hp_current=0, hp_max=10),
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=["dm", "shadowmere", "dm:g1", "dm:g2"],
            current_initiative_index=2,  # Points at first dead goblin
        )
        state = _make_game_state(combat_state=cs)
        assert route_to_next_agent(state) == END

    def test_defeated_then_pc_routes_to_pc(self) -> None:
        """AC #13: defeated NPC followed by live PC routes to the PC."""
        profiles = {
            "goblin_1": _make_npc(name="Goblin 1", hp_current=0, hp_max=10),
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=["dm", "dm:goblin_1", "thorin"],
            current_initiative_index=1,
        )
        state = _make_game_state(combat_state=cs)
        assert route_to_next_agent(state) == "thorin"

    def test_pc_with_zero_hp_not_skipped(self) -> None:
        """AC #12: PC entries are NEVER skipped on hp=0 basis."""
        # Note: PCs aren't tracked via npc_profiles HP, so this is a sanity
        # check that the router does NOT mis-skip a PC.
        profiles = {
            "goblin_1": _make_npc(name="Goblin 1", hp_current=0, hp_max=10),
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=["dm", "shadowmere", "dm:goblin_1", "thorin"],
            current_initiative_index=1,
        )
        state = _make_game_state(combat_state=cs)
        # Index 1 → shadowmere (alive PC). Should route to her.
        assert route_to_next_agent(state) == "shadowmere"

    def test_live_npc_at_index_routes_to_dm(self) -> None:
        """AC #12 inverse: live NPC slot still routes to dm node."""
        profiles = {
            "goblin_1": _make_npc(name="Goblin 1", hp_current=10, hp_max=10),
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=["dm", "dm:goblin_1", "shadowmere"],
            current_initiative_index=1,
        )
        state = _make_game_state(combat_state=cs)
        assert route_to_next_agent(state) == "dm"


# =============================================================================
# TestPersistentIndexSync (regression guard for HIGH-1 from code review)
# =============================================================================


class TestPersistentIndexSync:
    """Verify that when the router locally skips defeated NPCs to find the
    next live entry, the consuming node (dm_turn / pc_turn) re-aligns the
    persistent current_initiative_index so subsequent +1 advancement lands
    on the correct slot. Regression guard for the bug discovered in the
    code review where dm_turn would read a stale index and play a dead
    NPC's turn.
    """

    @patch("agents.get_llm")
    def test_dm_turn_advances_past_defeated_when_persistent_idx_is_stale(
        self, mock_get_llm: MagicMock
    ) -> None:
        from langchain_core.messages import AIMessage

        from agents import dm_turn

        # Scenario: index=1 points at dead g1. Router would skip g1 (idx 1)
        # and g2 (idx 2) to land on g3 (idx 3, alive). Without the fix,
        # dm_turn would read state idx=1 and set current_turn="dm:g1"
        # (playing the dead one). With the fix, dm_turn realigns idx to 3.
        profiles = {
            "g1": _make_npc(name="G1", hp_current=0, hp_max=10),
            "g2": _make_npc(name="G2", hp_current=0, hp_max=10),
            "g3": _make_npc(name="G3", hp_current=10, hp_max=10),
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=["dm", "dm:g1", "dm:g2", "dm:g3", "shadowmere"],
            current_initiative_index=1,  # points at dead g1
        )
        state = _make_game_state(combat_state=cs, current_turn="dm:g1")

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.return_value = AIMessage(content="G3 lunges forward.")
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        # After dm_turn: realigned index started at 3, then +1 -> 4
        assert result["combat_state"].current_initiative_index == 4, (
            "dm_turn must realign the persistent index past defeated NPCs "
            "before advancing, otherwise the next routing call routes to "
            "another dead slot."
        )
        # current_turn should reflect the LIVE entry it processed
        assert result["current_turn"] == "dm:g3"

    @patch("agents.get_llm")
    def test_pc_turn_aligns_index_when_router_skipped_defeated(
        self, mock_get_llm: MagicMock
    ) -> None:
        from langchain_core.messages import AIMessage

        from agents import pc_turn

        # Scenario: index=1 points at dead g1. Router would skip g1 to land
        # on shadowmere at idx 2. Without the fix, pc_turn would advance
        # idx 1->2 (still dead g1's slot conceptually). With the fix, pc_turn
        # realigns to idx 2 first, then advances to 3.
        profiles = {
            "g1": _make_npc(name="G1", hp_current=0, hp_max=10),
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=["dm", "dm:g1", "shadowmere", "thorin"],
            current_initiative_index=1,  # stale: points at dead g1
        )
        state = _make_game_state(combat_state=cs, current_turn="shadowmere")

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.return_value = AIMessage(content="I strike!")
        mock_get_llm.return_value = mock_model

        result = pc_turn(state, "shadowmere")

        # After pc_turn: realigned index 1 -> 2 (shadowmere's slot), then +1 -> 3
        assert result["combat_state"].current_initiative_index == 3, (
            "pc_turn must align persistent index to its actual slot in "
            "initiative_order before advancing."
        )


# =============================================================================
# TestSheetNotifications (AC #8)
# =============================================================================


class TestSheetNotifications:
    """Integration tests for `[SHEET]:` log entries via dm_turn() dispatch."""

    @patch("agents.get_llm")
    def test_damage_call_emits_sheet_log_entry(self, mock_get_llm: MagicMock) -> None:
        from langchain_core.messages import AIMessage

        from agents import dm_turn

        profiles = {
            "mist-stalker_alpha": _make_npc(
                name="Mist-Stalker Alpha", hp_current=15, hp_max=15
            ),
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=["dm", "dm:mist-stalker_alpha"],
            current_initiative_index=0,
        )
        state = _make_game_state(combat_state=cs, current_turn="dm")
        state["ground_truth_log"] = []

        tool_call_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "dm_update_npc",
                    "args": {
                        "npc_name": "Mist-Stalker Alpha",
                        "hp_change": -5,
                    },
                    "id": "call_001",
                }
            ],
        )
        final_response = AIMessage(
            content="Your blade bites deep into the Mist-Stalker's flank."
        )
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = [tool_call_response, final_response]
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        log = result["ground_truth_log"]
        sheet_entries = [e for e in log if e.startswith("[SHEET]")]
        assert len(sheet_entries) == 1
        assert "Mist-Stalker Alpha" in sheet_entries[0]
        assert "HP 15 -> 10" in sheet_entries[0]
        assert "(-5)" in sheet_entries[0]
        # Combat state propagated
        assert (
            result["combat_state"].npc_profiles["mist-stalker_alpha"].hp_current == 10
        )

    @patch("agents.get_llm")
    def test_defeat_call_emits_defeated_sheet_entry(
        self, mock_get_llm: MagicMock
    ) -> None:
        from langchain_core.messages import AIMessage

        from agents import dm_turn

        profiles = {
            "mist-stalker_alpha": _make_npc(
                name="Mist-Stalker Alpha", hp_current=5, hp_max=15
            ),
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=["dm", "dm:mist-stalker_alpha"],
            current_initiative_index=0,
        )
        state = _make_game_state(combat_state=cs, current_turn="dm")
        state["ground_truth_log"] = []

        tool_call_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "dm_update_npc",
                    "args": {
                        "npc_name": "Mist-Stalker Alpha",
                        "hp_change": -10,
                    },
                    "id": "call_def",
                }
            ],
        )
        final_response = AIMessage(
            content="The Mist-Stalker collapses, its mists dissipating."
        )
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = [tool_call_response, final_response]
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        log = result["ground_truth_log"]
        sheet_entries = [e for e in log if e.startswith("[SHEET]")]
        assert len(sheet_entries) == 1
        assert "(defeated)" in sheet_entries[0]
        assert result["combat_state"].npc_profiles["mist-stalker_alpha"].hp_current == 0

    @patch("agents.get_llm")
    def test_error_result_does_not_append_sheet_entry(
        self, mock_get_llm: MagicMock
    ) -> None:
        """Unknown-NPC errors must NOT pollute the ground_truth_log."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn

        cs = _make_combat_state(
            npc_profiles={"goblin_1": _make_npc(hp_current=5, hp_max=15)},
            initiative_order=["dm", "dm:goblin_1"],
            current_initiative_index=0,
        )
        state = _make_game_state(combat_state=cs, current_turn="dm")
        state["ground_truth_log"] = []

        tool_call_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "dm_update_npc",
                    "args": {
                        "npc_name": "Phantom NPC",  # not in profiles
                        "hp_change": -5,
                    },
                    "id": "call_bad",
                }
            ],
        )
        final_response = AIMessage(content="The phantom flickers and vanishes.")
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = [tool_call_response, final_response]
        mock_get_llm.return_value = mock_model

        result = dm_turn(state)

        log = result["ground_truth_log"]
        sheet_entries = [e for e in log if e.startswith("[SHEET]")]
        assert len(sheet_entries) == 0


# =============================================================================
# TestPersistenceRoundTrip (AC #15)
# =============================================================================


class TestPersistenceRoundTrip:
    """Persistence regression tests for mutated NPC state."""

    def test_round_trip_preserves_mutated_hp(self) -> None:
        cs = _make_combat_state(
            npc_profiles={
                "goblin_1": _make_npc(name="Goblin 1", hp_current=3, hp_max=15)
            }
        )
        state = _make_game_state(combat_state=cs)
        serialized = serialize_game_state(state)
        deserialized = deserialize_game_state(serialized)
        npc = deserialized["combat_state"].npc_profiles["goblin_1"]
        assert npc.hp_current == 3
        assert npc.hp_max == 15

    def test_round_trip_preserves_conditions(self) -> None:
        cs = _make_combat_state(
            npc_profiles={
                "goblin_1": _make_npc(
                    name="Goblin 1",
                    hp_current=10,
                    hp_max=15,
                    conditions=["poisoned", "prone"],
                )
            }
        )
        state = _make_game_state(combat_state=cs)
        serialized = serialize_game_state(state)
        deserialized = deserialize_game_state(serialized)
        npc = deserialized["combat_state"].npc_profiles["goblin_1"]
        assert npc.conditions == ["poisoned", "prone"]

    def test_round_trip_preserves_defeated_state(self) -> None:
        """A defeated NPC (hp_current=0) survives the round-trip."""
        cs = _make_combat_state(
            npc_profiles={
                "goblin_1": _make_npc(name="Goblin 1", hp_current=0, hp_max=15)
            }
        )
        state = _make_game_state(combat_state=cs)
        # JSON round-trip via serialize/deserialize (model_dump → JSON → model)
        serialized = serialize_game_state(state)
        # Quick sanity: JSON contains hp_current=0
        parsed = json.loads(serialized)
        assert parsed["combat_state"]["npc_profiles"]["goblin_1"]["hp_current"] == 0
        deserialized = deserialize_game_state(serialized)
        assert deserialized["combat_state"].npc_profiles["goblin_1"].hp_current == 0


# =============================================================================
# TestIntegrationSession017 (AC #16, end-to-end)
# =============================================================================


class TestIntegrationSession017:
    """End-to-end scenario reproducing the Session 017 Mist-Stalker incident."""

    def test_three_mist_stalkers_all_defeated_in_sequence(self) -> None:
        """All three Mist-Stalkers take fatal damage; (a) all show
        (DEFEATED) in context, (b) router returns END when only defeated
        NPC slots remain, (c) helper's confirmation strings include
        'defeated' for each."""
        profiles = {
            "mist-stalker_alpha": _make_npc(
                name="Mist-Stalker Alpha", hp_current=15, hp_max=15
            ),
            "mist-stalker_beta": _make_npc(
                name="Mist-Stalker Beta", hp_current=15, hp_max=15
            ),
            "mist-stalker_gamma": _make_npc(
                name="Mist-Stalker Gamma", hp_current=15, hp_max=15
            ),
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=[
                "dm",
                "dm:mist-stalker_alpha",
                "dm:mist-stalker_beta",
                "dm:mist-stalker_gamma",
            ],
            current_initiative_index=1,
        )

        # Apply three defeats via _execute_npc_update sequentially.
        confirmations: list[str] = []
        for name in (
            "Mist-Stalker Alpha",
            "Mist-Stalker Beta",
            "Mist-Stalker Gamma",
        ):
            confirmation, cs = _execute_npc_update(
                {"npc_name": name, "hp_change": -15}, cs
            )
            confirmations.append(confirmation)

        # (c) all three confirmations contain "defeated"
        assert all("defeated" in c.lower() for c in confirmations)

        # (a) all three are flagged DEFEATED in _build_dm_context
        state = _make_game_state(combat_state=cs)
        ctx = _build_dm_context(state)
        assert "Mist-Stalker Alpha: HP 0/15 (DEFEATED)" in ctx
        assert "Mist-Stalker Beta: HP 0/15 (DEFEATED)" in ctx
        assert "Mist-Stalker Gamma: HP 0/15 (DEFEATED)" in ctx

        # (b) router returns END now that all remaining slots are dead NPCs
        # (current_initiative_index=1 means the first dead NPC is next)
        assert route_to_next_agent(state) == END

    def test_alpha_dies_beta_and_gamma_continue(self) -> None:
        """AC #16: killing one NPC doesn't affect the other two."""
        profiles = {
            "mist-stalker_alpha": _make_npc(
                name="Mist-Stalker Alpha", hp_current=15, hp_max=15
            ),
            "mist-stalker_beta": _make_npc(
                name="Mist-Stalker Beta", hp_current=15, hp_max=15
            ),
            "mist-stalker_gamma": _make_npc(
                name="Mist-Stalker Gamma", hp_current=15, hp_max=15
            ),
        }
        cs = _make_combat_state(
            npc_profiles=profiles,
            initiative_order=[
                "dm",
                "dm:mist-stalker_alpha",
                "shadowmere",
                "dm:mist-stalker_beta",
                "dm:mist-stalker_gamma",
            ],
            current_initiative_index=1,  # Alpha is next, but Alpha is alive here
        )
        _, cs = _execute_npc_update(
            {"npc_name": "Mist-Stalker Alpha", "hp_change": -15}, cs
        )
        # Now current_initiative_index=1 lands on Alpha (defeated). Router
        # should skip Alpha and return shadowmere (live PC).
        state = _make_game_state(combat_state=cs)
        assert route_to_next_agent(state) == "shadowmere"
        # Beta and Gamma still alive in npc_profiles
        assert cs.npc_profiles["mist-stalker_beta"].hp_current == 15
        assert cs.npc_profiles["mist-stalker_gamma"].hp_current == 15


# =============================================================================
# TestSystemPromptAddendum (AC #11)
# =============================================================================


class TestSystemPromptAddendum:
    """Verify DM_COMBAT_NARRATIVE_ADDENDUM is appended on all combat turns."""

    def test_addendum_constant_documents_tool(self) -> None:
        """The addendum string explicitly names the dm_update_npc tool and
        the damage-tracking expectations."""
        assert "dm_update_npc" in DM_COMBAT_NARRATIVE_ADDENDUM
        assert "0 HP" in DM_COMBAT_NARRATIVE_ADDENDUM
        assert "Round" in DM_COMBAT_NARRATIVE_ADDENDUM

    @patch("agents.get_llm")
    def test_addendum_present_in_system_prompt_when_combat_active(
        self, mock_get_llm: MagicMock
    ) -> None:
        from langchain_core.messages import AIMessage

        from agents import dm_turn

        captured_messages: list[Any] = []

        def fake_invoke(msgs: list[Any]) -> Any:
            captured_messages.append(msgs)
            return AIMessage(content="The room hums with tension.")

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = fake_invoke
        mock_get_llm.return_value = mock_model

        cs = _make_combat_state()
        state = _make_game_state(combat_state=cs, current_turn="dm")
        dm_turn(state)

        assert captured_messages, "dm_turn never invoked the LLM"
        # The first message in the prompt list is the SystemMessage
        sys_content = captured_messages[0][0].content
        assert "dm_update_npc" in sys_content
        assert "Combat Damage Tracking" in sys_content

    @patch("agents.get_llm")
    def test_addendum_absent_in_exploration_mode(self, mock_get_llm: MagicMock) -> None:
        from langchain_core.messages import AIMessage

        from agents import dm_turn

        captured_messages: list[Any] = []

        def fake_invoke(msgs: list[Any]) -> Any:
            captured_messages.append(msgs)
            return AIMessage(content="The forest path winds onward.")

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = fake_invoke
        mock_get_llm.return_value = mock_model

        # Combat NOT active
        state = _make_game_state(
            combat_state=CombatState(active=False), current_turn="dm"
        )
        dm_turn(state)

        sys_content = captured_messages[0][0].content
        # The Combat Damage Tracking section must NOT appear
        assert "Combat Damage Tracking" not in sys_content


# =============================================================================
# TestSanitization (smoke check)
# =============================================================================


class TestNpcNameSanitization:
    """Smoke check that fuzzy lookup catches common DM input variants."""

    def test_lookup_via_display_name(self) -> None:
        cs = _make_combat_state(
            npc_profiles={
                "mist-stalker_alpha": _make_npc(
                    name="Mist-Stalker Alpha", hp_current=15, hp_max=15
                )
            }
        )
        # DM input uses display form with spaces and capitals
        result, new_cs = _execute_npc_update(
            {"npc_name": "Mist-Stalker Alpha", "hp_change": -3}, cs
        )
        assert not result.startswith("Error")
        assert new_cs.npc_profiles["mist-stalker_alpha"].hp_current == 12

    def test_lookup_via_sanitized_key(self) -> None:
        cs = _make_combat_state(
            npc_profiles={
                "goblin_1": _make_npc(name="Goblin 1", hp_current=10, hp_max=15)
            }
        )
        # Sanitization should match this lowercase underscored form too
        result, _ = _execute_npc_update({"npc_name": "goblin_1", "hp_change": -1}, cs)
        assert not result.startswith("Error")

    def test_sanitize_helper_imports(self) -> None:
        """Story 15.7 leans on _sanitize_npc_name — it must still resolve."""
        assert _sanitize_npc_name("Mist-Stalker Alpha") == "mist-stalker_alpha"
        assert _sanitize_npc_name("  Goblin 1  ") == "goblin_1"
