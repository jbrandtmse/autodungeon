<script lang="ts">
	import type { Character } from '$lib/types';

	/**
	 * Character library browser — grid of character cards with search and filtering.
	 * Story 16-9: Character Creation & Library.
	 */

	interface Props {
		characters: Character[];
		loading?: boolean;
		onSelect: (character: Character) => void;
		onCreate: () => void;
	}

	let { characters, loading = false, onSelect, onCreate }: Props = $props();

	let searchQuery = $state('');

	let filteredCharacters = $derived(
		searchQuery.trim()
			? characters.filter(
					(c) =>
						c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
						c.character_class.toLowerCase().includes(searchQuery.toLowerCase()),
				)
			: characters,
	);

	let presetCount = $derived(characters.filter((c) => c.source === 'preset').length);
	let libraryCount = $derived(characters.filter((c) => c.source === 'library').length);

	function classColor(characterClass: string): string {
		const classMap: Record<string, string> = {
			fighter: 'var(--color-fighter)',
			rogue: 'var(--color-rogue)',
			wizard: 'var(--color-wizard)',
			cleric: 'var(--color-cleric)',
		};
		return classMap[characterClass.toLowerCase()] ?? '#808080';
	}

	function truncate(text: string, maxLen: number): string {
		if (text.length <= maxLen) return text;
		return text.slice(0, maxLen).trimEnd() + '...';
	}

	function sanitize(text: string): string {
		return text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;');
	}

	function handleCardKeydown(e: KeyboardEvent, character: Character): void {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onSelect(character);
		}
	}
</script>

