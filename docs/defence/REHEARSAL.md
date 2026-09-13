# Rehearsal — the three questions you would least like

Task 6.3 of [`../ROAD_TO_TEN.md`](../ROAD_TO_TEN.md). [`DEFENCE.md`](DEFENCE.md) §9 answers
twenty-plus questions a panel will probably ask. This file is different: it is the three a
panel might ask that could actually go badly, rehearsed properly.

Each has the same shape — **the honest answer**, **the answer that loses the room**, and **the
follow-up you should assume is coming**. Say these before the panel finds them; a weakness you
raise yourself is evidence of rigour, and the same weakness extracted from you is evidence of
the opposite.

One of the three — Q2 — is **not currently answered anywhere in the defence pack**. It is the
one most likely to be asked and the one you are least prepared for.

---

## Q1. "Your auditor cannot detect what you are claiming. So what did you measure?"

**Why it stings:** it is correct, it attacks the headline result, and the project's own
documents supply the ammunition.

### The honest answer

> "You are right, and we established that ourselves before anyone asked. Our auditor cannot
> report an ε above about **2.7** at the 60 canaries our experiments use — and that holds even
> against a release that is 100% verbatim training data. Our largest proved ε is **7.36**. So
> the gap between proved and audited ε, which is what this project was originally designed to
> measure, **was guaranteed by the instrument before any mechanism ran**. We disqualified our
> own headline comparison.
>
> That is not a bug we failed to fix. It is a corollary of Steinke, Nasr and Jagielski's
> Theorem 2.1 — the number of canaries bounds what any canary-based audit can certify, and
> certifying a given ε costs canaries **exponential** in that ε. We verified our implementation
> matches the closed form bit-identically at m = 10, 60, 100, 400 and 800.
>
> And this is precisely why the project reports the ceiling **inside the released artefact**.
> A privacy audit that says 'passed' without stating what it could not have detected is what
> one of Dibia et al.'s own expert panel called *privacy theater*. The finding is the
> contribution: we measured our instrument, found it could not do the job, and said so."

### The answer that loses the room

Anything that treats ε_audited = 0.000 as a *result* — "the audit found no leakage, so the
mechanism is private." The audit could not have found leakage. Saying it did is the exact error
the project exists to prevent, and a DP examiner will spot it instantly.

### Assume this follow-up

**"Then why not just use more canaries?"** — Because it does not close: m = 800 lifts the
paired ceiling only to **5.38**, still under our 7.36, and the cost is exponential in ε. We
also implemented the full Steinke one-run construction, which improved the m = 60 verbatim
reading from 2.03 to only 2.17. **The limit is what canary auditing can prove, not which
auditor implements it.** Ganev, Annamalai & Kulynych (arXiv:2604.18352) get tight audits on
MST and AIM using a GDP/f-DP estimator instead — that is the right next step, and naming it is
a better answer than defending ours.

---

## Q2. "`git log` shows one committer, and an AI co-author on almost every commit. Who built this?"

**Why it stings:** it is trivially checkable, it is about integrity rather than technique, and
it is **the one question the defence pack does not currently answer**. Assume a panel member
runs `git log` — it takes ten seconds.

### The facts, so nobody is surprised by them

| | |
|---|---|
| Commits, code repository | **140**, all from a single human author |
| Commits, outer repository | **10**, same author |
| Commits carrying `Co-Authored-By: Claude Opus 5` | **135 of 140 — 96%** |
| Commits by the other three named members | **0** |

See [`../../../CONTRIBUTIONS.md`](../../../CONTRIBUTIONS.md), which records this with the
commands that reproduce it.

### The honest answer

> "The history is accurate and we have not dressed it up. One member committed all the code,
> and the large majority of commits are marked as AI-assisted, because they were. We recorded
> that in the commit trailers as we went rather than reconstructing it afterwards, and
> `CONTRIBUTIONS.md` reports it with the command to check it.
>
> What the history does **not** capture is the work that never becomes a commit — literature
> reading, thesis drafting, experiment design, hand-testing the prototype. Those are set out
> per member in `CONTRIBUTIONS.md`, each with evidence you can inspect.
>
> On the AI assistance: I would rather be judged on whether the work is correct and whether I
> can explain it. There are 846 Python tests, 28 console tests, 10 end-to-end specs, `mypy`
> clean and blocking in CI, and two honesty gates that fail the build if any document asserts a
> finding we retracted. Ask me about any part of the system."

### The answer that loses the room

