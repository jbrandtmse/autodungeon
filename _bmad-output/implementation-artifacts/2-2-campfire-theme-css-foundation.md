# Story 2.2: Campfire Theme & CSS Foundation

Status: done

## Story

As a **user**,
I want **a warm, campfire-themed visual design with dark mode**,
so that **the experience feels like gathering around a table, not using a productivity tool**.

## Acceptance Criteria

1. **Given** the styles/theme.css file
   **When** the application loads
   **Then** custom CSS is injected via `st.markdown` with `unsafe_allow_html=True`

2. **Given** the color palette
   **When** viewing the application
   **Then** I see:
   - Background: #1A1612 (deep warm black)
   - Secondary background: #2D2520 (warm gray-brown)
   - Message bubbles: #3D3530
   - Primary text: #F5E6D3 (warm off-white)
   - Accent: #E8A849 (amber)

3. **Given** the character color variables
   **When** viewing character-attributed content
   **Then** colors match: DM (#D4A574 gold), Fighter (#C45C4A red), Rogue (#6B8E6B green), Wizard (#7B68B8 purple), Cleric (#4A90A4 blue)

4. **Given** the typography system
   **When** viewing narrative text
   **Then** it uses Lora font at 17-18px with 1.6 line height
   **And** UI elements use Inter font at 13-14px

5. **Given** the overall aesthetic
   **When** using the application in the evening
   **Then** the warm tones reduce eye strain and feel inviting

## Tasks / Subtasks

- [x] Task 1: Extend CSS with full theme component styling (AC: #2, #3, #5)
  - [x] 1.1 Add DM message styling (gold border, italic Lora text, 18px)
  - [x] 1.2 Add PC message styling (character-colored borders, "Name, the Class:" attribution format)
  - [x] 1.3 Add message bubble styling with rounded corners and proper spacing
  - [x] 1.4 Add action/narration italic styling vs dialogue regular styling
  - [x] 1.5 Add justified text alignment for manuscript feel

- [x] Task 2: Implement session header styling (AC: #4)
  - [x] 2.1 Add chronicle-style session title (centered, Lora 24px, gold color)
  - [x] 2.2 Add session subtitle with Inter font in secondary text color
  - [x] 2.3 Add border-bottom separator styling

- [x] Task 3: Enhance character card styling for party panel (AC: #3, #4)
  - [x] 3.1 Update character card with proper character-color left border
  - [x] 3.2 Add character name styling (14px, 600 weight, character color)
  - [x] 3.3 Add character class styling (13px, secondary text color)
  - [x] 3.4 Add controlled state styling (glow effect, filled background)

- [x] Task 4: Implement Drop-In button styling (AC: #3, #5)
  - [x] 4.1 Add outline button default state (character-colored border)
  - [x] 4.2 Add hover state (fills with character color)
  - [x] 4.3 Add active/controlled state (filled, shows "Release")
  - [x] 4.4 Add button transitions for smooth interactions

- [x] Task 5: Enhance mode indicator styling (AC: #2, #5)
  - [x] 5.1 Add Watch Mode styling (green tint, pulsing dot animation)
  - [x] 5.2 Add Play Mode styling (amber tint with character color)
  - [x] 5.3 Add pulse animation keyframes
  - [x] 5.4 Add badge/pill styling with proper spacing

- [x] Task 6: Add Streamlit widget theme overrides (AC: #2, #4, #5)
  - [x] 6.1 Style input fields (dark background, warm border on focus)
  - [x] 6.2 Style buttons following hierarchy (primary amber, secondary outline)
  - [x] 6.3 Style selectbox/dropdown elements
  - [x] 6.4 Style expanders and containers

- [x] Task 7: Write tests for theme compliance
  - [x] 7.1 Test all required CSS variables are defined
  - [x] 7.2 Test DM message class has correct styling properties
  - [x] 7.3 Test PC message classes exist with character colors
  - [x] 7.4 Test pulse animation keyframes are defined
  - [x] 7.5 Test Lora and Inter fonts are properly imported

## Dev Notes

### Existing CSS Foundation (from Story 2.1)

**Story 2.1 already implemented:**
- All CSS variables (colors, fonts, spacing) are defined in `:root`
- Google Fonts import for Lora, Inter, JetBrains Mono
- Sidebar 240px fixed width styling
- Base layout with dark theme background
- Viewport warning for <1024px screens
- Basic character card placeholder
- Basic mode indicator placeholder

**This story extends the CSS with:**
- Full message component styling (DM and PC messages)
- Session header chronicle styling
- Enhanced character cards with character colors
- Drop-In button states and animations
- Mode indicator with pulse animation
- Streamlit widget theme overrides

### CSS Component Specifications (from UX Design Specification)

#### DM Message Block

Per UX spec, DM messages have special narrator styling:

```css
.dm-message {
    background: var(--bg-message);        /* #3D3530 */
    border-left: 4px solid var(--color-dm); /* #D4A574 */
    padding: var(--space-md) var(--space-lg); /* 16px 24px */
    margin-bottom: var(--space-md);       /* 16px */
    border-radius: 0 8px 8px 0;
}

.dm-message p {
    font-family: Lora, Georgia, serif;
    font-size: 18px;
    line-height: 1.6;
    color: var(--text-primary);           /* #F5E6D3 */
    font-style: italic;
    text-align: justify;
    margin: 0;
}
```

[Source: planning-artifacts/ux-design-specification.md#Narrative Message (DM)]

#### PC Message Block

Per UX spec, PC messages show "Name, the Class:" attribution:

```css
.pc-message {
    background: var(--bg-message);        /* #3D3530 */
    padding: var(--space-md);             /* 16px */
    margin-bottom: var(--space-md);       /* 16px */
    border-radius: 8px;
    border-left: 3px solid var(--character-color);
}

.pc-attribution {
    font-family: Lora, Georgia, serif;
    font-size: 14px;
    font-weight: 600;
    color: var(--character-color);
    margin-bottom: var(--space-xs);       /* 4px */
}

.pc-message p {
    font-family: Lora, Georgia, serif;
    font-size: 17px;
    line-height: 1.6;
    color: var(--text-primary);           /* #F5E6D3 */
    text-align: justify;
    margin: 0;
}

.pc-message .action-text {
    font-style: italic;
    color: var(--text-secondary);         /* #B8A896 */
}
```

[Source: planning-artifacts/ux-design-specification.md#Narrative Message (PC)]

#### Character-Specific Message Classes

Create per-character classes for border coloring:

```css
.pc-message.fighter { border-left-color: var(--color-fighter); }
.pc-message.rogue { border-left-color: var(--color-rogue); }
.pc-message.wizard { border-left-color: var(--color-wizard); }
.pc-message.cleric { border-left-color: var(--color-cleric); }

.pc-attribution.fighter { color: var(--color-fighter); }
.pc-attribution.rogue { color: var(--color-rogue); }
.pc-attribution.wizard { color: var(--color-wizard); }
.pc-attribution.cleric { color: var(--color-cleric); }
```

#### Session Header Styling

Per UX spec, chronicle-style header:

```css
.session-header {
    text-align: center;
    padding: var(--space-lg) 0;           /* 24px */
    border-bottom: 1px solid var(--bg-secondary);
    margin-bottom: var(--space-lg);
}

.session-title {
    font-family: Lora, Georgia, serif;
    font-size: 24px;
    font-weight: 600;
    color: var(--color-dm);               /* #D4A574 */
    letter-spacing: 0.05em;
    margin: 0;
}

.session-subtitle {
    font-family: Inter, system-ui, sans-serif;
    font-size: 13px;
    color: var(--text-secondary);         /* #B8A896 */
    margin-top: var(--space-xs);
}
```

[Source: planning-artifacts/ux-design-specification.md#Session Header]

#### Enhanced Character Card Styling

Per UX spec, character cards with character-specific colors:

```css
.character-card {
    background: var(--bg-secondary);      /* #2D2520 */
    border-radius: 8px;
    padding: var(--space-md);             /* 16px */
    margin-bottom: var(--space-sm);       /* 8px */
    border-left: 3px solid var(--character-color);
}

.character-card.controlled {
    background: var(--bg-message);        /* #3D3530 */
    border-left-width: 4px;
    box-shadow: 0 0 12px rgba(232, 168, 73, 0.2);
}

.character-name {
    font-family: Inter, system-ui, sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: var(--character-color);
}

.character-card.fighter { border-left-color: var(--color-fighter); }
.character-card.rogue { border-left-color: var(--color-rogue); }
.character-card.wizard { border-left-color: var(--color-wizard); }
.character-card.cleric { border-left-color: var(--color-cleric); }

.character-name.fighter { color: var(--color-fighter); }
.character-name.rogue { color: var(--color-rogue); }
.character-name.wizard { color: var(--color-wizard); }
.character-name.cleric { color: var(--color-cleric); }
```

[Source: planning-artifacts/ux-design-specification.md#Character Card]

#### Drop-In Button Styling

Per UX spec, button with character theming and states:

```css
.drop-in-button {
    background: transparent;
    border: 1px solid var(--character-color);
    color: var(--character-color);
    border-radius: 4px;
    padding: 6px 12px;
    font-family: Inter;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s ease;
    width: 100%;
    margin-top: var(--space-xs);
}

.drop-in-button:hover {
    background: var(--character-color);
    color: var(--bg-primary);
}

.drop-in-button.active {
    background: var(--character-color);
    color: var(--bg-primary);
}

.drop-in-button.fighter { border-color: var(--color-fighter); color: var(--color-fighter); }
.drop-in-button.fighter:hover { background: var(--color-fighter); }
.drop-in-button.rogue { border-color: var(--color-rogue); color: var(--color-rogue); }
.drop-in-button.rogue:hover { background: var(--color-rogue); }
.drop-in-button.wizard { border-color: var(--color-wizard); color: var(--color-wizard); }
.drop-in-button.wizard:hover { background: var(--color-wizard); }
.drop-in-button.cleric { border-color: var(--color-cleric); color: var(--color-cleric); }
.drop-in-button.cleric:hover { background: var(--color-cleric); }
```

[Source: planning-artifacts/ux-design-specification.md#Character Card]

#### Mode Indicator Styling

Per UX spec, Watch/Play mode badges with animation:

```css
.mode-indicator {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);                 /* 4px */
    padding: 4px 12px;
    border-radius: 16px;
    font-family: Inter, system-ui, sans-serif;
    font-size: 12px;
    font-weight: 500;
}

.mode-indicator.watch {
    background: rgba(107, 142, 107, 0.2); /* Success green, transparent */
    color: #6B8E6B;
}

.mode-indicator.play {
    background: rgba(232, 168, 73, 0.2);  /* Accent amber, transparent */
    color: var(--accent-warm);            /* #E8A849 */
}

.mode-indicator .pulse-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
}
```

[Source: planning-artifacts/ux-design-specification.md#Mode Indicator]

#### Input Context Bar (for Play Mode)

```css
.input-context {
    background: var(--bg-secondary);      /* #2D2520 */
    border-left: 3px solid var(--character-color);
    padding: var(--space-sm) var(--space-md); /* 8px 16px */
    margin-bottom: var(--space-sm);
    border-radius: 0 4px 4px 0;
}

.input-context-text {
    font-family: Inter, system-ui, sans-serif;
    font-size: 13px;
    color: var(--text-secondary);
}

.input-context-character {
    color: var(--character-color);
    font-weight: 500;
}
```

[Source: planning-artifacts/ux-design-specification.md#Input Context Bar]

### Streamlit Widget Overrides

Style native Streamlit widgets to match campfire theme:

```css
/* Text inputs and text areas */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background-color: var(--bg-secondary);
    color: var(--text-primary);
    border: 1px solid var(--bg-message);
    border-radius: 4px;
    font-family: var(--font-ui);
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--accent-warm);
    box-shadow: 0 0 0 1px var(--accent-warm);
}

/* Buttons - following hierarchy */
.stButton > button {
    background-color: var(--accent-warm);
    color: var(--bg-primary);
    border: none;
    border-radius: 4px;
    font-family: var(--font-ui);
    font-weight: 500;
    transition: all 0.15s ease;
}

.stButton > button:hover {
    background-color: #D49A3D; /* slightly darker amber */
}

/* Secondary button variant */
.stButton > button[kind="secondary"] {
    background-color: transparent;
    border: 1px solid var(--text-secondary);
    color: var(--text-primary);
}

/* Selectbox styling */
.stSelectbox > div > div {
    background-color: var(--bg-secondary);
    border-color: var(--bg-message);
}

.stSelectbox [data-baseweb="select"] {
    background-color: var(--bg-secondary);
}

/* Expander styling */
.streamlit-expanderHeader {
    background-color: var(--bg-secondary);
    color: var(--text-primary);
    border-radius: 4px;
}

/* Spinner styling */
.stSpinner > div {
    border-top-color: var(--accent-warm);
}
```

### Previous Story Intelligence (from Story 2.1)

**Key Learnings:**
- CSS injection works via `st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)`
- `load_css()` function already exists in `app.py` to load from `styles/theme.css`
- Character color variables already defined in `:root`
- Google Fonts already imported (Lora, Inter, JetBrains Mono)
- Story 2.1 created placeholder classes that need enhancement

**Files Modified in Story 2.1:**
- `styles/theme.css` - Extended with all CSS variables and base styling
- `app.py` - Added CSS injection and layout structure
- `tests/test_app.py` - Added 14 tests for CSS and session state

**Pattern: CSS Class Application in Python**

Story 2.3+ will use Python to generate HTML with these CSS classes:

```python
def render_dm_message(content: str) -> None:
    """Render DM narration with campfire styling."""
    st.markdown(
        f'''<div class="dm-message">
            <p>{content}</p>
        </div>''',
        unsafe_allow_html=True
    )

def render_pc_message(character: str, char_class: str, content: str) -> None:
    """Render PC dialogue with character styling."""
    class_slug = char_class.lower()
    st.markdown(
        f'''<div class="pc-message {class_slug}">
            <span class="pc-attribution {class_slug}">{character}, the {char_class}:</span>
            <p>{content}</p>
        </div>''',
        unsafe_allow_html=True
    )
```

### Git Intelligence (from Recent Commits)

**Recent commit patterns (4699962):**
- Story implementations follow task breakdown exactly
- Code review fixes applied in same commit
- Tests added for each implementation
- All 267 tests passing

**Files touched in last commit:**
- `styles/theme.css` - Extended from placeholder to full theme (this story continues extending it)
- `app.py` - Layout restructure (keep existing structure)
- `tests/test_app.py` - Added CSS and session state tests

### Architecture Compliance

Per architecture.md, this story:
- Keeps all CSS in `styles/theme.css` (single theme file)
- Uses CSS variables for all colors (not hardcoded values)
- Follows 8px base spacing grid
- Uses established font stack (Lora narrative, Inter UI)

### What This Story Does NOT Do

- Does NOT implement message rendering logic (Story 2.3: Narrative Message Display)
- Does NOT implement Drop-In button functionality (Story 2.4: Party Panel & Character Cards)
- Does NOT implement session title/turn counter updates (Story 2.5: Session Header & Controls)
- Does NOT implement auto-scroll or real-time updates (Story 2.6: Real-time Narrative Flow)
- Does NOT add Python rendering functions (only CSS classes)

This story creates the CSS foundation that later stories will use to render content.

### FR Coverage

| FR | Description | Implementation |
|----|-------------|----------------|
| FR26 | Visual distinction DM/PC/actions | DM and PC message CSS classes with distinct styling |
| FR27 | Character attribution per message | "Name, the Class:" attribution styling |
| FR29 (partial) | Current turn highlighted | Session header and narrative styling prepared |
| FR30 (partial) | Drop-In controls per character | Drop-In button CSS with character colors |

[Source: prd.md#Viewer Interface, epics.md#Story 2.2]

### Project Structure Notes

- All CSS goes in `styles/theme.css` (extend existing file)
- No new Python files needed
- Tests verify CSS properties and class definitions
- Flat layout maintained per architecture

### Testing Strategy

Tests should verify:
1. All required CSS classes are defined (`.dm-message`, `.pc-message`, `.character-card`, etc.)
2. CSS variables are correctly referenced in rules
3. Character-specific classes exist for all characters
4. Pulse animation keyframes are defined
5. Media query for dark theme is applied

Example test pattern:

```python
def test_dm_message_styling():
    """Test DM message CSS class has correct properties."""
    css = load_css()
    assert ".dm-message" in css
    assert "border-left" in css
    assert "var(--color-dm)" in css
    assert "font-style: italic" in css

def test_pc_message_character_classes():
    """Test PC message classes exist for all characters."""
    css = load_css()
    for char in ["fighter", "rogue", "wizard", "cleric"]:
        assert f".pc-message.{char}" in css
        assert f"var(--color-{char})" in css

def test_pulse_animation_defined():
    """Test pulse animation keyframes are defined."""
    css = load_css()
    assert "@keyframes pulse" in css
```

### References

- [Source: planning-artifacts/ux-design-specification.md#Visual Design Foundation] - All visual specs
- [Source: planning-artifacts/ux-design-specification.md#Component Strategy] - Component CSS specs
- [Source: planning-artifacts/ux-design-specification.md#UX Consistency Patterns] - Animation and state patterns
- [Source: planning-artifacts/architecture.md#Implementation Patterns] - CSS variable conventions
- [Source: epics.md#Story 2.2] - Full acceptance criteria
- [Source: styles/theme.css] - Existing CSS to extend
- [Source: _bmad-output/implementation-artifacts/2-1-streamlit-application-shell.md] - Previous story learnings

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- All 296 tests pass (29 new tests for Story 2.2)
- Ruff linting passes
- Code formatting applied

### Completion Notes List

- Task 1: Implemented DM message styling with `.dm-message` class using gold border (`var(--color-dm)`), italic Lora font, 18px text, justified alignment. PC message styling with `.pc-message` class supporting character-specific borders via `.pc-message.fighter`, `.pc-message.rogue`, `.pc-message.wizard`, `.pc-message.cleric`. Added `.pc-attribution` classes for character name coloring and `.action-text` for italic action text styling.

- Task 2: Enhanced `.session-header` with chronicle-style centered layout, added `.session-title` (Lora 24px, gold `var(--color-dm)`, letter-spacing 0.05em) and `.session-subtitle` (Inter 13px, secondary text color) with border-bottom separator.

- Task 3: Enhanced `.character-card` with character-specific border colors via `.character-card.fighter/.rogue/.wizard/.cleric`, added `.character-card.controlled` with glow effect (`box-shadow: 0 0 12px rgba(232, 168, 73, 0.2)`), added `.character-name` with character-specific color classes.

- Task 4: Implemented `.drop-in-button` with outline style, character-specific border/text colors, hover state that fills with character color, `.drop-in-button.active` for controlled state with amber fill, smooth 0.15s transition.

- Task 5: Enhanced `.mode-indicator` with flexbox layout, added `.mode-indicator.watch` (green tint background) and `.mode-indicator.play` (amber tint), implemented `.pulse-dot` with `@keyframes pulse` animation (2s ease-in-out infinite, scale 0.8-1.0, opacity 0.5-1.0).

- Task 6: Added comprehensive Streamlit widget overrides for `.stTextInput`, `.stTextArea` (dark background, warm focus border), `.stButton` (amber primary, secondary outline variant), `.stSelectbox`, `.streamlit-expanderHeader`, and `.stSpinner`.

- Task 7: Added 29 new tests in `tests/test_app.py` covering all CSS classes and styling requirements across 8 test classes: `TestDMMessageStyling`, `TestPCMessageStyling`, `TestSessionHeaderStyling`, `TestCharacterCardEnhancement`, `TestDropInButtonStyling`, `TestModeIndicatorEnhancement`, `TestStreamlitWidgetOverrides`, `TestFontsImport`.

### File List

- `styles/theme.css` - Extended with full theme component styling (DM/PC messages, session header, character cards, drop-in buttons, mode indicators, Streamlit widget overrides)
- `tests/test_app.py` - Added 29 new tests for Story 2.2 CSS compliance (now 37 tests after code review fixes)
- `app.py` - Updated HTML rendering to use proper CSS classes (code review fix)

### Change Log

- 2026-01-27: Story 2.2 implementation complete - Extended CSS theme with DM/PC message styling, session header, character cards, drop-in buttons, mode indicators, and Streamlit widget overrides. Added 29 new tests for CSS compliance verification.
- 2026-01-27: Code review fixes applied:
  - Fixed session header to use `.session-title` and `.session-subtitle` CSS classes
  - Fixed mode indicator to use `.watch`/`.play` classes and include `.pulse-dot` element
  - Fixed character cards to use character-specific CSS classes (`.character-card.fighter`, etc.)
  - Fixed character names to use `.character-name` class with character-specific coloring
  - Added Drop-In button to character cards for visual CSS verification
  - Added 8 new tests for improved CSS property verification specificity
  - Total tests now: 51 in test_app.py, 304 overall passing

