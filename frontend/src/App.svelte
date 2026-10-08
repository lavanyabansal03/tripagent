<script lang="ts">
  import { onMount } from 'svelte'
  import { t } from './copy/i18n'
  import { store } from './state/store.svelte'
  import { checkHealth, DEMO_MODE, type HealthStatus } from './api/client'
  import SetupPage from './pages/SetupPage.svelte'
  import UnderstoodPage from './pages/UnderstoodPage.svelte'
  import ItineraryPage from './pages/ItineraryPage.svelte'
  import Icon from './components/Icon.svelte'

  let theme = $state<'light' | 'dark'>('light')
  let health = $state<HealthStatus | null>(null)
  let checked = $state(false)

  onMount(async () => {
    const stored = localStorage.getItem('tripagent-theme')
    if (stored === 'light' || stored === 'dark') theme = stored
    else if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) theme = 'dark'

    // Match the skeleton's "Backend: connected" behaviour against /api/health.
    health = await checkHealth()
    checked = true
  })

  $effect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.dataset.theme = theme
      localStorage.setItem('tripagent-theme', theme)
    }
  })

  function toggleTheme() {
    theme = theme === 'light' ? 'dark' : 'light'
  }

  const route = $derived(store.route)
  const backendLabel = $derived(
    !checked
      ? t('app.backendChecking')
      : health
        ? t('app.backendConnected')
        : t('app.backendOffline'),
  )
</script>

<a class="skip-link" href="#main">{t('app.skipToContent')}</a>

<header class="app-header">
  <a class="brand" href="/">
    <Icon name="route" size={20} />
    <span>{t('app.name')}</span>
  </a>
  <div class="header-actions">
    {#if store.trip}
      <span class="destination">{store.trip.destination}</span>
    {/if}
    {#if DEMO_MODE}
      <span class="demo-badge" title={t('app.demoBadgeTitle')} data-testid="demo-badge">
        {t('app.demoBadge')}
      </span>
    {/if}
    <span
      class="backend"
      class:ok={health}
      class:offline={checked && !health}
      data-testid="backend-status"
      aria-live="polite"
    >
      <span class="dot" aria-hidden="true"></span>
      {backendLabel}
    </span>
    <button
      type="button"
      class="theme"
      aria-label={t('app.themeToggle')}
      aria-pressed={theme === 'dark'}
      onclick={toggleTheme}
    >
      <Icon name={theme === 'dark' ? 'moon' : 'sun'} size={16} />
    </button>
  </div>
</header>

<main id="main">
  {#if route.name === 'setup'}
    <SetupPage />
  {:else if route.name === 'planning'}
    <UnderstoodPage tripId={route.tripId} runId={route.runId} needsClarify={route.needsClarify} />
  {:else}
    <ItineraryPage />
  {/if}
</main>

<style>
  .skip-link {
    position: absolute;
    left: -9999px;
    top: 0;
    background: var(--color-brand);
    color: var(--color-brand-contrast);
    padding: var(--space-2) var(--space-4);
    z-index: 100;
  }
  .skip-link:focus {
    left: var(--space-2);
    top: var(--space-2);
  }
  .app-header {
    display: flex;
    align-items: center;
    height: var(--header-height);
    padding: 0 var(--space-4);
    border-bottom: 1px solid var(--color-border);
    background: var(--color-surface-raised);
    position: sticky;
    top: 0;
    z-index: 20;
  }
  .brand {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--text-lg);
    font-weight: var(--weight-semibold);
    color: var(--color-brand);
    text-decoration: none;
  }
  .header-actions {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: var(--space-3);
  }
  .destination {
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }
  .backend {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
  .backend .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--color-text-muted);
  }
  .backend.ok {
    color: var(--color-success);
  }
  .backend.ok .dot {
    background: var(--color-success);
  }
  .backend.offline {
    color: var(--color-warning);
  }
  .backend.offline .dot {
    background: var(--color-warning);
  }
  .demo-badge {
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    color: var(--color-info);
    background: var(--color-info-soft);
    border-radius: var(--radius-pill);
    padding: 1px var(--space-2);
  }
  .theme {
    display: inline-flex;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: transparent;
    color: var(--color-text);
    padding: var(--space-1) var(--space-2);
    cursor: pointer;
  }
  main {
    min-height: calc(100vh - var(--header-height));
    background: var(--color-bg);
  }
</style>
