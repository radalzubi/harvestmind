"use client";

/**
 * EXPORT FORMATS — the shape your own system expects.
 *
 * Every distributor's import template is different: one wants `PO_NUM`, another `Document Number`,
 * a third needs a plant code in every row that ZAAD has never heard of. So a workspace defines its
 * own formats here, column by column, and each column is either a ZAAD field or a fixed value.
 *
 * Upload the template you already use and ZAAD reads its heading row and proposes a mapping. The
 * proposal is a starting point a person confirms — the mapping is stored as data and applied
 * deterministically, and no spreadsheet is ever handed to a model to interpret.
 */
import { useEffect, useRef, useState } from "react";
import { Plus, Trash2, Upload } from "lucide-react";
import { Gate } from "@/components/workspace/Gate";
import { Button, ButtonLink, EmptyState, Loading, Notice, PageHead, Section } from "@/components/workspace/ui";
import { useToast } from "@/components/Toast";
import {
  COUNT, deleteProfile, fetchProfiles, readTemplate, saveProfile,
  type ExportColumn, type ExportProfile,
} from "@/lib/zaad/product";

const BLANK: ExportProfile = {
  profile_id: null, name: "", format: "csv", sheet_name: "Purchase Order", delimiter: ",",
  date_format: "iso", number_format: "plain", filename_template: "{reference}_{supplier}_{date}",
  supplier_id: null, columns: [],
};

