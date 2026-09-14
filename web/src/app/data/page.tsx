"use client";

/**
 * DATA — one place that answers: is ZAAD ready to plan, what is missing, what do I do next?
 *
 * Sources rather than tables: today every source is a file, and the same shape holds when one
 * becomes an ERP or an EDI feed. The staging table name lives under technical details only.
 */
import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, Check, RefreshCw, Upload } from "lucide-react";
import { Button, ButtonLink, Disclosure, EmptyState, ErrorState, Loading, Notice, PageHead, Section, TechnicalDetails } from "@/components/workspace/ui";
import { useReadiness, type DataSource } from "@/lib/zaad/readiness";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { useSession } from "@/lib/session";
import { clearStagingTable, extractFiles, loadSampleData, uploadCSV } from "@/lib/api";
import { useToast } from "@/components/Toast";

function SourceRow({ source, onChanged }: { source: DataSource; onChanged: () => void }) {
  const toast = useToast();
  const session = useSession();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  async function pick(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    try {
      const result = await uploadCSV(source.table, file);
      toast.push(result.errors.length
        ? `${source.name}: ${result.errors[0]}`
        : `${source.name}: ${result.rows_inserted.toLocaleString("en-US")} rows added`);
      onChanged();
    } catch (e) {
      toast.push(`${source.name} could not be read: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  const tone = source.state === "missing" ? (source.required ? "var(--bad)" : "var(--ink-400)")
    : source.state === "problem" ? "var(--warn)" : "var(--good)";

  return (
    <div style={{ borderBottom: "1px solid var(--line-soft)", padding: "14px 0" }}>
      <div style={{ display: "flex", gap: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
        <span aria-hidden style={{ marginTop: 3, color: tone, display: "inline-flex" }}>
          {source.state === "loaded" ? <Check size={16} /> : source.state === "problem" ? <AlertTriangle size={16} /> : <Upload size={16} />}
        </span>
        <div style={{ flex: 1, minWidth: 220 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <strong style={{ fontSize: 14, color: "var(--ink-950)", fontWeight: 600 }}>{source.name}</strong>
            {!source.required && <span className="tag">Optional</span>}
            <span style={{ fontSize: 12.5, color: "var(--ink-500)" }}>
              {source.state === "missing" ? "Not added yet" : `${source.rows.toLocaleString("en-US")} rows`}
            </span>
          </div>
          <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--ink-600)" }}>{source.why}</p>
          {source.issues.length > 0 && (
            <ul style={{ margin: "8px 0 0", paddingInlineStart: 18, fontSize: 12.5, color: "var(--warn)" }}>
              {source.issues.slice(0, 4).map((i, n) => <li key={n}>{i}</li>)}
            </ul>
          )}
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <input ref={input} type="file" accept=".csv,text/csv" hidden onChange={(e) => pick(e.target.files?.[0])}
            aria-label={`Upload a CSV for ${source.name}`} />
          <Button size="sm" pending={busy} disabled={!session.can("manageData")} onClick={() => input.current?.click()}>
            {source.state === "missing" ? "Add file" : "Replace"}
          </Button>
          {source.state !== "missing" && session.can("manageData") && (
            <Button size="sm" role="tertiary" onClick={async () => {
              await clearStagingTable(source.table).catch(() => {});
              toast.push(`${source.name} cleared`);
              onChanged();
            }}>Clear</Button>
          )}
        </div>
      </div>
    </div>
  );
}


/**
 * The column-mapping intake: drop any spreadsheet and ZAAD proposes which column is which,
 * for confirmation before anything is stored. Folded in from the old Upload page.
 */
function MappedIntake() {
  const router = useRouter();
  const toast = useToast();
  const session = useSession();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);

  async function pick(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true);
    try {
      const result = await extractFiles(Array.from(files));
      router.push(`/upload/confirm?session=${encodeURIComponent(result.session_id)}`);
    } catch (e) {
      toast.push(`Those files could not be read: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: "16px 18px" }}>
      <p style={{ margin: 0, fontSize: 13.5, color: "var(--ink-700)", lineHeight: 1.6, maxWidth: "62ch" }}>
        If your files do not match the sources below, add them here instead. ZAAD reads the columns, proposes
        what each one is, and shows you every proposal to confirm or correct before a single row is stored.
      </p>
      <input ref={input} type="file" multiple accept=".csv,.xlsx,.xls,text/csv" hidden
        onChange={(e) => pick(e.target.files)} aria-label="Choose spreadsheets for ZAAD to map" />
      <div style={{ marginTop: 12 }}>
        <Button role="secondary" pending={busy} disabled={!session.can("manageData")} onClick={() => input.current?.click()}>
          Choose files
        </Button>
      </div>
    </div>
  );
}

