# Prospect Research Notes

_Companion document to `first_20_prospects_template.csv`. Records what was
searched, what was found, what was rejected, what's verified, and what
still needs operator-side validation. **Source-of-record for accountability
on each prospect.**_

---

## Summary

| Metric | Count |
|---|---|
| Total prospects added | **20** |
| Fully verified active operations | 16 |
| Partially verified (needs deeper confirmation) | 4 |
| Rejected during research | 5 (see "Rejected" section) |

### Count by segment (matches target mix)

| Segment | Target | Actual |
|---|---|---|
| Produce hubs / aggregators | 6 | 6 |
| Seafood / shellfish | 4 | 4 |
| Small food/bev wholesalers | 4 | 4 |
| Fresh-cut processors | 3 | 3 |
| Institutional distributors | 3 | 3 |
| **Total** | **20** | **20** |

---

## Sources searched

| Source | Quality | Used for |
|---|---|---|
| USDA Local Food Directories (ams.usda.gov) | Medium — pointed to the directory portal; specific operator names required follow-up | Discovery |
| USDA LFPP awardees (FY 2024) | Medium — PDF format limits direct extraction; awardee details require manual lookup | Validation of grant-receiving operators |
| Michigan Food Hub Network via MSU CRFS | **High** — `localdifference.org` had a clean list of 11 named Michigan food hubs | Segment 1 |
| Indiana Grown for Schools — distributors and food hubs list | **High** — direct list of 13 Indiana distributors with websites and phones | Segment 1 and 3 |
| Indiana State Department of Agriculture RFSI awardees | Medium — Produce Patch LLC surfaced; others not pursued (sub-$1M scale) | Validation of grant-funded operators |
| Cape Cod / Massachusetts shellfish search | **High** — Pangea, Wellfleet, Chatham all readily verifiable | Segment 2 |
| Virginia Seafood Suppliers directory | **High** — Mobjack Bay, Bevans, Sam Rust all surfaced | Segment 2 |
| Ohio family-owned distributor search | **High** — Atlantic Foods, Sirna & Sons, DNO surfaced cleanly | Segment 3 |
| Illinois farm-to-school distributors search | **High** — Common Market Great Lakes, Tulip Tree Gardens, Midwest Foods surfaced | Segments 3 and 5 |
| Wisconsin DATCP Farm to School | Medium — REAP Food Group surfaced as the relevant coordinator | Segment 5 |
| FreshEdge company directory (freshedgefoods.com) | **Low for our purposes** — confirmed several "independent" fresh-cut processors are now part of FreshEdge (Garden Cut, Monteverde's, Indianapolis Fruit, Piazza) | Used to REJECT prospects, not add them |
| Direct company websites | **High when accessible** — Wellfleet, Region Roots, Hoosier Harvest, ValleyHUB, Oberlin Food Hub, Sirna & Sons, The Common Market, Pangea, Chatham, Mobjack Bay all returned useful content. Round Lake Produce About page returned 403. |
| Reddit (r/supplychain, r/ERP, r/smallbusiness) | High signal for vocabulary and pain patterns, low for named prospects (the oyster operator's name wasn't in the public post — see `reddit_discovery_post.md`) | Not used for naming individual prospects |
| Interstate Shellfish Sanitation Conference (ISSC) member list | Not directly accessed in this pass — recommended for next sourcing wave | Future Segment 2 expansion |
| National Association of Wholesaler-Distributors (NAW) | Not directly accessed in this pass | Future Segment 3 expansion |
| International Fresh-Cut Produce Association (IFPA) | Not directly accessed in this pass — name resolves but member directory not public-fetchable | Future Segment 4 expansion |

### Low-quality / abandoned sources

| Source | Why abandoned |
|---|---|
| Ohio Farmers Union food hubs page (ohfarmersunion.org/ohios-regional-food-hubs/) | Returned 404 |
| Round Lake Produce About page | Returned 403 (access blocked) |
| LFPP awardees PDF | Format prevented bulk extraction; only narrative-search-surfaced operators captured |
| Generic Cape Cod aquaculture overviews | Did not yield named multi-farm aggregators below the very largest |

---

## Segment-by-segment notes

### Segment 1 — Produce hubs / aggregators (6 prospects)

**Strongest fits**: Region Roots and Oberlin Food Hub. Both are
explicitly nonprofit, multi-farm, institutional-serving, with
verified contact information and recent activity.

**Verification status**:
- Region Roots: ✅ Fully verified (active page, contact email + phone, RFSI grant)
- Hoosier Harvest Market: ✅ Fully verified (named manager, contact email)
- Kalamazoo Valley CC ValleyHUB: ✅ Fully verified (phone, address, recent blog posts through Feb 2026)
- Oberlin Food Hub: ✅ Fully verified (email + phone), one anomaly to flag below
- Flint Fresh: ⚠️ Partially verified (website mentioned by Local Difference; not direct-fetched)
- West MI Farm Link: ⚠️ Partially verified (listed by Michigan Food Hub Network; not direct-fetched)

**Anomaly to flag**: **Oberlin Food Hub** lists a Cleveland address
(4540 Commerce Ave, Cleveland OH 44103) and a Boston area code phone
((617) 816-3786). Both seem inconsistent with the "Oberlin" name.
Verify before calling. The email (oberlinfoodhub@gmail.com) is the
safest first contact.

**Recommended additional research**: Indiana RFSI awardee Produce
Patch LLC (mentioned as supplying Daviess County Hospital + North
Daviess Schools) was not pursued because website was not surfaced
in the search; worth a manual lookup before week-2 outreach.

### Segment 2 — Seafood / shellfish (4 prospects)

**Strongest fits**: Wellfleet Shellfish Company (HACCP-certified
wholesale at meaningful scale, exact phone number, clear segment
match) and Mobjack Bay Seafood (named owner, multi-source
aggregation including own hatchery).

**Verification status**:
- Pangea Shellfish Company: ✅ Fully verified (active site through Nov 2025, B2B model clear)
- Wellfleet Shellfish Company: ✅ Fully verified (exact address, phone, certifications listed)
- Chatham Shellfish Co.: ✅ Verified (sales email, smaller scale)
- Mobjack Bay Seafood: ✅ Fully verified (founder named, exact location, volume figures)

**Critical sourcing note**: Avoid the very largest players (Island
Creek Oysters in Duxbury — 100+ farms + 700 chefs — likely too
sophisticated for a first pilot; they have a real ERP).

**Geographic concentration**: All 4 are East Coast (MA, MA, MA, VA).
Reflects where shellfish aggregation actually happens. Great Lakes
shellfish is too small a category to source from. If East Coast
operators don't respond, the next-best alternative is **Pacific
Northwest oyster cooperatives** (Hama Hama, Taylor Shellfish) —
researching them was deferred to next sourcing pass.

### Segment 3 — Food/bev wholesalers (4 prospects)

**Strongest fit**: Sirna & Sons (4th generation family, schools +
institutions, explicit in-house fresh-cut, exact contact info, in
target geography).

**Verification status**: All 4 fully verified for active operations,
ownership structure, customer mix, and approximate scale.

**Size concern**: DNO Produce and Midwest Foods may be at the upper
end of HarvestMind's intended ICP — they likely already have an
ERP. **This is actually intentional**: per the validation sprint
plan, ERP-equipped operators are valuable signal for Path C even if
they don't convert to a SaaS pilot. Approach them with the Version B
(venture-track) language; do not treat them as Path A prospects.

**Atlantic Foods caveat**: Contact email and phone were not surfaced
in the public search. Recommend phone-lookup or LinkedIn search
before outreach to fill the gap.

### Segment 4 — Fresh-cut processors (3 prospects)

**Strongest fit**: Round Lake Produce (independent, family-owned,
clearly in segment, regional reach matching our target).

**Verification status**:
- Round Lake Produce: ⚠️ Mostly verified (homepage and about-page metadata; About page returned 403 on direct fetch)
- Monteverde's: ⚠️ Verified but under FreshEdge umbrella (decision authority unclear)
- Preferred Fresh Cuts: ✅ Verified as independent Michigan-based fresh-cut

**Segment-wide observation**: The fresh-cut produce processor
category is heavily consolidated. Multiple operators I started
researching (G.O. Fresh, Garden Cut, Indianapolis Fruit, Piazza
Produce) turned out to be part of larger groups (FreshEdge, WPS
Fresh). **The "independent fresh-cut processor under 100 employees"
ICP is real but harder to source than expected.** This is itself
useful market signal — it suggests Path C (ERP add-on for
already-consolidated operators) may be the more accurate
venture-scale framing for the fresh-cut segment.

**Recommended additional research**: IFPA member directory if
accessible; LinkedIn search of "fresh-cut" + "operations" in target
states.

### Segment 5 — Institutional distributors (3 prospects)

**Strongest fit**: The Common Market Great Lakes (nonprofit,
explicitly institution-focused, 700 buying institutions, recently
acquired Local Foods Chicago which adds integration-pain story).

**Verification status**: All 3 verified for active operations.

**Size variance is high**:
- The Common Market Great Lakes: Likely $10M–$50M revenue. Large enough that they likely already have systems but the recent Local Foods acquisition creates a system-merging pain that's a HarvestMind-shaped problem.
- Tulip Tree Gardens: Probably $500K–$3M. Small. May not be at scale for a paid pilot but worth a discovery call.
- REAP Food Group: Nonprofit. Aggregator/coordinator hybrid. Pricing model will differ — pro-bono or grant-funded engagement may be more realistic than $3K–$15K paid pilot.

---

## Top 5 highest-priority prospects (across segments)

Ranked by combined fit + accessibility + likely willingness to engage:

1. **Sirna & Sons Produce** (OH) — 4th-gen family, 81 years, in-house fresh-cut, schools + institutions, verified email and phone. Strongest single all-around fit on the list.

2. **The Common Market Great Lakes** (Chicago, IL) — institutional-focused, 700 buying institutions, recent Local Foods acquisition creates immediate integration-pain narrative. Nonprofit with mission alignment to a "this helps schools and hospitals" framing.

3. **Region Roots Local Farm and Food Hub** (Crown Point, IN) — Indiana proximity to Purdue, verified contact, RFSI-grant-awardee status creates a natural conversation opener around grant-funded operations improvement.

4. **Wellfleet Shellfish Company** (Eastham, MA) — explicit operator-level perishable + traceability pain (HACCP-certified wholesale from multiple boat fisheries). Strong cold-outreach fit.

5. **Oberlin Food Hub** (Cleveland, OH) — explicit institutional + multi-buyer mix, smaller scale = lower decision-cycle friction, verified contact.

---

## Recommended first 10 outreach targets (for weeks 3–4 of the sprint)

Pick across segments deliberately — don't bias toward one segment in
the first wave. The whole point of the 3-segment sprint is to see
which segment responds.

1. Sirna & Sons Produce — OH — food/bev distributor
2. The Common Market Great Lakes — IL — institutional
3. Region Roots Local Farm and Food Hub — IN — produce hub
4. Wellfleet Shellfish Company — MA — seafood
5. Oberlin Food Hub — OH — produce hub
6. Round Lake Produce — MI — fresh-cut
7. Hoosier Harvest Market — IN — produce hub
8. Mobjack Bay Seafood — VA — seafood
9. Midwest Foods — IL — food/bev distributor
10. Preferred Fresh Cuts — MI — fresh-cut

That mix gives you 3 produce hubs, 2 seafood, 2 food/bev distributors,
2 fresh-cut, and 1 institutional in the first wave. The other 10
prospects are wave 2 (weeks 5–6).

---

## Gaps and uncertainties

| Gap | Mitigation |
|---|---|
| 4 prospects have no email surfaced in public search (Atlantic Foods, Round Lake Produce, Pangea Shellfish, Chatham Shellfish has only sales@) | Use LinkedIn + phone-call follow-up to surface direct emails before outreach. Several have contact forms that work. |
| Pangea Shellfish, Chatham Shellfish, Mobjack Bay have no named CEO/founder visible on the public site we fetched | Use LinkedIn search; for Mobjack Bay we already have founder John Vigliotta. |
| West MI Farm Link and Flint Fresh need direct-site verification | Spend 15 min on each website before week-3 outreach to confirm currently operating. |
| Oberlin Food Hub's geographic anomaly (Oberlin name, Cleveland address, Boston phone) | Verify by email first, not phone. Don't call until address/phone reconciled. |
| Fresh-cut processor segment is unexpectedly consolidated | This is a segment-level finding worth surfacing to advisors. Suggests Path C framing fits fresh-cut better than Path A. |
| No Great Lakes shellfish (it's not a meaningful category) | Accept East Coast for seafood; Pacific Northwest is next pool if East Coast underperforms |
| No Wisconsin or Pennsylvania-specific produce hub | Acceptable for now — IN/MI/OH coverage is dense |

---

## Prospects rejected during research (and why)

These were surfaced in search results but excluded from the final 20.
Recording them here so they aren't accidentally re-added.

| Prospect | Reason rejected |
|---|---|
| **Cherry Capital Foods** (Traverse City, MI) | **CLOSED November 2023.** Was previously the largest Michigan food hub. Listing it would have been the exact "do not fabricate" violation the user warned about. |
| Island Creek Oysters (Duxbury, MA) | Too large (operates own hatchery, distributes from 100+ farms to 700 chefs nationally). Almost certainly has full ERP + dedicated ops team. Not a Path A prospect; possible Path C target later. |
| Garden Cut (Indianapolis) | Acquired by FreshEdge group; not independently buyable. |
| Indianapolis Fruit Company | Under FreshEdge group. |
| Piazza Produce & Specialty Foods | Under FreshEdge group. |
| G.O. Fresh | Acquired by Wholesale Produce Supply (WPS Fresh) in January 2026. |
| Sysco Foods | Listed in Indiana Grown for Schools directory but obviously too large. |
| Stanz Food Service | Not researched in depth (Indiana distributor of unknown ownership); revisit if list needs filler. |
| Winkler Distribution | Same as Stanz — unverified in detail. |
| Local Source (Evansville IN) | Did not surface enough public information to verify segment fit. |
| Lost River Market and Deli (IN) | Market/deli, not an aggregator. |
| What Chefs Want | Larger distributor; not researched in detail. |
| Merkley & Sons Packing Co. | Packing-focused, not aggregation; not a clean segment match. |
| Bevans Oyster Company (VA) | Strong fit but Mobjack Bay Seafood preferred for the VA slot (clearer multi-farm aggregation evidence). Bevans is a good backup for wave 3. |
| Sam Rust Seafood (VA) | Family-owned since 1938; possible backup for seafood slot if Wellfleet or Mobjack don't respond. |

---

## What source types were most useful

Ranked by hit rate (verified prospect / search query):

1. **State-specific farm-to-school directories** — Indiana Grown for Schools, Illinois Farm to School Network. Very high quality. Many prospects, well-vetted, in target geography.
2. **State food hub network pages** — Michigan Food Hub Network (via Local Difference / MSU). Clean lists with locations and websites.
3. **Direct company websites** — when accessible, returned the most precise contact information.
4. **WebSearch for "[segment] [state] family owned distributor"** — surfaced 4 of the 4 food/bev distributors.
5. **WebSearch for "[segment] wholesale Massachusetts Virginia"** — surfaced all 4 shellfish operators.

Ranked by hit rate, low to medium:

6. USDA LFPP awardees PDF — narrative results only; full extract would require manual PDF parsing.
7. Generic search for "fresh-cut produce processor independent" — surfaced mostly consolidated entities.

Source types **NOT used in this pass** but worth a second sourcing wave:

- ISSC member list (for additional seafood operators)
- NAW member directory (for additional food/bev distributors)
- IFPA member directory (for independent fresh-cut operators not yet acquired)
- LinkedIn name + title searches (for surfacing direct GM/Ops Lead contacts)
- USDA F2S Census (for institutional buyer identification)

---

## Recommended next action

**Do not write more documents.**

The list is good enough to start outreach. The first 10 emails should go out within 3–5 business days. Run through these steps:

1. **Day 1 (tomorrow)**: For prospects 1–3 on the recommended first-10 list, surface the missing contact info via LinkedIn or a 5-minute phone call. Update CSV.

2. **Day 2**: Customize the operator outreach email (Version A, warm intro version if possible, cold otherwise) for the first 3 prospects using their segment-specific language.

3. **Day 3**: Send first 3 emails. Mark `outreach_status = email_sent` in CSV.

4. **Day 4**: Surface contact info for prospects 4–6. Send those emails.

5. **Day 5**: Surface 7–10 contacts and send. By end of week, first 10 emails are out.

6. **Day 5 (same day)**: Post first Reddit discovery post per `reddit_discovery_post.md`. r/supplychain or r/smallbusiness, depending on which feels more on-fit after a final read.

7. **Days 6–14**: Replies trickle in. Use `discovery_interview_script.md` for any reply that wants a call. Update CSV `outreach_status` daily.

8. **Day 14**: Pause. Re-score the response pattern by segment. The data from the first 10 emails is the most important thing.

The next strategy document gets written **after** the first 10 emails return data — and even then, only if the data warrants it.

---

## Honest meta-note

This research took ~90 minutes of automated searching and verification. **The same 90 minutes spent by a human with full LinkedIn access, phone-lookup tools, and trade-association directory access could likely produce a list 2–3× as deep.** The right next move is probably to spend 4–6 hours over a weekend manually expanding contact details (GM name, direct email, recent press) on the top 10 prospects, then to send outreach.

What I can't do from here that would help most:

- LinkedIn searches that require login
- Pulling individual contact emails from Hunter.io or Apollo
- Confirming current employment status of named operators
- Cross-referencing customer logos on operators' websites
- Pulling state procurement contract data to identify institutional buyers

Those are human-loop tasks. The list as it stands is a solid starting point that won't embarrass us in any operator conversation, but the contact-detail layer is intentionally thin and needs human enrichment before the first email goes out.
