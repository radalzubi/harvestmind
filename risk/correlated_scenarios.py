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
    """GAUSSIAN-ONLY identity rho_latent = 2 sin(pi rho_s / 6).

    Valid for the Gaussian copula only. It does NOT give the correct
    latent parameter for a t copula at finite degrees of freedom, so it
    must not be used on the shared path — see kendall_to_latent.
    """
    return 2.0 * np.sin(np.pi * np.asarray(rho_spearman, dtype=float) / 6.0)


def pearson_to_spearman(rho_pearson: float | np.ndarray) -> float | np.ndarray:
    """Inverse of the Gaussian-only identity: rho_s = (6/pi) arcsin(rho/2)."""
    r = np.clip(np.asarray(rho_pearson, dtype=float), -1.0, 1.0)
    return (6.0 / np.pi) * np.arcsin(r / 2.0)


def kendall_to_latent(tau: float | np.ndarray) -> float | np.ndarray:
    """Kendall's tau -> latent elliptical correlation: rho = sin(pi tau / 2).

    THE CONVERSION THAT WAS MISSING. A rank-correlation matrix is NOT the
    latent correlation parameter of a copula, and feeding one straight into
    the Cholesky factor — as this module previously did — silently targets
    the wrong dependence. The error grows with |rho|: a Spearman target of
    0.8 passed as latent produces materially less dependence than intended.

    Kendall's tau is used rather than Spearman because this identity holds
    for the WHOLE elliptical family — Gaussian and t alike, at any degrees
    of freedom. The Spearman identity rho = 2 sin(pi rho_s / 6) is
    Gaussian-specific, so using it on the t path would swap one silent
    misspecification for another.

    Reference: Lindskog, F., McNeil, A. & Schmock, U. (2003), "Kendall's
    tau for elliptical distributions," in *Credit Risk: Measurement,
    Evaluation and Management*, Physica-Verlag, 149-156.
    """
    t = np.clip(np.asarray(tau, dtype=float), -1.0, 1.0)
    return np.sin(np.pi * t / 2.0)


def latent_to_kendall(rho: float | np.ndarray) -> float | np.ndarray:
    """Inverse: tau = (2/pi) arcsin(rho)."""
    r = np.clip(np.asarray(rho, dtype=float), -1.0, 1.0)
    return (2.0 / np.pi) * np.arcsin(r)


class CorrelationValidationError(ValueError):
    """A correlation matrix failed a structural check."""


def validate_correlation_matrix(
    matrix: np.ndarray, tol: float = 1e-8,
) -> dict:
    """Structural checks on a correlation matrix. Reports, does not repair.

    Checks, in the order a failure would bite:
      * square and finite
      * unit diagonal
      * symmetric
      * entries within [-1, 1]
      * positive semidefinite (minimum eigenvalue >= -tol)

    Returned as a diagnostic dict rather than raising, so a caller can log
    exactly which property failed and how badly before deciding whether to
    regularise or refuse. ``nearest_positive_semidefinite`` performs the
    repair; keeping the two separate means a repair is always a recorded
    decision rather than something that happened invisibly.
    """
    m = np.asarray(matrix, dtype=float)
    out: dict = {"n": None, "square": False, "finite": False,
                 "unit_diagonal": False, "symmetric": False,
                 "in_range": False, "positive_semidefinite": False,
                 "min_eigenvalue": None, "max_asymmetry": None, "valid": False}
    if m.ndim != 2 or m.shape[0] != m.shape[1] or m.shape[0] == 0:
        return out
    out["square"] = True
    out["n"] = int(m.shape[0])
    if not np.all(np.isfinite(m)):
        return out
    out["finite"] = True
    out["unit_diagonal"] = bool(np.allclose(np.diag(m), 1.0, atol=1e-8))
    asym = float(np.max(np.abs(m - m.T))) if m.size else 0.0
    out["max_asymmetry"] = asym
    out["symmetric"] = bool(asym <= tol)
    out["in_range"] = bool(np.all(m >= -1.0 - tol) and np.all(m <= 1.0 + tol))
    sym = (m + m.T) / 2.0
    min_eig = float(np.min(np.linalg.eigvalsh(sym)))
    out["min_eigenvalue"] = min_eig
    out["positive_semidefinite"] = bool(min_eig >= -tol)
    out["valid"] = bool(out["unit_diagonal"] and out["symmetric"]
                        and out["in_range"] and out["positive_semidefinite"])
    return out


