"""Tests for Story 15.8: Auto-Detect Encounter Resolution.

Covers the all-NPCs-defeated nudge in `context_manager()`, the
`DM_COMBAT_ALL_DEFEATED_ADDENDUM` prompt addition, the 3-round force-end
fallback, the revival edge case (AC #9), persistence backward compatibility
for the new `defeat_nudge_emitted` and `defeat_nudge_round` fields, and
auto-reset of those fields by `_execute_end_combat()`.

17 tests across 8 classes — exceeds AC #11 minimum of 10.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from agents import (
    DM_COMBAT_ALL_DEFEATED_ADDENDUM,
    DM_COMBAT_NARRATIVE_ADDENDUM,
    _execute_end_combat,
)
from graph import context_manager
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

# =============================================================================
# Fixtures / Helpers
# =============================================================================


def _make_npc(
    name: str = "Mist-Stalker Alpha",
    hp_current: int = 0,
    hp_max: int = 15,
) -> NpcProfile:
    """Create an NPC fixture (defaults to defeated for AC #1 scenarios)."""
    return NpcProfile(
        name=name,
        initiative_modifier=2,
        hp_max=hp_max,
        hp_current=hp_current,
        ac=13,
        personality="Aggressive",
        tactics="Charges nearest enemy",
    )


def _make_combat_state(
    active: bool = True,
    round_number: int = 3,
    defeat_nudge_emitted: bool = False,
    defeat_nudge_round: int = 0,
    npc_profiles: dict[str, NpcProfile] | None = None,
    original_turn_queue: list[str] | None = None,
) -> CombatState:
    """Build a CombatState fixture mirroring the Session 017 incident
    (3 Mist-Stalkers vs the party).

    Defaults to ALL THREE Mist-Stalkers at hp_current=0 to exercise the
    happy-path defeat-detection.
    """
    if npc_profiles is None:
        npc_profiles = {
            "mist-stalker_alpha": _make_npc(name="Mist-Stalker Alpha"),
            "mist-stalker_beta": _make_npc(name="Mist-Stalker Beta"),
            "mist-stalker_gamma": _make_npc(name="Mist-Stalker Gamma"),
        }
    if original_turn_queue is None:
        original_turn_queue = ["dm", "shadowmere", "thorin", "gandalf"]
    return CombatState(
        active=active,
        round_number=round_number,
        initiative_order=[
            "dm",
            "shadowmere",
            "dm:mist-stalker_alpha",
            "thorin",
            "dm:mist-stalker_beta",
            "gandalf",
            "dm:mist-stalker_gamma",
        ],
        initiative_rolls={
            "shadowmere": 17,
            "dm:mist-stalker_alpha": 15,
            "thorin": 14,
            "dm:mist-stalker_beta": 12,
            "gandalf": 10,
            "dm:mist-stalker_gamma": 8,
        },
        original_turn_queue=original_turn_queue,
        npc_profiles=npc_profiles,
        defeat_nudge_emitted=defeat_nudge_emitted,
        defeat_nudge_round=defeat_nudge_round,
    )


def _make_game_state(
    current_turn: str = "dm",
    combat_state: CombatState | None = None,
    turn_queue: list[str] | None = None,
    game_config: GameConfig | None = None,
    ground_truth_log: list[str] | None = None,
) -> GameState:
    """Build a minimal GameState for Story 15.8 testing."""
    if combat_state is None:
        combat_state = CombatState()
    if turn_queue is None:
        turn_queue = ["dm", "shadowmere", "thorin", "gandalf"]
    if game_config is None:
        game_config = GameConfig(
            combat_mode="Tactical",  # type: ignore[arg-type]
            summarizer_model="gemini-1.5-flash",
            party_size=3,
            # Bump max_combat_rounds high enough that 15-6 force-end never
            # interferes with 15-8-specific assertions in this suite.
            max_combat_rounds=999,
        )
    if ground_truth_log is None:
        ground_truth_log = ["[DM]: The adventure begins."]

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
        ground_truth_log=ground_truth_log,
        turn_queue=turn_queue,
        current_turn=current_turn,
        agent_memories=agent_memories,
        game_config=game_config,
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
        character_sheets={},
        agent_secrets={"dm": AgentSecrets()},
        narrative_elements={},
        callback_database=NarrativeElementStore(),
        callback_log=CallbackLog(),
        active_fork_id=None,
        combat_state=combat_state,
    )


# =============================================================================
# TestCombatStateNudgeFields (AC #1, #2, #7, #8)
# =============================================================================


class TestCombatStateNudgeFields:
    """Pydantic-level checks on the new `defeat_nudge_*` fields."""

    def test_defaults_are_safe(self) -> None:
        """Fresh CombatState() has nudge fields at safe defaults."""
        cs = CombatState()
        assert cs.defeat_nudge_emitted is False
        assert cs.defeat_nudge_round == 0

    def test_construct_with_explicit_values(self) -> None:
        """CombatState accepts True/positive int for the two new fields."""
        cs = CombatState(defeat_nudge_emitted=True, defeat_nudge_round=5)
        assert cs.defeat_nudge_emitted is True
        assert cs.defeat_nudge_round == 5

    def test_negative_round_rejected(self) -> None:
        """defeat_nudge_round=-1 raises ValidationError (ge=0)."""
        with pytest.raises(ValidationError):
            CombatState(defeat_nudge_round=-1)


