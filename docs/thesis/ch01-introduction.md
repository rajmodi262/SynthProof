# Chapter 1 — Introduction & Motivation

**Target: 1,200 words.** Write *after* Ch.2 and Ch.3 — an introduction is far easier once you
know exactly what you are introducing.

## 1.1 Motivation (~350 words)

- Open with the concrete bind: data that could train genuinely useful models sits in compliance
  review instead.
- De-identification does not work. Sweeney (2000): 87% of the US population uniquely identified
  by ZIP + date of birth + sex. Narayanan & Shmatikov (2008): the Netflix Prize dataset
  re-identified from public IMDb ratings. AOL's "anonymised" search logs named users within days.
- Regulation now binds: GDPR Art. 9, HIPAA, and India's DPDP Act 2023.
- Synthetic data is the escape hatch teams reach for — and almost none of it ships with any
  statement of how private it actually is.

## 1.2 Problem statement (~250 words)

Two research communities, each solving half the problem. Formal DP proves an upper bound that
nobody verifies against the implementation. Empirical auditing measures a lower bound that
carries no guarantee, accumulates no budget across releases, and is not attached to the artefact
it describes. Nothing ships both.

## 1.3 Thesis statement (~100 words)

Use the statement from [`../thesis.md`](../thesis.md), tightened.

## 1.4 Contributions (~300 words)

Number them, and mark each honestly against what exists at submission:

1. A dual-sided assurance pipeline reporting ε_proved and ε_audited for the same artefact.
2. Budget-charged domain profiling — schema and range discovery priced rather than taken free.
3. An append-only Ed25519-signed ledger for cross-release organisational budget accounting.
4. An empirical study of the proved-vs-audited gap across mechanism families (H1), and of its
   variation across demographic subgroups (H2).

Be precise about which are *implemented* and which are *evaluated*. A reviewer will separate
these whether or not you do.

## 1.5 Scope and non-goals (~100 words)

Tabular data only. Single data holder. Record-level privacy. Forward-pointer to Ch.3 §3.5.

## 1.6 Thesis structure (~100 words)

One sentence per chapter.

## Writing note

The introduction is the most-read and least-carefully-written chapter in most theses. Draft it
last, then cut it by a third.
