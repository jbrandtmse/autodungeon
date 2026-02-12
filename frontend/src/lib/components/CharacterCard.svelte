<script lang="ts">
	import { gameState, isThinking, connectionStatus, sendCommand, uiState } from '$lib/stores';

	let {
		agentKey,
		name,
		characterClass,
		classSlug,
		isControlled = false,
		isGenerating = false,
		hp,
	}: {
		agentKey: string;
		name: string;
		characterClass: string;
		classSlug: string;
		isControlled: boolean;
		isGenerating: boolean;
		hp?: { current: number; max: number; temp: number };
	} = $props();

	const humanActive = $derived($gameState?.human_active ?? false);
	const notConnected = $derived($connectionStatus !== 'connected');
	const buttonsDisabled = $derived($isThinking || notConnected);

	const hpPercent = $derived(
		hp && hp.max > 0 ? Math.max(0, Math.min(100, (hp.current / hp.max) * 100)) : hp ? 0 : null
	);

	const hpColorClass = $derived.by(() => {
		if (hpPercent === null) return '';
		if (hpPercent > 50) return 'hp-green';
		if (hpPercent > 25) return 'hp-amber';
		return 'hp-red';
	});

	function handleDropInRelease(): void {
		if (isControlled) {
			sendCommand({ type: 'release_control' });
		} else {
			// Quick-switch: backend handles implicit release
			sendCommand({ type: 'drop_in', character: agentKey });
		}
	}

	function handleViewSheet(): void {
		uiState.update((s) => ({ ...s, characterSheetName: name }));
	}
</script>

<div
	class="character-card {classSlug}"
	class:controlled={isControlled}
	role="listitem"
