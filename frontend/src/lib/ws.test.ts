import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createGameConnection } from './ws';

// Mock WebSocket class
let mockWsInstance: MockWebSocket;

class MockWebSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: { code: number; reason: string }) => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onerror: ((ev: unknown) => void) | null = null;
  send = vi.fn();
  close = vi.fn();
  url: string;

  constructor(url: string) {
    this.url = url;
    mockWsInstance = this;
  }
}

describe('ws.ts — createGameConnection', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket);
    // Mock window.location
    vi.stubGlobal('location', {
      protocol: 'http:',
      host: 'localhost:5173',
    });
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('connect() creates a WebSocket with the correct URL based on window.location', () => {
    const conn = createGameConnection('test-session-123', {
      initialDelay: 1000,
      maxDelay: 30000,
      maxAttempts: 0,
    });
    conn.connect();

    expect(mockWsInstance).toBeDefined();
    expect(mockWsInstance.url).toBe('ws://localhost:5173/ws/game/test-session-123');
  });

  it('connect() uses wss: when protocol is https:', () => {
    vi.stubGlobal('location', {
      protocol: 'https:',
      host: 'example.com',
    });

    const conn = createGameConnection('my-session', {
      initialDelay: 1000,
      maxDelay: 30000,
      maxAttempts: 0,
    });
    conn.connect();

    expect(mockWsInstance.url).toBe('wss://example.com/ws/game/my-session');
  });

  it('send() calls ws.send() with JSON-serialized command', () => {
    const conn = createGameConnection('test', {
      initialDelay: 1000,
      maxDelay: 30000,
      maxAttempts: 0,
    });
    conn.connect();

    // Simulate open
    mockWsInstance.readyState = MockWebSocket.OPEN;
    mockWsInstance.onopen?.(new Event('open'));

    conn.send({ type: 'next_turn' });
    expect(mockWsInstance.send).toHaveBeenCalledWith(JSON.stringify({ type: 'next_turn' }));
  });

  it('send() logs error when not connected', () => {
    const conn = createGameConnection('test', {
      initialDelay: 1000,
      maxDelay: 30000,
      maxAttempts: 0,
    });
    conn.connect();
    // readyState stays CONNECTING — not OPEN
    mockWsInstance.readyState = MockWebSocket.CONNECTING;

    conn.send({ type: 'next_turn' });
    expect(console.error).toHaveBeenCalledWith('[WS] Cannot send — not connected');
    expect(mockWsInstance.send).not.toHaveBeenCalled();
  });

  it('disconnect() closes the WebSocket with code 1000 and sets isConnected to false', () => {
    const conn = createGameConnection('test', {
      initialDelay: 1000,
      maxDelay: 30000,
      maxAttempts: 0,
    });
    conn.connect();
    mockWsInstance.readyState = MockWebSocket.OPEN;
    mockWsInstance.onopen?.(new Event('open'));

    expect(conn.isConnected).toBe(true);
    conn.disconnect();
    expect(mockWsInstance.close).toHaveBeenCalledWith(1000, 'Client disconnect');
    expect(conn.isConnected).toBe(false);
  });

  it('onMessage callback receives parsed server events', () => {
    const conn = createGameConnection('test', {
      initialDelay: 1000,
      maxDelay: 30000,
      maxAttempts: 0,
    });
    const messageHandler = vi.fn();
    conn.onMessage(messageHandler);

    conn.connect();
    mockWsInstance.readyState = MockWebSocket.OPEN;
    mockWsInstance.onopen?.(new Event('open'));

    // Simulate a message
    const event = { type: 'turn_update', turn: 1, agent: 'dm', content: 'Hello', state: {} };
    mockWsInstance.onmessage?.({ data: JSON.stringify(event) });

    expect(messageHandler).toHaveBeenCalledWith(event);
  });

  it('onConnect callback fires when ws.onopen triggers', () => {
    const conn = createGameConnection('test', {
      initialDelay: 1000,
      maxDelay: 30000,
      maxAttempts: 0,
    });
    const connectHandler = vi.fn();
    conn.onConnect(connectHandler);

    conn.connect();
    mockWsInstance.readyState = MockWebSocket.OPEN;
    mockWsInstance.onopen?.(new Event('open'));

    expect(connectHandler).toHaveBeenCalled();
  });

  it('onDisconnect callback fires when ws.onclose triggers', () => {
    const conn = createGameConnection('test', {
      initialDelay: 1000,
      maxDelay: 30000,
      maxAttempts: 0,
    });
    const disconnectHandler = vi.fn();
    conn.onDisconnect(disconnectHandler);

    conn.connect();
    mockWsInstance.readyState = MockWebSocket.OPEN;
    mockWsInstance.onopen?.(new Event('open'));

    mockWsInstance.onclose?.({ code: 1000, reason: 'Normal closure' });
    expect(disconnectHandler).toHaveBeenCalledWith('Normal closure');
  });

  it('automatically responds to ping events with pong', () => {
    const conn = createGameConnection('test', {
      initialDelay: 1000,
      maxDelay: 30000,
      maxAttempts: 0,
    });
    const messageHandler = vi.fn();
    conn.onMessage(messageHandler);

    conn.connect();
    mockWsInstance.readyState = MockWebSocket.OPEN;
    mockWsInstance.onopen?.(new Event('open'));

    // Simulate a ping message
    mockWsInstance.onmessage?.({ data: JSON.stringify({ type: 'ping' }) });

    // Should auto-respond with pong
    expect(mockWsInstance.send).toHaveBeenCalledWith(JSON.stringify({ type: 'pong' }));
    // Should NOT pass ping to message callbacks
    expect(messageHandler).not.toHaveBeenCalled();
  });
});
