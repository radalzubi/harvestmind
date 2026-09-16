"use client";

/**
 * The workspace chrome: eight destinations in three groups, the workspace you are in, and help
 * that does not compete with the work.
 *
 * Four destinations were too few once ZAAD held stock, orders, suppliers and proposals: everything
 * that was not Home, Decisions or Network ended up inside Data, which is the one place nobody
 * looks for an operating task. The groups name the job rather than the feature —
 *
 *   OPERATE   what needs me, what do I have, what have I ordered
 *   ANALYZE   how does my network connect, why is performance changing
 *   DATA      bring information in, then inspect what ZAAD holds
 *
 * — and no group is a dumping ground. Upload comes before Data because that is the order the work
 * happens in. Optimizer phase names appear nowhere.
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3, Boxes, ChevronDown, Database, FileText, HelpCircle, History, Home, LayoutList, LogOut, MoreHorizontal,
  Search, Share2, Stethoscope, Upload, Wrench,
} from "lucide-react";
import { Logo } from "@/components/site/Logo";
import { useSession } from "@/lib/session";
import { useLocale, type Copy } from "@/lib/i18n";
import { DATE } from "@/lib/zaad/product";
import { useOpenDecisions, useWorkspaceData } from "@/lib/zaad/workspace-data";
import { AssistantButton } from "@/components/Assistant";
import { CommandPalette } from "./CommandPalette";

interface Destination { href: string; label: string; key: keyof Copy["workspace"]["nav"]; Icon: typeof Home }

const OPERATE: Destination[] = [
  { href: "/home", label: "Home", key: "home", Icon: Home },
  { href: "/decisions", label: "Decisions", key: "decisions", Icon: LayoutList },
  { href: "/inventory", label: "Inventory", key: "inventory", Icon: Boxes },
  { href: "/orders", label: "Purchase orders", key: "orders", Icon: FileText },
];
const ANALYZE: Destination[] = [
  { href: "/insights", label: "Insights", key: "insights", Icon: BarChart3 },
  { href: "/network", label: "Network", key: "network", Icon: Share2 },
  { href: "/diagnostics", label: "Diagnostics", key: "diagnostics", Icon: Stethoscope },
  { href: "/history", label: "History", key: "history", Icon: History },
];
const DATA: Destination[] = [
  { href: "/upload", label: "Upload", key: "upload", Icon: Upload },
  { href: "/data", label: "Data", key: "data", Icon: Database },
];

const GROUPS: Array<{ label: string | null; key: keyof Copy["workspace"]["groups"]; items: Destination[] }> = [
  { label: null, key: "operate", items: OPERATE },
  { label: "Analyse", key: "analyse", items: ANALYZE },
  { label: "Data", key: "data", items: DATA },
];

/** The phone bar: the four things a person opens most, and everything else behind More. */
const TABS = OPERATE;
const MORE = [...ANALYZE, ...DATA];

