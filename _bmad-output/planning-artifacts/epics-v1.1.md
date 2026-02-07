# autodungeon v1.1 - Enhancement Epics

## Overview

This document provides the epic and story breakdown for autodungeon v1.1 enhancements, building on the completed MVP (Epics 1-6).

**Summary:** 6 New Epics, 24 Stories

## New Functional Requirements

**Module Selection (FR56-FR59):**

- FR56: System can query DM LLM for known D&D modules from training data
- FR57: User can browse and select from available modules
- FR58: User can select a random module
- FR59: Selected module context is injected into DM system prompt

**Character Sheets (FR60-FR66):**

- FR60: Each character has a complete D&D 5e character sheet
- FR61: Character sheets are viewable in the UI
- FR62: Character sheet data is included in agent context (DM sees all, PC sees own)
- FR63: DM can update character sheets via tool calls
- FR64: Sheet changes are reflected in the narrative
- FR65: Character sheets persist across sessions
- FR66: Character sheets include: abilities, skills, HP, AC, equipment, spells, personality

**Character Creation (FR67-FR70):**

- FR67: User can create new characters via a wizard UI
- FR68: System can assist with backstory generation
- FR69: Created characters are validated for D&D 5e rules
- FR70: Characters can be saved to a library for reuse

**DM Whisper System (FR71-FR75):**

- FR71: DM can send private information to individual agents
- FR72: Whispered information only appears in recipient's context
- FR73: Human can whisper to DM (extends existing nudge)
- FR74: Secrets can be revealed dramatically in narrative
- FR75: Whisper history is tracked per agent

**Callback Tracker (FR76-FR80):**

- FR76: System can extract significant narrative elements
- FR77: Narrative elements are stored with context (who, what, when)
- FR78: DM context includes callback suggestions
- FR79: System can detect when callbacks occur
- FR80: User can view tracked elements and callback history

**Fork Gameplay (FR81-FR84):**

- FR81: User can create a fork (branch point) from current state
- FR82: User can view and switch between forks
- FR83: User can compare narrative divergence between forks
- FR84: User can merge or abandon forks

## Epic List

| Epic | Title | Stories | FRs |
|------|-------|---------|-----|
| 7 | Module Selection & Campaign Setup | 4 | 4 |
| 8 | Character Sheets | 5 | 7 |
| 9 | Character Creation UI | 4 | 4 |
| 10 | DM Whisper & Secrets System | 5 | 5 |
| 11 | Callback Tracker | 5 | 5 |
| 12 | Fork Gameplay | 4 | 4 |
| **Total** | | **27** | **29** |

---

## Epic 7: Module Selection & Campaign Setup

**Goal:** User can start a new adventure by selecting from D&D modules the DM knows from training.

**User Outcome:** "I ask the DM what adventures it knows, pick 'Curse of Strahd' from the list, and the DM starts running that campaign with full knowledge of the setting."

**FRs Covered:** FR56-FR59 (4 FRs)

---

### Story 7.1: Module Discovery via LLM Query

As a **user starting a new adventure**,
I want **to ask the DM LLM what D&D modules it knows**,
So that **I can choose from adventures the AI can run authentically**.

**Acceptance Criteria:**

**Given** the user clicks "New Adventure"
**When** the module discovery phase begins
**Then** the system queries the DM LLM with: "You are the dungeon master in a dungeons and dragons game. What dungeons and dragons modules do you know from your training?"

**Given** the LLM query
**When** requesting modules
**Then** the prompt requests exactly 100 modules in JSON format with: number, name, description

**Given** the LLM response
**When** parsed
**Then** each module has:
```json
{
  "number": 1,
  "name": "Curse of Strahd",
  "description": "Gothic horror adventure in the haunted realm of Barovia..."
}
```

**Given** the module list is retrieved
**When** cached
**Then** it's stored in session state for the duration of adventure creation

**Given** the LLM fails to return valid JSON
**When** parsing fails
**Then** the system retries with a more explicit JSON schema instruction

