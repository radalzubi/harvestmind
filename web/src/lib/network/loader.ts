"use client";

import { useCallback, useEffect, useState } from "react";
import { getApiToken, getSector } from "@/lib/api";
import { loadWorkspaceNetwork } from "./adapters/workspace";
import { ILLUSTRATIVE_NETWORK } from "./fixtures";
import type { NetworkModel } from "./model";

export type NetworkSource = "workspace" | "illustrative";

export interface NetworkLoad {
  model: NetworkModel;
  source: NetworkSource;
  /** Why the workspace could not be used, when it could not. */
  workspaceError: string | null;
  loading: boolean;
  setSource: (s: NetworkSource) => void;
  reload: () => void;
}

/**
 * Picks the operator's own network when a workspace key is present and the
 * commercial endpoints answer; otherwise the labelled illustrative fixture.
 * The fixture is the default until the workspace load has finished, so the
 * page shell and the graph appear at once.
 */
export function useNetworkModel(): NetworkLoad {
  const [workspace, setWorkspace] = useState<NetworkModel | null>(null);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [source, setSourceState] = useState<NetworkSource>("illustrative");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!getApiToken()) { setWorkspaceError("No workspace key: showing the illustrative network."); return; }
    if (getSector() === "produce") { setWorkspaceError("The perishable workspace has no lane-tagged supplier upload yet; showing the illustrative network."); return; }
    let alive = true;
    setLoading(true);
    loadWorkspaceNetwork()
      .then((m) => { if (!alive) return; setWorkspace(m); setWorkspaceError(null); setSourceState("workspace"); })
      .catch((e) => { if (!alive) return; setWorkspace(null); setWorkspaceError(e instanceof Error ? e.message : String(e)); setSourceState("illustrative"); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [tick]);

  const setSource = useCallback((s: NetworkSource) => { if (s === "illustrative" || workspace) setSourceState(s); }, [workspace]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  const model = source === "workspace" && workspace ? workspace : ILLUSTRATIVE_NETWORK;
  return { model, source: model.provenance, workspaceError, loading, setSource, reload };
}
