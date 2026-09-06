/**
 * Illustrative demo model for /how-it-works. Every number here is a designed example for a
 * hypothetical distributor ("the demo"), labelled ILLUSTRATIVE on the page. Nothing is a
 * customer result and nothing is derived from a live workspace.
 */
export type Mode = "LEAN" | "PROTECT" | "ALLOCATE" | "RECOVER";
export type Disruption = "supplier_delay" | "port_closure" | "demand_surge" | "fill_drop";
export type Scenario = "stable" | "volatile" | "supplier_delay" | "demand_surge";

export const NODES = [
  { id: "sup_a", kind: "supplier", label: "Supplier A", x: 60, y: 90 },
  { id: "sup_b", kind: "supplier", label: "Supplier B", x: 60, y: 230 },
  { id: "port", kind: "port", label: "Port", x: 250, y: 160 },
  { id: "dc", kind: "dc", label: "Central DC", x: 450, y: 160 },
  { id: "br_n", kind: "branch", label: "Branch North", x: 650, y: 70 },
  { id: "br_s", kind: "branch", label: "Branch South", x: 650, y: 250 },
  { id: "cust", kind: "customer", label: "Customers", x: 840, y: 160 },
] as const;

export const EDGES = [
  { id: "a_port", from: "sup_a", to: "port", route: true },
  { id: "b_port", from: "sup_b", to: "port", route: true },
  { id: "port_dc", from: "port", to: "dc", route: true },
  { id: "dc_n", from: "dc", to: "br_n", route: false },
  { id: "dc_s", from: "dc", to: "br_s", route: false },
  { id: "n_cust", from: "br_n", to: "cust", route: false },
  { id: "s_cust", from: "br_s", to: "cust", route: false },
] as const;

/** Node inspection facts, per mode (illustrative). */
export const NODE_FACTS: Record<string, Record<Mode, { inventory: string; pipeline: string; lead: string; exposure: string }>> = {
  sup_a: {
    LEAN: { inventory: "n/a", pipeline: "2 open POs, 360 cases", lead: "21 d, tail 24 d", exposure: "normal" },
    PROTECT: { inventory: "n/a", pipeline: "2 open POs, 360 cases", lead: "21 d, tail 33 d", exposure: "elevated: lead-time tail widened" },
    ALLOCATE: { inventory: "n/a", pipeline: "1 open PO late", lead: "35 d observed", exposure: "shortage" },
    RECOVER: { inventory: "n/a", pipeline: "1 open PO", lead: "22 d, tail 25 d", exposure: "normalising" },
  },
  sup_b: {
    LEAN: { inventory: "n/a", pipeline: "none", lead: "18 d", exposure: "approved alternate, not used" },
    PROTECT: { inventory: "n/a", pipeline: "1 open PO, 120 cases", lead: "18 d", exposure: "30% of next order moved here" },
    ALLOCATE: { inventory: "n/a", pipeline: "1 open PO, 120 cases", lead: "18 d", exposure: "primary source during shortage" },
    RECOVER: { inventory: "n/a", pipeline: "none", lead: "18 d", exposure: "standing by" },
  },
  port: {
    LEAN: { inventory: "in transit 360", pipeline: "2 vessels", lead: "dwell 2 d", exposure: "shared by both suppliers" },
    PROTECT: { inventory: "in transit 480", pipeline: "3 vessels", lead: "dwell 6 d", exposure: "congestion: shared failure domain" },
    ALLOCATE: { inventory: "in transit 480", pipeline: "closed", lead: "n/a", exposure: "closure" },
    RECOVER: { inventory: "in transit 240", pipeline: "2 vessels", lead: "dwell 2 d", exposure: "reopened, 4 clean arrivals" },
  },
  dc: {
    LEAN: { inventory: "1,240 cases", pipeline: "360 inbound", lead: "transfer to branch 1 d", exposure: "pooled stock for two branches" },
    PROTECT: { inventory: "1,540 cases", pipeline: "480 inbound", lead: "transfer 1 d", exposure: "holds the protection centrally" },
    ALLOCATE: { inventory: "410 cases", pipeline: "480 late", lead: "transfer 1 d", exposure: "scarce: allocating by priority" },
    RECOVER: { inventory: "1,380 cases", pipeline: "240 inbound", lead: "transfer 1 d", exposure: "draining temporary stock" },
  },
  br_n: {
    LEAN: { inventory: "180 cases", pipeline: "transfer 60", lead: "service same day", exposure: "supermarket contract 99%" },
    PROTECT: { inventory: "220 cases", pipeline: "transfer 90", lead: "same day", exposure: "protected: +6 days" },
    ALLOCATE: { inventory: "90 cases", pipeline: "transfer 120", lead: "same day", exposure: "priority customer served first" },
    RECOVER: { inventory: "200 cases", pipeline: "transfer 40", lead: "same day", exposure: "back to local service stock" },
  },
  br_s: {
    LEAN: { inventory: "140 cases", pipeline: "transfer 40", lead: "same day", exposure: "wholesale 95%, spot 90%" },
    PROTECT: { inventory: "140 cases", pipeline: "transfer 40", lead: "same day", exposure: "no change: not exposed" },
    ALLOCATE: { inventory: "60 cases", pipeline: "transfer 40", lead: "same day", exposure: "spot orders deferred" },
    RECOVER: { inventory: "140 cases", pipeline: "transfer 40", lead: "same day", exposure: "unchanged" },
  },
  cust: {
    LEAN: { inventory: "n/a", pipeline: "n/a", lead: "n/a", exposure: "all targets met" },
    PROTECT: { inventory: "n/a", pipeline: "n/a", lead: "n/a", exposure: "targets met with protection" },
    ALLOCATE: { inventory: "n/a", pipeline: "n/a", lead: "n/a", exposure: "99% and 95% met, 90% spot short" },
    RECOVER: { inventory: "n/a", pipeline: "n/a", lead: "n/a", exposure: "all targets met" },
  },
};

