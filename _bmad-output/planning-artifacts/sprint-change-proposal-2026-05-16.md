# Sprint Change Proposal: NPC Profile Visibility in the Frontend

**Date:** 2026-05-16
**Triggered by:** Live gameplay observation during Session XIX (Curse of Strahd, Qwen 3.6) — user noticed no UI surface for viewing NPC sheets despite Story 15-7 making NPC HP a live, mutating field.
**Scope:** Minor — one new story (15-9) within existing Epic 15.
**Risk:** Low

---

## Section 1: Issue Summary

Story 15-7 (NPC Damage Tracking, shipped 2026-05-15) turned `combat_state.npc_profiles[name].hp_current` from a static value (set once at combat start, never decremented) into a **live, mutating field** that the DM updates via the `dm_update_npc` tool every time an NPC takes damage or changes condition. Story 15-7 also injects a rich live combat-state summary into the DM's prompt context, so the **DM** can read every NPC's current HP, AC, conditions, and status label on every turn.

**The player cannot see any of this.** No frontend surface exposes the live `NpcProfile` data. During Session XIX's first warg fight, the engine knew "Warg HP: 8/22 (critically wounded), conditions: [bleeding]" — but the player only saw narrative prose. The player cannot:

- See current HP for any NPC in the encounter
- See AC, conditions, or any other NpcProfile field
- See the list of *all* active NPCs in one place (only their names appear in the initiative panel as the round progresses)
- Click on an NPC to view its full profile, as they can for any PC via the "Sheet" button

### Forensic Evidence

