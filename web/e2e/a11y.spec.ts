import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

/* Accessibility and the 1024 px layout (W8).
 *
 * axe-core checks the console against WCAG 2.1 A/AA. The gate is zero serious or critical
 * violations, on the page a visitor first sees AND with the run parameters open, because a
 * control that only appears after a click is still a control someone has to operate.
 */
const WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']

async function seriousViolations(page: import('@playwright/test').Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(WCAG).analyze()
  return violations
    .filter((v) => v.impact === 'serious' || v.impact === 'critical')
    .map((v) => `${v.id} (${v.impact}): ${v.nodes.length} node(s), e.g. ${v.nodes[0]?.target.join(' ')}`)
}

test.describe('accessibility', () => {
  test('the console has no serious or critical WCAG violations', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('button', { name: /Run release & compute proof/i }).first()).toBeVisible()
    expect(await seriousViolations(page)).toEqual([])
  })

  test('nor with the run parameters open', async ({ page }) => {
    await page.goto('/')
    await page.getByText(/Run parameters/i).first().click()
    expect(await seriousViolations(page)).toEqual([])
  })

  test('nor in dark mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark' })
    await page.goto('/')
    await expect(page.getByRole('button', { name: /Run release & compute proof/i }).first()).toBeVisible()
    expect(await seriousViolations(page)).toEqual([])
  })
})

test.describe('layout at 1024 px', () => {
  test.use({ viewport: { width: 1024, height: 768 } })

  test('nothing overflows the viewport horizontally', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('button', { name: /Run release & compute proof/i }).first()).toBeVisible()
    const { scroll, client } = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      client: document.documentElement.clientWidth,
    }))
    expect(scroll).toBeLessThanOrEqual(client)
  })

  test('the run control is reachable without scrolling sideways', async ({ page }) => {
    await page.goto('/')
    const box = await page.getByRole('button', { name: /Run release & compute proof/i }).first().boundingBox()
    expect(box).not.toBeNull()
    expect(box!.x).toBeGreaterThanOrEqual(0)
    expect(box!.x + box!.width).toBeLessThanOrEqual(1024)
  })
})
