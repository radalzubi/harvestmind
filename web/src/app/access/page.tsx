"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { KeyRound, LogOut } from "lucide-react";
import { Card, CardBody, CardHead, InfoBanner, PageHeader, Tbtn } from "@/components/ui";
import { BASE_URL, apiFetch, clearApiToken, getApiToken, setApiToken } from "@/lib/api";
import { useToast } from "@/components/Toast";

function AccessInner() {
  const toast = useToast();
  const router = useRouter();
  const params = useSearchParams();
  const [token, setToken] = useState("");
  const [connected, setConnected] = useState(false);
  const [checking, setChecking] = useState(false);
  // A toast is gone in three seconds. A credential that was refused is a blocking failure at the
  // front door of the product, and the person who looked away needs it still on the screen.
  const [refused, setRefused] = useState<string | null>(null);

  useEffect(() => setConnected(Boolean(getApiToken())), []);
  // An access link from the approval email carries the token once; consume it,
  // connect, and strip it from the address bar.
  useEffect(() => {
    const t = params.get("token");
    if (!t) return;
    // The credential leaves the address bar and the history entry before anything else happens, and it is
    // stored only once the API has accepted it (security review 2026-09, SEC-011).
    window.history.replaceState(window.history.state, "", "/access");
    fetch(`${BASE_URL}/me`, { headers: { Authorization: `Bearer ${t.trim()}` } }).then((r) => {
      if (!r.ok) throw new Error("refused");
      setApiToken(t);
      setConnected(true);
      toast.push("Workspace connected");
      router.replace("/start");
    }).catch(() => {
      clearApiToken();
      setRefused("That access link is not valid. It may have been replaced since it was sent.");
      toast.push("That access link is not valid.");
      router.replace("/access");
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const connect = async () => {
    if (!token.trim()) return;
    setChecking(true);
    setRefused(null);
    setApiToken(token);
    try {
      await apiFetch("/intake/status");
      setConnected(true);
      setToken("");
      toast.push("Operator vault connected");
    } catch (error) {
      clearApiToken();
      setConnected(false);
      // `String(error)` is "Error: Invalid API token" — the word "Error:" is the language's, not
      // ours, and it read as part of the sentence.
      const said = error instanceof Error ? error.message : String(error);
      setRefused(/invalid|unauthor|401/i.test(said)
        ? "That token was not accepted. Check it was copied whole, and that it has not been replaced since it was sent to you."
        : `ZAAD could not check that token: ${said}`);
      toast.push("That token was not accepted.");
    } finally {
      setChecking(false);
    }
  };

  const disconnect = () => {
    clearApiToken();
    setConnected(false);
    setRefused(null);
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
        configured Zaad Supply API.
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
          {refused && !connected && (
            <p role="alert" style={{ margin: "10px 0 0", maxWidth: 620, fontSize: 13.5, lineHeight: 1.55, color: "var(--bad)" }}>
              {refused}
            </p>
          )}
        </CardBody>
      </Card>
    </div>
  );
}

export default function AccessPage() {
  return <Suspense fallback={null}><AccessInner /></Suspense>;
}
