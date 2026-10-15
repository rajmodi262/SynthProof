"""Option validators and table loading shared by the CLI commands."""

import click

from synthproof.data.dataset import TabularDataset
from synthproof.data.schema import Schema

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