---

### Story 7.2: Module Selection UI

As a **user**,
I want **to browse and select from available modules**,
So that **I can choose an adventure that interests me**.

**Acceptance Criteria:**

**Given** the module list is loaded
**When** displayed in the UI
**Then** I see a searchable/filterable grid of module cards

**Given** each module card
**When** displayed
**Then** it shows: name, brief description, and a "Select" button

**Given** the module list
**When** I type in a search box
**Then** modules are filtered by name and description text

**Given** the module selection UI
**When** I want a surprise
**Then** I can click "Random Module" to select one randomly

**Given** I select a module
**When** confirming selection
**Then** the module name and description are shown for confirmation
**And** I can proceed to party setup or go back to choose another

---

### Story 7.3: Module Context Injection

As a **DM agent**,
I want **the selected module to be part of my system prompt**,
So that **I can run the adventure with knowledge of setting, NPCs, and plot**.

**Acceptance Criteria:**

**Given** a module has been selected
**When** the DM agent is initialized
**Then** the module context is injected into the DM system prompt

**Given** the module context injection
**When** building the DM prompt
**Then** it includes:
```
## Campaign Module: [Module Name]
[Module Description]

You are running this official D&D module. Draw upon your knowledge of:
- The setting, locations, and atmosphere
- Key NPCs, their motivations, and personalities
- The main plot hooks and story beats
- Encounters, monsters, and challenges appropriate to this module
```

**Given** the DM generates responses
**When** running the selected module
**Then** responses reflect knowledge of that specific adventure

**Given** the module context
**When** persisted
**Then** it's saved with the campaign config for session continuity

---

### Story 7.4: New Adventure Flow Integration

As a **user**,
I want **module selection integrated into the new adventure flow**,
So that **starting a new game is a smooth, guided experience**.

**Acceptance Criteria:**

**Given** I click "New Adventure" on the home screen
**When** the creation flow starts
**Then** the steps are:
1. Module Selection (new)
2. Party Setup (existing)
3. Adventure Begins

**Given** the module selection step
**When** modules are loading
**Then** a loading indicator shows "Consulting the Dungeon Master's Library..."

**Given** I complete module selection
**When** proceeding to party setup
**Then** the selected module is displayed in a header/banner

**Given** the full adventure creation completes
**When** the game starts
**Then** the DM's opening narration reflects the selected module's setting

**Given** I want to skip module selection
**When** offered the option
**Then** I can choose "Freeform Adventure" for an unstructured campaign

---

## Epic 8: Character Sheets

**Goal:** Each character has a full D&D 5e character sheet that's viewable and dynamically updated.

**User Outcome:** "I can click on any character and see their full sheet - HP, abilities, equipment, spells. When the fighter takes damage, their HP updates. When the rogue finds a magic dagger, it appears in their inventory."

**FRs Covered:** FR60-FR66 (7 FRs)

---

### Story 8.1: Character Sheet Data Model

As a **developer**,
I want **a comprehensive Pydantic model for D&D 5e character sheets**,
So that **all character data is validated, serializable, and type-safe**.

**Acceptance Criteria:**

**Given** the models.py module
**When** I import CharacterSheet
**Then** it includes all D&D 5e character sheet fields:

