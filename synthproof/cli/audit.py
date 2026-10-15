"""Audit planning and checking: `audit-power` and `boundary-audit`."""

import json
from pathlib import Path
from typing import Optional

import click

from synthproof.cli import main
from synthproof.cli._common import _validate_eps


def _check_power_args(eps, subgroups, gdp, mu, runs) -> None:
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


def _gdp_power(eps, alpha, as_json, gdp_delta, mu, runs) -> None:
    """The same question in mu-GDP space.

    A canary audit reduces the evidence to binary membership guesses and is bounded by the guess
    count. A GDP audit instead fits one parameter to the whole FPR/FNR tradeoff curve across many
    runs, so its budget is RUNS PER WORLD, not canaries -- and it has its own ceiling, set by the
    confidence correction on two zero counts. Reporting that ceiling is the point: without it, a
    small mu_emp reads as reassurance when the instrument could not have produced anything larger.
    """
    from synthproof.audit.gdp import max_provable_mu, mu_from_eps_delta, runs_needed_for_mu

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


def _canary_report(eps, canaries, alpha, subgroups) -> dict:
    from synthproof.audit.steinke import canaries_needed_for, max_provable_epsilon

    report = {
        "target_epsilon": eps,
        "alpha": alpha,
        "subgroups": subgroups,
        "canaries_required_total": canaries_needed_for(eps, alpha) * subgroups,
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
    return report


def _render_canary_report(report: dict) -> None:
    eps, subgroups = report["target_epsilon"], report["subgroups"]
    required_total = report["canaries_required_total"]
    click.echo("")
    click.echo(f"  target epsilon .................. {eps:g}")
    click.echo(f"  alpha .......................... {report['alpha']:g}")
    per_note = ""
    if subgroups > 1:
        click.echo(f"  subgroups ...................... {subgroups} (budget split equally)")
        per_note = ", {:,} per subgroup".format(report["canaries_required_per_subgroup"])
    click.echo(
        "  canaries required .............. {:,}   (perfect adversary{})".format(
            required_total, per_note
        )
    )
    if "canary_budget" not in report:
        click.echo("")
        click.secho(
            "  Pass --canaries to check a specific budget against this requirement.", fg="cyan"
        )
        return

    per_group = report["canaries_per_subgroup"]
    click.echo(f"  canary budget .................. {report['canary_budget']:,}")
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
    _check_power_args(eps, subgroups, gdp, mu, runs)
    if gdp:
        _gdp_power(eps, alpha, as_json, gdp_delta, mu, runs)
        return
    report = _canary_report(eps, canaries, alpha, subgroups)
    if as_json:
        click.echo(json.dumps(report, indent=2))
        return
    _render_canary_report(report)


@main.command("boundary-audit")
@click.argument("artefact", type=click.Path(exists=True, dir_okay=False))
@click.option("--json", "as_json", is_flag=True, help="Emit the report as JSON.")
@click.option(
    "--pubkey",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="The maker's public key. When given, the signature is verified FIRST (RB0).",
)
def boundary_audit_cmd(artefact: str, as_json: bool, pubkey: Optional[str] = None):
    """Checks a released sheet or Croissant record for leaks OUTSIDE its epsilon.

    Reads only the artefact -- never the data or the producer's code -- so anyone holding a release
    can run it. Exit status 1 when a channel is open: a published seed, a row count with no public
    basis, an unkeyed input hash, unlabelled real-table measurements, an uncharged domain.
    """
    from synthproof.audit import boundary

    try:
        document = json.loads(Path(artefact).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"{artefact} is not JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise click.ClickException(f"{artefact} is not a sheet or a Croissant record.")
    report = boundary.audit_release(document, public_key_path=pubkey)
    if as_json:
        click.echo(json.dumps(report.to_dict(), indent=2))
    else:
        click.echo(boundary.render(report))
    if not report.passed:
        raise SystemExit(1)
