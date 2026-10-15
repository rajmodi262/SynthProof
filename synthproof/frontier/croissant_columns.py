"""Croissant field descriptions from a DataFrame or a public schema."""

from typing import Any, Dict, List

from synthproof.frontier.croissant_vocab import (  # noqa: F401  (re-exported for existing callers)
    _CITATION,
    _NAME_RE,
    CROISSANT_VERSION,
    DP_NAMESPACE,
    MIRRORED_FIELDS,
    STANDARD_CONTEXT,
)

# Pandas dtype kind -> schema.org type. Croissant's `dataType` is a vocabulary term, so an
# unrecognised dtype falls back to `sc:Text` rather than being guessed at.
_DTYPE_TO_CROISSANT = {
    "i": "sc:Integer",
    "u": "sc:Integer",
    "f": "sc:Float",
    "b": "sc:Boolean",
    "M": "sc:Date",
    "O": "sc:Text",
}


def columns_from_dataframe(df: Any) -> List[Dict[str, str]]:
    """Derives Croissant column descriptors from the RELEASED table.

    Read from the synthetic output, never from the private input. The distinction matters:
    column names and types taken from the sensitive table would be undeclared metadata of
    exactly the kind `domain_source` exists to flag. Taken from the release, they describe
    something already public — the CSV's own header row — and cost nothing.

    Returns `[{"name": ..., "dataType": ...}, ...]`.
    """
    return [
        {
            "name": str(col),
            "dataType": _DTYPE_TO_CROISSANT.get(df[col].dtype.kind, "sc:Text"),
        }
        for col in df.columns
    ]


def columns_from_schema(schema: Any) -> List[Dict[str, str]]:
    """Derives Croissant column descriptors from the DECLARED schema.

    This is what the CLI uses, because `run_sweep` returns a data sheet and not the synthetic
    frame. The schema is the right source anyway when `domain_source` is `declared` or
    `codebook`: it is a public statement about the domain, so nothing here is charged.

    When `domain_source` is `inferred-nonprivate` the schema's BOUNDS were read from the data
    — but only column names and kinds are used here, and both appear in the released CSV's own
    header. No bound, category list or range crosses into the record from this function.
    """
    # The constant is imported rather than compared against a literal. `ColumnSpec.kind` holds
    # "numerical"/"categorical" in lower case, and an earlier version of this function tested
    # against "NUMERICAL" -- which silently typed every numeric column as `sc:Text`, because a
    # mismatched comparison falls through to the else branch instead of failing.
    from synthproof.data.schema import NUMERICAL

    return [
        {
            "name": str(col.name),
            "dataType": "sc:Float" if col.kind == NUMERICAL else "sc:Text",
        }
        for col in schema.columns
    ]
