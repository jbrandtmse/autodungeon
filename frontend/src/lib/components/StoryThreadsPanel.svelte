<script lang="ts">
	import { gameState } from '$lib/stores';
	import type { NarrativeElement, CallbackEntry } from '$lib/types';

	const elements = $derived(
		($gameState?.callback_database?.elements ?? []) as NarrativeElement[]
	);
	const callbackEntries = $derived(
		($gameState?.callback_log?.entries ?? []) as CallbackEntry[]
	);

	const activeElements = $derived(
		elements.filter((e) => !e.dormant && !e.resolved)
			.sort((a, b) => b.times_referenced - a.times_referenced)
	);
	const dormantElements = $derived(
		elements.filter((e) => e.dormant)
	);
	const storyMoments = $derived(
		callbackEntries.filter((e) => e.is_story_moment)
	);

	let expandedId = $state<string | null>(null);

	function toggleExpand(id: string): void {
		expandedId = expandedId === id ? null : id;
	}

	function getCallbacksForElement(elementId: string): CallbackEntry[] {
		return callbackEntries.filter((e) => e.element_id === elementId);
	}

	function truncate(text: string, maxLen: number): string {
		if (text.length <= maxLen) return text;
		return text.slice(0, maxLen) + '...';
	}

	function matchTypeLabel(matchType: string): string {
		switch (matchType) {
			case 'name_exact':
				return 'exact name match';
			case 'name_fuzzy':
				return 'fuzzy name match';
			case 'description_keyword':
				return 'keyword match';
			default:
				return matchType;
		}
	}

	const typeBadgeColors: Record<string, string> = {
		character: '#C45C4A',
		item: '#E8A849',
		location: '#6B8E6B',
		event: '#7B68B8',
		promise: '#4A90A4',
		threat: '#C45C4A',
	};
</script>

