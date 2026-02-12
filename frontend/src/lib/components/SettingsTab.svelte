<script lang="ts">
	interface Props {
		combatMode: 'Narrative' | 'Tactical';
		maxCombatRounds: number;
		partySize: number;
		narrativeDisplayLimit: number;
		onCombatModeChange: (value: 'Narrative' | 'Tactical') => void;
		onMaxCombatRoundsChange: (value: number) => void;
		onPartySizeChange: (value: number) => void;
		onNarrativeDisplayLimitChange: (value: number) => void;
	}

	let {
		combatMode,
		maxCombatRounds,
		partySize,
		narrativeDisplayLimit,
		onCombatModeChange,
		onMaxCombatRoundsChange,
		onPartySizeChange,
		onNarrativeDisplayLimitChange,
	}: Props = $props();

	function clamp(value: number, min: number, max: number): number {
		return Math.max(min, Math.min(max, value));
	}

	function restoreOnBlur(
		e: FocusEvent,
		currentValue: number,
		min: number,
		max: number,
		onChange: (v: number) => void,
	): void {
		const input = e.target as HTMLInputElement;
		const v = parseInt(input.value);
		if (isNaN(v) || input.value.trim() === '') {
			// Restore the current state value into the input
			input.value = String(currentValue);
		} else {
			// Clamp and sync on blur
			const clamped = clamp(v, min, max);
			if (clamped !== v) {
				input.value = String(clamped);
				onChange(clamped);
			}
		}
	}
</script>

<div class="settings-tab">
	<!-- Combat Settings -->
	<h4 class="section-header">Combat</h4>

	<div class="setting-row">
		<label class="setting-label" for="combat-mode">Combat Mode</label>
		<select
			id="combat-mode"
			class="setting-select"
			value={combatMode}
			onchange={(e) =>
				onCombatModeChange((e.target as HTMLSelectElement).value as 'Narrative' | 'Tactical')}
		>
			<option value="Narrative">Narrative</option>
			<option value="Tactical">Tactical</option>
		</select>
	</div>

	<div class="setting-row">
		<label class="setting-label" for="max-combat-rounds">
			Max Combat Rounds
			<span class="setting-help">Auto-end combat after this many rounds (0 = unlimited)</span>
		</label>
		<input
			id="max-combat-rounds"
			type="number"
			class="setting-input"
			min="0"
			max="100"
			value={maxCombatRounds}
			oninput={(e) => {
				const v = parseInt((e.target as HTMLInputElement).value);
				if (!isNaN(v)) onMaxCombatRoundsChange(clamp(v, 0, 100));
			}}
			onblur={(e) => restoreOnBlur(e, maxCombatRounds, 0, 100, onMaxCombatRoundsChange)}
		/>
	</div>

	<hr class="settings-divider" />

	<!-- Party Settings -->
	<h4 class="section-header">Party</h4>

	<div class="setting-row">
		<label class="setting-label" for="party-size">
			Party Size
			<span class="setting-help">Number of player characters (1-8)</span>
		</label>
		<input
			id="party-size"
			type="number"
			class="setting-input"
			min="1"
			max="8"
			value={partySize}
			oninput={(e) => {
				const v = parseInt((e.target as HTMLInputElement).value);
				if (!isNaN(v)) onPartySizeChange(clamp(v, 1, 8));
			}}
			onblur={(e) => restoreOnBlur(e, partySize, 1, 8, onPartySizeChange)}
		/>
	</div>

	<hr class="settings-divider" />

	<!-- Display Settings -->
	<h4 class="section-header">Display</h4>

	<div class="setting-row">
		<label class="setting-label" for="narrative-display-limit">
			Narrative Display Limit
			<span class="setting-help">
				Max messages shown in narrative area (10-1000).
				Use "Load earlier messages" to see older entries.
			</span>
		</label>
		<input
			id="narrative-display-limit"
			type="number"
			class="setting-input"
			min="10"
			max="1000"
			step="10"
			value={narrativeDisplayLimit}
			oninput={(e) => {
				const v = parseInt((e.target as HTMLInputElement).value);
				if (!isNaN(v)) onNarrativeDisplayLimitChange(clamp(v, 10, 1000));
			}}
			onblur={(e) =>
				restoreOnBlur(e, narrativeDisplayLimit, 10, 1000, onNarrativeDisplayLimitChange)}
		/>
	</div>
</div>

<style>
	.settings-tab {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.section-header {
		font-family: var(--font-ui);
		font-size: 15px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0 0 var(--space-xs) 0;
	}

	.setting-row {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-md);
		padding: var(--space-xs) 0;
	}

	.setting-label {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		font-weight: 500;
		color: var(--text-primary);
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.setting-help {
		font-size: 12px;
		font-weight: 400;
		color: var(--text-secondary);
		line-height: 1.3;
	}

	.setting-select,
	.setting-input {
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		padding: 6px 8px;
		font-family: var(--font-ui);
		font-size: var(--text-system);
		cursor: pointer;
		transition: border-color var(--transition-fast);
		min-width: 120px;
	}

	.setting-input {
		width: 100px;
		min-width: 100px;
		cursor: text;
		text-align: right;
	}

	.setting-select:hover,
	.setting-input:hover {
		border-color: var(--accent-warm);
	}

	.setting-select:focus,
	.setting-input:focus {
		outline: 2px solid var(--accent-warm);
		outline-offset: 1px;
		border-color: transparent;
	}

	.setting-select option {
		background: var(--bg-secondary);
		color: var(--text-primary);
	}

	/* Remove number input spinners on Chrome/Safari */
	.setting-input::-webkit-inner-spin-button,
	.setting-input::-webkit-outer-spin-button {
		-webkit-appearance: none;
		margin: 0;
	}

	/* Firefox */
	.setting-input[type='number'] {
		appearance: textfield;
		-moz-appearance: textfield;
	}

	.settings-divider {
		border: none;
		border-top: 1px solid rgba(184, 168, 150, 0.1);
		margin: var(--space-sm) 0;
	}
</style>
