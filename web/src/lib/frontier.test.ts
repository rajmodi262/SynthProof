import { describe, expect, it } from 'vitest'
import { SWEEP_GRID, pointFromResult, seriesFor, seriesKey, sweepCost, type FrontierPoint } from './frontier'
import type { RunRequest, RunResult } from '@/types'

const REQ: RunRequest = {
  dataset: 'toy', mechanism: 'pairwise', target_eps: 2, delta: 1e-5, seed: null, num_canaries: 60, rows: 2000,
}

function point(over: Partial<FrontierPoint>): FrontierPoint {
  return {
    target_eps: 1, proved_eps: 1, tstr_f1: 0.5, trtr_f1: 0.8, correlation_error: 0.01,
    dataset: 'toy', mechanism: 'pairwise', rows: 2000, entry_id: 'e', hash: 'h', ...over,
  }
}

describe('measured frontier', () => {
  it('takes every number from the completed release and its ledger entry', () => {
    const r = {
      measurements: { proved_eps: 1.97, tstr_f1: 0.61, trtr_f1: 0.83, correlation_error: 0.02 },
      ledger: { entry_id: 'abc', hash: 'f'.repeat(64) },
    } as unknown as RunResult
    expect(pointFromResult(REQ, r)).toEqual({
      target_eps: 2, proved_eps: 1.97, tstr_f1: 0.61, trtr_f1: 0.83, correlation_error: 0.02,
      dataset: 'toy', mechanism: 'pairwise', rows: 2000, entry_id: 'abc', hash: 'f'.repeat(64),
    })
  })

  it('never mixes tables, mechanisms or sizes in one series', () => {
    const pts = [
      point({ entry_id: 'a', proved_eps: 4 }),
      point({ entry_id: 'b', proved_eps: 1 }),
      point({ entry_id: 'c', mechanism: 'aim' }),
      point({ entry_id: 'd', rows: 500 }),
      point({ entry_id: 'e', dataset: 'adult' }),
    ]
    expect(seriesFor(pts, seriesKey(REQ)).map((p) => p.entry_id)).toEqual(['b', 'a'])
  })

  it('drops a point with a non-finite measurement instead of plotting it', () => {
    expect(seriesFor([point({ tstr_f1: NaN })], seriesKey(REQ))).toEqual([])
  })

  it('states the true cost of a sweep: the sum of its budgets', () => {
    expect(sweepCost()).toBe(SWEEP_GRID.reduce((a, b) => a + b, 0))
    expect(sweepCost([0.5, 1])).toBe(1.5)
  })
})
