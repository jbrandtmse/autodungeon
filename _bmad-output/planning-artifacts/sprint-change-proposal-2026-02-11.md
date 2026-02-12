# Sprint Change Proposal: UI Framework Migration — Streamlit to FastAPI + SvelteKit

**Date:** 2026-02-11
**Scope:** Major — Requires PRD update, Architecture revision, UX Design refresh, new Epics
**Risk:** Medium (proven technologies, well-understood requirements, additive not destructive)

---

## Section 1: Issue Summary

### Problem Statement

Streamlit's rerun-model architecture is fundamentally incompatible with autodungeon's core use case as a real-time, long-running game engine with interactive controls.

### Context

This issue was identified through cumulative evidence across the entire development lifecycle (Epics 2, 3, 6, 14) and confirmed definitively during Session IV live monitoring (2026-02-10/11), where 3 full Streamlit restarts were required in a 12-hour session due to:

1. **Autopilot death on widget interaction** — Any widget interaction (speed dropdown, page navigation, button click) triggers Streamlit's full script rerun, which resets the autopilot loop state
2. **WebSocket disconnections** — Multi-hour sessions drop the WebSocket connection between Streamlit frontend and backend (console error: "Cannot send rerun backMessage when disconnected")
3. **UI rendering collapse** — Sessions with 200+ turns cause blank/unresponsive UI (Epic 14 pagination was a band-aid fix)
4. **Mutually exclusive interaction** — Users must choose between controlling the game OR watching the game. "Don't touch the UI while autopilot runs" is the current workaround, which defeats the purpose of an interactive viewer.

### Evidence

| Observation | Source | Impact |
|------------|--------|--------|
| Speed change kills autopilot | Session IV Check 10-11 | Cannot adjust game speed during play |
| WebSocket disconnect after hours | Session IV Check 10 console | Frontend loses connection to backend |
| 3 forced restarts in 12 hours | Session IV Checks 7, 10, 11 | Unattended operation unreliable |
| 222-turn sessions render blank | Epic 14 trigger (Session III) | UI unusable for long sessions |
| Autopilot workaround: "don't touch UI" | Session IV operational learning | Interactive features useless during autopilot |

### Root Cause

This is not a bug — it's a **fundamental architectural mismatch**. Streamlit was designed for data exploration dashboards where reruns are the expected interaction model. Autodungeon is a real-time game engine with long-running background processes, persistent WebSocket streaming, and complex interactive state that must coexist with the running game loop.

---

## Section 2: Impact Analysis

### Epic Impact

| Epic | Status | Impact | Notes |
|------|--------|--------|-------|
| Epic 1: Core Game Engine | Done | **None** | Backend logic untouched |
| Epic 2: Streamlit Viewer | Done | **Replaced** | Entire UI layer rebuilt in SvelteKit |
| Epic 3: Human Participation | Done | **Replaced** | Drop-in/nudge/controls rebuilt |
| Epic 4: Persistence & Recovery | Done | **Minor** | API layer wraps existing persistence |
| Epic 5: Memory & Continuity | Done | **None** | Backend logic untouched |
| Epic 6: LLM Config UI | Done | **Replaced** | Settings UI rebuilt in SvelteKit |
| Epic 7: Module Selection | Done | **Partial** | Backend intact, UI rebuilt |
| Epic 8: Character Sheets | Done | **Partial** | Backend intact, viewer UI rebuilt |
| Epic 9: Character Creation | Done | **Partial** | Backend intact, wizard UI rebuilt |
| Epic 10: Whisper & Secrets | Done | **Partial** | Backend intact, whisper UI rebuilt |
| Epic 11: Callback Tracker | Done | **Partial** | Backend intact, tracker UI rebuilt |
| Epic 12: Fork Gameplay | Done | **Partial** | Backend intact, fork UI rebuilt |
| Epic 13: Adventure Setup | Done | **Partial** | Backend intact, setup UI rebuilt |
| Epic 14: Narrative Pagination | Done | **Obsolete** | SvelteKit handles virtual scrolling natively |
| Epic 15: Combat Initiative | Done | **Minor** | Backend intact, combat UI indicators rebuilt |

