<script lang="ts">
  /**
   * ItineraryPage — the core screen (guide Section 3 layout).
   * Desktop: day tabs + validation + activity list on the left, map on the
   * right, Adjust trip and Trace in the header. Mobile: Plan | Map | Trace tabs.
   */
  import { t } from '../copy/i18n'
  import type { ChangeEvent, Place } from '../types'
  import { mockEngine } from '../api/client'
  import { store } from '../state/store.svelte'
  import ActivityCard from '../components/ActivityCard.svelte'
  import AdjustTripDialog from '../components/AdjustTripDialog.svelte'
  import AgentTrace from '../components/AgentTrace.svelte'
  import ChangeSummaryPanel from '../components/ChangeSummaryPanel.svelte'
  import DayTabs from '../components/DayTabs.svelte'
  import InfeasibleNotice from '../components/InfeasibleNotice.svelte'
  import LegRow from '../components/LegRow.svelte'
  import MapView from '../components/MapView.svelte'
  import ValidationSummary from '../components/ValidationSummary.svelte'
  import Icon from '../components/Icon.svelte'

  let mobileTab = $state<'plan' | 'map' | 'trace'>('plan')
  let adjustOpen = $state(false)
  let focusPlace = $state<Place | null>(null)

  const itinerary = $derived(store.itinerary)
  const day = $derived(store.activeDay)
  const days = $derived(itinerary?.days ?? [])
  const activeDay = $derived(days.find((d) => d.day === day) ?? days[0])
  const latestReplan = $derived(store.replans.at(-1) ?? null)
  const previousItinerary = $derived(
    itinerary && store.versions.length > 1
      ? (mockEngine.getItinerary(store.trip?.id ?? '', itinerary.version - 1) ?? null)
      : null,
  )
  const canUndo = $derived(store.versions.indexOf(store.trip?.current_version ?? 0) > 0)
  const infeasible = $derived(store.infeasible)

  const dayList = $derived(
    days.map((d) => ({
      day: d.day,
      hasIssue: d.warnings.some((w) => !w.passed && w.severity === 'hard'),
    })),
  )

  const dates = $derived(
    store.trip ? `${store.trip.start_date} – ${store.trip.end_date}` : '',
  )

  function handleSwap(activityId: string, backupId: string, _name: string) {
    if (store.trip) void store.swap(store.trip.id, activityId, backupId)
  }
  function handleLock(activityId: string) {
    const activity = days.flatMap((d) => d.activities).find((a) => a.id === activityId)
    if (!activity || !itinerary) return
    activity.status = activity.status === 'locked' ? 'planned' : 'locked'
    itinerary.days = [...itinerary.days]
  }

  function handleQuickChange(typed: Partial<ChangeEvent>) {
    adjustOpen = false
    void store.submitTypedChange(typed)
  }
</script>

