"""Pre-flight checks that refuse a release before any sensitive value is read.

WHY THIS EXISTS. A system that always succeeds is lying somewhere. Before this module, a table
whose first column was a unique patient identifier ran to completion and emitted a signed
Privacy Data Sheet — and real identifiers appeared verbatim in the synthetic output, because a
value present in exactly one record can clear the profiler's category threshold. The pipeline
had no notion of an input it should decline.

THE DESIGN CONSTRAINT, and it is the whole difficulty. A check that reads the data to decide
whether the data is safe is the defect it is meant to prevent: counting distinct values in a
column is a query against sensitive records, and its answer ("column 7 looks like an
identifier") is exactly the kind of statement DP exists to bound. So **every check here reads
only the declared schema and the row count**. Nothing in this module touches a cell.

That has a consequence worth stating plainly rather than engineering around: a caller who
declares a careless schema gets a careless answer. Refusals are only as good as the public
metadata, and the honest response is to say so in the report rather than to reach for the data.

ONE ASYMMETRY. When the schema came from `Schema.infer_nonprivate`, its category lists were
read out of the table, so a check over them is transitively data-dependent. That does not make
the check *worse* — the non-private read already happened, and the whole path is marked as such
— but it does mean a refusal on an inferred schema is not evidence of a private pipeline. The
report records which case applied via `domain_source`.
"""

from dataclasses import asdict, dataclass
from typing import List, Optional

from synthproof.data.schema import Schema

# A table smaller than this cannot support a useful release at any epsilon anyone would accept:
# the noise needed to protect one record among a few hundred swamps the signal. The figure is a
# judgement call, not a theorem, and is stated as such in the refusal message.
MIN_ROWS = 500

# A categorical column whose declared domain covers this fraction of the rows or more is an
# identifier in all but name. At 1.0 every record has its own level.
NEAR_UNIQUE_FRACTION = 0.5

# Above this many declared levels a column behaves like free text for a marginal-based
# mechanism: every marginal touching it is mostly empty cells.
FREE_TEXT_LEVELS = 200

# Largest product of categorical domain sizes a 2-way marginal may span before the junction
# tree becomes the binding constraint. Chosen to match the ACS coarsening target.
MAX_PAIRWISE_CELLS = 5_000


@dataclass(frozen=True)
class Finding:
    """One reason the release should be refused or qualified."""

    code: str  # R1..R10, matching docs/design/USER_FACING_SYSTEM.md §2.5
    severity: str  # "refuse" | "warn"
    column: Optional[str]
    reason: str
    remedy: str

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        where = f" [{self.column}]" if self.column else ""
        return f"{self.code} {self.severity.upper()}{where}: {self.reason}\n    -> {self.remedy}"


class PreflightRefused(ValueError):
    """Raised when the input must not be released. Carries the findings."""

    def __init__(self, findings: List[Finding]):
        self.findings = findings
        blocking = [f for f in findings if f.severity == "refuse"]
        super().__init__(
            f"{len(blocking)} blocking issue(s) with this input:\n\n"
            + "\n\n".join(str(f) for f in blocking)
        )


