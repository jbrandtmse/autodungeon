# Sprint Change Proposal: Adventure Setup & Party Management

**Date:** 2026-02-08
**Triggered by:** End-to-end playtesting after completion of all 12 epics
**Scope Classification:** Minor-to-Moderate
**Recommended Approach:** Direct Adjustment (New Epic 13)

---

## Section 1: Issue Summary

### Problem Statement

During end-to-end playtesting after completion of all 12 epics, the new adventure flow was found to be missing a critical integration step. The UX specification describes a "Party Setup" screen between module selection and game start, but this screen was never implemented.

### Specific Gaps Identified

| # | Gap | Root Cause |
|---|-----|-----------|
| G1 | Sessions cannot be named — all show as "Unnamed Adventure" | Backend supports naming (`create_new_session(name=...)`), but no UI text input exists |
| G2 | Users cannot select which characters participate | All chars in `config/characters/*.yaml` auto-load; no selection step |
| G3 | Library characters cannot be used in games | Wizard saves to `library/` folder, but no bridge to session party selection |
| G4 | Character sheets empty at game start | `populate_game_state()` initializes `character_sheets={}` — agents play without mechanical data |

### Context

- **When discovered:** First real end-to-end playtest
- **Category:** Integration gaps between completed epics — not missing implementations
- **Key insight:** Individual components (character sheets, creation wizard, library, module selection, context injection, DM tools, sheet viewer) all work in isolation. The "Party Setup" screen that connects them was designed in the UX spec but never built.

### Evidence

- `app.py:8236` — `create_new_session()` called without `name` argument
- `app.py:8216-8264` — `handle_new_session_click()` jumps from module selection directly to game
- `models.py:2007-2081` — `populate_game_state()` hardcodes `character_sheets={}`
- UX spec Flow 1 and module selection flow both explicitly reference "Party Setup" as a defined step
- `config/characters/library/eden.yaml` — user-created character exists but unreachable from game flow

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Status | Impact |
|------|--------|--------|
| Epic 7 (Module Selection) | Done | Story 7.4 described 3-step flow with "Party Setup" as step 2 — that step was skipped |
| Epic 8 (Character Sheets) | Done | All 5 stories built (model, viewer, context injection, DM tools, notifications) but sheets never populated at game start |
| Epic 9 (Character Creation) | Done | Wizard and library work, but Story 9.4 assumed "party setup" screen as integration point |
| Epics 1-6, 10-12 | Done | No impact |

**No existing epics need to be reopened or rolled back.** A new cross-cutting Epic 13 addresses all gaps.

### Story Impact

No current stories require modification. Three new stories are needed:

- **13-1: Session Naming** — Add name input to adventure flow
- **13-2: Party Composition UI** — Build the Party Setup screen
- **13-3: Character Sheet Initialization** — Populate sheets at game start

### Artifact Conflicts

| Artifact | Conflict? | Action Needed |
|----------|-----------|---------------|
| PRD | No — FRs (FR1, FR9, FR10, FR70) are correctly specified | None — implementation catches up to spec |
| Architecture | No — core engine unaffected | None |
| UX Specification | No — already describes the missing Party Setup flow | None — implement as designed |
| Epics Document | Yes — needs Epic 13 definition | Add Epic 13 to `epics-v1.1.md` |
| Sprint Status | Yes — needs Epic 13 entries | Add entries to `sprint-status.yaml` |
| Tests | Yes — no integration tests for adventure setup flow | New test file needed |

### Technical Impact

- **Code changes:** `app.py` (new Party Setup view), `models.py` (populate_game_state signature + sheet init)
- **Infrastructure:** None
- **Deployment:** None
- **Breaking changes:** None — all changes are additive; backward compatible

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment (New Epic 13)

**Rationale:**

All building blocks exist. The missing piece is a single UI flow (Party Setup screen) plus one initialization function (populate character sheets). This is purely additive work — no refactoring, no model migrations, no breaking changes.

### Alternatives Considered

