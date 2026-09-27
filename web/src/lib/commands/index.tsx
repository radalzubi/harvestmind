"use client";

/**
 * The command centre: one provider that owns the device profile, the preferences, the bindings
 * in effect, the global key listener, the recents and the palette / help open state.
 *
 * Pages never add key listeners of their own; they register nothing and read nothing but this
 * context. The shell renders navigation from the registry through it; the palette lists commands
 * from it; the settings page edits preferences through it.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { TENANT_RESET_EVENT } from "@/lib/tenant-state";
import { usePathname, useRouter } from "next/navigation";
import { useSession, type Capability } from "@/lib/session";
import { useLocale } from "@/lib/i18n";
import { byId, byRoute, type Destination, type Visibility } from "./destinations";
import { detectProfile, type DeviceProfile } from "./platform";
import {
  EMPTY_DEVICE, EMPTY_USER, LocalPreferenceStore, MemoryPreferenceStore, mergedOverrides, pinnedDestinations, quickActions as quickActionsOf,
  resetAll as resetAllPrefs, restoreDefault as restoreDefaultPref, setBinding as setBindingPref, setQuickActions as setQuickActionsPref, togglePinned as togglePinnedPref,
  type DevicePrefs, type PreferenceStore, type UserPrefs,
} from "./preferences";
import { loadRecents, pushRecent, saveRecents, type Recent } from "./recents";
import { COMMANDS, commandById, displayBinding, effectiveBindings, resolve, type BindingMap, type ChordState, type Command } from "./shortcuts";

export interface CommandCentre {
  profile: DeviceProfile;
  visibility: Visibility;
  prefs: UserPrefs;
  devicePrefs: DevicePrefs;
  bindings: BindingMap;
  pinned: Destination[];
  quickActions: Destination[];
  recents: Recent[];
  paletteOpen: boolean;
  helpOpen: boolean;
  /** the chord prefix currently armed, for the on-screen hint */
  pendingChord: boolean;
  openPalette: () => void;
  closePalette: () => void;
  openHelp: () => void;
  closeHelp: () => void;
  run: (commandId: string) => void;
  display: (commandId: string) => string;
  label: (d: Destination) => string;
  commandLabel: (c: Command) => string;
  togglePinned: (id: string) => void;
  setQuickActions: (ids: string[]) => void;
  setBinding: (commandId: string, binding: string | null) => void;
  restoreDefault: (commandId: string) => void;
  resetAll: () => void;
  rememberRecord: (id: string, route: string, label: string) => void;
  /** actions the shell wires (run a plan, switch language); absent = not available here */
  registerAction: (commandId: string, fn: (() => void) | null) => void;
}

const Ctx = createContext<CommandCentre | null>(null);

