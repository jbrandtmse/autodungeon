<script lang="ts">
	import { uiState } from '$lib/stores';
	import type { NpcProfile } from '$lib/types';

	let {
		npcKey,
		npc,
	}: {
		npcKey: string;
		npc: NpcProfile;
	} = $props();

	const hpPercent = $derived(
		npc.hp_max > 0 ? Math.max(0, Math.min(100, (npc.hp_current / npc.hp_max) * 100)) : 0,
	);

	const hpColorClass = $derived.by(() => {
		if (hpPercent > 50) return 'hp-green';
		if (hpPercent > 25) return 'hp-amber';
		return 'hp-red';
	});

	const isDefeated = $derived(npc.hp_current === 0);

	const conditionsText = $derived(npc.conditions.join(', '));

	function openSheet(): void {
		uiState.update((s) => ({ ...s, npcSheetName: npcKey }));
	}

	function handleKeydown(e: KeyboardEvent): void {
		// Enter / Space activate the card (mirror native button behavior).
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			openSheet();
		}
	}
</script>

<div
	class="npc-card"
	class:defeated={isDefeated}
	role="button"
	tabindex="0"
	aria-label={`View NPC sheet for ${npc.name}`}
	onclick={openSheet}
	onkeydown={handleKeydown}
>
	<div class="card-header">
		<span class="npc-name">{npc.name}</span>
		<span class="ac-chip" aria-label="Armor Class">AC {npc.ac}</span>
	</div>

	<div
		class="hp-bar-container"
		role="meter"
		aria-label={`Hit points for ${npc.name}`}
		aria-valuenow={npc.hp_current}
		aria-valuemin={0}
		aria-valuemax={npc.hp_max}
	>
		<div class="hp-bar-fill {hpColorClass}" style="width: {hpPercent}%"></div>
		<span class="hp-text">{npc.hp_current}/{npc.hp_max} HP</span>
	</div>

	{#if conditionsText}
		<div class="conditions" aria-label="Conditions">
			<span class="conditions-label">Conditions:</span>
			<span class="conditions-list">{conditionsText}</span>
		</div>
	{/if}
</div>

<style>
	.npc-card {
		background: var(--bg-secondary);
		border-radius: var(--border-radius-md);
		border-left: 3px solid var(--color-dm, #b88c5e);
		padding: 10px 12px;
		display: flex;
		flex-direction: column;
		gap: 6px;
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.npc-card:hover {
		background: var(--bg-message);
	}

	.npc-card:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	/* Defeated styling: AC #3 — strikethrough name + greyed-out card. */
	.npc-card.defeated {
		opacity: 0.5;
	}
	.npc-card.defeated .npc-name {
		text-decoration: line-through;
	}

	.card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--space-sm);
	}

	.npc-name {
		font-family: var(--font-ui);
		font-size: 14px;
		font-weight: 600;
		color: var(--color-dm, #b88c5e);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.ac-chip {
		flex-shrink: 0;
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 600;
		padding: 2px 8px;
		border-radius: 10px;
		background: rgba(184, 168, 150, 0.15);
		color: var(--text-secondary);
		letter-spacing: 0.02em;
	}

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

	.conditions {
		font-family: var(--font-ui);
		font-size: 11px;
		color: var(--text-secondary);
		display: flex;
		gap: 4px;
		flex-wrap: wrap;
	}

	.conditions-label {
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.conditions-list {
		color: var(--text-primary);
	}
</style>
