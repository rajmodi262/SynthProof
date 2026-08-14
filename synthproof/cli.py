"""SynthProof command line interface."""

import json
from pathlib import Path

import click

from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import Schema
from synthproof.frontier.certificate import FrontierEngine
from synthproof.frontier.experiment import MECHANISMS
from synthproof.ledger import signing


@click.group()
def main():
    """SynthProof — synthetic data that ships with its proof."""
    pass


def _load(input_path, schema_path, rows, seed):
    """Loads a dataset from CSV, or builds the toy table when no input is given."""
    if input_path is None:
        click.echo(f"No --input given; using the built-in toy table ({rows} rows).")
        click.echo("  NOTE: toy columns are independent, so utility numbers mean little.")
        return TabularDataset.create_synthetic_toy(num_rows=rows, seed=seed)

    schema = None
    if schema_path:
        schema = Schema.from_json(schema_path)
        click.echo(f"Loaded public schema: {len(schema)} columns from {schema_path}")
    else:
        click.echo("  WARNING: no --schema given. Column kinds and numeric bounds will be")
        click.echo("  inferred from the data, which is NOT safe for a real release.")

    ds = TabularDataset.from_csv(input_path, schema=schema)
    if schema is None:
        # Re-load through an inferred schema so numeric columns are still clipped to a
        # concrete range. That range is data-derived, hence the warning above.
        ds = TabularDataset(ds.df, name=ds.name, schema=Schema.infer_nonprivate(ds.df))
    click.echo(f"Loaded {ds.num_rows} rows x {ds.num_cols} columns from {input_path}")
    return ds


@main.command("mechanisms")
def list_mechanisms():
    """Lists the generators available in this environment."""
    click.echo("Available mechanisms:\n")
    for key in sorted(MECHANISMS):
        click.echo(f"  {key}")
    missing = {"aim"} - set(MECHANISMS)
    if missing:
        click.echo(
            f"\nUnavailable: {', '.join(sorted(missing))}\n"
            "  AIM needs private-pgm (package `mbi`), which requires Python >= 3.11.\n"
            "  See docs/PYTHON311_UPGRADE.md."
        )


@main.command()
@click.option("--input", "input_path", default=None, type=click.Path(exists=True),
              help="CSV file to synthesise. Omit to use the built-in toy table.")
@click.option("--schema", "schema_path", default=None, type=click.Path(exists=True),
              help="Public schema JSON declaring column kinds and numeric bounds.")
@click.option("--eps", default=1.0, help="Total privacy budget for the release.")
@click.option("--delta", default=1e-5, help="Target delta.")
@click.option("--mechanism", default="pairwise",
              type=click.Choice(sorted(MECHANISMS)),
              help="Generator to use. `synthproof mechanisms` lists what is available.")
@click.option("--rows", default=100, help="Rows for the toy table when --input is omitted.")
@click.option("--seed", default=42, help="Random seed.")
@click.option("--canaries", default=30, help="Canaries planted for the audit.")
@click.option("--sign/--no-sign", default=False,
              help="Sign the data sheet with the persistent key (see `synthproof keygen`).")
@click.option("--out", default=None, type=click.Path(),
              help="Write the Privacy Data Sheet JSON here.")
def run(input_path, schema_path, eps, delta, mechanism, rows, seed, canaries, sign, out):
    """Synthesises a dataset and emits its Privacy Data Sheet."""
    ds = _load(input_path, schema_path, rows, seed)

    click.echo(f"Synthesising at total eps={eps} (delta={delta}) with '{mechanism}'...")
    datasheet = FrontierEngine(seed=seed).run_sweep(
        ds, eps_grid=[eps], delta=delta, mechanism=mechanism, num_canaries=canaries
    )

    if sign:
        try:
            signing.sign_datasheet(datasheet)
            click.echo("Signed with the persistent Ed25519 key.")
        except FileNotFoundError as exc:
            raise click.ClickException(str(exc)) from exc

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
    if not sign:
        click.echo("This sheet is UNSIGNED. Re-run with --sign to make it verifiable.")


@main.command()
@click.option("--key-dir", default=None, type=click.Path(),
              help="Where to write the keypair. Defaults to .keys/")
@click.option("--overwrite", is_flag=True,
              help="Replace an existing key. Every signature it made becomes unverifiable.")
def keygen(key_dir, overwrite):
    """Creates the persistent Ed25519 signing key."""
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
@click.option("--pubkey", required=True, type=click.Path(exists=True),
              help="The public key you expect the sheet to be signed with.")
def verify(datasheet, pubkey):
    """Verifies a signed Privacy Data Sheet. Needs only this file and a public key.

    This is the command a third party runs. It checks that the sheet was signed by the key
    you supply and has not been altered since. It does NOT check that the epsilon is correct
    or that the audit was run honestly — a key holder can sign wrong numbers.
    """
    sheet = json.loads(Path(datasheet).read_text(encoding="utf-8"))
    try:
        signing.verify_datasheet(sheet, key_path=Path(pubkey))
    except signing.SignatureError as exc:
        click.echo(click.style("FAILED", fg="red", bold=True))
        click.echo(str(exc))
        raise SystemExit(1) from exc

    click.echo(click.style("VERIFIED", fg="green", bold=True))
    click.echo(f"  dataset      {sheet.get('dataset_name')}  ({sheet.get('num_rows')} rows)")
    click.echo(f"  mechanism    {sheet.get('mechanism')}")
    click.echo(f"  eps proved   {sheet.get('total_proved_eps')}")
    click.echo(f"  eps audited  {sheet.get('total_audited_eps')}")
    click.echo(f"  ledger head  {sheet.get('ledger_hash', '')[:24]}...")
    click.echo(
        "\nThis proves the sheet came from the holder of that key and is unaltered.\n"
        "It does not prove the numbers in it are correct."
    )


@main.command("infer-schema")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True),
              help="CSV to inspect.")
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


@main.command()
@click.option("--rows", default=100, help="Number of rows for the toy benchmark.")
@click.option("--eps", default=1.0, help="Target privacy budget epsilon.")
@click.option("--mechanism", default="pairwise", type=click.Choice(sorted(MECHANISMS)))
def demo(rows: int, eps: float, mechanism: str):
    """Runs a quick end-to-end synthesis, audit, and certificate demo."""
    click.echo(f"SynthProof demo (rows={rows}, eps={eps}, mechanism={mechanism})...")
    ds = TabularDataset.create_synthetic_toy(num_rows=rows)
    datasheet = FrontierEngine(seed=42).run_sweep(
        ds, eps_grid=[eps], mechanism=mechanism, num_canaries=min(20, rows // 5)
    )
    click.echo("=" * 60)
    click.echo("PRIVACY DATA SHEET")
    click.echo("=" * 60)
    click.echo(datasheet.to_json())
    click.echo("=" * 60)
    click.echo("Demo completed.")


if __name__ == "__main__":
    main()
