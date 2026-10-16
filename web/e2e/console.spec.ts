import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = fileURLToPath(new URL('.', import.meta.url))

/* The console, driven the way a person drives it, against the real stack.
 *
 * Task 3.4 of archive/docs/ROAD_TO_TEN.md. Every defect that reached users on 2026-09-12 lived at a
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

  test('is served under a content security policy that forbids inline script', async ({
    request,
  }) => {
    // The console must keep working with it: the next test fails on any console error, and a
    // blocked script or stylesheet is reported as one (docs/threat_model.md, T4).
    const csp = (await request.get('/')).headers()['content-security-policy'] ?? ''
    expect(csp).toContain("script-src 'self'")
    expect(csp).toContain("frame-ancestors 'none'")
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

  test('verifier modal reports CLAIM EXCEEDS AUDIT RANGE when uploaded capsule exceeds ceiling', async ({ page }) => {
    await page.goto('/')
    // Open the Verifier modal
    await page.getByRole('button', { name: /Zero-Trust Verifier/i }).click()
    await expect(page.getByText('Zero-Trust Certificate Verifier')).toBeVisible()

    // Upload the demo capsule file
    const capsulePath = resolve(__dirname, '../../demo_capsules/uci_adult_eps8_claim_exceeds_audit_range_capsule.html')
    const fileChooserPromise = page.waitForEvent('filechooser')
    await page.getByText(/Upload Sheet \/ Capsule/i).click()
    const fileChooser = await fileChooserPromise
    await fileChooser.setFiles(capsulePath)

    // Wait for the badge to be visible before any negative assertion (trap 8)
    const badge = page.getByText('CLAIM EXCEEDS AUDIT RANGE')
    await expect(badge).toBeVisible({ timeout: 15_000 })

    // Negative assertions: old strings must not appear anywhere
    await expect(page.getByText(/valid detection zone/i)).toHaveCount(0)
    await expect(page.getByText(/MIQE 2\.0 Operating Range/i)).toHaveCount(0)
  })
})

// @slow -- a real DP synthesis driven through a browser. It finishes in about four seconds
// on a warm developer machine and does NOT finish inside nine minutes on a two-core GitHub
// runner with a cold JAX cache; the run starts and is still going when the timeout expires.
//
// So it is excluded from the per-push pipeline (`--grep-invert @slow`) and runs on the weekly
// schedule instead. This is the same call as the `slow` pytest marker, for the same reason:
// a check that makes every push wait twenty minutes is a check people learn to route around,
// and the nine specs that DO gate each push already cover the shell, the ledger, the tamper
// demo and the capsule round trip.
//
// It earns its place regardless -- it is the test that found the audit-ceiling marker being
// hidden whenever the ceiling exceeded the axis scale. Run it with `npm run test:e2e:slow`.
test.describe('the full pipeline, through the UI @slow', () => {
  // The only test that pays for a complete run. Everything above proves a contract; this one
  // proves the seams hold when a person clicks the button.
  test.setTimeout(600_000)

  test('runs a release and reports the audited epsilon BESIDE its ceiling', async ({ page }) => {
    await page.goto('/')

    // Drive the run down to the smallest thing the pipeline will accept, THROUGH THE UI.
    //
    // The point of this test is the seam -- click, SSE, readouts, ceiling -- not the size of
    // the synthesis. At the console defaults (2,000 rows, 60 canary pairs) a run takes a few
    // seconds on a warm developer machine and MORE THAN NINE MINUTES on a two-core CI runner
    // with a cold JAX cache, which failed the first CI run of this suite outright. Setting
    // the controls exercises them as well, which the previous version did not.
    // The controls live inside a collapsed <details>, so the disclosure has to be opened
    // first -- Playwright finds the input either way and then waits out the entire test
    // timeout on "element is not visible".
    //
    // Located structurally rather than by accessible name, too: the label's text sits in a
    // sibling <span>, so the number input has no accessible name to match against.
    // Use a preset rather than the default. The built-in toy table is the SLOW path here --
    // its columns are drawn independently, so the attack suite finds nothing and works
    // hardest doing it; a run against it was still going after nine minutes, while the same
    // pipeline over the 600-row HR CSV finishes in seconds.
    await page.getByRole('button', { name: /HR Attrition/i }).first().click()

    // Then cut the canary count, which is the other multiplier. The controls live inside a
    // collapsed <details>, so the disclosure has to be opened first: Playwright finds the
    // input either way and then waits out the whole test timeout on "element is not
    // visible". They are located structurally because the label's text sits in a sibling
    // <span>, leaving the number input with no accessible name to match against.
    await page.getByText(/Run parameters/i).first().click()
    await page.locator('label:has-text("canary pairs") input').fill('4')

    await page.getByRole('button', { name: /Run release & compute proof/i }).first().click()

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

    // The measured frontier holds exactly the one release that ran, with its ledger entry --
    // never a modelled curve (W8).
    await expect(page.getByTestId('frontier-point')).toHaveCount(1)
    await expect(page.getByRole('table', { name: /Measured frontier points/i })).toBeVisible()

    // Accessibility of the populated console, not just the empty first screen (W8). The
    // panels a release reveals are the ones an examiner actually reads.
    const { violations } = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .analyze()
    const serious = violations
      .filter((v) => v.impact === 'serious' || v.impact === 'critical')
      .map((v) => `${v.id}: ${v.nodes.length} node(s), e.g. ${v.nodes[0]?.target.join(' ')}`)
    expect(serious).toEqual([])
  })

  test('an epsilon sweep adds one measured point per real release, each with its ledger entry', async ({
    page,
    request,
  }) => {
    await page.goto('/')
    await page.getByRole('button', { name: /HR Attrition/i }).first().click()
    await page.getByText(/Run parameters/i).first().click()
    await page.locator('label:has-text("canary pairs") input').fill('4')
    const before = (await (await request.get('/api/ledger')).json()).count as number

    await page.getByRole('button', { name: /Run release & compute proof/i }).first().click()
    const sweep = page.getByRole('button', { name: /Sweep ε/ })
    await expect(sweep).toBeEnabled({ timeout: 300_000 })
    await sweep.click()

    // One release for the first run, then one per budget in the sweep grid (five).
    await expect(page.getByTestId('frontier-point')).toHaveCount(6, { timeout: 540_000 })
    await expect(sweep).toBeEnabled({ timeout: 60_000 })
    const rows = page.getByRole('table', { name: /Measured frontier points/i }).locator('tbody tr')
    await expect(rows).toHaveCount(6)

    // Every point was charged: the ledger grew by exactly the releases plotted.
    const after = (await (await request.get('/api/ledger')).json()).count as number
    expect(after - before).toBe(6)
  })

  test('every KPI value equals the API field it names, read from the real run stream', async ({
    page,
    request,
  }) => {
    // Capture the run stream itself. The route fetches the real response, keeps a copy, and
    // hands the same bytes to the page -- so the console renders exactly what was captured.
    let stream = ''
    await page.route('**/api/run', async (route) => {
      const response = await route.fetch()
      stream = await response.text()
      await route.fulfill({ response, body: stream })
    })

    await page.goto('/')
    await page.getByRole('button', { name: /HR Attrition/i }).first().click()
    await page.getByText(/Run parameters/i).first().click()
    await page.locator('label:has-text("canary pairs") input').fill('4')
    await page.getByRole('button', { name: /Run release & compute proof/i }).first().click()
    await expect(page.getByTestId('frontier-point')).toHaveCount(1, { timeout: 300_000 })

    const doneData = stream
      .split('\n\n')
      .find((frame) => frame.includes('event: done'))!
      .split('\n')
      .filter((l) => l.startsWith('data: '))
      .map((l) => l.slice(6))
      .join('\n')
    const sources = {
      run: JSON.parse(doneData),
      ledger: await (await request.get('/api/ledger')).json(),
    } as Record<string, unknown>
    const resolve = (path: string) =>
      path.split('.').reduce<unknown>((o, k) => (o as Record<string, unknown>)?.[k], sources)

    const cards = page.locator('[data-source]')
    const n = await cards.count()
    expect(n, 'every KPI card declares its source').toBeGreaterThanOrEqual(7)
    for (let i = 0; i < n; i++) {
      const card = cards.nth(i)
      const path = (await card.getAttribute('data-source'))!
      const shown = (await card.getByTestId('kpi-value').innerText()).trim()
      const actual = resolve(path)
      if (typeof actual === 'boolean') {
        expect(shown, path).toBe(actual ? 'INTACT' : 'BROKEN')
        continue
      }
      expect(typeof actual, `${path} resolves to a number in the API`).toBe('number')
      // Equal to the precision displayed: 0.123 means |actual - 0.123| <= 0.0005.
      const decimals = (shown.split('.')[1] ?? '').length
      expect(Math.abs(Number(shown.replace(/,/g, '')) - (actual as number)), `${path} shown as ${shown}`)
        .toBeLessThanOrEqual(0.5 * 10 ** -decimals + 1e-12)
    }

    // The capsule of THIS release must verify in a browser. Until 2026-10-16 every capsule
    // exported from a console release embedded a signature over empty bytes, so the page could
    // only ever report failure; no test exported a real release's sheet, so nothing noticed.
    const run = sources.run as { sheet: Record<string, unknown>; sample_records: unknown[] }
    const exported = await request.post('/api/capsule/export', {
      data: { sheet: run.sheet, records: run.sample_records.slice(0, 20) },
    })
    // Served from the test server's origin: WebCrypto exists only in a secure context, and a
    // setContent page has none, so it could only ever say "Cannot Verify In This Browser".
    const html = await exported.text()
    await page.route('**/__capsule_under_test', (route) =>
      route.fulfill({ contentType: 'text/html', body: html }),
    )
    await page.goto('/__capsule_under_test')
    await expect(page.locator('.badge')).toHaveText(/Cryptographically Verified/i, {
      timeout: 15_000,
    })
  })
})
