# Commercial Pilot Readiness — Implementation

## Scope

This change set closes the highest-risk gaps between a strong diagnostic
prototype and a safe paid pilot. It does not claim production SaaS maturity or
real-world model validation.

## Workstreams

### 1. One canonical decision path

- Keep `/planning/run` for deterministic and gamma-robust legacy workflows.
- Reject stochastic selections on that legacy route with a precise pointer to
  `/planning/two-sided`.
- Keep the staging-first two-sided path as the only stochastic commitment path.
- Add regression tests for the fail-closed behavior.

### 2. Pilot access and isolation

- Wire browser requests, including multipart uploads, to the existing bearer
  token authentication.
- Store the pasted pilot token in browser session storage only; never expose it
  in `NEXT_PUBLIC_*`, source, logs, or persistent local storage.
- Add a visible connection state and setup surface.
- Document auth, CORS, rate-limit, operator-vault, and secret requirements.

### 3. No static operational claims

- Replace hard-coded loss and performance pages with live API results or a
  clear unavailable state.
- Remove university endorsement wording from generated customer reports. Team
  biographies may accurately describe education, but the product must not say
  it is powered by or produced by the university without written authorization.

### 4. Reproducible deployment

- Pin the patched framework dependency and refresh the lockfile.
- Add container builds and a pilot deployment runbook.
- Keep operator databases on an explicit persistent volume and require TLS at
  the ingress.

### 5. Indiana synthetic validation

- Generate repeated, seeded food-hub histories using an Indiana produce basket,
  seasonal local availability, correlated regional disruptions, institutional
  demand, and deliberately imperfect records.
- Run the live four-policy rolling-origin benchmark over multiple seeds and a
  grid of spot premiums/capacities.
- Report all runs, including losses and failed model gates. Separate sourced
  inputs from modeled assumptions.

## Acceptance criteria

- Existing Python tests remain green; new route, auth-client, and generator
  behavior is covered.
- TypeScript checks and the production Next build pass.
- `npm audit` has no known high-severity finding in the production dependency
  tree, or the remaining blocker is documented with exact package/version.
- A clean container build or a documented environment limitation is recorded.
- Indiana results are reproducible from one command and explicitly labeled
  synthetic.
- README, security guidance, environment examples, and framework versions match
  the code.

