"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  LayoutDashboard,
  UploadCloud,
  Database,
  Users,
  Package,
  Activity,
  ShieldCheck,
  FileText,
  Settings,
  Search,
  TrendingUp,
  Truck,
} from "lucide-react";

type NavItem = {
  href: string;
  label: string;
  Icon: typeof LayoutDashboard;
  count?: number;
};

const NAV_MAIN: NavItem[] = [
  { href: "/", label: "Overview", Icon: LayoutDashboard },
];

const NAV_DATA: NavItem[] = [
  { href: "/upload", label: "Data Upload", Icon: UploadCloud },
  { href: "/data-quality", label: "Data Quality", Icon: Database },
];

const NAV_DIAGNOSTICS: NavItem[] = [
  { href: "/inventory", label: "Inventory Risk", Icon: Package },
  { href: "/atp", label: "Available-to-Promise", Icon: Activity },
  { href: "/traceability", label: "Traceability", Icon: ShieldCheck },
  { href: "/partners", label: "Partners", Icon: Users },
];

const NAV_PLANNING: NavItem[] = [
  { href: "/forecasts", label: "Demand Forecast", Icon: TrendingUp },
  { href: "/supply-risk", label: "Supply Risk", Icon: Truck },
];

const NAV_EXPORT: NavItem[] = [
  { href: "/reports", label: "Reports", Icon: FileText },
];

function Group({ items, current }: { items: NavItem[]; current: string }) {
  return (
    <>
      {items.map((n) => {
        const active = n.href === "/" ? current === "/" : current.startsWith(n.href);
        return (
          <Link
            key={n.href}
            href={n.href}
            className={clsx("rail-link", active && "active")}
          >
            <n.Icon className="rail-link-icon" strokeWidth={1.6} />
            <span>{n.label}</span>
            {n.count !== undefined && <span className="rail-link-count">{n.count}</span>}
          </Link>
        );
      })}
    </>
  );
}

export function Sidebar() {
  const pathname = usePathname() || "/";
  return (
    <aside className="rail">
      <div className="rail-brand">
        <div className="rail-brand-mark">H</div>
        <div className="rail-brand-name">HarvestMind</div>
      </div>

      <div className="rail-search">
        <Search size={13} strokeWidth={1.6} />
        <span>Search</span>
        <kbd>⌘K</kbd>
      </div>

      <div style={{ overflow: "auto", flex: 1 }}>
        <div className="rail-section">
          <Group items={NAV_MAIN} current={pathname} />
        </div>
        <div className="rail-section">
          <div className="rail-section-label">Data</div>
          <Group items={NAV_DATA} current={pathname} />
        </div>
        <div className="rail-section">
          <div className="rail-section-label">Diagnostics</div>
          <Group items={NAV_DIAGNOSTICS} current={pathname} />
        </div>
        <div className="rail-section">
          <div className="rail-section-label">Planning</div>
          <Group items={NAV_PLANNING} current={pathname} />
        </div>
        <div className="rail-section">
          <div className="rail-section-label">Export</div>
          <Group items={NAV_EXPORT} current={pathname} />
        </div>
      </div>

      <div className="rail-footer">
        <div className="rail-user">
          <div className="rail-user-avatar">OP</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="rail-user-name">Operator</div>
            <div className="rail-user-org">HarvestMind</div>
          </div>
          <Settings size={14} color="var(--ink-400)" strokeWidth={1.6} />
        </div>
      </div>
    </aside>
  );
}
