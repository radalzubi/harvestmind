# First 20 Prospects — How to Fill This Template

The CSV `first_20_prospects_template.csv` is intentionally empty.
**Do not fabricate prospects.** Every row must come from a verified
public source.

**Updated strategy (post-Reddit + ag-feed scan):** The first 20
prospects should span **five segments**, not just food hubs. This
matches the public-source signal that perishable operators across
seafood, food/bev distribution, and fresh-cut processing have
equal or stronger pain than food hubs alone. See
`three_segment_validation_sprint.md` for the full reasoning.

---

## Segment mix (target counts)

| Segment | Count | Why included |
|---|---|---|
| Produce aggregators / food hubs | 6 | Original HarvestMind ICP; strongest Purdue/Midwest founder access |
| Seafood / shellfish operators | 4 | Strong Reddit signal (oyster operator described exact problem) |
| Small food/bev wholesalers and distributors | 4 | r/ERP signal: actively searching for inventory + lot tracking tools |
| Fresh-cut processors | 3 | Highest perishability of all segments; high shortage/waste exposure |
| Local food distributors serving institutions | 3 | Strong traceability pressure from institutional buyers (schools, hospitals) |

**Total: 20 prospects across 5 segments.**

If a segment doesn't yield 4 quality prospects, leave the row
empty rather than padding with weak entries.

---

## Column dictionary

| Column | Required | What goes here |
|---|---|---|
| `organization` | ✅ | Legal operating name |
| `state` | ✅ | Two-letter state abbreviation. Midwest preferred but not required. |
| `website` | ✅ | Public website URL — confirm it loads before adding the row |
| `contact_name` | Recommended | Full name of the GM, Ops Lead, or Founder. From LinkedIn, About page, or grant filings |
| `contact_title` | Recommended | Their exact public-facing title |
| `email` | Recommended | Direct work email if published. Do not guess email formats — leave blank if unverified |
| `phone` | Optional | Main line is fine; avoid mobile numbers unless publicly listed |
| `buyer_types_served` | ✅ | Pipe-separated list from: `schools \| hospitals \| universities \| grocery \| foodservice \| restaurants \| wholesale \| institutional` |
| `evidence_of_produce_aggregation` | ✅ | One-line citation. Adapt this column to whatever the segment-specific evidence is: produce aggregation, seafood harvest, food/bev distribution, fresh-cut processing |
| `evidence_of_institutional_buyers` | ✅ | One-line citation. Example: "Sells to Indianapolis Public Schools per case study" |
| `estimated_size` | ✅ | One of: `< $1M`, `$1M–$3M`, `$3M–$10M`, `$10M–$25M`, `> $25M`, `unknown` |
| `pain_hypothesis` | ✅ | One sentence about why this operator likely has HarvestMind-shaped pain |
| `source_link` | ✅ | URL of the source you used to verify. Required for accountability |
| `priority_score` | ✅ | 1 (low) — 5 (high). See scoring rubric below |
| `outreach_status` | ✅ | One of: `not contacted`, `email sent`, `replied`, `call scheduled`, `call completed`, `disqualified`, `pilot in discussion` |
| `notes` | Optional | Free-text — what you learned, who introduced, segment-specific context |

**Recommended addition: `segment` column** at the front. Values:
`produce_hub`, `seafood`, `food_bev_distributor`, `fresh_cut`,
`institutional`. Make filtering by segment trivial.

---

## Priority scoring rubric (revised)

Score each prospect 1–5 by summing these factors (1 point each),
then dividing by 6:

| Factor | Yes (+1) | No (0) |
|---|---|---|
| In Midwest or accessible US region | Yes | Far-coast only |
| Revenue in sweet spot for segment | See per-segment ranges below | Outside |
| Has named operator contact (not generic info@) | Yes | No |
| Recently received a grant for tooling/ops (LFPP, RFBC, state ag) | Yes | No |
| Multiple farms/suppliers aggregated OR multi-location | Yes | Single-source / single-location |
| Public-facing FSMA-204 or traceability pressure | Mentioned in press, case study, or buyer documentation | Not visible |

Round to nearest integer. Anything ≤ 2 is probably not worth outreach.

### Per-segment revenue sweet spots

