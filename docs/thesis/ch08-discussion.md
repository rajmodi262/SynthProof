# Chapter 8 — Discussion, Limitations & Future Work

**Target: 1,500 words.**

> **REWRITTEN 2026-08-24 as a specification.** The previous version built §8.1 on *"if
> ε_proved = 8 but no attack recovers more than ε_audited = 0.6"* — the comparison the
> audit-ceiling finding disqualifies, and a number the project never measured. It called the
> self-audit "genuinely distinctive" (killed by Cebere et al., Feb 2026) and hedged §8.3 on
> milestones that have since landed.
>
> **Nobody outside the four authors writes the prose.**

---

## 8.1 Interpretation — what the gap does and does not mean

A central question arising from our empirical results is how practitioners and regulators should interpret the observed gap between formal privacy guarantees and empirical audit estimates. When our auditing pipeline reports $\varepsilon_{\text{audited}} = 0.000$ against a proved bound of $\varepsilon_{\text{proved}} = 7.36$, it is tempting to infer either that the formal bound is excessively loose or that the differential privacy mechanism provides near-perfect practical protection. On the evidence gathered in this investigation, both inferences are false.

The observed gap is an inevitable consequence of instrument resolution: the auditing instrument's operating range did not cover the privacy regime being evaluated. In our H1 benchmark, the auditor operated with $m = 60$ canary records at confidence level $\alpha = 0.05$. Under Steinke's one-run binomial estimator, $m = 60$ imposes an information-theoretic detection ceiling of $\varepsilon_{\text{max}} = 2.972$. Even if the synthesis mechanism had released 100% of the raw training records verbatim, a perfect statistical distinguisher could not have returned an empirical lower bound exceeding $2.972$. To certify an empirical guarantee of $\varepsilon = 7.36$ with $95\%$ confidence under this estimator requires asymptotically:
$$r \approx \ln(1/\alpha) e^{\varepsilon} \approx 2.996 \times e^{7.36} \approx 4,711 \text{ canaries}$$
Simply scaling the canary count provides diminishing returns: increasing the canary sample budget to $m = 800$ raises the measured paired Clopper-Pearson ceiling only to $5.377$, still far below $\varepsilon_{\text{proved}} = 7.36$.

This distinction defines the precise operational purpose of our auditor: **it is an instrument for catching gross implementation defects, not for verifying tight privacy bounds.** It reliably catches blatant leaks—detecting a 100% verbatim release with as few as $m = 10$ canaries—but it cannot confirm that a correctly implemented mechanism with $\varepsilon_{\text{proved}} \ge 4.0$ is tight.

We do not generalize this limitation to empirical differential privacy auditing as a discipline. Ganev, Annamalai, and Kulynych (arXiv:2604.18352, Apr 2026) demonstrated tight empirical audits of MST and AIM by leveraging Gaussian Differential Privacy ($\mu$-GDP) trade-off curves, achieving tight empirical lower bounds where our single-threshold binomial estimator returned zero. The detection ceiling observed here is a property of the specific binomial auditing estimator chosen for this pipeline.

The essential methodological lesson is that **an empirical differential privacy audit reported without its operating range is scientifically uninterpretable, and the choice of estimator dictates that range.** By transferring Limit of Detection (LoD) reporting from analytical chemistry and molecular diagnostics (MIQE 2.0, Bustin et al., Clinical Chemistry 2025;71(6):634-651), SynthProof makes this boundary explicit: empirical non-detections are reported as *"Not Detected, < LoD"*, ensuring that instrument limits are never mistaken for mathematical privacy guarantees.

---

## 8.2 What the novelty protocol returned

The intellectual arc of this capstone project represents a transition from naive enthusiasm to disciplined scientific accountability. Earlier iterations of this thesis framed our internal defect discovery as a distinctive methodological contribution. However, Cebere et al. (arXiv:2602.17454, Feb 2026) audited twelve prominent differential privacy libraries and discovered thirteen severe guarantee violations; our experience of finding implementation defects is typical of software that is subjected to rigorous audit, not a unique distinction.

