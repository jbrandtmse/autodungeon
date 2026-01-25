# Story 1.1: Project Foundation & Configuration

Status: ready-for-dev

## Story

As a **developer**,
I want **a properly scaffolded Python project with dependency management and configuration loading**,
so that **I can install dependencies, configure API keys, and run the application**.

## Acceptance Criteria

1. **Given** a fresh clone of the repository
   **When** I run `uv sync`
   **Then** all dependencies are installed (langgraph, langchain-google-genai, langchain-anthropic, langchain-ollama, streamlit, pydantic, pyyaml, python-dotenv)
   **And** the virtual environment is created automatically

2. **Given** a `.env.example` file exists in the project root
   **When** I copy it to `.env` and fill in my API keys
   **Then** the application can read GOOGLE_API_KEY, ANTHROPIC_API_KEY, and OLLAMA_BASE_URL

3. **Given** a `config/defaults.yaml` file exists
   **When** the application starts
   **Then** default configuration values are loaded via Pydantic Settings
   **And** environment variables override config file values

4. **Given** the project structure follows the flat layout from Architecture
   **When** I examine the project
   **Then** I see: `app.py`, `graph.py`, `agents.py`, `memory.py`, `models.py`, `tools.py`, `persistence.py`, `config.py`, `config/`, `styles/`, `campaigns/`, `tests/`

## Tasks / Subtasks

