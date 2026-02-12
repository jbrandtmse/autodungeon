# Story 16.8: Settings & Configuration UI

Status: ready-for-dev

## Story

As a **user playing autodungeon**,
I want **a settings modal accessible from the sidebar that lets me configure API keys, per-agent model selection, context limits, and display preferences**,
so that **I can customize the AI providers and game settings without leaving the game session, replacing the legacy Streamlit configuration modal**.

## Acceptance Criteria (Given/When/Then)

### AC1: Settings Button in Sidebar

**Given** the user is on any page (home or game)
**When** they look at the sidebar
**Then** a "Settings" button with a gear icon is visible below the existing sidebar controls
**And** clicking it opens the Settings modal

### AC2: Modal Structure with Tabs

**Given** the user clicks the "Settings" button
**When** the Settings modal opens
**Then** it displays as a centered overlay with `--bg-secondary` background and 12px border-radius
**And** it shows three tabs: "API Keys", "Models", "Settings"
**And** the active tab has an amber underline indicator (`--accent-warm`)
**And** the modal title "Configuration" is displayed at the top in Inter 16px weight 600

### AC3: API Keys Tab

**Given** the Settings modal is open on the "API Keys" tab
**When** the tab renders
**Then** it shows entry fields for three providers:
  - **Google (Gemini)**: password-type input for API key
  - **Anthropic (Claude)**: password-type input for API key
  - **Ollama**: text input for base URL (default "http://localhost:11434")
**And** each field has a label with the provider name
**And** API key fields mask the input (password type)
**And** each provider shows a status indicator (unconfigured/configured)

### AC4: Models Tab — Per-Agent Model Selection

**Given** the Settings modal is open on the "Models" tab
**When** the tab renders
**Then** it shows provider and model dropdowns for:
  - Dungeon Master (DM)
  - Summarizer (memory compression)
  - Extractor (narrative extraction)
**And** each row shows: agent name, provider dropdown, model dropdown
**And** changing the provider updates the model dropdown to show models for that provider
**And** the current session config values are pre-selected

### AC5: Settings Tab — Context Limits & Display

**Given** the Settings modal is open on the "Settings" tab
**When** the tab renders
**Then** it shows:
  - **Combat Mode**: dropdown with "Narrative" and "Tactical" options
  - **Max Combat Rounds**: number input (0-100, default 50)
  - **Party Size**: number input (1-8, default 4)
  - **Narrative Display Limit**: number input (10-1000, default 50, step 10)
**And** current session config values are pre-selected

### AC6: Save/Cancel with Change Detection

**Given** the Settings modal is open
**When** the user makes changes to any field
**Then** the "Save" button becomes visually active
**When** the user clicks "Save"
**Then** the config is sent via `PUT /api/sessions/{id}/config` for session-specific settings
**And** on success, the modal closes and a brief success message appears
**And** on failure, an error message is shown inline

**Given** the Settings modal has unsaved changes
**When** the user clicks "Cancel" or presses Escape
**Then** a confirmation dialog asks "Discard unsaved changes?"
**And** "Discard" closes the modal without saving
**And** "Keep Editing" returns to the modal

**Given** the Settings modal has no changes
**When** the user clicks "Cancel" or presses Escape
**Then** the modal closes immediately with no confirmation

### AC7: Loading States

**Given** the Settings modal is opening
**When** the config is being fetched from the API
**Then** a loading spinner is shown in the modal body
**And** once loaded, the form fields populate with current values

**Given** the user clicks "Save"
**When** the API call is in flight
**Then** the Save button shows a spinner and is disabled
**And** the Cancel button is also disabled

### AC8: Config Loading from API

**Given** a session is active
**When** the Settings modal opens
**Then** the current config is loaded via `GET /api/sessions/{id}/config`
**And** all form fields are populated with the returned values

**Given** no session is active (home page)
**When** the Settings modal opens
**Then** the API Keys tab is shown (global settings)
**And** the Models and Settings tabs show default values (not linked to a session)

## Tasks / Subtasks

- [ ] **Task 1: Create SettingsModal.svelte** (AC: 2, 6, 7)
  - [ ] 1.1: Modal backdrop and dialog container
  - [ ] 1.2: Tab navigation with amber underline active indicator
  - [ ] 1.3: Tab content switching (API Keys, Models, Settings)
  - [ ] 1.4: Save/Cancel footer with change detection
  - [ ] 1.5: Loading state while fetching config
  - [ ] 1.6: Unsaved changes confirmation via ConfirmDialog
  - [ ] 1.7: Escape key to close, backdrop click to close

- [ ] **Task 2: Create ApiKeysTab.svelte** (AC: 3)
  - [ ] 2.1: Google (Gemini) API key input with mask
  - [ ] 2.2: Anthropic (Claude) API key input with mask
  - [ ] 2.3: Ollama base URL input
  - [ ] 2.4: Status indicators per provider

