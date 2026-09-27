# ZAAD pilot security closure — credential rotation, tenant-switch hygiene, tenant offboarding (September 2026)

**Status: CODE COMPLETE ON THE BRANCH — RELEASE BLOCKED (2026-09-27): CI cannot start (GitHub Actions billing) and the credential rotation is the owner's action. Pilot-data readiness: BLOCKED.** Branch `security/pilot-closure` from `main` `fa07f12` (= the security hardening
runtime `c7ec175` plus its docs commits). Tracker written before code. Scope is deliberately small: retire the exposed
credential, close SEC-038 completely, add a tested tenant-offboarding procedure, state retention limits, and give a
binary pilot-data readiness verdict. No optimizer, analytics, business-logic or product-semantics change.

## 0. Review findings (before any change)

| item | exact status found |
|---|---|
| SEC-001 | **The committed code still authenticates on production** (probe of `GET /me` with the value read from history into a private scratch file: HTTP 200, the customer workspace). The value was also still present at HEAD in `tests/security/test_auth_hardening.py` as a "short code" sample (scrubbed in this pass). The second six-digit value in the same historical commit (a produce demo workspace) answers 401. |
| how codes work | one `token_hash` and one `access_code_hash` per workspace, unsalted SHA-256, both grant ADMIN; actor tokens appended, revoked by `revoked_at`; nothing expires. `HARVESTMIND_SEED_WORKSPACES` (`name|sector|code|logo;…`) runs at **every** start and re-applies the code when it is ≥ 12 characters; a short code in the secret leaves the stored hash alone with a warning. **The seed secret is therefore the controlling input for rotation**: a rotation made any other way is overwritten at the next boot if the secret later carries a long code, and a workspace suspended or deleted while still named in the secret is re-created empty at boot. No admin route sets or clears an access code; `POST /admin/operators/{id}/token` rotates the token only. |
| SEC-038 | open, LOW: `clearWorkspaceStorage()` runs only on explicit sign-out; `access/page.tsx` stores a new token without clearing the previous tenant's state; the paste path and `GetStarted` store the credential **before** validating it; `zaad.prefs.user.*` / `zaad.prefs.device.*` (operator-keyed) and `zaad.data.hidden.<dataset>` (**not** operator-keyed) are never cleared; `workspace-data.tsx` in-flight `watch`/`run` callbacks have no per-workspace guard; no 401 handling turns an invalid credential into a cleared session. No cookies, IndexedDB, module-level data caches or cross-tab sync exist. |
| tenant deletion | `OperatorRegistry.delete_operator` only sets `status="deleted"` (which stops authentication) and is called by nothing; no store has a delete path (JobStore, shadow ledger, reports, sessions, pool, corpus). |
| token lifecycle | rotate token: admin route; rotate code: seed secret (or CLI on the volume); revoke actor: `DELETE /workspace/actors/{id}` (ADMIN capability) or nothing admin-side; no expiry anywhere. |

## 1. Plan

1. **Credential** — scrub HEAD; rotate the customer code by replacing the seed secret with a new ≥ 12-character random
   code through `fly secrets import` (stdin, no argv, no shell history); verify old → 401, new → 200; store the new
   value only in a 0600 file for the owner, never in git/docs/chat; regression tests with synthetic values only.
2. **SEC-038** — one canonical `clearTenantClientState()` (`web/src/lib/tenant-state.ts`) with an inventory-driven key
   list, dispatching a `harvestmind-tenant-reset` event for in-memory holders; `switchCredential()` validates the
   candidate before touching storage and clears the previous tenant only when the candidate is accepted; wired into the
   access page (link + paste), `GetStarted`, `session.signIn/signOut`, and a `/me` 401/403; `zaad.data.hidden` re-keyed
   by operator; `workspace-data` in-flight guards; node tests A–G; browser QA on localhost for back/forward, sign-out,
   rapid switch and two tabs.
