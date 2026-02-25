<script lang="ts">
	import { goto } from '$app/navigation';
	import type { Session } from '$lib/types';
	import { toRomanNumeral, formatSessionDate } from '$lib/format';

	interface Props {
		session: Session;
		deleting?: boolean;
		onDelete: (sessionId: string) => void;
		imageCount?: number;
		onOpenGallery?: (sessionId: string) => void;
	}

	let { session, deleting = false, onDelete, imageCount = 0, onOpenGallery }: Props = $props();

	let displayName = $derived(session.name || 'Unnamed Adventure');

	let characterDisplay = $derived.by(() => {
		const names = session.character_names;
		if (names.length === 0) return '';
		if (names.length <= 3) return names.join(', ');
		return `${names.slice(0, 3).join(', ')} +${names.length - 3} more`;
	});

	function handleCardClick(): void {
		if (deleting) return;
		goto(`/game/${encodeURIComponent(session.session_id)}`);
	}

	function handleDelete(e: MouseEvent): void {
		e.stopPropagation();
		onDelete(session.session_id);
	}

	function handleKeydown(e: KeyboardEvent): void {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			handleCardClick();
		}
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="session-card"
	class:deleting
	onclick={handleCardClick}
	onkeydown={handleKeydown}
	role="button"
	tabindex="0"
	aria-label="Resume session {toRomanNumeral(session.session_number)}: {displayName}"
>
	<div class="card-header">
		<h3 class="session-title">Session {toRomanNumeral(session.session_number)}</h3>
		<div class="card-actions">
			{#if imageCount > 0 && onOpenGallery}
				<button
					class="gallery-btn"
					onclick={(e) => { e.stopPropagation(); onOpenGallery(session.session_id); }}
					aria-label="View {imageCount} illustrations for {displayName}"
					title="{imageCount} illustrations"
				>
					<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
						<rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
						<circle cx="8.5" cy="8.5" r="1.5" />
						<polyline points="21 15 16 10 5 21" />
					</svg>
					<span class="gallery-badge">{imageCount}</span>
				</button>
			{/if}
			<button
				class="delete-btn"
				onclick={handleDelete}
				disabled={deleting}
				aria-label="Delete session {displayName}"
				title="Delete session"
			>
				<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
					<polyline points="3 6 5 6 21 6" />
					<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
					<line x1="10" y1="11" x2="10" y2="17" />
					<line x1="14" y1="11" x2="14" y2="17" />
				</svg>
			</button>
		</div>
	</div>

	<p class="session-name">{displayName}</p>

	<div class="session-meta">
		<span class="meta-item">{formatSessionDate(session.updated_at)}</span>
		<span class="meta-separator">&middot;</span>
		<span class="meta-item">{session.turn_count} {session.turn_count === 1 ? 'turn' : 'turns'}</span>
	</div>

	{#if characterDisplay}
		<p class="session-characters">{characterDisplay}</p>
	{/if}
</div>

<style>
	.session-card {
		background: var(--bg-secondary);
		border-radius: var(--border-radius-md);
		border-left: 3px solid var(--color-dm);
		padding: var(--space-md);
		cursor: pointer;
		transition:
			background var(--transition-fast),
			transform var(--transition-fast),
			opacity var(--transition-fast);
	}

	.session-card:hover {
		background: var(--bg-message);
		transform: translateY(-1px);
	}

	.session-card:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.session-card.deleting {
		opacity: 0.5;
		pointer-events: none;
	}

	.card-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: var(--space-sm);
	}

	.session-title {
		font-family: var(--font-narrative);
		font-size: 18px;
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}

	.card-actions {
		display: flex;
		align-items: center;
		gap: 4px;
		flex-shrink: 0;
	}

	.gallery-btn {
		display: flex;
		align-items: center;
		gap: 2px;
		background: transparent;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 4px;
		border-radius: var(--border-radius-sm);
		transition:
			color var(--transition-fast),
			background var(--transition-fast);
		font-family: var(--font-mono);
		font-size: 11px;
	}

	.gallery-btn:hover {
		color: var(--accent-warm);
		background: rgba(232, 168, 73, 0.1);
	}

	.gallery-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.gallery-badge {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--accent-warm);
	}

	.delete-btn {
		background: transparent;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: 4px;
		border-radius: var(--border-radius-sm);
		transition:
			color var(--transition-fast),
			background var(--transition-fast);
	}

	.delete-btn:hover {
		color: var(--color-error);
		background: rgba(196, 92, 74, 0.1);
	}

	.delete-btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.delete-btn:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.session-name {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-secondary);
		margin: var(--space-xs) 0;
	}

	.session-meta {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-top: var(--space-xs);
	}

	.meta-item {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
	}

	.meta-separator {
		color: var(--text-secondary);
		opacity: 0.5;
		font-size: var(--text-system);
	}

	.session-characters {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--text-secondary);
		margin-top: var(--space-xs);
		font-style: italic;
	}
</style>
