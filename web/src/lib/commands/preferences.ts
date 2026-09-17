/**
 * Preferences, separated into what belongs to the person and what belongs to the device.
 *
 *   USER   pinned destinations, quick actions, logical shortcut overrides (`GO_INVENTORY → g i`)
 *   DEVICE nothing today beyond the detected platform; a device-specific override slot exists so
 *          a Mac binding is never blindly applied on Windows (the logical binding uses the
 *          `primary` modifier, which each platform renders and matches as its own)
 *
 * Storage is pluggable. Today: local storage on this device, keyed per workspace, so a person's
 * preferences travel with the workspace they are in and never leak between workspaces on a shared
 * machine. A server store implements the same `PreferenceStore` interface later; nothing else
 * changes. Nothing sensitive is stored: destination ids, command ids, bindings, and — for recents —
 * a route with at most a record identifier.
 */
import { DEFAULT_QUICK_ACTIONS, MAX_PINNED, MAX_QUICK_ACTIONS, byId, type Destination, type Visibility, visible } from "./destinations";
import { normaliseBinding, type BindingMap } from "./shortcuts";

export interface UserPrefs {
  pinned: string[];
  quickActions: string[];
  bindings: BindingMap;
  version: 1;
}

export interface DevicePrefs {
  /** overrides that only apply on this device's platform (empty by default) */
  bindings: BindingMap;
  version: 1;
}

export const EMPTY_USER: UserPrefs = { pinned: [], quickActions: [], bindings: {}, version: 1 };
export const EMPTY_DEVICE: DevicePrefs = { bindings: {}, version: 1 };

export interface PreferenceStore {
  loadUser(workspace: string): UserPrefs;
  saveUser(workspace: string, prefs: UserPrefs): void;
  loadDevice(workspace: string): DevicePrefs;
  saveDevice(workspace: string, prefs: DevicePrefs): void;
}

function sanitiseUser(raw: unknown): UserPrefs {
  const r = (raw && typeof raw === "object" ? raw : {}) as Partial<UserPrefs>;
  const ids = (xs: unknown, max: number) => (Array.isArray(xs) ? xs.filter((x): x is string => typeof x === "string" && Boolean(byId(x))).slice(0, max) : []);
  const bindings: BindingMap = {};
  for (const [k, v] of Object.entries((r.bindings && typeof r.bindings === "object" ? r.bindings : {}) as Record<string, unknown>)) {
    if (typeof k !== "string" || !/^[A-Z_]+$/.test(k)) continue;
    if (v === null) bindings[k] = null;
    else if (typeof v === "string") { const n = normaliseBinding(v); if (n) bindings[k] = n; }
  }
  return { pinned: ids(r.pinned, MAX_PINNED), quickActions: ids(r.quickActions, MAX_QUICK_ACTIONS), bindings, version: 1 };
}

function sanitiseDevice(raw: unknown): DevicePrefs {
  const r = (raw && typeof raw === "object" ? raw : {}) as Partial<DevicePrefs>;
  return { bindings: sanitiseUser({ bindings: r.bindings }).bindings, version: 1 };
}

/** Local storage on this device, per workspace. Every read is guarded; a broken value is ignored. */
export class LocalPreferenceStore implements PreferenceStore {
  constructor(private readonly storage: Pick<Storage, "getItem" | "setItem"> | null = typeof window === "undefined" ? null : window.localStorage) {}

  private read(key: string): unknown {
    try { const raw = this.storage?.getItem(key); return raw ? JSON.parse(raw) : null; } catch { return null; }
  }

  private write(key: string, value: unknown): void {
    try { this.storage?.setItem(key, JSON.stringify(value)); } catch { /* private mode or quota: preferences are best effort */ }
  }

