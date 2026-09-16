import { useEffect, useMemo, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import katex from 'katex'
import { EXPLAINERS, type RunStateContext } from '@/explainers/explainers'
import { DURATION, EASING } from '@/motion'

interface DetailDrawerProps {
  explainerKey: string | null
  context: RunStateContext
  onClose: () => void
}

export function DetailDrawer({ explainerKey, context, onClose }: DetailDrawerProps) {
  const explainer = explainerKey ? EXPLAINERS[explainerKey] : null
  const drawerRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  // Keyboard accessibility: Escape to close & focus trap
  useEffect(() => {
    if (!explainer) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    closeButtonRef.current?.focus()
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [explainer, onClose])

  const renderedFormula = useMemo(() => {
    if (!explainer?.katex) return ''
    try {
      return katex.renderToString(explainer.katex, {
        displayMode: true,
        throwOnError: false,
      })
    } catch {
      return explainer.katex
    }
  }, [explainer?.katex])

  const params = useMemo(() => {
    if (!explainer) return []
    return explainer.params(context)
  }, [explainer, context])

  return (
    <AnimatePresence>
      {explainer && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: DURATION.base, ease: EASING.standard }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-[#1A1712]/30 backdrop-blur-[2px]"
            aria-hidden="true"
          />

          {/* Drawer Tray */}
          <motion.aside
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="drawer-title"
            initial={{ x: '100%', opacity: 0.5 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ duration: DURATION.slow, ease: EASING.decel }}
            className="fixed bottom-0 right-0 top-16 z-50 flex w-full max-w-[440px] flex-col rounded-l-2xl border-l border-line bg-card shadow-e2"
          >
            {/* Header */}
            <div className="flex items-start justify-between border-b border-line px-6 py-5">
              <div className="pr-4">
                <span className="font-mono text-[11px] font-medium uppercase tracking-[0.14em] text-brass">
                  {explainer.eyebrow}
                </span>
                <h2 id="drawer-title" className="mt-1 font-display text-2xl leading-tight text-ink">
                  {explainer.title}
                </h2>
              </div>
              <button
                ref={closeButtonRef}
                onClick={onClose}
                aria-label="Close instrument detail drawer"
                className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-line text-muted transition-colors hover:border-brass hover:bg-paper-2 hover:text-ink focus:outline-none"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Scrollable Body */}
            <div className="thin-scroll flex-1 space-y-5 overflow-y-auto px-6 py-5 text-sm">
              {/* Layman register: In Plain Words */}
              <div className="relative rounded-r-md border-l-[3px] border-brass bg-paper-2/40 py-2.5 pl-4 pr-3">
                <p className="font-sans text-[14px] leading-relaxed text-ink">
                  {explainer.plain}
                </p>
              </div>

              {/* Mathematical formulation block */}
              <div>
                <span className="font-mono text-[10px] font-medium uppercase tracking-[0.12em] text-muted">
                  Formal Definition & Mechanism
                </span>
                <div className="thin-scroll mt-1.5 overflow-x-auto rounded-lg border border-line bg-paper-2 p-3.5 text-center shadow-inset">
                  <div
                    className="text-base text-ink"
                    dangerouslySetInnerHTML={{ __html: renderedFormula }}
                  />
                </div>
              </div>

              {/* Live parameter values */}
              <div>
                <span className="font-mono text-[10px] font-medium uppercase tracking-[0.12em] text-muted">
                  Live Run Parameters
                </span>
                <div className="mt-1.5 overflow-hidden rounded-lg border border-line bg-card">
                  <table className="w-full text-left font-mono text-[12px]">
                    <tbody>
                      {params.map((p, idx) => (
                        <tr
                          key={idx}
                          className={`border-b border-line/60 last:border-0 ${
                            idx % 2 === 0 ? 'bg-transparent' : 'bg-paper-2/30'
                          }`}
                        >
                          <td className="py-2 pl-3 pr-2 font-medium text-muted">
                            {p.label}
                          </td>
                          <td className="tnum py-2 pl-2 pr-3 text-right font-medium text-ink">
                            {p.value}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Footer: Verifiable source code pointer */}
            <div className="border-t border-line bg-paper-2/60 px-6 py-3.5">
              <div className="flex items-center gap-2 font-mono text-[11px] text-faint">
                <svg className="h-3.5 w-3.5 shrink-0 text-brass" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <span className="shrink-0 text-muted">Source:</span>
                <code className="truncate rounded bg-card/80 px-1 py-0.5 text-ink">
                  {explainer.source}
                </code>
              </div>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
