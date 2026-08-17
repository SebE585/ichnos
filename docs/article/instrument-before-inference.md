---
title: "Instrument before inference"
subtitle: "Device metrology on 447 public animal-tracking datasets"
author: Sébastien Edet
date: 2026-08-16
lang: en
compact: true
footer-text: "Preprint, 2026-08-16"
keywords: [movement ecology, biologging, data quality, GPS, device metrology]
bibliography: references.bib
link-citations: true
---

# Abstract {-}

Animal-tracking datasets are published as positions and analysed as movement.
Between the two sits an instrument whose behaviour is almost never described.
I applied a species-agnostic quality bench to 447 public datasets from the
Movebank Data Repository, 388 of which converted, covering 134,634,516 fixes,
17,418 individuals and 1,120 dataset-years.

**41.4 % of datasets carry at least one measurable instrument pathology, and
none of them is declared.** Fifty-five datasets are published with coordinates
truncated to four decimals or fewer, forty of them to a grid of 111 m or
coarser; this is not recoverable. Seventy-nine repeat positions on more than
5 % of consecutive rows, from two distinguishable causes. Fifty-three carry
gross position outliers.

The detector uses no species-specific threshold: it compares every animal to
its own step distribution. Applied unchanged across the corpus it recovers the
documented precision gap between Argos and GPS on its own, without being told
anything about the positioning system (median 0.021 % against 0.001 %,
Mann-Whitney *p* = $3.4 \times 10^{-7}$).

A case study shows what such a defect looks like, and how easily it is
mis-attributed. In one published, cited dataset the fifteen collars split in
two with no overlap, eight between 3.66 % and 17.27 % of physically impossible
fix pairs against seven below 0.0021 %, matching the delivery batches. The hardware
reading is wrong: **91.8 % of the anomalies sit on the first pair of a burst**,
the rate falls to zero in 2010 on collars still deployed, and discarding only
the first fixes that fail the physical test removes 92 % of the problem for
1.0 % of the data. It is an acquisition
behaviour, not a sensor: the collar reports at its scheduled second with no
measurable acquisition delay, whether or not its solution has converged. It is
invisible at the cadence these data are normally analysed at, and worse than
invisible — subsampling a burst keeps its first fix, so it **selects** the
defect at 3.91 % of samples, where no speed filter can see it. Taking the
second fix of each burst instead removes all of it and discards nothing.

Interrogating the instrument also produces results rather than warnings. From
GPS traces alone I recover the walk-run transition of a baboon at a Froude
number of 0.482 against 0.50 predicted, the wind aloft from stork thermal
soaring to 1 to 1.4 m/s per spiral, and a 12.5 % gain spread between nominally
identical accelerometers.

I close on what the bench cost to build: thirteen silent failures, six of them
in my own work, including one in the guard written against silent failures, one
in the measuring instrument itself, one in the headline conclusion of this
paper, one in the correction of that conclusion, and one in the table that was
supposed to establish it. None raised an exception. All
returned plausible results.

---

# Introduction

Wildlife telemetry is well equipped. Collars are mature products from a dozen
manufacturers, open platforms exist to visualise and alert on their output
[@wall2024], and the field has thirty years of methodological depth behind it.

What it does not have is **metrology of the device itself**. Nobody asks the
track what it is worth.

Collars are bought on a datasheet, deployed, and their output analysed as
though it were exact. Once a collar is on an animal the manufacturer never sees
its data again, and the ecologist who does see it has no reference against
which to characterise it. The error budget of a published trajectory is, in
almost every case, unstated and unmeasured.

This matters because the derived quantities the field relies on are functions of
the instrument as much as of the animal. Distance travelled, home range, step
length, turning angle and state assignments all inherit whatever the receiver
did. When the instrument is undescribed, so are they.

This paper treats the error budget as a first-class question rather than a
cleaning step. It asks three things of a public corpus:

1. Can device pathologies be detected without knowing the species?
2. How common are they, and are they declared?
3. What would a data format have to record for the answer to be visible?

---

# Materials and methods

## Corpus

The Movebank Data Repository [@movebank] was enumerated in full through its
DSpace API:
2,008 items, of which 447 carry published data files. All 447 were downloaded
and processed.

