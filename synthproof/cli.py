"""SynthProof command line interface."""

import click

from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import Schema
from synthproof.frontier.certificate import FrontierEngine


@click.group()
def main():
    """SynthProof — Synthetic Data That Ships With Its Proof."""
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


@main.command()
@click.option("--input", "input_path", default=None, type=click.Path(exists=True),
              help="CSV file to synthesise. Omit to use the built-in toy table.")
@click.option("--schema", "schema_path", default=None, type=click.Path(exists=True),
              help="Public schema JSON declaring column kinds and numeric bounds.")
@click.option("--eps", default=1.0, help="Total privacy budget for the release.")
@click.option("--delta", default=1e-5, help="Target delta.")
@click.option("--mechanism", default="AIM / MST", help="Generator to use.")
@click.option("--rows", default=100, help="Rows for the toy table when --input is omitted.")
@click.option("--seed", default=42, help="Random seed.")
@click.option("--out", default=None, type=click.Path(),
              help="Write the Privacy Data Sheet JSON here.")
def run(input_path, schema_path, eps, delta, mechanism, rows, seed, out):
    """Synthesises a dataset and emits its Privacy Data Sheet."""
    ds = _load(input_path, schema_path, rows, seed)

    click.echo(f"Synthesising at total eps={eps} (delta={delta}) with {mechanism}...")
    datasheet = FrontierEngine(seed=seed).run_sweep(
        ds, eps_grid=[eps], delta=delta, mechanism=mechanism
    )

    text = datasheet.to_json()
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
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
def demo(rows: int, eps: float):
    """Runs a quick end-to-end SynthProof synthesis, audit, and certificate demo."""
    click.echo(f"Running SynthProof End-to-End Demo (rows={rows}, eps={eps})...")
    ds = TabularDataset.create_synthetic_toy(num_rows=rows)
    datasheet = FrontierEngine(seed=42).run_sweep(ds, eps_grid=[eps])
    click.echo("=" * 60)
    click.echo("PRIVACY DATA SHEET CERTIFICATE")
    click.echo("=" * 60)
    click.echo(datasheet.to_json())
    click.echo("=" * 60)
    click.echo("Demo completed successfully!")


if __name__ == "__main__":
    main()
