"""A DP-SGD variational autoencoder — the project's first non-marginal-based mechanism.

WHY THIS EXISTS, AND WHY IT IS NOT A BOLT-ON.

Every mechanism this project had before it (`independent`, `moments`, `pairwise`, `aim`) is
**marginal-based**: each one picks a set of low-order marginals, measures them under DP, and
fits a distribution to the noisy measurements. That shared property is what makes the project's
strongest result — the clique-selection confound — impossible to test with the mechanisms it
already had.

The confound, restated: AIM selects ~6 two-way cliques by exponential mechanism, and its score
on a structure metric that measures ONE column pair is largely decided by whether that pair is
one it selected. On UCI Adult it selects `age x hours_per_week` at every epsilon and looks like
a clear winner; on ACSIncome it selects `AGEP x WKHP` at one epsilon of three and becomes
statistically indistinguishable from the independent baseline. Measured across all numeric
pairs, AIM's advantage over a no-dependence baseline is 11.9x larger on its best selected pair
than on its best unselected pair on Adult, and only 2.3x on ACS.

**A VAE selects nothing.** It has no marginal-selection step, no exponential mechanism over
statistics, no workload. Its parameters are updated by noisy gradients over whole records, so
every column pair is modelled by the same machinery. That makes it the control the confound
argument needs: if the selection effect is real, a mechanism that cannot select should show no
selection-linked structure in its per-pair error, while AIM does. If the DP-VAE shows the SAME
pattern, the confound explanation is wrong and the project must say so.

This is therefore a **control, not a competitor**. It is not expected to beat AIM. Published
comparisons generally find marginal-based mechanisms outperform deep generative ones on DP
tabular benchmarks at this sample size, and a result where the VAE loses on utility while
showing no selection structure is exactly what would support the argument.

WHAT IS AND IS NOT CHARGED.
  * The binning grid and the category domains come from `DomainProfile`, which was already
    produced and charged by the DP profiler. Reusing them costs nothing further. They are
    never recomputed from the sensitive table here.
  * The ONLY data-touching step is the DP-SGD loop. Per-example gradients are clipped to
    `clip_norm` and Gaussian noise is added to their sum, which is the standard mechanism of
    Abadi et al. (CCS 2016).
  * Composition is delegated. The noise multiplier is calibrated by
    `calibrate_noise_scale(..., steps=T, sampling_rate=q)` and charged as a single
    `MechanismSpec` carrying `steps` and `sampling_rate`, so `dp_accounting` applies
    Poisson-subsampling amplification and RDP composition. No bound is computed here.

HONEST LIMITS, stated because a reader will assume more.
  * Sampling is **Poisson** in the accounting and **fixed-size batches** in the loop. This is
    the standard implementation gap in nearly every DP-SGD library, and it means the accounted
    epsilon is not exactly the epsilon of the code that ran. It is recorded in
    `sampling_note_` and surfaced on the certificate rather than hidden. Chua et al. (2024)
    and Lebeda et al. discuss the discrepancy; treat the reported epsilon as the standard
    approximation, not as a proof about this loop.
  * Numerical columns are discretised, so the model cannot represent within-bin structure.
    `NUM_BINS` is public.
  * Initialisation and batch order are seeded, so a run is reproducible.
"""

from typing import Dict, List

import jax
import jax.numpy as jnp
import numpy as np
import pandas as pd

from synthproof.accounting.accountant import Accountant
from synthproof.accounting.calibration import calibrate_noise_scale
from synthproof.accounting.types import MechanismSpec
from synthproof.data.dataset import TabularDataset
from synthproof.data.profiler import DomainProfile
from synthproof.generators.base import BaseGenerator

NUM_BINS = 10  # public discretisation grid for numerical columns


def _init_params(key, in_dim: int, hidden: int, latent: int, blocks: List[int]):
    """Small MLP encoder/decoder. Glorot-scaled, seeded."""
    k1, k2, k3, k4, k5 = jax.random.split(key, 5)

    def g(k, a, b):
        return jax.random.normal(k, (a, b)) * jnp.sqrt(2.0 / (a + b))

    return {
        "enc_w": g(k1, in_dim, hidden),
        "enc_b": jnp.zeros((hidden,)),
        "mu_w": g(k2, hidden, latent),
        "mu_b": jnp.zeros((latent,)),
        "lv_w": g(k3, hidden, latent),
        "lv_b": jnp.zeros((latent,)),
        "dec_w": g(k4, latent, hidden),
        "dec_b": jnp.zeros((hidden,)),
        "out_w": g(k5, hidden, in_dim),
        "out_b": jnp.zeros((in_dim,)),
    }


