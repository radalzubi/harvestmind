"use client";

import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import {
  Badge,
  Card,
  CardBody,
  CardHead,
  KPI,
  KPIRow,
  PageError,
  PageHeader,
  PageLoading,
  Tbtn,
} from "@/components/ui";
import { getDataQuality, fmt, type DataQualityReport } from "@/lib/api";
import { getPoolStatus, setPoolConsent, type PoolStatus } from "@/lib/api";

export default function DataQualityPage() {
  const [data, setData] = useState<DataQualityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [poolStatus, setPoolStatus] = useState<PoolStatus | null>(null);
  const [showPoolInfo, setShowPoolInfo] = useState(false);
  // Authenticated pilots resolve the operator from the bearer token. The query
  // parameter remains only as a local-development fallback.
  const operatorId = typeof window !== "undefined"
    ? new URLSearchParams(window.location.search).get("operator_id") ?? undefined
    : undefined;

  const togglePoolConsent = async () => {
    if (!poolStatus?.operator) return;
    await setPoolConsent(!poolStatus.operator.pool_consent, operatorId);
    getPoolStatus(operatorId).then(setPoolStatus).catch(() => null);
  };

  const load = () => {
    setLoading(true);
    getDataQuality()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    getPoolStatus(operatorId).then(setPoolStatus).catch(() => setPoolStatus(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Initial load: show full-page states. During re-validate, keep data visible (button shows spinner).
  if (loading && !data) return <PageLoading message="Checking data quality…" />;
  if (error && !data) return <PageError error={error} />;
  if (!data) return null;

  const scoreColor = data.score >= 80 ? "var(--accent)" : data.score >= 60 ? "var(--warn)" : "var(--danger)";
  const readyCount = Object.values(data.tables).filter((t) => t.status === "ready").length;
  const totalTables = Object.keys(data.tables).length;

  return (
    <div className="page">
      <PageHeader
        title="Data Quality"
        sub="Completeness and validity of your uploaded staging data"
        actions={
          <Tbtn
            icon={<RefreshCw size={13} strokeWidth={1.6} />}
            onClick={load}
            pending={loading}
          >
            {loading ? "Checking…" : "Re-validate"}
          </Tbtn>
        }
      />

      <KPIRow>
        <KPI
          label="Quality Score"
          value={data.score.toString()}
          unit="%"
          deltaDir={data.score >= 80 ? "up" : "down"}
          sub={data.score_label}
        />
        <KPI
          label="Tables Ready"
          value={`${readyCount} / ${totalTables}`}
          sub="staging tables with data"
        />
        <KPI
          label="Total Rows"
          value={fmt(data.total_rows)}
          sub="across all staging tables"
        />
        <KPI
          label="Errors"
          value={fmt(data.errors.length)}
          deltaDir={data.errors.length > 0 ? "down" : "flat"}
          sub={`${data.warnings.length} warnings`}
        />
      </KPIRow>

      {/* Re-validate error — only shown when we already have data but the reload failed */}
      {error && data && (
        <div style={{ marginBottom: 16, padding: "10px 14px", border: "1px solid rgba(248,113,113,0.3)", background: "rgba(248,113,113,0.06)", borderRadius: 8, fontSize: 12, color: "var(--danger)" }}>
          Re-validation failed: {error}
        </div>
      )}

      {/* Global errors */}
      {data.errors.length > 0 && (
        <div style={{
          marginTop: 16,
          padding: "12px 16px",
          border: "1px solid rgba(248,113,113,0.3)",
          background: "rgba(248,113,113,0.06)",
          borderRadius: 8,
        }}>
          {data.errors.map((e, i) => (
            <div key={i} style={{ fontSize: 12, color: "var(--danger)", marginBottom: 4 }}>⚠ {e}</div>
          ))}
        </div>
      )}

      {/* Per-table status */}
      <Card style={{ marginTop: 16 }}>
        <CardHead title="Staging Tables" sub="Row counts and validation results per table" />
        <CardBody tight>
          <table className="data-table">
            <thead>
              <tr>
                <th>Table</th>
                <th className="r">Rows</th>
                <th>Status</th>
                <th>Issues</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.tables).map(([table, info]) => (
                <tr key={table}>
                  <td style={{ fontFamily: "monospace", fontSize: 11 }}>{table}</td>
                  <td className="r">{fmt(info.row_count)}</td>
                  <td>
                    {info.status === "ready" ? (
                      <Badge kind="low">Ready</Badge>
                    ) : info.status === "empty" ? (
                      <Badge kind="neutral">Empty</Badge>
                    ) : info.status === "warnings" ? (
                      <Badge kind="medium">Warnings</Badge>
                    ) : (
                      <Badge kind="high">Errors</Badge>
                    )}
                  </td>
                  <td style={{ fontSize: 11, color: "var(--muted)", maxWidth: 400 }}>
                    {info.issues.length === 0
                      ? <span style={{ color: "var(--accent)" }}>✓ No issues</span>
                      : info.issues.map((issue, i) => (
                          <div key={i} style={{ marginBottom: 2, color: info.status === "errors" ? "var(--danger)" : "var(--warn)" }}>
                            {issue}
                          </div>
                        ))
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>

      {/* Warnings */}
      {data.warnings.length > 0 && (
        <Card style={{ marginTop: 16 }}>
          <CardHead title="Warnings" sub="Non-blocking data quality issues" />
          <CardBody tight>
            <div style={{ padding: "8px 12px" }}>
              {data.warnings.map((w, i) => (
                <div key={i} style={{ fontSize: 12, color: "var(--warn)", marginBottom: 6, display: "flex", gap: 8, alignItems: "flex-start" }}>
                  <span style={{ flex: "none", marginTop: 1 }}>⚠</span>
                  <span>{w}</span>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Data pool indicator — anonymized, consent-gated */}
      {poolStatus && (
        <Card style={{ marginTop: 16 }}>
          <CardHead
            title="Data Pool"
            sub="Anonymized cross-operator signals that make every forecast smarter — categories and ratios only, never names, volumes, or prices"
          />
          <CardBody>
            <div style={{ display: "flex", gap: 18, alignItems: "center", flexWrap: "wrap", fontSize: 12 }}>
              <span>
                <b>{poolStatus.pool.n_operators_contributing}</b> operators contributing ·{" "}
                <b>{poolStatus.pool.n_signals}</b> signals
              </span>
              {poolStatus.operator && (
                <>
                  <span style={{ color: poolStatus.operator.pool_consent ? "var(--accent)" : "var(--muted)", fontWeight: 600 }}>
                    {poolStatus.operator.pool_consent ? "Contributing" : "Not contributing"}
                  </span>
                  <Tbtn onClick={togglePoolConsent}>
                    {poolStatus.operator.pool_consent ? "Stop contributing" : "Start contributing"}
                  </Tbtn>
                </>
              )}
              <button
                onClick={() => setShowPoolInfo(!showPoolInfo)}
                style={{ background: "none", border: "none", color: "var(--accent)", fontSize: 12, cursor: "pointer", textDecoration: "underline", padding: 0 }}
              >
                Your data is anonymized — see what we use
              </button>
            </div>
            {showPoolInfo && (
              <div style={{ marginTop: 12, fontSize: 11, color: "var(--muted)", lineHeight: 1.6 }}>
                The pool receives only category-level statistical signals: demand variability
                (with volumes normalized so your size is invisible), supplier fill-rate
                distributions (ratios, at least 10 deliveries behind every number), and waste
                rates with bucketed reasons. It never receives company names, buyer or supplier
                names, product names, prices, volumes, or anything below region level. If you
                stop contributing, future contributions end immediately; signals already
                pooled cannot be traced back to you and remain. Full explanation:
                docs/POOL_PRIVACY.md.
              </div>
            )}
          </CardBody>
        </Card>
      )}

      <style>{`.r { text-align: right; } .data-table { width: 100%; border-collapse: collapse; } .data-table th { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: 8px 12px; text-align: left; } .data-table td { padding: 8px 12px; border-top: 1px solid var(--border); font-size: 12px; } .data-table tr:hover td { background: rgba(255,255,255,.02); }`}</style>
    </div>
  );
}
