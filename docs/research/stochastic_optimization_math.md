# Stochastic Optimization: Theory, Audit, and Corrections

Research basis for `optimization/`, and the record of what an audit against
that theory found. Claims graded **[V]** verified against the primary
source, **[P]** partial, **[U]** unverified.

The headline: **four real defects were found, three of them silently
producing wrong numbers.** Each is described below with the reproduction
that confirmed it.

---

## 1. The theory the code must satisfy

**Birge, J.R. & Louveaux, F. (1997).** *Introduction to Stochastic
Programming*, Springer. Ch. 4, pp. 137–152. [V]

The two-stage program:

```
min  cᵀx + E_ξ[Q(x,ξ)]      s.t. Ax = b, x ≥ 0
Q(x,ξ) = min{ qᵀy | Wy = h(ξ) − T(ξ)x, y ≥ 0 }
```

Four quantities, easily confused and previously confused in our code:

| Symbol | Meaning |
|---|---|
| **RP** | the recourse problem — solve the full stochastic model |
| **EV** | the expected-value problem — replace ξ by its mean, solve once |
| **EEV** | *expected result of using the EV solution* — fix EV's first-stage decision, evaluate its expected cost over all scenarios |
| **WS** | wait-and-see — average of per-scenario optima |

```
VSS  = EEV − RP        EVPI = RP − WS
WS ≤ RP ≤ EEV          (Proposition 1, p. 140)
VSS ≥ 0 and EVPI ≥ 0   (Proposition 5a, p. 142)
```

**When is VSS = 0?** (p. 142) When the optimal first-stage decision does
not depend on the realisation — solving for the mean gives the same answer
as solving for the distribution. Birge & Louveaux also show VSS does **not**
increase monotonically with Var(ξ): "a general rule is unlikely to be
found."

**Newsvendor** (§1.1e, pp. 15–18) [V]: `x* = F⁻¹(c_u/(c_u+c_o))`. The
optimum equals the mean only when the critical fractile is 0.5 (`c_u = c_o`)
**and** the demand distribution is symmetric.

---

## 2. Defects found and fixed

### 2.1 VSS was computing the wrong quantity — reported as negative

`compute_vss` returned `EV_objective − RP`. That is not VSS. EV solves an
easier problem (one averaged scenario instead of the distribution), so by
Jensen `EV ≤ RP` and the difference is typically **negative**.

Reproduced before the fix on a deliberately asymmetric instance:

```
reported VSS: -5,383.64
```

A negative VSS is impossible by construction. Anyone reading that number
would conclude stochastic modelling had negative value.

**Fixed** by implementing EEV properly: solve EV, *fix* its first-stage
decision, re-optimise only the recourse across all scenarios. Both EV and
EEV are now built inside the *same* model class as RP, so the three are
genuinely comparable — mixing model classes was part of what made the old
number meaningless.

After the fix, on an interior newsvendor instance (c=2, c_u=10, c_o=1):

| quantity | value |
|---|---|
| critical fractile (c_u−c)/(c_u+c_o) | 0.7273 |
| theory optimum F⁻¹(0.727) | 1,181.4 kg |
| **RP actually committed** | **1,189.1 kg** |
| EV commits (the mean) | 1,004.6 kg |
| VSS | 233.43 (7.08% of EEV) |

RP reproduces the analytical newsvendor quantile to within 0.7% — the
residual is SAA sampling error. `EV ≤ RP ≤ EEV` holds.

### 2.2 And this finally explains the VSS ≈ 0 puzzle

An earlier stress test found the stochastic optimizer tying the
deterministic one. With the computation corrected, the cause is visible and
matches theory exactly — VSS is governed by **cost asymmetry**, because
that is what moves the critical fractile away from the mean:

| c_under | c_over | fractile | x*_theory | x*_RP | VSS | VSS % |
|---|---|---|---|---|---|---|
| 3 | 3 | 0.500 | 1,000 | 980 | 1.12 | **0.21%** |
| 4 | 2 | 0.667 | 1,108 | 1,051 | 44.11 | 8.15% |
| 6 | 2 | 0.750 | 1,169 | 1,123 | 136.50 | 18.92% |
| 9 | 1 | 0.900 | 1,320 | 1,265 | 509.08 | **56.45%** |

