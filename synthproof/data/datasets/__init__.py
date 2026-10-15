"""Benchmark dataset loaders with integrity verification.

Each loader fetches a public benchmark, verifies its SHA-256 against a pinned digest, and
returns a `TabularDataset` built against a **hand-declared public schema**.

The schemas here matter more than the download code. Their numeric bounds are publishable
facts about the domain (an age lies in [17, 90]; hours worked per week in [1, 99]) rather than
values measured from the data. That is what makes the sensitivity the profiler declares
defensible — see brutal_project_audit.md, finding F5.

Split into a package on 2026-10-16: `_source` (fetching and digests), `census`,
`extra` and `rivals` (loaders by family); the registry lives here.
"""

from typing import Callable, Dict

from synthproof.data.dataset import TabularDataset
from synthproof.data.datasets._source import (  # noqa: F401
    DEFAULT_DATA_DIR,
    DatasetSource,
    _cache_path,
    fetch,
    pin_checksum,
)
from synthproof.data.datasets.census import (  # noqa: F401
    ADULT,
    ADULT_COLUMNS,
    BANK_MARKETING,
    DIABETES_130,
    adult_schema,
    bank_marketing_schema,
    diabetes130_schema,
    load_adult,
    load_bank_marketing,
    load_diabetes130,
)
from synthproof.data.datasets.extra import (  # noqa: F401
    _BCW_FEATS,
    _GERMAN_COLS,
    _MUSHROOM_COLS,
    BREAST_CANCER,
    GERMAN_CREDIT,
    MUSHROOM,
    NURSERY,
    WINE_QUALITY,
    breast_cancer_schema,
    german_credit_schema,
    load_breast_cancer,
    load_german_credit,
    load_mushroom,
    load_nursery,
    load_wine_quality,
    mushroom_schema,
    nursery_schema,
    wine_quality_schema,
)
from synthproof.data.datasets.rivals import (  # noqa: F401
    _FIRE_COLS,
    SF_FIRE,
    TEXAS,
    load_sf_fire,
    load_texas,
    sf_fire_schema,
    texas_schema,
)

REGISTRY: Dict[str, Callable[..., TabularDataset]] = {
    "adult": load_adult,
    "diabetes": load_diabetes130,
    "bank": load_bank_marketing,
    "mushroom": load_mushroom,
    "nursery": load_nursery,
    "german": load_german_credit,
    "wine": load_wine_quality,
    "bcw": load_breast_cancer,
    "texas": load_texas,
    "fire": load_sf_fire,
}


def load(name: str, **kwargs) -> TabularDataset:
    """Loads a benchmark by short name."""
    if name not in REGISTRY:
        raise KeyError(f"Unknown dataset {name!r}. Available: {sorted(REGISTRY)}")
    return REGISTRY[name](**kwargs)
