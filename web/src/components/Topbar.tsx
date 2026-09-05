"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { ChevronDown } from "lucide-react";

const TITLES: Record<string, string> = {
  "/start": "Start",
  "/overview": "Overview",
  "/upload": "Upload",
  "/fmcg": "Purchase plan",
  "/state": "State and lanes",
  "/performance": "Performance",
  "/recommendations": "Recommendations",
  "/backtest": "Benchmark",
  "/loss": "Loss exposure",
  "/partners": "Partners",
  "/forecasts": "Demand forecast",
  "/supply-risk": "Supply risk",
  "/data-quality": "Data quality",
  "/reports": "Reports",
  "/access": "Pilot access",
};

const PERIODS = ["Last 4 weeks", "Last 12 weeks", "Last 26 weeks", "Last 52 weeks", "YTD"];

export function Topbar() {
  const pathname = usePathname() || "/";
  const title = TITLES[pathname] ?? "Overview";
  const [period, setPeriod] = useState("Last 12 weeks");
  const [open, setOpen] = useState(false);

  return (
    <header className="topbar">
      <div className="topbar-title">{title}</div>
      <div className="topbar-spacer" />

      <div style={{ position: "relative" }}>
        <button
          className="period-pill"
          onClick={() => setOpen((o) => !o)}
          style={{ border: 0, background: "var(--surface)" }}
        >
          {period}
          <ChevronDown size={12} color="var(--ink-500)" strokeWidth={1.6} />
        </button>
        {open && (
          <>
            <div
              onClick={() => setOpen(false)}
              style={{ position: "fixed", inset: 0, zIndex: 20 }}
            />
            <div
              style={{
                position: "absolute",
                right: 0,
                top: 38,
                minWidth: 180,
                background: "var(--surface)",
                border: "1px solid var(--line)",
                borderRadius: "var(--radius)",
                boxShadow: "var(--shadow-md)",
                padding: 4,
                zIndex: 30,
              }}
            >
              {PERIODS.map((p) => (
                <button
                  key={p}
                  onClick={() => {
                    setPeriod(p);
                    setOpen(false);
                  }}
                  style={{
                    display: "block",
                    width: "100%",
                    textAlign: "left",
                    padding: "8px 12px",
                    fontSize: 13,
                    color: p === period ? "var(--ink-900)" : "var(--ink-700)",
                    background: p === period ? "var(--ink-100)" : "transparent",
                    border: 0,
                    borderRadius: 4,
                    cursor: "pointer",
                  }}
                >
                  {p}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

    </header>
  );
}
