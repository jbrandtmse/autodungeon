import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import NarrativeMessage from './NarrativeMessage.svelte';
import type { ParsedMessage, CharacterInfo } from '$lib/narrative';

function makeParsedMessage(overrides: Partial<ParsedMessage> = {}): ParsedMessage {
  return {
    agent: 'dm',
    content: 'The adventure begins',
    messageType: 'dm_narration',
    index: 0,
    ...overrides,
  };
}

describe('NarrativeMessage', () => {
  it('renders DM narration with .dm-message CSS class', () => {
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({ messageType: 'dm_narration' }),
        isCurrent: false,
      },
    });
    const dmEl = container.querySelector('.dm-message');
    expect(dmEl).not.toBeNull();
  });

  it('renders PC dialogue with .pc-message CSS class and character attribution', () => {
    const charInfo: CharacterInfo = {
      name: 'Thorin',
      characterClass: 'Fighter',
      classSlug: 'fighter',
    };
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({
          agent: 'fighter',
          content: 'I charge!',
          messageType: 'pc_dialogue',
        }),
        characterInfo: charInfo,
        isCurrent: false,
      },
    });
    const pcEl = container.querySelector('.pc-message');
    expect(pcEl).not.toBeNull();
    // Check for attribution text
    const attribution = container.querySelector('.pc-attribution');
    expect(attribution).not.toBeNull();
    expect(attribution!.textContent).toContain('Thorin');
    expect(attribution!.textContent).toContain('Fighter');
  });

  it('renders sheet update with .sheet-notification CSS class', () => {
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({
          agent: 'SHEET',
          content: 'Character updated',
          messageType: 'sheet_update',
        }),
        isCurrent: false,
      },
    });
    const sheetEl = container.querySelector('.sheet-notification');
    expect(sheetEl).not.toBeNull();
  });

  it('renders system message with .system-message CSS class', () => {
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({
          agent: 'system',
          content: 'Session started',
          messageType: 'system',
        }),
        isCurrent: false,
      },
    });
    const sysEl = container.querySelector('.system-message');
    expect(sysEl).not.toBeNull();
  });

  it('applies current-turn CSS class when isCurrent is true', () => {
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({ messageType: 'dm_narration' }),
        isCurrent: true,
      },
    });
    const dmEl = container.querySelector('.dm-message');
    expect(dmEl).not.toBeNull();
    expect(dmEl!.classList.contains('current-turn')).toBe(true);
  });
});
