# Pilot data handling checklist — the first real customer

One page, ticked by the ZAAD owner before, during and after a pilot that carries a distributor's real operational
history. Companion to `SECURITY_REVIEW_2026_09.md`, `PILOT_SECURITY_CLOSURE_2026_09.md` and
`TENANT_OFFBOARDING_RUNBOOK.md`.

## Before any data is ingested

- [ ] A signed or written customer engagement covers the pilot, names the dataset and the people allowed to use it.
- [ ] The dataset is the one authorised: exports the customer already has (orders, purchase orders, receipts, stock,
      suppliers, prices); no personal data beyond business contact names in supplier or customer fields.
- [ ] The workspace exists (`POST /admin/workspaces` or the seed) with the customer's exact name and sector; its
      operator id is recorded.
- [ ] The credential is delivered through the agreed channel (in person, or the approval email to the named contact).
      It is a workspace token or a **≥ 12-character** access code; it is never typed into Git, chat, a ticket, a doc,
      a screenshot or a command line. The historical short code is retired (see the closure record, SEC-001).
- [ ] Named people get **actor tokens with roles** (VIEWER, BUYER, APPROVER, ADMIN); the workspace token stays with
      the owner.
- [ ] Retention expectations are written down: how long ZAAD keeps the vault after the pilot, and who asks for
      deletion.
- [ ] The owner and a security contact on the customer's side are identified, with a way to reach each other outside
      the product.
- [ ] The offboarding path has been exercised on a throwaway workspace in production (dry run and execution) since
      the last deploy.
- [ ] The production security QA (`prod_sec_qa.py` against throwaway tenants; headers; anonymous and cross-tenant
      refusals) is green on the current runtime.

## During the pilot

- [ ] Shadow mode: ZAAD recommends and records approvals; **it never sends an order to a supplier**, and there is no
      ERP write path.
- [ ] Every approval is a human action recorded in the workspace audit log; no autonomous purchase-order execution.
- [ ] Only the authorised dataset is uploaded; no additional sources (emails, other customers' files) without a new
      authorisation.
- [ ] Access changes (a person leaves, a role changes) are actioned the same day: revoke the actor, or rotate the
      workspace token.
- [ ] Incidents (a lost device, a shared credential, an unexpected login) trigger rotation first, questions second.
- [ ] Nobody runs demo or QA scripts against the customer workspace.

## After the pilot

- [ ] Retain by agreement (written, with a date), **or**
- [ ] Run the tenant offboarding runbook: dry run, execute, verify, receipt, and tell the customer what expires
      elsewhere (platform snapshots, provider logs).
- [ ] Remove the workspace from `HARVESTMIND_SEED_WORKSPACES` if it was seeded, so it is not re-created at the next
      start.
- [ ] Revoke any actor tokens that survive (offboarding removes them all; a retained workspace keeps them until
      revoked).

## Token lifecycle (current behaviour, for the record)

Workspace tokens, access codes and actor tokens **do not expire**. They are revoked by: rotating the workspace token
(`POST /admin/operators/{id}/token`), replacing the access code in the seed secret (`scripts/rotate_access_code.py`),
revoking an actor (`DELETE /workspace/actors/{actor_id}` by an ADMIN), or offboarding the workspace. For a controlled
pilot with named people, that revocation and rotation model is sufficient provided the checklist above is followed.
Automatic expiry is a separate, small change (an `expires_at` on the record, checked on authentication) proposed for
its own PR; it is not bundled here.
