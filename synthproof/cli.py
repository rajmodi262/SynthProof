"""SynthProof command line interface."""

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Optional

import click

from synthproof.data.dataset import TabularDataset
from synthproof.data.preflight import PreflightRefused
from synthproof.data.schema import Schema
from synthproof.frontier import croissant as croissant_mod
from synthproof.frontier.certificate import FrontierEngine
from synthproof.frontier.experiment import MECHANISMS
from synthproof.ledger import signing


@click.group()
def main():
    """SynthProof — synthetic data that ships with its proof."""
    pass


# Epsilon bands. These are conventions from the DP deployment literature, not theorems:
# eps <= 1 is conservative, 1-10 is the range most deployments sit in, and above ~10 the
# formal guarantee is so weak that quoting it is closer to marketing than to privacy.
EPS_WARN_ABOVE = 10.0
EPS_REFUSE_ABOVE = 1e6


def _validate_eps(ctx, param, value):
    """Rejects impossible epsilon and warns loudly about meaningless epsilon.

    Previously any value was accepted in silence: `--eps 1000000000` produced a Privacy Data
    Sheet reporting `proved eps=999986985.822` with no indication that this is not privacy in
    any useful sense. A number that large is almost always a typo or a misunderstanding, and
    a tool that prints it without comment is lending it credibility.
    """
    if value is None:
        return value
    if value <= 0:
        raise click.BadParameter(
            f"epsilon must be positive, got {value:g}. "
            "Epsilon bounds a likelihood ratio, so zero or negative has no meaning. "
            "Try --eps 1.0 for a conservative release."
        )
    if value > EPS_REFUSE_ABOVE:
        raise click.BadParameter(
            f"epsilon {value:g} is not a privacy parameter in any useful sense — "
            f"at this scale the mechanism is effectively releasing the raw data.\n"
            "If you genuinely want an unprotected baseline, say so explicitly by using the "
            "control generators in `synthproof.generators.leaky` rather than by inflating "
            "epsilon."
        )
    if value > EPS_WARN_ABOVE:
        click.secho(
            f"  WARNING: eps={value:g} is far above the range where the formal guarantee is "
            "meaningful.\n"
            f"  Above about {EPS_WARN_ABOVE:g}, exp(eps) is large enough that the bound "
            "permits an adversary to\n"
            "  distinguish membership almost perfectly. The number below is still correctly "
            "computed;\n"
            "  it just does not mean much. Reduce --eps for a defensible release.",
            fg="yellow",
            err=True,
        )
    return value


def _validate_delta(ctx, param, value):
    """Delta is a failure probability, so it must be a probability — and a small one."""
    if value is None:
        return value
    if not (0.0 < value < 1.0):
        raise click.BadParameter(
            f"delta must be in (0, 1), got {value:g}. It is the probability the epsilon "
            "bound fails to hold."
        )
    if value > 1e-3:
        click.secho(
            f"  WARNING: delta={value:g} is large. Convention is delta << 1/n, so for n rows "
            "of data\n"
            "  a delta above ~1e-3 admits mechanisms that may release individual records "
            "outright.",
            fg="yellow",
            err=True,
        )
    return value


def _load(input_path, schema_path, rows, seed):
    """Loads a dataset and reports how its schema was obtained.

    Returns (dataset, domain_source). The second value is not cosmetic: it is what the data
    sheet uses to tell a reader whether the column bounds were public facts or were read out
    of the sensitive table.
    """
    if input_path is None:
        click.echo(f"No --input given; using the built-in toy table ({rows} rows).")
        click.echo("  NOTE: toy columns are independent, so utility numbers mean little.")
        return TabularDataset.create_synthetic_toy(num_rows=rows, seed=seed), "declared"

    schema = None
    if schema_path:
        schema = Schema.from_json(schema_path)
        click.echo(f"Loaded public schema: {len(schema)} columns from {schema_path}")
    else:
        click.echo("  WARNING: no --schema given. Column kinds and numeric bounds will be")
        click.echo("  inferred from the data, which is NOT safe for a real release.")

    ds = TabularDataset.from_csv(input_path, schema=schema)
    domain_source = "declared"
    if schema is None:
        # Re-load through an inferred schema so numeric columns are still clipped to a
        # concrete range. That range is data-derived, hence the warning above.
        ds = TabularDataset(ds.df, name=ds.name, schema=Schema.infer_nonprivate(ds.df))
        domain_source = "inferred-nonprivate"
    click.echo(f"Loaded {ds.num_rows} rows x {ds.num_cols} columns from {input_path}")
    return ds, domain_source


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
@click.option("--seed", default=42, help="Random seed.")
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
):
    """Synthesises a dataset and emits its Privacy Data Sheet."""
    ds, domain_source = _load(input_path, schema_path, rows, seed)

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
    # Write the release itself. A Croissant record describes a distribution, so when one is
    # requested the CSV is written beside it even if --synthetic-out was not given: a record
    # pointing at a file that does not exist would be a claim about nothing.
    data_path = Path(synthetic_out) if synthetic_out else None
    if croissant_out and data_path is None:
        data_path = Path(croissant_out).with_suffix(".csv")

    data_sha = None
    if data_path is not None:
        if engine.last_release is None:
            raise click.ClickException(
                "The synthesis produced no retained release, so there is nothing to write. "
                "This is a bug: --synthetic-out/--croissant should have set retain_release."
            )
        engine.last_release.to_csv(data_path, index=False)
        data_sha = hashlib.sha256(data_path.read_bytes()).hexdigest()
        click.echo(f"Synthetic table written to {data_path}  ({len(engine.last_release)} rows)")

    if croissant_out:
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

    if not sign:
        click.echo("This sheet is UNSIGNED. Re-run with --sign to make it verifiable.")


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


