import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/site/JsonLd";
import { CONTENT } from "@/lib/resources-content";
import { ARTICLES, article } from "@/lib/resources";
import { articleJsonLd, breadcrumbJsonLd, pageMetadata } from "@/lib/seo";

export const dynamicParams = false;

export function generateStaticParams() {
  return ARTICLES.map((a) => ({ slug: a.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const a = article(slug);
  if (!a) return {};
  return pageMetadata({ title: a.title, description: a.description, path: `/resources/${a.slug}`, type: "article" });
}

export default async function ResourceArticle({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const a = article(slug);
  const body = CONTENT[slug];
  if (!a || !body) notFound();
  const related = a.related.map(article).filter((x): x is NonNullable<typeof x> => Boolean(x));
  const path = `/resources/${a.slug}`;
  return (
    <>
      <JsonLd data={[
        articleJsonLd({ title: a.title, description: a.description, path, published: a.published, modified: a.modified }),
        breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Resources", path: "/resources" }, { name: a.heading, path }]),
      ]} />
      <article className="section article">
        <div className="wrap article-wrap">
          <nav className="crumbs" aria-label="Breadcrumb">
            <Link href="/">Home</Link><span>/</span><Link href="/resources">Resources</Link>
          </nav>
          <h1 className="display sm">{a.heading}</h1>
          <p className="lede">{a.description}</p>
          <p className="article-meta">{a.readingMinutes} min read · published {a.published}{a.modified !== a.published ? ` · updated ${a.modified}` : ""} · by ZAAD</p>
          <div className="article-body">{body.body}</div>
          <section className="article-sources">
            <h2>Sources</h2>
            <ol>
              {body.sources.map((s) => (
                <li key={s.href}><a href={s.href} rel="noopener noreferrer" target="_blank">{s.label}</a>{s.note ? ` — ${s.note}` : ""}</li>
              ))}
            </ol>
          </section>
          <section className="article-next">
            <h2>Related</h2>
            <ul>
              {related.map((r) => <li key={r.slug}><Link href={`/resources/${r.slug}`}>{r.heading}</Link></li>)}
            </ul>
            <p>
              ZAAD applies these ideas to your own purchase orders, receipts and stock counts. <Link href="/product">See how it works</Link>,
              browse the <Link href="/sectors">sectors it serves</Link>, or <Link href="/get-started">open a workspace</Link>.
            </p>
          </section>
        </div>
      </article>
    </>
  );
}
