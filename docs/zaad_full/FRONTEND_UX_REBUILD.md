# ZAAD frontend rebuild — UX audit and record

Branch `feat/zaad-frontend-network-twin`, from `main` `dd2e57f`. Product UX only: the optimizer,
its mathematics, its economics and the canonical API semantics are untouched. The one backend
change is an additive read-only directory projection (§ *Backend*).

## 1. The audit (before)

### Routes

| route | group | what it is | verdict |
|---|---|---|---|
| `/` `(site)` | public | landing | **rebuild** — positioned as an inventory optimizer, not the decision layer |
| `/product` `/how-it-works` `/sectors` `/security` `/about` `/contact` `/resources` `/privacy` `/terms` | public | marketing | keep; nav trimmed |
| `/get-started` | public | access request + key entry | keep, restructured into the funnel |
| `/start` | workspace | onboarding checklist + run diagnostic | **fold into HOME** |
| `/overview` | workspace | produce diagnostic summary | secondary (produce) |
| `/upload` | workspace | CSV upload per table | **fold into DATA** |
| `/data-quality` | workspace | quality score + pool consent | **fold into DATA** |
| `/zaad/network` | workspace | raw canonical JSON planner | **move to `/advanced/planner`** |
| `/zaad` | workspace | redirect | keep |
| `/zaad/legacy` | workspace | superseded engine viewer | keep, unlinked |
| `/fmcg` | workspace | purchase plan | **fold into DECISIONS** |
| `/state` | workspace | state and lanes | **fold into NETWORK + HOME** |
| `/reports` | workspace | PDF export | **contextual export**, not a destination |
| `/inventory` `/atp` `/traceability` `/partners` `/forecasts` `/supply-risk` `/recommendations` `/backtest` `/loss` `/performance` | workspace | produce/meat diagnostics | keep at their URLs, secondary |
| `/access` | workspace | token entry | keep, re-languaged as workspace access |
| `/admin` `/welcome` `/upload/confirm` | workspace | supporting | keep |

### Navigation (before)

Commercial sidebar: **Start · Upload · Data quality · Zaad workspace · Purchase plan · State and lanes · Reports** — seven destinations, four of which are stages of one task.
Produce sidebar: thirteen destinations in five groups.
Topbar: page title + a permanent **Explain this page** button — the only action in the bar, louder than anything on the page.
Public nav: Product · How it works · Sectors · About + "Open workspace".

### Problems found

1. **Module-based navigation.** Start / Upload / Data quality / Purchase plan / State are five stops in what an operator experiences as two jobs: *is my data ready* and *what should I change*.
2. **The primary decision surface is an engineering console.** `/zaad/network` asks the operator to click a fixture button or paste canonical v2 JSON into a textarea, then renders eight `<details>` blocks of raw JSON. There is no plain-language recommendation anywhere on it.
3. **Two competing primary buttons** on that page ("Compare plans" and "Save authenticated shadow decision") with no indication which one an operator wants.
4. **`Explain this page` is the loudest control in the product** and appears on every page regardless of whether there is anything to explain.
5. **Jargon in primary copy**: "incumbent", "shadow decision", "canonical v2 JSON", "information hash", "ATP", "evidence label", "selected policy", "PENDING_REVIEW".
6. **Dead paths in production.** `/fmcg` defaults to `mode=canonical` (fine) but offers four legacy modes that return **410** when `ZAAD_LEGACY_PLANNERS=0`, which is production. `/zaad/legacy` is entirely 410 in production.
7. **No route from a decision to the thing it affects.** Nothing links a recommended purchase to its supplier, lane or location.
8. **No network surface at all.** `/state` renders lane outlooks as a list of sentences; there is no spatial or relational view.
9. **Approval is unreachable without JSON.** The review flow exists only after "Save authenticated shadow decision" on the raw planner.
10. **Data readiness is split** between `/start` (checklist), `/upload` (per-table), `/data-quality` (score) and `/fmcg` (`ready_to_plan`), each with its own vocabulary.
11. **`getApiToken()` is read directly in 11 page components**, so replacing the pilot key later means touching every page.
12. **Sector fork duplicates the shell.** Two hard-coded sidebars diverge in naming for the same concepts ("Overview" vs "Start").
13. **Landing claims and product are out of step**: the page sells inventory optimization; the product decides purchases, sourcing, positioning, allocation and open-PO amendments.
14. **Mobile workspace is unusable**: `.app` is a fixed `248px 1fr` grid with no breakpoint; the rail does not collapse.
15. **No empty/loading discipline**: `/fmcg` shows nothing until a plan is built; `/state` shows a bare spinner line.

