# Archive

Process records kept for history, moved out of `docs/` on 2026-10-16 so the live documentation is
what an examiner or a new contributor actually needs. Nothing here is current; where an archived
file and a live one disagree, the live one is right. Retracted claims in these files stay
retracted — see [`../CORRECTIONS.md`](../CORRECTIONS.md).

| File | What it was |
|---|---|
| [`docs/AGENT_HANDOFF.md`](docs/AGENT_HANDOFF.md) | Running handoff notes between AI-assisted work sessions |
| [`docs/AGENT_REPORT_2026-09.md`](docs/AGENT_REPORT_2026-09.md), [`docs/AGENT_REPORT_2026-09-FOLLOWUP.md`](docs/AGENT_REPORT_2026-09-FOLLOWUP.md) | September 2026 review reports and their follow-up |
| [`docs/ANTIGRAVITY_PROTOTYPE_BRIEF.md`](docs/ANTIGRAVITY_PROTOTYPE_BRIEF.md), [`docs/ANTIGRAVITY_PROTOTYPE_DESIGN_SPEC.md`](docs/ANTIGRAVITY_PROTOTYPE_DESIGN_SPEC.md), [`docs/ANTIGRAVITY_RESEARCH_BRIEF.md`](docs/ANTIGRAVITY_RESEARCH_BRIEF.md) | Briefs written for an external prototyping tool |
| [`docs/AUDIT_AND_ROADMAP.md`](docs/AUDIT_AND_ROADMAP.md), [`docs/ROAD_TO_TEN.md`](docs/ROAD_TO_TEN.md) | Earlier gap audits and roadmaps, superseded by the plan in the capstone folder and by `CORRECTIONS.md` |
| [`docs/PYTHON311_UPGRADE.md`](docs/PYTHON311_UPGRADE.md) | Notes from the Python 3.11 migration |
| [`docs/SYNOPSIS_RECONCILIATION.md`](docs/SYNOPSIS_RECONCILIATION.md) | Mapping between the original synopsis and what was built |
| [`docs/deck/PROMPT.md`](docs/deck/PROMPT.md) | The prompt used to draft an early slide deck |
| `web/pitch2/` … `web/pitch5/` | Four earlier variants of the browser pitch deck (August–September 2026). They predate the D1 re-run and are not kept building. The one maintained deck is [`web/pitch/`](../web/pitch/README.md), whose numbers are generated from `results/` |

## Live documentation

[README](../README.md) · [Architecture](../docs/ARCHITECTURE.md) · [Results](../results/RESULTS.md) ·
[Threat model](../docs/threat_model.md) · [Sensitivity](../docs/SENSITIVITY.md) ·
[Corrections](../CORRECTIONS.md) · [Demo](../DEMO.md) · [Thesis](../docs/thesis/README.md)

## Scripts

One-off analyses whose outputs are already recorded, kept so the record can be re-derived:
`archive/scripts/ab_mst_bank.py` (which audit-27 change moved MST on Bank),
`compare_audit27.py` and `fair_before_old_code.py` (the audit-27 before/after tables),
`mutation_probe.py` (a hand-rolled mutation probe, superseded by `scripts/mutation.sh`),
`gen_onepager.py`, `gen_layman_onepager.py`, `gen_umbrella.py` (one-page PDFs that embedded
numbers rather than generating them), `summarize_results.py` (an ad-hoc imputation summary).
They are not maintained and may not run against the current package.
