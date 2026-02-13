<script lang="ts">
	import { getSessionConfig, updateSessionConfig, getUserSettings, updateUserSettings, ApiError } from '$lib/api';
	import type { GameConfig, UserSettings } from '$lib/types';
	import { clearModelCache } from '$lib/modelUtils';
	import ConfirmDialog from './ConfirmDialog.svelte';
	import ApiKeysTab from './ApiKeysTab.svelte';
	import ModelsTab from './ModelsTab.svelte';
	import SettingsTab from './SettingsTab.svelte';

	type TabId = 'api-keys' | 'models' | 'settings';

	interface Props {
		open: boolean;
		sessionId: string | null;
		onClose: () => void;
	}

	let { open, sessionId, onClose }: Props = $props();

	// Tab state
	let activeTab = $state<TabId>('api-keys');

	// Loading / saving
	let loadingConfig = $state(false);
	let saving = $state(false);
	let saveError = $state<string | null>(null);

	// Unsaved changes confirmation
	let showDiscardConfirm = $state(false);

	// DOM refs for focus management
	let dialogEl: HTMLDivElement | undefined = $state();

	// Original values (for change detection)
	let originalConfig = $state<GameConfig | null>(null);

	// Form values — API keys (sent to backend, localStorage as fallback)
	let googleKey = $state('');
	let anthropicKey = $state('');
	let ollamaUrl = $state('');

	// Server-side configured status (from GET /api/user-settings)
	let googleKeyConfigured = $state(false);
	let anthropicKeyConfigured = $state(false);

	// Original API key values for change detection
	let origGoogleKey = $state('');
	let origAnthropicKey = $state('');
	let origOllamaUrl = $state('');

	// Form values — DM config (session-specific)
	let dmProvider = $state('gemini');
	let dmModel = $state('gemini-1.5-flash');
	let dmTokenLimit = $state(8000);

	// Form values — Models
	let summarizerProvider = $state('gemini');
	let summarizerModel = $state('gemini-1.5-flash');
	let extractorProvider = $state('gemini');
	let extractorModel = $state('gemini-3-flash-preview');

	// Form values — Token limits (global, saved to user-settings)
	let summarizerTokenLimit = $state(4000);
	let extractorTokenLimit = $state(4000);

	// Original token limits for change detection
	let origSummarizerTokenLimit = $state(4000);
	let origExtractorTokenLimit = $state(4000);

	// Form values — Settings
	let combatMode = $state<'Narrative' | 'Tactical'>('Narrative');
	let maxCombatRounds = $state(50);
	let partySize = $state(4);
	let narrativeDisplayLimit = $state(50);

	// Change detection
	let hasChanges = $derived.by(() => {
		const apiKeyChanges =
			googleKey !== origGoogleKey ||
			anthropicKey !== origAnthropicKey ||
			ollamaUrl !== origOllamaUrl;

		const tokenLimitChanges =
			summarizerTokenLimit !== origSummarizerTokenLimit ||
			extractorTokenLimit !== origExtractorTokenLimit;

		if (!originalConfig) {
			return apiKeyChanges || tokenLimitChanges;
		}
		return (
			apiKeyChanges ||
			tokenLimitChanges ||
			dmProvider !== originalConfig.dm_provider ||
			dmModel !== originalConfig.dm_model ||
			dmTokenLimit !== originalConfig.dm_token_limit ||
			summarizerProvider !== originalConfig.summarizer_provider ||
			summarizerModel !== originalConfig.summarizer_model ||
			extractorProvider !== originalConfig.extractor_provider ||
			extractorModel !== originalConfig.extractor_model ||
			combatMode !== originalConfig.combat_mode ||
			maxCombatRounds !== originalConfig.max_combat_rounds ||
			partySize !== originalConfig.party_size ||
			narrativeDisplayLimit !== originalConfig.narrative_display_limit
		);
	});

	// Load config and API keys when modal opens
	$effect(() => {
		if (open) {
			activeTab = 'api-keys';
			saveError = null;
			showDiscardConfirm = false;
			loadApiKeys();
			if (sessionId) {
				loadConfig();
			} else {
				loadingConfig = false;
				originalConfig = null;
				// Set defaults
				dmProvider = 'gemini';
				dmModel = 'gemini-1.5-flash';
				dmTokenLimit = 8000;
				summarizerProvider = 'gemini';
				summarizerModel = 'gemini-1.5-flash';
				extractorProvider = 'gemini';
				extractorModel = 'gemini-3-flash-preview';
				combatMode = 'Narrative';
				maxCombatRounds = 50;
				partySize = 4;
				narrativeDisplayLimit = 50;
			}
		}
	});

	async function loadApiKeys(): Promise<void> {
		// Try loading from backend first
		try {
			const settings = await getUserSettings();
			googleKeyConfigured = settings.google_api_key_configured;
			anthropicKeyConfigured = settings.anthropic_api_key_configured;
			ollamaUrl = settings.ollama_url || '';

			// Load token limit overrides from server
			summarizerTokenLimit = settings.token_limit_overrides?.summarizer ?? 4000;
			extractorTokenLimit = settings.token_limit_overrides?.extractor ?? 4000;
		} catch {
			// Fallback to localStorage if backend unavailable
			googleKeyConfigured = false;
			anthropicKeyConfigured = false;
			try {
				ollamaUrl = localStorage.getItem('autodungeon_ollama_url') ?? '';
			} catch {
				ollamaUrl = '';
			}
			summarizerTokenLimit = 4000;
			extractorTokenLimit = 4000;
		}

		// API key fields always start empty (we never expose raw keys)
		googleKey = '';
		anthropicKey = '';

		origGoogleKey = '';
		origAnthropicKey = '';
		origOllamaUrl = ollamaUrl;
		origSummarizerTokenLimit = summarizerTokenLimit;
		origExtractorTokenLimit = extractorTokenLimit;
	}

	async function loadConfig(): Promise<void> {
		if (!sessionId) return;
		loadingConfig = true;
		saveError = null;
		try {
			const config = await getSessionConfig(sessionId);
			originalConfig = { ...config };
			dmProvider = config.dm_provider;
			dmModel = config.dm_model;
			dmTokenLimit = config.dm_token_limit;
			summarizerProvider = config.summarizer_provider;
			summarizerModel = config.summarizer_model;
			extractorProvider = config.extractor_provider;
			extractorModel = config.extractor_model;
			combatMode = config.combat_mode;
			maxCombatRounds = config.max_combat_rounds;
			partySize = config.party_size;
			narrativeDisplayLimit = config.narrative_display_limit;
		} catch (e) {
			saveError = e instanceof ApiError ? e.message : 'Failed to load configuration';
		} finally {
			loadingConfig = false;
		}
	}

	async function handleSave(): Promise<void> {
		saving = true;
		saveError = null;

		// Build user-settings save (with localStorage fallback)
		const settingsPromise = (async () => {
			try {
				const settingsUpdate: Record<string, unknown> = {};
				if (googleKey.trim()) settingsUpdate.google_api_key = googleKey.trim();
				if (anthropicKey.trim()) settingsUpdate.anthropic_api_key = anthropicKey.trim();
				if (ollamaUrl !== origOllamaUrl) settingsUpdate.ollama_url = ollamaUrl.trim();
				settingsUpdate.token_limit_overrides = {
					summarizer: summarizerTokenLimit,
					extractor: extractorTokenLimit,
				};
				await updateUserSettings(settingsUpdate as Parameters<typeof updateUserSettings>[0]);
			} catch {
				try {
					if (googleKey.trim()) localStorage.setItem('autodungeon_google_key', googleKey.trim());
					if (anthropicKey.trim()) localStorage.setItem('autodungeon_anthropic_key', anthropicKey.trim());
					if (ollamaUrl.trim()) localStorage.setItem('autodungeon_ollama_url', ollamaUrl.trim());
					else localStorage.removeItem('autodungeon_ollama_url');
				} catch { /* localStorage unavailable */ }
			}
		})();

		// Build session-config save (if session active)
		const configPromise = (async (): Promise<GameConfig | null> => {
			if (!sessionId || !originalConfig) return null;
			return updateSessionConfig(sessionId, {
				summarizer_provider: summarizerProvider,
				summarizer_model: summarizerModel,
				extractor_provider: extractorProvider,
				extractor_model: extractorModel,
				combat_mode: combatMode,
				max_combat_rounds: maxCombatRounds,
				party_size: partySize,
				narrative_display_limit: narrativeDisplayLimit,
				dm_provider: dmProvider,
				dm_model: dmModel,
				dm_token_limit: dmTokenLimit,
			});
		})();

		// Run both saves in parallel — they're independent endpoints
		const [, configResult] = await Promise.allSettled([settingsPromise, configPromise]);

		// Clear model cache so dropdowns refetch with new API keys
		clearModelCache();

		// Update originals so change detection resets
		origGoogleKey = googleKey;
		origAnthropicKey = anthropicKey;
		origOllamaUrl = ollamaUrl;
		origSummarizerTokenLimit = summarizerTokenLimit;
		origExtractorTokenLimit = extractorTokenLimit;

		// Check session config result
		if (configResult.status === 'rejected') {
			const e = configResult.reason;
			saveError = e instanceof ApiError ? e.message : 'Failed to save configuration';
			saving = false;
			return;
		}

		if (configResult.value) {
			originalConfig = { ...configResult.value };
		}

		saving = false;
		onClose();
	}

	function handleCancel(): void {
		if (hasChanges) {
			showDiscardConfirm = true;
		} else {
			onClose();
		}
	}

	function handleDiscard(): void {
		showDiscardConfirm = false;
		onClose();
	}

	function handleKeepEditing(): void {
		showDiscardConfirm = false;
	}

	// Focus the dialog when it opens
	$effect(() => {
		if (open && dialogEl) {
			dialogEl.focus();
		}
	});

	function handleKeydown(e: KeyboardEvent): void {
		if (!open) return;
		if (showDiscardConfirm) return;
		if (e.key === 'Escape') {
			e.preventDefault();
			e.stopPropagation();
			handleCancel();
		}
		// Focus trap: keep Tab within the modal
		if (e.key === 'Tab' && dialogEl) {
			const focusable = dialogEl.querySelectorAll<HTMLElement>(
				'button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
			);
			if (focusable.length === 0) return;
			const first = focusable[0];
			const last = focusable[focusable.length - 1];
			if (e.shiftKey && document.activeElement === first) {
				e.preventDefault();
				last.focus();
			} else if (!e.shiftKey && document.activeElement === last) {
				e.preventDefault();
				first.focus();
			}
		}
	}

	function handleBackdropClick(e: MouseEvent): void {
		if (e.target === e.currentTarget) {
			handleCancel();
		}
	}

	const tabs: { id: TabId; label: string; requiresSession?: boolean }[] = [
		{ id: 'api-keys', label: 'API Keys' },
		{ id: 'models', label: 'Models', requiresSession: true },
		{ id: 'settings', label: 'Settings', requiresSession: true },
	];
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
	<div class="settings-backdrop" onclick={handleBackdropClick}>
		<div
			class="settings-modal"
			role="dialog"
			aria-modal="true"
			aria-label="Configuration"
			bind:this={dialogEl}
			tabindex="-1"
		>
			<!-- Header -->
			<div class="modal-header">
				<h3 class="modal-title">Configuration</h3>
				<button
					class="close-btn"
					onclick={handleCancel}
					aria-label="Close settings"
				>
					<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
						<line x1="4" y1="4" x2="12" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
						<line x1="12" y1="4" x2="4" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
					</svg>
				</button>
			</div>

			<!-- Tabs -->
			<div class="tab-bar" role="tablist">
				{#each tabs as tab}
					<button
						role="tab"
						class="tab-btn"
						class:active={activeTab === tab.id}
						class:tab-disabled={tab.requiresSession && !sessionId}
						aria-selected={activeTab === tab.id}
						disabled={tab.requiresSession && !sessionId}
						onclick={() => (activeTab = tab.id)}
					>
						{tab.label}
					</button>
				{/each}
			</div>

			<!-- Tab content -->
			<div class="tab-content">
				{#if loadingConfig}
					<div class="loading-state">
						<span class="spinner" aria-hidden="true"></span>
						<span class="loading-text">Loading configuration...</span>
					</div>
				{:else}
					{#if activeTab === 'api-keys'}
						<ApiKeysTab
							{googleKey}
							{anthropicKey}
							{ollamaUrl}
							{googleKeyConfigured}
							{anthropicKeyConfigured}
							onGoogleKeyChange={(v) => (googleKey = v)}
							onAnthropicKeyChange={(v) => (anthropicKey = v)}
							onOllamaUrlChange={(v) => (ollamaUrl = v)}
						/>
					{:else if activeTab === 'models'}
						<ModelsTab
							{dmProvider}
							{dmModel}
							{dmTokenLimit}
							{summarizerProvider}
							{summarizerModel}
							{summarizerTokenLimit}
							{extractorProvider}
							{extractorModel}
							{extractorTokenLimit}
							onDmProviderChange={(v) => (dmProvider = v)}
							onDmModelChange={(v) => (dmModel = v)}
							onDmTokenLimitChange={(v) => (dmTokenLimit = v)}
							onSummarizerProviderChange={(v) => (summarizerProvider = v)}
							onSummarizerModelChange={(v) => (summarizerModel = v)}
							onSummarizerTokenLimitChange={(v) => (summarizerTokenLimit = v)}
							onExtractorProviderChange={(v) => (extractorProvider = v)}
							onExtractorModelChange={(v) => (extractorModel = v)}
							onExtractorTokenLimitChange={(v) => (extractorTokenLimit = v)}
						/>
					{:else if activeTab === 'settings'}
						<SettingsTab
							{combatMode}
							{maxCombatRounds}
							{partySize}
							{narrativeDisplayLimit}
							onCombatModeChange={(v) => (combatMode = v)}
							onMaxCombatRoundsChange={(v) => (maxCombatRounds = v)}
							onPartySizeChange={(v) => (partySize = v)}
							onNarrativeDisplayLimitChange={(v) => (narrativeDisplayLimit = v)}
						/>
					{/if}
				{/if}
			</div>

			<!-- Error -->
			{#if saveError}
				<p class="save-error" role="alert">{saveError}</p>
			{/if}

			<!-- Footer -->
			<div class="modal-footer">
				<button
					class="btn btn-secondary"
					onclick={handleCancel}
					disabled={saving}
				>
					Cancel
				</button>
				<button
					class="btn btn-primary"
					onclick={handleSave}
					disabled={saving || loadingConfig}
				>
					{#if saving}
						<span class="spinner spinner-sm" aria-hidden="true"></span>
						Saving...
					{:else}
						Save
					{/if}
				</button>
			</div>
		</div>
	</div>

	<!-- Unsaved changes confirmation -->
	<ConfirmDialog
		open={showDiscardConfirm}
		title="Discard unsaved changes?"
		message="You have unsaved changes. Discard them?"
		confirmLabel="Discard"
		confirmDanger={true}
		onConfirm={handleDiscard}
		onCancel={handleKeepEditing}
	/>
{/if}

<style>
	.settings-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 150;
		animation: fadeIn 0.15s ease;
	}

	.settings-modal {
		background: var(--bg-secondary);
		border-radius: 12px;
		max-width: 560px;
		width: 92%;
		max-height: 85vh;
		display: flex;
		flex-direction: column;
		animation: scaleIn 0.15s ease;
		outline: none;
	}

	/* Header */
	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-md) var(--space-lg);
		border-bottom: 1px solid rgba(184, 168, 150, 0.1);
	}

	.modal-title {
		font-family: var(--font-ui);
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 4px;
		border-radius: var(--border-radius-sm);
		transition: color var(--transition-fast);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.close-btn:hover {
		color: var(--text-primary);
	}

	.close-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	/* Tab bar */
	.tab-bar {
		display: flex;
		gap: 0;
		padding: 0 var(--space-lg);
		border-bottom: 1px solid rgba(184, 168, 150, 0.1);
	}

	.tab-btn {
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--text-secondary);
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		font-weight: 500;
		padding: var(--space-sm) var(--space-md);
		cursor: pointer;
		transition:
			color var(--transition-fast),
			border-color var(--transition-fast);
	}

	.tab-btn:hover {
		color: var(--text-primary);
	}

	.tab-btn.active {
		color: var(--accent-warm);
		border-bottom-color: var(--accent-warm);
	}

	.tab-btn:disabled,
	.tab-btn.tab-disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.tab-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: -2px;
	}

	/* Tab content */
	.tab-content {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-lg);
		min-height: 200px;
	}

	/* Loading */
	.loading-state {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-sm);
		padding: var(--space-2xl) 0;
	}

	.loading-text {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-secondary);
	}

	/* Spinner */
	.spinner {
		display: inline-block;
		width: 18px;
		height: 18px;
		border: 2px solid var(--text-secondary);
		border-right-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	.spinner-sm {
		width: 14px;
		height: 14px;
	}

	/* Error */
	.save-error {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--color-error);
		padding: 0 var(--space-lg);
		margin: 0;
	}

	/* Footer */
	.modal-footer {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-sm);
		padding: var(--space-md) var(--space-lg);
		border-top: 1px solid rgba(184, 168, 150, 0.1);
	}

	/* Buttons */
	.btn {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		font-weight: 500;
		padding: 8px 16px;
		border-radius: var(--border-radius-sm);
		border: none;
		cursor: pointer;
		transition:
			background var(--transition-fast),
			opacity var(--transition-fast);
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}

	.btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.btn-primary {
		background: var(--accent-warm);
		color: var(--bg-primary);
	}

	.btn-primary:hover:not(:disabled) {
		background: var(--accent-warm-hover);
	}

	.btn-secondary {
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid rgba(184, 168, 150, 0.3);
	}

	.btn-secondary:hover:not(:disabled) {
		background: var(--bg-message);
		color: var(--text-primary);
	}

	/* Animations */
	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	@keyframes scaleIn {
		from {
			transform: scale(0.95);
			opacity: 0;
		}
		to {
			transform: scale(1);
			opacity: 1;
		}
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Responsive */
	@media (max-width: 768px) {
		.settings-modal {
			width: 98%;
			max-height: 90vh;
			border-radius: 8px;
		}

		.tab-content {
			padding: var(--space-md);
		}

		.modal-header,
		.modal-footer {
			padding: var(--space-sm) var(--space-md);
		}

		.tab-bar {
			padding: 0 var(--space-md);
		}
	}
</style>
