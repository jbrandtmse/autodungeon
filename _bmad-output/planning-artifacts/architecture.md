---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7]
inputDocuments:
  - 'planning-artifacts/prd.md'
  - 'planning-artifacts/product-brief-autodungeon-2026-01-24.md'
  - 'planning-artifacts/ux-design-specification.md'
  - 'planning-artifacts/research/technical-autodungeon-research-2026-01-24.md'
  - 'docs/prompt.md'
workflowType: 'architecture'
project_name: 'autodungeon'
user_name: 'Developer'
date: '2026-01-25'
lastEdited: '2026-02-11'
editHistory:
  - date: '2026-02-14'
    changes: 'AI Scene Image Generation: Added SceneImage + ImageGenerationConfig models, image generation module, API endpoints, WebSocket image_ready event, config extension, FR85-FR92 module mapping. Per Sprint Change Proposal 2026-02-14.'
  - date: '2026-02-11'
    changes: 'UI framework migration: Streamlit → FastAPI + SvelteKit. Updated state sync, execution model, project layout, module mapping, boundaries. Added API layer and frontend architecture. Per Sprint Change Proposal 2026-02-11.'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

84 functional requirements organized across 13 domains (55 MVP + 29 v1.1):

| Domain | FRs | Architectural Significance |
|--------|-----|---------------------------|
| Multi-Agent Game Loop | FR1-FR10 | Core orchestration engine - DM + N PC agents with turn management |
| Memory & Context | FR11-FR16 | Independent agent memory with summarization pipeline |
| Human Interaction | FR17-FR24 | Watch/Drop-In/Nudge modes with seamless transitions |
| Viewer Interface | FR25-FR32 | Real-time narrative display with character attribution |
| Persistence & Recovery | FR33-FR41 | Auto-checkpoint, restore, transcript export |
| LLM Configuration | FR42-FR50 | Multi-provider support with per-agent model selection |
| Agent Behavior | FR51-FR55 | Improv principles, personality consistency, dice mechanics |
| Module Selection (v1.1) | FR56-FR59 | LLM-queried module discovery, context injection |
| Character Sheets (v1.1) | FR60-FR66 | Full D&D 5e sheets, DM tool updates, context injection |
| Character Creation (v1.1) | FR67-FR70 | Wizard UI, AI backstory, validation, library |
| DM Whisper & Secrets (v1.1) | FR71-FR75 | Private channels, secret tracking, revelation |
| Callback Tracking (v1.1) | FR76-FR80 | Narrative element extraction, suggestion, detection |
| Fork Gameplay (v1.1) | FR81-FR84 | Branch creation, management, comparison, resolution |

**Non-Functional Requirements:**

| Category | Requirement | Constraint |
|----------|-------------|------------|
| Performance | Memory footprint | Must run on 16GB RAM |
| Performance | Turn timeout | Up to 2 minutes acceptable |
| Performance | UI responsiveness | Async processing, never block UI |
| Integration | LLM providers | Gemini + Claude + Ollama simultaneously |
| Integration | Provider switching | Mid-campaign without data loss |
| Reliability | Checkpoint frequency | Every turn auto-saved |
| Reliability | Recovery granularity | Restore to any previous turn |
| Reliability | State consistency | Complete agent memory state restored |

**Scale & Complexity:**

- Primary domain: Client-server application (Python backend with FastAPI + SvelteKit frontend)
- Complexity level: Medium-High
- Deployment: Self-hosted local application (dual runtime: Python + Node.js)
- Estimated architectural components: 8-12 major modules (backend + API layer + frontend)

### Technical Constraints & Dependencies

**Explicit Technology Choices (from requirements):**
- Python 3.10+ runtime (backend: game engine, API layer)
- Node.js 20+ runtime (frontend: SvelteKit build and dev server)
- LangGraph for multi-agent orchestration (cyclical state management)
- FastAPI for API and WebSocket endpoints
- SvelteKit for reactive frontend UI with scoped CSS
- Pydantic for data models and validation
- JSON/YAML file storage (no database for MVP)
- ~~Streamlit for UI~~ *(deprecated — architecturally incompatible with real-time game engine; see Sprint Change Proposal 2026-02-11)*

**External Dependencies:**
- Google Gemini API (ChatGoogleGenerativeAI)
- Anthropic Claude API (ChatAnthropic)
- Ollama for local models (ChatOllama)
- Internet connectivity required for cloud LLMs

**Resource Constraints:**
- Solo developer project
- Passion project with research value (not commercial)
- Must run on consumer hardware (16GB RAM Windows machine)

### Cross-Cutting Concerns Identified

