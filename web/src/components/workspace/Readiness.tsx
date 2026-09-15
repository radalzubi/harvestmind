"use client";

/**
 * What ZAAD can do with this workspace's data, per capability, and the field that decides it.
 *
 * V1 knew that a source was uploaded. This reads the server's counted answer: which fields are
 * there, how complete, and therefore which capability is Ready, Partial, Blocked (a field the
 * upload could carry is missing) or Not in the upload (nothing the canonical upload carries could
 * ever answer it). Every row names the source and column, so the path back is always "upload
 * that column".
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { DataTable } from "@/components/workspace/Table";
import { Notice } from "@/components/workspace/ui";
import { CAPABILITY_STATUS_LABEL, fetchReadiness, track, type CapabilityReadiness, type QualityCheck, type WorkspaceReadiness } from "@/lib/zaad/product";
import { useSession } from "@/lib/session";

export function useCapabilityReadiness(): { readiness: WorkspaceReadiness | null; error: string | null; refresh: () => void } {
  const session = useSession();
  const [readiness, setReadiness] = useState<WorkspaceReadiness | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (session.status !== "authenticated") return;
    let alive = true;
    fetchReadiness().then((r) => { if (alive) { setReadiness(r.applies === false ? null : r); setError(null); track("data_readiness_opened", { surface: window.location.pathname.slice(1, 40) }); } })
      .catch((e) => { if (alive) setError(e instanceof Error ? e.message : String(e)); });
    return () => { alive = false; };
  }, [session.status, tick]);
  return { readiness, error, refresh: () => setTick((t) => t + 1) };
}

const TONE: Record<CapabilityReadiness["status"], "good" | "warn" | "bad" | undefined> = {
  READY: "good", PARTIAL: "warn", BLOCKED: "bad", UNAVAILABLE: undefined,
};

const SOURCE_LABEL: Record<string, string> = {
  products: "product list", customer_orders: "customer orders", purchase_orders: "purchase orders",
  receipts: "goods received", inventory: "stock counts", suppliers: "supplier list", locations: "sites",
  lanes: "transfer lanes", sources: "alternative sources", po_options: "order amendment rights",
  customer_order_promises: "customer commitments", proposals: "proposals",
};

export function CapabilityMatrix({ rows }: { rows: CapabilityReadiness[] }) {
  return (
    <DataTable caption="What ZAAD can do with this data" dense rows={rows} rowKey={(r) => r.capability}
      columns={[
        { key: "label", label: "Capability", render: (r) => <span style={{ fontWeight: 500, color: "var(--ink-950)" }}>{r.label}</span> },
        { key: "status", label: "Status", render: (r) => <span className="chip" data-tone={TONE[r.status]}>{CAPABILITY_STATUS_LABEL[r.status]}</span> },
        { key: "reason", label: "Why", render: (r) => r.reason },
        { key: "column", label: "Decided by", hideBelow: 900, render: (r) => r.column
          ? <><code style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{r.column}</code>{r.source ? <span style={{ color: "var(--ink-500)" }}> in {SOURCE_LABEL[r.source] ?? r.source}</span> : null}</>
          : r.source ? <span style={{ color: "var(--ink-500)" }}>{SOURCE_LABEL[r.source] ?? r.source}</span> : <span className="na">—</span> },
      ]} />
  );
}

const SEVERITY_LABEL: Record<QualityCheck["severity"], string> = {
  BLOCKING: "Blocks planning", MATERIAL: "Changes the plan", INFORMATIONAL: "Noted",
};

export function QualityChecks({ rows }: { rows: QualityCheck[] }) {
  if (!rows.length) return <Notice>No duplicate, orphan, negative or impossible value was found in the sources ZAAD reads.</Notice>;
  return (
    <DataTable caption="Quality checks counted from your data" dense rows={rows} rowKey={(r) => r.check}
      columns={[
        { key: "count", label: "Rows", numeric: true, render: (r) => r.count.toLocaleString("en-US") },
        { key: "message", label: "What", render: (r) => r.message },
        { key: "severity", label: "Effect", render: (r) => <span className="chip" data-tone={r.severity === "BLOCKING" ? "bad" : r.severity === "MATERIAL" ? "warn" : undefined}>{SEVERITY_LABEL[r.severity]}</span> },
        { key: "source", label: "In", hideBelow: 700, render: (r) => <>{SOURCE_LABEL[r.source] ?? r.source}{r.column ? <> · <code style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{r.column}</code></> : null}</> },
      ]} />
  );
}

/** One sentence for Home: how much of ZAAD this data unlocks, and the first thing blocking the rest. */
export function ReadinessLine({ readiness }: { readiness: WorkspaceReadiness }) {
  const s = readiness.summary;
  const blocked = readiness.capabilities.filter((c) => c.status === "BLOCKED");
  const total = s.ready + s.partial + s.blocked;
  return (
    <p style={{ margin: 0 }}>
      Your data makes {s.ready} of {total} things ZAAD can do fully available{s.partial ? `, ${s.partial} partly` : ""}{s.blocked ? `, ${s.blocked} not yet` : ""}.
      {blocked.length > 0 && <> First gap: {blocked[0].label.toLowerCase()} — {blocked[0].reason}</>}
      {" "}<Link href="/upload">See what each needs</Link>.
    </p>
  );
}
