import { expect, test } from '@playwright/test'

/* The console, driven the way a person drives it, against the real stack.
 *
 * Task 3.4 of docs/ROAD_TO_TEN.md. Every defect that reached users on 2026-09-12 lived at a
 * seam between two layers that each had their own passing tests:
 *
 *   the capsule's JavaScript would not parse — the Python suite asserted substrings and
 *     never loaded it, and the console suite never saw it
 *   the headline "Viva Quick" preset pointed at a table pre-flight refuses — nothing had
 *     ever clicked it
 *   /api/ledger/tamper had no test at all, and it is the demo shown live at a viva
 *
 * Nothing is mocked: the FastAPI service is real, the console bundle it serves is the built
 * one, and /api/run does real DP synthesis. A seam is exactly what a unit test cannot see.
 *
 * ONE test drives a full pipeline through the UI, deliberately. A default run is 2,000 rows
 * through profiling, synthesis, a canary audit and five attacks, and takes minutes — so
 * paying that cost four times would produce a suite nobody waits for, which is the same
 * failure as an eight-minute unit suite nobody runs. The remaining tests exercise the same
 * endpoints directly and finish in seconds.
 */

test.describe('console: shell and contract', () => {
  test('serves the built console, not a stale placeholder', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/SynthProof/i)
    // React has actually mounted, rather than the server returning an index shell.
    await expect(page.getByText(/Demo Presets/i).first()).toBeVisible()
  })

  test('reports its authentication posture honestly', async ({ page }) => {
    // /api/health is deliberately unauthenticated and must say so loudly when auth is off.
    // Being open silently would be the worse failure.
    const body = await (await page.request.get('/api/health')).json()
    expect(body.status).toBe('ok')
    expect(body.auth).toBe('disabled')
    expect(body.auth_note).toMatch(/NO AUTHENTICATION/i)
  })

  test('every demo preset is selectable, and the refusal demo announces itself', async ({
    page,
  }) => {
    await page.goto('/')

    // The preset that is EXPECTED to be refused must say so before it is clicked. It used to
    // read "⚡ Viva Quick (3s)" and produced a refusal panel instead of the promised run.
    const refusal = page.getByRole('button', { name: /Refusal demo/i }).first()
    await expect(refusal).toBeVisible()
    await expect(refusal).toHaveAttribute('title', /REFUSED/i)

    for (const name of [/Clinical Outcomes/i, /Credit Risk/i, /HR Attrition/i]) {
      await expect(page.getByRole('button', { name }).first()).toBeVisible()
    }
  })

  test('renders no uncaught errors on load', async ({ page }) => {
    // The capsule shipped a page whose entire inline script failed to parse, and nothing
    // noticed. This is that check, applied to the console.
    const errors: string[] = []
    page.on('pageerror', (e) => errors.push(e.message))
    page.on('console', (m) => {
      if (m.type() === 'error') errors.push(m.text())
    })

    await page.goto('/')
    await expect(page.getByText(/Demo Presets/i).first()).toBeVisible()
    await page.waitForTimeout(1500)

    const real = errors.filter((e) => !/favicon|ResizeObserver|WebGL|THREE/i.test(e))
    expect(real, `uncaught errors on load:\n${real.join('\n')}`).toHaveLength(0)
  })
})

test.describe('the ledger, and the demo shown live', () => {
  test('tampering is DETECTED, without overclaiming what that proves', async ({ request }) => {
    // Seed the chain with a small real release, then attack it.
    const run = await request.post('/api/run', {
      data: {
        dataset: 'toy',
        mechanism: 'independent',
        target_eps: 1.0,
        delta: 1e-5,
        seed: 0,
        num_canaries: 10,
        rows: 200,
      },
      timeout: 120_000,
    })
    expect(run.ok()).toBeTruthy()

    const before = await (await request.get('/api/ledger')).json()
    expect(before.verified).toBe(true)
    expect(before.count).toBeGreaterThan(0)

    const verdict = await (
      await request.post('/api/ledger/tamper', {
        data: { attack_type: 'modify_eps', eps_spent: 99.0 },
      })
    ).json()

    // The demo's failure mode is silence: an undetected attack renders as a chain that is
    // still fine, which argues the opposite of the demo's point.
    expect(verdict.verified).toBe(false)
    expect(verdict.broken_count).toBeGreaterThanOrEqual(1)

    // And it must not overclaim while doing it. ledger/signing.py records that a key holder
    // can rewrite and re-sign, so this is tamper-EVIDENT, not tamper-proof.
    expect(verdict.explanation.toLowerCase()).not.toContain('non-repudiation')

    // Detection has to survive the response, not just appear in it.
    const after = await (await request.get('/api/ledger')).json()
    expect(after.verified).toBe(false)

    // The demo has to be repeatable.
    await request.post('/api/ledger/reset')
    expect((await (await request.get('/api/ledger')).json()).verified).toBe(true)
  })

  test('a broken chain is rendered as broken, never as verified', async ({ page, request }) => {
    await request.post('/api/run', {
      data: {
        dataset: 'toy', mechanism: 'independent', target_eps: 1.0, delta: 1e-5,
        seed: 0, num_canaries: 10, rows: 200,
      },
      timeout: 120_000,
    })
    await request.post('/api/ledger/tamper', { data: { attack_type: 'corrupt_hash' } })

    await page.goto('/')
    await expect(page.getByText(/attack detected|chain broken/i).first()).toBeVisible()
    await expect(page.getByText(/chain integrity: verified/i)).toHaveCount(0)

    await request.post('/api/ledger/reset')
  })
})

