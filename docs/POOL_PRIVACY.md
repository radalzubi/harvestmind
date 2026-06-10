# Your Data at HarvestMind — Plain English

_This is the document we ask you to read before deciding whether to
contribute to the data pool. The decision is yours, it is off by
default, and you can change it any time._

## What we store about your business (your vault)

Everything you upload lives in your own private vault: your original
files exactly as you sent them, your cleaned data, your diagnostics,
your reports. Your vault is physically separate from every other
operator's — separate files, separate database. No other operator can
see it, and no HarvestMind analysis for another operator can read it.
Every number in your dashboard can be traced back to the exact file and
upload it came from.

## What we use to improve the models (the pool — anonymized only)

If you opt in, after each confirmed upload we extract a small set of
**statistical signals** and add them to a shared, anonymized pool that
makes the forecasting models better for everyone — including you:

- **Demand patterns** — how variable demand is for a product *category*
  (like "leafy greens"), and whether it's trending up or down. Volumes
  are normalized so the size of your business is invisible.
- **Supplier reliability** — the *distribution* of fill rates for a
  category in your region. Ratios only, and only when at least 10
  deliveries stand behind the number.
- **Waste patterns** — waste *rates* per category with the reason
  bucketed into three broad types.

## What is never in the pool

Your company name. Your buyers' names. Your suppliers' names. Product
names (only categories). Your prices. Your volumes. Your locations
beyond a broad region. Anything that could identify your business. Any
signal that would rest on fewer than 10 underlying records is discarded
entirely, because thin samples can identify a business even without
names.

We test this mechanically: our build fails if any name from source data
appears in a pool file.

## Why contribute

The models that forecast your demand and your suppliers' reliability
start out smarter when they can lean on patterns from operators like
you — and yours did the same when you joined. Contributors get the
benefit of the pool; the pool gets only anonymous statistics.

## How to opt in or out

A toggle in your dashboard (Data Quality page), or tell us. Off by
default. Changing it takes effect immediately and every change is
recorded with a timestamp in your own consent file.

## If you stop contributing — or leave

Future contributions stop the moment you opt out. Signals already in
the pool **cannot be removed**, for the same reason they are safe: they
are not traceable back to you, so there is nothing to find and delete.
We tell you this now, before you decide — not after. If you leave
HarvestMind entirely, your vault is retained or returned per your
agreement; the pool keeps only what was always anonymous.

## Questions

Ask us anything about this before consenting. If any answer is unclear,
don't opt in until it is.
