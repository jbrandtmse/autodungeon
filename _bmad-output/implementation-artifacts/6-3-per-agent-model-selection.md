# Story 6.3: Per-Agent Model Selection

Status: done

## Story

As a **user**,
I want **to choose which LLM provider and model powers each character**,
so that **I can mix providers or use different models for different roles**.

## Acceptance Criteria

1. **Given** the "Models" tab in the config modal
   **When** I view it
   **Then** I see a grid with rows for: DM, Fighter, Rogue, Wizard, Cleric, Summarizer

2. **Given** each agent row
   **When** displayed
   **Then** it shows:
   - Agent name (in character color for PCs)
   - Provider dropdown (Gemini, Claude, Ollama)
   - Model dropdown (populated based on selected provider)
   - Status indicator (Active, AI, or "You" if controlled)

3. **Given** I select a provider for an agent
   **When** the selection changes
   **Then** the model dropdown updates with available models for that provider (FR42, FR43)

4. **Given** the Summarizer row
   **When** I configure it
   **Then** I can select which model handles memory summarization (FR44)
   **And** this is independent of agent models

5. **Given** quick actions below the grid
   **When** I click "Copy DM to all PCs"
   **Then** all PC agents are set to the same provider/model as the DM

6. **Given** quick actions
   **When** I click "Reset to defaults"
   **Then** all agents return to the default configuration from config/defaults.yaml

7. **Given** I change a model selection
   **When** I save the configuration
   **Then** a confirmation shows: "Changes will apply on next turn"

## Tasks / Subtasks

- [x] Task 1: Create agent row component for Models tab
  - [x] 1.1 Create `render_agent_model_row()` function in app.py with parameters: agent_key, agent_name, character_class, color, is_dm, is_summarizer
  - [x] 1.2 Display agent name with character color (use CSS var for PCs, gold for DM, secondary for Summarizer)
  - [x] 1.3 Create provider dropdown with options: Gemini, Claude, Ollama
  - [x] 1.4 Create model dropdown that updates based on selected provider
  - [x] 1.5 Add status indicator showing: "Active" (current turn), "AI", or "You" (controlled)
  - [x] 1.6 Write unit tests for agent row rendering in different states

