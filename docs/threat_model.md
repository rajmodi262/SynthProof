# SynthProof — Threat Model & Scope Specification

---

## 1. Adversary Model

- **Adversary Goal:** Determine whether a specific target individual $x^*$ was present in the sensitive training dataset $D_{\text{train}}$ (Membership Inference Attack) or reconstruct sensitive attributes of $x^*$ given partial background knowledge (Attribute Reconstruction Attack).
- **Adversary Capabilities:**
  - **Black-Box Access:** The adversary receives the released synthetic dataset $D_{\text{synth}}$ and the signed Privacy Data Sheet certificate.
  - **Auxiliary Knowledge:** The adversary possesses background knowledge of the population distribution and partial attribute values for target records.
  - **Held-out Reference Set:** The adversary has access to an independent held-out reference dataset $D_{\text{holdout}}$ from the same population distribution.

---

## 2. Unit of Privacy

- **Record-Level Differential Privacy:** SynthProof guarantees $(\epsilon, \delta)$-Differential Privacy at the single-record level. Addition or removal of any individual record $x$ alters the probability of output synthetic datasets by at most $e^\epsilon$.

---

## 2a. Disclosure risks measured

The EDPB's anonymisation criteria — operationalised by Anonymeter (Giomi et al., PoPETs 2023)
— treat three risks as distinct. All three are now measured on every release:

| Risk | Question | Implementation |
|---|---|---|
| **Singling out** | Can one record be isolated? | `attacks/exact_match_risk.py` |
| **Linkability** | Can two pieces of information be shown to concern the same person? | `attacks/linkability.py` |
| **Inference** | Can an attribute value be deduced? | `attacks/attribute_inference.py` |

**These are our own approximations, not Anonymeter.** Integrating the reference toolkit was
attempted on 2026-08-23 and is not possible here: `anonymeter` pins `numpy < 2` while
`jax`/`jaxlib` — and therefore `mbi`, private-PGM and real AIM — require `numpy >= 2`.
Installing it downgraded numpy and broke AIM outright. The trade is not worth making, and
naming our approximations after Anonymeter's concepts without saying so would breach standing
rule 4.

Each carries its own control, because a raw rate is uninterpretable: linkability reports
agreement in excess of a **row-shuffled release** (marginals preserved, row correspondence
destroyed), and attribute inference scores against a **conditional** baseline rather than a
marginal one. Linkability is reported **not applicable** on tables with fewer than four
columns, which cannot be split into two disjoint halves.

---

## 3. Out-of-Scope Attacks

- **Hardware Side-Channels:** Physical power, electromagnetic, or CPU cache timing side-channels during execution.
- **Upstream Data Corruption:** Adversarial poisoning of raw database extracts before ingestion by SynthProof.
