# Story 15.1: Combat State Model & Detection

Status: review

## Epic

Epic 15: Combat Initiative System

## Story

As a **game engine developer**,
I want **a CombatState model in GameState and DM tools for starting/ending combat**,
So that **the system can track whether combat is active, store initiative data, and NPC profiles, enabling future stories to implement initiative-based turn ordering and NPC turns**.

## Priority

High (foundation story -- all other Epic 15 stories depend on this)

## Estimate

Medium (new Pydantic models + 2 schema-only tools + factory updates + persistence + test fixture updates)

## Dependencies

- Epic 13 (Adventure Setup & Party Management): **done** -- `populate_game_state()` and `create_initial_game_state()` are current targets for modification
- Epic 8 (Character Sheets): **done** -- `CharacterSheet.initiative` field exists and will be referenced by Story 15-2
- `combat_mode: Literal["Narrative", "Tactical"]` already exists on `GameConfig` (line 282) -- this story adds the data structures it will gate

## Acceptance Criteria

1. **Given** `models.py`, **When** the developer imports from it, **Then** `CombatState` and `NpcProfile` Pydantic models are available with all required fields and defaults.

2. **Given** a new `CombatState()`, **When** created with defaults, **Then** `active=False`, `round_number=0`, `initiative_order=[]`, `initiative_rolls={}`, `original_turn_queue=[]`, `npc_profiles={}`.

3. **Given** a new `NpcProfile()`, **When** created with required fields, **Then** it stores `name`, `initiative_modifier`, `hp_max`, `hp_current`, `ac`, and optional `personality`, `tactics`, `secret`, `conditions`.

4. **Given** `GameState` TypedDict, **When** a developer reads the type definition, **Then** it includes a `combat_state: CombatState` field.

5. **Given** `create_initial_game_state()`, **When** called, **Then** the returned state includes `combat_state=CombatState()` (default inactive).

6. **Given** `populate_game_state()`, **When** called, **Then** the returned state includes `combat_state=CombatState()` (default inactive).

7. **Given** `serialize_game_state()`, **When** called on a state with `combat_state`, **Then** the JSON output includes `"combat_state"` key with all fields serialized.

8. **Given** `deserialize_game_state()`, **When** called on JSON with `"combat_state"` data, **Then** it reconstructs the `CombatState` (including nested `NpcProfile` objects).

9. **Given** `deserialize_game_state()`, **When** called on old checkpoint JSON WITHOUT `"combat_state"`, **Then** it defaults to `CombatState()` (backward compatible).

10. **Given** `tools.py`, **When** the developer imports DM tools, **Then** `dm_start_combat` and `dm_end_combat` are available as `@tool`-decorated functions.

11. **Given** `dm_start_combat` tool, **When** defined, **Then** its schema accepts a `participants` parameter (list of dicts with NPC data: name, initiative_modifier, hp, ac, personality, tactics, secret).

12. **Given** `dm_end_combat` tool, **When** defined, **Then** its schema accepts no parameters and returns a confirmation string.

13. **Given** both combat tools, **When** their function body executes, **Then** they return a placeholder string (schema-only, execution will be intercepted in `dm_turn()` by Story 15-2).

14. **Given** the `sample_game_state()` fixture in `test_persistence.py`, **When** used in tests, **Then** it includes `combat_state=CombatState()`.

15. **Given** the `expected_keys` set in `test_serialize_includes_all_fields`, **When** the test runs, **Then** `"combat_state"` is in the expected keys set.

## Tasks / Subtasks

