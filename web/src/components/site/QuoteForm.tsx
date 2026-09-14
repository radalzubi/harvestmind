"use client";

/**
 * "Get a company quote" — the high-intent commercial route.
 *
 * Five fields, and nothing that a first conversation would answer anyway. The research this
 * follows: Baymard finds perceived effort tracks the number of fields a person must consider
 * far more than the number of steps, so the optional context sits behind a disclosure rather
 * than on the page; GOV.UK's pattern is explicit labels and "(optional)" on the optional ones,
 * never an asterisk on the required ones; NN/g finds B2B buyers abandon when they cannot tell
 * whether a product applies to them, so what happens next is stated before the form, not after.
 *
 * Entered values survive a validation error — nothing is ever cleared on failure.
 */
import { useState } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { requestAccess, type Sector } from "@/lib/api";

const SECTORS: Array<{ value: Sector; label: string }> = [
  { value: "commercial", label: "Commercial goods — packaged goods, household products, raw materials" },
  { value: "produce", label: "Fresh produce — fruit and vegetables" },
  { value: "meats", label: "Meat and seafood — fresh and frozen" },
];

export function QuoteForm() {
  const [form, setForm] = useState({ company: "", contact_name: "", email: "", country: "", sector: "commercial" as Sector, erp: "", sku_count: "", note: "" });
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    setError(null);
    try {
      await requestAccess({
        company: form.company.trim(),
        contact_name: form.contact_name.trim(),
        email: form.email.trim(),
        country: form.country.trim(),
        sector: form.sector,
        erp: form.erp.trim(),
        sku_count: form.sku_count.trim() ? Number(form.sku_count) : null,
        note: form.note.trim(),
      });
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "That could not be sent. Please try again.");
    } finally {
      setSending(false);
    }
  }

  if (done) {
    return (
      <div className="zform">
        <div className="zform-done">
          <h2>Thank you — we have your request.</h2>
          <p>A person at ZAAD will read it and reply to {form.email} within two working days.</p>
          <ol className="zform-steps">
            <li><b>1</b><span>We read what you sent and check that ZAAD fits how you buy.</span></li>
            <li><b>2</b><span>A short call: what you import, how many products and suppliers, where your stock sits.</span></li>
            <li><b>3</b><span>A written quote for your company, and a workspace to run the diagnostic on your own history.</span></li>
          </ol>
          <div className="cta-row" style={{ justifyContent: "center", marginTop: 26 }}>
            <Link href="/how-it-works" className="btn btn-ghost btn-lg">See how it works</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <form className="zform" onSubmit={submit} noValidate={false}>
      <div className="zfield">
        <label className="zlabel" htmlFor="q-company">Company</label>
        <input id="q-company" className="zinput" required minLength={2} maxLength={120} autoComplete="organization"
          value={form.company} onChange={set("company")} />
      </div>

      <div className="zform-row" style={{ marginTop: 18 }}>
        <div className="zfield" style={{ marginTop: 0 }}>
          <label className="zlabel" htmlFor="q-name">Your name</label>
          <input id="q-name" className="zinput" required minLength={2} maxLength={120} autoComplete="name"
            value={form.contact_name} onChange={set("contact_name")} />
        </div>
        <div className="zfield" style={{ marginTop: 0 }}>
          <label className="zlabel" htmlFor="q-country">Country</label>
          <input id="q-country" className="zinput" required minLength={2} maxLength={60} autoComplete="country-name"
            value={form.country} onChange={set("country")} />
        </div>
      </div>

      <div className="zfield">
        <label className="zlabel" htmlFor="q-email">Work email</label>
        <input id="q-email" className="zinput" type="email" required maxLength={200} autoComplete="email"
          value={form.email} onChange={set("email")} />
        <p className="zhelp">We reply here. Nothing else is sent to this address.</p>
      </div>

      <div className="zfield">
        <label className="zlabel" htmlFor="q-sector">What do you import?</label>
        <select id="q-sector" className="zinput" value={form.sector} onChange={set("sector")}>
          {SECTORS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>

      <details className="disc" style={{ marginTop: 20, borderTop: "1px solid var(--line-soft)" }}>
        <summary>Anything that would help us prepare <span className="hint">optional</span></summary>
        <div className="disc-body">
          <div className="zfield" style={{ marginTop: 0 }}>
            <label className="zlabel" htmlFor="q-erp">System you buy in today <span style={{ color: "var(--ink-400)", fontWeight: 400 }}>(optional)</span></label>
            <input id="q-erp" className="zinput" maxLength={80} placeholder="SAP, Oracle, NetSuite, spreadsheets…"
              value={form.erp} onChange={set("erp")} />
          </div>
          <div className="zfield">
            <label className="zlabel" htmlFor="q-skus">Roughly how many products <span style={{ color: "var(--ink-400)", fontWeight: 400 }}>(optional)</span></label>
            <input id="q-skus" className="zinput" type="number" min={0} max={1000000} inputMode="numeric"
              value={form.sku_count} onChange={set("sku_count")} />
          </div>
          <div className="zfield">
            <label className="zlabel" htmlFor="q-note">Anything else <span style={{ color: "var(--ink-400)", fontWeight: 400 }}>(optional)</span></label>
            <textarea id="q-note" className="zinput" rows={3} maxLength={1000} value={form.note} onChange={set("note")} />
          </div>
        </div>
      </details>

      {error && <p className="zform-err" role="alert">{error} Nothing you typed was lost.</p>}

      <div className="zform-foot">
        <button type="submit" className="btn btn-primary btn-xl" disabled={sending}>
          {sending ? "Sending…" : "Request a quote"} {!sending && <ArrowRight size={16} className="dir-icon" />}
        </button>
      </div>
      <p className="zform-note">
        We use this only to reply to you about ZAAD. No supply-chain data is asked for here and none is
        needed to get a quote. <Link href="/privacy">How we handle it</Link>.
      </p>
    </form>
  );
}
