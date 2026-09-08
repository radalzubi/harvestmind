/**
 * Illustrative development data.
 *
 * One distributor in Jordan: two regional suppliers (Izmir, Alexandria) and
 * one long international source (Shenzhen) all land at Aqaba, feed a central
 * DC in Amman, two branches and three customer groups. Every number here is
 * invented to exercise the twin; nothing is a measurement.
 */
import { LANE_CATALOG, PORTS, type LonLat } from "./geo";
import type { NetworkEdge, NetworkModel, NetworkNode, NetworkRecommendation, RiskState, Shipment } from "./model";

export const ILLUSTRATIVE_LABEL = "Illustrative development data";

const SKUS = {
  detergent: "SKU-1042 Detergent 5L", softener: "SKU-1051 Softener 2L", rice: "SKU-2210 Rice 10kg",
  oil: "SKU-2318 Sunflower oil 1.8L", tissue: "SKU-3007 Facial tissue 200s", nappies: "SKU-3120 Nappies M 44s",
};

const risk = (score: number, reasons: string[], evidence: string[] = []): RiskState => ({
  level: score >= 0.75 ? "critical" : score >= 0.5 ? "high" : score >= 0.25 ? "medium" : "low", score, reasons, evidence,
});

const exact = (at: LonLat) => ({ lon: at[0], lat: at[1], precision: "exact" as const });

