export type RiskLevel = "Low" | "Medium" | "High" | "Critical";

export type Recommendation = {
  sku: string;
  product: string;
  commit: number;
  hist: number;
  fcst: number;
  std: number;
  spot: number;
  short: RiskLevel;
  waste: RiskLevel;
  status: "Auto-approved" | "Needs review";
  why: string;
};

export type Loss = {
  sku: string;
  product: string;
  spot: number;
  waste: number;
  total: number;
  reason: string;
  action: string;
};

export type SupplierRow = {
  id: string;
  supplier: string;
  product: string;
  committed: number;
  received: number;
  fill: number;
  rej: number;
  late: number;
  spotR: number;
  deliv: number;
  risk: RiskLevel;
};

export type BuyerRow = {
  buyer: string;
  product: string;
  lines: number;
  avg: number;
  cv: number;
  lost: number;
  fill: number;
  risk: RiskLevel;
};

export type DQRow = {
  dataset: string;
  rows: number;
  completeness: number;
  status: "Strong" | "Usable with caveats" | "Weak";
  note: string;
};

export type ReportRow = {
  id: string;
  name: string;
  type: string;
  date: string;
  status: "Sent" | "Draft" | "Archived";
  pages: number | string;
  by: string;
};

export type Alert = {
  sev: "critical" | "high" | "medium";
  text: string;
  when: string;
};

export const RECS: Recommendation[] = [
  { sku: "P-1041", product: "Organic Romaine", commit: 4200, hist: 4500, fcst: 4180, std: 380, spot: 0.06, short: "Low", waste: "Medium", status: "Auto-approved",
    why: "Forecast is 7% below trailing average, driven by softer Bay District Schools demand (term break). Holding at 4,200kg keeps fill rate >97% with minimal waste tail." },
  { sku: "P-1102", product: "Heirloom Tomato", commit: 1850, hist: 1620, fcst: 1910, std: 240, spot: 0.21, short: "High", waste: "Low", status: "Needs review",
    why: "Field & Fork Cafés ramped 2 new locations; demand 18% above trailing 8wk. Verde Valley Farms reliability has dipped (87%), recommend split commit with Sunset Pacific." },
  { sku: "P-1156", product: "Lacinato Kale", commit: 980, hist: 1150, fcst: 920, std: 95, spot: 0.04, short: "Low", waste: "High", status: "Needs review",
    why: "Three weeks of soft sell-through at Foothill and Hillcrest. Reduce 15% to avoid weekend spoilage; pair with markdown plan for any overage." },
  { sku: "P-1203", product: "Hass Avocado", commit: 2600, hist: 2200, fcst: 2640, std: 310, spot: 0.34, short: "Critical", waste: "Low", status: "Needs review",
    why: "Spot exposure 34%, well above 15% threshold. Mexican supply tightening; lock additional 600kg with Sunset Pacific by Tue to avoid expected $1.40/kg premium." },
  { sku: "P-1217", product: "Rainbow Carrot", commit: 1320, hist: 1280, fcst: 1310, std: 120, spot: 0.08, short: "Low", waste: "Low", status: "Auto-approved",
    why: "Stable demand, well-supplied by Mountain Ridge Co-op. Carrying historical commit forward." },
  { sku: "P-1284", product: "Baby Spinach", commit: 2240, hist: 2100, fcst: 2270, std: 200, spot: 0.12, short: "Medium", waste: "Medium", status: "Auto-approved",
    why: "Slight uptick from Cedar Hospital meal-program expansion. Cascade Organics has confirmed availability through W22." },
  { sku: "P-1301", product: "Zucchini Squash", commit: 1680, hist: 1900, fcst: 1640, std: 175, spot: 0.05, short: "Low", waste: "High", status: "Needs review",
    why: "Repeated waste events on Mondays after weekend dip. Reduce commit 12% and shift delivery cadence Wed/Fri vs Mon/Thu." },
  { sku: "P-1318", product: "Cremini Mushroom", commit: 740, hist: 690, fcst: 760, std: 80, spot: 0.18, short: "Medium", waste: "Low", status: "Auto-approved",
    why: "Steady demand from Field & Fork. Hidden Creek reliability 94%, on contract through Q3." },
  { sku: "P-1399", product: "Green Bell Pepper", commit: 1100, hist: 980, fcst: 1140, std: 130, spot: 0.16, short: "Medium", waste: "Low", status: "Auto-approved",
    why: "Independent grocers running summer salsa promo W21 to W23. Slight uplift expected; Sunset Pacific has capacity." },
  { sku: "P-1420", product: "Strawberry, 1lb", commit: 880, hist: 940, fcst: 860, std: 140, spot: 0.27, short: "High", waste: "High", status: "Needs review",
    why: "High-risk SKU, both shelf life and spot exposure. Coastal weather forecast suggests yield pressure; recommend daily-replenish cadence and tighter pre-orders." },
  { sku: "P-1456", product: "Blueberry, pint", commit: 620, hist: 540, fcst: 640, std: 90, spot: 0.22, short: "Medium", waste: "Medium", status: "Auto-approved",
    why: "Peak season starting; commit increase aligned with import calendar. Riverbend Growers has confirmed allocation." },
  { sku: "P-1488", product: "Yellow Onion", commit: 3100, hist: 3050, fcst: 3110, std: 95, spot: 0.02, short: "Low", waste: "Low", status: "Auto-approved",
    why: "Commodity-stable. Long shelf, multi-supplier coverage. No action required." },
];

