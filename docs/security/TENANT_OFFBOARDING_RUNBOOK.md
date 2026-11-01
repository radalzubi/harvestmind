# Tenant offboarding runbook

How ZAAD stops processing one pilot customer's data and removes it from every store ZAAD controls, without touching
any other workspace. Tooling: `infrastructure/offboarding.py`, driven by `scripts/offboard_operator.py` (on the data
volume) or `POST /admin/operators/{operator_id}/offboard` (inside the running API, admin key). Tests:
`tests/security/test_offboarding.py`. Security record: `SECURITY_REVIEW_2026_09.md` SEC-039.

## When to use

- A pilot customer asks ZAAD to stop processing its data, or the pilot ends without a retention agreement.
- A throwaway or demo workspace is to be removed completely (not merely revoked).

Not for: revoking one person's access (revoke the actor), rotating a credential (rotate the token or the seed
secret), or pausing a workspace (suspend, which stops authentication and keeps the data).

## Preconditions

1. The request is recorded (who asked, when, through which channel) and the owner has approved the deletion.
2. The **immutable operator id** (`op_` + 8 hex) is known and confirmed with the customer's workspace name from
   `GET /admin/workspaces`. The tool never accepts a name as the destructive identifier.
3. **The workspace is not named in `HARVESTMIND_SEED_WORKSPACES`.** The startup seed re-creates an empty workspace of
   any name it finds missing, so remove the entry from the secret first (or at the same time). The tool warns when the
   entry is still there.
4. No planning job of the workspace is queued or running (`GET /api/zaad/network/jobs` as the workspace, or the job
   store). The tool refuses the job-store stage while one is active: cancel it first.
5. Decide retention: if the customer asked for a copy, export it before this procedure (the vault is one DuckDB file
   under `operators/<id>/harvestmind.db`; uploads are under `operators/<id>/uploads/`). Offboarding takes no backup.

## Authorised operator

The ZAAD owner, or a person the owner names for this run, holding the admin key (route) or a shell on the data volume
(script). The run is logged as a `security event=offboarding` line and written to the receipt with its actor.

## Dry run (always first)

Route (preferred in production, because it also clears the running process's caches):

```bash
curl -s -X POST "$API/admin/operators/$OP/offboard" -H "X-Admin-Key: $ADMIN_KEY" -H 'Content-Type: application/json' -d '{}' | jq .
```

Script (where the data root is mounted, with the deployment's `HARVESTMIND_DATA_ROOT`, `ZAAD_JOB_STORE`,
`ZAAD_SHADOW_LEDGER`):

```bash
python scripts/offboard_operator.py --operator-id "$OP"
```

The plan lists, per store: `would_remove` with a count and the paths or files concerned, `nothing`, `not_configured`
(the store is not set in this environment), or `failed` with the reason (fix it before executing). It also names what
is **retained** and what is **outside ZAAD's control**. It prints no customer record. Check that every path carries
the target operator id and no other.

## Execution

```bash
curl -s -X POST "$API/admin/operators/$OP/offboard" -H "X-Admin-Key: $ADMIN_KEY" -H 'Content-Type: application/json' \
  -d "{\"execute\": true, \"confirm_operator_id\": \"$OP\"}" | jq .
# or
python scripts/offboard_operator.py --operator-id "$OP" --execute --confirm-operator-id "$OP"
```

Order of stages: credentials (status `deleted`; token, access code and actor hashes removed — nothing authenticates
from here on), vault directory (DuckDB + WAL, uploads, session snapshots, exports, diagnostic reports, upload hashes,
consent record), extraction sessions (every session whose `owner.json` names the operator), training corpus lines of
those sessions, planning job rows, shadow-ledger decisions and events, optimizer run records, access-request contact
details (blanked; id, status and times stay), pool signal rows and contribution-log lines attributed to the operator,
process caches (route only), registry tombstone, receipt.

Result status: `complete` (every stage that had something removed it), `nothing-to-do` (a rerun; nothing left),
`partial` (at least one stage failed; the others ran). Exit codes for the script: 0, 0, 2; a refusal is 3.

## Verification

As the removed workspace: `GET /me` with its old token → 401. As every other workspace: unchanged (`/me` 200, the same
counts). On the volume: `operators/<id>/` absent; no `extraction_sessions/*/owner.json` names the id; the job store
and the ledger return 0 rows for it; `registry/offboarding/<id>.json` exists with status `complete`. The test module
performs exactly these checks on two synthetic tenants with identical record ids.

## Failure recovery

A `partial` result names the failed stage and the reason (`the vault is open in this process`, `job(s) queued or
running`, `disk full`, a symlink where a directory was expected). Fix the cause and **run the same command again**:
every stage is idempotent, finished stages report `nothing`, and the receipt accumulates the runs. Never delete by
hand with a shell glob; if a path must be removed manually, remove that one path only, then rerun the tool so the
receipt records the final state.

## What stays, and why

| retained | why | owner |
|---|---|---|
| registry tombstone (`operator_id`, `name`, `created_at`, `status=deleted`) | the id is never reissued; the deletion is accountable | ZAAD owner |
| offboarding receipt (`registry/offboarding/<id>.json`: stages, counts, times, actor) | the audit record of the deletion itself; no payload | ZAAD owner |
| `registry/cross_access_log.jsonl` lines naming the operator id | security log of cross-vault reads (ids and purpose only) | ZAAD owner |
| access-request row (id, status, times, operator id; contact details blanked) | onboarding accountability | ZAAD owner |
| API stdout security events (operator ids) | platform log window | Fly.io |

**Audit-log policy.** The workspace's own `zaad_audit_log` (approvals, revocations, question hashes) lives inside its
vault and is removed with it: it is the customer's operational history. What ZAAD keeps for its own accountability is
the metadata above, none of which carries a customer record, a price, a supplier or a person's contact details.

## Outside ZAAD's control (not deleted by this procedure)

- Fly.io volume snapshots: a daily snapshot of the data volume may hold the vault until Fly's snapshot window expires
  (Fly's default retention is days, set on the volume). ZAAD cannot delete a snapshot's contents selectively.
- Fly.io and Vercel request logs and metrics (their own retention).
- The LLM provider's request logs for AI extraction and Ask ZAAD, under the provider's retention terms.
- The mail provider's copy of an access-approval email, if one was sent.
- Any export the customer or the owner took out of ZAAD.

Say this to the customer in the same sentence as the deletion: "removed from ZAAD's stores; platform snapshots and
provider logs expire on their own schedules".

## Audit record

Keep, outside the deleted vault: the request, the approval, the dry-run output, the execution output (or receipt),
the verification result and the date. The receipt file is the machine-readable part of this record.

## Final sign-off

- [ ] request and approval recorded
- [ ] seed secret no longer names the workspace
- [ ] dry run reviewed: only the target id in every path
- [ ] execution `complete` (or `partial` resolved and rerun to `complete`)
- [ ] verification: old credential 401; other workspaces unchanged; volume clean; receipt present
- [ ] customer told what was removed and what expires elsewhere
- [ ] signed: name, date
