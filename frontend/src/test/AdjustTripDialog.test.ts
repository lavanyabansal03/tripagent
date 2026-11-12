import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/svelte'
import AdjustTripDialog from '../components/AdjustTripDialog.svelte'

function open(question: string | null) {
  render(AdjustTripDialog, {
    open: true,
    onsubmit: vi.fn(),
    onquick: vi.fn(),
    onclose: vi.fn(),
    question,
  })
}

describe('AdjustTripDialog question from A5', () => {
  it("shows A5's question when a change was unclear", () => {
    open('Which place is closed: Frye Art Museum or Seattle Art Museum?')
    expect(
      screen.getByText(
        'We need one detail: Which place is closed: Frye Art Museum or Seattle Art Museum?',
      ),
    ).toBeInTheDocument()
  })

  it('shows the generic help text for the copy key', () => {
    open('adjust.needsClarification')
    expect(screen.getByText(/We didn't catch what changed/)).toBeInTheDocument()
  })

  it('shows no question normally', () => {
    open(null)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })
})