const nodes: NetworkNode[] = [
  {
    id: "sup_a", kind: "supplier", name: "Supplier A", subtitle: "Izmir, Türkiye", region: "TR", geo: exact([27.14, 38.42]),
    importance: 0.8, state: "LEAN",
    risk: risk(0.14, ["Fill has been steady for 9 months", "Lead time inside its own range"], ["62 receipts", "Aegean lane feed"]),
    metrics: {
      fill: { mean: 0.97, p10: 0.91, p90: 1.0, n: 62 },
      fillHistory: [0.98, 0.96, 0.99, 0.95, 0.97, 0.98, 0.94, 0.99, 0.97, 0.96, 0.98, 0.97].map((f, i) => ({ period: `W-${12 - i}`, fill: f })),
      leadDays: { mean: 12, p10: 10, p90: 15, n: 62 },
      openPOs: [{ id: "PO-7731", sku: SKUS.detergent, units: 4800, due: "in 6 days", status: "in_transit" }, { id: "PO-7740", sku: SKUS.softener, units: 2400, due: "in 13 days", status: "open" }],
      sharedFailureDomains: ["Suez Canal", "Port of Aqaba"], capacityPerWeek: 9000,
    },
    skus: [SKUS.detergent, SKUS.softener], alternatives: ["sup_b"],
  },
  {
    id: "sup_b", kind: "supplier", name: "Supplier B", subtitle: "Alexandria, Egypt", region: "EG", geo: exact([29.92, 31.2]),
    importance: 0.7, state: "LEAN",
    risk: risk(0.22, ["Two short deliveries in the last 8 weeks", "Approved alternate for Supplier A on two SKUs"], ["41 receipts"]),
    metrics: {
      fill: { mean: 0.93, p10: 0.82, p90: 1.0, n: 41 },
      fillHistory: [0.95, 0.92, 0.96, 0.9, 0.94, 0.86, 0.95, 0.97, 0.91, 0.84, 0.96, 0.95].map((f, i) => ({ period: `W-${12 - i}`, fill: f })),
      leadDays: { mean: 7, p10: 6, p90: 9, n: 41 },
      openPOs: [{ id: "PO-7736", sku: SKUS.oil, units: 3200, due: "today", status: "in_transit" }],
      sharedFailureDomains: ["Suez Canal", "Port of Aqaba"], capacityPerWeek: 6000,
    },
    skus: [SKUS.oil, SKUS.rice, SKUS.softener], alternatives: ["sup_a"],
  },
  {
    id: "sup_c", kind: "supplier", name: "Supplier C", subtitle: "Shenzhen, China", region: "CN", geo: exact([114.06, 22.54]),
    importance: 0.9, state: "PROTECT",
    risk: risk(0.58, ["Only source for nappies and tissue", "Its lane crosses Bab el-Mandeb, where transits are 38% below the lane's norm"], ["28 receipts", "chokepoint transit feed", "Red Sea shipping coverage"]),
    metrics: {
      fill: { mean: 0.95, p10: 0.86, p90: 1.0, n: 28 },
      fillHistory: [0.97, 0.95, 0.96, 0.94, 0.97, 0.95, 0.93, 0.96, 0.95, 0.9, 0.96, 0.95].map((f, i) => ({ period: `W-${12 - i}`, fill: f })),
      leadDays: { mean: 29, p10: 26, p90: 41, n: 28 },
      openPOs: [{ id: "PO-7702", sku: SKUS.nappies, units: 12000, due: "6 days late", status: "late" }, { id: "PO-7719", sku: SKUS.tissue, units: 9000, due: "in 22 days", status: "open" }],
      sharedFailureDomains: ["Bab el-Mandeb Strait", "Port of Aqaba"], capacityPerWeek: 20000,
    },
    skus: [SKUS.nappies, SKUS.tissue], alternatives: [],
    missing: ["No approved alternate supplier for nappies or tissue"],
  },
  { id: "port_yantian", kind: "port", name: PORTS.yantian.name, subtitle: "Origin port", region: "CN", geo: exact(PORTS.yantian.at), importance: 0.6, state: "LEAN",
    risk: risk(0.1, ["Normal dwell"], ["port call feed"]), metrics: { dwellDays: { mean: 2, p10: 1, p90: 4, n: 28 }, congestion: 0.2 }, skus: [SKUS.nappies, SKUS.tissue] },
  { id: "port_jebel_ali", kind: "port", name: PORTS.jebel_ali.name, subtitle: "Alternative entry", region: "AE", geo: exact(PORTS.jebel_ali.at), importance: 0.4, state: "LEAN",
    risk: risk(0.12, ["Not in use; approved as an alternative entry"], []), metrics: { dwellDays: { mean: 3, p10: 2, p90: 5, n: null }, congestion: 0.3 }, skus: [] },
  { id: "port_aqaba", kind: "port", name: PORTS.aqaba.name, subtitle: "Every inbound container lands here", region: "JO", geo: exact(PORTS.aqaba.at), importance: 1, state: "PROTECT",
    risk: risk(0.46, ["Shared by all three suppliers: one failure domain", "Dwell 4 days against a 2-day norm"], ["port call feed", "3 lanes"]),
    metrics: { dwellDays: { mean: 4, p10: 2, p90: 7, n: 96 }, congestion: 0.55 }, skus: Object.values(SKUS) },
  { id: "dc_amman", kind: "dc", name: "Central DC", subtitle: "Amman", region: "JO", geo: exact([35.93, 31.95]), importance: 1, state: "PROTECT",
    risk: risk(0.38, ["Nappies cover falls to 9 days in week 5 if PO-7702 slips again"], ["inventory snapshot", "open POs"]),
    metrics: { onHandUnits: 61400, onHandValue: 412000, inboundUnits: 31400, serviceTarget: 0.97, serviceProjected: 0.955,
      shortages: [{ sku: SKUS.nappies, units: 2600, when: "week 5" }],
      excess: [{ sku: SKUS.rice, units: 5200, weeksOfCover: 11 }],
      transferOpportunities: [{ to: "Branch North", sku: SKUS.rice, units: 1200 }],
      protection: { localUnits: 4100, pooledUnits: 7800 } },
    skus: Object.values(SKUS) },
  { id: "br_north", kind: "branch", name: "Branch North", subtitle: "Irbid", region: "JO", geo: exact([35.85, 32.55]), importance: 0.8, state: "LEAN",
    risk: risk(0.16, ["Service on target; pooled protection sits at the DC"], ["inventory snapshot"]),
    metrics: { onHandUnits: 12800, onHandValue: 84000, inboundUnits: 3600, serviceTarget: 0.97, serviceProjected: 0.975, shortages: [], excess: [], transferOpportunities: [], protection: { localUnits: 900, pooledUnits: 3100 } },
    skus: Object.values(SKUS), customers: ["cust_north"] },
  { id: "br_south", kind: "branch", name: "Branch South", subtitle: "Ma'an", region: "JO", geo: exact([35.73, 30.19]), importance: 0.8, state: "PROTECT",
    risk: risk(0.42, ["Nappies at 11 days of cover with the late PO", "Serves the HoReCa contract at 99%"], ["inventory snapshot", "customer orders"]),
    metrics: { onHandUnits: 9400, onHandValue: 61000, inboundUnits: 2100, serviceTarget: 0.97, serviceProjected: 0.94,
      shortages: [{ sku: SKUS.nappies, units: 900, when: "week 5" }], excess: [], transferOpportunities: [], protection: { localUnits: 1400, pooledUnits: 2600 } },
    skus: Object.values(SKUS), customers: ["cust_south"] },
  { id: "cust_north", kind: "customer", name: "Retail chains · North", subtitle: "14 stores", region: "JO", geo: exact([35.9, 32.4]), importance: 0.5, state: "LEAN",
    risk: risk(0.1, ["Normal orders"], ["customer orders"]), metrics: { demandPerWeek: 5200, serviceTarget: 0.97, tier: "standard" }, skus: Object.values(SKUS) },
  { id: "cust_south", kind: "customer", name: "HoReCa · South", subtitle: "Hotels and restaurants", region: "JO", geo: exact([35.5, 30.0]), importance: 0.5, state: "PROTECT",
    risk: risk(0.35, ["Contract service at 99%; nappies and tissue exposed in week 5"], ["customer orders"]), metrics: { demandPerWeek: 3100, serviceTarget: 0.99, tier: "contract" }, skus: [SKUS.tissue, SKUS.nappies, SKUS.oil] },
  { id: "cust_key", kind: "customer", name: "Key account · Supermarket group", subtitle: "Served from the DC", region: "JO", geo: exact([35.98, 31.9]), importance: 0.7, state: "LEAN",
    risk: risk(0.2, ["Highest-margin account; on target"], ["customer orders"]), metrics: { demandPerWeek: 7800, serviceTarget: 0.985, tier: "key" }, skus: Object.values(SKUS) },
];