Of these, 388 converted to a common tabular form. Fifty carry no position
column at all — light-level geolocators, accelerometer-only streams and
companion analysis tables — and are out of scope rather than failures. Nine
were unreadable, one of them because its archive is truncated at source with an
invalid CRC.

The converted corpus is **134,634,516 fixes, 17,418 individuals, 1,120
dataset-years** of cumulative coverage, spanning terrestrial mammals, marine
mammals, birds and primates, from GPS, Argos and other positioning systems.

Licences are heterogeneous and matter for reuse: 374 datasets are CC0, 27
CC BY 4.0, 34 CC BY-NC 4.0, eleven carry software licences and one declares
none. All results below are derived under those terms.

## A detector with no species and no scale

The obvious criterion — flag a fix pair implying a speed above the species
maximum — does not transpose. This corpus runs from a passerine to a sperm
whale, and a threshold tuned for one is meaningless for the other. Applying 447
species-specific ceilings would also mean reading 447 datasheets, which defeats
the purpose.

Instead I use an **out-and-back** criterion. An isolated bad fix forces the
trajectory to leave and return. Over three consecutive positions A, B, C:

$$\text{excursion} = \frac{AB + BC - AC}{2}$$

Real displacement gives a small excursion relative to the animal's usual step.
A position spike gives a large one. The quantity is **scale-free**, and it is
compared to the 95th percentile of that individual's own step distribution, so
each animal is judged against its own yardstick. A fix is flagged past ten
times that yardstick.

No species information enters at any point.

## Validation of the detector

The detector is validated against a fact it is not told: Argos Doppler
positioning has been documented as substantially less precise than GPS for
forty years.

| Positioning system | Datasets | Fixes | Median flagged | 75th pct |
|---|---|---|---|---|
| Argos | 49 | 3.2 M | **0.021 %** | 0.080 % |
| GPS | 238 | 97.7 M | **0.001 %** | 0.012 % |

Mann-Whitney, Argos greater than GPS: ***p* = $3.4 \times 10^{-7}$** over 287 datasets.

A detector that knows nothing of positioning systems, species or scales
recovers the difference on its own. This is what licenses the rest of the
paper.

---

# The state of the corpus

Three pathologies were measured on the 353 datasets the bench could process end
to end.

| Pathology | Datasets | Share |
|---|---|---|
| Repeated positions above 5 % | 79 | 22.4 % |
| Coordinates truncated to $\leq$ 4 decimals | 55 | 15.6 % |
| Position spikes above 0.05 % | 53 | 15.0 % |
| **At least one of the three** | **146** | **41.4 %** |

**None is declared anywhere in the metadata.**

## Truncation is the one that cannot be undone

Forty datasets are published with three decimals of latitude or fewer, a grid
of at least 111 m. Nine carry two decimals, a grid of 1.1 km. Two carry a
single decimal, 11 km.

For movement ecology at those grains the measurement is simply gone. And unlike
a spike, which a filter removes, a truncated precision cannot be restored. The
loss happened before publication and nothing in the file records it.

These datasets are in current use for habitat selection and home-range
analysis.

## Repeated positions have two distinguishable causes

Repetition is the most widespread pathology, with a maximum of 97.7 % of
consecutive rows carrying coordinates identical to the previous one. The cause
is not the same everywhere, and the coordinate grain separates the two cases:

| Signature | Diagnosis |
|---|---|
| 4 decimals, minimum step of tens of metres | truncation at export |
| 6 decimals, minimum step 2 cm, 94 % repeats | the device republishing a stale fix |

Both matter, both are invisible in the metadata, and only the second is a
device pathology at all. A criterion that did not look at the grain would
conflate them.

---

# Case study: a defect confined to the first fix of a burst

The `African elephants in Etosha National Park` dataset [@getz2019data;
@tsalyuk2019] carries 2,930,268 fixes from fifteen collars over six years. The
collars fire bursts: four fixes ten seconds apart, then roughly twenty minutes
of silence. Five fixes are flagged as outliers by the curators; every count and
proportion below is computed on the remaining 2,930,263.

