<script lang="ts">
  /** AgentTrace — timeline of nodes, tools, LLM calls and loop iterations (FR-20). */
  import { t } from '../copy/i18n'
  import type { ExecutionEvent } from '../types'
  import { formatTime } from '../copy/i18n'
  import Icon from './Icon.svelte'

  interface Props {
    events: ExecutionEvent[]
  }

  let { events }: Props = $props()
  let filter = $state<'all' | ExecutionEvent['type']>('all')

  const filters: Array<{ value: typeof filter; key: string }> = [
    { value: 'all', key: 'filterAll' },
    { value: 'node', key: 'filterNode' },
    { value: 'tool', key: 'filterTool' },
    { value: 'llm', key: 'filterLlm' },
    { value: 'validation', key: 'filterValidation' },
    { value: 'loop', key: 'filterLoop' },
  ]

  const shown = $derived(
    filter === 'all' ? events : events.filter((e) => e.type === filter),
  )
</script>

<section class="trace" aria-labelledby="trace-title">
  <header>
    <div>
      <h2 id="trace-title">{t('trace.title')}</h2>
      <p class="subtitle">{t('trace.subtitle')}</p>
    </div>
    <div class="filters" role="group" aria-label={t('trace.title')}>
      {#each filters as f (f.value)}
        <button
          type="button"
          class="filter"
          class:active={filter === f.value}
          aria-pressed={filter === f.value}
          onclick={() => (filter = f.value)}
        >
          {t(`trace.${f.key}`)}
        </button>
      {/each}
    </div>
  </header>

  {#if shown.length === 0}
    <p class="empty">{t('trace.empty')}</p>
  {:else}
    <ol class="events">
      {#each shown as event (event.id)}
        <li class="event" data-type={event.type} data-status={event.status}>
          <span class="marker">
            <Icon
              name={event.type === 'tool' ? 'route' : event.type === 'validation' ? 'check' : event.type === 'loop' ? 'refresh' : 'trace'}
              size={13}
            />
          </span>
          <span class="body">
            <span class="row">
              <code class="node">{event.node}</code>
              <span class="type">{event.type}</span>
              {#if event.metadata?.loop}
                <span class="loop">{event.metadata.loop} · {t('trace.iteration', { n: event.iteration })}</span>
              {/if}
            </span>
            <span class="row meta">
              <span class="status" data-status={event.status}>
                {t(`trace.status${event.status.charAt(0).toUpperCase()}${event.status.slice(1)}`)}
              </span>
              <span class="duration">{t('trace.duration', { ms: event.duration_ms })}</span>
              <time class="ts" datetime={event.ts}>{formatTime(event.ts)}</time>
            </span>
          </span>
        </li>
      {/each}
    </ol>
  {/if}
</section>

<style>
  .trace {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
  }
  header {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  h2 {
    margin: 0;
    font-size: var(--text-lg);
  }
  .subtitle {
    margin: 0;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
  }
  .filter {
    border: 1px solid var(--color-border);
    background: transparent;
    color: var(--color-text-muted);
    border-radius: var(--radius-pill);
    padding: 1px var(--space-2);
    font-size: var(--text-xs);
    cursor: pointer;
  }
  .filter.active {
    border-color: var(--color-brand);
    color: var(--color-brand);
    background: var(--color-brand-soft);
  }
  .empty {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--color-text-muted);
  }
  .events {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
  }
  .event {
    display: flex;
    gap: var(--space-3);
    padding: var(--space-2) 0;
    border-bottom: 1px solid var(--color-border);
  }
  .marker {
    display: inline-flex;
    color: var(--color-text-muted);
    padding-top: 2px;
  }
  .body {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .row {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    flex-wrap: wrap;
  }
  .node {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--color-text);
    background: var(--color-surface);
    padding: 0 var(--space-1);
    border-radius: var(--radius-sm);
  }
  .type,
  .loop,
  .status,
  .duration,
  .ts {
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
  .loop {
    color: var(--color-info);
  }
  .status[data-status='ok'] {
    color: var(--color-success);
  }
  .status[data-status='failed'] {
    color: var(--color-danger);
  }
  .status[data-status='degraded'] {
    color: var(--color-warning);
  }
</style>
