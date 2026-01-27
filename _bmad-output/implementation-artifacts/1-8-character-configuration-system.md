# Story 1.8: Character Configuration System

Status: done

## Story

As a **user**,
I want **to define character personalities and traits via YAML configuration files**,
so that **I can customize my party without editing code**.

## Acceptance Criteria

1. **Given** YAML files in `config/characters/` (dm.yaml, rogue.yaml, fighter.yaml, wizard.yaml, cleric.yaml)
   **When** the application starts
   **Then** each character configuration is loaded and validated

2. **Given** a character YAML file with format:
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
   **Then** a `CharacterConfig` Pydantic model is created with all fields populated

3. **Given** a user wants to add a new character
   **When** they create a new YAML file in the characters directory
   **Then** the application loads it on next startup

4. **Given** the config specifies 4 PC agents (FR9)
   **When** the game initializes
   **Then** exactly those 4 characters are created as PC agents

5. **Given** each character has defined traits
   **When** their agent is created
   **Then** the system prompt incorporates those traits for personality consistency (FR10, FR52)

## Tasks / Subtasks

- [x] Task 1: Create character YAML directory and default character files (AC: #1, #2)
  - [x] Create `config/characters/` directory
  - [x] Create `dm.yaml` with DM configuration
  - [x] Create `fighter.yaml` with default Fighter character
  - [x] Create `rogue.yaml` with default Rogue character
  - [x] Create `wizard.yaml` with default Wizard character
  - [x] Create `cleric.yaml` with default Cleric character

- [x] Task 2: Implement character configuration loading in `config.py` (AC: #1, #2, #3)
  - [x] Add `load_character_configs()` function to discover and load all YAML files in characters directory
  - [x] Add `load_dm_config()` function to load DM configuration from dm.yaml
  - [x] Validate loaded YAML against `CharacterConfig` and `DMConfig` Pydantic models
  - [x] Handle missing/malformed files with clear error messages
  - [x] Return dict of character configs keyed by lowercase name

- [x] Task 3: Integrate character loading with game initialization (AC: #4, #5)
  - [x] Add character configs to `AppConfig` class
  - [x] Update `create_initial_game_state()` or add helper to populate `characters` dict in GameState
  - [x] Build turn_queue from loaded character names (dm first, then PCs)
  - [x] Initialize agent_memories for each character

- [x] Task 4: Write comprehensive tests (AC: all)
  - [x] Test valid YAML loading and validation
  - [x] Test missing required fields raises ValidationError
  - [x] Test invalid color format raises ValidationError
  - [x] Test dynamic character discovery (adding new YAML file)
  - [x] Test game state initialization with loaded characters

## Dev Notes

### Existing Code to Leverage

**DO NOT recreate - these already exist:**
- `CharacterConfig` model in `models.py:61-107` - Pydantic model with validators for name, color
- `DMConfig` model in `models.py:113-156` - DM config with provider validation
- `GameState` TypedDict in `models.py:185-217` - includes `characters` and `dm_config` fields
- `create_initial_game_state()` in `models.py:232-253` - factory function (may need extension)
- `config.py` with `AppConfig`, `get_config()` - existing config infrastructure
- `agents.py` with `create_pc_agent()`, `build_pc_system_prompt()` - already uses CharacterConfig

**Use existing validation patterns from:**
- `CharacterConfig.name_not_empty()` validator at `models.py:89-95`
- `CharacterConfig.color_is_hex()` validator at `models.py:97-106`
- `DMConfig.provider_is_supported()` validator at `models.py:137-145`

### Character YAML Schema

Each PC character file (`config/characters/{name}.yaml`):
```yaml
# Required fields
name: "Shadowmere"           # Display name (validated: not empty/whitespace)
class: "Rogue"               # D&D class name (maps to CLASS_GUIDANCE in agents.py)
personality: "Sardonic wit, trust issues, always looking for the angle"

# Visual (required)
color: "#6B8E6B"             # Hex format validated

# LLM settings (optional - defaults from AppConfig)
provider: "claude"           # gemini | claude | ollama
model: "claude-3-haiku-20240307"
token_limit: 4000
```

DM config file (`config/characters/dm.yaml`):
```yaml
name: "Dungeon Master"
provider: "gemini"
model: "gemini-1.5-flash"
token_limit: 8000
color: "#D4A574"
```

### Character Colors (from UX Spec)

Use these canonical colors from the UX design:
- DM: `#D4A574` (gold)
- Fighter: `#C45C4A` (red)
- Rogue: `#6B8E6B` (green)
- Wizard: `#7B68B8` (purple)
- Cleric: `#4A90A4` (blue)

### Loading Pattern

```python
# In config.py - suggested approach
def load_character_configs() -> dict[str, CharacterConfig]:
    """Load all character configs from config/characters/*.yaml."""
    characters_dir = PROJECT_ROOT / "config" / "characters"
    configs: dict[str, CharacterConfig] = {}

    for yaml_file in characters_dir.glob("*.yaml"):
        if yaml_file.stem == "dm":
            continue  # DM handled separately
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # Key by lowercase name for turn_queue consistency
        config = CharacterConfig(**data)
        configs[config.name.lower()] = config

    return configs
```

### Integration with GameState

The `GameState.characters` field expects `dict[str, CharacterConfig]` keyed by lowercase agent name. This matches how `graph.py` creates PC nodes dynamically and how `pc_turn()` looks up character config.

### Test File Location

Add tests to `tests/test_config.py` (create if doesn't exist) or extend existing test files.

### Project Structure Notes

- Flat project layout - all modules in root
- Character YAML files go in `config/characters/` subdirectory
- Follow existing naming: snake_case functions, PascalCase classes

### References

- [Source: models.py#CharacterConfig] - Existing model definition
- [Source: models.py#DMConfig] - DM configuration model
- [Source: models.py#GameState] - State container with characters dict
- [Source: config.py#AppConfig] - Configuration loading infrastructure
- [Source: agents.py#build_pc_system_prompt] - Uses CharacterConfig for prompts
- [Source: graph.py#create_game_workflow] - Creates PC nodes from turn_queue
- [Source: architecture.md#Character-Config-YAML] - YAML format specification
- [Source: epics.md#Story-1.8] - Story requirements

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No errors encountered during implementation.

### Completion Notes List

- Created `config/characters/` directory with 5 YAML files: dm.yaml, fighter.yaml, rogue.yaml, wizard.yaml, cleric.yaml
- All character files use the canonical UX spec colors
- Implemented `load_character_configs()` function in config.py that discovers and loads all PC YAML files, maps YAML 'class' to Pydantic 'character_class', and keys results by lowercase character name
- Implemented `load_dm_config()` function that loads DM configuration from dm.yaml with fallback to default DMConfig
- Both functions handle missing directories/files gracefully (return empty dict or default config)
- Added `populate_game_state()` factory function in models.py that creates a fully initialized GameState with characters, turn_queue (dm first, then sorted PCs), and agent_memories with correct token limits
- Added 13 new tests covering: YAML loading, validation errors (missing fields, invalid colors), dynamic character discovery, game state initialization
- All 251 tests pass with no regressions
- Linting (ruff) passes with no errors

### File List

**New files:**
- config/characters/dm.yaml
- config/characters/fighter.yaml
- config/characters/rogue.yaml
- config/characters/wizard.yaml
- config/characters/cleric.yaml

**Modified files:**
- config.py - Added load_character_configs(), load_dm_config(), TYPE_CHECKING import, error handling for malformed YAML
- models.py - Added populate_game_state() factory function, updated __all__, added provider validation to CharacterConfig
- tests/test_config.py - Added TestCharacterConfigLoading class with 10 tests (including error handling)
- tests/test_models.py - Added TestGameStateInitialization class with 4 tests, added provider validation tests

**Note:** The following files were modified in a related story (1.6 PC Agent) but committed together:
- tools.py - Added pc_roll_dice tool
- tests/test_tools.py - Added TestPCRollDice class
- tests/test_agents.py - Added PC agent tests

## Change Log

- 2026-01-26: Implemented Story 1.8 - Character Configuration System
  - Created character YAML files with canonical UX colors
  - Added character/DM config loading functions to config.py
  - Added populate_game_state() factory for game initialization
  - Added comprehensive tests (13 new tests, 251 total pass)
- 2026-01-26: Code Review Fixes
  - Added provider validation to CharacterConfig (matching DMConfig)
  - Added error handling for malformed YAML files with clear error messages
  - Added 5 new tests for provider validation and error handling
  - Updated File List to document all modified files
