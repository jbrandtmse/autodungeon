<script lang="ts">
	import { tick, untrack } from 'svelte';
	import NarrativeMessage from './NarrativeMessage.svelte';
	import ThinkingIndicator from './ThinkingIndicator.svelte';
	import IllustrateMenu from './IllustrateMenu.svelte';
	import {
		resolveCharacterInfo,
		type ParsedMessage,
		type CharacterInfo,
	} from '$lib/narrative';
	import type { SceneImage } from '$lib/types';
	import { gameState, isAutopilotRunning, isThinking, thinkingAgent } from '$lib/stores/gameStore';
	import { narrativeMessages, displayLimit as displayLimitStore } from '$lib/stores/narrativeStore';
	import { images, generatingTurns, galleryOpen, startGeneration } from '$lib/stores/imageStore';
	import { generateTurnImage } from '$lib/api';
	import { uiState } from '$lib/stores/uiStore';

	let scrollContainer: HTMLElement;
	let displayOffset = $state(0);
	let showScrollButton = $state(false);

	// Use derived stores from narrativeStore (single source of truth for parsing)
	const parsedMessages = $derived($narrativeMessages);
	const displayLimit = $derived($displayLimitStore);
	// Characters dict may be present on the state object from the backend
	// but is not defined in the base GameState type yet. Cast safely via unknown.
	const characters = $derived(
		(($gameState as unknown as Record<string, unknown> | null)?.characters as
			| Record<string, { name: string; character_class: string }>
			| undefined) ?? {},
	);
	const currentTurnAgent = $derived($gameState?.current_turn ?? '');
	const sessionId = $derived($gameState?.session_id ?? '');

	// Paginated view
	const totalToShow = $derived(displayLimit + displayOffset);
	const startIndex = $derived(Math.max(0, parsedMessages.length - totalToShow));
	const visibleMessages = $derived(parsedMessages.slice(startIndex));
	const hiddenCount = $derived(startIndex);

	// Resolve character info for each visible message
	function getCharInfo(msg: ParsedMessage): CharacterInfo | undefined {
		if (msg.messageType !== 'pc_dialogue') return undefined;
		return resolveCharacterInfo(msg.agent, characters);
	}

	// Image generation: derive per-turn image lookup map
	const imagesByTurn = $derived(
		$images.reduce<Record<number, SceneImage>>((map, img) => {
			map[img.turn_number] = img;
			return map;
		}, {}),
	);
	const currentGenerating = $derived($generatingTurns);

	// Whether image generation is enabled via game config
	const imageEnabled = $derived(
		$gameState?.game_config?.image_generation_enabled ?? false,
	);

	// IllustrateMenu ref for keyboard shortcut toggling
	let illustrateMenuRef: IllustrateMenu | undefined = $state();

	/** Toggle the Illustrate dropdown menu (for keyboard shortcut). */
	export function toggleIllustrate(): void {
		illustrateMenuRef?.toggle();
	}

	async function handleIllustrateTurn(turnIndex: number): Promise<void> {
		if (!sessionId) return;
		try {
			startGeneration(turnIndex);
			await generateTurnImage(sessionId, turnIndex);
		} catch (e) {
			console.error('[Narrative] Failed to generate image:', e);
			generatingTurns.update((s) => {
				const next = new Set(s);
				next.delete(turnIndex);
				return next;
			});
		}
	}

	function handleOpenGallery(): void {
		galleryOpen.set(true);
	}

	// Thinking indicator state — use isThinking store (which is set to false
	// on turn_update arrival, then back to true) combined with autopilot
	// running, so the indicator disappears briefly when a new message arrives
	// per AC10.
	const showThinking = $derived($isAutopilotRunning && $isThinking);
	const thinkingAgentName = $derived($thinkingAgent || 'dm');
	const thinkingCharInfo = $derived(
		$thinkingAgent ? resolveCharacterInfo($thinkingAgent, characters) : undefined,
	);

	// Session title formatting
	const sessionTitle = $derived(formatSessionTitle(sessionId));

	function formatSessionTitle(id: string): string {
		if (!id) return 'Loading...';
		// If the session id contains a number, format as roman numeral
		const numMatch = id.match(/(\d+)/);
		if (numMatch) {
			const num = parseInt(numMatch[1], 10);
			const roman = toRomanNumeral(num);
			return `Session ${roman}`;
		}
		return `Session: ${id}`;
	}

	function toRomanNumeral(num: number): string {
		if (num <= 0 || num > 3999) return String(num);
		const vals = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1];
		const syms = ['M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I'];
		let result = '';
		let remaining = num;
		for (let i = 0; i < vals.length; i++) {
			while (remaining >= vals[i]) {
				result += syms[i];
				remaining -= vals[i];
			}
		}
		return result;
	}

	// Auto-scroll on new messages
	let prevMessageCount = $state(0);
	// Guard to suppress scroll-event handling during programmatic scrolls
	let isProgrammaticScroll = false;

	$effect(() => {
		const count = parsedMessages.length;
		// Use untrack for autoScroll so this effect only re-triggers on message
		// count changes, NOT when handleScroll toggles autoScroll (which would
		// create a scroll -> effect -> scroll feedback loop during smooth scrolling).
		const shouldAutoScroll = untrack(() => $uiState.autoScroll);
		if (count > prevMessageCount && shouldAutoScroll && scrollContainer) {
			isProgrammaticScroll = true;
			tick().then(() => {
				scrollContainer?.scrollTo({
					top: scrollContainer.scrollHeight,
					behavior: 'smooth',
				});
				// Release the guard after smooth scroll has had time to start.
				// The scroll event may still fire a few times but at this point
				// the user is at the bottom so autoScroll stays true.
				setTimeout(() => {
					isProgrammaticScroll = false;
				}, 100);
			});
		}
		prevMessageCount = count;
	});

	// Scroll event handler (passive — see onscroll binding)
	function handleScroll() {
		if (!scrollContainer || isProgrammaticScroll) return;
		const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
		const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
		const isAtBottom = distanceFromBottom < 100;

		uiState.update((s) => ({ ...s, autoScroll: isAtBottom }));
		showScrollButton = !isAtBottom;
	}

	async function loadEarlierMessages() {
		const oldHeight = scrollContainer?.scrollHeight ?? 0;
		const oldTop = scrollContainer?.scrollTop ?? 0;

		displayOffset += displayLimit;

		await tick();

		if (scrollContainer) {
			const newHeight = scrollContainer.scrollHeight;
			scrollContainer.scrollTop = newHeight - oldHeight + oldTop;
		}
	}

	function resumeAutoScroll() {
		uiState.update((s) => ({ ...s, autoScroll: true }));
		showScrollButton = false;
		if (scrollContainer) {
			isProgrammaticScroll = true;
			scrollContainer.scrollTo({
				top: scrollContainer.scrollHeight,
				behavior: 'smooth',
			});
			setTimeout(() => {
				isProgrammaticScroll = false;
			}, 100);
		}
	}