3. **Offboarding** — `infrastructure/offboarding.py` (inventory + dry run + execute, structured result, fail closed,
   path containment, no symlinks, per-stage status, idempotent, receipt), `scripts/offboard_operator.py` (dry run by
   default, `--execute --confirm-operator-id`), `POST /admin/operators/{id}/offboard` (admin key, same module, also
   clears in-process caches) so production can be offboarded without `fly ssh`; tests: dry run, exact targeting,
   execution, tenant B unaffected, idempotency, path safety, partial failure, retained items reported.
4. **Docs** — `TENANT_OFFBOARDING_RUNBOOK.md`, pilot data handling checklist, security review (SEC-001, SEC-038,
   SEC-039 offboarding control), CURRENT_SYSTEM, ledger.
5. **Release** — full CI on the exact head, merge, deploy the merge SHA, verify Fly/Vercel, production QA on throwaway
   tenants (including one throwaway offboarding), tag after QA.

## 2. Progress log

- 2026-09-26 01:35Z branch created; reviews complete; committed value scrubbed from the test file.
- 2026-09-26 02:05Z credential: production probe confirmed the committed code still authenticates (HTTP 200, the customer
  workspace); the second historical six-digit value answers 401. The agent's session was **refused the Fly secret write**
  (permission layer), so the rotation is prepared, not performed: `scripts/rotate_access_code.py` (value on stdin, new code to
  a 0600 file, never printed). SEC-001 = CODE FIXED / CREDENTIAL ROTATION OWNER-BLOCKED.
- 2026-09-26 02:30Z SEC-038 implemented (`web/src/lib/tenant-state.ts`; call sites: access link, paste, get-started,
  `session.signIn`, `/me` 401/403; in-memory holders on `harvestmind-tenant-reset`; workspace-data generation guard;
  `zaad.data.hidden` keyed by workspace). Node tests 7 (A, E, E', ordering, F, G, inventory classification).
- 2026-09-26 02:45Z offboarding: `infrastructure/offboarding.py`, `scripts/offboard_operator.py`, `POST
  /admin/operators/{id}/offboard`; tests 8 (all green); runbook and pilot checklist written; SEC-039 recorded.

## 3. Browser QA (localhost, two seeded tenants with identical record ids; tokens never pasted into production)

| flow | observed |
|---|---|
| A signed in, opens an **invalid** B link | token stripped from the URL, `/me` 401 once, A still signed in, A's keys untouched, refusal message shown |
| A → B by access link | `localStorage` holds only `zaad.recents.op_B`; A's recents, prefs and hidden-column keys gone; B's name only |
| B → Back → Back → Forward | `/access` as B, then `/inventory` **rendered as B** (B's rows), then `/access` as B; never A's name or rows |
| A → sign out → Back | both storages empty; Back lands on the gate ("not open here"), no rows |
| rapid A → B → A (three links in a row) | ends on A with only A's key; no B state |
| two tabs: tab 1 A, tab 2 A; tab 1 → B | tab 2 stays A (credential is per tab); tab 1 shows B only; when tab 2 navigates it rewrites `zaad.recents.op_A` in the shared local store — keyed by operator, never read by B's tab; there is no cross-tab auth sync and none is added |
| console | a fresh tab on the branch build (sign-in → `/start`) logs nothing; a clean tab on the stashed `main` build logs nothing either; the hydration warning seen in the long-lived QA tab came from its Back/Forward history and appears on both builds |

## 4. Local gates on the branch

`tests/security` 216 collected, all green (offboarding 8, auth hardening +3, SEC-038 node tests 7); canonical frozen regression
PASS; integration modules (front door, canonical API, analytics security, security hardening) 32 passed; unit suite (in
progress at the time of writing, see the PR); web tests 206 / 209 (the 3 pre-existing failures from untracked files); `tsc`
and `eslint` clean on the changed files; ruff and mypy clean on the new backend files.

## 5. Release standing (2026-09-27 02:50Z)

- PR #97 opened from `security/pilot-closure` head `5d26571`.
- **CI run 36289542773 did not run**: every job was refused within seconds with the annotation "The job was not started
  because recent account payments have failed or your spending limit needs to be increased" (GitHub Actions billing; the same
  block occurred on 2026-09-15). No job executed, so nothing about the head is proven by CI yet. Owner action: restore Actions
  billing, then re-run the workflow on the exact head (`gh run rerun 36289542773` or a new push).
- The Vercel preview build for the head failed in `next/font`'s Google loader ("Cannot read properties of null (reading '1')" in
  `layout.tsx`), the transient loader error already seen on PR #95; it is not caused by this change and clears on rebuild.
