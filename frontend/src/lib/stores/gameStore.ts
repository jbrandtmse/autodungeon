import { writable } from 'svelte/store';
import type { GameState, WsServerEvent } from '$lib/types';
import { uiState } from './uiStore';

export const gameState = writable<GameState | null>(null);
export const isAutopilotRunning = writable<boolean>(false);
export const isPaused = writable<boolean>(false);
export const speed = writable<string>('normal');
export const isThinking = writable<boolean>(false);
export const thinkingAgent = writable<string>('dm');
export const awaitingInput = writable<boolean>(false);
export const awaitingInputCharacter = writable<string>('');

/**
 * Central dispatch for all WebSocket server events.
 *
 * Updates the appropriate stores based on event type. The NarrativePanel
 * reads from gameState (specifically ground_truth_log) and reacts via
 * derived state.
 */
export function handleServerMessage(msg: WsServerEvent): void {
	switch (msg.type) {
		case 'session_state':
			// The session_state event carries the full game state
			gameState.set(msg.state as unknown as GameState);
			break;

		case 'turn_update':
			isThinking.set(false);
			awaitingInput.set(false);
			awaitingInputCharacter.set('');
			// Append new turn to the ground_truth_log in existing state
			gameState.update((state) => {
				if (!state) return state;
				const prefix =
					msg.agent.toUpperCase() === 'SHEET' ? 'SHEET' : msg.agent;
				return {
					...state,
					ground_truth_log: [...state.ground_truth_log, `[${prefix}]: ${msg.content}`],
					current_turn: msg.agent,
					turn_number: msg.turn,
				};
			});
			break;

		case 'autopilot_started':
			isAutopilotRunning.set(true);
			isThinking.set(true);
			thinkingAgent.set('dm');
			break;

		case 'autopilot_stopped':
			isAutopilotRunning.set(false);
			isThinking.set(false);
			break;

		case 'paused':
			isPaused.set(true);
			isThinking.set(false);
			break;

		case 'resumed':
			isPaused.set(false);
			break;

		case 'speed_changed':
			speed.set(msg.speed);
			break;

		case 'drop_in':
			gameState.update((state) => {
				if (!state) return state;
				return {
					...state,
					human_active: true,
					controlled_character: msg.character,
				};
			});
			uiState.update((s) => ({ ...s, uiMode: 'play' as const }));
			break;

		case 'release_control':
			gameState.update((state) => {
				if (!state) return state;
				return {
					...state,
					human_active: false,
					controlled_character: null,
				};
			});
			uiState.update((s) => ({ ...s, uiMode: 'watch' as const }));
			awaitingInput.set(false);
			awaitingInputCharacter.set('');
			break;

		case 'awaiting_input':
			awaitingInput.set(true);
			awaitingInputCharacter.set(msg.character);
			break;

		case 'error':
			isThinking.set(false);
			break;

		default:
			// Other events (ping/pong handled by ws.ts, command_ack, etc.)
			break;
	}
}

/**
 * Reset all stores to initial state. Called when navigating away
 * from a game session or connecting to a new one.
 */
export function resetStores(): void {
	gameState.set(null);
	isAutopilotRunning.set(false);
	isPaused.set(false);
	speed.set('normal');
	isThinking.set(false);
	thinkingAgent.set('dm');
	awaitingInput.set(false);
	awaitingInputCharacter.set('');
}
