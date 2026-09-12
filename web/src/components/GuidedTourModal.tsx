import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface GuidedTourModalProps {
  isOpen: boolean
  onClose: () => void
  onOpenVerifier: () => void
  onSelectMechanism?: (mech: string) => void
}

const TOUR_STEPS = [
  {
    step: 1,
    badge: 'STAGE 1: GENERATION ENGINE',
    title: 'Differential Privacy Synthesis & Formal Calibration',
    icon: '⚡',
    description:
      'SynthProof integrates 7 state-of-the-art synthetic data mechanisms, including AIM, Pairwise Marginals, Fixed Workload, and DP-VAE. Each mechanism uses exact numerical accountant composition (PLD / PRV / RDP) ensuring provable (ε, δ)-differential privacy bounds with zero heuristic budget drift.',
    highlights: [
      'Formal Privacy Calibration: Calibrates Gaussian and Laplace noise scale σ to target ε.',
      'Workload Optimization: Selects high-signal marginal queries under bounded sensitivity.',
      'Negative Control Support: Includes leaky baseline to validate attack sensitivity.',
    ],
    callToAction: 'Configure parameters in the left-hand panel and click "Run Release".',
  },
  {
    step: 2,
    badge: 'STAGE 2: VISUAL FIDELITY',
    title: '3D PCA Record Cloud & Structural Topologies',
    icon: '🌐',
    description:
      'The central 3D WebGL viewer visualizes real records (purple), synthetic records (amber), and planted canaries (crimson) projected into a shared dimensional space. Unlike static charts, this reveals whether noise preserves multi-attribute correlations or collapses them into Gaussian artifacts.',
    highlights: [
      'Interactive Orbit Controls: Pan, zoom, and rotate the shared coordinate manifold.',
      'Canary Connectors: Red vectors show distance to nearest release record, representing individual recoverability.',
      'Layer Toggling: Switch between Real, Synthetic, and Combined views in real time.',
    ],
    callToAction: 'Rotate the 3D stage and observe how well synthetic clusters match real records.',
  },
  {
    step: 3,
    badge: 'STAGE 3: CANARY AUDIT & MIQE 2.0',
    title: 'Worst-Case Canary Audit & Limit of Detection (LoD)',
    icon: '🎯',
    description:
      'A primary scientific breakthrough of SynthProof: canary auditors suffer from statistical ceilings m ≈ ln(B/z_α). When empirical audit results fall below the detector ceiling, reporting ε̂ = 0 is uninformative, not evidence of zero leakage. SynthProof enforces MIQE 2.0 compliance by always reporting the operating range bounds.',
    highlights: [
      'Clopper-Pearson Confidence: Rigorous empirical lower bound on epsilon at α=0.05.',
      'Limit of Detection (LoD) Gauge: Flags whether the test operated inside its informative zone.',
      'Multi-Attack Suite: Distance-MIA, DOMIAS generative MIA, exact-match, linkability, and attribute inference.',
    ],
    callToAction: 'Check the Empirical Audit card on the right to compare Proved ε vs Audited ε̂ vs Ceiling m.',
  },
  {
    step: 4,
    badge: 'STAGE 4: TAMPER RESISTANCE',
    title: 'Red-Team Adversarial Tamper Studio',
    icon: '🛡️',
    description:
      'The privacy budget ledger uses SHA-256 Merkle hash chaining and Ed25519 signatures over every spend. The Red-Team Studio lets you simulate four distinct real-world attacks directly against the SQLite database to prove non-repudiation.',
    highlights: [
      'Retroactive Spend Manipulation: Rewrites historical budget; breaks block SHA-256 hash.',
      'History Truncation: Deletes recent entries; intercepted by signed ledger_head checkpoint.',
      'Merkle Hash Corruption & Signature Forgery: Caught immediately by public-key verification.',
    ],
    callToAction: 'Scroll to the Privacy Budget Ledger panel below and click "Launch Attack".',
  },
  {
    step: 5,
    badge: 'STAGE 5: PORTABLE DISTRIBUTION',
    title: 'Self-Verifying Capsule & Croissant 1.1 JSON-LD',
    icon: '📦',
    description:
      'SynthProof eliminates reliance on trusted third parties by packaging synthetic datasets into standalone .html capsules. Each capsule embeds the data, MLCommons Croissant 1.1 metadata, and an offline WebCrypto Ed25519 verifier that runs in any browser without server dependencies.',
    highlights: [
      'Zero-Dependency Distribution: A single portable .html file that runs 100% offline.',
      'MLCommons Croissant 1.1: Machine-readable W3C JSON-LD dataset metadata.',
      'In-Browser WebCrypto Verification: Recipients verify digital signatures with one click.',
    ],
    callToAction: 'Click "Export Standalone Capsule (.html)" or open the Zero-Trust Verifier.',
  },
]

