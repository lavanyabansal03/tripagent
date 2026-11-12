import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/svelte'
import TripForm from '../components/TripForm.svelte'
import type { TripFormInput } from '../api/client'

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

describe('TripForm after "Edit trip details"', () => {
  it('comes back filled in with the last answers', () => {
    const initial = {
      destination: 'Kyoto',
      start_date: '2026-12-01',
      end_date: '2026-12-03',
      budget: 250,
      budget_strictness: 'flexible' as const,
      mode: 'walking' as const,
      pace: 'relaxed' as const,
      max_travel_min: 20,
      interests: ['temples'],
      avoid: ['crowds'],
      tourist_local_ratio: 70,
      free_text: 'Quiet temples and tea.',
      touched: ['destination', 'budget'],
    }
    const { container } = render(TripForm, { onsubmit: vi.fn(), demoMode: false, initial })

    expect((screen.getByLabelText('Destination') as HTMLInputElement).value).toBe('Kyoto')
    expect((container.querySelector('#start-date') as HTMLInputElement).value).toBe('2026-12-01')
    expect((container.querySelector('#budget') as HTMLInputElement).value).toBe('250')
    expect(
      (screen.getByLabelText('Tell us more about your trip') as HTMLTextAreaElement).value,
    ).toBe('Quiet temples and tea.')
  })
})

/** Submit the form and return what it sent. */
async function submitted(onsubmit: ReturnType<typeof vi.fn>): Promise<TripFormInput> {
  await fireEvent.submit(document.querySelector('form')!)
  expect(onsubmit).toHaveBeenCalledTimes(1)
  return onsubmit.mock.calls[0][0] as TripFormInput
}

describe('TripForm touched fields', () => {
  it('marks interests and avoid as chosen when the traveller picks chips', async () => {
    // Bug: picked chips were labelled "We assumed this" because they were never marked.
    const onsubmit = vi.fn()
    render(TripForm, { onsubmit, demoMode: false })
    await fireEvent.click(screen.getAllByLabelText('nature')[0])
    await fireEvent.click(screen.getByLabelText('nightlife'))
    const input = await submitted(onsubmit)
    expect(input.interests).toContain('nature')
    expect(input.avoid).toContain('nightlife')
    expect(input.touched).toEqual(expect.arrayContaining(['interests', 'avoid']))
  })

  it('marks interests and avoid as chosen when the traveller adds their own', async () => {
    const onsubmit = vi.fn()
    render(TripForm, { onsubmit, demoMode: false })
    const [interestBox, avoidBox] = screen.getAllByPlaceholderText('Add your own')
    const [addInterest, addAvoid] = screen.getAllByRole('button', { name: 'Add' })
    await fireEvent.input(interestBox, { target: { value: 'Jazz' } })
    await fireEvent.click(addInterest)
    await fireEvent.input(avoidBox, { target: { value: 'crowds' } })
    await fireEvent.click(addAvoid)
    const input = await submitted(onsubmit)
    expect(input.interests).toContain('jazz')
    expect(input.avoid).toContain('crowds')
    expect(input.touched).toEqual(expect.arrayContaining(['interests', 'avoid']))
  })

  it('leaves untouched interests unmarked so they stay "We assumed this"', async () => {
    const onsubmit = vi.fn()
    render(TripForm, { onsubmit, demoMode: false })
    const input = await submitted(onsubmit)
    expect(input.touched).not.toContain('interests')
    expect(input.touched).not.toContain('avoid')
  })
})

describe('TripForm budget', () => {
  it('sends the default budget when the field is not touched', async () => {
    const onsubmit = vi.fn()
    render(TripForm, { onsubmit, demoMode: false })
    expect((await submitted(onsubmit)).budget).toBe(500)
  })

  it('still submits after the traveller types a new budget', async () => {
    // Bug: typing in the number box made the value a number, and budget.trim() crashed.
    const onsubmit = vi.fn()
    render(TripForm, { onsubmit, demoMode: false })
    await fireEvent.input(screen.getByLabelText('Budget'), { target: { value: '300' } })
    const input = await submitted(onsubmit)
    expect(input.budget).toBe(300)
    expect(input.touched).toContain('budget')
  })

  it('sends no budget when the traveller clears the field', async () => {
    const onsubmit = vi.fn()
    render(TripForm, { onsubmit, demoMode: false })
    await fireEvent.input(screen.getByLabelText('Budget'), { target: { value: '' } })
    expect((await submitted(onsubmit)).budget).toBeNull()
  })
})
