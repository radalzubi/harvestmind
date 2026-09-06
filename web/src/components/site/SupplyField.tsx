"use client";

/**
 * SupplyField: the hero's living background.
 *
 * An abstract supply network on a 2D canvas: faint nodes (ports, suppliers,
 * warehouses, unlabelled), thin curved routes between them, and small
 * packets travelling along the routes. A slow ambient loop plays Zaad's
 * idea without words: routes flow evenly (NORMAL); one route fades and its
 * packets stop (DISRUPTION); a neighbouring route brightens and carries the
 * flow (ADAPTATION); the network settles back (RECOVERY).
 *
 * Costs are kept low on purpose: one rAF loop, transforms and alpha only,
 * device pixel ratio capped, paused when the tab is hidden or the hero is
 * off screen, fewer nodes on small screens, and a single static frame when
 * the visitor prefers reduced motion.
 */
import { useEffect, useRef } from "react";
import { reduceMotionNow } from "@/lib/motion";

type Node = { x: number; y: number; r: number; drift: number; phase: number; layer: 0 | 1 };
type Route = { a: number; b: number; cx: number; cy: number; act: number; target: number; hue: "calm" | "warm"; packets: number[]; speed: number };

const INK = { calm: [14, 159, 110] as const, warm: [217, 119, 6] as const, node: [24, 24, 27] as const };

