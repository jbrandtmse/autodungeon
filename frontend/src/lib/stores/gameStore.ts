import { writable } from 'svelte/store';
import type { GameState } from '$lib/types';

export const gameState = writable<GameState | null>(null);
export const isAutopilotRunning = writable<boolean>(false);
export const isPaused = writable<boolean>(false);
export const speed = writable<string>('normal');