<div class="story-threads-panel">
	{#if elements.length === 0}
		<p class="empty-text">No narrative elements tracked yet</p>
	{:else}
		<div class="summary-bar">
			<span class="summary-stat">{activeElements.length} Active</span>
			<span class="summary-divider">|</span>
			<span class="summary-stat">{dormantElements.length} Dormant</span>
			<span class="summary-divider">|</span>
			<span class="summary-stat">{storyMoments.length} Story Moments</span>
		</div>

		<!-- Active Elements -->
		{#each activeElements as element (element.id)}
			<button
				class="element-card"
				onclick={() => toggleExpand(element.id)}
				aria-expanded={expandedId === element.id}
			>
				<div class="element-header">
					<span
						class="type-badge"
						style="background: {typeBadgeColors[element.element_type] ?? 'var(--text-secondary)'}20; color: {typeBadgeColors[element.element_type] ?? 'var(--text-secondary)'}"
					>
						{element.element_type}
					</span>
					<span class="element-name">{element.name}</span>
				</div>
				<p class="element-desc">{truncate(element.description, 80)}</p>
				<div class="element-meta">
					<span>Referenced {element.times_referenced} times</span>
					{#if element.characters_involved.length > 0}
						<span class="meta-sep">|</span>
						<span>{element.characters_involved.join(', ')}</span>
					{/if}
				</div>
			</button>

			{#if expandedId === element.id}
				{@const elementCallbacks = getCallbacksForElement(element.id)}
				<div class="element-detail">
					<p class="detail-desc">{element.description}</p>
					{#if element.potential_callbacks.length > 0}
						<div class="detail-section">
							<h4 class="detail-heading">Potential Callbacks</h4>
							<ul class="callback-list">
								{#each element.potential_callbacks as cb}
									<li>{cb}</li>
								{/each}
							</ul>
						</div>
					{/if}

					<!-- Callback Timeline -->
					<div class="detail-section">
						<h4 class="detail-heading">Callback Timeline</h4>
						<div class="timeline">
							<div class="timeline-entry">
								<span class="timeline-dot"></span>
								<span class="timeline-text">
									Introduced in Turn {element.turn_introduced}, Session {element.session_introduced}
								</span>
							</div>
							{#each elementCallbacks as entry (entry.id)}
								<div class="timeline-entry" class:story-moment={entry.is_story_moment}>
									<span class="timeline-dot" class:story-moment-dot={entry.is_story_moment}></span>
									<div class="timeline-content">
										<span class="timeline-turn">Turn {entry.turn_detected}</span>
										<span class="timeline-match">{matchTypeLabel(entry.match_type)}</span>
										{#if entry.match_context}
											<p class="timeline-context">{entry.match_context}</p>
										{/if}
										{#if entry.is_story_moment}
											<span class="story-moment-label">{entry.turn_gap} turn gap</span>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					</div>
				</div>
			{/if}
		{/each}

		<!-- Dormant Elements -->
		{#if dormantElements.length > 0}
			<div class="dormant-divider">Dormant</div>
			{#each dormantElements as element (element.id)}
				<button
					class="element-card dormant"
					onclick={() => toggleExpand(element.id)}
					aria-expanded={expandedId === element.id}
				>
					<div class="element-header">
						<span
							class="type-badge"
							style="background: {typeBadgeColors[element.element_type] ?? 'var(--text-secondary)'}10; color: {typeBadgeColors[element.element_type] ?? 'var(--text-secondary)'}"
						>
							{element.element_type}
						</span>
						<span class="element-name">{element.name}</span>
					</div>
					<p class="element-desc">{truncate(element.description, 80)}</p>
					<div class="element-meta">
						<span>Referenced {element.times_referenced} times</span>
					</div>
				</button>

				{#if expandedId === element.id}
					{@const elementCallbacks = getCallbacksForElement(element.id)}
					<div class="element-detail">
						<p class="detail-desc">{element.description}</p>
						{#if elementCallbacks.length > 0}
							<div class="detail-section">
								<h4 class="detail-heading">Callback Timeline</h4>
								<div class="timeline">
									<div class="timeline-entry">
										<span class="timeline-dot"></span>
										<span class="timeline-text">
											Introduced in Turn {element.turn_introduced}, Session {element.session_introduced}
										</span>
									</div>
									{#each elementCallbacks as entry (entry.id)}
										<div class="timeline-entry" class:story-moment={entry.is_story_moment}>
											<span class="timeline-dot" class:story-moment-dot={entry.is_story_moment}></span>
											<div class="timeline-content">
												<span class="timeline-turn">Turn {entry.turn_detected}</span>
												<span class="timeline-match">{matchTypeLabel(entry.match_type)}</span>
												{#if entry.match_context}
													<p class="timeline-context">{entry.match_context}</p>
												{/if}
											</div>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{/if}
			{/each}
		{/if}
	{/if}
</div>

<style>
	.story-threads-panel {
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
		font-family: var(--font-ui);
	}

	.empty-text {
		font-size: var(--text-system);
		color: var(--text-secondary);
		font-style: italic;
		padding: var(--space-sm) 0;
	}

	.summary-bar {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 11px;
		color: var(--text-secondary);
		padding: var(--space-xs) 0;
	}

	.summary-stat {
		font-weight: 600;
	}

	.summary-divider {
		opacity: 0.4;
	}

	.element-card {
		width: 100%;
		background: var(--bg-secondary);
		border: 1px solid rgba(184, 168, 150, 0.1);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm);
		cursor: pointer;
		text-align: left;
		font-family: var(--font-ui);
		transition: background var(--transition-fast);
		display: flex;
		flex-direction: column;
		gap: 4px;
		color: var(--text-primary);
	}

	.element-card:hover {
		background: var(--bg-message);
	}

	.element-card.dormant {
		opacity: 0.6;
	}

	.element-header {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.type-badge {
		font-size: 10px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 1px 6px;
		border-radius: 8px;
		flex-shrink: 0;
	}

	.element-name {
		font-size: 13px;
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.element-desc {
		font-size: 11px;
		color: var(--text-secondary);
		line-height: 1.4;
	}

	.element-meta {
		font-size: 10px;
		color: var(--text-secondary);
		display: flex;
		gap: 4px;
	}

	.meta-sep {
		opacity: 0.4;
	}

	/* Detail Panel */
	.element-detail {
		padding: var(--space-sm);
		padding-left: var(--space-md);
		border-left: 2px solid var(--accent-warm);
		display: flex;
		flex-direction: column;
		gap: var(--space-sm);
	}

	.detail-desc {
		font-size: 12px;
		color: var(--text-primary);
		line-height: 1.5;
	}

	.detail-section {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
	}

	.detail-heading {
		font-size: 11px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.callback-list {
		list-style: disc;
		padding-left: 16px;
		margin: 0;
	}

	.callback-list li {
		font-size: 12px;
		color: var(--text-primary);
		padding: 2px 0;
	}

	/* Timeline */
	.timeline {
		display: flex;
		flex-direction: column;
		gap: var(--space-xs);
		padding-left: 8px;
	}

	.timeline-entry {
		display: flex;
		gap: var(--space-sm);
		align-items: flex-start;
		position: relative;
	}

	.timeline-entry.story-moment {
		border-left: 2px solid var(--accent-warm);
		padding-left: var(--space-sm);
		margin-left: -10px;
	}

	.timeline-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--text-secondary);
		margin-top: 5px;
		flex-shrink: 0;
	}

	.timeline-dot.story-moment-dot {
		background: var(--accent-warm);
	}

	.timeline-text {
		font-size: 11px;
		color: var(--text-secondary);
		font-style: italic;
	}

	.timeline-content {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.timeline-turn {
		font-size: 11px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.timeline-match {
		font-size: 10px;
		color: var(--text-secondary);
		font-style: italic;
	}

	.timeline-context {
		font-size: 11px;
		color: var(--text-primary);
		line-height: 1.4;
	}

	.story-moment-label {
		font-size: 10px;
		font-weight: 600;
		color: var(--accent-warm);
	}

	.dormant-divider {
		font-size: 10px;
		font-weight: 600;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		padding: var(--space-xs) 0;
		border-top: 1px solid rgba(184, 168, 150, 0.1);
		margin-top: var(--space-xs);
	}
</style>
