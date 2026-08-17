# Data from: Ámbito de hogar y actividad circadiana del ocelote (Leopardus pardalis) en la Isla de Barro Colorado, Panamá

ICHNOS quality sheet. Movebank Data Repository, item `de1cccab-7744-4014-9f15-504740aa31a2`.
Source licence: **CC0 1.0 Universal**.

## What the dataset carries

| | |
|---|---|
| Dominant sensor | radio-transmitter |
| Fixes | 2,291 |
| Individuals | 9 |
| Span | 752 days |
| Median cadence | 30 min |
| Dominant cadence | 15 min |
| Regularity | 26 % of intervals at the dominant step |
| 95th percentile of gaps | 5.9 j |

## Three quality measures

| Measure | Value | Reading |
|---|---|---|
| Position spikes | 0.000 % | nothing notable |
| Repeated positions | 28.31 % | **a major share of rows carries no new position** |
| Coordinate grain | 15 decimals | precision preserved |

## What this dataset does not support

- Fix counts as a measure of effort: **28 %** of rows repeat the previous position exactly.
- Comparing distances between individuals without resampling: only **26 %** of intervals are at the dominant step.

## Method

Out-and-back detector, no scale and no species: over three consecutive positions A, B, C the excursion is `(AB + BC - AC) / 2`, compared to the 95th percentile of **that individual's own** step. This avoids any species-dependent threshold. A fix is flagged past ten times its own yardstick.

Validation: applied unchanged across the corpus, this detector recovers the documented precision gap between Argos and GPS on its own, over the 287 datasets labelled as one or the other (median 0.021 % against 0.001 %, Mann-Whitney p = 3.4e-07), without being told anything about the positioning system.

This bench judges neither the science nor the fieldwork. It measures what the published file carries, and what it does not.

A contested measurement is a useful one: if this result looks wrong to you, the author would rather know.

---

*ICHNOS Field Clause, non-binding. This bench is free to use. If it was useful to you, and you work somewhere where things move, you are invited, and never required, to invite its author to come and see it.*