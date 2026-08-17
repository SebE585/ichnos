# Data from: Scales of blue and fin whale feeding behavior off California, USA, with implications for prey patchiness

ICHNOS quality sheet. Movebank Data Repository, item `ba6e95bb-60df-4015-8e21-422c1374f0cb`.
Source licence: **CC0 1.0 Universal**.

## What the dataset carries

| | |
|---|---|
| Dominant sensor | gps |
| Fixes | 17,169 |
| Individuals | 13 |
| Span | 367 days |
| Median cadence | 11 min |
| Dominant cadence | 7 min |
| Regularity | 20 % of intervals at the dominant step |
| 95th percentile of gaps | 44 min |

## Three quality measures

| Measure | Value | Reading |
|---|---|---|
| Position spikes | 0.058 % | **high rate, filter before analysis** |
| Repeated positions | 0.00 % | nothing notable |
| Coordinate grain | 4 decimals | **coordinates truncated at export, grid of about 11 m** |

## What this dataset does not support

- Any analysis finer than **11 m**: the precision was destroyed before publication and is not recoverable.
- Unfiltered path length: **0.06 %** of triplets show an out-and-back incompatible with that individual's own step.
- Comparing distances between individuals without resampling: only **20 %** of intervals are at the dominant step.

## Method

Out-and-back detector, no scale and no species: over three consecutive positions A, B, C the excursion is `(AB + BC - AC) / 2`, compared to the 95th percentile of **that individual's own** step. This avoids any species-dependent threshold. A fix is flagged past ten times its own yardstick.

Validation: applied unchanged across the corpus, this detector recovers the documented precision gap between Argos and GPS on its own, over the 287 datasets labelled as one or the other (median 0.021 % against 0.001 %, Mann-Whitney p = 3.4e-07), without being told anything about the positioning system.

This bench judges neither the science nor the fieldwork. It measures what the published file carries, and what it does not.

A contested measurement is a useful one: if this result looks wrong to you, the author would rather know.

---

*ICHNOS Field Clause, non-binding. This bench is free to use. If it was useful to you, and you work somewhere where things move, you are invited, and never required, to invite its author to come and see it.*