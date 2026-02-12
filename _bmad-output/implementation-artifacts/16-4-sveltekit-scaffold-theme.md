# Story 16.4: SvelteKit Scaffold & Theme

Status: ready-for-dev

## Story

As a **developer building the SvelteKit frontend**,
I want **a fully scaffolded SvelteKit project with the campfire dark theme ported as CSS custom properties, layout shell, API/WebSocket client utilities, reactive Svelte stores, and basic routing**,
so that **subsequent frontend stories (16-5 through 16-12) have a stable foundation to build components on, and the visual identity is established from the first page load**.

## Acceptance Criteria (Given/When/Then)

### AC1: SvelteKit Project Scaffolded in `frontend/` Directory

**Given** the project root contains no `frontend/` directory
**When** the developer scaffolds the SvelteKit project
**Then** a `frontend/` directory exists with a valid SvelteKit 2.0+ project (Svelte 5, TypeScript, Vite)
**And** `frontend/package.json` lists `@sveltejs/kit`, `svelte`, `vite`, `typescript`, and `@sveltejs/adapter-static` as dependencies
**And** `npx sv create` skeleton template was used (no demo content, no library CSS)
**And** running `cd frontend && npm install && npm run dev` starts the dev server on `localhost:5173`

### AC2: Project Structure Follows Architecture Specification

**Given** the `frontend/src/` directory exists
**When** I examine the directory structure
**Then** it contains:
  - `frontend/src/routes/` (SvelteKit pages)
  - `frontend/src/routes/+layout.svelte` (root layout with sidebar + main area)
  - `frontend/src/routes/+page.svelte` (home page — session browser)
  - `frontend/src/routes/game/[sessionId]/+page.svelte` (game view)
  - `frontend/src/lib/` (shared library)
  - `frontend/src/lib/stores/` (Svelte stores)
  - `frontend/src/lib/components/` (reusable components)
  - `frontend/src/lib/api.ts` (REST API client)
  - `frontend/src/lib/ws.ts` (WebSocket client)
  - `frontend/src/lib/types.ts` (TypeScript type definitions)
  - `frontend/src/app.css` (global campfire theme CSS custom properties)
  - `frontend/src/app.html` (HTML template with font imports)

### AC3: Global CSS Custom Properties Define the Campfire Theme

**Given** the `frontend/src/app.css` file exists
**When** I inspect its contents
**Then** it defines all design tokens as CSS custom properties on `:root`:

**Background Colors:**
  - `--bg-primary: #1A1612` (deep warm black — main canvas)
  - `--bg-secondary: #2D2520` (warm gray-brown — elevated surfaces)
  - `--bg-message: #3D3530` (message bubble background)

**Text Colors:**
  - `--text-primary: #F5E6D3` (warm off-white)
  - `--text-secondary: #B8A896` (muted warm gray)

**Accent:**
  - `--accent-warm: #E8A849` (amber highlight)
  - `--accent-warm-hover: #D49A3D` (amber hover state)

**Character Identity Colors:**
  - `--color-dm: #D4A574` (DM/Narrator — warm gold)
  - `--color-fighter: #C45C4A` (Fighter — bold red)
  - `--color-rogue: #6B8E6B` (Rogue — forest green)
  - `--color-wizard: #7B68B8` (Wizard — mystic purple)
  - `--color-cleric: #4A90A4` (Cleric — calm blue)

**Semantic Colors:**
  - `--color-success: #6B8E6B`
  - `--color-warning: #E8A849`
  - `--color-error: #C45C4A`
  - `--color-info: #4A90A4`

**Font Stack:**
  - `--font-narrative: 'Lora', Georgia, serif`
  - `--font-ui: 'Inter', system-ui, sans-serif`
  - `--font-mono: 'JetBrains Mono', monospace`

**Font Sizes:**
  - `--text-dm: 18px` (DM narration)
  - `--text-pc: 17px` (PC dialogue)
  - `--text-name: 14px` (character names, 600 weight)
  - `--text-ui: 14px` (UI controls)
  - `--text-system: 13px` (system text)

**Spacing (8px base grid):**
  - `--space-xs: 4px`
  - `--space-sm: 8px`
  - `--space-md: 16px`
  - `--space-lg: 24px`
  - `--space-xl: 32px`
  - `--space-2xl: 48px`

**Layout:**
  - `--sidebar-width: 240px`
  - `--max-content-width: 800px`
  - `--border-radius-sm: 4px`
  - `--border-radius-md: 8px`
  - `--border-radius-lg: 16px`

**Transitions:**
  - `--transition-fast: 0.15s ease`
  - `--transition-normal: 0.2s ease-in-out`

**And** the file applies base body/html styles: dark background, primary text color, UI font family, `box-sizing: border-box`
**And** the file includes custom scrollbar styles matching the dark theme
**And** the file imports Google Fonts (Lora, Inter, JetBrains Mono) via `@import url(...)`

### AC4: Root Layout Provides Sidebar + Main Content Structure

**Given** the `frontend/src/routes/+layout.svelte` file exists
**When** the application loads in the browser
**Then** the page renders a CSS Grid layout with two columns: `240px` sidebar + `1fr` main content area
**And** the sidebar has `--bg-secondary` background and spans the full viewport height
**And** the main content area has `--bg-primary` background
**And** the sidebar is scrollable if content overflows
**And** the main content area is scrollable independently
**And** the layout imports `app.css` globally via the `+layout.svelte` script

### AC5: API Client Utility Handles REST Calls to FastAPI Backend