| Option | Verdict | Reason |
|--------|---------|--------|
| Direct Adjustment (Epic 13) | **Selected** | Clean, additive, low risk, one focused epic |
| Rollback | Rejected | Would destroy working code with zero benefit |
| MVP Scope Reduction | Not needed | MVP (Epics 1-6) is fully intact; v1.1 integration is the gap |
| Reopen Epics 7/8/9 | Rejected | Muddies sprint tracking; those epics delivered their components correctly |

### Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Party Setup UI complexity creeps | Low | UX spec already defines the design — follow it |
| Sheet initialization edge cases | Medium | Both preset and wizard chars need handling; good test coverage needed |
| Wizard sheet data not saved | Medium | Change Proposal #5 addresses this — save CharacterSheet alongside CharacterConfig |

### Effort Estimate

- **Stories:** 3
- **Complexity:** Medium overall (1 small, 2 medium)
- **Dependencies:** Linear chain (13-1 → 13-2 → 13-3)

---

## Section 4: Detailed Change Proposals

### CP-1: Epic Definition Addition

**Artifact:** `_bmad-output/planning-artifacts/epics-v1.1.md`
**Action:** Append new Epic 13 definition after Epic 12

Epic 13: Adventure Setup & Party Management — 3 stories covering session naming, party composition UI, and character sheet initialization. Addresses FR1 (configured party), FR9 (party size), FR10 (character traits), FR70 (library reuse).

### CP-2: Sprint Status Update

**Artifact:** `_bmad-output/implementation-artifacts/sprint-status.yaml`
**Action:** Add Epic 13 entries (epic-13, 13-1, 13-2, 13-3, retrospective)

### CP-3: New Adventure Flow (app.py)

**Action:** Insert Party Setup step between module selection and game start

- New `app_view` state: `"party_setup"`
- New function: `render_party_setup_ui()` — session name input, character selection grid (presets + library), "Create Character" button, party size validation
- Modify `handle_new_session_click()` — pass session name and selected characters
- Modify module selection confirmation — route to party setup instead of game

### CP-4: Game State Initialization (models.py)

**Action:** Populate character sheets at game start

- Add `selected_characters` parameter to `populate_game_state()`
- New helper: `_initialize_character_sheets()` — generates CharacterSheet from CharacterConfig for preset chars, loads saved sheet for wizard chars
- Replace `character_sheets={}` with populated dict

### CP-5: Character Sheet Storage for Library Characters

**Action:** Save full CharacterSheet data when wizard completes

- When wizard saves to library, include CharacterSheet data (abilities, equipment, skills, backstory) alongside CharacterConfig
- Enables Story 13-3 to load user's exact choices instead of auto-generating

---

## Section 5: Implementation Handoff

### Scope Classification: Minor-to-Moderate

Code changes are additive and focused, but a new epic needs to be created in the backlog.

### Handoff Plan

| Role | Responsibility |
|------|---------------|
| PM | Finalize this proposal; create Epic 13 definition in epics-v1.1.md |
| SM / Story Creator | Create detailed story files (13-1, 13-2, 13-3) with full acceptance criteria, tasks, subtasks |
| Dev | Implement stories in sequence: 13-1 → 13-2 → 13-3 |
| Code Reviewer | Adversarial review per existing code-review workflow |
| Test Architect | Integration tests for end-to-end adventure setup flow |

### Success Criteria

1. User can name a session during creation and see the name in session browser
2. User can select/deselect characters from presets and library for party composition
3. Character sheets are populated in GameState at game start
4. DM context includes all party character sheets from turn 1
5. PC context includes own character sheet from turn 1
6. DM can modify character sheets via tool calls during gameplay
7. Sheet viewer shows real data (not sample fallbacks)
8. Library characters created via wizard are playable in sessions

### What's Already Built (No Changes Needed)

These systems activate automatically once character sheets are populated:

- Character sheet context injection (agents.py — DM sees all, PC sees own)
- DM tool: `dm_update_character_sheet` (tools.py + agents.py interception)
- `apply_character_sheet_update()` (HP, conditions, equipment, currency, spells, XP)
- Character sheet viewer modal (app.py — full D&D 5e display with CSS theming)
- Sheet change notifications (app.py — narrative integration)
- Character sheet persistence (persistence.py — serialize/deserialize)
- Per-character LLM configuration (models.py + agents.py + config.py)
