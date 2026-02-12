import type {
  Session,
  SessionCreateResponse,
  GameConfig,
  Character,
  CharacterDetail,
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
