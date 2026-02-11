# Sprint Change Proposal: Combat Initiative Turn Ordering

**Date:** 2026-02-10
**Triggered by:** Live gameplay observation during Session IV (Lost Mine of Phandelver)
**Scope:** Moderate - New epic with architecture and game engine changes
**Risk:** Medium

## Section 1: Issue Summary

During live monitoring of a fresh game session, combat encounters were observed where the DM narratively determines initiative order (rolling dice for each combatant), but **PCs always act in fixed alphabetical order** regardless of initiative results. The turn queue is hardcoded at session start as `["dm"] + sorted(characters.keys())` and never reorders.

In D&D, combat initiative determines the order in which characters and monsters act each round. This is a core mechanic that affects:
- **Tactical decisions** - Knowing when you act relative to enemies matters
- **Narrative tension** - A rogue going first to disarm a trap vs. going last after it triggers
- **DM encounter design** - Monsters interleaved with PCs, not always acting as a block

Currently, NPCs/monsters have no explicit "turn" in the queue. The DM narrates their actions as part of the DM's own turn, which works for narrative mode but doesn't support tactical combat where a goblin might act between two PCs.

### Evidence

From the game logs:
- DM rolls initiative (e.g., `DM rolled dice: {'notation': '1d20+4'}`) but results are cosmetic
- Turn order is always: DM -> Brother Aldric -> Elara -> Shadowmere -> Thorin (alphabetical)
- `route_to_next_agent()` in graph.py simply advances through the fixed `turn_queue` list
- `combat_mode` field exists in `GameConfig` but is never referenced in any logic
- `CharacterSheet.initiative` modifier is calculated but only displayed in the UI

## Section 2: Impact Analysis

### Epic Impact

All 14 existing epics are **done** and unaffected. This requires a **new Epic 15: Combat Initiative System**.

### Story Impact

No existing stories need modification. New stories are needed:

| Story | Description | Complexity |
|-------|-------------|------------|
| 15-1 | Combat State Model & Detection | Medium |
| 15-2 | Initiative Rolling & Turn Reordering | Medium |
| 15-3 | Combat-Aware Graph Routing | High |
| 15-4 | NPC/Monster Turns in Initiative | Medium |
| 15-5 | Combat UI Indicators (optional) | Low |
| 15-6 | Combat End Conditions & TPK Handling | Medium |

### Artifact Conflicts

| Artifact | Impact | Action Needed |
|----------|--------|---------------|
| **PRD** | No conflict. FR8 enhanced. | Add FR56: Combat initiative ordering |
| **Architecture** | `route_to_next_agent()` needs combat branch | Update routing section |
| **Models** | GameState needs combat tracking fields | Add combat state fields |
| **Graph** | Routing logic needs combat-aware path | Modify conditional edges |
| **Agents** | DM needs combat start/end detection | Enhance DM system prompt + tools |
| **UI** | Optional initiative order display | Nice-to-have enhancement |

### Technical Impact

**Files requiring changes:**

| File | Change | Risk |
|------|--------|------|
| `models.py` | Add `CombatState` model, new GameState fields | Low |
| `graph.py` | Combat-aware `route_to_next_agent()` | **High** - Core routing |
| `agents.py` | DM combat detection, NPC turn handling | Medium |
| `tools.py` | Initiative rolling tool, combat start/end tools | Low |
| `app.py` | Optional: initiative order display in party panel | Low |
| `persistence.py` | Serialize new combat state fields | Low |

## Section 3: Recommended Approach

### Selected: Direct Adjustment - New Epic 15

**Rationale:** This is a feature enhancement, not a bug fix. The existing turn system works correctly for exploration and roleplay. Combat-specific ordering is purely additive and can be gated behind the existing `combat_mode` GameConfig field.

### Design Considerations

This requires careful architectural thinking because of several competing concerns:

#### A. When does combat start/end?

**Option A1: DM Tool-Based (Recommended)**
- DM calls `start_combat(participants=[...])` tool when narrating combat start
- DM calls `end_combat()` tool when combat concludes
- Pro: DM has full control, matches D&D convention
- Con: Requires reliable tool calling from LLM

**Option A2: Automatic Detection**
- Heuristic-based: detect combat keywords in DM narration
- Pro: No tool calling needed
- Con: Unreliable, false positives/negatives

**Option A3: Hybrid**
- DM uses tools, but system can suggest combat start via prompt injection
- Best of both worlds but more complex

#### B. How are NPC/Monster turns handled?

