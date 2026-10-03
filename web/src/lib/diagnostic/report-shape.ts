/**
 * Can the in-app report view show this stored report?
 *
 * A diagnostic job keeps the report that was built when it ran. The view reads the sections of the
 * current report format without a guard, so a report stored in an earlier format — from before the
 * policy benchmark and the historical decision replay became sections of their own — made the
 * whole page throw while rendering. That is what happened on 2026-10-03: a workspace whose newest
 * run dated from the earlier format could not open `/start` at all.
 *
 * The lists below are exactly the sections the view dereferences unconditionally. A report that
 * lacks any of them is never handed to the view; it is shown as "produced by a different version"
 * with its PDF, which the server still renders.
 */
import type { DiagnosticReport } from "@/lib/api";

/** Sections that must be objects. */
export const REQUIRED_OBJECTS = [
  "conclusion",
  "executive_summary", "executive_summary.benchmark", "executive_summary.replay", "executive_summary.confidence",
  "readiness", "ordering_today", "policy_benchmark", "optimizer_replay", "suppliers", "actions",
  "appendix", "appendix.run",
] as const;

/** Sections that must be lists. */
export const REQUIRED_LISTS = [
  "executive_summary.findings", "executive_summary.actions",
  "readiness.facts", "readiness.limitations", "readiness.missing_fields",
  "ordering_today.items", "policy_benchmark.explanation",
  "findings", "lanes",
  "actions.now", "actions.next", "actions.monitor",
  "appendix.methodology", "appendix.candidates", "appendix.assumptions", "appendix.glossary", "appendix.warnings",
] as const;

/** Lists the view reads only when the section says it has something to show. */
export const CONDITIONAL_LISTS = [
  { when: "policy_benchmark.available", list: "policy_benchmark.rows" },
  { when: "suppliers.available", list: "suppliers.rows" },
] as const;

function at(root: unknown, path: string): unknown {
  let cur: unknown = root;
  for (const key of path.split(".")) {
    if (typeof cur !== "object" || cur === null || Array.isArray(cur)) return undefined;
    cur = (cur as Record<string, unknown>)[key];
  }
  return cur;
}

const isObject = (v: unknown) => typeof v === "object" && v !== null && !Array.isArray(v);

/** The sections the view needs and this report does not have, in a stable order. Empty when it can be shown. */
export function missingReportSections(report: unknown): string[] {
  if (!isObject(report)) return ["report"];
  const missing: string[] = [];
  for (const path of REQUIRED_OBJECTS) if (!isObject(at(report, path))) missing.push(path);
  for (const path of REQUIRED_LISTS) if (!Array.isArray(at(report, path))) missing.push(path);
  for (const { when, list } of CONDITIONAL_LISTS) if (at(report, when) && !Array.isArray(at(report, list))) missing.push(list);
  return missing;
}

export function reportRenderable(report: unknown): report is DiagnosticReport {
  return missingReportSections(report).length === 0;
}

/** The report's own version label, when it carries one (shown so a person can quote it). */
export function reportVersion(report: unknown): string | null {
  const v = at(report, "version");
  return typeof v === "string" && v.length > 0 && v.length <= 40 ? v : null;
}
