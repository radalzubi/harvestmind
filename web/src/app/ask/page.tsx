"use client";

/**
 * ASK ZAAD — a question in, a governed analysis out.
 *
 * The conversation is a list of turns kept in this tab. Each answer shows what was planned, the
 * chart the server recommended, the typed claims (OBSERVATION / ASSOCIATION / MODELLED / PLAN
 * RESULT / MISSING), the reasons present, and Data & scope. A follow-up sends the previous
 * validated spec, so "only Beverages" narrows rather than restarts. Every answer can be saved,
 * added to a dashboard, opened in Explore, followed to the records, or handed to the planner as a
 * decision context — which builds the canonical request and never a recommendation.
 */
import { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Send } from "lucide-react";
import { Gate } from "@/components/workspace/Gate";
import { Button, Disclosure, Loading, Notice, PageHead } from "@/components/workspace/ui";
import { Drawer } from "@/components/workspace/Table";
import { useToast } from "@/components/Toast";
import { useLocale } from "@/lib/i18n";
import { useSession } from "@/lib/session";
import { track } from "@/lib/zaad/product";
import { askStatus, askZaad, createAnalysis, listDashboards, requestHandoff, updateDashboard, type AskAnswer, type Dashboard, type Handoff, type QuerySpec, type VisualType } from "@/lib/analytics/client";
import { fromSpec, stateToParams } from "@/lib/analytics/spec";
import { drillThrough, recordsBehind } from "@/lib/analytics/links";
import { AnalysisCard } from "@/components/analytics/AnalysisCard";

interface Turn { question: string; answer: AskAnswer | null; error: string | null }

