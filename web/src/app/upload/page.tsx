"use client";

import { useState, useRef } from "react";
import { Upload, CheckCircle, XCircle, AlertTriangle, Database } from "lucide-react";
import { Card, CardBody, CardHead, PageHeader, Badge, Tbtn } from "@/components/ui";
import { useToast } from "@/components/Toast";
import { useRouter } from "next/navigation";
import { uploadCSV, clearStagingTable, getIntakeStatus, loadSampleData, extractFiles, getSector, getMe, setSector, type UploadResult, type IntakeStatus, type SampleLoadResult } from "@/lib/api";
import { useEffect } from "react";

type TableSpec = { table: string; label: string; description: string; required: string[] };

const PRODUCE_TABLES: TableSpec[] = [
  { table: "stg_products", label: "Products", description: "Product catalog with shelf life and traceability flags", required: ["product_name"] },
  { table: "stg_supplier_deliveries", label: "Supplier deliveries", description: "Historical supplier deliveries with accepted and rejected quantities", required: ["product_name", "delivery_date"] },
  { table: "stg_inventory_lots", label: "Inventory lots", description: "Current lot-level inventory with expiration dates", required: ["product_name", "quantity_on_hand"] },
  { table: "stg_buyer_orders", label: "Buyer orders", description: "Buyer order history with fulfilled quantities", required: ["product_name", "requested_quantity"] },
  { table: "stg_waste_adjustments", label: "Waste log", description: "Waste and spoilage with values lost", required: ["product_name", "quantity_lost"] },
];

const COMMERCIAL_TABLES: TableSpec[] = [
  { table: "stg_fmcg_skus", label: "Product list", description: "One row per product: item code, supplier, cost, selling price, units per case, minimum order", required: ["sku", "unit_cost"] },
  { table: "stg_fmcg_orders", label: "Sales (customer orders)", description: "Customer order lines: date, item, quantity ordered, quantity shipped", required: ["sku", "qty_ordered", "order_date"] },
  { table: "stg_fmcg_purchase_orders", label: "Purchase orders", description: "What you ordered from suppliers: PO number, date, supplier, item, quantity", required: ["po_id", "sku", "qty_ordered", "po_date"] },
  { table: "stg_fmcg_receipts", label: "Goods received", description: "What arrived against each PO: PO number, date received, quantity received", required: ["po_id", "qty_received", "receipt_date"] },
  { table: "stg_fmcg_inventory", label: "Stock counts", description: "Stock on hand per item, weekly or monthly", required: ["sku", "on_hand", "snapshot_date"] },
  { table: "stg_fmcg_suppliers", label: "Supplier list (optional)", description: "Supplier code, shipping route or port, country of origin, quoted lead time", required: ["supplier_id"] },
];

interface TableState {
  status: "idle" | "uploading" | "success" | "error";
  result?: UploadResult;
  rowCount?: number;
}