- [ ] **Task 3: Create ModelsTab.svelte** (AC: 4)
  - [ ] 3.1: Provider/model dropdowns for DM
  - [ ] 3.2: Provider/model dropdowns for Summarizer
  - [ ] 3.3: Provider/model dropdowns for Extractor
  - [ ] 3.4: Provider change updates available model list
  - [ ] 3.5: Pre-select current session config values

- [ ] **Task 4: Create SettingsTab.svelte** (AC: 5)
  - [ ] 4.1: Combat mode dropdown (Narrative/Tactical)
  - [ ] 4.2: Max combat rounds number input
  - [ ] 4.3: Party size number input
  - [ ] 4.4: Narrative display limit number input

- [ ] **Task 5: Integrate Settings button in Sidebar** (AC: 1)
  - [ ] 5.1: Add gear icon Settings button to Sidebar.svelte
  - [ ] 5.2: Wire button to open SettingsModal in +layout.svelte

- [ ] **Task 6: Verification** (all ACs)
  - [ ] 6.1: `npm run build` passes
  - [ ] 6.2: `npm run check` passes
  - [ ] 6.3: `python -m pytest` — no regressions
  - [ ] 6.4: Update sprint-status.yaml

## Dev Notes

### Architecture Context

This story builds the **Settings & Configuration modal** for the SvelteKit frontend. It replaces the Streamlit `render_config_modal()` (app.py:3422), `render_api_keys_tab()` (app.py:2264), `render_models_tab()` (app.py ~2800s), and `render_settings_tab()` (app.py:3316) functions.

The REST API endpoints already exist:
- `GET /api/sessions/{id}/config` — returns `GameConfigResponse`
- `PUT /api/sessions/{id}/config` — accepts `GameConfigUpdateRequest` (partial update)

The frontend API client already has:
- `getSessionConfig(sessionId)` — fetch config
- `updateSessionConfig(sessionId, config)` — update config

### Provider/Model Constants

Mirror from Python `config.py` (lines 846-866):

```typescript
const PROVIDERS = ['gemini', 'anthropic', 'ollama'] as const;
const PROVIDER_DISPLAY: Record<string, string> = {
  gemini: 'Gemini',
  anthropic: 'Claude',
  ollama: 'Ollama',
};
const GEMINI_MODELS = [
  'gemini-3-flash-preview',
  'gemini-1.5-pro',
  'gemini-2.0-flash',
  'gemini-2.5-flash-preview-05-20',
  'gemini-2.5-pro-preview-05-06',
  'gemini-3-pro-preview',
];
const CLAUDE_MODELS = [
  'claude-3-haiku-20240307',
  'claude-3-5-sonnet-20241022',
  'claude-sonnet-4-20250514',
];
const OLLAMA_MODELS = ['llama3', 'mistral', 'phi3'];
```

### Component Hierarchy

```
+layout.svelte
  ├── Sidebar.svelte
  │     └── Settings button (gear icon)
  └── SettingsModal.svelte (portal to body)
        ├── Tab navigation (API Keys | Models | Settings)
        ├── ApiKeysTab.svelte
        ├── ModelsTab.svelte
        ├── SettingsTab.svelte
        ├── Save/Cancel footer
        └── ConfirmDialog.svelte (for unsaved changes)
```

### Svelte 5 Patterns Used

| Pattern | Usage |
|---------|-------|
| `$state()` | Local reactive state (activeTab, formValues, hasChanges, etc.) |
| `$derived()` | Computed hasChanges from comparing original vs current values |
| `$effect()` | Load config when modal opens, reset form on close |
| `$props()` | Component props (open, sessionId, onClose) |
| `$bindable()` | Two-way binding for form inputs |

### API Keys Note

API keys are NOT persisted via the REST API config endpoints (those handle `GameConfig` fields only: combat_mode, models, party_size, etc.). API keys are stored client-side only in this implementation. The API Keys tab provides a UI but keys are stored in browser localStorage until a dedicated backend endpoint exists. This matches the Streamlit behavior where keys were in session_state only.

### File Structure

```
frontend/src/lib/components/
  ├── SettingsModal.svelte    # NEW: main modal with tabs
  ├── ApiKeysTab.svelte       # NEW: API key entry
  ├── ModelsTab.svelte        # NEW: per-agent model selection
  └── SettingsTab.svelte      # NEW: context limits, display settings

frontend/src/lib/components/
  └── Sidebar.svelte          # MODIFIED: add Settings button

frontend/src/routes/
  └── +layout.svelte          # MODIFIED: add SettingsModal rendering
```

### Common Pitfalls to Avoid

1. **Do NOT modify Python files** except sprint-status.yaml
2. **Do NOT use `window.confirm()`** — use existing ConfirmDialog component
3. **Use Svelte 5 runes** ($state, $derived, $props, $effect) not Svelte 4 reactive statements
4. **Tab styling**: amber underline on active tab, not background color change
5. **Form inputs**: use campfire theme CSS vars, not default browser styles
6. **Config endpoints are session-scoped** — need a session ID to save. If no session, settings are display-only
7. **Provider change cascades**: when provider changes, reset model to first available for that provider

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List

### File List