<div class="character-library">
	<!-- Header -->
	<header class="library-header">
		<div class="header-top">
			<h2 class="library-title">Character Library</h2>
			<button class="btn btn-primary" onclick={onCreate}>+ New Character</button>
		</div>
		{#if !loading && characters.length > 0}
			<p class="library-stats">
				{presetCount} preset{presetCount !== 1 ? 's' : ''}, {libraryCount} custom
			</p>
		{/if}
	</header>

	<!-- Search -->
	{#if !loading && characters.length > 0}
		<div class="search-wrapper">
			<svg
				class="search-icon"
				viewBox="0 0 24 24"
				width="16"
				height="16"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
				aria-hidden="true"
			>
				<circle cx="11" cy="11" r="8" />
				<line x1="21" y1="21" x2="16.65" y2="16.65" />
			</svg>
			<input
				type="text"
				class="search-input"
				placeholder="Search by name or class..."
				bind:value={searchQuery}
				aria-label="Search characters"
			/>
		</div>
	{/if}

	<!-- Loading state -->
	{#if loading}
		<div class="card-grid" aria-label="Loading characters">
			{#each [1, 2, 3, 4] as i (i)}
				<div class="skeleton-card">
					<div class="skeleton-line skeleton-name"></div>
					<div class="skeleton-line skeleton-class"></div>
					<div class="skeleton-line skeleton-personality"></div>
				</div>
			{/each}
		</div>

	<!-- Empty state -->
	{:else if characters.length === 0}
		<div class="empty-state">
			<div class="empty-icon" aria-hidden="true">
				<svg viewBox="0 0 64 64" width="64" height="64" fill="none">
					<circle cx="32" cy="32" r="20" fill="var(--color-dm)" opacity="0.1" />
					<path
						d="M32 18 L28 32 L32 30 L36 32 Z"
						fill="var(--color-dm)"
						opacity="0.3"
					/>
					<circle cx="32" cy="40" r="6" fill="var(--color-dm)" opacity="0.15" />
					<text
						x="32"
						y="43"
						text-anchor="middle"
						fill="var(--color-dm)"
						font-size="10"
						opacity="0.4">?</text
					>
				</svg>
			</div>
			<h3 class="empty-title">No characters yet</h3>
			<p class="empty-subtitle">Create your first character to begin building your party.</p>
		</div>

	<!-- Character grid -->
	{:else}
		<div class="card-grid">
			{#each filteredCharacters as character (character.name)}
				<!-- svelte-ignore a11y_no_static_element_interactions -->
				<div
					class="character-card"
					style="--card-accent: {character.color || classColor(character.character_class)}"
					onclick={() => onSelect(character)}
					onkeydown={(e) => handleCardKeydown(e, character)}
					role="button"
					tabindex="0"
					aria-label="View {sanitize(character.name)}, {sanitize(character.character_class)}"
				>
					<div class="card-accent"></div>
					<div class="card-body">
						<div class="card-top">
							<h3 class="card-name">{sanitize(character.name)}</h3>
							<span
								class="source-badge"
								class:preset={character.source === 'preset'}
								class:custom={character.source === 'library'}
							>
								{character.source === 'preset' ? 'Preset' : 'Custom'}
							</span>
						</div>
						<p class="card-class" style="color: {character.color || classColor(character.character_class)}">
							{sanitize(character.character_class)}
						</p>
						<p class="card-personality">{sanitize(truncate(character.personality, 100))}</p>
					</div>
				</div>
			{/each}
		</div>

		{#if filteredCharacters.length === 0 && searchQuery.trim()}
			<p class="no-results">No matching characters</p>
		{/if}
	{/if}
</div>

<style>
	.character-library {
		max-width: var(--max-content-width);
		margin: 0 auto;
	}

	/* Header */
	.library-header {
		margin-bottom: var(--space-lg);
	}

	.header-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--space-md);
		margin-bottom: var(--space-xs);
	}

	.library-title {
		font-family: var(--font-narrative);
		font-size: 28px;
		font-weight: 600;
		color: var(--color-dm);
		margin: 0;
	}

	.library-stats {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
		margin: 0;
	}

	/* Search */
	.search-wrapper {
		position: relative;
		margin-bottom: var(--space-lg);
	}

	.search-icon {
		position: absolute;
		left: 12px;
		top: 50%;
		transform: translateY(-50%);
		color: var(--text-secondary);
		opacity: 0.6;
		pointer-events: none;
	}

	.search-input {
		width: 100%;
		background: var(--bg-secondary);
		color: var(--text-primary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm) var(--space-md);
		padding-left: 36px;
		font-family: var(--font-ui);
		font-size: var(--text-ui);
	}

	.search-input:focus {
		outline: 2px solid var(--accent-warm);
		outline-offset: 1px;
		border-color: transparent;
	}

	.search-input::placeholder {
		color: var(--text-secondary);
		opacity: 0.6;
	}

	/* Card grid */
	.card-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
		gap: var(--space-md);
	}

	/* Character card */
	.character-card {
		background: var(--bg-secondary);
		border-radius: var(--border-radius-md);
		overflow: hidden;
		cursor: pointer;
		transition:
			background var(--transition-fast),
			transform var(--transition-fast);
	}

	.character-card:hover {
		background: var(--bg-message);
		transform: translateY(-2px);
	}

	.character-card:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.card-accent {
		height: 3px;
		background: var(--card-accent);
	}

	.card-body {
		padding: var(--space-md);
	}

	.card-top {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-sm);
		margin-bottom: var(--space-xs);
	}

	.card-name {
		font-family: var(--font-narrative);
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
		line-height: 1.3;
	}

	.source-badge {
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		padding: 2px 6px;
		border-radius: 3px;
		flex-shrink: 0;
		white-space: nowrap;
	}

	.source-badge.preset {
		background: rgba(212, 165, 116, 0.15);
		color: var(--color-dm);
	}

	.source-badge.custom {
		background: rgba(107, 142, 107, 0.15);
		color: var(--color-success);
	}

	.card-class {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 600;
		margin: 0 0 var(--space-sm) 0;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}

	.card-personality {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
		line-height: 1.4;
		margin: 0;
	}

	/* Buttons */
	.btn {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		font-weight: 500;
		padding: 8px 16px;
		border-radius: var(--border-radius-sm);
		border: none;
		cursor: pointer;
		transition:
			background var(--transition-fast),
			opacity var(--transition-fast);
		display: inline-flex;
		align-items: center;
		gap: 6px;
	}

	.btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.btn-primary {
		background: var(--accent-warm);
		color: var(--bg-primary);
	}

	.btn-primary:hover:not(:disabled) {
		background: var(--accent-warm-hover);
	}

	/* No results */
	.no-results {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-secondary);
		text-align: center;
		padding: var(--space-xl) 0;
	}

	/* Skeleton loading */
	.skeleton-card {
		background: var(--bg-secondary);
		border-radius: var(--border-radius-md);
		padding: var(--space-md);
		padding-top: calc(var(--space-md) + 3px);
	}

	.skeleton-line {
		background: var(--bg-message);
		border-radius: var(--border-radius-sm);
		animation: pulse 1.5s ease-in-out infinite;
	}

	.skeleton-name {
		height: 18px;
		width: 60%;
		margin-bottom: var(--space-sm);
	}

	.skeleton-class {
		height: 14px;
		width: 30%;
		margin-bottom: var(--space-sm);
	}

	.skeleton-personality {
		height: 14px;
		width: 80%;
	}

	/* Empty state */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		min-height: 40vh;
		gap: var(--space-md);
	}

	.empty-icon {
		margin-bottom: var(--space-sm);
		opacity: 0.8;
	}

	.empty-title {
		font-family: var(--font-narrative);
		font-size: 20px;
		font-weight: 600;
		color: var(--text-secondary);
		margin: 0;
	}

	.empty-subtitle {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-secondary);
		margin: 0;
		max-width: 320px;
	}

	/* Animations */
	@keyframes pulse {
		0%,
		100% {
			opacity: 0.3;
		}
		50% {
			opacity: 0.7;
		}
	}

	/* Responsive */
	@media (max-width: 768px) {
		.card-grid {
			grid-template-columns: 1fr;
		}

		.header-top {
			flex-wrap: wrap;
		}

		.library-title {
			font-size: 24px;
		}
	}
</style>