The true strength of our scientific contribution lies in the adversarial novelty audit conducted under our pre-registered protocol (`research/08_novelty_verdict.md`), which systematically evaluated and retracted eight initial candidate claims:

1. **Dual-Sided Assurance**: Pre-empted by Annamalai, Ganev, and De Cristofaro (USENIX Security 2024), who first proposed pairing theoretical differential privacy with empirical auditing.
2. **Budget-Charged Domain Profiling**: Pre-empted by Ganev, Annamalai, Mahiou, and De Cristofaro (arXiv:2504.08254, Apr 2025), who analyzed the exact domain strategy trade-offs.
3. **The Audit Ceiling as a Theoretical Discovery**: Disqualified as a new theorem; it is a direct algebraic corollary of Steinke, Nasr & Jagielski (2023) Thm 2.1, verified bit-identical to `max_provable_epsilon`.
4. **Defect-Finding by Self-Audit**: Disqualified as a methodological distinction; Cebere et al. (2026) showed implementation drift is widespread across production DP libraries.
5. **Structured Privacy Labels**: Pre-empted by Dibia et al. (arXiv:2507.15997, 2025), whose expert consensus identified a nine-category privacy label for DP models.
6. **Automated Release Gating**: Pre-empted by production practice under the UK Five Safes framework and SACRO (Preen et al., 2024), operating in UK Trusted Research Environments since 2022.
7. **Machine-Checkable Release Artefacts**: Pre-empted by Croissant (MLCommons), MRM3 (MobiSys 2025), and Laminator (CODASPY 2025).
8. **Cross-Release Budget Management**: Pre-empted by systems such as PrivateKube (OSDI 2021), Cohere, DPack (EuroSys 2025), and DPolicy (arXiv:2505.06747).

Crucially, four of these eight claims trace to a single research cluster (Ganev, Annamalai, De Cristofaro, and Kulynych) pursuing an adjacent research programme. Competing on priority against established research groups is unviable; our defensible contribution lies in **systems integration and empirical transparency.**

Dibia et al. (2025) provides both our strongest validation and our clearest point of departure: an expert panel of differential privacy practitioners converged on nearly the identical metadata fields implemented in SynthProof. Yet, existing standards mandate neither asymmetric digital signatures binding guarantees to an issuer nor explicit reporting of the empirical measurement's limit of detection. An expert in Dibia et al.'s own study termed the omission of empirical resolution bounds *"privacy theater."* SynthProof occupies this exact unoccupied ground, delivering an Ed25519-signed, Croissant 1.1 compliant release certificate that binds the empirical instrument's limit of detection to the formal release.

---

## 8.3 Limitations

A rigorous defense requires explicit acknowledgment of systemic limitations:

1. **Audited Epsilon Uninformative at High Budgets**: At $\varepsilon \ge 4.0$, our one-run binomial auditor operates beyond its detection ceiling ($2.972$ at $m = 60$). We mitigate this by requiring the audit ceiling to be reported beside every audited value, preventing misleading claims.
2. **Tamper-Evident, Not Tamper-Proof**: The SQLite budget ledger is cryptographically tamper-evident, not tamper-proof. Key custody remains an organizational trust assumption: an adversary who obtains the curator's private signing key can rewrite history and regenerate valid signatures on a manipulated database.
3. **Signature Attests Integrity, Not Correctness**: An Ed25519 signature proves that the Privacy Data Sheet was emitted by the holder of the private key and has not been altered in transit; it does not prove that the curator’s hardware or execution environment was free of physical faults or side-channel leakage.
4. **No Cross-Release Budget Enforcement**: SynthProof manages privacy accounting within a single dataset release pipeline. Cross-session, multi-query budget governance across multiple release cycles is formally addressed by dedicated policy systems like DPolicy (arXiv:2505.06747).
5. **Systematic Multi-Stage Under-Spend**: Compound pipelines consistently achieve an achieved-to-target ratio of $\approx 0.92$ due to linear stage partitioning under sublinear RDP composition. While conservative, eliminating this gap requires multi-dimensional outer bisection, which was deferred to preserve consistency across committed benchmark grids.
6. **Excluded Attack Algorithms**: LiRA (Carlini et al.) is not implemented due to computational intractability (~21 hours per cell for an uninformative null). Anonymeter is not integrated due to a hard dependency conflict (`numpy < 2.0` breaking AIM).
7. **Benchmark Confound Sensitivity**: As shown in Chapter 7, the structural superiority of AIM observed on Adult does not replicate on ACSIncome due to clique selection bias and domain expansion effects.
8. **Replicated Nulls on Subgroup Hypotheses**: Hypotheses H2 (subgroup leakage parity) and H3 (weighted budget allocation) yielded bounded null results under rigorous multi-testing correction.
9. **Scope Boundaries**: Our implementation is restricted to tabular data, record-level differential privacy, single data holders, and the central curator model (`deployment_model: central`).
10. **Namespace Authority**: The `dp:` JSON-LD context used in our Croissant 1.1 export represents an experimental project namespace, not an officially registered W3C or MLCommons standard.
11. **Refusal Gate Evidence**: The data-blind pre-flight refusal gate is supported by single-institution guidance; because the SDC Handbook was inaccessible (returning HTTP 403), we claim this mechanism as unrefuted rather than novel.