1. **State Management** - GameState model shared across orchestration, UI rendering, and persistence layers. Must maintain consistency during human drop-in/out transitions.

2. **Error Handling & Recovery** - LLM API failures must not corrupt game state. Checkpoint system provides recovery path. User-friendly error messaging required.

3. **Character Identity Flow** - Character configuration (name, class, personality, color) must flow consistently from setup through memory system to UI rendering.

4. **Logging & Research Observability** - Full transcript capture in JSON format for research analysis. Every agent interaction must be logged without impacting performance.

5. **Context Window Management** - Each agent's memory must be compressed before exceeding token limits. Summarizer model runs independently of primary agent models.

## Starter Template Evaluation

### Primary Technology Domain

Client-server application with predefined technology stack:

- **Backend**: Python 3.10+ (LangGraph orchestration, FastAPI API layer, Pydantic models)
- **Frontend**: SvelteKit 2.0+ (Svelte 5, Vite, scoped CSS, reactive stores)
- **Real-time**: WebSocket (persistent connection for game state streaming + control commands)
- **LLM Integration**: LangChain chat models (multi-provider abstraction)

### Starter Approach: Clean Project (Backend + Frontend)

Given the explicitly defined technology stack, no external starter template is required. The backend continues the established Python flat layout. The frontend is scaffolded via `npx sv create`.

**Rationale:**

- Backend technology choices are locked (LangGraph + FastAPI + Pydantic)
- Frontend benefits from SvelteKit's official scaffold for routing and build config
- Architectural complexity is in the API contract between backend and frontend
- Solo developer project benefits from simplicity over convention enforcement

### Project Scaffolding Decisions

**Dependency Management: uv**

| Option | Pros | Cons |
|--------|------|------|
| pip + requirements.txt | Simple, universal | No lock file, manual venv management |
| Poetry | Rich features, lock files | Slower resolution, heavier tooling |
| **uv** | Fast, modern, pip-compatible | Newer tool, less ecosystem maturity |

Selected: **uv** - Fast dependency resolution, built-in venv management, and simpler pyproject.toml than Poetry. Good fit for solo developer who wants modern tooling without ceremony.

**Project Layout: Flat (not src/)**

```text
autodungeon/
├── pyproject.toml           # Python dependencies (uv)
├── .env.example             # API key template
├── app.py                   # [LEGACY] Streamlit entry point (deprecated)
├── graph.py                 # LangGraph state machine
├── agents.py                # Agent definitions, LLM factory
├── memory.py                # MemoryManager, summarization
├── models.py                # Pydantic models (GameState, AgentMemory, etc.)
├── tools.py                 # Function tools (dice rolling, etc.)
├── persistence.py           # Checkpoint save/load, transcript export
├── config.py                # Configuration loading, defaults
│
├── api/                     # FastAPI application (v2.0)
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, lifespan
│   ├── routes.py            # REST endpoints (sessions, config, characters)
│   ├── websocket.py         # WebSocket endpoints (game stream, controls)
│   ├── engine.py            # GameEngine service (extracted from app.py)
│   ├── dependencies.py      # Shared dependencies (engine registry, config)
│   └── schemas.py           # API request/response models (Pydantic)
│
├── frontend/                # SvelteKit application (v2.0)
│   ├── src/
│   │   ├── routes/          # SvelteKit pages (+page.svelte, +layout.svelte)
│   │   ├── lib/
│   │   │   ├── stores/      # Svelte stores (gameState, ui, config)
│   │   │   ├── components/  # Reusable components (NarrativePanel, PartyCard, etc.)
│   │   │   └── ws.ts        # WebSocket client with auto-reconnect
│   │   └── app.css          # Global campfire theme CSS custom properties
│   ├── static/              # Static assets
│   ├── svelte.config.js
│   ├── vite.config.ts
│   └── package.json         # Node.js dependencies
│
├── styles/
│   └── theme.css            # [LEGACY] Streamlit theme (deprecated)
├── config/
│   ├── defaults.yaml
│   └── characters/
├── campaigns/               # Saved game data
└── tests/
    └── ...
```

Backend uses flat Python layout for simplicity. Frontend uses SvelteKit's standard directory structure. The API layer bridges the two.

**Development Tooling:**

| Tool | Purpose |
|------|---------|
| Ruff | Linting + formatting (replaces flake8, black, isort) |
| Pyright | Type checking (strict mode) |
| pytest | Testing framework |

**Configuration Approach:**

- Environment variables for API keys (`.env` file, python-dotenv)
- Pydantic Settings for typed configuration loading
- YAML files for character/campaign configuration

