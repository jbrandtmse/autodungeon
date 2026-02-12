import type {
  Session,
  SessionCreateResponse,
  GameConfig,
  Character,
  CharacterDetail,
  CharacterCreateRequest,
  CharacterUpdateRequest,
  ModelListResult,
  ForkMetadata,
  ComparisonData,
  CheckpointInfo,
  CheckpointPreview,
  CharacterSheetFull,
  UserSettings,
  UserSettingsUpdate,
  ModuleDiscoveryResponse,
  SessionStartConfig,
} from './types';

const BASE_URL = '';  // Empty — Vite proxy handles /api routing

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const { headers: optionHeaders, ...restOptions } = options ?? {};
  const response = await fetch(`${BASE_URL}${path}`, {
    ...restOptions,
    headers: {
      'Content-Type': 'application/json',
      ...(optionHeaders instanceof Headers
        ? Object.fromEntries(optionHeaders.entries())
        : optionHeaders),
    },
  });

  if (!response.ok) {
    const body = await response.text();
    let message: string;
    try {
      const json = JSON.parse(body);
      message = json.detail || json.message || body;
    } catch {
      message = body || response.statusText;
    }
    throw new ApiError(response.status, response.statusText, message);
  }

  return response.json();
}

// Session endpoints
export async function getSessions(): Promise<Session[]> {
  return request<Session[]>('/api/sessions');
}

export async function createSession(name?: string): Promise<SessionCreateResponse> {
  return request<SessionCreateResponse>('/api/sessions', {
    method: 'POST',
    body: JSON.stringify({ name: name ?? '' }),
  });
}

export async function getSession(sessionId: string): Promise<Session> {
  return request<Session>(`/api/sessions/${encodeURIComponent(sessionId)}`);
}

export async function deleteSession(sessionId: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const body = await response.text();
    let message: string;
    try {
      const json = JSON.parse(body);
      message = json.detail || json.message || body;
    } catch {
      message = body || response.statusText;
    }
    throw new ApiError(response.status, response.statusText, message);
  }
  // 204 No Content — no body to parse
}

export async function getSessionConfig(sessionId: string): Promise<GameConfig> {
  return request<GameConfig>(`/api/sessions/${encodeURIComponent(sessionId)}/config`);
}

export async function updateSessionConfig(
  sessionId: string,
  config: Partial<GameConfig>,
): Promise<GameConfig> {
  return request<GameConfig>(`/api/sessions/${encodeURIComponent(sessionId)}/config`, {
    method: 'PUT',
    body: JSON.stringify(config),
  });
}

// Character endpoints
export async function getCharacters(): Promise<Character[]> {
  return request<Character[]>('/api/characters');
}

export async function getCharacter(name: string): Promise<CharacterDetail> {
  return request<CharacterDetail>(`/api/characters/${encodeURIComponent(name)}`);
}

