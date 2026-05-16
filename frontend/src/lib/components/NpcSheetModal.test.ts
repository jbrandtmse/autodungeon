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
});