At symmetric costs over symmetric demand the critical fractile lands on the
mean, the EV decision is already optimal, and VSS is genuinely zero — the
math being right, not the model failing. Push the costs apart and VSS grows
to 56%. Pinned by `test_vss_grows_with_cost_asymmetry`.

The practical reading: **the stochastic layer earns its keep when overage
and underage costs are lopsided** — which for perishables they usually are,
since a stockout costs a customer relationship and a spoiled pallet costs
its landed cost.

### 2.3 Spot purchases were priced from a hardcoded fallback

`LPBaseline` priced spot via `price[(None, j, t)]` — a key that can never
exist, since the dict is keyed by real supplier ids. **Every spot purchase
silently used the 2.0 fallback.** With real contract prices above $2.00,
spot looked cheaper than any contract, so the LP committed nothing and
bought everything on spot.

Reproduced: contract at $10.00/kg, demand 1,000 kg.

```
committed:      0.0 kg   spot:   1000.0 kg   obj: 2600.00
                                  == 1000 × 2.0 fallback × 1.3
```

The objective is *exactly* the fallback arithmetic. Fixed to use the
per-product mean contract price; the same instance now commits 1,000 kg at
the real $10.00/kg. This matters beyond the baseline itself: the
deterministic LP is what the stochastic model is *compared against*, so the
defect corrupted every comparison.

### 2.4 CVaR had three defects at once

Rockafellar & Uryasev (2000), *Journal of Risk* 2(3):21–42 [V], Theorem 1:

```
CVaR_α[Z] = min_η { η + (1−α)⁻¹ · E[(Z − η)⁺] }
```

with scenario probabilities p_ω:  `η + (1−α)⁻¹ Σ_ω p_ω z_ω`.

1. **The tail was averaged with a uniform 1/N** while the expectation term
   used p_ω. Whenever weights are non-uniform — precisely what
   `scenario_reduction` produces — the estimator was simply wrong.
2. **The first-stage cost sat inside the expectation term but not the CVaR
   term.** Since `c'x` is deterministic, `CVaR(c'x + Q) = c'x + CVaR(Q)`;
   omitting it under-weighted procurement cost by a factor λ and biased the
   model toward over-committing whenever λ < 1.
3. **There was no unmet-demand variable at all**, so the risk-averse
   variant could not represent a lost sale and was forced to buy spot at
   any price. The main two-stage model has always had one — the two were
   not comparable.

All three fixed; per-product penalties and the newsvendor objective now
pass through too, so changing risk preference no longer silently changes
the cost model.

### 2.5 Scenario weights were inconsistent and unnormalised

A scenario missing from the weight map was counted at `1/N` in the
objective but at `0` when reporting expected spot/waste/unmet — the
reported quantities understated what the objective had optimised. And the
weights were never normalised: an unnormalised vector multiplies the
expectation term by an arbitrary constant while leaving the first-stage
cost alone, which **changes the optimal trade-off**, not just the reported
number. Both fixed in `_normalized_weights`, with a test that scaling all
weights by a constant leaves the decision unchanged.

---

## 3. Γ-robust: corrected to the actual Bertsimas-Sim structure

**Bertsimas, D. & Sim, M. (2004).** "The Price of Robustness."
*Operations Research* 52(1):35–53. doi:10.1287/opre.1030.0065 [V]

The budget of uncertainty Γ protects against at most Γ parameters deviating
adversarially, with a fractional allowance for the (Γ+1)-th. Γ=0 is the
nominal problem; Γ=|J| recovers Soyster (1973), *Oper. Res.* 21(5):1154 [V].

**What was wrong:** the implementation spread the budget *uniformly*
(`gamma_factor = Γ/(J·T)`) while documenting itself as "mathematically
equivalent to a Bertsimas-Sim Γ-robust counterpart." It is not. Uniform
spreading protects a little against everything; the actual counterpart
protects *fully* against the Γ worst deviations and not at all against the
rest. Since each product's deviation scales with its own demand, the
uniform version systematically under-protected the large-demand products
that drive cost.

