<script lang="ts">
  /**
   * Inline SVG icon set. Every status/category pairs a colour with an icon and a
   * word (Design Principle 4, NFR-14 — never colour alone). `currentColor` lets
   * callers tint via tokens.
   */
  export type IconName =
    | 'plus'
    | 'swap'
    | 'clock-arrow'
    | 'minus'
    | 'check'
    | 'lock'
    | 'unlock'
    | 'warning'
    | 'alert'
    | 'info'
    | 'cafe'
    | 'food'
    | 'nature'
    | 'culture'
    | 'shopping'
    | 'nightlife'
    | 'event'
    | 'landmark'
    | 'map'
    | 'route'
    | 'trace'
    | 'sun'
    | 'moon'
    | 'close'
    | 'chevron-down'
    | 'chevron-up'
    | 'arrow-left'
    | 'undo'
    | 'refresh'
    | 'spinner'

  interface Props {
    name: IconName
    size?: number
    label?: string
    class?: string
  }

  let { name, size = 16, label, class: className = '' }: Props = $props()

  const paths: Record<IconName, string> = {
    plus: 'M8 3v10M3 8h10',
    swap: 'M3 5h9l-2.5-2.5M13 11H4l2.5 2.5',
    'clock-arrow':
      'M8 4v4l3 2M13.5 8a5.5 5.5 0 1 0-1.6 3.9M13 4v3h-3',
    minus: 'M3 8h10',
    check: 'M3 8.5l3.5 3.5L13 4.5',
    lock: 'M4 7V5a4 4 0 0 1 8 0v2M3.5 7h9v6h-9z',
    unlock: 'M4 7V5a4 4 0 0 1 7.5-2M3.5 7h9v6h-9z',
    warning: 'M8 2.5L14.5 13.5h-13zM8 6.5v3M8 11.5h.01',
    alert: 'M8 2.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11zM8 5v3.5M8 11h.01',
    info: 'M8 2.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11zM8 7.5V11M8 5h.01',
    cafe: 'M3 4h9v5a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4zM12 5h1.5a2 2 0 0 1 0 4H12M3 13.5h10',
    food: 'M4 3v5a2 2 0 0 0 4 0V3M6 10v3M10 3c1 1.5 1 4 0 5.5V13',
    nature: 'M8 2L3.5 8h3L4 12h8l-2.5-4h3zM8 12v2',
    culture: 'M3 6l5-3 5 3M4 6v6M8 6v6M12 6v6M3 12.5h10',
    shopping: 'M4 5h8l-1 8H5zM6 5a2 2 0 0 1 4 0',
    nightlife: 'M6 2h4l-2 4zM6 2v12M4.5 14h7M10 7l4-1-1 6z',
    event: 'M3 4h10v9H3zM3 7h10M5.5 2.5v3M10.5 2.5v3',
    landmark: 'M8 2l5 3H3zM4 5v6M8 5v6M12 5v6M3 11.5h10M3 13.5h10',
    map: 'M2.5 4l4-1.5 3 1.5 4-1.5v9l-4 1.5-3-1.5-4 1.5zM6.5 2.5v9M9.5 4v9',
    route: 'M4 3a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM12 9a2 2 0 1 0 0 4 2 2 0 0 0 0-4zM4 7c0 3 4 1 4 4s4 1 4 4',
    trace: 'M2.5 3h11M2.5 6.5h7M2.5 10h9M2.5 13.5h5',
    sun: 'M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5zM8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1 1M11.6 11.6l1 1M12.6 3.4l-1 1M4.4 11.6l-1 1',
    moon: 'M13 9.5A5.5 5.5 0 0 1 6.5 3a5.5 5.5 0 1 0 6.5 6.5z',
    close: 'M4 4l8 8M12 4l-8 8',
    'chevron-down': 'M4 6l4 4 4-4',
    'chevron-up': 'M4 10l4-4 4 4',
    'arrow-left': 'M13 8H3M7 4L3 8l4 4',
    undo: 'M6 4L2.5 7.5 6 11M2.5 7.5H10a3.5 3.5 0 0 1 0 7H8',
    refresh: 'M13 8a5 5 0 1 1-1.5-3.5M13 2.5V5h-2.5',
    spinner: '',
  }

  const d = $derived(paths[name])
  const isSpinner = $derived(name === 'spinner')
</script>

<svg
  class="icon {className}"
  width={size}
  height={size}
  viewBox="0 0 16 16"
  fill="none"
  stroke="currentColor"
  stroke-width="1.6"
  stroke-linecap="round"
  stroke-linejoin="round"
  role={label ? 'img' : 'presentation'}
  aria-hidden={label ? undefined : 'true'}
  aria-label={label}
  class:spin={isSpinner}
>
  {#if isSpinner}
    <circle cx="8" cy="8" r="5.5" opacity="0.25" />
    <path d="M13.5 8a5.5 5.5 0 0 0-5.5-5.5" />
  {:else}
    <path d={d} />
  {/if}
</svg>

<style>
  .icon {
    display: inline-block;
    vertical-align: middle;
    flex: none;
  }
  .spin {
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
