# Zaad security and data-governance boundary

Code inspected: `zaad/contracts.py`, `zaad/signals.py`, `zaad/engine.py`, `api/routers/zaad.py`, `api/dependencies.py`, `api/main.py`. This is the implementation posture of the experimental recommendation path, not a penetration-test certificate, SOC 2 claim, legal opinion or production authorization.

## Implemented controls

| Boundary | Actual control | Residual limitation |
|---|---|---|
| Canonical input | Frozen Pydantic records reject extra fields, non-finite quantities, invalid quantity chains, unknown references, noncontiguous routes, undated/currently unknown operator data, duplicate snapshot PO revisions and malformed dimensions. | Most business records permit normal Pydantic coercion; frozen models alone do not prove the supplied facts are true. A Python developer can bypass validation with `model_copy`; public input must pass canonical validation. |
| External signal | Strict frozen typed record; HTTPS source attribution; three-clock/effective-time gating, finite magnitudes/confidence, rights states, reconstructed-history exclusion. | Provider/rights/confidence assertions must come from trusted onboarding. User-entered `contract_verified` is not proof of a contract or a calibrated probability. |
| Fetch destination | NWS adapter uses one fixed public HTTPS URL; no redirects; it never follows payload URLs or sends operator PO/inventory data. Connect/read limits, total elapsed-time check, bounded bytes/records and refusal of incomplete pagination. | No scheduled poller or durable source-version archive is implemented. Transport deadlines bound individual reads; infrastructure should also cap outbound jobs. |
| Failure handling | Explicit `ProviderError` for unavailable/malformed/oversized/rate-limited provider results; normalization returns only after the batch validates. Immutable replay returns a new store only after complete validation. | The caller must persist and retain the old store. Zero eligible observations must not silently mean zero underlying risk. |
| Untrusted content | Normalizer selects bounded fields; article descriptions and arbitrary instructions do not become model inputs/tool calls. No LLM is used in this decision path. | Provider/source/entity strings remain untrusted display data. Never add raw HTML rendering, automatic URL fetch, source-defined code or prompt-executable content. |
| Tenant binding | `/api/zaad/plan` checks authenticated operator against payload `operator_id`; inherited authentication rejects missing/invalid credentials in configured deployed environments. | Development mode intentionally permits local unauthenticated use. This is not a full role/approval workflow or proof of safe public deployment. |
| Request abuse | Recommendation POST requires canonical JSON, bounds streamed body to 2 MiB, limits request rates and concurrent planning slots per process. Contract caps item, route, history, horizon and scenario dimensions. | Per-process limits are not a cluster-wide quota; large valid jobs can still consume CPU. Add ingress identity-aware quotas, global concurrency, time budgets and cancellation before public multi-worker service. |
| Actions | Engine only returns recommendations. Reports require approval and mark `executable_purchase_order=False`. No PO execution, carrier booking or vendor payment is added. | An external integration must not reinterpret a report as authority to transact. Enforce a separate authenticated approval/quote/compliance step. |
| Data isolation | New planner is request-scoped and performs no operator-vault/database writes or external model training. | Other repository endpoints retain their own data paths. This audit does not certify those entire systems or override their retention policies. |
| Audit identity | Input fingerprint is a SHA-256 digest of the canonical request serialization; reports expose seed and method assumptions. | An unkeyed digest detects differing input, not authenticity. It is not an append-only ledger, digital signature, chain of custody or tamper-proof audit store. |

## Deployment constraints

Use the existing deployed-environment authentication settings (`HARVESTMIND_ENV=pilot`, `staging` or `prod`, with credentials configured). Legacy environment names remain for compatibility; they are not the company brand. Do not rename them casually. Set an explicit CORS origin allowlist, TLS termination, loopback/private upstream binding and configured bind-host declaration. The inherited startup guard cannot discover a bind host that the launcher fails to declare. CORS is not authentication.

No production launch is established by a local green build. Before internet exposure: test real authentication/tenant isolation, place global request and job limits at ingress, verify secrets/log redaction, set an operational runbook, measure worst-case valid-request runtime, confirm cancellation behavior, and review the actual hosting configuration. No API secret belongs in frontend bundles, request fixtures, reports, logs or Git.

## Data rights, privacy and training

- The registry in `config/external_data_sources.yaml` documents access and rights evidence; it does not automatically clear a legal entitlement. Keep unverified/paid providers disabled. See [source audit](DATA_SOURCE_AUDIT.md).
- Commercial use, internal caching, customer display, raw/derived redistribution, ML training/evaluation and retention after contract termination are separate permissions. A source being public or a browser page being free does not answer them.
- Do not upload operator records to external providers, hosted LLMs or training databases merely to enrich a route. Current NWS fetch sends only normal request headers to a fixed public service.
- Separate immutable permitted source snapshots from operator transaction records, analytical features and model-training datasets. Each retained artifact needs owner, purpose, license version, time semantics, retention deadline and deletion path.
- Sanctions lists and vessel/company ownership can contain personal data. Restrict access and retention, respect correction obligations and jurisdictional privacy requirements, and do not put them into unrestricted model training. Source-list membership is not complete transaction-law analysis.
- No external provider purchases, scraping around access restrictions, raw paid-data redistribution or third-party model training is authorized by this build.

## Civil scope and human control

The system is for lawful civilian commercial supply chains. It does not recommend prohibited routes, sanctions evasion, military asset tracking, conflict targeting or navigation/safety-of-life actions. A blocked or unreviewed route is infeasible regardless of modeled savings. A fresh alternative quote, current approval, capacity and legal review must precede procurement.

Official weather warnings are not port-entry permission. News mentions are not closure orders. AIS positions are not safety-certified vessel locations. A forecast that suggests lower inventory does not waive customer service obligations. The engine's Monte Carlo confirmation gate is not a no-harm guarantee and must remain described as modeled evidence.

## Required incident and audit behavior

On provider outage/schema change, preserve the previous permitted snapshot, label it stale/unavailable and prevent silent risk-state recovery. On a malformed batch, reject the entire new batch. On credential compromise, revoke the credential and suspend the affected connector; do not fall back to unauthenticated scraping. On a discovered historical-vintage error, retain the old report as superseded and rerun affected experiments with explicit exclusions rather than overwriting the record.

Production incident alerting, multi-tenant audit persistence, signed report custody, configurable rights enforcement across all providers and contractual deletion automation are **not implemented here**. They are launch prerequisites, not capabilities to imply from this document.