The data are owned in the first instance by Etosha National Park, Namibia;
their collection was funded by the United States government through a research
award to W. M. Getz at the University of California, Berkeley; and M. Tsalyuk
curates the published deposit. They are released under CC BY-NC 4.0, and the
present work is non-commercial. The section that follows examines an artefact
of the recording instrument, not of the fieldwork, the curation or the
analyses these data have supported.

Applying a deliberately generous physiological ceiling — two fixes 10 to 60 s
apart implying more than 8 m/s, against a documented sprint speed near 25 km/h
— produces **32,057 impossible pairs**, with a median jump of 266 m in ten
seconds and a maximum of 13.3 km.

The distribution across collars splits the fleet in two with no overlap:

| Group | Collars | Impossible pairs |
|---|---|---|
| serials AG004–AG013, deployed Oct 2008 | 8 | 3.66 % – 17.27 % |
| serials AG189–AG195, deployed 2009 | 7 | **0 – 0.0021 %** |

The criterion is given neither deployment date nor serial number; the split
emerges on its own, and Figure 1 shows it has no overlap and no borderline
case.

![Physically impossible fix pairs per collar, Etosha. Eight
collars between 3.66 % and 17.27 %, seven below 0.0021 % of which four at
exactly zero. No overlap and no borderline case: the two groups are separated
by a factor of 1,700.](figures/fig1-batch-effect.png)

## Where in the burst

That table invites a hardware explanation, and it would be the wrong one. The
position of the flagged pair inside the burst settles the mechanism:

| Rank within burst | Pairs | Flagged | Share |
|---|---|---|---|
| 1st to 2nd fix | 593,523 | **29,441** | 4.96 % |
| 2nd to 3rd | 436,047 | 364 | 0.083 % |
| 3rd to 4th | 401,983 | 2,250 | 0.560 % |
| 4th to 5th | 1,675 | 2 | 0.119 % |
| 5th to 6th | 804 | 0 | 0.000 % |

**91.8 % of the anomalies sit on the first pair of a burst**, at a rate sixty
times that of the second pair. This is the signature of a receiver emitting a
position before its solution has converged, after twenty minutes asleep — not
of a degraded sensor.

Two details sharpen it. First, the effect tracks how many fixes the burst
contains, and the fifteen collars do not agree on that either:

| First-pair flag rate | 3-fix bursts | 4-fix bursts | 5-fix | 6-fix |
|---|---|---|---|---|
| serials AG004–AG013 | 0.08 % | **18.83 %** | 17.75 % | 41.54 % |
| serials AG189–AG195 | 0.0000 % | 0.0008 % | — | — |

A three-fix burst from an affected collar is essentially clean; a four-fix
burst from the same collar is bad almost one time in five. The unaffected
collars stay below 0.001 % at every burst length: three flagged pairs across
858,740.

The obvious reading is that short bursts are the ones where the receiver waited
for convergence and emitted one fix fewer. It is wrong, and the data settle it.
The wake schedule is a strict 1,200 s grid, so the delay of the first fix
against its expected wake time measures acquisition effort directly. That delay
is **zero at every burst length and on both batches**, median and both
quartiles alike. The collar never waits: it reports at the scheduled second
whether or not it has a solution. That is the mechanism asserted above, now
measured rather than inferred. The same measurement disposes of a second
reading, that the true first fix is simply not recorded in short bursts — that
would place the recorded first fix ten seconds late, and it does not.

What decides burst length therefore remains open. A firmware rule ending
acquisition once a quality threshold is met would produce this pattern with the
causality reversed, a clean first fix *causing* the short burst rather than
resulting from it. Settling that needs telemetry this dataset does not carry.

Second, a weaker residue sits on the *last* pair of a burst: 0.48 % against
0.10 % for the middle pair across all burst lengths, or 0.56 % for the
third-to-fourth pair within the four-fix bursts that are 92 % of the corpus. It
accounts for most of the 2,616 anomalies that survive the first-fix remedy.
This paper does not explain it either, and the plausible causes are hardware
rather than acquisition: supply sag after thirty seconds of continuous receiver
activity, a power-down overlapping the last position computation, or write
noise as the burst is committed to flash. None of the three is tested here.

Discarding the first fixes that fail the physical test takes the worst collar
from 17.27 % to **1.29 %**.

