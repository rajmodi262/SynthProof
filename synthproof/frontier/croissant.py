"""Emit the Privacy Data Sheet as a Croissant record carrying a DP vocabulary extension.

WHY THIS EXISTS. The novelty protocol (`research/08_novelty_verdict.md`) killed eight of this
project's claims, including "shipping a structured privacy label" (Dibia, Lu, Bhattacharjee,
Near & Feng, arXiv 2507.15997, 2025 — expert-elicited, nine categories) and "a machine-checkable
release artefact" (Croissant, an MLCommons standard and a NeurIPS Datasets & Benchmarks
submission requirement). What survived is narrower and is a claim about INTEGRATION:

  * Croissant has the ecosystem, the provenance model (W3C PROV-O) and the tooling, and
    carries **no attestation** — nothing in the specification signs a claim or binds it to an
    issuer.
  * Dibia et al. elicited the field set a DP release should disclose and propose **no signing**
    and **no standard for reporting the limits of an empirical privacy metric** — an omission
    one of their own experts called "privacy theater".
  * We have both of those and no ecosystem.

This module is the join. It does not invent a metadata standard; it takes the one the field
already uses and adds the two things it lacks, so a DP synthetic release can be consumed by
ordinary Croissant tooling AND checked by a third party holding only a public key.

WHAT IT DOES NOT DO, stated because a reader who sees "signed Croissant" will assume more:

  * It does **not** re-sign the Croissant document. The Ed25519 signature covers the data
    sheet's own canonical bytes (`PrivacyDataSheet.signing_payload`). Re-serialising those
    fields into JSON-LD would change the bytes and break the signature, so the sheet is
    embedded **verbatim** under `dp:privacyDataSheet` and verification runs against the
    original payload. The Croissant record therefore *carries* a signed claim rather than
    being one.
  * Consequently the JSON-LD framing, the `@context` and the record-set descriptions are
    **outside** the signature. Anyone can edit them. That is exactly why `verify_croissant`
    cross-checks every mirrored field against the signed sheet and refuses on any divergence
    (see `MIRRORED_FIELDS`); without that check, a reader could be shown a false epsilon in
    the human-visible layer above a signature that still verified.
  * It does not validate against the official MLCommons validator at runtime. `mlcroissant`
    pulls a dependency tree we refused for the same reason `anonymeter` was refused — it
    conflicts with the numpy >= 2 that `jax`/`mbi`/private-PGM (and therefore real AIM)
    require. Conformance is checked structurally here by `validate_structure`, and against
    the real validator out-of-band in an isolated environment by
    `scripts/validate_croissant.py`. An unrun check must never look like a passed one.

NO NEW RUNTIME DEPENDENCIES. A Croissant record is a dict. Adding a package that breaks the
project's flagship mechanism in order to emit one would repeat a mistake this repository has
already made once and recorded.

References fetched during the novelty protocol:
  * Croissant 1.1 — https://docs.mlcommons.org/croissant/ (extensible by referencing external
    vocabularies at dataset, field and data level; PROV-O for chain of custody; no signing,
    checksums-as-attestation or cryptographic verification described).
  * Dibia et al., arXiv 2507.15997 (2025).
  * Song, Sarathy, Shoemate & Vadhan, CSCW 2024 (arXiv 2410.09721) — practitioners do not
    verify DP guarantees. The premise under the whole exercise.
"""

import json
import re
from typing import Any, Dict, List, Optional

from synthproof.ledger import signing

# The Croissant version this emitter targets. Declared in the record as `conformsTo` so a
# consumer can reject it rather than guess.
CROISSANT_VERSION = "http://mlcommons.org/croissant/1.1"

# Our DP vocabulary. Croissant's documented extension route is to reference an external
# vocabulary by namespace rather than to add terms to the core context, so every field this
# module introduces is prefixed `dp:` and every one of them resolves under this IRI.
#
# The IRI is a project namespace, not a registered vocabulary, and is named as such in the
# emitted record's `dp:vocabularyStatus`. Claiming otherwise would be the same defect as a
# class called `AIMGenerator` that ran independent histograms.
DP_NAMESPACE = "https://github.com/rajmodi262/SynthProof/vocab/dp#"

