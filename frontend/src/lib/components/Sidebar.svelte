<script lang="ts">
	import ModeIndicator from './ModeIndicator.svelte';
	import GameControls from './GameControls.svelte';
	import PartyPanel from './PartyPanel.svelte';
	import CombatInitiative from './CombatInitiative.svelte';
	import HumanControls from './HumanControls.svelte';
	import ConnectionStatus from './ConnectionStatus.svelte';
	import { uiState } from '$lib/stores';

	let storyThreadsOpen = $state(false);

	function openSettings(): void {
		uiState.update((s) => ({ ...s, settingsOpen: true }));
	}
</script>

<div class="sidebar-content">
	<ModeIndicator />

	<hr class="sidebar-divider" />

	<GameControls />

	<hr class="sidebar-divider" />

	<PartyPanel />

	<CombatInitiative />

	<hr class="sidebar-divider" />

	<HumanControls />

	<hr class="sidebar-divider" />

	<details class="story-threads" bind:open={storyThreadsOpen}>
		<summary class="story-threads-summary">Story Threads</summary>
		<p class="story-threads-placeholder">Coming soon...</p>
	</details>

	<hr class="sidebar-divider" />

	<ConnectionStatus />

	<hr class="sidebar-divider" />

	<button class="settings-btn" onclick={openSettings} aria-label="Open settings">
		<svg class="settings-icon" viewBox="0 0 20 20" width="14" height="14" aria-hidden="true">
			<path
				d="M10 13a3 3 0 100-6 3 3 0 000 6z"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
			/>
			<path
				d="M17.4 11c.2-.6.2-1.4 0-2l1.3-1c.1-.1.1-.3 0-.4l-1.2-2.1c-.1-.1-.3-.2-.4-.1l-1.5.6c-.5-.4-1-.7-1.6-.9l-.2-1.6c0-.2-.2-.3-.3-.3h-2.5c-.2 0-.3.1-.3.3l-.2 1.6c-.6.2-1.1.5-1.6.9l-1.5-.6c-.2-.1-.3 0-.4.1L5.8 7.6c-.1.1-.1.3 0 .4l1.3 1c-.2.6-.2 1.4 0 2l-1.3 1c-.1.1-.1.3 0 .4l1.2 2.1c.1.1.3.2.4.1l1.5-.6c.5.4 1 .7 1.6.9l.2 1.6c0 .2.2.3.3.3h2.5c.2 0 .3-.1.3-.3l.2-1.6c.6-.2 1.1-.5 1.6-.9l1.5.6c.2.1.3 0 .4-.1l1.2-2.1c.1-.1.1-.3 0-.4l-1.3-1z"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				stroke-linejoin="round"
			/>
		</svg>
		Settings
	</button>
</div>

<style>
	.sidebar-content {
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}

	.sidebar-divider {
		border: none;
		border-top: 1px solid rgba(184, 168, 150, 0.15);
		margin: 0;
	}

	/* Story threads placeholder */
	.story-threads {
		font-family: var(--font-ui);
	}

	.story-threads-summary {
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

	.story-threads-summary::-webkit-details-marker {
		display: none;
	}

	.story-threads-summary::before {
		content: '\25B6';
		font-size: 8px;
		color: var(--text-secondary);
		transition: transform var(--transition-fast);
	}

	.story-threads[open] .story-threads-summary::before {
		transform: rotate(90deg);
	}

	.story-threads-placeholder {
		font-size: var(--text-system);
		color: var(--text-secondary);
		font-style: italic;
		padding: var(--space-sm) 0;
		padding-left: 14px;
	}

	/* Settings button */
	.settings-btn {
		display: flex;
		align-items: center;
		gap: 6px;
		width: 100%;
		padding: var(--space-sm) var(--space-xs);
		background: none;
		border: 1px solid transparent;
		border-radius: var(--border-radius-sm);
		color: var(--text-secondary);
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 500;
		cursor: pointer;
		transition:
			background var(--transition-fast),
			color var(--transition-fast),
			border-color var(--transition-fast);
	}

	.settings-btn:hover {
		background: var(--bg-message);
		color: var(--text-primary);
		border-color: rgba(184, 168, 150, 0.15);
	}

	.settings-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.settings-icon {
		flex-shrink: 0;
	}
</style>
