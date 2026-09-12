import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '@/lib/api'
import type { CertificateVerifyResult } from '@/types'

interface VerifierModalProps {
  isOpen: boolean
  onClose: () => void
  initialSheet?: Record<string, any> | null
  sampleRecords?: Record<string, any>[] | null
}

export function VerifierModal({
  isOpen,
  onClose,
  initialSheet,
  sampleRecords,
}: VerifierModalProps) {
  const [jsonText, setJsonText] = useState('')
  const [croissantText, setCroissantText] = useState('')
  const [activeTab, setActiveTab] = useState<'sheet' | 'croissant'>('sheet')
  const [pubKeyOverride, setPubKeyOverride] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<CertificateVerifyResult | null>(null)
  const [exporting, setExporting] = useState(false)
  const [exportSuccess, setExportSuccess] = useState(false)
  const [copiedCroissant, setCopiedCroissant] = useState(false)

  // Initialize with initialSheet if supplied
  useEffect(() => {
    if (initialSheet) {
      setJsonText(JSON.stringify(initialSheet, null, 2))
      if (initialSheet.public_key) {
        setPubKeyOverride(initialSheet.public_key)
      }
      handleVerify(initialSheet, initialSheet.public_key)
      api.exportCroissant(initialSheet)
        .then((c) => setCroissantText(JSON.stringify(c, null, 2)))
        .catch(() => undefined)
    }
  }, [initialSheet])

  async function handleVerify(sheetObj?: any, pk?: string) {
    setLoading(true)
    setResult(null)
    setExportSuccess(false)

    try {
      let parsed = sheetObj
      if (!parsed) {
        if (!jsonText.trim()) throw new Error('Please paste a Privacy Data Sheet or Croissant JSON-LD record.')
        parsed = JSON.parse(jsonText)
      }

      const res = await api.verifyCertificate(parsed, pk || pubKeyOverride || undefined)
      setResult(res)

      // Also generate Croissant 1.1 if not already loaded
      api.exportCroissant(parsed)
        .then((c) => setCroissantText(JSON.stringify(c, null, 2)))
        .catch(() => undefined)
    } catch (err: any) {
      setResult({
        signature_valid: false,
        lod_safe: false,
        lod_status: 'ERROR',
        error: err.message || 'Verification failed.',
        details: {},
      })
    } finally {
      setLoading(false)
    }
  }

  async function handleExportCapsule() {
    if (!jsonText.trim()) return
    setExporting(true)
    try {
      const sheet = JSON.parse(jsonText)
      const html = await api.exportCapsule(sheet, sampleRecords || [])
      
      const blob = new Blob([html], { type: 'text/html' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${sheet.dataset_name || 'synthproof'}_capsule.html`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      setExportSuccess(true)
      setTimeout(() => setExportSuccess(false), 3000)
    } catch (err: any) {
      alert(`Capsule export failed: ${err.message}`)
    } finally {
      setExporting(false)
    }
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = async (event) => {
      const text = event.target?.result as string

      // If user uploaded a standalone .html capsule!
      if (file.name.endsWith('.html')) {
        setLoading(true)
        try {
          const capReport = await api.verifyCapsule(text)
          if (capReport.verified) {
            setResult({
              signature_valid: true,
              lod_safe: capReport.lod_safe,
              lod_status: capReport.lod_status,
              error: null,
              details: {
                proved_eps: capReport.proved_eps,
                audited_eps: capReport.audited_eps,
                audit_ceiling: capReport.audit_ceiling,
                mechanism: capReport.mechanism,
                dataset_name: capReport.dataset_name,
                num_rows: capReport.num_rows,
                ledger_hash: capReport.ledger_hash,
              },
            })
            if (capReport.public_key) setPubKeyOverride(capReport.public_key)
          } else {
            setResult({
              signature_valid: false,
              lod_safe: false,
              lod_status: 'ERROR',
              error: capReport.error || 'Capsule signature invalid',
              details: {},
            })
          }
        } catch (err: any) {
          alert(`Capsule parse error: ${err.message}`)
        } finally {
          setLoading(false)
        }
        return
      }

      // Otherwise JSON/JSON-LD
      setJsonText(text)
      try {
        const parsed = JSON.parse(text)
        if (parsed.public_key) setPubKeyOverride(parsed.public_key)
        handleVerify(parsed, parsed.public_key)
      } catch {
        // Let user inspect and verify manually
      }
    }
    reader.readAsText(file)
  }

  function copyCroissant() {
    if (!croissantText) return
    navigator.clipboard.writeText(croissantText)
    setCopiedCroissant(true)
    setTimeout(() => setCopiedCroissant(false), 2000)
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="relative flex max-h-[90vh] w-full max-w-4xl flex-col rounded-lg border border-bone-edge bg-[#FAF9F6] shadow-2xl dark:border-stage-line dark:bg-stage-deep"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-bone-edge p-5 dark:border-stage-line">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-proved/10 font-mono text-xs text-proved dark:bg-proved/20 dark:text-proved-lift">
                🛡️
              </span>
              <h2 className="font-display text-xl tracking-tight">Zero-Trust Certificate Verifier</h2>
            </div>
            <p className="mt-1 text-xs text-graphite-faint">
              Independent Ed25519 cryptographic signature, Croissant 1.1 metadata & MIQE 2.0 LoD validator.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-graphite-faint hover:bg-bone-edge/50 hover:text-graphite dark:hover:bg-stage-line dark:hover:text-bone"
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div className="thin-scroll flex-1 overflow-y-auto p-6 space-y-6">
          {/* Controls Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-bone-edge bg-bone/30 p-3 dark:border-stage-line dark:bg-stage/40">
            <div className="flex items-center gap-2">
              <label className="btn-secondary cursor-pointer !px-3 !py-1.5 !text-xs">
                📁 Upload Sheet / Capsule (.html, .json)
                <input
                  type="file"
                  accept=".json,.jsonld,.html"
                  className="hidden"
                  onChange={handleFileUpload}
                />
              </label>
              {initialSheet && (
                <button
                  className="btn-ghost !px-3 !py-1.5 !text-xs"
                  onClick={() => {
                    setJsonText(JSON.stringify(initialSheet, null, 2))
                    if (initialSheet.public_key) setPubKeyOverride(initialSheet.public_key)
                    handleVerify(initialSheet, initialSheet.public_key)
                  }}
                >
                  Load Current Run Sheet
                </button>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                className="btn-primary !px-4 !py-1.5 !text-xs"
                onClick={() => handleVerify()}
                disabled={loading}
              >
                {loading ? 'Verifying...' : '⚡ Verify Certificate'}
              </button>
              <button
                className="btn-secondary !px-4 !py-1.5 !text-xs !border-signal-ok/50 !text-signal-ok hover:!bg-signal-ok/10"
                onClick={handleExportCapsule}
                disabled={exporting || !jsonText.trim()}
              >
                {exporting ? 'Packaging...' : exportSuccess ? '✓ Capsule Exported!' : '📦 Export Standalone Capsule'}
              </button>
            </div>
          </div>

          {/* Verification Results Panel */}
          <AnimatePresence>
            {result && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                className="grid grid-cols-1 gap-4 md:grid-cols-2"
              >
                {/* Cryptographic Proof Box */}
                <div
                  className={`rounded-md border p-4 ${
                    result.signature_valid
                      ? 'border-signal-ok/50 bg-signal-ok/[0.04]'
                      : 'border-signal-bad/50 bg-signal-bad/[0.04]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold uppercase tracking-wider text-graphite dark:text-bone">
                      Ed25519 Signature
                    </span>
                    <span
                      className={`rounded-full px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider ${
                        result.signature_valid
                          ? 'bg-signal-ok/20 text-signal-ok'
                          : 'bg-signal-bad/20 text-signal-bad'
                      }`}
                    >
                      {result.signature_valid ? '✓ Authenticated' : '✗ Invalid / Forged'}
                    </span>
                  </div>

                  <p className="mt-2 text-xs text-graphite-soft dark:text-bone/80">
                    {result.signature_valid
                      ? 'Mathematical proof that this sheet has not been tampered with and was signed by the registered authority.'
                      : result.error || 'The cryptographic signature does not verify against this payload.'}
                  </p>

                  <div className="mt-3 space-y-1 font-mono text-[11px] text-graphite-faint">
                    <div>
                      Dataset:{' '}
                      <span className="text-graphite dark:text-bone">
                        {result.details.dataset_name || 'N/A'}
                      </span>{' '}
                      ({result.details.num_rows || 0} rows)
                    </div>
                    <div>
                      Mechanism:{' '}
                      <span className="text-graphite dark:text-bone">
                        {result.details.mechanism || 'N/A'}
                      </span>
                    </div>
                    <div className="truncate">
                      Ledger Head:{' '}
                      <span className="text-graphite dark:text-bone">
                        {result.details.ledger_hash || 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* MIQE 2.0 Operating Range Box */}
                <div
                  className={`rounded-md border p-4 ${
                    result.lod_safe
                      ? 'border-proved/50 bg-proved/[0.04]'
                      : 'border-signal-warn/50 bg-signal-warn/[0.04]'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-semibold uppercase tracking-wider text-graphite dark:text-bone">
                      MIQE 2.0 Operating Range
                    </span>
                    <span
                      className={`rounded-full px-2.5 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider ${
                        result.lod_safe
                          ? 'bg-proved/20 text-proved dark:text-proved-lift'
                          : 'bg-signal-warn/20 text-signal-warn'
                      }`}
                    >
                      {result.lod_status}
                    </span>
                  </div>

                  <p className="mt-2 text-xs text-graphite-soft dark:text-bone/80">
                    {result.lod_safe
                      ? 'Audited epsilon sits strictly below the statistical ceiling. The empirical test operated inside its valid detection zone.'
                      : 'Audited epsilon reached or exceeded the maximum detectable ceiling m.'}
                  </p>

                  <div className="mt-3 grid grid-cols-3 gap-2 text-center font-mono text-xs">
                    <div className="rounded bg-bone-edge/30 p-2 dark:bg-stage-line/30">
                      <div className="text-[10px] text-graphite-faint">Proved ε</div>
                      <div className="mt-0.5 font-bold text-proved dark:text-proved-lift">
                        {result.details.proved_eps?.toFixed(3) ?? 'N/A'}
                      </div>
                    </div>
                    <div className="rounded bg-bone-edge/30 p-2 dark:bg-stage-line/30">
                      <div className="text-[10px] text-graphite-faint">Audited ε̂</div>
                      <div className="mt-0.5 font-bold text-audited dark:text-audited-lift">
                        {result.details.audited_eps?.toFixed(3) ?? 'N/A'}
                      </div>
                    </div>
                    <div className="rounded bg-bone-edge/30 p-2 dark:bg-stage-line/30">
                      <div className="text-[10px] text-graphite-faint">Ceiling (m)</div>
                      <div className="mt-0.5 font-bold text-graphite dark:text-bone">
                        {result.details.audit_ceiling?.toFixed(3) ?? 'N/A'}
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Tab Switcher */}
          <div className="flex items-center justify-between border-b border-bone-edge pb-2 dark:border-stage-line">
            <div className="flex gap-2">
              <button
                onClick={() => setActiveTab('sheet')}
                className={`px-3 py-1 font-mono text-xs font-semibold uppercase tracking-wider transition-colors ${
                  activeTab === 'sheet'
                    ? 'border-b-2 border-proved text-proved dark:text-proved-lift'
                    : 'text-graphite-faint hover:text-graphite dark:hover:text-bone'
                }`}
              >
                Privacy Data Sheet
              </button>
              <button
                onClick={() => setActiveTab('croissant')}
                className={`px-3 py-1 font-mono text-xs font-semibold uppercase tracking-wider transition-colors ${
                  activeTab === 'croissant'
                    ? 'border-b-2 border-proved text-proved dark:text-proved-lift'
                    : 'text-graphite-faint hover:text-graphite dark:hover:text-bone'
                }`}
              >
                MLCommons Croissant 1.1 JSON-LD
              </button>
            </div>

            {activeTab === 'croissant' && croissantText && (
              <button
                onClick={copyCroissant}
                className="btn-ghost !px-2.5 !py-1 !text-2xs"
              >
                {copiedCroissant ? '✓ Copied!' : '📋 Copy JSON-LD'}
              </button>
            )}
          </div>

          {/* Content View */}
          {activeTab === 'sheet' ? (
            <div className="space-y-2">
              <textarea
                rows={12}
                value={jsonText}
                onChange={(e) => setJsonText(e.target.value)}
                placeholder='Paste PrivacyDataSheet JSON here, or click "Load Current Run Sheet"...'
                className="w-full rounded-md border border-bone-edge bg-bone-deep/50 p-3 font-mono text-xs leading-relaxed text-graphite focus:border-proved focus:outline-none dark:border-stage-line dark:bg-stage-deep dark:text-bone"
              />
            </div>
          ) : (
            <div className="space-y-2">
              <pre className="thin-scroll max-h-72 overflow-auto rounded-md border border-bone-edge bg-bone-deep/50 p-3 font-mono text-xs leading-relaxed text-graphite dark:border-stage-line dark:bg-stage-deep dark:text-bone">
                {croissantText || 'Run a release or verify a Privacy Data Sheet to view Croissant 1.1 JSON-LD specification.'}
              </pre>
            </div>
          )}

          {/* Optional Public Key Override */}
          <div className="space-y-1">
            <label className="font-mono text-xs text-graphite-faint">
              Expected Public Key (Hex 64-char) — Leave blank to verify against sheet's embedded key:
            </label>
            <input
              type="text"
              value={pubKeyOverride}
              onChange={(e) => setPubKeyOverride(e.target.value)}
              placeholder="e.g. 7f9a8b1c..."
              className="w-full rounded-md border border-bone-edge bg-bone-deep/50 px-3 py-1.5 font-mono text-xs text-graphite focus:border-proved focus:outline-none dark:border-stage-line dark:bg-stage-deep dark:text-bone"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-bone-edge p-4 dark:border-stage-line">
          <span className="font-mono text-[11px] text-graphite-faint">
            🔒 Fully offline-capable WebCrypto verification. No secret data ever leaves your browser.
          </span>
          <button className="btn-ghost !px-4 !py-1.5 !text-xs" onClick={onClose}>
            Close
          </button>
        </div>
      </motion.div>
    </div>
  )
}
