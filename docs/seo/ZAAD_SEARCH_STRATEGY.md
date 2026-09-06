# ZAAD search strategy

Branch `claude/zaad-seo` (stacked on `adaptive/decision-engine`, the branch that carries the
redesigned homepage from PR 22). Optimizer work lives on a separate branch and is not mixed
in here. Nothing in this document claims a ranking. Google decides ranking; this records what
is implemented, indexable, validated and currently observed.

Official identity used everywhere: **ZAAD**, alternate **ZAAD Supply**, domain
**zaadsupply.com**, description **"ZAAD is inventory optimization and supply resilience
software for distributors and importers."**

## 1. Current visibility (observed 2026-09-06)

Searches run through a web search API; results are US-oriented and may differ from a signed-in
Google session, but the picture is consistent.

| Query | What appears now |
|---|---|
| `ZAAD` | Zamyad Co. (Iranian vehicle maker), Zaad Restaurants (New York), Zaad Payment Solutions (LinkedIn), name pages (Zada, Zaid). No result for the product. |
| `"ZAAD supply"` | `www.zaadsupply.com` appears, but the snippet describes a different company: "Zaad Supply was established in 2018 as the international division of the Zaad Supply Group ... equity firms in Oman". Also Zaad Holdings / African Seeds Group (South Africa), Zaad Farms, ZAAD Services (mobile money, Somaliland), Zad Holding (Qatar). |
| `zaadsupply` | `www.zaadsupply.com` with a snippet about entering an address to check regional availability, "Goodness" delivery. |
| `zaadsupply.com` | Same stale snippet as above. |
| `site:zaadsupply.com` | No pages returned from the domain. |
| `"ZAAD" inventory optimization software distributors importers` | No ZAAD result; generic inventory optimization vendors. |

Two facts follow. First, the domain was previously used by an unrelated business (an Omani
"Zaad Supply" group with a regional delivery site), and search engines still hold that entity
for `zaadsupply.com`. The domain was attached to the Vercel project 19 hours before this
audit. Second, the word ZAAD is shared by at least six unrelated organisations. This is an
entity-disambiguation problem before it is a ranking problem: the site has to state, in
every machine-readable way, which ZAAD this is.

## 2. Production status (must be read before anything else)

At the time of the audit, `https://zaadsupply.com/` returned HTTP 200 with the title
**"HarvestMind"**, the description "AI-driven planning for fresh-produce food hubs", the
operator dashboard shell at `/`, no robots.txt (a 404 page was returned for it), no sitemap,
and `www.zaadsupply.com` served the same content with no redirect and no canonical.

Cause: the Vercel project `zaad` is git-integrated with production branch `main`, and `main`
received PR 26 ("Add ZAAD public pages without homepage redesign") at 09:13 local time on
2026-09-06. That commit keeps the HarvestMind dashboard at `/` and adds the public pages under
`/product`, `/about` and so on. The redesigned homepage merged in PR 22 lives on
`adaptive/decision-engine`, which is what this branch is built on.

This branch was not deployed to production and the Vercel production branch was not changed:
production had been redirected by a user action minutes earlier and changing it back is a
product decision. Until either `adaptive/decision-engine` (plus this branch) is promoted to
production or `main` receives the homepage, every item below is verified locally and on the
branch preview, not on the live domain. The live domain currently tells Google the site is
HarvestMind.

Required user decision: choose the production branch. Two clean options:

1. In Vercel, project `zaad`, set the production branch to `adaptive/decision-engine` and merge
   this branch into it; or
2. merge `adaptive/decision-engine` and this branch into `main`.

Either way, `www.zaadsupply.com` must also be attached to the project so the redirect below
takes effect (Vercel serves an unattached alias as a duplicate).

## 3. Technical changes implemented on this branch

- **Identity module** `web/src/lib/seo.ts`: one place for the site URL, name, alternate names,
  description, logo URL, share image, public page list and private route prefixes, plus
  metadata and JSON-LD builders.
