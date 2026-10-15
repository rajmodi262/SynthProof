"""The weekly reproduction check flags a moved number, and only a moved number."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.compare_results import _diff  # noqa: E402


def diffs(a, b, rtol=1e-9, atol=1e-12):
    out: list = []
    _diff(a, b, "", rtol, atol, out)
    return out


def test_identical_results_reproduce():
    r = {"cells": [{"eps": 7.999622083248946, "n": 3, "label": "aim"}], "ok": True}
    assert diffs(r, r) == []


def test_a_moved_number_is_caught_at_its_path():
    a = {"cells": [{"eps": 7.999622083248946}]}
    b = {"cells": [{"eps": 7.999623083248946}]}
    assert diffs(a, b) == ["/cells[0]/eps: 7.999622083248946 -> 7.999623083248946"]


def test_a_difference_inside_tolerance_passes():
    assert diffs({"x": 1.0}, {"x": 1.0 + 1e-8}, rtol=1e-6) == []


def test_timing_fields_are_ignored():
    assert diffs({"elapsed_seconds": 37.4, "x": 1}, {"elapsed_seconds": 128.0, "x": 1}) == []


def test_added_removed_and_resized_are_reported():
    assert diffs({"a": 1}, {"b": 1}) == ["/a: removed", "/b: added"]
    assert diffs({"a": [1, 2]}, {"a": [1]}) == ["/a: length 2 -> 1"]


def test_a_bool_flip_is_not_mistaken_for_a_number():
    assert diffs({"confirmed": True}, {"confirmed": False}) == ["/confirmed: True -> False"]


def test_nan_matches_nan_but_not_a_number():
    nan = float("nan")
    assert diffs({"r": nan}, {"r": nan}) == []
    assert diffs({"r": nan}, {"r": 0.5}) != []
