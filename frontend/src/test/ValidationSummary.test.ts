import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/svelte'
import ValidationSummary from '../components/ValidationSummary.svelte'
import type { ValidationResult } from '../types'

function result(rule: string, severity: ValidationResult['severity'], passed = false): ValidationResult {
  return { id: rule, trip_id: 't', version: 1, rule, passed, severity, message: '', activity_ids: [] }
}

describe('ValidationSummary pass message', () => {
  it('says everything fits when every check ran and passed', () => {
    render(ValidationSummary, { results: [result('budget', 'soft', true)] })
    expect(screen.getByText('Everything fits: hours, travel times and budget.')).toBeInTheDocument()
  })

  it('does not claim hours or budget fit when some data is unknown', () => {
    render(ValidationSummary, { results: [result('budget', 'data-gap'), result('opening_hours', 'data-gap')] })
    expect(
      screen.getByText('Everything we could check fits. Some hours or prices are not listed.'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Everything fits: hours, travel times and budget.')).not.toBeInTheDocument()
  })
})
