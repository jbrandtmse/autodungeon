# Story 15.5: Combat UI Indicators

Status: ready-for-dev

## Epic

Epic 15: Combat Initiative System

## Story

As a **user watching a tactical combat encounter**,
I want **visual indicators in the Streamlit UI showing combat status, round number, initiative order, and current turn highlighting**,
So that **I can follow the tactical combat flow, know which combatant is acting, and see the initiative order at a glance without reading through narrative text**.

## Priority

Medium (UI enhancement -- combat functions correctly without this, but the user has no visual feedback about combat state, initiative order, or whose turn it is)

## Estimate

Medium (new render functions in app.py, new CSS classes in theme.css, integration into render_sidebar and render_main_content, comprehensive tests)

## Dependencies

- Story 15-1 (Combat State Model & Detection): **done** -- provides `CombatState` model with `active`, `round_number`, `initiative_order`, `initiative_rolls`, `npc_profiles` fields on `GameState`.
- Story 15-2 (Initiative Rolling & Turn Reordering): **done** -- populates `combat_state.initiative_order`, `combat_state.initiative_rolls`, `combat_state.npc_profiles`, `combat_state.round_number` when combat starts.
- Story 15-3 (Combat-Aware Graph Routing): **done** -- provides combat-aware routing using `initiative_order`, sets `current_turn` to `"dm:npc_name"` for NPC turns.
- Story 15-4 (DM Bookend & NPC Turns): **in-dev** -- no hard dependency. This story reads `combat_state` from game state, which is populated by 15-1/15-2/15-3. Story 15-4 affects DM prompt content but not the UI rendering of combat indicators.

## Acceptance Criteria

1. **Given** `combat_state.active` is `True`, **When** the main content area renders, **Then** a combat banner is displayed at the top of the narrative area showing "COMBAT - Round N" (where N is `combat_state.round_number`) with campfire-themed styling (amber accent, bold text).

2. **Given** `combat_state.active` is `False` (exploration/roleplay mode), **When** the main content area renders, **Then** no combat banner is displayed.

3. **Given** `combat_state.active` is `True`, **When** the sidebar renders, **Then** an initiative order panel is displayed below the party panel showing all combatants in initiative order with their initiative rolls.

4. **Given** the initiative order contains PC entries (e.g., `"shadowmere"`, `"thorin"`), **When** the initiative panel renders, **Then** PC names are displayed using their character display names (from the `characters` dict) with their character class color.

5. **Given** the initiative order contains NPC entries (e.g., `"dm:goblin_1"`, `"dm:klarg"`), **When** the initiative panel renders, **Then** NPC names are displayed using the `NpcProfile.name` field from `combat_state.npc_profiles` (e.g., "Goblin 1", "Klarg") with a distinct NPC styling (DM gold color).

6. **Given** `combat_state.active` is `True` and `current_turn` matches an entry in `initiative_order`, **When** the initiative panel renders, **Then** the current combatant's entry is visually highlighted with a CSS class (e.g., amber border or background tint) to indicate whose turn it is.

7. **Given** the initiative order contains a `"dm"` bookend entry at position 0, **When** the initiative panel renders, **Then** the bookend entry is either omitted from the display or shown as a subtle "Round Start" label (not as a combatant).

8. **Given** `combat_state.active` is `False`, **When** the sidebar renders, **Then** no initiative order panel is displayed.

9. **Given** the combat banner HTML, **When** tested in isolation (without Streamlit), **Then** `render_combat_banner_html()` returns correct HTML with round number, appropriate CSS classes, and proper HTML escaping.

10. **Given** the initiative order HTML, **When** tested in isolation (without Streamlit), **Then** `render_initiative_order_html()` returns correct HTML with combatant names, initiative rolls, current turn highlighting, and proper HTML escaping.

11. **Given** an NPC entry in initiative order whose key is not found in `npc_profiles`, **When** the initiative panel renders, **Then** it falls back to displaying the raw NPC key (e.g., "goblin_1") instead of crashing.

