"use client";

import { useMemo, useState } from "react";
import { Check, ChevronRight, RefreshCw, Undo2 } from "lucide-react";
import {
  Badge,
  Card,
  CardBody,
  KPI,
  KPIRow,
  PageHeader,
  RiskBadge,
  Tabs,
  Tbtn,
} from "@/components/ui";
import { useToast } from "@/components/Toast";
import { RECS, fmt } from "@/lib/data";
import { downloadCSV, toCSV } from "@/lib/csv";

type Tab = "review" | "auto" | "all";
type Decision = "approved" | "overridden" | "snoozed";

export default function RecsPage() {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("review");
  const [open, setOpen] = useState<string | null>(RECS[1].sku);
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [pendingRerun, setPendingRerun] = useState(false);

  const filtered = useMemo(() => {
    if (tab === "review") {
      return RECS.filter(
        (r) => r.status === "Needs review" && !decisions[r.sku],
      );
    }
    if (tab === "auto") return RECS.filter((r) => r.status === "Auto-approved");
    return RECS;
  }, [tab, decisions]);

  const reviewCount = RECS.filter(
    (r) => r.status === "Needs review" && !decisions[r.sku],
  ).length;
  const autoCount = RECS.filter((r) => r.status === "Auto-approved").length;
  const decidedCount = Object.keys(decisions).length;

  const setDecision = (sku: string, d: Decision, label: string) => {
    setDecisions((prev) => ({ ...prev, [sku]: d }));
    toast.push(`${label}: ${RECS.find((r) => r.sku === sku)?.product}`);
    setOpen(null);
  };

  const undoDecision = (sku: string) => {
    setDecisions((prev) => {
      const next = { ...prev };
      delete next[sku];
      return next;
    });
  };

  const onApproveAll = () => {
    const pending = RECS.filter(
      (r) => r.status === "Needs review" && !decisions[r.sku],
    );
    if (pending.length === 0) {
      toast.push("Nothing to approve", "info");
      return;
    }
    const next: Record<string, Decision> = { ...decisions };
    pending.forEach((r) => (next[r.sku] = "approved"));
    setDecisions(next);
    toast.push(`Approved ${pending.length} recommendations`);
  };

  const onRerun = async () => {
    setPendingRerun(true);
    await new Promise((r) => setTimeout(r, 1100));
    setPendingRerun(false);
    toast.push("Re-ran planner — no new recommendations");
  };

  const onExportCSV = () => {
    const rows = RECS.map((r) => ({
      sku: r.sku,
      product: r.product,
      recommend_kg: r.commit,
      last_week_kg: r.hist,
      forecast_kg: r.fcst,
      spot_share: (r.spot * 100).toFixed(1) + "%",
      shortage_risk: r.short,
      waste_risk: r.waste,
      status: r.status,
      decision: decisions[r.sku] ?? "",
    }));
    const csv = toCSV(rows, [
      { key: "sku", label: "SKU" },
      { key: "product", label: "Product" },
      { key: "recommend_kg", label: "Recommend (kg)" },
      { key: "last_week_kg", label: "Last week (kg)" },
      { key: "forecast_kg", label: "Forecast (kg)" },
      { key: "spot_share", label: "Spot share" },
      { key: "shortage_risk", label: "Shortage risk" },
      { key: "waste_risk", label: "Waste risk" },
      { key: "status", label: "Status" },
      { key: "decision", label: "Decision" },
    ]);
    downloadCSV("recommendations.csv", csv);
  };

  return (
    <div className="page">
      <PageHeader
        title="Recommendations"
        sub="Week of May 4 — review and approve this week's plan"
        actions={
          <>
            <Tbtn onClick={onExportCSV}>Export CSV</Tbtn>
            <Tbtn
              icon={<RefreshCw size={13} strokeWidth={1.6} />}
              onClick={onRerun}
              pending={pendingRerun}
            >
              Re-run
            </Tbtn>
            <Tbtn
              variant="primary"
              icon={<Check size={13} strokeWidth={1.8} />}
              onClick={onApproveAll}
            >
              Approve all
            </Tbtn>
          </>
        }
      />

      <KPIRow cols={3}>
        <KPI label="Total SKUs" value="12" sub="in this week's plan" />
        <KPI
          label="Need review"
          value={String(reviewCount)}
          sub={
            decidedCount > 0
              ? `${decidedCount} decided this session`
              : "action required"
          }
        />
        <KPI label="At risk" value="$24.8K" sub="if no overrides applied" />
      </KPIRow>

      <Tabs<Tab>
        value={tab}
        onChange={setTab}
        tabs={[
          { id: "review", label: "Needs review", count: reviewCount },
          { id: "auto", label: "Auto-approved", count: autoCount },
          { id: "all", label: "All", count: RECS.length },
        ]}
      />

      <Card>
        <CardBody tight>
          <div className="table-wrap">
            <table className="t">
              <thead>
                <tr>
                  <th style={{ width: 28 }}></th>
                  <th>Product</th>
                  <th className="num">Recommend</th>
                  <th className="num">Last week</th>
                  <th className="num">Spot</th>
                  <th>Risk</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => {
                  const isOpen = open === r.sku;
                  const risk =
                    ["Critical", "High"].includes(r.short)
                      ? r.short
                      : ["Critical", "High"].includes(r.waste)
                      ? r.waste
                      : "Low";
                  const decision = decisions[r.sku];
                  return (
                    <FragmentRow
                      key={r.sku}
                      sku={r.sku}
                      product={r.product}
                      commit={r.commit}
                      hist={r.hist}
                      spot={r.spot}
                      status={r.status}
                      why={r.why}
                      risk={risk}
                      isOpen={isOpen}
                      decision={decision}
                      onToggle={() => setOpen(isOpen ? null : r.sku)}
                      onApprove={() => setDecision(r.sku, "approved", "Approved")}
                      onOverride={() =>
                        setDecision(r.sku, "overridden", "Overridden")
                      }
                      onSnooze={() => setDecision(r.sku, "snoozed", "Snoozed 1 week")}
                      onUndo={() => undoDecision(r.sku)}
                    />
                  );
                })}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ padding: "32px 18px", textAlign: "center", color: "var(--ink-500)" }}>
                      All caught up. No recommendations need review.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

