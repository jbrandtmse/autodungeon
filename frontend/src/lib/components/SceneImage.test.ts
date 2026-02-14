import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import SceneImage from './SceneImage.svelte';
import type { SceneImage as SceneImageType } from '$lib/types';

function makeSceneImage(overrides: Partial<SceneImageType> = {}): SceneImageType {
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

describe('SceneImage', () => {
  it('renders image with correct src and alt', () => {
    const image = makeSceneImage();
    const { container } = render(SceneImage, { props: { image } });

    const img = container.querySelector('img.scene-image');
    expect(img).not.toBeNull();
    expect(img!.getAttribute('src')).toBe(image.download_url);
    expect(img!.getAttribute('alt')).toBe(image.prompt);
  });

  it('has scene-image-container wrapper', () => {
    const image = makeSceneImage();
    const { container } = render(SceneImage, { props: { image } });

    const wrapper = container.querySelector('.scene-image-container');
    expect(wrapper).not.toBeNull();
  });

  it('has download button with correct aria-label', () => {
    const image = makeSceneImage({ turn_number: 9 });
    const { container } = render(SceneImage, { props: { image } });

    const downloadBtn = container.querySelector('.image-download-btn');
    expect(downloadBtn).not.toBeNull();
    // Turn 9 (0-based) displays as Turn 10 (1-based)
    expect(downloadBtn!.getAttribute('aria-label')).toBe('Download scene image for Turn 10');
  });

  it('download button uses download endpoint URL (not inline serve URL)', () => {
    const image = makeSceneImage({
      id: 'img-001',
      session_id: 'session-001',
    });
    const { container } = render(SceneImage, { props: { image } });

    const downloadBtn = container.querySelector('.image-download-btn') as HTMLAnchorElement;
    expect(downloadBtn).not.toBeNull();
    // Should use the download endpoint (with Content-Disposition), not the inline serve URL
    expect(downloadBtn.getAttribute('href')).toBe(
      '/api/sessions/session-001/images/img-001/download'
    );
    expect(downloadBtn.hasAttribute('download')).toBe(true);
  });

  it('has hover overlay for download button', () => {
    const image = makeSceneImage();
    const { container } = render(SceneImage, { props: { image } });

    const overlay = container.querySelector('.scene-image-overlay');
    expect(overlay).not.toBeNull();
  });
});
