<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { discoverModules, getCharacters, startSession, ApiError } from '$lib/api';
	import type { ModuleInfo, Character } from '$lib/types';

	// Route param — always defined since this is a [sessionId] route
	let sessionId = $derived($page.params.sessionId ?? '');

	// Wizard step: 1 = Module Selection, 2 = Party Setup, 3 = Launching
	let step = $state(1);

	// Step 1: Module Selection
	let modules = $state<ModuleInfo[]>([]);
	let modulesLoading = $state(true);
	let modulesError = $state<string | null>(null);
	let selectedModule = $state<ModuleInfo | null>(null);
	let freeformChosen = $state(false);
	let moduleSearch = $state('');

	let filteredModules = $derived(
		moduleSearch.trim()
			? modules.filter(
					(m) =>
						m.name.toLowerCase().includes(moduleSearch.toLowerCase()) ||
						m.description.toLowerCase().includes(moduleSearch.toLowerCase()) ||
						m.setting.toLowerCase().includes(moduleSearch.toLowerCase()),
				)
			: modules,
	);

	let moduleChosen = $derived(selectedModule !== null || freeformChosen);

	// Step 2: Party Setup
	let characters = $state<Character[]>([]);
	let charactersLoading = $state(false);
	let charactersError = $state<string | null>(null);
	let selectedCharacters = $state<Set<string>>(new Set());
	let adventureName = $state('');

	let partyValid = $derived(selectedCharacters.size >= 1);

	// Step 3: Launching
	let launching = $state(false);
	let launchError = $state<string | null>(null);

	function selectModule(m: ModuleInfo): void {
		selectedModule = m;
		freeformChosen = false;
	}

	function chooseFreeform(): void {
		selectedModule = null;
		freeformChosen = true;
	}

	function goToStep2(): void {
		if (!moduleChosen) return;
		step = 2;
		if (characters.length === 0) {
			loadCharacters();
		}
	}

	function goBackToStep1(): void {
		step = 1;
	}

	async function loadCharacters(): Promise<void> {
		charactersLoading = true;
		charactersError = null;
		try {
			characters = await getCharacters();
			// Default: select all preset characters, deselect library
			const defaults = new Set<string>();
			for (const c of characters) {
				if (c.source === 'preset') {
					defaults.add(c.name);
				}
			}
			selectedCharacters = defaults;
		} catch (e) {
			charactersError = e instanceof ApiError ? e.message : 'Failed to load characters';
		} finally {
			charactersLoading = false;
		}
	}

	function toggleCharacter(name: string): void {
		const next = new Set(selectedCharacters);
		if (next.has(name)) {
			next.delete(name);
		} else {
			next.add(name);
		}
		selectedCharacters = next;
	}

	async function beginAdventure(): Promise<void> {
		step = 3;
		launching = true;
		launchError = null;

		try {
			await startSession(sessionId, {
				selected_module: selectedModule,
				selected_characters: [...selectedCharacters],
				adventure_name: adventureName.trim(),
			});
			goto(`/game/${encodeURIComponent(sessionId)}`);
		} catch (e) {
			launchError = e instanceof ApiError ? e.message : 'Failed to start adventure';
			launching = false;
		}
	}

	function retryLaunch(): void {
		launchError = null;
		beginAdventure();
	}

	onMount(async () => {
		modulesLoading = true;
		modulesError = null;
		try {
			const result = await discoverModules();
			if (result.source === 'error') {
				modulesError = result.error || 'Module discovery failed';
				modules = [];
			} else {
				modules = result.modules;
			}
		} catch (e) {
			modulesError = e instanceof ApiError ? e.message : 'Failed to discover modules';
		} finally {
			modulesLoading = false;
		}
	});

	// Character color lookup helper
	const CLASS_COLORS: Record<string, string> = {
		fighter: 'var(--color-fighter)',
		rogue: 'var(--color-rogue)',
		wizard: 'var(--color-wizard)',
		cleric: 'var(--color-cleric)',
	};

	function getCharColor(c: Character): string {
		return c.color || CLASS_COLORS[c.character_class.toLowerCase()] || 'var(--text-secondary)';
	}
</script>

