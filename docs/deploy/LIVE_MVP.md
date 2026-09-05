# Going live: the hosted MVP

Two deployables: the API container (FastAPI, DuckDB vaults on a persistent disk) and the web app (Next.js). A visitor picks a sector on the landing page, requests access, is approved by hand, receives a one-time link, uploads pseudonymised exports into an isolated vault, runs the diagnostic, downloads the PDF.

## 1. API on Fly.io (or any host with a persistent volume)

```bash
fly launch --no-deploy --copy-config --name zaad-api
fly volumes create harvestmind_data --size 10 --region fra
fly secrets set \
  HARVESTMIND_ADMIN_KEY="$(openssl rand -hex 32)" \
  CORS_ALLOWED_ORIGINS="https://zaadsupply.com" \
  HARVESTMIND_APP_URL="https://zaadsupply.com" \
  HARVESTMIND_ADMIN_EMAIL="you@zaadsupply.com" \
  RESEND_API_KEY="re_..." \
  HARVESTMIND_MAIL_FROM="Zaad Supply <access@zaadsupply.com>"
fly deploy
```

`HARVESTMIND_ENV=pilot` makes auth fail closed; the container refuses to start permissive on a public interface. Without `RESEND_API_KEY` approvals still work: the admin response carries the access link to send by hand.

## 2. Web app on Vercel

Project root `web/`. Environment: `NEXT_PUBLIC_API_URL=https://zaad-api.fly.dev` (never put a token in a `NEXT_PUBLIC_*` variable). Point `zaadsupply.com` at the Vercel project.

## 2b. Invited workspaces with a short key

Set one secret and the API creates them at startup (idempotent):

```bash
fly secrets set HARVESTMIND_SEED_WORKSPACES="NTDCO|commercial|839285|/logos/ntdco.jpg"
```

Entries are `name|sector|key|logo`, separated by `;`. The key is stored hashed and works like a token: the customer types it on the landing page and lands on a welcome screen with their name and logo, then their workspace. Put the logo file in `web/public/logos/`. Short keys are for a handful of invited pilots; rotate them with `scripts/seed_workspace.py` and clear them after the pilot.

## 2c. DNS at Namecheap for zaadsupply.com

Advanced DNS, four records; leave everything else default and delete the parking records Namecheap adds.

| type | host | value | for |
|---|---|---|---|
| A | @ | 76.76.21.21 | site root on Vercel |
| CNAME | www | cname.vercel-dns.com | site www on Vercel |
| CNAME | api | zaad-api.fly.dev | API on Fly |
| CNAME | _acme-challenge.api | (value printed by `fly certs add api.zaadsupply.com`) | API certificate |

Then in Vercel add `zaadsupply.com` and `www.zaadsupply.com` to the project (it confirms the two records), and run `fly certs check api.zaadsupply.com` until it reports issued. Propagation is minutes at Namecheap, occasionally an hour.

## 3. Operating it

- **Approve a request**: `GET /admin/access-requests` then `POST /admin/access-requests/{id}/approve` with header `X-Admin-Key`. The requester gets the link by email, or you send it.
- **Demo workspace** (optional): `POST /admin/demo-operator?sector=commercial` returns a token; set `HARVESTMIND_DEMO_TOKEN` and `HARVESTMIND_DEMO_SECTOR` as secrets and redeploy. The landing page then offers "try the demo". The demo vault is shared and synthetic; re-run the endpoint to reset it.
- **Backups**: the volume holds every vault and the registry (`data/registry/operators.json` with token hashes and pseudonymisation secrets). Snapshot it daily (`fly volumes snapshots`). Losing the registry loses the ability to join a customer's hashed ids; treat it like a key file.
- **Refresh public feeds** monthly: `python scripts/fetch_real_data.py`, `python scripts/fetch_indicators.py`, `python scripts/fetch_public_priors.py`, then redeploy (they are baked into the image).
- **Long solves**: diagnostics run as background threads inside the single API process (`POST /jobs/diagnostic`, poll `GET /jobs/{id}`). A restart mid-run loses the job; the UI offers to rerun. Move to a worker process when there is more than a handful of concurrent customers.

## 4. What is deliberately not there yet

- Self-service sign-up: access is approved by hand on purpose, so every workspace has a human behind it.
- Multi-process job queue and object storage for vaults.
- Payment. The first customers pay for the diagnostic as a service; billing belongs after the second paying customer.
