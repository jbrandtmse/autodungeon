---
stepsCompleted: [1, 2, 3, 4]
status: complete
inputDocuments: ['docs/prompt.md']
session_topic: 'Complete exploration of autodungeon - game experience, architecture, LLM agent design, human-AI interaction, and differentiating features'
session_goals: 'Generate innovative features list, crystallize clear vision of magic moments, uncover research/experiment ideas'
selected_approach: 'ai-recommended'
techniques_used: ['Role Playing', 'What If Scenarios', 'Cross-Pollination', 'Emergent Thinking']
ideas_generated: ['variable-memory-by-character', 'dm-whisper-system', 'secret-goals', 'in-character-deception', 'pause-rewind-fork', 'campaign-continuity', 'shareable-replays', 'improv-principles-in-prompts', 'pacing-curves-for-dm', 'callback-tracker', 'character-arc-system']
context_file: 'docs/prompt.md'
current_phase: complete
---

# Brainstorming Session: autodungeon

**Date:** 2026-01-24
**Project:** autodungeon - Multi-Agent D&D Game Engine
**Facilitator:** Mary (Business Analyst)

---

## Session Overview

**Topic:** Complete exploration of autodungeon - game experience, architecture, LLM agent design, human-AI interaction, and differentiating features

**Goals:**
- Generate a rich list of innovative features
- Crystallize a clear vision of the "magic moments"
- Uncover compelling ideas for the research/experiment dimension

### Context Guidance

This project serves dual purposes:
1. **Research/Experiment** - Explore emergent behavior when multiple LLMs roleplay together
2. **Interactive Experience** - Create a playable human-in-the-middle game

Core architecture involves a multi-agent harness with DM Agent, PC Agents, optional Human Player, and flexible autopilot/hybrid modes.

### Session Setup

- **Approach:** AI-Recommended Techniques
- **Scope:** Full exploration across all project dimensions
- **Output Focus:** Features, vision clarity, research ideas

---

## Technique Selection

**Approach:** AI-Recommended Techniques
**Analysis Context:** Multi-agent D&D game engine with dual focus on research experimentation and interactive gameplay

**Recommended Technique Sequence:**

1. **Role Playing** - Embody DM Agent, PC Agents, Human Player, and Researcher perspectives
2. **What If Scenarios** - Break constraints and explore radical possibilities
3. **Cross-Pollination** - Transfer solutions from improv, psychology, MMO design, and other domains
4. **Emergent Thinking** - Let patterns crystallize into clear vision and research hypotheses

**AI Rationale:** This sequence builds from empathy (understanding all stakeholders) through divergent generation (features and possibilities) to synthesis (research vision). The dual nature of the project requires both creative game-design thinking and analytical research framing.

---

## Ideation Rounds

### Phase 1: Role Playing - Stakeholder Perspectives

#### DM Agent Perspective
- **Wants:** PCs to roleplay their character actions from presented scenarios
- **Frustrated by:** Agents breaking character or getting distracted
- **Success:** Presenting immersive scenarios that encourage participation
- **Secret management:** Holds scenario secrets (DMG-style), creates tension through controlled disclosure, gives hints when stuck

#### PC Agent Perspective
- **Needs:** Immersive story + helpful hints when needed
- **Feels real when:** Being part of the scenario, contributing to storytelling
- **Relationships:** Different dynamics with each PC - friends, rivals, complex bonds
- **Frustrated by:** Impossible scenarios that block creative action

#### Human Player Perspective
- **Why join:** "The agents look like they're having so much fun, I want to join in"
- **Most engaged:** When story takes creative turns outside the script - and it WORKS
- **Drop-in trigger:** When it looks fun, unique scenarios emerging
- **Wow factor:** "Remember D&D as a kid? Now you can have agents playing and JOIN IN"

#### Researcher Perspective
- **Hoping to observe:** Surprising storytelling, insights into LLM intelligence, emergent behavior
- **Data needed:** Full transcript + private LLM reasoning/insights
- **Would be surprised by:** Spontaneous side quests
- **Core question:** "When are LLMs intelligent enough to CREATE interactive stories, not just deliver them?"

#### Emerging System Requirements
1. Character consistency mechanisms
2. Adaptive scaffolding (immersion-first, hints when needed)
3. Relationship modeling between PCs
4. Fun visibility - make joy contagious and observable
5. Emergence detection - celebrate spontaneous creativity
6. Multi-layer logging (public narrative + private reasoning)
7. Frictionless human entry

---

### Phase 2: What If Scenarios - Constraint Breaking

#### Memory & Context
- **Variable memory by character:** Memory as character trait (high-INT wizard remembers more, barbarian lives in the moment)
- **Campaign continuity:** Sessions build on each other, fun moments get reused
- Perfect memory unrealistic; no memory breaks campaigns; variable is optimal

#### Information & Secrets
- **DM whisper system:** Private information channels to individual agents
- **Secret goals:** Hidden objectives per character (evil alignment, personal quests)
- **Ability-gated information:** Languages, clairvoyance, magic reveal different things
- **In-character deception:** OK when it serves story; strategic gaming between PCs acceptable

#### Agency & Control
- **Pause/rewind/fork:** Human can pause and take over, or fork to explore "what if"
- **Whisper to DM:** Human guidance without breaking game flow (validates existing whisper_queue design)
- **Multi-human (add-on):** Network feature for future, not MVP

