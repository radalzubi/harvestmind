"use client";

import { useEffect, useRef, useState } from "react";
import { Sparkles, X, Send } from "lucide-react";
import { apiFetch, getApiToken } from "@/lib/api";
import { useLocale } from "@/lib/i18n";

type Turn = { role: "user" | "assistant"; content: string };
type Summary = { summary: string; source: "model" | "rules" | "none"; model: string | null };

const T = {
  en: { open: "Explain", title: "Ask about this workspace", sub: "Answers use only what the engine computed for your data.",
        placeholder: "Ask anything, for example: why was my current policy kept?", send: "Ask", loading: "Reading your workspace…",
        thinking: "Thinking…", rules: "No language model is configured on this server; this is the plain reading from the numbers.",
        model: "Answered by", noKey: "Enter your key first." },
  ar: { open: "اشرح لي", title: "اسأل عن مساحة عملك", sub: "الإجابات تعتمد فقط على ما حسبه المحرك من بياناتك.",
        placeholder: "اسأل ما تريد، مثلاً: لماذا أُبقيت سياستي الحالية؟", send: "اسأل", loading: "جارٍ قراءة مساحة عملك…",
        thinking: "جارٍ التفكير…", rules: "لا يوجد نموذج لغوي مهيأ على هذا الخادم؛ هذه قراءة مباشرة من الأرقام.",
        model: "أجاب", noKey: "أدخل مفتاحك أولاً." },
};

export function AssistantButton() {
  const [open, setOpen] = useState(false);
  const { locale } = useLocale();
  const t = T[locale === "ar" ? "ar" : "en"];
  return (
    <>
      <button className="tbtn brand" onClick={() => setOpen(true)} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
        <Sparkles size={13} /> {t.open}
      </button>
      {open && <AssistantDrawer onClose={() => setOpen(false)} />}
    </>
  );
}

export function AssistantDrawer({ onClose }: { onClose: () => void }) {
  const { locale } = useLocale();
  const lang = locale === "ar" ? "ar" : "en";
  const t = T[lang];
  const [summary, setSummary] = useState<Summary | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!getApiToken()) { setError(t.noKey); return; }
    apiFetch<Summary>(`/assistant/summary?lang=${lang}`).then(setSummary).catch((e) => setError(e instanceof Error ? e.message : String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang]);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [turns, summary]);

  const ask = async () => {
    const question = q.trim();
    if (!question || busy) return;
    setQ(""); setBusy(true); setError(null);
    const next = [...turns, { role: "user" as const, content: question }];
    setTurns(next);
    try {
      const r = await apiFetch<{ answer: string }>("/assistant/ask", { method: "POST", body: JSON.stringify({ question, history: turns, lang }) });
      setTurns([...next, { role: "assistant", content: r.answer }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setBusy(false); }
  };

  return (
    <div className="drawer-scrim" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()} dir={lang === "ar" ? "rtl" : "ltr"} aria-label={t.title}>
        <header className="drawer-head">
          <div><b>{t.title}</b><div className="small muted">{t.sub}</div></div>
          <button className="iconbtn" onClick={onClose} aria-label="Close"><X size={15} /></button>
        </header>
        <div className="drawer-body">
          {!summary && !error && <p className="muted">{t.loading}</p>}
          {summary && (
            <div className="bubble assistant">
              {summary.summary.split("\n").map((line, i) => <p key={i}>{line}</p>)}
              <div className="xsmall faint" style={{ marginTop: 6 }}>{summary.source === "model" ? `${t.model} ${summary.model}` : summary.source === "rules" ? t.rules : ""}</div>
            </div>
          )}
          {turns.map((tn, i) => (
            <div key={i} className={`bubble ${tn.role}`}>{tn.content.split("\n").map((line, j) => <p key={j}>{line}</p>)}</div>
          ))}
          {busy && <p className="muted">{t.thinking}</p>}
          {error && <p style={{ color: "var(--bad)" }} role="alert">{error}</p>}
          <div ref={bottom} />
        </div>
        <form className="drawer-input" onSubmit={(e) => { e.preventDefault(); void ask(); }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.placeholder} aria-label={t.title} />
          <button className="tbtn primary" type="submit" disabled={busy || !q.trim()}><Send size={13} /> {t.send}</button>
        </form>
      </aside>
    </div>
  );
}
