/**
 * Recent destinations: the last few pages and records a person opened, kept on this device.
 *
 * Only what is needed to navigate is stored — the destination id, or a route with a record
 * identifier and a short label the person already saw. Never a line's contents, a price or a
 * result. Bounded, de-duplicated, newest first.
 */
export interface Recent {
  /** a destination id for a page, or `record` for a dynamic entity */
  kind: "page" | "record";
  id: string;
  route: string;
  label: string;
  at: number;
}

export const MAX_RECENTS = 8;

const ROUTE = /^\/[A-Za-z0-9\-_\/%.?=&]{0,240}$/;

export function pushRecent(list: Recent[], entry: Omit<Recent, "at">, now = Date.now()): Recent[] {
  if (!ROUTE.test(entry.route)) return list;
  const label = String(entry.label).slice(0, 80);
  const next: Recent = { ...entry, label, at: now };
  return [next, ...list.filter((r) => !(r.kind === entry.kind && r.id === entry.id))].slice(0, MAX_RECENTS);
}

export function loadRecents(workspace: string, storage: Pick<Storage, "getItem"> | null = typeof window === "undefined" ? null : window.localStorage): Recent[] {
  try {
    const raw = storage?.getItem(`zaad.recents.${workspace}`);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter((r): r is Recent => r && typeof r === "object" && (r.kind === "page" || r.kind === "record") && typeof r.id === "string" && typeof r.route === "string" && ROUTE.test(r.route))
      .map((r) => ({ kind: r.kind, id: String(r.id).slice(0, 120), route: r.route, label: String(r.label ?? r.id).slice(0, 80), at: Number(r.at) || 0 }))
      .slice(0, MAX_RECENTS);
  } catch { return []; }
}

export function saveRecents(workspace: string, list: Recent[], storage: Pick<Storage, "setItem"> | null = typeof window === "undefined" ? null : window.localStorage): void {
  try { storage?.setItem(`zaad.recents.${workspace}`, JSON.stringify(list.slice(0, MAX_RECENTS))); } catch { /* best effort */ }
}
