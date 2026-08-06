"""SynthProof Command Line Interface (CLI)."""

import click

from synthproof.data.dataset import TabularDataset
from synthproof.frontier.certificate import FrontierEngine


@click.group()
def main():
    """SynthProof — Synthetic Data That Ships With Its Proof."""
    pass


@main.command()
@click.option("--rows", default=100, help="Number of rows for synthetic benchmark.")
@click.option("--eps", default=1.0, help="Target privacy budget epsilon.")
def demo(rows: int, eps: float):
    """Runs a quick end-to-end SynthProof synthesis, audit, and certificate demo."""
    click.echo(f"Running SynthProof End-to-End Demo (rows={rows}, eps={eps})...")
    ds = TabularDataset.create_synthetic_toy(num_rows=rows)
    engine = FrontierEngine(seed=42)
    datasheet = engine.run_sweep(ds, eps_grid=[eps])
    click.echo("=" * 60)
    click.echo("PRIVACY DATA SHEET CERTIFICATE")
    click.echo("=" * 60)
    click.echo(datasheet.to_json())
    click.echo("=" * 60)
    click.echo("Demo completed successfully!")


if __name__ == "__main__":
    main()
