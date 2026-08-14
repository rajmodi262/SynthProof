import { useCallback, useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { api, runRelease } from '@/lib/api'
import { RecordCloud, type CloudLayer } from '@/components/RecordCloud'
import { BoundsGauge, BudgetMeter, Metric } from '@/components/Readouts'
import { PipelineLog } from '@/components/PipelineLog'
import { LedgerChain } from '@/components/LedgerChain'
import { AttackDossier } from '@/components/AttackDossier'
import { Marginals } from '@/components/Marginals'
import { Controls } from '@/components/Controls'
import type {
  DatasetOption,
  LedgerState,
  Mechanism,
  NotImplementedAttack,
  RunRequest,
  RunResult,
  StageEvent,
  StartEvent,
} from '@/types'

const DEFAULT_CONFIG: RunRequest = {
  dataset: 'toy',
  mechanism: 'pairwise',
  target_eps: 1.0,
  delta: 1e-5,
  seed: 0,
  num_canaries: 60,
  rows: 2000,
}

function useTheme() {
  const [dark, setDark] = useState(
    () =>
      localStorage.getItem('sp-theme') === 'dark' ||
      (!localStorage.getItem('sp-theme') &&
        window.matchMedia('(prefers-color-scheme: dark)').matches),
  )
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('sp-theme', dark ? 'dark' : 'light')
  }, [dark])
  return [dark, setDark] as const
}

