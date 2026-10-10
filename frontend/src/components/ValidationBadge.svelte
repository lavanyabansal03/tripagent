<script lang="ts">
  import { t } from '../copy/i18n'
  import type { Severity } from '../types'
  import { SEVERITY_VISUALS } from '../utils/visuals'
  import Icon from './Icon.svelte'

  interface Props {
    severity: Severity | 'pass'
    title?: string
  }

  let { severity, title }: Props = $props()
  const visual = $derived(
    severity === 'pass'
      ? { color: 'var(--color-success)', icon: 'check' as const, label: t('validation.passBadge') }
      : SEVERITY_VISUALS[severity],
  )
</script>

<span
  class="badge"
  style:--badge-color={visual.color}
  title={title ?? visual.label}
  aria-label={visual.label}
>
  <Icon name={visual.icon} size={13} />
  <span>{visual.label}</span>
</span>

<style>
  .badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    padding: 1px var(--space-2);
    border-radius: var(--radius-pill);
    font-size: var(--text-xs);
    font-weight: var(--weight-medium);
    color: var(--badge-color);
    background: color-mix(in srgb, var(--badge-color) 12%, transparent);
    border: 1px solid color-mix(in srgb, var(--badge-color) 40%, transparent);
  }
</style>