**Given** the `frontend/src/lib/api.ts` file exists
**When** I import `api` from `$lib/api`
**Then** it exports functions for each REST endpoint:
  - `getSessions(): Promise<Session[]>` — `GET /api/sessions`
  - `createSession(name?: string): Promise<SessionCreateResponse>` — `POST /api/sessions`
  - `getSession(sessionId: string): Promise<Session>` — `GET /api/sessions/{id}`
  - `getSessionConfig(sessionId: string): Promise<GameConfig>` — `GET /api/sessions/{id}/config`
  - `updateSessionConfig(sessionId: string, config: Partial<GameConfig>): Promise<GameConfig>` — `PUT /api/sessions/{id}/config`
  - `getCharacters(): Promise<Character[]>` — `GET /api/characters`
  - `getCharacter(name: string): Promise<CharacterDetail>` — `GET /api/characters/{name}`

**And** all functions use `fetch()` with a configurable `BASE_URL` (defaulting to `''` so the Vite proxy handles routing)
**And** all functions handle HTTP errors by throwing typed errors with status codes and messages
**And** request/response bodies are JSON with proper `Content-Type` headers

### AC6: WebSocket Client Utility Handles Real-Time Connection

**Given** the `frontend/src/lib/ws.ts` file exists
**When** I import `createGameConnection` from `$lib/ws`
**Then** it exports a function `createGameConnection(sessionId: string)` that returns a connection object with:
  - `connect(): void` — opens WebSocket to `ws://localhost:8000/ws/game/{sessionId}` (or via Vite proxy)
  - `disconnect(): void` — closes WebSocket gracefully
  - `send(command: object): void` — sends a JSON command message
  - `onMessage(callback: (event: WsServerEvent) => void): void` — registers a message handler
  - `onConnect(callback: () => void): void` — registers a connect handler
  - `onDisconnect(callback: (reason: string) => void): void` — registers a disconnect handler
  - `isConnected: boolean` — readonly connection status

**And** the client includes auto-reconnect logic with exponential backoff (initial 1s, max 30s, max 5 attempts)
**And** the client responds to server `{"type": "ping"}` with `{"type": "pong"}` for application-level keepalive
**And** the client logs connection events (connect, disconnect, reconnect attempts) to the browser console

### AC7: Svelte Stores Provide Reactive State Management

**Given** the `frontend/src/lib/stores/` directory contains store files
**When** I import stores from `$lib/stores`
**Then** the following stores are available:

**`gameStore.ts`:**
  - `gameState: Writable<GameState | null>` — current game state, updated from WebSocket `session_state` and `turn_update` events
  - `isAutopilotRunning: Writable<boolean>` — whether autopilot is active
  - `isPaused: Writable<boolean>` — whether the game is paused
  - `speed: Writable<string>` — current game speed (`"slow"`, `"normal"`, `"fast"`)

**`uiStore.ts`:**
  - `uiState: Writable<UiState>` — client-side UI state:
    - `sidebarOpen: boolean` (default `true`)
    - `selectedCharacter: string | null` (default `null`)
    - `uiMode: 'watch' | 'play'` (default `'watch'`)
    - `autoScroll: boolean` (default `true`)

**`connectionStore.ts`:**
  - `connectionStatus: Writable<'disconnected' | 'connecting' | 'connected' | 'reconnecting'>` — WebSocket connection state
  - `lastError: Writable<string | null>` — last error message from server

**And** all stores use Svelte's `writable()` from `svelte/store`
**And** stores are exported as named exports for tree-shaking

### AC8: TypeScript Types Mirror API Contract

**Given** the `frontend/src/lib/types.ts` file exists
**When** I inspect its contents
**Then** it defines TypeScript interfaces matching the API schemas from `api/schemas.py`:
  - `Session` (session_id, session_number, name, created_at, updated_at, character_names, turn_count)
  - `SessionCreateResponse` (session_id, session_number, name)
  - `GameConfig` (combat_mode, summarizer_provider, summarizer_model, etc.)
  - `Character` (name, character_class, personality, color, provider, model, source)
  - `CharacterDetail` (extends Character with token_limit)
  - `GameState` (ground_truth_log, turn_queue, current_turn, agent_memories, etc.)
  - `TurnEntry` (turn, agent, content)

**And** it defines WebSocket message types:
  - `WsServerEvent` — discriminated union of all server-to-client message types
  - `WsCommand` — discriminated union of all client-to-server command types
  - Individual event interfaces: `WsTurnUpdate`, `WsSessionState`, `WsError`, `WsAutopilotStarted`, `WsAutopilotStopped`, `WsDropIn`, `WsReleaseControl`, `WsAwaitingInput`, `WsNudgeReceived`, `WsSpeedChanged`, `WsPaused`, `WsResumed`

### AC9: Basic Routing with Placeholder Pages

**Given** the SvelteKit application is running
**When** I navigate to `/`
**Then** the home page renders with the campfire theme applied (dark background, warm text)
**And** a placeholder heading says "autodungeon" in the `--color-dm` gold color using `--font-narrative`
**And** a placeholder text says "Session browser coming in Story 16-7"

**Given** the SvelteKit application is running
**When** I navigate to `/game/test-session`
**Then** the game page renders with the campfire theme applied
**And** a placeholder heading says "Game: test-session"
**And** a placeholder text says "Narrative panel coming in Story 16-5"
**And** the `sessionId` parameter is extracted from the URL

### AC10: Vite Proxy Routes API and WebSocket to FastAPI Backend

