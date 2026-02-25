---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
workflowCompleted: '2026-01-24'
lastEdited: '2026-02-11'
editHistory:
  - date: '2026-02-24'
    changes: 'Illustration Gallery Enhancement: Added FR93-FR97, updated growth features table. Per Sprint Change Proposal 2026-02-24.'
  - date: '2026-02-14'
    changes: 'AI Scene Image Generation: Added FR85-FR92, v2.1 growth feature. Per Sprint Change Proposal 2026-02-14.'
  - date: '2026-02-11'
    changes: 'UI framework migration: Streamlit → FastAPI + SvelteKit. Updated tech stack, FR25-32, NFRs (Stability, Build & Deployment), deployment model, growth roadmap. Per Sprint Change Proposal 2026-02-11.'
inputDocuments:
  - 'planning-artifacts/product-brief-autodungeon-2026-01-24.md'
  - 'planning-artifacts/research/technical-autodungeon-research-2026-01-24.md'
  - 'analysis/brainstorming-session-2026-01-24.md'
  - 'docs/prompt.md'
workflowType: 'prd'
documentCounts:
  briefs: 1
  research: 1
  brainstorming: 1
  projectDocs: 1
classification:
  projectType: 'web_app'
  domain: 'scientific'
  complexity: 'medium'
  projectContext: 'greenfield'
---

# Product Requirements Document - autodungeon

**Author:** Developer
**Date:** 2026-01-24

---

## Executive Summary

autodungeon is a multi-agent D&D game engine where AI agents autonomously play Dungeons & Dragons together while humans can watch, drop in to play, or let it run unattended. The project serves three purposes: scratching the itch of D&D nostalgia without scheduling friends, advancing research on emergent multi-agent narrative behavior, and creating entertaining content worth sharing.

---

## Table of Contents

