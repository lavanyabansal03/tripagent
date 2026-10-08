<script lang="ts">
  import { t } from '../copy/i18n'
  import type { RouteLeg } from '../types'
  import { formatTime } from '../copy/i18n'
  import Icon from './Icon.svelte'

  interface Props {
    leg: RouteLeg
    /** User's max travel time; legs above it are hard violations (FR-09). */
    limit: number
    departAt: string
  }

  let { leg, limit, departAt }: Props = $props()
  const over = $derived(leg.duration_min > limit)
  const icon = $derived(
    leg.mode === 'walking' ? 'nature' : leg.mode === 'driving' ? 'route' : 'route',
  )
</script>

<div class="leg" class:over class:changed={leg.changed}>
  <span class="line" aria-hidden="true"></span>
  <span class="info">
    <Icon name={icon} size={13} />
    <span class="duration">{leg.duration_min} min {leg.mode}</span>
    <span class="dot" aria-hidden="true">·</span>
    <span class="distance">{leg.distance_km} km</span>
    <span class="dot" aria-hidden="true">·</span>
    <span class="depart">{formatTime(departAt)}</span>
    {#if over}
      <span class="flag" role="img" aria-label={t('validation.hardBadge')}>
        <Icon name="alert" size={12} />
        {t('validation.hardBadge')}
      </span>
    {/if}
    {#if leg.changed}
      <span class="changed-tag">{t('change.moved')}</span>
    {/if}
  </span>
</div>

<style>
  .leg {
    display: flex;
    gap: var(--space-3);
    padding-left: var(--space-4);
    min-height: 32px;
  }
  .line {
    width: 2px;
    background: var(--color-border);
    margin-left: 7px;
    border-radius: var(--radius-pill);
  }
  .leg.changed .line {
    background: repeating-linear-gradient(
      to bottom,
      var(--change-moved) 0 4px,
      transparent 4px 8px
    );
  }
  .info {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    padding: var(--space-1) 0;
  }
  .leg.over .info {
    color: var(--color-danger);
  }
  .duration {
    font-weight: var(--weight-medium);
  }
  .dot {
    opacity: 0.5;
  }
  .flag {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    color: var(--color-danger);
    font-weight: var(--weight-medium);
  }
  .changed-tag {
    color: var(--change-moved);
    font-weight: var(--weight-medium);
  }
</style>
