<script lang="ts">
  import { t } from '../copy/i18n'

  interface Props {
    value: number
    onchange?: (value: number) => void
  }

  let { value = $bindable(50), onchange }: Props = $props()

  function update(next: number) {
    value = next
    onchange?.(next)
  }
</script>

<div class="slider">
  <label class="label" for="tourist-local">{t('setup.sliderLabel')}</label>
  <input
    id="tourist-local"
    type="range"
    min="0"
    max="100"
    step="10"
    value={value}
    aria-valuetext="{value}% {t('setup.sliderRight')}"
    oninput={(e) => update(Number((e.currentTarget as HTMLInputElement).value))}
  />
  <div class="ends">
    <span>{t('setup.sliderLeft')}</span>
    <span class="ratio" aria-hidden="true">{value}%</span>
    <span>{t('setup.sliderRight')}</span>
  </div>
</div>

<style>
  .slider {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
  }
  .label {
    font-size: var(--text-sm);
    font-weight: var(--weight-medium);
    color: var(--color-text);
  }
  input[type='range'] {
    width: 100%;
    accent-color: var(--color-brand);
    height: 24px;
  }
  .ends {
    display: flex;
    justify-content: space-between;
    font-size: var(--text-xs);
    color: var(--color-text-muted);
  }
  .ratio {
    font-weight: var(--weight-semibold);
    color: var(--color-brand);
  }
</style>
