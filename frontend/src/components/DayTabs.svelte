<script lang="ts">
  import { t } from '../copy/i18n'

  interface Props {
    days: Array<{ day: number; hasIssue: boolean }>
    active: number
    onchange: (day: number) => void
  }

  let { days, active, onchange }: Props = $props()
</script>

<div class="tabs" role="tablist" aria-label="Days">
  {#each days as d (d.day)}
    <button
      type="button"
      role="tab"
      id="day-tab-{d.day}"
      aria-selected={d.day === active}
      aria-controls="day-panel-{d.day}"
      class="tab"
      class:active={d.day === active}
      onclick={() => onchange(d.day)}
    >
      {t('itinerary.dayTab', { day: d.day })}
      {#if d.hasIssue}
        <span class="issue" role="img" aria-label={t('itinerary.dayTabHasIssue', { day: d.day })}></span>
      {/if}
    </button>
  {/each}
</div>

<style>
  .tabs {
    display: flex;
    gap: var(--space-1);
    border-bottom: 1px solid var(--color-border);
    overflow-x: auto;
  }
  .tab {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    border: none;
    background: transparent;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
    font-weight: var(--weight-medium);
    padding: var(--space-2) var(--space-4);
    border-bottom: 2px solid transparent;
    cursor: pointer;
    white-space: nowrap;
  }
  .tab.active {
    color: var(--color-brand);
    border-bottom-color: var(--color-brand);
  }
  .issue {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-warning);
    flex: none;
  }
</style>
