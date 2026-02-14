# Story 17-1: Turn Number Display

**Epic:** 17 — AI Scene Image Generation
**Status:** done

---

## Story

As a **user watching the narrative**,
I want **to see turn numbers in the narrative message headers**,
So that **I can identify specific turns when requesting image generation at a particular moment**.

---

## Acceptance Criteria

### AC1: PC Message Turn Number in Attribution

**Given** the narrative panel displaying PC messages
**When** rendered
**Then** the attribution format is "Turn N --- Name, the Class:" where N is the 1-based index in ground_truth_log

### AC2: DM Message Turn Number Label

**Given** the narrative panel displaying DM messages
**When** rendered
**Then** a subtle "Turn N" label appears above the DM narration block

### AC3: Turn Number Computation (Frontend-Only)

**Given** the turn number
**When** computed
**Then** it is derived from the message's index in the ground_truth_log array (1-based), requiring NO backend changes

### AC4: Camera Icon Hover Hint

**Given** a turn number in the narrative
**When** hovered
**Then** a subtle camera icon hint appears, indicating the turn can be illustrated (click-to-illustrate interaction deferred to Story 17-5; this story adds the visual hover hint only)

### AC5: Turn Number Typography

**Given** the turn number styling
**When** rendered
**Then** it uses JetBrains Mono font (`--font-mono`), 11px, secondary text color at 60% opacity (per UX spec)

---

## Tasks / Subtasks

- [x] **Task 1: Add turn number to PC message attribution** (AC: 1, 3, 5)
  - [x] 1.1: In `NarrativeMessage.svelte`, compute `turnNumber` as `message.index + 1` (the `index` field from `ParsedMessage` is the 0-based position in `ground_truth_log`)
  - [x] 1.2: Update the PC attribution line from:
    ```svelte
    {characterInfo?.name ?? message.agent}, the {characterInfo?.characterClass ?? 'Adventurer'}:
    ```
    to:
    ```svelte
    <span class="turn-number">Turn {turnNumber}</span> --- {characterInfo?.name ?? message.agent}, the {characterInfo?.characterClass ?? 'Adventurer'}:
    ```
  - [x] 1.3: Use an em dash (`---` in the epic, rendered as `\u2014` or literal `---`) as the separator between turn number and character attribution. The epic specifies triple-dash; use a visual em-dash character `\u2014` for typographic correctness.

- [x] **Task 2: Add turn number label above DM messages** (AC: 2, 3, 5)
  - [x] 2.1: In `NarrativeMessage.svelte`, add a `<span class="turn-number">Turn {turnNumber}</span>` element above the DM message `<p>` tag, inside the `.dm-message` div
  - [x] 2.2: The turn number label should be a block-level element above the DM narration content (not inline with it), separated by `margin-bottom: var(--space-xs)` (4px)

- [x] **Task 3: Add turn number to sheet update messages** (AC: 3, 5)
  - [x] 3.1: Add a turn number label above sheet update content, similar to DM messages but using the same `.turn-number` class
  - [x] 3.2: Determine if sheet updates should show turn numbers (they are part of ground_truth_log and have indices). Include them for consistency so users can reference any turn.

- [x] **Task 4: Add turn number CSS styles** (AC: 5)
  - [x] 4.1: Add `.turn-number` CSS class in `NarrativeMessage.svelte` scoped styles:
    ```css
    .turn-number {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--text-secondary);
        opacity: 0.6;
        letter-spacing: 0.05em;
    }
    ```
  - [x] 4.2: Add context-specific positioning rules:
    ```css
    /* Inside PC attribution: inline, with spacing before the dash */
    .pc-attribution .turn-number {
        margin-right: var(--space-xs);
    }

    /* Above DM messages: block display */
    .dm-message .turn-number {
        display: block;
        margin-bottom: var(--space-xs);
    }
    ```

- [x] **Task 5: Add camera icon hover hint** (AC: 4)
  - [x] 5.1: Add CSS hover state for `.turn-number`:
    ```css
    .turn-number:hover {
        cursor: pointer;
        color: var(--accent-warm);
        opacity: 1;
    }

    .turn-number:hover::after {
        content: ' \01F4F7';  /* camera emoji */
        font-size: 10px;
    }
    ```
  - [x] 5.2: The hover is visual-only in this story. The actual click-to-illustrate handler will be wired in Story 17-5. For now, no `onclick` handler is needed, but the `cursor: pointer` signals interactivity.
  - [x] 5.3: Add `role="button"` and `aria-label="Illustrate Turn {N}"` to the turn number span for accessibility (per UX spec)

