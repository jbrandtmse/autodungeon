import { derived } from 'svelte/store';
import { gameState } from './gameStore';
import { parseGroundTruthLog, type ParsedMessage } from '$lib/narrative';

/**
 * Derived store: parsed messages from ground truth log.
 * Re-computes whenever gameState changes.
 */
export const narrativeMessages = derived<typeof gameState, ParsedMessage[]>(gameState, ($gs) => {
	if (!$gs) return [];
	return parseGroundTruthLog($gs.ground_truth_log);
});

/**
 * Derived store: display limit from game config.
 * Falls back to 50 if not configured.
 */
export const displayLimit = derived<typeof gameState, number>(gameState, ($gs) => {
	return $gs?.game_config?.narrative_display_limit ?? 50;
});
