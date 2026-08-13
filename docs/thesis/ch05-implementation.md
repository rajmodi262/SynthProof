# Chapter 5 — Implementation

**Target: 1,500 words.** Depends on M1.

## 5.1 Technology choices (~250 words)

Python 3.11; `dp_accounting` for composition; `private-pgm` for AIM; `scipy.stats` for exact
binomial intervals; `cryptography` for Ed25519; FastAPI; SQLite. One sentence each on *why* —
especially why composition is delegated rather than implemented in-house.

## 5.2 Package structure (~200 words)

Module-by-module table with responsibilities. Emphasise that module boundaries match the
pipeline stages in Ch.4, so the architecture diagram and the package tree are the same picture.

## 5.3 Noise sampling (~300 words)

- CKS'20 discrete Gaussian rejection sampler; discrete Laplace as a difference of geometrics.
- Why discrete at all: Mironov (2012) floating-point attack on inverse-CDF sampling.
- **Include the χ² goodness-of-fit test against the exact PMF.** A validated sampler is a
  different claim from an asserted one, and this is cheap evidence.
- Report the removed σ < 0.3 shortcut that returned deterministic zeros while the accountant
  still charged ε — a one-line defect that voided the guarantee silently.

## 5.4 Calibration implementation (~250 words)

Bracket-and-bisect, the convergence criterion, and the CI guard across 24 configurations.
Cross-reference Ch.4 §4.4 for the result rather than repeating it.

## 5.5 Ledger implementation (~250 words)

Canonical byte serialisation (fixed-precision floats, sorted keys — otherwise signatures are not
reproducible), chain construction, and verification order. Include the tamper tests that mutate
and delete rows directly in SQLite rather than going through the API.

## 5.6 Testing and CI (~250 words)

Test count, coverage, and what each regression test defends against. Note that every defect the
self-audit found now has a named test. List the property tests (M1.14) and the differential test
against `autodp` (M2.9).

## Figures

- Discrete Gaussian: empirical vs exact PMF
- Coverage report