**Given** the `frontend/vite.config.ts` file exists
**When** I inspect its configuration
**Then** it includes a proxy configuration for the dev server:
  - `/api` proxied to `http://localhost:8000`
  - `/ws` proxied to `http://localhost:8000` with WebSocket upgrade support (`ws: true`)

**And** running `npm run dev` starts the SvelteKit dev server on port 5173
**And** API requests from the frontend to `/api/sessions` are proxied to `http://localhost:8000/api/sessions`
**And** WebSocket connections to `/ws/game/{id}` are proxied to `ws://localhost:8000/ws/game/{id}`

### AC11: Static Adapter Configured for Production Build

**Given** the `frontend/svelte.config.js` file exists
**When** I inspect its configuration
**Then** it uses `@sveltejs/adapter-static` for production builds
**And** `prerender` is configured with `fallback: 'index.html'` for SPA behavior
**And** running `npm run build` produces a `frontend/build/` directory with static files
**And** the built files can be served by any static file server (or by FastAPI in production)

### AC12: HTML Template Includes Font Imports and Meta Tags

**Given** the `frontend/src/app.html` file exists
**When** I inspect its contents
**Then** it includes `<link>` tags to preconnect and load Google Fonts (Lora, Inter, JetBrains Mono)
**And** it sets `<meta name="viewport" content="width=device-width, initial-scale=1">` for responsive base
**And** it sets `<title>autodungeon</title>`
**And** it sets `<meta name="color-scheme" content="dark">` for dark mode preference
**And** the `<body>` tag has no default styles that conflict with the campfire theme

## Tasks / Subtasks

- [ ] **Task 1: Scaffold SvelteKit project** (AC: 1, 2)
  - [ ] 1.1: Run `npx sv create frontend` — select: skeleton project, TypeScript, no additional options
  - [ ] 1.2: `cd frontend && npm install`
  - [ ] 1.3: Install additional dependencies: `npm install -D @sveltejs/adapter-static`
  - [ ] 1.4: Verify `npm run dev` starts successfully on `localhost:5173`
  - [ ] 1.5: Create directory structure:
    - `frontend/src/lib/stores/`
    - `frontend/src/lib/components/`
    - `frontend/src/routes/game/[sessionId]/`
  - [ ] 1.6: Add `frontend/node_modules/` and `frontend/build/` to project `.gitignore` if not already covered

- [ ] **Task 2: Configure Vite proxy and SvelteKit adapter** (AC: 10, 11)
  - [ ] 2.1: Update `frontend/vite.config.ts` to add proxy configuration:
    ```typescript
    import { sveltekit } from '@sveltejs/kit/vite';
    import { defineConfig } from 'vite';

    export default defineConfig({
      plugins: [sveltekit()],
      server: {
        proxy: {
          '/api': {
            target: 'http://localhost:8000',
            changeOrigin: true,
          },
          '/ws': {
            target: 'http://localhost:8000',
            ws: true,
          },
        },
      },
    });
    ```
  - [ ] 2.2: Update `frontend/svelte.config.js` to use `adapter-static`:
    ```javascript
    import adapter from '@sveltejs/adapter-static';
    import { vitePreprocess } from '@sveltejs/kit/vite';

    /** @type {import('@sveltejs/kit').Config} */
    const config = {
      preprocess: vitePreprocess(),
      kit: {
        adapter: adapter({
          fallback: 'index.html',
        }),
      },
    };

    export default config;
    ```
  - [ ] 2.3: Verify `npm run build` produces `frontend/build/` with `index.html`

- [ ] **Task 3: Create global CSS theme (`app.css`)** (AC: 3)
  - [ ] 3.1: Create `frontend/src/app.css` with all CSS custom properties from AC3 (ported from `styles/theme.css`)
  - [ ] 3.2: Include Google Fonts `@import` for Lora (400, 600, 400 italic), Inter (400, 500, 600), JetBrains Mono (400, 500)
  - [ ] 3.3: Add base styles:
    ```css
    *,
    *::before,
    *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html {
      color-scheme: dark;
    }

    body {
      background-color: var(--bg-primary);
      color: var(--text-primary);
      font-family: var(--font-ui);
      font-size: var(--text-ui);
      line-height: 1.4;
      min-height: 100vh;
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
    }
    ```
  - [ ] 3.4: Add custom scrollbar styles (matching existing theme.css dark scrollbar styling):
    ```css
    ::-webkit-scrollbar {
      width: 8px;
      height: 8px;
    }
    ::-webkit-scrollbar-track {
      background: var(--bg-secondary);
      border-radius: var(--border-radius-sm);
    }
    ::-webkit-scrollbar-thumb {
      background: var(--text-secondary);
      border-radius: var(--border-radius-sm);
    }
    ::-webkit-scrollbar-thumb:hover {
      background: var(--accent-warm);
    }
    * {
      scrollbar-width: thin;
      scrollbar-color: var(--text-secondary) var(--bg-secondary);
    }
    ```
  - [ ] 3.5: Add utility classes for common patterns:
    ```css
    /* Focus states */
    :focus-visible {
      outline: 2px solid var(--accent-warm);
      outline-offset: 2px;
    }

    /* Link base styles */
    a {
      color: var(--accent-warm);
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    ```

