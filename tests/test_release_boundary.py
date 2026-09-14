"""Every artefact a release produces must be consistent with the add/remove-one guarantee.

docs/design/PUBLIC_RELEASE_BOUNDARY.md. A release used to hand the standard DP adversary -- who
knows every record but one -- four tests for the remaining record that no epsilon covered:

  D2  the exact row count: in the sheet, in the synthetic table's length, and in the refusal gate;
  D3  an unkeyed SHA-256 of the input table;
  D4  measurements on the real table, released without saying so;
  D5  the run seed, which replays every noise draw. Measured before the fix, not argued:
      research/release_boundary/seed_replay_probe.json -- 15 of 15 releases reproduced exactly
      from the true table and 0 of 15 from its neighbour.
"""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner

from synthproof.data.dataset import TabularDataset
from synthproof.data.preflight import MIN_ROWS, PreflightRefused
from synthproof.data.schema import CATEGORICAL, NUMERICAL, ColumnSpec, Schema
from synthproof.frontier import croissant as croissant_mod
from synthproof.frontier.certificate import EVALUATION_PRIVACY, FrontierEngine, input_fingerprint
from synthproof.frontier.experiment import MECHANISMS, run_cell
from synthproof.frontier.release_size import DP_COUNT_FRAC, dp_count
from synthproof.ledger import signing

# --------------------------------------------------------------------------- fixtures


def _table(n: int, seed: int = 0) -> TabularDataset:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "age": rng.integers(18, 90, n).astype(float),
            "region": rng.choice(list("abcdefgh"), n),
            "dx": rng.choice(["x", "y", "z"], n),
        }
    )
    schema = Schema(
        [
            ColumnSpec("age", NUMERICAL, lower=0.0, upper=120.0),
            ColumnSpec("region", CATEGORICAL, categories=list("abcdefgh")),
            ColumnSpec("dx", CATEGORICAL, categories=["x", "y", "z"]),
        ]
    )
    return TabularDataset(df, name="boundary", schema=schema)


def _neighbours(n: int = 1200):
    """A table and the same table with one record removed."""
    d = _table(n)
    dprime = TabularDataset(d.df.drop(index=0).reset_index(drop=True), name=d.name, schema=d.schema)
    return d, dprime


def _sweep(ds: TabularDataset, seed: int = 3, **kw):
    kw.setdefault("eps_grid", [1.0])
    kw.setdefault("mechanism", "independent")
    kw.setdefault("num_canaries", 10)
    engine = FrontierEngine(seed=seed)
    return engine, engine.run_sweep(ds, **kw)


@pytest.fixture
def keys(tmp_path, monkeypatch):
    """A throwaway signing key and fingerprint key, isolated from the repository's `.keys/`."""
    monkeypatch.setenv("SYNTHPROOF_KEY_DIR", str(tmp_path / "keys"))
    signing.generate_keypair()
    return signing.load_fingerprint_key(create=True)


def _plain_hash(df: pd.DataFrame) -> str:
    """What the sheet used to publish: an unkeyed SHA-256 of the input table."""
    content = pd.util.hash_pandas_object(df, index=False).values.tobytes()  # type: ignore[union-attr]
    return hashlib.sha256(content).hexdigest()


# --------------------------------------------------------------------------- D2: the row count


def test_neighbouring_tables_release_the_same_size():
    """Size independence. Before the fix both numbers were the table's own length, so these two
    releases differed by exactly the record whose presence DP is meant to hide."""
    d, dprime = _neighbours()
    ea, a = _sweep(d, release_rows=700, retain_release=True)
    eb, b = _sweep(dprime, release_rows=700, retain_release=True)

    assert a.num_rows == b.num_rows == 700
    assert ea.last_release is not None and eb.last_release is not None
    assert len(ea.last_release) == len(eb.last_release) == 700
    assert a.release_rows_source == b.release_rows_source == "declared"


def test_without_a_declaration_the_size_is_a_charged_noisy_count():
    """`dp_count` is charged: the proved epsilon is the release's own plus the count's, and the
    release is run on what is left, so the total is what was asked for."""
    d = _table(1200)
    _, sheet = _sweep(d, eps_grid=[2.0])

    assert sheet.release_rows_source == "dp_count"
    assert sheet.release_rows_eps == pytest.approx(DP_COUNT_FRAC * 2.0)
    cell = run_cell(
        d,
        "independent",
        2.0 - sheet.release_rows_eps,
        seed=3,
        num_canaries=10,
        release_rows=sheet.num_rows,
    )
    assert sheet.total_proved_eps == pytest.approx(cell["proved_eps"] + sheet.release_rows_eps)


