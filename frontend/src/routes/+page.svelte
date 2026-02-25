<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { getSessions, createSession, deleteSession, ApiError } from '$lib/api';
	import type { Session } from '$lib/types';
	import SessionCard from '$lib/components/SessionCard.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import GalleryModal from '$lib/components/GalleryModal.svelte';
	import {
		galleryOpen,
		loadSessionImages,
		loadSessionImageSummaries,
		sessionImageSummaries,
		resetImageStore,
	} from '$lib/stores/imageStore';

	let sessions = $state<Session[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let searchQuery = $state('');
	let showCreateForm = $state(false);
	let newSessionName = $state('');
	let creating = $state(false);
	let createError = $state<string | null>(null);
	let deletingId = $state<string | null>(null);
	let confirmDeleteSession = $state<Session | null>(null);
	let deleteError = $state<string | null>(null);
	let successMessage = $state<string | null>(null);
	let successTimer: ReturnType<typeof setTimeout> | undefined;

	let filteredSessions = $derived(
		searchQuery.trim()
			? sessions.filter(
					(s) =>
						s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
						s.session_id.toLowerCase().includes(searchQuery.toLowerCase()),
				)
			: sessions,
	);

	// Image count lookup map, derived from session summaries
	let imageCounts = $derived(
		new Map($sessionImageSummaries.map((s) => [s.session_id, s.image_count]))
	);

	async function openGalleryForSession(sessionId: string): Promise<void> {
		await loadSessionImages(sessionId);
		galleryOpen.set(true);
	}

	async function loadSessions(): Promise<void> {
		loading = true;
		error = null;
		try {
			sessions = await getSessions();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to load sessions';
		} finally {
			loading = false;
		}
	}

	async function handleCreate(): Promise<void> {
		creating = true;
		createError = null;
		try {
			const result = await createSession(newSessionName.trim() || undefined);
			newSessionName = '';
			showCreateForm = false;
			goto(`/setup/${encodeURIComponent(result.session_id)}`);
		} catch (e) {
			createError = e instanceof ApiError ? e.message : 'Failed to create session';
		} finally {
			creating = false;
		}
	}

	function requestDelete(sessionId: string): void {
		const session = sessions.find((s) => s.session_id === sessionId);
		if (session) {
			confirmDeleteSession = session;
			deleteError = null;
		}
	}

	async function handleDelete(): Promise<void> {
		if (!confirmDeleteSession) return;
		const sessionId = confirmDeleteSession.session_id;
		deletingId = sessionId;
		deleteError = null;
		try {
			await deleteSession(sessionId);
			sessions = sessions.filter((s) => s.session_id !== sessionId);
			confirmDeleteSession = null;
			showSuccess('Adventure deleted');
		} catch (e) {
			deleteError = e instanceof ApiError ? e.message : 'Failed to delete session';
		} finally {
			deletingId = null;
		}
	}

	function cancelDelete(): void {
		confirmDeleteSession = null;
		deleteError = null;
	}

	function showSuccess(msg: string): void {
		if (successTimer) clearTimeout(successTimer);
		successMessage = msg;
		successTimer = setTimeout(() => {
			successMessage = null;
		}, 3000);
	}

	function handleCreateKeydown(e: KeyboardEvent): void {
		if (e.key === 'Enter') {
			e.preventDefault();
			handleCreate();
		}
		if (e.key === 'Escape') {
			e.preventDefault();
			showCreateForm = false;
			newSessionName = '';
			createError = null;
		}
	}

	function openCreateForm(): void {
		showCreateForm = true;
		createError = null;
		newSessionName = '';
	}

	function cancelCreate(): void {
		showCreateForm = false;
		newSessionName = '';
		createError = null;
	}

	onMount(() => {
		loadSessions();
		loadSessionImageSummaries();
	});

	onDestroy(() => {
		if (successTimer) clearTimeout(successTimer);
		resetImageStore();
	});
</script>

<div class="session-browser">
	<!-- Header -->
	<header class="browser-header">
		<h2 class="browser-title">Your Adventures</h2>
		{#if !loading && sessions.length > 0 && !showCreateForm}
			<button class="btn btn-primary" onclick={openCreateForm}>+ New Adventure</button>
		{/if}
	</header>

	<!-- Success toast -->
	{#if successMessage}
		<div class="toast toast-success" role="status">{successMessage}</div>
	{/if}

	<!-- Create form -->
	{#if showCreateForm}
		<div class="create-form">
			<input
				type="text"
				class="create-input"
				placeholder="Name your adventure..."
				bind:value={newSessionName}
				onkeydown={handleCreateKeydown}
				disabled={creating}
			/>
			<div class="create-actions">
				<button class="btn btn-secondary" onclick={cancelCreate} disabled={creating}>
					Cancel
				</button>
				<button class="btn btn-primary" onclick={handleCreate} disabled={creating}>
					{#if creating}
						<span class="spinner" aria-hidden="true"></span>
						Creating...
					{:else}
						Create
					{/if}
				</button>
			</div>
			{#if createError}
				<p class="inline-error" role="alert">{createError}</p>
			{/if}
		</div>
	{/if}

	<!-- Loading state -->
	{#if loading}
		<div class="skeleton-list" aria-label="Loading sessions">
			{#each [1, 2, 3] as i (i)}
				<div class="skeleton-card">
					<div class="skeleton-line skeleton-title"></div>
					<div class="skeleton-line skeleton-name"></div>
					<div class="skeleton-line skeleton-meta"></div>
				</div>
			{/each}
		</div>

	<!-- Error state -->
	{:else if error}
		<div class="error-state" role="alert">
			<p class="error-message">{error}</p>
			<button class="btn btn-primary" onclick={loadSessions}>Retry</button>
		</div>

	<!-- Empty state -->
	{:else if sessions.length === 0}
		<div class="empty-state">
			<div class="empty-icon" aria-hidden="true">
				<svg viewBox="0 0 64 64" width="64" height="64" fill="none">
					<circle cx="32" cy="48" r="12" fill="var(--color-dm)" opacity="0.15" />
					<path d="M32 20 L26 44 L32 40 L38 44 Z" fill="var(--color-dm)" opacity="0.4" />
					<path d="M22 44 L18 48 L24 46 Z" fill="var(--accent-warm)" opacity="0.3" />
					<path d="M42 44 L46 48 L40 46 Z" fill="var(--accent-warm)" opacity="0.3" />
					<circle cx="27" cy="36" r="1.5" fill="var(--accent-warm)" opacity="0.6" />
					<circle cx="37" cy="32" r="1" fill="var(--accent-warm)" opacity="0.5" />
					<circle cx="32" cy="28" r="1.2" fill="var(--accent-warm)" opacity="0.7" />
				</svg>
			</div>
			<h3 class="empty-title">No adventures yet</h3>
			<p class="empty-subtitle">Start your first adventure and let the story unfold.</p>
			{#if !showCreateForm}
				<button class="btn btn-primary btn-lg" onclick={openCreateForm}>
					+ New Adventure
				</button>
			{/if}
		</div>

	<!-- Session list -->
	{:else}
		<!-- Search input -->
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
				placeholder="Search adventures..."
				bind:value={searchQuery}
				aria-label="Search adventures"
			/>
		</div>

		<!-- Session cards -->
		<div class="session-list">
			{#each filteredSessions as session (session.session_id)}
				<SessionCard
					{session}
					deleting={deletingId === session.session_id}
					onDelete={requestDelete}
					imageCount={imageCounts.get(session.session_id) ?? 0}
					onOpenGallery={openGalleryForSession}
				/>
			{/each}
		</div>

		<!-- No search results -->
		{#if filteredSessions.length === 0 && searchQuery.trim()}
			<p class="no-results">No matching adventures</p>
		{/if}
	{/if}
</div>

<!-- Delete confirmation dialog -->
<ConfirmDialog
	open={confirmDeleteSession !== null}
	title="Delete this adventure?"
	message="This cannot be undone."
	confirmLabel="Delete"
	confirmDanger={true}
	onConfirm={handleDelete}
	onCancel={cancelDelete}
	error={deleteError}
/>
<GalleryModal />

<style>
	.session-browser {
		max-width: var(--max-content-width);
		margin: 0 auto;
		padding: var(--space-md) 0;
	}

	/* Header */
	.browser-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--space-lg);
		gap: var(--space-md);
	}

	.browser-title {
		font-family: var(--font-narrative);
		font-size: 28px;
		font-weight: 600;
		color: var(--color-dm);
		margin: 0;
	}

	/* Toast */
	.toast {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		padding: var(--space-sm) var(--space-md);
		border-radius: var(--border-radius-sm);
		margin-bottom: var(--space-md);
		animation: fadeIn 0.2s ease;
	}

	.toast-success {
		background: rgba(107, 142, 107, 0.15);
		color: var(--color-success);
		border: 1px solid rgba(107, 142, 107, 0.3);
	}

	/* Create form */
	.create-form {
		background: var(--bg-secondary);
		border-radius: var(--border-radius-md);
		padding: var(--space-md);
		margin-bottom: var(--space-lg);
		animation: slideDown 0.15s ease;
	}

	.create-input {
		width: 100%;
		background: var(--bg-primary);
		color: var(--text-primary);
		border: 1px solid rgba(184, 168, 150, 0.2);
		border-radius: var(--border-radius-sm);
		padding: var(--space-sm) var(--space-md);
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		margin-bottom: var(--space-sm);
	}

	.create-input:focus {
		outline: 2px solid var(--accent-warm);
		outline-offset: 1px;
		border-color: transparent;
	}

	.create-input::placeholder {
		color: var(--text-secondary);
		opacity: 0.6;
	}

	.create-input:disabled {
		opacity: 0.5;
	}

	.create-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-sm);
	}

	.inline-error {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--color-error);
		margin-top: var(--space-sm);
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

	.btn-secondary {
		background: transparent;
		color: var(--text-secondary);
		border: 1px solid rgba(184, 168, 150, 0.3);
	}

	.btn-secondary:hover:not(:disabled) {
		background: var(--bg-message);
		color: var(--text-primary);
	}

	.btn-lg {
		padding: 12px 24px;
		font-size: 16px;
	}

	/* Spinner */
	.spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid currentColor;
		border-right-color: transparent;
		border-radius: 50%;
		animation: spin 0.6s linear infinite;
	}

	/* Search */
	.search-wrapper {
		position: relative;
		margin-bottom: var(--space-md);
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

	/* Session list */
	.session-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
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
	.skeleton-list {
		display: flex;
		flex-direction: column;
		gap: var(--space-md);
	}

	.skeleton-card {
		background: var(--bg-secondary);
		border-radius: var(--border-radius-md);
		border-left: 3px solid var(--color-dm);
		padding: var(--space-md);
	}

	.skeleton-line {
		background: var(--bg-message);
		border-radius: var(--border-radius-sm);
		animation: pulse 1.5s ease-in-out infinite;
	}

	.skeleton-title {
		height: 20px;
		width: 40%;
		margin-bottom: var(--space-sm);
	}

	.skeleton-name {
		height: 16px;
		width: 60%;
		margin-bottom: var(--space-sm);
	}

	.skeleton-meta {
		height: 14px;
		width: 35%;
	}

	/* Error state */
	.error-state {
		text-align: center;
		padding: var(--space-2xl) 0;
	}

	.error-message {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--color-error);
		margin-bottom: var(--space-md);
	}

	/* Empty state */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		min-height: 50vh;
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

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	@keyframes slideDown {
		from {
			opacity: 0;
			transform: translateY(-8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	/* Responsive: small desktop */
	@media (max-width: 1024px) {
		.session-browser {
			padding: var(--space-sm) 0;
		}
	}

	/* Responsive: mobile */
	@media (max-width: 768px) {
		.session-browser {
			padding: var(--space-xs) 0;
		}

		.browser-header {
			flex-wrap: wrap;
		}

		.browser-title {
			font-size: 24px;
		}

		.create-actions {
			flex-direction: column-reverse;
		}

		.create-actions .btn {
			width: 100%;
			justify-content: center;
		}
	}
</style>