## Two competing explanations, both tested and rejected

**Degraded timestamps.** The repository notes that some segments lack seconds
precision, which would manufacture false jumps. Rejected: the modal intra-burst
step is 10 s in both groups, both carry the same proportion of non-zero
seconds, and for pairs 15 to 40 minutes apart the two groups are
indistinguishable (99th percentile of implied speed 0.94 m/s against 0.99 m/s).

**Ageing hardware or batteries.** If the older collars had degraded with use,
the rate would grow over time. It does the opposite:

Rates below are on the first pair of each burst, which is where the defect
lives:

| Year | 2008 group | 2009 group |
|---|---|---|
| 2008 | 39.90 % | — |
| 2009 | 16.44 % | 0.0000 % |
| 2010 | **0.0000 %** | 0.0000 % |
| 2011–2014 | — | 0 – 0.0027 % |

The 2008 collars were still returning 44,269 first-burst pairs in 2010, not one
of which is flagged, and the defect had gone. It did not wear in; it was
resolved.

## What the dataset therefore contains

Not two populations of hardware, but an **acquisition behaviour that changed**.
Collars delivered in 2009 never exhibited it; collars delivered in 2008 did,
until something changed in the field in 2010. A firmware or configuration
revision fits every observation here, though the file cannot prove which.

The practical consequence is narrower and more useful than a hardware story
would be. No collar needs excluding and no animal needs dropping. But the
obvious remedy is the wrong one:

| Remedy | Fixes removed | Share of dataset |
|---|---|---|
| discard every first fix of a burst | 753,046 | 25.7 % |
| discard first fixes that fail the physical test | **29,441** | **1.00 %** |

Discarding every first fix throws away 723,605 sound positions to remove 29,441
bad ones, and costs the 2009 collars a quarter of their data for nothing. The
targeted remedy is simply this paper's own criterion applied where the defect
lives; it leaves 2,616 anomalous pairs in 2.93 million fixes, mostly on the
last pair of a burst rather than the first.

The general lesson is worth more than the particular fix: **locating a defect
is what makes a proportionate remedy possible**. Without knowing the anomalies
sit on the first fix, the only safe options are to drop whole collars or to
accept the contamination.

## Subsampling does not remove it. It selects it.

The obvious objection to everything above is that these
data are analysed at one-minute or twenty-to-thirty-minute intervals, with
outliers filtered on speed or distance, so a defect confined to a ten-second
burst cannot reach anyone's results. Both halves of that are testable, and both
fail.

**Which fix does subsampling keep?** A resample to one sample per burst keeps
the first fix of each burst — that is what `.first()` returns, and it is the
natural implementation. It is also precisely the fix that carries the defect.
Of the 753,046 samples such a subsample yields, **29,441, or 3.91 %, are the
contaminated fix**, and they carry a position error with a median of 241 m and
a 90th percentile of 722 m.

**Would a speed filter catch them?** At twenty-minute spacing, a 241 m error
implies 0.20 m/s, and 722 m implies 0.60 m/s. Those are walking speeds for an
elephant. Of the 29,441, a threshold at 2 m/s removes **seven**. At 1 m/s it
removes 336, or 1.14 %. Subsampling dilutes the error below every plausible
threshold while preserving the positional error in full.

**Which fix of a flagged pair is the wrong one?** Both readings are available
in the burst itself. Over the 28,922 four-fix bursts whose first pair is
flagged, the first fix sits a median of **242.7 m** from the centroid of the
other three, while the second sits **2.2 m** from the centroid of the last two.
A factor of 111, and the first fix is the outlier in **100.0 %** of them. That
2.2 m is also an independent restatement of §5.1: the fixes that are not first
agree with each other to within metres.

The remedy therefore costs nothing at all, and it is neither a filter nor a
deletion:

> When subsampling a burst-sampled dataset, take the **second** fix of each
> burst rather than the first.

One word in one line of code. It removes the whole defect, discards no data,
and needs no threshold, no species and no judgement. It needs only the
knowledge that the defect is there.

That the defect stays invisible at the cadence these data are normally analysed
at is why it survived publication; that subsampling then selects for it is why
being invisible was never the same as being harmless.

