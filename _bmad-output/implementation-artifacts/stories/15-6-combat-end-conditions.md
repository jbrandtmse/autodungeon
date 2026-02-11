# Story 15.6: Combat End Conditions

Status: ready-for-dev

## Epic

Epic 15: Combat Initiative System

## Story

As a **game engine developer**,
I want **the DM to end combat by calling `dm_end_combat`, which restores the original turn queue, resets all combat state fields, and handles edge cases like dead NPCs and a configurable max round safety limit**,
So that **combat transitions cleanly back to exploration mode, the turn queue reflects the pre-combat order, and infinite combat loops are prevented by a safety valve**.

## Priority

High (without this story, combat never cleanly returns to exploration mode -- `_execute_end_combat()` resets `CombatState` but does NOT restore `turn_queue`, leaving the game in a broken state after combat ends)

## Estimate

Medium (turn queue restoration in `_execute_end_combat()`, `max_combat_rounds` config option, round limit enforcement in `context_manager()`, comprehensive tests)

## Dependencies

- Story 15-1 (Combat State Model & Detection): **done** -- provides `CombatState`, `NpcProfile` models, `combat_state` field on `GameState`, `dm_end_combat` tool schema.
- Story 15-2 (Initiative Rolling & Turn Reordering): **done** -- provides `_execute_start_combat()` / `_execute_end_combat()` in agents.py, tool interception in `dm_turn()`. `_execute_start_combat()` saves `original_turn_queue`. `_execute_end_combat()` resets `CombatState()` to defaults but does NOT restore `turn_queue`.
- Story 15-3 (Combat-Aware Graph Routing): **done** -- provides combat-aware `route_to_next_agent()`, round increment in `context_manager()`, recursion limit adjustments.
- Story 15-4 (DM Bookend & NPC Turns): **done** -- provides `_get_combat_turn_type()`, NPC turn prompting, bookend narration, dynamic `current_turn` return in `dm_turn()`.

## Acceptance Criteria

1. **Given** the DM calls `dm_end_combat` during a combat encounter, **When** `_execute_end_combat()` processes the call, **Then** `combat_state.original_turn_queue` is restored to the `turn_queue` field in the returned state, so that subsequent rounds use the pre-combat exploration order.

2. **Given** `_execute_end_combat()` is called, **When** it completes, **Then** the returned `CombatState` is reset to defaults (`active=False`, `round_number=0`, empty `initiative_order`, `initiative_rolls`, `original_turn_queue`, `npc_profiles`).

3. **Given** `dm_turn()` intercepts a `dm_end_combat` tool call, **When** it processes the result from `_execute_end_combat()`, **Then** the returned `GameState` includes both the reset `combat_state` AND the restored `turn_queue` (both fields updated together).

4. **Given** `_execute_end_combat()` is called when `original_turn_queue` is empty (edge case -- combat started with empty backup), **When** it processes, **Then** the `turn_queue` is NOT overwritten (falls back to the current `turn_queue`), and a warning is logged.

5. **Given** `_execute_end_combat()` is called when combat is NOT active, **When** it processes, **Then** it returns a no-op message ("No combat is currently active.") and does NOT modify `turn_queue` or `combat_state`.

6. **Given** a `max_combat_rounds` field on `GameConfig`, **When** it is set (default: `50`), **Then** it defines the maximum number of combat rounds before automatic termination.

7. **Given** combat is active and `combat_state.round_number` exceeds `game_config.max_combat_rounds`, **When** `context_manager()` runs at the start of the next round, **Then** it forces combat to end by resetting `combat_state` to defaults and restoring `turn_queue` from `original_turn_queue`.

8. **Given** the max round limit is reached, **When** combat is force-ended in `context_manager()`, **Then** a log entry is appended to `ground_truth_log` indicating the combat timed out (e.g., "[System]: Combat ended after reaching the maximum round limit.").

9. **Given** the max round limit is reached, **When** combat is force-ended, **Then** a logger warning is emitted with the round number and max limit for debugging.