- [ ] **Task 4: Update HTML template (`app.html`)** (AC: 12)
  - [ ] 4.1: Update `frontend/src/app.html`:
    ```html
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="color-scheme" content="dark" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&family=Lora:ital,wght@0,400;0,600;1,400&display=swap"
          rel="stylesheet"
        />
        <title>autodungeon</title>
        <link rel="icon" href="%sveltekit.assets%/favicon.png" />
        %sveltekit.head%
      </head>
      <body data-sveltekit-preload-data="hover">
        <div style="display: contents">%sveltekit.body%</div>
      </body>
    </html>
    ```
  - [ ] 4.2: Remove the `@import url(...)` from `app.css` since fonts are loaded via `<link>` in `app.html` (faster, non-render-blocking with preconnect)

- [ ] **Task 5: Create root layout (`+layout.svelte`)** (AC: 4)
  - [ ] 5.1: Create `frontend/src/routes/+layout.svelte`:
    ```svelte
    <script lang="ts">
      import '../app.css';
      import type { Snippet } from 'svelte';

      let { children }: { children: Snippet } = $props();
    </script>

    <div class="app-layout">
      <aside class="sidebar">
        <div class="sidebar-header">
          <h1 class="app-title">autodungeon</h1>
        </div>
        <nav class="sidebar-nav">
          <p class="sidebar-placeholder">Party panel (Story 16-6)</p>
        </nav>
      </aside>
      <main class="main-content">
        {@render children()}
      </main>
    </div>

    <style>
      .app-layout {
        display: grid;
        grid-template-columns: var(--sidebar-width) 1fr;
        min-height: 100vh;
      }

      .sidebar {
        background-color: var(--bg-secondary);
        padding: var(--space-md);
        overflow-y: auto;
        height: 100vh;
        position: sticky;
        top: 0;
      }

      .sidebar-header {
        margin-bottom: var(--space-lg);
      }

      .app-title {
        font-family: var(--font-narrative);
        font-size: 20px;
        font-weight: 600;
        color: var(--color-dm);
        letter-spacing: 0.05em;
      }

      .sidebar-nav {
        display: flex;
        flex-direction: column;
        gap: var(--space-sm);
      }

      .sidebar-placeholder {
        color: var(--text-secondary);
        font-size: var(--text-system);
        font-style: italic;
      }

      .main-content {
        background-color: var(--bg-primary);
        padding: var(--space-lg);
        overflow-y: auto;
        height: 100vh;
      }
    </style>
    ```

- [ ] **Task 6: Create TypeScript type definitions (`types.ts`)** (AC: 8)
  - [ ] 6.1: Create `frontend/src/lib/types.ts` with interfaces matching `api/schemas.py`:
    ```typescript
    // === REST API Types ===

    export interface Session {
      session_id: string;
      session_number: number;
      name: string;
      created_at: string;
      updated_at: string;
      character_names: string[];
      turn_count: number;
    }

    export interface SessionCreateResponse {
      session_id: string;
      session_number: number;
      name: string;
    }

    export interface GameConfig {
      combat_mode: 'Narrative' | 'Tactical';
      summarizer_provider: string;
      summarizer_model: string;
      extractor_provider: string;
      extractor_model: string;
      party_size: number;
      narrative_display_limit: number;
      max_combat_rounds: number;
    }

    export interface Character {
      name: string;
      character_class: string;
      personality: string;
      color: string;
      provider: string;
      model: string;
      source: 'preset' | 'library';
    }

    export interface CharacterDetail extends Character {
      token_limit: number;
    }

    export interface AgentMemory {
      long_term_summary: string;
      short_term_buffer: string[];
      token_limit: number;
    }

    export interface TurnEntry {
      turn: number;
      agent: string;
      content: string;
    }

    export interface GameState {
      ground_truth_log: string[];
      turn_queue: string[];
      current_turn: string;
      agent_memories: Record<string, AgentMemory>;
      game_config: GameConfig;
      human_active: boolean;
      controlled_character: string | null;
      turn_number: number;
      session_id: string;
    }

    // === WebSocket Server-to-Client Events ===

    export interface WsTurnUpdate {
      type: 'turn_update';
      turn: number;
      agent: string;
      content: string;
      state: Record<string, unknown>;
    }

    export interface WsSessionState {
      type: 'session_state';
      state: Record<string, unknown>;
    }

    export interface WsError {
      type: 'error';
      message: string;
      recoverable: boolean;
    }

    export interface WsAutopilotStarted {
      type: 'autopilot_started';
    }

    export interface WsAutopilotStopped {
      type: 'autopilot_stopped';
      reason: string;
    }

    export interface WsDropIn {
      type: 'drop_in';
      character: string;
    }

    export interface WsReleaseControl {
      type: 'release_control';
    }

    export interface WsAwaitingInput {
      type: 'awaiting_input';
      character: string;
    }

    export interface WsNudgeReceived {
      type: 'nudge_received';
    }

    export interface WsSpeedChanged {
      type: 'speed_changed';
      speed: string;
    }

    export interface WsPaused {
      type: 'paused';
    }

    export interface WsResumed {
      type: 'resumed';
    }

    export interface WsPing {
      type: 'ping';
    }

    export type WsServerEvent =
      | WsTurnUpdate
      | WsSessionState
      | WsError
      | WsAutopilotStarted
      | WsAutopilotStopped
      | WsDropIn
      | WsReleaseControl
      | WsAwaitingInput
      | WsNudgeReceived
      | WsSpeedChanged
      | WsPaused
      | WsResumed
      | WsPing;

    // === WebSocket Client-to-Server Commands ===

    export interface WsCmdStartAutopilot {
      type: 'start_autopilot';
      speed?: string;
    }

    export interface WsCmdStopAutopilot {
      type: 'stop_autopilot';
    }

    export interface WsCmdNextTurn {
      type: 'next_turn';
    }

    export interface WsCmdDropIn {
      type: 'drop_in';
      character: string;
    }

    export interface WsCmdReleaseControl {
      type: 'release_control';
    }

    export interface WsCmdSubmitAction {
      type: 'submit_action';
      content: string;
    }

    export interface WsCmdNudge {
      type: 'nudge';
      content: string;
    }

    export interface WsCmdSetSpeed {
      type: 'set_speed';
      speed: string;
    }

    export interface WsCmdPause {
      type: 'pause';
    }

    export interface WsCmdResume {
      type: 'resume';
    }

    export interface WsCmdRetry {
      type: 'retry';
    }

    export type WsCommand =
      | WsCmdStartAutopilot
      | WsCmdStopAutopilot
      | WsCmdNextTurn
      | WsCmdDropIn
      | WsCmdReleaseControl
      | WsCmdSubmitAction
      | WsCmdNudge
      | WsCmdSetSpeed
      | WsCmdPause
      | WsCmdResume
      | WsCmdRetry;
    ```

