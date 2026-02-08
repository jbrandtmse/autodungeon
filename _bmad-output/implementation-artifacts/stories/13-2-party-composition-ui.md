# Story 13.2: Party Composition UI

Status: ready-for-dev

## Story

As a **user**,
I want **to choose which characters join my adventure from preset characters and my character library**,
So that **I can customize my party for each session**.

## Epic

Epic 13: Adventure Setup & Party Management

## Priority

High (blocks Story 13.3; critical integration gap identified during playtesting)

## Estimate

Medium (UI view + wiring + tests)

## Dependencies

- Story 13.1 (Session Naming): **done** -- session name input already lives in `render_module_selection_view()` and must be moved/shared with the new party setup screen.

## Acceptance Criteria

1. **Given** I complete module selection (or choose "Freeform Adventure"), **When** I proceed, **Then** I see a Party Setup screen (new `app_view = "party_setup"`) instead of the game starting immediately.

2. **Given** the Party Setup screen, **When** displayed, **Then** I see:
   - The session name input (carried forward from Story 13.1)
   - A "Preset Characters" section showing all characters from `config/characters/*.yaml` (excluding `dm.yaml`) with select/deselect toggles
   - A "Library Characters" section showing all characters from `config/characters/library/*.yaml` with select/deselect toggles
   - Each character card shows: name, class, and a visual indicator of selected state (color border or highlight)
   - A "Create New Character" button that routes to the character creation wizard
   - A "Back" button that returns to module selection
   - A "Begin Adventure" button to start the game

3. **Given** the party selection, **When** I first arrive at Party Setup, **Then** all preset characters are selected by default (library characters are deselected by default).

4. **Given** I click a character card or its toggle, **When** the toggle changes, **Then** the character is selected or deselected and the visual state updates accordingly.

5. **Given** I have selected at least 1 character, **When** I click "Begin Adventure", **Then** only the selected characters are passed to `populate_game_state()` and the game initializes with my chosen party.

6. **Given** I try to proceed with 0 characters selected, **When** I click "Begin Adventure", **Then** a validation message prevents proceeding: "Select at least one character for your party."

7. **Given** I click "Create New Character", **When** the wizard completes, **Then** I return to the Party Setup screen with the new character available in the Library section and selected.

8. **Given** I click "Back", **When** navigation occurs, **Then** I return to the module selection screen with my module selection preserved and party selection state cleared.

9. **Given** the party setup screen, **When** there are no library characters, **Then** the Library Characters section shows a message like "No characters in library yet" instead of an empty grid.

## Tasks / Subtasks

