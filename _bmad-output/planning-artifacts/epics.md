---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
status: complete
inputDocuments:
  - 'planning-artifacts/prd.md'
  - 'planning-artifacts/architecture.md'
  - 'planning-artifacts/ux-design-specification.md'
---

# autodungeon - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for autodungeon, decomposing the requirements from the PRD, UX Design, and Architecture into implementable stories.

**Summary:** 6 Epics, 35 Stories, 55 Functional Requirements covered.

## Requirements Inventory

### Functional Requirements

**Multi-Agent Game Loop (FR1-FR10):**

- FR1: User can start a new game session with a configured party of AI agents
- FR2: DM Agent can narrate scenes, describe environments, and present scenarios
- FR3: DM Agent can control NPC dialogue and behavior during encounters
- FR4: DM Agent can manage encounter flow (combat, roleplay, exploration transitions)
- FR5: PC Agents can respond in-character to DM narration and other PCs
- FR6: PC Agents can take actions appropriate to their character class and personality
- FR7: PC Agents can engage in dialogue with each other and NPCs
- FR8: System can manage turn order and route narrative flow between agents
- FR9: User can configure the number of PC agents in a party (1-N, default 4)
- FR10: User can define character personalities and traits for each PC agent

**Memory & Context Management (FR11-FR16):**

- FR11: Each agent can maintain a short-term context window of recent events
- FR12: System can generate session summaries for long-term memory persistence
- FR13: Agents can reference events from previous turns within the same session
- FR14: Agents can reference events from previous sessions via summaries
- FR15: Character facts and traits can persist across sessions
- FR16: System can compress memory when context limits are reached

**Human Interaction (FR17-FR24):**

- FR17: User can observe the game in Watch Mode without intervening
- FR18: User can take control of any PC agent at any time (Drop-In Mode)
- FR19: User can release control and return PC to AI autopilot
- FR20: User can send suggestions to the game without taking full control (Nudge)
- FR21: User can pause the game at any point
- FR22: User can resume a paused game
- FR23: User can adjust game speed (time between turns)
- FR24: System can run fully autonomously without human intervention (Autopilot Mode)

**Viewer Interface (FR25-FR32):**

- FR25: User can view narrative in real-time as turns are generated
- FR26: User can distinguish between DM narration, PC dialogue, and actions visually
- FR27: User can see which character is speaking for each message
- FR28: User can scroll through session history
- FR29: User can see the current turn highlighted in the narrative
- FR30: User can access Drop-In controls for each PC character
- FR31: User can access session controls (pause, speed, etc.)
- FR32: User can view session history and transcript

**Persistence & Recovery (FR33-FR41):**

- FR33: System can auto-save game state after each turn (checkpoint)
- FR34: User can view list of available checkpoints for a session
- FR35: User can restore game state from any previous checkpoint
- FR36: System can restore agent memories to checkpoint state
- FR37: User can continue a previous campaign across multiple sessions
- FR38: System can organize session files by campaign
- FR39: System can export full transcript as JSON for research analysis
- FR40: System can display clear error messages when LLM API calls fail
- FR41: User can recover from errors without losing significant progress

**LLM Configuration (FR42-FR50):**

- FR42: User can select which LLM provider to use for the DM agent
- FR43: User can select which LLM provider to use for each PC agent
- FR44: User can select which LLM to use for memory summarization
- FR45: User can configure context limits per agent
- FR46: User can manage API keys through environment variables
- FR47: User can override API key configuration through UI settings
- FR48: System can support Google Gemini models
- FR49: System can support Anthropic Claude models
- FR50: System can support local models via Ollama

**Agent Behavior (FR51-FR55):**

- FR51: DM Agent can incorporate improv principles ("Yes, and...") in responses
- FR52: PC Agents can exhibit distinct, consistent personalities
- FR53: Agents can make callbacks to earlier events in the narrative
- FR54: DM Agent can use dice roll results to inform narrative outcomes
- FR55: System can execute dice rolls with standard D&D notation

### NonFunctional Requirements

**Performance:**

- NFR1: Turn Generation Timeout - Up to 2 minutes per turn is acceptable
- NFR2: UI Responsiveness - UI must remain responsive during LLM API calls (async processing)
- NFR3: Visual Feedback - Spinner or "thinking..." indicator must display while waiting for turn generation
- NFR4: Memory Footprint - Must run comfortably on 16GB RAM system
- NFR5: Checkpoint Storage - Efficient storage - avoid redundant data in checkpoint files

**Integration:**

- NFR6: LLM Provider Support - Must support Gemini, Claude, and Ollama simultaneously
- NFR7: API Failure Handling - Display clear error message and offer checkpoint restore
- NFR8: Provider Switching - User can change LLM provider mid-campaign without data loss
- NFR9: API Key Management - Configurable via environment variables OR UI settings
- NFR10: Network Dependency - Requires stable internet for cloud LLM providers; Ollama works offline

**Reliability:**

- NFR11: Auto-Checkpoint Frequency - Every turn automatically saved
- NFR12: Recovery Granularity - User can restore to any previous turn
- NFR13: State Consistency - Checkpoint restore must restore complete agent memory state
- NFR14: Data Integrity - Session files must remain valid even after unexpected shutdown
- NFR15: Error Recovery - User can recover from any error without losing more than current turn

### Additional Requirements

**From Architecture - Project Setup:**

- Clean Python project scaffolding (no external starter template required)
- Use `uv` for dependency management
- Flat project layout (not src/)
- LangGraph + Streamlit + Pydantic technology stack
- Ruff for linting, Pyright for type checking, pytest for testing

**From Architecture - State Management:**

- TypedDict + Pydantic hybrid for state schema
- Supervisor pattern for DM-controlled turn management
- Pydantic Settings for configuration loading
- Character configuration via YAML files

**From Architecture - Persistence:**

- Single JSON file per checkpoint (`session_xxx/turn_xxx.json`)
- Separate append-only transcript.json for research export
- Pydantic serialization via `.model_dump_json()`

**From Architecture - Memory System:**

- Context Manager node runs once per cycle (before DM turn)
- Token-based threshold for compression trigger
- PC agents isolated, DM sees all memories
- "Janitor" summarizer prompt for memory compression

