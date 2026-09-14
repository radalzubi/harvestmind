/**
 * Adapter: the canonical ZAAD workspace -> NetworkModel.
 *
 * Sources, all released and all reachable in production:
 *   GET  /api/zaad/network/request/from-workspace  the compact contract the optimizer plans:
 *                                                  SKUs, locations, sources, stock, transfers,
 *                                                  customers, services, open POs — plus the build
 *                                                  report with fitted supplier fill and lead, their
 *                                                  sample sizes and provenance
 *   POST /api/zaad/network/plan/from-workspace     the report: actions against the incumbent, per
 *                                                  SKU/location protection rows, service outcomes,
 *                                                  economics, and the P4B commitment block
 *   GET  /api/zaad/network/directory               declared supplier and location master data the
 *                                                  compact contract drops (name, origin, route tag)
 *
 * What this file will not do: infer a number the optimizer did not produce, place a facility whose
 * country is not declared, invent a lane, or attribute plan-level value to a single object. Anything
 * missing lands in `missing` or `notes` in plain words.
 *
 * Note on the superseded path: PR #39 read `/fmcg/state` and `/fmcg/plan?mode=safe`. Those legacy
 * planning modes answer 410 in production (`ZAAD_LEGACY_PLANNERS=0`), so none of it is reused.
 */
import { LANE_CATALOG, PORTS, REGION_AT, type LonLat } from "../geo";
import type {
  NetworkEdge, NetworkModel, NetworkNode, NetworkRecommendation, OpenPO, RiskState, ZaadState,
} from "../model";
import { riskLevel } from "../model";
import type {
  DirectoryResponse, ZaadBuild, ZaadNetworkService, ZaadReport, ZaadRequest,
} from "@/lib/zaad/types";

const ISO3_TO_2: Record<string, string> = {
  JOR: "JO", SAU: "SA", ARE: "AE", EGY: "EG", KWT: "KW", QAT: "QA", BHR: "BH", OMN: "OM", IRQ: "IQ",
  LBN: "LB", SYR: "SY", TUR: "TR", ISR: "IL", PSE: "PS", IND: "IN", CHN: "CN", DEU: "DE", NLD: "NL",
  GBR: "GB", USA: "US", FRA: "FR", ITA: "IT", ESP: "ES", PAK: "PK", SGP: "SG",
};

const risk = (score: number, reasons: string[], evidence: string[]): RiskState =>
  ({ level: riskLevel(Math.max(0, Math.min(1, score))), score: Math.max(0, Math.min(1, score)), reasons, evidence });

/** Below this share of ordered quantity arriving, a supplier is worth mentioning. */
const NOTABLE_SHORTFALL = 0.04;

const approx = (at: LonLat) => ({ lon: at[0], lat: at[1], precision: "approximate" as const });
const exact = (at: LonLat) => ({ lon: at[0], lat: at[1], precision: "exact" as const });

export interface CanonicalInputs {
  request: ZaadRequest;
  build: ZaadBuild;
  report: ZaadReport | null;
  directory: DirectoryResponse | null;
  /** Country of the operator, used only to place their own sites approximately. */
  homeRegion: string | null;
  workspaceName: string;
}

/** Protection rows keyed by location, the optimizer's own per-site risk reading. */
interface ProtectionRow {
  sku: string; location: string; stance: string;
  on_hand_units?: number; protection_units?: number; late_probability?: number;
  shared_domains?: string[]; explanation?: string; data_sufficiency?: string;
  state?: { risk_active?: boolean; activity?: number; periods_to_lean?: number; decaying?: boolean; active_drivers?: Array<{ driver: string }> };
}

function stateFromStance(rows: ProtectionRow[], fallback: ZaadState): ZaadState {
  if (!rows.length) return fallback;
  if (rows.some((r) => r.stance === "no_replenishment")) return "ALLOCATE";
  const protecting = rows.filter((r) => r.stance === "protect");
  if (!protecting.length) return "LEAN";
  return protecting.every((r) => r.state?.decaying) ? "RECOVER" : "PROTECT";
}

