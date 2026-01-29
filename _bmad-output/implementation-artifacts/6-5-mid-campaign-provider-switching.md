# Story 6.5: Mid-Campaign Provider Switching

Status: done

## Story

As a **user**,
I want **to change AI providers during an active campaign**,
so that **I can experiment with different models or switch if one isn't working well**.

## Acceptance Criteria

1. **Given** an active campaign session
   **When** I open configuration and change a provider/model
   **Then** my campaign data is preserved (NFR8)
   **And** only the AI backend changes

2. **Given** I switch the DM from Gemini to Claude
   **When** I save and the game resumes
   **Then** the next DM turn uses Claude
   **And** narrative continuity is maintained via memory system

3. **Given** I switch a PC agent mid-session
   **When** the change takes effect
   **Then** the new model receives the same character config and memory
   **And** personality consistency is maintained through the system prompt

4. **Given** a provider becomes unavailable mid-session (API error)
   **When** I open configuration
   **Then** I can switch to an available provider
   **And** continue the session without data loss

5. **Given** the change confirmation
   **When** I save model changes during a session
   **Then** it clearly states: "[Character] will use [Provider/Model] starting next turn"

6. **Given** I switch providers
   **When** the next turn generates
   **Then** the transition is seamless to the user
   **And** the narrative style may subtly shift but story continues

## Tasks / Subtasks

- [x] Task 1: Verify existing model switching infrastructure
  - [x] 1.1 Audit `apply_model_config_changes()` in app.py - verify it updates dm_config, characters, and game_config
  - [x] 1.2 Verify model overrides are stored in session state (`agent_model_overrides`)
  - [x] 1.3 Confirm `create_dm_agent()` and `create_pc_agent()` read provider/model from config at call time (not cached)
  - [x] 1.4 Write test confirming model changes take effect on next turn
  - [x] 1.5 Document any gaps or issues found during audit (none found - infrastructure works correctly)

