<script lang="ts">
	import { tick } from 'svelte';
	import { images, galleryOpen } from '$lib/stores/imageStore';

	let panelElement: HTMLElement | undefined = $state();
	let previouslyFocused: HTMLElement | null = null;

	function close(): void {
		galleryOpen.set(false);
		// Restore focus to the element that was focused before the gallery opened
		if (previouslyFocused) {
			previouslyFocused.focus();
			previouslyFocused = null;
		}
	}

	function handleKeydown(e: KeyboardEvent): void {
		if (e.key === 'Escape') {
			e.preventDefault();
			e.stopPropagation();
			close();
		}
		// Focus trap: keep Tab within the gallery panel
		if (e.key === 'Tab' && panelElement) {
			const focusable = panelElement.querySelectorAll<HTMLElement>(
				'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
			);
			if (focusable.length === 0) return;
			const first = focusable[0];
			const last = focusable[focusable.length - 1];
			if (e.shiftKey) {
				if (document.activeElement === first) {
					e.preventDefault();
					last.focus();
				}
			} else {
				if (document.activeElement === last) {
					e.preventDefault();
					first.focus();
				}
			}
		}
	}

	// When the gallery opens, save the previously focused element and focus the close button
	$effect(() => {
		if ($galleryOpen) {
			previouslyFocused = document.activeElement as HTMLElement | null;
			tick().then(() => {
				const closeBtn = panelElement?.querySelector<HTMLElement>('.gallery-close-btn');
				closeBtn?.focus();
			});
		}
	});

	function modeBadge(mode: string): string {
		return mode.charAt(0).toUpperCase() + mode.slice(1);
	}

	function handleBackdropClick(e: MouseEvent): void {
		if (e.target === e.currentTarget) {
			close();
		}
	}
</script>

<svelte:window onkeydown={$galleryOpen ? handleKeydown : undefined} />

{#if $galleryOpen}
	<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
	<div class="gallery-backdrop" onclick={handleBackdropClick}>
		<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
		<div
			class="gallery-panel"
			bind:this={panelElement}
			onclick={(e) => e.stopPropagation()}
			role="dialog"
			tabindex="-1"
			aria-label="Scene Gallery"
			aria-modal="true"
		>
			<header class="gallery-header">
				<h3 class="gallery-title">Scene Gallery</h3>
				<button class="gallery-close-btn" onclick={close} aria-label="Close gallery">
					<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
						<line x1="4" y1="4" x2="12" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
						<line x1="12" y1="4" x2="4" y2="12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
					</svg>
				</button>
			</header>

			{#if $images.length === 0}
				<div class="gallery-empty">
					<p>No images yet. Use the Illustrate menu to generate scene images.</p>
				</div>
			{:else}
				<div class="image-gallery">
					{#each $images as img (img.id)}
						<div class="gallery-card">
							<img class="gallery-image" src={img.download_url} alt={img.prompt} loading="lazy" />
							<div class="gallery-meta">
								<span class="gallery-label">Turn {img.turn_number + 1}</span>
								<span class="gallery-mode-badge">{modeBadge(img.generation_mode)}</span>
							</div>
							<a
								class="gallery-download-btn"
								href={img.download_url}
								download
								aria-label="Download image for Turn {img.turn_number + 1}"
							>
								<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
									<path d="M8 1v10M4 8l4 4 4-4M2 14h12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none" />
								</svg>
							</a>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}

<style>
	.gallery-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.4);
		z-index: 140;
		display: flex;
		justify-content: flex-end;
		animation: gallery-fade-in 0.15s ease;
	}

	@keyframes gallery-fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	.gallery-panel {
		width: 520px;
		max-width: 90vw;
		height: 100%;
		background: var(--bg-secondary);
		display: flex;
		flex-direction: column;
		overflow: hidden;
		animation: gallery-slide-in 0.2s ease;
	}

	@keyframes gallery-slide-in {
		from { transform: translateX(100%); }
		to { transform: translateX(0); }
	}

	.gallery-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-md) var(--space-lg);
		border-bottom: 1px solid rgba(184, 168, 150, 0.1);
		flex-shrink: 0;
	}

	.gallery-title {
		font-family: var(--font-narrative);
		font-size: 18px;
		font-weight: 600;
		color: var(--color-dm);
		margin: 0;
	}

	.gallery-close-btn {
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 4px;
		border-radius: var(--border-radius-sm);
		transition: color var(--transition-fast);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.gallery-close-btn:hover {
		color: var(--text-primary);
	}

	.gallery-close-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.gallery-empty {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: var(--space-lg);
		text-align: center;
	}

	.gallery-empty p {
		font-family: var(--font-ui);
		font-size: 14px;
		color: var(--text-secondary);
		font-style: italic;
	}

	.image-gallery {
		display: grid;
		grid-template-columns: 1fr 1fr;
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
		transition: border-color var(--transition-fast);
	}

	.gallery-card:hover {
		border-color: rgba(184, 168, 150, 0.25);
	}

	.gallery-image {
		width: 100%;
		aspect-ratio: 16 / 9;
		object-fit: cover;
		display: block;
	}

	.gallery-meta {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--space-xs) var(--space-sm);
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

	/* Responsive */
	@media (max-width: 768px) {
		.gallery-panel {
			width: 100vw;
			max-width: 100vw;
		}

		.image-gallery {
			grid-template-columns: 1fr;
		}
	}
</style>