# =============================================================================
# TestDefeatDetection (AC #1, #4, #5)
# =============================================================================


class TestDefeatDetection:
    """`context_manager()` happy-path defeat detection."""

    def test_all_npcs_defeated_emits_nudge(self) -> None:
        """All NPCs at 0 HP + active combat -> [System] line + flag set."""
        cs = _make_combat_state(round_number=3)
        state = _make_game_state(combat_state=cs)

        result = context_manager(state)

        log = result["ground_truth_log"]
        assert any(
            "[System]:" in entry and "All hostile combatants are defeated" in entry
            for entry in log
        )
        new_cs = result["combat_state"]
        assert isinstance(new_cs, CombatState)
        assert new_cs.defeat_nudge_emitted is True
        # round_number was incremented from 3 -> 4 by the existing
        # round-tracking block; the nudge is emitted in round 4.
        assert new_cs.round_number == 4
        assert new_cs.defeat_nudge_round == 4

    def test_inactive_combat_skips_detection(self) -> None:
        """combat.active=False -> no log entry, no flag mutation (AC #5)."""
        cs = _make_combat_state(active=False, round_number=3)
        state = _make_game_state(combat_state=cs)

        result = context_manager(state)

        log = result["ground_truth_log"]
        assert not any(
            "[System]: All hostile combatants are defeated" in e for e in log
        )
        new_cs = result["combat_state"]
        assert isinstance(new_cs, CombatState)
        assert new_cs.defeat_nudge_emitted is False
        assert new_cs.defeat_nudge_round == 0

    def test_empty_npc_dict_skips_detection(self) -> None:
        """combat.npc_profiles={} skips detection (AC #4)."""
        cs = _make_combat_state(round_number=3, npc_profiles={})
        state = _make_game_state(combat_state=cs)

        result = context_manager(state)

        log = result["ground_truth_log"]
        assert not any(
            "[System]: All hostile combatants are defeated" in e for e in log
        )
        new_cs = result["combat_state"]
        assert isinstance(new_cs, CombatState)
        assert new_cs.defeat_nudge_emitted is False


# =============================================================================
# TestNudgeIdempotency (AC #2)
# =============================================================================


class TestNudgeIdempotency:
    """Verify the nudge is emitted at most once per encounter."""

    def test_two_consecutive_calls_emit_only_once(self) -> None:
        """Second context_manager() call with all-defeated state appends
        no additional [System] line and does not reset defeat_nudge_round."""
        # Start with the nudge already pre-flagged at round 3 to isolate
        # idempotency from the nudge-emission round-mismatch.
        cs = _make_combat_state(
            round_number=3,
            defeat_nudge_emitted=True,
            defeat_nudge_round=3,
        )
        state = _make_game_state(combat_state=cs)

        # First call: round_number bumps 3->4, nudge already emitted, no
        # new [System] line should appear.
        result1 = context_manager(state)
        log_after_first = list(result1["ground_truth_log"])
        nudge_count_1 = sum(
            1
            for e in log_after_first
            if "[System]: All hostile combatants are defeated" in e
        )
        assert nudge_count_1 == 0, "Pre-flagged nudge should not re-emit"

        # Second call (carry the new state forward): still all-defeated,
        # still flagged, must remain idempotent.
        next_state = {**state, **result1}  # carry forward mutations
        result2 = context_manager(next_state)
        log_after_second = list(result2["ground_truth_log"])
        nudge_count_2 = sum(
            1
            for e in log_after_second
            if "[System]: All hostile combatants are defeated" in e
        )
        assert nudge_count_2 == 0
        # defeat_nudge_round should NOT have been overwritten
        assert result2["combat_state"].defeat_nudge_round == 3

    def test_mixed_hp_does_not_fire_nudge(self) -> None:
        """At least one NPC alive -> no nudge regardless of repeated calls."""
        cs = _make_combat_state(
            round_number=3,
            npc_profiles={
                "mist-stalker_alpha": _make_npc(
                    name="Mist-Stalker Alpha", hp_current=0
                ),
                "mist-stalker_beta": _make_npc(
                    name="Mist-Stalker Beta",
                    hp_current=5,  # alive
                ),
                "mist-stalker_gamma": _make_npc(
                    name="Mist-Stalker Gamma", hp_current=0
                ),
            },
        )
        state = _make_game_state(combat_state=cs)

        result = context_manager(state)
        next_state = {**state, **result}
        result2 = context_manager(next_state)

        for r in (result, result2):
            log = r["ground_truth_log"]
            assert not any(
                "[System]: All hostile combatants are defeated" in e for e in log
            )
            assert r["combat_state"].defeat_nudge_emitted is False


# =============================================================================
# TestDmAddendumOnDefeat (AC #3)
# =============================================================================


