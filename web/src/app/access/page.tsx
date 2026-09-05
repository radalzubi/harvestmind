"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { KeyRound, LogOut } from "lucide-react";
import { Card, CardBody, CardHead, InfoBanner, PageHeader, Tbtn } from "@/components/ui";
import { apiFetch, clearApiToken, getApiToken, setApiToken } from "@/lib/api";
import { useToast } from "@/components/Toast";

function AccessInner() {
  const toast = useToast();
  const router = useRouter();
  const params = useSearchParams();
  const [token, setToken] = useState("");
  const [connected, setConnected] = useState(false);
  const [checking, setChecking] = useState(false);

  useEffect(() => setConnected(Boolean(getApiToken())), []);
  // An access link from the approval email carries the token once; consume it,
  // connect, and strip it from the address bar.
  useEffect(() => {
    const t = params.get("token");
    if (!t) return;
    setApiToken(t);
    apiFetch("/me").then(() => {
      setConnected(true);
      toast.push("Workspace connected");
      router.replace("/start");
    }).catch(() => { clearApiToken(); toast.push("That access link is not valid"); router.replace("/access"); });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const connect = async () => {
    if (!token.trim()) return;
    setChecking(true);
    setApiToken(token);
    try {
      await apiFetch("/intake/status");
      setConnected(true);
      setToken("");
      toast.push("Operator vault connected");
    } catch (error) {
      clearApiToken();
      setConnected(false);
      toast.push(`Connection failed: ${String(error)}`);
    } finally {
      setChecking(false);
    }
  };

  const disconnect = () => {
    clearApiToken();
    setConnected(false);
    toast.push("Operator vault disconnected", "info");
  };

  return (
    <div className="page">
      <PageHeader
        title="Pilot access"
        sub="Connect this browser session to one isolated operator vault"
      />
      <InfoBanner kind="info" title="Session-only credential">
        The token stays in this browser tab session. It is not persisted to
        local storage, bundled into the app, or sent anywhere except the
        configured HarvestMind API.
      </InfoBanner>
      <Card style={{ marginTop: 16 }}>
        <CardHead
          title={connected ? "Operator vault connected" : "Enter operator token"}
          sub={connected ? "API requests are authenticated for this session." : "Get this one-time token from the pilot administrator."}
        />
        <CardBody>
          {connected ? (
            <Tbtn icon={<LogOut size={13} />} onClick={disconnect}>Disconnect</Tbtn>
          ) : (
            <div style={{ display: "flex", gap: 8, maxWidth: 620 }}>
              <input
                type="password"
                autoComplete="off"
                value={token}
                onChange={(event) => setToken(event.target.value)}
                onKeyDown={(event) => { if (event.key === "Enter") void connect(); }}
                placeholder="Paste operator API token"
                aria-label="Operator API token"
                style={{ flex: 1, border: "1px solid var(--line)", borderRadius: 6, padding: "9px 11px" }}
              />
              <Tbtn variant="primary" icon={<KeyRound size={13} />} pending={checking} onClick={connect}>
                {checking ? "Checking…" : "Connect"}
              </Tbtn>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

export default function AccessPage() {
  return <Suspense fallback={null}><AccessInner /></Suspense>;
}
