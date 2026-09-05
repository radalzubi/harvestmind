"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, setApiToken } from "@/lib/api";

/** Connects the browser to the shared, synthetic demo workspace if one is configured. */
export function DemoButton() {
  const router = useRouter();
  const [state, setState] = useState<"idle" | "busy" | "none">("idle");
  const go = async () => {
    setState("busy");
    try {
      const r = await apiFetch<{ token: string }>("/access/demo", { method: "POST" });
      setApiToken(r.token);
      router.push("/start");
    } catch {
      setState("none");
    }
  };
  if (state === "none") return <span style={{ color: "var(--ink-500)" }}>No demo workspace is open right now.</span>;
  return (
    <button className="land-cta" style={{ background: "var(--ink-900)", border: 0, cursor: "pointer" }} onClick={go} disabled={state === "busy"}>
      {state === "busy" ? "Opening…" : "Try the demo with synthetic data"}
    </button>
  );
}
