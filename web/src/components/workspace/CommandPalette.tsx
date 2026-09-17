"use client";

/**
 * The command centre: NAVIGATE, SEARCH, ACT from one box.
 *
 * Before anyone types: pinned pages, recent pages and records, then every page this person may
 * open. As they type: pages match on label, id and keywords; records come from what the plan holds
 * (matched instantly) and from the server's bounded search over the whole catalogue (debounced);
 * actions match on their labels. Every hit shows its shortcut on this platform. Arrow keys move,
 * Enter opens, Escape closes and puts focus back where it was.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import { Box, Building2, Clock, FileText, Keyboard, MapPin, Pin, Play, Share2, Users, Languages } from "lucide-react";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { useLocale } from "@/lib/i18n";
import { STATE_LABEL, listDrafts, searchWorkspace, type SearchHit } from "@/lib/zaad/product";
import { useCommands } from "@/lib/commands";
import { search as searchDestinations, type Destination } from "@/lib/commands/destinations";
import { COMMANDS, commandForDestination } from "@/lib/commands/shortcuts";
import { ICONS } from "./Shell";

type Hit = { id: string; label: string; meta: string; group: "pages" | "recent" | "pinned" | "records" | "actions"; Icon: LucideIcon; rank: number; run: () => void; shortcut?: string; pinnable?: Destination };

function score(needle: string, ...hay: string[]): number {
  const q = needle.toLowerCase();
  let best = 0;
  for (const h of hay) {
    const s = (h ?? "").toLowerCase();
    if (!s) continue;
    if (s === q) best = Math.max(best, 4);
    else if (s.startsWith(q)) best = Math.max(best, 3);
    else if (s.includes(q)) best = Math.max(best, 2);
  }
  return best;
}

export function CommandPalette({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const { t } = useLocale();
  const copy = t.commands;
  const cmd = useCommands();
  const { request, decisions, network } = useWorkspaceData();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const [remote, setRemote] = useState<SearchHit[]>([]);
  const input = useRef<HTMLInputElement>(null);
  const opener = useRef<HTMLElement | null>(null);
  const navigated = useRef(false);

  useEffect(() => {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    input.current?.focus();
    return () => {
      const back = opener.current;
      if (!navigated.current && back?.isConnected) back.focus();
      opener.current = null;
    };
  }, []);

  useEffect(() => {
    const needle = q.trim();
    if (needle.length < 2) { setRemote([]); return; }
    let alive = true;
    const handle = window.setTimeout(() => {
      Promise.all([
        searchWorkspace(needle, 8).then((r) => r.results).catch(() => []),
        listDrafts({ q: needle, limit: 5, sort: "updated_at", direction: "desc" }).then((r) => r.rows.map((d) => ({
          kind: "proposal", id: d.draft_id, label: d.reference || d.draft_id.replace(/^draft_/, ""),
          detail: `${STATE_LABEL[d.state]}${d.supplier_id ? ` · ${d.supplier_id}` : ""}`, href: `/orders/${encodeURIComponent(d.draft_id)}`,
        }))).catch(() => []),
      ]).then(([vault, proposals]) => { if (alive) setRemote([...vault, ...proposals]); });
    }, 180);
    return () => { alive = false; window.clearTimeout(handle); };
  }, [q]);

  const go = (hit: Hit | undefined) => {
    if (!hit) return;
    navigated.current = true;
    hit.run();
    onClose();
  };
  const goRoute = (href: string) => { router.push(href); };

  const local = useMemo<Hit[]>(() => {
    const needle = q.trim();
    if (!needle) return [];
    const out: Hit[] = [];
    for (const d of decisions) {
      const s = score(needle, d.headline, d.target.label, d.target.id, d.category);
      if (s) out.push({ id: `dec:${d.id}`, label: d.headline, meta: d.category, group: "records", Icon: FileText, rank: s + 1, run: () => { cmd.rememberRecord(d.id, `/decisions?decision=${encodeURIComponent(d.id)}`, d.headline); goRoute(`/decisions?decision=${encodeURIComponent(d.id)}`); } });
    }
    for (const n of network?.nodes ?? []) {
      const byName = score(needle, n.name, n.id.split(":")[1] ?? "");
      const carried = byName ? null : (n.skus ?? []).find((sku) => score(needle, sku) >= 3) ?? null;
      if (!byName && !carried) continue;
      const Icon = n.kind === "supplier" ? Building2 : n.kind === "customer" ? Users : n.kind === "port" ? MapPin : Share2;
      const kind = n.kind === "supplier" ? "Supplier" : n.kind === "customer" ? "Customer" : n.kind === "port" ? "Port" : n.kind === "branch" ? "Branch" : "Site";
      const href = `/network?node=${encodeURIComponent(n.id)}`;
      out.push({ id: `node:${n.id}`, label: n.name, meta: carried ? `${kind} · handles ${carried}` : kind, group: "records", Icon, rank: byName || 0.5, run: () => { cmd.rememberRecord(n.id, href, n.name); goRoute(href); } });
    }
    for (const po of request?.pipeline ?? []) {
      const s = score(needle, po.id, po.id.replace(/^PO-?/i, ""));
      if (!s) continue;
      const decided = decisions.some((d) => d.id === `po:${po.id}`);
      const stage = po.stage.replaceAll("_", " ").toLowerCase();
      const href = decided ? `/decisions?decision=${encodeURIComponent(`po:${po.id}`)}` : `/orders?po=${encodeURIComponent(po.id)}`;
      out.push({ id: `po:${po.id}`, label: po.id, meta: decided ? `Open order · ${stage}` : `Open order · ${stage} · not in this plan`, group: "records", Icon: FileText, rank: s + 1, run: () => { cmd.rememberRecord(po.id, href, po.id); goRoute(href); } });
    }
    for (const sku of request?.skus ?? []) {
      const s = score(needle, sku.id);
      if (s) out.push({ id: `sku:${sku.id}`, label: sku.id, meta: "Product", group: "records", Icon: Box, rank: s, run: () => { cmd.rememberRecord(sku.id, `/network?sku=${encodeURIComponent(sku.id)}`, sku.id); goRoute(`/network?sku=${encodeURIComponent(sku.id)}`); } });
    }
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, decisions, network, request]);

  const REMOTE_ICON: Record<string, LucideIcon> = { product: Box, supplier: Building2, order: FileText, customer: Users, proposal: FileText };
  const REMOTE_META: Record<string, string> = { product: "Product", supplier: "Supplier", order: "Purchase order", customer: "Customer", proposal: "Proposal" };

  const hits = useMemo<Hit[]>(() => {
    const needle = q.trim();
    const out: Hit[] = [];
    const pageHit = (d: Destination, group: Hit["group"], rank: number): Hit => {
      const c = commandForDestination(d);
      return { id: `page:${d.id}`, label: cmd.label(d), meta: t.workspace.groups[d.group as keyof typeof t.workspace.groups] ?? d.group, group, Icon: ICONS[d.icon] ?? Box, rank,
               run: () => goRoute(d.route), shortcut: c ? cmd.display(c.id) : undefined, pinnable: d.pinnable ? d : undefined };
    };
    if (!needle) {
      for (const d of cmd.pinned) out.push(pageHit(d, "pinned", 5));
      for (const r of cmd.recents.slice(0, 5)) {
        if (r.kind === "page") { const d = searchDestinations(cmd.visibility, "").find((x) => x.destination.id === r.id)?.destination; if (d && !cmd.pinned.some((p) => p.id === d.id)) out.push({ ...pageHit(d, "recent", 4), id: `recent:${r.id}` }); }
        else out.push({ id: `recent:${r.id}`, label: r.label, meta: copy.recent, group: "recent", Icon: Clock, rank: 4, run: () => goRoute(r.route) });
      }
      for (const { destination } of searchDestinations(cmd.visibility, "")) if (!cmd.pinned.some((p) => p.id === destination.id)) out.push(pageHit(destination, "pages", 1));
      return out;
    }
    for (const { destination, rank } of searchDestinations(cmd.visibility, needle, cmd.label)) out.push(pageHit(destination, "pages", rank + 0.5));
    for (const c of COMMANDS) {
      if (c.kind === "navigate") continue;
      const label = cmd.commandLabel(c);
      const s = score(needle, label, c.id.toLowerCase().replaceAll("_", " "));
      if (!s) continue;
      if (c.id === "SEARCH" || c.id === "OPEN_COMMAND_PALETTE") continue;
      const Icon = c.id === "TOGGLE_LANGUAGE" ? Languages : c.id === "SHOW_SHORTCUTS" ? Keyboard : Play;
      out.push({ id: `cmd:${c.id}`, label, meta: copy.actions, group: "actions", Icon, rank: s, run: () => cmd.run(c.id), shortcut: cmd.display(c.id) });
    }
    out.push(...local);
    for (const hit of remote) {
      out.push({ id: `${hit.kind}:${hit.id}`, label: hit.label || hit.id, meta: hit.detail ? `${REMOTE_META[hit.kind] ?? hit.kind} · ${hit.detail}` : (REMOTE_META[hit.kind] ?? hit.kind), group: "records",
                 Icon: REMOTE_ICON[hit.kind] ?? Box, rank: 1.5, run: () => { cmd.rememberRecord(hit.id, hit.href, hit.label || hit.id); goRoute(hit.href); } });
    }
    const seen = new Set<string>();
    return out.sort((a, b) => b.rank - a.rank || a.label.localeCompare(b.label)).filter((h) => (seen.has(h.id) ? false : (seen.add(h.id), true))).slice(0, 14);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q, local, remote, cmd.pinned, cmd.recents, cmd.visibility, t]);

  const groups: Array<{ key: Hit["group"]; label: string }> = [
    { key: "pinned", label: copy.pinned }, { key: "recent", label: copy.recent }, { key: "pages", label: copy.pages }, { key: "records", label: copy.records }, { key: "actions", label: copy.actions },
  ];
  const ordered = groups.flatMap((g) => hits.filter((h) => h.group === g.key));
  const showKbd = cmd.profile.keyboard && cmd.profile.device !== "phone";

  return (
    <div role="dialog" aria-modal="true" aria-label={copy.placeholder} data-owns-keyboard="true" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
         style={{ position: "fixed", inset: 0, zIndex: 80, background: "rgba(24,24,27,.3)", display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "10vh 16px 16px" }}>
      <div className="cmd">
        <input ref={input} value={q} onChange={(e) => { setQ(e.target.value); setActive(0); }} placeholder={copy.placeholder} aria-label={copy.placeholder}
               role="combobox" aria-expanded aria-controls="cmd-list" aria-activedescendant={ordered[active] ? `hit-${active}` : undefined} aria-autocomplete="list"
               onKeyDown={(e) => {
                 if (e.key === "Escape") { e.preventDefault(); onClose(); }
                 if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, ordered.length - 1)); }
                 if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
                 if (e.key === "Enter") { e.preventDefault(); go(ordered[active]); }
               }} />
        <ul id="cmd-list" role="listbox" aria-label={copy.placeholder} className="cmd-list">
          {ordered.length === 0 && <li className="cmd-empty">{q.trim() ? `${copy.noResults} “${q.trim()}”.` : copy.typeToSearch}</li>}
          {groups.map((g) => {
            const items = ordered.filter((h) => h.group === g.key);
            if (!items.length) return null;
            return (
              <li key={g.key} role="presentation">
                <div className="cmd-group" aria-hidden>{g.label}</div>
                <ul role="group" aria-label={g.label} style={{ listStyle: "none", margin: 0, padding: 0 }}>
                  {items.map((h) => { const i = ordered.indexOf(h); return (
                    <li key={h.id} id={`hit-${i}`} role="option" aria-selected={i === active}>
                      <div className="cmd-row" data-active={i === active ? "true" : undefined} onMouseEnter={() => setActive(i)}>
                        <button type="button" className="cmd-hit" onClick={() => go(h)}>
                          <h.Icon size={15} aria-hidden />
                          <span className="cmd-label">{h.label}</span>
                          <span className="cmd-meta">{h.meta}</span>
                          {showKbd && h.shortcut && <kbd className="cmd-kbd" aria-label={h.shortcut}>{h.shortcut}</kbd>}
                        </button>
                        {h.pinnable && <button type="button" className="cmd-pin" aria-pressed={cmd.pinned.some((p) => p.id === h.pinnable!.id)} aria-label={cmd.pinned.some((p) => p.id === h.pinnable!.id) ? `${copy.unpin} ${h.label}` : `${copy.pin} ${h.label}`} onClick={(e) => { e.stopPropagation(); cmd.togglePinned(h.pinnable!.id); }}><Pin size={13} aria-hidden /></button>}
                      </div>
                    </li>
                  ); })}
                </ul>
              </li>
            );
          })}
        </ul>
        <div className="cmd-foot">
          <span>↑↓ {copy.move}</span><span>↵ {copy.open}</span><span>{copy.escToClose}</span>
          {showKbd && <button type="button" className="zb zb--tertiary zb--sm" style={{ marginInlineStart: "auto" }} onClick={() => { onClose(); cmd.openHelp(); }}><Keyboard size={13} aria-hidden /> {copy.keyboardShortcuts}</button>}
        </div>
      </div>
    </div>
  );
}
