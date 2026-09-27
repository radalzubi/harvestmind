# ZAAD pilot security closure — credential rotation, tenant-switch hygiene, tenant offboarding (September 2026)

**Status: IN PROGRESS (2026-09-26).** Branch `security/pilot-closure` from `main` `fa07f12` (= the security hardening
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