class TestDmAddendumOnDefeat:
    """Verify DM_COMBAT_ALL_DEFEATED_ADDENDUM injection in dm_turn()."""

    @patch("agents.get_llm")
    def test_addendum_present_when_nudge_emitted(self, mock_get_llm: MagicMock) -> None:
        """defeat_nudge_emitted=True -> addendum appears in SystemMessage."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn

        captured_messages: list[Any] = []

        def fake_invoke(msgs: list[Any]) -> Any:
            captured_messages.append(msgs)
            return AIMessage(content="The Mist-Stalkers lie still.")

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = fake_invoke
        mock_get_llm.return_value = mock_model

        cs = _make_combat_state(
            round_number=4,
            defeat_nudge_emitted=True,
            defeat_nudge_round=4,
        )
        state = _make_game_state(combat_state=cs, current_turn="dm")
        dm_turn(state)

        assert captured_messages, "dm_turn never invoked the LLM"
        sys_content = captured_messages[0][0].content
        # Both the standard combat addendum AND the new all-defeated
        # addendum should be present (layered, not replaced).
        assert "Combat Damage Tracking" in sys_content
        assert "Encounter Resolution" in sys_content
        assert "dm_end_combat" in sys_content

    @patch("agents.get_llm")
    def test_addendum_absent_when_nudge_not_emitted(
        self, mock_get_llm: MagicMock
    ) -> None:
        """defeat_nudge_emitted=False -> only standard addendum present."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn

        captured_messages: list[Any] = []

        def fake_invoke(msgs: list[Any]) -> Any:
            captured_messages.append(msgs)
            return AIMessage(content="The fight rages on.")

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = fake_invoke
        mock_get_llm.return_value = mock_model

        # Combat active, NPCs still alive, nudge not emitted.
        cs = _make_combat_state(
            round_number=2,
            defeat_nudge_emitted=False,
            npc_profiles={
                "mist-stalker_alpha": _make_npc(hp_current=10),
                "mist-stalker_beta": _make_npc(name="Mist-Stalker Beta", hp_current=8),
            },
        )
        state = _make_game_state(combat_state=cs, current_turn="dm")
        dm_turn(state)

        sys_content = captured_messages[0][0].content
        # Standard addendum still applies on every combat turn.
        assert "Combat Damage Tracking" in sys_content
        # All-defeated addendum must NOT appear yet.
        assert "Encounter Resolution" not in sys_content


# =============================================================================
# TestForceEndFallback (AC #6, #10)
# =============================================================================


