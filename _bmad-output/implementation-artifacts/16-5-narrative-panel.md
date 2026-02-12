# Story 16.5: Narrative Panel

Status: ready-for-dev

## Story

As a **user watching or playing an autodungeon session**,
I want **a beautifully styled narrative panel that displays the D&D story in real-time with character-attributed messages, auto-scrolling, and thoughtful typography**,
so that **I can follow the adventure as it unfolds, instantly recognize who is speaking, and feel the warmth and immersion of a campfire gathering**.

## Acceptance Criteria (Given/When/Then)

### AC1: NarrativePanel Component Renders in Game Page

**Given** the game page at `/game/{sessionId}` is loaded
**When** the page renders
**Then** the placeholder text ("Narrative panel coming in Story 16-5") is replaced by the `NarrativePanel` component
**And** the panel fills the main content area (max-width: 800px, centered horizontally)
**And** the panel has `--bg-primary` background with comfortable reading margins
**And** a session header is displayed at the top in chronicle style ("Session VII" format, Lora 24px, `--color-dm` gold, centered)

### AC2: WebSocket Connection Established on Game Page Mount

**Given** the game page loads with a valid `sessionId`
**When** the component mounts
**Then** a WebSocket connection is created via `createGameConnection(sessionId)` from `$lib/ws`
**And** on successful connection, `connectionStatus` store is set to `'connected'`
**And** on receiving a `session_state` event, the full `GameState` is written to the `gameState` store
**And** on receiving a `turn_update` event, the new message is appended to the narrative log
**And** on disconnect, `connectionStatus` store is set to `'disconnected'` or `'reconnecting'`
**And** on component unmount (navigation away), the WebSocket connection is cleanly disconnected

### AC3: DM Narration Messages Display with Gold Accent Styling

