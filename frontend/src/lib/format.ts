/**
 * Formatting utilities for the session management UI.
 *
 * Provides Roman numeral conversion and date formatting for session cards.
 */

const ROMAN_VALUES = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1];
const ROMAN_SYMBOLS = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I'];

/**
 * Convert a positive integer to a Roman numeral string.
 *
 * Supports values 1 through 3999. Values outside this range are returned
 * as plain decimal strings.
 */
export function toRomanNumeral(num: number): string {
	if (num < 1 || num > 3999 || !Number.isFinite(num)) return String(num);

	let remaining = Math.floor(num);
	let result = '';
	for (let i = 0; i < ROMAN_VALUES.length; i++) {
		while (remaining >= ROMAN_VALUES[i]) {
			result += ROMAN_SYMBOLS[i];
			remaining -= ROMAN_VALUES[i];
		}
	}
	return result;
}

/**
 * Format an ISO timestamp as "MMM DD, YYYY" (e.g., "Feb 11, 2026").
 *
 * Returns "Unknown date" if the timestamp is invalid.
 */
export function formatSessionDate(isoTimestamp: string): string {
	try {
		const date = new Date(isoTimestamp);
		if (isNaN(date.getTime())) return 'Unknown date';
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: 'numeric',
		});
	} catch {
		return 'Unknown date';
	}
}
