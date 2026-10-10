import { defineConfig, devices } from '@playwright/test'

/**
 * E2E flows for the two demo scenarios (R-02):
 *  - describe a trip in words -> understood -> itinerary on the map
 *  - report a change -> local, explained diff with undo
 * Runs against the Vite dev server in DEMO_MODE so it needs no backend.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    command: 'npm run dev -- --port 5173',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    env: { VITE_DEMO_MODE: 'true' },
    timeout: 60_000,
  },
})
