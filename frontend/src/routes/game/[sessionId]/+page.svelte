<script lang="ts">
	import { page } from '$app/stores';

	// Game view — full implementation in Story 16-5
	const sessionId = $derived($page.params.sessionId);
</script>

<div class="game-page">
	<h1 class="page-title">Game: {sessionId}</h1>
	<p class="page-subtitle">Narrative panel coming in Story 16-5</p>
</div>

<style>
	.game-page {
		padding: var(--space-lg);
	}

	.page-title {
		font-family: var(--font-narrative);
		font-size: 24px;
		font-weight: 600;
		color: var(--color-dm);
		margin-bottom: var(--space-md);
	}

	.page-subtitle {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-secondary);
		font-style: italic;
	}
</style>
