"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowLeft, ArrowRight, Check, KeyRound, Sparkles } from "lucide-react";
import { apiFetch, clearApiToken, setApiToken, setSector, type Sector } from "@/lib/api";
import { useLocale } from "@/lib/i18n";

type Mode = "key" | "signup";
type Step = "sector" | "mode" | "details";



const ease = [0.22, 1, 0.36, 1] as const;
const slide = {
  initial: { opacity: 0, x: 28 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -28 },
  transition: { duration: 0.45, ease },
};

export function GetStarted() {
  const router = useRouter();
  const params = useSearchParams();
  const reduce = useReducedMotion();
  const { t } = useLocale();
  const g = t.gs;
  const SECTORS = g.sectors as Array<{ slug: Sector; title: string; body: string }>;
  // Deep links (/get-started?sector=produce, ?mode=key) start on the right
  // step at first render, so nothing has to animate out of the way.
  const initialSector = (() => { const v = params.get("sector"); return v && SECTORS.some((x) => x.slug === v) ? (v as Sector) : null; })();
  const initialMode = (() => { const v = params.get("mode"); return v === "key" || v === "signup" ? (v as Mode) : null; })();
  const [sector, setSectorChoice] = useState<Sector | null>(initialSector);
  const [mode, setMode] = useState<Mode | null>(initialMode);
  const [step, setStep] = useState<Step>(initialMode ? "details" : initialSector ? "mode" : "sector");
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pickSector = (s: Sector) => { setSectorChoice(s); setError(null); setStep("mode"); };
  const pickMode = (m: Mode) => { setMode(m); setError(null); setStep("details"); };
  const back = () => { setError(null); setStep(step === "details" ? "mode" : "sector"); };

  const go = async () => {
    setBusy(true); setError(null);
    try {
      if (mode === "signup") {
        if (!sector) { setStep("sector"); return; }
        const r = await apiFetch<{ token: string }>("/access/start", { method: "POST", body: JSON.stringify({ sector }) });
        setApiToken(r.token); setSector(sector);
        router.push("/start?new=1");
      } else {
        if (!key.trim()) return;
        setApiToken(key.trim());
        await apiFetch("/me");
        router.push("/welcome");
      }
    } catch (e) {
      if (mode === "key") clearApiToken();
      setError(mode === "key" ? g.badKey : (e instanceof Error ? e.message : g.failed));
    } finally { setBusy(false); }
  };

  const stepIndex = step === "sector" ? 0 : step === "mode" ? 1 : 2;

  return (
    <section className="gs">
      <div className="wrap gs-wrap">
        <div className="gs-progress" aria-hidden>
          {[0, 1, 2].map((i) => <span key={i} className={i <= stepIndex ? "on" : ""} />)}
        </div>

        <AnimatePresence mode="wait" initial={false}>
          {step === "sector" && (
            <motion.div key="sector" {...(reduce ? {} : slide)} className="gs-step">
              <p className="eyebrow">{g.step} 1 {g.of} 3</p>
              <h1 className="h1">{g.q1}</h1>
              <p className="lede">{g.q1sub}</p>
              <div className="gs-cards">
                {SECTORS.map((s, i) => (
                  <motion.button key={s.slug} type="button" className="gs-card" onClick={() => pickSector(s.slug)}
                    initial={reduce ? false : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 + i * 0.07, duration: 0.5, ease }}
                    whileHover={reduce ? undefined : { y: -3 }} whileTap={{ scale: 0.99 }}>
                    <span className="gs-card-title">{s.title}</span>
                    <span className="gs-card-body">{s.body}</span>
                    <ArrowRight size={16} className="gs-card-arrow dir-icon" />
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}

          {step === "mode" && (
            <motion.div key="mode" {...(reduce ? {} : slide)} className="gs-step">
              <button className="gs-back" onClick={back}><ArrowLeft size={14} className="dir-icon" /> {g.back}</button>
              <p className="eyebrow">{g.step} 2 {g.of} 3 · {sector ? g.label[sector] : ""}</p>
              <h1 className="h1">{g.q2}</h1>
              <div className="gs-cards two">
                <motion.button type="button" className="gs-card" onClick={() => pickMode("key")} whileHover={reduce ? undefined : { y: -3 }} whileTap={{ scale: 0.99 }}>
                  <KeyRound size={20} className="gs-card-icon" />
                  <span className="gs-card-title">{g.useKey}</span>
                  <span className="gs-card-body">{g.useKeyBody}</span>
                  <ArrowRight size={16} className="gs-card-arrow dir-icon" />
                </motion.button>
                <motion.button type="button" className="gs-card" onClick={() => pickMode("signup")} whileHover={reduce ? undefined : { y: -3 }} whileTap={{ scale: 0.99 }}>
                  <Sparkles size={20} className="gs-card-icon" />
                  <span className="gs-card-title">{g.signup}</span>
                  <span className="gs-card-body">{g.signupBody}</span>
                  <ArrowRight size={16} className="gs-card-arrow dir-icon" />
                </motion.button>
              </div>
            </motion.div>
          )}

          {step === "details" && mode && (
            <motion.div key="details" {...(reduce ? {} : slide)} className="gs-step">
              <button className="gs-back" onClick={back}><ArrowLeft size={14} className="dir-icon" /> {g.back}</button>
              <p className="eyebrow">{g.step} 3 {g.of} 3 · {sector ? g.label[sector] : g.yourWorkspace}</p>
              <h1 className="h1">{g.q3}</h1>
              <ol className="gs-details">
                {g.details[mode].map((d, i) => (
                  <motion.li key={d} initial={reduce ? false : { opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 + i * 0.1, duration: 0.5, ease }}>
                    <span className="gs-check"><Check size={13} /></span>{d}
                  </motion.li>
                ))}
              </ol>
              {mode === "key" ? (
                <form className="gs-form" onSubmit={(e) => { e.preventDefault(); void go(); }}>
                  <input inputMode="numeric" autoComplete="off" autoFocus placeholder={g.keyPlaceholder} aria-label={g.keyLabel} value={key} onChange={(e) => setKey(e.target.value)} />
                  <button className="btn btn-primary btn-lg" type="submit" disabled={busy || !key.trim()}>{busy ? g.checking : g.openMine} <ArrowRight size={16} className="dir-icon" /></button>
                </form>
              ) : (
                <div className="gs-form">
                  {!sector && <p className="gs-hint">{g.chooseFirst}</p>}
                  <button className="btn btn-primary btn-lg" type="button" disabled={busy || !sector} onClick={() => void go()}>{busy ? g.opening : g.openNew} <ArrowRight size={16} className="dir-icon" /></button>
                </div>
              )}
              {error && <p className="gs-error" role="alert">{error}</p>}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
