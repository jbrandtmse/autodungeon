import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/svelte';
import SetupPage from './+page.svelte';

// Mock SvelteKit navigation
const mockGoto = vi.fn();
vi.mock('$app/navigation', () => ({
	goto: (...args: unknown[]) => mockGoto(...args),
}));

// Mock SvelteKit page store
vi.mock('$app/stores', async () => {
	const { readable } = await import('svelte/store');
	return {
		page: readable({ params: { sessionId: '001' } }),
	};
});

// Mock API functions
const mockDiscoverModules = vi.fn();
const mockGetCharacters = vi.fn();
const mockStartSession = vi.fn();

vi.mock('$lib/api', () => ({
	discoverModules: (...args: unknown[]) => mockDiscoverModules(...args),
	getCharacters: (...args: unknown[]) => mockGetCharacters(...args),
	startSession: (...args: unknown[]) => mockStartSession(...args),
	ApiError: class ApiError extends Error {
		status: number;
		statusText: string;
		constructor(status: number, statusText: string, message: string) {
			super(message);
			this.status = status;
			this.statusText = statusText;
		}
	},
}));

const MOCK_MODULES = [
	{
		number: 1,
		name: 'Curse of Strahd',
		description: 'Gothic horror in Ravenloft.',
		setting: 'Ravenloft',
		level_range: '1-10',
	},
	{
		number: 2,
		name: 'Lost Mine of Phandelver',
		description: 'Classic starter adventure.',
		setting: 'Forgotten Realms',
		level_range: '1-5',
	},
];

const MOCK_CHARACTERS = [
	{
		name: 'Shadowmere',
		character_class: 'Rogue',
		personality: 'Sardonic',
		color: '#6B8E6B',
		provider: 'claude',
		model: 'claude-3-haiku',
		source: 'preset' as const,
	},
	{
		name: 'Eldrin',
		character_class: 'Wizard',
		personality: 'Bookish',
		color: '#7B68B8',
		provider: 'gemini',
		model: 'gemini-1.5-flash',
		source: 'preset' as const,
	},
	{
		name: 'Eden',
		character_class: 'Warlock',
		personality: 'Mysterious',
		color: '#4B0082',
		provider: 'claude',
		model: 'claude-3-haiku',
		source: 'library' as const,
	},
];

describe('Adventure Setup Page', () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockDiscoverModules.mockResolvedValue({
			modules: MOCK_MODULES,
			provider: 'gemini',
			model: 'gemini-1.5-flash',
			source: 'llm',
			error: null,
		});
		mockGetCharacters.mockResolvedValue(MOCK_CHARACTERS);
		mockStartSession.mockResolvedValue({ status: 'started', session_id: '001' });
	});

	it('renders loading state then modules', async () => {
		render(SetupPage);

		// Should show loading initially
		expect(screen.getByText(/Consulting the Dungeon Master/i)).toBeTruthy();

		// Wait for modules to load
		await waitFor(() => {
			expect(screen.getByText('Curse of Strahd')).toBeTruthy();
		});

		expect(screen.getByText('Lost Mine of Phandelver')).toBeTruthy();
	});

	it('freeform button enables next step', async () => {
		render(SetupPage);

		await waitFor(() => {
			expect(screen.getByTestId('freeform-btn')).toBeTruthy();
		});

		await fireEvent.click(screen.getByTestId('freeform-btn'));

		// Next button should be enabled now
		const nextBtn = screen.getByTestId('next-step2');
		expect((nextBtn as HTMLButtonElement).disabled).toBe(false);
	});

	it('selecting a module enables next step', async () => {
		render(SetupPage);

		await waitFor(() => {
			expect(screen.getAllByTestId('module-card').length).toBeGreaterThan(0);
		});

		const moduleCards = screen.getAllByTestId('module-card');
		await fireEvent.click(moduleCards[0]);

		const nextBtn = screen.getByTestId('next-step2');
		expect((nextBtn as HTMLButtonElement).disabled).toBe(false);
	});

	it('step 2 shows characters after advancing', async () => {
		render(SetupPage);

		// Wait for modules, choose freeform, go to step 2
		await waitFor(() => {
			expect(screen.getByTestId('freeform-btn')).toBeTruthy();
		});

		await fireEvent.click(screen.getByTestId('freeform-btn'));
		await fireEvent.click(screen.getByTestId('next-step2'));

		// Wait for characters to load (step 2)
		await waitFor(() => {
			expect(screen.getByTestId('step-party')).toBeTruthy();
		});

		await waitFor(() => {
			expect(screen.getAllByTestId('character-card').length).toBe(3);
		});
	});

	it('shows error on module discovery failure', async () => {
		mockDiscoverModules.mockResolvedValue({
			modules: [],
			provider: 'gemini',
			model: 'gemini-1.5-flash',
			source: 'error',
			error: 'LLM API failed',
		});

		render(SetupPage);

		await waitFor(() => {
			expect(screen.getByText('LLM API failed')).toBeTruthy();
		});
	});

	it('begin adventure calls startSession API', async () => {
		render(SetupPage);

		// Step 1: choose freeform
		await waitFor(() => {
			expect(screen.getByTestId('freeform-btn')).toBeTruthy();
		});
		await fireEvent.click(screen.getByTestId('freeform-btn'));
		await fireEvent.click(screen.getByTestId('next-step2'));

		// Step 2: wait for characters, click begin
		await waitFor(() => {
			expect(screen.getByTestId('begin-adventure')).toBeTruthy();
		});

		await waitFor(() => {
			expect((screen.getByTestId('begin-adventure') as HTMLButtonElement).disabled).toBe(false);
		});

		await fireEvent.click(screen.getByTestId('begin-adventure'));

		await waitFor(() => {
			expect(mockStartSession).toHaveBeenCalledWith(
				'001',
				expect.objectContaining({
					selected_module: null,
					selected_characters: expect.any(Array),
				}),
			);
		});
	});

	it('shows error state on API failure during launch', async () => {
		mockStartSession.mockRejectedValue(new Error('Server error'));

		render(SetupPage);

		// Go through setup
		await waitFor(() => {
			expect(screen.getByTestId('freeform-btn')).toBeTruthy();
		});
		await fireEvent.click(screen.getByTestId('freeform-btn'));
		await fireEvent.click(screen.getByTestId('next-step2'));

		await waitFor(() => {
			expect((screen.getByTestId('begin-adventure') as HTMLButtonElement).disabled).toBe(false);
		});
		await fireEvent.click(screen.getByTestId('begin-adventure'));

		await waitFor(() => {
			expect(screen.getByText(/Failed to start adventure/i)).toBeTruthy();
		});
	});
});
