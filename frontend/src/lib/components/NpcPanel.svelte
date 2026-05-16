<script lang="ts">
	import { gameState } from '$lib/stores';
	import NpcCard from './NpcCard.svelte';

	const combatState = $derived($gameState?.combat_state ?? null);
	const isActive = $derived(combatState?.active === true);

	const npcs = $derived.by(() => {
		const profiles = combatState?.npc_profiles ?? {};
		return Object.entries(profiles);
	});
</script>

<!--
	Story 15-9: Active NPCs sidebar panel.

	AC #1/#2: Renders only when combat is active AND there is at least one
	NPC profile. The entire <section> is gated by the {#if} block so no DOM
	nodes are emitted out of combat.
-->
{#if isActive && npcs.length > 0}
	<section class="npc-panel">
		<h3 class="section-heading">Active NPCs</h3>

		<div class="npc-list" role="list">
			{#each npcs as [key, profile] (key)}
				<NpcCard npcKey={key} npc={profile} />
			{/each}
		</div>
	</section>
{/if}

<style>
	.npc-panel {
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

	.npc-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}
</style>
