"""W11: the real-release corpus is sourced cell by cell, and the committed study matches it."""

import copy
import json

from scripts.run_real_release_study import CORPUS, OUT, study, validate
from synthproof.audit.boundary import audit_sheet
from synthproof.audit.boundary._types import NOTE, UNVERIFIABLE


def _corpus():
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def test_every_coded_cell_cites_a_listed_source_with_evidence():
    assert validate(_corpus()) == []


def test_the_committed_results_are_what_the_corpus_produces():
    expected = json.dumps(study(_corpus()), indent=2) + "\n"
    assert (
        OUT.read_text(encoding="utf-8") == expected
    ), "run python -m scripts.run_real_release_study"


def test_a_documented_cell_without_a_source_is_refused():
    corpus = copy.deepcopy(_corpus())
    corpus["releases"][0]["properties"]["P10"] = {"status": "documented", "evidence": "trust me"}
    assert any("P10" in p for p in validate(corpus))


def test_a_source_without_a_fetch_date_is_refused():
    corpus = copy.deepcopy(_corpus())
    del corpus["releases"][0]["sources"][0]["fetched"]
    assert validate(corpus)


def test_silence_about_the_seed_is_not_read_as_withheld():
    (silent,) = [f for f in audit_sheet({"mechanism": "x"}).findings if f.code == "RB1"]
    (stated,) = [
        f for f in audit_sheet({"mechanism": "x", "seed": None}).findings if f.code == "RB1"
    ]
    assert silent.severity == UNVERIFIABLE and stated.severity == NOTE
