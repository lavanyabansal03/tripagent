<script lang="ts">
  import { t } from '../copy/i18n'
  import type { TripFormInput } from '../api/client'
  import TellUsMoreField from './TellUsMoreField.svelte'
  import TouristLocalSlider from './TouristLocalSlider.svelte'

  interface Props {
    onsubmit: (input: TripFormInput) => void
    busy?: boolean
  }

  let { onsubmit, busy = false }: Props = $props()

  // Seattle is the tuned demo city; prefill dates so the demo is one click.
  const today = new Date()
  const start = new Date(today.getTime() + 7 * 86_400_000).toISOString().slice(0, 10)
  const end = new Date(today.getTime() + 9 * 86_400_000).toISOString().slice(0, 10)

  let destination = $state('Seattle')
  let startDate = $state(start)
  let endDate = $state(end)
  let budget = $state<string>('500')
  let budgetStrict = $state(true)
  let mode = $state<TripFormInput['mode']>('transit')
  let pace = $state<TripFormInput['pace']>('moderate')
  let maxTravel = $state(30)
  let freeText = $state('')
  let touristLocal = $state(50)
  let interestInput = $state('')
  let interests = $state<string[]>(['coffee'])
  let avoid = $state<string[]>([])

  const modeOptions: Array<{ value: TripFormInput['mode']; label: string }> = [
    { value: 'walking', label: t('setup.modeWalking') },
    { value: 'transit', label: t('setup.modeTransit') },
    { value: 'driving', label: t('setup.modeDriving') },
    { value: 'cycling', label: t('setup.modeCycling') },
  ]
  const paceOptions: Array<{ value: TripFormInput['pace']; label: string }> = [
    { value: 'relaxed', label: t('setup.paceRelaxed') },
    { value: 'moderate', label: t('setup.paceModerate') },
    { value: 'packed', label: t('setup.pacePacked') },
  ]
  const suggested = ['coffee', 'nature', 'culture', 'food', 'bookstores', 'photography']

  function toggle(list: string[], value: string): string[] {
    return list.includes(value) ? list.filter((x) => x !== value) : [...list, value]
  }

  function addInterest() {
    const value = interestInput.trim().toLowerCase()
    if (value && !interests.includes(value)) interests = [...interests, value]
    interestInput = ''
  }

  function submit() {
    onsubmit({
      destination,
      start_date: startDate,
      end_date: endDate,
      budget: budget.trim() === '' ? null : Number(budget),
      budget_strictness: budgetStrict ? 'strict' : 'flexible',
      mode,
      pace,
      max_travel_min: maxTravel,
      interests,
      avoid,
      tourist_local_ratio: touristLocal,
      free_text: freeText,
    })
  }
</script>

<form
  class="trip-form"
  aria-labelledby="trip-form-title"
  onsubmit={(e) => {
    e.preventDefault()
    submit()
  }}