## Core Architectural Decisions

### Decision Summary

| Category | Decision | Choice |
|----------|----------|--------|
| State Schema | TypedDict + Pydantic hybrid | Pydantic models for complex structures, TypedDict wrapper for LangGraph |
| Turn Management | Supervisor pattern | DM routes to agents via conditional edges |
| Memory Trigger | Pre-turn Context Manager | Token-based threshold, checked once per cycle |
| Summarization | Synchronous | Block until complete (MVP simplicity) |
| Memory Isolation | Asymmetric | PCs isolated, DM sees all memories |
| LLM Factory | Factory function | `get_llm(provider, model)` in agents.py |
| Agent Config | Centralized + UI | Config file defaults, UI overrides |
| Checkpoint Format | Single JSON | One file per checkpoint, Pydantic serialization |
| Checkpoint Naming | Turn-based | `session_001/turn_042.json` |
| State Sync | WebSocket streaming | Backend broadcasts state updates; frontend subscribes via Svelte stores |
| Async Handling | Async event-driven | FastAPI async endpoints; autopilot runs as background task independent of client connections |

### LangGraph State Machine Architecture

**State Schema: Pydantic in TypedDict**

Complex domain objects (AgentMemory, GameConfig, CharacterConfig) are defined as Pydantic models for validation, serialization, and type safety. These are wrapped in a TypedDict for LangGraph compatibility.

```python
# models.py
class AgentMemory(BaseModel):
    long_term_summary: str
    short_term_buffer: list[str]
    token_limit: int

class GameConfig(BaseModel):
    combat_mode: Literal["Narrative", "Tactical"]
    summarizer_model: str

# graph.py
class GameState(TypedDict):
    ground_truth_log: list[str]
    turn_queue: list[str]
    current_turn: str
    agent_memories: dict[str, AgentMemory]
    game_config: GameConfig
    whisper_queue: list[str]
    human_active: bool
    controlled_character: str | None
```

**Turn Management: Supervisor with Conditional Edges**

The DM node acts as supervisor, routing to the next agent based on turn_queue and human_active state. This maps directly to D&D's structure where the DM controls narrative pacing.

```python
workflow.add_conditional_edges(
    "dm",
    route_to_next_agent,
    {
        "fighter": "fighter_node",
        "rogue": "rogue_node",
        "wizard": "wizard_node",
        "human": "human_intervention_node",
        "dm": "dm",
    }
)
```

### Memory System Architecture

**Compression Strategy:**

- Context Manager node runs once per cycle (before DM turn)
- Checks token count for each agent's short_term_buffer
- If threshold exceeded, invokes summarizer_model synchronously
- Updates long_term_summary, clears compressed messages from buffer

**Memory Isolation:**

- PC agents only see their own AgentMemory (strict isolation)
- DM agent has read access to all agent memories (enables dramatic irony, secrets)
- Ground truth log is append-only, used for checkpointing and research export

**Summarizer Prompt:** Uses the "Janitor" system prompt from original vision - preserves names, inventory, quest goals, status effects; discards verbatim dialogue, dice mechanics, repetitive descriptions.

### LLM Provider Abstraction

**Factory Pattern:**

```python
# agents.py
def get_llm(provider: str, model: str) -> BaseChatModel:
    match provider:
        case "gemini": return ChatGoogleGenerativeAI(model=model)
        case "claude": return ChatAnthropic(model=model)
        case "ollama": return ChatOllama(model=model)
        case _: raise ValueError(f"Unknown provider: {provider}")
```

**Configuration Hierarchy:**

1. Default config file (`config/defaults.yaml`) sets initial model assignments
2. Campaign config can override defaults
3. UI (Settings page) can override at runtime via REST API
4. Runtime changes persist to backend session state, optionally saved to campaign

### Persistence Strategy

**Checkpoint Format:** Single JSON file per turn

```text
campaigns/
└── session_001/
    ├── config.yaml          # Campaign configuration
    ├── turn_001.json        # Full GameState snapshot
    ├── turn_002.json
    ├── ...
    └── transcript.json      # Append-only research export
```

**Checkpoint Content:** Complete GameState including all agent memories, serialized via Pydantic's `.model_dump_json()`. Enables restore to any previous turn with full memory state.

**Transcript Format:** Separate append-only JSON file for research analysis. Each entry includes timestamp, agent name, raw output, and any tool calls.

### API Layer & Frontend Integration

**Architecture Overview:**

