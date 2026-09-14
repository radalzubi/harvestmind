"use client";

/**
 * Session, workspace identity and capabilities — one seam for the whole product.
 *
 * Today a pilot access code resolves to exactly one workspace, and the adapter
 * below is the only code that knows that. Pages ask this provider who the actor
 * is, which workspace they are in and what they may do; they never read the
 * access code. When accounts, organisations, SSO or roles arrive, only
 * `pilotAdapter` is replaced — Home, Decisions, Network and Data do not change.
 *
 * Deliberately not built here: roles, teams, billing, invitations management,
 * permission storage. `capabilities` is a flat set the adapter grants; that is
 * enough for approval buttons to be permission-aware later without RBAC now.
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiFetch, clearApiToken, getApiToken, getMe, setApiToken, setSector, type Me, type Sector } from "@/lib/api";

export type SessionStatus = "unknown" | "anonymous" | "authenticated" | "error";

/** What the signed-in person may do. The pilot grants all four; later adapters will not. */
export type Capability = "view" | "review" | "approve" | "manageData";

export interface Actor {
  id: string;
  /** Display name for the person. The pilot has no per-person identity, so this is the workspace's. */
  name: string;
}

export interface Workspace {
  id: string;
  name: string;
  /** The organisation the workspace belongs to. One per workspace in the pilot. */
  organisation: string;
  region: string;
  sector: Sector;
  /** Which upload family this workspace uses. */
  family: "commercial" | "produce";
  createdAt: string;
  uploads: number;
}

export interface Session {
  status: SessionStatus;
  actor: Actor | null;
  workspace: Workspace | null;
  capabilities: Set<Capability>;
  /** Why authentication failed, in words a person can act on. */
  error: string | null;
  can(capability: Capability): boolean;
  /** Exchange an access code for a session. Resolves to the workspace or throws. */
  signIn(code: string): Promise<Workspace>;
  signOut(): void;
  refresh(): void;
}

const PILOT_CAPABILITIES: Capability[] = ["view", "review", "approve", "manageData"];

function workspaceFrom(me: Me): Workspace {
  const name = me.display_name || me.name || me.operator_id;
  return {
    id: me.operator_id,
    name,
    organisation: name,
    region: (me.region || "").toUpperCase(),
    sector: me.sector,
    family: me.sector === "commercial" ? "commercial" : "produce",
    createdAt: me.created_at,
    uploads: me.upload_count,
  };
}

/** The pilot adapter: an access code in session storage, resolved through `/me`. */
const pilotAdapter = {
  hasCredential: () => Boolean(getApiToken()),
  resolve: async (): Promise<Workspace> => workspaceFrom(await getMe()),
  store: (code: string) => setApiToken(code),
  clear: () => clearApiToken(),
};

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<SessionStatus>("unknown");
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let alive = true;
    // The credential lives in session storage, so the answer is only knowable on the
    // client; deferring a tick keeps the first paint identical on server and client.
    Promise.resolve().then(() => {
      if (!alive) return;
      if (!pilotAdapter.hasCredential()) { setStatus("anonymous"); setWorkspace(null); setError(null); return; }
      pilotAdapter.resolve()
        .then((w) => { if (!alive) return; setWorkspace(w); setSector(w.sector); setStatus("authenticated"); setError(null); })
        .catch((e) => {
          if (!alive) return;
          setWorkspace(null);
          setStatus("error");
          setError(e instanceof Error ? e.message : "The workspace could not be reached.");
        });
    });
    return () => { alive = false; };
  }, [tick]);

  useEffect(() => {
    const on = () => setTick((t) => t + 1);
    window.addEventListener("harvestmind-auth-change", on);
    return () => window.removeEventListener("harvestmind-auth-change", on);
  }, []);

  const signIn = useCallback(async (code: string) => {
    pilotAdapter.store(code);
    try {
      const w = await pilotAdapter.resolve();
      setWorkspace(w);
      setSector(w.sector);
      setStatus("authenticated");
      setError(null);
      return w;
    } catch (e) {
      pilotAdapter.clear();
      setWorkspace(null);
      setStatus("anonymous");
      throw e;
    }
  }, []);

  const signOut = useCallback(() => {
    pilotAdapter.clear();
    setWorkspace(null);
    setStatus("anonymous");
    setError(null);
  }, []);

  const value = useMemo<Session>(() => {
    const capabilities = new Set<Capability>(status === "authenticated" ? PILOT_CAPABILITIES : []);
    return {
      status, workspace, error, capabilities,
      actor: workspace ? { id: workspace.id, name: workspace.name } : null,
      can: (c: Capability) => capabilities.has(c),
      signIn, signOut,
      refresh: () => setTick((t) => t + 1),
    };
  }, [status, workspace, error, signIn, signOut]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const value = useContext(SessionContext);
  if (!value) throw new Error("useSession must be used inside <SessionProvider>");
  return value;
}

/** Workspace-scoped API call. Present so pages never assemble auth headers themselves. */
export function workspaceFetch<T>(path: string, init?: RequestInit): Promise<T> {
  return apiFetch<T>(path, init);
}
