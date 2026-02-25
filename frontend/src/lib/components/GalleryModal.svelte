<script lang="ts">
	import { tick } from 'svelte';
	import { images, galleryOpen, lightboxIndex } from '$lib/stores/imageStore';
	import { getDownloadAllUrl } from '$lib/api';
	import GalleryGrid from './GalleryGrid.svelte';
	import ImageLightbox from './ImageLightbox.svelte';

	let modalElement: HTMLElement | undefined = $state();
	let previouslyFocused: HTMLElement | null = null;

	const sessionId = $derived($images.length > 0 ? $images[0].session_id : '');
	const hasImages = $derived($images.length > 0);

	function close(): void {
		galleryOpen.set(false);
		lightboxIndex.set(null);
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
			// If lightbox is open, close it first; otherwise close gallery
			if ($lightboxIndex !== null) {
				lightboxIndex.set(null);
			} else {
				close();
			}
		}
		// Focus trap: keep Tab within the gallery modal
		if (e.key === 'Tab' && modalElement) {
			const focusable = modalElement.querySelectorAll<HTMLElement>(
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
				const closeBtn = modalElement?.querySelector<HTMLElement>('.gallery-close-btn');
				closeBtn?.focus();
			});
		}
	});

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
			class="gallery-modal"
			bind:this={modalElement}
			onclick={(e) => e.stopPropagation()}
			role="dialog"
			tabindex="-1"
			aria-label="Illustration Gallery"
			aria-modal="true"
		>
			<header class="gallery-header">
				<h3 class="gallery-title">Illustration Gallery</h3>
				<div class="gallery-header-actions">
					{#if hasImages}
						<a
							class="gallery-download-all-btn"
							href={getDownloadAllUrl(sessionId)}
							download
							aria-label="Download all images as zip"
						>
							<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
								<path
									d="M8 1v10M4 8l4 4 4-4M2 14h12"
									stroke="currentColor"
									stroke-width="1.5"
									stroke-linecap="round"
									stroke-linejoin="round"
									fill="none"
								/>
							</svg>
							Download All
						</a>
					{:else}
						<span class="gallery-download-all-btn disabled" title="No images to download">
							Download All
						</span>
					{/if}
					<button class="gallery-close-btn" onclick={close} aria-label="Close gallery">
						<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
							<line
								x1="4"
								y1="4"
								x2="12"
								y2="12"
								stroke="currentColor"
								stroke-width="1.5"
								stroke-linecap="round"
							/>
							<line
								x1="12"
								y1="4"
								x2="4"
								y2="12"
								stroke="currentColor"
								stroke-width="1.5"
								stroke-linecap="round"
							/>
						</svg>
					</button>
				</div>
			</header>

			{#if $images.length === 0}
				<div class="gallery-empty">
					<p>No images yet. Use the Illustrate menu to generate scene images.</p>
				</div>
			{:else}
				<GalleryGrid />
			{/if}
		</div>
	</div>

	{#if $lightboxIndex !== null}
		<ImageLightbox />
	{/if}
{/if}

<style>
	.gallery-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.8);
		z-index: 1000;
		display: flex;
		align-items: center;
		justify-content: center;
		animation: gallery-fade-in 0.15s ease;
	}

	@keyframes gallery-fade-in {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	.gallery-modal {
		width: 80vw;
		height: 80vh;
		background: var(--bg-secondary);
		border-radius: 12px;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		animation: gallery-scale-in 0.2s ease;
	}

	@keyframes gallery-scale-in {
		from {
			transform: scale(0.95);
			opacity: 0;
		}
		to {
			transform: scale(1);
			opacity: 1;
		}
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

	.gallery-header-actions {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
	}

	.gallery-download-all-btn {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 4px 10px;
		background: rgba(232, 168, 73, 0.15);
		color: var(--accent-warm);
		border: 1px solid rgba(232, 168, 73, 0.3);
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 12px;
		font-weight: 500;
		text-decoration: none;
		cursor: pointer;
		transition:
			background var(--transition-fast),
			border-color var(--transition-fast);
	}

	.gallery-download-all-btn:hover {
		background: rgba(232, 168, 73, 0.25);
		border-color: rgba(232, 168, 73, 0.5);
		text-decoration: none;
	}

	.gallery-download-all-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.gallery-download-all-btn.disabled {
		opacity: 0.4;
		cursor: not-allowed;
		pointer-events: none;
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

	/* Responsive */
	@media (max-width: 768px) {
		.gallery-modal {
			width: 95vw;
			height: 90vh;
			border-radius: 8px;
		}
	}
</style>