/** SKU table for the mode sections (illustrative). */
export const SKUS = [
  { id: "SKU A", desc: "Import, Supplier A via port", exposed: ["supplier_delay", "port_closure"] as Disruption[] },
  { id: "SKU B", desc: "Import, Supplier A, trending up", exposed: ["supplier_delay", "port_closure", "demand_surge"] as Disruption[] },
  { id: "SKU C", desc: "Local supplier, 3-day lead", exposed: [] as Disruption[] },
  { id: "SKU D", desc: "Import, Supplier B, substitute approved", exposed: ["port_closure", "fill_drop"] as Disruption[] },
  { id: "SKU E", desc: "Slow mover, transfer from DC", exposed: [] as Disruption[] },
];

/** Candidate decisions in the decision lab, with illustrative outcome scores 0..1 (higher = better) except inventory/capital (higher = more). */
export const CANDIDATES = [
  { id: "keep", label: "Do nothing", service: .91, inventory: .42, capital: .40, shortage: .30, risk: .38, cost: .35 },
  { id: "more", label: "Order more", service: .97, inventory: .78, capital: .80, shortage: .10, risk: .22, cost: .62 },
  { id: "less", label: "Order less", service: .86, inventory: .30, capital: .28, shortage: .48, risk: .55, cost: .30 },
  { id: "defer", label: "Defer PO 1842", service: .93, inventory: .38, capital: .30, shortage: .22, risk: .32, cost: .28 },
  { id: "transfer", label: "Transfer 120 cases", service: .96, inventory: .44, capital: .40, shortage: .12, risk: .26, cost: .31 },
  { id: "sub", label: "Use approved substitute", service: .95, inventory: .40, capital: .38, shortage: .15, risk: .30, cost: .36 },
  { id: "source", label: "Split to Supplier B", service: .96, inventory: .46, capital: .44, shortage: .12, risk: .18, cost: .41 },
  { id: "expedite", label: "Expedite", service: .97, inventory: .48, capital: .46, shortage: .09, risk: .24, cost: .58 },
  { id: "deexpedite", label: "De-expedite", service: .92, inventory: .36, capital: .32, shortage: .26, risk: .36, cost: .27 },
  { id: "allocate", label: "Allocate by priority", service: .94, inventory: .42, capital: .40, shortage: .18, risk: .28, cost: .33 },
] as const;

