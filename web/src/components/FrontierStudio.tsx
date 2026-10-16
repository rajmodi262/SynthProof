import { useMemo, useState } from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css' // with the component, not in the render-blocking global sheet
import type { RunResult } from '@/types'
import { SWEEP_GRID, sweepCost, type FrontierPoint } from '@/lib/frontier'

interface FrontierStudioProps {
  result: RunResult | null
  /** The measured points comparable with the current release (same table, mechanism, size). */
  points: FrontierPoint[]
  /** Runs one real release per budget in SWEEP_GRID. */
  onSweep?: () => void
  /** True while any release is running; a sweep cannot start then. */
  running?: boolean
  /** 1-based progress of a running sweep, or null. */
  sweepProgress?: { done: number; total: number } | null
}

function MathSpan({
  math,
  display = false,
  className = '',
}: {
  math: string
  display?: boolean
  className?: string
}) {
  const html = useMemo(() => {
    try {
      return katex.renderToString(math, { displayMode: display, throwOnError: false })
    } catch {
      return math
    }
  }, [math, display])
  return <span className={className} dangerouslySetInnerHTML={{ __html: html }} />
}

// Plot geometry. Epsilon spans orders of magnitude, so the x-axis is logarithmic.
const W = 480
const H = 180
const PAD = 10
const TICKS = [0.25, 0.5, 1, 2, 4, 8, 16]

