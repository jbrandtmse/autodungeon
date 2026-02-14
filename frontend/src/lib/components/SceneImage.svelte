<script lang="ts">
	import type { SceneImage } from '$lib/types';

	let {
		image,
	}: {
		image: SceneImage;
	} = $props();

	const turnDisplay = $derived(image.turn_number + 1);
</script>

<div class="scene-image-container">
	<img
		class="scene-image"
		src={image.download_url}
		alt={image.prompt}
		loading="lazy"
	/>
	<div class="scene-image-overlay">
		<a
			class="image-download-btn"
			href={image.download_url}
			download
			aria-label="Download scene image for Turn {turnDisplay}"
		>
			<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
				<path d="M8 1v10M4 8l4 4 4-4M2 14h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none" />
			</svg>
			Download
		</a>
	</div>
</div>

<style>
	.scene-image-container {
		position: relative;
		margin-bottom: var(--space-md);
		border-radius: 8px;
		overflow: hidden;
		border: 1px solid var(--bg-message);
	}

	.scene-image {
		width: 100%;
		height: auto;
		display: block;
		aspect-ratio: 16 / 9;
		object-fit: cover;
	}

	.scene-image-overlay {
		position: absolute;
		bottom: 0;
		right: 0;
		padding: var(--space-sm);
		display: flex;
		gap: var(--space-xs);
		opacity: 0;
		transition: opacity 0.15s ease;
	}

	.scene-image-container:hover .scene-image-overlay {
		opacity: 1;
	}

	.image-download-btn {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 4px 10px;
		background: rgba(0, 0, 0, 0.7);
		color: var(--text-primary);
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 12px;
		font-weight: 500;
		text-decoration: none;
		transition: background var(--transition-fast);
	}

	.image-download-btn:hover {
		background: rgba(0, 0, 0, 0.9);
		text-decoration: none;
	}

	.image-download-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}
</style>