A single script reproducing this from the public files is available at
`github.com/SebE585/etosha-batch-effect`.

# What the instrument yields when it is interrogated

Metrology is usually framed as a source of warnings. Interrogated properly, the
instrument produces results.

## The burst as a free state sensor

The Etosha collars fire four fixes ten seconds apart. Read as one measurement
rather than four positions, after removing uniform motion, the residual of the
fit is the receiver's short-term dispersion: **0.40 m at rest**, against
several metres of absolute accuracy for the same receivers.

This is not a contradiction. GPS error is strongly time-correlated over tens of
seconds, so short-term *relative* precision far exceeds absolute accuracy. It
also means a burst separates rest from motion with two orders of magnitude of
margin **without an accelerometer**, on a device that has no energy budget for
an inertial unit.

## Two independent estimates of position noise

On 19,208,637 fixes at 1 Hz from 26 baboons wearing e-obs collars
[@crofoot2021data; @strandburgpeshkin2015], position noise at rest was
estimated twice, by methods sharing no assumption:

- windows where the **measured Doppler speed** says the animal is stationary,
  which is not circular because Doppler is independent of the position
  solution: **0.62 to 0.93 m** per collar;
- the second difference of the **relative vector between two collars** in the
  same troop, where any variation is instrument error on two receivers:
  **0.53 to 0.92 m**.

The two converge on roughly 0.8 m.

## Calibration from gravity, and why pooling is wrong

The accelerometers ship raw ADC counts with no documented offset or gain.
Fitting a sphere to the raw vectors of at-rest bursts recovers both, using the
only reference available everywhere: at rest the sensor measures gravity alone,
so the cloud of raw vectors describes a sphere whose centre is the offset and
whose radius is counts per *g*.

Across eight collars of the same model the gain spans **389.7 to 443.9 counts
per g, a 12.5 % spread**, with a median fit residual of 1.14 %. Applying a
single fleet-wide calibration therefore costs up to 100 mg of error.

Per-device calibration is therefore not a refinement but a precondition: a
single fleet-wide gain puts an error of up to 100 mg into every derived
quantity.

## A prediction the data was not told about

Cadence of stride was extracted spectrally over 442,827 eight-second windows
and confronted with the **Doppler** speed, the two coming from sensors that do
not communicate.

The spectral resolution is 0.125 Hz, so the location of an argmax is a bin and
not a measurement. Interpolating the peak parabolically removes that
quantisation, and the result survives it: below 1.5 m/s the cadence rises from
1.38 to 1.99 Hz, a 44 % increase. Above, across seven speed classes from 1.6 to
4.5 m/s — a 177 % increase in speed — **it varies by 2.3 %**, from 1.894 to
1.937 Hz, while stride length alone grows.

Cadence saturating while stride length takes over is the canonical walk-run
transition. Figure 2 shows the spectral ridge against Doppler speed.

![Stride cadence against Doppler speed, 442,827 windows of 8 s
from seven baboons. The ridge is the argmax, which can only sit on a 0.125 Hz
bin; the sub-bin estimate quoted in the text varies by 2.3 % across the seven
classes above the transition, while speed rises by 177 %. The dashed line is
the transition predicted by a Froude number of 0.5, placed before the data were
examined.](figures/fig2-gait-froude.png)

Alexander and Jayes' dynamic similarity hypothesis places gait transitions at
comparable Froude numbers across quadrupedal mammals, the walk-run transition
falling near *Fr* = 0.5 [@alexander1983]. Taking a hip height of 0.40 m for an
adult olive baboon, the transition measured here sits at ***Fr* = 0.482**.

The inverse operation is tempting and should be resisted. Assuming exactly
*Fr* = 0.5 and solving for hip height returns 38.6 cm, plausible for the
species — but the transition Froude number is not a physical constant, it
varies between species and studies, so this is a consistency check and not a
measurement of the animal. What the data support is the agreement between a
transition located by two sensors that do not communicate and a dimensionless
prediction written thirty-six years before the collars were fitted.

## Wind aloft, and a validation with no external source