Now allocated as the theory specifies: sort deviations, protect the ⌊Γ⌋
largest fully, give the next the remainder.

**Probabilistic guarantee** (Theorem 2): `Pr(violation) ≤ exp(−Γ²/(2n))`.
Exposed as `violation_probability_bound`, and inverted by
`gamma_for_target_risk` so an operator can say "at most a 5% chance of
being short" instead of guessing Γ.

> **Caveat carried in the code:** the bound assumes *independent* deviations.
> Regionally correlated weather shocks violate that, and the true violation
> probability is then higher than the bound suggests. See
> `agronomy/systemic_risk.py`.

---

## 4. New: are our scenario counts actually enough?

**Kleywegt, Shapiro & Homem-de-Mello (2002).** *SIAM J. Optimization*
12(2):479–502. doi:10.1137/S1052623499363220 [V]
**Mak, Morton & Wood (1999).** *Oper. Res. Letters* 24(1):47–56.
doi:10.1016/S0167-6377(98)00054-6 [P]

The SAA objective is **downward-biased** for minimisation: `E[v̂_N] ≤ v*`.
The sampled optimum looks better than the truth, and looks better the fewer
scenarios you use — optimistic exactly where you would most want a warning.
Nothing in the stack previously measured this.

`optimization/saa_bounds.py` implements the multiple-replication procedure:
M independent replications give a statistical lower bound; the candidate
decision evaluated against the full scenario pool gives an upper bound.

In-sample stability on a test instance — behaving exactly as theory says:

| N | mean objective | CV across replications |
|---|---|---|
| 10 | 676.2 | 22.6% |
| 25 | 687.1 | 12.5% |
| 50 | 697.3 | 9.7% |
| 100 | 745.4 | 6.2% |
| 200 | 722.8 | 4.6% |

The objective rises (bias shrinking) and the spread narrows, as predicted.

Optimality gap by scenario count:

| N | gap % |
|---|---|
| 10 | 32.8% |
| 25 | 13.2% |
| 100 | 7.2% |
| 400 | 5.3% |

**Consequence for us:** the production default is `n_scenarios = 100`,
where the gap is roughly 7%. **Differences smaller than that between
policies are sampling noise, not findings.** Any VSS or policy comparison
we report should be read against this.

One honest note on the estimator itself: the first implementation evaluated
the upper bound on a bootstrap resample, which injected enough noise that
the gap did not shrink with N (stuck near 11–13% for both N=25 and N=200).
Evaluating against the full pool fixed it.

**No universal "how many scenarios" number exists in the literature** [U] —
the guidance is instance-specific stability testing, which is why this is a
measurement rather than a constant.

---

## 5. Random yield: what the literature says we should expect

| Finding | Source | Grade |
|---|---|---|
| Yield taxonomy: stochastically proportional, random capacity, all-or-nothing | Yano & Lee (1995) *Oper. Res.* 43(2):311–334 | [V] |
| Under multiplicative random yield, **base-stock optimality breaks down** — a "non-order-up-to" policy is optimal | Henig & Gerchak (1990) *Oper. Res.* 38(4):634–643 | [V] |
| With unreliable suppliers a newsvendor orders **more in aggregate but achieves a LOWER fill rate** than the reliable benchmark | Dada, Petruzzi & Schwarz (2007) *M&SOM* 9(1):9–32 | [V] |
| Under **random capacity** (as opposed to yield) the order-up-to level is unaffected — structure is preserved | Ciarallo, Akella & Morton (1994) *Mgmt Sci* 40(3):320–332 | [P] |
| Expected profit **decreases** monotonically as supply correlation rises; **increases** as supply-demand correlation rises | Sting & Huchzermeier (2014) *POM* 23(7):1212–1226 | [V] |
| Supplier-yield correlation is explicitly "surprisingly very rare" in the literature; positive correlation favours consolidation, negative favours splitting | secondary synthesis | [P] |

