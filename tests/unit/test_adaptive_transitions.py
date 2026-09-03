"""Transition behaviour of the state layer on simulated episodes (estimator
only, no optimizer, so it runs in seconds): a progressive disruption is
detected on the affected suppliers and not on the others, a single bad
week is not a regime, recovery unwinds the posture, and a calm operation
is left alone."""
from __future__ import annotations

from dataclasses import replace

import numpy as np
from adaptive.engine import estimate
from adaptive.state_estimator import TrackerBank
from scripts.run_fmcg_counterfactuals import fold_from_history
from synthetic.fmcg.distributor_sim import ARCHETYPES, build_history


def _hist(profile, seed=7, share=0.5, base="C_constrained_supplier", **kw):
    spec = replace(ARCHETYPES[base], disruption_week=None, disruption_profile=profile,
                   disrupted_supplier_share=share, **kw)
    return build_history(base, seed=seed, spec=spec)


def _trace(h, origins, cover=2.0):
    dis = set(h.suppliers[h.suppliers["disrupted"]]["supplier_id"])
    bank = TrackerBank()
    out = []
    for o in origins:
        fi, _ = fold_from_history(h, o, 12, 52, cover, 0.95, 0.02 / 4.33)
        est = estimate(fi, tracker=bank)
        aff = [est.sku[j].p_disruptive() for j in fi.products if fi.supplier_of[j] in dis]
        un = [est.sku[j].p_disruptive() for j in fi.products if fi.supplier_of[j] not in dis]
        out.append({"t": o, "aff": float(np.mean(aff)) if aff else None, "unaff": float(np.mean(un)) if un else None,
                    "flags": sum(bank.get(j).posture_disrupted for j in fi.products),
                    "commit": est.posture.commit_window, "lam": est.posture.cvar_lambda,
                    "rec": float(np.mean([est.sku[j].probabilities["RECOVERY"] for j in fi.products
                                          if fi.supplier_of[j] in dis])) if aff else 0.0})
    return out


def test_progressive_disruption_is_detected_on_affected_suppliers_only():
    h = _hist([(62, 1.0, 1.0), (66, 0.8, 1.3), (70, 0.6, 2.0), (76, 0.6, 2.0), (80, 0.85, 1.3), (84, 1.0, 1.0)])
    tr = _trace(h, list(range(60, 86, 2)))          # every review, as in production
    assert tr[0]["aff"] < 0.25 and tr[0]["flags"] == 0
    assert max(x["aff"] for x in tr[4:]) > 0.5, tr
    assert all(x["unaff"] < 0.25 for x in tr), tr
    assert any(x["flags"] > 0 for x in tr[4:])
    assert min(x["commit"] for x in tr[4:]) < tr[0]["commit"]
    assert max(x["lam"] for x in tr[4:]) > tr[0]["lam"]


def test_false_alarm_does_not_flip_the_posture():
    h = _hist([(66, 1.0, 1.0), (67, 0.55, 2.0), (68, 1.0, 1.0)])
    tr = _trace(h, [66, 70, 72, 76, 80])
    assert all(x["flags"] == 0 for x in tr), tr
    assert max(x["aff"] for x in tr) < 0.5
    assert all(x["commit"] == tr[0]["commit"] for x in tr)


def test_recovery_unwinds_the_posture():
    h = _hist([(44, 1.0, 1.0), (46, 0.6, 2.0), (54, 0.6, 2.0), (58, 1.0, 1.0)])
    tr = _trace(h, [54, 56, 58, 60, 66, 72, 80, 88])
    assert max(x["aff"] for x in tr[:3]) > 0.5 and any(x["flags"] > 0 for x in tr[:4]), tr
    assert tr[-1]["aff"] < 0.25 and tr[-1]["flags"] == 0
    assert tr[-1]["commit"] > tr[0]["commit"]


def test_easy_slack_operation_is_left_alone():
    h = _hist([], share=0.0, base="A_stable")
    tr = _trace(h, [60, 70, 80, 90], cover=5.0)
    assert all(x["unaff"] < 0.2 and x["flags"] == 0 and x["commit"] == 4 for x in tr), tr