def shrink_correlation(
    matrix: np.ndarray, target_rho: float = 0.0, weight: float = 0.0,
) -> np.ndarray:
    """Linear (Ledoit-Wolf style) shrinkage toward a structured target.

    Regularisation for the sparse case. A correlation matrix estimated from
    short, unequal, partly-overlapping supplier histories is noisy and
    frequently indefinite; shrinking it toward an equicorrelated target
    stabilises it before any repair is needed:

        R_shrunk = (1 - w) * R_hat + w * R_target

    ``weight`` should rise as the evidence thins — see
    ``recommended_shrinkage`` for the rule we apply, which is a documented
    heuristic rather than an estimated optimal intensity.
    """
    m = np.asarray(matrix, dtype=float)
    w = float(np.clip(weight, 0.0, 1.0))
    if w <= 0.0:
        return m
    target = equicorrelation_matrix(m.shape[0], target_rho)
    out = (1.0 - w) * m + w * target
    np.fill_diagonal(out, 1.0)
    return out


def recommended_shrinkage(n_periods: int, n_entities: int) -> float:
    """Shrinkage intensity implied by how thin the joint history is.

    A correlation matrix over k entities has k(k-1)/2 free parameters, all
    estimated from the SAME n periods. The ratio of parameters to periods
    is the honest measure of how over-fitted the estimate is:

        w = clip( params / (params + n_periods), 0.1, 0.9 )

    With 6 suppliers (15 pairs) and 10 shared weeks the weight is 0.6 —
    the estimate is mostly discarded, which is correct: fifteen
    correlations cannot be learned from ten observations. The floor of 0.1
    keeps a little regularisation even with long histories; the ceiling of
    0.9 stops the estimate being ignored entirely. Both bounds are
    judgement, and are stated as such.
    """
    if n_entities < 2 or n_periods <= 0:
        return 1.0
    params = n_entities * (n_entities - 1) / 2.0
    return float(np.clip(params / (params + n_periods), 0.1, 0.9))


def nearest_positive_semidefinite(matrix: np.ndarray, eps: float = 1e-8) -> np.ndarray:
    """Project a correlation matrix to the nearest PSD correlation matrix.

    An estimated correlation matrix from short, unequal histories is often
    slightly indefinite, and Cholesky then fails. Clipping the eigenvalues
    at a small positive floor and renormalising the diagonal is the
    standard repair; it changes the matrix by the minimum needed to make
    sampling possible. Symmetry is imposed first, since ``eigvalsh``
    assumes it and would otherwise silently use one triangle.
    """
    m = np.asarray(matrix, dtype=float)
    m = (m + m.T) / 2.0
    vals, vecs = np.linalg.eigh(m)
    if np.all(vals > eps):
        np.fill_diagonal(m, 1.0)
        return m
    vals = np.clip(vals, eps, None)
    out = vecs @ np.diag(vals) @ vecs.T
    d = np.sqrt(np.clip(np.diag(out), eps, None))
    out = out / np.outer(d, d)
    out = (out + out.T) / 2.0
    np.fill_diagonal(out, 1.0)
    return out


# Backwards-compatible alias: the previous name promised definiteness the
# eigenvalue floor does not strictly deliver at the boundary.
nearest_positive_definite = nearest_positive_semidefinite


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