```python
class CharacterSheet(BaseModel):
    # Basic Info
    name: str
    race: str
    character_class: str
    level: int = 1
    background: str
    alignment: str
    experience_points: int = 0

    # Ability Scores (score and modifier calculated)
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int

    # Combat Stats
    armor_class: int
    initiative: int
    speed: int
    hit_points_max: int
    hit_points_current: int
    hit_points_temp: int = 0
    hit_dice: str  # e.g., "1d10"
    hit_dice_remaining: int

    # Saving Throws (proficiency flags)
    saving_throw_proficiencies: list[str]

    # Skills (proficiency and expertise flags)
    skill_proficiencies: list[str]
    skill_expertise: list[str] = []

    # Proficiencies
    armor_proficiencies: list[str]
    weapon_proficiencies: list[str]
    tool_proficiencies: list[str]
    languages: list[str]

    # Features & Traits
    class_features: list[str]
    racial_traits: list[str]
    feats: list[str] = []

    # Equipment & Inventory
    weapons: list[Weapon]
    armor: Optional[Armor]
    equipment: list[EquipmentItem]
    gold: int = 0
    silver: int = 0
    copper: int = 0

    # Spellcasting (if applicable)
    spellcasting_ability: Optional[str]
    spell_save_dc: Optional[int]
    spell_attack_bonus: Optional[int]
    cantrips: list[str] = []
    spells_known: list[Spell] = []
    spell_slots: dict[int, SpellSlots] = {}  # level -> {max, current}

    # Personality
    personality_traits: str
    ideals: str
    bonds: str
    flaws: str
    backstory: str

    # Conditions & Status
    conditions: list[str] = []  # poisoned, exhausted, etc.
    death_saves: DeathSaves = DeathSaves()
```

**Given** the CharacterSheet model
**When** serialized
**Then** it can be converted to/from JSON for persistence

**Given** ability scores
**When** accessing modifiers
**Then** computed properties return the modifier: `(score - 10) // 2`

**Given** proficiency bonus
**When** calculated
**Then** it's derived from level per D&D 5e rules

---

### Story 8.2: Character Sheet Viewer UI

As a **user**,
I want **to view any character's full sheet in the UI**,
So that **I can see their stats, abilities, and inventory at any time**.

**Acceptance Criteria:**

**Given** the party panel in the sidebar
**When** I click on a character's name (not Drop-In button)
**Then** a character sheet modal/panel opens

**Given** the character sheet viewer
**When** displayed
**Then** it shows organized sections:
- Header: Name, Race, Class, Level
- Abilities: Six ability scores with modifiers
- Combat: AC, HP bar, Initiative, Speed
- Skills: All 18 skills with proficiency indicators
- Equipment: Weapons, armor, inventory
- Spells (if caster): Cantrips, prepared spells, spell slots
- Features: Class features, racial traits
- Personality: Traits, ideals, bonds, flaws

**Given** the HP display
**When** current HP is below max
**Then** a visual bar shows remaining HP with color coding (green/yellow/red)

**Given** spell slots
**When** displayed
**Then** each level shows filled/empty dots for used/available slots

**Given** the character sheet
**When** viewing during an active game
**Then** it shows real-time values (HP changes, spell slot usage, etc.)

---

### Story 8.3: Character Sheet Context Injection

As an **agent (DM or PC)**,
I want **character sheet data in my context**,
So that **I can make decisions based on actual character capabilities**.

**Acceptance Criteria:**

**Given** a PC agent
**When** building their prompt context
**Then** their own character sheet is included in a readable format

**Given** the DM agent
**When** building their prompt context
**Then** ALL party character sheets are included (DM sees all)

**Given** the character sheet context
**When** formatted for prompts
**Then** it's concise but complete:
```
## Your Character Sheet: Thorin, Dwarf Fighter (Level 5)
HP: 45/52 | AC: 18 | Speed: 25ft

STR: 18 (+4) | DEX: 12 (+1) | CON: 16 (+3)
INT: 10 (+0) | WIS: 14 (+2) | CHA: 8 (-1)

Proficiencies: All armor, shields, simple/martial weapons
Skills: Athletics (+7), Intimidation (+2), Perception (+5)

Equipment: Longsword (+7, 1d8+4), Shield, Chain Mail
Inventory: 50ft rope, torches (5), rations (3 days), 47 gold

Features: Second Wind, Action Surge, Extra Attack
Conditions: None
```

**Given** a PC agent with spellcasting
**When** their context includes spells
**Then** available spell slots and prepared spells are listed

---

### Story 8.4: DM Tool Calls for Sheet Updates

As a **DM agent**,
I want **tool calls to update character sheets**,
So that **game mechanics are reflected in character data**.

**Acceptance Criteria:**

