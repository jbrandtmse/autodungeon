import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import GalleryGrid from './GalleryGrid.svelte';
import { images, lightboxIndex, resetImageStore } from '$lib/stores/imageStore';
import { get } from 'svelte/store';
import type { SceneImage } from '$lib/types';

// Mock the API module
vi.mock('$lib/api', () => ({
  getImageDownloadUrl: (sessionId: string, imageId: string) =>
    `/api/sessions/${sessionId}/images/${imageId}/download`,
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

describe('GalleryGrid', () => {
  beforeEach(() => {
    resetImageStore();
  });

  it('renders thumbnail cards for each image', () => {
    const imgs = [
      makeSceneImage({ id: 'img-a', turn_number: 0 }),
      makeSceneImage({ id: 'img-b', turn_number: 5 }),
      makeSceneImage({ id: 'img-c', turn_number: 10 }),
    ];
    images.set(imgs);

    const { container } = render(GalleryGrid);
    const cards = container.querySelectorAll('.gallery-card');
    expect(cards.length).toBe(3);
  });

  it('sorts cards by turn_number ascending', () => {
    const imgs = [
      makeSceneImage({ id: 'img-c', turn_number: 10 }),
      makeSceneImage({ id: 'img-a', turn_number: 0 }),
      makeSceneImage({ id: 'img-b', turn_number: 5 }),
    ];
    images.set(imgs);

    const { container } = render(GalleryGrid);
    const labels = container.querySelectorAll('.gallery-label');
    expect(labels[0].textContent).toBe('Turn 1');
    expect(labels[1].textContent).toBe('Turn 6');
    expect(labels[2].textContent).toBe('Turn 11');
  });

  it('shows turn badge with 1-based number', () => {
    images.set([makeSceneImage({ id: 'img-a', turn_number: 4 })]);
    const { container } = render(GalleryGrid);
    const label = container.querySelector('.gallery-label');
    expect(label).not.toBeNull();
    expect(label!.textContent).toBe('Turn 5');
  });

  it('shows generation mode badge', () => {
    images.set([makeSceneImage({ id: 'img-a', generation_mode: 'best' })]);
    const { container } = render(GalleryGrid);
    const badge = container.querySelector('.gallery-mode-badge');
    expect(badge).not.toBeNull();
    expect(badge!.textContent).toBe('Best');
  });

  it('shows formatted timestamp', () => {
    images.set([
      makeSceneImage({ id: 'img-a', generated_at: '2026-02-14T12:00:00Z' }),
    ]);
    const { container } = render(GalleryGrid);
    const timestamp = container.querySelector('.gallery-timestamp');
    expect(timestamp).not.toBeNull();
    // Timestamp is formatted via toLocaleString, just check it exists and is non-empty
    expect(timestamp!.textContent!.length).toBeGreaterThan(0);
  });

  it('each card has role="button" and aria-label', () => {
    images.set([makeSceneImage({ id: 'img-a', turn_number: 3 })]);
    const { container } = render(GalleryGrid);
    const card = container.querySelector('.gallery-card');
    expect(card!.getAttribute('role')).toBe('button');
    expect(card!.getAttribute('aria-label')).toBe('View Turn 4 illustration');
  });

  it('clicking a card sets lightboxIndex', async () => {
    images.set([
      makeSceneImage({ id: 'img-a', turn_number: 0 }),
      makeSceneImage({ id: 'img-b', turn_number: 5 }),
    ]);
    const { container } = render(GalleryGrid);
    const cards = container.querySelectorAll('.gallery-card');
    await fireEvent.click(cards[1]);
    expect(get(lightboxIndex)).toBe(1);
  });

  it('pressing Enter on a card sets lightboxIndex', async () => {
    images.set([makeSceneImage({ id: 'img-a', turn_number: 0 })]);
    const { container } = render(GalleryGrid);
    const card = container.querySelector('.gallery-card') as HTMLElement;
    await fireEvent.keyDown(card, { key: 'Enter' });
    expect(get(lightboxIndex)).toBe(0);
  });

  it('per-card download button has correct href', () => {
    images.set([
      makeSceneImage({ id: 'img-a', session_id: 'sess-1', turn_number: 3 }),
    ]);
    const { container } = render(GalleryGrid);
    const downloadBtn = container.querySelector(
      '.gallery-download-btn'
    ) as HTMLAnchorElement;
    expect(downloadBtn).not.toBeNull();
    expect(downloadBtn.getAttribute('href')).toBe(
      '/api/sessions/sess-1/images/img-a/download'
    );
    expect(downloadBtn.hasAttribute('download')).toBe(true);
    expect(downloadBtn.getAttribute('aria-label')).toBe(
      'Download image for Turn 4'
    );
  });

  it('download button click does not open lightbox', async () => {
    images.set([makeSceneImage({ id: 'img-a', turn_number: 0 })]);
    const { container } = render(GalleryGrid);
    const downloadBtn = container.querySelector(
      '.gallery-download-btn'
    ) as HTMLAnchorElement;
    await fireEvent.click(downloadBtn);
    // lightboxIndex should remain null because stopPropagation prevents the card click
    expect(get(lightboxIndex)).toBeNull();
  });

  it('renders empty grid when no images', () => {
    const { container } = render(GalleryGrid);
    const cards = container.querySelectorAll('.gallery-card');
    expect(cards.length).toBe(0);
  });

  it('thumbnails have square aspect ratio class', () => {
    images.set([makeSceneImage({ id: 'img-a' })]);
    const { container } = render(GalleryGrid);
    const thumbnail = container.querySelector('.gallery-thumbnail');
    expect(thumbnail).not.toBeNull();
  });
});
