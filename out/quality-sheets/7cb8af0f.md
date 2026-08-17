# Data from: Case Report: Long-distance overwater migration of the Northern Boobook, Ninox japonica, revealed by year-round GPS tracking

ICHNOS quality sheet. Movebank Data Repository, item `7cb8af0f-115a-42ce-ac53-ed89753ed608`.
Source licence: **Attribution 4.0 International**.

## What the dataset carries

| | |
|---|---|
| Dominant sensor | gps |
| Fixes | 253 |
| Individuals | 1 |
| Span | 334 days |
| Median cadence | 24.0 h |
| Dominant cadence | 2.0 j |
| Regularity | 35 % of intervals at the dominant step |
| 95th percentile of gaps | 2.0 j |

## Three quality measures

| Measure | Value | Reading |
|---|---|---|
| Position spikes | 0.000 % | nothing notable |
| Repeated positions | 0.00 % | nothing notable |
| Coordinate grain | 5 decimals | acceptable grain |

## What this dataset does not support

- Comparing distances between individuals without resampling: only **35 %** of intervals are at the dominant step.

## Method

Out-and-back detector, no scale and no species: over three consecutive positions A, B, C the excursion is `(AB + BC - AC) / 2`, compared to the 95th percentile of **that individual's own** step. This avoids any species-dependent threshold. A fix is flagged past ten times its own yardstick.

Validation: applied unchanged across the corpus, this detector recovers the documented precision gap between Argos and GPS on its own, over the 287 datasets labelled as one or the other (median 0.021 % against 0.001 %, Mann-Whitney p = 3.4e-07), without being told anything about the positioning system.

This bench judges neither the science nor the fieldwork. It measures what the published file carries, and what it does not.

A contested measurement is a useful one: if this result looks wrong to you, the author would rather know.

---

*ICHNOS Field Clause, non-binding. This bench is free to use. If it was useful to you, and you work somewhere where things move, you are invited, and never required, to invite its author to come and see it.*