**Given** the tools.py module
**When** I examine DM tools
**Then** there's an `update_character_sheet()` function

**Given** the update_character_sheet tool
**When** called
**Then** it accepts:
```python
def update_character_sheet(
    character_name: str,
    updates: dict[str, Any]
) -> str:
    """
    Update a character's sheet.

    Examples:
    - {"hit_points_current": 35}  # Take damage
    - {"gold": 100, "equipment": ["+Potion of Healing"]}  # Loot
    - {"conditions": ["+poisoned"]}  # Add condition
    - {"spell_slots": {"1": {"current": 2}}}  # Use spell slot
    """
```

**Given** the DM narrates damage
**When** processing the turn
**Then** the DM calls `update_character_sheet("Thorin", {"hit_points_current": 35})`

**Given** equipment changes (loot, loss, purchase)
**When** the DM narrates them
**Then** the tool updates the equipment list

**Given** spell slot usage
**When** a caster uses a spell
**Then** the DM updates remaining slots

**Given** an invalid update
**When** the tool is called
**Then** it returns an error message and the sheet remains unchanged

---

### Story 8.5: Sheet Change Notifications

As a **user**,
I want **to see when character sheets change**,
So that **I know when someone takes damage, gains loot, or levels up**.

**Acceptance Criteria:**

**Given** a character sheet update occurs
**When** the change is significant (HP, conditions, equipment)
**Then** a subtle notification appears in the UI

**Given** HP changes
**When** displayed
**Then** the notification shows: "Thorin: 52 HP → 35 HP (-17)"

**Given** equipment changes
**When** an item is gained
**Then** the notification shows: "Shadowmere gained: Dagger +1"

**Given** condition changes
**When** a condition is added/removed
**Then** the notification shows: "Elara is now poisoned" or "Aldric is no longer frightened"

**Given** the narrative area
**When** sheet changes occur
**Then** they can optionally be woven into the narrative display

**Given** the character sheet viewer
**When** open during changes
**Then** it updates in real-time with highlighted changes

---

## Epic 9: Character Creation UI

**Goal:** User can create new characters through a guided wizard interface.

**User Outcome:** "I click 'Create Character', walk through choosing race, class, and abilities, get help writing a backstory, and have a ready-to-play character saved to my library."

**FRs Covered:** FR67-FR70 (4 FRs)

---

### Story 9.1: Character Creation Wizard

As a **user**,
I want **a step-by-step wizard to create new characters**,
So that **I can build valid D&D characters without knowing all the rules**.

**Acceptance Criteria:**

**Given** I access character creation (from party setup or library)
**When** the wizard starts
**Then** I see a multi-step form with progress indicator

**Given** the wizard steps
**When** progressing through
**Then** the steps are:
1. Basics: Name, Race, Class
2. Abilities: Point buy or standard array
3. Background: Select background, get proficiencies
4. Equipment: Starting equipment choices
5. Personality: Traits, ideals, bonds, flaws
6. Review: Complete sheet preview

**Given** step 1 (Basics)
**When** selecting race and class
**Then** dropdowns show all standard D&D 5e options with brief descriptions

**Given** step 2 (Abilities)
**When** assigning scores
**Then** point-buy calculator shows remaining points
**Or** standard array (15,14,13,12,10,8) can be assigned

**Given** step 3 (Background)
**When** selecting a background
**Then** associated proficiencies and equipment are auto-added

**Given** any step
**When** I want to go back
**Then** I can navigate to previous steps without losing data

---

### Story 9.2: AI-Assisted Backstory Generation

As a **user**,
I want **AI help writing my character's backstory**,
So that **I can have a rich history even if I'm not a creative writer**.

**Acceptance Criteria:**

**Given** the personality/backstory step
**When** I click "Generate with AI"
**Then** the LLM creates personality traits based on race, class, and background

**Given** the AI generation
**When** it runs
**Then** it produces:
- 2 personality traits
- 1 ideal (aligned with background)
- 1 bond (story hook)
- 1 flaw (interesting weakness)
- 2-3 paragraph backstory