The system is split into three layers:
1. **Game Engine** (Python) — LangGraph orchestration, agents, memory, persistence (unchanged)
2. **API Layer** (FastAPI) — WebSocket + REST endpoints that expose the game engine to clients
3. **Frontend** (SvelteKit) — Reactive UI that consumes the API

**State Management:**

- Backend: `GameEngine` service class holds GameState per session (keyed by session_id)
- API: WebSocket broadcasts state updates to all connected clients for a session
- Frontend: `gameStore` (writable Svelte store) subscribes to WebSocket stream
- Frontend: `uiStore` (client-side only) manages sidebar state, scroll position, selected character
- Frontend: `configStore` synced to backend via REST API

**Key Principle:** UI interactions send commands via WebSocket. Backend processes commands and streams updates. No coupling between UI rendering and game engine execution. Widget interactions cannot affect the game loop.

**Execution Model:**

- Autopilot runs as an `asyncio` background task, independent of client connections
- Turn generation is async — frontend remains fully interactive during LLM calls
- WebSocket streams turn-by-turn updates as they complete
- Auto-reconnect on WebSocket drop (target: survive 12+ hour sessions)

**Human Intervention Flow:**

1. User clicks "Drop-In" → frontend sends `{type: "drop_in", character: "rogue"}` via WebSocket
2. Backend sets `human_active=True`, `controlled_character="rogue"` on GameState
3. Graph routes to `human_intervention_node` instead of AI node
4. Backend sends `{type: "awaiting_input", character: "rogue"}` to frontend
5. User submits action → frontend sends `{type: "human_action", content: "..."}` via WebSocket
6. Backend feeds action to graph, graph continues
7. User clicks "Release" → frontend sends `{type: "release_control"}`, AI resumes

**WebSocket Message Protocol:**

```
# Client → Server (commands)
{type: "start_autopilot", speed: "normal"}
{type: "stop_autopilot"}
{type: "next_turn"}
{type: "drop_in", character: "rogue"}
{type: "release_control"}
{type: "human_action", content: "I check the door for traps."}
{type: "nudge", content: "Maybe try talking to the innkeeper?"}
{type: "set_speed", speed: "fast"}

# Server → Client (updates)
{type: "turn_update", turn: 42, agent: "dm", content: "...", state: {...}}
{type: "awaiting_input", character: "rogue"}
{type: "autopilot_started"}
{type: "autopilot_stopped", reason: "user_request"}
{type: "error", message: "LLM API timeout", recoverable: true}
{type: "session_state", state: {...}}  # Full state sync on connect/reconnect
```

## Implementation Patterns & Consistency Rules

### Pattern Summary

| Category | Pattern | Convention |
|----------|---------|------------|
| Python naming | PEP 8 | snake_case functions/variables, PascalCase classes |
| Model organization | Single file | All Pydantic models in `models.py` until >500 lines |
| Model naming | No suffix | `GameState`, not `GameStateModel` |
| Node functions | Agent pattern | `{agent}_turn` (e.g., `dm_turn`, `rogue_turn`) |
| Node IDs | Lowercase short | `"dm"`, `"rogue"`, `"fighter"` |
| Svelte store names | camelCase | `gameStore`, `uiStore`, `configStore` |
| API route paths | kebab-case | `/api/sessions`, `/api/config`, `/ws/game/{session_id}` |
| Config YAML keys | Concise | `name`, `class`, `personality` |
| Error messages | Friendly narrative | Match campfire aesthetic for user-facing |

### Naming Patterns

**LangGraph Nodes:**

```python
# Node functions: {agent}_turn
def dm_turn(state: GameState) -> GameState: ...
def rogue_turn(state: GameState) -> GameState: ...
def context_manager(state: GameState) -> GameState: ...

# Node IDs: lowercase, short
workflow.add_node("dm", dm_turn)
workflow.add_node("rogue", rogue_turn)

# Router: descriptive verb
def route_to_next_agent(state: GameState) -> str: ...
```

**Svelte Stores (frontend/src/lib/stores/):**

```typescript
// gameStore.ts — subscribed to WebSocket stream
export const gameStore = writable<GameState | null>(null);

// uiStore.ts — client-side only
export const uiStore = writable({
    sidebarOpen: true,
    selectedCharacter: null as string | null,
    uiMode: 'watch' as 'watch' | 'play',
});

// configStore.ts — synced to backend via REST
export const configStore = writable<GameConfig | null>(null);
```

**API Endpoints (api/routes.py):**

```python
# REST
GET  /api/sessions              # List sessions
POST /api/sessions              # Create session
GET  /api/sessions/{id}         # Get session details
GET  /api/sessions/{id}/config  # Get session config
PUT  /api/sessions/{id}/config  # Update config
GET  /api/characters            # List character library

# WebSocket
WS   /ws/game/{session_id}      # Game state stream + control commands
```

