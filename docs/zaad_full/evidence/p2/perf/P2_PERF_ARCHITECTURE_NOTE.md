# P2 performance: architecture note (multi-SKU networks, async safety)

## What scales, after the FEFO symmetry elimination

Per candidate solve the model carries, for every world w, period t, SKU s and location l:

* one `inventory` column per live cohort of s at l (cohorts = opening lots + one per purchase /
  transfer / PO arrival period), one `allocate` column per cohort and compatible service, one
  `unmet` per service, one `depleted` indicator per service with demand and stock, `priority` and
  `direct_first` indicators only where a lower-priority or substitute service shares the stock;
* the FEFO indicators only between a cohort and an older cohort that can still matter inside the
  window (perishable stock, or any cohort within horizon + longest lane lead).

So the integer part of a long-shelf-life network is `services x periods x worlds` (`depleted`)
plus the executable-period packs / dispatch flags; it grows linearly in SKUs and services and in
worlds, not in cohorts. For a perishable network (shelf life inside the window) the FEFO rows
return for the cohorts that can expire, which is the physics the model must keep; there the same
exact levers apply in order: aggregate cohorts that share every expiry-dependent attribute inside
the window (an exact relabelling, not implemented because no fixture needs it), then tighten the
big-M of `depleted` / `fefo` from finite supplier, lane or opening capacities when the data declares
them (on the P2 requests they are 1e6, so no data-derived bound exists).

Multi-SKU requests multiply the columns per (t, w, l) by the SKU count and add the substitution
rows; nothing couples SKUs except shared supplier resources, supplier-order economics (one `order`
indicator per supplier and period), location capacity and cash. The interactive caps (20 SKUs, 40
sources, 20 services, horizon 12, 4 scenarios on the payload path; `NETWORK_LIMITS` 12 locations /
60 lanes) bound the model at roughly 20 x the two-SKU fixtures' size per world; with the FEFO rows
gone the binaries stay at `services x periods x worlds` (<= 20 x 12 x 8 = 1,920 `depleted` flags),
which is the regime every profiled candidate solved at the root node.

## What remains a safety mechanism

The runtime architecture is unchanged: the interactive API keeps its aggregate solve-time bound
(180 s) and the per-solve budgets (`solve_budget`, `network_solve_seconds`), a solve that reaches its
budget still returns a physically validated FEASIBLE_TIME_LIMIT plan rather than nothing, and
structurally heavy requests (long horizons, many worlds - the job path's 32 worlds and 26 periods)
still go to the asynchronous job store. None of that was needed on the authoritative set after the
change; it is the fail-closed path for requests outside it, not a way to meet the gate.

## What was deliberately not done

No commercial solver; no gap loosening (measured: decision time equals proof time); no parallel
candidate execution, HiGHS parameter tuning, thread changes, model caching or decomposition - each
would change the solver path on frozen cells for no gate benefit once the portfolio sits two
orders of magnitude inside the gate. They are the next levers if a future request class (multi-SKU
perishable networks at eight worlds) reintroduces branching.