### Click counts (before)

Measured from a loaded workspace with a valid key, counting clicks, not keystrokes.

| workflow | before |
|---|---|
| A. see what needs attention | **not possible** — no such surface |
| B. open the highest-priority decision | not possible |
| C. understand why | 4 (`/zaad/network` → fixture → Compare plans → expand JSON) and the answer is JSON |
| D. approve/reject a decision | 6 (load state → Save shadow → type reason → Approve) |
| E. check supplier/lane risk | 2 (`/state` → read) with no link to anything |
| F. upload/replace data | 2 (`/upload` → table) |
| G. check data quality | 2 (`/data-quality`) |
| H. export | 2 (`/reports` → open) |
| I. analyst gets model detail | 4 and only as raw JSON |
| J. decision → affected supplier/lane | **not possible** |

## 2. The rebuild (after)

### Navigation

| | before | after |
|---|---|---|
| workspace (commercial) | Start · Upload · Data quality · Zaad workspace · Purchase plan · State and lanes · Reports | **Home · Decisions · Network · Data** |
| workspace (produce) | thirteen items in five groups | the same four, with the diagnostic pages as a secondary group |
| topbar | page title + a permanent "Explain this page" button | workspace identity · search (⌘K) · low-emphasis Help · account menu |
| public | Product · How it works · Sectors · About + "Open workspace" | Product · How it works · Who it's for · Security + "Get a diagnostic" (primary), "Get a company quote" (secondary), "Open your workspace" (text) |
| phone | none — the rail was a fixed 248px column at every width | the same four as a bottom tab bar |

### Routes consolidated

`/start` → `/home` · `/upload` → `/data` · `/data-quality` → `/data` · `/fmcg` → `/decisions` ·
`/state` → `/network` · `/reports` → `/decisions` · `/zaad/network` → `/decisions`.

Kept and reachable, off primary navigation: `/reports` (the diagnostic PDF), `/start` (the produce
diagnostic runner), `/upload/confirm` (the column-mapping confirmation), `/advanced/planner` (the
raw canonical console, moved intact from `/zaad/network`), `/access`, `/admin`, `/welcome` and the
ten produce diagnostic pages. Nothing was deleted; every old URL still resolves.

### Click counts

Measured on a loaded workspace with a computed plan.

| workflow | before | after |
|---|---|---|
| A. see what needs attention | not possible | **0** — it is the first line of Home |
| B. open the highest-priority decision | not possible | **1** |
| C. understand why | 4, and the answer was JSON | **1** (open) — "Why ZAAD recommends this" is open by default |
| C2. reach the evidence behind it | not possible | **1** more |
| C3. reach the raw report | 4 | **1** more |
| D. approve or reject | 6, via the raw planner | **2** (reason chip → Approve), no page change |
| E. check supplier or lane risk | 2, with no link to anything | **1** from Home or Decisions |
| F. upload or replace data | 2 | **1** from primary nav |
| G. see a data problem | 2 | **0–1** — Data leads with it, and Home surfaces it when it blocks something |
| H. export | 2 | contextual, no dedicated destination |
| I. analyst gets model detail | 4, raw JSON only | **2** (decision → Technical details) |
| J. decision → affected supplier/lane | not possible | **1** ("View in network") |
| K. network object → its decision | not possible | **1** (panel → decision) |

### Buttons

Removed: "Compare plans" and "Save authenticated shadow decision" as competing primaries (one
run action now); the permanent "Explain this page" CTA (contextual Help, tertiary); four legacy
planning modes on the purchase plan that answer 410 in production; per-page bespoke button styling.

