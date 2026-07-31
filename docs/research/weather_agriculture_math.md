# Weather Predictability and Agricultural Response: Research Basis

Every formula in `agronomy/` traces to a source listed here. Claims are
graded: **[V]** verified against the primary source, **[P]** partial —
confirmed via a reliable secondary source or abstract only, **[U]**
unverified, recorded so it is not mistaken for evidence.

The most useful thing in this document may be the section on what the
literature does *not* support. Skip to "Limits of the evidence" if that is
what you need.

---

## 1. How far ahead weather is knowable

The atmosphere imposes a hard ceiling, and a decision system that ignores
it will be confidently wrong at long lead times.

| Finding | Value | Source | Grade |
|---|---|---|---|
| Practical deterministic limit | ~9–10 days | Zhang et al. 2019, *J. Atmos. Sci.* 76(4):1077–1091, doi:10.1175/JAS-D-18-0269.1 | [V] |
| Theoretical limit | ~2 weeks | same | [V] |
| Gain if initial-condition error fell 10× | +4–5 days | same | [V] |
| Ensemble (probabilistic) skill horizon | 16–23 days | Buizza & Leutbecher 2015, ECMWF Tech Memo 754, doi:10.21957/6g2wkoyb6 | [V] |
| Precipitation skill effectively gone | day 7–9 | ECMWF Newsletter 174; Skok et al. 2016 *QJRMS* 142:2599, doi:10.1002/qj.2849 | [V] |
| Skill improvement rate | ~1 day per decade | Bauer, Thorpe & Brunet 2015, *Nature* 525:47–55, doi:10.1038/nature14956 | [V] via WMO restatement |
| ECMWF ENS / NOAA GEFS members | 51 / 31 | ECMWF FUG; NOAA GEFSv12 documentation | [V] |

**Temperature is far more predictable than precipitation.** This matters
directly: our heat-stress covariate is a temperature threshold, so it sits
on the more predictable side. A rainfall-driven covariate would decay
several days faster, and `SKILL_HORIZON_DAYS` encodes that difference.

**ENSO skill is gated by the calendar, not just lead time.** NOAA's spring
predictability barrier: October-initialised forecasts of the following
Nov–Jan explain ~90% of Niño 3.4 variance; May-initialised forecasts of the
*same* season explain ~50%. Remarkably, an April forecast at 7-month lead
(~38%) can beat an April forecast at 1-month lead (~33%) — lead time alone
does not determine skill. Source: L'Heureux 2015, NOAA Climate.gov ENSO
Blog. [V]

**Implemented in** `agronomy/forecast_skill.py`. The decay curve
ρ(L) = exp(−L/τ) is anchored so ρ reaches the floor exactly at each
published horizon. This is interpolation between published endpoints, not a
fit to our own verification data — stated plainly because the difference
matters, and an operator with enough history should replace it with
measured regional skill.

---

## 2. Weather to yield: the response is nonlinear and asymmetric

The canonical result is that yields rise gently with heat up to a threshold
and fall steeply above it. Using average temperature misses this entirely.

**Schlenker, W. & Roberts, M.J. (2009).** "Nonlinear temperature effects
indicate severe damages to U.S. crop yields under climate change." *PNAS*
106(37):15594–15598. doi:10.1073/pnas.0906865106 [V]

- Damage thresholds: **corn 29 °C, soybeans 30 °C, cotton 32 °C**.
- Method: the within-day temperature path is approximated as a **sinusoid
  between that day's Tmin and Tmax**, and the model measures *time spent*
  in each 1 °C bin, summed over the season.
- Magnitude anchor: substituting one day at 40 °C for one day at 29 °C
  predicts roughly a **7% corn yield decline**.
- Precipitation enters quadratically, giving a concave response with an
  optimum at **25.0 in (corn), 27.2 in (soybeans)**.

Canonical specification:

```
ln(yield_it) = β₁·DD_below + β₂·DD_above + γ₁·P + γ₂·P² + c_i + λ_st + ε_it
```

with `c_i` a county fixed effect (absorbing soil, drainage, baseline
management) and `λ_st` a state-specific time trend (absorbing technology).
Identification comes from year-to-year weather deviations *within* the same
county — much closer to a natural experiment than cross-sectional
comparison.

**Related findings:**

