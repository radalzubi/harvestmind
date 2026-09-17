/**
 * The command centre's logic without a browser: the registry, platform display, chords, focus
 * safety, collisions, preferences, quick actions, pinning and recents.
 */
import assert from "node:assert/strict";
import { test } from "node:test";
import { DESTINATIONS, DEFAULT_QUICK_ACTIONS, MAX_QUICK_ACTIONS, byRoute, integrity, paletteDestinations, search, visible, type Visibility } from "../destinations";
import { detectDevice, detectPlatform, keyGlyph } from "../platform";
import { COMMANDS, bindingProblem, collidesWith, collisions, comboOf, defaultBindings, displayBinding, effectiveBindings, isEditableTarget, normaliseBinding, resolve } from "../shortcuts";
import { EMPTY_USER, MemoryPreferenceStore, mergedOverrides, pinnedDestinations, quickActions, resetAll, restoreDefault, setBinding, setQuickActions, togglePinned } from "../preferences";
import { loadRecents, pushRecent, saveRecents } from "../recents";

const everyone: Visibility = { device: "desktop", can: () => true, family: "commercial" };
const viewer: Visibility = { device: "desktop", can: (c) => c === "view" || c === "viewAnalytics", family: "commercial" };
const phone: Visibility = { device: "phone", can: () => true, family: "commercial" };

// ── registry ──

test("the registry has unique ids, routes and chords, and every page is command-reachable", () => {
  assert.deepEqual(integrity(), []);
  for (const id of ["home", "decisions", "inventory", "orders", "insights", "explore", "dashboards", "ask", "network", "diagnostics", "history", "upload", "data", "advanced-planner", "order-formats", "shortcuts"]) {
    assert.ok(DESTINATIONS.some((d) => d.id === id), id);
  }
  const palette = paletteDestinations(everyone).map((d) => d.id);
  for (const d of DESTINATIONS.filter((x) => !x.families)) assert.ok(palette.includes(d.id), `${d.id} not in the palette`);
});

test("search finds pages by prefix, keyword and label, ranked", () => {
  const ids = (q: string) => search(everyone, q).map((r) => r.destination.id);
  assert.equal(ids("inv")[0], "inventory");
  assert.equal(ids("diag")[0], "diagnostics");
  assert.equal(ids("dash")[0], "dashboards");
  assert.equal(ids("ask")[0], "ask");
  assert.equal(ids("upload")[0], "upload");
  assert.ok(ids("stock").includes("inventory"));
  assert.ok(ids("po").includes("orders"));
  assert.equal(search(everyone, "").length, paletteDestinations(everyone).length);
});

test("visibility respects device, capability and family; nothing leaks through metadata", () => {
  assert.ok(visible(everyone).some((d) => d.id === "explore"));
  assert.ok(!visible(phone).some((d) => d.id === "explore"), "authoring is not offered on a phone");
  assert.ok(visible(phone).some((d) => d.id === "ask"));
  assert.ok(!visible(viewer).some((d) => d.id === "ask"), "a viewer cannot reach Ask ZAAD");
  assert.ok(visible(viewer).some((d) => d.id === "dashboards"));
  assert.ok(!visible(everyone).some((d) => d.id === "produce-atp"));
  assert.ok(visible({ ...everyone, family: "produce" }).some((d) => d.id === "produce-atp"));
  assert.equal(byRoute("/orders/formats")?.id, "order-formats");
  assert.equal(byRoute("/orders/draft_1")?.id, "orders");
});

// ── platform ──

