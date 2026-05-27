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

> "Most regional produce operators leak margin to waste, missed orders, and
> last-minute substitutions — and they don't see those numbers anywhere.
> HarvestMind is a diagnostic that takes the CSV exports an operator already
> produces and turns them into a board-readable report on where that margin
> is going. I'll show you in five minutes."

Pause. Share screen. Show the Upload page.

---

## 0:15 — The data shape (30 seconds)

> "HarvestMind needs five files — products, supplier deliveries, inventory
> lots, buyer orders, and a waste log. These are the same exports an operator
> already pulls out of QuickBooks, an ERP, or a picking spreadsheet. No
> integration. No IT project. CSV in, diagnostic out."

Point at the five status cards (all gray, zero rows).

> "I'll load a sample dataset so you can see what the diagnostic looks like
> against real-shaped data. Two important caveats up front: the sample is
> intentionally messy — one low-performing supplier, near-expiry lots, two
> lots missing their lot ID. And the dollar numbers in this sample are very
> small because the dataset is very small. The point of the demo is to show
> you the shape of the analysis, not to imply real-operator savings."

---

## 0:45 — Load sample (15 seconds)

Click **Load sample dataset**.

> "Two seconds. Five tables loaded. Now I'll walk through the diagnostic."

Wait for the chips to turn green.

Navigate to the Overview page.

---

## 1:00 — Overview (45 seconds)

> "Top of the page — total waste loss, total shortage loss, risky suppliers,
> traceability completeness. The red banner at the top is the period
> addressable total — the dollar figure that summarizes 'this is how much
> money this period leaked through these four categories' for whatever
> period the data spans."

Point at the banner.

> "Top loss drivers on the left — the specific products and reasons driving
> that loss. Savings opportunity on the right — annualized and shown as a
> range, 15 to 30 percent reduction of addressable loss, sourced from USDA
> SR-77 research benchmarks. That's the conversation-starter figure, not a
> guarantee."

Click the **Data Quality** sidebar item briefly.

> "We also score the data itself. If the data is incomplete, we tell the
> operator what's missing before we run the diagnostic, so we don't generate
> false confidence in numbers built on holes."

---

## 1:45 — Inventory Risk (45 seconds)

Navigate to **Inventory Risk**.

> "This is the on-hand picture. Total on-hand, near-expiry — anything within
> three days of expiry — and expired stock that's still in the file. Most
> operators are surprised by their own near-expiry percentage when they see
> it as a share of total stock."

Point at the "Inventory by Product" table.

> "Per-product. So the GM can ask 'why is 18 percent of our tomato stock
> within three days of expiry' and we can answer with the specific lots."

---

## 2:30 — Available-to-Promise (45 seconds)

Navigate to **Available-to-Promise**.

> "This is the action layer. Available-to-promise is on-hand minus
> committed minus expired minus near-expiry. It's the number that should
> be on the screen when a buyer calls and asks 'can you commit 500 kilos
> for Thursday?' "

Point at the **Commitment Recommendations** table.

> "For risky products, we don't just show a number — we show a safe commit
> figure and a holdback, with a one-line reason. This is the kind of output
> that, if it's useful, would get used in a morning operations meeting."

---

## 3:15 — Partners (45 seconds)

Navigate to **Partners**, **Suppliers** tab.

> "Supplier reliability. Each supplier ranked by fill rate. This supplier —
> 62 percent fill rate — would be a high-risk relationship that's likely
> costing the operator real money in substitutions and missed orders."

Click the **Buyers** tab.

> "Same view on the buyer side — which buyers do we keep missing orders
> for? Most operators carry this in their head but haven't tied it to a
> dollar number."

---

## 4:00 — Traceability (30 seconds)

Navigate to **Traceability**.

> "FSMA-204 readiness — what percent of lots have all six required trace
> fields. This number matters because if the operator ships to a buyer
> on the FDA Food Traceability List, this is the number that buyer is
> going to ask for."

Point at the incomplete-lots table.

> "And here are the specific lots that fail. Those missing lot IDs would
> be a problem in an audit, today."

---

## 4:30 — The report (20 seconds)

Navigate to **Reports**. Open the HTML report.

> "Everything we just looked at gets compiled into a thirteen-section
> report. Board-readable. Printable. Has an assumptions and limitations
> section so the GM can defend the numbers. This is the deliverable for
> a paid diagnostic engagement."

Scroll past sections quickly. Stop at the Savings box and the Assumptions
section.

---

## 4:50 — The ask (10 seconds)

Stop sharing.

> "That's the demo. The question I have for you is — would this be useful
> if it used your real data instead of our sample? And if it would, which
> of these would be most valuable: a one-time analysis, recurring
> quarterly diagnostics, or a live tool connected to your existing
> system?"

Stop talking. Let them answer. The closing question is the entire point
— it's how we find out which business model the market is pulling us
toward.

---

## Q&A — Anticipated questions and honest answers

**Q: How long to set this up with our data?**
A: First diagnostic takes 30 days. Week 1 is data intake, week 2–3 is
analysis, week 4 is the readout.

**Q: What does it cost?**
A: $3,000–$7,500 for the diagnostic depending on scope. For larger
operators we'd quote $10K–$15K. Pricing for ongoing service depends on
what the diagnostic reveals you actually need — that's the closing
question.

**Q: How much could you save us?**
A: Honest answer — we don't know yet. We have a diagnostic engine that
quantifies waste, shortage, and traceability gaps from your actual data.
Industry research (USDA SR-77) suggests 15–30% of addressable loss is
typically recoverable by operators who act on this kind of analysis.
Whether the dollar figure in your specific case is large enough to justify
ongoing investment is what the diagnostic itself would answer.

**Q: Is our data going to a cloud somewhere?**
A: No. The MVP runs locally. For pilots we deploy a dedicated instance
for your data, never shared.

**Q: Can it talk to our QuickBooks / ERP?**
A: Not today. The wedge is CSV-in. Integration is a future question
that depends on whether the diagnostic is valuable enough to you to
make integration worth building.

**Q: What about AI?**
A: There's no LLM in the diagnostic. It's deterministic math on operator
data so the report is auditable. We deliberately don't use the word "AI".

**Q: Who else are you working with?**
A: We are at the pre-customer stage. The MVP is built, but the first
paid diagnostics are still ahead of us. That is exactly why we are
having this conversation — to find an operator willing to be in that
first cohort.

**Q: What's the catch?**
A: We are a Purdue student team. We have a working product, not a sales
organization. The diagnostic engine works, but we have not yet validated
which version of the product (one-time analysis, recurring service, or
live tool) is what operators actually want. The first three paid
diagnostics will tell us. We are honest about that.

---

## What to never say during the demo

- "AI" or "machine learning"
- "Optimization" without explanation — say "diagnostic" or "recommendation"
- "Platform" — say "tool" or "diagnostic"
- "Disrupt" — say "fits alongside your existing system"
- A revenue, customer, or savings claim grounded in anything other than
  the sample dataset
- "We've validated this with [N] operators" — we haven't
- The phrase "we'll save you $X" — that's a sample-data sentence and
  doesn't generalize
