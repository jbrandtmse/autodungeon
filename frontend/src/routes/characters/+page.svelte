<script lang="ts">
	/**
	 * Characters route page — composes library, detail, and creator views.
	 * Story 16-9: Character Creation & Library.
	 */
	import { onMount } from 'svelte';
	import {
		getCharacters,
		getCharacter,
		createCharacter,
		updateCharacter,
		deleteCharacter,
		ApiError,
	} from '$lib/api';
	import type { Character, CharacterDetail, CharacterCreateRequest } from '$lib/types';
	import CharacterLibrary from '$lib/components/CharacterLibrary.svelte';
	import CharacterDetailView from '$lib/components/CharacterDetail.svelte';
	import CharacterCreator from '$lib/components/CharacterCreator.svelte';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';

	type ViewMode = 'library' | 'detail' | 'create' | 'edit';

	let viewMode = $state<ViewMode>('library');
	let characters = $state<Character[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let selectedCharacter = $state<CharacterDetail | null>(null);
	let editingCharacter = $state<CharacterDetail | null>(null);
	let saving = $state(false);
	let saveError = $state<string | null>(null);
	let confirmDeleteCharacter = $state<CharacterDetail | null>(null);
	let deleteError = $state<string | null>(null);
	let deleting = $state(false);
	let successMessage = $state<string | null>(null);
	let successTimer: ReturnType<typeof setTimeout> | undefined;

	async function loadCharacters(): Promise<void> {
		loading = true;
		error = null;
		try {
			characters = await getCharacters();
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to load characters';
		} finally {
			loading = false;
		}
	}

	async function handleSelect(character: Character): Promise<void> {
		try {
			selectedCharacter = await getCharacter(character.name);
			viewMode = 'detail';
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'Failed to load character details';
		}
	}

	function handleCreate(): void {
		editingCharacter = null;
		saveError = null;
		viewMode = 'create';
	}

	function handleEdit(character: CharacterDetail): void {
		editingCharacter = character;
		saveError = null;
		viewMode = 'edit';
	}

	function handleDeleteRequest(character: CharacterDetail): void {
		confirmDeleteCharacter = character;
		deleteError = null;
	}

	async function handleDeleteConfirm(): Promise<void> {
		if (!confirmDeleteCharacter) return;
		deleting = true;
		deleteError = null;
		try {
			await deleteCharacter(confirmDeleteCharacter.name);
			showSuccess(`${confirmDeleteCharacter.name} deleted`);
			confirmDeleteCharacter = null;
			selectedCharacter = null;
			viewMode = 'library';
			await loadCharacters();
		} catch (e) {
			deleteError = e instanceof ApiError ? e.message : 'Failed to delete character';
		} finally {
			deleting = false;
		}
	}

	function handleDeleteCancel(): void {
		confirmDeleteCharacter = null;
		deleteError = null;
	}

	async function handleSaveCreate(data: CharacterCreateRequest): Promise<void> {
		saving = true;
		saveError = null;
		try {
			await createCharacter(data);
			showSuccess(`${data.name} created`);
			viewMode = 'library';
			await loadCharacters();
		} catch (e) {
			saveError = e instanceof ApiError ? e.message : 'Failed to create character';
		} finally {
			saving = false;
		}
	}

	async function handleSaveEdit(data: CharacterCreateRequest): Promise<void> {
		if (!editingCharacter) return;
		saving = true;
		saveError = null;
		try {
			await updateCharacter(editingCharacter.name, data);
			showSuccess(`${data.name} updated`);
			editingCharacter = null;
			viewMode = 'library';
			await loadCharacters();
		} catch (e) {
			saveError = e instanceof ApiError ? e.message : 'Failed to update character';
		} finally {
			saving = false;
		}
	}

	function handleCancel(): void {
		editingCharacter = null;
		saveError = null;
		viewMode = selectedCharacter ? 'detail' : 'library';
	}

	async function handleModelConfigSaved(updated: CharacterDetail): Promise<void> {
		selectedCharacter = updated;
		showSuccess(`${updated.name} model config updated`);
		await loadCharacters();
	}

	function handleBackToLibrary(): void {
		selectedCharacter = null;
		viewMode = 'library';
	}

	function showSuccess(msg: string): void {
		if (successTimer) clearTimeout(successTimer);
		successMessage = msg;
		successTimer = setTimeout(() => {
			successMessage = null;
		}, 3000);
	}

	onMount(() => {
		loadCharacters();
		return () => {
			if (successTimer) clearTimeout(successTimer);
		};
	});
</script>

<div class="characters-page">
	<!-- Success toast -->
	{#if successMessage}
		<div class="toast toast-success" role="status">{successMessage}</div>
	{/if}

	<!-- Error banner -->
	{#if error && viewMode === 'library'}
		<div class="error-banner" role="alert">
			<p class="error-text">{error}</p>
			<button class="btn btn-primary" onclick={loadCharacters}>Retry</button>
		</div>
	{/if}

	<!-- View modes -->
	{#if viewMode === 'library'}
		<CharacterLibrary
			{characters}
			{loading}
			onSelect={handleSelect}
			onCreate={handleCreate}
		/>
	{:else if viewMode === 'detail' && selectedCharacter}
		<CharacterDetailView
			character={selectedCharacter}
			onBack={handleBackToLibrary}
			onEdit={handleEdit}
			onDelete={handleDeleteRequest}
			onModelConfigSaved={handleModelConfigSaved}
		/>
	{:else if viewMode === 'create'}
		<CharacterCreator
			onSave={handleSaveCreate}
			onCancel={handleCancel}
			{saving}
			error={saveError}
		/>
	{:else if viewMode === 'edit' && editingCharacter}
		<CharacterCreator
			editCharacter={editingCharacter}
			onSave={handleSaveEdit}
			onCancel={handleCancel}
			{saving}
			error={saveError}
		/>
	{/if}
</div>

<!-- Delete confirmation dialog -->
<ConfirmDialog
	open={confirmDeleteCharacter !== null}
	title="Delete this character?"
	message={confirmDeleteCharacter
		? `"${confirmDeleteCharacter.name}" will be permanently removed from your library.`
		: ''}
	confirmLabel={deleting ? 'Deleting...' : 'Delete'}
	confirmDanger={true}
	onConfirm={handleDeleteConfirm}
	onCancel={handleDeleteCancel}
	error={deleteError}
/>

<style>
	.characters-page {
		padding: var(--space-md) 0;
	}

	/* Toast */
	.toast {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		padding: var(--space-sm) var(--space-md);
		border-radius: var(--border-radius-sm);
		margin-bottom: var(--space-md);
		max-width: var(--max-content-width);
		margin-left: auto;
		margin-right: auto;
		animation: fadeIn 0.2s ease;
	}

	.toast-success {
		background: rgba(107, 142, 107, 0.15);
		color: var(--color-success);
		border: 1px solid rgba(107, 142, 107, 0.3);
	}

	/* Error banner */
	.error-banner {
		text-align: center;
		padding: var(--space-xl) 0;
		max-width: var(--max-content-width);
		margin: 0 auto;
	}

	.error-text {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--color-error);
		margin-bottom: var(--space-md);
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
	}

	.btn:focus-visible {
		outline: 2px solid var(--accent-warm);
		outline-offset: 2px;
	}

	.btn-primary {
		background: var(--accent-warm);
		color: var(--bg-primary);
	}

	.btn-primary:hover {
		background: var(--accent-warm-hover);
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}
</style>
