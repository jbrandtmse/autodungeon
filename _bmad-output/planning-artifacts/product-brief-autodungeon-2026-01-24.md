---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - "analysis/brainstorming-session-2026-01-24.md"
  - "planning-artifacts/research/technical-autodungeon-research-2026-01-24.md"
  - "docs/prompt.md"
date: 2026-01-24
author: Developer
project: autodungeon
---

# Product Brief: autodungeon

## Executive Summary

**autodungeon** is a multi-agent D&D game engine that brings the magic of collaborative tabletop roleplaying to anyone with a computer - no scheduling, no flaky friends, no compromise.

At its core, autodungeon solves a problem that millions of former D&D players face: the longing for emergent, collaborative storytelling that modern life makes nearly impossible to organize. Unlike scripted video game RPGs or lonely solo adventures, autodungeon creates a living party of AI characters that play together, develop relationships, and generate surprising stories - while you watch, laugh, and jump in whenever you want.

The product serves a dual purpose: it delivers genuine entertainment value to nostalgic players, while simultaneously advancing research into multi-agent LLM collaboration. The system proves that multiple AI agents with independent memory can maintain narrative coherence and create genuinely emergent storytelling - a previously understudied capability with implications far beyond gaming.

**Vision Statement:** *"Nostalgia for D&D, made accessible for people who can't coordinate 4 friends."*

---

## Core Vision

### Problem Statement

Millions of adults who grew up playing Dungeons & Dragons have been forced to abandon the hobby - not because they lost interest, but because coordinating 4+ schedules for regular sessions is nearly impossible in modern life. The result: a generation of players who remember the magic of collaborative storytelling but have no way to experience it.

### Problem Impact

- **Unfulfilled nostalgia**: The unique joy of emergent, collaborative storytelling remains inaccessible
- **Inadequate substitutes**: Video games are scripted; solo adventures lack social dynamics; watching streams is passive
- **Lost creative outlet**: The improvisational, collaborative nature of D&D is irreplaceable by individual activities

### Why Existing Solutions Fall Short

| Solution | Critical Gap |
|----------|-------------|
| Video game RPGs | Stories are discovered, not collaboratively created |
| Solo adventures | Missing the surprise and creativity of other players |
| AI DM tools (AI Dungeon, etc.) | Still require human to be the player - no party dynamics |
| Coordinated play (Friends & Fables) | Still requires scheduling real humans |
| Streaming/watching | Passive consumption, not participation |

**No existing solution recreates the emergent party dynamic without requiring human coordination.**

### Proposed Solution

autodungeon creates a self-playing D&D party where:
- **One AI acts as Dungeon Master**, narrating the world and managing NPCs
- **Multiple AIs play as Player Characters**, each with distinct personalities, goals, and memories
- **The human can watch the adventure unfold** like a living story
- **At any moment, the human can "drop in"** to control a character, then leave when desired

The system uses improv theater principles ("Yes, and..."), game design pacing curves, and variable character memory to create genuinely collaborative, surprising stories - not scripted experiences.

### Key Differentiators

1. **Watch-First Experience**: The AI party plays without you; join when it looks fun
2. **True Party Dynamics**: Multiple LLMs interact as distinct characters, not just user + AI
3. **Emergent Storytelling**: Improv principles and memory systems create genuine surprises
4. **Research Foundation**: Full logging enables study of multi-agent narrative coherence
5. **Frictionless Human Entry**: Drop in/out without disrupting the game
6. **Dual Value Proposition**: Entertainment product + AI research platform

---

## Target Users

### Primary User Persona

**"Marcus" - The Nostalgic Professional**

*Demographics:*
- Age: 42 (Gen X)
- Occupation: Software engineer, but could be any professional
- Life Stage: Working professional, possibly with family responsibilities
- Location: Suburban home, limited social time

*D&D History:*
- Played heavily in middle school and high school (late 80s/early 90s)
- Stopped when life got busy - college, career, family
- Has tried multiple times to restart with old friends or new groups
- Every attempt fizzles: scheduling conflicts, someone moves, life happens

*Current State:*
- Watches Critical Role or Dimension 20 while doing chores
- Played Baldur's Gate 3 and loved it, but it's still scripted
- Has experimented with ChatGPT for interactive storytelling - it's okay but lonely
- Accepted that "real D&D" isn't happening anymore
- Misses the party dynamic most - the surprise of what other players do

*Success Vision:*
> "I want to feel like I'm at the table again - but on my own schedule. If I could watch AI characters develop relationships and go on adventures, and jump in when I feel like it... that would be magic."

---

### Secondary User Personas

**"Dr. Chen" - The AI Researcher**

*Profile:*
- Academic or industry AI researcher interested in emergent multi-agent behavior
- Uses autodungeon as a research platform, not primarily entertainment
- Values: full transcripts, metrics, ability to compare scenarios

*Success Vision:*
> "I need a controlled environment to study how LLMs coordinate narrative without explicit training. The D&D framing is ideal - clear roles, measurable coherence."

**"Alex" - The Content Creator**

*Profile:*
- YouTube/Twitch streamer looking for unique content
- Sees autodungeon as a new genre: "AI plays D&D"
- Would stream sessions, commentate, join at dramatic moments

*Success Vision:*
> "This is a completely new type of content. Nobody else has AI agents actually playing D&D together. The unpredictability is perfect for streaming."

---

### User Journey: Marcus

