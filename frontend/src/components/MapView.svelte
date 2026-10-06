<script lang="ts">
  /**
   * MapView (guide 4.4): pins by category, route legs with times, a diff layer
   * kept dashed until the summary closes, and an always-visible legend.
   *
   * With VITE_MAPBOX_PUBLIC_TOKEN set it renders Mapbox GL JS. Without a token
   * (the default demo) it falls back to a schematic SVG map that uses the exact
   * same data, so reviews and tests never depend on the provider.
   */
  import { t } from '../copy/i18n'
  import type { Itinerary, LatLng, Place } from '../types'
  import { CATEGORY_VISUALS, CHANGE_VISUALS, categoryToken } from '../utils/visuals'
  import { boundsFor, collectPoints, projectToView } from '../utils/map'
  import Icon from './Icon.svelte'
  import MapboxCanvas from './MapboxCanvas.svelte'

  interface Props {
    itinerary: Itinerary | null
    day: number | null
    focusPlace?: Place | null
    showDiff?: boolean
    onselect?: (place: Place) => void
  }

  let { itinerary, day, focusPlace = null, showDiff = false, onselect }: Props = $props()

  const token = import.meta.env.VITE_MAPBOX_PUBLIC_TOKEN ?? ''
  const width = 800
  const height = 520

  const days = $derived(day ? (itinerary?.days.filter((d) => d.day === day) ?? []) : (itinerary?.days ?? []))
  const points = $derived(collectPoints(itinerary, day ?? undefined))
  const bounds = $derived(boundsFor(points))
  let reducedMotion = $state(false)

  $effect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    reducedMotion = mq.matches
    const handler = (e: MediaQueryListEvent) => {
      reducedMotion = e.matches
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  })

  function pos(p: LatLng) {
    return projectToView(p, bounds, width, height)
  }

  const categoriesUsed = $derived([
    ...new Set(days.flatMap((d) => d.activities.map((a) => a.place.experience_types[0]))),
  ])
  const changedLegs = $derived(days.flatMap((d) => d.legs.filter((l) => l.changed)))
</script>

<section class="map" aria-label={t('itinerary.mapTab')}>
  {#if token}
    <div class="mapbox" data-testid="mapbox">
      <MapboxCanvas {itinerary} {day} {focusPlace} {showDiff} {token} {reducedMotion} />
    </div>
  {:else}
    <svg
      class="schematic"
      viewBox="0 0 {width} {height}"
      role="img"
      aria-label={t('itinerary.mapTab')}
      data-testid="schematic-map"
    >
      <rect width={width} height={height} fill="var(--color-surface)" />
      <!-- subtle grid -->
      {#each Array.from({ length: 9 }) as _, i (i)}
        <line x1={(i * width) / 8} y1="0" x2={(i * width) / 8} y2={height} stroke="var(--color-border)" opacity="0.35" />
      {/each}
      {#each Array.from({ length: 6 }) as _, i (i)}
        <line x1="0" y1={(i * height) / 5} x2={width} y2={(i * height) / 5} stroke="var(--color-border)" opacity="0.35" />
      {/each}

      <!-- route legs -->
      {#each days as d (d.day)}
        {#each d.legs as leg (leg.from_activity_id + leg.to_activity_id)}
          {@const a = d.activities.find((x) => x.id === leg.from_activity_id)}
          {@const b = d.activities.find((x) => x.id === leg.to_activity_id)}
          {#if a && b}
            {@const pa = pos(a.place)}
            {@const pb = pos(b.place)}
            <line
              x1={pa.x}
              y1={pa.y}
              x2={pb.x}
              y2={pb.y}
              class="leg"
              class:changed={showDiff && leg.changed}
              stroke={showDiff && leg.changed ? 'var(--change-moved)' : 'var(--color-brand)'}
              stroke-width={showDiff && leg.changed ? 3 : 2}
              stroke-dasharray={showDiff && leg.changed ? '6 6' : undefined}
            />
            <text x={(pa.x + pb.x) / 2} y={(pa.y + pb.y) / 2 - 4} class="leg-time">
              {leg.duration_min} min
            </text>
          {/if}
        {/each}
      {/each}

      <!-- markers -->
      {#each points as place (place.id)}
        {@const p = pos(place)}
        {@const cat = place.experience_types[0]}
        {@const isFocus = focusPlace?.id === place.id}
        <g
          class="marker"
          class:focus={isFocus}
          role="button"
          tabindex="0"
          aria-label={place.name}
          onclick={() => onselect?.(place)}
          onkeydown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') onselect?.(place)
          }}
        >
          <circle
            cx={p.x}
            cy={p.y}
            r={isFocus ? 12 : 9}
            fill={categoryToken(cat)}
            stroke="var(--color-bg)"
            stroke-width="2"
          />
        </g>
      {/each}
    </svg>
  {/if}

  <div class="legend" role="group" aria-label={t('a11y.mapLegend')}>
    {#each categoriesUsed as category (category)}
      <span class="legend-item">
        <span class="swatch" style:background={categoryToken(category as string)}></span>
        <Icon
          name={CATEGORY_VISUALS[category as keyof typeof CATEGORY_VISUALS]?.icon ?? 'landmark'}
          size={12}
        />
        {CATEGORY_VISUALS[category as keyof typeof CATEGORY_VISUALS]?.label ?? category}
      </span>
    {/each}
    {#if showDiff && changedLegs.length}
      <span class="legend-item diff" aria-label={t('a11y.routeDiff')}>
        <span class="swatch dashed"></span>
        <Icon name={CHANGE_VISUALS.moved.icon} size={12} />
        {CHANGE_VISUALS.moved.label}
      </span>
    {/if}
  </div>
</section>

<style>
  .map {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 320px;
    border-radius: var(--radius-md);
    overflow: hidden;
    border: 1px solid var(--color-border);
  }
  .schematic {
    display: block;
    width: 100%;
    height: 100%;
  }
  .leg {
    transition: stroke var(--dur-base) var(--ease-out);
  }
  .leg.changed {
    animation: dash 0.6s var(--ease-out) once;
  }
  @keyframes dash {
    from {
      stroke-dashoffset: 24;
    }
    to {
      stroke-dashoffset: 0;
    }
  }
  .leg-time {
    font-size: 18px;
    fill: var(--color-text-muted);
    text-anchor: middle;
  }
  .marker {
    cursor: pointer;
  }
  .marker:focus-visible circle {
    outline: 3px solid var(--color-brand);
  }
  .marker.focus circle {
    filter: drop-shadow(0 0 4px var(--color-brand));
  }
  .legend {
    position: absolute;
    left: var(--space-2);
    bottom: var(--space-2);
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-2);
    background: color-mix(in srgb, var(--color-bg) 88%, transparent);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--space-2);
    max-width: calc(100% - var(--space-4));
  }
  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: var(--space-1);
    font-size: var(--text-xs);
    color: var(--color-text);
  }
  .swatch {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
  }
  .swatch.dashed {
    width: 16px;
    height: 0;
    border-top: 2px dashed var(--change-moved);
    border-radius: 0;
  }
  @media (max-width: 767px) {
    .legend {
      display: none;
    }
  }
</style>
