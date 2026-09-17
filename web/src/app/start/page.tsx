"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle, Circle, Play } from "lucide-react";
import { Card, CardBody, CardHead, InfoBanner, PageHeader, Tbtn } from "@/components/ui";
import { apiFetch, cancelJob, downloadReport, familyOf, getApiToken, getJob, getMe, latestJob, setSector, startDiagnostic, type IntakeStatus, type Me } from "@/lib/api";
import { DiagnosticPoller, isTerminal, type PollerState } from "@/lib/diagnostic/lifecycle";
import { DiagnosticRun } from "@/components/diagnostic/DiagnosticRun";
import { DiagnosticReportView } from "@/components/diagnostic/DiagnosticReport";
import { useToast } from "@/components/Toast";

const SECTOR_LABEL: Record<string, string> = { commercial: "Commercial goods", produce: "Fresh produce", meats: "Meat and seafood" };

const FILES: Record<"commercial" | "produce", Array<{ table: string; label: string }>> = {
  commercial: [
    { table: "stg_fmcg_skus", label: "Product list" },
    { table: "stg_fmcg_orders", label: "Sales (customer orders)" },
    { table: "stg_fmcg_purchase_orders", label: "Purchase orders" },
    { table: "stg_fmcg_receipts", label: "Goods received" },
    { table: "stg_fmcg_inventory", label: "Stock counts" },
    { table: "stg_fmcg_suppliers", label: "Supplier list (optional)" },
  ],
  produce: [
    { table: "stg_products", label: "Products" },
    { table: "stg_supplier_deliveries", label: "Supplier deliveries" },
    { table: "stg_inventory_lots", label: "Inventory lots" },
    { table: "stg_buyer_orders", label: "Buyer orders" },
    { table: "stg_waste_adjustments", label: "Waste log (optional)" },
  ],
};

/** The poller with browser timers. One per mounted page; it reconnects to the newest job first. */
function usePoller(enabled: boolean) {
  const [state, setState] = useState<PollerState>({ job: null, connectionLost: false, starting: false });
  const ref = useRef<DiagnosticPoller | null>(null);
  useEffect(() => {
    if (!enabled) return;
    const p = new DiagnosticPoller({
      fetchJob: getJob, start: startDiagnostic, latest: latestJob, cancel: cancelJob,
      setTimer: (fn, ms) => window.setTimeout(fn, ms), clearTimer: (h) => window.clearTimeout(h as number),
    }, setState);
    ref.current = p;
    void p.reconnect();
    return () => { p.stop(); ref.current = null; };
  }, [enabled]);
  return { state, poller: ref };
}

