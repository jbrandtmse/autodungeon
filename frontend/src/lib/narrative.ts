/**
 * Log entry parsing, formatting, and sanitization for the narrative panel.
 *
 * Ports the Python `parse_log_entry()` from models.py and the formatting
 * logic from app.py (`format_pc_content`, `render_*_message_html`) to
 * TypeScript for the SvelteKit frontend.
 *
 * Processing pipeline (defense-in-depth):
 *   raw content -> sanitizeContent() -> formatDiceNotation() -> formatActionText() -> {@html}
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type MessageType = 'dm_narration' | 'pc_dialogue' | 'sheet_update' | 'system';

export interface ParsedMessage {
	agent: string;
	content: string;
	messageType: MessageType;
	index: number; // original index in ground_truth_log for keying
}

export interface CharacterInfo {
	name: string;
	characterClass: string;
	classSlug: string; // lowercase for CSS class matching
}

// ---------------------------------------------------------------------------
// Log Entry Parsing (mirrors models.py parse_log_entry)
// ---------------------------------------------------------------------------

/**
 * Parse a raw ground_truth_log entry into agent and content.
 *
 * Entry format: "[agent_name]: message content"
 *
 * Handles edge cases:
 * - Entry without brackets -> treat as DM narration
 * - Empty agent `[]` -> use fallback "unknown"
 * - Only parses first [agent] at start of string
 * - Strips duplicate agent prefix if LLM echoed the format
 */
export function parseLogEntry(entry: string): { agent: string; content: string } {
	if (entry.startsWith('[')) {
		const bracketEnd = entry.indexOf(']');
		if (bracketEnd > 0) {
			const agent = entry.substring(1, bracketEnd) || 'unknown';
			let content = entry.substring(bracketEnd + 1);
			// Strip leading ": " or ":" or whitespace
			content = content.replace(/^[:\s]+/, '');
			// Handle duplicate prefix: LLM sometimes echoes "[agent]:" in response
			const dupPrefix = `[${agent}]`;
			if (content.startsWith(dupPrefix)) {
				content = content.substring(dupPrefix.length).replace(/^[:\s]+/, '');
			}
			return { agent, content };
		}
	}
	// No brackets at start — treat as DM narration
	return { agent: 'dm', content: entry };
}

/**
 * Determine message type from agent name.
 */
export function getMessageType(agent: string): MessageType {
	const lower = agent.toLowerCase();
	if (lower === 'dm') return 'dm_narration';
	if (agent.toUpperCase() === 'SHEET') return 'sheet_update';
	if (lower === 'system') return 'system';
	return 'pc_dialogue';
}

/**
 * Parse an entire ground_truth_log into typed messages.
 */
export function parseGroundTruthLog(log: string[]): ParsedMessage[] {
	return log.map((entry, index) => {
		const { agent, content } = parseLogEntry(entry);
		return {
			agent,
			content,
			messageType: getMessageType(agent),
			index,
		};
	});
}

// ---------------------------------------------------------------------------
// Character Info Resolution (mirrors app.py get_character_info)
// ---------------------------------------------------------------------------

interface CharacterConfig {
	name: string;
	character_class: string;
}

/**
 * Resolve character display info from agent name and characters dict.
 *
 * Lookup order:
 * 1. Direct key lookup (lowercase agent key)
 * 2. Search by character name (log entries may use display names)
 * 3. Fallback: use agent name as-is with class "Adventurer"
 */
export function resolveCharacterInfo(
	agentName: string,
	characters: Record<string, CharacterConfig> = {},
): CharacterInfo {
	// Direct key lookup (lowercase)
	const lowerKey = agentName.toLowerCase();
	const directMatch = characters[lowerKey];
	if (directMatch) {
		return {
			name: directMatch.name,
			characterClass: directMatch.character_class,
			classSlug: directMatch.character_class.toLowerCase(),
		};
	}

	// Search by character name
	for (const char of Object.values(characters)) {
		if (char.name === agentName) {
			return {
				name: char.name,
				characterClass: char.character_class,
				classSlug: char.character_class.toLowerCase(),
			};
		}
	}

	// Fallback
	return {
		name: agentName,
		characterClass: 'Adventurer',
		classSlug: 'adventurer',
	};
}

// ---------------------------------------------------------------------------
// Sanitization (mirrors html.escape / escape_html from app.py)
// ---------------------------------------------------------------------------

/**
 * Escape HTML entities to prevent XSS. Must be called BEFORE any
 * formatting that injects HTML spans (dice, action text).
 */
export function sanitizeContent(content: string): string {
	return content
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#x27;');
}

// ---------------------------------------------------------------------------
// Content Formatting
// ---------------------------------------------------------------------------

/** Regex matching dice notation: 1d20, 2d6+3, d8, 3d6-1 */
const DICE_PATTERN = /\b(\d*d\d+(?:[+-]\d+)?)\b/gi;

/** Regex matching action text: *draws sword* */
const ACTION_PATTERN = /\*([^*]+)\*/g;

/**
 * Wrap dice notation in styled spans. Operates on already-sanitized content.
 */
export function formatDiceNotation(content: string): string {
	return content.replace(DICE_PATTERN, '<span class="dice-roll">$1</span>');
}

/**
 * Wrap *action text* in styled spans. Operates on already-sanitized content.
 * Mirrors Python ACTION_PATTERN.sub from app.py format_pc_content().
 */
export function formatActionText(content: string): string {
	return content.replace(ACTION_PATTERN, '<span class="action-text">$1</span>');
}

/**
 * Full formatting pipeline for message content.
 *
 * Applies sanitization first, then formatting based on message type:
 * - dm_narration: sanitize -> dice (entire text is italic via CSS)
 * - pc_dialogue: sanitize -> dice -> action text
 * - sheet_update: sanitize only (no dice/action formatting)
 * - system: sanitize only
 */
export function formatMessageContent(content: string, messageType: MessageType): string {
	const sanitized = sanitizeContent(content);

	switch (messageType) {
		case 'dm_narration':
			return formatDiceNotation(sanitized);
		case 'pc_dialogue':
			return formatActionText(formatDiceNotation(sanitized));
		case 'sheet_update':
		case 'system':
			return sanitized;
	}
}
