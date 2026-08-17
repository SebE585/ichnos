# Data from: Where do livestock guardian dogs go? Movement patterns of free-ranging Maremma sheepdogs

ICHNOS quality sheet. Movebank Data Repository, item `eda74cd3-d35b-4fb5-9981-2d72b3e641d5`.
Source licence: **CC0 1.0 Universal**.

## What the dataset carries

| | |
|---|---|
| Dominant sensor | gps |
| Fixes | 162,342 |
| Individuals | 22 |
| Span | 1287 days |
| Median cadence | 30 min |
| Dominant cadence | 30 min |
| Regularity | 94 % of intervals at the dominant step |
| 95th percentile of gaps | 60 min |

## Three quality measures

| Measure | Value | Reading |
|---|---|---|
| Position spikes | 0.000 % | nothing notable |
| Repeated positions | 0.16 % | nothing notable |
| Coordinate grain | 6 decimals | precision preserved |

## What this dataset does not support

- No limitation detected by this bench. That does not mean the dataset is sound, only that it passes these three tests.

## Method

Out-and-back detector, no scale and no species: over three consecutive positions A, B, C the excursion is `(AB + BC - AC) / 2`, compared to the 95th percentile of **that individual's own** step. This avoids any species-dependent threshold. A fix is flagged past ten times its own yardstick.

Validation: applied unchanged across the corpus, this detector recovers the documented precision gap between Argos and GPS on its own, over the 287 datasets labelled as one or the other (median 0.021 % against 0.001 %, Mann-Whitney p = 3.4e-07), without being told anything about the positioning system.

This bench judges neither the science nor the fieldwork. It measures what the published file carries, and what it does not.

A contested measurement is a useful one: if this result looks wrong to you, the author would rather know.

---

*ICHNOS Field Clause, non-binding. This bench is free to use. If it was useful to you, and you work somewhere where things move, you are invited, and never required, to invite its author to come and see it.*