  loadUser(workspace: string): UserPrefs { return sanitiseUser(this.read(`zaad.prefs.user.${workspace}`)); }
  saveUser(workspace: string, prefs: UserPrefs): void { this.write(`zaad.prefs.user.${workspace}`, sanitiseUser(prefs)); }
  loadDevice(workspace: string): DevicePrefs { return sanitiseDevice(this.read(`zaad.prefs.device.${workspace}`)); }
  saveDevice(workspace: string, prefs: DevicePrefs): void { this.write(`zaad.prefs.device.${workspace}`, sanitiseDevice(prefs)); }
}

export class MemoryPreferenceStore implements PreferenceStore {
  private user = new Map<string, UserPrefs>();
  private device = new Map<string, DevicePrefs>();
  loadUser(workspace: string): UserPrefs { return this.user.get(workspace) ?? EMPTY_USER; }
  saveUser(workspace: string, prefs: UserPrefs): void { this.user.set(workspace, sanitiseUser(prefs)); }
  loadDevice(workspace: string): DevicePrefs { return this.device.get(workspace) ?? EMPTY_DEVICE; }
  saveDevice(workspace: string, prefs: DevicePrefs): void { this.device.set(workspace, sanitiseDevice(prefs)); }
}

/** The bindings in effect: defaults ← user logical overrides ← device overrides. */
export function mergedOverrides(user: UserPrefs, device: DevicePrefs): BindingMap {
  return { ...user.bindings, ...device.bindings };
}

/** Pinned destinations this person may still see, in their order. */
export function pinnedDestinations(prefs: UserPrefs, v: Visibility): Destination[] {
  const allowed = new Set(visible(v).filter((d) => d.pinnable).map((d) => d.id));
  return prefs.pinned.filter((id) => allowed.has(id)).map((id) => byId(id)!).filter(Boolean);
}

/**
 * The phone's quick actions: the person's choice, padded from the defaults so there are always
 * exactly `MAX_QUICK_ACTIONS` reachable, permitted destinations. Everything else stays behind More.
 */
export function quickActions(prefs: UserPrefs, v: Visibility): Destination[] {
  const allowed = visible({ ...v, device: "phone" }).filter((d) => d.quickAction);
  const allowedIds = new Set(allowed.map((d) => d.id));
  const chosen = prefs.quickActions.filter((id) => allowedIds.has(id));
  for (const id of DEFAULT_QUICK_ACTIONS) if (chosen.length < MAX_QUICK_ACTIONS && allowedIds.has(id) && !chosen.includes(id)) chosen.push(id);
  for (const d of allowed) if (chosen.length < MAX_QUICK_ACTIONS && !chosen.includes(d.id)) chosen.push(d.id);
  return chosen.slice(0, MAX_QUICK_ACTIONS).map((id) => byId(id)!);
}

export function togglePinned(prefs: UserPrefs, id: string): UserPrefs {
  const d = byId(id);
  if (!d || !d.pinnable) return prefs;
  const pinned = prefs.pinned.includes(id) ? prefs.pinned.filter((x) => x !== id) : [...prefs.pinned, id].slice(-MAX_PINNED);
  return { ...prefs, pinned };
}

export function setQuickActions(prefs: UserPrefs, ids: string[]): UserPrefs {
  const clean = ids.filter((id, i) => byId(id)?.quickAction && ids.indexOf(id) === i).slice(0, MAX_QUICK_ACTIONS);
  return { ...prefs, quickActions: clean };
}

export function setBinding(prefs: UserPrefs, command: string, binding: string | null): UserPrefs {
  const bindings = { ...prefs.bindings };
  if (binding === null) bindings[command] = null;
  else {
    const n = normaliseBinding(binding);
    if (!n) return prefs;
    bindings[command] = n;
  }
  return { ...prefs, bindings };
}

export function restoreDefault(prefs: UserPrefs, command: string): UserPrefs {
  const bindings = { ...prefs.bindings };
  delete bindings[command];
  return { ...prefs, bindings };
}

export function resetAll(prefs: UserPrefs): UserPrefs {
  return { ...prefs, bindings: {} };
}
