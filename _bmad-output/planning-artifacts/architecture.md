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

- Primary domain: Full-stack Python (LangGraph orchestration + Streamlit UI)
- Complexity level: Medium-High
- Deployment: Self-hosted local application
- Estimated architectural components: 6-8 major modules

### Technical Constraints & Dependencies

**Explicit Technology Choices (from requirements):**
- Python 3.10+ runtime
- LangGraph for multi-agent orchestration (cyclical state management)
- Streamlit for UI (with heavy CSS customization)
- Pydantic for data models and validation
- JSON/YAML file storage (no database for MVP)

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

Full-stack Python application with predefined technology stack:

- **Orchestration**: LangGraph (cyclical state management for turn-based gameplay)
- **UI**: Streamlit (with heavy CSS customization)
- **Data Models**: Pydantic (type-safe game state)
- **LLM Integration**: LangChain chat models (multi-provider abstraction)

### Starter Approach: Clean Python Project

Given the explicitly defined technology stack and envisioned module structure, no external starter template is required. The project will be scaffolded from scratch with established Python conventions.

**Rationale:**

- Technology choices are locked (LangGraph + Streamlit + Pydantic)
- Original vision already defines sensible module breakdown
- Architectural complexity is in component integration, not scaffolding
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
├── pyproject.toml
├── .env.example
├── app.py              # Streamlit entry point
├── graph.py            # LangGraph state machine
├── agents.py           # Agent definitions, LLM factory
├── memory.py           # MemoryManager, summarization
├── models.py           # Pydantic models (GameState, AgentMemory, etc.)
├── tools.py            # Function tools (dice rolling, etc.)
├── persistence.py      # Checkpoint save/load, transcript export
├── config.py           # Configuration loading, defaults
├── styles/
│   └── theme.css       # Custom Streamlit theming
├── campaigns/          # Saved game data
│   └── .gitkeep
└── tests/
    └── ...
```

Flat layout chosen for simplicity - no import path complexity for a focused application.

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
| State Sync | Shared object | GameState in `st.session_state["game"]` |
| Async Handling | Blocking | Synchronous execution with spinner feedback |

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
3. UI (Streamlit sidebar) can override at runtime
4. Runtime changes persist to session state, optionally saved to campaign

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

### Streamlit Integration

**State Synchronization:**

- GameState lives in `st.session_state["game"]`
- LangGraph execution reads/writes to this shared object
- UI rendering reads from same object
- No polling or callbacks needed - Streamlit's rerun model handles updates

**Execution Model:**

- Graph execution is synchronous (blocking)
- UI shows spinner/loading indicator during LLM calls
- Matches UX spec: "spinner after 500ms delay"
- Async execution deferred to post-MVP if needed

**Human Intervention Flow:**

1. User clicks "Drop-In" → sets `human_active=True`, `controlled_character="rogue"`
2. Graph routes to `human_intervention_node` instead of AI node
3. Node pauses, waits for Streamlit input
4. User submits action → node completes, graph continues
5. User clicks "Release" → resets flags, AI resumes control

## Implementation Patterns & Consistency Rules

### Pattern Summary

| Category | Pattern | Convention |
|----------|---------|------------|
| Python naming | PEP 8 | snake_case functions/variables, PascalCase classes |
| Model organization | Single file | All Pydantic models in `models.py` until >500 lines |
| Model naming | No suffix | `GameState`, not `GameStateModel` |
| Node functions | Agent pattern | `{agent}_turn` (e.g., `dm_turn`, `rogue_turn`) |
| Node IDs | Lowercase short | `"dm"`, `"rogue"`, `"fighter"` |
| Session state keys | Underscore separated | `"game"`, `"ui_mode"`, `"controlled_character"` |
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

**Streamlit Session State:**

```python
st.session_state["game"]                 # GameState object
st.session_state["ui_mode"]              # "watch" | "play"
st.session_state["controlled_character"] # str | None
st.session_state["error"]                # UserError | None
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

