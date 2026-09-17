/**
 * THE destination registry: one list every navigation surface reads.
 *
 * The desktop rail, the phone tabs, the More sheet, the command palette, the keyboard shortcuts,
 * the shortcut settings, the quick actions and the navigation search all derive from these
 * entries. A page added here is automatically reachable everywhere, subject to what it declares:
 * where it is available (desktop / tablet / phone), which capability it needs, and whether it may
 * be pinned, offered as a quick action or bound to a chord.
 *
 * Nothing here is a string a person sees: labels come from the i18n table through `labelKey`.
 * Route strings are the product's; no optimizer phase name appears.
 */
import type { Capability } from "@/lib/session";

export type DestinationGroup = "operate" | "analyse" | "data" | "settings" | "secondary";
export type Device = "desktop" | "tablet" | "phone";

export interface Destination {
  /** Stable, language-independent id. Never shown. */
  id: string;
  route: string;
  /** The English canonical label; the i18n key resolves the displayed one. */
  label: string;
  labelKey: string;
  /** A lucide icon name resolved by the shell (kept as a string so this module has no React). */
  icon: string;
  group: DestinationGroup;
  keywords: string[];
  availability: Device[];
  /** The capability a person needs to *see* the destination. Every authenticated person has `view`. */
  capability: Capability;
  /** The default two-key chord (after the `g` prefix), or null when the page has none by default. */
  chord: string | null;
  pinnable: boolean;
  palette: boolean;
  quickAction: boolean;
  /** Which workspace families see it; undefined = every workspace. */
  families?: Array<"commercial" | "produce">;
}

