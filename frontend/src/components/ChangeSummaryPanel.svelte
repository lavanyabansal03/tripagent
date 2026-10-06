<script lang="ts">
  /**
   * ChangeSummaryPanel (guide 4.3). Appears after every replan. Groups changes
   * in a fixed order: Replaced, Moved, Added, Removed, Kept.
   */
  import { t } from '../copy/i18n'
  import type { Activity, Itinerary, ReplanEvent } from '../types'
  import { CHANGE_VISUALS } from '../utils/visuals'
  import { formatTime } from '../copy/i18n'
  import Icon from './Icon.svelte'

  interface Props {
    replan: ReplanEvent | null
    itinerary: Itinerary
    previous?: Itinerary | null
    approvalMode?: boolean
    onundo: () => void
    onclose: () => void
    onapply?: () => void
    onkeep?: () => void
  }

  let {
    replan,
    itinerary,
    previous,
    approvalMode = false,
    onundo,
    onclose,
    onapply,
    onkeep,
  }: Props = $props()

  let keptOpen = $state(false)

  const all = $derived(itinerary.days.flatMap((d) => d.activities))
  const byType = $derived({
    replaced: all.filter((a) => a.change_type === 'replaced'),
    moved: all.filter((a) => a.change_type === 'moved'),
    added: all.filter((a) => a.change_type === 'added'),
    removed: [],
    kept: all.filter((a) => a.change_type === 'kept' || a.change_type === null || a.change_type === undefined),
  })

  // Activities removed in the previous version (not present now).
  const removed = $derived(
    (previous?.days ?? [])
      .flatMap((d) => d.activities)
      .filter((a) => !all.some((now) => now.place_id === a.place_id)),
  )

  const trigger = $derived(replan?.trigger_text ?? 'something changed')
  const changedCount = $derived(
    byType.replaced.length + byType.moved.length + byType.added.length + removed.length,
  )
  const keptCount = $derived(byType.kept.length)

  function reason(a: Activity): string {
    return replan?.reasons[a.id] ?? a.reason ?? ''
  }

  const groups = $derived([
    { key: 'replaced', label: t('change.replaced'), items: byType.replaced },
    { key: 'moved', label: t('change.moved'), items: byType.moved },
    { key: 'added', label: t('change.added'), items: byType.added },
    { key: 'removed', label: t('change.removed'), items: removed },
  ])
</script>

<section class="panel" aria-labelledby="change-title">
  <header>
    <h2 id="change-title">
      {approvalMode ? t('changeSummary.approvalTitle') : t('changeSummary.title')}
    </h2>
    {#if approvalMode}
      <span class="proposal"><Icon name="info" size={13} />{t('changeSummary.proposalBadge')}</span>
    {/if}
    <button type="button" class="close" aria-label={t('changeSummary.close')} onclick={onclose}>
      <Icon name="close" size={16} />
    </button>
  </header>

  <p class="trigger">
    {t('changeSummary.triggerLine', { trigger, n: changedCount, m: keptCount })}
  </p>
  {#if approvalMode}
    <p class="approval-body">{t('changeSummary.approvalBody')}</p>
  {/if}

  <ul class="groups">
    {#each groups as group (group.key)}
      {#if group.items.length}
        <li class="group">
          <span class="group-label" style:--group-color={CHANGE_VISUALS[group.key as keyof typeof CHANGE_VISUALS].color}>
            <Icon name={CHANGE_VISUALS[group.key as keyof typeof CHANGE_VISUALS].icon} size={13} />
            {group.label}
          </span>
          <ul class="items">
            {#each group.items as a (a.id)}
              <li class="item">
                <span class="place">{a.place.name}</span>
                <span class="when">{formatTime(a.start)}</span>
                {#if reason(a)}
                  <span class="reason">{reason(a)}</span>
                {/if}
              </li>
            {/each}
          </ul>
        </li>
      {/if}
    {/each}
  </ul>

  {#if keptCount > 0}
    <div class="kept">
      <button type="button" class="kept-toggle" aria-expanded={keptOpen} onclick={() => (keptOpen = !keptOpen)}>
        <Icon name="check" size={13} />
        {t('changeSummary.keptCollapsed', { m: keptCount, expand: keptOpen ? t('common.collapse') : t('common.expand') })}
      </button>
      {#if keptOpen}
        <ul class="items kept-list">
          {#each byType.kept as a (a.id)}
            <li class="item"><span class="place">{a.place.name}</span><span class="when">{formatTime(a.start)}</span></li>
          {/each}
        </ul>
      {/if}
    </div>
  {/if}

  <footer class="actions">
    {#if approvalMode}
      <button type="button" class="ghost" onclick={onkeep}>{t('changeSummary.keepMyPlan')}</button>
      <button type="button" class="primary" onclick={onapply}>{t('changeSummary.applyChanges')}</button>
    {:else}
      <button type="button" class="ghost" onclick={onundo}>
        <Icon name="undo" size={13} />
        {t('changeSummary.undoChanges')}
      </button>
      <button type="button" class="primary" onclick={onclose}>{t('changeSummary.looksGood')}</button>
    {/if}
  </footer>
</section>

<style>
  .panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    background: var(--color-surface-raised);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-4);
    box-shadow: var(--shadow-2);
  }
  header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
  }
  h2 {
    margin: 0;
    font-size: var(--text-lg);
  }
  .proposal {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-xs);
    color: var(--color-info);
    background: var(--color-info-soft);
    border-radius: var(--radius-pill);
    padding: 1px var(--space-2);
  }
  .close {
    margin-left: auto;
    border: none;
    background: transparent;
    color: var(--color-text-muted);
    cursor: pointer;
    display: inline-flex;
  }
  .trigger {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--color-text);
  }
  .approval-body {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }
  .groups {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  .group-label {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-xs);
    font-weight: var(--weight-semibold);
    color: var(--group-color);
    text-transform: uppercase;
    letter-spacing: 0.02em;
  }
  .items {
    list-style: none;
    margin: var(--space-1) 0 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  .item {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    font-size: var(--text-sm);
    align-items: baseline;
  }
  .place {
    font-weight: var(--weight-medium);
  }
  .when {
    color: var(--color-text-muted);
    font-variant-numeric: tabular-nums;
    font-size: var(--text-xs);
  }
  .reason {
    color: var(--color-text-muted);
    font-size: var(--text-xs);
    flex-basis: 100%;
  }
  .kept-toggle {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    border: none;
    background: transparent;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    cursor: pointer;
    padding: 0;
  }
  .kept-list {
    margin-top: var(--space-1);
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--space-2);
    border-top: 1px solid var(--color-border);
    padding-top: var(--space-3);
  }
  .ghost {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    border: 1px solid var(--color-border);
    background: transparent;
    color: var(--color-text);
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-4);
    cursor: pointer;
  }
  .primary {
    background: var(--color-brand);
    color: var(--color-brand-contrast);
    border: none;
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-4);
    font-weight: var(--weight-semibold);
    cursor: pointer;
  }
</style>