@main.command()
@click.option("--rows", default=100, help="Number of rows for the toy benchmark.")
@click.option(
    "--eps",
    default=1.0,
    callback=_validate_eps,
    help="Target privacy budget epsilon. Must be > 0; warns above 10.",
)
@click.option("--mechanism", default="pairwise", type=click.Choice(sorted(MECHANISMS)))
def demo(rows: int, eps: float, mechanism: str):
    """Runs a quick end-to-end synthesis, audit, and certificate demo."""
    click.echo(f"SynthProof demo (rows={rows}, eps={eps}, mechanism={mechanism})...")
    ds = TabularDataset.create_synthetic_toy(num_rows=rows)
    # The toy table is generated, not sensitive, and is deliberately smaller than the
    # pre-flight row floor so the demo stays quick. Bypassing the refusal checks is therefore
    # legitimate here and nowhere else — and it is announced rather than done quietly, because
    # a demo that silently takes a path real releases cannot take teaches the wrong thing.
    click.echo(
        "  NOTE: pre-flight refusal checks are SKIPPED for the toy table. A real table of "
        f"{rows} rows would be refused (R1: below the 500-row floor)."
    )
    datasheet = FrontierEngine(seed=42).run_sweep(
        ds,
        eps_grid=[eps],
        mechanism=mechanism,
        num_canaries=min(20, rows // 5),
        skip_preflight=True,
    )
    click.echo("=" * 60)
    click.echo("PRIVACY DATA SHEET")
    click.echo("=" * 60)
    click.echo(datasheet.to_json())
    click.echo("=" * 60)
    click.echo("Demo completed.")


@main.command("audit-power")
@click.option(
    "--eps",
    type=float,
    default=None,
    callback=_validate_eps,
    help=(
        "The epsilon you want the audit to certify (usually your proved epsilon). "
        "Required unless --gdp --mu is used."
    ),
)
@click.option("--canaries", type=int, default=None, help="Canary budget you intend to spend.")
@click.option("--alpha", type=float, default=0.05, show_default=True, help="Significance level.")
@click.option(
    "--subgroups",
    type=int,
    default=1,
    show_default=True,
    help="Split the canary budget equally across this many subgroups (as H2 does).",
)
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option(
    "--gdp",
    is_flag=True,
    help="Answer the same question in mu-GDP space instead of epsilon/canaries.",
)
@click.option(
    "--delta",
    "gdp_delta",
    type=float,
    default=1e-5,
    show_default=True,
    help="Delta, used with --gdp to convert the target epsilon into a target mu.",
)
@click.option(
    "--mu",
    type=float,
    default=None,
    help="Target mu directly, instead of converting from --eps/--delta. Requires --gdp.",
)
@click.option(
    "--runs",
    type=int,
    default=None,
    help="Audit runs PER WORLD you intend to spend. Requires --gdp.",
)
def audit_power(eps, canaries, alpha, subgroups, as_json, gdp, gdp_delta, mu, runs):
    """Can your audit certify the epsilon you care about? Answer BEFORE you run it.

    Audits are routinely run at budgets that could not have produced the answer being sought,
    and a zero is then read as evidence of no leakage.

    AN EARLIER VERSION OF THIS DOCSTRING CLAIMED "privacy auditing has no equivalent" of
    statistical power analysis. That is FALSE and was corrected on 2026-09-03. The ceiling --
    the largest value a given budget could certify against a perfect adversary -- is published
    repeatedly, in both coordinates:

      * mu-GDP: Mitchell, Andrew, Ganesh, McMahan & Kairouz, arXiv:2606.10481 (Google, Jun
        2026), verbatim and verified from the full text: "We use n=3000 unique canaries per
        set, so the estimated mu of a perfect classifier is 7.17."
      * epsilon: Liu & Xiong, UniAud, arXiv:2507.04457 S III-B -- "The greatest privacy lower
        bound that A can estimate is eps_O when all guesses are correct, which is limited by
        the statistical power given T observations."
      * Also Heller & Fetaya arXiv:2110.05057 SV-B, and Zanella-Beguelin et al.
        arXiv:2206.05199, both computing it from run count via Clopper-Pearson.

    The estimator itself is likewise published: Koskela & Mohammadi (SaTML 2025,
    arXiv:2406.04827) give mu_emp = Phi^-1(1 - alpha_bar) - Phi^-1(beta_bar) with
    Clopper-Pearson or Jeffreys upper bounds -- which is `audit.gdp.mu_lower_bound`, and
    `max_provable_mu` is that same equation with both error counts set to zero.

    SO WHAT THIS COMMAND IS: an implementation, as a runnable pre-audit tool, of a quantity the
    literature states but does not ship. That is engineering, not a finding, and it must never
    be presented as one.

    This project ran exactly that experiment. H1 used 60 canaries against a proved epsilon of
    7.36, where the ceiling is 2.97: the instrument could not have reported above 2.97 even
    against a release that was 100% verbatim training data. The gap was guaranteed before any
    mechanism ran. This command exists so nobody repeats it.

    The ceiling binds the estimator class that reduces canary evidence to binary membership
    guesses -- Steinke et al. (2023) and both of this project's auditors. See
    `synthproof/audit/steinke.py` for the constructions that escape it.
    """
    from synthproof.audit.steinke import canaries_needed_for, max_provable_epsilon

    if subgroups < 1:
        raise click.BadParameter("--subgroups must be at least 1")

    if mu is not None and not gdp:
        raise click.BadParameter("--mu requires --gdp")
    if eps is None and not (gdp and mu is not None):
        raise click.BadParameter(
            "--eps is required, unless you give a target directly with --gdp --mu."
        )
    if runs is not None and not gdp:
        raise click.BadParameter("--runs requires --gdp")

    if gdp:
        # ---- the same question, in mu-GDP space ------------------------------------------
        # A canary audit reduces the evidence to binary membership guesses and is bounded by
        # the guess count. A GDP audit instead fits one parameter to the whole FPR/FNR
        # tradeoff curve across many runs, so its budget is RUNS PER WORLD, not canaries --
        # and it has its own ceiling, set by the confidence correction on two zero counts.
        # Reporting that ceiling is the point: without it, a small mu_emp reads as reassurance
        # when the instrument could not have produced anything larger.
        from synthproof.audit.gdp import (
            max_provable_mu,
            mu_from_eps_delta,
            runs_needed_for_mu,
        )

        target_mu = mu if mu is not None else mu_from_eps_delta(eps, gdp_delta)
        needed = runs_needed_for_mu(target_mu, alpha)
        report = {
            "metric": "mu-GDP",
            "target_mu": target_mu,
            "target_mu_source": (
                "given directly"
                if mu is not None
                else f"inverted from (eps={eps:g}, delta={gdp_delta:g}) -- the LOOSE comparator; "
                "use the mechanism's own sqrt(k)/sigma when the noise is known"
            ),
            "alpha": alpha,
            "runs_required_per_world": needed,
            "assumes": "a PERFECT adversary (zero false positives and zero false negatives)",
        }
        if runs is not None:
            if runs < 1:
                raise click.BadParameter("--runs must be at least 1")
            ceiling = max_provable_mu(runs, runs, alpha)
            report["runs_per_world"] = runs
            report["ceiling_mu"] = ceiling
            report["can_certify_target"] = bool(ceiling >= target_mu)

        if as_json:
            click.echo(json.dumps(report, indent=2))
            return

        click.echo("")
        click.echo(f"  target mu ...................... {target_mu:.4f}")
        click.echo(f"  ({report['target_mu_source']})")
        click.echo(f"  alpha .......................... {alpha:g}")
        click.echo(f"  runs required per world ........ {needed:,}   (perfect adversary)")
        if runs is not None:
            click.echo(f"  run budget per world ........... {runs:,}")
            click.echo(f"  ceiling at that budget ......... {report['ceiling_mu']:.4f}")
            click.echo("")
            if report["can_certify_target"]:
                click.echo(
                    f"  VERDICT: this audit CAN certify mu = {target_mu:.4f}.\n"
                    f"           A smaller mu_emp is then a measurement, not a floor."
                )
            else:
                click.echo(
                    f"  VERDICT: this audit CANNOT certify mu = {target_mu:.4f}.\n"
                    f"           At {runs:,} runs per world the largest certifiable mu is "
                    f"{report['ceiling_mu']:.4f}.\n"
                    f"           Raise the budget to {needed:,}, or report the ceiling beside\n"
                    f"           the result so a small value cannot be misread."
                )
        click.echo("")
        return

    required_total = canaries_needed_for(eps, alpha) * subgroups
    report = {
        "target_epsilon": eps,
        "alpha": alpha,
        "subgroups": subgroups,
        "canaries_required_total": required_total,
        "canaries_required_per_subgroup": canaries_needed_for(eps, alpha),
        "assumes": "a PERFECT adversary (every canary identified correctly)",
    }

    if canaries is not None:
        if canaries < 1:
            raise click.BadParameter("--canaries must be at least 1")
        per_group = canaries // subgroups
        report["canary_budget"] = canaries
        report["canaries_per_subgroup"] = per_group
        report["ceiling"] = max_provable_epsilon(per_group, alpha) if per_group >= 1 else 0.0
        report["can_certify_target"] = bool(report["ceiling"] >= eps)

    if as_json:
        click.echo(json.dumps(report, indent=2))
        return

    click.echo("")
    click.echo(f"  target epsilon .................. {eps:g}")
    click.echo(f"  alpha .......................... {alpha:g}")
    if subgroups > 1:
        click.echo(f"  subgroups ...................... {subgroups} (budget split equally)")
    per_note = ""
    if subgroups > 1:
        per_note = ", {:,} per subgroup".format(report["canaries_required_per_subgroup"])
    click.echo(
        "  canaries required .............. {:,}   (perfect adversary{})".format(
            required_total, per_note
        )
    )

    if canaries is None:
        click.echo("")
        click.secho(
            "  Pass --canaries to check a specific budget against this requirement.", fg="cyan"
        )
        return

    per_group = report["canaries_per_subgroup"]
    click.echo(f"  canary budget .................. {canaries:,}")
    if subgroups > 1:
        click.echo(f"  canaries per subgroup .......... {per_group:,}")
    click.echo(f"  ceiling at that budget ......... {report['ceiling']:.2f}")
    click.echo("")

    if report["can_certify_target"]:
        click.secho(
            f"  VERDICT: this audit CAN certify epsilon = {eps:g}. Run it.", fg="green", bold=True
        )
    else:
        click.secho(f"  VERDICT: this audit CANNOT certify epsilon = {eps:g}.", fg="red", bold=True)
        click.echo(
            f"           At {per_group:,} guesses the largest certifiable epsilon is "
            f"{report['ceiling']:.2f}.\n"
            f"           A reported 0 would be uninformative, not evidence of no leakage.\n"
            f"           Either raise the budget to {required_total:,}, or report the ceiling\n"
            f"           beside the result so the zero cannot be misread."
        )
    click.echo("")


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
    """Verifies an offline capsule's Ed25519 signature and its MIQE 2.0 LoD bounds."""
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
    click.echo(
        f"    Dataset       : {res['dataset_name']} "
        f"({res['num_rows']:,} rows recorded, "
        f"{res['total_records_in_capsule']:,} in capsule)"
    )
    click.echo(f"    Mechanism     : {res['mechanism']}")
    click.echo(f"    Ledger Head   : {res['ledger_hash']}")
    click.echo(f"    Signing Key   : {res['public_key'][:32]}...")

    click.echo("")
    if res["lod_safe"]:
        click.secho(f"  ✓ MIQE 2.0 LoD BOUNDS: {res['lod_status']}", fg="green", bold=True)
        click.echo(
            f"    Audited eps ({res['audited_eps']:.3f}) < "
            f"Auditor ceiling ({res['audit_ceiling']:.3f}) <= "
            f"Proved eps ({res['proved_eps']:.3f})"
        )
    else:
        click.secho(f"  ! MIQE 2.0 WARNING: {res['lod_status']}", fg="yellow", bold=True)
        click.echo(
            f"    Audited eps ({res['audited_eps']:.3f}) reached or exceeded "
            f"auditor ceiling ({res['audit_ceiling']:.3f})"
        )
    click.echo("")


@main.command("prototype")
@click.option("--port", default=8000, help="Port to run server on.")
def prototype_cmd(port: int):
    """Launches the 100% working interactive prototype showcase."""
    import os

    # run_prototype.py is a loose launcher at the REPOSITORY ROOT, not part of the installed
    # package, so this import resolves only from a source checkout. After
    # `pip install synthproof` it raised a bare ModuleNotFoundError. Say what is wrong and
    # what to do instead, rather than failing with an import error naming a file the user has
    # never heard of.
    try:
        import run_prototype
    except ImportError as exc:
        raise click.ClickException(
            "`synthproof prototype` needs the launcher script that lives at the root of the "
            "source checkout, and it is not importable here -- this usually means SynthProof "
            "was pip-installed rather than cloned.\n"
            "Run it from a checkout, or start the service directly with:\n"
            "    uvicorn synthproof.api.main:app --host 127.0.0.1 --port "
            f"{port}"
        ) from exc

    os.environ["PORT"] = str(port)
    run_prototype.main()


if __name__ == "__main__":
    main()
