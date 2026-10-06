/**
 * Tiny i18n layer. All UI strings live in copy/en.json (guide S5.4); components
 * must not inline text. Supports {name} interpolation and the small subset of
 * ICU plural we use: "{count, plural, one {..} other {..}}".
 */
import en from './en.json'

export type Copy = typeof en
export type Locale = string

const catalogs: Record<string, unknown> = { en }
let activeLocale: Locale = 'en'

export function setLocale(locale: Locale): void {
  activeLocale = locale
}

export function getLocale(): Locale {
  return activeLocale
}

function lookup(catalog: unknown, key: string): string | undefined {
  const parts = key.split('.')
  let node: unknown = catalog
  for (const part of parts) {
    if (node && typeof node === 'object' && part in (node as Record<string, unknown>)) {
      node = (node as Record<string, unknown>)[part]
    } else {
      return undefined
    }
  }
  return typeof node === 'string' ? node : undefined
}

/** Resolve an ICU plural fragment: "{count, plural, one {..} other {..}}". */
function resolvePlural(template: string, vars: Record<string, string | number>): string {
  const pluralRe = /\{(\w+),\s*plural,\s*((?:(?:=\d+|one|other|few|many|zero)\s*\{[^{}]*\}\s*)+)\}/g
  return template.replace(pluralRe, (_match, varName: string, body: string) => {
    const value = Number(vars[varName] ?? 0)
    const branchRe = /(=\d+|one|other|few|many|zero)\s*\{([^{}]*)\}/g
    const branches: Record<string, string> = {}
    let m: RegExpExecArray | null
    while ((m = branchRe.exec(body)) !== null) branches[m[1]] = m[2]
    const exact = branches[`=${value}`]
    if (exact !== undefined) return exact.replace('#', String(value))
    const category = new Intl.PluralRules(activeLocale).select(value)
    const chosen = branches[category] ?? branches.other ?? ''
    return chosen.replace('#', String(value))
  })
}

/** Exposed for tests. */
export function resolvePluralForTest(template: string, count: number): string {
  return resolvePlural(template, { n: count })
}

/** Translate a dotted key, interpolating {placeholders}. */
export function t(key: string, vars: Record<string, string | number> = {}): string {
  const catalog = catalogs[activeLocale] ?? catalogs.en
  const template = lookup(catalog, key) ?? lookup(catalogs.en, key) ?? key
  const withPlural = resolvePlural(template, vars)
  return withPlural.replace(/\{(\w+)\}/g, (_m, name: string) =>
    name in vars ? String(vars[name]) : `{${name}}`,
  )
}

/* --- Intl formatting helpers (never concatenate currency symbols) --- */

export function formatMoney(
  amount: number,
  locale: Locale = activeLocale,
  currency = 'USD',
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: Number.isInteger(amount) ? 0 : 2,
  }).format(amount)
}

export function formatCost(
  estCost: number | null,
  low: number | null | undefined,
  high: number | null | undefined,
  basis: string,
  locale: Locale = activeLocale,
): string {
  if (basis === 'free') return t('validation.free')
  if (basis === 'unknown' || (estCost === null && (low == null || high == null))) {
    return t('validation.unknownCost')
  }
  if (basis === 'price_level' && low != null && high != null) {
    return t('validation.estimatedCost', {
      low: formatMoney(low, locale),
      high: formatMoney(high, locale),
    })
  }
  return t('validation.knownCost', { amount: formatMoney(estCost ?? low ?? 0, locale) })
}

export function formatTime(iso: string, locale: Locale = activeLocale): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return new Intl.DateTimeFormat(locale, { hour: 'numeric', minute: '2-digit' }).format(d)
}

export function formatDate(iso: string, locale: Locale = activeLocale): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return new Intl.DateTimeFormat(locale, { month: 'short', day: 'numeric' }).format(d)
}

export function formatDateRange(
  startIso: string,
  endIso: string,
  locale: Locale = activeLocale,
): string {
  const start = new Date(startIso)
  const end = new Date(endIso)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return `${startIso}–${endIso}`
  const sameMonth = start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear()
  const fmt = new Intl.DateTimeFormat(locale, { month: 'short', day: 'numeric' })
  if (sameMonth) return `${fmt.format(start)}–${new Intl.DateTimeFormat(locale, { day: 'numeric' }).format(end)}`
  return `${fmt.format(start)}–${fmt.format(end)}`
}

/** "today, 9:40 AM", "yesterday", "3 days ago" — used by freshness labels. */
export function formatRelativeWhen(iso: string, now = new Date(), locale: Locale = activeLocale): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const days = Math.round((startOf(now) - startOf(d)) / 86_400_000)
  if (days <= 0) return t('validation.freshToday', { time: formatTime(iso, locale) })
  if (days === 1) return 'yesterday'
  return `${days} days ago`
}

export function isStale(iso: string, maxAgeHours: number, now = new Date()): boolean {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return true
  return now.getTime() - d.getTime() > maxAgeHours * 3_600_000
}
