"use client";

/**
 * The onboarding state of Home. One next step, never a checklist of seven — the rest of the
 * setup is visible on Data for anyone who wants to see it, but it is not asked for here.
 */
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { useReadiness } from "@/lib/zaad/readiness";
import { ButtonLink, EmptyState, Loading, Section } from "./ui";

export function Onboarding() {
  const { notReady } = useWorkspaceData();
  const readiness = useReadiness();

  if (readiness.loading) return <Loading label="Checking what you have already added…" cards={1} />;

  const step = readiness.nextStep;
  const done = readiness.sources.filter((s) => s.state !== "missing");

  return (
    <>
      <EmptyState
        title={step ? step.title : "Almost ready"}
        actions={<ButtonLink href="/data" role="primary" size="lg">Add this data</ButtonLink>}
      >
        {step ? step.detail : notReady ?? "ZAAD has what it needs and will plan on your next visit."}
      </EmptyState>

      {done.length > 0 && (
        <Section title="Already added">
          <div className="facts">
            {done.map((s) => (
              <div key={s.table}>
                <dt>{s.name}</dt>
                <dd>{s.rows.toLocaleString("en-US")} rows</dd>
              </div>
            ))}
          </div>
        </Section>
      )}

      <Section title="What happens next">
        <div className="notice">
          Once the required data is in, ZAAD fits your demand and your suppliers&rsquo; reliability from your own
          history, compares your current buying plan against every alternative it can build, and tells you what to
          change. It never places an order.
        </div>
      </Section>
    </>
  );
}
