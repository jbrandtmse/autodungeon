<script lang="ts">
	import '../app.css';
	import type { Snippet } from 'svelte';
	import { page } from '$app/stores';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import SettingsModal from '$lib/components/SettingsModal.svelte';
	import { uiState } from '$lib/stores';

	let { children }: { children: Snippet } = $props();

	const sessionId = $derived($page.params.sessionId ?? null);

	function toggleSidebar(): void {
		uiState.update((s) => ({ ...s, sidebarOpen: !s.sidebarOpen }));
	}

	function closeSettings(): void {
		uiState.update((s) => ({ ...s, settingsOpen: false }));
	}
</script>

<div class="app-layout" class:sidebar-collapsed={!$uiState.sidebarOpen}>
	<aside class="sidebar" class:open={$uiState.sidebarOpen}>
		<div class="sidebar-header">
			<a href="/" class="app-title">autodungeon</a>
		</div>
		<nav class="sidebar-nav">
			<Sidebar />
		</nav>
	</aside>

	<!-- Mobile hamburger toggle -->
	<button
		class="sidebar-toggle"
		onclick={toggleSidebar}
		aria-label={$uiState.sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
		aria-expanded={$uiState.sidebarOpen}
	>
		<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
			{#if $uiState.sidebarOpen}
				<line x1="6" y1="6" x2="18" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
				<line x1="18" y1="6" x2="6" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
			{:else}
				<line x1="4" y1="6" x2="20" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
				<line x1="4" y1="12" x2="20" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
				<line x1="4" y1="18" x2="20" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
			{/if}
		</svg>
	</button>

	<main class="main-content">
		{@render children()}
	</main>
</div>

<SettingsModal
	open={$uiState.settingsOpen}
	{sessionId}
	onClose={closeSettings}
/>

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
		text-decoration: none;
		display: block;
		transition: opacity var(--transition-fast);
	}

	.app-title:hover {
		text-decoration: none;
		opacity: 0.85;
	}

	.sidebar-nav {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.main-content {
		background-color: var(--bg-primary);
		padding: var(--space-lg);
		overflow-y: auto;
		height: 100vh;
	}

	/* Hamburger toggle (hidden by default, shown on mobile) */
	.sidebar-toggle {
		display: none;
		position: fixed;
		top: var(--space-sm);
		left: var(--space-sm);
		z-index: 100;
		background: var(--bg-secondary);
		color: var(--text-primary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		padding: 6px;
		cursor: pointer;
		transition: background var(--transition-fast);
	}
	.sidebar-toggle:hover {
		background: var(--bg-message);
	}

	/* === Responsive: small desktop (768-1024px) === */
	@media (max-width: 1024px) {
		.app-layout {
			grid-template-columns: 200px 1fr;
		}

		.sidebar {
			padding: var(--space-sm);
		}
	}

	/* === Responsive: mobile (<768px) === */
	@media (max-width: 768px) {
		.app-layout {
			grid-template-columns: 1fr;
		}

		.sidebar {
			position: fixed;
			top: 0;
			left: 0;
			width: 260px;
			height: 100vh;
			z-index: 50;
			transform: translateX(-100%);
			transition: transform 0.25s ease;
			padding: var(--space-md);
		}

		.sidebar.open {
			transform: translateX(0);
		}

		.sidebar-toggle {
			display: flex;
			align-items: center;
			justify-content: center;
		}

		.main-content {
			padding: var(--space-md);
			padding-top: 48px;
		}
	}
</style>
