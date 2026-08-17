# Data from: Influence of density-dependent competition on foraging and migratory behavior of a subtropical colonial seabird

ICHNOS quality sheet. Movebank Data Repository, item `cec3bcf7-08fe-43e7-ac0c-af8f7d684a04`.
Source licence: **CC0 1.0 Universal**.

## What the dataset carries

| | |
|---|---|
| Dominant sensor | gps |
| Fixes | 169,564 |
| Individuals | 81 |
| Span | 1017 days |
| Median cadence | 1.5 h |
| Dominant cadence | 90 min |
| Regularity | 62 % of intervals at the dominant step |
| 95th percentile of gaps | 10.5 h |

## Three quality measures

| Measure | Value | Reading |
|---|---|---|
| Position spikes | 0.184 % | **high rate, filter before analysis** |
| Repeated positions | 6.70 % | **a major share of rows carries no new position** |
| Coordinate grain | 4 decimals | **coordinates truncated at export, grid of about 0 m** |

## What this dataset does not support

- Any analysis finer than **0 m**: the precision was destroyed before publication and is not recoverable.
- Fix counts as a measure of effort: **7 %** of rows repeat the previous position exactly.
- Unfiltered path length: **0.18 %** of triplets show an out-and-back incompatible with that individual's own step.

## Method

Out-and-back detector, no scale and no species: over three consecutive positions A, B, C the excursion is `(AB + BC - AC) / 2`, compared to the 95th percentile of **that individual's own** step. This avoids any species-dependent threshold. A fix is flagged past ten times its own yardstick.

Validation: applied unchanged across the corpus, this detector recovers the documented precision gap between Argos and GPS on its own, over the 287 datasets labelled as one or the other (median 0.021 % against 0.001 %, Mann-Whitney p = 3.4e-07), without being told anything about the positioning system.

This bench judges neither the science nor the fieldwork. It measures what the published file carries, and what it does not.

A contested measurement is a useful one: if this result looks wrong to you, the author would rather know.

---

*ICHNOS Field Clause, non-binding. This bench is free to use. If it was useful to you, and you work somewhere where things move, you are invited, and never required, to invite its author to come and see it.*