"""Offline release capsules: `export-capsule` and `verify-capsule`."""

import json
import textwrap
from pathlib import Path
from typing import Optional

import click

from synthproof.cli import main


@main.command("export-capsule")
@click.option(
    "--sheet", required=True, type=click.Path(exists=True), help="Path to PrivacyDataSheet JSON."
)
@click.option(
    "--data", required=True, type=click.Path(exists=True), help="Path to synthetic CSV or Parquet."
)
@click.option(
    "--out",
    required=False,
    type=click.Path(),
    default="capsule.html",
    help="Output HTML file path.",
)
@click.option(
    "--curator",
    required=False,
    default="SynthProof Autonomous Curator",
    help="Curator organization name.",
)
def export_capsule(sheet: str, data: str, out: str, curator: str):
    """Exports a self-verifying, offline HTML release capsule."""
    import pandas as pd

    from synthproof.capsule.generator import generate_capsule_html

    sheet_path = Path(sheet)
    data_path = Path(data)
    out_path = Path(out)

    click.echo(f"Loading sheet from {sheet_path}...")
    with open(sheet_path, "r", encoding="utf-8") as f:
        sheet_dict = json.load(f)

    click.echo(f"Loading synthetic data from {data_path}...")
    if data_path.suffix == ".parquet":
        df = pd.read_parquet(data_path)
    else:
        df = pd.read_csv(data_path)

    click.echo(f"Generating self-verifying capsule for {len(df):,} records...")
    generate_capsule_html(sheet_dict, df, output_path=out_path, curator_name=curator)

    click.secho(
        f"  SUCCESS: Exported self-verifying capsule to {out_path.resolve()}", fg="green", bold=True
    )
    click.echo("  Anyone can open this single file in ANY browser to verify the Ed25519 signature,")
    click.echo("  inspect the Limit of Detection gauge, and explore the data completely offline.")


def _print_key_trust(res: dict) -> None:
    fp = res.get("key_fingerprint", "unknown")
    if not res.get("publisher_authenticated", False):
        click.secho(
            f"  ! KEY TRUST: Verified against embedded key (fingerprint {fp}).\n"
            "    Not checked against a publisher key. Compare fingerprint before trusting.",
            fg="yellow",
        )
    else:
        click.secho(
            f"  ✓ KEY TRUST: Authenticated against supplied publisher key\n"
            f"    (fingerprint {fp}).",
            fg="green",
        )


@main.command("verify-capsule")
@click.option(
    "--capsule", required=True, type=click.Path(exists=True), help="Path to capsule HTML file."
)
@click.option(
    "--key-path",
    required=False,
    type=click.Path(exists=True),
    help="Path to expected Ed25519 public key file.",
)
def verify_capsule_cmd(capsule: str, key_path: Optional[str] = None):
    """Verifies an offline capsule's Ed25519 signature, and whether its audit could have
    certified its privacy claim.

    Exits 1 on a bad signature, AND on a claim that fails its own consistency checks (an audit
    lower bound above the proof, or a ceiling that is not the one its declared audit produces).
    A signature proves who made a claim; it does not make the claim coherent.
    """
    from synthproof.capsule.generator import verify_capsule

    capsule_path = Path(capsule)
    click.echo(f"Inspecting capsule: {capsule_path.resolve()}")
    try:
        res = verify_capsule(capsule_path, key_path=Path(key_path) if key_path else None)
    except Exception as exc:
        click.secho(f"  VERIFICATION FAILED: {exc}", fg="red", bold=True)
        raise SystemExit(1) from exc

    click.echo("")
    click.secho("  ✓ CRYPTOGRAPHIC INTEGRITY: ED25519 SIGNATURE AUTHENTIC", fg="green", bold=True)
    _print_key_trust(res)
    click.echo(
        f"    Dataset       : {res['dataset_name']} "
        f"({res['num_rows']:,} rows recorded, "
        f"{res['total_records_in_capsule']:,} in capsule)"
    )
    click.echo(f"    Mechanism     : {res['mechanism']}")
    click.echo(f"    Ledger Head   : {res['ledger_hash']}")
    click.echo(f"    Signing Key   : {res['public_key'][:32]}...")

    click.echo("")
    # The previous version printed "Audited < Ceiling <= Proved" under a green tick without
    # checking the second inequality -- which was false for both shipped demo capsules.
    tone = res["range_tone"]
    colour = {"ok": "green", "warn": "yellow", "fail": "red"}[tone]
    mark = {"ok": "✓", "warn": "!", "fail": "✗"}[tone]
    click.secho(f"  {mark} AUDIT RANGE: {res['lod_status']}", fg=colour, bold=True)
    click.echo(
        f"    proved eps {res['proved_eps']:.3f} · audited eps {res['audited_eps']:.3f} · "
        f"audit ceiling {res['audit_ceiling']:.3f}"
    )
    for line in textwrap.wrap(res["range_explanation"], 88):
        click.echo(f"    {line}")
    click.echo("")
    if tone == "fail":
        raise SystemExit(1)