class TestForceEndFallback:
    """Force-end fallback after DM ignores the nudge for ≥3 more rounds."""

    def test_force_ends_after_three_rounds_of_inaction(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """All NPCs defeated, nudge at round 5, current round 8 -> force-end.

        round_number 7 will be incremented by the round-tracking block to 8;
        delta 8 - 5 = 3 -> >= 3 triggers force-end.
        """
        cs = _make_combat_state(
            round_number=7,
            defeat_nudge_emitted=True,
            defeat_nudge_round=5,
        )
        original_queue = ["dm", "shadowmere", "thorin", "gandalf"]
        state = _make_game_state(
            combat_state=cs,
            turn_queue=["fighter_in_combat_only"],
            ground_truth_log=["[DM]: Battle endures."],
        )
        # Override original_turn_queue so we can verify it gets restored.
        state["combat_state"] = cs.model_copy(
            update={"original_turn_queue": original_queue}
        )

        with caplog.at_level(logging.WARNING, logger="autodungeon"):
            result = context_manager(state)

        new_cs = result["combat_state"]
        assert isinstance(new_cs, CombatState)
        assert new_cs.active is False
        assert new_cs == CombatState()  # full reset
        assert result["turn_queue"] == original_queue
        assert any(
            "[System]: Combat force-ended after DM failed to call dm_end_combat" in e
            for e in result["ground_truth_log"]
        )
        # Warning emitted with rounds-since-nudge in the message string
        assert any(
            "force-ended via auto-end fallback" in record.message
            for record in caplog.records
        )

    def test_does_not_force_end_within_grace_window(self) -> None:
        """delta=2 (round 7 vs nudge_round 5) -> NO force-end yet."""
        # Pre-increment: round_number=6, after bump becomes 7. 7 - 5 = 2 < 3.
        cs = _make_combat_state(
            round_number=6,
            defeat_nudge_emitted=True,
            defeat_nudge_round=5,
        )
        state = _make_game_state(combat_state=cs)

        result = context_manager(state)

        new_cs = result["combat_state"]
        assert isinstance(new_cs, CombatState)
        # Combat must remain active — grace window has not elapsed.
        assert new_cs.active is True
        assert new_cs.defeat_nudge_emitted is True
        # No force-end log line.
        assert not any(
            "force-ended after DM failed" in e for e in result["ground_truth_log"]
        )

    def test_force_end_independent_of_max_rounds(self) -> None:
        """AC #10: 15-8 force-end fires independently of 15-6 max_rounds.

        Set max_combat_rounds high (no 15-6 trigger) — confirm 15-8 still
        force-ends combat purely on nudge-grace expiration.
        """
        cs = _make_combat_state(
            round_number=10,
            defeat_nudge_emitted=True,
            defeat_nudge_round=5,
        )
        # max_combat_rounds=999 -> 15-6 max-rounds CANNOT fire at round 11.
        config = GameConfig(
            combat_mode="Tactical",  # type: ignore[arg-type]
            summarizer_model="gemini-1.5-flash",
            party_size=3,
            max_combat_rounds=999,
        )
        state = _make_game_state(combat_state=cs, game_config=config)

        result = context_manager(state)

        new_cs = result["combat_state"]
        assert isinstance(new_cs, CombatState)
        assert new_cs.active is False
        # The system log should contain the 15-8 message, NOT the 15-6 one.
        log = result["ground_truth_log"]
        assert any(
            "Combat force-ended after DM failed to call dm_end_combat" in e for e in log
        )
        assert not any(
            "Combat ended after reaching the maximum round limit" in e for e in log
        )


# =============================================================================
# TestRevivalResetsNudge (AC #9)
# =============================================================================


class TestRevivalResetsNudge:
    """Edge case: NPC revived (hp_current > 0) -> nudge flags clear."""

    def test_revived_npc_clears_nudge_flag_and_round(self) -> None:
        """defeat_nudge_emitted=True, then one NPC has hp_current=5 ->
        context_manager() resets defeat_nudge_emitted=False AND
        defeat_nudge_round=0 (so a future re-defeat re-fires the nudge)."""
        # Start with nudge already flagged at round 4
        cs = _make_combat_state(
            round_number=4,
            defeat_nudge_emitted=True,
            defeat_nudge_round=4,
            npc_profiles={
                "mist-stalker_alpha": _make_npc(hp_current=5),  # REVIVED
                "mist-stalker_beta": _make_npc(name="Mist-Stalker Beta", hp_current=0),
                "mist-stalker_gamma": _make_npc(
                    name="Mist-Stalker Gamma", hp_current=0
                ),
            },
        )
        state = _make_game_state(combat_state=cs)

        result = context_manager(state)

        new_cs = result["combat_state"]
        assert isinstance(new_cs, CombatState)
        assert new_cs.defeat_nudge_emitted is False
        assert new_cs.defeat_nudge_round == 0
        # Combat itself is still active — only the nudge flag cleared.
        assert new_cs.active is True


# =============================================================================
# TestPersistenceBackwardCompat (AC #8)
# =============================================================================


class TestPersistenceBackwardCompat:
    """Round-trip new fields and back-fill defaults for legacy checkpoints."""

    def test_round_trip_preserves_nudge_fields(self) -> None:
        """serialize -> deserialize round-trip preserves both new fields."""
        cs = _make_combat_state(
            round_number=6,
            defeat_nudge_emitted=True,
            defeat_nudge_round=7,
        )
        state = _make_game_state(combat_state=cs)

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        restored_cs = restored["combat_state"]
        assert isinstance(restored_cs, CombatState)
        assert restored_cs.defeat_nudge_emitted is True
        assert restored_cs.defeat_nudge_round == 7

    def test_legacy_checkpoint_back_fills_defaults(self) -> None:
        """Old checkpoint dict with no nudge fields -> defaults applied."""
        # Build a state, serialize it, then strip the new keys to simulate
        # a pre-15.8 checkpoint on disk.
        import json

        state = _make_game_state(combat_state=_make_combat_state())
        json_str = serialize_game_state(state)
        as_dict = json.loads(json_str)
        # Strip the new fields from the combat_state subdict
        as_dict["combat_state"].pop("defeat_nudge_emitted", None)
        as_dict["combat_state"].pop("defeat_nudge_round", None)
        legacy_json = json.dumps(as_dict)

        restored = deserialize_game_state(legacy_json)

        restored_cs = restored["combat_state"]
        assert isinstance(restored_cs, CombatState)
        assert restored_cs.defeat_nudge_emitted is False
        assert restored_cs.defeat_nudge_round == 0

    def test_round_trip_preserves_current_initiative_index(self) -> None:
        """Code Review carry-over fix: the Story 15-3 `current_initiative_index`
        cursor must round-trip through persistence so a checkpoint loaded
        mid-combat resumes at the correct slot rather than restarting the
        round at index 0. (Was an unfixed Story 15-7 oversight; rolled
        into the 15-8 review since the surrounding deserialization code
        was being modified.)"""
        cs = _make_combat_state(round_number=5)
        cs = cs.model_copy(update={"current_initiative_index": 4})
        state = _make_game_state(combat_state=cs)

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)

        restored_cs = restored["combat_state"]
        assert isinstance(restored_cs, CombatState)
        assert restored_cs.current_initiative_index == 4


# =============================================================================
# TestEndCombatResetsNudgeFields (AC #7)
# =============================================================================


class TestEndCombatResetsNudgeFields:
    """`_execute_end_combat()` returns a fresh CombatState() with new
    fields back at False/0 (auto via Pydantic defaults — no code change
    in `_execute_end_combat()` itself; this is a regression guard)."""

    def test_end_combat_clears_nudge_fields(self) -> None:
        cs = _make_combat_state(
            round_number=4,
            defeat_nudge_emitted=True,
            defeat_nudge_round=3,
        )
        state = _make_game_state(combat_state=cs)

        _, reset_cs, _ = _execute_end_combat(state)

        assert isinstance(reset_cs, CombatState)
        assert reset_cs.defeat_nudge_emitted is False
        assert reset_cs.defeat_nudge_round == 0


# =============================================================================
# TestAddendumConstants (sanity / AC #3)
# =============================================================================


