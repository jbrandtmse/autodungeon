<script lang="ts">
	import { getForks, createFork, renameFork, deleteFork, switchFork, promoteFork, returnToMain } from '$lib/api';
	import { gameState } from '$lib/stores';
	import ConfirmDialog from './ConfirmDialog.svelte';
	import type { ForkMetadata } from '$lib/types';

	let { sessionId, onCompare }: { sessionId: string; onCompare: (forkId: string) => void } = $props();

	let forks = $state<ForkMetadata[]>([]);
	let forkNameInput = $state('');
	let creating = $state(false);
	let loading = $state(true);
	let validationError = $state('');
	let renamingForkId = $state<string | null>(null);
	let renameInput = $state('');
	let menuOpenForkId = $state<string | null>(null);

	// Confirm dialog state
	let confirmOpen = $state(false);
	let confirmTitle = $state('');
	let confirmMessage = $state('');
	let confirmLabel = $state('Confirm');
	let confirmDanger = $state(false);
	let confirmAction = $state<() => void>(() => {});

	const activeForkId = $derived($gameState?.active_fork_id ?? null);

	async function loadForks(): Promise<void> {
		if (!sessionId) return;
		try {
			forks = await getForks(sessionId);
		} catch {
			forks = [];
		} finally {
			loading = false;
		}
	}

	$effect(() => {
		if (sessionId) {
			loadForks();
		}
	});

	async function handleCreateFork(): Promise<void> {
		const trimmed = forkNameInput.trim();
		if (!trimmed) {
			validationError = 'Please enter a fork name';
			return;
		}
		validationError = '';
		creating = true;
		try {
			await createFork(sessionId, trimmed);
			forkNameInput = '';
			await loadForks();
		} catch {
			validationError = 'Failed to create fork';
		} finally {
			creating = false;
		}
	}

	async function handleSwitch(forkId: string): Promise<void> {
		try {
			await switchFork(sessionId, forkId);
			window.location.reload();
		} catch {
			// Error handling
		}
	}

	async function handleReturnToMain(): Promise<void> {
		try {
			await returnToMain(sessionId);
			window.location.reload();
		} catch {
			// Error handling
		}
	}

	function handleCompare(forkId: string): void {
		onCompare(forkId);
	}

	function openRename(fork: ForkMetadata, event: MouseEvent): void {
		event.stopPropagation();
		renamingForkId = fork.fork_id;
		renameInput = fork.name;
		menuOpenForkId = null;
	}

	async function handleRename(forkId: string): Promise<void> {
		const trimmed = renameInput.trim();
		if (!trimmed) return;
		try {
			await renameFork(sessionId, forkId, trimmed);
			renamingForkId = null;
			renameInput = '';
			await loadForks();
		} catch {
			// Error handling
		}
	}

	function requestDelete(fork: ForkMetadata, event: MouseEvent): void {
		event.stopPropagation();
		menuOpenForkId = null;
		confirmTitle = 'Delete Fork';
		confirmMessage = `Delete '${fork.name}'? Cannot be undone.`;
		confirmLabel = 'Delete';
		confirmDanger = true;
		confirmAction = async () => {
			confirmOpen = false;
			try {
				await deleteFork(sessionId, fork.fork_id);
				await loadForks();
			} catch {
				// Error handling
			}
		};
		confirmOpen = true;
	}

	function requestPromote(fork: ForkMetadata, event: MouseEvent): void {
		event.stopPropagation();
		menuOpenForkId = null;
		confirmTitle = 'Promote Fork';
		confirmMessage = `Promote '${fork.name}' to main timeline? The current main timeline's post-branch turns will be archived into a new fork. This cannot be undone.`;
		confirmLabel = 'Make Primary';
		confirmDanger = false;
		confirmAction = async () => {
			confirmOpen = false;
			try {
				await promoteFork(sessionId, fork.fork_id);
				window.location.reload();
			} catch {
				// Error handling
			}
		};
		confirmOpen = true;
	}

	function toggleMenu(forkId: string, event: MouseEvent): void {
		event.stopPropagation();
		menuOpenForkId = menuOpenForkId === forkId ? null : forkId;
	}

	function formatDate(isoStr: string): string {
		try {
			return new Date(isoStr).toLocaleDateString(undefined, {
				month: 'short',
				day: 'numeric',
				hour: '2-digit',
				minute: '2-digit',
			});
		} catch {
			return isoStr;
		}
	}