| Finding | Value | Source | Grade |
|---|---|---|---|
| Extreme degree days (>30 °C) dominate seasonal rainfall in explanatory power for maize; mechanism is largely VPD-driven water stress | qualitative | Lobell et al. 2013, *Nat. Clim. Change* 3:497, doi:10.1038/nclimate1832 | [P] |
| Climate variation explains ~a third of global yield variability | 32–39% (maize 39%, wheat 35%, rice 32%) | Ray et al. 2015, *Nat. Commun.* 6:5989, doi:10.1038/ncomms6989 | [V] |
| SPEI explains US maize/soybean yield variance | 12.6% / 12.8% national; county R² to 0.57/0.67 | Zipper, Qiu & Kucharik 2016, *ERL* 11:094021, doi:10.1088/1748-9326/11/9/094021 | [V] |
| GDD has two incompatible computation conventions | — | McMaster & Wilhelm 1997, *Agric. For. Meteorol.* 87(4):291–300, doi:10.1016/S0168-1923(97)00027-0 | [V] |
| Saturation vapour pressure coefficients | e\*=0.61121·exp(17.502T/(T+240.97)) | Hatfield & Prueger 2015, *Weather Clim. Extremes* 10:4–10, doi:10.1016/j.wace.2015.08.001 | [V] |

The Ray et al. figure is the single most useful number for calibrating
expectations: **weather can explain roughly a third of yield variability,
not most of it.** Any claim that a weather feature will transform forecast
accuracy is arguing against this result.

**Implemented in** `agronomy/heat_exposure.py`. The sinusoid's closed forms
(arcsine CDF for time-below-threshold; single-sine integral for degree days
above threshold) are derived directly and **verified against numerical
integration in the tests**, so they hold regardless of citation.

---

## 3. Specialty crops: the honest gap

There is **no vegetable-crop equivalent of Schlenker & Roberts.** No
comparably large county-panel study with estimated thresholds and standard
errors exists for tomatoes, lettuce, peppers, or cucumbers. The specialty
literature is controlled-environment physiology, so thresholds are
*observed critical points*, not regression breakpoints.

| Crop | Threshold | Source | Grade |
|---|---|---|---|
| Tomato | ~32–35 °C day / ~20–25 °C night; pollen viability collapses first, foliage stays healthy | Hatfield & Prueger 2015 synthesis; Sato, Peet & Thomas 2000 *Plant Cell Environ.* 23:719 | [P], a range not a point |
| Tomato (protected culture) | mean daily 25–26 °C | *Agronomy* 2014, 4:167–177 | [P] — shows the threshold is cultivar/system dependent |
| Lettuce | bolting/quality loss ~30–33 °C | Dufault, Ward & Hassell 2009 *Sci. Hortic.* 120:452 | [P] |
| Pepper, cucumber | qualitative only | — | [U] — no usable coefficient found |

**Consequence for us:** the *method* transfers (nothing in the
Schlenker-Roberts machinery is corn-specific); the *thresholds* do not.
`CROP_THRESHOLDS_C` therefore carries an explicit `threshold_evidence` field
(`estimated` / `observed` / `observed_weak` / `default`) that travels with
every result, so a horticultural range can never be silently presented as
an econometric estimate.

---

## 4. Correlated shocks: why supplier risk does not diversify away

This is the section that changed how we think about our own optimizer.

**Miranda, M.J. & Glauber, J.W. (1997).** "Systemic Risk, Reinsurance, and
the Failure of Crop Insurance Markets." *AJAE* 79(1):206–215.
doi:10.2307/1243954 [V]

Crop insurers' portfolios are **20 to 50 times riskier** than if farm-level
yields were independent, because weather shocks hit whole regions at once.
Supporting: 43–56% of large Illinois/Kansas farm revenue losses were
correlated with county-level losses, and the dominant insured perils are
the spatially correlated ones — drought >40% of wheat indemnities,
precipitation >22% of corn — versus idiosyncratic hail at ~10%. [P]

For n suppliers with equal variance and equal pairwise correlation ρ:

```
Var(mean fill) = σ²·[1/n + (n−1)/n·ρ]     risk multiplier M = 1 + (n−1)ρ
```

As n → ∞ the variance floors at **σ²ρ**, the non-diversifiable component.
Inverting M at n=100 reads Miranda & Glauber's 20–50× back as **ρ ≈ 0.19 to
0.49** — a defensible calibration band for "regionally correlated," derived
rather than chosen.

