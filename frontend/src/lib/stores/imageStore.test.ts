import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';
import {
  images,
  generatingTurns,
  generatingBest,
  galleryOpen,
  lightboxIndex,
  gallerySessionId,
  sessionImageSummaries,
  compareImages,
  handleImageReady,
  startGeneration,
  startBestGeneration,
  resetImageStore,
  loadSessionImages,
  loadSessionImageSummaries,
} from './imageStore';
import type { SceneImage, SessionImageSummary } from '$lib/types';

// Mock the API module at the top level (hoisted by Vitest)
const mockGetSessionImages = vi.fn();
const mockGetSessionImageSummaries = vi.fn();
vi.mock('$lib/api', () => ({
  getSessionImages: (...args: unknown[]) => mockGetSessionImages(...args),
  getSessionImageSummaries: (...args: unknown[]) => mockGetSessionImageSummaries(...args),
}));

function makeSceneImage(overrides: Partial<SceneImage> = {}): SceneImage {
  return {
    id: 'img-001',
    session_id: 'session-001',
    turn_number: 5,
    prompt: 'A dark cavern with glowing crystals',
    image_path: 'campaigns/session_001/images/img-001.png',
    provider: 'gemini',
    model: 'imagen-3',
    generation_mode: 'current',
    generated_at: '2026-02-14T12:00:00Z',
    download_url: '/api/sessions/session-001/images/img-001.png',
    ...overrides,
  };
}

