"use client";

import { usePathname } from "next/navigation";
import { AssistantButton } from "@/components/Assistant";

/** The workspace bar says where you are and offers one thing: an explanation of it. */
const TITLES: Record<string, string> = {
  "/start": "Start", "/network": "Network Twin", "/overview": "Overview", "/upload": "Upload", "/fmcg": "Purchase plan", "/state": "State and lanes",
  "/performance": "Performance", "/recommendations": "Recommendations", "/backtest": "Benchmark", "/loss": "Loss exposure",
  "/partners": "Partners", "/forecasts": "Demand forecast", "/supply-risk": "Supply risk", "/data-quality": "Data quality",
  "/reports": "Reports", "/access": "Workspace key", "/inventory": "Inventory risk", "/atp": "Available to promise", "/traceability": "Traceability",
};

export function Topbar() {
  const pathname = usePathname() || "/";
  const title = TITLES[pathname] ?? "Workspace";
  return (
    <header className="topbar">
      <div className="topbar-title">{title}</div>
      <div className="topbar-spacer" />
      <AssistantButton label="Explain this page" />
    </header>
  );
}
