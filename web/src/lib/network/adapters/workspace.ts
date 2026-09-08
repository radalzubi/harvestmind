/**
 * Adapter: ZAAD workspace endpoints -> NetworkModel.
 *
 * Reads what the commercial workspace already exposes and says plainly what
 * it does not. Sources, in order of trust:
 *   /fmcg/state       supplier and SKU regime states, lane outlooks, posture,
 *                     and (when the server provides it) the `network` block
 *                     with supplier_of / route_of / opening stock / pipeline
 *   /fmcg/status      row counts per staging table
 *   /me               operator region, used to place the warehouse
 *   /forecasts/supply supplier fill distributions, when calibrated data exists
 * No optimizer logic is reimplemented here; recommendations come only from a
 * plan the server built.
 */
import { apiFetch, getMe, type Me } from "@/lib/api";
import { LANE_CATALOG, PORTS, REGION_AT, type LonLat } from "../geo";
import type { NetworkEdge, NetworkModel, NetworkNode, NetworkRecommendation, OpenPO, RiskState, ZaadState } from "../model";
import { riskLevel } from "../model";

type Outlook = { risk: number; quality: number; reasons: string[]; missing: string[]; stale?: string[]; contrib?: Record<string, number> };
type EntityState = { dominant: string; p_disruptive: number; stress: number; probabilities: Record<string, number>; reasons: string[]; change_points?: unknown[] };
export interface StateResponse {
  as_of?: string;
  mode?: string;
  portfolio?: { probabilities: Record<string, number>; dominant: string; stress: number; reasons: string[]; data_quality: number };
  posture?: { commit_window: number; cvar_lambda: number; autonomy: number; scenario_width: number; candidates: string[] };
  sku?: Record<string, EntityState>;
  supplier?: Record<string, EntityState>;
  outlooks?: Record<string, Outlook>;
  replan_triggers?: string[];
  plain?: { headline: string; lanes: Array<{ lane: string; sentence: string; reasons: string[]; missing: string[] }> };
  network?: {
    products?: string[];
    supplier_of?: Record<string, string>;
    route_of?: Record<string, string>;
    lead_of?: Record<string, number>;
    opening?: Record<string, number>;
    pipeline?: Record<string, number>;
    unit_cost?: Record<string, number>;
    suppliers?: Record<string, { name?: string | null; route?: string | null; origin_iso3?: string | null; capacity_per_week?: number | null }>;
  };
}
export interface StatusResponse { tables: Record<string, number>; ready_to_plan?: boolean; minimum_history_weeks?: number }
export interface SupplyRisk { suppliers: Array<{ supplier_id: string; supplier_name: string; n_deliveries: number; posterior_mean: number; downside: number; spread: number; risk_level: string }> }
export interface PlanOrder { sku: string; supplier_id: string; week_offset: number; order_units: number; lots: number; lot_unit: string; explanation: string[]; purchase_value: { amount: string; currency: string } }
export interface PlanResponse { run_id: string; mode_run: string; solver_status: string; warnings: string[]; orders: PlanOrder[] }

const REGIME_STATE: Record<string, ZaadState> = {
  SUPPLIER_FAILURE: "ALLOCATE", PORT_DISRUPTION: "ALLOCATE", ROUTE_DISRUPTION: "ALLOCATE", CAPACITY_CONSTRAINED: "ALLOCATE",
  SUPPLIER_DEGRADED: "PROTECT", DEMAND_VOLATILE: "PROTECT", DEMAND_SHIFT: "PROTECT", WATCH: "PROTECT",
  RECOVERY: "RECOVER", NORMAL: "LEAN", CALM: "LEAN",
};
const ISO3_TO_2: Record<string, string> = { JOR: "JO", SAU: "SA", ARE: "AE", EGY: "EG", KWT: "KW", QAT: "QA", BHR: "BH", OMN: "OM", IRQ: "IQ", LBN: "LB", SYR: "SY", TUR: "TR", ISR: "IL", PSE: "PS", IND: "IN", CHN: "CN", DEU: "DE", NLD: "NL", GBR: "GB", USA: "US", FRA: "FR", ITA: "IT", ESP: "ES", PAK: "PK" };

const risk = (score: number, reasons: string[], evidence: string[]): RiskState => ({ level: riskLevel(score), score, reasons, evidence });
const approx = (at: LonLat) => ({ lon: at[0], lat: at[1], precision: "approximate" as const });
const stateOf = (e: EntityState | undefined): ZaadState => (e ? REGIME_STATE[e.dominant] ?? (e.p_disruptive >= 0.5 ? "ALLOCATE" : e.p_disruptive >= 0.25 ? "PROTECT" : "LEAN") : "LEAN");

