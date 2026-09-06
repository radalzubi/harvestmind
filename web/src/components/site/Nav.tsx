"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { ArrowRight } from "lucide-react";
import { Logo } from "./Logo";
import { useLocale } from "@/lib/i18n";

/** EN / عربي as one pill; the active language is the solid half. */
export function LangToggle({ className }: { className?: string }) {
  const { locale, setLocale } = useLocale();
  return (
    <div className={clsx("lang-pill", className)} role="group" aria-label="Language">
      <button type="button" className={locale === "en" ? "on" : ""} onClick={() => setLocale("en")} lang="en" aria-pressed={locale === "en"}>EN</button>
      <button type="button" className={locale === "ar" ? "on" : ""} onClick={() => setLocale("ar")} lang="ar" aria-pressed={locale === "ar"}>عربي</button>
    </div>
  );
}

/**
 * Three places to go, one thing to do. "Open workspace" covers both entering
 * a key and starting a new workspace; the get-started flow asks which.
 */
export function Nav() {
  const pathname = usePathname() || "/";
  const { t } = useLocale();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 8);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  useEffect(() => { setOpen(false); }, [pathname]);

  const links = [
    { href: "/product", label: t.nav.product },
    { href: "/sectors", label: t.nav.sectors },
    { href: "/about", label: t.nav.about },
    { href: "/resources", label: t.nav.resources },
  ];

  return (
    <header className={clsx("site-nav", scrolled && "scrolled", open && "open")}>
      <div className="site-nav-inner">
        <Logo size={24} />
        <nav className="site-links" aria-label="Site">
          {links.map((l) => (
            <Link key={l.href} href={l.href} className={clsx(pathname.startsWith(l.href) && "active")}>{l.label}</Link>
          ))}
        </nav>
        <div className="site-cta">
          <LangToggle />
          <Link href="/get-started" className="btn btn-primary">{t.nav.open} <ArrowRight size={14} className="dir-icon" /></Link>
        </div>
        <LangToggle className="lang-pill-mobile" />
        <button className="site-burger" aria-label={open ? t.nav.menuClose : t.nav.menuOpen} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
          <span /><span />
        </button>
      </div>
      <div className="site-drawer">
        {links.map((l) => <Link key={l.href} href={l.href}>{l.label}</Link>)}
        <Link href="/security">{t.nav.security}</Link>
        <Link href="/get-started" className="btn btn-primary" style={{ marginTop: 8 }}>{t.nav.open} <ArrowRight size={14} className="dir-icon" /></Link>
      </div>
    </header>
  );
}
