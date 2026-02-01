# Story 8.2: Character Sheet Viewer UI

Status: done

## Story

As a **user**,
I want **to view any character's full sheet in the UI**,
so that **I can see their stats, abilities, and inventory at any time**.

## Acceptance Criteria

1. **Given** the party panel in the sidebar
   **When** I click on a character's name (not Drop-In button)
   **Then** a character sheet modal/panel opens

2. **Given** the character sheet viewer
   **When** displayed
   **Then** it shows organized sections:
   - Header: Name, Race, Class, Level
   - Abilities: Six ability scores with modifiers
   - Combat: AC, HP bar, Initiative, Speed
   - Skills: All 18 skills with proficiency indicators
   - Equipment: Weapons, armor, inventory
   - Spells (if caster): Cantrips, prepared spells, spell slots
   - Features: Class features, racial traits
   - Personality: Traits, ideals, bonds, flaws

3. **Given** the HP display
   **When** current HP is below max
   **Then** a visual bar shows remaining HP with color coding (green/yellow/red)

4. **Given** spell slots
   **When** displayed
   **Then** each level shows filled/empty dots for used/available slots

5. **Given** the character sheet
   **When** viewing during an active game
   **Then** it shows real-time values (HP changes, spell slot usage, etc.)

## Tasks / Subtasks

