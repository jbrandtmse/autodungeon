# Story 16-12: Cutover & Cleanup

**Epic:** 16 — UI Framework Migration (FastAPI + SvelteKit)
**Status:** done

---

## Story

As a **developer or new contributor to the autodungeon project**,
I want **the documentation, configuration, and developer tooling updated to reflect the new FastAPI + SvelteKit architecture as the primary way to run the application**,
so that **the project README, CLAUDE.md, startup scripts, and sprint tracking all accurately represent the current dual-runtime architecture with SvelteKit as the recommended frontend and Streamlit preserved as a legacy fallback**.

---

## Acceptance Criteria

### AC1: README.md Updated with New Architecture

**Given** the current README.md documents only the Streamlit-based tech stack and startup instructions
**When** a developer reads the README
**Then** the Tech Stack table includes FastAPI, SvelteKit, Vite, and TypeScript alongside the existing Python stack
**And** the "Getting Started" section documents both the FastAPI backend (`uvicorn api.main:app --reload`) and SvelteKit frontend (`cd frontend && npm run dev`) as the PRIMARY way to run the app
**And** a "Legacy Mode (Streamlit)" subsection explains how to run `streamlit run app.py` as a backward-compatible alternative
**And** the Epic Progress table includes Epic 14 (Performance & UX Polish), Epic 15 (Combat Initiative System), and Epic 16 (UI Framework Migration) with their statuses
**And** the Project Structure section reflects the new `api/`, `frontend/`, and engine layout alongside the original flat Python files

### AC2: CLAUDE.md Updated with New Tech Stack and Commands

**Given** the current CLAUDE.md tech stack table lists only Streamlit as the UI
**When** a developer or AI assistant reads CLAUDE.md
**Then** the Tech Stack table includes:
  - `UI (Primary)` row: `SvelteKit 2 + Svelte 5 (via Vite 7)`
  - `API` row: `FastAPI 0.128+ (uvicorn)`
  - `UI (Legacy)` row: `Streamlit 1.40+ (backward-compatible)`
**And** the Commands section includes both backend and frontend startup commands
**And** the Project Structure section shows `api/`, `frontend/`, and the existing flat Python modules
**And** the UI Testing section references both `http://localhost:5173` (SvelteKit dev) and `http://localhost:8501` (Streamlit legacy)
**And** the Configuration section mentions that the override hierarchy now includes both Streamlit UI and SvelteKit UI (runtime)

### AC3: Dev Startup Script(s) Created

**Given** a developer wants to run the full stack locally
**When** they execute the startup script
**Then** a `dev.sh` script (Bash, for Git Bash / Linux / macOS) exists in the project root
**And** running `bash dev.sh` starts the FastAPI backend on port 8000 and the SvelteKit dev server on port 5173 as background processes
**And** the script prints the URLs for both servers on startup
**And** pressing Ctrl+C (SIGINT) gracefully stops both servers
**And** a `dev.ps1` script (PowerShell, for native Windows) provides equivalent functionality
**And** both scripts check for prerequisites (`uv`, `node`, `npm`) and print clear error messages if missing

### AC4: Configuration Alignment

**Given** the `.env.example` file currently only documents Python-side environment variables
**When** a developer copies `.env.example` to `.env`
**Then** the file includes a comment section noting that the SvelteKit frontend connects to the FastAPI backend via Vite proxy (no separate frontend env vars needed for local dev)
**And** `config/defaults.yaml` continues to work with both Streamlit and FastAPI runtimes without modification
**And** no new environment variables are required to run the SvelteKit frontend in development mode

### AC5: Sprint Status Finalization

**Given** the sprint-status.yaml currently shows `epic-16: in-progress` and `16-12-cutover-cleanup: backlog`
**When** this story is completed
**Then** `16-12-cutover-cleanup` is marked as `done` in sprint-status.yaml
**And** `16-11-frontend-testing` is verified as `done` (or updated if it was completed during this epic)
**And** `epic-16` is marked as `done`
**And** the overall development_status section is consistent (no in-progress stories under a done epic)

### AC6: No Game Engine Modifications

**Given** this story is documentation, configuration, and tooling only
**When** examining the git diff
**Then** zero changes exist in: `models.py`, `agents.py`, `graph.py`, `memory.py`, `tools.py`, `persistence.py`, `config.py`
**And** `app.py` is NOT deleted or modified (preserved for legacy Streamlit mode)
**And** no files under `api/` are modified (API layer is already complete)
**And** no files under `frontend/src/` are modified (frontend is already complete)

---

## Tasks / Subtasks