const edges: NetworkEdge[] = [
  { id: "lane_izmir_aqaba", kind: "ocean", from: "sup_a", to: "port_aqaba", name: "Izmir → Aqaba via Suez",
    path: [[27.14, 38.42], [26.2, 37.4], [28.5, 35.2], [31.0, 33.2], [32.3, 31.26], [32.55, 30.0], [32.6, 29.7], [33.3, 28.3], [34.3, 27.6], [34.55, 27.9], [34.65, 28.6], [34.85, 29.3], [35.0, 29.52]],
    leadDays: { normal: 12, current: 12, p90: 15 }, capacityPerWeek: 9000, transportCostPerUnit: 0.31, state: "LEAN",
    risk: risk(0.18, ["Suez transits at norm"], ["chokepoint feed"]), skus: [SKUS.detergent, SKUS.softener], alternatives: [] },
  { id: "lane_alex_aqaba", kind: "ocean", from: "sup_b", to: "port_aqaba", name: "Alexandria → Aqaba via Suez",
    path: [[29.92, 31.2], [31.2, 31.9], [32.3, 31.26], [32.55, 30.0], [32.6, 29.7], [33.3, 28.3], [34.3, 27.6], [34.55, 27.9], [34.65, 28.6], [34.85, 29.3], [35.0, 29.52]],
    leadDays: { normal: 7, current: 7, p90: 9 }, capacityPerWeek: 6000, transportCostPerUnit: 0.22, state: "LEAN",
    risk: risk(0.16, ["Suez transits at norm"], ["chokepoint feed"]), skus: [SKUS.oil, SKUS.rice, SKUS.softener], alternatives: [] },
  { id: "lane_sup_c_yantian", kind: "road", from: "sup_c", to: "port_yantian", name: "Shenzhen plant → Yantian",
    path: [[114.06, 22.54], [114.27, 22.57]], leadDays: { normal: 1, current: 1, p90: 2 }, capacityPerWeek: 20000, transportCostPerUnit: 0.02, state: "LEAN",
    risk: risk(0.05, ["Short drayage"], []), skus: [SKUS.nappies, SKUS.tissue], alternatives: [] },
  { id: "lane_yantian_aqaba", kind: "ocean", from: "port_yantian", to: "port_aqaba", name: "Yantian → Aqaba via Bab el-Mandeb",
    path: [[114.27, 22.57], [112.0, 16.0], [108.5, 8.0], [104.5, 2.0], [103.75, 1.26], [100.6, 3.2], [95.0, 6.0], [80.0, 5.5], [65.0, 10.0], [58.0, 13.0], [48.0, 12.4], [43.35, 12.6], [42.2, 14.5], [40.0, 18.0], [37.6, 22.5], [36.2, 25.5], [34.55, 27.9], [34.65, 28.6], [34.85, 29.3], [35.0, 29.52]],
    leadDays: { normal: 28, current: 34, p90: 41 }, capacityPerWeek: 20000, transportCostPerUnit: 0.38, state: "PROTECT",
    risk: risk(0.64, ["Bab el-Mandeb transits 38% below the lane's 365-day norm", "Red Sea shipping coverage 2.4× its usual level", "PO-7702 already 6 days late"], ["chokepoint transit feed", "news coverage index", "receipts"]),
    skus: [SKUS.nappies, SKUS.tissue], alternatives: ["lane_yantian_jebel_ali"],
    disruptionEvidence: ["Chokepoint transit index 0.62 (7-day mean vs 365-day median)", "Conflict coverage index 2.4", "Carrier advisory: +6 days Cape routing"] },
  { id: "lane_yantian_jebel_ali", kind: "ocean", from: "port_yantian", to: "port_jebel_ali", name: "Yantian → Jebel Ali via Hormuz (alternative)",
    path: [[114.27, 22.57], [112.0, 16.0], [108.5, 8.0], [104.5, 2.0], [103.75, 1.26], [100.6, 3.2], [95.0, 6.0], [80.0, 5.5], [65.0, 10.0], [58.0, 13.0], [59.0, 22.0], [57.2, 24.6], [56.3, 26.55], [55.06, 25.01]],
    leadDays: { normal: 22, current: 22, p90: 27 }, capacityPerWeek: 8000, transportCostPerUnit: 0.36, state: "LEAN",
    risk: risk(0.2, ["Standby: approved, not in use", "Crosses Hormuz instead of Bab el-Mandeb"], ["chokepoint feed"]), skus: [SKUS.nappies, SKUS.tissue], alternatives: ["lane_yantian_aqaba"] },
  { id: "lane_jebel_ali_amman", kind: "road", from: "port_jebel_ali", to: "dc_amman", name: LANE_CATALOG.road_saudi.name + " (alternative)",
    path: LANE_CATALOG.road_saudi.path, leadDays: { normal: 5, current: 5, p90: 7 }, capacityPerWeek: 8000, transportCostPerUnit: 0.44, state: "LEAN",
    risk: risk(0.15, ["Standby road corridor", "Two border crossings"], []), skus: [SKUS.nappies, SKUS.tissue], alternatives: [] },
  { id: "lane_aqaba_amman", kind: "road", from: "port_aqaba", to: "dc_amman", name: "Aqaba → Amman (Desert Highway)",
    path: [[35.0, 29.52], [35.6, 30.5], [35.9, 31.4], [35.93, 31.95]], leadDays: { normal: 1, current: 1, p90: 2 }, capacityPerWeek: 40000, transportCostPerUnit: 0.05, state: "LEAN",
    risk: risk(0.08, ["Own fleet; daily"], []), skus: Object.values(SKUS), alternatives: [] },
  { id: "xfer_dc_north", kind: "transfer", from: "dc_amman", to: "br_north", name: "Transfer Amman → Irbid",
    path: [[35.93, 31.95], [35.85, 32.55]], leadDays: { normal: 1, current: 1, p90: 1 }, capacityPerWeek: 15000, transportCostPerUnit: 0.03, state: "LEAN",
    risk: risk(0.05, ["Daily shuttle"], []), skus: Object.values(SKUS), alternatives: [] },
  { id: "xfer_dc_south", kind: "transfer", from: "dc_amman", to: "br_south", name: "Transfer Amman → Ma'an",
    path: [[35.93, 31.95], [35.73, 30.19]], leadDays: { normal: 1, current: 1, p90: 2 }, capacityPerWeek: 12000, transportCostPerUnit: 0.04, state: "PROTECT",
    risk: risk(0.3, ["Carries the protection the south will need in week 5"], []), skus: Object.values(SKUS), alternatives: [] },
  { id: "lane_north_cust", kind: "road", from: "br_north", to: "cust_north", name: "Irbid delivery rounds",
    path: [[35.85, 32.55], [35.9, 32.4]], leadDays: { normal: 0, current: 0, p90: 1 }, capacityPerWeek: 9000, transportCostPerUnit: 0.02, state: "LEAN", risk: risk(0.05, ["Same day"], []), skus: Object.values(SKUS), alternatives: [] },
  { id: "lane_south_cust", kind: "road", from: "br_south", to: "cust_south", name: "Southern HoReCa rounds",
    path: [[35.73, 30.19], [35.5, 30.0]], leadDays: { normal: 0, current: 0, p90: 1 }, capacityPerWeek: 5000, transportCostPerUnit: 0.03, state: "LEAN", risk: risk(0.1, ["Same day"], []), skus: [SKUS.tissue, SKUS.nappies, SKUS.oil], alternatives: [] },
  { id: "lane_dc_key", kind: "road", from: "dc_amman", to: "cust_key", name: "DC → key account",
    path: [[35.93, 31.95], [35.98, 31.9]], leadDays: { normal: 0, current: 0, p90: 1 }, capacityPerWeek: 12000, transportCostPerUnit: 0.02, state: "LEAN", risk: risk(0.05, ["Same day"], []), skus: Object.values(SKUS), alternatives: [] },
];