def joint_coverage(
    observations: dict[str, np.ndarray], min_overlap: int = 4,
) -> dict:
    """Measure how much genuinely JOINT history exists.

    THE MISTAKE THIS REPLACES. Coverage was previously summarised as the
    largest number of finite observations held by any ONE entity. That is
    not joint history at all: supplier A observed January-June and supplier
    B observed July-December would report 30 periods while sharing not a
    single week, and dependence cannot be estimated from disjoint records.

    What actually matters is PAIRWISE OVERLAP, so that is what is reported:
    per-pair counts, their distribution, the share of pairs clearing
    ``min_overlap``, the number of periods in which two or more entities
    were observed together, and whether the graph of adequately-overlapping
    pairs is CONNECTED. Connectivity matters because a matrix whose
    estimable pairs form disjoint clusters cannot support a coherent joint
    dependence structure — the cross-cluster entries would all be defaults
    wearing the label "estimated".
    """
    keys = sorted(observations)
    n = len(keys)
    out: dict = {"n_entities": n, "min_overlap": min_overlap}
    if n < 2:
        return {**out, "n_pairs": 0, "pairs_adequate": 0,
                "pct_pairs_adequate": 0.0, "min_pair_overlap": 0,
                "median_pair_overlap": 0.0, "max_pair_overlap": 0,
                "n_joint_periods": 0, "connected": False}

    masks = {k: np.isfinite(np.asarray(observations[k], dtype=float))
             for k in keys}
    overlaps: list[int] = []
    adjacency = np.zeros((n, n), dtype=bool)
    for i in range(n):
        for j in range(i + 1, n):
            ov = int(np.sum(masks[keys[i]] & masks[keys[j]]))
            overlaps.append(ov)
            if ov >= min_overlap:
                adjacency[i, j] = adjacency[j, i] = True

    # Periods in which at least two entities were observed together.
    stacked = np.vstack([masks[k] for k in keys])
    n_joint = int(np.sum(stacked.sum(axis=0) >= 2))

    # Connectivity of the adequately-overlapping graph, by BFS.
    seen = {0}
    frontier = [0]
    while frontier:
        node = frontier.pop()
        for other in range(n):
            if adjacency[node, other] and other not in seen:
                seen.add(other)
                frontier.append(other)

    n_pairs = len(overlaps)
    adequate = int(np.sum(np.asarray(overlaps) >= min_overlap))
    return {
        **out,
        "n_pairs": n_pairs,
        "pairs_adequate": adequate,
        "pct_pairs_adequate": round(adequate / n_pairs * 100.0, 1) if n_pairs else 0.0,
        "min_pair_overlap": int(np.min(overlaps)),
        "median_pair_overlap": float(np.median(overlaps)),
        "max_pair_overlap": int(np.max(overlaps)),
        "n_joint_periods": n_joint,
        "connected": bool(len(seen) == n),
    }


def estimate_rank_correlation(
    observations: dict[str, np.ndarray],
    min_overlap: int = 4,
    default_rho: float = 0.0,
    method: str = "kendall",
) -> tuple[np.ndarray, list[str], dict]:
    """Rank-dependence matrix across entities from aligned observations.

    Returns a matrix on the RANK scale — Kendall's tau by default, which is
    what ``kendall_to_latent`` converts into a copula's latent correlation.
    It is NOT itself a latent correlation matrix and must never be handed
    straight to a Cholesky factor.

    ``observations`` maps entity -> equal-length array of per-period
    values, with NaN where that entity had no delivery in a period. Pairs
    with fewer than ``min_overlap`` shared periods fall back to
    ``default_rho`` rather than reporting a dependence estimated from two
    points, which would be noise presented as signal.
    """
    if method not in ("kendall", "spearman"):
        raise ValueError(f"unknown rank-correlation method {method!r}")
    keys = sorted(observations)
    n = len(keys)
    mat = np.eye(n)
    diagnostics: dict = {"n_entities": n, "pairs_estimated": 0,
                         "pairs_defaulted": 0, "min_overlap": min_overlap,
                         "rank_method": method, "scale": "rank"}
    for i in range(n):
        for j in range(i + 1, n):
            a = np.asarray(observations[keys[i]], dtype=float)
            b = np.asarray(observations[keys[j]], dtype=float)
            ok = np.isfinite(a) & np.isfinite(b)
            if (int(ok.sum()) >= min_overlap
                    and np.std(a[ok]) > 1e-12 and np.std(b[ok]) > 1e-12):
                if method == "kendall":
                    r, _ = stats.kendalltau(a[ok], b[ok])
                else:
                    r, _ = stats.spearmanr(a[ok], b[ok])
                r = float(r) if np.isfinite(r) else default_rho
                diagnostics["pairs_estimated"] += 1
            else:
                r = default_rho
                diagnostics["pairs_defaulted"] += 1
            mat[i, j] = mat[j, i] = r
    diagnostics.update(joint_coverage(observations, min_overlap))
    return mat, keys, diagnostics