- [x] Task 1: Add `NpcProfile` model to `models.py` (AC: #3)
  - [x] 1.1: Define `NpcProfile(BaseModel)` with fields: `name: str`, `initiative_modifier: int = 0`, `hp_max: int = 1`, `hp_current: int = 1`, `ac: int = 10`, `personality: str = ""`, `tactics: str = ""`, `secret: str = ""`, `conditions: list[str] = []`
  - [x] 1.2: Add appropriate `Field()` descriptors with `ge=` validators for hp/ac
  - [x] 1.3: Add `NpcProfile` to `__all__` exports

- [x] Task 2: Add `CombatState` model to `models.py` (AC: #1, #2)
  - [x] 2.1: Define `CombatState(BaseModel)` with fields: `active: bool = False`, `round_number: int = 0` (with `ge=0`), `initiative_order: list[str] = []`, `initiative_rolls: dict[str, int] = {}`, `original_turn_queue: list[str] = []`, `npc_profiles: dict[str, NpcProfile] = {}`
  - [x] 2.2: Add appropriate `Field()` descriptors with descriptions matching the sprint change proposal
  - [x] 2.3: Add `CombatState` to `__all__` exports

- [x] Task 3: Add `combat_state` field to `GameState` TypedDict (AC: #4)
  - [x] 3.1: Add `combat_state: CombatState` to the `GameState` class body (after `active_fork_id`)
  - [x] 3.2: Update the class docstring to document the new field

- [x] Task 4: Update `create_initial_game_state()` factory (AC: #5)
  - [x] 4.1: Add `combat_state=CombatState()` to the returned `GameState(...)` constructor

- [x] Task 5: Update `populate_game_state()` factory (AC: #6)
  - [x] 5.1: Add `combat_state=CombatState()` to the returned `GameState(...)` constructor

- [x] Task 6: Add `dm_start_combat` tool to `tools.py` (AC: #10, #11, #13)
  - [x] 6.1: Define `@tool` decorated `dm_start_combat(participants: list[dict[str, Any]]) -> str`
  - [x] 6.2: Docstring should describe participant dict schema: `{"name": str, "initiative_modifier": int, "hp": int, "ac": int, "personality": str, "tactics": str, "secret": str | None}`
  - [x] 6.3: Function body returns placeholder string: `"Combat started with {len(participants)} NPC(s)."`
  - [x] 6.4: Add comment: `# Tool schema only - execution intercepted in dm_turn()`
  - [x] 6.5: Add `dm_start_combat` to `__all__` exports

- [x] Task 7: Add `dm_end_combat` tool to `tools.py` (AC: #12, #13)
  - [x] 7.1: Define `@tool` decorated `dm_end_combat() -> str`
  - [x] 7.2: Function body returns: `"Combat ended. Restoring exploration turn order."`
  - [x] 7.3: Add comment: `# Tool schema only - execution intercepted in dm_turn()`
  - [x] 7.4: Add `dm_end_combat` to `__all__` exports

- [x] Task 8: Update `serialize_game_state()` in `persistence.py` (AC: #7)
  - [x] 8.1: Add `combat_state` serialization to the `serializable` dict: `"combat_state": state.get("combat_state", CombatState()).model_dump()`
  - [x] 8.2: Add `CombatState` to the imports from `models`

- [x] Task 9: Update `deserialize_game_state()` in `persistence.py` (AC: #8, #9)
  - [x] 9.1: Add backward-compatible deserialization: `combat_state_raw = data.get("combat_state", {})`
  - [x] 9.2: Reconstruct nested `NpcProfile` objects from `npc_profiles` dict
  - [x] 9.3: Build `CombatState` from the raw data, defaulting to `CombatState()` if empty/missing
  - [x] 9.4: Add `combat_state=combat_state` to the returned `GameState(...)` constructor
  - [x] 9.5: Add `CombatState` and `NpcProfile` to the imports from `models`

- [x] Task 10: Update `sample_game_state` test fixtures (AC: #14, #15)
  - [x] 10.1: In `tests/test_persistence.py`, add `combat_state=CombatState()` to `sample_game_state()` fixture and add `CombatState` import
  - [x] 10.2: Add `"combat_state"` to the `expected_keys` set in `test_serialize_includes_all_fields`
  - [x] 10.3: Check ALL other `sample_game_state()` fixtures across test files and add `combat_state=CombatState()` to each:
    - `tests/test_story_12_1_fork_creation.py`
    - `tests/test_story_12_2_fork_management_ui.py`
    - `tests/test_story_12_3_fork_comparison_view.py`
    - `tests/test_story_12_4_fork_resolution.py`

- [x] Task 11: Write new tests in `tests/test_story_15_1_combat_state_model.py` (AC: #1-15)
  - [x] 11.1: Test `NpcProfile` default construction (all defaults valid)
  - [x] 11.2: Test `NpcProfile` with full fields (name, hp, ac, personality, tactics, secret, conditions)
  - [x] 11.3: Test `NpcProfile` hp/ac validators reject negative values
  - [x] 11.4: Test `CombatState` default construction (`active=False`, `round_number=0`, empty collections)
  - [x] 11.5: Test `CombatState` with populated `npc_profiles` dict containing `NpcProfile` instances
  - [x] 11.6: Test `CombatState` `round_number` validator rejects negative
  - [x] 11.7: Test `GameState` TypedDict accepts `combat_state` field
  - [x] 11.8: Test `create_initial_game_state()` returns state with `combat_state` field
  - [x] 11.9: Test `populate_game_state()` returns state with `combat_state` field (mock config loading)
  - [x] 11.10: Test `dm_start_combat` tool exists and is callable
  - [x] 11.11: Test `dm_start_combat` returns placeholder string containing participant count
  - [x] 11.12: Test `dm_end_combat` tool exists and is callable
  - [x] 11.13: Test `dm_end_combat` returns placeholder string
  - [x] 11.14: Test `serialize_game_state` includes `combat_state` key in JSON
  - [x] 11.15: Test `serialize_game_state` with non-default CombatState (active combat with NPCs)
  - [x] 11.16: Test `deserialize_game_state` round-trips CombatState correctly
  - [x] 11.17: Test `deserialize_game_state` backward-compatible with missing `combat_state` key
  - [x] 11.18: Test `deserialize_game_state` reconstructs nested `NpcProfile` objects

## Dev Notes

### Model Placement in models.py

Place `NpcProfile` and `CombatState` **after the `CallbackLog` class** (around line 770) and **before the `CharacterSheet`-related models**. This groups combat models with other game-state tracking models. Both must be defined BEFORE the `GameState` TypedDict (line 1744) since `CombatState` is referenced there.

### NpcProfile Design

The `NpcProfile` model stores data that the DM provides via `start_combat()` and uses during NPC turns. Key fields:

```python
class NpcProfile(BaseModel):
    """NPC/monster profile for combat encounters.

    Stored in CombatState.npc_profiles and injected into the DM's
    prompt on each NPC's initiative turn (Story 15-4).
    """
    name: str = Field(..., min_length=1, description="NPC name (e.g., 'Goblin 1', 'Klarg')")
    initiative_modifier: int = Field(default=0, description="Added to d20 for initiative roll")
    hp_max: int = Field(default=1, ge=1, description="Maximum hit points")
    hp_current: int = Field(default=1, ge=0, description="Current hit points (0 = defeated)")
    ac: int = Field(default=10, ge=0, description="Armor class")
    personality: str = Field(default="", description="Personality traits for DM roleplay")
    tactics: str = Field(default="", description="Combat tactics for DM to follow")
    secret: str = Field(default="", description="Hidden info (e.g., 'knows where prisoner is held')")
    conditions: list[str] = Field(default_factory=list, description="Active conditions (poisoned, prone, etc.)")
```

Note: `hp_current` uses `ge=0` (not `ge=1`) because NPCs can reach 0 HP (defeated). `hp_max` uses `ge=1` because max HP must be at least 1.

### CombatState Design

```python
class CombatState(BaseModel):
    """Tracks active combat encounter state.

    When combat_mode is 'Tactical' and active is True, the graph routing
    (Story 15-3) uses initiative_order instead of the standard turn_queue.
    """
    active: bool = Field(default=False, description="Whether combat is currently active")
    round_number: int = Field(default=0, ge=0, description="Current combat round (0 = not started)")
    initiative_order: list[str] = Field(
        default_factory=list,
        description="Turn order for combat (agent names, with 'dm:npc_name' for NPC turns)",
    )
    initiative_rolls: dict[str, int] = Field(
        default_factory=dict,
        description="Initiative roll results per combatant (name -> total roll)",
    )
    original_turn_queue: list[str] = Field(
        default_factory=list,
        description="Saved pre-combat turn queue for restoration when combat ends",
    )
    npc_profiles: dict[str, NpcProfile] = Field(
        default_factory=dict,
        description="NPC data keyed by NPC name (for DM context injection on NPC turns)",
    )
```

The `npc_profiles` dict is keyed by the NPC name (e.g., `"goblin_1"`, `"klarg"`) -- the same name that appears after `"dm:"` in `initiative_order` entries.

### Tool Definition Pattern (Schema-Only)

Follow the exact pattern used by `dm_whisper_to_agent` (tools.py line 540) and `dm_reveal_secret` (line 575):

```python
@tool
def dm_start_combat(participants: list[dict[str, Any]]) -> str:
    """Begin a tactical combat encounter.

    Call this when combat starts. Provide profiles for all NPC/monster
    combatants. Initiative will be rolled for all PCs and NPCs, and
    the turn order will be reordered by initiative.

    Each participant dict should contain:
    - name (str, required): NPC name (e.g., "Goblin 1", "Klarg")
    - initiative_modifier (int): Modifier added to d20 initiative roll
    - hp (int): Maximum hit points
    - ac (int): Armor class
    - personality (str): Personality for distinct NPC roleplay
    - tactics (str): Combat tactics to follow
    - secret (str, optional): Hidden information

    Args:
        participants: List of NPC profile dicts.

    Returns:
        Confirmation message.

    Examples:
        - dm_start_combat([{"name": "Goblin 1", "initiative_modifier": 2, "hp": 7, "ac": 15, "personality": "Cowardly", "tactics": "Uses shortbow from cover"}])
        - dm_start_combat([{"name": "Klarg", "initiative_modifier": 3, "hp": 27, "ac": 16, "personality": "Brutal, vain", "tactics": "Uses wolf as flanking partner, retreats below 10 HP", "secret": "Knows where Gundren was taken"}])
    """
    # Tool schema only - execution intercepted in dm_turn()
    return f"Combat started with {len(participants)} NPC(s)."


@tool
def dm_end_combat() -> str:
    """End the current combat encounter.

    Call this when combat concludes (enemies defeated, party flees,
    or narrative resolution). The turn order will be restored to the
    pre-combat exploration order.

    Returns:
        Confirmation message.
    """
    # Tool schema only - execution intercepted in dm_turn()
    return "Combat ended. Restoring exploration turn order."
```

**CRITICAL**: These tools must use the `@tool` decorator from `langchain_core.tools` (already imported in tools.py line 10). The `Any` type is already imported (line 8). No new imports needed in tools.py.

### Persistence Serialization Pattern

Follow the exact pattern used by other fields. In `serialize_game_state()`:

```python
# Story 15.1: Combat state persistence
"combat_state": state.get("combat_state", CombatState()).model_dump(),
```

In `deserialize_game_state()`:

```python
# Handle combat_state deserialization (Story 15.1)
# Backward compatible: old checkpoints may not have this field
combat_state_raw = data.get("combat_state", {})
if isinstance(combat_state_raw, dict) and combat_state_raw:
    # Reconstruct NpcProfile objects from nested dicts
    npc_profiles_raw = combat_state_raw.get("npc_profiles", {})
    npc_profiles = {k: NpcProfile(**v) for k, v in npc_profiles_raw.items()}
    combat_state = CombatState(
        active=combat_state_raw.get("active", False),
        round_number=combat_state_raw.get("round_number", 0),
        initiative_order=combat_state_raw.get("initiative_order", []),
        initiative_rolls=combat_state_raw.get("initiative_rolls", {}),
        original_turn_queue=combat_state_raw.get("original_turn_queue", []),
        npc_profiles=npc_profiles,
    )
else:
    combat_state = CombatState()
```

Import `CombatState` and `NpcProfile` from `models` in `persistence.py` -- add to the existing import block (line 23-44).

### GameState TypedDict Addition

Add after the `active_fork_id` field (line 1796):

```python
combat_state: CombatState  # Story 15.1: Combat encounter tracking
```

### Factory Function Updates

Both factories need a single line addition. In `create_initial_game_state()` (line 2498), add to the `GameState(...)` constructor:

```python
combat_state=CombatState(),
```

Same in `populate_game_state()` (line 2609).

### Test Fixture Updates -- ALL sample_game_state Fixtures

The `GameState` TypedDict change means EVERY function that constructs a `GameState` dict must include `combat_state`. The following test files have `sample_game_state()` fixtures that need updating:

| File | Line | Change |
|------|------|--------|
| `tests/test_persistence.py` | 57 | Add `combat_state=CombatState()` + import |
| `tests/test_story_12_1_fork_creation.py` | 45 | Add `combat_state=CombatState()` + import |
| `tests/test_story_12_2_fork_management_ui.py` | 54 | Add `combat_state=CombatState()` + import |
| `tests/test_story_12_3_fork_comparison_view.py` | 47 | Add `combat_state=CombatState()` + import |
| `tests/test_story_12_4_fork_resolution.py` | 49 | Add `combat_state=CombatState()` + import |

Also update `expected_keys` in `test_persistence.py` line 212 to include `"combat_state"`.

**CRITICAL PATTERN**: When adding the import, add `CombatState` to the existing `from models import ...` block in each file. Do NOT create a new import statement.

### Files to Modify

1. **`models.py`** -- Add `NpcProfile`, `CombatState` models; add `combat_state` to `GameState` TypedDict; update `create_initial_game_state()` and `populate_game_state()` factories; update `__all__`
2. **`tools.py`** -- Add `dm_start_combat` and `dm_end_combat` tool functions; update `__all__`
3. **`persistence.py`** -- Add `combat_state` to `serialize_game_state()` and `deserialize_game_state()`; update imports
4. **`tests/test_persistence.py`** -- Update `sample_game_state` fixture and `expected_keys`
5. **`tests/test_story_12_1_fork_creation.py`** -- Update `sample_game_state` fixture
6. **`tests/test_story_12_2_fork_management_ui.py`** -- Update `sample_game_state` fixture
7. **`tests/test_story_12_3_fork_comparison_view.py`** -- Update `sample_game_state` fixture
8. **`tests/test_story_12_4_fork_resolution.py`** -- Update `sample_game_state` fixture
9. **`tests/test_story_15_1_combat_state_model.py`** -- **NEW** test file

### Files NOT to Modify

- **`agents.py`** -- No changes. Tool interception for `dm_start_combat` / `dm_end_combat` will be added in Story 15-2.
- **`graph.py`** -- No changes. Combat-aware routing is Story 15-3.
- **`app.py`** -- No changes. Combat UI is Story 15-5.
- **`config.py`** -- No changes. `combat_mode` already exists on `GameConfig`.
- **`memory.py`** -- No changes.
- **`styles/theme.css`** -- No changes.

### Existing combat_mode Field

`GameConfig.combat_mode` (models.py line 282) is `Literal["Narrative", "Tactical"]` defaulting to `"Narrative"`. This field is already defined and persisted. Story 15-1 does NOT reference or gate on `combat_mode` -- that logic comes in Story 15-2 and 15-3. This story only adds the data structures.

### __all__ Export Updates

In `models.py`, add to `__all__` (alphabetical position):
- `"CombatState"` (after `"ComparisonTurn"`)
- `"NpcProfile"` (after `"NarrativeMessage"`)

In `tools.py`, add to `__all__`:
- `"dm_end_combat"` (after `"dm_update_character_sheet"` or wherever alphabetical)
- `"dm_start_combat"` (after `"dm_end_combat"`)

In `persistence.py`, add to imports from `models`:
- `CombatState`
- `NpcProfile`

### Test Approach

Create `tests/test_story_15_1_combat_state_model.py`. Use class-based test organization (matching project convention):

- `class TestNpcProfile` -- model construction, defaults, validation
- `class TestCombatState` -- model construction, defaults, nested NpcProfile
- `class TestGameStateCombatField` -- TypedDict integration
- `class TestFactoryFunctions` -- `create_initial_game_state()`, `populate_game_state()`
- `class TestCombatTools` -- `dm_start_combat`, `dm_end_combat` schema and returns
- `class TestPersistence` -- serialize/deserialize round-trip, backward compatibility

Mock `load_character_configs` and `load_dm_config` for `populate_game_state()` tests (same pattern as `tests/test_models.py`).

### Edge Cases to Handle

- `NpcProfile.hp_current` can be 0 (defeated NPC) -- use `ge=0`, not `ge=1`
- `NpcProfile.hp_max` must be at least 1 -- use `ge=1`
- `CombatState.round_number` can be 0 (not started) -- use `ge=0`
- Old checkpoints without `combat_state` must deserialize cleanly
- `npc_profiles` dict may contain NpcProfile objects with nested validation

### Project Structure Notes

- All models in `models.py` (flat layout, no separate files)
- All tools in `tools.py` (flat layout)
- Tests in `tests/` directory with `test_story_{epic}_{story}_{name}.py` naming
- Uses `python -m pytest` and `python -m ruff` (uv not on PATH in MINGW64)

### References

- [Source: models.py#GameState ~line 1744] - TypedDict to extend
- [Source: models.py#GameConfig ~line 271] - `combat_mode` field already defined
- [Source: models.py#create_initial_game_state ~line 2488] - Factory to update
- [Source: models.py#populate_game_state ~line 2522] - Factory to update
- [Source: tools.py#dm_whisper_to_agent ~line 540] - Schema-only tool pattern to follow
- [Source: tools.py#dm_reveal_secret ~line 575] - Schema-only tool pattern to follow
- [Source: tools.py#__all__ ~line 17] - Exports list to update
- [Source: persistence.py#serialize_game_state ~line 202] - Serialization to extend
- [Source: persistence.py#deserialize_game_state ~line 263] - Deserialization to extend
- [Source: persistence.py#imports ~line 23] - Import block to extend
- [Source: tests/test_persistence.py#sample_game_state ~line 57] - Test fixture to update
- [Source: tests/test_persistence.py#expected_keys ~line 212] - Key set to update
- [Source: tests/test_story_12_1_fork_creation.py#sample_game_state ~line 45] - Fixture to update
- [Source: tests/test_story_12_2_fork_management_ui.py#sample_game_state ~line 54] - Fixture to update
- [Source: tests/test_story_12_3_fork_comparison_view.py#sample_game_state ~line 47] - Fixture to update
- [Source: tests/test_story_12_4_fork_resolution.py#sample_game_state ~line 49] - Fixture to update
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-10.md#Story 15-1] - Design specification
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-10.md#Section 3] - Architecture decisions

## Dev Agent Record

### Agent Model Used
claude-opus-4-6

### Debug Log References
- Fixed populate_game_state mock: config.load_character_configs, not models.load_character_configs
- LangChain @tool objects are StructuredTool instances (not plain callables), tests use hasattr(invoke)
- Updated test_minimal_state_file_size threshold from 1024 to 1500 to accommodate new combat_state field
- test_story_12_1/12_3/12_4 use create_initial_game_state() so no fixture updates needed

### Completion Notes List
- All 11 tasks completed
- 37 new tests in test_story_15_1_combat_state_model.py (all passing)
- 4361 total tests passing (14 pre-existing failures unchanged)
- No regressions in any affected test files

### File List
- models.py: Added NpcProfile, CombatState models; combat_state field on GameState; factory updates; __all__ exports
- tools.py: Added dm_start_combat, dm_end_combat schema-only tools; __all__ exports
- persistence.py: Added combat_state serialize/deserialize with backward compat; CombatState/NpcProfile imports
- tests/test_persistence.py: Added CombatState import, fixture update, expected_keys update, file size threshold update
- tests/test_story_12_2_fork_management_ui.py: Added CombatState import and fixture update
- tests/test_story_15_1_combat_state_model.py: NEW - 37 tests covering all acceptance criteria
