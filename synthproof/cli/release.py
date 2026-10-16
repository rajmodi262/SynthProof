"""Making and checking a release: `run`, `keygen`, `verify`, `croissant`, `infer-schema`."""

import hashlib
import json
import secrets
from datetime import date
from pathlib import Path
from typing import Optional, Tuple

import click

from synthproof.cli import main
from synthproof.cli._common import _load, _validate_delta, _validate_eps
from synthproof.data.dataset import TabularDataset
from synthproof.data.preflight import PreflightRefused
from synthproof.data.schema import Schema
from synthproof.frontier import croissant as croissant_mod
from synthproof.frontier.certificate import FrontierEngine
from synthproof.frontier.experiment import MECHANISMS
from synthproof.ledger import signing


def _resolve_seed(seed: Optional[int]) -> int:
    """A secret OS seed unless one was given -- and a warning when one was."""
    if seed is None:
        click.echo("Noise seed drawn from the OS and kept secret; it is not written anywhere.")
        return secrets.randbits(63)
    click.echo(
        "  WARNING: --seed given. This release is only as private as that number is secret. "
        "The sheet does not record it; do not publish it."
    )
    return seed


def _report(datasheet, eps: float, canaries: int, out: Optional[str]) -> None:
    """Writes or prints the sheet, then the plain-language summary and its caveats."""
    text = datasheet.to_json()
    if out:
        Path(out).write_text(text, encoding="utf-8")
        click.echo(f"Privacy Data Sheet written to {out}")
    else:
        click.echo("=" * 60)
        click.echo("PRIVACY DATA SHEET")
        click.echo("=" * 60)
        click.echo(text)

    click.echo(
        f"\nRequested eps={eps:.3f}  ->  proved eps={datasheet.total_proved_eps:.3f}"
        f"  (ratio {datasheet.total_proved_eps / eps:.3f}; calibration never overspends)"
    )
    # Epsilon on its own is not interpretable. Nanayakkara et al. (USENIX Security 2023) found
    # odds-based explanations beat both example outputs and omitting epsilon entirely.
    click.echo(f"\n  {datasheet.plain_statement()}")

    if not datasheet.audit_is_informative():
        click.echo(
            f"  NOTE: the audit ceiling at {canaries} canaries is "
            f"{datasheet.audit_ceiling:.2f}, below the proved eps of "
            f"{datasheet.total_proved_eps:.2f}. An audited eps of "
            f"{datasheet.total_audited_eps:.2f} means the auditor COULD NOT have detected "
            "this budget -- not that nothing leaked."
        )
    if datasheet.domain_source == "inferred-nonprivate":
        click.echo(
            "  NOTE: domain_source=inferred-nonprivate. The bounds and category domains here "
            "were read from your data and were not charged. Declare a schema before anyone "
            "else relies on this sheet."
        )


def _write_table(
    engine, synthetic_out: Optional[str], croissant_out: Optional[str]
) -> Tuple[Optional[Path], Optional[str]]:
    """Writes the synthetic table; returns its path and SHA-256 (both None if not written).

    A Croissant record describes a distribution, so when one is requested the CSV is written
    beside it even if --synthetic-out was not given: a record pointing at a file that does not
    exist would be a claim about nothing.
    """
    data_path = Path(synthetic_out) if synthetic_out else None
    if croissant_out and data_path is None:
        data_path = Path(croissant_out).with_suffix(".csv")
    if data_path is None:
        return None, None
    if engine.last_release is None:
        raise click.ClickException(
            "The synthesis produced no retained release, so there is nothing to write. "
            "This is a bug: --synthetic-out/--croissant should have set retain_release."
        )
    engine.last_release.to_csv(data_path, index=False)
    click.echo(f"Synthetic table written to {data_path}  ({len(engine.last_release)} rows)")
    return data_path, hashlib.sha256(data_path.read_bytes()).hexdigest()


def _write_croissant(datasheet, ds, croissant_out: str, data_path, data_sha) -> None:
    try:
        record = croissant_mod.to_croissant(
            datasheet,
            columns=croissant_mod.columns_from_schema(ds.schema),
            data_url=data_path.name if data_path else None,
            data_sha256=data_sha,
            # The release is being produced now, so this is the genuine publication date
            # rather than a placeholder. The emitter itself never invents one.
            date_published=date.today().isoformat(),
        )
    except croissant_mod.CroissantError as exc:
        raise click.ClickException(str(exc)) from exc
    Path(croissant_out).write_text(croissant_mod.to_json(record), encoding="utf-8")
    click.echo(f"Croissant record written to {croissant_out}")
    for problem in croissant_mod.validate_structure(record):
        click.echo(f"  {problem}")


