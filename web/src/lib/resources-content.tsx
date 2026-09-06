import type { ReactNode } from "react";

/**
 * Article bodies. Written for practitioners; every quantitative claim is either standard
 * textbook material with a source below, or explicitly qualified. No customer results, no
 * savings figures, no invented case studies.
 */
export type Source = { label: string; href: string; note?: string };
export type ArticleBody = { body: ReactNode; sources: Source[] };

const silver = { label: "Silver, Pyke and Thomas, Inventory and Production Management in Supply Chains, 4th ed. (CRC Press, 2016)", href: "https://doi.org/10.1201/9781315374406", note: "the standard treatment of reorder points, safety stock and service measures" };
const hopp = { label: "Hopp and Spearman, Factory Physics, 3rd ed. (Waveland Press, 2011)", href: "https://www.waveland.com/browse.php?t=453", note: "variability laws: how lead-time and demand variability translate into inventory" };
const graves = { label: "Graves and Willems, \"Optimizing Strategic Safety Stock Placement in Supply Chains\", Manufacturing & Service Operations Management 2(1), 2000", href: "https://doi.org/10.1287/msom.2.1.68.23267", note: "the guaranteed-service model behind most MEIO software" };
const clark = { label: "Clark and Scarf, \"Optimal Policies for a Multi-Echelon Inventory Problem\", Management Science 6(4), 1960", href: "https://doi.org/10.1287/mnsc.6.4.475", note: "the origin of echelon stock and multi-echelon base-stock policies" };
const sheffi = { label: "Sheffi, The Resilient Enterprise (MIT Press, 2005)", href: "https://mitpress.mit.edu/9780262693493/the-resilient-enterprise/", note: "disruption profiles, redundancy versus flexibility" };
const simchi = { label: "Simchi-Levi, Schmidt and Wei, \"From Superstorms to Factory Fires: Managing Unpredictable Supply-Chain Disruptions\", Harvard Business Review, January 2014", href: "https://hbr.org/2014/01/from-superstorms-to-factory-fires", note: "time-to-recover and time-to-survive as the resilience measures that matter" };
const rockafellar = { label: "Rockafellar and Uryasev, \"Optimization of Conditional Value-at-Risk\", Journal of Risk 2(3), 2000", href: "https://doi.org/10.21314/JOR.2000.038", note: "the linear formulation of tail-risk constraints used in scenario optimization" };
const kaplan = { label: "Kaplan and Meier, \"Nonparametric Estimation from Incomplete Observations\", Journal of the American Statistical Association 53(282), 1958", href: "https://doi.org/10.1080/01621459.1958.10501452", note: "estimating lead-time distributions when some orders have not yet arrived" };
const cusum = { label: "Page, \"Continuous Inspection Schemes\", Biometrika 41(1/2), 1954", href: "https://doi.org/10.1093/biomet/41.1-2.100", note: "the CUSUM change detector" };
const birge = { label: "Birge and Louveaux, Introduction to Stochastic Programming, 2nd ed. (Springer, 2011)", href: "https://doi.org/10.1007/978-1-4614-0237-4", note: "two-stage and multi-stage stochastic programs, the value of the stochastic solution" };
const schwartz = { label: "Schwarz, Ward and Zhang, \"On the Interactions between Routing and Inventory-Management Policies in a One-Warehouse N-Retailer Distribution System\", Manufacturing & Service Operations Management 8(3), 2006", href: "https://doi.org/10.1287/msom.1060.0111", note: "one-warehouse, multi-retailer distribution networks" };

function P({ children }: { children: ReactNode }) { return <p>{children}</p>; }

