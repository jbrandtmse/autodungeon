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
  dm_provider: string;
  dm_model: string;
  dm_token_limit: number;
}

export interface UserSettings {
  google_api_key_configured: boolean;
  anthropic_api_key_configured: boolean;
  ollama_url: string;
  token_limit_overrides: Record<string, number>;
}

export interface UserSettingsUpdate {
  google_api_key?: string;
  anthropic_api_key?: string;
  ollama_url?: string;
  token_limit_overrides?: Record<string, number>;
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

export interface AgentSecrets {
  whispers?: Whisper[];
  [key: string]: unknown;
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
  active_fork_id?: string | null;
  callback_database?: NarrativeElementStore | null;
  callback_log?: CallbackLog | null;
  agent_secrets?: Record<string, AgentSecrets> | null;
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

export interface WsCmdWhisper {
  type: 'whisper';
  content: string;
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
  | WsCmdRetry
  | WsCmdWhisper;

// === Fork Management Types (Story 16-10) ===

export interface ForkMetadata {
  fork_id: string;
  name: string;
  parent_session_id: string;
  branch_turn: number;
  created_at: string;
  updated_at: string;
  turn_count: number;
}

export interface ComparisonTurn {
  turn_number: number;
  entries: string[];
  is_branch_point: boolean;
  is_ended: boolean;
}

export interface ComparisonTimeline {
  label: string;
  timeline_type: 'main' | 'fork';
  fork_id: string | null;
  turns: ComparisonTurn[];
  total_turns: number;
}

export interface ComparisonData {
  session_id: string;
  branch_turn: number;
  left: ComparisonTimeline;
  right: ComparisonTimeline;
}

// === Whisper Types (Story 16-10) ===

export interface Whisper {
  id: string;
  from_agent: string;
  to_agent: string;
  content: string;
  turn_created: number;
  revealed: boolean;
  turn_revealed: number | null;
}

export interface WhisperHistory {
  [characterName: string]: Whisper[];
}

// === Character Sheet Types (Story 16-10) ===

export interface WeaponData {
  name: string;
  damage_dice: string;
  damage_type: string;
  properties: string[];
  attack_bonus: number;
  is_equipped: boolean;
}

export interface ArmorData {
  name: string;
  armor_class: number;
  armor_type: string;
  strength_requirement: number;
  stealth_disadvantage: boolean;
  is_equipped: boolean;
}

export interface EquipmentItemData {
  name: string;
  quantity: number;
  description: string;
  weight: number;
}

export interface SpellData {
  name: string;
  level: number;
  school: string;
  casting_time: string;
  range: string;
  components: string[];
  duration: string;
  description: string;
  is_prepared: boolean;
}

export interface SpellSlotsData {
  max: number;
  current: number;
}

export interface DeathSavesData {
  successes: number;
  failures: number;
}

export interface CharacterSheetFull {
  // Basic Info
  name: string;
  race: string;
  character_class: string;
  level: number;
  background: string;
  alignment: string;
  experience_points: number;

  // Ability Scores
  strength: number;
  dexterity: number;
  constitution: number;
  intelligence: number;
  wisdom: number;
  charisma: number;

  // Computed Modifiers
  strength_modifier: number;
  dexterity_modifier: number;
  constitution_modifier: number;
  intelligence_modifier: number;
  wisdom_modifier: number;
  charisma_modifier: number;
  proficiency_bonus: number;

  // Combat Stats
  armor_class: number;
  initiative: number;
  speed: number;
  hit_points_max: number;
  hit_points_current: number;
  hit_points_temp: number;
  hit_dice: string;
  hit_dice_remaining: number;

  // Saving Throws
  saving_throw_proficiencies: string[];

  // Skills
  skill_proficiencies: string[];
  skill_expertise: string[];

  // Proficiencies
  armor_proficiencies: string[];
  weapon_proficiencies: string[];
  tool_proficiencies: string[];
  languages: string[];

  // Features & Traits
  class_features: string[];
  racial_traits: string[];
  feats: string[];

  // Equipment
  weapons: WeaponData[];
  armor: ArmorData | null;
  equipment: EquipmentItemData[];
  gold: number;
  silver: number;
  copper: number;

  // Spellcasting
  spellcasting_ability: string | null;
  spell_save_dc: number | null;
  spell_attack_bonus: number | null;
  cantrips: string[];
  spells_known: SpellData[];
  spell_slots: Record<string, SpellSlotsData>;

  // Personality
  personality_traits: string;
  ideals: string;
  bonds: string;
  flaws: string;
  backstory: string;

  // Conditions & Status
  conditions: string[];
  death_saves: DeathSavesData;
}

// === Story Threads Types (Story 16-10) ===

export interface NarrativeElement {
  id: string;
  element_type: 'character' | 'item' | 'location' | 'event' | 'promise' | 'threat';
  name: string;
  description: string;
  turn_introduced: number;
  session_introduced: number;
  turns_referenced: number[];
  characters_involved: string[];
  resolved: boolean;
  times_referenced: number;
  last_referenced_turn: number;
  potential_callbacks: string[];
  dormant: boolean;
}

export interface NarrativeElementStore {
  elements: NarrativeElement[];
}

export interface CallbackEntry {
  id: string;
  element_id: string;
  element_name: string;
  element_type: string;
  turn_detected: number;
  turn_gap: number;
  match_type: 'name_exact' | 'name_fuzzy' | 'description_keyword';
  match_context: string;
  is_story_moment: boolean;
  session_detected: number;
}

export interface CallbackLog {
  entries: CallbackEntry[];
}

export interface StoryThreadsSummary {
  activeCount: number;
  dormantCount: number;
  storyMomentCount: number;
}

// === Checkpoint Types (Story 16-10) ===

export interface CheckpointInfo {
  turn_number: number;
  timestamp: string;
  brief_context: string;
  message_count: number;
}

export interface CheckpointPreview {
  turn_number: number;
  entries: string[];
}
