"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { requestAccess } from "@/lib/api";

function Form() {
  const params = useSearchParams();
  const initial = params.get("sector") === "produce" ? "produce" : "commercial";
  const [sector, setSector] = useState<"commercial" | "produce">(initial);
  const [form, setForm] = useState({ company: "", contact_name: "", email: "", country: "", erp: "", sku_count: "", note: "" });
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const r = await requestAccess({ ...form, sector, sku_count: form.sku_count ? Number(form.sku_count) : null });
      setDone(r.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send the request");
    } finally { setBusy(false); }
  };

  if (done) {
    return (
      <div className="land-form">
        <div className="land-done"><b>Request received.</b> {done}</div>
        <p style={{ marginTop: 18 }}><Link href="/">Back to the start</Link></p>
      </div>
    );
  }
  return (
    <form className="land-form" onSubmit={submit}>
      <h1 style={{ fontSize: 26, margin: "0 0 6px" }}>Request access</h1>
      <p style={{ color: "var(--ink-500)", margin: 0 }}>We review every request by hand and reply within one working day. You upload nothing until your workspace exists.</p>
      <label>Sector</label>
      <div className="land-seg">
        <button type="button" className={sector === "commercial" ? "on" : ""} onClick={() => setSector("commercial")}>
          Commercial goods<small>packaged goods, household, raw materials</small>
        </button>
        <button type="button" className={sector === "produce" ? "on" : ""} onClick={() => setSector("produce")}>
          Fresh produce<small>importers, distributors, food hubs, growers</small>
        </button>
      </div>
      <label>Company</label><input required value={form.company} onChange={set("company")} />
      <label>Your name</label><input required value={form.contact_name} onChange={set("contact_name")} />
      <label>Work email</label><input required type="email" value={form.email} onChange={set("email")} />
      <label>Country</label><input required value={form.country} onChange={set("country")} placeholder="Jordan" />
      <label>ERP or system you export from</label><input value={form.erp} onChange={set("erp")} placeholder="SAP Business One, Odoo, Dynamics, Excel…" />
      <label>Roughly how many products do you buy?</label><input type="number" min={0} value={form.sku_count} onChange={set("sku_count")} />
      <label>Anything we should know</label><textarea value={form.note} onChange={set("note")} />
      {error && <p style={{ color: "var(--bad)", marginTop: 12 }} role="alert">{error}</p>}
      <button className="land-cta" type="submit" disabled={busy} style={{ marginTop: 18, border: 0, cursor: "pointer" }}>
        {busy ? "Sending…" : "Send request"}
      </button>
    </form>
  );
}

export default function RequestAccessPage() {
  return <Suspense fallback={null}><Form /></Suspense>;
}