- [ ] **Task 1: Update README.md** (AC: 1)
  - [ ] 1.1: Update the Tech Stack table to include the full dual-runtime stack:
    ```
    | Category       | Technology                                    |
    |----------------|-----------------------------------------------|
    | Language        | Python 3.10+, TypeScript 5.9+                |
    | Orchestration   | LangGraph (cyclical state management)        |
    | API             | FastAPI + uvicorn (REST + WebSocket)          |
    | UI (Primary)    | SvelteKit 2 + Svelte 5 (via Vite 7)         |
    | UI (Legacy)     | Streamlit (backward-compatible)              |
    | Data Models     | Pydantic                                     |
    | LLM Providers   | Google Gemini, Anthropic Claude, Ollama      |
    ```
  - [ ] 1.2: Rewrite the "Getting Started / Installation" section:
    - Prerequisites: add Node.js 18+ alongside Python 3.10+ and uv
    - Add `cd frontend && npm install` step after `uv sync`
    - Primary run instructions: `bash dev.sh` (or manual two-terminal approach)
    - Add "Legacy Mode" subsection with `streamlit run app.py` instructions
  - [ ] 1.3: Update the Epic Progress table to add:
    - `Performance & UX Polish` section with Epic 14 as complete
    - `Combat Initiative System` section with Epic 15 as complete
    - `UI Framework Migration (v2.0)` section with Epic 16 as complete
  - [ ] 1.4: Update the Project Structure section to reflect the new layout:
    ```
    autodungeon/
    ├── api/                    # FastAPI backend (REST + WebSocket)
    │   ├── main.py             # FastAPI entry point
    │   ├── routes.py           # REST API routes
    │   ├── websocket.py        # WebSocket game streaming
    │   ├── engine.py           # Game engine wrapper
    │   ├── schemas.py          # API request/response models
    │   └── dependencies.py     # FastAPI dependency injection
    ├── frontend/               # SvelteKit frontend
    │   ├── src/
    │   │   ├── routes/         # SvelteKit pages
    │   │   ├── lib/            # Stores, components, utilities
    │   │   └── app.html        # HTML shell
    │   ├── package.json
    │   └── vite.config.ts      # Vite config with API proxy
    ├── app.py                  # Streamlit entry point (legacy)
    ├── graph.py                # LangGraph state machine
    ├── agents.py               # Agent definitions, LLM factory
    ├── memory.py               # MemoryManager, summarization
    ├── models.py               # Pydantic models (GameState, etc.)
    ├── tools.py                # Function tools (dice rolling, etc.)
    ├── persistence.py          # Checkpoint save/load, transcript
    ├── config.py               # Configuration loading
    ├── config/                 # YAML configs
    ├── styles/                 # CSS theming (Streamlit legacy)
    ├── campaigns/              # Saved game data (JSON per turn)
    ├── tests/                  # Python test suite
    └── dev.sh / dev.ps1        # Dev startup scripts
    ```
  - [ ] 1.5: Update the Development section to include frontend commands:
    ```bash
    # Backend
    ruff check .                  # Lint Python
    ruff format .                 # Format Python
    pyright .                     # Type check Python
    pytest                        # Run Python tests

    # Frontend
    cd frontend
    npm run check                 # Type check TypeScript/Svelte
    npm run test                  # Run Vitest suite
    npm run build                 # Production build
    ```

- [ ] **Task 2: Update CLAUDE.md** (AC: 2)
  - [ ] 2.1: Update the Tech Stack table:
    ```
    | Category       | Technology                                    |
    |----------------|-----------------------------------------------|
    | Language        | Python 3.10+, TypeScript 5.9+                |
    | Orchestration   | LangGraph 0.2.0+ (cyclical state management)|
    | API             | FastAPI 0.128+ (uvicorn, REST + WebSocket)   |
    | UI (Primary)    | SvelteKit 2 + Svelte 5 (Vite 7)             |
    | UI (Legacy)     | Streamlit 1.40.0+ (with custom CSS)          |
    | Data Models     | Pydantic 2.0+                                |
    | LLM - Google    | langchain-google-genai (Gemini)              |
    | LLM - Anthropic | langchain-anthropic (Claude)                 |
    | LLM - Local     | langchain-ollama (Llama 3, Mistral)          |
    | Config          | PyYAML, pydantic-settings, python-dotenv     |
    ```
  - [ ] 2.2: Update the Commands section to include both runtimes:
    ```bash
    # Dependency management
    uv sync                       # Install Python dependencies
    cd frontend && npm install    # Install frontend dependencies

    # Run the full stack (recommended)
    bash dev.sh                   # Starts FastAPI + SvelteKit dev servers

    # Run individually
    uvicorn api.main:app --reload         # FastAPI backend (port 8000)
    cd frontend && npm run dev            # SvelteKit frontend (port 5173)

    # Legacy Streamlit mode
    streamlit run app.py                  # Streamlit UI (port 8501)

    # Development
    ruff check .                  # Lint Python
    ruff format .                 # Format Python
    pyright .                     # Type check Python (strict mode)
    pytest                        # Run Python tests
    pytest --cov                  # Python tests with coverage
    cd frontend && npm run check  # Type check frontend
    cd frontend && npm run test   # Run frontend tests (Vitest)
    ```
  - [ ] 2.3: Update the Project Structure section to include `api/`, `frontend/`, and `dev.sh`/`dev.ps1`
  - [ ] 2.4: Update the UI Testing section to reference both ports:
    - SvelteKit dev: `http://localhost:5173`
    - FastAPI API: `http://localhost:8000`
    - Streamlit legacy: `http://localhost:8501`
  - [ ] 2.5: Update the Configuration section to note the override hierarchy now includes both UI runtimes:
    `YAML defaults -> environment variables -> Streamlit UI (legacy) / SvelteKit UI (primary) (runtime)`
  - [ ] 2.6: Update `Status:` from "Implimenting." to "Implementing. v2.0 (FastAPI + SvelteKit) active."