**Summary:** Backend (Epics 1, 4, 5, 15) fully preserved. UI layer (Epics 2, 3, 6, 14) fully replaced. Hybrid epics (7-13) keep backend logic, UI rebuilt.

### Artifact Conflicts

**PRD (Product Requirements Document):**
- Technology Stack table: Streamlit → FastAPI + SvelteKit
- FR25-32 (Viewer Interface): Remove Streamlit-specific descriptions
- NFR: Add WebSocket stability requirement, frontend build pipeline
- Deployment model: Add Node.js runtime alongside Python

**Architecture Document:**
- State sync: `st.session_state["game"]` → FastAPI WebSocket + Svelte stores
- Execution model: Synchronous blocking → async event-driven
- Module layout: Add `api/` (FastAPI), `frontend/` (SvelteKit) to project structure
- New component: API layer between game engine and frontend
- Remove: Streamlit-specific patterns, `st.markdown(unsafe_allow_html=True)` CSS injection

**UX Design Specification:**
- Design system: "Streamlit Native + Heavy Custom CSS" → "SvelteKit + Scoped CSS"
- Component specs: Redefine using Svelte components (not Streamlit widgets)
- Interaction patterns: True event-driven (not rerun-based)
- **Portable (keep as-is):** Color palette, typography, character colors, literary attribution, campfire aesthetic, accessibility requirements

**Sprint Status:**
- Add Epic 16: API Layer & Frontend Migration
- Add Epic 17: UX Design Refresh (optional — could be integrated into Epic 16)

### Technical Impact

**Files Affected:**

| File | Size | Change |
|------|------|--------|
| `app.py` | 324 KB (~9000 lines) | **Deprecated** — game engine logic extracted to API; UI code replaced by SvelteKit |
| `graph.py` | 20 KB | **Minor** — remove Streamlit session state coupling |
| `agents.py` | 108 KB | **None** — pure backend |
| `models.py` | 109 KB | **Minor** — add API serialization helpers |
| `memory.py` | 55 KB | **None** — pure backend |
| `persistence.py` | 70 KB | **None** — pure backend |
| `tools.py` | 31 KB | **None** — pure backend |
| `config.py` | 30 KB | **Minor** — expose config via API |
| `styles/theme.css` | ~5 KB | **Replaced** — SvelteKit scoped styles |
| NEW: `api/` | ~15-20 KB est. | FastAPI app, WebSocket endpoints, routes |
| NEW: `frontend/` | ~50-80 KB est. | SvelteKit app, components, stores |

**Key Insight:** The backend is cleanly separated already (models, agents, memory, persistence, tools, graph). The main coupling point is `app.py`, which mixes game engine orchestration with Streamlit UI rendering. The migration primarily means:
1. Extract game engine orchestration from `app.py` into an API service
2. Build SvelteKit frontend that consumes the API
3. `app.py` becomes legacy/optional

---

## Section 3: Recommended Approach

### Selected: Direct Adjustment — Phased Additive Migration

**Phase 0: Planning & Design (This Proposal)**
- Update PRD with new tech stack
- Revise Architecture document for client-server split
- Full UX Design refresh leveraging SvelteKit capabilities
- Create Epic 16 with stories

**Phase 1: API Layer (Epic 16, Stories 1-3)**
- Extract game engine from `app.py` into standalone service
- Create FastAPI application with WebSocket endpoints
- Game state streaming, control commands, session management
- **Both UIs can coexist** — Streamlit continues working while API is built

**Phase 2: SvelteKit Frontend (Epic 16, Stories 4-8)**
- Scaffold SvelteKit application with campfire theme
- Build narrative panel with WebSocket streaming
- Build sidebar controls (party, autopilot, speed, drop-in)
- Build settings/configuration pages
- Build adventure setup, character creation flows

**Phase 3: Feature Parity & Polish (Epic 16, Stories 9-11)**
- Fork management UI
- Callback tracker UI
- Combat UI indicators
- Keyboard shortcuts
- Mobile responsive adjustments

**Phase 4: Cutover & Cleanup (Epic 16, Story 12)**
- Deprecate `app.py` Streamlit UI
- Update deployment documentation
- Archive Streamlit-specific tests, create frontend test suite

