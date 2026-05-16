import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import { get } from 'svelte/store';
import NpcPanel from './NpcPanel.svelte';
import type { GameState, NpcProfile } from '$lib/types';

// Mock $lib/stores — gameState is a writable that we mutate in tests.
vi.mock('$lib/stores', async () => {
  const { writable: w } = await import('svelte/store');
  return {
    gameState: w<GameState | null>(null),
    isThinking: w(false),
    connectionStatus: w('connected'),
    sendCommand: vi.fn(),
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

// Helper to access & mutate the mocked gameState across tests.
async function setMockGameState(value: GameState | null): Promise<void> {
  const stores = (await import('$lib/stores')) as unknown as {
    gameState: ReturnType<typeof writable<GameState | null>>;
  };
  stores.gameState.set(value);
}

// Suppress unused-import warning — used in setMockGameState casts above.
void get;

function makeNpc(overrides: Partial<NpcProfile> = {}): NpcProfile {
  return {
    name: 'Goblin 1',
    initiative_modifier: 2,
    hp_max: 15,
    hp_current: 10,
    ac: 13,
    personality: '',
    tactics: '',
    secret: '',
    conditions: [],
    ...overrides,
  };
}

function makeGameState(combatStateOverrides: Partial<GameState['combat_state']> = {}): GameState {
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
      ...combatStateOverrides,
    },
  };
}

describe('NpcPanel', () => {
  beforeEach(async () => {
    await setMockGameState(null);
  });

  it('renders nothing when gameState is null', async () => {
    await setMockGameState(null);
    const { container } = render(NpcPanel);
    expect(container.querySelector('.npc-panel')).toBeNull();
  });

  it('renders nothing when combat_state.active is false', async () => {
    await setMockGameState(
      makeGameState({
        active: false,
        npc_profiles: { goblin_1: makeNpc() },
      }),
    );
    const { container } = render(NpcPanel);
    expect(container.querySelector('.npc-panel')).toBeNull();
  });

  it('renders nothing when npc_profiles is empty', async () => {
    await setMockGameState(
      makeGameState({
        active: true,
        npc_profiles: {},
      }),
    );
    const { container } = render(NpcPanel);
    expect(container.querySelector('.npc-panel')).toBeNull();
  });

  it('renders one NpcCard per profile when combat is active', async () => {
    await setMockGameState(
      makeGameState({
        active: true,
        npc_profiles: {
          goblin_1: makeNpc({ name: 'Goblin 1' }),
          warg_alpha: makeNpc({ name: 'Warg Alpha', hp_current: 20, hp_max: 22 }),
          orc_chief: makeNpc({ name: 'Orc Chief', hp_current: 30, hp_max: 30 }),
        },
      }),
    );
    const { container } = render(NpcPanel);
    const cards = container.querySelectorAll('.npc-card');
    expect(cards.length).toBe(3);
  });

  it('section heading is "Active NPCs"', async () => {
    await setMockGameState(
      makeGameState({
        active: true,
        npc_profiles: { goblin_1: makeNpc() },
      }),
    );
    const { container } = render(NpcPanel);
    const heading = container.querySelector('.section-heading');
    expect(heading).not.toBeNull();
    expect(heading!.textContent).toContain('Active NPCs');
  });

  it('NpcCards are rendered inside a role=list container', async () => {
    await setMockGameState(
      makeGameState({
        active: true,
        npc_profiles: { goblin_1: makeNpc() },
      }),
    );
    const { container } = render(NpcPanel);
    const list = container.querySelector('[role="list"]');
    expect(list).not.toBeNull();
  });
});