- [ ] **Task 7: Create API client utility (`api.ts`)** (AC: 5)
  - [ ] 7.1: Create `frontend/src/lib/api.ts`:
    ```typescript
    import type {
      Session,
      SessionCreateResponse,
      GameConfig,
      Character,
      CharacterDetail,
    } from './types';

    const BASE_URL = '';  // Empty — Vite proxy handles /api routing

    export class ApiError extends Error {
      constructor(
        public status: number,
        public statusText: string,
        message: string,
      ) {
        super(message);
        this.name = 'ApiError';
      }
    }

    async function request<T>(path: string, options?: RequestInit): Promise<T> {
      const response = await fetch(`${BASE_URL}${path}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const body = await response.text();
        let message: string;
        try {
          const json = JSON.parse(body);
          message = json.detail || json.message || body;
        } catch {
          message = body || response.statusText;
        }
        throw new ApiError(response.status, response.statusText, message);
      }

      return response.json();
    }

    // Session endpoints
    export async function getSessions(): Promise<Session[]> {
      return request<Session[]>('/api/sessions');
    }

    export async function createSession(name?: string): Promise<SessionCreateResponse> {
      return request<SessionCreateResponse>('/api/sessions', {
        method: 'POST',
        body: JSON.stringify({ name: name ?? '' }),
      });
    }

    export async function getSession(sessionId: string): Promise<Session> {
      return request<Session>(`/api/sessions/${sessionId}`);
    }

    export async function getSessionConfig(sessionId: string): Promise<GameConfig> {
      return request<GameConfig>(`/api/sessions/${sessionId}/config`);
    }

    export async function updateSessionConfig(
      sessionId: string,
      config: Partial<GameConfig>,
    ): Promise<GameConfig> {
      return request<GameConfig>(`/api/sessions/${sessionId}/config`, {
        method: 'PUT',
        body: JSON.stringify(config),
      });
    }

    // Character endpoints
    export async function getCharacters(): Promise<Character[]> {
      return request<Character[]>('/api/characters');
    }

    export async function getCharacter(name: string): Promise<CharacterDetail> {
      return request<CharacterDetail>(`/api/characters/${name}`);
    }
    ```

- [ ] **Task 8: Create WebSocket client utility (`ws.ts`)** (AC: 6)
  - [ ] 8.1: Create `frontend/src/lib/ws.ts`:
    ```typescript
    import type { WsServerEvent, WsCommand } from './types';

    export interface GameConnection {
      connect(): void;
      disconnect(): void;
      send(command: WsCommand): void;
      onMessage(callback: (event: WsServerEvent) => void): void;
      onConnect(callback: () => void): void;
      onDisconnect(callback: (reason: string) => void): void;
      readonly isConnected: boolean;
    }

    interface ReconnectConfig {
      initialDelay: number;    // ms
      maxDelay: number;        // ms
      maxAttempts: number;
    }

    const DEFAULT_RECONNECT: ReconnectConfig = {
      initialDelay: 1000,
      maxDelay: 30000,
      maxAttempts: 5,
    };

    export function createGameConnection(
      sessionId: string,
      reconnectConfig: ReconnectConfig = DEFAULT_RECONNECT,
    ): GameConnection {
      let ws: WebSocket | null = null;
      let connected = false;
      let reconnectAttempts = 0;
      let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
      let intentionalClose = false;

      const messageCallbacks: Array<(event: WsServerEvent) => void> = [];
      const connectCallbacks: Array<() => void> = [];
      const disconnectCallbacks: Array<(reason: string) => void> = [];

      function getWsUrl(): string {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        return `${protocol}//${host}/ws/game/${sessionId}`;
      }

      function connect(): void {
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
          return;
        }

        intentionalClose = false;
        const url = getWsUrl();
        console.log(`[WS] Connecting to ${url}`);

        ws = new WebSocket(url);

        ws.onopen = () => {
          connected = true;
          reconnectAttempts = 0;
          console.log('[WS] Connected');
          connectCallbacks.forEach((cb) => cb());
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as WsServerEvent;

            // Respond to server pings with pong
            if (data.type === 'ping') {
              ws?.send(JSON.stringify({ type: 'pong' }));
              return;
            }

            messageCallbacks.forEach((cb) => cb(data));
          } catch (err) {
            console.error('[WS] Failed to parse message:', err);
          }
        };

        ws.onclose = (event) => {
          connected = false;
          const reason = event.reason || `Code ${event.code}`;
          console.log(`[WS] Disconnected: ${reason}`);
          disconnectCallbacks.forEach((cb) => cb(reason));

          if (!intentionalClose && reconnectAttempts < reconnectConfig.maxAttempts) {
            scheduleReconnect();
          }
        };

        ws.onerror = (error) => {
          console.error('[WS] Error:', error);
        };
      }

      function scheduleReconnect(): void {
        const delay = Math.min(
          reconnectConfig.initialDelay * Math.pow(2, reconnectAttempts),
          reconnectConfig.maxDelay,
        );
        reconnectAttempts++;
        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/${reconnectConfig.maxAttempts})`);
        reconnectTimeout = setTimeout(connect, delay);
      }

      function disconnect(): void {
        intentionalClose = true;
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout);
          reconnectTimeout = null;
        }
        if (ws) {
          ws.close(1000, 'Client disconnect');
          ws = null;
        }
        connected = false;
      }

      function send(command: WsCommand): void {
        if (!ws || ws.readyState !== WebSocket.OPEN) {
          console.error('[WS] Cannot send — not connected');
          return;
        }
        ws.send(JSON.stringify(command));
      }

      function onMessage(callback: (event: WsServerEvent) => void): void {
        messageCallbacks.push(callback);
      }

      function onConnect(callback: () => void): void {
        connectCallbacks.push(callback);
      }

      function onDisconnect(callback: (reason: string) => void): void {
        disconnectCallbacks.push(callback);
      }

      return {
        connect,
        disconnect,
        send,
        onMessage,
        onConnect,
        onDisconnect,
        get isConnected() {
          return connected;
        },
      };
    }
    ```