describe('imageStore', () => {
  beforeEach(() => {
    resetImageStore();
  });

  describe('handleImageReady', () => {
    it('appends image to images store', () => {
      const img = makeSceneImage();
      handleImageReady(img);
      expect(get(images)).toEqual([img]);
    });

    it('appends multiple images', () => {
      const img1 = makeSceneImage({ id: 'img-001', turn_number: 3 });
      const img2 = makeSceneImage({ id: 'img-002', turn_number: 7 });
      handleImageReady(img1);
      handleImageReady(img2);
      expect(get(images)).toHaveLength(2);
      expect(get(images)[0].id).toBe('img-001');
      expect(get(images)[1].id).toBe('img-002');
    });

    it('removes turn_number from generatingTurns', () => {
      startGeneration(5);
      expect(get(generatingTurns).has(5)).toBe(true);
      handleImageReady(makeSceneImage({ turn_number: 5 }));
      expect(get(generatingTurns).has(5)).toBe(false);
    });

    it('clears generatingBest when generation_mode is best', () => {
      startBestGeneration();
      expect(get(generatingBest)).toBe(true);
      handleImageReady(makeSceneImage({ generation_mode: 'best' }));
      expect(get(generatingBest)).toBe(false);
    });

    it('does not clear generatingBest when generation_mode is not best', () => {
      startBestGeneration();
      handleImageReady(makeSceneImage({ generation_mode: 'current' }));
      expect(get(generatingBest)).toBe(true);
    });
  });

  describe('startGeneration', () => {
    it('adds turn number to generatingTurns', () => {
      startGeneration(3);
      expect(get(generatingTurns).has(3)).toBe(true);
    });

    it('can track multiple turn numbers', () => {
      startGeneration(1);
      startGeneration(5);
      startGeneration(10);
      const gen = get(generatingTurns);
      expect(gen.has(1)).toBe(true);
      expect(gen.has(5)).toBe(true);
      expect(gen.has(10)).toBe(true);
    });
  });

  describe('startBestGeneration', () => {
    it('sets generatingBest to true', () => {
      expect(get(generatingBest)).toBe(false);
      startBestGeneration();
      expect(get(generatingBest)).toBe(true);
    });
  });

  describe('resetImageStore', () => {
    it('resets all stores to defaults', () => {
      handleImageReady(makeSceneImage());
      startGeneration(3);
      startBestGeneration();
      galleryOpen.set(true);
      lightboxIndex.set(2);
      gallerySessionId.set('sess-123');
      sessionImageSummaries.set([
        { session_id: 'sess-123', session_name: 'Test', image_count: 5 },
      ]);

      resetImageStore();

      expect(get(images)).toEqual([]);
      expect(get(generatingTurns).size).toBe(0);
      expect(get(generatingBest)).toBe(false);
      expect(get(galleryOpen)).toBe(false);
      expect(get(lightboxIndex)).toBeNull();
      expect(get(gallerySessionId)).toBeNull();
      expect(get(sessionImageSummaries)).toEqual([]);
    });
  });

  describe('loadSessionImages', () => {
    beforeEach(() => {
      mockGetSessionImages.mockReset();
    });

    it('populates images from API (mocked)', async () => {
      const mockImages = [
        makeSceneImage({ id: 'img-a', turn_number: 0 }),
        makeSceneImage({ id: 'img-b', turn_number: 5 }),
      ];
      mockGetSessionImages.mockResolvedValue(mockImages);

      await loadSessionImages('session-001');

      expect(get(images)).toEqual(mockImages);
      expect(mockGetSessionImages).toHaveBeenCalledWith('session-001');
    });

    it('sets gallerySessionId when loading images', async () => {
      mockGetSessionImages.mockResolvedValue([]);

      await loadSessionImages('session-042');

      expect(get(gallerySessionId)).toBe('session-042');
    });

    it('handles API error gracefully', async () => {
      mockGetSessionImages.mockRejectedValue(new Error('Network error'));
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      await loadSessionImages('session-001');

      // Should not throw, images remain empty
      expect(get(images)).toEqual([]);
      consoleSpy.mockRestore();
    });
  });

  describe('galleryOpen', () => {
    it('defaults to false', () => {
      expect(get(galleryOpen)).toBe(false);
    });

    it('can be toggled', () => {
      galleryOpen.set(true);
      expect(get(galleryOpen)).toBe(true);
      galleryOpen.set(false);
      expect(get(galleryOpen)).toBe(false);
    });
  });

  describe('lightboxIndex', () => {
    it('defaults to null', () => {
      expect(get(lightboxIndex)).toBeNull();
    });

    it('can be set to a number', () => {
      lightboxIndex.set(3);
      expect(get(lightboxIndex)).toBe(3);
    });

    it('can be set back to null', () => {
      lightboxIndex.set(5);
      lightboxIndex.set(null);
      expect(get(lightboxIndex)).toBeNull();
    });

    it('is cleared by resetImageStore', () => {
      lightboxIndex.set(2);
      resetImageStore();
      expect(get(lightboxIndex)).toBeNull();
    });
  });

  describe('compareImages', () => {
    it('sorts by turn_number ascending', () => {
      const a = makeSceneImage({ turn_number: 10, generated_at: '2026-01-01T00:00:00Z' });
      const b = makeSceneImage({ turn_number: 5, generated_at: '2026-01-01T00:00:00Z' });
      expect(compareImages(a, b)).toBeGreaterThan(0);
      expect(compareImages(b, a)).toBeLessThan(0);
    });

    it('uses generated_at as tiebreaker for same turn_number', () => {
      const a = makeSceneImage({ turn_number: 5, generated_at: '2026-02-14T14:00:00Z' });
      const b = makeSceneImage({ turn_number: 5, generated_at: '2026-02-14T12:00:00Z' });
      expect(compareImages(a, b)).toBeGreaterThan(0);
      expect(compareImages(b, a)).toBeLessThan(0);
    });

    it('returns 0 for identical turn_number and generated_at', () => {
      const a = makeSceneImage({ turn_number: 5, generated_at: '2026-02-14T12:00:00Z' });
      const b = makeSceneImage({ turn_number: 5, generated_at: '2026-02-14T12:00:00Z' });
      expect(compareImages(a, b)).toBe(0);
    });
  });

  describe('gallerySessionId', () => {
    it('defaults to null', () => {
      expect(get(gallerySessionId)).toBeNull();
    });

    it('can be set to a string', () => {
      gallerySessionId.set('session-abc');
      expect(get(gallerySessionId)).toBe('session-abc');
    });

    it('can be set back to null', () => {
      gallerySessionId.set('session-abc');
      gallerySessionId.set(null);
      expect(get(gallerySessionId)).toBeNull();
    });

    it('is cleared by resetImageStore', () => {
      gallerySessionId.set('session-abc');
      resetImageStore();
      expect(get(gallerySessionId)).toBeNull();
    });
  });

  describe('sessionImageSummaries', () => {
    it('defaults to empty array', () => {
      expect(get(sessionImageSummaries)).toEqual([]);
    });

    it('can be set to a list of summaries', () => {
      const summaries: SessionImageSummary[] = [
        { session_id: '001', session_name: 'Alpha', image_count: 5 },
        { session_id: '002', session_name: 'Beta', image_count: 3 },
      ];
      sessionImageSummaries.set(summaries);
      expect(get(sessionImageSummaries)).toEqual(summaries);
    });

    it('is cleared by resetImageStore', () => {
      sessionImageSummaries.set([
        { session_id: '001', session_name: 'Alpha', image_count: 5 },
      ]);
      resetImageStore();
      expect(get(sessionImageSummaries)).toEqual([]);
    });
  });

  describe('loadSessionImageSummaries', () => {
    beforeEach(() => {
      mockGetSessionImageSummaries.mockReset();
    });

    it('populates sessionImageSummaries from API', async () => {
      const mockSummaries: SessionImageSummary[] = [
        { session_id: '001', session_name: 'Alpha', image_count: 5 },
        { session_id: '002', session_name: 'Beta', image_count: 3 },
      ];
      mockGetSessionImageSummaries.mockResolvedValue(mockSummaries);

      await loadSessionImageSummaries();

      expect(get(sessionImageSummaries)).toEqual(mockSummaries);
      expect(mockGetSessionImageSummaries).toHaveBeenCalled();
    });

    it('handles API error gracefully', async () => {
      mockGetSessionImageSummaries.mockRejectedValue(new Error('Network error'));
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      await loadSessionImageSummaries();

      // Should not throw, summaries remain empty
      expect(get(sessionImageSummaries)).toEqual([]);
      consoleSpy.mockRestore();
    });
  });
});
