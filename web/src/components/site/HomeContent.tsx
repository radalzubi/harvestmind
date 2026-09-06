"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Reveal, Stagger, Item } from "./Reveal";
import { Hero } from "./Hero";
import { RouteCard } from "./RouteCard";
import { InventoryField } from "./InventoryField";
import { DecisionCard } from "./DecisionCard";
import { useLocale } from "@/lib/i18n";
import { QaContext } from "@/lib/motion";

export function HomeContent({ qa = false }: { qa?: boolean }) {
  const { t } = useLocale();
  const c = t.home;
  return (
    <QaContext.Provider value={qa}>
    <div className="home">
      <Hero />

      {/* the memorable interaction: a lane slips, the plan moves */}
      <section className="section moment">
        <div className="wrap split moment-split">
          <Reveal>
            <p className="eyebrow">{c.routeEyebrow}</p>
            <h2 className="h2">{c.routeH2}</h2>
            <p className="lede">{c.routeLede}</p>
          </Reveal>
          <Reveal delay={0.1} y={28}><RouteCard /></Reveal>
        </div>
      </section>

      {/* lean, protect, allocate, recover */}
      <section className="section">
        <div className="wrap split field-split">
          <Reveal delay={0.05} y={0} className="field-visual"><InventoryField /></Reveal>
          <Reveal>
            <p className="eyebrow">{c.fieldEyebrow}</p>
            <h2 className="h2">{c.fieldH2}</h2>
            <p className="lede">{c.fieldLede}</p>
          </Reveal>
        </div>
      </section>

      {/* how it decides */}
      <section className="section decide">
        <div className="wrap split">
          <div>
            <Reveal><p className="eyebrow">{c.decideEyebrow}</p></Reveal>
            <Reveal delay={0.05}><h2 className="h2">{c.decideH2}</h2></Reveal>
            <Stagger className="decide-steps" step={0.12}>
              {c.steps.map(([k, v], i) => (
                <Item key={k} className="decide-step"><span className="decide-n">{i + 1}</span><div><b>{k}</b><p>{v}</p></div></Item>
              ))}
            </Stagger>
          </div>
          <DecisionCard />
        </div>
      </section>

      {/* sectors, compact */}
      <section className="section sectors">
        <div className="wrap">
          <Reveal><p className="eyebrow">{c.sectorsEyebrow}</p></Reveal>
          <Reveal delay={0.05}><h2 className="h2">{c.sectorsH2}</h2></Reveal>
          <Stagger className="grid3">
            {c.sectors.map((s) => (
              <Item key={s.slug}>
                <Link href={`/get-started?sector=${s.slug}`} className="sector-card">
                  <h3>{s.title}</h3><p>{s.body}</p>
                  <span className="sector-card-go">{c.start} <ArrowRight size={14} className="dir-icon" /></span>
                </Link>
              </Item>
            ))}
          </Stagger>
        </div>
      </section>

      <section className="section">
        <div className="wrap">
          <Reveal className="cta-band">
            <h2 className="h2">{c.vaultH2}</h2>
            <p className="lede">{c.vaultLede}</p>
            <div className="cta-row">
              <Link href="/get-started" className="btn btn-primary btn-lg">{c.vaultCta} <ArrowRight size={16} className="dir-icon" /></Link>
              <Link href="/security" className="btn btn-ghost btn-lg">{c.vaultMore}</Link>
            </div>
          </Reveal>
        </div>
      </section>
    </div>
    </QaContext.Provider>
  );
}
