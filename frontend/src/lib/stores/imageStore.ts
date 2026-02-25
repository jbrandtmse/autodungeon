import { get, writable } from 'svelte/store';
import type { SceneImage, SessionImageSummary } from '$lib/types';
import { getSessionImages, getSessionImageSummaries } from '$lib/api';

/** All generated images for the current session. */
export const images = writable<SceneImage[]>([]);

/** Turn numbers with in-progress generation (for loading placeholders). */
export const generatingTurns = writable<Set<number>>(new Set());

/** Whether a "best scene" scan is running. */
export const generatingBest = writable<boolean>(false);

/** Gallery panel visibility. */
export const galleryOpen = writable<boolean>(false);

/** Index of the image currently open in lightbox (null = closed). */
export const lightboxIndex = writable<number | null>(null);

/** Which session the gallery is currently showing (null = not set). */
export const gallerySessionId = writable<string | null>(null);

/** Cached session image summaries for session switcher dropdown. */
export const sessionImageSummaries = writable<SessionImageSummary[]>([]);

/**
 * Sort comparator for gallery images: ascending by turn_number,
 * then by generated_at timestamp for stable ordering when multiple
 * images share the same turn_number (e.g., "current" + "best" mode).
 * MUST be used by both GalleryGrid and ImageLightbox to keep
 * lightboxIndex consistent between the two components.
 */
export function compareImages(a: SceneImage, b: SceneImage): number {
	if (a.turn_number !== b.turn_number) return a.turn_number - b.turn_number;
	return a.generated_at.localeCompare(b.generated_at);
}

/**
 * Called when a WebSocket image_ready event arrives.
 * Appends the image and clears generation state.
 * Ignores images from sessions other than the one currently displayed
 * in the gallery (prevents cross-session contamination when the gallery
 * is showing a different session via the session switcher).
 */
export function handleImageReady(image: SceneImage): void {
	// Cross-session guard: only append if the image belongs to the session
	// currently being viewed, or if no gallery session is set yet.
	// Prevents WebSocket image_ready from a different session contaminating
	// the gallery when the user has switched sessions via the session switcher.
	const currentSessionId = get(gallerySessionId);
	if (currentSessionId && image.session_id !== currentSessionId) return;

	images.update((list) => {
		// Deduplicate: skip if an image with the same id already exists
		// (guards against WebSocket reconnect re-delivery or race with loadSessionImages)
		if (list.some((existing) => existing.id === image.id)) return list;
		return [...list, image];
	});
	generatingTurns.update((s) => {
		const next = new Set(s);
		next.delete(image.turn_number);
		return next;
	});
	if (image.generation_mode === 'best') {
		generatingBest.set(false);
	}
}

/**
 * Mark a turn number as having an in-progress generation.
 */
export function startGeneration(turnNumber: number): void {
	generatingTurns.update((s) => {
		const next = new Set(s);
		next.add(turnNumber);
		return next;
	});
}

/**
 * Mark a "best scene" scan as running.
 */
export function startBestGeneration(): void {
	generatingBest.set(true);
}

/**
 * Load existing images for a session from the REST API.
 */
export async function loadSessionImages(sessionId: string): Promise<void> {
	try {
		const list = await getSessionImages(sessionId);
		images.set(list);
		gallerySessionId.set(sessionId);
	} catch (e) {
		console.error('[ImageStore] Failed to load images:', e);
	}
}

/**
 * Load session image summaries from the REST API (for session switcher dropdown).
 * Uses a simple cache: skips the API call if summaries are already populated.
 * Pass `force: true` to bypass the cache (e.g., after generating a new image).
 */
export async function loadSessionImageSummaries(force = false): Promise<void> {
	if (!force && get(sessionImageSummaries).length > 0) return;
	try {
		const summaries = await getSessionImageSummaries();
		sessionImageSummaries.set(summaries);
	} catch (e) {
		console.error('[ImageStore] Failed to load image summaries:', e);
	}
}

/**
 * Reset all image stores to initial state.
 */
export function resetImageStore(): void {
	images.set([]);
	generatingTurns.set(new Set());
	generatingBest.set(false);
	galleryOpen.set(false);
	lightboxIndex.set(null);
	gallerySessionId.set(null);
	sessionImageSummaries.set([]);
}