### Rationale

1. **Additive, not destructive** — Streamlit UI continues working throughout migration. No "big bang" rewrite risk.
2. **Backend is clean** — Models, agents, memory, persistence, graph are already well-separated. The coupling is only in `app.py`.
3. **Well-understood requirements** — All 15 epics are implemented. We know exactly what the UI needs to do. No ambiguity.
4. **Proven technologies** — FastAPI and SvelteKit are both production-ready, well-documented frameworks.
5. **Solves the root cause** — SvelteKit's reactive store model and event-driven architecture directly address every Streamlit limitation we've hit.

### Effort Estimate

| Phase | Effort | Risk |
|-------|--------|------|
| Phase 0: Planning & Design | Medium | Low |
| Phase 1: API Layer | Medium | Low (well-understood patterns) |
| Phase 2: Core Frontend | High | Medium (new framework, most code) |
| Phase 3: Feature Parity | Medium | Low (requirements are known) |
| Phase 4: Cutover | Low | Low |
| **Total** | **High** | **Medium** |

### Technology Choices

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| API Framework | **FastAPI** | Python async, native WebSocket, standard |
| Frontend Framework | **SvelteKit** | Surgical DOM updates for streaming, scoped CSS, smallest bundle, simplest DX |
| Styling | **Scoped CSS** (Svelte native) | No VDOM diffing, styles co-located with components |
| State Management | **Svelte Stores** | Reactive, decoupled — sidebar doesn't affect stream |
| Real-time | **WebSocket** | Persistent connection for narrative streaming + control commands |
| Frontend Testing | **Vitest + Playwright** | SvelteKit ecosystem standard |
| Build Tool | **Vite** (via SvelteKit) | Fast HMR, production builds |

---

## Section 4: Detailed Change Proposals

### 4.1 PRD Updates

```
Document: prd.md
Section: Technology Stack (Locked)

OLD:
| UI | Streamlit 1.40.0+ (with custom CSS) |

NEW:
| API Layer | FastAPI 0.100+ (WebSocket, REST) |
| Frontend | SvelteKit 2.0+ (Svelte 5, Vite) |
| Frontend Styling | Scoped CSS (campfire theme) |
| Frontend Testing | Vitest + Playwright |
| Legacy UI | Streamlit 1.40.0+ (deprecated, maintained for fallback) |

Rationale: Streamlit's rerun model is architecturally incompatible with
real-time game engine requirements. FastAPI+SvelteKit provides event-driven
architecture with persistent WebSocket connections.
```

```
Document: prd.md
Section: FR25-32 (Viewer Interface)

OLD:
References to Streamlit widgets, st.markdown, session state

NEW:
Framework-agnostic descriptions of UI behavior:
- FR25: "Narrative display renders new messages in real-time via WebSocket stream"
- FR26: "Visual distinction between DM narration, PC dialogue, and action results using character-colored message components"
- FR27: "Character attribution uses literary 'Name, the Class:' format"
- FR28: "Scrollable history with virtual scrolling for sessions exceeding 200 turns"
(etc. — remove all Streamlit-specific implementation details from requirements)

Rationale: Requirements should describe behavior, not implementation.
This allows the frontend framework to change without PRD modifications.
```

```
Document: prd.md
Section: Non-Functional Requirements (new additions)

ADD:
| Stability | WebSocket | Connection must survive 12+ hour sessions with automatic reconnection |
| Stability | UI Interaction | User controls must not interrupt background game engine processes |
| Build | Frontend | Node.js 20+ required for SvelteKit build pipeline |
| Deployment | Dual Runtime | Python (backend) + Node.js (frontend) served together or separately |

Rationale: Addressing the specific gaps that caused Streamlit failures.
```

### 4.2 Architecture Updates

