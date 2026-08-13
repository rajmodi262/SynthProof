# Chapter 8 — Discussion, Limitations & Future Work

**Target: 1,500 words.** Depends on M2.

## 8.1 Interpretation (~400 words)

What does the proved-vs-audited gap mean for a practitioner? If ε_proved = 8 but no attack
recovers more than ε_audited = 0.6, what should a data holder actually do?

There are two readings — the bounds are loose, or the attacks are weak — and the chapter should
say how to tell them apart. Be careful not to overclaim: **a failed attack is not proof of
safety**, and the audit only lower-bounds what *these* adversaries achieved.

## 8.2 The self-audit as method (~250 words)

A genuinely distinctive section, and one most theses cannot write.

This project audited its own codebase adversarially and found: fabricated metrics in four
modules, an unsound subsampling bound that under-reported ε by roughly 2×, a zero-noise shortcut
that voided the guarantee while still charging budget, mechanisms charged but never applied, and
a mechanism-dispatch bug that meant two "different" generators were secretly the same one. Each
defect is now defended by a named regression test.

The general argument: **DP implementations need adversarial code review as standard practice**,
because a privacy claim is only as strong as its least-checked line. Most published DP systems
have never had this done to them, and the failures found here were not exotic — they were
ordinary software defects with extraordinary consequences.

## 8.3 Limitations (~450 words)

Be thorough. A reviewer trusts a paper that finds its own holes.

- Unbounded min/max sensitivity in the profiler, if M1.7 did not land.
- Simplified canary audit versus the full Steinke construction.
- The ledger is tamper-*evident*, not tamper-*proof*; key custody is an organisational control,
  not a cryptographic one.
- `dp_accounting` is treated as trusted (mitigated by the differential test, if M2.9 landed).
- Tabular data only; record-level privacy only; single data holder.
- Any hypothesis not fully tested — state it plainly rather than letting it go unmentioned.

## 8.4 Future work (~250 words)

User-level privacy for multi-row individuals; multi-party and federated settings; a formal proof
of the pipeline invariant (no read without a charge); a deployment study with a real data holder;
and extending the Privacy Data Sheet format toward a community standard.

## 8.5 Conclusion (~150 words)

Return to the thesis statement. State what was demonstrated — and, with equal clarity, what
was not.
