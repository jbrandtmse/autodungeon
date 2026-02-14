<script lang="ts">
	let {
		turnNumber,
		mode = 'specific',
	}: {
		turnNumber: number;
		mode: 'current' | 'best' | 'specific';
	} = $props();

	const turnDisplay = $derived(turnNumber + 1);
	const label = $derived(
		mode === 'best'
			? 'Painting the best scene...'
			: `Painting the scene for Turn ${turnDisplay}...`
	);
</script>

<div class="image-generating" aria-live="polite">
	<span class="image-generating-spinner" aria-hidden="true"></span>
	<span class="image-generating-text">{label}</span>
</div>

<style>
	.image-generating {
		background: var(--bg-secondary);
		border: 1px dashed var(--accent-warm);
		border-radius: 8px;
		padding: var(--space-lg);
		text-align: center;
		margin-bottom: var(--space-md);
		min-height: 200px;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: var(--space-sm);
	}

	.image-generating-text {
		font-family: var(--font-ui);
		font-size: 14px;
		color: var(--accent-warm);
		font-style: italic;
	}

	.image-generating-spinner {
		display: inline-block;
		width: 24px;
		height: 24px;
		border: 2px solid var(--accent-warm);
		border-right-color: transparent;
		border-radius: 50%;
		animation: image-spin 0.8s linear infinite;
	}

	@keyframes image-spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
