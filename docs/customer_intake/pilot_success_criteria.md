# Pilot Success Criteria

**HarvestMind Pilot — Mutual Agreement Document**

This document defines what success looks like for the HarvestMind pilot engagement.
Both parties (HarvestMind and the partner operator) should review and agree on these
criteria before the pilot begins.

---

## Pilot Scope

| Item | Value |
|---|---|
| Partner name | _____________________________ |
| Pilot start date | _____________________________ |
| Pilot end date | _____________________________ |
| Primary operator contact | _____________________________ |
| Data time range | _____________________________ (e.g., Apr–Jun 2026) |
| Products in scope | All products / Specific categories: _____ |

---

## Data Readiness Criteria (Entry Gate)

The pilot is considered ready to begin when all of the following are true:

- [ ] **All 5 staging tables loaded** — row counts > 0 in HarvestMind for
  products, supplier deliveries, inventory lots, buyer orders, and waste adjustments
- [ ] **Data quality score ≥ 60%** — visible on the Data Quality dashboard page
- [ ] **At least 30 days** of order history and delivery history loaded
- [ ] **Current inventory snapshot** loaded (today's on-hand quantities and expiry dates)
- [ ] **Waste log** covers the same date range as orders and deliveries

---

## Diagnostic Accuracy Criteria

After loading data, the partner operator will:

1. Review the **Waste Loss** figure and confirm it is in the right order of magnitude
   compared to their internal waste logs
2. Review the **Shortage Loss** figure and confirm at-risk orders correspond to real
   fulfillment shortfalls they experienced
3. Review the **Supplier Reliability** table and confirm the risk tiers (High/Medium/Low)
   match their operational experience
4. Review the **Buyer Fulfillment** table and confirm the identified risky buyers match
   their known problem accounts
5. Review the **ATP by Product** table and confirm on-hand quantities are approximately
   correct as of the snapshot date

**Acceptance threshold**: The operator agrees that ≥ 3 of the 5 above areas are
directionally accurate (not necessarily exact dollar figures).

---

## Value Discovery Criteria

The pilot is considered a value discovery success if HarvestMind identifies at least
one of the following:

- [ ] A supplier with fill rate < 80% that the operator was not formally tracking
- [ ] A near-expiry or expired inventory situation that had not been escalated
- [ ] A buyer with fulfillment rate < 85% representing > $X/month in missed revenue
- [ ] A traceability gap (incomplete lots) that the operator was unaware of
- [ ] A waste reason category representing > 20% of total waste loss

---

## Pilot Outputs

By the end of the pilot, HarvestMind will deliver:

- [ ] A completed diagnostic HTML report exported as PDF
- [ ] A written summary (2–3 paragraphs) of top findings specific to the partner
- [ ] A recommendation for which 1–2 operational changes would have the highest impact
- [ ] An updated savings estimate based on actual partner data (not sample data)

---

## Out of Scope for This Pilot

The following are explicitly NOT part of this pilot engagement:

- Real-time inventory tracking or WMS integration
- Automated reorder triggers or purchasing workflows
- Multi-location / multi-warehouse support
- ERP system integration or data sync
- Mobile application or offline access
- User accounts, role-based access, or audit logging
- FSMA-204 full compliance certification (HarvestMind provides readiness assessment only)

---

## Data Handling Agreement

- [ ] The operator confirms the data provided does not contain personally identifiable
  information (PII) beyond organization names and product names
- [ ] HarvestMind confirms the data will be stored only in the local DuckDB instance
  and will not be shared with third parties
- [ ] Both parties agree to delete the pilot data at the end of the engagement unless
  a commercial agreement extends the relationship
- [ ] The diagnostic report is confidential and intended only for internal use by the
  partner operator

---

## Pilot Exit Criteria

### Go → Commercial Engagement

Proceed to a paid commercial engagement if:

1. Data readiness criteria met
2. Diagnostic accuracy confirmed (≥ 3 of 5 areas directionally accurate)
3. At least one value discovery finding confirmed by the operator
4. Operator expresses intent to act on at least one recommendation

### No Go → Lessons Learned

If the pilot does not proceed to commercial engagement, both parties agree to a
30-minute debrief call to document:
- What data gaps prevented a full diagnostic
- What findings (if any) were useful
- What would need to change for a future engagement

---

## Sign-Off

| Role | Name | Date |
|---|---|---|
| Operator representative | | |
| HarvestMind representative | | |

_Both parties have reviewed and agreed to the criteria above._