export const LOSSES: Loss[] = [
  { sku: "P-1203", product: "Hass Avocado",     spot: 14820, waste: 3120, total: 17940, reason: "Quality rejection", action: "Lock 60-day commit + qualify 2nd source" },
  { sku: "P-1102", product: "Heirloom Tomato",  spot:  9740, waste: 5210, total: 14950, reason: "Cold chain failure", action: "Audit Verde Valley reefer chain" },
  { sku: "P-1420", product: "Strawberry, 1lb",  spot:  6810, waste: 7240, total: 14050, reason: "Shelf life",         action: "Move to daily replenish + pre-order" },
  { sku: "P-1156", product: "Lacinato Kale",    spot:  1100, waste: 6480, total:  7580, reason: "Demand miss",        action: "Reduce commit 15%, add markdown rule" },
  { sku: "P-1301", product: "Zucchini Squash",  spot:  1840, waste: 4970, total:  6810, reason: "Over-commitment",    action: "Shift cadence Wed/Fri" },
  { sku: "P-1456", product: "Blueberry, pint",  spot:  3920, waste: 2410, total:  6330, reason: "Shelf life",         action: "Tighten on-hand to 1.5d" },
  { sku: "P-1284", product: "Baby Spinach",     spot:  3100, waste: 2980, total:  6080, reason: "Quality rejection",  action: "Add 2nd grower for redundancy" },
  { sku: "P-1399", product: "Green Bell Pepper",spot:  2240, waste: 1660, total:  3900, reason: "Demand miss",        action: "No change, in tolerance" },
];

export const SUP_REL: SupplierRow[] = [
  { id: "S-101", supplier: "Verde Valley Farms",   product: "Heirloom Tomato",  committed: 14200, received: 12380, fill: 0.872, rej: 0.068, late: 0.13, spotR: 0.21, deliv: 24, risk: "High" },
  { id: "S-104", supplier: "Sunset Pacific",       product: "Hass Avocado",     committed: 26100, received: 24960, fill: 0.956, rej: 0.024, late: 0.06, spotR: 0.08, deliv: 31, risk: "Low" },
  { id: "S-103", supplier: "Cascade Organics",     product: "Baby Spinach",     committed: 22400, received: 21500, fill: 0.960, rej: 0.030, late: 0.05, spotR: 0.04, deliv: 28, risk: "Low" },
  { id: "S-102", supplier: "Mountain Ridge Co-op", product: "Rainbow Carrot",   committed: 13200, received: 13050, fill: 0.989, rej: 0.012, late: 0.02, spotR: 0.01, deliv: 22, risk: "Low" },
  { id: "S-105", supplier: "Riverbend Growers",    product: "Blueberry, pint",  committed:  6200, received:  5720, fill: 0.923, rej: 0.041, late: 0.09, spotR: 0.13, deliv: 18, risk: "Medium" },
  { id: "S-106", supplier: "Hidden Creek Farms",   product: "Cremini Mushroom", committed:  7400, received:  6960, fill: 0.941, rej: 0.034, late: 0.06, spotR: 0.05, deliv: 26, risk: "Low" },
  { id: "S-107", supplier: "Blue Sky Produce",     product: "Strawberry, 1lb",  committed:  8800, received:  7340, fill: 0.834, rej: 0.084, late: 0.18, spotR: 0.27, deliv: 21, risk: "Critical" },
  { id: "S-108", supplier: "Three Sisters Farm",   product: "Zucchini Squash",  committed: 16800, received: 16100, fill: 0.958, rej: 0.022, late: 0.04, spotR: 0.03, deliv: 25, risk: "Low" },
];

