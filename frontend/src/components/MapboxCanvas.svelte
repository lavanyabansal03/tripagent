<script lang="ts">
  /**
   * Mapbox GL JS renderer. Only loaded when VITE_MAPBOX_PUBLIC_TOKEN is set;
   * the browser receives only the URL-restricted public token (SRS Section 11).
   */
  import { onMount, onDestroy } from 'svelte'
  import type { Itinerary, Place } from '../types'
  import { tokens } from '../styles/tokens'
  import { categoryToken } from '../utils/visuals'
  import { MAPBOX_STYLE, MAPBOX_STYLE_DARK } from '../utils/map'

  interface Props {
    itinerary: Itinerary | null
    day: number | null
    focusPlace: Place | null
    showDiff: boolean
    token: string
    reducedMotion: boolean
  }

  let { itinerary, day, focusPlace, showDiff, token: mapToken, reducedMotion }: Props = $props()

  let container: HTMLDivElement
  let map: import('mapbox-gl').Map | null = null
  let ready = $state(false)

  const isDark = $derived(
    typeof document !== 'undefined' && document.documentElement.dataset.theme === 'dark',
  )

  onMount(async () => {
    const mod = await import('mapbox-gl')
    const mapboxgl = mod.default
    mapboxgl.accessToken = mapToken
    if (!container) return
    const instance = new mapboxgl.Map({
      container,
      style: isDark ? MAPBOX_STYLE_DARK : MAPBOX_STYLE,
      center: [-122.335, 47.625],
      zoom: 11.2,
      attributionControl: true,
    })
    map = instance
    instance.addControl(new mapboxgl.NavigationControl({ showCompass: false }), 'top-right')
    instance.on('load', () => {
      ready = true
      instance.addSource('route', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      instance.addLayer({
        id: 'route-line',
        type: 'line',
        source: 'route',
        paint: { 'line-color': tokens.color.brand, 'line-width': 3 },
      })
      instance.addSource('route-diff', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      instance.addLayer({
        id: 'route-diff-line',
        type: 'line',
        source: 'route-diff',
        paint: { 'line-color': tokens.change.moved, 'line-width': 3, 'line-dasharray': [2, 2] },
      })
      instance.addSource('places', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      instance.addLayer({
        id: 'places-circle',
        type: 'circle',
        source: 'places',
        paint: {
          'circle-radius': 8,
          'circle-color': ['get', 'color'],
          'circle-stroke-color': '#FFFFFF',
          'circle-stroke-width': 2,
        },
      })
      update()
    })
  })

  function setData(id: string, features: Array<Record<string, unknown>>) {
    if (!map) return
    const source = map.getSource(id) as import('mapbox-gl').GeoJSONSource | undefined
    source?.setData({ type: 'FeatureCollection', features } as never)
  }

  function update() {
    if (!map || !ready) return
    const days = day ? (itinerary?.days.filter((d) => d.day === day) ?? []) : (itinerary?.days ?? [])
    const places = days.flatMap((d) => d.activities.map((a) => a.place))
    setData(
      'places',
      places.map((p) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [p.lng, p.lat] },
        properties: { name: p.name, color: categoryToken(p.experience_types[0]) },
      })),
    )

    const lines: Array<Record<string, unknown>> = []
    const diffLines: Array<Record<string, unknown>> = []
    for (const d of days) {
      for (const leg of d.legs) {
        const feature = {
          type: 'Feature',
          geometry: { type: 'LineString', coordinates: leg.geometry.map((p) => [p.lng, p.lat]) },
          properties: {},
        }
        if (showDiff && leg.changed) diffLines.push(feature)
        else lines.push(feature)
      }
    }
    setData('route', lines)
    setData('route-diff', diffLines)

    if (places.length) {
      const lngs = places.map((p) => p.lng)
      const lats = places.map((p) => p.lat)
      map.fitBounds(
        [
          [Math.min(...lngs), Math.min(...lats)],
          [Math.max(...lngs), Math.max(...lats)],
        ],
        { padding: 60, duration: reducedMotion ? 0 : 400 },
      )
    }
  }

  $effect(() => {
    // Re-run whenever data, day or diff mode changes.
    void itinerary
    void day
    void showDiff
    update()
  })

  $effect(() => {
    if (!map || !focusPlace) return
    map.flyTo({
      center: [focusPlace.lng, focusPlace.lat],
      zoom: 14,
      duration: reducedMotion ? 0 : 500,
    })
  })

  onDestroy(() => {
    map?.remove()
    map = null
  })
</script>

<div class="canvas" bind:this={container} data-testid="mapbox-canvas"></div>

<style>
  .canvas {
    width: 100%;
    height: 100%;
    min-height: 320px;
  }
</style>
