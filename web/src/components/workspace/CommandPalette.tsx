"use client";

/**
 * Search across what the workspace actually holds.
 *
 * Two sources, deliberately. What the *plan* holds — decisions, the products it covered, the open
 * orders it evaluated — is already in the browser and matched instantly. Everything else is asked
 * of the server, because a catalogue of fifty thousand products cannot live in a React state and a
 * buyer searching for one of them should not be limited to the bounded set the last run happened
 * to cover.
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Box, Building2, FileText, MapPin, Share2, Users } from "lucide-react";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { searchWorkspace, type SearchHit } from "@/lib/zaad/product";

type Hit = { id: string; label: string; meta: string; href: string; Icon: typeof Box; rank: number };

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
  const { request, decisions, network } = useWorkspaceData();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);
  const [remote, setRemote] = useState<SearchHit[]>([]);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => { input.current?.focus(); }, []);

  // The whole catalogue, from the server, debounced. A failure here narrows the results to what
  // the plan holds rather than emptying the palette.
  useEffect(() => {
    const needle = q.trim();
    if (needle.length < 2) { setRemote([]); return; }
    let alive = true;
    const handle = window.setTimeout(() => {
      searchWorkspace(needle, 8)
        .then((r) => { if (alive) setRemote(r.results); })
        .catch(() => { if (alive) setRemote([]); });
    }, 180);
    return () => { alive = false; window.clearTimeout(handle); };
  }, [q]);

  const local = useMemo<Hit[]>(() => {
    const needle = q.trim();
    if (!needle) return [];
    const out: Hit[] = [];
    for (const d of decisions) {
      const s = score(needle, d.headline, d.target.label, d.target.id, d.category);
      if (s) out.push({ id: d.id, label: d.headline, meta: d.category, href: `/decisions?decision=${encodeURIComponent(d.id)}`, Icon: FileText, rank: s + 1 });
    }
    for (const n of network?.nodes ?? []) {
      // A node matches on its own name, or because it handles the product being searched for. Both
      // are worth showing — but typing a product code and getting back "DC · Site" with no reason
      // reads as noise, so a match on the product says so, and ranks below the product itself.
      const byName = score(needle, n.name, n.id.split(":")[1] ?? "");
      const carried = byName ? null : (n.skus ?? []).find((sku) => score(needle, sku) >= 3) ?? null;
      if (!byName && !carried) continue;
      const Icon = n.kind === "supplier" ? Building2 : n.kind === "customer" ? Users : n.kind === "port" ? MapPin : Share2;
      const kind = n.kind === "supplier" ? "Supplier" : n.kind === "customer" ? "Customer" : n.kind === "port" ? "Port" : n.kind === "branch" ? "Branch" : "Site";
      out.push({
        id: n.id, label: n.name, meta: carried ? `${kind} · handles ${carried}` : kind,
        href: `/network?node=${encodeURIComponent(n.id)}`, Icon, rank: byName || 0.5,
      });
    }
    for (const po of request?.pipeline ?? []) {
      const s = score(needle, po.id, po.id.replace(/^PO-?/i, ""));
      if (s) out.push({ id: po.id, label: po.id, meta: `Open order · ${po.stage.replaceAll("_", " ").toLowerCase()}`, href: `/decisions?decision=${encodeURIComponent(`po:${po.id}`)}`, Icon: FileText, rank: s + 1 });
    }
    for (const sku of request?.skus ?? []) {
      const s = score(needle, sku.id);
      if (s) out.push({ id: sku.id, label: sku.id, meta: "Product", href: `/network?sku=${encodeURIComponent(sku.id)}`, Icon: Box, rank: s });
    }
    return out;
  }, [q, decisions, network, request]);

  const REMOTE_ICON: Record<string, typeof Box> = {
    product: Box, supplier: Building2, order: FileText, customer: Users,
  };
  const REMOTE_META: Record<string, string> = {
    product: "Product", supplier: "Supplier", order: "Purchase order", customer: "Customer",
  };

  const hits = useMemo<Hit[]>(() => {
    const out: Hit[] = [...local];
    for (const hit of remote) {
      out.push({
        id: `${hit.kind}:${hit.id}`, label: hit.label || hit.id,
        meta: hit.detail ? `${REMOTE_META[hit.kind] ?? hit.kind} · ${hit.detail}` : (REMOTE_META[hit.kind] ?? hit.kind),
        href: hit.href, Icon: REMOTE_ICON[hit.kind] ?? Box, rank: 1.5,
      });
    }
    const seen = new Set<string>();
    return out
      .sort((a, b) => b.rank - a.rank || a.label.localeCompare(b.label))
      .filter((h) => {
        const key = h.label.toLowerCase();
        return seen.has(key) ? false : (seen.add(key), true);
      })
      .slice(0, 10);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [local, remote]);

  const go = (hit: Hit | undefined) => {
    if (!hit) return;
    router.push(hit.href);
    onClose();
  };

  return (
    <div
      role="dialog" aria-modal="true" aria-label="Search"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      style={{ position: "fixed", inset: 0, zIndex: 80, background: "rgba(24,24,27,.3)", display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "12vh 16px 16px" }}
    >
      <div style={{ width: "min(620px, 100%)", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-lg)", boxShadow: "var(--shadow-lg)", overflow: "hidden" }}>
        <input
          ref={input} value={q} onChange={(e) => { setQ(e.target.value); setActive(0); }}
          placeholder="Search products, suppliers, orders, customers and decisions"
          aria-label="Search products, suppliers, orders, customers and decisions"
          aria-activedescendant={hits[active] ? `hit-${active}` : undefined}
          onKeyDown={(e) => {
            if (e.key === "Escape") { e.preventDefault(); onClose(); }
            if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(a + 1, hits.length - 1)); }
            if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)); }
            if (e.key === "Enter") { e.preventDefault(); go(hits[active]); }
          }}
          style={{ width: "100%", border: 0, borderBottom: "1px solid var(--line)", padding: "15px 18px", fontSize: 15, fontFamily: "inherit", outline: "none", background: "transparent", color: "var(--ink-950)" }}
        />
        {q.trim() !== "" && (
          <ul role="listbox" aria-label="Results" style={{ listStyle: "none", margin: 0, padding: 6, maxHeight: "46vh", overflow: "auto" }}>
            {hits.length === 0 && <li style={{ padding: "14px 12px", fontSize: 13, color: "var(--ink-500)" }}>Nothing in this workspace matches “{q.trim()}”.</li>}
            {hits.map((h, i) => (
              <li key={h.id} id={`hit-${i}`} role="option" aria-selected={i === active}>
                <button
                  onMouseEnter={() => setActive(i)} onClick={() => go(h)}
                  className="zb zb--tertiary zb--block"
                  style={{ justifyContent: "flex-start", height: 42, background: i === active ? "var(--ink-100)" : undefined }}
                >
                  <h.Icon size={15} aria-hidden />
                  <span style={{ color: "var(--ink-950)", overflow: "hidden", textOverflow: "ellipsis" }}>{h.label}</span>
                  <span style={{ marginInlineStart: "auto", fontSize: 12, color: "var(--ink-500)", fontWeight: 400 }}>{h.meta}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
        <div style={{ borderTop: "1px solid var(--line-soft)", padding: "8px 14px", fontSize: 11.5, color: "var(--ink-400)", display: "flex", gap: 14 }}>
          <span>↑↓ to move</span><span>↵ to open</span><span>esc to close</span>
        </div>
      </div>
    </div>
  );
}
