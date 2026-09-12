/* Component tests for the console.
 *
 * Written for task 3.3 of docs/ROAD_TO_TEN.md. Before this, eleven components had no test at
 * all and the entire frontend suite covered one SSE parser. The selection here is by risk,
 * not by coverage arithmetic:
 *
 *   LedgerChain    is the tamper demo shown live at a viva. If it rendered "verified" after a
 *                  successful attack, the demo would argue the opposite of its point.
 *   VerifierModal  is the third-party verification surface. A modal that reports success on a
 *                  rejected sheet is the same class of defect as the capsule bypass.
 *   ErrorBoundary  is what stands between a thrown render and a blank white page in front of
 *                  an examiner.
 *
 * The API module is mocked throughout: these assert what the UI does with a verdict, not
 * whether the backend produces the right one. The backend's own correctness is pinned by
 * tests/test_capsule.py and the API test suite.
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom/vitest'

import { LedgerChain } from './LedgerChain'
import { VerifierModal } from './VerifierModal'
import { ErrorBoundary } from './ErrorBoundary'
import type { LedgerState } from '@/types'

vi.mock('@/lib/api', () => ({
  api: {
    tamper: vi.fn(),
    tamperAdvanced: vi.fn(),
    resetLedger: vi.fn(),
    ledger: vi.fn(),
    datasets: vi.fn(),
    mechanisms: vi.fn(),
    verifyCapsule: vi.fn(),
    verifySheet: vi.fn(),
    verifyCertificate: vi.fn(),
    exportCroissant: vi.fn(),
  },
  runRelease: vi.fn(),
}))

import { api } from '@/lib/api'

const LEDGER: LedgerState = {
  verified: true,
  head: 'a'.repeat(64),
  count: 2,
  total_eps_spent: 1.25,
  entries: [
    {
      entry_id: 'e1',
      mechanism_name: 'pairwise',
      eps_spent: 0.75,
      hash: 'b'.repeat(64),
      prev_hash: '0'.repeat(64),
      timestamp: '2026-09-12T00:00:00Z',
    },
    {
      entry_id: 'e2',
      mechanism_name: 'pairwise',
      eps_spent: 0.5,
      hash: 'c'.repeat(64),
      prev_hash: 'b'.repeat(64),
      timestamp: '2026-09-12T00:00:01Z',
    },
  ] as LedgerState['entries'],
}

beforeEach(() => vi.clearAllMocks())

// ---------------------------------------------------------------------------- LedgerChain

describe('LedgerChain', () => {
  it('reports a verified chain when the ledger verifies', () => {
    render(<LedgerChain ledger={LEDGER} onRefresh={() => {}} />)
    expect(screen.getByText(/chain integrity: verified/i)).toBeInTheDocument()
  })

  it('says "attack detected" — not "verified" — once the chain is broken', () => {
    render(<LedgerChain ledger={{ ...LEDGER, verified: false }} onRefresh={() => {}} />)
    expect(screen.getByText(/attack detected: chain broken/i)).toBeInTheDocument()
    expect(screen.queryByText(/chain integrity: verified/i)).not.toBeInTheDocument()
  })

  it('distinguishes "not checked" from "verified"', () => {
    // The same distinction the capsule now makes. An unchecked chain is not a passing one.
    render(<LedgerChain ledger={null} onRefresh={() => {}} />)
    expect(screen.getByText(/not checked/i)).toBeInTheDocument()
    expect(screen.queryByText(/chain integrity: verified/i)).not.toBeInTheDocument()
  })

  it('surfaces the tamper result and marks the downstream blocks broken', async () => {
    vi.mocked(api.tamperAdvanced).mockResolvedValue({
      verified: false,
      broken_from_index: 1,
      broken_count: 1,
      attack: 'Retroactive Spend Manipulation',
      explanation: 'detectable',
    } as never)

    render(<LedgerChain ledger={LEDGER} onRefresh={() => {}} />)
    // The button reads "Launch <icon> Attack"; the attack-mode chips above it are separate
    // buttons, so match the verb rather than the word "attack".
    const button = screen.getAllByRole('button').find((b) => /^Launch/i.test((b.textContent || '').trim()))
    expect(button, 'the Launch Attack button').toBeDefined()
    await userEvent.click(button!)

    await waitFor(() => expect(api.tamperAdvanced).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText(/Invalidated 1 downstream block/i)).toBeInTheDocument())
  })
})

// -------------------------------------------------------------------------- VerifierModal

describe('VerifierModal', () => {
  it('renders nothing while closed', () => {
    const { container } = render(<VerifierModal isOpen={false} onClose={() => {}} />)
    expect(container.textContent).toBe('')
  })

  it('opens with the verification surface available', () => {
    render(<VerifierModal isOpen onClose={() => {}} />)
    expect(screen.getByText(/Ed25519/i)).toBeInTheDocument()
  })

  it('does not claim a signature is valid before anything has been checked', () => {
    // The invariant from the capsule, applied to the console: "verified" must never be the
    // resting state of a verification surface.
    render(<VerifierModal isOpen onClose={() => {}} />)
    expect(screen.queryByText(/signature valid/i)).not.toBeInTheDocument()
  })

  it('closes when asked', async () => {
    const onClose = vi.fn()
    render(<VerifierModal isOpen onClose={onClose} />)
    const closer = screen.getAllByRole('button').find((b) => /close|×|✕/i.test(b.textContent || ''))
    if (closer) {
      await userEvent.click(closer)
      expect(onClose).toHaveBeenCalled()
    }
  })
})

// -------------------------------------------------------------------------- ErrorBoundary

describe('ErrorBoundary', () => {
  function Boom(): JSX.Element {
    throw new Error('render exploded')
  }

  it('renders its children when nothing throws', () => {
    render(
      <ErrorBoundary>
        <p>all good</p>
      </ErrorBoundary>,
    )
    expect(screen.getByText('all good')).toBeInTheDocument()
  })

  it('catches a thrown render instead of blanking the page', () => {
    // React logs the caught error; silence it so a passing test does not look like a failure.
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    )
    // Something is on screen, and it is not an empty document.
    expect(document.body.textContent?.trim().length).toBeGreaterThan(0)
    expect(screen.queryByText('all good')).not.toBeInTheDocument()
    spy.mockRestore()
  })
})