### Format Patterns

**Character Config YAML:**

```yaml
name: "Shadowmere"
class: "Rogue"
personality: "Sardonic wit, trust issues"
color: "#6B8E6B"
provider: "claude"
model: "claude-3-haiku-20240307"
token_limit: 4000
```

**Transcript Entry:**

```json
{
  "turn": 42,
  "timestamp": "2026-01-25T14:35:22Z",
  "agent": "rogue",
  "content": "I check the door for traps.",
  "tool_calls": [{"name": "roll_dice", "args": {"notation": "1d20+7"}, "result": "18"}]
}
```

### Error Handling

**User-Facing (Friendly):**

```python
class UserError(BaseModel):
    title: str    # "The magical connection was interrupted"
    message: str  # "The spirits are not responding..."
    action: str   # "Try again or restore from checkpoint"
```

**Internal (Structured Logging):**

```python
logger.error("LLM API failed", extra={"provider": "gemini", "agent": "dm"})
```

### Enforcement

**All AI Agents MUST:**

1. Follow PEP 8 (enforced by Ruff) for Python; follow Svelte conventions for frontend
2. Use type hints (enforced by Pyright) for Python; TypeScript for frontend
3. Place Pydantic models in `models.py`; API schemas in `api/schemas.py`
4. Use `{agent}_turn` node naming for LangGraph nodes
5. Access game state via `GameEngine` service (backend) or `gameStore` (frontend)
6. Use friendly narrative for user errors
7. Never couple game engine logic to UI framework — all UI communication via API layer

## Project Structure & Boundaries

### Complete Project Directory

```text
autodungeon/
├── pyproject.toml           # Python dependencies (uv)
├── .env.example             # API key template
├── .gitignore
├── README.md
│
├── app.py                   # [LEGACY] Streamlit entry point (deprecated)
├── graph.py                 # LangGraph state machine, nodes
├── agents.py                # Agent definitions, get_llm factory
├── memory.py                # MemoryManager, summarization
├── models.py                # Pydantic models (GameState, etc.)
├── tools.py                 # roll_dice, generate_scene
├── persistence.py           # Checkpoint save/load, transcript
├── config.py                # Pydantic Settings, config loading
│
├── api/                     # FastAPI application (v2.0)
│   ├── __init__.py
│   ├── main.py              # FastAPI app, CORS, lifespan
│   ├── routes.py            # REST endpoints
│   ├── websocket.py         # WebSocket endpoints
│   ├── engine.py            # GameEngine service class
│   ├── dependencies.py      # Shared deps (engine registry)
│   └── schemas.py           # API request/response Pydantic models
│
├── frontend/                # SvelteKit application (v2.0)
│   ├── src/
│   │   ├── routes/          # SvelteKit pages
│   │   ├── lib/
│   │   │   ├── stores/      # gameStore, uiStore, configStore
│   │   │   ├── components/  # NarrativePanel, PartyCard, etc.
│   │   │   └── ws.ts        # WebSocket client
│   │   └── app.css          # Campfire theme CSS custom properties
│   ├── static/
│   ├── svelte.config.js
│   ├── vite.config.ts
│   └── package.json
│
├── config/
│   ├── defaults.yaml        # Default LLM assignments
│   └── characters/          # Character templates
│
├── styles/
│   └── theme.css            # [LEGACY] Streamlit theme (deprecated)
│
├── campaigns/               # Saved game data
│   └── session_001/
│       ├── config.yaml
│       ├── turn_001.json
│       └── transcript.json
│
└── tests/
    ├── conftest.py
    ├── test_models.py
    ├── test_memory.py
    ├── test_graph.py
    ├── test_persistence.py
    └── test_api.py          # FastAPI endpoint tests
```

### FR Category to Module Mapping

