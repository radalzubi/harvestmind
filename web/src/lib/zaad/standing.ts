/**
 * One ladder for "how is this workspace doing", used by every surface that says so.
 *
 * The product previously answered that question in three places at once, from three different
 * inputs, and could contradict itself in a single screen: "Nothing ZAAD can improve right now"
 * beside "1 area needs attention" beside a warehouse marked Critical whose service was projected
 * at 100% against a 95% target. Every sentence was true of its own input. Together they were
 * incoherent, and an operator cannot act on that.
 *
 * So there is now one deterministic ladder, and nothing else is allowed to state a standing:
 *
 *   1. BLOCKED   — ZAAD cannot answer. A required upload is missing, or the run failed, or the
 *                  information the answer rests on is not usable.
 *   2. DECIDE    — ZAAD has something for a person: a recommendation to review, or a proposal
 *                  waiting for approval.
 *   3. WATCH     — nothing to decide, but a measured condition is worth monitoring.
 *   4. NORMAL    — nothing to decide and nothing measured that needs watching.
 *
 * The rungs are exclusive and ordered. A workspace at DECIDE may still have watches, and they are
 * carried on the result so they can be shown *underneath* the decision rather than beside it as a
 * competing headline.
 */
import type { AttentionArea } from "@/lib/network/attention";
import type { Decision } from "./decisions";

export type Level = "blocked" | "decide" | "watch" | "normal" | "working";

export const LEVEL_LABEL: Record<Level, string> = {
  blocked: "Needs data",
  decide: "Needs a decision",
  watch: "Worth watching",
  normal: "Running normally",
  working: "Working on it",
};

export interface Standing {
  level: Level;
  /** The chip beside the headline. Usually `LEVEL_LABEL[level]`, but a blocked workspace is
   *  blocked for one of two different reasons and a chip that names the wrong one is worse than
   *  none: "Needs data" above "ZAAD could not finish its last run" is simply untrue. */
  label: string;
  /** The one sentence at the top of Home. */
  headline: string;
  /** What follows it. Never contradicts the headline; never repeats it. */
  detail: string;
  /** Conditions worth monitoring, whatever the level. */
  watches: AttentionArea[];
  /** Why ZAAD cannot answer, when it cannot. */
  blockers: string[];
  /** The single thing to do next, when there is one. */
  next: { label: string; href: string } | null;
}

export interface StandingInput {
  /** The workspace read failed or the vault is not ready to plan. */
  notReady: string | null;
  readError: string | null;
  /** Whether a plan exists, and whether the last attempt failed. */
  planPhase: "none" | "queued" | "running" | "ready" | "failed";
  planError: string | null;
  /** Decisions the plan produced that still want a human answer. */
  openDecisions: Decision[];
  /** Proposed orders sitting in review. */
  proposalsAwaitingReview: number;
  /** Network conditions the adapter measured. */
  areas: AttentionArea[];
  /** Data problems the build reported, already translated for an operator. */
  dataProblems: string[];
}

const count = (n: number, one: string, many: string) => `${n === 1 ? "One" : n} ${n === 1 ? one : many}`;

/** The plural-safe name of the first few watched things, for a sentence. */
function named(areas: AttentionArea[]): string {
  const names = areas.slice(0, 2).map((a) => a.title);
  if (!names.length) return "";
  if (areas.length <= 2) return names.join(" and ");
  return `${names.join(", ")} and ${areas.length - 2} more`;
}

export function standing(input: StandingInput): Standing {
  // Only a condition an operator would act on is a watch. The network model scores a site from
  // measured service shortfalls and products it cannot resupply; planned protection is the system
  // working and is deliberately not scored, so it never reaches this list.
  const watches = input.areas.filter((a) => a.level === "attention");
  const quiet = input.areas.filter((a) => a.level === "watch");

  // 1. BLOCKED
  const blockers: string[] = [];
  if (input.notReady) blockers.push(input.notReady);
  if (input.readError) blockers.push(input.readError);
  if (input.planPhase === "failed" && input.planError) blockers.push(input.planError);
  if (blockers.length) {
    return {
      level: "blocked",
      label: input.notReady ? LEVEL_LABEL.blocked : "Run interrupted",
      headline: input.notReady
        ? "ZAAD needs more before it can tell you what to change."
        : "ZAAD could not finish its last run.",
      detail: blockers[0],
      watches, blockers,
      next: input.notReady ? { label: "Add the missing data", href: "/upload" }
        : { label: "Try the run again", href: "/decisions" },
    };
  }

  // A run in flight is its own state. Without it the ladder said "Run a plan" while a plan was
  // running three inches below — the same class of contradiction this file exists to end.
  if (input.planPhase === "queued" || input.planPhase === "running") {
    return {
      level: "working",
      label: LEVEL_LABEL.working,
      headline: input.planPhase === "queued" ? "Your plan is queued." : "ZAAD is comparing your options.",
      detail: "A full comparison takes a few minutes. You can leave this page — the run continues and the "
        + "result will be here when you come back. Your stock, orders, suppliers and network are ready now."
        + (watches.length ? ` ${named(watches)} ${watches.length === 1 ? "needs" : "need"} watching meanwhile.` : ""),
      watches, blockers: [],
      next: null,
    };
  }

  // 2. DECIDE
  const decisions = input.openDecisions.length;
  const proposals = input.proposalsAwaitingReview;
  if (decisions || proposals) {
    const parts: string[] = [];
    if (decisions) parts.push(`${count(decisions, "recommendation", "recommendations")} to review`);
    if (proposals) parts.push(`${count(proposals, "proposed order", "proposed orders")} waiting for approval`);
    return {
      level: "decide",
      label: LEVEL_LABEL.decide,
      headline: decisions
        ? decisions === 1 ? "One thing needs your decision." : `${decisions} things need your decision.`
        : proposals === 1 ? "One proposed order is waiting for you." : `${proposals} proposed orders are waiting for you.`,
      detail: `${parts.join(", and ")}.${watches.length ? ` ${named(watches)} ${watches.length === 1 ? "also needs" : "also need"} watching.` : ""}`,
      watches, blockers: [],
      next: decisions ? { label: "Review the recommendations", href: "/decisions" }
        : { label: "Review the proposals", href: "/orders?state=READY_FOR_REVIEW" },
    };
  }

  // 3. WATCH
  if (watches.length) {
    return {
      level: "watch",
      label: LEVEL_LABEL.watch,
      headline: "No changes recommended.",
      detail: `${named(watches)} ${watches.length === 1 ? "needs" : "need"} monitoring. ZAAD compared your current plan against every alternative it can build and found none worth acting on, including here.`,
      watches, blockers: [],
      next: { label: "Look at the network", href: "/network" },
    };
  }

  // 4. NORMAL
  const planned = input.planPhase === "ready";
  return {
    level: "normal",
    label: LEVEL_LABEL.normal,
    headline: planned ? "No changes recommended." : "ZAAD has read your workspace.",
    detail: planned
      ? `ZAAD compared your current plan against every alternative it can build and found nothing worth changing.${quiet.length ? ` ${count(quiet.length, "thing is", "things are")} showing early signs but nothing that needs you.` : ""}${input.dataProblems.length ? " Your data has something worth a look, below." : ""}`
      : "Run a plan to find out what to change. Everything else — your stock, your orders, your suppliers and your network — is ready to look at now.",
    watches, blockers: [],
    next: planned ? null : { label: "Run a plan", href: "/decisions" },
  };
}
