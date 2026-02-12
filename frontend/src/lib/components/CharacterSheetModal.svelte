<script lang="ts">
	import { getCharacterSheet } from '$lib/api';
	import type { CharacterSheetFull } from '$lib/types';

	let { open, sessionId, characterName, onClose }: {
		open: boolean;
		sessionId: string;
		characterName: string;
		onClose: () => void;
	} = $props();

	let sheet = $state<CharacterSheetFull | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let dialogEl: HTMLDivElement | undefined = $state();

	$effect(() => {
		if (open && sessionId && characterName) {
			loadSheet();
		}
		if (!open) {
			sheet = null;
			error = null;
		}
	});

	async function loadSheet(): Promise<void> {
		loading = true;
		error = null;
		try {
			sheet = await getCharacterSheet(sessionId, characterName);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load character sheet';
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
				'button:not([disabled]), [tabindex]:not([tabindex="-1"])',
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

	function formatModifier(mod: number): string {
		return mod >= 0 ? `+${mod}` : `${mod}`;
	}

	const hpPercent = $derived(
		sheet && sheet.hit_points_max > 0
			? Math.max(0, Math.min(100, (sheet.hit_points_current / sheet.hit_points_max) * 100))
			: 0
	);

	const hpColorClass = $derived.by(() => {
		if (hpPercent > 50) return 'hp-green';
		if (hpPercent > 25) return 'hp-amber';
		return 'hp-red';
	});

	const abilities = $derived(
		sheet
			? [
				{ name: 'STR', score: sheet.strength, mod: sheet.strength_modifier },
				{ name: 'DEX', score: sheet.dexterity, mod: sheet.dexterity_modifier },
				{ name: 'CON', score: sheet.constitution, mod: sheet.constitution_modifier },
				{ name: 'INT', score: sheet.intelligence, mod: sheet.intelligence_modifier },
				{ name: 'WIS', score: sheet.wisdom, mod: sheet.wisdom_modifier },
				{ name: 'CHA', score: sheet.charisma, mod: sheet.charisma_modifier },
			]
			: []
	);
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="modal-backdrop" onclick={handleBackdropClick} onkeydown={handleKeydown}>
		<div
			class="modal"
			role="dialog"
			aria-modal="true"
			aria-label="Character Sheet"
			bind:this={dialogEl}
		>
			<button class="close-btn" onclick={onClose} aria-label="Close character sheet">X</button>

			{#if loading}
				<div class="modal-loading">Loading character sheet...</div>
			{:else if error}
				<div class="modal-error">{error}</div>
			{:else if sheet}
				<header class="sheet-header">
					<h2 class="sheet-name">{sheet.name}</h2>
					<div class="sheet-subinfo">
						{sheet.race} {sheet.character_class}, Level {sheet.level}
						{#if sheet.background}
							<span class="separator">|</span> {sheet.background}
						{/if}
						{#if sheet.alignment}
							<span class="separator">|</span> {sheet.alignment}
						{/if}
					</div>
				</header>

				<div class="sheet-columns">
					<!-- Left Column -->
					<div class="sheet-col">
						<!-- Ability Scores -->
						<section class="sheet-section">
							<h3 class="section-title">Ability Scores</h3>
							<div class="ability-grid">
								{#each abilities as ability}
									<div class="ability-item">
										<span class="ability-name">{ability.name}</span>
										<span class="ability-score">{ability.score}</span>
										<span class="ability-mod">{formatModifier(ability.mod)}</span>
									</div>
								{/each}
							</div>
						</section>

						<!-- Combat Stats -->
						<section class="sheet-section">
							<h3 class="section-title">Combat</h3>
							<div class="combat-grid">
								<div class="combat-stat">
									<span class="stat-label">AC</span>
									<span class="stat-value">{sheet.armor_class}</span>
								</div>
								<div class="combat-stat">
									<span class="stat-label">Initiative</span>
									<span class="stat-value">{formatModifier(sheet.initiative)}</span>
								</div>
								<div class="combat-stat">
									<span class="stat-label">Speed</span>
									<span class="stat-value">{sheet.speed} ft</span>
								</div>
								<div class="combat-stat">
									<span class="stat-label">Hit Dice</span>
									<span class="stat-value">{sheet.hit_dice}</span>
								</div>
							</div>
							<div class="hp-section">
								<span class="stat-label">HP</span>
								<div
									class="hp-bar-container"
									role="meter"
									aria-label="Hit points"
									aria-valuenow={sheet.hit_points_current}
									aria-valuemin={0}
									aria-valuemax={sheet.hit_points_max}
								>
									<div class="hp-bar-fill {hpColorClass}" style="width: {hpPercent}%"></div>
									<span class="hp-text">
										{sheet.hit_points_current}/{sheet.hit_points_max}
										{#if sheet.hit_points_temp > 0}
											(+{sheet.hit_points_temp} temp)
										{/if}
									</span>
								</div>
							</div>
						</section>

						<!-- Equipment -->
						<details class="sheet-details">
							<summary class="section-title clickable">Equipment</summary>
							<div class="details-content">
								{#if sheet.weapons.length > 0}
									<h4 class="subsection-title">Weapons</h4>
									{#each sheet.weapons as weapon}
										<div class="item-row">
											<span class="item-name">{weapon.name}</span>
											<span class="item-detail">{weapon.damage_dice} {weapon.damage_type}</span>
										</div>
									{/each}
								{/if}
								{#if sheet.armor}
									<h4 class="subsection-title">Armor</h4>
									<div class="item-row">
										<span class="item-name">{sheet.armor.name}</span>
										<span class="item-detail">AC {sheet.armor.armor_class}</span>
									</div>
								{/if}
								{#if sheet.equipment.length > 0}
									<h4 class="subsection-title">Items</h4>
									{#each sheet.equipment as item}
										<div class="item-row">
											<span class="item-name">{item.name}</span>
											{#if item.quantity > 1}
												<span class="item-detail">x{item.quantity}</span>
											{/if}
										</div>
									{/each}
								{/if}
								<div class="currency-row">
									{#if sheet.gold > 0}<span class="currency">{sheet.gold} gp</span>{/if}
									{#if sheet.silver > 0}<span class="currency">{sheet.silver} sp</span>{/if}
									{#if sheet.copper > 0}<span class="currency">{sheet.copper} cp</span>{/if}
								</div>
							</div>
						</details>
					</div>

					<!-- Right Column -->
					<div class="sheet-col">
						<!-- Skills -->
						<details class="sheet-details">
							<summary class="section-title clickable">Skills</summary>
							<div class="details-content">
								{#if sheet.skill_proficiencies.length > 0}
									<ul class="skill-list">
										{#each sheet.skill_proficiencies as skill}
											<li class="skill-item">
												<span class="proficiency-marker">*</span> {skill}
												{#if sheet.skill_expertise.includes(skill)}
													<span class="expertise-marker">(expertise)</span>
												{/if}
											</li>
										{/each}
									</ul>
								{:else}
									<p class="empty-text">No skill proficiencies</p>
								{/if}
							</div>
						</details>

						<!-- Spellcasting -->
						{#if sheet.spellcasting_ability}
							<details class="sheet-details" open>
								<summary class="section-title clickable">Spellcasting</summary>
								<div class="details-content">
									<div class="spell-stats">
										{#if sheet.spell_save_dc}
											<span class="spell-stat">Save DC: {sheet.spell_save_dc}</span>
										{/if}
										{#if sheet.spell_attack_bonus !== null}
											<span class="spell-stat">Attack: {formatModifier(sheet.spell_attack_bonus)}</span>
										{/if}
									</div>
									{#if sheet.cantrips.length > 0}
										<h4 class="subsection-title">Cantrips</h4>
										<p class="spell-list-text">{sheet.cantrips.join(', ')}</p>
									{/if}
									{#if sheet.spells_known.length > 0}
										<h4 class="subsection-title">Spells</h4>
										{#each sheet.spells_known as spell}
											<div class="spell-row">
												<span class="spell-name">{spell.name}</span>
												<span class="spell-level">Lvl {spell.level}</span>
											</div>
										{/each}
									{/if}
									{#if Object.keys(sheet.spell_slots).length > 0}
										<h4 class="subsection-title">Spell Slots</h4>
										<div class="slot-grid">
											{#each Object.entries(sheet.spell_slots) as [level, slot]}
												<div class="slot-item">
													<span class="slot-level">Lvl {level}</span>
													<span class="slot-count">{slot.current}/{slot.max}</span>
												</div>
											{/each}
										</div>
									{/if}
								</div>
							</details>
						{/if}

						<!-- Features & Traits -->
						<details class="sheet-details">
							<summary class="section-title clickable">Features &amp; Traits</summary>
							<div class="details-content">
								{#if sheet.class_features.length > 0}
									<h4 class="subsection-title">Class Features</h4>
									<ul class="feature-list">
										{#each sheet.class_features as feature}
											<li>{feature}</li>
										{/each}
									</ul>
								{/if}
								{#if sheet.racial_traits.length > 0}
									<h4 class="subsection-title">Racial Traits</h4>
									<ul class="feature-list">
										{#each sheet.racial_traits as trait}
											<li>{trait}</li>
										{/each}
									</ul>
								{/if}
								{#if sheet.feats.length > 0}
									<h4 class="subsection-title">Feats</h4>
									<ul class="feature-list">
										{#each sheet.feats as feat}
											<li>{feat}</li>
										{/each}
									</ul>
								{/if}
							</div>
						</details>

						<!-- Personality -->
						<details class="sheet-details">
							<summary class="section-title clickable">Personality</summary>
							<div class="details-content">
								{#if sheet.personality_traits}
									<h4 class="subsection-title">Traits</h4>
									<p class="personality-text">{sheet.personality_traits}</p>
								{/if}
								{#if sheet.ideals}
									<h4 class="subsection-title">Ideals</h4>
									<p class="personality-text">{sheet.ideals}</p>
								{/if}
								{#if sheet.bonds}
									<h4 class="subsection-title">Bonds</h4>
									<p class="personality-text">{sheet.bonds}</p>
								{/if}
								{#if sheet.flaws}
									<h4 class="subsection-title">Flaws</h4>
									<p class="personality-text">{sheet.flaws}</p>
								{/if}
								{#if sheet.backstory}
									<h4 class="subsection-title">Backstory</h4>
									<p class="personality-text">{sheet.backstory}</p>
								{/if}
							</div>
						</details>
					</div>
				</div>
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
		max-width: 800px;
		width: 95%;
		max-height: 90vh;
		overflow-y: auto;
		padding: var(--space-lg);
		position: relative;
		animation: scaleIn 0.15s ease;
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
		color: var(--color-error);
	}

	/* Header */
	.sheet-header {
		margin-bottom: var(--space-lg);
		padding-bottom: var(--space-md);
		border-bottom: 1px solid rgba(184, 168, 150, 0.15);
	}

	.sheet-name {
		font-family: var(--font-narrative);
		font-size: 22px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: 4px;
	}

	.sheet-subinfo {
		font-family: var(--font-ui);
		font-size: 13px;
		color: var(--text-secondary);
	}

	.separator {
		margin: 0 6px;
		opacity: 0.5;
	}

	/* Columns */
	.sheet-columns {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--space-lg);
	}

	@media (max-width: 600px) {
		.sheet-columns {
			grid-template-columns: 1fr;
		}
	}

	.sheet-col {
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}

	/* Sections */
	.sheet-section {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.section-title {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.08em;
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

	.sheet-details[open] .section-title.clickable::before {
		transform: rotate(90deg);
	}

	.sheet-details {
		font-family: var(--font-ui);
	}

	.details-content {
		padding-top: var(--space-sm);
		padding-left: 14px;
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
	}

	/* Ability Scores */
	.ability-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: var(--space-xs);
	}

	.ability-item {
		text-align: center;
		background: var(--bg-primary);
		border-radius: var(--border-radius-sm);
		padding: var(--space-xs);
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.ability-name {
		font-family: var(--font-ui);
		font-size: 10px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.ability-score {
		font-family: var(--font-mono);
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.ability-mod {
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--accent-warm);
	}

	/* Combat */
	.combat-grid {
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: var(--space-xs);
	}

	.combat-stat {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 4px var(--space-sm);
		background: var(--bg-primary);
		border-radius: var(--border-radius-sm);
	}

	.stat-label {
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
	}

	.stat-value {
		font-family: var(--font-mono);
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}

	/* HP Bar */
	.hp-section {
		display: flex;
		align-items: center;
		gap: var(--space-sm);
	}

	.hp-bar-container {
		position: relative;
		flex: 1;
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

	/* Items */
	.subsection-title {
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 600;
		color: var(--text-secondary);
		margin-top: var(--space-xs);
	}

	.item-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 12px;
		padding: 2px 0;
	}

	.item-name {
		color: var(--text-primary);
	}

	.item-detail {
		color: var(--text-secondary);
		font-family: var(--font-mono);
		font-size: 11px;
	}

	.currency-row {
		display: flex;
		gap: var(--space-sm);
		font-size: 12px;
		color: var(--accent-warm);
		margin-top: var(--space-xs);
	}

	.currency {
		font-family: var(--font-mono);
	}

	/* Skills */
	.skill-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.skill-item {
		font-size: 12px;
		color: var(--text-primary);
		padding: 2px 0;
	}

	.proficiency-marker {
		color: var(--accent-warm);
		font-weight: 700;
	}

	.expertise-marker {
		font-size: 10px;
		color: var(--text-secondary);
		font-style: italic;
	}

	.empty-text {
		font-size: 12px;
		color: var(--text-secondary);
		font-style: italic;
	}

	/* Spells */
	.spell-stats {
		display: flex;
		gap: var(--space-md);
	}

	.spell-stat {
		font-size: 12px;
		color: var(--text-secondary);
		font-family: var(--font-mono);
	}

	.spell-list-text {
		font-size: 12px;
		color: var(--text-primary);
	}

	.spell-row {
		display: flex;
		justify-content: space-between;
		font-size: 12px;
		padding: 2px 0;
	}

	.spell-name {
		color: var(--text-primary);
	}

	.spell-level {
		color: var(--text-secondary);
		font-family: var(--font-mono);
		font-size: 11px;
	}

	.slot-grid {
		display: flex;
		gap: var(--space-sm);
		flex-wrap: wrap;
	}

	.slot-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
		background: var(--bg-primary);
		padding: 4px 8px;
		border-radius: var(--border-radius-sm);
	}

	.slot-level {
		font-size: 10px;
		color: var(--text-secondary);
	}

	.slot-count {
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--text-primary);
	}

	/* Features */
	.feature-list {
		list-style: disc;
		padding-left: 16px;
		margin: 0;
	}

	.feature-list li {
		font-size: 12px;
		color: var(--text-primary);
		padding: 2px 0;
	}

	/* Personality */
	.personality-text {
		font-size: 12px;
		color: var(--text-primary);
		line-height: 1.5;
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
