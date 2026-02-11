# Story 15.3: Combat-Aware Routing

Status: ready-for-dev

## Epic

Epic 15: Combat Initiative System

## Story

As a **game engine developer**,
I want **`route_to_next_agent()` to follow `combat_state.initiative_order` when combat is active, routing DM bookend and NPC turns to the DM node and PC turns to their respective nodes**,
So that **tactical combat uses initiative-based turn ordering with NPCs interleaved at their correct initiative positions, and normal exploration routing is restored when combat ends**.

## Priority

High (core routing change -- Story 15-4 DM bookend/NPC prompting and Story 15-6 combat end conditions depend on combat routing working)

## Estimate

High (core graph routing changes, dynamic workflow creation, round tracking, comprehensive test coverage for a high-risk code path)

## Dependencies

- Story 15-1 (Combat State Model & Detection): **done** -- provides `CombatState`, `NpcProfile` models, `combat_state` field on `GameState`, persistence support.
- Story 15-2 (Initiative Rolling & Turn Reordering): **in-dev** -- provides `roll_initiative()`, `_execute_start_combat()` / `_execute_end_combat()` in agents.py, tool interception in `dm_turn()`. Story 15-2 populates `combat_state.initiative_order`, `combat_state.active`, `combat_state.round_number`, `combat_state.original_turn_queue`, and `combat_state.npc_profiles`. This story reads those fields for routing decisions.
- `combat_state.initiative_order` format: `["dm", "dm:goblin_1", "shadowmere", "dm:goblin_2", "thorin", "brother_aldric", "elara"]` where `"dm"` at index 0 is the bookend turn and `"dm:npc_name"` entries are individual NPC turns routed to the DM node.

## Acceptance Criteria

1. **Given** `combat_state.active` is `True`, **When** `route_to_next_agent()` determines the next turn, **Then** it reads from `combat_state.initiative_order` instead of `turn_queue`.

2. **Given** `combat_state.active` is `False` (or `combat_state` is at default), **When** `route_to_next_agent()` determines the next turn, **Then** it reads from `turn_queue` exactly as before (no behavior change for non-combat rounds).

3. **Given** the next entry in `initiative_order` starts with `"dm:"` (e.g., `"dm:goblin_1"`), **When** `route_to_next_agent()` routes, **Then** it returns `"dm"` (routing to the DM node, which will handle NPC-specific prompting in Story 15-4).

