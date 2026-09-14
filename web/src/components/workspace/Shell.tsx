"use client";

/**
 * The workspace chrome: four destinations, the workspace you are in, and help that does
 * not compete with the work. The rail on a desktop and the same four as a bottom bar on a
 * phone — one information architecture, two shapes.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Database, Home, LayoutList, Share2, ChevronDown, HelpCircle, LogOut, Search, Wrench } from "lucide-react";
import { Logo } from "@/components/site/Logo";
import { useSession } from "@/lib/session";
import { useOpenDecisions, useWorkspaceData } from "@/lib/zaad/workspace-data";
import { AssistantButton } from "@/components/Assistant";
import { CommandPalette } from "./CommandPalette";

const NAV = [
  { href: "/home", label: "Home", Icon: Home },
  { href: "/decisions", label: "Decisions", Icon: LayoutList },
  { href: "/network", label: "Network", Icon: Share2 },
  { href: "/data", label: "Data", Icon: Database },
] as const;

/** Produce and meat workspaces keep their diagnostic pages; they are secondary, not primary. */
const PRODUCE_SECONDARY = [
  { href: "/overview", label: "Diagnostic summary" },
  { href: "/inventory", label: "Inventory risk" },
  { href: "/atp", label: "Available for customers" },
  { href: "/traceability", label: "Traceability" },
  { href: "/partners", label: "Partners" },
  { href: "/forecasts", label: "Demand forecast" },
  { href: "/supply-risk", label: "Supply risk" },
];

function current(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(href + "/");
}

function NavCount({ href }: { href: string }) {
  const open = useOpenDecisions();
  if (href !== "/decisions" || !open.length) return null;
  return <span className="ws-nav-count" aria-label={`${open.length} awaiting review`}>{open.length}</span>;
}

function Account() {
  const session = useSession();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!(e.target as HTMLElement).closest("[data-account]")) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("click", close);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("click", close); document.removeEventListener("keydown", esc); };
  }, [open]);

  return (
    <div data-account style={{ position: "relative" }}>
      <button className="zb zb--tertiary zb--sm" aria-expanded={open} aria-haspopup="menu" onClick={() => setOpen((o) => !o)}>
        {session.workspace?.name ?? "Workspace"}
        <ChevronDown size={13} aria-hidden />
      </button>
      {open && (
        <div role="menu" style={{
          position: "absolute", insetInlineEnd: 0, top: "calc(100% + 6px)", zIndex: 50, minWidth: 232,
          background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius)",
          boxShadow: "var(--shadow-lg)", padding: 6,
        }}>
          <div style={{ padding: "8px 10px 10px", borderBottom: "1px solid var(--line-soft)" }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--ink-950)" }}>{session.workspace?.organisation}</div>
            <div style={{ fontSize: 12, color: "var(--ink-500)" }}>
              {session.workspace?.region || "Region not set"} · {session.workspace?.sector === "commercial" ? "Commercial goods" : session.workspace?.sector === "produce" ? "Fresh produce" : "Meat and seafood"}
            </div>
          </div>
          <Link role="menuitem" href="/advanced/planner" className="zb zb--tertiary zb--sm zb--block" style={{ justifyContent: "flex-start", marginTop: 4 }} onClick={() => setOpen(false)}>
            <Wrench size={14} aria-hidden /> Advanced planner
          </Link>
          <button role="menuitem" className="zb zb--tertiary zb--sm zb--block" style={{ justifyContent: "flex-start" }}
            onClick={() => { session.signOut(); router.push("/get-started"); }}>
            <LogOut size={14} aria-hidden /> Sign out of this workspace
          </button>
        </div>
      )}
    </div>
  );
}

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const session = useSession();
  const { summary } = useWorkspaceData();
  const [palette, setPalette] = useState(false);

  useEffect(() => {
    const on = (e: KeyboardEvent) => {
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && !/input|textarea/i.test((e.target as HTMLElement)?.tagName ?? ""))) {
        e.preventDefault();
        setPalette(true);
      }
    };
    window.addEventListener("keydown", on);
    return () => window.removeEventListener("keydown", on);
  }, []);

  const secondary = session.workspace?.family === "produce" ? PRODUCE_SECONDARY : [];

  return (
    <div className="ws">
      <a className="skip-link" href="#ws-content">Skip to content</a>
      <aside className="ws-rail">
        {/* Logo renders its own link; wrapping it in another produces nested anchors. */}
        <div className="ws-rail-brand"><Logo size={21} href="/home" /></div>
        <nav className="ws-nav" aria-label="Workspace">
          {NAV.map(({ href, label, Icon }) => (
            <Link key={href} href={href} aria-current={current(pathname, href) ? "page" : undefined}>
              <Icon strokeWidth={1.7} aria-hidden /><span>{label}</span><NavCount href={href} />
            </Link>
          ))}
        </nav>
        {secondary.length > 0 && (
          <div className="ws-secondary" style={{ overflow: "auto" }}>
            <div className="ws-secondary-label">Diagnostics</div>
            <nav className="ws-nav" aria-label="Diagnostics" style={{ padding: 0 }}>
              {secondary.map((s) => (
                <Link key={s.href} href={s.href} aria-current={current(pathname, s.href) ? "page" : undefined}>
                  <span>{s.label}</span>
                </Link>
              ))}
            </nav>
          </div>
        )}
        <div className="ws-rail-foot">
          <div style={{ fontSize: 11.5, color: "var(--ink-400)", lineHeight: 1.5 }}>
            ZAAD recommends and records approvals. It never sends an order to a supplier.
          </div>
        </div>
      </aside>

      <div className="ws-main">
        <header className="ws-top">
          <div className="ws-top-id">
            <span className="ws-top-name">{session.workspace?.name ?? "Workspace"}</span>
            {summary && <span className="ws-top-sub" title={`Information set ${summary.informationHash.slice(0, 12)}`}>
              · as at {new Date(summary.asOf).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
            </span>}
          </div>
          <div className="ws-top-spacer" />
          <button className="ws-search" onClick={() => setPalette(true)} aria-label="Search suppliers, orders, products and decisions">
            <Search size={14} aria-hidden />
            <span>Search</span>
            <kbd aria-hidden>⌘K</kbd>
          </button>
          <AssistantButton label="Help" variant="tertiary" icon={<HelpCircle size={15} aria-hidden />} />
          <Account />
        </header>
        <main id="ws-content" className={pathname.startsWith("/network") ? "ws-page wide" : "ws-page"}>{children}</main>
      </div>

      <nav className="ws-tabs" aria-label="Workspace">
        {NAV.map(({ href, label, Icon }) => (
          <Link key={href} href={href} aria-current={current(pathname, href) ? "page" : undefined}>
            <Icon strokeWidth={1.7} aria-hidden /><span>{label}</span><NavCount href={href} />
          </Link>
        ))}
      </nav>

      {palette && <CommandPalette onClose={() => setPalette(false)} />}
    </div>
  );
}
