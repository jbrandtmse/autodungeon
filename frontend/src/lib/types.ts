// === REST API Types ===
// Mirrors api/schemas.py Pydantic models

export interface Session {
  session_id: string;
  session_number: number;
  name: string;
  created_at: string;
  updated_at: string;
  character_names: string[];
  turn_count: number;
}

export interface SessionCreateResponse {
  session_id: string;
  session_number: number;
  name: string;
}

export interface GameConfig {
  combat_mode: 'Narrative' | 'Tactical';
  summarizer_provider: string;
  summarizer_model: string;
  extractor_provider: string;
  extractor_model: string;
  party_size: number;
  narrative_display_limit: number;
  max_combat_rounds: number;
}

export interface Character {
  name: string;
  character_class: string;
  personality: string;
  color: string;
  provider: string;
  model: string;
  source: 'preset' | 'library';
}

export interface CharacterDetail extends Character {
  token_limit: number;
  backstory: string;
}

export interface CharacterCreateRequest {
  name: string;
  character_class: string;
  personality?: string;
  backstory?: string;
  color?: string;
  provider?: string;
  model?: string;
  token_limit?: number;
}

export interface CharacterUpdateRequest {
  name?: string;
  character_class?: string;
  personality?: string;
  backstory?: string;
  color?: string;
  provider?: string;
  model?: string;
  token_limit?: number;
}

export interface AgentMemory {
  long_term_summary: string;
  short_term_buffer: string[];
  token_limit: number;
}

export interface TurnEntry {
  turn: number;
  agent: string;
  content: string;
}

export interface CharacterSheetHP {
  current: number;
  max: number;
  temp: number;
}

export interface CombatState {
  active: boolean;
  round_number: number;
  initiative_order: string[];
  initiative_rolls: Record<string, number>;
  current_combatant: string;
  npc_profiles: Record<string, { name: string }>;
}

export interface GameState {
  ground_truth_log: string[];
  turn_queue: string[];
  current_turn: string;
  agent_memories: Record<string, AgentMemory>;
  game_config: GameConfig;
  human_active: boolean;
  controlled_character: string | null;
  turn_number: number;
  session_id: string;
  characters?: Record<string, Character>;
  combat_state?: CombatState | null;
  character_sheets?: Record<string, { hp: CharacterSheetHP }>;
}

// === WebSocket Server-to-Client Events ===

export interface WsTurnUpdate {
  type: 'turn_update';
  turn: number;
  agent: string;
  content: string;
  state: Record<string, unknown>;
}

export interface WsSessionState {
  type: 'session_state';
  state: Record<string, unknown>;
}

export interface WsError {
  type: 'error';
  message: string;
  recoverable: boolean;
}

export interface WsAutopilotStarted {
  type: 'autopilot_started';
}

export interface WsAutopilotStopped {
  type: 'autopilot_stopped';
  reason: string;
}

export interface WsDropIn {
  type: 'drop_in';
  character: string;
}

export interface WsReleaseControl {
  type: 'release_control';
}

export interface WsAwaitingInput {
  type: 'awaiting_input';
  character: string;
}

export interface WsNudgeReceived {
  type: 'nudge_received';
}

export interface WsSpeedChanged {
  type: 'speed_changed';
  speed: string;
}

export interface WsPaused {
  type: 'paused';
}

export interface WsResumed {
  type: 'resumed';
}

export interface WsPing {
  type: 'ping';
}

export interface WsPong {
  type: 'pong';
}

export interface WsCommandAck {
  type: 'command_ack';
  command: string;
}

export type WsServerEvent =
  | WsTurnUpdate
  | WsSessionState
  | WsError
  | WsAutopilotStarted
  | WsAutopilotStopped
  | WsDropIn
  | WsReleaseControl
  | WsAwaitingInput
  | WsNudgeReceived
  | WsSpeedChanged
  | WsPaused
  | WsResumed
  | WsPing
  | WsPong
  | WsCommandAck;

// === WebSocket Client-to-Server Commands ===

export interface WsCmdStartAutopilot {
  type: 'start_autopilot';
  speed?: string;
}

export interface WsCmdStopAutopilot {
  type: 'stop_autopilot';
}

export interface WsCmdNextTurn {
  type: 'next_turn';
}

export interface WsCmdDropIn {
  type: 'drop_in';
  character: string;
}

export interface WsCmdReleaseControl {
  type: 'release_control';
}

export interface WsCmdSubmitAction {
  type: 'submit_action';
  content: string;
}

export interface WsCmdNudge {
  type: 'nudge';
  content: string;
}

export interface WsCmdSetSpeed {
  type: 'set_speed';
  speed: string;
}

export interface WsCmdPause {
  type: 'pause';
}

export interface WsCmdResume {
  type: 'resume';
}

export interface WsCmdRetry {
  type: 'retry';
}

export type WsCommand =
  | WsCmdStartAutopilot
  | WsCmdStopAutopilot
  | WsCmdNextTurn
  | WsCmdDropIn
  | WsCmdReleaseControl
  | WsCmdSubmitAction
  | WsCmdNudge
  | WsCmdSetSpeed
  | WsCmdPause
  | WsCmdResume
  | WsCmdRetry;
