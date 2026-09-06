"use client";

import Link from "next/link";
import { Logo } from "./Logo";
import { useLocale } from "@/lib/i18n";

export function Footer() {
  const { t } = useLocale();
  const f = t.footer;
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="site-footer-brand">
          <Logo size={22} muted />
          <p>{f.blurb}</p>
        </div>
        <div className="site-footer-cols">
          <div><h4>{f.product}</h4><Link href="/product">{f.howItWorks}</Link><Link href="/sectors">{f.sectors}</Link><Link href="/security">{f.security}</Link></div>
          <div><h4>{f.company}</h4><Link href="/about">{f.about}</Link><Link href="/contact">{f.contact}</Link></div>
          <div><h4>{f.workspace}</h4><Link href="/get-started">{f.getStarted}</Link><Link href="/get-started?mode=key">{f.enterKey}</Link></div>
          <div><h4>{f.legal}</h4><Link href="/privacy">{f.privacy}</Link><Link href="/terms">{f.terms}</Link></div>
        </div>
      </div>
      <div className="site-footer-base">
        <span>© {new Date().getFullYear()} {f.rights}</span>
        <span>{f.tagline}</span>
      </div>
    </footer>
  );
}
