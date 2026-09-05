"""Front door: access requests, approval, and "who am I".

  POST /access/request           public, rate-limited: a company asks for access
  GET  /me                       operator: name, sector, region
  GET  /admin/access-requests    admin: list requests
  POST /admin/access-requests/{id}/approve   admin: create the vault, issue the token, email the link
  POST /admin/access-requests/{id}/reject

Requests live in the registry directory (git-ignored) as JSON; the token
is stored only as a hash on the operator record, as everywhere else.
"""
from __future__ import annotations

import json
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.dependencies import rate_limiter, require_operator
from api.routers.admin import require_admin
from infrastructure.mailer import configured as mail_configured, send_email
from infrastructure.operator_registry import OperatorNotFoundError, OperatorRegistry

router = APIRouter(tags=["access"])
SECTORS = ("produce", "commercial")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AccessRequest(BaseModel):
    company: str = Field(min_length=2, max_length=120)
    contact_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=200)
    country: str = Field(min_length=2, max_length=60)
    sector: str
    erp: str = Field(default="", max_length=80)
    sku_count: int | None = Field(default=None, ge=0, le=1_000_000)
    note: str = Field(default="", max_length=1000)


def _store_path(registry: OperatorRegistry) -> Path:
    registry.registry_dir.mkdir(parents=True, exist_ok=True)
    return registry.registry_dir / "access_requests.json"


def _load(registry: OperatorRegistry) -> list:
    p = _store_path(registry)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text())
    except ValueError:
        return []


def _save(registry: OperatorRegistry, rows: list) -> None:
    p = _store_path(registry)
    p.write_text(json.dumps(rows, indent=1, default=str))
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def _app_url() -> str:
    return os.getenv("HARVESTMIND_APP_URL", "http://localhost:3000").rstrip("/")


@router.post("/access/request", dependencies=[Depends(rate_limiter)])
def request_access(req: AccessRequest):
    if req.sector not in SECTORS:
        raise HTTPException(422, f"sector must be one of {SECTORS}")
    if not _EMAIL.match(req.email):
        raise HTTPException(422, "a valid email address is required")
    registry = OperatorRegistry()
    rows = _load(registry)
    rid = f"req_{secrets.token_hex(4)}"
    rows.append({**req.model_dump(), "id": rid, "status": "pending",
                 "requested_at": datetime.now(timezone.utc).isoformat()})
    _save(registry, rows)
    admin_to = os.getenv("HARVESTMIND_ADMIN_EMAIL")
    if admin_to:
        send_email(admin_to, f"HarvestMind access request: {req.company}",
                   f"{req.company} ({req.country}, {req.sector}) — {req.contact_name} <{req.email}>\n"
                   f"ERP: {req.erp or '-'}  SKUs: {req.sku_count or '-'}\n{req.note}\n\nRequest id: {rid}")
    return {"id": rid, "status": "pending",
            "message": "Thanks. We review every request by hand and reply within one working day."}


@router.get("/me")
def me(authed: str | None = Depends(require_operator)):
    if not authed:
        raise HTTPException(401, "operator token required")
    registry = OperatorRegistry()
    try:
        rec = registry.get_operator(authed)
    except OperatorNotFoundError:
        raise HTTPException(404, "unknown operator")
    return {"operator_id": rec.operator_id, "name": rec.name, "sector": getattr(rec, "sector", "produce"),
            "region": rec.region, "created_at": rec.created_at, "upload_count": rec.upload_count}


@router.get("/admin/access-requests", dependencies=[Depends(require_admin)])
def list_requests(status: str = "pending"):
    rows = _load(OperatorRegistry())
    return [r for r in rows if status == "all" or r.get("status") == status]


@router.post("/admin/access-requests/{rid}/approve", dependencies=[Depends(require_admin)])
def approve(rid: str):
    registry = OperatorRegistry()
    rows = _load(registry)
    row = next((r for r in rows if r["id"] == rid), None)
    if row is None:
        raise HTTPException(404, "unknown request")
    if row.get("status") == "approved" and row.get("operator_id"):
        raise HTTPException(409, "already approved")
    rec = registry.create_operator(row["company"], region=row["country"], sector=row["sector"])
    token = registry.issue_token(rec.operator_id)
    link = f"{_app_url()}/access?token={token}"
    mail = send_email(row["email"], "Your HarvestMind access",
                      f"Hello {row['contact_name']},\n\nYour workspace for {row['company']} is ready.\n"
                      f"Open this link once to connect: {link}\n\nThe link carries your access token; it is shown "
                      f"only in this email and cannot be recovered, so keep it. Nothing you upload is shared with "
                      f"anyone else, and identifiers are pseudonymised before storage.\n\nHarvestMind")
    row.update(status="approved", operator_id=rec.operator_id, approved_at=datetime.now(timezone.utc).isoformat(),
               email_sent=bool(mail.get("sent")))
    _save(registry, rows)
    out = {"id": rid, "operator_id": rec.operator_id, "sector": row["sector"], "email_sent": bool(mail.get("sent"))}
    if not mail.get("sent"):
        # No mailer: hand the link to the admin exactly once so it can be sent by hand.
        out["access_link"] = link
        out["note"] = "mailer not configured; send this link to the requester yourself"
    return out