export const BUYER_DEM: BuyerRow[] = [
  { buyer: "Foothill Market",      product: "Mixed produce", lines: 412, avg:  870, cv: 0.18, lost: 0.02, fill: 0.97, risk: "Low" },
  { buyer: "Hillcrest Co-op",      product: "Mixed produce", lines: 386, avg:  740, cv: 0.22, lost: 0.03, fill: 0.96, risk: "Low" },
  { buyer: "Bay District Schools", product: "Mixed produce", lines: 198, avg: 1480, cv: 0.41, lost: 0.07, fill: 0.92, risk: "High" },
  { buyer: "Cedar Hospital",       product: "Mixed produce", lines: 224, avg:  920, cv: 0.16, lost: 0.01, fill: 0.98, risk: "Low" },
  { buyer: "Field & Fork Cafés",   product: "Mixed produce", lines: 312, avg:  540, cv: 0.34, lost: 0.05, fill: 0.94, risk: "Medium" },
  { buyer: "North Shore Bistro",   product: "Mixed produce", lines: 156, avg:  280, cv: 0.48, lost: 0.09, fill: 0.89, risk: "Critical" },
  { buyer: "Verdant Café",         product: "Mixed produce", lines: 174, avg:  320, cv: 0.31, lost: 0.04, fill: 0.95, risk: "Medium" },
  { buyer: "Crescent Foods",       product: "Mixed produce", lines: 268, avg: 1620, cv: 0.20, lost: 0.02, fill: 0.97, risk: "Low" },
];

export const DQ: DQRow[] = [
  { dataset: "Orders",                rows: 78420, completeness: 0.998, status: "Strong", note: "52 weeks of order lines, all fields populated." },
  { dataset: "Order Lines",           rows: 184320, completeness: 0.996, status: "Strong", note: "SKU + buyer + qty present." },
  { dataset: "Purchase Orders",       rows: 12480, completeness: 0.991, status: "Strong", note: "18 weeks live, 34 weeks backfilled." },
  { dataset: "Deliveries",            rows: 11860, completeness: 0.974, status: "Strong", note: "Reject quantities sometimes posted next-day." },
  { dataset: "Waste Events",          rows:  3140, completeness: 0.812, status: "Usable with caveats", note: "Reason code missing on 19% of events." },
  { dataset: "Spot Purchases",        rows:   840, completeness: 0.943, status: "Strong", note: "Captured via PO override flag." },
  { dataset: "Suppliers",             rows:    34, completeness: 1.000, status: "Strong", note: "" },
  { dataset: "Buyers",                rows:    62, completeness: 1.000, status: "Strong", note: "" },
  { dataset: "Products",              rows:   148, completeness: 0.987, status: "Strong", note: "2 SKUs missing shelf-life days." },
  { dataset: "Locations",             rows:    18, completeness: 1.000, status: "Strong", note: "" },
  { dataset: "Weather (NOAA)",        rows: 38240, completeness: 0.890, status: "Usable with caveats", note: "11 days missing for Salinas station." },
  { dataset: "USDA AMS prices",       rows:  6240, completeness: 0.760, status: "Usable with caveats", note: "Org strawberry pricing intermittent." },
  { dataset: "Backtest Results",      rows: 12,    completeness: 1.000, status: "Strong", note: "12 origins, 4-week horizon." },
  { dataset: "Planning Recommendations", rows: 12, completeness: 1.000, status: "Strong", note: "Latest run: 2026-04-30." },
];

