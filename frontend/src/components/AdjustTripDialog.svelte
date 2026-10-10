<script lang="ts">
  import { t } from '../copy/i18n'
  import type { ChangeEvent } from '../types'
  import Icon from './Icon.svelte'

  interface Props {
    open: boolean
    busy?: boolean
    onsubmit: (text: string) => void
    onquick: (typed: Partial<ChangeEvent>) => void
    onclose: () => void
  }

  let { open, busy = false, onsubmit, onquick, onclose }: Props = $props()
  let text = $state('')

  const quickActions = [
    { key: 'quickRunningLate', typed: { type: 'time', payload: { minutes: 90 } } },
    { key: 'quickLowerBudget', typed: { type: 'budget', payload: { budget: 300 } } },
    { key: 'quickSwitchWalking', typed: { type: 'transport', payload: { mode: 'walking' } } },
    { key: 'quickSkip', typed: { type: 'preference', payload: { avoid: ['shopping'] } } },
    {
      key: 'quickCoffeeOnTheWay',
      typed: {
        type: 'preference',
        payload: { interests: ['coffee'], along_route: true, trigger: 'you wanted coffee on the way' },
      },
    },
  ] as const

  function submit() {
    if (!text.trim()) return
    onsubmit(text.trim())
    text = ''
  }
</script>

{#if open}
  <div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && onclose()}>
    <div class="dialog" role="dialog" aria-modal="true" aria-labelledby="adjust-title">
      <header>
        <h2 id="adjust-title">{t('adjust.dialogTitle')}</h2>
        <button type="button" class="close" aria-label={t('common.close')} onclick={onclose}>
          <Icon name="close" size={18} />
        </button>
      </header>

      <textarea
        rows="3"
        bind:value={text}
        placeholder={t('adjust.placeholder')}
        disabled={busy}
        onkeydown={(e) => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit()
        }}
      ></textarea>

      <fieldset class="quick">
        <legend>{t('adjust.quickActionsLabel')}</legend>
        <div class="quick-row">
          {#each quickActions as action (action.key)}
            <button type="button" class="quick-chip" disabled={busy} onclick={() => onquick(action.typed)}>
              {t(`adjust.${action.key}`)}
            </button>
          {/each}
        </div>
      </fieldset>

      <footer>
        <button type="button" class="ghost" onclick={onclose}>{t('adjust.cancel')}</button>
        <button type="button" class="primary" disabled={busy || !text.trim()} onclick={submit}>
          {busy ? t('adjust.working') : t('adjust.cta')}
        </button>
      </footer>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(15, 20, 25, 0.5);
    display: grid;
    place-items: center;
    padding: var(--space-4);
    z-index: 40;
  }
  .dialog {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    width: min(560px, 100%);
    background: var(--color-surface-raised);
    border-radius: var(--radius-lg);
    padding: var(--space-6);
    box-shadow: var(--shadow-3);
  }
  header {
    display: flex;
    align-items: center;
  }
  h2 {
    margin: 0;
    font-size: var(--text-xl);
  }
  .close {
    margin-left: auto;
    border: none;
    background: transparent;
    color: var(--color-text-muted);
    cursor: pointer;
    display: inline-flex;
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
  }
  .quick {
    border: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  legend {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.02em;
  }
  .quick-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }
  .quick-chip {
    border: 1px solid var(--color-border);
    background: var(--color-surface);
    color: var(--color-text);
    border-radius: var(--radius-pill);
    padding: var(--space-1) var(--space-3);
    font-size: var(--text-sm);
    cursor: pointer;
  }
  .quick-chip:hover {
    border-color: var(--color-brand);
    color: var(--color-brand);
  }
  footer {
    display: flex;
    justify-content: flex-end;
    gap: var(--space-2);
  }
  .ghost {
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
  .primary:disabled {
    opacity: 0.6;
    cursor: default;
  }
</style>
