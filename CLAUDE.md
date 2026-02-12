# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Practice

**Always research before implementation/design.** Use Perplexity to research when:

- Unsure how to implement something
- There may be newer approaches or best practices you're not aware of
- Working with libraries/APIs that may have evolved since your knowledge cutoff

**Epic status tracking:** At the start/end of each epic, update the Epic Progress table in README.md to reflect current status.

**UI Testing:** For UI-related stories, use chrome-devtools MCP tools to verify acceptance criteria:
- `navigate_page` to load the app:
  - SvelteKit (primary): `http://localhost:5173`
  - FastAPI API docs: `http://localhost:8000/docs`
  - Streamlit (legacy): `http://localhost:8501`
- `take_screenshot` to capture visual state
- `resize_page` to test responsive behavior
- `take_snapshot` for accessibility tree inspection

## Project Overview

**autodungeon** is a multi-agent D&D game engine where AI agents autonomously play Dungeons & Dragons together. One DM agent orchestrates the game while N PC agents roleplay as adventurers. Humans can watch passively, drop in to control a character, or let it run fully autonomous.

**Status:** Implementing. v2.0 (FastAPI + SvelteKit) active.

## Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.10+, TypeScript 5.9+ |
| Orchestration | LangGraph 0.2.0+ (cyclical state management) |
| API | FastAPI 0.128+ (uvicorn, REST + WebSocket) |
| UI (Primary) | SvelteKit 2 + Svelte 5 (Vite 7) |
| UI (Legacy) | Streamlit 1.40.0+ (with custom CSS) |
| Data Models | Pydantic 2.0+ |
| LLM - Google | langchain-google-genai (Gemini) |
| LLM - Anthropic | langchain-anthropic (Claude) |
| LLM - Local | langchain-ollama (Llama 3, Mistral) |
| Config | PyYAML, pydantic-settings, python-dotenv |

## Commands

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

## Project Structure

```
autodungeon/
├── api/                # FastAPI backend (REST + WebSocket)
│   ├── main.py         # FastAPI entry point
│   ├── routes.py       # REST API routes
│   ├── websocket.py    # WebSocket game streaming
│   ├── engine.py       # Game engine wrapper
│   ├── schemas.py      # API request/response models
│   └── dependencies.py # FastAPI dependency injection
├── frontend/           # SvelteKit frontend
│   ├── src/
│   │   ├── routes/     # SvelteKit pages
│   │   ├── lib/        # Stores, components, utilities
│   │   └── app.html    # HTML shell
│   ├── package.json
│   └── vite.config.ts  # Vite config with API proxy
├── app.py              # Streamlit entry point (legacy)
├── graph.py            # LangGraph state machine
├── agents.py           # Agent definitions, LLM factory
├── memory.py           # MemoryManager, summarization
├── models.py           # Pydantic models (GameState, AgentMemory, etc.)
├── tools.py            # Function tools (dice rolling, scene gen)
├── persistence.py      # Checkpoint save/load, transcript export
├── config.py           # Configuration loading
├── config/             # YAML configs
│   ├── defaults.yaml
│   └── characters/
├── styles/             # CSS theming (Streamlit legacy)
├── campaigns/          # Saved game data (JSON per turn)
├── tests/              # Python test suite
├── dev.sh              # Dev startup script (Bash)
└── dev.ps1             # Dev startup script (PowerShell)
```

## Architecture Patterns

### State Management
- **GameState** is a TypedDict containing Pydantic models
- `ground_truth_log`: Append-only complete history
- `agent_memories`: Dict[str, AgentMemory] - per-agent context
- `turn_queue`: List of agent names in turn order
- `human_active` + `controlled_character`: Human intervention state

### LangGraph Orchestration (Supervisor Pattern)
- `context_manager` node: Runs before DM, triggers summarization if buffer exceeds threshold
- `dm_turn` node: Narrates, controls NPCs, routes to next agent
- `{agent}_turn` nodes: PC agents act based on their isolated memory view
- `human_intervention_node`: Pauses graph for human input

### Memory Isolation (Asymmetric)
- **PC agents**: Only see their own AgentMemory (strict isolation)
- **DM agent**: Reads ALL agent memories (enables dramatic irony)
- **Summarizer**: Compresses short_term_buffer -> long_term_summary using separate LLM

### Dual-Runtime Architecture (v2.0)
- **FastAPI backend** (`api/`): Exposes game engine via REST and WebSocket APIs
- **SvelteKit frontend** (`frontend/`): Primary browser UI, proxies to FastAPI via Vite
- **Streamlit** (`app.py`): Legacy standalone UI, connects directly to game engine

### LLM Factory Pattern
```python
def get_llm(provider: str, model: str) -> BaseChatModel
```
Supports Gemini, Claude, and Ollama with config hierarchy: defaults.yaml -> env vars -> UI overrides

### Checkpoint Format
```
campaigns/session_001/
├── config.yaml         # Campaign config
├── turn_001.json       # Full GameState snapshot
├── turn_002.json
└── transcript.json     # Append-only research export
```

## Key Documentation

- [docs/prompt.md](docs/prompt.md) - Original project vision
- [_bmad-output/planning-artifacts/prd.md](_bmad-output/planning-artifacts/prd.md) - 55 functional requirements
- [_bmad-output/planning-artifacts/architecture.md](_bmad-output/planning-artifacts/architecture.md) - Architecture decisions
- [_bmad-output/planning-artifacts/epics.md](_bmad-output/planning-artifacts/epics.md) - Epic/story breakdown
- [_bmad-output/implementation-artifacts/sprint-status.yaml](_bmad-output/implementation-artifacts/sprint-status.yaml) - Progress tracking

## Configuration

- **API Keys**: `.env` file (template: `.env.example`)
- **Defaults**: `config/defaults.yaml`
- **Characters**: `config/characters/*.yaml`
- **Override hierarchy**: YAML defaults -> environment variables -> Streamlit UI (legacy) / SvelteKit UI (primary) (runtime)

## Naming Conventions

- Python: PEP 8 (snake_case functions, PascalCase classes)
- TypeScript/Svelte: camelCase functions/variables, PascalCase components
- LangGraph nodes: `{agent}_turn` (e.g., `dm_turn`, `rogue_turn`)
- Session state keys: underscore-separated (`game`, `ui_mode`)
- API routes: `/api/v1/{resource}` (RESTful)
