"use client";

/**
 * Interactive pieces of /how-it-works. One shared simulation state (mode + active disruptions)
 * drives the network map, the SKU table, the stock bars and the recovery strip, so the page reads
 * as one operating model rather than a set of illustrations. Every figure is the illustrative demo
 * in lib/hiw.ts; labels come from the locale so Arabic reads as Arabic.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode, type RefObject } from "react";
import { AnimatePresence, motion } from "motion/react";
import { useLocale } from "@/lib/i18n";
import { useReduce } from "@/lib/motion";
import { ACTIONS, CANDIDATES, COMPARE, EDGES, NODES, NODE_FACTS, NODE_FACTS_AR, SKUS, series, type Disruption, type Mode, type Scenario } from "@/lib/hiw";

type Sim = { mode: Mode; disruptions: Disruption[]; toggle: (d: Disruption) => void; reset: () => void };
const SimContext = createContext<Sim>({ mode: "LEAN", disruptions: [], toggle: () => {}, reset: () => {} });
export const useSim = () => useContext(SimContext);

/** Mode follows the disruptions: any port closure → ALLOCATE, any other disruption → PROTECT, clearing → RECOVER, reset → LEAN. */
export function SimProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>("LEAN");
  const [disruptions, setDisruptions] = useState<Disruption[]>([]);
  const toggle = useCallback((d: Disruption) => setDisruptions((list) => {
    const next = list.includes(d) ? list.filter((x) => x !== d) : [...list, d];
    setMode(next.length ? (next.includes("port_closure") ? "ALLOCATE" : "PROTECT") : "RECOVER");
    return next;
  }), []);
  const reset = useCallback(() => { setDisruptions([]); setMode("LEAN"); }, []);
  const value = useMemo(() => ({ mode, disruptions, toggle, reset }), [mode, disruptions, toggle, reset]);
  return <SimContext.Provider value={value}>{children}</SimContext.Provider>;
}

const EASE = [0.22, 1, 0.36, 1] as const;

/** Runs a callback on animation frames only while the element is on screen and motion is allowed. */
function useOnscreenFrame(ref: RefObject<Element | null>, cb: (t: number) => void) {
  const reduce = useReduce();
  useEffect(() => {
    if (reduce) return;
    const el = ref.current;
    if (!el) return;
    let visible = false, raf = 0;
    const start = performance.now();
    const loop = (now: number) => { if (visible) cb((now - start) / 1000); raf = requestAnimationFrame(loop); };
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; }, { threshold: .1 });
    io.observe(el);
    raf = requestAnimationFrame(loop);
    return () => { cancelAnimationFrame(raf); io.disconnect(); };
  }, [ref, cb, reduce]);
}

export function ModeTag({ mode, big }: { mode: Mode; big?: boolean }) {
  const { t } = useLocale();
  const label = t.hiw.modes.cards[["LEAN", "PROTECT", "ALLOCATE", "RECOVER"].indexOf(mode)][0];
  return <span className={"hiw-mode-tag " + mode.toLowerCase() + (big ? " big" : "")}><i />{label}</span>;
}

/* ------------------------------------------------------------------ network */

