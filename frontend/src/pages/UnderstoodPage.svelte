<script lang="ts">
  /**
   * UnderstoodPage — clarification (L1) and the "Here's what we understood"
   * preference review, then the RunProgress while the graph runs.
   */
  import { onMount } from 'svelte'
  import { t, formatMoney, formatTripDate } from '../copy/i18n'
  import type { Provenance } from '../types'
  import { mockEngine } from '../api/client'
  import { store } from '../state/store.svelte'
  import ClarifyCard from '../components/ClarifyCard.svelte'
  import PreferenceChips from '../components/PreferenceChips.svelte'
  import RunProgress from '../components/RunProgress.svelte'
  import InfeasibleNotice from '../components/InfeasibleNotice.svelte'

  interface Props {
    tripId: string
    runId: string
    needsClarify: boolean
  }

  let { tripId, runId, needsClarify }: Props = $props()

  const questions = $derived(mockEngine.getTripRecord(tripId)?.questions ?? [])
  // store.planning covers live mode, where "Build my plan" waits for the whole plan.
  const running = $derived(store.run?.status === 'running' || store.planning)
  // A failed run brings its own report; a failed request (network, server) only a message.
  const problem = $derived(
    store.infeasible ??
      (store.error ? { blocking_rule: 'error', explanation: store.error, suggestions: [] } : null),
  )
  const finished = $derived(store.run?.status === 'done' && Boolean(store.itinerary))

  // Once the plan completes, move to the itinerary route.
  $effect(() => {
    if (finished) {
      store.setRoute({ name: 'itinerary' })
    }
  })

  onMount(async () => {
    try {
      await store.reload(tripId)
      if (runId) await store.pollRun(tripId, runId)
    } catch {
      store.setError('errors.loadFailed')
    }
  })

  const chips = $derived(
    (() => {
      const req = store.requirements
      if (!req) return []
      const out: Array<{ key: string; label: string; provenance: Provenance }> = []
      const source = (field: string): Provenance => req.provenance[field] ?? 'default'

      for (const interest of req.interests) {
        out.push({
          key: `interests.${interest}`,
          label: interest,
          provenance: req.provenance[`interests.${interest}`] ?? 'default',
        })
      }
      for (const item of req.avoid) {
        out.push({
          key: `avoid.${item}`,
          label: t('understood.avoidItem', { item }),
          provenance: req.provenance[`avoid.${item}`] ?? 'default',
        })
      }
      out.push({ key: 'mode', label: t('understood.modeValue', { value: req.mode }), provenance: source('mode') })
      out.push({ key: 'pace', label: t('understood.paceValue', { value: req.pace }), provenance: source('pace') })
      out.push({
        key: 'max_travel_min',
        label: t('understood.travelValue', { n: req.max_travel_min }),
        provenance: source('max_travel_min'),
      })
      const ratio = req.tourist_local_ratio
      out.push({
        key: 'tourist_local_ratio',
        label:
          ratio <= 30
            ? t('understood.ratioSights', { n: ratio })
            : ratio >= 70
              ? t('understood.ratioLocal', { n: ratio })
              : t('understood.ratioBalanced', { n: ratio }),
        provenance: source('tourist_local_ratio'),
      })
      out.push({
        key: 'budget',
        label:
          req.budget == null
            ? t('understood.budgetNone')
            : t('understood.budgetValue', { amount: formatMoney(req.budget) }),
        provenance: source('budget'),
      })
      if (req.dietary.length) {
        out.push({ key: 'dietary', label: req.dietary.join(', '), provenance: source('dietary') })
      }
      return out
    })(),
  )

  function startPlan() {
    void store.startPlanning(tripId)
  }

  function skipClarify() {
    store.setRoute({ name: 'planning', tripId, runId: '', needsClarify: false })
  }
</script>

{#if needsClarify && questions.length}
  <div class="wrap">
    <ClarifyCard
      {questions}
      busy={store.busy}
      onsubmit={(answers) => store.submitAnswers(tripId, answers)}
      onskip={skipClarify}
    />
  </div>
{:else if running}
  <RunProgress run={store.run} busy={store.planning} />
{:else if problem}
  <InfeasibleNotice
    report={problem}
    city={store.requirements?.destination}
    budget={store.requirements?.budget}
    minutes={store.requirements?.max_travel_min}
    onretry={problem.blocking_rule === 'error' ? startPlan : undefined}
    onedit={() => store.editTrip()}
  />
{:else}
  <div class="wrap">
    <section class="understood" aria-labelledby="understood-title">
      <h1 id="understood-title">{t('understood.sectionTitle')}</h1>
      {#if store.trip}
        <p class="summary">
          {store.trip.destination} · {formatTripDate(store.trip.start_date)} – {formatTripDate(store.trip.end_date)}
        </p>
      {/if}
      <PreferenceChips {chips} />
      <div class="actions">
        <button type="button" class="secondary" onclick={() => store.editTrip()}>
          {t('understood.editTrip')}
        </button>
        <button type="button" class="primary" onclick={startPlan} disabled={store.planning}>
          {t('setup.primaryCta')}
        </button>
      </div>
    </section>
  </div>
{/if}

<style>
  .wrap {
    max-width: 640px;
    margin: 0 auto;
    padding: var(--space-8) var(--space-4);
  }
  .understood {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    background: var(--color-surface-raised);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-6);
    box-shadow: var(--shadow-1);
  }
  h1 {
    margin: 0;
    font-size: var(--text-xl);
  }
  .summary {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-3);
  }
  .secondary {
    background: transparent;
    color: var(--color-brand);
    border: 1px solid var(--color-brand);
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-6);
    font-size: var(--text-md);
    font-weight: var(--weight-semibold);
    cursor: pointer;
  }
  .primary {
    align-self: flex-start;
    background: var(--color-brand);
    color: var(--color-brand-contrast);
    border: none;
    border-radius: var(--radius-md);
    padding: var(--space-3) var(--space-6);
    font-size: var(--text-md);
    font-weight: var(--weight-semibold);
    cursor: pointer;
  }
  .primary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
</style>