export const ACTIONS = ["Do nothing", "Buy", "Buy less", "Defer", "Cancel", "Reschedule", "Expedite", "De-expedite", "Transfer", "Substitute", "Allocate", "Change supplier", "Change route"] as const;

/** Before / after comparison (illustrative). */
export const COMPARE = {
  current: { service: .91, inventory: 1.9, capital: 412, risk: .38, changed: 0, untouched: 34 },
  zaad: { service: .96, inventory: 1.6, capital: 356, risk: .24, changed: 3, untouched: 31 },
};

/** Series for the uncertainty lab: 26 periods of demand, lead time, fill (illustrative). */
export function series(scenario: Scenario) {
  const n = 26;
  const demand: number[] = [];
  const lead: number[] = [];
  const fill: number[] = [];
  let seed = 7;
  const rnd = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280 - .5; };
  for (let i = 0; i < n; i++) {
    let d = 100 + rnd() * (scenario === "volatile" ? 60 : 16);
    if (scenario === "demand_surge" && i >= 16) d = 145 + rnd() * 20;
    let l = 21 + rnd() * 2;
    if (scenario === "supplier_delay" && i >= 14) l = 26 + Math.abs(rnd()) * 14;
    let f = .96 + rnd() * .03;
    if (scenario === "supplier_delay" && i >= 14) f = .84 + rnd() * .1;
    demand.push(Math.round(d)); lead.push(Math.round(l)); fill.push(Math.round(f * 100) / 100);
  }
  const bandDemand = scenario === "volatile" ? 34 : scenario === "demand_surge" ? 26 : 12;
  const bandLead = scenario === "supplier_delay" ? 11 : 2;
  return { demand, lead, fill, bandDemand, bandLead };
}

