import { sveltekit } from '@sveltejs/kit/vite';
import { svelteTesting } from '@testing-library/svelte/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [sveltekit(), svelteTesting()],
	test: {
		include: ['src/**/*.test.ts'],
		environment: 'jsdom',
		setupFiles: ['src/tests/setup.ts'],
	},
	server: {
		proxy: {
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true,
				// 10 min — accommodates slow LLM calls like module discovery
				// against a local 27B+ model that takes 3-9 min to respond.
				timeout: 600000,
				proxyTimeout: 600000,
			},
			'/ws': {
				target: 'http://localhost:8000',
				ws: true,
			},
		},
	},
});
