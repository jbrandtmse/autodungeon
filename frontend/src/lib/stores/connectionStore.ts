import { writable } from 'svelte/store';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export const connectionStatus = writable<ConnectionStatus>('disconnected');
export const lastError = writable<string | null>(null);
