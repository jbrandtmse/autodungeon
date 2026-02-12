import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { uiState } from './uiStore';
import type { UiState } from './uiStore';

const DEFAULT_UI_STATE: UiState = {
  sidebarOpen: true,
  selectedCharacter: null,
  uiMode: 'watch',
  autoScroll: true,
  settingsOpen: false,
  characterSheetName: null,
  comparisonForkId: null,
};

describe('uiStore', () => {
  beforeEach(() => {
    uiState.set({ ...DEFAULT_UI_STATE });
  });

  it('has correct default values', () => {
    const state = get(uiState);
    expect(state.sidebarOpen).toBe(true);
    expect(state.uiMode).toBe('watch');
    expect(state.autoScroll).toBe(true);
    expect(state.settingsOpen).toBe(false);
    expect(state.characterSheetName).toBeNull();
    expect(state.comparisonForkId).toBeNull();
    expect(state.selectedCharacter).toBeNull();
  });

  it('update correctly merges partial state', () => {
    uiState.update((s) => ({ ...s, settingsOpen: true, uiMode: 'play' as const }));

    const state = get(uiState);
    expect(state.settingsOpen).toBe(true);
    expect(state.uiMode).toBe('play');
    // Other fields unchanged
    expect(state.sidebarOpen).toBe(true);
    expect(state.autoScroll).toBe(true);
  });

  it('each field can be set and read independently', () => {
    uiState.update((s) => ({ ...s, sidebarOpen: false }));
    expect(get(uiState).sidebarOpen).toBe(false);

    uiState.update((s) => ({ ...s, characterSheetName: 'Thorin' }));
    expect(get(uiState).characterSheetName).toBe('Thorin');
    // sidebarOpen still false
    expect(get(uiState).sidebarOpen).toBe(false);

    uiState.update((s) => ({ ...s, comparisonForkId: 'fork-123' }));
    expect(get(uiState).comparisonForkId).toBe('fork-123');

    uiState.update((s) => ({ ...s, autoScroll: false }));
    expect(get(uiState).autoScroll).toBe(false);
  });
});
