# Three-Segment Validation Sprint — 90 Days

_Operational plan for the next 90 days. Replaces the implicit
"food hubs first" framing with parallel testing across three
segments. Goal: one paid diagnostic from any segment. Stretch
goal: three paid diagnostics, one per segment._

This document was triggered by a public-source scan (Reddit
r/supplychain, r/ERP, r/smallbusiness; USDA Regional Food
Business Centers; 2025 National Food Hub Survey) showing that
the operational pain HarvestMind addresses is broader than
food hubs. Seafood/shellfish operators and small food/bev
distributors are showing stronger willingness-to-buy signals
than food hubs alone.

---

## Why three segments, not one

| Reason | What the scan showed |
|---|---|
| Seafood signal is unexpectedly strong | An oyster-farm operator on r/smallbusiness described double/triple order entry, lot codes, harvest tags, QuickBooks integration pain, regulatory reporting, and traceability — at >$1M revenue. That's exactly HarvestMind's diagnostic shape. |
| Small food/bev distributors are actively searching | r/ERP threads show distributors saying "QuickBooks + spreadsheets stopped working" and asking for inventory + lot tracking tools, comparing real vendors. |
| Food hubs alone too narrow | 2025 National Food Hub Survey: 1 in 3 hubs cite infrastructure/equipment gaps, 43% want technical assistance. Real need, but the SaaS-funding niche is small. |
| Founder access varies by segment | Produce hubs accessible via Roy Ballard / RFBC / Purdue. Seafood requires different network. Food/bev distributors searchable via LinkedIn + ERP communities. |
| Diagnostic engine is segment-agnostic | The 5 staging tables (products, supplier deliveries, inventory lots, buyer orders, waste) work for any perishable operator. No product change needed to test 3 segments. |

**The core insight from the scan**: the diagnostic engine generalizes
to any perishable operator with messy data and lot-tracking pain. The
strategic mistake would be pre-committing to one segment before the
first 5 pilots tell us which converts fastest.

---

## Segment definitions

### Segment 1 — Produce aggregators / food hubs

| | |
|---|---|
| Revenue range | $1M–$25M |
| Why fits | Original HarvestMind ICP. FSMA-204 anchor. Purdue/Midwest geography. |
| Pain signal | Medium (food hub survey + LFPP grant data) |
| Sourcing | USDA Local Food Directories, RFBC, LFPP awardees |
| Founder access | High (Roy Ballard, extension, Purdue alumni) |
| Target count for sprint | 6 prospects |

### Segment 2 — Seafood / shellfish operators

| | |
|---|---|
| Revenue range | $500K–$10M |
| Why fits | Strong Reddit signal. Lot/harvest tag pain. BlueTrace + QuickBooks gap. Regulatory reporting (FDA, state shellfish). |
| Pain signal | **Strong** (one operator described exactly the problem HarvestMind solves) |
| Sourcing | Interstate Shellfish Sanitation Conference member lists, state shellfish programs, Aquaculture North America directory, r/oysterfarming and adjacent communities |
| Founder access | Low (no existing relationships) — needs cold outreach |
| Target count for sprint | 4 prospects |

### Segment 3 — Small food/bev wholesalers and distributors

| | |
|---|---|
| Revenue range | $2M–$30M |
| Why fits | r/ERP signal. Active ERP search behavior. Lot tracking + BBD tracking + inventory across multiple warehouses. |
| Pain signal | Strong |
| Sourcing | LinkedIn ("Director of Operations" + "food distributor"), trade associations (NAW, FMI), regional wholesale grocer networks |
| Founder access | Medium |
| Target count for sprint | 4 prospects |

### Segment 4 — Fresh-cut processors

| | |
|---|---|
| Revenue range | $3M–$50M |
| Why fits | Highest perishability of all segments. Same-day-to-3-day shelf life. Major shortage/waste exposure. |
| Pain signal | Strong (inferred from category economics; not directly Reddit-confirmed) |
| Sourcing | International Fresh-Cut Produce Association (IFPA), state ag departments |
| Founder access | Low |
| Target count for sprint | 3 prospects |

### Segment 5 — Local food distributors serving institutions

| | |
|---|---|
| Revenue range | $1M–$10M |
| Why fits | Farm-to-school + institutional procurement. Often hybrid hub/distributor. Strong traceability pressure from institutional buyers. |
| Pain signal | Medium |
| Sourcing | National Farm to School Network, state farm-to-school directories, school district produce procurement contacts |
| Founder access | Medium (via extension contacts) |
| Target count for sprint | 3 prospects |

**Total target: 20 prospects across 5 segments.**

---

## 90-day sprint structure

### Weeks 1–2: Build the prospect list

**Output**: 20 named prospects in `first_20_prospects_template.csv`
with the segment mix above. Each prospect must have:

- Verified organization name + state
- Working website
- Named contact (GM, Ops Lead, Founder) from LinkedIn or About page
- Source link (USDA, RFBC, LinkedIn, state directory, etc.)
- Priority score (1–5) per rubric in `first_20_prospects_template.README.md`
- Pain hypothesis specific to that operator

**Do not skip the priority scoring.** A list of 20 well-researched
prospects will outperform 200 names from a directory dump.

**Time investment**: ~15–20 hours of research over 2 weeks.

### Weeks 3–4: First outreach wave + Reddit posts

**Output**:
- 10 cold outreach emails sent (Version B, see `operator_outreach_email.md`)
- 3 Reddit discovery posts published (see `reddit_discovery_post.md`)
- 5 warm intros requested through Purdue/RFBC contacts
- 2 connector calls (Roy Ballard + 1 RFBC contact)

**Discovery, not pitch**, in every channel. Goal is 25-minute
discovery calls, not sales.

