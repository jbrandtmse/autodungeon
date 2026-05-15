# Story 15.7: NPC Damage Tracking & Combat-State Injection in DM Context

Status: review

## Epic

Epic 15: Combat Initiative System (v1.2)

## Story

As a **game engine developer**,
I want **a `dm_update_npc` tool that mutates `NpcProfile.hp_current` and conditions, plus injection of the live combat state into the DM's main context prompt and filtering of defeated NPCs from `initiative_order`**,
So that **the DM has a consistent, mutable view of NPC HP across all turn types, narrates combat that actually ends when enemies die, and defeated NPCs stop acting on subsequent rounds**.

## Priority

High (combat coherence is broken without this — root cause of the Session 017 Mist-Stalker incident where a 101-turn encounter never resolved because NPC HP never decremented)

## Estimate

Medium (~150–250 LoC across `tools.py`, `agents.py`, `graph.py`, plus ~25 tests). Touches DM prompt assembly hot-path — strict gating required.

## Dependencies

- Story 15-1 (Combat State Model & Detection): **done** — provides `NpcProfile.hp_current: int = Field(ge=0)`, `CombatState.npc_profiles`, `combat_state` field on `GameState`. Validates that `hp_current=0` is a legal defeated state.
- Story 15-2 (Initiative Rolling & Turn Reordering): **done** — provides `_execute_start_combat()` which is the template for `_execute_npc_update()`, and `_sanitize_npc_name()` for key normalization. `_execute_start_combat()` initializes `hp_current=hp_max` at [agents.py:2491](agents.py#L2491) (the field this story mutates).
- Story 15-3 (Combat-Aware Routing): **done** — provides `route_to_next_agent()` in graph.py with `initiative_order` consumption and `current_initiative_index` advancement. This story filters defeated NPCs out of the order this function reads.
- Story 15-4 (DM Bookend & NPC Turns): **done** — provides `_build_combatant_summary()` which already shows NPC HP on bookend turns; this story extends that visibility to regular DM narrative turns.
- Story 15-6 (Combat End Conditions): **done** — provides `max_combat_rounds` safety valve. This story addresses a different gap (HP never drops to trigger natural end) and does not interact with the safety valve.
- Story 8-4 (DM Tool Calls for Sheet Updates): **done** — provides the *template pattern* this story mirrors: `dm_update_character_sheet` tool, `_execute_sheet_update()` interception, and the `[SHEET]:` notification format from Story 8-5.

## Acceptance Criteria

1. **Given** `tools.py`, **When** a developer imports DM tools, **Then** `dm_update_npc(npc_name: str, hp_change: int = 0, conditions_add: list[str] | None = None, conditions_remove: list[str] | None = None) -> str` is available as a `@tool`-decorated function with a docstring containing usage examples.

2. **Given** the `dm_update_npc` tool's schema, **When** registered, **Then** it is added to `__all__` in `tools.py` (alphabetical position) and bound to the DM agent in `create_dm_agent()` at [agents.py:821-829](agents.py#L821-L829).

3. **Given** the `dm_update_npc` tool is called inside `dm_turn()`, **When** the tool name is detected, **Then** the existing tool-call dispatch loop in `dm_turn()` ([agents.py:1942-2030](agents.py#L1942-L2030)) intercepts it (mirroring the `dm_update_character_sheet` branch at [agents.py:1957-1966](agents.py#L1957-L1966)) and calls a new helper `_execute_npc_update(tool_args, combat_state_working_copy)`.

4. **Given** `_execute_npc_update()` is called with a valid `npc_name` matching a key in `combat_state.npc_profiles` (case-insensitive lookup via `_sanitize_npc_name()` from [tools.py:768](tools.py#L768)), **When** it processes, **Then** the matching `NpcProfile` has its `hp_current` adjusted by `hp_change` and clamped to `[0, hp_max]`. The mutation MUST produce a new `NpcProfile` via `model_copy(update={...})` — never mutate in place.

5. **Given** `_execute_npc_update()` is called with valid `conditions_add` and/or `conditions_remove` lists, **When** it processes, **Then** the NPC's `conditions` list is updated: items in `conditions_add` are appended (deduplicated, case-insensitive), and items in `conditions_remove` are filtered out (case-insensitive match).

6. **Given** `_execute_npc_update()` is called with `npc_name` that does not match any key in `npc_profiles` (after sanitization and case-insensitive match), **When** it processes, **Then** it returns `"Error: NPC '<name>' not found in active combat. Available: <comma-separated keys>"` and does NOT mutate state. (Mirror the unknown-character pattern from [agents.py:2429-2431](agents.py#L2429-L2431).)

7. **Given** `_execute_npc_update()` is called when `combat_state.active is False`, **When** it processes, **Then** it returns `"Error: No combat is currently active."` and does NOT mutate state.

8. **Given** an NPC's `hp_current` reaches `0` after the update, **When** the tool result is built, **Then** the returned confirmation string ends with `" (defeated)"` and the dispatcher appends a `[SHEET]: Updated <NPC display name>: HP <old> -> 0 (defeated)` entry to `ground_truth_log`. For non-fatal damage, the format is `[SHEET]: Updated <NPC display name>: HP <old> -> <new> (<+/-N>)`. (Same notification path used for PC sheet updates at [agents.py:2113-2114](agents.py#L2113-L2114).)

9. **Given** `combat_state.active is True`, **When** `_build_dm_context(state)` runs ([agents.py:1367-1480](agents.py#L1367-L1480)), **Then** the resulting context string includes a new section formatted as:
   ```
   ## Active Combat — Round N

   ### NPCs (DM-controlled):
   - Mist-Stalker Alpha: HP 4/15 (wounded) — conditions: prone
   - Mist-Stalker Beta: HP 0/15 (DEFEATED)
   - Mist-Stalker Gamma: HP 12/15
   ```
   The section MUST be inserted before the "## Player Knowledge" section (after character sheets) so it sits prominently in the prompt. NPCs are listed in `initiative_order` sequence (preserving the order the DM has been working with). The status label rules: HP at full = no label, HP at 0 = `(DEFEATED)`, HP between 0 and 25% of max = `(critically wounded)`, HP between 25% and 75% of max = `(wounded)`, HP above 75% but below max = `(lightly wounded)`. Empty `conditions` → omit ` — conditions: ...` suffix.

10. **Given** `combat_state.active is False`, **When** `_build_dm_context(state)` runs, **Then** the combat section is omitted entirely (no behavioral change for exploration mode). This is the critical risk-mitigation requirement.

11. **Given** the DM agent's system prompt during combat, **When** `dm_turn()` assembles `system_prompt_parts` ([agents.py:1855-1868](agents.py#L1855-L1868)), **Then** a combat-aware addendum is appended whenever `combat_state.active is True` containing the guidance:
    > *"You have a `dm_update_npc` tool — call it after PC actions resolve to record damage dealt to NPCs, conditions applied (poisoned, prone, frightened, etc.), and deaths. Do not let an NPC at 0 HP continue acting. When an NPC reaches 0 HP, narrate their defeat in the same response."*
    This addendum runs on **all DM turns during active combat** (regular narrative, bookend, AND NPC-control turns), not just bookends.

12. **Given** an NPC reaches `hp_current = 0`, **When** `route_to_next_agent()` ([graph.py:172-253](graph.py#L172-L253)) executes for the next routing decision, **Then** that NPC's slot in `initiative_order` is skipped: if the entry at `current_initiative_index` is `f"dm:{npc_key}"` and `npc_profiles[npc_key].hp_current == 0`, the function increments `current_initiative_index` and reads the next entry (looping until a live entry is found or the order is exhausted). PC entries are never skipped on this basis.

13. **Given** all NPCs in `npc_profiles` are at 0 HP, **When** `route_to_next_agent()` runs and all remaining `dm:*` entries map to defeated NPCs, **Then** routing falls through to the next live entry (PC or `dm` bookend) without error. The function MUST NOT enter an infinite loop or return `END` prematurely solely because of defeated-NPC filtering. (Story 15-8 will add explicit "all enemies defeated" handling.)

14. **Given** `_execute_npc_update()` returns a non-error result, **When** the tool dispatcher in `dm_turn()` processes it, **Then** the updated `CombatState` is captured into the `updated_combat_state` variable (same path the start-combat / end-combat tools use at [agents.py:2012, 2020](agents.py#L2012)) so it propagates into the returned `GameState.combat_state` at [agents.py:2202](agents.py#L2202).

15. **Given** persistence, **When** `serialize_game_state()` and `deserialize_game_state()` round-trip a state with mutated `npc_profiles[name].hp_current` and `conditions`, **Then** the values are preserved exactly. No persistence code changes required — existing Pydantic `model_dump()` already serializes the fields. A regression test MUST verify this.

16. **Given** the multi-NPC scenario from Session 017 (Mist-Stalkers Alpha/Beta/Gamma at full HP), **When** the DM issues `dm_update_npc(npc_name="Mist-Stalker Alpha", hp_change=-15)`, **Then** Alpha's `hp_current` becomes 0, Alpha is marked `(DEFEATED)` in subsequent `_build_dm_context()` calls, Alpha's `dm:mist-stalker_alpha` slot is skipped by `route_to_next_agent()`, and Beta and Gamma continue acting normally.

17. **Given** the DM passes `hp_change=999` (over-kill), **When** `_execute_npc_update()` processes, **Then** `hp_current` is clamped to `0` (not negative). Given `hp_change=-999` (over-heal — DM passes negative as healing convention), **Then** `hp_current` is clamped to `hp_max` (not above).

    > **Convention note:** `hp_change` follows the *delta semantics* — negative = damage taken, positive = healing. This matches the natural language "the goblin took 7 damage" (`hp_change=-7`) the DM is most likely to produce. Document this clearly in the tool docstring.

18. **Given** the DM passes `conditions_add=["Poisoned"]` and the NPC's `conditions` list already contains `"poisoned"` (different case), **When** processed, **Then** the list remains `["poisoned"]` (no duplicate). Given `conditions_remove=["Poisoned"]`, **Then** the matching condition is removed regardless of case.

19. **Given** an empty `npc_profiles` dict (no NPCs registered — unusual but possible if combat started with PCs only), **When** the combat-section injection in `_build_dm_context()` runs, **Then** the section header is still emitted but the NPC list shows `- (no NPCs in this encounter)` (do not omit the section entirely; the round number is still valuable context).

20. **Given** a defeated NPC (`hp_current == 0`) is later "revived" by the DM via `dm_update_npc(npc_name="...", hp_change=5)`, **When** processed, **Then** the NPC's `hp_current` becomes 5 and `route_to_next_agent()` resumes including the NPC in initiative order from the next round. (Edge case — unlikely in normal play, but the implementation must not assume one-way defeat.)

21. **Given** the new test file `tests/test_story_15_7_npc_damage_tracking.py`, **When** pytest runs, **Then** ≥25 tests pass covering the AC items above, organized into class-based test fixtures (project convention): `TestDmUpdateNpcTool`, `TestExecuteNpcUpdate`, `TestCombatStateInjection`, `TestDefeatedNpcRouting`, `TestSheetNotifications`, `TestPersistenceRoundTrip`, `TestIntegrationSession017`.

22. **Given** the total project test count is currently ~4700+ ([MEMORY.md baseline](C:/Users/Josh/.claude/projects/c--autodungeon/memory/MEMORY.md)), **When** Story 15-7 lands, **Then** total passing tests is ≥ baseline (no new regressions). Pre-existing ~20 failing tests are excluded from the baseline per project convention.

## Tasks / Subtasks

- [x] **Task 1: Add `dm_update_npc` tool to `tools.py`** (AC: #1, #2, #17)
  - [x] 1.1: Define `@tool` decorated `dm_update_npc(npc_name: str, hp_change: int = 0, conditions_add: list[str] | None = None, conditions_remove: list[str] | None = None) -> str` immediately after `dm_update_character_sheet` (around line 715, before `dm_start_combat`).
  - [x] 1.2: Write docstring matching the pattern of `dm_update_character_sheet` — include parameter descriptions, return contract, and ≥3 usage examples (damage, condition apply, defeat).
  - [x] 1.3: Docstring MUST explicitly state delta semantics: `hp_change` is negative for damage, positive for healing.
  - [x] 1.4: Function body returns a placeholder string (e.g., `f"NPC update for {npc_name}: hp_change={hp_change}, conditions_add={conditions_add}, conditions_remove={conditions_remove}"`) — actual execution is intercepted in `dm_turn()`.
  - [x] 1.5: Add `"dm_update_npc"` to `__all__` in `tools.py` ([tools.py:17-33](tools.py#L17-L33)) in alphabetical order (between `dm_update_character_sheet` and `dm_whisper_to_agent`).

- [x] **Task 2: Bind `dm_update_npc` to the DM agent** (AC: #2)
  - [x] 2.1: Add `dm_update_npc` to the imports at the top of `agents.py` near the existing `dm_update_character_sheet` import ([agents.py:48](agents.py#L48)).
  - [x] 2.2: Add `dm_update_npc` to the tool list in `create_dm_agent()` at [agents.py:821-829](agents.py#L821-L829), placed after `dm_update_character_sheet` for visual grouping.

- [x] **Task 3: Implement `_execute_npc_update()` helper in `agents.py`** (AC: #4, #5, #6, #7, #8, #14, #17, #18, #20)
  - [x] 3.1: Add the function immediately after `_execute_sheet_update` at [agents.py:2387-2439](agents.py#L2387-L2439).
  - [x] 3.2: Signature: `def _execute_npc_update(tool_args: dict[str, object], combat_state: CombatState) -> tuple[str, CombatState]`. Returns `(confirmation_string, possibly_updated_combat_state)`.
  - [x] 3.3: Extract args: `npc_name = str(tool_args.get("npc_name", ""))`, `hp_change = int(tool_args.get("hp_change", 0))`, `conditions_add = tool_args.get("conditions_add") or []`, `conditions_remove = tool_args.get("conditions_remove") or []`. Tolerate JSON-string `tool_args` like `_execute_sheet_update` does at [agents.py:2414-2422](agents.py#L2414-L2422).
  - [x] 3.4: Validate `combat_state.active` is `True`. If not → return `("Error: No combat is currently active.", combat_state)`.
  - [x] 3.5: Resolve `npc_name` to a profile key via `_sanitize_npc_name()` from [tools.py:768](tools.py#L768). If sanitized key not in `combat_state.npc_profiles`, attempt a fuzzy lookup (lowercase comparison against all profile `name` field values and keys). If still unresolved → return `("Error: NPC '<name>' not found in active combat. Available: <keys>", combat_state)`.
  - [x] 3.6: Compute new HP: `old_hp = npc.hp_current`, `new_hp = max(0, min(old_hp + hp_change, npc.hp_max))`.
  - [x] 3.7: Update conditions list with case-insensitive add (dedupe) and remove. Helper: pass through a small inline `_apply_npc_conditions(current, add, remove)` function or reuse `_apply_list_updates` pattern from tools.py if it fits without modification (read it first — likely needs minor adaptation since PC version uses `+`/`-` prefixes).
  - [x] 3.8: Build a new `NpcProfile` via `npc.model_copy(update={"hp_current": new_hp, "conditions": new_conditions})`. Build a new `CombatState` via `combat_state.model_copy(update={"npc_profiles": {**combat_state.npc_profiles, npc_key: new_npc}})`.
  - [x] 3.9: Construct confirmation string: if `new_hp == 0` → `f"Updated {npc.name}: HP {old_hp} -> 0 (defeated)"`; else → `f"Updated {npc.name}: HP {old_hp} -> {new_hp} ({hp_change:+d})"`. Append condition deltas if any: `". Conditions: +poisoned, -prone."`.
  - [x] 3.10: Return `(confirmation_string, new_combat_state)`.

- [x] **Task 4: Wire `_execute_npc_update()` into `dm_turn()` tool dispatch** (AC: #3, #8, #14)
  - [x] 4.1: In `dm_turn()` at [agents.py:1942-2030](agents.py#L1942-L2030), add a new `elif tool_name == "dm_update_npc":` branch immediately after the `dm_update_character_sheet` branch ([agents.py:1957-1966](agents.py#L1957-L1966)).
  - [x] 4.2: Determine the working combat state: use `updated_combat_state` if non-None (from a prior tool call in the same turn), else `state.get("combat_state", CombatState())`.
  - [x] 4.3: Call `tool_result, new_combat_state = _execute_npc_update(tool_args, working_combat_state)`.
  - [x] 4.4: If `tool_result` does not start with `"Error"`, assign `updated_combat_state = new_combat_state` (mirror Story 15-2's pattern at [agents.py:2007-2013](agents.py#L2007-L2013)).
  - [x] 4.5: If `tool_result` does not start with `"Error"`, append `tool_result` to `sheet_notifications` (the existing list at [agents.py:1900](agents.py#L1900)) so the `[SHEET]:` log entry is emitted by the existing notification loop at [agents.py:2112-2114](agents.py#L2112-L2114). This reuses the Story 8-5 notification mechanism — no new code needed for the log line.
  - [x] 4.6: Log via `logger.info("DM updated NPC: %s -> %s", tool_args, tool_result)` matching the sheet-update log format at [agents.py:1959-1963](agents.py#L1959-L1963).
  - [x] 4.7: Append the standard `ToolMessage(content=tool_result, tool_call_id=tool_id)` to `messages`, same as all other tools.

- [x] **Task 5: Inject combat-state section into `_build_dm_context()`** (AC: #9, #10, #19)
  - [x] 5.1: In `_build_dm_context()` at [agents.py:1367-1480](agents.py#L1367-L1480), insert the new combat-state block AFTER the character-sheets block (currently at [agents.py:1404-1409](agents.py#L1404-L1409)) and BEFORE the "Player Knowledge" block ([agents.py:1411-1421](agents.py#L1411-L1421)).
  - [x] 5.2: Read `combat = state.get("combat_state")`. Guard: `if not isinstance(combat, CombatState) or not combat.active: skip the block entirely`.
  - [x] 5.3: Build the section header: `f"## Active Combat — Round {combat.round_number}\n\n### NPCs (DM-controlled):"`.
  - [x] 5.4: Iterate over `initiative_order` in order, filtering to NPC entries (`entry.startswith("dm:")`). Dedupe by key (NPCs only appear once in `initiative_order` so trivial). If `npc_profiles` is empty, emit `- (no NPCs in this encounter)` (AC #19).
  - [x] 5.5: For each NPC, build a line: `f"- {npc.name}: HP {npc.hp_current}/{npc.hp_max}{status_label}{conditions_suffix}"`.
  - [x] 5.6: Status label logic (extract into a module-level helper `_npc_status_label(hp_current: int, hp_max: int) -> str` for testability):
    | hp_current | Label |
    |---|---|
    | `0` | ` (DEFEATED)` |
    | `> 0` and `<= 0.25 * hp_max` | ` (critically wounded)` |
    | `> 0.25 * hp_max` and `<= 0.75 * hp_max` | ` (wounded)` |
    | `> 0.75 * hp_max` and `< hp_max` | ` (lightly wounded)` |
    | `== hp_max` | `""` (empty) |
  - [x] 5.7: Conditions suffix: if `npc.conditions` non-empty → ` — conditions: {', '.join(npc.conditions)}`. Else → `""`.
  - [x] 5.8: Append the assembled block to `context_parts` (the local list at [agents.py:1379](agents.py#L1379)).
  - [x] 5.9: **CRITICAL**: Ensure the new code path is wholly gated on `combat.active is True`. There must be zero behavioral diff for exploration mode (any test that asserts pre-existing `_build_dm_context` output for non-combat states must still pass).

- [x] **Task 6: Add combat addendum to DM system prompt during combat** (AC: #11)
  - [x] 6.1: Define a new module-level template constant `DM_COMBAT_NARRATIVE_ADDENDUM` in `agents.py` near `DM_COMBAT_BOOKEND_PROMPT_TEMPLATE` ([agents.py:277-292](agents.py#L277-L292)):
    ```python
    DM_COMBAT_NARRATIVE_ADDENDUM = """
    ## Combat Damage Tracking — REQUIRED

    Combat is currently ACTIVE. You have a `dm_update_npc` tool — call it after PC actions resolve to record damage dealt to NPCs, conditions applied (poisoned, prone, frightened, etc.), and deaths. Use negative `hp_change` for damage and positive for healing.

    - Do NOT let an NPC at 0 HP continue acting.
    - When an NPC reaches 0 HP, narrate their defeat in the same response.
    - Refer to the "Active Combat — Round N" section in your context for the live HP and condition state of every NPC. The state shown there is authoritative — do not contradict it.
    """
    ```
  - [x] 6.2: In `dm_turn()` at [agents.py:1855-1868](agents.py#L1855-L1868), after the existing `_get_combat_turn_type()` branching, add:
    ```python
    # Story 15.7: append damage-tracking guidance on ALL combat turns
    combat_st = state.get("combat_state")
    if isinstance(combat_st, CombatState) and combat_st.active:
        system_prompt_parts.append(DM_COMBAT_NARRATIVE_ADDENDUM)
    ```
  - [x] 6.3: Export the template via `__all__` in `agents.py` ([agents.py:60-64](agents.py#L60-L64)) — add `"DM_COMBAT_NARRATIVE_ADDENDUM"` in alphabetical position (between `"DM_COMBAT_BOOKEND_PROMPT_TEMPLATE"` and `"DM_NPC_TURN_PROMPT_TEMPLATE"`).

- [x] **Task 7: Filter defeated NPCs from `route_to_next_agent()` in `graph.py`** (AC: #12, #13, #20)
  - [x] 7.1: In `route_to_next_agent()` at [graph.py:172-253](graph.py#L172-L253), modify the combat-routing branch (the block starting at [graph.py:222-247](graph.py#L222-L247)) so that, after computing `next_agent = order[current_idx]`, it checks whether `next_agent.startswith("dm:")` AND `combat.npc_profiles[npc_key].hp_current == 0`. If true → advance `current_idx` and read the next entry; loop until a live entry is found or `current_idx >= len(order)`.
  - [x] 7.2: When skipping defeated NPCs, the `current_initiative_index` must be advanced in the *returned* state too — otherwise the next routing call will re-read the same defeated slot. Achieve this by returning a routing-only signal (the function only returns a node name, not state) — instead, advance the index in the **DM node's return state** when it detects a defeated NPC turn (alternative). **Decision**: simplest approach is to skip in the routing function only (it loops to a live entry), and let the upstream node (e.g., the DM node returning at [agents.py:2156-2159](agents.py#L2156-L2159)) advance the index normally. The router's loop ensures the next live entry is chosen; the index advance happens once per successful turn. Document this choice clearly in code comments.
  - [x] 7.3: Edge case (AC #13): if ALL remaining entries from `current_idx` onward are defeated NPCs, the loop exits with `current_idx >= len(order)` → return `END` to close the round. (Story 15-8 will add an "all NPCs defeated → end combat" prompt; for 15-7, simply ending the round is correct behavior.)
  - [x] 7.4: PC entries (no `dm:` prefix) MUST never be skipped on this basis, even if a future PC has 0 HP — PC death handling is out of scope for this story.
  - [x] 7.5: Add a defensive `logger.debug` line when a defeated NPC slot is skipped: `logger.debug("route_to_next_agent: skipping defeated NPC slot %s", next_agent)`.

- [x] **Task 8: Write tests in `tests/test_story_15_7_npc_damage_tracking.py`** (AC: #21, #22, all functional ACs)
  - [x] 8.1: Create the file with class-based organization (project convention — see `tests/test_story_15_1_combat_state_model.py` for the reference structure).
  - [x] 8.2: `class TestDmUpdateNpcTool` — schema-level tests (5 tests):
    - Tool exists, is decorated with `@tool`, has correct signature.
    - Tool is in `__all__` of `tools.py`.
    - Tool is bound to the DM agent (inspect `create_dm_agent().bound.tools` or similar — see test patterns from Story 15-1 Task 11.10-11.12).
    - Tool returns a placeholder string when called directly (schema-only behavior).
    - Tool's signature uses `int` for `hp_change` with default `0`.
  - [x] 8.3: `class TestExecuteNpcUpdate` — helper unit tests (8 tests):
    - Damage path: full HP → wounded (`hp_change=-5`, hp_max=15 → hp_current=10).
    - Damage path: clamped to 0 (over-kill: `hp_change=-999` → hp_current=0).
    - Healing path: positive `hp_change` increases HP.
    - Healing path: clamped to hp_max (`hp_change=999`).
    - Conditions add: deduplicated case-insensitive.
    - Conditions remove: case-insensitive match.
    - Unknown NPC name → error string, state unchanged.
    - Combat inactive → error string, state unchanged.
  - [x] 8.4: `class TestCombatStateInjection` — `_build_dm_context()` tests (5 tests):
    - Combat inactive → no `## Active Combat` section.
    - Combat active with NPCs at full HP → section present, no status labels.
    - Combat active with mixed HP → correct status labels per AC #9 table.
    - Defeated NPC shows `(DEFEATED)`.
    - Empty `npc_profiles` with `active=True` → section emitted with `- (no NPCs in this encounter)`.
  - [x] 8.5: `class TestDefeatedNpcRouting` — `route_to_next_agent()` tests (4 tests):
    - One defeated NPC mid-order is skipped, next live entry returned.
    - Multiple consecutive defeated NPCs all skipped.
    - All remaining NPCs defeated → returns `END`.
    - Defeated NPC followed by live PC → PC's name returned (verifies PCs not skipped).
  - [x] 8.6: `class TestSheetNotifications` — integration tests for the `[SHEET]:` log entry (2 tests):
    - Successful damage call produces a `[SHEET]: Updated <name>: HP <old> -> <new> (-N)` entry.
    - Defeat call (HP → 0) produces a `[SHEET]: Updated <name>: HP <old> -> 0 (defeated)` entry.
  - [x] 8.7: `class TestPersistenceRoundTrip` — serialization regression (2 tests):
    - State with mutated `hp_current` round-trips through `serialize_game_state` → `deserialize_game_state` with no loss.
    - State with non-empty NPC `conditions` round-trips.
  - [x] 8.8: `class TestIntegrationSession017` — end-to-end scenario (1 test):
    - Set up a 3-NPC combat (Mist-Stalker Alpha/Beta/Gamma, all at hp_current=15/15). Issue three `dm_update_npc` calls reducing each to 0. Verify: (a) all three show `(DEFEATED)` in `_build_dm_context()` output, (b) `route_to_next_agent()` returns `END` when all NPC slots are next, (c) `[SHEET]:` log entries for all three are present in `ground_truth_log`.
  - [x] 8.9: All test classes mock LLM calls — use `unittest.mock.patch` against `create_dm_agent()` or pass a `Mock()` chat model. Follow existing fixture patterns from `tests/test_story_15_2_initiative_rolling.py` and `tests/test_story_15_4_dm_bookend_npc_turns.py`.
  - [x] 8.10: Use the standard `sample_game_state()` fixture pattern from the project — if absent in this file, build one matching `tests/test_story_15_1_combat_state_model.py`. Include `combat_state=CombatState(active=True, ...)` for combat tests.

- [x] **Task 9: Verify no pre-existing tests regress** (AC: #22)
  - [x] 9.1: Run `python -m pytest tests/test_story_15_*.py -v` and confirm all Story 15-1 through 15-6 tests still pass.
  - [x] 9.2: Run `python -m pytest tests/test_agents.py tests/test_persistence.py tests/test_models.py -v` to catch any DM-context or serialization regressions.
  - [x] 9.3: Spot-check `tests/test_story_8_4_dm_tool_calls.py` and `tests/test_story_8_5_sheet_notifications.py` — the `[SHEET]:` notification pipeline this story reuses MUST still pass.
  - [x] 9.4: Run `python -m ruff check tools.py agents.py graph.py tests/test_story_15_7_npc_damage_tracking.py` and `python -m ruff format` the same files.

## Dev Notes

### File-by-file modification map

| File | Lines (current) | Change |
|---|---|---|
| `tools.py` | 17–33 | Add `"dm_update_npc"` to `__all__` (alphabetical) |
| `tools.py` | after 714 (after `dm_update_character_sheet`) | Add `@tool`-decorated `dm_update_npc()` (~35 LoC) |
| `agents.py` | 48 | Add `dm_update_npc` to the existing `from tools import ...` block |
| `agents.py` | 60–64 (`__all__`) | Add `"DM_COMBAT_NARRATIVE_ADDENDUM"` |
| `agents.py` | 277–292 area | Add `DM_COMBAT_NARRATIVE_ADDENDUM` template constant (~10 LoC) |
| `agents.py` | 1367–1480 (`_build_dm_context`) | Insert combat-state section between sheets block and player-knowledge block (~30 LoC) |
| `agents.py` | new module-level helper | Add `_npc_status_label(hp_current, hp_max) -> str` (~10 LoC) |
| `agents.py` | 1855–1868 (`dm_turn` system prompt assembly) | Append `DM_COMBAT_NARRATIVE_ADDENDUM` when combat active (~5 LoC) |
| `agents.py` | 1942–2030 (`dm_turn` tool dispatch) | Add `dm_update_npc` branch (~12 LoC) |
| `agents.py` | 821–829 (`create_dm_agent`) | Add `dm_update_npc` to bound tools list (1 line) |
| `agents.py` | after 2439 (after `_execute_sheet_update`) | Add `_execute_npc_update()` helper (~50 LoC) |
| `graph.py` | 222–247 (`route_to_next_agent` combat branch) | Add defeated-NPC skip loop (~12 LoC) |
| `tests/test_story_15_7_npc_damage_tracking.py` | NEW | ~25 tests, class-based (~300 LoC) |

**Total estimated:** ~175 LoC production + ~300 LoC tests. Aligns with the proposal's "~150–250 LoC + ~25 tests" estimate.

### Files NOT to Modify

- **`models.py`** — `NpcProfile.hp_current: int = Field(default=1, ge=0)` already supports the defeated state (verified [models.py:846-848](models.py#L846-L848)). No model changes required for 15-7. (Story 15-8 may add a `defeated_at_turn: int | None` field — out of scope here.)
- **`persistence.py`** — Existing `model_dump()`-based serialization handles mutated `hp_current` and `conditions` automatically.
- **`memory.py`** — No memory-system changes.
- **Frontend (`frontend/`)** — NPC HP remains DM-private per the existing design decision (see proposal Section 2 / "Artifact Conflicts" / UI/UX row). UI surfacing of NPC HP is explicitly out of scope.

### Mirror Pattern: `dm_update_character_sheet` (Story 8-4)

The closest analog to this story's `dm_update_npc` tool is the existing `dm_update_character_sheet` tool from Story 8-4. Use it as the *exact template* for:

1. **Tool definition pattern** at [tools.py:671-714](tools.py#L671-L714): `@tool` decorator, docstring with examples, function body returns placeholder, comment `# This tool's execution is intercepted in dm_turn()...`.
2. **Tool interception pattern** at [agents.py:1957-1966](agents.py#L1957-L1966): `elif tool_name == "dm_update_character_sheet":` → `tool_result = _execute_sheet_update(tool_args, updated_sheets)` → append to `sheet_notifications` if non-error.
3. **Helper function pattern** at [agents.py:2387-2439](agents.py#L2387-L2439) (`_execute_sheet_update`): signature `(tool_args, mutable_collection) -> str`, parse JSON if needed, validate, mutate via `model_copy()`, return confirmation string.
4. **Notification pattern** at [agents.py:2112-2114](agents.py#L2112-L2114): the existing loop `for notification in sheet_notifications: new_log.append(f"[SHEET]: {notification}")` is reused — `_execute_npc_update`'s confirmation string just needs to be appended to the same `sheet_notifications` list.

**Key difference from PC sheets**: NPC state lives in `combat_state.npc_profiles` (a Pydantic field of a Pydantic field of GameState), not in the top-level `character_sheets` dict. So the working data structure passed into `_execute_npc_update` is a `CombatState` (immutable Pydantic) and the helper must return a *new* `CombatState`. The PC helper mutates a dict in place — DO NOT copy that mutability pattern for NPCs; Pydantic immutability is the established convention for `combat_state` (see `_execute_start_combat` / `_execute_end_combat` patterns).

### Reference: `_execute_start_combat` initializes `hp_current`

At [agents.py:2491](agents.py#L2491), the NPC is constructed:
```python
npc_profiles[key] = NpcProfile(
    name=str(name),
    initiative_modifier=int(p.get("initiative_modifier", 0)),
    hp_max=hp,
    hp_current=hp,   # <-- THIS is the field 15-7 will mutate over time
    ac=int(p.get("ac", 10)),
    ...
)
```

This is the ONLY place `hp_current` is written today. After Story 15-7 lands, `_execute_npc_update()` becomes the second writer. No other code path should write to `hp_current` directly — funnel all mutations through `_execute_npc_update()` to ensure consistent clamping and notification.

### Combat-state injection — placement rationale

The new "Active Combat — Round N" section must be placed in `_build_dm_context()` between:
- **After** the character sheets block ([agents.py:1404-1409](agents.py#L1404-L1409)) — so the DM sees PC state first (as the actor of the previous turn was a PC most of the time during combat), then sees what damage they need to apply to NPCs.
- **Before** the player knowledge block ([agents.py:1411-1421](agents.py#L1411-L1421)) — so the live combat state is prominent in the prompt, not buried below memory snippets.

This placement keeps the existing exploration-mode context structure intact (when `combat.active is False`, the section is omitted and the rest of the function is unchanged).

### Why this story does NOT introduce `defeated: bool` on `NpcProfile`

The proposal's "Models" row in Section 2 mentions adding `NpcProfile.defeated: bool = False` and/or `defeated_at_turn: int | None` as an **option**. This story deliberately does NOT add those fields because:

1. `hp_current == 0` is *already* a load-bearing defeated marker (the `Field(ge=0)` validator is explicit about this).
2. Adding `defeated` as a derived boolean would create a second source of truth that could drift from `hp_current`. The PC analog (`CharacterSheet`) doesn't have a `defeated` field either — it relies on `hit_points_current == 0`.
3. Story 15-8 (auto-detect encounter resolution) may want a `defeated_at_turn` field for "when did this NPC die" tracking. Defer that decision to 15-8 where the use case is concrete.

### Existing combat-context plumbing this story complements

The DM already has *some* combat-state visibility on specific turn types:

| Turn type | Existing source | Existing function |
|---|---|---|
| Bookend (round start) | Per-NPC HP line in combatant summary | `_build_combatant_summary()` at [agents.py:1665-1710](agents.py#L1665-L1710) |
| NPC-control turn | Single NPC's full profile (HP, AC, personality, tactics, conditions) | `_build_npc_turn_prompt()` at [agents.py:1737-1778](agents.py#L1737-L1778) |
| **Regular narrative turn (PC just acted, DM narrating consequence)** | **NOTHING — the gap this story fills** | (new — `_build_dm_context()` injection) |

The new section in `_build_dm_context()` is the THIRD place NPC HP appears to the DM. The data source (`combat_state.npc_profiles`) is the same in all three places — they read from the single source of truth, they don't synthesize new state.

### Routing edge case: defeated NPC AT `current_initiative_index`

Today, `route_to_next_agent()` ([graph.py:222-247](graph.py#L222-L247)) reads `next_agent = order[current_idx]`. If `next_agent == "dm:goblin_1"` and Goblin 1 is at 0 HP, today's code routes to the DM node, which then narrates Goblin 1's "action" (which is the bug Session 017 hit — defeated enemies kept attacking).

Story 15-7's fix loops within the function:
```python
while current_idx < len(order):
    next_agent = order[current_idx]
    if next_agent.startswith("dm:") and combat.npc_profiles.get(next_agent[3:], None) and combat.npc_profiles[next_agent[3:]].hp_current == 0:
        logger.debug("route_to_next_agent: skipping defeated NPC slot %s", next_agent)
        current_idx += 1
        continue
    break
else:
    return END

# next_agent is now a live entry
```

**Critical**: this loop only advances the local `current_idx` for the purpose of finding the next live entry. The persistent `combat_state.current_initiative_index` is advanced by the consuming node (DM or PC turn) at the end of *its* execution, as it does today (see [agents.py:2156-2159](agents.py#L2156-L2159) for the DM advance, [graph.py:326-330](graph.py#L326-L330) for the human-intervention advance). The router's loop just ensures the next valid entry's name is returned; the index update is the node's responsibility.

If we ever need the router to *persist* the skip, we'd need to update the routing-and-state interaction model — that's a larger refactor and explicitly out of scope. For this story, the loop-in-router approach is sufficient because each defeated-NPC skip is followed by a real node execution that advances the index.

### Tool docstring requirements (Task 1.2-1.3)

The tool docstring is the DM model's primary interface to learn this tool's contract. It MUST include:

1. **Delta semantics in the FIRST paragraph**: "`hp_change` is a delta. Negative values apply damage (e.g., -7 means the NPC took 7 damage). Positive values heal."
2. **Clamping behavior**: "HP is clamped to `[0, hp_max]`. Overkill values do not produce negative HP."
3. **Defeat semantics**: "When `hp_current` reaches 0, the NPC is marked defeated and will be skipped in subsequent rounds. Narrate the defeat in the same response."
4. **At least 3 usage examples**:
   ```
   - Damage: dm_update_npc(npc_name="Goblin 1", hp_change=-7)
   - Heal: dm_update_npc(npc_name="Mist-Stalker Alpha", hp_change=5)
   - Defeat + condition: dm_update_npc(npc_name="Klarg", hp_change=-12, conditions_add=["unconscious"])
   - Remove condition: dm_update_npc(npc_name="Spider", conditions_remove=["webbed"])
   ```

### Test fixtures — sample_game_state for combat

Existing combat tests use a pattern like:
```python
def sample_combat_state(active: bool = True) -> CombatState:
    return CombatState(
        active=active,
        round_number=2,
        initiative_order=["dm", "shadowmere", "dm:mist-stalker_alpha", "thorin", "dm:mist-stalker_beta"],
        initiative_rolls={"shadowmere": 17, "dm:mist-stalker_alpha": 15, "thorin": 12, "dm:mist-stalker_beta": 10},
        original_turn_queue=["dm", "shadowmere", "thorin"],
        npc_profiles={
            "mist-stalker_alpha": NpcProfile(name="Mist-Stalker Alpha", hp_max=15, hp_current=15, ac=13),
            "mist-stalker_beta": NpcProfile(name="Mist-Stalker Beta", hp_max=15, hp_current=15, ac=13),
        },
        current_initiative_index=0,
    )
```

Reuse this pattern in the new test file. Reference [tests/test_story_15_2_initiative_rolling.py](tests/test_story_15_2_initiative_rolling.py) and [tests/test_story_15_4_dm_bookend_npc_turns.py](tests/test_story_15_4_dm_bookend_npc_turns.py) for similar fixtures.

### Mocking LLMs in tests

For the DM-context integration tests, mock `create_dm_agent` to return a `Mock()` chat model. The new `_build_dm_context()` code path is pure — no LLM involved — so most tests need NO mocking. The integration test for `dm_turn()` tool dispatch needs a chat-model mock that returns a tool call followed by a text response (standard pattern from `tests/test_story_8_4_dm_tool_calls_for_sheet_updates.py`).

### Project Structure Notes

- All models in `models.py` (flat layout, no separate files) — no changes needed here.
- All tools in `tools.py` (flat layout) — `dm_update_npc` goes here.
- All agent helpers in `agents.py` (flat layout) — `_execute_npc_update` and `_npc_status_label` go here.
- Graph routing in `graph.py` — defeated-NPC skip loop goes here.
- Tests in `tests/` with `test_story_{epic}_{story}_{name}.py` naming.
- Uses `python -m pytest` and `python -m ruff` (uv not on PATH in MINGW64 — per MEMORY.md "Dev Tooling" note).
- Class-based test organization (project convention — see Story 15-1 Task 11 for the canonical reference).

### Naming conventions

- Tool: `dm_update_npc` (snake_case, matches `dm_update_character_sheet` precedent).
- Helper: `_execute_npc_update` (underscore prefix marks internal, matches `_execute_sheet_update`).
- Status label helper: `_npc_status_label` (underscore prefix, descriptive).
- Template constant: `DM_COMBAT_NARRATIVE_ADDENDUM` (SCREAMING_SNAKE_CASE for module-level template strings, matches `DM_COMBAT_BOOKEND_PROMPT_TEMPLATE`).
- Confirmation prefix in `[SHEET]:` log: `"Updated <NPC name>: HP X -> Y (delta)"` — mirrors PC pattern from [tools.py:481-483](tools.py#L481-L483).

### Edge cases checklist

- [x] hp_change = 0 → no-op (still emits a confirmation, may or may not emit `[SHEET]:` entry; recommendation: emit only if conditions changed or hp_change != 0)
- [x] Over-kill (hp_change = -999) → clamped to 0
- [x] Over-heal (hp_change = 999) → clamped to hp_max
- [x] Negative `hp_change` on already-defeated NPC → no-op (already at 0)
- [x] Positive `hp_change` on defeated NPC (revive) → HP increases above 0, NPC re-enters initiative
- [x] Conditions add with duplicate (case-insensitive) → no dupe
- [x] Conditions remove not in list → no-op (no error)
- [x] Unknown NPC name → error string
- [x] Combat inactive → error string
- [x] Empty npc_profiles → context section shows "(no NPCs in this encounter)"
- [x] All NPCs defeated → router skips all, returns END
- [x] Defeated NPC followed by PC in initiative_order → router skips NPC, returns PC name
- [x] Tool called by mistake during exploration → returns error, state unchanged
- [x] Persistence round-trip of mutated hp_current and conditions → preserved exactly

### References

**Live code (current state — verified read 2026-05-15):**
- [Source: models.py#NpcProfile L832-L860] — Target Pydantic model. `hp_current: int = Field(default=1, ge=0)` already supports defeated state.
- [Source: models.py#CombatState L863-L896] — Container. `npc_profiles: dict[str, NpcProfile]` is the mutable field.
- [Source: tools.py#dm_update_character_sheet L671-L714] — Template tool pattern.
- [Source: tools.py#apply_character_sheet_update L440-L539] — Template helper (case-insensitive conditions handling at L496-L512).
- [Source: tools.py#_sanitize_npc_name L768-L770] — Reuse for npc_name → key resolution.
- [Source: tools.py#__all__ L17-L33] — Add `"dm_update_npc"`.
- [Source: agents.py#_build_dm_context L1367-L1480] — Inject new combat-state section between L1409 (sheets block end) and L1411 (player knowledge block start).
- [Source: agents.py#_build_combatant_summary L1665-L1710] — Reference: existing NPC HP rendering pattern (bookend turns only).
- [Source: agents.py#_build_npc_turn_prompt L1737-L1778] — Reference: per-NPC profile rendering on NPC turns.
- [Source: agents.py#dm_turn L1781-L2203] — Hook tool interception (L1942-L2030) and system-prompt assembly (L1855-L1868).
- [Source: agents.py#_execute_sheet_update L2387-L2439] — Template for `_execute_npc_update`.
- [Source: agents.py#_execute_start_combat L2442-L2538, esp. L2491] — Original initializer of `hp_current=hp_max`.
- [Source: agents.py#create_dm_agent L808-L830] — Add `dm_update_npc` to bound tools list at L821-L829.
- [Source: agents.py#DM_COMBAT_BOOKEND_PROMPT_TEMPLATE L277-L292] — Pattern for new `DM_COMBAT_NARRATIVE_ADDENDUM` template.
- [Source: agents.py#__all__ L60-L64] — Add `"DM_COMBAT_NARRATIVE_ADDENDUM"`.
- [Source: agents.py#SHEET notification loop L2112-L2114] — Existing `[SHEET]:` log emission this story reuses.
- [Source: graph.py#route_to_next_agent L172-L253, esp. combat branch L222-L247] — Add defeated-NPC skip loop.
- [Source: graph.py#current_initiative_index advancement L326-L330] — Pattern: index advance lives on the consuming node, not the router.

**Story precedents:**
- [Source: _bmad-output/implementation-artifacts/stories/15-1-combat-state-model.md] — Combat state model foundation. Format and class-based test conventions.
- [Source: _bmad-output/implementation-artifacts/stories/15-2-initiative-rolling.md] — `_execute_start_combat` pattern (Pydantic immutability via `model_copy`).
- [Source: _bmad-output/implementation-artifacts/stories/15-3-combat-aware-routing.md] — `route_to_next_agent` combat-aware path.
- [Source: _bmad-output/implementation-artifacts/stories/15-4-dm-bookend-npc-turns.md] — `_build_combatant_summary`, `_build_npc_turn_prompt`, `DM_COMBAT_BOOKEND_PROMPT_TEMPLATE`.
- [Source: _bmad-output/implementation-artifacts/stories/15-6-combat-end-conditions.md] — `max_combat_rounds` safety valve (orthogonal to this story).

**Design specification:**
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-15.md#Section 4 Story 15-7] — Authoritative spec for this story (10 ACs in proposal, expanded to 22 here for implementation precision).
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-05-15.md#Section 1] — Forensic evidence from Session 017 Mist-Stalker incident.

**Tests to reuse / regress against:**
- [Source: tests/test_story_15_1_combat_state_model.py] — Class-based test reference (37 tests, canonical Story 15 test structure).
- [Source: tests/test_story_15_2_initiative_rolling.py] — Combat-state fixture pattern.
- [Source: tests/test_story_15_4_dm_bookend_npc_turns.py] — Mock chat-model patterns for DM context tests.
- [Source: tests/test_story_8_4_dm_tool_calls_for_sheet_updates.py] — Mock chat-model with tool-call response pattern (the template for Task 8.3's tool-dispatch tests).
- [Source: tests/test_story_8_5_sheet_notifications.py] — `[SHEET]:` log entry assertion pattern.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) — claude-opus-4-7[1m]. Executed within the BMAD `dev-story` workflow as a sub-agent of the autodungeon epic-dev-cycle.

### Debug Log References

- `python -m pytest tests/test_story_15_7_npc_damage_tracking.py -xvs` — 51 tests, all passing in ~53s on first run.
- `python -m pytest tests/test_agents.py::TestModuleExports::test_all_public_symbols_exported` — initially failed because `__all__` was extended; updated the snapshot fixture in `tests/test_agents.py` to include the three new exports (`DM_COMBAT_NARRATIVE_ADDENDUM`, `_execute_npc_update`, `_npc_status_label`). Now passing.
- `python -m ruff check tools.py agents.py tests/test_story_15_7_npc_damage_tracking.py` — clean. (The pre-existing UP035 warning in `graph.py:18` is unrelated to this story.)
- Pre-existing failures confirmed orthogonal via `git stash` round-trip: `test_models.py`/`test_agents.py` failures stem from `defaults.yaml` provider/model defaults drift (Tactical vs Narrative, gemini-3 vs gemini-1.5), not from Story 15.7.

### Completion Notes List

- All 22 acceptance criteria implemented and verified.
- Tool `dm_update_npc` added to `tools.py` with delta-semantics docstring, 5 usage examples, and `int hp_change=0` / `list[str] | None = None` default args. Schema test verifies it's bound to the DM agent via `create_dm_agent()`.
- `_execute_npc_update()` mutates `NpcProfile.hp_current` and conditions exclusively via `model_copy(update=...)` — no in-place mutation. HP clamped to `[0, hp_max]`. Conditions add/remove are case-insensitive with dedupe.
- `_build_dm_context()` now emits an `## Active Combat — Round N` section (with NPC HP/status labels and condition suffixes) between the character sheets block and the player-knowledge block — but ONLY when `combat_state.active is True`. Exploration mode unchanged (regression test included).
- `_npc_status_label()` helper produces `(DEFEATED)` / `(critically wounded)` / `(wounded)` / `(lightly wounded)` / `""` per the AC #9 threshold table.
- `DM_COMBAT_NARRATIVE_ADDENDUM` is appended to the DM system prompt on EVERY DM turn while combat is active (regular narrative, bookend, NPC-control). Verified via mock-LLM test that captures the assembled prompt.
- `route_to_next_agent()` now loops past defeated NPC slots (`dm:<key>` where `hp_current == 0`) and returns `END` if all remaining entries are dead NPCs. PC entries are never skipped on this basis. The persistent `combat_state.current_initiative_index` is still advanced by the consuming node, as before — the router's loop only advances a local copy to find the next live entry.
- `dm_turn()` tool dispatch wires `dm_update_npc` calls through `_execute_npc_update()`, captures the updated `CombatState`, and reuses the Story 8.5 `[SHEET]:` notification pipeline (no new log-emission code).
- 51 tests added (target was >=25). Test classes: `TestDmUpdateNpcTool` (6), `TestExecuteNpcUpdate` (10), `TestCombatStateInjection` (9), `TestNpcStatusLabel` (6), `TestDefeatedNpcRouting` (6), `TestSheetNotifications` (3), `TestPersistenceRoundTrip` (3), `TestIntegrationSession017` (2), `TestSystemPromptAddendum` (3), `TestNpcNameSanitization` (3).
- One small extension beyond the spec: `_execute_npc_update()` includes a fuzzy fallback lookup against profile display names (not just sanitized keys) so DM-supplied "Mist-Stalker Alpha" resolves to the `mist-stalker_alpha` key even if `_sanitize_npc_name()` produces a slightly different sanitization. Task 3.5 explicitly authorized this fallback.
- No production model changes required (`NpcProfile.hp_current` already supports `0` defeated state via `Field(ge=0)`); no persistence changes required (existing `model_dump()` path serializes mutated state correctly — regression test included).

### File List

**New files:**

- `tests/test_story_15_7_npc_damage_tracking.py` — 51-test suite covering all 22 ACs.

**Modified files:**

- `tools.py` — Added `dm_update_npc` to `__all__` (alphabetical position) and added the `@tool`-decorated function with delta-semantics docstring (~50 LoC).
- `agents.py` —
  - Added `dm_update_npc` to `from tools import ...`.
  - Added `DM_COMBAT_NARRATIVE_ADDENDUM`, `_execute_npc_update`, `_npc_status_label` to `__all__`.
  - Added `DM_COMBAT_NARRATIVE_ADDENDUM` template constant.
  - Added `_npc_status_label()` helper.
  - Injected combat-state section into `_build_dm_context()` (active-only).
  - Appended `DM_COMBAT_NARRATIVE_ADDENDUM` to `dm_turn()` system prompt assembly on all active-combat turns.
  - Added `dm_update_npc` branch in the tool-dispatch loop with `_execute_npc_update()` call and `sheet_notifications` append.
  - Added `dm_update_npc` to `create_dm_agent()` bound tool list.
  - Added `_execute_npc_update()` helper (~140 LoC) immediately before `_execute_start_combat()`.
- `graph.py` — Added defeated-NPC skip loop in the combat-routing branch of `route_to_next_agent()` (~20 LoC).
- `tests/test_agents.py` — Extended `TestModuleExports.test_all_public_symbols_exported` snapshot with the three new exports.

### Change Log

| Date       | Change                                                       |
|------------|--------------------------------------------------------------|
| 2026-05-15 | Story 15.7 implemented. 51 tests added, all passing.         |
| 2026-05-15 | Adversarial code review (Opus 4.7). Found 1 HIGH, 1 MEDIUM, 5 LOW issues. HIGH and MEDIUM auto-fixed; 2 LOW auto-fixed; 3 LOW deferred. +2 regression-guard tests. Final: 53 tests passing. |

## Code Review (2026-05-15)

Adversarial Senior Developer code review (BMAD `code-review` workflow). Reviewer: Claude Opus 4.7 (1M context). Scope: `tools.py` (additions), `agents.py` (additions), `graph.py` (additions), `tests/test_story_15_7_npc_damage_tracking.py` (51 tests), `tests/test_agents.py` (snapshot update).

### Findings Summary

| Severity | Count | Auto-fixed | Deferred |
| -------- | ----- | ---------- | -------- |
| HIGH     | 1     | 1          | 0        |
| MEDIUM   | 1     | 1          | 0        |
| LOW      | 5     | 2          | 3        |

### HIGH-1: Defeated-NPC routing skip is not synchronized with `current_initiative_index`

**Severity:** HIGH (the bug Story 15-7 was meant to fix in the first place)
**File:** `agents.py` `dm_turn()` line ~1909, `pc_turn()` line ~2926
**Discovery:** The pre-flagged risk #2 escalated. Verified by direct reproduction.

**Original behavior:** `route_to_next_agent()` skips defeated NPC slots only in a LOCAL `current_idx` variable and returns the routing target string. But the consuming nodes (`dm_turn`, `pc_turn`) read the *persistent* `combat_state.current_initiative_index` to determine which combatant is acting:

- `dm_turn` at line 1909: `idx = combat_st.current_initiative_index` then `state["current_turn"] = combat_st.initiative_order[idx]`. When the router skipped from idx=1 (dead NPC) to idx=3 (live NPC) and routed to "dm" for the live NPC, `dm_turn` still read `state.combat.current_initiative_index = 1` and set `current_turn = "dm:<dead_npc_key>"` — playing the *dead* NPC's turn.
- After processing, the index was advanced by +1 to a still-defeated slot. Next routing call would re-skip, but again to a stale index.

**Reproduction confirmed in isolation** before the fix: with `initiative_order = ['dm', 'dm:g1', 'dm:g2', 'dm:g3', 'shadowmere']`, all goblins dead, `current_initiative_index=1` — `route_to_next_agent` returns `"dm"` (router thinks g3 should act), but `dm_turn` sets `current_turn = "dm:g1"` (the dead one). This is precisely the Session 017 Mist-Stalker incident the story was designed to fix.

**Test coverage gap:** The 6 tests in `TestDefeatedNpcRouting` only validate `route_to_next_agent` in isolation. None of them exercise the router-plus-consuming-node integration, so this bug shipped despite 51 passing tests.

**Fix (auto-applied):**

1. **`agents.py` `dm_turn()` lines 1900-1940:** Before reading the persistent index, advance it past defeated NPC slots and persist the alignment back into `state["combat_state"]`. This mirrors the router's local skip loop and ensures the +1 advancement at the end of the turn lands on the correct next entry.
2. **`agents.py` `pc_turn()` lines 2933-2960:** When `pc_turn` is called for a PC (the router having skipped defeated NPCs to find it), scan forward from `current_initiative_index` to locate the actual position of the named PC in `initiative_order` and persist that index before advancing.

**Regression guards added (2 new tests):**

- `TestPersistentIndexSync.test_dm_turn_advances_past_defeated_when_persistent_idx_is_stale`: verifies `dm_turn` realigns the index past defeated NPCs and that `current_turn` reflects a live NPC after the call.
- `TestPersistentIndexSync.test_pc_turn_aligns_index_when_router_skipped_defeated`: verifies `pc_turn` aligns its persistent index to its actual slot before advancing.

Both new tests **fail** when the fix is reverted (verified by surgical revert), confirming they catch the regression.

### MEDIUM-1: `_execute_npc_update` parameter type annotation lies about JSON-string args

**Severity:** MEDIUM
**File:** `agents.py:2573-2615`
**Discovery:** Pre-flagged risk #1, confirmed by pyright (`# type: ignore[unreachable]` on the JSON-string isinstance check).

**Original code:** Parameter typed `tool_args: dict[str, object]`, but the implementation runs `isinstance(tool_args, str)` and JSON-decodes when LangChain passes a string. The type checker marks this `# type: ignore[unreachable]`. Misleading for future maintainers and breaks strict-mode type checks.

**Fix (auto-applied):** Widened the annotation to `dict[str, object] | str` and refactored the JSON-decode branch as a clean union dispatch (`if isinstance(tool_args, str): … else: parsed_args = tool_args`). Removed the `type: ignore` directive. Pyright now type-checks both branches naturally. Tests still pass (the union path was already being exercised at runtime).

### LOW Issues

#### LOW-1: Redundant `elif` branch in confirmation-string assembly — AUTO-FIXED

**File:** `agents.py:2714-2718` (was). Both `if new_hp == 0 and old_hp != 0` and `elif new_hp == 0 and old_hp == 0` produced **identical** output (`f"Updated {npc.name}: HP {old_hp} -> 0 (defeated)"`). Collapsed to a single `if new_hp == 0` branch.

#### LOW-2: Noisy "(+0)" suffix on no-op `hp_change=0` calls — AUTO-FIXED

**File:** `agents.py:2720-2722` (was). When the DM called the tool with `hp_change=0` (e.g., for conditions-only updates), the output was `"Updated G1: HP 15 -> 15 (+0)"`. The story's edge-cases checklist explicitly recommended omitting the noisy delta for no-op HP changes. Added a special-case branch that emits `"Updated G1: HP 15 -> 15"` when `hp_change == 0` and HP didn't actually change.

#### LOW-3: Combat addendum prompt bloat on NPC-control turns — DEFERRED

**File:** `agents.py:1969-1973` (pre-flagged risk #3). `DM_COMBAT_NARRATIVE_ADDENDUM` is appended on ALL combat turns including NPC-control turns where the per-NPC prompt already exists. This is **explicitly required by AC #11** ("on all DM turns during active combat … not just bookends"), so any change would violate the spec. Documented for future epic if prompt-size becomes a concern.

#### LOW-4: Overly defensive test assertion — DEFERRED

**File:** `tests/test_story_15_7_npc_damage_tracking.py:391-395`. The `test_full_hp_shows_no_status_label` assertion uses an unusual `or` short-circuit:

```python
assert "Mist-Stalker Alpha: HP 15/15\n" in ctx + "\n" or (
    "Mist-Stalker Alpha: HP 15/15" in ctx
    and "(DEFEATED)" not in ctx
    and "(wounded)" not in ctx
)
```

The pattern is ugly but the test passes correctly. Deferred — refactor would touch test logic without changing coverage.

#### LOW-5: Pyright "Unnecessary isinstance" warnings — DEFERRED

**File:** `agents.py:1470`, `agents.py:1910`, `agents.py:2941`. Defensive `isinstance(combat_state, CombatState)` checks where `state.get("combat_state")` returns `CombatState | None`. The isinstance handles the None case implicitly. Pattern is consistent with `_get_combat_turn_type` and other combat-aware code in the file. Refactoring to `if combat_state is not None and combat_state.active` would diverge from established style. Deferred.

### Pre-flagged risks resolution

| Risk                                         | Status                                                                          |
| -------------------------------------------- | ------------------------------------------------------------------------------- |
| #1 MEDIUM: JSON-string args type annotation  | **Confirmed; auto-fixed** (MEDIUM-1)                                            |
| #2 MEDIUM: Router skip not persisted         | **Escalated to HIGH; auto-fixed** (HIGH-1)                                      |
| #3 LOW: Addendum on NPC-control turns        | **Confirmed; deferred** (LOW-3, AC-mandated)                                    |
| #4 LOW: 25%/75% boundary off-by-one          | **Investigated; no issue** (verified `<=` semantics produce documented behavior) |

### Final Status

- **Tests (Story 15.7):** 53 passing (51 original + 2 regression-guards). 0 failing.
- **Tests (broader regression set):** Same 20 pre-existing failures as baseline (`test_story_15_3` 7, `test_story_15_4` 7, `test_models.py` config-drift, others) — confirmed orthogonal to Story 15.7 via `git stash -u` round-trip. **No new regressions.**
- **Tests (Story 8.4 / 8.5 SHEET pipeline):** 244 passing.
- **Ruff:** Clean apart from the pre-existing UP035 warning in `graph.py:18` (unrelated to this story).
- **Ruff format:** Applied to `agents.py`, `tools.py`, `graph.py`. No semantic changes.
- **Pyright:** Same pattern of warnings as the rest of `agents.py` (LangChain partial-types, defensive isinstance). No new strict-mode errors introduced by Story 15.7's code.

### Verdict

Story 15.7 is **ready for commit** with the fixes applied. The HIGH-severity bug (the very issue Story 15.7 was meant to solve) would have re-emerged in production despite all 51 original tests passing — the bug lived in the integration seam between the router and the consuming nodes. The added `TestPersistentIndexSync` class plugs that integration-test gap.
