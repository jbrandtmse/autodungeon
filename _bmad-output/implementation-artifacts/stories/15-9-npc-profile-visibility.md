# Story 15.9: NPC Profile Visibility in the Frontend

Status: done

## Epic

Epic 15: Combat Initiative System (v1.2)

## Story

As a **player watching tactical combat**,
I want **a panel showing all active NPCs with live HP/conditions, and a sheet modal for full NPC details**,
So that **I can see the same tactical state the DM sees — the live HP that Story 15-7's `dm_update_npc` is tracking — instead of guessing at numbers from narrative prose alone**.

## Priority

Medium (UX completeness — Stories 15-7/15-8 deliver the engine behavior; 15-9 surfaces it to the player)

## Estimate

Medium (~300-450 LoC across `frontend/` and `api/` + ~30 tests). Pure presentation layer plus one read-only API endpoint and a snapshot widening on the backend. Lowest-risk story shipped in Epic 15 — all changes are additive, no existing behavior touched.

## Dependencies

- **Story 15-1 (Combat State Model & Detection): done** — provides the `NpcProfile` Pydantic model ([models.py:832-860](C:/autodungeon/models.py#L832)) with all the fields this story surfaces: `name`, `hp_max`, `hp_current`, `ac`, `personality`, `tactics`, `secret`, `conditions`, `initiative_modifier`.
- **Story 15-5 (Combat UI Indicators): done** — provides the existing `CombatInitiative.svelte` component ([frontend/src/lib/components/CombatInitiative.svelte](C:/autodungeon/frontend/src/lib/components/CombatInitiative.svelte)) which already reads `combat_state.npc_profiles` and renders NPC names only. AC #5 of that story explicitly limited the surface to names; 15-9 supersedes that limit.
- **Story 15-7 (NPC Damage Tracking): done** — **HARD DEPENDENCY** — provides the live mutation of `combat_state.npc_profiles[name].hp_current` via `dm_update_npc` ([agents.py:`_execute_npc_update`](C:/autodungeon/agents.py)). Without 15-7, NPC HP values would never change and this UI would be a static read-out. This story does NOT add any mutation surface; the UI is strictly read-only.
- **Story 15-8 (Auto-Detect Encounter Resolution): done** — produces `[SHEET]:` notification entries for NPC HP changes that the narrative panel already renders. AC #14 of this story is a regression check that those continue to render unchanged.
- **Story 16-6 (Sidebar & Party Controls): done** — provides `Sidebar.svelte` ([frontend/src/lib/components/Sidebar.svelte](C:/autodungeon/frontend/src/lib/components/Sidebar.svelte)) which is the mount point for the new `<NpcPanel />`.
- **Story 16-10 (Advanced Features UI): done** — provides the **mirror pattern** for this story:
  - `CharacterSheetModal.svelte` → mirror for `NpcSheetModal.svelte`
  - `getCharacterSheet()` in `api.ts` → mirror for `getNpcProfile()`
  - `GET /sessions/{id}/character-sheets/{character_name}` ([api/routes.py:2265](C:/autodungeon/api/routes.py#L2265)) → mirror for `GET /sessions/{id}/npcs/{npc_key}`
  - `CharacterSheetResponse` in `api/schemas.py` → mirror for `NpcProfileResponse`
  - `uiState.characterSheetName` ([frontend/src/lib/stores/uiStore.ts:10](C:/autodungeon/frontend/src/lib/stores/uiStore.ts#L10)) → mirror for `uiState.npcSheetName`

## Acceptance Criteria

1. **Given** `combat_state.active` is `True` and `combat_state.npc_profiles` is non-empty, **When** the sidebar renders, **Then** a new `<NpcPanel />` is displayed below the existing `<CombatInitiative />` listing every NPC with: `<name>`, `current HP / max HP`, an HP-ratio visual indicator (bar or color), and a comma-separated list of `conditions`.

2. **Given** `combat_state.active` is `False`, **When** the sidebar renders, **Then** `<NpcPanel />` is not displayed (early return in the component — no DOM nodes emitted).

3. **Given** an NPC in the panel has `hp_current == 0`, **When** the panel renders, **Then** that NPC is visually marked as defeated (e.g., strikethrough name + greyed-out card) but remains visible (not removed) so the player can see the post-combat outcome.

4. **Given** the frontend type `npc_profiles` in [frontend/src/lib/types.ts:121](C:/autodungeon/frontend/src/lib/types.ts#L121), **When** the TypeScript type is read, **Then** it matches the full `NpcProfile` Pydantic model shape: `{ name: string; hp_max: number; hp_current: number; ac: number; personality: string; tactics: string; secret: string; conditions: string[]; initiative_modifier: number }`. Extract this into a named export `export interface NpcProfile { ... }` (mirror existing exported interfaces) and reference it from `CombatState.npc_profiles: Record<string, NpcProfile>`.

5. **Given** `_get_state_snapshot()` in [api/engine.py:858](C:/autodungeon/api/engine.py#L858), **When** it serializes the state, **Then** the snapshot's top-level `combat_state` field is present and contains the full `CombatState.model_dump()` (including `npc_profiles` keyed by sanitized NPC keys, each entry being the full `NpcProfile.model_dump()`). The snapshot currently OMITS `combat_state` entirely (verified by grep) — implementation MUST add it. Use `model_dump()` for Pydantic objects and pass through dicts for already-deserialized state. Set `combat_state` to `None` if the state's value is `None`.

6. **Given** an NPC card in the panel, **When** the user clicks/taps it (or presses Enter/Space while focused — the card MUST be keyboard-accessible via `role="button"` + `tabindex="0"` + `onkeydown` handler), **Then** an `<NpcSheetModal />` opens displaying: name, HP (with bar), AC, conditions, personality, tactics. The `secret` field is rendered separately under a collapsible `<details>` "DM-only" disclosure (player can see that a secret exists but reveals it explicitly by expanding the disclosure).

7. **Given** the `NpcSheetModal` is open, **When** the user presses Escape or clicks the backdrop, **Then** the modal closes. Implementation MUST mirror the keydown/backdrop handlers in [CharacterSheetModal.svelte:39-66](C:/autodungeon/frontend/src/lib/components/CharacterSheetModal.svelte#L39) including the focus-trap on Tab/Shift+Tab.

8. **Given** [frontend/src/lib/stores/uiStore.ts](C:/autodungeon/frontend/src/lib/stores/uiStore.ts), **When** a developer reads the store, **Then** the `UiState` interface declares a new writable field `npcSheetName: string | null` (parallel to the existing `characterSheetName: string | null` on line 10) and the `writable(...)` initial value sets `npcSheetName: null`. Update all four existing places that destructure/spread `UiState` (vitest mock setups in `*.test.ts` files) to include the new field.

9. **Given** the API at [api/routes.py](C:/autodungeon/api/routes.py), **When** a developer reads the routes, **Then** `GET /sessions/{session_id}/npcs/{npc_key}` exists (defined in the same routes module, response_model `NpcProfileResponse`), returning the `NpcProfile` JSON or `404` if the NPC is not in the current `combat_state.npc_profiles`. The implementation pattern MUST mirror `get_character_sheet()` at [api/routes.py:2269](C:/autodungeon/api/routes.py#L2269) including: `_validate_and_check_session(session_id)` call, path-traversal validation on `npc_key` (`"/", "\\", "\x00", ".."` rejected with 400), latest-checkpoint load, case-insensitive key lookup.

10. **Given** the `NpcSheetModal` opens for an NPC key, **When** it loads, **Then** it calls `getNpcProfile(sessionId, npcKey)` from `api.ts`. The new `getNpcProfile()` function signature MUST mirror `getCharacterSheet()` at [api.ts:289-296](C:/autodungeon/frontend/src/lib/api.ts#L289):
    ```typescript
    export async function getNpcProfile(sessionId: string, npcKey: string): Promise<NpcProfile> {
      return request<NpcProfile>(
        `/api/sessions/${encodeURIComponent(sessionId)}/npcs/${encodeURIComponent(npcKey)}`,
      );
    }
    ```

11. **Given** combat ends (`combat_state.active` flips to `False`), **When** the sidebar re-renders, **Then** `<NpcPanel />` disappears cleanly (AC #2) AND any open `NpcSheetModal` is closed. Implementation: add a `$effect` in `NpcSheetModal.svelte` that watches `$gameState?.combat_state?.active` and calls `onClose()` when it flips false; or alternatively a `$effect` in `Sidebar.svelte`/`NpcPanel.svelte` that resets `uiState.npcSheetName = null` on the same condition. Either is acceptable — pick one and document the choice in code comments.

12. **Given** the new endpoint, **When** called for an unknown `npc_key` (after sanitization + case-insensitive lookup), **Then** it returns `404 Not Found` with `detail: "NPC '<key>' not found in active combat"` (clear error body — match the format used by `get_character_sheet`'s 404).

13. **Given** the new endpoint, **When** called and the session has no active combat (`combat_state is None` OR `combat_state.active is False` OR `combat_state.npc_profiles` is empty), **Then** it returns `404 Not Found` with `detail: "No active combat in session"`. Rationale: NPCs only exist during active combat (`combat_state.npc_profiles` is reset by `_execute_end_combat`).

14. **Given** the SHEET-notification narrative entries (e.g., `[SHEET]: Updated Wargs: HP 8 -> 0 (defeated)`), **When** Story 15-9 ships, **Then** those entries continue to render exactly as they do today (no regression — Story 15-7 emits them, the narrative panel renders them via existing logic). This is a regression check — no new code, but it MUST be covered by at least one test that asserts the existing rendering path is untouched.

15. **Given** ≥20 tests exist in `tests/test_story_15_9_npc_profile_visibility.py` (backend) plus Vitest component tests in `frontend/src/lib/components/NpcPanel.test.ts`, `NpcCard.test.ts`, and `NpcSheetModal.test.ts` (frontend), **When** the full suites run (`pytest` + `cd frontend && npm run test`), **Then** all new tests pass AND the total project test count grows by ≥30 with no regressions in existing tests. Pre-existing ~20 failing tests (per [MEMORY.md](C:/Users/Josh/.claude/projects/c--autodungeon/memory/MEMORY.md)) remain excluded from the baseline per project convention.

## Tasks / Subtasks

- [x] **Task 1: Widen TypeScript types for NpcProfile** (AC: #4)
  - [x] 1.1: In [frontend/src/lib/types.ts](C:/autodungeon/frontend/src/lib/types.ts), add a new exported interface `NpcProfile` mirroring the Pydantic model at [models.py:832-860](C:/autodungeon/models.py#L832). Place it immediately before `CombatState` (line 115).
  - [x] 1.2: Update `CombatState.npc_profiles` type from `Record<string, { name: string }>` to `Record<string, NpcProfile>`.
  - [x] 1.3: Run `cd frontend && npm run check` to confirm no type regressions. The existing `CombatInitiative.svelte` reads `npc_profile?.name` — this still type-checks because `NpcProfile.name` is required.

- [x] **Task 2: Expose combat_state in the WebSocket snapshot** (AC: #5)
  - [x] 2.1: In [api/engine.py:858](C:/autodungeon/api/engine.py#L858) `_get_state_snapshot()`, add a `combat_state` key to the returned snapshot dict (after `characters`, before `game_config`).
  - [x] 2.2: Implementation pattern (mirror the `characters` handler at lines 887-890):
    ```python
    combat_state_raw = self._state.get("combat_state")
    if combat_state_raw is None:
        snapshot["combat_state"] = None
    elif hasattr(combat_state_raw, "model_dump"):
        snapshot["combat_state"] = combat_state_raw.model_dump()
    else:
        snapshot["combat_state"] = dict(combat_state_raw)
    ```
  - [x] 2.3: Verify `npc_profiles` inside the dump is itself a dict of dicts (Pydantic's `model_dump()` recurses through nested models — confirm in a unit test).
  - [x] 2.4: Add a regression test asserting `_get_state_snapshot()` includes `combat_state` AND that `combat_state["npc_profiles"][key]` contains all 9 `NpcProfile` fields (`name`, `hp_max`, `hp_current`, `ac`, `personality`, `tactics`, `secret`, `conditions`, `initiative_modifier`).

- [x] **Task 3: Add NpcProfileResponse schema and GET /sessions/{id}/npcs/{npc_key} endpoint** (AC: #9, #12, #13)
  - [x] 3.1: In [api/schemas.py](C:/autodungeon/api/schemas.py), add a new `NpcProfileResponse` Pydantic model mirroring `models.NpcProfile` field-for-field. Place it after `CharacterSheetResponse` (line 389) in a new section header comment `# NPC Profile Schemas (Story 15.9)`.
  - [x] 3.2: In [api/routes.py](C:/autodungeon/api/routes.py), immediately after `get_character_sheet` (line 2330), add a new endpoint `get_npc_profile(session_id: str, npc_key: str) -> NpcProfileResponse` decorated with `@router.get("/sessions/{session_id}/npcs/{npc_key}", response_model=NpcProfileResponse)`.
  - [x] 3.3: Implementation steps:
    1. Call `_validate_and_check_session(session_id)` (existing helper).
    2. Reject path-traversal patterns in `npc_key`: `if any(c in npc_key for c in ("/", "\\", "\x00")) or ".." in npc_key: raise HTTPException(400, "NPC key contains invalid characters")`.
    3. Load latest checkpoint via `_aio_load_checkpoint`.
    4. Read `combat_state = state.get("combat_state")`. If `None`, OR `combat_state.active` is False, OR `combat_state.npc_profiles` is empty: raise `HTTPException(404, "No active combat in session")`.
    5. Case-insensitive key lookup (mirror `_get` helper in `get_character_sheet`): iterate `npc_profiles.items()` and match `key.lower() == npc_key.lower()`.
    6. If not found: raise `HTTPException(404, f"NPC '{npc_key}' not found in active combat")`.
    7. Return `NpcProfileResponse(**npc.model_dump())` (or `NpcProfileResponse(**npc)` if dict).
  - [x] 3.4: Add `from api.schemas import NpcProfileResponse` to the existing schemas import block (alphabetical).

- [x] **Task 4: Add getNpcProfile() to api.ts** (AC: #10)
  - [x] 4.1: In [frontend/src/lib/api.ts:289](C:/autodungeon/frontend/src/lib/api.ts#L289), immediately after `getCharacterSheet`, add `getNpcProfile()` per AC #10 signature.
  - [x] 4.2: Add `NpcProfile` to the imports block at the top of `api.ts`.

- [x] **Task 5: Add npcSheetName to uiStore** (AC: #8)
  - [x] 5.1: In [frontend/src/lib/stores/uiStore.ts](C:/autodungeon/frontend/src/lib/stores/uiStore.ts), add `npcSheetName: string | null;` to the `UiState` interface (after `characterSheetName` on line 10).
  - [x] 5.2: In the `writable<UiState>({...})` initializer, add `npcSheetName: null,` (after `characterSheetName: null,` on line 21).
  - [x] 5.3: Find all `.test.ts` files that mock `uiState` (`grep -r "characterSheetName: null" frontend/src/lib/components/*.test.ts`) and add `npcSheetName: null,` to each mock initializer. Currently affects:
    - `CharacterCard.test.ts:18`
    - Any other test file that spreads the full `UiState` shape.

- [x] **Task 6: Create NpcCard.svelte (list-row component)** (AC: #1, #3, #6)
  - [x] 6.1: Create [frontend/src/lib/components/NpcCard.svelte](C:/autodungeon/frontend/src/lib/components/NpcCard.svelte). Mirror the structure of `CharacterCard.svelte` (header row + HP bar + actions) but simplified:
    - Props: `npcKey: string`, `npc: NpcProfile`
    - Display: NPC name (greyed/strikethrough if `hp_current == 0`), `hp_current/hp_max HP`, HP bar with `hp-green / hp-amber / hp-red` color classes (mirror the existing `hpColorClass` derivation in `CharacterSheetModal.svelte:78-82`), conditions list (comma-separated, omit if empty).
    - Interactive: `role="button"`, `tabindex="0"`, `aria-label="View NPC sheet for {npc.name}"`, click and keydown (Enter/Space) handlers that set `uiState.update(s => ({ ...s, npcSheetName: npcKey }))`.
  - [x] 6.2: Use existing CSS variables from the campfire theme (`var(--bg-secondary)`, `var(--text-primary)`, `var(--accent-warm)`, etc.) for visual consistency.
  - [x] 6.3: Defeated styling: `class:defeated={npc.hp_current === 0}` with a `.defeated { opacity: 0.5; text-decoration: line-through; }` rule (or similar — match existing campfire patterns).

- [x] **Task 7: Create NpcPanel.svelte (sidebar panel)** (AC: #1, #2)
  - [x] 7.1: Create [frontend/src/lib/components/NpcPanel.svelte](C:/autodungeon/frontend/src/lib/components/NpcPanel.svelte). Mirror the structure of `PartyPanel.svelte`:
    - `const combatState = $derived($gameState?.combat_state ?? null);`
    - `const isActive = $derived(combatState?.active === true);`
    - `const npcs = $derived.by(() => Object.entries(combatState?.npc_profiles ?? {}));`
    - Wrap entire output in `{#if isActive && npcs.length > 0}` block.
    - Section heading: `Active NPCs` (mirror `Party` heading style in `PartyPanel.svelte:34`).
    - Render `<NpcCard>` for each entry, passing `npcKey={key}` and `npc={profile}`.
  - [x] 7.2: Use the same `section-heading` class pattern from `PartyPanel.svelte:70-78` for visual consistency.

- [x] **Task 8: Create NpcSheetModal.svelte (full sheet modal)** (AC: #6, #7, #11)
  - [x] 8.1: Create [frontend/src/lib/components/NpcSheetModal.svelte](C:/autodungeon/frontend/src/lib/components/NpcSheetModal.svelte). Mirror the structure of [CharacterSheetModal.svelte](C:/autodungeon/frontend/src/lib/components/CharacterSheetModal.svelte) but simpler (no ability scores, no spellcasting, no equipment — just the 8 NpcProfile fields).
    - Props: `open: boolean`, `sessionId: string`, `npcKey: string`, `onClose: () => void`.
    - State: `npc = $state<NpcProfile | null>(null)`, `loading = $state(false)`, `error = $state<string | null>(null)`.
    - On `$effect(open && sessionId && npcKey)`: call `getNpcProfile(sessionId, npcKey)` and populate `npc`.
    - Layout: header with `<NPC name>`, body sections: HP bar (mirror `CharacterSheetModal.svelte:168-186`), AC chip, conditions list, personality paragraph, tactics paragraph, then a `<details>` disclosure labeled `Secret (DM-only)` containing `npc.secret` (only rendered if `npc.secret` is non-empty; otherwise hide the disclosure entirely).
  - [x] 8.2: Keyboard handling: copy the `handleKeydown` (Escape + Tab focus-trap) and `handleBackdropClick` patterns from [CharacterSheetModal.svelte:39-66](C:/autodungeon/frontend/src/lib/components/CharacterSheetModal.svelte#L39) verbatim.
  - [x] 8.3: a11y: `role="dialog"`, `aria-modal="true"`, `aria-label="NPC Sheet"`, `bind:this={dialogEl}` for focus trap.
  - [x] 8.4: Auto-close on combat-end (AC #11): add `$effect(() => { if (!$gameState?.combat_state?.active && open) onClose(); })` inside the script block.

- [x] **Task 9: Mount NpcPanel and NpcSheetModal in Sidebar/layout** (AC: #1, #11)
  - [x] 9.1: In [frontend/src/lib/components/Sidebar.svelte](C:/autodungeon/frontend/src/lib/components/Sidebar.svelte), import `NpcPanel` and mount it immediately after `<CombatInitiative />` on line 39:
    ```svelte
    <CombatInitiative />
    <NpcPanel />
    ```
  - [x] 9.2: For the modal, mount it at the same level as the existing `CharacterSheetModal` (search `frontend/src/routes/` for where `CharacterSheetModal` is currently mounted — likely a top-level route layout). Add `<NpcSheetModal open={$uiState.npcSheetName !== null} sessionId={sessionId} npcKey={$uiState.npcSheetName ?? ''} onClose={() => uiState.update(s => ({...s, npcSheetName: null}))} />` alongside it.

- [x] **Task 10: Backend tests** (AC: #5, #9, #12, #13, #14, #15)
  - [x] 10.1: Create `tests/test_story_15_9_npc_profile_visibility.py`. Use class-based fixtures (project convention — see `tests/test_story_15_7_npc_damage_tracking.py` for pattern).
  - [x] 10.2: Test classes:
    - `TestStateSnapshotIncludesCombatState` (~5 tests): snapshot contains `combat_state` key; `combat_state["npc_profiles"]["goblin_1"]` has all 9 NpcProfile fields; combat_state is `None` when state has none; combat_state["active"] is False during exploration; hp_current mutation is reflected after `dm_update_npc`.
    - `TestGetNpcProfileEndpoint` (~8 tests): happy path returns 200 with full NpcProfileResponse; 404 on unknown npc_key; 404 on no active combat; 404 on combat_state=None; 400 on path-traversal in npc_key (`../`, `\`, `\x00`); case-insensitive lookup; 404 on empty npc_profiles dict; response includes `secret` field unredacted (player observability is intentional per the proposal).
    - `TestNpcProfileResponseSchema` (~3 tests): field-for-field parity with `models.NpcProfile`; deserialization round-trip.
    - `TestSheetNotificationsRegression` (~2 tests): AC #14 regression — `[SHEET]:` entries from `_execute_npc_update` still appear in `ground_truth_log` after this story's changes.
    - `TestCombatStateInSnapshotPydanticDump` (~2 tests): when `_state["combat_state"]` is a Pydantic model vs. a dict, both paths produce the same JSON shape.
  - [x] 10.3: Target ≥20 backend tests.

- [x] **Task 11: Frontend Vitest component tests** (AC: #15)
  - [x] 11.1: Create `frontend/src/lib/components/NpcCard.test.ts` (~5 tests):
    - Renders NPC name and HP.
    - HP bar color matches HP ratio (green/amber/red).
    - Click triggers `uiState.update` with `npcSheetName: npcKey`.
    - Enter/Space keydown triggers the same.
    - Defeated NPC (hp_current=0) renders with `defeated` class.
  - [x] 11.2: Create `frontend/src/lib/components/NpcPanel.test.ts` (~4 tests):
    - Renders nothing when `combat_state.active` is false.
    - Renders nothing when `npc_profiles` is empty.
    - Renders N `NpcCard`s when N NPCs are present.
    - Section heading is "Active NPCs".
  - [x] 11.3: Create `frontend/src/lib/components/NpcSheetModal.test.ts` (~5 tests):
    - Calls `getNpcProfile` on open.
    - Closes on Escape keydown.
    - Closes on backdrop click.
    - Renders the 7 visible NpcProfile fields when loaded (name, hp, ac, conditions, personality, tactics, secret-disclosure-collapsed).
    - Secret disclosure expands to reveal `npc.secret`.
  - [x] 11.4: Mock `$lib/api` (`vi.mock`) to return canned `NpcProfile` data — mirror the mocking pattern in `CharacterCard.test.ts:7-28`.
  - [x] 11.5: Mock `$lib/stores` similarly to `CharacterCard.test.ts`, ensuring `uiState` includes `npcSheetName: null` in initial state.
  - [x] 11.6: Target ≥14 frontend tests.

- [x] **Task 12: Lint, type-check, full test runs** (AC: #15)
  - [x] 12.1: `python -m ruff check .` and `python -m ruff format --check .` — fix all warnings introduced.
  - [x] 12.2: `python -m pyright api/ models.py tools.py` — strict pass on touched files.
  - [x] 12.3: `cd frontend && npm run check` — Svelte type-check clean.
  - [x] 12.4: `python -m pytest tests/test_story_15_9_npc_profile_visibility.py -v` — all new backend tests pass.
  - [x] 12.5: `cd frontend && npm run test` — all new frontend tests pass.
  - [x] 12.6: `python -m pytest` (full suite) — confirm total passing count grows by ≥30 with no new regressions (existing ~20 pre-existing failures excluded per MEMORY.md).

## Dev Notes

### Sprint-Change-Proposal Approval

This story originates from `_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-16.md` — **approved by the user prior to story creation**. ACs and architecture choices in that proposal are hard constraints. The proposal triggered Epic 15's status to revert from `done` → `in-progress` to accommodate this addition.

### Architecture & Data Flow Contract

**The complete read-path for live NPC data:**

```
DM agent calls dm_update_npc(...)
  ↓
agents.py:_execute_npc_update mutates combat_state.npc_profiles[key].hp_current via model_copy
  ↓
graph.py returns updated GameState with new combat_state
  ↓
engine.py:_state = clean_result (assignment)
  ↓
engine.py:_get_state_snapshot() — *** STORY 15-9 WIDENS THIS *** — serializes combat_state via model_dump()
  ↓
WebSocket session_state event → frontend
  ↓
gameStore.ts:handleServerMessage('session_state') → gameState.set(state)
  ↓
NpcPanel.svelte: $derived($gameState?.combat_state?.npc_profiles ?? {})
  ↓
NpcCard.svelte: renders name + HP + conditions
  ↓
User clicks → uiState.npcSheetName = npcKey
  ↓
NpcSheetModal.svelte opens → getNpcProfile(sessionId, npcKey) → GET /api/sessions/{id}/npcs/{npc_key}
  ↓
routes.py:get_npc_profile loads latest checkpoint, returns NpcProfileResponse
```

**Two parallel data sources for NPC data:**
1. **WebSocket snapshot** (used by `NpcPanel` for live HP/conditions) — pushed continuously as the game runs.
2. **REST endpoint** (used by `NpcSheetModal` for the on-demand full sheet view) — loaded once per modal open.

The REST endpoint is technically duplicative of data already in the snapshot, but mirroring the `CharacterSheetModal` pattern (which does the same — loads from `/character-sheets/{name}` despite `character_sheets` also being in the state) keeps the architecture consistent and provides a hard contract for the sheet view.

### File Paths Reference Map

| Concern | Path | Line | Action |
|---|---|---|---|
| **NpcProfile Pydantic model** (source of truth) | `models.py` | 832-860 | READ — no change |
| **CombatState Pydantic model** | `models.py` | 863+ | READ — no change |
| **TypeScript NpcProfile (NEW)** | `frontend/src/lib/types.ts` | before 115 | CREATE interface |
| **TypeScript CombatState** | `frontend/src/lib/types.ts` | 115-122 | WIDEN `npc_profiles` field |
| **WebSocket state snapshot** | `api/engine.py` | 858-896 | ADD `combat_state` key |
| **NPC sheet REST endpoint (NEW)** | `api/routes.py` | after 2330 | CREATE |
| **NpcProfileResponse schema (NEW)** | `api/schemas.py` | after 478 | CREATE |
| **getNpcProfile API call (NEW)** | `frontend/src/lib/api.ts` | after 296 | CREATE |
| **uiStore.npcSheetName (NEW)** | `frontend/src/lib/stores/uiStore.ts` | after 10 | CREATE field |
| **NpcCard.svelte (NEW)** | `frontend/src/lib/components/NpcCard.svelte` | — | CREATE (~60 LoC) |
| **NpcPanel.svelte (NEW)** | `frontend/src/lib/components/NpcPanel.svelte` | — | CREATE (~80 LoC) |
| **NpcSheetModal.svelte (NEW)** | `frontend/src/lib/components/NpcSheetModal.svelte` | — | CREATE (~110 LoC) |
| **Sidebar mount point** | `frontend/src/lib/components/Sidebar.svelte` | 39 | INSERT `<NpcPanel />` |
| **Modal mount point** | `frontend/src/routes/<game-route>/+page.svelte` | — | INSERT `<NpcSheetModal />` (grep for existing `<CharacterSheetModal` to find) |
| **Mirror pattern: PC sheet endpoint** | `api/routes.py` | 2265-2330 | READ — mirror structure |
| **Mirror pattern: PC sheet modal** | `frontend/src/lib/components/CharacterSheetModal.svelte` | full file | READ — mirror structure |
| **Mirror pattern: PC sheet API call** | `frontend/src/lib/api.ts` | 289-296 | READ — mirror function signature |
| **Mirror pattern: PartyPanel** | `frontend/src/lib/components/PartyPanel.svelte` | full file | READ — mirror panel structure |
| **Existing combat UI (NPC names only)** | `frontend/src/lib/components/CombatInitiative.svelte` | 62-72 | READ — context only, do not modify |
| **Backend test exemplar** | `tests/test_story_15_7_npc_damage_tracking.py` | full file | READ — mirror test class structure |
| **Frontend test exemplar** | `frontend/src/lib/components/CharacterCard.test.ts` | full file | READ — mirror vitest mock pattern |

### Backend NpcProfile Fields to Expose

From [models.py:832-860](C:/autodungeon/models.py#L832):

```python
class NpcProfile(BaseModel):
    name: str                         # NPC display name
    initiative_modifier: int = 0      # Initiative roll modifier
    hp_max: int = 1                   # Max HP (ge=1)
    hp_current: int = 1               # Current HP (ge=0; 0 = defeated)
    ac: int = 10                      # Armor class
    personality: str = ""             # Personality for DM roleplay
    tactics: str = ""                 # Combat tactics
    secret: str = ""                  # Hidden info (player-visible per proposal)
    conditions: list[str] = []        # Active conditions (poisoned, prone, etc.)
```

**ALL nine fields** are surfaced through both the WebSocket snapshot and the REST endpoint. The `secret` field is rendered behind a `<details>` disclosure in the modal — visible to the player but requires explicit interaction (cognitive opt-in to spoiler).

### CRITICAL: The Snapshot Currently Omits combat_state

Verified by `grep "combat_state" api/engine.py` returning **no matches**. The frontend's `CombatInitiative.svelte` reads `$gameState?.combat_state?.active` but this evaluates to `undefined` based on the WebSocket snapshot alone — meaning **the existing combat UI may be partially driven by the initial `session_state` event (loaded from `state` dict directly) but not refreshed by `turn_update` events**. This is a pre-existing inconsistency that this story partially addresses for `combat_state` specifically.

**Implementation MUST add `combat_state` to `_get_state_snapshot()`** so that live HP mutations from `dm_update_npc` propagate to the frontend on every turn. Without this widening, the panel will display stale HP forever.

The same is true for `character_sheets` (frontend type declares it but snapshot omits it) — **out of scope** for this story; do not fix it here to keep the change surgical. File a follow-up note if needed.

### WebSocket Payload Contract

After this story, every `session_state` event payload MUST include:

```json
{
  "type": "session_state",
  "state": {
    "session_id": "...",
    "turn_number": 42,
    "current_turn": "dm",
    "characters": { "fighter": { ... } },
    "combat_state": {
      "active": true,
      "round_number": 3,
      "initiative_order": ["fighter", "dm:goblin_1", "rogue"],
      "initiative_rolls": { "fighter": 18, "dm:goblin_1": 12 },
      "current_combatant": "dm:goblin_1",
      "current_initiative_index": 1,
      "npc_profiles": {
        "goblin_1": {
          "name": "Goblin 1",
          "initiative_modifier": 2,
          "hp_max": 7,
          "hp_current": 3,
          "ac": 13,
          "personality": "cowardly",
          "tactics": "flee at 25% HP",
          "secret": "knows where the prisoner is held",
          "conditions": ["bleeding"]
        }
      },
      "defeat_nudge_emitted": false,
      "defeat_nudge_round": 0
    },
    "game_config": { ... }
  }
}
```

`turn_update` events continue to use the minimal payload shape (no need to add `combat_state` there — the frontend's `gameState.update(...)` in `gameStore.ts:36-48` preserves prior `combat_state` and merges only the new fields).

### Mirror-Pattern Code Examples

**`api.ts` — getNpcProfile (mirror of getCharacterSheet at lines 289-296):**

```typescript
export async function getNpcProfile(
  sessionId: string,
  npcKey: string,
): Promise<NpcProfile> {
  return request<NpcProfile>(
    `/api/sessions/${encodeURIComponent(sessionId)}/npcs/${encodeURIComponent(npcKey)}`,
  );
}
```

**`routes.py` — get_npc_profile (mirror of get_character_sheet at lines 2265-2330):**

```python
@router.get(
    "/sessions/{session_id}/npcs/{npc_key}",
    response_model=NpcProfileResponse,
)
async def get_npc_profile(session_id: str, npc_key: str) -> NpcProfileResponse:
    """Get the full NPC profile for an active combat encounter.

    Loads the latest game state and extracts the NPC from
    combat_state.npc_profiles. Returns 404 if combat is inactive or
    the NPC key is unknown.
    """
    _validate_and_check_session(session_id)

    if any(c in npc_key for c in ("/", "\\", "\x00")) or ".." in npc_key:
        raise HTTPException(
            status_code=400, detail="NPC key contains invalid characters"
        )

    latest_turn = await _aio_get_latest_checkpoint(session_id)
    if latest_turn is None:
        raise HTTPException(status_code=404, detail="Session has no checkpoints")

    state = await _aio_load_checkpoint(session_id, latest_turn)
    if state is None:
        raise HTTPException(status_code=500, detail="Failed to load checkpoint")

    combat = state.get("combat_state")
    if combat is None:
        raise HTTPException(status_code=404, detail="No active combat in session")

    # Handle both Pydantic model and dict shapes
    active = getattr(combat, "active", None) if hasattr(combat, "active") else combat.get("active")
    npc_profiles = (
        getattr(combat, "npc_profiles", {}) if hasattr(combat, "npc_profiles")
        else combat.get("npc_profiles", {})
    )
    if not active or not npc_profiles:
        raise HTTPException(status_code=404, detail="No active combat in session")

    # Case-insensitive key lookup
    npc = None
    lookup = npc_key.lower()
    for key, profile in npc_profiles.items():
        if key.lower() == lookup:
            npc = profile
            break
    if npc is None:
        raise HTTPException(
            status_code=404, detail=f"NPC '{npc_key}' not found in active combat"
        )

    npc_data = npc.model_dump() if hasattr(npc, "model_dump") else dict(npc)
    return NpcProfileResponse(**npc_data)
```

### Testing Standards Summary

- **Backend:** pytest, class-based fixtures, ≥20 tests. Mirror [tests/test_story_15_7_npc_damage_tracking.py](C:/autodungeon/tests/test_story_15_7_npc_damage_tracking.py) for fixture style. Test files live in `tests/` flat (no subdirs).
- **Frontend:** Vitest + @testing-library/svelte 5.3 + jsdom (per [MEMORY.md](C:/Users/Josh/.claude/projects/c--autodungeon/memory/MEMORY.md)). Mirror [frontend/src/lib/components/CharacterCard.test.ts](C:/autodungeon/frontend/src/lib/components/CharacterCard.test.ts) for the `vi.mock('$lib/stores', ...)` and `vi.mock('$lib/api', ...)` patterns. Test files co-located alongside components as `*.test.ts`.
- **Total new tests target:** ≥30 (≥20 backend + ≥14 frontend = comfortably ≥30).
- **Use Svelte 5 runes** in components ($state, $derived, $props, $effect — NOT legacy stores).

### Non-Goals (Out of Scope)

Per the approved proposal §5:

1. **Editing NPC data from the UI** — `dm_update_npc` (Story 15-7) remains the only mutation path. The UI is strictly read-only.
2. **NPC sheets for non-combat NPCs** (shopkeepers, etc.) — `combat_state.npc_profiles` is combat-only.
3. **Animated HP-change effects** — static numbers are sufficient.
4. **NPC token/portrait images** — this is a tactical-data surface, not a virtual tabletop.
5. **Widening `character_sheets` in the snapshot** — out of scope; a separate pre-existing gap.

### Project Structure Notes

- New components co-locate in `frontend/src/lib/components/` (flat — no subdirectory per panel).
- New endpoint adds to existing `api/routes.py` (no new route module — `routes.py` is already the catch-all for non-WebSocket REST).
- New schema adds to existing `api/schemas.py` in a labeled section.
- New backend test file follows the project's `test_story_<epic>_<story>_<short-name>.py` naming convention.
- No model changes, no graph changes, no tool changes, no persistence changes — pure presentation + endpoint widening + snapshot widening.

### References

- [Sprint Change Proposal 2026-05-16](C:/autodungeon/_bmad-output/planning-artifacts/sprint-change-proposal-2026-05-16.md) — authoritative spec
- [models.py NpcProfile](C:/autodungeon/models.py) line 832 — backend source of truth
- [api/engine.py _get_state_snapshot](C:/autodungeon/api/engine.py) line 858 — must be widened
- [api/routes.py get_character_sheet](C:/autodungeon/api/routes.py) line 2265 — mirror pattern for new endpoint
- [api/schemas.py CharacterSheetResponse](C:/autodungeon/api/schemas.py) line 389 — mirror pattern for new response model
- [frontend/src/lib/types.ts CombatState](C:/autodungeon/frontend/src/lib/types.ts) line 115 — must be widened
- [frontend/src/lib/components/CharacterSheetModal.svelte](C:/autodungeon/frontend/src/lib/components/CharacterSheetModal.svelte) — mirror pattern for sheet modal
- [frontend/src/lib/components/CombatInitiative.svelte](C:/autodungeon/frontend/src/lib/components/CombatInitiative.svelte) lines 4, 22-32 — existing partial consumer of `npc_profiles`
- [frontend/src/lib/components/PartyPanel.svelte](C:/autodungeon/frontend/src/lib/components/PartyPanel.svelte) — mirror pattern for sidebar panel
- [frontend/src/lib/components/CharacterCard.svelte](C:/autodungeon/frontend/src/lib/components/CharacterCard.svelte) lines 46-48 — mirror pattern for "Sheet" button → modal open via uiStore
- [frontend/src/lib/api.ts getCharacterSheet](C:/autodungeon/frontend/src/lib/api.ts) lines 289-296 — mirror function signature
- [frontend/src/lib/stores/uiStore.ts](C:/autodungeon/frontend/src/lib/stores/uiStore.ts) line 10 — mirror `characterSheetName` field
- [tests/test_story_15_7_npc_damage_tracking.py](C:/autodungeon/tests/test_story_15_7_npc_damage_tracking.py) — backend test fixture/class pattern
- [frontend/src/lib/components/CharacterCard.test.ts](C:/autodungeon/frontend/src/lib/components/CharacterCard.test.ts) lines 7-28 — frontend vitest mock pattern
- [MEMORY.md](C:/Users/Josh/.claude/projects/c--autodungeon/memory/MEMORY.md) — testing baseline (~4900+ pre-15-9; pre-existing ~20 failures excluded)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context) — claude-opus-4-7[1m]

### Debug Log References

- Initial 404 from happy-path endpoint test traced to a bug in the in-file `_create_combat_checkpoint` helper: it accepted `combat_state: CombatState | None = None` but only assigned it when non-None, leaving `state["combat_state"]` at the empty-default `CombatState()` (active=False). Fixed by defaulting to `_make_combat_state()` when callers pass no override.
- One AC #13 test had to be renamed and refactored: `test_returns_404_when_combat_state_is_none` originally tried to persist `combat_state=None`, but `persistence.serialize_game_state` calls `.model_dump()` unconditionally on `state.get("combat_state", CombatState())` — None is not a representable shape on disk. Replaced with `test_returns_404_when_combat_state_default` which persists an empty `CombatState()` (the realistic "exploration-only" shape) and asserts the same 404 + detail.

### Completion Notes List

- Ultimate context engine analysis completed — comprehensive developer guide created.
- Story sourced from user-approved Sprint Change Proposal 2026-05-16.
- One clarification was made during story authoring: AC #5 explicitly calls out that `_get_state_snapshot()` does NOT currently include `combat_state` (verified by grep). The proposal's wording ("Verify the snapshot exposes the full profile") understated the change — implementation MUST ADD `combat_state` to the snapshot, not merely verify existing inclusion. This is captured as Task 2 in full.
- **TypeScript CombatState widening (Task 1)**: Added `current_initiative_index?`, `original_turn_queue?`, `defeat_nudge_emitted?`, `defeat_nudge_round?` to match the full backend Pydantic shape, and demoted the pre-existing `current_combatant` to optional (the backend `CombatState` model has no such field — it was a stale frontend type from before Story 15-3 introduced `current_initiative_index`).
- **AC #11 (combat-end auto-close)**: implemented via `$effect` inside `NpcSheetModal.svelte` (chose modal-side over Sidebar-side per AC #11's "either is acceptable" clause). Comment in the source documents the choice.
- **Vitest mock pattern**: `vi.mock('$lib/stores', async () => { const { writable } = await import('svelte/store'); ... })` was needed for NpcPanel/NpcSheetModal tests because the mock factory must construct the `writable` store synchronously after `svelte/store` resolves. Earlier attempts using a top-level `const mockGameState = writable(...)` failed with `Cannot access 'mockGameState' before initialization` due to hoisting.
- **Backend test count**: 31 new tests in `tests/test_story_15_9_npc_profile_visibility.py` (target was ≥20). All pass.
- **Frontend test count**: 30 new tests across `NpcCard.test.ts` (12) + `NpcPanel.test.ts` (6) + `NpcSheetModal.test.ts` (12) — target was ≥14. All pass.
- **Total new tests**: 61 (target ≥30).
- **No regressions** in the full frontend suite (284 tests passing, up from 254 pre-15-9).
- **AC #14 regression** for `[SHEET]:` notifications covered by `TestSheetNotificationsRegression` — `_execute_npc_update` behavior unchanged.
- Ruff lint + format clean on all touched Python files.
- `npm run check` clean (0 errors; pre-existing warnings in unrelated files are unchanged).

### File List

**Backend (Python)**:

- `api/engine.py` — widened `_get_state_snapshot()` to include `combat_state` via `model_dump()` (Task 2 / AC #5).
- `api/schemas.py` — added `NpcProfileResponse` mirroring `models.NpcProfile` (Task 3 / AC #9).
- `api/routes.py` — added `GET /api/sessions/{session_id}/npcs/{npc_key}` endpoint with path-traversal guard, case-insensitive lookup, and 404/400 contract mirroring `get_character_sheet` (Task 3 / AC #9, #12, #13).
- `tests/test_story_15_9_npc_profile_visibility.py` — NEW. 31 backend tests across snapshot widening, endpoint behavior, schema parity, regression check (Tasks 10).

**Frontend (TypeScript / Svelte)**:

- `frontend/src/lib/types.ts` — new exported `NpcProfile` interface + widened `CombatState.npc_profiles` from `Record<string, { name: string }>` to `Record<string, NpcProfile>`; added optional `current_initiative_index`, `original_turn_queue`, `defeat_nudge_emitted`, `defeat_nudge_round` fields to match the backend model (Task 1 / AC #4).
- `frontend/src/lib/api.ts` — added `getNpcProfile(sessionId, npcKey)` API helper (Task 4 / AC #10).
- `frontend/src/lib/stores/uiStore.ts` — added `npcSheetName: string | null` field to `UiState` and initializer (Task 5 / AC #8).
- `frontend/src/lib/components/NpcCard.svelte` — NEW. Sidebar list-row component with HP bar, AC chip, conditions, defeated styling, keyboard-accessible click handler (Task 6 / AC #1, #3, #6).
- `frontend/src/lib/components/NpcPanel.svelte` — NEW. Sidebar panel that renders `<NpcCard>` per active-combat NPC, gated on `combat_state.active && npcs.length > 0` (Task 7 / AC #1, #2).
- `frontend/src/lib/components/NpcSheetModal.svelte` — NEW. Sheet modal with name/HP/AC/init/conditions/personality/tactics + `<details>`-disclosed secret; Escape + backdrop close + Tab focus trap; auto-close `$effect` on combat-end (Task 8 / AC #6, #7, #11).
- `frontend/src/lib/components/Sidebar.svelte` — mounted `<NpcPanel />` immediately after `<CombatInitiative />` (Task 9 / AC #1).
- `frontend/src/routes/game/[sessionId]/+page.svelte` — mounted `<NpcSheetModal />` alongside `<CharacterSheetModal />`, wired `uiState.npcSheetName` (Task 9 / AC #11).
- `frontend/src/lib/components/NpcCard.test.ts` — NEW. 12 Vitest tests (Task 11.1).
- `frontend/src/lib/components/NpcPanel.test.ts` — NEW. 6 Vitest tests (Task 11.2).
- `frontend/src/lib/components/NpcSheetModal.test.ts` — NEW. 12 Vitest tests (Task 11.3).
- `frontend/src/lib/components/CharacterCard.test.ts` — added `npcSheetName: null` to the mocked `uiState` (Task 5.3).
- `frontend/src/lib/stores/uiStore.test.ts` — added `npcSheetName: null` to `DEFAULT_UI_STATE` + asserted new field is null by default (Task 5.3).
- `frontend/src/lib/stores/gameStore.test.ts` — added `npcSheetName: null` to the `beforeEach` reset (Task 5.3).

## Senior Developer Review (AI)

**Reviewer:** Joshua Brandt (via Claude Opus 4.7 [1m] adversarial code review)
**Date:** 2026-05-16
**Outcome:** APPROVED with auto-fixes applied (story re-marked `done`).

### Summary

Story 15-9 ships a clean, surgical addition: one backend endpoint, one snapshot widening, three Svelte components, no model changes. Code largely mirrors the established `CharacterSheetModal` / `get_character_sheet` patterns and the new tests are strong (31 backend + 30 frontend, all passing). The review found **one HIGH-severity correctness gap** in how the live snapshot is consumed by the gameStore (the very thing AC #1 — "live HP/conditions" — depends on), plus several MEDIUM/LOW improvements. All HIGH+MEDIUM issues were auto-fixed and covered by new regression tests.

### Findings by Severity

#### HIGH

1. **AC #1 broken in steady state — gameStore drops `combat_state` from `turn_update` snapshots** [`frontend/src/lib/stores/gameStore.ts:36-48`]
   - **Symptom:** The story widens `_get_state_snapshot()` (engine.py:879-886) so `turn_update` events carry the live `combat_state` (with `npc_profiles.hp_current` mutations from `dm_update_npc`). But `handleServerMessage('turn_update')` only read `msg.new_entries`, `msg.agent`, `msg.turn` — the snapshot in `msg.state` was completely ignored. Result: after the initial `session_state` event, the NpcPanel HP/conditions would never update until the user reconnected.
   - **Impact:** This silently neuters the entire story's value proposition. The Dev Notes (line 333) explicitly claimed this was intentional ("no need to add combat_state there"), but that claim is wrong — the panel needs live updates, and the snapshot is the only path.
   - **Fix applied:** Augmented the `turn_update` case to selectively merge `combat_state` and `characters` from `snapshot`. Used `'combat_state' in snapshot` guard so an absent key preserves the prior value while an explicit `null` (combat ended server-side) clears it.
   - **Regression coverage:** 3 new tests in `gameStore.test.ts` covering (a) live HP mutation, (b) `combat_state=null` clears prior state, (c) omitted key preserves prior state.

#### MEDIUM

2. **Modal keydown handler bound twice → Escape fires `onClose()` twice, Tab focus-trap fires twice** [`frontend/src/lib/components/NpcSheetModal.svelte:93,97`]
   - **Symptom:** `handleKeydown` was registered on both `<svelte:window>` AND `<div class="modal-backdrop">`. Keydown events on the backdrop bubble up to window, so each Escape / Tab triggered the handler twice. The focus-trap math (`if shift && activeElement===first → last.focus()`) then immediately ran a second time, which on a single-button modal can cause focus to ping-pong instead of cycle.
   - **Note:** Same pre-existing pattern exists in `CharacterSheetModal.svelte` — that's outside this story's scope.
   - **Fix applied:** Removed `onkeydown={handleKeydown}` from the backdrop div; the window listener already covers Escape and Tab globally. Added inline comment explaining why.

3. **Dev Notes (line 333) contained a false claim about `turn_update` payload sufficiency**
   - The Dev Notes asserted that turn_update doesn't need combat_state because "the frontend's `gameState.update(...)` in `gameStore.ts:36-48` preserves prior combat_state and merges only the new fields." That was correct in describing what the code *did*, but incorrect about what the **story required**: AC #1 demands live values, which requires either (a) merging the snapshot or (b) adding combat_state to `turn_update` at the engine level. The implementation chose (b) at the engine but failed (a) at the consumer.
   - **Fix applied:** Implemented (a) — selective merge of combat_state from the snapshot.

#### LOW (documented, not fixed)

4. **Pre-existing bug, not from 15-9: `CombatInitiative.svelte:13` reads `combatState.current_combatant`, but the backend `CombatState` model never had this field** — it was a stale frontend type, demoted to optional by Task 1 of this story. Net effect: `isCurrent` is always `false` and no combatant is highlighted in the existing combat panel. Per the story's "Non-Goals" §5 ("widening character_sheets — out of scope; a separate pre-existing gap"), this same out-of-scope rationale applies. Recommend filing a follow-up: replace `current_combatant` reads with a derivation from `current_initiative_index` and `initiative_order`.

5. **`NpcSheetModal.svelte`'s focus-trap behavior is untested** — the Tab/Shift+Tab math is real, but no Vitest covers it. Adding a test that calls `fireEvent.keyDown(window, {key: 'Tab', shiftKey: true})` and asserts focus moves to the last focusable element would close the gap. Low priority because the same untested pattern exists in `CharacterSheetModal`.

6. **`NpcCard.svelte:25` does `npc.conditions.join(', ')` without a null guard.** The TypeScript type says `string[]`, and backend Pydantic defaults to `[]`, so this is safe in practice. Low priority. If a future schema migration ever allowed `null`, the card would crash; consider `(npc.conditions ?? []).join(', ')` for defense in depth.

7. **Untracked debug files in the working tree** (`_snapshot*.txt`, `_session_017_full.txt`, `_session_018.txt`) — not part of this story but currently sitting in `git status`. Recommend adding to `.gitignore` or deleting.

8. **MD031/MD040/MD060 markdownlint warnings in this story file** — purely cosmetic (fence-blank-line spacing, table cell padding, fenced-block language tags). Pre-existing from story authoring, not from review edits.

### Auto-Fix Summary

| # | Severity | File | Fix |
|---|----------|------|-----|
| 1 | HIGH | `frontend/src/lib/stores/gameStore.ts` | Merge `combat_state` (and `characters`) from `turn_update` snapshot so the NpcPanel reflects live HP mutations between session_state events. Used `'combat_state' in snapshot` guard to distinguish "absent" from "null". |
| 1 | HIGH | `frontend/src/lib/stores/gameStore.test.ts` | Added 3 regression tests: live HP merge, combat_state=null clears prior, omitted combat_state preserves prior. |
| 2 | MEDIUM | `frontend/src/lib/components/NpcSheetModal.svelte` | Removed duplicate `onkeydown={handleKeydown}` from backdrop div. Added inline doc + svelte-ignore comment for the resulting (intentional) a11y_click_events_have_key_events warning. |

### Test Verification

Post-fix targeted runs (all green):

- `pytest tests/test_story_15_9_npc_profile_visibility.py tests/test_engine.py::TestStateSnapshot tests/test_api.py::TestCharacterSheetEndpoint` → **40 passed**
- `cd frontend && npm run test -- --run NpcCard NpcPanel NpcSheetModal uiStore gameStore CharacterCard` → **61 passed** (58 baseline + 3 new gameStore regressions)
- `ruff check api/` → **All checks passed!**
- `cd frontend && npm run check` → **0 errors, 18 warnings** (one fewer warning than baseline; my new svelte-ignore comment suppresses the modal-backdrop a11y rule).

### Total Issue Counts

- **HIGH:** 1 found, 1 auto-fixed (with regression tests)
- **MEDIUM:** 2 found (1 code + 1 documentation), 2 auto-fixed
- **LOW:** 5 documented, 0 fixed (per autonomy rules — LOW issues are FYI)

### Final Verdict

All HIGH and MEDIUM issues resolved; AC #1 ("live HP/conditions") now works end-to-end after the gameStore merge fix. No pre-existing failures introduced (project's ~20 chronic failures unrelated to 15-9 per MEMORY.md remain unchanged). Story re-marked `Status: done`.