export function buildCanonicalModel(input: CanonicalInputs): NetworkModel {
  const { request, build, report, directory, homeRegion, workspaceName } = input;
  const notes: string[] = [];
  const nodes: NetworkNode[] = [];
  const edges: NetworkEdge[] = [];
  const recommendations: NetworkRecommendation[] = [];

  const supplierMaster = new Map((directory?.suppliers ?? []).map((s) => [s.id, s]));
  const fits = build.fits ?? {};
  const protection = ((report?.protection ?? []) as unknown as ProtectionRow[]);
  const serviceRows: ZaadNetworkService[] = report?.network_service ?? [];
  const home = homeRegion ? REGION_AT[homeRegion] ?? null : null;

  // ── locations ──────────────────────────────────────────────────────────────
  const stockByLocation = new Map<string, { units: number; value: number; skus: Set<string> }>();
  const skuValue = new Map(request.skus.map((s) => [s.id, s.unit_value ?? 0]));
  for (const s of request.stock) {
    const hit = stockByLocation.get(s.location) ?? { units: 0, value: 0, skus: new Set<string>() };
    hit.units += s.quantity;
    hit.value += s.quantity * (skuValue.get(s.sku) ?? 0);
    hit.skus.add(s.sku);
    stockByLocation.set(s.location, hit);
  }

  const locationIds = new Set(request.locations.map((l) => l.id));
  const multiSite = request.locations.length > 1;
  for (const loc of request.locations) {
    const id = `loc:${loc.id}`;
    const stock = stockByLocation.get(loc.id);
    const rows = protection.filter((p) => p.location === loc.id);
    const service = serviceRows.filter((s) => s.location === loc.id);
    const gaps = service
      .map((s) => (s.selected_achieved ?? s.expected_achieved) != null ? s.requested - (s.selected_achieved ?? s.expected_achieved)! : null)
      .filter((g): g is number => g != null && g > 0);
    const worstGap = gaps.length ? Math.max(...gaps) : 0;
    const reasons: string[] = [];
    if (worstGap > 0) reasons.push(`Service is projected ${(worstGap * 100).toFixed(1)} points below target here`);
    const short = rows.filter((r) => r.stance === "no_replenishment");
    if (short.length) reasons.push(`${short.length} product${short.length === 1 ? " has" : "s have"} no replenishment route to this site`);
    const protectRows = rows.filter((r) => r.stance === "protect");

    // Score from measured conditions only: a service shortfall the optimizer projects, and a
    // product it cannot resupply to this site. Protection is deliberately NOT scored — the
    // `protect` stance is P0 holding cover where cover is justified, which is the system working,
    // not a warning. Counting it once made a site read "Critical" while its service was projected
    // at 100% against a 95% target, with the panel saying no change was recommended. Three true
    // statements that could not all be true of the same warehouse.
    const score = Math.min(1, worstGap * 8 + (short.length ? 0.5 : 0));
    const missing: string[] = [];
    if (!home) missing.push("This site has no declared country, so it is not placed on the map.");
    if (!stock) missing.push("No stock snapshot has been uploaded for this site.");
    if (!service.length) missing.push("No customer service target is declared for this site.");

    nodes.push({
      id,
      kind: loc.kind === "branch" ? "branch" : "dc",
      name: loc.id === "MAIN" ? `${workspaceName} warehouse` : loc.id,
      subtitle: loc.kind.replaceAll("_", " "),
      region: homeRegion ?? undefined,
      // Locations carry no coordinates in the contract; the operator's own country is the only
      // honest basis, and every site would stack on it, so only a single-site workspace is placed.
      geo: home && !multiSite ? approx(home) : null,
      importance: loc.kind === "central_dc" || loc.kind === "warehouse" ? 1 : 0.7,
      state: stateFromStance(rows, report?.mode as ZaadState ?? "LEAN"),
      risk: risk(score, reasons, [
        ...(service.length ? [`${service.length} service target${service.length === 1 ? "" : "s"} measured`] : []),
        ...(protectRows.length ? [`${protectRows.length} product${protectRows.length === 1 ? " is" : "s are"} being held with extra cover, as planned`] : []),
        ...(rows.length ? [`${rows.length} product protection row${rows.length === 1 ? "" : "s"}`] : []),
      ]),
      metrics: {
        onHandUnits: stock?.units ?? null,
        onHandValue: stock?.value || null,
        serviceTarget: service.length ? Math.max(...service.map((s) => s.requested)) : null,
        serviceProjected: service.length
          ? Math.min(...service.map((s) => s.selected_achieved ?? s.expected_achieved ?? 1))
          : null,
        shortages: rows.filter((r) => r.stance === "no_replenishment").map((r) => ({ sku: r.sku, units: 0, when: "no replenishment route" })),
        protection: {
          localUnits: rows.length ? rows.reduce((a, r) => a + (r.protection_units ?? 0), 0) : null,
          pooledUnits: null,
        },
      },
      skus: [...(stock?.skus ?? new Set<string>())],
      missing: missing.length ? missing : undefined,
    });
  }
  if (multiSite && home) notes.push("Sites are not placed on the map: the workspace declares more than one location and no site carries its own coordinates.");

  // ── suppliers, their routes and the ports they land at ─────────────────────
  const bySupplier = new Map<string, { skus: Set<string>; destinations: Set<string>; unitPrice: number[]; capacity: number | null }>();
  for (const s of request.sources) {
    const hit = bySupplier.get(s.supplier) ?? { skus: new Set<string>(), destinations: new Set<string>(), unitPrice: [], capacity: null };
    hit.skus.add(s.sku);
    hit.destinations.add(s.destination);
    hit.unitPrice.push(s.unit_price);
    bySupplier.set(s.supplier, hit);
  }

  const posBySupplier = new Map<string, OpenPO[]>();
  const sourceToSupplier = new Map(request.sources.map((s) => [s.id, s.supplier]));
  for (const po of request.pipeline) {
    const supplier = sourceToSupplier.get(po.source);
    if (!supplier) continue;
    const list = posBySupplier.get(supplier) ?? [];
    const eta = po.current_eta ? new Date(po.current_eta) : null;
    list.push({
      id: po.id,
      sku: request.sources.find((s) => s.id === po.source)?.sku ?? "",
      units: po.expected_accepted_remaining,
      due: eta ? eta.toISOString().slice(0, 10) : null,
      status: po.stage === "IN_TRANSIT" || po.stage === "SHIPPED" ? "in_transit"
        : eta && eta.getTime() < Date.parse(request.as_of) ? "late" : "open",
    });
    posBySupplier.set(supplier, list);
  }

  const portNodes = new Set<string>();
  let unplacedSuppliers = 0;
  for (const [supplier, agg] of bySupplier) {
    const master = supplierMaster.get(supplier);
    const fit = fits[supplier];
    const iso2 = master?.origin_iso3 ? ISO3_TO_2[master.origin_iso3] ?? null : null;
    const origin = iso2 ? REGION_AT[iso2] ?? null : null;
    const routeTag = master?.route ?? null;
    const lane = routeTag ? LANE_CATALOG[routeTag] : undefined;
    const pos = posBySupplier.get(supplier) ?? [];

    const reasons: string[] = [];
    // The only measured supplier signal in the canonical build is the fitted fill and its sample.
    // Short deliveries are normal at the margin, so nothing is said until the shortfall is one an
    // operator would act on; the score and the sentence share that threshold so a supplier never
    // carries colour without a reason next to it.
    let score = 0;
    if (fit?.fill_mean != null) {
      const shortfall = Math.max(0, 1 - fit.fill_mean);
      const thin = (fit.sample_size ?? 0) < 6;
      if (shortfall > NOTABLE_SHORTFALL) {
        score = Math.min(1, (shortfall - NOTABLE_SHORTFALL) * 4);
        reasons.push(`${(fit.fill_mean * 100).toFixed(1)}% of ordered quantity has been arriving${thin ? ` (only ${fit.sample_size ?? 0} deliveries measured)` : ""}`);
        // A handful of deliveries cannot justify calling a supplier critical.
        if (thin) score = Math.min(score, 0.45);
      }
    }
    const late = pos.filter((p) => p.status === "late");
    if (late.length) { reasons.push(`${late.length} open order${late.length === 1 ? " is" : "s are"} past their expected arrival`); score = Math.max(score, 0.5); }

    const missing: string[] = [];
    if (!origin) { missing.push("No origin country is declared for this supplier, so it is placed by its route if one is known."); if (!lane) unplacedSuppliers += 1; }
    if (fit?.fill_mean == null) missing.push("Delivery reliability needs more delivery history before it can be measured.");
    if (!routeTag) missing.push("No shipping route is declared for this supplier.");

    const geo = origin ? approx(origin) : lane ? approx(lane.path[0]) : null;
    const supplierId = `sup:${supplier}`;
    nodes.push({
      id: supplierId,
      kind: "supplier",
      name: master?.name || supplier,
      subtitle: iso2 ? `Origin ${iso2}` : lane?.name,
      region: iso2 ?? undefined,
      geo,
      importance: Math.min(1, 0.45 + agg.skus.size * 0.08),
      state: score >= 0.6 ? "ALLOCATE" : score >= 0.3 ? "PROTECT" : "LEAN",
      risk: risk(score, reasons, [
        ...(fit?.sample_size ? [`${fit.sample_size} past deliveries`] : []),
        ...(fit?.provenance ? [fit.provenance.replaceAll("_", " ").toLowerCase()] : []),
      ]),
      metrics: {
        fill: fit?.fill_mean != null ? { mean: fit.fill_mean, p10: null, p90: null, n: fit.sample_size ?? null } : undefined,
        leadDays: fit?.lead_days != null ? { mean: fit.lead_days, p10: null, p90: null, n: fit.sample_size ?? null } : undefined,
        openPOs: pos,
        capacityPerWeek: master?.capacity_per_week ?? null,
        sharedFailureDomains: [
          ...(master?.risk_group ? [`${master.risk_group_kind ?? "shared"}: ${master.risk_group}`] : []),
          ...(lane ? lane.chokepoints.map((c) => c.replaceAll("_", " ")) : []),
        ],
      },
      skus: [...agg.skus],
      missing: missing.length ? missing : undefined,
    });

    const destination = [...agg.destinations][0];
    const destinationId = locationIds.has(destination) ? `loc:${destination}` : null;

    if (lane?.port) {
      const portId = `port:${lane.port}`;
      const port = PORTS[lane.port];
      if (!portNodes.has(portId)) {
        portNodes.add(portId);
        nodes.push({
          id: portId, kind: "port", name: port.name, subtitle: "Entry port", region: port.country,
          geo: exact(port.at), importance: 0.85, state: "LEAN",
          risk: risk(0, [], ["no port signal is measured in the workspace"]),
          metrics: {}, skus: [],
          missing: ["Congestion and dwell time are not part of the current upload."],
        });
        if (destinationId) {
          edges.push({
            id: `lane:${lane.port}->${destination}`, kind: "road", from: portId, to: destinationId,
            name: `${port.name} → ${destination}`, path: home ? [port.at, home] : null,
            leadDays: { normal: null, current: null, p90: null },
            capacityPerWeek: null, transportCostPerUnit: null, state: "LEAN", risk: risk(0, [], []),
            skus: [], alternatives: [],
            missing: ["Inland transit time and cost are not declared."],
          });
        }
      }
      edges.push({
        id: `lane:${supplier}->${lane.port}`, kind: lane.kind, from: supplierId, to: portId,
        name: `${master?.name || supplier} → ${port.name}`,
        path: [geo ? [geo.lon, geo.lat] as LonLat : lane.path[0], ...lane.path],
        leadDays: { normal: fit?.lead_days != null ? Math.round(fit.lead_days) : null, current: null, p90: null },
        capacityPerWeek: master?.capacity_per_week ?? null, transportCostPerUnit: null,
        state: score >= 0.6 ? "ALLOCATE" : score >= 0.3 ? "PROTECT" : "LEAN",
        risk: risk(score * 0.8, reasons.length ? [`Carries ${master?.name || supplier}: ${reasons[0].toLowerCase()}`] : [], []),
        skus: [...agg.skus], alternatives: [],
        missing: [
          "This lane has no independent signal: its state follows the supplier that ships on it.",
          `Route "${routeTag}" is the operator's declared tag; the drawn path is the published shipping route for it, not a tracked vessel position.`,
        ],
      });
    } else if (destinationId) {
      edges.push({
        id: `supply:${supplier}->${destination}`, kind: "supply", from: supplierId, to: destinationId,
        name: `${master?.name || supplier} → ${destination}`, path: null,
        leadDays: { normal: fit?.lead_days != null ? Math.round(fit.lead_days) : null, current: null, p90: null },
        capacityPerWeek: master?.capacity_per_week ?? null, transportCostPerUnit: null,
        state: score >= 0.6 ? "ALLOCATE" : score >= 0.3 ? "PROTECT" : "LEAN",
        risk: risk(score * 0.8, reasons.slice(0, 1), []),
        skus: [...agg.skus], alternatives: [],
        missing: ["No shipping route is declared, so this is drawn as a supply relationship rather than a lane."],
      });
    }
  }
  if (unplacedSuppliers) notes.push(`${unplacedSuppliers} supplier${unplacedSuppliers === 1 ? " is" : "s are"} not on the map: neither an origin country nor a route is declared for them.`);

  // ── transfer lanes between sites ───────────────────────────────────────────
  const laneSeen = new Set<string>();
  for (const t of request.transfers) {
    const id = `lane:${t.origin}->${t.destination}`;
    if (laneSeen.has(id)) continue;
    laneSeen.add(id);
    if (!locationIds.has(t.origin) || !locationIds.has(t.destination)) continue;
    const skus = request.transfers.filter((x) => x.origin === t.origin && x.destination === t.destination).map((x) => x.sku);
    edges.push({
      id, kind: "transfer", from: `loc:${t.origin}`, to: `loc:${t.destination}`,
      name: `${t.origin} → ${t.destination}`, path: null,
      leadDays: { normal: t.lead_periods * (request.period_days || 7), current: null, p90: null },
      capacityPerWeek: t.capacity || null, transportCostPerUnit: t.cost_per_unit,
      state: "LEAN", risk: risk(0, [], []), skus, alternatives: [],
      missing: t.approved ? undefined : ["This lane is declared but not approved for use."],
    });
  }

  // ── customers and the service they are owed ────────────────────────────────
  const servicesByCustomer = new Map<string, typeof request.services>();
  for (const s of request.services) {
    const list = servicesByCustomer.get(s.customer) ?? [];
    list.push(s);
    servicesByCustomer.set(s.customer, list);
  }
  for (const c of request.customers) {
    const services = servicesByCustomer.get(c.id) ?? [];
    if (!services.length) continue;
    const measured = serviceRows.filter((r) => services.some((s) => s.id === r.service));
    const gap = measured
      .map((r) => (r.selected_achieved ?? r.expected_achieved) != null ? r.requested - (r.selected_achieved ?? r.expected_achieved)! : 0)
      .reduce((a, b) => Math.max(a, b), 0);
    const id = `cust:${c.id}`;
    nodes.push({
      id, kind: "customer", name: c.id, subtitle: c.channel,
      geo: null, importance: Math.min(1, 0.3 + c.priority / 10),
      state: gap > 0.005 ? "ALLOCATE" : "LEAN",
      risk: risk(Math.min(1, gap * 10), gap > 0.005 ? [`Projected to fall ${(gap * 100).toFixed(1)} points short of the agreed service level`] : [], measured.length ? [`${measured.length} service line${measured.length === 1 ? "" : "s"}`] : []),
      metrics: {
        serviceTarget: Math.max(...services.map((s) => s.target)),
        serviceProjected: measured.length ? Math.min(...measured.map((r) => r.selected_achieved ?? r.expected_achieved ?? 1)) : null,
        tier: c.service_class ?? null,
        demandPerWeek: null,
      },
      skus: [...new Set(services.map((s) => s.sku))],
      missing: ["Customer locations are not part of the current upload, so customers are shown in the network view only."],
    });
    for (const location of new Set(services.map((s) => s.location))) {
      if (!locationIds.has(location)) continue;
      edges.push({
        id: `service:${location}->${c.id}`, kind: "service", from: `loc:${location}`, to: id,
        name: `${location} → ${c.id}`, path: null,
        leadDays: { normal: null, current: null, p90: null },
        capacityPerWeek: null, transportCostPerUnit: null,
        state: gap > 0.005 ? "ALLOCATE" : "LEAN", risk: risk(Math.min(1, gap * 10), [], []),
        skus: [...new Set(services.filter((s) => s.location === location).map((s) => s.sku))],
        alternatives: [],
      });
    }
  }

  // ── what ZAAD recommends, attached to the object it affects ────────────────
  if (report) {
    for (const order of report.commitments?.orders ?? []) {
      if (order.recommended_action === "KEEP") continue;
      const supplier = sourceToSupplier.get(order.source) ?? order.source;
      recommendations.push({
        id: `po:${order.po}`, targetType: "node", targetId: `sup:${supplier}`,
        state: "PROTECT", source: "optimizer",
        action: `${order.recommended_action} ${order.po} — ${order.quantity_affected.toLocaleString()} units`,
        rationale: report.commitments?.reading ?? "",
        noAction: `${order.current_commitment.open_units.toLocaleString()} units arrive as agreed and the remaining invoice falls due on the current date.`,
      });
    }
    const firstReviewPurchases = (report.actions ?? []).filter((a) => a.action === "purchase" && a.period === 0 && a.quantity > 0);
    const bySupplierAction = new Map<string, number>();
    for (const a of firstReviewPurchases) {
      const supplier = sourceToSupplier.get(a.source ?? "") ?? "";
      if (!supplier) continue;
      bySupplierAction.set(supplier, (bySupplierAction.get(supplier) ?? 0) + a.quantity);
    }
    for (const [supplier, quantity] of bySupplierAction) {
      recommendations.push({
        id: `buy:${supplier}`, targetType: "node", targetId: `sup:${supplier}`,
        state: (report.mode as ZaadState) ?? "LEAN", source: "optimizer",
        action: `Order ${quantity.toLocaleString()} units this week`,
        rationale: (report.reasons ?? [])[0] ?? "The plan's reasoning is on the decision.",
        noAction: "The current ordering rule places its own quantity for this week.",
      });
    }
  }

  if (!request.pipeline.length) notes.push("No open purchase orders are declared, so no order change can be evaluated.");
  if (!directory?.suppliers.length) notes.push("No supplier master list is uploaded: suppliers show their id rather than their name, and none can be placed on the map.");
  for (const w of build.warnings ?? []) notes.push(w);

  return {
    id: `workspace:${request.operator_id}`,
    name: workspaceName,
    provenance: "workspace",
    asOf: request.as_of,
    nodes, edges,
    // Shipment positions are not tracked anywhere in the released system; nothing is drawn in motion.
    shipments: [],
    recommendations,
    notes,
  };
}