export interface WorkspaceInputs {
  state: StateResponse;
  status: StatusResponse | null;
  me: Me | null;
  supply: SupplyRisk | null;
}

export async function loadWorkspaceNetwork(): Promise<NetworkModel> {
  const [state, status, me, supply] = await Promise.all([
    apiFetch<StateResponse>("/fmcg/state"),
    apiFetch<StatusResponse>("/fmcg/status").catch(() => null),
    getMe().catch(() => null),
    apiFetch<SupplyRisk>("/forecasts/supply").catch(() => null),
  ]);
  return buildWorkspaceModel({ state, status, me, supply });
}

/** Pure: raw payloads in, NetworkModel out. Tolerates older servers and partial uploads. */
export function buildWorkspaceModel({ state, status, me, supply }: WorkspaceInputs): NetworkModel {
  const net = state.network;
  const portfolio = state.portfolio ?? { probabilities: {}, dominant: "NORMAL", stress: 0, reasons: [], data_quality: 0 };
  const outlooks = state.outlooks ?? {};
  const notes: string[] = [];
  if (!net) notes.push("Supplier-to-lane, SKU and stock links are not available from this server version.");
  if (status?.tables) {
    const rows = Object.entries(status.tables).filter(([, n]) => n > 0).map(([t, n]) => `${t.replace("stg_fmcg_", "")} ${n.toLocaleString()} rows`);
    notes.push(rows.length ? `Loaded: ${rows.join(", ")}` : "No commercial tables loaded yet.");
    if (!status.tables.stg_fmcg_inventory) notes.push("Stock on hand is not available until an inventory snapshot is uploaded.");
    if (!status.tables.stg_fmcg_purchase_orders) notes.push("Open orders and inbound stock are not available until purchase orders are uploaded.");
  }
  const region = me?.region?.toUpperCase() ?? "";
  const home = REGION_AT[region] ?? null;
  const fillById = new Map((supply?.suppliers ?? []).map((s) => [s.supplier_id, s]));

  const nodes: NetworkNode[] = [];
  const edges: NetworkEdge[] = [];
  const supplierOf = net?.supplier_of ?? {}, opening = net?.opening ?? {}, pipelineOf = net?.pipeline ?? {}, unitCost = net?.unit_cost ?? {};
  const leadOf = net?.lead_of ?? {}, masters = net?.suppliers ?? {}, routeOf = net?.route_of ?? {};
  const skusOf = (sid: string) => Object.entries(supplierOf).filter(([, s]) => s === sid).map(([j]) => j);
  const onHand = net?.opening ? Object.values(opening).reduce((a, b) => a + b, 0) : null;
  const inbound = net?.pipeline ? Object.values(pipelineOf).reduce((a, b) => a + b, 0) : null;
  const onHandValue = net?.opening ? Object.entries(opening).reduce((a, [j, q]) => a + q * (unitCost[j] ?? 0), 0) : null;

  // the warehouse: one node for the whole commercial workspace
  const dcId = "dc_workspace";
  const skuStates = Object.entries(state.sku ?? {});
  const stressedSkus = skuStates.filter(([, s]) => s.p_disruptive >= 0.25).map(([j]) => j);
  nodes.push({
    id: dcId, kind: "dc", name: me?.display_name || me?.name ? `${me?.display_name ?? me?.name} warehouse` : "Your warehouse",
    subtitle: region ? `Region ${region}` : "Region not set", region, geo: home ? approx(home) : null, importance: 1,
    state: state.mode === "PROTECTION" ? "PROTECT" : state.mode === "BALANCED" ? "PROTECT" : "LEAN",
    risk: risk(portfolio.stress ?? 0, (portfolio.reasons ?? []).slice(0, 3), [`data quality ${(portfolio.data_quality ?? 0).toFixed(2)}`]),
    metrics: { onHandUnits: onHand, onHandValue, inboundUnits: inbound, serviceTarget: null, serviceProjected: null,
      shortages: stressedSkus.map((j) => ({ sku: j, units: 0, when: "regime at risk" })), excess: [], transferOpportunities: [], protection: { localUnits: null, pooledUnits: null } },
    skus: net?.products ?? skuStates.map(([j]) => j),
    missing: [
      ...(home ? [] : ["Location has not been set for this warehouse, so it is not shown on the map"]),
      "Service figures appear once a purchase plan has been built",
      ...(net ? [] : ["Stock and inbound units are not available from this server version"]),
      "Branches and customer groups are not part of the current upload",
    ],
  });

  // suppliers, from the state read; lane and SKU links from the network block
  const portNodes = new Set<string>();
  for (const [sid, es] of Object.entries(state.supplier ?? {})) {
    const master = masters[sid];
    const route = master?.route ?? routeOf[sid] ?? null;
    const lane = route ? LANE_CATALOG[route] : undefined;
    const originIso = master?.origin_iso3 ? ISO3_TO_2[master.origin_iso3] ?? null : null;
    const origin = originIso ? REGION_AT[originIso] ?? null : null;
    const fill = fillById.get(sid);
    const skus = skusOf(sid);
    const missing: string[] = [];
    if (!origin) missing.push("Origin country has not been added for this supplier; it is placed by its route");
    if (!fill) missing.push("Delivery reliability needs more delivery history before it can be shown");
    if (!route) missing.push("Route information has not been added for this supplier");
    if (!skus.length) missing.push("Which SKUs this supplier provides is not available");
    const geo = origin ? approx(origin) : lane ? approx(lane.path[0]) : null;
    nodes.push({
      id: `sup_${sid}`, kind: "supplier", name: master?.name || fill?.supplier_name || sid, subtitle: originIso ? `Origin ${originIso}` : route ? lane?.name : undefined,
      region: originIso ?? undefined, geo, importance: Math.min(1, 0.5 + skus.length * 0.1), state: stateOf(es),
      risk: risk(Math.max(es.p_disruptive, es.stress * 0.8), es.reasons.slice(0, 3), [`${Object.keys(es.probabilities).length} regimes scored`, ...(fill ? [`${fill.n_deliveries} deliveries`] : [])]),
      metrics: {
        fill: fill ? { mean: fill.posterior_mean, p10: fill.downside, p90: null, n: fill.n_deliveries } : undefined,
        leadDays: leadOf[sid] != null ? { mean: leadOf[sid] * 7, p10: null, p90: null, n: null } : undefined,
        openPOs: [] as OpenPO[], sharedFailureDomains: lane ? lane.chokepoints.map((c) => c.replace(/_/g, " ")).concat(lane.port ? [PORTS[lane.port].name] : []) : [],
        capacityPerWeek: master?.capacity_per_week ?? null,
      },
      skus, alternatives: [], missing,
    });
    // supplier -> port lane, when the route is known; otherwise a supply relationship straight to the warehouse
    if (lane && lane.port) {
      const pid = `port_${lane.port}`;
      if (!portNodes.has(pid)) {
        portNodes.add(pid);
        const o = outlooks[route!];
        nodes.push({ id: pid, kind: "port", name: PORTS[lane.port].name, subtitle: "Entry port", region: PORTS[lane.port].country, geo: { lon: PORTS[lane.port].at[0], lat: PORTS[lane.port].at[1], precision: "exact" },
          importance: 0.9, state: o ? (o.risk >= 0.55 ? "ALLOCATE" : o.risk >= 0.3 ? "PROTECT" : "LEAN") : "LEAN",
          risk: o ? risk(o.risk, o.reasons.slice(0, 3), Object.keys(o.contrib ?? {})) : risk(0, [], []), metrics: { dwellDays: { mean: null, p10: null, p90: null, n: null }, congestion: null }, skus: [],
          missing: o?.missing?.length ? ["Some shipping signals for this port are not available yet"] : undefined });
        edges.push({ id: `lane_${lane.port}_dc`, kind: "road", from: pid, to: dcId, name: `${PORTS[lane.port].name} → warehouse`, path: home ? [PORTS[lane.port].at, home] : null,
          leadDays: { normal: null, current: null, p90: null }, capacityPerWeek: null, transportCostPerUnit: null, state: "LEAN", risk: risk(0, [], []), skus: [], alternatives: [],
          missing: ["Inland transit time and cost have not been added"] });
      }
      const o = outlooks[route!];
      edges.push({
        id: `lane_${sid}_${route}`, kind: lane.kind, from: `sup_${sid}`, to: pid, name: `${master?.name || sid} → ${PORTS[lane.port].name} (${lane.name})`,
        path: [geo ? [geo.lon, geo.lat] : lane.path[0], ...lane.path],
        leadDays: { normal: leadOf[sid] != null ? leadOf[sid] * 7 : null, current: null, p90: null },
        capacityPerWeek: master?.capacity_per_week ?? null, transportCostPerUnit: null,
        state: o ? (o.risk >= 0.55 ? "ALLOCATE" : o.risk >= 0.3 ? "PROTECT" : "LEAN") : "LEAN",
        risk: o ? risk(o.risk, o.reasons.slice(0, 4), Object.keys(o.contrib ?? {})) : risk(0, ["No lane outlook for this route"], []),
        skus, alternatives: [], disruptionEvidence: o?.reasons ?? [],
        missing: [...(o?.missing?.length ? ["Some shipping signals for this lane are not available yet"] : []), "Current transit time appears once receipts are recorded against open orders", "Transport cost has not been added"],
      });
    } else {
      edges.push({ id: `supply_${sid}`, kind: "supply", from: `sup_${sid}`, to: dcId, name: `${master?.name || sid} → warehouse`, path: null,
        leadDays: { normal: leadOf[sid] != null ? leadOf[sid] * 7 : null, current: null, p90: null },
        capacityPerWeek: master?.capacity_per_week ?? null, transportCostPerUnit: null, state: stateOf(es), risk: risk(es.p_disruptive, es.reasons.slice(0, 3), []),
        skus, alternatives: [], missing: ["Route information has not been added for this supplier, so this is shown as a relationship rather than a lane"] });
    }
  }
  // lanes with an outlook but no tagged supplier still deserve a place
  for (const [route, o] of Object.entries(outlooks)) {
    const lane = LANE_CATALOG[route];
    if (!lane || !lane.port || portNodes.has(`port_${lane.port}`)) continue;
    const pid = `port_${lane.port}`;
    portNodes.add(pid);
    nodes.push({ id: pid, kind: "port", name: PORTS[lane.port].name, subtitle: lane.name, region: PORTS[lane.port].country, geo: { lon: PORTS[lane.port].at[0], lat: PORTS[lane.port].at[1], precision: "exact" },
      importance: 0.8, state: o.risk >= 0.55 ? "ALLOCATE" : o.risk >= 0.3 ? "PROTECT" : "LEAN", risk: risk(o.risk, o.reasons.slice(0, 3), Object.keys(o.contrib ?? {})),
      metrics: {}, skus: [], missing: ["No supplier is assigned to this route yet"] });
    edges.push({ id: `lane_${route}`, kind: lane.kind, from: pid, to: dcId, name: `${lane.name} → warehouse`, path: home ? [...lane.path, home] : lane.path,
      leadDays: { normal: null, current: null, p90: null }, capacityPerWeek: null, transportCostPerUnit: null,
      state: o.risk >= 0.55 ? "ALLOCATE" : o.risk >= 0.3 ? "PROTECT" : "LEAN", risk: risk(o.risk, o.reasons.slice(0, 4), Object.keys(o.contrib ?? {})), skus: [], alternatives: [], disruptionEvidence: o.reasons });
  }

  return {
    id: `workspace_${me?.operator_id ?? "anon"}`,
    name: me?.display_name ?? me?.name ?? "Your workspace",
    provenance: "workspace",
    asOf: state.as_of ?? new Date().toISOString(),
    nodes, edges, shipments: [], recommendations: [],
    notes: [...notes, "Shipment positions are not part of the current upload.", (state.plain?.headline ?? "").trim()].filter(Boolean),
  };
}

