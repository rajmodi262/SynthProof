// The privacy-utility frontier, built ONLY from releases that actually ran.
//
// Until 2026-10-16 the console drew F1(eps) = F_inf * (1 - exp(-1.45 * eps)) -- a curve with a
// hand-picked rate constant and a 0.82 fallback ceiling, labelled "illustrative". A labelled
// fiction is still a fiction on a screen an examiner reads. Every point here is a completed run:
// its proved epsilon, its measured TSTR F1, and the ledger entry that charged for it.
import type { RunRequest, RunResult } from '@/types'

export interface FrontierPoint {
  /** Requested budget. */
  target_eps: number
  /** The epsilon the accountant proved for this release (the x-axis). */
  proved_eps: number
  tstr_f1: number
  trtr_f1: number
  correlation_error: number
  dataset: string
  mechanism: string
  rows: number
  /** Provenance: the signed ledger entry that charged this release. */
  entry_id: string
  hash: string
}

/**
 * The budgets a sweep runs. Each one is a real release, charged to the ledger, so the whole
 * sweep costs the sum of the grid.
 */
export const SWEEP_GRID: readonly number[] = [0.5, 1, 2, 4, 8]

export function sweepCost(grid: readonly number[] = SWEEP_GRID): number {
  return grid.reduce((a, b) => a + b, 0)
}

export function pointFromResult(req: RunRequest, r: RunResult): FrontierPoint {
  return {
    target_eps: req.target_eps,
    proved_eps: r.measurements.proved_eps,
    tstr_f1: r.measurements.tstr_f1,
    trtr_f1: r.measurements.trtr_f1,
    correlation_error: r.measurements.correlation_error,
    dataset: req.dataset,
    mechanism: req.mechanism,
    rows: req.rows,
    entry_id: r.ledger.entry_id,
    hash: r.ledger.hash,
  }
}

/** Releases are comparable only on the same table, mechanism and size. */
export function seriesKey(p: Pick<FrontierPoint, 'dataset' | 'mechanism' | 'rows'>): string {
  return `${p.dataset}|${p.mechanism}|${p.rows}`
}

/** The comparable points for one configuration, in increasing proved epsilon. */
export function seriesFor(points: readonly FrontierPoint[], key: string): FrontierPoint[] {
  return points
    .filter((p) => seriesKey(p) === key && Number.isFinite(p.proved_eps) && Number.isFinite(p.tstr_f1))
    .sort((a, b) => a.proved_eps - b.proved_eps || a.target_eps - b.target_eps)
}
