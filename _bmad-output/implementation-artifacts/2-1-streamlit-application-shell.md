# Story 2.1: Streamlit Application Shell

Status: done

## Story

As a **user**,
I want **a Streamlit application with a proper layout structure**,
so that **I have a sidebar for controls and a main area for the narrative**.

## Acceptance Criteria

1. **Given** the app.py entry point
   **When** I run `streamlit run app.py`
   **Then** the application launches in my default browser

2. **Given** the application is running
   **When** I view the page
   **Then** I see a fixed 240px sidebar on the left and a fluid main narrative area

3. **Given** the Streamlit configuration
   **When** the app loads
   **Then** it uses wide layout mode (`st.set_page_config(layout="wide")`)
   **And** the page title is "autodungeon"

4. **Given** the GameState is stored in session state
   **When** I interact with the app
   **Then** state persists via `st.session_state["game"]`

5. **Given** the viewport is less than 1024px wide
   **When** viewing the application
   **Then** a message displays: "Please use a wider browser window for the best experience"

## Tasks / Subtasks

- [x] Task 1: Create CSS theme file with base layout structure (AC: #2, #5)
  - [x] 1.1 Create `styles/theme.css` with CSS variables from UX spec
  - [x] 1.2 Add layout grid: 240px sidebar + fluid main area
  - [x] 1.3 Add responsive breakpoint for <1024px viewport warning
  - [x] 1.4 Add dark theme colors (#1A1612 background, #2D2520 surfaces)
  - [x] 1.5 Add typography settings (Lora for narrative, Inter for UI)

- [x] Task 2: Restructure app.py with sidebar/main layout (AC: #1, #2, #3)
  - [x] 2.1 Keep existing page config (already wide layout with autodungeon title)
  - [x] 2.2 Add CSS injection via `st.markdown(unsafe_allow_html=True)`
  - [x] 2.3 Create sidebar section using `st.sidebar`
  - [x] 2.4 Create main narrative area using `st.container`
  - [x] 2.5 Move existing config status to sidebar (condensed view)

- [x] Task 3: Implement session state initialization (AC: #4)
  - [x] 3.1 Initialize `st.session_state["game"]` with populated GameState
  - [x] 3.2 Use `populate_game_state()` from models.py for initialization
  - [x] 3.3 Load character configs via `load_character_configs()` from config.py
  - [x] 3.4 Add `st.session_state["ui_mode"]` = "watch" (default)
  - [x] 3.5 Add `st.session_state["controlled_character"]` = None

- [x] Task 4: Create placeholder UI components (AC: #2)
  - [x] 4.1 Add sidebar header with mode indicator placeholder
  - [x] 4.2 Add party panel placeholder (list characters from session state)
  - [x] 4.3 Add main narrative area with session header placeholder
  - [x] 4.4 Add narrative container placeholder for future message display

- [x] Task 5: Write tests for app initialization
  - [x] 5.1 Test CSS file exists and contains required variables
  - [x] 5.2 Test session state initialization with proper GameState
  - [x] 5.3 Test sidebar width CSS rule is present (240px)

## Dev Notes

### Existing Code to Leverage

**DO NOT recreate - these already exist:**
- `app.py` - Existing Streamlit entry point with page config and basic structure
- `config.py` with `get_config()`, `load_character_configs()`, `load_dm_config()`
- `models.py` with `populate_game_state()` factory function
- `GameState` TypedDict in `models.py:185-217`
- Character YAML files in `config/characters/`

**Existing page config (keep this):**
```python
st.set_page_config(
    page_title="autodungeon",
    page_icon="🎲",
    layout="wide",
)
```

### CSS Variables (from UX Design Specification)

Per UX spec, use these exact CSS variables:

```css
/* Background Colors */
--bg-primary: #1A1612;    /* Deep warm black - main canvas */
--bg-secondary: #2D2520;  /* Warm gray-brown - elevated surfaces */
--bg-message: #3D3530;    /* Message bubble background */

/* Text Colors */
--text-primary: #F5E6D3;  /* Warm off-white */
--text-secondary: #B8A896; /* Muted warm gray */

/* Accent */
--accent-warm: #E8A849;   /* Amber highlight */

/* Character Identity Colors */
--color-dm: #D4A574;      /* DM/Narrator - warm gold */
--color-fighter: #C45C4A; /* Fighter - bold red */
--color-rogue: #6B8E6B;   /* Rogue - forest green */
--color-wizard: #7B68B8;  /* Wizard - mystic purple */
--color-cleric: #4A90A4;  /* Cleric - calm blue */
```

[Source: planning-artifacts/ux-design-specification.md#Color System]

### Typography (from UX Design Specification)

```css
/* Font Stack */
--font-narrative: 'Lora', Georgia, serif;
--font-ui: 'Inter', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', monospace;

/* Font Sizes */
--text-dm: 18px;          /* DM narration */
--text-pc: 17px;          /* PC dialogue */
--text-name: 14px;        /* Character names, 600 weight */
--text-ui: 14px;          /* UI controls */
--text-system: 13px;      /* System text */
```

[Source: planning-artifacts/ux-design-specification.md#Typography System]

### Layout Specifications

Per UX spec:
- Sidebar width: 240px fixed
- Max content width: 800px for narrative area
- Spacing uses 8px base grid
- Minimum supported viewport: 1024px

```css
.app-container {
    display: grid;
    grid-template-columns: 240px 1fr;
    min-height: 100vh;
}

.narrative-area {
    max-width: 800px;
    margin: 0 auto;
    padding: var(--space-lg);
}

@media (max-width: 1023px) {
    .viewport-warning {
        display: block;
    }
    .app-content {
        display: none;
    }
}
```

[Source: planning-artifacts/ux-design-specification.md#Responsive Strategy]

### Session State Keys (from Architecture)

Per architecture.md, use these session state keys:
```python
st.session_state["game"]                 # GameState object
st.session_state["ui_mode"]              # "watch" | "play"
st.session_state["controlled_character"] # str | None
st.session_state["error"]                # UserError | None (for future)
```

[Source: planning-artifacts/architecture.md#Streamlit Integration]

### CSS Injection Pattern

Streamlit requires CSS injection via markdown:

```python
def load_css() -> str:
    """Load CSS from theme file."""
    css_path = Path(__file__).parent / "styles" / "theme.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""

# In main():
css = load_css()
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
```

### Viewport Warning Implementation

Per UX spec, show warning for small viewports:

```css
.viewport-warning {
    display: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: var(--bg-primary);
    z-index: 9999;
    color: var(--text-primary);
    font-family: var(--font-ui);
    padding: 2rem;
    text-align: center;
}

@media (max-width: 1023px) {
    .viewport-warning {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
}
```

### GameState Initialization Pattern

Use existing infrastructure:

```python
from config import get_config, load_character_configs, load_dm_config
from models import populate_game_state

def initialize_game_state() -> None:
    """Initialize game state in session state if not present."""
    if "game" not in st.session_state:
        config = get_config()
        characters = load_character_configs()
        dm_config = load_dm_config()

        st.session_state["game"] = populate_game_state(
            characters=characters,
            dm_config=dm_config,
        )
        st.session_state["ui_mode"] = "watch"
        st.session_state["controlled_character"] = None
```

[Source: models.py#populate_game_state, config.py#load_character_configs]

### Previous Story Intelligence

**From Epic 1 Implementation:**
- All 251+ tests passing
- Character configs load from `config/characters/*.yaml`
- `populate_game_state()` creates fully initialized GameState with characters, turn_queue, agent_memories
- DM config loaded separately from PC configs
- Existing `app.py` has page config already set up correctly

**Key Patterns Established:**
- Flat project layout - modules in root
- snake_case functions, PascalCase classes
- CSS goes in `styles/` subdirectory
- Configuration via YAML files in `config/`

### Git Intelligence

Recent commits show:
- Story 1.7 and 1.8 completed
- Tests use mocking for LLM invocations
- Code review fixes applied (current_turn updates, provider validation)

### What NOT To Do

- Do NOT implement full message display (that's Story 2.3)
- Do NOT implement full character cards with Drop-In buttons (that's Story 2.4)
- Do NOT implement session header with turn counter (that's Story 2.5)
- Do NOT add auto-scroll or real-time updates (that's Story 2.6)
- Do NOT remove existing app.py functionality - extend it
- Do NOT use inline styles - use CSS file
- Do NOT hardcode colors - use CSS variables

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR25 (partial) | Real-time narrative display | Layout container prepared |
| FR30 (partial) | Drop-In controls per character | Party panel placeholder |
| FR31 (partial) | Session controls access | Sidebar structure |

[Source: prd.md#Viewer Interface, epics.md#Story 2.1]

### Project Structure Notes

- Keep flat layout per architecture
- CSS file goes in `styles/theme.css`
- No new Python modules needed - extend `app.py`
- Tests can use pytest-streamlit or simply verify CSS/state initialization

### References

- [Source: planning-artifacts/ux-design-specification.md#Design System Foundation] - All CSS variables
- [Source: planning-artifacts/ux-design-specification.md#Layout Zones] - Sidebar + narrative layout
- [Source: planning-artifacts/ux-design-specification.md#Responsive Strategy] - Viewport handling
- [Source: planning-artifacts/architecture.md#Streamlit Integration] - Session state keys
- [Source: models.py#populate_game_state] - Game state factory
- [Source: config.py#load_character_configs] - Character loading
- [Source: epics.md#Story 2.1] - Full acceptance criteria
- [Source: app.py] - Existing Streamlit entry point to extend

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

No debug issues encountered.

### Completion Notes List

- **Task 1**: Created comprehensive CSS theme file `styles/theme.css` with all UX-spec CSS variables (colors, typography, spacing), 240px sidebar layout, dark theme colors, and responsive viewport warning for <1024px screens.

- **Task 2**: Restructured `app.py` with proper sidebar/main layout using `st.sidebar` and `st.container`. Added `load_css()` function for CSS injection, `render_sidebar()` for sidebar content, `render_main_content()` for narrative area, and `render_viewport_warning()` for narrow screen handling.

- **Task 3**: Implemented `initialize_session_state()` function that initializes `st.session_state["game"]` using existing `populate_game_state()`, sets `ui_mode` to "watch", and `controlled_character` to None. Function is idempotent - won't overwrite existing state.

- **Task 4**: Created placeholder UI components including mode indicator in sidebar header, party panel that lists characters from GameState with their class colors, session header placeholder, and narrative container placeholder.

- **Task 5**: Added 14 new tests covering CSS file existence, CSS variable validation, sidebar width rules, viewport warning styles, `load_css()` function, session state initialization (game, ui_mode, controlled_character), and idempotency.

### File List

- `styles/theme.css` - Modified (expanded from placeholder to full theme implementation)
- `app.py` - Modified (restructured with sidebar/main layout, CSS injection, session state init)
- `tests/test_app.py` - Modified (added 11 new tests, updated 3 existing tests)

## Change Log

- 2026-01-27: Story 2.1 implemented - Streamlit Application Shell with campfire theme CSS, sidebar/main layout, session state initialization, and placeholder UI components. All 267 tests passing (14 new tests for this story).
- 2026-01-27: Code review fixes applied:
  - Removed inline styles from app.py (Issues #2, #3) - replaced with CSS classes
  - Added Google Fonts @import for Lora, Inter, JetBrains Mono (Issue #5)
  - Added `.character-class` CSS class using `--text-system` and `--text-secondary` variables
  - Added `.narrative-placeholder` CSS class for italic placeholder text
  - Changed `.character-card` background from `--bg-secondary` to `--bg-message` for better contrast
