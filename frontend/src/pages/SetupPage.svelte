<script lang="ts">
  import { t } from '../copy/i18n'
  import type { TripFormInput } from '../api/client'
  import { store } from '../state/store.svelte'
  import TripForm from '../components/TripForm.svelte'
  import InfeasibleNotice from '../components/InfeasibleNotice.svelte'

  async function handleSubmit(input: TripFormInput) {
    await store.createTrip(input)
  }
</script>

{#if store.error && !store.itinerary}
  <InfeasibleNotice
    report={{ blocking_rule: 'error', explanation: 'errors.unknown', suggestions: [] }}
    onrelax={() => store.setError(null)}
  />
{/if}

<TripForm onsubmit={handleSubmit} busy={store.busy} />

{#if store.busy}
  <p class="sr-status" role="status">{t('common.loading')}</p>
{/if}

<style>
  .sr-status {
    text-align: center;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }
</style>
