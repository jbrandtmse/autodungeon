<script lang="ts">
	import ModeIndicator from './ModeIndicator.svelte';
	import GameControls from './GameControls.svelte';
	import PartyPanel from './PartyPanel.svelte';
	import CombatInitiative from './CombatInitiative.svelte';
	import HumanControls from './HumanControls.svelte';
	import ConnectionStatus from './ConnectionStatus.svelte';

	let storyThreadsOpen = $state(false);
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
</style>
