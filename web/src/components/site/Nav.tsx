"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { Logo } from "./Logo";

const LINKS = [
  { href: "/product", label: "Product" },
  { href: "/sectors", label: "Sectors" },
  { href: "/security", label: "Security" },
  { href: "/about", label: "About" },
];

export function Nav() {
  const pathname = usePathname() || "/";
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 8);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  useEffect(() => { setOpen(false); }, [pathname]);

  return (
    <header className={clsx("site-nav", scrolled && "scrolled", open && "open")}>
      <div className="site-nav-inner">
        <Logo size={24} />
        <nav className="site-links" aria-label="Site">
          {LINKS.map((l) => (
            <Link key={l.href} href={l.href} className={clsx(pathname.startsWith(l.href) && "active")}>{l.label}</Link>
          ))}
        </nav>
        <div className="site-cta">
          <Link href="/get-started?mode=key" className="btn btn-ghost">Enter key</Link>
          <Link href="/get-started" className="btn btn-primary">Get started</Link>
        </div>
        <button className="site-burger" aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open} onClick={() => setOpen((o) => !o)}>
          <span /><span />
        </button>
      </div>
      <div className="site-drawer">
        {LINKS.map((l) => <Link key={l.href} href={l.href}>{l.label}</Link>)}
        <Link href="/get-started?mode=key">Enter key</Link>
        <Link href="/get-started" className="btn btn-primary" style={{ marginTop: 8 }}>Get started</Link>
      </div>
    </header>
  );
}