- [x] **Task 6: Verify no backend changes** (AC: 3)
  - [x] 6.1: Confirm zero changes to any Python files (`models.py`, `agents.py`, `graph.py`, `api/`, etc.)
  - [x] 6.2: Run `python -m ruff check .` -- no new violations
  - [x] 6.3: Run `python -m pytest` -- no regressions

- [x] **Task 7: Frontend verification** (AC: all)
  - [x] 7.1: Run `cd frontend && npm run check` -- TypeScript passes (0 errors, 14 pre-existing warnings)
  - [x] 7.2: Run `cd frontend && npm run build` -- build succeeds
  - [x] 7.3: Run `cd frontend && npm run test` -- all 141 tests pass (13 NarrativeMessage tests: 5 original + 8 new)
  - [x] 7.4: Start the dev stack (`bash dev.sh` or equivalent) and navigate to a game session
  - [x] 7.5: Use chrome-devtools MCP to take screenshots:
    - Verify PC messages show "Turn N --- Name, the Class:" attribution
    - Verify DM messages show "Turn N" label above the narration block
    - Verify turn number uses JetBrains Mono, 11px, muted opacity
    - Verify hovering a turn number shows camera icon and amber highlight
  - [x] 7.6: Verify responsive behavior at mobile breakpoint (< 768px)

---

## Dev Notes

### Architecture Context

This is a **frontend-only** story. The turn number is already available as the array index in `ground_truth_log` -- no new data from the backend is needed. The `ParsedMessage` interface (defined in `frontend/src/lib/narrative.ts`) already carries an `index` field that is the 0-based position in the log array. The turn number is simply `index + 1`.

This story is a prerequisite for Story 17-5 (Image Generation UI), which will add click-to-illustrate behavior on the turn numbers. This story only adds the **visual display** and **hover hint**.

### Files to Modify

| File | Change |
|------|--------|
| `frontend/src/lib/components/NarrativeMessage.svelte` | Add turn number to PC attribution and DM/sheet labels; add `.turn-number` CSS; add hover styles |

**No new files are created.** This is a single-component enhancement.

### Current Component Structure (NarrativeMessage.svelte)

The component receives three props via `$props()`:

```typescript
let {
    message,        // ParsedMessage (has .index, .agent, .content, .messageType)
    characterInfo,  // CharacterInfo | undefined (has .name, .characterClass, .classSlug)
    isCurrent,      // boolean (last message highlight)
}: { ... } = $props();
```

The `message.index` field is the 0-based position in `ground_truth_log`. The turn number to display is `message.index + 1`.

### Implementation: Turn Number Derivation

Add a derived value at the top of the component script:

```typescript
const turnNumber = $derived(message.index + 1);
```

This is reactive and will update if the message prop changes (e.g., during pagination reflows).

### Implementation: PC Attribution Change

**Current template (line 25-27):**
```svelte
<span class="pc-attribution {classSlug}">
    {characterInfo?.name ?? message.agent}, the {characterInfo?.characterClass ?? 'Adventurer'}:
</span>
```

**New template:**
```svelte
<span class="pc-attribution {classSlug}">
    <span class="turn-number" role="button" aria-label="Illustrate Turn {turnNumber}">Turn {turnNumber}</span>
    {' \u2014 '}
    {characterInfo?.name ?? message.agent}, the {characterInfo?.characterClass ?? 'Adventurer'}:
</span>
```

The em dash (`\u2014`) matches the UX spec's "Turn 42 --- Thorgrim, the Fighter:" format. Using the Unicode em dash character rather than three hyphens produces cleaner typography.

### Implementation: DM Narration Change

**Current template (line 20-22):**
```svelte
<div class="dm-message" class:current-turn={isCurrent}>
    <p>{@html formattedContent}</p>
</div>
```

**New template:**
```svelte
<div class="dm-message" class:current-turn={isCurrent}>
    <span class="turn-number" role="button" aria-label="Illustrate Turn {turnNumber}">Turn {turnNumber}</span>
    <p>{@html formattedContent}</p>
</div>
```

The `.dm-message .turn-number` CSS rule sets `display: block` and `margin-bottom: var(--space-xs)` so the turn label sits above the narration paragraph.

### Implementation: Sheet Update Change

Sheet updates (lines 30-32) should also get turn numbers for consistency:

```svelte
<div class="sheet-notification" class:current-turn={isCurrent}>
    <span class="turn-number" role="button" aria-label="Illustrate Turn {turnNumber}">Turn {turnNumber}</span>
    <p>{@html formattedContent}</p>
</div>
```

### CSS Specification (from UX Design Spec)

The UX design specification at `_bmad-output/planning-artifacts/ux-design-specification.md` (lines 3284-3358) provides the exact CSS:

```css
/* Base turn number styling */
.turn-number {
    font-family: var(--font-mono);   /* JetBrains Mono */
    font-size: 11px;
    color: var(--text-secondary);     /* #B8A896 */
    opacity: 0.6;
    letter-spacing: 0.05em;
}

/* Inline within PC attribution */
.pc-attribution .turn-number {
    margin-right: var(--space-xs);    /* 4px gap before em dash */
}

/* Block label above DM/sheet messages */
.dm-message .turn-number,
.sheet-notification .turn-number {
    display: block;
    margin-bottom: var(--space-xs);   /* 4px below label */
}

/* Hover hint: camera icon appears */
.turn-number:hover {
    cursor: pointer;
    color: var(--accent-warm);        /* #E8A849 amber */
    opacity: 1;
}

.turn-number:hover::after {
    content: ' \01F4F7';              /* camera emoji */
    font-size: 10px;
}
```

**Notes on CSS custom properties used:**
- `--font-mono`: `'JetBrains Mono', monospace` (defined in `frontend/src/app.css` line 36)
- `--text-secondary`: `#B8A896` (defined in `frontend/src/app.css` line 14)
- `--accent-warm`: `#E8A849` (defined in `frontend/src/app.css` line 19)
- `--space-xs`: `4px` (defined in `frontend/src/app.css` line 46)

### System Messages

System messages (the `else` branch at line 34-37 of the current component) do NOT get turn numbers. System messages are UI-generated (connection status, errors) and are not part of the game log, so they have no meaningful turn index.

### Existing Patterns to Follow

- **Scoped CSS in components:** All message styling is scoped within `NarrativeMessage.svelte` using Svelte's `<style>` block. The new `.turn-number` class should be added here, not in `app.css`.
- **No hardcoded colors:** Use CSS custom properties (`var(--font-mono)`, `var(--text-secondary)`, etc.).
- **Svelte 5 runes:** Use `$derived()` for computed values like `turnNumber`.
- **Accessibility:** Add `role="button"` and `aria-label` to turn number spans (per UX spec line 3621).
- **No `{@html}` for turn numbers:** Turn numbers are static text, not LLM content. Use normal Svelte text interpolation `{turnNumber}`, not `{@html}`.

### Emoji Rendering Consideration

The camera emoji (`\01F4F7`) in the `::after` pseudo-element relies on system emoji fonts. This should render consistently across modern browsers. If emoji rendering is problematic, an alternative is to use a Unicode camera symbol like `\u{1F4F7}` (same codepoint, different escape syntax in CSS: `\1F4F7`). The CSS `content` property should use: `content: ' \1F4F7';`.

### What This Story Does NOT Do

- **No click handler on turn numbers.** The click-to-illustrate interaction is wired in Story 17-5.
- **No backend changes.** No Python files are modified.
- **No new components.** This modifies only `NarrativeMessage.svelte`.
- **No new stores or types.** The existing `ParsedMessage.index` field is sufficient.
- **No new tests.** The existing narrative tests cover parsing; visual changes are verified via chrome-devtools MCP screenshots. If component tests exist for `NarrativeMessage`, they may need minor updates to account for the new turn number spans in the rendered output.

### Common Pitfalls to Avoid

1. **Do NOT use `message.index` directly as the displayed number.** It is 0-based. Always add 1.
2. **Do NOT add turn numbers to system messages.** They are not part of `ground_truth_log`.
3. **Do NOT add an `onclick` handler.** That belongs in Story 17-5. Only the visual hover hint (`cursor: pointer`, camera icon `::after`) is implemented here.
4. **Do NOT modify `narrative.ts` or any other files.** This is a single-file change to `NarrativeMessage.svelte`.
5. **Do NOT use inline styles.** All styling via the scoped `<style>` block and CSS custom properties.

### References

- [Source: frontend/src/lib/components/NarrativeMessage.svelte — Component to modify]
- [Source: frontend/src/lib/narrative.ts — ParsedMessage type with `index` field]
- [Source: frontend/src/lib/components/NarrativePanel.svelte — Parent component, renders NarrativeMessage in keyed loop]
- [Source: frontend/src/app.css — CSS custom properties (design tokens)]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md:3262-3358 — Turn number display CSS spec and hover behavior]
- [Source: _bmad-output/planning-artifacts/epics-v2.1.md — Epic 17 story definitions]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A

### Completion Notes List

- Added `turnNumber` derived value (`message.index + 1`) to NarrativeMessage.svelte
- PC attribution format: `Turn N -- Name, the Class:` with em dash (U+2014) separator
- DM messages: block-level `Turn N` label above narration paragraph
- Sheet updates: block-level `Turn N` label above content (consistent with DM)
- System messages: no turn number (not part of ground_truth_log)
- All turn number spans include `role="button"` and `aria-label="Illustrate Turn {N}"` for accessibility
- CSS uses existing custom properties: `--font-mono`, `--text-secondary`, `--accent-warm`, `--space-xs`
- Hover effect: cursor pointer, amber highlight, camera emoji (U+1F4F7) via `::after` pseudo-element
- No onclick handler (deferred to Story 17-5)
- Zero backend changes -- frontend-only modification
- 8 new tests added (13 total for NarrativeMessage component), all 141 frontend tests pass
- TypeScript check: 0 errors; build: successful

