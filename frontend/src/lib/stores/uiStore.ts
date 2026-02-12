import { writable } from 'svelte/store';

export interface UiState {
  sidebarOpen: boolean;
  selectedCharacter: string | null;
  uiMode: 'watch' | 'play';
  autoScroll: boolean;
  settingsOpen: boolean;
}

export const uiState = writable<UiState>({
  sidebarOpen: true,
  selectedCharacter: null,
  uiMode: 'watch',
  autoScroll: true,
  settingsOpen: false,
});