export async function createCharacter(data: CharacterCreateRequest): Promise<CharacterDetail> {
  return request<CharacterDetail>('/api/characters', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateCharacter(
  name: string,
  data: CharacterUpdateRequest,
): Promise<CharacterDetail> {
  return request<CharacterDetail>(`/api/characters/${encodeURIComponent(name)}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteCharacter(name: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/api/characters/${encodeURIComponent(name)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const body = await response.text();
    let message: string;
    try {
      const json = JSON.parse(body);
      message = json.detail || json.message || body;
    } catch {
      message = body || response.statusText;
    }
    throw new ApiError(response.status, response.statusText, message);
  }
  // 204 No Content — no body to parse
}

// === Model Listing API ===

export async function getModels(provider: string): Promise<ModelListResult> {
  return request<ModelListResult>(`/api/models/${encodeURIComponent(provider)}`);
}

// Re-export for modelUtils
export type { ModelListResult };

// === User Settings API ===

export async function getUserSettings(): Promise<UserSettings> {
  return request<UserSettings>('/api/user-settings');
}

export async function updateUserSettings(data: UserSettingsUpdate): Promise<UserSettings> {
  return request<UserSettings>('/api/user-settings', {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

// === Fork Management API (Story 16-10) ===

export async function getForks(sessionId: string): Promise<ForkMetadata[]> {
  return request<ForkMetadata[]>(
    `/api/sessions/${encodeURIComponent(sessionId)}/forks`,
  );
}

export async function createFork(
  sessionId: string,
  name: string,
): Promise<ForkMetadata> {
  return request<ForkMetadata>(
    `/api/sessions/${encodeURIComponent(sessionId)}/forks`,
    {
      method: 'POST',
      body: JSON.stringify({ name }),
    },
  );
}

export async function renameFork(
  sessionId: string,
  forkId: string,
  name: string,
): Promise<ForkMetadata> {
  return request<ForkMetadata>(
    `/api/sessions/${encodeURIComponent(sessionId)}/forks/${encodeURIComponent(forkId)}`,
    {
      method: 'PUT',
      body: JSON.stringify({ name }),
    },
  );
}

export async function deleteFork(sessionId: string, forkId: string): Promise<void> {
  const response = await fetch(
    `${BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}/forks/${encodeURIComponent(forkId)}`,
    { method: 'DELETE' },
  );
  if (!response.ok) {
    const body = await response.text();
    let message: string;
    try {
      const json = JSON.parse(body);
      message = json.detail || json.message || body;
    } catch {
      message = body || response.statusText;
    }
    throw new ApiError(response.status, response.statusText, message);
  }
  // 204 No Content — no body to parse
}

export async function switchFork(sessionId: string, forkId: string): Promise<void> {
  await request<{ status: string; fork_id: string }>(
    `/api/sessions/${encodeURIComponent(sessionId)}/forks/${encodeURIComponent(forkId)}/switch`,
    { method: 'POST' },
  );
}

export async function promoteFork(sessionId: string, forkId: string): Promise<void> {
  await request<{ status: string; latest_turn: number }>(
    `/api/sessions/${encodeURIComponent(sessionId)}/forks/${encodeURIComponent(forkId)}/promote`,
    { method: 'POST' },
  );
}

export async function returnToMain(sessionId: string): Promise<void> {
  await request<{ status: string }>(
    `/api/sessions/${encodeURIComponent(sessionId)}/forks/return-to-main`,
    { method: 'POST' },
  );
}

export async function getComparison(
  sessionId: string,
  forkId: string,
): Promise<ComparisonData> {
  return request<ComparisonData>(
    `/api/sessions/${encodeURIComponent(sessionId)}/forks/${encodeURIComponent(forkId)}/compare`,
  );
}

// === Checkpoint API (Story 16-10) ===

export async function getCheckpoints(sessionId: string): Promise<CheckpointInfo[]> {
  return request<CheckpointInfo[]>(
    `/api/sessions/${encodeURIComponent(sessionId)}/checkpoints`,
  );
}

export async function getCheckpointPreview(
  sessionId: string,
  turn: number,
): Promise<CheckpointPreview> {
  return request<CheckpointPreview>(
    `/api/sessions/${encodeURIComponent(sessionId)}/checkpoints/${turn}/preview`,
  );
}

export async function restoreCheckpoint(sessionId: string, turn: number): Promise<void> {
  await request<{ status: string; turn: number }>(
    `/api/sessions/${encodeURIComponent(sessionId)}/checkpoints/${turn}/restore`,
    { method: 'POST' },
  );
}

// === Character Sheet API (Story 16-10) ===

export async function getCharacterSheet(
  sessionId: string,
  name: string,
): Promise<CharacterSheetFull> {
  return request<CharacterSheetFull>(
    `/api/sessions/${encodeURIComponent(sessionId)}/character-sheets/${encodeURIComponent(name)}`,
  );
}

// === Module Discovery & Session Start API ===

export async function discoverModules(): Promise<ModuleDiscoveryResponse> {
  return request<ModuleDiscoveryResponse>('/api/modules/discover', { method: 'POST' });
}

export async function startSession(
  sessionId: string,
  config: SessionStartConfig,
): Promise<{ status: string; session_id: string }> {
  return request<{ status: string; session_id: string }>(
    `/api/sessions/${encodeURIComponent(sessionId)}/start`,
    {
      method: 'POST',
      body: JSON.stringify(config),
    },
  );
}
