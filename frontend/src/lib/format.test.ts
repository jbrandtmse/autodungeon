import { describe, it, expect } from 'vitest';
import { toRomanNumeral, formatSessionDate } from './format';

describe('toRomanNumeral', () => {
  it('converts 1 to I', () => {
    expect(toRomanNumeral(1)).toBe('I');
  });

  it('converts 4 to IV', () => {
    expect(toRomanNumeral(4)).toBe('IV');
  });

  it('converts 9 to IX', () => {
    expect(toRomanNumeral(9)).toBe('IX');
  });

  it('converts 42 to XLII', () => {
    expect(toRomanNumeral(42)).toBe('XLII');
  });

  it('converts 2024 to MMXXIV', () => {
    expect(toRomanNumeral(2024)).toBe('MMXXIV');
  });

  it('converts 3999 to MMMCMXCIX', () => {
    expect(toRomanNumeral(3999)).toBe('MMMCMXCIX');
  });

  it('returns decimal string for 0', () => {
    expect(toRomanNumeral(0)).toBe('0');
  });

  it('returns decimal string for 4000', () => {
    expect(toRomanNumeral(4000)).toBe('4000');
  });

  it('returns decimal string for negative numbers', () => {
    expect(toRomanNumeral(-1)).toBe('-1');
  });

  it('returns decimal string for Infinity', () => {
    expect(toRomanNumeral(Infinity)).toBe('Infinity');
  });
});

describe('formatSessionDate', () => {
  it('formats a valid ISO timestamp as "MMM DD, YYYY"', () => {
    const result = formatSessionDate('2026-02-11T12:00:00Z');
    // The exact format depends on locale but should contain these components
    expect(result).toMatch(/Feb\s+11,\s+2026/);
  });

  it('formats another valid date correctly', () => {
    // Use a mid-day timestamp to avoid timezone boundary issues
    const result = formatSessionDate('2026-06-15T12:00:00Z');
    expect(result).toMatch(/Jun\s+15,\s+2026/);
  });

  it('returns "Unknown date" for invalid timestamps', () => {
    expect(formatSessionDate('not-a-date')).toBe('Unknown date');
  });

  it('returns "Unknown date" for empty string', () => {
    expect(formatSessionDate('')).toBe('Unknown date');
  });
});
