import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import {
  getSessions,
  createSession,
  getSession,
  deleteSession,
  getForks,
  createFork,
  deleteFork,
  getCharacterSheet,
  getImageDownloadUrl,
  getDownloadAllUrl,
  ApiError,
} from './api';

// Helper to create mock responses
function mockJsonResponse(data: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
    headers: new Headers({ 'Content-Type': 'application/json' }),
  } as Response);
}

function mock204Response() {
  return Promise.resolve({
    ok: true,
    status: 204,
    statusText: 'No Content',
    json: () => Promise.reject(new Error('No body')),
    text: () => Promise.resolve(''),
    headers: new Headers(),
  } as Response);
}

function mockErrorResponse(status: number, body: unknown, statusText = 'Error') {
  return Promise.resolve({
    ok: false,
    status,
    statusText,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
    headers: new Headers({ 'Content-Type': 'application/json' }),
  } as Response);
}

describe('api.ts', () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getSessions', () => {
    it('calls GET /api/sessions and returns parsed JSON', async () => {
      const sessions = [{ session_id: 'test-1', name: 'Adventure' }];
      mockFetch.mockReturnValueOnce(mockJsonResponse(sessions));

      const result = await getSessions();
      expect(result).toEqual(sessions);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sessions',
        expect.objectContaining({
          headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        }),
      );
    });
  });

  describe('createSession', () => {
    it('calls POST /api/sessions with the correct body', async () => {
      const response = { session_id: 'new-1', session_number: 1, name: 'My Session' };
      mockFetch.mockReturnValueOnce(mockJsonResponse(response));

      const result = await createSession('My Session');
      expect(result).toEqual(response);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sessions',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ name: 'My Session' }),
        }),
      );
    });

    it('sends empty name when no name provided', async () => {
      const response = { session_id: 'new-2', session_number: 2, name: '' };
      mockFetch.mockReturnValueOnce(mockJsonResponse(response));

      await createSession();
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sessions',
        expect.objectContaining({
          body: JSON.stringify({ name: '' }),
        }),
      );
    });
  });

  describe('getSession', () => {
    it('calls GET /api/sessions/{id} with URL-encoded session ID', async () => {
      const session = { session_id: 'test with spaces', name: 'Test' };
      mockFetch.mockReturnValueOnce(mockJsonResponse(session));

      const result = await getSession('test with spaces');
      expect(result).toEqual(session);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sessions/test%20with%20spaces',
        expect.any(Object),
      );
    });
  });

  describe('deleteSession', () => {
    it('calls DELETE and does not attempt response.json() on 204', async () => {
      mockFetch.mockReturnValueOnce(mock204Response());

      await expect(deleteSession('test-1')).resolves.toBeUndefined();
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sessions/test-1',
        expect.objectContaining({ method: 'DELETE' }),
      );
    });
  });

  describe('ApiError', () => {
    it('is thrown with correct status, statusText, and parsed detail on non-ok responses', async () => {
      mockFetch.mockReturnValueOnce(
        mockErrorResponse(404, { detail: 'Session not found' }, 'Not Found'),
      );

      try {
        await getSessions();
        expect.fail('Should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(404);
        expect(apiErr.statusText).toBe('Not Found');
        expect(apiErr.message).toBe('Session not found');
      }
    });

    it('falls back to raw body text when response is not JSON', async () => {
      mockFetch.mockReturnValueOnce(
        Promise.resolve({
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
          json: () => Promise.reject(new Error('not json')),
          text: () => Promise.resolve('Something went wrong'),
          headers: new Headers(),
        } as Response),
      );

      try {
        await getSessions();
        expect.fail('Should have thrown');
      } catch (err) {
        expect(err).toBeInstanceOf(ApiError);
        const apiErr = err as ApiError;
        expect(apiErr.status).toBe(500);
        expect(apiErr.message).toBe('Something went wrong');
      }
    });
  });

  describe('getForks', () => {
    it('calls GET /api/sessions/{id}/forks', async () => {
      const forks = [{ fork_id: 'fork-1', name: 'Fork A' }];
      mockFetch.mockReturnValueOnce(mockJsonResponse(forks));

      const result = await getForks('session-1');
      expect(result).toEqual(forks);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sessions/session-1/forks',
        expect.any(Object),
      );
    });
  });

  describe('createFork', () => {
    it('calls POST /api/sessions/{id}/forks with { name } body', async () => {
      const fork = { fork_id: 'fork-new', name: 'My Fork' };
      mockFetch.mockReturnValueOnce(mockJsonResponse(fork));

      const result = await createFork('session-1', 'My Fork');
      expect(result).toEqual(fork);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sessions/session-1/forks',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ name: 'My Fork' }),
        }),
      );
    });
  });

  describe('deleteFork', () => {
    it('handles 204 No Content without error', async () => {
      mockFetch.mockReturnValueOnce(mock204Response());

      await expect(deleteFork('session-1', 'fork-1')).resolves.toBeUndefined();
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sessions/session-1/forks/fork-1',
        expect.objectContaining({ method: 'DELETE' }),
      );
    });
  });

  describe('getCharacterSheet', () => {
    it('calls the correct endpoint with URL-encoded character name', async () => {
      const sheet = { name: 'Thorin Ironforge', character_class: 'Fighter' };
      mockFetch.mockReturnValueOnce(mockJsonResponse(sheet));

      const result = await getCharacterSheet('session-1', 'Thorin Ironforge');
      expect(result).toEqual(sheet);
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/sessions/session-1/character-sheets/Thorin%20Ironforge',
        expect.any(Object),
      );
    });
  });

  // Story 17-6: URL builder functions for image downloads
  describe('getImageDownloadUrl', () => {
    it('returns the correct download URL', () => {
      const url = getImageDownloadUrl('001', 'img-uuid-123');
      expect(url).toBe('/api/sessions/001/images/img-uuid-123/download');
    });

    it('encodes session ID with special characters', () => {
      const url = getImageDownloadUrl('session with spaces', 'img-001');
      expect(url).toBe('/api/sessions/session%20with%20spaces/images/img-001/download');
    });

    it('encodes image ID with special characters', () => {
      const url = getImageDownloadUrl('001', 'id with spaces');
      expect(url).toBe('/api/sessions/001/images/id%20with%20spaces/download');
    });
  });

  describe('getDownloadAllUrl', () => {
    it('returns the correct bulk download URL', () => {
      const url = getDownloadAllUrl('001');
      expect(url).toBe('/api/sessions/001/images/download-all');
    });

    it('encodes session ID with special characters', () => {
      const url = getDownloadAllUrl('session with spaces');
      expect(url).toBe('/api/sessions/session%20with%20spaces/images/download-all');
    });
  });
});