12. **Given** combat ends (combat_state.active transitions to False), **When** the UI re-renders, **Then** both the combat banner and initiative order panel disappear cleanly.

## Tasks / Subtasks

- [ ] Task 1: Add `render_combat_banner_html()` to `app.py` (AC: #1, #2, #9)
  - [ ] 1.1: Define `render_combat_banner_html(round_number: int) -> str` that generates HTML for the combat banner
  - [ ] 1.2: Use CSS class `combat-banner` with the round number displayed prominently
  - [ ] 1.3: Include a crossed-swords icon or text indicator (e.g., "COMBAT" in small caps) for visual distinction
  - [ ] 1.4: Return empty string if called with `round_number <= 0` (defensive, should not happen)

- [ ] Task 2: Add `render_combat_banner()` to `app.py` (AC: #1, #2, #12)
  - [ ] 2.1: Define `render_combat_banner() -> None` Streamlit wrapper function
  - [ ] 2.2: Read `combat_state` from `st.session_state["game"]`
  - [ ] 2.3: If `combat_state.active` is True, render the banner HTML via `st.markdown(..., unsafe_allow_html=True)`
  - [ ] 2.4: If `combat_state.active` is False or missing, render nothing

- [ ] Task 3: Add `render_initiative_order_html()` to `app.py` (AC: #3, #4, #5, #6, #7, #10, #11)
  - [ ] 3.1: Define `render_initiative_order_html(combat_state: CombatState, current_turn: str, characters: dict[str, CharacterConfig]) -> str`
  - [ ] 3.2: Iterate over `combat_state.initiative_order`, skipping the `"dm"` bookend entry (or rendering it as a subtle "Round Start" divider)
  - [ ] 3.3: For PC entries: look up display name from `characters` dict, determine character class for color styling, display initiative roll from `combat_state.initiative_rolls`
  - [ ] 3.4: For NPC entries (`"dm:npc_name"`): extract NPC key, look up `NpcProfile.name` from `combat_state.npc_profiles`, fall back to raw key if not found, use DM gold color styling
  - [ ] 3.5: Add `initiative-active` CSS class to the entry matching `current_turn`
  - [ ] 3.6: Wrap all entries in a container div with CSS class `initiative-order`
  - [ ] 3.7: Each entry uses CSS class `initiative-entry` (with optional `initiative-pc`, `initiative-npc`, `initiative-active` modifiers)
  - [ ] 3.8: Display initiative roll number next to each combatant name using `font-mono` style
  - [ ] 3.9: Escape all user-provided text (character names, NPC names) with `escape_html()`

- [ ] Task 4: Add `render_initiative_order()` to `app.py` (AC: #3, #8, #12)
  - [ ] 4.1: Define `render_initiative_order() -> None` Streamlit wrapper function
  - [ ] 4.2: Read `combat_state` and `current_turn` from `st.session_state["game"]`
  - [ ] 4.3: Read `characters` from game state for PC name resolution
  - [ ] 4.4: If `combat_state.active` is True, render initiative HTML via `st.markdown(..., unsafe_allow_html=True)`
  - [ ] 4.5: If `combat_state.active` is False or missing, render nothing

- [ ] Task 5: Add combat CSS classes to `styles/theme.css` (AC: #1, #6)
  - [ ] 5.1: Add `.combat-banner` class -- amber accent background tint, bold text, centered, JetBrains Mono font for "Round N", border matching campfire theme
  - [ ] 5.2: Add `.initiative-order` class -- container styling for the initiative list in the sidebar
  - [ ] 5.3: Add `.initiative-entry` class -- individual combatant row styling with padding, border-bottom divider
  - [ ] 5.4: Add `.initiative-entry.initiative-active` class -- highlighted background (amber tint), left border accent to indicate current turn
  - [ ] 5.5: Add `.initiative-entry.initiative-pc` class -- default PC styling
  - [ ] 5.6: Add `.initiative-entry.initiative-npc` class -- DM gold color for NPC names
  - [ ] 5.7: Add `.initiative-roll` class -- monospace font for initiative roll numbers
  - [ ] 5.8: Add character-class-specific initiative entry colors (`.initiative-entry.fighter`, `.initiative-entry.rogue`, etc.)

- [ ] Task 6: Integrate combat banner into `render_main_content()` (AC: #1, #2, #12)
  - [ ] 6.1: Call `render_combat_banner()` after the session header and before the narrative container in `render_main_content()`
  - [ ] 6.2: Position after the error panel and secret reveal notification, before the comparison view / narrative container block

- [ ] Task 7: Integrate initiative order into `render_sidebar()` (AC: #3, #8, #12)
  - [ ] 7.1: Call `render_initiative_order()` after the party panel section and before the keyboard shortcuts help
  - [ ] 7.2: Add a "---" divider and "### Initiative" heading before the initiative panel (only when combat is active)

- [ ] Task 8: Write tests in `tests/test_story_15_5_combat_ui_indicators.py` (AC: #1-#12)
  - [ ] 8.1: `class TestRenderCombatBannerHtml` -- banner HTML generation
  - [ ] 8.2: `class TestRenderInitiativeOrderHtml` -- initiative order HTML generation
  - [ ] 8.3: `class TestRenderCombatBanner` -- Streamlit integration (mock st.markdown)
  - [ ] 8.4: `class TestRenderInitiativeOrder` -- Streamlit integration (mock st.markdown)
  - [ ] 8.5: `class TestCombatBannerIntegration` -- render_main_content calls banner
  - [ ] 8.6: `class TestInitiativeOrderIntegration` -- render_sidebar calls initiative panel
  - [ ] 8.7: `class TestEdgeCases` -- missing combat_state, inactive combat, missing NPC profiles

## Dev Notes

### Combat Banner Design

The combat banner sits between the session header and the narrative container. It should be visually prominent but not overwhelming -- a compact bar with the campfire theme's amber accent:

```python
def render_combat_banner_html(round_number: int) -> str:
    """Generate HTML for the combat status banner.

    Displays "COMBAT - Round N" at the top of the narrative area
    when tactical combat is active.

    Args:
        round_number: Current combat round number (1+).

    Returns:
        HTML string for combat banner, or empty string if round_number <= 0.
    """
    if round_number <= 0:
        return ""
    return (
        '<div class="combat-banner">'
        f'<span class="combat-banner-label">COMBAT</span>'
        f' <span class="combat-banner-round">Round {round_number}</span>'
        '</div>'
    )
```

### Initiative Order Panel Design

The initiative order panel lives in the sidebar, below the party panel. It lists all combatants in initiative order with their roll, highlighting the active combatant:

```python
def render_initiative_order_html(
    combat_state: CombatState,
    current_turn: str,
    characters: dict[str, CharacterConfig],
) -> str:
    """Generate HTML for the initiative order display.

    Shows all combatants in initiative order with roll numbers.
    The current combatant is highlighted. PCs use their character
    class color; NPCs use DM gold.

    Args:
        combat_state: Active combat state with initiative data.
        current_turn: Current turn identifier (e.g., "dm", "shadowmere", "dm:goblin_1").
        characters: Character config dict for PC name/class lookup.

    Returns:
        HTML string for initiative order panel.
    """
    entries: list[str] = []

    for entry in combat_state.initiative_order:
        if entry == "dm":
            # Skip bookend entry from initiative display
            continue

        roll = combat_state.initiative_rolls.get(entry, 0)
        is_active = entry == current_turn
        active_class = " initiative-active" if is_active else ""

        if entry.startswith("dm:"):
            # NPC entry
            npc_key = entry.split(":", 1)[1]
            npc_profile = combat_state.npc_profiles.get(npc_key)
            display_name = escape_html(npc_profile.name if npc_profile else npc_key)
            entries.append(
                f'<div class="initiative-entry initiative-npc{active_class}">'
                f'<span class="initiative-name">{display_name}</span>'
                f'<span class="initiative-roll">{roll}</span>'
                f'</div>'
            )
        else:
            # PC entry
            char_config = characters.get(entry)
            if char_config:
                display_name = escape_html(char_config.name)
                class_slug = "".join(
                    c for c in char_config.character_class.lower()
                    if c.isalnum() or c == "-"
                )
            else:
                display_name = escape_html(entry)
                class_slug = ""

            class_attr = f" {class_slug}" if class_slug else ""
            entries.append(
                f'<div class="initiative-entry initiative-pc{class_attr}{active_class}">'
                f'<span class="initiative-name">{display_name}</span>'
                f'<span class="initiative-roll">{roll}</span>'
                f'</div>'
            )

    entries_html = "\n".join(entries)
    return (
        f'<div class="initiative-order">'
        f'{entries_html}'
        f'</div>'
    )
```

### CSS Design for Combat Banner

Add to `styles/theme.css` in a new section after the Session Header section (~line 362):

```css
/* ==========================================================================
   Combat UI Indicators (Story 15.5)
   ========================================================================== */

/* Combat banner - shown at top of narrative area during tactical combat */
.combat-banner {
  background: rgba(232, 168, 73, 0.12);
  border: 1px solid var(--accent-warm);
  border-radius: 6px;
  padding: var(--space-sm) var(--space-md);
  margin-bottom: var(--space-sm);
  text-align: center;
}

.combat-banner-label {
  font-family: var(--font-ui);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--accent-warm);
}

.combat-banner-round {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin-left: var(--space-xs);
}

/* Initiative order panel in sidebar */
.initiative-order {
  background: var(--bg-primary);
  border-radius: 6px;
  padding: var(--space-xs);
  margin-top: var(--space-xs);
}

/* Individual combatant entry in initiative order */
.initiative-entry {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-xs) var(--space-sm);
  border-radius: 4px;
  margin-bottom: 2px;
  font-family: var(--font-ui);
  font-size: var(--text-system);
  color: var(--text-secondary);
}

/* Active combatant highlighting */
.initiative-entry.initiative-active {
  background: rgba(232, 168, 73, 0.15);
  border-left: 3px solid var(--accent-warm);
  color: var(--text-primary);
  font-weight: 600;
}

/* PC entries - inherit character class colors */
.initiative-entry.initiative-pc { color: var(--text-primary); }
.initiative-entry.fighter .initiative-name { color: var(--color-fighter); }
.initiative-entry.rogue .initiative-name { color: var(--color-rogue); }
.initiative-entry.wizard .initiative-name { color: var(--color-wizard); }
.initiative-entry.cleric .initiative-name { color: var(--color-cleric); }

/* NPC entries - DM gold */
.initiative-entry.initiative-npc .initiative-name {
  color: var(--color-dm);
  font-style: italic;
}

/* Combatant name */
.initiative-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Initiative roll number */
.initiative-roll {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
  min-width: 24px;
  text-align: right;
}
```

### Integration Point: render_main_content()

Insert the combat banner call in `render_main_content()` (app.py ~line 7793) after the secret reveal notification and before the comparison view check:

```python
# Secret reveal notification (existing code)
...
st.session_state["pending_secret_reveal"] = None

# Story 15.5: Combat banner (above narrative area)
render_combat_banner()

# Story 12.3: Fork Comparison View (existing code)
if st.session_state.get("comparison_mode"):
    render_comparison_view()
else:
    ...
```

### Integration Point: render_sidebar()

Insert the initiative order display in `render_sidebar()` (app.py ~line 7096) after the party panel and before keyboard shortcuts:

```python
# Party panel loop (existing code)
...

# Story 15.5: Initiative order (combat only)
render_initiative_order()

# Keyboard shortcuts help (Story 3.6) -- existing code
render_keyboard_shortcuts_help()
```

The `render_initiative_order()` function internally checks `combat_state.active` and renders nothing when combat is not active, so no conditional wrapper is needed at the call site. However, the "### Initiative" heading should only appear during combat:

```python
def render_initiative_order() -> None:
    """Render initiative order panel in sidebar during active combat."""
    game: GameState | None = st.session_state.get("game")
    if not game:
        return

    combat_state = game.get("combat_state")
    if not combat_state or not isinstance(combat_state, CombatState) or not combat_state.active:
        return

    current_turn = game.get("current_turn", "")
    characters = game.get("characters", {})

    st.markdown("---")
    st.markdown("### Initiative")
    st.markdown(
        render_initiative_order_html(combat_state, current_turn, characters),
        unsafe_allow_html=True,
    )
```

### Imports Needed in app.py

Add `CombatState` to the imports from `models` in app.py. Check the existing import block (app.py top of file) -- `CombatState` may already be imported. If not, add it to the existing `from models import ...` block.

### HTML Escaping

All user-provided content (character names, NPC names) MUST be passed through `escape_html()` before insertion into HTML strings. The `escape_html()` function is already defined in app.py (used throughout the codebase for safe HTML rendering).

### CombatState Access Pattern

Follow the defensive access pattern used elsewhere in the codebase:

```python
combat_state = game.get("combat_state")
if not combat_state or not isinstance(combat_state, CombatState) or not combat_state.active:
    return  # No combat indicators
```

The `isinstance` check guards against old GameState dicts that might have `combat_state` as a plain dict instead of a `CombatState` model instance.

### Character Class Slug Pattern

Follow the same `class_slug` pattern used in `render_character_card_html()` (app.py line 1527):

```python
class_slug = "".join(c for c in char_class.lower() if c.isalnum() or c == "-")
```

This strips non-alphanumeric characters from the class name for safe CSS class usage.

### NPC Name Display

NPC entries in `initiative_order` use the format `"dm:npc_key"` (e.g., `"dm:goblin_1"`). The display name comes from `combat_state.npc_profiles[npc_key].name` (e.g., "Goblin 1"). If the NPC key is not found in `npc_profiles`, fall back to displaying the raw key with underscores replaced by spaces for readability.

### Files to Modify

1. **`app.py`** -- Add `render_combat_banner_html()`, `render_combat_banner()`, `render_initiative_order_html()`, `render_initiative_order()` functions; integrate `render_combat_banner()` into `render_main_content()`; integrate `render_initiative_order()` into `render_sidebar()`; add `CombatState` import if not already present
2. **`styles/theme.css`** -- Add combat banner and initiative order CSS classes (`.combat-banner`, `.combat-banner-label`, `.combat-banner-round`, `.initiative-order`, `.initiative-entry`, `.initiative-active`, `.initiative-pc`, `.initiative-npc`, `.initiative-name`, `.initiative-roll`)
3. **`tests/test_story_15_5_combat_ui_indicators.py`** -- **NEW** test file

### Files NOT to Modify

- **`models.py`** -- No changes. `CombatState` and `NpcProfile` already defined (Story 15-1).
- **`tools.py`** -- No changes. Combat tools are Story 15-1/15-2.
- **`agents.py`** -- No changes. DM prompting is Story 15-4.
- **`graph.py`** -- No changes. Combat routing is Story 15-3.
- **`persistence.py`** -- No changes. `CombatState` serialization already handled (Story 15-1).
- **`config.py`** -- No changes.
- **`memory.py`** -- No changes.

### Test Approach

Create `tests/test_story_15_5_combat_ui_indicators.py`. Use class-based test organization matching project convention.

**`class TestRenderCombatBannerHtml`:**
- Test returns HTML with round number for valid round (1, 5, 10)
- Test HTML contains `combat-banner` CSS class
- Test HTML contains `combat-banner-label` with "COMBAT" text
- Test HTML contains `combat-banner-round` with "Round N" text
- Test returns empty string for round_number 0
- Test returns empty string for negative round_number

**`class TestRenderInitiativeOrderHtml`:**
- Test renders PC entries with character names and class slugs
- Test renders NPC entries with NPC profile names in DM gold styling
- Test skips "dm" bookend entry from display
- Test highlights current turn entry with `initiative-active` class
- Test displays initiative rolls for each combatant
- Test falls back to raw NPC key when profile not found
- Test falls back to raw PC key when character not in characters dict
- Test escapes HTML in character names (XSS prevention)
- Test escapes HTML in NPC names (XSS prevention)
- Test empty initiative_order returns empty container
- Test initiative order with only PCs (no NPCs)
- Test initiative order with only NPCs (no PCs)
- Test initiative order with mixed PCs and NPCs

**`class TestRenderCombatBanner`:**
- Test calls st.markdown with banner HTML when combat active
- Test renders nothing when combat inactive
- Test renders nothing when game state missing
- Test renders nothing when combat_state missing from game

**`class TestRenderInitiativeOrder`:**
- Test calls st.markdown with initiative HTML when combat active
- Test renders nothing when combat inactive
- Test renders nothing when game state missing
- Test renders heading "### Initiative" when combat active

**`class TestCombatBannerIntegration`:**
- Test render_main_content calls render_combat_banner
- Test banner appears after session header

**`class TestInitiativeOrderIntegration`:**
- Test render_sidebar displays initiative panel during combat
- Test initiative panel not displayed during non-combat

**`class TestEdgeCases`:**
- Test combat_state as plain dict (not CombatState instance) -- defensive handling
- Test combat_state.active False produces no output
- Test NPC key with underscores displays correctly
- Test very long initiative order (10+ combatants) renders all
- Test current_turn matches NPC entry (dm:npc_name) for highlighting
- Test current_turn is "dm" (bookend) -- no entry highlighted in initiative panel (bookend is hidden)

Use `unittest.mock.patch` for `st.markdown` and `st.session_state`. Build minimal `GameState` dicts with `CombatState` instances for testing. Import `CombatState`, `NpcProfile` from `models` and `CharacterConfig` for test fixtures.

### References

- [Source: app.py#render_main_content ~line 7755] - Main content render function (banner insertion point)
- [Source: app.py#render_sidebar ~line 7058] - Sidebar render function (initiative panel insertion point)
- [Source: app.py#render_session_header_html ~line 374] - Session header HTML pattern to follow
- [Source: app.py#render_character_card_html ~line 1511] - Character card HTML pattern (class slug generation)
- [Source: app.py#render_module_banner ~line 7723] - Module banner pattern (conditional display in main content)
- [Source: app.py#escape_html] - HTML escaping function used throughout
- [Source: app.py#render_dm_message_html ~line 1253] - DM message HTML pattern
- [Source: styles/theme.css#:root ~line 11] - CSS variables (colors, fonts, spacing)
- [Source: styles/theme.css#.session-header ~line 335] - Session header CSS (adjacent styling pattern)
- [Source: styles/theme.css#.character-card ~line 376] - Character card CSS (class-specific color pattern)
- [Source: styles/theme.css#.narrative-container ~line 1043] - Narrative container CSS
- [Source: models.py#CombatState ~line 853] - CombatState model definition
- [Source: models.py#NpcProfile ~line 822] - NpcProfile model with name field
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-10.md#Story 15-5] - Design specification
- [Source: _bmad-output/implementation-artifacts/stories/15-1-combat-state-model.md] - Story 15-1 context (CombatState fields)
- [Source: _bmad-output/implementation-artifacts/stories/15-4-dm-bookend-npc-turns.md] - Story 15-4 context (combat turn types)

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
