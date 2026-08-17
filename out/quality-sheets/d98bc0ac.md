# Data from: Individual variation in migratory path and behavior among Eastern Lark Sparrows

ICHNOS quality sheet. Movebank Data Repository, item `d98bc0ac-2a97-475c-b052-814b76da2cce`.
Source licence: **CC0 1.0 Universal**.

## What the dataset carries

| | |
|---|---|
| Dominant sensor | solar-geolocator |
| Fixes | 3,233 |
| Individuals | 6 |
| Span | 384 days |
| Median cadence | 12.0 h |
| Dominant cadence | 13.0 h |
| Regularity | 44 % of intervals at the dominant step |
| 95th percentile of gaps | 15.0 h |

## Three quality measures

| Measure | Value | Reading |
|---|---|---|
| Position spikes | 0.000 % | nothing notable |
| Repeated positions | 0.00 % | nothing notable |
| Coordinate grain | 12 decimals | precision preserved |

## What this dataset does not support

- Comparing distances between individuals without resampling: only **44 %** of intervals are at the dominant step.

## Method

Out-and-back detector, no scale and no species: over three consecutive positions A, B, C the excursion is `(AB + BC - AC) / 2`, compared to the 95th percentile of **that individual's own** step. This avoids any species-dependent threshold. A fix is flagged past ten times its own yardstick.

Validation: applied unchanged across the corpus, this detector recovers the documented precision gap between Argos and GPS on its own, over the 287 datasets labelled as one or the other (median 0.021 % against 0.001 %, Mann-Whitney p = 3.4e-07), without being told anything about the positioning system.

This bench judges neither the science nor the fieldwork. It measures what the published file carries, and what it does not.

A contested measurement is a useful one: if this result looks wrong to you, the author would rather know.

---

*ICHNOS Field Clause, non-binding. This bench is free to use. If it was useful to you, and you work somewhere where things move, you are invited, and never required, to invite its author to come and see it.*