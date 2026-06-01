# Safe Supply Commitments for Perishable Food Networks
### Decision Support Under Yield Uncertainty and Shelf-Life Constraints

---

**CONCEPT**

Regional produce operators — food hubs, aggregators, and fresh distributors — commit supply to institutional buyers before they know what their suppliers will actually deliver. Once those commitments are made, the window for correction is narrow. A delivery that comes in 20% short, a lot that expires two days before delivery, or a supplier whose fill rate collapses mid-season all create the same outcome: the operator either wastes product they scrambled to find or misses the order entirely. The current state of the art for this decision is a spreadsheet and a phone call. We believe the right framing is a two-stage stochastic model that treats supplier delivery as the uncertain first stage and buyer commitment as the decision variable to be optimized before that uncertainty resolves.

---

**THE PROBLEM**

The planning gap is structural. ERP systems and inventory trackers operate after the commitment is made — they record what happened, not what should have been promised. The pre-commitment window, where the operator is deciding how much to promise to which buyer given uncertain upstream supply, has no formal decision-support layer in common use. McKinsey estimates that close to three-quarters of supply chain functions still rely on spreadsheets for demand planning. In perishable food distribution, the cost of getting this decision wrong is not abstract: it is either spoiled inventory or a missed institutional order. For a $5M regional food hub operating at 18% gross margin, a 5% improvement in commitment accuracy is material.

---

**OUR APPROACH**

We have built a working diagnostic engine — HarvestMind — that ingests five CSV files from any operator's existing system and produces waste loss, shortage loss, supplier reliability scores, and available-to-promise recommendations by product. The system currently uses deterministic thresholds: a supplier with a 62% historical fill rate gets a 15% holdback applied to its available quantity. That is correct direction but the wrong model. It treats historical fill rate as a point estimate rather than a distribution. It does not account for fill-rate variance — a supplier averaging 62% who is consistently 62% is a different risk than one who alternates between 40% and 85%. It does not model the time-to-expiry decay that makes a near-expiry lot a fundamentally different commitment risk than a fresh one. The right upgrade is a chance-constrained or robust formulation: commit no more than Q kg such that the probability of a downstream shortfall is below some threshold p, given a supplier delivery distribution estimated from historical records.

---

**WHY THIS CONNECTS TO YOUR WORK**

Your research on machine learning for constrained optimization and robust supply chain design addresses exactly the class of problems we are sitting inside. The specific gap we are trying to close — moving from deterministic thresholds to a distribution-aware commitment model for a small operator with limited historical data — is a practical instantiation of the robust/chance-constrained framing you have published on. The applied constraint is real: our operators may have as few as 3–8 delivery records per supplier per season, which is too little for classical distribution fitting but not necessarily too little for a robust formulation with the right uncertainty set.

---

**TWO QUESTIONS FOR YOU**

**1. Robust versus chance-constrained for thin-data settings.**
Our operators often have very short supplier histories — sometimes as few as 3 deliveries in a season. In your experience with robust and stochastic optimization models, what is the right formulation when the uncertainty set cannot be estimated from data with confidence? Is a distribution-free robust approach more appropriate than a chance-constrained one when sample size is this small, or does the structure of the problem (perishable goods, bounded delivery quantities) give enough to work with?

**2. Incorporating perishability into the commitment decision.**
Current ATP logic treats all non-expired inventory as equally committable. A lot with 10 days of shelf life and a lot with 2 days are treated identically as long as neither is expired yet. The right model should discount near-expiry inventory's commitment value as a function of delivery lead time. Have you seen clean formulations of shelf-life decay inside a supply commitment or allocation model — and at what level of complexity does it remain deployable for a small-operator context?

---

**IF THIS RESONATES**

We are at the point where the deterministic version works and produces defensible output, but we know it is not yet mathematically rigorous as a planning model. We would genuinely value 25 minutes of your time to pressure-test the model framing and understand whether the upgrade path we are describing is the right one — or whether there is a cleaner formulation we are not seeing. We are not looking for a commitment of any kind. Just honest technical feedback from someone whose work sits directly on top of this problem.

If there is mutual fit later, we would be open to a formal research collaboration or advisor relationship through the proper Purdue COI/IP process.

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