4. **Given** the next entry in `initiative_order` is a PC name (e.g., `"shadowmere"`), **When** `route_to_next_agent()` routes, **Then** it returns that PC name (routing to the PC's agent node).

5. **Given** the next entry in `initiative_order` is `"dm"` (the bookend turn at position 0), **When** `route_to_next_agent()` routes, **Then** it returns `"dm"` (routing to the DM node for round narration).

6. **Given** the current turn is the last entry in `initiative_order`, **When** `route_to_next_agent()` checks for round completion, **Then** it returns `END` to signal the round is complete.

7. **Given** the current agent just completed the last turn in `initiative_order` (round complete), **When** the next `run_single_round()` begins, **Then** `combat_state.round_number` is incremented and the initiative order starts again from position 0 (`"dm"` bookend).

8. **Given** `combat_state.active` is `True`, **When** `create_game_workflow()` builds the graph, **Then** the routing map includes `"dm"` for all `"dm:npc_name"` entries in the initiative order (so conditional edges can route NPC turns to the DM node).

9. **Given** `create_game_workflow()` is called with a `turn_queue` that does NOT include NPC entries, **When** combat routing sends a `"dm:npc_name"` turn to the DM node, **Then** the DM node is already registered and handles it correctly (NPC entries do not need their own graph nodes).

10. **Given** human intervention is active for a controlled character, **When** that character's turn comes up in `initiative_order` during combat, **Then** the human intervention routing still works correctly (routes to `"human"` node).

11. **Given** `dm_turn()` returns state with `current_turn` set to a `"dm:npc_name"` value (from Story 15-4, future), **When** `route_to_next_agent()` looks up the current position, **Then** it finds the `"dm:npc_name"` entry in `initiative_order` and advances to the next entry.

12. **Given** `run_single_round()` is called during active combat, **When** the recursion limit is set, **Then** it accounts for the potentially larger number of turns per round (initiative_order may have more entries than turn_queue due to NPC entries).

13. **Given** `dm_end_combat()` resets `combat_state` to defaults (active=False), **When** the next round's `route_to_next_agent()` runs, **Then** it uses `turn_queue` (normal exploration order) because `combat_state.active` is `False`.

## Tasks / Subtasks

- [ ] Task 1: Modify `route_to_next_agent()` in `graph.py` to support combat routing (AC: #1, #2, #3, #4, #5, #6, #10, #11)
  - [ ] 1.1: At the top of the function, read `combat_state` from state: `combat = state.get("combat_state")`
  - [ ] 1.2: Determine the turn order list: if `combat` and `combat.active`, use `combat.initiative_order`; otherwise use `state["turn_queue"]`
  - [ ] 1.3: Look up `current` in the chosen order list. Handle `ValueError` by defaulting to `"dm"`.
  - [ ] 1.4: If current is at the last position, return `END` (round complete)
  - [ ] 1.5: Get `next_agent` from the next position in the order list
  - [ ] 1.6: If `next_agent.startswith("dm:")`, return `"dm"` (route NPC turns to DM node)
  - [ ] 1.7: Preserve existing human intervention logic: check `human_active` and `controlled_character` against the NEXT agent (not current), applying to both combat and non-combat routing
  - [ ] 1.8: Otherwise return `next_agent` directly (PC turn or DM bookend)

- [ ] Task 2: Modify `create_game_workflow()` in `graph.py` to handle combat routing map (AC: #8, #9)
  - [ ] 2.1: The routing map already includes `"dm"` as a valid target. Verify that `route_to_next_agent()` only ever returns node names that exist in the graph (i.e., `"dm"`, PC names, `"human"`, or `END`). Since NPC turns return `"dm"`, no new nodes are needed.
  - [ ] 2.2: No changes to `create_game_workflow()` are needed IF `route_to_next_agent()` only returns values already in the routing map. The key insight is that `"dm:npc_name"` entries are NEVER returned as routing targets -- they are resolved to `"dm"` inside `route_to_next_agent()`.

- [ ] Task 3: Add round increment logic for combat round tracking (AC: #7)
  - [ ] 3.1: Add a `_maybe_increment_combat_round()` helper function in `graph.py` that checks if combat is active and increments `round_number` when a new round starts
  - [ ] 3.2: Call this helper in `context_manager()` (which runs at the start of each round before the DM turn). If `combat_state.active` is True, increment `combat_state.round_number` by 1 and return the updated state.
  - [ ] 3.3: Alternatively, the round increment could happen in `run_single_round()` before invoking the workflow. Choose the location that is most testable and least intrusive.

- [ ] Task 4: Update `run_single_round()` recursion limit for combat rounds (AC: #12)
  - [ ] 4.1: The current recursion limit is `len(state["turn_queue"]) + 2`. During combat, the initiative_order may be longer (includes NPC entries). Update to use `max(len(state["turn_queue"]), len(combat_state.initiative_order)) + 2` when combat is active.

- [ ] Task 5: Update `dm_turn()` return dict to pass through `combat_state` (AC: #11)
  - [ ] 5.1: **NOTE**: Story 15-2 may already handle this. If `dm_turn()` already includes `combat_state` in its return `GameState(...)`, this task is a no-op. If not, add `combat_state=state.get("combat_state", CombatState())` to the return dict.
  - [ ] 5.2: Similarly ensure `pc_turn()` passes through `combat_state` in its return dict: `combat_state=state.get("combat_state", CombatState())`.
  - [ ] 5.3: This is critical because LangGraph merges state updates from node functions. If `combat_state` is not included, it could be lost between turns.

- [ ] Task 6: Ensure `current_turn` is set correctly for NPC turns (AC: #11)
  - [ ] 6.1: When the DM handles an NPC turn (e.g., `"dm:goblin_1"`), `dm_turn()` currently sets `current_turn="dm"`. For combat routing to advance correctly, `current_turn` must be set to the actual initiative_order entry (e.g., `"dm:goblin_1"`).
  - [ ] 6.2: **NOTE**: This is primarily a Story 15-4 concern (DM bookend & NPC turn prompting). For Story 15-3, the routing logic should be written to WORK with `"dm:npc_name"` values in `current_turn`, but the actual setting of `current_turn` to NPC entries may come in 15-4.
  - [ ] 6.3: For now, document that `route_to_next_agent()` expects `current_turn` to match an entry in `initiative_order` during combat. If `current_turn` is `"dm"` and there are multiple `"dm"` / `"dm:*"` entries, the first match is used (which is the bookend at position 0).

- [ ] Task 7: Write tests in `tests/test_story_15_3_combat_aware_routing.py` (AC: #1-#13)
  - [ ] 7.1: `class TestRouteToNextAgentNonCombat` -- verify all existing non-combat routing behavior is preserved
  - [ ] 7.2: `class TestRouteToNextAgentCombat` -- combat routing with initiative_order
  - [ ] 7.3: `class TestRouteToNextAgentNpcRouting` -- NPC entries route to "dm"
  - [ ] 7.4: `class TestRouteToNextAgentHumanIntervention` -- human override works in combat
  - [ ] 7.5: `class TestRouteToNextAgentRoundCompletion` -- END signal at last initiative entry
  - [ ] 7.6: `class TestCombatRoundIncrement` -- round_number increments on new rounds
  - [ ] 7.7: `class TestRunSingleRoundRecursionLimit` -- recursion limit adjusts for combat
  - [ ] 7.8: `class TestCombatStatePassthrough` -- dm_turn and pc_turn preserve combat_state
  - [ ] 7.9: `class TestCombatEndRestoresRouting` -- after end_combat, routing uses turn_queue again
  - [ ] 7.10: `class TestCreateGameWorkflowCombat` -- workflow creation handles combat routing

## Dev Notes

### Core Routing Change (`route_to_next_agent()`)

This is the highest-risk change in Epic 15. The `route_to_next_agent()` function is the routing heart of the entire game loop. Every turn transition goes through it. The combat branch must be carefully implemented to avoid breaking non-combat (exploration/roleplay) routing.

Current implementation (graph.py line 113-157):

```python
def route_to_next_agent(state: GameState) -> str:
    current = state["current_turn"]
    turn_queue = state["turn_queue"]

    # Human override
    if state["human_active"] and state["controlled_character"]:
        if current != "dm" and current == state["controlled_character"]:
            return "human"

    # Find position, advance, or END
    try:
        current_idx = turn_queue.index(current)
    except ValueError:
        return "dm"
    if current_idx == len(turn_queue) - 1:
        return END
    return turn_queue[current_idx + 1]
```

New implementation should be:

```python
def route_to_next_agent(state: GameState) -> str:
    from models import CombatState

    current = state["current_turn"]
    combat = state.get("combat_state")

    # Determine which order list to use
    if combat and isinstance(combat, CombatState) and combat.active:
        order = combat.initiative_order
    else:
        order = state["turn_queue"]

    # Find current position in the order
    try:
        current_idx = order.index(current)
    except ValueError:
        # Current agent not found in order -- default to DM
        return "dm"

    # Check if round is complete (last agent in order)
    if current_idx == len(order) - 1:
        return END

    # Get next agent
    next_agent = order[current_idx + 1]

    # Handle human override -- check if next agent is the controlled character
    if state["human_active"] and state["controlled_character"]:
        # Only intercept if the next agent IS the controlled character (not DM, not NPC)
        if next_agent == state["controlled_character"]:
            return "human"

    # Route NPC turns to DM node
    if next_agent.startswith("dm:"):
        return "dm"

    return next_agent
```

**CRITICAL DESIGN DECISION -- Human Intervention Timing:**

The current code checks if `current == state["controlled_character"]` (i.e., checks whether the CHARACTER THAT JUST ACTED is the controlled one). This is because the routing happens AFTER a node executes -- `current_turn` is set by the node that just ran.

However, looking more carefully, the current code checks `current != "dm" and current == state["controlled_character"]`. This means: "if the current turn was the controlled character, route to human." This is WRONG for the combat case because `current_turn` is the agent that JUST acted, and routing determines WHERE TO GO NEXT.

Actually, re-reading the code flow: `route_to_next_agent` is called as a conditional edge AFTER a node runs. The node sets `current_turn` to itself. So `route_to_next_agent` determines the NEXT node. The current logic says: "if the character that just acted is the human-controlled one, route to human." This means the human gets to act ON their own turn (after the previous agent acts, the routing sees it's the controlled character's turn and routes to human).

Wait -- that doesn't match. Let me re-examine: The conditional edge is attached to EACH node. After the DM node runs (sets `current_turn="dm"`), routing runs. It looks at `turn_queue.index("dm")` = 0, finds next is `turn_queue[1]`. Before returning `turn_queue[1]`, it checks if `current == controlled_character` -- but `current` is `"dm"`, so it doesn't trigger. The next PC runs. After PC1 runs (sets `current_turn="pc1"`), routing runs again. If PC1 is the controlled character, `current == controlled_character` is True, so it returns `"human"`. But PC1 already ran! The human node then processes the human's action for PC1's "turn".

Actually, I think the human intervention works differently -- looking at the flow:
1. DM runs, sets `current_turn="dm"`
2. Routing: `turn_queue.index("dm") = 0`, next = `turn_queue[1]` = "fighter". Check human: current="dm" != controlled_character. Return "fighter".
3. Fighter runs, sets `current_turn="fighter"`
4. Routing: `turn_queue.index("fighter") = 1`, next = `turn_queue[2]` = "rogue". Check human: current="fighter" == controlled_character? If yes, return "human".

So human takes over AFTER the fighter has already acted? That seems like a bug... but the human_intervention_node reads from `st.session_state["human_pending_action"]`. The autopilot loop likely detects human_active and pauses before invoking, letting the human type their action. The graph structure allows the human node to execute IN PLACE of the next PC's turn by routing to "human" instead.

Actually, I think the intention is different. The human intervention works like this: when it's the controlled character's turn, the PREVIOUS turn's routing redirects to "human" instead of to the controlled character. Let me re-read:

```python
if current != "dm" and current == state["controlled_character"]:
    return "human"
```

This says: if the current turn (the agent that just acted) is the controlled character AND is not the DM, route to human. This means AFTER the controlled character's AI turn runs, it routes to "human" instead of the next agent. The human node then adds the human's action (essentially replacing or supplementing the AI's action).

For combat routing, we need to maintain this same behavior. The key question is: in combat, when `current_turn` is set to a value like `"dm:goblin_1"`, will the human check still work? Yes, because the human check only triggers when `current == controlled_character`, and `controlled_character` is always a PC name (never `"dm:*"`).

**REVISED**: Keep the human intervention check in its current position -- checking `current` (the agent that just acted). The check should remain `current == state["controlled_character"]` and should NOT check `current != "dm"` restriction in combat mode because DM bookend and NPC turns don't affect it.

Actually, the simplest approach is to keep the human check exactly as-is. It checks `current` (who just acted). If the controlled character just acted, route to human. This works for both combat and non-combat because:
- In combat: PC runs -> current_turn = "pc_name" -> if that's the controlled character, route to human
- NPC runs -> current_turn = "dm:npc_name" -> never matches controlled_character -> normal routing
- DM bookend runs -> current_turn = "dm" -> blocked by `current != "dm"` -> normal routing

### No Changes Needed to `create_game_workflow()`

This is a key insight. The `route_to_next_agent()` function only ever RETURNS these values:
- `"dm"` -- for DM turns, DM bookend turns, AND NPC turns (all go to the DM node)
- `"{pc_name}"` -- for PC turns (already in the routing map)
- `"human"` -- for human intervention (already in the routing map)
- `END` -- for round completion (already in the routing map)

Since `"dm:npc_name"` is NEVER returned (it's resolved to `"dm"` inside the function), the routing map in `create_game_workflow()` does NOT need any changes. The existing routing map handles all possible return values.

### Round Increment Location

The round number should be incremented in `context_manager()` at the start of each round. This is the natural location because:
1. `context_manager` runs at `START -> context_manager -> dm` (before every round)
2. It already manages pre-round state (memory compression)
3. The increment is: if `combat_state.active`, set `round_number += 1`

However, there is a subtlety: the FIRST round (round 1) is set by `_execute_start_combat()` in Story 15-2. So `context_manager` should only increment for rounds AFTER the first. The check is: if `combat_state.active and combat_state.round_number >= 1`, increment.

Wait, that would increment on every round including the first continuation. Let me think more carefully:

- `_execute_start_combat()` sets `round_number = 1` and `active = True`
- The first combat round executes (DM bookend -> NPCs/PCs -> END)
- `run_single_round()` is called again for round 2
- `context_manager` runs and should set `round_number = 2`
- Round 2 executes
- `run_single_round()` for round 3
- `context_manager` increments to `round_number = 3`

So the logic in `context_manager` should be:

```python
# Combat round tracking (Story 15.3)
combat = updated_state.get("combat_state")
if combat and combat.active and combat.round_number >= 1:
    # Increment round for each new round after the initial one
    updated_state["combat_state"] = combat.model_copy(
        update={"round_number": combat.round_number + 1}
    )
```

But wait -- this runs EVERY time `context_manager` is invoked. For the FIRST round (when `_execute_start_combat()` just set `round_number=1`), we do NOT want to increment because the combat just started. The combat start happens DURING the DM's turn (mid-round), and the current round should complete as round 1.

Timeline:
1. Round N (exploration): `context_manager` -> DM (calls start_combat, sets round=1) -> PCs act in initiative order -> END
2. Round N+1 (combat round 2): `context_manager` should increment to round=2 -> DM bookend -> NPCs/PCs -> END
3. Round N+2 (combat round 3): `context_manager` increments to round=3 -> ...

So `context_manager` should increment `round_number` ONLY when `active=True` AND `round_number >= 1`. Since `_execute_start_combat` sets `round_number=1`, the first time `context_manager` runs after combat starts, `round_number` is 1, so it increments to 2. This is correct because that IS the start of round 2.

But there is an issue: the combat starts MID-round. When the DM calls `start_combat` during their turn, the remaining PCs in that round act in initiative order. Then END is reached. The NEXT `run_single_round()` call starts combat round 2. So:

- DM turn (starts combat, round_number=1) -> PCs act (still round 1) -> END
- context_manager (increments to 2) -> DM bookend (round 2) -> NPCs/PCs -> END
- context_manager (increments to 3) -> DM bookend (round 3) -> ...

This is correct!

Actually wait -- there is another subtlety. When combat starts mid-round, the PCs that act AFTER the DM in that round should follow the initiative order. But they are still in the same `run_single_round()` invocation. The routing will switch to initiative_order because `combat_state.active` is now True. The DM's turn set `current_turn="dm"`, and the routing will look up "dm" in `initiative_order` (position 0), then advance to position 1. This works correctly.

### Recursion Limit Update in `run_single_round()`

Current: `len(state["turn_queue"]) + 2`

During combat, `initiative_order` may include NPC entries, making it longer than `turn_queue`. Update to:

```python
combat = state.get("combat_state")
if combat and hasattr(combat, 'active') and combat.active:
    turn_count = len(combat.initiative_order)
else:
    turn_count = len(state["turn_queue"])
recursion_limit = turn_count + 2
```

The `+ 2` accounts for the `context_manager` node and one extra margin.

### State Passthrough in Node Functions

Every node function (`dm_turn`, `pc_turn`, `human_intervention_node`, `context_manager`) must include `combat_state` in their return dict. Otherwise LangGraph's state merging may drop it.

Check what Story 15-2 does:
- If `dm_turn()` already returns `combat_state`, this is handled for the DM node.
- `pc_turn()` (agents.py line 2200-2220) currently does NOT include `combat_state` in its return. Must add it.
- `human_intervention_node()` (graph.py line 160-263) does NOT include `combat_state`. Must add it.
- `context_manager()` (graph.py line 45-110) does NOT include `combat_state`. Must add it (and this is where round increment happens).

**IMPORTANT**: Since `GameState` is a TypedDict and LangGraph merges returned state, missing fields are NOT overwritten -- they retain their previous values. So if `pc_turn` doesn't return `combat_state`, the previous value is preserved. HOWEVER, this behavior depends on LangGraph's merge strategy. To be safe, all node functions should pass through `combat_state`.

Actually, looking at the existing code more carefully, `dm_turn()` and `pc_turn()` return a FULL `GameState(...)` with ALL fields. They don't return partial dicts. So `combat_state` MUST be included or it will be missing from the returned state. Let me verify...

Yes, `dm_turn()` returns `GameState(...)` at line 1750 with every field listed. The return currently does NOT include `combat_state` or `active_fork_id`. This means these fields are effectively lost after the DM turn! This is a bug.

Wait -- looking at `GameState` definition (TypedDict), ALL fields are required (no `NotRequired`). But `dm_turn()` at line 1750 constructs a `GameState(...)` without `active_fork_id` or `combat_state`. In Python, TypedDict doesn't enforce at runtime, so this creates a dict that is technically missing those keys. LangGraph then merges this with the previous state... but if it REPLACES rather than merges, those fields would be lost.

This needs to be investigated during implementation. For now, the story should require that all node functions include `combat_state` in their return dicts.

### Files to Modify

1. **`graph.py`** -- Modify `route_to_next_agent()` for combat routing; modify `context_manager()` for round increment; modify `human_intervention_node()` to pass through `combat_state`; modify `run_single_round()` for recursion limit
2. **`agents.py`** -- Ensure `dm_turn()` and `pc_turn()` include `combat_state` in return dict (may overlap with Story 15-2)
3. **`tests/test_story_15_3_combat_aware_routing.py`** -- **NEW** test file

### Files NOT to Modify

- **`models.py`** -- No changes. CombatState already defined (Story 15-1).
- **`tools.py`** -- No changes. Initiative rolling is Story 15-2.
- **`persistence.py`** -- No changes. CombatState serialization already handled (Story 15-1).
- **`app.py`** -- No changes. Combat UI is Story 15-5.
- **`config.py`** -- No changes.
- **`memory.py`** -- No changes.
- **`styles/theme.css`** -- No changes.

### Test Approach

Create `tests/test_story_15_3_combat_aware_routing.py`. Use class-based test organization matching project convention.

**`class TestRouteToNextAgentNonCombat`:**
- Test standard routing: DM -> PC1 -> PC2 -> END (no combat)
- Test with `combat_state` at defaults (active=False) -- same as no combat
- Test `combat_state` field missing from state dict -- same as no combat
- Test human intervention in non-combat -- behavior unchanged
- Test unknown `current_turn` defaults to "dm"

**`class TestRouteToNextAgentCombat`:**
- Test combat routing follows initiative_order: dm -> dm:goblin_1 -> shadowmere -> dm:goblin_2 -> thorin -> END
- Test first entry after dm bookend routes correctly
- Test mid-order PC routing advances correctly
- Test last entry in initiative_order returns END
- Test initiative_order with only PCs (no NPCs)
- Test initiative_order with only NPCs (edge case)

**`class TestRouteToNextAgentNpcRouting`:**
- Test `"dm:goblin_1"` next entry returns `"dm"`
- Test `"dm:wolf"` next entry returns `"dm"`
- Test NPC entry in various positions (first after bookend, middle, last before END)
- Test consecutive NPC entries (dm:goblin_1 -> dm:goblin_2 both route to "dm")

**`class TestRouteToNextAgentHumanIntervention`:**
- Test human override works during combat for controlled character
- Test human override does NOT trigger for NPC turns
- Test human override does NOT trigger for DM bookend
- Test human override with controlled character NOT in initiative_order (edge case)

**`class TestRouteToNextAgentRoundCompletion`:**
- Test END returned when current is last in initiative_order
- Test END returned when current is last in turn_queue (non-combat)
- Test round completion with single entry in initiative_order (edge case)

**`class TestCombatRoundIncrement`:**
- Test context_manager increments round_number when combat active
- Test context_manager does NOT increment when combat inactive
- Test round_number goes from 1 to 2 on second round
- Test round_number sequence: 1 -> 2 -> 3 over multiple rounds
- Test context_manager does not modify other combat_state fields

**`class TestRunSingleRoundRecursionLimit`:**
- Test recursion limit uses turn_queue length when no combat
- Test recursion limit uses initiative_order length when combat active
- Test recursion limit with initiative_order longer than turn_queue

**`class TestCombatStatePassthrough`:**
- Test dm_turn return includes combat_state
- Test pc_turn return includes combat_state
- Test human_intervention_node return includes combat_state
- Test context_manager return includes combat_state

**`class TestCombatEndRestoresRouting`:**
- Test routing uses turn_queue after combat_state.active becomes False
- Test routing uses turn_queue after combat_state is reset to defaults

**`class TestCreateGameWorkflowCombat`:**
- Test workflow compiles with standard turn_queue (no combat-specific nodes needed)
- Test route_to_next_agent only returns valid node names ("dm", PC names, "human", END)

Build test state helpers with `CombatState` populated with realistic initiative_order values. Mock `dm_turn` and `pc_turn` in integration tests to avoid LLM calls.

### Edge Cases to Handle

- `combat_state` is `None` or missing from state dict (defensive coding)
- `combat_state` is a plain dict instead of `CombatState` instance (deserialization edge case)
- `initiative_order` is empty while `active` is True (defensive -- fall back to turn_queue)
- `current_turn` is `"dm:npc_name"` but not found in initiative_order (default to "dm")
- Multiple `"dm"` entries in initiative_order -- `list.index()` returns first match, which is correct for bookend
- `current_turn = "dm"` matches bookend at position 0, not NPC entries (correct behavior)
- Human-controlled character that doesn't appear in initiative_order (handle gracefully)

### Import Requirements

In `graph.py`, add import of `CombatState` from `models`. Use conditional import or TYPE_CHECKING to avoid circular imports if needed. Since `graph.py` already imports from `models`, just add `CombatState` to the existing import.

### References

- [Source: graph.py#route_to_next_agent ~line 113] - Current routing implementation to modify
- [Source: graph.py#context_manager ~line 45] - Round increment location
- [Source: graph.py#create_game_workflow ~line 266] - Workflow factory (verify no changes needed)
- [Source: graph.py#run_single_round ~line 399] - Recursion limit to update
- [Source: graph.py#human_intervention_node ~line 160] - Human node (combat_state passthrough)
- [Source: models.py#CombatState ~line 853] - CombatState model with initiative_order, active, round_number
- [Source: models.py#GameState ~line 1813] - GameState TypedDict with combat_state field
- [Source: agents.py#dm_turn ~line 1484] - DM turn return dict (needs combat_state)
- [Source: agents.py#pc_turn ~line 2198] - PC turn return dict (needs combat_state)
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-10.md#Story 15-3] - Design specification
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-10.md#Section 3 Option C1] - Dynamic Turn Queue architecture decision
- [Source: _bmad-output/implementation-artifacts/stories/15-1-combat-state-model.md] - Story 15-1 context
- [Source: _bmad-output/implementation-artifacts/stories/15-2-initiative-rolling.md] - Story 15-2 context (dependency)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
