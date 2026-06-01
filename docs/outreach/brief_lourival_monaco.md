# HarvestMind: A Diagnostic Engine for Perishable Food Operators
### From Messy Spreadsheet Exports to Operational Intelligence

---

**CONCEPT**

Regional produce operators — food hubs, aggregators, fresh distributors, and seafood wholesalers — manage supply commitments, inventory, and buyer fulfillment almost entirely through spreadsheets and institutional memory. When they over-commit and waste product, or under-commit and miss an institutional order, that cost disappears into low gross margin rather than appearing as a named line item anywhere. HarvestMind ingests the five CSV files any operator already exports from their existing systems and returns a board-readable report quantifying where that margin went — in dollars, by product, by supplier, and by buyer. No integration, no IT project, no change to existing workflows. CSV in, diagnostic out. The question we are trying to answer through the first 3–5 paid pilots is whether the strongest business model is recurring SaaS, a productized quarterly diagnostic, or an intelligence add-on for operators already on ERPs like Famous or Produce Pro.

---

**THE PROBLEM**

BCG's 2025 agrifood resilience report identifies coordination failure — not just climate — as the primary driver of supply chain fragility in fresh food. McKinsey estimates that close to three-quarters of supply chain functions still rely on spreadsheets for demand planning, and that this is as true at the $5M regional food hub level as it is at larger distributors. The operators who feel this most acutely are the ones your 2025 Climate-Smart Agrifood report maps to the distribution node of the value chain: aggregators and regional distributors handling perishables without the ERP infrastructure that larger players have. The pain is real. A Reddit thread from an oyster farm operator — $1M+ in revenue — described double and triple order entry, lot codes on paper, harvest tags disconnected from inventory, QuickBooks integration that breaks under volume, and software issues that were actively blocking growth. That operator, and thousands like them, have no tool built for their problem.

---

**WHAT WE HAVE BUILT**

HarvestMind is a working MVP. Five staging tables accept messy operator CSVs. A diagnostic engine computes waste loss in dollars, shortage loss in dollars, supplier fill rate and rejection rate with risk tiers, buyer fulfillment rates, FSMA-204 traceability completeness, and available-to-promise recommendations by product. A 13-section HTML report is printable and board-readable. A one-click sample dataset loader lets anyone run a full demo in two seconds. 296 backend tests pass. The frontend is deployed at a private URL. The code is on GitHub. The math was formally audited — the savings module annualizes correctly from the operator's actual data window, and the ATP formula now properly excludes near-expiry stock from committable quantities. This is not a prototype. It is a demo-ready MVP with no customers yet.

---

**WHY THIS CONNECTS TO DIAL'S MISSION**

Your Climate-Smart Agrifood report maps digitization opportunities across six value-chain nodes. HarvestMind operates at the distribution node — where food waste, traceability gaps, and fulfillment failures actually occur and where the existing digital layer is thinnest. The DIAL mission is to build digital-native companies that help the agrifood system catch up to where it needs to be. The specific problem HarvestMind addresses — operators making supply commitment decisions with no data-driven decision layer — is precisely the coordination failure that BCG and your own research identify as the primary driver of value-chain fragility. The regulatory context (FSMA-204 compliance target July 20, 2028) is also creating new pressure on operators to clean and structure the traceability data that HarvestMind uses as its input. Compliance is the data-cleaning trigger. Operational intelligence is the ongoing value.

---

**TWO QUESTIONS FOR YOU**

**1. Is the diagnostic-first wedge the right commercial entry point?**
We have built the diagnostic before the optimizer on the theory that operators need to trust the output before they will trust a recommendation. Your work on digital transformation success factors in agrifood — and your experience with DIAL cohort companies — suggests you have a view on whether this sequencing is right, or whether there is a different entry point that converts faster. Is a $3K–$15K paid diagnostic the right first product for operators at the $2M–$20M revenue range, or is there a different offer that would be more natural for this segment?

**2. Does DIAL's network include the operators we need?**
The most valuable thing for us right now is one warm introduction to a perishable operator — food hub, fresh distributor, seafood wholesaler, fresh-cut processor — who would be willing to share 6–12 months of operational data for a structured paid diagnostic. We are not looking for a funding conversation. We are looking for the operator who will tell us whether the diagnostic findings are directionally accurate — and whose response to the report will tell us which business model this should become.

---

**IF THIS RESONATES**

We are at an early and honest stage: working product, no customers, three plausible business paths, and a genuine need for someone who has seen enough agrifood startups to tell us which path is real. Whether that means a 25-minute meeting to pressure-test the wedge, an introduction to one operator or advisor, or a conversation about whether this belongs in the DIAL ecosystem — we would be grateful for any time you are willing to give it.

If there is mutual fit later, we would be open to a formal advisor relationship through the proper Purdue conflict-of-interest and intellectual-property process.

---

**Rad AlZubi**
Industrial Engineering · Minor: Management
Purdue University, graduating December 2026
Supply chain operations experience
(312) 900-2705 · alzubi@purdue.edu

**Mustafa Sabieha**
Industrial Engineering · Minor: Management
Purdue University, graduating May 2026
Pharmaceutical manufacturing experience
(765) 269-0655 · msabieha@purdue.edu
