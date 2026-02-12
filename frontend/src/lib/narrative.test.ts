import { describe, it, expect } from 'vitest';
import {
  parseLogEntry,
  getMessageType,
  parseGroundTruthLog,
  resolveCharacterInfo,
  sanitizeContent,
  formatDiceNotation,
  formatActionText,
  formatMessageContent,
} from './narrative';

describe('parseLogEntry', () => {
  it('extracts agent and content from standard format "[agent]: content"', () => {
    const result = parseLogEntry('[dm]: The door opens');
    expect(result.agent).toBe('dm');
    expect(result.content).toBe('The door opens');
  });

  it('handles entries without brackets — fallback to dm', () => {
    const result = parseLogEntry('A mysterious sound echoes');
    expect(result.agent).toBe('dm');
    expect(result.content).toBe('A mysterious sound echoes');
  });

  it('handles empty agent "[]" — uses "unknown"', () => {
    const result = parseLogEntry('[]: Some message');
    expect(result.agent).toBe('unknown');
    expect(result.content).toBe('Some message');
  });

  it('strips duplicate agent prefix when LLM echoes format', () => {
    const result = parseLogEntry('[fighter]: [fighter]: I attack!');
    expect(result.agent).toBe('fighter');
    expect(result.content).toBe('I attack!');
  });

  it('handles whitespace after closing bracket', () => {
    const result = parseLogEntry('[rogue]:   sneaks around');
    expect(result.agent).toBe('rogue');
    expect(result.content).toBe('sneaks around');
  });
});

describe('getMessageType', () => {
  it('returns dm_narration for dm', () => {
    expect(getMessageType('dm')).toBe('dm_narration');
  });

  it('returns dm_narration for DM (case-insensitive)', () => {
    expect(getMessageType('DM')).toBe('dm_narration');
  });

  it('returns sheet_update for SHEET', () => {
    expect(getMessageType('SHEET')).toBe('sheet_update');
  });

  it('returns system for system', () => {
    expect(getMessageType('system')).toBe('system');
  });

  it('returns pc_dialogue for any other agent', () => {
    expect(getMessageType('fighter')).toBe('pc_dialogue');
    expect(getMessageType('rogue')).toBe('pc_dialogue');
    expect(getMessageType('wizard')).toBe('pc_dialogue');
  });
});

describe('parseGroundTruthLog', () => {
  it('converts an array of raw entries into ParsedMessage[]', () => {
    const log = [
      '[dm]: The quest begins',
      '[fighter]: I draw my sword',
      '[SHEET]: Character stats update',
    ];
    const messages = parseGroundTruthLog(log);
    expect(messages).toHaveLength(3);
    expect(messages[0]).toMatchObject({
      agent: 'dm',
      content: 'The quest begins',
      messageType: 'dm_narration',
      index: 0,
    });
    expect(messages[1]).toMatchObject({
      agent: 'fighter',
      content: 'I draw my sword',
      messageType: 'pc_dialogue',
      index: 1,
    });
    expect(messages[2]).toMatchObject({
      agent: 'SHEET',
      content: 'Character stats update',
      messageType: 'sheet_update',
      index: 2,
    });
  });

  it('returns empty array for empty log', () => {
    expect(parseGroundTruthLog([])).toEqual([]);
  });
});

describe('resolveCharacterInfo', () => {
  const characters = {
    fighter: { name: 'Thorin', character_class: 'Fighter' },
    rogue: { name: 'Shadowmere', character_class: 'Rogue' },
  };

  it('finds character by direct key lookup', () => {
    const info = resolveCharacterInfo('fighter', characters);
    expect(info.name).toBe('Thorin');
    expect(info.characterClass).toBe('Fighter');
    expect(info.classSlug).toBe('fighter');
  });

  it('finds character by name search', () => {
    const info = resolveCharacterInfo('Shadowmere', characters);
    expect(info.name).toBe('Shadowmere');
    expect(info.characterClass).toBe('Rogue');
    expect(info.classSlug).toBe('rogue');
  });

  it('returns fallback for unknown agents', () => {
    const info = resolveCharacterInfo('unknown_agent', characters);
    expect(info.name).toBe('unknown_agent');
    expect(info.characterClass).toBe('Adventurer');
    expect(info.classSlug).toBe('adventurer');
  });

  it('returns fallback when characters dict is empty', () => {
    const info = resolveCharacterInfo('fighter', {});
    expect(info.name).toBe('fighter');
    expect(info.characterClass).toBe('Adventurer');
  });
});

describe('sanitizeContent', () => {
  it('escapes <, >, &, double quote, and single quote', () => {
    const result = sanitizeContent('<script>alert("xss")&test\'</script>');
    expect(result).toBe('&lt;script&gt;alert(&quot;xss&quot;)&amp;test&#x27;&lt;/script&gt;');
  });

  it('returns unchanged string when no special characters present', () => {
    expect(sanitizeContent('Hello world')).toBe('Hello world');
  });
});

describe('formatDiceNotation', () => {
  it('wraps dice notation in span tags', () => {
    expect(formatDiceNotation('Roll 1d20')).toBe(
      'Roll <span class="dice-roll">1d20</span>',
    );
  });

  it('handles dice with modifiers', () => {
    expect(formatDiceNotation('Damage: 2d6+3')).toBe(
      'Damage: <span class="dice-roll">2d6+3</span>',
    );
  });

  it('handles multiple dice notations', () => {
    const result = formatDiceNotation('Roll 1d20 and 2d6');
    expect(result).toContain('<span class="dice-roll">1d20</span>');
    expect(result).toContain('<span class="dice-roll">2d6</span>');
  });
});

describe('formatActionText', () => {
  it('wraps asterisk-enclosed text in action-text spans', () => {
    expect(formatActionText('*draws sword*')).toBe(
      '<span class="action-text">draws sword</span>',
    );
  });

  it('handles multiple action texts', () => {
    const result = formatActionText('*draws sword* and *charges*');
    expect(result).toContain('<span class="action-text">draws sword</span>');
    expect(result).toContain('<span class="action-text">charges</span>');
  });
});

describe('formatMessageContent', () => {
  it('dm_narration: applies sanitize then dice formatting', () => {
    const result = formatMessageContent('Roll 1d20 to open', 'dm_narration');
    expect(result).toContain('<span class="dice-roll">1d20</span>');
    // Action text should NOT be applied
    expect(result).not.toContain('action-text');
  });

  it('pc_dialogue: applies sanitize, dice, then action text', () => {
    const result = formatMessageContent('*attacks* with 1d20', 'pc_dialogue');
    expect(result).toContain('<span class="dice-roll">1d20</span>');
    expect(result).toContain('<span class="action-text">attacks</span>');
  });

  it('sheet_update: applies sanitize only', () => {
    const result = formatMessageContent('HP: 20/30 & 1d20', 'sheet_update');
    expect(result).toContain('&amp;');
    expect(result).not.toContain('<span class="dice-roll">');
  });

  it('system: applies sanitize only', () => {
    const result = formatMessageContent('Error: <failed>', 'system');
    expect(result).toContain('&lt;failed&gt;');
    expect(result).not.toContain('<span class="dice-roll">');
  });

  it('sanitizes before formatting (XSS prevention)', () => {
    const result = formatMessageContent('<script>alert("xss")</script> Roll 1d20', 'dm_narration');
    expect(result).not.toContain('<script>');
    expect(result).toContain('&lt;script&gt;');
    expect(result).toContain('<span class="dice-roll">1d20</span>');
  });
});
