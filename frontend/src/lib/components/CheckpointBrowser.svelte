<script lang="ts">
	import { getCheckpoints, getCheckpointPreview, restoreCheckpoint } from '$lib/api';
	import { gameState, sendCommand } from '$lib/stores';
	import ConfirmDialog from './ConfirmDialog.svelte';
	import type { CheckpointInfo, CheckpointPreview } from '$lib/types';

	let { sessionId }: { sessionId: string } = $props();

	let checkpoints = $state<CheckpointInfo[]>([]);
	let loading = $state(true);
	let previewTurn = $state<number | null>(null);
	let preview = $state<CheckpointPreview | null>(null);
	let previewLoading = $state(false);

	// Confirm dialog state
	let confirmOpen = $state(false);
	let confirmTitle = $state('');
	let confirmMessage = $state('');
	let confirmAction = $state<() => void>(() => {});

	const currentTurn = $derived($gameState?.turn_number ?? 0);

	async function loadCheckpoints(): Promise<void> {
		if (!sessionId) return;
		loading = true;
		try {
			checkpoints = await getCheckpoints(sessionId);
		} catch {
			checkpoints = [];
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (sessionId) {
			loadCheckpoints();
		}
	});

	async function handlePreview(turn: number): Promise<void> {
		if (previewTurn === turn) {
			previewTurn = null;
			preview = null;
			return;
		}
		previewTurn = turn;
		previewLoading = true;
		try {
			preview = await getCheckpointPreview(sessionId, turn);
		} catch {
			preview = null;
		} finally {
			previewLoading = false;
		}
	}

	function requestRestore(turn: number): void {
		const turnsToUndo = currentTurn - turn;
		confirmTitle = 'Restore Checkpoint';
		confirmMessage = `Restore to Turn ${turn}? This will undo ${turnsToUndo} turn(s).`;
		confirmAction = async () => {
			confirmOpen = false;
			try {
				await restoreCheckpoint(sessionId, turn);
				// Stop autopilot if running
				sendCommand({ type: 'stop_autopilot' });
				window.location.reload();
			} catch {
				// Error handling
			}
		};
		confirmOpen = true;
	}
</script>

<details class="sidebar-section">
	<summary class="sidebar-section-summary">Session History</summary>
	<div class="sidebar-section-content">
		{#if loading}
			<p class="loading-text">Loading checkpoints...</p>
		{:else if checkpoints.length === 0}
			<p class="empty-text">No checkpoints available yet</p>
		{:else}
			<div class="checkpoint-list">
				{#each checkpoints as cp (cp.turn_number)}
					<div class="checkpoint-entry">
						<div class="checkpoint-header">
							<div class="checkpoint-info">
								<span class="checkpoint-turn">Turn {cp.turn_number}</span>
								<span class="checkpoint-time">{cp.timestamp}</span>
							</div>
							<div class="checkpoint-actions">
								<button
									class="checkpoint-btn"
									onclick={() => handlePreview(cp.turn_number)}
								>
									{previewTurn === cp.turn_number ? 'Close' : 'Preview'}
								</button>
								{#if cp.turn_number < currentTurn}
									<button
										class="checkpoint-btn restore-btn"
										onclick={() => requestRestore(cp.turn_number)}
									>
										Restore
									</button>
								{/if}
							</div>
						</div>

						{#if cp.brief_context}
							<p class="checkpoint-context">{cp.brief_context}</p>
						{/if}

						{#if previewTurn === cp.turn_number}
							<div class="preview-section">
								{#if previewLoading}
									<p class="preview-loading">Loading preview...</p>
								{:else if preview}
									{#each preview.entries as entry}
										<p class="preview-entry">{entry}</p>
									{/each}
								{:else}
									<p class="preview-empty">No preview available</p>
								{/if}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	</div>
</details>

<ConfirmDialog
	open={confirmOpen}
	title={confirmTitle}
	message={confirmMessage}
	confirmLabel="Restore"
	confirmDanger={false}
	onConfirm={confirmAction}
	onCancel={() => { confirmOpen = false; }}
/>

<style>
	.sidebar-section {
		font-family: var(--font-ui);
	}

	.sidebar-section-summary {
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

	.sidebar-section-summary::-webkit-details-marker {
		display: none;
	}

	.sidebar-section-summary::before {
		content: '\25B6';
		font-size: 8px;
		color: var(--text-secondary);
		transition: transform var(--transition-fast);
	}

	.sidebar-section[open] .sidebar-section-summary::before {
		transform: rotate(90deg);
	}

	.sidebar-section-content {
		padding: var(--space-sm) 0;
		padding-left: 14px;
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.loading-text,
	.empty-text {
		font-size: var(--text-system);
		color: var(--text-secondary);
		font-style: italic;
	}

	.checkpoint-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.checkpoint-entry {
		background: var(--bg-secondary);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm);
		border: 1px solid rgba(184, 168, 150, 0.1);
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.checkpoint-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-xs);
	}

	.checkpoint-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.checkpoint-turn {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.checkpoint-time {
		font-size: 10px;
		color: var(--text-secondary);
	}

	.checkpoint-actions {
		display: flex;
		gap: 4px;
		flex-shrink: 0;
	}

	.checkpoint-btn {
		padding: 3px 8px;
		background: transparent;
		border: 1px solid var(--text-secondary);
		border-radius: var(--border-radius-sm);
		color: var(--text-secondary);
		font-family: var(--font-ui);
		font-size: 10px;
		font-weight: 500;
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.checkpoint-btn:hover {
		background: var(--bg-message);
		color: var(--text-primary);
		border-color: var(--text-primary);
	}

	.restore-btn {
		border-color: var(--accent-warm);
		color: var(--accent-warm);
	}

	.restore-btn:hover {
		background: rgba(232, 168, 73, 0.1);
		border-color: var(--accent-warm);
		color: var(--accent-warm);
	}

	.checkpoint-context {
		font-size: 11px;
		color: var(--text-secondary);
		line-height: 1.4;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.preview-section {
		border-top: 1px solid rgba(184, 168, 150, 0.1);
		padding-top: var(--space-xs);
		margin-top: var(--space-xs);
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.preview-loading {
		font-size: 11px;
		color: var(--text-secondary);
		font-style: italic;
	}

	.preview-entry {
		font-size: 11px;
		color: var(--text-primary);
		font-style: italic;
		line-height: 1.4;
		padding-left: var(--space-sm);
		border-left: 2px solid rgba(184, 168, 150, 0.15);
	}

	.preview-empty {
		font-size: 11px;
		color: var(--text-secondary);
		font-style: italic;
	}
</style>