export function CommandProvider({ children, store }: { children: ReactNode; store?: PreferenceStore }) {
  const session = useSession();
  const router = useRouter();
  const pathname = usePathname() || "/";
  const { t, locale, setLocale } = useLocale();
  const workspace = session.workspace?.id ?? "anonymous";
  const family = session.workspace?.family ?? null;
  const [profile, setProfile] = useState<DeviceProfile>({ platform: "other", device: "desktop", keyboard: true, touch: false });
  const storeRef = useRef<PreferenceStore>(store ?? (typeof window === "undefined" ? new MemoryPreferenceStore() : new LocalPreferenceStore()));
  const [prefs, setPrefs] = useState<UserPrefs>(EMPTY_USER);
  const [devicePrefs] = useState<DevicePrefs>(EMPTY_DEVICE);
  const [recents, setRecents] = useState<Recent[]>([]);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const [pendingChord, setPendingChord] = useState(false);
  const chord = useRef<ChordState | null>(null);
  const actions = useRef<Map<string, () => void>>(new Map());

  // the device profile is only knowable on the client; the first paint is the desktop default
  useEffect(() => {
    const read = () => setProfile(detectProfile());
    read();
    window.addEventListener("resize", read);
    return () => window.removeEventListener("resize", read);
  }, []);

  useEffect(() => {
    setPrefs(storeRef.current.loadUser(workspace));
    setRecents(loadRecents(workspace));
  }, [workspace]);

  // a tenant reset (sign-out, switch, refused credential) empties what is held in memory at once,
  // before the session resolves the next workspace (SEC-038)
  useEffect(() => {
    const on = () => { setRecents([]); setPrefs(EMPTY_USER); };
    window.addEventListener(TENANT_RESET_EVENT, on);
    return () => window.removeEventListener(TENANT_RESET_EVENT, on);
  }, []);

  const can = useCallback((c: Capability) => (session.status === "authenticated" ? session.can(c) : c === "view"), [session]);
  const visibility = useMemo<Visibility>(() => ({ device: profile.device, can, family }), [profile.device, can, family]);
  const bindings = useMemo(() => effectiveBindings(mergedOverrides(prefs, devicePrefs)), [prefs, devicePrefs]);
  const pinned = useMemo(() => pinnedDestinations(prefs, visibility), [prefs, visibility]);
  const quick = useMemo(() => quickActionsOf(prefs, visibility), [prefs, visibility]);

  const label = useCallback((d: Destination) => {
    const nav = t.workspace.nav as Record<string, string>;
    return nav[d.labelKey] ?? d.label;
  }, [t]);
  const commandLabel = useCallback((c: Command) => {
    const copy = t.commands as Record<string, string>;
    if (c.kind === "navigate" && c.destination) {
      const d = byId(c.destination);
      return d ? `${copy.goTo} ${label(d)}` : c.label;
    }
    return (c.labelKey && copy[c.labelKey]) || c.label;
  }, [t, label]);

  const save = useCallback((next: UserPrefs) => { setPrefs(next); storeRef.current.saveUser(workspace, next); }, [workspace]);

  const rememberRecord = useCallback((id: string, route: string, text: string) => {
    if (session.status !== "authenticated") return;
    setRecents((list) => { const next = pushRecent(list, { kind: "record", id, route, label: text }); saveRecents(workspace, next); return next; });
  }, [workspace, session.status]);

  // every page visit is a recent
  useEffect(() => {
    const d = byRoute(pathname);
    if (!d || session.status !== "authenticated") return;
    setRecents((list) => { const next = pushRecent(list, { kind: "page", id: d.id, route: d.route, label: d.label }); saveRecents(workspace, next); return next; });
    setPaletteOpen(false);
    setHelpOpen(false);
  }, [pathname, workspace, session.status]);

  const run = useCallback((commandId: string) => {
    const c = commandById(commandId);
    if (!c) return;
    if (c.kind === "navigate" && c.destination) {
      const d = byId(c.destination);
      if (!d || !can(d.capability)) return;
      router.push(d.route);
      return;
    }
    if (commandId === "OPEN_COMMAND_PALETTE" || commandId === "SEARCH") { setPaletteOpen(true); return; }
    if (commandId === "SHOW_SHORTCUTS") { setHelpOpen((h) => !h); return; }
    if (commandId === "TOGGLE_LANGUAGE") { setLocale(locale === "ar" ? "en" : "ar"); return; }
    const fn = actions.current.get(commandId);
    if (fn) fn();
  }, [can, router, setLocale, locale]);

  // the one global key listener
  useEffect(() => {
    if (!profile.keyboard && profile.device === "phone") return;
    const timer = { handle: 0 };
    const on = (e: KeyboardEvent) => {
      if (e.key === "Escape" && chord.current) { chord.current = null; setPendingChord(false); return; }
      const out = resolve(e, bindings, profile.platform, chord.current, performance.now());
      chord.current = out.pending;
      setPendingChord(Boolean(out.pending));
      window.clearTimeout(timer.handle);
      if (out.pending) timer.handle = window.setTimeout(() => { chord.current = null; setPendingChord(false); }, 1600);
      if (out.consumed) e.preventDefault();
      if (out.command) run(out.command);
    };
    window.addEventListener("keydown", on);
    return () => { window.removeEventListener("keydown", on); window.clearTimeout(timer.handle); };
  }, [bindings, profile, run]);

  const value = useMemo<CommandCentre>(() => ({
    profile, visibility, prefs, devicePrefs, bindings, pinned, quickActions: quick, recents, paletteOpen, helpOpen, pendingChord,
    openPalette: () => setPaletteOpen(true), closePalette: () => setPaletteOpen(false), openHelp: () => setHelpOpen(true), closeHelp: () => setHelpOpen(false),
    run, display: (id) => displayBinding(bindings[id], profile.platform, (t.commands as Record<string, string>).then ?? "then"), label, commandLabel,
    togglePinned: (id) => save(togglePinnedPref(prefs, id)),
    setQuickActions: (ids) => save(setQuickActionsPref(prefs, ids)),
    setBinding: (id, b) => save(setBindingPref(prefs, id, b)),
    restoreDefault: (id) => save(restoreDefaultPref(prefs, id)),
    resetAll: () => save(resetAllPrefs(prefs)),
    rememberRecord,
    registerAction: (id, fn) => { if (fn) actions.current.set(id, fn); else actions.current.delete(id); },
  }), [profile, visibility, prefs, devicePrefs, bindings, pinned, quick, recents, paletteOpen, helpOpen, pendingChord, run, label, commandLabel, save, rememberRecord, t]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useCommands(): CommandCentre {
  const v = useContext(Ctx);
  if (!v) throw new Error("useCommands needs a CommandProvider");
  return v;
}

export { COMMANDS };