| FR Domain | Primary Module | API Layer | Frontend |
|-----------|---------------|-----------|----------|
| Multi-Agent Game Loop (FR1-10) | `graph.py` | `api/engine.py` | — |
| Memory & Context (FR11-16) | `memory.py` | — | — |
| Human Interaction (FR17-24) | `graph.py` | `api/websocket.py` | `stores/gameStore` |
| Viewer Interface (FR25-32) | — | `api/websocket.py` | `components/NarrativePanel` |
| Persistence (FR33-41) | `persistence.py` | `api/routes.py` | `routes/sessions` |
| LLM Configuration (FR42-50) | `agents.py`, `config.py` | `api/routes.py` | `routes/settings` |
| Agent Behavior (FR51-55) | `agents.py` | — | — |
| Module Selection (FR56-59) | `agents.py` | `api/routes.py` | `routes/adventure` |
| Character Sheets (FR60-66) | `models.py`, `tools.py` | `api/websocket.py` | `components/CharacterSheet` |
| Character Creation (FR67-70) | `agents.py`, `models.py` | `api/routes.py` | `routes/characters` |
| DM Whisper & Secrets (FR71-75) | `tools.py`, `models.py` | `api/websocket.py` | `components/WhisperPanel` |
| Callback Tracking (FR76-80) | `memory.py`, `models.py` | `api/websocket.py` | `components/CallbackTracker` |
| Fork Gameplay (FR81-84) | `persistence.py` | `api/routes.py` | `routes/forks` |
| AI Scene Illustration (FR85-92) | `image_gen.py` | `api/routes.py` | `components/ImageGen`, `stores/imageStore` |

### Architectural Boundaries

**Game Engine ↔ API Layer:**

- Bridge: `GameEngine` service class wraps graph execution, state management, and autopilot
- API layer instantiates `GameEngine` per session, manages lifecycle
- Game engine has zero knowledge of HTTP, WebSocket, or frontend

**API Layer ↔ Frontend:**

- Bridge: WebSocket for real-time game state streaming + bidirectional control commands
- REST for CRUD operations (sessions, config, characters)
- Frontend sends commands; backend processes and streams updates
- No shared state — all communication via explicit messages

**Memory ↔ Agents:**

- `MemoryManager.get_context(agent_name)` returns prompt-ready string
- Agents never access raw GameState directly

**Persistence ↔ State:**

- `save_checkpoint(state, session_id)` serializes full state
- `load_checkpoint(session_id, turn)` deserializes to GameState

## v1.1 Extension Architecture

### New Data Models

**CharacterSheet (models.py):**

```python
class AbilityScores(BaseModel):
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

class CharacterSheet(BaseModel):
    """Full D&D 5e character sheet for a PC."""
    # Core Identity
    name: str
    race: str
    character_class: str
    level: int = 1
    background: str = ""
    alignment: str = ""

    # Ability Scores & Modifiers
    abilities: AbilityScores = Field(default_factory=AbilityScores)

    # Combat Stats
    hit_points: int
    max_hit_points: int
    temporary_hp: int = 0
    armor_class: int
    initiative_bonus: int = 0
    speed: int = 30
    hit_dice: str = "1d8"

    # Proficiencies & Skills
    proficiency_bonus: int = 2
    saving_throws: list[str] = Field(default_factory=list)
    skills: dict[str, int] = Field(default_factory=dict)
    languages: list[str] = Field(default_factory=list)
    tool_proficiencies: list[str] = Field(default_factory=list)

    # Equipment & Resources
    equipment: list[str] = Field(default_factory=list)
    gold: int = 0

    # Spellcasting (optional)
    spellcasting_ability: str | None = None
    spell_save_dc: int | None = None
    spell_attack_bonus: int | None = None
    spell_slots: dict[int, int] = Field(default_factory=dict)  # level -> slots
    spells_known: list[str] = Field(default_factory=list)
    cantrips: list[str] = Field(default_factory=list)

    # Class Features & Traits
    class_features: list[str] = Field(default_factory=list)
    racial_traits: list[str] = Field(default_factory=list)

    # Personality (for RP context)
    personality_traits: list[str] = Field(default_factory=list)
    ideals: list[str] = Field(default_factory=list)
    bonds: list[str] = Field(default_factory=list)
    flaws: list[str] = Field(default_factory=list)
    backstory: str = ""

    # Status Effects
    conditions: list[str] = Field(default_factory=list)  # poisoned, exhausted, etc.
```

**Whisper (models.py):**

```python
class Whisper(BaseModel):
    """Private message from DM to a single agent."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    from_agent: str  # "dm" or "human"
    to_agent: str    # Target PC agent name
    content: str     # The secret information
    revealed: bool = False
    turn_created: int
    turn_revealed: int | None = None
```

**NarrativeElement (models.py):**

```python
class NarrativeElement(BaseModel):
    """Extracted narrative element for callback tracking."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    element_type: Literal["character", "item", "location", "event", "promise", "threat"]
    name: str
    description: str
    turn_introduced: int
    turns_referenced: list[int] = Field(default_factory=list)
    resolved: bool = False
```

**Fork (models.py):**

```python
class Fork(BaseModel):
    """A branched timeline from a checkpoint."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    parent_session_id: str
    parent_turn: int
    created_at: datetime = Field(default_factory=datetime.now)
    description: str = ""
    is_canonical: bool = False
```

