import type { Metadata } from "next";
import { Reveal } from "@/components/site/Reveal";

export const metadata: Metadata = { title: "Privacy — zaad" };

export default function PrivacyPage() {
  return (
    <section className="page-hero">
      <div className="wrap doc">
        <Reveal><p className="eyebrow">Privacy</p><h1 className="h1">Privacy notice</h1><p className="muted">Last updated 5 September 2026 · pilot</p></Reveal>
        <Reveal delay={0.05} className="prose">
          <h3>What we collect</h3>
          <p>Files you upload to your workspace (purchasing, sales, receipts, stock and supplier records), the pseudonymised tables derived from them, diagnostic reports generated for your workspace, and standard server logs (request path, status, timestamp, coarse IP) kept for security.</p>
          <h3>What we do not collect</h3>
          <p>We do not ask for an account, password or email to open a workspace. Contact columns in uploaded files (names, emails, phone numbers) are dropped on arrival. Workspace keys are not logged.</p>
          <h3>How your data is used</h3>
          <p>Only to produce the diagnostic and plans inside your workspace. We do not pool workspaces, sell data, or use your files to train models.</p>
          <h3>Where it lives</h3>
          <p>On an encrypted volume in Frankfurt, Germany, in a database isolated per workspace. The website is served from a global edge network and holds no workspace data.</p>
          <h3>Third parties</h3>
          <p>Hosting (Fly.io for the service, Vercel for the website). Optional smart upload sends column headers and a few sample rows to a language-model provider for mapping, only when you use it, and shows the mapping before anything loads.</p>
          <h3>Deletion</h3>
          <p>Email <a href="mailto:hello@zaadsupply.com">hello@zaadsupply.com</a> from the address you use with us and we remove the workspace and its vault.</p>
        </Reveal>
      </div>
    </section>
  );
}