export const DESTINATIONS: readonly Destination[] = [
  { id: "home", route: "/home", label: "Home", labelKey: "home", icon: "Home", group: "operate", keywords: ["start", "overview", "console", "الرئيسية"], availability: ["desktop", "tablet", "phone"], capability: "view", chord: "h", pinnable: true, palette: true, quickAction: true },
  { id: "decisions", route: "/decisions", label: "Decisions", labelKey: "decisions", icon: "LayoutList", group: "operate", keywords: ["plan", "recommendations", "verdicts", "review", "القرارات"], availability: ["desktop", "tablet", "phone"], capability: "view", chord: "d", pinnable: true, palette: true, quickAction: true },
  { id: "inventory", route: "/inventory", label: "Inventory", labelKey: "inventory", icon: "Boxes", group: "operate", keywords: ["stock", "on hand", "cover", "products", "المخزون"], availability: ["desktop", "tablet", "phone"], capability: "view", chord: "i", pinnable: true, palette: true, quickAction: true },
  { id: "orders", route: "/orders", label: "Purchase orders", labelKey: "orders", icon: "FileText", group: "operate", keywords: ["po", "purchase", "proposals", "drafts", "suppliers", "أوامر الشراء"], availability: ["desktop", "tablet", "phone"], capability: "view", chord: "p", pinnable: true, palette: true, quickAction: true },
  { id: "insights", route: "/insights", label: "Insights", labelKey: "insights", icon: "BarChart3", group: "analyse", keywords: ["analytics", "demand", "charts", "curated", "الرؤى"], availability: ["desktop", "tablet", "phone"], capability: "view", chord: "s", pinnable: true, palette: true, quickAction: true },
  { id: "explore", route: "/explore", label: "Explore", labelKey: "explore", icon: "Compass", group: "analyse", keywords: ["build", "analysis", "pivot", "measure", "dimension", "استكشاف"], availability: ["desktop", "tablet"], capability: "viewAnalytics", chord: "e", pinnable: true, palette: true, quickAction: false },
  { id: "dashboards", route: "/dashboards", label: "Dashboards", labelKey: "dashboards", icon: "LayoutDashboard", group: "analyse", keywords: ["board", "saved", "tiles", "لوحات"], availability: ["desktop", "tablet", "phone"], capability: "viewAnalytics", chord: "b", pinnable: true, palette: true, quickAction: true },
  { id: "ask", route: "/ask", label: "Ask ZAAD", labelKey: "ask", icon: "MessageSquareText", group: "analyse", keywords: ["question", "ai", "chat", "assistant", "اسأل"], availability: ["desktop", "tablet", "phone"], capability: "askZaad", chord: "a", pinnable: true, palette: true, quickAction: true },
  { id: "network", route: "/network", label: "Network", labelKey: "network", icon: "Share2", group: "analyse", keywords: ["twin", "map", "sites", "lanes", "الشبكة"], availability: ["desktop", "tablet", "phone"], capability: "view", chord: "n", pinnable: true, palette: true, quickAction: true },
  { id: "diagnostics", route: "/diagnostics", label: "Diagnostics", labelKey: "diagnostics", icon: "Stethoscope", group: "analyse", keywords: ["suppliers", "routes", "physics", "value", "late", "التشخيص"], availability: ["desktop", "tablet", "phone"], capability: "view", chord: "x", pinnable: true, palette: true, quickAction: true },
  { id: "history", route: "/history", label: "History", labelKey: "history", icon: "History", group: "analyse", keywords: ["audit", "outcomes", "responses", "log", "السجل"], availability: ["desktop", "tablet", "phone"], capability: "view", chord: "y", pinnable: true, palette: true, quickAction: true },
  { id: "upload", route: "/upload", label: "Upload", labelKey: "upload", icon: "Upload", group: "data", keywords: ["files", "import", "csv", "data", "الرفع"], availability: ["desktop", "tablet", "phone"], capability: "view", chord: "u", pinnable: true, palette: true, quickAction: true },
  { id: "data", route: "/data", label: "Data", labelKey: "data", icon: "Database", group: "data", keywords: ["explorer", "records", "datasets", "rows", "البيانات"], availability: ["desktop", "tablet", "phone"], capability: "view", chord: "t", pinnable: true, palette: true, quickAction: true },
  { id: "advanced-planner", route: "/advanced/planner", label: "Advanced planner", labelKey: "advancedPlanner", icon: "Wrench", group: "secondary", keywords: ["planner", "request", "horizon", "advanced"], availability: ["desktop", "tablet"], capability: "view", chord: null, pinnable: true, palette: true, quickAction: false },
  { id: "order-formats", route: "/orders/formats", label: "Order export formats", labelKey: "orderFormats", icon: "FileText", group: "secondary", keywords: ["export", "profile", "template", "formats"], availability: ["desktop", "tablet"], capability: "view", chord: null, pinnable: true, palette: true, quickAction: false },
  { id: "shortcuts", route: "/settings/shortcuts", label: "Shortcuts", labelKey: "shortcuts", icon: "Keyboard", group: "settings", keywords: ["keyboard", "settings", "bindings", "quick actions", "preferences"], availability: ["desktop", "tablet", "phone"], capability: "view", chord: null, pinnable: false, palette: true, quickAction: false },
  { id: "access", route: "/access", label: "Workspace key", labelKey: "access", icon: "KeyRound", group: "settings", keywords: ["key", "token", "sign in", "people"], availability: ["desktop", "tablet", "phone"], capability: "view", chord: null, pinnable: false, palette: true, quickAction: false },
  // Fresh-produce workspaces keep their older diagnostic pages; secondary, family-scoped.
  { id: "produce-overview", route: "/overview", label: "Diagnostic summary", labelKey: "produceOverview", icon: "LayoutDashboard", group: "secondary", keywords: ["produce", "summary"], availability: ["desktop", "tablet"], capability: "view", chord: null, pinnable: true, palette: true, quickAction: false, families: ["produce"] },
  { id: "produce-atp", route: "/atp", label: "Available for customers", labelKey: "produceAtp", icon: "Activity", group: "secondary", keywords: ["atp", "promise", "customers"], availability: ["desktop", "tablet"], capability: "view", chord: null, pinnable: true, palette: true, quickAction: false, families: ["produce"] },
  { id: "produce-traceability", route: "/traceability", label: "Traceability", labelKey: "produceTraceability", icon: "ShieldCheck", group: "secondary", keywords: ["lots", "trace"], availability: ["desktop", "tablet"], capability: "view", chord: null, pinnable: true, palette: true, quickAction: false, families: ["produce"] },
  { id: "produce-partners", route: "/partners", label: "Partners", labelKey: "producePartners", icon: "Users", group: "secondary", keywords: ["partners"], availability: ["desktop", "tablet"], capability: "view", chord: null, pinnable: true, palette: true, quickAction: false, families: ["produce"] },
  { id: "produce-forecasts", route: "/forecasts", label: "Demand forecast", labelKey: "produceForecasts", icon: "TrendingUp", group: "secondary", keywords: ["forecast"], availability: ["desktop", "tablet"], capability: "view", chord: null, pinnable: true, palette: true, quickAction: false, families: ["produce"] },
  { id: "produce-supply-risk", route: "/supply-risk", label: "Supply risk", labelKey: "produceSupplyRisk", icon: "Truck", group: "secondary", keywords: ["risk"], availability: ["desktop", "tablet"], capability: "view", chord: null, pinnable: true, palette: true, quickAction: false, families: ["produce"] },
];

