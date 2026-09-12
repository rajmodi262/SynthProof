import { defineConfig, devices } from '@playwright/test'

/* End-to-end configuration.
 *
 * This drives the REAL stack: the FastAPI service, the built console bundle it serves, and
 * the actual synthesis pipeline behind /api/run. Nothing is mocked. That is the whole point
 * — every other suite in this repository tests one layer in isolation, and the defects that
 * reached users on 2026-09-12 were all at the seams between layers:
 *
 *   the capsule's JavaScript failed to parse, and no Python test loaded it
 *   the "Viva Quick" preset pointed at a table pre-flight refuses, and no test clicked it
 *   /api/ledger/tamper was untested, and it is the demo shown live
 *
 * A seam is exactly what a unit test cannot see.
 *
 * The web server is the API rather than Vite's dev server, because that is what
 * START_PROTOTYPE.bat launches and therefore what an examiner will actually run.
 */
export default defineConfig({
  testDir: './e2e',
  // The pipeline does real DP synthesis; a 30s default is not enough on a cold JAX import.
  timeout: 180_000,
  expect: { timeout: 20_000 },
  fullyParallel: false, // the ledger is process-wide state on the server
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['list']] : [['list']],

  use: {
    baseURL: 'http://127.0.0.1:8765',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },

  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],

  webServer: {
    // An in-memory ledger, so a tamper test cannot leave a broken chain on disk for the
    // next run. SYNTHPROOF_API_KEY stays unset: the console talks to an unauthenticated
    // local service, which is the configuration being tested.
    // SYNTHPROOF_PYTHON lets a developer point this at the project venv. Bare `python` on a
    // Windows PATH resolved to a system interpreter that had synthproof installed but NOT
    // private-PGM, so the console under test reported AIM as unavailable while the developer's
    // own environment had it -- an e2e suite testing a different stack than the one being
    // worked on. CI has a single interpreter, so the default is correct there.
    command: `${process.env.SYNTHPROOF_PYTHON ?? 'python'} -m uvicorn synthproof.api.main:app --host 127.0.0.1 --port 8765 --log-level warning`,
    cwd: '..',
    url: 'http://127.0.0.1:8765/api/health',
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    env: { SYNTHPROOF_LEDGER_DB: ':memory:', SYNTHPROOF_DEMO: '1' },
  },
})
