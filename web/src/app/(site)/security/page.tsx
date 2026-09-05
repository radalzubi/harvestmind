import type { Metadata } from "next";
import { Reveal, Stagger, Item } from "@/components/site/Reveal";

export const metadata: Metadata = { title: "Security — zaad" };

const POINTS = [
  ["Pseudonymised on arrival", "Item, supplier and customer codes are replaced by keyed hashes the moment a file lands. Names, emails and phone numbers in known contact columns are dropped, not stored. The key is unique to your workspace."],
  ["One vault per workspace", "Each workspace has its own isolated database file. Requests are authenticated per workspace; there is no administrator screen that lists or opens a workspace’s rows."],
  ["The key stays in your tab", "Your workspace key is held in browser session storage only. It is never written to our logs, never emailed, never bundled into the site."],
  ["Nothing leaves for a model", "Uploaded files are parsed locally on our server. The optional smart upload sends only column headers and a handful of sample rows to a language model for mapping, and shows you the mapping before anything loads."],
  ["Encrypted in transit and at rest", "HTTPS everywhere, certificates renewed automatically, storage on an encrypted volume in the EU (Frankfurt)."],
  ["Deletable on request", "Ask and the workspace and its vault are removed. Reports you downloaded are yours; we do not keep a copy of your source files beyond the vault."],
];

export default function SecurityPage() {
  return (
    <>
      <section className="page-hero">
        <div className="wrap">
          <Reveal><p className="eyebrow">Security</p></Reveal>
          <Reveal delay={0.05}><h1 className="display sm">A vault we do not open.</h1></Reveal>
          <Reveal delay={0.1}><p className="lede">The product only works if a distributor can hand over a year of purchasing history without hesitation. Everything below exists to make that reasonable.</p></Reveal>
        </div>
      </section>
      <section className="section">
        <div className="wrap">
          <Stagger className="grid2">
            {POINTS.map(([t, b]) => <Item key={t} className="feature"><h3>{t}</h3><p>{b}</p></Item>)}
          </Stagger>
        </div>
      </section>
      <section className="section">
        <div className="wrap"><Reveal className="note">
          <p><b>Pilot notice.</b> Zaad Supply is in pilot. Workspace keys issued for testing are short by design; workspaces holding real data receive long keys, and we will rotate any key on request. For a data-handling summary or a mutual NDA before you upload, write to <a href="mailto:hello@zaadsupply.com">hello@zaadsupply.com</a>.</p>
        </Reveal></div>
      </section>
    </>
  );
}