### File List

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/lib/components/NarrativeMessage.svelte` | Modified | Added turn number display to DM, PC, and sheet update messages; added `.turn-number` CSS with hover effects |
| `frontend/src/lib/components/NarrativeMessage.test.ts` | Modified | Added 8 new tests for turn number display, 1-based computation, accessibility attributes, em dash separator, and system message exclusion |

---

## Code Review

**Reviewer:** Claude Opus 4.6 (Adversarial Review)
**Date:** 2026-02-14
**Verdict:** PASS (after fixes)

### Issues Found: 8 (3 HIGH/MEDIUM auto-fixed, 3 LOW documented)

#### Issue 1 (HIGH) -- FIXED: Missing `tabindex="0"` on `role="button"` elements

All three turn-number `<span>` elements had `role="button"` without `tabindex="0"`, making them unreachable via keyboard Tab navigation. Every other `role="button"` element in the codebase (SessionCard, CharacterLibrary) pairs it with `tabindex="0"`. Without tabindex, screen reader and keyboard-only users cannot reach or activate the turn number elements. Violates WCAG 2.1 SC 2.1.1 (Keyboard).

**Resolution:** Added `tabindex="0"` to all three turn-number spans (DM, PC, sheet update). Updated accessibility test to verify `tabindex="0"` is present.

#### Issue 2 (MEDIUM) -- FIXED: No CSS `transition` on hover state

The `.turn-number:hover` state changed `color` and `opacity` instantly with no transition, causing an abrupt visual snap. All other interactive elements in the codebase (`.load-earlier-btn`, `.resume-scroll-btn`, `.session-card`) use `var(--transition-fast)` for hover transitions.

**Resolution:** Added `transition: color var(--transition-fast), opacity var(--transition-fast)` to the base `.turn-number` rule.

#### Issue 3 (MEDIUM) -- FIXED: `cursor: pointer` inside `:hover` rule instead of base rule

The `cursor: pointer` was declared inside `.turn-number:hover`, which causes a brief cursor flicker from default to pointer on first hover. Since the element has `role="button"` and is always interactive, `cursor: pointer` should be on the base `.turn-number` selector. This matches the pattern used by all other interactive elements in the codebase.

**Resolution:** Moved `cursor: pointer` from `.turn-number:hover` to the base `.turn-number` rule.

#### Issue 4 (MEDIUM) -- FIXED: Test gap for `tabindex` accessibility attribute

The existing accessibility test verified `role="button"` but did not verify `tabindex="0"`. This gap would have allowed Issue 1 to recur undetected.

**Resolution:** Updated the "turn number span has role='button' for accessibility" test to also assert `tabindex="0"`.

#### Issue 5 (LOW): Camera emoji rendering via CSS `content` may not work on all systems

The CSS `content: ' \1F4F7'` relies on system emoji fonts. Some older Windows builds may render this as a box character. A safer approach would be an SVG icon, but the spec explicitly calls for the camera emoji. No action required.

#### Issue 6 (LOW): Story document internal contradiction about tests

The Dev Notes section under "What This Story Does NOT Do" says "No new tests" but 8 new tests were added (correctly documented in Completion Notes). Minor documentation inconsistency. No code action required.

#### Issue 7 (LOW): `$derived` wrapper on `turnNumber` is semantically a constant

`const turnNumber = $derived(message.index + 1)` -- since message props don't change for a given component instance (keyed by `msg.index` in the parent loop), `$derived` is unnecessary overhead. A simple `const turnNumber = message.index + 1` would suffice. However, this follows the existing pattern used by `classSlug` on the same line, so it is consistent. No action required.

### Acceptance Criteria Verification

| AC | Status | Notes |
|----|--------|-------|
| AC1: PC attribution format | PASS | "Turn N --- Name, the Class:" with em dash separator |
| AC2: DM turn label | PASS | Block-level "Turn N" above narration |
| AC3: Frontend-only computation | PASS | `message.index + 1`, zero backend changes |
| AC4: Camera icon hover hint | PASS | Hover shows amber highlight + camera emoji via `::after` |
| AC5: Typography | PASS | JetBrains Mono (`--font-mono`), 11px, secondary color at 60% opacity |

### Post-Fix Test Results

- **NarrativeMessage tests:** 13/13 pass
- **Full frontend suite:** 141/141 pass
- **Zero regressions**

