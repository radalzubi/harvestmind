"""Durable tenant-bound append-only decision/outcome ledger. Never a training DB."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid

from zaad.full.contracts import Request
from zaad.full.planner import report_json


class ShadowConflict(ValueError):
    pass


class ShadowLedger:
    def __init__(self, path: Path):
        self.path = path
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError("shadow storage cannot use symlinks")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS decisions (
              id TEXT PRIMARY KEY, operator TEXT NOT NULL, information_hash TEXT NOT NULL,
              created_at TEXT NOT NULL, expires_at TEXT NOT NULL, request TEXT NOT NULL,
              report TEXT NOT NULL, status TEXT NOT NULL, version INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, decision_id TEXT NOT NULL,
              operator TEXT NOT NULL, timestamp TEXT NOT NULL, kind TEXT NOT NULL,
              payload TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS decisions_tenant ON decisions(operator, created_at);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def _event(self, db, decision_id, operator, kind, payload, now):
        prior = db.execute("SELECT hash FROM events WHERE decision_id=? AND operator=? ORDER BY id DESC LIMIT 1",
                           (decision_id, operator)).fetchone()
        previous = prior[0] if prior else ""
        body = report_json(payload)
        digest = hashlib.sha256((previous + decision_id + operator + now.isoformat() + kind + body).encode()).hexdigest()
        db.execute("INSERT INTO events(decision_id,operator,timestamp,kind,payload,previous_hash,hash) VALUES(?,?,?,?,?,?,?)",
                   (decision_id, operator, now.isoformat(), kind, body, previous, digest))

    def save(self, req: Request, report: dict, operator: str, now: datetime | None = None) -> str:
        now = now or datetime.now(timezone.utc)
        fingerprint = hashlib.sha256(req.model_dump_json().encode()).hexdigest()
        if operator != req.operator_id or report["operator_id"] != operator or report["information_hash"] != fingerprint:
            raise ShadowConflict("tenant/information-set mismatch")
        expires = min([req.as_of + timedelta(days=req.period_days)] + [s.quote_expires for s in req.sources]
                      + [o.deadline for p in req.pipeline for o in p.options if o.action != "keep"])
        state = "PENDING_REVIEW" if report["status"] == "PENDING_REVIEW" and expires > now else "EXPIRED"
        identity = str(uuid.uuid4())
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?)", (identity, operator, fingerprint,
                       now.isoformat(), expires.isoformat(), req.model_dump_json(), report_json(report), state, 1))
            self._event(db, identity, operator, "CREATED", {"status": state, "information_hash": fingerprint}, now)
        return identity

    def get(self, decision_id: str, operator: str, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        with self.connect() as db:
            row = db.execute("SELECT * FROM decisions WHERE id=? AND operator=?", (decision_id, operator)).fetchone()
            if row is None:
                raise KeyError("decision not found")
            result = dict(row)
            if result["status"] == "PENDING_REVIEW" and datetime.fromisoformat(result["expires_at"]) <= now:
                result["status"] = "EXPIRED"
            result["request"], result["report"] = json.loads(result["request"]), json.loads(result["report"])
            result["events"] = [dict(r) for r in db.execute("SELECT timestamp,kind,payload,hash,previous_hash FROM events WHERE decision_id=? AND operator=? ORDER BY id", (decision_id, operator))]
            return result

    def review(self, decision_id: str, operator: str, status: str, information_hash: str,
               version: int, reason: str, now: datetime | None = None) -> dict:
        now = now or datetime.now(timezone.utc)
        if status not in {"APPROVED", "REJECTED"} or not reason.strip() or len(reason) > 2000:
            raise ShadowConflict("explicit review and reason required")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM decisions WHERE id=? AND operator=?", (decision_id, operator)).fetchone()
            if row is None:
                raise KeyError("decision not found")
            if row["information_hash"] != information_hash or row["version"] != version:
                raise ShadowConflict("stale or different information set; replan")
            if row["status"] != "PENDING_REVIEW" or datetime.fromisoformat(row["expires_at"]) <= now:
                raise ShadowConflict("decision is no longer pending or has expired")
            db.execute("UPDATE decisions SET status=?,version=version+1 WHERE id=? AND operator=? AND version=?",
                       (status, decision_id, operator, version))
            self._event(db, decision_id, operator, status, {"reason": reason, "human_only": True, "approved_action_scope": "period_zero_only"}, now)
        return self.get(decision_id, operator, now)

    def outcome(self, decision_id: str, operator: str, observation: dict, now: datetime | None = None):
        now = now or datetime.now(timezone.utc)
        self.get(decision_id, operator, now)
        if len(report_json(observation)) > 65536:
            raise ShadowConflict("outcome exceeds 64 KiB")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._event(db, decision_id, operator, "OUTCOME", observation, now)