export function NetworkMap() {
  const { t, locale } = useLocale();
  const c = t.hiw.network;
  const { mode, disruptions } = useSim();
  const [hover, setHover] = useState<string>("dc");
  const svgRef = useRef<SVGSVGElement>(null);
  const packetRefs = useRef<Record<string, SVGCircleElement | null>>({});
  const pos = useMemo(() => Object.fromEntries(NODES.map((n) => [n.id, n])) as Record<string, (typeof NODES)[number]>, []);
  const closure = disruptions.includes("port_closure"), late = disruptions.includes("supplier_delay");
  const stressed = useCallback((edge: (typeof EDGES)[number]) => (closure && edge.route) || (late && edge.id === "a_port"), [closure, late]);
  const frame = useCallback((time: number) => {
    EDGES.forEach((e, i) => {
      const el = packetRefs.current[e.id];
      if (!el) return;
      const a = pos[e.from], b = pos[e.to];
      const f = (time * (stressed(e) ? .16 : .42) + i * .17) % 1;
      el.setAttribute("cx", String(a.x + (b.x - a.x) * f));
      el.setAttribute("cy", String(a.y + (b.y - a.y) * f));
      el.setAttribute("opacity", closure && e.route ? "0.12" : "0.9");
    });
  }, [pos, stressed, closure]);
  useOnscreenFrame(svgRef, frame);
  const facts = (locale === "ar" ? NODE_FACTS_AR : NODE_FACTS)[hover][mode];
  const node = pos[hover];
  const exposedIds = mode === "LEAN" ? [] : ["sup_a", "port", "br_n", ...(mode === "ALLOCATE" ? ["dc"] : [])];
  return (
    <div className="hiw-network">
      <svg ref={svgRef} viewBox="0 0 900 320" className="hiw-network-svg" role="img" aria-label={c.aria}>
        {EDGES.map((e) => {
          const a = pos[e.from], b = pos[e.to];
          return <line key={e.id} x1={a.x} y1={a.y} x2={b.x} y2={b.y} className={"hiw-edge" + (stressed(e) ? " stressed" : "")} />;
        })}
        {EDGES.map((e) => <circle key={"p" + e.id} r="4" className="hiw-packet" ref={(el) => { packetRefs.current[e.id] = el; }} cx={pos[e.from].x} cy={pos[e.from].y} />)}
        {NODES.map((n) => (
          <g key={n.id} className={"hiw-node" + (hover === n.id ? " active" : "") + (exposedIds.includes(n.id) ? " exposed" : "")}
             onMouseEnter={() => setHover(n.id)} onFocus={() => setHover(n.id)} onClick={() => setHover(n.id)}
             onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setHover(n.id); } }}
             tabIndex={0} role="button" aria-pressed={hover === n.id} aria-label={c.nodes[n.id]}>
            <circle cx={n.x} cy={n.y} r={n.kind === "dc" ? 22 : 16} />
            <text x={n.x} y={n.y + (n.kind === "dc" ? 42 : 34)} textAnchor="middle">{c.nodes[n.id]}</text>
          </g>
        ))}
      </svg>
      <div className="hiw-inspect" aria-live="polite">
        <div className="hiw-inspect-head"><span className="hiw-chip">{c.inspect}</span><strong>{c.nodes[node.id]}</strong><ModeTag mode={mode} /></div>
        <dl>
          <div><dt>{c.inventory}</dt><dd>{facts.inventory}</dd></div>
          <div><dt>{c.pipeline}</dt><dd>{facts.pipeline}</dd></div>
          <div><dt>{c.lead}</dt><dd>{facts.lead}</dd></div>
          <div><dt>{c.exposure}</dt><dd>{facts.exposure}</dd></div>
        </dl>
        <p className="hiw-illustrative">{t.hiw.illustrative}</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ uncertainty lab */

function Chart({ values, band, height = 120, max, unit, label }: { values: number[]; band?: number; height?: number; max: number; unit?: string; label: string }) {
  const w = 520, pad = 8;
  const x = (i: number) => pad + (i / (values.length - 1)) * (w - 2 * pad);
  const y = (v: number) => height - pad - (v / max) * (height - 2 * pad);
  const line = values.map((v, i) => `${x(i)},${y(v)}`).join(" ");
  const upper = values.map((v, i) => `${x(i)},${y(Math.min(max, v + (band ?? 0)))}`).join(" ");
  const lower = values.map((v, i) => `${x(i)},${y(Math.max(0, v - (band ?? 0)))}`).reverse().join(" ");
  return (
    <figure className="hiw-chart">
      <figcaption>{label}{unit ? <span> · {unit}</span> : null}</figcaption>
      <svg viewBox={`0 0 ${w} ${height}`} role="img" aria-label={label}>
        {band ? <polygon points={`${upper} ${lower}`} className="hiw-band" /> : null}
        <polyline points={line} className="hiw-line" />
      </svg>
    </figure>
  );
}