export const REPORTS: ReportRow[] = [
  { id: "R-2604", name: "Foothill Market, Q1 ROI memo",   type: "ROI memo",   date: "Apr 28, 2026", status: "Sent",     pages: 4, by: "AS" },
  { id: "R-2603", name: "Cedar Hospital, Q1 ROI memo",    type: "ROI memo",   date: "Apr 26, 2026", status: "Sent",     pages: 5, by: "AS" },
  { id: "R-2602", name: "Field & Fork, Q1 ROI memo",      type: "ROI memo",   date: "Apr 22, 2026", status: "Draft",    pages: 4, by: "JM" },
  { id: "R-2601", name: "Hillcrest Co-op, pilot summary", type: "Summary",    date: "Apr 18, 2026", status: "Sent",     pages: 3, by: "AS" },
  { id: "R-2598", name: "Loss attribution, March",        type: "CSV export", date: "Apr 02, 2026", status: "Archived", pages: "n/a", by: "JM" },
  { id: "R-2596", name: "Foothill Market, Mar update",    type: "ROI memo",   date: "Mar 31, 2026", status: "Sent",     pages: 4, by: "AS" },
];

export const ALERTS: Alert[] = [
  { sev: "critical", text: "Hass Avocado spot exposure 34%, above 15% threshold", when: "2h ago" },
  { sev: "high",     text: "Verde Valley Farms fill reliability dropped to 87%",    when: "5h ago" },
  { sev: "medium",   text: "Strawberry waste rate trending up W19 to W21",             when: "1d ago" },
];

export type CostTrendPoint = { week: number; label: string; baseline: number; optimised: number };

export const COST_TREND: CostTrendPoint[] = (() => {
  const out: CostTrendPoint[] = [];
  for (let i = 0; i < 30; i++) {
    const baseline = 18000 + Math.sin(i / 4) * 1800 + i * 60;
    const optimised = baseline * (0.78 + Math.cos(i / 5) * 0.04) - i * 35;
    out.push({
      week: i,
      label: `W${String(40 + (i % 52)).padStart(2, "0")}`,
      baseline: Math.round(baseline),
      optimised: Math.round(optimised),
    });
  }
  return out;
})();

export type BacktestRow = {
  label: string;
  baseline: number;
  saa: number;
  service: number;
};

export const BACKTEST: BacktestRow[] = (() => {
  // Deterministic, no Math.random in module init to keep SSR + client identical.
  const seeded = (i: number) => {
    const s = Math.sin(i * 12.9898) * 43758.5453;
    return s - Math.floor(s);
  };
  const rows: BacktestRow[] = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date(2025, 6 + Math.floor(i / 4), 1 + (i % 4) * 7);
    rows.push({
      label: `${d.toLocaleString("en", { month: "short" })} W${(i % 4) + 1}`,
      baseline: Math.round(22400 + Math.sin(i) * 1800 + seeded(i) * 600),
      saa:      Math.round(17400 + Math.sin(i) * 1300 + seeded(i + 1) * 300),
      service:  0.948 + (seeded(i + 2) * 0.03 - 0.01),
    });
  }
  return rows;
})();

export const SPOT_TREND = (() => {
  const seeded = (i: number) => {
    const s = Math.sin(i * 9.123) * 12.345;
    return s - Math.floor(s);
  };
  const out: { label: string; val: number }[] = [];
  for (let i = 0; i < 14; i++) {
    out.push({ label: `W${15 + i}`, val: Math.round(1200 + Math.sin(i / 2) * 500 + seeded(i) * 400) });
  }
  return out;
})();

export const WASTE_REASONS = [
  { reason: "Quality rejection",  v: 12480 },
  { reason: "Shelf life",         v:  9620 },
  { reason: "Cold chain failure", v:  6810 },
  { reason: "Demand miss",        v:  5240 },
  { reason: "Over-commitment",    v:  3120 },
  { reason: "Transit damage",     v:  1480 },
];

export const fmt = {
  cur: (v: number | null | undefined, compact = false): string => {
    if (v == null || isNaN(v)) return "n/a";
    if (compact) {
      const a = Math.abs(v);
      if (a >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
      if (a >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
    }
    return `$${Math.round(v).toLocaleString()}`;
  },
  pct: (v: number | null | undefined, d = 1): string =>
    v == null ? "n/a" : `${(v * 100).toFixed(d)}%`,
  kg: (v: number | null | undefined): string =>
    v == null ? "n/a" : `${Math.round(v).toLocaleString()} kg`,
  num: (v: number | null | undefined): string =>
    v == null ? "n/a" : Math.round(v).toLocaleString(),
};

export const RISK_ORDER: RiskLevel[] = ["Critical", "High", "Medium", "Low"];
