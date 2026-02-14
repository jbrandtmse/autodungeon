import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import IllustrateMenu from './IllustrateMenu.svelte';
import { connectionStatus } from '$lib/stores/connectionStore';

// Mock the API module
vi.mock('$lib/api', () => ({
  generateCurrentImage: vi.fn().mockResolvedValue({ task_id: 't1', session_id: 's1', turn_number: 0, status: 'pending' }),
  generateBestImage: vi.fn().mockResolvedValue({ task_id: 't2', session_id: 's1', status: 'scanning' }),
  generateTurnImage: vi.fn().mockResolvedValue({ task_id: 't3', session_id: 's1', turn_number: 5, status: 'pending' }),
}));

describe('IllustrateMenu', () => {
  beforeEach(() => {
    connectionStatus.set('connected');
  });

  it('renders the Illustrate button', () => {
    const { container } = render(IllustrateMenu, {
      props: {
        sessionId: 'session-001',
        totalTurns: 10,
        onOpenGallery: () => {},
      },
    });

    const btn = container.querySelector('.illustrate-btn');
    expect(btn).not.toBeNull();
    expect(btn!.textContent).toContain('Illustrate');
  });

  it('dropdown opens on button click', async () => {
    const { container } = render(IllustrateMenu, {
      props: {
        sessionId: 'session-001',
        totalTurns: 10,
        onOpenGallery: () => {},
      },
    });

    const btn = container.querySelector('.illustrate-btn') as HTMLButtonElement;
    await fireEvent.click(btn);

    const dropdown = container.querySelector('.illustrate-dropdown');
    expect(dropdown).not.toBeNull();
  });

  it('shows menu items when dropdown is open', async () => {
    const { container } = render(IllustrateMenu, {
      props: {
        sessionId: 'session-001',
        totalTurns: 10,
        onOpenGallery: () => {},
      },
    });

    const btn = container.querySelector('.illustrate-btn') as HTMLButtonElement;
    await fireEvent.click(btn);

    const items = container.querySelectorAll('.dropdown-item');
    expect(items.length).toBe(4); // Current Scene, Best Scene, Turn #..., View Gallery
    expect(items[0].textContent).toContain('Current Scene');
    expect(items[1].textContent).toContain('Best Scene');
    expect(items[2].textContent).toContain('Turn #');
    expect(items[3].textContent).toContain('View Gallery');
  });

  it('button is disabled when not connected', async () => {
    connectionStatus.set('disconnected');
    const { container } = render(IllustrateMenu, {
      props: {
        sessionId: 'session-001',
        totalTurns: 10,
        onOpenGallery: () => {},
      },
    });

    const btn = container.querySelector('.illustrate-btn') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  it('has aria-haspopup and aria-expanded attributes', async () => {
    const { container } = render(IllustrateMenu, {
      props: {
        sessionId: 'session-001',
        totalTurns: 10,
        onOpenGallery: () => {},
      },
    });

    const btn = container.querySelector('.illustrate-btn') as HTMLButtonElement;
    expect(btn.getAttribute('aria-haspopup')).toBe('true');
    expect(btn.getAttribute('aria-expanded')).toBe('false');

    await fireEvent.click(btn);
    expect(btn.getAttribute('aria-expanded')).toBe('true');
  });

  it('Turn # opens turn dialog', async () => {
    const { container } = render(IllustrateMenu, {
      props: {
        sessionId: 'session-001',
        totalTurns: 10,
        onOpenGallery: () => {},
      },
    });

    const btn = container.querySelector('.illustrate-btn') as HTMLButtonElement;
    await fireEvent.click(btn);

    const items = container.querySelectorAll('.dropdown-item');
    await fireEvent.click(items[2]); // "Turn #..."

    const turnDialog = container.querySelector('.turn-dialog');
    expect(turnDialog).not.toBeNull();

    const turnInput = container.querySelector('.turn-input') as HTMLInputElement;
    expect(turnInput).not.toBeNull();
  });

  it('View Gallery calls onOpenGallery callback', async () => {
    const onOpenGallery = vi.fn();
    const { container } = render(IllustrateMenu, {
      props: {
        sessionId: 'session-001',
        totalTurns: 10,
        onOpenGallery,
      },
    });

    const btn = container.querySelector('.illustrate-btn') as HTMLButtonElement;
    await fireEvent.click(btn);

    const items = container.querySelectorAll('.dropdown-item');
    await fireEvent.click(items[3]); // "View Gallery"

    expect(onOpenGallery).toHaveBeenCalledOnce();
  });
});