@dataclass(frozen=True)
class SupplyRiskPolicy:
    """Explicit, recorded choice of how supplier dependence is modelled.

    WHY THIS IS A POLICY AND NOT A DEFAULT
    --------------------------------------
    Correlated sampling changes the recommended commitment, so which
    dependence model is in force must be an operator-visible decision with
    a name and a rationale, not a constant chosen by whoever wrote the
    module. Two of the parameters below are genuinely unestimated at
    present:

      * ``copula`` — the t copula's advantage over Gaussian is that it has
        nonzero tail dependence. Whether an operator's suppliers actually
        exhibit joint-tail clustering is an empirical question that needs
        joint history to answer.
      * ``df`` — the t degrees of freedom control HOW MUCH tail clustering.
        The value 5 is a convention borrowed from financial risk practice,
        not something fitted to agricultural supply data.

    Because both are judgements, ``INDEPENDENT`` is the default policy.
    That is the conservative choice in the sense that matters here: it is
    the behaviour the system has always had, so enabling dependence is a
    deliberate act with a documented reason rather than a silent change to
    every operator's recommendation.

    ``mode``:
      "independent"    each supplier drawn from its own Beta (legacy)
      "equicorrelated" one operator-supplied rho, no estimation
      "estimated"      rank correlation from the operator's own history,
                       shrunk toward equicorrelation by evidence weight
    """

    mode: str = "independent"
    copula: str = "gaussian"
    df: float = 5.0
    # Target dependence on the KENDALL'S TAU scale, not a latent
    # correlation. tau is used because rho_latent = sin(pi*tau/2) holds for
    # the whole elliptical family (Gaussian and t at any df), so the same
    # target means the same thing whichever copula is selected.
    rho: float | None = None
    min_overlap: int = 4
    min_periods_for_estimation: int = 12
    # Minimum share of supplier PAIRS that must clear min_overlap before a
    # full matrix may be called "estimated" rather than mostly-defaulted.
    min_pct_pairs_adequate: float = 60.0
    require_connected: bool = True
    # What to do when an explicitly requested correlated policy cannot be
    # honoured. "raise" is the default precisely because a silent switch to
    # independent draws changes the recommended commitment while looking
    # like a normal result.
    on_failure: str = "raise"
    seed: int = 42

    def __post_init__(self):
        if self.mode not in ("independent", "equicorrelated", "estimated"):
            raise ValueError(f"unknown supply-risk mode {self.mode!r}")
        if self.copula not in ("gaussian", "t"):
            raise ValueError(f"unknown copula {self.copula!r}")
        if self.mode == "equicorrelated" and self.rho is None:
            raise ValueError("mode='equicorrelated' requires an explicit rho "
                             "(target Kendall's tau)")
        if self.on_failure not in ("raise", "independent"):
            raise ValueError(f"unknown on_failure {self.on_failure!r}; use "
                             "'raise' or 'independent'")

    @property
    def enabled(self) -> bool:
        return self.mode != "independent"

    def describe(self) -> str:
        if not self.enabled:
            return ("independent supplier draws; aggregate supply risk is "
                    "UNDERSTATED if these suppliers share a weather region")
        if self.mode == "equicorrelated":
            return (f"{self.copula} copula, operator-supplied rank "
                    f"correlation {self.rho}")
        return (f"{self.copula} copula, rank correlation estimated from "
                f"delivery history and shrunk toward equicorrelation")


# The policy in force when a caller does not supply one. Independent by
# design — see SupplyRiskPolicy for why this is not the t copula.
DEFAULT_SUPPLY_RISK_POLICY = SupplyRiskPolicy()


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


