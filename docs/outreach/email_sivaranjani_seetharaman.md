# Sivaranjani Seetharaman — follow-up email

_Drafted 2026-08-28._

## Context (verified)

- **Panel:** "Bridging Engineering and Agriculture: Innovations for Resilient
  Supply Chains," 26 March 2026, ARMS Atrium, Purdue. Part of the Purdue
  Engineering Distinguished Lecture Series. Panelists: **Anna Nagurney**
  (UMass Amherst) and **Sivaranjani Seetharaman** (Purdue Edwardson School of
  IE). Moderated by Hua Cai. Themes: optimization and game theory for
  agricultural supply chains, fresh produce quality in multitiered chains,
  measuring resilience to disruption.
- **Her:** Assistant Professor, Edwardson School of Industrial Engineering
  (same school as us). Control plus machine learning in large-scale networked
  systems; energy, transportation, interdependent infrastructures. PhD
  Electrical Engineering, Notre Dame (advisor Vijay Gupta). MIT Rising Stars
  in EECS 2018. DEPSCoR award 2023.
- **Email:** sseetha@purdue.edu
- **Our prior contact:** spoke with her briefly after the panel. Nothing was
  built at that point. The status update is the news hook.

## Why the correlation angle is the right hook for her

Her work is interdependent infrastructure networks, where correlated failure
across coupled components is the central problem. Our copula layer is the
same structure: suppliers sharing a weather region fail together, and
treating them as independent understates aggregate risk. That is her
vocabulary, not ours, and it is also the resilience theme of the panel.

## Draft (simplified)

**To:** sseetha@purdue.edu
**Subject:** Following up from the March panel with Anna Nagurney

Dear Professor Seetharaman,

We are the two industrial engineering students who spoke with you after the
"Bridging Engineering and Agriculture" panel with Anna Nagurney in March. At
the time we described an idea. We wanted to follow up now that it is built.

The tool helps perishable food operators decide how much to commit to each
supplier and buyer before they know what will actually arrive. It runs on
the records they already keep, and underneath it is a two stage stochastic
program.

One finding may interest you. When we treated suppliers as independent, the
value of the stochastic solution nearly vanished. Once we modeled the
correlation between them, since suppliers in the same region tend to fail
together, the result changed completely. That felt close to the resilience
questions the panel kept returning to.

We would value two things. First, a critical read on how we validate
ourselves. We measure performance out of sample and report the result even
when it is unfavorable, and we would like to know whether that design holds
up. Second, introductions. Everything so far runs on synthetic data, and our
bottleneck is a first operator willing to share six to twelve months of
history for a free, no obligation analysis.

Could we have twenty five minutes? We are in the Edwardson School as well
and happy to come to you.

Thank you for your time,

Rad Al Zubi and Mustafa Sabieha
Industrial Engineering, Purdue University