class TestAddendumConstants:
    """Module-level sanity on the new prompt constant."""

    def test_constant_mentions_required_terms(self) -> None:
        """The constant text covers the contractual phrases from AC #3."""
        assert "0 HP" in DM_COMBAT_ALL_DEFEATED_ADDENDUM
        assert "dm_end_combat" in DM_COMBAT_ALL_DEFEATED_ADDENDUM
        assert "Encounter Resolution" in DM_COMBAT_ALL_DEFEATED_ADDENDUM

    def test_constant_distinct_from_narrative_addendum(self) -> None:
        """Layered design — the two constants must be different objects."""
        assert DM_COMBAT_ALL_DEFEATED_ADDENDUM != DM_COMBAT_NARRATIVE_ADDENDUM


# =============================================================================
# TestComposabilityWithMaxRounds (additional coverage — Story 15-6 + 15-8 stack)
# =============================================================================


class TestComposabilityWithMaxRounds:
    """Verify the Story 15-6 max-rounds path and the Story 15-8 force-end
    fallback compose correctly when both could fire on the same round (AC #10).

    Per `context_manager()` ordering: the max-rounds block runs FIRST and can
    reset combat to `CombatState()` (active=False). Once that happens, the
    15-8 block's `combat.active` guard short-circuits and 15-8 does NOT also
    append a duplicate `[System]:` line. The losing path becomes a no-op.
    """

    def test_max_rounds_wins_when_both_eligible_same_round(self) -> None:
        """Both 15-6 max-rounds AND 15-8 force-end eligible -> 15-6 fires
        first; 15-8 must NOT also append its force-end log line."""
        # round_number=10 -> bumps to 11. With max_combat_rounds=10, 15-6
        # fires (new_round 11 > max_rounds 10). 15-8 would ALSO fire on
        # the same invocation (defeat_nudge_round=5, delta=11-5=6 >= 3),
        # but the 15-6 reset must short-circuit it.
        cs = _make_combat_state(
            round_number=10,
            defeat_nudge_emitted=True,
            defeat_nudge_round=5,
        )
        config = GameConfig(
            combat_mode="Tactical",  # type: ignore[arg-type]
            summarizer_model="gemini-1.5-flash",
            party_size=3,
            max_combat_rounds=10,
        )
        state = _make_game_state(combat_state=cs, game_config=config)

        result = context_manager(state)

        new_cs = result["combat_state"]
        assert isinstance(new_cs, CombatState)
        # Combat fully reset (could be by either branch).
        assert new_cs.active is False
        assert new_cs == CombatState()
        # Crucial assertion: ONLY ONE force-end-style [System]: line.
        log = result["ground_truth_log"]
        max_rounds_msgs = [
            e for e in log if "Combat ended after reaching the maximum round limit" in e
        ]
        force_end_msgs = [
            e
            for e in log
            if "Combat force-ended after DM failed to call dm_end_combat" in e
        ]
        nudge_msgs = [e for e in log if "All hostile combatants are defeated" in e]
        assert len(max_rounds_msgs) == 1, "15-6 max-rounds line should appear once"
        assert len(force_end_msgs) == 0, (
            "15-8 force-end MUST NOT also fire after 15-6 reset combat"
        )
        # Pre-flagged nudge state from before should not get re-emitted either.
        assert len(nudge_msgs) == 0

    def test_combat_state_fully_resets_when_both_paths_eligible(self) -> None:
        """When 15-6 fires and resets combat, the new (fresh) CombatState
        must have defeat_nudge_emitted=False and defeat_nudge_round=0,
        regardless of whether the prior state had them set."""
        cs = _make_combat_state(
            round_number=10,
            defeat_nudge_emitted=True,
            defeat_nudge_round=5,
        )
        config = GameConfig(
            combat_mode="Tactical",  # type: ignore[arg-type]
            summarizer_model="gemini-1.5-flash",
            party_size=3,
            max_combat_rounds=10,
        )
        state = _make_game_state(combat_state=cs, game_config=config)

        result = context_manager(state)

        new_cs = result["combat_state"]
        assert isinstance(new_cs, CombatState)
        assert new_cs.defeat_nudge_emitted is False
        assert new_cs.defeat_nudge_round == 0


# =============================================================================
# TestMultiEncounterSequence (additional coverage — encounter A -> B isolation)
# =============================================================================


