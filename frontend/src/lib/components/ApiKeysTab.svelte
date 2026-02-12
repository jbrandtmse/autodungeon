<script lang="ts">
	interface Props {
		googleKey: string;
		anthropicKey: string;
		ollamaUrl: string;
		onGoogleKeyChange: (value: string) => void;
		onAnthropicKeyChange: (value: string) => void;
		onOllamaUrlChange: (value: string) => void;
	}

	let {
		googleKey,
		anthropicKey,
		ollamaUrl,
		onGoogleKeyChange,
		onAnthropicKeyChange,
		onOllamaUrlChange,
	}: Props = $props();

	function getStatus(value: string, isUrl: boolean = false): 'configured' | 'unconfigured' {
		if (isUrl) {
			return value.trim().length > 0 ? 'configured' : 'unconfigured';
		}
		return value.trim().length > 0 ? 'configured' : 'unconfigured';
	}

	let googleStatus = $derived(getStatus(googleKey));
	let anthropicStatus = $derived(getStatus(anthropicKey));
	let ollamaStatus = $derived(getStatus(ollamaUrl, true));
</script>

<div class="api-keys-tab">
	<h4 class="section-header">Provider API Keys</h4>
	<p class="section-description">
		API keys are stored in your browser only and are not sent to the autodungeon server.
	</p>

	<!-- Google (Gemini) -->
	<div class="key-field">
		<div class="key-header">
			<label class="key-label" for="google-key">Google (Gemini)</label>
			<span class="key-status" class:configured={googleStatus === 'configured'}>
				{#if googleStatus === 'configured'}
					<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
						<circle cx="8" cy="8" r="6" fill="var(--color-success)" />
						<path d="M5 8l2 2 4-4" stroke="var(--bg-primary)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round" />
					</svg>
					Configured
				{:else}
					<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
						<circle cx="8" cy="8" r="6" fill="var(--text-secondary)" opacity="0.4" />
					</svg>
					Not configured
				{/if}
			</span>
		</div>
		<input
			id="google-key"
			type="password"
			class="key-input"
			placeholder="Enter Google API key..."
			value={googleKey}
			oninput={(e) => onGoogleKeyChange((e.target as HTMLInputElement).value)}
			autocomplete="off"
			spellcheck="false"
		/>
	</div>

	<hr class="key-divider" />

	<!-- Anthropic (Claude) -->
	<div class="key-field">
		<div class="key-header">
			<label class="key-label" for="anthropic-key">Anthropic (Claude)</label>
			<span class="key-status" class:configured={anthropicStatus === 'configured'}>
				{#if anthropicStatus === 'configured'}
					<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
						<circle cx="8" cy="8" r="6" fill="var(--color-success)" />
						<path d="M5 8l2 2 4-4" stroke="var(--bg-primary)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round" />
					</svg>
					Configured
				{:else}
					<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
						<circle cx="8" cy="8" r="6" fill="var(--text-secondary)" opacity="0.4" />
					</svg>
					Not configured
				{/if}
			</span>
		</div>
		<input
			id="anthropic-key"
			type="password"
			class="key-input"
			placeholder="Enter Anthropic API key..."
			value={anthropicKey}
			oninput={(e) => onAnthropicKeyChange((e.target as HTMLInputElement).value)}
			autocomplete="off"
			spellcheck="false"
		/>
	</div>

	<hr class="key-divider" />

	<!-- Ollama -->
	<div class="key-field">
		<div class="key-header">
			<label class="key-label" for="ollama-url">Ollama (Local)</label>
			<span class="key-status" class:configured={ollamaStatus === 'configured'}>
				{#if ollamaStatus === 'configured'}
					<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
						<circle cx="8" cy="8" r="6" fill="var(--color-success)" />
						<path d="M5 8l2 2 4-4" stroke="var(--bg-primary)" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round" />
					</svg>
					Configured
				{:else}
					<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
						<circle cx="8" cy="8" r="6" fill="var(--text-secondary)" opacity="0.4" />
					</svg>
					Not configured
				{/if}
			</span>
		</div>
		<input
			id="ollama-url"
			type="text"
			class="key-input"
			placeholder="http://localhost:11434"
			value={ollamaUrl}
			oninput={(e) => onOllamaUrlChange((e.target as HTMLInputElement).value)}
			autocomplete="off"
			spellcheck="false"
		/>
		<p class="key-help">Base URL for your local Ollama instance</p>
	</div>
</div>

<style>
	.api-keys-tab {
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

	.key-field {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
	}

	.key-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.key-label {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		font-weight: 500;
		color: var(--text-primary);
	}

	.key-status {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
	}

	.key-status.configured {
		color: var(--color-success);
	}

	.key-input {
		width: 100%;
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm) var(--space-md);
		font-family: var(--font-mono);
		font-size: var(--text-system);
	}

	.key-input:focus {
		outline: 2px solid var(--accent-warm);
		outline-offset: 1px;
		border-color: transparent;
	}

	.key-input::placeholder {
		color: var(--text-secondary);
		opacity: 0.5;
		font-family: var(--font-ui);
	}

	.key-help {
		font-family: var(--font-ui);
		font-size: 12px;
		color: var(--text-secondary);
		margin: 0;
	}

	.key-divider {
		border: none;
		border-top: 1px solid rgba(184, 168, 150, 0.1);
		margin: var(--space-sm) 0;
	}
</style>
