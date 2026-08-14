import { useRef, useState } from 'react'
import { motion } from 'framer-motion'
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

  return (
    <div className="flex flex-col gap-4">
      {/* ---------------------------------------------------------------- data */}
      <section className="panel p-4">
        {/* A bare <span> is not a label, so the select had no accessible name. */}
        <label className="label" htmlFor="dataset-select">
          Sensitive table
        </label>

        <select
          id="dataset-select"
          className="field mt-2"
          value={config.dataset}
          onChange={(e) => patch({ dataset: e.target.value })}
          disabled={running}
        >
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>
              {d.label}
              {d.rows ? ` · ${d.rows.toLocaleString()} rows` : ''}
            </option>
          ))}
        </select>

        {datasets.find((d) => d.id === config.dataset)?.note && (
          <p className="mt-2 text-[11px] leading-snug text-graphite-faint">
            {datasets.find((d) => d.id === config.dataset)?.note}
          </p>
        )}

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
        <button
          className="btn-ghost mt-3 w-full !py-2 !text-xs"
          onClick={() => fileRef.current?.click()}
          disabled={running || uploading}
        >
          {uploading ? 'Reading CSV…' : 'Upload your own CSV'}
        </button>

        {uploadError && (
          <p className="mt-2 text-[11px] leading-snug text-signal-bad">{uploadError}</p>
        )}

        {uploadNote?.warning && (
          <div className="mt-2 rounded-sm border-l-2 border-signal-warn bg-signal-warn/[0.07] p-2.5">
            <p className="text-[11px] leading-snug text-graphite-soft dark:text-bone">
              <strong className="font-medium">Schema inferred from your data.</strong>{' '}
              {uploadNote.warning}
            </p>
          </div>
        )}
      </section>

      {/* ---------------------------------------------------------------- mechanism */}
      <section className="panel p-4">
        <span className="label">Mechanism</span>
        <div className="mt-2 flex flex-col gap-1.5">
          {mechanisms.map((m) => {
            const active = config.mechanism === m.key
            return (
              <button
                key={m.key}
                onClick={() => m.available && patch({ mechanism: m.key })}
                disabled={!m.available || running}
                className={`rounded-sm border p-2.5 text-left transition-colors disabled:opacity-40 ${
                  active
                    ? 'border-proved bg-proved/[0.07]'
                    : 'border-bone-edge hover:border-graphite-faint dark:border-stage-line'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-sans text-[13px] font-medium">{m.label}</span>
                  <span
                    className={`rounded-[2px] px-1 font-mono text-[9px] uppercase tracking-[0.1em] ${
                      m.family === 'structured'
                        ? 'bg-proved/15 text-proved dark:text-proved-lift'
                        : 'bg-graphite-faint/15 text-graphite-faint'
                    }`}
                  >
                    {m.family}
                  </span>
                </div>
                <p className="mt-1 text-[11px] leading-snug text-graphite-faint">
                  {m.available ? m.blurb : m.unavailable_reason}
                </p>
              </button>
            )
          })}
        </div>
      </section>

      {/* ---------------------------------------------------------------- budget */}
      <section className="panel p-4">
        <div className="flex items-baseline justify-between">
          <span className="label">Privacy budget ε</span>
          <span className="tnum font-mono text-lg text-proved dark:text-proved-lift">
            {config.target_eps.toFixed(2)}
          </span>
        </div>

        <input
          type="range"
          min={0.25}
          max={8}
          step={0.25}
          value={config.target_eps}
          disabled={running}
          onChange={(e) => patch({ target_eps: Number(e.target.value) })}
          className="mt-3 w-full accent-[#4B46C4]"
          aria-label="Target epsilon"
        />

        <div className="mt-2 flex gap-1">
          {EPS_GRID.map((e) => (
            <button
              key={e}
              onClick={() => patch({ target_eps: e })}
              disabled={running}
              className={`tnum flex-1 rounded-sm border py-1 font-mono text-[11px] transition-colors ${
                config.target_eps === e
                  ? 'border-proved bg-proved text-white'
                  : 'border-bone-edge text-graphite-faint hover:border-graphite-faint dark:border-stage-line'
              }`}
            >
              {e}
            </button>
          ))}
        </div>

        <p className="mt-2.5 text-[11px] leading-snug text-graphite-faint">
          Lower ε means more noise and stronger privacy. Calibration inverts the composition
          theorem, so the ε you ask for is the ε you are charged — never more.
        </p>
      </section>

      {/* ---------------------------------------------------------------- advanced */}
      <details className="panel p-4">
        <summary className="label cursor-pointer select-none list-none">
          Run parameters ▾
        </summary>
        <div className="mt-3 grid grid-cols-2 gap-3">
          <label className="block">
            <span className="font-mono text-[10px] text-graphite-faint">rows</span>
            <input
              type="number"
              className="field mt-1 !py-1.5 !text-xs"
              min={100}
              max={20000}
              step={100}
              value={config.rows}
              disabled={running}
              onChange={(e) => patch({ rows: Number(e.target.value) })}
            />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] text-graphite-faint">canaries</span>
            <input
              type="number"
              className="field mt-1 !py-1.5 !text-xs"
              min={1}
              max={500}
              value={config.num_canaries}
              disabled={running}
              onChange={(e) => patch({ num_canaries: Number(e.target.value) })}
            />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] text-graphite-faint">seed</span>
            <input
              type="number"
              className="field mt-1 !py-1.5 !text-xs"
              value={config.seed}
              disabled={running}
              onChange={(e) => patch({ seed: Number(e.target.value) })}
            />
          </label>
          <label className="block">
            <span className="font-mono text-[10px] text-graphite-faint">delta</span>
            <input
              type="number"
              className="field mt-1 !py-1.5 !text-xs"
              step="1e-6"
              value={config.delta}
              disabled={running}
              onChange={(e) => patch({ delta: Number(e.target.value) })}
            />
          </label>
        </div>
        <p className="mt-2.5 text-[11px] leading-snug text-graphite-faint">
          More canaries raise audit power but dilute the table&rsquo;s real structure — a known
          confound in this harness. Keep it fixed when comparing mechanisms.
        </p>
      </details>

      {/* ---------------------------------------------------------------- run */}
      <motion.button
        whileTap={{ scale: 0.985 }}
        className={running ? 'btn-ghost w-full !py-3' : 'btn-primary w-full !py-3'}
        onClick={running ? onCancel : onRun}
      >
        {running ? 'Stop watching' : 'Synthesise & audit'}
      </motion.button>
    </div>
  )
}
