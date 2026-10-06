/**
 * TypeScript mirror of the design tokens for map layers.
 * The map cannot read CSS custom properties for paint expressions, so the
 * Frontend & Maps Eng. keeps this object in sync with tokens.css (guide S2).
 */
export const tokens = {
  color: {
    bg: '#FFFFFF',
    surface: '#F6F8FA',
    text: '#1F2A37',
    textMuted: '#5B6675',
    border: '#D0D7DE',
    brand: '#0F6E6E',
    success: '#1A7F37',
    warning: '#9A6700',
    danger: '#CF222E',
    info: '#0969DA',
  },
  change: {
    added: '#1A7F37',
    replaced: '#0969DA',
    moved: '#9A6700',
    removed: '#CF222E',
    preserved: '#5B6675',
  },
  category: {
    food: '#E69F00',
    cafe: '#A0522D',
    nature: '#009E73',
    culture: '#56B4E9',
    shopping: '#CC79A7',
    nightlife: '#6A4C93',
    event: '#D55E00',
    landmark: '#5B6675',
  },
  radius: { sm: 4, md: 8, lg: 16 },
  motion: { fast: 120, base: 200, slow: 320 },
} as const

export type CategoryToken = keyof typeof tokens.category
export type ChangeToken = keyof typeof tokens.change