```
Document: architecture.md
Section: Project Layout

OLD:
autodungeon/
├── app.py              # Streamlit entry point
├── styles/
│   └── theme.css       # Custom Streamlit theming

NEW:
autodungeon/
├── app.py              # [LEGACY] Streamlit entry point (deprecated)
├── api/
│   ├── __init__.py
│   ├── main.py         # FastAPI application
│   ├── routes.py       # REST endpoints (sessions, config, characters)
│   ├── websocket.py    # WebSocket endpoints (game stream, controls)
│   ├── dependencies.py # Shared dependencies (game engine, config)
│   └── schemas.py      # API request/response models
├── frontend/
│   ├── src/
│   │   ├── routes/     # SvelteKit pages
│   │   ├── lib/
│   │   │   ├── stores/ # Svelte stores (gameState, ui, config)
│   │   │   ├── components/ # Reusable components
│   │   │   └── ws.ts   # WebSocket client
│   │   └── app.css     # Global campfire theme variables
│   ├── static/
│   ├── svelte.config.js
│   └── package.json
├── styles/
│   └── theme.css       # [LEGACY] Streamlit theme (deprecated)

Rationale: Clean separation — API layer exposes game engine, frontend consumes it.
```

```
Document: architecture.md
Section: State Management (new)

OLD:
State sync via st.session_state["game"] — GameState lives in Streamlit session state.
Execution model: Synchronous (blocking) — UI shows spinner during LLM calls.

NEW:
State management is split between backend and frontend:

Backend (FastAPI):
- GameState managed by game engine service (extracted from app.py)
- Each session has a GameEngine instance keyed by session_id
- WebSocket broadcasts state updates to connected clients
- Autopilot runs as an asyncio background task, independent of client connections

Frontend (SvelteKit):
- gameStore: Writable Svelte store subscribed to WebSocket game state stream
- uiStore: Client-side only (sidebar open, selected character, scroll position)
- configStore: Synced to backend via REST API

Key Principle: UI interactions send commands via WebSocket. Backend processes
commands and streams updates. No coupling between UI rendering and game engine execution.

Rationale: Complete decoupling of UI and game engine eliminates the fundamental
Streamlit problem — widget interactions cannot affect the game loop.
```

### 4.3 UX Design Specification Updates

```
Document: ux-design-specification.md
Section: Design System Choice

OLD:
"Streamlit Native + Heavy Custom CSS Theming"
- Streamlit for shell/state, config.toml + CSS for theme
- Custom CSS via st.markdown for narrative display

NEW:
"SvelteKit + Scoped Component Styling"
- SvelteKit for routing, components, and state management
- Scoped CSS per component (Svelte native feature)
- CSS custom properties for theme tokens (colors, fonts, spacing)
- No framework CSS to override — full control from the start

Rationale: Svelte's scoped styles eliminate CSS bleeding issues and the need
for unsafe_allow_html injection. Theme tokens ensure consistency across components.
```

```
Document: ux-design-specification.md
Section: Component Specifications

REQUIRES FULL REFRESH:
- NarrativePanel.svelte (replaces render_narrative_messages)
- PartyPanel.svelte (replaces render_party_panel)
- SessionControls.svelte (replaces render_session_controls)
- CharacterCard.svelte (replaces render_character_card)
- SettingsPage.svelte (replaces render_settings_tab)
- AdventureSetup.svelte (replaces render_adventure_setup)
- CharacterCreation.svelte (replaces render_character_creation)
(etc.)

PRESERVED (portable design tokens):
- Color palette: DM #D4A574, Fighter #C45C4A, Rogue #6B8E6B, Wizard #7B68B8, Cleric #4A90A4
- Typography: Lora (narrative), Inter (UI), JetBrains Mono (dice/stats)
- Literary "Name, the Class:" attribution format
- Justified text for manuscript feel
- Campfire dark aesthetic (warm tones, dark backgrounds)
- Keyboard shortcuts: 1-4 for drop-in, Escape to release
- Drop-in transition < 2 seconds, no confirmation dialogs

Rationale: Visual identity and UX patterns are framework-independent.
Component implementation changes, but the user experience should feel identical
or better.
```

### 4.4 New Epic: Epic 16 — UI Framework Migration