- [ ] **Task 9: Create Svelte stores** (AC: 7)
  - [ ] 9.1: Create `frontend/src/lib/stores/gameStore.ts`:
    ```typescript
    import { writable } from 'svelte/store';
    import type { GameState } from '$lib/types';

    export const gameState = writable<GameState | null>(null);
    export const isAutopilotRunning = writable<boolean>(false);
    export const isPaused = writable<boolean>(false);
    export const speed = writable<string>('normal');
    ```
  - [ ] 9.2: Create `frontend/src/lib/stores/uiStore.ts`:
    ```typescript
    import { writable } from 'svelte/store';

    export interface UiState {
      sidebarOpen: boolean;
      selectedCharacter: string | null;
      uiMode: 'watch' | 'play';
      autoScroll: boolean;
    }

    export const uiState = writable<UiState>({
      sidebarOpen: true,
      selectedCharacter: null,
      uiMode: 'watch',
      autoScroll: true,
    });
    ```
  - [ ] 9.3: Create `frontend/src/lib/stores/connectionStore.ts`:
    ```typescript
    import { writable } from 'svelte/store';

    export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

    export const connectionStatus = writable<ConnectionStatus>('disconnected');
    export const lastError = writable<string | null>(null);
    ```
  - [ ] 9.4: Create `frontend/src/lib/stores/index.ts` barrel export:
    ```typescript
    export { gameState, isAutopilotRunning, isPaused, speed } from './gameStore';
    export { uiState, type UiState } from './uiStore';
    export { connectionStatus, lastError, type ConnectionStatus } from './connectionStore';
    ```

- [ ] **Task 10: Create placeholder pages** (AC: 9)
  - [ ] 10.1: Create `frontend/src/routes/+page.svelte` (home page):
    ```svelte
    <script lang="ts">
      // Session browser — full implementation in Story 16-7
    </script>

    <div class="home-page">
      <h1 class="page-title">autodungeon</h1>
      <p class="page-subtitle">Session browser coming in Story 16-7</p>
    </div>

    <style>
      .home-page {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 60vh;
        text-align: center;
      }

      .page-title {
        font-family: var(--font-narrative);
        font-size: 48px;
        font-weight: 600;
        color: var(--color-dm);
        letter-spacing: 0.05em;
        margin-bottom: var(--space-md);
      }

      .page-subtitle {
        font-family: var(--font-ui);
        font-size: var(--text-ui);
        color: var(--text-secondary);
        font-style: italic;
      }
    </style>
    ```
  - [ ] 10.2: Create `frontend/src/routes/game/[sessionId]/+page.svelte` (game view):
    ```svelte
    <script lang="ts">
      import { page } from '$app/stores';

      // Game view — full implementation in Story 16-5
      const sessionId = $derived($page.params.sessionId);
    </script>

    <div class="game-page">
      <h1 class="page-title">Game: {sessionId}</h1>
      <p class="page-subtitle">Narrative panel coming in Story 16-5</p>
    </div>

    <style>
      .game-page {
        padding: var(--space-lg);
      }

      .page-title {
        font-family: var(--font-narrative);
        font-size: 24px;
        font-weight: 600;
        color: var(--color-dm);
        margin-bottom: var(--space-md);
      }

      .page-subtitle {
        font-family: var(--font-ui);
        font-size: var(--text-ui);
        color: var(--text-secondary);
        font-style: italic;
      }
    </style>
    ```

- [ ] **Task 11: Verify the frontend builds and runs** (AC: 1, 9, 10, 11)
  - [ ] 11.1: Run `cd frontend && npm run dev` — verify dev server starts, home page renders with campfire theme
  - [ ] 11.2: Navigate to `http://localhost:5173/` — verify sidebar + main layout renders correctly
  - [ ] 11.3: Navigate to `http://localhost:5173/game/test-session` — verify game page renders with sessionId
  - [ ] 11.4: Run `cd frontend && npm run build` — verify static build succeeds
  - [ ] 11.5: Run `cd frontend && npm run check` — verify TypeScript type checking passes (svelte-check)
  - [ ] 11.6: Verify fonts load correctly (Lora, Inter, JetBrains Mono visible in browser DevTools)
  - [ ] 11.7: Verify dark theme renders with correct colors (use browser DevTools to inspect CSS custom properties)

