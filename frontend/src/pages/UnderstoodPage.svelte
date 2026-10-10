<script lang="ts">
  /**
   * UnderstoodPage — clarification (L1) and the "Here's what we understood"
   * preference review, then the RunProgress while the graph runs.
   */
  import { onMount } from 'svelte'
  import { t } from '../copy/i18n'
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
  const running = $derived(store.run?.status === 'running')
  const finished = $derived(store.run?.status === 'done' && Boolean(store.itinerary))

  // Once the plan completes, move to the itinerary route.
  $effect(() => {
    if (finished) {
      store.setRoute({ name: 'itinerary' })
    }
  })

  onMount(async () => {
    await store.reload(tripId)
    if (runId) await store.pollRun(tripId, runId)
  })

  const chips = $derived(
    (() => {
      const req = store.requirements
      if (!req) return []
      const out: Array<{ key: string; label: string; provenance: Provenance }> = []
      for (const interest of req.interests) {
        out.push({
          key: `interests.${interest}`,
          label: interest,
          provenance: req.provenance[`interests.${interest}`] ?? 'default',
        })
      }
      out.push({ key: 'mode', label: req.mode, provenance: req.provenance.mode ?? 'explicit' })
      out.push({ key: 'pace', label: req.pace, provenance: req.provenance.pace ?? 'explicit' })
      out.push({
        key: 'max_travel_min',
        label: `${req.max_travel_min} min travel`,
        provenance: req.provenance.max_travel_min ?? 'explicit',
      })
      if (req.dietary.length) {
        out.push({ key: 'dietary', label: req.dietary.join(', '), provenance: 'explicit' })
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
  <RunProgress run={store.run} />
{:else if store.infeasible}
  <InfeasibleNotice
    report={store.infeasible}
    city={store.requirements?.destination}
    budget={store.requirements?.budget}
    minutes={store.requirements?.max_travel_min}
  />
{:else}
  <div class="wrap">
    <section class="understood" aria-labelledby="understood-title">
      <h1 id="understood-title">{t('understood.sectionTitle')}</h1>
      {#if store.trip}
        <p class="summary">
          {store.trip.destination} · {store.trip.start_date} – {store.trip.end_date}
        </p>
      {/if}
      <PreferenceChips {chips} />
      <button type="button" class="primary" onclick={startPlan}>
        {t('setup.primaryCta')}
      </button>
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
</style>
