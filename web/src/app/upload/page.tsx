"use client";

/**
 * UPLOAD — bring information into ZAAD. That is the only thing this page does.
 *
 * It used to be folded into Data, which put "add my files" behind a page called "inspect what I
 * have" — the wrong way round for the order the work actually happens in. Upload now comes first
 * in the navigation and holds nothing but intake: what ZAAD needs, what it has, what to add next,
 * and the mapped route for a spreadsheet that does not match a named source.
 */
import { useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, Check, Upload as UploadIcon } from "lucide-react";
import { Button, ButtonLink, Disclosure, EmptyState, ErrorState, Loading, Notice, PageHead, Section } from "@/components/workspace/ui";
import { useReadiness, type DataSource } from "@/lib/zaad/readiness";
import { CapabilityMatrix, useCapabilityReadiness } from "@/components/workspace/Readiness";
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
          {source.state === "loaded" ? <Check size={16} /> : source.state === "problem" ? <AlertTriangle size={16} /> : <UploadIcon size={16} />}
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

/** Drop any spreadsheet: ZAAD proposes which column is which, for confirmation before anything is stored. */
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

export default function UploadPage() {
  const session = useSession();
  const readiness = useReadiness();
  const capabilities = useCapabilityReadiness();
  const workspace = useWorkspaceData();
  const toast = useToast();
  const [seeding, setSeeding] = useState(false);

  if (session.status === "anonymous") {
    return <EmptyState title="This workspace is not open here"
      actions={<ButtonLink href="/get-started" role="primary">Open your workspace</ButtonLink>}>
      ZAAD keeps your access to the browser tab you opened it in. Open your workspace to add or
      replace data.
    </EmptyState>;
  }
  if (readiness.loading) return <Loading label="Checking what your workspace holds…" cards={2} />;
  if (readiness.error) {
    return <ErrorState title="Your data could not be read"
      affects="Nothing was changed or uploaded."
      whatToDo="Try again; if it keeps failing, your access may have been rotated."
      detail={readiness.error}
      actions={<Button role="primary" onClick={readiness.refresh}>Try again</Button>} />;
  }

  const ready = readiness.canPlan;
  const missing = readiness.sources.filter((s) => s.state === "missing" && s.required);

  return (
    <>
      <PageHead title="Upload"
        sub="Bring your data into ZAAD. Everything lands in your own isolated workspace; nothing is pooled with another operator and nothing is used for training." />

      <div className="status-line">
        <span className="status-dot" data-tone={ready ? (readiness.sources.some((s) => s.state === "problem") ? "watch" : "ok") : "attention"} aria-hidden />
        <div>
          <h2 className="status-head" style={{ fontSize: 20 }}>
            {ready ? "ZAAD has what it needs to plan." : "ZAAD cannot plan yet."}
          </h2>
          {/* "Nothing needs your attention" used to sit a screen above a table saying five
              capabilities were blocked. The sentence now comes from the same counted answer. */}
          <p className="status-sub">
            {ready
              ? <>{readiness.totalRows.toLocaleString("en-US")} rows across {readiness.sources.filter((s) => s.state !== "missing").length} sources.
                {" "}{readiness.nextStep ? readiness.nextStep.title
                  : capabilities.readiness
                    ? capabilities.readiness.summary.blocked || capabilities.readiness.summary.partial
                      ? `${capabilities.readiness.summary.ready} of ${capabilities.readiness.summary.ready + capabilities.readiness.summary.partial + capabilities.readiness.summary.blocked} things ZAAD can do are fully available; ${capabilities.readiness.summary.blocked} ${capabilities.readiness.summary.blocked === 1 ? "is" : "are"} blocked by a missing field — see below.`
                      : "Every capability the upload can carry is available."
                    : ""}{" "}
                <Link href="/data">Inspect what ZAAD holds</Link> or <Link href="/home">go to Home</Link>.</>
              : <>{readiness.nextStep?.title ?? "Something required is missing"}. {readiness.nextStep?.detail}</>}
          </p>
        </div>
      </div>

      {missing.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Notice tone="warn">
            <strong>Still needed:</strong> {missing.map((s) => s.name.toLowerCase()).join(", ")}.
            {" "}Everything else is optional and adds detail rather than unlocking planning.
          </Notice>
        </div>
      )}

      <Section title="Add a file ZAAD maps for you">
        <MappedIntake />
      </Section>

      <Section title="Your data sources" more="Inspect the records" moreHref="/data">
        <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: "2px 16px 8px" }}>
          {readiness.sources.map((s) => (
            <SourceRow key={s.table} source={s} onChanged={() => { readiness.refresh(); capabilities.refresh(); workspace.refresh(); }} />
          ))}
        </div>
        <p className="zhelp" style={{ marginTop: 10 }}>
          Adding a file replaces that source; it does not merge with what was there.{" "}
          <Link href="/security">How your data is handled</Link>.
        </p>
      </Section>

      {/* A source can be loaded and still not carry the field a capability needs: 16,751
          purchase orders with no promised date is "loaded" and cannot measure lateness. This
          says, per capability, what the data unlocks and which column decides it. */}
      {capabilities.readiness && (
        <Section title="What ZAAD can do with this data" more="Inspect the fields" moreHref="/data">
          <CapabilityMatrix rows={capabilities.readiness.capabilities} />
          <p className="zhelp" style={{ marginTop: 10 }}>
            Counted from your uploaded rows, not from whether a file exists. &ldquo;Blocked&rdquo; names a
            column the upload could carry; &ldquo;Not in the upload&rdquo; needs data the canonical upload does not have.
          </p>
        </Section>
      )}

      {session.can("manageData") && (
        <Section title="Advanced">
          <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: "4px 16px 8px" }}>
            <Disclosure summary="Load a demonstration dataset" hint="clearly synthetic">
              <p>
                Adds a small illustrative dataset to this workspace so you can see how ZAAD behaves before your own
                history is in. It is synthetic, it replaces what is in these sources, and it is not a customer
                validation of anything.
              </p>
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
          </div>
        </Section>
      )}
    </>
  );
}
