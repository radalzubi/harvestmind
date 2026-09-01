# Pilot Deployment Runbook

This configuration is suitable for a controlled single-host pilot behind a
TLS reverse proxy. It is not a multi-region SaaS architecture.

## Required controls

1. Create a 32+ character admin key in the host secret manager. Do not place it
   in the repository or a browser-visible variable.
2. Set the exact HTTPS web origin in `CORS_ALLOWED_ORIGINS` and set the exact
   externally reachable API origin in `NEXT_PUBLIC_API_URL` **before building**
   the web image. Next.js inlines public variables at build time.
3. Put both services behind TLS. Keep ports 3000 and 8000 bound to loopback as
   configured; expose only the reverse proxy.
4. Back up the named `harvestmind-data` volume encrypted at rest. Test restore
   before accepting partner data.
5. Establish written retention, deletion, incident-response, and acceptable-use
   terms. Generated traceability output is decision support, not legal
   certification.
6. The production API image installs only the core dependency set. Legacy
   Streamlit, live-LLM, and PDF extras are excluded unless explicitly requested
   and separately audited.

## Start and verify

```bash
export HARVESTMIND_ADMIN_KEY='replace-with-secret-manager-injection'
export CORS_ALLOWED_ORIGINS='https://pilot.example.com'
export NEXT_PUBLIC_API_URL='https://api.pilot.example.com'
docker compose -f compose.pilot.yml build
docker compose -f compose.pilot.yml up -d
curl http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/intake/status  # must return 401
```

## Onboard one operator

Create the operator from a trusted shell, issue its token once through the
admin endpoint, transfer it out-of-band, then paste it into `/access`. The raw
token is never stored server-side and rotation invalidates the old token.

Do not share the admin key with an operator. Do not place an operator token in
`NEXT_PUBLIC_*`, container environment, source code, analytics, or logs.

## Known scale boundary

DuckDB vaults and the JSON registry support a small, low-concurrency pilot.
Before broad launch, move identity and registry state to a transactional store,
add distributed request limits and observability, define background-job
isolation, and load-test concurrent uploads and solver runs.
