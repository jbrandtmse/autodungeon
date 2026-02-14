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

  // ===== Turn Number Display Tests (Story 17-1) =====

  it('displays turn number in DM narration messages', () => {
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({ messageType: 'dm_narration', index: 4 }),
        isCurrent: false,
      },
    });
    const turnEl = container.querySelector('.dm-message .turn-number');
    expect(turnEl).not.toBeNull();
    expect(turnEl!.textContent).toBe('Turn 5');
  });

  it('displays turn number in PC dialogue attribution', () => {
    const charInfo: CharacterInfo = {
      name: 'Lyra',
      characterClass: 'Wizard',
      classSlug: 'wizard',
    };
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({
          agent: 'wizard',
          content: 'I cast fireball!',
          messageType: 'pc_dialogue',
          index: 9,
        }),
        characterInfo: charInfo,
        isCurrent: false,
      },
    });
    const turnEl = container.querySelector('.pc-attribution .turn-number');
    expect(turnEl).not.toBeNull();
    expect(turnEl!.textContent).toBe('Turn 10');
    // The full attribution should contain turn number, em dash, and character name
    const attribution = container.querySelector('.pc-attribution');
    expect(attribution!.textContent).toContain('Turn 10');
    expect(attribution!.textContent).toContain('\u2014');
    expect(attribution!.textContent).toContain('Lyra');
    expect(attribution!.textContent).toContain('Wizard');
  });

  it('displays turn number in sheet update messages', () => {
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({
          agent: 'SHEET',
          content: 'HP updated',
          messageType: 'sheet_update',
          index: 14,
        }),
        isCurrent: false,
      },
    });
    const turnEl = container.querySelector('.sheet-notification .turn-number');
    expect(turnEl).not.toBeNull();
    expect(turnEl!.textContent).toBe('Turn 15');
  });

  it('does NOT display turn number in system messages', () => {
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({
          agent: 'system',
          content: 'Connected',
          messageType: 'system',
          index: 2,
        }),
        isCurrent: false,
      },
    });
    const turnEl = container.querySelector('.turn-number');
    expect(turnEl).toBeNull();
  });

  it('computes turn number as 1-based (index + 1)', () => {
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({ messageType: 'dm_narration', index: 0 }),
        isCurrent: false,
      },
    });
    const turnEl = container.querySelector('.turn-number');
    expect(turnEl).not.toBeNull();
    expect(turnEl!.textContent).toBe('Turn 1');
  });

  it('turn number span has role="button" and tabindex="0" for accessibility', () => {
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({ messageType: 'dm_narration', index: 6 }),
        isCurrent: false,
      },
    });
    const turnEl = container.querySelector('.turn-number');
    expect(turnEl).not.toBeNull();
    expect(turnEl!.getAttribute('role')).toBe('button');
    expect(turnEl!.getAttribute('tabindex')).toBe('0');
  });

  it('turn number span has aria-label for accessibility', () => {
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({ messageType: 'dm_narration', index: 41 }),
        isCurrent: false,
      },
    });
    const turnEl = container.querySelector('.turn-number');
    expect(turnEl).not.toBeNull();
    expect(turnEl!.getAttribute('aria-label')).toBe('Illustrate Turn 42');
  });

  it('PC attribution with turn number uses em dash separator', () => {
    const charInfo: CharacterInfo = {
      name: 'Thorgrim',
      characterClass: 'Fighter',
      classSlug: 'fighter',
    };
    const { container } = render(NarrativeMessage, {
      props: {
        message: makeParsedMessage({
          agent: 'fighter',
          content: 'I attack!',
          messageType: 'pc_dialogue',
          index: 41,
        }),
        characterInfo: charInfo,
        isCurrent: false,
      },
    });
    const attribution = container.querySelector('.pc-attribution');
    expect(attribution).not.toBeNull();
    // Should contain: "Turn 42 — Thorgrim, the Fighter:"
    const text = attribution!.textContent!;
    expect(text).toContain('Turn 42');
    expect(text).toContain('\u2014');
    expect(text).toContain('Thorgrim, the Fighter:');
  });
});
