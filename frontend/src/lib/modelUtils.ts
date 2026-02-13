/**
 * Shared model fetching utilities for ModelsTab and CharacterCreator.
 *
 * Provides dynamic model listing from the API with an in-memory cache,
 * and static fallbacks when the API is unavailable.
 */

import { getModels, type ModelListResult } from '$lib/api';

export const PROVIDERS = ['gemini', 'anthropic', 'ollama'] as const;
export type Provider = (typeof PROVIDERS)[number];

export const PROVIDER_DISPLAY: Record<Provider, string> = {
	gemini: 'Gemini',
	anthropic: 'Claude',
	ollama: 'Ollama',
};

export const FALLBACK_MODELS: Record<Provider, string[]> = {
	gemini: [
		'gemini-3-flash-preview',
		'gemini-2.0-flash',
		'gemini-1.5-pro',
		'gemini-2.5-flash-preview-05-20',
		'gemini-2.5-pro-preview-05-06',
		'gemini-3-pro-preview',
	],
	anthropic: [
		'claude-sonnet-4-20250514',
		'claude-3-5-sonnet-20241022',
		'claude-3-haiku-20240307',
	],
	ollama: ['llama3', 'mistral', 'phi3', 'qwen3:14b'],
};

/** In-memory cache: provider -> { models, source, timestamp } */
const cache = new Map<string, { models: string[]; source: string; ts: number }>();
const CACHE_TTL = 60_000; // 60 seconds

/** In-flight deduplication: provider -> pending promise */
const inFlight = new Map<string, Promise<{ models: string[]; source: 'api' | 'fallback' }>>();

/**
 * Normalize provider name for the API call.
 * The API accepts both "claude" and "anthropic" but normalizes to "anthropic".
 */
function normalizeProvider(provider: string): Provider {
	const lower = provider.toLowerCase();
	if (lower === 'claude') return 'anthropic';
	if (lower === 'gemini' || lower === 'anthropic' || lower === 'ollama') {
		return lower as Provider;
	}
	return 'gemini'; // fallback
}

/**
 * Fetch models for a provider from the API, with caching.
 * Returns the model list and source indicator.
 */
export async function fetchModelsForProvider(
	provider: string,
): Promise<{ models: string[]; source: 'api' | 'fallback' }> {
	const normalized = normalizeProvider(provider);

	// Check cache
	const cached = cache.get(normalized);
	if (cached && Date.now() - cached.ts < CACHE_TTL) {
		return { models: cached.models, source: cached.source as 'api' | 'fallback' };
	}

	// Return existing in-flight request if one is pending (deduplication)
	const pending = inFlight.get(normalized);
	if (pending) return pending;

	// Start new fetch and track the promise
	const promise = (async (): Promise<{ models: string[]; source: 'api' | 'fallback' }> => {
		try {
			const result: ModelListResult = await getModels(normalized);
			const models =
				result.models.length > 0 ? result.models : getFallbackModels(normalized);
			cache.set(normalized, { models, source: result.source, ts: Date.now() });
			return { models, source: result.source };
		} catch {
			// API completely unreachable — use fallbacks
			const models = getFallbackModels(normalized);
			cache.set(normalized, { models, source: 'fallback', ts: Date.now() });
			return { models, source: 'fallback' };
		} finally {
			inFlight.delete(normalized);
		}
	})();

	inFlight.set(normalized, promise);
	return promise;
}

/** Get static fallback models for a provider. */
export function getFallbackModels(provider: string): string[] {
	const normalized = normalizeProvider(provider);
	return FALLBACK_MODELS[normalized] ?? FALLBACK_MODELS.gemini;
}

/** Clear the model cache. Call after saving API keys. */
export function clearModelCache(): void {
	cache.clear();
}
