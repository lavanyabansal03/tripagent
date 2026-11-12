import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
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

describe('TripForm budget', () => {
  async function submitWithBudget(value: string) {
    const onsubmit = vi.fn()
    const { container } = render(TripForm, { onsubmit, demoMode: false })
    const budget = container.querySelector('#budget') as HTMLInputElement
    await fireEvent.input(budget, { target: { value } })
    await fireEvent.submit(container.querySelector('form') as HTMLFormElement)
    return onsubmit
  }

  it('sends a typed budget as a number (typing used to crash the button)', async () => {
    const onsubmit = await submitWithBudget('300')

    expect(onsubmit).toHaveBeenCalledTimes(1)
    expect(onsubmit.mock.calls[0][0].budget).toBe(300)
    expect(onsubmit.mock.calls[0][0].touched).toContain('budget')
  })

  it('sends no budget when the box is emptied', async () => {
    const onsubmit = await submitWithBudget('')

    expect(onsubmit.mock.calls[0][0].budget).toBeNull()
  })
})