function Body() {
  const search = useSearchParams();
  const session = useSession();
  const toast = useToast();
  const { locale, t } = useLocale();
  const lc = locale === "ar" ? "ar" : "en";
  const copy = t.analytics.ask;
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<{ model_available: boolean } | null>(null);
  const [conversation] = useState(() => `c_${Math.random().toString(36).slice(2, 10)}`);
  const [seed] = useState<QuerySpec | null>(() => { const s = search.get("spec"); if (!s) return null; try { return JSON.parse(s) as QuerySpec; } catch { return null; } });
  const [handoff, setHandoff] = useState<{ turn: number; result: Handoff | null; busy: boolean; issue: string } | null>(null);
  const [dashboards, setDashboards] = useState<Dashboard[]>([]);
  const [savePick, setSavePick] = useState<number | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => { askStatus().then(setStatus).catch(() => setStatus(null)); track("insights_opened", { surface: "ask" }); }, []);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [turns.length, busy]);

  const previous = () => { for (let i = turns.length - 1; i >= 0; i--) { const a = turns[i].answer; if (a?.answered && a.spec) return { spec: a.spec, visual: a.visual?.visual_type ?? null }; } return seed ? { spec: seed, visual: null } : null; };

  const ask = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    setBusy(true);
    setQuestion("");
    const index = turns.length;
    setTurns((ts) => [...ts, { question: q, answer: null, error: null }]);
    const prev = previous();
    try {
      const answer = await askZaad({ question: q, locale: lc, previous: prev?.spec ?? null, previous_visual_type: (prev?.visual as VisualType | null) ?? null, conversation_id: conversation });
      setTurns((ts) => ts.map((tu, i) => (i === index ? { ...tu, answer } : tu)));
    } catch (e) {
      setTurns((ts) => ts.map((tu, i) => (i === index ? { ...tu, error: (e as Error).message } : tu)));
    } finally { setBusy(false); }
  };

  const save = async (turn: number, dashboardId?: string) => {
    const a = turns[turn]?.answer;
    if (!a?.visual) return;
    try {
      const saved = await createAnalysis({ name: (a.visual.title[lc] || a.visual.title.en || a.question || "Ask ZAAD").slice(0, 160), visual: a.visual, origin: "ask_zaad",
                                           notes: `planner=${a.planner}; intent=${a.intent}; question=${(a.question ?? "").slice(0, 200)}` });
      if (dashboardId) {
        const board = dashboards.find((d) => d.dashboard_id === dashboardId);
        if (board) await updateDashboard(board.dashboard_id, { spec: { ...board.spec, tiles: [...board.spec.tiles, { tile_id: `t_${saved.analysis_id.slice(3)}`, analysis_id: saved.analysis_id, x: 0, y: board.spec.tiles.length, w: 2, h: 1 }] } });
      }
      toast.push(`${copy.saved}: ${saved.name}`);
      setSavePick(null);
    } catch (e) { toast.push((e as Error).message, "warn"); }
  };
  const openSavePicker = async (turn: number) => { setSavePick(turn); try { setDashboards((await listDashboards({ limit: 50 })).rows); } catch { setDashboards([]); } };

  const startHandoff = (turn: number) => setHandoff({ turn, result: null, busy: false, issue: turns[turn].question });
  const runHandoff = async (submit: boolean) => {
    if (!handoff) return;
    const a = turns[handoff.turn].answer;
    if (!a?.spec) return;
    setHandoff((h) => (h ? { ...h, busy: true } : h));
    try {
      const result = await requestHandoff({ query: a.spec, observed_issue: handoff.issue, skus: a.handoff?.skus ?? [], suppliers: a.handoff?.suppliers ?? [], submit });
      setHandoff((h) => (h ? { ...h, result, busy: false } : h));
      if (result.job?.submitted) toast.push(copy.submitted);
    } catch (e) { toast.push((e as Error).message, "warn"); setHandoff((h) => (h ? { ...h, busy: false } : h)); }
  };

  return (
    <div className="ask">
      <PageHead title={copy.title} sub={copy.sub} />
      <p className="zhelp" role="status">{status ? (status.model_available ? copy.modelOn : copy.modelOff) : ""}</p>
      <div className="ask-thread" aria-live="polite">
        {turns.length === 0 && (
          <div className="ask-empty">
            <p>{copy.empty}</p>
            <ul className="ask-examples">{copy.examples.map((ex) => <li key={ex}><button type="button" className="chip" onClick={() => ask(ex)}>{ex}</button></li>)}</ul>
            <p className="zhelp">{copy.followUp}</p>
          </div>
        )}
        {turns.map((turn, i) => (
          <article key={i} className="ask-turn">
            <p className="ask-q"><span className="sr-only">{copy.question}: </span>{turn.question}</p>
            {turn.error && <Notice tone="warn">{turn.error}</Notice>}
            {!turn.answer && !turn.error && <p className="phase"><span className="spin" aria-hidden />{copy.thinking}</p>}
            {turn.answer && !turn.answer.answered && (
              <div className="ask-a">
                <Notice><strong>{copy.clarification}.</strong> {turn.answer.clarification}</Notice>
                {turn.answer.warnings.length > 0 && <ul className="ask-warn">{turn.answer.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
              </div>
            )}
            {turn.answer && turn.answer.answered && turn.answer.visual && turn.answer.result && (
              <div className="ask-a">
                <AnalysisCard visual={turn.answer.visual} result={turn.answer.result} height={300}
                  badge={<span className="tag" data-tone="approx">{copy.planner}: {turn.answer.planner}</span>}
                  leads={[...(recordsBehind(turn.answer.result) ? [{ ...recordsBehind(turn.answer.result)!, label: copy.openRecords }] : []),
                          ...(turn.answer.handoff?.suppliers?.slice(0, 1).map((s) => drillThrough("supplier", s)!).filter(Boolean) ?? [])]}
                  actions={<>
                    {session.can("createAnalysis") && <button type="button" className="zb zb--tertiary zb--sm" onClick={() => openSavePicker(i)}>{copy.save}</button>}
                    <Link href={`/explore?${stateToParams(fromSpec(turn.answer.spec!, turn.answer.visual.visual_type)).toString()}`} className="zb zb--tertiary zb--sm">{copy.modify}</Link>
                    {turn.answer.handoff?.possible && session.can("askZaad") && <button type="button" className="zb zb--secondary zb--sm" onClick={() => startHandoff(i)}>{copy.whatShouldChange}</button>}
                  </>}>
                  <div className="ask-claims">
                    <h4>{copy.claims}</h4>
                    <ul>
                      {(turn.answer.claims ?? []).map((c, k) => <li key={k} data-kind={c.kind}><span className="ask-kind">{copy.kinds[c.kind]}</span> {c.text}</li>)}
                    </ul>
                    <p className="zhelp">{copy.visual}: {turn.answer.visual_reason}{turn.answer.reasons_present?.length ? ` · ${copy.reasons}: ${turn.answer.reasons_present.map((r) => t.analytics.reasons[r as keyof typeof t.analytics.reasons] ?? r).join(", ")}` : ""}</p>
                    {turn.answer.warnings.length > 0 && <ul className="ask-warn">{turn.answer.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
                    <Disclosure summary={copy.attempts} hint={`${turn.answer.attempts.length}`}>
                      <ol style={{ margin: 0, paddingInlineStart: 18 }}>{turn.answer.attempts.map((a, k) => <li key={k}>{a.source}: {a.outcome}{a.code ? ` (${a.code}: ${a.message})` : ""}</li>)}</ol>
                      {turn.answer.attempts.some((a) => a.outcome === "refused") && <p className="zhelp">{copy.refused}.</p>}
                    </Disclosure>
                  </div>
                </AnalysisCard>
              </div>
            )}
          </article>
        ))}
        <div ref={bottom} />
      </div>
      <form className="ask-form" onSubmit={(e) => { e.preventDefault(); ask(question); }}>
        <label className="sr-only" htmlFor="ask-input">{copy.placeholder}</label>
        <input id="ask-input" className="zinput" placeholder={copy.placeholder} value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={1000} disabled={busy} dir="auto" />
        <Button role="primary" icon={<Send size={14} aria-hidden />} disabled={busy || !question.trim()} type="submit">{copy.send}</Button>
        {turns.length > 0 && <Button role="tertiary" onClick={() => setTurns([])} type="button">{copy.newConversation}</Button>}
      </form>

      <Drawer open={savePick !== null} title={copy.save} onClose={() => setSavePick(null)} actions={<Button role="primary" onClick={() => savePick !== null && save(savePick)}>{copy.save}</Button>}>
        <p className="zhelp">{copy.addToDashboard}</p>
        <ul className="db-pick">
          {dashboards.map((d) => <li key={d.dashboard_id}><button type="button" className="zb zb--tertiary zb--block" style={{ justifyContent: "flex-start" }} onClick={() => savePick !== null && save(savePick, d.dashboard_id)}>{d.name}</button></li>)}
        </ul>
      </Drawer>

      <Drawer open={handoff !== null} title={copy.handoffTitle} onClose={() => setHandoff(null)} wide
              actions={handoff && !handoff.result?.request_built ? <Button role="primary" disabled={handoff.busy} onClick={() => runHandoff(false)}>{copy.buildRequest}</Button>
                : handoff?.result?.request_built && session.can("evaluate") && !handoff.result.job ? <Button role="primary" disabled={handoff.busy} onClick={() => runHandoff(true)}>{copy.submitPlan}</Button> : undefined}>
        {handoff && (
          <>
            <p className="zhelp">{copy.handoffHint}</p>
            <div className="zfield"><label className="zlabel" htmlFor="ho-issue">{copy.question}</label><textarea id="ho-issue" className="zinput" rows={2} value={handoff.issue} maxLength={600} onChange={(e) => setHandoff((h) => (h ? { ...h, issue: e.target.value } : h))} /></div>
            <dl className="kv">
              <dt>{copy.contextSkus}</dt><dd>{turns[handoff.turn].answer?.handoff?.skus.join(", ") || (handoff.result?.context.skus.join(", ") ?? "—")}</dd>
              <dt>{copy.contextSuppliers}</dt><dd>{turns[handoff.turn].answer?.handoff?.suppliers.join(", ") || "—"}</dd>
              {handoff.result && <><dt>{copy.buildRequest}</dt><dd>{handoff.result.request_built ? JSON.stringify(handoff.result.request_summary) : `${handoff.result.refusal?.code}: ${handoff.result.refusal?.message}`}</dd></>}
              {handoff.result?.notes?.map((n) => <div key={n} style={{ display: "contents" }}><dt>Note</dt><dd>{n}</dd></div>)}
              {handoff.result?.job && <><dt>{copy.submitPlan}</dt><dd>{handoff.result.job.submitted ? <Link href="/decisions">{copy.submitted} · {handoff.result.job.job_id}</Link> : `${handoff.result.job.error}: ${handoff.result.job.message}`}</dd></>}
            </dl>
          </>
        )}
      </Drawer>
    </div>
  );
}

export default function AskPage() {
  return <Gate needsWorkspace={false}><Suspense fallback={<Loading label="Ask ZAAD" cards={1} />}><Body /></Suspense></Gate>;
}
