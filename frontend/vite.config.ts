/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// Frontend & Maps Eng. — Vite + Svelte 5 + TS.
// VITE_DEMO_MODE=true (default) makes every API call resolve against recorded
// fixtures so the UI runs without the backend, matching FR-55.
export default defineConfig({
  plugins: [svelte()],
  server: {
    port: 5173,
    proxy: {
      // With the real backend set VITE_DEMO_MODE=false and point this proxy at
      // the FastAPI service.
      '/api': {
        target: process.env.VITE_API_PROXY ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
})
