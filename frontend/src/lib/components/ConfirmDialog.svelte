<script lang="ts">
	interface Props {
		open: boolean;
		title: string;
		message: string;
		confirmLabel?: string;
		confirmDanger?: boolean;
		error?: string | null;
		onConfirm: () => void;
		onCancel: () => void;
	}

	let {
		open,
		title,
		message,
		confirmLabel = 'Confirm',
		confirmDanger = false,
		error = null,
		onConfirm,
		onCancel,
	}: Props = $props();

	let confirmBtn: HTMLButtonElement | undefined = $state();
	let dialogEl: HTMLDivElement | undefined = $state();

	// Focus the confirm button when dialog opens
	$effect(() => {
		if (open && confirmBtn) {
			confirmBtn.focus();
		}
	});

	function handleKeydown(e: KeyboardEvent): void {
		if (!open) return;
		if (e.key === 'Escape') {
			e.preventDefault();
			onCancel();
		}
		// Trap focus within dialog
		if (e.key === 'Tab' && dialogEl) {
			const focusable = dialogEl.querySelectorAll<HTMLElement>(
				'button:not([disabled]), [tabindex]:not([tabindex="-1"])',
			);
			if (focusable.length === 0) return;
			const first = focusable[0];
			const last = focusable[focusable.length - 1];
			if (e.shiftKey && document.activeElement === first) {
				e.preventDefault();
				last.focus();
			} else if (!e.shiftKey && document.activeElement === last) {
				e.preventDefault();
				first.focus();
			}
		}
	}

	function handleBackdropClick(e: MouseEvent): void {
		if (e.target === e.currentTarget) {
			onCancel();
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="dialog-backdrop" onclick={handleBackdropClick} onkeydown={handleKeydown}>
		<div
			class="dialog"
			role="dialog"
			aria-modal="true"
			aria-label={title}
			bind:this={dialogEl}
		>
			<h3 class="dialog-title">{title}</h3>
			<p class="dialog-message">{message}</p>
			{#if error}
				<p class="dialog-error" role="alert">{error}</p>
			{/if}
			<div class="dialog-actions">
				<button class="btn btn-secondary" onclick={onCancel}>Cancel</button>
				<button
					class="btn"
					class:btn-danger={confirmDanger}
					class:btn-primary={!confirmDanger}
					onclick={onConfirm}
					bind:this={confirmBtn}
				>
					{confirmLabel}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.dialog-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 200;
		animation: fadeIn 0.15s ease;
	}

	.dialog {
		background: var(--bg-secondary);
		border-radius: 12px;
		padding: var(--space-lg);
		max-width: 400px;
		width: 90%;
		animation: scaleIn 0.15s ease;
	}

	.dialog-title {
		font-family: var(--font-ui);
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: var(--space-sm);
	}

	.dialog-message {
		font-family: var(--font-ui);
		font-size: var(--text-ui);
		color: var(--text-secondary);
		line-height: 1.5;
		margin-bottom: var(--space-lg);
	}

	.dialog-error {
		font-family: var(--font-ui);
		font-size: var(--text-system);
		color: var(--color-error);
		margin-top: calc(-1 * var(--space-sm));
		margin-bottom: var(--space-md);
	}

	.dialog-actions {
		display: flex;
		justify-content: flex-end;
		gap: var(--space-sm);
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

	.btn-primary {
		background: var(--accent-warm);
		color: var(--bg-primary);
	}

	.btn-primary:hover {
		background: var(--accent-warm-hover);
	}

	.btn-danger {
		background: var(--color-error);
		color: var(--text-primary);
	}

	.btn-danger:hover {
		background: #a84a3b;
	}

	@keyframes fadeIn {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	@keyframes scaleIn {
		from {
			transform: scale(0.95);
			opacity: 0;
		}
		to {
			transform: scale(1);
			opacity: 1;
		}
	}
</style>
