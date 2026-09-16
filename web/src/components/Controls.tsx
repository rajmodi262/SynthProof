import { useRef, useState, type DragEvent } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import type { DatasetOption, Mechanism, RunRequest, UploadResult } from '@/types'

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

  const privacyTier =
    config.target_eps <= 1.0
      ? { label: 'High Privacy (Formal Guarantee)', tone: 'text-verify', border: 'border-verify/40', bg: 'bg-verify-bg/40' }
      : config.target_eps <= 4.0
      ? { label: 'Balanced Utility / Privacy', tone: 'text-brass', border: 'border-brass/40', bg: 'bg-paper-2' }
      : { label: 'Permissive / Low Noise', tone: 'text-seal', border: 'border-seal/40', bg: 'bg-seal-bg/40' }

  const currentDataset = datasets.find((d) => d.id === config.dataset)

  return (
    <div className="flex flex-col gap-4">
      {/* 1. Sensitive Source Table */}
      <section className="rounded-xl border border-line bg-card p-4.5 shadow-e0">
        <div className="flex items-center justify-between">
          <label className="font-mono text-[11px] font-semibold uppercase tracking-wider text-muted" htmlFor="dataset-select">
            Sensitive Source Table
          </label>
          <span className="font-mono text-[10px] text-faint">
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
          <p className="mt-2 text-[11px] leading-relaxed text-muted">
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
          className={`group mt-3 flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-3.5 text-center transition-all ${
            isDragging
              ? 'border-brass bg-paper-2 scale-[1.01]'
              : 'border-line hover:border-brass/70 hover:bg-paper-2/50'
          } ${running || uploading ? 'pointer-events-none opacity-50' : ''}`}
        >
          <div className="flex items-center gap-2 text-xs font-medium text-ink">
            <span className="text-base">📂</span>
            <span>{uploading ? 'Reading & Profiling CSV…' : 'Drop CSV here or click to browse'}</span>
          </div>
          <span className="mt-1 font-mono text-[10px] text-faint">
            Supports comma/semicolon delimited tabular files
          </span>
        </div>

        <AnimatePresence>
          {uploadError && (
            <motion.p
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-2 rounded-md bg-seal-bg border border-seal/30 p-2 font-mono text-[11px] text-seal"
            >
              ⚠️ {uploadError}
            </motion.p>
          )}

          {uploadNote?.warning && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-2 rounded-md border-l-2 border-brass bg-paper-2 p-2.5"
            >
              <p className="text-[11px] leading-snug text-ink">
                <strong className="font-medium text-brass">Schema inferred:</strong>{' '}
                {uploadNote.warning}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      {/* 2. Synthesis Mechanism */}
      <section className="rounded-xl border border-line bg-card p-4.5 shadow-e0">
        <div className="flex items-baseline justify-between">
          <span className="font-mono text-[11px] font-semibold uppercase tracking-wider text-muted">
            Synthesis Mechanism
          </span>
          <span className="font-mono text-[10px] text-brass font-medium">
            Formal DP
          </span>
        </div>

        <div className="mt-2.5 flex flex-col gap-2">
          {mechanisms.map((m) => {
            const active = config.mechanism === m.key
            return (
              <button
                key={m.key}
                type="button"
                onClick={() => m.available && patch({ mechanism: m.key })}
                disabled={!m.available || running}
                className={`group relative rounded-lg border p-3 text-left transition-all disabled:opacity-40 ${
                  active
                    ? 'border-brass bg-paper-2/60 shadow-xs ring-1 ring-brass'
                    : 'border-line bg-card hover:border-brass/60 hover:bg-paper-2/30'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-2 w-2 rounded-full transition-all ${
                        active ? 'bg-brass ring-2 ring-brass/30' : 'bg-line'
                      }`}
                    />
                    <span className="font-sans text-[13px] font-medium tracking-tight text-ink">
                      {m.label}
                    </span>
                  </div>
                  <span
                    className={`rounded px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wider ${
                      m.family === 'structured'
                        ? 'bg-brass/15 text-brass'
                        : 'bg-paper-2 text-faint'
                    }`}
                  >
                    {m.family}
                  </span>
                </div>
                <p className="mt-1.5 pl-4 text-[11px] leading-snug text-muted">
                  {m.available ? m.blurb : m.unavailable_reason}
                </p>
              </button>
            )
          })}
        </div>
      </section>

      {/* 3. Privacy Budget Target */}
      <section className="rounded-xl border border-line bg-card p-4.5 shadow-e0">
        <div className="flex items-baseline justify-between">
          <span className="font-mono text-[11px] font-semibold uppercase tracking-wider text-muted">
            Privacy Budget Target (ε)
          </span>
          <div className="flex items-baseline gap-1">
            <span className="tnum font-mono text-xl font-semibold text-brass">
              {config.target_eps.toFixed(2)}
            </span>
            <span className="font-mono text-xs text-faint">ε</span>
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
          className="mt-3.5 h-1.5 w-full cursor-pointer appearance-none rounded-full bg-paper-2 accent-[#8A5A2B]"
          aria-label="Target epsilon dial"
        />

        <div className="mt-2.5 flex gap-1.5">
          {EPS_GRID.map((e) => (
            <button
              key={e}
              type="button"
              onClick={() => patch({ target_eps: e })}
              disabled={running}
              className={`tnum flex-1 rounded-md border py-1.5 font-mono text-[11px] font-medium transition-all ${
                config.target_eps === e
                  ? 'border-brass bg-brass text-white shadow-xs'
                  : 'border-line text-muted hover:border-brass hover:text-ink bg-card'
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
          <span className="font-mono text-[10px] text-faint">δ = {config.delta}</span>
        </div>
      </section>

      {/* 4. Advanced Run Parameters */}
      <details className="rounded-xl border border-line bg-card p-4 shadow-e0">
        <summary className="font-mono text-[11px] font-semibold uppercase tracking-wider text-muted flex cursor-pointer select-none items-center justify-between list-none">
          <span>Run parameters</span>
          <span className="font-mono text-[10px] text-faint">⚙️ expand</span>
        </summary>
        <div className="mt-3 grid grid-cols-2 gap-3 border-t border-line/60 pt-3">
          <label className="block">
            <span className="font-mono text-[10px] text-faint">synthetic rows</span>
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
            <span className="font-mono text-[10px] text-faint">canary pairs</span>
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
            <span className="font-mono text-[10px] text-faint">random seed</span>
            <input
              type="number"
              className="field mt-1 !py-1.5 !text-xs font-mono"
              placeholder="secret (withheld)"
              value={config.seed ?? ''}
              disabled={running}
              onChange={(e) =>
                patch({ seed: e.target.value === '' ? null : Number(e.target.value) })
              }
            />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] text-faint">failure delta (δ)</span>
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
      </details>

      {/* 5. Primary Run Release Action Button */}
      <motion.button
        whileTap={{ scale: 0.985 }}
        className={
          running
            ? 'btn-seal w-full !py-3.5 !font-semibold text-sm shadow-xs'
            : 'btn-brass w-full !py-3.5 !font-semibold text-sm shadow-e1'
        }
        onClick={running ? onCancel : onRun}
      >
        {running ? (
          <span className="flex items-center gap-2">
            <span className="h-2 w-2 animate-ping rounded-full bg-seal" />
            <span>Abort Verification Pipeline</span>
          </span>
        ) : (
          <span className="flex items-center gap-2 font-medium">
            <span>⚡</span>
            <span>Run release & compute proof</span>
          </span>
        )}
      </motion.button>
    </div>
  )
}
