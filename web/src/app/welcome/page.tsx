"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getApiToken, getMe, setSector, type Me } from "@/lib/api";

type Profile = Me & { display_name?: string; logo_url?: string | null };

export default function WelcomePage() {
  const [me, setMe] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!getApiToken()) { setError("no-key"); return; }
    getMe().then((m) => { setMe(m as Profile); setSector(m.sector); }).catch((e) => setError(e.message));
  }, []);

  if (error === "no-key") {
    return <main className="welcome"><p>No key entered. <Link href="/">Back to the start</Link></p></main>;
  }
  if (error) return <main className="welcome"><p>That key did not open a workspace. <Link href="/">Try again</Link></p></main>;
  if (!me) return <main className="welcome" />;
  const name = me.display_name || me.name;
  return (
    <main className="welcome">
      {me.logo_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img className="welcome-logo" src={me.logo_url} alt={`${name} logo`} />
      ) : (
        <div className="welcome-mark">{name.slice(0, 1)}</div>
      )}
      <h1>Welcome, {name}</h1>
      <p className="welcome-sub">
        Your private {me.sector === "commercial" ? "commercial goods" : "fresh produce"} workspace is ready. Everything you upload stays in a vault only this key opens.
      </p>
      <Link className="land-cta" href="/start">Open the workspace</Link>
    </main>
  );
}