- **Homepage title** `ZAAD | Inventory Optimization & Supply Resilience` (absolute, no
  template). **Homepage description**: "ZAAD helps distributors and importers optimize
  inventory, purchasing, sourcing and supply resilience while protecting customer service.
  Backtested on your own history." The visible hero eyebrow now reads "ZAAD · Inventory
  optimization and supply resilience for distributors and importers", the lede names ZAAD,
  the footer blurb uses the identity sentence, and the copyright line reads "ZAAD
  (zaadsupply.com)". Arabic copy carries the same brand line.
- **Site-wide metadata** (`web/src/app/layout.tsx`): `applicationName` ZAAD, title template
  `%s | ZAAD`, `og:site_name` ZAAD, default share image, icon set.
- **Canonicals**: every public page emits a self-referencing absolute canonical on
  `https://zaadsupply.com`; `www.zaadsupply.com` redirects permanently to the apex
  (`next.config.ts`); Vercel already redirects `http` to `https` with a 308.
- **robots.txt** (`web/src/app/robots.ts`): allow `/`, disallow workspace, admin, state and
  API prefixes, sitemap declared.
- **sitemap.xml** (`web/src/app/sitemap.ts`): canonical public pages and the seven resource
  articles only, each with a maintained `lastmod` date; no workspace, query or language
  duplicates.
- **noindex on private surfaces**: `X-Robots-Tag: noindex, nofollow` response header on every
  workspace, admin, state, `/zaad` and `/api` route (`next.config.ts`), which holds even when
  robots.txt is ignored. Authentication on those routes is unchanged.
- **Structured data** (server-rendered JSON-LD in the initial HTML): `WebSite` and
  `Organization` on the homepage, `BreadcrumbList` on every other public page, `Article` plus
  `BreadcrumbList` on each resource article.
- **Favicon system**: `favicon.ico` (16, 32, 48), `icon.svg`, `icon-192.png`, `icon-512.png`,
  `apple-icon.png` (180). The mark is a Z with the seed dot on a dark rounded square, legible
  at 16 px.
- **Organization logo**: `https://zaadsupply.com/brand/zaad-logo-512.png`, square, on white,
  512×512, stable path.
- **Share image**: `https://zaadsupply.com/og/zaad-supply-network.png`, 1200×630, a supply
  network with the wordmark, generated from the site's own palette; `og:image` with
  dimensions and alt text on every public page.
- **Resource library**: seven sourced articles under `/resources/<slug>` with an index page,
  linked from the navigation and footer, each linking to product, sectors and get-started.
- **Automated checks**: `web/scripts/seo-check.mjs` (`npm run seo:check -- --base <url>`).

## 4. Structured data (exact)

WebSite (homepage):

```json
{"@context":"https://schema.org","@type":"WebSite","@id":"https://zaadsupply.com/#website",
 "name":"ZAAD","alternateName":["ZAAD Supply","zaadsupply.com"],"url":"https://zaadsupply.com/",
 "inLanguage":["en","ar"],"publisher":{"@id":"https://zaadsupply.com/#organization"}}
```

Organization (homepage):

```json
{"@context":"https://schema.org","@type":"Organization","@id":"https://zaadsupply.com/#organization",
 "name":"ZAAD","alternateName":["ZAAD Supply","zaadsupply.com"],"url":"https://zaadsupply.com/",
 "description":"ZAAD is inventory optimization and supply resilience software for distributors and importers.",
 "logo":{"@type":"ImageObject","url":"https://zaadsupply.com/brand/zaad-logo-512.png","width":512,"height":512},
 "image":"https://zaadsupply.com/brand/zaad-logo-512.png",
 "contactPoint":[{"@type":"ContactPoint","contactType":"sales","url":"https://zaadsupply.com/contact","availableLanguage":["en","ar"]}],
 "knowsAbout":["inventory optimization","supply chain resilience","purchase order planning","safety stock","multi-echelon inventory optimization","supplier lead time variability"],
 "areaServed":["Jordan","Middle East","United States"]}
```

