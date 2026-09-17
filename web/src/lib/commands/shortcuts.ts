/**
 * Logical commands, normalised bindings, platform-adapted display and execution.
 *
 * A command is platform-independent (`OPEN_COMMAND_PALETTE`, `GO_INVENTORY`). A binding is either
 * a combination — modifiers plus one key, with the `primary` modifier standing for ⌘ on a Mac and
 * Ctrl elsewhere — or a chord: a prefix key followed by one key within a timeout (`g` then `i`).
 * Bindings are stored normalised (`primary+k`, `g i`), shown through the platform's glyphs, and
 * matched against real key events with the platform's modifier substituted.
 *
 * Safety: a global binding never fires while the person is typing in an input, a textarea, a
 * contenteditable or a select; chords cancel on Escape, on any modifier, on a pause longer than
 * their timeout; a binding the browser or the OS reserves is refused at customisation time.
 */
import { DESTINATIONS, type Destination } from "./destinations";
import { joiner, keyGlyph, primaryModifier, type Platform } from "./platform";

export type CommandKind = "navigate" | "search" | "action";

export interface Command {
  id: string;
  kind: CommandKind;
  label: string;          // English canonical; localised through labelKey when present
  labelKey?: string;
  /** default binding, normalised; null = none */
  defaultBinding: string | null;
  /** a navigation command's destination id */
  destination?: string;
  /** whether the binding may fire while an editable element has focus (never for chords) */
  safeInEditable?: boolean;
}

export const CHORD_PREFIX = "g";
export const CHORD_TIMEOUT_MS = 1500;

/** Combinations the browser or the OS owns. Refused when someone tries to bind them. */
const RESERVED: readonly string[] = [
  "primary+t", "primary+w", "primary+n", "primary+q", "primary+r", "primary+l", "primary+d", "primary+f", "primary+p", "primary+s",
  "primary+shift+t", "primary+shift+n", "primary+shift+w", "primary+tab", "primary+shift+tab", "primary+a", "primary+c", "primary+v", "primary+x", "primary+z",
  "ctrl+alt+delete", "alt+f4", "alt+tab", "f5", "f11", "f12", "primary+0", "primary+-", "primary+=", "primary+h", "primary+m",
];

export const COMMANDS: readonly Command[] = [
  { id: "OPEN_COMMAND_PALETTE", kind: "search", label: "Open the command palette", labelKey: "openPalette", defaultBinding: "primary+k", safeInEditable: true },
  { id: "SEARCH", kind: "search", label: "Search records", labelKey: "search", defaultBinding: "/" },
  { id: "SHOW_SHORTCUTS", kind: "action", label: "Show keyboard shortcuts", labelKey: "showShortcuts", defaultBinding: "shift+/" },
  { id: "TOGGLE_LANGUAGE", kind: "action", label: "Switch language", labelKey: "toggleLanguage", defaultBinding: null },
  { id: "RUN_PLAN", kind: "action", label: "Run a plan", labelKey: "runPlan", defaultBinding: null },
  ...DESTINATIONS.map((d): Command => ({
    id: `GO_${d.id.toUpperCase().replace(/-/g, "_")}`, kind: "navigate", label: `Go to ${d.label}`, labelKey: d.labelKey,
    defaultBinding: d.chord ? `${CHORD_PREFIX} ${d.chord}` : null, destination: d.id,
  })),
];

export function commandById(id: string): Command | undefined {
  return COMMANDS.find((c) => c.id === id);
}

export function commandForDestination(d: Destination): Command | undefined {
  return COMMANDS.find((c) => c.destination === d.id);
}

// ── binding representation ──

export interface Combo { kind: "combo"; modifiers: string[]; key: string }
export interface Chord { kind: "chord"; prefix: string; key: string }
export type Binding = Combo | Chord;

const MOD_ORDER = ["primary", "ctrl", "meta", "alt", "shift"];

