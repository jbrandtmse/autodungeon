import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import GalleryModal from './GalleryModal.svelte';
import { images, galleryOpen, lightboxIndex, resetImageStore } from '$lib/stores/imageStore';
import { get } from 'svelte/store';
import type { SceneImage } from '$lib/types';

// Mock the API module
vi.mock('$lib/api', () => ({
  getDownloadAllUrl: (sessionId: string) => `/api/sessions/${sessionId}/images/download-all`,
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

describe('GalleryModal', () => {
  beforeEach(() => {
    resetImageStore();
  });

  it('does not render when galleryOpen is false', () => {
    galleryOpen.set(false);
    const { container } = render(GalleryModal);
    const modal = container.querySelector('.gallery-modal');
    expect(modal).toBeNull();
  });

  it('renders when galleryOpen is true', () => {
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const modal = container.querySelector('.gallery-modal');
    expect(modal).not.toBeNull();
  });

  it('shows centered modal (not side panel)', () => {
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const modal = container.querySelector('.gallery-modal');
    expect(modal).not.toBeNull();
    // Should NOT have old gallery-panel class
    const oldPanel = container.querySelector('.gallery-panel');
    expect(oldPanel).toBeNull();
  });

  it('shows empty state when no images', () => {
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const empty = container.querySelector('.gallery-empty');
    expect(empty).not.toBeNull();
    expect(empty!.textContent).toContain('No images yet');
  });

  it('does not show empty state when images exist', () => {
    images.set([makeSceneImage()]);
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const empty = container.querySelector('.gallery-empty');
    expect(empty).toBeNull();
  });

  it('has close button with correct aria-label', () => {
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const closeBtn = container.querySelector('.gallery-close-btn');
    expect(closeBtn).not.toBeNull();
    expect(closeBtn!.getAttribute('aria-label')).toBe('Close gallery');
  });

  it('has role="dialog" with aria-modal and aria-label', () => {
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const modal = container.querySelector('.gallery-modal');
    expect(modal!.getAttribute('role')).toBe('dialog');
    expect(modal!.getAttribute('aria-modal')).toBe('true');
    expect(modal!.getAttribute('aria-label')).toBe('Illustration Gallery');
  });

  it('renders gallery title', () => {
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const title = container.querySelector('.gallery-title');
    expect(title).not.toBeNull();
    expect(title!.textContent).toBe('Illustration Gallery');
  });

  it('shows "Download All" button when images exist', () => {
    images.set([makeSceneImage({ id: 'img-a', session_id: 'sess-1' })]);
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const downloadAllBtn = container.querySelector(
      '.gallery-download-all-btn'
    ) as HTMLAnchorElement;
    expect(downloadAllBtn).not.toBeNull();
    expect(downloadAllBtn.textContent).toContain('Download All');
    expect(downloadAllBtn.getAttribute('href')).toBe(
      '/api/sessions/sess-1/images/download-all'
    );
    expect(downloadAllBtn.hasAttribute('download')).toBe(true);
    expect(downloadAllBtn.getAttribute('aria-label')).toBe('Download all images as zip');
  });

  it('shows disabled "Download All" when no images', () => {
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const downloadAllBtn = container.querySelector('.gallery-download-all-btn');
    expect(downloadAllBtn).not.toBeNull();
    expect(downloadAllBtn!.classList.contains('disabled')).toBe(true);
    expect(downloadAllBtn!.getAttribute('title')).toBe('No images to download');
    // Disabled version is a <span>, not <a>
    expect(downloadAllBtn!.tagName).toBe('SPAN');
  });

  it('has gallery-header-actions container', () => {
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const actions = container.querySelector('.gallery-header-actions');
    expect(actions).not.toBeNull();
  });

  it('closes gallery when close button is clicked', async () => {
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const closeBtn = container.querySelector('.gallery-close-btn') as HTMLButtonElement;
    await fireEvent.click(closeBtn);
    expect(get(galleryOpen)).toBe(false);
  });

  it('ESC closes gallery when lightbox is not open', async () => {
    galleryOpen.set(true);
    lightboxIndex.set(null);
    render(GalleryModal);
    await fireEvent.keyDown(window, { key: 'Escape' });
    expect(get(galleryOpen)).toBe(false);
  });

  it('ESC closes lightbox first when lightbox is open', async () => {
    images.set([makeSceneImage()]);
    galleryOpen.set(true);
    lightboxIndex.set(0);
    render(GalleryModal);
    await fireEvent.keyDown(window, { key: 'Escape' });
    // Lightbox should close
    expect(get(lightboxIndex)).toBeNull();
    // Gallery should remain open
    expect(get(galleryOpen)).toBe(true);
  });

  it('closes gallery when backdrop is clicked', async () => {
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const backdrop = container.querySelector('.gallery-backdrop') as HTMLElement;
    await fireEvent.click(backdrop);
    expect(get(galleryOpen)).toBe(false);
  });

  it('does not close gallery when modal content is clicked', async () => {
    galleryOpen.set(true);
    const { container } = render(GalleryModal);
    const modal = container.querySelector('.gallery-modal') as HTMLElement;
    await fireEvent.click(modal);
    expect(get(galleryOpen)).toBe(true);
  });

  it('resets lightboxIndex when gallery closes', async () => {
    images.set([makeSceneImage()]);
    galleryOpen.set(true);
    lightboxIndex.set(0);
    const { container } = render(GalleryModal);
    const closeBtn = container.querySelector('.gallery-close-btn') as HTMLButtonElement;
    await fireEvent.click(closeBtn);
    expect(get(lightboxIndex)).toBeNull();
    expect(get(galleryOpen)).toBe(false);
  });
});
