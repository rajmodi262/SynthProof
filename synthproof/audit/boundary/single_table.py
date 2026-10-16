"""Single-table release-boundary checks (RB1-RB10): channels a sheet can leak through
outside its epsilon."""

from typing import Any, List, Mapping

from synthproof.audit.boundary._types import (
    _HEX64,
    _SOUND_DOMAIN_SOURCES,
    LEAK,
    NOTE,
    UNVERIFIABLE,
    BoundaryFinding,
    _number,
)


def _seed(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    # An explicit null is a statement ("withheld"); a missing key is silence. SynthProof's own
    # sheets always carry the key, but a sheet transcribed from someone else's documentation
    # (scripts/run_real_release_study.py) has it only when the documentation addresses it, and
    # reading silence as "withheld" would credit a release with a property nobody stated.
    if "seed" not in sheet:
        return [
            BoundaryFinding(
                "RB1",
                UNVERIFIABLE,
                "seed",
                "The artefact does not say whether the run seed or random numbers are withheld.",
                "If the seed were published or derivable, the release would be a deterministic "
                "function of the table and membership could be decided by replay.",
                "State that the randomness is withheld (seed: null), as a published claim.",
            )
        ]
    seed = sheet.get("seed")
    if seed is None:
        return [
            BoundaryFinding(
                "RB1",
                NOTE,
                "seed",
                "The run seed is withheld.",
                "Nobody outside the curator can replay the noise, so the release is not a "
                "deterministic function of the table for a reader.",
                "None. Keep the seed with the curator if it is kept at all.",
            )
        ]
    return [
        BoundaryFinding(
            "RB1",
            LEAK,
            "seed",
            f"The sheet publishes the run seed ({seed}).",
            "Every noise draw derives from the seed, so the release is a deterministic function of "
            "(table, seed). A reader who knows every other record rebuilds it for both candidate "
            "tables and sees which one matches: membership decided with certainty, whatever "
            "epsilon says. Measured on this project's own releases: 15 of 15.",
            "Withhold the seed. Draw it from the operating system; if it must be kept for "
            "reproducibility, keep it with the curator and never in the artefact.",
        )
    ]


def _row_count(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    n = sheet.get("num_rows")
    source = sheet.get("release_rows_source")
    if n is None and source is None:
        return []  # no size is published, so there is no size channel to check
    if source in (None, "unknown"):
        return [
            BoundaryFinding(
                "RB2",
                LEAK,
                "num_rows",
                f"num_rows = {n} is published with no stated basis (no release_rows_source).",
                "Under add/remove-one the exact row count is private: two neighbouring tables "
                "differ in length by one. A size with no stated basis has to be read as the "
                "input's exact count.",
                "Release a size declared before the data is read, or a charged noisy count, and "
                "record which in release_rows_source.",
            )
        ]
    if source == "dp_count":
        cost = _number(sheet.get("release_rows_eps")) or 0.0
        if cost <= 0:
            return [
                BoundaryFinding(
                    "RB2",
                    LEAK,
                    "release_rows_eps",
                    "num_rows is called a noisy count, but no epsilon is recorded for it.",
                    "An uncharged count is not a DP count. The size may be exact, or its cost may "
                    "be missing from total_proved_eps.",
                    "Record the count's epsilon and include it in the proved total.",
                )
            ]
        return [
            BoundaryFinding(
                "RB2",
                NOTE,
                "num_rows",
                f"num_rows = {n} is a noisy count costing epsilon {cost:g}, stated as included "
                "in total_proved_eps.",
                "The size is covered by the guarantee, provided the stated cost was really "
                "charged.",
                "None.",
            )
        ]
    if source in ("declared", "protocol"):
        return [
            BoundaryFinding(
                "RB2",
                UNVERIFIABLE,
                "num_rows",
                f"num_rows = {n} is {source}: fixed before the data was read, by the producer's "
                "account.",
                "Nothing in the artefact can show the number was not read off the table. A "
                "declared size that happens to equal the input's length leaks it.",
                "Rely on it only if the curator's declaration process is trusted.",
            )
        ]
    return [
        BoundaryFinding(
            "RB2",
            LEAK,
            "release_rows_source",
            f"release_rows_source = {source!r} is not a recognised basis.",
            "An unrecognised basis gives no reason to believe the size is public.",
            "Use declared, protocol or dp_count.",
        )
    ]


_UNKEYED_SCHEMES = ("sha256", "sha-256", "unkeyed", "plain")
_KEYED_SCHEMES = ("hmac-sha256", "hmac", "hmac-sha-256")


def _fingerprint(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    fp = sheet.get("input_fingerprint")
    if not fp:
        return []

    # A declared scheme is the checkable path (added 2026-09-17). The old heuristic could only
    # ever say "unverifiable" for a keyed fingerprint, because a plain SHA-256 and an HMAC are
    # both 64 hex characters. A producer that DECLARES the scheme -- and, in a signed sheet,
    # binds that declaration under the signature -- turns the guess into something a reader can
    # act on: a self-declared unkeyed hash is a self-declared membership test (LEAK), and a
    # declared HMAC with a named key is a claim the producer cannot later repudiate (NOTE).
    scheme = sheet.get("fingerprint_scheme")
    if scheme is not None:
        s = str(scheme).lower()
        if s in _UNKEYED_SCHEMES:
            return [
                BoundaryFinding(
                    "RB3",
                    LEAK,
                    "fingerprint_scheme",
                    f"The sheet declares its input fingerprint is {scheme!r} -- an unkeyed hash.",
                    "By the producer's own declaration this is a deterministic function of the "
                    "input table: a reader who knows every other record hashes both candidate "
                    "tables and compares. A membership test no epsilon covers.",
                    "Switch to an HMAC under a curator secret (fingerprint_scheme='hmac-sha256' "
                    "with a fingerprint_key_id), or omit the fingerprint.",
                )
            ]
        if s in _KEYED_SCHEMES:
            key_id = sheet.get("fingerprint_key_id")
            if key_id:
                return [
                    BoundaryFinding(
                        "RB3",
                        NOTE,
                        "fingerprint_scheme",
                        f"The fingerprint is declared {scheme!r} under key {key_id!r}.",
                        "A keyed fingerprint is not a membership test for a reader without the "
                        "key. The named key binds the claim: in a signed sheet the producer "
                        "cannot later deny the fingerprint was keyed, so this is checkable "
                        "accountability rather than a guess (it does not verify the bytes).",
                        "None. Keep the key secret; publish only its id/commitment.",
                    )
                ]
            return [
                BoundaryFinding(
                    "RB3",
                    UNVERIFIABLE,
                    "fingerprint_scheme",
                    f"The fingerprint is declared {scheme!r} but no fingerprint_key_id is given.",
                    "A keyed scheme with no named key is not bound to anything -- nothing stops "
                    "the value being an unkeyed hash relabelled.",
                    "Publish a fingerprint_key_id (a public identifier or commitment for the "
                    "secret key), so the keyed claim is bound.",
                )
            ]
        return [
            BoundaryFinding(
                "RB3",
                UNVERIFIABLE,
                "fingerprint_scheme",
                f"fingerprint_scheme = {scheme!r} is not a recognised scheme.",
                "An unrecognised scheme gives no reason to believe the fingerprint is keyed.",
                "Use 'hmac-sha256' (keyed) or 'sha256' (unkeyed, and a leak).",
            )
        ]

    # No declared scheme: fall back to the legacy heuristic.
    legacy = sheet.get("release_rows_source") in (None, "unknown")
    if legacy and isinstance(fp, str) and _HEX64.match(fp):
        return [
            BoundaryFinding(
                "RB3",
                LEAK,
                "input_fingerprint",
                "A 64-hex input fingerprint is published by a producer that predates keyed "
                "fingerprints. Treat it as an unkeyed SHA-256 of the input table.",
                "A reader who knows every other record hashes both candidate tables and compares: "
                "a deterministic membership test that no epsilon covers.",
                "Publish an HMAC under a curator secret, or omit the field.",
            )
        ]
    return [
        BoundaryFinding(
            "RB3",
            UNVERIFIABLE,
            "input_fingerprint",
            "An input fingerprint is published with no declared scheme.",
            "A keyed HMAC and a plain SHA-256 look identical from outside. Only the producer's "
            "code decides whether this is a membership test.",
            "Declare fingerprint_scheme ('hmac-sha256' with a fingerprint_key_id), or omit it.",
        )
    ]


def _evaluation(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    has_measurements = bool(sheet.get("evaluation")) or sheet.get("total_audited_eps") is not None
    if not has_measurements:
        return []
    if sheet.get("evaluation_privacy"):
        return [
            BoundaryFinding(
                "RB4",
                NOTE,
                "evaluation_privacy",
                "Measurements on the real table are published and labelled as outside epsilon.",
                "They are non-private statistics of the input. The label stops a reader assuming "
                "epsilon covers them.",
                "None, beyond deciding whether they need publishing at all.",
            )
        ]
    return [
        BoundaryFinding(
            "RB4",
            LEAK,
            "evaluation",
            "Measurements computed on the real table (utility, membership-inference AUC, audited "
            "epsilon) are published with no statement that epsilon does not cover them.",
            "Each is a non-private statistic of the input, and a reader will reasonably assume the "
            "headline epsilon covers everything in the artefact.",
            "Label them outside epsilon in the artefact itself, or do not publish them.",
        )
    ]


def _domain(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    source = sheet.get("domain_source")
    if source == "inferred-nonprivate":
        return [
            BoundaryFinding(
                "RB6",
                LEAK,
                "domain_source",
                "Column bounds and category domains were read from the sensitive table and not "
                "charged.",
                "The domain itself is released outside the guarantee. A category present in one "
                "record announces that record.",
                "Declare the schema from public knowledge, or charge its construction.",
            )
        ]
    if source in _SOUND_DOMAIN_SOURCES:
        return []
    return [
        BoundaryFinding(
            "RB6",
            UNVERIFIABLE,
            "domain_source",
            f"How the domain was obtained is not stated (domain_source: {source or 'absent'}).",
            "Every epsilon in the artefact is conditional on a domain that may have leaked.",
            "State domain_source.",
        )
    ]


def _contribution(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    bound = sheet.get("contribution_bound", 1)
    if bound in (1, None):
        return []
    return [
        BoundaryFinding(
            "RB7",
            UNVERIFIABLE,
            "contribution_bound",
            f"Up to {bound} rows per person.",
            f"The guarantee is per record, so a person with {bound} rows is protected about "
            f"{bound} times less than epsilon suggests.",
            "Pre-process to one row per person, or read epsilon as a per-record figure.",
        )
    ]


_SOUND_DISCRETIZATION = ("uniform-public", "dp-charged", "declared", "not-applicable")


def _public_invariants(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    """RB8. Quantities the producer declares as published OUTSIDE epsilon (e.g. the 2020 Census
    invariants: exact state totals, structural zeros). A declared invariant with a stated basis is
    a sound outside-epsilon label; one without a basis reads like an uncharged private statistic."""
    inv = sheet.get("public_invariants")
    if not inv:
        return []
    items: List[Mapping[str, Any]]
    if isinstance(inv, Mapping):
        items = [{"name": k, "basis": v} for k, v in inv.items()]
    elif isinstance(inv, (list, tuple)):
        items = [x if isinstance(x, Mapping) else {"name": x, "basis": None} for x in inv]
    else:
        items = [{"name": str(inv), "basis": None}]
    missing = [str(i.get("name")) for i in items if not i.get("basis")]
    if missing:
        return [
            BoundaryFinding(
                "RB8",
                UNVERIFIABLE,
                "public_invariants",
                f"{len(missing)} invariant(s) declared outside epsilon with no stated basis: "
                f"{', '.join(missing)}.",
                "A quantity published outside the budget needs a reason (statutory, public "
                "aggregate, structural zero); without one a reader cannot tell a policy invariant "
                "from an uncharged private statistic.",
                "Give each public invariant a basis, e.g. 'statutory' or 'structural-zero'.",
            )
        ]
    names = ", ".join(str(i.get("name")) for i in items)
    return [
        BoundaryFinding(
            "RB8",
            NOTE,
            "public_invariants",
            f"{len(items)} quantity(ies) declared outside epsilon with a stated basis: {names}.",
            "They are labelled as published outside the budget by policy, so a reader will not "
            "mistake them for epsilon-covered outputs (cf. the 2020 Census invariants).",
            "None. The exact values still rest on the declaration; a private count also trips RB2.",
        )
    ]


def _discretization(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    """RB9. How continuous columns were binned. Bins read from the data (quantile, k-means) and not
    charged release the input distribution outside epsilon (Ganev et al., 2504.06923)."""
    src = sheet.get("discretization_source")
    if src is None:
        return []
    if src == "data-derived":
        return [
            BoundaryFinding(
                "RB9",
                LEAK,
                "discretization_source",
                "Bin edges were chosen from the sensitive data (e.g. quantile or k-means) and not "
                "charged.",
                "Data-derived bins release information about the input distribution outside "
                "epsilon; reading the binning off the data can break end-to-end DP.",
                "Use uniform bins over the public domain, or charge the discretiser (PrivTree).",
            )
        ]
    if src in _SOUND_DISCRETIZATION:
        return []
    return [
        BoundaryFinding(
            "RB9",
            UNVERIFIABLE,
            "discretization_source",
            f"discretization_source = {src!r} is not a recognised basis.",
            "An unrecognised basis gives no reason to believe the bins were public or charged.",
            "Use uniform-public, dp-charged, declared, or not-applicable.",
        )
    ]


def _amplification(sheet: Mapping[str, Any]) -> List[BoundaryFinding]:
    """RB10. If a release claims a smaller epsilon via amplification (subsampling, missingness), the
    assumption must be stated or the published epsilon is an unverifiable under-estimate (P7)."""
    amp = sheet.get("privacy_amplification")
    if not amp:
        return []
    basis = amp.get("basis") if isinstance(amp, Mapping) else None
    factor = amp.get("factor") if isinstance(amp, Mapping) else None
    if not basis:
        return [
            BoundaryFinding(
                "RB10",
                LEAK,
                "privacy_amplification",
                "The release claims amplified (smaller) epsilon but states no amplification basis.",
                "An amplification factor with no stated assumption (subsampling rate, MCAR "
                "missingness) cannot be checked, and a wrong assumption makes the published "
                "epsilon an under-estimate.",
                "State the basis and its assumption, e.g. 'poisson-subsampling q=0.01' or "
                "'mcar-missingness'.",
            )
        ]
    return [
        BoundaryFinding(
            "RB10",
            NOTE,
            "privacy_amplification",
            f"Epsilon is amplified (factor {factor}) on a stated basis: {basis}.",
            "The tighter epsilon rests on the stated assumption, which a reader can check.",
            "None, provided the assumption holds.",
        )
    ]