/** The primary rail groups, in order; `secondary` and `settings` render elsewhere. */
export const PRIMARY_GROUPS: Array<"operate" | "analyse" | "data"> = ["operate", "analyse", "data"];

/** The phone's default quick actions when nothing is customised. */
export const DEFAULT_QUICK_ACTIONS = ["home", "decisions", "inventory", "orders"];
export const MAX_QUICK_ACTIONS = 4;
export const MAX_PINNED = 6;

export interface Visibility {
  device: Device;
  can: (capability: Capability) => boolean;
  family?: "commercial" | "produce" | null;
}

export function byId(id: string): Destination | undefined {
  return DESTINATIONS.find((d) => d.id === id);
}

export function byRoute(pathname: string): Destination | undefined {
  // longest matching route wins, so /orders/formats resolves to its own entry
  const matches = DESTINATIONS.filter((d) => pathname === d.route || pathname.startsWith(d.route + "/"));
  return matches.sort((a, b) => b.route.length - a.route.length)[0];
}

/** Every destination this person may see on this device, in registry order. */
export function visible(v: Visibility): Destination[] {
  return DESTINATIONS.filter((d) =>
    d.availability.includes(v.device)
    && v.can(d.capability)
    && (!d.families || (v.family != null && d.families.includes(v.family))));
}

export function group(v: Visibility, g: DestinationGroup): Destination[] {
  return visible(v).filter((d) => d.group === g);
}

/** What the command palette lists before anyone types. */
export function paletteDestinations(v: Visibility): Destination[] {
  return visible(v).filter((d) => d.palette);
}

/** Search destinations by label, id and keywords; ranked, case-insensitive, prefix first. */
export function search(v: Visibility, query: string, label: (d: Destination) => string = (d) => d.label): Array<{ destination: Destination; rank: number }> {
  const q = query.trim().toLowerCase();
  if (!q) return paletteDestinations(v).map((destination) => ({ destination, rank: 1 }));
  const out: Array<{ destination: Destination; rank: number }> = [];
  for (const d of paletteDestinations(v)) {
    const hay = [label(d).toLowerCase(), d.label.toLowerCase(), d.id, ...d.keywords.map((k) => k.toLowerCase())];
    let rank = 0;
    for (const h of hay) {
      if (h === q) rank = Math.max(rank, 4);
      else if (h.startsWith(q)) rank = Math.max(rank, 3);
      else if (h.split(/\s+/).some((w) => w.startsWith(q))) rank = Math.max(rank, 2.5);
      else if (h.includes(q)) rank = Math.max(rank, 2);
    }
    if (rank) out.push({ destination: d, rank });
  }
  return out.sort((a, b) => b.rank - a.rank || a.destination.label.localeCompare(b.destination.label));
}

/** Registry integrity, checked by tests: unique ids, routes and default chords. */
export function integrity(): string[] {
  const problems: string[] = [];
  const ids = new Set<string>();
  const routes = new Set<string>();
  const chords = new Map<string, string>();
  for (const d of DESTINATIONS) {
    if (ids.has(d.id)) problems.push(`duplicate id ${d.id}`);
    ids.add(d.id);
    if (routes.has(d.route)) problems.push(`duplicate route ${d.route}`);
    routes.add(d.route);
    if (d.chord) {
      if (!/^[a-z0-9]$/.test(d.chord)) problems.push(`chord ${d.chord} on ${d.id} is not one key`);
      const owner = chords.get(d.chord);
      if (owner) problems.push(`chord ${d.chord} bound to both ${owner} and ${d.id}`);
      chords.set(d.chord, d.id);
    }
    if (!d.availability.length) problems.push(`${d.id} is available nowhere`);
    if (d.quickAction && !d.availability.includes("phone")) problems.push(`${d.id} offers a quick action but is not available on a phone`);
  }
  return problems;
}
