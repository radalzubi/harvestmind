"use client";

/**
 * One place that answers "can this page show anything yet?", so every workspace surface
 * handles no-session, not-ready, loading and error the same way and in the same words.
 *
 * Never falls back to demonstration data: inside a workspace, an empty answer is stated,
 * not filled in.
 */
import type { ReactNode } from "react";
import { useSession } from "@/lib/session";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import { Button, ButtonLink, ErrorState, Loading, EmptyState } from "./ui";

export function Gate({ children, loadingLabel = "Reading your workspace…", needsPlan = true }: {
  children: ReactNode;
  loadingLabel?: string;
  /** Only changes how much skeleton is shown while the workspace is read. */
  needsPlan?: boolean;
}) {
  const session = useSession();
  const data = useWorkspaceData();

  if (session.status === "unknown") return <Loading label="Opening your workspace…" cards={2} />;

  if (session.status === "anonymous") {
    return (
      <EmptyState
        title="This workspace is not open on this device"
        actions={<ButtonLink href="/get-started" role="primary">Open your workspace</ButtonLink>}
      >
        ZAAD keeps your access to the browser session you opened it in. Open your workspace again to
        carry on where you left off.
      </EmptyState>
    );
  }

  if (session.status === "error") {
    return (
      <ErrorState
        title="Your workspace could not be reached"
        affects="Nothing was changed, and none of your data was affected."
        whatToDo="Try again in a moment; if it keeps happening, your access may have been rotated."
        detail={session.error ?? undefined}
        actions={<><Button role="primary" onClick={session.refresh}>Try again</Button><ButtonLink href="/access">Enter access again</ButtonLink></>}
      />
    );
  }

  if (data.phase === "not-ready") {
    return (
      <EmptyState
        title="ZAAD needs a little more before it can plan"
        actions={<ButtonLink href="/upload" role="primary">Go to Upload</ButtonLink>}
      >
        {data.notReady}
      </EmptyState>
    );
  }

  if (data.phase === "error") {
    return (
      <ErrorState
        title="The plan could not be computed"
        affects="Your data is untouched and nothing was sent anywhere."
        whatToDo="Run it again. If it fails a second time, the diagnostics below tell support exactly where it stopped."
        detail={data.error ?? undefined}
        actions={<Button role="primary" onClick={data.refresh}>Run it again</Button>}
      />
    );
  }

  if (data.phase !== "ready") return <Loading label={loadingLabel} cards={needsPlan ? 3 : 2} />;

  return <>{children}</>;
}
