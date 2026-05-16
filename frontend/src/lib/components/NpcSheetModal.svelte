<script lang="ts">
	import { getNpcProfile } from '$lib/api';
	import { gameState } from '$lib/stores';
	import type { NpcProfile } from '$lib/types';

	let { open, sessionId, npcKey, onClose }: {
		open: boolean;
		sessionId: string;
		npcKey: string;
		onClose: () => void;
	} = $props();

	let npc = $state<NpcProfile | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let dialogEl: HTMLDivElement | undefined = $state();

	// Load profile when modal opens for a given key. Reset on close.
	$effect(() => {
		if (open && sessionId && npcKey) {
			loadProfile();
		}
		if (!open) {
			npc = null;
			error = null;
		}
	});

	// AC #11: When combat ends, auto-close any open modal so the player
	// never sees a stale sheet for a no-longer-existent encounter.
	$effect(() => {
		if (open && $gameState && $gameState.combat_state?.active === false) {
			onClose();
		}
	});

	async function loadProfile(): Promise<void> {
		loading = true;
		error = null;
		try {
			npc = await getNpcProfile(sessionId, npcKey);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load NPC profile';
		} finally {
			loading = false;
		}
	}

	function handleKeydown(e: KeyboardEvent): void {
		if (!open) return;
		if (e.key === 'Escape') {
			e.preventDefault();
			onClose();
		}
		if (e.key === 'Tab' && dialogEl) {
			const focusable = dialogEl.querySelectorAll<HTMLElement>(
				'button:not([disabled]), [tabindex]:not([tabindex="-1"]), details summary',
			);
			if (focusable.length === 0) return;
			const first = focusable[0];
			const last = focusable[focusable.length - 1];
			if (e.shiftKey && document.activeElement === first) {
				e.preventDefault();
				last.focus();
			} else if (!e.shiftKey && document.activeElement === last) {
				e.preventDefault();
				first.focus();
			}
		}
	}

	function handleBackdropClick(e: MouseEvent): void {
		if (e.target === e.currentTarget) {
			onClose();
		}
	}

	const hpPercent = $derived(
		npc && npc.hp_max > 0
			? Math.max(0, Math.min(100, (npc.hp_current / npc.hp_max) * 100))
			: 0,
	);

	const hpColorClass = $derived.by(() => {
		if (hpPercent > 50) return 'hp-green';
		if (hpPercent > 25) return 'hp-amber';
		return 'hp-red';
	});

	const isDefeated = $derived(npc?.hp_current === 0);
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<!--
		Keydown is handled exclusively by `<svelte:window>` above. Binding it
		on the backdrop too would cause Escape / Tab to fire `handleKeydown`
		twice as the event bubbles (closing the modal twice, breaking the
		focus trap behaviour for Shift+Tab from first / Tab from last).
		The window-level keydown listener handles Escape so the click-event-
		without-keyevent a11y rule has an equivalent keyboard activation.
	-->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="modal-backdrop" onclick={handleBackdropClick}>
		<div
			class="modal"
			role="dialog"
			aria-modal="true"
			aria-label="NPC Sheet"
			bind:this={dialogEl}
		>
			<button class="close-btn" onclick={onClose} aria-label="Close NPC sheet">X</button>

			{#if loading}
				<div class="modal-loading">Loading NPC profile...</div>
			{:else if error}
				<div class="modal-error">{error}</div>
			{:else if npc}
				<header class="sheet-header">
					<h2 class="sheet-name" class:defeated={isDefeated}>{npc.name}</h2>
					{#if isDefeated}
						<div class="defeated-label">Defeated</div>
					{/if}
				</header>

				<!-- HP -->
				<section class="sheet-section">
					<h3 class="section-title">Hit Points</h3>
					<div
						class="hp-bar-container"
						role="meter"
						aria-label="Hit points"
						aria-valuenow={npc.hp_current}
						aria-valuemin={0}
						aria-valuemax={npc.hp_max}
					>
						<div class="hp-bar-fill {hpColorClass}" style="width: {hpPercent}%"></div>
						<span class="hp-text">{npc.hp_current}/{npc.hp_max}</span>
					</div>
				</section>

				<!-- Combat Chips -->
				<section class="sheet-section">
					<h3 class="section-title">Combat</h3>
					<div class="chip-row">
						<div class="chip">
							<span class="chip-label">AC</span>
							<span class="chip-value">{npc.ac}</span>
						</div>
						<div class="chip">
							<span class="chip-label">Init</span>
							<span class="chip-value">
								{npc.initiative_modifier >= 0 ? `+${npc.initiative_modifier}` : npc.initiative_modifier}
							</span>
						</div>
					</div>
				</section>

				<!-- Conditions -->
				<section class="sheet-section">
					<h3 class="section-title">Conditions</h3>
					{#if npc.conditions.length > 0}
						<ul class="condition-list">
							{#each npc.conditions as condition}
								<li class="condition-item">{condition}</li>
							{/each}
						</ul>
					{:else}
						<p class="empty-text">None</p>
					{/if}
				</section>

				<!-- Personality -->
				{#if npc.personality}
					<section class="sheet-section">
						<h3 class="section-title">Personality</h3>
						<p class="prose">{npc.personality}</p>
					</section>
				{/if}

				<!-- Tactics -->
				{#if npc.tactics}
					<section class="sheet-section">
						<h3 class="section-title">Tactics</h3>
						<p class="prose">{npc.tactics}</p>
					</section>
				{/if}

				<!-- Secret (opt-in disclosure). AC #6: rendered separately. -->
				{#if npc.secret}
					<details class="secret-details">
						<summary class="section-title clickable">Secret (DM-only)</summary>
						<p class="prose secret-text">{npc.secret}</p>
					</details>
				{/if}
			{/if}
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 200;
		animation: fadeIn 0.15s ease;
	}

	.modal {
		background: var(--bg-secondary);
		border-radius: 12px;
		max-width: 560px;
		width: 95%;
		max-height: 90vh;
		overflow-y: auto;
		padding: var(--space-lg);
		position: relative;
		animation: scaleIn 0.15s ease;
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}

	.close-btn {
		position: absolute;
		top: var(--space-md);
		right: var(--space-md);
		background: none;
		border: none;
		color: var(--text-secondary);
		font-family: var(--font-ui);
		font-size: 16px;
		font-weight: 600;
		cursor: pointer;
		padding: 4px 8px;
		border-radius: var(--border-radius-sm);
		transition: all var(--transition-fast);
	}

	.close-btn:hover {
		background: var(--bg-message);
		color: var(--text-primary);
	}

	.modal-loading,
	.modal-error {
		text-align: center;
		padding: var(--space-xl);
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-secondary);
	}

	.modal-error {
		color: var(--color-error, #c45c4a);
	}

	.sheet-header {
		padding-bottom: var(--space-sm);
		border-bottom: 1px solid rgba(184, 168, 150, 0.15);
	}

	.sheet-name {
		font-family: var(--font-narrative);
		font-size: 22px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}

	.sheet-name.defeated {
		text-decoration: line-through;
		opacity: 0.6;
	}

	.defeated-label {
		font-family: var(--font-ui);
		font-size: 12px;
		font-weight: 600;
		color: var(--color-error, #c45c4a);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		margin-top: 4px;
	}

	.sheet-section {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
	}

	.section-title {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		margin: 0;
	}

	.section-title.clickable {
		cursor: pointer;
		list-style: none;
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.section-title.clickable::-webkit-details-marker {
		display: none;
	}

	.section-title.clickable::before {
		content: '\25B6';
		font-size: 8px;
		color: var(--text-secondary);
		transition: transform var(--transition-fast);
	}

	.secret-details[open] .section-title.clickable::before {
		transform: rotate(90deg);
	}

	.hp-bar-container {
		position: relative;
		height: 20px;
		background: var(--bg-primary);
		border-radius: var(--border-radius-sm);
		overflow: hidden;
	}

	.hp-bar-fill {
		height: 100%;
		border-radius: var(--border-radius-sm);
		transition: width 0.4s ease;
	}

	.hp-bar-fill.hp-green { background: #6B8E6B; }
	.hp-bar-fill.hp-amber { background: #E8A849; }
	.hp-bar-fill.hp-red { background: #C45C4A; }

	.hp-text {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 500;
		color: var(--text-primary);
		text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6);
	}

	.chip-row {
		display: flex;
		gap: var(--space-sm);
		flex-wrap: wrap;
	}

	.chip {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 4px 10px;
		background: var(--bg-primary);
		border-radius: var(--border-radius-sm);
	}

	.chip-label {
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
	}

	.chip-value {
		font-family: var(--font-mono);
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.condition-list {
		list-style: disc;
		padding-left: 18px;
		margin: 0;
	}

	.condition-item {
		font-family: var(--font-ui);
		font-size: 13px;
		color: var(--text-primary);
		padding: 2px 0;
	}

	.empty-text {
		font-family: var(--font-ui);
		font-size: 13px;
		color: var(--text-secondary);
		font-style: italic;
		margin: 0;
	}

	.prose {
		font-family: var(--font-ui);
		font-size: 13px;
		color: var(--text-primary);
		line-height: 1.5;
		margin: 0;
	}

	.secret-details {
		font-family: var(--font-ui);
		padding-top: var(--space-xs);
		border-top: 1px dashed rgba(184, 168, 150, 0.15);
	}

	.secret-text {
		padding-top: var(--space-xs);
		color: var(--accent-warm, #e8a849);
		font-style: italic;
	}

	@keyframes fadeIn {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	@keyframes scaleIn {
		from { transform: scale(0.95); opacity: 0; }
		to { transform: scale(1); opacity: 1; }
	}
</style>
