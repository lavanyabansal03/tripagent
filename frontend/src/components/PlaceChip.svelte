<script lang="ts">
  import { t } from '../copy/i18n'
  import type { ExperienceCategory, Place } from '../types'
  import { CATEGORY_VISUALS, LOCAL_SIGNAL_VISUALS } from '../utils/visuals'
  import Icon from './Icon.svelte'

  interface Props {
    place: Place
    removable?: boolean
    onremove?: (place: Place) => void
  }

  let { place, removable = false, onremove }: Props = $props()
  const signal = $derived(place.local_signal)
  const signalVisual = $derived(LOCAL_SIGNAL_VISUALS[signal])
</script>

<span class="chip">
  {#each place.experience_types.slice(0, 2) as category (category)}
    <Icon
      name={CATEGORY_VISUALS[category as ExperienceCategory].icon}
      size={12}
      label={CATEGORY_VISUALS[category as ExperienceCategory].label}
    />
  {/each}
  <span class="name">{place.name}</span>
  {#if signalVisual}
    <span class="signal" style:--signal-color={signalVisual.color} title={t('validation.signalTooltip')}>
      <Icon name={signalVisual.icon} size={11} />
      {signalVisual.label}
    </span>
  {/if}
  {#if removable}
    <button
      type="button"
      class="remove"
      aria-label={t('understood.remove', { label: place.name })}
      onclick={() => onremove?.(place)}
    >
      <Icon name="close" size={11} />
    </button>
  {/if}
</span>

<style>
  .chip {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    padding: var(--space-1) var(--space-2);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-pill);
    background: var(--color-surface);
    font-size: var(--text-xs);
    color: var(--color-text);
    max-width: 100%;
  }
  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 18ch;
  }
  .signal {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    color: var(--signal-color);
    font-weight: var(--weight-medium);
  }
  .remove {
    display: inline-flex;
    border: none;
    background: transparent;
    color: var(--color-text-muted);
    cursor: pointer;
    padding: 0;
  }
</style>
