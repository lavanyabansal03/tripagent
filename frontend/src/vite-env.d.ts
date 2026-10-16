/// <reference types="svelte" />
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DEMO_MODE?: string
  readonly VITE_MAPBOX_PUBLIC_TOKEN?: string
  readonly VITE_API_PROXY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