/** Parse a stored binding. `primary+shift+k` or `g i`. Returns null when malformed. */
export function parseBinding(text: string | null | undefined): Binding | null {
  if (!text) return null;
  const t = text.trim().toLowerCase();
  if (/^[a-z0-9] [a-z0-9]$/.test(t)) {
    const [prefix, key] = t.split(" ");
    return { kind: "chord", prefix, key };
  }
  const parts = t.split("+").map((p) => p.trim()).filter(Boolean);
  if (!parts.length) return null;
  const key = parts[parts.length - 1];
  const modifiers = parts.slice(0, -1);
  if (!key || key.length === 0) return null;
  if (modifiers.some((m) => !MOD_ORDER.includes(m))) return null;
  if (key.length > 1 && !/^(f\d{1,2}|enter|escape|tab|space|arrowup|arrowdown|arrowleft|arrowright|backspace|delete|home|end|pageup|pagedown|\/|\?)$/.test(key)) return null;
  return { kind: "combo", modifiers: MOD_ORDER.filter((m) => modifiers.includes(m)), key };
}

export function normaliseBinding(text: string): string | null {
  const b = parseBinding(text);
  if (!b) return null;
  return b.kind === "chord" ? `${b.prefix} ${b.key}` : [...b.modifiers, b.key].join("+");
}

/** What a binding looks like on this platform: `⌘K`, `Ctrl+K`, `G then I`. */
export function displayBinding(text: string | null | undefined, platform: Platform, then = "then"): string {
  const b = parseBinding(text);
  if (!b) return "";
  if (b.kind === "chord") return `${keyGlyph(b.prefix, platform)} ${then} ${keyGlyph(b.key, platform)}`;
  const mods = b.modifiers.map((m) => (m === "primary" ? primaryModifier(platform) : m));
  return [...mods, b.key].map((k) => keyGlyph(k, platform)).join(joiner(platform));
}

export function isReserved(text: string): boolean {
  const n = normaliseBinding(text);
  return n != null && RESERVED.includes(n);
}

/** A binding that is unsafe or ambiguous: a bare letter (typing), a reserved combination, a chord on a modifier. */
export function bindingProblem(text: string): string | null {
  const b = parseBinding(text);
  if (!b) return "not_a_binding";
  if (isReserved(text)) return "reserved";
  if (b.kind === "combo" && b.modifiers.length === 0 && /^[a-z0-9]$/.test(b.key)) return "bare_key";
  if (b.kind === "combo" && b.modifiers.length === 1 && b.modifiers[0] === "shift" && /^[a-z0-9]$/.test(b.key)) return "bare_key";
  if (b.kind === "chord" && b.prefix !== CHORD_PREFIX) return "chord_prefix";
  return null;
}

// ── bindings in effect ──

export type BindingMap = Record<string, string | null>;   // command id → normalised binding (null = removed)

export function defaultBindings(): BindingMap {
  const out: BindingMap = {};
  for (const c of COMMANDS) out[c.id] = c.defaultBinding;
  return out;
}

/** Defaults overlaid with the person's overrides. An override of `null` removes the binding. */
export function effectiveBindings(overrides: BindingMap | null | undefined): BindingMap {
  const out = defaultBindings();
  for (const [id, binding] of Object.entries(overrides ?? {})) {
    if (!(id in out)) continue;
    out[id] = binding == null ? null : normaliseBinding(binding);
  }
  return out;
}

/** Commands whose active bindings collide, as [binding, [command ids]]. */
export function collisions(bindings: BindingMap): Array<[string, string[]]> {
  const seen = new Map<string, string[]>();
  for (const [id, b] of Object.entries(bindings)) {
    if (!b) continue;
    seen.set(b, [...(seen.get(b) ?? []), id]);
  }
  return [...seen.entries()].filter(([, ids]) => ids.length > 1);
}

/** Which command a proposed binding would collide with, ignoring `forCommand` itself. */
export function collidesWith(bindings: BindingMap, forCommand: string, text: string): string | null {
  const n = normaliseBinding(text);
  if (!n) return null;
  for (const [id, b] of Object.entries(bindings)) {
    if (id !== forCommand && b === n) return id;
  }
  return null;
}

