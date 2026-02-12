<script lang="ts">
	import { gameState, isPaused } from '$lib/stores';

	const humanActive = $derived($gameState?.human_active ?? false);
	const controlledCharacter = $derived($gameState?.controlled_character ?? null);
	const characters = $derived($gameState?.characters ?? {});

	const mode = $derived.by(() => {
		if ($isPaused) return 'paused' as const;
		if (humanActive && controlledCharacter) return 'play' as const;
		return 'watch' as const;
	});

	const controlledCharInfo = $derived.by(() => {
		if (!controlledCharacter || !characters) return null;
		// Try agent key lookup first, then fallback to name match
		for (const [key, char] of Object.entries(characters)) {
			if (key === controlledCharacter || char.name === controlledCharacter) {
				return char;
			}
		}
		return null;
	});

	const classSlug = $derived(
		controlledCharInfo?.character_class
			? controlledCharInfo.character_class.toLowerCase().replace(/[^a-z0-9-]/g, '')
			: ''
	);

	const displayName = $derived(controlledCharInfo?.name ?? controlledCharacter ?? '');
</script>

<div
	class="mode-indicator {mode} {mode === 'play' ? classSlug : ''}"
	aria-live="polite"
	role="status"
>
	{#if mode === 'paused'}
		<span class="indicator-dot pause-dot"></span>
		<span class="indicator-text">Paused</span>
	{:else if mode === 'play'}
		<span class="indicator-dot pulse-dot"></span>
		<span class="indicator-text">Playing as {displayName}</span>
	{:else}
		<span class="indicator-dot pulse-dot"></span>
		<span class="indicator-text">Watching</span>
	{/if}
</div>

<style>
	.mode-indicator {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 6px 14px;
		border-radius: 16px;
		font-family: var(--font-ui);
		font-size: 12px;
		font-weight: 500;
		letter-spacing: 0.02em;
		transition: all var(--transition-normal);
	}

	.indicator-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.indicator-text {
		line-height: 1;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	/* Watch mode: green */
	.mode-indicator.watch {
		background: rgba(107, 142, 107, 0.2);
		color: #6B8E6B;
	}
	.mode-indicator.watch .indicator-dot {
		background: #6B8E6B;
	}

	/* Play mode: amber default */
	.mode-indicator.play {
		background: rgba(232, 168, 73, 0.2);
		color: var(--accent-warm);
	}
	.mode-indicator.play .indicator-dot {
		background: var(--accent-warm);
	}

	/* Play mode: character-specific colors */
	.mode-indicator.play.fighter {
		background: rgba(196, 92, 74, 0.2);
		color: var(--color-fighter);
	}
	.mode-indicator.play.fighter .indicator-dot {
		background: var(--color-fighter);
	}
	.mode-indicator.play.rogue {
		background: rgba(107, 142, 107, 0.2);
		color: var(--color-rogue);
	}
	.mode-indicator.play.rogue .indicator-dot {
		background: var(--color-rogue);
	}
	.mode-indicator.play.wizard {
		background: rgba(123, 104, 184, 0.2);
		color: var(--color-wizard);
	}
	.mode-indicator.play.wizard .indicator-dot {
		background: var(--color-wizard);
	}
	.mode-indicator.play.cleric {
		background: rgba(74, 144, 164, 0.2);
		color: var(--color-cleric);
	}
	.mode-indicator.play.cleric .indicator-dot {
		background: var(--color-cleric);
	}

	/* Paused: amber static */
	.mode-indicator.paused {
		background: rgba(232, 168, 73, 0.2);
		color: var(--accent-warm);
	}
	.mode-indicator.paused .indicator-dot {
		background: var(--accent-warm);
	}

	/* Pulse animation for active modes */
	.pulse-dot {
		animation: mode-pulse 2s ease-in-out infinite;
	}

	.pause-dot {
		animation: none;
	}

	@keyframes mode-pulse {
		0%, 100% {
			opacity: 1;
			transform: scale(1);
		}
		50% {
			opacity: 0.5;
			transform: scale(0.85);
		}
	}
</style>
