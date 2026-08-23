# Phase 2 — Search Strategy and Log

> **Status: PLANNED, NOT EXECUTED.** No query below has been run. The log table is empty by
> design — it is filled only with searches actually performed, with real hit counts and dates.
> Awaiting `CONTINUE`.

---

## 1. Keyword matrix

Axes: core concept x method x application x synonym x adjacent-field term. Historical and
obsolete names included deliberately — see `00_problem_framing.md` §7 for why.

### A. Empirical privacy auditing (highest priority — guards §5.3)
- "privacy auditing" differential privacy lower bound
- "empirical epsilon" estimation differential privacy
- auditing differentially private machine learning
- "one-run" privacy audit / single training run audit
- canary insertion memorization audit
- statistical power privacy audit / sample complexity of privacy auditing
- "tight auditing" differential privacy
- Bayesian estimation differential privacy parameter
- lower bound epsilon Clopper-Pearson audit
- **negative-result framing:** "audit fails to detect" / "insufficient canaries" / "audit power"

### B. DP synthetic tabular data
- differentially private synthetic data tabular marginals
- AIM adaptive iterative mechanism / MST / private-PGM / graphical model DP synthesis
- NIST synthetic data challenge
- **SDC terms:** fully synthetic microdata, partially synthetic data, multiple imputation
  disclosure, Rubin synthetic microdata, Reiter synthetic

### C. Budget accounting and management
- privacy budget management system / privacy budget scheduler
- **privacy odometer / privacy filter** adaptive composition
- privacy accounting library RDP PLD
- DP in database systems (PINQ, Airavat, GUPT, PrivateSQL, Chorus, Sage)
- cross-release / longitudinal privacy budget

### D. Verifiability and cryptographic assurance
- verifiable differential privacy
- zero-knowledge proof differential privacy
- attested / trusted execution differential privacy
- transparency log / certificate transparency / tamper-evident audit log
- proof of correct noise / verifiable randomness DP

### E. Transparency artefacts
- datasheets for datasets / model cards / AI FactSheets
- **privacy nutrition label**
- disclosure risk report / SDC report
- machine-readable privacy metadata / dataset provenance AI Act

### F. Subgroup / fairness (guards H2)
- disparate impact differential privacy accuracy
- **disparate vulnerability membership inference**
- subgroup privacy leakage / per-group empirical privacy
- fairness differentially private synthetic data
- Robin Hood Matthew effects synthetic data

### G. Attacks
- membership inference synthetic data / LiRA / DOMIAS density ratio
- anonymeter singling out linkability inference
- attribute inference reconstruction tabular
- TPR at low FPR membership inference

### H. The critique angle (guards the reframing)
- "differential privacy implementation bugs" / DP library correctness
- floating point attack differential privacy
- reproducibility crisis privacy evaluation
- "epsilon reporting" practice survey / how epsilon is chosen in deployments

## 2. Venues, labs, people likely to own this space

**Venues.** PETS/PoPETs · IEEE S&P · ACM CCS · USENIX Security · NDSS · NeurIPS/ICML/ICLR ·
TPDP workshop · **PSD (Privacy in Statistical Databases)** · **UNECE/Eurostat SDC work
sessions** · Journal of Privacy and Confidentiality · Journal of Official Statistics · VLDB/SIGMOD.

**Groups (INFERENCE, to confirm).** Google/Brain DP team (Steinke, Kamath, Thakurta) · Nasr &
Carlini & Tramer (auditing/attacks) · McKenna/Sheldon/Miklau (UMass, private-PGM) · Troncoso's
SPRING lab EPFL (Stadler, Kulynych) · De Cristofaro's group (Ganev) · Machanavajjhala (Duke) ·
US Census DAS team · OpenDP/Harvard · Reiter (Duke, SDC).

## 3. Coverage plan

| Source | Purpose | Planned |
|---|---|---|
| arXiv | preprints, most recent work | yes |
| Semantic Scholar / OpenAlex | citation graph, forward snowball | yes |
| ACM DL / IEEE Xplore | security venue proceedings | yes |
| Papers With Code | benchmark + leaderboard reality | yes |
| GitHub | OpenDP, SmartNoise, private-pgm, dp_accounting, anonymeter — **what they actually require** | yes, high priority for §5.2 |
| Google Patents / Espacenet | industrial claims on DP certificates/ledgers | yes |
| PhD theses | fuller lit reviews than papers | yes |
| **SDC / official statistics** | the 30-year blind spot | **yes, mandatory** |
| Negative results / retractions | audits that failed | yes |

## 4. Snowballing plan

- **Backward:** references of Steinke et al. 2023, Jagielski et al. 2020, McKenna et al. 2022,
  Stadler et al. 2022, Rogers et al. 2016.
- **Forward:** who cites Steinke 2023 (the auditing-ceiling question lives here) and who cites
  Jagielski 2020.

## 5. Stop rule

Stop when **two consecutive searches yield no new S/A-tier sources**. State explicitly when
saturation was reached, or state honestly that it was not. Minimum bar: >=60 screened, >=20
deep-read, unless the field is provably tiny.

## 6. Execution log

Every query, with date, source, hit count, and new-S/A count. **Empty until Phase 2 runs.**

| # | Date | Source | Query | Hits | New S/A | Note |
|---|---|---|---|---|---|---|
| — | — | — | *(none run)* | — | — | — |