- [ ] **Task 12: Verify no regressions in Python backend** (AC: all)
  - [ ] 12.1: Run `python -m ruff check .` from project root — no new violations
  - [ ] 12.2: Run `python -m pytest` from project root — no regressions in existing ~4100 tests
  - [ ] 12.3: Verify `api/` backend still starts: `uvicorn api.main:app` — no import errors or startup failures

## Dev Notes

### Architecture Context

This story creates the **SvelteKit frontend foundation** that all subsequent frontend stories (16-5 through 16-12) build upon. It is the frontend counterpart to Story 16-1 (API Layer Foundation) — establishing the project scaffold, visual identity, utilities, and conventions that the rest of the frontend follows.

**Key Architecture Principle:** "Frontend sends commands; backend processes and streams updates. No shared state — all communication via explicit messages." The `api.ts` and `ws.ts` utilities created in this story are the sole bridges between frontend and backend.

**Key Architecture Principle:** "UI interactions send commands via WebSocket. Backend processes commands and streams updates. No coupling between UI rendering and game engine execution."

### SvelteKit Scaffold Approach

**Use `npx sv create` (NOT `npm create svelte@latest`):** The SvelteKit team renamed the scaffold tool. As of early 2026, `sv create` is the current command. Select:
- Template: **Skeleton project** (no demo app, no library)
- Type checking: **TypeScript**
- Additional options: none (we add what we need manually)

**Svelte 5 Runes:** SvelteKit 2.x ships with Svelte 5. Use the Svelte 5 runes syntax:
- `$state()` for reactive variables in components
- `$derived()` for computed values
- `$effect()` for side effects
- `$props()` for component props
- `{@render children()}` for slots (replaces `<slot />`)

However, **Svelte stores** (`writable`, `readable`, `derived` from `svelte/store`) are still the correct pattern for shared state across components. Stores are NOT deprecated in Svelte 5 — they serve a different purpose than runes (cross-component vs. intra-component reactivity).

### CSS Strategy: Global Tokens + Scoped Styles

The CSS architecture has two layers:

1. **Global tokens** (`app.css`) — CSS custom properties defining the design system. Imported once in the root layout. These are the portable design tokens from the existing `styles/theme.css`, stripped of all Streamlit-specific selectors.

2. **Scoped styles** (per component `<style>` blocks) — Component-specific CSS. SvelteKit automatically scopes these to the component, eliminating CSS bleeding issues. No `!important` overrides needed, no `data-testid` selectors, no `unsafe_allow_html`.

**CRITICAL:** Do NOT copy the Streamlit-specific CSS rules (`.stApp`, `[data-testid="stSidebar"]`, `.stButton`, etc.) into the SvelteKit project. Only port the design tokens (colors, fonts, spacing) and the component styling patterns (`.dm-message`, `.pc-message`, `.mode-indicator`, etc.).

### WebSocket URL Resolution

The WebSocket client uses a relative URL pattern that works with Vite's proxy in development:
- Dev: `ws://localhost:5173/ws/game/{sessionId}` -> Vite proxies to `ws://localhost:8000/ws/game/{sessionId}`
- Production: `wss://{host}/ws/game/{sessionId}` (when served behind a reverse proxy)

The `getWsUrl()` helper in `ws.ts` derives the protocol and host from `window.location`, so it works in both environments without configuration changes.

### Vite Proxy Configuration

The Vite proxy is essential for development — it routes `/api/*` and `/ws/*` requests from the SvelteKit dev server (port 5173) to the FastAPI backend (port 8000). This avoids CORS issues during development and simulates the production topology where both are served from the same origin.

**Important:** The proxy config is only used during `npm run dev`. In production, the SvelteKit static build is served by FastAPI (or nginx), and API/WS requests go directly to the same server.

### Existing Code to Reference (DO NOT Copy Wholesale)

| Need | Source | What to Extract |
|------|--------|-----------------|
| Design tokens | `styles/theme.css:11-53` | CSS custom properties only (`:root` block) |
| DM message styling | `styles/theme.css:250-267` | Background, border, font, padding patterns |
| PC message styling | `styles/theme.css:269-311` | Character-colored borders, attribution format |
| Mode indicator | `styles/theme.css:556-636` | Badge styling, pulse animation keyframes |
| Character card | `styles/theme.css:367-437` | Card layout, border, glow patterns |
| Drop-in button | `styles/theme.css:444-478` | Button styling, hover states, character colors |
| Scrollbar | `styles/theme.css:136-159` | Webkit + Firefox scrollbar styles |
| API contract | `api/schemas.py` | Pydantic models -> TypeScript interfaces |
| WS message protocol | `api/schemas.py` + architecture doc | Server/client event types |
| REST endpoints | `api/routes.py` | URL paths, request/response shapes |

### TypeScript Type Alignment

The types in `types.ts` MUST match the Pydantic models in `api/schemas.py`. When unsure about a field name or type, check `api/schemas.py` as the source of truth. The key mapping rules:
- Pydantic `str` -> TypeScript `string`
- Pydantic `int` -> TypeScript `number`
- Pydantic `bool` -> TypeScript `boolean`
- Pydantic `list[str]` -> TypeScript `string[]`
- Pydantic `dict[str, T]` -> TypeScript `Record<string, T>`
- Pydantic `Literal["a", "b"]` -> TypeScript `'a' | 'b'`
- Pydantic `Optional[str]` / `str | None` -> TypeScript `string | null`