- [ ] **Task 3: Create dev.sh startup script** (AC: 3)
  - [ ] 3.1: Create `dev.sh` in the project root with Bash shebang
  - [ ] 3.2: Add prerequisite checks:
    - Verify `python` (or `python3`) is available and >= 3.10
    - Verify `uv` is on PATH (or fall back to `python -m uv` if applicable)
    - Verify `node` is available and >= 18
    - Verify `npm` is available
    - Print clear error messages for any missing prerequisite
  - [ ] 3.3: Start the FastAPI backend as a background process:
    ```bash
    uvicorn api.main:app --reload --port 8000 &
    BACKEND_PID=$!
    ```
  - [ ] 3.4: Start the SvelteKit dev server as a background process:
    ```bash
    cd frontend && npm run dev &
    FRONTEND_PID=$!
    cd ..
    ```
  - [ ] 3.5: Print startup banner with URLs:
    ```
    autodungeon dev servers starting...
      Backend (FastAPI):   http://localhost:8000
      Frontend (SvelteKit): http://localhost:5173
      Legacy (Streamlit):  Run 'streamlit run app.py' separately
    Press Ctrl+C to stop both servers.
    ```
  - [ ] 3.6: Set up a trap for SIGINT/SIGTERM that kills both child processes:
    ```bash
    trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0' SIGINT SIGTERM
    wait
    ```

- [ ] **Task 4: Create dev.ps1 startup script** (AC: 3)
  - [ ] 4.1: Create `dev.ps1` in the project root
  - [ ] 4.2: Add prerequisite checks (equivalent to dev.sh but in PowerShell):
    - Check for `python`, `node`, `npm`
    - Print error messages for missing prerequisites
  - [ ] 4.3: Start both servers using `Start-Process` or background jobs:
    ```powershell
    $backend = Start-Process -NoNewWindow -PassThru uvicorn -ArgumentList "api.main:app --reload --port 8000"
    $frontend = Start-Process -NoNewWindow -PassThru -WorkingDirectory "./frontend" npm -ArgumentList "run dev"
    ```
  - [ ] 4.4: Print startup banner with URLs
  - [ ] 4.5: Wait for Ctrl+C and gracefully stop both processes on exit

- [ ] **Task 5: Update .env.example** (AC: 4)
  - [ ] 5.1: Add a comment section at the end of `.env.example`:
    ```bash
    # ──────────────────────────────────────────────────────
    # SvelteKit Frontend
    # ──────────────────────────────────────────────────────
    # No additional environment variables needed for local development.
    # The SvelteKit dev server proxies API requests to FastAPI via
    # Vite config (frontend/vite.config.ts -> http://localhost:8000).
    #
    # For production builds, set:
    # PUBLIC_API_URL=https://your-api-host.example.com
    ```
  - [ ] 5.2: Verify `config/defaults.yaml` works unmodified with both runtimes (read-only check, no changes expected)

- [ ] **Task 6: Update sprint-status.yaml** (AC: 5)
  - [ ] 6.1: Set `16-11-frontend-testing` to `done` (if not already done by that story)
  - [ ] 6.2: Set `16-12-cutover-cleanup` to `done`
  - [ ] 6.3: Set `epic-16` to `done`
  - [ ] 6.4: Review all other epic-16 story entries to confirm they are `done`

