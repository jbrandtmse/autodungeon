import type { GameState, Session, GameConfig } from '$lib/types';

export function makeGameConfig(overrides: Partial<GameConfig> = {}): GameConfig {
  return {
    combat_mode: 'Narrative',
    summarizer_provider: 'gemini',
    summarizer_model: 'gemini-2.0-flash',
    extractor_provider: 'gemini',
    extractor_model: 'gemini-2.0-flash',
    party_size: 4,
    narrative_display_limit: 50,
    max_combat_rounds: 10,
    ...overrides,
  };
}

export function makeGameState(overrides: Partial<GameState> = {}): GameState {
  return {
    ground_truth_log: [],
    turn_queue: ['dm', 'fighter', 'rogue'],
    current_turn: 'dm',
    agent_memories: {},
    game_config: makeGameConfig(overrides.game_config),
    human_active: false,
    controlled_character: null,
    turn_number: 0,
    session_id: 'test-session-001',
    ...overrides,
  };
}

export function makeSession(overrides: Partial<Session> = {}): Session {
  return {
    session_id: 'test-001',
    session_number: 1,
    name: 'Test Adventure',
    created_at: '2026-02-01T12:00:00Z',
    updated_at: '2026-02-01T14:00:00Z',
    character_names: ['Shadowmere', 'Thorin', 'Elara'],
    turn_count: 42,
    ...overrides,
  };
}
