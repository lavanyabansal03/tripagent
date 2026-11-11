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
