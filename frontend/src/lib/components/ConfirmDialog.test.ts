import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import ConfirmDialog from './ConfirmDialog.svelte';

describe('ConfirmDialog', () => {
  it('is not rendered when open is false', () => {
    const { container } = render(ConfirmDialog, {
      props: {
        open: false,
        title: 'Delete?',
        message: 'Are you sure?',
        onConfirm: vi.fn(),
        onCancel: vi.fn(),
      },
    });
    const dialog = container.querySelector('[role="dialog"]');
    expect(dialog).toBeNull();
  });

  it('renders title, message, and buttons when open is true', () => {
    const { container } = render(ConfirmDialog, {
      props: {
        open: true,
        title: 'Delete Session',
        message: 'This cannot be undone.',
        onConfirm: vi.fn(),
        onCancel: vi.fn(),
      },
    });
    const dialog = container.querySelector('[role="dialog"]');
    expect(dialog).not.toBeNull();
    expect(dialog!.textContent).toContain('Delete Session');
    expect(dialog!.textContent).toContain('This cannot be undone.');
  });

  it('confirm button uses confirmLabel text', () => {
    render(ConfirmDialog, {
      props: {
        open: true,
        title: 'Delete?',
        message: 'Sure?',
        confirmLabel: 'Yes, Delete',
        onConfirm: vi.fn(),
        onCancel: vi.fn(),
      },
    });
    const confirmBtn = screen.getByText('Yes, Delete');
    expect(confirmBtn).toBeDefined();
  });

  it('cancel button calls onCancel', async () => {
    const onCancel = vi.fn();
    render(ConfirmDialog, {
      props: {
        open: true,
        title: 'Delete?',
        message: 'Sure?',
        onConfirm: vi.fn(),
        onCancel,
      },
    });
    const cancelBtn = screen.getByText('Cancel');
    await fireEvent.click(cancelBtn);
    expect(onCancel).toHaveBeenCalled();
  });

  it('confirm button calls onConfirm', async () => {
    const onConfirm = vi.fn();
    render(ConfirmDialog, {
      props: {
        open: true,
        title: 'Delete?',
        message: 'Sure?',
        confirmLabel: 'OK',
        onConfirm,
        onCancel: vi.fn(),
      },
    });
    const confirmBtn = screen.getByText('OK');
    await fireEvent.click(confirmBtn);
    expect(onConfirm).toHaveBeenCalled();
  });

  it('error message is displayed when error prop is set', () => {
    const { container } = render(ConfirmDialog, {
      props: {
        open: true,
        title: 'Delete?',
        message: 'Sure?',
        error: 'Something went wrong',
        onConfirm: vi.fn(),
        onCancel: vi.fn(),
      },
    });
    const errorEl = container.querySelector('.dialog-error');
    expect(errorEl).not.toBeNull();
    expect(errorEl!.textContent).toContain('Something went wrong');
  });
});
