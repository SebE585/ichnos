# Data from: Study "Movements of the Christmas Island flying fox, Australia"

ICHNOS quality sheet. Movebank Data Repository, item `3cef8e9d-c82a-43d2-8bea-fd9d3527c66b`.
Source licence: **CC0 1.0 Universal**.

## What the dataset carries

| | |
|---|---|
| Dominant sensor | gps |
| Fixes | 6,139 |
| Individuals | 27 |
| Span | 839 days |
| Median cadence | 20 min |
| Dominant cadence | 20 min |
| Regularity | 68 % of intervals at the dominant step |
| 95th percentile of gaps | 2.5 h |

## Three quality measures

| Measure | Value | Reading |
|---|---|---|
| Position spikes | 0.000 % | nothing notable |
| Repeated positions | 0.02 % | nothing notable |
| Coordinate grain | 7 decimals | precision preserved |

## What this dataset does not support

- No limitation detected by this bench. That does not mean the dataset is sound, only that it passes these three tests.

## Method

Out-and-back detector, no scale and no species: over three consecutive positions A, B, C the excursion is `(AB + BC - AC) / 2`, compared to the 95th percentile of **that individual's own** step. This avoids any species-dependent threshold. A fix is flagged past ten times its own yardstick.

Validation: applied unchanged across the corpus, this detector recovers the documented precision gap between Argos and GPS on its own, over the 287 datasets labelled as one or the other (median 0.021 % against 0.001 %, Mann-Whitney p = 3.4e-07), without being told anything about the positioning system.

This bench judges neither the science nor the fieldwork. It measures what the published file carries, and what it does not.

A contested measurement is a useful one: if this result looks wrong to you, the author would rather know.

---

*ICHNOS Field Clause, non-binding. This bench is free to use. If it was useful to you, and you work somewhere where things move, you are invited, and never required, to invite its author to come and see it.*