# Fields duplicated from the signed sheet into the human-visible Croissant layer, mapped
# `croissant key -> data sheet key`. Every one of these is re-checked at verification time.
#
# THIS IS THE SECURITY-RELEVANT PART OF THE MODULE. The signature covers the embedded sheet,
# not the layer above it. A record whose `dp:epsilonProved` said 0.5 above an embedded sheet
# saying 7.36 would verify by signature alone while telling a reader the opposite of the truth
# — a signed lie assembled entirely out of honest parts. Any field mirrored upward must appear
# here, or it is unchecked.
MIRRORED_FIELDS: Dict[str, str] = {
    "dp:epsilonProved": "total_proved_eps",
    "dp:epsilonAudited": "total_audited_eps",
    "dp:delta": "delta",
    "dp:auditCeiling": "audit_ceiling",
    # The ceiling is meaningless without the series it came from: at m=800 the paired
    # Clopper-Pearson ceiling is 5.377 and the one-run one is 5.586, and the GDP ceiling is in
    # mu rather than epsilon. Mirroring these three makes a reader able to check which.
    "dp:auditEstimator": "audit_estimator",
    "dp:auditBudget": "audit_budget",
    "dp:auditAlpha": "audit_alpha",
    "dp:mechanism": "mechanism",
    "dp:unitOfPrivacy": "unit_of_privacy",
    "dp:contributionBound": "contribution_bound",
    "dp:deploymentModel": "deployment_model",
    "dp:domainSource": "domain_source",
    "dp:ledgerHash": "ledger_hash",
    "dp:inputFingerprint": "input_fingerprint",
}

# The official Croissant JSON-LD @context, reproduced verbatim from `mlcroissant`'s
# `_src/core/rdf.py::make_context()` (checked against the installed reference implementation on
# 2026-08-23), plus our two extension prefixes.
#
# It is copied rather than imported for the dependency reason in the module docstring, and it
# is copied WHOLE rather than trimmed to the terms we use: mlcroissant compares the record's
# context keys against this set and warns "the JSON-LD @context is not standard" on any that
# are missing, even for terms the record never mentions. A partial context validates but is
# not interoperable, and a warning a reader has to learn to ignore is worse than no warning.
#
# `dp:` is ours (see DP_NAMESPACE). `prov:` is W3C PROV-O, which Croissant's own extension
# guidance names for chain-of-custody.
STANDARD_CONTEXT: Dict[str, Any] = {
    "@language": "en",
    "@vocab": "https://schema.org/",
    "citeAs": "cr:citeAs",
    "column": "cr:column",
    "conformsTo": "dct:conformsTo",
    "cr": "http://mlcommons.org/croissant/",
    "data": {"@id": "cr:data", "@type": "@json"},
    "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
    "dct": "http://purl.org/dc/terms/",
    "dp": DP_NAMESPACE,
    # These three are declared JSON LITERALS (`@type: @json`), the same treatment Croissant
    # gives its own `data` and `examples` terms. Two reasons, and the first is correctness
    # rather than convenience:
    #
    #   1. `dp:privacyDataSheet` is the exact byte sequence the Ed25519 signature covers.
    #      Expanding it into RDF triples would model it as an unordered set of statements,
    #      which is precisely what it is not -- the signature is over a canonical, ordered
    #      serialisation. It is an opaque attested payload, not graph data.
    #   2. Without this, the reference validator recurses infinitely on it. An empty JSON
    #      object anywhere inside the sheet -- `evaluation: {}` on a release with no utility
    #      evaluation, which is a perfectly ordinary sheet -- drives
    #      `mlcroissant._src.core.json_ld.recursively_populate_jsonld` past the recursion
    #      limit. Found on 2026-08-23 by validating a sheet whose `evaluation` was empty; the
    #      first record we validated happened to have a populated one, so it passed.
    "dp:privacyDataSheet": {"@id": "dp:privacyDataSheet", "@type": "@json"},
    "dp:accountantAgreement": {"@id": "dp:accountantAgreement", "@type": "@json"},
    "dp:preflightFindings": {"@id": "dp:preflightFindings", "@type": "@json"},
    "equivalentProperty": "cr:equivalentProperty",
    "examples": {"@id": "cr:examples", "@type": "@json"},
    "extract": "cr:extract",
    "field": "cr:field",
    "fileObject": "cr:fileObject",
    "fileProperty": "cr:fileProperty",
    "fileSet": "cr:fileSet",
    "format": "cr:format",
    "includes": "cr:includes",
    "isLiveDataset": "cr:isLiveDataset",
    "jsonPath": "cr:jsonPath",
    "key": "cr:key",
    "md5": "cr:md5",
    "parentField": "cr:parentField",
    "path": "cr:path",
    "prov": "http://www.w3.org/ns/prov#",
    "rai": "http://mlcommons.org/croissant/RAI/",
    "recordSet": "cr:recordSet",
    "references": "cr:references",
    "regex": "cr:regex",
    "repeated": "cr:repeated",
    "replace": "cr:replace",
    "samplingRate": "cr:samplingRate",
    "sc": "https://schema.org/",
    "separator": "cr:separator",
    "source": "cr:source",
    "subField": "cr:subField",
    "transform": "cr:transform",
}