- [x] Task 2: Implement provider-to-models mapping (AC #3)
  - [x] 2.1 Create `get_available_models()` function in config.py that returns models for a provider
  - [x] 2.2 For Gemini: Return `["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"]`
  - [x] 2.3 For Claude: Return `["claude-3-haiku-20240307", "claude-3-5-sonnet-20241022", "claude-sonnet-4-20250514"]`
  - [x] 2.4 For Ollama: Return dynamically from `st.session_state["ollama_available_models"]` (set by Story 6.2)
  - [x] 2.5 Handle Ollama fallback if no models available: `["llama3", "mistral", "phi3"]` as suggestions
  - [x] 2.6 Write unit tests for model list retrieval

- [x] Task 3: Implement agent model state management
  - [x] 3.1 Create `AgentModelConfig` model in models.py with fields: agent_key, provider, model
  - [x] 3.2 Add `agent_model_overrides` to session state: `dict[str, AgentModelConfig]`
  - [x] 3.3 Create `get_effective_agent_model()` function: returns override or config default
  - [x] 3.4 Store DM, PCs, and Summarizer configs separately in state
  - [x] 3.5 Write unit tests for state management

- [x] Task 4: Render Models tab grid (AC #1)
  - [x] 4.1 Replace placeholder content in "Models" tab with agent grid
  - [x] 4.2 Add section header "Agent Models" with campfire styling
  - [x] 4.3 Render DM row first (gold color, no class)
  - [x] 4.4 Render PC rows in turn order (Fighter, Rogue, Wizard, Cleric) with character colors
  - [x] 4.5 Add separator line
  - [x] 4.6 Render Summarizer row (secondary color, labeled "Summarizer")
  - [x] 4.7 Write visual verification tests

- [x] Task 5: Implement dropdown change handlers (AC #3)
  - [x] 5.1 Create `handle_provider_change()` function that updates session state and resets model selection
  - [x] 5.2 When provider changes, set model to first available for that provider
  - [x] 5.3 Create `handle_model_change()` function that updates session state
  - [x] 5.4 Call `mark_config_changed()` when any selection changes
  - [x] 5.5 Handle Ollama case: show warning if no models available
  - [x] 5.6 Write unit tests for change handlers

- [x] Task 6: Implement status indicator logic (AC #2)
  - [x] 6.1 Create `get_agent_status()` function: returns "Active" | "AI" | "You"
  - [x] 6.2 "Active" when agent matches `game["current_turn"]`
  - [x] 6.3 "You" when agent matches `controlled_character`
  - [x] 6.4 "AI" for all other agents
  - [x] 6.5 Style status badge with appropriate color (amber for Active, green for AI, purple for You)
  - [x] 6.6 Write unit tests for status logic

- [x] Task 7: Implement "Copy DM to all PCs" quick action (AC #5)
  - [x] 7.1 Add "Copy DM to all PCs" button below the agent grid
  - [x] 7.2 Create `handle_copy_dm_to_pcs()` function
  - [x] 7.3 Get DM's current provider and model from state
  - [x] 7.4 Apply to all PC agents (Fighter, Rogue, Wizard, Cleric)
  - [x] 7.5 Do NOT apply to Summarizer (independent)
  - [x] 7.6 Mark config as changed and trigger rerun
  - [x] 7.7 Write unit tests for copy action

- [x] Task 8: Implement "Reset to defaults" quick action (AC #6)
  - [x] 8.1 Add "Reset to defaults" button next to "Copy DM to all PCs"
  - [x] 8.2 Create `handle_reset_model_defaults()` function
  - [x] 8.3 Load defaults from `config/defaults.yaml` (dm, summarizer) and character YAMLs
  - [x] 8.4 Clear all agent model overrides in session state
  - [x] 8.5 Mark config as changed and trigger rerun
  - [x] 8.6 Write unit tests for reset action

- [x] Task 9: Implement Summarizer row (AC #4)
  - [x] 9.1 Summarizer uses same provider/model dropdowns as other agents
  - [x] 9.2 Summarizer config is stored separately: `game_config.summarizer_model` (existing) plus new provider
  - [x] 9.3 Add `summarizer_provider` field to GameConfig model
  - [x] 9.4 Summarizer has no status indicator (it's not a turn-taking agent)
  - [x] 9.5 Add help text: "Model used for memory compression"
  - [x] 9.6 Write unit tests for Summarizer configuration

- [x] Task 10: Implement save confirmation message (AC #7)
  - [x] 10.1 When Save is clicked and model configs have changed, show toast: "Changes will apply on next turn"
  - [x] 10.2 Add `model_config_changed` flag to distinguish from API key changes
  - [x] 10.3 Apply changes by updating game state (dm_config, characters, game_config)
  - [x] 10.4 Write integration tests for save flow

- [x] Task 11: Wire up changes to game state
  - [x] 11.1 Create `apply_model_config_changes()` function
  - [x] 11.2 Update `dm_config.provider` and `dm_config.model` from overrides
  - [x] 11.3 Update each character's `provider` and `model` in `characters` dict
  - [x] 11.4 Update `game_config.summarizer_model` and new `summarizer_provider`
  - [x] 11.5 Changes take effect on next turn (no mid-turn switching)
  - [x] 11.6 Write integration tests for state updates

- [x] Task 12: Add CSS styling for Models tab
  - [x] 12.1 Add `.agent-model-grid` class for grid layout
  - [x] 12.2 Add `.agent-model-row` class with character color border
  - [x] 12.3 Style dropdowns to match campfire theme
  - [x] 12.4 Style status badges (Active/AI/You)
  - [x] 12.5 Style quick action buttons (secondary style)
  - [x] 12.6 Add separator styling between PCs and Summarizer
  - [x] 12.7 Write visual verification tests using chrome-devtools MCP

- [x] Task 13: Update snapshot_config_values for change detection
  - [x] 13.1 Include agent model configs in snapshot
  - [x] 13.2 Compare current agent models against snapshot
  - [x] 13.3 Write unit tests for model config change detection

- [x] Task 14: Write acceptance tests
  - [x] 14.1 Test: Models tab shows all agent rows (AC #1)
  - [x] 14.2 Test: Each row displays name, provider, model, status (AC #2)
  - [x] 14.3 Test: Provider change updates model dropdown (AC #3)
  - [x] 14.4 Test: Summarizer can be configured independently (AC #4)
  - [x] 14.5 Test: "Copy DM to all PCs" applies DM config to PCs (AC #5)
  - [x] 14.6 Test: "Reset to defaults" loads config from YAML (AC #6)
  - [x] 14.7 Test: Save shows confirmation toast (AC #7)
  - [x] 14.8 Test: Changes are applied to game state on save

## Dev Notes

### Implementation Strategy

This story populates the "Models" tab created in Story 6.1 with a grid for per-agent model selection. The key challenges are:

1. **Dynamic model lists** - Model dropdown must update when provider changes
2. **State management** - Track overrides separately from config file values
3. **Integration with existing config** - Changes must flow to dm_config, characters, and game_config

### Existing Foundation (from Stories 6.1 and 6.2)

**Config modal and tab structure already exist:**

```python
# app.py (render_config_modal)
@st.dialog("Configuration", width="large")
def render_config_modal() -> None:
    tab1, tab2, tab3 = st.tabs(["API Keys", "Models", "Settings"])

    with tab1:
        render_api_keys_tab()  # Story 6.2 implemented

    with tab2:
        st.markdown(
            '<p class="config-tab-placeholder">Model selection coming in Story 6.3</p>',
            unsafe_allow_html=True,
        )
    # ...
```

**DMConfig already has provider/model fields:**

```python
# models.py (DMConfig)
class DMConfig(BaseModel):
    name: str = Field(default="Dungeon Master", description="DM display name")
    provider: str = Field(default="gemini", description="LLM provider")
    model: str = Field(default="gemini-1.5-flash", description="Model name")
    token_limit: int = Field(default=8000, ge=1, description="Context limit for DM")
    color: str = Field(default="#D4A574", description="Hex color for UI")
```

**CharacterConfig already has provider/model fields:**

```python
# models.py (CharacterConfig)
class CharacterConfig(BaseModel):
    name: str = Field(..., min_length=1, description="Character name")
    character_class: str = Field(..., description="D&D class")
    personality: str = Field(..., description="Personality traits")
    color: str = Field(..., description="Hex color for UI (e.g., #6B8E6B)")
    provider: str = Field(default="gemini", description="LLM provider")
    model: str = Field(default="gemini-1.5-flash", description="Model name")
    token_limit: int = Field(default=4000, ge=1, description="Context limit for this character")
```

**GameConfig has summarizer_model:**

```python
# models.py (GameConfig)
class GameConfig(BaseModel):
    combat_mode: Literal["Narrative", "Tactical"] = Field(default="Narrative")
    summarizer_model: str = Field(default="gemini-1.5-flash", description="Model for memory compression")
    party_size: int = Field(default=4, ge=1, le=8, description="Number of player characters")
```

**SUPPORTED_PROVIDERS constant exists:**

```python
# agents.py
SUPPORTED_PROVIDERS: frozenset[str] = frozenset(["gemini", "claude", "ollama"])

DEFAULT_MODELS: dict[str, str] = {
    "gemini": "gemini-1.5-flash",
    "claude": "claude-3-haiku-20240307",
    "ollama": "llama3",
}
```

**Ollama models available from Story 6.2:**

```python
# Available in session state after Ollama validation
st.session_state["ollama_available_models"]  # list[str]
```

### Model Lists by Provider

| Provider | Models |
|----------|--------|
| Gemini | gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash |
| Claude | claude-3-haiku-20240307, claude-3-5-sonnet-20241022, claude-sonnet-4-20250514 |
| Ollama | Dynamic from server, or fallback: llama3, mistral, phi3 |

### Session State Keys

**New keys for this story:**

| Key | Type | Purpose |
|-----|------|---------|
| `agent_model_overrides` | `dict[str, dict[str, str]]` | Per-agent provider/model overrides |
| `model_config_changed` | `bool` | Track if model configs changed (distinct from API keys) |

**Example agent_model_overrides structure:**

```python
{
    "dm": {"provider": "gemini", "model": "gemini-1.5-pro"},
    "theron": {"provider": "claude", "model": "claude-3-haiku-20240307"},
    "shadowmere": {"provider": "ollama", "model": "llama3"},
    "lyra": {"provider": "gemini", "model": "gemini-1.5-flash"},
    "brother aldric": {"provider": "gemini", "model": "gemini-1.5-flash"},
    "summarizer": {"provider": "gemini", "model": "gemini-1.5-flash"},
}
```

### Agent Row Component Structure

```
+------------------------------------------------------------------------+
| [Color] Agent Name    | Provider [v] | Model [v]      | Status Badge   |
+------------------------------------------------------------------------+
```

Example rows:
```
+------------------------------------------------------------------------+
| [Gold] Dungeon Master | Gemini [v]   | gemini-1.5-flash [v] | Active   |
+------------------------------------------------------------------------+
| [Red] Theron          | Gemini [v]   | gemini-1.5-flash [v] | AI       |
+------------------------------------------------------------------------+
| [Green] Shadowmere    | Claude [v]   | claude-3-haiku [v]   | You      |
+------------------------------------------------------------------------+
| [Purple] Lyra         | Ollama [v]   | llama3 [v]           | AI       |
+------------------------------------------------------------------------+
| [Blue] Brother Aldric | Gemini [v]   | gemini-1.5-flash [v] | AI       |
+------------------------------------------------------------------------+
| --- |
+------------------------------------------------------------------------+
| Summarizer            | Gemini [v]   | gemini-1.5-flash [v] |          |
+------------------------------------------------------------------------+
```

### Status Indicator Logic

```python
def get_agent_status(agent_key: str, game: GameState) -> str:
    """Determine status for an agent.

    Returns:
        "Active" if this agent's turn
        "You" if human controls this agent
        "AI" otherwise
    """
    if st.session_state.get("controlled_character") == agent_key:
        return "You"
    if game.get("current_turn") == agent_key:
        return "Active"
    return "AI"
```

### Provider Change Handler

```python
def handle_provider_change(agent_key: str, new_provider: str) -> None:
    """Handle provider dropdown change.

    Resets model to first available for the new provider.
    """
    # Get first available model for new provider
    models = get_available_models(new_provider)
    default_model = models[0] if models else DEFAULT_MODELS.get(new_provider, "")

    # Update overrides
    overrides = st.session_state.get("agent_model_overrides", {})
    overrides[agent_key] = {"provider": new_provider, "model": default_model}
    st.session_state["agent_model_overrides"] = overrides

    mark_config_changed()
```

### Quick Actions

**Copy DM to all PCs:**

```python
def handle_copy_dm_to_pcs() -> None:
    """Copy DM's provider/model to all PC agents."""
    overrides = st.session_state.get("agent_model_overrides", {})
    dm_config = overrides.get("dm", {})

    if not dm_config:
        # Fall back to current game state
        game = st.session_state.get("game", {})
        dm = game.get("dm_config", DMConfig())
        dm_config = {"provider": dm.provider, "model": dm.model}

    # Apply to all PCs (not Summarizer)
    characters = st.session_state.get("game", {}).get("characters", {})
    for agent_key in characters.keys():
        overrides[agent_key] = dm_config.copy()

    st.session_state["agent_model_overrides"] = overrides
    mark_config_changed()
```

**Reset to defaults:**

```python
def handle_reset_model_defaults() -> None:
    """Reset all agents to YAML defaults."""
    # Clear all overrides
    st.session_state["agent_model_overrides"] = {}
    mark_config_changed()
```

### Applying Changes to Game State

When Save is clicked:

```python
def apply_model_config_changes() -> None:
    """Apply model config overrides to game state.

    Changes take effect on the NEXT turn, not immediately.
    This is by design - we don't want to switch models mid-turn.
    """
    overrides = st.session_state.get("agent_model_overrides", {})
    game: GameState = st.session_state.get("game", {})

    # Update DM config
    if "dm" in overrides:
        dm_override = overrides["dm"]
        game["dm_config"] = game["dm_config"].model_copy(update={
            "provider": dm_override.get("provider", game["dm_config"].provider),
            "model": dm_override.get("model", game["dm_config"].model),
        })

    # Update character configs
    for agent_key, config in game.get("characters", {}).items():
        if agent_key in overrides:
            char_override = overrides[agent_key]
            game["characters"][agent_key] = config.model_copy(update={
                "provider": char_override.get("provider", config.provider),
                "model": char_override.get("model", config.model),
            })

    # Update summarizer config
    if "summarizer" in overrides:
        summ_override = overrides["summarizer"]
        game["game_config"] = game["game_config"].model_copy(update={
            "summarizer_model": summ_override.get("model", game["game_config"].summarizer_model),
        })
        # Note: May need to add summarizer_provider to GameConfig

    st.session_state["game"] = game
```

### GameConfig Update for Summarizer Provider

Add to models.py GameConfig:

```python
class GameConfig(BaseModel):
    combat_mode: Literal["Narrative", "Tactical"] = Field(default="Narrative")
    summarizer_provider: str = Field(default="gemini", description="Provider for memory compression")
    summarizer_model: str = Field(default="gemini-1.5-flash", description="Model for memory compression")
    party_size: int = Field(default=4, ge=1, le=8, description="Number of player characters")
```

### CSS Classes to Add

Add to `styles/theme.css`:

```css
/* Agent Model Grid (Story 6.3) */
.agent-model-grid {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
}

.agent-model-row {
    display: grid;
    grid-template-columns: 1fr 120px 180px 80px;
    gap: var(--space-md);
    align-items: center;
    padding: var(--space-md);
    background: var(--bg-secondary);
    border-radius: 8px;
    border-left: 3px solid var(--text-secondary);
}

.agent-model-row.dm {
    border-left-color: var(--char-dm);
}

.agent-model-row.fighter {
    border-left-color: var(--char-fighter);
}

.agent-model-row.rogue {
    border-left-color: var(--char-rogue);
}

.agent-model-row.wizard {
    border-left-color: var(--char-wizard);
}

.agent-model-row.cleric {
    border-left-color: var(--char-cleric);
}

.agent-model-row.summarizer {
    border-left-color: var(--text-secondary);
    opacity: 0.9;
}

.agent-model-name {
    font-family: var(--font-ui);
    font-size: 14px;
    font-weight: 600;
}

.agent-model-name.dm { color: var(--char-dm); }
.agent-model-name.fighter { color: var(--char-fighter); }
.agent-model-name.rogue { color: var(--char-rogue); }
.agent-model-name.wizard { color: var(--char-wizard); }
.agent-model-name.cleric { color: var(--char-cleric); }
.agent-model-name.summarizer { color: var(--text-secondary); }

.agent-status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-family: var(--font-ui);
    font-size: 11px;
    font-weight: 500;
    text-align: center;
}

.agent-status-badge.active {
    background: rgba(232, 168, 73, 0.2);
    color: var(--accent-warm);
}

.agent-status-badge.ai {
    background: rgba(107, 142, 107, 0.2);
    color: var(--char-rogue);
}

.agent-status-badge.you {
    background: rgba(123, 104, 184, 0.2);
    color: var(--char-wizard);
}

.model-quick-actions {
    display: flex;
    gap: var(--space-md);
    margin-top: var(--space-lg);
    padding-top: var(--space-md);
    border-top: 1px solid var(--bg-secondary);
}

.model-separator {
    height: 1px;
    background: var(--bg-secondary);
    margin: var(--space-md) 0;
}
```

### Edge Cases

1. **Ollama not connected**: Show warning, allow selection but with note "Ollama models not verified"
2. **Provider API key missing**: Show warning icon, allow selection but note "API key not configured"
3. **Same model selected for all**: Valid use case, no warning needed
4. **Model not available for provider**: Reset to first available model
5. **Summarizer provider different from agents**: Valid use case, fully supported
6. **Human controlling character**: "You" status updates in real-time as modal is open

### Architecture Compliance

| Pattern | Compliance | Notes |
|---------|------------|-------|
| Session state for UI state | YES | Model overrides in session state |
| CSS via theme.css | YES | All styling in centralized stylesheet |
| Functions with docstrings | YES | All public functions documented |
| Pydantic for models | YES | Uses existing DMConfig, CharacterConfig |
| Config hierarchy | YES | YAML defaults -> overrides |

### Performance Considerations

- Model lists are static (except Ollama) - no API calls on dropdown change
- State updates are lightweight (dict operations)
- No mid-turn model switching prevents race conditions

### What This Story Implements

1. Per-agent provider/model selection in the Models tab
2. Dynamic model dropdowns based on provider
3. Summarizer configuration (independent of agents)
4. Quick actions: Copy DM to PCs, Reset to defaults
5. Status indicators (Active/AI/You)
6. Integration with game state for next-turn application

### What This Story Does NOT Implement

- Context limit configuration (Story 6.4)
- Mid-turn provider switching (Story 6.5 handles transitions)
- Persisting changes to YAML files (session-only by design)

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR42 | Select DM LLM provider | DM row with provider/model dropdowns |
| FR43 | Select PC LLM providers | PC rows with provider/model dropdowns |
| FR44 | Select summarization model | Summarizer row with provider/model dropdowns |

### Testing Strategy

**Unit Tests (pytest):**
- Agent row rendering in different states
- Provider-to-model mapping
- Status indicator logic
- Quick action handlers
- Change detection with model configs

**Integration Tests (pytest + mock):**
- Full model selection flow
- State propagation to game state
- Save/apply behavior
- Copy DM to PCs action

**Visual Tests (chrome-devtools MCP):**
- Grid layout and spacing
- Character color borders
- Status badge styling
- Dropdown appearance

### Files to Modify

| File | Changes |
|------|---------|
| `app.py` | Replace Models tab placeholder with grid, add handlers, update save logic |
| `config.py` | Add `get_available_models()` function |
| `models.py` | Add `summarizer_provider` to GameConfig |
| `styles/theme.css` | Add agent model grid CSS classes |

### Files to Create

None - all code goes in existing files.

### Dependencies

- Story 6.1 (Configuration Modal Structure) - COMPLETE
- Story 6.2 (API Key Management UI) - COMPLETE (provides ollama_available_models)
- Streamlit 1.40.0+ (for st.dialog, st.selectbox)

### References

- [Source: planning-artifacts/prd.md#LLM Configuration FR42-FR44]
- [Source: planning-artifacts/architecture.md#LLM Provider Abstraction]
- [Source: planning-artifacts/architecture.md#Configuration Hierarchy]
- [Source: planning-artifacts/epics.md#Story 6.3]
- [Source: app.py#render_config_modal] - Tab structure to populate
- [Source: models.py#DMConfig] - DM provider/model fields
- [Source: models.py#CharacterConfig] - PC provider/model fields
- [Source: models.py#GameConfig] - summarizer_model field
- [Source: agents.py#SUPPORTED_PROVIDERS] - Provider list
- [Source: agents.py#DEFAULT_MODELS] - Default model per provider
- [Source: config/defaults.yaml] - Default configuration values

---

## Dev Agent Record

### File List

| File | Changes |
|------|---------|
| `app.py` | Added Story 6.3 implementation: render_models_tab, render_agent_model_row, handle_provider_change, handle_model_change, handle_copy_dm_to_pcs, handle_reset_model_defaults, apply_model_config_changes, get_agent_status, get_current_agent_model, render_status_badge. Added PROVIDER_OPTIONS, PROVIDER_KEYS, PROVIDER_DISPLAY constants. Updated snapshot_config_values to include model overrides. |
| `config.py` | Added get_available_models() function, GEMINI_MODELS, CLAUDE_MODELS, OLLAMA_FALLBACK_MODELS constants. |
| `models.py` | Added summarizer_provider field to GameConfig model. |
| `styles/theme.css` | Added Agent Model Selection UI CSS classes: .agent-model-grid, .agent-model-row, .agent-model-name, .agent-status-badge, .model-quick-actions, .model-separator, .models-section-header, .model-help-text. |
| `tests/test_story_6_3_model_selection.py` | Created comprehensive test suite with 42 tests covering all ACs. |

---

## Senior Developer Review (AI)

**Review Date:** 2026-01-28
**Reviewer:** Claude Opus 4.5

### Issues Found: 7 total (2 HIGH, 3 MEDIUM, 2 LOW)

#### HIGH Severity (Auto-Fixed)

1. **Missing validation in handle_provider_change() - Potential IndexError**
   - Location: `app.py:1647`
   - Issue: When `get_available_models()` returns empty list, `models[0]` would raise IndexError
   - Fix: Added fallback to `DEFAULT_MODELS.get(new_provider)` when models list is empty

2. **Missing input validation on agent_key parameters**
   - Location: `app.py:1552, 1605, 1647, 1672, 1739`
   - Issue: Functions don't validate that `agent_key` is a non-empty string
   - Fix: Added input validation at start of `get_agent_status()`, `get_current_agent_model()`, `handle_provider_change()`, `handle_model_change()` - return safe defaults for invalid input

#### MEDIUM Severity (Auto-Fixed)

3. **HTML injection risk in render_agent_model_row() - Incomplete escaping**
   - Location: `app.py:1739`
   - Issue: `css_class` variable directly interpolated into HTML without sanitization
   - Fix: Added sanitization to only allow alphanumeric chars and hyphens in css_class

4. **Test file missing edge case tests**
   - Location: `tests/test_story_6_3_model_selection.py`
   - Issue: No tests for empty/None agent_key, empty models list
   - Fix: Added `TestEdgeCases` class with 7 new edge case tests

5. **Missing docstring for PROVIDER_OPTIONS constants**
   - Location: `app.py:1534-1549`
   - Issue: Module-level constants lack documentation
   - Fix: Added inline documentation explaining the purpose and relationship of PROVIDER_OPTIONS, PROVIDER_KEYS, PROVIDER_DISPLAY

#### LOW Severity (Documented, Not Fixed)

6. **Inconsistent status badge text cases**
   - Location: `app.py:1552`
   - Issue: Status returns "Active", "You", "AI" - "AI" is all-caps while others are capitalized
   - Decision: Not fixed - this is intentional UI design choice for abbreviation

7. **Pre-existing pyright issues in config.py and models.py**
   - Location: `config.py:390+`, `models.py:16`
   - Issue: google.generativeai import issues and datetime.UTC
   - Decision: Not fixed - pre-existing issues unrelated to this story

### Test Results

- All 42 Story 6.3 tests pass
- All 2239 project tests pass
- Linting (ruff) passes
- No regressions introduced

### Verification Checklist

- [x] All Acceptance Criteria implemented and tested
- [x] All Tasks marked [x] verified as complete
- [x] Code quality issues fixed
- [x] Test coverage includes edge cases
- [x] Security vulnerabilities addressed (HTML injection)
- [x] Architecture compliance verified

### Outcome: APPROVED

All HIGH and MEDIUM severity issues have been fixed. Story implementation is complete and ready for merge.

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-28 | Story created via create-story workflow | Claude Opus 4.5 |
| 2026-01-28 | Implementation complete, status changed to review | Claude Opus 4.5 |
| 2026-01-28 | Code review completed - 5 issues auto-fixed, APPROVED | Claude Opus 4.5 |
