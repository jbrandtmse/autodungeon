<script lang="ts">
	import {
		gameState,
		awaitingInput,
		awaitingInputCharacter,
		connectionStatus,
		sendCommand,
	} from '$lib/stores';

	const humanActive = $derived($gameState?.human_active ?? false);
	const controlledCharacter = $derived($gameState?.controlled_character ?? null);
	const characters = $derived($gameState?.characters ?? {});
	const notConnected = $derived($connectionStatus !== 'connected');

	const controlledCharInfo = $derived.by(() => {
		if (!controlledCharacter || !characters) return null;
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

	const isAwaitingMyInput = $derived(
		$awaitingInput && controlledCharacter !== null &&
		($awaitingInputCharacter === controlledCharacter ||
		 $awaitingInputCharacter === controlledCharInfo?.name)
	);

	let actionText = $state('');
	let nudgeText = $state('');
	let showNudgeConfirmation = $state(false);
	let nudgeTimer: ReturnType<typeof setTimeout> | null = null;
	let actionTextarea: HTMLTextAreaElement | undefined = $state(undefined);

	// Auto-focus textarea when awaiting input
	$effect(() => {
		if (isAwaitingMyInput && actionTextarea) {
			actionTextarea.focus();
		}
	});

	// Cleanup nudge timer on destroy
	$effect(() => {
		return () => {
			if (nudgeTimer) {
				clearTimeout(nudgeTimer);
				nudgeTimer = null;
			}
		};
	});

	function handleSubmitAction(): void {
		const trimmed = actionText.trim();
		if (!trimmed) return;
		sendCommand({ type: 'submit_action', content: trimmed });
		actionText = '';
	}

	function handleActionKeydown(event: KeyboardEvent): void {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSubmitAction();
		}
	}

	function handleSubmitNudge(): void {
		const trimmed = nudgeText.trim();
		if (!trimmed) return;
		sendCommand({ type: 'nudge', content: trimmed });
		nudgeText = '';
		showNudgeConfirmation = true;
		if (nudgeTimer) clearTimeout(nudgeTimer);
		nudgeTimer = setTimeout(() => {
			showNudgeConfirmation = false;
		}, 3000);
	}

	function handleNudgeKeydown(event: KeyboardEvent): void {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			handleSubmitNudge();
		}
	}
</script>

<section class="human-controls">
	{#if humanActive && controlledCharInfo}
		<div class="action-area" class:awaiting={isAwaitingMyInput}>
			<div class="context-bar {classSlug}">
				You are {controlledCharInfo.name}, the {controlledCharInfo.character_class}
			</div>
			<textarea
				class="action-input {classSlug}"
				bind:this={actionTextarea}
				bind:value={actionText}
				placeholder="What do you do?"
				rows={3}
				disabled={notConnected}
				onkeydown={handleActionKeydown}
			></textarea>
			<button
				class="submit-btn"
				onclick={handleSubmitAction}
				disabled={!actionText.trim() || notConnected}
			>
				Submit Action
			</button>
		</div>
	{:else}
		<div class="nudge-area">
			<h3 class="section-heading">Suggest Something</h3>
			<textarea
				class="nudge-input"
				bind:value={nudgeText}
				placeholder="Whisper a suggestion to the DM..."
				rows={2}
				disabled={notConnected}
				onkeydown={handleNudgeKeydown}
			></textarea>
			<button
				class="nudge-btn"
				onclick={handleSubmitNudge}
				disabled={!nudgeText.trim() || notConnected}
			>
				Send Nudge
			</button>
			{#if showNudgeConfirmation}
				<p class="nudge-confirmation">Nudge sent</p>
			{/if}
		</div>
	{/if}
</section>

<style>
	.human-controls {
		display: flex;
		flex-direction: column;
	}

	.section-heading {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		margin-bottom: var(--space-sm);
	}

	/* ===== Action Area (Play mode) ===== */
	.action-area {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.context-bar {
		font-family: var(--font-ui);
		font-size: 12px;
		font-weight: 500;
		padding: 6px 10px;
		border-radius: var(--border-radius-sm);
		background: rgba(232, 168, 73, 0.1);
		color: var(--accent-warm);
	}
	.context-bar.fighter { color: var(--color-fighter); background: rgba(196, 92, 74, 0.1); }
	.context-bar.rogue { color: var(--color-rogue); background: rgba(107, 142, 107, 0.1); }
	.context-bar.wizard { color: var(--color-wizard); background: rgba(123, 104, 184, 0.1); }
	.context-bar.cleric { color: var(--color-cleric); background: rgba(74, 144, 164, 0.1); }

	.action-input {
		width: 100%;
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid var(--text-secondary);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm);
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		resize: vertical;
		min-height: 60px;
		transition: border-color var(--transition-fast);
	}
	.action-input:focus {
		outline: none;
		border-color: var(--accent-warm);
	}
	.action-input.fighter:focus { border-color: var(--color-fighter); }
	.action-input.rogue:focus { border-color: var(--color-rogue); }
	.action-input.wizard:focus { border-color: var(--color-wizard); }
	.action-input.cleric:focus { border-color: var(--color-cleric); }

	/* Awaiting input: pulsing border */
	.action-area.awaiting .action-input {
		animation: awaiting-pulse 2s ease-in-out infinite;
	}

	@keyframes awaiting-pulse {
		0%, 100% { border-color: var(--accent-warm); box-shadow: 0 0 0 0 rgba(232, 168, 73, 0); }
		50% { border-color: var(--accent-warm); box-shadow: 0 0 8px rgba(232, 168, 73, 0.3); }
	}

	.submit-btn {
		align-self: flex-end;
		padding: 8px 16px;
		background: var(--accent-warm);
		color: var(--bg-primary);
		border: none;
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 13px;
		font-weight: 500;
		cursor: pointer;
		transition: background var(--transition-fast);
	}
	.submit-btn:hover:not(:disabled) {
		background: var(--accent-warm-hover);
	}
	.submit-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* ===== Nudge Area (Watch mode) ===== */
	.nudge-area {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.nudge-input {
		width: 100%;
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid var(--text-secondary);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm);
		font-family: var(--font-ui);
		font-size: var(--text-system);
		resize: vertical;
		min-height: 48px;
		transition: border-color var(--transition-fast);
	}
	.nudge-input:focus {
		outline: none;
		border-color: var(--accent-warm);
	}

	.nudge-btn {
		align-self: flex-end;
		padding: 6px 14px;
		background: transparent;
		color: var(--text-primary);
		border: 1px solid var(--text-secondary);
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: all var(--transition-fast);
	}
	.nudge-btn:hover:not(:disabled) {
		background: var(--bg-message);
		border-color: var(--text-primary);
	}
	.nudge-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.nudge-confirmation {
		font-family: var(--font-ui);
		font-size: 12px;
		color: var(--color-success);
		text-align: center;
		padding: var(--space-xs) 0;
		animation: fade-in 200ms ease-out;
	}

	@keyframes fade-in {
		from { opacity: 0; transform: translateY(-4px); }
		to { opacity: 1; transform: translateY(0); }
	}
</style>