**Given** the generated content
**When** displayed
**Then** I can edit any part before accepting

**Given** I don't like the generation
**When** I click "Regenerate"
**Then** new content is generated with the same inputs

**Given** I prefer to write manually
**When** I skip AI generation
**Then** I can fill in all fields by hand

---

### Story 9.3: Character Validation

As a **system**,
I want **to validate created characters against D&D 5e rules**,
So that **characters are mechanically correct**.

**Acceptance Criteria:**

**Given** a character is being created
**When** moving between steps
**Then** validation runs on completed sections

**Given** ability scores
**When** using point buy
**Then** total points cannot exceed the budget (27 standard)

**Given** class/race combinations
**When** selected
**Then** any restrictions are shown (e.g., some races have stat bonuses)

**Given** proficiency selections
**When** exceeding allowed count
**Then** an error prevents proceeding

**Given** the review step
**When** displayed
**Then** a validation summary shows any issues or warnings

**Given** all validation passes
**When** I click "Create Character"
**Then** the character is saved with a complete, valid sheet

---

### Story 9.4: Character Library

As a **user**,
I want **to save created characters to a library**,
So that **I can reuse them in different campaigns**.

**Acceptance Criteria:**

**Given** a character is created
**When** saved
**Then** it's stored in `config/characters/library/[name].yaml`

**Given** the character library
**When** accessed from party setup
**Then** I see all saved characters with quick stats

**Given** a library character
**When** adding to a party
**Then** a copy is made (original preserved for other campaigns)

**Given** the library view
**When** managing characters
**Then** I can: view, edit, duplicate, or delete characters

**Given** the party setup flow
**When** creating a party
**Then** I can mix library characters with preset characters

---

## Epic 10: DM Whisper & Secrets System

**Goal:** DM can send private information to individual agents, enabling dramatic secrets.

**User Outcome:** "The DM secretly tells the rogue there's a hidden door. Only the rogue knows. When she 'discovers' it, it feels like real discovery to everyone else."

**FRs Covered:** FR71-FR75 (5 FRs)

---

### Story 10.1: Whisper Data Model

As a **developer**,
I want **a data model for private whispers between DM and agents**,
So that **secrets can be tracked and managed**.

**Acceptance Criteria:**

**Given** the models.py module
**When** I import Whisper and WhisperHistory
**Then** they define:
```python
class Whisper(BaseModel):
    id: str
    from_agent: str  # "dm" or "human"
    to_agent: str    # character name
    content: str
    turn_created: int
    revealed: bool = False
    turn_revealed: Optional[int] = None

class AgentSecrets(BaseModel):
    whispers: list[Whisper] = []

    def active_whispers(self) -> list[Whisper]:
        return [w for w in self.whispers if not w.revealed]
```

**Given** the GameState
**When** extended
**Then** it includes `agent_secrets: dict[str, AgentSecrets]`

**Given** whispers
**When** serialized with checkpoints
**Then** they persist and can be restored

---

### Story 10.2: DM Whisper Tool

As a **DM agent**,
I want **a tool to send private information to individual characters**,
So that **I can create dramatic irony and secrets**.

**Acceptance Criteria:**

**Given** the tools.py module
**When** I examine DM tools
**Then** there's a `whisper_to_agent()` function

**Given** the whisper tool
**When** called by DM
**Then** it accepts:
```python
def whisper_to_agent(
    character_name: str,
    secret_info: str,
    context: str = ""  # When/why this becomes relevant
) -> str:
    """Send private information to a character that others don't know."""
```

**Given** the DM wants to create a secret
**When** generating a response
**Then** it can call: `whisper_to_agent("Shadowmere", "You notice a concealed door behind the tapestry")`

**Given** a whisper is sent
**When** confirmed
**Then** the tool returns: "Secret shared with Shadowmere"

**Given** the whisper system prompt
**When** DM is initialized
**Then** it includes guidance on using whispers for dramatic effect

---

