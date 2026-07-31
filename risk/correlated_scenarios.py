"""Correlated supply scenarios via copulas.

WHY THIS EXISTS
---------------
``risk/scenario_generation.yield_scenarios_from_distributions`` draws each
supplier's fill rate independently from its own Beta. That is wrong in a
specific and costly way: weather is regional. A heat wave, a freeze or a
drought hits every grower in a supply shed at once, so their shortfalls
arrive together rather than cancelling.

The consequence is measurable, not theoretical. Independent draws average
out across suppliers, the aggregate tightens around its mean, and the
stochastic optimizer finds nothing worth hedging — which is exactly the
VSS ~ 0 result we spent a long time explaining. Independence was doing the
work, not the economics. Miranda & Glauber (1997) put the same point in
insurance terms: correlated weather shocks make a book of business 20-50x
riskier than independence implies (see agronomy/systemic_risk.py).

WHAT IS PRESERVED
-----------------
Copulas separate the marginals from the dependence, so we keep the
calibrated per-supplier Beta distributions EXACTLY and only change how the
draws are coupled. Nothing about the marginal calibration is disturbed.

Two families, and the choice matters:

Gaussian copula
    Draw Z ~ N(0, R) via Cholesky, map through Phi to uniforms, then
    through each marginal's inverse CDF. Simple and fast.

    Its limitation is not a detail: the Gaussian copula has ZERO tail
    dependence for any rho < 1. Extreme events become asymptotically
    independent, so simultaneous severe shortfalls across a region are
    systematically under-represented — the precise scenario a perishable
    buyer most needs to plan for.

t copula
    Same construction with a chi-square mixing variable, giving nonzero
    tail dependence controlled by the degrees of freedom nu. Lower nu means
    stronger joint-tail clustering. This is the right default when the
    hazard is regional weather.
    Demarta, S. & McNeil, A.J. (2005), "The t Copula and Related Copulas,"
    *International Statistical Review* 73(1):111-129.

RANK CORRELATION, NOT LINEAR
----------------------------
The target is Spearman rank correlation, because it is invariant under the
monotone marginal transforms this construction applies — Pearson
correlation is not, and would be distorted by the mapping to Beta
marginals. The Gaussian-copula identity converts between them:

    rho_pearson = 2 * sin(pi * rho_spearman / 6)

implemented in ``spearman_to_pearson`` and checked in the tests.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import stats


def spearman_to_pearson(rho_spearman: float | np.ndarray) -> float | np.ndarray:
    """Gaussian-copula identity rho_p = 2 sin(pi rho_s / 6)."""
    return 2.0 * np.sin(np.pi * np.asarray(rho_spearman, dtype=float) / 6.0)


def pearson_to_spearman(rho_pearson: float | np.ndarray) -> float | np.ndarray:
    """Inverse identity rho_s = (6/pi) arcsin(rho_p / 2)."""
    r = np.clip(np.asarray(rho_pearson, dtype=float), -1.0, 1.0)
    return (6.0 / np.pi) * np.arcsin(r / 2.0)


def nearest_positive_definite(matrix: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """Project a correlation matrix to the nearest PSD one.

    An estimated correlation matrix from short, unequal histories is often
    slightly indefinite, and Cholesky then fails. Clipping the eigenvalues
    at a small positive floor and renormalising the diagonal is the
    standard repair; it changes the matrix by the minimum needed to make
    sampling possible.
    """
    m = np.asarray(matrix, dtype=float)
    m = (m + m.T) / 2.0
    vals, vecs = np.linalg.eigh(m)
    if np.all(vals > eps):
        return m
    vals = np.clip(vals, eps, None)
    out = vecs @ np.diag(vals) @ vecs.T
    d = np.sqrt(np.clip(np.diag(out), eps, None))
    out = out / np.outer(d, d)
    np.fill_diagonal(out, 1.0)
    return out


def equicorrelation_matrix(n: int, rho: float) -> np.ndarray:
    """Constant-correlation matrix — the shared-regional-shock model.

    Used when there is not enough joint history to estimate a full matrix
    but the operator knows their growers share a weather region. One
    number, honestly labelled, beats a noisy full matrix estimated from
    six overlapping deliveries.
    """
    rho = float(np.clip(rho, -1.0 / max(n - 1, 1) + 1e-9, 0.999))
    m = np.full((n, n), rho, dtype=float)
    np.fill_diagonal(m, 1.0)
    return m


def estimate_rank_correlation(
    observations: dict[str, np.ndarray],
    min_overlap: int = 4,
    default_rho: float = 0.0,
) -> tuple[np.ndarray, list[str], dict]:
    """Spearman correlation across entities from aligned observations.

    ``observations`` maps entity -> equal-length array of per-period
    values, with NaN where that entity had no delivery in a period. Pairs
    with fewer than ``min_overlap`` shared periods fall back to
    ``default_rho`` rather than reporting a correlation estimated from two
    points, which would be noise presented as signal.
    """
    keys = sorted(observations)
    n = len(keys)
    mat = np.eye(n)
    diagnostics = {"n_entities": n, "pairs_estimated": 0,
                   "pairs_defaulted": 0, "min_overlap": min_overlap}
    for i in range(n):
        for j in range(i + 1, n):
            a = np.asarray(observations[keys[i]], dtype=float)
            b = np.asarray(observations[keys[j]], dtype=float)
            ok = np.isfinite(a) & np.isfinite(b)
            if int(ok.sum()) >= min_overlap and np.std(a[ok]) > 1e-12 and np.std(b[ok]) > 1e-12:
                rho, _ = stats.spearmanr(a[ok], b[ok])
                rho = float(rho) if np.isfinite(rho) else default_rho
                diagnostics["pairs_estimated"] += 1
            else:
                rho = default_rho
                diagnostics["pairs_defaulted"] += 1
            mat[i, j] = mat[j, i] = rho
    return mat, keys, diagnostics


@dataclass
class CopulaScenarioGenerator:
    """Sample jointly-dependent fill rates with exact Beta marginals.

    copula: "t" (default, has tail dependence) or "gaussian".
    df: t degrees of freedom. Lower means stronger joint-tail clustering;
        as df grows the t copula converges to the Gaussian.
    """

    copula: str = "t"
    df: float = 5.0
    seed: int = 42

    def sample_uniforms(
        self, n_draws: int, correlation: np.ndarray,
    ) -> np.ndarray:
        """Dependent uniforms on [0,1], shape (n_draws, n_entities)."""
        r = nearest_positive_definite(np.asarray(correlation, dtype=float))
        n = r.shape[0]
        rng = np.random.default_rng(self.seed)
        chol = np.linalg.cholesky(r)
        z = rng.standard_normal((n_draws, n)) @ chol.T

        if self.copula == "gaussian":
            return stats.norm.cdf(z)
        if self.copula == "t":
            # t copula: scale the Gaussian vector by sqrt(df/chi2_df).
            chi = rng.chisquare(self.df, size=(n_draws, 1))
            t = z / np.sqrt(chi / self.df)
            return stats.t.cdf(t, df=self.df)
        raise ValueError(f"unknown copula {self.copula!r}; use 'gaussian' or 't'")

    def sample_beta_marginals(
        self,
        beta_params: dict[str, tuple[float, float]],
        n_draws: int,
        correlation: np.ndarray | None = None,
        rho: float | None = None,
    ) -> dict[str, np.ndarray]:
        """Correlated draws with each entity's exact Beta marginal.

        Supply either a full ``correlation`` matrix or a single ``rho`` for
        the equicorrelated case. Marginals are preserved exactly: the
        inverse-CDF step maps uniforms through each Beta unchanged.
        """
        keys = sorted(beta_params)
        n = len(keys)
        if n == 0:
            return {}
        if correlation is None:
            correlation = equicorrelation_matrix(n, rho if rho is not None else 0.0)
        u = self.sample_uniforms(n_draws, correlation)
        # Guard the inverse CDF against exact 0/1 from floating point.
        u = np.clip(u, 1e-12, 1.0 - 1e-12)
        out: dict[str, np.ndarray] = {}
        for idx, key in enumerate(keys):
            a, b = beta_params[key]
            out[key] = np.clip(stats.beta.ppf(u[:, idx], a, b), 0.0, 1.0)
        return out


def correlated_yield_scenarios(
    conn,
    scenario_indices: list[int],
    rho: float | None = None,
    copula: str = "t",
    df: float = 5.0,
    seed: int = 42,
    min_overlap: int = 4,
) -> tuple[dict, dict]:
    """Drop-in correlated replacement for the independent yield sampler.

    Returns ``({(scenario_index, supplier_id): fill}, diagnostics)`` — the
    same mapping shape ``TwoStageStochasticLP`` already consumes, so this
    substitutes without touching the optimizer.

    When ``rho`` is None the rank correlation is ESTIMATED from the
    operator's own delivery history: suppliers' weekly fill rates aligned
    on common weeks. Falls back to independence only when there is
    genuinely no overlapping history, and says so in the diagnostics rather
    than silently assuming it.
    """
    from risk.supplier_distribution import supplier_fill_distributions

    dists = supplier_fill_distributions(conn, quantile=0.10)
    beta_params = {sid: (float(d["alpha"]), float(d["beta"]))
                   for sid, d in dists.items() if sid != "_prior"}
    diagnostics: dict = {"n_suppliers": len(beta_params), "copula": copula,
                         "df": df, "seed": seed}
    if not beta_params:
        return {}, {**diagnostics, "status": "no_suppliers"}

    correlation = None
    if rho is None:
        obs = _weekly_fill_matrix(conn, sorted(beta_params))
        if obs:
            correlation, keys, diag = estimate_rank_correlation(
                obs, min_overlap=min_overlap)
            # Reorder to the sorted key order used by the sampler.
            order = [keys.index(k) for k in sorted(beta_params) if k in keys]
            if len(order) == len(beta_params):
                correlation = correlation[np.ix_(order, order)]
                off = correlation[~np.eye(len(order), dtype=bool)]
                diagnostics.update(
                    correlation_source="estimated_from_history",
                    mean_pairwise_rank_correlation=round(float(np.mean(off)), 4),
                    **diag)
            else:
                correlation = None
        if correlation is None:
            diagnostics["correlation_source"] = (
                "none available — falling back to INDEPENDENT draws; "
                "aggregate supply risk will be understated if these "
                "suppliers share a weather region")
            diagnostics["mean_pairwise_rank_correlation"] = 0.0
    else:
        diagnostics.update(correlation_source="operator_supplied_rho",
                           mean_pairwise_rank_correlation=float(rho))

    gen = CopulaScenarioGenerator(copula=copula, df=df, seed=seed)
    draws = gen.sample_beta_marginals(
        beta_params, len(scenario_indices), correlation=correlation, rho=rho)

    out: dict = {}
    for sid, vals in draws.items():
        for k, omega in enumerate(scenario_indices):
            out[(int(omega), sid)] = float(vals[k])
    return out, diagnostics


def _weekly_fill_matrix(conn, supplier_ids: list[str]) -> dict[str, np.ndarray]:
    """Per-supplier weekly fill-rate series aligned on a common week grid."""
    try:
        df = conn.execute("""
            SELECT supplier_id,
                   DATE_TRUNC('week', delivery_date) AS wk,
                   SUM(COALESCE(accepted_quantity, delivered_quantity))
                       / NULLIF(SUM(ordered_quantity), 0) AS fill
            FROM stg_supplier_deliveries
            WHERE ordered_quantity > 0 AND delivery_date IS NOT NULL
            GROUP BY 1, 2
        """).df()
    except Exception:
        return {}
    if df.empty:
        return {}
    weeks = sorted(df["wk"].unique())
    index = {w: i for i, w in enumerate(weeks)}
    out: dict[str, np.ndarray] = {}
    for sid in supplier_ids:
        series = np.full(len(weeks), np.nan)
        sub = df[df["supplier_id"] == sid]
        for _, r in sub.iterrows():
            series[index[r["wk"]]] = float(r["fill"])
        if np.isfinite(series).sum() >= 2:
            out[sid] = series
    return out