- [ ] **Task 7: Verification and final checks** (AC: 6)
  - [ ] 7.1: Verify no game engine Python files are modified: check that `models.py`, `agents.py`, `graph.py`, `memory.py`, `tools.py`, `persistence.py`, `config.py` have no changes in `git diff`
  - [ ] 7.2: Verify `app.py` still exists and is unmodified
  - [ ] 7.3: Verify no files under `api/` or `frontend/src/` are modified
  - [ ] 7.4: Run `python -m pytest` to confirm existing Python tests still pass
  - [ ] 7.5: Verify `dev.sh` is executable and has correct line endings (LF, not CRLF)
  - [ ] 7.6: Verify `dev.ps1` runs without syntax errors: `powershell -Command "& { Get-Content dev.ps1 | Out-Null }"`

---

## Dev Notes

### Scope Boundaries

This story is purely about **documentation, configuration, and developer tooling**. It creates no new application code and modifies no existing application code. The only files touched are:

- `README.md` — Updated documentation
- `CLAUDE.md` — Updated AI assistant guidance
- `dev.sh` — NEW: Bash startup script
- `dev.ps1` — NEW: PowerShell startup script
- `.env.example` — Minor comment additions
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — Status updates

### Backward Compatibility

The Streamlit app (`app.py`) is explicitly **NOT** removed or modified. It continues to function as a standalone application reading from the same `config/`, `.env`, and `campaigns/` directories. Both runtimes share the same backend data layer.

The intent is that:
- New users follow the SvelteKit path (documented as primary)
- Existing users can continue using Streamlit (`streamlit run app.py`) without changes
- Both UIs can run simultaneously without conflict (they use different ports: Streamlit on 8501, SvelteKit on 5173, FastAPI on 8000)

### Dev Script Design Decisions

**Why both `dev.sh` and `dev.ps1`?** The project runs on Windows (Git Bash / MINGW64), Linux, and macOS. Bash scripts work in Git Bash on Windows but native PowerShell users need a `.ps1` alternative. The MEMORY.md notes that `uv` is not always on PATH in MINGW64, so the scripts should handle that gracefully (fall back to `python -m uvicorn` if `uvicorn` command is not found).

**Why not `npm run dev:all` or a Makefile?** A root-level shell script is the simplest approach that:
1. Does not require adding npm to the Python project root
2. Does not require Make (not default on Windows)
3. Is immediately understandable to any developer

### Vite Proxy Configuration (Already in Place)

The SvelteKit frontend already has API proxying configured in `frontend/vite.config.ts`:
```typescript
server: {
  proxy: {
    '/api': { target: 'http://localhost:8000', changeOrigin: true },
    '/ws': { target: 'http://localhost:8000', ws: true },
  },
},
```

This means the frontend dev server at `http://localhost:5173` automatically forwards `/api/*` and `/ws/*` requests to the FastAPI backend at `http://localhost:8000`. No additional configuration is needed for local development.

### CORS Configuration (Already in Place)

The FastAPI backend already has CORS middleware allowing requests from:
- `http://localhost:5173` (SvelteKit dev)
- `http://localhost:4173` (SvelteKit preview)
- `http://localhost:8501` (Streamlit)

No changes to `api/main.py` are needed.

### Port Summary

| Service         | Port | URL                       |
|-----------------|------|---------------------------|
| FastAPI backend | 8000 | `http://localhost:8000`   |
| SvelteKit dev   | 5173 | `http://localhost:5173`   |
| SvelteKit build | 4173 | `http://localhost:4173`   |
| Streamlit       | 8501 | `http://localhost:8501`   |

### What NOT to Change

- **pyproject.toml** — Already has FastAPI/uvicorn/httpx dependencies from Story 16-1
- **frontend/package.json** — Already complete from Stories 16-4 through 16-11
- **api/*.py** — Already complete from Stories 16-1 through 16-3
- **frontend/src/** — Already complete from Stories 16-4 through 16-10
- **Any game engine file** — models.py, agents.py, graph.py, memory.py, tools.py, persistence.py, config.py are untouched

### References

- [Source: README.md — Current documentation to update]
- [Source: CLAUDE.md — Current AI guidance to update]
- [Source: .env.example — Current environment template]
- [Source: config/defaults.yaml — Shared configuration, no changes needed]
- [Source: api/main.py — FastAPI entry point (port 8000, CORS already configured)]
- [Source: frontend/vite.config.ts — Vite proxy config (already proxies /api and /ws)]
- [Source: frontend/package.json — Frontend package definition (npm run dev on port 5173)]
- [Source: _bmad-output/implementation-artifacts/sprint-status.yaml — Sprint tracking to finalize]
