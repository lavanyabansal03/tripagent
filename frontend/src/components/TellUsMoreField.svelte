<script lang="ts">
  import { t } from '../copy/i18n'

  interface Props {
    value?: string
    max?: number
    label?: string
    placeholder?: string
    helper?: string
    onchange?: (value: string) => void
  }

  let {
    value = $bindable(''),
    max = 1000,
    label = t('setup.freeTextLabel'),
    placeholder = t('setup.freeTextPlaceholder'),
    helper = t('setup.freeTextHelper'),
    onchange,
  }: Props = $props()

  const overLimit = $derived(value.length > max)

  function update(next: string) {
    value = next
    onchange?.(next)
  }
</script>

<div class="field">
  <label for="tell-us-more">{label}</label>
  <textarea
    id="tell-us-more"
    rows="5"
    placeholder={placeholder}
    aria-describedby="tell-us-more-help"
    aria-invalid={overLimit}
    value={value.slice(0, max)}
    oninput={(e) => update((e.currentTarget as HTMLTextAreaElement).value)}
  ></textarea>
  <div class="meta">
    <p id="tell-us-more-help" class="helper">{helper}</p>
    <span class="counter" class:over={overLimit}>
      {#if overLimit}
        {t('setup.freeTextOverLimit', { max })}
      {:else}
        {t('setup.freeTextCounter', { count: value.length, max })}
      {/if}
    </span>
  </div>
</div>

<style>
  .field {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  label {
    font-size: var(--text-sm);
    font-weight: var(--weight-medium);
  }
  textarea {
    font: inherit;
    line-height: var(--lh-body);
    padding: var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
    resize: vertical;
    min-height: 120px;
  }
  textarea:focus-visible {
    outline: 2px solid var(--color-brand);
    outline-offset: 1px;
  }
  .meta {
    display: flex;
    justify-content: space-between;
    gap: var(--space-3);
    align-items: baseline;
  }
  .helper {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
  .counter {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    white-space: nowrap;
  }
  .counter.over {
    color: var(--color-warning);
  }
</style>
