<script lang="ts">
	import '../app.css';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
</script>

<div class="app-layout">
	<aside class="sidebar">
		<div class="sidebar-header">
			<h1 class="app-title">autodungeon</h1>
		</div>
		<nav class="sidebar-nav">
			<p class="sidebar-placeholder">Party panel (Story 16-6)</p>
		</nav>
	</aside>
	<main class="main-content">
		{@render children()}
	</main>
</div>

<style>
	.app-layout {
		display: grid;
		grid-template-columns: var(--sidebar-width) 1fr;
		min-height: 100vh;
	}

	.sidebar {
		background-color: var(--bg-secondary);
		padding: var(--space-md);
		overflow-y: auto;
		height: 100vh;
		position: sticky;
		top: 0;
	}

	.sidebar-header {
		margin-bottom: var(--space-lg);
	}

	.app-title {
		font-family: var(--font-narrative);
		font-size: 20px;
		font-weight: 600;
		color: var(--color-dm);
		letter-spacing: 0.05em;
	}

	.sidebar-nav {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.sidebar-placeholder {
		color: var(--text-secondary);
		font-size: var(--text-system);
		font-style: italic;
	}

	.main-content {
		background-color: var(--bg-primary);
		padding: var(--space-lg);
		overflow-y: auto;
		height: 100vh;
	}
</style>
