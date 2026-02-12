<script lang="ts">
	import {
		isAutopilotRunning,
		isPaused,
		speed,
		isThinking,
		gameState,
		connectionStatus,
		sendCommand,
	} from '$lib/stores';

	const humanActive = $derived($gameState?.human_active ?? false);
	const hasMessages = $derived(($gameState?.ground_truth_log?.length ?? 0) > 0);
	const notConnected = $derived($connectionStatus !== 'connected');

	function handleAutopilotToggle(): void {
		if ($isAutopilotRunning) {
			sendCommand({ type: 'stop_autopilot' });
		} else {
			sendCommand({ type: 'start_autopilot', speed: $speed });
		}
	}

	function handleNextTurn(): void {
		sendCommand({ type: 'next_turn' });
	}

	function handlePauseResume(): void {
		if ($isPaused) {
			sendCommand({ type: 'resume' });
		} else {
			sendCommand({ type: 'pause' });
		}
	}

	function handleSpeedChange(event: Event): void {
		const target = event.target as HTMLSelectElement;
		sendCommand({ type: 'set_speed', speed: target.value });
	}
</script>

<section class="game-controls">
	<h3 class="section-heading">Controls</h3>

	<div class="controls-row">
		<button
			class="control-btn autopilot-btn"
			class:active={$isAutopilotRunning}
			onclick={handleAutopilotToggle}
			disabled={humanActive || notConnected}
			title={humanActive ? 'Release character control first' : ''}
		>
			{#if $isAutopilotRunning}
				<svg class="btn-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
					<rect x="3" y="3" width="10" height="10" rx="1" fill="currentColor"/>
				</svg>
				Stop
			{:else}
				<svg class="btn-icon" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
					<polygon points="4,2 14,8 4,14" fill="currentColor"/>
				</svg>
				Start Autopilot
			{/if}
		</button>
	</div>

	<div class="controls-row">
		<button
			class="control-btn secondary-btn"
			onclick={handleNextTurn}
			disabled={$isAutopilotRunning || $isThinking || notConnected}
		>
			{hasMessages ? 'Next Turn' : 'Start Game'}
		</button>

		{#if $isAutopilotRunning}
			<button
				class="control-btn secondary-btn"
				onclick={handlePauseResume}
				disabled={notConnected}
			>
				{$isPaused ? 'Resume' : 'Pause'}
			</button>
		{/if}
	</div>

	<div class="speed-row">
		<label class="speed-label" for="speed-select">Speed</label>
		<select
			id="speed-select"
			class="speed-select"
			value={$speed}
			onchange={handleSpeedChange}
			disabled={notConnected}
		>
			<option value="slow">Slow</option>
			<option value="normal">Normal</option>
			<option value="fast">Fast</option>
		</select>
	</div>
</section>

<style>
	.game-controls {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.section-heading {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		margin-bottom: var(--space-xs);
	}

	.controls-row {
		display: flex;
		gap: var(--space-sm);
	}

	.control-btn {
		flex: 1;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
		padding: 8px 12px;
		border: 1px solid transparent;
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 13px;
		font-weight: 500;
		cursor: pointer;
		transition: all var(--transition-fast);
		white-space: nowrap;
	}

	.control-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-icon {
		flex-shrink: 0;
	}

	/* Autopilot button: primary style */
	.autopilot-btn {
		background: var(--accent-warm);
		color: var(--bg-primary);
		border-color: var(--accent-warm);
	}
	.autopilot-btn:hover:not(:disabled) {
		background: var(--accent-warm-hover);
		border-color: var(--accent-warm-hover);
	}

	/* Active autopilot: outlined style */
	.autopilot-btn.active {
		background: transparent;
		color: var(--text-secondary);
		border-color: var(--text-secondary);
	}
	.autopilot-btn.active:hover:not(:disabled) {
		background: rgba(184, 168, 150, 0.1);
	}

	/* Secondary buttons */
	.secondary-btn {
		background: transparent;
		color: var(--text-primary);
		border-color: var(--text-secondary);
	}
	.secondary-btn:hover:not(:disabled) {
		background: var(--bg-message);
		border-color: var(--text-primary);
	}

	/* Speed selector row */
	.speed-row {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
	}

	.speed-label {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
		white-space: nowrap;
	}

	.speed-select {
		flex: 1;
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid var(--text-secondary);
		border-radius: var(--border-radius-sm);
		padding: 6px 8px;
		font-family: var(--font-ui);
		font-size: var(--text-system);
		cursor: pointer;
		transition: border-color var(--transition-fast);
	}
	.speed-select:hover:not(:disabled) {
		border-color: var(--accent-warm);
	}
	.speed-select:focus {
		outline: 2px solid var(--accent-warm);
		outline-offset: 1px;
	}
	.speed-select:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	/* Dark option backgrounds */
	.speed-select option {
		background: var(--bg-secondary);
		color: var(--text-primary);
	}
</style>