export function GuidedTourModal({
  isOpen,
  onClose,
  onOpenVerifier,
}: GuidedTourModalProps) {
  const [currentStepIdx, setCurrentStepIdx] = useState(0)

  if (!isOpen) return null

  const step = TOUR_STEPS[currentStepIdx]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 p-4 backdrop-blur-xs">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="relative flex max-h-[90vh] w-full max-w-3xl flex-col rounded-lg border border-bone-edge bg-[#FAF9F6] shadow-2xl dark:border-stage-line dark:bg-stage-deep"
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-bone-edge p-5 dark:border-stage-line">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-proved/15 text-sm">
                🎯
              </span>
              <h2 className="font-display text-2xl tracking-tight">SynthProof Prototype Guided Tour</h2>
            </div>
            <p className="mt-1 text-xs text-graphite-faint">
              An interactive walkthrough demonstrating the full differential privacy & cryptographic verification system.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-graphite-faint hover:bg-bone-edge/50 hover:text-graphite dark:hover:bg-stage-line dark:hover:text-bone"
          >
            ✕
          </button>
        </div>

        {/* Stepper Dots Bar */}
        <div className="flex items-center justify-between border-b border-bone-edge/60 bg-bone/20 px-6 py-2.5 dark:border-stage-line/60 dark:bg-stage/20">
          <div className="flex items-center gap-2">
            {TOUR_STEPS.map((s, idx) => (
              <button
                key={s.step}
                onClick={() => setCurrentStepIdx(idx)}
                className={`flex h-6 items-center gap-1.5 rounded-full px-2.5 font-mono text-[10px] font-semibold transition-colors ${
                  idx === currentStepIdx
                    ? 'bg-proved text-white shadow-xs'
                    : idx < currentStepIdx
                      ? 'bg-signal-ok/20 text-signal-ok hover:bg-signal-ok/30'
                      : 'bg-bone-edge text-graphite-faint hover:text-graphite dark:bg-stage-line dark:hover:text-bone'
                }`}
              >
                <span>{s.step}</span>
                <span className="hidden sm:inline">{s.title.split(' ')[0]}</span>
              </button>
            ))}
          </div>
          <span className="font-mono text-2xs text-graphite-faint">
            Step {currentStepIdx + 1} of {TOUR_STEPS.length}
          </span>
        </div>

        {/* Body Content */}
        <div className="thin-scroll flex-1 overflow-y-auto p-6 space-y-5">
          <AnimatePresence mode="wait">
            <motion.div
              key={step.step}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.2 }}
              className="space-y-4"
            >
              <div className="flex items-center gap-2">
                <span className="rounded bg-proved/15 px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-wider text-proved dark:text-proved-lift">
                  {step.badge}
                </span>
              </div>

              <div className="flex items-start gap-3">
                <span className="text-3xl">{step.icon}</span>
                <div>
                  <h3 className="font-display text-xl tracking-tight text-graphite dark:text-bone">
                    {step.title}
                  </h3>
                  <p className="mt-1.5 text-xs leading-relaxed text-graphite-soft dark:text-bone/80">
                    {step.description}
                  </p>
                </div>
              </div>

              {/* Highlights Box */}
              <div className="rounded-md border border-bone-edge bg-bone-deep/40 p-4 dark:border-stage-line dark:bg-stage/40">
                <h4 className="font-mono text-2xs font-semibold uppercase tracking-wider text-graphite-faint">
                  Key Technical Capabilities
                </h4>
                <ul className="mt-2 space-y-2">
                  {step.highlights.map((h, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-graphite dark:text-bone">
                      <span className="mt-0.5 text-proved dark:text-proved-lift">✦</span>
                      <span>{h}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Call to Action Banner */}
              <div className="rounded-md border border-signal-ok/30 bg-signal-ok/[0.04] p-3 text-xs">
                <span className="font-mono font-bold text-signal-ok">How to try it: </span>
                <span className="text-graphite dark:text-bone">{step.callToAction}</span>
              </div>
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Footer Navigation */}
        <div className="flex items-center justify-between border-t border-bone-edge p-4 dark:border-stage-line">
          <button
            onClick={() => setCurrentStepIdx((i) => Math.max(0, i - 1))}
            disabled={currentStepIdx === 0}
            className="btn-secondary !px-3 !py-1.5 !text-xs disabled:opacity-40"
          >
            ← Previous
          </button>

          <div className="flex items-center gap-2">
            {currentStepIdx === TOUR_STEPS.length - 1 && (
              <button
                onClick={() => {
                  onClose()
                  onOpenVerifier()
                }}
                className="btn-primary !border-proved !bg-proved !px-3 !py-1.5 !text-xs !text-white"
              >
                🛡️ Open Zero-Trust Verifier
              </button>
            )}

            {currentStepIdx < TOUR_STEPS.length - 1 ? (
              <button
                onClick={() => setCurrentStepIdx((i) => Math.min(TOUR_STEPS.length - 1, i + 1))}
                className="btn-primary !px-4 !py-1.5 !text-xs"
              >
                Next Step →
              </button>
            ) : (
              <button
                onClick={onClose}
                className="btn-ghost !px-3 !py-1.5 !text-xs"
              >
                Done / Explore Console
              </button>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  )
}
