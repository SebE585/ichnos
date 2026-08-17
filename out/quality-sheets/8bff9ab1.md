# Data from: Study "Long-tailed Jaeger - PTT - Canadian Arctic"

ICHNOS quality sheet. Movebank Data Repository, item `8bff9ab1-d9f9-4fd7-b253-2a24753a0e2e`.
Source licence: **CC0 1.0 Universal**.

## What the dataset carries

| | |
|---|---|
| Dominant sensor | argos-doppler-shift |
| Fixes | 1,093 |
| Individuals | 9 |
| Span | 84 days |
| Median cadence | 27 min |
| Dominant cadence | 30 s |
| Regularity | 2 % of intervals at the dominant step |
| 95th percentile of gaps | 4.3 j |

## Three quality measures

| Measure | Value | Reading |
|---|---|---|
| Position spikes | 0.279 % | **high rate, filter before analysis** |
| Repeated positions | 1.11 % | frequent repeats |
| Coordinate grain | 3 decimals | **coordinates truncated at export, grid of about 111 m** |

## What this dataset does not support

- Any analysis finer than **111 m**: the precision was destroyed before publication and is not recoverable.
- Unfiltered path length: **0.28 %** of triplets show an out-and-back incompatible with that individual's own step.
- Comparing distances between individuals without resampling: only **2 %** of intervals are at the dominant step.

## Method

Out-and-back detector, no scale and no species: over three consecutive positions A, B, C the excursion is `(AB + BC - AC) / 2`, compared to the 95th percentile of **that individual's own** step. This avoids any species-dependent threshold. A fix is flagged past ten times its own yardstick.

Validation: applied unchanged across the corpus, this detector recovers the documented precision gap between Argos and GPS on its own, over the 287 datasets labelled as one or the other (median 0.021 % against 0.001 %, Mann-Whitney p = 3.4e-07), without being told anything about the positioning system.

This bench judges neither the science nor the fieldwork. It measures what the published file carries, and what it does not.

A contested measurement is a useful one: if this result looks wrong to you, the author would rather know.

---

*ICHNOS Field Clause, non-binding. This bench is free to use. If it was useful to you, and you work somewhere where things move, you are invited, and never required, to invite its author to come and see it.*