{#if infeasible}
  <InfeasibleNotice
    report={infeasible}
    city={store.requirements?.destination}
    budget={store.requirements?.budget}
    minutes={store.requirements?.max_travel_min}
    onrelax={(label) => store.setError(label)}
  />
{:else if !itinerary}
  <div class="empty">
    <p>{t('itinerary.noPlan')}</p>
  </div>
{:else}
  <div class="page">
    <header class="trip-header">
      <div class="title">
        <h1>{t('itinerary.headerCity', { city: store.trip?.destination ?? '', dates })}</h1>
        <span class="version" data-testid="version-chip">{t('itinerary.version', { version: itinerary.version })}</span>
      </div>
      <div class="header-tools">
        {#if canUndo}
          <button type="button" class="tool" title={t('itinerary.undoTooltip')} onclick={() => store.undo()}>
            <Icon name="undo" size={15} />
            {t('itinerary.undo')}
          </button>
        {/if}
        <button type="button" class="tool primary-tool" onclick={() => (adjustOpen = true)}>
          <Icon name="refresh" size={15} />
          {t('itinerary.adjustTrip')}
        </button>
        <button type="button" class="tool" onclick={() => (mobileTab = mobileTab === 'trace' ? 'plan' : 'trace')}>
          <Icon name="trace" size={15} />
          {t('itinerary.trace')}
        </button>
      </div>
    </header>

    <!-- Mobile view switch -->
    <nav class="mobile-tabs" aria-label={t('app.name')}>
      {#each [['plan', t('itinerary.planTab')], ['map', t('itinerary.mapTab')], ['trace', t('itinerary.traceTab')]] as [value, label] (value)}
        <button
          type="button"
          role="tab"
          aria-selected={mobileTab === value}
          class:active={mobileTab === value}
          onclick={() => (mobileTab = value as typeof mobileTab)}
        >
          {label}
        </button>
      {/each}
    </nav>

    <div class="layout">
      <div class="left" class:mobile-hidden={mobileTab === 'map' || mobileTab === 'trace'}>
        <DayTabs days={dayList} active={day} onchange={(d) => store.setActiveDay(d)} />

        {#if store.showChangeSummary && latestReplan}
          <ChangeSummaryPanel
            replan={latestReplan}
            {itinerary}
            previous={previousItinerary}
            onundo={() => store.undo()}
            onclose={() => store.setShowChangeSummary(false)}
          />
        {/if}

        <div class="day-panel" id="day-panel-{day}" role="tabpanel" aria-labelledby="day-tab-{day}">
          {#if activeDay}
            <ValidationSummary
              results={activeDay.warnings}
              maxTravelMin={store.requirements?.max_travel_min ?? 30}
              onMixItUp={() => store.simulate('diversity')}
            />
            <ol class="activities">
              {#each activeDay.activities as activity, i (activity.id)}
                <li>
                  <ActivityCard
                    {activity}
                    busy={store.busy}
                    onswap={(backupId, name) => handleSwap(activity.id, backupId, name)}
                    onlocktoggle={handleLock}
                    onfocusmap={(p) => {
                      focusPlace = p
                      mobileTab = 'map'
                    }}
                  />
                  {#if activeDay.legs[i]}
                    <LegRow
                      leg={activeDay.legs[i]}
                      limit={store.requirements?.max_travel_min ?? 30}
                      departAt={activeDay.activities[i].end}
                    />
                  {/if}
                </li>
              {/each}
            </ol>
          {/if}
        </div>
      </div>

      <div class="right" class:mobile-hidden={mobileTab === 'plan' || mobileTab === 'trace'}>
        <MapView
          {itinerary}
          day={mobileTab === 'map' ? null : day}
          {focusPlace}
          showDiff={store.showChangeSummary}
          onselect={(p: Place) => (focusPlace = p)}
        />
        {#if mobileTab === 'trace'}
          <div class="trace-wrap">
            <AgentTrace events={store.trace} />
          </div>
        {/if}
      </div>

      <aside class="trace-side" class:mobile-hidden={mobileTab === 'plan' || mobileTab === 'map'}>
        <AgentTrace events={store.trace} />
      </aside>
    </div>
  </div>
{/if}

<AdjustTripDialog
  open={adjustOpen}
  busy={store.busy}
  onsubmit={(text) => {
    adjustOpen = false
    void store.submitChange(text)
  }}
  onquick={handleQuickChange}
  onclose={() => (adjustOpen = false)}
/>

<style>
  .page {
    max-width: var(--content-max);
    margin: 0 auto;
    padding: var(--space-4);
  }
  .trip-header {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    flex-wrap: wrap;
    padding-bottom: var(--space-3);
  }
  .title {
    display: flex;
    align-items: baseline;
    gap: var(--space-3);
  }
  h1 {
    margin: 0;
    font-size: var(--text-xl);
  }
  .version {
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    color: var(--color-brand);
    background: var(--color-brand-soft);
    border-radius: var(--radius-pill);
    padding: 1px var(--space-2);
  }
  .header-tools {
    margin-left: auto;
    display: flex;
    gap: var(--space-2);
  }
  .tool {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    border: 1px solid var(--color-border);
    background: var(--color-surface-raised);
    color: var(--color-text);
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-3);
    font-size: var(--text-sm);
    cursor: pointer;
  }
  .primary-tool {
    border-color: var(--color-brand);
    color: var(--color-brand);
  }
  .mobile-tabs {
    display: none;
  }
  .layout {
    display: grid;
    grid-template-columns: var(--sidebar-width) 1fr;
    gap: var(--space-4);
    align-items: start;
  }
  .left {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    min-width: 0;
  }
  .right {
    position: sticky;
    top: calc(var(--header-height) + var(--space-4));
    height: calc(100vh - var(--header-height) - var(--space-8));
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  .trace-side {
    display: none;
  }
  .day-panel {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  .activities {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  .empty {
    padding: var(--space-12);
    text-align: center;
    color: var(--color-text-muted);
  }
  .trace-wrap {
    overflow: auto;
    max-height: 40vh;
  }

  @media (max-width: 1023px) {
    .layout {
      grid-template-columns: 1fr;
    }
    .right {
      position: static;
      height: 55vh;
    }
    .mobile-tabs {
      display: flex;
      gap: var(--space-1);
      border-bottom: 1px solid var(--color-border);
      margin-bottom: var(--space-3);
    }
    .mobile-tabs button {
      border: none;
      background: transparent;
      color: var(--color-text-muted);
      font-size: var(--text-sm);
      font-weight: var(--weight-medium);
      padding: var(--space-2) var(--space-4);
      border-bottom: 2px solid transparent;
      cursor: pointer;
    }
    .mobile-tabs button.active {
      color: var(--color-brand);
      border-bottom-color: var(--color-brand);
    }
    .mobile-hidden {
      display: none;
    }
    .trace-side {
      display: none;
    }
  }

  @media (min-width: 1280px) {
    .layout {
      grid-template-columns: var(--sidebar-width) 1fr 360px;
    }
    .trace-side {
      display: block;
      max-height: calc(100vh - var(--header-height) - var(--space-8));
      overflow: auto;
      background: var(--color-surface-raised);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-md);
      padding: var(--space-4);
    }
  }
</style>