10. **Given** `max_combat_rounds` is set to `0`, **When** combat is active, **Then** the round limit is disabled (no automatic termination), allowing combat to run indefinitely.

11. **Given** the DM ends combat with NPCs at 0 HP in `npc_profiles`, **When** `_execute_end_combat()` resets the state, **Then** the NPC profiles are cleared along with all other combat state (the DM is responsible for narrating NPC defeat as part of the end-combat narration).

12. **Given** the DM ends combat normally, **When** the next round's `route_to_next_agent()` runs, **Then** it uses `turn_queue` (restored exploration order) because `combat_state.active` is `False`.

13. **Given** the current `_execute_end_combat()` signature returns `tuple[str, CombatState]`, **When** this story modifies it, **Then** the return type is updated to `tuple[str, CombatState, list[str] | None]` where the third element is the restored turn queue (or `None` if no restoration needed).

14. **Given** `dm_turn()` currently handles the `dm_end_combat` tool call by storing `reset_combat_state`, **When** this story updates the handler, **Then** it also stores the restored `turn_queue` and includes it in the returned `GameState`.

## Tasks / Subtasks

- [ ] Task 1: Add `max_combat_rounds` field to `GameConfig` in `models.py` (AC: #6, #10)
  - [ ] 1.1: Add `max_combat_rounds: int = Field(default=50, ge=0, description="Maximum combat rounds before auto-termination (0 = unlimited)")` to `GameConfig`
  - [ ] 1.2: Place the field after `combat_mode` for logical grouping

- [ ] Task 2: Update `_execute_end_combat()` in `agents.py` to restore turn queue (AC: #1, #2, #3, #4, #5, #11, #13)
  - [ ] 2.1: Change return type from `tuple[str, CombatState]` to `tuple[str, CombatState, list[str] | None]`
  - [ ] 2.2: When combat is active, retrieve `original_turn_queue` from `combat_state`
  - [ ] 2.3: If `original_turn_queue` is non-empty, return it as the third element (restored turn queue)
  - [ ] 2.4: If `original_turn_queue` is empty (edge case), return `None` for the third element and log a warning
  - [ ] 2.5: When combat is NOT active (no-op), return `None` for the third element
  - [ ] 2.6: Return reset `CombatState()` as before (second element)

- [ ] Task 3: Update `dm_turn()` tool interception for `dm_end_combat` (AC: #3, #14)
  - [ ] 3.1: Update the `dm_end_combat` handler to unpack the new three-element tuple from `_execute_end_combat()`
  - [ ] 3.2: Store the restored turn queue (if not `None`) in a variable (e.g., `restored_turn_queue`)
  - [ ] 3.3: At the end of `dm_turn()`, include `turn_queue=restored_turn_queue` in the returned `GameState` when the value is not `None`

- [ ] Task 4: Add max round limit enforcement in `context_manager()` in `graph.py` (AC: #7, #8, #9, #10)
  - [ ] 4.1: After the existing round increment logic, add a max round limit check
  - [ ] 4.2: Read `max_combat_rounds` from `state["game_config"]`
  - [ ] 4.3: If `max_combat_rounds > 0` and `combat.round_number > max_combat_rounds`, force-end combat
  - [ ] 4.4: Force-end: restore `turn_queue` from `combat_state.original_turn_queue` (if non-empty), reset `combat_state` to `CombatState()` defaults
  - [ ] 4.5: Append "[System]: Combat ended after reaching the maximum round limit." to `ground_truth_log`
  - [ ] 4.6: Emit `logger.warning("Combat force-ended: round %d exceeded max_combat_rounds=%d", round_number, max_combat_rounds)`
  - [ ] 4.7: If `max_combat_rounds == 0`, skip the check entirely (unlimited rounds)

- [ ] Task 5: Update persistence for `max_combat_rounds` (AC: #6)
  - [ ] 5.1: Verify `serialize_game_state()` handles the new `GameConfig` field automatically via `model_dump()` (it should, since GameConfig is a Pydantic model)
  - [ ] 5.2: Verify `deserialize_game_state()` handles backward compatibility (old saves without `max_combat_rounds` will use the Pydantic default of 50)
  - [ ] 5.3: If explicit handling is needed, add it (likely a no-op since Pydantic handles missing fields with defaults)

- [ ] Task 6: Write tests in `tests/test_story_15_6_combat_end_conditions.py` (AC: #1-#14)
  - [ ] 6.1: `class TestExecuteEndCombatTurnQueueRestoration` -- turn queue restoration logic
  - [ ] 6.2: `class TestExecuteEndCombatEdgeCases` -- empty original_turn_queue, combat not active
  - [ ] 6.3: `class TestDmTurnEndCombatIntegration` -- dm_turn correctly processes end combat with queue restoration
  - [ ] 6.4: `class TestMaxCombatRoundsConfig` -- GameConfig field defaults, validation, zero means unlimited
  - [ ] 6.5: `class TestContextManagerMaxRoundEnforcement` -- force-end when limit exceeded
  - [ ] 6.6: `class TestContextManagerMaxRoundDisabled` -- no force-end when max is 0
  - [ ] 6.7: `class TestCombatEndRoutingRestoration` -- route_to_next_agent uses turn_queue after combat ends
  - [ ] 6.8: `class TestCombatEndStateClear` -- all combat_state fields reset to defaults
  - [ ] 6.9: `class TestPersistenceBackwardCompat` -- old saves without max_combat_rounds deserialize correctly

## Dev Notes

### Turn Queue Restoration -- The Missing Piece

The current `_execute_end_combat()` (agents.py line 2377) resets `CombatState()` to defaults but does NOT return a restored turn queue. The `dm_turn()` handler at the `dm_end_combat` branch stores the reset combat state but does not touch `turn_queue`. This means after combat ends:

1. `combat_state.active = False` (correct -- routing falls back to `turn_queue`)
2. `turn_queue` still has the pre-combat exploration order (it was NEVER modified -- Story 15-2 explicitly chose not to modify `turn_queue`, storing combat order in `initiative_order` instead)
3. `combat_state.original_turn_queue` was saved but is now lost (reset to empty list in the new `CombatState()`)

Wait -- re-examining the flow:
- `_execute_start_combat()` saves `turn_queue` into `combat_state.original_turn_queue` but does NOT modify `turn_queue` itself
- `route_to_next_agent()` uses `combat_state.initiative_order` when combat is active, ignoring `turn_queue`
- `_execute_end_combat()` resets `combat_state` to defaults, so `active=False`
- `route_to_next_agent()` now reads `turn_queue` again, which was never modified

So **in the current implementation, `turn_queue` is actually already correct** after combat ends! The `original_turn_queue` backup is redundant because `turn_queue` was never overwritten.

HOWEVER, the sprint change proposal explicitly calls for restoring `original_turn_queue`, and it is good practice to explicitly restore it for safety and clarity. If a future story modifies `turn_queue` during combat (e.g., removing dead PCs), the restoration logic becomes essential.

**Recommendation**: Still implement the restoration for robustness, but the primary code path will be confirming that `turn_queue` matches `original_turn_queue`. The edge case where they differ (future: PC death removes them from `turn_queue`) is where this becomes critical.

### Updating `_execute_end_combat()` Return Type

Current signature (agents.py line 2377):

```python
def _execute_end_combat(
    state: GameState,
) -> tuple[str, CombatState]:
```

New signature:

```python
def _execute_end_combat(
    state: GameState,
) -> tuple[str, CombatState, list[str] | None]:
    """Process dm_end_combat tool call.

    Resets combat state to defaults and restores the original turn queue.

    Story 15.6: Combat End Conditions.

    Args:
        state: Current game state for reading combat_state.

    Returns:
        Tuple of (tool_result_string, reset_combat_state, restored_turn_queue).
        restored_turn_queue is None when combat was not active or
        original_turn_queue was empty.
    """
    combat_state = state.get("combat_state")
    if combat_state is None or not combat_state.active:
        return "No combat is currently active.", CombatState(), None

    # Restore turn queue from backup
    restored_queue: list[str] | None = None
    if combat_state.original_turn_queue:
        restored_queue = list(combat_state.original_turn_queue)
    else:
        logger.warning(
            "Combat ending but original_turn_queue is empty -- "
            "turn_queue will not be modified"
        )

    return (
        "Combat ended. Restoring exploration turn order.",
        CombatState(),
        restored_queue,
    )
```

### Updating `dm_turn()` End Combat Handler

Current handler (in the dm_turn tool call loop):

```python
elif tool_name == "dm_end_combat":
    tool_result, reset_combat_state = _execute_end_combat(state)
    updated_combat_state = reset_combat_state
    logger.info("DM ended combat: %s", tool_result)
```

Updated handler:

```python
elif tool_name == "dm_end_combat":
    tool_result, reset_combat_state, restored_queue = _execute_end_combat(state)
    updated_combat_state = reset_combat_state
    if restored_queue is not None:
        restored_turn_queue = restored_queue
    logger.info("DM ended combat: %s", tool_result)
```

Initialize `restored_turn_queue: list[str] | None = None` alongside the other tracking variables at the top of `dm_turn()`.

At the end of `dm_turn()` where the return `GameState(...)` is constructed, add:

```python
# Story 15.6: Restore turn queue when combat ends
turn_queue_for_return = (
    restored_turn_queue if restored_turn_queue is not None
    else state["turn_queue"]
)
```

And set `turn_queue=turn_queue_for_return` in the returned `GameState(...)`.

### Max Combat Rounds -- Config Field

Add to `GameConfig` (models.py line 284, after `combat_mode`):

```python
max_combat_rounds: int = Field(
    default=50,
    ge=0,
    description="Maximum combat rounds before auto-termination (0 = unlimited)",
)
```

Default of 50 is a generous safety valve. A typical D&D combat lasts 3-8 rounds. 50 rounds means something has gone seriously wrong (likely an infinite loop scenario). Setting to 0 disables the limit.

### Max Round Enforcement in `context_manager()`

The round limit check goes AFTER the round increment (graph.py line 110-118), so the sequence is:

1. Round number is incremented (existing logic)
2. Check if incremented round exceeds max limit
3. If exceeded, force-end combat

```python
# Combat round tracking (Story 15-3)
combat = updated_state.get("combat_state")
if combat and isinstance(combat, CombatState) and combat.active and combat.round_number >= 1:
    updated_state["combat_state"] = combat.model_copy(
        update={"round_number": combat.round_number + 1}
    )

    # Story 15.6: Max round limit safety valve
    max_rounds = updated_state.get("game_config", GameConfig()).max_combat_rounds
    new_round = combat.round_number + 1
    if max_rounds > 0 and new_round > max_rounds:
        logger.warning(
            "Combat force-ended: round %d exceeded max_combat_rounds=%d",
            new_round,
            max_rounds,
        )
        # Restore turn queue from backup
        if combat.original_turn_queue:
            updated_state["turn_queue"] = list(combat.original_turn_queue)
        # Reset combat state
        updated_state["combat_state"] = CombatState()
        # Append system notification to ground truth log
        updated_state["ground_truth_log"] = [
            *updated_state["ground_truth_log"],
            "[System]: Combat ended after reaching the maximum round limit.",
        ]
```

Note: The `GameConfig` type needs to be imported in `graph.py`. Check if it is already imported -- if not, add it to the existing import from `models`.

### Dead NPC Handling

Per the design decision in the sprint change proposal, the DM decides when combat ends. There is no automatic victory/TPK detection in this story. The `check_combat_end_conditions()` function from the proposal is intentionally NOT implemented here -- it was described as a future consideration.

When combat ends:
- NPCs at 0 HP are simply cleared when `npc_profiles` is reset (part of `CombatState()` defaults)
- The DM is expected to narrate NPC defeat/death as part of its end-combat turn narration
- No automatic cleanup or state modification for dead NPCs

This is the simplest approach and keeps the DM in full narrative control.

### Backward Compatibility -- `max_combat_rounds`

Old checkpoint JSON files will not have `max_combat_rounds` in their `GameConfig` data. Since `GameConfig` is a Pydantic model with `max_combat_rounds` having a default value of `50`, deserialization will use the default automatically. No explicit backward compatibility code is needed in `persistence.py`.

However, if `GameConfig` instances are created from dicts with `**data`, Pydantic will fill in the default. Verify this works by testing deserialization of old-format saves.

### Files to Modify

1. **`models.py`** -- Add `max_combat_rounds` field to `GameConfig` (after `combat_mode`)
2. **`agents.py`** -- Update `_execute_end_combat()` return type and logic to include turn queue restoration; update `dm_turn()` end combat handler to unpack restored queue and include in return state
3. **`graph.py`** -- Add max round limit enforcement in `context_manager()` after the round increment logic; import `GameConfig` if not already imported
4. **`tests/test_story_15_6_combat_end_conditions.py`** -- **NEW** test file

### Files NOT to Modify

- **`tools.py`** -- No changes. `dm_end_combat` tool schema is already defined (Story 15-1).
- **`persistence.py`** -- No changes. `GameConfig` serialization handles new fields via `model_dump()` and deserialization uses Pydantic defaults for missing fields.
- **`app.py`** -- No changes. Combat UI is Story 15-5.
- **`config.py`** -- No changes. `max_combat_rounds` is a `GameConfig` field with a default.
- **`memory.py`** -- No changes.
- **`styles/theme.css`** -- No changes.

### Test Approach

Create `tests/test_story_15_6_combat_end_conditions.py`. Use class-based test organization matching project convention.

**`class TestMaxCombatRoundsConfig`:**
- Test `GameConfig` has `max_combat_rounds` field with default 50
- Test `max_combat_rounds=0` is valid (unlimited)
- Test `max_combat_rounds=-1` raises `ValidationError` (ge=0)
- Test `max_combat_rounds=100` is valid (custom limit)
- Test `GameConfig()` with no `max_combat_rounds` keyword uses default 50

**`class TestExecuteEndCombatTurnQueueRestoration`:**
- Test returns three-element tuple (str, CombatState, list | None)
- Test restored turn queue matches `original_turn_queue` when combat active
- Test returned `CombatState` is reset to defaults (active=False, empty collections)
- Test `original_turn_queue` is preserved as a copy (not a reference to the original list)
- Test with realistic `original_turn_queue` (e.g., `["dm", "fighter", "rogue", "wizard", "cleric"]`)

**`class TestExecuteEndCombatEdgeCases`:**
- Test combat not active returns `None` for turn queue and no-op message
- Test empty `original_turn_queue` returns `None` for turn queue and logs warning
- Test `combat_state` missing from state returns `None` for turn queue

**`class TestDmTurnEndCombatIntegration`:**
- Test `dm_turn()` returns state with restored `turn_queue` after end combat
- Test `dm_turn()` returns state with reset `combat_state` after end combat
- Test `dm_turn()` turn_queue is unchanged when end combat has no restoration (no-op)
- Mock the LLM to avoid real API calls

**`class TestContextManagerMaxRoundEnforcement`:**
- Test force-ends combat when `round_number + 1 > max_combat_rounds`
- Test restores `turn_queue` from `original_turn_queue` on force-end
- Test resets `combat_state` to defaults on force-end
- Test appends "[System]:" log entry on force-end
- Test emits warning log on force-end
- Test does NOT force-end when `round_number + 1 <= max_combat_rounds`
- Test combat state fields are all reset (active, round_number, initiative_order, etc.)

**`class TestContextManagerMaxRoundDisabled`:**
- Test `max_combat_rounds=0` skips the limit check entirely
- Test combat continues past round 100 when `max_combat_rounds=0`

**`class TestCombatEndRoutingRestoration`:**
- Test `route_to_next_agent()` uses `turn_queue` after combat_state is reset
- Test `route_to_next_agent()` does not reference initiative_order after combat ends

**`class TestCombatEndStateClear`:**
- Test all `CombatState` fields are at defaults after end combat
- Test `npc_profiles` is empty (dead NPC cleanup)
- Test `initiative_order` is empty
- Test `initiative_rolls` is empty
- Test `original_turn_queue` is empty
- Test `active` is False
- Test `round_number` is 0

**`class TestPersistenceBackwardCompat`:**
- Test old `GameConfig` JSON without `max_combat_rounds` deserializes with default 50
- Test `GameConfig` with `max_combat_rounds` set serializes and deserializes correctly round-trip

Build test state helpers with `CombatState` populated with realistic combat data (active combat with NPCs, initiative_order, original_turn_queue). Mock `dm_turn` internals (LLM) in integration tests.

### Edge Cases to Handle

- `original_turn_queue` is empty when combat ends (logged warning, no queue modification)
- `combat_state` is None or missing from state dict (defensive coding -- treat as no combat)
- `max_combat_rounds` is 0 (unlimited -- skip check)
- `max_combat_rounds` set very low (e.g., 1) -- combat ends after first round increment
- `game_config` missing from state (defensive -- use `GameConfig()` default)
- Force-end via max rounds while DM is mid-turn (context_manager runs before DM, so this ends combat before the round starts)
- `_execute_end_combat` called twice in same turn (second call is no-op since combat already inactive)

### Import Requirements

In `graph.py`, ensure `GameConfig` is imported from `models`. Check the existing import block -- if `GameConfig` is not there, add it. `CombatState` should already be imported (Story 15-3).

In `agents.py`, no new imports needed -- `CombatState`, `GameConfig`, and logging are already available.

### Existing Patterns to Follow

- **Helper function naming**: `_execute_start_combat()`, `_execute_end_combat()` -- modifying the existing `_execute_end_combat()` in place
- **Config field pattern**: `combat_mode` on `GameConfig` -- follow with `max_combat_rounds` immediately after
- **Logger usage**: `logger.warning(...)` -- same pattern as other combat logging
- **Ground truth log append**: `[System]:` prefix for system messages (matches existing convention)
- **Test file naming**: `tests/test_story_15_6_combat_end_conditions.py`
- **Test organization**: Class-based grouping matching project convention

### References

- [Source: agents.py#_execute_end_combat ~line 2377] - Current end combat helper to modify (add turn queue restoration)
- [Source: agents.py#_execute_start_combat ~line 2282] - Start combat helper that saves original_turn_queue
- [Source: agents.py#dm_turn ~line 1692] - DM turn function with end combat tool interception
- [Source: graph.py#context_manager ~line 45] - Context manager with round increment (add max round enforcement)
- [Source: graph.py#route_to_next_agent ~line 123] - Routing function that falls back to turn_queue when combat inactive
- [Source: graph.py#run_single_round ~line 430] - Round execution with recursion limit
- [Source: models.py#GameConfig ~line 273] - Config class to add max_combat_rounds field
- [Source: models.py#GameConfig.combat_mode ~line 284] - Adjacent field for placement reference
- [Source: models.py#CombatState ~line 853] - Combat state with original_turn_queue, active, round_number
- [Source: models.py#GameState ~line 1813] - GameState TypedDict with turn_queue and combat_state
- [Source: models.py#CharacterSheet.hit_points_current ~line 1607] - PC HP field (ge=0, so 0 HP is valid)
- [Source: models.py#NpcProfile.hp_current ~line 836] - NPC HP field (ge=0, so 0 HP is valid)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-10.md#Story 15-6] - Design specification
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-10.md#Section 3 Option C1] - Dynamic Turn Queue with restoration on combat end
- [Source: _bmad-output/implementation-artifacts/stories/15-1-combat-state-model.md] - Story 15-1 context (CombatState, NpcProfile, dm_end_combat)
- [Source: _bmad-output/implementation-artifacts/stories/15-2-initiative-rolling.md] - Story 15-2 context (_execute_end_combat, _execute_start_combat)
- [Source: _bmad-output/implementation-artifacts/stories/15-3-combat-aware-routing.md] - Story 15-3 context (combat-aware routing, round increment)
- [Source: _bmad-output/implementation-artifacts/stories/15-4-dm-bookend-npc-turns.md] - Story 15-4 context (current_turn dynamic return)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
