"use client";

/**
 * UPLOAD A PROPOSED ORDER — the buyer already has it in a spreadsheet.
 *
 * Two steps, deliberately. ZAAD reads the heading row and says which column it thinks is which;
 * the buyer confirms or changes that; only then are the lines read. Every row ZAAD could not read
 * is reported by its number in the file, and nothing is stored until the buyer creates the
 * proposal from what they can see.
 */
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload } from "lucide-react";
import { Gate } from "@/components/workspace/Gate";
import { Button, ButtonLink, Loading, Notice, PageHead, Section } from "@/components/workspace/ui";
import { DataTable } from "@/components/workspace/Table";
import { EMPTY_HEADER, HeaderFields, LineEditor, type OrderHeader } from "@/components/workspace/OrderForm";
import { useToast } from "@/components/Toast";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { createDraft, readProposalFile, type DraftLine } from "@/lib/zaad/product";

type Read = Awaited<ReturnType<typeof readProposalFile>>;

function UploadBody() {
  const router = useRouter();
  const toast = useToast();
  const { request } = useWorkspaceData();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [first, setFirst] = useState<Read | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [lines, setLines] = useState<DraftLine[] | null>(null);
  const [problems, setProblems] = useState<string[]>([]);
  const [header, setHeader] = useState<OrderHeader>({ ...EMPTY_HEADER, currency: request?.currency ?? "USD" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function pick(chosen: File | undefined) {
    if (!chosen) return;
    setBusy(true);
    setError(null);
    setLines(null);
    setProblems([]);
    try {
      const read = await readProposalFile(chosen);
      setFile(chosen);
      setFirst(read);
      setMapping(read.suggested_mapping ?? {});
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  async function apply() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const read = await readProposalFile(file, mapping);
      setLines(read.lines ?? []);
      setProblems(read.problems ?? []);
      if (read.order) {
        setHeader((h) => ({
          ...h,
          supplier_id: h.supplier_id || (read.order?.supplier_id ?? ""),
          destination_id: h.destination_id || (read.order?.destination_id ?? ""),
          reference: h.reference || (read.order?.reference ?? ""),
        }));
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function create() {
    setBusy(true);
    try {
      const draft = await createDraft({
        origin: "UPLOADED_PROPOSAL", ...header, currency: header.currency.toUpperCase(),
        requested_receipt_date: header.requested_receipt_date || null,
        notes: header.notes || `Uploaded from ${file?.name ?? "a spreadsheet"}.`,
        lines: (lines ?? []).filter((l) => l.sku.trim() && Number(l.quantity) > 0),
      });
      toast.push("Proposal created from your file.");
      router.push(`/orders/${encodeURIComponent(draft.draft_id)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  const fields = first?.fields ?? {};

  return (
    <>
      <PageHead
        title="Upload a proposed order"
        sub="Bring an order you already have in a spreadsheet, confirm what the columns mean, then have ZAAD evaluate it."
        actions={<ButtonLink size="sm" href="/orders">Purchase orders</ButtonLink>}
      />

      <Section title="1. Choose the file">
        <input ref={input} type="file" accept=".csv,.xlsx" hidden aria-label="Choose a spreadsheet"
          onChange={(e) => pick(e.target.files?.[0])} />
        <div className="tbar">
          <Button role={first ? "secondary" : "primary"} icon={<Upload size={15} aria-hidden />} pending={busy && !first}
            onClick={() => input.current?.click()}>
            {file ? `Replace ${file.name}` : "Choose a CSV or Excel file"}
          </Button>
        </div>
        {error && <div style={{ marginTop: 10 }}><Notice tone="warn">{error}</Notice></div>}
      </Section>

      {first && (
        <Section title="2. Confirm what each column is">
          <p style={{ margin: "0 0 12px", fontSize: 13.5, color: "var(--ink-600)", maxWidth: "62ch", lineHeight: 1.6 }}>
            ZAAD read {first.rows} row{first.rows === 1 ? "" : "s"} and proposed the mapping below.
            {first.truncated && " Only the first rows were read."} Change anything that is wrong; a product column
            and a quantity column are the two ZAAD needs.
          </p>
          <div className="tbl-wrap">
            <table className="tbl tbl--dense">
              <caption className="sr-only">Column mapping</caption>
              <thead><tr><th scope="col">ZAAD field</th><th scope="col">Column in your file</th></tr></thead>
              <tbody>
                {Object.entries(fields).map(([field, label]) => (
                  <tr key={field}>
                    <td>{label}</td>
                    <td>
                      <select className="fld" style={{ width: "100%" }} aria-label={`Column for ${label}`}
                        value={mapping[field] ?? ""}
                        onChange={(e) => {
                          const next = { ...mapping };
                          if (e.target.value) next[field] = e.target.value;
                          else delete next[field];
                          setMapping(next);
                        }}>
                        <option value="">Not in this file</option>
                        {(first.headers ?? []).map((h) => <option key={h} value={h}>{h}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {first.preview && first.preview.length > 0 && (
            <div style={{ marginTop: 14 }}>
              <p className="tbl-count" style={{ marginTop: 0 }}>The first rows of your file</p>
              <div className="tbl-wrap">
                <table className="tbl tbl--dense">
                  <caption className="sr-only">A preview of the uploaded file</caption>
                  <thead><tr>{(first.headers ?? []).map((h) => <th key={h} scope="col">{h}</th>)}</tr></thead>
                  <tbody>
                    {first.preview.slice(0, 5).map((row, index) => (
                      <tr key={index}>{row.map((cell, i) => <td key={i}>{cell}</td>)}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          <div style={{ marginTop: 14 }}>
            <Button role="primary" pending={busy} disabled={!mapping.sku || !mapping.quantity} onClick={apply}>
              Read the lines
            </Button>
          </div>
        </Section>
      )}

      {lines && (
        <>
          <Section title="3. Check the lines">
            {problems.length > 0 && (
              <div className="notice" data-tone="warn" style={{ marginBottom: 12 }}>
                <strong>{problems.length} row{problems.length === 1 ? "" : "s"} could not be read and {problems.length === 1 ? "was" : "were"} left out</strong>
                <ul style={{ margin: "6px 0 0", paddingInlineStart: 18 }}>
                  {problems.slice(0, 8).map((p, i) => <li key={i}>{p}</li>)}
                </ul>
              </div>
            )}
            <LineEditor lines={lines} onChange={setLines} currency={header.currency || "USD"} />
          </Section>

          <Section title="4. The order">
            <HeaderFields value={header} onChange={setHeader}
              locations={(request?.locations ?? []).map((l) => l.id)} />
          </Section>

          <div style={{ marginTop: 20, display: "flex", gap: 8 }}>
            <Button role="primary" pending={busy} disabled={!lines.some((l) => l.sku.trim() && Number(l.quantity) > 0)}
              onClick={create}>Create the proposal</Button>
            <ButtonLink href="/orders">Cancel</ButtonLink>
          </div>
        </>
      )}
    </>
  );
}

export default function UploadProposalPage() {
  return (
    <Gate loadingLabel="Opening your workspace…" needsPlan={false} needsWorkspace={false}>
      <UploadBody />
    </Gate>
  );
}
