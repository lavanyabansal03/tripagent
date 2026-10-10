<script lang="ts">
  import { t } from '../copy/i18n'
  import type { Place } from '../types'
  import { formatRelativeWhen, isStale } from '../copy/i18n'
  import Icon from './Icon.svelte'

  interface Props {
    place: Place
    /** Place data older than 7 days is labelled stale (FR-39). */
    maxAgeHours?: number
    onRefresh?: () => void
  }

  let { place, maxAgeHours = 24 * 7, onRefresh }: Props = $props()
  const stale = $derived(isStale(place.retrieved_at, maxAgeHours))
</script>

<span class="freshness" class:stale>
  <Icon name={stale ? 'warning' : 'check'} size={13} />
  {#if stale}
    <span>{t('validation.stale', { when: formatRelativeWhen(place.retrieved_at) })}</span>
    {#if onRefresh}
      <button type="button" class="refresh" onclick={onRefresh}>
        <Icon name="refresh" size={12} />
        {t('validation.checkAgain')}
      </button>
    {/if}
  {:else}
    <span>{formatRelativeWhen(place.retrieved_at)}</span>
  {/if}
</span>

<style>
  .freshness {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
  .freshness.stale {
    color: var(--color-warning);
  }
  .refresh {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    margin-left: var(--space-1);
    border: none;
    background: transparent;
    color: inherit;
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    text-decoration: underline;
    cursor: pointer;
    padding: 0;
  }
</style>
