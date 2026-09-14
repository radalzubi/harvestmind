"use client";

/**
 * ONE PROPOSED ORDER — edit it, ask ZAAD what it does, approve it, export it.
 *
 * The comparison is the heart of this page, and it is three columns from the engine, never from
 * here: your current plan, what ZAAD recommends instead, and your proposal. All three come out of
 * the same optimizer over the same information set, because the evaluation runs the workspace
 * twice — once as it is, once with this order treated as placed. Subtracting two figures the
 * engine reported is the only arithmetic this page does.
 *
 * A change to an order that already exists is different and says so: an amendment is worth what
 * the contract says it is worth, so ZAAD reads its own commitment block rather than modelling the
 * change, and where no right is declared it reports that it cannot price it.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { CheckCircle2, Download, FileSearch, Trash2, Undo2 } from "lucide-react";
import { Gate } from "@/components/workspace/Gate";
import { Button, ButtonLink, Disclosure, ErrorState, Loading, Notice, PageHead, Section } from "@/components/workspace/ui";
import { Column, DataTable } from "@/components/workspace/Table";
import { HeaderFields, LineEditor, Warnings, type OrderHeader } from "@/components/workspace/OrderForm";
import { useToast } from "@/components/Toast";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import {
  AMENDMENT_LABEL, DATE, MONEY, NUMBER, ORIGIN_LABEL, PERCENT, STATE_LABEL,
  actOnDraft, deleteDraft, exportDraft, fetchProfiles, readAmendment, readDraft, readEvaluation,
  reviseDraft, startEvaluation, updateDraft,
  type Comparison, type Draft, type DraftLine, type EvaluationState, type ExportProfile, type LedgerRow,
} from "@/lib/zaad/product";

const POLL_MS = 4000;

function headerOf(draft: Draft): OrderHeader {
  return {
    reference: draft.reference ?? "",
    supplier_id: draft.supplier_id ?? "",
    destination_id: draft.destination_id ?? "",
    currency: draft.currency ?? "USD",
    requested_order_date: (draft.requested_order_date ?? "").slice(0, 10),
    requested_receipt_date: (draft.requested_receipt_date ?? "").slice(0, 10),
    notes: draft.notes ?? "",
  };
}

// ── the three-column comparison ───────────────────────────────────────────────

function delta(row: LedgerRow, currency: string) {
  if (row.proposal_vs_current == null) return <span className="na">—</span>;
  // Below half a cent the two plans are the same on this line. "−USD 0.00" reads as a saving.
  if (Math.abs(row.proposal_vs_current) < 0.005) return <span className="na">no change</span>;
  const sign = row.proposal_vs_current > 0 ? "up" : "down";
  return <span data-sign={sign}>{row.proposal_vs_current > 0 ? "+" : "−"}{MONEY(Math.abs(row.proposal_vs_current), currency)}</span>;
}

/** `svc_QA-0001@QA-DC-AMMAN` is an engine id. A person reads "QA-0001 at QA-DC-AMMAN". */
function serviceName(id: string, location: string | null): string {
  const stripped = id.replace(/^svc_/, "");
  const [sku, at] = stripped.split("@");
  return `${sku}${at || location ? ` at ${at || location}` : ""}`;
}

