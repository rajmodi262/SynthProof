# Amendments to the W10 H1 confirmatory preregistration

The preregistration (`docs/prereg/W10_h1_confirmatory.md`) is frozen so the SHA-256 recorded in its
results stays checkable. Amendments are recorded here.

## A1 (2026-10-16 18:35, before any confirmatory result was inspected): scope cut for runtime

**Why.** The plan estimated AIM at about 70 s per cell from the pilot's checkpoint timestamps. The
first confirmatory cell (AIM, adult, epsilon 1, seed 100) took 18 min 46 s (18:08:13 to 18:26:59). A
full H1 cell runs two AIM fits (one on canaries, one canary-free for utility), the canary audit and
five attacks, which the pilot timestamps did not reflect. At that rate the 120 AIM cells of the plan
need about 38 hours on this machine.

**Change.** Only the comparison the pilot left unresolved is run: **adult, epsilon 8**, mechanisms
aim, pairwise and independent, seeds 100–114 (15 per mechanism), everything else as planned. Chosen
by the team on 2026-10-16 from the runtime estimate alone.

**Consequences for the analysis (§3).** One primary comparison instead of eight, so Holm over a family
of one is the plain Welch test at alpha 0.05, and TOST runs at alpha 0.05 (was 0.05 / 8). Margin
(0.005), verdict rules and the MDE report are unchanged. `scripts/analyse_h1_confirmatory.py` is
updated accordingly in the same commit as this amendment.

**Data already produced.** Two epsilon-1 cells finished before the stop (seeds 100 and 101). They are
outside the amended design, were not opened, and are kept unanalysed in
`results/h1_confirmatory/_discarded_before_amendment/`.

**Not run, stated:** acs, bank and diabetes; epsilon 1 on every dataset. They remain open, with the
measured cost above.
