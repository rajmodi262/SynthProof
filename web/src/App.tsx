import { useCallback, useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { api, runRelease } from '@/lib/api'
import { PrivacyChamber, type CloudLayer } from '@/components/PrivacyChamber'
import { KpiRow } from '@/components/KpiRow'
import { RightRail } from '@/components/RightRail'
import { LedgerChain } from '@/components/LedgerChain'
import { Controls } from '@/components/Controls'
import { DetailDrawer } from '@/components/DetailDrawer'
import { VerifierModal } from '@/components/VerifierModal'
import { GuidedTourModal } from '@/components/GuidedTourModal'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { FrontierStudio } from '@/components/FrontierStudio'
import type { RunStateContext } from '@/explainers/explainers'
import type {
  DatasetOption,
  LedgerState,
  Mechanism,
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
  seed: null,
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
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
    localStorage.setItem('sp-theme', dark ? 'dark' : 'light')
  }, [dark])

  return [dark, setDark] as const
}

type Preset = { id: string; label: string; eps: number; rows: number; refuses?: boolean }
const DEMO_PRESETS: Preset[] = [
  { id: '01_healthcare_patient_outcomes', label: '🏥 Clinical Outcomes', eps: 0.75, rows: 800 },
  { id: '02_financial_credit_risk', label: '💳 Credit Risk', eps: 1.0, rows: 1000 },
  { id: '03_telecom_customer_churn', label: '📱 Telecom Churn', eps: 1.5, rows: 800 },
  { id: '04_hr_employee_attrition', label: '⚡ HR Attrition (fastest)', eps: 1.0, rows: 600 },
  {
    id: '05_quick_demo_demographics',
    label: '🛑 Refusal Demo (400 rows)',
    eps: 0.5,
    rows: 400,
    refuses: true,
  },
]

export type LayoutMode = 'studio' | 'executive'