/** Attach a server-built purchase plan to supplier nodes as optimizer recommendations. */
export async function loadPlanRecommendations(model: NetworkModel): Promise<NetworkRecommendation[]> {
  const q = new URLSearchParams({ mode: "safe", horizon_weeks: "12", service_level: "0.97" });
  const plan = await apiFetch<PlanResponse>(`/fmcg/plan?${q}`, { method: "POST" });
  const bySupplier = new Map<string, PlanOrder[]>();
  for (const o of plan.orders) {
    if (!bySupplier.has(o.supplier_id)) bySupplier.set(o.supplier_id, []);
    bySupplier.get(o.supplier_id)!.push(o);
  }
  const recs: NetworkRecommendation[] = [];
  for (const [sid, orders] of bySupplier) {
    const id = `sup_${sid}`;
    if (!model.nodes.some((n) => n.id === id)) continue;
    const units = orders.reduce((s, o) => s + o.order_units, 0);
    const soonest = Math.min(...orders.map((o) => o.week_offset));
    recs.push({ id: `plan_${plan.run_id}_${sid}`, targetType: "node", targetId: id, state: model.nodes.find((n) => n.id === id)!.state, source: "optimizer",
      action: `Order ${units.toLocaleString()} units across ${orders.length} line${orders.length === 1 ? "" : "s"}, first in week ${soonest} (plan ${plan.mode_run}, solver ${plan.solver_status}).`,
      rationale: orders[0]?.explanation?.[0] ?? "See the purchase plan for the line-level reasoning.",
      noAction: "Not modelled by the plan endpoint; the plan states orders, not the counterfactual." });
  }
  return recs;
}
