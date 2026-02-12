import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';
import { connectionStatus, lastError, wsSend, sendCommand } from './connectionStore';

describe('connectionStore', () => {
  beforeEach(() => {
    connectionStatus.set('disconnected');
    lastError.set(null);
    wsSend.set(null);
  });

  it('connectionStatus defaults to disconnected', () => {
    expect(get(connectionStatus)).toBe('disconnected');
  });

  it('wsSend defaults to null and can be set and cleared', () => {
    expect(get(wsSend)).toBeNull();

    const mockSend = vi.fn();
    wsSend.set(mockSend);
    expect(get(wsSend)).toBe(mockSend);

    wsSend.set(null);
    expect(get(wsSend)).toBeNull();
  });

  it('sendCommand calls the stored send function with the command', () => {
    const mockSend = vi.fn();
    wsSend.set(mockSend);

    sendCommand({ type: 'next_turn' });
    expect(mockSend).toHaveBeenCalledWith({ type: 'next_turn' });
  });

  it('sendCommand calls console.warn when wsSend is null', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
    wsSend.set(null);

    sendCommand({ type: 'next_turn' });

    expect(warnSpy).toHaveBeenCalledWith('[WS] Cannot send command — not connected');
    warnSpy.mockRestore();
  });
});
