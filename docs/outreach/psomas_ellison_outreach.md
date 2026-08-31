# Psomas / Ellison Thread

_Started 2026-08-26. Brenna Ellison (Purdue, food waste research) replied to
our cold email, offered a meeting, and referred us to Dr. Alex Psomas._

## Status

- **Brenna Ellison** — replied 2026-08-26. Transparent that her network is
  household-focused (her food waste research targets households), so limited
  operator connections. Offered Teams/Zoom **Tue 2026-09-01, 12:00-1:30pm**.
  ACTION: accept promptly and propose a specific 30-min slot inside her window.
- **Dr. Alex Psomas** — Assistant Professor, Computer Science, Purdue.
  Referred by Ellison. Warm referral: name-drop her in line one.

## Psomas background (verified 2026-08-26)

- Assistant Professor of Computer Science, Purdue. Expert in AI decision
  making, algorithmic game theory, fair division / mechanism design.
- Works with the **Indy Hunger Network** on its **Food Drop** initiative:
  matching truckloads of rejected-but-edible food (grocery, restaurant,
  logistics rejects) to food banks instead of landfill.
- His system makes **automatic allocations rather than recommendations**,
  removing the phone-around step for IHN staff and the idle wait for drivers.
- Talk title: "Theory and Practice of Fair Food Allocation" (Purdue LaunchTalk).
- Sources: purdue.edu newsroom 2024-Q4; Purdue Exponent; AAU featured research;
  Purdue Stories podcast ep. 128.

## Why he matters to us

1. **Closest methodological peer on campus.** He solves constrained allocation
   of perishable food under uncertainty; we solve two-stage stochastic
   commitment. Different objective (fairness vs cost), same problem family.
2. **He has shipped to a real operator.** IHN is live, not synthetic. He knows
   what it took to get real operational data out of a food organization, which
   is exactly our current bottleneck.
3. **Network.** Indy Hunger Network touches grocery, restaurant, and logistics
   donors plus food banks (incl. Gleaners / Fresh Connect Central). Those
   donors ARE commercial food distributors.
4. **Possible advisor / collaborator.** CS faculty with a deployed food-systems
   system is a credible technical advisor if there is mutual fit.

## Questions to ask him

- How did IHN agree to share operational data, and what did the first version
  actually need to be before they trusted it?
- Is the pain upstream of donation, i.e. do donors ever say why the load was
  rejected in the first place?
- Which donors or food banks in the network would recognize the
  commit-before-supply-is-certain problem?
- Would fairness constraints and our cost-based recourse ever compose, e.g.
  allocating scarce committed supply across buyers?

## Contact (verified 2026-08-26)

- **Dr. Alex Psomas** — apsomas@purdue.edu — office DSAI 2144, Purdue CS.
- **Dr. Brenna Ellison** — replied from her Purdue address; keep the thread.

## Draft email to Psomas

**To:** apsomas@purdue.edu
**Subject:** Referred by Brenna Ellison, Purdue IE students working on food allocation

Dear Dr. Psomas,

Brenna Ellison suggested we reach out to you. I am an industrial
engineering student at Purdue, and with my co-founder Mustafa Sabieha,
also a Purdue industrial engineer, I am building a supply planning
optimizer for perishable food operators. It treats the weekly buying
decision as a two stage stochastic program, committing to suppliers
before yields and demand are known and minimizing the expected cost of
what follows: spot purchases, wasted product, and unmet orders.

Your Food Drop work with the Indy Hunger Network is the closest thing on
campus to what we are attempting. You optimize for fairness across
recipients. We optimize for cost, meaning the waste and lost margin an
operator absorbs when a commitment turns out wrong. The objective
functions differ, but the underlying problem is the same, allocating
perishable supply under uncertainty and hard constraints.

We would value a broad conversation rather than a narrow one. Critique of
the model is welcome, but so is your read on the problem itself and on
what we are most likely getting wrong. The question we are genuinely
stuck on is less technical than that: how you got a real organization to
trust a system with live decisions. Our engine is gate tested but has
only ever seen synthetic data, and a first operator willing to share real
history is our bottleneck. If anyone in the Indy Hunger Network orbit, a
food bank, a grocery or restaurant donor, or a logistics partner, might
recognize this problem or be worth speaking to, a pointer would be just
as valuable.

Could we have twenty five minutes at your convenience? We are on campus
and happy to come to you.

Thank you for your time.

Rad Al Zubi
Industrial Engineering, Purdue University

## Draft reply to Brenna Ellison (send today, meeting is 9/1)

**Reply in thread, keep her subject line.**

Hi Brenna,

Thank you for the quick and generous reply, and for being upfront about
where your connections sit. That kind of transparency saves everyone time
and we appreciate it.

Tuesday 9/1 works well for us. Would 12:30 to 1:00 suit you? We are happy
to take any thirty minutes inside your window if another time is easier.

We would still value your perspective a great deal. Part of what our tool
does is put a dollar figure on waste at the operator level, so how you
measure and frame waste on the household side is a useful check on
whether we are counting the right things and drawing the right
boundaries.

Thank you also for pointing us to Dr. Psomas. His Food Drop work looks
like the closest thing on campus to what we are building. We plan to
write to him this week, and if you felt an introduction was appropriate
we would be grateful, though please do not feel any obligation.

Happy to send a one page overview ahead of Tuesday if that would be
useful for you.

Best regards,

Rad Al Zubi and Mustafa Sabieha
Industrial Engineering, Purdue University
