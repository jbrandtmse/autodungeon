<script lang="ts">
	const PROVIDERS = ['gemini', 'anthropic', 'ollama'] as const;
	type Provider = (typeof PROVIDERS)[number];

	const PROVIDER_DISPLAY: Record<Provider, string> = {
		gemini: 'Gemini',
		anthropic: 'Claude',
		ollama: 'Ollama',
	};

	const MODELS_BY_PROVIDER: Record<Provider, string[]> = {
		gemini: [
			'gemini-3-flash-preview',
			'gemini-1.5-pro',
			'gemini-2.0-flash',
			'gemini-2.5-flash-preview-05-20',
			'gemini-2.5-pro-preview-05-06',
			'gemini-3-pro-preview',
		],
		anthropic: [
			'claude-3-haiku-20240307',
			'claude-3-5-sonnet-20241022',
			'claude-sonnet-4-20250514',
		],
		ollama: ['llama3', 'mistral', 'phi3'],
	};

	interface Props {
		dmProvider: string;
		dmModel: string;
		dmTokenLimit: number;
		summarizerProvider: string;
		summarizerModel: string;
		summarizerTokenLimit: number;
		extractorProvider: string;
		extractorModel: string;
		extractorTokenLimit: number;
		onDmProviderChange: (provider: string) => void;
		onDmModelChange: (model: string) => void;
		onDmTokenLimitChange: (limit: number) => void;
		onSummarizerProviderChange: (provider: string) => void;
		onSummarizerModelChange: (model: string) => void;
		onSummarizerTokenLimitChange: (limit: number) => void;
		onExtractorProviderChange: (provider: string) => void;
		onExtractorModelChange: (model: string) => void;
		onExtractorTokenLimitChange: (limit: number) => void;
	}

	let {
		dmProvider,
		dmModel,
		dmTokenLimit,
		summarizerProvider,
		summarizerModel,
		summarizerTokenLimit,
		extractorProvider,
		extractorModel,
		extractorTokenLimit,
		onDmProviderChange,
		onDmModelChange,
		onDmTokenLimitChange,
		onSummarizerProviderChange,
		onSummarizerModelChange,
		onSummarizerTokenLimitChange,
		onExtractorProviderChange,
		onExtractorModelChange,
		onExtractorTokenLimitChange,
	}: Props = $props();

	function getModelsForProvider(provider: string): string[] {
		const p = provider.toLowerCase() as Provider;
		return MODELS_BY_PROVIDER[p] ?? MODELS_BY_PROVIDER.gemini;
	}

	function handleProviderChange(
		currentModel: string,
		newProvider: string,
		onProviderChange: (p: string) => void,
		onModelChange: (m: string) => void,
	): void {
		onProviderChange(newProvider);
		const models = getModelsForProvider(newProvider);
		// Reset model to first available if current model not in new provider's list
		if (!models.includes(currentModel)) {
			onModelChange(models[0] ?? '');
		}
	}

	function handleTokenLimitInput(value: string, onChange: (limit: number) => void): void {
		const num = parseInt(value, 10);
		if (!isNaN(num) && num >= 1000) {
			onChange(num);
		}
	}

	let dmModels = $derived(getModelsForProvider(dmProvider));
	let summarizerModels = $derived(getModelsForProvider(summarizerProvider));
	let extractorModels = $derived(getModelsForProvider(extractorProvider));
</script>