**Why this resolves our own open question.** An earlier stress test found
the two-stage stochastic program tying the deterministic LP. The diagnosis
was that the synthetic data drew *independent* supplier shortfalls, which
average out. Correlated weather shocks are the opposite regime, and
`estimate_shock_correlation()` now measures which regime an operator is
actually in, from their own delivery history. The demonstration output:

| Regime | measured ρ | risk multiplier | 10 suppliers behave like |
|---|---|---|---|
| Independent shocks | −0.02 | 1.0× | 10.0 independent |
| Regional weather shock | 0.93 | 9.3× | **1.1 independent** |

That second row is the case for stochastic and CVaR optimization, stated as
a measurement rather than an assumption.

**Implemented in** `agronomy/systemic_risk.py`.

---

## 5. Temperature after harvest

Weather does not stop mattering at the farm gate — this channel acts within
days, not seasons.

```
Q10 = (R₂/R₁)^(10/(T₂−T₁))      shelf_life(T) = L_ref / Q10^((T−T_ref)/10)
```

| Finding | Value | Source | Grade |
|---|---|---|---|
| Q10 2.0–2.5 → 50–60% shelf-life loss per 10 °C | verbatim | UF/IFAS EDIS HS1270, doi:10.32473/edis-hs1270-2015 | [V] |
| Respiration rates at 0/10/20 °C for lettuce, tomato, strawberry | see module | USDA Agriculture Handbook 66 | [V] |
| Tomato 18–20 °C → 26 °C | −11% shelf life (~4 days), weight loss 2.5%→5.1% | Thole, Vain & Martin 2021, *Plants* 10(11):2359, doi:10.3390/plants10112359 | [V] |
| Lettuce retail abuse at 21–24 °C | vitamin C −81%, chlorophyll −67% | Managa et al. 2018, *Food Sci. Nutr.* 6(6):1527, doi:10.1002/fsn3.685 | [V] |
| Arrhenius framework, Ea by reaction class | k = k₀·exp(−Ea/RT) | Labuza 1984, *J. Chem. Educ.* 61(4):348, doi:10.1021/ed061p348 | [V] |

**Q10 is not constant with temperature.** Computed from Handbook 66,
lettuce is 2.65 over 0–10 °C but 1.82 over 10–20 °C. Selecting one value
for a span crossing 10 °C is not merely imprecise — it produced a
*non-monotonic* shelf life (longer at 20 °C than 15 °C) in our first
implementation. `rate_multiplier_piecewise` composes across ranges, and a
regression test pins the monotonicity.

**Caveat carried in the module:** most published activation energies for
food quality loss come from thermal-processing studies at 60–100 °C, not
0–25 °C cold chain. Q10 fitted to refrigerated respiration data is the
defensible choice in our range.

---

## 6. Drought indices

SPI: fit a gamma to accumulated precipitation, mix in the zero-precip atom,
transform through the inverse standard normal.

- McKee, Doesken & Kleist 1993, *8th Conf. Applied Climatology*, AMS [V]
- Guttman 1999, *JAWRA* 35(2):311, doi:10.1111/j.1752-1688.1999.tb03592.x [V]
- WMO-No. 1090, SPI User Guide [V]
- SPEI (P − PET, log-logistic fit): Vicente-Serrano, Beguería &
  López-Moreno 2010, *J. Climate* 23(7):1696, doi:10.1175/2009JCLI2909.1 [V]

**USDM percentile bands** (Svoboda et al. 2002, *BAMS* 83(8):1181,
doi:10.1175/1520-0477(2002)083<1181:TDM>2.3.CO;2) [V]:

| Category | Percentile | SPI |
|---|---|---|
| D0 abnormally dry | 21–30 | ≤ −0.5 |
| D1 moderate | 11–20 | ≤ −0.8 |
| D2 severe | 6–10 | ≤ −1.3 |
| D3 extreme | 3–5 | ≤ −1.6 |
| D4 exceptional | 0–2 | ≤ −2.0 |

The USDM is explicitly a **convergence-of-evidence blend** — objective
indicators plus expert adjustment from 400+ local reports — not a pure
percentile computation. Our `usdm_category_from_percentile` reproduces only
the percentile scaffolding and says so.

One implementation detail worth recording: the Abramowitz & Stegun 26.2.23
constant c₁ is **0.802853**; a widely copied secondary source transposes it
to 0.802583. Our test checks the approximation against scipy's exact
inverse normal, which would have caught the typo.

