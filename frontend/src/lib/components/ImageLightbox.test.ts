import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import ImageLightbox from './ImageLightbox.svelte';
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

describe('ImageLightbox', () => {
  beforeEach(() => {
    resetImageStore();
  });

  it('does not render when lightboxIndex is null', () => {
    images.set([makeSceneImage()]);
    lightboxIndex.set(null);
    const { container } = render(ImageLightbox);
    const overlay = container.querySelector('.lightbox-overlay');
    expect(overlay).toBeNull();
  });

  it('renders when lightboxIndex is a valid number', () => {
    images.set([makeSceneImage()]);
    lightboxIndex.set(0);
    const { container } = render(ImageLightbox);
    const overlay = container.querySelector('.lightbox-overlay');
    expect(overlay).not.toBeNull();
  });

  it('shows correct image based on lightboxIndex', () => {
    const imgs = [
      makeSceneImage({
        id: 'img-a',
        turn_number: 0,
        download_url: '/url-a',
        prompt: 'Scene A',
      }),
      makeSceneImage({
        id: 'img-b',
        turn_number: 5,
        download_url: '/url-b',
        prompt: 'Scene B',
      }),
    ];
    images.set(imgs);
    lightboxIndex.set(1); // Second image (sorted by turn_number)
    const { container } = render(ImageLightbox);
    const img = container.querySelector('.lightbox-image') as HTMLImageElement;
    expect(img.src).toContain('/url-b');
    expect(img.alt).toBe('Scene B');
  });

  it('has role="dialog" and aria-modal="true"', () => {
    images.set([makeSceneImage()]);
    lightboxIndex.set(0);
    const { container } = render(ImageLightbox);
    const overlay = container.querySelector('.lightbox-overlay');
    expect(overlay!.getAttribute('role')).toBe('dialog');
    expect(overlay!.getAttribute('aria-modal')).toBe('true');
    expect(overlay!.getAttribute('aria-label')).toBe('Image lightbox');
  });

  it('shows metadata panel with turn, prompt, mode, timestamp, model', () => {
    images.set([
      makeSceneImage({
        turn_number: 4,
        prompt: 'A magical forest',
        generation_mode: 'best',
        model: 'imagen-3',
        generated_at: '2026-02-14T12:00:00Z',
      }),
    ]);
    lightboxIndex.set(0);
    const { container } = render(ImageLightbox);

    const turnMeta = container.querySelector('.lightbox-meta-turn');
    expect(turnMeta!.textContent).toContain('Turn 5');
    expect(turnMeta!.textContent).toContain('Best Scene');

    const promptMeta = container.querySelector('.lightbox-meta-prompt');
    expect(promptMeta!.textContent).toBe('A magical forest');

    const modelMeta = container.querySelector('.lightbox-meta-model');
    expect(modelMeta!.textContent).toContain('imagen-3');

    const timeMeta = container.querySelector('.lightbox-meta-time');
    expect(timeMeta!.textContent!.length).toBeGreaterThan(0);
  });

  it('has download button with correct href', () => {
    images.set([
      makeSceneImage({ id: 'img-a', session_id: 'sess-1' }),
    ]);
    lightboxIndex.set(0);
    const { container } = render(ImageLightbox);
    const downloadBtn = container.querySelector(
      '.lightbox-download-btn'
    ) as HTMLAnchorElement;
    expect(downloadBtn).not.toBeNull();
    expect(downloadBtn.getAttribute('href')).toBe(
      '/api/sessions/sess-1/images/img-a/download'
    );
    expect(downloadBtn.hasAttribute('download')).toBe(true);
    expect(downloadBtn.getAttribute('aria-label')).toBe('Download image');
  });

  it('has close button that sets lightboxIndex to null', async () => {
    images.set([makeSceneImage()]);
    lightboxIndex.set(0);
    const { container } = render(ImageLightbox);
    const closeBtn = container.querySelector(
      '.lightbox-close-btn'
    ) as HTMLButtonElement;
    expect(closeBtn).not.toBeNull();
    expect(closeBtn.getAttribute('aria-label')).toBe('Close lightbox');
    await fireEvent.click(closeBtn);
    expect(get(lightboxIndex)).toBeNull();
  });

  it('has prev/next navigation buttons', () => {
    images.set([
      makeSceneImage({ id: 'img-a', turn_number: 0 }),
      makeSceneImage({ id: 'img-b', turn_number: 5 }),
      makeSceneImage({ id: 'img-c', turn_number: 10 }),
    ]);
    lightboxIndex.set(1);
    const { container } = render(ImageLightbox);
    const prevBtn = container.querySelector(
      '.lightbox-nav-prev'
    ) as HTMLButtonElement;
    const nextBtn = container.querySelector(
      '.lightbox-nav-next'
    ) as HTMLButtonElement;
    expect(prevBtn).not.toBeNull();
    expect(nextBtn).not.toBeNull();
    expect(prevBtn.getAttribute('aria-label')).toBe('Previous image');
    expect(nextBtn.getAttribute('aria-label')).toBe('Next image');
  });

  it('disables prev button at first image', () => {
    images.set([
      makeSceneImage({ id: 'img-a', turn_number: 0 }),
      makeSceneImage({ id: 'img-b', turn_number: 5 }),
    ]);
    lightboxIndex.set(0);
    const { container } = render(ImageLightbox);
    const prevBtn = container.querySelector(
      '.lightbox-nav-prev'
    ) as HTMLButtonElement;
    expect(prevBtn.disabled).toBe(true);
  });

  it('disables next button at last image', () => {
    images.set([
      makeSceneImage({ id: 'img-a', turn_number: 0 }),
      makeSceneImage({ id: 'img-b', turn_number: 5 }),
    ]);
    lightboxIndex.set(1);
    const { container } = render(ImageLightbox);
    const nextBtn = container.querySelector(
      '.lightbox-nav-next'
    ) as HTMLButtonElement;
    expect(nextBtn.disabled).toBe(true);
  });

  it('clicking prev button navigates to previous image', async () => {
    images.set([
      makeSceneImage({ id: 'img-a', turn_number: 0 }),
      makeSceneImage({ id: 'img-b', turn_number: 5 }),
    ]);
    lightboxIndex.set(1);
    const { container } = render(ImageLightbox);
    const prevBtn = container.querySelector(
      '.lightbox-nav-prev'
    ) as HTMLButtonElement;
    await fireEvent.click(prevBtn);
    expect(get(lightboxIndex)).toBe(0);
  });

  it('clicking next button navigates to next image', async () => {
    images.set([
      makeSceneImage({ id: 'img-a', turn_number: 0 }),
      makeSceneImage({ id: 'img-b', turn_number: 5 }),
    ]);
    lightboxIndex.set(0);
    const { container } = render(ImageLightbox);
    const nextBtn = container.querySelector(
      '.lightbox-nav-next'
    ) as HTMLButtonElement;
    await fireEvent.click(nextBtn);
    expect(get(lightboxIndex)).toBe(1);
  });

  it('ArrowLeft key navigates to previous image', async () => {
    images.set([
      makeSceneImage({ id: 'img-a', turn_number: 0 }),
      makeSceneImage({ id: 'img-b', turn_number: 5 }),
    ]);
    lightboxIndex.set(1);
    render(ImageLightbox);
    await fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(get(lightboxIndex)).toBe(0);
  });

  it('ArrowRight key navigates to next image', async () => {
    images.set([
      makeSceneImage({ id: 'img-a', turn_number: 0 }),
      makeSceneImage({ id: 'img-b', turn_number: 5 }),
    ]);
    lightboxIndex.set(0);
    render(ImageLightbox);
    await fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(get(lightboxIndex)).toBe(1);
  });

  it('ArrowLeft does not go below 0', async () => {
    images.set([makeSceneImage({ id: 'img-a', turn_number: 0 })]);
    lightboxIndex.set(0);
    render(ImageLightbox);
    await fireEvent.keyDown(window, { key: 'ArrowLeft' });
    expect(get(lightboxIndex)).toBe(0);
  });

  it('ArrowRight does not go beyond last image', async () => {
    images.set([makeSceneImage({ id: 'img-a', turn_number: 0 })]);
    lightboxIndex.set(0);
    render(ImageLightbox);
    await fireEvent.keyDown(window, { key: 'ArrowRight' });
    expect(get(lightboxIndex)).toBe(0);
  });

  it('clicking backdrop closes lightbox', async () => {
    images.set([makeSceneImage()]);
    lightboxIndex.set(0);
    const { container } = render(ImageLightbox);
    const overlay = container.querySelector('.lightbox-overlay') as HTMLElement;
    // Simulate click on the overlay itself (not a child)
    await fireEvent.click(overlay);
    expect(get(lightboxIndex)).toBeNull();
  });

  it('renders with single image correctly', () => {
    images.set([makeSceneImage({ id: 'img-a', turn_number: 0 })]);
    lightboxIndex.set(0);
    const { container } = render(ImageLightbox);
    const prevBtn = container.querySelector(
      '.lightbox-nav-prev'
    ) as HTMLButtonElement;
    const nextBtn = container.querySelector(
      '.lightbox-nav-next'
    ) as HTMLButtonElement;
    // Both should be disabled with a single image
    expect(prevBtn.disabled).toBe(true);
    expect(nextBtn.disabled).toBe(true);
  });

  it('mode badge shows correct labels', () => {
    images.set([
      makeSceneImage({
        id: 'img-a',
        turn_number: 0,
        generation_mode: 'specific',
      }),
    ]);
    lightboxIndex.set(0);
    const { container } = render(ImageLightbox);
    const turnMeta = container.querySelector('.lightbox-meta-turn');
    expect(turnMeta!.textContent).toContain('Specific Turn');
  });
});