Merged: Upload's six per-table buttons and Data quality's actions into one row per source; "Enter
key" and "Get started" into one entry point; the three PDF export buttons into one contextual action.

One system replaces two: `primary · secondary · tertiary · danger · icon`, four sizes, one focus
ring, one disabled treatment. `.btn` (public, pill) and `.tbtn` (legacy pages) now derive from the
same tokens, so a control behaves the same everywhere.

### Network Twin

Reused from PR #39: the normalised visual model (`model.ts`), the deterministic layered layout
(`layout.ts`), the dependency index and search (`graph.ts`), the attention layer and its
plain-language `describe()` (`attention.ts`), customer grouping (`groups.ts`), the geography
catalog (`geo.ts`), the React Flow node and edge rendering, and the vendored MapLibre worker with
its build-time check.

Rejected, with reasons:

* **the `/fmcg` adapter** — it read `/fmcg/state` and `/fmcg/plan?mode=safe`; those legacy planning
  modes answer **410** in production (`ZAAD_LEGACY_PLANNERS=0`). Replaced by `adapters/canonical.ts`.
* **the scenario engine** — the released system has no scenario endpoint. An authenticated
  workspace must not show a made-up optimizer result (§23).
* **the globe** — no usability advantage at this data's precision.
* **deck.gl (three packages)** — MapLibre's own symbol layer does the label collision that PR #39
  hand-rolled in ~80 lines of screen-space box tests, and does it better.
* **the illustrative fixture** — there is now no importable demonstration model anywhere in
  `src/lib`, so an authenticated surface cannot fall back to one even by mistake. The public site
  has its own, clearly labelled, hand-drawn SVG.

Live entities: suppliers (name, declared origin, route tag, fitted fill and lead with sample size
and provenance, open orders, shared risk group), sites (kind, stock on hand and its value, service
target and projected service, per-product protection stance), entry ports from the declared route
tag, supplier → port → site lanes, transfer lanes between sites, customers and the service they are
owed, and every recommendation attached to the object it affects.

Unavailable, and stated as such: shipment positions (not tracked anywhere in the released system —
nothing is drawn in motion); site coordinates (the contract carries none, so a multi-site workspace
is not placed on the map and the map says how many items that is); customer locations; port
congestion and dwell; inland transit time and cost.

Precision: a facility placed from its declared country is drawn hollow and labelled "Placed by
country". A lane path is the published shipping route for the operator's declared route tag, and
the map says so rather than implying a tracked vessel.

### How planning actually works now

The measured cost of a solve changed the design. Reading a 150-product workspace takes ~4 s; a
bounded eight-product network plan measured **~108 s**. A page load cannot own that.

So the product does two things at two speeds. The workspace read happens on entry and Network and
Data are usable immediately. Planning runs on the released asynchronous jobs path
(`POST /api/zaad/network/jobs`), which reports QUEUED and RUNNING honestly, survives a reload, and
keeps the last completed plan — so Home opens on the last plan with the date of the data it used,
and running a new one is a deliberate act with visible progress.

A run may cover a selection of products, and when it does the interface says so in the same words
everywhere, with the rule that chose them: every product with a declared order change first, then
the products with the most units still on order. Products carrying declared amendment rights always
travel with the run — leaving one out orphans its declared options and the server rightly refuses.

### Progressive disclosure