A bird circling in a thermal has a ground velocity that is the sum of a
rotating airspeed vector and a constant wind. Over one full turn the rotating
term averages out (method after [@weinzierl2016]). Applied to 60 white
storks, 7,165,703 fixes at 1 Hz [@flack2017data], this yields **19,565 complete spirals**, a
deduced airspeed of 9.03 m/s and climb rates with a median of 0.79 m/s, typical
of lowland thermals.

The validation uses no meteorological source. Two birds close together must
find the same wind; two birds far apart need not:

| Separation | Pairs | Median disagreement |
|---|---|---|
| under 2 km | 193,239 | **1.36 m/s** |
| 2–10 km | 23,835 | 1.95 |
| 10–50 km | 11,288 | 2.14 |
| 50–200 km | 47,197 | 2.62 |
| over 200 km | 38,082 | 3.85 |

Figure 3 plots that growth against distance.

![Disagreement between two independent wind estimates against
the distance separating the two birds, 19,565 spirals from 60 white storks.
Noise would give the same value at every distance.](figures/fig3-wind-structure.png)

Noise would give the same value at every distance. The monotone growth is what
shows the estimate carries real spatial information.

Turning that floor into a per-spiral error needs more care than it first
appears. Variances of independent errors add, so dividing by $\sqrt{2}$ is the
right operation, but on a variance and not on a median. Applied to the root
mean square of 1.94 m/s it gives **1.37 m/s per spiral**; applied to the median
it would give 0.96, and the distribution is skewed enough (skewness 1.25,
median/RMS 0.70 against 0.94 for a Rayleigh) that no single statistic describes
it well. The defensible figure is of order **1 to 1.4 m/s**, and the quantity
to quote is the 1.36 m/s median disagreement itself.

Two caveats on the control. Birds under 2 km apart are often in the same
thermal, so they share the wind, which is the point. But soaring birds also
coordinate, matching turn radius and drift correction on their neighbours, and
shared behaviour would correlate their errors and depress the floor. It is
therefore an upper bound on achievable agreement, and the per-spiral error is
more likely under- than over-stated.

## What cadence costs, briefly

That sampling cadence biases path length is long established in movement
ecology and is not a contribution of this paper. One number is worth keeping
because it is operational rather than geometric: on the Etosha corpus, against
the real park fence polygon, a collar at the hourly cadence standard in the
field detects 112 of the 206 crossings visible at native resolution. **It
misses 46 % of park exits.**

Figure 4 gives the count at each cadence. For a protected-area manager
choosing a duty cycle, that is a different quantity from a biased distance
estimate, and it is the one that decides whether the deployment answers its own
question.

![Crossings of the real Etosha fence polygon against sampling
cadence. Same fixes throughout; only the interval
changes.](figures/fig4-cadence-cost.png)

## The thread running through five of the six

Every result above except 5.6 comes from **measuring twice so that the
discrepancy becomes the control**: Doppler against position, two birds in one
thermal, two collars in one troop, two independent noise estimators. Section
5.6 is the exception and does not belong to this family — it subsamples a
single trace against a fixed polygon, which is why it is reported as an
operational number rather than as a measurement of the instrument. The
method held from beginning to end everywhere it applied.

---

# What a format would have to record

If a corpus is this heterogeneous, what would it take to describe it
faithfully? I put the same 388 datasets through an open pivot format for
mobility data [@telemachus], versions 1.0.0a3 and 1.0.0a4 installed from PyPI,
and validated
the output.

The first result is a specification failure, not a corpus one. **89 % of
non-conformities (274 of 309) were caused by a single mandatory column**: a
Doppler ground speed, which no energy-constrained receiver emits. 278 of 388
datasets do not carry one, and **not one of them could be conformant**.

Making that column conditional takes conformance from **20.4 % to 90.7 %** of
the 388 datasets that could be evaluated, 79 to 352. Rates over all 447 items
downloaded are 17.7 % and 78.7 %, but 59 of those carry no position data at all
and can be neither conformant nor not; the 388 denominator is the honest one
and is used here throughout. The measurement was repeated against the published
wheel and against the source branch, with **zero datasets classified
differently out of 447**, so the figure holds for what users install and not
only for what the code does.

The second result concerns provenance. Of the 110 datasets that do declare a
speed, the validator judges **47 of them derived from their own positions,
43 %**. Almost one declared speed in two is not a measurement, and nothing in
the file says so.

