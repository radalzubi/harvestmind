"use client";

/**
 * The workspace chrome, drawn from one destination registry.
 *
 * The desktop rail, the phone tabs and the More sheet are three views of `lib/commands/
 * destinations.ts`, filtered by device, capability and workspace family. Pinned pages sit above
 * the groups; the phone's tabs are the person's quick actions. The command palette, the keyboard
 * shortcuts and the shortcut help come from the same registry through the command centre, so a
 * page added there is reachable everywhere at once.
 *
 *   OPERATE   what needs me, what do I have, what have I ordered
 *   ANALYSE   how does my network connect, why is performance changing, explore, dashboards, ask
 *   DATA      bring information in, then inspect what ZAAD holds
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import {
  Activity, BarChart3, Boxes, ChevronDown, Compass, Database, FileText, HelpCircle, History, Home, Keyboard, KeyRound, LayoutDashboard, LayoutList, LogOut,
  MessageSquareText, MoreHorizontal, Pin, Search, Share2, ShieldCheck, Stethoscope, TrendingUp, Truck, Upload, Users, Wrench,
} from "lucide-react";
import { Logo } from "@/components/site/Logo";
import { useSession } from "@/lib/session";
import { useLocale } from "@/lib/i18n";
import { DATE } from "@/lib/zaad/product";
import { useOpenDecisions, useWorkspaceData } from "@/lib/zaad/workspace-data";
import { AssistantButton } from "@/components/Assistant";
import { CommandProvider, useCommands } from "@/lib/commands";
import { PRIMARY_GROUPS, group as groupOf, visible, type Destination } from "@/lib/commands/destinations";
import { CommandPalette } from "./CommandPalette";
import { ShortcutHelp } from "./ShortcutHelp";

export const ICONS: Record<string, LucideIcon> = {
  Home, LayoutList, Boxes, FileText, BarChart3, Compass, LayoutDashboard, MessageSquareText, Share2, Stethoscope, History, Upload, Database, Wrench, Keyboard, KeyRound,
  Activity, ShieldCheck, Users, TrendingUp, Truck,
};

function current(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(href + "/");
}

function NavCount({ href }: { href: string }) {
  const open = useOpenDecisions();
  if (href !== "/decisions" || !open.length) return null;
  return <span className="ws-nav-count" aria-label={`${open.length} awaiting review`}>{open.length}</span>;
}

function DestinationLink({ d, pathname, label, short }: { d: Destination; pathname: string; label: string; short?: boolean }) {
  const Icon = ICONS[d.icon] ?? Home;
  return (
    <Link href={d.route} aria-current={current(pathname, d.route) ? "page" : undefined}>
      <Icon strokeWidth={1.7} aria-hidden /><span>{label}</span>{!short && <NavCount href={d.route} />}{short && <NavCount href={d.route} />}
    </Link>
  );
}

function Account() {
  const session = useSession();
  const router = useRouter();
  const { t } = useLocale();
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
        <div role="menu" style={{ position: "absolute", insetInlineEnd: 0, top: "calc(100% + 6px)", zIndex: 50, minWidth: 232, background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius)", boxShadow: "var(--shadow-lg)", padding: 6 }}>
          <div style={{ padding: "8px 10px 10px", borderBottom: "1px solid var(--line-soft)" }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--ink-950)" }}>{session.workspace?.organisation}</div>
            <div style={{ fontSize: 12, color: "var(--ink-500)" }}>
              {session.workspace?.region || "Region not set"} · {session.workspace?.sector === "commercial" ? "Commercial goods" : session.workspace?.sector === "produce" ? "Fresh produce" : "Meat and seafood"}
            </div>
          </div>
          <Link role="menuitem" href="/orders/formats" className="zb zb--tertiary zb--sm zb--block" style={{ justifyContent: "flex-start", marginTop: 4 }} onClick={() => setOpen(false)}>
            <FileText size={14} aria-hidden /> {t.workspace.nav.orderFormats}
          </Link>
          <Link role="menuitem" href="/advanced/planner" className="zb zb--tertiary zb--sm zb--block" style={{ justifyContent: "flex-start" }} onClick={() => setOpen(false)}>
            <Wrench size={14} aria-hidden /> {t.workspace.nav.advancedPlanner}
          </Link>
          <Link role="menuitem" href="/settings/shortcuts" className="zb zb--tertiary zb--sm zb--block" style={{ justifyContent: "flex-start" }} onClick={() => setOpen(false)}>
            <Keyboard size={14} aria-hidden /> {t.workspace.nav.shortcuts}
          </Link>
          <button role="menuitem" className="zb zb--tertiary zb--sm zb--block" style={{ justifyContent: "flex-start" }} onClick={() => { session.signOut(); router.push("/get-started"); }}>
            <LogOut size={14} aria-hidden /> Sign out of this workspace
          </button>
        </div>
      )}
    </div>
  );
}

function MoreSheet({ pathname, onClose, items, label }: { pathname: string; onClose: () => void; items: Destination[]; label: (d: Destination) => string }) {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [onClose]);
  return (
    <>
      <div className="drw-scrim" onClick={onClose} aria-hidden />
      <nav className="ws-more" aria-label="More destinations">
        {items.map((d) => { const Icon = ICONS[d.icon] ?? Home; return (
          <Link key={d.id} href={d.route} onClick={onClose} aria-current={current(pathname, d.route) ? "page" : undefined}>
            <Icon strokeWidth={1.7} aria-hidden /><span>{label(d)}</span>
          </Link>
        ); })}
      </nav>
    </>
  );
}

function WorkspaceChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const session = useSession();
  const { summary } = useWorkspaceData();
  const { t, locale, setLocale } = useLocale();
  const w = t.workspace;
  const cmd = useCommands();
  const [more, setMore] = useState(false);
  useEffect(() => { setMore(false); }, [pathname]);

  // the desktop rail always shows the desktop registry; the phone bar shows the quick actions
  const railVisibility = { ...cmd.visibility, device: "desktop" as const };
  const groups = PRIMARY_GROUPS.map((g) => ({ key: g, items: groupOf(railVisibility, g) })).filter((g) => g.items.length);
  const secondary = groupOf(railVisibility, "secondary").filter((d) => d.families);
  const tabs = cmd.quickActions;
  const moreItems = visible({ ...cmd.visibility, device: "phone" }).filter((d) => !tabs.some((q) => q.id === d.id) && d.group !== "settings");
  const paletteHint = cmd.display("OPEN_COMMAND_PALETTE");
  const showKbd = cmd.profile.keyboard && cmd.profile.device !== "phone";

  return (
    <div className="ws" data-chord={cmd.pendingChord ? "armed" : undefined}>
      <a className="skip-link" href="#ws-content">{w.skip}</a>
      <aside className="ws-rail">
        <div className="ws-rail-brand"><Logo size={21} href="/home" /></div>
        <div className="ws-rail-scroll">
          {cmd.pinned.length > 0 && (
            <div>
              <div className="ws-secondary-label"><Pin size={11} aria-hidden style={{ verticalAlign: -1 }} /> {w.groups.pinned}</div>
              <nav className="ws-nav" aria-label={w.groups.pinned}>
                {cmd.pinned.map((d) => <DestinationLink key={d.id} d={d} pathname={pathname} label={cmd.label(d)} />)}
              </nav>
            </div>
          )}
          {groups.map((g) => (
            <div key={g.key}>
              {g.key !== "operate" && <div className="ws-secondary-label">{w.groups[g.key]}</div>}
              <nav className="ws-nav" aria-label={w.groups[g.key]}>
                {g.items.map((d) => <DestinationLink key={d.id} d={d} pathname={pathname} label={cmd.label(d)} />)}
              </nav>
            </div>
          ))}
          {secondary.length > 0 && (
            <div className="ws-secondary">
              <div className="ws-secondary-label">Fresh produce</div>
              <nav className="ws-nav" aria-label="Fresh produce" style={{ padding: 0 }}>
                {secondary.map((d) => <Link key={d.id} href={d.route} aria-current={current(pathname, d.route) ? "page" : undefined}><span>{cmd.label(d)}</span></Link>)}
              </nav>
            </div>
          )}
        </div>
        <div className="ws-rail-foot">
          <div style={{ fontSize: 11.5, color: "var(--ink-500)", lineHeight: 1.5 }}>{w.foot}</div>
          <div style={{ display: "flex", gap: 6, marginTop: 8, flexWrap: "wrap" }}>
            <button type="button" className="zb zb--tertiary zb--sm" lang={locale === "ar" ? "en" : "ar"} aria-label={w.langLabel} onClick={() => setLocale(locale === "ar" ? "en" : "ar")}>{w.lang}</button>
            {showKbd && <button type="button" className="zb zb--tertiary zb--sm" aria-label={t.commands.keyboardShortcuts} title={`${t.commands.keyboardShortcuts} (${cmd.display("SHOW_SHORTCUTS")})`} onClick={cmd.openHelp}><Keyboard size={14} aria-hidden /></button>}
          </div>
        </div>
      </aside>

      <div className="ws-main">
        <header className="ws-top">
          <div className="ws-top-id">
            <span className="ws-top-name">{session.workspace?.name ?? "Workspace"}</span>
            {summary && <span className="ws-top-sub" title={`Information set ${summary.informationHash.slice(0, 12)}`}>· {w.asAt} <span className="fig">{DATE(summary.asOf)}</span></span>}
          </div>
          <div className="ws-top-spacer" />
          <button className="ws-search" onClick={cmd.openPalette} aria-label={w.searchLabel} aria-keyshortcuts={showKbd ? paletteHint : undefined}>
            <Search size={14} aria-hidden />
            <span>{w.search}</span>
            {showKbd && paletteHint && <kbd aria-hidden>{paletteHint}</kbd>}
          </button>
          <AssistantButton label={w.help} variant="tertiary" icon={<HelpCircle size={15} aria-hidden />} />
          <Account />
        </header>
        <main id="ws-content" tabIndex={-1} className={pathname.startsWith("/network") ? "ws-page wide" : "ws-page"}>{children}</main>
      </div>

      <nav className="ws-tabs" aria-label="Workspace">
        {tabs.map((d) => { const Icon = ICONS[d.icon] ?? Home; return (
          <Link key={d.id} href={d.route} aria-current={current(pathname, d.route) ? "page" : undefined}>
            <Icon strokeWidth={1.7} aria-hidden /><span>{d.id === "orders" ? w.nav.ordersShort : cmd.label(d)}</span><NavCount href={d.route} />
          </Link>
        ); })}
        <button type="button" onClick={() => setMore((m) => !m)} aria-expanded={more} aria-current={moreItems.some((m) => current(pathname, m.route)) ? "page" : undefined}>
          <MoreHorizontal strokeWidth={1.7} aria-hidden /><span>{w.nav.more}</span>
        </button>
      </nav>

      {more && <MoreSheet pathname={pathname} onClose={() => setMore(false)} items={moreItems} label={cmd.label} />}
      {cmd.paletteOpen && <CommandPalette onClose={cmd.closePalette} />}
      {cmd.helpOpen && <ShortcutHelp onClose={cmd.closeHelp} />}
      {cmd.pendingChord && <div className="ws-chord" role="status">{t.commands.chordArmed}</div>}
    </div>
  );
}

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  return <CommandProvider><WorkspaceChrome>{children}</WorkspaceChrome></CommandProvider>;
}
