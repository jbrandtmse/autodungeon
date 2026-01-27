# Story 2.3: Narrative Message Display

Status: done

## Story

As a **user**,
I want **visually distinct message components for DM narration and PC dialogue**,
so that **I can instantly recognize who is speaking**.

## Acceptance Criteria

1. **Given** a DM narration message
   **When** displayed in the narrative area
   **Then** it shows with:
   - Gold (#D4A574) left border (4px)
   - Italic text
   - Lora font at 18px
   - No speaker attribution (DM is implicit)

2. **Given** a PC dialogue message
   **When** displayed in the narrative area
   **Then** it shows with:
   - "Name, the Class:" attribution in character color
   - Message bubble background (#3D3530)
   - Character-colored left border (3px)
   - Regular text for dialogue, italic for actions

3. **Given** a PC message contains both dialogue and actions
   **When** displayed
   **Then** quoted dialogue appears in regular text
   **And** action descriptions (*italicized*) appear in secondary color (#B8A896)

4. **Given** the narrative area
   **When** multiple messages are displayed
   **Then** messages are separated by 16px spacing
   **And** text is justified for manuscript feel

## Tasks / Subtasks

- [x] Task 1: Create message data model and parsing utilities (AC: #2, #3)
  - [x] 1.1 Add NarrativeMessage Pydantic model to models.py with agent, content, timestamp fields
  - [x] 1.2 Add message_type property (dm_narration, pc_dialogue) based on agent name
  - [x] 1.3 Create parse_message_content() utility to detect dialogue vs action text
  - [x] 1.4 Add unit tests for message model and parsing

- [x] Task 2: Implement DM message renderer (AC: #1, #4)
  - [x] 2.1 Create render_dm_message(content: str) function in app.py
  - [x] 2.2 Apply dm-message CSS class with gold border, italic Lora text
  - [x] 2.3 Ensure proper spacing between consecutive DM messages
  - [x] 2.4 Add unit test verifying HTML output structure

- [x] Task 3: Implement PC message renderer (AC: #2, #3, #4)
  - [x] 3.1 Create render_pc_message(name: str, char_class: str, content: str) function
  - [x] 3.2 Apply pc-message and character-specific CSS classes (fighter, rogue, etc.)
  - [x] 3.3 Render "Name, the Class:" attribution with pc-attribution class
  - [x] 3.4 Parse content to apply action-text class to *italicized* portions
  - [x] 3.5 Add unit tests verifying HTML output structure and character styling

- [x] Task 4: Create narrative area container component (AC: #4)
  - [x] 4.1 Update render_main_content() to include message list rendering
  - [x] 4.2 Create render_narrative_messages() function that iterates ground_truth_log
  - [x] 4.3 Determine message type from agent name prefix and route to appropriate renderer
  - [x] 4.4 Maintain proper 16px spacing via CSS margin-bottom

- [x] Task 5: Integrate with GameState ground_truth_log (AC: #1, #2, #3, #4)
  - [x] 5.1 Define ground_truth_log entry format: "[agent] content"
  - [x] 5.2 Create parse_log_entry() to extract agent name and content
  - [x] 5.3 Map agent names to character configs for color/class lookup
  - [x] 5.4 Handle edge cases gracefully:
    - Entry without brackets → treat as DM narration
    - Empty agent `[]` → use fallback "unknown"
    - Unknown agent → apply default (text-secondary) styling
    - Nested brackets in content → only parse first `[agent]`

- [x] Task 6: Add sample messages for testing display (AC: #1, #2, #3, #4)
  - [x] 6.1 Add sample DM narration entries to demonstrate styling
  - [x] 6.2 Add sample PC dialogue entries for each character class
  - [x] 6.3 Add sample mixed content (dialogue + action) messages
  - [x] 6.4 Ensure samples display correctly on app startup

- [x] Task 7: Write comprehensive tests
  - [x] 7.1 Test DM message rendering produces correct HTML structure
  - [x] 7.2 Test PC message rendering with each character class
  - [x] 7.3 Test action text parsing correctly identifies *italicized* portions
  - [x] 7.4 Test narrative container properly sequences multiple messages
  - [x] 7.5 Test ground_truth_log parsing handles edge cases

## Dev Notes

### Existing CSS Foundation (from Story 2.2)

All CSS classes needed for this story are already defined in `styles/theme.css`:

**DM Message Classes (ready to use):**
```css
.dm-message {
  background: var(--bg-message);
  border-left: 4px solid var(--color-dm);
  padding: var(--space-md) var(--space-lg);
  margin-bottom: var(--space-md);
  border-radius: 0 8px 8px 0;
}

.dm-message p {
  font-family: var(--font-narrative);
  font-size: var(--text-dm);
  line-height: 1.6;
  color: var(--text-primary);
  font-style: italic;
  text-align: justify;
  margin: 0;
}
```
[Source: styles/theme.css:153-169]

**PC Message Classes (ready to use):**
```css
.pc-message {
  background: var(--bg-message);
  padding: var(--space-md);
  margin-bottom: var(--space-md);
  border-radius: 8px;
  border-left: 3px solid var(--text-secondary);
}

.pc-message.fighter { border-left-color: var(--color-fighter); }
.pc-message.rogue { border-left-color: var(--color-rogue); }
.pc-message.wizard { border-left-color: var(--color-wizard); }
.pc-message.cleric { border-left-color: var(--color-cleric); }

.pc-attribution {
  font-family: var(--font-narrative);
  font-size: var(--text-name);
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: var(--space-xs);
}

.pc-attribution.fighter { color: var(--color-fighter); }
.pc-attribution.rogue { color: var(--color-rogue); }
.pc-attribution.wizard { color: var(--color-wizard); }
.pc-attribution.cleric { color: var(--color-cleric); }

.action-text {
  font-style: italic;
  color: var(--text-secondary);
}
```
[Source: styles/theme.css:172-214]

### Message Format Design

**ground_truth_log Entry Format:**
```
"[agent_name] message content here"
```

Examples:
- `"[dm] The tavern falls silent as the stranger enters, her cloak dripping with rain..."`
- `"[rogue] \"I'll check for traps,\" *she whispers, moving silently to the door.*"`
- `"[fighter] \"Stand ready!\" *He draws his sword and positions himself at the front.*"`

**Parsing Logic:**
1. Extract agent name from `[brackets]` at start
2. Map agent name to character config for name/class/color
3. Parse content for quoted dialogue vs asterisk-wrapped actions
4. Special case: `dm` agent gets DM-specific styling (no attribution line)

### Character Color Mapping

From `models.py` and `config/characters/*.yaml`:

| Agent Key | Character Name | Class | Color |
|-----------|----------------|-------|-------|
| dm | Dungeon Master | - | #D4A574 |
| fighter | Theron | Fighter | #C45C4A |
| rogue | Shadowmere | Rogue | #6B8E6B |
| wizard | Elara | Wizard | #7B68B8 |
| cleric | Brother Marcus | Cleric | #4A90A4 |

[Source: config/characters/*.yaml, models.py:85]

**Config Lookup Pattern:**
```python
def get_character_info(state: GameState, agent_name: str) -> tuple[str, str] | None:
    """Get (name, class) tuple for PC agent, None for DM.

    Args:
        state: Current game state
        agent_name: Agent key (e.g., "rogue", "fighter", "dm")

    Returns:
        (character_name, character_class) tuple, or None if DM
    """
    if agent_name == "dm":
        return None  # DM uses implicit narrator styling
    char_config = state["characters"].get(agent_name)
    if char_config:
        return (char_config.name, char_config.character_class)
    return ("Unknown", "Adventurer")  # Fallback for unknown agents
```

### Action/Dialogue Parsing

Content parsing rules for mixed messages:
1. Text wrapped in `"quotes"` = dialogue (regular weight)
2. Text wrapped in `*asterisks*` = action (italic, secondary color)
3. Unwrapped text = narration (follows parent element styling)

**Regex Pattern for Parsing (define at module level in app.py):**
```python
import re

# Module-level compiled patterns for performance
ACTION_PATTERN = re.compile(r'\*([^*]+)\*')
DIALOGUE_PATTERN = re.compile(r'"([^"]+)"')
LOG_ENTRY_PATTERN = re.compile(r'^\[(\w+)\]\s*(.*)$')

def parse_message_content(content: str) -> list[tuple[str, str]]:
    """Parse content into typed segments.

    Returns list of (type, text) tuples where type is:
    - 'dialogue': quoted text
    - 'action': asterisk-wrapped text
    - 'narration': everything else
    """
    # Implementation details in Task 1.3
```

### HTML Rendering Functions

**DM Message Renderer:**
```python
def render_dm_message(content: str) -> None:
    """Render DM narration with campfire styling."""
    st.markdown(
        f'''<div class="dm-message">
            <p>{escape_html(content)}</p>
        </div>''',
        unsafe_allow_html=True,
    )
```

**PC Message Renderer:**
```python
def render_pc_message(
    name: str,
    char_class: str,
    content: str,
) -> None:
    """Render PC dialogue with character styling."""
    class_slug = char_class.lower()
    formatted_content = format_pc_content(content)  # Apply action styling
    st.markdown(
        f'''<div class="pc-message {class_slug}">
            <span class="pc-attribution {class_slug}">{name}, the {char_class}:</span>
            <p>{formatted_content}</p>
        </div>''',
        unsafe_allow_html=True,
    )

def format_pc_content(content: str) -> str:
    """Format PC message content with action styling.

    Wraps *asterisk text* in <span class="action-text">.
    """
    # Replace *text* with <span class="action-text">text</span>
    return ACTION_PATTERN.sub(
        r'<span class="action-text">\1</span>',
        escape_html(content)
    )
```

### Previous Story Intelligence (from Story 2.2)

**Key Learnings:**
- CSS injection works via `st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)`
- `load_css()` function exists in `app.py` to load from `styles/theme.css`
- Character color variables already defined in `:root`
- Google Fonts already imported (Lora, Inter, JetBrains Mono)
- Story 2.2 created all required CSS classes for message styling

**Files Modified in Story 2.2:**
- `styles/theme.css` - Extended with all CSS variables and component styling
- `app.py` - Added CSS injection, layout structure, sidebar rendering
- `tests/test_app.py` - Added CSS compliance tests

[Source: _bmad-output/implementation-artifacts/2-2-campfire-theme-css-foundation.md]

### Git Intelligence (Recent Commits)

**Recent commit patterns (a17944e):**
- Story 2.2 implemented full CSS theme foundation
- Code review fixes applied in same commit
- Tests added for each implementation
- All 304 tests passing

**Files touched in Story 2.2:**
- `styles/theme.css` - Full theme component styling (message classes ready)
- `app.py` - Layout restructure with mode indicator, party panel
- `tests/test_app.py` - Added 37 CSS and session state tests

### Architecture Compliance

Per architecture.md, this story:
- Keeps rendering logic in `app.py` (Viewer Interface primary module)
- Uses existing CSS classes from `styles/theme.css` (no new CSS needed)
- Accesses state via `st.session_state["game"]`
- Uses `ground_truth_log` for message history (append-only log)
- Follows PEP 8 naming conventions (snake_case functions)

[Source: architecture.md#FR Category to Module Mapping]

### Dependencies and Imports

**Required imports for app.py:**
```python
import re
from html import escape as escape_html
from pathlib import Path

import streamlit as st

from models import GameState, CharacterConfig
```

### Sample Messages for Testing

Add these to `populate_game_state()` or create a separate test fixture:

```python
sample_messages = [
    "[dm] The tavern falls silent as the stranger enters, her cloak dripping with rain. The firelight catches the glint of steel beneath her traveling cloak.",
    "[fighter] \"Stand ready,\" *Theron mutters, his hand moving to his sword hilt.* \"Something feels wrong about this.\"",
    "[rogue] *Shadowmere melts into the shadows near the bar, her eyes never leaving the newcomer.* \"Let her make the first move.\"",
    "[wizard] *Elara sets down her wine glass, arcane symbols flickering briefly in her eyes.* \"She carries powerful enchantments. Be cautious.\"",
    "[cleric] \"Peace, friends.\" *Brother Marcus raises a calming hand.* \"Perhaps she merely seeks shelter from the storm.\"",
    "[dm] The stranger approaches the bar, her boots leaving wet prints on the worn wooden floor. She speaks to the barkeep in hushed tones, then turns to survey the room. Her gaze lingers on your table.",
]
```

### Testing Strategy

Organize tests in dedicated test classes within `tests/test_app.py`:

```python
class TestDMMessageRendering:
    """Tests for DM message HTML generation."""

class TestPCMessageRendering:
    """Tests for PC message HTML generation with character styling."""

class TestActionTextParsing:
    """Tests for *asterisk* to action-text span conversion."""

class TestLogEntryParsing:
    """Tests for ground_truth_log entry parsing."""

class TestNarrativeContainer:
    """Tests for full narrative area rendering."""
```

Tests should verify:
1. DM messages produce correct HTML with `.dm-message` class
2. PC messages produce correct HTML with character-specific classes
3. Action text parsing correctly wraps `*asterisks*` in `.action-text` spans
4. Ground truth log parsing extracts agent and content correctly
5. Edge cases: empty log, malformed entries, unknown agents
6. Empty narrative area shows placeholder text

**Test Pattern (use `_html` suffix functions for testability):**
```python
# In app.py: separate HTML generation from Streamlit rendering
def render_dm_message_html(content: str) -> str:
    """Generate HTML for DM message (testable without Streamlit)."""
    return f'<div class="dm-message"><p>{escape_html(content)}</p></div>'

def render_dm_message(content: str) -> None:
    """Render DM message to Streamlit."""
    st.markdown(render_dm_message_html(content), unsafe_allow_html=True)

# In tests:
def test_render_dm_message_html_structure():
    """Test DM message rendering produces correct HTML."""
    html = render_dm_message_html("The tavern is quiet.")
    assert 'class="dm-message"' in html
    assert '<p>' in html
    assert 'The tavern is quiet.' in html

def test_render_pc_message_with_action():
    """Test PC message with action text styling."""
    html = render_pc_message_html(
        "Theron", "Fighter",
        '*draws his sword* "For glory!"'
    )
    assert 'class="pc-message fighter"' in html
    assert 'class="action-text"' in html
    assert 'draws his sword' in html
```

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR25 | Real-time narrative display | Message rendering in narrative container |
| FR26 | Visual distinction DM/PC/actions | DM message class, PC message class, action-text class |
| FR27 | Character attribution per message | "Name, the Class:" attribution with character color |
| FR28 (partial) | Scroll session history | Narrative container supports scrolling |

[Source: prd.md#Viewer Interface, epics.md#Story 2.3]

### What This Story Does NOT Do

- Does NOT implement auto-scroll behavior (Story 2.6: Real-time Narrative Flow)
- Does NOT implement current turn highlighting (Story 2.6)
- Does NOT implement thinking/loading indicators (Story 2.6)
- Does NOT implement Drop-In button functionality (Story 3.2: Drop-In Mode)
- Does NOT implement LangGraph integration for real turn generation (already done in Epic 1)

This story creates the message rendering components that Story 2.6 will use for real-time updates.

### Project Structure Notes

- All message rendering logic goes in `app.py` (rendering module)
- Message model/parsing utilities can go in `models.py` if needed, or inline in `app.py`
- CSS already complete in `styles/theme.css` - no modifications needed
- Tests go in `tests/test_app.py` (extend existing test file)

### Security Consideration

**HTML Escaping:** All user/agent-generated content MUST be escaped before rendering to prevent XSS:

```python
from html import escape as escape_html

def render_dm_message(content: str) -> None:
    escaped = escape_html(content)
    # ... render with escaped content
```

The `format_pc_content()` function escapes content before applying regex replacements. Note that `html.escape()` only escapes `<`, `>`, `&`, and optionally quotes - asterisks (`*`) are NOT HTML special characters and pass through unchanged, so `ACTION_PATTERN.sub()` works correctly after escaping.

### References

- [Source: planning-artifacts/ux-design-specification.md#Narrative Message (DM)] - DM message spec
- [Source: planning-artifacts/ux-design-specification.md#Narrative Message (PC)] - PC message spec
- [Source: planning-artifacts/architecture.md#Implementation Patterns] - Naming conventions
- [Source: styles/theme.css] - All CSS classes ready for use
- [Source: epics.md#Story 2.3] - Full acceptance criteria
- [Source: _bmad-output/implementation-artifacts/2-2-campfire-theme-css-foundation.md] - Previous story

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- No debug issues encountered

### Completion Notes List

- **Task 1**: Added `NarrativeMessage` and `MessageSegment` Pydantic models to `models.py`. Created `parse_log_entry()` and `parse_message_content()` functions with compiled regex patterns for efficient parsing. Handles dialogue (quoted), action (*asterisks*), and narration segments.

- **Task 2**: Implemented `render_dm_message_html()` for testable HTML generation and `render_dm_message()` wrapper for Streamlit rendering in `app.py`. Uses existing `.dm-message` CSS class from Story 2.2.

- **Task 3**: Implemented `render_pc_message_html()`, `render_pc_message()`, and `format_pc_content()` in `app.py`. Action text wrapped in `*asterisks*` is converted to `<span class="action-text">`. All content is HTML-escaped before rendering to prevent XSS.

- **Task 4**: Updated `render_main_content()` to render actual messages from `ground_truth_log` instead of placeholder. Created `render_narrative_messages()` function to iterate log and route to appropriate renderer.

- **Task 5**: Created `get_character_info()` to look up character name/class from state. Agent keys in `ground_truth_log` are character names (lowercase), not class names. Edge cases handled: no brackets → DM, empty brackets → fallback, unknown agent → "Unknown Adventurer".

- **Task 6**: Modified `populate_game_state()` to accept `include_sample_messages` parameter (default `True`). Added `_get_sample_messages()` helper that generates demo messages for all character classes with mixed dialogue and action text.

- **Task 7**: Added 65 new tests across 11 test classes covering all acceptance criteria, edge cases, and HTML structure verification. Total test count increased from 304 to 367 (all passing).

### File List

**Modified:**
- `models.py` - Added NarrativeMessage, MessageSegment models, parse_log_entry(), parse_message_content(), _get_sample_messages(), updated populate_game_state()
- `app.py` - Added render_dm_message_html(), render_dm_message(), format_pc_content(), render_pc_message_html(), render_pc_message(), get_character_info(), render_narrative_messages(), updated render_main_content()
- `tests/test_app.py` - Added 65 new tests in 11 test classes for Story 2.3

### Change Log

- 2026-01-27: Implemented Story 2.3 Narrative Message Display - all tasks complete, 367 tests passing
- 2026-01-27: Code review fixes applied:
  - Fixed LOG_ENTRY_PATTERN regex to support agent names with spaces (e.g., "brother aldric")
  - Fixed parse_message_content() to filter out empty segments from edge cases like "**"
  - Added 2 new tests for edge cases (369 tests passing)