1. Follow PEP 8 (enforced by Ruff)
2. Use type hints (enforced by Pyright)
3. Place Pydantic models in `models.py`
4. Use `{agent}_turn` node naming
5. Access state via `st.session_state["game"]`
6. Use friendly narrative for user errors

## Project Structure & Boundaries

### Complete Project Directory

```text
autodungeon/
├── pyproject.toml           # uv/pip config, dependencies
├── .env.example             # API key template
├── .gitignore
├── README.md
│
├── app.py                   # Streamlit entry point
├── graph.py                 # LangGraph state machine, nodes
├── agents.py                # Agent definitions, get_llm factory
├── memory.py                # MemoryManager, summarization
├── models.py                # Pydantic models (GameState, etc.)
├── tools.py                 # roll_dice, generate_scene
├── persistence.py           # Checkpoint save/load, transcript
├── config.py                # Pydantic Settings, config loading
│
├── config/
│   ├── defaults.yaml        # Default LLM assignments
│   └── characters/          # Character templates
│       ├── dm.yaml
│       ├── rogue.yaml
│       ├── fighter.yaml
│       └── wizard.yaml
│
├── styles/
│   └── theme.css            # Campfire aesthetic CSS
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
    └── test_persistence.py
```

### FR Category to Module Mapping

| FR Domain | Primary Module | Supporting |
|-----------|---------------|------------|
| Multi-Agent Game Loop (FR1-10) | `graph.py` | `agents.py` |
| Memory & Context (FR11-16) | `memory.py` | `models.py` |
| Human Interaction (FR17-24) | `graph.py` | `app.py` |
| Viewer Interface (FR25-32) | `app.py` | `styles/` |
| Persistence (FR33-41) | `persistence.py` | `campaigns/` |
| LLM Configuration (FR42-50) | `agents.py`, `config.py` | `config/` |
| Agent Behavior (FR51-55) | `agents.py` | `tools.py` |
| Module Selection (FR56-59) | `agents.py`, `app.py` | `models.py` |
| Character Sheets (FR60-66) | `models.py`, `tools.py` | `app.py` |
| Character Creation (FR67-70) | `app.py` | `agents.py`, `models.py` |
| DM Whisper & Secrets (FR71-75) | `tools.py`, `models.py` | `graph.py` |
| Callback Tracking (FR76-80) | `memory.py`, `models.py` | `app.py` |
| Fork Gameplay (FR81-84) | `persistence.py`, `app.py` | `models.py` |

### Architectural Boundaries

**LangGraph ↔ Streamlit:**

- Bridge: `st.session_state["game"]` holds GameState
- Graph reads/writes state, Streamlit renders it

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

## Architecture Validation

### Validation Results

| Check | Status |
|-------|--------|
| Decision Compatibility | ✅ LangGraph + Pydantic + Streamlit cohesive |
| Pattern Consistency | ✅ PEP 8, node naming, session state keys |
| Structure Alignment | ✅ Flat layout supports all decisions |
| FR Coverage | ✅ All 13 domains mapped to modules (MVP + v1.1) |
| NFR Coverage | ✅ 16GB RAM, 2min timeout addressed |
| Implementation Ready | ✅ Patterns + examples complete |
| v1.1 Models Defined | ✅ CharacterSheet, Whisper, NarrativeElement, Fork, ModuleInfo |
| v1.1 Tools Defined | ✅ update_character_sheet, whisper_to_agent, reveal_secret |
| v1.1 Context Patterns | ✅ Sheet injection, module context, whisper context |

### Architecture Readiness: READY FOR IMPLEMENTATION

**First Implementation Step:**

```bash
uv init autodungeon
cd autodungeon
uv add langgraph langchain-google-genai langchain-anthropic streamlit pydantic pyyaml python-dotenv
```

**AI Agent Guidelines:**

- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries
- Refer to this document for all architectural questions

