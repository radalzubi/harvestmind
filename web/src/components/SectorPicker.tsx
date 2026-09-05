"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, setApiToken } from "@/lib/api";

const SECTORS = [
  {
    key: "commercial" as const,
    name: "Commercial goods",
    who: "Distributors and manufacturers of packaged goods, household products and raw materials",
    lines: [
      "Whole cases, pallets and minimum orders, in the units you buy in",
      "Real fill rates and lead times measured from your own receipts, by supplier and by lane",
      "A warning on your sea lanes weeks before your deliveries slip",
    ],
  },
  {
    key: "produce" as const,
    name: "Fresh produce",
    who: "Produce importers, distributors, food hubs and growers",
    lines: [
      "Shelf life and spoilage priced into every order, first-expiry-first-out",
      "Yield and weather risk on the supply side, not only demand",
      "Waste and lost sales measured in your own numbers",
    ],
  },
];

export function SectorPicker() {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const start = async (sector: "commercial" | "produce") => {
    setBusy(sector); setError(null);
    try {
      const r = await apiFetch<{ token: string }>("/access/start", { method: "POST", body: JSON.stringify({ sector }) });
      setApiToken(r.token);
      window.sessionStorage.setItem("harvestmind.sector", sector);
      router.push("/start?new=1");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open a workspace");
      setBusy(null);
    }
  };

  return (
    <section className="land-pick">
      <h2>Pick your sector and start</h2>
      <p className="land-who" style={{ marginBottom: 12 }}>A private workspace opens immediately. No form, no account; you get a key to come back with.</p>
      <div className="land-cards">
        {SECTORS.map((s) => (
          <article key={s.key} className="land-card">
            <h3>{s.name}</h3>
            <p className="land-who">{s.who}</p>
            <ul>{s.lines.map((l) => <li key={l}>{l}</li>)}</ul>
            <button className="land-cta" style={{ border: 0, cursor: "pointer" }} disabled={busy !== null} onClick={() => start(s.key)}>
              {busy === s.key ? "Opening your workspace…" : `Start with ${s.name.toLowerCase()}`}
            </button>
          </article>
        ))}
      </div>
      {error && <p style={{ color: "var(--bad)", marginTop: 12 }} role="alert">{error}</p>}
    </section>
  );
}