Level 1 is the page: an imperative headline, the object, one sentence. Level 2 is two disclosures —
"Why ZAAD recommends this" (open by default, and carrying the do-nothing outcome) and "Evidence"
(named facts with the optimizer's own provenance label). Level 3 is "Technical details": the raw
report fragment. An analyst reaches the raw model in one interaction from any decision; a
non-technical reader never sees it.

### Jargon removed from operator copy

incumbent → "your current plan" · ATP → "available for customers" · recourse → "future adjustment" ·
commitment intervention → "open PO change" · PENDING_REVIEW → "changes to review" ·
RETAIN_INCUMBENT → "no change recommended" · shadow decision → "your decision" ·
information hash → shown only under technical details · staging table names → only under Advanced ·
"canonical v2 JSON" → gone from every operator surface.

A test asserts this: no decision's headline, summary, reasons, effects or do-nothing text may
contain the engine's vocabulary.

### Approval

The released ledger records one human decision per information set, so that is what the interface
offers and says: reason chips plus an optional note, "Approve recommendation" (never "send order"),
and a line stating that recording a decision covers the recommendations in this plan and that ZAAD
does not contact the supplier. Capabilities are resolved through the session abstraction, so the
control can be permissioned later without touching the page.

### Landing page

Positioned as **the decision layer for imported supply**. The narrative is: what ZAAD is → the nine
things it decides → the product itself → a lane slipping → the operating loop → how it earns trust →
who it is for → what it costs → one way in.

Research that shaped it, with sources: NN/g's B2B findings (missing pricing is the most
user-hostile trait of B2B sites; a visitor must be able to judge fit without registering) produced
the "What it costs" section, which states plainly that ZAAD is priced per company after the
diagnostic rather than staying silent. Baymard's checkout research (perceived effort tracks the
number of fields a person must consider more than the number of steps) produced a five-field quote
with the rest behind a disclosure. The GOV.UK question-page pattern produced explicit labels,
"(optional)" on optional fields and no asterisks on required ones. Stripe and Linear were inspected
for above-the-fold structure: both lead with a declarative "what this is, for whom" line and a
single primary action, and Linear shows the actual product rather than an abstract visual — which,
with NN/g's judging-fit finding, is why the Twin appears on the page instead of being described.

CTA wording is identical everywhere it appears ("Get a diagnostic", "Get a company quote"), and the
commercial CTAs are 46–52px with full-width behaviour on a phone.

### Performance

MapLibre (1,033 KB) loads only when the MAP view is first shown; React Flow (~149 KB across two
chunks) only on NETWORK. Neither is in the landing page's critical path — the landing Twin is
hand-drawn SVG for exactly that reason. The root bundle is 437 KB. Production build compiles in
~7 s.

### Accessibility

One focus ring on every control, never hidden under sticky chrome. Skip link to content. The Twin
is keyboard-operable: tab through nodes and lanes, Enter to select, Escape to clear, and search
reachable without a pointer. Icon-only controls carry accessible names. Status is never encoded by
colour alone — every state carries a word and a shape. `prefers-reduced-motion` removes the panel
slide, the node transitions, the skeleton shimmer and the twin preview's pulse. Targets are 44px or
larger on the commercial CTAs and the mobile tab bar.

### Screens inspected in a browser

Landing (desktop and 375px), the decision-verb section, the Twin preview with selection, the quote
page, Home with a plan, Home with no plan, Home onboarding, Decisions, the decision detail, Network
(graph, live data), Network (map, live tiles), the intelligence panel on a supplier, Data ready,
the run-failed state, and the mobile Network.

### Defects found and fixed during QA

1. Nested `<a>` in the workspace rail brand — a hydration failure on every workspace page.
2. The Twin used a fixed three-row grid while its attention strip is conditional; with the strip
   absent the canvas collapsed to zero height. Hit desktop too, whenever nothing needed attention.
3. A supplier delivering 98% of ordered quantity was flagged as a problem.
4. A change that avoids no invoice printed "0" among real figures instead of describing the invoice.
5. Raw engine warnings naming staging tables and migration numbers reached the operator's data strip.
6. "Nothing needs changing" was shown beside a 23-point service shortfall ZAAD could not improve;
   it now says it cannot improve it.
7. A scoped run orphaned declared amendment rights and the server refused it.
8. The Data page showed a row total belonging to a different upload family.
9. A lead-time sample size was quoted as if it measured delivery reliability.
10. Fractional units in prose ("31,866.25 units"); a duplicated service sentence; a singular/plural
    slip ("6 open commitment"); an attention card showing "Critical" and "Stable" together.
11. The hero's two CTAs had different widths on a phone (the magnetic wrapper was inline-block).
12. The verb grid left a hole at desktop widths (nine items in four columns).

### Known limitations

