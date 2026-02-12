import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import {
  gameState,
  isAutopilotRunning,
  isPaused,
  speed,
  isThinking,
  thinkingAgent,
  awaitingInput,
  awaitingInputCharacter,
  handleServerMessage,
  resetStores,
} from './gameStore';
import { uiState } from './uiStore';
import { makeGameState } from '../../tests/fixtures';
import type { WsServerEvent } from '$lib/types';

describe('gameStore', () => {
  beforeEach(() => {
    resetStores();
    // Also reset uiState since some events modify it
    uiState.set({
      sidebarOpen: true,
      selectedCharacter: null,
      uiMode: 'watch',
      autoScroll: true,
      settingsOpen: false,
      characterSheetName: null,
      comparisonForkId: null,
    });
  });

  describe('handleServerMessage — session_state', () => {
    it('sets gameState from session_state event', () => {
      const state = makeGameState({ turn_number: 5 });
      handleServerMessage({
        type: 'session_state',
        state: state as unknown as Record<string, unknown>,
      });
      expect(get(gameState)).toEqual(state);
    });
  });

  describe('handleServerMessage — turn_update', () => {
    it('appends a turn entry to ground_truth_log', () => {
      gameState.set(makeGameState({ ground_truth_log: ['[dm]: Start'] }));
      handleServerMessage({
        type: 'turn_update',
        turn: 1,
        agent: 'fighter',
        content: 'I attack the goblin',
        state: {},
      });
      const gs = get(gameState);
      expect(gs!.ground_truth_log).toEqual([
        '[dm]: Start',
        '[fighter]: I attack the goblin',
      ]);
      expect(gs!.current_turn).toBe('fighter');
      expect(gs!.turn_number).toBe(1);
    });

    it('uses uppercase SHEET prefix for SHEET agent', () => {
      gameState.set(makeGameState());
      handleServerMessage({
        type: 'turn_update',
        turn: 2,
        agent: 'SHEET',
        content: 'Updated character stats',
        state: {},
      });
      const gs = get(gameState);
      expect(gs!.ground_truth_log).toContain('[SHEET]: Updated character stats');
    });

    it('preserves SHEET prefix regardless of case', () => {
      gameState.set(makeGameState());
      handleServerMessage({
        type: 'turn_update',
        turn: 2,
        agent: 'sheet',
        content: 'Stats updated',
        state: {},
      });
      const gs = get(gameState);
      expect(gs!.ground_truth_log).toContain('[SHEET]: Stats updated');
    });

    it('returns null when gameState is null (no crash)', () => {
      expect(get(gameState)).toBeNull();
      handleServerMessage({
        type: 'turn_update',
        turn: 1,
        agent: 'dm',
        content: 'Hello',
        state: {},
      });
      // State should still be null since update on null returns null
      expect(get(gameState)).toBeNull();
    });

    it('clears isThinking, awaitingInput, awaitingInputCharacter', () => {
      isThinking.set(true);
      awaitingInput.set(true);
      awaitingInputCharacter.set('fighter');
      gameState.set(makeGameState());

      handleServerMessage({
        type: 'turn_update',
        turn: 1,
        agent: 'dm',
        content: 'The adventure begins',
        state: {},
      });

      expect(get(isThinking)).toBe(false);
      expect(get(awaitingInput)).toBe(false);
      expect(get(awaitingInputCharacter)).toBe('');
    });
  });

  describe('handleServerMessage — autopilot_started', () => {
    it('sets isAutopilotRunning and isThinking to true', () => {
      handleServerMessage({ type: 'autopilot_started' });
      expect(get(isAutopilotRunning)).toBe(true);
      expect(get(isThinking)).toBe(true);
      expect(get(thinkingAgent)).toBe('dm');
    });
  });

  describe('handleServerMessage — autopilot_stopped', () => {
    it('sets isAutopilotRunning and isThinking to false', () => {
      isAutopilotRunning.set(true);
      isThinking.set(true);
      handleServerMessage({ type: 'autopilot_stopped', reason: 'user_stopped' });
      expect(get(isAutopilotRunning)).toBe(false);
      expect(get(isThinking)).toBe(false);
    });
  });

  describe('handleServerMessage — paused', () => {
    it('sets isPaused true and isThinking false', () => {
      isThinking.set(true);
      handleServerMessage({ type: 'paused' });
      expect(get(isPaused)).toBe(true);
      expect(get(isThinking)).toBe(false);
    });
  });

  describe('handleServerMessage — resumed', () => {
    it('sets isPaused to false', () => {
      isPaused.set(true);
      handleServerMessage({ type: 'resumed' });
      expect(get(isPaused)).toBe(false);
    });
  });

  describe('handleServerMessage — speed_changed', () => {
    it('sets speed to the event value', () => {
      handleServerMessage({ type: 'speed_changed', speed: 'fast' });
      expect(get(speed)).toBe('fast');
    });
  });

  describe('handleServerMessage — drop_in', () => {
    it('sets human_active and controlled_character on gameState', () => {
      gameState.set(makeGameState());
      handleServerMessage({ type: 'drop_in', character: 'rogue' });
      const gs = get(gameState);
      expect(gs!.human_active).toBe(true);
      expect(gs!.controlled_character).toBe('rogue');
    });

    it('sets uiMode to play', () => {
      gameState.set(makeGameState());
      handleServerMessage({ type: 'drop_in', character: 'rogue' });
      expect(get(uiState).uiMode).toBe('play');
    });
  });

  describe('handleServerMessage — release_control', () => {
    it('clears human_active and controlled_character', () => {
      gameState.set(makeGameState({ human_active: true, controlled_character: 'rogue' }));
      handleServerMessage({ type: 'release_control' });
      const gs = get(gameState);
      expect(gs!.human_active).toBe(false);
      expect(gs!.controlled_character).toBeNull();
    });

    it('sets uiMode to watch', () => {
      uiState.update((s) => ({ ...s, uiMode: 'play' as const }));
      gameState.set(makeGameState({ human_active: true, controlled_character: 'rogue' }));
      handleServerMessage({ type: 'release_control' });
      expect(get(uiState).uiMode).toBe('watch');
    });

    it('clears awaitingInput and awaitingInputCharacter', () => {
      awaitingInput.set(true);
      awaitingInputCharacter.set('rogue');
      gameState.set(makeGameState({ human_active: true, controlled_character: 'rogue' }));
      handleServerMessage({ type: 'release_control' });
      expect(get(awaitingInput)).toBe(false);
      expect(get(awaitingInputCharacter)).toBe('');
    });
  });

  describe('handleServerMessage — awaiting_input', () => {
    it('sets awaitingInput true and awaitingInputCharacter', () => {
      handleServerMessage({ type: 'awaiting_input', character: 'fighter' });
      expect(get(awaitingInput)).toBe(true);
      expect(get(awaitingInputCharacter)).toBe('fighter');
    });
  });

  describe('handleServerMessage — error', () => {
    it('clears isThinking', () => {
      isThinking.set(true);
      handleServerMessage({ type: 'error', message: 'something went wrong', recoverable: true });
      expect(get(isThinking)).toBe(false);
    });
  });

  describe('handleServerMessage — unknown event type', () => {
    it('does not change any stores', () => {
      gameState.set(makeGameState());
      const stateBefore = get(gameState);
      const autopilotBefore = get(isAutopilotRunning);
      const pausedBefore = get(isPaused);

      handleServerMessage({ type: 'command_ack', command: 'test' } as WsServerEvent);

      expect(get(gameState)).toEqual(stateBefore);
      expect(get(isAutopilotRunning)).toBe(autopilotBefore);
      expect(get(isPaused)).toBe(pausedBefore);
    });
  });

  describe('resetStores', () => {
    it('resets all stores to initial values', () => {
      gameState.set(makeGameState());
      isAutopilotRunning.set(true);
      isPaused.set(true);
      speed.set('fast');
      isThinking.set(true);
      thinkingAgent.set('fighter');
      awaitingInput.set(true);
      awaitingInputCharacter.set('rogue');

      resetStores();

      expect(get(gameState)).toBeNull();
      expect(get(isAutopilotRunning)).toBe(false);
      expect(get(isPaused)).toBe(false);
      expect(get(speed)).toBe('normal');
      expect(get(isThinking)).toBe(false);
      expect(get(thinkingAgent)).toBe('dm');
      expect(get(awaitingInput)).toBe(false);
      expect(get(awaitingInputCharacter)).toBe('');
    });
  });
});