def preflight(
    schema: Optional[Schema],
    num_rows: int,
    *,
    schema_declared: bool = True,
    contribution_bound: int = 1,
) -> List[Finding]:
    """Checks an input using ONLY public metadata. Never reads a cell.

    Args:
        schema: The public schema. `None` means no metadata at all, which is itself refusable.
        num_rows: Row count. Already known to the caller and reported in the data sheet.
        schema_declared: False when the schema came from `infer_nonprivate`.
        contribution_bound: Declared maximum rows per person.

    Returns:
        Findings, worst first. Callers decide whether to raise; `enforce()` does it for them.
    """
    out: List[Finding] = []

    if schema is None:
        out.append(
            Finding(
                "R0",
                "refuse",
                None,
                "No schema was supplied, so there is no public domain to release against.",
                "Supply a schema with `--schema`. `synthproof infer-schema` writes a starter, "
                "but every bound in it must be replaced with a publishable fact before use.",
            )
        )
        return out

    # ---- R1: too few rows -------------------------------------------------
    if num_rows < MIN_ROWS:
        out.append(
            Finding(
                "R1",
                "refuse",
                None,
                f"{num_rows} rows is below the {MIN_ROWS}-row floor. Protecting one record "
                "among this few requires noise that leaves nothing to release; the output "
                "would be noise carrying a certificate.",
                f"Use at least {MIN_ROWS} rows, or accept that this table cannot be released "
                "under differential privacy at any epsilon worth claiming.",
            )
        )

    cats = [schema[c] for c in schema.categorical]

    # ---- R4: no categorical column ---------------------------------------
    if not cats:
        out.append(
            Finding(
                "R4",
                "refuse",
                None,
                "No categorical column, so there is no target for the utility evaluation.",
                "Declare at least one categorical column, or use the library API directly if "
                "you want synthesis without a utility measurement.",
            )
        )

    for spec in cats:
        levels = len(spec.categories) if spec.categories else None

        # ---- R2: near-unique -> a direct identifier ----------------------
        if levels is not None and num_rows > 0 and levels >= NEAR_UNIQUE_FRACTION * num_rows:
            out.append(
                Finding(
                    "R2",
                    "refuse",
                    spec.name,
                    f"Declared domain has {levels} levels over {num_rows} rows "
                    f"({levels / num_rows:.0%} of the table). A column with roughly one level "
                    "per record is a direct identifier; releasing its domain releases the "
                    "individuals.",
                    f"Drop {spec.name!r}, or replace it with a coarser public grouping "
                    "(a region instead of a postcode, an age band instead of a birth date).",
                )
            )
        # ---- R3: free text ------------------------------------------------
        elif levels is not None and levels > FREE_TEXT_LEVELS:
            out.append(
                Finding(
                    "R3",
                    "refuse",
                    spec.name,
                    f"Declared domain has {levels} levels. Beyond a few hundred, a column "
                    "behaves like free text: every marginal touching it is mostly empty, and "
                    "rare levels carry individual records.",
                    f"Coarsen {spec.name!r} against a published code book — the ACS loader "
                    "does this for occupation (529 codes -> 25 groups) at no privacy cost — "
                    "or drop the column.",
                )
            )
        # ---- R3b: categorical with no declared domain --------------------
        elif levels is None:
            out.append(
                Finding(
                    "R3",
                    "refuse",
                    spec.name,
                    "Categorical column with no declared domain, so the level set can only "
                    "come from the data.",
                    f"Declare the public domain for {spec.name!r}: "
                    "ColumnSpec(name, CATEGORICAL, categories=[...]).",
                )
            )

    # ---- R5: pairwise domain blow-up -------------------------------------
    sized = [(s.name, len(s.categories)) for s in cats if s.categories]
    worst = None
    for i, (n1, k1) in enumerate(sized):
        for n2, k2 in sized[i + 1 :]:
            if worst is None or k1 * k2 > worst[2]:
                worst = (n1, n2, k1 * k2)
    if worst and worst[2] > MAX_PAIRWISE_CELLS:
        out.append(
            Finding(
                "R5",
                "refuse",
                f"{worst[0]} x {worst[1]}",
                f"The largest 2-way marginal spans {worst[2]:,} cells. A tree- or "
                "graph-structured mechanism must materialise it, and the noise per cell makes "
                "it uninformative long before memory does.",
                f"Coarsen {worst[0]!r} or {worst[1]!r} so the product stays under "
                f"{MAX_PAIRWISE_CELLS:,}.",
            )
        )

    # ---- R9: contribution bound ------------------------------------------
    if contribution_bound != 1:
        sev = "refuse" if contribution_bound < 1 else "warn"
        out.append(
            Finding(
                "R9",
                sev,
                None,
                f"Declared contribution bound is {contribution_bound} rows per person. The "
                "accountant charges add/remove-ONE-record, so a person contributing k rows "
                "receives a guarantee weaker by a factor of k.",
                "Either pre-process to one row per person, or read the reported epsilon as "
                f"{contribution_bound}x larger for anyone contributing that many rows.",
            )
        )

    # ---- R8: inferred schema ---------------------------------------------
    if not schema_declared:
        out.append(
            Finding(
                "R8",
                "warn",
                None,
                "The schema was inferred from the data, so its bounds and category domains "
                "are themselves functions of the sensitive table and were not charged.",
                "For a release anyone else will rely on, declare the schema. This run is "
                "marked `domain_source=inferred-nonprivate` in the data sheet.",
            )
        )

    order = {"refuse": 0, "warn": 1}
    return sorted(out, key=lambda f: (order[f.severity], f.code))


def enforce(
    schema: Optional[Schema],
    num_rows: int,
    *,
    schema_declared: bool = True,
    contribution_bound: int = 1,
) -> List[Finding]:
    """Runs `preflight` and raises `PreflightRefused` if anything blocks. Returns warnings."""
    findings = preflight(
        schema,
        num_rows,
        schema_declared=schema_declared,
        contribution_bound=contribution_bound,
    )
    if any(f.severity == "refuse" for f in findings):
        raise PreflightRefused(findings)
    return findings