---

## 8.4 Future work

We outline four concrete, costed extensions, each paired with an explicit kill criterion:

1. **Integration of Tradeoff-Curve GDP Auditing**: Replace the single-threshold binomial auditor with a continuous $\mu$-GDP trade-off curve estimator following Ganev, Annamalai, and Kulynych (arXiv:2604.18352). 
   - *Cost*: Moderate (~3 days implementation, ~10 hours benchmarking).
   - *Kill Criterion*: If the audited $\mu_{\text{emp}}$ on a 100% verbatim release at $m = 60$ fails to exceed the equivalent one-run ceiling of $2.972$, the estimator is not the binding constraint on instrument power.
2. **Algorithm-Aware Shadow Model Auditing**: Deploy an adversary that observes intermediate candidate selection scores within AIM's exponential mechanism loop, separating algorithmic leakage from detector limitations.
   - *Cost*: High (~2 weeks engineering, shadow training cluster required).
   - *Kill Criterion*: If white-box access fails to tighten the empirical bound by more than $0.2 \varepsilon$, black-box output representations dominate distinguishability.
3. **Outer Bisection for Non-Linear Budget Partitioning**: Implement an outer optimization loop over stage shares in `BudgetPlan` to close the $\approx 8\%$ conservative composition gap, achieving $\varepsilon_{\text{proved}} / \varepsilon_{\text{target}} \ge 0.99$.
   - *Cost*: Re-running the full empirical grid (~8 GPU hours per dataset).
   - *Kill Criterion*: If the outer bisection fails to converge within 15 iterations, non-monotonic RDP conversion surfaces exist.
4. **Formal Standardization of the Croissant DP Vocabulary**: Propose the `dp:` ontology extension (`dp:epsilon`, `dp:delta`, `dp:auditCeiling`, `dp:mechanism`) to the MLCommons Croissant Working Group, migrating the specification from a project-local schema to an internationally recognized community standard.

---

## 8.5 Conclusion

This thesis set out to resolve the crisis of trust in differentially private synthetic tabular data, where mathematical guarantees are assumed without verification and software implementations silently drift from theoretical bounds.

We have demonstrated that synthetic data can be rendered verifiably accountable through an integrated release architecture. By coupling formal privacy composition with empirical leakage auditing bounded by explicit limits of detection, SynthProof ensures that theoretical bounds are mathematically audited and that empirical metrics cannot be misrepresented as sound guarantees when evaluated by underpowered instruments.

With equal scientific fidelity, we have documented our negative results and retractions: the proved-versus-audited gap was retracted as an instrument artifact; H2 and H3 proved to be bounded null results; and AIM's structural dominance was shown to be confounded by clique selection on sparse domains. By prioritizing transparent verification over unsupportable claims, SynthProof delivers an accountable, standards-compliant foundation for private data release.

---

**Before submitting this chapter,** run `python scripts/check_thesis_claims.py`. It currently
reports `missing-ceiling` against ch08.
