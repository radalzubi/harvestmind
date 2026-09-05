import type { Metadata } from "next";
import { Reveal } from "@/components/site/Reveal";

export const metadata: Metadata = { title: "Terms — zaad" };

export default function TermsPage() {
  return (
    <section className="page-hero">
      <div className="wrap doc">
        <Reveal><p className="eyebrow">Terms</p><h1 className="h1">Pilot terms</h1><p className="muted">Last updated 5 September 2026</p></Reveal>
        <Reveal delay={0.05} className="prose">
          <h3>The service</h3>
          <p>Zaad Supply provides a purchasing diagnostic and, where its own gate is passed, purchase plans, computed from files you upload. It is offered during the pilot without charge unless agreed separately in writing.</p>
          <h3>No guarantee of outcomes</h3>
          <p>Every figure is a backtest on your history under stated assumptions. It is not a forecast, and it is not advice to buy or not buy. Decisions remain yours.</p>
          <h3>Your content</h3>
          <p>You keep all rights to your files. You confirm you are entitled to upload them. We process them only to provide the service, as described in the privacy notice.</p>
          <h3>Keys</h3>
          <p>Whoever holds a workspace key can open that workspace. Keep it private; ask us to rotate it at any time.</p>
          <h3>Availability</h3>
          <p>The pilot may change or pause with notice on this site. We will give reasonable notice before removing a workspace.</p>
          <h3>Law</h3>
          <p>These terms are governed by the laws of the Hashemite Kingdom of Jordan.</p>
        </Reveal>
      </div>
    </section>
  );
}
