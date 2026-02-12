<script lang="ts">
	let {
		agentName,
		agentClass,
		visible = false,
	}: {
		agentName?: string;
		agentClass?: string;
		visible: boolean;
	} = $props();

	let showIndicator = $state(false);
	let delayTimer: ReturnType<typeof setTimeout> | null = null;

	$effect(() => {
		if (visible) {
			delayTimer = setTimeout(() => {
				showIndicator = true;
			}, 500);
		} else {
			showIndicator = false;
			if (delayTimer) {
				clearTimeout(delayTimer);
				delayTimer = null;
			}
		}
		return () => {
			if (delayTimer) {
				clearTimeout(delayTimer);
				delayTimer = null;
			}
		};
	});

	const indicatorText = $derived(getIndicatorText(agentName, agentClass));

	function getIndicatorText(name?: string, charClass?: string): string {
		if (!name) return 'The tale continues';
		const lower = name.toLowerCase();
		if (lower === 'dm') return 'The Dungeon Master weaves the tale';
		// Class-specific flavor text
		switch (charClass?.toLowerCase()) {
			case 'fighter':
				return `${name} steels their resolve`;
			case 'rogue':
				return `${name} plots their next move`;
			case 'wizard':
				return `${name} consults their arcane knowledge`;
			case 'cleric':
				return `${name} seeks divine guidance`;
			default:
				return `${name} contemplates`;
		}
	}

	const colorClass = $derived(agentClass ? agentClass.toLowerCase() : 'dm');
</script>

{#if showIndicator}
	<div class="thinking-indicator" role="status" aria-live="polite">
		<span class="thinking-text {colorClass}">{indicatorText}</span>
		<span class="thinking-dots" aria-hidden="true">
			<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>
		</span>
	</div>
{/if}

<style>
	.thinking-indicator {
		padding: var(--space-sm) var(--space-md);
		display: flex;
		align-items: center;
		gap: var(--space-xs);
	}

	.thinking-text {
		font-family: var(--font-narrative);
		font-style: italic;
		font-size: 0.875rem;
		color: var(--text-secondary);
	}

	/* Agent-specific colors */
	.thinking-text.dm {
		color: var(--color-dm);
	}
	.thinking-text.fighter {
		color: var(--color-fighter);
	}
	.thinking-text.rogue {
		color: var(--color-rogue);
	}
	.thinking-text.wizard {
		color: var(--color-wizard);
	}
	.thinking-text.cleric {
		color: var(--color-cleric);
	}

	.thinking-dots {
		display: inline-flex;
		font-size: 1.2rem;
		color: var(--text-secondary);
	}

	.dot {
		animation: dotPulse 1.4s infinite;
		opacity: 0;
	}
	.dot:nth-child(2) {
		animation-delay: 0.2s;
	}
	.dot:nth-child(3) {
		animation-delay: 0.4s;
	}

	@keyframes dotPulse {
		0%,
		80%,
		100% {
			opacity: 0;
		}
		40% {
			opacity: 1;
		}
	}
</style>