def _decode(params, z):
    h = jnp.tanh(z @ params["dec_w"] + params["dec_b"])
    return h @ params["out_w"] + params["out_b"]


def _elbo(params, x, key, block_sizes, kl_weight):
    """Negative ELBO for ONE example. Categorical cross-entropy per column block."""
    h = jnp.tanh(x @ params["enc_w"] + params["enc_b"])
    mu = h @ params["mu_w"] + params["mu_b"]
    logvar = jnp.clip(h @ params["lv_w"] + params["lv_b"], -6.0, 6.0)
    z = mu + jnp.exp(0.5 * logvar) * jax.random.normal(key, mu.shape)
    logits = _decode(params, z)

    recon, off = 0.0, 0
    for size in block_sizes:
        seg_logits = jax.lax.dynamic_slice(logits, (off,), (size,))
        seg_x = jax.lax.dynamic_slice(x, (off,), (size,))
        recon = recon - jnp.sum(seg_x * jax.nn.log_softmax(seg_logits))
        off += size

    kl = -0.5 * jnp.sum(1.0 + logvar - mu**2 - jnp.exp(logvar))
    return recon + kl_weight * kl


def _clip(grad, clip_norm):
    """Clips one example's gradient to `clip_norm` in global L2 norm."""
    leaves = jax.tree_util.tree_leaves(grad)
    norm = jnp.sqrt(sum(jnp.sum(g**2) for g in leaves))
    factor = jnp.minimum(1.0, clip_norm / (norm + 1e-12))
    return jax.tree_util.tree_map(lambda g: g * factor, grad)