#### Meta Layer
- **Shareable replays:** Watch other sessions, best-of compilations
- **Scenario comparison:** Run same scenario with different configs for research

#### Design Principles
1. Memory as character trait, not just technical limit
2. Information asymmetry serves the story
3. DM is master but responsible for fun
4. Human can nudge without breaking immersion
5. Sessions should persist and grow into campaigns

---

### Phase 3: Cross-Pollination - Ideas from Other Domains

#### Improv Theater
- **"Yes, and..." principles** embedded in agent system prompts
- Agents should build on each other's offers, never block
- Status games, callbacks, finding the game

#### Game Design
- **Pacing curves** in DM instructions (tension → release → build → climax)
- Flow state management (challenge matches skill)
- Reward moments, discovery satisfaction

#### Film/TV Writing
- **Chekhov's Gun callback system:** Track what emerges, use it later
- **Character arc tracking:** Growth, motivations, internal conflicts
- **Discovery-first, narrate-to-pace:** Let players find things, but keep momentum

---

### Phase 4: Emergent Thinking - Synthesis

#### Core Themes Identified
1. **Emergent creativity** - Spontaneous side quests, creative turns that "work"
2. **Contagious fun** - "Agents look like they're having fun, I want to join"
3. **Realistic simulation** - Variable memory, character arcs, relationship dynamics
4. **Human as special guest** - Frictionless entry, whisper controls, drop-in/out
5. **Research as byproduct** - Full transcripts, emergence detection

#### Vision Statement
> **"Nostalgia for D&D, made accessible for people who can't coordinate 4 friends"**

#### Primary Research Hypothesis
> **Collaborative Coherence:** "Multiple LLMs with independent memory can maintain narrative coherence across extended sessions without human intervention."

#### Coherence Metrics
- Story consistency (facts stay stable)
- Character fidelity (personalities persist)
- Callback rate (earlier events referenced later)
- Contradiction frequency (how often agents contradict)
- Recovery from drift (group recovers from off-script moments)

#### The Magic Moment
> *You're watching AI agents play D&D. The rogue just made a callback to something the wizard said three sessions ago. The whole table laughs. You realize: "They're actually building something together." And then: "I want in."*

---

## Session Outputs

### Feature Ideas (Prioritized)

#### Core Features (MVP)
1. Variable memory by character (INT-based)
2. DM whisper system for private info
3. Improv principles in agent prompts
4. Pacing curve awareness for DM
5. Pause/rewind for human control
6. Full transcript logging
7. Character consistency mechanisms

#### High Priority (Post-MVP)
1. Secret goals system
2. Callback tracker (Chekhov's Gun)
3. Character arc tracking
4. Fork gameplay for exploration
5. Campaign continuity across sessions
6. Emergence detection/celebration

#### Future/Add-on
1. Shareable replays
2. Multi-human network play
3. Scenario comparison for research
4. Best-of compilation generation

### Research Questions
1. Can LLMs maintain narrative coherence with independent memory?
2. Do improv-trained agents produce more surprising creativity?
3. When do humans choose to join vs. observe?
4. Can we detect and measure "emergence events"?

### Next Steps
1. Proceed to **Research** workflow for technical/competitive analysis
2. Then **Product Brief** to formalize vision and requirements
3. Use these brainstorming outputs as input context

---

## Supplemental Research: Core DM Concepts

*Quick research to inform DM agent design*

### The 7 Pillars of Dungeon Mastering

| Skill | Description | Implication for DM Agent |
|-------|-------------|-------------------------|
| **Storytelling** | Compelling hooks, weaving player backstories, vivid sensory narration | Agent needs rich descriptive output, character awareness |
| **Pacing** | Alternate fast (combat/exploration) with slow (roleplay), maintain momentum | Pacing curve awareness - validates brainstorming |
| **Player Engagement** | Passion, unique NPC voices, incorporate player creativity | Agent must react to and build on PC actions |
| **Improvisation** | Adapt to unexpected actions, quick thinking | Core LLM strength - embrace uncertainty |
| **World Building** | Novel settings, NPC motivations (1-3 key points each), immersive environments | Structured NPC/location data, avoid clichés |
| **Encounter Design** | Balance party strength, sensory descriptions, noticeable clues | Challenge calibration |
| **Challenge Balance** | Fair rules, Difficulty Classes (5-30 scale), collaborative not combative | DM is master but responsible for fun |

### New Design Patterns from Research

- **NPC design pattern:** 1-3 key points per NPC (motivation, personality, quirk)
- **DC scale:** 5 (very easy) → 30 (nearly impossible) for skill checks
- **Co-storyteller role:** DM collaborates, doesn't dictate outcomes
- **Sensory narration:** Describe using all 5 senses (sight, sound, smell, taste, touch)
- **Avoid clichés:** "You meet in a tavern" is overused - start with unique hooks

### Sources
- [DiceBag: Traits Every DM Needs](https://dicebag.co.uk/blogs/the-scroll/become-a-better-dm-traits-every-dungeon-master-needs)
- [D&D Beyond: How to Be a DM](https://www.dndbeyond.com/posts/1452-how-to-be-a-dungeon-master)
- [DND Duet: Basic Roles of the DM](https://dndduet.com/the-basic-roles-of-the-dungeon-master/)

---

