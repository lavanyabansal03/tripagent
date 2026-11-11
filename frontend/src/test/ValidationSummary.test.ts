import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/svelte'
import ValidationSummary from '../components/ValidationSummary.svelte'
import type { ValidationResult } from '../types'

function result(overrides: Partial<ValidationResult>): ValidationResult {
  return {
    id: 'check',
    trip_id: 'trip_1',
    version: 1,
    rule: 'overlap',
    passed: true,
    severity: 'soft',
    message: '',
    activity_ids: [],
    ...overrides,
  } as ValidationResult
}

const budgetUnknown = result({
  id: 'budget-check',
  rule: 'budget',
  passed: false,
  severity: 'data-gap',
  message: 'Budget check passed. Regular cost: $0; splurges: $0; total: $0. 9 activities have unknown costs.',
})

describe('ValidationSummary wording', () => {
  it('says "Everything fits" only when nothing is unknown', () => {
    render(ValidationSummary, { results: [result({ passed: true })] })
    expect(screen.getByText('Everything fits: hours, travel times and budget.')).toBeInTheDocument()
  })

  it('does not claim everything fits when some details are unknown', () => {
    render(ValidationSummary, { results: [budgetUnknown] })
    expect(screen.queryByText(/Everything fits/)).not.toBeInTheDocument()
    expect(screen.getByText('No problems found, but some details are unknown. See below.')).toBeInTheDocument()
  })

  it('never shows $0 for unknown costs', () => {
    render(ValidationSummary, { results: [budgetUnknown] })
    expect(screen.queryByText(/\$0/)).not.toBeInTheDocument()
    expect(
      screen.getByText("Some stops have no listed price, so we can't fully check your budget."),
    ).toBeInTheDocument()
  })

  it('shows the variety warning once, in the design-guide words', () => {
    const variety = result({
      id: 'variety-check',
      rule: 'variety',
      passed: false,
      severity: 'soft',
      message: 'Days 1, 2 and 3 have too many activities of the same kind in a row.',
    })
    render(ValidationSummary, { results: [variety] })
    expect(screen.getAllByText('Some stops in a row are the same kind. Want more variety?')).toHaveLength(1)
  })
})
