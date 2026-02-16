<script lang="ts">
	import type { ParsedMessage, CharacterInfo } from '$lib/narrative';
	import type { SceneImage as SceneImageType } from '$lib/types';
	import { formatMessageContent } from '$lib/narrative';
	import SceneImage from './SceneImage.svelte';
	import ImageGenerating from './ImageGenerating.svelte';

	let {
		message,
		characterInfo,
		isCurrent = false,
		sceneImage = undefined,
		isGenerating = false,
		onIllustrateTurn = undefined,
		logOffset = 0,
	}: {
		message: ParsedMessage;
		characterInfo?: CharacterInfo;
		isCurrent: boolean;
		sceneImage?: SceneImageType | undefined;
		isGenerating?: boolean;
		onIllustrateTurn?: ((turnIndex: number) => void) | undefined;
		logOffset?: number;
	} = $props();

	const formattedContent = $derived(formatMessageContent(message.content, message.messageType));
	const classSlug = $derived(characterInfo?.classSlug ?? 'adventurer');
	const turnNumber = $derived(logOffset + message.index + 1);

	function handleTurnClick(): void {
		onIllustrateTurn?.(message.index);
	}

	function handleTurnKeydown(e: KeyboardEvent): void {
		if (e.key === 'Enter') {
			onIllustrateTurn?.(message.index);
		}
	}
</script>

{#if isGenerating && !sceneImage}
	<ImageGenerating turnNumber={turnNumber} mode="specific" />
{/if}

{#if sceneImage}
	<SceneImage image={sceneImage} />
{/if}

{#if message.messageType === 'dm_narration'}
	<div class="dm-message" class:current-turn={isCurrent}>
		<span class="turn-number" role="button" tabindex="0" aria-label="Illustrate Turn {turnNumber}" onclick={handleTurnClick} onkeydown={handleTurnKeydown}>Turn {turnNumber}</span>
		<p>{@html formattedContent}</p>
	</div>
{:else if message.messageType === 'pc_dialogue'}
	<div class="pc-message {classSlug}" class:current-turn={isCurrent}>
		<span class="pc-attribution {classSlug}">
			<span class="turn-number" role="button" tabindex="0" aria-label="Illustrate Turn {turnNumber}" onclick={handleTurnClick} onkeydown={handleTurnKeydown}>Turn {turnNumber}</span>
			{' \u2014 '}
			{characterInfo?.name ?? message.agent}, the {characterInfo?.characterClass ?? 'Adventurer'}:
		</span>
		<p>{@html formattedContent}</p>
	</div>
{:else if message.messageType === 'sheet_update'}
	<div class="sheet-notification" class:current-turn={isCurrent}>
		<span class="turn-number" role="button" tabindex="0" aria-label="Illustrate Turn {turnNumber}" onclick={handleTurnClick} onkeydown={handleTurnKeydown}>Turn {turnNumber}</span>
		<p>{@html formattedContent}</p>
	</div>
{:else}
	<div class="system-message">
		<p>{@html formattedContent}</p>
	</div>
{/if}

<style>
	/* ===== DM Narration ===== */
	.dm-message {
		background: var(--bg-message);
		border-left: 4px solid var(--color-dm);
		padding: 12px var(--space-md);
		margin-bottom: var(--space-md);
		border-radius: 0 var(--border-radius-md) var(--border-radius-md) 0;
	}

	.dm-message p {
		font-family: var(--font-narrative);
		font-size: var(--text-dm);
		line-height: 1.6;
		color: var(--text-primary);
		font-style: italic;
		text-align: justify;
		margin: 0 0 0.6em 0;
	}

	.dm-message p:last-child {
		margin-bottom: 0;
	}

	/* ===== PC Dialogue ===== */
	.pc-message {
		background: var(--bg-message);
		padding: var(--space-md);
		margin-bottom: var(--space-md);
		border-radius: var(--border-radius-md);
		border-left: 3px solid var(--text-secondary);
	}

	.pc-message p {
		font-family: var(--font-narrative);
		font-size: var(--text-pc);
		line-height: 1.6;
		color: var(--text-primary);
		text-align: justify;
		margin: 0 0 0.6em 0;
	}

	.pc-message p:last-child {
		margin-bottom: 0;
	}

	/* PC Attribution - "Name, the Class:" format (Inter, not Lora per AC4) */
	.pc-attribution {
		display: block;
		font-family: var(--font-ui);
		font-size: var(--text-name);
		font-weight: 600;
		color: var(--text-secondary);
		margin-bottom: var(--space-xs);
	}

	/* Character-specific PC classes (border + attribution color) */
	.pc-message.fighter {
		border-left-color: var(--color-fighter);
	}
	.pc-message.rogue {
		border-left-color: var(--color-rogue);
	}
	.pc-message.wizard {
		border-left-color: var(--color-wizard);
	}
	.pc-message.cleric {
		border-left-color: var(--color-cleric);
	}

	.pc-attribution.fighter {
		color: var(--color-fighter);
	}
	.pc-attribution.rogue {
		color: var(--color-rogue);
	}
	.pc-attribution.wizard {
		color: var(--color-wizard);
	}
	.pc-attribution.cleric {
		color: var(--color-cleric);
	}

	/* ===== Sheet Notification ===== */
	.sheet-notification {
		background: rgba(232, 168, 73, 0.08);
		border-left: 3px solid var(--accent-warm);
		padding: var(--space-sm) var(--space-md);
		margin-bottom: var(--space-sm);
		border-radius: 0 6px 6px 0;
	}

	.sheet-notification p {
		font-family: var(--font-ui);
		font-size: 14px;
		line-height: 1.4;
		color: var(--accent-warm);
		margin: 0;
	}

	/* ===== System Messages ===== */
	.system-message {
		padding: var(--space-sm);
		margin-bottom: var(--space-sm);
	}

	.system-message p {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
		text-align: center;
		margin: 0;
	}

	/* ===== Turn Number ===== */
	.turn-number {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-secondary);
		opacity: 0.6;
		letter-spacing: 0.05em;
		cursor: pointer;
		transition: color var(--transition-fast), opacity var(--transition-fast);
	}

	/* Inline within PC attribution: spacing before the em dash */
	.pc-attribution .turn-number {
		margin-right: var(--space-xs);
	}

	/* Block label above DM/sheet messages */
	.dm-message .turn-number,
	.sheet-notification .turn-number {
		display: block;
		margin-bottom: var(--space-xs);
	}

	/* Hover hint: camera icon appears */
	.turn-number:hover {
		color: var(--accent-warm);
		opacity: 1;
	}

	.turn-number:hover::after {
		content: ' \1F4F7';
		font-size: 20px;
		vertical-align: middle;
	}

	/* ===== Current Turn Highlight ===== */
	.current-turn {
		animation: current-turn-highlight 3s ease-out;
	}

	@keyframes current-turn-highlight {
		0% {
			box-shadow: 0 0 15px rgba(232, 168, 73, 0.4);
		}
		100% {
			box-shadow: none;
		}
	}

	/* ===== Responsive ===== */
	@media (max-width: 768px) {
		.dm-message p {
			font-size: 17px;
		}
		.pc-message p {
			font-size: 16px;
		}
	}
</style>