export function UncertaintyLab() {
  const { t } = useLocale();
  const c = t.hiw.uncertainty;
  const [scenario, setScenario] = useState<Scenario>("stable");
  const s = useMemo(() => series(scenario), [scenario]);
  const options: { id: Scenario; label: string; read: string }[] = [
    { id: "stable", label: c.stable, read: c.riskLow }, { id: "volatile", label: c.volatile, read: c.riskDemand },
    { id: "supplier_delay", label: c.delay, read: c.riskSupply }, { id: "demand_surge", label: c.surge, read: c.riskSurge },
  ];
  const active = options.find((o) => o.id === scenario) ?? options[0];
  return (
    <div className="hiw-lab">
      <div className="hiw-toggles" role="group" aria-label={c.aria}>
        {options.map((o) => <button key={o.id} type="button" aria-pressed={scenario === o.id} className={"hiw-toggle" + (scenario === o.id ? " on" : "")} onClick={() => setScenario(o.id)}>{o.label}</button>)}
      </div>
      <div className="hiw-charts">
        <Chart values={s.demand} band={s.bandDemand} max={200} label={c.demand} unit={c.cases} />
        <Chart values={s.lead} band={s.bandLead} max={45} label={c.lead} unit={c.days} />
        <Chart values={s.fill.map((v) => v * 100)} max={100} label={c.fill} unit="%" />
      </div>
      <div className="hiw-readout" aria-live="polite">
        <span className="hiw-chip">{c.riskLabel}</span>
        <AnimatePresence mode="wait"><motion.strong key={scenario} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: .3, ease: EASE }} className={scenario === "stable" ? "lean" : "protect"}>{active.read}</motion.strong></AnimatePresence>
        <p>{c.note}</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ decision lab */