class TestMultiEncounterSequence:
    """Verify nudge state isolates cleanly across encounters.

    Encounter A: nudge fires -> DM calls dm_end_combat -> CombatState reset.
    Encounter B: fresh combat starts -> nudge can fire again without being
    suppressed by stale flags from encounter A.
    """

    def test_nudge_can_fire_in_second_encounter_after_first_ended(self) -> None:
        """End encounter A via _execute_end_combat; start encounter B fresh
        via CombatState(active=True, ...); confirm context_manager() emits
        a fresh nudge for B."""
        # === Encounter A: fully defeated, nudge already emitted ===
        cs_a = _make_combat_state(
            round_number=4,
            defeat_nudge_emitted=True,
            defeat_nudge_round=3,
        )
        state_a = _make_game_state(combat_state=cs_a)

        # End combat A (mirrors what dm_end_combat triggers).
        _, reset_cs, _ = _execute_end_combat(state_a)
        assert reset_cs.defeat_nudge_emitted is False
        assert reset_cs.defeat_nudge_round == 0
        assert reset_cs.active is False

        # === Encounter B: brand-new combat, all NPCs immediately at 0 HP ===
        # (Simulating: PCs nuke a fresh encounter on round 1 with a fireball.)
        cs_b = CombatState(
            active=True,
            round_number=1,
            initiative_order=["dm", "shadowmere", "dm:goblin_chief"],
            initiative_rolls={"shadowmere": 18, "dm:goblin_chief": 6},
            original_turn_queue=["dm", "shadowmere", "thorin", "gandalf"],
            npc_profiles={
                "goblin_chief": _make_npc(name="Goblin Chief", hp_current=0, hp_max=20),
            },
        )
        state_b = _make_game_state(combat_state=cs_b)

        result_b = context_manager(state_b)
        new_cs_b = result_b["combat_state"]

        assert isinstance(new_cs_b, CombatState)
        # Nudge MUST fire for the new encounter (not suppressed by stale state).
        assert new_cs_b.defeat_nudge_emitted is True
        # round_number bumped 1 -> 2 by the round-tracking block.
        assert new_cs_b.defeat_nudge_round == 2
        log = result_b["ground_truth_log"]
        assert any(
            "[System]: All hostile combatants are defeated" in e for e in log
        )

    def test_end_combat_then_start_combat_preserves_nudge_isolation(self) -> None:
        """Double-check: a CombatState() reconstruction (as _execute_end_combat
        returns) discards nudge state; constructing a NEW CombatState(active=True)
        does NOT inherit nudge fields from the prior encounter."""
        # This exercises the type-level guarantee: nudge state lives only on
        # the current CombatState instance, not via any module-level cache.
        prior = CombatState(
            active=True,
            round_number=8,
            defeat_nudge_emitted=True,
            defeat_nudge_round=3,
        )
        # Simulate _execute_end_combat: returns CombatState() defaults.
        ended = CombatState()
        assert ended.defeat_nudge_emitted is False
        assert ended.defeat_nudge_round == 0
        # The prior instance is untouched (Pydantic immutable-ish via copy).
        assert prior.defeat_nudge_emitted is True
        # New combat has independent state.
        fresh = CombatState(active=True, round_number=1)
        assert fresh.defeat_nudge_emitted is False
        assert fresh.defeat_nudge_round == 0


# =============================================================================
# TestPersistenceFullFieldRoundTrip (additional coverage — bug-class regression)
# =============================================================================


class TestPersistenceFullFieldRoundTrip:
    """Combined round-trip of ALL three CombatState fields touched by the
    Story 15-7/15-8 work: `current_initiative_index` (15-7 carry-over fix
    rolled into 15-8 review), `defeat_nudge_emitted` (15-8), and
    `defeat_nudge_round` (15-8). Single-test omnibus to catch any ordering /
    keyword-argument regressions in `deserialize_game_state()`."""

    def test_round_trip_preserves_all_new_fields_together(self) -> None:
        """Single state with non-default values for ALL three fields must
        round-trip cleanly."""
        cs = _make_combat_state(
            round_number=5,
            defeat_nudge_emitted=True,
            defeat_nudge_round=3,
        )
        cs = cs.model_copy(update={"current_initiative_index": 4})
        state = _make_game_state(combat_state=cs)

        json_str = serialize_game_state(state)
        restored = deserialize_game_state(json_str)
        restored_cs = restored["combat_state"]

        assert isinstance(restored_cs, CombatState)
        assert restored_cs.current_initiative_index == 4
        assert restored_cs.defeat_nudge_emitted is True
        assert restored_cs.defeat_nudge_round == 3
        # And the unrelated fields are preserved too (sanity).
        assert restored_cs.round_number == 5
        assert restored_cs.active is True
        assert len(restored_cs.npc_profiles) == 3
        # NPCs round-trip with hp_current=0 (the defeated state that drove
        # the nudge in the first place).
        assert all(p.hp_current == 0 for p in restored_cs.npc_profiles.values())

    def test_legacy_checkpoint_missing_all_three_fields(self) -> None:
        """Pre-15-7 checkpoint: combat_state subdict lacks all three new
        fields. deserialize_game_state() must back-fill safe defaults
        for each independently."""
        import json

        state = _make_game_state(combat_state=_make_combat_state())
        json_str = serialize_game_state(state)
        as_dict = json.loads(json_str)
        # Strip ALL three new fields from the combat_state subdict.
        as_dict["combat_state"].pop("defeat_nudge_emitted", None)
        as_dict["combat_state"].pop("defeat_nudge_round", None)
        as_dict["combat_state"].pop("current_initiative_index", None)
        legacy_json = json.dumps(as_dict)

        restored = deserialize_game_state(legacy_json)
        restored_cs = restored["combat_state"]

        assert isinstance(restored_cs, CombatState)
        assert restored_cs.defeat_nudge_emitted is False
        assert restored_cs.defeat_nudge_round == 0
        assert restored_cs.current_initiative_index == 0


# =============================================================================
# TestSystemPromptAddendumStacking (additional coverage — order + simultaneous)
# =============================================================================