**ModuleInfo (models.py):**

```python
class ModuleInfo(BaseModel):
    """D&D module information from LLM knowledge."""
    number: int
    name: str
    description: str
    setting: str = ""
    level_range: str = ""
```

### New Tool Definitions

**Character Sheet Tools (tools.py):**

```python
@tool
def update_character_sheet(
    character_name: str,
    updates: dict[str, Any]
) -> str:
    """Update a character's sheet. DM only.

    Args:
        character_name: Name of the character to update
        updates: Dictionary of field -> value updates
            - hit_points: int (current HP)
            - temporary_hp: int
            - equipment: list[str] (add/remove items)
            - gold: int
            - spell_slots: dict[int, int] (current remaining)
            - conditions: list[str] (status effects)

    Returns:
        Confirmation message with changes made.
    """
    ...
```

**Whisper Tools (tools.py):**

```python
@tool
def whisper_to_agent(
    target_agent: str,
    secret: str
) -> str:
    """Send a private whisper to a specific PC agent.

    The whispered information will only be visible to the target
    agent and will be injected into their context on their next turn.

    Args:
        target_agent: Name of the PC to whisper to
        secret: The secret information to share

    Returns:
        Confirmation that whisper was sent.
    """
    ...

@tool
def reveal_secret(
    whisper_id: str,
    dramatic_moment: str
) -> str:
    """Mark a secret as revealed during a dramatic moment.

    Args:
        whisper_id: ID of the whisper to reveal
        dramatic_moment: Description of how it was revealed

    Returns:
        The revealed secret content.
    """
    ...
```

### Context Injection Patterns

**Character Sheet Context:**

- DM receives all character sheets in summarized form for encounter balancing
- Each PC receives only their own character sheet
- Sheet data injected after system prompt, before memory context

```python
def get_character_sheet_context(agent_name: str, all_sheets: dict[str, CharacterSheet]) -> str:
    """Build character sheet context for an agent."""
    if agent_name == "dm":
        # DM sees all sheets (summarized)
        return format_all_sheets_summary(all_sheets)
    else:
        # PC sees only their own sheet
        return format_own_sheet(all_sheets.get(agent_name))
```

**Module Context:**

- Selected module injected into DM system prompt
- Contains setting, plot hooks, key NPCs, encounter guidelines
- Does not contain spoilers for PCs (DM context only)

```python
MODULE_CONTEXT_TEMPLATE = """
## Current Module: {module.name}

### Setting
{module.setting}

### Campaign Hooks
{module.hooks}

### Key NPCs
{module.npcs}

### Encounter Guidelines
{module.guidelines}

Use this module as inspiration while maintaining improvisational flexibility.
"""
```

**Whisper Context:**

- Pending whispers injected into target PC's context only
- Marked as [SECRET - DO NOT REVEAL DIRECTLY]
- PC should act on information without explicitly stating it

```python
WHISPER_CONTEXT_TEMPLATE = """
[SECRET - DO NOT REVEAL DIRECTLY]
You have received private information from the DM:
{whisper.content}

Act on this knowledge naturally without explicitly stating you received a whisper.
"""
```

### Callback Tracking System

**Element Extraction:**

- Run after each agent turn
- Use LLM to extract narrative elements from dialogue
- Store in NarrativeElement database

**Callback Suggestion:**

- Before DM turn, query callback database
- Suggest elements that haven't been referenced recently
- Prioritize unresolved promises and threats

**Detection & Logging:**

- After each turn, check for references to existing elements
- Update `turns_referenced` for matched elements
- Track callback rate as research metric

### Fork Management

**Storage Structure:**

```text
campaigns/
└── session_001/
    ├── config.yaml
    ├── turn_001.json
    ├── turn_042.json         # Fork point
    └── forks/
        ├── fork_abc123/
        │   ├── fork_meta.yaml  # Fork model data
        │   ├── turn_043.json   # Divergent history
        │   └── turn_044.json
        └── fork_def456/
            └── ...
```

**Fork Operations:**

1. **Create Fork:** Copy GameState at checkpoint, create new fork directory
2. **Switch Fork:** Load fork's latest state into session
3. **Compare Forks:** Side-by-side ground_truth_log display
4. **Resolve Fork:** Mark one as canonical, optionally archive others

## v2.1 Extension Architecture

### AI Scene Image Generation

**New Data Models** (`models.py`):

