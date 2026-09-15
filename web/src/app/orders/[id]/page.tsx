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
import { Column, DataTable, NotAvailable } from "@/components/workspace/Table";
import { HeaderFields, LineEditor, Warnings, type OrderHeader } from "@/components/workspace/OrderForm";
import { useToast } from "@/components/Toast";
import { useSession } from "@/lib/session";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import {
  AMENDMENT_LABEL, DATE, EXTERNAL_LABEL, EXTERNAL_NEXT, MONEY, NUMBER, ORIGIN_LABEL, OUTCOME_METRICS, PERCENT, STATE_LABEL,
  actOnDraft, deleteDraft, exportDraft, exportPreview, fetchProfiles, readAmendment, readDraft, readEvaluation, readHistory,
  recordExternalStatus, recordOutcome, reviseDraft, startEvaluation, track, updateDraft,
  type Comparison, type Draft, type DraftHistory, type DraftLine, type EvaluationState, type ExportPreview, type ExportProfile,
  type ExternalStatus, type LedgerRow,
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

  // `updated_at` is in the dependency list on purpose: saving an edit is what makes an existing
  // comparison out of date, and the answer to "is it?" comes from the server. Without it the page
  // would keep the stale comparison, unmarked, until the next reload.
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
  }, [draft.draft_id, draft.updated_at]);

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
      {/* A draft stays editable and an edit does not start a new revision, so a comparison can
          outlive the lines it was computed for. Saying so is the difference between an honest
          answer and a confident wrong one. */}
      {state?.stale && !running && state.stale_reason && (
        <div style={{ marginBottom: 12 }}>
          <Notice tone="warn">
            <strong>This comparison is out of date.</strong> {state.stale_reason}
          </Notice>
        </div>
      )}
      {state?.comparison && !running && <ComparisonTable comparison={state.comparison} />}
      {state?.comparison?.unavailable?.length ? (
        <div style={{ marginTop: 12 }}><Notice tone="warn">{state.comparison.unavailable.join(" ")}</Notice></div>
      ) : null}
      <div style={{ marginTop: 14 }}>
        <Button role={state?.comparison && !state?.stale ? "secondary" : "primary"} pending={busy} disabled={running || !draft.lines.length}
          icon={<FileSearch size={15} aria-hidden />} onClick={run}>
          {state?.stale ? "Evaluate what you have now" : state?.comparison ? "Evaluate again" : "Ask ZAAD to evaluate this"}
        </Button>
        {/* The Approve/Reject pair already explains why it is greyed. These two did not: a
            proposal with no lines left four disabled buttons and one warning in another section
            that a reader had to connect for themselves. */}
        {!draft.lines.length && (
          <p className="zhelp" style={{ marginTop: 8 }}>
            There is nothing to evaluate until this proposal has a line. Add a product above.
          </p>
        )}
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
      {view?.reason && <Notice tone={view.declared_windows?.length ? "info" : "warn"}>{view.reason}</Notice>}
      {/* The rights the contract declares, whether or not the plan chose to use one. Every value
          is the engine's own; nothing is multiplied out into a total ZAAD did not compute. */}
      {view?.declared_windows && view.declared_windows.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <DataTable caption={`Declared amendment terms on ${view.po_id}`} dense
            rows={view.declared_windows} rowKey={(w) => String(w.option)}
            columns={[
              { key: "action", label: "Right", render: (w) => (
                // The chip must survive the narrow rule (max-width 180px, nowrap), so this cell
                // wraps rather than ellipsising "you are proposing this" off the end.
                <span style={{ whiteSpace: "normal", display: "inline-block" }}>
                  {String(w.label ?? w.action)}
                  {draft.amendment_action && String(w.option) === String(view.proposed_window?.option)
                    ? <span className="chip" data-tone="good" style={{ marginInlineStart: 6 }}>you are proposing this</span>
                    : null}
                </span>
              ) },
              { key: "fee_per_unit", label: "Fee/unit", numeric: true,
                render: (w) => w.fee_per_unit != null ? MONEY(Number(w.fee_per_unit), draft.currency ?? "USD") : <NotAvailable /> },
              { key: "credit_per_unit", label: "Credit/unit", numeric: true,
                render: (w) => w.credit_per_unit != null ? MONEY(Number(w.credit_per_unit), draft.currency ?? "USD") : <NotAvailable /> },
              { key: "capacity_units", label: "Up to", numeric: true,
                render: (w) => w.capacity_units != null ? NUMBER(Number(w.capacity_units)) : <NotAvailable /> },
              { key: "deadline", label: "By", render: (w) => w.deadline ? DATE(String(w.deadline)) : <NotAvailable /> },
              { key: "provenance", label: "Where from", render: (w) => String(w.provenance ?? "—").replaceAll("_", " ").toLowerCase() },
            ]} />
          <p className="zhelp" style={{ marginTop: 8 }}>
            These are the per-unit terms your own contract declares, read back from the plan. ZAAD
            prices a change against them inside a plan — it does not total them up here.
          </p>
        </div>
      )}
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

