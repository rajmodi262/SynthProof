# Python 3.11 Upgrade — unblocking real AIM (M1.8)

> **Result: no installation required, and `private-pgm` works.** Python 3.11.4 was already
> present on the development machine. A project-local virtualenv was created and the reference
> implementation verified end to end. **M1.8 is unblocked.**

---

## What was blocking

`private-pgm` (the package is `mbi`) declares `requires-python >= 3.11`. The project targeted
3.10, so `pip install` refused:

```
ERROR: Package 'mbi' requires a different Python: 3.10.0 not in '>=3.11'
```

Without it there was no published state-of-the-art mechanism, leaving H1 to compare two
in-house implementations rather than against AIM.

## What was actually available

```
py --list
 -V:3.11 *        Python 3.11 (64-bit)     <- already installed
 -V:3.10          Python 3.10 (64-bit)     <- what the project was using
```

Also present: `uv` 0.11.28, and a 3.13 under `%LOCALAPPDATA%\Programs\Python`.

**Nothing needed installing.** The 3.10 interpreter simply happened to be first on `PATH`.

## Setting it up

```bash
uv venv --python "C:\Program Files\Python311\python.exe" .venv311
uv pip install --python .venv311\Scripts\python.exe -e ".[dev]"
uv pip install --python .venv311\Scripts\python.exe "git+https://github.com/ryan112358/private-pgm.git"
```

Installs `mbi==1.3.0` plus `jax`, `optax`, `networkx`, `opt-einsum`.

The existing suite passes unchanged on 3.11 — **71 passed** — after adding `httpx`, which newer
Starlette requires for `TestClient`. That is the only compatibility change the upgrade needed.

## Verified working

`mbi` was exercised end to end, not merely imported. On a table with two correlated columns
(true correlation 0.503), graphical-model inference recovers the dependence:

| measurement noise σ | synthetic correlation |
|---:|---:|
| 0.5 | **0.487** |

## The API (this is the part worth keeping)

The published examples are out of date; these are the signatures that actually work in 1.3.0.

```python
import numpy as np, pandas as pd
from mbi import Domain, Dataset, LinearMeasurement, estimation

# 1. Domain: attribute names and their cardinalities. Everything must be integer-coded.
dom  = Domain(("a", "b"), (5, 5))
data = Dataset(df, dom)

# 2. Measure marginals and add DP noise. `stddev` tells the estimator how much to trust each.
meas = []
for clique in [("a",), ("b",), ("a", "b")]:
    y = data.project(clique).datavector()
    meas.append(LinearMeasurement(y + np.random.normal(0, sigma, y.shape),
                                  clique, stddev=sigma))

# 3. Fit the graphical model. NOTE: domain first, then measurements.
model = estimation.MirrorDescent().estimate(dom, meas, known_total=n, iters=300)

# 4. Sample. `.records` is NOT a frame — use `.to_dict()`.
synth = pd.DataFrame(model.synthetic_data(rows=n).to_dict())
```

Four API traps, all of which cost time:

| Trap | Correct form |
|---|---|
| `estimation.mirror_descent` | `estimation.MirrorDescent` (a dataclass estimator) |
| `MirrorDescent(iters=...)` | `iters` belongs to `.estimate()`, not the constructor |
| `.estimate(measurements, domain, ...)` | **domain first**: `.estimate(domain, measurements, known_total=...)` |
| `.synthetic_data(...).df` | `.records` is an `int`; use `.to_dict()` |

## Remaining work for M1.8

The environment is done; the integration is not. Roughly 10–14 hours:

1. **Integer-code the pipeline for `mbi`.** Numeric columns bin against the public schema range;
   categoricals map to the DP-released domain. This already exists in
   `generators/pairwise.py::_build_levels` and can be lifted out.
2. **Adaptive clique selection via the exponential mechanism** — the part that makes AIM AIM.
   Must be charged to the accountant; it is a mechanism, not free.
3. **Map `stddev` to our calibrated noise scale** so AIM composes to its target ε like every
   other generator.
4. **Register as `MECHANISMS["aim"]`** and re-run the H1 grid with three families.

## Should the project move to 3.11?

**Yes, and the cost is close to zero.**

| | |
|---|---|
| Interpreter | already installed |
| Suite on 3.11 | 71/71 passing |
| Code changes | none |
| Dependency changes | add `httpx` to dev extras |
| Unlocks | `private-pgm`, published AIM, a real SOTA comparison for H1 |

`requires-python` is being raised to `>=3.11` and CI now runs 3.11/3.12/3.13. The 3.10
environment can stay for day-to-day work, but **any run producing published numbers should use
3.11+**, since that is the only environment where AIM can participate.

## Reproducing

```bash
uv venv --python 3.11 .venv311 && uv pip install --python .venv311/Scripts/python.exe -e ".[dev]"
uv pip install --python .venv311/Scripts/python.exe "git+https://github.com/ryan112358/private-pgm.git"
.venv311/Scripts/python.exe -m pytest -q
```

`.venv311/` is gitignored.
