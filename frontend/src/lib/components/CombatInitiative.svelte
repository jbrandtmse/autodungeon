<script lang="ts">
	import { gameState } from '$lib/stores';

	const combatState = $derived($gameState?.combat_state ?? null);
	const characters = $derived($gameState?.characters ?? {});
	const isActive = $derived(combatState?.active === true);

	const combatants = $derived.by(() => {
		if (!combatState) return [];
		const order = combatState.initiative_order ?? [];
		const rolls = combatState.initiative_rolls ?? {};
		const npcs = combatState.npc_profiles ?? {};
		const current = combatState.current_combatant ?? '';

		return order
			.filter((entry) => entry !== 'dm')
			.map((entry) => {
				const isNpc = entry.startsWith('dm:');
				const roll = rolls[entry] ?? 0;
				const isCurrent = entry === current;

				if (isNpc) {
					const npcKey = entry.slice(3);
					const npcProfile = npcs[entry] ?? npcs[npcKey];
					const displayName = npcProfile?.name ?? npcKey;
					return {
						key: entry,
						displayName,
						roll,
						isCurrent,
						isNpc: true,
						classSlug: 'dm',
					};
				} else {
					const char = characters[entry];
					const displayName = char?.name ?? entry;
					const classSlug = char?.character_class
						? char.character_class.toLowerCase().replace(/[^a-z0-9-]/g, '')
						: 'adventurer';
					return {
						key: entry,
						displayName,
						roll,
						isCurrent,
						isNpc: false,
						classSlug,
					};
				}
			});
	});
</script>

{#if isActive && combatState}
	<section class="combat-initiative">
		<div class="combat-banner">
			COMBAT &mdash; Round {combatState.round_number}
		</div>

		<h3 class="section-heading">Initiative</h3>

		<ol class="initiative-list">
			{#each combatants as c (c.key)}
				<li
					class="initiative-entry {c.classSlug}"
					class:current={c.isCurrent}
					class:npc={c.isNpc}
				>
					<span class="combatant-name">{c.displayName}</span>
					<span class="initiative-roll">{c.roll}</span>
				</li>
			{/each}
		</ol>
	</section>
{/if}

<style>
	.combat-initiative {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.combat-banner {
		font-family: var(--font-ui);
		font-size: 12px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--accent-warm);
		background: rgba(232, 168, 73, 0.1);
		border: 1px solid rgba(232, 168, 73, 0.3);
		border-radius: var(--border-radius-sm);
		padding: 6px 10px;
		text-align: center;
	}

	.section-heading {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	.initiative-list {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 2px;
		padding: 0;
		margin: 0;
	}

	.initiative-entry {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 4px 8px;
		border-radius: var(--border-radius-sm);
		font-family: var(--font-ui);
		font-size: 13px;
		transition: background var(--transition-fast);
	}

	.initiative-entry.current {
		background: rgba(232, 168, 73, 0.15);
	}

	.combatant-name {
		font-weight: 500;
		color: var(--text-secondary);
	}

	/* PC class colors */
	.initiative-entry.fighter .combatant-name { color: var(--color-fighter); }
	.initiative-entry.rogue .combatant-name { color: var(--color-rogue); }
	.initiative-entry.wizard .combatant-name { color: var(--color-wizard); }
	.initiative-entry.cleric .combatant-name { color: var(--color-cleric); }

	/* NPC color: DM gold */
	.initiative-entry.npc .combatant-name { color: var(--color-dm); }

	.initiative-roll {
		font-family: var(--font-mono);
		font-size: 12px;
		color: var(--text-secondary);
		min-width: 24px;
		text-align: right;
	}
</style>
