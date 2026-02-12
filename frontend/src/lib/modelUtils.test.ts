import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchModelsForProvider, getFallbackModels, clearModelCache, FALLBACK_MODELS } from './modelUtils';

// Mock the api module
vi.mock('$lib/api', () => ({
	getModels: vi.fn(),
}));

import { getModels } from '$lib/api';
const mockGetModels = vi.mocked(getModels);

describe('modelUtils', () => {
	beforeEach(() => {
		clearModelCache();
		vi.clearAllMocks();
	});

	describe('getFallbackModels', () => {
		it('returns gemini models for gemini provider', () => {
			const models = getFallbackModels('gemini');
			expect(models).toEqual(FALLBACK_MODELS.gemini);
		});

		it('returns anthropic models for claude provider', () => {
			const models = getFallbackModels('claude');
			expect(models).toEqual(FALLBACK_MODELS.anthropic);
		});

		it('returns anthropic models for anthropic provider', () => {
			const models = getFallbackModels('anthropic');
			expect(models).toEqual(FALLBACK_MODELS.anthropic);
		});

		it('returns ollama models for ollama provider', () => {
			const models = getFallbackModels('ollama');
			expect(models).toEqual(FALLBACK_MODELS.ollama);
		});

		it('returns gemini models as fallback for unknown provider', () => {
			const models = getFallbackModels('unknown');
			expect(models).toEqual(FALLBACK_MODELS.gemini);
		});
	});

	describe('fetchModelsForProvider', () => {
		it('fetches models from API', async () => {
			mockGetModels.mockResolvedValue({
				provider: 'gemini',
				models: ['gemini-pro', 'gemini-flash'],
				source: 'api',
				error: null,
			});

			const result = await fetchModelsForProvider('gemini');
			expect(result.models).toEqual(['gemini-pro', 'gemini-flash']);
			expect(result.source).toBe('api');
			expect(mockGetModels).toHaveBeenCalledWith('gemini');
		});

		it('normalizes claude to anthropic', async () => {
			mockGetModels.mockResolvedValue({
				provider: 'anthropic',
				models: ['claude-3-haiku'],
				source: 'api',
				error: null,
			});

			await fetchModelsForProvider('claude');
			expect(mockGetModels).toHaveBeenCalledWith('anthropic');
		});

		it('uses cache on second call', async () => {
			mockGetModels.mockResolvedValue({
				provider: 'gemini',
				models: ['gemini-pro'],
				source: 'api',
				error: null,
			});

			await fetchModelsForProvider('gemini');
			await fetchModelsForProvider('gemini');
			// Only one API call
			expect(mockGetModels).toHaveBeenCalledTimes(1);
		});

		it('returns fallback when API fails', async () => {
			mockGetModels.mockRejectedValue(new Error('Network error'));

			const result = await fetchModelsForProvider('gemini');
			expect(result.source).toBe('fallback');
			expect(result.models).toEqual(FALLBACK_MODELS.gemini);
		});

		it('uses fallback when API returns empty models', async () => {
			mockGetModels.mockResolvedValue({
				provider: 'ollama',
				models: [],
				source: 'api',
				error: null,
			});

			const result = await fetchModelsForProvider('ollama');
			expect(result.models).toEqual(FALLBACK_MODELS.ollama);
		});
	});

	describe('clearModelCache', () => {
		it('forces refetch after clearing', async () => {
			mockGetModels.mockResolvedValue({
				provider: 'gemini',
				models: ['gemini-pro'],
				source: 'api',
				error: null,
			});

			await fetchModelsForProvider('gemini');
			clearModelCache();
			await fetchModelsForProvider('gemini');
			expect(mockGetModels).toHaveBeenCalledTimes(2);
		});
	});
});