def _estimation_refusal(
    obs: dict | None, cov: dict | None, pol: "SupplyRiskPolicy", n_ent: int,
) -> dict | None:
    """Decide whether joint history can support a full matrix.

    Returns a diagnostics dict describing the refusal, or None to proceed.
    The checks are on genuine PAIRWISE overlap, not on the longest single
    series: two suppliers with 30 observations each but no shared weeks
    carry no information about their dependence, and filling the matrix
    with zeros while calling it "estimated" would be a lie about provenance.
    """
    base = {"mean_latent_correlation": 0.0,
            "min_periods_required": pol.min_periods_for_estimation}
    if not obs or cov is None:
        return {**base, "correlation_source": "refused_no_history",
                "note": "no delivery history available to estimate dependence"}
    base.update({k: cov[k] for k in (
        "n_joint_periods", "n_pairs", "pairs_adequate", "pct_pairs_adequate",
        "min_pair_overlap", "median_pair_overlap", "max_pair_overlap",
        "connected")})
    degraded = (" Degraded to INDEPENDENT draws; aggregate supply risk is "
                "understated if these suppliers share a region.")

    if len(obs) < n_ent:
        return {**base, "correlation_source": "refused_incomplete_coverage",
                "note": (f"only {len(obs)} of {n_ent} suppliers have usable "
                         f"series." + degraded)}
    if cov["n_joint_periods"] < pol.min_periods_for_estimation:
        return {**base, "correlation_source": "refused_insufficient_history",
                "note": (f"{cov['n_joint_periods']} periods with two or more "
                         f"suppliers observed together, below the required "
                         f"{pol.min_periods_for_estimation}." + degraded)}
    if cov["pct_pairs_adequate"] < pol.min_pct_pairs_adequate:
        return {**base, "correlation_source": "refused_sparse_pairs",
                "note": (f"only {cov['pct_pairs_adequate']:.0f}% of supplier "
                         f"pairs clear {pol.min_overlap} shared periods "
                         f"(need {pol.min_pct_pairs_adequate:.0f}%); most of "
                         "the matrix would be defaults wearing the label "
                         "'estimated'." + degraded)}
    if pol.require_connected and not cov["connected"]:
        return {**base, "correlation_source": "refused_disconnected",
                "note": ("the adequately-overlapping supplier pairs form "
                         "disjoint clusters, so no coherent joint dependence "
                         "structure can be estimated across them." + degraded)}
    return None


class CorrelatedScenarioError(RuntimeError):
    """An explicitly requested correlation policy could not be honoured."""


