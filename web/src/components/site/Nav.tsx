"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { Logo } from "./Logo";
import { useLocale } from "@/lib/i18n";

export function LangToggle({ className }: { className?: string }) {
  const { locale, setLocale, t } = useLocale();
  return (
    <button type="button" className={clsx("lang-toggle", className)} onClick={() => setLocale(locale === "ar" ? "en" : "ar")}
      aria-label={locale === "ar" ? "Switch to English" : "التبديل إلى العربية"} lang={locale === "ar" ? "en" : "ar"}>
      {t.nav.lang}
    </button>
  );
}

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
    { href: "/security", label: t.nav.security },
    { href: "/about", label: t.nav.about },
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
          <Link href="/get-started?mode=key" className="btn btn-ghost">{t.nav.enterKey}</Link>
          <Link href="/get-started" className="btn btn-primary">{t.nav.getStarted}</Link>
        </div>
        <LangToggle className="lang-toggle-mobile" />
        <button className="site-burger" aria-label={open ? t.nav.menuClose : t.nav.menuOpen} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
          <span /><span />
        </button>
      </div>
      <div className="site-drawer">
        {links.map((l) => <Link key={l.href} href={l.href}>{l.label}</Link>)}
        <Link href="/get-started?mode=key">{t.nav.enterKey}</Link>
        <Link href="/get-started" className="btn btn-primary" style={{ marginTop: 8 }}>{t.nav.getStarted}</Link>
      </div>
    </header>
  );
}