>
	<div class="card-header">
		<div class="card-identity">
			<span class="char-name {classSlug}">{name}</span>
			<span class="char-class">{characterClass}</span>
		</div>
		<span class="status-badge" class:you={isControlled} class:generating={isGenerating}>
			{#if isControlled}
				You
			{:else if isGenerating}
				<span class="thinking-dots" aria-label="Thinking">
					<span class="dot"></span><span class="dot"></span><span class="dot"></span>
				</span>
			{:else}
				AI
			{/if}
		</span>
	</div>

	{#if hp && hpPercent !== null}
		<div
			class="hp-bar-container"
			role="meter"
			aria-label="Hit points for {name}"
			aria-valuenow={hp.current}
			aria-valuemin={0}
			aria-valuemax={hp.max}
		>
			<div class="hp-bar-fill {hpColorClass}" style="width: {hpPercent}%"></div>
			<span class="hp-text">{hp.current}/{hp.max} HP</span>
		</div>
	{/if}

	<div class="card-actions">
		<button
			class="drop-in-btn {classSlug}"
			class:release={isControlled}
			onclick={handleDropInRelease}
			disabled={buttonsDisabled}
			aria-label={isControlled ? `Release control of ${name}` : `Drop in as ${name}`}
		>
			{isControlled ? 'Release' : 'Drop In'}
		</button>
		<button
			class="view-sheet-btn"
			onclick={handleViewSheet}
			aria-label="View character sheet for {name}"
		>
			Sheet
		</button>
	</div>
</div>

<style>
	.character-card {
		background: var(--bg-secondary);
		border-radius: var(--border-radius-md);
		border-left: 3px solid var(--text-secondary);
		padding: 10px 12px;
		display: flex;
		flex-direction: column;
		gap: 8px;
		transition: all var(--transition-fast);
	}

	.character-card.controlled {
		background: var(--bg-message);
		border-left-width: 4px;
		box-shadow: 0 0 12px rgba(232, 168, 73, 0.2);
	}

	/* Character class border colors */
	.character-card.fighter { border-left-color: var(--color-fighter); }
	.character-card.rogue { border-left-color: var(--color-rogue); }
	.character-card.wizard { border-left-color: var(--color-wizard); }
	.character-card.cleric { border-left-color: var(--color-cleric); }

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-sm);
	}

	.card-identity {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}

	.char-name {
		font-family: var(--font-ui);
		font-size: 14px;
		font-weight: 600;
		color: var(--text-secondary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.char-name.fighter { color: var(--color-fighter); }
	.char-name.rogue { color: var(--color-rogue); }
	.char-name.wizard { color: var(--color-wizard); }
	.char-name.cleric { color: var(--color-cleric); }

	.char-class {
		font-family: var(--font-ui);
		font-size: 13px;
		color: var(--text-secondary);
	}

	/* Status badge */
	.status-badge {
		flex-shrink: 0;
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 600;
		padding: 2px 8px;
		border-radius: 10px;
		background: rgba(184, 168, 150, 0.15);
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	.status-badge.you {
		background: rgba(232, 168, 73, 0.2);
		color: var(--accent-warm);
	}
	.status-badge.generating {
		background: rgba(184, 168, 150, 0.1);
	}

	/* Thinking dots */
	.thinking-dots {
		display: inline-flex;
		gap: 2px;
	}
	.dot {
		width: 4px;
		height: 4px;
		border-radius: 50%;
		background: var(--text-secondary);
		animation: dotPulse 1.4s infinite;
	}
	.dot:nth-child(2) { animation-delay: 0.2s; }
	.dot:nth-child(3) { animation-delay: 0.4s; }

	@keyframes dotPulse {
		0%, 80%, 100% { opacity: 0.2; }
		40% { opacity: 1; }
	}

	/* HP bar */
	.hp-bar-container {
		position: relative;
		height: 16px;
		background: var(--bg-message);
		border-radius: var(--border-radius-sm);
		overflow: hidden;
	}

	.hp-bar-fill {
		height: 100%;
		border-radius: var(--border-radius-sm);
		transition: width 0.4s ease;
	}

	.hp-bar-fill.hp-green { background: #6B8E6B; }
	.hp-bar-fill.hp-amber { background: #E8A849; }
	.hp-bar-fill.hp-red { background: #C45C4A; }

	.hp-text {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-mono);
		font-size: 10px;
		font-weight: 500;
		color: var(--text-primary);
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
	}

	/* Button row */
	.card-actions {
		display: flex;
		gap: 6px;
	}

	/* Drop-In / Release button */
	.drop-in-btn {
		flex: 1;
		padding: 6px 12px;
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: all var(--transition-fast);
		background: transparent;
		border: 1px solid var(--text-secondary);
		color: var(--text-secondary);
	}

	/* Character-class-colored buttons */
	.drop-in-btn.fighter {
		border-color: var(--color-fighter);
		color: var(--color-fighter);
	}
	.drop-in-btn.fighter:hover:not(:disabled) {
		background: var(--color-fighter);
		color: var(--bg-primary);
	}
	.drop-in-btn.rogue {
		border-color: var(--color-rogue);
		color: var(--color-rogue);
	}
	.drop-in-btn.rogue:hover:not(:disabled) {
		background: var(--color-rogue);
		color: var(--bg-primary);
	}
	.drop-in-btn.wizard {
		border-color: var(--color-wizard);
		color: var(--color-wizard);
	}
	.drop-in-btn.wizard:hover:not(:disabled) {
		background: var(--color-wizard);
		color: var(--bg-primary);
	}
	.drop-in-btn.cleric {
		border-color: var(--color-cleric);
		color: var(--color-cleric);
	}
	.drop-in-btn.cleric:hover:not(:disabled) {
		background: var(--color-cleric);
		color: var(--bg-primary);
	}

	/* Release button: filled style */
	.drop-in-btn.release {
		border-color: var(--accent-warm);
		background: var(--accent-warm);
		color: var(--bg-primary);
	}
	.drop-in-btn.release:hover:not(:disabled) {
		background: var(--accent-warm-hover);
		border-color: var(--accent-warm-hover);
	}

	.drop-in-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* View Sheet button */
	.view-sheet-btn {
		padding: 6px 10px;
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 500;
		cursor: pointer;
		transition: all var(--transition-fast);
		background: transparent;
		border: 1px solid var(--text-secondary);
		color: var(--text-secondary);
		flex-shrink: 0;
	}

	.view-sheet-btn:hover {
		background: var(--bg-message);
		color: var(--text-primary);
		border-color: var(--text-primary);
	}
</style>
