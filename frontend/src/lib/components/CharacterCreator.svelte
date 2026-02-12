<script lang="ts">
	import type { CharacterDetail, CharacterCreateRequest } from '$lib/types';

	/**
	 * Character creation/editing wizard — multi-step form.
	 * Story 16-9: Character Creation & Library.
	 *
	 * Steps:
	 *   0 - Name & Class
	 *   1 - Personality & Backstory
	 *   2 - Provider, Model & Color
	 *   3 - Review & Save
	 */

	interface Props {
		/** When set, the wizard is in edit mode. */
		editCharacter?: CharacterDetail | null;
		onSave: (data: CharacterCreateRequest) => void;
		onCancel: () => void;
		saving?: boolean;
		error?: string | null;
	}

	let { editCharacter = null, onSave, onCancel, saving = false, error = null }: Props = $props();

	const STEPS = ['Identity', 'Personality', 'Configuration', 'Review'];
	const DND_CLASSES = [
		'Fighter',
		'Rogue',
		'Wizard',
		'Cleric',
		'Barbarian',
		'Bard',
		'Druid',
		'Monk',
		'Paladin',
		'Ranger',
		'Sorcerer',
		'Warlock',
	];
	const PROVIDERS = ['gemini', 'claude', 'ollama'];
	const CLASS_COLORS: Record<string, string> = {
		Fighter: '#C45C4A',
		Rogue: '#6B8E6B',
		Wizard: '#7B68B8',
		Cleric: '#4A90A4',
		Barbarian: '#C45C4A',
		Bard: '#D4A574',
		Druid: '#6B8E6B',
		Monk: '#B8A896',
		Paladin: '#D4A574',
		Ranger: '#6B8E6B',
		Sorcerer: '#7B68B8',
		Warlock: '#4B0082',
	};

	let currentStep = $state(0);

	// Form fields — intentionally capture initial prop values for mutable form state.
	// eslint-disable-next-line svelte/valid-compile -- initial capture is correct
	const initName = editCharacter?.name ?? '';
	const initClass = editCharacter?.character_class ?? '';
	const initPersonality = editCharacter?.personality ?? '';
	const initProvider = editCharacter?.provider ?? 'gemini';
	const initModel = editCharacter?.model ?? 'gemini-1.5-flash';
	const initColor = editCharacter?.color ?? '#808080';
	const initTokenLimit = editCharacter?.token_limit ?? 4000;

	let name = $state(initName);
	let characterClass = $state(initClass);
	let personality = $state(initPersonality);
	const initBackstory = editCharacter?.backstory ?? '';
	let backstory = $state(initBackstory);
	let provider = $state(initProvider);
	let model = $state(initModel);
	let color = $state(initColor);
	let tokenLimit = $state(initTokenLimit);

	let isEditMode = $derived(editCharacter !== null);

	// Validation
	let nameError = $derived.by(() => {
		if (currentStep === 0 && !name.trim()) return 'Name is required';
		if (name.length > 50) return 'Name must be 50 characters or fewer';
		return null;
	});

	let classError = $derived.by(() => {
		if (currentStep === 0 && !characterClass.trim()) return 'Class is required';
		return null;
	});

	let colorError = $derived.by(() => {
		if (!/^#[0-9A-Fa-f]{6}$/.test(color)) return 'Must be a valid hex color (e.g. #C45C4A)';
		return null;
	});

	let tokenLimitError = $derived.by(() => {
		if (tokenLimit < 1) return 'Token limit must be at least 1';
		if (tokenLimit > 128000) return 'Token limit must be 128,000 or fewer';
		if (!Number.isInteger(tokenLimit)) return 'Token limit must be a whole number';
		return null;
	});

	let modelError = $derived.by(() => {
		if (currentStep === 2 && !model.trim()) return 'Model name is required';
		return null;
	});

	let canAdvance = $derived.by(() => {
		if (currentStep === 0) return !!name.trim() && !!characterClass.trim();
		if (currentStep === 2) return !colorError && !tokenLimitError && !modelError;
		return true;
	});

	function nextStep(): void {
		if (currentStep < STEPS.length - 1 && canAdvance) {
			currentStep++;
		}
	}

	function prevStep(): void {
		if (currentStep > 0) {
			currentStep--;
		}
	}

	function handleSubmit(): void {
		if (saving || !name.trim() || !characterClass.trim() || !model.trim()) return;
		if (colorError || tokenLimitError) return;
		const data: CharacterCreateRequest = {
			name: name.trim(),
			character_class: characterClass.trim(),
			personality: personality.trim() || undefined,
			backstory: backstory.trim() || undefined,
			color,
			provider,
			model: model.trim(),
			token_limit: tokenLimit,
		};
		onSave(data);
	}

	function handleClassSelect(cls: string): void {
		characterClass = cls;
		// Auto-set color to class default if user hasn't customized
		if (color === '#808080' || Object.values(CLASS_COLORS).includes(color)) {
			color = CLASS_COLORS[cls] ?? '#808080';
		}
	}

	function sanitize(text: string): string {
		return text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;');
	}

	function handleKeydown(e: KeyboardEvent): void {
		if (e.key === 'Escape') {
			e.preventDefault();
			onCancel();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="character-creator">
	<!-- Header -->
	<header class="creator-header">
		<h2 class="creator-title">
			{isEditMode ? `Edit ${sanitize(editCharacter?.name ?? '')}` : 'Create Character'}
		</h2>
	</header>

	<!-- Progress bar -->
	<div class="progress-bar" role="progressbar" aria-valuenow={currentStep + 1} aria-valuemin={1} aria-valuemax={STEPS.length}>
		{#each STEPS as step, i (step)}
			<div class="progress-step" class:active={i === currentStep} class:completed={i < currentStep}>
				<div class="step-indicator">{i < currentStep ? '\u2713' : i + 1}</div>
				<span class="step-label">{step}</span>
			</div>
			{#if i < STEPS.length - 1}
				<div class="step-connector" class:completed={i < currentStep}></div>
			{/if}
		{/each}
	</div>

	<!-- Step content -->
	<div class="step-content">
		<!-- Step 0: Identity -->
		{#if currentStep === 0}
			<div class="form-section">
				<label class="form-label" for="char-name">
					Character Name <span class="required">*</span>
				</label>
				<input
					id="char-name"
					type="text"
					class="form-input"
					class:error={nameError && name.length > 0}
					placeholder="e.g., Thorin, Shadowmere, Elara..."
					bind:value={name}
					maxlength={50}
					disabled={saving}
				/>
				{#if nameError && name.length > 0}
					<p class="field-error">{nameError}</p>
				{/if}
			</div>

			<fieldset class="form-section form-fieldset">
				<legend class="form-label">
					Character Class <span class="required">*</span>
				</legend>
				<div class="class-grid" role="group" aria-label="Character class selection">
					{#each DND_CLASSES as cls (cls)}
						<button
							class="class-chip"
							class:selected={characterClass === cls}
							style="--chip-color: {CLASS_COLORS[cls] ?? '#808080'}"
							onclick={() => handleClassSelect(cls)}
							disabled={saving}
							type="button"
						>
							{cls}
						</button>
					{/each}
				</div>
				{#if characterClass}
					<p class="class-selection">
						Selected: <span style="color: {CLASS_COLORS[characterClass] ?? '#808080'}; font-weight: 600">{characterClass}</span>
					</p>
				{/if}
			</fieldset>

		<!-- Step 1: Personality -->
		{:else if currentStep === 1}
			<div class="form-section">
				<label class="form-label" for="char-personality">Personality Traits</label>
				<textarea
					id="char-personality"
					class="form-textarea"
					placeholder="Describe your character's personality, mannerisms, and speaking style..."
					bind:value={personality}
					rows={4}
					maxlength={2000}
					disabled={saving}
				></textarea>
				<p class="field-hint">{personality.length}/2000 characters</p>
			</div>

			<div class="form-section">
				<label class="form-label" for="char-backstory">Backstory</label>
				<textarea
					id="char-backstory"
					class="form-textarea"
					placeholder="A brief backstory for your character (optional)..."
					bind:value={backstory}
					rows={5}
					maxlength={5000}
					disabled={saving}
				></textarea>
				<p class="field-hint">{backstory.length}/5000 characters</p>
			</div>

		<!-- Step 2: Configuration -->
		{:else if currentStep === 2}
			<div class="form-section">
				<label class="form-label" for="char-provider">LLM Provider</label>
				<select id="char-provider" class="form-select" bind:value={provider} disabled={saving}>
					{#each PROVIDERS as p (p)}
						<option value={p}>{p}</option>
					{/each}
				</select>
			</div>

			<div class="form-section">
				<label class="form-label" for="char-model">Model Name</label>
				<input
					id="char-model"
					type="text"
					class="form-input"
					class:error={!!modelError && model.length === 0}
					placeholder="e.g., gemini-1.5-flash, claude-3-haiku-20240307"
					bind:value={model}
					disabled={saving}
				/>
				{#if modelError && model.length === 0}
					<p class="field-error">{modelError}</p>
				{/if}
			</div>

			<div class="form-row">
				<div class="form-section form-half">
					<label class="form-label" for="char-color">Color</label>
					<div class="color-input-wrapper">
						<input
							id="char-color"
							type="color"
							class="form-color"
							bind:value={color}
							disabled={saving}
						/>
						<input
							type="text"
							class="form-input color-text"
							class:error={!!colorError}
							bind:value={color}
							placeholder="#808080"
							maxlength={7}
							disabled={saving}
						/>
					</div>
					{#if colorError}
						<p class="field-error">{colorError}</p>
					{/if}
				</div>

				<div class="form-section form-half">
					<label class="form-label" for="char-tokens">Token Limit</label>
					<input
						id="char-tokens"
						type="number"
						class="form-input"
						class:error={!!tokenLimitError}
						bind:value={tokenLimit}
						min={1}
						max={128000}
						disabled={saving}
					/>
					{#if tokenLimitError}
						<p class="field-error">{tokenLimitError}</p>
					{/if}
				</div>
			</div>

		<!-- Step 3: Review -->
		{:else if currentStep === 3}
			<div class="review-card" style="--review-accent: {color}">
				<div class="review-accent"></div>
				<div class="review-body">
					<h3 class="review-name">{sanitize(name || 'Unnamed')}</h3>
					<p class="review-class" style="color: {color}">
						{sanitize(characterClass || 'No class selected')}
					</p>

					{#if personality.trim()}
						<div class="review-section">
							<h4 class="review-label">Personality</h4>
							<p class="review-text">{sanitize(personality)}</p>
						</div>
					{/if}

					{#if backstory.trim()}
						<div class="review-section">
							<h4 class="review-label">Backstory</h4>
							<p class="review-text">{sanitize(backstory)}</p>
						</div>
					{/if}

					<div class="review-section">
						<h4 class="review-label">Configuration</h4>
						<div class="review-config">
							<span><strong>Provider:</strong> {sanitize(provider)}</span>
							<span><strong>Model:</strong> {sanitize(model)}</span>
							<span><strong>Tokens:</strong> {tokenLimit.toLocaleString()}</span>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>

	<!-- Error display -->
	{#if error}
		<p class="submit-error" role="alert">{error}</p>
	{/if}

	<!-- Navigation buttons -->
	<div class="creator-nav">
		<div class="nav-left">
			{#if currentStep > 0}
				<button class="btn btn-secondary" onclick={prevStep} disabled={saving} type="button">
					Previous
				</button>
			{/if}
		</div>

		<div class="nav-right">
			<button class="btn btn-secondary" onclick={onCancel} disabled={saving} type="button">
				Cancel
			</button>

			{#if currentStep < STEPS.length - 1}
				<button
					class="btn btn-primary"
					onclick={nextStep}
					disabled={!canAdvance || saving}
					type="button"
				>
					Next
				</button>
			{:else}
				<button
					class="btn btn-primary"
					onclick={handleSubmit}
					disabled={!name.trim() || !characterClass.trim() || saving}
					type="button"
				>
					{#if saving}
						<span class="spinner" aria-hidden="true"></span>
						Saving...
					{:else}
						{isEditMode ? 'Save Changes' : 'Create Character'}
					{/if}
				</button>
			{/if}
		</div>
	</div>
</div>

<style>
	.character-creator {
		max-width: var(--max-content-width);
		margin: 0 auto;
	}

	/* Header */
	.creator-header {
		margin-bottom: var(--space-lg);
	}

	.creator-title {
		font-family: var(--font-narrative);
		font-size: 28px;
		font-weight: 600;
		color: var(--color-dm);
		margin: 0;
	}

	/* Progress bar */
	.progress-bar {
		display: flex;
		align-items: center;
		margin-bottom: var(--space-xl);
		gap: 0;
	}

	.progress-step {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		flex-shrink: 0;
	}

	.step-indicator {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-ui);
		font-size: 12px;
		font-weight: 600;
		background: var(--bg-message);
		color: var(--text-secondary);
		border: 2px solid rgba(184, 168, 150, 0.2);
		transition:
			background var(--transition-fast),
			color var(--transition-fast),
			border-color var(--transition-fast);
	}

	.progress-step.active .step-indicator {
		background: var(--accent-warm);
		color: var(--bg-primary);
		border-color: var(--accent-warm);
	}

	.progress-step.completed .step-indicator {
		background: var(--color-success);
		color: var(--text-primary);
		border-color: var(--color-success);
	}

	.step-label {
		font-family: var(--font-ui);
		font-size: 11px;
		color: var(--text-secondary);
		white-space: nowrap;
	}

	.progress-step.active .step-label {
		color: var(--accent-warm);
		font-weight: 600;
	}

	.step-connector {
		flex: 1;
		height: 2px;
		background: rgba(184, 168, 150, 0.2);
		margin: 0 var(--space-xs);
		margin-bottom: 18px;
		transition: background var(--transition-fast);
	}

	.step-connector.completed {
		background: var(--color-success);
	}

	/* Step content */
	.step-content {
		background: var(--bg-secondary);
		border-radius: var(--border-radius-md);
		padding: var(--space-lg);
		margin-bottom: var(--space-lg);
		min-height: 200px;
	}

	/* Form elements */
	.form-section {
		margin-bottom: var(--space-lg);
	}

	.form-section:last-child {
		margin-bottom: 0;
	}

	.form-fieldset {
		border: none;
		padding: 0;
		margin: 0 0 var(--space-lg) 0;
	}

	.form-label {
		display: block;
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: var(--space-xs);
	}

	.required {
		color: var(--color-error);
	}

	.form-input,
	.form-textarea,
	.form-select {
		width: 100%;
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm) var(--space-md);
		font-family: var(--font-ui);
		font-size: var(--text-ui);
	}

	.form-input:focus,
	.form-textarea:focus,
	.form-select:focus {
		outline: 2px solid var(--accent-warm);
		outline-offset: 1px;
		border-color: transparent;
	}

	.form-input::placeholder,
	.form-textarea::placeholder {
		color: var(--text-secondary);
		opacity: 0.6;
	}

	.form-input.error {
		border-color: var(--color-error);
	}

	.form-input:disabled,
	.form-textarea:disabled,
	.form-select:disabled {
		opacity: 0.5;
	}

	.form-textarea {
		resize: vertical;
		min-height: 80px;
	}

	.form-select {
		cursor: pointer;
	}

	.form-row {
		display: flex;
		gap: var(--space-md);
	}

	.form-half {
		flex: 1;
	}

	.field-error {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--color-error);
		margin-top: var(--space-xs);
	}

	.field-hint {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
		margin-top: var(--space-xs);
	}

	/* Class grid */
	.class-grid {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-sm);
	}

	.class-chip {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 500;
		padding: 6px 14px;
		border-radius: 20px;
		border: 1px solid rgba(184, 168, 150, 0.2);
		background: var(--bg-primary);
		color: var(--text-secondary);
		cursor: pointer;
		transition:
			background var(--transition-fast),
			color var(--transition-fast),
			border-color var(--transition-fast);
	}

	.class-chip:hover {
		border-color: var(--chip-color);
		color: var(--chip-color);
	}

	.class-chip.selected {
		background: var(--chip-color);
		color: var(--bg-primary);
		border-color: var(--chip-color);
		font-weight: 600;
	}

	.class-chip:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.class-chip:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.class-selection {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-secondary);
		margin-top: var(--space-sm);
	}

	/* Color input */
	.color-input-wrapper {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
	}

	.form-color {
		width: 40px;
		height: 36px;
		padding: 0;
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		background: transparent;
		cursor: pointer;
		flex-shrink: 0;
	}

	.color-text {
		flex: 1;
		font-family: var(--font-mono);
	}

	/* Review card */
	.review-card {
		background: var(--bg-primary);
		border-radius: var(--border-radius-md);
		overflow: hidden;
	}

	.review-accent {
		height: 4px;
		background: var(--review-accent);
	}

	.review-body {
		padding: var(--space-lg);
	}

	.review-name {
		font-family: var(--font-narrative);
		font-size: 22px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0 0 var(--space-xs) 0;
	}

	.review-class {
		font-family: var(--font-ui);
		font-size: 14px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		margin: 0 0 var(--space-md) 0;
	}

	.review-section {
		margin-top: var(--space-md);
	}

	.review-label {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.06em;
		margin: 0 0 var(--space-xs) 0;
	}

	.review-text {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-primary);
		line-height: 1.5;
		margin: 0;
		white-space: pre-wrap;
	}

	.review-config {
		display: flex;
		flex-wrap: wrap;
		gap: var(--space-md);
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-primary);
	}

	/* Error */
	.submit-error {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--color-error);
		background: rgba(196, 92, 74, 0.1);
		border: 1px solid rgba(196, 92, 74, 0.3);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm) var(--space-md);
		margin-bottom: var(--space-md);
	}

	/* Navigation */
	.creator-nav {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.nav-left,
	.nav-right {
		display: flex;
		gap: var(--space-sm);
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

	/* Spinner */
	.spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid currentColor;
		border-right-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* Responsive */
	@media (max-width: 768px) {
		.creator-title {
			font-size: 24px;
		}

		.progress-bar {
			flex-wrap: nowrap;
			overflow-x: auto;
		}

		.step-label {
			font-size: 10px;
		}

		.form-row {
			flex-direction: column;
		}

		.creator-nav {
			flex-direction: column;
			gap: var(--space-sm);
		}

		.nav-left,
		.nav-right {
			width: 100%;
			justify-content: stretch;
		}

		.nav-right .btn,
		.nav-left .btn {
			flex: 1;
			justify-content: center;
		}
	}
</style>
