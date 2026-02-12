<script lang="ts">
	import { page } from '$app/stores';
	import { onMount, onDestroy } from 'svelte';
	import NarrativePanel from '$lib/components/NarrativePanel.svelte';
	import { createGameConnection, type GameConnection } from '$lib/ws';
	import { connectionStatus, lastError } from '$lib/stores/connectionStore';
	import { handleServerMessage, resetStores } from '$lib/stores/gameStore';

	const sessionId = $derived($page.params.sessionId ?? '');

	let connection: GameConnection | undefined;
	let cleanupCallbacks: Array<() => void> = [];

	onMount(() => {
		if (!sessionId) return;
		resetStores();

		const conn = createGameConnection(sessionId);
		connection = conn;

		// Store cleanup functions returned by on* methods to avoid memory leaks
		cleanupCallbacks.push(
			conn.onConnect(() => {
				connectionStatus.set('connected');
			}),
		);

		cleanupCallbacks.push(
			conn.onDisconnect(() => {
				connectionStatus.set('reconnecting');
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
	});

	onDestroy(() => {
		// Unsubscribe all callbacks before disconnecting to prevent
		// stale closures firing during in-flight reconnect races
		cleanupCallbacks.forEach((cleanup) => cleanup());
		cleanupCallbacks = [];
		connection?.disconnect();
		connectionStatus.set('disconnected');
	});
</script>

<div class="game-view">
	<div class="connection-badge-container">
		<span
			class="connection-badge"
			class:connected={$connectionStatus === 'connected'}
			class:reconnecting={$connectionStatus === 'reconnecting'}
			class:connecting={$connectionStatus === 'connecting'}
		>
			{$connectionStatus}
		</span>
	</div>

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

	.connection-badge-container {
		display: flex;
		justify-content: flex-end;
		margin-bottom: var(--space-sm);
		flex-shrink: 0;
	}

	.connection-badge {
		font-size: 0.7rem;
		padding: var(--space-xs) var(--space-sm);
		border-radius: var(--border-radius-sm);
		background-color: var(--bg-secondary);
		color: var(--text-muted, var(--text-secondary));
		text-transform: uppercase;
		letter-spacing: 0.05em;
		font-family: var(--font-ui);
	}

	.connection-badge.connected {
		background-color: rgba(107, 142, 107, 0.2);
		color: var(--color-rogue);
	}

	.connection-badge.reconnecting {
		background-color: rgba(232, 168, 73, 0.2);
		color: var(--accent-warm);
	}

	.connection-badge.connecting {
		background-color: rgba(74, 144, 164, 0.2);
		color: var(--color-cleric);
	}

	.narrative-area {
		flex: 1;
		overflow: hidden;
	}
</style>
