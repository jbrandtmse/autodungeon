import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import { get, writable } from 'svelte/store';
import NpcCard from './NpcCard.svelte';
import type { NpcProfile } from '$lib/types';

// Mock the stores barrel export (mirror CharacterCard.test.ts pattern).
vi.mock('$lib/stores', () => {
  const gameState = writable(null);
  const isThinking = writable(false);
  const connectionStatus = writable('connected');
  const sendCommand = vi.fn();
  const uiState = writable({
    sidebarOpen: true,
    selectedCharacter: null,
    uiMode: 'watch',
    autoScroll: true,
    settingsOpen: false,
    characterSheetName: null,
    npcSheetName: null,
    comparisonForkId: null,
  });
  return {
    gameState,
    isThinking,
    connectionStatus,
    sendCommand,
    uiState,
  };
});

function makeNpc(overrides: Partial<NpcProfile> = {}): NpcProfile {
  return {
    name: 'Goblin 1',
    initiative_modifier: 2,
    hp_max: 15,
    hp_current: 10,
    ac: 13,
    personality: 'cowardly',
    tactics: 'flee at 25%',
    secret: 'knows of the back tunnel',
    conditions: [],
    ...overrides,
  };
}

describe('NpcCard', () => {
  it('renders NPC name and HP', () => {
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc() },
    });
    const nameEl = container.querySelector('.npc-name');
    expect(nameEl).not.toBeNull();
    expect(nameEl!.textContent).toContain('Goblin 1');

    const hpText = container.querySelector('.hp-text');
    expect(hpText).not.toBeNull();
    expect(hpText!.textContent).toContain('10/15 HP');
  });

  it('renders AC chip', () => {
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ ac: 17 }) },
    });
    const ac = container.querySelector('.ac-chip');
    expect(ac).not.toBeNull();
    expect(ac!.textContent).toContain('AC 17');
  });

  it('HP bar color is green at >50% HP', () => {
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ hp_current: 12, hp_max: 15 }) },
    });
    const fill = container.querySelector('.hp-bar-fill');
    expect(fill!.classList.contains('hp-green')).toBe(true);
  });

  it('HP bar color is amber at 26-50% HP', () => {
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ hp_current: 5, hp_max: 15 }) },
    });
    const fill = container.querySelector('.hp-bar-fill');
    expect(fill!.classList.contains('hp-amber')).toBe(true);
  });

  it('HP bar color is red at <=25% HP', () => {
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ hp_current: 2, hp_max: 15 }) },
    });
    const fill = container.querySelector('.hp-bar-fill');
    expect(fill!.classList.contains('hp-red')).toBe(true);
  });

  it('defeated NPC (hp_current=0) gets defeated class', () => {
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ hp_current: 0 }) },
    });
    const card = container.querySelector('.npc-card');
    expect(card!.classList.contains('defeated')).toBe(true);
  });

  it('renders conditions list when present', () => {
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ conditions: ['poisoned', 'prone'] }) },
    });
    const conds = container.querySelector('.conditions-list');
    expect(conds).not.toBeNull();
    expect(conds!.textContent).toContain('poisoned');
    expect(conds!.textContent).toContain('prone');
  });

  it('hides conditions block when empty', () => {
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ conditions: [] }) },
    });
    expect(container.querySelector('.conditions')).toBeNull();
  });

  it('click triggers uiState.update with npcSheetName', async () => {
    const stores = await import('$lib/stores');
    (stores.uiState as ReturnType<typeof writable>).set({
      sidebarOpen: true,
      selectedCharacter: null,
      uiMode: 'watch',
      autoScroll: true,
      settingsOpen: false,
      characterSheetName: null,
      npcSheetName: null,
      comparisonForkId: null,
    });
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc() },
    });
    const card = container.querySelector('.npc-card') as HTMLElement;
    await fireEvent.click(card);
    const state = get(stores.uiState as ReturnType<typeof writable>);
    expect((state as { npcSheetName: string | null }).npcSheetName).toBe('goblin_1');
  });

  it('Enter key opens the sheet', async () => {
    const stores = await import('$lib/stores');
    (stores.uiState as ReturnType<typeof writable>).set({
      sidebarOpen: true,
      selectedCharacter: null,
      uiMode: 'watch',
      autoScroll: true,
      settingsOpen: false,
      characterSheetName: null,
      npcSheetName: null,
      comparisonForkId: null,
    });
    const { container } = render(NpcCard, {
      props: { npcKey: 'warg_alpha', npc: makeNpc({ name: 'Warg Alpha' }) },
    });
    const card = container.querySelector('.npc-card') as HTMLElement;
    await fireEvent.keyDown(card, { key: 'Enter' });
    const state = get(stores.uiState as ReturnType<typeof writable>);
    expect((state as { npcSheetName: string | null }).npcSheetName).toBe('warg_alpha');
  });

  it('Space key opens the sheet', async () => {
    const stores = await import('$lib/stores');
    (stores.uiState as ReturnType<typeof writable>).set({
      sidebarOpen: true,
      selectedCharacter: null,
      uiMode: 'watch',
      autoScroll: true,
      settingsOpen: false,
      characterSheetName: null,
      npcSheetName: null,
      comparisonForkId: null,
    });
    const { container } = render(NpcCard, {
      props: { npcKey: 'lich_1', npc: makeNpc({ name: 'The Lich' }) },
    });
    const card = container.querySelector('.npc-card') as HTMLElement;
    await fireEvent.keyDown(card, { key: ' ' });
    const state = get(stores.uiState as ReturnType<typeof writable>);
    expect((state as { npcSheetName: string | null }).npcSheetName).toBe('lich_1');
  });

  it('keyboard accessible: role=button + tabindex=0 + aria-label', () => {
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc() },
    });
    const card = container.querySelector('.npc-card') as HTMLElement;
    expect(card.getAttribute('role')).toBe('button');
    expect(card.getAttribute('tabindex')).toBe('0');
    expect(card.getAttribute('aria-label')).toContain('Goblin 1');
  });

  // ===========================================================================
  // Gap-coverage additions (testarch-automate, 2026-05-16)
  // ===========================================================================

  it('renders 0% HP bar width when hp_current=0 (defeated, full bar empty)', () => {
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ hp_current: 0, hp_max: 15 }) },
    });
    const fill = container.querySelector('.hp-bar-fill') as HTMLElement;
    expect(fill.style.width).toBe('0%');
    expect(fill.classList.contains('hp-red')).toBe(true);
  });

  it('renders 100% HP bar width when hp_current=hp_max (full health)', () => {
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ hp_current: 15, hp_max: 15 }) },
    });
    const fill = container.querySelector('.hp-bar-fill') as HTMLElement;
    expect(fill.style.width).toBe('100%');
    expect(fill.classList.contains('hp-green')).toBe(true);
  });

  it('clamps over-max HP to 100% bar width (LLM-over-heal defense)', () => {
    // If a future bug or DM action ever sets hp_current > hp_max (e.g., a
    // bad dm_update_npc tool call), the bar must visually clamp instead of
    // overflowing past the container. Verifies the Math.min(100, ...) guard.
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ hp_current: 99, hp_max: 15 }) },
    });
    const fill = container.querySelector('.hp-bar-fill') as HTMLElement;
    expect(fill.style.width).toBe('100%');
  });

  it('does NOT crash when hp_max is 0 (division-by-zero guard)', () => {
    // hp_max=0 violates the Pydantic ge=1 invariant, but defense in depth:
    // a malformed payload from a future schema migration must not throw.
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ hp_current: 0, hp_max: 0 }) },
    });
    const fill = container.querySelector('.hp-bar-fill') as HTMLElement;
    expect(fill.style.width).toBe('0%');
  });

  it('aria-valuenow/min/max reflect HP for screen readers', () => {
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ hp_current: 7, hp_max: 12 }) },
    });
    const meter = container.querySelector('[role="meter"]') as HTMLElement;
    expect(meter).not.toBeNull();
    expect(meter.getAttribute('aria-valuenow')).toBe('7');
    expect(meter.getAttribute('aria-valuemin')).toBe('0');
    expect(meter.getAttribute('aria-valuemax')).toBe('12');
  });

  it('renders a single-condition list correctly (no trailing comma)', () => {
    // Defense check for the conditions.join(', ') call — single entry
    // must NOT produce a trailing separator.
    const { container } = render(NpcCard, {
      props: { npcKey: 'goblin_1', npc: makeNpc({ conditions: ['prone'] }) },
    });
    const conds = container.querySelector('.conditions-list') as HTMLElement;
    expect(conds.textContent?.trim()).toBe('prone');
  });
});