---

## 7. What the literature does NOT support

Recording this so nobody re-derives false confidence later.

1. **No published per-degree-day yield-loss coefficient was verifiable.**
   Figures like "−0.5% per killing degree day" circulate in search
   summaries but could not be traced to a table in Schlenker & Roberts or a
   companion paper. **Not used anywhere in the code.**

2. **No clean skill-by-lead-time curve for weather-informed yield
   forecasts.** The literature is scattered across regional case studies
   with inconsistent metrics. Vijverberg, Hamed & Coumou 2023 (*AIES* 2(3),
   doi:10.1175/AIES-D-21-0009.1) likely answers this for US soy but was
   paywalled. Any precise "beats climatology at week N" claim is unverified.

3. **Essentially no peer-reviewed literature on weather effects on
   distributor or wholesaler fill rates.** This is the exact quantity our
   engine models. The academic gap is real — which is an argument for
   measuring it on operator data, and against citing a literature that does
   not exist.

4. **The US Midwest summer ENSO signal appears weak**, contrary to how ENSO
   is often invoked. Iizumi et al. 2014 (*Nat. Commun.* 5:3712,
   doi:10.1038/ncomms4712) [V] finds El Niño gives soybean +2.1% to +5.4%
   globally, while La Niña is uniformly non-positive across all four major
   crops (−4.5% to 0.0%); the strong teleconnections are in Argentina,
   Australia, and Southeast Asia rather than the US Corn Belt. No specific
   US Midwest correlation coefficient was verifiable. **Our ENSO feature is
   loaded but should not be assumed useful for Indiana** — the admission
   gate will decide.

5. **No verified exact ACC-by-lead-day table** from ECMWF/GFS operational
   verification; the pages are dynamic charts. Our skill horizons rest on
   the published horizon figures instead, which were verifiable.

---

## 8. Forecast value, for context

| Finding | Value | Source | Grade |
|---|---|---|---|
| Improved ENSO forecast information to US agriculture | ~$145M/yr perfect, ~$96M/yr realistic (1990s $) | Adams et al. 1995, *Contemp. Econ. Policy* 13(3):10–19, doi:10.1111/j.1465-7287.1995.tb00720.x | [V] |
| Perfect ENSO prediction value | ~$323M/yr | Solow et al. 1998, *Climatic Change* 39:47–60, doi:10.1023/A:1005342500057 | [P] |
| JRC MARS operational yield forecast accuracy | median MAPE 6.3% (potato) to 10.2% (durum wheat) | van der Velde & Nisini 2019, *Agric. Syst.* 168:203–212, doi:10.1016/j.agsy.2018.06.009 | [V] |
| Best ML yield models vs baselines | CNN+GP RMSE 5.55 vs 7.73 best baseline (−30%) | You et al. 2017, AAAI-17:4559–4565 | [V] |

The MARS numbers are a useful sanity bound: a mature, well-funded
operational system achieves 6–10% MAPE on *national* crop yields. Anyone
promising materially better at operator scale should be asked how.

---

## Implementation map

| Module | Implements | Anchored on |
|---|---|---|
| `agronomy/heat_exposure.py` | sinusoidal within-day exposure, time-in-bins, GDD (3 conventions), extreme degree days, VPD | Schlenker & Roberts 2009; McMaster & Wilhelm 1997; Hatfield & Prueger 2015 |
| `agronomy/forecast_skill.py` | ρ(lead) decay, effect attenuation, unresolved-variance decomposition | Zhang et al. 2019; Buizza & Leutbecher 2015; ECMWF/Skok et al. 2016 |
| `agronomy/systemic_risk.py` | equicorrelated portfolio variance, implied ρ, effective independent count, estimator | Miranda & Glauber 1997 |
| `agronomy/drought_index.py` | SPI (Thom gamma + normal transform), USDM bands | McKee et al. 1993; Guttman 1999; Svoboda et al. 2002 |
| `agronomy/shelf_life_kinetics.py` | Q10 (piecewise), Arrhenius, cold-chain penalty | USDA Handbook 66; UF/IFAS HS1270; Labuza 1984 |

Integration: `risk/yield_covariates.weather_shift_for_window` now
attenuates the admitted effect by ρ(lead) and retires it entirely beyond
the usable forecast horizon, falling back to climatology.