@main.command()
@click.option(
    "--input",
    "input_path",
    default=None,
    type=click.Path(exists=True),
    help="CSV file to synthesise. Omit to use the built-in toy table.",
)
@click.option(
    "--schema",
    "schema_path",
    default=None,
    type=click.Path(exists=True),
    help="Public schema JSON declaring column kinds and numeric bounds.",
)
@click.option(
    "--eps",
    default=1.0,
    callback=_validate_eps,
    help="Total privacy budget for the release. Must be > 0; warns above 10.",
)
@click.option(
    "--delta",
    default=1e-5,
    callback=_validate_delta,
    help="Target delta: the probability the epsilon bound fails. Must be in (0, 1).",
)
@click.option(
    "--mechanism",
    default="pairwise",
    type=click.Choice(sorted(MECHANISMS)),
    help="Generator to use. `synthproof mechanisms` lists what is available.",
)
@click.option("--rows", default=100, help="Rows for the toy table when --input is omitted.")
@click.option(
    "--seed",
    type=int,
    default=None,
    help="Noise seed. Leave it out and a secret one is drawn. Anyone who learns the seed can "
    "replay the release and test whether a record was in the input, so it is never written to "
    "the sheet.",
)
@click.option(
    "--release-rows",
    "release_rows",
    type=click.IntRange(min=1),
    default=None,
    help="Rows to release, declared in advance. Left out with --input, a small share of the "
    "budget buys a noisy row count instead, because the exact count is private.",
)
@click.option(
    "--target",
    "target_col",
    default=None,
    help="Categorical column the utility evaluation predicts. Omitted: `income` if present, "
    "else the table's last categorical column.",
)
@click.option("--canaries", default=30, help="Canaries planted for the audit.")
@click.option(
    "--sign/--no-sign",
    default=False,
    help="Sign the data sheet with the persistent key (see `synthproof keygen`).",
)
@click.option(
    "--out", default=None, type=click.Path(), help="Write the Privacy Data Sheet JSON here."
)
@click.option(
    "--synthetic-out",
    "synthetic_out",
    default=None,
    type=click.Path(),
    help="Write the synthetic table itself here as CSV. This is the release.",
)
@click.option(
    "--croissant",
    "croissant_out",
    default=None,
    type=click.Path(),
    help="Also emit a Croissant 1.1 record carrying the signed sheet. Requires --sign.",
)
def run(
    input_path,
    schema_path,
    eps,
    delta,
    mechanism,
    rows,
    seed,
    canaries,
    sign,
    out,
    synthetic_out,
    croissant_out,
    release_rows,
    target_col,
):
    """Synthesises a dataset and emits its Privacy Data Sheet."""
    seed = _resolve_seed(seed)
    # The toy generator needs a 32-bit seed. Its table is public test data either way.
    ds, domain_source = _load(input_path, schema_path, rows, seed % (2**32))
    if input_path is None and release_rows is None:
        # The toy table has exactly --rows rows, a number the operator chose, so it is public.
        release_rows = rows
    # Created only beside a signing key that exists: a key directory is the operator's to set up.
    key_ready = sign and (signing.resolve_key_dir() / signing.PRIVATE_KEY_NAME).exists()
    fingerprint_key = signing.load_fingerprint_key(create=key_ready)

    from synthproof.frontier.experiment import default_target

    try:
        # Validated before any budget is spent, so a typo costs nothing.
        target_col = default_target(ds, target_col)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Utility is evaluated by predicting '{target_col}'.")
    click.echo(f"Synthesising at total eps={eps} (delta={delta}) with '{mechanism}'...")
    try:
        engine = FrontierEngine(seed=seed)
        datasheet = engine.run_sweep(
            ds,
            retain_release=bool(synthetic_out or croissant_out),
            eps_grid=[eps],
            delta=delta,
            mechanism=mechanism,
            num_canaries=canaries,
            domain_source=domain_source,
            release_rows=release_rows,
            fingerprint_key=fingerprint_key,
            target_col=target_col,
        )
    except PreflightRefused as exc:
        # A refusal is an outcome, not a crash. Show every blocking reason and its remedy.
        raise click.ClickException(str(exc)) from exc

    if sign:
        try:
            signing.sign_datasheet(datasheet)
            click.echo("Signed with the persistent Ed25519 key.")
        except FileNotFoundError as exc:
            raise click.ClickException(str(exc)) from exc

    _report(datasheet, eps, canaries, out)
    data_path, data_sha = _write_table(engine, synthetic_out, croissant_out)
    if croissant_out:
        _write_croissant(datasheet, ds, croissant_out, data_path, data_sha)
    if not sign:
        click.echo("This sheet is UNSIGNED. Re-run with --sign to make it verifiable.")