| Segment | Sweet spot |
|---|---|
| Produce aggregators / food hubs | $3M–$15M |
| Seafood / shellfish | $1M–$10M |
| Food/bev distributors | $5M–$30M |
| Fresh-cut processors | $5M–$25M |
| Institutional distributors | $2M–$10M |

---

## Sources by segment

### Segment 1 — Produce aggregators / food hubs

| Source | URL |
|---|---|
| USDA Local Food Directories — Food Hubs | https://www.ams.usda.gov/local-food-directories/foodhubs |
| USDA Regional Food Business Centers | https://www.ams.usda.gov/services/local-regional/rfbcp |
| LFPP awardees (USDA AMS) | https://www.ams.usda.gov/services/grants/lfpp/awards |
| Wallace Center Food Systems Leadership Network | https://foodsystemsleadershipnetwork.org |
| State ag departments | Indiana: in.gov/isda · Illinois: agr.state.il.us · Michigan: michigan.gov/mdard |

### Segment 2 — Seafood / shellfish operators

| Source | URL or method |
|---|---|
| Interstate Shellfish Sanitation Conference member list | https://www.issc.org |
| State shellfish program directories | Search "[state] shellfish growers" |
| Aquaculture North America directory | https://www.aquaculturenorthamerica.com |
| Reddit (r/oysterfarming, r/aquaculture) | Discovery only — see `reddit_discovery_post.md` |
| LinkedIn search | "Oyster farm" + "operations" + "[state]" |

### Segment 3 — Small food/bev wholesalers and distributors

| Source | URL or method |
|---|---|
| NAW (National Association of Wholesaler-Distributors) directory | https://www.naw.org |
| LinkedIn search | "Director of Operations" + "food distributor" + revenue filters |
| Trade Press (Food Logistics, Refrigerated Frozen Foods) | https://www.foodlogistics.com |
| State wholesale grocers associations | Region-specific |
| r/ERP threads | https://reddit.com/r/ERP — track real operators asking about inventory tools |

### Segment 4 — Fresh-cut processors

| Source | URL or method |
|---|---|
| International Fresh-Cut Produce Association (IFPA) | https://www.freshproduce.com |
| State ag departments — processor lists | Each state ag dept |
| Press: Produce Business, Fresh Cut magazine | https://www.producebusiness.com |
| LinkedIn search | "Fresh-cut" + "operations manager" |

### Segment 5 — Local food distributors serving institutions

| Source | URL or method |
|---|---|
| National Farm to School Network | https://www.farmtoschool.org |
| USDA Farm to School Census | https://farmtoschoolcensus.fns.usda.gov |
| State farm-to-school coordinators | Each state |
| School district produce procurement contacts | Targeted research by district |
| Regional Food Business Centers (cross-listed with Segment 1) | https://www.ams.usda.gov/services/local-regional/rfbcp |

---

## What changed from the previous version

| Before scan | After scan |
|---|---|
| All 20 prospects = food hubs | Mix of 5 segments |
| USDA directory primary source | USDA + ISSC + NAW + IFPA + Farm to School |
| Midwest-only | Midwest preferred, national acceptable |
| Priority scoring 5-factor | Priority scoring 6-factor (added FSMA/traceability pressure visibility) |
| Avoided ERP-equipped operators | Open to ERP-equipped operators (tests Path C signal) |

---

## What to do once the list is full

1. Sort by `priority_score` descending, then `segment` (so the
   highest-priority prospects from each segment surface first)
2. Send Version A (warm intro) outreach for any prospect where
   you can identify a connector (Purdue contact, mutual LinkedIn,
   board member, RFBC staff)
3. Send Version A (cold outbound) for the rest, in batches of
   3–5 per week
4. Use the `reddit_discovery_post.md` plan to add Reddit-sourced
   prospects in parallel
5. Update `outreach_status` within 24 hours of every send and
   every reply
6. Re-score quarterly — operators who didn't respond may become
   priority targets after a season change or new buyer relationship

---

## A note on the 20-prospect ceiling

20 is a deliberate cap, not a goal. **Quality of research beats
quantity of names.** A well-researched 20-prospect list from
which 3–5 paid pilots emerge in 90 days is better than a
200-name list that produces 0 pilots.

If you find yourself with 40 prospects at the same priority
score, narrow to 20. The discipline of choosing is part of the
work.
