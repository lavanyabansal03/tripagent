<script lang="ts">
  /**
   * ActivityCard — the card for one scheduled activity (guide 4.2).
   * Carries time, place, cost, reason and backups. Keyboard: Enter expands
   * backups, L locks. Change state is announced via a polite live region.
   */
  import { t } from '../copy/i18n'
  import type { Activity, ExperienceCategory, Place } from '../types'
  import { CHANGE_VISUALS, CATEGORY_VISUALS, LOCAL_SIGNAL_VISUALS } from '../utils/visuals'
  import { formatCost, formatTime } from '../copy/i18n'
  import BackupDrawer from './BackupDrawer.svelte'
  import FreshnessLabel from './FreshnessLabel.svelte'
  import Icon from './Icon.svelte'
  import ValidationBadge from './ValidationBadge.svelte'

  interface Props {
    activity: Activity
    onswap?: (backupId: string, placeName: string) => void
    onlocktoggle?: (activityId: string) => void
    onfocusmap?: (place: Place) => void
    busy?: boolean
  }

  let { activity, onswap, onlocktoggle, onfocusmap, busy = false }: Props = $props()

  const place = $derived(activity.place)
  const category = $derived(place.experience_types[0] as ExperienceCategory)
  const categoryVisual = $derived(CATEGORY_VISUALS[category])
  const change = $derived(activity.change_type ? CHANGE_VISUALS[activity.change_type] : null)
  const signal = $derived(place.local_signal !== 'unknown' ? LOCAL_SIGNAL_VISUALS[place.local_signal] : null)
  const locked = $derived(activity.status === 'locked')
  const done = $derived(activity.status === 'done')
  const hasHard = $derived((activity.warnings ?? []).some((w) => w.severity === 'hard'))
  const hasSoft = $derived((activity.warnings ?? []).some((w) => w.severity === 'soft'))
  const cost = $derived(
    formatCost(activity.est_cost, place.est_cost_low, place.est_cost_high, activity.cost_basis),
  )
  const costHint = $derived(activity.cost_basis === 'price_level' ? t('validation.estimatedCostTooltip') : undefined)
  let whyOpen = $state(false)
</script>

<article
  class="card"
  class:locked
  class:done
  class:warning={hasHard || hasSoft}
  aria-labelledby="activity-{activity.id}"
  data-change={activity.change_type ?? 'none'}