export default function App() {
  const [dark, setDark] = useTheme()

  const [datasets, setDatasets] = useState<DatasetOption[]>([])
  const [mechanisms, setMechanisms] = useState<Mechanism[]>([])
  const [notImplemented, setNotImplemented] = useState<NotImplementedAttack[]>([])
  const [ledger, setLedger] = useState<LedgerState | null>(null)
  const [offline, setOffline] = useState(false)

  const [config, setConfig] = useState<RunRequest>(DEFAULT_CONFIG)
  const [running, setRunning] = useState(false)
  const [stages, setStages] = useState<StageEvent[]>([])
  const [start, setStart] = useState<StartEvent | null>(null)
  const [result, setResult] = useState<RunResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [abort, setAbort] = useState<(() => void) | null>(null)

  const [layer, setLayer] = useState<CloudLayer>('both')
  const [showCanaries, setShowCanaries] = useState(true)
  const [showLinks, setShowLinks] = useState(true)

  const refreshLedger = useCallback(() => {
    api.ledger().then(setLedger).catch(() => undefined)
  }, [])

  useEffect(() => {
    Promise.all([api.datasets(), api.mechanisms(), api.ledger()])
      .then(([d, m, l]) => {
        setDatasets(d.datasets)
        setMechanisms(m.mechanisms)
        setNotImplemented(m.attacks_not_implemented)
        setLedger(l)
        const firstAvailable = m.mechanisms.find((x) => x.available)
        if (firstAvailable && !m.mechanisms.find((x) => x.key === DEFAULT_CONFIG.mechanism)?.available) {
          setConfig((c) => ({ ...c, mechanism: firstAvailable.key }))
        }
      })
      .catch(() => setOffline(true))
  }, [])

  // Budget spent so far, read off whichever charging stage reported last.
  const spent = useMemo(() => {
    for (let i = stages.length - 1; i >= 0; i--) {
      const v = stages[i].eps_spent
      if (typeof v === 'number') return v
    }
    return result?.measurements.proved_eps ?? 0
  }, [stages, result])

  const currentStage = running ? (stages[stages.length - 1]?.stage ?? 'starting') : null

  function handleRun() {
    setRunning(true)
    setStages([])
    setResult(null)
    setError(null)
    setStart(null)

    const cancel = runRelease(config, {
      onStart: setStart,
      onStage: (e) => setStages((prev) => [...prev, e]),
      onDone: (r) => {
        setResult(r)
        setRunning(false)
        refreshLedger()
      },
      onError: (m) => {
        setError(m)
        setRunning(false)
      },
    })
    setAbort(() => cancel)
  }

  function handleCancel() {
    abort?.()
    setRunning(false)
  }

  const m = result?.measurements ?? null

  return (
    <div className="min-h-screen">
      {/* ------------------------------------------------------------- header */}
      <header className="sticky top-0 z-30 border-b border-bone-edge bg-[#F0EFEA]/85 backdrop-blur dark:border-stage-line dark:bg-[#15161C]/85">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-6 gap-y-2 px-6 py-3">
          <div className="flex items-baseline gap-3">
            <span className="font-display text-2xl leading-none">SynthProof</span>
            <span className="hidden font-mono text-2xs uppercase tracking-[0.14em] text-graphite-faint sm:inline">
              synthetic data that ships with its proof
            </span>
          </div>

          <div className="ml-auto flex items-center gap-4">
            {ledger && (
              <span className="hidden items-center gap-1.5 font-mono text-2xs uppercase tracking-[0.1em] md:flex">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    ledger.verified ? 'bg-signal-ok' : 'bg-signal-bad'
                  }`}
                />
                <span className={ledger.verified ? 'text-signal-ok' : 'text-signal-bad'}>
                  chain {ledger.verified ? 'verified' : 'broken'}
                </span>
                <span className="text-graphite-faint">
                  · {ledger.count} releases · Σε {ledger.total_eps_spent.toFixed(2)}
                </span>
              </span>
            )}
            <button
              onClick={() => setDark(!dark)}
              className="rounded-sm border border-bone-edge px-2 py-1 font-mono text-2xs uppercase tracking-[0.1em] text-graphite-faint transition-colors hover:text-graphite dark:border-stage-line dark:hover:text-bone"
            >
              {dark ? 'light' : 'dark'}
            </button>
          </div>
        </div>
      </header>

      {offline && (
        <div className="border-b border-signal-warn/40 bg-signal-warn/[0.08] px-6 py-2.5">
          <p className="mx-auto max-w-[1600px] font-mono text-[11px] text-graphite-soft dark:text-bone">
            Cannot reach the API. Start it with{' '}
            <span className="rounded-sm bg-bone-deep px-1.5 py-0.5 dark:bg-stage-deep">
              uvicorn synthproof.api.main:app --reload --port 8000
            </span>
          </p>
        </div>
      )}

      <main className="mx-auto max-w-[1600px] px-6 py-6">
        {/* ----------------------------------------------------------- top row */}
        <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)_360px]">
          <Controls
            datasets={datasets}
            mechanisms={mechanisms}
            config={config}
            setConfig={setConfig}
            running={running}
            onRun={handleRun}
            onCancel={handleCancel}
            onUploaded={() => api.datasets().then((d) => setDatasets(d.datasets))}
          />

          {/* ------------------------------------------------------- the stage */}
          <section className="flex min-h-[560px] flex-col overflow-hidden rounded-sm bg-stage shadow-inset">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-stage-line px-5 py-3">
              <span className="label text-graphite-faint">Record space</span>

              <div className="flex gap-1">
                {(['both', 'real', 'synthetic'] as CloudLayer[]).map((l) => (
                  <button
                    key={l}
                    onClick={() => setLayer(l)}
                    className={`rounded-sm px-2 py-1 font-mono text-[10px] uppercase tracking-[0.1em] transition-colors ${
                      layer === l
                        ? 'bg-stage-line text-bone'
                        : 'text-graphite-faint hover:text-bone'
                    }`}
                  >
                    {l}
                  </button>
                ))}
              </div>

              <label className="flex cursor-pointer items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-graphite-faint">
                <input
                  type="checkbox"
                  checked={showCanaries}
                  onChange={(e) => setShowCanaries(e.target.checked)}
                  className="accent-[#FF5C7A]"
                />
                canaries
              </label>
              <label className="flex cursor-pointer items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.1em] text-graphite-faint">
                <input
                  type="checkbox"
                  checked={showLinks}
                  onChange={(e) => setShowLinks(e.target.checked)}
                  disabled={!showCanaries}
                  className="accent-[#FF5C7A]"
                />
                nearest match
              </label>

              {result && (
                <span className="ml-auto font-mono text-[10px] text-graphite-faint">
                  {result.cloud.method === 'pca'
                    ? `PCA · ${(result.cloud.explained_variance.reduce((a, b) => a + b, 0) * 100).toFixed(0)}% variance`
                    : result.cloud.axes.join(' × ')}
                </span>
              )}
            </div>

            <div className="relative flex-1">
              <RecordCloud
                cloud={result?.cloud ?? null}
                layer={layer}
                showCanaries={showCanaries}
                showLinks={showLinks}
                running={running}
              />

              {!result && (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center px-8">
                  <div className="max-w-md text-center">
                    <p className="font-display text-2xl text-bone">
                      Every point is a real record.
                    </p>
                    <p className="mt-2 text-[13px] leading-relaxed text-graphite-faint">
                      Run a release to see the synthetic cloud drawn against it, with planted
                      canaries linked to their nearest synthetic match — the exact quantity the
                      auditor scores.
                    </p>
                  </div>
                </div>
              )}

              {/* legend */}
              {result && (
                <div className="pointer-events-none absolute bottom-4 left-5 flex flex-col gap-1.5">
                  {[
                    ['#8F8AF0', 'real records'],
                    ['#E8964C', 'synthetic'],
                    ['#FF5C7A', 'planted canaries'],
                  ].map(([c, label]) => (
                    <span
                      key={label}
                      className="flex items-center gap-2 font-mono text-[10px] text-graphite-faint"
                    >
                      <span
                        className="h-1.5 w-1.5 rounded-full"
                        style={{ background: c as string }}
                      />
                      {label}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </section>

          {/* ------------------------------------------------------- readouts */}
          <div className="flex flex-col gap-4">
            <BoundsGauge measurements={m} audit={result?.audit ?? null} targetEps={config.target_eps} />
            <BudgetMeter spent={spent} total={config.target_eps} stage={currentStage} />
            <div className="min-h-[240px] flex-1">
              <PipelineLog stages={stages} running={running} />
            </div>
          </div>
        </div>

        {/* ----------------------------------------------------------- errors */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-4 rounded-sm border-l-2 border-signal-bad bg-signal-bad/[0.07] p-4"
            >
              <span className="label !text-signal-bad">Run failed</span>
              <p className="mt-1 font-mono text-[12px] text-graphite-soft dark:text-bone">
                {error}
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ----------------------------------------------------------- metrics */}
        {m && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
          >
            <Metric
              label="Requested vs charged"
              value={`${(m.proved_eps / config.target_eps).toFixed(3)}×`}
              tone="proved"
              hint={`Asked ε ${config.target_eps.toFixed(2)}, charged ${m.proved_eps.toFixed(3)}. Calibration returns the conservative bracket, so this never exceeds 1.0.`}
            />
            <Metric
              label="Utility gap"
              value={Math.max(0, m.trtr_f1 - m.tstr_f1).toFixed(3)}
              hint={`TSTR ${m.tstr_f1.toFixed(3)} against a TRTR baseline of ${m.trtr_f1.toFixed(3)}, both on the same held-out real split.`}
            />
            <Metric
              label="Correlation error"
              value={m.correlation_error.toFixed(3)}
              tone="audited"
              hint="Mean absolute error over the pairwise correlation matrix. Structured mechanisms should beat the independent baseline here."
            />
            <Metric
              label="MIA AUC"
              value={m.mia_auc.toFixed(3)}
              tone={m.mia_auc > 0.6 ? 'warn' : 'neutral'}
              hint="Nearest-neighbour membership inference. 0.5 is chance; this is a weak baseline, not LiRA."
            />
          </motion.div>
        )}

        {/* ----------------------------------------------------------- detail */}
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <AttackDossier
            attack={result?.attack ?? null}
            audit={result?.audit ?? null}
            notImplemented={notImplemented}
          />
          <LedgerChain ledger={ledger} onRefresh={refreshLedger} />
        </div>

        {result && Object.keys(result.histograms).length > 0 && (
          <div className="mt-4">
            <Marginals histograms={result.histograms} />
          </div>
        )}

        {/* ----------------------------------------------------------- charges */}
        {result && result.spends.length > 0 && (
          <section className="panel mt-4 p-5">
            <header className="mb-3">
              <h3 className="font-display text-xl">Accountant charges</h3>
              <p className="mt-0.5 text-[12px] text-graphite-faint">
                Every operation that read the sensitive table, and what it cost. Composition is
                sublinear, so the running total is not the sum of the marginals.
              </p>
            </header>
            <div className="thin-scroll max-h-64 overflow-auto">
              <table className="w-full font-mono text-[11px]">
                <thead className="sticky top-0 bg-[#FAF9F6] dark:bg-[#1B1D25]">
                  <tr className="text-left text-graphite-faint">
                    <th className="py-1.5 pr-3 font-normal uppercase tracking-[0.1em]">operation</th>
                    <th className="py-1.5 pr-3 font-normal uppercase tracking-[0.1em]">mech</th>
                    <th className="py-1.5 pr-3 text-right font-normal uppercase tracking-[0.1em]">σ</th>
                    <th className="py-1.5 pr-3 text-right font-normal uppercase tracking-[0.1em]">steps</th>
                    <th className="py-1.5 pr-3 text-right font-normal uppercase tracking-[0.1em]">marginal ε</th>
                    <th className="py-1.5 text-right font-normal uppercase tracking-[0.1em]">total ε</th>
                  </tr>
                </thead>
                <tbody>
                  {result.spends.map((s, i) => (
                    <tr key={i} className="border-t border-bone-edge dark:border-stage-line">
                      <td className="py-1.5 pr-3">{s.run_id ?? '—'}</td>
                      <td className="py-1.5 pr-3 text-graphite-faint">{s.mechanism}</td>
                      <td className="tnum py-1.5 pr-3 text-right">{s.noise_scale.toFixed(3)}</td>
                      <td className="tnum py-1.5 pr-3 text-right">{s.steps}</td>
                      <td className="tnum py-1.5 pr-3 text-right text-audited dark:text-audited-lift">
                        {s.marginal_eps.toFixed(4)}
                      </td>
                      <td className="tnum py-1.5 text-right text-proved dark:text-proved-lift">
                        {s.computed_eps.toFixed(4)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* ----------------------------------------------------------- sheet */}
        {result && start && (
          <section className="panel mt-4 p-5">
            <header className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-display text-xl">Privacy data sheet</h3>
                <p className="mt-0.5 text-[12px] text-graphite-faint">
                  The artefact that ships with the release.
                </p>
              </div>
              <span className="rounded-sm border border-signal-warn/50 px-2 py-1 font-mono text-2xs uppercase tracking-[0.1em] text-signal-warn">
                unsigned
              </span>
            </header>

            <p className="mb-3 text-[11px] leading-relaxed text-graphite-faint">
              {result.ledger.signature_note} Until a persisted key and a standalone{' '}
              <span className="font-mono">synthproof verify</span> command land, this sheet is a
              record, not a proof — and the badge above says so.
            </p>

            <pre className="thin-scroll display max-h-72 overflow-auto p-4 font-mono text-[11px] leading-relaxed text-bone">
{JSON.stringify(
  {
    dataset: start.dataset.name,
    rows: start.dataset.rows,
    columns: start.dataset.cols,
    mechanism: start.mechanism_label,
    target_epsilon: start.target_eps,
    delta: start.delta,
    seed: start.seed,
    epsilon_proved: Number(m?.proved_eps.toFixed(6)),
    epsilon_audited: Number(m?.audited_eps.toFixed(6)),
    audit: {
      p_value: Number(result.audit.p_value.toFixed(6)),
      canaries_in: result.audit.num_members,
      canaries_out: result.audit.num_holdout,
      confidence: result.audit.confidence,
      method: 'Clopper-Pearson lower bound, Fisher exact test',
    },
    utility: {
      tstr_macro_f1: Number(m?.tstr_f1.toFixed(6)),
      trtr_macro_f1: Number(m?.trtr_f1.toFixed(6)),
      target_column: start.target_col,
    },
    attacks_run: [result.attack.name],
    attacks_not_implemented: result.attacks_not_implemented.map((a) => a.name),
    ledger_head: result.ledger.head,
    entry_hash: result.ledger.hash,
    signature: null,
  },
  null,
  2,
)}
            </pre>
          </section>
        )}

        <footer className="mt-8 border-t border-bone-edge py-6 dark:border-stage-line">
          <p className="max-w-3xl text-[11px] leading-relaxed text-graphite-faint">
            Every figure in this console is returned by the pipeline in{' '}
            <span className="font-mono">synthproof/frontier/experiment.py</span>. Nothing is
            hardcoded, and capabilities that do not exist are labelled rather than omitted. Where
            a number is uninformative — ε_audited below the auditor&rsquo;s unmeasured detection
            floor — the interface says that instead of showing a pass.
          </p>
        </footer>
      </main>
    </div>
  )
}