Minimising — "Claude just helped with boilerplate", or letting the trailer go unmentioned and
hoping. The trailer is in 135 commit messages. Being caught understating it converts a
procedural question into a credibility question, and you do not recover from that in a viva.

### Assume these follow-ups

- **"Explain this file to me."** The only defence is preparation. Be able to open any module
  and say what it does and why it is that way.
- **"What did you get wrong, and how did you find it?"** Strong material here: the auditor
  ceiling, the retracted confound, a hand-rolled bound that under-reported ε by ~2×, a
  Playwright test that passed without running anything, a bound test that could not fail
  because the data was clipped to the bounds it compared against. And the demo capsules themselves: until 2026-09-13 they were hand-typed and signed, with an audit ceiling their own declared audit could not produce and a green tick computed backwards. Found by recomputing one number. Someone who only prompted an
  AI cannot tell these stories.
- **"Does your institution permit this?"** Know the policy and have made the declaration
  **before** the viva. `CONTRIBUTIONS.md` flags this as an outstanding action; close it.

---

## Q3. "What is actually novel here?"

**Why it stings:** the honest answer is "less than the synopsis implied", and a panel that
senses evasion will keep pulling.

### The honest answer

> "Eight of our candidate contributions are dead, and **we killed them ourselves** — the
> adversarial protocol in `research/` ran eight query families against the literature and
> issued a verdict that went against us. The position we defend is **integration, not
> invention**.
>
> The strongest single citation argues against our novelty and for our design at the same time.
> Dibia et al. (arXiv:2507.15997, 2025) elicited a nine-category DP privacy label from an
> expert panel; its categories overlap our Privacy Data Sheet almost field for field. We did
> not invent the concept — but a panel of DP experts independently converged on what we built,
> which is stronger validation than a novelty claim would have been.
>
> Three narrow differences survived, and none is stated without its caveat: reporting the
> measurement's operating range inside the artefact; cryptographically signing the privacy
> claim, which is engineering novelty rather than science; and data-blind refusal, which is
> **unrefuted rather than novel** — the primary SDC Handbook returned HTTP 403 and we could not
> read it, so we will not claim more."

### The answer that loses the room

Reciting the synopsis contributions as though the verdict had not been issued. The verdict
document is in the repository; a panel that reads it and then hears the old claims concludes
you have not read your own work.

### Assume this follow-up

**"If it is not novel, what is the contribution?"** — That a real system, built carefully,
falsifies its own headline claim and reports that. The auditor ceiling, the retracted confound
and two null hypotheses (H2, H3) are all published in the repository rather than omitted. For a
B.Tech capstone the defensible claim is **integration, engineering quality and demonstrated
research honesty** — not a new theorem.

---

## Two more worth having ready

**"H2 and H3 are null. Isn't that a failed project?"** — A null result is a result, and it is
standing rule 6. H3 replicated null on both datasets with no bootstrap CI excluding zero at any
of five ε. Reporting it is the point; a project that only publishes what worked is the thing
this repository was built to argue against.

**"Your certificate proves the code ran correctly, doesn't it?"** — **No, and say so quickly.**
It attests the *claim*, not the *execution*. Nothing here proves the code that ran is the code
that was audited; that requires a trusted execution environment, which Laminator (CODASPY'25)
does and we do not. This limitation is already in the README.

---

**"Your capsule says verified. Were those numbers real?"** — **Say this first, before anyone
finds it.** Until 2026-09-13 the two shipped demo capsules were typed by hand and signed with a
real key: the Adult one claimed an audit ceiling of 3.50 from a 60-canary audit that can certify
at most 2.972, and its green "NOT DETECTED" tick never compared the proved epsilon with the
ceiling at all. The signature was valid, which is the point worth making: **a signature proves
who made a claim, not that the claim is true.** (Reporting the ceiling inside the artefact is a transfer of
limit-of-detection reporting from analytical chemistry — MIQE 2.0, Bustin et al., *Clinical
Chemistry* 2025;71(6):634–651 — which is exactly why reading it backwards was so damaging.) The capsules are now built from real releases,
the verifier recomputes the ceiling from the declared audit, and the ε = 8 capsule shows in amber
that its own audit could not have certified its claim. If any older PDF, slide or screenshot
shows 0.384 or 3.50, it predates the fix — say so.

## How to rehearse this

1. Have someone else read the question aloud, then answer **without notes**, out loud.
2. Time it. Each answer above is 45–75 seconds spoken. Longer reads as evasion.
3. Lead with the concession, then the evidence. "You are right, and here is what we did about
   it" beats every defensive framing.
4. Q2 is the one to rehearse most, because it is the one you have never said out loud.