- [ ] Task 1: Initialize Python project with uv (AC: #1)
  - [ ] 1.1 Run `uv init autodungeon` to create project scaffold
  - [ ] 1.2 Configure pyproject.toml with project metadata
  - [ ] 1.3 Add all required dependencies via `uv add`
  - [ ] 1.4 Verify `uv sync` creates venv and installs all packages

- [ ] Task 2: Create project directory structure (AC: #4)
  - [ ] 2.1 Create flat layout with all required module files (empty placeholders)
  - [ ] 2.2 Create `config/` directory with `defaults.yaml`
  - [ ] 2.3 Create `config/characters/` directory for character templates
  - [ ] 2.4 Create `styles/` directory with placeholder `theme.css`
  - [ ] 2.5 Create `campaigns/` directory with `.gitkeep`
  - [ ] 2.6 Create `tests/` directory with `conftest.py` placeholder

- [ ] Task 3: Implement environment variable configuration (AC: #2)
  - [ ] 3.1 Create `.env.example` with all required API key placeholders
  - [ ] 3.2 Add `.env` to `.gitignore`
  - [ ] 3.3 Create `config.py` with python-dotenv loading
  - [ ] 3.4 Implement API key validation (warn if missing, don't crash)

- [ ] Task 4: Implement Pydantic Settings configuration (AC: #3)
  - [ ] 4.1 Create `AppConfig` Pydantic Settings model in `config.py`
  - [ ] 4.2 Load defaults from `config/defaults.yaml`
  - [ ] 4.3 Implement environment variable override hierarchy
  - [ ] 4.4 Export singleton config instance for application use

- [ ] Task 5: Setup development tooling
  - [ ] 5.1 Configure Ruff for linting/formatting in pyproject.toml
  - [ ] 5.2 Configure Pyright for type checking
  - [ ] 5.3 Configure pytest for testing
  - [ ] 5.4 Create basic test to verify config loading works

- [ ] Task 6: Create minimal app.py entry point
  - [ ] 6.1 Create Streamlit app that loads config
  - [ ] 6.2 Display config status (which API keys are set)
  - [ ] 6.3 Verify app runs with `streamlit run app.py`

## Dev Notes

### Architecture Compliance

This story establishes the foundation that ALL subsequent stories build upon. Follow these decisions EXACTLY:

**Dependency Management: uv (MANDATORY)**
- Selected over pip/poetry for fast resolution and built-in venv management
- Use `pyproject.toml` (not requirements.txt)
- [Source: architecture.md#Starter Approach]

**Project Layout: Flat (NOT src/)**
```
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
├── config/
│   ├── defaults.yaml   # Default LLM assignments
│   └── characters/     # Character templates
├── styles/
│   └── theme.css       # Custom Streamlit theming
├── campaigns/          # Saved game data
│   └── .gitkeep
└── tests/
    └── conftest.py
```
[Source: architecture.md#Project Scaffolding Decisions]

**Development Tooling (MANDATORY)**
| Tool | Purpose |
|------|---------|
| Ruff | Linting + formatting (replaces flake8, black, isort) |
| Pyright | Type checking (strict mode) |
| pytest | Testing framework |

[Source: architecture.md#Project Scaffolding Decisions]

### Required Dependencies

```toml
[project]
dependencies = [
    "langgraph>=0.2.0",
    "langchain-google-genai>=2.0.0",
    "langchain-anthropic>=0.2.0",
    "langchain-ollama>=0.2.0",
    "streamlit>=1.40.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "pyyaml>=6.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "ruff>=0.8.0",
    "pyright>=1.1.0",
]
```

### Configuration Hierarchy

1. `config/defaults.yaml` - Base configuration values
2. Environment variables (`.env` file) - Override defaults
3. Runtime UI changes - Session-level overrides (future stories)

[Source: architecture.md#LLM Provider Abstraction]

### .env.example Contents

```bash
# LLM Provider API Keys
GOOGLE_API_KEY=your-google-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# Ollama Configuration (local models)
OLLAMA_BASE_URL=http://localhost:11434

# Optional: Override default models
# DEFAULT_DM_PROVIDER=gemini
# DEFAULT_DM_MODEL=gemini-1.5-flash
```

### config/defaults.yaml Contents

```yaml
# Default LLM Configuration
default_provider: gemini
default_model: gemini-1.5-flash

# Per-agent defaults (can override)
agents:
  dm:
    provider: gemini
    model: gemini-1.5-flash
    token_limit: 8000
  summarizer:
    provider: gemini
    model: gemini-1.5-flash
    token_limit: 4000

# Game defaults
party_size: 4
auto_save: true
```

### Pydantic Settings Pattern

```python
# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import yaml
from pathlib import Path

class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Keys
    google_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    # Defaults (loaded from YAML, overridable by env)
    default_provider: str = "gemini"
    default_model: str = "gemini-1.5-flash"

    @classmethod
    def load(cls) -> "AppConfig":
        """Load config with YAML defaults + env overrides."""
        # Implementation in Task 4
```

[Source: architecture.md#Configuration Approach]

### Testing Requirements

Write tests that verify:
1. `uv sync` installs all dependencies (integration test, can be manual)
2. `.env` loading works correctly
3. Config hierarchy works (env overrides yaml)
4. Missing API keys produce warnings, not crashes

### Project Structure Notes

- Flat layout chosen for simplicity - no import path complexity
- All Pydantic models go in `models.py` (until >500 lines)
- Configuration loading centralized in `config.py`
- `campaigns/` directory created but empty (used by Story 4.1)

### References

- [architecture.md#Starter Approach: Clean Python Project]
- [architecture.md#Project Scaffolding Decisions]
- [architecture.md#LLM Provider Abstraction]
- [architecture.md#Implementation Patterns & Consistency Rules]
- [prd.md#LLM Configuration]

### Critical Constraints

1. **Python 3.10+ required** - Use modern type hints (str | None, not Optional[str])
2. **No database** - File-based storage only for MVP
3. **Must run on 16GB RAM** - Keep imports lazy where possible
4. **Strict typing** - Pyright strict mode, all functions typed

### What NOT To Do

- Do NOT use Poetry (use uv)
- Do NOT create a src/ layout (use flat)
- Do NOT use requirements.txt (use pyproject.toml)
- Do NOT hardcode API keys
- Do NOT crash on missing API keys (warn and continue)
- Do NOT add features beyond what's specified (no database, no auth)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

