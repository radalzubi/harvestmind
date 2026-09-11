# Prospective shadow pilot and security boundary

Use a real operator's dated SKUs, locations, customers, inventory lots, demand/order
lines, supplier/source quotes, capacities, POs/revisions, receipts/shipments,
transfers, approved substitutions, payment terms, calendars, service policies and
costs. Templates and schema are under `templates/`. JSON-valued CSV cells preserve
arrays, nulls and explicit booleans; missing critical financial values are refused.
Resolve revisions as-of; never select the latest future revision.

The dedicated SQLite shadow ledger records the exact request, information hash,
engine version, recommendation, incumbent actions, forecast/ETA/risk information,
expected economics, service and operator review/outcomes. Events are append-only
and hash linked. Human review uses a tenant predicate, expected information hash,
optimistic version and expiry deadline. Only pending, unexpired decisions can be
approved/rejected. No API transmits procurement or writes a training database.

Persistent routes require authentication even in development. Deploy only with
the existing enforced auth posture, HTTPS, an encrypted protected storage volume,
backup/restore procedure and a dedicated `ZAAD_SHADOW_LEDGER`. API schema/body,
rate and concurrent-compute limits apply. Request metadata/error bodies avoid
echoing sensitive input. Paid external feeds remain disabled without licensing.

Before enrolling an operator:

1. Reconcile opening stock, pipeline and AP/AR against the operator's accounts.
2. Define legal action permissions, shortage/SLA costs and all payment dates.
3. Define the planning and financial horizons, including later unpaid invoices.
4. Run actual order-line, substitution and receiving-calendar edge cases.
5. Agree downside tolerances and independently review failed stress conditions.
6. Save decisions prospectively; collect overrides and actual outcomes without
   retraining on customer data or promising gainshare before attributable savings.

Known limitations: no distributed worker quota, no automated live feed scheduler,
no calibrated real shipment model, and no production ERP write-back. The local
browser smoke passed after the Mac was unlocked and the exact localhost UI origin
was configured. Changing the draft invalidates displayed recommendations and
approval state. Approval is not execution.