</script>

<details class="sidebar-section">
	<summary class="sidebar-section-summary">Fork Timeline</summary>
	<div class="sidebar-section-content">
		{#if activeForkId}
			<div class="fork-banner">
				<span class="fork-banner-text">Playing fork</span>
				<button class="return-main-btn" onclick={handleReturnToMain}>Return to Main</button>
			</div>
		{/if}

		<div class="fork-create">
			<input
				type="text"
				class="fork-name-input"
				bind:value={forkNameInput}
				placeholder="e.g., Diplomacy attempt"
				disabled={creating}
				onkeydown={(e: KeyboardEvent) => { if (e.key === 'Enter') handleCreateFork(); }}
			/>
			<button
				class="create-fork-btn"
				onclick={handleCreateFork}
				disabled={creating}
			>
				{creating ? 'Creating...' : 'Create Fork'}
			</button>
			{#if validationError}
				<p class="validation-error">{validationError}</p>
			{/if}
		</div>

		{#if loading}
			<p class="loading-text">Loading forks...</p>
		{:else if forks.length === 0}
			<p class="empty-text">No forks yet</p>
		{:else}
			<div class="fork-list">
				{#each forks as fork (fork.fork_id)}
					<div class="fork-card" class:active={activeForkId === fork.fork_id}>
						<div class="fork-header">
							{#if renamingForkId === fork.fork_id}
								<div class="rename-form">
									<input
										type="text"
										class="rename-input"
										bind:value={renameInput}
										onkeydown={(e: KeyboardEvent) => { if (e.key === 'Enter') handleRename(fork.fork_id); if (e.key === 'Escape') { renamingForkId = null; } }}
									/>
									<button class="rename-save-btn" onclick={() => handleRename(fork.fork_id)}>Save</button>
								</div>
							{:else}
								<div class="fork-name-row">
									<span class="fork-name">{fork.name}</span>
									{#if activeForkId === fork.fork_id}
										<span class="active-badge">(active)</span>
									{/if}
								</div>
							{/if}
							<button
								class="menu-btn"
								onclick={(e: MouseEvent) => toggleMenu(fork.fork_id, e)}
								aria-label="Fork actions"
							>...</button>
						</div>

						{#if menuOpenForkId === fork.fork_id}
							<div class="fork-menu">
								<button class="menu-item" onclick={(e: MouseEvent) => openRename(fork, e)}>Rename</button>
								<button class="menu-item" onclick={(e: MouseEvent) => requestPromote(fork, e)}>Make Primary</button>
								{#if activeForkId !== fork.fork_id}
									<button class="menu-item menu-item-danger" onclick={(e: MouseEvent) => requestDelete(fork, e)}>Delete</button>
								{/if}
							</div>
						{/if}

						<p class="fork-meta">
							Branched at turn {fork.branch_turn} | Turns: {fork.turn_count} | Last: {formatDate(fork.updated_at)}
						</p>

						<div class="fork-actions">
							{#if activeForkId !== fork.fork_id}
								<button class="fork-action-btn" onclick={() => handleSwitch(fork.fork_id)}>Switch</button>
							{/if}
							<button class="fork-action-btn" onclick={() => handleCompare(fork.fork_id)}>Compare</button>
						</div>
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
	confirmLabel={confirmLabel}
	confirmDanger={confirmDanger}
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

	.fork-banner {
		background: rgba(232, 168, 73, 0.1);
		border: 1px solid rgba(232, 168, 73, 0.3);
		border-radius: var(--border-radius-sm);
		padding: var(--space-xs) var(--space-sm);
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-sm);
	}

	.fork-banner-text {
		font-size: var(--text-system);
		font-weight: 600;
		color: var(--accent-warm);
	}

	.return-main-btn {
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 500;
		padding: 4px 8px;
		border-radius: var(--border-radius-sm);
		border: 1px solid var(--accent-warm);
		background: transparent;
		color: var(--accent-warm);
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.return-main-btn:hover {
		background: var(--accent-warm);
		color: var(--bg-primary);
	}

	.fork-create {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
	}

	.fork-name-input {
		width: 100%;
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid var(--text-secondary);
		border-radius: var(--border-radius-sm);
		padding: var(--space-xs) var(--space-sm);
		font-family: var(--font-ui);
		font-size: var(--text-system);
		transition: border-color var(--transition-fast);
	}

	.fork-name-input:focus {
		outline: none;
		border-color: var(--accent-warm);
	}

	.create-fork-btn {
		align-self: flex-end;
		padding: 6px 12px;
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

	.create-fork-btn:hover:not(:disabled) {
		background: var(--bg-message);
		border-color: var(--text-primary);
	}

	.create-fork-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.validation-error {
		font-size: 11px;
		color: var(--color-error);
	}

	.loading-text,
	.empty-text {
		font-size: var(--text-system);
		color: var(--text-secondary);
		font-style: italic;
	}

	.fork-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.fork-card {
		background: var(--bg-secondary);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm);
		border: 1px solid rgba(184, 168, 150, 0.1);
		position: relative;
	}

	.fork-card.active {
		border-color: rgba(232, 168, 73, 0.3);
	}

	.fork-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--space-xs);
	}

	.fork-name-row {
		display: flex;
		align-items: center;
		gap: 6px;
		min-width: 0;
	}

	.fork-name {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.active-badge {
		font-size: 11px;
		color: var(--accent-warm);
		font-weight: 500;
		flex-shrink: 0;
	}

	.menu-btn {
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 2px 6px;
		font-size: 14px;
		font-weight: 700;
		letter-spacing: 1px;
		border-radius: var(--border-radius-sm);
		transition: background var(--transition-fast);
	}

	.menu-btn:hover {
		background: var(--bg-message);
	}

	.fork-menu {
		position: absolute;
		right: var(--space-sm);
		top: 32px;
		background: var(--bg-primary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		padding: 4px 0;
		z-index: 10;
		min-width: 120px;
	}

	.menu-item {
		display: block;
		width: 100%;
		padding: 6px 12px;
		background: none;
		border: none;
		color: var(--text-primary);
		font-family: var(--font-ui);
		font-size: 12px;
		text-align: left;
		cursor: pointer;
		transition: background var(--transition-fast);
	}

	.menu-item:hover {
		background: var(--bg-message);
	}

	.menu-item-danger {
		color: var(--color-error);
	}

	.fork-meta {
		font-size: 11px;
		color: var(--text-secondary);
		margin-top: 4px;
	}

	.fork-actions {
		display: flex;
		gap: 6px;
		margin-top: var(--space-xs);
	}

	.fork-action-btn {
		padding: 4px 10px;
		background: transparent;
		border: 1px solid var(--text-secondary);
		border-radius: var(--border-radius-sm);
		color: var(--text-secondary);
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 500;
		cursor: pointer;
		transition: all var(--transition-fast);
	}

	.fork-action-btn:hover {
		background: var(--bg-message);
		color: var(--text-primary);
		border-color: var(--text-primary);
	}

	.rename-form {
		display: flex;
		gap: 4px;
		flex: 1;
	}

	.rename-input {
		flex: 1;
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid var(--accent-warm);
		border-radius: var(--border-radius-sm);
		padding: 2px 6px;
		font-family: var(--font-ui);
		font-size: 12px;
	}

	.rename-input:focus {
		outline: none;
	}

	.rename-save-btn {
		padding: 2px 8px;
		background: var(--accent-warm);
		color: var(--bg-primary);
		border: none;
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 500;
		cursor: pointer;
	}
</style>
