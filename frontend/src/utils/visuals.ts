/**
 * Maps domain values to design-system tokens, colour + icon + label triples.
 * Used by both the list UI and the map so change states and categories never
 * rely on colour alone (Design Principle 4, NFR-14).
 */
import type { ChangeType, ExperienceCategory, LocalSignal, Severity } from '../types'
import type { IconName } from '../components/Icon.svelte'
import { t } from '../copy/i18n'

export interface Visual {
  color: string
  icon: IconName
  label: string
}

export const CHANGE_VISUALS: Record<ChangeType, Visual> = {
  added: { color: 'var(--change-added)', icon: 'plus', label: t('change.added') },
  replaced: { color: 'var(--change-replaced)', icon: 'swap', label: t('change.replaced') },
  moved: { color: 'var(--change-moved)', icon: 'clock-arrow', label: t('change.moved') },
  removed: { color: 'var(--change-removed)', icon: 'minus', label: t('change.removed') },
  kept: { color: 'var(--change-preserved)', icon: 'check', label: t('change.kept') },
}

export const CATEGORY_VISUALS: Record<ExperienceCategory, Visual> = {
  food: { color: 'var(--cat-food)', icon: 'food', label: 'Food' },
  cafe: { color: 'var(--cat-cafe)', icon: 'cafe', label: 'Coffee' },
  nature: { color: 'var(--cat-nature)', icon: 'nature', label: 'Nature' },
  culture: { color: 'var(--cat-culture)', icon: 'culture', label: 'Culture' },
  shopping: { color: 'var(--cat-shopping)', icon: 'shopping', label: 'Shopping' },
  nightlife: { color: 'var(--cat-nightlife)', icon: 'nightlife', label: 'Nightlife' },
  event: { color: 'var(--cat-event)', icon: 'event', label: 'Event' },
  landmark: { color: 'var(--cat-landmark)', icon: 'landmark', label: 'Landmark' },
}

export const SEVERITY_VISUALS: Record<Severity, Visual> = {
  hard: { color: 'var(--color-danger)', icon: 'alert', label: t('validation.hardBadge') },
  soft: { color: 'var(--color-warning)', icon: 'warning', label: t('validation.softBadge') },
  'data-gap': { color: 'var(--color-text-muted)', icon: 'info', label: t('validation.unknownBadge') },
}

export const LOCAL_SIGNAL_VISUALS: Record<LocalSignal, Visual | null> = {
  tourist: { color: 'var(--color-info)', icon: 'landmark', label: t('validation.popularSight') },
  local: { color: 'var(--color-success)', icon: 'check', label: t('validation.localPick') },
  hidden: { color: 'var(--color-brand)', icon: 'nature', label: t('validation.hiddenGem') },
  unknown: null,
}

export function categoryVisual(category: string | undefined): Visual {
  return (
    CATEGORY_VISUALS[category as ExperienceCategory] ?? {
      color: 'var(--color-text-muted)',
      icon: 'landmark',
      label: category ?? t('common.unknown'),
    }
  )
}

export function categoryToken(category: string | undefined): string {
  const map: Record<string, string> = {
    food: '#E69F00',
    cafe: '#A0522D',
    nature: '#009E73',
    culture: '#56B4E9',
    shopping: '#CC79A7',
    nightlife: '#6A4C93',
    event: '#D55E00',
    landmark: '#5B6675',
  }
  return map[category ?? ''] ?? '#5B6675'
}
