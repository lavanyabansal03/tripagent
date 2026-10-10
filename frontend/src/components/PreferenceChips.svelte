<script lang="ts">
  import { t } from '../copy/i18n'
  import type { Provenance } from '../types'
  import Icon from './Icon.svelte'

  interface Chip {
    key: string
    label: string
    provenance: Provenance
  }

  interface Props {
    chips: Chip[]
    editable?: boolean
    onchange?: (key: string, label: string) => void
    onremove?: (key: string) => void
  }

  let { chips, editable = true, onchange, onremove }: Props = $props()
  let editing = $state<string | null>(null)
  let draft = $state('')

  const provenanceLabel: Record<Provenance, string> = {
    explicit: t('understood.fromText'),
    inferred: t('understood.inferred'),
    default: t('understood.assumed'),
  }

  function beginEdit(chip: Chip) {
    editing = chip.key
    draft = chip.label
  }
  function commit(chip: Chip) {
    onchange?.(chip.key, draft.trim() || chip.label)
    editing = null
  }
</script>

<div class="chips" role="list" aria-label={t('understood.sectionTitle')}>
  {#each chips as chip (chip.key)}
    <div class="chip" role="listitem" data-provenance={chip.provenance}>
      {#if editing === chip.key}
        <input
          class="edit"
          bind:value={draft}
          aria-label={t('understood.editLabel', { label: chip.label })}
          onkeydown={(e) => {
            if (e.key === 'Enter') commit(chip)
            if (e.key === 'Escape') editing = null
          }}
          onblur={() => commit(chip)}
        />
      {:else}
        <button
          type="button"
          class="pill"
          onclick={() => editable && beginEdit(chip)}
          title={editable ? t('understood.editLabel', { label: chip.label }) : undefined}
        >
          <span class="text">{chip.label}</span>
        </button>
        <span class="provenance">{provenanceLabel[chip.provenance]}</span>
        {#if onremove}
          <button
            type="button"
            class="remove"
            aria-label={t('understood.remove', { label: chip.label })}
            onclick={() => onremove(chip.key)}
          >
            <Icon name="close" size={11} />
          </button>
        {/if}
      {/if}
    </div>
  {/each}
  {#if chips.length === 0}
    <p class="empty">{t('understood.empty')}</p>
  {/if}
</div>

<style>
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    align-items: flex-start;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-pill);
    background: var(--color-surface);
    padding: 2px var(--space-2) 2px 2px;
  }
  .chip[data-provenance='default'] {
    border-style: dashed;
    background: var(--color-warning-soft);
  }
  .chip[data-provenance='inferred'] {
    background: var(--color-info-soft);
  }
  .pill {
    border: none;
    background: transparent;
    color: var(--color-text);
    font-size: var(--text-sm);
    font-weight: var(--weight-medium);
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-pill);
    cursor: pointer;
  }
  .provenance {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    padding-right: var(--space-1);
  }
  .remove {
    border: none;
    background: transparent;
    color: var(--color-text-muted);
    cursor: pointer;
    padding: 0;
    display: inline-flex;
  }
  .edit {
    font: inherit;
    font-size: var(--text-sm);
    border: 1px solid var(--color-brand);
    border-radius: var(--radius-sm);
    padding: var(--space-1);
    min-width: 8ch;
    background: var(--color-bg);
    color: var(--color-text);
  }
  .empty {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }
</style>