function ComparisonTable({ comparison }: { comparison: Comparison }) {
  const currency = comparison.currency;
  const columns: Column<LedgerRow>[] = [
    { key: "label", label: "", width: 220, render: (r) => r.label },
    { key: "current", label: "Your current plan", numeric: true, render: (r) => r.current != null ? MONEY(r.current, currency) : <span className="na">—</span> },
    { key: "zaad", label: "What ZAAD recommends", numeric: true, render: (r) => r.zaad != null ? MONEY(r.zaad, currency) : <span className="na">—</span> },
    { key: "proposal", label: "Your proposal", numeric: true, render: (r) => r.proposal != null ? MONEY(r.proposal, currency) : <span className="na">—</span> },
    { key: "difference", label: "Proposal vs current", numeric: true, render: (r) => delta(r, currency) },
  ];
  return (
    <>
      {comparison.zaad_abstained && (
        <div style={{ marginBottom: 12 }}>
          <Notice>
            ZAAD kept your current plan for these products, so the middle column is the same as the left one.
            It found no alternative worth recommending — which does not mean your proposal is not worth making.
          </Notice>
        </div>
      )}
      <DataTable caption="The plan's modelled cost, three ways" columns={columns} rows={comparison.ledger}
        rowKey={(r) => r.component} dense />
      <dl className="kv" style={{ marginTop: 14 }}>
        <dt>Cash tied up</dt>
        <dd>
          {comparison.working_capital.current != null ? MONEY(comparison.working_capital.current, currency) : "—"} now ·{" "}
          {comparison.working_capital.proposal != null ? MONEY(comparison.working_capital.proposal, currency) : "—"} with your proposal
        </dd>
      </dl>
      {comparison.service.length > 0 && (
        <Section title="What customers would get">
          <DataTable caption="Projected service by service line" dense rows={comparison.service} rowKey={(r) => r.service}
            columns={[
              { key: "service", label: "Service", render: (r) => serviceName(r.service, r.location) },
              { key: "requested", label: "Target", numeric: true, render: (r) => PERCENT(r.requested) },
              { key: "current", label: "Current plan", numeric: true, render: (r) => PERCENT(r.current) },
              { key: "zaad", label: "ZAAD", numeric: true, render: (r) => PERCENT(r.zaad) },
              { key: "proposal", label: "Your proposal", numeric: true, render: (r) => PERCENT(r.proposal) },
            ]} />
        </Section>
      )}
      <Section title="What this comparison does and does not cover">
        <ul style={{ margin: 0, paddingInlineStart: 18, fontSize: 13, color: "var(--ink-600)", lineHeight: 1.65 }}>
          {comparison.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}
        </ul>
        <div style={{ marginTop: 12 }}>
          <Disclosure summary="Where each column comes from" hint="so nobody has to take it on trust">
            <dl className="kv">
              {comparison.columns.map((column) => (
                <div key={column.key} style={{ display: "contents" }}>
                  <dt>{column.label}</dt><dd>{column.source}</dd>
                </div>
              ))}
              <dt>Information set</dt>
              <dd style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{comparison.information_hash?.slice(0, 16) ?? "—"}</dd>
              <dt>As at</dt><dd>{DATE(comparison.as_of)}</dd>
              <dt>Products covered</dt><dd>{comparison.scope.join(", ") || "—"}</dd>
            </dl>
          </Disclosure>
        </div>
      </Section>
    </>
  );
}

