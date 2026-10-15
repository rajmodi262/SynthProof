"""SynthProof command line interface.

Split into a package on 2026-10-16 (it was one 961-line module). Commands live by purpose:
`release` (run, keygen, verify, croissant, infer-schema), `audit` (audit-power,
boundary-audit), `capsule` (export-capsule, verify-capsule); the small ones stay here. The
entry point is unchanged: `synthproof = synthproof.cli:main`, and `python -m synthproof.cli`.
"""

import click

from synthproof.cli._common import (  # noqa: F401  (re-exported: tests and scripts import these)
    EPS_REFUSE_ABOVE,
    EPS_WARN_ABOVE,
    _load,
    _validate_delta,
    _validate_eps,
)
from synthproof.data.dataset import TabularDataset
from synthproof.frontier.certificate import FrontierEngine
from synthproof.frontier.experiment import MECHANISMS


@click.group()
def main():
    """SynthProof — synthetic data that ships with its proof."""
    pass


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
            "  See archive/docs/PYTHON311_UPGRADE.md."
        )


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
    datasheet = FrontierEngine().run_sweep(
        ds,
        eps_grid=[eps],
        mechanism=mechanism,
        num_canaries=min(20, rows // 5),
        skip_preflight=True,
        # The toy table has exactly --rows rows, a number the operator chose, so it is public.
        release_rows=rows,
    )
    click.echo("=" * 60)
    click.echo("PRIVACY DATA SHEET")
    click.echo("=" * 60)
    click.echo(datasheet.to_json())
    click.echo("=" * 60)
    click.echo("Demo completed.")


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


# Registering the remaining commands. Imported last: each module decorates `main`.
from synthproof.cli import audit, capsule, release  # noqa: E402,F401