const shipments: Shipment[] = [
  { id: "shp_1", edgeId: "lane_yantian_aqaba", ref: "MSKU 884 213 · PO-7702", skus: [SKUS.nappies], units: 12000, status: "delayed", progress: 0.58, eta: "in 9 days", etaOriginal: "in 3 days" },
  { id: "shp_2", edgeId: "lane_izmir_aqaba", ref: "PO-7731", skus: [SKUS.detergent], units: 4800, status: "in_transit", progress: 0.35, eta: "in 6 days", etaOriginal: "in 6 days" },
  { id: "shp_3", edgeId: "lane_alex_aqaba", ref: "PO-7736", skus: [SKUS.oil], units: 3200, status: "customs", progress: 0.97, eta: "today", etaOriginal: "today" },
  { id: "shp_4", edgeId: "lane_aqaba_amman", ref: "Truck 14 · rice", skus: [SKUS.rice], units: 2600, status: "in_transit", progress: 0.5, eta: "today", etaOriginal: "today" },
];

const recommendations: NetworkRecommendation[] = [
  { id: "rec_1", targetType: "edge", targetId: "lane_yantian_aqaba", state: "PROTECT", source: "illustrative",
    action: "Bring PO-7719 forward 8 days and hold 14% more nappies at the Central DC until PO-7702 lands.",
    rationale: "The lane's lead-time tail widened from 33 to 41 days; the DC, not the branches, is where that protection is cheapest.",
    noAction: "Nappies cover at Branch South falls to 4 days in week 5; HoReCa contract service drops to about 0.91." },
  { id: "rec_2", targetType: "node", targetId: "sup_c", state: "PROTECT", source: "illustrative",
    action: "Qualify Supplier B as an alternate for tissue (it already holds the softener approval).",
    rationale: "Supplier C is the only source for two SKUs and shares the Bab el-Mandeb failure domain with nothing else in the network that could replace it.",
    noAction: "Any further slip on the Red Sea lane has no substitute; the exposure stays." },
  { id: "rec_3", targetType: "node", targetId: "dc_amman", state: "LEAN", source: "illustrative",
    action: "Transfer 1,200 units of rice to Branch North instead of re-ordering there.",
    rationale: "The DC holds 11 weeks of rice cover; the branch is at 3.",
    noAction: "Roughly $4,100 of rice sits idle at the DC while the branch re-orders." },
];

export const ILLUSTRATIVE_NETWORK: NetworkModel = {
  id: "illustrative-jo-distributor",
  name: "Illustrative distributor · Jordan",
  provenance: "illustrative",
  asOf: "development fixture",
  nodes, edges, shipments, recommendations,
  notes: [ILLUSTRATIVE_LABEL, "Every figure is invented to exercise the twin. Connect a workspace key to see your own network."],
};