- Merge, deploy, production QA, the runtime tag and the CURRENT_SYSTEM / ledger updates wait for a green CI run on the exact head
  (§51 of the hardening brief; §32 of this one). Nothing was merged or deployed.

## 6. Pilot-data readiness

**BLOCKED.** Two owner actions stand between the branch and READY FOR CONTROLLED PILOT:
1. Replace the seed secret so the historical code stops authenticating (`scripts/rotate_access_code.py`; then the old value must
   answer 401 and the new one 200). Code hardening alone does not retire a leaked credential.
2. Restore GitHub Actions billing so CI can prove the head, then merge and deploy PR #97 per the release process.
With both done and the production QA (§31) green on throwaway tenants, the READY conditions are met: no open CRITICAL/HIGH,
exposed credential revoked, SEC-038 closed with tests, tested offboarding, tenant isolation suite green, no new regression.

## 7. Release-closure attempt (2026-09-27 20:30Z)

Re-checked from the exact head `c62a05a` (no newer commits on PR #97):

| gate | result |
|---|---|
| historical code on production | **still authenticates** (`GET /me` HTTP 200, the customer workspace) |
| Fly seed-secret rotation | not possible from this session (the permission layer refuses secret-store writes; not retried) → **CREDENTIAL ROTATION OWNER ACTION REQUIRED** |
| GitHub Actions | run 36289649860 re-run at 20:14Z, attempt 2: every job refused in 2 s with "The job was not started because recent account payments have failed or your spending limit needs to be increased" → **CI BLOCKED — OWNER MUST FIX GITHUB BILLING/SPENDING LIMIT** |
| HEAD secret scan | the historical value appears in no tracked file (data files included); no replacement credential exists to leak; `docs/security` reproduces no code; fixtures use synthetic values only; gitleaks runs in CI (blocked) |
| SEC-038 | node tests 7 / 7 on the head; browser QA of §3 unchanged (no frontend change since) |
| offboarding + credential regression | 21 passed, 1 skipped; whole `tests/security` 215 passed, 1 skipped |
| frozen canonical regression | PASS on the head (see the log line below); `P1_INVARIANTS.json` untouched |

Nothing merged, nothing deployed, no tag. **PILOT DATA READINESS: BLOCKED.**

### Exact owner actions

1. **Rotate the seed secret** (retires the exposed code; nothing else does):
   ```bash
   python scripts/rotate_access_code.py --app zaad-api --name "<the workspace's registry name>" --sector commercial \
       --logo "<its logo path>" --out ~/.zaad-secrets/customer_access_code_$(date +%F).txt
   ```
   The workspace name, sector and logo are the ones `GET /me` reports for the workspace (the seed matches on the exact name).
   The app restarts and applies the new code at start. Then verify without printing either value:
   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $(cat OLD_CODE_FILE)" https://zaad-api.fly.dev/me   # expect 401
   curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $(cat ~/.zaad-secrets/customer_access_code_*.txt)" https://zaad-api.fly.dev/me   # expect 200
   ```
   Hand the new code to the customer through the agreed channel; keep the 0600 file or delete it once delivered.
2. **Restore GitHub Actions billing** (Settings → Billing & plans), then re-run CI on the exact head:
   ```bash
   gh run rerun 36289649860
   ```
   and continue with the release process in the closure brief (14/14 green → merge → deploy the merge SHA → production QA on throwaway tenants including one throwaway offboarding → tag → records).

Frozen regression log line on the head: `CANONICAL REGRESSION PASS`
