# Censored ETA model

For observed duration v, event indicator delta, survival is
`S(v)=product_(u<=v)(1-events(u)/at_risk(u))`. Open orders contribute to the
risk set until their censor time; they are not treated as completed shipments.
Condition on still open at age a: `P(T-a<=k | T>a)=1-S(a+k)/S(a)`.

The implementation returns P50/P80/P90 remaining days and unresolved tail mass.
If empirical support cannot identify a quantile it returns null, not a finite
made-up ETA. Conditional mass beyond available support stays outside the planning
horizon. Fewer than six records are explicitly insufficient; where no history
exists the operational quote ETA remains labelled quote-based, not calibrated.

Stratification uses source/stage/carrier when at least12 rows and6 arrivals are
available, otherwise source scope is explicit. AFT/Cox/survival boosting would
support richer covariates but require more observed events and model checking.
Hierarchical time-to-event modeling would help thin lanes; no fitted hierarchical
ETA model or nominal field calibration is claimed here.

Reference: [NIST Kaplan–Meier product-limit estimation](https://itl.nist.gov/div898/handbook/apr/section2/apr215.htm),
[NIST right censoring](https://www.itl.nist.gov/div898/handbook/apr/section1/apr131.htm).

The regression tests verify censoring and aging. Those tests do **not** establish
real shipment P90 calibration or incremental savings from ETA estimation.
