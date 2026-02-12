<script lang="ts">
	import { connectionStatus } from '$lib/stores';

	const statusConfig = $derived(getStatusConfig($connectionStatus));

	function getStatusConfig(status: string): { label: string; cssClass: string } {
		switch (status) {
			case 'connected':
				return { label: 'Connected', cssClass: 'connected' };
			case 'reconnecting':
				return { label: 'Reconnecting', cssClass: 'reconnecting' };
			case 'disconnected':
				return { label: 'Disconnected', cssClass: 'disconnected' };
			case 'connecting':
				return { label: 'Connecting', cssClass: 'connecting' };
			default:
				return { label: status, cssClass: 'disconnected' };
		}
	}
</script>

<div class="connection-status {statusConfig.cssClass}" aria-label="Connection status: {statusConfig.label}">
	<span class="status-dot"></span>
	<span class="status-text">{statusConfig.label}</span>
</div>

<style>
	.connection-status {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: var(--space-xs) var(--space-sm);
		border-radius: var(--border-radius-lg);
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 500;
		letter-spacing: 0.02em;
	}

	.status-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.status-text {
		line-height: 1;
	}

	/* Connected: green */
	.connection-status.connected {
		background: rgba(107, 142, 107, 0.2);
		color: #6B8E6B;
	}
	.connection-status.connected .status-dot {
		background: #6B8E6B;
	}

	/* Reconnecting: amber */
	.connection-status.reconnecting {
		background: rgba(232, 168, 73, 0.2);
		color: var(--accent-warm);
	}
	.connection-status.reconnecting .status-dot {
		background: var(--accent-warm);
		animation: pulse-dot 1.5s ease-in-out infinite;
	}

	/* Disconnected: red */
	.connection-status.disconnected {
		background: rgba(196, 92, 74, 0.15);
		color: #C45C4A;
	}
	.connection-status.disconnected .status-dot {
		background: #C45C4A;
	}

	/* Connecting: blue */
	.connection-status.connecting {
		background: rgba(74, 144, 164, 0.2);
		color: var(--color-cleric);
	}
	.connection-status.connecting .status-dot {
		background: var(--color-cleric);
		animation: pulse-dot 1.5s ease-in-out infinite;
	}

	@keyframes pulse-dot {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.4; }
	}
</style>