This is not cosmetic. Section 5.2 above selects stationary samples *by Doppler
speed*, precisely because Doppler is independent of the position solution.
Doing the same with a position-derived speed is circular: it returns a
plausible number that means nothing, and no error is raised anywhere. The two
carry the same column name.

A format for this corpus therefore needs, at minimum: mandatory columns that
are conditional on what the receiver measures, and a per-column declaration of
whether a value was measured or derived.

---

# Silent failure as a class

The bench described above took two days to build. In that time it produced
thirteen failures that raised no exception and returned plausible results. Six
were in my own tools, including one in the guard written against silent
failures, one in the measuring instrument itself, one in the headline
conclusion of this paper, one in the correction of that conclusion, and one in
the table that was supposed to establish it.

I list them because the list is the reusable part of this paper. They are
separated by consequence, because the two kinds are not equally interesting: a
wrong number that reaches a reader is a scientific problem, a broken build is
not.

## Failures that put a wrong number in a document

1. **The headline mechanism of this paper, wrong on first writing.** The fleet
   split cleanly by delivery batch, so I concluded two populations of hardware.
   An adversarial reading of the draft objected that a firmware revision or
   battery ageing fitted the same observation, and that the standard cause of
   intra-burst outliers — a receiver emitting before its solution converges —
   had not been examined at all. Both objections were testable in data I already had. The
   split was real, the mechanism was not, and the correct one yields a targeted
   remedy where mine required treating fifteen animals as two groups.
2. **The tables that replaced it, also wrong.** Sections 4.1 and 4.2 are the
   evidence for the corrected mechanism. Their first published version
   overstated the concentration on the first pair (99.93 % against a true
   91.8 %), understated the residue by two orders of magnitude (23 anomalous
   pairs against 2,616), reported a remedy cost 14 % too low, and gave a
   year-by-year table that reproduces under no definition of the rate at all —
   it also failed to state which one it used. The conclusions survived; six of
   the numbers supporting them did not. The cause is the one this paper argues
   against everywhere else: every other figure here is produced by a committed
   script that writes a file which the text and the plots both read, and this
   one was computed in a throwaway shell and typed in by hand. It
   survived two revisions and two adversarial readings. The third added up the
   column and found it did not reach a total published four pages earlier.
3. **A density plotted in linear space on a logarithmic axis**, crushing the
   right-hand mass and hiding a bimodality that turned out to carry the main
   result.
4. **A spectral resolution of 1 Hz mistaken for a biological plateau.** Stride
   cadence came out at exactly 2.0 Hz at every speed. That was the FFT bin
   width, not the animal. Splicing the contiguous records into 8 s windows took
   the resolution to the 0.125 Hz used in section 5.4, and the plateau moved
   but did not disappear; only parabolic interpolation inside the bin showed
   what it really was.
5. **A `sensor-type contains "gps"` filter** that silently excluded all 46
   Argos datasets, which is exactly the population whose quality was most in
   question. The filter deleted the question instead of asking it.
6. **`.astype("int64")` returning microseconds** rather than nanoseconds in a
   newer pandas, collapsing a thousand seconds into one, so a deduplication
   removed 99.8 % of records believing they were duplicates.
7. **An adapter silently accepting a column mapping and dropping it**,
   producing an all-null identifier column, which turned an entity-aware
   deduplication into a global one: 64 % of a file destroyed, 29 of 30 animals
   gone, validation reporting PASS with no warning.
8. **A missing unit declaration** in a conversion mapping, causing 122 datasets
   to be rejected for a reason that had nothing to do with the format under
   test, and briefly producing a completely wrong headline figure.
9. **A quality guard that discarded its own findings** on the default code
   path, so the manifest recorded "checked, nothing found" when it meant
   "checked, result not kept". Written by the author, in the very feature
   intended to prevent silent loss.

## Failures in the machinery around it

These cost time rather than truth, and are listed only because their shape is
the same.

10. **A specification and its implementation disagreeing.** A normative section
    was rewritten to make a column conditional; the Python set the validator
    consults was never touched. Two people read the changed text closely and
    neither looked at the set. The published release refused files its own text
    declared valid.
