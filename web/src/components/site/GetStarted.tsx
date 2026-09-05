"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowLeft, ArrowRight, Check, KeyRound, Sparkles } from "lucide-react";
import { apiFetch, clearApiToken, setApiToken, setSector, type Sector } from "@/lib/api";

type Mode = "key" | "signup";
type Step = "sector" | "mode" | "details";

const SECTORS: Array<{ slug: Sector; title: string; body: string }> = [
  { slug: "produce", title: "Fresh produce", body: "Fruit, vegetables, anything with a shelf life in days." },
  { slug: "meats", title: "Meat and seafood", body: "Fresh and frozen, cold chain, lot-level traceability." },
  { slug: "commercial", title: "Commercial goods", body: "Packaged goods, household products, raw materials." },
];
const LABEL: Record<Sector, string> = { produce: "fresh produce", meats: "meat and seafood", commercial: "commercial goods" };

const DETAILS: Record<Mode, string[]> = {
  key: [
    "We check the key against its workspace and greet you by your company name.",
    "The key lives only in this browser tab. Close the tab and it is gone from here.",
    "You land in your workspace: upload, diagnostic, purchase plan and reports.",
  ],
  signup: [
    "A private, isolated workspace opens immediately. No form, no email.",
    "You get a key, shown once. Save it; it is the only way back in.",
    "Upload a year of files. Codes are pseudonymised the moment they land, then run the diagnostic.",
  ],
};

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
  const [sector, setSectorChoice] = useState<Sector | null>(null);
  const [mode, setMode] = useState<Mode | null>(null);
  const [step, setStep] = useState<Step>("sector");
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Deep links: /get-started?sector=produce, /get-started?mode=key
  useEffect(() => {
    const s = params.get("sector") as Sector | null;
    const m = params.get("mode") as Mode | null;
    if (s && SECTORS.some((x) => x.slug === s)) { setSectorChoice(s); setStep("mode"); }
    if (m === "key" || m === "signup") { setMode(m); setStep("details"); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
      setError(mode === "key" ? "That key did not open a workspace. Check it and try again." : (e instanceof Error ? e.message : "Could not open a workspace"));
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
              <p className="eyebrow">Step 1 of 3</p>
              <h1 className="h1">What do you bring in?</h1>
              <p className="lede">Pick the closest fit. It sets which files we ask for and how the diagnostic reads them.</p>
              <div className="gs-cards">
                {SECTORS.map((s, i) => (
                  <motion.button key={s.slug} type="button" className="gs-card" onClick={() => pickSector(s.slug)}
                    initial={reduce ? false : { opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08 + i * 0.07, duration: 0.5, ease }}
                    whileHover={reduce ? undefined : { y: -3 }} whileTap={{ scale: 0.99 }}>
                    <span className="gs-card-title">{s.title}</span>
                    <span className="gs-card-body">{s.body}</span>
                    <ArrowRight size={16} className="gs-card-arrow" />
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}

          {step === "mode" && (
            <motion.div key="mode" {...(reduce ? {} : slide)} className="gs-step">
              <button className="gs-back" onClick={back}><ArrowLeft size={14} /> Back</button>
              <p className="eyebrow">Step 2 of 3 · {sector ? LABEL[sector] : ""}</p>
              <h1 className="h1">How would you like in?</h1>
              <div className="gs-cards two">
                <motion.button type="button" className="gs-card" onClick={() => pickMode("key")} whileHover={reduce ? undefined : { y: -3 }} whileTap={{ scale: 0.99 }}>
                  <KeyRound size={20} className="gs-card-icon" />
                  <span className="gs-card-title">Use a key</span>
                  <span className="gs-card-body">You were given a workspace key. It takes you straight to your workspace.</span>
                  <ArrowRight size={16} className="gs-card-arrow" />
                </motion.button>
                <motion.button type="button" className="gs-card" onClick={() => pickMode("signup")} whileHover={reduce ? undefined : { y: -3 }} whileTap={{ scale: 0.99 }}>
                  <Sparkles size={20} className="gs-card-icon" />
                  <span className="gs-card-title">Sign up for a key</span>
                  <span className="gs-card-body">Open a private workspace now and get a key to come back with.</span>
                  <ArrowRight size={16} className="gs-card-arrow" />
                </motion.button>
              </div>
            </motion.div>
          )}

          {step === "details" && mode && (
            <motion.div key="details" {...(reduce ? {} : slide)} className="gs-step">
              <button className="gs-back" onClick={back}><ArrowLeft size={14} /> Back</button>
              <p className="eyebrow">Step 3 of 3 · {sector ? LABEL[sector] : "your workspace"}</p>
              <h1 className="h1">{mode === "key" ? "What happens next" : "What happens next"}</h1>
              <ol className="gs-details">
                {DETAILS[mode].map((d, i) => (
                  <motion.li key={d} initial={reduce ? false : { opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.15 + i * 0.1, duration: 0.5, ease }}>
                    <span className="gs-check"><Check size={13} /></span>{d}
                  </motion.li>
                ))}
              </ol>
              {mode === "key" ? (
                <form className="gs-form" onSubmit={(e) => { e.preventDefault(); void go(); }}>
                  <input inputMode="numeric" autoComplete="off" autoFocus placeholder="Your key" aria-label="Workspace key" value={key} onChange={(e) => setKey(e.target.value)} />
                  <button className="btn btn-primary btn-lg" type="submit" disabled={busy || !key.trim()}>{busy ? "Checking…" : "Open my workspace"} <ArrowRight size={16} /></button>
                </form>
              ) : (
                <div className="gs-form">
                  {!sector && <p className="gs-hint">Choose a sector first.</p>}
                  <button className="btn btn-primary btn-lg" type="button" disabled={busy || !sector} onClick={() => void go()}>{busy ? "Opening…" : "Open a workspace"} <ArrowRight size={16} /></button>
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
