"""The Croissant 1.1 context, the DP vocabulary namespace, and which signed-sheet fields are
mirrored into the visible record."""

import re
from typing import Any, Dict

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
    # Why `dp:numRows` is a public number, and that the evaluation figures are NOT covered by the
    # proved epsilon. A record that showed the numbers without these would overstate them.
    # docs/design/PUBLIC_RELEASE_BOUNDARY.md, D2 and D4.
    "dp:releaseRowsSource": "release_rows_source",
    "dp:evaluationPrivacy": "evaluation_privacy",
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