**Tracking**: Update prospects CSV `outreach_status` column daily.

### Weeks 5–6: First discovery calls

**Output**:
- 5–8 discovery calls completed using the 15-question script in
  `discovery_interview_script.md`
- Notes captured in structured format (segment, tech stack, top
  pain, willingness signals)
- Initial pattern recognition: which segment is leaning in?

**Expect**: 30–50% of email outreach produces a reply, of which
30–50% convert to a call. That's 1–3 calls from the cold cohort,
plus whatever Reddit + warm intros produce.

### Weeks 7–8: First paid pilot conversion attempts

**Output**:
- 2–4 operators who completed a discovery call asked to scope a
  paid pilot
- 1 signed paid pilot at $3K–$15K

**This is the critical moment.** If no operator converts to a
paid pilot by end of week 8, the wedge offer needs revision.

### Weeks 9–10: First paid diagnostic begins

**Output**:
- Week 9: data intake + validation with the first pilot operator
- Week 10: diagnostic engine run on real operator data

**This is the moment the engine touches real data for the first
time.** Expect bugs. Document them. They're product feedback.

### Weeks 11–12: Findings + readout + business model question

**Output**:
- Final report delivered to the first pilot operator
- 60-minute readout call
- The closing question asked explicitly: *"Which would be most
  valuable — a one-time analysis, recurring quarterly diagnostics,
  or a live tool connected to your existing system?"*

**This answer is the most important data point of the sprint.**

---

## Three-segment tracking (the actual point of the sprint)

The reason for testing three segments in parallel is to surface
which one converts fastest. Track these metrics by segment:

| Metric | Why it matters |
|---|---|
| Email response rate | Which segment is reachable cold? |
| Discovery call conversion | Which segment finds time for a 25-minute call? |
| Pain language match | Which segment uses the words from the Reddit/ag-feed scan? |
| Tech stack distribution | Which segment maps to which path (A/B/C)? |
| Willingness-to-pay signal | Which segment names a budget number unprompted? |
| Pilot conversion | Which segment signs a paid contract? |
| Data export feasibility | Which segment can actually produce clean CSVs? |

At end of 90 days, rank segments by these metrics. The next 90
days commit to the top 1–2 segments only.

---

## Decision criteria at end of sprint (day 90)

### Continue with all three segments if:
- ≥ 1 paid pilot from any segment
- ≥ 2 discovery calls per segment completed
- No segment is uniformly dead (no responses, no interest)

### Narrow to top 2 segments if:
- ≥ 1 paid pilot
- One segment shows 3× the engagement of the lowest
- The lowest segment had < 1 discovery call

### Narrow to one segment if:
- ≥ 1 paid pilot
- One segment clearly dominates (5×+ engagement)
- Founder time is the binding constraint

### Pivot the offer if:
- 0 paid pilots after 90 days of focused outreach
- Discovery calls happen but none convert to scoping
- Operators uniformly say "this is interesting but not now"

### Wind down the project if:
- 0 paid pilots
- < 5 discovery calls completed
- 0 operator-side advisor candidates engaged
- Founder team confidence below 50% for 30+ days

---

## What the scan changed in the operating plan

| Before scan | After scan |
|---|---|
| ICP = food hubs | ICP = perishable operators across 5 segments |
| First pilot = produce hub | First pilot = whichever segment converts first |
| FSMA-204 enforcement Jan 2026 | FSMA-204 compliance target July 20, 2028 |
| Lead generation = USDA directory only | LinkedIn + USDA + state directories + Reddit discovery + trade associations |
| "Produce operator" in operator outreach | "Perishable operator" in outreach |
| Strict pricing tiers | Pricing tiers + larger-operator tier ($10K–$15K) |
| 0 Reddit presence | 3 Reddit discovery posts in week 3–4 |

---

## What did NOT change

- The diagnostic engine itself (engine is segment-agnostic)
- The pilot offer pricing structure ($3K–$15K with larger-operator tier)
- The 30-day pilot timeline
- Version A vs. Version B audience split
- The single most important next milestone: **one real messy dataset**

---

## The single sentence to remember

The sprint is designed to answer **one question**:

> *"Across produce hubs, seafood/shellfish operators, and food/bev
> distributors, which segment converts to a paid diagnostic the
> fastest, and which one of Path A/B/C does that segment pull toward?"*

The first paid operator answers half of it. The first 3 paid operators
answer all of it. Everything else in the next 90 days is in service
of that question.

---

## Operator-side advisor recruiting runs in parallel

`operator_advisor_recruiting_note.md` (Version B) describes the
operator co-founder/advisor recruitment. That track runs
independently of segment validation. The two tracks reinforce
each other:

- An operator-side advisor helps interpret segment signals
- A segment that converts fastest helps identify operator-side
  advisor candidates from that segment

If by week 6 of the sprint no operator-side advisor candidate has
engaged, that's worth surfacing as a separate risk. Don't let it
go silent.

---

## What to do tomorrow

1. Open `first_20_prospects_template.csv`
2. Spend 2 hours researching segment 1 (produce hubs) prospects.
   Pull from USDA directories. Score 6 prospects.
3. Spend 2 hours researching segment 2 (seafood/shellfish).
   Start with Interstate Shellfish Sanitation Conference member
   list. Score 4 prospects.
4. Spend 1 hour drafting and posting the first Reddit discovery
   post (use `reddit_discovery_post.md` template). Post to
   r/supplychain or r/smallbusiness.
5. Do not write more documents.

That is 5 hours of work tomorrow. The work after that is more
research, the first 10 outreach emails, and the first Reddit
discovery posts. Total time investment in weeks 1–2: ~25 hours.

Everything else is procrastination until the first operator says yes.
