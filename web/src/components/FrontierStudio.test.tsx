/* The frontier panel shows measured releases and nothing else (W8). It used to draw a
 * saturation curve from a hand-picked constant; these pin that no point appears that did not
 * come from a release, and that each one carries its ledger entry. */
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom/vitest'
import { FrontierStudio } from './FrontierStudio'
import type { FrontierPoint } from '@/lib/frontier'

function point(eps: number, id: string): FrontierPoint {
  return {
    target_eps: eps, proved_eps: eps * 0.98, tstr_f1: 0.4 + eps / 20, trtr_f1: 0.8,
    correlation_error: 0.01, dataset: 'toy', mechanism: 'pairwise', rows: 2000,
    entry_id: id, hash: id.repeat(8),
  }
}

describe('FrontierStudio', () => {
  it('draws nothing when no release has run', () => {
    const { container } = render(<FrontierStudio result={null} points={[]} />)
    expect(screen.queryAllByTestId('frontier-point')).toHaveLength(0)
    expect(container.querySelector('path[stroke="#F59E0B"]')).toBeNull()
    expect(screen.getByText(/No comparable releases yet/)).toBeInTheDocument()
  })

  it('draws one point per release and lists each with its ledger entry', () => {
    const pts = [point(0.5, 'entry-aaaa-01'), point(2, 'entry-bbbb-02'), point(8, 'entry-cccc-03')]
    render(<FrontierStudio result={null} points={pts} />)
    expect(screen.getAllByTestId('frontier-point')).toHaveLength(3)
    for (const p of pts) expect(screen.getByText(p.entry_id.slice(0, 12))).toBeInTheDocument()
    expect(screen.getByText(pts[2].tstr_f1.toFixed(3))).toBeInTheDocument()
  })

  it('does not join a single release into a curve', () => {
    const { container } = render(<FrontierStudio result={null} points={[point(1, 'only-one-entry')]} />)
    expect(container.querySelector('path[stroke="#F59E0B"]')).toBeNull()
    expect(screen.getByText(/One release measured/)).toBeInTheDocument()
  })

  it('states what a sweep costs and will not start one while a release runs', async () => {
    const onSweep = vi.fn()
    const { rerender } = render(<FrontierStudio result={null} points={[]} onSweep={onSweep} running />)
    expect(screen.getByText(/charges ε = 15.5 to the ledger/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Sweep ε/ })).toBeDisabled()
    rerender(<FrontierStudio result={null} points={[]} onSweep={onSweep} />)
    await userEvent.click(screen.getByRole('button', { name: /Sweep ε/ }))
    expect(onSweep).toHaveBeenCalledOnce()
  })
})