/** Arabic rendering of the node inspection facts (same figures, same modes). */
export const NODE_FACTS_AR: typeof NODE_FACTS = {
  sup_a: {
    LEAN: { inventory: "لا ينطبق", pipeline: "أمرا شراء مفتوحان، 360 كرتونة", lead: "21 يوماً، الذيل 24", exposure: "طبيعي" },
    PROTECT: { inventory: "لا ينطبق", pipeline: "أمرا شراء مفتوحان، 360 كرتونة", lead: "21 يوماً، الذيل 33", exposure: "مرتفع: اتسع ذيل الليد تايم" },
    ALLOCATE: { inventory: "لا ينطبق", pipeline: "أمر شراء واحد متأخر", lead: "35 يوماً مرصودة", exposure: "نقص" },
    RECOVER: { inventory: "لا ينطبق", pipeline: "أمر شراء واحد", lead: "22 يوماً، الذيل 25", exposure: "يعود إلى الطبيعي" },
  },
  sup_b: {
    LEAN: { inventory: "لا ينطبق", pipeline: "لا شيء", lead: "18 يوماً", exposure: "بديل معتمد، غير مستخدم" },
    PROTECT: { inventory: "لا ينطبق", pipeline: "أمر شراء واحد، 120 كرتونة", lead: "18 يوماً", exposure: "30٪ من الطلبية القادمة نُقلت إلى هنا" },
    ALLOCATE: { inventory: "لا ينطبق", pipeline: "أمر شراء واحد، 120 كرتونة", lead: "18 يوماً", exposure: "المصدر الأساسي أثناء النقص" },
    RECOVER: { inventory: "لا ينطبق", pipeline: "لا شيء", lead: "18 يوماً", exposure: "على أهبة الاستعداد" },
  },
  port: {
    LEAN: { inventory: "في الطريق 360", pipeline: "باخرتان", lead: "مكوث يومان", exposure: "مشترك بين المورّدين" },
    PROTECT: { inventory: "في الطريق 480", pipeline: "ثلاث بواخر", lead: "مكوث 6 أيام", exposure: "ازدحام: نطاق فشل مشترك" },
    ALLOCATE: { inventory: "في الطريق 480", pipeline: "مغلق", lead: "لا ينطبق", exposure: "إغلاق" },
    RECOVER: { inventory: "في الطريق 240", pipeline: "باخرتان", lead: "مكوث يومان", exposure: "أعيد فتحه، 4 وصولات نظيفة" },
  },
  dc: {
    LEAN: { inventory: "1,240 كرتونة", pipeline: "360 واردة", lead: "تحويل للفرع يوم واحد", exposure: "مخزون مجمّع لفرعين" },
    PROTECT: { inventory: "1,540 كرتونة", pipeline: "480 واردة", lead: "تحويل يوم واحد", exposure: "يحمل الحماية مركزياً" },
    ALLOCATE: { inventory: "410 كراتين", pipeline: "480 متأخرة", lead: "تحويل يوم واحد", exposure: "شحيح: توزيع حسب الأولوية" },
    RECOVER: { inventory: "1,380 كرتونة", pipeline: "240 واردة", lead: "تحويل يوم واحد", exposure: "تصريف المخزون المؤقت" },
  },
  br_n: {
    LEAN: { inventory: "180 كرتونة", pipeline: "تحويل 60", lead: "خدمة في اليوم نفسه", exposure: "عقد سوبرماركت 99٪" },
    PROTECT: { inventory: "220 كرتونة", pipeline: "تحويل 90", lead: "اليوم نفسه", exposure: "محمي: +6 أيام" },
    ALLOCATE: { inventory: "90 كرتونة", pipeline: "تحويل 120", lead: "اليوم نفسه", exposure: "العميل ذو الأولوية يُخدم أولاً" },
    RECOVER: { inventory: "200 كرتونة", pipeline: "تحويل 40", lead: "اليوم نفسه", exposure: "عودة إلى مخزون الخدمة المحلي" },
  },
  br_s: {
    LEAN: { inventory: "140 كرتونة", pipeline: "تحويل 40", lead: "اليوم نفسه", exposure: "جملة 95٪، فوري 90٪" },
    PROTECT: { inventory: "140 كرتونة", pipeline: "تحويل 40", lead: "اليوم نفسه", exposure: "لا تغيير: غير معرّض" },
    ALLOCATE: { inventory: "60 كرتونة", pipeline: "تحويل 40", lead: "اليوم نفسه", exposure: "الطلبات الفورية مؤجلة" },
    RECOVER: { inventory: "140 كرتونة", pipeline: "تحويل 40", lead: "اليوم نفسه", exposure: "دون تغيير" },
  },
  cust: {
    LEAN: { inventory: "لا ينطبق", pipeline: "لا ينطبق", lead: "لا ينطبق", exposure: "كل الأهداف محققة" },
    PROTECT: { inventory: "لا ينطبق", pipeline: "لا ينطبق", lead: "لا ينطبق", exposure: "الأهداف محققة مع الحماية" },
    ALLOCATE: { inventory: "لا ينطبق", pipeline: "لا ينطبق", lead: "لا ينطبق", exposure: "99٪ و95٪ محققان، الفوري 90٪ ناقص" },
    RECOVER: { inventory: "لا ينطبق", pipeline: "لا ينطبق", lead: "لا ينطبق", exposure: "كل الأهداف محققة" },
  },
};
