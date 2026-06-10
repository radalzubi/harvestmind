"use client";

import { useEffect, useState } from "react";
import { Play } from "lucide-react";
import {
  Card,
  CardBody,
  CardHead,
  InfoBanner,
  PageError,
  PageHeader,
  PageLoading,
  Tbtn,
} from "@/components/ui";
import { useToast } from "@/components/Toast";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface TrainingStatus {
  models: Record<string, Record<string, unknown>>;
  pool: { n_operators_contributing?: number; n_signals?: number;
          coverage_by_category?: Record<string, number> };
}

export default function AdminPage() {
  const toast = useToast();
  const [status, setStatus] = useState<TrainingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const load = () => {
    fetch(`${BASE}/training/status`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status} from /training/status`);
        const body = await r.json();
        if (!body || typeof body.models !== "object") {
          throw new Error("unexpected /training/status payload");
        }
        return body as TrainingStatus;
      })
      .then(setStatus)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const runRetrain = async () => {
    setRunning(true);
    try {
      const r = await fetch(`${BASE}/training/retrain`, { method: "POST" });
      const body = await r.json();
      toast.push(
        Object.entries(body)
          .map(([m, v]) => `${m}: ${(v as { decision?: string }).decision}`)
          .join(" · ")
      );
      load();
    } catch (e) {
      toast.push(String(e));
    } finally {
      setRunning(false);
    }
  };

  if (loading) return <PageLoading message="Loading training status…" />;
  if (error) return <PageError error={error} />;
  if (!status) return null;

  return (
    <div className="page">
      <PageHeader
        title="Training Status"
        sub="Admin view — model versions, retrain gates, and the data pool. Not shown to operators."
        actions={
          <Tbtn variant="primary" icon={<Play size={13} />} pending={running}
                onClick={runRetrain}>
            {running ? "Running…" : "Run retrain now"}
          </Tbtn>
        }
      />

      <InfoBanner kind="info" title="Every retrain is gated:">
        a refit deploys only if it beats the current production model on
        held-out data. Manual runs go through the same gates.
      </InfoBanner>

      <Card style={{ marginTop: 16 }}>
        <CardHead title="Models" sub="Versions, last retrains, distance to the next one" />
        <CardBody tight>
          <table className="data-table">
            <thead>
              <tr><th>Model</th><th>Version</th><th>Last retrain</th>
                  <th className="r">New data</th><th className="r">Needed</th>
                  <th>Status</th></tr>
            </thead>
            <tbody>
              {Object.entries(status.models).map(([name, m]) => (
                <tr key={name}>
                  <td style={{ fontWeight: 600 }}>{name}</td>
                  <td><code style={{ fontSize: 11 }}>
                    {String(m.current_version ?? "—")}</code></td>
                  <td style={{ fontSize: 11, color: "var(--muted)" }}>
                    {String(m.last_retrain ?? "never")}</td>
                  <td className="r">
                    {String(m.new_data_since_retrain ??
                            m.corpus_usable_sessions ?? "—")}</td>
                  <td className="r">
                    {String(m.new_data_needed ?? m.min_required ?? "—")}</td>
                  <td style={{ fontSize: 11, color: "var(--muted)", maxWidth: 320 }}>
                    {String(m.verdict ?? "scheduled")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardBody>
      </Card>

      <Card style={{ marginTop: 16 }}>
        <CardHead title="Data Pool" sub="The cross-operator signal base the models learn from" />
        <CardBody>
          <div style={{ fontSize: 12 }}>
            <b>{status.pool.n_operators_contributing ?? 0}</b> operators contributing ·{" "}
            <b>{status.pool.n_signals ?? 0}</b> signals
            {status.pool.coverage_by_category &&
              Object.keys(status.pool.coverage_by_category).length > 0 && (
              <span style={{ color: "var(--muted)" }}>
                {" "}· categories: {Object.entries(status.pool.coverage_by_category)
                  .map(([c, n]) => `${c} (${n})`).join(", ")}
              </span>
            )}
          </div>
        </CardBody>
      </Card>

      <style>{`.r { text-align: right; } .data-table { width: 100%; border-collapse: collapse; } .data-table th { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); padding: 8px 12px; text-align: left; } .data-table td { padding: 8px 12px; border-top: 1px solid var(--border); font-size: 12px; }`}</style>
    </div>
  );
}