- [ ] Task 1: Create character sheet modal structure (AC: #1, #2)
  - [ ] 1.1 Add `@st.dialog("Character Sheet", width="large")` decorator function `render_character_sheet_modal(character_name: str)`
  - [ ] 1.2 Create mock/sample CharacterSheet factory function for testing (`create_sample_character_sheet(character_class: str)`)
  - [ ] 1.3 Implement modal open handler when character name is clicked
  - [ ] 1.4 Store active character sheet in session state (`st.session_state["viewing_character_sheet"]`)

- [ ] Task 2: Implement character sheet header section (AC: #2)
  - [ ] 2.1 Create `render_sheet_header(sheet: CharacterSheet)` function
  - [ ] 2.2 Display Name, Race, Class, Level in header layout
  - [ ] 2.3 Include character-specific color accent (from CharacterConfig if available)
  - [ ] 2.4 Add proficiency bonus display in header

- [ ] Task 3: Implement ability scores section (AC: #2)
  - [ ] 3.1 Create `render_ability_scores(sheet: CharacterSheet)` function
  - [ ] 3.2 Display all six abilities: STR, DEX, CON, INT, WIS, CHA
  - [ ] 3.3 Show both raw score and computed modifier (e.g., "14 (+2)")
  - [ ] 3.4 Use 3x2 grid layout for ability score cards
  - [ ] 3.5 Highlight saving throw proficiencies with indicator

- [ ] Task 4: Implement combat stats section (AC: #2, #3)
  - [ ] 4.1 Create `render_combat_stats(sheet: CharacterSheet)` function
  - [ ] 4.2 Display AC, Initiative modifier, Speed
  - [ ] 4.3 Create HP bar component with current/max display
  - [ ] 4.4 Implement HP color coding: green (>50%), yellow (25-50%), red (<25%)
  - [ ] 4.5 Show temporary HP if present
  - [ ] 4.6 Display hit dice (total and remaining)
  - [ ] 4.7 Show death saves status if character is at 0 HP

- [ ] Task 5: Implement skills section (AC: #2)
  - [ ] 5.1 Create `render_skills_section(sheet: CharacterSheet)` function
  - [ ] 5.2 List all 18 D&D 5e skills organized by ability
  - [ ] 5.3 Show proficiency indicator (filled circle for proficient, double for expertise)
  - [ ] 5.4 Calculate and display skill modifier (ability mod + proficiency if applicable)
  - [ ] 5.5 Use collapsible expander for skills to save space

- [ ] Task 6: Implement equipment section (AC: #2)
  - [ ] 6.1 Create `render_equipment_section(sheet: CharacterSheet)` function
  - [ ] 6.2 Display weapons with damage dice, damage type, properties
  - [ ] 6.3 Display worn armor with AC contribution
  - [ ] 6.4 List inventory items with quantities
  - [ ] 6.5 Show currency (gold, silver, copper)

- [ ] Task 7: Implement spellcasting section (AC: #2, #4)
  - [ ] 7.1 Create `render_spellcasting_section(sheet: CharacterSheet)` function
  - [ ] 7.2 Conditionally show only for characters with spellcasting_ability set
  - [ ] 7.3 Display spell save DC and spell attack bonus
  - [ ] 7.4 List cantrips
  - [ ] 7.5 List prepared/known spells grouped by level
  - [ ] 7.6 Implement spell slot visualization with filled/empty dots
  - [ ] 7.7 Show current/max slots for each spell level

- [ ] Task 8: Implement features and traits section (AC: #2)
  - [ ] 8.1 Create `render_features_section(sheet: CharacterSheet)` function
  - [ ] 8.2 Display class features list
  - [ ] 8.3 Display racial traits list
  - [ ] 8.4 Display feats if any
  - [ ] 8.5 Use collapsible expander for features to save space

- [ ] Task 9: Implement personality section (AC: #2)
  - [ ] 9.1 Create `render_personality_section(sheet: CharacterSheet)` function
  - [ ] 9.2 Display personality traits, ideals, bonds, flaws
  - [ ] 9.3 Display backstory in collapsible expander
  - [ ] 9.4 Show active conditions if any

- [ ] Task 10: Make character name clickable in party panel (AC: #1)
  - [ ] 10.1 Modify `render_character_card()` to make name a clickable element
  - [ ] 10.2 Separate click handling for name (opens sheet) vs Drop-In button (controls character)
  - [ ] 10.3 Add cursor pointer style and hover effect to character name
  - [ ] 10.4 Ensure keyboard accessibility for name click

- [ ] Task 11: Implement real-time data binding (AC: #5)
  - [ ] 11.1 Character sheet modal reads from GameState's character_sheets dict
  - [ ] 11.2 For MVP: use sample sheets stored in session state until Story 8.3 integrates with GameState
  - [ ] 11.3 Modal refresh on game state changes

- [ ] Task 12: Add CSS styling for character sheet viewer
  - [ ] 12.1 Create character-sheet specific CSS classes in theme.css
  - [ ] 12.2 Style HP bar with gradient colors
  - [ ] 12.3 Style ability score cards
  - [ ] 12.4 Style spell slot dots (filled vs empty)
  - [ ] 12.5 Maintain campfire theme consistency

- [ ] Task 13: Write tests for character sheet viewer
  - [ ] 13.1 Test `create_sample_character_sheet()` returns valid CharacterSheet
  - [ ] 13.2 Test HP color coding logic
  - [ ] 13.3 Test skill modifier calculation
  - [ ] 13.4 Test spell slot visualization logic
  - [ ] 13.5 Test HTML generation functions are XSS-safe

- [ ] Task 14: Run quality checks
  - [ ] 14.1 Run `ruff check .` and fix lint errors
  - [ ] 14.2 Run `ruff format .`
  - [ ] 14.3 Run `pyright .` and address type errors
  - [ ] 14.4 Run `pytest` and ensure all tests pass

## Dev Notes

### Architecture Context

This story implements the UI viewer for character sheets. The data model (CharacterSheet, Weapon, Armor, Spell, etc.) was implemented in Story 8.1 and is available in `models.py`.

**Key Dependencies:**
- Story 8.1 (Character Sheet Data Model) - DONE - provides all Pydantic models
- Epic 6 patterns (config modal) - provides `@st.dialog` decorator pattern
- Epic 2 patterns (party panel) - provides character card rendering patterns

### Implementation Strategy

**Modal Pattern (from Story 6.1):**

The configuration modal in app.py provides the exact pattern to follow:

```python
@st.dialog("Character Sheet", width="large")
def render_character_sheet_modal(character_name: str) -> None:
    """Render character sheet modal for the specified character.

    Uses @st.dialog decorator for modal container.
    Follows Story 6.1 modal pattern.
    """
    # Get character sheet from session state or create sample
    sheet = get_character_sheet(character_name)
    if sheet is None:
        st.error(f"Character sheet not found for {character_name}")
        return

    # Render sections
    render_sheet_header(sheet)
    render_ability_scores(sheet)
    render_combat_stats(sheet)
    # ... etc
```

**Opening the Modal:**

Streamlit dialogs are opened by calling the decorated function. The pattern is:

```python
# In session state
st.session_state["viewing_character_sheet"] = None  # or character name

# To open modal, call the function
if st.session_state.get("viewing_character_sheet"):
    render_character_sheet_modal(st.session_state["viewing_character_sheet"])
```

### Character Name Click Handler

Modify `render_character_card()` in app.py to separate name click from Drop-In button:

```python
def render_character_card(
    agent_key: str, char_config: CharacterConfig, controlled: bool
) -> None:
    """Render a single character card with clickable name and Drop-In button."""
    class_slug = "".join(
        c for c in char_config.character_class.lower() if c.isalnum() or c == "-"
    )
    controlled_class = " controlled" if controlled else ""

    # Character info section
    st.markdown(
        f'<div class="character-card-wrapper {class_slug}{controlled_class}">'
        f'<div class="character-card {class_slug}{controlled_class}">',
        unsafe_allow_html=True,
    )

    # Clickable character name (opens sheet)
    if st.button(
        char_config.name,
        key=f"view_sheet_{agent_key}",
        help="View character sheet"
    ):
        st.session_state["viewing_character_sheet"] = agent_key
        st.rerun()

    # Character class display
    st.markdown(
        f'<span class="character-class">{escape_html(char_config.character_class)}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Drop-In button (unchanged)
    button_label = get_drop_in_button_label(controlled)
    is_generating = st.session_state.get("is_generating", False)
    if st.button(button_label, key=f"drop_in_{agent_key}", disabled=is_generating):
        handle_drop_in_click(agent_key)
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
```

### Sample Character Sheet Factory

For testing the viewer before Story 8.3 integrates with GameState:

```python
def create_sample_character_sheet(character_class: str, name: str = "Sample") -> CharacterSheet:
    """Create a sample character sheet for UI testing.

    Args:
        character_class: D&D class (Fighter, Rogue, Wizard, Cleric)
        name: Character name

    Returns:
        A populated CharacterSheet instance
    """
    # Base stats vary by class
    class_stats = {
        "Fighter": {"strength": 16, "dexterity": 14, "constitution": 15,
                    "intelligence": 10, "wisdom": 12, "charisma": 8},
        "Rogue": {"strength": 10, "dexterity": 16, "constitution": 12,
                  "intelligence": 14, "wisdom": 12, "charisma": 14},
        "Wizard": {"strength": 8, "dexterity": 14, "constitution": 12,
                   "intelligence": 16, "wisdom": 14, "charisma": 10},
        "Cleric": {"strength": 14, "dexterity": 10, "constitution": 14,
                   "intelligence": 10, "wisdom": 16, "charisma": 12},
    }

    stats = class_stats.get(character_class, class_stats["Fighter"])

    return CharacterSheet(
        name=name,
        race="Human",  # Default for sample
        character_class=character_class,
        level=5,
        background="Folk Hero",
        alignment="Neutral Good",
        **stats,
        armor_class=16,
        hit_points_max=45,
        hit_points_current=32,  # Show some damage
        hit_dice="5d10",
        hit_dice_remaining=3,
        skill_proficiencies=["Athletics", "Perception", "Intimidation"],
        # ... etc
    )
```

### HP Bar Color Coding Logic

```python
def get_hp_color(current: int, max_hp: int) -> str:
    """Get HP bar color based on percentage.

    Args:
        current: Current HP
        max_hp: Maximum HP

    Returns:
        CSS color code: green (>50%), yellow (25-50%), red (<25%)
    """
    if max_hp <= 0:
        return "#C45C4A"  # Red for invalid

    percentage = (current / max_hp) * 100

    if percentage > 50:
        return "#6B8E6B"  # Green (Rogue color)
    elif percentage > 25:
        return "#E8A849"  # Amber/Yellow (accent-warm)
    else:
        return "#C45C4A"  # Red (Fighter color)


def render_hp_bar_html(current: int, max_hp: int, temp: int = 0) -> str:
    """Generate HTML for HP bar visualization.

    Args:
        current: Current HP
        max_hp: Maximum HP
        temp: Temporary HP

    Returns:
        HTML string for HP bar
    """
    percentage = min(100, (current / max_hp) * 100) if max_hp > 0 else 0
    color = get_hp_color(current, max_hp)

    temp_display = f" (+{temp})" if temp > 0 else ""

    return (
        f'<div class="hp-container">'
        f'<div class="hp-bar-bg">'
        f'<div class="hp-bar-fill" style="width: {percentage}%; background-color: {color};"></div>'
        f'</div>'
        f'<span class="hp-text">{current}/{max_hp}{temp_display} HP</span>'
        f'</div>'
    )
```

### Spell Slot Visualization

```python
def render_spell_slots_html(spell_slots: dict[int, SpellSlots]) -> str:
    """Generate HTML for spell slot visualization.

    Args:
        spell_slots: Dict mapping spell level to SpellSlots model

    Returns:
        HTML string with filled/empty dots for each level
    """
    if not spell_slots:
        return ""

    html_parts = ['<div class="spell-slots-container">']

    for level in sorted(spell_slots.keys()):
        slots = spell_slots[level]
        if slots.max == 0:
            continue

        filled = slots.current
        empty = slots.max - slots.current

        dots = ('●' * filled) + ('○' * empty)

        html_parts.append(
            f'<div class="spell-slot-row">'
            f'<span class="spell-level">Level {level}:</span>'
            f'<span class="spell-dots">{dots}</span>'
            f'</div>'
        )

    html_parts.append('</div>')
    return ''.join(html_parts)
```

### Skills with Ability Mapping

All 18 D&D 5e skills mapped to their governing ability:

```python
SKILLS_BY_ABILITY: dict[str, list[str]] = {
    "strength": ["Athletics"],
    "dexterity": ["Acrobatics", "Sleight of Hand", "Stealth"],
    "intelligence": ["Arcana", "History", "Investigation", "Nature", "Religion"],
    "wisdom": ["Animal Handling", "Insight", "Medicine", "Perception", "Survival"],
    "charisma": ["Deception", "Intimidation", "Performance", "Persuasion"],
}


def calculate_skill_modifier(
    sheet: CharacterSheet, skill: str, ability: str
) -> int:
    """Calculate total skill modifier.

    Args:
        sheet: Character sheet
        skill: Skill name
        ability: Governing ability

    Returns:
        Total modifier (ability mod + proficiency if applicable)
    """
    ability_mod = sheet.get_ability_modifier(ability)

    if skill in sheet.skill_expertise:
        return ability_mod + (sheet.proficiency_bonus * 2)
    elif skill in sheet.skill_proficiencies:
        return ability_mod + sheet.proficiency_bonus
    else:
        return ability_mod
```

### CSS Additions for Character Sheet

Add to `styles/theme.css`:

```css
/* ==========================================================================
   Character Sheet Modal (Story 8.2)
   ========================================================================== */

.character-sheet-header {
    text-align: center;
    padding: 16px;
    border-bottom: 2px solid var(--accent-warm, #E8A849);
    margin-bottom: 16px;
}

.character-sheet-name {
    font-family: Lora, Georgia, serif;
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary, #F5E6D3);
    margin: 0;
}

.character-sheet-subtitle {
    font-family: Inter, system-ui, sans-serif;
    font-size: 14px;
    color: var(--text-secondary, #B8A896);
    margin: 4px 0 0 0;
}

/* Ability Score Cards */
.ability-score-card {
    background: var(--bg-message, #3D3530);
    border-radius: 8px;
    padding: 12px;
    text-align: center;
    border: 1px solid var(--bg-secondary, #2D2520);
}

.ability-name {
    font-family: Inter, system-ui, sans-serif;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary, #B8A896);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.ability-modifier {
    font-family: JetBrains Mono, monospace;
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary, #F5E6D3);
}

.ability-score {
    font-family: JetBrains Mono, monospace;
    font-size: 14px;
    color: var(--text-secondary, #B8A896);
}

/* HP Bar */
.hp-container {
    margin: 8px 0;
}

.hp-bar-bg {
    background: var(--bg-secondary, #2D2520);
    border-radius: 4px;
    height: 20px;
    overflow: hidden;
}

.hp-bar-fill {
    height: 100%;
    transition: width 0.3s ease;
}

.hp-text {
    font-family: JetBrains Mono, monospace;
    font-size: 14px;
    color: var(--text-primary, #F5E6D3);
    display: block;
    text-align: center;
    margin-top: 4px;
}

/* Spell Slots */
.spell-slots-container {
    margin: 8px 0;
}

.spell-slot-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 4px 0;
}

.spell-level {
    font-family: Inter, system-ui, sans-serif;
    font-size: 13px;
    color: var(--text-secondary, #B8A896);
    min-width: 60px;
}

.spell-dots {
    font-family: JetBrains Mono, monospace;
    font-size: 14px;
    color: var(--accent-warm, #E8A849);
    letter-spacing: 2px;
}

/* Skill Proficiency Indicators */
.skill-row {
    display: flex;
    align-items: center;
    padding: 4px 0;
    border-bottom: 1px solid var(--bg-secondary, #2D2520);
}

.skill-proficiency {
    width: 16px;
    font-size: 12px;
    color: var(--accent-warm, #E8A849);
}

.skill-name {
    flex: 1;
    font-family: Inter, system-ui, sans-serif;
    font-size: 13px;
    color: var(--text-primary, #F5E6D3);
}

.skill-modifier {
    font-family: JetBrains Mono, monospace;
    font-size: 13px;
    color: var(--text-secondary, #B8A896);
}

/* Section Headers */
.sheet-section-header {
    font-family: Inter, system-ui, sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: var(--accent-warm, #E8A849);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 16px 0 8px 0;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--bg-secondary, #2D2520);
}

/* Equipment List */
.equipment-item {
    font-family: Inter, system-ui, sans-serif;
    font-size: 13px;
    color: var(--text-primary, #F5E6D3);
    padding: 4px 0;
}

.equipment-detail {
    font-size: 12px;
    color: var(--text-secondary, #B8A896);
    margin-left: 8px;
}

/* Clickable Character Name in Party Panel */
.character-card .character-name-clickable {
    cursor: pointer;
    transition: color 0.2s ease;
}

.character-card .character-name-clickable:hover {
    color: var(--accent-warm, #E8A849);
    text-decoration: underline;
}
```

### Project Structure Notes

| File | Changes |
|------|---------|
| `app.py` | Add character sheet modal function, modify render_character_card() for clickable name, add sample sheet factory |
| `styles/theme.css` | Add character sheet viewer CSS classes |
| `tests/test_story_8_2_character_sheet_viewer.py` | New test file for viewer functions |

### Testing Strategy

**Unit Tests (pytest):**

```python
# tests/test_story_8_2_character_sheet_viewer.py

class TestSampleCharacterSheet:
    def test_create_fighter_sheet(self): ...
    def test_create_rogue_sheet(self): ...
    def test_create_wizard_sheet(self): ...
    def test_create_cleric_sheet(self): ...
    def test_sample_sheet_is_valid(self): ...

class TestHPBarRendering:
    def test_hp_color_green_above_50_percent(self): ...
    def test_hp_color_yellow_25_to_50_percent(self): ...
    def test_hp_color_red_below_25_percent(self): ...
    def test_hp_bar_html_structure(self): ...
    def test_hp_bar_with_temp_hp(self): ...

class TestSkillModifierCalculation:
    def test_base_skill_modifier(self): ...
    def test_proficient_skill_modifier(self): ...
    def test_expertise_skill_modifier(self): ...

class TestSpellSlotVisualization:
    def test_spell_slots_filled_dots(self): ...
    def test_spell_slots_empty_dots(self): ...
    def test_spell_slots_mixed(self): ...
    def test_empty_spell_slots_returns_empty(self): ...

class TestHTMLSafety:
    def test_name_html_escaped(self): ...
    def test_equipment_html_escaped(self): ...
```

### Edge Cases

1. **Non-caster characters** - Spellcasting section should not render if `spellcasting_ability` is None
2. **Character at 0 HP** - Show death saves section, HP bar fully red
3. **No equipped armor** - Show "Unarmored" or calculate base AC from DEX
4. **Empty inventory** - Show "No items" message
5. **Very long lists** - Use expanders to keep modal scrollable
6. **Missing CharacterSheet** - Show error/placeholder until Story 8.3 integrates

### What This Story Implements

1. **Modal dialog** for viewing character sheets (FR63)
2. **Organized sections** displaying all character data
3. **HP bar** with color-coded visualization
4. **Spell slot** dots visualization
5. **Clickable character names** in party panel
6. **Sample character sheets** for testing before full integration

### What This Story Does NOT Implement

- Character sheet storage in GameState (Story 8.3)
- DM tool calls to update sheets (Story 8.4)
- Sheet change notifications (Story 8.5)
- Editing character sheets (future enhancement)
- Character creation wizard (Epic 9)

### FR/NFR Coverage

| Requirement | Description | Implementation |
|-------------|-------------|----------------|
| FR63 | User can view any character's sheet in a dedicated UI panel | Character sheet modal with organized sections |

### References

- [Source: planning-artifacts/architecture.md#v1.1 Extension Architecture] - CharacterSheet model definition
- [Source: planning-artifacts/ux-design-specification.md#Visual Design Foundation] - Campfire theme colors and typography
- [Source: planning-artifacts/epics.md#Story 8.2] - Original story definition
- [Source: planning-artifacts/prd.md#FR60-FR66] - Character sheet functional requirements
- [Source: app.py:2669-2709] - Configuration modal pattern with @st.dialog
- [Source: app.py:3244-3285] - Character card rendering pattern
- [Source: models.py:723-900+] - CharacterSheet model implementation from Story 8.1
- [Source: implementation-artifacts/8-1-character-sheet-data-model.md] - Story 8.1 completion details

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Character sheet modal implemented with @st.dialog decorator
- All 9 sections implemented (header, abilities, combat, skills, equipment, spells, features, personality)
- HP bar with color coding (green >50%, yellow 25-50%, red <25%)
- Spell slot visualization with filled/empty dots
- Clickable character names in party panel

### File List

- `app.py` - Character sheet viewer functions, modal, clickable names, sample sheet factory
- `styles/theme.css` - Character sheet CSS classes and styling
- `tests/test_story_8_2_character_sheet_viewer.py` - Unit tests for viewer functions

---

## Senior Developer Review (AI)

**Review Date:** 2026-02-01
**Reviewer:** Claude Opus 4.5

### Review Summary

| Category | Count |
|----------|-------|
| HIGH Severity Issues | 2 (FIXED) |
| MEDIUM Severity Issues | 4 (FIXED) |
| LOW Severity Issues | 2 (1 FIXED, 1 documented) |

### Issues Found and Resolved

#### HIGH SEVERITY (FIXED)

1. **Task 4.7 NOT IMPLEMENTED - Death saves status when at 0 HP**
   - Story requirement: Show death saves when HP = 0
   - Finding: `render_combat_stats_html()` did not check for 0 HP or display death saves
   - Fix: Added `render_death_saves_html()` function and integrated into combat stats when HP <= 0
   - Files: `app.py:3753-3785`

2. **Missing ARIA labels for accessibility**
   - Story requirement: Task 10.4 requires keyboard accessibility
   - Finding: Character sheet modal and components had no ARIA labels for screen readers
   - Fix: Added role and aria-label attributes to ability scores, HP bar, spell slots, combat stats
   - Files: `app.py` (multiple functions), `styles/theme.css`

#### MEDIUM SEVERITY (FIXED)

3. **Task 10.4 NOT FULLY IMPLEMENTED - Keyboard accessibility**
   - Finding: No visual focus indicator style for view_sheet buttons
   - Fix: Added `:focus-visible` CSS styles for character name buttons
   - Files: `styles/theme.css:2994-2999`

4. **No responsive CSS for character sheet on mobile**
   - Finding: Character sheet modal had no @media queries for smaller screens
   - Fix: Added responsive breakpoints for ability grid, combat stats, spell stats
   - Files: `styles/theme.css:3068-3080`

5. **Potential negative empty dots in spell slots**
   - Finding: If `slots.current > slots.max`, empty variable becomes negative
   - Fix: Added clamping with `max(0, min(...))` to prevent negative values
   - Files: `app.py:3395-3396`

6. **Missing import for DeathSaves**
   - Finding: DeathSaves model not imported to display death saves
   - Fix: Added DeathSaves to imports from models
   - Files: `app.py:52`

#### LOW SEVERITY

7. **Shield listed as weapon (FIXED)**
   - Finding: Fighter sample had "Shield" as a weapon with damage dice (not D&D 5e accurate)
   - Fix: Changed to "Javelin" which is a proper throwing weapon
   - Files: `app.py:3502-3507`

8. **Story tasks all marked [ ] but implementation exists (Documented)**
   - Finding: Tasks should be marked [x] since implementation is complete
   - Status: Left for user/dev to update task checkboxes

### Tests Added

- `TestDeathSavesDisplay` - 4 tests for death saves rendering
- `TestAccessibility` - 3 tests for ARIA labels and roles

### Verification

- All 43 tests pass
- Code formatted with ruff
- Type checking passes (no new errors introduced)

### Review Outcome

**APPROVED** - All HIGH and MEDIUM issues have been resolved. Story implementation meets acceptance criteria.