test.describe('the capsule, end to end', () => {
  test('exports a parseable capsule with no verification bypass', async ({ request }) => {
    const sheet = {
      dataset_name: 'E2E',
      mechanism: 'independent',
      num_rows: 3,
      total_proved_eps: 1.0,
      total_audited_eps: 0.0,
      audit_ceiling: 2.97,
    }
    const exported = await request.post('/api/capsule/export', {
      data: { sheet, records: [{ a: 1 }, { a: 2 }, { a: 3 }] },
    })
    expect(exported.ok()).toBeTruthy()
    const html = await exported.text()

    // The shared verifier is inlined from synthproof/capsule/verifier.js. If this string is
    // gone, either the generator regressed or someone re-inlined a private copy.
    expect(html).toContain('spDecideVerdict')

    // The retired length-check bypass must stay retired: these strings were the green badge
    // a forged capsule used to get.
    expect(html).not.toContain('Proof Format Verified')
    expect(html).not.toContain('Verified 64-byte')
  })

  test('an exported capsule actually runs and verifies IN A BROWSER', async ({ page, request }) => {
    // The defect that shipped was a page whose script did not parse, so the badge never left
    // "VERIFYING PROOF...". Asserting on the HTML cannot see that; loading it can.
    const exported = await request.post('/api/capsule/export', {
      data: {
        sheet: {
          dataset_name: 'E2E', mechanism: 'independent', num_rows: 3,
          total_proved_eps: 1.0, total_audited_eps: 0.0, audit_ceiling: 2.97,
        },
        records: [{ a: 1 }, { a: 2 }, { a: 3 }],
      },
    })
    const html = await exported.text()

    const errors: string[] = []
    page.on('pageerror', (e) => errors.push(e.message))
    await page.setContent(html)

    // Whatever the verdict, the badge must RESOLVE. "VERIFYING PROOF..." forever is the bug.
    await expect(page.locator('.badge')).not.toHaveText(/VERIFYING/i, { timeout: 15_000 })
    expect(errors, `capsule script errors:\n${errors.join('\n')}`).toHaveLength(0)

    // This sheet is unsigned, so the honest verdict is a refusal — and critically NOT the
    // green "Verified" that the old structural fallback produced for exactly this input.
    const badge = (await page.locator('.badge').innerText()).toLowerCase()
    expect(badge).not.toContain('cryptographically verified')
  })

  test('malformed input fails closed rather than crashing', async ({ request }) => {
    const report = await (
      await request.post('/api/capsule/verify', { data: { html_content: '<p>nope</p>' } })
    ).json()
    expect(report.verified).toBe(false)
    expect(report.lod_status).toBe('ERROR')
  })
})

test.describe('the full pipeline, through the UI', () => {
  // The only test that pays for a complete run. Everything above proves a contract; this one
  // proves the seams hold when a person clicks the button.
  test.setTimeout(600_000)

  test('runs a release and reports the audited epsilon BESIDE its ceiling', async ({ page }) => {
    await page.goto('/')

    // The smallest preset that pre-flight accepts, so this costs minutes rather than more.
    await page.getByRole('button', { name: /HR Attrition/i }).first().click()
    await page.getByRole('button', { name: /Synthesise & Audit Release/i }).first().click()

    const abort = page.getByRole('button', { name: /Abort Verification Pipeline/i })

    // Wait for the run to START before waiting for it to finish. Asserting only that the
    // abort control is absent passes INSTANTLY, before the pipeline has begun — which is
    // exactly what this test did on its first run: 2.5 seconds, green, and proving nothing.
    // A vacuous end-to-end test is worse than none, because it reports coverage it does not
    // have.
    await expect(abort).toBeVisible({ timeout: 30_000 })
    await expect(abort).toHaveCount(0, { timeout: 540_000 })

    const body = await page.locator('body').innerText()

    // The assertion this whole project exists for. An audited epsilon without the ceiling
    // beside it is the uninterpretable number: a 0 that could mean "no leakage" or "the
    // instrument cannot see this far", and only the ceiling tells them apart.
    expect(body).toMatch(/audited/i)
    expect(body).toMatch(/ceiling/i)
    expect(body).toMatch(/proved/i)

    // And on VALUES, not just the labels. "Ε PROVED" and "Ε AUDITED" are headings the panel
    // renders whether or not a run ever happened, so matching the words alone would pass on
    // an empty console — the same vacuity this test had on its first version.
    //
    // The ceiling's own sentence is the strongest thing to assert on, because it is the
    // claim: at this canary count the instrument cannot report above ε ≈ N, even against a
    // release that is 100% verbatim training data.
    expect(body, 'the ceiling stated as a value').toMatch(/cannot report above[\s\S]{0,40}\d+\.\d+/i)
    expect(body, 'an audited epsilon value').toMatch(/ε[_ ]?audited[\s\S]{0,40}\d+\.\d+/i)

    // The ceiling MARKER on the bounds gauge, not just the sentence beneath it. It was
    // drawn only when `ceiling < scale`, and the scale did not account for the ceiling --
    // so at the default target of eps=1 it silently vanished, hiding the ceiling in exactly
    // the case where it matters: sitting far above the proved bound.
    await expect(page.getByText(/audit ceiling/i).first()).toBeVisible()
  })
})
