# Story 16-11: Frontend Testing

**Epic:** 16 — UI Framework Migration (FastAPI + SvelteKit)
**Status:** done

---

## Story

As a **developer maintaining the autodungeon SvelteKit frontend**,
I want **a comprehensive test suite covering stores, utility modules, and key UI components using Vitest and @testing-library/svelte**,
so that **regressions are caught early, refactoring is safe, and the frontend codebase has at least baseline coverage for critical paths including state management, API interactions, WebSocket handling, narrative formatting, and component rendering**.

---

## Acceptance Criteria

### AC1: Test Framework Setup

**Given** the `frontend/` directory with an existing SvelteKit + Vite + TypeScript project
**When** a developer runs `npm run test` (or `npx vitest run`)
**Then** Vitest executes all `*.test.ts` and `*.test.svelte.ts` files under `frontend/src/`
**And** the test environment uses `jsdom` (or `happy-dom`) for DOM simulation
**And** `@testing-library/svelte` is available for rendering Svelte 5 components
**And** `$lib` path aliases resolve correctly in tests (via Vite's built-in SvelteKit alias resolution)
**And** the existing `npm run check` and `npm run build` commands still pass without error

### AC2: Store Unit Tests — gameStore

**Given** the `gameStore.ts` module exports `gameState`, `isAutopilotRunning`, `isPaused`, `speed`, `isThinking`, `thinkingAgent`, `awaitingInput`, `awaitingInputCharacter`, `handleServerMessage`, and `resetStores`
**When** the test suite runs
**Then** at least 12 tests verify:
  - `handleServerMessage` correctly updates `gameState` on `session_state` events
  - `handleServerMessage` appends to `ground_truth_log` on `turn_update` events
  - `handleServerMessage` sets `isAutopilotRunning` true/false on `autopilot_started`/`autopilot_stopped`
  - `handleServerMessage` sets `isPaused` on `paused`/`resumed`
  - `handleServerMessage` sets `speed` on `speed_changed`
  - `handleServerMessage` sets `human_active` and `controlled_character` on `drop_in`
  - `handleServerMessage` clears `human_active` and `controlled_character` on `release_control`
  - `handleServerMessage` sets `awaitingInput`/`awaitingInputCharacter` on `awaiting_input`
  - `handleServerMessage` clears `isThinking` on `error`
  - `handleServerMessage` handles unknown event types gracefully (no-op)
  - `resetStores` returns all stores to their initial values
  - `turn_update` with agent "SHEET" uses the correct prefix

### AC3: Store Unit Tests — connectionStore

**Given** the `connectionStore.ts` module exports `connectionStatus`, `lastError`, `wsSend`, and `sendCommand`
**When** the test suite runs
**Then** at least 4 tests verify:
  - `sendCommand` calls the stored send function when `wsSend` is set
  - `sendCommand` logs a warning (via `console.warn`) when `wsSend` is null
  - `connectionStatus` defaults to `'disconnected'`
  - `wsSend` can be set and cleared

### AC4: Store Unit Tests — uiStore

**Given** the `uiStore.ts` module exports `uiState` with its `UiState` interface
**When** the test suite runs
**Then** at least 3 tests verify:
  - Default values: `sidebarOpen: true`, `uiMode: 'watch'`, `autoScroll: true`, `settingsOpen: false`, `characterSheetName: null`, `comparisonForkId: null`
  - `uiState.update` correctly merges partial state
  - Each field can be set and read back independently

### AC5: Store Unit Tests — narrativeStore

**Given** the `narrativeStore.ts` module exports `narrativeMessages` (derived from `gameState`) and `displayLimit`
**When** the test suite runs
**Then** at least 4 tests verify:
  - `narrativeMessages` returns an empty array when `gameState` is null
  - `narrativeMessages` parses `ground_truth_log` entries into `ParsedMessage[]` when gameState is set
  - `narrativeMessages` re-derives when `gameState` changes
  - `displayLimit` defaults to 50 when `game_config.narrative_display_limit` is absent, and reflects the configured value when present

### AC6: Utility Tests — narrative.ts

**Given** the `narrative.ts` module exports `parseLogEntry`, `getMessageType`, `parseGroundTruthLog`, `resolveCharacterInfo`, `sanitizeContent`, `formatDiceNotation`, `formatActionText`, and `formatMessageContent`
**When** the test suite runs
**Then** at least 14 tests verify:
  - `parseLogEntry` extracts agent and content from `"[dm]: The door opens"`
  - `parseLogEntry` handles entries without brackets (fallback to dm)
  - `parseLogEntry` handles empty agent `"[]: message"` (uses "unknown")
  - `parseLogEntry` strips duplicate agent prefix when LLM echoes format
  - `getMessageType` returns `'dm_narration'` for `'dm'`, `'sheet_update'` for `'SHEET'`, `'system'` for `'system'`, `'pc_dialogue'` for any other agent
  - `parseGroundTruthLog` converts an array of raw entries into `ParsedMessage[]`
  - `resolveCharacterInfo` finds character by direct key lookup
  - `resolveCharacterInfo` finds character by name search
  - `resolveCharacterInfo` returns fallback for unknown agents
  - `sanitizeContent` escapes `<`, `>`, `&`, `"`, `'`
  - `formatDiceNotation` wraps dice notation in `<span class="dice-roll">` tags
  - `formatActionText` wraps `*action text*` in `<span class="action-text">` tags
  - `formatMessageContent` applies correct pipeline for each message type (dm_narration gets dice only, pc_dialogue gets dice + action, sheet_update/system gets sanitize only)
  - `formatMessageContent` sanitizes before formatting (XSS prevention)

### AC7: Utility Tests — format.ts

**Given** the `format.ts` module exports `toRomanNumeral` and `formatSessionDate`
**When** the test suite runs
**Then** at least 8 tests verify:
  - `toRomanNumeral(1)` returns `'I'`, `(4)` returns `'IV'`, `(9)` returns `'IX'`, `(42)` returns `'XLII'`, `(2024)` returns `'MMXXIV'`
  - `toRomanNumeral` returns decimal string for out-of-range values (0, 4000, negative, Infinity)
  - `formatSessionDate` formats a valid ISO timestamp as `"MMM DD, YYYY"`
  - `formatSessionDate` returns `"Unknown date"` for invalid timestamps

### AC8: Utility Tests — api.ts

**Given** the `api.ts` module exports session, character, fork, checkpoint, and character sheet API functions
**When** the test suite runs
**Then** at least 10 tests verify (using a mocked global `fetch`):
  - `getSessions` calls `GET /api/sessions` and returns parsed JSON
  - `createSession` calls `POST /api/sessions` with the correct body
  - `deleteSession` calls `DELETE` and does not attempt `response.json()` on 204
  - `getSession` calls `GET /api/sessions/{id}` with URL-encoded session ID
  - `ApiError` is thrown with correct `status`, `statusText`, and parsed `detail` on non-ok responses
  - `ApiError` falls back to raw body text when response is not JSON
  - `getForks` calls `GET /api/sessions/{id}/forks`
  - `createFork` calls `POST /api/sessions/{id}/forks` with `{ name }` body
  - `deleteFork` handles 204 No Content without error
  - `getCharacterSheet` calls the correct endpoint with URL-encoded character name

### AC9: Utility Tests — ws.ts

**Given** the `ws.ts` module exports `createGameConnection` returning a `GameConnection` object
**When** the test suite runs
**Then** at least 6 tests verify (using a mocked `WebSocket` global):
  - `connect()` creates a WebSocket with the correct URL based on `window.location`
  - `send()` serializes the command as JSON via `ws.send()`
  - `send()` logs an error when not connected
  - `disconnect()` closes the WebSocket with code 1000 and sets `isConnected` to false
  - `onMessage` callback receives parsed server events
  - `onConnect` and `onDisconnect` callbacks fire at appropriate times
  - The connection automatically responds to `ping` events with `pong`

### AC10: Component Tests — NarrativeMessage

**Given** the `NarrativeMessage.svelte` component accepts `message`, `characterInfo`, and `isCurrent` props
**When** the test suite runs
**Then** at least 5 tests verify:
  - A DM narration message renders with the `.dm-message` CSS class
  - A PC dialogue message renders with the `.pc-message` CSS class and character attribution text
  - A sheet update message renders with `.sheet-notification`
  - A system message renders with `.system-message`
  - The `current-turn` CSS class is applied when `isCurrent` is true

### AC11: Component Tests — SessionCard

**Given** the `SessionCard.svelte` component accepts `session`, `deleting`, and `onDelete` props
**When** the test suite runs
**Then** at least 4 tests verify:
  - The card renders session title using Roman numeral conversion
  - The card renders the session name (or "Unnamed Adventure" fallback)
  - The delete button calls `onDelete` with the session ID and stops event propagation
  - The card applies the `.deleting` class when `deleting` is true

### AC12: Component Tests — ConfirmDialog

**Given** the `ConfirmDialog.svelte` component accepts `open`, `title`, `message`, `confirmLabel`, `confirmDanger`, `error`, `onConfirm`, and `onCancel` props
**When** the test suite runs
**Then** at least 5 tests verify:
  - The dialog is not rendered when `open` is false
  - The dialog renders title, message, and confirm/cancel buttons when `open` is true
  - The confirm button uses the `confirmLabel` text
  - The cancel button calls `onCancel`
  - The confirm button calls `onConfirm`
  - An error message is displayed when the `error` prop is set

### AC13: Component Tests — CharacterCard

**Given** the `CharacterCard.svelte` component accepts `agentKey`, `name`, `characterClass`, `classSlug`, `isControlled`, `isGenerating`, and `hp` props
**When** the test suite runs
**Then** at least 4 tests verify:
  - The card renders the character name and class
  - The status badge shows "You" when `isControlled` is true
  - The status badge shows "AI" when not controlled and not generating
  - The HP bar renders when `hp` prop is provided with correct percentage

### AC14: Test Count and Coverage Target

**Given** the complete test suite
**When** `npx vitest run` completes
**Then** at least 50 tests pass across all test files
**And** zero tests are skipped without a documented reason
**And** the test run completes in under 30 seconds

### AC15: No Python File Modifications

**Given** this story is frontend-only
**When** examining the git diff
**Then** zero Python files (`.py`) have been modified
**And** only files under `frontend/` and `_bmad-output/implementation-artifacts/` are changed

---

## Tasks / Subtasks

- [x]**Task 1: Install test framework dependencies** (AC: 1)
  - [x]1.1: Add Vitest and related packages as devDependencies:
    ```bash
    cd frontend
    npm install -D vitest @testing-library/svelte @testing-library/jest-dom jsdom
    ```
  - [x]1.2: Add `@sveltejs/vite-plugin-svelte` testing support — verify `svelte.config.js` is compatible with Vitest's Svelte preprocessing
  - [x]1.3: Add Vitest type declarations to `tsconfig.json` if needed (typically via `/// <reference types="vitest" />`)

- [x]**Task 2: Configure Vitest** (AC: 1)
  - [x]2.1: Create `frontend/vitest.config.ts` (or add `test` config to existing `vite.config.ts`):
    ```typescript
    import { defineConfig } from 'vitest/config';
    import { sveltekit } from '@sveltejs/kit/vite';

    export default defineConfig({
      plugins: [sveltekit()],
      test: {
        include: ['src/**/*.test.ts'],
        environment: 'jsdom',
        globals: true,
        setupFiles: ['src/tests/setup.ts'],
        alias: {
          // $lib alias is automatically handled by sveltekit() plugin
        },
      },
    });
    ```
  - [x]2.2: Create `frontend/src/tests/setup.ts` for global test setup:
    - Import `@testing-library/jest-dom/vitest` for extended matchers
    - Set up any global mocks needed (e.g., `window.matchMedia`)
    - Mock CSS custom properties if needed for component tests
  - [x]2.3: Add npm scripts to `package.json`:
    ```json
    {
      "scripts": {
        "test": "vitest run",
        "test:watch": "vitest",
        "test:coverage": "vitest run --coverage"
      }
    }
    ```
  - [x]2.4: Verify `npm run test` runs and exits cleanly (with zero tests initially)
  - [x]2.5: Verify `npm run check` and `npm run build` still pass

- [x]**Task 3: Write gameStore tests** (AC: 2)
  - [x]3.1: Create `frontend/src/lib/stores/gameStore.test.ts`
  - [x]3.2: Import `get` from `svelte/store` for reading store values in tests
  - [x]3.3: Call `resetStores()` in `beforeEach` to ensure clean state between tests
  - [x]3.4: Test `handleServerMessage` with `session_state` event — verify `gameState` is set
  - [x]3.5: Test `handleServerMessage` with `turn_update` event — verify log entry appended with correct `[agent]: content` format
  - [x]3.6: Test `turn_update` with agent `"SHEET"` — verify prefix is uppercase `SHEET`
  - [x]3.7: Test `turn_update` when `gameState` is null — verify no crash (returns null)
  - [x]3.8: Test `autopilot_started` — sets `isAutopilotRunning` true, `isThinking` true
  - [x]3.9: Test `autopilot_stopped` — sets `isAutopilotRunning` false, `isThinking` false
  - [x]3.10: Test `paused` — sets `isPaused` true, `isThinking` false
  - [x]3.11: Test `resumed` — sets `isPaused` false
  - [x]3.12: Test `speed_changed` — sets `speed` to the event's speed value
  - [x]3.13: Test `drop_in` — sets `human_active` true, `controlled_character` to event's character
  - [x]3.14: Test `release_control` — clears human control, sets uiMode to 'watch'
  - [x]3.15: Test `awaiting_input` — sets `awaitingInput` true, `awaitingInputCharacter`
  - [x]3.16: Test `error` — clears `isThinking`
  - [x]3.17: Test unknown event type — no store changes
  - [x]3.18: Test `resetStores` — all stores return to initial values

- [x]**Task 4: Write connectionStore tests** (AC: 3)
  - [x]4.1: Create `frontend/src/lib/stores/connectionStore.test.ts`
  - [x]4.2: Test `connectionStatus` defaults to `'disconnected'`
  - [x]4.3: Test `wsSend` defaults to null and can be set/cleared
  - [x]4.4: Test `sendCommand` calls the stored send function with the command
  - [x]4.5: Test `sendCommand` calls `console.warn` when `wsSend` is null

- [x]**Task 5: Write uiStore tests** (AC: 4)
  - [x]5.1: Create `frontend/src/lib/stores/uiStore.test.ts`
  - [x]5.2: Test default values of `uiState`
  - [x]5.3: Test partial update via `uiState.update`
  - [x]5.4: Test each field can be set and read independently

- [x]**Task 6: Write narrativeStore tests** (AC: 5)
  - [x]6.1: Create `frontend/src/lib/stores/narrativeStore.test.ts`
  - [x]6.2: Test `narrativeMessages` returns `[]` when `gameState` is null
  - [x]6.3: Test `narrativeMessages` parses log entries when `gameState` has `ground_truth_log`
  - [x]6.4: Test `narrativeMessages` re-derives on `gameState` change
  - [x]6.5: Test `displayLimit` defaults to 50 and reflects configured value

- [x]**Task 7: Write narrative.ts utility tests** (AC: 6)
  - [x]7.1: Create `frontend/src/lib/narrative.test.ts`
  - [x]7.2: Test `parseLogEntry` — standard format `[agent]: content`
  - [x]7.3: Test `parseLogEntry` — no brackets (fallback to dm)
  - [x]7.4: Test `parseLogEntry` — empty agent `[]` (uses "unknown")
  - [x]7.5: Test `parseLogEntry` — strips duplicate agent prefix
  - [x]7.6: Test `getMessageType` — dm, SHEET, system, and PC agent cases
  - [x]7.7: Test `parseGroundTruthLog` — array to ParsedMessage[] conversion
  - [x]7.8: Test `resolveCharacterInfo` — direct key lookup
  - [x]7.9: Test `resolveCharacterInfo` — name search
  - [x]7.10: Test `resolveCharacterInfo` — fallback for unknown agent
  - [x]7.11: Test `sanitizeContent` — all HTML entities escaped
  - [x]7.12: Test `formatDiceNotation` — wraps dice rolls in spans
  - [x]7.13: Test `formatActionText` — wraps asterisk-enclosed text in spans
  - [x]7.14: Test `formatMessageContent` — full pipeline for each message type
  - [x]7.15: Test `formatMessageContent` — sanitization occurs before formatting (inject `<script>` in dice context)

- [x]**Task 8: Write format.ts utility tests** (AC: 7)
  - [x]8.1: Create `frontend/src/lib/format.test.ts`
  - [x]8.2: Test `toRomanNumeral` — standard conversions (1=I, 4=IV, 9=IX, 42=XLII, 2024=MMXXIV, 3999=MMMCMXCIX)
  - [x]8.3: Test `toRomanNumeral` — edge cases (0, 4000, -1, NaN, Infinity) return decimal strings
  - [x]8.4: Test `formatSessionDate` — valid ISO timestamp returns formatted date
  - [x]8.5: Test `formatSessionDate` — invalid/empty string returns "Unknown date"

- [x]**Task 9: Write api.ts utility tests** (AC: 8)
  - [x]9.1: Create `frontend/src/lib/api.test.ts`
  - [x]9.2: Set up `beforeEach` with `vi.stubGlobal('fetch', ...)` to mock the global `fetch`
  - [x]9.3: Create helper function for mock fetch responses (ok JSON, ok empty 204, error)
  - [x]9.4: Test `getSessions` — calls GET /api/sessions, returns parsed array
  - [x]9.5: Test `createSession` — calls POST with `{ name }` body
  - [x]9.6: Test `getSession` — URL-encodes the session ID in the path
  - [x]9.7: Test `deleteSession` — calls DELETE and does not parse body on 204
  - [x]9.8: Test `ApiError` — thrown on non-ok response with parsed `detail` field
  - [x]9.9: Test `ApiError` — falls back to raw text body when JSON parse fails
  - [x]9.10: Test `getForks` — calls correct fork endpoint
  - [x]9.11: Test `createFork` — sends POST with `{ name }` body
  - [x]9.12: Test `deleteFork` — handles 204 without error
  - [x]9.13: Test `getCharacterSheet` — URL-encodes character name in path

- [x]**Task 10: Write ws.ts utility tests** (AC: 9)
  - [x]10.1: Create `frontend/src/lib/ws.test.ts`
  - [x]10.2: Create a mock WebSocket class:
    ```typescript
    class MockWebSocket {
      static OPEN = 1;
      static CONNECTING = 0;
      static CLOSED = 3;
      readyState = MockWebSocket.OPEN;
      onopen: (() => void) | null = null;
      onclose: ((e: { code: number; reason: string }) => void) | null = null;
      onmessage: ((e: { data: string }) => void) | null = null;
      onerror: ((e: unknown) => void) | null = null;
      send = vi.fn();
      close = vi.fn();
    }
    ```
  - [x]10.3: Stub `window.WebSocket` with the mock before each test
  - [x]10.4: Test `connect()` creates a WebSocket with correct URL (`ws://localhost/ws/game/{sessionId}`)
  - [x]10.5: Test `send()` calls `ws.send()` with JSON-serialized command
  - [x]10.6: Test `send()` logs error when not connected (readyState !== OPEN)
  - [x]10.7: Test `disconnect()` calls `ws.close(1000, ...)` and sets `isConnected` false
  - [x]10.8: Test `onMessage` callback receives parsed events when ws.onmessage fires
  - [x]10.9: Test `onConnect` callback fires when ws.onopen triggers
  - [x]10.10: Test auto-pong: when a `{ type: 'ping' }` message arrives, `ws.send` is called with `{ type: 'pong' }`

- [x]**Task 11: Write NarrativeMessage component tests** (AC: 10)
  - [x]11.1: Create `frontend/src/lib/components/NarrativeMessage.test.ts`
  - [x]11.2: Import `render` from `@testing-library/svelte` and `NarrativeMessage`
  - [x]11.3: Test DM narration — container has class `dm-message`
  - [x]11.4: Test PC dialogue — container has class `pc-message`, attribution text shows character info
  - [x]11.5: Test sheet update — container has class `sheet-notification`
  - [x]11.6: Test system message — container has class `system-message`
  - [x]11.7: Test `isCurrent` prop adds `current-turn` class

- [x]**Task 12: Write SessionCard component tests** (AC: 11)
  - [x]12.1: Create `frontend/src/lib/components/SessionCard.test.ts`
  - [x]12.2: Mock `$app/navigation` (`goto`) as Vitest module mock
  - [x]12.3: Test session title renders as Roman numeral (e.g., session_number 7 renders "Session VII")
  - [x]12.4: Test session name renders (or "Unnamed Adventure" fallback when name is empty)
  - [x]12.5: Test delete button calls `onDelete` callback with session ID
  - [x]12.6: Test `.deleting` class is applied when `deleting` prop is true

- [x]**Task 13: Write ConfirmDialog component tests** (AC: 12)
  - [x]13.1: Create `frontend/src/lib/components/ConfirmDialog.test.ts`
  - [x]13.2: Test dialog is not rendered when `open` is false — `queryByRole('dialog')` returns null
  - [x]13.3: Test dialog renders title, message, and buttons when `open` is true
  - [x]13.4: Test confirm button uses `confirmLabel` text
  - [x]13.5: Test cancel button calls `onCancel`
  - [x]13.6: Test confirm button calls `onConfirm`
  - [x]13.7: Test error message renders when `error` prop is provided

- [x]**Task 14: Write CharacterCard component tests** (AC: 13)
  - [x]14.1: Create `frontend/src/lib/components/CharacterCard.test.ts`
  - [x]14.2: Mock `$lib/stores` exports to provide test values for `gameState`, `isThinking`, `connectionStatus`, `sendCommand`, `uiState`
  - [x]14.3: Test card renders character name and class
  - [x]14.4: Test status badge shows "You" when `isControlled` is true
  - [x]14.5: Test status badge shows "AI" when not controlled and not generating
  - [x]14.6: Test HP bar renders when `hp` prop is provided

- [x]**Task 15: Verification and final checks** (AC: 14, 15)
  - [x]15.1: Run `cd frontend && npm run test` — all tests pass, 50+ total
  - [x]15.2: Run `cd frontend && npm run check` — TypeScript check passes
  - [x]15.3: Run `cd frontend && npm run build` — production build succeeds
  - [x]15.4: Verify no Python files are modified: `git diff --name-only | grep ".py$"` returns empty
  - [x]15.5: Verify test run completes in under 30 seconds
  - [x]15.6: Update `sprint-status.yaml` with story completion

---

## Dev Notes

### Test Framework Rationale

**Vitest** is the standard test runner for SvelteKit projects because it shares the same Vite-based transform pipeline, meaning TypeScript, Svelte preprocessing, and `$lib` path aliases work out of the box. Jest would require separate configuration for each of these.

**@testing-library/svelte** provides the `render()` function for mounting Svelte 5 components in a test DOM, plus query utilities (`getByRole`, `getByText`, etc.) that encourage accessible markup testing. The library is framework-agnostic in API shape, matching the @testing-library philosophy.

**jsdom** is the test environment recommended for Vitest when testing browser code. It simulates enough of the DOM API for component tests. `happy-dom` is a lighter-weight alternative if jsdom is too slow, but jsdom has broader compatibility.

### SvelteKit + Vitest Configuration

The key insight is that Vitest should use the **same Vite config** as SvelteKit to get path alias resolution (`$lib`, `$app`, etc.) working in tests. The `sveltekit()` Vite plugin handles this. There are two approaches:

**Option A — Extend vite.config.ts** (simpler):
```typescript
// vite.config.ts
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [sveltekit()],
  test: {
    include: ['src/**/*.test.ts'],
    environment: 'jsdom',
    globals: true,
    setupFiles: ['src/tests/setup.ts'],
  },
  server: {
    proxy: { /* ... existing proxy config ... */ },
  },
});
```

**Option B — Separate vitest.config.ts** (more isolated):
```typescript
// vitest.config.ts
import { defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      include: ['src/**/*.test.ts'],
      environment: 'jsdom',
      globals: true,
      setupFiles: ['src/tests/setup.ts'],
    },
  }),
);
```

Option A is recommended for simplicity unless the proxy config causes test issues.

### Mocking Strategy

#### Global `fetch` (api.ts tests)
Use Vitest's `vi.stubGlobal` to mock `fetch`:
```typescript
const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

// Helper to create mock responses
function mockJsonResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as Response);
}

function mock204Response() {
  return Promise.resolve({
    ok: true,
    status: 204,
    statusText: 'No Content',
  } as Response);
}
```

#### WebSocket (ws.ts tests)
Create a mock WebSocket class and stub `window.WebSocket`:
```typescript
class MockWebSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static CLOSING = 2;
  static CLOSED = 3;
  readyState = MockWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  send = vi.fn();
  close = vi.fn();
  url: string;
  constructor(url: string) {
    this.url = url;
    // Simulate async open
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 0);
  }
}
vi.stubGlobal('WebSocket', MockWebSocket);
```

#### Svelte Stores (component tests)
For component tests that depend on stores (e.g., `CharacterCard` imports from `$lib/stores`), use `vi.mock`:
```typescript
import { writable } from 'svelte/store';

vi.mock('$lib/stores', () => ({
  gameState: writable(null),
  isThinking: writable(false),
  connectionStatus: writable('connected'),
  sendCommand: vi.fn(),
  uiState: writable({
    sidebarOpen: true,
    selectedCharacter: null,
    uiMode: 'watch',
    autoScroll: true,
    settingsOpen: false,
    characterSheetName: null,
    comparisonForkId: null,
  }),
}));
```

#### SvelteKit Modules (component tests)
Mock `$app/navigation` for components that use `goto`:
```typescript
vi.mock('$app/navigation', () => ({
  goto: vi.fn(),
}));
```

### Svelte 5 Testing Considerations

Svelte 5 uses runes (`$state`, `$derived`, `$effect`, `$props`) which compile differently than Svelte 4 reactivity. Key points:

1. **@testing-library/svelte v5+** is required for Svelte 5 component testing. Earlier versions do not support the runes compilation output.
2. **`$props()` components** require passing props via the `render()` function's second argument:
   ```typescript
   render(NarrativeMessage, {
     props: {
       message: { agent: 'dm', content: 'Test', messageType: 'dm_narration', index: 0 },
       isCurrent: false,
     },
   });
   ```
3. **Derived state** in stores tests may require `tick()` or `await` for reactivity to propagate:
   ```typescript
   import { tick } from 'svelte';
   gameState.set(mockState);
   await tick();
   expect(get(narrativeMessages)).toHaveLength(3);
   ```

### File Structure Created by This Story

```
frontend/
├── vitest.config.ts                          # NEW (or vite.config.ts modified)
├── package.json                              # MODIFIED: add test deps + scripts
├── src/
│   ├── tests/
│   │   └── setup.ts                          # NEW: global test setup
│   ├── lib/
│   │   ├── narrative.test.ts                 # NEW: 14+ tests
│   │   ├── format.test.ts                    # NEW: 8+ tests
│   │   ├── api.test.ts                       # NEW: 10+ tests
│   │   ├── ws.test.ts                        # NEW: 6+ tests
│   │   ├── stores/
│   │   │   ├── gameStore.test.ts             # NEW: 12+ tests
│   │   │   ├── connectionStore.test.ts       # NEW: 4+ tests
│   │   │   ├── uiStore.test.ts              # NEW: 3+ tests
│   │   │   └── narrativeStore.test.ts        # NEW: 4+ tests
│   │   └── components/
│   │       ├── NarrativeMessage.test.ts      # NEW: 5+ tests
│   │       ├── SessionCard.test.ts           # NEW: 4+ tests
│   │       ├── ConfirmDialog.test.ts         # NEW: 5+ tests
│   │       └── CharacterCard.test.ts         # NEW: 4+ tests
```

### Test Data Fixtures

Create reusable test fixtures for commonly needed data structures:

```typescript
// Example: minimal GameState for store tests
export function makeGameState(overrides: Partial<GameState> = {}): GameState {
  return {
    ground_truth_log: [],
    turn_queue: ['dm', 'fighter', 'rogue'],
    current_turn: 'dm',
    agent_memories: {},
    game_config: {
      combat_mode: 'Narrative',
      summarizer_provider: 'gemini',
      summarizer_model: 'gemini-2.0-flash',
      extractor_provider: 'gemini',
      extractor_model: 'gemini-2.0-flash',
      party_size: 4,
      narrative_display_limit: 50,
      max_combat_rounds: 10,
    },
    human_active: false,
    controlled_character: null,
    turn_number: 0,
    session_id: 'test-session-001',
    ...overrides,
  };
}

// Example: session fixture
export function makeSession(overrides: Partial<Session> = {}): Session {
  return {
    session_id: 'test-001',
    session_number: 1,
    name: 'Test Adventure',
    created_at: '2026-02-01T12:00:00Z',
    updated_at: '2026-02-01T14:00:00Z',
    character_names: ['Shadowmere', 'Thorin', 'Elara'],
    turn_count: 42,
    ...overrides,
  };
}
```

Consider creating a `frontend/src/tests/fixtures.ts` file for these if multiple test files need them.

### Common Pitfalls to Avoid

1. **Do NOT install Jest or jest-environment-jsdom.** This project uses Vitest exclusively. Jest and Vitest are incompatible when installed together.
2. **Do NOT use `@testing-library/svelte` versions below 5.0.** Svelte 5 runes require the v5 release of the testing library.
3. **Do NOT forget to reset stores between tests.** Svelte stores persist across tests within the same module. Use `beforeEach(() => resetStores())` in gameStore tests and manually reset other stores.
4. **Do NOT test implementation details of CSS.** Test for presence of CSS classes (`.dm-message`, `.pc-message`) but do not assert specific pixel values or computed styles since jsdom does not compute styles.
5. **Do NOT use `import { describe, it, expect } from 'vitest'` when `globals: true` is set.** Vitest injects these automatically; explicit imports cause duplicate declaration errors in some configurations.
6. **Do NOT attempt to test `$effect` side effects synchronously.** Effects run asynchronously. Use `await tick()` or `vi.advanceTimersByTime()` as needed.
7. **Do NOT modify `vite.config.ts` proxy settings.** The proxy config is for the dev server only and should not be removed or altered by test configuration.
8. **Do NOT mock the stores barrel export (`$lib/stores/index.ts`) when testing individual store files.** Import directly from the store file under test (e.g., `$lib/stores/gameStore`) to avoid circular mock issues.
9. **Do NOT forget to clean up `vi.stubGlobal` mocks.** Use `afterEach(() => vi.restoreAllMocks())` to prevent leaking between test files.
10. **Do NOT call `response.json()` in `deleteSession`/`deleteFork` tests.** These are 204 No Content responses — verify the test mocks return no body.

### Package Version Compatibility

As of Feb 2026, the following versions are known to work together:

| Package | Version | Notes |
|---------|---------|-------|
| `vitest` | `^3.x` or `^2.x` | Must match the `vite` major version (Vite 7 may need Vitest 3+) |
| `@testing-library/svelte` | `^5.x` | Required for Svelte 5 runes support |
| `@testing-library/jest-dom` | `^6.x` | Extended matchers (toBeInTheDocument, toHaveClass, etc.) |
| `jsdom` | `^25.x` or `^24.x` | Standard JSDOM — check Vitest compat |

If `vitest` version conflicts arise with `vite@7.3.1`, check the Vitest release notes for Vite 7 compatibility. The `@vitest/browser` package is NOT needed since we use jsdom, not real browser testing.

### Integration Tests (Optional / Future)

Playwright integration tests are out of scope for this story but could be added in a follow-up. The structure would be:

```
frontend/
├── e2e/
│   ├── session-create.spec.ts
│   ├── game-page.spec.ts
│   └── playwright.config.ts
```

These would test full user flows (create session, navigate to game, verify narrative renders) against a running backend. They are deferred because they require the full FastAPI backend + game engine to be running and seeded with test data.

### References

- [Source: frontend/src/lib/stores/gameStore.ts — Game state management, handleServerMessage, resetStores]
- [Source: frontend/src/lib/stores/connectionStore.ts — Connection state, sendCommand]
- [Source: frontend/src/lib/stores/uiStore.ts — UI state with UiState interface]
- [Source: frontend/src/lib/stores/narrativeStore.ts — Derived stores: narrativeMessages, displayLimit]
- [Source: frontend/src/lib/narrative.ts — Log parsing, formatting, sanitization pipeline]
- [Source: frontend/src/lib/format.ts — Roman numeral conversion, date formatting]
- [Source: frontend/src/lib/api.ts — REST API client with ApiError, fetch wrapper]
- [Source: frontend/src/lib/ws.ts — WebSocket connection factory with reconnect logic]
- [Source: frontend/src/lib/types.ts — All TypeScript interfaces for API, WS, game state]
- [Source: frontend/src/lib/components/NarrativeMessage.svelte — Message rendering by type]
- [Source: frontend/src/lib/components/SessionCard.svelte — Session card with Roman numeral, delete]
- [Source: frontend/src/lib/components/ConfirmDialog.svelte — Modal confirmation dialog]
- [Source: frontend/src/lib/components/CharacterCard.svelte — Character card with drop-in, HP bar, sheet button]
- [Source: frontend/src/lib/components/SettingsModal.svelte — Settings modal pattern reference]
- [Source: frontend/vite.config.ts — Current Vite config with SvelteKit plugin and proxy]
- [Source: frontend/svelte.config.js — SvelteKit config with static adapter]
- [Source: frontend/tsconfig.json — TypeScript strict mode, bundler resolution]
- [Source: frontend/package.json — Current devDependencies (Svelte 5, Vite 7, SvelteKit 2)]

---

## Dev Agent Record

**Status:** done
**Completed:** 2026-02-11

### Files Created
- `frontend/src/tests/setup.ts` — Global test setup (imports @testing-library/jest-dom/vitest matchers)
- `frontend/src/tests/fixtures.ts` — Reusable test fixtures (makeGameState, makeSession, makeGameConfig)
- `frontend/src/lib/stores/gameStore.test.ts` — 20 tests for gameStore (handleServerMessage, resetStores)
- `frontend/src/lib/stores/connectionStore.test.ts` — 4 tests for connectionStore (sendCommand, defaults)
- `frontend/src/lib/stores/uiStore.test.ts` — 3 tests for uiStore (defaults, partial update, independent fields)
- `frontend/src/lib/stores/narrativeStore.test.ts` — 5 tests for narrativeStore (derived messages, displayLimit)
- `frontend/src/lib/narrative.test.ts` — 28 tests for narrative utilities (parseLogEntry, getMessageType, parseGroundTruthLog, resolveCharacterInfo, sanitizeContent, formatDiceNotation, formatActionText, formatMessageContent)
- `frontend/src/lib/format.test.ts` — 14 tests for format utilities (toRomanNumeral, formatSessionDate)
- `frontend/src/lib/api.test.ts` — 11 tests for API client (getSessions, createSession, getSession, deleteSession, getForks, createFork, deleteFork, getCharacterSheet, ApiError handling)
- `frontend/src/lib/ws.test.ts` — 9 tests for WebSocket connection (connect, send, disconnect, callbacks, auto-pong)
- `frontend/src/lib/components/NarrativeMessage.test.ts` — 5 tests for NarrativeMessage component (CSS classes by message type, current-turn)
- `frontend/src/lib/components/SessionCard.test.ts` — 5 tests for SessionCard component (Roman numerals, name, delete, deleting class)
- `frontend/src/lib/components/ConfirmDialog.test.ts` — 6 tests for ConfirmDialog component (open/closed, buttons, callbacks, error display)
- `frontend/src/lib/components/CharacterCard.test.ts` — 5 tests for CharacterCard component (name/class, status badge, HP bar)

### Files Modified
- `frontend/vite.config.ts` — Added vitest/config import, svelteTesting() plugin, test configuration block
- `frontend/package.json` — Added devDependencies (vitest, @testing-library/svelte, @testing-library/jest-dom, jsdom) and test scripts (test, test:watch, test:coverage)

### Test Results
- **115 tests passing** across 12 test files
- **0 failures, 0 skipped**
- **Test run duration: ~11 seconds**
- `npm run check` passes (0 errors)
- `npm run build` succeeds
- No Python files modified

### Implementation Notes
- Used Option A approach: extended `vite.config.ts` with test config (simpler, avoids separate vitest.config.ts)
- Added `svelteTesting()` plugin from `@testing-library/svelte/vite` for automatic cleanup and Svelte 5 runes support
- Store tests import directly from individual store files (not barrel export) per pitfall #8
- Component tests use `vi.mock('$lib/stores', ...)` and `vi.mock('$app/navigation', ...)` for isolation
- WebSocket tests use a MockWebSocket class with manual readyState/callback control
- API tests use `vi.stubGlobal('fetch', mockFetch)` pattern with helpers for JSON, 204, and error responses
- `globals: true` was NOT set in vitest config; explicit vitest imports used instead (avoids ambiguity with @testing-library/jest-dom matchers)
- formatSessionDate test uses mid-day timestamps to avoid timezone boundary edge cases in jsdom
