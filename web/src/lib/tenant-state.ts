/**
 * Tenant-scoped browser state, and the one place that clears it (security review 2026-09, SEC-038).
 *
 * The interface keeps a little state in the browser for convenience: the credential for this tab,
 * the workspace's sector, the last pages and records a person opened, their pinned destinations
 * and shortcut bindings, and which columns they hid on a dataset. Every one of those belongs to
 * the workspace it was written in. When the credential changes hands — a sign-out, an access link
 * for another workspace, a credential the server no longer accepts — all of it goes, in one call,
 * before anything of the next workspace is stored. Only genuinely personal, workspace-free
 * preferences (the interface language) survive.
 *
 * Everything here takes its storage as a parameter so the rules are testable without a browser;
 * the defaults are the window's stores.
 */

/** Session-storage keys that hold the credential or a fact about the signed-in workspace. */
export const TENANT_SESSION_KEYS = ["harvestmind.operator-token", "harvestmind.sector"] as const;

/** Local-storage key prefixes whose values are written for one workspace (the operator id follows the prefix). */
export const TENANT_LOCAL_PREFIXES = [
  "zaad.recents.",      // recent pages and records (ids, routes, short labels)
  "zaad.prefs.user.",   // pinned destinations, quick actions, shortcut bindings
  "zaad.prefs.device.", // device-level binding overrides
  "zaad.data.hidden.",  // hidden columns per dataset
] as const;

/** Keys that are the person's, not a workspace's, and survive a switch. */
export const GLOBAL_LOCAL_KEYS = ["zaad.locale"] as const;

/** Fired on `window` after tenant state is cleared, so in-memory holders (recents, toasts) drop theirs too. */
export const TENANT_RESET_EVENT = "harvestmind-tenant-reset";

export interface TenantStores {
  local: Pick<Storage, "length" | "key" | "removeItem"> | null;
  session: Pick<Storage, "removeItem"> | null;
}

function windowStores(): TenantStores {
  if (typeof window === "undefined") return { local: null, session: null };
  let local: TenantStores["local"] = null;
  let session: TenantStores["session"] = null;
  try { local = window.localStorage; } catch { /* storage blocked */ }
  try { session = window.sessionStorage; } catch { /* storage blocked */ }
  return { local, session };
}

export function isTenantLocalKey(key: string): boolean {
  return TENANT_LOCAL_PREFIXES.some((prefix) => key.startsWith(prefix));
}

/**
 * Remove every tenant-scoped key from both stores and tell in-memory holders to reset.
 * Returns the keys removed (for tests and for the reset event's detail). Never throws: a
 * blocked store is treated as already empty.
 */
export function clearTenantClientState(stores: TenantStores = windowStores(), notify = typeof window !== "undefined"): string[] {
  const removed: string[] = [];
  if (stores.session) {
    for (const key of TENANT_SESSION_KEYS) {
      try { stores.session.removeItem(key); removed.push(key); } catch { /* storage unavailable */ }
    }
  }
  if (stores.local) {
    try {
      const stale: string[] = [];
      for (let i = 0; i < stores.local.length; i += 1) {
        const key = stores.local.key(i);
        if (key && isTenantLocalKey(key)) stale.push(key);
      }
      for (const key of stale) { stores.local.removeItem(key); removed.push(key); }
    } catch { /* storage unavailable */ }
  }
  if (notify) {
    try { window.dispatchEvent(new CustomEvent(TENANT_RESET_EVENT, { detail: { removed } })); } catch { /* no window */ }
  }
  return removed;
}

export type CredentialCheck = (candidate: string) => Promise<boolean>;

export interface SwitchResult {
  /** `accepted`: the candidate authenticates and is now the session's credential. `refused`: it does not, and nothing changed. */
  outcome: "accepted" | "refused" | "empty";
  /** the tenant-scoped keys cleared before the new credential was stored (empty unless accepted) */
  cleared: string[];
}

/**
 * Replace the session's credential with `candidate` — but only once the server has accepted it.
 *
 * Order matters and is the whole point: validate first, with the candidate alone (never the stored
 * credential); if refused, touch nothing, so a person signed in to workspace A who opens a dead
 * link for workspace B is still signed in to A and told the link was refused; if accepted, clear
 * every trace of the previous workspace, then store the candidate. There is no instant in which
 * B's credential and A's recents, sector or hidden-column choices coexist.
 */
export async function switchCredential(candidate: string, check: CredentialCheck, store: (token: string) => void,
                                       stores: TenantStores = windowStores()): Promise<SwitchResult> {
  const cleaned = candidate.trim();
  if (!cleaned) return { outcome: "empty", cleared: [] };
  let ok = false;
  try { ok = await check(cleaned); } catch { ok = false; }
  if (!ok) return { outcome: "refused", cleared: [] };
  const cleared = clearTenantClientState(stores);
  store(cleaned);
  return { outcome: "accepted", cleared };
}
