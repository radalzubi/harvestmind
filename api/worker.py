"""One-shot diagnostic worker.

Runs on an ephemeral machine (see infrastructure/fly_machines.py). It pulls
its job's data bundle from the API over the private network, rebuilds the
workspace's staging tables in a scratch vault, runs the same diagnostic
code the in-process thread would run, reports progress, posts the result
and exits. It never sees a workspace key and holds nothing after exit.

Env: ZAAD_JOB_ID, ZAAD_INTERNAL_API (http://[6pn-ip]:8000), HARVESTMIND_WORKER_TOKEN.
"""
from __future__ import annotations

import io
import json
import logging
import os
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

log = logging.getLogger("harvestmind.worker")


def _internal_base() -> str:
    """The API address the launcher handed us: http(s) only, no file or custom schemes."""
    base = os.environ["ZAAD_INTERNAL_API"].rstrip("/")
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.query or parsed.fragment:
        raise RuntimeError("ZAAD_INTERNAL_API must be an http(s) origin")
    return base


def _call(method: str, path: str, body: dict | None = None, raw: bool = False, tries: int = 5):
    base = _internal_base()
    if not path.startswith("/jobs/internal/"):
        raise RuntimeError("worker may only call the internal job endpoints")
    tok = os.environ["HARVESTMIND_WORKER_TOKEN"]
    data = json.dumps(body, default=str).encode() if body is not None else None
    last: Exception | None = None
    for attempt in range(tries):
        req = urllib.request.Request(base + path, method=method, data=data,
                                     headers={"X-Worker-Token": tok, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310  # nosec B310 - scheme and path validated above
                out = resp.read()
            return out if raw else (json.loads(out) if out else {})
        except (urllib.error.URLError, OSError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"API unreachable after {tries} tries: {last}")


def restore_bundle(blob: bytes, data_root: Path):
    """Rebuild the staging tables from the bundle in a scratch vault and
    return (conn, meta). Schema comes from the same migrations the API uses."""
    from infrastructure.db_manager import DBManager
    from infrastructure.operator_registry import OperatorRegistry
    reg = OperatorRegistry(data_root=data_root)
    meta = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        meta = json.loads(zf.read("job.json"))
        rec = reg.create_operator(meta.get("name", "worker"), sector=meta.get("sector", "commercial"))
        dbm = DBManager(reg)
        conn = dbm.get_operator_connection(rec.operator_id)
        tmp = data_root / "bundle"
        tmp.mkdir(exist_ok=True)
        for name in zf.namelist():
            if not name.endswith(".parquet"):
                continue
            table = name[:-len(".parquet")]
            if not table.startswith("stg_") or not table.replace("_", "").isalnum():
                continue
            target = tmp / name
            target.write_bytes(zf.read(name))
            conn.execute(f"INSERT INTO {table} BY NAME SELECT * FROM read_parquet(?)", [str(target)])  # noqa: S608  # nosec B608 - validated staging name
    return conn, meta


def run_job(job_id: str) -> int:
    from api.routers.jobs import _run_commercial, _run_produce
    job: dict[str, Any] = {"id": job_id, "status": "running", "progress": "worker starting"}

    def hook(kw: dict) -> None:
        if "progress" in kw or "stage" in kw:
            try:
                out = _call("POST", f"/jobs/internal/{job_id}/progress",
                            {"progress": kw.get("progress", job.get("progress", "")), "stage": kw.get("stage", job.get("stage"))}, tries=2)
            except RuntimeError as exc:
                log.warning("progress not delivered: %s", exc)
                return
            if isinstance(out, dict) and out.get("ok") is False:
                # the operator cancelled, or the API timed the job out: stop solving
                raise SystemExit(3)
    job["_hook"] = hook

    blob = _call("GET", f"/jobs/internal/{job_id}/bundle", raw=True)
    with tempfile.TemporaryDirectory() as td:
        conn, meta = restore_bundle(blob, Path(td))
        try:
            sector = meta.get("sector", "commercial")
            summary = _run_commercial(conn, job) if sector == "commercial" else _run_produce(conn, job)
            _call("POST", f"/jobs/internal/{job_id}/result", {"status": "done", "summary": summary})
            return 0
        except Exception as exc:  # noqa: BLE001
            log.exception("diagnostic failed on worker")
            _call("POST", f"/jobs/internal/{job_id}/result",
                  {"status": "failed", "error": f"{type(exc).__name__}: {exc}"[:300]})
            return 1


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    job_id = os.environ.get("ZAAD_JOB_ID")
    if not job_id:
        log.error("ZAAD_JOB_ID missing")
        return 2
    t = time.time()
    code = run_job(job_id)
    log.info("job %s finished with %d in %.0fs", job_id, code, time.time() - t)
    return code


if __name__ == "__main__":
    sys.exit(main())