```yaml
# Add to sprint-status.yaml:
  # ===========================================
  # v2.0 UI FRAMEWORK MIGRATION
  # ===========================================

  # Epic 16: UI Framework Migration — FastAPI + SvelteKit (12 stories)
  epic-16: backlog
  16-1-api-layer-foundation: backlog
  16-2-game-engine-extraction: backlog
  16-3-websocket-game-streaming: backlog
  16-4-sveltekit-scaffold-theme: backlog
  16-5-narrative-panel: backlog
  16-6-sidebar-party-controls: backlog
  16-7-session-management-ui: backlog
  16-8-settings-configuration-ui: backlog
  16-9-character-creation-library: backlog
  16-10-advanced-features-ui: backlog
  16-11-frontend-testing: backlog
  16-12-cutover-cleanup: backlog
```

**Story Breakdown:**

| Story | Title | Scope |
|-------|-------|-------|
| 16-1 | API Layer Foundation | FastAPI app, CORS, session mgmt, REST routes for config/characters/sessions |
| 16-2 | Game Engine Extraction | Extract orchestration from app.py into standalone service class |
| 16-3 | WebSocket Game Streaming | WS endpoints for game state stream, control commands, auto-reconnect |
| 16-4 | SvelteKit Scaffold & Theme | Project setup, campfire CSS tokens, layout shell, WebSocket store |
| 16-5 | Narrative Panel | Message components, virtual scrolling, auto-scroll, DM/PC styling |
| 16-6 | Sidebar & Party Controls | Party panel, drop-in buttons, autopilot controls, speed selector |
| 16-7 | Session Management UI | Home page, session list, adventure setup, "While you were away" |
| 16-8 | Settings & Configuration | API keys, model selection, context limits, display settings |
| 16-9 | Character Creation & Library | Creation wizard, AI backstory, validation, library browser |
| 16-10 | Advanced Features UI | Fork management, callback tracker, combat indicators, whispers |
| 16-11 | Frontend Testing | Vitest unit tests, Playwright E2E tests, CI integration |
| 16-12 | Cutover & Cleanup | Deprecate app.py, update docs, archive Streamlit tests |

---

## Section 5: Implementation Handoff

### Change Scope Classification: **Major**

This is a fundamental architectural change affecting the entire UI layer. It requires:

1. **Product Manager:** PRD updates (tech stack, requirements language)
2. **Solution Architect:** Architecture document revision (client-server split, API design)
3. **UX Designer:** Full UX design refresh for SvelteKit components
4. **Development Team:** Epic 16 implementation (12 stories)

### Handoff Plan

| Step | Agent/Role | Deliverable | Dependency |
|------|-----------|-------------|------------|
| 1 | PM | Updated PRD | This proposal approved |
| 2 | Architect | Revised Architecture doc | Updated PRD |
| 3 | UX Designer | SvelteKit UX Design Spec | Revised Architecture |
| 4 | SM | Sprint planning for Epic 16 | UX Design complete |
| 5 | Dev | Epic 16 implementation | Sprint planned |

### Success Criteria

1. FastAPI WebSocket endpoint streams game state updates to connected clients
2. SvelteKit frontend renders narrative in real-time without interrupting autopilot
3. All interactive controls (speed, drop-in, nudge, pause) work during autopilot
4. 12+ hour sessions maintain stable WebSocket connection with auto-reconnect
5. Visual parity with current Streamlit campfire theme
6. All existing backend tests continue to pass
7. Frontend test suite achieves 80%+ coverage
8. Streamlit app.py deprecated but preserved as fallback

---

## Appendix: Technology Research

### Why SvelteKit over React/Next.js?

| Factor | SvelteKit | React/Next.js |
|--------|-----------|---------------|
| Bundle size | ~15KB | ~85KB |
| Streaming DOM updates | Surgical (no VDOM) | VDOM diffing per chunk |
| CSS | Scoped by default | Requires CSS modules/Tailwind |
| State management | Built-in stores | Requires Redux/Zustand |
| DX for solo dev | Simpler mental model | More boilerplate |
| Ecosystem | Smaller but sufficient | Massive |

**Decision:** SvelteKit's reactive model is purpose-built for streaming text with independent sidebar controls — the exact use case autodungeon needs.

### Why Not Reflex (Python-only)?

- Still in v0.8, APIs subject to change
- Unclear WebSocket streaming performance for large text payloads
- Limited production validation for this exact use case
- Risk of hitting framework limitations mid-migration
