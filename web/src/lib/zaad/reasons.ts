/**
 * The engine's reasons, in the operator's words.
 *
 * The planner writes its reasons for an engineer: "no candidate materially improves
 * priority-weighted service shortfall over the incumbent". That sentence is true and it belongs
 * in the record, but it is not what a buyer reads at eight in the morning.
 *
 * Every rule below maps one of the planner's own strings onto a sentence that says the same thing
 * without the vocabulary. The original is never discarded — it travels into Technical details, so
 * an analyst always sees exactly what the engine said.
 *
 * A reason that matches no rule is still shown, with the few terms that have plain equivalents
 * replaced. Nothing is dropped: an unexplained plan is worse than an awkward sentence.
 */

interface Rule { match: RegExp; say: string }

const RULES: Rule[] = [
  {
    match: /no candidate materially improves .*service shortfall over the incumbent/i,
    say: "No alternative ZAAD could build serves your customers better than what you are already doing, by enough to be worth the change.",
  },
  {
    match: /recovery candidate does not materially improve .*service shortfall/i,
    say: "The best recovery ZAAD could find does not meaningfully improve service over its decision reference.",
  },
  {
    match: /recovery candidate lowers a service without raising a higher-priority one/i,
    say: "The alternative would improve one customer's service by taking it from another of equal or higher priority.",
  },
  {
    match: /recovery candidate improves service but exceeds the configured economic downside tolerance/i,
    say: "An alternative would improve service, but it costs more in the bad cases than the tolerance you have set allows.",
  },
  {
    match: /out-of-model stress confirmation rejected/i,
    say: "Under the stress tests, the alternative either broke a physical limit, carried too much downside, or failed to recover service — so it was not offered.",
  },
  {
    match: /incumbent misses a requested service target .* and no candidate reaches it either/i,
    say: "ZAAD's decision reference misses a service target, and nothing ZAAD could build reaches it either.",
  },
  {
    match: /neither the incumbent nor any candidate meets every requested service target/i,
    say: "Neither ZAAD's decision reference nor any alternative meets every service target you have set.",
  },
  {
    match: /candidate meets a service target the incumbent misses, but exceeds the .*downside tolerance/i,
    say: "An alternative would meet a service target you are currently missing, but its downside is larger than the tolerance you have set.",
  },
  {
    match: /independent fitted-model confirmation does not establish positive benefit/i,
    say: "Checked a second time against a model fitted to your own history, the alternative's benefit did not hold up.",
  },
  {
    match: /own solve stopped with an optimality gap wider than the economic benefit claimed/i,
    say: "The solver did not finish exploring the alternative closely enough to be sure its advantage is real, so it was not offered.",
  },
  {
    match: /candidate meets every service target with no material economic penalty and materially less carried inventory/i,
    say: "The recommended plan meets every service target, costs no more to speak of, and holds materially less stock.",
  },
  {
    match: /service-first acceptance/i,
    say: "ZAAD's decision reference misses a service target; the recommendation meets every target and stays inside the downside tolerance you have set.",
  },
  {
    match: /unit-fill regression control cannot open approval gate/i,
    say: "A control that guards against service going backwards is not satisfied, so ZAAD will not recommend a change.",
  },
  {
    match: /operator incumbent is missing; a synthetic proxy is not evidence/i,
    say: "ZAAD does not know how you order today, and it will not judge you against an assumed policy. Declaring your ordering rule lets it compare properly.",
  },
  {
    match: /incumbent itself has no verified feasible projection/i,
    say: "ZAAD's decision reference could not be projected as physically workable, and ZAAD will not invent a fallback in its place.",
  },
  {
    match: /requested service targets are not jointly achievable/i,
    say: "Your service targets cannot all be met at once from where you are, so ZAAD looked for the best achievable recovery instead of pretending otherwise.",
  },
  {
    match: /no selection candidate achieves every requested service metric/i,
    say: "No alternative ZAAD could build meets every service measure you have set.",
  },
  {
    match: /^NO MATERIAL IMPROVEMENT AVAILABLE/i,
    say: "Nothing ZAAD could build changes cost, stock or service by enough to be worth acting on.",
  },
];

/** Terms with a plain equivalent, for a reason no rule recognises. */
const TERMS: Array<[RegExp, string]> = [
  [/\bthe incumbent\b/gi, "ZAAD's decision reference"],
  [/\bincumbent\b/gi, "ZAAD's decision reference"],
  [/\bcandidate\b/gi, "alternative"],
  [/\bpriority-weighted\b/gi, "priority-adjusted"],
  [/\bout-of-model\b/gi, "independent"],
  [/\bSLA\b/g, "service agreement"],
  [/\brecourse\b/gi, "future adjustment"],
];

/** One engine reason, said plainly. Returns null only for an empty string. */
export function plainReason(reason: string): string | null {
  const text = reason.trim();
  if (!text) return null;
  for (const rule of RULES) if (rule.match.test(text)) return rule.say;
  return TERMS.reduce((acc, [term, plain]) => acc.replace(term, plain), text);
}

/** The plan's reasons in operator language, de-duplicated and capped so nobody reads a wall. */
export function plainReasons(reasons: string[] | undefined, limit = 3): string[] {
  const out: string[] = [];
  for (const r of reasons ?? []) {
    const said = plainReason(r);
    if (said && !out.includes(said)) out.push(said);
    if (out.length >= limit) break;
  }
  return out;
}