function Evaluation({ draft, onChanged }: { draft: Draft; onChanged: () => void }) {
  const [state, setState] = useState<EvaluationState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | null>(null);

  const poll = useCallback(async () => {
    try {
      const next = await readEvaluation(draft.draft_id);
      setState(next);
      if (next.status === "QUEUED" || next.status === "RUNNING") {
        timer.current = window.setTimeout(poll, POLL_MS);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [draft.draft_id]);

  useEffect(() => {
    poll();
    return () => { if (timer.current) window.clearTimeout(timer.current); };
  }, [poll]);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      await startEvaluation(draft.draft_id);
      await poll();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (draft.origin === "IMPORTED_AMENDMENT") return <AmendmentView draft={draft} />;

  const running = state?.status === "QUEUED" || state?.status === "RUNNING";
  return (
    <Section title="What this order would do">
      {error && <Notice tone="warn">{error}</Notice>}
      {state?.status === "NONE" && (
        <Notice>
          ZAAD has not evaluated this proposal yet. Evaluating runs the optimizer twice — once on your workspace
          as it is, once with this order placed — so the two are comparable. It takes a few minutes.
        </Notice>
      )}
      {running && (
        <div className="notice">
          <p className="phase" style={{ margin: 0 }} aria-live="polite">
            <span className="spin" aria-hidden />
            {state?.status === "QUEUED" ? "Queued" : "Running"} — two runs of the optimizer, a few minutes.
          </p>
          {state?.runs && (
            <dl className="kv" style={{ marginTop: 10 }}>
              <dt>Without your proposal</dt><dd>{state.runs.baseline?.status ?? "—"}</dd>
              <dt>With your proposal</dt><dd>{state.runs.proposal?.status ?? "—"}</dd>
            </dl>
          )}
        </div>
      )}
      {state?.status === "FAILED" && (
        <Notice tone="warn">
          One of the two runs did not finish, so there is nothing to compare.{" "}
          {Object.entries(state.runs ?? {}).map(([key, run]) => run.error ? `${key}: ${run.error}` : null).filter(Boolean).join(" ")}
        </Notice>
      )}
      {state?.comparison && !running && <ComparisonTable comparison={state.comparison} />}
      {state?.comparison?.unavailable?.length ? (
        <div style={{ marginTop: 12 }}><Notice tone="warn">{state.comparison.unavailable.join(" ")}</Notice></div>
      ) : null}
      <div style={{ marginTop: 14 }}>
        <Button role={state?.comparison ? "secondary" : "primary"} pending={busy} disabled={running || !draft.lines.length}
          icon={<FileSearch size={15} aria-hidden />} onClick={run}>
          {state?.comparison ? "Evaluate again" : "Ask ZAAD to evaluate this"}
        </Button>
      </div>
    </Section>
  );
}

function AmendmentView({ draft }: { draft: Draft }) {
  const [view, setView] = useState<Awaited<ReturnType<typeof readAmendment>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    readAmendment(draft.draft_id).then((v) => alive && setView(v)).catch((e) => alive && setError(e.message));
    return () => { alive = false; };
  }, [draft.draft_id]);

  return (
    <Section title="What this change is worth">
      {error && <Notice tone="warn">{error}</Notice>}
      {!view && !error && <Loading label="Reading the plan for this order…" cards={1} />}
      {view && !view.priced && <Notice tone="warn">{view.reason}</Notice>}
      {view?.priced && view.order && (
        <>
          <Notice>
            ZAAD&rsquo;s plan recommends{" "}
            <strong>{AMENDMENT_LABEL[(view.recommended_action ?? "KEEP") as keyof typeof AMENDMENT_LABEL] ?? view.recommended_action}</strong>{" "}
            for {view.po_id}. You are proposing{" "}
            <strong>{draft.amendment_action ? AMENDMENT_LABEL[draft.amendment_action] : "a change"}</strong>.
          </Notice>
          <div style={{ marginTop: 12 }}>
            <Disclosure summary="The engine's own reading of this order" hint="from the last plan" defaultOpen>
              <p style={{ margin: "0 0 10px", fontSize: 13, color: "var(--ink-700)", lineHeight: 1.6 }}>{view.reading}</p>
              <pre className="disc-tech">{JSON.stringify(view.order, null, 2)}</pre>
            </Disclosure>
          </div>
        </>
      )}
      <p className="zhelp" style={{ marginTop: 10 }}>
        A change to an existing order is worth what your contract says it is worth. ZAAD prices only the
        amendment rights you have declared for it, and never infers one.
      </p>
    </Section>
  );
}

// ── the page ──────────────────────────────────────────────────────────────────

function DraftBody({ id }: { id: string }) {
  const router = useRouter();
  const toast = useToast();
  const { request } = useWorkspaceData();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [header, setHeader] = useState<OrderHeader | null>(null);
  const [lines, setLines] = useState<DraftLine[]>([]);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [profiles, setProfiles] = useState<ExportProfile[]>([]);
  const [profileId, setProfileId] = useState<string>("");

  const load = useCallback(async () => {
    try {
      const next = await readDraft(id);
      setDraft(next);
      setHeader(headerOf(next));
      setLines(next.lines.map((l) => ({ ...l })));
      setDirty(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { fetchProfiles().then((p) => setProfiles(p.profiles)).catch(() => setProfiles([])); }, []);

  const locations = useMemo(() => (request?.locations ?? []).map((l) => l.id), [request]);

  if (error) {
    return <ErrorState title="That proposal could not be opened"
      affects="Nothing was changed." whatToDo="It may belong to another workspace, or it may have been deleted."
      detail={error} actions={<ButtonLink href="/orders" role="primary">Back to purchase orders</ButtonLink>} />;
  }
  if (!draft || !header) return <Loading label="Reading this proposal…" cards={2} />;

  const editable = draft.editable;
  const currency = header.currency || "USD";

  async function act(fn: () => Promise<unknown>, label: string, message: string) {
    setBusy(label);
    try {
      await fn();
      toast.push(message);
      await load();
    } catch (e) {
      toast.push(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHead
        title={draft.reference || draft.draft_id.replace(/^draft_/, "Proposal ")}
        sub={`${ORIGIN_LABEL[draft.origin]} · revision ${draft.revision} · ${STATE_LABEL[draft.state]}`}
        actions={<ButtonLink size="sm" href="/orders">All purchase orders</ButtonLink>}
      />

      {draft.source_po_id && (
        <Notice>
          A proposed change to <Link href={`/orders?po=${encodeURIComponent(draft.source_po_id)}`}>{draft.source_po_id}</Link>
          {draft.amendment_action ? <>: <strong>{AMENDMENT_LABEL[draft.amendment_action]}</strong></> : null}.
          The order in your system is untouched.
        </Notice>
      )}
      {draft.supersedes && (
        <div style={{ marginTop: 10 }}>
          <Notice>This is revision {draft.revision}. <Link href={`/orders/${encodeURIComponent(draft.supersedes)}`}>Revision {draft.revision - 1}</Link> is kept exactly as it was decided.</Notice>
        </div>
      )}
      {draft.state === "SUPERSEDED" && draft.superseded_by && (
        <div style={{ marginTop: 10 }}>
          <Notice tone="warn">This revision has been replaced by <Link href={`/orders/${encodeURIComponent(draft.superseded_by)}`}>a newer one</Link>.</Notice>
        </div>
      )}

      <Section title="The order">
        <HeaderFields value={header} onChange={(next) => { setHeader(next); setDirty(true); }}
          locations={locations} disabled={!editable} />
      </Section>

      <Section title="Lines">
        <LineEditor lines={lines} onChange={(next) => { setLines(next); setDirty(true); }}
          currency={currency} disabled={!editable} />
        <Warnings items={draft.warnings} />
        {editable && dirty && (
          <div style={{ marginTop: 14, display: "flex", gap: 8 }}>
            <Button role="primary" pending={busy === "save"} onClick={() => act(
              () => updateDraft(id, {
                ...header, currency: currency.toUpperCase(),
                requested_receipt_date: header.requested_receipt_date || null,
                lines: lines.filter((l) => l.sku.trim() && Number(l.quantity) > 0),
              }), "save", "Saved.")}>Save changes</Button>
            <Button role="tertiary" icon={<Undo2 size={14} aria-hidden />} onClick={load}>Discard changes</Button>
          </div>
        )}
        {!editable && (
          <div style={{ marginTop: 12 }}>
            <Notice>
              {draft.state === "READY_FOR_REVIEW"
                ? "This proposal is with a reviewer. Return it to draft to change it."
                : "This revision is part of the record and does not change. Create the next revision to change anything."}
            </Notice>
          </div>
        )}
      </Section>

      <Evaluation draft={draft} onChanged={load} />

      <Section title="Decision">
        {draft.state === "APPROVED" || draft.state === "EXPORTED" ? (
          <Notice>
            Approved{draft.approved_by ? ` by ${draft.approved_by}` : ""}{draft.approved_at ? ` on ${DATE(draft.approved_at)}` : ""}
            {draft.decision_reason ? `: “${draft.decision_reason}”` : "."}
          </Notice>
        ) : draft.state === "REJECTED" ? (
          <Notice tone="warn">Rejected{draft.decision_reason ? `: “${draft.decision_reason}”` : "."}</Notice>
        ) : (
          <>
            <label>
              <span className="fld-label">Why — a sentence the next person can read</span>
              <input className="fld fld--block" value={reason} onChange={(e) => setReason(e.target.value)}
                placeholder="Cover is thin and the alternative costs more" />
            </label>
            <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
              {draft.state === "DRAFT" && (
                <Button pending={busy === "submit"} onClick={() => act(() => actOnDraft(id, "submit"), "submit", "Sent for review.")}>
                  Send for review
                </Button>
              )}
              {draft.state === "READY_FOR_REVIEW" && (
                <Button role="tertiary" pending={busy === "reopen"} onClick={() => act(() => actOnDraft(id, "reopen"), "reopen", "Back to draft.")}>
                  Return to draft
                </Button>
              )}
              <Button role="primary" icon={<CheckCircle2 size={15} aria-hidden />} pending={busy === "approve"}
                disabled={!reason.trim()}
                onClick={() => act(() => actOnDraft(id, "approve", reason), "approve", "Approved. Nothing has been sent to a supplier.")}>
                Approve
              </Button>
              <Button role="danger" pending={busy === "reject"} disabled={!reason.trim()}
                onClick={() => act(() => actOnDraft(id, "reject", reason), "reject", "Rejected.")}>
                Reject
              </Button>
            </div>
          </>
        )}
      </Section>

      <Section title="Export">
        <p style={{ margin: "0 0 12px", fontSize: 13.5, color: "var(--ink-700)", lineHeight: 1.6, maxWidth: "62ch" }}>
          Produces a file in your own format for you to place. <strong>ZAAD does not send it anywhere</strong> —
          not to the supplier, not to your ERP. Every export is recorded below.
        </p>
        <div className="tbar">
          <label className="fld-wrap">
            <span className="sr-only">Format</span>
            <select className="fld" value={profileId} onChange={(e) => setProfileId(e.target.value)} aria-label="Output format">
              {profiles.map((p) => <option key={p.profile_id ?? "built-in"} value={p.profile_id ?? ""}>{p.name}</option>)}
            </select>
          </label>
          <Button icon={<Download size={15} aria-hidden />} pending={busy === "export"}
            disabled={!draft.lines.length}
            onClick={() => act(async () => {
              const name = await exportDraft(id, { profileId: profileId || null });
              toast.push(`${name} downloaded. It has not been sent to anyone.`);
            }, "export", "Exported.")}>
            Export
          </Button>
          <ButtonLink size="sm" role="tertiary" href="/orders/formats">Define a format</ButtonLink>
        </div>
        {draft.exports.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <DataTable caption="Files exported from this proposal" dense rows={draft.exports} rowKey={(r) => r.export_id}
              columns={[
                { key: "filename", label: "File", render: (r) => r.filename },
                { key: "profile_name", label: "Format", render: (r) => `${r.profile_name} (${r.format})` },
                { key: "happened_at", label: "When", render: (r) => DATE(r.happened_at) },
                { key: "actor", label: "By", render: (r) => r.actor ?? "—" },
              ]} />
          </div>
        )}
      </Section>

      <Section title="History">
        <DataTable caption="What has happened to this proposal" dense rows={draft.events}
          rowKey={(r, ) => `${r.happened_at}-${r.event}`}
          columns={[
            { key: "event", label: "Event", render: (r) => r.event },
            { key: "happened_at", label: "When", render: (r) => DATE(r.happened_at) },
            { key: "actor", label: "By", render: (r) => r.actor ?? "—" },
            { key: "detail", label: "Detail", render: (r) => r.detail ?? "—" },
          ]} />
      </Section>

      <div style={{ marginTop: 22, display: "flex", gap: 8, flexWrap: "wrap" }}>
        {["APPROVED", "EXPORTED", "REJECTED"].includes(draft.state) && (
          <Button pending={busy === "revise"} onClick={() => act(async () => {
            const next = await reviseDraft(id);
            router.push(`/orders/${encodeURIComponent(next.draft_id)}`);
          }, "revise", "New revision created.")}>Create the next revision</Button>
        )}
        {draft.deletable && (
          <Button role="danger" icon={<Trash2 size={14} aria-hidden />} pending={busy === "delete"}
            onClick={() => act(async () => { await deleteDraft(id); router.push("/orders"); }, "delete", "Deleted.")}>
            Delete this draft
          </Button>
        )}
      </div>
    </>
  );
}

export default function DraftPage() {
  const params = useParams<{ id: string }>();
  const id = Array.isArray(params?.id) ? params.id[0] : params?.id;
  return (
    <Gate loadingLabel="Opening your workspace…" needsPlan={false}>
      {id ? <DraftBody id={id} /> : <Loading label="Opening this proposal…" cards={2} />}
    </Gate>
  );
}