# Croissant requires `name` to be a token, not a sentence.
_NAME_RE = re.compile(r"[^a-zA-Z0-9\-_\.]+")

_CITATION = "SynthProof: Synthetic Data That Ships With Its Proof (MIT-WPU, 2026)."


class CroissantError(Exception):
    """Raised when a record cannot be emitted, or fails structural or cross-check validation."""


def _slug(text: str) -> str:
    """A Croissant-legal `name`. Empty input is an error, not a silent default."""
    cleaned = _NAME_RE.sub("-", str(text)).strip("-")
    if not cleaned:
        raise CroissantError(
            f"Cannot derive a Croissant-legal name from {text!r}. Croissant requires "
            "`name` to match [a-zA-Z0-9\\-_.]+; supply a dataset name that contains at "
            "least one such character."
        )
    return cleaned


def _sheet_to_dict(sheet: Any) -> Dict[str, Any]:
    """Accepts a `PrivacyDataSheet` or an already-parsed dict, and returns the dict."""
    if isinstance(sheet, dict):
        return dict(sheet)
    if hasattr(sheet, "to_dict"):
        return sheet.to_dict()
    raise CroissantError(
        f"Expected a PrivacyDataSheet or a parsed sheet dict, got {type(sheet).__name__}."
    )


def _audit_note(sheet: Dict[str, Any]) -> str:
    """The sentence that stops an audited epsilon being read as reassurance.

    This is S1 from the novelty verdict — the surviving claim — and it is the reason this
    record is worth emitting at all. Dibia et al.'s label proposes empirical privacy metrics
    and no way to report their operating range; one of their experts named that gap as
    "privacy theater". This field is that missing report, and it travels inside the record.

    We found the hazard the hard way: H1 reported an audited epsilon of 0.000 against a
    ceiling of 2.97 and a proved epsilon of 7.36. The instrument could not have returned
    anything else — the gap was guaranteed before any mechanism ran.
    """
    ceiling = sheet.get("audit_ceiling")
    proved = sheet.get("total_proved_eps")
    audited = sheet.get("total_audited_eps")

    if ceiling is None:
        return (
            "NOT REPORTED. This release does not state the operating range of its empirical "
            "privacy measurement, so the audited epsilon below cannot be interpreted: a low "
            "value may mean little leakage, or may mean the auditor could not have detected "
            "any. Do not read it as reassurance."
        )

    if proved is not None and ceiling < proved:
        return (
            f"UNINFORMATIVE. The auditor's ceiling is {ceiling:.3f} — the largest epsilon this "
            f"canary count could certify even against a release that was 100% verbatim "
            f"training data — while the proved epsilon is {proved:.3f}. The audited value of "
            f"{audited if audited is None else f'{audited:.3f}'} is therefore the instrument "
            "reading its own floor, NOT evidence that the mechanism leaks less than it is "
            "permitted to. Certifying an epsilon costs canaries exponential in that epsilon "
            "(Steinke, Nasr & Jagielski, NeurIPS 2023, Thm 2.1). Auditing catches broken "
            "implementations; it does not confirm tight ones."
        )

    return (
        f"INFORMATIVE. The auditor's ceiling is {ceiling:.3f}, at or above the proved epsilon "
        f"of {proved:.3f}, so the audited value below was measurable in principle and carries "
        "evidential weight."
    )


