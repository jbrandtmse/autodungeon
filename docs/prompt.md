# Multi-Agent D&D Game Engine

**Project:** autodungeon
**Role:** Principal AI Architect & Python Developer

**Task:** Build an advanced, multi-agent Dungeons & Dragons Game Engine with independent context management, decoupled summarization, and human-in-the-loop features.

---

## Project Vision & Goals

### Dual Purpose

This project serves two complementary objectives:

| Dimension | Goal |
|-----------|------|
| **Research/Experiment** | Explore emergent behavior when multiple LLMs roleplay with each other in a structured game context |
| **Interactive Experience** | Create a playable human-in-the-middle game where the human participates as a player character |

### Core Concept

A **multi-agent harness** that orchestrates a D&D game session:

- **Dungeon Master (DM) Agent** - One LLM runs the game, controls NPCs, narrates the world
- **Player Character (PC) Agents** - Other LLMs play as adventurers, making decisions in-character
- **Human Player (Optional)** - A human can take control of one PC for interactive gameplay
- **Autopilot Mode** - The entire session can run autonomously for observation/experimentation

### Flexibility Modes

| Mode | Description |
|------|-------------|
| **Full Autopilot** | All agents are LLMs - observe emergent roleplay behavior |
| **Human-in-the-Middle** | Human controls one PC while LLMs play the others |
| **Hybrid** | Human can drop in/out, with LLM taking over when human is absent |

---

## Tech Stack Suggestions (subject to full analysis)

| Category | Technology |
| -------- | ---------- |
| Core | Python 3.10+, Pydantic |
| Orchestration | LangGraph (Required for cyclical state management) |
| UI | Streamlit |
| LLM - Google | ChatGoogleGenerativeAI (Primary for DM & Summarizer) |
| LLM - Anthropic | ChatAnthropic (Claude 3 Haiku) |
| LLM - Local | ChatOllama (Llama 3, Mistral) |
| Image Gen | OpenAI DALL-E 3 API (with dummy fallback) or Google Imagen |

---

## 1. System Architecture & State Management

The system must maintain a "Ground Truth" global state, but each agent must possess a unique, private "View" of the world that gets compressed over time using a dedicated summarizer model.

Define a `GameState` Pydantic model containing:

- **ground_truth_log:** The absolute, uncompressed history of all events
- **agent_memories:** A dictionary mapping `agent_name` to an `AgentMemory` object
- **turn_queue:** List of agent names (e.g., `["DM", "Rogue", "Paladin"]`)
- **game_config:**
  - `combat_mode`: Enum `["Narrative", "Tactical"]`
  - `global_summarizer_model`: String (e.g., `"gemini-1.5-flash"`)
- **whisper_queue:** Private instructions from the human user to the DM

---

## 2. Independent Context & Decoupled Compression

Create a class `MemoryManager`.

### Configuration

The class acts as a factory. It accepts a `primary_model` (for acting) and a `summarizer_model` (for compressing) independently.

### Structure

Each `AgentMemory` object holds:

- **long_term_summary:** A condensed narrative of past events
- **short_term_buffer:** List of recent raw messages
- **token_limit:** The max context size for this specific agent

### Logic

1. Before an agent acts, check if `len(short_term_buffer) > threshold`
2. **The Decoupling:** If threshold is exceeded, instantiate the `summarizer_model` to compress the buffer
3. **Prompt Construction:** When an agent acts, its input is: `System Prompt + Long Term Summary + Short Term Buffer`

---

## 3. Tooling (Function Calling)

| Function | Description |
| -------- | ----------- |
| `roll_dice(notation: str) -> str` | Real random number generation (e.g., `"1d20+5"`) |
| `generate_scene(description: str) -> url` | Visual generation |
| `get_inventory() -> json` | Returns the agent's current inventory |

---

## 4. The Agent Workflow (LangGraph)

### Node: Context_Manager

- Iterates through all agents
- If any agent's buffer exceeds their limit, triggers the `summarizer_model` to condense their memory before the game loop proceeds

### Node: DM_Turn (Gemini Pro)

- Checks `whisper_queue`
- Decides if Scene Image is needed → calls `generate_scene`
- Decides if NPCs need to roll dice → calls `roll_dice`
- Outputs narrative

### Node: PC_Turn (Haiku/Flash/Ollama)

- Receives only its private `AgentMemory` view
- Decides action using its `primary_model`
- Calls `roll_dice` for skill checks

### Node: Human_Intervention

- If the active character is flagged "Human", pause graph and wait for Streamlit input

---

## 5. Streamlit UI Requirements

### Sidebar Configuration

- **Global Settings:** Select Summarizer Model (Default: Gemini 1.5 Flash)
- **Agent Setup:** Dynamic list of PCs
- **Per-Agent Settings:** Select Primary Model (Gemini Pro, Flash, Haiku, Ollama) AND Context Limit

### Main Area

- **Visuals:** Display generated scene image
- **Chat Log:** Render the `ground_truth_log` nicely
- **Memory Inspector (Debug):** An expander that shows the current compressed summary of a selected agent

---

## Deliverables

| File | Description |
| ---- | ----------- |
| `memory.py` | Implementation of `MemoryManager` with dual-model support |
| `agents.py` | Agent definitions and LLM factory |
| `graph.py` | LangGraph state machine |
| `app.py` | Streamlit interface |

---

## Bonus: The "Janitor" System Prompt

Since you are using context compression, the "Janitor" (Summarizer) needs strict instructions so it doesn't accidentally delete your magical items. Include this prompt in your `memory.py`:

```python
SUMMARIZER_SYSTEM_PROMPT = """
You are the Memory Keeper for a Dungeons & Dragons AI Agent.
Your goal is to compress the "Recent Chat History" into the "Current Summary" without losing critical game state.

INPUTS:
1. Current Summary (The past history).
2. Recent Chat History (New dialogue/events since the last summary).

INSTRUCTIONS:
- Merge the inputs into a SINGLE cohesive narrative in the second person ("You went to...").
- PRESERVE:
    - Specific Names (NPCs, Locations).
    - Inventory changes (Items gained/lost).
    - Current Quest Goals.
    - Health/Status effects (e.g., "You are currently poisoned").
- DISCARD:
    - Verbatim dialogue (unless iconic).
    - Dice roll mechanics (e.g. "Rolled a 15" -> "You successfully hit").
    - Repetitive descriptions.

OUTPUT:
The updated summary text only.
"""
```