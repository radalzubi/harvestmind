# Five-Minute Demo Script

**Audience**: Operator GM/Ops Manager, or an advisor evaluating product fit
**Length**: 5 minutes of demo + 2 minutes of Q&A
**Pre-flight**: Backend running on :8000, frontend running on :3000, browser
already open to `/upload`, sample data **not yet loaded** so the audience sees
the empty-state-to-loaded transition.

Read this script aloud once before the call. Do not improvise the opening or
the closing — those are the parts that get cut wrong under pressure.

---

## 0:00 — Opening (15 seconds)

> "Most regional food hubs lose 5 to 15 percent of gross margin to waste,
> missed orders, and last-minute substitutions — and they don't see those
> numbers anywhere. HarvestMind is a diagnostic that takes the CSV exports a
> hub already produces and turns them into a board-readable report on where
> that margin is going. I'll show you in five minutes."

Pause. Share screen. Show the Upload page.

---

## 0:15 — The data shape (30 seconds)

> "HarvestMind needs five files — products, supplier deliveries, inventory
> lots, buyer orders, and a waste log. These are the same exports a hub
> already pulls out of QuickBooks or its picking spreadsheet. No ERP
> integration. No IT project. CSV in, diagnostic out."

Point at the five status cards (all gray, zero rows).

> "I'll load a sample dataset so you can see what the diagnostic looks like
> against real-shaped data. The sample is intentionally messy — one
> low-performing supplier, a couple of near-expiry lots, two lots missing
> their lot ID."

---

## 0:45 — Load sample (15 seconds)

Click **Load sample dataset**.

> "Two seconds. Five tables loaded. Now I'll walk through the diagnostic."

Wait for the chips to turn green.

Navigate to the Overview page.

---

## 1:00 — Overview (45 seconds)

> "Top of the page — total waste loss, total shortage loss, risky suppliers,
> traceability completeness. The red banner at the top is the addressable
> total — the dollar figure that summarizes 'this is how much money this
> period leaked through these four categories.'"

Point at the banner.

> "Top loss drivers on the left — the specific products and reasons driving
> that loss. Savings opportunity on the right — annualized at a 30 percent
> reduction assumption, which comes from USDA research benchmarks. That's
> the conversation-starter figure."

Click the **Data Quality** sidebar item briefly.

> "We also score the data itself. If a hub uploads incomplete data, we tell
> them what's missing before we run the diagnostic, so we don't generate
> false confidence."

---

## 1:45 — Inventory Risk (45 seconds)

Navigate to **Inventory Risk**.

> "This is the on-hand picture. Total on-hand, near-expiry — anything within
> three days of expiry — and expired stock that's still in the file.
> Most operators are surprised by their own near-expiry number when they
> see it as a percentage of total stock."

Point at the "Inventory by Product" table.

> "Per-product. So the GM can ask 'why is 18 percent of our tomato stock
> within three days of expiry' and we can answer with the specific lots."

---

## 2:30 — Available-to-Promise (45 seconds)

Navigate to **Available-to-Promise**.

> "This is what we call the action layer. Available-to-promise is on-hand
> minus committed minus expired minus near-expiry. It's the number the
> hub should actually use when a buyer calls and asks 'can you commit 500
> kilos for Thursday?'"

Point at the **Commitment Recommendations** table.

> "For risky products, we don't just show a number — we show a safe commit
> figure and a holdback, with a one-line reason. This is what gets used in
> the morning operations meeting."

---

## 3:15 — Partners (45 seconds)

Navigate to **Partners**, **Suppliers** tab.

> "Supplier reliability. Each supplier ranked by fill rate. This supplier —
> 62 percent fill rate — is a high-risk relationship that's likely costing
> the hub real money in substitutions and missed orders."

Click the **Buyers** tab.

> "Same view on the buyer side — who do we keep missing orders for?
> Operators usually know this in their head, but they've never seen it as
> a dollar number tied to a specific buyer."

---

## 4:00 — Traceability (30 seconds)

Navigate to **Traceability**.

> "FSMA-204 readiness — what percent of our lots have all six required
> trace fields. This number matters because if the hub ships to a buyer
> that's on the FDA Food Traceability List, this is the number the buyer
> is going to ask for."

Point at the incomplete-lots table.

> "And here are the specific lots that fail. Those two missing lot IDs
> would be a problem in an audit, today."

---

## 4:30 — The report (20 seconds)

Navigate to **Reports**. Open the HTML report.

> "Everything we just looked at gets compiled into a thirteen-section report.
> Board-readable. Printable. Has an assumptions and limitations section so
> the GM can defend the numbers. This is the deliverable for the diagnostic
> pilot."

Scroll past sections quickly. Stop at the Savings box and the Assumptions
section.

---

## 4:50 — The ask (10 seconds)

Stop sharing.

> "That's the demo. The question I have for you is — would this be useful
> if it used your real data instead of our sample? If yes, we'd like to
> talk about a 30-day paid diagnostic with your CSV exports."

Stop talking. Let them answer.

---

## Q&A — Anticipated questions and short answers

**Q: How long to set this up with our data?**
A: First diagnostic takes 30 days. Week 1 is data intake, week 2–3 is analysis,
week 4 is the readout. After that, weekly refreshes are automated.

**Q: What does it cost?**
A: The diagnostic pilot is $3,000 to $7,500 depending on product line count.
Live SaaS afterward is $1,500–$3,000 per month. We'd give you a fixed quote
after seeing your data shape.

**Q: Is our data going to a cloud somewhere?**
A: No. The MVP today runs locally. For pilots we deploy a dedicated instance
for your data with no shared multi-tenant storage.

**Q: Can it talk to our QuickBooks?**
A: Not today. The wedge is CSV-in. ERP integrations are a phase-two question
once we know the diagnostic is valuable to you.

**Q: What about AI?**
A: There's no LLM in the diagnostic. It's deterministic math on operator data
so the report is auditable. We don't use the word AI deliberately.

**Q: What's the catch?**
A: Two honest catches. One — you have to actually export the CSVs. That's
real operator time. Two — we are a student team. We have a working product,
not a sales organization. If you want hand-holding at scale, that's not us
today.

---

## What to never say during the demo

- "AI" or "machine learning" — we don't use either
- "Optimization" without explanation — say "diagnostic" or "recommendation"
- "Platform" — say "tool" or "diagnostic"
- "Disrupt" — say "fits alongside QuickBooks"
- "Just" as in "we just need your data" — never minimize the ask
- A revenue or user number — we have none, do not invent any