export const CONTENT: Record<string, ArticleBody> = {
  "what-is-inventory-optimization-for-distributors": {
    body: (
      <>
        <P>A distributor's inventory problem is not "how much stock should I hold". It is "what should I order, from whom, and when, so that the customers I have promised to serve are served, without tying up more working capital than the business can carry". Inventory optimization is the discipline of answering that question with the operator's own data rather than with a rule of thumb.</P>
        <h2>What it decides</h2>
        <P>At minimum, an inventory optimization system decides three things for every SKU at every stocking location: the timing of the next purchase order, its quantity, and the source it goes to. In a distribution business that also holds stock at more than one site, it decides transfers between sites. Where a customer has approved a substitute product, it decides whether to serve a shortage with the substitute. Every one of those decisions competes for the same cash and the same supplier and warehouse capacity, which is why they are optimized together rather than SKU by SKU.</P>
        <h2>How it differs from forecasting</h2>
        <P>A forecast estimates demand. It is an input, and an uncertain one. Inventory optimization takes the forecast, its uncertainty, the supplier's lead-time and fill behaviour, the customer's service commitment, and the cost of holding, expediting and missing a sale, and turns them into a decision. Two distributors with the same forecast should place different orders if one has a reliable local supplier and the other imports through a single port. Treating a point forecast as truth is the most common way to end up lean at exactly the wrong time.</P>
        <h2>How it differs from reorder points</h2>
        <P>Reorder-point systems (order Q when stock falls to R) are inventory optimization in a narrow form: R and Q are chosen once from average demand, average lead time and a service target. The textbook treatment (Silver, Pyke and Thomas) is still the right place to learn the mechanics. What a static reorder point cannot do is respond when the supplier's lead-time distribution widens, when a strategic customer's demand shifts, or when cash is constrained this month. Modern optimization re-solves the whole plan at each review with the latest evidence.</P>
        <h2>What evidence a distributor should demand</h2>
        <P>Before changing how a business orders, an operator should insist on a replay: take the last year of purchase orders, receipts, sales and stock counts, reconstruct what the current policy did, and run the candidate policy through the same history under many plausible futures. The comparison that matters is not the average saving but the conservative lower bound and the service achieved on held-out weeks. A candidate that only wins on average, or wins only on the weeks it was tuned on, has not earned the right to change anything.</P>
        <P>Two warning signs in any vendor conversation: a promised saving before the data has been seen, and a service level that is quoted without saying which metric (unit fill, line fill, order fill or on-time-in-full) it refers to. These are different numbers and they move differently.</P>
        <h2>Where it pays and where it does not</h2>
        <P>Optimization pays most where uncertainty is large and expensive: long import lanes, suppliers that short-ship, customers with hard service commitments and high-margin lines. It pays least on SKUs with short, reliable replenishment and low margin, where a simple rule is close to optimal and the cost of being wrong is small. A good system should say so, SKU by SKU, and stay lean where lean is safe.</P>
      </>
    ),
    sources: [silver, hopp, birge],
  },

  "safety-stock-vs-inventory-optimization": {
    body: (
      <>
        <P>Safety stock is the inventory held above expected demand over the replenishment lead time, to absorb the variability in demand and supply. The classic formula sizes it as a safety factor times the standard deviation of demand over the lead time: <code>SS = z · σ<sub>DL</sub></code>, where <code>z</code> comes from the service target (about 1.65 for a 95% cycle-service level under a normal approximation) and <code>σ<sub>DL</sub></code> combines demand and lead-time variability. When lead time itself varies, the standard extension is <code>σ<sub>DL</sub>² = L · σ<sub>D</sub>² + D² · σ<sub>L</sub>²</code>. The derivations are in Silver, Pyke and Thomas.</P>
        <h2>Where the formula holds</h2>
        <P>The formula is a good approximation when demand is roughly normal, lead time is stable, the supplier delivers what was ordered, and one service target applies to the SKU. Many fast-moving lines at a distributor with a local supplier fit this description well enough. For them, a well-set safety stock is close to optimal and there is little to gain from anything more elaborate.</P>
        <h2>Where it breaks for distributors</h2>
        <P>Four things common in distribution and import break the formula's assumptions.</P>
        <P><b>Suppliers that short-ship.</b> If a supplier accepts an order for 100 and delivers 85 on average, the expected receipt is lower and its variance is higher than the order suggests. The formula has no term for fill rate; the effective lead-time demand it should protect against is larger.</P>
        <P><b>Lead times with a tail.</b> An import lane that usually takes three weeks but occasionally takes six has a lead-time distribution that is not symmetric. The <code>σ<sub>L</sub></code> term understates the tail; the right quantity to protect against is the lead time at the required quantile, not the standard deviation.</P>
        <P><b>One SKU, several service commitments.</b> A supermarket contract at 99% and a spot customer at 90% are two different protection problems on the same stock. A single safety factor either over-protects the spot customer or under-protects the contract. Protection has to be sized by the customers who will actually be served first when stock is short.</P>
        <P><b>Alternatives and shared exposure.</b> An approved second supplier or a transfer from another branch reduces the protection a SKU needs, but only if the alternative is genuinely independent. Two suppliers that ship through the same port are not two sources during a port closure.</P>
        <h2>What scenario-based optimization does instead</h2>
        <P>Instead of a closed-form buffer, a scenario-based optimizer draws many plausible futures for demand, fill and arrival dates, including deliberately adverse ones, and chooses the plan that meets each customer's service target across those futures at least cost. Protection is then an output, not a parameter. It is larger where the scenarios spread (a supplier whose observed lead times have widened) and smaller where they are tight (a short, reliable lane with a substitute on the shelf). A tail-risk constraint such as conditional value-at-risk, in the linear form due to Rockafellar and Uryasev, makes the worst share of scenarios count, not just their average.</P>
        <h2>A practical test</h2>
        <P>Ask the system to explain, per SKU, why it holds what it holds: "supply tail widened", "strategic customer at 99%", "shared port with the alternate", or "not needed: two independent sources within one week". If it cannot, it is a buffer factor with a nicer interface.</P>
      </>
    ),
    sources: [silver, hopp, rockafellar],
  },

  "planning-inventory-during-supply-disruptions": {
    body: (
      <>
        <P>A disruption is a period in which supply from one or more sources is late, short or absent for longer than the normal variation allows. Sheffi's account of how firms weather disruptions, and Simchi-Levi's time-to-recover and time-to-survive measures, are the right frame: the question is not whether a disruption will happen, but how long the business can serve its customers when it does, and how quickly it can restore normal supply.</P>
        <h2>Before: know your exposure</h2>
        <P>Map every SKU to its sources and every source to the nodes it depends on: supplier plant, port of loading, carrier, transhipment hub, border, port of discharge, receiving warehouse. Two suppliers that share a node share a failure. Count the effective number of independent sources per SKU, weighted by how much capacity each can actually provide, and rank SKUs by the product of exposure, margin and customer commitment. This is the list that deserves protection; most of the range does not.</P>
        <h2>During: a sequence, not a panic</h2>
        <P><b>1. Reposition before buying.</b> Stock already inside the network is the cheapest supply there is. Before an emergency purchase, check whether a transfer from a site with excess can cover the shortage without creating a worse one there. Transfer lead time, receiving capacity and shelf life all bound what is feasible.</P>
        <P><b>2. Allocate by commitment.</b> When stock is short, serve the customers with the highest priority and contractual targets first, and say so. A recovery plan that raises a strategic customer's service by lowering a spot customer's is legitimate; one that quietly does the reverse is not.</P>
        <P><b>3. Use approved alternatives, priced honestly.</b> An alternate supplier, an alternate route, a split order, expediting or an approved substitute each costs something. The right comparison is that cost against the expected shortage avoided plus the reduction in tail exposure. Moving part of an order to a more expensive supplier is worth it when the shortage it prevents is worth more, and not otherwise.</P>
        <P><b>4. Do not fight the last war.</b> One late shipment is not a regime change. Protection should rise with evidence: observed lateness, observed partial deliveries, confirmed route signals. A single abnormal week should move a probability, not the whole plan.</P>
        <h2>After: let protection fall</h2>
        <P>The most common mistake after a disruption is to keep the protection forever. Once the supplier's observed lead times return to normal and the route signal clears, the extra stock is working capital doing nothing. A plan that cannot come back to lean is not resilient, it is just expensive.</P>
        <h2>What to measure</h2>
        <P>Service achieved against target, by customer class; the share of misses that were avoidable (a feasible action existed) versus unavoidable (nothing feasible could have met the target); inventory in periods of demand; the number of emergency actions; and the time from the first missed period to full service. Track these separately from cost savings, because a plan can save money and fail every one of them.</P>
      </>
    ),
    sources: [sheffi, simchi, hopp],
  },

  "multi-echelon-inventory-optimization-explained": {
    body: (
      <>
        <P>A distributor with a central warehouse feeding branches has a multi-echelon network: stock at the centre and stock at the branches protect the same customers, and a decision at one level changes what the other level needs. Multi-echelon inventory optimization (MEIO) is the family of methods that set stock across those levels together instead of treating each site as its own independent supplier.</P>
        <h2>Where the idea comes from</h2>
        <P>Clark and Scarf showed in 1960 that for a serial system the right quantity to control is the echelon stock (a site's stock plus everything downstream of it), and that base-stock policies on echelon stock are optimal under their assumptions. Most of what followed, including the one-warehouse, many-retailer results, builds on that observation.</P>
        <h2>The model behind most MEIO software</h2>
        <P>Commercial MEIO tools are largely built on the guaranteed-service model of Graves and Willems. Each stage quotes a guaranteed service time to the next; demand is assumed bounded; safety stock is placed to cover the net replenishment time at each stage. The model is elegant and solvable at scale, and it produces the familiar picture of pooling risk at the centre and holding less at the branches.</P>
        <P>Its assumptions deserve attention in distribution. Bounded demand and guaranteed interstage service are exactly the assumptions a port closure or a supplier outage violates. When the centre cannot receive, the branch's guaranteed service time from the centre is fiction, and the safety stock placed on that basis is short.</P>
        <h2>Network optimization as an alternative</h2>
        <P>A different approach models the network directly: purchases arriving at the centre, transfers on approved lanes to branches, receiving and storage limits at each site, cash and credit shared across all of them, and demand and supply drawn as scenarios rather than bounded. Each review re-solves the whole network. Risk pooling appears as a consequence (the optimizer holds at the centre when that serves several branches cheaply) rather than as a design rule, and disappears when transfers are slow or capacity-limited.</P>
        <P>This is heavier computationally and needs an operator's actual lanes and constraints, which is why it suits a distributor with a handful of sites more than a global manufacturer with hundreds of stages.</P>
        <h2>What to ask any MEIO vendor</h2>
        <P>Does the model know the transfer lead time and receiving capacity between sites, or does it assume instant availability? Does it treat two suppliers through one port as two sources? What happens to the placement when the upstream lane fails? And can it show the value of the multi-echelon placement separately from the value of a transfer it would have made anyway? Counting the same saving twice is easy in this area.</P>
      </>
    ),
    sources: [clark, graves, schwartz],
  },

  "supplier-fill-rate-and-lead-time-variability": {
    body: (
      <>
        <P>Two supplier behaviours do more damage to a distributor's service than demand ever does: shipping less than was ordered, and shipping late. Both are visible in the receipts the business already has. Both are usually summarised by an average, and the average is the wrong number.</P>
        <h2>Fill rate is a distribution</h2>
        <P>A supplier with an 85% average fill might ship 100% most of the time and 40% occasionally, or 85% every time. The first pattern is far more dangerous: the occasional 40% is the week the customer is short. Measure, from goods receipts against purchase orders, the accepted ratio on every order, and look at the whole distribution: the average, the spread, and the probability of a partial delivery below the level that would cause a stockout. Protection should scale with the spread and the partial probability, not with the mean.</P>
        <h2>Lead time has a tail</h2>
        <P>Import lead times are typically right-skewed: most shipments arrive near the quoted date, a few arrive much later. The standard deviation understates the tail. What matters for protection is the lead time at the required quantile (the 90th percentile for a 90% target, roughly) and the probability that an order is late by more than one review period.</P>
        <P>A subtlety: at any moment, some orders are still open. Ignoring them biases the estimate toward the quick arrivals; treating them as if they had arrived fabricates data. The right tool is the Kaplan-Meier estimator, which uses open orders as right-censored observations: it knows the order has taken at least this long, and no more. It also gives the conditional estimate that a planner actually needs: given that this order is already 20 days old and still open, when will it arrive?</P>
        <h2>Why variability costs inventory</h2>
        <P>Hopp and Spearman's variability laws are the compact statement: inventory needed to hit a service level rises with the variability of both demand and replenishment, and the effects compound. A supplier whose lead time doubles in variance while its mean stays the same forces more stock, not because more is being sold but because when it arrives is less certain. The same is true of fill variance.</P>
        <h2>What a planner can do about it</h2>
        <P>Order earlier for the tail rather than more for the mean; split orders between suppliers whose failures are independent; move part of the volume to a more reliable source when the shortage avoided is worth the price difference; expedite only when the economics say so. And treat the supplier's own record as the evidence: a source whose observed tail has widened gets more protection; one whose record is clean does not, however alarming its quote.</P>
        <h2>Measuring it honestly</h2>
        <P>Use the operator's receipts, not the supplier's promises. Keep censored orders as censored. Report the number of records the estimate rests on: a distribution built from four deliveries is a guess with error bars, and the plan should say so.</P>
      </>
    ),
    sources: [hopp, kaplan, silver],
  },

  "reduce-inventory-without-hurting-service-levels": {
    body: (
      <>
        <P>Inventory can be reduced safely only where the protection it provides is not needed. The task is to find those places precisely, rather than cutting a percentage across the board and discovering which customers notice.</P>
        <h2>Where cuts are usually safe</h2>
        <P><b>Short, reliable replenishment.</b> A SKU that can be replenished within one review period from a supplier whose observed lead times and fill are tight needs little protection beyond the demand variation of that one period.</P>
        <P><b>Genuinely independent alternatives.</b> A second approved supplier on a different route, or a branch with excess and a fast transfer lane, reduces the protection the SKU needs. The word genuine matters: shared ports, carriers or plants do not diversify.</P>
        <P><b>Approved substitutes on the shelf.</b> Where a customer has approved a substitute, its stock counts toward the requested SKU's protection at the conversion ratio.</P>
        <P><b>Low-priority demand.</b> Protection sized for a 90% spot customer is smaller than protection sized for a 99% contract. Holding the higher level for everyone is the most common source of excess.</P>
        <h2>Where cuts are not safe</h2>
        <P>Long import lanes with a lead-time tail; suppliers with a record of partial deliveries; SKUs where every source shares a node; strategic customers with contractual service; and any SKU whose demand history is too short or has just shifted to say what normal looks like. A recent level change should widen the uncertainty, not narrow the buffer.</P>
        <h2>The method</h2>
        <P>Replay the candidate policy on the operator's own past year under many plausible futures and under deliberate stress (a supplier at 70% fill, three weeks late, for two months). Accept a leaner plan only if it meets each customer's target on the fitted futures and does not do worse than the current policy under stress. Measure service by the metric the customer uses: unit fill, line fill, order fill or on-time-in-full are different numbers.</P>
        <h2>Two things a leaner plan must still do</h2>
        <P>It must be able to protect again: when a supplier's observed tail widens or a route signal appears, the plan should rebuild protection on that SKU alone, without waiting for a stockout. And it must classify any service miss honestly: unavoidable (no feasible action could have met the target), avoidable (a feasible action was not taken), an economic trade-off the operator explicitly accepted, a model that was wrong, or data that was insufficient. A plan that only reports "service breach" is hiding which of those it was.</P>
      </>
    ),
    sources: [silver, hopp, rockafellar],
  },

  "lean-protect-allocate-recover": {
    body: (
      <>
        <P>Most supply planning advice describes one posture: be lean, or be resilient. A distributor needs both, at different times, on different SKUs. This framework names four states a SKU at a location can be in, what moves it between them, and what a planner should be able to say in each.</P>
        <h2>LEAN</h2>
        <P>The default. Replenishment is short and reliable, alternatives are real, uncertainty is within its normal range, and the customers served do not need more than the stock on hand and inbound. Protection is small and the plan should be able to explain why: "two independent sources within one period, spread within calibration".</P>
        <h2>PROTECT</h2>
        <P>Entered when uncertainty becomes economically dangerous: the supplier's observed lead-time tail widens, partial deliveries rise, a route signal appears, demand shifts up and the new level is not yet confirmed, or a high-commitment customer's exposure grows. Protection is bought early and specifically: order earlier, split the source, hold more of this SKU, not every SKU. The size of the protection follows from the spread of plausible futures and the probability given to the adverse ones, so it is larger for a credible, expensive stress and smaller for a remote one. Page's CUSUM and its descendants are the workhorse for detecting the demand part of this without reacting to one abnormal week.</P>
        <h2>ALLOCATE</h2>
        <P>Entered when the requested service targets are not jointly achievable with the stock and supply that exist. The question changes from "how do we meet every target" to "which customers do we serve first, and by how much do we miss the rest". Priority and contractual targets decide; a plan that raises a lower-priority customer at the expense of a higher one is rejected; and the miss is classified as unavoidable, avoidable, an economic trade-off, a model failure or insufficient data. Cheapness is not a reason to prefer a plan in this state.</P>
        <h2>RECOVER</h2>
        <P>Entered when supply is coming back: open orders are arriving, the supplier's record is normalising, the route signal has cleared. The plan works off the emergency actions, restores the customers that were rationed in priority order, and stops buying protection for a risk that is passing. Time to recover, in Simchi-Levi's sense, is measured here.</P>
        <h2>Back to LEAN</h2>
        <P>The test of the whole framework is the return. If protection built during a disruption is still there a year later, the business has not become resilient, it has become expensive. Protection should disappear when the risk disappears, and the plan should be able to show that it did.</P>
        <h2>Why states, not a dial</h2>
        <P>A single "risk appetite" dial applies the same posture to every SKU and customer. States are per SKU and per location, they are entered on evidence, and each has its own reporting: what triggered it, what it cost, what it protected. That is what lets an operator approve a plan, rather than trust it.</P>
      </>
    ),
    sources: [sheffi, simchi, cusum, rockafellar],
  },
};
