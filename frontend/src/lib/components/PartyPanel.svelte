<script lang="ts">
	import { gameState, isThinking, thinkingAgent } from '$lib/stores';
	import CharacterCard from './CharacterCard.svelte';

	const characters = $derived($gameState?.characters ?? {});
	const controlledCharacter = $derived($gameState?.controlled_character ?? null);
	const characterSheets = $derived($gameState?.character_sheets ?? {});

	const partyList = $derived.by(() => {
		const entries = Object.entries(characters);
		return entries.map(([key, char]) => {
			const classSlug = char.character_class
				? char.character_class.toLowerCase().replace(/[^a-z0-9-]/g, '')
				: 'adventurer';
			const sheet = characterSheets[key];
			const hp = sheet?.hp ?? undefined;
			const isControlled =
				controlledCharacter === key || controlledCharacter === char.name;
			const isGenerating = $isThinking && ($thinkingAgent === key || $thinkingAgent === char.name);
			return {
				agentKey: key,
				name: char.name,
				characterClass: char.character_class,
				classSlug,
				isControlled,
				isGenerating,
				hp,
			};
		});
	});
</script>

<section class="party-panel">
	<h3 class="section-heading">Party</h3>

	{#if partyList.length > 0}
		<div class="character-list" role="list">
			{#each partyList as char (char.agentKey)}
				<CharacterCard
					agentKey={char.agentKey}
					name={char.name}
					characterClass={char.characterClass}
					classSlug={char.classSlug}
					isControlled={char.isControlled}
					isGenerating={char.isGenerating}
					hp={char.hp}
				/>
			{/each}
		</div>
	{:else}
		<p class="empty-state">No characters loaded</p>
	{/if}

	<div class="shortcuts-hint">
		Press
		<kbd>1</kbd><kbd>2</kbd><kbd>3</kbd><kbd>4</kbd>
		to drop in,
		<kbd>Esc</kbd>
		to release
	</div>
</section>

<style>
	.party-panel {
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

	.character-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.empty-state {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
		font-style: italic;
		padding: var(--space-sm) 0;
	}

	.shortcuts-hint {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 4px;
		padding-top: var(--space-xs);
	}

	kbd {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 20px;
		height: 20px;
		padding: 0 5px;
		background: var(--bg-primary);
		border: 1px solid var(--text-secondary);
		border-radius: 3px;
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-primary);
		line-height: 1;
	}
</style>
