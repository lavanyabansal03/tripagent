<script lang="ts">
  import { t } from '../copy/i18n'
  import type { RunStatus } from '../types'
  import Icon from './Icon.svelte'

  interface Props {
    run: RunStatus | null
  }

  let { run }: Props = $props()

  // Step messages map to real graph nodes (UX Copy Guide, "Planning in progress").
  const stepKeys = ['reading', 'finding', 'checking', 'arranging', 'backups', 'doubleChecking']
  const stepIndex = $derived(run?.step_index ?? 0)
  const total = $derived(run?.step_count ?? stepKeys.length)
  const degraded = $derived(run?.status === 'failed')
  let slow = $state(false)

  // "Still working..." after 12s (copy guide).
  $effect(() => {
    slow = false
    run?.status
    const id = setTimeout(() => {
      slow = true
    }, 12_000)
    return () => clearTimeout(id)
  })
</script>

<section class="progress" aria-live="polite" aria-busy={run?.status === 'running'}>
  <h2>{t('planning.title')}</h2>
  <ol class="steps">
    {#each stepKeys as key, i (key)}
      <li
        class="step"
        class:done={i < stepIndex}
        class:current={i === stepIndex && run?.status === 'running'}
      >
        <span class="marker">
          {#if i < stepIndex}
            <Icon name="check" size={14} />
          {:else if i === stepIndex && run?.status === 'running'}
            <Icon name="spinner" size={14} />
          {:else}
            <span class="dot"></span>
          {/if}
        </span>
        <span class="text">{t(`planning.steps.${key}`)}</span>
      </li>
    {/each}
  </ol>
  <div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax={total} aria-valuenow={stepIndex}>
    <div class="fill" style:width="{(stepIndex / total) * 100}%"></div>
  </div>
  {#if slow && run?.status === 'running'}
    <p class="slow">
      <Icon name="info" size={14} />
      {t('planning.slow')}
    </p>
  {/if}
  {#if degraded}
    <p class="slow warning">
      <Icon name="warning" size={14} />
      {t('planning.degraded')}
    </p>
  {/if}
</section>

<style>
  .progress {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    max-width: 520px;
    margin: var(--space-12) auto;
    padding: var(--space-6);
    background: var(--color-surface-raised);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-1);
  }
  h2 {
    margin: 0;
    font-size: var(--text-lg);
  }
  .steps {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  .step {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }
  .step.done {
    color: var(--color-text);
  }
  .step.current {
    color: var(--color-brand);
    font-weight: var(--weight-medium);
  }
  .marker {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    flex: none;
  }
  .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--color-border);
  }
  .bar {
    height: 6px;
    border-radius: var(--radius-pill);
    background: var(--color-surface);
    overflow: hidden;
  }
  .fill {
    height: 100%;
    background: var(--color-brand);
    transition: width var(--dur-base) var(--ease-out);
  }
  .slow {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin: 0;
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }
  .slow.warning {
    color: var(--color-warning);
  }
</style>