1. [Success Criteria](#success-criteria)
2. [Product Scope](#product-scope)
3. [User Journeys](#user-journeys)
4. [Innovation & Novel Patterns](#innovation--novel-patterns)
5. [Web Application Technical Requirements](#web-application-technical-requirements)
6. [Project Scoping & Phased Development](#project-scoping--phased-development)
7. [Functional Requirements](#functional-requirements)
8. [Non-Functional Requirements](#non-functional-requirements)

---

## Success Criteria

### User Success

**Primary Success Indicator: "The Phone a Friend Moment"**
The ultimate signal of success: a user is so excited by their experience that they contact friends who used to play D&D and say "You have to try this."

**Measurable User Outcomes:**
| Metric | Definition | Target |
|--------|------------|--------|
| Drop-In Rate | User takes control of a character during a session | At least once per session |
| Session Continuity | User returns to continue the same campaign | Multi-session campaigns become common |
| Organic Sharing | User shares screenshots, clips, or stories unprompted | Evidence of sharing without prompting |

**Emotional Validation:**
- The story is interesting enough to make you want to drop in
- At least one "I didn't expect that!" moment per session
- You find yourself checking back on the adventure

### Business Success

This is a passion project with research value, not a commercial product.

**Success is measured by:**
1. **Personal Fulfillment** - Does using autodungeon feel like being at the table again?
2. **Research Contribution** - Does it advance understanding of multi-agent narrative coherence?
3. **Community Interest** - Do others find it compelling enough to try?

*Revenue and scale are explicitly not goals for MVP.*

### Technical Success

**Performance Requirements:**
- Must run on a modern Windows computer (see NFR Performance for specifics)
- Requires high-speed internet for LLM API calls
- No specific latency targets for MVP (reasonable responsiveness expected)

**MVP Technical Validation:**
- [ ] Agents maintain coherent conversation for 30+ turns
- [ ] Characters exhibit distinct, recognizable personalities
- [ ] Human can drop in and out without breaking the narrative
- [ ] Sessions can be paused and resumed
- [ ] Full transcripts captured and analyzable

### Research Success

**Metrics (Methodology TBD):**
| Metric | What It Measures |
|--------|------------------|
| Narrative Coherence Score | Can agents maintain consistent storylines across sessions? |
| Character Differentiation | Do agents exhibit distinct, consistent personalities? |
| Memory Utilization | Are callbacks and references used naturally and correctly? |
| Emergent Behavior Rate | How often do agents do something genuinely unexpected? |

### Community Success

| Metric | Target |
|--------|--------|
| Repository Clones | 10 users who download, set up, and run their own instances |
| Community Engagement | Users contribute feedback, bug reports, or improvements |
| Interest Signal | Project generates discussion in AI/gaming communities (Reddit, HN) |

## Product Scope

### MVP - Minimum Viable Product

**Core Features:**
1. Multi-Agent Game Loop (DM + N PCs with turn-based narrative)
2. Simple Memory System (short-term buffer + session summaries)
3. Human Interaction (Watch Mode, Drop-In Mode, Nudge Option)
4. Viewer Interface (web-based real-time display via WebSocket streaming)
5. Core Infrastructure (LangGraph, multi-LLM support, Pydantic models, transcript logging)

### Growth Features (Post-MVP)

| Feature | Target Version |
|---------|----------------|
| Module selection & campaign setup | v1.1 |
| Character sheets (dynamic, DM-editable) | v1.1 |
| Character creation UI | v1.1 |
| DM whisper/secrets system | v1.1 |
| Callback tracker (Chekhov's Gun) | v1.1 |
| Fork gameplay (branch exploration) | v1.1 |
| Advanced pacing curves | v1.2 |
| INT-based variable memory | v1.2 |
| AI scene illustration (text-to-image) | v2.1 |

### Vision (Future)

**v2.x - Community & Scale:**
- Share campaigns/transcripts with others
- Community-created characters and scenarios
- Streaming integration for content creators
- Research dashboard

**Long-term Vision:**
A platform where anyone can experience collaborative D&D storytelling on their own schedule, while contributing to AI research on emergent multi-agent behavior.

## User Journeys

### Journey 1: Marcus - The Return to the Table (Primary Happy Path)

**Persona:** Marcus, 42, software engineer. Played D&D heavily in high school, abandoned the hobby when life got busy. Every attempt to restart with old friends fizzles due to scheduling conflicts.

**Opening Scene:**
It's 9 PM on a Tuesday. Marcus just finished putting the kids to bed. He has an hour before sleep. He sees a Reddit post: "I built AI agents that play D&D together." He clicks immediately - the title hits him somewhere nostalgic.

**Rising Action:**
He watches a 5-minute demo. The AI rogue tries to pickpocket the AI paladin. The paladin catches him. They argue in-character. Marcus laughs out loud - this is the energy he remembers.

He downloads the repo, configures his API keys, creates a classic party: fighter, rogue, wizard, cleric. Starts his first session. The DM describes a tavern (of course), but then the wizard starts asking questions Marcus didn't expect. The rogue makes a side comment about a job gone wrong in another town. The fighter is suspicious.

**Climax:**
Session 5. The wizard references something the rogue said three sessions ago - a throwaway line about "the incident in Neverwinter." The DM picks it up and weaves it into the current quest. Marcus realizes: they're not just responding to prompts. They're building a story together. They remember.

He hits the "Drop In" button and takes over the rogue for the first time. He decides to finally explain what happened in Neverwinter.

**Resolution:**
Two months later, Marcus runs autodungeon most evenings while doing dishes or folding laundry. Sometimes he watches. Sometimes he plays. He's sent the link to three old D&D friends with the message: "You have to try this."

---

### Journey 2: Marcus - Session Recovery (Edge Case)

**Persona:** Same Marcus, mid-campaign.

**Opening Scene:**
Marcus is deep in session 12 of his campaign. The party is in a tense negotiation with a dragon. Suddenly, the Gemini API returns an error. The DM's response is garbled nonsense.

**Rising Action:**
Marcus sees an error message in the UI. The session is corrupted - the last three turns don't make sense narratively. He's frustrated but not panicked.

**Climax:**
He clicks "Session History" in the sidebar, sees the list of auto-saved checkpoints (one per turn). He selects the checkpoint from just before the dragon negotiation started and clicks "Restore."

**Resolution:**
The session reloads to the checkpoint state. All agent memories are restored to that point. Marcus resumes the session - the dragon negotiation begins fresh. The story continues as if the error never happened. He loses 10 minutes of content but saves the campaign.

**Capability Revealed:** Auto-checkpoint system, session restore functionality, clear error messaging.

---

### Journey 3: Dr. Chen - Research Observation

**Persona:** Dr. Chen, AI researcher studying emergent multi-agent behavior. Uses autodungeon as a controlled environment for experiments.

**Opening Scene:**
Dr. Chen is writing a paper on narrative coherence in multi-LLM systems. She needs data: can multiple LLMs with independent memory maintain consistent storylines without human intervention?

**Rising Action:**
She configures autodungeon with 4 PC agents and a DM, all set to autopilot. No human intervention. She starts a session and lets it run for 50 turns while she works on other research.

She opens the transcript log - a complete JSON record of every turn, including which agent spoke, what they said, timestamps, and any tool calls (dice rolls, etc.).

**Climax:**
Analyzing the transcripts, she notices something interesting: the agents naturally developed a callback pattern. Events from turn 12 were referenced in turn 38. Character personalities remained consistent. One agent (the cleric) consistently advocated for peaceful solutions across all encounters.

She has data for her paper.

**Resolution:**
Dr. Chen runs 10 more sessions with different configurations (different LLM models, different character setups). She exports all transcripts and builds a coherence scoring methodology. The paper gets accepted at a workshop. She cites autodungeon in the methodology section.

**Capability Revealed:** Full transcript logging (JSON export), autopilot mode, configurable agent setup, multi-session comparison capability via saved transcripts.

---

### Journey 4: Alex - Content Creation

**Persona:** Alex, Twitch streamer looking for unique content. Sees autodungeon as a new genre: "AI plays D&D."

**Opening Scene:**
Alex finds autodungeon on Twitter. The clip shows AI agents arguing about whether to trust an NPC. Alex thinks: "My viewers would love this. Nobody else is streaming this."

**Rising Action:**
Alex sets up autodungeon with OBS screen capture on the web UI. Creates a colorful party with exaggerated personalities: an arrogant wizard, a cowardly barbarian, a cynical cleric, and a too-helpful bard.

Starts streaming. The AI agents immediately start clashing in entertaining ways. Chat goes wild when the barbarian runs from a spider.

**Climax:**
Mid-stream, something unexpected happens: the bard starts lying to the party about a treasure map. The DM plays along. The other agents don't catch on. Alex sees it unfolding and decides to drop in as the wizard to confront the bard in-character.

Chat explodes. "THE STREAMER IS IN THE GAME." The confrontation is dramatic and unscripted.

**Resolution:**
The stream clips go viral on TikTok. Alex makes "AI D&D" a weekly series. Viewers start requesting specific party compositions and scenarios. Alex becomes known as the "AI Dungeon Master" streamer.

**Capability Revealed:** Screen-capture-friendly UI, drop-in interaction during observation, entertaining agent behaviors, unique content potential.

---

### Journey Requirements Summary

| Journey | Key Capabilities Revealed |
|---------|--------------------------|
| Marcus Happy Path | Watch mode, drop-in mode, session persistence, character memory, multi-session continuity |
| Marcus Edge Case | Auto-checkpoint system, session restore, error handling, clear UI feedback |
| Dr. Chen Research | Full transcript logging, autopilot mode, JSON export, configurable agents |
| Alex Content | Screen-capture-friendly UI, entertaining agent interactions, seamless drop-in during stream |

**Core Capabilities Required for MVP:**

1. Watch Mode with real-time narrative display
2. Drop-In Mode with seamless human takeover
3. Session persistence with auto-checkpoints
4. Transcript logging for research export
5. Autopilot mode (no human required)
6. Session restore from checkpoint
7. Clear error messaging and recovery

## Innovation & Novel Patterns

### Detected Innovation Areas

**Primary Innovation: Autonomous Multi-Agent D&D**

autodungeon occupies a unique position at the intersection of:

1. **AI Research Tool** - Study emergent LLM collaborative behavior in a controlled environment
2. **Accessible D&D** - Play without coordinating friends or schedules
3. **Entertainment Product** - Watch AI agents have adventures together

**No existing solution addresses:**

- Autonomous multi-LLM agents playing D&D together
- Human-optional observation mode (watch agents roleplay)
- Research-focused emergent behavior tracking
- Hybrid human drop-in/drop-out gameplay

### Market Context & Competitive Landscape

| Competitor | Approach | Gap |
|------------|----------|-----|
| Friends & Fables | Human players + AI DM | Still requires coordinating humans |
| AI Dungeon | Human player + AI narrator | No party dynamics, no observation mode |
| SillyTavern | Multi-NPC chat | Chat-focused, no game mechanics |
| DreamGen | Single user controls all characters | No autonomous agent behavior |

**Strategic Position:** autodungeon is the first to combine autonomous multi-agent play with human observation and frictionless drop-in participation.

### Academic Foundation

The CollabStory dataset (NAACL 2024) validates the core premise:

- 32,000+ stories generated by 1-5 LLMs collaborating
- LLMs maintain coherence comparable to single-author baselines
- Key finding: Multi-agent narrative coherence is academically proven viable

**Research Gap Addressed:** "Fully emergent narrative behavior (where plot direction emerges unpredictably from agent interactions)" remains understudied. autodungeon directly addresses this gap.

### Validation Approach

**Technical Validation:**

- Agents maintain coherent conversation for 30+ turns
- Characters exhibit distinct, recognizable personalities
- Callbacks and references occur naturally

**Emotional Validation:**

- Stories are interesting enough to make users want to drop in
- "I didn't expect that!" moments occur regularly
- Users check back on adventures

**Research Validation:**

- Full transcripts enable coherence analysis
- Character differentiation is measurable
- Emergent behavior can be detected and studied

## Web Application Technical Requirements

### Project-Type Overview

autodungeon is a client-server web application with a Python backend (FastAPI) and a SvelteKit frontend. It runs locally on the user's machine, connecting to external LLM APIs for agent intelligence. The backend exposes a WebSocket API for real-time game state streaming and REST endpoints for session/configuration management. The frontend renders narrative in real-time and provides interactive controls that never interrupt the game engine. The application prioritizes real-time narrative display, seamless human interaction, and persistent game state across sessions.

### Technical Architecture Considerations

**Application Type:** Local client-server application (FastAPI backend + SvelteKit frontend)

**Runtime Environment:**

- Python 3.10+ required (backend: game engine, API layer)
- Node.js 20+ required (frontend: SvelteKit build and dev server)
- FastAPI for API and WebSocket endpoints
- SvelteKit for reactive frontend UI
- LangGraph for multi-agent orchestration
- External LLM API connections (Gemini, Claude, Ollama)

**Deployment Model:**

- Self-hosted on user's local machine
- No cloud deployment for MVP
- Users clone repo, install Python and Node.js dependencies, configure API keys
- Backend and frontend can run as a single process (FastAPI serves SvelteKit build) or separately during development

### UI/UX Requirements

**Narrative Display:**

- Turn-by-turn rendering (not word-by-word streaming)
- Clear visual distinction between DM narration, PC dialogue, and actions
- Character attribution for each message
- Scrollable history with current turn highlighted

**Responsive Design:**

- Desktop-first design (primary use case)
- Mobile/tablet support strongly desired
- Minimum viewport: 375px width (mobile portrait)
- Touch-friendly controls for drop-in buttons

**Accessibility:**

- No specific accessibility requirements for MVP
- Standard semantic HTML and ARIA attributes sufficient

### State Persistence

**Storage Strategy:**

- Local file storage for game state (JSON/YAML)
- SQLite optional if indexing/querying becomes necessary
- Auto-checkpoint after each turn
- Session files organized by campaign

**Data Structure:**

- Ground truth log (complete history)
- Agent memories (per-character compressed summaries)
- Turn queue and game configuration
- Checkpoint snapshots for restore capability

### LLM Configuration

**Configuration Method:** UI Settings (dedicated settings page)

**Configurable Options:**

- Global summarizer model selection
- Per-agent primary model selection (DM, each PC)
- Per-agent context limit settings
- API key management (environment variables or UI input)

**Supported Providers:**

- Google Gemini (ChatGoogleGenerativeAI)
- Anthropic Claude (ChatAnthropic)
- Local models via Ollama (ChatOllama)

### Performance Targets

**Response Time:**

- No strict latency requirements for MVP
- "Reasonable responsiveness" - turn generation within typical LLM response times
- UI remains fully interactive during LLM API calls (event-driven architecture, no blocking)

**Resource Usage:**

- Must run on 16GB RAM system
- Minimize memory footprint for agent state
- Efficient checkpoint storage (don't store redundant data)

### Implementation Considerations

**Key Technical Decisions:**

1. FastAPI + SvelteKit for event-driven UI with persistent WebSocket connections (replacing Streamlit, which was architecturally incompatible with real-time game engine requirements)
2. LangGraph supervisor pattern for turn management
3. Pydantic models for type-safe game state
4. JSON/YAML file storage (no database complexity for MVP)
5. Environment-based API key configuration with UI override option
6. WebSocket for real-time narrative streaming and bidirectional control commands

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Experience MVP

The goal is to prove that watching AI agents play D&D together is genuinely fun and creates the emotional response we're targeting - the "I want to drop in" moment. Technical validation (coherence, memory) serves the emotional validation, not the other way around.

**Resource Model:** Solo developer, full scope commitment

**Risk Acceptance:** Proceeding despite technical uncertainty around long-session coherence. The CollabStory research provides confidence, and checkpoint/restore provides fallback if coherence degrades.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**

| Journey | MVP Support Level |
|---------|-------------------|
| Marcus Happy Path | Full support |
| Marcus Edge Case (Recovery) | Full support |
| Dr. Chen Research | Basic support (transcript logging) |
| Alex Content | Basic support (screen-capture friendly UI) |

**Must-Have Capabilities:**

1. **Multi-Agent Game Loop**
   - DM Agent (narration, NPC control, encounter management)
   - N Player Character Agents (configurable, default 4)
   - Turn-based narrative exchange
   - Basic scene management (combat, roleplay, exploration)

2. **Memory System**
   - Short-term context window per agent
   - Session summaries persisted between sessions
   - Character facts/traits maintained

3. **Human Interaction**
   - Watch Mode (real-time narrative streaming)
   - Drop-In Mode (take control of any PC)
   - Nudge Option (influence without full control)
   - Seamless transition between modes

4. **Viewer Interface (SvelteKit + WebSocket)**
   - Real-time narrative display via WebSocket streaming with character attribution
   - Visual distinction (DM vs PC vs actions) using character-colored components
   - Drop-In buttons per character
   - Session controls (pause, speed) that never interrupt the game engine
   - Session history with virtual scrolling for large sessions

5. **Persistence & Recovery**
   - Auto-checkpoint per turn
   - Session restore from checkpoint
   - Campaign file organization
   - Full transcript logging (JSON)

6. **LLM Configuration**
   - Multi-provider support (Gemini, Claude, Ollama)
   - Per-agent model selection via UI
   - API key management

### Post-MVP Features

**Phase 2 - Enhanced Experience (v1.1):**

| Feature | Rationale |
|---------|-----------|
| Module selection & campaign setup | Query LLM for 100 known modules, select for DM context |
| Character sheets (dynamic) | Full D&D 5e sheets, DM updates via tools, context injection |
| Character creation UI | Step-by-step wizard with AI backstory generation |
| DM whisper/secrets system | Private channels to agents, dramatic irony |
| Callback tracker | Extract narrative elements, suggest callbacks, track references |
| Fork gameplay | Branch exploration from checkpoints, compare timelines |

**Phase 2.5 - Refinements (v1.2):**

| Feature | Rationale |
|---------|-----------|
| INT-based variable memory | Smarter characters remember more - adds depth |
| Advanced pacing curves | Tension → release → climax rhythms |

**Phase 2.9 - UI Framework Migration (v2.0):** *(Applied to PRD 2026-02-11; implementation pending as Epic 16)*

| Feature | Rationale |
|---------|-----------|
| FastAPI API layer | WebSocket streaming, REST endpoints, decoupled game engine |
| SvelteKit frontend | Event-driven UI, scoped CSS, reactive stores, no game engine interruption |
| Streamlit deprecation | Rerun-model incompatible with real-time game engine; causes autopilot death on widget interaction, WebSocket drops in long sessions |

**Phase 3 - Community & Scale (v2.x):**

| Feature | Rationale |
|---------|-----------|
| Share campaigns/transcripts | Community content sharing |
| Community-created scenarios | User-generated content |
| Streaming integration | Native OBS/Twitch support |
| Research dashboard | Coherence metrics visualization |
| Multiplayer/network play | Multiple humans, remote sessions |

### Risk Mitigation Strategy

**Technical Risk: Long-session coherence**

- *Mitigation:* Simple memory system with session summaries prevents context window overflow. Checkpoint/restore provides recovery path if coherence degrades. CollabStory research provides confidence in viability.
- *Fallback:* If 30+ turn coherence proves difficult, can recommend shorter session lengths while memory system is refined.

**Technical Risk: Character differentiation**

- *Mitigation:* Distinct personality prompts with character trait enforcement in system prompts.
- *Fallback:* If characters become indistinguishable, can strengthen personality constraints or reduce party size.

**Technical Risk: Narrative quality**

- *Mitigation:* Improv principles ("Yes, and...") baked into prompts; DM pacing awareness to vary tension.
- *Fallback:* If stories become repetitive, can add scenario variety or DM guidance rules.

**Technical Risk: LLM API failures**

- *Mitigation:* Auto-checkpoint per turn; graceful error handling with clear messaging and restore capability.
- *Recovery:* User can restore to any previous turn without data loss.

**Market Risk: Is this actually fun?**

- *Mitigation:* Experience MVP approach - get to "fun" quickly and validate emotional response before building advanced features.
- *Validation:* Personal use, sharing with D&D friends, Reddit/HN community feedback.

**Resource Risk: Solo developer scope**

- *Mitigation:* Full commitment to current scope, but features are intentionally modular. If overwhelmed, can defer Phase 2 features indefinitely.
- *Contingency:* Core loop (DM + PCs + Watch Mode) is the minimum viable slice. Drop-In and Recovery can be simplified if needed.

## Functional Requirements

### Multi-Agent Game Loop

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

### Memory & Context Management

- FR11: Each agent can maintain a short-term context window of recent events
- FR12: System can generate session summaries for long-term memory persistence
- FR13: Agents can reference events from previous turns within the same session
- FR14: Agents can reference events from previous sessions via summaries
- FR15: Character facts and traits can persist across sessions
- FR16: System can compress memory when context limits are reached

### Human Interaction

- FR17: User can observe the game in Watch Mode without intervening
- FR18: User can take control of any PC agent at any time (Drop-In Mode)
- FR19: User can release control and return PC to AI autopilot
- FR20: User can send suggestions to the game without taking full control (Nudge)
- FR21: User can pause the game at any point
- FR22: User can resume a paused game
- FR23: User can adjust game speed (time between turns)
- FR24: System can run fully autonomously without human intervention (Autopilot Mode)

### Viewer Interface

- FR25: User can view narrative in real-time as turns are streamed via WebSocket
- FR26: User can distinguish between DM narration, PC dialogue, and actions via character-colored message components
- FR27: User can see which character is speaking via literary "Name, the Class:" attribution
- FR28: User can scroll through session history with virtual scrolling for sessions exceeding 200 turns
- FR29: User can see the current turn highlighted in the narrative
- FR30: User can access Drop-In controls for each PC character
- FR31: User can access session controls (pause, speed, etc.)
- FR32: User can view session history and transcript

### Persistence & Recovery

- FR33: System can auto-save game state after each turn (checkpoint)
- FR34: User can view list of available checkpoints for a session
- FR35: User can restore game state from any previous checkpoint
- FR36: System can restore agent memories to checkpoint state
- FR37: User can continue a previous campaign across multiple sessions
- FR38: System can organize session files by campaign
- FR39: System can export full transcript as JSON for research analysis
- FR40: System can display clear error messages when LLM API calls fail
- FR41: User can recover from errors without losing significant progress

### LLM Configuration

- FR42: User can select which LLM provider to use for the DM agent
- FR43: User can select which LLM provider to use for each PC agent
- FR44: User can select which LLM to use for memory summarization
- FR45: User can configure context limits per agent
- FR46: User can manage API keys through environment variables
- FR47: User can override API key configuration through UI settings
- FR48: System can support Google Gemini models
- FR49: System can support Anthropic Claude models
- FR50: System can support local models via Ollama

### Agent Behavior

- FR51: DM Agent can incorporate improv principles ("Yes, and...") in responses
- FR52: PC Agents can exhibit distinct, consistent personalities
- FR53: Agents can make callbacks to earlier events in the narrative
- FR54: DM Agent can use dice roll results to inform narrative outcomes
- FR55: System can execute dice rolls with standard D&D notation

### Module Selection & Campaign Setup (v1.1)

- FR56: User can query the DM for available D&D modules from its training knowledge
- FR57: System can present a list of 100 modules with number, name, and description in JSON format
- FR58: User can select a specific module or choose random selection from available modules
- FR59: Selected module context can be injected into the DM's system prompt for campaign guidance

### Character Sheets (v1.1)

- FR60: Each PC can have a complete D&D 5e character sheet with abilities, skills, HP, AC, and equipment
- FR61: Character sheets can include spells, spell slots, and class features
- FR62: Character sheets can include personality traits, ideals, bonds, and flaws
- FR63: User can view any character's sheet in a dedicated UI panel
- FR64: DM Agent can update character sheets via tool calls (HP changes, inventory, status effects)
- FR65: Character sheet data can be injected into agent context (DM sees all, PC sees own)
- FR66: System can display notifications when character sheet values change during gameplay

### Character Creation (v1.1)

- FR67: User can create new characters through a step-by-step wizard interface
- FR68: System can use AI to assist with backstory generation based on class/race/background
- FR69: System can validate character builds against D&D 5e rules (ability scores, proficiencies)
- FR70: User can save created characters to a persistent character library for reuse

### DM Whisper & Secrets System (v1.1)

- FR71: DM Agent can send private whispers to individual PC agents not visible to others
- FR72: PC agents can receive and act on secret information from whispers
- FR73: User can send whispers to the DM to influence story direction
- FR74: System can track which secrets have been revealed vs. still hidden
- FR75: DM can trigger secret revelation moments when dramatically appropriate

### Callback Tracking (v1.1)

- FR76: System can extract narrative elements (names, items, events, promises) from agent dialogue
- FR77: System can store extracted elements in a structured callback database
- FR78: DM Agent can receive suggestions for callbacks to earlier narrative elements
- FR79: System can detect when agents naturally reference earlier narrative elements
- FR80: User can view callback history and track unresolved narrative threads

### Fork Gameplay (v1.1)

- FR81: User can create a fork from any checkpoint to explore alternate storylines
- FR82: System can manage multiple active forks with distinct GameState branches
- FR83: User can compare forks side-by-side to see divergent narratives
- FR84: User can resolve forks by selecting one branch to continue as canonical

### AI Scene Illustration & Gallery (v2.1)

- FR85: User can generate an AI illustration of the current scene
- FR86: User can generate an AI illustration of the "best scene" from the entire session, using a configurable LLM to scan/analyze session history
- FR87: User can generate an AI illustration of a scene at a specific turn number
- FR88: Turn numbers are visible in the narrative display (format: "Turn N — Name, the Class:")
- FR89: User can configure the text-to-image model (Imagen 3, Imagen 4, Gemini Flash Image)
- FR90: User can configure which LLM model scans session history for "best scene" selection
- FR91: User can download an individual generated image or bulk-download all images for a session
- FR92: Generated images are stored in the campaign directory for persistence

**Illustration Gallery (v2.1):**

- FR93: User can browse all session illustrations in a modal gallery with thumbnail grid, hover-to-view prompt, and card metadata (turn number, generation mode, timestamp)
- FR94: User can click a gallery thumbnail to open a full-size lightbox view with image navigation (prev/next), metadata panel, and download button
- FR95: User can switch between sessions within the gallery modal to browse illustrations from other adventures
- FR96: User can access the illustration gallery from the adventures list page, with image count badges on session cards
- FR97: Backend provides a lightweight session image summary endpoint for gallery population and image count badges

## Non-Functional Requirements

### Performance

| Requirement | Specification |
|-------------|---------------|
| Turn Generation Timeout | Up to 2 minutes per turn is acceptable |
| UI Responsiveness | UI must remain fully interactive during LLM API calls; user controls must never interrupt background game engine processes |
| Visual Feedback | Spinner or "thinking..." indicator must display while waiting for turn generation |
| Memory Footprint | Must run comfortably on 16GB RAM system |
| Checkpoint Storage | Efficient storage - avoid redundant data in checkpoint files |

### Integration

| Requirement | Specification |
|-------------|---------------|
| LLM Provider Support | Must support Gemini, Claude, and Ollama simultaneously |
| API Failure Handling | Display clear error message and offer checkpoint restore |
| Provider Switching | User can change LLM provider mid-campaign without data loss |
| API Key Management | Configurable via environment variables OR UI settings |
| Network Dependency | Requires stable internet for cloud LLM providers; Ollama works offline |

### Reliability

| Requirement | Specification |
|-------------|---------------|
| Auto-Checkpoint Frequency | Every turn automatically saved |
| Recovery Granularity | User can restore to any previous turn |
| State Consistency | Checkpoint restore must restore complete agent memory state |
| Data Integrity | Session files must remain valid even after unexpected shutdown |
| Error Recovery | User can recover from any error without losing more than current turn |

### Stability

| Requirement | Specification |
|-------------|---------------|
| WebSocket Connection | Must survive 12+ hour sessions with automatic reconnection on drop |
| UI Non-Interruption | User interactions (controls, navigation, settings) must not interrupt background game engine processes (autopilot, turn generation) |
| Long-Session Rendering | Sessions with 200+ turns must render efficiently via virtual scrolling without UI degradation |

### Build & Deployment

| Requirement | Specification |
|-------------|---------------|
| Backend Runtime | Python 3.10+ (game engine, FastAPI API layer) |
| Frontend Runtime | Node.js 20+ (SvelteKit build pipeline, dev server) |
| Dual Runtime | Backend and frontend can be served together (FastAPI serves SvelteKit build artifacts) or separately during development |
| Dependency Management | Python: uv/pip; Node.js: npm/pnpm |
