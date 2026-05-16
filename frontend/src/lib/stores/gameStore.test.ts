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
      npcSheetName: null,
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
    it('appends new_entries to existing ground_truth_log', () => {
      gameState.set(makeGameState({ ground_truth_log: ['[dm]: Start'] }));
      handleServerMessage({
        type: 'turn_update',
        turn: 3,
        agent: 'fighter',
        content: '[fighter]: I attack the goblin',
        new_entries: ['[dm]: The round begins', '[fighter]: I attack the goblin'],
        state: {},
      });
      const gs = get(gameState);
      expect(gs!.ground_truth_log).toEqual([
        '[dm]: Start',
        '[dm]: The round begins',
        '[fighter]: I attack the goblin',
      ]);
      expect(gs!.current_turn).toBe('fighter');
      expect(gs!.turn_number).toBe(3);
    });

    it('appends all agents from a full round via new_entries', () => {
      gameState.set(makeGameState({ ground_truth_log: [] }));
      const newEntries = [
        '[dm]: The adventure begins',
        '[Brother Aldric]: I cast a spell',
        '[Elara]: I examine the runes',
        '[Shadowmere]: I check for traps',
        '[Thorin]: I take point',
      ];
      handleServerMessage({
        type: 'turn_update',
        turn: 5,
        agent: 'Thorin',
        content: '[Thorin]: I take point',
        new_entries: newEntries,
        state: {},
      });
      const gs = get(gameState);
      expect(gs!.ground_truth_log).toEqual(newEntries);
      expect(gs!.ground_truth_log).toHaveLength(5);
    });

    it('keeps existing log when new_entries is missing', () => {
      gameState.set(makeGameState({ ground_truth_log: ['[dm]: Start'] }));
      handleServerMessage({
        type: 'turn_update',
        turn: 1,
        agent: 'fighter',
        content: 'I attack the goblin',
        state: {},
      });
      const gs = get(gameState);
      expect(gs!.ground_truth_log).toEqual(['[dm]: Start']);
    });

    it('Story 15-9: merges combat_state from turn_update snapshot for live NPC HP', () => {
      // Story 15-9 / code-review fix: the engine widens the turn_update snapshot
      // with combat_state (carrying mutated npc_profiles.hp_current). Without
      // this merge, the NpcPanel would freeze at the values from the last
      // session_state event and never reflect live HP changes.
      gameState.set(
        makeGameState({
          combat_state: {
            active: true,
            round_number: 1,
            initiative_order: [],
            initiative_rolls: {},
            npc_profiles: {
              goblin_1: {
                name: 'Goblin 1',
                initiative_modifier: 2,
                hp_max: 10,
                hp_current: 10,
                ac: 13,
                personality: '',
                tactics: '',
                secret: '',
                conditions: [],
              },
            },
          },
        }),
      );
      handleServerMessage({
        type: 'turn_update',
        turn: 2,
        agent: 'fighter',
        content: '[fighter]: I swing.',
        new_entries: ['[fighter]: I swing.'],
        state: {
          combat_state: {
            active: true,
            round_number: 1,
            initiative_order: [],
            initiative_rolls: {},
            npc_profiles: {
              goblin_1: {
                name: 'Goblin 1',
                initiative_modifier: 2,
                hp_max: 10,
                hp_current: 4, // <-- live mutation from dm_update_npc
                ac: 13,
                personality: '',
                tactics: '',
                secret: '',
                conditions: ['bleeding'],
              },
            },
          },
        } as unknown as Record<string, unknown>,
      });
      const gs = get(gameState);
      expect(gs!.combat_state?.npc_profiles.goblin_1.hp_current).toBe(4);
      expect(gs!.combat_state?.npc_profiles.goblin_1.conditions).toEqual(['bleeding']);
    });

    it('Story 15-9: combat_state=null in snapshot clears prior combat_state (combat ended)', () => {
      gameState.set(
        makeGameState({
          combat_state: {
            active: true,
            round_number: 1,
            initiative_order: [],
            initiative_rolls: {},
            npc_profiles: {
              g: {
                name: 'g',
                initiative_modifier: 0,
                hp_max: 1,
                hp_current: 1,
                ac: 10,
                personality: '',
                tactics: '',
                secret: '',
                conditions: [],
              },
            },
          },
        }),
      );
      handleServerMessage({
        type: 'turn_update',
        turn: 3,
        agent: 'dm',
        content: '[dm]: Combat ends.',
        new_entries: ['[dm]: Combat ends.'],
        state: { combat_state: null } as unknown as Record<string, unknown>,
      });
      const gs = get(gameState);
      expect(gs!.combat_state).toBeNull();
    });

    it('Story 15-9: omitted combat_state in snapshot preserves prior combat_state', () => {
      // If the backend ever sends a snapshot without combat_state (e.g., an
      // intermediate event before the field exists), DO NOT clobber the
      // existing one. Only update when the key is present.
      const cs = {
        active: true,
        round_number: 4,
        initiative_order: [],
        initiative_rolls: {},
        npc_profiles: {},
      };
      gameState.set(makeGameState({ combat_state: cs }));
      handleServerMessage({
        type: 'turn_update',
        turn: 5,
        agent: 'rogue',
        content: '[rogue]: sneaky',
        state: {} as Record<string, unknown>,
      });
      const gs = get(gameState);
      expect(gs!.combat_state).toEqual(cs);
    });

    // =========================================================================
    // Gap-coverage additions (testarch-automate, 2026-05-16)
    // Snapshot merge edge-cases not covered by the 3 existing Story 15-9 tests.
    // =========================================================================

    it('Story 15-9: characters in snapshot are merged on turn_update', () => {
      // The Story 15-9 gameStore fix merges BOTH combat_state and characters
      // from the turn_update snapshot. Without merging characters, character
      // HP/XP changes (from non-combat tool calls) would also stall.
      gameState.set(
        makeGameState({
          characters: {
            fighter: { name: 'Fighter', hp_current: 30, hp_max: 30 },
          } as unknown as GameState['characters'],
        }),
      );
      handleServerMessage({
        type: 'turn_update',
        turn: 2,
        agent: 'dm',
        content: '[dm]: An attack lands.',
        new_entries: ['[dm]: An attack lands.'],
        state: {
          characters: {
            fighter: { name: 'Fighter', hp_current: 22, hp_max: 30 },
          },
        } as unknown as Record<string, unknown>,
      });
      const gs = get(gameState);
      expect((gs!.characters as Record<string, { hp_current: number }>).fighter.hp_current).toBe(
        22,
      );
    });

    it('Story 15-9: combat_state AND characters can be merged in one turn_update', () => {
      // Realistic scenario: an attack mutates both an NPC's HP (combat_state)
      // and a PC's HP (characters) in the same round. The merge must apply
      // both selectively without dropping either.
      gameState.set(
        makeGameState({
          characters: {
            fighter: { name: 'Fighter', hp_current: 30, hp_max: 30 },
          } as unknown as GameState['characters'],
          combat_state: {
            active: true,
            round_number: 1,
            initiative_order: [],
            initiative_rolls: {},
            npc_profiles: {
              orc: {
                name: 'Orc',
                initiative_modifier: 1,
                hp_max: 20,
                hp_current: 20,
                ac: 13,
                personality: '',
                tactics: '',
                secret: '',
                conditions: [],
              },
            },
          },
        }),
      );
      handleServerMessage({
        type: 'turn_update',
        turn: 2,
        agent: 'dm',
        content: '[dm]: Trade of blows.',
        new_entries: ['[dm]: Trade of blows.'],
        state: {
          characters: {
            fighter: { name: 'Fighter', hp_current: 22, hp_max: 30 },
          },
          combat_state: {
            active: true,
            round_number: 1,
            initiative_order: [],
            initiative_rolls: {},
            npc_profiles: {
              orc: {
                name: 'Orc',
                initiative_modifier: 1,
                hp_max: 20,
                hp_current: 12,
                ac: 13,
                personality: '',
                tactics: '',
                secret: '',
                conditions: [],
              },
            },
          },
        } as unknown as Record<string, unknown>,
      });
      const gs = get(gameState);
      expect((gs!.characters as Record<string, { hp_current: number }>).fighter.hp_current).toBe(
        22,
      );
      expect(gs!.combat_state?.npc_profiles.orc.hp_current).toBe(12);
    });

    it('Story 15-9: missing snapshot (state=undefined) does not crash', () => {
      // Defense in depth: an older backend or a malformed event might omit
      // `state` entirely. The merge should treat it as empty and update only
      // log/agent/turn — not throw.
      gameState.set(
        makeGameState({
          combat_state: {
            active: true,
            round_number: 1,
            initiative_order: [],
            initiative_rolls: {},
            npc_profiles: {},
          },
        }),
      );
      handleServerMessage({
        type: 'turn_update',
        turn: 9,
        agent: 'dm',
        content: '[dm]: tick',
        new_entries: ['[dm]: tick'],
        // intentionally no `state` field
      } as unknown as WsServerEvent);
      const gs = get(gameState);
      expect(gs).not.toBeNull();
      expect(gs!.turn_number).toBe(9);
      // Prior combat_state preserved.
      expect(gs!.combat_state?.round_number).toBe(1);
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
        new_entries: ['[dm]: The adventure begins'],
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
