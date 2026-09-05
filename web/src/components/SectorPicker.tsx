"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, clearApiToken, setApiToken, setSector } from "@/lib/api";

/** Two ways in: start a commercial-goods workspace, or enter a key you were given. */
export function SectorPicker() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [key, setKey] = useState("");
  const [error, setError] = useState<string | null>(null);

  const start = async () => {
    setBusy(true); setError(null);
    try {
      const r = await apiFetch<{ token: string }>("/access/start", { method: "POST", body: JSON.stringify({ sector: "commercial" }) });
      setApiToken(r.token); setSector("commercial");
      router.push("/start?new=1");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open a workspace"); setBusy(false);
    }
  };

  const enter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!key.trim()) return;
    setBusy(true); setError(null);
    setApiToken(key.trim());
    try {
      await apiFetch("/me");
      router.push("/welcome");
    } catch {
      clearApiToken();
      setError("That key did not open a workspace. Check it and try again.");
      setBusy(false);
    }
  };

  return (
    <section className="land-pick">
      <h2>Start</h2>
      <div className="land-cards">
        <article className="land-card">
          <h3>Commercial goods</h3>
          <p className="land-who">Distributors and manufacturers of packaged goods, household products and raw materials. A private workspace opens immediately; you get a key to come back with.</p>
          <button className="land-cta" style={{ border: 0, cursor: "pointer" }} disabled={busy} onClick={start}>
            {busy ? "Opening…" : "Start with commercial goods"}
          </button>
        </article>
        <article className="land-card">
          <h3>I have a key</h3>
          <p className="land-who">Enter the key you were given and we will take you to your workspace.</p>
          <form className="land-key" onSubmit={enter}>
            <input inputMode="numeric" autoComplete="off" placeholder="Your key" value={key} onChange={(e) => setKey(e.target.value)} aria-label="Workspace key" />
            <button className="land-cta" style={{ border: 0, cursor: "pointer", marginTop: 0 }} disabled={busy || !key.trim()} type="submit">Enter</button>
          </form>
        </article>
      </div>
      {error && <p style={{ color: "var(--bad)", marginTop: 12 }} role="alert">{error}</p>}
    </section>
  );
}
