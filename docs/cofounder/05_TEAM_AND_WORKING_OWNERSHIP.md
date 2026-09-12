# ZAAD Co-Founder Team and Working Ownership

## 1. Current co-founder team

ZAAD currently has three co-founders:

- **Rad Al Zubi**
- **Mustafa Sabieha**
- **Hamza Al Adwan**

This document defines a recommended operating split. It is not a legal governance document and does not by itself define equity, board rights, compensation, vesting, or corporate authority.

---

## 2. Recommended operating ownership

### Rad Al Zubi — Co-Founder / CEO, Product + Commercial

Primary ownership:

- customer discovery,
- ICP definition,
- sales,
- pricing,
- partnerships,
- product requirements,
- commercial positioning,
- external narrative,
- translating operator pain into decision requirements.

Rad should own the question:

> **Are we solving a problem operators will actually pay to solve?**

Rad should not unilaterally override mathematical correctness because a result is commercially attractive.

---

### Mustafa Sabieha — Co-Founder / Operations, Customer + Implementation

Primary ownership:

- customer data acquisition,
- onboarding,
- implementation workflow,
- pilot operations,
- operator process mapping,
- data quality,
- internal operating systems,
- ensuring recommendations can survive real operational constraints.

Mustafa should own the question:

> **Can this recommendation actually work inside the customer's operating process?**

Mustafa's feedback should be treated as a hard operational-feasibility input, not merely UX feedback.

---

### Hamza Al Adwan — Co-Founder, Quantitative Optimization + Decision Science

Recommended primary ownership:

- mathematical formulation,
- stochastic optimization,
- uncertainty architecture,
- model correctness,
- non-anticipativity / recourse design,
- numerical performance,
- adversarial model review,
- validation methodology,
- decision-loss evaluation,
- future P4+ quantitative architecture.

Hamza should own the question:

> **Is the optimizer mathematically valid, causally honest, numerically defensible, and solving the decision we think it is solving?**

Hamza should have real escalation authority on mathematical integrity. A model should not ship merely because a benchmark result looks commercially attractive.

---

## 3. Cross-functional decision rules

### Product / commercial scope

Rad leads.

But a product requirement that violates physical, mathematical, or data reality must be challenged by Hamza/Mustafa.

### Mathematical formulation

Hamza leads.

But the formulation must solve an operator decision that Rad/Mustafa can explain and validate.

### Operational feasibility

Mustafa leads.

But operator habit alone should not become a hard constraint unless it is actually operationally required.

### Customer commitments

No founder should promise capabilities, savings, deadlines, or automation authority that the product has not actually established.

---

## 4. The three-founder loop

The desired working loop is:

```text
Rad
operator pain / commercial requirement
        ↓
Mustafa
real workflow / data / implementation constraints
        ↓
Hamza
mathematical decision model / validation
        ↓
ZAAD recommendation
        ↓
Mustafa
operational review
        ↓
Rad
customer value / commercial feedback
        ↺
```

This avoids three failure modes:

1. technically impressive optimization with no buyer,
2. customer-driven heuristics with weak mathematical foundations,
3. mathematically correct recommendations that cannot be implemented operationally.

---

## 5. Recommended technical onboarding for Hamza

Hamza should not start by editing P4.

First complete a read-only onboarding pass covering:

1. this `docs/cofounder/` folder,
2. P0 closeout,
3. P1 final closure sections,
4. P2 closeout/performance history,
5. sector-physics closeout/correction,
6. P3 architecture/closeout/performance closure,
7. core optimizer code,
8. current roadmap document.

Then he should produce his own independent system map and identify:

- assumptions he disagrees with,
- possible hidden coupling,
- weak formulations,
- missing invariants,
- places where the evidence is insufficient,
- questions requiring operator data.

The goal is not for Hamza to memorize prior conclusions. The goal is for him to understand and challenge them intelligently.

---

## 6. Suggested near-term ownership

### Rad

- continue operator discovery and prospecting,
- tighten paid diagnostic offer,
- identify first real datasets,
- validate which future modules customers actually control/value.

### Mustafa

- define minimum viable customer data package,
- map onboarding/data-quality workflow,
- specify customer implementation process,
- identify operational constraints not yet represented in the model.

### Hamza

- audit P0-P3 ownership boundaries and final formulations,
- understand P3 performance correction deeply,
- review P4 design before implementation/freeze,
- challenge non-anticipativity/information-set design,
- help define future uncertainty/model-risk framework.

---

## 7. Areas that should be jointly decided

All three founders should jointly review:

- major roadmap reprioritization,
- moving into a new customer vertical,
- any autonomous-execution capability,
- major architecture replacement,
- changes to customer claims,
- use of sensitive customer data,
- security/privacy policy,
- any result used publicly as product-performance evidence.

---

## 8. Governance still needs a separate legal decision

This repository document should not be treated as a substitute for a founders' agreement.

Separately define with appropriate legal advice:

- equity,
- vesting,
- IP assignment,
- decision rights,
- board/control rights,
- departure/bad-leaver treatment,
- confidentiality,
- compensation,
- incorporation/entity matters.

Those issues should not be inferred from technical repository roles.