function FragmentRow({
  sku,
  product,
  commit,
  hist,
  spot,
  status,
  why,
  risk,
  isOpen,
  decision,
  onToggle,
  onApprove,
  onOverride,
  onSnooze,
  onUndo,
}: {
  sku: string;
  product: string;
  commit: number;
  hist: number;
  spot: number;
  status: "Auto-approved" | "Needs review";
  why: string;
  risk: string;
  isOpen: boolean;
  decision?: Decision;
  onToggle: () => void;
  onApprove: () => void;
  onOverride: () => void;
  onSnooze: () => void;
  onUndo: () => void;
}) {
  const decisionLabel: Record<Decision, { label: string; kind: "low" | "medium" | "neutral" }> = {
    approved: { label: "Approved", kind: "low" },
    overridden: { label: "Overridden", kind: "medium" },
    snoozed: { label: "Snoozed", kind: "neutral" },
  };

  return (
    <>
      <tr style={{ cursor: "pointer" }} onClick={onToggle}>
        <td style={{ paddingLeft: 18, paddingRight: 0 }}>
          <ChevronRight
            size={12}
            color="var(--ink-400)"
            strokeWidth={1.6}
            style={{ transform: isOpen ? "rotate(90deg)" : "none", transition: "transform 0.1s" }}
          />
        </td>
        <td className="product">
          {product}
          <span style={{ color: "var(--ink-400)", fontSize: 12, marginLeft: 6 }}>{sku}</span>
        </td>
        <td className="num strong">{fmt.kg(commit)}</td>
        <td className="num muted">{fmt.kg(hist)}</td>
        <td className="num">
          <span style={{ color: spot > 0.15 ? "var(--bad)" : "var(--ink-700)" }}>
            {fmt.pct(spot, 0)}
          </span>
        </td>
        <td>
          <RiskBadge level={risk} />
        </td>
        <td style={{ textAlign: "right", paddingRight: 18 }}>
          {decision ? (
            <Badge kind={decisionLabel[decision].kind}>{decisionLabel[decision].label}</Badge>
          ) : status === "Auto-approved" ? (
            <Badge kind="neutral">Auto</Badge>
          ) : (
            <Badge kind="medium">Review</Badge>
          )}
        </td>
      </tr>
      {isOpen && (
        <tr>
          <td
            colSpan={7}
            style={{
              background: "var(--surface-2)",
              padding: "18px 24px 22px 50px",
              borderBottom: "1px solid var(--line-soft)",
            }}
          >
            <div
              style={{
                fontSize: 13.5,
                color: "var(--ink-700)",
                lineHeight: 1.6,
                maxWidth: 720,
                marginBottom: 14,
              }}
            >
              {why}
            </div>
            <div className="row" style={{ gap: 8 }}>
              {decision ? (
                <Tbtn icon={<Undo2 size={12} strokeWidth={1.6} />} onClick={onUndo}>
                  Undo
                </Tbtn>
              ) : (
                <>
                  <Tbtn variant="primary" icon={<Check size={12} strokeWidth={1.8} />} onClick={onApprove}>
                    Approve
                  </Tbtn>
                  <Tbtn onClick={onOverride}>Override</Tbtn>
                  <Tbtn onClick={onSnooze}>Snooze 1 week</Tbtn>
                </>
              )}
              <div style={{ flex: 1 }} />
              <span className="small muted">
                Forecast confidence: 88% · stockout p: 3.1%
              </span>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
