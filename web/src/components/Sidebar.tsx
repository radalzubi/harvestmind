"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  LayoutDashboard, UploadCloud, Database, Users, Package, Activity, ShieldCheck, FileText,
  TrendingUp, Truck, ListChecks, FlaskConical, Boxes, Rocket, Radar, KeyRound,
} from "lucide-react";
import { familyOf, getApiToken, getMe, getSector, setSector, type Sector } from "@/lib/api";
import { Logo } from "@/components/site/Logo";

type NavItem = { href: string; label: string; Icon: typeof LayoutDashboard };
type Section = { label?: string; items: NavItem[] };

const COMMERCIAL: Section[] = [
  { items: [{ href: "/start", label: "Start", Icon: Rocket }] },
  { label: "Data", items: [{ href: "/upload", label: "Upload", Icon: UploadCloud }, { href: "/data-quality", label: "Data quality", Icon: Database }] },
  { label: "Decide", items: [{ href: "/zaad/network", label: "Zaad workspace", Icon: LayoutDashboard }, { href: "/fmcg", label: "Purchase plan", Icon: Boxes }, { href: "/state", label: "State and lanes", Icon: Radar }] },
  { label: "Export", items: [{ href: "/reports", label: "Reports", Icon: FileText }] },
];

const PRODUCE: Section[] = [
  { items: [{ href: "/start", label: "Start", Icon: Rocket }, { href: "/overview", label: "Overview", Icon: LayoutDashboard }] },
  { label: "Data", items: [{ href: "/upload", label: "Upload", Icon: UploadCloud }, { href: "/data-quality", label: "Data quality", Icon: Database }] },
  { label: "Diagnostics", items: [
    { href: "/inventory", label: "Inventory risk", Icon: Package }, { href: "/atp", label: "Available to promise", Icon: Activity },
    { href: "/traceability", label: "Traceability", Icon: ShieldCheck }, { href: "/partners", label: "Partners", Icon: Users }] },
  { label: "Planning", items: [
    { href: "/forecasts", label: "Demand forecast", Icon: TrendingUp }, { href: "/supply-risk", label: "Supply risk", Icon: Truck },
    { href: "/recommendations", label: "Recommendations", Icon: ListChecks }, { href: "/backtest", label: "Benchmark", Icon: FlaskConical }] },
  { label: "Export", items: [{ href: "/reports", label: "Reports", Icon: FileText }] },
];

function Group({ items, current }: { items: NavItem[]; current: string }) {
  return (
    <>
      {items.map((n) => (
        <Link key={n.href} href={n.href} className={clsx("rail-link", current.startsWith(n.href) && "active")}>
          <n.Icon className="rail-link-icon" strokeWidth={1.6} />
          <span>{n.label}</span>
        </Link>
      ))}
    </>
  );
}

export function Sidebar() {
  const pathname = usePathname() || "/";
  const [sector, setSectorState] = useState<Sector | null>(null);
  const [name, setName] = useState<string>("");

  useEffect(() => {
    const load = () => {
      const cached = getSector();
      if (cached) setSectorState(cached);
      if (!getApiToken()) { setName(""); return; }
      getMe().then((me) => { setSector(me.sector); setSectorState(me.sector); setName(me.name); }).catch(() => {});
    };
    load();
    window.addEventListener("harvestmind-auth-change", load);
    return () => window.removeEventListener("harvestmind-auth-change", load);
  }, []);

  const sections = sector == null ? [{ items: [{ href: "/start", label: "Start", Icon: Rocket }] }]
    : familyOf(sector) === "commercial" ? COMMERCIAL : PRODUCE;

  return (
    <aside className="rail">
      <div className="rail-brand">
        <Logo size={22} />
      </div>
      <div style={{ overflow: "auto", flex: 1 }}>
        {sections.map((s, i) => (
          <div className="rail-section" key={i}>
            {s.label && <div className="rail-section-label">{s.label}</div>}
            <Group items={s.items} current={pathname} />
          </div>
        ))}
      </div>
      <div className="rail-footer">
        <Link href="/access" className="rail-link">
          <KeyRound className="rail-link-icon" strokeWidth={1.6} />
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{name || "Workspace key"}</span>
        </Link>
      </div>
    </aside>
  );
}
