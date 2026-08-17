# Data from: Study "Wood stork (Mycteria americana) Southeastern US 2004–2019"

ICHNOS quality sheet. Movebank Data Repository, item `4fdcdd25-6032-4571-a8ab-9fb578b35e23`.
Source licence: **CC0 1.0 Universal**.

## What the dataset carries

| | |
|---|---|
| Dominant sensor | gps |
| Fixes | 1,135,643 |
| Individuals | 133 |
| Span | 5580 days |
| Median cadence | 60 min |
| Dominant cadence | 60 min |
| Regularity | 69 % of intervals at the dominant step |
| 95th percentile of gaps | 9.0 h |

## Three quality measures

| Measure | Value | Reading |
|---|---|---|
| Position spikes | 0.005 % | nothing notable |
| Repeated positions | 17.90 % | **a major share of rows carries no new position** |
| Coordinate grain | 5 decimals | acceptable grain |

## What this dataset does not support

- Fix counts as a measure of effort: **18 %** of rows repeat the previous position exactly.

## Method

Out-and-back detector, no scale and no species: over three consecutive positions A, B, C the excursion is `(AB + BC - AC) / 2`, compared to the 95th percentile of **that individual's own** step. This avoids any species-dependent threshold. A fix is flagged past ten times its own yardstick.

Validation: applied unchanged across the corpus, this detector recovers the documented precision gap between Argos and GPS on its own, over the 287 datasets labelled as one or the other (median 0.021 % against 0.001 %, Mann-Whitney p = 3.4e-07), without being told anything about the positioning system.

This bench judges neither the science nor the fieldwork. It measures what the published file carries, and what it does not.

A contested measurement is a useful one: if this result looks wrong to you, the author would rather know.

---

*ICHNOS Field Clause, non-binding. This bench is free to use. If it was useful to you, and you work somewhere where things move, you are invited, and never required, to invite its author to come and see it.*