import { test, expect } from '@playwright/test'

/**
 * Sprint 3 centerpiece: report a change, see only what broke repaired, read the
 * explained diff, then undo it (FR-51, US-16, US-29).
 */
async function planTrip(page: import('@playwright/test').Page) {
  await page.goto('/')
  await page.getByLabel('Destination').fill('Seattle')
  await page.getByRole('button', { name: 'Build my plan' }).click()
  await expect(page.getByRole('heading', { name: "Here's what we understood" })).toBeVisible()
  await page.getByRole('button', { name: 'Build my plan' }).click()
  await expect(page.getByTestId('version-chip')).toHaveText('v1', { timeout: 30_000 })
}

test('adjusting the trip shows an explained, undoable change summary', async ({ page }) => {
  await planTrip(page)

  await page.getByRole('button', { name: 'Adjust trip' }).click()
  await expect(page.getByRole('dialog', { name: 'What changed?' })).toBeVisible()
  await page
    .getByPlaceholder(/I'm running 90 minutes late/)
    .fill('My budget is now $300')
  await page.getByRole('button', { name: 'Adjust my trip' }).click()

  // A new version with a change summary.
  await expect(page.getByTestId('version-chip')).toHaveText('v2', { timeout: 30_000 })
  await expect(page.getByText('Your trip is updated')).toBeVisible()
  await expect(page.getByText(/Because your budget is now \$300/)).toBeVisible()

  // Undo restores v1.
  await page.getByRole('button', { name: 'Undo changes' }).click()
  await expect(page.getByTestId('version-chip')).toHaveText('v1', { timeout: 30_000 })
})

test('quick action lowers the budget and reports the trigger', async ({ page }) => {
  await planTrip(page)
  await page.getByRole('button', { name: 'Adjust trip' }).click()
  await page.getByRole('button', { name: 'Lower budget' }).click()
  await expect(page.getByTestId('version-chip')).toHaveText('v2', { timeout: 30_000 })
  await expect(page.getByText(/Because your budget is now \$300/)).toBeVisible()
})
