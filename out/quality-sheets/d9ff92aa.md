# Data from: Locally adapted migration strategies: Comparing routes and timing of northern wheatears from alpine and lowland European populations [Switzerland]

ICHNOS quality sheet. Movebank Data Repository, item `d9ff92aa-47b8-4c41-881a-ae5e59e11daa`.
Source licence: **CC0 1.0 Universal**.

## What the dataset carries

| | |
|---|---|
| Dominant sensor | solar-geolocator |
| Fixes | 8,653 |
| Individuals | 19 |
| Span | 1453 days |
| Median cadence | 12.0 h |
| Dominant cadence | 12.3 h |
| Regularity | 58 % of intervals at the dominant step |
| 95th percentile of gaps | 16.4 h |

## Three quality measures

| Measure | Value | Reading |
|---|---|---|
| Position spikes | 0.000 % | nothing notable |
| Repeated positions | 90.77 % | **a major share of rows carries no new position** |
| Coordinate grain | 13 decimals | precision preserved |

## What this dataset does not support

- Fix counts as a measure of effort: **91 %** of rows repeat the previous position exactly.
- Comparing distances between individuals without resampling: only **58 %** of intervals are at the dominant step.

## Method

Out-and-back detector, no scale and no species: over three consecutive positions A, B, C the excursion is `(AB + BC - AC) / 2`, compared to the 95th percentile of **that individual's own** step. This avoids any species-dependent threshold. A fix is flagged past ten times its own yardstick.

Validation: applied unchanged across the corpus, this detector recovers the documented precision gap between Argos and GPS on its own, over the 287 datasets labelled as one or the other (median 0.021 % against 0.001 %, Mann-Whitney p = 3.4e-07), without being told anything about the positioning system.

This bench judges neither the science nor the fieldwork. It measures what the published file carries, and what it does not.

A contested measurement is a useful one: if this result looks wrong to you, the author would rather know.

---

*ICHNOS Field Clause, non-binding. This bench is free to use. If it was useful to you, and you work somewhere where things move, you are invited, and never required, to invite its author to come and see it.*