**From UX Design - Platform:**

- Desktop-only application (minimum 1024px viewport)
- Dark mode only ("campfire" aesthetic with warm colors)
- Chrome primary, Firefox secondary, Edge tertiary browser support

**From UX Design - Visual Identity:**

- Lora font for narrative text, Inter for UI, JetBrains Mono for dice/stats
- Character color theming (DM: #D4A574 gold, Fighter: #C45C4A red, Rogue: #6B8E6B green, Wizard: #7B68B8 purple, Cleric: #4A90A4 blue)
- Message bubble styling with character-colored borders
- Literary "Name, the Class:" attribution format
- Justified text alignment for manuscript feel

**From UX Design - Interaction:**

- Drop-in transition under 2 seconds, no confirmation dialogs
- Keyboard shortcuts: 1-4 for party drop-in, Escape to release
- Auto-scroll with pausable behavior
- Mode indicator (Watch/Play) with pulse animation
- Quick switch between characters without explicit release

**From UX Design - First Session Flow:**

- Quick party setup with preset parties for instant start
- Returning users go straight to their session
- "While you were away..." catch-up summary

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 1 | Start new game session with configured party |
| FR2 | Epic 1 | DM narrates scenes and environments |
| FR3 | Epic 1 | DM controls NPC dialogue and behavior |
| FR4 | Epic 1 | DM manages encounter flow |
| FR5 | Epic 1 | PC agents respond in-character |
| FR6 | Epic 1 | PC agents take class-appropriate actions |
| FR7 | Epic 1 | PC agents engage in dialogue |
| FR8 | Epic 1 | System manages turn order |
| FR9 | Epic 1 | Configure number of PC agents |
| FR10 | Epic 1 | Define character personalities |
| FR11 | Epic 5 | Short-term context window per agent |
| FR12 | Epic 5 | Generate session summaries |
| FR13 | Epic 5 | Reference previous turns in session |
| FR14 | Epic 5 | Reference previous sessions via summaries |
| FR15 | Epic 5 | Character facts persist across sessions |
| FR16 | Epic 5 | Compress memory at context limits |
| FR17 | Epic 3 | Watch Mode observation |
| FR18 | Epic 3 | Drop-In Mode character control |
| FR19 | Epic 3 | Release control to AI |
| FR20 | Epic 3 | Nudge without full control |
| FR21 | Epic 3 | Pause game |
| FR22 | Epic 3 | Resume paused game |
| FR23 | Epic 3 | Adjust game speed |
| FR24 | Epic 3 | Autopilot Mode |
| FR25 | Epic 2 | Real-time narrative display |
| FR26 | Epic 2 | Visual distinction DM/PC/actions |
| FR27 | Epic 2 | Character attribution per message |
| FR28 | Epic 2 | Scroll session history |
| FR29 | Epic 2 | Current turn highlighted |
| FR30 | Epic 2 | Drop-In controls per character |
| FR31 | Epic 2 | Session controls access |
| FR32 | Epic 2 | View session history/transcript |
| FR33 | Epic 4 | Auto-save after each turn |
| FR34 | Epic 4 | View checkpoint list |
| FR35 | Epic 4 | Restore from checkpoint |
| FR36 | Epic 4 | Restore agent memories |
| FR37 | Epic 4 | Continue campaign across sessions |
| FR38 | Epic 4 | Organize files by campaign |
| FR39 | Epic 4 | Export transcript as JSON |
| FR40 | Epic 4 | Clear error messages |
| FR41 | Epic 4 | Error recovery |
| FR42 | Epic 6 | Select DM LLM provider (UI) |
| FR43 | Epic 6 | Select PC LLM providers (UI) |
| FR44 | Epic 6 | Select summarization model (UI) |
| FR45 | Epic 6 | Configure context limits (UI) |
| FR46 | Epic 1 | API keys via environment variables |
| FR47 | Epic 6 | Override API keys in UI |
| FR48 | Epic 1 | Support Google Gemini |
| FR49 | Epic 1 | Support Anthropic Claude |
| FR50 | Epic 1 | Support Ollama local models |
| FR51 | Epic 1 | DM improv principles |
| FR52 | Epic 1 | Distinct PC personalities |
| FR53 | Epic 1 | Callbacks to earlier events |
| FR54 | Epic 1 | Dice results inform narrative |
| FR55 | Epic 1 | Execute dice rolls |

## Epic List

| Epic | Title | Stories | FRs |
|------|-------|---------|-----|
| 1 | Core Game Engine | 8 | 19 |
| 2 | Streamlit Viewer Experience | 6 | 8 |
| 3 | Human Participation | 6 | 8 |
| 4 | Session Persistence & Recovery | 5 | 9 |
| 5 | Memory & Narrative Continuity | 5 | 6 |
| 6 | LLM Configuration UI | 5 | 5 |
| **Total** | | **35** | **55** |

---

## Epic 1: Core Game Engine

**Goal:** User can run the application and watch AI agents play D&D together autonomously.

**User Outcome:** "I can start the app and see AI characters having a D&D adventure - the DM narrates, characters respond in-character, dice roll, and the story unfolds."

**FRs Covered:** FR1-FR10, FR46, FR48-FR50, FR51-FR55 (19 FRs)

---

### Story 1.1: Project Foundation & Configuration

As a **developer**,
I want **a properly scaffolded Python project with dependency management and configuration loading**,
So that **I can install dependencies, configure API keys, and run the application**.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** I run `uv sync`
**Then** all dependencies are installed (langgraph, langchain-google-genai, langchain-anthropic, langchain-ollama, streamlit, pydantic, pyyaml, python-dotenv)
**And** the virtual environment is created automatically

**Given** a `.env.example` file exists in the project root
**When** I copy it to `.env` and fill in my API keys
**Then** the application can read GOOGLE_API_KEY, ANTHROPIC_API_KEY, and OLLAMA_BASE_URL

**Given** a `config/defaults.yaml` file exists
**When** the application starts
**Then** default configuration values are loaded via Pydantic Settings
**And** environment variables override config file values

**Given** the project structure follows the flat layout from Architecture
**When** I examine the project
**Then** I see: `app.py`, `graph.py`, `agents.py`, `memory.py`, `models.py`, `tools.py`, `persistence.py`, `config.py`, `config/`, `styles/`, `campaigns/`, `tests/`

---

### Story 1.2: Core Game State Models

As a **developer**,
I want **type-safe Pydantic models for game state, agent memory, and character configuration**,
So that **the application has validated, serializable data structures**.

**Acceptance Criteria:**

**Given** the models.py module
**When** I import GameState
**Then** it includes: ground_truth_log (list[str]), turn_queue (list[str]), current_turn (str), agent_memories (dict), game_config, human_active (bool), controlled_character (str | None)

**Given** the models.py module
**When** I import AgentMemory
**Then** it includes: long_term_summary (str), short_term_buffer (list[str]), token_limit (int)
**And** it can serialize to JSON via `.model_dump_json()`

**Given** the models.py module
**When** I import CharacterConfig
**Then** it includes: name, character_class, personality, color, provider, model, token_limit
**And** all fields have appropriate type hints and validation

**Given** a CharacterConfig instance with invalid data (e.g., empty name)
**When** I attempt to create it
**Then** Pydantic raises a ValidationError with a clear message

---

### Story 1.3: LLM Provider Integration

As a **developer**,
I want **a factory function that creates LLM clients for different providers**,
So that **agents can use Gemini, Claude, or Ollama interchangeably**.

**Acceptance Criteria:**

**Given** the agents.py module with `get_llm(provider: str, model: str)` function
**When** I call `get_llm("gemini", "gemini-1.5-flash")`
**Then** it returns a ChatGoogleGenerativeAI instance configured with that model

**Given** valid Anthropic API credentials in environment
**When** I call `get_llm("claude", "claude-3-haiku-20240307")`
**Then** it returns a ChatAnthropic instance configured with that model

**Given** Ollama running locally
**When** I call `get_llm("ollama", "llama3")`
**Then** it returns a ChatOllama instance pointing to the local server

**Given** an unknown provider string
**When** I call `get_llm("unknown", "model")`
**Then** it raises a ValueError with message "Unknown provider: unknown"

**Given** missing API credentials for a cloud provider
**When** I attempt to use that provider
**Then** a clear error message indicates which credentials are missing

---

### Story 1.4: Dice Rolling System

As a **player or DM agent**,
I want **a dice rolling function that supports standard D&D notation**,
So that **game mechanics can be resolved with random outcomes**.

**Acceptance Criteria:**

**Given** the tools.py module with `roll_dice(notation: str)` function
**When** I call `roll_dice("1d20")`
**Then** it returns a result between 1 and 20 inclusive
**And** the result includes the notation, individual rolls, and total

**Given** a notation with modifiers like "1d20+5"
**When** I call `roll_dice("1d20+5")`
**Then** the modifier is added to the total correctly

**Given** a multi-dice notation like "3d6"
**When** I call `roll_dice("3d6")`
**Then** it rolls 3 separate d6 dice and sums them
**And** the result includes each individual roll

**Given** complex notation like "2d6+1d4+3"
**When** I call `roll_dice("2d6+1d4+3")`
**Then** it handles multiple dice types and modifiers correctly

**Given** invalid notation like "abc" or "d"
**When** I call `roll_dice()` with it
**Then** it raises a ValueError with a helpful message

---

### Story 1.5: DM Agent Implementation

As a **user watching the game**,
I want **a DM agent that narrates scenes, describes environments, and manages encounters**,
So that **the story unfolds with engaging narration**.

**Acceptance Criteria:**

**Given** a DM agent with a system prompt incorporating improv principles ("Yes, and...")
**When** the DM's turn occurs
**Then** it generates narrative text describing the scene, NPCs, or situation
**And** the response acknowledges and builds on previous player actions

**Given** a combat encounter is active
**When** the DM generates a response
**Then** it can describe NPC actions and request dice rolls from players

**Given** a roleplay encounter is active
**When** the DM generates NPC dialogue
**Then** the NPC voices are distinct and consistent with their described personalities

**Given** the DM receives dice roll results
**When** generating the next response
**Then** the narrative incorporates those results meaningfully (FR54)

**Given** the game transitions between encounter types (combat → roleplay → exploration)
**When** the DM narrates
**Then** the transitions feel natural and the pacing varies appropriately

---

### Story 1.6: PC Agent Implementation

As a **user watching the game**,
I want **PC agents that respond in-character with distinct, consistent personalities**,
So that **each character feels like a unique individual**.

**Acceptance Criteria:**

**Given** a PC agent configured with name "Shadowmere", class "Rogue", personality "Sardonic wit, trust issues"
**When** the PC's turn occurs
**Then** it responds in first person as that character
**And** the response reflects the sardonic, distrustful personality

**Given** multiple PC agents in the party
**When** they each take turns
**Then** their voices and decision-making styles are noticeably different

**Given** a PC agent with class "Wizard"
**When** approaching a problem
**Then** they suggest solutions appropriate to their class (e.g., magic, knowledge)

**Given** a PC agent receives dialogue from the DM or another PC
**When** responding
**Then** they can engage in natural conversation and react to what was said (FR7)

**Given** a situation requiring action
**When** a PC responds
**Then** they take actions appropriate to their character class and personality (FR6)

---

### Story 1.7: LangGraph Turn Orchestration

As a **user**,
I want **a game loop that orchestrates turns between the DM and PC agents**,
So that **the narrative flows naturally with proper turn order**.

**Acceptance Criteria:**

**Given** a configured GameState with DM and 4 PC agents
**When** I start a game session
**Then** the LangGraph state machine initializes with all agents in the turn queue

**Given** the game is running
**When** the DM completes their turn
**Then** the supervisor pattern routes to the next PC in the turn queue

**Given** all PCs have taken their turns
**When** the round completes
**Then** control returns to the DM for the next narrative beat

**Given** the graph.py module
**When** I examine the workflow definition
**Then** it uses conditional edges with a `route_to_next_agent` function
**And** the DM node acts as supervisor routing to PC nodes

**Given** the ground_truth_log in GameState
**When** any agent generates a response
**Then** the response is appended to the log with agent attribution

---

### Story 1.8: Character Configuration System

As a **user**,
I want **to define character personalities and traits via YAML configuration files**,
So that **I can customize my party without editing code**.

**Acceptance Criteria:**

**Given** YAML files in `config/characters/` (dm.yaml, rogue.yaml, fighter.yaml, wizard.yaml)
**When** the application starts
**Then** each character configuration is loaded and validated

**Given** a character YAML file with format:
```yaml
name: "Shadowmere"
class: "Rogue"
personality: "Sardonic wit, trust issues"
color: "#6B8E6B"
provider: "claude"
model: "claude-3-haiku-20240307"
token_limit: 4000
```
**When** loaded
**Then** a CharacterConfig Pydantic model is created with all fields populated

**Given** a user wants to add a new character
**When** they create a new YAML file in the characters directory
**Then** the application loads it on next startup

**Given** the config specifies 4 PC agents (FR9)
**When** the game initializes
**Then** exactly those 4 characters are created as PC agents

**Given** each character has defined traits
**When** their agent is created
**Then** the system prompt incorporates those traits for personality consistency (FR10, FR52)

---

## Epic 2: Streamlit Viewer Experience

**Goal:** User can watch the story unfold in a themed, immersive UI with clear character attribution.

**User Outcome:** "I see the adventure in a beautiful campfire-themed interface. DM narration looks different from character dialogue. I always know who's speaking."

**FRs Covered:** FR25-FR32 (8 FRs)

---

### Story 2.1: Streamlit Application Shell

As a **user**,
I want **a Streamlit application with a proper layout structure**,
So that **I have a sidebar for controls and a main area for the narrative**.

**Acceptance Criteria:**

**Given** the app.py entry point
**When** I run `streamlit run app.py`
**Then** the application launches in my default browser

**Given** the application is running
**When** I view the page
**Then** I see a fixed 240px sidebar on the left and a fluid main narrative area

**Given** the Streamlit configuration
**When** the app loads
**Then** it uses wide layout mode (`st.set_page_config(layout="wide")`)
**And** the page title is "autodungeon"

**Given** the GameState is stored in session state
**When** I interact with the app
**Then** state persists via `st.session_state["game"]`

**Given** the viewport is less than 1024px wide
**When** viewing the application
**Then** a message displays: "Please use a wider browser window for the best experience"

---

### Story 2.2: Campfire Theme & CSS Foundation

As a **user**,
I want **a warm, campfire-themed visual design with dark mode**,
So that **the experience feels like gathering around a table, not using a productivity tool**.

**Acceptance Criteria:**

**Given** the styles/theme.css file
**When** the application loads
**Then** custom CSS is injected via `st.markdown` with `unsafe_allow_html=True`

**Given** the color palette
**When** viewing the application
**Then** I see:
- Background: #1A1612 (deep warm black)
- Secondary background: #2D2520 (warm gray-brown)
- Message bubbles: #3D3530
- Primary text: #F5E6D3 (warm off-white)
- Accent: #E8A849 (amber)

**Given** the character color variables
**When** viewing character-attributed content
**Then** colors match: DM (#D4A574 gold), Fighter (#C45C4A red), Rogue (#6B8E6B green), Wizard (#7B68B8 purple), Cleric (#4A90A4 blue)

**Given** the typography system
**When** viewing narrative text
**Then** it uses Lora font at 17-18px with 1.6 line height
**And** UI elements use Inter font at 13-14px

**Given** the overall aesthetic
**When** using the application in the evening
**Then** the warm tones reduce eye strain and feel inviting

---

### Story 2.3: Narrative Message Display

As a **user**,
I want **visually distinct message components for DM narration and PC dialogue**,
So that **I can instantly recognize who is speaking**.

**Acceptance Criteria:**

**Given** a DM narration message
**When** displayed in the narrative area
**Then** it shows with:
- Gold (#D4A574) left border (4px)
- Italic text
- Lora font at 18px
- No speaker attribution (DM is implicit)

**Given** a PC dialogue message
**When** displayed in the narrative area
**Then** it shows with:
- "Name, the Class:" attribution in character color
- Message bubble background (#3D3530)
- Character-colored left border (3px)
- Regular text for dialogue, italic for actions

**Given** a PC message contains both dialogue and actions
**When** displayed
**Then** quoted dialogue appears in regular text
**And** action descriptions (*italicized*) appear in secondary color (#B8A896)

**Given** the narrative area
**When** multiple messages are displayed
**Then** messages are separated by 16px spacing
**And** text is justified for manuscript feel

---

### Story 2.4: Party Panel & Character Cards

As a **user**,
I want **a sidebar panel showing all party members with Drop-In controls**,
So that **I can see who's in the party and quickly take control of any character**.

**Acceptance Criteria:**

**Given** the sidebar party panel
**When** viewing the application
**Then** I see a character card for each PC agent (Fighter, Rogue, Wizard, Cleric)

**Given** each character card
**When** displayed
**Then** it shows:
- Character name in character color (14px, weight 600)
- Character class in secondary text (13px)
- Drop-In button with character-colored border

**Given** a Drop-In button in default state
**When** I hover over it
**Then** the button fills with the character color
**And** text color inverts to dark background

**Given** the character card styling
**When** viewed
**Then** cards have #2D2520 background, 8px border radius, character-colored left border (3px)

**Given** I click a Drop-In button
**When** the action completes
**Then** the button changes to "Release" and the card shows a subtle glow (for Epic 3 integration)

---

### Story 2.5: Session Header & Controls

As a **user**,
I want **a chronicle-style session header and accessible session controls**,
So that **I know what session I'm in and can control playback**.

**Acceptance Criteria:**

**Given** the narrative area header
**When** viewing a session
**Then** I see a centered title like "Session VII" in Lora font (24px, gold color)
**And** a subtitle with session date/info in secondary text

**Given** the sidebar header area
**When** viewing the application
**Then** I see a mode indicator badge showing "Watch Mode" or "Play Mode"

**Given** the mode indicator in Watch Mode
**When** the story is actively generating
**Then** a green pulsing dot animates next to "Watching"

**Given** the session controls in the sidebar
**When** viewing the application
**Then** I can access: Pause/Resume button, Speed control (for Epic 3)
**And** controls use the established button hierarchy (secondary style)

---

### Story 2.6: Real-time Narrative Flow

As a **user**,
I want **the narrative to update in real-time with auto-scrolling and turn highlighting**,
So that **I can follow the story as it unfolds without manual scrolling**.

**Acceptance Criteria:**

**Given** the game is running in Watch Mode
**When** a new message is generated
**Then** it appears in the narrative area immediately (FR25)
**And** the view auto-scrolls to show the new content

**Given** auto-scroll is active
**When** I manually scroll up to read history
**Then** auto-scroll pauses
**And** a "Resume auto-scroll" indicator appears

**Given** the current turn
**When** viewing the narrative
**Then** the most recent message has a subtle highlight or indicator (FR29)

**Given** the session history
**When** I scroll through past messages
**Then** I can read the full transcript of the session (FR28, FR32)

**Given** an LLM is generating a response
**When** waiting for the turn to complete
**Then** a spinner or "thinking..." indicator appears after 500ms delay (NFR3)

---

## Epic 3: Human Participation

**Goal:** User can seamlessly watch, drop in to control a character, and release control back to AI.

**User Outcome:** "I'm watching the story, something interesting happens, I click a button and instantly I'm playing that character. When I'm done, one click and the AI takes over."

**FRs Covered:** FR17-FR24 (8 FRs)

---

### Story 3.1: Watch Mode & Autopilot

As a **user**,
I want **to observe the game running autonomously without needing to intervene**,
So that **I can enjoy the story passively like watching a show**.

**Acceptance Criteria:**

**Given** the application starts with a session
**When** I take no action
**Then** the game runs in Watch Mode by default (FR17)
**And** the mode indicator shows "Watching" with a pulsing green dot

**Given** Watch Mode is active
**When** turns are generated
**Then** the DM and PC agents take turns automatically
**And** the narrative updates without any user input required

**Given** no human has dropped in
**When** the game is running
**Then** it operates in full Autopilot Mode (FR24)
**And** can run indefinitely without human intervention

**Given** `st.session_state["human_active"]` is False
**When** the LangGraph executes
**Then** all PC nodes use AI agents, not human input

**Given** I am in Watch Mode
**When** I want to participate
**Then** Drop-In buttons are visible and accessible in the party panel

---

### Story 3.2: Drop-In Mode

As a **user**,
I want **to instantly take control of any PC character with a single click**,
So that **I can participate in the story when something interesting happens**.

**Acceptance Criteria:**

**Given** I am in Watch Mode
**When** I click a character's "Drop-In" button
**Then** I take control of that character in under 2 seconds (FR18)
**And** no confirmation dialog appears

**Given** I have dropped in as a character
**When** the mode switches
**Then** the mode indicator changes to "Playing as [Character Name]"
**And** the indicator uses the character's color

**Given** I am controlling a character
**When** the UI updates
**Then** an input context bar appears showing "You are [Character Name], the [Class]"
**And** a text input area expands for me to type my action

**Given** I am controlling a character
**When** I type an action and submit
**Then** my input is sent to the DM agent for integration
**And** my message appears in the narrative with my character's attribution

**Given** `st.session_state["controlled_character"]` is set to a character name
**When** LangGraph routes to that character's turn
**Then** it routes to `human_intervention_node` instead of the AI node

**Given** I submit my action
**When** the DM processes it
**Then** the DM acknowledges and weaves my action into the narrative
**And** other AI party members can respond to what I did

---

### Story 3.3: Release Control & Character Switching

As a **user**,
I want **to release control back to the AI or quickly switch to another character**,
So that **I can return to watching or play a different role seamlessly**.

**Acceptance Criteria:**

**Given** I am controlling a character
**When** I click the "Release" button
**Then** control returns to the AI immediately (FR19)
**And** the mode indicator returns to "Watching"

**Given** I release control
**When** the AI takes over
**Then** the transition is seamless with no narrative disruption
**And** the AI can continue mid-scene naturally

**Given** I am controlling Character A
**When** I click "Drop-In" on Character B
**Then** Character A is automatically released
**And** I take control of Character B without explicit release step

**Given** I release control
**When** the UI updates
**Then** the input area collapses/hides
**And** the character card returns to default (non-controlled) styling

**Given** `st.session_state["human_active"]` transitions to False
**When** the next turn cycle runs
**Then** all characters use AI agents again

---

### Story 3.4: Nudge System

As a **user**,
I want **to send suggestions to influence the game without taking full control**,
So that **I can guide the story subtly while staying in observation mode**.

**Acceptance Criteria:**

**Given** I am in Watch Mode
**When** I access the Nudge feature
**Then** a lightweight input appears for typing a suggestion (FR20)

**Given** I type a nudge like "The rogue should check for traps"
**When** I submit it
**Then** the suggestion is added to the DM's context for the next turn
**And** I remain in Watch Mode (not controlling any character)

**Given** a nudge has been submitted
**When** the DM generates the next response
**Then** it may incorporate the suggestion naturally
**And** the nudge is not shown directly in the narrative

**Given** I send a nudge
**When** it's processed
**Then** a subtle toast notification confirms "Nudge sent"
**And** the nudge input clears

**Given** the Nudge feature
**When** compared to Drop-In
**Then** Nudge is less intrusive - I don't control a specific character
**And** the DM has discretion on whether/how to incorporate it

---

### Story 3.5: Pause, Resume & Speed Control

As a **user**,
I want **to pause the game, resume it, and adjust the pacing**,
So that **I can take breaks or slow down intense moments**.

**Acceptance Criteria:**

**Given** the game is running
**When** I click the Pause button
**Then** turn generation stops immediately (FR21)
**And** the mode indicator shows "Paused" with a static amber dot

**Given** the game is paused
**When** I click Resume
**Then** turn generation continues from where it stopped (FR22)
**And** the mode indicator returns to active state

**Given** the game is paused
**When** I take other actions (scroll history, read, etc.)
**Then** the UI remains fully functional
**And** no new turns are generated until I resume

**Given** the speed control in the sidebar
**When** I adjust it
**Then** the delay between turns changes (FR23)
**And** options include: Slow, Normal, Fast (or a slider)

**Given** I set speed to Slow
**When** turns are generated
**Then** there is a longer pause between each turn for reading

**Given** I open the config modal
**When** the modal is displayed
**Then** the game auto-pauses
**And** it auto-resumes when I close the modal

---

### Story 3.6: Keyboard Shortcuts

As a **user**,
I want **keyboard shortcuts for quick Drop-In and Release actions**,
So that **I can participate instantly without reaching for the mouse**.

**Acceptance Criteria:**

**Given** I am in Watch Mode
**When** I press the `1` key
**Then** I drop in as the first party member (e.g., Fighter)

**Given** I am in Watch Mode
**When** I press `2`, `3`, or `4`
**Then** I drop in as the second, third, or fourth party member respectively

**Given** I am controlling any character
**When** I press the `Escape` key
**Then** I release control and return to Watch Mode

**Given** keyboard shortcuts are active
**When** I am typing in an input field
**Then** the shortcuts are disabled to prevent accidental triggers

**Given** the keyboard shortcuts
**When** displayed in a help tooltip or sidebar
**Then** users can discover them: "Press 1-4 to drop in, Escape to release"

---

## Epic 4: Session Persistence & Recovery

**Goal:** User can save and restore sessions, never losing more than one turn of progress.

**User Outcome:** "I close the app, come back tomorrow, and continue exactly where I left off. If something goes wrong, I can restore to any previous turn."

**FRs Covered:** FR33-FR41 (9 FRs)

---

### Story 4.1: Auto-Checkpoint System

As a **user**,
I want **the game to automatically save after every turn**,
So that **I never lose more than one turn of progress if something goes wrong**.

**Acceptance Criteria:**

**Given** a turn completes (DM or PC generates a response)
**When** the response is added to the ground truth log
**Then** a checkpoint is automatically saved (FR33, NFR11)
**And** no user action is required

**Given** the persistence.py module with `save_checkpoint(state, session_id, turn_number)` function
**When** a checkpoint is saved
**Then** it creates a file at `campaigns/session_xxx/turn_xxx.json`

**Given** a checkpoint file
**When** examining its contents
**Then** it contains the complete GameState serialized via Pydantic `.model_dump_json()`
**And** includes all agent memories at that point in time

**Given** checkpoint storage (NFR5)
**When** saving checkpoints
**Then** each file is self-contained (no delta encoding)
**And** old checkpoints are not modified

**Given** an unexpected shutdown occurs
**When** the user restarts the application
**Then** session files remain valid and uncorrupted (NFR14)

---

### Story 4.2: Checkpoint Browser & Restore

As a **user**,
I want **to view available checkpoints and restore to any previous turn**,
So that **I can recover from errors or revisit earlier points in the story**.

**Acceptance Criteria:**

**Given** the session history view in the UI
**When** I access it
**Then** I see a list of available checkpoints for the current session (FR34)
**And** each checkpoint shows: turn number, timestamp, brief context

**Given** the checkpoint list
**When** I select a checkpoint
**Then** I see a preview of what was happening at that turn

**Given** I want to restore to a previous checkpoint
**When** I click "Restore" on a checkpoint
**Then** the game state is loaded from that checkpoint file (FR35)
**And** all agent memories are restored to that exact state (FR36, NFR13)

**Given** a restore operation completes
**When** the game resumes
**Then** it continues from the restored turn
**And** all turns after that checkpoint are effectively "undone"

**Given** the `load_checkpoint(session_id, turn_number)` function
**When** called
**Then** it deserializes the JSON file back into a valid GameState
**And** populates `st.session_state["game"]` with the restored state

---

### Story 4.3: Campaign Organization & Multi-Session Continuity

As a **user**,
I want **my adventures organized by campaign with multi-session continuity**,
So that **I can have multiple ongoing stories and return to any of them**.

**Acceptance Criteria:**

**Given** the campaigns/ directory structure
**When** I start a new session
**Then** it creates a new session folder: `campaigns/session_001/` (FR38)
**And** a `config.yaml` file stores session metadata

**Given** I have played multiple sessions
**When** I open the application
**Then** I see a list of available campaigns/sessions to continue

**Given** I select a previous session
**When** it loads
**Then** I continue from the last checkpoint of that session (FR37)
**And** all character memories and story progress are intact

**Given** I am returning to a session after time away
**When** the session loads
**Then** a "While you were away..." summary appears
**And** it highlights key events from the last few turns for context

**Given** the session folder structure
**When** examining a campaign
**Then** I see: `config.yaml`, `turn_001.json`, `turn_002.json`, ..., `transcript.json`

---

### Story 4.4: Transcript Export

As a **researcher (Dr. Chen persona)**,
I want **to export the full session transcript as JSON**,
So that **I can analyze agent behavior and narrative coherence**.

**Acceptance Criteria:**

**Given** the transcript.json file in each session folder
**When** turns are generated
**Then** each turn is appended to the transcript file (FR39)
**And** the file is append-only (never overwritten)

**Given** a transcript entry
**When** examining its structure
**Then** it includes:
```json
{
  "turn": 42,
  "timestamp": "2026-01-25T14:35:22Z",
  "agent": "rogue",
  "content": "I check the door for traps.",
  "tool_calls": [{"name": "roll_dice", "args": {"notation": "1d20+7"}, "result": 18}]
}
```

**Given** the UI
**When** I want to export the transcript
**Then** I can access an "Export Transcript" option
**And** it provides the JSON file for download

**Given** I run a session in full Autopilot Mode
**When** the session completes or I stop it
**Then** the complete transcript is available for analysis
**And** every agent interaction is logged

**Given** the transcript format
**When** used for research analysis
**Then** it supports coherence scoring, character differentiation metrics, and callback detection

---

### Story 4.5: Error Handling & Recovery

As a **user**,
I want **clear error messages and easy recovery when things go wrong**,
So that **I don't lose progress and can continue my adventure**.

**Acceptance Criteria:**

**Given** an LLM API call fails (timeout, rate limit, invalid response)
**When** the error occurs
**Then** a user-friendly error message displays (FR40, NFR7)
**And** the message uses campfire-narrative style (e.g., "The magical connection was interrupted...")

**Given** an error panel appears
**When** I view it
**Then** I see:
- Friendly title explaining what happened
- Suggested actions (Retry, Restore from checkpoint, Start new session)
- No technical jargon exposed to the user

**Given** an error occurs mid-turn
**When** I choose to recover
**Then** I can restore to the last successful checkpoint
**And** I lose at most one turn of progress (FR41, NFR15)

**Given** I click "Retry" on an error
**When** the retry executes
**Then** the failed action is attempted again
**And** if successful, the game continues normally

**Given** the error logging
**When** an error occurs
**Then** technical details are logged internally for debugging
**And** the log includes: provider, agent, error type, timestamp

**Given** network connectivity is lost
**When** using cloud LLM providers
**Then** a clear message indicates the connection issue
**And** suggests checking internet or switching to Ollama for offline play

---

## Epic 5: Memory & Narrative Continuity

**Goal:** Characters remember past events and reference them, creating ongoing story threads.

**User Outcome:** "The rogue mentions something that happened three sessions ago. The DM weaves old plot threads into new encounters. They actually remember!"

**FRs Covered:** FR11-FR16 (6 FRs)

---

### Story 5.1: Short-Term Context Buffer

As an **agent (DM or PC)**,
I want **a short-term memory buffer of recent events**,
So that **I can maintain context during the current scene and respond coherently**.

**Acceptance Criteria:**

**Given** the AgentMemory model with `short_term_buffer: list[str]`
**When** a turn completes
**Then** the turn's content is added to the agent's short_term_buffer (FR11)

**Given** each agent's short_term_buffer
**When** the agent generates a response
**Then** recent turns from the buffer are included in the prompt context

**Given** the buffer has a configurable size limit (based on token_limit)
**When** the buffer approaches the limit
**Then** older entries are candidates for compression (handled in Story 5.5)

**Given** a PC agent's buffer
**When** building their prompt
**Then** they only see their own buffer contents (PC isolation per Architecture)

**Given** the DM agent's context
**When** building the DM prompt
**Then** the DM can access all agents' short_term_buffers (DM sees all)

**Given** the memory.py module with `MemoryManager` class
**When** calling `get_context(agent_name)`
**Then** it returns a prompt-ready string with recent buffer contents

---

### Story 5.2: Session Summary Generation

As a **system**,
I want **to generate summaries of session events for long-term memory**,
So that **important story beats persist beyond the short-term buffer**.

**Acceptance Criteria:**

**Given** a session has progressed through multiple turns
**When** the Context Manager triggers summarization
**Then** a summary is generated capturing key events (FR12)

**Given** the summarizer uses a dedicated LLM (configurable via FR44)
**When** generating summaries
**Then** it uses the "Janitor" prompt that preserves:
- Character names and relationships
- Inventory and equipment changes
- Quest goals and progress
- Status effects and conditions

**Given** the "Janitor" summarizer
**When** compressing content
**Then** it discards:
- Verbatim dialogue (keeps gist)
- Detailed dice mechanics
- Repetitive descriptions

**Given** a summary is generated
**When** stored in AgentMemory
**Then** it updates the `long_term_summary` field
**And** the summary is serialized with checkpoints

**Given** the summary generation
**When** complete
**Then** it runs synchronously (blocking) as per Architecture decision
**And** the UI shows a brief indicator if it takes time

---

### Story 5.3: In-Session Memory References

As a **user watching the game**,
I want **agents to reference events from earlier in the current session**,
So that **the story feels connected and coherent**.

**Acceptance Criteria:**

**Given** an event occurred 10 turns ago in the current session
**When** it's relevant to the current situation
**Then** an agent may reference it naturally in their response (FR13)

**Given** the DM described a mysterious symbol in turn 5
**When** a similar symbol appears in turn 25
**Then** a PC agent might say "This looks like that marking we saw in the cave earlier..."

**Given** the short_term_buffer contains relevant context
**When** an agent generates a response
**Then** the LLM can draw connections and make callbacks

**Given** callback behavior
**When** it occurs naturally
**Then** it creates "aha moments" that delight users (UX: Memory is Magic)

**Given** in-session references
**When** they occur
**Then** they demonstrate narrative coherence without explicit prompting

---

### Story 5.4: Cross-Session Memory & Character Facts

As a **user returning to a campaign**,
I want **agents to remember events from previous sessions**,
So that **my ongoing story has real continuity**.

**Acceptance Criteria:**

**Given** a campaign spans multiple sessions
**When** a new session starts
**Then** each agent's `long_term_summary` is loaded from the previous session (FR14)

**Given** the long_term_summary contains "The party befriended a goblin named Skrix"
**When** goblins are encountered again
**Then** an agent might reference Skrix or that previous encounter

**Given** character facts (name, class, key traits, relationships)
**When** stored in AgentMemory
**Then** they persist across sessions (FR15)
**And** are always included in the agent's context

**Given** the rogue established a rivalry with a merchant in session 2
**When** that merchant appears in session 5
**Then** the rogue's response reflects that history

**Given** cross-session memory loading
**When** a session resumes
**Then** the "While you were away..." summary draws from these memories
**And** agents can reference past sessions naturally

---

### Story 5.5: Memory Compression System

As a **system**,
I want **to automatically compress memories when approaching context limits**,
So that **agents don't exceed token limits while retaining important information**.

**Acceptance Criteria:**

**Given** the Context Manager node in LangGraph
**When** a turn cycle begins (before DM turn)
**Then** it checks each agent's token count against their limit (FR16)

**Given** an agent's short_term_buffer approaches `token_limit`
**When** the threshold is exceeded (e.g., 80% of limit)
**Then** the Context Manager triggers summarization for that agent

**Given** summarization is triggered
**When** it completes
**Then** older buffer entries are compressed into the long_term_summary
**And** those entries are removed from short_term_buffer

**Given** the compression process
**When** preserving information
**Then** the most recent N turns remain in short_term_buffer uncompressed
**And** older content is summarized and merged into long_term_summary

**Given** memory compression runs
**When** it completes
**Then** the agent's total context fits within their token_limit
**And** critical story information is preserved

**Given** the compression is per-agent
**When** one agent compresses
**Then** other agents' memories are unaffected
**And** each agent manages their own memory independently

---

## Epic 6: LLM Configuration UI

**Goal:** User can customize which AI models power each character through a settings interface.

**User Outcome:** "I can open settings and choose different models for each character - maybe Claude for the DM, Gemini for the wizard, Ollama for local testing."

**FRs Covered:** FR42-FR45, FR47 (5 FRs)

---

### Story 6.1: Configuration Modal Structure

As a **user**,
I want **a settings modal with organized tabs for different configuration areas**,
So that **I can access all settings in one place without leaving my session**.

**Acceptance Criteria:**

**Given** the sidebar
**When** I click the "Configure" button
**Then** a modal dialog opens centered on screen

**Given** the configuration modal
**When** it opens
**Then** it displays three tabs: "API Keys", "Models", "Settings"
**And** uses the established dark theme styling (#1A1612 background, #2D2520 surfaces)

**Given** an active game session
**When** I open the configuration modal
**Then** the game automatically pauses (per UX flow)
**And** the mode indicator shows "Paused"

**Given** the configuration modal is open
**When** I close it (X button, Escape key, or click outside)
**Then** the game automatically resumes
**And** any saved changes take effect

**Given** I have unsaved changes in the modal
**When** I attempt to close it
**Then** a confirmation appears: "Discard changes?"
**And** I can choose to save or discard

**Given** the modal styling
**When** displayed
**Then** it matches the campfire aesthetic with warm colors and Inter font

---

### Story 6.2: API Key Management UI

As a **user**,
I want **to enter and validate API keys through the settings interface**,
So that **I can configure providers without editing environment files**.

**Acceptance Criteria:**

**Given** the "API Keys" tab in the config modal
**When** I view it
**Then** I see entry fields for: Google (Gemini), Anthropic (Claude), Ollama Base URL (FR47)

**Given** an API key field
**When** it's empty and no environment variable is set
**Then** the field shows a placeholder prompting for input

**Given** an API key is set via environment variable
**When** viewing the field
**Then** it shows "Set via environment" with a masked preview
**And** I can optionally override it in the UI

**Given** I enter an API key in the UI
**When** I blur the field (move focus away)
**Then** the key is validated asynchronously
**And** a spinner shows during validation

**Given** an API key is valid
**When** validation completes
**Then** a green checkmark appears next to the field
**And** the provider is marked as available

**Given** an API key is invalid
**When** validation completes
**Then** a red X appears with "Invalid key" message
**And** the provider is marked as unavailable

**Given** Ollama configuration
**When** entering the base URL
**Then** it validates by attempting to connect to the Ollama server
**And** shows available models if successful

---

### Story 6.3: Per-Agent Model Selection

As a **user**,
I want **to choose which LLM provider and model powers each character**,
So that **I can mix providers or use different models for different roles**.

**Acceptance Criteria:**

**Given** the "Models" tab in the config modal
**When** I view it
**Then** I see a grid with rows for: DM, Fighter, Rogue, Wizard, Cleric, Summarizer

**Given** each agent row
**When** displayed
**Then** it shows:
- Agent name (in character color for PCs)
- Provider dropdown (Gemini, Claude, Ollama)
- Model dropdown (populated based on selected provider)
- Status indicator (Active, AI, or "You" if controlled)

**Given** I select a provider for an agent
**When** the selection changes
**Then** the model dropdown updates with available models for that provider (FR42, FR43)

**Given** the Summarizer row
**When** I configure it
**Then** I can select which model handles memory summarization (FR44)
**And** this is independent of agent models

**Given** quick actions below the grid
**When** I click "Copy DM to all PCs"
**Then** all PC agents are set to the same provider/model as the DM

**Given** quick actions
**When** I click "Reset to defaults"
**Then** all agents return to the default configuration from config/defaults.yaml

**Given** I change a model selection
**When** I save the configuration
**Then** a confirmation shows: "Changes will apply on next turn"

---

### Story 6.4: Context Limit Configuration

As a **user**,
I want **to configure the context token limit for each agent**,
So that **I can balance memory depth against response quality and cost**.

**Acceptance Criteria:**

**Given** each agent row in the Models tab
**When** I expand advanced options (or a separate Settings tab section)
**Then** I see a token limit field for that agent (FR45)

**Given** the token limit field
**When** displayed
**Then** it shows the current limit (default from character YAML)
**And** includes a hint about the model's maximum context

**Given** I enter a new token limit
**When** it's below a minimum threshold (e.g., 1000)
**Then** a warning appears: "Low limit may affect memory quality"

**Given** I enter a token limit exceeding the model's maximum
**When** validation runs
**Then** it clamps to the model's maximum
**And** shows an info message explaining the adjustment

**Given** I save token limit changes
**When** the game continues
**Then** the new limits are used for memory compression thresholds
**And** existing memories are not retroactively compressed

**Given** different agents have different limits
**When** the game runs
**Then** each agent's memory is managed according to their individual limit

---

### Story 6.5: Mid-Campaign Provider Switching

As a **user**,
I want **to change AI providers during an active campaign**,
So that **I can experiment with different models or switch if one isn't working well**.

**Acceptance Criteria:**

**Given** an active campaign session
**When** I open configuration and change a provider/model
**Then** my campaign data is preserved (NFR8)
**And** only the AI backend changes

**Given** I switch the DM from Gemini to Claude
**When** I save and the game resumes
**Then** the next DM turn uses Claude
**And** narrative continuity is maintained via memory system

**Given** I switch a PC agent mid-session
**When** the change takes effect
**Then** the new model receives the same character config and memory
**And** personality consistency is maintained through the system prompt

**Given** a provider becomes unavailable mid-session (API error)
**When** I open configuration
**Then** I can switch to an available provider
**And** continue the session without data loss

**Given** the change confirmation
**When** I save model changes during a session
**Then** it clearly states: "[Character] will use [Provider/Model] starting next turn"

**Given** I switch providers
**When** the next turn generates
**Then** the transition is seamless to the user
**And** the narrative style may subtly shift but story continues