export function FrontierStudio({
  result,
  points,
  onSweep,
  running = false,
  sweepProgress = null,
}: FrontierStudioProps) {
  const [matrixView, setMatrixView] = useState<'diff' | 'real' | 'synth'>('diff')

  // Every value below comes from `points` -- completed releases -- or from `result`. Nothing is
  // modelled, extrapolated or defaulted: with no releases the plot is empty and says so.
  const epsValues = points.map((p) => p.proved_eps).filter((e) => e > 0)
  const lo = Math.min(0.25, ...epsValues)
  const hi = Math.max(16, ...epsValues)
  const xOf = (eps: number) => ((Math.log(Math.max(eps, lo)) - Math.log(lo)) / (Math.log(hi) - Math.log(lo))) * W
  const yOf = (f1: number) => H - Math.min(Math.max(f1, 0), 1) * (H - 2 * PAD) - PAD
  const path = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${xOf(p.proved_eps).toFixed(1)},${yOf(p.tstr_f1).toFixed(1)}`)
    .join(' ')
  const trtr = result ? result.measurements.trtr_f1 : null
  const currentId = result?.ledger.entry_id

  // MEASURED correlations from the run (api/projection.correlation_matrices).
  const corr = result?.correlations ?? null
  const cols = corr ? corr.columns : []
  const offDiag = corr
    ? corr.real.flatMap((row, i) => row.map((r, j) => (i < j ? Math.abs(r - corr.synth[i][j]) : NaN)))
        .filter((v) => !Number.isNaN(v))
    : []
  const meanAbsDiff = offDiag.length ? offDiag.reduce((a, b) => a + b, 0) / offDiag.length : null
  const maxAbsDiff = offDiag.length ? Math.max(...offDiag) : null

  return (
    <section className="well overflow-hidden rounded-2xl border border-line bg-card/75 p-5 shadow-e0 backdrop-blur-md">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-line/60 pb-3.5">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-display text-2xl text-ink">Measured Frontier & Correlation Topology</h3>
            <span className="rounded-full border border-brass/40 bg-brass/10 px-2.5 py-0.5 font-mono text-[9px] font-bold text-brass tracking-wider">
              MEASURED ONLY
            </span>
          </div>
          <p className="mt-1 font-sans text-xs text-muted">
            Each point is a release that ran and was charged to the ledger. No curve is fitted or
            drawn between budgets that were not run.
          </p>
        </div>
      </header>

      <div className="grid gap-6 xl:grid-cols-2">
        {/* -------------------------------------- Measured privacy-utility frontier */}
        <div className="rounded-xl border border-line bg-paper-2/60 p-4 shadow-sm">
          <div className="flex items-baseline justify-between">
            <span className="font-mono text-xs font-bold uppercase tracking-wider text-ink">
              Privacy-utility frontier
            </span>
            <span className="font-mono text-xs text-brass">
              <MathSpan math="\text{TSTR } F_1 \text{ vs proved } \varepsilon" />
            </span>
          </div>

          <div className="relative mt-3 h-48 w-full">
            <svg
              viewBox={`0 0 ${W} ${H + 14}`}
              className="h-full w-full overflow-visible"
              role="img"
              aria-label={`Measured frontier: ${points.length} release${points.length === 1 ? '' : 's'}`}
            >
              <line x1="0" y1={H - PAD} x2={W} y2={H - PAD} stroke="currentColor" className="text-line" strokeWidth="1" />
              {TICKS.filter((t) => t >= lo && t <= hi).map((t) => (
                <g key={t}>
                  <line x1={xOf(t)} y1={PAD} x2={xOf(t)} y2={H - PAD} stroke="currentColor" className="text-line" strokeWidth="0.5" strokeDasharray="2 3" />
                  <text x={xOf(t)} y={H + 8} textAnchor="middle" fill="currentColor" className="text-muted" fontSize="9" fontFamily="Geist Mono">
                    ε={t}
                  </text>
                </g>
              ))}

              {trtr !== null && (
                <g>
                  <line x1="0" y1={yOf(trtr)} x2={W} y2={yOf(trtr)} stroke="#38BDF8" strokeWidth="1.5" strokeDasharray="4 4" />
                  <text x={W - 6} y={yOf(trtr) - 4} textAnchor="end" fill="#38BDF8" fontSize="10" fontFamily="Geist Mono" fontWeight="600">
                    TRTR, this release ({trtr.toFixed(3)})
                  </text>
                </g>
              )}

              {points.length > 1 && <path d={path} fill="none" stroke="#F59E0B" strokeWidth="2" />}

              {points.map((p) => (
                <circle
                  key={p.entry_id}
                  data-testid="frontier-point"
                  cx={xOf(p.proved_eps)}
                  cy={yOf(p.tstr_f1)}
                  r={p.entry_id === currentId ? 7 : 5}
                  fill={p.entry_id === currentId ? '#38BDF8' : '#F59E0B'}
                  stroke="#FFFFFF"
                  strokeWidth="1.5"
                >
                  <title>{`proved ε ${p.proved_eps.toFixed(3)} · TSTR F1 ${p.tstr_f1.toFixed(3)} · ledger ${p.entry_id}`}</title>
                </circle>
              ))}
            </svg>
          </div>

          {points.length < 2 && (
            <p className="mt-2 font-mono text-[11px] text-faint">
              {points.length === 0
                ? 'No comparable releases yet.'
                : 'One release measured. A frontier needs releases at several budgets: run a sweep, or run this configuration again at another ε.'}
            </p>
          )}

          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-line/60 pt-2.5">
            <button
              type="button"
              onClick={onSweep}
              disabled={!onSweep || running}
              className="rounded-md bg-brass px-3 py-1.5 font-mono text-xs font-bold text-on-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              {sweepProgress
                ? `Sweeping: release ${sweepProgress.done} of ${sweepProgress.total}`
                : `Sweep ε ∈ {${SWEEP_GRID.join(', ')}}`}
            </button>
            <span className="font-mono text-[11px] text-muted">
              {SWEEP_GRID.length} real releases; charges ε = {sweepCost()} to the ledger
            </span>
          </div>

          {points.length > 0 && (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full border-collapse font-mono text-[11px]" aria-label="Measured frontier points">
                <thead>
                  <tr className="text-muted">
                    <th className="p-1 text-left font-normal">target ε</th>
                    <th className="p-1 text-left font-normal">proved ε</th>
                    <th className="p-1 text-left font-normal">TSTR F1</th>
                    <th className="p-1 text-left font-normal">corr. error</th>
                    <th className="p-1 text-left font-normal">ledger entry</th>
                  </tr>
                </thead>
                <tbody>
                  {points.map((p) => (
                    <tr key={p.entry_id} className={p.entry_id === currentId ? 'text-ink font-bold' : 'text-ink'}>
                      <td className="p-1">{p.target_eps}</td>
                      <td className="p-1">{p.proved_eps.toFixed(3)}</td>
                      <td className="p-1">{p.tstr_f1.toFixed(3)}</td>
                      <td className="p-1">{p.correlation_error.toFixed(4)}</td>
                      <td className="p-1 text-muted" title={p.hash}>
                        {p.entry_id.slice(0, 12)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* -------------------------------------- Pairwise Correlation Matrix */}
        <div className="rounded-xl border border-line bg-paper-2/60 p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-mono text-xs font-bold uppercase tracking-wider text-ink">
              <span>Feature Correlation Matrix</span>
              <MathSpan math="(R_{i,j})" className="text-brass normal-case" />
            </div>
            <div className="flex rounded-lg border border-line bg-card p-0.5 shadow-2xs">
              {(['diff', 'real', 'synth'] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setMatrixView(mode)}
                  className={`rounded px-2.5 py-1 font-mono text-[10px] font-bold uppercase tracking-wider transition-all ${
                    matrixView === mode
                      ? 'bg-brass text-on-accent shadow-xs'
                      : 'text-muted hover:text-ink hover:bg-paper-2'
                  }`}
                >
                  {mode === 'diff' ? 'Δ Diff MAE' : mode === 'real' ? 'Real R' : 'Synth R'}
                </button>
              ))}
            </div>
          </div>

          <p className="mt-1 font-sans text-xs text-muted leading-relaxed">
            {matrixView === 'diff' ? (
              <span>
                Absolute correlation distortion <MathSpan math="|R_{\text{real}} - R_{\text{synth}}|" />. Emerald indicates near-zero structural deformation.
              </span>
            ) : matrixView === 'real' ? (
              <span>
                Empirical Pearson correlation coefficients <MathSpan math="R_{\text{real}}" /> on original sensitive training data.
              </span>
            ) : (
              <span>
                Pearson correlation <MathSpan math="R_{\text{synth}}" /> of the released synthetic table.
              </span>
            )}
          </p>

          {!corr && (
            <p className="mt-3 font-mono text-[11px] text-faint">
              {result
                ? 'Not computed: this table has fewer than two numeric columns.'
                : 'Run a release to compute the measured correlation matrix.'}
            </p>
          )}
          <div className="mt-3 overflow-x-auto">
            <table className="w-full border-collapse font-mono text-[11px]">
              <thead>
                <tr>
                  <th className="p-1 text-left font-normal text-muted"></th>
                  {cols.map((c) => (
                    <th key={c} className="p-1 text-center font-semibold text-ink truncate max-w-[70px]">
                      {c.slice(0, 8)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cols.map((rowCol, rIdx) => (
                  <tr key={rowCol}>
                    <td className="p-1 text-right font-semibold text-muted truncate max-w-[80px]">
                      {rowCol.slice(0, 8)}
                    </td>
                    {cols.map((colCol, cIdx) => {
                      // Measured values from the run (see `corr` above).
                      const isDiag = rIdx === cIdx
                      const realCorr = corr ? corr.real[rIdx][cIdx] : 0
                      const synthCorr = corr ? corr.synth[rIdx][cIdx] : 0
                      const diff = isDiag ? 0.0 : Math.abs(realCorr - synthCorr)

                      const val = matrixView === 'diff' ? diff : matrixView === 'real' ? realCorr : synthCorr
                      // The tint carries the band; the number stays ink so it reads in both themes.
                      const cellStyle =
                        matrixView === 'diff'
                          ? diff < 0.04
                            ? 'bg-emerald-500/20 text-ink border border-emerald-500/40 font-bold'
                            : diff < 0.10
                              ? 'bg-amber-500/20 text-ink border border-amber-500/40'
                              : 'bg-rose-500/25 text-ink border border-rose-500/40'
                          : Math.abs(val) > 0.4
                            ? 'bg-sky-500/20 text-ink border border-sky-500/40 font-bold'
                            : 'bg-card text-muted border border-line/40'

                      return (
                        <td
                          key={colCol}
                          className={`p-1.5 text-center font-mono rounded-[3px] transition-all hover:scale-105 ${cellStyle}`}
                        >
                          {val.toFixed(2)}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex items-center justify-between border-t border-line/60 pt-2 font-mono text-xs text-muted">
            <span>
              Mean |ΔR| off-diagonal:{' '}
              <strong className="text-ink">{meanAbsDiff !== null ? meanAbsDiff.toFixed(3) : '—'}</strong>
            </span>
            <span>
              Max |ΔR|:{' '}
              <strong className="text-ink">{maxAbsDiff !== null ? maxAbsDiff.toFixed(3) : '—'}</strong>
            </span>
          </div>
        </div>
      </div>
    </section>
  )
}
