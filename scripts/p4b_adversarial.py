"""P4B V1 adversarial matrix (fail closed). Writes docs/zaad_full/evidence/p4b/P4B_ADVERSARIAL.{md,json}."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
from pydantic import ValidationError

from scripts.setup_db import setup_db
from zaad.commitments.fixtures import CANCEL, DEFER, KEEP, base, build_request, open_po, option, with_stock
from zaad.commitments.workspace import attach, commitment_declarations
from zaad.full.settlement import PhysicalViolation, settle
from zaad.full.worlds import draw
from zaad.meio.planner import solution_from_actions

OUT = Path("docs/zaad_full/evidence/p4b")


def refused(fn) -> tuple[bool, str]:
    try:
        fn()
    except (ValidationError, ValueError, PhysicalViolation) as exc:
        return True, ("REFUSED_AT_CONTRACT: " if isinstance(exc, (ValidationError, ValueError)) else "PHYSICAL_VIOLATION: ") + str(exc).split("[type=")[0].strip()[:150]
    return False, "ACCEPTED (must not be)"


def d():
    return with_stock(base(), 100.)


def case_unknown_action():
    x = d()
    return refused(lambda: build_request(x, open_po(x, [KEEP(x), option(x, "z", "reroute", 2)])))


def case_malformed_stage():
    x = d()
    return refused(lambda: build_request(x, open_po(x, [KEEP(x), CANCEL(x)], stage="teleported")))


def case_expired_option():
    """A cancel option whose deadline has passed: no capacity in the model, and a forced amendment is refused by the settlement."""
    x = d()
    req = build_request(x, open_po(x, [KEEP(x), CANCEL(x, deadline_days=-1)]))
    forced = solution_from_actions([{"action": "po_option", "po": "po1", "option": "cancel", "period": 0, "quantity": 100.}])
    return refused(lambda: settle(req, forced, draw(req, req.seed, 1, deterministic=True)[0]))


def case_prohibited_stage():
    x = d()
    req = build_request(x, open_po(x, [KEEP(x), CANCEL(x)], stage="shipped", departed=True))
    forced = solution_from_actions([{"action": "po_option", "po": "po1", "option": "cancel", "period": 0, "quantity": 100.}])
    return refused(lambda: settle(req, forced, draw(req, req.seed, 1, deterministic=True)[0]))


def case_negative_fee():
    x = d()
    return refused(lambda: option(x, "c", "cancel", 2, fee=-1.) and build_request(x, open_po(x, [KEEP(x), option(x, "c", "cancel", 2, fee=-1.)])))


def case_negative_credit():
    x = d()
    return refused(lambda: build_request(x, open_po(x, [KEEP(x), CANCEL(x, credit=-1.)])))


def case_excessive_refund():
    """credit above prepaid x refundable fraction"""
    x = d()
    return refused(lambda: build_request(x, open_po(x, [KEEP(x), CANCEL(x, credit=3.)], prepaid=2., refundable=1.)))


def case_credit_above_paid():
    """a credit with nothing refundable (fraction 0) or nothing paid"""
    x = d()
    a = refused(lambda: build_request(x, open_po(x, [KEEP(x), CANCEL(x, credit=1.)], prepaid=2., refundable=0.)))
    b = refused(lambda: build_request(x, open_po(x, [KEEP(x), CANCEL(x, credit=1.)], prepaid=0., refundable=1.)))
    return a[0] and b[0], f"{a[1][:70]} | {b[1][:70]}"


def case_cancel_above_remaining():
    x = d()
    req = build_request(x, open_po(x, [KEEP(x), CANCEL(x)]))
    forced = solution_from_actions([{"action": "po_option", "po": "po1", "option": "cancel", "period": 0, "quantity": 101.}])
    return refused(lambda: settle(req, forced, draw(req, req.seed, 1, deterministic=True)[0]))


def case_minimum_remaining_violation():
    x = d()
    return refused(lambda: build_request(x, open_po(x, [KEEP(x), CANCEL(x, max_quantity=70.)], split=True, minimum=40.)))


def case_split_when_prohibited():
    x = d()
    req = build_request(x, open_po(x, [KEEP(x), CANCEL(x), DEFER(x)], split=False))
    forced = solution_from_actions([{"action": "po_option", "po": "po1", "option": "cancel", "period": 0, "quantity": 50.},
                                    {"action": "po_option", "po": "po1", "option": "defer", "period": 0, "quantity": 50.}])
    return refused(lambda: settle(req, forced, draw(req, req.seed, 1, deterministic=True)[0]))


def _vault():
    conn = duckdb.connect(":memory:")
    setup_db(conn)
    return conn


def case_unknown_po():
    conn = _vault()
    conn.execute("insert into stg_po_options (operator_id, po_id, option_id, action, due_offset_periods, fee_per_unit, max_quantity, deadline, allowed_stages, contract_reference, provenance) "
                 "values ('op', 'ghost', 'c', 'cancel', 2, 0.25, 100, TIMESTAMP '2030-01-01', '[\"ordered\"]', 'ref', 'CONTRACT')")
    x = d()
    rows = [{**open_po(x, [KEEP(x)]), "id": "po1"}]
    from datetime import datetime, timezone
    return refused(lambda: attach(rows, commitment_declarations(conn, "op"), as_of=datetime(2026, 1, 1, tzinfo=timezone.utc), period_days=7))


def case_cross_tenant_declaration():
    conn = _vault()
    conn.execute("insert into stg_po_options (operator_id, po_id, option_id, action, due_offset_periods, fee_per_unit, max_quantity, deadline, allowed_stages, contract_reference, provenance) "
                 "values ('other_tenant', 'po1', 'c', 'cancel', 2, 0.25, 100, TIMESTAMP '2030-01-01', '[\"ordered\"]', 'ref', 'CONTRACT')")
    decl = commitment_declarations(conn, "op")
    return decl is None, "IGNORED: another tenant's declaration attaches nothing (KEEP-only)" if decl is None else "ACCEPTED (must not be)"


def case_missing_provenance():
    """a non-keep option resting on a CONFIGURED_ASSUMPTION"""
    x = d()
    return refused(lambda: build_request(x, open_po(x, [KEEP(x), CANCEL(x, provenance="CONFIGURED_ASSUMPTION")])))


def case_declared_keep_row():
    conn = _vault()
    conn.execute("insert into stg_po_options (operator_id, po_id, option_id, action, deadline, contract_reference, provenance) values ('op', 'po1', 'k', 'keep', TIMESTAMP '2030-01-01', 'ref', 'CONTRACT')")
    x = d()
    rows = [{**open_po(x, [KEEP(x)]), "id": "po1"}]
    from datetime import datetime, timezone
    return refused(lambda: attach(rows, commitment_declarations(conn, "op"), as_of=datetime(2026, 1, 1, tzinfo=timezone.utc), period_days=7))


def case_option_without_deadline():
    conn = _vault()
    conn.execute("insert into stg_po_options (operator_id, po_id, option_id, action, fee_per_unit, max_quantity, contract_reference, provenance) values ('op', 'po1', 'c', 'cancel', 0.25, 100, 'ref', 'CONTRACT')")
    x = d()
    rows = [{**open_po(x, [KEEP(x)]), "id": "po1"}]
    from datetime import datetime, timezone
    return refused(lambda: attach(rows, commitment_declarations(conn, "op"), as_of=datetime(2026, 1, 1, tzinfo=timezone.utc), period_days=7))


CASES = [("unknown action", case_unknown_action), ("malformed stage", case_malformed_stage), ("expired option", case_expired_option),
         ("prohibited stage", case_prohibited_stage), ("negative fee", case_negative_fee), ("negative credit", case_negative_credit),
         ("excessive refund", case_excessive_refund), ("credit above paid / refundable amount", case_credit_above_paid),
         ("cancel quantity above remaining", case_cancel_above_remaining), ("minimum remaining violation", case_minimum_remaining_violation),
         ("split when split prohibited", case_split_when_prohibited), ("unknown PO in declarations", case_unknown_po),
         ("cross-tenant declaration", case_cross_tenant_declaration), ("missing provenance (assumption)", case_missing_provenance),
         ("declared keep row", case_declared_keep_row), ("option without deadline", case_option_without_deadline)]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for name, fn in CASES:
        ok, how = fn()
        results.append({"case": name, "pass": ok, "outcome": how})
        print(f"{name:42s} {'PASS' if ok else 'FAIL'}  {how[:100]}")
    passed = sum(r["pass"] for r in results)
    (OUT / "P4B_ADVERSARIAL.json").write_text(json.dumps({"passed": passed, "total": len(results), "results": results}, indent=1))
    md = ["# P4B V1 adversarial matrix (fail closed)\n", f"{passed} / {len(results)} PASS\n", "| case | outcome | result |", "|---|---|---|"]
    md += [f"| {r['case']} | {r['outcome'][:110]} | {'PASS' if r['pass'] else 'FAIL'} |" for r in results]
    (OUT / "P4B_ADVERSARIAL.md").write_text("\n".join(md) + "\n")
    print(f"ADVERSARIAL {passed}/{len(results)}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