**Option B1: DM Acts for Each NPC Individually at Initiative Position (Recommended)**
- Initiative order includes NPC entries interleaved with PCs (e.g., `["dm", "dm:goblin_1", "shadowmere", "dm:goblin_2", "thorin", "brother_aldric", "elara"]`)
- The `"dm"` entry at the start is a **bookend turn** where the DM sets the scene, summarizes the previous round, and describes the environment
- Each `"dm:npc_name"` entry is a separate DM call where the DM acts for that specific NPC/monster
- Pro: Strict D&D initiative ordering, PCs can react to individual NPC actions, faithful tactical feel
- Con: Multiple DM calls per round (adds ~20s per NPC: LLM + extractor)

**Option B2: DM Narrates All NPCs in One Turn** *(rejected)*
- DM gets one turn per round, handles all NPC actions at once
- Pro: Fewer LLM calls, simpler
- Con: Doesn't respect initiative order for monsters interleaved with PCs

**Option B3: DM Batch at Highest NPC Initiative** *(rejected)*
- DM gets one turn at the highest-rolling NPC's initiative position
- Con: PCs can't react to individual monster actions between initiative slots

#### C. How does the graph handle variable turn counts?

Currently the graph is a fixed cycle: `context_manager -> dm -> pc1 -> pc2 -> pc3 -> pc4 -> END`. With combat initiative, the order changes per combat, and NPC turns may be interspersed.

**Option C1: Dynamic Turn Queue (Recommended)**
- When combat starts, replace `turn_queue` with initiative-sorted order
- `route_to_next_agent()` already reads from `turn_queue` - just reorder it
- When combat ends, restore the original exploration order
- Pro: Minimal graph changes, leverages existing routing
- Con: Need to handle DM-as-NPC routing carefully

**Option C2: Combat Subgraph**
- Create a separate LangGraph subgraph for combat
- Pro: Clean separation of concerns
- Con: Major architectural change, high risk

#### D. How does the DM roleplay NPCs?

**Option D1: Rich NPC Context Injection (Recommended)**
- DM controls all NPCs but receives detailed NPC profiles on each NPC's initiative turn
- Profile includes: HP, AC, personality, motivations, tactics, secrets, current status
- DM roleplays NPCs distinctly while maintaining full narrative control
- Example context for `dm:klarg` turn:
  ```
  NPC Turn: Klarg (Bugbear)
  HP: 27/27 | AC: 16 | Initiative: 18
  Personality: Brutal, vain, cowardly when outmatched
  Motivation: Impress King Grol, hoard treasure
  Tactics: Uses wolf Ripper as flanking partner, retreats below 10 HP
  Secret: Knows where Gundren was taken
  ```
- Pro: 80% of emergent feel, DM can make narrative-serving decisions
- Pro: Matches tabletop D&D where DM plays all NPCs with distinct voices
- Con: NPCs won't truly surprise the DM (but the DM can surprise itself via rich context)

**Option D2: Autonomous NPC Agents** *(rejected for now, future experiment)*
- Each major NPC gets a temporary agent with isolated context and its own LLM calls
- Pro: Fully autonomous, potentially surprising NPC behavior
- Con: NPCs might act against the narrative (boss surrenders too early, goblins make overly clever plans)
- Con: Significant complexity (temporary agent lifecycle, memory isolation, extra LLM calls)
- Con: Risk of narrative incoherence without DM oversight

**Decision:** D1. The DM-with-rich-context approach preserves narrative control while encouraging emergent NPC behavior within the DM's storytelling framework. NPC profiles are injected as part of the `start_combat()` tool call and referenced on each NPC turn.

#### E. What about the existing `combat_mode` field?

The `combat_mode: Literal["Narrative", "Tactical"]` field in GameConfig is currently unused. This is the natural toggle:
- **Narrative mode:** Current behavior (fixed turn order, DM narrates combat freely)
- **Tactical mode:** Initiative-based ordering, structured combat rounds

### Recommended Combination

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Combat start/end | A1: DM Tool-Based | Most reliable, matches D&D |
| NPC turns | B1: DM acts per-NPC + bookend | Strict initiative ordering, faithful D&D tactical feel |
| NPC roleplay | D1: Rich context injection | DM controls NPCs with detailed profiles, preserves narrative control |
| Graph handling | C1: Dynamic turn queue | Minimal changes, leverages existing code |
| Mode toggle | Use existing `combat_mode` field | Already defined, just needs wiring |

### Combat Round Structure

Each tactical combat round follows this structure:

```
DM (bookend)            - Summarize last round, set the scene, describe environment
dm:goblin_1 (init 18)   - DM acts for Goblin 1 (attack, move, etc.)
shadowmere (init 16)    - Shadowmere takes their action
dm:goblin_2 (init 14)   - DM acts for Goblin 2
thorin (init 12)        - Thorin takes their action
brother_aldric (init 10) - Brother Aldric takes their action
elara (init 8)          - Elara takes their action
END -> next round starts with DM bookend
```