def correlated_yield_scenarios(
    conn,
    scenario_indices: list[int],
    policy: SupplyRiskPolicy | None = None,
) -> tuple[dict, dict]:
    """Supplier fill draws under an explicit supply-risk policy.

    Returns ``({(scenario_index, supplier_id): fill}, diagnostics)`` — the
    same mapping shape ``TwoStageStochasticLP`` already consumes, so this
    substitutes without touching the optimizer.

    HOW CORRELATION IS OBTAINED, in the order attempted:

    1. ``mode="independent"`` (the default) — no correlation at all. The
       diagnostics say so explicitly, including that aggregate risk is
       understated when suppliers share a weather region.
    2. ``mode="equicorrelated"`` — a single operator-supplied rank
       correlation. No estimation, no pretence of one.
    3. ``mode="estimated"`` — pairwise Spearman correlation of weekly fill
       rates on shared weeks, then:
         a. pairs with fewer than ``min_overlap`` shared weeks are set to 0
            rather than reporting a correlation computed from two points;
         b. the whole matrix is SHRUNK toward equicorrelation with weight
            ``recommended_shrinkage(n_periods, n_entities)``, because k
            suppliers imply k(k-1)/2 correlations all estimated from the
            same n weeks;
         c. the result is validated (symmetry, unit diagonal, range, PSD)
            and projected to the nearest PSD matrix if needed;
         d. if fewer than ``min_periods_for_estimation`` weeks of joint
            history exist, estimation is REFUSED and the policy degrades to
            independent, recorded as such.

    Every one of those branches is reported in the returned diagnostics, so
    a plan can always be traced back to the dependence assumption behind it.
    """
    from risk.supplier_distribution import supplier_fill_distributions

    pol = policy or DEFAULT_SUPPLY_RISK_POLICY
    dists = supplier_fill_distributions(conn, quantile=0.10)
    beta_params = {sid: (float(d["alpha"]), float(d["beta"]))
                   for sid, d in dists.items() if sid != "_prior"}

    diagnostics: dict = {
        "n_suppliers": len(beta_params),
        "policy_mode": pol.mode,
        "policy_description": pol.describe(),
        "copula": pol.copula if pol.enabled else None,
        "df": pol.df if (pol.enabled and pol.copula == "t") else None,
        "seed": pol.seed,
    }
    if not beta_params:
        return {}, {**diagnostics, "status": "no_suppliers"}

    keys_sorted = sorted(beta_params)
    n_ent = len(keys_sorted)
    correlation = None

    if pol.mode == "equicorrelated":
        # pol.rho is a target KENDALL'S TAU; convert once to the latent
        # parameter the copula actually consumes.
        latent_rho = float(kendall_to_latent(float(pol.rho)))
        correlation = equicorrelation_matrix(n_ent, latent_rho)
        diagnostics.update(correlation_source="operator_supplied_tau",
                           target_kendall_tau=float(pol.rho),
                           mean_latent_correlation=round(latent_rho, 4),
                           shrinkage_weight=0.0)

    elif pol.mode == "estimated":
        obs = _weekly_fill_matrix(conn, keys_sorted)
        cov = joint_coverage(obs, pol.min_overlap) if obs else None
        refusal = _estimation_refusal(obs, cov, pol, n_ent)

        if refusal is not None:
            diagnostics.update(refusal)
        else:
            raw_tau, keys, diag = estimate_rank_correlation(
                obs, min_overlap=pol.min_overlap, method="kendall")
            order = [keys.index(k) for k in keys_sorted if k in keys]
            raw_tau = raw_tau[np.ix_(order, order)]

            # Shrink on the RANK scale, where zero means independence for
            # every copula, then convert once to the latent parameter.
            w = recommended_shrinkage(cov["n_joint_periods"], n_ent)
            tau = shrink_correlation(raw_tau, target_rho=0.0, weight=w)

            # THE CONVERSION. A rank matrix is not a latent correlation;
            # feeding tau straight to Cholesky silently targets the wrong
            # dependence, and the error grows with |tau|.
            latent = np.asarray(kendall_to_latent(tau), dtype=float)
            np.fill_diagonal(latent, 1.0)

            check = validate_correlation_matrix(latent)
            if not check["valid"]:
                latent = nearest_positive_semidefinite(latent)
                diagnostics["regularized"] = True
                diagnostics["pre_repair_min_eigenvalue"] = check["min_eigenvalue"]
            correlation = latent

            off = ~np.eye(n_ent, dtype=bool)
            diagnostics.update(
                correlation_source="estimated_from_history_shrunk",
                rank_scale="kendall_tau",
                shrinkage_weight=round(w, 4),
                raw_mean_pairwise_tau=round(float(np.mean(raw_tau[off])), 4),
                shrunk_mean_pairwise_tau=round(float(np.mean(tau[off])), 4),
                mean_latent_correlation=round(float(np.mean(correlation[off])), 4),
                correlation_validation=validate_correlation_matrix(correlation),
                **{k: v for k, v in diag.items() if k not in ("n_entities",)})

    if correlation is None:
        diagnostics.setdefault("correlation_source", "independent_by_policy")
        diagnostics.setdefault("mean_latent_correlation", 0.0)
        correlation = equicorrelation_matrix(n_ent, 0.0)

    gen = CopulaScenarioGenerator(copula=pol.copula, df=pol.df, seed=pol.seed)
    draws = gen.sample_beta_marginals(
        beta_params, len(scenario_indices), correlation=correlation)

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
