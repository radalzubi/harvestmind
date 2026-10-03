/**
 * Regression for the 2026-10-03 incident: a workspace whose newest diagnostic run was stored in the
 * earlier report format could not open `/start` — the report view threw on a section that format
 * does not have, and the page showed the framework's "This page couldn't load".
 *
 * The earlier-format fixture has the exact structure of such a stored report (keys and types; the
 * values are synthetic). The current-format fixture carries only what the shape check demands, so
 * it also proves the check is sufficient: if the view starts reading a new section without a
 * guard, rendering this fixture fails here instead of in a customer's browser.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { CONDITIONAL_LISTS, REQUIRED_LISTS, REQUIRED_OBJECTS, missingReportSections, reportRenderable } from "../report-shape";
import { DiagnosticReportView } from "../../../components/diagnostic/DiagnosticReport";
import { DiagnosticResult } from "../../../components/diagnostic/DiagnosticResult";

const noop = () => {};

/** A report as the earlier format stored it: no benchmark / replay split, `policy_comparison` instead of `policy_benchmark`. */
function earlierFormat(): Record<string, unknown> {
  return {
    version: "2026.09.2", run_id: "job_synthetic01", company: "Synthetic Co", generated_at: "2026-09-17T19:45:49+00:00", sector: "commercial",
    conclusion: { kind: "retain", headline: "Keep the current ordering rule", body: "No tested alternative was reliably better." },
    executive_summary: {
      findings: [{ id: "f1", headline: "Excess cover", line: "Three products hold more than twelve weeks.", severity: "medium", confidence: "Moderate" }],
      actions: ["Review the three products with excess cover."],
      confidence: { level: "Moderate", statement: "Forty weeks of history." },
    },
    readiness: {
      label: "Usable", level: "usable", confidence: "Moderate", confidence_rule: "rule", statement: "Enough history to compare policies.",
      facts: [{ label: "History", value: "40 weeks" }], limitations: [{ effect: "No promotions file." }], missing_fields: [{ field: "unit_cost" }],
      required_missing: [], history_weeks: 40, products: 12, suppliers: 3, internal_verdict: "READY", unknown_margin_count: 0,
    },
    ordering_today: { internal_label: "reorder_point", summary: "Read from the purchase orders.", items: [{ label: "Review rhythm", value: "weekly", note: null, tag: "Measured" }] },
    policy_comparison: {
      available: true, candidate: "order_up_to", candidate_label: "Order up to a level", current_label: "Your current rule",
      explanation: ["The candidate was not reliably better."], fold_chart: null, internal: { candidate_evidence: {} }, outcome: "retain",
      rows: [{ metric: "Cost", current: "100", candidate: "99", difference: "1%", note: null }],
    },
    findings: [{ id: "f1", severity: "medium", category: "Inventory", confidence: "Moderate", headline: "Excess cover", observation: "o", business_implication: "b",
                 possible_driver: null, driver_tag: "Inferred", recommendation: "r", evidence: [], related: [], confidence_basis: "c", summary_line: null }],
    suppliers: { available: false, note: "No supplier file.", rows: [] },
    lanes: [],
    actions: { now: [{ text: "Review excess cover.", link: null }], next: [], monitor: [] },
    appendix: { assumptions: [], candidates: [], carrying_cost_sensitivity: [], gates: {}, glossary: [], methodology: ["m"], run: { run_id: "job_synthetic01" }, warnings: [] },
  };
}

/** The least a report must carry for the view: exactly the sections the shape check lists. */
function currentFormatMinimal(): Record<string, unknown> {
  return {
    version: "2026.09.4", run_id: "job_synthetic02", company: "Synthetic Co", generated_at: "2026-09-30T08:00:00+00:00", sector: "commercial",
    conclusion: { kind: "retain", headline: "Keep the current ordering rule", body: "No tested alternative was reliably better." },
    executive_summary: {
      benchmark: { label: "Simple policy benchmark", statement: "No tested policy was reliably better." },
      replay: { label: "ZAAD historical decision replay", statement: "Not available on this history.", available: false },
      findings: [], actions: [], confidence: { level: "Moderate", statement: "Forty weeks of history." },
    },
    readiness: { label: "Usable", level: "usable", confidence: "Moderate", confidence_rule: "rule", statement: "s", facts: [], limitations: [], missing_fields: [], required_missing: [], history_weeks: 40, products: 12, suppliers: 3 },
    ordering_today: { summary: "s", items: [] },
    policy_benchmark: { available: false, question: "q", explainer: "e", statement: null, current_label: "Your current rule", candidate: null, candidate_label: "", rows: [], explanation: [], outcome: null, fold_chart: null },
    optimizer_replay: { question: "q", explainer: "e", available: false, status: "unavailable", statement: "Not available on this history." },
    findings: [], suppliers: { available: false, note: "No supplier file." }, lanes: [],
    actions: { now: [], next: [], monitor: [] },
    appendix: { methodology: [], candidates: [], assumptions: [], glossary: [], warnings: [], run: {} },
  };
}