| Stage | Experience |
|-------|------------|
| **Discovery** | Sees a Reddit post: "I built AI agents that play D&D together" - clicks immediately |
| **First Impression** | Watches a 5-minute demo of agents roleplaying - recognizes the party dynamic he misses |
| **Onboarding** | Starts his first session - creates a party of classic characters (fighter, rogue, wizard, cleric) |
| **First Session** | Watches the AI party navigate a dungeon - laughs when the rogue tries to steal from the party |
| **Aha Moment** | The wizard references something that happened 3 sessions ago - "They remember! They're building something!" |
| **Drop-In Experience** | Takes control of the rogue for a critical moment - makes a choice that changes the story |
| **Long-Term** | Runs a campaign that spans weeks - it becomes his evening wind-down ritual |

---

## Success Metrics

### Primary Success Indicator

**The "Phone a Friend" Moment**
> The ultimate success signal: Marcus is so excited by what he's experiencing that he calls his old D&D buddies and says "You have to try this."

This captures the emotional core of success - not just engagement, but genuine enthusiasm that triggers word-of-mouth.

### User Success Metrics

| Metric | What It Measures | Target |
|--------|------------------|--------|
| **Drop-In Rate** | How often users choose to take control during a session | Users drop in at least once per session |
| **Session Continuity** | Users returning to continue the same campaign | Multi-session campaigns become common |
| **Sharing Behavior** | Screenshots, clips, or stories shared with others | Organic sharing without prompting |

### Research Success Metrics

| Metric | What It Measures |
|--------|------------------|
| **Narrative Coherence Score** | Can agents maintain consistent storylines across sessions? |
| **Character Differentiation** | Do agents exhibit distinct, consistent personalities? |
| **Memory Utilization** | Are callbacks and references used naturally and correctly? |
| **Emergent Behavior Rate** | How often do agents do something genuinely unexpected? |

*Note: Specific scoring methodologies to be developed during implementation.*

### Project Success Metrics

**Personal:**
- The creator finds it genuinely fun to use
- It scratches the nostalgic itch it was designed to address

**Community:**
- A small but engaged group of users download, set up, and run their own instances
- Users contribute feedback, bug reports, or improvements
- The project generates interest in AI/gaming communities (Reddit, HackerNews, etc.)

### Business Objectives

This is a passion project with research value, not a commercial product. Success is measured by:

1. **Personal Fulfillment**: Does using autodungeon feel like being at the table again?
2. **Research Contribution**: Does it advance understanding of multi-agent narrative coherence?
3. **Community Interest**: Do others find it compelling enough to try?

*Revenue and scale are explicitly not goals for this phase.*

---

## MVP Scope

### Core Features

**1. Multi-Agent Game Loop**
- DM Agent that narrates scenes, controls NPCs, and manages encounters
- N Player Character Agents (configurable, default 4) with distinct personalities
- Turn-based narrative exchange with natural dialogue flow
- Basic scene management (combat, roleplay, exploration states)

**2. Simple Memory System**
- Short-term context window for immediate conversation
- Basic session summary persisted between sessions
- Character facts/traits maintained across turns
- *Note: Advanced INT-based variable memory deferred to post-MVP*

**3. Human Interaction**
- **Watch Mode**: Stream the adventure in real-time via Streamlit UI
- **Drop-In Mode**: Take control of any PC at any moment
- **Nudge Option**: Influence without full control (suggest actions, ask questions)
- Seamless transition between watching and playing

**4. Viewer Interface (Streamlit)**
- Real-time narrative display with character attribution
- Visual distinction between DM narration, PC dialogue, and actions
- "Drop In" button for each character
- Session controls (pause, speed adjustment)
- Basic session history/transcript

**5. Core Technical Infrastructure**
- LangGraph orchestration with supervisor pattern
- Multi-LLM provider support (Gemini, Claude, Ollama)
- Pydantic data models for game state
- Full transcript logging for research analysis

### Out of Scope for MVP

| Feature | Rationale | Target Phase |
|---------|-----------|--------------|
| INT-based variable memory | Adds complexity; simple memory proves concept first | v1.1 |
| DM whisper/secrets system | Nice-to-have; not essential for core loop | v1.1 |
| Advanced pacing curves | Can be added once basic gameplay works | v1.2 |
| Character creation UI | Can use config files initially | v1.1 |
| Campaign/module library | Start with one hardcoded scenario | v1.2 |
| Multiplayer/sharing | Solo experience first | v2.0 |
| Mobile UI | Desktop Streamlit sufficient | v2.0 |

### MVP Success Criteria

**Technical Validation:**
- [ ] Agents maintain coherent conversation for 30+ turns
- [ ] Characters exhibit distinct, recognizable personalities
- [ ] Human can drop in and out without breaking the narrative
- [ ] Sessions can be paused and resumed

**Emotional Validation:**
- [ ] The story is interesting enough to make you want to drop in
- [ ] At least one "I didn't expect that!" moment per session
- [ ] You find yourself checking back on the adventure

**Research Validation:**
- [ ] Full transcripts are captured and analyzable
- [ ] Character differentiation is measurable across sessions

### Future Vision

**v1.x - Enhanced Experience:**
- INT-based variable memory (smarter characters remember more)
- DM whisper system for secrets and dramatic irony
- Pacing curves that create tension → release → climax rhythms
- Character creation interface
- Multiple campaign modules

**v2.x - Community & Scale:**
- Share campaigns/transcripts with others
- Community-created characters and scenarios
- Streaming integration for content creators
- Research dashboard for Dr. Chen types

**Long-term Vision:**
A platform where anyone can experience the magic of collaborative D&D storytelling on their own schedule, while contributing to AI research on emergent multi-agent behavior.

---