// ── matching real key events ──

export interface KeyLike {
  key: string;
  metaKey: boolean;
  ctrlKey: boolean;
  altKey: boolean;
  shiftKey: boolean;
  target?: unknown;
}

/** Whether the event's target is somewhere a person types. */
export function isEditableTarget(target: unknown): boolean {
  const el = target as { tagName?: string; isContentEditable?: boolean; getAttribute?: (n: string) => string | null; closest?: (s: string) => unknown } | null;
  if (!el || typeof el !== "object") return false;
  const tag = (el.tagName || "").toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select") return true;
  if (el.isContentEditable) return true;
  if (el.getAttribute?.("role") === "textbox") return true;
  if (typeof el.closest === "function" && el.closest('[contenteditable=""], [contenteditable="true"], [role="dialog"][data-owns-keyboard="true"]')) return true;
  return false;
}

/** The normalised combination a key event represents on this platform, or null for a bare modifier. */
export function comboOf(e: KeyLike, platform: Platform): string | null {
  const key = e.key.length === 1 ? e.key.toLowerCase() : e.key.toLowerCase();
  if (["meta", "control", "alt", "shift"].includes(key)) return null;
  const primary = primaryModifier(platform);
  const mods: string[] = [];
  const meta = e.metaKey, ctrl = e.ctrlKey;
  if ((primary === "meta" && meta) || (primary === "ctrl" && ctrl)) mods.push("primary");
  if (primary === "meta" && ctrl) mods.push("ctrl");
  if (primary === "ctrl" && meta) mods.push("meta");
  if (e.altKey) mods.push("alt");
  if (e.shiftKey && !(key === "?" || key === "/")) mods.push("shift");
  const k = key === "?" ? "/" : key;
  if (key === "?") mods.push("shift");
  return [...MOD_ORDER.filter((m) => mods.includes(m)), k].join("+");
}

export interface ChordState { prefix: string; at: number }

export interface Resolution {
  command: string | null;
  /** a chord prefix was consumed; wait for the second key */
  pending: ChordState | null;
  /** the event should be prevented (a binding matched or a prefix was armed) */
  consumed: boolean;
}

/** Resolve one key event against the bindings, with the chord state from the previous event. */
export function resolve(e: KeyLike, bindings: BindingMap, platform: Platform, pending: ChordState | null, now: number, timeout = CHORD_TIMEOUT_MS): Resolution {
  const editable = isEditableTarget(e.target);
  const key = e.key.length === 1 ? e.key.toLowerCase() : e.key.toLowerCase();
  if (key === "escape") return { command: null, pending: null, consumed: false };
  const combo = comboOf(e, platform);
  if (!combo) return { command: null, pending: pending && now - pending.at <= timeout ? pending : null, consumed: false };
  const hasModifier = combo.includes("+") && !/^shift\+\/$/.test(combo);

  // a live chord: the second key completes it, anything else cancels it
  if (pending && now - pending.at <= timeout && !editable && !hasModifier) {
    const chord = `${pending.prefix} ${key}`;
    for (const [id, b] of Object.entries(bindings)) if (b === chord) return { command: id, pending: null, consumed: true };
    return { command: null, pending: null, consumed: false };
  }
  // a combination
  for (const [id, b] of Object.entries(bindings)) {
    if (b !== combo) continue;
    const cmd = commandById(id);
    if (editable && !cmd?.safeInEditable) continue;
    return { command: id, pending: null, consumed: true };
  }
  // arming a chord
  if (!editable && !hasModifier && key === CHORD_PREFIX && Object.values(bindings).some((b) => b?.startsWith(`${CHORD_PREFIX} `))) {
    return { command: null, pending: { prefix: key, at: now }, consumed: true };
  }
  return { command: null, pending: null, consumed: false };
}