Deliberately absent: `address`, `telephone`, `email`, `legalName`, `foundingDate`,
`numberOfEmployees`, identifiers, and `sameAs`. None of these has a public, verified value
yet. Add `sameAs` only when an official profile exists (section 8). Breadcrumb and Article
markup follow Google's documented property sets; validation is by the check script (shape)
and should be repeated in Google's Rich Results Test once the branch is live.

## 5. Page metadata

| Path | Title | Description (summary) |
|---|---|---|
| `/` | ZAAD \| Inventory Optimization & Supply Resilience | ZAAD helps distributors and importers optimize inventory, purchasing, sourcing and supply resilience while protecting customer service. |
| `/product` | How ZAAD Works: Inventory Optimization Software for Distributors \| ZAAD | Read the current policy, backtest candidates on your own history, change orders only when the evidence says so. |
| `/sectors` | Sectors: Supply Planning for Produce, Meat and Commercial Importers \| ZAAD | Produce, meat and seafood, commercial goods. |
| `/about` | About ZAAD: Inventory Optimization and Supply Resilience Software \| ZAAD | Who we are, what the product does, what it refuses to promise. |
| `/security` | ZAAD Security Architecture: Isolated Workspaces and Pseudonymised Data \| ZAAD | Pseudonymisation, isolated database per workspace, key-only access. |
| `/contact` | Contact ZAAD \| ZAAD | Talk to ZAAD about inventory optimization and supply resilience. |
| `/resources` | Resources: Inventory Optimization and Supply Resilience for Distributors \| ZAAD | Short, sourced guides. |
| `/resources/<slug>` | article title \| ZAAD | article description |
| `/get-started` | Get Started with ZAAD \| ZAAD | indexable, not in the sitemap (entry flow, not content) |
| `/privacy`, `/terms` | Privacy Policy / Terms of Service \| ZAAD | unique one-line descriptions |

Every description is unique; the check script fails on duplicates.

## 6. Content opportunity

