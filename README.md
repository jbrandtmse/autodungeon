# autodungeon

**Multi-agent D&D game engine where AI plays Dungeons & Dragons together.**

*"Nostalgia for D&D, made accessible for people who can't coordinate 4 friends."*

---

## What is autodungeon?

autodungeon creates a self-playing D&D party where multiple AI agents roleplay as adventurers while another AI runs the game as Dungeon Master. You can watch the adventure unfold like a living story, or drop in at any moment to take control of a character.

**The Problem:** Millions of adults who grew up playing D&D have been forced to abandon the hobby—not because they lost interest, but because coordinating 4+ schedules is nearly impossible in modern life.

**The Solution:** AI agents that play D&D together, creating emergent collaborative storytelling on your schedule.

### Key Features

- **Watch Mode** - AI party plays autonomously; watch the story unfold in real time
- **Drop-In Mode** - Take control of any character at any moment, then release when you're done
- **AI Scene Illustrations** - Hover any turn number to reveal a camera icon; click to generate fantasy artwork via Google Imagen/Gemini
- **True Party Dynamics** - Multiple LLMs interact as distinct characters with independent memories
- **Combat System** - Narrative (story-first) or Tactical (full D&D 5e initiative with per-NPC turns)
- **Fork Timeline** - Branch your adventure at any decision point and explore alternate storylines
- **Character Library** - Create, customize, and save characters with race, gender, class, abilities, and equipment
- **Module Selection** - Choose official D&D-style modules or embark on freeform adventures
- **DM Whisper & Secrets** - Send private suggestions or questions to the DM mid-game
- **Story Thread Tracking** - Narrative element extraction surfaces callbacks, foreshadowing, and plot threads
- **Memory & Summarization** - Asymmetric memory isolation with automatic long-term compression
- **Session Persistence** - Full checkpoint save/load with per-turn snapshots and transcript export
- **Multi-Provider LLMs** - Mix Gemini, Claude, and Ollama (local) models across agents
- **Full Transcript Logging** - Research-ready logs for studying multi-agent narrative behavior

## Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.10+, TypeScript 5.9+ |
| Orchestration | LangGraph (cyclical state management) |
| API | FastAPI + uvicorn (REST + WebSocket) |
| UI (Primary) | SvelteKit 2 + Svelte 5 (via Vite 7) |
| UI (Legacy) | Streamlit (backward-compatible) |
| Data Models | Pydantic |
| LLM Providers | Google Gemini, Anthropic Claude, Ollama (local) |
| Image Generation | Google Imagen / Gemini Image (via google-genai SDK) |

## Project Status

**Status: v2.1 - AI Scene Image Generation complete**

All 17 epics (92 functional requirements) have been implemented across 4 major releases.

### Epic Progress

#### MVP (v1.0)

| Epic | Description | Status |
|------|-------------|--------|
| 1 | Core Game Engine | Done |
| 2 | Streamlit Viewer Experience | Done |
| 3 | Human Participation | Done |
| 4 | Session Persistence & Recovery | Done |
| 5 | Memory & Narrative Continuity | Done |
| 6 | LLM Configuration UI | Done |

#### Enhancements (v1.1)

| Epic | Description | Status |
|------|-------------|--------|
| 7 | Module Selection & Campaign Setup | Done |
| 8 | Character Sheets | Done |
| 9 | Character Creation UI | Done |
| 10 | DM Whisper & Secrets System | Done |
| 11 | Callback Tracker | Done |
| 12 | Fork Gameplay | Done |
| 13 | Adventure Setup & Party Management | Done |

#### Performance & Combat (v1.2)

| Epic | Description | Status |
|------|-------------|--------|
| 14 | Performance & UX Polish | Done |
| 15 | Combat Initiative System | Done |

#### UI Framework Migration (v2.0)

| Epic | Description | Status |
|------|-------------|--------|
| 16 | FastAPI + SvelteKit UI | Done |

#### AI Scene Image Generation (v2.1)

| Epic | Description | Status |
|------|-------------|--------|
| 17 | AI Scene Image Generation | Done |

See the [planning artifacts](_bmad-output/planning-artifacts/) for:

- [Product Requirements Document](_bmad-output/planning-artifacts/prd.md) - 92 functional requirements
- [Architecture Decisions](_bmad-output/planning-artifacts/architecture.md) - Technical design choices
- [Epic/Story Breakdown (MVP)](_bmad-output/planning-artifacts/epics.md) - v1.0 roadmap
- [Epic/Story Breakdown (v1.1)](_bmad-output/planning-artifacts/epics-v1.1.md) - Enhancement roadmap
- [Epic/Story Breakdown (v2.1)](_bmad-output/planning-artifacts/epics-v2.1.md) - AI image generation

## Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- Node.js 18+ and npm
- API keys for at least one LLM provider (Gemini, Claude, or Ollama for local)

### Installation

```bash
# Clone the repository
git clone https://github.com/jbrandtmse/autodungeon.git
cd autodungeon

# Install Python dependencies
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..

# Copy environment template and add your API keys
cp .env.example .env
# Edit .env with your API keys
```

### Running the Application (Recommended)

The easiest way to start both servers is with the dev startup script:

```bash
# Linux / macOS / Git Bash on Windows
bash dev.sh

# PowerShell on Windows
.\dev.ps1
```

This starts the FastAPI backend on port 8000 and the SvelteKit frontend on port 5173. Press Ctrl+C to stop both servers.

Alternatively, start each server manually in separate terminals:

```bash
# Terminal 1: FastAPI backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: SvelteKit frontend
cd frontend && npm run dev
```

Then open http://localhost:5173 in your browser.

### Legacy Mode (Streamlit)

The original Streamlit UI is preserved as a backward-compatible alternative. It connects directly to the game engine without the FastAPI layer:

