import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import CharacterCard from './CharacterCard.svelte';

// Mock the stores barrel export used by CharacterCard
vi.mock('$lib/stores', () => {
  const gameState = writable(null);
  const isThinking = writable(false);
  const connectionStatus = writable('connected');
  const sendCommand = vi.fn();
  const uiState = writable({
    sidebarOpen: true,
    selectedCharacter: null,
    uiMode: 'watch',
    autoScroll: true,
    settingsOpen: false,
    characterSheetName: null,
    comparisonForkId: null,
  });
  return {
    gameState,
    isThinking,
    connectionStatus,
    sendCommand,
    uiState,
  };
});

describe('CharacterCard', () => {
  it('renders character name and class', () => {
    const { container } = render(CharacterCard, {
      props: {
        agentKey: 'fighter',
        name: 'Thorin',
        characterClass: 'Fighter',
        classSlug: 'fighter',
        isControlled: false,
        isGenerating: false,
      },
    });
    const nameEl = container.querySelector('.char-name');
    expect(nameEl).not.toBeNull();
    expect(nameEl!.textContent).toContain('Thorin');

    const classEl = container.querySelector('.char-class');
    expect(classEl).not.toBeNull();
    expect(classEl!.textContent).toContain('Fighter');
  });

  it('status badge shows "You" when isControlled is true', () => {
    const { container } = render(CharacterCard, {
      props: {
        agentKey: 'fighter',
        name: 'Thorin',
        characterClass: 'Fighter',
        classSlug: 'fighter',
        isControlled: true,
        isGenerating: false,
      },
    });
    const badge = container.querySelector('.status-badge');
    expect(badge).not.toBeNull();
    expect(badge!.textContent?.trim()).toBe('You');
  });

  it('status badge shows "AI" when not controlled and not generating', () => {
    const { container } = render(CharacterCard, {
      props: {
        agentKey: 'fighter',
        name: 'Thorin',
        characterClass: 'Fighter',
        classSlug: 'fighter',
        isControlled: false,
        isGenerating: false,
      },
    });
    const badge = container.querySelector('.status-badge');
    expect(badge).not.toBeNull();
    expect(badge!.textContent?.trim()).toBe('AI');
  });

  it('HP bar renders when hp prop is provided with correct percentage', () => {
    const { container } = render(CharacterCard, {
      props: {
        agentKey: 'fighter',
        name: 'Thorin',
        characterClass: 'Fighter',
        classSlug: 'fighter',
        isControlled: false,
        isGenerating: false,
        hp: { current: 15, max: 30, temp: 0 },
      },
    });
    const hpContainer = container.querySelector('.hp-bar-container');
    expect(hpContainer).not.toBeNull();

    const hpFill = container.querySelector('.hp-bar-fill');
    expect(hpFill).not.toBeNull();
    // 15/30 = 50%
    expect(hpFill!.getAttribute('style')).toContain('width: 50%');

    const hpText = container.querySelector('.hp-text');
    expect(hpText).not.toBeNull();
    expect(hpText!.textContent).toContain('15/30 HP');
  });

  it('HP bar does not render when hp prop is not provided', () => {
    const { container } = render(CharacterCard, {
      props: {
        agentKey: 'fighter',
        name: 'Thorin',
        characterClass: 'Fighter',
        classSlug: 'fighter',
        isControlled: false,
        isGenerating: false,
      },
    });
    const hpContainer = container.querySelector('.hp-bar-container');
    expect(hpContainer).toBeNull();
  });
});