def _rotate(key_dir: Optional[Path], ledger_db: Optional[str]) -> None:
    """Rotates the signing key and, if given, re-signs a ledger under it -- ledger first checked."""
    from synthproof.ledger.ledger import Ledger

    ledger = None
    if ledger_db:
        # Verify under the CURRENT key before anything changes: a ledger that does not verify
        # must not be re-signed into one that does.
        ledger = Ledger(
            db_path=ledger_db,
            private_key=signing.load_private_key(
                (key_dir or signing.resolve_key_dir()) / signing.PRIVATE_KEY_NAME
            ),
        )
        ok, reason = ledger.verify_with_reason()
        if not ok:
            raise click.ClickException(
                f"The ledger does not verify, so it was not rotated: {reason}"
            )
    try:
        old_fp, new_fp = signing.rotate_keypair(key_dir)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Rotated signing key {old_fp} -> {new_fp}.")
    click.echo(
        f"  The old public key is kept in retired/{old_fp}.pub; its private key is destroyed."
    )
    if ledger is not None:
        ledger.rotate_key(
            signing.load_private_key(
                (key_dir or signing.resolve_key_dir()) / signing.PRIVATE_KEY_NAME
            )
        )
        click.echo(
            f"  Re-signed {len(ledger.get_entries())} ledger entries and the head; it verifies."
        )


@main.command()
@click.option(
    "--key-dir",
    default=None,
    type=click.Path(),
    help="Where to write the keypair. Defaults to .keys/",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Replace an existing key. Every signature it made becomes unverifiable.",
)
@click.option(
    "--rotate",
    is_flag=True,
    help="Replace the key, keeping the old PUBLIC key in retired/ so earlier sheets still verify.",
)
@click.option(
    "--ledger",
    "ledger_db",
    default=None,
    type=click.Path(exists=True, dir_okay=False),
    help="With --rotate: a file-backed ledger to re-sign under the new key (it is verified first).",
)
def keygen(key_dir, overwrite, rotate, ledger_db):
    """Creates the persistent Ed25519 signing key, or rotates it.

    Set SYNTHPROOF_KEY_PASSPHRASE (or SYNTHPROOF_KEY_PASSPHRASE_FILE) first to have the private
    key encrypted at rest.
    """
    if rotate:
        _rotate(Path(key_dir) if key_dir else None, ledger_db)
        return
    if ledger_db:
        raise click.UsageError("--ledger only applies with --rotate.")
    kwargs = {"overwrite": overwrite}
    if key_dir:
        kwargs["key_dir"] = Path(key_dir)
    try:
        priv, pub = signing.generate_keypair(**kwargs)
    except FileExistsError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Private key: {priv}   (keep secret; .keys/ is gitignored)")
    click.echo(f"Public key:  {pub}    (publish this)")
    click.echo(
        "\nAnyone with the public key can now check a signed data sheet:\n"
        f"    synthproof verify sheet.json --pubkey {pub}"
    )


