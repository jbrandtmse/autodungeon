# Story 11-5: Callback UI & History

## Story

As a **user**,
I want **to view tracked narrative elements and callback history**,
So that **I can appreciate the story's interconnections**.

## Status

**Status:** review
**Epic:** 11 - Callback Tracker (Chekhov's Gun)
**Created:** 2026-02-07
**FRs Covered:** FR80 (user can view callback history and track unresolved narrative threads)
**Predecessors:** Story 11-1 (Narrative Element Extraction) - DONE, Story 11-2 (Callback Database) - DONE, Story 11-3 (DM Callback Suggestions) - DONE, Story 11-4 (Callback Detection) - DONE

## Acceptance Criteria

**Given** the sidebar or a dedicated panel
**When** I access "Story Threads"
**Then** I see a list of tracked narrative elements

**Given** the element list
**When** displayed
**Then** each shows: name, type, turn introduced, times referenced

**Given** I click on an element
**When** expanding details
**Then** I see: full description, callback history, original context

**Given** elements with callbacks
**When** displayed
**Then** they show a "referenced X times" badge

**Given** the callback history
**When** viewed
**Then** it shows a timeline of when elements were introduced and referenced

**Given** dormant elements
**When** displayed
**Then** they're visually distinct (grayed out) but still accessible

## Context: What Stories 11-1 Through 11-4 Built

### models.py (existing)
- `NarrativeElement` model with fields: `id`, `element_type`, `name`, `description`, `turn_introduced`, `session_introduced`, `turns_referenced` (list[int]), `characters_involved`, `resolved`, `times_referenced`, `last_referenced_turn`, `potential_callbacks` (list[str]), `dormant`
- `NarrativeElementStore` with methods: `get_active()`, `get_by_type()`, `find_by_name()`, `add_element()`, `record_reference()`, `update_dormancy()`, `get_dormant()`, `get_active_non_dormant()`, `get_by_relevance(limit)`, `get_all()`
- `CallbackEntry` model with fields: `id`, `element_id`, `element_name`, `element_type`, `turn_detected`, `turn_gap`, `match_type`, `match_context`, `is_story_moment`, `session_detected`
- `CallbackLog` with methods: `add_entry()`, `get_by_element()`, `get_story_moments()`, `get_by_turn()`, `get_recent()`
- `GameState` has `callback_database: NarrativeElementStore` (campaign-level)
- `GameState` has `callback_log: CallbackLog` (all detected callbacks)

### app.py (existing UI patterns)
- `render_sidebar(config)` at line 6426: orchestrates all sidebar sections in order (mode indicator, game controls, party, session controls, checkpoint browser, transcript export, nudge, whisper, LLM status, configure button, back to sessions)
- `render_nudge_input()` at line 760: sidebar section with HTML label, text area, submit button
- `render_human_whisper_input()` at line 809: sidebar section with HTML label, text area, submit button
- `render_character_sheet_modal()` at line 4394: `@st.dialog` modal with columns, expanders, HTML content
- `render_checkpoint_browser()` at line 4617: sidebar section with expanders for session history
- `render_character_card()` at line 3526: HTML card rendering with character-specific CSS classes
- Pattern: HTML generation functions (`render_*_html()`) separate from Streamlit render functions (`render_*()`)
- Pattern: `unsafe_allow_html=True` for all `st.markdown(html)` calls

### styles/theme.css (existing CSS patterns)
- CSS variables for colors: `--bg-primary`, `--bg-secondary`, `--bg-message`, `--text-primary`, `--text-secondary`, `--accent-warm`
- Character cards: `.character-card` with left border, `.character-card.controlled` with glow
- Badge pattern: `.api-key-source-badge`, `.proficiency-badge`, `.agent-status-badge`
- Expander: `.streamlit-expanderHeader` with bg-secondary
- Font variables: `--font-narrative`, `--font-ui`, `--font-mono`
- Size variables: `--text-dm`, `--text-pc`, `--text-name`, `--text-ui`, `--text-system`
- Spacing variables: `--space-xs`, `--space-sm`, `--space-md`, `--space-lg`

### persistence.py (existing)
- `serialize_game_state()` / `deserialize_game_state()` handle `callback_database` and `callback_log`
- All data already persists in checkpoints

## What Story 11.5 Changes

This story adds a **user-facing "Story Threads" panel** to the Streamlit sidebar. It is the only story in Epic 11 with UI changes. Specifically:

1. **New sidebar section "Story Threads"** in app.py: An `st.expander` in the sidebar that lists all tracked narrative elements from the campaign-level `callback_database`.
2. **Element list display**: Each element shows name, type icon, turn introduced, and a "referenced X times" badge.
3. **Expandable element details**: Clicking/expanding an element shows full description, characters involved, potential callbacks, and callback history timeline.
4. **Callback timeline**: For each element with callbacks, shows a chronological list of when it was referenced (from `callback_log`).
5. **Dormant element styling**: Dormant elements rendered with reduced opacity and a "dormant" label, but remain accessible.
6. **Story moment highlights**: Callbacks flagged as "story moments" (20+ turn gap) are visually highlighted with amber accent.
7. **CSS classes** in styles/theme.css: New classes for story thread cards, badges, dormant styling, and timeline.
8. **Summary statistics**: Top-level count of active threads, dormant threads, and story moments.

No new models, no persistence changes, no LLM calls. This is purely Streamlit UI + CSS.

## Tasks

### 1. Add CSS Classes for Story Threads (styles/theme.css)

1. [x]Add `/* Story Threads Panel (Story 11.5) */` section to theme.css
   - After the existing "Human Whisper to DM" CSS section
2. [x]Add `.story-threads-summary` class
   - `font-size: var(--text-system)`, `color: var(--text-secondary)`, `margin-bottom: var(--space-sm)`
   - For the summary line "X active, Y dormant, Z story moments"
3. [x]Add `.story-element-card` class
   - `background: var(--bg-secondary)`, `border-radius: 6px`, `padding: var(--space-sm)`
   - `margin-bottom: var(--space-xs)`, `border-left: 3px solid var(--text-secondary)`
   - Follows `.character-card` pattern
4. [x]Add `.story-element-card.dormant` class
   - `opacity: 0.55`, `border-left-color: var(--bg-message)`
   - Visually distinct per AC
5. [x]Add `.story-element-card.resolved` class
   - `opacity: 0.4`, `text-decoration: line-through` on the name
6. [x]Add element type color classes for left border
   - `.story-element-card.type-character { border-left-color: var(--color-fighter); }`
   - `.story-element-card.type-item { border-left-color: var(--accent-warm); }`
   - `.story-element-card.type-location { border-left-color: var(--color-rogue); }`
   - `.story-element-card.type-event { border-left-color: var(--color-wizard); }`
   - `.story-element-card.type-promise { border-left-color: var(--color-cleric); }`
   - `.story-element-card.type-threat { border-left-color: var(--color-fighter); }`
7. [x]Add `.story-element-name` class
   - `font-family: var(--font-ui)`, `font-size: var(--text-name)`, `font-weight: 600`
   - `color: var(--text-primary)`
8. [x]Add `.story-element-meta` class
   - `font-size: var(--text-system)`, `color: var(--text-secondary)`, `margin-top: 2px`
9. [x]Add `.story-element-badge` class
   - `display: inline-block`, `font-size: 11px`, `padding: 1px 6px`
   - `border-radius: 8px`, `background: var(--bg-message)`, `color: var(--text-secondary)`
   - `margin-left: var(--space-xs)`
10. [x]Add `.story-element-badge.story-moment` class
    - `background: rgba(232, 168, 73, 0.2)`, `color: var(--accent-warm)`
    - Amber highlight for story moments
11. [x]Add `.story-element-badge.dormant-badge` class
    - `background: rgba(61, 53, 48, 0.5)`, `color: var(--text-secondary)`
12. [x]Add `.story-element-description` class
    - `font-family: var(--font-narrative)`, `font-size: var(--text-system)`, `font-style: italic`
    - `color: var(--text-secondary)`, `margin: var(--space-xs) 0`
13. [x]Add `.callback-timeline` class
    - `margin-top: var(--space-xs)`, `padding-left: var(--space-sm)`
    - `border-left: 2px solid var(--bg-message)`
14. [x]Add `.callback-timeline-entry` class
    - `font-size: var(--text-system)`, `color: var(--text-secondary)`
    - `padding: 2px 0 2px var(--space-sm)`, `position: relative`
15. [x]Add `.callback-timeline-entry::before` pseudo-element
    - Small circle marker: `content: ""`, `width: 6px`, `height: 6px`
    - `border-radius: 50%`, `background: var(--text-secondary)`
    - `position: absolute`, `left: -4px`, `top: 8px` (centered on left border)
16. [x]Add `.callback-timeline-entry.story-moment::before` class
    - `background: var(--accent-warm)` (amber dot for story moments)
17. [x]Add `.callback-timeline-entry.introduced` class
    - `color: var(--text-primary)`, `font-weight: 500` (introduction entry is brighter)
18. [x]Add `.story-element-detail` class
    - `font-size: var(--text-system)`, `color: var(--text-secondary)`, `margin-top: var(--space-xs)`
19. [x]Add `.story-element-detail strong` class
    - `color: var(--text-primary)` (labels within details)

### 2. Add Story Threads HTML Rendering Functions (app.py)

20. [x]Add `render_story_threads_summary_html()` function to app.py
    - Signature: `render_story_threads_summary_html(active_count: int, dormant_count: int, story_moment_count: int) -> str`
    - Returns HTML: `<div class="story-threads-summary">X active threads, Y dormant, Z story moments</div>`
    - If all counts are 0, returns `<div class="story-threads-summary">No narrative elements tracked yet</div>`
21. [x]Add `render_story_element_card_html()` function to app.py
    - Signature: `render_story_element_card_html(element: NarrativeElement, callback_entries: list[CallbackEntry], is_expanded: bool = False) -> str`
    - Builds an HTML card with:
      - Element name with type-specific CSS class
      - Type icon text (Character, Item, Location, Event, Promise, Threat)
      - "Turn X, Session Y" metadata line
      - "referenced Z times" badge (if times_referenced > 1)
      - "story moment" badge (if any callback_entries have is_story_moment=True)
      - "dormant" badge (if element.dormant is True)
    - CSS classes applied: `story-element-card`, `type-{element_type}`, optionally `dormant` or `resolved`
22. [x]Add `render_story_element_detail_html()` function to app.py
    - Signature: `render_story_element_detail_html(element: NarrativeElement, callback_entries: list[CallbackEntry]) -> str`
    - Builds HTML for expanded detail view:
      - Description in italic narrative font
      - "Characters involved:" list
      - "Potential callbacks:" list (if any)
      - Callback timeline (if any callback entries)
    - Returns empty string if no meaningful detail to show
23. [x]Add `render_callback_timeline_html()` function to app.py
    - Signature: `render_callback_timeline_html(element: NarrativeElement, callback_entries: list[CallbackEntry]) -> str`
    - Builds the timeline HTML:
      - First entry: "Introduced in Turn {turn_introduced}, Session {session_introduced}" with class `introduced`
      - For each callback entry (sorted by turn_detected): "Referenced in Turn {turn_detected}" with match type and context excerpt
      - Story moment entries get class `story-moment`
    - Returns empty string if no callback entries (only the introduction line is shown in that case)
24. [x]Add `NarrativeElement`, `NarrativeElementStore`, `CallbackEntry`, `CallbackLog` to imports from models in app.py
    - Add to the existing `from models import (...)` block

### 3. Add Story Threads Sidebar Render Function (app.py)

25. [x]Add `render_story_threads()` function to app.py
    - Signature: `render_story_threads() -> None`
    - Gets `callback_database` from `st.session_state.get("game", {}).get("callback_database")`
    - Gets `callback_log` from `st.session_state.get("game", {}).get("callback_log")`
    - If no callback_database or no elements, shows "No narrative elements tracked yet" caption
    - Shows summary statistics line (active, dormant, story moments)
    - Gets all elements from callback_database sorted by relevance via `get_by_relevance()`
    - For each element, renders inside a `st.expander` with the element name as header
    - The expander header shows: element name + type label + badge count
    - Inside the expander: full detail HTML (description, characters, callbacks, timeline)
    - Dormant elements are listed after active elements (separated by a visual divider)
    - Wraps the whole section in an `st.expander("Story Threads", expanded=False)` for sidebar compactness
26. [x]Add `_get_element_type_label()` helper function
    - Maps element_type to display labels: character -> "Character", item -> "Item", location -> "Location", event -> "Event", promise -> "Promise", threat -> "Threat"
    - Returns the label string
27. [x]Add `_get_element_type_icon()` helper function
    - Maps element_type to text-based icons for sidebar compactness (no emoji per code style):
      - character -> "NPC", item -> "ITEM", location -> "LOC", event -> "EVT", promise -> "VOW", threat -> "RISK"
    - Returns short label string for compact display

### 4. Integrate Story Threads into Sidebar (app.py)

28. [x]Add `render_story_threads()` call to `render_sidebar()` function
    - Insert after the "Human Whisper to DM" section and its divider
    - Before the "LLM Status" expander
    - Pattern:
      ```python
      st.markdown("---")

      # Story Threads (Story 11.5 - FR80)
      render_story_threads()
      ```
29. [x]Verify render_story_threads() only renders when game state exists
    - Guard: if no game or no callback_database, return early with no output
    - Do NOT show empty "Story Threads" section before game starts

### 5. Tests

30. [x]Test `render_story_threads_summary_html()` function
    - All zeros returns "No narrative elements tracked yet"
    - Active/dormant/story_moment counts render correctly
    - CSS class `story-threads-summary` present in output
31. [x]Test `render_story_element_card_html()` function
    - Active element: name, type class, turn/session metadata, referenced badge
    - Dormant element: has `dormant` CSS class
    - Resolved element: has `resolved` CSS class
    - Element with 1 reference: no "referenced X times" badge (only show for > 1)
    - Element with 5 references: shows "referenced 5 times" badge
    - Element with story moment callbacks: shows story-moment badge
    - Type-specific CSS class present (e.g., `type-character`, `type-item`)
    - HTML is properly escaped for XSS prevention (element names/descriptions)
32. [x]Test `render_story_element_detail_html()` function
    - Element with description: description rendered in italic
    - Element with characters_involved: characters listed
    - Element with potential_callbacks: callbacks listed
    - Element with no description/characters/callbacks: returns empty or minimal HTML
    - Element with callback entries: timeline section included
    - All text content is HTML-escaped
33. [x]Test `render_callback_timeline_html()` function
    - Element with no callbacks: returns minimal timeline (just introduction)
    - Element with callbacks: chronological entries with turn numbers
    - Story moment entry has `story-moment` CSS class
    - Introduction entry has `introduced` CSS class
    - Multiple callbacks sorted by turn_detected
    - Match context excerpt included in each entry
34. [x]Test `render_story_threads()` function (integration)
    - No game state: renders nothing (no error)
    - Game with empty callback_database: shows "No narrative elements tracked yet"
    - Game with active elements: renders element list with expanders
    - Game with dormant elements: dormant elements listed separately with distinct styling
    - Game with story moments: story moment count in summary
    - Callback log entries associated with correct elements
35. [x]Test `_get_element_type_label()` and `_get_element_type_icon()` helpers
    - All 6 element types return correct labels/icons
    - Unknown type returns fallback (the type string itself)
36. [x]Test sidebar integration
    - `render_sidebar()` calls `render_story_threads()` (verify function is called)
    - Story Threads section appears in correct position (after whisper, before LLM status)

## Dependencies

- **Story 11-1** (done): Provides `NarrativeElement`, `NarrativeElementStore` models
- **Story 11-2** (done): Provides `callback_database` on `GameState`, `get_by_relevance()`, `get_dormant()`, `get_active_non_dormant()`, dormancy tracking
- **Story 11-3** (done): Provides callback suggestion formatting patterns (read-only context building)
- **Story 11-4** (done): Provides `CallbackEntry`, `CallbackLog` models with `get_by_element()`, `get_story_moments()`
- **Story 2.1** (done): Provides Streamlit application shell and sidebar structure
- **Story 2.2** (done): Provides campfire CSS theme foundation, CSS variable system
- **Story 2.4** (done): Provides party panel/character card patterns in sidebar

## Dev Notes

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `app.py` | Modify | Add `render_story_threads()`, `render_story_threads_summary_html()`, `render_story_element_card_html()`, `render_story_element_detail_html()`, `render_callback_timeline_html()`, `_get_element_type_label()`, `_get_element_type_icon()`, add imports, integrate into `render_sidebar()` |
| `styles/theme.css` | Modify | Add Story Threads CSS section with card, badge, timeline, dormant styling |
| `tests/test_story_11_5_callback_ui_and_history.py` | Create | Unit tests for HTML rendering functions and integration test for sidebar |

### Code Patterns to Follow

#### 1. Story Threads CSS (styles/theme.css)

Add after the "Human Whisper to DM" CSS section (around line 1170). Follow the character card pattern:

```css
/* ==========================================================================
   Story Threads Panel (Story 11.5 - FR80)
   ========================================================================== */

/* Summary statistics line */
.story-threads-summary {
  font-family: var(--font-ui);
  font-size: var(--text-system);
  color: var(--text-secondary);
  margin-bottom: var(--space-sm);
}

/* Narrative element card (follows character-card pattern) */
.story-element-card {
  background: var(--bg-secondary);
  border-radius: 6px;
  padding: var(--space-sm);
  margin-bottom: var(--space-xs);
  border-left: 3px solid var(--text-secondary);
}

/* Element type color classes */
.story-element-card.type-character { border-left-color: var(--color-fighter); }
.story-element-card.type-item { border-left-color: var(--accent-warm); }
.story-element-card.type-location { border-left-color: var(--color-rogue); }
.story-element-card.type-event { border-left-color: var(--color-wizard); }
.story-element-card.type-promise { border-left-color: var(--color-cleric); }
.story-element-card.type-threat { border-left-color: var(--color-fighter); }

/* Dormant elements - grayed out per AC */
.story-element-card.dormant {
  opacity: 0.55;
  border-left-color: var(--bg-message);
}

/* Resolved elements */
.story-element-card.resolved {
  opacity: 0.4;
}

.story-element-card.resolved .story-element-name {
  text-decoration: line-through;
}

/* Element name */
.story-element-name {
  font-family: var(--font-ui);
  font-size: var(--text-name);
  font-weight: 600;
  color: var(--text-primary);
  display: inline;
}

/* Element metadata line (type, turn, session) */
.story-element-meta {
  font-size: var(--text-system);
  color: var(--text-secondary);
  margin-top: 2px;
}

/* Reference count and status badges */
.story-element-badge {
  display: inline-block;
  font-family: var(--font-ui);
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
  background: var(--bg-message);
  color: var(--text-secondary);
  margin-left: var(--space-xs);
  vertical-align: middle;
}

/* Story moment badge - amber accent */
.story-element-badge.story-moment {
  background: rgba(232, 168, 73, 0.2);
  color: var(--accent-warm);
}

/* Dormant badge */
.story-element-badge.dormant-badge {
  background: rgba(61, 53, 48, 0.5);
  color: var(--text-secondary);
}

/* Element description (italic narrative font) */
.story-element-description {
  font-family: var(--font-narrative);
  font-size: var(--text-system);
  font-style: italic;
  color: var(--text-secondary);
  margin: var(--space-xs) 0;
}

/* Detail section within expanded element */
.story-element-detail {
  font-size: var(--text-system);
  color: var(--text-secondary);
  margin-top: var(--space-xs);
}

.story-element-detail strong {
  color: var(--text-primary);
}

/* Callback timeline (vertical line with dots) */
.callback-timeline {
  margin-top: var(--space-xs);
  padding-left: var(--space-sm);
  border-left: 2px solid var(--bg-message);
}

/* Individual timeline entry */
.callback-timeline-entry {
  font-size: var(--text-system);
  color: var(--text-secondary);
  padding: 2px 0 2px var(--space-sm);
  position: relative;
}

/* Timeline dot marker */
.callback-timeline-entry::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-secondary);
  position: absolute;
  left: calc(var(--space-sm) * -1 - 4px);
  top: 8px;
}

/* Story moment timeline entry - amber dot */
.callback-timeline-entry.story-moment::before {
  background: var(--accent-warm);
}

/* Introduction entry (brighter than regular callbacks) */
.callback-timeline-entry.introduced {
  color: var(--text-primary);
  font-weight: 500;
}
```

#### 2. HTML Rendering Functions (app.py)

Follow the `render_nudge_input_html()` / `render_character_card_html()` pattern of generating HTML strings with CSS classes:

```python
from html import escape as escape_html

# Type labels for display
_ELEMENT_TYPE_LABELS: dict[str, str] = {
    "character": "Character",
    "item": "Item",
    "location": "Location",
    "event": "Event",
    "promise": "Promise",
    "threat": "Threat",
}

# Short type icons for compact sidebar display
_ELEMENT_TYPE_ICONS: dict[str, str] = {
    "character": "NPC",
    "item": "ITEM",
    "location": "LOC",
    "event": "EVT",
    "promise": "VOW",
    "threat": "RISK",
}


def _get_element_type_label(element_type: str) -> str:
    """Get display label for a narrative element type.

    Args:
        element_type: Element type string (character, item, etc.).

    Returns:
        Human-readable label.
    """
    return _ELEMENT_TYPE_LABELS.get(element_type, element_type.title())


def _get_element_type_icon(element_type: str) -> str:
    """Get short icon/label for a narrative element type.

    Args:
        element_type: Element type string (character, item, etc.).

    Returns:
        Short label for compact display.
    """
    return _ELEMENT_TYPE_ICONS.get(element_type, element_type.upper()[:4])


def render_story_threads_summary_html(
    active_count: int, dormant_count: int, story_moment_count: int
) -> str:
    """Generate HTML for story threads summary statistics.

    Story 11.5: Callback UI & History.
    FR80: User can view callback history.

    Args:
        active_count: Number of active (non-dormant, non-resolved) elements.
        dormant_count: Number of dormant elements.
        story_moment_count: Number of story moments detected.

    Returns:
        HTML string for summary line.
    """
    if active_count == 0 and dormant_count == 0:
        return '<div class="story-threads-summary">No narrative elements tracked yet</div>'

    parts: list[str] = []
    if active_count > 0:
        parts.append(f"{active_count} active")
    if dormant_count > 0:
        parts.append(f"{dormant_count} dormant")
    if story_moment_count > 0:
        parts.append(f"{story_moment_count} story moment{'s' if story_moment_count != 1 else ''}")

    return f'<div class="story-threads-summary">{", ".join(parts)}</div>'


def render_story_element_card_html(
    element: NarrativeElement,
    callback_entries: list[CallbackEntry],
) -> str:
    """Generate HTML for a narrative element card.

    Renders a compact card with element name, type, metadata,
    and reference badges.

    Story 11.5: Callback UI & History.

    Args:
        element: The NarrativeElement to render.
        callback_entries: CallbackEntry list for this element (for story moment badge).

    Returns:
        HTML string for the element card.
    """
    # Build CSS classes
    css_classes = ["story-element-card", f"type-{element.element_type}"]
    if element.dormant:
        css_classes.append("dormant")
    if element.resolved:
        css_classes.append("resolved")

    # Type label
    type_icon = _get_element_type_icon(element.element_type)

    # Badges
    badges_html = ""
    if element.times_referenced > 1:
        badges_html += (
            f'<span class="story-element-badge">'
            f"referenced {element.times_referenced} times</span>"
        )
    has_story_moment = any(e.is_story_moment for e in callback_entries)
    if has_story_moment:
        badges_html += '<span class="story-element-badge story-moment">story moment</span>'
    if element.dormant:
        badges_html += '<span class="story-element-badge dormant-badge">dormant</span>'

    return (
        f'<div class="{" ".join(css_classes)}">'
        f'  <span class="story-element-name">{escape_html(element.name)}</span>'
        f"  {badges_html}"
        f'  <div class="story-element-meta">'
        f"    {type_icon} &middot; Turn {element.turn_introduced}, Session {element.session_introduced}"
        f"  </div>"
        f"</div>"
    )


def render_story_element_detail_html(
    element: NarrativeElement,
    callback_entries: list[CallbackEntry],
) -> str:
    """Generate HTML for expanded element detail view.

    Shows full description, characters involved, potential callbacks,
    and callback timeline.

    Story 11.5: Callback UI & History.

    Args:
        element: The NarrativeElement to show detail for.
        callback_entries: CallbackEntry list for this element.

    Returns:
        HTML string for the detail view.
    """
    parts: list[str] = []

    # Description
    if element.description:
        parts.append(
            f'<div class="story-element-description">'
            f'"{escape_html(element.description)}"</div>'
        )

    # Characters involved
    if element.characters_involved:
        chars = ", ".join(escape_html(c) for c in element.characters_involved)
        parts.append(
            f'<div class="story-element-detail">'
            f"<strong>Characters:</strong> {chars}</div>"
        )

    # Potential callbacks
    if element.potential_callbacks:
        cb_items = "".join(
            f"<li>{escape_html(cb)}</li>" for cb in element.potential_callbacks
        )
        parts.append(
            f'<div class="story-element-detail">'
            f"<strong>Potential callbacks:</strong><ul>{cb_items}</ul></div>"
        )

    # Callback timeline
    timeline_html = render_callback_timeline_html(element, callback_entries)
    if timeline_html:
        parts.append(timeline_html)

    return "\n".join(parts)


def render_callback_timeline_html(
    element: NarrativeElement,
    callback_entries: list[CallbackEntry],
) -> str:
    """Generate HTML for callback timeline.

    Shows a chronological timeline of when the element was introduced
    and subsequently referenced.

    Story 11.5: Callback UI & History.

    Args:
        element: The NarrativeElement for the timeline.
        callback_entries: CallbackEntry list for this element, sorted by turn_detected.

    Returns:
        HTML string for the timeline, or empty string if no entries.
    """
    entries_html: list[str] = []

    # Introduction entry (always shown)
    entries_html.append(
        f'<div class="callback-timeline-entry introduced">'
        f"Introduced in Turn {element.turn_introduced}, Session {element.session_introduced}"
        f"</div>"
    )

    # Callback entries sorted by turn
    sorted_entries = sorted(callback_entries, key=lambda e: e.turn_detected)
    for entry in sorted_entries:
        css_class = "callback-timeline-entry"
        if entry.is_story_moment:
            css_class += " story-moment"

        # Match type label
        match_label = {
            "name_exact": "exact name match",
            "name_fuzzy": "fuzzy name match",
            "description_keyword": "keyword match",
        }.get(entry.match_type, entry.match_type)

        context_snippet = ""
        if entry.match_context:
            truncated = entry.match_context[:80]
            if len(entry.match_context) > 80:
                truncated += "..."
            context_snippet = (
                f' <span style="opacity: 0.7;">- {escape_html(truncated)}</span>'
            )

        moment_label = ""
        if entry.is_story_moment:
            moment_label = f" ({entry.turn_gap} turn gap!)"

        entries_html.append(
            f'<div class="{css_class}">'
            f"Turn {entry.turn_detected} ({match_label}){moment_label}"
            f"{context_snippet}"
            f"</div>"
        )

    if not callback_entries:
        # Only introduction, still wrap in timeline
        return (
            '<div class="story-element-detail"><strong>Timeline:</strong></div>'
            f'<div class="callback-timeline">{"".join(entries_html)}</div>'
        )

    return (
        '<div class="story-element-detail"><strong>Callback Timeline:</strong></div>'
        f'<div class="callback-timeline">{"".join(entries_html)}</div>'
    )
```

#### 3. Story Threads Render Function (app.py)

Follow the pattern of `render_checkpoint_browser()` and `render_nudge_input()`:

```python
def render_story_threads() -> None:
    """Render Story Threads panel in the sidebar.

    Shows tracked narrative elements from the campaign-level callback
    database with expandable details and callback timeline.

    Story 11.5: Callback UI & History.
    FR80: User can view callback history and track unresolved narrative threads.
    """
    game: GameState = st.session_state.get("game", {})
    callback_database = game.get("callback_database")
    callback_log = game.get("callback_log")

    if callback_database is None or not callback_database.elements:
        return  # No elements tracked yet, don't show section

    if callback_log is None:
        callback_log = CallbackLog()

    # Compute summary statistics
    active_elements = callback_database.get_active_non_dormant()
    dormant_elements = callback_database.get_dormant()
    story_moments = callback_log.get_story_moments()

    with st.expander(
        f"Story Threads ({len(active_elements) + len(dormant_elements)})",
        expanded=False,
    ):
        # Summary statistics
        st.markdown(
            render_story_threads_summary_html(
                len(active_elements),
                len(dormant_elements),
                len(story_moments),
            ),
            unsafe_allow_html=True,
        )

        # Active elements (sorted by relevance)
        all_by_relevance = callback_database.get_by_relevance()
        active_sorted = [e for e in all_by_relevance if not e.dormant]
        dormant_sorted = [e for e in all_by_relevance if e.dormant]

        for element in active_sorted:
            # Get callback entries for this element
            element_callbacks = callback_log.get_by_element(element.id)

            # Card HTML
            st.markdown(
                render_story_element_card_html(element, element_callbacks),
                unsafe_allow_html=True,
            )

            # Expandable detail
            with st.expander(
                f"Details: {element.name}",
                expanded=False,
            ):
                st.markdown(
                    render_story_element_detail_html(element, element_callbacks),
                    unsafe_allow_html=True,
                )

        # Dormant elements (after divider)
        if dormant_sorted:
            st.markdown("---")
            st.caption("Dormant Threads")
            for element in dormant_sorted:
                element_callbacks = callback_log.get_by_element(element.id)

                st.markdown(
                    render_story_element_card_html(element, element_callbacks),
                    unsafe_allow_html=True,
                )

                with st.expander(
                    f"Details: {element.name}",
                    expanded=False,
                ):
                    st.markdown(
                        render_story_element_detail_html(element, element_callbacks),
                        unsafe_allow_html=True,
                    )
```

#### 4. Sidebar Integration (app.py)

Insert into `render_sidebar()` after the Human Whisper section and before LLM Status:

```python
def render_sidebar(config: AppConfig) -> None:
    with st.sidebar:
        # ... existing sections (mode indicator through human whisper) ...

        st.markdown("---")

        # Human Whisper to DM (Story 10.4)
        render_human_whisper_input()

        st.markdown("---")

        # Story Threads (Story 11.5 - FR80)
        render_story_threads()

        st.markdown("---")

        # Configuration status (condensed, moved from main area) (2.5)
        with st.expander("LLM Status", expanded=False):
            # ... existing code ...
```

The divider before Story Threads is already present (from the whisper section). The function renders nothing if no elements are tracked, so the divider after it may show a blank gap -- this is acceptable and consistent with how other sidebar sections handle empty states.

#### 5. Import Additions (app.py)

Add to the existing `from models import (...)` block at the top of app.py:

```python
from models import (
    # ... existing imports ...
    CallbackEntry,
    CallbackLog,
    NarrativeElement,
    NarrativeElementStore,
)
```

### Key Design Decisions

1. **Sidebar placement (expander, not dedicated panel):** The Story Threads panel lives in the sidebar as a collapsible `st.expander` rather than a separate page or main panel. This is consistent with how checkpoint browser, nudge, and whisper features work -- they are auxiliary tools that don't interrupt the main narrative flow.

2. **Nested expanders for element details:** Each element is shown as a compact card, with a separate `st.expander("Details: ...")` for the full view. This keeps the sidebar compact while still providing deep detail. Streamlit supports nested expanders within a parent expander.

3. **Active elements before dormant:** Active (non-dormant) elements are shown first, sorted by relevance score. Dormant elements are shown after a divider with a "Dormant Threads" caption. This matches the AC requirement that dormant elements are "visually distinct but still accessible."

4. **CSS follows existing patterns exactly:** Card styling follows `.character-card`, badge styling follows `.api-key-source-badge` and `.proficiency-badge`, font and spacing use existing CSS variables. No new CSS variables are introduced.

5. **No emoji in code output:** Per CLAUDE.md instructions, all type indicators use text labels (NPC, ITEM, LOC, etc.) rather than emoji. The CSS handles all visual distinction via colors and styling.

6. **HTML escaping everywhere:** All user-visible text (element names, descriptions, match context) is passed through `escape_html()` to prevent XSS. This matches the existing pattern in `render_character_card_html()` and `render_module_banner()`.

7. **No new models or persistence changes:** This is purely a UI story. All data comes from existing `callback_database` and `callback_log` fields on `GameState` which are already serialized/deserialized.

8. **Callback timeline is read-only:** The timeline displays historical data from `CallbackLog.get_by_element()`. No state mutations occur during rendering.

9. **Graceful degradation:** If `callback_database` is None (old checkpoints), the section is not rendered at all. If `callback_log` is None, it defaults to an empty `CallbackLog()`. This ensures backward compatibility.

10. **Summary count in expander header:** The expander header shows `"Story Threads (N)"` where N is the total element count (active + dormant). This gives users a quick glance at whether there are elements to explore without opening the expander.

### Test Strategy

**Test file:** `tests/test_story_11_5_callback_ui_and_history.py`

**Unit Tests (HTML rendering):**

- `render_story_threads_summary_html()`: empty state, active only, dormant only, mixed, story moments
- `render_story_element_card_html()`: active element, dormant element, resolved element, badges (referenced, story moment, dormant), type-specific CSS classes, HTML escaping
- `render_story_element_detail_html()`: description, characters, potential callbacks, empty element, with/without callback entries
- `render_callback_timeline_html()`: introduction only, with callbacks, with story moments, sorted order, match context truncation
- `_get_element_type_label()`: all 6 types, unknown fallback
- `_get_element_type_icon()`: all 6 types, unknown fallback

**Integration Tests (Streamlit rendering):**

- `render_story_threads()` with no game state
- `render_story_threads()` with empty callback_database
- `render_story_threads()` with populated data
- `render_sidebar()` includes story threads call

**Mock Pattern:**

```python
from models import (
    CallbackEntry,
    CallbackLog,
    NarrativeElement,
    NarrativeElementStore,
    create_callback_entry,
    create_narrative_element,
)

# Create test elements
element = create_narrative_element(
    element_type="character",
    name="Skrix the Goblin",
    description="Befriended by party, promised cave information",
    turn_introduced=5,
    session_introduced=1,
    characters_involved=["Shadowmere"],
    potential_callbacks=["Could return as ally"],
)

# Build test store
store = NarrativeElementStore(elements=[element])

# Test HTML rendering directly (no Streamlit mocking needed)
html = render_story_element_card_html(element, [])
assert "Skrix the Goblin" in html
assert "type-character" in html
assert "story-element-card" in html

# For Streamlit integration tests, use unittest.mock to patch st.session_state
```

HTML rendering functions can be tested without mocking Streamlit since they return plain strings. Only `render_story_threads()` requires mocking `st.session_state` and Streamlit calls.

### Important Constraints

- **No new dependencies:** Uses only existing Streamlit, Pydantic models, and Python standard library
- **No state mutations:** Rendering is strictly read-only. No changes to `callback_database` or `callback_log` during display
- **No LLM calls:** This is purely a UI rendering story
- **HTML escaping required:** All dynamic text must use `escape_html()` to prevent XSS
- **Sidebar width constraint:** The sidebar is fixed at 240px. All cards and text must fit within this width. Use compact type icons (NPC, ITEM, etc.) rather than full labels in card view
- **Performance:** `get_by_relevance()` is O(n log n) for sorting. For typical games with < 100 elements, this is instant. No caching needed for MVP
- **Backward compatibility:** Old checkpoints without `callback_database` or `callback_log` must not cause errors. Guard with None checks and defaults
- **No emoji:** Per CLAUDE.md code style, avoid emoji in generated output
