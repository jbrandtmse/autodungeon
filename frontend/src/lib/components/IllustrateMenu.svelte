<script lang="ts">
	import { generateCurrentImage, generateBestImage, generateTurnImage } from '$lib/api';
	import { startGeneration, startBestGeneration, generatingTurns, generatingBest, galleryOpen } from '$lib/stores/imageStore';
	import { connectionStatus } from '$lib/stores/connectionStore';

	interface Props {
		sessionId: string;
		totalTurns: number;
		onOpenGallery: () => void;
	}

	let { sessionId, totalTurns, onOpenGallery }: Props = $props();

	let open = $state(false);
	let showTurnDialog = $state(false);
	let turnInput = $state(1);
	let error = $state<string | null>(null);

	const notConnected = $derived($connectionStatus !== 'connected');

	/** Toggle the dropdown (for keyboard shortcut). */
	export function toggle(): void {
		if (notConnected) return;
		open = !open;
		if (!open) {
			showTurnDialog = false;
			error = null;
		}
	}

	function closeMenu(): void {
		open = false;
		showTurnDialog = false;
		error = null;
	}

	async function handleCurrentScene(): Promise<void> {
		if (!sessionId || totalTurns === 0) return;
		error = null;
		const turnIndex = totalTurns - 1;
		try {
			startGeneration(turnIndex);
			await generateCurrentImage(sessionId);
			closeMenu();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to generate image';
			generatingTurns.update((s) => {
				const next = new Set(s);
				next.delete(turnIndex);
				return next;
			});
		}
	}

	async function handleBestScene(): Promise<void> {
		if (!sessionId) return;
		error = null;
		try {
			startBestGeneration();
			await generateBestImage(sessionId);
			closeMenu();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to generate image';
			generatingBest.set(false);
		}
	}

	function handleTurnPrompt(): void {
		showTurnDialog = true;
		turnInput = 1;
		error = null;
	}

	async function handleTurnGenerate(): Promise<void> {
		if (!sessionId) return;
		error = null;
		const turnIndex = turnInput - 1;
		if (turnIndex < 0 || turnIndex >= totalTurns) {
			error = `Turn must be between 1 and ${totalTurns}`;
			return;
		}
		try {
			startGeneration(turnIndex);
			await generateTurnImage(sessionId, turnIndex);
			closeMenu();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to generate image';
			generatingTurns.update((s) => {
				const next = new Set(s);
				next.delete(turnIndex);
				return next;
			});
		}
	}

	function handleViewGallery(): void {
		closeMenu();
		onOpenGallery();
	}

	function handleCancelTurnDialog(): void {
		showTurnDialog = false;
		error = null;
	}

	function handleClickOutside(e: MouseEvent): void {
		const target = e.target as HTMLElement;
		if (!target.closest('.illustrate-menu-wrapper')) {
			closeMenu();
		}
	}

	function handleMenuKeydown(e: KeyboardEvent): void {
		if (e.key === 'Escape') {
			e.preventDefault();
			e.stopPropagation();
			closeMenu();
		}
	}
</script>

<svelte:window onclick={open ? handleClickOutside : undefined} />

