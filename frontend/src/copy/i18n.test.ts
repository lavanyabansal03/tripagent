import { describe, it, expect } from 'vitest'
import {
  formatCost,
  formatMoney,
  formatPlaceTime,
  formatRelativeWhen,
  formatTripDate,
  isStale,
  resolvePluralForTest,
  t,
} from './i18n'

describe('formatTripDate', () => {
  it('shows trip days as US dates (mm/dd/yyyy)', () => {
    expect(formatTripDate('2026-11-27')).toBe('11/27/2026')
    expect(formatTripDate('2026-12-05')).toBe('12/05/2026')
    expect(formatTripDate('2027-01-01')).toBe('01/01/2027') // no shift to the day before
  })

  it('leaves text that is not a date as it is', () => {
    expect(formatTripDate('soon')).toBe('soon')
  })
})

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

describe('formatPlaceTime', () => {
  it('shows the destination clock time, whatever the viewer time zone is', () => {
    // 10:00 in Seattle is 18:00 UTC; the traveller must see 10:00.
    expect(formatPlaceTime('2026-11-13T10:00:00-08:00', 'en')).toBe('10:00 AM')
    expect(formatPlaceTime('2026-11-13T13:52:00-08:00', 'en')).toBe('1:52 PM')
  })

  it('keeps demo times without an offset as written', () => {
    expect(formatPlaceTime('2026-10-12T11:00:00', 'en')).toBe('11:00 AM')
  })
})
