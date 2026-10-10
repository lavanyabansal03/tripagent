import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

// Svelte 5 component tests must resolve the *browser* export condition,
// otherwise `mount()` is replaced by the server stub and every render throws
// `lifecycle_function_unavailable`. Vitest runs modules through Vite's SSR
// pipeline, so the condition has to be set for both normal and ssr resolution.
export default mergeConfig(
  viteConfig,
  defineConfig({
    resolve: {
      conditions: ['browser'],
    },
    ssr: {
      resolve: {
        conditions: ['browser'],
      },
      noExternal: true,
    },
    test: {
      server: {
        deps: {
          inline: [/svelte/, /@testing-library\/svelte/],
        },
      },
    },
  }),
)
