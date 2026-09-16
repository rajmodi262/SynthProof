# The differential accountant and Poisson subsampling

> **Found 2026-09-14** by `tests/test_release_boundary.py`, while checking that every mechanism runs
> with a full-width secret seed. Standing rules apply: `INFERENCE:` marks reasoning, and every
> number here is copied from the JSON files in this directory.

## What was seen

`FrontierEngine.run_sweep` refused every DP-VAE release with `AccountantDisagreement`, identically
with seeds 3 and 2⁶³ − 1:

| Table rows | dp_accounting ε | autodp ε (as the cross-check composed it) |
|---:|---:|---:|
| 900 | 0.939751 | 2.449350 |
| 3000 | 0.939758 | 9.502148 |

The gap did not depend on the seed, and autodp's ε *grew* with the table, although a larger table
means a smaller sampling rate.

## Cause

`synthproof/accounting/differential.py::cross_check_spends` rebuilt each charge in autodp from
`name`, `noise_scale`, `sensitivity` and `steps`, and never read `sampling_rate`. DP-VAE charges
one Gaussian with `sampling_rate = batch_size / n` and `steps = 200`, so the cross-check recomposed
200 steps of a Gaussian applied to the whole table.

`INFERENCE:` a smaller sampling rate lets the calibration choose a smaller noise multiplier for the
same ε. Composed without the amplification, that smaller noise reads as far more privacy loss,
which is why the gap widened with n.

## First fix attempt, and why it was not kept

`dpvae_subsampling_probe.json` recomposed DP-VAE's real charges in autodp with
`AmplificationBySampling(PoissonSampling=True, improved_bound_flag=True)`:

| Rows | Gaussian noise multiplier | q | steps | dp_accounting ε | autodp, no subsampling | autodp, Poisson subsampling |
|---:|---:|---:|---:|---:|---:|---:|
| 900 | 18.042053 | 0.284444 | 200 | 0.939791 | 3.597449 | 0.939791 |
| 3000 | 5.549316 | 0.085333 | 200 | 0.939759 | 14.481192 | 0.939724 |

Those two charges agreed. A standard DP-SGD setting (σ = 1.1, q = 0.01, 1000 steps) did not:
dp_accounting 1.711770 against autodp 1.725229, and the gate refused the release at a 0.8% gap.

`subsampled_gaussian_grid.json` then compared three computations on 40 configurations: σ ∈ {0.8,
1.1, 2, 5.549316, 18.042053}, q ∈ {0.001, 0.01, 0.085333, 0.284444}, steps ∈ {100, 1000},
δ = 1e-5. The three were the RDP ε the accountant charges (dp_accounting), autodp with Poisson
amplification, and dp_accounting's PLD accountant.

| Finding | Value |
|---|---|
| Charged RDP ε below the PLD ε | **0 of 40** configurations |
| autodp relative to charged ε, largest excess | **+17.2%** (σ 0.8, q 0.284444, 1000 steps) |
| autodp relative to charged ε, largest shortfall | **−68.1%** (σ 18.042053, q 0.001, 100 steps) |

`INFERENCE:` for subsampled Gaussians the two libraries apply different subsampling bounds; they
are not one bound implemented twice. A 1% agreement tolerance, or reading "lower than autodp" as
under-reporting, therefore means nothing on these charges. Keeping the amplified comparison would
have traded one false refusal for verdicts that are arbitrary in both directions. In one cell autodp
also came out below the PLD value (0.001169 against 0.001240). That is not interpreted here: the
PLD accountant's default estimate is itself pessimistic.

## What was done

- `cross_check_spends` reports any release containing a Poisson-subsampled charge as
  **`unsupported`**. That verdict never blocks a release and never reads as agreement, and the
  sheet says the release was not independently cross-checked. It is the module's rule for every
  charge it cannot honestly compare.
- `tests/test_differential_accounting.py` pins that verdict on DP-VAE's two real charges and the
  standard DP-SGD setting. It also pins the check that does hold: on those three, the charged ε is
  never below the PLD accountant's.
- `tests/test_release_boundary.py` asserts that a DP-VAE release now passes `run_sweep`.

## What it means

- **DP-VAE's proved ε was not shown to be wrong.** In 40 of 40 configurations it sits above
  the PLD estimate. The cross-check was wrong, and only in the safe direction: it refused, it
  never passed.
- **The assurance for subsampled releases is weaker than for the rest.** They rest on
  dp_accounting alone, and the PLD comparison runs in tests, not per release. A per-release
  PLD comparison would restore a second computation, but not an independent implementation, since
  both come from the same library.

`CONFIDENCE: high` for the cause: the code omitted the field. `CONFIDENCE: high` that autodp's
amplified bound is not a usable agreement check on these charges: the grid shows gaps of both
signs, up to 68%. `CONFIDENCE: med` that no other subsampled path exists: DP-VAE is the only
generator that sets `sampling_rate`, per a search of `synthproof/` on 2026-09-14.