>
  <h1 id="trip-form-title">{t('setup.pageTitle')}</h1>
  <p class="intro">{t('setup.intro')}</p>

  <div class="grid">
    <div class="field">
      <label for="destination">{t('setup.destinationLabel')}</label>
      <input
        id="destination"
        type="text"
        bind:value={destination}
        placeholder={t('setup.destinationPlaceholder')}
        required
      />
    </div>

    <fieldset class="field dates">
      <legend>{t('setup.datesLabel')}</legend>
      <div class="date-row">
        <div>
          <label for="start-date">{t('setup.startDateLabel')}</label>
          <input id="start-date" type="date" bind:value={startDate} required />
        </div>
        <div>
          <label for="end-date">{t('setup.endDateLabel')}</label>
          <input id="end-date" type="date" bind:value={endDate} min={startDate} required />
        </div>
      </div>
    </fieldset>

    <div class="field">
      <label for="budget">{t('setup.budgetLabel')}</label>
      <input id="budget" type="number" min="0" step="10" bind:value={budget} placeholder={t('setup.budgetPlaceholder')} />
      <p class="helper">{t('setup.budgetHelp')}</p>
      <label class="checkbox">
        <input type="checkbox" bind:checked={budgetStrict} />
        {t('setup.budgetStrictLabel')}
      </label>
    </div>

    <fieldset class="field">
      <legend>{t('setup.modeLabel')}</legend>
      <div class="segmented">
        {#each modeOptions as option (option.value)}
          <label class="segment" class:active={mode === option.value}>
            <input type="radio" name="mode" value={option.value} checked={mode === option.value} onchange={() => (mode = option.value)} />
            {option.label}
          </label>
        {/each}
      </div>
    </fieldset>

    <fieldset class="field">
      <legend>{t('setup.paceLabel')}</legend>
      <div class="segmented">
        {#each paceOptions as option (option.value)}
          <label class="segment" class:active={pace === option.value}>
            <input type="radio" name="pace" value={option.value} checked={pace === option.value} onchange={() => (pace = option.value)} />
            {option.label}
          </label>
        {/each}
      </div>
    </fieldset>

    <div class="field">
      <label for="max-travel">{t('setup.maxTravelLabel')}</label>
      <div class="range-row">
        <input id="max-travel" type="range" min="10" max="90" step="5" bind:value={maxTravel} />
        <output for="max-travel">{maxTravel} {t('setup.maxTravelUnit')}</output>
      </div>
    </div>

    <fieldset class="field">
      <legend>{t('setup.interestsLabel')}</legend>
      <div class="chips">
        {#each suggested as item (item)}
          <label class="chip" class:active={interests.includes(item)}>
            <input type="checkbox" checked={interests.includes(item)} onchange={() => (interests = toggle(interests, item))} />
            {item}
          </label>
        {/each}
      </div>
      <div class="add-row">
        <input
          type="text"
          bind:value={interestInput}
          placeholder="Add your own"
          onkeydown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              addInterest()
            }
          }}
        />
        <button type="button" onclick={addInterest}>Add</button>
      </div>
    </fieldset>

    <fieldset class="field">
      <legend>{t('setup.avoidLabel')}</legend>
      <div class="chips">
        {#each ['culture', 'nightlife', 'shopping', 'food'] as item (item)}
          <label class="chip" class:active={avoid.includes(item)}>
            <input type="checkbox" checked={avoid.includes(item)} onchange={() => (avoid = toggle(avoid, item))} />
            {item}
          </label>
        {/each}
      </div>
    </fieldset>
  </div>

  <TellUsMoreField bind:value={freeText} />
  <TouristLocalSlider bind:value={touristLocal} />

  <div class="actions">
    <button type="submit" class="primary" disabled={busy}>
      {busy ? t('setup.submitting') : t('setup.primaryCta')}
    </button>
    <p class="demo-note">{t('setup.demoNote')}</p>
  </div>
</form>

<style>
  .trip-form {
    display: flex;
    flex-direction: column;
    gap: var(--space-6);
    max-width: 780px;
    margin: 0 auto;
    padding: var(--space-8) var(--space-4) var(--space-12);
  }
  h1 {
    margin: 0;
    font-size: var(--text-2xl);
  }
  .intro {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-md);
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: var(--space-4);
  }
  .field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    border: none;
    padding: 0;
    margin: 0;
  }
  legend,
  label {
    font-size: var(--text-sm);
    font-weight: var(--weight-medium);
  }
  input[type='text'],
  input[type='number'],
  input[type='date'] {
    font: inherit;
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
  }
  .date-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--space-3);
  }
  .date-row > div {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  .helper {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
  .checkbox {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    font-weight: var(--weight-regular);
    font-size: var(--text-sm);
  }
  .segmented {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }
  .segment {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-pill);
    padding: var(--space-1) var(--space-3);
    font-size: var(--text-sm);
    cursor: pointer;
  }
  .segment.active {
    border-color: var(--color-brand);
    background: var(--color-brand-soft);
    color: var(--color-brand);
    font-weight: var(--weight-medium);
  }
  .segment input,
  .chip input {
    position: absolute;
    opacity: 0;
    pointer-events: none;
  }
  .range-row {
    display: flex;
    align-items: center;
    gap: var(--space-3);
  }
  .range-row input[type='range'] {
    flex: 1;
    accent-color: var(--color-brand);
  }
  .range-row output {
    font-size: var(--text-sm);
    font-weight: var(--weight-medium);
    min-width: 7ch;
  }
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }
  .chip {
    display: inline-flex;
    align-items: center;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-pill);
    padding: var(--space-1) var(--space-3);
    font-size: var(--text-sm);
    cursor: pointer;
  }
  .chip.active {
    border-color: var(--color-brand);
    background: var(--color-brand-soft);
  }
  .add-row {
    display: flex;
    gap: var(--space-2);
  }
  .add-row input {
    flex: 1;
  }
  .add-row button {
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text);
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-3);
    cursor: pointer;
  }
  .actions {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
    align-items: flex-start;
  }
  .primary {
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
    cursor: default;
  }
  .demo-note {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
</style>
