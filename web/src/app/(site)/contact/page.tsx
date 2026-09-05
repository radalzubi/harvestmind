import type { Metadata } from "next";
import Link from "next/link";
import { Reveal } from "@/components/site/Reveal";

export const metadata: Metadata = { title: "Contact — zaad" };

export default function ContactPage() {
  return (
    <section className="page-hero tall">
      <div className="wrap split">
        <Reveal>
          <p className="eyebrow">Contact</p>
          <h1 className="display sm">Write to us.</h1>
          <p className="lede">One address, read by the people who build the product.</p>
        </Reveal>
        <Reveal delay={0.1} className="contact-card">
          <h4>Email</h4>
          <a className="contact-big" href="mailto:hello@zaadsupply.com">hello@zaadsupply.com</a>
          <h4>Based in</h4>
          <p>Amman, Jordan</p>
          <h4>Already have a key?</h4>
          <p><Link href="/get-started?mode=key">Enter it here</Link> and go straight to your workspace.</p>
        </Reveal>
      </div>
    </section>
  );
}
