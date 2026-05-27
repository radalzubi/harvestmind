# First 20 Prospects — How to Fill This Template

The CSV `first_20_prospects_template.csv` is intentionally empty.
**Do not fabricate prospects.** Every row must come from a verified public
source. Below is the column dictionary and the recommended sources.

---

## Column Dictionary

| Column | Required | What goes here |
|---|---|---|
| `organization` | ✅ | Legal operating name of the food hub or aggregator |
| `state` | ✅ | Two-letter state abbreviation. Midwest preferred for first 20 |
| `website` | ✅ | Public website URL — confirm it loads before adding the row |
| `contact_name` | Recommended | Full name of the GM, Ops Lead, or Founder. From LinkedIn, About page, or grant filings |
| `contact_title` | Recommended | Their exact public-facing title |
| `email` | Recommended | Direct work email if published. Do not guess email formats — leave blank if unverified |
| `phone` | Optional | Main line is fine; avoid mobile numbers unless publicly listed |
| `buyer_types_served` | ✅ | Pipe-separated list from: `schools \| hospitals \| universities \| grocery \| foodservice \| restaurants \| wholesale` |
| `evidence_of_produce_aggregation` | ✅ | One-line citation. Example: "Lists 23 partner farms on About page" or "USDA LFPP 2023 awardee — produce aggregation grant" |
| `evidence_of_institutional_buyers` | ✅ | One-line citation. Example: "Sells to Indianapolis Public Schools per case study" |
| `estimated_size` | ✅ | One of: `< $1M`, `$1M–$3M`, `$3M–$10M`, `$10M–$25M`, `> $25M`, `unknown`. Use grant awards, employee counts on LinkedIn, or press coverage to estimate |
| `pain_hypothesis` | ✅ | One sentence about why this operator likely has HarvestMind-shaped pain |
| `source_link` | ✅ | URL of the source you used to verify. Required for accountability |
| `priority_score` | ✅ | 1 (low) — 5 (high). See scoring rubric below |
| `outreach_status` | ✅ | One of: `not contacted`, `email sent`, `replied`, `call scheduled`, `call completed`, `disqualified`, `pilot in discussion` |
| `notes` | Optional | Free-text field — what you learned, who introduced, follow-up reminders |

---

## Priority Scoring Rubric

Score each prospect 1–5 by summing these factors, then dividing by 5:

| Factor | Yes (+1) | No (0) |
|---|---|---|
| In Midwest (proximity to Purdue) | Indiana, Illinois, Michigan, Ohio, Kentucky | Other |
| Revenue in $3M–$15M sweet spot | Yes | Outside this range |
| Sells to institutional buyers | Yes | Only wholesale or DTC |
| Recently received a grant for tooling/ops | LFPP, RFBC, or state ag grant in last 24 months | No |
| Public-facing operator (GM, founder named on website) | Yes | Generic info@ contact only |

Round to nearest integer. Anything ≤ 2 is probably not worth outreach yet.

---

## Recommended Sources (public, verifiable)

### Primary sources

1. **USDA Local Food Directories**
   https://www.ams.usda.gov/local-food-directories/foodhubs
2. **USDA Local Food Promotion Program (LFPP) awardees**
   https://www.ams.usda.gov/services/grants/lfpp/awards
3. **Regional Food Business Centers**
   https://www.ams.usda.gov/services/local-regional/regional-food-business-centers
4. **State Department of Agriculture local-food directories**
   - Indiana: in.gov/isda/markets-and-grants/
   - Illinois: agr.state.il.us
   - Michigan: michigan.gov/mdard
   - Ohio: agri.ohio.gov

### Secondary sources

5. **Wallace Center / Food Systems Leadership Network** member directory
6. **National Farm to School Network** — institutional buyer side
7. **Local Line, Barn2Door, Open Food Network customer logos** (small hubs often visible)
8. **Press coverage** — search `"food hub" + state + "2023" OR "2024"`
9. **LinkedIn company search** with filters: industry = "Food Production", size = 11–200

### Avoid these as sources

- Buy-side directories that pay-to-play (no validation of operator size)
- Crowdfunding pages (unreliable revenue signals)
- Trade-show exhibitor lists (operators show up for vendors, not as vendors)

---

## Suggested Workflow

1. Start with USDA LFPP awardees in Midwest states from last 2 years — these
   are publicly disclosed, recent, and signal a hub that's investing in operations
2. Cross-reference against the Regional Food Business Centers' member lists
3. For each candidate, spend 10 minutes confirming: still operating, has a
   named GM, sells to institutional buyers, has a working website
4. Add to CSV with priority score
5. **Stop at 20.** Quality beats quantity. A list of 20 well-researched
   prospects will outperform a list of 200 names from a directory dump

---

## What to do once the list is full

1. Sort by `priority_score` descending
2. Send Version A (warm intro) outreach for any prospect where you can
   identify a connector (Purdue contact, mutual LinkedIn, board member)
3. Send Version B (cold outbound) for the rest, in batches of 3–5 per week
4. Update `outreach_status` within 24 hours of every send and every reply
5. Re-score quarterly — operators who didn't respond may become priority
   targets after a season change or new buyer relationship
