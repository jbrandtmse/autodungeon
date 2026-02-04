# autodungeon

> **⚠️ UNDER HEAVY DEVELOPMENT**
> This project is actively being built. Features may be incomplete, broken, or change without notice. Not yet ready for production use.

**Multi-agent D&D game engine where AI plays Dungeons & Dragons together.**

*"Nostalgia for D&D, made accessible for people who can't coordinate 4 friends."*

---

## What is autodungeon?

autodungeon creates a self-playing D&D party where multiple AI agents roleplay as adventurers while another AI runs the game as Dungeon Master. You can watch the adventure unfold like a living story, or drop in at any moment to take control of a character.

**The Problem:** Millions of adults who grew up playing D&D have been forced to abandon the hobby—not because they lost interest, but because coordinating 4+ schedules is nearly impossible in modern life.

**The Solution:** AI agents that play D&D together, creating emergent collaborative storytelling on your schedule.

### Key Features

- **Watch Mode** - AI party plays autonomously; watch the story unfold
- **Drop-In Mode** - Take control of any character at any moment, then leave when you want
- **True Party Dynamics** - Multiple LLMs interact as distinct characters with independent memories
- **Emergent Storytelling** - Improv principles ("Yes, and...") create genuine surprises
- **Full Transcript Logging** - Research-ready logs for studying multi-agent narrative behavior

## Tech Stack

| Category | Technology |
|----------|-----------|
| Language | Python 3.10+ |
| Orchestration | LangGraph (cyclical state management) |
| UI | Streamlit (with custom CSS theming) |
| Data Models | Pydantic |
| LLM Providers | Google Gemini, Anthropic Claude, Ollama (local) |

## Project Status

**Status: In Development**

This project has completed comprehensive planning and architecture design. Implementation is underway.

### Epic Progress

#### MVP (v1.0) - Complete

| Epic | Description | Status |
|------|-------------|--------|
| 1 | Core Game Engine | ✅ Complete |
| 2 | Streamlit Viewer Experience | ✅ Complete |
| 3 | Human Participation | ✅ Complete |
| 4 | Session Persistence & Recovery | ✅ Complete |
| 5 | Memory & Narrative Continuity | ✅ Complete |
| 6 | LLM Configuration UI | ✅ Complete |

#### Enhancements (v1.1) - Planned

| Epic | Description | Status |
|------|-------------|--------|
| 7 | Module Selection & Campaign Setup | ✅ Complete |
| 8 | Character Sheets | ✅ Complete |
| 9 | Character Creation UI | 📋 Planned |
| 10 | DM Whisper & Secrets System | 📋 Planned |
| 11 | Callback Tracker | 📋 Planned |
| 12 | Fork Gameplay | 📋 Planned |

See the [planning artifacts](_bmad-output/planning-artifacts/) for:

- [Product Requirements Document](_bmad-output/planning-artifacts/prd.md) - 55 functional requirements
- [Architecture Decisions](_bmad-output/planning-artifacts/architecture.md) - Technical design choices
- [Epic/Story Breakdown (MVP)](_bmad-output/planning-artifacts/epics.md) - v1.0 implementation roadmap
- [Epic/Story Breakdown (v1.1)](_bmad-output/planning-artifacts/epics-v1.1.md) - Enhancement roadmap

## Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- API keys for at least one LLM provider (Gemini, Claude, or Ollama for local)

### Installation

```bash
# Clone the repository
git clone https://github.com/jbrandtmse/autodungeon.git
cd autodungeon

# Install dependencies
uv sync

# Copy environment template and add your API keys
cp .env.example .env
# Edit .env with your API keys

# Run the application
streamlit run app.py
```

### Configuration

- **API Keys**: Set in `.env` file
- **Game Defaults**: `config/defaults.yaml`
- **Characters**: `config/characters/*.yaml`

## Architecture Overview

autodungeon uses a **supervisor pattern** where the DM agent orchestrates turns:

```
┌─────────────────┐
│ Context Manager │ ← Monitors memory, triggers summarization
└────────┬────────┘
         ▼
    ┌─────────┐
    │ DM Turn │ ← Narrates, controls NPCs, routes to next agent
    └────┬────┘
         ▼
  ┌──────────────┐
  │ PC Turn(s)   │ ← Each agent acts based on isolated memory
  └──────────────┘
         ▼
  ┌──────────────┐
  │ Human Node   │ ← Pauses for human input when active
  └──────────────┘
```

**Memory Isolation (Asymmetric):**
- PC agents only see their own memories (strict isolation)
- DM agent sees all memories (enables dramatic irony and secrets)

## Development

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
pyright .

# Run tests
pytest
```

## Project Structure

```
autodungeon/
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

This project is in early development. Contributions, ideas, and feedback are welcome!

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

Built with [BMAD](https://github.com/bmadcode/BMAD-METHOD) workflow methodology for AI-assisted development.
