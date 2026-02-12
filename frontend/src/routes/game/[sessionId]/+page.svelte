<script lang="ts">
	import { page } from '$app/stores';
	import { onMount, onDestroy } from 'svelte';
	import NarrativePanel from '$lib/components/NarrativePanel.svelte';
	import { createGameConnection, type GameConnection } from '$lib/ws';
	import { connectionStatus, lastError, wsSend, sendCommand } from '$lib/stores/connectionStore';
	import { handleServerMessage, resetStores, gameState } from '$lib/stores/gameStore';

	const sessionId = $derived($page.params.sessionId ?? '');

	let connection: GameConnection | undefined;
	let cleanupCallbacks: Array<() => void> = [];

	function handleKeydown(event: KeyboardEvent): void {
		// Skip if user is typing in an input/textarea/select or contentEditable
		const target = event.target as HTMLElement;
		const tag = target?.tagName;
		if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
		if (target?.isContentEditable) return;

		if (event.key >= '1' && event.key <= '4') {
			const index = parseInt(event.key) - 1;
			const characterKeys = Object.keys($gameState?.characters ?? {});
			if (index < characterKeys.length) {
				sendCommand({ type: 'drop_in', character: characterKeys[index] });
			}
		} else if (event.key === 'Escape') {
			if ($gameState?.human_active) {
				sendCommand({ type: 'release_control' });
			}
		}
	}

	onMount(() => {
		if (!sessionId) return;
		resetStores();

		const conn = createGameConnection(sessionId);
		connection = conn;

		// Store cleanup functions returned by on* methods to avoid memory leaks
		cleanupCallbacks.push(
			conn.onConnect(() => {
				connectionStatus.set('connected');
				wsSend.set((cmd) => conn.send(cmd));
			}),
		);

		cleanupCallbacks.push(
			conn.onDisconnect(() => {
				connectionStatus.set('reconnecting');
				wsSend.set(null);
			}),
		);

		cleanupCallbacks.push(
			conn.onMessage((event) => {
				handleServerMessage(event);

				// Capture errors to lastError store
				if (event.type === 'error') {
					lastError.set(event.message);
				}
			}),
		);

		connectionStatus.set('connecting');
		conn.connect();

		// Register keyboard shortcuts
		window.addEventListener('keydown', handleKeydown);
	});

	onDestroy(() => {
		// Remove keyboard shortcut listener
		window.removeEventListener('keydown', handleKeydown);

		// Unsubscribe all callbacks before disconnecting to prevent
		// stale closures firing during in-flight reconnect races
		cleanupCallbacks.forEach((cleanup) => cleanup());
		cleanupCallbacks = [];
		wsSend.set(null);
		connection?.disconnect();
		connectionStatus.set('disconnected');
	});
</script>

<div class="game-view">
	<div class="narrative-area">
		<NarrativePanel />
	</div>
</div>

<style>
	.game-view {
		display: flex;
		flex-direction: column;
		height: calc(100vh - var(--space-lg) * 2);
	}

	.narrative-area {
		flex: 1;
		overflow: hidden;
	}
</style>
