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

## 3. Out-of-Scope Attacks

- **Hardware Side-Channels:** Physical power, electromagnetic, or CPU cache timing side-channels during execution.
- **Upstream Data Corruption:** Adversarial poisoning of raw database extracts before ingestion by SynthProof.
