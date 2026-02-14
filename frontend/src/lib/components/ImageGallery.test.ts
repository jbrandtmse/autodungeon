import { describe, it, expect, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import ImageGallery from './ImageGallery.svelte';
import { images, galleryOpen, resetImageStore } from '$lib/stores/imageStore';
import type { SceneImage } from '$lib/types';

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

describe('ImageGallery', () => {
  beforeEach(() => {
    resetImageStore();
  });

  it('does not render when galleryOpen is false', () => {
    galleryOpen.set(false);
    const { container } = render(ImageGallery);
    const panel = container.querySelector('.gallery-panel');
    expect(panel).toBeNull();
  });

  it('renders when galleryOpen is true', () => {
    galleryOpen.set(true);
    const { container } = render(ImageGallery);
    const panel = container.querySelector('.gallery-panel');
    expect(panel).not.toBeNull();
  });

  it('shows empty state when no images', () => {
    galleryOpen.set(true);
    const { container } = render(ImageGallery);
    const empty = container.querySelector('.gallery-empty');
    expect(empty).not.toBeNull();
    expect(empty!.textContent).toContain('No images yet');
  });

  it('renders grid of images', () => {
    const imgs = [
      makeSceneImage({ id: 'img-a', turn_number: 0, generation_mode: 'current' }),
      makeSceneImage({ id: 'img-b', turn_number: 5, generation_mode: 'best' }),
      makeSceneImage({ id: 'img-c', turn_number: 10, generation_mode: 'specific' }),
    ];
    images.set(imgs);
    galleryOpen.set(true);

    const { container } = render(ImageGallery);
    const cards = container.querySelectorAll('.gallery-card');
    expect(cards.length).toBe(3);
  });

  it('displays correct turn labels (1-based)', () => {
    images.set([makeSceneImage({ id: 'img-a', turn_number: 4 })]);
    galleryOpen.set(true);

    const { container } = render(ImageGallery);
    const label = container.querySelector('.gallery-label');
    expect(label).not.toBeNull();
    expect(label!.textContent).toBe('Turn 5');
  });

  it('displays generation mode badge', () => {
    images.set([makeSceneImage({ id: 'img-a', generation_mode: 'best' })]);
    galleryOpen.set(true);

    const { container } = render(ImageGallery);
    const badge = container.querySelector('.gallery-mode-badge');
    expect(badge).not.toBeNull();
    expect(badge!.textContent).toBe('Best');
  });

  it('has close button', () => {
    galleryOpen.set(true);
    const { container } = render(ImageGallery);
    const closeBtn = container.querySelector('.gallery-close-btn');
    expect(closeBtn).not.toBeNull();
    expect(closeBtn!.getAttribute('aria-label')).toBe('Close gallery');
  });

  it('has gallery download button per image', () => {
    images.set([makeSceneImage({ id: 'img-a', turn_number: 3 })]);
    galleryOpen.set(true);

    const { container } = render(ImageGallery);
    const downloadBtn = container.querySelector('.gallery-download-btn');
    expect(downloadBtn).not.toBeNull();
    // Turn 3 (0-based) = Turn 4 (1-based)
    expect(downloadBtn!.getAttribute('aria-label')).toBe('Download image for Turn 4');
  });

  it('has role="dialog" with aria-label', () => {
    galleryOpen.set(true);
    const { container } = render(ImageGallery);
    const panel = container.querySelector('.gallery-panel');
    expect(panel!.getAttribute('role')).toBe('dialog');
    expect(panel!.getAttribute('aria-label')).toBe('Scene Gallery');
  });

  it('renders gallery title', () => {
    galleryOpen.set(true);
    const { container } = render(ImageGallery);
    const title = container.querySelector('.gallery-title');
    expect(title).not.toBeNull();
    expect(title!.textContent).toBe('Scene Gallery');
  });
});
