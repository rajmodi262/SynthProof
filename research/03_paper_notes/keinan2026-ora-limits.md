# Keinan, Shenfeld & Ligett — How Well Can Differential Privacy Be Audited in One Run?

| | |
|---|---|
| **id** | `keinan2026-ora-limits` |
| **Authors** | Amit Keinan, Moshe Shenfeld, Katrina Ligett (Hebrew University of Jerusalem) |
| **Venue** | **To appear in NeurIPS 2025** (header of PDF) |
| **Version read** | arXiv:2503.07199v4, dated 20 Feb 2026 |
| **URL** | https://arxiv.org/abs/2503.07199 · PDF https://arxiv.org/pdf/2503.07199 |
| **Code** | https://github.com/amitkeinan1/exploring-one-run-auditing-of-dp (stated in footnote 2, **not yet checked**) |
| **Tier** | **S** |
| **Fetched** | yes — full text of pp. 1-5 read directly |
| **Relevance to SynthProof** | **5 / 5** — it is the closest published work to finding F2 |

---

## Problem solved

Steinke et al. (2023) proved one-run auditing (ORA) yields a *valid* lower bound on the true
privacy parameter. They left open **how precisely** ORA can recover the true parameter, and what
properties of the audited algorithm govern that precision. This paper characterises the maximum
achievable efficacy of ORA and identifies what limits it.

## Method in five sentences

1. Formalise ORA as a guessing game: sample `S ~ Uniform({-1,1}^n)`, use it to pick one element
   from each pair in a pair vector `Z` to build dataset `D`, run `M`, and let a guesser `G` emit
   guesses `T` with abstentions allowed.
2. Define **ORA efficacy** as `E = E[V_n / R_n]` — expected ratio of correct guesses to taken
   guesses (Def. 3.2).
3. Prove ORA is asymptotically tight **iff** there exists an adversary strategy whose efficacy
   converges to `p(eps(M))`, where `p` is the standard logistic function (Lemma 3.3).
4. Show ORA is *not* asymptotically tight for broad algorithm classes, via three explicit gaps,
   each demonstrated with a constructed algorithm.
5. Characterise optimal efficacy through a relaxation they call *distributional differential
   privacy*, and propose adaptive variants to shrink the interference gap for DP-SGD.

## The three gaps (§4) — this is the core result

| Gap | Statement |
|---|---|
| (1) Non-worst-case privacy for elements | DP is set by the *worst-case* element; ORA must guess on many elements, most of which are not worst-case. Illustrated with Name-And-Shame: optimal efficacy tends to 1/2. |
| (2) Non-worst-case outputs | DP quantifies over *any* output; ORA sees one run's *typical* output. Illustrated with All-or-Nothing. |
| (3) **Interference** | When an algorithm's output aggregates many inputs, elements interfere and one can only be guessed using knowledge of the others. Illustrated with XOR: optimal efficacy is exactly 1/2. |

**The sentence that matters most (verbatim, §4):**

> *"DP bounds the privacy loss of **every element** from **any output** against an adversary with
> **full knowledge**. In contrast, ORA captures a more relaxed privacy notion that only protects
> the **average element** from the **typical output** against an adversary with **partial
> knowledge**."*

## Key assumptions, including unstated ones

- Focuses on **pure eps-DP** (delta = 0) to isolate ORA's limits; argues approximate DP behaves
  similarly but that auditing it can only add a further gap (§1, footnote 1 citing
  Kasiviswanathan & Smith).
- Assumes the supremum in the DP definition is attained (footnote 4; argued not to weaken results).
- **Unstated:** the analysis is asymptotic — Def. 3.1 requires `R_n -> infinity` (*unlimited
  guesses*). Everything is about what survives as the guess count grows without bound.
- **Unstated:** assumes the loss is computationally feasible to evaluate (footnote 9 concedes
  this may itself be a further source of gap in all auditing methods).

## What this paper makes impossible for SynthProof to claim as novel

- Any claim that "one-run auditing has limits nobody has characterised." **That is this paper's
  entire contribution**, at a NeurIPS venue, from a strong group.
- Any claim to have first noticed that ORA understates true epsilon.
- Any claim about *interference* between simultaneously-audited elements — they name it, and
  note Xiang et al. [12] independently identified it too.

## What it does NOT cover — the surviving space for F2

**This is the decisive distinction and it must be defended precisely.**

| | Keinan et al. | SynthProof F2 |
|---|---|---|
| Regime | **asymptotic** — `R_n -> infinity`, unlimited guesses | **finite-sample** — fixed canary count `m` |
| Barrier | structural: worst-case vs average element, worst-case vs typical output, interference | statistical: Clopper-Pearson interval width at finite `m` |
| Persists as m grows? | **yes** — a gap that never closes | **no** — vanishes as `m -> infinity` |
| Object | efficacy of the *guesser* | maximum *reportable epsilon* of the *estimator* |
| Audience | theory | practitioner reporting standard |

They are **two different ceilings on the same instrument.** Keinan et al. bound what ORA can
learn even with infinite data; SynthProof measured what it can *report* with the data an
experiment actually has.

## Verdict on SynthProof finding F2

- **The mathematics of F2 is KILLED — and not even by this paper.** Steinke et al.'s own bound,
  reproduced in this paper's §2 as `eps'_beta(v,r) := sup{eps : Pr[Bin(r, p(eps)) >= v] <= beta}`,
  gives SynthProof's ceiling in one substitution: set `v = r` (perfect adversary) and it reduces
  to `p(eps)^r = beta`, which is exactly the `p^r = alpha` relation in
  `results/AUDITOR_COMPARISON.md`. SynthProof independently re-derived a one-line corollary of
  the paper it was already citing. `CONFIDENCE: high` — the formula is on the page.
- **The reporting-standard framing of F2 is WOUNDED, NOT KILLED.** This paper is theoretical and
  asymptotic. It does not argue that published audit results should be reported alongside the
  maximum value achievable at their sample size, and does not tabulate max epsilon against canary
  count. `CONFIDENCE: med` — pending Phase 2 family A, which is searching for exactly that.

## Strategic warning

This is a NeurIPS paper from Katrina Ligett's group, revised as recently as February 2026, with
a public code repo. **"How well can auditing work" is an active, competitive research front.** A
capstone that tries to make a theoretical contribution here will be outgunned. If any part of F2
survives, it survives as an *empirical / practice* contribution — measuring what deployed audits
actually do — not as theory.

## Leads generated (all `[UNVERIFIED]`, from this paper's related work)

- Malek Esmaeili et al. [9] — efficient auditing via MIA on many examples in one run
- Zanella-Beguelin et al. [10] — more rigorous evaluation of the above
- **Xiang et al. [12]** — contemporaneous f-DP one-run auditing, information-theoretic, *also
  identifies the interference gap*
- Jagielski et al. [6]; Nasr et al. [7], [8]; Kasiviswanathan & Smith [2]
