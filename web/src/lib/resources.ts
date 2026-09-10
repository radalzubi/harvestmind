/**
 * The resource library: a small set of substantive articles around the questions distributors
 * and importers actually ask. Slugs are canonical URL segments under /resources; dates are the
 * dates the content was written or materially revised. No article is published without sources.
 */
export type ArticleMeta = {
  slug: string;
  title: string;          // page title (brand appended by the layout template)
  heading: string;        // visible H1
  description: string;    // meta description and card summary
  published: string;
  modified: string;
  readingMinutes: number;
  related: string[];      // slugs
};

export const ARTICLES: ArticleMeta[] = [
  { slug: "what-is-inventory-optimization-for-distributors",
    title: "What Is Inventory Optimization for Distributors?",
    heading: "What is inventory optimization for distributors?",
    description: "Inventory optimization for distributors explained: what it decides, how it differs from forecasting and reorder points, and what evidence a distributor should demand before changing how it orders.",
    published: "2026-09-06", modified: "2026-09-06", readingMinutes: 7,
    related: ["safety-stock-vs-inventory-optimization", "reduce-inventory-without-hurting-service-levels"] },
  { slug: "safety-stock-vs-inventory-optimization",
    title: "Safety Stock vs. Inventory Optimization",
    heading: "Safety stock versus inventory optimization",
    description: "The classic safety stock formula, where it breaks for distributors with variable suppliers, and how scenario-based inventory optimization sizes protection per SKU, customer and supply lane.",
    published: "2026-09-06", modified: "2026-09-06", readingMinutes: 8,
    related: ["supplier-fill-rate-and-lead-time-variability", "what-is-inventory-optimization-for-distributors"] },
  { slug: "planning-inventory-during-supply-disruptions",
    title: "How Distributors Should Plan Inventory During Supply Disruptions",
    heading: "How distributors should plan inventory during supply disruptions",
    description: "A practical sequence for distributors when a port, supplier or lane fails: reposition, reallocate by customer priority, use approved alternatives, and let protection fall again when the risk passes.",
    published: "2026-09-06", modified: "2026-09-06", readingMinutes: 8,
    related: ["lean-protect-allocate-recover", "supplier-fill-rate-and-lead-time-variability"] },
  { slug: "multi-echelon-inventory-optimization-explained",
    title: "Multi-Echelon Inventory Optimization Explained",
    heading: "Multi-echelon inventory optimization, explained",
    description: "What multi-echelon inventory optimization (MEIO) means for a distributor with a central warehouse and branches, the guaranteed-service model behind most tools, and where network optimization differs.",
    published: "2026-09-06", modified: "2026-09-06", readingMinutes: 7,
    related: ["safety-stock-vs-inventory-optimization", "planning-inventory-during-supply-disruptions"] },
  { slug: "supplier-fill-rate-and-lead-time-variability",
    title: "How Supplier Fill Rate and Lead-Time Variability Affect Inventory",
    heading: "How supplier fill rate and lead-time variability affect inventory",
    description: "Why a supplier that ships 85% of what you ordered, three weeks late on occasion, needs more protection than its average suggests, and how to measure it from your own receipts without fabricating data.",
    published: "2026-09-06", modified: "2026-09-06", readingMinutes: 7,
    related: ["safety-stock-vs-inventory-optimization", "planning-inventory-during-supply-disruptions"] },
  { slug: "reduce-inventory-without-hurting-service-levels",
    title: "How to Reduce Inventory Without Hurting Service Levels",
    heading: "How to reduce inventory without hurting service levels",
    description: "Where distributors can cut working capital safely: SKUs with short, reliable replenishment and alternatives, and where they cannot: long lanes, correlated suppliers and strategic customers.",
    published: "2026-09-06", modified: "2026-09-06", readingMinutes: 7,
    related: ["what-is-inventory-optimization-for-distributors", "lean-protect-allocate-recover"] },
  { slug: "lean-protect-allocate-recover",
    title: "LEAN, PROTECT, ALLOCATE, RECOVER: A Resilience Planning Framework",
    heading: "LEAN, PROTECT, ALLOCATE, RECOVER: a resilience planning framework",
    description: "A four-state framework for supply planning under uncertainty: stay lean while it is safe, buy protection when uncertainty becomes expensive, allocate by customer priority in scarcity, and recover back to lean.",
    published: "2026-09-06", modified: "2026-09-06", readingMinutes: 8,
    related: ["planning-inventory-during-supply-disruptions", "reduce-inventory-without-hurting-service-levels"] },
];

export function article(slug: string): ArticleMeta | undefined {
  return ARTICLES.find((a) => a.slug === slug);
}