The bookend turn gives the DM a narrative framing role each round while individual NPC turns maintain strict initiative ordering.

### Effort & Risk

- **Effort estimate:** Medium (3-5 stories, ~2-3 dev sessions)
- **Risk level:** Medium (graph routing changes need careful testing)
- **Timeline impact:** None on shipped features. This is v1.2+ work.

## Section 4: Detailed Change Proposals

### Story 15-1: Combat State Model & Detection

**Scope:** Add combat tracking to GameState and DM tools for combat start/end.

**models.py changes:**

```python
# NEW: Combat tracking model
class CombatState(BaseModel):
    """Tracks active combat encounter state."""
    active: bool = Field(default=False, description="Whether combat is currently active")
    round_number: int = Field(default=0, ge=0, description="Current combat round")
    initiative_order: list[str] = Field(
        default_factory=list,
        description="Turn order for combat (agent names, with 'dm:npc_name' for NPCs)",
    )
    initiative_rolls: dict[str, int] = Field(
        default_factory=dict,
        description="Initiative roll results per combatant",
    )
    original_turn_queue: list[str] = Field(
        default_factory=list,
        description="Saved pre-combat turn queue for restoration",
    )

# GameState addition:
combat_state: CombatState  # Add to TypedDict
```

**tools.py changes:**

```python
# NEW DM tools:
def start_combat(participants: list[dict]) -> str:
    """DM calls this when combat begins.
    participants: [{
        "name": "Goblin 1",
        "initiative_modifier": 2,
        "hp": 7, "ac": 15,
        "personality": "Cowardly, fights in groups",
        "tactics": "Uses shortbow from cover, flees below 3 HP",
        "secret": None
    }, ...]
    Rolls initiative for all PCs and NPCs, builds initiative order,
    stores NPC profiles for context injection on their turns.
    """

def end_combat() -> str:
    """DM calls this when combat concludes.
    Restores original turn queue, clears combat state.
    """
```

**NPC profiles** provided in `start_combat()` are stored in `CombatState` and injected into the DM's prompt on each NPC's initiative turn, enabling the DM to roleplay each NPC with distinct personality and tactics.

### Story 15-2: Initiative Rolling & Turn Reordering

**Scope:** Implement initiative rolling logic and turn queue reordering.

When `start_combat()` is called:
1. Roll 1d20 + initiative modifier for each PC (using CharacterSheet.initiative)
2. Roll 1d20 + modifier for each NPC (modifier provided by DM)
3. Sort all combatants by roll (highest first, ties broken by modifier then alphabetical)
4. Save current `turn_queue` to `combat_state.original_turn_queue`
5. Replace `turn_queue` with initiative-sorted order
6. NPC entries use format `dm:npc_name` to indicate DM-controlled turns

### Story 15-3: Combat-Aware Graph Routing

**Scope:** Modify `route_to_next_agent()` to handle combat initiative order, DM bookend turns, and DM-as-NPC turns.

**graph.py changes:**

```python
def route_to_next_agent(state: GameState) -> str:
    combat = state.get("combat_state")
    current = state["current_turn"]

    if combat and combat.active:
        # Use initiative order (includes "dm" bookend + "dm:npc_name" entries)
        order = combat.initiative_order
    else:
        # Use standard turn queue
        order = state["turn_queue"]

    # Find current position
    try:
        current_idx = order.index(current)
    except ValueError:
        return "dm"

    if current_idx == len(order) - 1:
        return END  # Round complete

    next_agent = order[current_idx + 1]

    # Handle DM-controlled NPC turns - route to DM node with NPC context
    if next_agent.startswith("dm:"):
        return "dm"  # DM node handles NPC-specific prompting

    return next_agent
```

The initiative_order list looks like:
`["dm", "dm:goblin_1", "shadowmere", "dm:goblin_2", "thorin", "brother_aldric", "elara"]`

- `"dm"` at position 0 is the bookend turn (scene setting, round summary)
- `"dm:goblin_1"` etc. are individual NPC action turns
- PC names are their standard agent turns

### Story 15-4: DM Bookend & NPC Turn Prompting

**Scope:** Enable the DM to serve two distinct roles in combat - narrator (bookend) and NPC controller (per-NPC turns).

**Bookend turn** (`current_turn == "dm"`):
- DM receives prompt context: "Begin combat round {N}. Summarize the battlefield, describe the environment, and set the scene for this round."
- DM narrates the round opening but does NOT act for any NPC
- This is the DM's traditional narrator role

