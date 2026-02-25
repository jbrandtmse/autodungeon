import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import SessionCard from './SessionCard.svelte';
import { makeSession } from '../../tests/fixtures';

// Mock $app/navigation so goto doesn't error
vi.mock('$app/navigation', () => ({
  goto: vi.fn(),
}));

describe('SessionCard', () => {
  it('renders session title using Roman numeral conversion', () => {
    const { container } = render(SessionCard, {
      props: {
        session: makeSession({ session_number: 7 }),
        onDelete: vi.fn(),
      },
    });
    const title = container.querySelector('.session-title');
    expect(title).not.toBeNull();
    expect(title!.textContent).toContain('Session VII');
  });

  it('renders the session name', () => {
    const { container } = render(SessionCard, {
      props: {
        session: makeSession({ name: 'Dragon Hunt' }),
        onDelete: vi.fn(),
      },
    });
    const name = container.querySelector('.session-name');
    expect(name).not.toBeNull();
    expect(name!.textContent).toContain('Dragon Hunt');
  });

  it('renders "Unnamed Adventure" fallback when name is empty', () => {
    const { container } = render(SessionCard, {
      props: {
        session: makeSession({ name: '' }),
        onDelete: vi.fn(),
      },
    });
    const name = container.querySelector('.session-name');
    expect(name).not.toBeNull();
    expect(name!.textContent).toContain('Unnamed Adventure');
  });

  it('delete button calls onDelete with session ID', async () => {
    const onDelete = vi.fn();
    const { container } = render(SessionCard, {
      props: {
        session: makeSession({ session_id: 'abc-123' }),
        onDelete,
      },
    });
    const deleteBtn = container.querySelector('.delete-btn');
    expect(deleteBtn).not.toBeNull();
    await fireEvent.click(deleteBtn!);
    expect(onDelete).toHaveBeenCalledWith('abc-123');
  });

  it('applies .deleting class when deleting prop is true', () => {
    const { container } = render(SessionCard, {
      props: {
        session: makeSession(),
        deleting: true,
        onDelete: vi.fn(),
      },
    });
    const card = container.querySelector('.session-card');
    expect(card).not.toBeNull();
    expect(card!.classList.contains('deleting')).toBe(true);
  });

  describe('gallery icon', () => {
    it('renders gallery button when imageCount > 0 and onOpenGallery provided', () => {
      const { container } = render(SessionCard, {
        props: {
          session: makeSession({ session_id: 'sess-1' }),
          onDelete: vi.fn(),
          imageCount: 12,
          onOpenGallery: vi.fn(),
        },
      });
      const galleryBtn = container.querySelector('.gallery-btn');
      expect(galleryBtn).not.toBeNull();
    });

    it('does not render gallery button when imageCount is 0', () => {
      const { container } = render(SessionCard, {
        props: {
          session: makeSession(),
          onDelete: vi.fn(),
          imageCount: 0,
          onOpenGallery: vi.fn(),
        },
      });
      const galleryBtn = container.querySelector('.gallery-btn');
      expect(galleryBtn).toBeNull();
    });

    it('does not render gallery button when imageCount not provided', () => {
      const { container } = render(SessionCard, {
        props: {
          session: makeSession(),
          onDelete: vi.fn(),
        },
      });
      const galleryBtn = container.querySelector('.gallery-btn');
      expect(galleryBtn).toBeNull();
    });

    it('does not render gallery button when onOpenGallery not provided', () => {
      const { container } = render(SessionCard, {
        props: {
          session: makeSession(),
          onDelete: vi.fn(),
          imageCount: 5,
        },
      });
      const galleryBtn = container.querySelector('.gallery-btn');
      expect(galleryBtn).toBeNull();
    });

    it('shows correct image count in badge', () => {
      const { container } = render(SessionCard, {
        props: {
          session: makeSession(),
          onDelete: vi.fn(),
          imageCount: 42,
          onOpenGallery: vi.fn(),
        },
      });
      const badge = container.querySelector('.gallery-badge');
      expect(badge).not.toBeNull();
      expect(badge!.textContent).toBe('42');
    });

    it('calls onOpenGallery with session_id when clicked', async () => {
      const onOpenGallery = vi.fn();
      const { container } = render(SessionCard, {
        props: {
          session: makeSession({ session_id: 'abc-123' }),
          onDelete: vi.fn(),
          imageCount: 5,
          onOpenGallery,
        },
      });
      const galleryBtn = container.querySelector('.gallery-btn');
      expect(galleryBtn).not.toBeNull();
      await fireEvent.click(galleryBtn!);
      expect(onOpenGallery).toHaveBeenCalledWith('abc-123');
    });

    it('has correct aria-label with image count', () => {
      const { container } = render(SessionCard, {
        props: {
          session: makeSession({ name: 'Dragon Quest' }),
          onDelete: vi.fn(),
          imageCount: 7,
          onOpenGallery: vi.fn(),
        },
      });
      const galleryBtn = container.querySelector('.gallery-btn');
      expect(galleryBtn).not.toBeNull();
      expect(galleryBtn!.getAttribute('aria-label')).toContain('7');
      expect(galleryBtn!.getAttribute('aria-label')).toContain('Dragon Quest');
    });
  });
});
