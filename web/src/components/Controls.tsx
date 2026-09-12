import { useRef, useState, type DragEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import type { DatasetOption, Mechanism, RunRequest, UploadResult } from '@/types'

/** ε values the sweep grid uses, so the console and the experiments stay on one scale. */
const EPS_GRID = [0.5, 1, 2, 4, 8]

export function Controls({
  datasets,
  mechanisms,
  config,
  setConfig,
  running,
  onRun,
  onCancel,
  onUploaded,
}: {
  datasets: DatasetOption[]
  mechanisms: Mechanism[]
  config: RunRequest
  setConfig: (c: RunRequest) => void
  running: boolean
  onRun: () => void
  onCancel: () => void
  onUploaded: (r: UploadResult) => void
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadNote, setUploadNote] = useState<UploadResult | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  const patch = (p: Partial<RunRequest>) => setConfig({ ...config, ...p })

  async function handleFile(file: File) {
    setUploading(true)
    setUploadError(null)
    try {
      const res = await api.upload(file)
      setUploadNote(res)
      onUploaded(res)
      patch({ dataset: res.id })
    } catch (err) {
      setUploadError((err as Error).message)
    } finally {
      setUploading(false)
    }
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (!running) setIsDragging(true)
  }

  function handleDragLeave(e: DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    if (running) return
    const file = e.dataTransfer.files?.[0]
    if (file && (file.name.endsWith('.csv') || file.type.includes('csv'))) {
      handleFile(file)
    } else if (file) {
      setUploadError('Please drop a valid .csv file.')
    }
  }

  // Determine privacy rating label based on target epsilon
  const privacyTier =
    config.target_eps <= 1.0
      ? { label: 'High Privacy (Formal Guarantee)', tone: 'text-signal-ok', border: 'border-signal-ok/40', bg: 'bg-signal-ok/[0.08]' }
      : config.target_eps <= 4.0
        ? { label: 'Balanced Utility / Privacy', tone: 'text-proved dark:text-proved-lift', border: 'border-proved/40', bg: 'bg-proved/[0.08]' }
        : { label: 'Permissive / Low Noise', tone: 'text-signal-warn', border: 'border-signal-warn/40', bg: 'bg-signal-warn/[0.08]' }

  const currentDataset = datasets.find((d) => d.id === config.dataset)

  return (
    <div className="flex flex-col gap-4">
      {/* ---------------------------------------------------------------- data */}
      <section className="glass-panel p-4.5">
        <div className="flex items-center justify-between">
          <label className="label" htmlFor="dataset-select">
            Sensitive Source Table
          </label>
          <span className="font-mono text-[10px] text-graphite-faint">
            {datasets.length} available
          </span>
        </div>

        <select
          id="dataset-select"
          className="field mt-2.5 cursor-pointer font-medium"
          value={config.dataset}
          onChange={(e) => patch({ dataset: e.target.value })}
          disabled={running}
        >
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>
              {d.label}
              {d.rows ? ` (${d.rows.toLocaleString()} rows)` : ''}
            </option>
          ))}
        </select>

        {currentDataset?.note && (
          <p className="mt-2 text-[11px] leading-relaxed text-graphite-faint">
            {currentDataset.note}
          </p>
        )}

        {/* Drag & Drop Upload Zone */}
        <input
          ref={fileRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) handleFile(f)
            e.target.value = ''
          }}
        />

        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => !running && !uploading && fileRef.current?.click()}
          className={`group mt-3 flex cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed p-3.5 text-center transition-all ${
            isDragging
              ? 'border-proved bg-proved/10 scale-[1.01]'
              : 'border-bone-edge hover:border-graphite-faint/60 hover:bg-bone-deep/40 dark:border-stage-line dark:hover:border-stage-line/90 dark:hover:bg-stage-deep/40'
          } ${running || uploading ? 'pointer-events-none opacity-50' : ''}`}
        >
          <div className="flex items-center gap-2 text-xs font-medium text-graphite-soft dark:text-bone">
            <span className="text-base">📂</span>
            <span>{uploading ? 'Reading & Profiling CSV…' : 'Drop CSV here or click to browse'}</span>
          </div>
          <span className="mt-1 font-mono text-[10px] text-graphite-faint">
            Supports comma/semicolon delimited tabular files
          </span>
        </div>

        <AnimatePresence>
          {uploadError && (
            <motion.p
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-2 rounded-sm bg-signal-bad/10 p-2 font-mono text-[11px] text-signal-bad"
            >
              ⚠️ {uploadError}
            </motion.p>
          )}

          {uploadNote?.warning && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-2 rounded-sm border-l-2 border-signal-warn bg-signal-warn/[0.08] p-2.5"
            >
              <p className="text-[11px] leading-snug text-graphite-soft dark:text-bone">
                <strong className="font-medium text-signal-warn">Schema inferred:</strong>{' '}
                {uploadNote.warning}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* ---------------------------------------------------------------- mechanism */}
      <section className="glass-panel p-4.5">
        <div className="flex items-baseline justify-between">
          <span className="label">Synthesis Mechanism</span>
          <span className="font-mono text-[10px] text-proved dark:text-proved-lift">
            Formal DP
          </span>
        </div>

        <div className="mt-2.5 flex flex-col gap-2">
          {mechanisms.map((m) => {
            const active = config.mechanism === m.key
            return (
              <button
                key={m.key}
                onClick={() => m.available && patch({ mechanism: m.key })}
                disabled={!m.available || running}
                className={`group relative rounded-md border p-3 text-left transition-all disabled:opacity-40 ${
                  active
                    ? 'border-proved bg-proved/[0.09] shadow-sm shadow-proved/10'
                    : 'border-bone-edge hover:border-graphite-faint/60 hover:bg-bone-deep/30 dark:border-stage-line dark:hover:border-stage-line/90 dark:hover:bg-stage-deep/30'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-2 w-2 rounded-full transition-all ${
                        active ? 'bg-proved ring-2 ring-proved/30' : 'bg-graphite-faint/40'
                      }`}
                    />
                    <span className="font-sans text-[13px] font-medium tracking-tight text-graphite dark:text-bone">
                      {m.label}
                    </span>
                  </div>
                  <span
                    className={`rounded-[3px] px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-[0.08em] ${
                      m.family === 'structured'
                        ? 'bg-proved/15 text-proved dark:text-proved-lift'
                        : 'bg-graphite-faint/15 text-graphite-faint'
                    }`}
                  >
                    {m.family}
                  </span>
                </div>
                <p className="mt-1.5 pl-4 text-[11px] leading-snug text-graphite-faint group-hover:text-graphite-soft dark:group-hover:text-bone/80">
                  {m.available ? m.blurb : m.unavailable_reason}
                </p>
              </button>
            )
          })}
        </div>
      </section>

      {/* ---------------------------------------------------------------- budget */}
      <section className="glass-panel p-4.5">
        <div className="flex items-baseline justify-between">
          <span className="label">Privacy Budget Target (ε)</span>
          <div className="flex items-baseline gap-1">
            <span className="tnum font-mono text-xl font-semibold text-proved dark:text-proved-lift">
              {config.target_eps.toFixed(2)}
            </span>
            <span className="font-mono text-xs text-graphite-faint">ε</span>
          </div>
        </div>

        <input
          type="range"
          min={0.25}
          max={8}
          step={0.25}
          value={config.target_eps}
          disabled={running}
          onChange={(e) => patch({ target_eps: Number(e.target.value) })}
          className="mt-3.5 h-1.5 w-full cursor-pointer appearance-none rounded-full bg-bone-deep accent-proved dark:bg-stage-line"
          aria-label="Target epsilon"
        />

        <div className="mt-2.5 flex gap-1.5">
          {EPS_GRID.map((e) => (
            <button
              key={e}
              onClick={() => patch({ target_eps: e })}
              disabled={running}
              className={`tnum flex-1 rounded-md border py-1.5 font-mono text-[11px] font-medium transition-all ${
                config.target_eps === e
                  ? 'border-proved bg-proved text-white shadow-sm shadow-proved/30'
                  : 'border-bone-edge text-graphite-faint hover:border-graphite-faint hover:text-graphite dark:border-stage-line dark:hover:text-bone'
              }`}
            >
              {e}
            </button>
          ))}
        </div>

        {/* Dynamic Privacy Tier Indicator */}
        <div className={`mt-3 flex items-center justify-between rounded-md border px-2.5 py-1.5 ${privacyTier.border} ${privacyTier.bg}`}>
          <span className={`font-mono text-[10px] font-medium ${privacyTier.tone}`}>
            {privacyTier.label}
          </span>
          <span className="font-mono text-[10px] text-graphite-faint">δ = {config.delta}</span>
        </div>

        <p className="mt-2.5 text-[11px] leading-relaxed text-graphite-faint">
          Lower ε injects stronger mathematical calibrated noise. SynthProof uses RDP/PLD accountant
          inversion so actual charge never drifts above target.
        </p>
      </section>

      {/* ---------------------------------------------------------------- advanced */}
      <details className="glass-panel p-4">
        <summary className="label flex cursor-pointer select-none items-center justify-between list-none">
          <span>Run parameters</span>
          <span className="font-mono text-[10px] text-graphite-faint">⚙️ expand</span>
        </summary>
        <div className="mt-3 grid grid-cols-2 gap-3 border-t border-bone-edge/50 pt-3 dark:border-stage-line/50">
          <label className="block">
            <span className="font-mono text-[10px] text-graphite-faint">synthetic rows</span>
            <input
              type="number"
              className="field mt-1 !py-1.5 !text-xs font-mono"
              min={100}
              max={20000}
              step={100}
              value={config.rows}
              disabled={running}
              onChange={(e) => patch({ rows: Number(e.target.value) })}
            />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] text-graphite-faint">canary pairs</span>
            <input
              type="number"
              className="field mt-1 !py-1.5 !text-xs font-mono"
              min={1}
              max={500}
              value={config.num_canaries}
              disabled={running}
              onChange={(e) => patch({ num_canaries: Number(e.target.value) })}
            />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] text-graphite-faint">random seed</span>
            <input
              type="number"
              className="field mt-1 !py-1.5 !text-xs font-mono"
              value={config.seed}
              disabled={running}
              onChange={(e) => patch({ seed: Number(e.target.value) })}
            />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] text-graphite-faint">failure delta (δ)</span>
            <input
              type="number"
              className="field mt-1 !py-1.5 !text-xs font-mono"
              step="1e-6"
              value={config.delta}
              disabled={running}
              onChange={(e) => patch({ delta: Number(e.target.value) })}
            />
          </label>
        </div>
        <p className="mt-2.5 text-[10px] leading-snug text-graphite-faint">
          Canaries raise audit statistical power ($m \propto \ln(B/z_\alpha)$). Keep fixed when comparing mechanism architectures.
        </p>
      </details>

      {/* ---------------------------------------------------------------- run */}
      <motion.button
        whileTap={{ scale: 0.985 }}
        className={
          running
            ? 'btn-ghost w-full !py-3.5 !font-semibold !text-signal-bad border-signal-bad/40 hover:bg-signal-bad/10'
            : 'btn-primary w-full !py-3.5 !font-semibold text-sm shadow-lg glow-proved'
        }
        onClick={running ? onCancel : onRun}
      >
        {running ? (
          <span className="flex items-center gap-2">
            <span className="h-2 w-2 animate-ping rounded-full bg-signal-bad" />
            <span>Abort Verification Pipeline</span>
          </span>
        ) : (
          <span className="flex items-center gap-2">
            <span>⚡</span>
            <span>Synthesise & Audit Release</span>
          </span>
        )}
      </motion.button>
    </div>
  )
}

