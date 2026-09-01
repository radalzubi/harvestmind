# Discovery Interview Script — 15 Questions

_25-minute call. Goal: assess whether this operator has the problem,
which version of the product would help, and whether they'd consider
a paid diagnostic. **This is not a sales call.** It is a structured
discovery conversation._

The right outcome of a discovery call is **not** a sale. The right
outcome is one of:

1. "Yes, this problem matches mine. I'd consider a paid diagnostic."
2. "Yes, this problem matches mine, but I would only want X (one-time / recurring / live tool)."
3. "This problem partially matches. The bigger thing I struggle with is Y."
4. "This problem does not match. Here's what I actually struggle with: Z."

All four are valuable. The worst outcome is "I don't really know
what they meant" — which usually means the interviewer pitched
instead of listening.

---

## Pre-call setup (10 minutes before the call)

- [ ] Re-read prospect's website, About page, LinkedIn
- [ ] Identify 2 facts to reference: "I saw you supply [X buyer]"
  or "Your About page mentions [Y]"
- [ ] Have prospect's row in the CSV open
- [ ] Have this script open in a separate window
- [ ] Have a blank doc for notes
- [ ] Mute notifications

**Do not have a pitch deck open.** If you reach for one mid-call,
you've lost the conversation.

---

## Call structure (25 minutes)

| Minutes | Phase | Goal |
|---|---|---|
| 0:00 – 2:00 | Opening | Confirm time, set expectation, ground the conversation |
| 2:00 – 5:00 | Context (Q1–Q3) | What they do, what their stack looks like |
| 5:00 – 15:00 | Pain dig (Q4–Q11) | Where things break, what they currently do about it |
| 15:00 – 20:00 | Willingness (Q12–Q14) | What they'd pay, what shape they'd buy |
| 20:00 – 23:00 | Mutual fit (Q15) | Whether this is a real pilot conversation |
| 23:00 – 25:00 | Close | Next step + thank you |

---

## Opening (2 minutes)

> "Thanks for the time. I want to be respectful of your 25 minutes,
> so here's what I'm hoping we get to: I'd like to understand how
> your operations actually work — what systems you use, where things
> break, and whether the problem I'm working on matches yours. I'm
> not selling anything today. If at the end of the call we think
> there's a fit for a paid diagnostic engagement, we can talk about
> that, but it's not the goal of the call."

That opening does three things:

1. Confirms the time bound
2. Names "not selling anything today" — relaxes the operator
3. Names the possibility of a paid engagement — sets expectations

---

## Q0 — THE LOAD-BEARING QUESTION. Ask it on every call.

**"Have you ever told a customer you can only commit to less than they
asked for, because you weren't sure your supplier would actually deliver?
Or do you promise it and then figure it out?"**

*Why we ask*: This is the single question that decides whether the product
has a decision to optimize. Our engine recommends how much to commit
BEFORE supply resolves. If operators never reduce a commitment — if they
always promise and scramble — then commitment is not a choice variable,
there is no interior optimum, and the optimizer has nothing to do no
matter how good the math is.

It also explains something the competitive research could not: no vendor
sells stochastic customer-commitment optimization, even though Lokad,
GAINS and ToolsGroup could all build it and already serve these
customers. Absence may be a demand signal rather than a capability gap.
This question tells us which.

*Listen for*:
- **"We always promise and sort it out later"** → the decision does not
  exist. Ask what happens when they cannot deliver, and who absorbs it.
  If the answer is "we buy on the market and eat the cost", the value is
  in RECOURSE COST, not in the commitment.
- **"Yes, we hold back on some customers"** → the decision exists. Ask
  immediately: how do you decide how much to hold back? If the answer is
  a gut number or a flat percentage, that is exactly the gap.
- **"We only commit what we have in the building"** → they have already
  solved it by refusing to pre-commit. Ask what that costs them in lost
  orders.

*Follow-up regardless of answer*: **"When a supplier comes up short, what
do you actually do that day?"** Their recourse options and cost are the
other half of the economics, and our own testing shows the model is worth
most when recourse is expensive or unavailable.

*What answer kills the bet*: "We never have supply problems, our growers
always deliver what they promise."

---

## The 15 questions

### Context (Q1–Q3)

**Q1 — "What system do you use for inventory today?"**

*Why we ask*: Identifies tech stack. Maps to Path A/B/C signal.
*Listen for*: QuickBooks, Excel, Google Sheets, Local Line,
Famous, Produce Pro, NetSuite, Sage, BlueTrace, AirTable,
custom Access database.
*What answer kills the bet*: "We just rebuilt our ERP last quarter
with [Tier-1 ERP]." (They've already absorbed the budget.)

**Q2 — "What system do you use for accounting?"**

*Why we ask*: Usually QuickBooks for the segment we target.
Confirms the "ERP-equipped vs. spreadsheet-heavy" axis.
*Listen for*: QuickBooks Online, QuickBooks Desktop, Sage,
NetSuite, Xero, custom.
*What answer kills the bet*: "Same as inventory — it's all in
NetSuite." (Already integrated; smaller pain.)

**Q3 — "How many warehouse locations or sites are you running?"**