export function DecisionLab() {
  const { t } = useLocale();
  const c = t.hiw.lab;
  const [active, setActive] = useState(4);
  const cand = CANDIDATES[active];
  const dims: { key: "service" | "inventory" | "capital" | "shortage" | "risk" | "cost"; label: string; good: boolean }[] = [
    { key: "service", label: c.service, good: true }, { key: "inventory", label: c.inventory, good: false }, { key: "capital", label: c.capital, good: false },
    { key: "shortage", label: c.shortage, good: false }, { key: "risk", label: c.risk, good: false }, { key: "cost", label: c.cost, good: false },
  ];
  return (
    <div className="hiw-decision">
      <div className="hiw-branches">
        <div className="hiw-state"><span className="hiw-chip">{c.state}</span><strong>{c.stateName}</strong></div>
        <ul aria-label={c.aria}>
          {CANDIDATES.map((x, i) => (
            <li key={x.id}>
              <button type="button" className={"hiw-branch" + (active === i ? " on" : "") + (i === 0 ? " base" : "")} onMouseEnter={() => setActive(i)} onFocus={() => setActive(i)} onClick={() => setActive(i)} aria-pressed={active === i}>
                <i /> {c.candidates[i]}
              </button>
            </li>
          ))}
        </ul>
      </div>
      <div className="hiw-outcomes" aria-live="polite">
        <div className="hiw-outcomes-head"><span className="hiw-chip">{c.outcome}</span><strong>{c.candidates[active]}</strong></div>
        {dims.map((d) => {
          const v = cand[d.key];
          return (
            <div key={d.key} className="hiw-meter">
              <span>{d.label}</span>
              <div className="hiw-meter-track"><motion.div className={"hiw-meter-fill" + (d.good ? " good" : "")} initial={false} animate={{ width: `${Math.round(v * 100)}%` }} transition={{ duration: .5, ease: EASE }} /></div>
              <em>{d.key === "service" ? `${Math.round(v * 100)}%` : Math.round(v * 100)}</em>
            </div>
          );
        })}
        <p className="hiw-illustrative">{c.note}</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ incumbent first */

export function IncumbentFirst() {
  const { t } = useLocale();
  const c = t.hiw.incumbent;
  const [which, setWhich] = useState<"keep" | "change">("keep");
  const row = c[which];
  return (
    <div className="hiw-incumbent">
      <div className="hiw-toggles">
        <button type="button" className={"hiw-toggle" + (which === "keep" ? " on" : "")} onClick={() => setWhich("keep")} aria-pressed={which === "keep"}>{c.scenarioA}</button>
        <button type="button" className={"hiw-toggle" + (which === "change" ? " on" : "")} onClick={() => setWhich("change")} aria-pressed={which === "change"}>{c.scenarioB}</button>
      </div>
      <div className="hiw-compare-cols">
        <div className="hiw-plan"><span className="hiw-chip">{c.current}</span><ul>{row.current.map((x) => <li key={x}>{x}</li>)}</ul></div>
        <div className="hiw-plan zaad"><span className="hiw-chip">{c.candidate}</span><ul>{row.candidate.map((x) => <li key={x}>{x}</li>)}</ul></div>
      </div>
      <AnimatePresence mode="wait">
        <motion.div key={which} className={"hiw-verdict " + which} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: .35, ease: EASE }} aria-live="polite">
          <strong>{row.verdict}</strong><p>{row.why}</p>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

/* ------------------------------------------------------------------ modes: lean / protect / allocate / recover */

export function DisruptionControls() {
  const { t } = useLocale();
  const c = t.hiw.modes;
  const { disruptions, toggle, reset, mode } = useSim();
  const controls: { id: Disruption; label: string }[] = [
    { id: "supplier_delay", label: c.supplierDelay }, { id: "port_closure", label: c.portClosure }, { id: "demand_surge", label: c.demandSurge }, { id: "fill_drop", label: c.fillDrop },
  ];
  return (
    <div className="hiw-controls" role="group" aria-label={c.controlsAria}>
      {controls.map((x) => (
        <button key={x.id} type="button" className={"hiw-switch" + (disruptions.includes(x.id) ? " on" : "")} aria-pressed={disruptions.includes(x.id)} onClick={() => toggle(x.id)}>
          <i /> {x.label}
        </button>
      ))}
      <button type="button" className="hiw-switch reset" onClick={reset} disabled={!disruptions.length && mode === "LEAN"}>{c.normalise}</button>
      <ModeTag mode={mode} big />
    </div>
  );
}

export function ModeCards() {
  const { t } = useLocale();
  const { mode } = useSim();
  const order: Mode[] = ["LEAN", "PROTECT", "ALLOCATE", "RECOVER"];
  return (
    <div className="hiw-mode-cards">
      {t.hiw.modes.cards.map(([title, body], i) => (
        <div key={title} className={"hiw-mode-card " + order[i].toLowerCase() + (mode === order[i] ? " on" : "")} aria-current={mode === order[i] ? "true" : undefined}>
          <span className={"hiw-mode-tag " + order[i].toLowerCase()}><i />{title}</span>
          <p>{body}</p>
        </div>
      ))}
    </div>
  );
}

export function SkuTable() {
  const { t } = useLocale();
  const c = t.hiw.modes;
  const { disruptions, mode } = useSim();
  return (
    <div className="hiw-table-wrap">
      <table className="hiw-skus">
        <thead><tr><th>{c.sku}</th><th>{c.profile}</th><th>{c.exposure}</th><th>{c.decision}</th></tr></thead>
        <tbody>
          {SKUS.map((s, i) => {
            const hits = s.exposed.filter((d) => disruptions.includes(d));
            const exposed = hits.length > 0;
            const label = mode === "RECOVER" ? (s.exposed.length ? c.unwinding : c.noChange) : exposed ? c.protection[hits[0]] : c.noChange;
            const changed = exposed || (mode === "RECOVER" && s.exposed.length > 0);
            return (
              <tr key={s.id} className={changed ? "exposed" : ""}>
                <td><strong>{s.id}</strong></td><td>{c.skuDesc[i]}</td>
                <td>{exposed ? <span className="hiw-mode-tag protect"><i />{c.exposed}</span> : <span className="hiw-mode-tag lean"><i />{c.notExposed}</span>}</td>
                <td><AnimatePresence mode="wait" initial={false}><motion.span key={label} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: .25 }} className={changed ? "hiw-decision-on" : ""}>{label}</motion.span></AnimatePresence></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function InventoryBars() {
  const { t } = useLocale();
  const c = t.hiw.modes;
  const { mode } = useSim();
  const levels: Record<Mode, number[]> = { LEAN: [.42, .38, .30, .36, .28], PROTECT: [.70, .82, .30, .52, .28], ALLOCATE: [.22, .18, .30, .26, .28], RECOVER: [.52, .55, .30, .40, .28] };
  const lean = levels.LEAN;
  return (
    <div className="hiw-bars" role="img" aria-label={c.barsAria}>
      <div className="hiw-bars-grid">
        {SKUS.map((s, i) => (
          <div key={s.id} className="hiw-bar">
            <div className="hiw-bar-track">
              <div className="hiw-bar-lean" style={{ bottom: `${lean[i] * 100}%` }} />
              <motion.div className={"hiw-bar-fill " + mode.toLowerCase()} initial={false} animate={{ height: `${levels[mode][i] * 100}%` }} transition={{ duration: .8, ease: EASE }} />
            </div>
            <span>{s.id}</span>
          </div>
        ))}
      </div>
      <div className="hiw-bars-legend"><i className="lean" /> {c.leanLevel} <i className="fill" /> {c.plannedLevel}</div>
    </div>
  );
}

export function AllocatePanel() {
  const { t } = useLocale();
  const c = t.hiw.allocate;
  const [priority, setPriority] = useState<[number, number, number]>([3, 2, 1]);
  const supply = 300;
  const demand = [180, 160, 120];
  const names = [c.supermarket, c.wholesale, c.spot];
  const targets = ["99%", "95%", "90%"];
  // Priority-ordered fill: highest priority first; equal priorities share what is left in proportion to demand.
  const alloc = [0, 0, 0];
  let left = supply;
  for (const p of [3, 2, 1]) {
    const group = [0, 1, 2].filter((i) => priority[i] === p);
    const need = group.reduce((a, i) => a + demand[i], 0);
    if (!group.length) continue;
    const give = Math.min(need, left);
    group.forEach((i) => { alloc[i] = Math.round(give * demand[i] / need); });
    left -= give;
  }
  return (
    <div className="hiw-allocate">
      <div className="hiw-allocate-head"><span className="hiw-chip">{c.supplyLabel}</span><strong>{supply} {c.cases}</strong><span className="hiw-chip warn">{c.demandLabel} {demand.reduce((a, b) => a + b)} {c.cases}</span></div>
      {names.map((n, i) => (
        <div key={n} className="hiw-alloc-row">
          <div className="hiw-alloc-name"><strong>{n}</strong><span>{c.target} {targets[i]}</span></div>
          <label className="hiw-alloc-priority">{c.priority}
            <input type="range" min={1} max={3} step={1} value={priority[i]} onChange={(e) => { const p = [...priority] as [number, number, number]; p[i] = Number(e.target.value); setPriority(p); }} aria-label={`${c.priority}: ${n}`} />
            <em>{priority[i]}</em>
          </label>
          <div className="hiw-alloc-bar"><motion.div initial={false} animate={{ width: `${(alloc[i] / demand[i]) * 100}%` }} transition={{ duration: .5, ease: EASE }} className={alloc[i] < demand[i] ? "short" : ""} /><span>{alloc[i]} / {demand[i]}</span></div>
        </div>
      ))}
      <p className="hiw-note">{c.note}</p>
    </div>
  );
}

export function RecoveryStrip() {
  const { t } = useLocale();
  const c = t.hiw.recover;
  const { mode } = useSim();
  const steps = [c.s1, c.s2, c.s3, c.s4, c.s5];
  const on = mode === "RECOVER" || mode === "LEAN";
  return (
    <ol className={"hiw-recovery" + (on ? " on" : "")} aria-label={c.aria}>
      {steps.map((s, i) => (
        <motion.li key={s} initial={false} animate={{ opacity: on ? 1 : .4 }} transition={{ delay: on ? i * .18 : 0, duration: .4 }}>
          <i />{s}
        </motion.li>
      ))}
    </ol>
  );
}

/* ------------------------------------------------------------------ before / after */

export function BeforeAfter() {
  const { t } = useLocale();
  const c = t.hiw.compare;
  const [split, setSplit] = useState(50);
  const rows: { label: string; a: string; b: string }[] = [
    { label: c.service, a: `${Math.round(COMPARE.current.service * 100)}%`, b: `${Math.round(COMPARE.zaad.service * 100)}%` },
    { label: c.inventory, a: `${COMPARE.current.inventory} ${c.periods}`, b: `${COMPARE.zaad.inventory} ${c.periods}` },
    { label: c.capital, a: `${COMPARE.current.capital}k`, b: `${COMPARE.zaad.capital}k` },
    { label: c.risk, a: `${Math.round(COMPARE.current.risk * 100)}`, b: `${Math.round(COMPARE.zaad.risk * 100)}` },
    { label: c.changed, a: `${COMPARE.current.changed}`, b: `${COMPARE.zaad.changed}` },
    { label: c.untouched, a: `${COMPARE.current.untouched}`, b: `${COMPARE.zaad.untouched}` },
  ];
  return (
    <div className="hiw-ba">
      <div className="hiw-ba-panes" style={{ ["--split" as string]: `${split}%` }}>
        <div className="hiw-ba-pane a"><span className="hiw-chip">{c.current}</span>{rows.map((r) => <div key={r.label} className="hiw-ba-row"><span>{r.label}</span><strong>{r.a}</strong></div>)}</div>
        <div className="hiw-ba-pane b"><span className="hiw-chip">{c.zaad}</span>{rows.map((r) => <div key={r.label} className="hiw-ba-row"><span>{r.label}</span><strong>{r.b}</strong></div>)}</div>
        <div className="hiw-ba-handle" aria-hidden />
      </div>
      <input type="range" min={10} max={90} value={split} onChange={(e) => setSplit(Number(e.target.value))} className="hiw-ba-slider" aria-label={c.sliderAria} />
      <p className="hiw-illustrative">{t.hiw.illustrative}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ action space */

const ACTION_EFFECT: Record<(typeof ACTIONS)[number], [number, number, number]> = {
  "Do nothing": [0, 0, 0], Buy: [3, .4, 60], "Buy less": [-3, -.3, -40], Defer: [0, -.15, -31], Cancel: [-2, -.3, -55], Reschedule: [1, -.05, -6],
  Expedite: [2, 0, 18], "De-expedite": [-1, 0, -12], Transfer: [3, -.1, 0], Substitute: [2, 0, 0], Allocate: [1, 0, 0], "Change supplier": [1, 0, 8], "Change route": [1, 0, 8],
};

export function ActionSpace() {
  const { t } = useLocale();
  const c = t.hiw.actions;
  const [picked, setPicked] = useState<number[]>([3, 8]);
  const effect = useMemo(() => {
    let s = 91, inv = 1.9, cap = 412;
    for (const i of picked) { const [ds, di, dc] = ACTION_EFFECT[ACTIONS[i]]; s += ds; inv += di; cap += dc; }
    return { service: Math.min(99, Math.max(60, s)), inventory: Math.max(.6, inv).toFixed(2), capital: Math.round(cap) };
  }, [picked]);
  return (
    <div className="hiw-actions">
      <div className="hiw-action-grid" role="group" aria-label={c.aria}>
        {ACTIONS.map((a, i) => <button key={a} type="button" className={"hiw-action" + (picked.includes(i) ? " on" : "")} aria-pressed={picked.includes(i)} onClick={() => setPicked((p) => p.includes(i) ? p.filter((x) => x !== i) : [...p, i])}>{c.labels[i]}</button>)}
      </div>
      <div className="hiw-action-effect" aria-live="polite">
        <div><span>{c.service}</span><strong>{effect.service}%</strong></div>
        <div><span>{c.inventory}</span><strong>{effect.inventory} {c.periods}</strong></div>
        <div><span>{c.capital}</span><strong>{effect.capital}k</strong></div>
        <p>{c.note}</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ approval */

export function ApprovalPanel() {
  const { t } = useLocale();
  const c = t.hiw.approval;
  const [open, setOpen] = useState<number | null>(0);
  const [approved, setApproved] = useState(false);
  return (
    <div className="hiw-approval">
      <div className="hiw-approval-head"><span className="hiw-chip accent">{c.recommends}</span><span className="hiw-chip muted">{approved ? c.approved : c.pending}</span></div>
      <ul>
        {c.items.map(([action, why], i) => (
          <li key={action} className={open === i ? "open" : ""}>
            <div className="hiw-rec-row">
              <strong>{action}</strong>
              <button type="button" className="hiw-why" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i} aria-controls={`hiw-why-${i}`}>{c.why}</button>
            </div>
            <AnimatePresence initial={false}>
              {open === i && <motion.div id={`hiw-why-${i}`} key="why" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: .3, ease: EASE }} style={{ overflow: "hidden" }}><p>{why}</p></motion.div>}
            </AnimatePresence>
          </li>
        ))}
      </ul>
      <div className="hiw-approval-actions">
        <button type="button" className="btn btn-ghost" onClick={() => setOpen(open === null ? 0 : (open + 1) % c.items.length)}>{c.review}</button>
        <button type="button" className="btn btn-primary" onClick={() => setApproved(true)} disabled={approved}>{approved ? c.approved : c.approve}</button>
      </div>
      <p className="hiw-note" aria-live="polite">{approved ? c.afterApprove : c.humanNote}</p>
    </div>
  );
}
