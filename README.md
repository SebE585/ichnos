# ICHNOS

> *ikhnos* (ἴχνος): the trace, the mark left by something that moved.

A metrology bench for animal-tracking data. It does not ask what the animal
did. It asks what the instrument did, and whether the file says so.

## The gap this fills

Animal tracking is a well-equipped field. The hardware is mature, the platforms
are open, and there are thirty years of published science behind it. What is
missing is **device metrology**: nobody asks the trace what it is worth.
Collars are bought on a datasheet, deployed, and their output analysed as if it
were exact.

Of the 447 items downloaded from the Movebank Data Repository, 388 converted
and 353 carried enough data to be surveyed end to end. Of those
353, **41.4 % carry at least one measurable instrument pathology, and
none of them is declared.**

| Pathology | Datasets | Share |
|---|---|---|
| Repeated positions above 5 % of rows | 79 | 22.4 % |
| Coordinates truncated to 4 decimals or fewer | 55 | 15.6 % |
| Gross position outliers above 0.05 % | 53 | 15.0 % |

Forty datasets are published on a grid of 111 m or coarser, two of them at a
single decimal. That is not recoverable.

## Why the detector can be trusted

It uses no species-specific threshold. Over three consecutive positions A, B, C
the excursion is `(AB + BC - AC) / 2`, compared to the 95th percentile of *that
individual's own* step. A ceiling tuned for a passerine is meaningless for a
whale; an animal compared to itself needs no tuning.

Applied unchanged across the corpus it recovers the documented precision gap
between Argos and GPS on its own, over the 287 datasets labelled
as one or the other, **without being told anything about the positioning
system**: median 0.021 % against
0.001 %, Mann-Whitney p = 3.4e-07.

That measurement licenses everything else here. It is produced by
`ichnos/common/detector_validation.py`, which refuses to write its output if
the conclusion does not survive a change of sensor label.

## Three cases, three different demonstrations

| | Elephants | Baboons | Storks |
|---|---|---|---|
| Dataset | Etosha 2008-2014 | Mpala, Kenya, 2012 | migration 2014 |
| Volume | 2.9 M fixes, 15 animals | 19.2 M fixes, 26 animals | 7.2 M fixes, 60 birds |
| Sensors | position only | position 1 Hz, Doppler, accel 12 Hz | position 1 Hz, Doppler |
| Question | **what is the device worth?** | **what can be extracted?** | **how far can it go?** |
| Result | a defect nobody had measured | hip height derived from gait | wind aloft from soaring |

### Elephants: subsampling selects the defect

The fifteen collars split in two with no overlap, matching the delivery
batches. That reading is wrong: **91.8 % of the anomalies sit on the first pair
of a burst**, and the collar's first fix carries no acquisition delay at all
against its 1,200 s wake grid. It reports at the scheduled second whether or
not its solution has converged.

The consequence is what matters. A resample keeps the first fix of each burst,
so subsampling does not remove the defect, **it selects it**: 3.91 % of
samples, median position error 241 m. At twenty-minute spacing that is
0.20 m/s, so no speed filter sees it. Over 28,922 bursts the first fix is the
outlier against the other three in 100 % of cases.

The remedy is one word in one line: subsample on the **second** fix of the
burst rather than the first. No threshold, no species, nothing discarded.

Single-result reproduction, downloading the public files and running on pandas
and numpy alone: <https://github.com/SebE585/etosha-batch-effect>

### Baboons: a prediction the data was not told about

Speed comes from a Doppler shift, stride cadence from an accelerometer. Two
sensors that do not talk to each other, confronted with a law published
thirty-six years before the collar. The walk-run transition lands at Froude
0.482 against 0.50 predicted, and inverting it gives a hip height of 38.6 cm,
consistent with an adult olive baboon.

### Storks: a physical quantity outside the animal

Wind aloft, read from thermal soaring, validated by a structure function: the
disagreement between two birds grows with the distance separating them, where
noise would give the same value everywhere.

## The method, in one line

**Measure twice so that the discrepancy is the control.** Doppler against
position, two birds in one thermal, two collars in one troop, two independent
noise estimators.

## Layout

```
ichnos/adapters/      Movebank and e-obs to the pivot format, validating their own output
ichnos/elephants/     fleet health, burst ranks, what subsampling selects
ichnos/baboons/       position noise, gravity calibration, gait profiles
ichnos/storks/        wind aloft from thermal soaring
ichnos/conformance/   conformance of the corpus to the pivot format
ichnos/common/        corpus survey, quality sheets, detector validation, figures
docs/article/         the paper source, its figures and its bibliography
out/quality-sheets/   353 one-page sheets, one per dataset
```

## Getting started

```
pip install -r requirements.txt
make help          # lists the targets
make corpus        # the survey behind sections 2, 3 and 6 of the paper
make elephants     # the case study of section 4
```

Python 3.10 or later. **No dataset is redistributed and no credentials are
needed**: the Movebank Data Repository serves its published files anonymously,
and the code downloads what it needs from the item identifiers in
`out/movebank_inventory.parquet`.

Two things worth knowing before you start. The three case datasets are about
**3 GB**, downloaded once and cached under `data/`, and the full corpus survey
reads several hundred more. And the pivot format the conformance survey uses is
a **pre-release** (`telemachus==1.0.0a3`), pinned in `requirements.txt` to the
version the published figure was measured against; the survey is the only part
of the bench that needs it.

The paper is versioned as its markdown source and figures, not as a PDF: a
binary that changes on every edit bloats the history and drifts from its
source. `make paper` builds it, and each release carries the built PDF.

This repository holds what reproduces the paper. The bench carries further
measurements that the paper does not use, and they are not shipped here.

## How this was built, and what went wrong

Two days of work on public data. The central mechanism of the elephant case was
wrong on first writing, and the table meant to establish the corrected version
was wrong too. Both were caught by adversarial re-reading of successive drafts,
not from inside the work, and both are recorded with eleven other silent
failures in section 7 of the paper.

What came out of that is the discipline visible here: every figure in the paper
is produced by a committed script that writes a file which the text and the
plots both read, and several of those scripts refuse to write their output when
an independent path disagrees with them. The numbers that were once typed in by
hand are exactly the ones that turned out to be wrong.

## Licensing

**Code**: MIT, see `LICENSE`.

**The paper** (`docs/article/`): CC BY 4.0.

**Quality sheets** (`out/quality-sheets/`): each sheet is derived from one
published dataset and **inherits that dataset's licence**, stated at the top of
every sheet. 34 of the 447 items surveyed carry a CC BY-NC licence, and
28 of them reached the sheet stage; those sheets are marked and may
not be used commercially. `out/licences.parquet` gives the licence of every
item.

## Field clause

*Non-binding, and not a condition of use.* This bench is free to use, modify
and redistribute. If it was useful to you, and you work somewhere where things
move, you are invited, and never required, to invite its author to come and see
it.

---

If a measurement here is wrong, I would rather know. Open an issue.
