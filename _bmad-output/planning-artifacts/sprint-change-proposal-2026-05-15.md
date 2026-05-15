# Sprint Change Proposal: NPC Damage Tracking & DM Combat-State Awareness

**Date:** 2026-05-15
**Triggered by:** Live gameplay observation during Session 017 (Aethelgard ruins, Qwen 3.6 campaign)
**Scope:** Minor — Two new stories within existing Epic 15 (Combat Initiative System)
**Risk:** Low–Medium

---

## Section 1: Issue Summary

During an overnight autopilot run of Session 017, a Mist-Stalker combat encounter that began at game turn 9 ran for **101+ consecutive turns without resolving**, and the autopilot was eventually halted at a 100-turn safety threshold by the external monitor — *not* by any in-engine logic.

Forensic analysis of the saved checkpoint at `campaigns/session_017/turn_110.json` revealed:

| Signal | Count / Value |
|---|---|
| Total log entries | 110 |
| `damage / wound / strike` keyword mentions | 201 |
| `kill / die / defeat / slain` keyword mentions | 6 |
| `combat_state.active` | `True` |
| `combat_state.round_number` | 8 |
| `combat_state.npc_profiles["mist-stalker_alpha"].hp_current` | **15/15** (full) |
| `combat_state.npc_profiles["mist-stalker_beta"].hp_current` | **15/15** (full) |
| `combat_state.npc_profiles["mist-stalker_gamma"].hp_current` | **15/15** (full) |
| `game_config.max_combat_rounds` | 50 (safety valve, didn't trigger because round_number is only 8) |

The DM **narratively** "killed" the Alpha at turn 57 ("dies") and again at turn 91 ("killed"), and Gamma at turn 30 ("killed") — but each "killed" enemy continued attacking PCs in subsequent turns. Qwen 3.6 produces high-quality combat prose but cannot maintain HP/death state across turns when the structured state contradicts the narrative.

### Root Cause (verified via code inspection)

1. **NPC `hp_current` is never decremented anywhere in the codebase.** It is set once at combat start in `_execute_start_combat()` ([agents.py:2491](agents.py#L2491)) and no code path mutates it thereafter. There is no equivalent of `dm_update_character_sheet` for NPCs.

2. **The DM's main turn prompt (`_build_dm_context`, [agents.py:1367-1480](agents.py#L1367-L1480)) contains zero combat-state information.** Combat HP and initiative data are injected only on (a) NPC-specific turns via `_build_npc_turn_prompt` and (b) round-bookend turns via `_build_combatant_summary` — *not* during regular narrative DM turns. So when the DM is narrating "Aurelia strikes the Alpha", it has no current view of the Alpha's HP, recent damage history, or which NPCs are dead.

3. **Even on NPC turns where HP IS shown, it always reads "15/15"** because of bug #1, so the DM perceives no progress regardless.

This is a critical narrative-coherence bug for any combat-heavy session. It does not affect short combats (which finish via DM narrative beats before the inconsistency becomes obvious) but breaks every prolonged tactical encounter.

---

## Section 2: Impact Analysis

### Epic Impact

- **Epic 15 (Combat Initiative System):** Currently marked `done` in [sprint-status.yaml](_bmad-output/implementation-artifacts/sprint-status.yaml). Status will revert to `in-progress` with the addition of new stories below. Epic acceptance criteria need a small addendum: "NPC HP decrements in response to PC actions and the DM consistently sees the live HP state."
- **All other epics (1–14, 16–17):** No impact.

### Story Impact

**No existing stories require modification.** All Epic 15 stories (15-1 through 15-6) shipped correctly per their original scope; the gap is in capabilities they intentionally deferred.

**Two new stories proposed:**

| Story | Title | Complexity |
|---|---|---|
| 15-7 | NPC Damage Tracking & Combat-State Injection in DM Context | Medium |
| 15-8 | Auto-Detect Encounter Resolution (all NPCs at 0 HP → DM prompt to end combat) | Low–Medium |

### Artifact Conflicts

| Artifact | Impact | Action |
|---|---|---|
| **PRD** | No conflict. Existing FR coverage assumes HP is tracked. | No update needed. |
| **Architecture** | Asymmetric memory section already covers DM-reads-everything pattern. | Optional: add note that NPCs are tracked separately from PCs. |
| **Architecture (combat section)** | Original Epic 15 design did not specify HP mutation flow. | Add subsection "NPC State Mutation Flow" after Story 15-7 implementation. |
| **UI/UX** | Combat panel currently shows party HP only. NPC HP visible to DM only (per existing design). | No UI change required for 15-7. UI surfacing of NPC HP could be a separate future story. |
| **Models** | `NpcProfile.hp_current` already supports `ge=0` (defeated state). | No model changes required for 15-7's core. 15-8 may add a `defeated_at_turn: int | None` field. |
| **Tools** | New `dm_update_npc` tool (or extend `dm_update_character_sheet` to detect NPC names). | Add tool. |
| **Agents** | `_build_dm_context` needs combat-state section. `dm_turn` needs new tool interception. | Modify both. |
| **Persistence** | New fields auto-handled by Pydantic `model_dump()`. | No explicit changes. |

### Technical Impact

| File | Change | Risk |
|---|---|---|
| `tools.py` | Add `dm_update_npc(npc_name, hp_change, conditions_add, conditions_remove)` tool. | Low |
| `agents.py` | Hook tool interception in `dm_turn()` (mirror of sheet-update path). Inject combat summary into `_build_dm_context()` when `combat_state.active`. Emit SHEET-style notifications for NPC updates. | **Medium** — touches DM prompt assembly |
| `models.py` | Optional: `NpcProfile.defeated: bool = False` and/or `defeated_at_turn` for clean dead-state markers. | Low |
| `graph.py` | Story 15-8 only: in `context_manager`, detect "all NPCs at 0 HP" and append a `[System]:` nudge for the DM to call `dm_end_combat`. | Low |
| `tests/` | New test files: `test_story_15_7_npc_damage_tracking.py`, `test_story_15_8_auto_end_combat.py`. | Low |
| Frontend | None for these stories (NPC HP remains DM-private). | None |

---

## Section 3: Recommended Approach

### Selected: Direct Adjustment — Two New Stories Within Existing Epic 15

**Rationale:**
- The existing Epic 15 implementation is correct as far as it went; we're filling a gap, not undoing work.
- Both stories are additive — they don't change any existing user-facing behavior except by improving combat coherence.
- Risk is bounded to `agents.py`'s DM prompt assembly and a new tool. Both are well-isolated patterns the codebase has already established (Story 8-4's `dm_update_character_sheet` is the exact template).
- No rollback, no MVP scope change, no architectural pivot. Pure feature completion.

### Effort & Timeline Estimate

| Story | Estimated effort | Depends on |
|---|---|---|
| 15-7 | ~150–250 LoC across `tools.py`, `agents.py`, plus ~25 tests | Story 15-1 (done) |
| 15-8 | ~50–100 LoC in `graph.py` and `agents.py`, plus ~10 tests | Story 15-7 (above) |

Total: roughly one focused dev session for 15-7, half a session for 15-8.

### Alternatives Considered

| Option | Why rejected |
|---|---|
| **Rollback Epic 15** | Excessive — the structured combat system works; only the HP-mutation gap is broken. |
| **MVP redefinition** | Combat is already shipped and used in multiple campaigns. Removing it would be a regression. |
| **Heuristic post-hoc HP parsing** | E.g., regex over narration text to extract "Damage: 7" and apply to a target NPC. Brittle, hard to test, and the DM sometimes attributes damage ambiguously. Tool-call based mutation is the established pattern. |
| **Make the DM track HP in narration only** | This is what we have today. Demonstrably fails on long encounters. |
| **Inject `combat_state` into DM context without adding the tool** | DM would see "Alpha 15/15 HP" forever — useless context. The tool and the context injection are co-dependent. |

---

## Section 4: Detailed Change Proposals

### Story 15-7: NPC Damage Tracking & Combat-State Injection in DM Context

**Story:**

> As a **game engine developer**,
> I want **a `dm_update_npc` tool that mutates `NpcProfile.hp_current` and conditions, plus injection of the live combat state into the DM's main context prompt**,
> So that **the DM has a consistent, mutable view of NPC HP across all turn types and can narrate combat that actually ends when enemies die**.

**Priority:** High (combat coherence is broken without this)
**Estimate:** Medium

**Acceptance Criteria:**

1. **Given** `tools.py`, **When** the developer imports DM tools, **Then** `dm_update_npc(npc_name: str, hp_change: int = 0, conditions_add: list[str] = None, conditions_remove: list[str] = None) -> str` is available as a `@tool`-decorated function.
2. **Given** the tool is bound to the DM agent and called with valid inputs, **When** `dm_turn()` intercepts the call, **Then** the matching entry in `combat_state.npc_profiles` has its `hp_current` adjusted by `hp_change` (clamped to `[0, hp_max]`), and conditions added/removed accordingly.
3. **Given** an NPC's `hp_current` reaches `0`, **When** the tool returns, **Then** a `[SHEET]: Updated <npc_name>: HP -> 0 (defeated)` entry is appended to `ground_truth_log` — same pattern as PC SHEET notifications from Story 8-5.
4. **Given** an unknown NPC name, **When** the tool is called, **Then** it returns `"Error: NPC '<name>' not found in active combat."` without mutating state. Match against `npc_profiles` keys with case-insensitive normalization (mirror PC name resolution).
5. **Given** `combat_state.active is True`, **When** `_build_dm_context(state)` runs (regular DM turn), **Then** the resulting context includes a section like:
    ```
    ## Active Combat — Round N

    ### NPCs (DM-controlled):
    - Mist-Stalker Alpha: HP 4/15 (wounded) — conditions: prone
    - Mist-Stalker Beta: HP 0/15 (DEFEATED)
    - Mist-Stalker Gamma: HP 12/15
    ```
6. **Given** `combat_state.active is False`, **When** `_build_dm_context(state)` runs, **Then** the combat section is omitted (no change to prior behavior).
7. **Given** the DM agent's system prompt addendum during combat, **When** the prompt is assembled, **Then** it includes guidance: *"You have a `dm_update_npc` tool — call it after PC actions to record damage, conditions, and deaths. Do not let an NPC at 0 HP continue acting."*
8. **Given** an NPC reaches `hp_current = 0`, **When** the next routing decision runs in `route_to_next_agent()`, **Then** that NPC's slot in `initiative_order` is skipped on subsequent rounds (defeated NPCs no longer act). Implementation note: filter `initiative_order` against `npc_profiles[name].hp_current > 0` for NPC entries.
9. **Given** persistence, **When** state is saved and reloaded, **Then** `npc_profiles[name].hp_current` round-trips correctly (already supported by existing serialization — verify with test).
10. **Given** ≥25 unit tests exist in `tests/test_story_15_7_npc_damage_tracking.py`, **When** run, **Then** all pass and total project test count remains >=4700.

**Key files:**
- `tools.py` — add `dm_update_npc` (~30 LoC)
- `agents.py` — `_execute_npc_update()` (~40 LoC), `dm_turn()` interception (~20 LoC), `_build_dm_context()` injection (~30 LoC), system-prompt addendum (~10 LoC), `route_to_next_agent()` defeated-NPC filter (~15 LoC if not in graph.py)
- `tests/test_story_15_7_npc_damage_tracking.py` — new file (~250 LoC)

**Risk note:** Modifying `_build_dm_context()` is the riskiest change because it sits on the DM's hot path. Mitigation: gate the new section strictly on `combat_state.active is True`, never break exploration mode.

---

### Story 15-8: Auto-Detect Encounter Resolution

**Story:**

> As a **player watching an autopilot session**,
> I want **the engine to detect when all NPCs in an active combat are at 0 HP and prompt the DM to formally end the encounter**,
> So that **encounters resolve promptly instead of the DM continuing to narrate fights against defeated foes**.

**Priority:** Medium (15-7 fixes the core problem; 15-8 closes the loop)
**Estimate:** Low–Medium

**Acceptance Criteria:**

1. **Given** `combat_state.active is True` and all entries in `combat_state.npc_profiles` have `hp_current == 0`, **When** `context_manager()` runs, **Then** a `[System]: All hostile combatants are defeated. The DM should end this encounter.` entry is appended to `ground_truth_log` (idempotent — only emitted once per combat encounter).
2. **Given** the system message has been emitted, **When** the next DM turn runs, **Then** the DM's prompt addendum reinforces: *"All NPCs are at 0 HP. You should call `dm_end_combat` after narrating the resolution of the fight."*
3. **Given** the DM does not call `dm_end_combat` on the next turn (model ignores the nudge), **When** combat continues for ≥3 more rounds in the all-NPCs-defeated state, **Then** combat is force-ended via the existing `max_combat_rounds` mechanism *or* by an explicit secondary check — pick one approach and document.
4. **Given** combat has zero NPCs in `npc_profiles` (party fled, encounter was entered without NPCs, etc.), **When** the all-defeated check runs, **Then** the check is skipped (do not trigger on empty NPC dict).
5. **Given** `combat_state.active is False`, **When** `context_manager()` runs, **Then** no defeat-detection logic runs.
6. **Given** ≥10 unit tests exist in `tests/test_story_15_8_auto_end_combat.py`, **When** run, **Then** all pass.

**Key files:**
- `graph.py` — defeat-detection block in `context_manager()` (~30 LoC)
- `agents.py` — DM combat-prompt addendum text adjustment (~10 LoC)
- `tests/test_story_15_8_auto_end_combat.py` — new file (~120 LoC)

---

## Section 5: Implementation Handoff

**Scope classification:** **Minor** — direct development implementation. No backlog reorganization, no PM/Architect escalation.

### Recipients & Responsibilities

| Role | Responsibility |
|---|---|
| **Dev (you / dev agent)** | Implement Story 15-7 first, then 15-8. Standard cycle: `create-story` → `dev-story` → `code-review` → commit → `finalize`. |
| **Product Owner** (you) | Verify the proposed acceptance criteria match intent before dev starts. Approve final commit. |

### Success Criteria

- A subsequent test campaign with 100+ combat turns shows `npc_profiles[name].hp_current` actually decrementing and reaching 0.
- Combat encounters end within their max-round budget (no more 100+ turn churns against the same enemies).
- The DM, when asked via Whisper "what's the Alpha's HP?", reports a number that matches the engine's structured state.
- Total project test count grows by ~35 (25 from 15-7, 10 from 15-8). All previously-passing tests still pass.

### Non-Goals (Explicitly Out of Scope)

- **Frontend NPC HP display** — NPCs remain DM-private. If you want UI surfacing, it's a separate story (15-9?).
- **PC HP rebalancing for harder encounters** — independent concern.
- **Replacing the current narrative-driven combat with strict HP arithmetic** — the LLM still narrates; the tool just records what the LLM said it did.
- **Backporting fixes to in-flight Session 017** — once shipped, new combats will benefit; the current Mist-Stalker encounter has no clean fix and should be ended via Drop In or the manual nudge that was already sent.

---

## Appendix: Checklist Completion Record

| Section | Status | Notes |
|---|---|---|
| 1.1 Trigger story | [N/A] | Not story-triggered; gameplay-triggered (Session 017) |
| 1.2 Core problem | [Done] | NPC HP never decremented; DM context lacks combat state |
| 1.3 Evidence | [Done] | Forensic counts + checkpoint snapshot data |
| 2.1 Current epic still completable | [Done] | Yes, Epic 15 with 2 added stories |
| 2.2 Epic-level changes | [Done] | Add 15-7, 15-8 |
| 2.3 Future epic impact | [Done] | None |
| 2.4 New epics needed | [N/A] | No |
| 2.5 Epic resequencing | [N/A] | No |
| 3.1 PRD conflicts | [Done] | None |
| 3.2 Architecture conflicts | [Done] | Minor doc addition only |
| 3.3 UI/UX conflicts | [Done] | None for these stories |
| 3.4 Other artifacts | [Done] | Test files only |
| 4.1 Direct Adjustment viable | [Viable] | Selected approach — Effort: Medium, Risk: Low–Medium |
| 4.2 Rollback viable | [Not viable] | Existing Epic 15 work is correct |
| 4.3 MVP review viable | [Not viable] | No scope reduction needed |
| 4.4 Selected path | [Done] | Direct Adjustment — Stories 15-7 & 15-8 |
| 5.1 Issue summary | [Done] | Section 1 |
| 5.2 Epic + artifact impact | [Done] | Section 2 |
| 5.3 Recommended path + rationale | [Done] | Section 3 |
| 5.4 PRD MVP impact | [Done] | None — combat already in MVP |
| 5.5 Handoff plan | [Done] | Section 5 |
| 6.1 Checklist completion | [Done] | This appendix |
| 6.2 Proposal accuracy | [Pending] | Awaiting user review |
| 6.3 Explicit approval | [Pending] | Awaiting user yes/no |
| 6.4 Next steps confirmed | [Pending] | After approval |
