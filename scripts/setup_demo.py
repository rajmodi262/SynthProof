"""Builds the `demo/` folder that docs/DEMO_SCRIPT.md assumes exists.

Task 6.1 of docs/ROAD_TO_TEN.md. The demo script opens with "Every command here was run end
to end and produces the output shown" and then uses `demo/ok.csv` and `demo/patients.csv` --
neither of which was in the repository, and nor was the folder. So the rehearsed path could
not be rehearsed, which is the failure mode a demo script exists to prevent. On viva day that
surfaces as a FileNotFoundError in front of a panel.

Everything here is deterministic (fixed seeds) and offline-capable once UCI Adult is cached,
so the demo can be rebuilt on a machine with no network -- which is the point of a fallback.

Usage:
    python -m scripts.setup_demo
"""

import numpy as np
import pandas as pd

from synthproof.data.datasets import load_adult

DEMO = "demo"
N_OK = 3000
N_PATIENTS = 2000
SEED = 0


def build_ok() -> pd.DataFrame:
    """3,000 rows of real UCI Adult -- an ordinary table that releases cleanly."""
    ds = load_adult()
    return ds.df.sample(n=N_OK, random_state=SEED).reset_index(drop=True)


def build_patients() -> pd.DataFrame:
    """A table carrying a direct identifier, so the refusal path has something to refuse.

    `mrn` is a medical record number: unique per row and a direct identifier. The point of the
    demo step that uses this file is that the system declines to proceed WITHOUT having read
    any value in the column -- it decides from the schema and the row count alone. Synthetic
    rather than real, because a demo fixture must never be a real clinical table.
    """
    rng = np.random.default_rng(SEED)
    n = N_PATIENTS
    age = rng.integers(18, 91, size=n)
    # Diagnosis depends on age, so there is genuine structure to preserve or lose. A fixture
    # with independent columns would make every utility number in the demo meaningless -- the
    # exact defect that got the original toy sweep deleted from this repository.
    p_chronic = np.clip((age - 18) / 90.0, 0.05, 0.85)
    diagnosis = np.where(
        rng.random(n) < p_chronic,
        rng.choice(["diabetes", "hypertension", "cardiac"], size=n),
        rng.choice(["fracture", "infection", "routine"], size=n),
    )
    return pd.DataFrame(
        {
            "mrn": [f"MRN{i:07d}" for i in rng.permutation(n)],
            "age": age,
            "sex": rng.choice(["F", "M"], size=n, p=[0.51, 0.49]),
            "diagnosis": diagnosis,
            "los_days": np.clip(rng.poisson(3.0, size=n) + (age > 65).astype(int), 1, 60),
        }
    )


def main() -> None:
    from pathlib import Path

    out = Path(DEMO)
    out.mkdir(exist_ok=True)

    ok = build_ok()
    ok.to_csv(out / "ok.csv", index=False)
    print(f"wrote {out / 'ok.csv'}  {len(ok)} rows x {ok.shape[1]} cols")

    patients = build_patients()
    patients.to_csv(out / "patients.csv", index=False)
    print(f"wrote {out / 'patients.csv'}  {len(patients)} rows x {patients.shape[1]} cols")
    print(f"  mrn is unique per row: {patients['mrn'].nunique() == len(patients)}")

    print("\nNow run the five commands in docs/DEMO_SCRIPT.md.")


if __name__ == "__main__":
    main()
