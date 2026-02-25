# Architecture Deep Dive: Checkpoints, Memory, and Context Building

This document traces how game state flows through the autodungeon system — from LLM responses to checkpoint files, through memory compression, and into agent context windows.

## Table of Contents

- [Turn File Structure](#turn-file-structure)
- [Ground Truth Log](#ground-truth-log)
- [Memory Compression Pipeline](#memory-compression-pipeline)
- [Narrative Element Extraction](#narrative-element-extraction)
- [Context Building and Memory Isolation](#context-building-and-memory-isolation)
- [Full Round Flow](#full-round-flow)
- [Checkpoint Persistence](#checkpoint-persistence)
- [Static Prompt Templates](#static-prompt-templates)

---

## Turn File Structure

Each turn produces a complete `GameState` snapshot saved as `campaigns/session_NNN/turn_NNN.json`. The checkpoint contains:

| Field | Description |
|-------|-------------|
| `ground_truth_log` | Append-only list of all game events (plain strings) |
| `agent_memories` | Per-agent memory: `long_term_summary`, `short_term_buffer`, `character_facts` |
| `character_sheets` | Per-character HP, abilities, inventory, conditions |
| `agent_secrets` | Per-agent whispers from the DM (private knowledge) |
| `narrative_elements` | Per-session extracted NPCs, locations, items, quests |
| `callback_database` | Campaign-level element store for cross-session callbacks |
| `callback_log` | Detected references to dormant narrative elements |
| `turn_queue` | Agent turn order for the current round |
| `game_config` / `dm_config` | Runtime configuration |
| `characters` | Character configs (name, class, provider, model, etc.) |
| `whisper_queue` | Pending DM whispers to deliver |

---

## Ground Truth Log

The `ground_truth_log` is the simplest structure in the system: an **append-only list of plain strings**. No summaries, no structured data — just raw agent output with attribution.

Each turn appends one entry:
```
"[DM]: The fog thickens around the churchyard..."
"[Shadowmere]: I dart forward, rapier gleaming..."
"[Thorin]: Not today, devil."
```

This log serves as:
- The **shared table** — what every player "hears" (PCs read the last N entries as their scene context)
- The **transcript source** — entries are parsed into `transcript.json` for export
- The **debugging record** — complete history of every game event

Key implementation points:
- DM entries: `agents.py:1717` — `f"[DM]: {response_content}"`
- PC entries: `agents.py:2165` — `f"[{character_config.name}]: {response_content}"`
- Human entries: `graph.py:201` — `f"[{controlled}]: {pending_action}"`

---

## Memory Compression Pipeline

Summaries are **not** generated every turn. They are generated during **compression**, which only fires when a buffer approaches its token limit.

### When Compression Triggers

The `context_manager` node (`graph.py:45-110`) runs **once per round, before the DM's turn**. For each agent:

```
is_near_limit(agent_name) → buffer tokens > 80% of token_limit
```

With DM at 32,000 tokens, compression fires at ~25,600 tokens. For PCs at 8,000, it fires at ~6,400 tokens.

### What Compression Does

`MemoryManager.compress_buffer()` (`memory.py:705-769`):

1. Takes all buffer entries **except the most recent few** (`RETAIN_AFTER_COMPRESSION`)
2. Sends them to the **Summarizer LLM** (Gemini 3 Flash) with the Janitor system prompt
3. The Summarizer produces a concise narrative summary preserving essential story information
4. Merges the new summary with the existing `long_term_summary` via `_merge_summaries()`
5. Clears compressed entries from the buffer, keeps recent ones

### Multi-Pass Compression

If the total context (summary + buffer) is still over the token limit after one pass, the system re-compresses the `long_term_summary` itself — up to `MAX_COMPRESSION_PASSES` times (`graph.py:94-96`). This handles edge cases where summaries themselves grow too large.

### Buffer Truncation Safety

The `MAX_BUFFER_CHARS` constant (`memory.py:178`) caps the text sent to the Summarizer at 250,000 characters (~62K tokens). This provides 2x headroom for the largest agent buffer (DM at 32K tokens) and prevents context overflow in the Summarizer LLM.

---

## Narrative Element Extraction

### Trigger: Every Single Turn

Unlike compression, element extraction runs on **every turn** — both DM and PC turns (`agents.py:1731-1746` and `agents.py:2181-2196`). It uses a separate, lightweight LLM call (the Extractor, also Gemini 3 Flash).

### What Gets Extracted

The `NarrativeElementExtractor` (`memory.py:1214-1340`) parses each response into structured `NarrativeElement` objects:

```python
NarrativeElement:
    id: str                    # UUID
    name: str                  # "The Coachman", "Mary's House", "Rusted Key"
    element_type: Literal[     # Category
        "npc", "location", "item", "quest", "organization"
    ]
    description: str           # Context about the element
    turn_introduced: int       # First appearance
    last_referenced_turn: int  # Most recent mention
    dormancy_turns: int        # Turns since last reference
```

### Dual Storage

Extracted elements are stored in two places:
- **`narrative_elements[session_id]`** — per-session tracking
- **`callback_database`** — campaign-level, persists across sessions for cross-session callbacks

### Callback Detection

After extraction, `detect_callbacks()` does fuzzy name-matching against the database to find when agents reference dormant elements. For example, when Shadowmere uses Mary's rusted key 50 turns after finding it, the system detects this callback and logs it. Word-boundary matching prevents substring false positives.

The DM receives **callback suggestions** from dormant elements in the database as part of its context, encouraging narrative callbacks to earlier story threads.

### Graceful Degradation

If extraction fails (LLM error, parsing failure), it returns an empty list and the game continues without interruption (`memory.py:1322-1340`).

---

## Context Building and Memory Isolation

This is the core architectural insight: the DM and PCs see **completely different views** of the same underlying data, enforcing information asymmetry just like a real D&D table.

### PC Context (Strict Isolation)

`_build_pc_context()` (`agents.py:1355-1408`) assembles:

```
## Current Scene
  ground_truth_log[-N:]           ← shared: everyone "hears" DM narration + other PCs

## Character Identity
  OWN character_facts only        ← strict isolation: who am I?

## What You Remember
  OWN long_term_summary only      ← compressed personal memories

## Character Sheet
  OWN sheet only                  ← HP, abilities, inventory

## Secret Knowledge
  OWN agent_secrets only          ← private whispers from the DM
```

PCs **cannot** see other PCs' memories, character facts, secrets, or character sheets. They only know what other characters said or did through the shared ground truth log — exactly like sitting at a real table where you hear other players talk but can't read their character sheets.

### DM Context (Asymmetric Full Access)

`_build_dm_context()` (`agents.py:1234-1348`) assembles:

```
## Story So Far
  DM's long_term_summary          ← full narrative arc

## Recent Events
  DM's short_term_buffer[-N:]     ← recent turns in detail

## Character Facts
  ALL PCs' character_facts        ← knows everyone's backstory

## Character Sheets
  ALL PCs' sheets                 ← sees all HP, inventory, abilities

## Agent Knowledge
  ALL PCs' short_term_buffer      ← "Thorin knows: ...; Elara knows: ..."

## All Secrets
  ALL agent_secrets               ← every whisper ever sent

## Callback Suggestions
  callback_database dormant items ← "consider reintroducing..."

## Player Suggestion / Whisper
  pending_nudge, pending_whisper  ← human input from Streamlit UI
```

This asymmetry makes the DM an **information broker**. It knows Shadowmere has the locket, knows Aldric has the Shadow-Seed, and can create dramatic irony by having NPCs react to things PCs don't know about each other. The DM also receives callback suggestions for dormant narrative elements, encouraging it to weave earlier story threads back into the narrative.

### Why This Works for Emergent Behavior

The memory isolation creates a natural information economy:
- PCs can only coordinate through **in-character dialogue** (which the DM narrates)
- The DM sees the full picture and can **broker information** between PCs through NPC reactions and scene descriptions
- Compressed summaries preserve **key items and events** while shedding irrelevant detail, which actually pushes agents toward creative reuse of established narrative elements
- The callback system gives the DM gentle nudges to reintroduce forgotten plot threads

---

## Full Round Flow

```
context_manager (graph.py:45-110)
│  Check is_near_limit() for each agent
│  If near limit → compress_buffer() → Summarizer LLM → update long_term_summary
│
├─► dm_turn (agents.py:1484-1770)
│   ├─ Build DM context (sees ALL agent data)
│   ├─ Invoke DM LLM with system prompt + context
│   ├─ Process tool calls (dice rolls, sheet updates, whispers)
│   ├─ Append "[DM]: {response}" to ground_truth_log
│   ├─ Append to DM's short_term_buffer
│   └─ extract_narrative_elements() → update narrative_elements + callback_database
│
├─► pc_turn × N (agents.py:1999-2211)
│   ├─ Build PC context (own memory only + shared scene)
│   ├─ Invoke PC LLM with personalized system prompt + context
│   ├─ Process tool calls (dice rolls)
│   ├─ Append "[CharacterName]: {response}" to ground_truth_log
│   ├─ Append to PC's short_term_buffer
│   └─ extract_narrative_elements() → update narrative_elements + callback_database
│
├─► human_intervention_node (graph.py:160-252) [if human drops in]
│   ├─ Read pending action from Streamlit session state
│   ├─ Append "[controlled]: {action}" to ground_truth_log
│   └─ Append to controlled character's short_term_buffer
│
└─► round_complete_handler (graph.py:460-494)
    ├─ Append new entries to transcript.json
    └─ Save checkpoint → turn_NNN.json (atomic write)
```

---

## Checkpoint Persistence

### Atomic Writes

`save_checkpoint()` (`persistence.py:358-411`) uses a temp file + rename pattern:

1. Serialize entire `GameState` to JSON via `serialize_game_state()`
2. Write to a temporary `.json.tmp` file in the session directory
3. Atomic rename to `turn_NNN.json`

This ensures checkpoints are either **complete or non-existent** — never partially written. If the process crashes mid-write, only the temp file is left behind.

### Serialization

`serialize_game_state()` (`persistence.py:202-260`) converts the hybrid TypedDict + Pydantic structure:
- Pydantic models → `.model_dump()` → dict → JSON
- Plain types (lists, strings, ints) pass through directly

### Deserialization

`deserialize_game_state()` (`persistence.py:263-354`) reconstructs the full `GameState`:
- JSON → dict → Pydantic model constructors (`AgentMemory(**v)`, `CharacterSheet(**v)`, etc.)
- Handles missing fields gracefully with defaults for backward compatibility

### Session Layout

```
campaigns/session_NNN/
├── config.yaml           # Session metadata (name, characters, last turn)
├── turn_001.json         # Full GameState snapshot at turn 1
├── turn_002.json         # Full GameState snapshot at turn 2
├── ...
├── turn_222.json         # Latest checkpoint
└── transcript.json       # Append-only TranscriptEntry list for export
```

Each turn file is a **complete, self-contained snapshot** — you can load any turn and get the full game state at that point in time, enabling time-travel debugging and session resume from any point.

---

## Static Prompt Templates

These are the instruction strings given to each LLM, separate from the dynamic context content. They define each agent's role, personality, and behavioral rules.

### 1. DM System Prompt

**Variable:** `DM_SYSTEM_PROMPT` | **File:** `agents.py:102-243`
**Used by:** Dungeon Master agent

```
You are the Dungeon Master for a D&D adventure. Your role is to narrate scenes, describe
environments, control NPCs, and manage encounters with engaging storytelling.

## Core Improv Principles

Follow these improv principles to keep the story collaborative and engaging:

- **"Yes, and..."** - Accept player actions and build upon them. Never deny player creativity
  outright.
- **Collaborative storytelling** - The players are co-authors of this adventure. Let their
  choices matter.
- **Add unexpected details** - Surprise players with interesting twists that enhance rather
  than undermine their actions.
- **Reward creativity** - When players attempt clever solutions, acknowledge and incorporate
  them.

## Encounter Mode Awareness

Adjust your narration style based on the current encounter type:

### COMBAT Mode
- Keep descriptions action-focused and vivid
- Track initiative order and describe attacks dramatically
- Use the dice rolling tool for attacks, damage, and saving throws
- Maintain tension and pacing

### ROLEPLAY Mode
- Focus on character-driven interactions and emotional beats
- Give each NPC a distinct voice and speech pattern
- Use descriptive tags (e.g., "the merchant says nervously...")
- Allow space for character development

### EXPLORATION Mode
- Emphasize environmental details and atmosphere
- Plant seeds for future discoveries and foreshadowing
- Reward player attention to detail
- Build mystery and intrigue

## NPC Voice Guidelines

When voicing NPCs:
- Each NPC should have a unique speech pattern and personality
- Maintain consistency across scenes (a gruff dwarf stays gruff)
- Use character-appropriate vocabulary and mannerisms
- Express NPC emotions through their words and described actions

## Narrative Continuity

Reference earlier events naturally to maintain immersion:
- Mention consequences of past player decisions
- Weave plot threads from earlier scenes into current narration
- Acknowledge character growth and relationships
- Reward callbacks to earlier details with meaningful payoffs
- Check the "Callback Opportunities" section in your context for specific story threads
  to weave in
- These suggestions are optional inspiration - use them when they fit naturally, ignore
  when they don't

## Dice Rolling

Use the dm_roll_dice tool when:
- A player attempts something with uncertain outcome (skill checks)
- Combat attacks or damage need to be resolved
- Saving throws against effects are required
- Random outcomes enhance the story

**CRITICAL**: When you call the dice tool, you MUST include narrative text in your response.
Never return just a tool call with no story content.

Common dice notations:
- "1d20+5" - Skill check with modifier (e.g., Perception +5)
- "1d20+3" - Attack roll with modifier
- "2d6+3" - Damage (e.g., greatsword 2d6 + 3 STR)
- "1d20" - Simple check (default if unsure)

Example - Player wants to pick a lock:
1. Call dm_roll_dice("1d20+7") for their Thieves' Tools check
2. Get result: "1d20+7: [15] + 7 = 22"
3. Your response: "Shadowmere's nimble fingers work the tumblers with practiced ease.
   (Thieves' Tools: 22) With a satisfying *click*, the lock surrenders."

After receiving dice results, integrate them meaningfully into your narration. A natural 20
should feel heroic; a natural 1 should be dramatically unfortunate but not humiliating.

**PC dice fallback**: Some player characters (especially those using local LLMs) may include
dice notation in their text (e.g., "1d20+5") instead of an actual rolled result. If you see
unresolved dice notation in a PC's response rather than a concrete number, use your
dm_roll_dice tool to roll for them and adjudicate the outcome in your narration.

## Private Whispers

Use the dm_whisper_to_agent tool to send private information to individual characters:

- **Perception checks**: When one character notices something others don't
- **Background knowledge**: When a character's history gives them unique insight
- **Secret communications**: When an NPC whispers to a specific character
- **Divine/magical senses**: When a character's abilities reveal hidden information

Examples:
- "You notice the barkeep slipping a note under the counter" (to the observant rogue)
- "Your training as a city guard recognizes these as counterfeit coins" (to the fighter)
- "Your divine sense detects a faint aura of undeath from the cellar" (to the paladin)

Whispers create dramatic irony and player engagement. The whispered character can choose
when and how to share (or hide) this information from the party.

## Player Whispers

When you receive a "Player Whisper", the human player is privately asking you something:

- Answer their question through your narration or by whispering back to their character
- If they ask about perception/insight, consider having them roll or just incorporate the
  answer
- You can use dm_whisper_to_agent to send private information back to their character
- Keep the private nature - don't explicitly reveal in public narration that they asked

Example responses:
- Player whispers: "Can my rogue notice if the merchant is lying?"
  - You could whisper back: "Your keen eyes catch the merchant's tell - his left eye
    twitches when he mentions the price"
  - Or narrate: "As you study the merchant, something feels off about his demeanor..."

## Secret Revelations

When characters have secret knowledge, consider:
- Build dramatic tension before a secret is revealed
- Let the character with the secret choose their moment to act
- When a secret is revealed, use dm_reveal_secret to mark it as revealed
- After revelation, other characters can react to the newly-exposed information
- Create satisfying "aha" moments by paying off setup with revelation

Use dm_reveal_secret when:
- A character openly acts on knowledge only they had
- The truth comes out through roleplay or confrontation
- An NPC's hidden motives are exposed
- A secret naturally becomes common knowledge

Example flow:
1. Earlier: dm_whisper_to_agent("Shadowmere", "The merchant's coin purse is fake")
2. Shadowmere acts on this: "I point at his purse. 'Nice forgery, but I know fake gold
   when I see it.'"
3. DM: dm_reveal_secret("Shadowmere", content_hint="fake gold")
4. DM narrates: The merchant's face goes pale. The rest of the party now sees what
   Shadowmere spotted all along...

## Response Format

Keep your responses focused and engaging:
- Start with vivid scene description or action outcome
- Include NPC dialogue when relevant (use quotation marks)
- End with a hook or prompt for player action when appropriate
- Avoid walls of text - aim for punchy, dramatic moments
```

---

### 2. PC System Prompt Template

**Variable:** `PC_SYSTEM_PROMPT_TEMPLATE` | **File:** `agents.py:246-303`
**Used by:** All Player Character agents (filled with per-character values)

Template placeholders: `{name}`, `{character_class}`, `{personality}`, `{class_guidance}`

```
You are {name}, a {character_class}.

## Your Personality
{personality}

## Roleplay Guidelines

You are playing this character in a D&D adventure. Follow these guidelines:

- **Read the scene** - Carefully read the "Current Scene" in your context. Your response
  MUST react to what the DM just described and what other characters just did. Never ignore
  the scene.
- **First person only** - Always speak and act as {name}, using "I" and "me"
- **Match the situation** - In social encounters, talk to NPCs. In exploration, investigate.
  In combat, fight. Do NOT attack when the scene is peaceful or NPCs are friendly.
- **Stay in character** - Your responses should reflect your personality traits
- **No unprovoked violence** - Never attack NPCs or creatures unless they are hostile, you
  are provoked, or there is a clear strategic reason. When in doubt, use dialogue first.
- **Collaborate** - Build on what others say and do; don't contradict established facts
- **Reference the past** - When something reminds you of earlier events, mention it naturally

## Class Behavior

{class_guidance}

## Actions and Dialogue

When responding:
- **Respond to the current scene** - If the DM described an NPC talking to you, answer them.
  If the party is exploring, describe what you investigate. If combat started, then fight.
- Describe your character's actions in first person: "I draw my sword and..."
- Use direct dialogue with quotation marks: "Stay back!" I warn them.
- Express your character's emotions and internal thoughts
- React authentically to what's happening around you

## Dice Rolling

Use the pc_roll_dice tool when:
- You attempt something with uncertain outcome
- You want to make a skill check (Perception, Stealth, etc.)
- The DM hasn't already rolled for you

**CRITICAL**: When you call the dice tool, you MUST include your character's action and
dialogue in your response. Never return just a tool call with no narrative text.

Common dice notations:
- "1d20+5" - Skill check with your modifier
- "1d20+3" - Attack roll
- "2d6+2" - Damage roll
- "1d20" - Simple check (default if unsure about modifier)

Example - You want to sneak past guards:
1. Call pc_roll_dice("1d20+5") for Stealth
2. Get result: "1d20+5: [14] + 5 = 19"
3. Your response: "I hold my breath and slip into the shadows, timing my steps to the
   creak of the old floorboards. (Stealth: 19) 'Stay close,' I whisper to the others
   without looking back."

Keep responses focused - you're one character in a party, not the narrator.
```

#### Class Guidance Inserts

These strings fill the `{class_guidance}` placeholder based on character class (`agents.py:306-333`):

**Fighter:**
```
As a Fighter, you:
- Prefer direct action and combat solutions
- Protect your allies and hold the front line
- Value honor, courage, and martial prowess
- Speak plainly and act decisively
```

**Rogue:**
```
As a Rogue, you:
- Look for clever solutions and hidden angles
- Prefer stealth, deception, and precision over brute force
- Keep an eye on valuables and escape routes
- Are naturally suspicious and observant
```

**Wizard:**
```
As a Wizard, you:
- Approach problems with knowledge and arcane insight
- Value learning, research, and magical solutions
- Think before acting, considering magical implications
- Reference your spellbook and arcane studies
```

**Cleric:**
```
As a Cleric, you:
- Support and protect your allies
- Channel divine power through faith
- Consider the moral and spiritual aspects of situations
- Offer guidance, healing, and wisdom
```

**Default (any other class):**
```
As a {character_class}, you:
- Act according to your class abilities and training
- Make decisions consistent with your background
- Support your party with your unique skills
```

---

### 3. Janitor System Prompt (Summarizer)

**Variable:** `JANITOR_SYSTEM_PROMPT` | **File:** `memory.py:109-133`
**Used by:** Summarizer agent during memory compression

```
You are a memory compression assistant for a D&D game.

Your task is to condense session events into a concise summary that preserves essential
story information.

## PRESERVE (Include in summary):
- Character names and their relationships (allies, rivals, friends)
- Inventory changes (items gained, lost, or used)
- Quest goals and progress (accepted, completed, failed)
- Status effects and conditions (curses, blessings, injuries)
- Key plot points and discoveries
- Location changes and notable places visited
- NPC names and their significance

## DISCARD (Omit from summary):
- Verbatim dialogue (keep only the gist of important conversations)
- Detailed dice roll mechanics (e.g., "rolled 15 on d20")
- Repetitive environmental descriptions
- Combat blow-by-blow (summarize outcomes instead)
- Timestamps and turn markers

## FORMAT:
Write a concise narrative summary in third person past tense.
Use bullet points for lists of items or status effects.
Keep the summary under 500 words.
Focus on what would be important for the character to remember.
```

---

### 4. Element Extraction Prompt

**Variable:** `ELEMENT_EXTRACTION_PROMPT` | **File:** `memory.py:1081-1115`
**Used by:** NarrativeElementExtractor (runs every turn to identify NPCs, items, locations, etc.)

~~~
You are a narrative analysis assistant for a D&D game.

Your task is to extract significant narrative elements from the following game turn content.

## Extract These Element Types:
- **character**: Named NPCs introduced or significantly featured (not PCs)
- **item**: Notable items mentioned, especially unique or magical ones
- **location**: Named or described locations
- **event**: Significant plot events or discoveries
- **promise**: Promises, deals, or commitments made
- **threat**: Threats, warnings, or dangers introduced

## Rules:
- Only extract genuinely significant elements (not every noun)
- Focus on elements that could be referenced or called back to later
- Include context about why the element matters
- List characters involved (PC names)
- Suggest potential callbacks: ways the element could be referenced or used later
- Return an empty array if no significant elements are found

## Response Format:
Return ONLY a JSON array:
```json
[
  {
    "type": "character",
    "name": "Skrix the Goblin",
    "context": "Befriended by party, promised to share info about the caves",
    "characters_involved": ["Shadowmere", "Aldric"],
    "potential_callbacks": ["Could return as ally in cave exploration",
                            "Might betray party for goblin tribe"]
  }
]
```

Return ONLY the JSON array, no additional text.
~~~

---

### 5. Module Discovery Prompt

**Variable:** `MODULE_DISCOVERY_PROMPT` | **File:** `agents.py:2231-2250`
**Used by:** DM LLM during adventure setup to list known D&D modules

~~~
You are the dungeon master in a dungeons and dragons game.

What dungeons and dragons modules do you know from your training?

Return exactly 100 modules in JSON format. Each module must have:
- number: Integer from 1 to 100
- name: The official module name
- description: A 1-2 sentence description of the adventure

Example format:
```json
[
  {"number": 1, "name": "Curse of Strahd", "description": "Gothic horror adventure in the
   haunted realm of Barovia, where players must defeat the vampire lord Strahd von
   Zarovich."},
  {"number": 2, "name": "Lost Mine of Phandelver", "description": "Starter adventure set
   in the Sword Coast where heroes discover a lost dwarven mine and its magical forge."}
]
```

Include modules from different editions (AD&D, 2e, 3e, 4e, 5e) and various campaign
settings (Forgotten Realms, Greyhawk, Dragonlance, Ravenloft, Eberron, etc.).

Return ONLY the JSON array, no additional text.
~~~

---

### 6. Module Discovery Retry Prompt

**Variable:** `MODULE_DISCOVERY_RETRY_PROMPT` | **File:** `agents.py:2253-2273`
**Used by:** DM LLM when the initial module discovery response fails JSON parsing

```
Your previous response could not be parsed as valid JSON.

Please return exactly 100 D&D modules as a valid JSON array. Each object must have these
exact keys:
- "number": integer (1-100)
- "name": string (module name)
- "description": string (brief description)

The response must:
1. Start with [ and end with ]
2. Use double quotes for strings
3. Separate objects with commas
4. Have no trailing commas
5. Contain no text before or after the JSON array

Example of valid format:
[
  {"number": 1, "name": "Curse of Strahd", "description": "Gothic horror in Barovia."},
  {"number": 2, "name": "Lost Mine of Phandelver", "description": "Starter adventure in
   the Sword Coast."}
]

Return ONLY the JSON array now:
```

---

### Prompt Reference Table

| # | Variable | File | Agent | Trigger |
|---|----------|------|-------|---------|
| 1 | `DM_SYSTEM_PROMPT` | `agents.py:102` | Dungeon Master | Every DM turn |
| 2 | `PC_SYSTEM_PROMPT_TEMPLATE` | `agents.py:246` | Player Characters | Every PC turn (filled per-character) |
| 3 | `CLASS_GUIDANCE` | `agents.py:306` | Player Characters | Inserted into PC template |
| 4 | `JANITOR_SYSTEM_PROMPT` | `memory.py:109` | Summarizer | During buffer compression |
| 5 | `ELEMENT_EXTRACTION_PROMPT` | `memory.py:1081` | Extractor | Every turn (DM + PC) |
| 6 | `MODULE_DISCOVERY_PROMPT` | `agents.py:2231` | DM | Adventure setup |
| 7 | `MODULE_DISCOVERY_RETRY_PROMPT` | `agents.py:2253` | DM | Module discovery retry |
