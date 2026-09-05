"""Outbound email for access links. Uses the Resend HTTP API when
RESEND_API_KEY is set; otherwise sends nothing and says so, so the admin
can copy the link by hand. Never raises into a request path."""
from __future__ import annotations

import logging
import os

log = logging.getLogger("harvestmind.mailer")


def configured() -> bool:
    return bool(os.getenv("RESEND_API_KEY"))


def send_email(to: str, subject: str, text: str) -> dict:
    if not configured():
        log.info("mailer not configured; email to %s not sent", to)
        return {"sent": False, "reason": "RESEND_API_KEY not set"}
    try:
        import requests
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}", "Content-Type": "application/json"},
            json={"from": os.getenv("HARVESTMIND_MAIL_FROM", "HarvestMind <access@harvestmind.app>"),
                  "to": [to], "subject": subject, "text": text},
            timeout=20,
        )
        ok = r.status_code < 300
        if not ok:
            log.warning("mailer: %s %s", r.status_code, r.text[:200])
        return {"sent": ok, "status": r.status_code}
    except Exception as exc:  # noqa: BLE001
        log.warning("mailer failed: %s", type(exc).__name__)
        return {"sent": False, "reason": type(exc).__name__}