### Story 10.3: Secret Knowledge Injection

As a **PC agent**,
I want **my secret whispers included in my context**,
So that **I can act on information others don't have**.

**Acceptance Criteria:**

**Given** a PC agent with active whispers
**When** building their prompt context
**Then** whispers are included in a "Secret Knowledge" section

**Given** the secret knowledge section
**When** formatted
**Then** it appears as:
```
## Secret Knowledge (Only You Know This)
- [Turn 15] You noticed a concealed door behind the tapestry in the throne room.
- [Turn 22] The merchant whispered that the baron is actually a vampire.
```

**Given** another PC agent without those whispers
**When** their context is built
**Then** they do NOT see those secrets

**Given** the DM agent
**When** building context
**Then** the DM sees ALL whispers (knows all secrets)

**Given** a PC with secret knowledge
**When** generating responses
**Then** they can choose when/how to reveal or act on secrets

---

### Story 10.4: Human Whisper to DM

As a **human player**,
I want **to whisper privately to the DM**,
So that **I can suggest secrets or ask for private information**.

**Acceptance Criteria:**

**Given** the existing nudge system
**When** extended
**Then** there's a "Whisper to DM" option separate from nudge

**Given** the whisper input
**When** I type a message
**Then** it's marked as private and only the DM sees it

**Given** a human whisper
**When** sent
**Then** it appears in the DM's context as:
```
## Player Whisper
The human player privately asks: "Can my rogue notice if the merchant is lying?"
```

**Given** the DM processes a human whisper
**When** responding
**Then** it may whisper back information or incorporate it into narrative

**Given** human whispers
**When** logged
**Then** they're tracked in the whisper history but not in public transcript

---

### Story 10.5: Secret Revelation System

As a **user watching the game**,
I want **dramatic moments when secrets are revealed**,
So that **the story has satisfying reveals and twists**.

**Acceptance Criteria:**

**Given** a character acts on secret knowledge
**When** the action reveals the secret
**Then** the system can mark the whisper as "revealed"

**Given** a secret is revealed
**When** the DM narrates
**Then** other characters can now react to the revealed information

**Given** the reveal moment
**When** displayed in UI
**Then** a subtle indicator shows "Secret Revealed" for drama

**Given** the whisper history
**When** viewed (debug/review mode)
**Then** revealed vs unrevealed secrets are distinguished

**Given** the DM's dramatic timing
**When** secrets exist
**Then** the DM prompt encourages building tension before reveals

---

## Epic 11: Callback Tracker (Chekhov's Gun)

**Goal:** Track narrative elements for potential callbacks, helping create a coherent, interwoven story.

**User Outcome:** "The wizard mentions an old mentor in session 1. Ten sessions later, that mentor shows up as an NPC. The system helped the DM remember and use that earlier detail."

**FRs Covered:** FR76-FR80 (5 FRs)

---

### Story 11.1: Narrative Element Extraction

As a **system**,
I want **to extract significant narrative elements from each turn**,
So that **potential callback material is identified and stored**.

**Acceptance Criteria:**

**Given** each turn's content
**When** processed
**Then** an LLM extracts notable elements:
- Named NPCs introduced
- Locations described
- Items mentioned (especially unique ones)
- Plot hooks or unresolved threads
- Character backstory references
- Promises or threats made

**Given** the extraction prompt
**When** run after each DM turn
**Then** it returns structured data:
```json
{
  "elements": [
    {
      "type": "npc",
      "name": "Skrix the Goblin",
      "context": "Befriended by party, promised to share info about the caves",
      "characters_involved": ["Shadowmere", "Aldric"]
    }
  ]
}
```

**Given** the extraction
**When** run
**Then** it's lightweight (fast model) to not slow down gameplay

---

### Story 11.2: Callback Database

As a **system**,
I want **to store narrative elements with full context**,
So that **they can be surfaced for callbacks later**.

**Acceptance Criteria:**

