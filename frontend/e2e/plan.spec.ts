import { test, expect } from '@playwright/test'

/**
 * Sprint 1 demo: enter the Maya persona description, see it understood, then
 * plan and land on the itinerary + map.
 */
test('describe a trip in words and get a map-verified itinerary', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Plan a trip' })).toBeVisible()

  await page.getByLabel('Tell us more about your trip').fill(
    'First time in Seattle. I love coffee, bookstores and photography, want places locals enjoy, and I would rather not travel more than 30 minutes between stops.',
  )
  await page.getByLabel('Destination').fill('Seattle')
  await page.getByRole('button', { name: 'Build my plan' }).click()

  // "Here's what we understood" with provenance labels (US-17).
  await expect(page.getByRole('heading', { name: "Here's what we understood" })).toBeVisible()
  await expect(page.getByText('From your note').first()).toBeVisible()
  await page.getByRole('button', { name: 'Build my plan' }).click()

  // Planning progress, then the itinerary.
  await expect(page.getByRole('heading', { name: /Seattle, / })).toBeVisible({ timeout: 30_000 })
  await expect(page.getByTestId('version-chip')).toHaveText('v1')
  await expect(page.locator('article').first()).toBeVisible()
})

test('empty input is rejected by native validation', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Destination').fill('')
  await page.getByRole('button', { name: 'Build my plan' }).click()
  // The form is still on screen because destination is required.
  await expect(page.getByRole('heading', { name: 'Plan a trip' })).toBeVisible()
})