* Planning is minutes long; a full 150-product run is unlikely to finish inside the job timeout.
  The interface exposes the selection and says what it covered, but ZAAD cannot yet plan a large
  catalogue in one run. That is an engine capability boundary, not a frontend one.
* `/api/zaad/network/jobs` refuses more than 200 products, 400 sources or 200 services.
* Sites have no coordinates in the canonical contract, so a multi-site workspace is not placed on
  the map. A supplier without a declared origin or route is not placed either.
* One planner slot per API process: a long run makes a concurrent interactive plan answer 429.
* The produce diagnostic pages keep their original design; only their place in the navigation changed.
* `web/` was not audited page by page beyond the routes listed here.
* The landing Twin is a hand-drawn illustration, not the real component.

### Frontend debt

The ten produce diagnostic pages still use the old page furniture. `/advanced/planner` is unchanged
from the raw console. The SKU filter in the Twin is a native select and becomes unwieldy past a few
hundred products. There is no analytics implementation — the event names below are documented for
whenever one is added.

### Event model (documented, not implemented)

`landing_primary_cta` · `landing_quote_cta` · `quote_submitted` · `diagnostic_started` ·
`workspace_opened` · `data_source_added` · `data_ready` · `plan_run_started` · `plan_run_finished` ·
`decision_opened` · `decision_evidence_opened` · `decision_technical_opened` · `decision_reviewed` ·
`network_opened` · `network_object_selected` · `decision_to_network`.

## 3. Heuristic self-review

Run against the rebuilt product with a live workspace, not against the design intent. Only issues
that were real are listed; each was fixed in this branch unless marked otherwise.

| heuristic | what was wrong | resolution |
|---|---|---|
| Visibility of system status | A solve takes minutes and the first build blocked page load on it, with no way to tell whether anything was happening. | Planning moved to the released jobs path with QUEUED / RUNNING stated, surviving a reload; the workspace read stays fast so Network and Data are usable immediately. |
| Match to real-world language | The planner's own reasons reached the operator verbatim — "no candidate materially improves priority-weighted service shortfall over the incumbent". | Every reason the planner can emit is translated, with the original kept under Technical details. A test holds the real strings to the policy. |
| Match to real-world language | "Reliability not measured" was printed beside "from 1,865 deliveries", attaching a lead-time sample to a fill measurement. | The sample now attaches to what it measured, and the missing one says what would make it measurable. |
| User control and freedom | A run covered a selection of products with no way to see or change which. | The selection, its size and the rule that chose it are stated wherever the plan appears, and the size is a control next to the run button. |
| Consistency | An attention card showed "Critical" and "Stable" at once — risk level next to replenishment stance. | The card shows how exposed the object is; the stance stays in the panel where it has room to explain itself. |
| Error prevention | Narrowing a run orphaned declared amendment rights, and the server refused the request. | Products carrying a declared order change always travel with the run. |
| Recognition over recall | A decision had no route to the thing it affects, and a network object had no route to its decision. | Both directions are one click, and the selection lives in the address bar. |
| Efficiency | The default filter on Decisions was "Needs review"; a plan with nothing to review opened on an empty list while six decisions sat behind "All". | The default follows the data. |
| Minimalism | An abstaining plan rendered six "Not available" rows and three empty disclosures. | A plan that priced nothing says so once. |
| Minimalism | The service list repeated each location once per product. | One row per location, showing its worst line. |
| Error recovery | Every failed run said "run it again over fewer products", including when the server had refused the data outright. | A refusal, a timeout and an unknown failure now say different things, and a refusal offers Data. |
| Contextual help | "Explain this page" was the loudest control in the product, on every page. | Tertiary "Help" in the bar; the explanation itself is on the decision. |
| Aesthetic integrity | Nine decision verbs in a four-column grid left a hole showing the grid's own gap colour; the hero's two CTAs had different widths on a phone. | Three columns; the magnetic wrapper goes full width on a phone. |

Two findings were not frontend problems and are recorded as limitations rather than fixed here: a
full-catalogue run is unlikely to finish inside the job timeout, and one planner slot per API
process means a long run makes a concurrent interactive plan answer 429.
