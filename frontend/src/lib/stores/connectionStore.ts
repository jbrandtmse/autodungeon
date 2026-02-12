import { writable, get } from 'svelte/store';
import type { WsCommand } from '$lib/types';

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export const connectionStatus = writable<ConnectionStatus>('disconnected');
export const lastError = writable<string | null>(null);

/**
 * Writable store holding the WebSocket send function.
 * Set by the game page when connected, cleared on disconnect.
 */
export const wsSend = writable<((cmd: WsCommand) => void) | null>(null);

/**
 * Send a WebSocket command via the stored send function.
 * Logs a warning if not connected.
 */
export function sendCommand(cmd: WsCommand): void {
	const send = get(wsSend);
	if (send) {
		send(cmd);
	} else {
		console.warn('[WS] Cannot send command — not connected');
	}
}