test("platform detection prefers client hints, then platform, then the user agent; unknown is other", () => {
  assert.equal(detectPlatform({ userAgentData: { platform: "macOS" } }), "mac");
  assert.equal(detectPlatform({ platform: "Win32", userAgent: "Mozilla/5.0 (Windows NT 10.0)" }), "windows");
  assert.equal(detectPlatform({ platform: "Linux x86_64" }), "linux");
  assert.equal(detectPlatform({ userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)" }), "ios");
  assert.equal(detectPlatform({ userAgent: "Mozilla/5.0 (Linux; Android 14)" }), "android");
  assert.equal(detectPlatform({}), "other");
  assert.equal(detectPlatform(undefined), "other");
});

test("device profile comes from pointer and viewport, not the platform alone", () => {
  const win = (width: number, coarse: boolean, fine = !coarse) => ({ innerWidth: width, matchMedia: (q: string) => ({ matches: q.includes("coarse") ? coarse : q.includes("fine") ? fine : q.includes("hover: none") ? coarse : false }) });
  assert.equal(detectDevice(win(1400, false), "mac").device, "desktop");
  assert.equal(detectDevice(win(390, true), "ios").device, "phone");
  assert.equal(detectDevice(win(1024, true), "ios").device, "tablet");
  assert.equal(detectDevice(win(1024, true, true), "ios").keyboard, true, "an iPad with a fine pointer has a keyboard");
  assert.equal(detectDevice(win(500, false), "windows").device, "phone");
  assert.equal(detectDevice(win(500, false), "windows").keyboard, true);
});

test("the same logical binding displays with the platform's glyphs", () => {
  assert.equal(displayBinding("primary+k", "mac"), "⌘K");
  assert.equal(displayBinding("primary+k", "windows"), "Ctrl+K");
  assert.equal(displayBinding("primary+k", "linux"), "Ctrl+K");
  assert.equal(displayBinding("primary+shift+k", "mac"), "⌘⇧K");
  assert.equal(displayBinding("primary+shift+k", "windows"), "Ctrl+Shift+K");
  assert.equal(displayBinding("g i", "mac"), "G then I");
  assert.equal(displayBinding("g i", "windows", "then"), "G then I");
  assert.equal(displayBinding("shift+/", "other"), "Shift+/");
  assert.equal(keyGlyph("enter", "mac"), "↵");
});

// ── bindings and resolution ──

test("bindings normalise, refuse reserved and bare keys, and detect collisions", () => {
  assert.equal(normaliseBinding("Shift+Primary+K"), "primary+shift+k");
  assert.equal(normaliseBinding("G I"), "g i");
  assert.equal(normaliseBinding("nonsense+++"), null);
  assert.equal(bindingProblem("primary+t"), "reserved");
  assert.equal(bindingProblem("primary+w"), "reserved");
  assert.equal(bindingProblem("k"), "bare_key");
  assert.equal(bindingProblem("shift+k"), "bare_key");
  assert.equal(bindingProblem("x i"), "chord_prefix");
  assert.equal(bindingProblem("primary+shift+e"), null);
  assert.equal(bindingProblem("g e"), null);
  const b = effectiveBindings({ GO_EXPLORE: "g i" });
  assert.deepEqual(collisions(b), [["g i", ["GO_INVENTORY", "GO_EXPLORE"]]]);
  assert.equal(collidesWith(defaultBindings(), "GO_EXPLORE", "g i"), "GO_INVENTORY");
  assert.equal(collidesWith(defaultBindings(), "GO_INVENTORY", "g i"), null);
  assert.deepEqual(collisions(defaultBindings()), [], "defaults never collide");
});

const key = (k: string, mods: Partial<{ metaKey: boolean; ctrlKey: boolean; altKey: boolean; shiftKey: boolean }> = {}, target?: unknown) =>
  ({ key: k, metaKey: false, ctrlKey: false, altKey: false, shiftKey: false, ...mods, target });

test("Cmd+K on a Mac and Ctrl+K on Windows resolve to the same command; slash searches; ? opens help", () => {
  const b = defaultBindings();
  assert.equal(resolve(key("k", { metaKey: true }), b, "mac", null, 0).command, "OPEN_COMMAND_PALETTE");
  assert.equal(resolve(key("k", { ctrlKey: true }), b, "windows", null, 0).command, "OPEN_COMMAND_PALETTE");
  assert.equal(resolve(key("k", { ctrlKey: true }), b, "linux", null, 0).command, "OPEN_COMMAND_PALETTE");
  assert.equal(resolve(key("k", { ctrlKey: true }), b, "mac", null, 0).command, null, "Ctrl+K is not the primary on a Mac");
  assert.equal(resolve(key("/"), b, "mac", null, 0).command, "SEARCH");
  assert.equal(resolve(key("?", { shiftKey: true }), b, "mac", null, 0).command, "SHOW_SHORTCUTS");
});

test("two-key chords need the prefix within the timeout and cancel on Escape, modifiers or a pause", () => {
  const b = defaultBindings();
  const armed = resolve(key("g"), b, "mac", null, 1000);
  assert.equal(armed.command, null);
  assert.ok(armed.pending && armed.consumed);
  assert.equal(resolve(key("i"), b, "mac", armed.pending, 1500).command, "GO_INVENTORY");
  assert.equal(resolve(key("e"), b, "mac", armed.pending, 1500).command, "GO_EXPLORE");
  assert.equal(resolve(key("a"), b, "mac", armed.pending, 1500).command, "GO_ASK");
  assert.equal(resolve(key("b"), b, "mac", armed.pending, 1500).command, "GO_DASHBOARDS");
  assert.equal(resolve(key("i"), b, "mac", armed.pending, 5000).command, null, "the chord expired");
  assert.equal(resolve(key("Escape"), b, "mac", armed.pending, 1200).pending, null);
  assert.equal(resolve(key("i", { metaKey: true }), b, "mac", armed.pending, 1200).command, null, "a modifier cancels the chord");
  assert.equal(resolve(key("i"), b, "mac", null, 0).command, null, "a bare key never navigates");
});

test("global shortcuts never fire while typing, except bindings marked safe", () => {
  const b = defaultBindings();
  const input = { tagName: "INPUT" };
  const editable = { tagName: "DIV", isContentEditable: true };
  const textbox = { tagName: "DIV", getAttribute: (n: string) => (n === "role" ? "textbox" : null) };
  assert.ok(isEditableTarget(input) && isEditableTarget(editable) && isEditableTarget(textbox));
  assert.ok(!isEditableTarget({ tagName: "BUTTON" }));
  assert.equal(resolve(key("/", {}, input), b, "mac", null, 0).command, null, "slash types in an input");
  assert.equal(resolve(key("g", {}, input), b, "mac", null, 0).pending, null, "no chord arms while typing");
  assert.equal(resolve(key("k", { metaKey: true }, input), b, "mac", null, 0).command, "OPEN_COMMAND_PALETTE", "the palette binding is safe in an editable");
  assert.equal(comboOf(key("Meta", { metaKey: true }), "mac"), null);
});

// ── preferences ──

test("user preferences: bindings, restore, reset; device prefs overlay; a store round-trips", () => {
  let prefs = setBinding(EMPTY_USER, "GO_EXPLORE", "primary+shift+e");
  assert.equal(prefs.bindings.GO_EXPLORE, "primary+shift+e");
  prefs = setBinding(prefs, "GO_INVENTORY", null);
  const eff = effectiveBindings(mergedOverrides(prefs, { bindings: {}, version: 1 }));
  assert.equal(eff.GO_EXPLORE, "primary+shift+e");
  assert.equal(eff.GO_INVENTORY, null);
  assert.equal(eff.GO_HOME, "g h");
  prefs = restoreDefault(prefs, "GO_INVENTORY");
  assert.equal(effectiveBindings(mergedOverrides(prefs, { bindings: {}, version: 1 })).GO_INVENTORY, "g i");
  assert.deepEqual(resetAll(prefs).bindings, {});
  const device = { bindings: { GO_EXPLORE: "primary+e" }, version: 1 as const };
  assert.equal(effectiveBindings(mergedOverrides(prefs, device)).GO_EXPLORE, "primary+e", "the device overlay wins on this device");
  const store = new MemoryPreferenceStore();
  store.saveUser("ws1", prefs);
  assert.deepEqual(store.loadUser("ws1"), prefs);
  assert.deepEqual(store.loadUser("ws2"), EMPTY_USER, "preferences are per workspace");
  assert.equal(setBinding(prefs, "GO_EXPLORE", "garbage+++"), prefs, "a malformed binding changes nothing");
});

test("quick actions are always four reachable, permitted destinations; pins are bounded", () => {
  assert.deepEqual(quickActions(EMPTY_USER, phone).map((d) => d.id), DEFAULT_QUICK_ACTIONS);
  const chosen = setQuickActions(EMPTY_USER, ["home", "orders", "explore", "diagnostics", "ask", "network"]);
  assert.deepEqual(chosen.quickActions, ["home", "orders", "diagnostics", "ask"], "explore is not a quick action; the list is capped");
  const phoneViewer: Visibility = { device: "phone", can: (c) => c === "view" || c === "viewAnalytics", family: "commercial" };
  const q = quickActions(setQuickActions(EMPTY_USER, ["home", "ask", "decisions", "inventory"]), phoneViewer).map((d) => d.id);
  assert.equal(q.length, MAX_QUICK_ACTIONS);
  assert.ok(!q.includes("ask"), "a viewer's quick actions never include a page they cannot open");
  let p = togglePinned(EMPTY_USER, "explore");
  p = togglePinned(p, "shortcuts");
  assert.deepEqual(p.pinned, ["explore"], "a non-pinnable page is ignored");
  assert.deepEqual(pinnedDestinations(p, viewer).map((d) => d.id), ["explore"]);
  assert.deepEqual(pinnedDestinations(togglePinned(EMPTY_USER, "ask"), viewer), [], "a pin the role cannot open is hidden, not shown");
  for (const id of ["home", "decisions", "inventory", "orders", "insights", "explore", "dashboards"]) p = togglePinned(p, id);
  assert.ok(p.pinned.length <= 6);
});

test("recents keep identifiers and short labels only, de-duplicated and bounded", () => {
  let list = pushRecent([], { kind: "page", id: "inventory", route: "/inventory", label: "Inventory" }, 1);
  list = pushRecent(list, { kind: "record", id: "PO-1", route: "/orders?po=PO-1", label: "PO-1" }, 2);
  list = pushRecent(list, { kind: "page", id: "inventory", route: "/inventory", label: "Inventory" }, 3);
  assert.deepEqual(list.map((r) => r.id), ["inventory", "PO-1"]);
  assert.equal(pushRecent(list, { kind: "record", id: "x", route: "javascript:alert(1)", label: "x" }).length, 2, "a non-route is refused");
  const long = "a".repeat(200);
  assert.equal(pushRecent([], { kind: "record", id: "y", route: "/data", label: long })[0].label.length, 80);
  for (let i = 0; i < 20; i++) list = pushRecent(list, { kind: "record", id: `r${i}`, route: "/data", label: `r${i}` }, 10 + i);
  assert.equal(list.length, 8);
  const mem: Record<string, string> = {};
  const storage = { getItem: (k: string) => mem[k] ?? null, setItem: (k: string, v: string) => { mem[k] = v; } };
  saveRecents("ws", list, storage);
  assert.deepEqual(loadRecents("ws", storage).map((r) => r.id), list.map((r) => r.id));
  mem["zaad.recents.bad"] = JSON.stringify([{ kind: "record", id: "z", route: "https://evil", label: "z" }, "junk"]);
  assert.deepEqual(loadRecents("bad", storage), []);
});

test("every destination has a navigation command and the analytics pages participate automatically", () => {
  for (const d of DESTINATIONS) assert.ok(COMMANDS.some((c) => c.destination === d.id), d.id);
  const b = defaultBindings();
  assert.equal(b.GO_EXPLORE, "g e");
  assert.equal(b.GO_DASHBOARDS, "g b");
  assert.equal(b.GO_ASK, "g a");
});