>
  {#if change}
    <span class="change" style:--change-color={change.color}>
      <Icon name={change.icon} size={13} />
      {change.label}
    </span>
  {/if}

  <div class="head">
    <span class="time">
      <time datetime={activity.start}>{formatTime(activity.start)}</time>
      <span class="dash" aria-hidden="true">–</span>
      <time datetime={activity.end}>{formatTime(activity.end)}</time>
    </span>
    <h3 id="activity-{activity.id}">{place.name}</h3>
    {#if locked}
      <span class="status locked-tag" title={t('validation.lockTooltip')}>
        <Icon name="lock" size={13} />
        {t('validation.locked')}
      </span>
    {:else if done}
      <span class="status done-tag">
        <Icon name="check" size={13} />
        {t('validation.done')}
      </span>
    {/if}
  </div>

  <div class="meta">
    <span class="category" style:--cat-color={categoryVisual.color}>
      <Icon name={categoryVisual.icon} size={12} />
      {categoryVisual.label}
    </span>
    <span class="cost" title={costHint}>{cost}</span>
    {#if signal}
      <span class="signal" style:--signal-color={signal.color} title={t('validation.signalTooltip')}>
        <Icon name={signal.icon} size={11} />
        {signal.label}
      </span>
    {/if}
    <FreshnessLabel {place} />
  </div>

  {#if activity.reason}
    <p class="reason">
      <button type="button" class="why" onclick={() => (whyOpen = !whyOpen)} aria-expanded={whyOpen}>
        {t('validation.why')}
      </button>
      {#if whyOpen}
        <span class="reason-text">{activity.reason}</span>
      {/if}
    </p>
  {/if}

  {#if place.hours === null}
    <p class="gap">
      <Icon name="info" size={13} />
      {t('validation.unknownHours')}
    </p>
  {/if}

  {#if place.tip}
    <p class="tip">“{place.tip}”</p>
  {/if}

  <div class="actions">
    {#if onfocusmap}
      <button type="button" class="ghost" onclick={() => onfocusmap(place)}>
        <Icon name="map" size={13} />
        {t('itinerary.mapTab')}
      </button>
    {/if}
    {#if onlocktoggle}
      <button
        type="button"
        class="ghost"
        aria-pressed={locked}
        title={t('validation.lockTooltip')}
        onclick={() => onlocktoggle(activity.id)}
        onkeydown={(e) => {
          if (e.key === 'l' || e.key === 'L') {
            e.preventDefault()
            onlocktoggle(activity.id)
          }
        }}
      >
        <Icon name={locked ? 'lock' : 'unlock'} size={13} />
        {locked ? t('validation.locked') : t('validation.lockShortcut')}
      </button>
    {/if}
    {#if hasHard || hasSoft}
      <ValidationBadge severity={hasHard ? 'hard' : 'soft'} />
    {/if}
  </div>

  {#if !done && !locked && activity.priority !== 'low' && onswap}
    <BackupDrawer {activity} onswap={onswap} disabled={busy} />
  {/if}
</article>

<style>
  .card {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    background: var(--color-surface-raised);
    border: 1px solid var(--color-border);
    border-left: 4px solid var(--cat-landmark);
    border-radius: var(--radius-md);
    padding: var(--space-4);
    box-shadow: var(--shadow-1);
    transition: box-shadow var(--dur-fast) var(--ease-out);
  }
  .card:focus-within {
    box-shadow: var(--shadow-2);
  }
  .card.locked {
    background: var(--color-surface);
    border-left-color: var(--color-brand);
  }
  .card.done {
    opacity: 0.7;
  }
  .card.warning {
    border-left-color: var(--color-warning);
  }
  .card[data-change='added'] {
    border-left-color: var(--change-added);
  }
  .card[data-change='replaced'] {
    border-left-color: var(--change-replaced);
  }
  .card[data-change='moved'] {
    border-left-color: var(--change-moved);
  }
  .change {
    position: absolute;
    top: -10px;
    left: var(--space-4);
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    padding: 1px var(--space-2);
    border-radius: var(--radius-pill);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    color: var(--color-bg);
    background: var(--change-color);
  }
  .head {
    display: flex;
    align-items: baseline;
    gap: var(--space-2);
    flex-wrap: wrap;
  }
  .time {
    font-variant-numeric: tabular-nums;
    font-size: var(--text-sm);
    font-weight: var(--weight-semibold);
    color: var(--color-text);
  }
  .dash {
    color: var(--color-text-muted);
  }
  h3 {
    margin: 0;
    font-size: var(--text-md);
    font-weight: var(--weight-semibold);
  }
  .status {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    margin-left: auto;
  }
  .locked-tag {
    color: var(--color-brand);
  }
  .done-tag {
    color: var(--color-success);
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-3);
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
  .category,
  .signal {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-weight: var(--weight-medium);
  }
  .category {
    color: var(--cat-color);
  }
  .signal {
    color: var(--signal-color);
  }
  .cost {
    font-weight: var(--weight-medium);
    color: var(--color-text);
  }
  .reason {
    margin: 0;
    font-size: var(--text-sm);
    display: flex;
    gap: var(--space-2);
    align-items: baseline;
  }
  .why {
    border: none;
    background: transparent;
    color: var(--color-info);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    text-decoration: underline;
    cursor: pointer;
    padding: 0;
  }
  .reason-text {
    color: var(--color-text-muted);
  }
  .gap {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin: 0;
    font-size: var(--text-xs);
    color: var(--color-warning);
  }
  .tip {
    margin: 0;
    font-size: var(--text-sm);
    font-style: italic;
    color: var(--color-text-muted);
    border-left: 2px solid var(--color-border);
    padding-left: var(--space-3);
  }
  .actions {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-wrap: wrap;
  }
  .ghost {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    border: 1px solid var(--color-border);
    background: transparent;
    color: var(--color-text-muted);
    border-radius: var(--radius-pill);
    padding: 2px var(--space-3);
    font-size: var(--text-xs);
    cursor: pointer;
  }
  .ghost:focus-visible {
    outline: 2px solid var(--color-brand);
    outline-offset: 1px;
  }
</style>