function setPath(root: Record<string, unknown>, path: string, value: unknown): void {
  const keys = path.split(".");
  let cur = root;
  for (const key of keys.slice(0, -1)) cur = cur[key] as Record<string, unknown>;
  if (value === undefined) delete cur[keys[keys.length - 1]]; else cur[keys[keys.length - 1]] = value;
}

test("the incident: the report view throws on a report stored in the earlier format", () => {
  assert.throws(() => renderToStaticMarkup(createElement(DiagnosticReportView, { report: earlierFormat() as never, onDownload: noop })), TypeError);
});

test("an earlier-format report is recognised, with the sections it lacks named", () => {
  const report = earlierFormat();
  assert.equal(reportRenderable(report), false);
  const missing = missingReportSections(report);
  for (const section of ["executive_summary.benchmark", "executive_summary.replay", "policy_benchmark", "optimizer_replay"]) assert.ok(missing.includes(section), section);
});

test("the version label does not decide: a current-layout report with the same label is shown", () => {
  // the label was not changed when the layout was, so both layouts carry it
  const report = currentFormatMinimal();
  report.version = "2026.09.2";
  assert.equal(reportRenderable(report), true);
});

test("the result renders a note and the PDF for an earlier-format report instead of throwing", () => {
  const html = renderToStaticMarkup(createElement(DiagnosticResult, { report: earlierFormat(), onDownload: noop }));
  assert.match(html, /stored in a report layout this page does not show/);
  assert.match(html, /Nothing was lost: the full report of this run is available as a PDF/);
  assert.match(html, /Download the report \(PDF\)/);
  assert.doesNotMatch(html, /Executive summary/);
});

test("the note claims nothing that is false for a sector still built in the other layout", () => {
  // a produce report is built in the other layout today: no version claim, no promise about a new run
  const produce = { ...earlierFormat(), sector: "produce" };
  const html = renderToStaticMarkup(createElement(DiagnosticResult, { report: produce, onDownload: noop }));
  assert.doesNotMatch(html, /version/i);
  assert.doesNotMatch(html, /again/i);
  assert.match(html, /Download the report \(PDF\)/);
});

test("a current-format report is handed to the view and rendered", () => {
  const report = currentFormatMinimal();
  assert.deepEqual(missingReportSections(report), []);
  const html = renderToStaticMarkup(createElement(DiagnosticResult, { report, onDownload: noop }));
  assert.match(html, /Executive summary/);
  assert.match(html, /Keep the current ordering rule/);
  assert.doesNotMatch(html, /layout this page does not show/);
});

test("the check is complete: removing any required section makes the report non-renderable", () => {
  for (const path of [...REQUIRED_OBJECTS, ...REQUIRED_LISTS]) {
    for (const bad of [undefined, null, "text", 7]) {
      const report = currentFormatMinimal();
      setPath(report, path, bad);
      assert.equal(reportRenderable(report), false, `${path} = ${String(bad)}`);
      assert.ok(missingReportSections(report).includes(path), path);
    }
  }
  // a list where an object is required, and an object where a list is required
  const a = currentFormatMinimal(); setPath(a, "optimizer_replay", []); assert.equal(reportRenderable(a), false);
  const b = currentFormatMinimal(); setPath(b, "findings", {}); assert.equal(reportRenderable(b), false);
});

test("the check is sufficient: every report it accepts renders through the real view", () => {
  // nothing but the required sections
  assert.doesNotThrow(() => renderToStaticMarkup(createElement(DiagnosticReportView, { report: currentFormatMinimal() as never, onDownload: noop })));
  // sections that say they have something to show, with their conditional lists present
  const full = currentFormatMinimal();
  setPath(full, "policy_benchmark.available", true);
  setPath(full, "suppliers", { available: true, note: "n", rows: [] });
  setPath(full, "optimizer_replay", { question: "q", explainer: "e", available: true, status: "complete", statement: "s" });
  assert.equal(reportRenderable(full), true);
  assert.doesNotThrow(() => renderToStaticMarkup(createElement(DiagnosticReportView, { report: full as never, onDownload: noop })));
  // …and without them the check refuses, because the view would read them
  for (const { when, list } of CONDITIONAL_LISTS) {
    const report = currentFormatMinimal();
    setPath(report, when, true);
    setPath(report, list, undefined);
    assert.equal(reportRenderable(report), false, list);
  }
});

test("anything that is not a report is a note, never an exception", () => {
  for (const junk of [null, undefined, "report", 42, [], {}, { version: 7 }, { executive_summary: null }]) {
    assert.equal(reportRenderable(junk), false);
    const html = renderToStaticMarkup(createElement(DiagnosticResult, { report: junk, onDownload: noop }));
    assert.match(html, /Download the report \(PDF\)/);
  }
});
