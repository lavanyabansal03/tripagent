<script lang="ts">
  import { t } from '../copy/i18n'
  import type { Activity } from '../types'
  import { formatCost } from '../copy/i18n'
  import { placesById } from '../api/mock/fixtures'
  import Icon from './Icon.svelte'

  interface Props {
    activity: Activity
    onswap: (backupId: string, placeName: string) => void
    disabled?: boolean
  }

  let { activity, onswap, disabled = false }: Props = $props()
  let expanded = $state(false)
  const backups = $derived(activity.backups ?? [])

  function placeName(placeId: string): string {
    return placesById.get(placeId)?.name ?? placeId
  }
  function placeCost(placeId: string): string {
    const p = placesById.get(placeId)
    if (!p) return t('validation.unknownCost')
    return formatCost(p.est_cost_high ?? p.est_cost_low ?? null, p.est_cost_low, p.est_cost_high, p.cost_basis)
  }
</script>

<div class="drawer">
  <button
    type="button"
    class="toggle"
    aria-expanded={expanded}
    onclick={() => (expanded = !expanded)}
  >
    <Icon name={expanded ? 'chevron-up' : 'chevron-down'} size={14} />
    {t('validation.backupsHeader')}
    <span class="count">{t('validation.backupsCount', { count: backups.length })}</span>
  </button>

  {#if expanded}
    {#if backups.length === 0}
      <p class="empty">{t('validation.noBackups')}</p>
    {:else}
      <ul class="list">
        {#each backups as backup (backup.place_id)}
          <li class="item">
            <div class="meta">
              <span class="name">{placeName(backup.place_id)}</span>
              <span class="cost">{placeCost(backup.place_id)}</span>
            </div>
            <div class="signals">
              <span class="similarity" title={t('validation.signalTooltip')}>
                <Icon name="check" size={12} />
                {Math.round(backup.purpose_similarity * 100)}% {t('change.kept')}
              </span>
              {#if backup.cost_delta < 0}
                <span class="cheaper">{formatCost(backup.cost_delta, null, null, 'known')}</span>
              {/if}
              <button
                type="button"
                class="swap"
                disabled={disabled || activity.status === 'locked'}
                onclick={() => onswap(backup.place_id, placeName(backup.place_id))}
              >
                {t('change.replaced')}
              </button>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</div>

<style>
  .drawer {
    border-top: 1px solid var(--color-border);
    margin-top: var(--space-2);
    padding-top: var(--space-2);
  }
  .toggle {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    border: none;
    background: transparent;
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    cursor: pointer;
    padding: var(--space-1) 0;
  }
  .count {
    color: var(--color-text-muted);
  }
  .empty {
    margin: var(--space-1) 0 0;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
  .list {
    list-style: none;
    margin: var(--space-2) 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  .item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--space-2);
    padding: var(--space-2);
    background: var(--color-surface);
    border-radius: var(--radius-sm);
  }
  .meta {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .name {
    font-size: var(--text-sm);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .cost {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
  .signals {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex: none;
  }
  .similarity {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    font-size: var(--text-xs);
    color: var(--color-success);
  }
  .cheaper {
    font-size: var(--text-xs);
    color: var(--color-success);
  }
  .swap {
    border: 1px solid var(--color-brand);
    background: transparent;
    color: var(--color-brand);
    border-radius: var(--radius-pill);
    padding: 2px var(--space-3);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    cursor: pointer;
  }
  .swap:disabled {
    opacity: 0.5;
    cursor: default;
  }
</style>
