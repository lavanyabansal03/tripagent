import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/svelte'
import TripForm from '../components/TripForm.svelte'

describe('TripForm demo label', () => {
  it('shows the demo note when running on recorded data', () => {
    render(TripForm, { onsubmit: vi.fn(), demoMode: true })
    expect(screen.getByText(/Demo mode: everything runs on recorded data/)).toBeInTheDocument()
  })

  it('does not show any "Demo mode" text in live mode', () => {
    render(TripForm, { onsubmit: vi.fn(), demoMode: false })
    expect(screen.queryByText(/Demo mode/)).not.toBeInTheDocument()
  })
})