/** Produce and meat workspaces keep their older diagnostic pages; they are secondary, not primary. */
const PRODUCE_SECONDARY = [
  { href: "/overview", label: "Diagnostic summary" },
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
          <Link role="menuitem" href="/orders/formats" className="zb zb--tertiary zb--sm zb--block" style={{ justifyContent: "flex-start", marginTop: 4 }} onClick={() => setOpen(false)}>
            <FileText size={14} aria-hidden /> Order export formats
          </Link>
          <Link role="menuitem" href="/advanced/planner" className="zb zb--tertiary zb--sm zb--block" style={{ justifyContent: "flex-start" }} onClick={() => setOpen(false)}>
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

function MoreSheet({ pathname, onClose }: { pathname: string; onClose: () => void }) {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [onClose]);
  return (
    <>
      <div className="drw-scrim" onClick={onClose} aria-hidden />
      <nav className="ws-more" aria-label="More destinations">
        {MORE.map(({ href, label, Icon }) => (
          <Link key={href} href={href} onClick={onClose} aria-current={current(pathname, href) ? "page" : undefined}>
            <Icon strokeWidth={1.7} aria-hidden /><span>{label}</span>
          </Link>
        ))}
      </nav>
    </>
  );
}

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const session = useSession();
  const { summary } = useWorkspaceData();
  const { t, locale, setLocale } = useLocale();
  const w = t.workspace;
  const [palette, setPalette] = useState(false);
  const [more, setMore] = useState(false);

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

  useEffect(() => { setMore(false); }, [pathname]);

  const secondary = session.workspace?.family === "produce" ? PRODUCE_SECONDARY : [];

  return (
    <div className="ws">
      <a className="skip-link" href="#ws-content">{w.skip}</a>
      <aside className="ws-rail">
        {/* Logo renders its own link; wrapping it in another produces nested anchors. */}
        <div className="ws-rail-brand"><Logo size={21} href="/home" /></div>
        <div className="ws-rail-scroll">
          {GROUPS.map((group) => (
            <div key={group.key}>
              {group.label && <div className="ws-secondary-label">{w.groups[group.key]}</div>}
              <nav className="ws-nav" aria-label={w.groups[group.key]}>
                {group.items.map(({ href, key, Icon }) => (
                  <Link key={href} href={href} aria-current={current(pathname, href) ? "page" : undefined}>
                    <Icon strokeWidth={1.7} aria-hidden /><span>{w.nav[key]}</span><NavCount href={href} />
                  </Link>
                ))}
              </nav>
            </div>
          ))}
          {secondary.length > 0 && (
            <div className="ws-secondary">
              <div className="ws-secondary-label">Fresh produce</div>
              <nav className="ws-nav" aria-label="Fresh produce" style={{ padding: 0 }}>
                {secondary.map((s) => (
                  <Link key={s.href} href={s.href} aria-current={current(pathname, s.href) ? "page" : undefined}>
                    <span>{s.label}</span>
                  </Link>
                ))}
              </nav>
            </div>
          )}
        </div>
        <div className="ws-rail-foot">
          <div style={{ fontSize: 11.5, color: "var(--ink-500)", lineHeight: 1.5 }}>{w.foot}</div>
          <button type="button" className="zb zb--tertiary zb--sm" style={{ marginTop: 8 }} lang={locale === "ar" ? "en" : "ar"}
            aria-label={w.langLabel} onClick={() => setLocale(locale === "ar" ? "en" : "ar")}>{w.lang}</button>
        </div>
      </aside>

      <div className="ws-main">
        <header className="ws-top">
          <div className="ws-top-id">
            <span className="ws-top-name">{session.workspace?.name ?? "Workspace"}</span>
            {summary && <span className="ws-top-sub" title={`Information set ${summary.informationHash.slice(0, 12)}`}>
              {/* One formatter for one field: DATE() reads it in UTC, the way it is stated. */}
              · {w.asAt} <span className="fig">{DATE(summary.asOf)}</span>
            </span>}
          </div>
          <div className="ws-top-spacer" />
          <button className="ws-search" onClick={() => setPalette(true)} aria-label={w.searchLabel}>
            <Search size={14} aria-hidden />
            <span>{w.search}</span>
            <kbd aria-hidden>⌘K</kbd>
          </button>
          <AssistantButton label={w.help} variant="tertiary" icon={<HelpCircle size={15} aria-hidden />} />
          <Account />
        </header>
        {/* tabIndex -1 keeps this out of the tab order but lets it *take* focus, which is the
            whole point of the skip link: without it the link scrolls the page and the keyboard
            stays where it was, so the next Tab goes to the second nav item rather than the page. */}
        <main id="ws-content" tabIndex={-1}
          className={pathname.startsWith("/network") ? "ws-page wide" : "ws-page"}>{children}</main>
      </div>

      <nav className="ws-tabs" aria-label="Workspace">
        {TABS.map(({ href, key, Icon }) => (
          <Link key={href} href={href} aria-current={current(pathname, href) ? "page" : undefined}>
            <Icon strokeWidth={1.7} aria-hidden /><span>{key === "orders" ? w.nav.ordersShort : w.nav[key]}</span><NavCount href={href} />
          </Link>
        ))}
        <button type="button" onClick={() => setMore((m) => !m)} aria-expanded={more}
          aria-current={MORE.some((m) => current(pathname, m.href)) ? "page" : undefined}>
          <MoreHorizontal strokeWidth={1.7} aria-hidden /><span>{w.nav.more}</span>
        </button>
      </nav>

      {more && <MoreSheet pathname={pathname} onClose={() => setMore(false)} />}
      {palette && <CommandPalette onClose={() => setPalette(false)} />}
    </div>
  );
}
