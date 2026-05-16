import { writable } from 'svelte/store';

export interface UiState {
  sidebarOpen: boolean;
  selectedCharacter: string | null;
  uiMode: 'watch' | 'play';
  autoScroll: boolean;
  settingsOpen: boolean;
  /** When set, the CharacterSheetModal opens for this character name. */
  characterSheetName: string | null;
  /** When set, the NpcSheetModal opens for this NPC key (Story 15.9). */
  npcSheetName: string | null;
  /** When set, the ForkComparison overlay is shown for this fork ID. */
  comparisonForkId: string | null;
}

export const uiState = writable<UiState>({
  sidebarOpen: true,
  selectedCharacter: null,
  uiMode: 'watch',
  autoScroll: true,
  settingsOpen: false,
  characterSheetName: null,
  npcSheetName: null,
  comparisonForkId: null,
});