### Adapter Selection: adapter-static

We use `@sveltejs/adapter-static` because:
1. The SvelteKit app is a client-side SPA — no server-side rendering needed
2. In production, FastAPI serves the built static files
3. `fallback: 'index.html'` ensures SvelteKit's client-side router handles all routes (SPA mode)

### File Structure Created by This Story

```
frontend/
├── package.json                           # Node.js dependencies
├── package-lock.json                      # Lock file
├── tsconfig.json                          # TypeScript config (from scaffold)
├── svelte.config.js                       # SvelteKit config (adapter-static)
├── vite.config.ts                         # Vite config (proxy, plugins)
├── src/
│   ├── app.css                            # Global campfire theme tokens
│   ├── app.html                           # HTML template with font imports
│   ├── app.d.ts                           # SvelteKit type declarations
│   ├── routes/
│   │   ├── +layout.svelte                 # Root layout (sidebar + main)
│   │   ├── +page.svelte                   # Home page placeholder
│   │   └── game/
│   │       └── [sessionId]/
│   │           └── +page.svelte           # Game view placeholder
│   ├── lib/
│   │   ├── api.ts                         # REST API client
│   │   ├── ws.ts                          # WebSocket client
│   │   ├── types.ts                       # TypeScript type definitions
│   │   ├── stores/
│   │   │   ├── index.ts                   # Barrel export
│   │   │   ├── gameStore.ts               # Game state store
│   │   │   ├── uiStore.ts                 # UI state store
│   │   │   └── connectionStore.ts         # Connection status store
│   │   └── components/                    # Empty — populated by Stories 16-5+
│   └── (scaffold files: app.d.ts, etc.)
└── static/
    └── favicon.png                        # SvelteKit default (replace later)
```

### Dependencies (package.json)

The SvelteKit scaffold provides the core dependencies. Additional explicit dependencies:

**Dev dependencies (from scaffold):**
- `@sveltejs/kit` — SvelteKit framework
- `@sveltejs/vite-plugin-svelte` — Vite plugin for Svelte
- `svelte` — Svelte compiler
- `svelte-check` — Type checking for Svelte files
- `typescript` — TypeScript compiler
- `vite` — Build tool

**Dev dependencies (added manually):**
- `@sveltejs/adapter-static` — Static site adapter

No runtime dependencies needed — the API client uses native `fetch()` and the WebSocket client uses the browser's native `WebSocket` API.

### Common Pitfalls to Avoid

1. **Do NOT install or import Streamlit in any frontend file.** The frontend has zero Python dependency.
2. **Do NOT copy Streamlit-specific CSS selectors** (`[data-testid="stSidebar"]`, `.stButton`, `.stApp`, etc.). Only port the design token values and pure component styling patterns.
3. **Do NOT use `npm create svelte@latest`.** Use `npx sv create` which is the current SvelteKit scaffold tool.
4. **Do NOT use Svelte 4 slot syntax** (`<slot />`). Use Svelte 5 snippet pattern (`{@render children()}`).
5. **Do NOT install a CSS framework** (Tailwind, Bootstrap, etc.). The campfire aesthetic requires full CSS control — CSS custom properties + scoped styles per architecture doc.
6. **Do NOT modify any Python files** (no changes to `api/`, `models.py`, `config.py`, etc.). This is a frontend-only story.
7. **Do NOT create component implementations** for NarrativePanel, PartyCard, etc. Those are Stories 16-5 and 16-6. Only create the directories and placeholder pages.
8. **Font loading strategy:** Use `<link>` preconnect + stylesheet in `app.html` (NOT `@import` in CSS). This is faster and non-render-blocking.
9. **Store naming:** Use camelCase for store variable names (`gameState`, not `game_state`) per the architecture doc's Svelte naming conventions.
10. **Import paths:** Use SvelteKit's `$lib` alias (`import { gameState } from '$lib/stores'`), NOT relative paths (`../../lib/stores`).

### Development Workflow

To work on this story, the developer runs:

```bash
# Terminal 1: Backend (already running from previous stories)
uvicorn api.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
# Opens http://localhost:5173
```

The Vite proxy handles routing API/WS requests to the backend. Both servers must be running for full integration, but the frontend can be developed independently (API calls will fail gracefully).

### References

- [Source: _bmad-output/planning-artifacts/architecture.md -- "Project Structure & Boundaries", "Complete Project Directory"]
- [Source: _bmad-output/planning-artifacts/architecture.md -- "API Layer & Frontend Integration" section]
- [Source: _bmad-output/planning-artifacts/architecture.md -- "Svelte Stores", naming conventions]
- [Source: _bmad-output/planning-artifacts/architecture.md -- "Architecture Readiness: Frontend Setup"]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md -- "Design System Foundation", CSS Variable Strategy]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md -- "Typography System", "Spacing & Layout Foundation"]
- [Source: _bmad-output/planning-artifacts/ux-design-specification.md -- "Color System", Character Identity Colors]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-02-11.md -- Section 4.4, Story 16-4 scope]
- [Source: styles/theme.css -- CSS custom properties (:root block), component styling patterns]
- [Source: api/schemas.py -- Pydantic response models for TypeScript type alignment]
- [Source: api/routes.py -- REST endpoint paths and request/response shapes]
- [Source: api/websocket.py -- WebSocket message protocol]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
