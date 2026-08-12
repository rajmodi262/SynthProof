# SynthProof — Pitch Decks

Two self-contained pitch decks for the capstone. Both are single HTML files with no external
dependencies — no CDN, no webfonts, no build step. Open either by double-clicking it, or serve
the folder and browse to it.

| File | What it is |
|---|---|
| [`pitch-slides.html`](pitch-slides.html) | 14 static slides. Arrow keys / space to advance, or scroll. Best for a projected talk. |
| [`pitch-interactive.html`](pitch-interactive.html) | Interactive scrollytelling version with four live demos. Best for a screen-shared or self-guided read. |

`PROMPT.md` holds the reusable prompt that generated these, for building similar decks later.

---

## The interactive demos

`pitch-interactive.html` runs real computation in the browser rather than animating pre-baked
results:

- **Re-identification collapse** — toggling ZIP / birth date / sex narrows a synthetic crowd of
  600 down to one person (600 → ~75 → ~3 → 1).
- **The ε dial** — a genuine 14×14 histogram DP mechanism. Gaussian mechanism at δ=1e-5,
  σ = √(2·ln(1.25/δ))/ε, counts clamped at zero and renormalised. Correlation retained is
  measured off the generated points and averaged over 5 noise draws; the membership-inference
  AUC is measured against 300 held-out non-members from the same distribution.
- **Ledger tamper demo** — four blocks chained with real SHA-256 via `crypto.subtle`. Tampering
  with block #2 genuinely invalidates blocks #2–#4.
- **Interactive architecture** — click any pipeline stage for its description.

---

## Accuracy notes — read before presenting

Both decks separate what is measured from what is projected, and that separation must be kept
accurate as the project moves.

- **The Privacy Data Sheet slide is illustrative.** The ε values, audit p-value, and utility
  figures on it show the *shape* of the target artefact, not measured results. Both decks label
  this on the slide itself. Do not remove that label.
- **The ε dial's attack AUC stays near 0.5 across the whole range.** This is the honest measured
  outcome, not a broken widget — the mechanism genuinely does not leak much at this sample size.
  The deck makes that the point: ε_proved spans a factor of 100 while measured attack advantage
  barely moves. That gap is hypothesis H1.
- **The status slide reflects a specific moment.** It lists test counts, coverage, and per
  component Built / Partial / Not-started state. Re-check it against the repo before any
  presentation — a stale status slide is the one thing on here that could mislead a reviewer.

See [`../../brutal_project_audit.md`](../../brutal_project_audit.md) for the full self-audit the
status slide is derived from.
