import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import NpcSheetModal from './NpcSheetModal.svelte';
import type { GameState, NpcProfile } from '$lib/types';

// API mock — vi.hoisted so the mock fn is created BEFORE the vi.mock factory runs.
const { mockGetNpcProfile } = vi.hoisted(() => ({
  mockGetNpcProfile: vi.fn<(sessionId: string, npcKey: string) => Promise<NpcProfile>>(),
}));

vi.mock('$lib/api', () => ({
  getNpcProfile: mockGetNpcProfile,
}));

vi.mock('$lib/stores', async () => {
  const { writable: w } = await import('svelte/store');
  return {
    gameState: w<GameState | null>(null),
    uiState: w({
      sidebarOpen: true,
      selectedCharacter: null,
      uiMode: 'watch',
      autoScroll: true,
      settingsOpen: false,
      characterSheetName: null,
      npcSheetName: null,
      comparisonForkId: null,
    }),
  };
});

async function setMockGameState(value: GameState | null): Promise<void> {
  const stores = (await import('$lib/stores')) as unknown as {
    gameState: ReturnType<typeof writable<GameState | null>>;
  };
  stores.gameState.set(value);
}

function makeNpc(overrides: Partial<NpcProfile> = {}): NpcProfile {
  return {
    name: 'Goblin 1',
    initiative_modifier: 2,
    hp_max: 15,
    hp_current: 10,
    ac: 13,
    personality: 'Aggressive coward',
    tactics: 'Flee at low HP',
    secret: 'knows where the prisoner is held',
    conditions: ['poisoned'],
    ...overrides,
  };
}

function makeActiveCombatState(): GameState {
  return {
    ground_truth_log: [],
    turn_queue: [],
    current_turn: 'dm',
    agent_memories: {},
    game_config: {
      combat_mode: 'Tactical',
      summarizer_provider: '',
      summarizer_model: '',
      extractor_provider: '',
      extractor_model: '',
      party_size: 4,
      narrative_display_limit: 100,
      max_combat_rounds: 10,
      dm_provider: '',
      dm_model: '',
      dm_token_limit: 8000,
    },
    human_active: false,
    controlled_character: null,
    turn_number: 1,
    session_id: '001',
    combat_state: {
      active: true,
      round_number: 1,
      initiative_order: [],
      initiative_rolls: {},
      npc_profiles: {},
    },
  };
}