Vocabulary was drawn from the competitor and vendor pages that surface for the target terms
(GAINS, Logility, Kinaxis, Anaplan roundups; "inventory optimization software for
distributors" and "supply chain resilience for importers" pages). Clusters and the pages that
now target them:

| Cluster | Terms | Page |
|---|---|---|
| Inventory optimization | inventory optimization software for distributors, safety stock optimization, reorder point optimization, working capital inventory reduction | `/`, `/product`, articles 1, 2, 6 |
| Supply planning | distributor replenishment optimization, supplier allocation, purchase order optimization, demand and inventory planning | `/product`, article 5 |
| Resilience | supply chain resilience software, disruption inventory planning, alternate supplier planning, route risk planning | `/`, articles 3, 7 |
| Multi-echelon | multi-echelon inventory optimization, central DC and branches | article 4 |
| Industry | FMCG distributor, food distributor, importer inventory optimization, wholesale distribution planning | `/sectors`, article 1 |

Seven articles were written, each with named academic or practitioner sources (Silver, Pyke
and Thomas; Hopp and Spearman; Graves and Willems; Clark and Scarf; Sheffi; Simchi-Levi et
al.; Rockafellar and Uryasev; Kaplan and Meier; Page). No case studies, no customer figures.
Next candidates, only if they can be written to the same standard: "Inventory optimization
for importers" (customs and lead-time tails), "How to measure OTIF versus fill rate", and an
Arabic edition once Arabic URLs exist (section 10).

## 7. Brand search dominance

Signals now consistent across homepage title, H1 context, eyebrow, footer, `og:site_name`,
`applicationName`, WebSite `name`/`alternateName`, Organization `name`/`alternateName`,
logo and favicon: **ZAAD**, with **ZAAD Supply** and **zaadsupply.com** as fallbacks. Google
supports one site name per domain and prefers WebSite structured data, then `og:site_name`,
then the title and headings; all four agree. Because other organisations use the word, the
alternate names are the realistic fallback if Google declines "ZAAD" for this domain.

Not done, by design: no attempt to influence results for the other ZAAD entities, no
fabricated mentions, no paid links.

## 8. External entity signals and authority (user actions)

Each should use the same name, URL, one-sentence description and the 512 px logo. None was
created here; account creation is the user's.

- LinkedIn company page "ZAAD" with website `https://zaadsupply.com/`. Then add its URL to
  `sameAs` in `web/src/lib/seo.ts`.
- GitHub organisation or public repository presence only if the public strategy permits; the
  engineering repository is private today.
- Crunchbase / company databases: only if the company is registered under a name that maps to
  ZAAD; use `legalName` in the Organization schema once known.
- Purdue entrepreneurship or research pages: only if genuinely earned (a programme listing, a
  research collaboration). Ask; do not fabricate.
- Supply-chain publications and podcasts: pitch the LEAN / PROTECT / ALLOCATE / RECOVER
  framework and the "no forecast of savings" stance; earned references only.
- Industry associations in Jordan and the region (chambers, logistics associations): listing
  pages with the canonical URL.

No link purchases, no directory spam, no press fabrication.

## 9. Search Console (requires user access)

1. Open Google Search Console, add a **Domain** property for `zaadsupply.com`, verify by DNS
   TXT record at the registrar (the third-party nameservers shown in Vercel).
2. Submit `https://zaadsupply.com/sitemap.xml` in Sitemaps.
3. URL Inspection on `https://zaadsupply.com/`; confirm the rendered HTML shows the ZAAD title
   and the JSON-LD; request indexing.
4. Request indexing for `/product`, `/sectors`, `/about`, `/security`, `/resources`.
5. After a week, check Pages (indexed versus not), then Enhancements for Breadcrumb and
   structured data errors, and the Site name / favicon appearance in a branded search.
6. Monitor Performance filtered to queries containing `zaad` and to page `/`.
7. Check Core Web Vitals and Page Experience reports for the public pages.
8. Because the domain previously hosted another business, expect stale snippets for a while;
   use URL Inspection to request recrawl of `/` after every material change.

This was not configured by the assistant; it has no Search Console access.

## 10. Language

Arabic is a client-side toggle stored in local storage; there are no separate Arabic URLs, so
no `hreflang` was added (adding it without distinct indexable URLs is incorrect). The server
renders `lang="en"`; the client flips `lang`/`dir` on toggle. If Arabic search matters
commercially, the right architecture is `/ar/...` routes rendered server-side with reciprocal
`hreflang` including `x-default`; that is a routing change beyond this pass.

## 11. Performance

No new client JavaScript was added to public pages (JSON-LD is inline in the server HTML;
the share image and logo are static). The hero's H1, eyebrow and lede are in the initial HTML;
the animation only changes opacity and position after hydration. A Lighthouse pass on the
preview and on production after promotion is still required to record LCP, CLS and INP.

## 12. Monitoring (monthly)

Indexed pages; impressions and average position for `ZAAD`, `ZAAD Supply`, `zaadsupply`,
`zaadsupply.com`, `ZAAD inventory optimization`; non-brand impressions and CTR for the
cluster terms; referring domains; whether Google shows the site name "ZAAD", the favicon and
sitelinks for branded queries; rich-result errors.

## 13. Validation record

- `npx tsc --noEmit`: passed. `next build`: passed; 45 routes including `/robots.txt`,
  `/sitemap.xml`, `/resources` and seven static article routes.
- `npm run seo:check -- --base http://localhost:3111` against `next start`: all checks passed
  (titles, unique descriptions, canonicals, single H1, indexability, `og:site_name`,
  `og:image`, server-rendered `lang`, JSON-LD presence and shape, noindex headers on five
  private routes, robots.txt, sitemap with lastmod, six image assets).
- Headless render of `/`, `/resources` and one article: brand eyebrow and H1 visible in the
  first viewport; resource pages render inside the public site layout.
- Production (`https://zaadsupply.com/`): still serving `main` (see section 2); the checks
  were not run there because they would fail on the title alone.
