<script lang="ts">
	import { getComparison } from '$lib/api';
	import type { ComparisonData } from '$lib/types';

	let { sessionId, forkId, onClose }: {
		sessionId: string;
		forkId: string;
		onClose: () => void;
	} = $props();

	let comparison = $state<ComparisonData | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	$effect(() => {
		if (sessionId && forkId) {
			loadComparison();
		}
	});

	async function loadComparison(): Promise<void> {
		loading = true;
		error = null;
		try {
			comparison = await getComparison(sessionId, forkId);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load comparison';
		} finally {
			loading = false;
		}
	}

	function handleKeydown(e: KeyboardEvent): void {
		if (e.key === 'Escape') {
			onClose();
		}
	}

	const maxTurns = $derived(
		comparison
			? Math.max(comparison.left.turns.length, comparison.right.turns.length)
			: 0
	);
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="comparison-overlay">
	<div class="comparison-header">
		<h2 class="comparison-title">Timeline Comparison</h2>
		{#if comparison}
			<span class="branch-info">Branch point: Turn {comparison.branch_turn}</span>
		{/if}
		<button class="close-btn" onclick={onClose} aria-label="Close comparison">Close</button>
	</div>

	{#if loading}
		<div class="comparison-loading">
			<p>Loading comparison data...</p>
		</div>
	{:else if error}
		<div class="comparison-error">
			<p>{error}</p>
		</div>
	{:else if comparison}
		<div class="comparison-grid">
			<div class="timeline-header left">
				<h3 class="timeline-label">{comparison.left.label}</h3>
				<span class="timeline-info">{comparison.left.total_turns} turns</span>
			</div>
			<div class="timeline-header right">
				<h3 class="timeline-label">{comparison.right.label}</h3>
				<span class="timeline-info">{comparison.right.total_turns} turns</span>
			</div>

			{#each { length: maxTurns } as _, i}
				{@const leftTurn = comparison.left.turns[i]}
				{@const rightTurn = comparison.right.turns[i]}
				<div
					class="turn-cell left"
					class:branch-point={leftTurn?.is_branch_point}
					class:ended={leftTurn?.is_ended}
				>
					{#if leftTurn}
						{#if leftTurn.is_ended}
							<span class="ended-marker">[Timeline ends here]</span>
						{:else}
							<span class="turn-number">Turn {leftTurn.turn_number}</span>
							{#each leftTurn.entries as entry}
								<p class="turn-entry">{entry}</p>
							{/each}
						{/if}
					{/if}
				</div>
				<div
					class="turn-cell right"
					class:branch-point={rightTurn?.is_branch_point}
					class:ended={rightTurn?.is_ended}
				>
					{#if rightTurn}
						{#if rightTurn.is_ended}
							<span class="ended-marker">[Timeline ends here]</span>
						{:else}
							<span class="turn-number">Turn {rightTurn.turn_number}</span>
							{#each rightTurn.entries as entry}
								<p class="turn-entry">{entry}</p>
							{/each}
						{/if}
					{/if}
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.comparison-overlay {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--bg-primary);
		overflow: hidden;
	}

	.comparison-header {
		display: flex;
		align-items: center;
		gap: var(--space-md);
		padding: var(--space-md);
		border-bottom: 1px solid rgba(184, 168, 150, 0.15);
		flex-shrink: 0;
	}

	.comparison-title {
		font-family: var(--font-narrative);
		font-size: 18px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.branch-info {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
	}

	.close-btn {
		margin-left: auto;
		padding: 6px 14px;
		background: transparent;
		color: var(--text-primary);
		border: 1px solid var(--text-secondary);
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 13px;
		font-weight: 500;
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.close-btn:hover {
		background: var(--bg-message);
		border-color: var(--text-primary);
	}

	.comparison-loading,
	.comparison-error {
		display: flex;
		align-items: center;
		justify-content: center;
		flex: 1;
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-secondary);
	}

	.comparison-error {
		color: var(--color-error);
	}

	.comparison-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0;
		flex: 1;
		overflow-y: auto;
		padding: var(--space-sm);
	}

	.timeline-header {
		padding: var(--space-sm) var(--space-md);
		border-bottom: 2px solid rgba(184, 168, 150, 0.2);
		position: sticky;
		top: 0;
		background: var(--bg-primary);
		z-index: 1;
	}

	.timeline-header.left {
		border-right: 1px solid rgba(184, 168, 150, 0.15);
	}

	.timeline-label {
		font-family: var(--font-ui);
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.timeline-info {
		font-family: var(--font-ui);
		font-size: 11px;
		color: var(--text-secondary);
	}

	.turn-cell {
		padding: var(--space-sm) var(--space-md);
		border-bottom: 1px solid rgba(184, 168, 150, 0.1);
		min-height: 40px;
	}

	.turn-cell.left {
		border-right: 1px solid rgba(184, 168, 150, 0.15);
	}

	.turn-cell.branch-point {
		background: rgba(232, 168, 73, 0.05);
		border-left: 3px solid var(--accent-warm);
	}

	.turn-cell.ended {
		opacity: 0.5;
	}

	.turn-number {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-secondary);
		display: block;
		margin-bottom: 4px;
	}

	.turn-entry {
		font-family: var(--font-narrative);
		font-size: 13px;
		color: var(--text-primary);
		line-height: 1.5;
		margin-bottom: 4px;
	}

	.ended-marker {
		font-family: var(--font-ui);
		font-size: 12px;
		color: var(--text-secondary);
		font-style: italic;
	}
</style>
