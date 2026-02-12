import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import { narrativeMessages, displayLimit } from './narrativeStore';
import { gameState, resetStores } from './gameStore';
import { makeGameState } from '../../tests/fixtures';

describe('narrativeStore', () => {
  beforeEach(() => {
    resetStores();
  });

  it('narrativeMessages returns empty array when gameState is null', () => {
    expect(get(gameState)).toBeNull();
    expect(get(narrativeMessages)).toEqual([]);
  });

  it('narrativeMessages parses ground_truth_log entries into ParsedMessage[]', () => {
    gameState.set(
      makeGameState({
        ground_truth_log: [
          '[dm]: The tavern is dimly lit',
          '[fighter]: I approach the bar',
          '[SHEET]: Stats updated',
        ],
      }),
    );

    const messages = get(narrativeMessages);
    expect(messages).toHaveLength(3);
    expect(messages[0]).toMatchObject({
      agent: 'dm',
      content: 'The tavern is dimly lit',
      messageType: 'dm_narration',
      index: 0,
    });
    expect(messages[1]).toMatchObject({
      agent: 'fighter',
      content: 'I approach the bar',
      messageType: 'pc_dialogue',
      index: 1,
    });
    expect(messages[2]).toMatchObject({
      agent: 'SHEET',
      content: 'Stats updated',
      messageType: 'sheet_update',
      index: 2,
    });
  });

  it('narrativeMessages re-derives when gameState changes', () => {
    gameState.set(makeGameState({ ground_truth_log: ['[dm]: First message'] }));
    expect(get(narrativeMessages)).toHaveLength(1);

    gameState.set(
      makeGameState({
        ground_truth_log: ['[dm]: First message', '[rogue]: Second message'],
      }),
    );
    expect(get(narrativeMessages)).toHaveLength(2);
  });

  it('displayLimit defaults to 50 when narrative_display_limit is not configured', () => {
    gameState.set(null);
    expect(get(displayLimit)).toBe(50);
  });

  it('displayLimit reflects configured value when present', () => {
    gameState.set(
      makeGameState({
        game_config: {
          combat_mode: 'Narrative',
          summarizer_provider: 'gemini',
          summarizer_model: 'gemini-2.0-flash',
          extractor_provider: 'gemini',
          extractor_model: 'gemini-2.0-flash',
          party_size: 4,
          narrative_display_limit: 100,
          max_combat_rounds: 10,
          dm_provider: 'gemini',
          dm_model: 'gemini-1.5-flash',
          dm_token_limit: 8000,
        },
      }),
    );
    expect(get(displayLimit)).toBe(100);
  });
});