*Why we ask*: Multi-site operators have more inventory complexity
and bigger waste exposure. Single-site simpler.
*Listen for*: 1 (single hub), 2–4 (regional), 5+ (multi-DC).
*What answer kills the bet*: Nothing — both extremes are real
customers. This just sizes the pilot.

### Pain dig (Q4–Q11)

**Q4 — "Where do lot codes live?"**

*Why we ask*: This is the diagnostic-critical question. If lot codes
don't exist in any system, traceability module can't run.
*Listen for*: "On paper", "In a separate spreadsheet", "In [system]
but disconnected from inventory", "We use BlueTrace / Trustwell /
Wherefour for that."
*What answer kills the bet*: "All in our ERP, fully integrated to
inventory." (Path C signal but no immediate diagnostic value.)

**Q5 — "Where do sales orders live? Where do supplier deliveries live?"**

*Why we ask*: If these are in different systems, double entry is
almost guaranteed. That's the r/ERP and r/smallbusiness signal.
*Listen for*: "Orders in [X], deliveries in [Y], and we re-key
them." That's the textbook pain we address.
*What answer kills the bet*: "All in one system, no re-entry."

**Q6 — "Where do waste / shrink / spoilage records live?"**

*Why we ask*: Most operators have NO formal waste log. If they
don't track it, they can't size it.
*Listen for*: "Honestly, nowhere", "Sales reps tell me", "In a
notebook in the cooler", "Daily inventory count but not tracked
over time."
*What answer kills the bet*: "We have a formal waste log and we
review it monthly." (Less pain to address.)

**Q7 — "If I asked you to trace one specific lot from supplier to
buyer right now, how long would it take you?"**

*Why we ask*: FSMA-204 readiness question without using the term.
*Listen for*: "Hours", "Days", "I'd have to call the supplier",
"Honestly, we couldn't do it for older lots."
*What answer kills the bet*: "Twenty minutes — we have a clean
chain in [system]." (Compliance is solved; ops is the bigger pain.)

**Q8 — "How many times does the same order data get entered into
different systems on a typical day?"**

*Why we ask*: Direct quote from r/smallbusiness oyster operator.
Universal pain in the segment.
*Listen for*: "Two or three", "Don't get me started", "I make my
team re-enter into [X] every morning."
*What answer kills the bet*: "Once. We've automated it."

**Q9 — "What report is hardest to produce right now: a buyer
report, a regulatory report, an audit, a board update, or an
internal ops dashboard?"**

*Why we ask*: Names the report we should design for.
*Listen for*: "Buyer audit", "Sysco/[hospital network] traceability
questionnaire", "Our board wants margin variance and we struggle
to explain it."
*What answer kills the bet*: "All of them are easy. We have
[BI tool]."

**Q10 — "What breaks first when order volume increases?"**

*Why we ask*: Reveals the operator's mental model of their
scaling constraint.
*Listen for*: "Fulfillment", "Picking accuracy", "Buyer complaints",
"Substitutions go up", "We start over-promising."
*What answer kills the bet*: "Nothing — we have headroom."

**Q11 — "Do you ever overpromise product because inventory or
supply is uncertain at commit time?"**

*Why we ask*: The available-to-promise question.
*Listen for*: "All the time", "Yes, especially during [season]",
"That's why we keep buffer."
*What answer kills the bet*: "Never. We commit conservatively."
(That operator doesn't have ATP pain.)

### Willingness (Q12–Q14)

**Q12 — "Do you currently know how much product you lose to
spoilage, expiry, or discounting each month — in dollars?"**

*Why we ask*: The waste-loss diagnostic question.
*Listen for*: "Roughly", "No, but I know it's significant", "I
estimate it from gross margin shrinkage", "We track quantity but
not value."
*What answer kills the bet*: "Yes — we have a clean monthly
waste dollar figure that we present to the board."

**Q13 — "Would you pay for a diagnostic that quantified your
waste loss, shortage loss, supplier reliability, buyer fulfillment
risk, and traceability completeness — in dollars, against your
own data?"**

*Why we ask*: The willingness-to-pay question. Direct.
*Listen for*: "Yes, definitely", "Yes, if it's not too expensive",
"How much?", "What's the deliverable?", "Why not just hire a
consultant?"
*What answer kills the bet*: "Not really — we'd want to build it
ourselves."

If they say yes, follow up: **"What would you reasonably pay
for that?"** Their number is gold. Write it down verbatim.

**Q14 — "If the diagnostic found real losses, would you want it
as a one-time analysis you act on internally, a recurring
quarterly engagement, or a live tool that updates weekly or
monthly?"**

*Why we ask*: This is the Path A/B/C question, asked directly.
*Listen for*:
- "Once would be useful" → Path B
- "Quarterly seems right" → Path B
- "I'd want it always on" → Path A
- "Could it plug into our ERP?" → Path C

*What answer kills the bet*: "I'd want all three at once but only
if you build them in the next 60 days." (Wrong expectations.)

### Mutual fit (Q15)

**Q15 — "If we wanted to run a 30-day paid diagnostic with your
data — five CSV exports from your systems — what would the
process look like inside your team to make that happen?"**

*Why we ask*: Surfaces real-world objections (IT, legal, data
privacy, internal champion). If they engage seriously, you
have a buyer. If they hand-wave, you don't.
*Listen for*: "I'd need to talk to [boss/CFO]", "We'd want an
NDA", "Our data team would need to pull the exports",
"What's the price range?"
*What answer kills the bet*: "Yeah, send me a proposal." (Likely
brush-off. Press for who else would be involved.)

---

## Close (2 minutes)

> "This was incredibly useful, thank you. To make sure I heard you
> right: your biggest operational pain is [summarize their top 2–3
> pain points]. You'd prefer the diagnostic as [one-time / recurring
> / live], and the next step on your side to make this real would
> be [their answer to Q15]. Did I miss anything important?"

