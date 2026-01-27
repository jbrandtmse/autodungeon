# Story 2.4: Party Panel & Character Cards

Status: done

## Story

As a **user**,
I want **a sidebar panel showing all party members with Drop-In controls**,
so that **I can see who's in the party and quickly take control of any character**.

## Acceptance Criteria

1. **Given** the sidebar party panel
   **When** viewing the application
   **Then** I see a character card for each PC agent (Fighter, Rogue, Wizard, Cleric)

2. **Given** each character card
   **When** displayed
   **Then** it shows:
   - Character name in character color (14px, weight 600)
   - Character class in secondary text (13px)
   - Drop-In button with character-colored border

3. **Given** a Drop-In button in default state
   **When** I hover over it
   **Then** the button fills with the character color
   **And** text color inverts to dark background

4. **Given** the character card styling
   **When** viewed
   **Then** cards have #2D2520 background, 8px border radius, character-colored left border (3px)

5. **Given** I click a Drop-In button
   **When** the action completes
   **Then** the button changes to "Release" and the card shows a subtle glow (for Epic 3 integration)

## Tasks / Subtasks

- [x] Task 1: Refactor render_sidebar() for proper character card structure (AC: #1, #2, #4)
  - [x] 1.1 Extract character card rendering to dedicated `render_character_card()` function
  - [x] 1.2 Ensure each PC agent (fighter, rogue, wizard, cleric) has a character card - exclude DM
  - [x] 1.3 Verify card displays character name from CharacterConfig.name (not agent key)
  - [x] 1.4 Verify card displays character class from CharacterConfig.character_class
  - [x] 1.5 Apply CSS class `character-card {class_slug}` for character-colored left border

- [x] Task 2: Implement functional Drop-In button with Streamlit callback (AC: #3, #5)
  - [x] 2.1 Replace HTML button with `st.button()` for actual click handling
  - [x] 2.2 Create unique button key per character using agent key (e.g., `drop_in_fighter`)
  - [x] 2.3 Implement button click handler to set `st.session_state["controlled_character"]`
  - [x] 2.4 Implement button click handler to set `st.session_state["ui_mode"]` to "play"
  - [x] 2.5 Apply character-specific CSS styling to Streamlit button container

- [x] Task 3: Implement controlled state visual feedback (AC: #5)
  - [x] 3.1 Check `st.session_state["controlled_character"]` to determine if card is controlled
  - [x] 3.2 Add `.controlled` class to character-card div when controlled
  - [x] 3.3 Change button label to "Release" when controlling this character
  - [x] 3.4 Implement release handler to reset `controlled_character` to None and `ui_mode` to "watch"
  - [x] 3.5 Ensure clicking same character's button toggles control (Drop-In → Release)

- [x] Task 4: Create HTML rendering helper for testability (AC: #1, #2, #4)
  - [x] 4.1 Create `render_character_card_html()` function returning HTML string
  - [x] 4.2 Include all structural elements: name, class, button container
  - [x] 4.3 Apply correct CSS classes for character color theming
  - [x] 4.4 Handle `controlled` state parameter for glow effect styling

- [x] Task 5: Verify CSS classes produce expected visual styling (AC: #2, #3, #4)
  - [x] 5.1 Test character-name color matches character color for each class
  - [x] 5.2 Test character-card left border color matches character color
  - [x] 5.3 Test drop-in-button hover fills with character color (requires manual/visual test)
  - [x] 5.4 Test controlled card has glow effect (box-shadow)

- [x] Task 6: Write comprehensive tests
  - [x] 6.1 Test render_character_card_html() produces correct HTML structure
  - [x] 6.2 Test each character class (fighter, rogue, wizard, cleric) gets correct CSS classes
  - [x] 6.3 Test controlled state adds .controlled class
  - [x] 6.4 Test button label changes based on controlled state
  - [x] 6.5 Test sidebar renders all 4 PC characters (excludes DM)
  - [x] 6.6 Test session state updates on button click (integration test)

## Dev Notes

### Existing Implementation (from Story 2.1/2.2)

The current `render_sidebar()` in `app.py` already has a basic character card implementation:

```python
# Current implementation (app.py:226-247)
game: GameState = st.session_state.get("game", {})
characters = game.get("characters", {})

if characters:
    for _char_name, char_config in characters.items():
        class_slug = char_config.character_class.lower()
        st.markdown(
            f'<div class="character-card {class_slug}">'
            f'<span class="character-name {class_slug}">'
            f"{char_config.name}</span><br/>"
            f'<span class="character-class">'
            f"{char_config.character_class}</span>"
            f'<button class="drop-in-button {class_slug}">Drop-In</button>'
            f"</div>",
            unsafe_allow_html=True,
        )
```
[Source: app.py:226-247]

**Issues with current implementation:**
1. HTML `<button>` element is non-functional (no click handler)
2. No controlled state detection or visual feedback
3. No "Release" button functionality
4. DM may be included in characters dict (should be excluded from party panel)

### CSS Foundation (from Story 2.2)

All CSS classes are already defined in `styles/theme.css`:

**Character Card Classes:**
```css
.character-card {
  background: var(--bg-secondary);  /* #2D2520 */
  border-radius: 8px;
  padding: var(--space-md);
  margin-bottom: var(--space-sm);
  border-left: 3px solid var(--text-secondary);
}

.character-card.controlled {
  background: var(--bg-message);  /* #3D3530 */
  border-left-width: 4px;
  box-shadow: 0 0 12px rgba(232, 168, 73, 0.2);  /* Warm glow */
}

.character-card.fighter { border-left-color: var(--color-fighter); }
.character-card.rogue { border-left-color: var(--color-rogue); }
.character-card.wizard { border-left-color: var(--color-wizard); }
.character-card.cleric { border-left-color: var(--color-cleric); }
```
[Source: styles/theme.css:257-296]

**Character Name Classes:**
```css
.character-name {
  font-family: var(--font-ui);
  font-size: var(--text-name);  /* 14px */
  font-weight: 600;
  color: var(--text-primary);
}

.character-name.fighter { color: var(--color-fighter); }  /* #C45C4A */
.character-name.rogue { color: var(--color-rogue); }      /* #6B8E6B */
.character-name.wizard { color: var(--color-wizard); }    /* #7B68B8 */
.character-name.cleric { color: var(--color-cleric); }    /* #4A90A4 */
```
[Source: styles/theme.css:273-296]

**Drop-In Button Classes:**
```css
.drop-in-button {
  background: transparent;
  border: 1px solid var(--text-secondary);
  color: var(--text-secondary);
  border-radius: 4px;
  padding: 6px 12px;
  font-family: var(--font-ui);
  font-size: var(--text-system);  /* 13px */
  cursor: pointer;
  transition: all 0.15s ease;
  width: 100%;
  margin-top: var(--space-xs);
}

.drop-in-button:hover {
  background: var(--text-secondary);
  color: var(--bg-primary);
}

.drop-in-button.fighter { border-color: var(--color-fighter); color: var(--color-fighter); }
.drop-in-button.fighter:hover { background: var(--color-fighter); color: var(--bg-primary); }
/* ... similar for rogue, wizard, cleric */
```
[Source: styles/theme.css:302-336]

### Implementation Approach

**Streamlit Button Integration Challenge:**

Streamlit buttons (`st.button()`) don't support custom CSS classes directly. To achieve the character-colored button styling, we need a hybrid approach:

1. Wrap `st.button()` in a container div with the character class
2. Use CSS selectors to target buttons within that container
3. Add CSS to theme.css to style buttons within character-card containers

**Recommended CSS Addition:**
```css
/* Style Streamlit buttons inside character cards */
.character-card.fighter .stButton > button {
  background: transparent;
  border: 1px solid var(--color-fighter);
  color: var(--color-fighter);
}
.character-card.fighter .stButton > button:hover {
  background: var(--color-fighter);
  color: var(--bg-primary);
}
/* ... similar for rogue, wizard, cleric */
```

**Alternative: HTML + JavaScript approach:**
Keep the HTML button but add JavaScript click handlers that communicate with Streamlit via query params or custom components. This is more complex and not recommended for MVP.

### Character Config Lookup

Characters are stored in `st.session_state["game"]["characters"]` as a dict:
- Key: agent key (e.g., "fighter", "rogue", "wizard", "cleric")
- Value: CharacterConfig Pydantic model

**Important:** Exclude "dm" from party panel - the DM is not a controllable character.

```python
# Correct iteration pattern
for agent_key, char_config in characters.items():
    if agent_key == "dm":
        continue  # Skip DM in party panel
    # ... render character card
```

### Session State Keys

Per architecture.md, these session state keys are used:
- `st.session_state["game"]` - GameState object
- `st.session_state["ui_mode"]` - "watch" | "play"
- `st.session_state["controlled_character"]` - str | None (agent key when controlling)

[Source: architecture.md#Streamlit Session State]

### Streamlit Button Key Pattern

Each button needs a unique key to prevent Streamlit duplicate key errors:

```python
if st.button(
    "Drop-In" if not is_controlled else "Release",
    key=f"drop_in_{agent_key}",  # e.g., "drop_in_fighter"
):
    # Handle click
```

### HTML Rendering for Testability

Follow the pattern from Story 2.3 - create `_html` suffix functions for testable HTML generation:

```python
def render_character_card_html(
    name: str,
    char_class: str,
    controlled: bool = False,
) -> str:
    """Generate HTML for character card (testable without Streamlit).

    Args:
        name: Character display name (e.g., "Theron").
        char_class: Character class (e.g., "Fighter").
        controlled: Whether this character is currently controlled.

    Returns:
        HTML string for character card div.
    """
    class_slug = char_class.lower()
    controlled_class = " controlled" if controlled else ""
    return (
        f'<div class="character-card {class_slug}{controlled_class}">'
        f'<span class="character-name {class_slug}">{escape_html(name)}</span><br/>'
        f'<span class="character-class">{escape_html(char_class)}</span>'
        # Button placeholder - actual button rendered via st.button()
        f'</div>'
    )
```

### Previous Story Intelligence (from Story 2.3)

**Key Learnings:**
- HTML escaping is critical for all user/agent content
- Separate HTML generation from Streamlit rendering for testability
- Use `_html` suffix functions for pure HTML generation
- CSS classes from theme.css work correctly with `st.markdown()`
- Test classes organized by functionality (e.g., TestCharacterCardRendering)

**Files Modified in Story 2.3:**
- `models.py` - Added NarrativeMessage, parse_log_entry(), parse_message_content()
- `app.py` - Added render_dm_message_html(), render_pc_message_html(), etc.
- `tests/test_app.py` - Added 65 new tests

[Source: _bmad-output/implementation-artifacts/2-3-narrative-message-display.md]

### Git Intelligence (Recent Commits)

**Recent commit patterns (9dfd9fa):**
- Story 2.3 implemented narrative message display
- Code review fixes applied in same commit
- Tests added for each implementation
- All 369 tests passing

**Commit structure pattern:**
```
Implement Story X.Y: Title with code review fixes
```

### Architecture Compliance

Per architecture.md, this story:
- Keeps UI rendering logic in `app.py` (Viewer Interface primary module)
- Extends existing CSS classes from `styles/theme.css`
- Accesses state via `st.session_state["game"]`, `st.session_state["controlled_character"]`
- Follows PEP 8 naming conventions (snake_case functions)

[Source: architecture.md#FR Category to Module Mapping]

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR30 | Drop-In controls per character | Drop-In button in each character card |

[Source: prd.md#Viewer Interface, epics.md#Story 2.4]

### What This Story Does NOT Do

- Does NOT implement full Drop-In mode input area (Story 3.2: Drop-In Mode)
- Does NOT implement keyboard shortcuts for drop-in (Story 3.6: Keyboard Shortcuts)
- Does NOT implement mode indicator update on drop-in (already handled - mode indicator reads ui_mode)
- Does NOT implement human intervention in LangGraph (Story 3.2: Drop-In Mode)

This story creates the visual UI for party panel and wires up the session state changes. Story 3.2 will handle the actual gameplay integration.

### Testing Strategy

Organize tests in dedicated test class within `tests/test_app.py`:

```python
class TestCharacterCardRendering:
    """Tests for character card HTML generation and rendering."""

class TestDropInButton:
    """Tests for Drop-In/Release button functionality."""

class TestPartyPanel:
    """Tests for sidebar party panel rendering."""
```

**Test Categories:**
1. HTML structure tests (render_character_card_html output)
2. CSS class application tests (character colors, controlled state)
3. Session state mutation tests (controlled_character, ui_mode)
4. Integration tests (full sidebar rendering)

**Test Pattern (from Story 2.3):**
```python
def test_render_character_card_html_structure():
    """Test character card rendering produces correct HTML."""
    html = render_character_card_html("Theron", "Fighter", controlled=False)
    assert 'class="character-card fighter"' in html
    assert 'class="character-name fighter"' in html
    assert 'Theron' in html
    assert 'Fighter' in html

def test_render_character_card_controlled_state():
    """Test controlled character has controlled class."""
    html = render_character_card_html("Theron", "Fighter", controlled=True)
    assert 'class="character-card fighter controlled"' in html
```

### Security Consideration

**HTML Escaping:** All character names and classes MUST be escaped before rendering:

```python
from html import escape as escape_html

def render_character_card_html(name: str, char_class: str, ...) -> str:
    return f'... {escape_html(name)} ... {escape_html(char_class)} ...'
```

### Project Structure Notes

- Character card rendering logic goes in `app.py` (rendering module)
- CSS additions (if needed) go in `styles/theme.css`
- Tests go in `tests/test_app.py` (extend existing test file)

### CSS Addition Required

Add to `styles/theme.css` to style Streamlit buttons within character cards:

```css
/* ==========================================================================
   Character Card Streamlit Button Overrides (Story 2.4)
   ========================================================================== */

/* Reset default Streamlit button styling inside character cards */
.character-card .stButton > button {
  background: transparent;
  border: 1px solid var(--text-secondary);
  color: var(--text-secondary);
  border-radius: 4px;
  padding: 6px 12px;
  font-size: var(--text-system);
  width: 100%;
  margin-top: var(--space-xs);
  transition: all 0.15s ease;
}

/* Fighter Drop-In button */
.character-card.fighter .stButton > button {
  border-color: var(--color-fighter);
  color: var(--color-fighter);
}
.character-card.fighter .stButton > button:hover {
  background: var(--color-fighter);
  color: var(--bg-primary);
}

/* Rogue Drop-In button */
.character-card.rogue .stButton > button {
  border-color: var(--color-rogue);
  color: var(--color-rogue);
}
.character-card.rogue .stButton > button:hover {
  background: var(--color-rogue);
  color: var(--bg-primary);
}

/* Wizard Drop-In button */
.character-card.wizard .stButton > button {
  border-color: var(--color-wizard);
  color: var(--color-wizard);
}
.character-card.wizard .stButton > button:hover {
  background: var(--color-wizard);
  color: var(--bg-primary);
}

/* Cleric Drop-In button */
.character-card.cleric .stButton > button {
  border-color: var(--color-cleric);
  color: var(--color-cleric);
}
.character-card.cleric .stButton > button:hover {
  background: var(--color-cleric);
  color: var(--bg-primary);
}

/* Controlled state - Release button uses amber accent */
.character-card.controlled .stButton > button {
  background: var(--accent-warm);
  border-color: var(--accent-warm);
  color: var(--bg-primary);
}
.character-card.controlled .stButton > button:hover {
  background: #D49A3D;
}
```

### Implementation Order

1. **Task 4 first** - Create `render_character_card_html()` for testability
2. **Task 6.1-6.4** - Write tests for HTML rendering
3. **Task 1** - Refactor render_sidebar() to use new function
4. **Task 2** - Replace HTML button with functional Streamlit button
5. **Task 3** - Add controlled state handling
6. **Task 5** - Add CSS for Streamlit button styling
7. **Task 6.5-6.6** - Write integration tests

### References

- [Source: planning-artifacts/ux-design-specification.md#Character Card] - Character card spec
- [Source: planning-artifacts/ux-design-specification.md#Drop-In Button] - Button styling spec
- [Source: planning-artifacts/architecture.md#Streamlit Session State] - Session state keys
- [Source: styles/theme.css:257-336] - Existing CSS classes
- [Source: epics.md#Story 2.4] - Full acceptance criteria
- [Source: _bmad-output/implementation-artifacts/2-3-narrative-message-display.md] - Previous story patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No debug issues encountered during implementation.

### Completion Notes List

- Implemented `render_character_card_html()` function for testable HTML generation with proper HTML escaping
- Created `get_drop_in_button_label()` helper for button label logic
- Added `get_party_characters()` function to filter DM from character list
- Implemented `handle_drop_in_click()` handler for session state management (Drop-In/Release toggle)
- Created `render_character_card()` function combining HTML rendering with Streamlit button
- Added CSS overrides for Streamlit buttons within character cards (all 4 character classes + controlled state)
- Added 23 new tests covering HTML rendering, button labels, party filtering, and session state changes
- All 389 tests pass, ruff lint clean

### File List

- `app.py` (modified) - Added 5 new functions for character card rendering and button handling; added type annotations
- `styles/theme.css` (modified) - Added ~70 lines of CSS for Streamlit button styling using `.character-card-wrapper` selectors
- `tests/test_app.py` (modified) - Added 28 new tests (141 total in test_app.py, 394 total project tests)

### Change Log

- 2026-01-27: Implemented Story 2.4 Party Panel & Character Cards
  - Refactored render_sidebar() to use dedicated character card rendering
  - Replaced non-functional HTML button with functional Streamlit st.button()
  - Added controlled state visual feedback (controlled class, Release label)
  - Added CSS overrides for character-colored Streamlit buttons
  - Excluded DM from party panel
  - All acceptance criteria satisfied

- 2026-01-27: Code Review Fixes Applied
  - **H1 Fixed**: Added type annotation `CharacterConfig` for `char_config` parameter in `render_character_card()`
  - **H2 Fixed**: Added return type `dict[str, CharacterConfig]` for `get_party_characters()`
  - **H3 Fixed**: Restructured HTML with new `.character-card-wrapper` div to enable proper CSS targeting of Streamlit buttons
  - **M2 Fixed**: Added `TestPartyPanelIntegration` class with tests for full party panel rendering
  - **M3 Fixed**: Added integration tests for control toggle cycle and quick character switching
  - Updated CSS selectors from `.character-card` to `.character-card-wrapper` for button styling
  - All 394 tests pass, pyright 0 errors, ruff lint clean
