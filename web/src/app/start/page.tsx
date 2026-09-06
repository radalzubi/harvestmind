"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle, Circle, Download, Loader2, Play } from "lucide-react";
import { Card, CardBody, CardHead, InfoBanner, PageHeader, Tbtn } from "@/components/ui";
import { apiFetch, downloadReport, familyOf, getApiToken, getJob, getMe, setSector, startDiagnostic, type IntakeStatus, type Job, type Me } from "@/lib/api";

const SECTOR_LABEL: Record<string, string> = { commercial: "Commercial goods", produce: "Fresh produce", meats: "Meat and seafood" };
import { useToast } from "@/components/Toast";


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

function StartInner() {
  const toast = useToast();
  const params = useSearchParams();
  const isNew = params.get("new") === "1";
  const [copied, setCopied] = useState(false);
  const [me, setMe] = useState<Me | null>(null);
  const [status, setStatus] = useState<IntakeStatus | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!getApiToken()) { setError("no-token"); return; }
    getMe().then((m) => { setMe(m); setSector(m.sector); }).catch((e) => setError(e.message));
    apiFetch<IntakeStatus>("/intake/status").then(setStatus).catch(() => {});
    return () => { if (timer.current) window.clearInterval(timer.current); };
  }, []);

  const poll = (id: string) => {
    if (timer.current) window.clearInterval(timer.current);
    timer.current = window.setInterval(async () => {
      try {
        const j = await getJob(id);
        setJob(j);
        if (j.status === "done" || j.status === "failed") {
          if (timer.current) window.clearInterval(timer.current);
          toast.push(j.status === "done" ? "Diagnostic ready" : `Diagnostic failed: ${j.error ?? ""}`);
        }
      } catch { /* keep polling */ }
    }, 3000);
  };

  const run = async () => {
    try {
      const j = await startDiagnostic();
      setJob(j);
      poll(j.id);
    } catch (e) {
      toast.push(`Could not start: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

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
  const uploadHref = "/upload";
  const running = job && (job.status === "queued" || job.status === "running");
  const summary = (job?.summary ?? null) as Record<string, unknown> | null;
  const improvement = summary?.improvement as { mean?: number; lower_bound?: number; worst?: number; n_folds?: number } | null | undefined;

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
            <Link href={uploadHref}><Tbtn variant="primary">Upload files</Tbtn></Link>
          </div>
        </CardBody>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <CardHead title="2. Run the diagnostic" sub="Your current policy as read from your history, a backtested comparison with a conservative lower bound, and your lane risk today. A few minutes." />
        <CardBody>
          {!running && (
            <Tbtn variant="primary" icon={<Play size={13} />} onClick={run} disabled={!requiredDone}>
              {requiredDone ? "Run diagnostic" : "Upload the required files first"}
            </Tbtn>
          )}
          {running && (
            <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--ink-600)" }}>
              <Loader2 size={16} className="spin" /> {job?.progress}
            </div>
          )}
          {job?.status === "failed" && <p style={{ color: "var(--bad)" }} role="alert">{job.error}</p>}
        </CardBody>
      </Card>

      {job?.status === "done" && summary && (
        <Card style={{ marginTop: 16 }}>
          <CardHead title="3. Your result" sub={String(summary.reason ?? "")} />
          <CardBody>
            <p style={{ margin: "0 0 10px" }}>Decision: <b>{String(summary.decision)}</b></p>
            {improvement && (
              <p style={{ margin: "0 0 10px", color: "var(--ink-700)" }}>
                Cost change versus your own policy on your own history: mean {fmtPct(improvement.mean)}, conservative lower bound {fmtPct(improvement.lower_bound)}, worst fold {fmtPct(improvement.worst)} over {improvement.n_folds} folds. Positive is a reduction.
              </p>
            )}
            {!improvement && <p style={{ margin: "0 0 10px", color: "var(--ink-700)" }}>No candidate was evidenced against your policy; your current ordering was retained. That is a valid result.</p>}
            <Tbtn variant="primary" icon={<Download size={13} />} onClick={() => downloadReport(job.id).catch((e) => toast.push(String(e)))}>
              Download the report (PDF)
            </Tbtn>
          </CardBody>
        </Card>
      )}
    </div>
  );
}

function fmtPct(x?: number | null): string {
  return x == null ? "n/a" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(1)}%`;
}

export default function StartPage() {
  return <Suspense fallback={null}><StartInner /></Suspense>;
}