**The "divide by E[Y]" heuristic** for inflating orders under random yield
is approximate only — Gerchak, Vickson & Parlar (1988) show the expected
yield at the optimal lot size does not generally equal the inventory gap
[P]. **No universal closed-form inflation factor appears to exist** [U];
the literature gives structural results, not a multiplier.

**Consequence for our `diversification_cap` constraint:** it forces
commitment to be spread across suppliers. Under *positively correlated*
yields — which is exactly what regional weather produces — that spreading
is not a hedge, because the suppliers fail together. The constraint remains
useful for relationship and contractual reasons, but it should not be sold
as risk reduction without checking the measured correlation first
(`agronomy/systemic_risk.estimate_shock_correlation`).

**Our `service_level_floor` is a Type-2 (fill-rate) constraint in
expectation**, not Type-1 (cycle service level). Type 1 is the probability
of *no* stockout in a cycle; Type 2 is the *fraction of demand* met. Type 2
is numerically much higher for the same policy, since a small shortfall
destroys Type 1 but barely dents Type 2. Worth stating in any operator
conversation, since "99% service" means very different things under each.

---

## 6. Perishables

| Finding | Source | Grade |
|---|---|---|
| Optimal policy depends on the **full age distribution** of inventory, making exact DP intractable and motivating the heuristic literature | Nahmias (1982) *Oper. Res.* 30(4):680–708 | [V] |
| FIFO issuing is optimal for standard cost structures; the exception is declining prices with age | Pierskalla & Roach (1972) *Mgmt Sci* 18(11):603–614 | [V] |
| Modern reviews | Karaesmen, Scheller-Wolf & Deniz (2011), Springer ch.; Bakker, Riezebos & Teunter (2012) *EJOR* 221(2):275–284 | [V] |

Citation correction: "Nahmias (1975, 1982)" is **two different papers** —
1982 is the review; Nahmias (1975) *Oper. Res.* 23(4):735–749 is a separate
research paper on optimal ordering for fixed-lifetime perishables. Our
notes previously ran them together.

---

## 7. Empirical value — and the gap in it

| Finding | Source | Grade |
|---|---|---|
| Quick-response probabilistic forecasting raised profits ~60% over the firm's existing process at a ski-wear manufacturer | Fisher & Raman (1996) *Oper. Res.* 44(1):87–99 | [V] citation, [P] percentages |
| Operational systems achieve 6–10% MAPE on national crop yields | van der Velde & Nisini (2019) *Agric. Syst.* 168:203 | [V] |

**Not found:** a peer-reviewed, inventory- or perishables-specific study
reporting VSS with a clean percentage and a named company [U]. Generic
cross-domain VSS figures (energy dispatch, HVAC) exist but should **not** be
cited as if they transferred to perishable procurement. Also not found: a
credible honest-negative-result paper for this domain — likely publication
bias rather than absence of such results.

---

## 8. Implementation map

| Module | Implements | Anchored on |
|---|---|---|
| `two_stage_sp.py` | two-stage SAA extensive form; **corrected** VSS = EEV − RP; fixed-first-stage evaluation; normalised weights | Birge & Louveaux Ch. 4 |
| `lp_baseline.py` | deterministic EV problem; **fixed** spot pricing | — |
| `cvar_extension.py` | mean-CVaR, **corrected** probability weighting, first-stage handling, unmet variable | Rockafellar & Uryasev (2000) Thm 1–2 |
| `gamma_robust_lp.py` | **corrected** Γ-budget allocation to worst deviations; violation bound and its inverse | Bertsimas & Sim (2004) Thm 1–2; Soyster (1973) |
| `saa_bounds.py` | **new** — optimality-gap estimation, in-sample stability curve | Kleywegt et al. (2002) §3.2–3.3; Mak et al. (1999) |
| `scenario_reduction.py` | backward reduction with probability redistribution | Dupačová, Gröwe-Kuska & Römisch (2003) [P] |

Note on `scenario_reduction`: the docstring says "fast forward selection"
but the implementation is **backward reduction**. Both appear in this
literature; "fast forward selection" is a later Heitsch & Römisch
refinement rather than part of the 2003 paper [P]. The implementation is
correct for backward reduction; only the label was wrong.
