/**
 * Platform and device detection for shortcuts: what the modifier is called, whether a keyboard
 * is first class, and whether the screen is a phone.
 *
 * Platform comes from `navigator.userAgentData.platform` when the browser exposes it, then from
 * `navigator.platform`, and only then from the user-agent string. Unknown platforms are treated
 * as "other" and display generic modifier words. The device profile comes from the pointer and
 * viewport media queries, not from the platform: an iPad with a hardware keyboard is a tablet
 * whose shortcuts work; a desktop browser narrowed to 500 px is still a desktop.
 */
import type { Device } from "./destinations";

export type Platform = "mac" | "windows" | "linux" | "ios" | "android" | "other";

export interface DeviceProfile {
  platform: Platform;
  device: Device;
  /** true when a hardware keyboard is likely present (fine pointer or a desktop platform) */
  keyboard: boolean;
  touch: boolean;
}

interface NavigatorLike {
  userAgentData?: { platform?: string; mobile?: boolean };
  platform?: string;
  userAgent?: string;
  maxTouchPoints?: number;
}

export function detectPlatform(nav: NavigatorLike | undefined = typeof navigator === "undefined" ? undefined : navigator): Platform {
  if (!nav) return "other";
  const hinted = (nav.userAgentData?.platform || "").toLowerCase();
  const platform = (nav.platform || "").toLowerCase();
  const ua = (nav.userAgent || "").toLowerCase();
  const text = hinted || platform || ua;
  if (/iphone|ipad|ipod/.test(text) || (/mac/.test(text) && (nav.maxTouchPoints ?? 0) > 1 && /mobile|ipad/.test(ua))) return "ios";
  if (/android/.test(text) || /android/.test(ua)) return "android";
  if (/mac/.test(text)) return "mac";
  if (/win/.test(text)) return "windows";
  if (/linux|x11|cros/.test(text)) return "linux";
  if (/iphone|ipad/.test(ua)) return "ios";
  if (/mac os/.test(ua)) return "mac";
  if (/windows/.test(ua)) return "windows";
  if (/linux/.test(ua)) return "linux";
  return "other";
}

export function detectDevice(win: { matchMedia?: (q: string) => { matches: boolean }; innerWidth?: number } | undefined = typeof window === "undefined" ? undefined : window,
                             platform: Platform = "other"): { device: Device; keyboard: boolean; touch: boolean } {
  if (!win) return { device: "desktop", keyboard: true, touch: false };
  const mq = (q: string) => Boolean(win.matchMedia?.(q)?.matches);
  const coarse = mq("(pointer: coarse)") && !mq("(pointer: fine)");
  const width = win.innerWidth ?? 1280;
  const touch = mq("(hover: none)") || coarse;
  if (width < 700 && (touch || platform === "ios" || platform === "android")) return { device: "phone", keyboard: false, touch: true };
  if (width < 700) return { device: "phone", keyboard: true, touch: false };
  if (touch || platform === "ios" || platform === "android") return { device: "tablet", keyboard: mq("(pointer: fine)") || !coarse, touch: true };
  return { device: "desktop", keyboard: true, touch: false };
}

export function detectProfile(): DeviceProfile {
  const platform = detectPlatform();
  const { device, keyboard, touch } = detectDevice(undefined, platform);
  return { platform, device, keyboard, touch };
}

/** The primary modifier for "command" bindings: ⌘ on Mac, Ctrl elsewhere. */
export function primaryModifier(platform: Platform): "meta" | "ctrl" {
  return platform === "mac" || platform === "ios" ? "meta" : "ctrl";
}

const GLYPHS: Record<Platform, Record<string, string>> = {
  mac: { meta: "⌘", ctrl: "⌃", alt: "⌥", shift: "⇧", enter: "↵", escape: "esc", arrowup: "↑", arrowdown: "↓" },
  ios: { meta: "⌘", ctrl: "⌃", alt: "⌥", shift: "⇧", enter: "↵", escape: "esc", arrowup: "↑", arrowdown: "↓" },
  windows: { meta: "Win", ctrl: "Ctrl", alt: "Alt", shift: "Shift", enter: "Enter", escape: "Esc", arrowup: "↑", arrowdown: "↓" },
  linux: { meta: "Super", ctrl: "Ctrl", alt: "Alt", shift: "Shift", enter: "Enter", escape: "Esc", arrowup: "↑", arrowdown: "↓" },
  android: { meta: "Meta", ctrl: "Ctrl", alt: "Alt", shift: "Shift", enter: "Enter", escape: "Esc", arrowup: "↑", arrowdown: "↓" },
  other: { meta: "Meta", ctrl: "Ctrl", alt: "Alt", shift: "Shift", enter: "Enter", escape: "Esc", arrowup: "↑", arrowdown: "↓" },
};

/** The glyph or word for one key on this platform. */
export function keyGlyph(key: string, platform: Platform): string {
  const k = key.toLowerCase();
  const glyph = GLYPHS[platform][k];
  if (glyph) return glyph;
  if (k === " ") return "Space";
  return k.length === 1 ? k.toUpperCase() : key;
}

/** The joiner between keys of one combination: none on Mac (⌘K), "+" elsewhere (Ctrl+K). */
export function joiner(platform: Platform): string {
  return platform === "mac" || platform === "ios" ? "" : "+";
}
