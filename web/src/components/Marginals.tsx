import type { Histogram } from '@/types'

/**
 * Real vs synthetic marginals, drawn on shared bin edges.
 *
 * Shared edges are the whole point: two histograms binned independently cannot be compared,
 * and independent binning is a common way for a fidelity chart to flatter a generator. The
 * server computes both from one set of edges fitted on the real column.
 */
function Spark({ hist, name }: { hist: Histogram; name: string }) {
  const w = 240
  const h = 56
  const peak = Math.max(...hist.real, ...hist.synthetic, 1e-9)
  const n = hist.real.length

  const path = (vals: number[]) =>
    vals
      .map((v, i) => {
        const x = (i / Math.max(1, n - 1)) * w
        const y = h - (v / peak) * h
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
      })
      .join(' ')

  const area = (vals: number[]) => `${path(vals)} L${w},${h} L0,${h} Z`

  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between">
        <span className="font-mono text-[11px] text-graphite-soft dark:text-bone">{name}</span>
        <span className="font-mono text-[10px] text-graphite-faint">
          {hist.edges[0].toFixed(0)} – {hist.edges[hist.edges.length - 1].toFixed(0)}
        </span>
      </div>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        className="h-14 w-full"
        preserveAspectRatio="none"
        role="img"
        aria-label={`Distribution of ${name}, real versus synthetic`}
      >
        <path d={area(hist.real)} className="fill-proved/15" />
        <path d={path(hist.real)} className="stroke-proved" fill="none" strokeWidth="1.5" />
        <path
          d={path(hist.synthetic)}
          className="stroke-audited"
          fill="none"
          strokeWidth="1.5"
          strokeDasharray="3 2"
        />
      </svg>
    </div>
  )
}

export function Marginals({ histograms }: { histograms: Record<string, Histogram> }) {
  const entries = Object.entries(histograms)
  if (!entries.length) return null

  return (
    <section className="panel p-5">
      <header className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h3 className="font-display text-xl">Marginal fidelity</h3>
          <p className="mt-0.5 text-[12px] text-graphite-faint">
            Per-column distributions on shared bin edges.
          </p>
        </div>
        <div className="flex items-center gap-4 font-mono text-[10px] text-graphite-faint">
          <span className="flex items-center gap-1.5">
            <svg width="16" height="2" aria-hidden="true">
              <line x1="0" y1="1" x2="16" y2="1" className="stroke-proved" strokeWidth="2" />
            </svg>
            real
          </span>
          <span className="flex items-center gap-1.5">
            <svg width="16" height="2" aria-hidden="true">
              <line
                x1="0"
                y1="1"
                x2="16"
                y2="1"
                className="stroke-audited"
                strokeWidth="2"
                strokeDasharray="3 2"
              />
            </svg>
            synthetic
          </span>
        </div>
      </header>

      <div className="grid gap-5 sm:grid-cols-2">
        {entries.map(([name, hist]) => (
          <Spark key={name} hist={hist} name={name} />
        ))}
      </div>
    </section>
  )
}