<div class="illustrate-menu-wrapper">
	<button
		class="illustrate-btn"
		class:active={open}
		onclick={(e) => { e.stopPropagation(); toggle(); }}
		disabled={notConnected}
		aria-haspopup="true"
		aria-expanded={open}
		aria-label="Illustrate menu"
		title={notConnected ? 'Connect to a session to illustrate' : 'Generate scene illustrations'}
	>
		<svg class="illustrate-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
			<path d="M2 14l4-4 3 3 5-6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none" />
			<circle cx="11" cy="4" r="2" stroke="currentColor" stroke-width="1.2" fill="none" />
		</svg>
		Illustrate
	</button>

	{#if open}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			class="illustrate-dropdown"
			role="menu"
			tabindex="-1"
			onkeydown={handleMenuKeydown}
		>
			{#if !showTurnDialog}
				<button
					class="dropdown-item"
					role="menuitem"
					onclick={handleCurrentScene}
					disabled={totalTurns === 0}
				>
					Current Scene
				</button>
				<button
					class="dropdown-item"
					role="menuitem"
					onclick={handleBestScene}
					disabled={totalTurns === 0}
				>
					Best Scene
				</button>
				<button
					class="dropdown-item"
					role="menuitem"
					onclick={handleTurnPrompt}
					disabled={totalTurns === 0}
				>
					Turn #...
				</button>
				<div class="dropdown-separator" role="separator"></div>
				<button
					class="dropdown-item"
					role="menuitem"
					onclick={handleViewGallery}
				>
					View Gallery
				</button>
			{:else}
				<div class="turn-dialog">
					<label class="turn-label" for="turn-input">
						Turn number (1&ndash;{totalTurns}):
					</label>
					<input
						id="turn-input"
						class="turn-input"
						type="number"
						min="1"
						max={totalTurns}
						bind:value={turnInput}
						onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleTurnGenerate(); } }}
					/>
					<div class="turn-dialog-actions">
						<button class="turn-cancel-btn" onclick={handleCancelTurnDialog}>
							Cancel
						</button>
						<button class="turn-generate-btn" onclick={handleTurnGenerate}>
							Generate
						</button>
					</div>
				</div>
			{/if}

			{#if error}
				<p class="dropdown-error" role="alert">{error}</p>
			{/if}
		</div>
	{/if}
</div>

<style>
	.illustrate-menu-wrapper {
		position: relative;
		display: inline-flex;
	}

	.illustrate-btn {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		padding: 4px 10px;
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 13px;
		font-weight: 500;
		cursor: pointer;
		transition: color var(--transition-fast), border-color var(--transition-fast);
	}

	.illustrate-btn:hover:not(:disabled) {
		color: var(--accent-warm);
		border-color: var(--accent-warm);
	}

	.illustrate-btn.active {
		color: var(--accent-warm);
		border-color: var(--accent-warm);
	}

	.illustrate-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.illustrate-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.illustrate-icon {
		flex-shrink: 0;
	}

	/* Dropdown */
	.illustrate-dropdown {
		position: absolute;
		top: calc(100% + 4px);
		right: 0;
		min-width: 180px;
		background: var(--bg-secondary);
		border: 1px solid rgba(184, 168, 150, 0.15);
		border-radius: var(--border-radius-md);
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
		z-index: 100;
		padding: var(--space-xs) 0;
		animation: dropdown-in 0.1s ease;
	}

	@keyframes dropdown-in {
		from {
			opacity: 0;
			transform: translateY(-4px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.dropdown-item {
		display: block;
		width: 100%;
		padding: 8px var(--space-md);
		background: none;
		border: none;
		color: var(--text-primary);
		font-family: var(--font-ui);
		font-size: 13px;
		text-align: left;
		cursor: pointer;
		transition: background var(--transition-fast);
	}

	.dropdown-item:hover:not(:disabled) {
		background: var(--bg-message);
	}

	.dropdown-item:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.dropdown-item:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: -2px;
	}

	.dropdown-separator {
		height: 1px;
		background: rgba(184, 168, 150, 0.1);
		margin: var(--space-xs) 0;
	}

	/* Turn Dialog (inline) */
	.turn-dialog {
		padding: var(--space-sm) var(--space-md);
	}

	.turn-label {
		display: block;
		font-family: var(--font-ui);
		font-size: 12px;
		color: var(--text-secondary);
		margin-bottom: var(--space-xs);
	}

	.turn-input {
		width: 100%;
		padding: 6px 8px;
		background: var(--bg-primary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		color: var(--text-primary);
		font-family: var(--font-mono);
		font-size: 14px;
		margin-bottom: var(--space-sm);
	}

	.turn-input:focus {
		border-color: var(--accent-warm);
		outline: none;
	}

	.turn-dialog-actions {
		display: flex;
		gap: var(--space-xs);
		justify-content: flex-end;
	}

	.turn-cancel-btn,
	.turn-generate-btn {
		padding: 4px 12px;
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		border: none;
	}

	.turn-cancel-btn {
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid rgba(184, 168, 150, 0.2);
	}

	.turn-cancel-btn:hover {
		color: var(--text-primary);
		background: var(--bg-message);
	}

	.turn-generate-btn {
		background: var(--accent-warm);
		color: var(--bg-primary);
	}

	.turn-generate-btn:hover {
		background: var(--accent-warm-hover);
	}

	.dropdown-error {
		padding: var(--space-xs) var(--space-md);
		font-family: var(--font-ui);
		font-size: 12px;
		color: var(--color-error);
		margin: 0;
	}
</style>