**Given** extracted narrative elements
**When** stored
**Then** each element has:
```python
class NarrativeElement(BaseModel):
    id: str
    element_type: str  # npc, location, item, plot_hook, backstory
    name: str
    description: str
    turn_introduced: int
    session_introduced: int
    characters_involved: list[str]
    times_referenced: int = 1
    last_referenced_turn: int
    potential_callbacks: list[str] = []  # AI-suggested uses
```

**Given** the callback database
**When** persisted
**Then** it's saved with the campaign (not just session)

**Given** elements are referenced again
**When** detected
**Then** `times_referenced` increments and `last_referenced_turn` updates

**Given** the database grows
**When** elements haven't been referenced in 20+ turns
**Then** they're marked as "dormant" (still available but lower priority)

---

### Story 11.3: DM Callback Suggestions

As a **DM agent**,
I want **suggestions for callbacks in my context**,
So that **I can weave earlier story threads into current narrative**.

**Acceptance Criteria:**

**Given** the DM's prompt context
**When** built
**Then** a "Callback Opportunities" section is included

**Given** callback suggestions
**When** formatted
**Then** they appear as:
```
## Callback Opportunities
Consider weaving in these earlier story elements:

1. **Skrix the Goblin** (Turn 15, Session 2)
   The party befriended this goblin who promised cave information.
   Potential use: He could appear with the promised info, or be in danger.

2. **The Broken Amulet** (Turn 42, Session 3)
   Elara found half an amulet. The other half's location is unknown.
   Potential use: A merchant could have the other half.
```

**Given** callback suggestions
**When** selected
**Then** they prioritize:
- High relevance to current scene
- Longer time since last reference (more impactful callback)
- Character involvement (if that character is active)

**Given** the DM uses a callback
**When** generating response
**Then** it doesn't have to use suggestions (just inspiration)

---

### Story 11.4: Callback Detection

As a **system**,
I want **to detect when callbacks occur**,
So that **the story's interconnectedness can be tracked and celebrated**.

**Acceptance Criteria:**

**Given** a turn's content
**When** it references a stored narrative element
**Then** the system detects the callback

**Given** callback detection
**When** running
**Then** it uses fuzzy matching on:
- Named entities (NPCs, locations, items)
- Semantic similarity to stored element descriptions

**Given** a callback is detected
**When** confirmed
**Then** the element's reference count increments
**And** the callback is logged with context

**Given** the callback log
**When** maintained
**Then** it tracks: element, turn used, how it was referenced

**Given** a particularly good callback (20+ turns gap)
**When** detected
**Then** it's flagged as a "story moment" for research metrics

---

### Story 11.5: Callback UI & History

As a **user**,
I want **to view tracked narrative elements and callback history**,
So that **I can appreciate the story's interconnections**.

**Acceptance Criteria:**

**Given** the sidebar or a dedicated panel
**When** I access "Story Threads"
**Then** I see a list of tracked narrative elements

**Given** the element list
**When** displayed
**Then** each shows: name, type, turn introduced, times referenced

**Given** I click on an element
**When** expanding details
**Then** I see: full description, callback history, original context

**Given** elements with callbacks
**When** displayed
**Then** they show a "referenced X times" badge

**Given** the callback history
**When** viewed
**Then** it shows a timeline of when elements were introduced and referenced

**Given** dormant elements
**When** displayed
**Then** they're visually distinct (grayed out) but still accessible

---

## Epic 12: Fork Gameplay

**Goal:** User can branch the story to explore "what if" scenarios without losing the main timeline.

**User Outcome:** "The party is about to fight the dragon. I create a fork, try diplomacy in the fork, see how it plays out, then go back to my main timeline and fight."

**FRs Covered:** FR81-FR84 (4 FRs)

---

### Story 12.1: Fork Creation

As a **user**,
I want **to create a fork (branch point) from the current game state**,
So that **I can explore alternate story paths**.

**Acceptance Criteria:**

**Given** an active game session
**When** I click "Create Fork"
**Then** the current state is saved as a branch point

