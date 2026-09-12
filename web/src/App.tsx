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
import { VerifierModal } from '@/components/VerifierModal'
import { GuidedTourModal } from '@/components/GuidedTourModal'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { FrontierStudio } from '@/components/FrontierStudio'
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
  // The config the displayed result was actually produced with, frozen at launch.
  const [submitted, setSubmitted] = useState<RunRequest | null>(null)
  const [running, setRunning] = useState(false)
  const [stages, setStages] = useState<StageEvent[]>([])
  const [start, setStart] = useState<StartEvent | null>(null)
  const [result, setResult] = useState<RunResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [abort, setAbort] = useState<(() => void) | null>(null)
  const [verifierOpen, setVerifierOpen] = useState(false)
  const [tourOpen, setTourOpen] = useState(false)
  const [exportingCapsule, setExportingCapsule] = useState(false)

  async function handleDownloadCapsule() {
    if (!result?.sheet) return
    setExportingCapsule(true)
    try {
      const html = await api.exportCapsule(result.sheet, result.sample_records || [])
      const blob = new Blob([html], { type: 'text/html' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${result.sheet.dataset_name || 'synthproof'}_verified_capsule.html`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err: any) {
      alert(`Export failed: ${err.message}`)
    } finally {
      setExportingCapsule(false)
    }
  }

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

    // Freeze the config this run was launched with. The readouts below divide the charged
    // epsilon by the requested one; reading live `config` meant that moving the slider after
    // a run silently recomputed the ratio against a budget that run never used.
    const submitted = config
    setSubmitted(submitted)

    const cancel = runRelease(submitted, {
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


  const [copiedSheet, setCopiedSheet] = useState(false)

  function copySheetJson() {
    if (!result?.sheet) return
    navigator.clipboard.writeText(JSON.stringify(result.sheet, null, 2))
    setCopiedSheet(true)
    setTimeout(() => setCopiedSheet(false), 2000)
  }

  // The last preset is EXPECTED to be refused, and that is the point of it.
  //
  // It used to be labelled "⚡ Viva Quick (3s)" and pointed at a 400-row table. Pre-flight
  // refuses anything under 500 rows (R1: protecting one record among that few needs noise
  // that leaves nothing to release), so the headline speed button produced a refusal rather
  // than a run -- the system contradicting its own demo. Rather than pad the file to 500
  // rows and lose the example, it is now the one-click demonstration of data-blind refusal,
  // which is one of the three claims that survived the novelty protocol and is better
  // material than a fifth successful run. `refuses` marks it so the UI can say so first.
  type Preset = { id: string; label: string; eps: number; rows: number; refuses?: boolean }
  const DEMO_PRESETS: Preset[] = [
    { id: '01_healthcare_patient_outcomes', label: '🏥 Clinical Outcomes', eps: 0.75, rows: 800 },
    { id: '02_financial_credit_risk', label: '💳 Credit Risk', eps: 1.0, rows: 1000 },
    { id: '03_telecom_customer_churn', label: '📱 Telecom Churn', eps: 1.5, rows: 800 },
    { id: '04_hr_employee_attrition', label: '⚡ HR Attrition (fastest)', eps: 1.0, rows: 600 },
    {
      id: '05_quick_demo_demographics',
      label: '🛑 Refusal demo (400 rows)',
      eps: 0.5,
      rows: 400,
      refuses: true,
    },
  ]

  function selectPreset(preset: Preset) {
    if (running) return
    const found = datasets.find((d) => d.id === preset.id || d.id.includes(preset.id.slice(3, 10)))
    if (found) {
      setConfig((c) => ({
        ...c,
        dataset: found.id,
        target_eps: preset.eps,
        rows: preset.rows,
      }))
    }
  }

  return (
    <div className="min-h-screen bg-[#F0EFEA] text-graphite transition-colors dark:bg-[#121318] dark:text-bone">
      {/* ------------------------------------------------------------- header */}
      <header className="sticky top-0 z-30 border-b border-bone-edge/80 bg-[#F0EFEA]/80 backdrop-blur-md dark:border-stage-line/80 dark:bg-[#15161C]/80">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-x-6 gap-y-2 px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-gradient-to-tr from-proved to-[#6366f1] text-white shadow-sm glow-proved">
              <span className="text-sm font-bold">SP</span>
            </div>
            <div>
              <div className="flex items-baseline gap-2">
                <span className="font-display text-2xl font-normal tracking-tight">SynthProof</span>
                <span className="rounded-full bg-proved/10 px-2 py-0.5 font-mono text-[9px] font-semibold text-proved dark:text-proved-lift">
                  v0.2.0-preview
                </span>
              </div>
              <p className="hidden font-mono text-2xs uppercase tracking-[0.14em] text-graphite-faint sm:block">
                Synthetic data that ships with its proof
              </p>
            </div>
          </div>

          {/* Quick preset selector buttons */}
          <div className="hidden items-center gap-1.5 xl:flex">
            <span className="font-mono text-[10px] uppercase tracking-wider text-graphite-faint">
              Demo Presets:
            </span>
            {DEMO_PRESETS.map((p) => {
              const active = config.dataset === p.id || config.dataset.includes(p.id.slice(3, 10))
              return (
                <button
                  key={p.id}
                  onClick={() => selectPreset(p)}
                  disabled={running}
                  title={
                    p.refuses
                      ? 'Expected to be REFUSED: 400 rows is below the 500-row floor. Demonstrates data-blind refusal — pre-flight sees only the schema and the row count, never the data.'
                      : `${p.rows} rows at eps=${p.eps}`
                  }
                  className={`rounded-full px-2.5 py-1 font-mono text-[10px] font-medium transition-all ${
                    active
                      ? p.refuses
                        ? 'bg-amber-500 text-white shadow-sm'
                        : 'bg-proved text-white shadow-sm glow-proved'
                      : p.refuses
                        ? 'border border-amber-500/60 bg-amber-50/70 text-amber-700 hover:border-amber-500 dark:border-amber-500/50 dark:bg-amber-950/30 dark:text-amber-300'
                        : 'border border-bone-edge/80 bg-white/60 text-graphite-soft hover:border-graphite-faint dark:border-stage-line dark:bg-stage-deep/60 dark:text-bone dark:hover:border-stage-line/90'
                  }`}
                >
                  {p.label}
                </button>
              )
            })}
          </div>

          <div className="flex items-center gap-3">
            {ledger && (
              <span className="hidden items-center gap-2 rounded-full border border-bone-edge/80 bg-white/60 px-3 py-1 font-mono text-2xs uppercase tracking-[0.1em] dark:border-stage-line dark:bg-stage-deep/60 md:flex">
                <span
                  className={`h-2 w-2 rounded-full ${
                    ledger.verified ? 'bg-signal-ok shadow-sm shadow-signal-ok' : 'bg-signal-bad shadow-sm shadow-signal-bad'
                  }`}
                />
                <span className={ledger.verified ? 'text-signal-ok font-medium' : 'text-signal-bad font-medium'}>
                  {ledger.verified ? 'Chain Verified' : 'Chain Broken'}
                </span>
                <span className="text-graphite-faint">
                  · {ledger.count} releases · Σε {ledger.total_eps_spent.toFixed(2)}
                </span>
              </span>
            )}
            <button
              onClick={() => setTourOpen(true)}
              className="flex items-center gap-1.5 rounded-md border border-signal-ok/50 bg-signal-ok/[0.08] px-3 py-1.5 font-mono text-2xs font-semibold uppercase tracking-[0.08em] text-signal-ok transition-all hover:bg-signal-ok/20 hover:shadow-sm"
            >
              <span>🎯</span>
              <span>Guided Tour</span>
            </button>
            <button
              onClick={() => setVerifierOpen(true)}
              className="flex items-center gap-1.5 rounded-md border border-proved/50 bg-proved/[0.08] px-3 py-1.5 font-mono text-2xs font-semibold uppercase tracking-[0.08em] text-proved transition-all hover:bg-proved/20 hover:shadow-sm dark:text-proved-lift"
            >
              <span>🛡️</span>
              <span>Zero-Trust Verifier</span>
            </button>
            <button
              onClick={() => setDark(!dark)}
              className="rounded-md border border-bone-edge px-2.5 py-1.5 font-mono text-2xs uppercase tracking-[0.1em] text-graphite-faint transition-all hover:border-graphite-faint hover:text-graphite dark:border-stage-line dark:hover:text-bone"
              aria-label="Toggle theme"
            >
              {dark ? '☀️ light' : '🌙 dark'}
            </button>
          </div>
        </div>
      </header>

      {offline && (
        <div className="border-b border-signal-warn/40 bg-signal-warn/[0.08] px-6 py-2.5">
          <p className="mx-auto max-w-[1600px] font-mono text-[11px] text-graphite-soft dark:text-bone">
            ⚠️ Cannot reach the API. Start it with{' '}
            <span className="rounded-sm bg-bone-deep px-1.5 py-0.5 dark:bg-stage-deep font-semibold">
              run_prototype.py
            </span>
          </p>
        </div>
      )}

      <main className="mx-auto max-w-[1600px] px-6 py-6">
        {/* Mobile preset selector bar */}
        <div className="mb-4 flex flex-wrap items-center gap-1.5 xl:hidden">
          <span className="font-mono text-[10px] uppercase tracking-wider text-graphite-faint">
            Demo Presets:
          </span>
          {DEMO_PRESETS.map((p) => {
            const active = config.dataset === p.id || config.dataset.includes(p.id.slice(3, 10))
            return (
              <button
                key={p.id}
                onClick={() => selectPreset(p)}
                disabled={running}
                title={
                  p.refuses
                    ? 'Expected to be REFUSED: 400 rows is below the 500-row floor. Demonstrates data-blind refusal — pre-flight sees only the schema and the row count, never the data.'
                    : `${p.rows} rows at eps=${p.eps}`
                }
                className={`rounded-full px-2 py-0.5 font-mono text-[10px] font-medium transition-all ${
                  active
                    ? p.refuses
                      ? 'bg-amber-500 text-white shadow-sm'
                      : 'bg-proved text-white shadow-sm glow-proved'
                    : p.refuses
                      ? 'border border-amber-500/60 bg-amber-50/70 text-amber-700 hover:border-amber-500 dark:border-amber-500/50 dark:bg-amber-950/30 dark:text-amber-300'
                      : 'border border-bone-edge/80 bg-white/60 text-graphite-soft hover:border-graphite-faint dark:border-stage-line dark:bg-stage-deep/60 dark:text-bone'
                }`}
              >
                {p.label}
              </button>
            )
          })}
        </div>
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
              <ErrorBoundary fallbackTitle="3D Point Cloud View">
                <RecordCloud
                  cloud={result?.cloud ?? null}
                  layer={layer}
                  showCanaries={showCanaries}
                  showLinks={showLinks}
                  running={running}
                />
              </ErrorBoundary>

              {!result && (
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center p-6 text-center">
                  <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-proved/15 ring-1 ring-proved/30 animate-pulse">
                    <span className="text-2xl">🌐</span>
                  </div>
                  <p className="font-display text-2xl text-bone">
                    High-Dimensional Latent Manifold
                  </p>
                  <p className="mt-2 max-w-md text-xs leading-relaxed text-graphite-faint">
                    Real records, DP synthetic records, and planted adversarial canaries projected into a shared 3D coordinate space via fitted PCA.
                  </p>
                  <div className="mt-4 flex flex-wrap justify-center gap-2">
                    <span className="rounded-full bg-stage-line/80 px-2.5 py-1 font-mono text-[10px] text-proved-lift">
                      🟣 Real Records
                    </span>
                    <span className="rounded-full bg-stage-line/80 px-2.5 py-1 font-mono text-[10px] text-audited-lift">
                      🟠 DP Synthetic
                    </span>
                    <span className="rounded-full bg-stage-line/80 px-2.5 py-1 font-mono text-[10px] text-[#FF5C7A]">
                      🔴 Planted Canaries
                    </span>
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
            <BoundsGauge measurements={m} audit={result?.audit ?? null} targetEps={(submitted ?? config).target_eps} />
            <BudgetMeter spent={spent} total={(submitted ?? config).target_eps} stage={currentStage} />
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
              icon="⚖️"
              label="Requested vs charged"
              value={`${(m.proved_eps / (submitted ?? config).target_eps).toFixed(3)}×`}
              tone="proved"
              hint={`Asked ε ${(submitted ?? config).target_eps.toFixed(2)}, charged ${m.proved_eps.toFixed(3)}. Calibration returns the conservative bracket, so this never exceeds 1.0.`}
            />
            <Metric
              icon="🎯"
              label="Utility gap (TRTR - TSTR)"
              value={Math.max(0, m.trtr_f1 - m.tstr_f1).toFixed(3)}
              hint={`TSTR ${m.tstr_f1.toFixed(3)} against a TRTR baseline of ${m.trtr_f1.toFixed(3)}, both on the same held-out real split.`}
            />
            <Metric
              icon="🔬"
              label="Correlation error (MAE)"
              value={m.correlation_error.toFixed(3)}
              tone="audited"
              hint={
                `Mean absolute error over the pairwise correlation matrix, scored against ` +
                `the ${result?.evaluation.reference ?? 'fit split'}. ` +
                (result && typeof result.evaluation.canary_fraction === 'number'
                  ? `The fit contained ${(result.evaluation.canary_fraction * 100).toFixed(1)}% planted canaries, which biases this figure — treat it as indicative, not a clean fidelity measurement.`
                  : '')
              }
            />
            <Metric
              icon="🛡️"
              label="MIA Resistance (AUC)"
              value={m.mia_auc.toFixed(3)}
              tone={m.mia_auc > 0.6 ? 'warn' : 'neutral'}
              hint="Nearest-neighbour membership inference. 0.5 is chance (ideal defense); this is a weak baseline, not LiRA."
            />
          </motion.div>
        )}

        {/* ----------------------------------------------------------- Frontier Modeling & Correlation Topology */}
        <div className="mt-4">
          <ErrorBoundary fallbackTitle="Frontier Modeling Studio">
            <FrontierStudio
              measurements={m}
              result={result}
              targetEps={(submitted ?? config).target_eps}
            />
          </ErrorBoundary>
        </div>

        {/* ----------------------------------------------------------- detail */}
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <ErrorBoundary fallbackTitle="Adversarial Attack Dossier">
            <AttackDossier
              attack={result?.attack ?? null}
              audit={result?.audit ?? null}
              notImplemented={notImplemented}
            />
          </ErrorBoundary>
          <ErrorBoundary fallbackTitle="Cryptographic Ledger Chain">
            <LedgerChain ledger={ledger} onRefresh={refreshLedger} />
          </ErrorBoundary>
        </div>

        {result && Object.keys(result.histograms).length > 0 && (
          <div className="mt-4">
            <ErrorBoundary fallbackTitle="Marginal Fidelity Histograms">
              <Marginals histograms={result.histograms} />
            </ErrorBoundary>
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
                  The verified cryptographic artefact that ships with the release.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-sm border px-2.5 py-1 font-mono text-2xs uppercase tracking-[0.1em] ${
                    result.sheet?.signature
                      ? 'border-signal-ok/40 bg-signal-ok/[0.08] text-signal-ok'
                      : 'border-signal-warn/50 text-signal-warn'
                  }`}
                >
                  {result.sheet?.signature ? '✓ signed (Ed25519)' : 'unsigned'}
                </span>
                <button
                  onClick={() => setVerifierOpen(true)}
                  className="btn-primary !px-2.5 !py-1 !text-xs"
                >
                  🛡️ Inspect in Verifier
                </button>
                <button
                  onClick={copySheetJson}
                  className="btn-ghost !px-2.5 !py-1 !text-xs"
                >
                  {copiedSheet ? '✓ Copied!' : '📋 Copy JSON-LD'}
                </button>
                <button
                  onClick={handleDownloadCapsule}
                  disabled={exportingCapsule}
                  className="btn-secondary !border-signal-ok/50 !text-signal-ok hover:!bg-signal-ok/10 !px-2.5 !py-1 !text-xs"
                >
                  {exportingCapsule ? 'Packaging...' : '📦 Export Standalone Capsule (.html)'}
                </button>
              </div>
            </header>

            <p className="mb-3 text-[11px] leading-relaxed text-graphite-faint">
              This sheet includes full accountant provenance, differential privacy budget guarantees,
              worst-case canary audit empirical lower bounds, and Ed25519 digital signature.
            </p>

            <pre className="thin-scroll display max-h-72 overflow-auto p-4 font-mono text-[11px] leading-relaxed text-bone">
{JSON.stringify(
  result.sheet || {
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

      <VerifierModal
        isOpen={verifierOpen}
        onClose={() => setVerifierOpen(false)}
        initialSheet={result?.sheet}
        sampleRecords={result?.sample_records}
      />

      <GuidedTourModal
        isOpen={tourOpen}
        onClose={() => setTourOpen(false)}
        onOpenVerifier={() => setVerifierOpen(true)}
      />
    </div>
  )
}