class DPVAEGenerator(BaseGenerator):
    """Deep generative DP mechanism trained with DP-SGD. Selects no marginals."""

    def __init__(
        self,
        seed: int = 42,
        hidden: int = 64,
        latent: int = 8,
        steps: int = 200,
        batch_size: int = 256,
        clip_norm: float = 1.0,
        lr: float = 0.05,
        kl_weight: float = 1.0,
    ):
        super().__init__(seed=seed)
        self.hidden, self.latent = hidden, latent
        self.steps, self.batch_size = steps, batch_size
        self.clip_norm, self.lr, self.kl_weight = clip_norm, lr, kl_weight
        self.params_ = None
        self.sampling_note_ = (
            "Accounted as Poisson subsampling at rate q = batch_size / n; implemented as "
            "fixed-size batches. This is the standard DP-SGD implementation gap (see Chua et "
            "al. 2024) and the reported epsilon is the standard approximation, not a proof "
            "about this loop."
        )

    # ---------------------------------------------------------------- encoding

    def _build_encoding(self, profile: DomainProfile):
        """Column -> one-hot block. Grid comes from the ALREADY-CHARGED profile."""
        self.blocks_, self.block_sizes_, self.bin_edges_, self.cats_ = [], [], {}, {}
        for col in self.columns:
            cp = profile.columns.get(col)
            if cp is None:
                raise ValueError(f"Column {col!r} is absent from the DP domain profile.")
            if col in self.numerical_cols:
                lo, hi = cp.min_val, cp.max_val
                if lo is None or hi is None:
                    raise ValueError(f"Column {col!r} has no DP range in the profile.")
                if not hi > lo:
                    hi = lo + 1.0
                self.bin_edges_[col] = np.linspace(float(lo), float(hi), NUM_BINS + 1)
                size = NUM_BINS
            else:
                cats = list(cp.categories or [])
                if not cats:
                    raise ValueError(
                        f"Column {col!r} has an empty DP category domain; the profiler "
                        "suppressed everything. Raise the profiling budget."
                    )
                self.cats_[col] = cats
                size = len(cats)
            self.blocks_.append(col)
            self.block_sizes_.append(size)

    def _encode(self, df: pd.DataFrame) -> np.ndarray:
        rows = np.zeros((len(df), sum(self.block_sizes_)), dtype=np.float32)
        off = 0
        for col, size in zip(self.blocks_, self.block_sizes_, strict=True):
            if col in self.bin_edges_:
                idx = np.clip(
                    np.digitize(df[col].to_numpy(dtype=float), self.bin_edges_[col][1:-1]),
                    0,
                    size - 1,
                )
            else:
                lookup = {c: i for i, c in enumerate(self.cats_[col])}
                # `lookup` is bound as a default so the closure cannot capture the loop
                # variable. `.map` is eager so this is correct either way, but a late-bound
                # closure in a loop is the kind of thing that becomes a bug on the next edit.
                idx = df[col].map(lambda v, _lk=lookup: _lk.get(v, 0)).to_numpy(dtype=int)
            rows[np.arange(len(df)), off + idx] = 1.0
            off += size
        return rows

    # ---------------------------------------------------------------- fit

    def fit(
        self,
        dataset: TabularDataset,
        profile: DomainProfile,
        accountant: Accountant,
        target_eps: float,
    ) -> None:
        """Trains the VAE with DP-SGD, spending exactly `target_eps`."""
        self.columns = dataset.columns
        self.numerical_cols = dataset.numerical_cols
        self.categorical_cols = dataset.categorical_cols
        self._build_encoding(profile)

        X = jnp.asarray(self._encode(dataset.df))
        n = X.shape[0]
        q = min(1.0, self.batch_size / max(1, n))

        # Calibrate the noise multiplier so the WHOLE training run costs target_eps. The
        # inversion is done by the shared calibration routine against dp_accounting, with
        # subsampling and step count declared -- nothing is derived here.
        noise_scale = calibrate_noise_scale(
            target_eps=target_eps,
            target_delta=accountant.budget.delta,
            name="gaussian",
            sensitivity=self.clip_norm,
            steps=self.steps,
            sampling_rate=q if q < 1.0 else None,
        )
        spec = MechanismSpec(
            name="gaussian",
            sensitivity=self.clip_norm,
            noise_scale=noise_scale,
            sampling_rate=q if q < 1.0 else None,
            steps=self.steps,
            metadata={"mechanism": "dp_sgd_vae", "sampling_note": self.sampling_note_},
        )
        accountant.charge(spec, run_id="dpvae_dpsgd")
        self.noise_scale_ = float(noise_scale)

        key = jax.random.PRNGKey(self.seed)
        key, ik = jax.random.split(key)
        params = _init_params(ik, X.shape[1], self.hidden, self.latent, self.block_sizes_)
        block_sizes = tuple(self.block_sizes_)
        kl_w = self.kl_weight

        def per_example(p, x, k):
            return jax.grad(_elbo)(p, x, k, block_sizes, kl_w)

        grad_batch = jax.jit(jax.vmap(per_example, in_axes=(None, 0, 0)))

        @jax.jit
        def step(p, xb, keys, nkey):
            grads = grad_batch(p, xb, keys)
            clipped = jax.vmap(lambda g: _clip(g, self.clip_norm))(grads)
            summed = jax.tree_util.tree_map(lambda g: jnp.sum(g, axis=0), clipped)
            nkeys = jax.random.split(nkey, len(jax.tree_util.tree_leaves(summed)))
            leaves, treedef = jax.tree_util.tree_flatten(summed)
            noised = [
                g + noise_scale * jax.random.normal(k, g.shape)
                for g, k in zip(leaves, nkeys, strict=True)
            ]
            avg = jax.tree_util.tree_map(
                lambda g: g / xb.shape[0], jax.tree_util.tree_unflatten(treedef, noised)
            )
            return jax.tree_util.tree_map(lambda a, b: a - self.lr * b, p, avg)

        bs = min(self.batch_size, n)
        for _ in range(self.steps):
            key, bk, ek, nk = jax.random.split(key, 4)
            idx = jax.random.choice(bk, n, shape=(bs,), replace=False)
            params = step(params, X[idx], jax.random.split(ek, bs), nk)

        self.params_ = params
        self.is_fitted = True

    # ---------------------------------------------------------------- generate

    def generate(self, num_samples: int) -> pd.DataFrame:
        """Samples from the prior and decodes. Touches no data."""
        if not self.is_fitted:
            raise RuntimeError("DPVAEGenerator.generate called before fit.")

        key = jax.random.PRNGKey(self.seed + 1)
        key, zk = jax.random.split(key)
        z = jax.random.normal(zk, (num_samples, self.latent))
        logits = np.asarray(_decode(self.params_, z))

        rng = np.random.default_rng(self.seed + 2)
        out: Dict[str, List] = {}
        off = 0
        for col, size in zip(self.blocks_, self.block_sizes_, strict=True):
            seg = logits[:, off : off + size]
            seg = seg - seg.max(axis=1, keepdims=True)
            p = np.exp(seg)
            p /= p.sum(axis=1, keepdims=True)
            picks = np.array([rng.choice(size, p=row) for row in p])
            if col in self.bin_edges_:
                edges = self.bin_edges_[col]
                lo, hi = edges[picks], edges[picks + 1]
                out[col] = rng.uniform(lo, hi)
            else:
                cats = self.cats_[col]
                out[col] = [cats[i] for i in picks]
            off += size
        return pd.DataFrame(out, columns=self.columns)