@main.command()
@click.argument("datasheet", type=click.Path(exists=True))
@click.option(
    "--pubkey",
    required=True,
    type=click.Path(exists=True),
    help="The public key you expect the sheet to be signed with.",
)
def verify(datasheet, pubkey):
    """Verifies a signed Privacy Data Sheet. Needs only this file and a public key.

    This is the command a third party runs. It checks that the sheet was signed by the key
    you supply and has not been altered since. It does NOT check that the epsilon is correct
    or that the audit was run honestly — a key holder can sign wrong numbers.
    """
    doc = json.loads(Path(datasheet).read_text(encoding="utf-8"))

    # A Croissant record carries the sheet under `dp:privacyDataSheet`. Detect it rather than
    # making the reader remember which of two commands to run, and verify the mirrored fields
    # as well as the signature -- the signature does not cover them.
    is_croissant = isinstance(doc.get("dp:privacyDataSheet"), dict)
    sheet = doc["dp:privacyDataSheet"] if is_croissant else doc

    try:
        if is_croissant:
            croissant_mod.verify_croissant(doc, key_path=Path(pubkey))
        else:
            signing.verify_datasheet(sheet, key_path=Path(pubkey))
    except (signing.SignatureError, croissant_mod.CroissantError) as exc:
        click.echo(click.style("FAILED", fg="red", bold=True))
        click.echo(str(exc))
        raise SystemExit(1) from exc

    click.echo(click.style("VERIFIED", fg="green", bold=True))
    if is_croissant:
        click.echo("  format       Croissant 1.1 record with DP vocabulary extension")
        click.echo("               signature and all mirrored fields agree with the signed sheet")
    click.echo(f"  dataset      {sheet.get('dataset_name')}  ({sheet.get('num_rows')} rows)")
    click.echo(f"  mechanism    {sheet.get('mechanism')}")
    click.echo(f"  eps proved   {sheet.get('total_proved_eps')}")
    click.echo(f"  eps audited  {sheet.get('total_audited_eps')}")
    click.echo(f"  ledger head  {sheet.get('ledger_hash', '')[:24]}...")
    click.echo(
        "\nThis proves the sheet came from the holder of that key and is unaltered.\n"
        "It does not prove the numbers in it are correct."
    )


@main.command("croissant")
@click.option(
    "--datasheet",
    required=True,
    type=click.Path(exists=True),
    help="A signed Privacy Data Sheet JSON.",
)
@click.option("--out", default=None, type=click.Path(), help="Write the Croissant record here.")
@click.option("--data-url", default=None, help="Where the synthetic CSV can be fetched.")
def croissant(datasheet, out, data_url):
    """Converts a signed Privacy Data Sheet into a Croissant 1.1 record.

    Croissant is the metadata standard ML datasets ship with and a NeurIPS Datasets &
    Benchmarks submission requirement. It carries provenance and no attestation. This wraps
    the signed sheet in one, so a DP release can be consumed by ordinary Croissant tooling
    and still be checked by a third party holding only a public key.

    The signature is NOT recomputed — it still covers the embedded sheet's own bytes. Fields
    mirrored into the visible layer are outside it, which is why `synthproof verify`
    cross-checks them.
    """
    sheet = json.loads(Path(datasheet).read_text(encoding="utf-8"))
    try:
        record = croissant_mod.to_croissant(sheet, data_url=data_url)
    except croissant_mod.CroissantError as exc:
        raise click.ClickException(str(exc)) from exc

    text = croissant_mod.to_json(record)
    if out:
        Path(out).write_text(text, encoding="utf-8")
        click.echo(f"Croissant record written to {out}")
    else:
        click.echo(text)

    problems = croissant_mod.validate_structure(record)
    if problems:
        click.echo("\nStructural check:")
        for problem in problems:
            click.echo(f"  {problem}")
    else:
        click.echo("\nStructural check passed.")
    click.echo(
        "This is not the official MLCommons validator. Run scripts/validate_croissant.py "
        "in an isolated environment for that."
    )


@main.command("infer-schema")
@click.option(
    "--input", "input_path", required=True, type=click.Path(exists=True), help="CSV to inspect."
)
@click.option("--out", default=None, type=click.Path(), help="Write the schema JSON here.")
def infer_schema(input_path, out):
    """Infers a starter schema from a CSV. Review the bounds before using it for a release.

    The bounds this produces are read from the data, so they leak. Treat the output as a
    template: replace each range with a bound that is publishable knowledge about the domain.
    """
    ds = TabularDataset.from_csv(input_path)
    schema = Schema.infer_nonprivate(ds.df)
    text = schema.to_json(out)

    if out:
        click.echo(f"Starter schema written to {out}")
    else:
        click.echo(text)
    click.echo("\nWARNING: these bounds were read from the data and therefore leak.")
    click.echo("Replace each range with a publishable fact about the domain before release.")