| File | Evidence |
|---|---|
| [api/engine.py](api/engine.py) `_get_state_snapshot` | Serializes `combat_state` but the frontend's narrower type discards fields |
| [frontend/src/lib/types.ts:121](frontend/src/lib/types.ts#L121) | `npc_profiles: Record<string, { name: string }>` — explicitly throws away `hp_current`, `hp_max`, `ac`, `conditions`, `personality`, `tactics`, `secret` |
| [frontend/src/lib/components/CombatInitiative.svelte](frontend/src/lib/components/CombatInitiative.svelte) | Iterates `combat_state.npc_profiles` but renders **name only** in the initiative list (lines 62-72) |
| [frontend/src/lib/components/CharacterCard.svelte:98-104](frontend/src/lib/components/CharacterCard.svelte) | "Sheet" button exists for PCs, opens `CharacterSheetModal` |
| [frontend/src/lib/components/CharacterSheetModal.svelte](frontend/src/lib/components/CharacterSheetModal.svelte) | Hard-coded to PCs via `getCharacterSheet(sessionId, characterName)` — calls `/sessions/{id}/character-sheets/{name}` (PC endpoint only) |
| [api/routes.py:2266](api/routes.py#L2266) | `GET /sessions/{id}/character-sheets/{character_name}` exists for PCs; no NPC equivalent |
| [_bmad-output/implementation-artifacts/stories/15-5-combat-ui-indicators.md:40](../implementation-artifacts/stories/15-5-combat-ui-indicators.md) AC #5 | The Combat UI story explicitly scoped NPC display to **names only** ("NPC names are displayed using the `NpcProfile.name` field") — HP/AC/conditions were never in scope |

### Why this is a gap now (but wasn't before)

| Before Story 15-7 (yesterday) | After Story 15-7 (today) |
|---|---|
| `hp_current` always equal to `hp_max` (never mutated) | `hp_current` mutates per dm_update_npc call |
| Nothing meaningful to show for NPCs | Live tactical data exists per NPC, updated per turn |
| "DM-only opacity" was a coherent design choice | "DM-only opacity" now means the player is structurally less informed than the DM about combat math the engine tracks precisely |
| Sheet button parity wasn't relevant — NPCs had no sheet | Sheet button parity is a noticeable asymmetry |

---

## Section 2: Impact Analysis

### Epic Impact

- **Epic 15 (Combat Initiative System):** Currently marked `done` (after Stories 15-7/15-8). Will revert to `in-progress` with the addition of Story 15-9.
- **All other epics (1-14, 16-17):** No impact.

### Story Impact

**No existing stories require modification.** Story 15-5's AC #5 (NPC names in initiative) remains correct as far as it went; this proposal adds a complementary surface for full NPC visibility.

**One new story proposed:**

| Story | Title | Complexity |
|---|---|---|
| 15-9 | NPC Profile Visibility in the Frontend | Medium |

### Artifact Conflicts

| Artifact | Impact | Action |
|---|---|---|
| **PRD** | No conflict. Existing FR for player observability is implicit. | No update. |
| **Architecture** | Add note under "Asymmetric memory" section that NPC profiles are now player-visible (was DM-only). | Optional doc tweak after 15-9 implementation. |
| **UI/UX spec** | New surfaces: NPC list in sidebar, NPC sheet modal. | Add to ux-design-specification.md after design discussion. |
| **Models** | `NpcProfile` model is sufficient (has all needed fields already). | No model changes. |
| **Tools** | No new tools. | No changes. |
| **Agents** | No changes (`_execute_npc_update` already emits the data; backend snapshot exposes it). | No changes. |
| **Persistence** | No changes (npc_profiles already round-trip cleanly). | No changes. |

### Technical Impact

| File | Change | Risk |
|---|---|---|
| `frontend/src/lib/types.ts` | Widen `npc_profiles` type to full `NpcProfile` shape (mirror the Pydantic model). | Low |
| `frontend/src/lib/components/NpcPanel.svelte` | **NEW** — sidebar panel showing active-combat NPC list with HP/conditions; gated on `combat_state.active`. | Low |
| `frontend/src/lib/components/NpcCard.svelte` | **NEW** — single-NPC list-row component with HP bar + status label + "Sheet" button. | Low |
| `frontend/src/lib/components/NpcSheetModal.svelte` | **NEW** — full NPC sheet modal, mirror of `CharacterSheetModal` structure. | Low |
| `frontend/src/lib/components/Sidebar.svelte` | Render `<NpcPanel />` below `CombatInitiative` (also gated on combat active). | Low |
| `frontend/src/lib/stores/uiStore.ts` | Add `npcSheetName: string | null` state (parallel to existing `characterSheetName`). | Low |
| `frontend/src/lib/api.ts` | Add `getNpcProfile(sessionId, npcKey)` API call (calls new endpoint). | Low |
| `api/routes.py` | Add `GET /sessions/{id}/npcs/{npc_key}` endpoint returning the `NpcProfile` JSON. | Low |
| `api/schemas.py` | Add `NpcProfileResponse` model mirroring `models.NpcProfile`. | Low |
| `api/engine.py` `_get_state_snapshot` | Verify full `NpcProfile` data flows in `combat_state` snapshot. Likely already works via `model_dump()` — confirm/test. | Low |
| `tests/test_story_15_9_npc_profile_visibility.py` | **NEW** — ~20-30 tests covering type widening, panel rendering, modal, API endpoint, route gating. | Low |
| Frontend Vitest equivalent | **NEW** — component tests for NpcPanel, NpcCard, NpcSheetModal. | Low |

---

## Section 3: Recommended Approach

### Selected: Direct Adjustment — One New Story Within Existing Epic 15

**Rationale:**
- Pure UX gap fill — the underlying data exists, is mutating correctly (verified live in Session XIX turn 86), and just needs a frontend surface.
- Mirror pattern: `CharacterSheetModal` for PCs → `NpcSheetModal` for NPCs is a direct analog. Low cognitive load for users; low risk for implementation.
- No model changes, no tool changes, no graph changes. Pure presentation layer + one read-only API endpoint.
- The "DM-only opacity" original design no longer fits the data model — surfacing this is *closing* a design drift, not opening a new one.

### Effort & Timeline Estimate

| Story | Estimated effort | Depends on |
|---|---|---|
| 15-9 | ~300-450 LoC across `frontend/` and `api/` + ~25 tests | Story 15-7 (done) |

Roughly one focused dev session.

### Alternatives Considered

| Option | Why rejected |
|---|---|
| **Minimal: HP-inline in CombatInitiative** | Faster (~50 LoC) but only surfaces HP. Loses AC, conditions, personality, tactics. Doesn't fix the asymmetry, just patches the worst symptom. The user explicitly chose "Full" scope. |
| **Reveal NPC profiles only after defeat** ("post-mortem" mode) | Preserves dramatic tension but defeats the tactical-feedback purpose. Player still can't make informed in-the-moment decisions. |
| **Rollback Story 15-7's data model** | Would re-break combat resolution. Story 15-7 is doing exactly what it was meant to. |
| **MVP redefinition** | No scope change needed; this is a one-story addition. |

---

## Section 4: Detailed Change Proposal — Story 15-9

### Story 15-9: NPC Profile Visibility in the Frontend

**Story:**

> As a **player watching tactical combat**,
> I want **a panel showing all active NPCs with live HP/conditions, and a sheet modal for full NPC details**,
> So that **I can see the same tactical state the DM sees — the live HP that Story 15-7's `dm_update_npc` is tracking — instead of guessing at numbers from narrative prose alone**.

**Priority:** Medium (UX completeness — Stories 15-7/15-8 deliver the engine behavior; 15-9 surfaces it to the player)

**Estimate:** Medium

**Acceptance Criteria:**

1. **Given** `combat_state.active` is `True` and `combat_state.npc_profiles` is non-empty, **When** the sidebar renders, **Then** a new `<NpcPanel />` is displayed below the existing `<CombatInitiative />` listing every NPC with: `<name>`, current HP / max HP, an HP-ratio visual indicator (bar or color), and a comma-separated list of `conditions`.

2. **Given** `combat_state.active` is `False`, **When** the sidebar renders, **Then** `<NpcPanel />` is not displayed.

3. **Given** an NPC in the panel has `hp_current == 0`, **When** the panel renders, **Then** that NPC is visually marked as defeated (e.g., strikethrough name + greyed-out card) but remains visible (not removed) so the player can see the post-combat outcome.

4. **Given** the frontend type `npc_profiles`, **When** the TypeScript type is read, **Then** it matches the full `NpcProfile` Pydantic model shape: `{ name: string, hp_max: number, hp_current: number, ac: number, personality: string, tactics: string, secret: string, conditions: string[] }`.

5. **Given** `_get_state_snapshot()` in `api/engine.py`, **When** it serializes `combat_state`, **Then** the snapshot's `npc_profiles` field contains the full `NpcProfile` model_dump (not a truncated shape).

6. **Given** an NPC in the panel, **When** the user clicks/taps it (or presses Enter while focused), **Then** an `<NpcSheetModal />` opens displaying: name, HP, AC, conditions, personality, tactics. The `secret` field is rendered separately under a collapsible "DM-only" disclosure (player can see that a secret exists but reveals it explicitly).

7. **Given** the `NpcSheetModal` is open, **When** the user presses Escape or clicks the backdrop, **Then** the modal closes (mirror behavior of existing `CharacterSheetModal`).

8. **Given** `uiStore.ts`, **When** a developer reads the store, **Then** a new writable `npcSheetName: string | null` state exists (parallel to existing `characterSheetName`).

9. **Given** the API at `api/routes.py`, **When** a developer reads the routes, **Then** `GET /sessions/{session_id}/npcs/{npc_key}` exists, returning the `NpcProfile` JSON or 404 if the NPC is not in the current `combat_state.npc_profiles`.

10. **Given** the `NpcSheetModal` opens for an NPC key, **When** it loads, **Then** it calls `getNpcProfile(sessionId, npcKey)` from `api.ts` (mirror of `getCharacterSheet`).

11. **Given** combat ends (`combat_state.active` flips to `False`), **When** the sidebar re-renders, **Then** `<NpcPanel />` disappears cleanly and any open `NpcSheetModal` closes.

12. **Given** the new endpoint, **When** called for an unknown `npc_key`, **Then** it returns `404 Not Found` with a clear error body.

13. **Given** the new endpoint, **When** called and the session has no active combat, **Then** it returns `404 Not Found` (NPCs only exist during active combat).

14. **Given** the SHEET-notification narrative entries (e.g., `[SHEET]: Updated Wargs: HP 8 -> 0 (defeated)`), **When** Story 15-9 ships, **Then** those entries continue to render exactly as they do today (no regression — Story 15-7 emits them, narrative panel renders them).

15. **Given** ≥20 tests exist in `tests/test_story_15_9_npc_profile_visibility.py` (backend) + corresponding Vitest component tests, **When** run, **Then** all pass and total project test count grows by ≥30.

**Key files:**

| Path | Action | Approx LoC |
|---|---|---|
| `frontend/src/lib/types.ts` | Widen `npc_profiles` type | ~10 |
| `frontend/src/lib/components/NpcPanel.svelte` | NEW | ~80 |
| `frontend/src/lib/components/NpcCard.svelte` | NEW | ~60 |
| `frontend/src/lib/components/NpcSheetModal.svelte` | NEW (mirror CharacterSheetModal) | ~110 |
| `frontend/src/lib/components/Sidebar.svelte` | Mount `<NpcPanel />` conditionally | ~5 |
| `frontend/src/lib/stores/uiStore.ts` | Add `npcSheetName` state | ~3 |
| `frontend/src/lib/api.ts` | Add `getNpcProfile()` | ~10 |
| `api/routes.py` | Add `GET /sessions/{id}/npcs/{npc_key}` | ~30 |
| `api/schemas.py` | Add `NpcProfileResponse` | ~15 |
| `api/engine.py` | Verify `_get_state_snapshot` exposes full profile (likely no change) | ~0-5 |
| `tests/test_story_15_9_npc_profile_visibility.py` | NEW | ~250 |
| Component test files | NEW (3 small files) | ~150 |

**Risk note:** Lowest-risk story we've shipped in Epic 15. All changes are additive, no existing behavior touched. The only spot to be careful: ensuring the API endpoint is *read-only* (no mutation surface) and explicit about returning 404 when combat is inactive (an NPC profile fetched out-of-combat would be ambiguous).

---

## Section 5: Implementation Handoff

**Scope classification:** **Minor** — direct dev implementation.

### Recipients & Responsibilities

| Role | Responsibility |
|---|---|
| **Dev (sub-agent)** | Implement Story 15-9 via standard cycle: `create-story` → `dev-story` → `code-review` → commit → `testarch-automate` → commit. |
| **Product Owner** (user) | Verify the proposed ACs match intent; approve final commit. |

### Success Criteria

- Visit a session with active combat. The sidebar now shows an "Active NPCs" panel listing every combatant with HP/conditions.
- HP numbers in the panel tick down as `dm_update_npc` fires (live updates via the same WebSocket snapshot stream).
- Clicking an NPC opens a sheet modal showing full profile (HP, AC, conditions, personality, tactics; secret hidden behind disclosure).
- Defeated NPCs appear in the panel with a visual "defeated" treatment, then disappear when combat ends.
- Project test count grows by ~30; all previously-passing tests still pass.

### Non-Goals (Out of Scope)

- **Editing NPC data from the UI** — `dm_update_npc` remains the only mutation path; the UI is read-only.
- **NPC sheets for non-combat NPCs** (shopkeepers, etc.) — out of scope; `combat_state.npc_profiles` is combat-only.
- **Animated HP-change effects** — static numbers are sufficient; animation can be a polish follow-up.
- **NPC token / portrait images** — out of scope; this is a tactical-data surface, not a virtual tabletop.

---

## Appendix: Checklist Completion Record

| Section | Status | Notes |
|---|---|---|
| 1.1 Trigger story | [N/A] | Not story-triggered; user observation during Session XIX gameplay |
| 1.2 Core problem | [Done] | Live NPC data tracked server-side, no frontend surface |
| 1.3 Evidence | [Done] | Forensic citations across 7 files in Section 1 |
| 2.1 Current epic still completable | [Done] | Yes, Epic 15 with 1 added story (15-9) |
| 2.2 Epic-level changes | [Done] | Add 15-9 |
| 2.3 Future epic impact | [Done] | None |
| 2.4 New epics needed | [N/A] | No |
| 2.5 Epic resequencing | [N/A] | No |
| 3.1 PRD conflicts | [Done] | None |
| 3.2 Architecture conflicts | [Done] | Optional asymmetric-memory section update |
| 3.3 UI/UX conflicts | [Done] | New surfaces; ux-design-spec optional update |
| 3.4 Other artifacts | [Done] | Test files only |
| 4.1 Direct Adjustment viable | [Viable] | Selected — Effort: Medium, Risk: Low |
| 4.2 Rollback viable | [Not viable] | Story 15-7 must stay |
| 4.3 MVP review viable | [Not viable] | No scope reduction needed |
| 4.4 Selected path | [Done] | Direct Adjustment — Story 15-9 |
| 5.1 Issue summary | [Done] | Section 1 |
| 5.2 Epic + artifact impact | [Done] | Section 2 |
| 5.3 Recommended path + rationale | [Done] | Section 3 |
| 5.4 PRD MVP impact | [Done] | None |
| 5.5 Handoff plan | [Done] | Section 5 |
| 6.1 Checklist completion | [Done] | This appendix |
| 6.2 Proposal accuracy | [Pending] | Awaiting user review |
| 6.3 Explicit approval | [Pending] | Awaiting user yes/no |
| 6.4 Next steps confirmed | [Pending] | After approval |