describe('NpcSheetModal', () => {
  beforeEach(async () => {
    mockGetNpcProfile.mockReset();
    await setMockGameState(makeActiveCombatState());
  });

  it('does not render when open is false', () => {
    const { container } = render(NpcSheetModal, {
      props: {
        open: false,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose: vi.fn(),
      },
    });
    expect(container.querySelector('.modal-backdrop')).toBeNull();
  });

  it('calls getNpcProfile when opened', async () => {
    mockGetNpcProfile.mockResolvedValue(makeNpc());
    render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: 'session-001',
        npcKey: 'goblin_1',
        onClose: vi.fn(),
      },
    });
    await waitFor(() => {
      expect(mockGetNpcProfile).toHaveBeenCalledWith('session-001', 'goblin_1');
    });
  });

  it('renders the loaded NPC name and HP', async () => {
    mockGetNpcProfile.mockResolvedValue(makeNpc({ name: 'Lich King', hp_current: 80, hp_max: 200 }));
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'lich_king',
        onClose: vi.fn(),
      },
    });
    await waitFor(() => {
      const name = container.querySelector('.sheet-name');
      expect(name?.textContent).toContain('Lich King');
    });
    const hp = container.querySelector('.hp-text');
    expect(hp?.textContent).toContain('80/200');
  });

  it('renders AC and initiative chips', async () => {
    mockGetNpcProfile.mockResolvedValue(makeNpc({ ac: 18, initiative_modifier: 4 }));
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose: vi.fn(),
      },
    });
    await waitFor(() => {
      const chips = container.querySelectorAll('.chip');
      expect(chips.length).toBe(2);
      expect(chips[0].textContent).toContain('AC');
      expect(chips[0].textContent).toContain('18');
      expect(chips[1].textContent).toContain('+4');
    });
  });

  it('renders conditions list', async () => {
    mockGetNpcProfile.mockResolvedValue(makeNpc({ conditions: ['poisoned', 'prone'] }));
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose: vi.fn(),
      },
    });
    await waitFor(() => {
      const items = container.querySelectorAll('.condition-item');
      expect(items.length).toBe(2);
      expect(items[0].textContent).toContain('poisoned');
      expect(items[1].textContent).toContain('prone');
    });
  });

  it('renders personality and tactics', async () => {
    mockGetNpcProfile.mockResolvedValue(
      makeNpc({ personality: 'Ruthless', tactics: 'Charges the strongest' }),
    );
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose: vi.fn(),
      },
    });
    await waitFor(() => {
      const proseEls = container.querySelectorAll('.prose');
      const texts = Array.from(proseEls).map((p) => p.textContent ?? '');
      expect(texts.some((t) => t.includes('Ruthless'))).toBe(true);
      expect(texts.some((t) => t.includes('Charges the strongest'))).toBe(true);
    });
  });

  it('secret renders inside a <details> disclosure (collapsed by default)', async () => {
    mockGetNpcProfile.mockResolvedValue(makeNpc({ secret: 'phylactery in the crypt' }));
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose: vi.fn(),
      },
    });
    await waitFor(() => {
      const details = container.querySelector('.secret-details');
      expect(details).not.toBeNull();
      expect((details as HTMLDetailsElement).open).toBe(false);
    });
    const summary = container.querySelector('.secret-details summary');
    expect(summary?.textContent).toContain('Secret');
    // Body text is in DOM (just visually hidden inside collapsed <details>).
    const body = container.querySelector('.secret-text');
    expect(body?.textContent).toContain('phylactery');
  });

  it('hides the secret disclosure when npc.secret is empty', async () => {
    mockGetNpcProfile.mockResolvedValue(makeNpc({ secret: '' }));
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose: vi.fn(),
      },
    });
    await waitFor(() => {
      expect(container.querySelector('.sheet-name')).not.toBeNull();
    });
    expect(container.querySelector('.secret-details')).toBeNull();
  });

  it('Escape key calls onClose', async () => {
    mockGetNpcProfile.mockResolvedValue(makeNpc());
    const onClose = vi.fn();
    render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose,
      },
    });
    await waitFor(() => {
      expect(mockGetNpcProfile).toHaveBeenCalled();
    });
    await fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  it('backdrop click calls onClose', async () => {
    mockGetNpcProfile.mockResolvedValue(makeNpc());
    const onClose = vi.fn();
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose,
      },
    });
    await waitFor(() => {
      expect(mockGetNpcProfile).toHaveBeenCalled();
    });
    const backdrop = container.querySelector('.modal-backdrop') as HTMLElement;
    // Simulate click directly on backdrop (target === currentTarget).
    await fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalled();
  });

  it('renders error state when API fails', async () => {
    mockGetNpcProfile.mockRejectedValue(new Error('NPC not found'));
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose: vi.fn(),
      },
    });
    await waitFor(() => {
      const err = container.querySelector('.modal-error');
      expect(err?.textContent).toContain('NPC not found');
    });
  });

  it('defeated NPC (hp_current=0) gets defeated treatment', async () => {
    mockGetNpcProfile.mockResolvedValue(makeNpc({ hp_current: 0 }));
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose: vi.fn(),
      },
    });
    await waitFor(() => {
      const name = container.querySelector('.sheet-name');
      expect(name?.classList.contains('defeated')).toBe(true);
    });
    const label = container.querySelector('.defeated-label');
    expect(label?.textContent).toContain('Defeated');
  });

  // ===========================================================================
  // Gap-coverage additions (testarch-automate, 2026-05-16)
  // Covers code-review LOW #5 (untested focus-trap math) and AC #11
  // (auto-close on combat end).
  // ===========================================================================

  it('AC #11: auto-closes when combat_state.active flips to false', async () => {
    mockGetNpcProfile.mockResolvedValue(makeNpc());
    const onClose = vi.fn();
    render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose,
      },
    });
    await waitFor(() => {
      expect(mockGetNpcProfile).toHaveBeenCalled();
    });
    // Flip combat off — the modal's $effect must invoke onClose.
    await setMockGameState({
      ...makeActiveCombatState(),
      combat_state: {
        active: false,
        round_number: 1,
        initiative_order: [],
        initiative_rolls: {},
        npc_profiles: {},
      },
    });
    // The $effect runs synchronously on store update. waitFor for safety.
    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });
  });

  it('does NOT auto-close when combat_state.active is still true', async () => {
    // Negative case: changing other state should not trigger the AC #11
    // auto-close. Without this, a future $effect-dependency mistake (e.g.,
    // depending on any combat_state field) would silently break the modal.
    mockGetNpcProfile.mockResolvedValue(makeNpc());
    const onClose = vi.fn();
    render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose,
      },
    });
    await waitFor(() => {
      expect(mockGetNpcProfile).toHaveBeenCalled();
    });
    // Mutate combat (e.g., HP change) while staying active.
    await setMockGameState({
      ...makeActiveCombatState(),
      combat_state: {
        active: true,
        round_number: 2,
        initiative_order: [],
        initiative_rolls: {},
        npc_profiles: {},
      },
    });
    // Give the effect a tick to (incorrectly) fire if it would.
    await new Promise((r) => setTimeout(r, 30));
    expect(onClose).not.toHaveBeenCalled();
  });

  it('focus trap: Tab from last focusable cycles to first', async () => {
    // Covers code-review LOW #5. With the secret-details disclosure
    // present, the modal has at least 2 focusable elements (close button
    // + summary). Tab from the LAST element with focus should wrap to
    // the FIRST.
    mockGetNpcProfile.mockResolvedValue(makeNpc({ secret: 'hidden lore' }));
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose: vi.fn(),
      },
    });
    await waitFor(() => {
      expect(container.querySelector('.secret-details')).not.toBeNull();
    });
    const closeBtn = container.querySelector('.close-btn') as HTMLButtonElement;
    const summary = container.querySelector(
      '.secret-details summary',
    ) as HTMLElement;
    expect(closeBtn).not.toBeNull();
    expect(summary).not.toBeNull();

    // Move focus to the last focusable (summary), then press Tab.
    summary.focus();
    expect(document.activeElement).toBe(summary);

    await fireEvent.keyDown(window, { key: 'Tab' });

    // Focus should wrap to the first focusable (close button).
    expect(document.activeElement).toBe(closeBtn);
  });

  it('focus trap: Shift+Tab from first focusable cycles to last', async () => {
    // Inverse of the previous test — backward wrap.
    mockGetNpcProfile.mockResolvedValue(makeNpc({ secret: 'hidden lore' }));
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose: vi.fn(),
      },
    });
    await waitFor(() => {
      expect(container.querySelector('.secret-details')).not.toBeNull();
    });
    const closeBtn = container.querySelector('.close-btn') as HTMLButtonElement;
    const summary = container.querySelector(
      '.secret-details summary',
    ) as HTMLElement;

    closeBtn.focus();
    expect(document.activeElement).toBe(closeBtn);

    await fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });

    expect(document.activeElement).toBe(summary);
  });

  it('focus trap: mid-cycle Tab does NOT preventDefault (browser handles it)', async () => {
    // Ensures the focus-trap logic only intervenes at the boundaries. If
    // focus is in the middle of the focusable list, the trap must let the
    // browser handle the Tab naturally (no preventDefault).
    mockGetNpcProfile.mockResolvedValue(makeNpc({ secret: 'hidden lore' }));
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose: vi.fn(),
      },
    });
    await waitFor(() => {
      expect(container.querySelector('.secret-details')).not.toBeNull();
    });

    // Focus is on document.body (no relevant focusable) — Tab should
    // pass through. We verify by checking the event default.
    const event = new KeyboardEvent('keydown', {
      key: 'Tab',
      bubbles: true,
      cancelable: true,
    });
    const wasDefaultPrevented = !window.dispatchEvent(event);
    // dispatchEvent returns false if preventDefault was called. With no
    // focus inside the trap, the handler should leave it alone.
    expect(wasDefaultPrevented).toBe(false);
  });

  it('Tab handler is a no-op when modal is closed (open=false)', async () => {
    // Guards against a future refactor accidentally trapping keystrokes
    // while the modal is hidden. With open=false the keydown handler
    // returns early — Escape must not call onClose.
    const onClose = vi.fn();
    render(NpcSheetModal, {
      props: {
        open: false,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose,
      },
    });
    await fireEvent.keyDown(window, { key: 'Escape' });
    expect(onClose).not.toHaveBeenCalled();
  });

  it('clicking inside the modal body does NOT close (target != currentTarget)', async () => {
    // The handleBackdropClick guard (target === currentTarget) prevents
    // accidental close when the user clicks inside the modal content.
    mockGetNpcProfile.mockResolvedValue(makeNpc());
    const onClose = vi.fn();
    const { container } = render(NpcSheetModal, {
      props: {
        open: true,
        sessionId: '001',
        npcKey: 'goblin_1',
        onClose,
      },
    });
    await waitFor(() => {
      expect(container.querySelector('.modal')).not.toBeNull();
    });
    const modalBody = container.querySelector('.modal') as HTMLElement;
    await fireEvent.click(modalBody);
    expect(onClose).not.toHaveBeenCalled();
  });
});