def test_the_noisy_count_is_not_the_exact_count():
    """At eps = 0.04 the noise scale is 25 rows; an exact answer should be rare, not routine."""
    sizes = [dp_count(1200, 0.04, seed=s).rows for s in range(20)]
    assert sum(r != 1200 for r in sizes) >= 18, sizes


def test_the_gate_judges_the_public_size_not_the_table():
    """The R1 floor compared the EXACT count with 500, so a refusal near it announced n. It now sees
    only the public size: a short table with a large declaration passes, and a long table with a
    small declaration is refused."""
    _sweep(_table(300), release_rows=MIN_ROWS)

    with pytest.raises(PreflightRefused) as refused:
        _sweep(_table(3000), release_rows=MIN_ROWS - 1)
    assert "R1" in str(refused.value)


# --------------------------------------------------------------------------- D3: the fingerprint


def test_no_artefact_carries_an_unkeyed_hash_of_the_input(keys):
    d = _table(1200)
    _, sheet = _sweep(d, release_rows=800, fingerprint_key=keys)
    signing.sign_datasheet(sheet)
    record = croissant_mod.to_croissant(sheet)

    published = sheet.to_json() + json.dumps(record)
    assert _plain_hash(d.df) not in published
    assert sheet.input_fingerprint == input_fingerprint(d.df, keys)
    assert "dp:inputFingerprintHmacSha256" in published
    assert "dp:inputFingerprintSha256" not in published


def test_the_fingerprint_needs_the_key():
    d, other = _table(1200), _table(1200, seed=1)
    k1, k2 = b"\x01" * 32, b"\x02" * 32

    assert input_fingerprint(d.df, k1) == input_fingerprint(d.df, k1)
    assert input_fingerprint(d.df, k1) != input_fingerprint(d.df, k2)
    assert input_fingerprint(d.df, k1) != input_fingerprint(other.df, k1)

    _, sheet = _sweep(d, release_rows=800)
    assert sheet.input_fingerprint is None, "no key must mean no fingerprint, not a plain hash"


def test_a_fingerprint_key_is_created_once_and_never_replaced(tmp_path):
    assert signing.load_fingerprint_key(tmp_path) is None
    key = signing.load_fingerprint_key(tmp_path, create=True)
    assert key is not None and len(key) == 32
    assert signing.load_fingerprint_key(tmp_path, create=True) == key

    (tmp_path / signing.FINGERPRINT_KEY_NAME).write_bytes(b"short")
    with pytest.raises(ValueError, match="at least 32"):
        signing.load_fingerprint_key(tmp_path)


# --------------------------------------------------------------------------- D4: disclosure


def test_the_evaluation_is_labelled_outside_epsilon_inside_the_signature(keys):
    _, sheet = _sweep(_table(1200), release_rows=800, fingerprint_key=keys)
    signing.sign_datasheet(sheet)

    payload = sheet.signing_payload().decode("utf-8")
    assert '"evaluation_privacy"' in payload and '"release_rows_source"' in payload
    assert sheet.evaluation_privacy == EVALUATION_PRIVACY
    assert any("evaluation_privacy" in item for item in sheet.residual_risk)

    record = croissant_mod.to_croissant(sheet)
    assert record["dp:evaluationPrivacy"] == EVALUATION_PRIVACY
    assert record["dp:releaseRowsSource"] == "declared"


# --------------------------------------------------------------------------- D5: the seed


def test_a_published_seed_would_decide_membership():
    """The premise for withholding the seed, pinned so it cannot quietly stop being true.

    Same public size, same seed: the true table reproduces the release exactly and its neighbour
    does not. If this ever stops holding, the release has stopped being a deterministic function
    of (table, seed), and the reasoning in D5 needs revisiting rather than silently weakening.
    """
    d, dprime = _neighbours()

    def release(ds):
        engine, _ = _sweep(ds, seed=11, release_rows=800, retain_release=True)
        return engine.last_release

    published = release(d)
    assert release(d).equals(published)
    assert not release(dprime).equals(published)