@router.post("/admin/access-requests/{rid}/reject", dependencies=[Depends(require_admin)])
def reject(rid: str):
    registry = OperatorRegistry()
    rows = _load(registry)
    row = next((r for r in rows if r["id"] == rid), None)
    if row is None:
        raise HTTPException(404, "unknown request")
    row.update(status="rejected", rejected_at=datetime.now(timezone.utc).isoformat())
    _save(registry, rows)
    return {"id": rid, "status": "rejected"}


@router.get("/access/mail-status", dependencies=[Depends(require_admin)])
def mail_status():
    return {"configured": mail_configured()}


# ── Demo tenant ─────────────────────────────────────────────────────────────
# A visitor can look around a workspace preloaded with SYNTHETIC data before
# sending anything. The admin creates it (below) and sets its token in
# HARVESTMIND_DEMO_TOKEN; the public endpoint hands that token out, rate
# limited. The demo vault is shared and writable, so it is reset by
# re-running the admin endpoint; it never holds operator data.

@router.post("/access/demo", dependencies=[Depends(rate_limiter)])
def demo_access():
    token = os.getenv("HARVESTMIND_DEMO_TOKEN")
    if not token:
        raise HTTPException(404, "no demo workspace is configured")
    return {"token": token, "sector": os.getenv("HARVESTMIND_DEMO_SECTOR", "commercial"),
            "note": "shared demo workspace with synthetic data; anything you upload here is visible to other visitors"}


@router.post("/admin/demo-operator", dependencies=[Depends(require_admin)])
def create_demo_operator(sector: str = "commercial", seed: int = 7):
    """Create (or recreate) a demo workspace loaded with synthetic history.
    Returns the token to put in HARVESTMIND_DEMO_TOKEN."""
    if sector not in SECTORS:
        raise HTTPException(422, f"sector must be one of {SECTORS}")
    registry = OperatorRegistry()
    rec = registry.create_operator(f"Demo ({sector}, synthetic data)", region="demo", sector=sector)
    from infrastructure.db_manager import DBManager
    dbm = DBManager(registry)
    conn = dbm.get_operator_connection(rec.operator_id)
    loaded: dict = {}
    try:
        if sector == "commercial":
            import pandas as pd

            from synthetic.fmcg.distributor_sim import build_history
            h = build_history("E_mixed_portfolio", seed=seed)
            po = h.purchase_orders.copy()
            rec_df = h.receipts.copy()
            skus = h.skus[["sku", "supplier_id", "unit_cost", "unit_price", "units_per_case", "moq_units", "category"]]
            orders = h.order_lines.merge(h.customer_orders[["order_id", "customer_id", "order_date"]], on="order_id")
            orders = orders[["order_id", "customer_id", "order_date", "sku", "qty_ordered"]]
            inv = h.inventory_snapshots.rename(columns={"week_start": "snapshot_date"})[["snapshot_date", "sku", "on_hand", "in_transit"]]
            sup = h.suppliers[["supplier_id"]].copy()
            sup["route"] = ["aqaba" if i % 2 == 0 else "road_saudi" for i in range(len(sup))]
            sup["origin_iso3"] = ["DEU" if i % 2 == 0 else "SAU" for i in range(len(sup))]
            for table, df in (("stg_fmcg_skus", skus), ("stg_fmcg_orders", orders),
                              ("stg_fmcg_purchase_orders", po[["po_id", "po_date", "supplier_id", "sku", "qty_ordered", "unit_cost"]]),
                              ("stg_fmcg_receipts", rec_df[["po_id", "receipt_date", "sku", "qty_received"]]),
                              ("stg_fmcg_inventory", inv), ("stg_fmcg_suppliers", sup)):
                frame = df.copy()
                for c in frame.columns:
                    if "date" in c:
                        frame[c] = pd.to_datetime(frame[c]).dt.date
                conn.register("_demo_df", frame)
                cols = ", ".join(frame.columns)
                conn.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM _demo_df")  # nosec B608 - table allowlisted above
                conn.unregister("_demo_df")
                loaded[table] = int(len(frame))
        else:
            from api.routers.intake import load_sample_data
            loaded = load_sample_data(conn=conn)
    finally:
        dbm.close_all()
    token = registry.issue_token(rec.operator_id)
    return {"operator_id": rec.operator_id, "sector": sector, "loaded": loaded, "token": token,
            "note": "set HARVESTMIND_DEMO_TOKEN to this value (and HARVESTMIND_DEMO_SECTOR) and restart"}


# ── Self-serve start (MVP) ──────────────────────────────────────────────────
# A visitor picks a sector and gets an isolated workspace immediately. No
# form, no approval: the token is the only credential, shown once to the
# browser that created the workspace. Rate limited like every public route.

class StartRequest(BaseModel):
    sector: str
    company: str = Field(default="", max_length=120)


@router.post("/access/start", dependencies=[Depends(rate_limiter)])
def self_serve_start(req: StartRequest):
    if req.sector not in SECTORS:
        raise HTTPException(422, f"sector must be one of {SECTORS}")
    if os.getenv("HARVESTMIND_SELF_SERVE", "true").strip().lower() in ("0", "false", "no"):
        raise HTTPException(404, "self-serve workspaces are disabled")
    registry = OperatorRegistry()
    name = (req.company.strip() or f"Workspace {secrets.token_hex(2)}")[:120]
    rec = registry.create_operator(name, region="unspecified", sector=req.sector)
    token = registry.issue_token(rec.operator_id)
    return {"operator_id": rec.operator_id, "sector": req.sector, "name": rec.name, "token": token,
            "note": "This token is your only key to this workspace. It is shown once. Keep it."}