**NPC turn** (`current_turn == "dm:npc_name"`):
- DM receives prompt context: "It is now {npc_name}'s turn (Initiative: {roll}). Narrate {npc_name}'s action this round. Focus only on this creature."
- DM narrates that specific NPC/monster's actions (attack, movement, abilities)
- Keeps NPC actions focused and interleaved with PC actions at correct initiative positions

### Story 15-5: Combat UI Indicators (Optional)

**Scope:** Show initiative order in the party panel or narrative area during combat.

- Display current initiative order with active combatant highlighted
- Show round number
- Indicate when combat mode is Tactical vs. Narrative

### Story 15-6: Combat End Conditions & TPK Handling

**Scope:** Detect combat-ending conditions and force resolution to prevent infinite loops.

**Problem:** Currently, PCs at 0 HP still receive their turn and generate unconscious narrations. If all PCs drop to 0 HP, the game loops indefinitely with unconscious monologues and no resolution.

**Detection logic (checked after each turn in combat):**

```python
def check_combat_end_conditions(state: GameState) -> str | None:
    """Returns end condition type or None if combat continues."""
    combat = state.get("combat_state")
    if not combat or not combat.active:
        return None

    sheets = state.get("character_sheets", {})

    # TPK: All PCs at 0 HP
    pc_names = [n for n in state["turn_queue"] if n != "dm"]
    all_down = all(
        sheets.get(name, {}).hp_current <= 0
        for name in pc_names
        if name in sheets
    )
    if all_down:
        return "tpk"

    # All enemies defeated: No NPC entries left alive in initiative
    npc_entries = [e for e in combat.initiative_order if e.startswith("dm:")]
    # NPC HP tracked in combat_state.npc_profiles
    all_enemies_dead = all(
        combat.npc_profiles.get(e.split(":", 1)[1], {}).get("hp_current", 0) <= 0
        for e in npc_entries
    )
    if all_enemies_dead:
        return "victory"

    return None
```

**Resolution behavior:**

| Condition | Action |
|-----------|--------|
| **TPK** | DM receives forced prompt: "All party members are unconscious/dead. Resolve this encounter narratively - the enemies may capture, kill, or abandon the party. End combat." `end_combat()` is called automatically after DM response. |
| **Victory** | DM receives prompt: "All enemies are defeated. Narrate the aftermath and end combat." `end_combat()` is called automatically. |

**Death saving throws (future consideration):**
- D&D rules: Unconscious PCs roll death saves (d20) on their turn. 3 successes = stable, 3 failures = dead.
- For v1, skip death saves - DM handles unconscious PCs narratively
- Could be added as a 15-6b follow-up if desired

**Skip unconscious PC turns:**
- When combat is active and a PC's `hp_current <= 0`, skip their turn in the initiative order (or reduce to a brief status narration)
- Prevents the "infinite unconscious monologue" problem

## Section 5: Implementation Handoff

### Scope Classification: Moderate

This requires:
- New data models (CombatState)
- Core routing logic changes (graph.py)
- New DM tools (tools.py)
- DM prompt enhancement (agents.py)
- GameState persistence updates
- Comprehensive testing (routing changes are high-risk)

### Handoff Plan

| Role | Responsibility |
|------|---------------|
| **SM (create-story)** | Create Epic 15 and stories 15-1 through 15-6 |
| **Dev (dev-story)** | Implement each story with tests |
| **Code Review** | Critical for story 15-3 (routing changes) |
| **QA** | End-to-end testing with live gameplay |

### Success Criteria

1. In Tactical combat mode, initiative is rolled when DM starts combat
2. Turn order reflects initiative rolls (not alphabetical)
3. NPCs act at their initiative position
4. Exploration/roleplay rounds use original fixed order
5. Combat end restores normal turn order
6. All existing tests continue to pass
7. Narrative combat mode (default) preserves current behavior
8. TPK detection triggers DM resolution narrative and ends combat
9. Victory detection triggers DM aftermath narrative and ends combat
10. Unconscious PCs are skipped (or minimized) in initiative order

### Dependencies

- Story 15-1 must complete before 15-2 and 15-3
- Story 15-3 depends on 15-2 (needs initiative order to route)
- Story 15-4 depends on 15-3 (needs combat routing to work)
- Story 15-5 is independent (UI only)
- Story 15-6 depends on 15-1 (needs CombatState) and 15-3 (needs combat routing to hook into)

### Sprint Status Update

Add to `sprint-status.yaml`:
```yaml
  # Epic 15: Combat Initiative System
  epic-15: backlog
  15-1-combat-state-model: backlog
  15-2-initiative-rolling: backlog
  15-3-combat-aware-routing: backlog
  15-4-npc-monster-turns: backlog
  15-5-combat-ui-indicators: backlog
  15-6-combat-end-conditions: backlog
```
