"""The last mile, as a seam.

Today an approved proposal leaves ZAAD as a file the operator places themselves. Later it may
leave through a connector to an ERP. Both must operate from the same approved canonical action
object — the draft as `drafts.read_draft` returns it — through the same four verbs:

    validate   can this adapter take this object as it stands?
    preview    what would it produce or send, without producing or sending it?
    submit     produce or send it, and say what happened
    get_status what the other side says about it since

Only one real adapter exists: the file export. A test adapter exists so the seam can be exercised
and is labelled as such. **No adapter is named for a system it does not integrate with.**
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from api.product import exporting


class OutboundRefused(ValueError):
    """The adapter cannot take the object as it stands. The message says why."""


@dataclass(frozen=True)
class SubmitResult:
    #: what the adapter did, in words an operator reads: "file produced", "sent to test endpoint"
    outcome: str
    payload: bytes = b""
    media_type: str = "application/octet-stream"
    filename: str = ""
    #: the reference the other side gave, when there is another side
    external_reference: str | None = None
    #: always False for the file adapter: producing a file is not transmitting it
    transmitted: bool = False
    detail: dict[str, Any] = field(default_factory=dict)


class OutboundAdapter(Protocol):
    name: str
    kind: str          # "file" | "test" — never a vendor name unless it integrates with that vendor
    real: bool         # False for a test/mock adapter

    def describe(self) -> dict[str, Any]: ...
    def validate(self, draft: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]: ...
    def preview(self, draft: dict[str, Any], profile: dict[str, Any], **kw: Any) -> dict[str, Any]: ...
    def submit(self, draft: dict[str, Any], profile: dict[str, Any], **kw: Any) -> SubmitResult: ...
    def get_status(self, external_reference: str) -> dict[str, Any]: ...


class FileExportAdapter:
    """The one real adapter: a CSV, XLSX or printable PDF the operator places themselves."""

    name = "file-export"
    kind = "file"
    real = True

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "real": True, "transmits": False,
                "note": "Produces a file in your own format for you to place. Nothing is sent anywhere."}

    def validate(self, draft: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        problems: list[str] = []
        if not draft.get("lines"):
            problems.append("This proposal has no lines.")
        if draft.get("state") not in ("APPROVED", "EXPORTED"):
            problems.append("Only an approved proposal is exported.")
        fmt = str(profile.get("format") or "csv").lower()
        if fmt not in exporting.FORMATS:
            problems.append(f"{fmt!r} is not a format ZAAD writes.")
        for column in profile.get("columns") or []:
            if column.get("field") and column["field"] not in exporting.EXPORT_FIELDS:
                problems.append(f"Column {column.get('header')!r} maps to a field ZAAD does not hold.")
        return {"ok": not problems, "problems": problems}

    def preview(self, draft: dict[str, Any], profile: dict[str, Any], **kw: Any) -> dict[str, Any]:
        headers, body = exporting.build_rows(draft, profile, supplier_names=kw.get("supplier_names"))
        return {"filename": exporting.filename(draft, profile) + "." + {"print": "pdf"}.get(str(profile.get("format")), str(profile.get("format") or "csv")),
                "headers": headers, "rows": body[:10], "row_count": len(body), "transmits": False}

    def submit(self, draft: dict[str, Any], profile: dict[str, Any], **kw: Any) -> SubmitResult:
        check = self.validate(draft, profile)
        if not check["ok"]:
            raise OutboundRefused(" ".join(check["problems"]))
        try:
            payload, media, filename = exporting.render(draft, profile, supplier_names=kw.get("supplier_names"),
                                                        workspace=str(kw.get("workspace") or ""))
        except exporting.ExportRefused as exc:
            raise OutboundRefused(str(exc)) from exc
        return SubmitResult(outcome="file produced", payload=payload, media_type=media, filename=filename,
                            external_reference=None, transmitted=False, detail={"format": profile.get("format")})

    def get_status(self, external_reference: str) -> dict[str, Any]:
        return {"known": False, "note": "A file has no other side to ask. Record what happened to it on the proposal."}


class TestConnector:
    """A **test** adapter, labelled as such, that records what it was given and sends nothing.

    Exists so the seam can be exercised end to end. It is never offered to an operator and never
    called by the product outside tests.
    """

    name = "test-connector"
    kind = "test"
    real = False

    def __init__(self) -> None:
        self.submitted: list[dict[str, Any]] = []

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "real": False, "transmits": False,
                "note": "TEST adapter: records what it is given and sends nothing anywhere."}

    def validate(self, draft: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
        return FileExportAdapter().validate(draft, profile)

    def preview(self, draft: dict[str, Any], profile: dict[str, Any], **kw: Any) -> dict[str, Any]:
        return {"would_send": {"draft_id": draft.get("draft_id"), "lines": len(draft.get("lines") or [])}, "transmits": False}

    def submit(self, draft: dict[str, Any], profile: dict[str, Any], **kw: Any) -> SubmitResult:
        check = self.validate(draft, profile)
        if not check["ok"]:
            raise OutboundRefused(" ".join(check["problems"]))
        self.submitted.append({"draft_id": draft.get("draft_id"), "revision": draft.get("revision")})
        return SubmitResult(outcome="recorded by the test connector; nothing was sent",
                            external_reference=f"TEST-{len(self.submitted)}", transmitted=False)

    def get_status(self, external_reference: str) -> dict[str, Any]:
        return {"known": external_reference.startswith("TEST-"), "status": "test", "transmits": False}


ADAPTERS: dict[str, type] = {"file-export": FileExportAdapter}
