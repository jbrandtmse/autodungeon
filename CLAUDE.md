# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Practice

**Always research before implementation/design.** Use Perplexity to research when:

- Unsure how to implement something
- There may be newer approaches or best practices you're not aware of
- Working with libraries/APIs that may have evolved since your knowledge cutoff

**Epic status tracking:** At the start/end of each epic, update the Epic Progress table in README.md to reflect current status.

## Project Overview

**autodungeon** is a multi-agent D&D game engine where AI agents autonomously play Dungeons & Dragons together. One DM agent orchestrates the game while N PC agents roleplay as adventurers. Humans can watch passively, drop in to control a character, or let it run fully autonomous.

**Status:** Implimenting.

## Tech Stack (Locked)

| Category | Technology |
|----------|-----------|
| Language | Python 3.10+ |
| Orchestration | LangGraph 0.2.0+ (cyclical state management) |
| UI | Streamlit 1.40.0+ (with custom CSS) |
| Data Models | Pydantic 2.0+ |
| LLM - Google | langchain-google-genai (Gemini for DM + summarizer) |
| LLM - Anthropic | langchain-anthropic (Claude for PC agents) |
| LLM - Local | langchain-ollama (Llama 3, Mistral) |
| Config | PyYAML, pydantic-settings, python-dotenv |

## Commands

```bash
# Dependency management (uses uv, not pip)
uv sync                       # Install dependencies
uv add <package>              # Add a dependency

# Run the application
streamlit run app.py

# Development
ruff check .                  # Lint
ruff format .                 # Format
pyright .                     # Type check (strict mode)
pytest                        # Run tests
pytest --cov                  # Tests with coverage
```

## Project Structure (Flat Layout)

```
autodungeon/
├── app.py              # Streamlit entry point
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
├── styles/             # CSS theming
├── campaigns/          # Saved game data (JSON per turn)
└── tests/
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
- **Summarizer**: Compresses short_term_buffer → long_term_summary using separate LLM

### LLM Factory Pattern
```python
def get_llm(provider: str, model: str) -> BaseChatModel
```
Supports Gemini, Claude, and Ollama with config hierarchy: defaults.yaml → env vars → UI overrides

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
- **Override hierarchy**: YAML defaults → environment variables → Streamlit UI (runtime)

## Naming Conventions

- Python: PEP 8 (snake_case functions, PascalCase classes)
- LangGraph nodes: `{agent}_turn` (e.g., `dm_turn`, `rogue_turn`)
- Session state keys: underscore-separated (`game`, `ui_mode`)
