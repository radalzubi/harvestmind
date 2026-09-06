"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight } from "lucide-react";
import { Logo } from "@/components/site/Logo";
import { getApiToken, getMe, setSector, type Me } from "@/lib/api";
import { useLocale } from "@/lib/i18n";

const ease = [0.22, 1, 0.36, 1] as const;

export default function WelcomePage() {
  const reduce = useReducedMotion();
  const { t } = useLocale(); const w = t.welcome;
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!getApiToken()) { setError("no-key"); return; }
    getMe().then((m) => { setMe(m); setSector(m.sector); }).catch((e) => setError(e.message));
  }, []);

  if (error === "no-key") return <main className="welcome"><p>{w.noKey} <Link href="/get-started?mode=key">{w.enterOne}</Link></p></main>;
  if (error) return <main className="welcome"><p>{w.badKey} <Link href="/get-started?mode=key">{w.tryAgain}</Link></p></main>;
  if (!me) return <main className="welcome" />;
  const name = me.display_name || me.name;
  const up = (d: number) => ({ initial: reduce ? false : { opacity: 0, y: 18 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.7, delay: d, ease } });
  return (
    <main className="welcome">
      <motion.div initial={reduce ? false : { opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7, ease }}>
        {me.logo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img className="welcome-logo" src={me.logo_url} alt={`${name} logo`} />
        ) : (
          <div className="welcome-mark">{name.slice(0, 1)}</div>
        )}
      </motion.div>
      <motion.h1 {...up(0.15)}>{w.hello} {name}</motion.h1>
      <motion.p className="welcome-sub" {...up(0.25)}>
        {w.ready.replace("{sector}", w.sector[me.sector] ?? "")}
      </motion.p>
      <motion.div {...up(0.35)}>
        <Link className="btn btn-primary btn-lg" href="/start">{w.open} <ArrowRight size={16} className="dir-icon" /></Link>
      </motion.div>
      <motion.div className="welcome-foot" {...up(0.5)}><Logo size={18} muted /></motion.div>
    </main>
  );
}