function StartInner() {
  const toast = useToast();
  const params = useSearchParams();
  const isNew = params.get("new") === "1";
  const [copied, setCopied] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const [status, setStatus] = useState<IntakeStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const { state, poller } = usePoller(!!me);
  const job = state.job;
  const lastStatus = useRef<string | null>(null);

  useEffect(() => {
    if (!getApiToken()) { setError("no-token"); return; }
    getMe().then((m) => { setMe(m); setSector(m.sector); }).catch((e) => setError(e.message));
    apiFetch<IntakeStatus>("/intake/status").then(setStatus).catch(() => {});
  }, []);

  // one toast per transition into a terminal state
  useEffect(() => {
    const s = job?.status ?? null;
    if (s && s !== lastStatus.current && isTerminal(s) && lastStatus.current != null) {
      toast.push(s === "done" ? "Diagnostic ready" : s === "cancelled" ? "Diagnostic cancelled" : `Diagnostic ${s === "timed_out" ? "timed out" : "failed"} (reference ${job?.reference ?? job?.id})`);
    }
    lastStatus.current = s;
  }, [job?.status, job?.reference, job?.id, toast]);

  const run = useCallback(async () => {
    try { await poller.current?.start(); }
    catch (e) { toast.push(`Could not start: ${e instanceof Error ? e.message : String(e)}`); }
  }, [poller, toast]);

  const cancel = useCallback(async () => {
    setCancelling(true);
    try { await poller.current?.cancel(); }
    catch (e) { toast.push(`Could not cancel: ${e instanceof Error ? e.message : String(e)}`); }
    finally { setCancelling(false); }
  }, [poller, toast]);

  const download = useCallback(async () => {
    if (!job) return;
    setDownloading(true);
    try { await downloadReport(job.id); }
    catch (e) { toast.push(`Download failed: ${e instanceof Error ? e.message : String(e)}`); }
    finally { setDownloading(false); }
  }, [job, toast]);

  if (error === "no-token") {
    return (
      <div className="page">
        <PageHeader title="Start" sub="Connect your workspace first" />
        <InfoBanner kind="info" title="No workspace connected">
          Open the access link from your approval email, or enter your token on the <Link href="/access">access page</Link>.
        </InfoBanner>
      </div>
    );
  }
  if (error) return <div className="page"><InfoBanner kind="warn" title="Could not load your workspace">{error}</InfoBanner></div>;
  if (!me) return <div className="page">Loading…</div>;

  const files = FILES[familyOf(me.sector)];
  const tables = status?.tables ?? {};
  const rows = (t: string) => tables[t]?.row_count ?? 0;
  const uploaded = files.filter((f) => rows(f.table) > 0).length;
  const requiredDone = files.filter((f) => !f.label.includes("optional")).every((f) => rows(f.table) > 0);
  // the first run button; a finished run shows "Run again" beside its result, a failed, timed-out
  // or cancelled run shows its own retry inside the terminal state
  const showButton = job == null;

  return (
    <div className="page">
      <PageHeader title={`${me.name}`} sub={`${SECTOR_LABEL[me.sector] ?? "Your"} workspace · ${me.region}`} />
      {isNew && (
        <InfoBanner kind="warn" title="Save your workspace key now">
          This key is the only way back into this workspace and it is shown once. It is not stored anywhere but your browser session.
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
            <code style={{ fontFamily: "var(--mono)", fontSize: 12, background: "var(--surface)", padding: "6px 8px", borderRadius: 6, border: "1px solid var(--line)", wordBreak: "break-all" }}>{getApiToken()}</code>
            <Tbtn onClick={() => { navigator.clipboard.writeText(getApiToken() ?? "").then(() => setCopied(true)).catch(() => {}); }}>{copied ? "Copied" : "Copy"}</Tbtn>
          </div>
        </InfoBanner>
      )}
      <InfoBanner kind="info" title="Your files stay yours">
        Identifiers are pseudonymised the moment a file arrives and your vault is isolated from every other workspace.
        There is no administrator screen that shows your data.
      </InfoBanner>

      <Card style={{ marginTop: 16 }}>
        <CardHead title="1. Upload your exports" sub={`${uploaded} of ${files.length} files present. Twelve to twenty-four months of history; twenty-four is best.`} />
        <CardBody>
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 8 }}>
            {files.map((f) => {
              const n = rows(f.table);
              return (
                <li key={f.table} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  {n > 0 ? <CheckCircle size={16} color="var(--good)" /> : <Circle size={16} color="var(--ink-300)" />}
                  <span style={{ flex: 1 }}>{f.label}</span>
                  <span style={{ color: "var(--ink-500)", fontVariantNumeric: "tabular-nums" }}>{n > 0 ? `${n.toLocaleString()} rows` : "not yet"}</span>
                </li>
              );
            })}
          </ul>
          <div style={{ marginTop: 14 }}>
            <Link href="/upload"><Tbtn variant="primary">Upload files</Tbtn></Link>
          </div>
        </CardBody>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <CardHead title="2. Run the diagnostic" sub="How you order today as read from your history, alternative policies tested on that same history with a conservative estimate, and your supply lanes. A few minutes; you can leave this page and come back." />
        <CardBody>
          {showButton && (
            <Tbtn variant="primary" icon={<Play size={13} />} onClick={run} disabled={!requiredDone} pending={state.starting}>
              {requiredDone ? (job ? "Run the diagnostic again" : "Run diagnostic") : "Upload the required files first"}
            </Tbtn>
          )}
          <DiagnosticRun job={job} connectionLost={state.connectionLost} onCancel={cancel} onRetry={run} cancelling={cancelling} />
          {job?.status === "done" && (
            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 12 }}>
              <span style={{ color: "var(--ink-600)", fontSize: 13 }}>Diagnostic ready{job.timing?.run_s != null ? ` in ${Math.round(job.timing.run_s)} s` : ""}. Your result is below.</span>
              <Tbtn variant="ghost" icon={<Play size={13} />} onClick={run} disabled={!requiredDone} pending={state.starting}>Run again</Tbtn>
            </div>
          )}
        </CardBody>
      </Card>

      {job?.status === "done" && job.report && (
        <Card style={{ marginTop: 16 }}>
          <CardHead title="3. Your result" sub={`Purchasing diagnostic for ${job.report.company}`} />
          <CardBody>
            <DiagnosticReportView report={job.report} onDownload={download} downloading={downloading} />
          </CardBody>
        </Card>
      )}
      {job?.status === "done" && !job.report && (
        <Card style={{ marginTop: 16 }}>
          <CardHead title="3. Your result" sub={String(job.summary?.reason ?? "")} />
          <CardBody>
            <p style={{ margin: "0 0 10px" }}>The structured report could not be built for this run; the PDF is still available.</p>
            <Tbtn variant="primary" onClick={download} pending={downloading}>Download the report (PDF)</Tbtn>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

export default function StartPage() {
  return <Suspense fallback={null}><StartInner /></Suspense>;
}