```python
class SceneImage(BaseModel):
    """A generated scene illustration."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    turn_number: int  # Which turn this illustrates
    prompt: str  # The text-to-image prompt used
    image_path: str  # Relative path within campaign directory
    provider: str  # "gemini"
    model: str  # "imagen-3.0-generate-002"
    generation_mode: Literal["current", "best", "specific"]
    generated_at: datetime = Field(default_factory=datetime.now)

class ImageGenerationConfig(BaseModel):
    """Configuration for AI scene image generation."""
    enabled: bool = False
    image_provider: str = "gemini"
    image_model: str = "imagen-3.0-generate-002"
    scanner_provider: str = "gemini"
    scanner_model: str = "gemini-2.5-pro"
    scanner_token_limit: int = 128000
```

**New Module** — `image_gen.py`:

- Wraps `google-genai` SDK (`client.models.generate_images()`)
- Scene-to-prompt pipeline: extract recent log entries → LLM summarizes into a vivid image prompt → generate image
- "Best scene" scanner: chunked analysis of full session history using configurable LLM
- Image storage to `campaigns/{session}/images/{image_id}.png`
- Supported models: Imagen 3 (`imagen-3.0-generate-002`), Imagen 4 (`imagen-4.0-generate-001`), Gemini 2.5 Flash Image

**New API Endpoints** (`api/routes.py`):

```python
POST /api/sessions/{session_id}/images/generate-current   # Generate image of current scene
POST /api/sessions/{session_id}/images/generate-best       # Generate image of best scene (LLM-scanned)
POST /api/sessions/{session_id}/images/generate-turn/{turn_number}  # Generate image at specific turn
GET  /api/sessions/{session_id}/images                     # List all generated images
GET  /api/sessions/{session_id}/images/{image_id}/download # Download single image (PNG)
GET  /api/sessions/{session_id}/images/download-all        # Bulk download as zip
GET  /api/sessions/images/summary                          # Lightweight summary: [{session_id, session_name, image_count}]
```

**Configuration Extension** (`config/defaults.yaml`):

```yaml
image_generation:
  enabled: false
  image_provider: gemini
  image_model: imagen-3.0-generate-002
  scanner_provider: gemini
  scanner_model: gemini-2.5-pro
  scanner_token_limit: 128000
```

**WebSocket Extension**: New `image_ready` event type for async notification when generation completes:

```json
{
  "type": "image_ready",
  "image_id": "abc-123",
  "turn_number": 42,
  "generation_mode": "current",
  "image_url": "/api/sessions/{session_id}/images/abc-123/download"
}
```

**Turn Number in Narrative**: Turn number = 1-based index in `ground_truth_log`. Computed in frontend from array index. No backend log format change needed.

**Image Storage Structure:**

```text
campaigns/
└── session_001/
    ├── config.yaml
    ├── turn_001.json
    ├── images/
    │   ├── abc123.png    # Generated scene image
    │   ├── def456.png
    │   └── images.json   # Image metadata index
    └── transcript.json
```

**Dependencies**: `google-genai`, `Pillow` (added to `pyproject.toml`)

## Architecture Validation

### Validation Results

| Check | Status |
|-------|--------|
| Decision Compatibility | ✅ LangGraph + Pydantic + FastAPI + SvelteKit cohesive |
| Pattern Consistency | ✅ PEP 8 (Python), Svelte conventions (frontend), API naming |
| Structure Alignment | ✅ Flat Python layout + SvelteKit standard structure + API bridge |
| FR Coverage | ✅ All 13 domains mapped to modules with API + frontend columns |
| NFR Coverage | ✅ 16GB RAM, 2min timeout, WebSocket stability, UI non-interruption |
| Implementation Ready | ✅ Patterns + examples + WebSocket protocol defined |
| v1.1 Models Defined | ✅ CharacterSheet, Whisper, NarrativeElement, Fork, ModuleInfo |
| v1.1 Tools Defined | ✅ update_character_sheet, whisper_to_agent, reveal_secret |
| v1.1 Context Patterns | ✅ Sheet injection, module context, whisper context |
| API Contract | ✅ REST endpoints + WebSocket message protocol documented |
| State Architecture | ✅ Backend GameEngine + frontend Svelte stores with WebSocket bridge |

### Architecture Readiness: READY FOR IMPLEMENTATION (Epic 16)

**Backend Setup:**

```bash
uv add fastapi uvicorn[standard] websockets
```

**Frontend Setup:**

```bash
npx sv create frontend
cd frontend && npm install
```

**AI Agent Guidelines:**

- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries — game engine logic in Python, UI in SvelteKit, API as the bridge
- Never import UI framework code in game engine modules
- Refer to this document for all architectural questions