class TestSystemPromptAddendumStacking:
    """When both DM_COMBAT_NARRATIVE_ADDENDUM (15-7) and
    DM_COMBAT_ALL_DEFEATED_ADDENDUM (15-8) are eligible, the assembled
    SystemMessage must contain BOTH, in the documented order
    (NARRATIVE first, ALL_DEFEATED second). Code Review verdict #1 noted
    the "layered, not replaced" design — this guards that explicitly."""

    @patch("agents.get_llm")
    def test_both_addenda_present_in_correct_order(
        self, mock_get_llm: MagicMock
    ) -> None:
        """All-defeated nudge active -> SystemMessage contains both
        addenda; NARRATIVE addendum appears BEFORE ALL_DEFEATED addendum."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn

        captured: list[Any] = []

        def fake_invoke(msgs: list[Any]) -> Any:
            captured.append(msgs)
            return AIMessage(content="The Mist-Stalkers lie defeated.")

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = fake_invoke
        mock_get_llm.return_value = mock_model

        cs = _make_combat_state(
            round_number=4,
            defeat_nudge_emitted=True,
            defeat_nudge_round=4,
        )
        state = _make_game_state(combat_state=cs, current_turn="dm")
        dm_turn(state)

        sys_content = captured[0][0].content
        # Both signature phrases must be present.
        narrative_marker = "Combat Damage Tracking"
        all_defeated_marker = "Encounter Resolution"
        assert narrative_marker in sys_content
        assert all_defeated_marker in sys_content
        # NARRATIVE (15-7) must precede ALL_DEFEATED (15-8) — the layering
        # order is load-bearing because the all-defeated reinforcement
        # builds on the narrative addendum's dm_update_npc reminder.
        assert sys_content.index(narrative_marker) < sys_content.index(
            all_defeated_marker
        ), "NARRATIVE addendum must appear before ALL_DEFEATED addendum"

    @patch("agents.get_llm")
    def test_all_defeated_addendum_skipped_when_combat_inactive(
        self, mock_get_llm: MagicMock
    ) -> None:
        """Even if defeat_nudge_emitted=True (stale), combat.active=False
        means NEITHER addendum should appear — the gating is on active."""
        from langchain_core.messages import AIMessage

        from agents import dm_turn

        captured: list[Any] = []

        def fake_invoke(msgs: list[Any]) -> Any:
            captured.append(msgs)
            return AIMessage(content="Exploration narrative.")

        mock_model = MagicMock()
        mock_model.bind_tools.return_value = mock_model
        mock_model.invoke.side_effect = fake_invoke
        mock_get_llm.return_value = mock_model

        # Inactive combat with stale nudge flag set (defensive scenario).
        cs = _make_combat_state(
            active=False,
            round_number=4,
            defeat_nudge_emitted=True,
            defeat_nudge_round=4,
        )
        state = _make_game_state(combat_state=cs, current_turn="dm")
        dm_turn(state)

        sys_content = captured[0][0].content
        assert "Combat Damage Tracking" not in sys_content
        assert "Encounter Resolution" not in sys_content


# =============================================================================
# TestRevivalThenRedefeatRefiresNudge (additional coverage — AC #9 follow-on)
# =============================================================================


class TestRevivalThenRedefeatRefiresNudge:
    """The existing TestRevivalResetsNudge test verifies the FIRST half of
    AC #9 (revival clears the flag). This class verifies the LATTER half —
    the rationale documented in AC #9: "if all NPCs go to 0 HP again later,
    the nudge should fire again". Three-state machine: defeated -> revived
    -> re-defeated, end-to-end."""

    def test_revival_then_redefeat_fires_nudge_again(self) -> None:
        """Sequence:
        1. All defeated, nudge fires (round_number bumps 3 -> 4, nudge_round=4).
        2. Revive one NPC to hp=5; context_manager() resets the flag.
        3. Re-defeat the revived NPC (hp=0 again); context_manager() must
           emit a SECOND [System]: line and re-flag defeat_nudge_emitted=True
           with the NEW round_number.
        """
        # === Step 1: all defeated, nudge fires ===
        cs1 = _make_combat_state(round_number=3)
        state1 = _make_game_state(combat_state=cs1)
        result1 = context_manager(state1)

        cs_after_1 = result1["combat_state"]
        assert isinstance(cs_after_1, CombatState)
        assert cs_after_1.defeat_nudge_emitted is True
        first_nudge_round = cs_after_1.defeat_nudge_round
        assert first_nudge_round == 4  # bumped from 3
        first_nudge_count = sum(
            1
            for e in result1["ground_truth_log"]
            if "[System]: All hostile combatants are defeated" in e
        )
        assert first_nudge_count == 1

        # === Step 2: revive one NPC; flag should clear ===
        revived_profiles = {
            "mist-stalker_alpha": _make_npc(hp_current=5),  # REVIVED
            "mist-stalker_beta": _make_npc(name="Mist-Stalker Beta", hp_current=0),
            "mist-stalker_gamma": _make_npc(name="Mist-Stalker Gamma", hp_current=0),
        }
        cs2 = cs_after_1.model_copy(update={"npc_profiles": revived_profiles})
        # Carry the prior log forward so we can compare lengths later.
        state2 = {**state1, **result1, "combat_state": cs2}
        result2 = context_manager(state2)

        cs_after_2 = result2["combat_state"]
        assert isinstance(cs_after_2, CombatState)
        assert cs_after_2.defeat_nudge_emitted is False
        assert cs_after_2.defeat_nudge_round == 0

        # === Step 3: re-defeat. Nudge must fire AGAIN. ===
        redefeated_profiles = {
            "mist-stalker_alpha": _make_npc(hp_current=0),  # killed again
            "mist-stalker_beta": _make_npc(name="Mist-Stalker Beta", hp_current=0),
            "mist-stalker_gamma": _make_npc(name="Mist-Stalker Gamma", hp_current=0),
        }
        cs3 = cs_after_2.model_copy(update={"npc_profiles": redefeated_profiles})
        state3 = {**state1, **result2, "combat_state": cs3}
        result3 = context_manager(state3)

        cs_after_3 = result3["combat_state"]
        assert isinstance(cs_after_3, CombatState)
        # Nudge re-fires.
        assert cs_after_3.defeat_nudge_emitted is True
        # New nudge_round MUST differ from the first (round_number kept
        # incrementing across the three calls).
        assert cs_after_3.defeat_nudge_round != first_nudge_round
        assert cs_after_3.defeat_nudge_round > first_nudge_round

        # Total [System]: nudge lines in the log = 2 (first + re-fire).
        nudge_count = sum(
            1
            for e in result3["ground_truth_log"]
            if "[System]: All hostile combatants are defeated" in e
        )
        assert nudge_count == 2


# =============================================================================
# TestForceEndEdgeCases (additional coverage — Block E corner cases)
# =============================================================================


class TestForceEndEdgeCases:
    """Edge-case behavior of the Story 15-8 force-end fallback (Block E)
    not covered by the existing TestForceEndFallback class."""

    def test_force_end_with_empty_original_turn_queue_does_not_modify_queue(
        self,
    ) -> None:
        """If `original_turn_queue` is empty (defensive: should never
        happen in practice — _execute_start_combat always saves it — but
        the production code's `if combat_for_fallback.original_turn_queue:`
        guard means we don't clobber `turn_queue` when the backup is
        empty). Combat itself is still force-ended."""
        cs = _make_combat_state(
            round_number=8,
            defeat_nudge_emitted=True,
            defeat_nudge_round=4,
            original_turn_queue=[],  # empty backup
        )
        existing_queue = ["dm", "shadowmere", "thorin", "gandalf"]
        state = _make_game_state(
            combat_state=cs,
            turn_queue=existing_queue,
        )

        result = context_manager(state)

        new_cs = result["combat_state"]
        assert isinstance(new_cs, CombatState)
        # Combat still force-ended.
        assert new_cs.active is False
        assert new_cs == CombatState()
        # turn_queue NOT overwritten (empty backup -> no restore).
        assert result["turn_queue"] == existing_queue
        # System line still appended.
        assert any(
            "Combat force-ended after DM failed to call dm_end_combat" in e
            for e in result["ground_truth_log"]
        )

    def test_force_end_only_one_system_line_appended(self) -> None:
        """A single context_manager() invocation that triggers force-end
        must append exactly ONE force-end [System]: line — not duplicate it
        if the function were re-entered (but we only call it once here, this
        is a single-invocation invariant guard)."""
        cs = _make_combat_state(
            round_number=8,
            defeat_nudge_emitted=True,
            defeat_nudge_round=4,
        )
        state = _make_game_state(combat_state=cs)

        result = context_manager(state)

        force_end_count = sum(
            1
            for e in result["ground_truth_log"]
            if "Combat force-ended after DM failed to call dm_end_combat" in e
        )
        assert force_end_count == 1

    def test_force_end_after_revival_then_redefeat_uses_new_nudge_round(
        self,
    ) -> None:
        """Subtle: after revival -> re-defeat (Block D resets nudge_round
        to 0, then Block C re-emits at the new round_number), the force-end
        countdown must restart from the NEW nudge_round, not the original.
        Otherwise a slow revival would falsely accelerate force-end.

        Setup: combat at round 10. Pre-flagged with nudge_round=2 (would
        normally trigger force-end immediately, delta=8). But one NPC is
        alive — Block D should reset both flags. Combat continues.
        """
        cs = _make_combat_state(
            round_number=10,
            defeat_nudge_emitted=True,
            defeat_nudge_round=2,  # very stale — would force-end if not reset
            npc_profiles={
                "mist-stalker_alpha": _make_npc(hp_current=5),  # alive
                "mist-stalker_beta": _make_npc(name="Mist-Stalker Beta", hp_current=0),
                "mist-stalker_gamma": _make_npc(name="Mist-Stalker Gamma", hp_current=0),
            },
        )
        state = _make_game_state(combat_state=cs)

        result = context_manager(state)

        new_cs = result["combat_state"]
        assert isinstance(new_cs, CombatState)
        # Critical: combat MUST still be active. Block D must reset BEFORE
        # Block E reads. If the order were inverted, the stale (round=11,
        # nudge_round=2, delta=9) would force-end despite the revival.
        assert new_cs.active is True
        assert new_cs.defeat_nudge_emitted is False
        assert new_cs.defeat_nudge_round == 0
        # No force-end line appended.
        assert not any(
            "Combat force-ended after DM failed to call dm_end_combat" in e
            for e in result["ground_truth_log"]
        )
