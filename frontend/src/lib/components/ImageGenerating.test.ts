import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import ImageGenerating from './ImageGenerating.svelte';

describe('ImageGenerating', () => {
  it('renders "Painting the scene..." text', () => {
    const { container } = render(ImageGenerating, {
      props: { turnNumber: 5, mode: 'specific' },
    });

    const text = container.querySelector('.image-generating-text');
    expect(text).not.toBeNull();
    // Turn 5 (0-based) displays as Turn 6 (1-based)
    expect(text!.textContent).toContain('Painting the scene for Turn 6');
  });

  it('shows best scene label when mode is best', () => {
    const { container } = render(ImageGenerating, {
      props: { turnNumber: 0, mode: 'best' },
    });

    const text = container.querySelector('.image-generating-text');
    expect(text).not.toBeNull();
    expect(text!.textContent).toContain('Painting the best scene');
  });

  it('has aria-live="polite" for accessibility', () => {
    const { container } = render(ImageGenerating, {
      props: { turnNumber: 0, mode: 'specific' },
    });

    const el = container.querySelector('.image-generating');
    expect(el).not.toBeNull();
    expect(el!.getAttribute('aria-live')).toBe('polite');
  });

  it('has image-generating CSS class', () => {
    const { container } = render(ImageGenerating, {
      props: { turnNumber: 3, mode: 'current' },
    });

    const el = container.querySelector('.image-generating');
    expect(el).not.toBeNull();
  });

  it('has spinner element', () => {
    const { container } = render(ImageGenerating, {
      props: { turnNumber: 0, mode: 'specific' },
    });

    const spinner = container.querySelector('.image-generating-spinner');
    expect(spinner).not.toBeNull();
  });
});