def test_no_artefact_carries_the_seed(keys):
    _, sheet = _sweep(_table(1200), seed=987654321, release_rows=800, fingerprint_key=keys)
    signing.sign_datasheet(sheet)
    record = croissant_mod.to_croissant(sheet)

    assert sheet.seed is None
    assert "dp:seed" not in json.dumps(record)
    assert "987654321" not in sheet.to_json() + json.dumps(record)


def test_an_engine_without_a_seed_draws_a_fresh_full_width_one():
    seeds = {FrontierEngine().seed for _ in range(8)}
    assert len(seeds) == 8
    # All eight below 2**32 has probability 2**-248 for a 63-bit draw.
    assert max(seeds) >= 2**32


@pytest.mark.parametrize("mechanism", sorted(MECHANISMS))
def test_every_mechanism_runs_with_a_full_width_seed(mechanism):
    """REGRESSION. The evaluators pass their seed to NumPy's legacy generator and scikit-learn,
    which reject anything above 32 bits, so a secret 63-bit seed crashed every mechanism; DP-VAE
    also overflowed building its JAX key.

    Driven through `run_cell`, not `run_sweep`, so that DP-VAE's separate accountant disagreement
    (pinned below) cannot mask a seed failure."""
    res = run_cell(_table(900), mechanism, 1.0, seed=2**63 - 1, num_canaries=10, release_rows=600)
    assert res["proved_eps"] > 0


@pytest.mark.xfail(
    strict=True,
    reason="OPEN (2026-09-14): for DP-VAE the two accountants disagree -- dp_accounting 0.94 vs "
    "autodp 2.45 at 900 rows and 9.50 at 3000, with seeds 3 and 2**63-1 alike -- so run_sweep "
    "refuses the release. Not caused by the release-boundary change; under investigation. Strict, "
    "so resolving it fails this marker and forces the finding to be written up.",
)
def test_a_dpvae_release_passes_the_differential_accountant():
    from synthproof.accounting.differential import AccountantDisagreement

    try:
        _sweep(_table(900), mechanism="dpvae", release_rows=600)
    except AccountantDisagreement as exc:
        pytest.fail(str(exc))


def test_dpvae_keys_keep_the_high_bits_of_the_seed():
    jax = pytest.importorskip("jax")
    from synthproof.generators.dpvae import _prng_key

    def data(k):
        return np.asarray(jax.random.key_data(k))

    # JAX alone collapses these two seeds to one key when x64 is off.
    assert not np.array_equal(data(_prng_key(2**40 + 7)), data(_prng_key(2**40 + 2**33 + 7)))
    # A research seed keeps exactly the key it always had.
    assert np.array_equal(data(_prng_key(3)), data(jax.random.PRNGKey(3)))


# --------------------------------------------------------------------------- the CLI


def _csv(tmp_path, n=900):
    rng = np.random.default_rng(0)
    path = tmp_path / "in.csv"
    pd.DataFrame(
        {
            "age": rng.integers(18, 90, n),
            "hours": rng.integers(1, 60, n),
            "grp": rng.choice(list("abcd"), n),
            "label": rng.choice(["yes", "no"], n),
        }
    ).to_csv(path, index=False)
    return path


def test_cli_run_publishes_a_declared_size_and_no_seed(tmp_path, keys):
    from synthproof.cli import main

    out = tmp_path / "sheet.json"
    args = ["run", "--input", str(_csv(tmp_path)), "--out", str(out), "--eps", "1.0"]
    r = CliRunner().invoke(main, [*args, "--release-rows", "600", "--sign"])
    assert r.exit_code == 0, r.output

    sheet = json.loads(out.read_text(encoding="utf-8"))
    assert sheet["num_rows"] == 600
    assert sheet["release_rows_source"] == "declared"
    assert sheet["seed"] is None
    assert sheet["input_fingerprint"] is not None, "--sign beside a key must fingerprint, keyed"


def test_cli_run_without_a_declaration_charges_a_count(tmp_path, keys):
    from synthproof.cli import main

    out = tmp_path / "sheet.json"
    args = ["run", "--input", str(_csv(tmp_path)), "--out", str(out), "--eps", "1.0"]
    r = CliRunner().invoke(main, args)
    assert r.exit_code == 0, r.output

    sheet = json.loads(out.read_text(encoding="utf-8"))
    assert sheet["release_rows_source"] == "dp_count"
    assert sheet["release_rows_eps"] == pytest.approx(DP_COUNT_FRAC * 1.0)
    assert sheet["seed"] is None
