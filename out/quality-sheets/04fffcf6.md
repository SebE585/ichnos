# Data from: Airplane tracking documents the fastest flight speeds recorded for bats

ICHNOS quality sheet. Movebank Data Repository, item `04fffcf6-b556-40c1-90c4-947376de3fab`.
Source licence: **CC0 1.0 Universal**.

## What the dataset carries

| | |
|---|---|
| Dominant sensor | radio-transmitter |
| Fixes | 564 |
| Individuals | 7 |
| Span | 6 days |
| Median cadence | 2 min |
| Dominant cadence | 2 min |
| Regularity | 16 % of intervals at the dominant step |
| 95th percentile of gaps | 7 min |

## Three quality measures

| Measure | Value | Reading |
|---|---|---|
| Position spikes | 0.000 % | nothing notable |
| Repeated positions | 0.18 % | nothing notable |
| Coordinate grain | 5 decimals | acceptable grain |

## What this dataset does not support

- Comparing distances between individuals without resampling: only **16 %** of intervals are at the dominant step.

## Method

Out-and-back detector, no scale and no species: over three consecutive positions A, B, C the excursion is `(AB + BC - AC) / 2`, compared to the 95th percentile of **that individual's own** step. This avoids any species-dependent threshold. A fix is flagged past ten times its own yardstick.

Validation: applied unchanged across the corpus, this detector recovers the documented precision gap between Argos and GPS on its own, over the 287 datasets labelled as one or the other (median 0.021 % against 0.001 %, Mann-Whitney p = 3.4e-07), without being told anything about the positioning system.

This bench judges neither the science nor the fieldwork. It measures what the published file carries, and what it does not.

A contested measurement is a useful one: if this result looks wrong to you, the author would rather know.

---

*ICHNOS Field Clause, non-binding. This bench is free to use. If it was useful to you, and you work somewhere where things move, you are invited, and never required, to invite its author to come and see it.*