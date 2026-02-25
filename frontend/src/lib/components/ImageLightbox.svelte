<script lang="ts">
	import { images, lightboxIndex, compareImages } from '$lib/stores/imageStore';
	import { getImageDownloadUrl } from '$lib/api';

	// Sort images identically to GalleryGrid using shared comparator
	const sortedImages = $derived(
		[...$images].sort(compareImages)
	);
	const currentImage = $derived(
		$lightboxIndex !== null ? sortedImages[$lightboxIndex] ?? null : null
	);
	const canPrev = $derived($lightboxIndex !== null && $lightboxIndex > 0);
	const canNext = $derived(
		$lightboxIndex !== null && $lightboxIndex < sortedImages.length - 1
	);

	function closeLightbox(): void {
		lightboxIndex.set(null);
	}

	function goPrev(): void {
		if ($lightboxIndex !== null && $lightboxIndex > 0) {
			lightboxIndex.set($lightboxIndex - 1);
		}
	}

	function goNext(): void {
		if ($lightboxIndex !== null && $lightboxIndex < sortedImages.length - 1) {
			lightboxIndex.set($lightboxIndex + 1);
		}
	}

	function downloadCurrent(): void {
		if (!currentImage) return;
		const url = getImageDownloadUrl(currentImage.session_id, currentImage.id);
		const a = document.createElement('a');
		a.href = url;
		a.download = '';
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
	}

	function handleKeydown(e: KeyboardEvent): void {
		// Skip if user is typing in an input/textarea/select or contentEditable
		const target = e.target as HTMLElement;
		const tag = target?.tagName;
		if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
		if (target?.isContentEditable) return;

		// ESC is handled by GalleryModal (it checks lightboxIndex first)
		if (e.key === 'ArrowLeft') {
			e.preventDefault();
			goPrev();
		} else if (e.key === 'ArrowRight') {
			e.preventDefault();
			goNext();
		} else if (e.key === 'd' || e.key === 'D') {
			e.preventDefault();
			downloadCurrent();
		}
	}

	function formatTimestamp(iso: string): string {
		return new Date(iso).toLocaleString(undefined, {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function modeBadge(mode: string): string {
		const labels: Record<string, string> = {
			current: 'Current Scene',
			best: 'Best Scene',
			specific: 'Specific Turn'
		};
		return labels[mode] ?? mode;
	}

	function handleBackdropClick(e: MouseEvent): void {
		if (e.target === e.currentTarget) {
			closeLightbox();
		}
	}
</script>

<svelte:window onkeydown={currentImage ? handleKeydown : undefined} />

{#if currentImage}
	<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events a11y_interactive_supports_focus -->
	<div
		class="lightbox-overlay"
		role="dialog"
		aria-modal="true"
		aria-label="Image lightbox"
		tabindex="-1"
		onclick={handleBackdropClick}
	>
		<div class="lightbox-header">
			<a
				class="lightbox-download-btn"
				href={getImageDownloadUrl(currentImage.session_id, currentImage.id)}
				download
				aria-label="Download image"
			>
				<svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
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
			<button class="lightbox-close-btn" onclick={closeLightbox} aria-label="Close lightbox">
				<svg viewBox="0 0 16 16" width="18" height="18" aria-hidden="true">
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

		<button
			class="lightbox-nav-btn lightbox-nav-prev"
			onclick={goPrev}
			disabled={!canPrev}
			aria-label="Previous image"
		>
			<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
				<polyline
					points="15 18 9 12 15 6"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					fill="none"
				/>
			</svg>
		</button>

		<img class="lightbox-image" src={currentImage.download_url} alt={currentImage.prompt} />

		<button
			class="lightbox-nav-btn lightbox-nav-next"
			onclick={goNext}
			disabled={!canNext}
			aria-label="Next image"
		>
			<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">
				<polyline
					points="9 18 15 12 9 6"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					fill="none"
				/>
			</svg>
		</button>

		<div class="lightbox-meta">
			<p class="lightbox-meta-turn">
				Turn {currentImage.turn_number + 1} &bull; {modeBadge(currentImage.generation_mode)}
			</p>
			<p class="lightbox-meta-time">{formatTimestamp(currentImage.generated_at)}</p>
			<p class="lightbox-meta-prompt">{currentImage.prompt}</p>
			<p class="lightbox-meta-model">Model: {currentImage.model}</p>
		</div>
	</div>
{/if}

<style>
	.lightbox-overlay {
		position: fixed;
		inset: 0;
		z-index: 1100;
		background: rgba(0, 0, 0, 0.95);
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		animation: lightbox-fade-in 0.15s ease;
	}

	@keyframes lightbox-fade-in {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	.lightbox-header {
		position: absolute;
		top: var(--space-md);
		right: var(--space-md);
		display: flex;
		gap: var(--space-sm);
		z-index: 1;
	}

	.lightbox-download-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		background: rgba(255, 255, 255, 0.1);
		color: white;
		border-radius: 4px;
		text-decoration: none;
		transition: background var(--transition-fast);
	}

	.lightbox-download-btn:hover {
		background: rgba(255, 255, 255, 0.2);
		text-decoration: none;
	}

	.lightbox-download-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.lightbox-close-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		background: rgba(255, 255, 255, 0.1);
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
		transition: background var(--transition-fast);
	}

	.lightbox-close-btn:hover {
		background: rgba(255, 255, 255, 0.2);
	}

	.lightbox-close-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.lightbox-image {
		max-width: 90vw;
		max-height: 70vh;
		object-fit: contain;
		border-radius: 4px;
	}

	.lightbox-nav-btn {
		position: absolute;
		top: 50%;
		transform: translateY(-50%);
		background: rgba(255, 255, 255, 0.1);
		border: none;
		color: white;
		font-size: 24px;
		padding: var(--space-md);
		cursor: pointer;
		border-radius: 4px;
		transition: background var(--transition-fast);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.lightbox-nav-btn:hover:not(:disabled) {
		background: rgba(255, 255, 255, 0.2);
	}

	.lightbox-nav-btn:disabled {
		opacity: 0.3;
		cursor: default;
	}

	.lightbox-nav-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.lightbox-nav-prev {
		left: var(--space-lg);
	}

	.lightbox-nav-next {
		right: var(--space-lg);
	}

	.lightbox-meta {
		padding: var(--space-md);
		text-align: center;
		color: var(--text-secondary);
		max-width: 600px;
	}

	.lightbox-meta-turn {
		font-family: var(--font-mono);
		font-size: 13px;
		color: var(--accent-warm);
		margin: 0 0 4px 0;
	}

	.lightbox-meta-time {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-secondary);
		margin: 0 0 8px 0;
	}

	.lightbox-meta-prompt {
		font-family: var(--font-ui);
		font-size: 12px;
		color: var(--text-secondary);
		margin: 0 0 4px 0;
		line-height: 1.4;
		font-style: italic;
		max-height: 100px;
		overflow-y: auto;
		word-break: break-word;
	}

	.lightbox-meta-model {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text-secondary);
		margin: 0;
		opacity: 0.7;
	}
</style>
