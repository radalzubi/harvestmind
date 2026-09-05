"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import Link from "next/link";
import { Check, Download, Pencil } from "lucide-react";
import {
  Card,
  CardBody,
  CardHead,
  EmptyState,
  InfoBanner,
  PageError,
  PageHeader,
  PageLoading,
  Tbtn,
} from "@/components/ui";
import { useToast } from "@/components/Toast";
import {
  confirmExtraction,
  getExtractionSession,
  type ExtractionResultPayload,
  type ExtractionRow,
} from "@/lib/api";

const TARGET_FIELDS: Record<string, string[]> = {
  stg_products: ["product_id", "product_name", "category", "unit",
    "default_shelf_life_days", "traceability_required"],
  stg_supplier_deliveries: ["delivery_id", "supplier_id", "supplier_name",
    "product_id", "product_name", "delivery_date", "ordered_quantity",
    "delivered_quantity", "accepted_quantity", "rejected_quantity",
    "unit_cost", "quality_grade", "lot_id"],
  stg_inventory_lots: ["lot_id", "product_id", "product_name", "supplier_id",
    "quantity_on_hand", "unit", "arrival_date", "expiration_date",
    "warehouse_location", "quality_grade", "committed_quantity"],
  stg_buyer_orders: ["order_id", "buyer_id", "buyer_name", "product_id",
    "product_name", "order_date", "delivery_date", "requested_quantity",
    "fulfilled_quantity", "substituted_quantity", "sales_price",
    "required_quality_grade"],
  stg_fmcg_skus: ["sku", "sku_name", "category", "supplier_id", "unit_cost", "unit_price", "units_per_case", "moq_units", "shelf_life_days", "abc_class"],
  stg_fmcg_orders: ["order_id", "customer_id", "order_date", "requested_delivery_date", "sku", "qty_ordered", "qty_shipped", "channel"],
  stg_fmcg_purchase_orders: ["po_id", "po_date", "supplier_id", "sku", "qty_ordered", "unit_cost", "expected_delivery_date"],
  stg_fmcg_receipts: ["receipt_id", "po_id", "receipt_date", "sku", "qty_received", "qty_rejected"],
  stg_fmcg_inventory: ["snapshot_date", "sku", "location_id", "on_hand", "in_transit"],
  stg_fmcg_suppliers: ["supplier_id", "supplier_name", "route", "origin_iso3", "lead_time_promised_weeks", "capacity_per_week"],
  stg_waste_adjustments: ["adjustment_id", "date", "product_id",
    "product_name", "lot_id", "quantity_lost", "reason",
    "estimated_value_lost"],
};

const FIELD_HELP: Record<string, string> = {
  ordered_quantity: "How much you ordered from the supplier",
  delivered_quantity: "How much the supplier actually delivered",
  accepted_quantity: "How much you accepted after inspection",
  rejected_quantity: "How much you rejected at delivery",
  requested_quantity: "How much the buyer asked for",
  fulfilled_quantity: "How much you actually delivered to the buyer",
  substituted_quantity: "Quantity covered with a substitute product",
  unit_cost: "What YOU paid the supplier per unit",
  sales_price: "What the BUYER paid you per unit",
  quantity_on_hand: "Current stock for this lot",
  committed_quantity: "Stock already promised to buyers",
  expiration_date: "When the lot expires (FSMA-critical)",
  arrival_date: "When the lot arrived (FSMA-critical)",
  lot_id: "Lot/batch identifier (FSMA-critical)",
  quantity_lost: "How much was wasted or written off",
  estimated_value_lost: "Dollar value of the waste",
};

function confBadge(c: number) {
  const color = c >= 0.9 ? "var(--accent)" : c >= 0.7 ? "var(--warn)" : "var(--danger)";
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, color, border: `1px solid ${color}`,
      borderRadius: 4, padding: "1px 5px", marginLeft: 6,
    }}>
      {(c * 100).toFixed(0)}%
    </span>
  );
}