function ColumnRow({ column, fields, onChange, onRemove }: {
  column: ExportColumn; fields: Record<string, string>;
  onChange: (next: ExportColumn) => void; onRemove: () => void;
}) {
  return (
    <tr>
      <td>
        <input className="fld" style={{ width: "100%" }} value={column.header} aria-label="Column heading"
          onChange={(e) => onChange({ ...column, header: e.target.value })} />
      </td>
      <td>
        <select className="fld" style={{ width: "100%" }} aria-label="What goes in it"
          value={column.field ?? (column.constant != null ? "__constant" : "")}
          onChange={(e) => {
            const value = e.target.value;
            if (value === "__constant") onChange({ ...column, field: null, constant: column.constant ?? "" });
            else onChange({ ...column, field: value || null, constant: null });
          }}>
          <option value="">Choose…</option>
          <option value="__constant">A fixed value</option>
          {Object.entries(fields).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select>
      </td>
      <td>
        {column.field ? <span className="na">—</span> : (
          <input className="fld" style={{ width: "100%" }} value={column.constant ?? ""} aria-label="Fixed value"
            placeholder="e.g. JOR01" onChange={(e) => onChange({ ...column, constant: e.target.value })} />
        )}
      </td>
      <td data-align="end">
        <Button size="sm" role="tertiary" icon={<Trash2 size={14} aria-hidden />} label="Remove column" onClick={onRemove} />
      </td>
    </tr>
  );
}

function Editor({ profile, fields, onSaved, onCancel }: {
  profile: ExportProfile; fields: Record<string, string>;
  onSaved: () => void; onCancel: () => void;
}) {
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState<ExportProfile>(profile);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function readFile(file: File | undefined) {
    if (!file) return;
    try {
      const found = await readTemplate(file);
      setDraft((d) => ({
        ...d,
        name: d.name || file.name.replace(/\.[^.]+$/, ""),
        format: file.name.toLowerCase().endsWith(".xlsx") ? "xlsx" : d.format,
        columns: found.suggested_columns,
      }));
      const unmapped = found.suggested_columns.filter((c) => !c.field).length;
      toast.push(unmapped
        ? `${COUNT(found.headers.length, "column")} read. ${unmapped} need you to say what goes in them.`
        : `${COUNT(found.headers.length, "column")} read and mapped. Check each one before you save.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (input.current) input.current.value = "";
    }
  }

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await saveProfile({ ...draft, columns: draft.columns }, draft.profile_id);
      toast.push("Format saved.");
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  }

  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", padding: 18 }}>
      <div className="fld-row">
        <label><span className="fld-label">Name</span>
          <input className="fld fld--block" value={draft.name} placeholder="Oracle PO Import"
            onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></label>
        <label><span className="fld-label">File type</span>
          <select className="fld fld--block" aria-label="File type" value={draft.format}
            onChange={(e) => setDraft({ ...draft, format: e.target.value as ExportProfile["format"] })}>
            <option value="csv">CSV</option>
            <option value="xlsx">Excel (.xlsx)</option>
            <option value="print">Printable PDF</option>
          </select></label>
        <label><span className="fld-label">Dates</span>
          <select className="fld fld--block" aria-label="Date style" value={draft.date_format ?? "iso"}
            onChange={(e) => setDraft({ ...draft, date_format: e.target.value })}>
            <option value="iso">2026-02-09</option>
            <option value="dmy">09/02/2026</option>
            <option value="mdy">02/09/2026</option>
            <option value="compact">20260209</option>
          </select></label>
        <label><span className="fld-label">File name</span>
          <input className="fld fld--block" value={draft.filename_template ?? ""}
            onChange={(e) => setDraft({ ...draft, filename_template: e.target.value })} /></label>
      </div>

      <Section title="Columns">
        <div className="tbar">
          <input ref={input} type="file" accept=".csv,.xlsx" hidden aria-label="Upload a template to read its headings"
            onChange={(e) => readFile(e.target.files?.[0])} />
          <Button size="sm" icon={<Upload size={14} aria-hidden />} onClick={() => input.current?.click()}>
            Read my template
          </Button>
          <Button size="sm" role="tertiary" icon={<Plus size={14} aria-hidden />}
            onClick={() => setDraft({ ...draft, columns: [...draft.columns, { header: "", field: null, constant: null }] })}>
            Add a column
          </Button>
        </div>
        {draft.columns.length ? (
          <div className="tbl-wrap">
            <table className="tbl tbl--dense">
              <caption className="sr-only">Columns in this output format</caption>
              <thead><tr>
                <th scope="col">Heading in your file</th>
                <th scope="col">What goes in it</th>
                <th scope="col">Fixed value</th>
                <th scope="col"><span className="sr-only">Remove</span></th>
              </tr></thead>
              <tbody>
                {draft.columns.map((column, index) => (
                  <ColumnRow key={index} column={column} fields={fields}
                    onChange={(next) => setDraft({ ...draft, columns: draft.columns.map((c, i) => (i === index ? next : c)) })}
                    onRemove={() => setDraft({ ...draft, columns: draft.columns.filter((_, i) => i !== index) })} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Notice>Upload the template you already use, or add columns one at a time.</Notice>
        )}
      </Section>

      {error && <div style={{ marginTop: 12 }}><Notice tone="warn">{error}</Notice></div>}

      <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
        <Button role="primary" pending={busy} onClick={save}
          disabled={!draft.name.trim() || !draft.columns.length}>Save this format</Button>
        <Button role="tertiary" onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  );
}

function FormatsBody() {
  const toast = useToast();
  const [data, setData] = useState<Awaited<ReturnType<typeof fetchProfiles>> | null>(null);
  const [editing, setEditing] = useState<ExportProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => fetchProfiles().then(setData).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  if (error) return <Notice tone="warn">{error}</Notice>;
  if (!data) return <Loading label="Reading your formats…" cards={2} />;

  const own = data.profiles.filter((p) => p.profile_id);

  return (
    <>
      <PageHead
        title="Order export formats"
        sub="The shape your own system expects. Define it once and every approved order comes out in it."
        actions={<>
          <ButtonLink size="sm" href="/orders">Purchase orders</ButtonLink>
          {!editing && <Button role="primary" icon={<Plus size={15} aria-hidden />} onClick={() => setEditing({ ...BLANK })}>New format</Button>}
        </>}
      />

      {editing ? (
        <Editor profile={editing} fields={data.fields}
          onSaved={() => { setEditing(null); load(); }} onCancel={() => setEditing(null)} />
      ) : (
        <>
          <Section title="Your formats">
            {own.length ? (
              <div style={{ display: "grid", gap: 10 }}>
                {own.map((profile) => (
                  <div key={profile.profile_id} className="dec" style={{ cursor: "default" }}>
                    <div className="dec-top">
                      <span className="dec-verb">{profile.format.toUpperCase()}</span>
                      <span className="dec-cat">{COUNT(profile.columns.length, "column")}</span>
                    </div>
                    <h3 className="dec-h">{profile.name}</h3>
                    <p className="dec-sub">{profile.columns.map((c) => c.header).join(" · ")}</p>
                    <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
                      <Button size="sm" onClick={() => setEditing(profile)}>Edit</Button>
                      <Button size="sm" role="danger" onClick={async () => {
                        await deleteProfile(profile.profile_id!);
                        toast.push("Format removed.");
                        load();
                      }}>Remove</Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No format of your own yet"
                actions={<Button role="primary" onClick={() => setEditing({ ...BLANK })}>Define one</Button>}>
                Until you define one, orders export in ZAAD&rsquo;s standard columns. Upload the template your
                system already imports and ZAAD will propose the mapping.
              </EmptyState>
            )}
          </Section>

          <Section title="What ZAAD starts with">
            <Notice>
              <strong>{data.profiles[0]?.name}</strong> — {data.profiles[0]?.columns.map((c) => c.header).join(", ")}.
              Available to every workspace and not editable; define your own to change it.
            </Notice>
          </Section>
        </>
      )}
    </>
  );
}

export default function FormatsPage() {
  return (
    <Gate loadingLabel="Opening your workspace…" needsPlan={false} needsWorkspace={false}>
      <FormatsBody />
    </Gate>
  );
}
