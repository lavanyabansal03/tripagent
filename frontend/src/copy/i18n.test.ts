import { describe, it, expect } from 'vitest'
import {
  formatCost,
  formatMoney,
  formatRelativeWhen,
  isStale,
  resolvePluralForTest,
  t,
} from './i18n'

describe('i18n', () => {
  it('interpolates named placeholders', () => {
    expect(t('itinerary.version', { version: 3 })).toBe('v3')
  })

  it('formats ICU plurals', () => {
    expect(t('validation.backupsCount', { count: 1 })).toBe('1 backup')
    expect(t('validation.backupsCount', { count: 2 })).toBe('2 backups')
  })

  it('never concatenates currency symbols manually', () => {
    const formatted = formatMoney(15)
    expect(formatted).toMatch(/\$15/)
  })

  it('labels estimated cost ranges', () => {
    const text = formatCost(20, 15, 35, 'price_level')
    expect(text).toContain('15')
    expect(text).toContain('35')
  })

  it('labels unknown cost and free explicitly', () => {
    expect(formatCost(null, null, null, 'unknown')).toBe('Cost unknown')
    expect(formatCost(0, 0, 0, 'free')).toBe('Free')
  })

  it('describes recency in user terms', () => {
    const now = new Date('2026-10-14T12:00:00Z')
    expect(formatRelativeWhen('2026-10-14T09:40:00Z', now)).toContain('today')
    const threeDays = new Date(now.getTime() - 3 * 86_400_000).toISOString()
    expect(formatRelativeWhen(threeDays, now)).toBe('3 days ago')
  })

  it('marks data stale past its max age (FR-39)', () => {
    const now = new Date('2026-10-14T12:00:00Z')
    const old = new Date(now.getTime() - 8 * 86_400_000).toISOString()
    const fresh = new Date(now.getTime() - 60_000).toISOString()
    expect(isStale(old, 24 * 7, now)).toBe(true)
    expect(isStale(fresh, 24 * 7, now)).toBe(false)
  })

  it('falls back to the key when a string is missing', () => {
    expect(t('does.not.exist')).toBe('does.not.exist')
  })
})

describe('plural helper', () => {
  it('resolves exact and category branches', () => {
    expect(resolvePluralForTest('{n, plural, one {# thing} other {# things}}', 1)).toBe('1 thing')
    expect(resolvePluralForTest('{n, plural, one {# thing} other {# things}}', 5)).toBe('5 things')
  })
})