```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

### Configuration

- **API Keys**: Set in `.env` file (or configure via the in-app Configuration modal)
- **Game Defaults**: `config/defaults.yaml`
- **Characters**: `config/characters/*.yaml`
- **User Overrides**: `user-settings.yaml` (auto-generated by the UI)

All agent models, token limits, API keys, and image generation settings can be configured from the Configuration modal in either the SvelteKit or Streamlit UI. Changes are saved to `user-settings.yaml` and take effect on the next turn.

#### Recommended Starting Configuration

**With Ollama available** (best cost/performance balance):

| Agent | Provider | Model |
|-------|----------|-------|
| Dungeon Master | Gemini | `gemini-3-flash-preview` |
| PC Characters | Ollama | `qwen3:14b` |
| Summarizer | Gemini | `gemini-3-flash-preview` |
| Extractor | Gemini | `gemini-3-flash-preview` |

This keeps the DM and background agents (summarizer, extractor) on Gemini Flash for speed and quality, while running PC characters locally on Ollama to reduce API costs.

**Without Ollama** (cloud-only):

| Agent | Provider | Model |
|-------|----------|-------|
| Dungeon Master | Gemini | `gemini-3-flash-preview` |
| PC Characters | Gemini | `gemini-3-flash-preview` |
| Summarizer | Gemini | `gemini-3-flash-preview` |
| Extractor | Gemini | `gemini-3-flash-preview` |

Set your Google API key in `.env` as `GOOGLE_API_KEY` and all agents will use Gemini Flash. You can also mix in Claude models for PC characters if you have an Anthropic key.

### Combat Modes

autodungeon supports two combat modes, configurable per-session in the Configuration modal:

| Feature | Narrative (default) | Tactical |
|---------|-------------------|----------|
| Initiative rolls | Skipped | Full d20 + modifier per combatant |
| Turn reordering | No - fixed turn queue | Yes - sorted by initiative result |
| NPC turns | DM narrates all NPCs in a single turn | Individual NPC turns interleaved with PCs |
| Round tracking | No | Yes, with configurable max round limit |
| Combat state | Not created | Full CombatState (HP, AC, initiative, NPC profiles) |

**Narrative mode** is story-first: when the DM starts combat, no mechanics are activated. The DM narrates all NPC actions as part of their own turn and the party order stays fixed. Best for roleplay-heavy sessions where combat is dramatic flavor rather than tactical challenge.

**Tactical mode** activates the full D&D 5e initiative system. When combat starts, initiative is rolled (`1d20 + modifier`) for every PC and NPC. The turn order is reordered by initiative, NPCs get individual turns interleaved with PCs, and a DM "bookend" turn opens each round to set the scene. When combat ends, the original turn queue is restored.

### AI Scene Illustrations

autodungeon can generate fantasy artwork for any turn in your adventure using Google's image generation models. Hover over any turn number in the narrative to reveal a camera icon, then click to generate an illustration.

**Three generation modes:**

| Mode | Description |
|------|-------------|
| **Illustrate Turn** | Click the camera icon on any turn number to illustrate that specific moment |
| **Illustrate Current Scene** | Generate an image of the current scene using surrounding context |
| **Best Scene** | An LLM scans the full session history and picks the most visually compelling moment |

**Supported models:**

| Model | Description |
|-------|-------------|
| `gemini-2.5-flash-image` | Fast image generation via Gemini (default) |
| `gemini-3-pro-image-preview` | Higher quality Gemini image generation |
| `imagen-4.0-generate-001` | Google Imagen 4 |
| `imagen-4-fast` | Imagen 4 Fast |
| `imagen-4-ultra` | Imagen 4 Ultra |

Image generation is configured in the Settings tab of the Configuration modal. Generated images are stored in the campaign directory alongside turn data and can be downloaded individually or in bulk.

The prompt builder automatically includes character race and gender from their character sheets when referenced in the scene, producing more accurate illustrations.

## Architecture Overview

autodungeon uses a **supervisor pattern** where the DM agent orchestrates turns:

```
                        +-------------------+
                        | Context Manager   | <-- Monitors memory, triggers summarization
                        +---------+---------+
                                  |
                                  v
                          +-------+-------+
                          |   DM Turn     | <-- Narrates, controls NPCs, routes to next agent
                          +-------+-------+
                                  |
                                  v
                        +---------+---------+
                        |   PC Turn(s)      | <-- Each agent acts based on isolated memory
                        +---------+---------+
                                  |
                                  v
                        +---------+---------+
                        |   Human Node      | <-- Pauses for human input when active
                        +-------------------+
```

**Memory Isolation (Asymmetric):**
- PC agents only see their own memories (strict isolation)
- DM agent sees all memories (enables dramatic irony and secrets)

**Dual-Runtime Architecture (v2.0):**
- FastAPI backend exposes the game engine via REST and WebSocket APIs
- SvelteKit frontend provides the primary browser UI
- Streamlit remains as a legacy standalone alternative

## Development

```bash
# Backend (Python)
ruff check .                  # Lint Python
ruff format .                 # Format Python
pyright .                     # Type check Python
pytest                        # Run Python tests
pytest --cov                  # Python tests with coverage

# Frontend (TypeScript/Svelte)
cd frontend
npm run check                 # Type check TypeScript/Svelte
npm run test                  # Run Vitest suite
npm run build                 # Production build
```

## Project Structure

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
├── image_gen.py            # AI scene image generation service
├── image_scanner.py        # LLM-powered best scene selection
├── tools.py                # Function tools (dice rolling, etc.)
├── persistence.py          # Checkpoint save/load, transcript
├── config.py               # Configuration loading
├── config/                 # YAML configs
│   ├── defaults.yaml
│   └── characters/         # Character configs + library/
├── styles/                 # CSS theming (Streamlit legacy)
├── campaigns/              # Saved game data, images, transcripts
├── tests/                  # Python test suite
├── dev.sh                  # Dev startup script (Bash)
├── dev.ps1                 # Dev startup script (PowerShell)
├── _bmad/                  # BMAD workflow framework
├── _bmad-output/           # Planning & implementation artifacts
│   ├── planning-artifacts/ # PRD, architecture, epics
│   └── implementation-artifacts/
├── docs/                   # Project documentation
├── .claude/                # Claude Code settings
└── CLAUDE.md               # AI assistant guidance
```

## Dual Purpose

This project serves two complementary objectives:

1. **Entertainment** - Genuine D&D experience for players who can't coordinate groups
2. **Research** - Platform for studying emergent multi-agent narrative behavior

Full transcript logging enables research into:
- Narrative coherence across multiple LLMs
- Character differentiation and personality consistency
- Emergent callbacks and story development

## Contributing

Contributions, ideas, and feedback are welcome!

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with [BMAD](https://github.com/bmadcode/BMAD-METHOD) workflow methodology for AI-assisted development.