export function SupplyField({ density = 1, pointer = true }: { density?: number; pointer?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const wrap = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvasEl = ref.current;
    const hostEl = wrap.current;
    if (!canvasEl || !hostEl) return;
    const canvas: HTMLCanvasElement = canvasEl;
    const host: HTMLDivElement = hostEl;
    const context = canvas.getContext("2d");
    if (!context) return;
    const ctx: CanvasRenderingContext2D = context;
    const reduce = reduceMotionNow();
    const small = window.innerWidth < 768;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);

    let w = 0, h = 0, nodes: Node[] = [], routes: Route[] = [];
    let raf = 0, last = 0, running = false, visible = true, onScreen = true, t = 0;
    let phase: "normal" | "disrupt" | "adapt" | "recover" = "normal";
    const CONTOURS = small ? 5 : 9;
    let phaseAt = 0, disrupted = -1, alternate = -1;
    const px = { x: 0, y: 0, tx: 0, ty: 0 };

    const seeded = (seed: number) => () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };

    function build() {
      const rect = host.getBoundingClientRect();
      w = Math.max(1, rect.width); h = Math.max(1, rect.height);
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      canvas.style.width = `${w}px`; canvas.style.height = `${h}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const rnd = seeded(7);
      const n = Math.round((small ? 10 : 20) * density);
      nodes = [];
      for (let i = 0; i < n; i++) {
        // the whole hero is the map; the paper veil keeps the headline readable
        const layer: 0 | 1 = i % 3 === 0 ? 0 : 1;   // 0 = far, small and faint; 1 = near
        const x = w * (0.03 + rnd() * 0.94);
        const y = h * (0.06 + rnd() * 0.9);
        nodes.push({ x, y, r: (layer ? 1.2 : 0.8) + rnd() * (layer ? 1.4 : 0.8), drift: 0.4 + rnd() * 0.8, phase: rnd() * Math.PI * 2, layer });
      }
      routes = [];
      // each node links to its two nearest neighbours; curved through a control point off the chord
      nodes.forEach((a, i) => {
        const near = nodes.map((b, j) => ({ j, d: Math.hypot(a.x - b.x, a.y - b.y), l: b.layer })).filter((o) => o.j !== i && o.l === a.layer).sort((p, q) => p.d - q.d).slice(0, 2);
        near.forEach(({ j }) => {
          if (routes.some((r) => (r.a === i && r.b === j) || (r.a === j && r.b === i))) return;
          const b = nodes[j];
          const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
          const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy) || 1;
          const bend = (rnd() - 0.5) * Math.min(220, len * 0.8);
          routes.push({ a: i, b: j, cx: mx - (dy / len) * bend, cy: my + (dx / len) * bend, act: 0.55, target: 0.55, hue: "calm",
                        packets: Array.from({ length: 1 + Math.floor(rnd() * 2) }, () => rnd()), speed: 0.04 + rnd() * 0.04 });
        });
      });
    }

    const bez = (r: Route, s: number) => {
      const a = nodes[r.a], b = nodes[r.b], u = 1 - s;
      return { x: u * u * a.x + 2 * u * s * r.cx + s * s * b.x, y: u * u * a.y + 2 * u * s * r.cy + s * s * b.y };
    };

    function step(dt: number) {
      t += dt;
      // ambient loop: 11s normal, 1.6s disruption onset, 6s adapted, 3s recovery
      const since = t - phaseAt;
      if (phase === "normal" && since > 11 && routes.length > 3) {
        disrupted = Math.floor((t * 13) % routes.length);
        const d = routes[disrupted];
        const cand = routes.map((r, i) => ({ r, i })).filter(({ r, i }) => i !== disrupted && (r.a === d.a || r.b === d.a || r.a === d.b || r.b === d.b));
        alternate = cand.length ? cand[Math.floor((t * 7) % cand.length)].i : -1;
        d.target = 0.12; d.hue = "warm"; phase = "disrupt"; phaseAt = t;
      } else if (phase === "disrupt" && since > 1.6) {
        if (alternate >= 0) { routes[alternate].target = 1; routes[alternate].hue = "calm"; }
        phase = "adapt"; phaseAt = t;
      } else if (phase === "adapt" && since > 6) {
        if (disrupted >= 0) { routes[disrupted].target = 0.55; routes[disrupted].hue = "calm"; }
        if (alternate >= 0) routes[alternate].target = 0.55;
        phase = "recover"; phaseAt = t;
      } else if (phase === "recover" && since > 3) {
        phase = "normal"; phaseAt = t; disrupted = -1; alternate = -1;
      }
      for (const r of routes) {
        r.act += (r.target - r.act) * Math.min(1, dt * 1.6);
        if (r.act > 0.25) for (let k = 0; k < r.packets.length; k++) r.packets[k] = (r.packets[k] + dt * r.speed * (0.6 + r.act)) % 1;
      }
      px.x += (px.tx - px.x) * Math.min(1, dt * 3);
      px.y += (px.ty - px.y) * Math.min(1, dt * 3);
    }

    function contours() {
      // slow, wide waves: the terrain the routes cross. Phase drifts with t.
      for (let k = 0; k < CONTOURS; k++) {
        const y0 = h * (0.08 + (k / (CONTOURS - 1)) * 0.84);
        const amp = h * 0.05 * (0.6 + ((k * 7) % 5) / 5);
        const f = 1.4 + ((k * 3) % 4) * 0.35;
        const ph = t * 0.06 * (1 + (k % 3) * 0.35) + k;
        ctx.beginPath();
        for (let x = -20; x <= w + 20; x += 24) {
          const y = y0 + Math.sin((x / w) * Math.PI * f + ph) * amp + Math.sin((x / w) * Math.PI * 4.1 + ph * 1.7) * amp * 0.25;
          if (x === -20) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = `rgba(24,24,27,${0.034 + (k % 2) * 0.014})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
    }

    function draw() {
      ctx.clearRect(0, 0, w, h);
      ctx.lineCap = "round";
      ctx.save();
      if (pointer && !small) ctx.translate(px.x * 0.25, px.y * 0.25);
      contours();
      ctx.restore();
      const par = pointer && !small;
      for (const layer of [0, 1] as const) {
        ctx.save();
        if (par) ctx.translate(px.x * (layer ? 1 : 0.4), px.y * (layer ? 1 : 0.4));
        const dim = layer ? 1 : 0.55;
        for (const r of routes) {
          const a = nodes[r.a], b = nodes[r.b];
          if (a.layer !== layer) continue;
          const c = INK[r.hue];
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.quadraticCurveTo(r.cx, r.cy, b.x, b.y);
          ctx.strokeStyle = `rgba(${c[0]},${c[1]},${c[2]},${(0.05 + r.act * 0.15) * dim})`;
          ctx.lineWidth = (0.8 + r.act * 0.9) * (layer ? 1 : 0.7);
          ctx.stroke();
          if (r.act > 0.25) {
            for (const s of r.packets) {
              const p = bez(r, s);
              const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, 8);
              g.addColorStop(0, `rgba(${c[0]},${c[1]},${c[2]},${0.45 * r.act * dim})`); g.addColorStop(1, `rgba(${c[0]},${c[1]},${c[2]},0)`);
              ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p.x, p.y, 8, 0, Math.PI * 2); ctx.fill();
              ctx.fillStyle = `rgba(${c[0]},${c[1]},${c[2]},${0.75 * r.act * dim})`; ctx.beginPath(); ctx.arc(p.x, p.y, layer ? 1.7 : 1.2, 0, Math.PI * 2); ctx.fill();
            }
          }
        }
        nodes.forEach((n, i) => {
          if (n.layer !== layer) return;
          const breathe = reduce ? 0 : Math.sin(t * n.drift + n.phase) * 0.6;
          const lit = routes.some((r) => (r.a === i || r.b === i) && r.act > 0.8);
          ctx.beginPath(); ctx.arc(n.x, n.y, n.r + breathe + (lit ? 1 : 0), 0, Math.PI * 2);
          ctx.fillStyle = lit ? `rgba(${INK.calm.join(",")},${0.7 * dim})` : `rgba(${INK.node.join(",")},${0.18 * dim})`;
          ctx.fill();

        });
        ctx.restore();
      }
    }

    function frame(now: number) {
      if (!running) return;
      const dt = Math.min(0.05, (now - last) / 1000 || 0.016);
      last = now;
      step(dt); draw();
      raf = requestAnimationFrame(frame);
    }
    function start() { if (running || reduce || !visible || !onScreen) return; running = true; last = performance.now(); raf = requestAnimationFrame(frame); }
    function stop() { running = false; cancelAnimationFrame(raf); }

    build();
    if (reduce) { step(0); draw(); } else start();

    const onVis = () => { visible = document.visibilityState === "visible"; visible ? start() : stop(); };
    const io = new IntersectionObserver(([e]) => { onScreen = e.isIntersecting; onScreen ? start() : stop(); }, { threshold: 0.05 });
    io.observe(host);
    const ro = new ResizeObserver(() => { build(); if (reduce) draw(); });
    ro.observe(host);
    const onMove = (e: PointerEvent) => {
      if (!pointer || small || reduce) return;
      const rect = host.getBoundingClientRect();
      px.tx = ((e.clientX - rect.left) / rect.width - 0.5) * 8;
      px.ty = ((e.clientY - rect.top) / rect.height - 0.5) * 6;
    };
    document.addEventListener("visibilitychange", onVis);
    window.addEventListener("pointermove", onMove, { passive: true });
    return () => { stop(); io.disconnect(); ro.disconnect(); document.removeEventListener("visibilitychange", onVis); window.removeEventListener("pointermove", onMove); };
  }, [density, pointer]);

  return (
    <div ref={wrap} className="field" aria-hidden>
      <canvas ref={ref} />
    </div>
  );
}