That summary forces them to confirm or correct. Both are useful.

Then:

> "I'll send you a one-page summary of the diagnostic offer by
> end of day tomorrow. If it makes sense after you read it, we
> can talk about scoping a 30-day pilot. If it doesn't, no
> pressure — I'd just like to come back to you in a quarter or
> two if our offer changes. Sound fair?"

The "no pressure, come back later" framing keeps the door open
even on a no.

---

## Structured note format (fill in immediately after the call)

| Field | Value |
|---|---|
| Operator name | |
| Date | |
| Duration | |
| Segment (produce / seafood / food-bev / fresh-cut / institutional) | |
| Revenue range (estimated) | |
| Tech stack (Q1, Q2) | |
| Multi-site? (Q3) | |
| Lot code system (Q4) | |
| Order/delivery system separation (Q5) | |
| Waste tracking maturity (Q6) | |
| Traceability speed (Q7) | |
| Double-entry severity (Q8) | |
| Hardest report (Q9) | |
| Scaling constraint (Q10) | |
| Overcommitment frequency (Q11) | |
| Waste dollar visibility (Q12) | |
| Willingness to pay (Q13) — direct quote | |
| Stated path preference (Q14) — A / B / C | |
| Path forward (Q15) | |
| Pain language they used (verbatim) | |
| Pilot likelihood (1–5) | |
| Next step + date | |

The "Pain language they used" field is the single most important
note. Operator's own words become the language we use in subsequent
outreach. Don't paraphrase. Capture verbatim.

---

## Pattern recognition across calls

After each call, update a master tracker with:

| Question | Operator A | Operator B | Operator C | ... |
|---|---|---|---|---|

After 5 calls, look for patterns:

- **Same tech stack repeating?** → Standardize a connector for that stack
- **Same hardest-report answer?** → Make that the front-page output of the diagnostic
- **Same Q14 answer?** → That's the path the market is pulling toward
- **Different segments saying same things?** → Diagnostic generalizes
- **Same segment saying different things?** → Need more segment depth

---

## Red flags to walk away from

| Signal | Likely meaning |
|---|---|
| Operator brings their CTO/IT lead to the call | They're evaluating you as a vendor, not as a discovery partner. Either pivot to a vendor pitch or end gracefully. |
| Operator dominates the conversation pitching their own startup | They're not a buyer; they're a competitor. End politely. |
| Operator asks for free pilot or "we'll be your reference" | Procurement red flag. Free customers don't commit; they extract. Politely name the paid pilot price. |
| Operator says "we'd use it but only if it's free" | Not a real buyer. |
| Operator's answers to Q4, Q5, Q6 are all "we have that solved" | They don't have the problem. End the call early and ask who else in their network might. |

---

## Green flags worth doubling down on

| Signal | What to do |
|---|---|
| Operator answers Q8 with a direct dollar estimate of double-entry labor cost | They've thought about this; they're a buyer. Send the pilot offer within 24 hours. |
| Operator names a specific buyer asking for traceability records (Sysco, Cisco, named hospital network) | Compliance urgency is real. Reference the named buyer in follow-up. |
| Operator names a specific number for willingness to pay | Their number is your floor. Anchor the pilot price within it. |
| Operator offers to introduce you to a peer at end of call | Strong signal. Accept on the spot. |
| Operator wants the next call to include a more senior person | Procurement is moving. Schedule within 7 days. |

---

## Pitfall: do not pitch the product on a discovery call

The temptation to pitch is strongest when the operator says
something that maps perfectly to a HarvestMind module. Resist.

Bad version:
> "Oh, that's exactly what our traceability module shows!
> Let me walk you through it..."

Good version:
> "Tell me more about that — when did you start noticing it?"

The product pitch comes in the **follow-up email after the call**,
not during the call. Use the call to extract their language. Use
the follow-up to reflect their language back to them with the
diagnostic offer attached.

---

## What to do after the call

- Within 1 hour: complete the note template above
- Within 24 hours: send a thank-you email summarizing the top 2
  pain points (using their verbatim language) plus the one-page
  diagnostic offer
- Within 3 days: send any follow-up data they requested (sample
  report excerpt, NDA template, etc.)
- After 7 days of no reply: one single follow-up: "Following up —
  any questions on the offer?"
- After 14 days: move to "pause", revisit in 60–90 days