- [ ] Task 1: Add `"party_setup"` app_view state and routing (AC: #1)
  - [ ] 1.1: Update view state machine comment at `app.py:1691-1700` to document `party_setup` between `module_selection` and `game`
  - [ ] 1.2: Add `elif app_view == "party_setup":` routing block in `main()` at `app.py:~8570` (between `module_selection` and the `else`/game block)
  - [ ] 1.3: In that block, call `st.title("autodungeon")` then `render_party_setup_view()`
  - [ ] 1.4: Add `"party_setup"` to the `# Valid views:` comment at `app.py:8537`

- [ ] Task 2: Modify module selection confirmation to route to party setup instead of game (AC: #1)
  - [ ] 2.1: In `render_module_selection_view()` at `app.py:8295-8300`, change the `module_selection_confirmed` handler: instead of calling `handle_new_session_click()` and `clear_module_discovery_state()`, set `app_view = "party_setup"` and `st.rerun()`
  - [ ] 2.2: Do NOT call `clear_module_discovery_state()` at this transition -- module state (selected_module, new_session_name) must survive into party setup
  - [ ] 2.3: Move the session name `st.text_input` from `render_module_selection_view()` to `render_party_setup_view()` (it belongs on the party setup screen per UX spec and epic definition)

- [ ] Task 3: Create `render_party_setup_view()` function (AC: #2, #3, #8, #9)
  - [ ] 3.1: Add function in `app.py` near the other adventure flow functions (~line 8260 area)
  - [ ] 3.2: Render step header: `'<h1 class="step-header">Step 2: Assemble Your Party</h1>'`
  - [ ] 3.3: Render caption with selected module name (or "Freeform Adventure")
  - [ ] 3.4: Render session name text input (moved from Story 13.1's placement in module selection view); use same session state key `"new_session_name"` and widget key pattern
  - [ ] 3.5: Load preset characters using `load_character_configs()` from `config.py`
  - [ ] 3.6: Load library characters using `list_library_characters()` (already in `app.py:5613`)
  - [ ] 3.7: Initialize party selection state in `st.session_state["party_selection"]` as a dict `{char_key: bool}` -- preset chars default `True`, library chars default `False`
  - [ ] 3.8: Render "Preset Characters" section header
  - [ ] 3.9: Render preset character cards in a grid (2-3 columns using `st.columns`)
  - [ ] 3.10: Render "Library Characters" section header
  - [ ] 3.11: Render library character cards in a grid, or "No characters in library yet" message if empty
  - [ ] 3.12: Render "Create New Character" button
  - [ ] 3.13: Render "Back to Module Selection" button
  - [ ] 3.14: Render "Begin Adventure" button with party size validation

- [ ] Task 4: Create `render_party_character_card()` helper function (AC: #2, #4)
  - [ ] 4.1: Accept parameters: `name`, `char_class`, `color`, `card_key`, `is_selected`
  - [ ] 4.2: Render a card with character name, class, and color-coded border
  - [ ] 4.3: Use `st.checkbox` for select/deselect toggle, keyed with `card_key`
  - [ ] 4.4: Visual distinction between selected (full-color border, opaque background) and deselected (dimmed border, semi-transparent)
  - [ ] 4.5: Use `escape_html()` on name and class for XSS protection

- [ ] Task 5: Implement "Begin Adventure" flow (AC: #5, #6)
  - [ ] 5.1: Count selected characters from `st.session_state["party_selection"]`
  - [ ] 5.2: If 0 selected, show `st.warning("Select at least one character for your party.")`
  - [ ] 5.3: If >= 1 selected, call `handle_new_session_click()` with the selected character set
  - [ ] 5.4: Modify `handle_new_session_click()` to accept an optional `selected_characters` parameter (list of character keys to include)
  - [ ] 5.5: Modify `populate_game_state()` to accept an optional `selected_characters` parameter and filter `load_character_configs()` result to only include those keys
  - [ ] 5.6: For library characters, convert their YAML data to `CharacterConfig` instances so they can be included in the characters dict
  - [ ] 5.7: After game start, clear party setup session state

- [ ] Task 6: Implement "Create New Character" flow from party setup (AC: #7)
  - [ ] 6.1: On button click, store `st.session_state["party_setup_return"] = True` to flag return destination
  - [ ] 6.2: Initialize wizard state (same pattern as session browser wizard button at `app.py:8491-8496`)
  - [ ] 6.3: Set `app_view = "character_wizard"` and `st.rerun()`
  - [ ] 6.4: In `main()` wizard completion handler (`app.py:8554-8561`), check for `party_setup_return` flag
  - [ ] 6.5: If flag is set, return to `app_view = "party_setup"` instead of `session_browser`
  - [ ] 6.6: Clear `party_setup_return` flag after use

- [ ] Task 7: Implement "Back" navigation (AC: #8)
  - [ ] 7.1: On "Back to Module Selection" button click, set `app_view = "module_selection"` and clear party selection state
  - [ ] 7.2: Preserve `selected_module` and `module_selection_confirmed = False` so user can re-select
  - [ ] 7.3: Clear `party_selection` from session state

- [ ] Task 8: Add `clear_party_setup_state()` utility function
  - [ ] 8.1: Clear `party_selection`, `party_setup_return` from session state
  - [ ] 8.2: Call from `handle_new_session_click()` after successful game start
  - [ ] 8.3: Call from back-to-module-selection navigation

- [ ] Task 9: Write tests (AC: #1-9)
  - [ ] 9.1: Test module selection confirmation routes to `party_setup` (not directly to game)
  - [ ] 9.2: Test preset characters loaded and displayed
  - [ ] 9.3: Test library characters loaded and displayed
  - [ ] 9.4: Test preset characters selected by default, library characters deselected
  - [ ] 9.5: Test character select/deselect toggles update state
  - [ ] 9.6: Test "Begin Adventure" with valid selection calls `handle_new_session_click()`
  - [ ] 9.7: Test "Begin Adventure" with 0 selected shows validation warning
  - [ ] 9.8: Test "Create New Character" navigates to wizard with return flag
  - [ ] 9.9: Test wizard completion returns to party_setup when flag is set
  - [ ] 9.10: Test "Back" navigation returns to module selection
  - [ ] 9.11: Test party selection state cleared after game start
  - [ ] 9.12: Test `populate_game_state()` with `selected_characters` parameter filters correctly
  - [ ] 9.13: Test library character converted to CharacterConfig for game state
  - [ ] 9.14: Test empty library shows informational message
  - [ ] 9.15: Test XSS resilience: HTML in character names escaped in cards
  - [ ] 9.16: Test session name input present on party setup screen
  - [ ] 9.17: Test session name persists across module selection -> party setup transition

## Dev Notes

### Current Adventure Flow (Before This Story)

```
session_browser --> module_selection --> game
                                    ^
                              (direct jump, no party setup)
```

The flow after this story will be:

```
session_browser --> module_selection --> party_setup --> game
                        |                   |
                        +-> session_browser  +-> module_selection (back)
                        (cancel/back)        +-> character_wizard (create new char)
```

### Key Code Locations

**View routing (`app.py:8536-8574`):** The `main()` function routes based on `app_view`. Add `"party_setup"` as a new branch between `module_selection` and the default `game` case. The existing valid views are: `session_browser`, `module_selection`, `character_wizard`, `character_library`, `game`.

**Module selection confirmation (`app.py:8295-8300`):**
```python
# CURRENT CODE (to be modified):
if st.session_state.get("module_selection_confirmed"):
    # Proceed to game initialization
    handle_new_session_click()  # Already handles selected_module (Story 7.3)
    clear_module_discovery_state()  # Cleanup
    st.rerun()
    return
```
Change this to route to `party_setup` instead of calling `handle_new_session_click()` directly. Do NOT call `clear_module_discovery_state()` here -- the selected module and session name must survive into party setup.

**Session name input (`app.py:8278-8286`):** Currently in `render_module_selection_view()`. Move this to `render_party_setup_view()`. The session name should be entered on the party setup screen, not the module selection screen. This changes the Story 13.1 placement but keeps the same session state key `"new_session_name"` and the same `handle_new_session_click()` wiring.

**`handle_new_session_click()` (`app.py:8306-8364`):** Currently calls `populate_game_state()` which loads ALL preset characters. Must be modified to:
1. Accept selected character keys
2. Pass them to `populate_game_state()`
3. Handle library characters alongside preset characters

**`populate_game_state()` (`models.py:2007-2081`):** Currently calls `load_character_configs()` which loads ALL preset characters. Must be extended with a `selected_characters` parameter to filter. For library characters, the caller will need to pass pre-built `CharacterConfig` instances.

**Character loading functions:**
- `load_character_configs()` (`config.py:202-253`) -- loads `config/characters/*.yaml` (excluding `dm.yaml`), returns `dict[str, CharacterConfig]` keyed by lowercase name
- `list_library_characters()` (`app.py:5613-5646`) -- loads `config/characters/library/*.yaml`, returns `list[dict[str, Any]]` with raw YAML data + `_filename` and `_filepath` metadata

**Library character data format** (example from `config/characters/library/eden.yaml`):
```yaml
name: Eden
race: Elf
class: Warlock
background: Sage
personality: A mysterious adventurer.
color: '#4B0082'
provider: claude
model: claude-3-haiku-20240307
token_limit: 4000
abilities:
  strength: 8
  ...
```
This has `class` (not `character_class`) -- the same YAML-to-Pydantic mapping in `load_character_configs()` handles this with `data["character_class"] = data.pop("class")`. Reuse this pattern when converting library characters to `CharacterConfig`.

**Wizard return destination (`app.py:8554-8561`):**
```python
# CURRENT CODE:
if not st.session_state.get("wizard_active", False):
    # Return to library if we were editing, otherwise session browser
    if st.session_state.get("library_editing"):
        del st.session_state["library_editing"]
        st.session_state["app_view"] = "character_library"
    else:
        st.session_state["app_view"] = "session_browser"
    st.rerun()
```
Add a new check: `elif st.session_state.get("party_setup_return"): ...` to return to `party_setup` instead.

### View State Machine

Update the comment at `app.py:1691-1700`:
```python
# App view routing (Story 4.3, 7.4, 13.2)
# View state machine:
#   session_browser -> module_selection -> party_setup -> game
#                          |                   |
#                          +-> session_browser  +-> module_selection (back)
#                          (cancel/back)        +-> character_wizard (create char)
#
# Valid app_view values:
#   - "session_browser": List of sessions, "New Adventure" button
#   - "module_selection": Module discovery loading, grid selection UI (Story 7.4)
#   - "party_setup": Party composition selection (Story 13.2)
#   - "character_wizard": Character creation wizard (Story 9.1)
#   - "character_library": Character library management (Story 9.4)
#   - "game": Active game view with narrative, controls, etc.
```

### Session State Keys

| Key | Type | Purpose |
|-----|------|---------|
| `party_selection` | `dict[str, bool]` | Character key -> selected state. Keys are `"preset:{lowercase_name}"` for presets, `"library:{filename}"` for library chars. |
| `party_setup_return` | `bool` | Flag to return to party_setup after wizard completion |
| `new_session_name` | `str` | Session name (from Story 13.1, moved from module selection) |
| `selected_module` | `ModuleInfo \| None` | Preserved from module selection step |

### Character Key Convention

To avoid name collisions between preset and library characters (e.g., both could have a "Shadowmere"), use namespaced keys:
- Preset characters: `"preset:shadowmere"` (using lowercase name from `load_character_configs()`)
- Library characters: `"library:eden.yaml"` (using filename from `list_library_characters()`)

### CSS / Theming Guidance

Follow the existing campfire theme patterns. Character cards should use:
- The character's `color` field for border accent
- Dark background matching `.module-card` pattern from Story 7.2
- Selected state: full opacity, prominent border
- Deselected state: reduced opacity (~0.5), dimmed border

Reference the existing `render_character_library_card()` at `app.py:5748-5801` for card styling patterns (inline styles with character color border).

The step header should reuse the `.step-header` CSS class already used in `render_module_selection_view()`.

### Converting Library Characters to CharacterConfig

Library characters have extra fields (`race`, `background`, `abilities`, `skills`, `equipment`) that `CharacterConfig` does not include. When converting:
1. Extract only the fields `CharacterConfig` needs: `name`, `character_class` (mapped from `class`), `personality`, `color`, `provider`, `model`, `token_limit`
2. Use the same `class` -> `character_class` mapping from `load_character_configs()`
3. Create `CharacterConfig(**filtered_data)`
4. The extra library data (abilities, skills, equipment) will be used by Story 13.3 for character sheet initialization -- that is out of scope for this story

### Modifying `populate_game_state()` Signature

Add an optional `characters_override` parameter:

```python
def populate_game_state(
    include_sample_messages: bool = True,
    selected_module: ModuleInfo | None = None,
    characters_override: dict[str, CharacterConfig] | None = None,
) -> GameState:
```

When `characters_override` is provided, use it directly instead of calling `load_character_configs()`. This way `handle_new_session_click()` can build the filtered character dict (preset + library) and pass it in.

### Party Size Validation

- **Minimum:** 1 character (enforced by UI validation before game start)
- **Maximum:** No hard cap enforced by this story. The system already supports N characters. The UI will naturally limit by showing only available characters.
- FR9 says "1-N, default 4" -- preset characters being selected by default gives 4 as the default.

### Error Handling

- If `load_character_configs()` fails (e.g., malformed YAML), show `st.error()` with the error message
- If `list_library_characters()` returns empty, show informational message (not an error)
- If `CharacterConfig` construction from library data fails (e.g., missing required fields), skip that character and show a warning

### Security Considerations

- Use `escape_html()` (imported from `html` module at `app.py:25`) on all character names and class strings rendered in HTML
- Library character data comes from user-created YAML files which could contain malicious strings
- Follow the same XSS protection pattern used throughout the codebase

## Test Guidance

### Test File

Create `tests/test_story_13_2_party_composition_ui.py` following the project naming convention.

### Test Patterns

Reference test patterns from:
- `tests/test_story_13_1_session_naming.py` -- mocking Streamlit session state, verifying state transitions
- `tests/test_story_7_4_new_adventure_flow.py` -- mocking adventure flow functions, `handle_new_session_click()`

### Key Test Scenarios

**Routing tests:**
- Module selection confirmation sets `app_view = "party_setup"` (not `"game"`)
- Party setup "Begin Adventure" transitions to `"game"`
- Party setup "Back" transitions to `"module_selection"`
- Wizard return with `party_setup_return` flag goes to `"party_setup"`

**Character loading tests:**
- Preset characters loaded from `load_character_configs()`
- Library characters loaded from `list_library_characters()`
- Preset characters selected by default
- Library characters deselected by default

**Selection tests:**
- Toggle select/deselect updates `party_selection` state
- Multiple characters can be selected
- All characters can be deselected

**Validation tests:**
- 0 selected characters: warning shown, game does not start
- 1+ selected characters: game starts successfully

**Integration tests:**
- Selected characters passed to `populate_game_state()` via `characters_override`
- Library character successfully converted to `CharacterConfig`
- Session name preserved across module_selection -> party_setup transition
- Party selection state cleared after game start

**XSS tests:**
- Character name with HTML tags is escaped in card rendering

### Mocking Strategy

- Mock `load_character_configs()` to return test fixture characters
- Mock `list_library_characters()` to return test fixture library data
- Mock `st.session_state` as a dict
- Mock `st.checkbox`, `st.button`, `st.text_input` for widget interaction tests
- Mock `create_new_session` to verify it receives correct parameters
- Mock `populate_game_state` to verify `characters_override` parameter

## References

- [Source: app.py#render_module_selection_view ~line 8261] - Module selection view to modify
- [Source: app.py#handle_new_session_click ~line 8306] - Session creation to modify
- [Source: app.py#main ~line 8536] - View routing to extend
- [Source: app.py#initialize_session_state ~line 1691] - State machine docs to update
- [Source: app.py#clear_module_discovery_state ~line 7870] - State cleanup pattern
- [Source: app.py#list_library_characters ~line 5613] - Library character loading
- [Source: app.py#render_character_library_card ~line 5748] - Card rendering pattern
- [Source: app.py#get_default_wizard_data ~line 5143] - Wizard initialization pattern
- [Source: config.py#load_character_configs ~line 202] - Preset character loading
- [Source: models.py#populate_game_state ~line 2007] - Game state factory
- [Source: models.py#CharacterConfig ~line 165] - Character config model
- [Source: _bmad-output/planning-artifacts/epics-v1.1.md#Story 13.2] - Epic requirements
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-08.md#CP-3] - Change proposal
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md#Flow 1] - UX Party Setup flow