def to_croissant(
    sheet: Any,
    *,
    data_url: Optional[str] = None,
    license_url: str = "https://spdx.org/licenses/MIT.html",
    version: str = "1.0.0",
    columns: Optional[List[Dict[str, Any]]] = None,
    date_published: Optional[str] = None,
    data_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """Builds a Croissant 1.1 record carrying the signed Privacy Data Sheet.

    Args:
        sheet: A `PrivacyDataSheet`, or a sheet already parsed from JSON.
        data_url: Where the synthetic CSV can be fetched. Omitted rather than faked when
            unknown — a `contentUrl` pointing nowhere is worse than an absent one.
        license_url: SPDX URL for the release licence.
        version: Release version string.
        columns: Optional `[{"name": ..., "dataType": ...}, ...]` describing the released
            table, used to build the Croissant `recordSet`. When absent the record set is
            omitted and `validate_structure` says so.

    Returns:
        A JSON-serialisable dict.

    Raises:
        CroissantError: if the sheet is unsigned. An unsigned sheet inside a record that
            advertises attestation is precisely the confusion this module exists to prevent,
            so it is refused rather than emitted with a warning.
    """
    d = _sheet_to_dict(sheet)

    if not d.get("signature"):
        raise CroissantError(
            "Refusing to emit: this Privacy Data Sheet is unsigned.\n"
            "The only thing this record adds over a plain Croissant record is that the "
            "privacy claim inside it is attributable and tamper-evident. Emitting an "
            "unsigned sheet under a `dp:` vocabulary that advertises attestation would "
            "make the record claim more than it can support.\n"
            "Fix: run `synthproof run ... --sign`, or sign the sheet with "
            "`synthproof.ledger.signing.sign_datasheet`."
        )

    # An empirical epsilon with no operating range is not a weaker result, it is an unreadable
    # one -- and this record is the point at which it would leave the project. `audit_ceiling`
    # alone will not do: three ceiling series live in this repo, in two units, and a reader who
    # cannot tell which one produced the number cannot check it. Refuse rather than emit.
    if d.get("total_audited_eps") is not None:
        missing = [
            k
            for k in ("audit_ceiling", "audit_estimator", "audit_budget", "audit_alpha")
            if d.get(k) is None
        ]
        if missing:
            raise CroissantError(
                f"Refusing to emit: this sheet reports dp:epsilonAudited = "
                f"{d['total_audited_eps']} but is missing {', '.join(missing)}.\n"
                "A reader cannot tell an audited 0.0 that means 'nothing leaked' from an "
                "audited 0.0 that means 'the instrument could not have seen anything'. This "
                "project published exactly that confusion once: eps_audited 0.000 against "
                "eps_proved 7.36, where 60 canaries capped the auditor at 2.97.\n"
                "Fix: derive the ceiling with "
                "`synthproof.audit.ceiling.ceiling_for(estimator, budget, alpha)` and set "
                "audit_estimator / audit_budget / audit_alpha on the sheet before signing."
            )

    name = _slug(d.get("dataset_name") or "synthproof-release")
    mechanism = d.get("mechanism", "unknown")

    record: Dict[str, Any] = {
        "@context": dict(STANDARD_CONTEXT),
        "@type": "sc:Dataset",
        "conformsTo": CROISSANT_VERSION,
        "name": name,
        "description": (
            f"Differentially private synthetic tabular data generated from {d.get('dataset_name')} "
            f"by the {mechanism} mechanism, released with a signed Privacy Data Sheet that "
            f"reports both the proved epsilon and the operating range of the empirical audit "
            f"that accompanies it."
        ),
        "license": license_url,
        "version": version,
        # `citeAs` is Croissant's term; `citation` is the schema.org property the reference
        # validator recommends. Both carry the same string rather than one being derived from
        # the other, so neither can drift.
        "citeAs": _CITATION,
        "citation": _CITATION,
        # ---- PROV-O provenance ------------------------------------------------------------
        # Croissant's documented chain-of-custody route. `wasDerivedFrom` carries the input
        # fingerprint rather than the input itself: the point of the release is that the
        # source table is not shipped.
        "prov:wasGeneratedBy": {
            "@type": "prov:Activity",
            "prov:used": {
                "@type": "prov:Entity",
                "dp:inputFingerprintSha256": d.get("input_fingerprint"),
            },
            "dp:mechanism": mechanism,
            "dp:mechanismAvailable": d.get("mechanism_available"),
            "dp:seed": d.get("seed"),
            "dp:numRows": d.get("num_rows"),
        },
    }

    # Omitted rather than defaulted to "now". The library has no business inventing a
    # publication date for a release it is only serialising; a caller that knows the date
    # supplies it. `validate_structure` reports the absence rather than letting it pass silently.
    if date_published:
        record["datePublished"] = date_published

    # ---- the DP extension -----------------------------------------------------------------
    # Mirrored upward for a human reader and for ordinary Croissant tooling that will not know
    # to look inside `dp:privacyDataSheet`. Every one of these is cross-checked at verification
    # against the signed copy; see MIRRORED_FIELDS.
    for croissant_key, sheet_key in MIRRORED_FIELDS.items():
        record[croissant_key] = d.get(sheet_key)

    record["dp:vocabularyStatus"] = (
        "PROJECT NAMESPACE, NOT A REGISTERED VOCABULARY. The dp: terms in this record are "
        "defined by this project and are not part of Croissant, schema.org or any standards "
        "body's vocabulary. They follow Croissant 1.1's documented extension route "
        "(referencing an external vocabulary by namespace) but carry no external authority."
    )

    # S1, the surviving claim, as a first-class field rather than a footnote.
    record["dp:auditInterpretation"] = _audit_note(d)
    record["dp:auditIsInformative"] = (
        d.get("audit_ceiling") is not None
        and d.get("total_proved_eps") is not None
        and d["audit_ceiling"] >= d["total_proved_eps"]
    )
    record["dp:attacksRun"] = d.get("attacks_run", [])
    record["dp:attacksNotImplemented"] = d.get("attacks_not_implemented", [])
    record["dp:residualRisk"] = d.get("residual_risk", [])
    record["dp:accountantAgreement"] = d.get("accountant_agreement")
    record["dp:preflightFindings"] = d.get("preflight_findings", [])

    # ---- the attestation ------------------------------------------------------------------
    record["dp:privacyDataSheet"] = d
    record["dp:signature"] = {
        "@type": "dp:Ed25519Signature",
        "dp:algorithm": "Ed25519",
        "dp:publicKeyHex": d.get("public_key"),
        "dp:signatureHex": d.get("signature"),
        "dp:covers": (
            "The `dp:privacyDataSheet` node of this record, serialised as JSON with sorted "
            "keys and separators (',', ':'), excluding its own `signature` and `public_key` "
            "members. It does NOT cover the JSON-LD framing, the @context, or any dp: field "
            "outside that node."
        ),
        "dp:verifyWith": "synthproof verify <this-file> --pubkey <public-key>",
        "dp:proves": (
            "That this privacy claim was produced by the holder of the named key and has not "
            "been altered since. It does NOT prove the epsilon is correct, that the mechanism "
            "is sound, or that the audit was run honestly."
        ),
    }

    # ---- distribution and record set ------------------------------------------------------
    # A `recordSet` whose fields carry no `source` is INVALID Croissant -- the reference
    # validator rejects it ("does not define `source` or `value`"), and it was rejecting ours
    # until this was fixed. So the record set is emitted only alongside a file object for its
    # fields to point at. `data_url` may be a relative path: the record is meant to sit next
    # to the CSV it describes.
    file_id = f"{name}-data"
    if data_url:
        # Croissant requires a FileObject to carry `md5` or `sha256`, and rejects the record
        # otherwise. Emitting an invalid record would be bad enough; emitting a release
        # artefact that names a data file nobody can check against the claim would defeat the
        # point of signing the claim at all. So this refuses rather than degrades.
        if not data_sha256:
            raise CroissantError(
                f"Refusing to emit: `data_url` was given ({data_url!r}) with no `data_sha256`.\n"
                "Croissant requires every FileObject to carry a checksum, and a record that "
                "points at a data file without one lets the file be swapped for another "
                "while the signed privacy claim still verifies.\n"
                "Fix: pass data_sha256=hashlib.sha256(path.read_bytes()).hexdigest()."
            )
        record["distribution"] = [
            {
                "@type": "cr:FileObject",
                "@id": file_id,
                "name": file_id,
                "description": "The synthetic table this privacy claim describes.",
                "contentUrl": data_url,
                "encodingFormat": "text/csv",
                **({"sha256": data_sha256} if data_sha256 else {}),
            }
        ]

        if columns:
            record["recordSet"] = [
                {
                    "@type": "cr:RecordSet",
                    "@id": f"{name}-records",
                    "name": f"{name}-records",
                    "description": ("Synthetic records. No row corresponds to a real individual."),
                    "field": [
                        {
                            "@type": "cr:Field",
                            "@id": f"{name}-records/{_slug(col['name'])}",
                            "name": _slug(col["name"]),
                            "description": f"Synthetic values for {col['name']}.",
                            "dataType": col.get("dataType", "sc:Text"),
                            "source": {
                                "fileObject": {"@id": file_id},
                                "extract": {"column": str(col["name"])},
                            },
                        }
                        for col in columns
                    ],
                }
            ]
    elif columns:
        # Asked to describe columns with nowhere to source them from. Emitting an invalid
        # record set would be worse than emitting none, and silently dropping the request
        # would hide the reason, so it is recorded in the record itself.
        record["dp:recordSetOmitted"] = (
            "Column descriptors were supplied but no `data_url` was, and a Croissant field "
            "must reference the file it comes from. Pass the released CSV's path or URL to "
            "get a loadable record set."
        )

    return record


def validate_structure(record: Dict[str, Any]) -> List[str]:
    """Checks the record against what Croissant 1.1 requires, with no external dependency.

    Returns a list of human-readable problems; empty means it passed every check this
    function performs.

    THIS IS NOT THE OFFICIAL VALIDATOR and must never be described as one. It checks the
    required top-level properties, the `conformsTo` declaration, name legality and the
    internal consistency of the DP extension. `mlcroissant` checks considerably more.
    Run `scripts/validate_croissant.py` for that, in an isolated environment.
    """
    problems: List[str] = []

    for required in ("@context", "@type", "name", "description", "conformsTo"):
        if not record.get(required):
            problems.append(f"missing required property `{required}`")

    if record.get("@type") != "sc:Dataset":
        problems.append(f"`@type` must be `sc:Dataset`, got {record.get('@type')!r}")

    if record.get("conformsTo") != CROISSANT_VERSION:
        problems.append(
            f"`conformsTo` must be {CROISSANT_VERSION!r}, got {record.get('conformsTo')!r}"
        )

    name = record.get("name")
    if name and _NAME_RE.search(str(name)):
        problems.append(f"`name` {name!r} contains characters Croissant does not allow")

    ctx = record.get("@context") or {}
    if isinstance(ctx, dict):
        if ctx.get("dp") != DP_NAMESPACE:
            problems.append("`@context` does not bind the `dp:` prefix to the DP vocabulary")
        if "cr" not in ctx:
            problems.append("`@context` does not bind the `cr:` (Croissant) prefix")
    else:
        problems.append("`@context` must be an object")

    if not record.get("dp:privacyDataSheet"):
        problems.append("no `dp:privacyDataSheet` — this is not a SynthProof release record")
    if not (record.get("dp:signature") or {}).get("dp:signatureHex"):
        problems.append("`dp:signature` carries no signature")

    if record.get("dp:auditCeiling") is None:
        problems.append(
            "`dp:auditCeiling` is absent. The audited epsilon in this record cannot be "
            "interpreted without it"
        )

    if "recordSet" not in record:
        problems.append(
            "NOTE: no `recordSet`. The record is valid but describes no columns, so "
            "Croissant tooling cannot load the table from it"
        )

    if not record.get("datePublished"):
        problems.append(
            "NOTE: no `datePublished`. The reference validator recommends it; pass "
            "`date_published=` rather than letting the emitter invent one"
        )

    return problems


def verify_croissant(
    record: Dict[str, Any],
    public_key: Optional[Any] = None,
    key_path: Optional[Any] = None,
) -> bool:
    """Verifies a Croissant record: signature over the embedded sheet, then the mirrored fields.

    Two checks, and the second is the one that is easy to forget:

      1. The Ed25519 signature over `dp:privacyDataSheet` verifies against the supplied key.
         Delegated to `signing.verify_datasheet`, so there is one implementation of this and
         not two.
      2. Every field mirrored into the human-visible layer still agrees with the signed copy.
         The signature does not cover that layer. Without this check a record could carry a
         valid signature over a truthful sheet while displaying a different epsilon to anyone
         who read the record rather than the embedded node — which is what a reader, and every
         piece of general-purpose Croissant tooling, will actually do.

    Returns:
        True. Failure raises, so a caller cannot mistake a falsy return for a passing check —
        the same convention as `signing.verify_datasheet`.

    Raises:
        CroissantError: no embedded sheet, or a mirrored field diverges.
        signing.SignatureError: the signature is absent, malformed, or does not verify.
    """
    sheet = record.get("dp:privacyDataSheet")
    if not isinstance(sheet, dict):
        raise CroissantError(
            "This record carries no `dp:privacyDataSheet`, so there is nothing to verify. "
            "It may be an ordinary Croissant record rather than a SynthProof release."
        )

    signing.verify_datasheet(sheet, public_key=public_key, key_path=key_path)

    divergent: List[str] = []
    for croissant_key, sheet_key in MIRRORED_FIELDS.items():
        if croissant_key not in record:
            continue
        shown = record[croissant_key]
        signed = sheet.get(sheet_key)
        if shown != signed:
            divergent.append(
                f"  {croissant_key}: record says {shown!r}, signed sheet says {signed!r}"
            )

    if divergent:
        raise CroissantError(
            "SIGNATURE VALID, RECORD UNTRUSTWORTHY.\n"
            "The embedded Privacy Data Sheet is correctly signed, but the human-visible "
            "fields above it have been altered and no longer match it. The signature does "
            "not cover those fields. Trust the signed sheet; do not trust this record.\n"
            + "\n".join(divergent)
        )

    return True


def to_json(record: Dict[str, Any]) -> str:
    """Serialises a record for writing to disk."""
    return json.dumps(record, indent=2, sort_keys=False, ensure_ascii=False)


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