11. **The measuring instrument importing the published package** rather than
    the corrected working copy. Both report the same version string; only the
    filesystem path distinguishes them.
12. **A `pip install` piped into `tail`**, whose exit status is that of the
    last element of the pipe, so a failed installation reported success.
13. **A correction that silently did not apply.** One `str.replace` no longer
    matched its target because an earlier edit had changed the surrounding text
    by one word. Python returns the string unchanged rather than raising, and
    my verification was a `grep` over an alternation of three patterns: two
    matched, the count looked like success, and the third was the one that
    mattered.

## What they have in common

Nearly all are a **false assertion where an unknown should have been
declared**. An empty list of findings that means "not collected". A profile
deemed conformant because a table and a code path agreed with each other and
were both wrong. A version string that cannot distinguish two import paths.

Two are worse than a silent failure, and they are the two that concern the
argument of this paper rather than its plumbing: a conclusion and then a table
that were **plausible, internally consistent, and supported by a real signal**.
Neither was questioned from inside the work. Both moved only under a question
the author had not thought to ask — first "what else produces this table", then
"does this column add up".

That is the honest limit of the three rules below: none of them would have
caught either one. What caught them was adversarial reading from outside the
work, which is a dependency rather than a method, and it is worth saying so
plainly rather than presenting the corrections as internal quality control.

## Three rules

- **A test that can no longer fail must say so.** A canary that fails when the
  parser stops measuring is worth more than a green test.
- **Declare the instrument before the number**, and the path, not only the
  version.
- **Measure twice so that the discrepancy is the control** — including against
  yourself: the table in section 4.1 now recomputes a total that another script
  derives independently, and refuses to write its output if the two disagree.

The pattern is structural, and nobody is exempt from it, least of all those
looking for it.

---

# Limitations

- The detector **flags**; it does not prove a defect. A column may legitimately
  begin to carry values.
- The batch effect rests on **one dataset**. It is a case study demonstrating
  the method, not a general claim about a manufacturer or a production era.
- The corpus is limited to what authors chose to publish in one repository.
  Publication bias is not measured and is likely large.
- The Etosha collars date from 2008 and 2009.
- The conversion mapping is built by introspecting the columns present, dataset
  by dataset. A different mapping would convert a few more or fewer datasets,
  moving the third decimal but not the taxonomy.
- **The 8-second spectral windows assume stationarity** (§5.4). A wild animal's
  speed and cadence fluctuate within that span, which smears the peak, and
  parabolic interpolation assumes a clean symmetric peak. The sub-bin figures
  should be read as indicative rather than precise.
- Position noise figures (§5.2) were measured in open savanna. Urban multipath
  would raise the floor; the mechanism holds, the value does not.
- **No absolute ground truth anywhere.** Every validation here is relative or
  comparative: Doppler against position, one collar against another, a
  measurement against an external prediction. No collar was ever placed on a
  surveyed point or carried alongside a differential receiver. The bench
  therefore establishes internal consistency and detects disagreement; it does
  not establish accuracy against a known coordinate.
- **The out-and-back detector is blind to slow correlated drift.** It compares
  three consecutive positions, so a receiver drifting smoothly over minutes
  under multipath or ionospheric disturbance produces a locally smooth track
  and is never flagged. That failure mode is arguably worse for home-range
  estimation than the isolated spikes the detector does catch, and nothing
  here measures it.

---

# Data and code availability

The bench, the 353 per-dataset quality sheets and the repository inventory are
archived with a DOI. The single-result reproduction of §4 is at
`github.com/SebE585/etosha-batch-effect` and runs from the public files with
pandas and numpy alone.

All figures regenerate from the archived code.

The list of the 29,441 fixes flagged by §4.1 is included in the archive, keyed
by collar and timestamp, so that the dataset's curators can apply or reject the
remedy without rerunning anything.

# Acknowledgements {-}

To the authors and curators who published these datasets openly. A corpus that
can be measured is a corpus someone chose to make measurable, and that choice
precedes every result above.

Successive drafts were read adversarially rather than for approval, and three
of the corrections recorded in section 7 come from that. The author remains
solely responsible for the analysis, the code, and every number above,
including the ones that had to be corrected twice.
