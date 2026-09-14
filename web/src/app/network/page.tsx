"use client";

/**
 * NETWORK — the Digital Network Twin of this operator's supply.
 *
 * Built from the same workspace read that produces the decisions, so a recommendation and the
 * object it affects are always the same object. Nothing illustrative is ever shown here.
 */
import { Suspense, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { Gate } from "@/components/workspace/Gate";
import { EmptyState, ButtonLink } from "@/components/workspace/ui";
import { TwinProvider } from "@/components/network/store";
import { NetworkTwin } from "@/components/network/NetworkTwin";
import { useWorkspaceData } from "@/lib/zaad/workspace-data";
import type { SelectionRef } from "@/lib/network/model";

function NetworkBody() {
  const { network, index } = useWorkspaceData();
  const params = useSearchParams();

  const initial = useMemo(() => {
    const node = params.get("node");
    const edge = params.get("edge");
    const selection: SelectionRef | null = node ? { type: "node", id: node } : edge ? { type: "edge", id: edge } : null;
    return { selection, sku: params.get("sku"), view: params.get("view") === "map" ? ("map" as const) : ("network" as const) };
    // Read once: after this the Twin owns the selection and writes it back to the address bar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!network || !index) return null;

  if (network.nodes.length === 0) {
    return (
      <div style={{ padding: 24 }}>
        <EmptyState title="There is no network to draw yet" actions={<ButtonLink href="/data" role="primary">Go to Data</ButtonLink>}>
          ZAAD has your planning data but no suppliers, sites or lanes it can place in a network.
          Adding your supplier list gives every supplier a name, an origin and a shipping route.
        </EmptyState>
      </div>
    );
  }

  return (
    <TwinProvider model={network} index={index} initial={initial}>
      <NetworkTwin />
    </TwinProvider>
  );
}

export default function NetworkPage() {
  return (
    <Gate>
      <Suspense fallback={null}>
        <NetworkBody />
      </Suspense>
    </Gate>
  );
}
