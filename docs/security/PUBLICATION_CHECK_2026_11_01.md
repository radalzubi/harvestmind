# Publication security verification — 2026-11-01

## SEC-001 closure

The historical pilot access code in Git history is treated as compromised. Its matching access-code hash was removed from the live pilot workspace registry on `zaad-api`. No replacement credential was issued; the inspected workspace had no alternative admin credential. A fresh secure invitation or access code is required before the customer's next login.

Verification on commit `d7d7a03e1b5419c43b2c82d3009511650f0b3d80`:
- [Publication security check, run 41330230853](https://github.com/radalzubi/harvestmind/actions/runs/41330230853): **success**.
- The exposed code is absent from the live registry and returns **HTTP 401** at both `https://api.zaadsupply.com/me` and `https://zaad-api.fly.dev/me`.
- Both origins' health endpoints returned **HTTP 200** after maintenance.
- Seven targeted maintenance tests passed. This was not a rerun of the full product validation suite.
- Full fetched branch/tag history was scanned with checksum-verified Gitleaks 8.30.1. All 11 reported matches were reviewed: they were Fly image/release references, not credentials. The short pilot code was handled separately because it is outside the scanner's detection.

## Scope and operational record

The maintenance changed the matching registry access-code hash only. Customer datasets, workspace records, planner/model code, deployed image and machine size were preserved. The production API remains Fly v38, `canonical-c7ec175`.

The first maintenance attempt created a registry file owned by root, causing authentication requests to return HTTP 500. The follow-up repaired registry and lock-file ownership, runs the atomic save as the application user, and verified normal unauthorized responses afterward. No customer data was deleted.

The expired GitHub Actions deployment token was replaced with a token scoped to `zaad-api`, stored in the existing `FLY_API_TOKEN` repository secret. Its 30-day validity ends on 2026-12-01. No token value is stored in this record.

The September security review's other residual limitations remain. This closure is evidence for the known publication blocker, not a guarantee that all possible vulnerabilities or sensitive information have been discovered.
