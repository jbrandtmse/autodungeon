<script lang="ts">
	import { gameState, connectionStatus, sendCommand } from '$lib/stores';
	import type { Whisper } from '$lib/types';

	const humanActive = $derived($gameState?.human_active ?? false);
	const notConnected = $derived($connectionStatus !== 'connected');

	let whisperText = $state('');
	let showConfirmation = $state(false);
	let confirmTimer: ReturnType<typeof setTimeout> | null = null;

	// Derive whisper data from game state agent_secrets
	const whispers = $derived.by((): Whisper[] => {
		const secrets = $gameState?.agent_secrets;
		if (!secrets) return [];
		const all: Whisper[] = [];
		for (const agentSecrets of Object.values(secrets)) {
			if (agentSecrets?.whispers && Array.isArray(agentSecrets.whispers)) {
				for (const w of agentSecrets.whispers) {
					all.push(w as Whisper);
				}
			}
		}
		return all;
	});

	const whispersByCharacter = $derived.by((): Record<string, Whisper[]> => {
		const grouped: Record<string, Whisper[]> = {};
		for (const w of whispers) {
			const key = w.to_agent;
			if (!grouped[key]) grouped[key] = [];
			grouped[key].push(w);
		}
		return grouped;
	});

	// Cleanup timer
	$effect(() => {
		return () => {
			if (confirmTimer) {
				clearTimeout(confirmTimer);
				confirmTimer = null;
			}
		};
	});

	function handleSendWhisper(): void {
		const trimmed = whisperText.trim();
		if (!trimmed) return;
		sendCommand({ type: 'whisper', content: trimmed });
		whisperText = '';
		showConfirmation = true;
		if (confirmTimer) clearTimeout(confirmTimer);
		confirmTimer = setTimeout(() => {
			showConfirmation = false;
		}, 3000);
	}

	function handleKeydown(event: KeyboardEvent): void {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSendWhisper();
		}
	}
</script>

<div class="whisper-panel">
	{#if !humanActive}
		<div class="whisper-input-section">
			<h3 class="section-heading">Whisper to DM</h3>
			<textarea
				class="whisper-input"
				bind:value={whisperText}
				placeholder="Ask the DM something privately..."
				rows={2}
				disabled={notConnected}
				onkeydown={handleKeydown}
			></textarea>
			<button
				class="whisper-btn"
				onclick={handleSendWhisper}
				disabled={!whisperText.trim() || notConnected}
			>
				Send Whisper
			</button>
			{#if showConfirmation}
				<p class="whisper-confirmation">Whisper sent - the DM will respond privately</p>
			{/if}
		</div>
	{/if}

	{#if whispers.length > 0}
		<details class="whisper-history">
			<summary class="whisper-history-summary">Whisper History</summary>
			<div class="whisper-history-content">
				{#each Object.entries(whispersByCharacter) as [characterName, charWhispers] (characterName)}
					<div class="whisper-group">
						<h4 class="whisper-character">{characterName}</h4>
						{#each charWhispers as whisper (whisper.id)}
							<div class="whisper-entry" class:revealed={whisper.revealed}>
								<span class="whisper-badge" class:active={!whisper.revealed} class:revealed-badge={whisper.revealed}>
									{whisper.revealed ? 'Revealed' : 'Active'}
								</span>
								<span class="whisper-turn">
									Turn {whisper.turn_created}
									{#if whisper.revealed && whisper.turn_revealed !== null}
										(Revealed turn {whisper.turn_revealed})
									{/if}
								</span>
								<p class="whisper-content">{whisper.content}</p>
							</div>
						{/each}
					</div>
				{/each}
			</div>
		</details>
	{/if}
</div>

<style>
	.whisper-panel {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.section-heading {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		margin-bottom: var(--space-xs);
	}

	.whisper-input-section {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
	}

	.whisper-input {
		width: 100%;
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid var(--text-secondary);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm);
		font-family: var(--font-ui);
		font-size: var(--text-system);
		resize: vertical;
		min-height: 48px;
		transition: border-color var(--transition-fast);
	}

	.whisper-input:focus {
		outline: none;
		border-color: var(--accent-warm);
	}

	.whisper-btn {
		align-self: flex-end;
		padding: 6px 14px;
		background: transparent;
		color: var(--text-primary);
		border: 1px solid var(--text-secondary);
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.whisper-btn:hover:not(:disabled) {
		background: var(--bg-message);
		border-color: var(--text-primary);
	}

	.whisper-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.whisper-confirmation {
		font-family: var(--font-ui);
		font-size: 12px;
		color: var(--color-success);
		text-align: center;
		padding: var(--space-xs) 0;
		animation: fade-in 200ms ease-out;
	}

	@keyframes fade-in {
		from { opacity: 0; transform: translateY(-4px); }
		to { opacity: 1; transform: translateY(0); }
	}

	/* Whisper History */
	.whisper-history {
		font-family: var(--font-ui);
	}

	.whisper-history-summary {
		font-size: var(--text-system);
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		cursor: pointer;
		padding: var(--space-xs) 0;
		list-style: none;
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.whisper-history-summary::-webkit-details-marker {
		display: none;
	}

	.whisper-history-summary::before {
		content: '\25B6';
		font-size: 8px;
		color: var(--text-secondary);
		transition: transform var(--transition-fast);
	}

	.whisper-history[open] .whisper-history-summary::before {
		transform: rotate(90deg);
	}

	.whisper-history-content {
		padding: var(--space-sm) 0;
		padding-left: 14px;
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}

	.whisper-group {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
	}

	.whisper-character {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
		text-transform: capitalize;
	}

	.whisper-entry {
		padding: var(--space-xs) var(--space-sm);
		border-left: 2px solid var(--accent-warm);
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.whisper-entry.revealed {
		opacity: 0.6;
		border-left-color: var(--color-success);
	}

	.whisper-badge {
		font-size: 10px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 1px 6px;
		border-radius: 8px;
		width: fit-content;
	}

	.whisper-badge.active {
		background: rgba(232, 168, 73, 0.2);
		color: var(--accent-warm);
	}

	.whisper-badge.revealed-badge {
		background: rgba(107, 142, 107, 0.2);
		color: var(--color-success);
	}

	.whisper-turn {
		font-size: 11px;
		color: var(--text-secondary);
	}

	.whisper-content {
		font-size: 12px;
		color: var(--text-primary);
		line-height: 1.4;
	}
</style>