<div class="setup-page">
	<!-- Progress indicator -->
	<div class="progress-bar">
		<div class="progress-step" class:active={step >= 1} class:done={step > 1}>
			<span class="step-num">1</span>
			<span class="step-label">Module</span>
		</div>
		<div class="progress-line" class:active={step > 1}></div>
		<div class="progress-step" class:active={step >= 2} class:done={step > 2}>
			<span class="step-num">2</span>
			<span class="step-label">Party</span>
		</div>
		<div class="progress-line" class:active={step > 2}></div>
		<div class="progress-step" class:active={step >= 3}>
			<span class="step-num">3</span>
			<span class="step-label">Launch</span>
		</div>
	</div>

	<!-- Step 1: Module Selection -->
	{#if step === 1}
		<div class="step-content" data-testid="step-module">
			<h2 class="step-title">Choose Your Adventure</h2>
			<p class="step-subtitle">Select a D&D module or embark on a freeform adventure.</p>

			{#if modulesLoading}
				<div class="loading-state">
					<div class="spinner-lg" aria-hidden="true"></div>
					<p class="loading-text">Consulting the Dungeon Master's Library...</p>
				</div>
			{:else if modulesError}
				<div class="error-banner" role="alert">
					<p>{modulesError}</p>
				</div>
				<!-- Even on error, offer freeform -->
				<button
					class="btn btn-freeform"
					onclick={chooseFreeform}
					class:selected={freeformChosen}
				>
					Freeform Adventure
					<span class="freeform-desc">Let the DM create a unique story</span>
				</button>
			{:else}
				<!-- Freeform option -->
				<button
					class="btn btn-freeform"
					onclick={chooseFreeform}
					class:selected={freeformChosen}
					data-testid="freeform-btn"
				>
					Freeform Adventure
					<span class="freeform-desc">Let the DM create a unique story</span>
				</button>

				<!-- Search -->
				{#if modules.length > 10}
					<div class="module-search-wrapper">
						<input
							type="text"
							class="module-search"
							placeholder="Search modules..."
							bind:value={moduleSearch}
							aria-label="Search modules"
						/>
					</div>
				{/if}

				<!-- Module grid -->
				<div class="module-grid">
					{#each filteredModules as m (m.number)}
						<button
							class="module-card"
							class:selected={selectedModule?.number === m.number}
							onclick={() => selectModule(m)}
							data-testid="module-card"
						>
							<div class="module-header">
								<span class="module-name">{m.name}</span>
								{#if m.level_range}
									<span class="module-level">Lvl {m.level_range}</span>
								{/if}
							</div>
							<p class="module-desc">{m.description}</p>
							{#if m.setting}
								<span class="module-setting">{m.setting}</span>
							{/if}
						</button>
					{/each}
				</div>

				{#if filteredModules.length === 0 && moduleSearch.trim()}
					<p class="no-results">No modules match "{moduleSearch}"</p>
				{/if}
			{/if}

			<!-- Next button -->
			<div class="step-actions">
				<button
					class="btn btn-primary btn-lg"
					disabled={!moduleChosen}
					onclick={goToStep2}
					data-testid="next-step2"
				>
					Next: Assemble Party &rarr;
				</button>
			</div>
		</div>

	<!-- Step 2: Party Setup -->
	{:else if step === 2}
		<div class="step-content" data-testid="step-party">
			<h2 class="step-title">Assemble Your Party</h2>
			<p class="step-subtitle">Choose the adventurers who will join this quest.</p>

			{#if charactersLoading}
				<div class="loading-state">
					<div class="spinner-lg" aria-hidden="true"></div>
					<p class="loading-text">Loading characters...</p>
				</div>
			{:else if charactersError}
				<div class="error-banner" role="alert">
					<p>{charactersError}</p>
				</div>
			{:else}
				<div class="character-grid">
					{#each characters as c (c.name)}
						<button
							class="character-card"
							class:selected={selectedCharacters.has(c.name)}
							onclick={() => toggleCharacter(c.name)}
							data-testid="character-card"
						>
							<div class="char-indicator" style="background: {getCharColor(c)}"></div>
							<div class="char-info">
								<span class="char-name">{c.name}</span>
								<span class="char-class">{c.character_class}</span>
								<span class="char-meta">{c.provider}/{c.model}</span>
							</div>
							<div class="char-source">{c.source}</div>
							<div class="char-check" class:checked={selectedCharacters.has(c.name)}>
								{#if selectedCharacters.has(c.name)}
									&#10003;
								{/if}
							</div>
						</button>
					{/each}
				</div>

				<div class="adventure-name-wrapper">
					<label for="adventure-name" class="adventure-name-label">
						Adventure Name <span class="optional">(optional)</span>
					</label>
					<input
						id="adventure-name"
						type="text"
						class="adventure-name-input"
						placeholder="e.g., The Lost Mine of Phandelver"
						bind:value={adventureName}
					/>
				</div>
			{/if}

			<div class="step-actions step-actions-split">
				<button class="btn btn-secondary" onclick={goBackToStep1}>
					&larr; Back
				</button>
				<button
					class="btn btn-primary btn-lg"
					disabled={!partyValid}
					onclick={beginAdventure}
					data-testid="begin-adventure"
				>
					Begin Adventure &rarr;
				</button>
			</div>
		</div>

	<!-- Step 3: Launching -->
	{:else if step === 3}
		<div class="step-content step-launch" data-testid="step-launch">
			{#if launchError}
				<div class="error-banner" role="alert">
					<p>{launchError}</p>
				</div>
				<button class="btn btn-primary" onclick={retryLaunch}>
					Retry
				</button>
				<button class="btn btn-secondary" onclick={goBackToStep1}>
					&larr; Back to Setup
				</button>
			{:else}
				<div class="loading-state">
					<div class="spinner-lg" aria-hidden="true"></div>
					<p class="loading-text">Preparing your adventure...</p>
					{#if selectedModule}
						<p class="loading-detail">Module: {selectedModule.name}</p>
					{:else}
						<p class="loading-detail">Freeform adventure</p>
					{/if}
					<p class="loading-detail">Party: {[...selectedCharacters].join(', ')}</p>
				</div>
			{/if}
		</div>
	{/if}
</div>

<style>
	.setup-page {
		max-width: var(--max-content-width);
		margin: 0 auto;
		padding: var(--space-lg) var(--space-md);
		min-height: 100vh;
	}

	/* Progress Bar */
	.progress-bar {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0;
		margin-bottom: var(--space-2xl);
	}

	.progress-step {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
		opacity: 0.4;
		transition: opacity var(--transition-normal);
	}

	.progress-step.active {
		opacity: 1;
	}

	.step-num {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: var(--bg-message);
		color: var(--text-secondary);
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 600;
		transition:
			background var(--transition-normal),
			color var(--transition-normal);
	}

	.progress-step.active .step-num {
		background: var(--accent-warm);
		color: var(--bg-primary);
	}

	.progress-step.done .step-num {
		background: var(--color-success);
		color: var(--bg-primary);
	}

	.step-label {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
	}

	.progress-line {
		width: 60px;
		height: 2px;
		background: var(--bg-message);
		margin: 0 var(--space-sm);
		transition: background var(--transition-normal);
	}

	.progress-line.active {
		background: var(--color-success);
	}

	/* Step Content */
	.step-content {
		animation: fadeIn 0.2s ease;
	}

	.step-title {
		font-family: var(--font-narrative);
		font-size: 28px;
		font-weight: 600;
		color: var(--color-dm);
		margin-bottom: var(--space-xs);
	}

	.step-subtitle {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-secondary);
		margin-bottom: var(--space-lg);
	}

	/* Loading */
	.loading-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: var(--space-2xl) 0;
		gap: var(--space-md);
	}

	.spinner-lg {
		width: 32px;
		height: 32px;
		border: 3px solid var(--accent-warm);
		border-right-color: transparent;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	.loading-text {
		font-family: var(--font-narrative);
		font-size: var(--text-dm);
		color: var(--text-secondary);
		font-style: italic;
	}

	.loading-detail {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
		opacity: 0.7;
	}

	/* Error banner */
	.error-banner {
		background: rgba(196, 92, 74, 0.12);
		border: 1px solid rgba(196, 92, 74, 0.3);
		border-radius: var(--border-radius-md);
		padding: var(--space-md);
		margin-bottom: var(--space-md);
		color: var(--color-error);
		font-family: var(--font-ui);
		font-size: var(--text-ui);
	}

	/* Freeform button */
	.btn-freeform {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		width: 100%;
		background: var(--bg-secondary);
		border: 2px solid rgba(184, 168, 150, 0.15);
		border-radius: var(--border-radius-md);
		padding: var(--space-md);
		color: var(--text-primary);
		cursor: pointer;
		font-family: var(--font-narrative);
		font-size: 16px;
		font-weight: 600;
		text-align: left;
		margin-bottom: var(--space-md);
		transition:
			border-color var(--transition-fast),
			background var(--transition-fast);
	}

	.btn-freeform:hover {
		border-color: var(--accent-warm);
		background: var(--bg-message);
	}

	.btn-freeform.selected {
		border-color: var(--accent-warm);
		background: rgba(232, 168, 73, 0.08);
	}

	.freeform-desc {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 400;
		color: var(--text-secondary);
		margin-top: var(--space-xs);
	}

	/* Module search */
	.module-search-wrapper {
		margin-bottom: var(--space-md);
	}

	.module-search {
		width: 100%;
		background: var(--bg-secondary);
		color: var(--text-primary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm) var(--space-md);
		font-family: var(--font-ui);
		font-size: var(--text-ui);
	}

	.module-search:focus {
		outline: 2px solid var(--accent-warm);
		outline-offset: 1px;
		border-color: transparent;
	}

	.module-search::placeholder {
		color: var(--text-secondary);
		opacity: 0.6;
	}

	/* Module grid */
	.module-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: var(--space-sm);
		max-height: 50vh;
		overflow-y: auto;
		padding-right: var(--space-xs);
		margin-bottom: var(--space-md);
	}

	.module-card {
		display: flex;
		flex-direction: column;
		background: var(--bg-secondary);
		border: 2px solid rgba(184, 168, 150, 0.1);
		border-radius: var(--border-radius-md);
		padding: var(--space-md);
		cursor: pointer;
		text-align: left;
		transition:
			border-color var(--transition-fast),
			background var(--transition-fast);
	}

	.module-card:hover {
		border-color: rgba(184, 168, 150, 0.3);
		background: var(--bg-message);
	}

	.module-card.selected {
		border-color: var(--accent-warm);
		background: rgba(232, 168, 73, 0.08);
	}

	.module-header {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--space-sm);
		margin-bottom: var(--space-xs);
	}

	.module-name {
		font-family: var(--font-narrative);
		font-size: 15px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.module-level {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--accent-warm);
		white-space: nowrap;
	}

	.module-desc {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
		line-height: 1.4;
		margin-bottom: var(--space-xs);
	}

	.module-setting {
		font-family: var(--font-ui);
		font-size: 11px;
		color: var(--text-secondary);
		opacity: 0.7;
	}

	.no-results {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-secondary);
		text-align: center;
		padding: var(--space-lg) 0;
	}

	/* Character grid */
	.character-grid {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
		margin-bottom: var(--space-lg);
	}

	.character-card {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		background: var(--bg-secondary);
		border: 2px solid rgba(184, 168, 150, 0.1);
		border-radius: var(--border-radius-md);
		padding: var(--space-sm) var(--space-md);
		cursor: pointer;
		text-align: left;
		transition:
			border-color var(--transition-fast),
			background var(--transition-fast);
	}

	.character-card:hover {
		border-color: rgba(184, 168, 150, 0.3);
		background: var(--bg-message);
	}

	.character-card.selected {
		border-color: var(--accent-warm);
		background: rgba(232, 168, 73, 0.06);
	}

	.char-indicator {
		width: 8px;
		height: 40px;
		border-radius: 4px;
		flex-shrink: 0;
	}

	.char-info {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.char-name {
		font-family: var(--font-narrative);
		font-size: 15px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.char-class {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
	}

	.char-meta {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-secondary);
		opacity: 0.6;
	}

	.char-source {
		font-family: var(--font-ui);
		font-size: 11px;
		color: var(--text-secondary);
		opacity: 0.5;
		text-transform: uppercase;
		letter-spacing: 0.5px;
	}

	.char-check {
		width: 24px;
		height: 24px;
		border-radius: var(--border-radius-sm);
		border: 2px solid rgba(184, 168, 150, 0.3);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 14px;
		color: var(--bg-primary);
		flex-shrink: 0;
		transition:
			background var(--transition-fast),
			border-color var(--transition-fast);
	}

	.char-check.checked {
		background: var(--accent-warm);
		border-color: var(--accent-warm);
	}

	/* Adventure name */
	.adventure-name-wrapper {
		margin-bottom: var(--space-lg);
	}

	.adventure-name-label {
		display: block;
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-secondary);
		margin-bottom: var(--space-xs);
	}

	.optional {
		opacity: 0.6;
		font-size: var(--text-system);
	}

	.adventure-name-input {
		width: 100%;
		background: var(--bg-secondary);
		color: var(--text-primary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm) var(--space-md);
		font-family: var(--font-ui);
		font-size: var(--text-ui);
	}

	.adventure-name-input:focus {
		outline: 2px solid var(--accent-warm);
		outline-offset: 1px;
		border-color: transparent;
	}

	.adventure-name-input::placeholder {
		color: var(--text-secondary);
		opacity: 0.6;
	}

	/* Step actions */
	.step-actions {
		display: flex;
		justify-content: flex-end;
		padding-top: var(--space-md);
		border-top: 1px solid rgba(184, 168, 150, 0.1);
	}

	.step-actions-split {
		justify-content: space-between;
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
		opacity: 0.4;
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

	.btn-lg {
		padding: 12px 24px;
		font-size: 16px;
	}

	/* Launch step */
	.step-launch {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--space-md);
		padding-top: var(--space-2xl);
	}

	/* Animations */
	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Responsive */
	@media (max-width: 768px) {
		.module-grid {
			grid-template-columns: 1fr;
		}

		.progress-line {
			width: 30px;
		}

		.step-label {
			display: none;
		}
	}
</style>