export default function App() {
  const [dark, setDark] = useTheme()

  const [datasets, setDatasets] = useState<DatasetOption[]>([])
  const [mechanisms, setMechanisms] = useState<Mechanism[]>([])
  const [ledger, setLedger] = useState<LedgerState | null>(null)
  const [offline, setOffline] = useState(false)

  const [config, setConfig] = useState<RunRequest>(DEFAULT_CONFIG)
  const [submitted, setSubmitted] = useState<RunRequest | null>(null)
  const [running, setRunning] = useState(false)
  const [stages, setStages] = useState<StageEvent[]>([])
  const [start, setStart] = useState<StartEvent | null>(null)
  const [result, setResult] = useState<RunResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [abort, setAbort] = useState<(() => void) | null>(null)

  // Layout mode & presentation state
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('studio')
  const [kpiExpanded, setKpiExpanded] = useState(true)

  // Modals & Drawers
  const [verifierOpen, setVerifierOpen] = useState(false)
  const [tourOpen, setTourOpen] = useState(false)
  const [exportingCapsule, setExportingCapsule] = useState(false)
  const [activeExplainer, setActiveExplainer] = useState<string | null>(null)
  const [selectedLedgerIndex, setSelectedLedgerIndex] = useState<number | undefined>(undefined)

  // 3D Chamber Layer toggles
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
        setLedger(l)
        const firstAvailable = m.mechanisms.find((x) => x.available)
        if (firstAvailable && !m.mechanisms.find((x) => x.key === DEFAULT_CONFIG.mechanism)?.available) {
          setConfig((c) => ({ ...c, mechanism: firstAvailable.key }))
        }
      })
      .catch(() => setOffline(true))
  }, [])

  // Budget spent so far
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

    const submittedConfig = config
    setSubmitted(submittedConfig)

    const cancel = runRelease(submittedConfig, {
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

  const [copiedSheet, setCopiedSheet] = useState(false)
  function copySheetJson() {
    if (!result?.sheet) return
    navigator.clipboard.writeText(JSON.stringify(result.sheet, null, 2))
    setCopiedSheet(true)
    setTimeout(() => setCopiedSheet(false), 2000)
  }

  // Explainer context for DetailDrawer
  const explainerContext: RunStateContext = {
    result,
    ledger,
    targetEps: (submitted ?? config).target_eps,
    selectedLedgerIndex,
  }

  function openExplainer(key: string, ledgerIdx?: number) {
    setSelectedLedgerIndex(ledgerIdx)
    setActiveExplainer(key)
  }

  return (
    <div className="min-h-screen bg-paper text-ink selection:bg-brass selection:text-white">
      {/* ------------------------------------------------------------- 1. Header (Sticky H 56px) */}
      <header className="sticky top-0 z-30 h-14 border-b border-line bg-paper/90 backdrop-blur-md">
        <div className="mx-auto flex h-full max-w-[1600px] items-center justify-between px-5">
          {/* Left: Product Lockup */}
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brass text-white shadow-brass">
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <div className="flex items-baseline gap-1.5">
                <span className="font-display text-xl font-normal tracking-tight text-ink">SynthProof</span>
                <span className="rounded bg-paper-2 px-1.5 py-0.2 font-mono text-[9px] font-semibold text-brass border border-line">
                  ATELIER
                </span>
              </div>
            </div>
          </div>

          {/* Center: View Mode Switcher (Executive vs Studio Focus) */}
          <div className="flex items-center rounded-lg border border-line bg-paper-2 p-0.5">
            <button
              type="button"
              onClick={() => setLayoutMode('studio')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 font-mono text-xs font-semibold transition-all ${
                layoutMode === 'studio'
                  ? 'bg-brass text-white shadow-xs'
                  : 'text-muted hover:text-ink'
              }`}
            >
              <span>🔬 3D Studio Focus</span>
            </button>
            <button
              type="button"
              onClick={() => setLayoutMode('executive')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 font-mono text-xs font-semibold transition-all ${
                layoutMode === 'executive'
                  ? 'bg-brass text-white shadow-xs'
                  : 'text-muted hover:text-ink'
              }`}
            >
              <span>⬡ Executive Grid</span>
            </button>
          </div>

          {/* Presets (Desktop) */}
          <div className="hidden 2xl:flex items-center gap-1">
            <span className="font-mono text-[10px] uppercase tracking-wider text-faint mr-1">
              Presets:
            </span>
            {DEMO_PRESETS.map((p) => {
              const active = config.dataset === p.id || config.dataset.includes(p.id.slice(3, 10))
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => selectPreset(p)}
                  disabled={running}
                  className={`rounded-full px-2 py-0.5 font-mono text-[10px] font-medium transition-all ${
                    active
                      ? p.refuses
                        ? 'bg-amber-600 text-white shadow-xs'
                        : 'bg-brass text-white shadow-xs'
                      : p.refuses
                      ? 'border border-amber-600/40 bg-amber-600/10 text-amber-800 dark:text-amber-300'
                      : 'border border-line bg-card text-muted hover:border-brass hover:text-ink'
                  }`}
                >
                  {p.label}
                </button>
              )
            })}
          </div>

          {/* Right: Actions and Theme Toggle */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setTourOpen(true)}
              className="btn-ghost !px-2.5 !py-1 !text-xs font-mono"
            >
              <span>🎯 Tour</span>
            </button>
            <button
              onClick={() => setVerifierOpen(true)}
              className="btn-brass !px-2.5 !py-1 !text-xs font-mono"
            >
              <span>🛡️ Verifier</span>
            </button>
            <button
              onClick={() => setDark(!dark)}
              className="flex h-7 w-7 items-center justify-center rounded-md border border-line text-muted hover:border-brass hover:text-ink"
              aria-label="Toggle theme"
            >
              {dark ? '☀️' : '🌙'}
            </button>
          </div>
        </div>
      </header>

      {offline && (
        <div className="border-b border-seal/40 bg-seal-bg px-6 py-2">
          <p className="mx-auto max-w-[1600px] font-mono text-xs text-seal">
            ⚠️ Cannot reach the API. Start it with <strong>python run_prototype.py</strong>
          </p>
        </div>
      )}

      {/* ------------------------------------------------------------- Main Content Area */}
      <main className="mx-auto max-w-[1600px] px-5 py-4 space-y-5">
        {/* 2. Collapsible KPI Row (Saves vertical space so 3D Chamber is 100% visible on screen) */}
        <section className="rounded-xl border border-line bg-card/60 p-3 shadow-e0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">
                Live Instrument Telemetry · Click any dial for mechanism KaTeX math
              </span>
            </div>
            <button
              type="button"
              onClick={() => setKpiExpanded(!kpiExpanded)}
              className="font-mono text-[10px] text-faint hover:text-brass flex items-center gap-1"
            >
              <span>{kpiExpanded ? '▲ Compact Dials' : '▼ Expand 7 Cards'}</span>
            </button>
          </div>

          <AnimatePresence initial={false}>
            {kpiExpanded ? (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-2.5"
              >
                <KpiRow
                  result={result}
                  ledger={ledger}
                  activeExplainer={activeExplainer}
                  onOpenExplainer={(key) => openExplainer(key)}
                />
              </motion.div>
            ) : (
              <div className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-line/50 pt-2 font-mono text-xs">
                <span className="text-muted">
                  ε Proved: <strong className="text-ink font-mono">{result?.measurements.proved_eps.toFixed(3) ?? '—'}</strong>
                </span>
                <span className="text-muted">
                  ε Audited: <strong className="text-ink font-mono">{result?.measurements.audited_eps.toFixed(3) ?? '—'}</strong>
                </span>
                <span className="text-muted">
                  Audit Reach: <strong className="text-brass font-mono">{result?.audit.ceiling.toFixed(2) ?? '—'}</strong>
                </span>
                <span className="text-muted">
                  Correlation MAE: <strong className="text-ink font-mono">{result?.measurements.correlation_error.toFixed(3) ?? '—'}</strong>
                </span>
                <span className="text-muted">
                  Rows: <strong className="text-ink font-mono">{result?.sheet?.num_rows ?? '—'}</strong>
                </span>
                <span className="text-muted">
                  Ledger: <strong className="text-ink font-mono">{ledger?.count ?? 0} blocks</strong>
                </span>
                <span className={ledger?.verified ? 'text-verify font-semibold' : 'text-seal font-semibold'}>
                  {ledger?.verified ? '✓ Chain Intact' : '✗ Chain Compromised'}
                </span>
              </div>
            )}
          </AnimatePresence>
        </section>

        {/* 3. Center Stage (3D Chamber) + Controls + Right Rail */}
        {layoutMode === 'studio' ? (
          /* Studio Focus Layout: 3D Chamber is Hero Centerpiece (620px tall on first screen!) */
          <div className="grid gap-5 xl:grid-cols-[280px_minmax(0,1fr)_320px]">
            {/* Left: Release Controls */}
            <div className="order-2 xl:order-1">
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
            </div>

            {/* Center Hero: 3D Privacy Chamber Stage (Takes Center Command!) */}
            <div className="order-1 xl:order-2 flex flex-col min-h-[580px] lg:min-h-[620px]">
              <ErrorBoundary fallbackTitle="3D Privacy Chamber Stage">
                <PrivacyChamber
                  cloud={result?.cloud ?? null}
                  layer={layer}
                  showCanaries={showCanaries}
                  showLinks={showLinks}
                  running={running}
                  currentStage={currentStage}
                  onLayerChange={setLayer}
                  onToggleCanaries={setShowCanaries}
                  onToggleLinks={setShowLinks}
                  onPointClick={(type) => {
                    if (type === 'synthetic') openExplainer('aim')
                    else if (type === 'canary') openExplainer('canary')
                    else openExplainer('boundary')
                  }}
                />
              </ErrorBoundary>
            </div>

            {/* Right: Rail Readouts */}
            <div className="order-3">
              <RightRail
                spent={spent}
                targetEps={(submitted ?? config).target_eps}
                currentStage={currentStage}
                result={result}
                stages={stages}
                running={running}
                onOpenExplainer={(key) => openExplainer(key)}
              />
            </div>
          </div>
        ) : (
          /* Executive Grid Layout */
          <div className="grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)] xl:grid-cols-[300px_minmax(0,1fr)_340px]">
            <div>
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
            </div>

            <div className="flex flex-col min-h-[520px]">
              <ErrorBoundary fallbackTitle="3D Privacy Chamber Stage">
                <PrivacyChamber
                  cloud={result?.cloud ?? null}
                  layer={layer}
                  showCanaries={showCanaries}
                  showLinks={showLinks}
                  running={running}
                  currentStage={currentStage}
                  onLayerChange={setLayer}
                  onToggleCanaries={setShowCanaries}
                  onToggleLinks={setShowLinks}
                  onPointClick={(type) => {
                    if (type === 'synthetic') openExplainer('aim')
                    else if (type === 'canary') openExplainer('canary')
                    else openExplainer('boundary')
                  }}
                />
              </ErrorBoundary>
            </div>

            <div className="lg:col-span-2 xl:col-span-1">
              <RightRail
                spent={spent}
                targetEps={(submitted ?? config).target_eps}
                currentStage={currentStage}
                result={result}
                stages={stages}
                running={running}
                onOpenExplainer={(key) => openExplainer(key)}
              />
            </div>
          </div>
        )}

        {/* Error notification */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="rounded-lg border border-seal bg-seal-bg p-4"
            >
              <div className="flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-wider text-seal">
                <span>⚠️ Run Failed</span>
              </div>
              <p className="mt-1 font-mono text-xs text-ink">{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 4. Full 12-Column Ledger Spine & Tamper Studio */}
        <section>
          <ErrorBoundary fallbackTitle="Cryptographic Privacy Ledger">
            <LedgerChain
              ledger={ledger}
              onRefresh={refreshLedger}
              onOpenBlockExplainer={(idx) => openExplainer('ledger', idx)}
            />
          </ErrorBoundary>
        </section>

        {/* 5. Frontier Curve & Correlation Topology (if available) */}
        {result && (
          <section>
            <ErrorBoundary fallbackTitle="Frontier Modeling Studio">
              <FrontierStudio
                measurements={result.measurements}
                result={result}
                targetEps={(submitted ?? config).target_eps}
              />
            </ErrorBoundary>
          </section>
        )}

        {/* 6. Privacy Data Sheet Export */}
        {result && start && (
          <section className="rounded-xl border border-line bg-card p-6 shadow-e0">
            <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-display text-2xl text-ink">Privacy Data Sheet</h3>
                <p className="mt-0.5 text-xs text-muted">
                  Cryptographic machine-checkable proof bundle emitted with this release.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className={`rounded-full border px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider ${
                    result.sheet?.signature
                      ? 'border-verify/40 bg-verify-bg text-verify'
                      : 'border-seal/40 bg-seal-bg text-seal'
                  }`}
                >
                  {result.sheet?.signature ? '✓ Signed (Ed25519)' : 'Unsigned'}
                </span>
                <button
                  onClick={() => setVerifierOpen(true)}
                  className="btn-brass !px-3 !py-1 !text-xs"
                >
                  🛡️ Inspect in Verifier
                </button>
                <button
                  onClick={copySheetJson}
                  className="btn-ghost !px-3 !py-1 !text-xs"
                >
                  {copiedSheet ? '✓ Copied!' : '📋 Copy JSON-LD'}
                </button>
                <button
                  onClick={handleDownloadCapsule}
                  disabled={exportingCapsule}
                  className="btn-verify !px-3 !py-1 !text-xs"
                >
                  {exportingCapsule ? 'Packaging...' : '📦 Export Standalone Capsule (.html)'}
                </button>
              </div>
            </header>

            <pre className="thin-scroll max-h-72 overflow-auto rounded-lg border border-line bg-paper-2 p-4 font-mono text-[11px] leading-relaxed text-ink shadow-inset">
              {JSON.stringify(result.sheet, null, 2)}
            </pre>
          </section>
        )}

        {/* Footer */}
        <footer className="border-t border-line py-5">
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted font-sans">
            <div>
              SynthProof — B.Tech Capstone · Runs locally · Every number computed.
            </div>
            <div className="font-mono text-[11px] text-faint">
              docs/design/PUBLIC_RELEASE_BOUNDARY.md
            </div>
          </div>
        </footer>
      </main>

      {/* Signature DetailDrawer */}
      <DetailDrawer
        explainerKey={activeExplainer}
        context={explainerContext}
        onClose={() => setActiveExplainer(null)}
      />

      {/* Modals */}
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
