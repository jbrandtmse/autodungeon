# Story 16.6: Sidebar & Party Controls

Status: ready-for-dev

## Story

As a **user watching or playing an autodungeon session**,
I want **a fully functional sidebar with a party panel showing character cards, game controls for autopilot/speed/pause, human drop-in/release/nudge controls, a mode indicator, combat initiative display, connection status, and keyboard shortcut hints**,
so that **I can see the party at a glance, take control of characters, manage game pacing, and interact with the adventure without leaving the narrative view**.

## Acceptance Criteria (Given/When/Then)

### AC1: Sidebar Replaces Placeholder in Layout

**Given** the root layout at `+layout.svelte` currently shows `"Party panel (Story 16-6)"` placeholder text
**When** the sidebar components are implemented
**Then** the placeholder is replaced with the full sidebar component tree:
  - Mode indicator (top)
  - Game controls section
  - Party panel with character cards
  - Combat initiative display (when active)
  - Keyboard shortcuts hint
  - Human controls (nudge input, whisper placeholder)
  - Story threads (placeholder)
  - Connection status indicator (bottom)
**And** the sidebar background is `--bg-secondary` (#2D2520), fixed 240px width, full viewport height
**And** the sidebar scrolls vertically if content overflows

### AC2: Mode Indicator Displays Current State

**Given** the user is on the game page with an active session
**When** the sidebar renders
**Then** a mode indicator badge is shown at the top of the sidebar
**And** in Watch Mode: a pulsing green dot with "Watching" text, background `rgba(107,142,107,0.2)`, color `#6B8E6B`
**And** in Play Mode: a pulsing character-colored dot with "Playing as {Name}" text, background `rgba(232,168,73,0.2)`, color `--accent-warm`
**And** in Paused state: a static amber dot with "Paused" text (highest priority, overrides Watch/Play)
**And** the badge uses Inter font, 12px, weight 500, pill shape (border-radius 16px)
**And** the pulse animation cycles at 2 seconds with ease-in-out opacity/scale
**And** the mode indicator has `aria-live="polite"` for screen reader announcements

### AC3: Game Controls Section

**Given** the sidebar is rendered in a game session
**When** the user views the game controls section
**Then** the following controls are displayed:

**Start/Stop Autopilot button:**
  - If autopilot is NOT running: button shows "Start Autopilot" with play icon
  - If autopilot IS running: button shows "Stop Autopilot" with stop icon
  - Clicking sends `start_autopilot` or `stop_autopilot` WebSocket command
  - Button is disabled while human is controlling a character
  - Uses `--accent-warm` background (primary style) when starting, `--text-secondary` outline when stopping

**Next Turn button:**
  - Shows "Next Turn" or "Start Game" (if no messages in `ground_truth_log`)
  - Clicking sends `next_turn` WebSocket command
  - Disabled when autopilot is running or game is generating (thinking)
  - Uses secondary button style

**Pause/Resume button:**
  - If NOT paused: shows "Pause"
  - If paused: shows "Resume"
  - Clicking sends `pause` or `resume` WebSocket command
  - Only visible when autopilot is running
  - Uses secondary button style

**Speed selector:**
  - Dropdown/select with options: "Slow", "Normal", "Fast"
  - Current speed reflected from `speed` store
  - Changing sends `set_speed` WebSocket command with lowercase value
  - Uses campfire-themed dropdown styling (dark backgrounds, amber accents)

### AC4: Party Panel with Character Cards

**Given** the game state includes character configuration (from `game_config` or state `characters` dict)
**When** the party panel renders
**Then** a "Party" heading is displayed
**And** a character card is rendered for each PC in the party
**And** each card shows:
  - Character name in character class color (Inter 14px, weight 600)
  - Character class in `--text-secondary` (Inter 13px)
  - HP bar (if character sheet data available in state): colored bar showing current/max HP
    - Green (#6B8E6B) above 50%, amber (#E8A849) 25-50%, red (#C45C4A) below 25%
  - Status indicator: "AI" badge for AI control, "You" badge for human-controlled, thinking dots when generating
  - Drop-In / Release button
**And** cards have `--bg-secondary` background, 8px border-radius, 3px character-colored left border
**And** the controlled character card has `--bg-message` background, 4px left border, subtle glow (`box-shadow: 0 0 12px rgba(232,168,73,0.2)`)
**And** cards are wrapped in a `role="list"` container with each card as `role="listitem"`

### AC5: Drop-In / Release Button Per Character

**Given** a character card is rendered
**When** in AI-controlled state
**Then** a "Drop-In" button is shown with transparent background, 1px character-colored border, character-colored text
**And** on hover, the button fills with the character color and text inverts to `--bg-primary`
**And** clicking sends `drop_in` WebSocket command with the character name
**And** the button has `aria-label="Drop in as {Character Name}"`

**Given** the user is controlling this character
**When** the card renders
**Then** the button shows "Release" with filled character-color background
**And** clicking sends `release_control` WebSocket command
**And** the mode indicator updates to "Watching"

**Given** the user is controlling Character A
**When** they click "Drop-In" on Character B
**Then** a `release_control` command is sent first, followed by `drop_in` for Character B (quick switch, no confirmation dialog)

**Given** the game is generating (thinking)
**When** viewing drop-in buttons
**Then** all drop-in/release buttons are disabled (opacity 50%, cursor not-allowed)

### AC6: Human Action Input Area

**Given** the user has dropped in to control a character
**When** the sidebar renders
**Then** a context bar appears: "You are {Name}, the {Class}" in character color
**And** a text input area expands below with placeholder: "What do you do?"
**And** a "Submit" button appears below the input
**And** clicking Submit or pressing Enter sends `submit_action` WebSocket command with the input content
**And** the input clears after successful submission
**And** the area uses `max-height` CSS transition for smooth expand/collapse (300ms)

**Given** the user releases control
**When** the sidebar updates
**Then** the action input area collapses smoothly
**And** the context bar fades out

### AC7: Nudge Input

**Given** the user is in Watch Mode (not controlling a character)
**When** the sidebar renders below the party panel
**Then** a "Suggest Something" section appears with a text area (placeholder: "Whisper a suggestion to the DM...")
**And** a "Send Nudge" button
**And** clicking sends `nudge` WebSocket command with the text content
**And** the input clears after submission
**And** a brief toast notification confirms "Nudge sent" (3 second auto-dismiss)
**And** the nudge section is NOT visible when the user is controlling a character

### AC8: Combat Initiative Display

**Given** the game state includes `combat_state` with `active: true`
**When** the sidebar renders
**Then** an "Initiative" section appears below the party panel
**And** it shows a combat banner: "COMBAT - Round {N}" in amber
**And** a list of combatants in initiative order with initiative roll numbers
**And** PCs display in their character class color
**And** NPCs display in DM gold (`--color-dm`)
**And** the current turn combatant is highlighted with `--accent-warm` background highlight
**And** the "dm" entry (bookend) is excluded from the display

**Given** combat is not active
**When** the sidebar renders
**Then** the initiative section is hidden

### AC9: Connection Status Indicator

**Given** the `connectionStatus` store has a value
**When** the sidebar renders
**Then** a small connection badge is shown at the bottom of the sidebar
**And** connected: green dot + "Connected" text, `rgba(107,142,107,0.2)` background
**And** reconnecting: amber dot + "Reconnecting" text, `rgba(232,168,73,0.2)` background
**And** disconnected: red dot + "Disconnected" text, `rgba(196,92,74,0.15)` background
**And** the badge is unobtrusive (small text, muted colors)

### AC10: Keyboard Shortcuts Hint

**Given** the sidebar is rendered
**When** the user views the party section
**Then** below the character cards, a keyboard shortcuts hint is displayed:
  "Press 1 2 3 4 to drop in, Esc to release"
**And** the hint uses `--text-secondary` color, `--text-system` (13px) size
**And** keyboard key references use `<kbd>` elements with subtle background styling

### AC11: Keyboard Shortcut Implementation

**Given** the game page is active
**When** the user presses keys `1`, `2`, `3`, or `4` (not in an input field)
**Then** a `drop_in` WebSocket command is sent for the corresponding party member (1st, 2nd, 3rd, 4th character)
**And** the drop-in happens immediately, no confirmation

**Given** the user is controlling a character
**When** the user presses `Escape` (not in an input field)
**Then** a `release_control` WebSocket command is sent
**And** the user returns to Watch Mode

**Given** the user is typing in a text input or textarea
**When** they press `1-4` or `Escape`
**Then** the keyboard shortcuts do NOT fire (input fields suppress shortcuts)

### AC12: GameState Type Extension for Characters and Combat

**Given** the frontend TypeScript types in `types.ts`
**When** the sidebar components need character config and combat state data
**Then** the `GameState` interface is extended to include:
  - `characters: Record<string, Character>` (character configs keyed by agent key)
  - `combat_state?: CombatState | null` (combat initiative data)
**And** a `CombatState` interface is added:
  - `active: boolean`
  - `round_number: number`
  - `initiative_order: string[]`
  - `initiative_rolls: Record<string, number>`
  - `current_combatant: string`
  - `npc_profiles: Record<string, { name: string }>`
**And** a `CharacterSheet` interface is added (minimal, for HP display):
  - `hp: { current: number; max: number; temp: number }`

### AC13: WebSocket Command Sending from Sidebar

**Given** the sidebar needs to send commands to the backend
**When** the game page establishes a WebSocket connection
**Then** the `GameConnection.send()` method is accessible to sidebar components
**And** sidebar components import and use the connection via a shared context or store
**And** all commands use the typed `WsCommand` union from `types.ts`
**And** commands that receive `command_ack` events from the server confirm success (logged, not displayed)

### AC14: Responsive Sidebar Behavior

**Given** the browser viewport is resized
**When** the width changes:
  - Above 1024px: sidebar is 240px, fully visible
  - Between 768px and 1024px: sidebar compresses to 200px, smaller font sizes
  - Below 768px: sidebar collapses (hidden), hamburger menu to toggle
**And** sidebar overflow scrolls vertically
**And** all controls remain functional at all supported widths

### AC15: Story Threads Placeholder

**Given** the sidebar layout
**When** rendered
**Then** a collapsible "Story Threads" section appears as a placeholder
**And** it shows "Coming soon..." in muted text
**And** the section is collapsed by default (for future Epic story)

### AC16: Event Handling for Drop-In/Release Server Events

**Given** the WebSocket receives a `drop_in` event from the server
**When** the `handleServerMessage` function processes it
**Then** the `gameState` store is updated:
  - `human_active` set to `true`
  - `controlled_character` set to the character name from the event
**And** the `uiState` store is updated: `uiMode` set to `'play'`

**Given** the WebSocket receives a `release_control` event from the server
**When** the `handleServerMessage` function processes it
**Then** the `gameState` store is updated:
  - `human_active` set to `false`
  - `controlled_character` set to `null`
**And** the `uiState` store is updated: `uiMode` set to `'watch'`

**Given** the WebSocket receives an `awaiting_input` event
**When** the `handleServerMessage` function processes it
**Then** the action input area for the corresponding character activates
**And** a visual cue (pulsing border or focus) draws attention to the input area

## Tasks / Subtasks

- [ ] **Task 1: Extend TypeScript types** (AC: 12)
  - [ ] 1.1: Add `CombatState` interface to `frontend/src/lib/types.ts`:
    ```typescript
    export interface CombatState {
      active: boolean;
      round_number: number;
      initiative_order: string[];
      initiative_rolls: Record<string, number>;
      current_combatant: string;
      npc_profiles: Record<string, { name: string }>;
    }
    ```
  - [ ] 1.2: Add minimal `CharacterSheetHP` interface:
    ```typescript
    export interface CharacterSheetHP {
      current: number;
      max: number;
      temp: number;
    }
    ```
  - [ ] 1.3: Extend `GameState` interface with:
    ```typescript
    characters?: Record<string, Character>;
    combat_state?: CombatState | null;
    character_sheets?: Record<string, { hp: CharacterSheetHP }>;
    ```
  - [ ] 1.4: Add `WsAwaitingInput` handling to server events (already typed, verify gameStore handles it)

- [ ] **Task 2: Update gameStore to handle drop-in/release/awaiting_input events** (AC: 16)
  - [ ] 2.1: Update `handleServerMessage` in `gameStore.ts` to handle `drop_in` event:
    - Set `gameState.human_active = true`, `gameState.controlled_character = event.character`
  - [ ] 2.2: Handle `release_control` event:
    - Set `gameState.human_active = false`, `gameState.controlled_character = null`
  - [ ] 2.3: Handle `awaiting_input` event:
    - Add `awaitingInput` writable store (boolean), `awaitingInputCharacter` writable store (string)
    - Set both when `awaiting_input` event arrives
    - Clear when `turn_update` or `release_control` arrives
  - [ ] 2.4: Update `uiState` store on drop-in/release:
    - Import and update `uiState` in the relevant handlers: `uiMode: 'play'` / `uiMode: 'watch'`
  - [ ] 2.5: Export new stores from `index.ts`

- [ ] **Task 3: Create shared WebSocket send context** (AC: 13)
  - [ ] 3.1: Create `frontend/src/lib/stores/connectionStore.ts` extension (or new file `frontend/src/lib/stores/wsCommandStore.ts`):
    - Add a writable store `wsSend` that holds a `((cmd: WsCommand) => void) | null`
    - The game page sets this store when the WebSocket connection is established
  - [ ] 3.2: Update `game/[sessionId]/+page.svelte` to set the `wsSend` store on mount:
    ```typescript
    wsSend.set((cmd) => connection?.send(cmd));
    ```
    And clear it on destroy: `wsSend.set(null)`
  - [ ] 3.3: Export from `stores/index.ts`
  - [ ] 3.4: Create a helper `sendCommand(cmd: WsCommand): void` that reads the store and sends, with a console warning if not connected

- [ ] **Task 4: Create ModeIndicator component** (AC: 2)
  - [ ] 4.1: Create `frontend/src/lib/components/ModeIndicator.svelte`
  - [ ] 4.2: Subscribe to `gameState` (for `human_active`, `controlled_character`), `isPaused`, `uiState` (for `uiMode`)
  - [ ] 4.3: Derive mode state with priority: paused > play > watch
  - [ ] 4.4: Resolve character name and class color from `gameState.characters` when in play mode
  - [ ] 4.5: Render badge HTML:
    - Watch: `<div class="mode-indicator watch"><span class="pulse-dot"></span>Watching</div>`
    - Play: `<div class="mode-indicator play {classSlug}"><span class="pulse-dot"></span>Playing as {Name}</div>`
    - Paused: `<div class="mode-indicator paused"><span class="pause-dot"></span>Paused</div>`
  - [ ] 4.6: Add scoped CSS for mode indicator badge, pulse animation, character color variants
  - [ ] 4.7: Add `aria-live="polite"` attribute for accessibility

- [ ] **Task 5: Create CharacterCard component** (AC: 4, 5)
  - [ ] 5.1: Create `frontend/src/lib/components/CharacterCard.svelte`
  - [ ] 5.2: Define props:
    ```typescript
    interface Props {
      agentKey: string;
      name: string;
      characterClass: string;
      classSlug: string;
      isControlled: boolean;
      isGenerating: boolean;
      hp?: { current: number; max: number; temp: number };
    }
    ```
  - [ ] 5.3: Render card content:
    - Character name in class color
    - Character class in `--text-secondary`
    - HP bar (if `hp` prop provided): percentage-width div with color-coded fill
    - Status badge: "AI" / "You" / thinking dots
    - Drop-In / Release button
  - [ ] 5.4: Implement Drop-In button:
    - Import `sendCommand` helper from stores
    - On click (not controlled): send `{ type: 'drop_in', character: agentKey }`
    - On click (controlled): send `{ type: 'release_control' }`
    - Handle quick-switch: if another character is controlled, send release first, then drop-in
  - [ ] 5.5: Implement HP bar sub-element:
    - Bar background: `--bg-message` with rounded corners
    - Fill width: `percentage = (current/max) * 100`, clamped to 0-100
    - Fill color: green above 50%, amber 25-50%, red below 25%
    - Text overlay: "{current}/{max} HP" in small mono font
    - `role="meter"` with `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
  - [ ] 5.6: Add scoped CSS:
    - Card: `--bg-secondary` bg, 8px radius, 3px left border in character color
    - Controlled card: `--bg-message` bg, 4px left border, glow shadow
    - Name: Inter 14px weight 600, character color
    - Class: Inter 13px, `--text-secondary`
    - Drop-In button: transparent bg, 1px character-color border, hover fill effect
    - Release button: filled character-color bg, inverted text
    - Disabled: opacity 0.5, cursor not-allowed
    - CSS classes for `.fighter`, `.rogue`, `.wizard`, `.cleric` with respective colors

- [ ] **Task 6: Create PartyPanel component** (AC: 4, 10)
  - [ ] 6.1: Create `frontend/src/lib/components/PartyPanel.svelte`
  - [ ] 6.2: Subscribe to `gameState` store to derive party characters
  - [ ] 6.3: Derive character list from `$gameState?.characters` or fallback to `$gameState?.game_config`
  - [ ] 6.4: Render heading "Party" in sidebar section style
  - [ ] 6.5: Iterate over characters with `{#each}` and render `<CharacterCard>` for each
  - [ ] 6.6: Empty state: "No characters loaded" in muted text
  - [ ] 6.7: Render keyboard shortcuts hint below cards:
    - "Press" `<kbd>1</kbd><kbd>2</kbd><kbd>3</kbd><kbd>4</kbd>` "to drop in," `<kbd>Esc</kbd>` "to release"
    - Muted text, small font, `<kbd>` elements styled with subtle bg
  - [ ] 6.8: Wrap character cards in `role="list"` container

- [ ] **Task 7: Create GameControls component** (AC: 3)
  - [ ] 7.1: Create `frontend/src/lib/components/GameControls.svelte`
  - [ ] 7.2: Subscribe to `isAutopilotRunning`, `isPaused`, `speed`, `isThinking`, `gameState` stores
  - [ ] 7.3: Implement Start/Stop Autopilot button:
    - Label: "Start Autopilot" / "Stop Autopilot"
    - Send `start_autopilot` or `stop_autopilot` command
    - Disabled when human is controlling a character
  - [ ] 7.4: Implement Next Turn button:
    - Label: "Start Game" (if `ground_truth_log` empty) or "Next Turn"
    - Send `next_turn` command
    - Disabled when autopilot running or thinking
  - [ ] 7.5: Implement Pause/Resume button:
    - Only shown when autopilot is running
    - Label: "Pause" / "Resume"
    - Send `pause` or `resume` command
  - [ ] 7.6: Implement Speed selector:
    - `<select>` with options "Slow", "Normal", "Fast"
    - Bound to `speed` store value (capitalize for display)
    - On change: send `set_speed` command with lowercase value
  - [ ] 7.7: Add scoped CSS for control buttons and dropdown matching campfire theme

- [ ] **Task 8: Create HumanControls component** (AC: 6, 7)
  - [ ] 8.1: Create `frontend/src/lib/components/HumanControls.svelte`
  - [ ] 8.2: Subscribe to `gameState` for `human_active`, `controlled_character`, `characters`
  - [ ] 8.3: Implement action input area (shown when controlling):
    - Context bar: "You are {Name}, the {Class}" in character color
    - Text input with placeholder "What do you do?"
    - Submit button
    - Enter key submits (when not shift+enter)
    - Send `submit_action` command on submit, clear input
    - Smooth expand/collapse with `max-height` CSS transition (300ms)
  - [ ] 8.4: Implement awaiting input indicator:
    - When `awaitingInput` store is true and matches controlled character
    - Pulsing border animation on the input area
    - Focus the textarea automatically
  - [ ] 8.5: Implement nudge input (shown when NOT controlling):
    - "Suggest Something" heading
    - Text area with placeholder "Whisper a suggestion to the DM..."
    - "Send Nudge" button
    - Send `nudge` command on submit, clear input
    - Brief success toast on submission
  - [ ] 8.6: Add scoped CSS for expand/collapse transitions, input styling, context bar

- [ ] **Task 9: Create CombatInitiative component** (AC: 8)
  - [ ] 9.1: Create `frontend/src/lib/components/CombatInitiative.svelte`
  - [ ] 9.2: Subscribe to `gameState` for `combat_state`, `current_turn`, `characters`
  - [ ] 9.3: Only render when `combat_state?.active === true`
  - [ ] 9.4: Render combat banner: "COMBAT - Round {N}" in amber styling
  - [ ] 9.5: Render initiative order list:
    - Skip "dm" bookend entries
    - For NPC entries (starts with "dm:"): display NPC name in DM gold
    - For PC entries: display character name in class color
    - Show initiative roll number next to each name
    - Highlight current combatant with `--accent-warm` background
  - [ ] 9.6: Add scoped CSS for combat banner (amber border, dark bg) and initiative list entries

- [ ] **Task 10: Create ConnectionStatus component** (AC: 9)
  - [ ] 10.1: Create `frontend/src/lib/components/ConnectionStatus.svelte`
  - [ ] 10.2: Subscribe to `connectionStatus` store
  - [ ] 10.3: Render small badge with colored dot + status text
  - [ ] 10.4: Color mapping: connected (green), reconnecting (amber), disconnected (red), connecting (blue)
  - [ ] 10.5: Add scoped CSS for compact badge styling

- [ ] **Task 11: Create Sidebar component** (AC: 1, 15)
  - [ ] 11.1: Create `frontend/src/lib/components/Sidebar.svelte`
  - [ ] 11.2: Compose all sidebar sub-components:
    ```svelte
    <ModeIndicator />
    <GameControls />
    <hr class="sidebar-divider" />
    <PartyPanel />
    <CombatInitiative />
    <hr class="sidebar-divider" />
    <HumanControls />
    <hr class="sidebar-divider" />
    <StoryThreadsPlaceholder />
    <hr class="sidebar-divider" />
    <ConnectionStatus />
    ```
  - [ ] 11.3: Add `StoryThreadsPlaceholder`: collapsible section, collapsed by default, "Coming soon..." text
  - [ ] 11.4: Add sidebar section dividers with subtle horizontal rule styling
  - [ ] 11.5: Add scoped CSS for sidebar-specific layout, section spacing, dividers

- [ ] **Task 12: Update root layout** (AC: 1)
  - [ ] 12.1: Update `frontend/src/routes/+layout.svelte`:
    - Import `Sidebar` component
    - Replace sidebar placeholder content with `<Sidebar />`
    - Keep existing layout grid structure (`grid-template-columns: var(--sidebar-width) 1fr`)
  - [ ] 12.2: Add responsive media queries:
    - 768-1024px: sidebar compresses to 200px
    - Below 768px: sidebar hidden, hamburger toggle (basic implementation)

- [ ] **Task 13: Implement keyboard shortcuts** (AC: 11)
  - [ ] 13.1: Add `keydown` event listener in `game/[sessionId]/+page.svelte`:
    ```typescript
    function handleKeydown(event: KeyboardEvent) {
      // Skip if user is typing in an input/textarea
      const tag = (event.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (event.key >= '1' && event.key <= '4') {
        const index = parseInt(event.key) - 1;
        const characterKeys = Object.keys($gameState?.characters ?? {});
        if (index < characterKeys.length) {
          sendCommand({ type: 'drop_in', character: characterKeys[index] });
        }
      } else if (event.key === 'Escape') {
        if ($gameState?.human_active) {
          sendCommand({ type: 'release_control' });
        }
      }
    }
    ```
  - [ ] 13.2: Attach listener on mount: `window.addEventListener('keydown', handleKeydown)`
  - [ ] 13.3: Remove listener on destroy: `window.removeEventListener('keydown', handleKeydown)`
  - [ ] 13.4: Ensure input fields do not trigger shortcuts (tag check in handler)

- [ ] **Task 14: Verify integration and visual fidelity** (AC: all)
  - [ ] 14.1: Start backend: `uvicorn api.main:app --reload --port 8000`
  - [ ] 14.2: Start frontend: `cd frontend && npm run dev`
  - [ ] 14.3: Navigate to `http://localhost:5173/game/test-session`
  - [ ] 14.4: Verify sidebar renders with all sections (mode indicator, controls, party, shortcuts, connection)
  - [ ] 14.5: Use chrome-devtools MCP to take screenshots at various viewports:
    - Desktop (1440x900): full sidebar visible
    - Small desktop (1024x768): compressed sidebar
    - Tablet (768x1024): sidebar hidden/collapsed
  - [ ] 14.6: Verify all buttons send correct WebSocket commands (check browser Network/console)
  - [ ] 14.7: Verify mode indicator updates on drop-in/release events
  - [ ] 14.8: Verify keyboard shortcuts (1-4 drop-in, Esc release, not in input fields)
  - [ ] 14.9: Run `cd frontend && npm run check` -- TypeScript passes
  - [ ] 14.10: Run `cd frontend && npm run build` -- production build succeeds

- [ ] **Task 15: Verify no Python backend regressions** (AC: all)
  - [ ] 15.1: Run `python -m ruff check .` from project root -- no new violations
  - [ ] 15.2: Run `python -m pytest` from project root -- no regressions
  - [ ] 15.3: Verify `uvicorn api.main:app` -- no import errors or startup failures

## Dev Notes

### Architecture Context

This story builds the **entire interactive sidebar** for the autodungeon SvelteKit frontend. It is the SvelteKit replacement for the Streamlit `render_sidebar()` function (app.py:7070-7170) and all its sub-renderers: `render_mode_indicator_html`, `render_game_controls`, `render_character_card`, `render_session_controls`, `render_autopilot_toggle`, `render_nudge_input`, `render_keyboard_shortcuts_help`, `render_initiative_order`, `render_combat_banner`, and `render_fork_controls` (placeholder only).

Unlike the NarrativePanel (Story 16-5) which is read-only, the sidebar is the primary **command surface** -- it sends WebSocket commands to control the game. All user interactions (drop-in, autopilot, speed, pause, nudge, submit action) go through the WebSocket using typed `WsCommand` messages.

**Key Principle:** The sidebar reads from Svelte stores (populated by WebSocket events) and writes commands via the WebSocket `send()` method. The backend processes commands and broadcasts state updates. The sidebar re-renders reactively when stores change.

### Component Hierarchy

```
+layout.svelte
  └── Sidebar.svelte
        ├── ModeIndicator.svelte
        ├── GameControls.svelte
        │     ├── Start/Stop Autopilot button
        │     ├── Next Turn / Start Game button
        │     ├── Pause/Resume button
        │     └── Speed selector
        ├── PartyPanel.svelte
        │     ├── {#each} CharacterCard.svelte
        │     │     ├── Character name + class
        │     │     ├── HP bar (optional)
        │     │     ├── Status badge (AI/You/thinking)
        │     │     └── Drop-In/Release button
        │     └── Keyboard shortcuts hint
        ├── CombatInitiative.svelte (conditional)
        │     ├── Combat banner
        │     └── Initiative order list
        ├── HumanControls.svelte
        │     ├── Action input area (when controlling)
        │     └── Nudge input (when watching)
        ├── StoryThreadsPlaceholder (collapsed)
        └── ConnectionStatus.svelte
```

### WebSocket Command Flow

The sidebar needs to send commands to the backend. The `GameConnection.send()` method is created in the game page (`game/[sessionId]/+page.svelte`). To make it available to sidebar components (which live in `+layout.svelte`), we use a writable store:

```typescript
// connectionStore.ts (or new wsCommandStore.ts)
export const wsSend = writable<((cmd: WsCommand) => void) | null>(null);

// Helper for components:
export function sendCommand(cmd: WsCommand): void {
  const send = get(wsSend);
  if (send) {
    send(cmd);
  } else {
    console.warn('[WS] Cannot send command — not connected');
  }
}
```

The game page sets `wsSend` when the WebSocket connects, and clears it on destroy. Sidebar components call `sendCommand()` without needing direct access to the connection object.

**Important:** The sidebar is in `+layout.svelte` (always rendered), but commands only work when a game session is active and WebSocket is connected. The sidebar should gracefully handle the case where `wsSend` is null (e.g., on the home page). Controls that require a connection should be disabled when `connectionStatus !== 'connected'`.

### Store-Driven Reactivity

All sidebar state comes from stores. The sidebar NEVER directly modifies `gameState` -- it sends commands and waits for the server to broadcast state updates.

| Store | Source | Sidebar Usage |
|-------|--------|---------------|
| `gameState` | WebSocket `session_state` / `turn_update` | Characters, controlled_character, human_active, combat_state |
| `isAutopilotRunning` | WebSocket `autopilot_started` / `autopilot_stopped` | Toggle button label |
| `isPaused` | WebSocket `paused` / `resumed` | Pause/Resume button, mode indicator |
| `speed` | WebSocket `speed_changed` | Speed dropdown selection |
| `isThinking` | WebSocket `turn_update` timing | Disable buttons, show thinking dots |
| `connectionStatus` | WebSocket connect/disconnect | Connection badge, disable controls |
| `uiState` | Local (updated on drop-in/release events) | Mode indicator (watch/play) |

### Event Handling Gap: drop_in / release_control

The current `handleServerMessage` in `gameStore.ts` does NOT handle `drop_in` or `release_control` events -- these fall through to the `default` case. This story must add handling for these events to update `gameState.human_active`, `gameState.controlled_character`, and `uiState.uiMode`. The `awaiting_input` event is also unhandled and needs a new store.

### Character Data Resolution

The backend sends character data in the `session_state` event. The `state` object includes a `characters` dict keyed by agent key (e.g., `"fighter"`, `"rogue"`) with values matching the `Character` interface. However, the current `GameState` TypeScript type does not include `characters` -- this story must extend it.

For character class color resolution, use the same CSS class approach as Story 16-5:
```css
.character-card.fighter { border-left-color: var(--color-fighter); }
.character-name.fighter { color: var(--color-fighter); }
```

The `classSlug` is computed by lowercasing the character class and keeping only alphanumeric characters and hyphens (matching the Python `app.py:4077` logic).

### HP Bar

Character sheets with HP data may be available in `gameState.character_sheets` if the session has initialized sheets (Epic 8). The HP bar is an optional enhancement -- if HP data is not available, the card simply omits the bar. The HP color thresholds match `app.py:4135-4155`:
- Green (`#6B8E6B`) above 50%
- Amber (`#E8A849`) between 25-50%
- Red (`#C45C4A`) below 25%

### Combat Initiative

Combat state arrives in the `session_state` snapshot as `combat_state`. The initiative display mirrors `app.py:7788-7856`. Key rules:
- Skip the `"dm"` bookend entry (it's a routing artifact, not a combatant)
- NPC entries start with `"dm:"` (e.g., `"dm:goblin_1"`) -- display with NPC name from `npc_profiles`
- PC entries are agent keys (e.g., `"shadowmere"`) -- look up in `characters` dict for display name and class color
- Current combatant gets highlight styling

### Quick-Switch Logic

When clicking "Drop-In" on Character B while controlling Character A, the frontend should send `release_control` followed by `drop_in` for B. However, since the backend handles this atomically (the `drop_in` command on the engine implicitly releases the current character), the frontend can simply send the `drop_in` command for B. The backend will broadcast both `release_control` and `drop_in` events, which the store handlers will process in order. Verify this behavior against the `GameEngine.drop_in()` method.

### Nudge Toast Notification

For the brief "Nudge sent" confirmation, implement a simple inline notification rather than a full toast system (which would be overkill for this story). A small success message that appears for 3 seconds below the nudge button is sufficient:

```svelte
{#if showNudgeConfirmation}
  <p class="nudge-confirmation" transition:fade>Nudge sent</p>
{/if}
```

Use a `setTimeout` to clear the confirmation after 3 seconds.

### Keyboard Shortcuts

Keyboard shortcuts are implemented as a `window.addEventListener('keydown', ...)` in the game page component. They are NOT implemented in the sidebar component itself because:
1. The sidebar doesn't have focus context
2. Shortcuts should work regardless of which element has focus (as long as it's not an input)
3. The game page already manages the WebSocket connection

The handler must check `event.target.tagName` to suppress shortcuts when the user is typing in input/textarea/select elements.

### Svelte 5 Patterns Used

| Pattern | Usage |
|---------|-------|
| `$props()` | Component props (CharacterCard, ModeIndicator) |
| `$state()` | Local reactive state (nudge text, action text, showConfirmation) |
| `$derived()` | Computed values (isControlled, partyList, buttonLabel) |
| `$effect()` | Side effects (auto-focus on awaiting input, toast timeout) |
| `{#if}` | Conditional rendering (combat display, nudge vs action input) |
| `{#each ... (key)}` | Keyed iteration over character cards |
| `class:name={condition}` | Dynamic CSS classes (controlled, generating, class colors) |
| `transition:fade` | Fade transitions for toast notifications |
| `transition:slide` | Slide transitions for action input expand/collapse |
| `on:click` / `onclick` | Button click handlers |
| `on:keydown` | Keyboard shortcut listener |
| `bind:value` | Two-way binding for text inputs and select |

### Existing Code Reference (Streamlit -> SvelteKit Port)

| Streamlit (app.py) | SvelteKit | What to Port |
|---------------------|-----------|-------------|
| `render_mode_indicator_html()` (app.py:729) | `ModeIndicator.svelte` | Watch/Play/Paused badge with pulse dot |
| `render_game_controls()` (app.py:7713) | `GameControls.svelte` | Start/Next Turn button |
| `render_autopilot_toggle()` (app.py:3597) | `GameControls.svelte` | Start/Stop autopilot button |
| `render_session_controls()` (app.py:3616) | `GameControls.svelte` | Pause/Resume, Speed dropdown |
| `render_character_card()` (app.py:4062) | `CharacterCard.svelte` | Card with name, class, Drop-In button |
| `render_character_card_html()` (app.py:1512) | `CharacterCard.svelte` | Card HTML structure |
| `get_drop_in_button_label()` (app.py:1560) | `CharacterCard.svelte` | "Drop-In" / "Release" label |
| `handle_drop_in_click()` (app.py:3659) | `CharacterCard.svelte` + WebSocket | Drop-in/release via WS command |
| `render_nudge_input()` (app.py:796) | `HumanControls.svelte` | Nudge text area and submit |
| `render_keyboard_shortcuts_help_html()` (app.py:634) | `PartyPanel.svelte` | kbd hint text |
| `render_initiative_order_html()` (app.py:7788) | `CombatInitiative.svelte` | Initiative list with rolls |
| `render_combat_banner_html()` (app.py:7743) | `CombatInitiative.svelte` | "COMBAT - Round N" banner |
| `render_hp_bar_html()` (app.py:4158) | `CharacterCard.svelte` | HP bar with color coding |
| `get_hp_color()` (app.py:4135) | `CharacterCard.svelte` | HP color thresholds |
| `render_sidebar()` (app.py:7070) | `Sidebar.svelte` | Full sidebar composition |

### File Structure Created by This Story

```
frontend/src/
├── lib/
│   ├── components/
│   │   ├── Sidebar.svelte              # Root sidebar composition
│   │   ├── ModeIndicator.svelte        # Watch/Play/Paused badge
│   │   ├── GameControls.svelte         # Autopilot, Next Turn, Pause, Speed
│   │   ├── PartyPanel.svelte           # Character card list + shortcuts hint
│   │   ├── CharacterCard.svelte        # Individual character card with Drop-In
│   │   ├── HumanControls.svelte        # Action input + Nudge input
│   │   ├── CombatInitiative.svelte     # Initiative order (combat only)
│   │   └── ConnectionStatus.svelte     # WebSocket connection badge
│   ├── stores/
│   │   ├── gameStore.ts                # Updated: handle drop_in, release, awaiting_input
│   │   ├── connectionStore.ts          # Updated: add wsSend store + sendCommand helper
│   │   └── index.ts                    # Updated: export new stores
│   └── types.ts                        # Updated: CombatState, CharacterSheetHP, GameState ext
└── routes/
    ├── +layout.svelte                  # Updated: import Sidebar, replace placeholder
    └── game/
        └── [sessionId]/
            └── +page.svelte            # Updated: set wsSend store, keyboard shortcuts
```

### Common Pitfalls to Avoid

1. **Do NOT modify `gameState` directly in sidebar components.** Always send WebSocket commands and let the server broadcast state updates. The sidebar is a command surface, not a state manager.
2. **Do NOT hardcode character colors.** Use CSS classes (`.fighter`, `.rogue`, `.wizard`, `.cleric`) that reference CSS custom properties. New classes get fallback `--text-secondary`.
3. **Do NOT send commands when not connected.** Check `connectionStatus` or use the `sendCommand` helper which handles the null case gracefully.
4. **Do NOT fire keyboard shortcuts in input fields.** Always check `event.target.tagName` to prevent `1-4` and `Escape` from firing when the user is typing.
5. **Do NOT add toast library dependencies.** Simple inline confirmation messages with `setTimeout` are sufficient for this story. A full toast system can be added in Story 16-10 if needed.
6. **Do NOT block sidebar rendering on missing data.** Characters, combat state, and HP data may be absent. Use optional chaining and fallback rendering (empty state messages).
7. **Do NOT modify any Python backend files.** This is a frontend-only story. The API and engine are unchanged.
8. **Do NOT create full test suites.** Testing is Story 16-11. However, pure functions like HP color calculation and classSlug derivation should be testable.
9. **Do NOT use `{@html}` for sidebar content.** Unlike the narrative panel, sidebar content does not contain LLM-generated text. Use Svelte template syntax and reactive bindings directly.
10. **Do NOT forget to clean up the wsSend store on destroy.** Stale send functions can cause memory leaks or errors if the WebSocket connection is gone.

### Development Workflow

```bash
# Terminal 1: Backend
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
# Opens http://localhost:5173

# Navigate to http://localhost:5173/game/{sessionId}
# The sidebar should render with all controls
```

For visual verification, use the chrome-devtools MCP:
```
navigate_page -> http://localhost:5173/game/test-session
take_screenshot -> verify sidebar layout, character cards, controls
resize_page -> verify responsive behavior (1440, 1024, 768 widths)
take_snapshot -> inspect accessibility tree for ARIA attributes
```

### References

- [Source: app.py:729-779 -- `render_mode_indicator_html()` -- Mode indicator logic]
- [Source: app.py:782-827 -- `render_nudge_input()` -- Nudge input rendering]
- [Source: app.py:634-653 -- `render_keyboard_shortcuts_help_html()` -- Shortcuts hint]
- [Source: app.py:1512-1535 -- `render_character_card_html()` -- Card HTML structure]
- [Source: app.py:3597-3656 -- `render_session_controls()` -- Autopilot, Pause, Speed]
- [Source: app.py:3659-3695 -- `handle_drop_in_click()` -- Drop-in/release logic]
- [Source: app.py:4062-4117 -- `render_character_card()` -- Full card with button]
- [Source: app.py:4135-4184 -- `get_hp_color()`, `render_hp_bar_html()` -- HP bar]
- [Source: app.py:7070-7170 -- `render_sidebar()` -- Full sidebar composition]
- [Source: app.py:7713-7735 -- `render_game_controls()` -- Game control buttons]
- [Source: app.py:7743-7886 -- Combat banner + initiative order rendering]
- [Source: frontend/src/lib/types.ts -- TypeScript types (to extend)]
- [Source: frontend/src/lib/ws.ts -- WebSocket client (GameConnection.send)]
- [Source: frontend/src/lib/stores/gameStore.ts -- Game state store (to update)]
- [Source: frontend/src/lib/stores/connectionStore.ts -- Connection store (to extend)]
- [Source: frontend/src/lib/stores/uiStore.ts -- UI state store]
- [Source: frontend/src/routes/+layout.svelte -- Root layout (to update)]
- [Source: frontend/src/routes/game/[sessionId]/+page.svelte -- Game page (to update)]
- [Source: frontend/src/app.css -- CSS custom properties (design tokens)]
- [Source: api/schemas.py -- WebSocket event schemas]
- [Source: api/websocket.py -- WebSocket command routing]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md:1099-1297 -- Character Card and Mode Indicator CSS specs]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md:1504-1598 -- Mode transition, character interaction, button hierarchy patterns]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-11.md -- Epic 16 story breakdown]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