function ConfirmInner() {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const sessionId = params.get("session") ?? "";

  const [session, setSession] = useState<ExtractionResultPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<ExtractionRow[]>([]);
  const [actioned, setActioned] = useState<Set<number>>(new Set());
  const [excluded, setExcluded] = useState<Set<number>>(new Set());
  const [corrections, setCorrections] = useState<Array<Record<string, unknown>>>([]);
  const [editing, setEditing] = useState<{ row: number; field: string } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!sessionId) { setLoading(false); return; }
    getExtractionSession(sessionId)
      .then((s) => { setSession(s); setRows(s.extracted_rows.filter((r) => !r.rejected)); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sessionId]);

  const flagged = useMemo(() => rows.filter((r) => r.requires_confirmation), [rows]);
  const unactioned = flagged.filter((r) => !actioned.has(r.row_index));
  const bulkAcceptable = useMemo(
    () => flagged.filter((r) =>
      Object.values(r.field_metadata).every((m) => m.confidence >= 0.9)),
    [flagged]
  );

  if (!sessionId) return <PageError error="No session id, start from the Upload page." />;
  if (loading) return <PageLoading message="Loading extraction session…" />;
  if (error) return <PageError error={error} />;
  if (!session) return null;

  if (session.status === "rejected") {
    return (
      <div className="page">
        <PageHeader title="Extraction Rejected" sub="The file could not be read reliably" />
        <InfoBanner kind="danger" title="Confidence too low to proceed:">
          {session.rejection_guidance}
        </InfoBanner>
        <Link href="/upload"><Tbtn variant="primary">Back to Upload</Tbtn></Link>
      </div>
    );
  }

  const editCell = (rowIdx: number, field: string, value: string) => {
    setRows((prev) => prev.map((r) => {
      if (r.row_index !== rowIdx) return r;
      const old = r.fields[field];
      if (String(old ?? "") !== value) {
        setCorrections((c) => [...c, {
          row_index: rowIdx, field, llm_predicted: old,
          operator_corrected: value, correction_type: "value_edit",
        }]);
      }
      return { ...r, fields: { ...r.fields, [field]: value === "" ? null : value } };
    }));
    setActioned((a) => new Set(a).add(rowIdx));
    setEditing(null);
  };

  const remapColumn = (sourceCol: string, oldTarget: string, newTarget: string) => {
    if (oldTarget === newTarget) return;
    setCorrections((c) => [...c, {
      field: newTarget, llm_predicted: oldTarget,
      operator_corrected: newTarget, source_column: sourceCol,
      correction_type: "column_mapping",
    }]);
    setRows((prev) => prev.map((r) => {
      const fields = { ...r.fields };
      if (oldTarget in fields) {
        fields[newTarget] = fields[oldTarget];
        fields[oldTarget] = null;
      }
      return { ...r, fields };
    }));
    setSession((s) => s && ({
      ...s,
      column_mappings: s.column_mappings.map((m) =>
        m.source_column === sourceCol ? { ...m, target_field: newTarget, confidence: 1.0, reasoning: "operator override" } : m),
    }));
    toast.push(`Remapped '${sourceCol}' → ${newTarget}`);
  };

  const acceptRow = (rowIdx: number) => setActioned((a) => new Set(a).add(rowIdx));
  const excludeRow = (rowIdx: number) => {
    setExcluded((e) => new Set(e).add(rowIdx));
    setActioned((a) => new Set(a).add(rowIdx));
  };
  const bulkAccept = () => {
    setActioned((a) => {
      const next = new Set(a);
      bulkAcceptable.forEach((r) => next.add(r.row_index));
      return next;
    });
    toast.push(`Accepted ${bulkAcceptable.length} high-confidence rows`);
  };

  const exportCSV = () => {
    const byTable: Record<string, ExtractionRow[]> = {};
    rows.filter((r) => !excluded.has(r.row_index)).forEach((r) => {
      (byTable[r.table] ??= []).push(r);
    });
    Object.entries(byTable).forEach(([table, trs]) => {
      const cols = TARGET_FIELDS[table] ?? Object.keys(trs[0].fields);
      const lines = [cols.join(",")].concat(
        trs.map((r) => cols.map((c) => JSON.stringify(r.fields[c] ?? "")).join(",")));
      const blob = new Blob([lines.join("\n")], { type: "text/csv" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${table}_confirmed.csv`;
      a.click();
    });
  };

  const submit = async () => {
    setSubmitting(true);
    try {
      const res = await confirmExtraction({
        session_id: session.session_id,
        rows: rows.map((r) => ({
          row_index: r.row_index, table: r.table, fields: r.fields,
          accepted: !excluded.has(r.row_index),
        })),
        corrections,
        actioned_flag_indices: Array.from(actioned),
      });
      toast.push(`Loaded ${res.total_inserted} rows into staging`);
      router.push("/");
    } catch (e) {
      toast.push(e instanceof Error ? e.message : "Confirm failed");
    } finally {
      setSubmitting(false);
    }
  };

  const s = session.summary;

  return (
    <div className="page">
      <PageHeader
        title="Confirm Extracted Data"
        sub={`Session ${session.session_id} · ${session.source_files.join(", ")}`}
      />

      {session.mock_mode && (
        <InfoBanner kind="warn" title="Running in demo mode">
          smart mapping not yet active. Data extracted using standard mapping rules.
        </InfoBanner>
      )}
      {session.fallback_used && (
        <InfoBanner kind="warn" title="Smart mapping temporarily unavailable">
          using standard mapping. Results below came from the deterministic fallback.
        </InfoBanner>
      )}

      {/* Summary bar */}
      <Card>
        <CardBody>
          <div style={{ display: "flex", gap: 18, flexWrap: "wrap", fontSize: 12, alignItems: "center" }}>
            <span><b>{s.total_rows}</b> rows extracted</span>
            <span style={{ color: "var(--warn)" }}><b>{s.flagged_for_review}</b> flagged</span>
            <span style={{ color: "var(--accent)" }}><b>{s.auto_accepted}</b> auto-accepted</span>
            <span style={{ color: "var(--danger)" }}><b>{s.rejected}</b> rejected</span>
            <span>confidence <b>{(s.overall_confidence * 100).toFixed(0)}%</b></span>
            <span style={{
              fontWeight: 700, fontSize: 10, letterSpacing: ".08em",
              color: session.mock_mode ? "var(--warn)" : "var(--accent)",
              border: "1px solid currentColor", borderRadius: 4, padding: "2px 6px",
            }}>
              {session.mock_mode ? "MOCK" : "LIVE"} MODE
            </span>
          </div>
        </CardBody>
      </Card>

      {session.sufficiency_warnings.length > 0 && (
        <InfoBanner kind="warn" title="Data sufficiency:">
          {session.sufficiency_warnings.join(" · ")}
        </InfoBanner>
      )}

      {/* Column mappings */}
      <Card style={{ marginTop: 16 }}>
        <CardHead title="Column Mapping" sub="How your columns were read, correct anything that looks wrong" />
        <CardBody tight>
          <table className="data-table">
            <thead><tr><th>Your column</th><th>Mapped to</th><th>Why</th></tr></thead>
            <tbody>
              {session.column_mappings.map((m) => {
                const table = rows.find((r) => m.target_field in r.fields)?.table
                  ?? Object.keys(TARGET_FIELDS).find((t) => TARGET_FIELDS[t].includes(m.target_field))
                  ?? "stg_buyer_orders";
                return (
                  <tr key={`${m.source_column}-${m.target_field}`}>
                    <td style={{ fontWeight: 600 }}>{m.source_column}{confBadge(m.confidence)}</td>
                    <td>
                      <select
                        value={m.target_field}
                        onChange={(e) => remapColumn(m.source_column, m.target_field, e.target.value)}
                        style={{ background: "var(--bg, #111)", color: "inherit", border: "1px solid var(--border)", borderRadius: 6, padding: "3px 6px", fontSize: 12 }}
                      >
                        {(TARGET_FIELDS[table] ?? []).map((f) => (
                          <option key={f} value={f} title={FIELD_HELP[f] ?? ""}>{f}</option>
                        ))}
                      </select>
                    </td>
                    <td style={{ fontSize: 11, color: "var(--muted)" }}>
                      {m.reasoning}
                      {m.alternative_mapping && ` · alt: ${m.alternative_mapping}`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {session.unmapped_columns.length > 0 && (
            <div style={{ fontSize: 11, color: "var(--muted)", padding: "8px 12px" }}>
              Not loaded: {session.unmapped_columns.join(", ")}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Flags panel */}
      <Card style={{ marginTop: 16 }}>
        <CardHead
          title={`Needs Your Review (${unactioned.length} remaining)`}
          sub="Every flagged row must be accepted, edited, or excluded before the data loads"
        />
        <CardBody tight>
          {flagged.length === 0 ? (
            <div style={{ fontSize: 12, color: "var(--muted)", padding: 12 }}>Nothing flagged.</div>
          ) : (
            <>
              {bulkAcceptable.length > 0 && (
                <div style={{ padding: "8px 12px" }}>
                  <Tbtn onClick={bulkAccept} icon={<Check size={13} />}>
                    Accept all {bulkAcceptable.length} high-confidence rows (≥90%)
                  </Tbtn>
                </div>
              )}
              <table className="data-table">
                <thead><tr><th>Row</th><th>Table</th><th>Why flagged</th><th>Action</th></tr></thead>
                <tbody>
                  {flagged.map((r) => (
                    <tr key={r.row_index} style={{ opacity: actioned.has(r.row_index) ? 0.5 : 1 }}>
                      <td>#{r.row_index}</td>
                      <td><code style={{ fontSize: 10 }}>{r.table}</code></td>
                      <td style={{ fontSize: 11, color: "var(--muted)", maxWidth: 420 }}>
                        {Array.from(new Set([
                          ...r.flags,
                          ...Object.entries(r.field_metadata)
                            .filter(([, m]) => m.flag_reason)
                            .map(([f, m]) => `${f}: ${m.flag_reason}`),
                        ].map((t) => t.replace(/^[a-z_]+: /, ""))))
                          .slice(0, 3).join(" · ") || "low-confidence fields"}
                      </td>
                      <td style={{ whiteSpace: "nowrap" }}>
                        {actioned.has(r.row_index) ? (
                          excluded.has(r.row_index) ? "excluded" : "✓ actioned"
                        ) : (
                          <span style={{ display: "inline-flex", gap: 6 }}>
                            <Tbtn onClick={() => acceptRow(r.row_index)}>Accept</Tbtn>
                            <Tbtn variant="ghost" onClick={() => excludeRow(r.row_index)}>Exclude</Tbtn>
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </CardBody>
      </Card>

      {/* Schema gaps */}
      {session.schema_gaps.length > 0 && (
        <Card style={{ marginTop: 16 }}>
          <CardHead title="Gaps & Notes" sub="Things we could not load, and why" />
          <CardBody>
            <ul style={{ fontSize: 11, color: "var(--muted)", margin: 0, paddingLeft: 18 }}>
              {session.schema_gaps.map((g, i) => <li key={i}>{g}</li>)}
            </ul>
          </CardBody>
        </Card>
      )}

      {/* Data preview */}
      <Card style={{ marginTop: 16 }}>
        <CardHead
          title="Data Preview (first 50 rows)"
          sub="Click a cell to edit. ƒ = derived value (hover to see the arithmetic)."
        />
        <CardBody tight>
          <div style={{ overflowX: "auto" }}>
            {Object.entries(
              rows.slice(0, 50).reduce<Record<string, ExtractionRow[]>>((acc, r) => {
                (acc[r.table] ??= []).push(r); return acc;
              }, {})
            ).map(([table, trs]) => {
              const cols = (TARGET_FIELDS[table] ?? []).filter((c) =>
                trs.some((r) => r.fields[c] !== undefined));
              return (
                <div key={table} style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, padding: "6px 12px", color: "var(--muted)", textTransform: "uppercase", letterSpacing: ".05em" }}>{table}</div>
                  <table className="data-table">
                    <thead>
                      <tr>{cols.map((c) => <th key={c} title={FIELD_HELP[c] ?? c}>{c}</th>)}</tr>
                    </thead>
                    <tbody>
                      {trs.map((r) => (
                        <tr key={r.row_index} style={{ opacity: excluded.has(r.row_index) ? 0.35 : 1 }}>
                          {cols.map((c) => {
                            const m = r.field_metadata[c];
                            const derived = m?.inference_source?.startsWith("derived");
                            const color = !m ? undefined
                              : m.confidence >= 0.9 ? undefined
                              : m.confidence >= 0.7 ? "var(--warn)" : "var(--danger)";
                            const isEditing = editing?.row === r.row_index && editing?.field === c;
                            return (
                              <td
                                key={c}
                                style={{ color, cursor: "pointer" }}
                                onClick={() => !isEditing && setEditing({ row: r.row_index, field: c })}
                                title={m ? `${(m.confidence * 100).toFixed(0)}% · ${m.inference_source}` : undefined}
                              >
                                {isEditing ? (
                                  <input
                                    autoFocus
                                    defaultValue={String(r.fields[c] ?? "")}
                                    onBlur={(e) => editCell(r.row_index, c, e.target.value)}
                                    onKeyDown={(e) => {
                                      if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                                      if (e.key === "Escape") setEditing(null);
                                    }}
                                    style={{ width: 90, fontSize: 12, background: "transparent", color: "inherit", border: "1px solid var(--border)", borderRadius: 4, padding: "1px 4px" }}
                                  />
                                ) : (
                                  <>
                                    {String(r.fields[c] ?? "n/a")}
                                    {derived && (
                                      <span title={m.inference_source} style={{ marginLeft: 4, fontStyle: "italic", color: "var(--muted)", fontWeight: 700 }}>ƒ</span>
                                    )}
                                  </>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            })}
          </div>
        </CardBody>
      </Card>

      {/* Actions */}
      <div style={{ display: "flex", gap: 10, marginTop: 18, alignItems: "center" }}>
        <Tbtn
          variant="primary"
          onClick={submit}
          disabled={unactioned.length > 0 || submitting}
          pending={submitting}
          icon={<Check size={14} />}
          title={unactioned.length > 0 ? `${unactioned.length} flags still need action` : "Load confirmed data"}
        >
          Confirm &amp; Run
        </Tbtn>
        <Tbtn onClick={exportCSV} icon={<Download size={13} />}>Export confirmed CSV</Tbtn>
        {unactioned.length > 0 && (
          <span style={{ fontSize: 11, color: "var(--warn)" }}>
            <Pencil size={11} style={{ verticalAlign: "-2px" }} /> {unactioned.length} flagged row(s) need action first
          </span>
        )}
      </div>

      <style>{`.data-table { width: 100%; border-collapse: collapse; } .data-table th { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: 8px 12px; text-align: left; } .data-table td { padding: 6px 12px; border-top: 1px solid var(--border); font-size: 12px; } .data-table tr:hover td { background: rgba(255,255,255,.02); }`}</style>
    </div>
  );
}

export default function ConfirmPage() {
  return (
    <Suspense fallback={<PageLoading message="Loading…" />}>
      <ConfirmInner />
    </Suspense>
  );
}