export default function UploadPage() {
  const toast = useToast();
  const [sector, setSectorState] = useState<"commercial" | "produce">(() => getSector() ?? "produce");
  const STAGING_TABLES = sector === "commercial" ? COMMERCIAL_TABLES : PRODUCE_TABLES;
  const [states, setStates] = useState<Record<string, TableState>>(() =>
    Object.fromEntries([...PRODUCE_TABLES, ...COMMERCIAL_TABLES].map((t) => [t.table, { status: "idle" }]))
  );
  const [intakeStatus, setIntakeStatus] = useState<IntakeStatus | null>(null);
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});

  useEffect(() => {
    getMe().then((me) => { setSector(me.sector); setSectorState(me.sector); }).catch(() => {});
    getIntakeStatus()
      .then(setIntakeStatus)
      .catch(() => {});
  }, []);

  const refreshStatus = () => {
    getIntakeStatus()
      .then(setIntakeStatus)
      .catch(() => {});
  };

  const handleUpload = async (table: string, file: File) => {
    setStates((s) => ({ ...s, [table]: { status: "uploading" } }));
    try {
      const result = await uploadCSV(table, file);
      if (result.errors.length > 0) {
        setStates((s) => ({ ...s, [table]: { status: "error", result } }));
        toast.push(`${table}: upload failed — ${result.errors[0]}`);
      } else {
        setStates((s) => ({
          ...s,
          [table]: { status: "success", result, rowCount: result.rows_inserted },
        }));
        toast.push(`${table}: ${result.rows_inserted} rows loaded`);
        refreshStatus();
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Upload failed";
      setStates((s) => ({ ...s, [table]: { status: "error", result: undefined } }));
      toast.push(`${table}: ${message}`);
    }
  };

  const handleClear = async (table: string) => {
    try {
      await clearStagingTable(table);
      setStates((s) => ({ ...s, [table]: { status: "idle" } }));
      toast.push(`${table} cleared`);
      refreshStatus();
    } catch {
      toast.push(`Failed to clear ${table}`);
    }
  };

  const [sampleLoading, setSampleLoading] = useState(false);
  const [sampleResult, setSampleResult] = useState<SampleLoadResult | null>(null);
  const [sampleError, setSampleError] = useState<string | null>(null);

  // ── Smart upload (LLM extraction layer) ──────────────────────────────
  const router = useRouter();
  const [smartBusy, setSmartBusy] = useState(false);
  const [smartError, setSmartError] = useState<string | null>(null);
  const smartRef = useRef<HTMLInputElement | null>(null);

  const handleSmartUpload = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    setSmartBusy(true);
    setSmartError(null);
    try {
      const result = await extractFiles(Array.from(fileList));
      if (result.status === "rejected") {
        setSmartError(result.rejection_guidance ?? "Extraction confidence too low.");
        return;
      }
      router.push(`/upload/confirm?session=${encodeURIComponent(result.session_id)}`);
    } catch (e) {
      setSmartError(e instanceof Error ? e.message : "Extraction failed");
    } finally {
      setSmartBusy(false);
      if (smartRef.current) smartRef.current.value = "";
    }
  };

  const handleLoadSample = async () => {
    setSampleLoading(true);
    setSampleResult(null);
    setSampleError(null);
    try {
      const result = await loadSampleData();
      setSampleResult(result);
      toast.push(`Sample data loaded — ${result.total_rows} rows across ${result.tables_loaded} tables`);
      refreshStatus();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load sample data";
      setSampleError(message);
      toast.push(`Sample load failed: ${message}`);
    } finally {
      setSampleLoading(false);
    }
  };

  const loadedCount = intakeStatus
    ? Object.values(intakeStatus.tables).filter((t) => t.loaded).length
    : 0;

  return (
    <div className="page">
      <PageHeader
        title="Upload"
        sub={sector === "commercial"
          ? "Six exports from your ERP: product list, sales, purchase orders, goods received, stock counts, suppliers. Twelve to twenty-four months of history."
          : "Five exports: products, supplier deliveries, inventory lots, buyer orders, waste log."}
      />

      {/* Smart upload — LLM extraction layer (additive; classic flow below unchanged) */}
      <Card style={{ marginBottom: 20 }}>
        <CardHead
          title="Smart Upload — Any Format"
          sub="Drop whatever you have: messy Excel, QuickBooks exports, PDF invoices, CSVs, message logs. We read it, map it, and show you everything for confirmation before anything loads."
        />
        <CardBody>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <input
              ref={smartRef}
              type="file"
              multiple
              accept=".csv,.xlsx,.xls,.pdf,.txt,.json"
              style={{ display: "none" }}
              onChange={(e) => handleSmartUpload(e.target.files)}
            />
            <Tbtn
              variant="primary"
              pending={smartBusy}
              onClick={() => smartRef.current?.click()}
            >
              {smartBusy ? "Reading your data…" : "Choose files (any format)"}
            </Tbtn>
            <span style={{ fontSize: 11, color: "var(--muted)" }}>
              Nothing loads until you confirm it. Every inferred value is marked and explained.
            </span>
          </div>
          {smartError && (
            <div style={{ marginTop: 10, fontSize: 12, color: "var(--danger)" }}>
              ⚠ {smartError}
            </div>
          )}
        </CardBody>
      </Card>

      {/* Quick-start: one-click sample loader (produce sample set) */}
      {sector === "produce" && <Card style={{ marginBottom: 20 }}>
        <CardHead
          title="Quick Start — Load Sample Dataset"
          sub="Skip manual upload and explore HarvestMind with a pre-built demo dataset"
        />
        <CardBody>
          <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 14, lineHeight: 1.6 }}>
            Loads 5 sample tables covering tomatoes, cucumbers, strawberries, and more — with
            intentional quality issues (near-expiry lots, a low-fill-rate supplier, a buyer with
            recurring missed orders) so every diagnostic panel shows real findings.{" "}
            <strong style={{ color: "var(--text)" }}>
              Replaces any existing staging data.
            </strong>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <Tbtn
              variant="primary"
              icon={<Database size={13} strokeWidth={1.6} />}
              pending={sampleLoading}
              onClick={handleLoadSample}
            >
              {sampleLoading ? "Loading sample data…" : "Load sample dataset"}
            </Tbtn>
            {sampleResult && !sampleLoading && (
              <span style={{ fontSize: 12, color: "var(--accent)", display: "flex", alignItems: "center", gap: 5 }}>
                <CheckCircle size={13} />
                {sampleResult.total_rows} rows loaded across {sampleResult.tables_loaded} tables
              </span>
            )}
            {sampleError && (
              <span style={{ fontSize: 12, color: "var(--danger)", display: "flex", alignItems: "center", gap: 5 }}>
                <XCircle size={13} />
                {sampleError}
              </span>
            )}
          </div>
          {sampleResult?.errors && sampleResult.errors.length > 0 && (
            <div style={{ marginTop: 10 }}>
              {sampleResult.errors.map((e, i) => (
                <div key={i} style={{ fontSize: 11, color: "var(--warn)", marginBottom: 2 }}>⚠ {e}</div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>}

      {/* Progress summary */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        {STAGING_TABLES.map((t) => {
          const loaded = intakeStatus?.tables[t.table]?.loaded;
          const state = states[t.table];
          return (
            <div
              key={t.table}
              style={{
                flex: 1,
                background: "var(--surface)",
                border: `1px solid ${loaded ? "rgba(74,222,128,0.3)" : state.status === "error" ? "rgba(248,113,113,0.3)" : "var(--border)"}`,
                borderRadius: 8,
                padding: "10px 14px",
              }}
            >
              <div style={{ fontSize: 10, color: "var(--muted)", marginBottom: 4 }}>
                {t.label}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {loaded ? (
                  <CheckCircle size={14} color="var(--accent)" />
                ) : state.status === "error" ? (
                  <XCircle size={14} color="var(--danger)" />
                ) : (
                  <div style={{ width: 14, height: 14, borderRadius: "50%", background: "var(--border)" }} />
                )}
                <span style={{ fontSize: 11 }}>
                  {intakeStatus?.tables[t.table]?.row_count ?? 0} rows
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Upload cards */}
      {STAGING_TABLES.map((t) => {
        const state = states[t.table];
        const loaded = intakeStatus?.tables[t.table]?.loaded;

        return (
          <Card key={t.table} style={{ marginBottom: 12 }}>
            <CardHead
              title={t.label}
              actions={
                loaded ? (
                  <Badge kind="low">
                    {intakeStatus?.tables[t.table]?.row_count} rows
                  </Badge>
                ) : null
              }
            />
            <CardBody>
              <div style={{ color: "var(--muted)", fontSize: 12, marginBottom: 12 }}>
                {t.description}
              </div>
              <div style={{ fontSize: 11, color: "var(--muted)", marginBottom: 10 }}>
                Required columns:{" "}
                <span style={{ color: "var(--text)", fontFamily: "monospace" }}>
                  {t.required.join(", ")}
                </span>
              </div>

              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <input
                  ref={(el) => { fileRefs.current[t.table] = el; }}
                  type="file"
                  accept=".csv"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleUpload(t.table, file);
                    if (e.target) e.target.value = "";
                  }}
                />
                <Tbtn
                  variant="primary"
                  pending={state.status === "uploading"}
                  icon={<Upload size={12} />}
                  onClick={() => fileRefs.current[t.table]?.click()}
                >
                  {state.status === "uploading" ? "Uploading…" : "Upload CSV"}
                </Tbtn>
                {loaded && (
                  <Tbtn onClick={() => handleClear(t.table)}>
                    Clear
                  </Tbtn>
                )}
              </div>

              {/* Result feedback */}
              {state.result && (
                <div style={{ marginTop: 12 }}>
                  {state.result.errors.length > 0 && (
                    <div style={{ marginBottom: 8 }}>
                      {state.result.errors.map((e, i) => (
                        <div key={i} style={{ display: "flex", gap: 6, alignItems: "flex-start", color: "var(--danger)", fontSize: 12, marginBottom: 4 }}>
                          <XCircle size={13} style={{ marginTop: 1, flexShrink: 0 }} />
                          {e}
                        </div>
                      ))}
                    </div>
                  )}
                  {state.result.warnings.length > 0 && (
                    <div>
                      {state.result.warnings.map((w, i) => (
                        <div key={i} style={{ display: "flex", gap: 6, alignItems: "flex-start", color: "var(--warn)", fontSize: 12, marginBottom: 4 }}>
                          <AlertTriangle size={13} style={{ marginTop: 1, flexShrink: 0 }} />
                          {w}
                        </div>
                      ))}
                    </div>
                  )}
                  {state.result.errors.length === 0 && state.result.warnings.length === 0 && (
                    <div style={{ display: "flex", gap: 6, alignItems: "center", color: "var(--accent)", fontSize: 12 }}>
                      <CheckCircle size={13} />
                      {state.result.rows_inserted} rows loaded — no issues
                    </div>
                  )}
                </div>
              )}
            </CardBody>
          </Card>
        );
      })}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