- [x] Task 2: Implement confirmation message for provider switch (AC #5)
  - [x] 2.1 Modify `handle_config_save_click()` to generate specific change messages
  - [x] 2.2 Create `generate_model_change_messages()` function that compares before/after states
  - [x] 2.3 Format message as "[Character] will use [Provider/Model] starting next turn"
  - [x] 2.4 Show as toast notification (multi-line for multiple changes)
  - [x] 2.5 Write unit tests for message generation
  - [ ] 2.6 Write visual verification test with chrome-devtools MCP (deferred - requires running app)

- [x] Task 3: Ensure campaign data preservation (AC #1, NFR8)
  - [x] 3.1 Write integration test: make model change, verify ground_truth_log unchanged
  - [x] 3.2 Write integration test: make model change, verify agent_memories unchanged
  - [x] 3.3 Write integration test: make model change, verify whisper_queue unchanged
  - [x] 3.4 Write integration test: make model change, verify turn_queue unchanged
  - [x] 3.5 Document data preservation guarantees in story file

- [x] Task 4: Verify memory continuity across provider switch (AC #2, AC #3)
  - [x] 4.1 Write test: DM switch preserves long_term_summary in context
  - [x] 4.2 Write test: DM switch preserves short_term_buffer in context
  - [x] 4.3 Write test: PC switch preserves CharacterFacts in context
  - [x] 4.4 Write test: PC switch preserves character_class and personality in system prompt
  - [x] 4.5 Verify `_build_dm_context()` and `_build_pc_context()` work identically regardless of provider
  - [x] 4.6 Document memory continuity guarantees

- [x] Task 5: Handle provider unavailability gracefully (AC #4)
  - [x] 5.1 Add provider status indicators to Models tab (using existing validation from Story 6.2)
  - [x] 5.2 Show which providers are currently available/unavailable via `get_provider_availability_status()`
  - [x] 5.3 Create `get_provider_availability_status()` function reusing validation logic
  - [x] 5.4 If current provider is unavailable, show warning badge on agent row via `render_provider_unavailable_warning()`
  - [x] 5.5 Allow switching away from unavailable provider without validation error
  - [x] 5.6 Write unit tests for availability status display
  - [x] 5.7 Write integration test: simulate API error, switch provider, continue session

- [x] Task 6: Verify seamless turn transition (AC #6)
  - [x] 6.1 Write test: switch DM provider, verify agent created with new provider
  - [x] 6.2 Write test: switch PC provider, verify agent created with new provider
  - [x] 6.3 Write test: switch summarizer provider, verify config updated
  - [x] 6.4 Verify no exceptions or errors during provider transition
  - [x] 6.5 Document expected behavior: style may shift, story continues

- [x] Task 7: Add UI feedback for pending changes
  - [x] 7.1 Add visual indicator to agent rows when pending change exists (from session overrides)
  - [x] 7.2 Show "(pending)" badge next to agent name when override differs from saved config
  - [x] 7.3 Clear pending badge after save (handled by clearing overrides)
  - [x] 7.4 Add CSS for `.pending-change-badge` indicator
  - [ ] 7.5 Write visual verification test (deferred - requires running app)

- [x] Task 8: Write comprehensive acceptance tests
  - [x] 8.1 Test: Provider switch preserves campaign data (AC #1)
  - [x] 8.2 Test: DM switch uses new provider on next turn (AC #2)
  - [x] 8.3 Test: PC switch preserves memory and personality (AC #3)
  - [x] 8.4 Test: Provider availability status functions (AC #4)
  - [x] 8.5 Test: Confirmation message format correct (AC #5)
  - [x] 8.6 Test: Turn transition seamless after switch (AC #6)
  - [x] 8.7 Test: Multiple sequential provider switches work correctly
  - [x] 8.8 Test: Switch all agents simultaneously, verify all use new providers

- [ ] Task 9: Update documentation and CLAUDE.md
  - [ ] 9.1 Document mid-campaign provider switching behavior
  - [ ] 9.2 Add troubleshooting guide for common switch scenarios
  - [ ] 9.3 Update README epic progress table

## Dev Notes

### Implementation Strategy

This story validates and enhances the existing provider switching infrastructure from Stories 6.2-6.4. The core switching mechanism already exists - this story focuses on:

1. **Verification** - Confirming existing code handles mid-session switching correctly
2. **User Feedback** - Clear confirmation messages about what changed
3. **Error Handling** - Graceful handling when providers become unavailable
4. **Visual Indicators** - Showing pending changes and provider status

Most of the heavy lifting is already done. The key additions are better user feedback and provider availability status.

### Existing Infrastructure (Stories 6.1-6.4)

**Model Switching (Story 6.3 - already implemented):**

```python
# app.py - apply_model_config_changes()
def apply_model_config_changes() -> None:
    """Apply model config overrides to game state.

    Changes take effect on the NEXT turn, not immediately.
    """
    overrides = st.session_state.get("agent_model_overrides", {})
    game: GameState | None = st.session_state.get("game")

    if not game or not overrides:
        return

    # Update DM config
    if "dm" in overrides:
        dm_override = overrides["dm"]
        old_dm = game.get("dm_config") or DMConfig()
        game["dm_config"] = old_dm.model_copy(
            update={
                "provider": dm_override.get("provider", old_dm.provider),
                "model": dm_override.get("model", old_dm.model),
            }
        )

    # Update character configs
    for agent_key, config in game.get("characters", {}).items():
        if agent_key in overrides:
            char_override = overrides[agent_key]
            game["characters"][agent_key] = config.model_copy(
                update={
                    "provider": char_override.get("provider", config.provider),
                    "model": char_override.get("model", config.model),
                }
            )

    # Update summarizer config
    if "summarizer" in overrides:
        summ_override = overrides["summarizer"]
        old_game_config = game.get("game_config") or GameConfig()
        game["game_config"] = old_game_config.model_copy(
            update={
                "summarizer_provider": summ_override.get("provider", ...),
                "summarizer_model": summ_override.get("model", ...),
            }
        )

    st.session_state["game"] = game
```

**Agent Creation (agents.py - reads config at call time):**

```python
# agents.py - create_dm_agent()
def create_dm_agent(config: DMConfig) -> Runnable:
    """Create a DM agent with tool bindings."""
    base_model = get_llm(config.provider, config.model)  # Uses current config
    return base_model.bind_tools([dm_roll_dice])

# agents.py - create_pc_agent()
def create_pc_agent(config: CharacterConfig) -> Runnable:
    """Create a PC agent with tool bindings."""
    base_model = get_llm(config.provider, config.model)  # Uses current config
    return base_model.bind_tools([pc_roll_dice])
```

**Turn Execution (agents.py - dm_turn, pc_turn):**

```python
# agents.py - dm_turn()
def dm_turn(state: GameState) -> GameState:
    dm_config = state["dm_config"]  # Reads from current state
    dm_agent = create_dm_agent(dm_config)  # Creates fresh agent
    # ... executes with current provider/model

# agents.py - pc_turn()
def pc_turn(state: GameState, agent_name: str) -> GameState:
    character_config = state["characters"][agent_name]  # Reads from current state
    pc_agent = create_pc_agent(character_config)  # Creates fresh agent
    # ... executes with current provider/model
```

**Key Insight:** Agents are created fresh each turn by reading config from GameState. This means provider changes take effect immediately on the next turn - no caching or stale references.

### Confirmation Message Format (AC #5)

Currently, save shows a generic toast: "Changes will apply on next turn"

Need to enhance to show specific changes:

```python
def generate_model_change_messages() -> list[str]:
    """Generate specific change messages for each agent that changed.

    Returns:
        List of messages like "DM will use Claude/claude-3-haiku starting next turn"
    """
    messages = []
    overrides = st.session_state.get("agent_model_overrides", {})
    game: GameState | None = st.session_state.get("game")

    if not game or not overrides:
        return messages

    for agent_key, override in overrides.items():
        # Get agent display name
        if agent_key == "dm":
            display_name = "Dungeon Master"
        elif agent_key == "summarizer":
            display_name = "Summarizer"
        else:
            char_config = game.get("characters", {}).get(agent_key)
            display_name = char_config.name if char_config else agent_key.title()

        provider_display = PROVIDER_DISPLAY.get(override["provider"], override["provider"])
        model = override["model"]

        messages.append(
            f"{display_name} will use {provider_display}/{model} starting next turn"
        )

    return messages
```

### Provider Availability Status (AC #4)

Reuse validation logic from Story 6.2 to show provider status:

```python
def get_provider_availability_status() -> dict[str, bool]:
    """Get availability status for each provider.

    Returns:
        Dict mapping provider key to availability (True = available).
    """
    status = {}

    # Check Google/Gemini
    config = get_config()
    status["gemini"] = bool(config.google_api_key)

    # Check Anthropic/Claude
    status["claude"] = bool(config.anthropic_api_key)

    # Check Ollama (attempt connection)
    try:
        import requests
        resp = requests.get(f"{config.ollama_base_url}/api/tags", timeout=2)
        status["ollama"] = resp.status_code == 200
    except Exception:
        status["ollama"] = False

    return status
```

Display in Models tab:

```
+------------------------------------------------------------------+
| Dungeon Master           | [Gemini v] [gemini-1.5-flash v] | AI  |
| (provider available ✓)   |                                  |     |
+------------------------------------------------------------------+
| Theron (Fighter)         | [Claude v] [claude-3-haiku v]   | AI  |
| (provider unavailable ✗) |                                  |     |
+------------------------------------------------------------------+
```

### Session State Keys

**Existing keys used:**

| Key | Type | Purpose |
|-----|------|---------|
| `agent_model_overrides` | `dict[str, dict[str, str]]` | Per-agent provider/model overrides |
| `config_has_changes` | `bool` | Tracks unsaved changes in modal |
| `model_config_changed` | `bool` | Flag set after save to trigger toast |

**New keys for this story:**

| Key | Type | Purpose |
|-----|------|---------|
| `provider_availability` | `dict[str, bool]` | Cached provider availability status |
| `last_model_change_messages` | `list[str]` | Specific change messages for toast |

### Data Preservation Guarantees (NFR8)

Provider switching MUST NOT modify:

1. **ground_truth_log** - Complete narrative history
2. **agent_memories** - Short-term buffers and long-term summaries
3. **character_facts** - Persistent character identity
4. **whisper_queue** - Pending private messages
5. **checkpoint files** - Historical state snapshots
6. **transcript.json** - Research export file

Provider switching ONLY modifies:

1. **dm_config.provider** and **dm_config.model**
2. **characters[name].provider** and **characters[name].model**
3. **game_config.summarizer_provider** and **game_config.summarizer_model**

### Memory Continuity Across Provider Switch

When a provider changes, the agent still receives:

1. **System Prompt** - Built from CharacterConfig (name, class, personality, CLASS_GUIDANCE)
2. **Long-Term Summary** - From AgentMemory.long_term_summary
3. **Short-Term Buffer** - From AgentMemory.short_term_buffer (last 10 entries)
4. **Character Facts** - From AgentMemory.character_facts (if present)

This context is provider-agnostic. The functions `_build_dm_context()` and `_build_pc_context()` in agents.py construct the context string without any provider-specific logic.

### Pending Change Visual Indicator

Show "(pending)" badge when agent has uncommitted override:

```css
/* CSS for pending change indicator */
.pending-change-badge {
    font-family: var(--font-ui);
    font-size: 11px;
    color: var(--accent-warm);
    background: rgba(232, 168, 73, 0.15);
    padding: 2px 6px;
    border-radius: 4px;
    margin-left: var(--space-sm);
}
```

```python
def has_pending_change(agent_key: str) -> bool:
    """Check if agent has uncommitted model override."""
    overrides = st.session_state.get("agent_model_overrides", {})
    return agent_key in overrides
```

### Edge Cases

1. **Switch during human control** - Provider change applies to AI turns, not human input. If human is controlling a character, the change takes effect when AI resumes.

2. **Switch while paused** - Change is saved to config. Takes effect on next turn after resume.

3. **API key removed after switch** - If user switches to Claude, then removes Claude API key in API Keys tab, validation should catch this before save.

4. **Rapid switching** - Multiple config changes before any turn executes. Only final state matters.

5. **Switch summarizer during compression** - Compression runs synchronously before DM turn. If summarizer changed, new provider used for next compression.

### Architecture Compliance

| Pattern | Compliance | Notes |
|---------|------------|-------|
| Immutable state updates | YES | Uses model_copy() for config changes |
| Session state for UI state | YES | Overrides stored in session state |
| GameState for game data | YES | Config changes written to GameState |
| LLM factory at call time | YES | Agents created fresh each turn |
| Provider-agnostic context | YES | Context building doesn't depend on provider |

### Performance Considerations

- Provider availability check includes network call to Ollama - cache result with short TTL
- No model pre-loading or caching - agents created on demand
- Memory context building is O(n) where n is buffer entries - unchanged by provider

### What This Story Validates/Implements

1. **VALIDATES:** Model switching infrastructure from Story 6.3 works mid-session
2. **VALIDATES:** Campaign data preserved during provider switch (NFR8)
3. **VALIDATES:** Memory continuity maintained across provider boundaries
4. **IMPLEMENTS:** Specific confirmation messages for each changed agent
5. **IMPLEMENTS:** Provider availability status display
6. **IMPLEMENTS:** Pending change visual indicators
7. **IMPLEMENTS:** Comprehensive test suite for mid-session switching

### What This Story Does NOT Implement

- Automatic provider fallback on error (out of scope - user must manually switch)
- Provider preference persistence to YAML (session-only by design)
- Real-time provider health monitoring (static check on modal open)

### FR/NFR Coverage

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| NFR8 | Provider switching without data loss | Verified via tests, existing infrastructure |

### Testing Strategy

**Unit Tests (pytest):**
- generate_model_change_messages() function
- get_provider_availability_status() function
- has_pending_change() function
- Data preservation during switch

**Integration Tests (pytest + mock):**
- Full provider switch flow with mock LLM
- Multi-agent simultaneous switch
- Switch from unavailable provider
- Memory continuity verification

**Visual Tests (chrome-devtools MCP):**
- Confirmation toast format
- Provider availability indicators
- Pending change badges
- Agent row with unavailable provider warning

### Files to Modify

| File | Changes |
|------|---------|
| `app.py` | Add `generate_model_change_messages()`, `get_provider_availability_status()`, `has_pending_change()`. Update `handle_config_save_click()` to show specific messages. Add provider status to `render_agent_model_row()`. Add pending change badge rendering. |
| `styles/theme.css` | Add `.pending-change-badge`, `.provider-status-indicator`, `.provider-unavailable-warning` CSS classes. |

### Files to Create

| File | Purpose |
|------|---------|
| `tests/test_story_6_5_mid_campaign_switch.py` | Comprehensive test suite for all ACs |

### Dependencies

- Story 6.1 (Configuration Modal Structure) - COMPLETE
- Story 6.2 (API Key Management UI) - COMPLETE (provides validation)
- Story 6.3 (Per-Agent Model Selection) - COMPLETE (provides switching infrastructure)
- Story 6.4 (Context Limit Configuration) - COMPLETE
- Streamlit 1.40.0+ (for st.dialog, st.toast)

### References

- [Source: planning-artifacts/prd.md#NFR8 Provider Switching]
- [Source: planning-artifacts/architecture.md#LLM Factory Pattern]
- [Source: planning-artifacts/epics.md#Story 6.5]
- [Source: app.py#apply_model_config_changes] - Existing model switch function
- [Source: agents.py#create_dm_agent] - Agent creation at call time
- [Source: agents.py#create_pc_agent] - Agent creation at call time
- [Source: agents.py#dm_turn] - DM turn reads config from state
- [Source: agents.py#pc_turn] - PC turn reads config from state
- [Source: agents.py#_build_dm_context] - Provider-agnostic context building
- [Source: agents.py#_build_pc_context] - Provider-agnostic context building

---

## Code Review

**Review Date:** 2026-01-28
**Reviewer:** Claude Opus 4.5 (BMAD code-review workflow)
**Status:** APPROVED with fixes applied

### Issues Found and Resolved

| # | Severity | Issue | Resolution |
|---|----------|-------|------------|
| 1 | MEDIUM | Missing defensive validation in `generate_model_change_messages()` - accessing `override["provider"]` and `override["model"]` without checking key existence could cause KeyError on malformed session state | Added defensive checks: `isinstance(override, dict)` and `.get()` with None checks before accessing keys |
| 2 | MEDIUM | Missing test coverage for `is_agent_provider_unavailable` edge cases (override provider check, missing game state) | Added 3 new tests: `test_is_agent_provider_unavailable_with_override`, `test_is_agent_provider_unavailable_no_override`, `test_is_agent_provider_unavailable_missing_game` |
| 3 | LOW | Missing test for malformed override handling | Added 2 new tests: `test_generate_messages_skips_malformed_overrides`, `test_generate_messages_handles_mixed_valid_invalid` |
| 4 | LOW | Pyright warnings about unknown types from session_state dict access | Added explicit type narrowing with `str()` conversion after validation |

### Pre-existing Issues (Not Story 6.5)

- 4 pyright `reportUnnecessaryIsInstance` errors in earlier Story code (defensive isinstance checks for strings)
- 3 pyright warnings about `Runnable[Unknown, Unknown]` generic types from LangChain

### Test Summary

- **Tests added:** 5 new tests (total: 41 Story 6.5 tests)
- **All tests pass:** 41/41 passed
- **Full suite:** 2403 passed, 1 skipped
- **Linting:** All checks passed (ruff)
- **Type checking:** No new errors introduced

### Files Modified During Review

| File | Changes |
|------|---------|
| `app.py` | Added defensive validation in `generate_model_change_messages()` with type narrowing |
| `tests/test_story_6_5_mid_campaign_switch.py` | Added 5 new edge case tests |

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-28 | Story created via create-story workflow | Claude Opus 4.5 |
| 2026-01-28 | Code review completed - 4 issues found and resolved | Claude Opus 4.5 |