export default function DataPage() {
  const session = useSession();
  const readiness = useReadiness();
  const workspace = useWorkspaceData();
  const toast = useToast();
  const [seeding, setSeeding] = useState(false);

  if (session.status === "anonymous") {
    return <EmptyState title="This workspace is not open on this device" actions={<ButtonLink href="/get-started" role="primary">Open your workspace</ButtonLink>}>
      Open your workspace to add or replace data.
    </EmptyState>;
  }
  if (readiness.loading) return <Loading label="Checking what your workspace holds…" cards={2} />;
  if (readiness.error) {
    return <ErrorState
      title="Your data could not be read"
      affects="Nothing was changed or uploaded."
      whatToDo="Try again; if it keeps failing, your access may have been rotated."
      detail={readiness.error}
      actions={<Button role="primary" onClick={readiness.refresh}>Try again</Button>}
    />;
  }

  const ready = readiness.canPlan;
  const missing = readiness.sources.filter((s) => s.state === "missing");

  return (
    <>
      <PageHead
        title="Data"
        sub="What ZAAD reads, how fresh it is and what is still missing."
        actions={<Button role="tertiary" size="sm" icon={<RefreshCw size={14} aria-hidden />} onClick={() => { readiness.refresh(); workspace.refresh(); }}>Refresh</Button>}
      />

      <div className="status-line">
        <span className="status-dot" data-tone={ready ? (readiness.sources.some((s) => s.state === "problem") ? "watch" : "ok") : "attention"} aria-hidden />
        <div>
          <h2 className="status-head" style={{ fontSize: 20 }}>
            {ready ? "ZAAD is ready to plan." : "ZAAD cannot plan yet."}
          </h2>
          <p className="status-sub">
            {ready
              ? <>{readiness.totalRows.toLocaleString("en-US")} rows across {readiness.sources.filter((s) => s.state !== "missing").length} sources.{" "}
                {readiness.nextStep ? readiness.nextStep.title : "Nothing needs your attention here."}{" "}
                <Link href="/home">Go to Home</Link> to see what to change.</>
              : <>{readiness.nextStep?.title ?? "Something required is missing"}. {readiness.nextStep?.detail}</>}
          </p>
        </div>
      </div>

      {!ready && missing.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Notice tone="warn">
            <strong>Still needed:</strong> {missing.filter((s) => s.required).map((s) => s.name.toLowerCase()).join(", ") || "nothing"}.
            {" "}Everything else is optional and adds detail rather than unlocking planning.
          </Notice>
        </div>
      )}

      <Section title="Add a file ZAAD maps for you">
        <MappedIntake />
      </Section>

      <Section title="Your data sources">
        <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: "2px 16px 8px" }}>
          {readiness.sources.map((s) => <SourceRow key={s.table} source={s} onChanged={() => { readiness.refresh(); workspace.refresh(); }} />)}
        </div>
        <p className="zhelp" style={{ marginTop: 10 }}>
          Files are CSV today. ZAAD reads each source into your own isolated workspace; nothing is pooled with
          another operator and nothing is used for training. <Link href="/security">How your data is handled</Link>.
        </p>
      </Section>

      {readiness.score != null && (
        <Section title="Data quality">
          <div className="facts">
            <div><dt>Overall</dt><dd>{Math.round(readiness.score)}<span style={{ color: "var(--ink-400)", fontWeight: 400 }}>/100</span>{readiness.scoreLabel ? <span className="note">{readiness.scoreLabel}</span> : null}</dd></div>
            <div><dt>Rows read</dt><dd>{readiness.totalRows.toLocaleString("en-US")}</dd></div>
            <div><dt>Sources with issues</dt><dd>{readiness.sources.filter((s) => s.issues.length).length}</dd></div>
          </div>
        </Section>
      )}

      <Section title="What ZAAD fitted from your history">
        {workspace.build?.fits && Object.keys(workspace.build.fits).length > 0 ? (
          <dl className="evid" style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: "4px 16px" }}>
            {Object.entries(workspace.build.fits).slice(0, 12).map(([supplier, fit]) => (
              <div className="evid-row" key={supplier}>
                <dt>{supplier}</dt>
                <dd>
                  {fit.fill != null ? `${(fit.fill * 100).toFixed(1)}% of ordered quantity arrives` : <span className="na">Reliability not measured</span>}
                  {fit.lead_days != null && `, about ${Math.round(fit.lead_days)} days lead`}
                  {fit.sample_size != null && ` — from ${fit.sample_size} deliver${fit.sample_size === 1 ? "y" : "ies"}`}
                  {fit.provenance && <span className="evid-prov">{fit.provenance.replaceAll("_", " ").toLowerCase()}</span>}
                </dd>
              </div>
            ))}
          </dl>
        ) : (
          <Notice>Supplier reliability appears once goods received are matched to purchase orders.</Notice>
        )}
      </Section>

      <Section title="Advanced">
        <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: "4px 16px 8px" }}>
          <Disclosure summary="Source names and row counts" hint="for a technical reader">
            <dl className="evid">
              {readiness.sources.map((s) => (
                <div className="evid-row" key={s.table}>
                  <dt style={{ fontFamily: "var(--mono)", fontSize: 12 }}>{s.table}</dt>
                  <dd>{s.rows.toLocaleString("en-US")} rows{s.issues.length ? ` · ${s.issues.length} issue${s.issues.length === 1 ? "" : "s"}` : ""}</dd>
                </div>
              ))}
            </dl>
          </Disclosure>
          <TechnicalDetails value={{ rows_read: workspace.build?.rows_read, compact: workspace.build?.compact, leakage_guard: workspace.build?.leakage_guard, incumbent_rule: workspace.build?.incumbent_rule, warnings: workspace.build?.warnings }} hint="build report" />
          {session.can("manageData") && (
            <Disclosure summary="Load a demonstration dataset" hint="replaces nothing you have added">
              <p>Adds a small illustrative dataset to this workspace so you can see how ZAAD behaves before your own history is in. It is clearly synthetic and is not a customer validation of anything.</p>
              <Button pending={seeding} onClick={async () => {
                setSeeding(true);
                try {
                  const r = await loadSampleData();
                  toast.push(`Demonstration data loaded: ${r.total_rows.toLocaleString("en-US")} rows`);
                  readiness.refresh(); workspace.refresh();
                } catch (e) {
                  toast.push(`Could not load it: ${e instanceof Error ? e.message : String(e)}`);
                } finally { setSeeding(false); }
              }}>Load demonstration data</Button>
            </Disclosure>
          )}
        </div>
      </Section>
    </>
  );
}
