<script lang="ts">
	import { images, lightboxIndex, compareImages } from '$lib/stores/imageStore';
	import { getImageDownloadUrl } from '$lib/api';
	import type { SceneImage } from '$lib/types';

	const sortedImages = $derived(
		[...$images].sort(compareImages)
	);

	let tooltipImage: SceneImage | null = $state(null);
	let tooltipPosition = $state({ x: 0, y: 0 });

	function openLightbox(index: number): void {
		lightboxIndex.set(index);
	}

	function handleCardKeydown(e: KeyboardEvent, index: number): void {
		if (e.key === 'Enter') {
			e.preventDefault();
			openLightbox(index);
		}
	}

	function formatTimestamp(iso: string): string {
		// Handle malformed ISO strings like "2026-02-24T11:25:33+00:00Z" (both offset and Z)
		const cleaned = iso.replace(/\+00:00Z$/, 'Z');
		const d = new Date(cleaned);
		if (isNaN(d.getTime())) return '';
		return d.toLocaleString(undefined, {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function modeBadge(mode: string): string {
		return mode.charAt(0).toUpperCase() + mode.slice(1);
	}

	function handleMouseEnter(e: MouseEvent, img: SceneImage): void {
		tooltipImage = img;
		const x = Math.min(e.clientX + 10, window.innerWidth - 320);
		const y = Math.min(e.clientY + 10, window.innerHeight - 100);
		tooltipPosition = { x, y };
	}

	function handleMouseLeave(): void {
		tooltipImage = null;
	}
</script>

<div class="gallery-grid">
	{#each sortedImages as img, index (img.id)}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="gallery-card"
			role="button"
			tabindex="0"
			aria-label="View Turn {img.turn_number + 1} illustration"
			onclick={() => openLightbox(index)}
			onkeydown={(e) => handleCardKeydown(e, index)}
			onmouseenter={(e) => handleMouseEnter(e, img)}
			onmouseleave={handleMouseLeave}
		>
			<img
				class="gallery-thumbnail"
				src={img.download_url}
				alt={img.prompt}
				loading="lazy"
			/>
			<div class="gallery-meta">
				<span class="gallery-label">Turn {img.turn_number + 1}</span>
				<span class="gallery-mode-badge">{modeBadge(img.generation_mode)}</span>
				<span class="gallery-timestamp">{formatTimestamp(img.generated_at)}</span>
			</div>
			<a
				class="gallery-download-btn"
				href={getImageDownloadUrl(img.session_id, img.id)}
				download
				aria-label="Download image for Turn {img.turn_number + 1}"
				onclick={(e) => e.stopPropagation()}
			>
				<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
					<path
						d="M8 1v10M4 8l4 4 4-4M2 14h12"
						stroke="currentColor"
						stroke-width="1.5"
						stroke-linecap="round"
						stroke-linejoin="round"
						fill="none"
					/>
				</svg>
			</a>
		</div>
	{/each}
</div>

{#if tooltipImage}
	<div
		class="gallery-tooltip"
		style="left:{tooltipPosition.x}px; top:{tooltipPosition.y}px"
		role="tooltip"
	>
		<p class="tooltip-prompt">{tooltipImage.prompt}</p>
		<p class="tooltip-time">{formatTimestamp(tooltipImage.generated_at)}</p>
	</div>
{/if}

<style>
	.gallery-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: var(--space-md);
		padding: var(--space-md);
		overflow-y: auto;
		flex: 1;
	}

	.gallery-card {
		position: relative;
		background: var(--bg-primary);
		border-radius: var(--border-radius-md);
		overflow: hidden;
		border: 1px solid rgba(184, 168, 150, 0.1);
		transition:
			border-color var(--transition-fast),
			transform var(--transition-fast),
			box-shadow var(--transition-fast);
		cursor: pointer;
	}

	.gallery-card:hover {
		border-color: rgba(184, 168, 150, 0.25);
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
	}

	.gallery-card:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.gallery-thumbnail {
		width: 100%;
		aspect-ratio: 1;
		object-fit: cover;
		display: block;
	}

	.gallery-meta {
		display: flex;
		align-items: center;
		gap: var(--space-xs);
		padding: var(--space-xs) var(--space-sm);
		flex-wrap: wrap;
	}

	.gallery-label {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-secondary);
	}

	.gallery-mode-badge {
		font-family: var(--font-mono);
		font-size: 10px;
		padding: 2px 6px;
		border-radius: 4px;
		background: rgba(232, 168, 73, 0.15);
		color: var(--accent-warm);
	}

	.gallery-timestamp {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-secondary);
		margin-left: auto;
	}

	.gallery-download-btn {
		position: absolute;
		top: var(--space-xs);
		right: var(--space-xs);
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		background: rgba(0, 0, 0, 0.6);
		color: var(--text-primary);
		border-radius: var(--border-radius-sm);
		opacity: 0;
		transition: opacity var(--transition-fast);
		text-decoration: none;
	}

	.gallery-card:hover .gallery-download-btn {
		opacity: 1;
	}

	.gallery-download-btn:hover {
		background: rgba(0, 0, 0, 0.8);
		text-decoration: none;
	}

	.gallery-download-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
		opacity: 1;
	}

	.gallery-tooltip {
		position: fixed;
		z-index: 1050;
		max-width: 300px;
		background: var(--bg-primary);
		border: 1px solid var(--accent-warm);
		border-radius: 8px;
		padding: var(--space-sm);
		pointer-events: none;
	}

	.tooltip-prompt {
		font-family: var(--font-ui);
		font-size: 12px;
		color: var(--text-primary);
		margin: 0 0 4px 0;
		line-height: 1.4;
		max-height: 120px;
		overflow-y: auto;
		word-break: break-word;
	}

	.tooltip-time {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-secondary);
		margin: 0;
	}
</style>
