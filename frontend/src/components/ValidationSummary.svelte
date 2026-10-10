<script lang="ts">
  import { t } from '../copy/i18n'
  import type { ValidationResult } from '../types'
  import { SEVERITY_VISUALS } from '../utils/visuals'
  import Icon from './Icon.svelte'

  interface Props {
    results: ValidationResult[]
    /** When true, show the reassuring all-pass line if there is nothing wrong. */
    showPass?: boolean
    /** Travel limit, interpolated into the leg message. */
    maxTravelMin?: number
    onMixItUp?: () => void
  }

  let { results, showPass = true, maxTravelMin = 30, onMixItUp }: Props = $props()

  /** Map validator rule codes to the UX copy guide's user-facing sentences. */
  function messageFor(result: ValidationResult): string {
    switch (result.message) {
      case 'leg_over_limit':
        return t('validation.msgLeg', { max: maxTravelMin })
      case 'consecutive_same_category':
        return t('validation.msgSameCategory')
      case 'low_variety':
        return t('validation.msgLowVariety')
      case 'over_budget':
        return t('validation.msgOverBudget')
      case 'outside_hours':
        return t('validation.msgOutsideHours')
      case 'unknown_cost':
        return t('validation.unknownCost')
      default:
        return result.message
    }
  }

  const problems = $derived(results.filter((r) => !r.passed))
  const hard = $derived(problems.filter((r) => r.severity === 'hard'))
  const soft = $derived(problems.filter((r) => r.severity === 'soft'))
  const gaps = $derived(problems.filter((r) => r.severity === 'data-gap'))
  const allGood = $derived(hard.length === 0 && soft.length === 0)
</script>

<section class="summary" aria-label={t('a11y.validationSummary')}>
  {#if allGood && showPass}
    <p class="line pass">
      <Icon name="check" size={16} />
      <span>{t('validation.pass')}</span>
    </p>
  {/if}

  {#each hard as result (result.id)}
    <p class="line" style:--line-color={SEVERITY_VISUALS[result.severity].color}>
      <Icon name={SEVERITY_VISUALS[result.severity].icon} size={16} />
      <span>{messageFor(result)}</span>
    </p>
  {/each}

  {#each soft as result (result.id)}
    <p class="line" style:--line-color={SEVERITY_VISUALS[result.severity].color}>
      <Icon name={SEVERITY_VISUALS[result.severity].icon} size={16} />
      <span>{messageFor(result)}</span>
      {#if onMixItUp}
        <button type="button" class="mix" onclick={onMixItUp}>{t('validation.mixItUp')}</button>
      {/if}
    </p>
  {/each}

  {#each gaps as result (result.id)}
    <p class="line muted" style:--line-color={SEVERITY_VISUALS[result.severity].color}>
      <Icon name={SEVERITY_VISUALS[result.severity].icon} size={16} />
      <span>{messageFor(result)}</span>
    </p>
  {/each}
</section>

<style>
  .summary {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }
  .line {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin: 0;
    font-size: var(--text-sm);
    color: var(--line-color, var(--color-text));
    line-height: var(--lh-body);
  }
  .line.pass {
    color: var(--color-success);
  }
  .line.muted {
    color: var(--color-text-muted);
  }
  .mix {
    margin-left: auto;
    border: 1px solid currentColor;
    background: transparent;
    color: inherit;
    border-radius: var(--radius-pill);
    padding: 2px var(--space-3);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    cursor: pointer;
  }
  .mix:hover {
    background: var(--color-warning-soft);
  }
</style>
