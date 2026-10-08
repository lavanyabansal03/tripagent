<script lang="ts">
  import { t } from '../copy/i18n'
  import type { Question } from '../types'

  interface Props {
    questions: Question[]
    onsubmit: (answers: Record<string, string>) => void
    onskip?: () => void
    busy?: boolean
  }

  let { questions, onsubmit, onskip, busy = false }: Props = $props()
  let answers = $state<Record<string, string>>({})

  // Up to 3 questions per round (FR-34).
  const shown = $derived(questions.slice(0, 3))

  function submit() {
    onsubmit(answers)
  }
</script>

<form
  class="clarify"
  aria-labelledby="clarify-title"
  onsubmit={(e) => {
    e.preventDefault()
    submit()
  }}
>
  <h2 id="clarify-title">{t('clarify.intro')}</h2>
  <p class="count">{t('clarify.questionCount', { count: shown.length })}</p>

  {#each shown as q (q.id)}
    <fieldset class="question">
      <legend>{q.text === 'contradiction' ? t('clarify.contradiction') : q.text}</legend>
      {#if q.options}
        <div class="options">
          {#each q.options as option (option)}
            <label class="option">
              <input
                type="radio"
                name={q.id}
                value={option}
                checked={answers[q.id] === option}
                onchange={() => (answers[q.id] = option)}
              />
              {option}
            </label>
          {/each}
        </div>
      {:else}
        <input
          type="text"
          placeholder={t('clarify.answerPlaceholder')}
          value={answers[q.id] ?? ''}
          oninput={(e) => (answers[q.id] = (e.currentTarget as HTMLInputElement).value)}
        />
      {/if}
    </fieldset>
  {/each}

  <div class="actions">
    {#if onskip}
      <button type="button" class="skip" onclick={onskip}>{t('clarify.skip')}</button>
    {/if}
    <button type="submit" class="primary" disabled={busy}>
      {busy ? t('clarify.submitting') : t('clarify.submit')}
    </button>
  </div>
</form>

<style>
  .clarify {
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    background: var(--color-surface-raised);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--space-6);
    box-shadow: var(--shadow-1);
  }
  h2 {
    margin: 0;
    font-size: var(--text-lg);
  }
  .count {
    margin: 0;
    color: var(--color-text-muted);
    font-size: var(--text-sm);
  }
  .question {
    border: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  legend {
    font-weight: var(--weight-medium);
    font-size: var(--text-sm);
    margin-bottom: var(--space-1);
  }
  .options {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
  }
  .option {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-pill);
    padding: var(--space-1) var(--space-3);
    font-size: var(--text-sm);
    cursor: pointer;
  }
  .option:has(input:checked) {
    border-color: var(--color-brand);
    background: var(--color-brand-soft);
  }
  input[type='text'] {
    font: inherit;
    padding: var(--space-2) var(--space-3);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
  }
  .actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--space-2);
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
  .skip {
    background: transparent;
    border: 1px solid var(--color-border);
    color: var(--color-text);
    border-radius: var(--radius-md);
    padding: var(--space-2) var(--space-4);
    cursor: pointer;
  }
</style>