</script>

<div class="narrative-panel">
	<header class="session-header">
		<h2 class="session-title">{sessionTitle}</h2>
		{#if imageEnabled}
			<IllustrateMenu
				bind:this={illustrateMenuRef}
				{sessionId}
				totalTurns={parsedMessages.length}
				onOpenGallery={handleOpenGallery}
			/>
		{/if}
	</header>

	<div
		class="narrative-scroll"
		bind:this={scrollContainer}
		onscroll={handleScroll}
	>
		{#if hiddenCount > 0}
			<button class="load-earlier-btn" onclick={loadEarlierMessages}>
				Load earlier messages ({hiddenCount} hidden)
			</button>
		{/if}

		{#if visibleMessages.length === 0}
			<div class="empty-state">
				<p class="empty-title">The adventure awaits...</p>
				<p class="empty-subtitle">Start a new game to begin.</p>
			</div>
		{:else}
			{#each visibleMessages as msg (msg.index)}
				<NarrativeMessage
					message={msg}
					characterInfo={getCharInfo(msg)}
					isCurrent={msg.index === parsedMessages.length - 1}
					sceneImage={imagesByTurn[msg.index]}
					isGenerating={currentGenerating.has(msg.index)}
					onIllustrateTurn={handleIllustrateTurn}
				/>
			{/each}
		{/if}

		<ThinkingIndicator
			agentName={thinkingAgentName}
			agentClass={thinkingCharInfo?.classSlug}
			visible={showThinking}
		/>
	</div>

	{#if showScrollButton}
		<button class="resume-scroll-btn" onclick={resumeAutoScroll}>
			&#8595; Resume auto-scroll
		</button>
	{/if}
</div>

<style>
	.narrative-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
		max-width: var(--max-content-width);
		margin: 0 auto;
		position: relative;
	}

	/* Session Header */
	.session-header {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-md);
		padding: var(--space-sm) var(--space-md);
		border-bottom: 1px solid var(--bg-secondary);
		margin-bottom: 0;
		flex-shrink: 0;
		position: relative;
	}

	.session-title {
		font-family: var(--font-narrative);
		font-size: 24px;
		font-weight: 600;
		color: var(--color-dm);
		margin: 0;
	}

	/* Scrollable area */
	.narrative-scroll {
		flex: 1;
		overflow-y: auto;
		padding: var(--space-md) var(--space-lg);
		scroll-behavior: smooth;
	}

	/* Load Earlier Messages */
	.load-earlier-btn {
		display: block;
		width: 100%;
		padding: var(--space-sm);
		margin-bottom: var(--space-md);
		background-color: var(--bg-secondary);
		color: var(--text-secondary);
		border: none;
		border-radius: var(--border-radius-sm);
		cursor: pointer;
		font-family: var(--font-ui);
		font-size: 0.85rem;
		transition: all var(--transition-fast);
	}

	.load-earlier-btn:hover {
		background-color: var(--bg-message);
		color: var(--text-primary);
	}

	/* Empty State */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 300px;
		text-align: center;
	}

	.empty-title {
		font-family: var(--font-narrative);
		font-style: italic;
		color: var(--accent-warm);
		font-size: 1.25rem;
		margin-bottom: var(--space-sm);
	}

	.empty-subtitle {
		color: var(--text-secondary);
		font-size: 0.9rem;
	}

	/* Resume Auto-Scroll */
	.resume-scroll-btn {
		position: absolute;
		bottom: var(--space-md);
		right: var(--space-md);
		padding: var(--space-xs) var(--space-md);
		background-color: var(--accent-warm);
		color: var(--bg-primary);
		border: none;
		border-radius: var(--border-radius-md);
		cursor: pointer;
		font-family: var(--font-ui);
		font-size: 0.85rem;
		font-weight: 500;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
		transition: all var(--transition-fast);
		z-index: 10;
	}

	.resume-scroll-btn:hover {
		background-color: var(--accent-warm-hover);
	}

	/* ===== Responsive ===== */

	/* Tablet (768px - 1024px) */
	@media (max-width: 1024px) {
		.narrative-panel {
			max-width: 100%;
		}
		.narrative-scroll {
			padding: var(--space-md);
		}
	}

	/* Mobile (< 768px) */
	@media (max-width: 768px) {
		.narrative-scroll {
			padding: var(--space-sm);
		}
		.session-title {
			font-size: 20px;
		}
	}
</style>