// ── the closed loop: what a person recorded happened outside ZAAD ─────────────

function ExternalStatusPanel({ draft, onChanged }: { draft: Draft; onChanged: () => void }) {
  const session = useSession();
  const toast = useToast();
  const [status, setStatus] = useState<ExternalStatus | "">("");
  const [reference, setReference] = useState("");
  const [observed, setObserved] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const decided = draft.state === "APPROVED" || draft.state === "EXPORTED";
  const next = EXTERNAL_NEXT[draft.external_status ?? "none"] ?? [];
  const canRecord = session.can("recordExternal");

  if (!decided) return null;

  async function save() {
    if (!status) return;
    setBusy(true);
    try {
      await recordExternalStatus(draft.draft_id, {
        status, external_reference: reference.trim() || null, note: note.trim() || null,
        observed_at: observed || null, expected_version: draft.version ?? null,
      });
      track("external_status_recorded", { draft_id: draft.draft_id });
      toast.push(`Recorded: ${EXTERNAL_LABEL[status]}. ZAAD sent nothing; this is your record.`);
      setStatus(""); setReference(""); setObserved(""); setNote("");
      onChanged();
    } catch (e) {
      toast.push(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Section title="What happened outside ZAAD">
      <p style={{ margin: "0 0 12px", fontSize: 13.5, color: "var(--ink-700)", lineHeight: 1.6, maxWidth: "62ch" }}>
        ZAAD does not place, send or receive orders. Record here what you did with this one in your own system and what
        the supplier said, so the record follows the order to the end.
      </p>
      <dl className="kv">
        <dt>Recorded so far</dt>
        <dd>
          {draft.external_status
            ? <>{EXTERNAL_LABEL[draft.external_status]}{draft.external_reference ? ` · reference ${draft.external_reference}` : ""}
                {draft.external_updated_at ? ` · ${DATE(draft.external_updated_at)}` : ""}{draft.external_updated_by ? ` · by ${draft.external_updated_by}` : ""}</>
            : <span className="na">Not yet recorded as placed</span>}
        </dd>
      </dl>
      {next.length > 0 && canRecord && (
        <div style={{ marginTop: 12, display: "grid", gap: 8, maxWidth: 560 }}>
          <label>
            <span className="fld-label">What happened</span>
            <select className="fld fld--block" value={status} onChange={(e) => setStatus(e.target.value as ExternalStatus | "")} aria-label="What happened">
              <option value="">Choose…</option>
              {next.map((s) => <option key={s} value={s}>{EXTERNAL_LABEL[s]}</option>)}
            </select>
          </label>
          <label>
            <span className="fld-label">Reference your system or supplier gave (optional)</span>
            <input className="fld fld--block" value={reference} onChange={(e) => setReference(e.target.value)} maxLength={200} placeholder="ERP order number, supplier confirmation" />
          </label>
          <label>
            <span className="fld-label">When (optional, defaults to now)</span>
            <input className="fld" type="datetime-local" value={observed} onChange={(e) => setObserved(e.target.value)} aria-label="When it happened" />
          </label>
          <label>
            <span className="fld-label">Note (optional)</span>
            <input className="fld fld--block" value={note} onChange={(e) => setNote(e.target.value)} maxLength={2000} />
          </label>
          <div>
            <Button role="primary" pending={busy} disabled={!status} onClick={save}>Record it</Button>
          </div>
        </div>
      )}
      {next.length === 0 && draft.external_status && (
        <p className="zhelp" style={{ marginTop: 8 }}>This order's record is complete: {EXTERNAL_LABEL[draft.external_status].toLowerCase()}.</p>
      )}
      {!canRecord && next.length > 0 && <p className="zhelp" style={{ marginTop: 8 }}>Your role can read this record but not add to it.</p>}
    </Section>
  );
}

function OutcomesPanel({ draft, history, onChanged }: { draft: Draft; history: DraftHistory | null; onChanged: () => void }) {
  const session = useSession();
  const toast = useToast();
  const [metric, setMetric] = useState("received_units");
  const [value, setValue] = useState("");
  const [observed, setObserved] = useState("");
  const [comparator, setComparator] = useState("");
  const [basis, setBasis] = useState("");
  const [busy, setBusy] = useState(false);
  const decided = draft.state === "APPROVED" || draft.state === "EXPORTED";
  if (!decided) return null;
  const canRecord = session.can("recordOutcome");
  const unit = OUTCOME_METRICS[metric]?.unit;
  const currency = draft.currency ?? "USD";

  async function save() {
    setBusy(true);
    try {
      await recordOutcome(draft.draft_id, {
        metric, value: unit === "date" ? null : (value === "" ? null : Number(value)),
        observed_at: observed || null, comparator_value: comparator === "" ? null : Number(comparator), comparator_basis: basis.trim() || null,
      });
      track("outcome_recorded", { draft_id: draft.draft_id });
      toast.push("Outcome recorded as observed after this action.");
      setValue(""); setObserved(""); setComparator(""); setBasis("");
      onChanged();
    } catch (e) {
      toast.push(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const fmt = (metricName: string, v: number | null) => {
    if (v == null) return "—";
    const kind = OUTCOME_METRICS[metricName]?.unit;
    return kind === "money" ? MONEY(v, currency) : kind === "fraction" ? PERCENT(v) : NUMBER(v);
  };

  return (
    <Section title="What happened afterwards">
      <p style={{ margin: "0 0 12px", fontSize: 13.5, color: "var(--ink-700)", lineHeight: 1.6, maxWidth: "62ch" }}>
        Observed after the action — never attributed to ZAAD. A saving is claimed only where you record what was observed
        <em> and</em> a comparator with its basis stated.
      </p>
      {history && (
        <dl className="kv" style={{ marginBottom: 12 }}>
          <dt>Modelled difference</dt>
          <dd>{history.evaluations.length ? `${history.evaluations.length} evaluation${history.evaluations.length === 1 ? "" : "s"} — see “What this order would do”` : <span className="na">Not evaluated</span>}</dd>
          <dt>Approved against</dt>
          <dd>{draft.approval_evaluation_state === "current" ? "a current evaluation"
            : draft.approval_evaluation_state === "stale_acknowledged" ? "an evaluation the approver knew was out of date"
            : draft.approval_evaluation_state === "none" ? "no evaluation" : <span className="na">Not recorded</span>}</dd>
          <dt>Backtested opportunity</dt><dd><span className="na">Not available — no held-out replay is wired into this product</span></dd>
          <dt>Realized outcome</dt>
          <dd>{history.realized_value.realized_outcome ? `${history.outcomes.length} observation${history.outcomes.length === 1 ? "" : "s"} recorded` : <span className="na">None observed yet</span>}</dd>
          <dt>Realized savings</dt>
          <dd>{history.realized_value.realized_savings.length
            ? history.realized_value.realized_savings.map((r) => (
                <div key={r.metric}>{OUTCOME_METRICS[r.metric]?.label ?? r.metric}: observed {fmt(r.metric, r.observed)} against {fmt(r.metric, r.comparator)}
                  {r.difference != null ? ` — ${r.difference >= 0 ? "" : "−"}${MONEY(Math.abs(r.difference), currency)} ${r.difference >= 0 ? "less" : "more"} than the comparator` : ""} <small style={{ color: "var(--ink-500)" }}>(basis: {r.basis})</small></div>))
            : <span className="na">None — no observation carries a comparator with its basis</span>}</dd>
        </dl>
      )}
      {history && history.outcomes.length > 0 && (
        <DataTable caption="Observations recorded for this order" dense rows={history.outcomes} rowKey={(r) => r.outcome_id}
          columns={[
            { key: "metric", label: "What", render: (r) => OUTCOME_METRICS[r.metric]?.label ?? r.metric },
            { key: "value", label: "Observed", numeric: true, render: (r) => fmt(r.metric, r.value) },
            { key: "observed_at", label: "When", render: (r) => r.observed_at ? DATE(r.observed_at) : <span className="na">—</span> },
            { key: "source", label: "How", render: (r) => r.source === "matched" ? "matched from receipts" : "recorded by a person" },
            { key: "comparator", label: "Comparator", render: (r) => r.comparator_value != null ? `${fmt(r.metric, r.comparator_value)} · ${r.comparator_basis}` : <span className="na">none</span> },
          ]} />
      )}
      {canRecord && (
        <div style={{ marginTop: 12, display: "grid", gap: 8, maxWidth: 560 }}>
          <label>
            <span className="fld-label">Record an observation</span>
            <select className="fld fld--block" value={metric} onChange={(e) => setMetric(e.target.value)} aria-label="What was observed">
              {Object.entries(OUTCOME_METRICS).map(([k, m]) => <option key={k} value={k}>{m.label}</option>)}
            </select>
          </label>
          {unit !== "date" && (
            <label><span className="fld-label">Value ({unit === "money" ? currency : unit})</span>
              <input className="fld" type="number" value={value} onChange={(e) => setValue(e.target.value)} aria-label="Observed value" /></label>
          )}
          <label><span className="fld-label">Observed on</span>
            <input className="fld" type="date" value={observed} onChange={(e) => setObserved(e.target.value)} aria-label="Observed on" /></label>
          {(unit === "money") && (
            <>
              <label><span className="fld-label">Comparator (optional): the figure it is measured against</span>
                <input className="fld" type="number" value={comparator} onChange={(e) => setComparator(e.target.value)} aria-label="Comparator value" /></label>
              <label><span className="fld-label">Where the comparator comes from (required with a comparator)</span>
                <input className="fld fld--block" value={basis} onChange={(e) => setBasis(e.target.value)} maxLength={500} placeholder="e.g. the price on the superseded order in our ERP" /></label>
            </>
          )}
          <div><Button pending={busy} disabled={unit !== "date" && value === ""} onClick={save}>Record observation</Button></div>
        </div>
      )}
    </Section>
  );
}

// ── the page ──────────────────────────────────────────────────────────────────

function DraftBody({ id }: { id: string }) {
  const router = useRouter();
  const toast = useToast();
  const session = useSession();
  const { request } = useWorkspaceData();
  const [draft, setDraft] = useState<Draft | null>(null);
  const [history, setHistory] = useState<DraftHistory | null>(null);
  const [preview, setPreview] = useState<ExportPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [header, setHeader] = useState<OrderHeader | null>(null);
  const [lines, setLines] = useState<DraftLine[]>([]);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [acknowledgeStale, setAcknowledgeStale] = useState(false);
  const [profiles, setProfiles] = useState<ExportProfile[]>([]);
  const [profileId, setProfileId] = useState<string>("");

  const load = useCallback(async () => {
    try {
      const next = await readDraft(id);
      setDraft(next);
      setHeader(headerOf(next));
      setLines(next.lines.map((l) => ({ ...l })));
      setDirty(false);
      readHistory(id).then(setHistory).catch(() => setHistory(null));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { fetchProfiles().then((p) => setProfiles(p.profiles)).catch(() => setProfiles([])); }, []);
  // Which format an export would use, and why, before the button is pressed (V2 §53).
  useEffect(() => {
    if (!draft) return;
    exportPreview(id, profileId || null).then(setPreview).catch(() => setPreview(null));
  }, [id, profileId, draft]);

  const locations = useMemo(() => (request?.locations ?? []).map((l) => l.id), [request]);

  if (error) {
    return <ErrorState title="That proposal could not be opened"
      affects="Nothing was changed." whatToDo="It may belong to another workspace, or it may have been deleted."
      detail={error} actions={<ButtonLink href="/orders" role="primary">Back to purchase orders</ButtonLink>} />;
  }
  if (!draft || !header) return <Loading label="Reading this proposal…" cards={2} />;

  const editable = draft.editable && session.can("editDraft");
  const currency = header.currency || "USD";
  const canApprove = session.can("approve");
  const canReview = session.can("review");
  const canExport = session.can("export");
  const selfBlocked = session.workspace?.policy.selfApproval === "different_approver"
    && draft.created_by != null && session.actor?.id === draft.created_by;

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
                expected_version: draft.version ?? null,
              } as Parameters<typeof updateDraft>[1]), "save", "Saved.")}>Save changes</Button>
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
            {/* An approval that does not say what it was looking at cannot be reviewed later. */}
            {draft.approval_evaluation_state === "current" && " Approved against a current evaluation."}
            {draft.approval_evaluation_state === "stale_acknowledged" && " Approved knowing the evaluation was out of date."}
            {draft.approval_evaluation_state === "none" && " Approved without asking ZAAD to evaluate it."}
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
            {/* Approve and Reject are disabled until this is written. Two greyed buttons with no
                explanation is a puzzle; one sentence turns it into a rule. */}
            <p className="zhelp" style={{ marginTop: 8 }}>
              {reason.trim()
                ? "This is stored with the decision and shown to whoever reads the order next."
                : "Approving or rejecting needs this sentence first. It is stored with the decision and shown to whoever reads the order next."}
            </p>
            {/* Never silently. The comparison above may describe an earlier version of these
                lines; the approver says they know, and that is written into the record. */}
            {draft.evaluation_stale && (
              <div style={{ marginTop: 10 }}>
                <Notice tone="warn">
                  <strong>The comparison is out of date.</strong> {draft.evaluation_stale_reason}
                  <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
                    <input type="checkbox" checked={acknowledgeStale} onChange={(e) => setAcknowledgeStale(e.target.checked)} />
                    <span>I know the comparison is out of date and want to approve anyway. This is recorded with the approval.</span>
                  </label>
                </Notice>
              </div>
            )}
            <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
              {draft.state === "DRAFT" && canReview && (
                <Button pending={busy === "submit"} onClick={() => act(() => actOnDraft(id, "submit", undefined, { expectedVersion: draft.version ?? null }), "submit", "Sent for review.")}>
                  Send for review
                </Button>
              )}
              {draft.state === "READY_FOR_REVIEW" && canReview && (
                <Button role="tertiary" pending={busy === "reopen"} onClick={() => act(() => actOnDraft(id, "reopen", undefined, { expectedVersion: draft.version ?? null }), "reopen", "Back to draft.")}>
                  Return to draft
                </Button>
              )}
              <Button role="primary" icon={<CheckCircle2 size={15} aria-hidden />} pending={busy === "approve"}
                disabled={!canApprove || selfBlocked || !reason.trim() || (Boolean(draft.evaluation_stale) && !acknowledgeStale)}
                onClick={() => act(() => actOnDraft(id, "approve", reason, { acknowledgeStale, expectedVersion: draft.version ?? null }), "approve", "Approved. Nothing has been sent to a supplier.")}>
                Approve
              </Button>
              <Button role="danger" pending={busy === "reject"} disabled={!canApprove || !reason.trim()}
                onClick={() => act(() => actOnDraft(id, "reject", reason, { expectedVersion: draft.version ?? null }), "reject", "Rejected.")}>
                Reject
              </Button>
            </div>
            {!canApprove && (
              <p className="zhelp" style={{ marginTop: 8 }}>
                Your role ({session.actor?.role.toLowerCase()}) can prepare this proposal but not approve it. An approver decides.
              </p>
            )}
            {canApprove && selfBlocked && (
              <p className="zhelp" style={{ marginTop: 8 }}>
                This workspace requires a different person to approve a proposal than the one who created it.
              </p>
            )}
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
              <option value="">Use the declared default</option>
              {profiles.map((p) => <option key={p.profile_id ?? "built-in"} value={p.profile_id ?? ""}>{p.name}</option>)}
            </select>
          </label>
          <Button icon={<Download size={15} aria-hidden />} pending={busy === "export"}
            disabled={!draft.lines.length || !draft.exportable || !canExport}
            onClick={() => act(async () => {
              const name = await exportDraft(id, { profileId: profileId || null });
              track("po_exported", { draft_id: id });
              toast.push(`${name} downloaded. It has not been sent to anyone.`);
            }, "export", "Exported.")}>
            Export
          </Button>
          <ButtonLink size="sm" role="tertiary" href="/orders/formats">Define a format</ButtonLink>
        </div>
        {preview && (
          <p className="zhelp" style={{ marginTop: 8 }}>
            Will use {preview.detail} · {preview.adapter.real ? "produces a file" : "test adapter"}; {preview.adapter.transmits ? "" : "nothing is sent anywhere"}.
          </p>
        )}
        {!canExport && <p className="zhelp" style={{ marginTop: 8 }}>Your role can read this proposal but not export it.</p>}
        {!draft.lines.length ? (
          <p className="zhelp" style={{ marginTop: 8 }}>
            There is nothing to export until this proposal has a line. Add a product above.
          </p>
        ) : !draft.exportable ? (
          <p className="zhelp" style={{ marginTop: 8 }}>
            {draft.state === "REJECTED" || draft.state === "SUPERSEDED"
              ? "This revision was not approved, so no file is produced from it."
              : "A file is produced once this proposal is approved, so nothing unapproved leaves as a purchase order."}
          </p>
        ) : null}
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

      <ExternalStatusPanel draft={draft} onChanged={load} />
      <OutcomesPanel draft={draft} history={history} onChanged={load} />

      <Section title="History">
        <DataTable caption="What has happened to this proposal" dense rows={history?.events ?? draft.events}
          rowKey={(r, ) => `${r.happened_at}-${r.event}`}
          columns={[
            { key: "event", label: "Event", render: (r) => r.event },
            { key: "happened_at", label: "When", render: (r) => DATE(r.happened_at) },
            { key: "actor", label: "By", render: (r) => r.actor ?? "—" },
            { key: "detail", label: "Detail", render: (r) => r.detail ?? "—" },
          ]} />
        {history && history.revisions.length > 1 && (
          <p className="zhelp" style={{ marginTop: 8 }}>Across {history.revisions.length} revisions of this order.</p>
        )}
        {history && history.audit.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <Disclosure summary="Audit trail" hint={`${history.audit.length} entries · append-only`}>
              <DataTable caption="Every recorded action on this order and its revisions" dense rows={history.audit} rowKey={(r) => r.audit_id}
                columns={[
                  { key: "happened_at", label: "When", render: (r) => DATE(r.happened_at) },
                  { key: "actor", label: "Who", render: (r) => `${r.actor ?? "—"}${r.actor_role ? ` (${r.actor_role.toLowerCase()})` : ""}` },
                  { key: "action", label: "Action", render: (r) => r.action.replaceAll("_", " ") },
                  { key: "state", label: "State", render: (r) => r.before_state || r.after_state ? `${r.before_state ?? "—"} → ${r.after_state ?? "—"}` : "—" },
                  { key: "request_id", label: "Request", render: (r) => <span style={{ fontFamily: "var(--mono)", fontSize: 11.5 }}>{r.request_id ?? "—"}</span> },
                ]} />
            </Disclosure>
          </div>
        )}
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
    <Gate loadingLabel="Opening your workspace…" needsPlan={false} needsWorkspace={false}>
      {id ? <DraftBody id={id} /> : <Loading label="Opening this proposal…" cards={2} />}
    </Gate>
  );
}
