import type { LedgerState, RunResult } from '@/types'

export interface RunStateContext {
  result: RunResult | null
  ledger: LedgerState | null
  targetEps?: number
  selectedLedgerIndex?: number
  pointLayer?: 'real' | 'synthetic' | 'canary'
}

export interface ExplainerParam {
  label: string
  value: string
}

export interface Explainer {
  key: string
  eyebrow: string
  title: string
  plain: string
  katex: string
  params: (ctx: RunStateContext) => ExplainerParam[]
  source: string
}

export const EXPLAINERS: Record<string, Explainer> = {
  epsilon: {
    key: 'epsilon',
    eyebrow: 'PRIVACY GUARANTEE · BUDGET',
    title: 'Differential Privacy (ε, δ) Accounting',
    plain:
      'ε bounds how much any single individual’s record can alter the probability of any release outcome. We compose multiple discrete noisy steps into a verified total upper bound using Rényi Differential Privacy.',
    katex:
      '\\mathbb{P}[\\mathcal{M}(D) \\in S] \\le e^{\\varepsilon} \\cdot \\mathbb{P}[\\mathcal{M}(D\') \\in S] + \\delta',
    params: (ctx) => {
      const sheet = ctx.result?.sheet
      const m = ctx.result?.measurements
      const proved = sheet?.total_proved_eps ?? m?.proved_eps
      const delta = sheet?.target_delta ?? 1e-5
      const target = ctx.targetEps ?? 1.0
      return [
        { label: 'Proved Epsilon (ε)', value: typeof proved === 'number' ? proved.toFixed(4) : '—' },
        { label: 'Target Epsilon (ε)', value: target.toFixed(2) },
        { label: 'Delta (δ)', value: delta.toExponential(1) },
        { label: 'Composition Method', value: 'RDP (Google dp_accounting)' },
        { label: 'Calibration Status', value: 'Conservative bracket' },
      ]
    },
    source: 'synthproof/accounting/accountant.py',
  },

  aim: {
    key: 'aim',
    eyebrow: 'GENERATOR MECHANISM · AIM',
    title: 'Adaptive Marginal Selection & PGM Inference',
    plain:
      'AIM iteratively identifies high-error 2-way marginal candidate pairs using report-noisy-max with Laplace noise, measures them with calibrated discrete noise, and estimates a consistent distribution via private-PGM without revealing the true dataset row count.',
    katex:
      '\\text{Selection: } \\operatorname*{argmax}_{c \\in \\mathcal{C}} \\left( \\|\\mathbf{y}_c - \\hat{\\mathbf{y}}_c\\|_1 + \\operatorname{Laplace}\\left(\\frac{2}{\\varepsilon_{\\text{sel}}}\\right) \\right), \\quad \\hat{N} = \\operatorname{PGM}(\\mathbf{y} + \\mathcal{N}(0, \\sigma^2))',
    params: (ctx) => {
      const sheet = ctx.result?.sheet
      const mech = sheet?.mechanism_label ?? ctx.result?.sheet?.mechanism ?? 'AIM / Pairwise'
      const rows = sheet?.num_rows ?? '—'
      const source = sheet?.release_rows_source ?? 'declared'
      return [
        { label: 'Synthesis Mechanism', value: String(mech) },
        { label: 'Released Rows (N)', value: String(rows) },
        { label: 'Row Count Source', value: String(source) },
        { label: 'Known Total n Used', value: 'None (privacy preservation D1)' },
        { label: 'Selection Mechanism', value: 'Report-Noisy-Max (sensitivity Δ=2)' },
      ]
    },
    source: 'synthproof/generators/aim.py',
  },

  ceiling: {
    key: 'ceiling',
    eyebrow: 'AUDIT RESOLUTION · HONESTY CEILING',
    title: 'Maximum Provable Audit Ceiling',
    plain:
      'The theoretical upper limit of leakage this specific empirical audit could ever have certified with its planted decoy budget. If an audit detects 0.000 leakage but the ceiling is 2.97, claims above 2.97 are uncertified.',
    katex:
      '\\varepsilon_{\\max}(r) = \\ln\\left( \\frac{\\alpha^{1/r}}{1 - \\alpha^{1/r}} \\right) \\approx \\ln\\left( \\frac{r}{\\ln(1/\\alpha)} \\right)',
    params: (ctx) => {
      const audit = ctx.result?.audit
      const ceiling = audit?.ceiling
      const audited = audit?.audited_eps
      const canaries = audit?.num_canaries ?? audit?.num_members
      const informative = audit?.detects_leak_above !== null
      return [
        { label: 'Audit Ceiling (ε_max)', value: typeof ceiling === 'number' ? ceiling.toFixed(3) : '—' },
        { label: 'Audited Epsilon (ε_aud)', value: typeof audited === 'number' ? audited.toFixed(3) : '—' },
        { label: 'Planted Canaries (r)', value: canaries !== undefined ? String(canaries) : '—' },
        { label: 'Significance Alpha (α)', value: '0.05' },
        { label: 'Informative Range', value: informative ? 'In verifiable range' : 'Below resolution floor' },
      ]
    },
    source: 'synthproof/audit/ceiling.py',
  },

  ledger: {
    key: 'ledger',
    eyebrow: 'IMMUTABLE AUDIT TRAIL · LEDGER',
    title: 'Cryptographic Hash-Chained Privacy Spine',
    plain:
      'Every release commits to the canonical SHA-256 fingerprint of the previous entry, forming an unbroken tamper-evident ledger. The ledger head commits to the current chain length and tip hash under an Ed25519 signature.',
    katex:
      'h_i = \\operatorname{SHA-256}(\\text{canonical}(e_i) \\mathbin{\\|} h_{i-1}), \\quad \\sigma_{\\text{head}} = \\operatorname{Ed25519}_{\\text{sk}}(\\text{count} \\mathbin{\\|} h_{\\text{tip}})',
    params: (ctx) => {
      const idx = ctx.selectedLedgerIndex ?? 0
      const entries = ctx.ledger?.entries ?? []
      const entry = entries[idx] || entries[entries.length - 1]
      return [
        { label: 'Entry ID', value: entry?.entry_id ? entry.entry_id.slice(0, 16) + '…' : '—' },
        { label: 'Entry Hash', value: entry?.hash ? entry.hash.slice(0, 16) + '…' : '—' },
        { label: 'Previous Hash', value: entry?.prev_hash ? entry.prev_hash.slice(0, 16) + '…' : '—' },
        { label: 'Eps Charged', value: typeof entry?.eps_spent === 'number' ? entry.eps_spent.toFixed(4) : '—' },
        { label: 'Chain Intact', value: ctx.ledger?.verified ? 'Verified (INTACT)' : 'Broken / Compromised' },
      ]
    },
    source: 'synthproof/ledger/ledger.py',
  },

  faithfulness: {
    key: 'faithfulness',
    eyebrow: 'STATISTICAL FIDELITY · UTILITY',
    title: 'Downstream Utility & Correlation Preservation',
    plain:
      'Measures how well synthetic records preserve statistical interactions by evaluating Train on Synthetic, Test on Real (TSTR) against the Train on Real, Test on Real (TRTR) baseline, alongside pairwise correlation drift.',
    katex:
      '\\text{Gap} = \\max(0, F1_{\\text{TRTR}} - F1_{\\text{TSTR}}), \\quad \\text{MAE}_{\\text{corr}} = \\frac{1}{\\binom{d}{2}} \\sum_{i < j} |R_{ij} - \\hat{R}_{ij}|',
    params: (ctx) => {
      const m = ctx.result?.measurements
      return [
        { label: 'TSTR Macro F1', value: m ? m.tstr_f1.toFixed(3) : '—' },
        { label: 'TRTR Macro F1', value: m ? m.trtr_f1.toFixed(3) : '—' },
        { label: 'Utility Gap', value: m ? Math.max(0, m.trtr_f1 - m.tstr_f1).toFixed(3) : '—' },
        { label: 'Correlation MAE', value: m ? m.correlation_error.toFixed(3) : '—' },
        { label: 'MIA Defense AUC', value: m ? m.mia_auc.toFixed(3) : '—' },
      ]
    },
    source: 'synthproof/evaluate/utility.py',
  },

  canary: {
    key: 'canary',
    eyebrow: 'ADVERSARIAL AUDIT · CANARY',
    title: 'Empirical Decoy Membership Inference',
    plain:
      'Outlier decoy records are planted in the training distribution. The audit tests whether an empirical nearest-neighbour adversary can distinguish included decoys from held-out decoys, estimating an empirical lower bound.',
    katex:
      '\\mathbb{P}\\left[ \\operatorname{Binomial}\\left(r, \\frac{e^{\\varepsilon}}{1 + e^{\\varepsilon}}\\right) \\ge v \\right] \\le \\alpha',
    params: (ctx) => {
      const audit = ctx.result?.audit
      return [
        { label: 'Canaries Included', value: audit?.num_members !== undefined ? String(audit.num_members) : '—' },
        { label: 'Canaries Held Out', value: audit?.num_holdout !== undefined ? String(audit.num_holdout) : '—' },
        { label: 'Audited Epsilon (Lower)', value: audit ? audit.audited_eps.toFixed(3) : '—' },
        { label: 'Fisher p-value', value: audit ? audit.p_value.toFixed(4) : '—' },
        { label: 'Test Method', value: 'One-run binomial tail (Steinke 2023)' },
      ]
    },
    source: 'synthproof/audit/canary.py',
  },

  seal: {
    key: 'seal',
    eyebrow: 'CRYPTOGRAPHIC VERIFICATION · SEAL',
    title: 'Zero-Trust Chain Integrity & Digital Signatures',
    plain:
      'Anyone can inspect and independently verify the SHA-256 hash chaining and Ed25519 digital signature of every datasheet and ledger entry in the browser without contacting or trusting the server.',
    katex:
      '\\operatorname{Verify}_{\\text{pk}}(\\sigma_{\\text{sheet}}, \\operatorname{SHA-256}(\\text{canonical}(\\text{sheet}))) \\stackrel{?}{=} \\text{True}',
    params: (ctx) => {
      const ledger = ctx.ledger
      return [
        { label: 'Ledger Verified', value: ledger?.verified ? 'True (Intact)' : 'False (Compromised)' },
        { label: 'Total Sealed Entries', value: ledger ? String(ledger.count) : '—' },
        { label: 'Total Budget Spent', value: ledger ? `Σε ${ledger.total_eps_spent.toFixed(2)}` : '—' },
        { label: 'Signature Algorithm', value: 'Ed25519 (RFC 8032)' },
        { label: 'Hash Digest', value: 'SHA-256 (FIPS 180-4)' },
      ]
    },
    source: 'synthproof/ledger/ledger.py',
  },

  boundary: {
    key: 'boundary',
    eyebrow: 'PUBLIC BOUNDARY · SECURITY',
    title: 'Random Seed Withholding & Replay Protection',
    plain:
      'Publishing the pseudorandom seed makes DP synthesis deterministic: an adversary who knows the seed can replay the algorithm and test candidate records with 100% precision (15/15 replay leak). The seed is drawn securely and never published.',
    katex:
      '\\text{Deterministic Replay: } \\hat{D} = f(D, \\text{seed}) \\implies \\operatorname{Attack}_{\\text{known-seed}}(x) = 1.0',
    params: () => [
      { label: 'Published Seed', value: 'None (Withheld)' },
      { label: 'Measured Replay Leak', value: '15/15 with seed vs 0/15 without' },
      { label: 'Boundary Rule', value: 'Decision D5 in Public Release Boundary' },
      { label: 'Neighbouring Relation', value: 'Add/remove one record' },
    ],
    source: 'docs/design/PUBLIC_RELEASE_BOUNDARY.md',
  },
}
