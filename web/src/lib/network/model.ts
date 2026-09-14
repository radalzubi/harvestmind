/**
 * Network Twin model.
 *
 * A normalised picture of one distributor's supply network, independent of
 * whichever ZAAD endpoint or fixture produced it. Visual components read only
 * these types; adapters translate raw API payloads into them. Anything an
 * adapter cannot fill stays `null` and is explained in `missing`, so panels
 * can say "not available" instead of inventing a number.
 */

export type NodeKind = "supplier" | "port" | "dc" | "branch" | "customer";
export type EdgeKind = "ocean" | "road" | "transfer" | "supply" | "service";
/** ZAAD operating state, the same four words the optimizer uses. */
export type ZaadState = "LEAN" | "PROTECT" | "ALLOCATE" | "RECOVER";
export type RiskLevel = "low" | "medium" | "high" | "critical";
/** Where a model came from. `workspace` is the operator's own ZAAD data. */
export type Provenance = "workspace" | "illustrative";

export interface GeoPoint {
  lon: number;
  lat: number;
  /** exact: a known facility; approximate: placed by region or lane; unknown: no basis. */
  precision: "exact" | "approximate";
}

export interface RiskState {
  level: RiskLevel;
  /** 0..1, comparable across nodes and lanes. */
  score: number;
  reasons: string[];
  /** Named evidence behind the score (a feed, a delivery history, a PO). */
  evidence: string[];
}

export interface OpenPO {
  id: string;
  sku: string;
  units: number;
  due: string | null;
  status: "open" | "late" | "partial" | "in_transit";
}

export interface Distribution {
  mean: number | null;
  p10: number | null;
  p90: number | null;
  /** Sample count the distribution rests on. */
  n: number | null;
}

/** Kind-specific facts. Every field is optional and nullable by design. */
export interface NodeMetrics {
  // supplier
  fill?: Distribution;
  fillHistory?: Array<{ period: string; fill: number }>;
  leadDays?: Distribution;
  openPOs?: OpenPO[];
  sharedFailureDomains?: string[];
  capacityPerWeek?: number | null;
  // port
  dwellDays?: Distribution;
  congestion?: number | null;
  // dc / branch
  onHandUnits?: number | null;
  onHandValue?: number | null;
  inboundUnits?: number | null;
  serviceTarget?: number | null;
  serviceProjected?: number | null;
  /**
   * Products the plan flags at this place, each with the clause that says what is true of it.
   * `said` is a finished clause because the only producer today is the `no_replenishment` stance,
   * which is "there is no route to resupply this" — not "this runs short", which is a different
   * claim and one the stance does not make.
   */
  shortages?: Array<{ sku: string; units: number; said: string }>;
  excess?: Array<{ sku: string; units: number; weeksOfCover: number }>;
  transferOpportunities?: Array<{ to: string; sku: string; units: number }>;
  protection?: { localUnits: number | null; pooledUnits: number | null };
  // customer
  demandPerWeek?: number | null;
  tier?: string | null;
}

export interface NetworkNode {
  id: string;
  kind: NodeKind;
  name: string;
  subtitle?: string;
  region?: string;
  geo: GeoPoint | null;
  /** 0..1; drives which nodes and labels appear at world zoom. */
  importance: number;
  state: ZaadState;
  risk: RiskState;
  metrics: NodeMetrics;
  skus: string[];
  /** Customer ids served downstream, when known. */
  customers?: string[];
  /** Ids of alternative nodes (an approved second supplier, a sister branch). */
  alternatives?: string[];
  /** What this node's data does not contain, in plain words. */
  missing?: string[];
}

export interface NetworkEdge {
  id: string;
  kind: EdgeKind;
  from: string;
  to: string;
  name: string;
  /** Geographic waypoints [lon, lat]; null when no geometry is known. */
  path: Array<[number, number]> | null;
  leadDays: { normal: number | null; current: number | null; p90: number | null };
  capacityPerWeek: number | null;
  transportCostPerUnit: number | null;
  state: ZaadState;
  risk: RiskState;
  skus: string[];
  /** Alternative lane ids that could carry the same flow. */
  alternatives: string[];
  disruptionEvidence?: string[];
  missing?: string[];
}

export type ShipmentStatus = "in_transit" | "delayed" | "at_port" | "customs" | "delivered";

export interface Shipment {
  id: string;
  edgeId: string;
  ref: string;
  skus: string[];
  units: number;
  status: ShipmentStatus;
  /** 0..1 along the lane; null when position is unknown. */
  progress: number | null;
  eta: string | null;
  etaOriginal: string | null;
}

export interface NetworkRecommendation {
  id: string;
  targetType: "node" | "edge";
  targetId: string;
  state: ZaadState;
  action: string;
  rationale: string;
  /** What the model expects if nobody acts. */
  noAction: string;
  /** optimizer: a real ZAAD plan; illustrative: a labelled demo result. */
  source: "optimizer" | "illustrative";
}

export interface NetworkModel {
  id: string;
  name: string;
  provenance: Provenance;
  asOf: string;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  shipments: Shipment[];
  recommendations: NetworkRecommendation[];
  /** Data-quality notes for the whole model (row counts, missing tables). */
  notes: string[];
  /**
   * The workspace's own currency, so a sentence that quotes money does not assume one.
   *
   * `describe()` printed a site's stock value as `about $5,726` — a hard `$` — three lines from a
   * facts row printing the same number through the workspace's currency. On a workspace that does
   * not trade in dollars the two disagreed, and one of them was simply wrong.
   */
  currency: string;
}

export type SelectionRef = { type: "node" | "edge"; id: string };

/** Plain words for each state; the optimizer's own names stay under Advanced. */
export const STATE_LABEL: Record<ZaadState, string> = {
  LEAN: "Stable", PROTECT: "Risk rising", ALLOCATE: "Supply constrained", RECOVER: "Recovering",
};
export const STATE_TECHNICAL: Record<ZaadState, string> = { LEAN: "LEAN", PROTECT: "PROTECT", ALLOCATE: "ALLOCATE", RECOVER: "RECOVER" };
export const STATE_SENTENCE: Record<ZaadState, string> = {
  LEAN: "Supply is stable.",
  PROTECT: "Risk is rising. ZAAD recommends targeted protection.",
  ALLOCATE: "Supply is constrained. ZAAD is prioritising customers.",
  RECOVER: "Supply is returning to normal.",
};
export const RISK_LABEL: Record<RiskLevel, string> = { low: "Normal", medium: "Watch", high: "Needs attention", critical: "Critical" };
/** Above this score something is an exception worth the executive's eye. */
export const ATTENTION_SCORE = 0.5;
export const WATCH_SCORE = 0.25;

export const KIND_LABEL: Record<NodeKind, string> = {
  supplier: "Supplier", port: "Port", dc: "Distribution centre", branch: "Branch", customer: "Customer",
};

export const EDGE_LABEL: Record<EdgeKind, string> = {
  ocean: "Ocean lane", road: "Road lane", transfer: "Transfer lane", supply: "Supplier relationship",
  service: "Customer commitment",
};

export function riskLevel(score: number): RiskLevel {
  return score >= 0.75 ? "critical" : score >= 0.5 ? "high" : score >= 0.25 ? "medium" : "low";
}

export function stateForRisk(score: number, recovering = false): ZaadState {
  if (recovering) return "RECOVER";
  return score >= 0.6 ? "ALLOCATE" : score >= 0.3 ? "PROTECT" : "LEAN";
}
