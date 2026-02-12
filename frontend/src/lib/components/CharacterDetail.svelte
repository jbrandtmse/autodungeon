<script lang="ts">
	import type { CharacterDetail } from '$lib/types';

	/**
	 * Full character detail view with edit/delete actions.
	 * Story 16-9: Character Creation & Library.
	 */

	interface Props {
		character: CharacterDetail;
		onBack: () => void;
		onEdit: (character: CharacterDetail) => void;
		onDelete: (character: CharacterDetail) => void;
	}

	let { character, onBack, onEdit, onDelete }: Props = $props();

	let isPreset = $derived(character.source === 'preset');

	function classColor(characterClass: string): string {
		const classMap: Record<string, string> = {
			fighter: 'var(--color-fighter)',
			rogue: 'var(--color-rogue)',
			wizard: 'var(--color-wizard)',
			cleric: 'var(--color-cleric)',
		};
		return classMap[characterClass.toLowerCase()] ?? '#808080';
	}

	function sanitize(text: string): string {
		return text
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;');
	}

	let accentColor = $derived(character.color || classColor(character.character_class));
</script>

<div class="character-detail">
	<!-- Back button -->
	<button class="back-btn" onclick={onBack}>
		<svg
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
			<line x1="19" y1="12" x2="5" y2="12" />
			<polyline points="12 19 5 12 12 5" />
		</svg>
		Back to Library
	</button>

	<!-- Character header -->
	<div class="detail-header" style="--detail-accent: {accentColor}">
		<div class="header-accent"></div>
		<div class="header-content">
			<div class="header-top">
				<div class="header-info">
					<h2 class="detail-name">{sanitize(character.name)}</h2>
					<p class="detail-class" style="color: {accentColor}">
						{sanitize(character.character_class)}
					</p>
				</div>
				<span
					class="source-badge"
					class:preset={isPreset}
					class:custom={!isPreset}
				>
					{isPreset ? 'Preset' : 'Custom'}
				</span>
			</div>
		</div>
	</div>

	<!-- Character details -->
	<div class="detail-sections">
		<!-- Personality -->
		<section class="detail-section">
			<h3 class="section-title">Personality</h3>
			<p class="section-content">{sanitize(character.personality)}</p>
		</section>

		<!-- LLM Configuration -->
		<section class="detail-section">
			<h3 class="section-title">LLM Configuration</h3>
			<div class="config-grid">
				<div class="config-item">
					<span class="config-label">Provider</span>
					<span class="config-value">{sanitize(character.provider)}</span>
				</div>
				<div class="config-item">
					<span class="config-label">Model</span>
					<span class="config-value">{sanitize(character.model)}</span>
				</div>
				<div class="config-item">
					<span class="config-label">Token Limit</span>
					<span class="config-value mono">{character.token_limit.toLocaleString()}</span>
				</div>
				<div class="config-item">
					<span class="config-label">Color</span>
					<span class="config-value">
						<span class="color-swatch" style="background: {accentColor}"></span>
						{sanitize(character.color)}
					</span>
				</div>
			</div>
		</section>
	</div>

	<!-- Actions -->
	{#if !isPreset}
		<div class="detail-actions">
			<button class="btn btn-secondary" onclick={() => onEdit(character)}>
				<svg
					viewBox="0 0 24 24"
					width="14"
					height="14"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
					<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
				</svg>
				Edit Character
			</button>
			<button class="btn btn-danger" onclick={() => onDelete(character)}>
				<svg
					viewBox="0 0 24 24"
					width="14"
					height="14"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					aria-hidden="true"
				>
					<polyline points="3 6 5 6 21 6" />
					<path
						d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
					/>
				</svg>
				Delete Character
			</button>
		</div>
	{/if}
</div>

<style>
	.character-detail {
		max-width: var(--max-content-width);
		margin: 0 auto;
	}

	/* Back button */
	.back-btn {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		background: none;
		border: none;
		color: var(--text-secondary);
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		cursor: pointer;
		padding: var(--space-xs) 0;
		margin-bottom: var(--space-md);
		transition: color var(--transition-fast);
	}

	.back-btn:hover {
		color: var(--text-primary);
	}

	.back-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	/* Header */
	.detail-header {
		background: var(--bg-secondary);
		border-radius: var(--border-radius-md);
		overflow: hidden;
		margin-bottom: var(--space-lg);
	}

	.header-accent {
		height: 4px;
		background: var(--detail-accent);
	}

	.header-content {
		padding: var(--space-lg);
	}

	.header-top {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-md);
	}

	.header-info {
		flex: 1;
	}

	.detail-name {
		font-family: var(--font-narrative);
		font-size: 28px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0 0 var(--space-xs) 0;
	}

	.detail-class {
		font-family: var(--font-ui);
		font-size: 16px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		margin: 0;
	}

	.source-badge {
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		padding: 3px 8px;
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

	/* Sections */
	.detail-sections {
		display: flex;
		flex-direction: column;
		gap: var(--space-lg);
		margin-bottom: var(--space-lg);
	}

	.detail-section {
		background: var(--bg-secondary);
		border-radius: var(--border-radius-md);
		padding: var(--space-lg);
	}

	.section-title {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		margin: 0 0 var(--space-sm) 0;
	}

	.section-content {
		font-family: var(--font-narrative);
		font-size: 16px;
		color: var(--text-primary);
		line-height: 1.6;
		margin: 0;
	}

	/* Config grid */
	.config-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
		gap: var(--space-md);
	}

	.config-item {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.config-label {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
	}

	.config-value {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-primary);
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.config-value.mono {
		font-family: var(--font-mono);
	}

	.color-swatch {
		display: inline-block;
		width: 14px;
		height: 14px;
		border-radius: 3px;
		border: 1px solid rgba(184, 168, 150, 0.3);
		flex-shrink: 0;
	}

	/* Actions */
	.detail-actions {
		display: flex;
		gap: var(--space-sm);
		flex-wrap: wrap;
	}

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

	.btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.btn-secondary {
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid rgba(184, 168, 150, 0.3);
	}

	.btn-secondary:hover {
		background: var(--bg-message);
		color: var(--text-primary);
	}

	.btn-danger {
		background: transparent;
		color: var(--color-error);
		border: 1px solid rgba(196, 92, 74, 0.3);
	}

	.btn-danger:hover {
		background: rgba(196, 92, 74, 0.1);
	}

	/* Responsive */
	@media (max-width: 768px) {
		.detail-name {
			font-size: 24px;
		}

		.config-grid {
			grid-template-columns: 1fr 1fr;
		}

		.detail-actions {
			flex-direction: column;
		}

		.detail-actions .btn {
			justify-content: center;
		}
	}
</style>