**Given** the fork creation
**When** prompted
**Then** I can name the fork (e.g., "Diplomacy attempt", "Fight the dragon")

**Given** a fork is created
**When** confirmed
**Then** it creates a new session directory: `campaigns/session_001/forks/fork_001/`
**And** copies the current checkpoint as the fork's starting point

**Given** I continue playing after creating a fork
**When** generating turns
**Then** the main timeline continues normally
**And** the fork is available to switch to

**Given** multiple forks
**When** created from the same point
**Then** each is tracked independently

---

### Story 12.2: Fork Management UI

As a **user**,
I want **to view, switch between, and manage forks**,
So that **I can explore multiple storylines**.

**Acceptance Criteria:**

**Given** the session has forks
**When** viewing the Session History panel
**Then** forks are shown as branches off the main timeline

**Given** the fork list
**When** displayed
**Then** each fork shows: name, turn created, current turn, last played

**Given** I want to play a fork
**When** I click "Switch to Fork"
**Then** the game state loads from that fork's latest checkpoint
**And** the mode indicator shows "Fork: [Fork Name]"

**Given** I'm playing in a fork
**When** I want to return to main timeline
**Then** I can click "Return to Main"
**And** the fork's progress is saved

**Given** fork management
**When** I right-click or access options
**Then** I can: Rename, Delete, or "Make Primary" (promote fork to main)

---

### Story 12.3: Fork Comparison View

As a **user**,
I want **to compare how forks diverged from the branch point**,
So that **I can see the consequences of different choices**.

**Acceptance Criteria:**

**Given** multiple forks from the same point
**When** I access "Compare Forks"
**Then** a side-by-side view shows divergent narratives

**Given** the comparison view
**When** displayed
**Then** it shows:
- Branch point (common starting turn)
- Parallel columns for each fork's subsequent turns
- Highlighted differences in outcomes

**Given** the comparison
**When** scrolling
**Then** turns are aligned by sequence number for easy comparison

**Given** a fork that's significantly longer
**When** compared to a shorter one
**Then** the shorter one shows "[Fork ends here]" with summary

**Given** the comparison view
**When** reading
**Then** I can click any turn to expand full details

---

### Story 12.4: Fork Resolution

As a **user**,
I want **to merge or abandon forks**,
So that **I can choose my canonical timeline**.

**Acceptance Criteria:**

**Given** I've explored a fork
**When** I decide it's the "true" path
**Then** I can "Promote to Main" which makes it the primary timeline

**Given** promoting a fork
**When** confirmed
**Then** the old main timeline becomes a fork (preserved, not deleted)
**And** the promoted fork becomes the new main

**Given** I don't want a fork anymore
**When** I choose to abandon it
**Then** a confirmation asks "Delete this alternate timeline?"
**And** deletion removes the fork's checkpoint files

**Given** merging is not practical (story diverged too much)
**When** I want to incorporate ideas
**Then** I can view the fork while playing main (read-only reference)

**Given** all forks
**When** the campaign ends or I want to clean up
**Then** I can "Collapse to Single Timeline" to keep only main

---

## Implementation Priority

**Recommended Order:**

1. **Epic 7** (Module Selection) - Better game start experience
2. **Epic 8** (Character Sheets) - Foundation for mechanics
3. **Epic 10** (DM Whisper) - Immediate gameplay enhancement
4. **Epic 9** (Character Creation) - Improved onboarding
5. **Epic 11** (Callback Tracker) - Research value + narrative quality
6. **Epic 12** (Fork Gameplay) - Advanced feature, builds on checkpoints

---

## File Summary

| File | Changes |
|------|---------|
| `models.py` | CharacterSheet, Whisper, NarrativeElement, Fork models |
| `tools.py` | update_character_sheet(), whisper_to_agent() |
| `agents.py` | Module context injection, character sheet context |
| `memory.py` | Whisper context injection, callback suggestions |
| `persistence.py` | Fork management, callback database |
| `app.py` | Module selection UI, character sheet viewer, fork UI, whisper UI |
| `config/` | Character library storage |
