"use client";

/**
 * DASHBOARDS — saved compositions. The list, and a way to make a new one.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";
import { Gate } from "@/components/workspace/Gate";
import { Button, EmptyState, Loading, Notice, PageHead } from "@/components/workspace/ui";
import { useLocale } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import { DATE } from "@/lib/zaad/product";
import { createDashboard, listDashboards, type Dashboard } from "@/lib/analytics/client";

function DashboardsBody() {
  const { t } = useLocale();
  const copy = t.analytics.dashboards;
  const session = useSession();
  const router = useRouter();
  const [rows, setRows] = useState<Dashboard[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    listDashboards({ limit: 100 }).then((r) => alive && setRows(r.rows)).catch((e: Error) => alive && setError(e.message));
    return () => { alive = false; };
  }, []);
  const create = async () => {
    try { const d = await createDashboard({ name: copy.untitled }); router.push(`/dashboards/${encodeURIComponent(d.dashboard_id)}?edit=1`); }
    catch (e) { setError((e as Error).message); }
  };
  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!rows) return <Loading label={copy.title} cards={2} />;
  return (
    <>
      <PageHead title={copy.title} sub={copy.sub} actions={session.can("createAnalysis") ? <Button role="primary" size="sm" icon={<Plus size={14} aria-hidden />} onClick={create}>{copy.create}</Button> : undefined} />
      {rows.length === 0 ? (
        <EmptyState title={copy.none} actions={session.can("createAnalysis") ? <Button role="primary" onClick={create}>{copy.create}</Button> : undefined}>{copy.noneHint}</EmptyState>
      ) : (
        <div className="db-list">
          {rows.map((d) => (
            <Link key={d.dashboard_id} href={`/dashboards/${encodeURIComponent(d.dashboard_id)}`} className="dec db-item">
              <div className="db-item-h"><strong>{d.name}</strong><span className="tag">{d.visibility === "workspace" ? copy.workspace : copy.private}</span></div>
              <div className="dec-cat">{d.tiles} {copy.tiles} · {DATE(d.updated_at)}</div>
              {d.description && <p style={{ margin: "6px 0 0", fontSize: 13, color: "var(--ink-600)" }}>{d.description}</p>}
            </Link>
          ))}
        </div>
      )}
    </>
  );
}

export default function DashboardsPage() {
  return <Gate needsWorkspace={false}><DashboardsBody /></Gate>;
}