**Given** the game state contains `ground_truth_log` entries with agent `"dm"` or `"DM"`
**When** the narrative panel renders those entries
**Then** each DM message displays with:
  - `--bg-message` (#3D3530) background
  - 4px left border in `--color-dm` (#D4A574 warm gold)
  - Lora font at `--text-dm` (18px), line-height 1.6
  - Italic text style
  - Justified text alignment for manuscript feel
  - `0 8px 8px 0` border-radius (rounded on the right side)
  - 16px horizontal padding, 12px vertical padding
  - No explicit speaker attribution (DM is implicit from the gold border)

### AC4: PC Dialogue Messages Display with Character-Colored Styling

**Given** the game state contains `ground_truth_log` entries with a PC agent (e.g., "Thorin", "Shadowmere")
**When** the narrative panel renders those entries
**Then** each PC message displays with:
  - `--bg-message` (#3D3530) background
  - 3px left border in the character's class color:
    - Fighter: `--color-fighter` (#C45C4A red)
    - Rogue: `--color-rogue` (#6B8E6B green)
    - Wizard: `--color-wizard` (#7B68B8 purple)
    - Cleric: `--color-cleric` (#4A90A4 blue)
    - Fallback: `--text-secondary` for unknown classes
  - Literary attribution header: "Name, the Class:" (e.g., "Thorin, the Fighter:")
    - Attribution in character class color
    - Font: Inter at `--text-name` (14px), font-weight 600
    - Margin-bottom: 4px below attribution
  - Message body in Lora font at `--text-pc` (17px), line-height 1.6
  - Justified text alignment
  - 8px border-radius
  - Action text (`*asterisk wrapped*`) rendered in italic with `--text-secondary` color
  - Quoted dialogue (regular text) rendered in `--text-primary` color

### AC5: Sheet Update Messages Display with Amber Accent Styling

**Given** the game state contains `ground_truth_log` entries with agent `"SHEET"`
**When** the narrative panel renders those entries
**Then** each sheet update message displays with:
  - Subtle amber background: `rgba(232, 168, 73, 0.08)`
  - 3px left border in `--accent-warm` (#E8A849)
  - Inter font (not Lora) at 14px, line-height 1.4
  - Text color: `--accent-warm`
  - Smaller vertical spacing (8px padding, 8px margin-bottom)
  - `0 6px 6px 0` border-radius

### AC6: System Messages Display with Muted Styling

**Given** a system-generated message (e.g., connection status, error recovery notice)
**When** the narrative panel renders it
**Then** the message displays with:
  - No background (transparent) or very subtle `--bg-secondary` background
  - Inter font at `--text-system` (13px)
  - `--text-secondary` color
  - Centered text alignment
  - No left border
  - Reduced spacing (8px margin)

### AC7: Current Turn Highlight Animation

**Given** the most recent message in the narrative log
**When** it is rendered
**Then** it receives a `current-turn` CSS class
**And** a subtle amber glow animation plays (box-shadow fades from `rgba(232, 168, 73, 0.4)` to none over 3 seconds)
**And** the animation uses `ease-out` timing
**And** previous messages do not have the highlight

### AC8: Auto-Scroll to Newest Message

**Given** the narrative panel has rendered messages and the `autoScroll` state in `uiStore` is `true`
**When** a new message is appended to the log (via WebSocket `turn_update`)
**Then** the panel smoothly scrolls to the bottom to reveal the new message
**And** the scroll animation uses `smooth` behavior (not instant jump)

**Given** the user manually scrolls upward in the narrative panel
**When** they scroll more than 100px above the bottom
**Then** auto-scroll is paused (set `autoScroll` to `false` in `uiStore`)
**And** a floating "Resume auto-scroll" button appears at the bottom-right of the narrative panel
**And** the button uses `--accent-warm` styling with a down-arrow indicator

**Given** the "Resume auto-scroll" button is visible
**When** the user clicks it
**Then** auto-scroll resumes (set `autoScroll` to `true`)
**And** the panel scrolls to the bottom
**And** the button disappears

**Given** the user is scrolled to the bottom of the panel (within 100px threshold)
**When** a new message arrives
**Then** auto-scroll remains active without user action

### AC9: Message Pagination with "Load Earlier Messages"

**Given** the game has more messages in `ground_truth_log` than the display limit (default 50, configurable via `game_config.narrative_display_limit`)
**When** the narrative panel renders
**Then** only the most recent N messages are displayed (where N = `narrative_display_limit`)
**And** a "Load earlier messages (X hidden)" button appears at the top of the message list
**And** X shows the count of hidden messages
**And** the button uses `--text-secondary` color with `--bg-secondary` background

**Given** the "Load earlier messages" button is visible
**When** the user clicks it
**Then** an additional batch of messages (equal to `narrative_display_limit`) is prepended to the visible messages
**And** the scroll position is preserved (the user does not jump to the top)
**And** if all messages are now visible, the button disappears

### AC10: Thinking Indicator During Agent Processing

**Given** the game is running (autopilot active or awaiting next turn)
**When** the backend is processing an agent's turn (between `turn_update` events)
**Then** a thinking indicator appears below the last message
**And** the indicator shows: "The tale continues..." with an animated three-dot pulse
**And** the indicator uses `--text-secondary` color, Lora italic font
**And** the indicator appears after a 500ms delay (to avoid flicker on fast responses)
**And** the indicator disappears when the next `turn_update` arrives

**Given** the current turn agent is known (from `gameState.current_turn`)
**When** the thinking indicator is shown
**Then** it includes the agent's name: "Thorin contemplates..." or "The Dungeon Master weaves the tale..."
**And** the indicator text uses the character's class color

### AC11: Dice Roll Formatting

**Given** a message contains dice notation (e.g., "1d20+5", "3d6", "2d8+3")
**When** the message is rendered
**Then** dice notation is visually distinguished using:
  - JetBrains Mono font (`--font-mono`)
  - Slightly different color or background to stand out from narrative text
  - The dice expression is wrapped in a styled `<span>` with `--font-mono`, `--accent-warm` color
**And** natural language around the dice notation renders normally in Lora

### AC12: HTML/XSS Sanitization

**Given** message content arrives from the backend (LLM-generated text)
**When** the narrative panel renders it
**Then** all content is sanitized to prevent XSS attacks
**And** HTML tags in message content are escaped (displayed as text, not rendered as HTML)
**And** only styled elements created by the component itself (action text spans, dice spans) render as HTML
**And** no `{@html}` directive is used on raw LLM content without sanitization

### AC13: Empty State Display

**Given** the game state has an empty `ground_truth_log` (no messages yet)
**When** the narrative panel renders
**Then** a centered placeholder message displays: "The adventure awaits... Start a new game to begin."
**And** the placeholder uses Lora italic font, `--text-secondary` color
**And** the placeholder is vertically centered in the panel

### AC14: Responsive Layout

**Given** the browser window is resized
**When** the viewport width changes
**Then** the narrative panel adjusts:
  - Above 1024px: max-width 800px, centered with comfortable side margins
  - Between 768px and 1024px: full width with 16px horizontal padding
  - Below 768px: full width with 8px horizontal padding, font sizes reduce by 1px
**And** message bubbles maintain readable line length (~70 characters optimal)
**And** the session header remains readable at all sizes

### AC15: Log Entry Parsing (Frontend Port)

**Given** the `ground_truth_log` contains entries in the format `"[agent_name]: message content"`
**When** the narrative panel processes entries for rendering
**Then** each entry is parsed to extract:
  - `agent`: the agent key from within brackets (e.g., "dm", "Thorin", "SHEET")
  - `content`: everything after `]: ` (stripped of leading colon/space)
  - `messageType`: determined from agent — "dm_narration" if agent is "dm"/"DM", "sheet_update" if agent is "SHEET", otherwise "pc_dialogue"
**And** entries without brackets are treated as DM narration (fallback)
**And** duplicate prefix stripping is applied (if LLM echoed `[agent]:` in content)

### AC16: Character Info Resolution

**Given** a PC message is being rendered and the `gameState` includes a `characters` dict (from `game_config` or state)
**When** the component looks up character info for an agent name
**Then** it resolves the character's display name and class:
  - First: direct key lookup in characters dict (lowercase agent key)
  - Second: search by character name (log entries may use display names)
  - Fallback: use agent name as-is with class "Adventurer"
**And** the resolved class determines the character color for border and attribution
**And** the class-to-color mapping uses CSS custom properties (not hardcoded hex values)

## Tasks / Subtasks

- [ ] **Task 1: Create log entry parser utility** (AC: 15, 16, 12)
  - [ ] 1.1: Create `frontend/src/lib/narrative.ts` with types and parsing functions:
    ```typescript
    // Types for parsed narrative messages
    export type MessageType = 'dm_narration' | 'pc_dialogue' | 'sheet_update' | 'system';

    export interface ParsedMessage {
      agent: string;
      content: string;
      messageType: MessageType;
      index: number;  // original index in ground_truth_log for keying
    }

    // Character info for rendering
    export interface CharacterInfo {
      name: string;
      characterClass: string;
      classSlug: string;  // lowercase for CSS class matching
    }
    ```
  - [ ] 1.2: Implement `parseLogEntry(entry: string): { agent: string; content: string }`:
    - Check if entry starts with `[`
    - Find matching `]`
    - Extract agent from brackets, content from remainder
    - Strip leading `: ` from content
    - Handle duplicate prefix stripping (LLM echo)
    - Entries without brackets default to agent `"dm"`
  - [ ] 1.3: Implement `getMessageType(agent: string): MessageType`:
    - `"dm"` or `"DM"` returns `"dm_narration"`
    - `"SHEET"` returns `"sheet_update"`
    - All others return `"pc_dialogue"`
  - [ ] 1.4: Implement `parseGroundTruthLog(log: string[]): ParsedMessage[]`:
    - Maps over the log array, calling `parseLogEntry` and `getMessageType` for each entry
    - Preserves original index for React-like keying
  - [ ] 1.5: Implement `resolveCharacterInfo(agentName: string, characters: Record<string, any>): CharacterInfo`:
    - Direct key lookup (lowercase)
    - Name search fallback
    - Default to `{ name: agentName, characterClass: 'Adventurer', classSlug: 'adventurer' }`
  - [ ] 1.6: Implement `sanitizeContent(content: string): string`:
    - Escape `<`, `>`, `&`, `"`, `'` characters
    - This is for plain text display, not `{@html}` — but defense in depth
  - [ ] 1.7: Implement `formatActionText(content: string): string`:
    - Replace `*text*` patterns with styled markup (for use with `{@html}`)
    - Must sanitize content FIRST, then apply action text formatting
    - Returns safe HTML string
  - [ ] 1.8: Implement `formatDiceNotation(content: string): string`:
    - Regex to find dice patterns: `/\b(\d+d\d+(?:[+-]\d+)?)\b/g`
    - Wrap matches in `<span class="dice-roll">` tags
    - Must work on already-sanitized content (no double-escaping)
  - [ ] 1.9: Combine formatting: `formatMessageContent(content: string, messageType: MessageType): string`:
    - Sanitize → format dice → format actions (for PC messages)
    - Sanitize → format dice (for DM messages — entire text is italic via CSS)
    - Sanitize only (for sheet updates — no action/dice formatting)

- [ ] **Task 2: Create NarrativeMessage component** (AC: 3, 4, 5, 6, 7, 11, 12)
  - [ ] 2.1: Create `frontend/src/lib/components/NarrativeMessage.svelte`
  - [ ] 2.2: Define props using `$props()`:
    ```typescript
    interface Props {
      message: ParsedMessage;
      characterInfo?: CharacterInfo;
      isCurrent: boolean;
    }
    ```
  - [ ] 2.3: Implement DM narration rendering:
    - `<div class="dm-message" class:current-turn={isCurrent}>`
    - Content rendered with `{@html formatMessageContent(message.content, 'dm_narration')}`
    - DM styling via scoped CSS (gold left border, italic, Lora font)
  - [ ] 2.4: Implement PC dialogue rendering:
    - `<div class="pc-message {classSlug}" class:current-turn={isCurrent}>`
    - Attribution: `<span class="pc-attribution {classSlug}">{name}, the {class}:</span>`
    - Content rendered with `{@html formatMessageContent(message.content, 'pc_dialogue')}`
    - Character color applied via CSS class (`.pc-message.fighter`, `.pc-message.rogue`, etc.)
  - [ ] 2.5: Implement sheet update rendering:
    - `<div class="sheet-notification" class:current-turn={isCurrent}>`
    - Content rendered with `{@html formatMessageContent(message.content, 'sheet_update')}`
    - Amber accent styling via scoped CSS
  - [ ] 2.6: Implement system message rendering:
    - `<div class="system-message">`
    - Muted, centered, smaller text
  - [ ] 2.7: Add scoped CSS for all message types:
    - DM: gold border, italic Lora, justified, message bubble background
    - PC: character-colored border/attribution, action text styling
    - Sheet: amber background/border, Inter font
    - System: muted, centered, no border
    - Current turn: glow animation keyframes
    - Dice roll: JetBrains Mono, amber color
    - Action text: italic, secondary color
  - [ ] 2.8: Implement dynamic character color via CSS class matching:
    - The `classSlug` prop maps to CSS classes: `.fighter`, `.rogue`, `.wizard`, `.cleric`
    - Each class sets `border-left-color` and attribution color via CSS custom properties
    - Unknown classes fall back to `--text-secondary`

- [ ] **Task 3: Create ThinkingIndicator component** (AC: 10)
  - [ ] 3.1: Create `frontend/src/lib/components/ThinkingIndicator.svelte`
  - [ ] 3.2: Define props:
    ```typescript
    interface Props {
      agentName?: string;
      agentClass?: string;  // for coloring
      visible: boolean;
    }
    ```
  - [ ] 3.3: Implement 500ms delay before showing (use `$effect` with `setTimeout`):
    - When `visible` becomes `true`, start a 500ms timer
    - If `visible` becomes `false` before timer fires, cancel it
    - Only render the indicator after the timer fires
  - [ ] 3.4: Implement animated dots:
    - Three dots that pulse in sequence using CSS `@keyframes` animation
    - Staggered animation-delay for each dot (0s, 0.2s, 0.4s)
  - [ ] 3.5: Implement agent-specific text:
    - DM: "The Dungeon Master weaves the tale"
    - PC: "{Name} contemplates..." (e.g., "Thorin contemplates...")
    - Fallback: "The tale continues..."
    - Text in Lora italic, `--text-secondary` color
    - Agent name in character class color
  - [ ] 3.6: Add scoped CSS:
    - Fade-in transition (Svelte `transition:fade`)
    - Dot animation keyframes
    - Margin matching message spacing

- [ ] **Task 4: Create NarrativePanel component** (AC: 1, 8, 9, 13, 14)
  - [ ] 4.1: Create `frontend/src/lib/components/NarrativePanel.svelte`
  - [ ] 4.2: Define reactive state using `$state()`:
    ```typescript
    let scrollContainer: HTMLElement;
    let displayOffset = $state(0);  // for pagination
    let showScrollButton = $state(false);
    let showThinking = $state(false);
    ```
  - [ ] 4.3: Subscribe to `gameState` store to derive parsed messages:
    - Import `gameState` from `$lib/stores`
    - Use `$derived()` to compute `parsedMessages` from `$gameState?.ground_truth_log`
    - Apply pagination: slice to show last `(displayLimit + displayOffset)` messages
    - Compute `hiddenCount` for "Load earlier messages" button
  - [ ] 4.4: Implement session header:
    - Centered title: "Session {romanNumeral}" or session name from state
    - Lora font, 24px, `--color-dm` gold
    - Subtle bottom border separator
  - [ ] 4.5: Implement empty state:
    - When `ground_truth_log` is empty, show centered placeholder
    - "The adventure awaits... Start a new game to begin."
    - Lora italic, `--text-secondary`, vertically centered
  - [ ] 4.6: Implement message list rendering:
    - `{#each visibleMessages as message (message.index)}` with keyed loop
    - Render `<NarrativeMessage>` for each, passing `characterInfo` and `isCurrent`
    - `isCurrent` is true only for the last message
  - [ ] 4.7: Implement "Load earlier messages" button:
    - Appears when `hiddenCount > 0`
    - On click: increment `displayOffset` by `displayLimit`
    - Preserve scroll position: measure scroll height before/after prepend, adjust scrollTop
    - Button styling: `--text-secondary` color, `--bg-secondary` background, centered
  - [ ] 4.8: Implement auto-scroll logic:
    - Subscribe to `uiState` store for `autoScroll` boolean
    - On new message appended (reactive to `parsedMessages.length` change):
      - If `autoScroll` is true, scroll to bottom with `scrollBehavior: 'smooth'`
    - On user scroll event on the container:
      - Calculate distance from bottom: `scrollHeight - scrollTop - clientHeight`
      - If distance > 100px, set `autoScroll = false` (in uiStore)
      - If distance <= 100px, set `autoScroll = true`
    - Show "Resume auto-scroll" floating button when `autoScroll` is false
  - [ ] 4.9: Implement "Resume auto-scroll" button:
    - Fixed/absolute position at bottom-right of the narrative panel
    - `--accent-warm` background, white text, down-arrow icon (CSS or unicode)
    - On click: set `autoScroll = true`, scroll to bottom
    - Fade transition on show/hide
  - [ ] 4.10: Implement ThinkingIndicator integration:
    - Show when `isAutopilotRunning` is true AND no new message arrived for 500ms+
    - Pass current agent name/class from `$gameState?.current_turn`
    - Position below last message
  - [ ] 4.11: Add scoped CSS for panel layout:
    - `max-width: var(--max-content-width)` (800px), `margin: 0 auto`
    - `overflow-y: auto`, padding for comfortable reading
    - Session header styling
    - Responsive breakpoints (768px, 1024px)
    - Scroll-to-bottom button positioning

- [ ] **Task 5: Wire NarrativePanel into game page** (AC: 1, 2)
  - [ ] 5.1: Update `frontend/src/routes/game/[sessionId]/+page.svelte`:
    - Import `NarrativePanel` from `$lib/components/NarrativePanel.svelte`
    - Import `createGameConnection` from `$lib/ws`
    - Import stores: `gameState`, `isAutopilotRunning`, `connectionStatus`
    - Import `uiState` from `$lib/stores`
  - [ ] 5.2: Establish WebSocket connection on mount:
    ```typescript
    import { onMount, onDestroy } from 'svelte';

    let connection: GameConnection;

    onMount(() => {
      connection = createGameConnection(sessionId);
      connectionStatus.set('connecting');

      connection.onConnect(() => {
        connectionStatus.set('connected');
      });

      connection.onDisconnect((reason) => {
        connectionStatus.set('reconnecting');
      });

      connection.onMessage((event) => {
        if (event.type === 'session_state') {
          gameState.set(event.state as GameState);
        } else if (event.type === 'turn_update') {
          // Append new turn to existing state
          gameState.update((state) => {
            if (!state) return state;
            return {
              ...state,
              ground_truth_log: [...state.ground_truth_log, `[${event.agent}]: ${event.content}`],
              current_turn: event.agent,
              turn_number: event.turn,
            };
          });
        } else if (event.type === 'autopilot_started') {
          isAutopilotRunning.set(true);
        } else if (event.type === 'autopilot_stopped') {
          isAutopilotRunning.set(false);
        } else if (event.type === 'error') {
          lastError.set(event.message);
        }
      });

      connection.connect();
    });

    onDestroy(() => {
      connection?.disconnect();
    });
    ```
  - [ ] 5.3: Replace placeholder content with `<NarrativePanel />` component
  - [ ] 5.4: Add connection status indicator:
    - Small badge in corner showing connection state
    - Green dot for connected, amber for reconnecting, red for disconnected
    - Uses `connectionStatus` store
  - [ ] 5.5: Add scoped CSS for game page layout (padding, full height)

- [ ] **Task 6: Add narrative store for derived state** (AC: 9, 10)
  - [ ] 6.1: Create `frontend/src/lib/stores/narrativeStore.ts`:
    ```typescript
    import { derived } from 'svelte/store';
    import { gameState } from './gameStore';
    import { parseGroundTruthLog, type ParsedMessage } from '$lib/narrative';

    // Derived store: parsed messages from ground truth log
    export const narrativeMessages = derived(gameState, ($gs) => {
      if (!$gs) return [];
      return parseGroundTruthLog($gs.ground_truth_log);
    });

    // Derived store: display limit from config
    export const displayLimit = derived(gameState, ($gs) => {
      return $gs?.game_config?.narrative_display_limit ?? 50;
    });
    ```
  - [ ] 6.2: Update `frontend/src/lib/stores/index.ts` to export narrative stores

- [ ] **Task 7: Responsive layout and typography** (AC: 14)
  - [ ] 7.1: Add CSS media queries in `NarrativePanel.svelte`:
    ```css
    /* Default: desktop (>1024px) */
    .narrative-panel {
      max-width: var(--max-content-width);
      margin: 0 auto;
      padding: 0 var(--space-lg);
    }

    /* Tablet (768px - 1024px) */
    @media (max-width: 1024px) {
      .narrative-panel {
        max-width: 100%;
        padding: 0 var(--space-md);
      }
    }

    /* Mobile (< 768px) */
    @media (max-width: 768px) {
      .narrative-panel {
        padding: 0 var(--space-sm);
      }
    }
    ```
  - [ ] 7.2: Add responsive font adjustments in `NarrativeMessage.svelte`:
    - Below 768px: reduce DM text to 17px, PC text to 16px
    - Ensure line length stays ~70 characters maximum
  - [ ] 7.3: Ensure session header and buttons are readable at all breakpoints

- [ ] **Task 8: Verify integration and visual fidelity** (AC: all)
  - [ ] 8.1: Start backend: `uvicorn api.main:app --reload --port 8000`
  - [ ] 8.2: Start frontend: `cd frontend && npm run dev`
  - [ ] 8.3: Navigate to `http://localhost:5173/game/test-session`
  - [ ] 8.4: Verify WebSocket connects (check browser console for `[WS] Connected`)
  - [ ] 8.5: Use chrome-devtools MCP to take screenshots at various viewports:
    - Desktop (1440x900)
    - Tablet (768x1024)
    - Narrow (600x800)
  - [ ] 8.6: Verify all message types render correctly with proper fonts, colors, borders
  - [ ] 8.7: Verify auto-scroll behavior (scroll up, button appears, click to resume)
  - [ ] 8.8: Verify "Load earlier messages" button works with scroll position preserved
  - [ ] 8.9: Run `cd frontend && npm run check` — verify TypeScript type checking passes
  - [ ] 8.10: Verify no regressions: `cd frontend && npm run build` succeeds

- [ ] **Task 9: Verify no Python backend regressions** (AC: all)
  - [ ] 9.1: Run `python -m ruff check .` from project root — no new violations
  - [ ] 9.2: Run `python -m pytest` from project root — no regressions in existing tests
  - [ ] 9.3: Verify `uvicorn api.main:app` — no import errors or startup failures

## Dev Notes

### Architecture Context

This story builds the **heart of the autodungeon frontend** — the narrative panel where the D&D story unfolds. It is the SvelteKit replacement for the Streamlit `render_narrative_messages()` function and all its supporting renderers (`render_dm_message_html`, `render_pc_message_html`, `render_sheet_message_html`) from `app.py`.

The narrative panel is a read-only view that subscribes to the `gameState` store (populated via WebSocket). It does NOT send commands — that is the responsibility of the sidebar controls (Story 16-6) and game page controls. The panel's only interactive elements are:
1. "Load earlier messages" pagination button
2. "Resume auto-scroll" button
3. Scroll interaction (pause/resume auto-scroll)

**Key Principle:** The narrative panel renders from the `ground_truth_log` array in GameState. Each entry is a string in the format `"[agent_name]: message content"`. The frontend parses these strings into typed messages for rendering — mirroring the `parse_log_entry()` function from `models.py`.

### Component Hierarchy

```
game/[sessionId]/+page.svelte
  └── NarrativePanel.svelte
        ├── Session Header (inline)
        ├── "Load Earlier Messages" button (conditional)
        ├── {#each} NarrativeMessage.svelte
        │     ├── DM Narration (gold border, italic)
        │     ├── PC Dialogue (character-colored, attributed)
        │     ├── Sheet Update (amber accent)
        │     └── System Message (muted)
        ├── ThinkingIndicator.svelte (conditional)
        └── "Resume Auto-Scroll" button (conditional)
```

### Log Entry Format Reference

The `ground_truth_log` contains strings in this format:

```
"[DM]: The tavern door creaks open, revealing a dimly lit room..."
"[Thorin]: *draws his sword* \"Stay behind me,\" he growls."
"[SHEET]: HP Updated: Thorin 45/50 → 38/50 (-7 damage)"
"[Shadowmere]: *slips into the shadows* I'll scout ahead."
```

The frontend parser must handle:
- `[agent]: content` — standard format
- `[agent]: [agent]: content` — duplicate prefix (LLM echo, strip the second)
- `content without brackets` — treat as DM narration (fallback)
- `[]` — empty brackets, use "unknown" as agent

### Character Color Resolution

The class-to-color mapping is handled via CSS classes, NOT JavaScript. The component sets a CSS class on the message element (e.g., `class="pc-message fighter"`), and scoped CSS rules map classes to colors:

```css
.pc-message.fighter { border-left-color: var(--color-fighter); }
.pc-attribution.fighter { color: var(--color-fighter); }
```

This approach (ported from `styles/theme.css` lines 302-311) means:
- No hardcoded hex values in JavaScript
- Colors are overridable via CSS custom properties
- New character classes can be added by adding CSS rules
- The `classSlug` is the lowercase character class (e.g., "fighter", "rogue", "wizard", "cleric")

For characters with non-standard classes (custom creation from Epic 9), the fallback is `--text-secondary` for both border and attribution color. The component should include a generic fallback CSS rule.

### Action Text Formatting

PC messages may contain action text wrapped in asterisks: `*draws his sword*`. This is a roleplay convention (from SillyTavern/roleplay communities) that distinguishes narrated actions from spoken dialogue.

The formatter:
1. Sanitizes the raw content (escape HTML entities)
2. Replaces `*text*` patterns with `<span class="action-text">text</span>`
3. The `action-text` class applies italic styling and `--text-secondary` color

This uses `{@html}` in the Svelte template, which is safe because the content is sanitized before the action text spans are inserted. The sanitization happens first, then the formatting adds only known-safe HTML.

**Implementation:**
```typescript
function formatActionText(sanitizedContent: string): string {
  return sanitizedContent.replace(/\*([^*]+)\*/g, '<span class="action-text">$1</span>');
}
```

### Dice Roll Formatting

Dice notation (e.g., `1d20+5`, `3d6`, `2d8+3`) should be visually distinct from narrative text. The formatter wraps dice patterns in a styled span:

```typescript
function formatDiceNotation(content: string): string {
  return content.replace(/\b(\d+d\d+(?:[+-]\d+)?)\b/g, '<span class="dice-roll">$1</span>');
}
```

The `.dice-roll` class applies:
- `font-family: var(--font-mono)` (JetBrains Mono)
- `color: var(--accent-warm)` (amber)
- Optional: subtle background highlight

### Auto-Scroll Implementation

Auto-scroll is the most nuanced UX behavior in this component. The implementation must handle:

1. **New message arrives + user at bottom** → scroll down smoothly
2. **New message arrives + user scrolled up** → do NOT scroll (user is reading history)
3. **User scrolls to bottom** → re-enable auto-scroll
4. **User scrolls up** → disable auto-scroll, show "Resume" button

The scroll detection uses the `scroll` event on the narrative container:

```typescript
function handleScroll(event: Event) {
  const el = event.target as HTMLElement;
  const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
  const isAtBottom = distanceFromBottom < 100;  // 100px threshold

  uiState.update(s => ({ ...s, autoScroll: isAtBottom }));
  showScrollButton = !isAtBottom;
}
```

For scrolling to bottom on new messages, use a reactive effect:

```typescript
$effect(() => {
  if ($uiState.autoScroll && parsedMessages.length > 0) {
    // Use tick() to wait for DOM update, then scroll
    tick().then(() => {
      scrollContainer?.scrollTo({
        top: scrollContainer.scrollHeight,
        behavior: 'smooth'
      });
    });
  }
});
```

**Important:** Use Svelte's `tick()` to wait for DOM updates before scrolling, otherwise the scroll target may not include the newly rendered message.

### Scroll Position Preservation for Pagination

When "Load earlier messages" prepends messages, the scroll position must be preserved so the user does not jump to the top. The technique:

1. Before prepending: capture `scrollHeight` and `scrollTop`
2. After DOM update: new `scrollHeight` is larger
3. Set `scrollTop = newScrollHeight - oldScrollHeight + oldScrollTop`

```typescript
async function loadEarlierMessages() {
  const oldHeight = scrollContainer.scrollHeight;
  const oldTop = scrollContainer.scrollTop;

  displayOffset += displayLimit;

  await tick();  // Wait for DOM update

  const newHeight = scrollContainer.scrollHeight;
  scrollContainer.scrollTop = newHeight - oldHeight + oldTop;
}
```

### WebSocket Integration Pattern

The game page establishes the WebSocket connection and dispatches events to stores. The NarrativePanel reads from stores — it does NOT directly interact with the WebSocket. This separation follows the architecture principle: "stores are the single source of truth for UI rendering."

```
WebSocket → game page event handler → store updates → NarrativePanel reacts
```

The `turn_update` event from the WebSocket includes:
```json
{
  "type": "turn_update",
  "turn": 42,
  "agent": "dm",
  "content": "The dragon roars...",
  "state": { ... }
}
```

The game page handler reconstructs the log entry format (`[agent]: content`) and appends it to the `gameState.ground_truth_log` array. The NarrativePanel's derived store automatically recomputes the parsed messages.

### Thinking Indicator Agent Names

The thinking indicator should show a thematic message based on the current agent:

| Agent | Indicator Text |
|-------|---------------|
| `dm` / `DM` | "The Dungeon Master weaves the tale" |
| Fighter character | "{Name} steels their resolve" |
| Rogue character | "{Name} plots their next move" |
| Wizard character | "{Name} consults their arcane knowledge" |
| Cleric character | "{Name} seeks divine guidance" |
| Generic fallback | "The tale continues" |

These messages add flavor and maintain the campfire aesthetic during wait times.

### HTML Sanitization Strategy

**Defense in depth with two layers:**

1. **Content sanitization** (`sanitizeContent()`): All LLM-generated text is HTML-escaped before any processing. This converts `<`, `>`, `&`, `"`, `'` to their HTML entity equivalents.

2. **Controlled `{@html}` usage**: After sanitization, the formatter adds ONLY known-safe HTML elements (`<span class="action-text">`, `<span class="dice-roll">`). The `{@html}` directive is used on this post-processed content.

**Never** pass raw, unsanitized LLM content to `{@html}`. The processing pipeline is:
```
raw content → sanitizeContent() → formatDiceNotation() → formatActionText() → {@html result}
```

### Svelte 5 Patterns Used

This story uses Svelte 5 runes and patterns:

| Pattern | Usage |
|---------|-------|
| `$props()` | Component props (NarrativeMessage, ThinkingIndicator) |
| `$state()` | Local reactive state (displayOffset, showScrollButton) |
| `$derived()` | Computed values (parsedMessages, visibleMessages) |
| `$effect()` | Side effects (auto-scroll, thinking indicator timer) |
| `{@html}` | Rendering formatted message content (after sanitization) |
| `{#each ... (key)}` | Keyed iteration over messages |
| `class:name={condition}` | Conditional CSS classes |
| `transition:fade` | Fade transitions for buttons/indicators |
| `onMount` / `onDestroy` | Lifecycle for WebSocket connection |

**Stores** (`writable`, `derived` from `svelte/store`) are used for cross-component state (`gameState`, `uiState`, `narrativeMessages`). Runes are used for intra-component state.

### Existing Code Reference (Streamlit → SvelteKit Port)

| Streamlit (app.py) | SvelteKit | What to Port |
|---------------------|-----------|-------------|
| `parse_log_entry()` (models.py:1926) | `narrative.ts:parseLogEntry()` | Log entry parsing logic |
| `render_dm_message_html()` (app.py:1254) | `NarrativeMessage.svelte` (DM branch) | Gold border, italic, Lora font |
| `render_pc_message_html()` (app.py:1466) | `NarrativeMessage.svelte` (PC branch) | Character colors, attribution format |
| `render_sheet_message_html()` (app.py:1282) | `NarrativeMessage.svelte` (Sheet branch) | Amber accent, Inter font |
| `format_pc_content()` (app.py:1450) | `narrative.ts:formatActionText()` | `*action*` → italic span |
| `render_narrative_messages()` (app.py:1617) | `NarrativePanel.svelte` | Pagination, rendering loop, empty state |
| `get_character_info()` (app.py:1585) | `narrative.ts:resolveCharacterInfo()` | Character lookup for attribution |
| `escape_html()` | `narrative.ts:sanitizeContent()` | XSS prevention |
| Theme CSS (theme.css:250-330) | Scoped CSS in components | Message styling (ported, not copied) |
| Current-turn animation (theme.css:966-979) | Scoped CSS in NarrativeMessage | Glow keyframes |

### File Structure Created by This Story

```
frontend/src/
├── lib/
│   ├── narrative.ts                              # Log parsing, formatting, sanitization
│   ├── components/
│   │   ├── NarrativePanel.svelte                 # Main panel (scrolling, pagination, layout)
│   │   ├── NarrativeMessage.svelte               # Individual message rendering
│   │   └── ThinkingIndicator.svelte              # Animated thinking dots
│   └── stores/
│       ├── narrativeStore.ts                     # Derived stores for parsed messages
│       └── index.ts                              # Updated barrel export
└── routes/
    └── game/
        └── [sessionId]/
            └── +page.svelte                      # Updated: WebSocket + NarrativePanel
```

### Common Pitfalls to Avoid

1. **Do NOT use `{@html}` on raw LLM content.** Always sanitize first. The formatting pipeline must be: sanitize → format dice → format actions → `{@html}`.
2. **Do NOT hardcode hex color values in JavaScript or inline styles.** Use CSS classes that reference CSS custom properties. The class-based approach (`class="pc-message fighter"`) is more maintainable and themeable.
3. **Do NOT use `innerHTML` or direct DOM manipulation.** Use Svelte's reactive system (`$state`, `$derived`, `$effect`) for all state changes and rendering.
4. **Do NOT forget `tick()` before scrolling.** Svelte batches DOM updates. If you scroll immediately after a state change, the new content may not be in the DOM yet.
5. **Do NOT subscribe to stores in the component script without unsubscribing.** Use `$` prefix for auto-subscriptions in `.svelte` files, or use `derived` stores.
6. **Do NOT modify any Python files.** This is a frontend-only story. The backend API and game engine are unchanged.
7. **Do NOT install new npm packages** unless absolutely necessary. The narrative panel should work with native browser APIs and Svelte built-ins. The `{@html}` directive with manual sanitization is simpler and lighter than a DOMPurify dependency.
8. **Do NOT create full tests in this story.** Testing is Story 16-11. However, the `narrative.ts` parsing functions are pure functions that will be easy to test later.
9. **Scroll event throttling:** The `handleScroll` function fires frequently. Use passive event listeners (`on:scroll|passive={handleScroll}`) and avoid expensive computation in the handler.
10. **Keyed `{#each}` is essential.** Use `(message.index)` as the key to prevent Svelte from recreating DOM nodes when messages are prepended by pagination.

### Development Workflow

```bash
# Terminal 1: Backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
# Opens http://localhost:5173

# Navigate to http://localhost:5173/game/{sessionId}
# The WebSocket will attempt to connect via Vite proxy to backend
```

For visual verification, use the chrome-devtools MCP:
```
navigate_page → http://localhost:5173/game/test-session
take_screenshot → verify campfire theme, message styling
resize_page → verify responsive behavior at different widths
take_snapshot → inspect accessibility tree
```

### References

- [Source: app.py:1254-1270 -- `render_dm_message_html()` — DM message HTML structure]
- [Source: app.py:1282-1301 -- `render_sheet_message_html()` — Sheet update HTML structure]
- [Source: app.py:1450-1463 -- `format_pc_content()` — Action text formatting with regex]
- [Source: app.py:1466-1492 -- `render_pc_message_html()` — PC message HTML with attribution]
- [Source: app.py:1585-1614 -- `get_character_info()` — Character lookup logic]
- [Source: app.py:1617-1688 -- `render_narrative_messages()` — Pagination, display logic]
- [Source: models.py:1894-1956 -- `NarrativeMessage`, `parse_log_entry()` — Log entry parsing]
- [Source: styles/theme.css:250-328 -- DM/PC/Sheet message CSS styling]
- [Source: styles/theme.css:966-979 -- Current-turn highlight animation]
- [Source: frontend/src/app.css -- CSS custom properties (design tokens)]
- [Source: frontend/src/lib/ws.ts -- WebSocket client with auto-reconnect]
- [Source: frontend/src/lib/stores/gameStore.ts -- Game state store]
- [Source: frontend/src/lib/stores/uiStore.ts -- UI state store with autoScroll]
- [Source: frontend/src/lib/types.ts -- TypeScript types (GameState, WsServerEvent)]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md -- Typography, colors, layout specs]
- [Source: _bmad-output/planning-artifacts/architecture.md -- WebSocket protocol, state management]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-11.md -- Story 16-5 scope]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
