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
export type EdgeKind = "ocean" | "road" | "transfer" | "supply";
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
  shortages?: Array<{ sku: string; units: number; when: string }>;
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
}

export type SelectionRef = { type: "node" | "edge"; id: string };

export const STATE_LABEL: Record<ZaadState, string> = {
  LEAN: "Lean", PROTECT: "Protect", ALLOCATE: "Allocate", RECOVER: "Recover",
};

export const KIND_LABEL: Record<NodeKind, string> = {
  supplier: "Supplier", port: "Port", dc: "Distribution centre", branch: "Branch", customer: "Customer",
};

export const EDGE_LABEL: Record<EdgeKind, string> = {
  ocean: "Ocean lane", road: "Road lane", transfer: "Transfer lane", supply: "Supplier relationship",
};

export function riskLevel(score: number): RiskLevel {
  return score >= 0.75 ? "critical" : score >= 0.5 ? "high" : score >= 0.25 ? "medium" : "low";
}

export function stateForRisk(score: number, recovering = false): ZaadState {
  if (recovering) return "RECOVER";
  return score >= 0.6 ? "ALLOCATE" : score >= 0.3 ? "PROTECT" : "LEAN";
}