<div class="models-tab">
	<h4 class="section-header">Agent Models</h4>
	<p class="section-description">
		Select which AI provider and model powers each agent role.
		Changes take effect on the next turn.
	</p>

	<!-- Dungeon Master -->
	<div class="agent-row">
		<div class="agent-info">
			<span class="agent-name dm">Dungeon Master</span>
			<span class="agent-help">Model used for game narration and NPC control</span>
		</div>
		<div class="agent-controls">
			<select
				class="model-select provider-select"
				value={dmProvider}
				onchange={(e) =>
					handleProviderChange(
						dmModel,
						(e.target as HTMLSelectElement).value,
						onDmProviderChange,
						onDmModelChange,
					)}
				aria-label="DM provider"
			>
				{#each PROVIDERS as p}
					<option value={p}>{PROVIDER_DISPLAY[p]}</option>
				{/each}
			</select>
			<select
				class="model-select model-name-select"
				value={dmModel}
				onchange={(e) => onDmModelChange((e.target as HTMLSelectElement).value)}
				aria-label="DM model"
			>
				{#each dmModels as m}
					<option value={m}>{m}</option>
				{/each}
				{#if !dmModels.includes(dmModel) && dmModel}
					<option value={dmModel}>{dmModel}</option>
				{/if}
			</select>
		</div>
		<div class="token-limit-row">
			<label class="token-label" for="dm-token-limit">Token limit</label>
			<input
				id="dm-token-limit"
				type="number"
				class="token-input"
				min="1000"
				step="1000"
				value={dmTokenLimit}
				oninput={(e) => handleTokenLimitInput((e.target as HTMLInputElement).value, onDmTokenLimitChange)}
				aria-label="DM token limit"
			/>
		</div>
	</div>

	<hr class="model-divider" />

	<!-- Summarizer -->
	<div class="agent-row">
		<div class="agent-info">
			<span class="agent-name summarizer">Summarizer</span>
			<span class="agent-help">Model used for memory compression</span>
		</div>
		<div class="agent-controls">
			<select
				class="model-select provider-select"
				value={summarizerProvider}
				onchange={(e) =>
					handleProviderChange(
						summarizerModel,
						(e.target as HTMLSelectElement).value,
						onSummarizerProviderChange,
						onSummarizerModelChange,
					)}
				aria-label="Summarizer provider"
			>
				{#each PROVIDERS as p}
					<option value={p}>{PROVIDER_DISPLAY[p]}</option>
				{/each}
			</select>
			<select
				class="model-select model-name-select"
				value={summarizerModel}
				onchange={(e) => onSummarizerModelChange((e.target as HTMLSelectElement).value)}
				aria-label="Summarizer model"
			>
				{#each summarizerModels as m}
					<option value={m}>{m}</option>
				{/each}
				{#if !summarizerModels.includes(summarizerModel) && summarizerModel}
					<option value={summarizerModel}>{summarizerModel}</option>
				{/if}
			</select>
		</div>
		<div class="token-limit-row">
			<label class="token-label" for="summarizer-token-limit">Token limit</label>
			<input
				id="summarizer-token-limit"
				type="number"
				class="token-input"
				min="1000"
				step="1000"
				value={summarizerTokenLimit}
				oninput={(e) => handleTokenLimitInput((e.target as HTMLInputElement).value, onSummarizerTokenLimitChange)}
				aria-label="Summarizer token limit"
			/>
		</div>
	</div>

	<hr class="model-divider" />

	<!-- Extractor -->
	<div class="agent-row">
		<div class="agent-info">
			<span class="agent-name extractor">Extractor</span>
			<span class="agent-help">Model used for narrative element extraction</span>
		</div>
		<div class="agent-controls">
			<select
				class="model-select provider-select"
				value={extractorProvider}
				onchange={(e) =>
					handleProviderChange(
						extractorModel,
						(e.target as HTMLSelectElement).value,
						onExtractorProviderChange,
						onExtractorModelChange,
					)}
				aria-label="Extractor provider"
			>
				{#each PROVIDERS as p}
					<option value={p}>{PROVIDER_DISPLAY[p]}</option>
				{/each}
			</select>
			<select
				class="model-select model-name-select"
				value={extractorModel}
				onchange={(e) => onExtractorModelChange((e.target as HTMLSelectElement).value)}
				aria-label="Extractor model"
			>
				{#each extractorModels as m}
					<option value={m}>{m}</option>
				{/each}
				{#if !extractorModels.includes(extractorModel) && extractorModel}
					<option value={extractorModel}>{extractorModel}</option>
				{/if}
			</select>
		</div>
		<div class="token-limit-row">
			<label class="token-label" for="extractor-token-limit">Token limit</label>
			<input
				id="extractor-token-limit"
				type="number"
				class="token-input"
				min="1000"
				step="1000"
				value={extractorTokenLimit}
				oninput={(e) => handleTokenLimitInput((e.target as HTMLInputElement).value, onExtractorTokenLimitChange)}
				aria-label="Extractor token limit"
			/>
		</div>
	</div>
</div>

<style>
	.models-tab {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.section-header {
		font-family: var(--font-ui);
		font-size: 15px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0 0 var(--space-xs) 0;
	}

	.section-description {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
		margin: 0 0 var(--space-md) 0;
		line-height: 1.4;
	}

	.agent-row {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
		padding: var(--space-sm) 0;
	}

	.agent-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.agent-name {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		font-weight: 600;
		color: var(--text-primary);
	}

	.agent-name.dm {
		color: var(--accent-warm);
	}

	.agent-name.summarizer,
	.agent-name.extractor {
		color: var(--color-info);
	}

	.agent-help {
		font-family: var(--font-ui);
		font-size: 12px;
		color: var(--text-secondary);
	}

	.agent-controls {
		display: flex;
		gap: var(--space-sm);
	}

	.model-select {
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		padding: 6px 8px;
		font-family: var(--font-ui);
		font-size: var(--text-system);
		cursor: pointer;
		transition: border-color var(--transition-fast);
	}

	.model-select:hover {
		border-color: var(--accent-warm);
	}

	.model-select:focus {
		outline: 2px solid var(--accent-warm);
		outline-offset: 1px;
		border-color: transparent;
	}

	.model-select option {
		background: var(--bg-secondary);
		color: var(--text-primary);
	}

	.provider-select {
		flex: 0 0 110px;
	}

	.model-name-select {
		flex: 1;
		min-width: 0;
	}

	.token-limit-row {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
	}

	.token-label {
		font-family: var(--font-ui);
		font-size: 12px;
		color: var(--text-secondary);
		flex-shrink: 0;
	}

	.token-input {
		width: 100px;
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		padding: 4px 8px;
		font-family: var(--font-mono);
		font-size: var(--text-system);
	}

	.token-input:focus {
		outline: 2px solid var(--accent-warm);
		outline-offset: 1px;
		border-color: transparent;
	}

	.model-divider {
		border: none;
		border-top: 1px solid rgba(184, 168, 150, 0.1);
		margin: var(--space-xs) 0;
	}
</style>
