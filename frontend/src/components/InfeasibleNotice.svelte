<script lang="ts">
  import { t } from '../copy/i18n'
  import type { InfeasibleReport } from '../types'
  import Icon from './Icon.svelte'

  interface Props {
    report: InfeasibleReport
    /** City and budget are interpolated into the copy template. */
    city?: string
    budget?: number | null
    minutes?: number
    onrelax?: (label: string) => void
    /** Shown as "Try again" (for a failure, not for a trip that cannot fit). */
    onretry?: () => void
    /** Shown as "Edit trip details". */
    onedit?: () => void
  }

  let {
    report,
    city = '',
    budget = null,
    minutes = 15,
    onrelax,
    onretry,
    onedit,
  }: Props = $props()

  // "error" means planning failed (a crash, the network), not that the trip cannot fit.
  const failed = $derived(report.blocking_rule === 'error')
  const body = $derived(
    report.explanation === 'infeasible.noPlan'
      ? t('infeasible.noPlan', { city, budget: budget ?? '' })
      : report.explanation === 'infeasible.travelLimit'
        ? t('infeasible.travelLimit', { minutes, suggested: minutes + 10 })
        : t(report.explanation), // an i18n key such as errors.unknown, or the backend's sentence
  )
</script>

<section class="notice" role="alert" aria-labelledby="infeasible-title">
  <header>
    <Icon name="alert" size={20} />
    <h2 id="infeasible-title">{failed ? t('planning.failed') : t('infeasible.title')}</h2>
  </header>
  <p class="body">{body}</p>
  {#if report.suggestions.length}
    <div class="suggestions">
      {#each report.suggestions as suggestion (suggestion.label)}
        <button type="button" class="chip" onclick={() => onrelax?.(suggestion.label)}>
          {t(suggestion.label)}
        </button>
      {/each}
    </div>
  {/if}
  {#if onretry || onedit}
    <div class="suggestions">
      {#if onretry}
        <button type="button" class="chip" onclick={() => onretry?.()}>
          {t('infeasible.tryAgain')}
        </button>
      {/if}
      {#if onedit}
        <button type="button" class="chip" onclick={() => onedit?.()}>
          {t('understood.editTrip')}
        </button>
      {/if}
    </div>
  {/if}
</section>

<style>
  .notice {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    max-width: 560px;
    margin: var(--space-8) auto;
    padding: var(--space-5, 20px);
    background: var(--color-danger-soft);
    border: 1px solid color-mix(in srgb, var(--color-danger) 35%, transparent);
    border-radius: var(--radius-lg);
  }
  header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--color-danger);
  }
  h2 {
    margin: 0;
    font-size: var(--text-lg);
  }
  .body {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--color-text);
    line-height: var(--lh-body);
  }
  .suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }
  .chip {
    border: 1px solid var(--color-danger);
    background: var(--color-bg);
    color: var(--color-danger);
    border-radius: var(--radius-pill);
    padding: var(--space-1) var(--space-3);
    font-size: var(--text-sm);
    font-weight: var(--weight-medium);
    cursor: pointer;
  }
  .chip:hover {
    background: var(--color-danger);
    color: var(--color-bg);
  }
</style>
