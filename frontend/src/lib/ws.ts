import type { WsServerEvent, WsCommand } from './types';

export interface GameConnection {
  connect(): void;
  disconnect(): void;
  send(command: WsCommand): void;
  onMessage(callback: (event: WsServerEvent) => void): () => void;
  onConnect(callback: () => void): () => void;
  onDisconnect(callback: (reason: string) => void): () => void;
  readonly isConnected: boolean;
}

interface ReconnectConfig {
  initialDelay: number;    // ms
  maxDelay: number;        // ms
  maxAttempts: number;
}

const DEFAULT_RECONNECT: ReconnectConfig = {
  initialDelay: 1000,
  maxDelay: 30000,
  maxAttempts: 5,
};

export function createGameConnection(
  sessionId: string,
  reconnectConfig: ReconnectConfig = DEFAULT_RECONNECT,
): GameConnection {
  let ws: WebSocket | null = null;
  let connected = false;
  let reconnectAttempts = 0;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  let intentionalClose = false;

  const messageCallbacks: Array<(event: WsServerEvent) => void> = [];
  const connectCallbacks: Array<() => void> = [];
  const disconnectCallbacks: Array<(reason: string) => void> = [];

  function getWsUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    return `${protocol}//${host}/ws/game/${encodeURIComponent(sessionId)}`;
  }

  function connect(): void {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    intentionalClose = false;
    const url = getWsUrl();
    console.log(`[WS] Connecting to ${url}`);

    ws = new WebSocket(url);

    ws.onopen = () => {
      connected = true;
      reconnectAttempts = 0;
      console.log('[WS] Connected');
      connectCallbacks.forEach((cb) => cb());
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WsServerEvent;

        // Respond to server pings with pong
        if (data.type === 'ping') {
          ws?.send(JSON.stringify({ type: 'pong' }));
          return;
        }

        messageCallbacks.forEach((cb) => cb(data));
      } catch (err) {
        console.error('[WS] Failed to parse message:', err);
      }
    };

    ws.onclose = (event) => {
      connected = false;
      const reason = event.reason || `Code ${event.code}`;
      console.log(`[WS] Disconnected: ${reason}`);
      disconnectCallbacks.forEach((cb) => cb(reason));

      if (!intentionalClose && reconnectAttempts < reconnectConfig.maxAttempts) {
        scheduleReconnect();
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
    };
  }

  function scheduleReconnect(): void {
    const delay = Math.min(
      reconnectConfig.initialDelay * Math.pow(2, reconnectAttempts),
      reconnectConfig.maxDelay,
    );
    reconnectAttempts++;
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts}/${reconnectConfig.maxAttempts})`);
    reconnectTimeout = setTimeout(connect, delay);
  }

  function disconnect(): void {
    intentionalClose = true;
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
    if (ws) {
      ws.close(1000, 'Client disconnect');
      ws = null;
    }
    connected = false;
  }

  function send(command: WsCommand): void {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.error('[WS] Cannot send — not connected');
      return;
    }
    ws.send(JSON.stringify(command));
  }

  function onMessage(callback: (event: WsServerEvent) => void): () => void {
    messageCallbacks.push(callback);
    return () => {
      const idx = messageCallbacks.indexOf(callback);
      if (idx !== -1) messageCallbacks.splice(idx, 1);
    };
  }

  function onConnect(callback: () => void): () => void {
    connectCallbacks.push(callback);
    return () => {
      const idx = connectCallbacks.indexOf(callback);
      if (idx !== -1) connectCallbacks.splice(idx, 1);
    };
  }

  function onDisconnect(callback: (reason: string) => void): () => void {
    disconnectCallbacks.push(callback);
    return () => {
      const idx = disconnectCallbacks.indexOf(callback);
      if (idx !== -1) disconnectCallbacks.splice(idx, 1);
    };
  }

  return {
    connect,
    disconnect,
    send,
    onMessage,
    onConnect,
    onDisconnect,
    get isConnected() {
      return connected;
    },
  };
}
