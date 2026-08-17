"""
ICHNOS -- one-page quality sheet for a dataset.

One page, not pretty, useful. Written for the people who own the data: it
tells them what their dataset actually carries, and above all which analyses
it does not support.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "out"


def _duree(s):
    if s != s:
        return "inconnue"
    if s < 90:
        return f"{s:.0f} s"
    if s < 5400:
        return f"{s/60:.0f} min"
    if s < 172800:
        return f"{s/3600:.1f} h"
    return f"{s/86400:.1f} j"


def fiche(r, licence: str, valid: dict) -> str:
    """Build the sheet. English, like the paper and the repository it accompanies.

    Two things are no longer typed by hand. The licence comes from
    licences.parquet, because 34 datasets in the corpus are CC BY-NC and a
    sheet that stays silent invites a use its source forbids. And the
    validation figures come from detector_validation.json, because the
    previous version announced 237 datasets where the test counts 287.
    """
    L = []
    A = L.append
    A(f"# {r.titre}\n")
    A(f"ICHNOS quality sheet. Movebank Data Repository, item `{r.uuid}`.")
    A(f"Source licence: **{licence}**."
      + ("\n\n> This dataset is published under a non-commercial licence. This"
         " sheet is derived from it and inherits that restriction.\n"
         if "NonCommercial" in licence else "\n"))

    A("## What the dataset carries\n")
    A("| | |")
    A("|---|---|")
    A(f"| Dominant sensor | {r.get('capteur') or 'not declared'} |")
    A(f"| Fixes | {int(r.n_fixes):,} |")
    A(f"| Individuals | {int(r.n_individus)} |")
    A(f"| Span | {r.jours:.0f} days |")
    A(f"| Median cadence | {_duree(r.cadence_mediane_s)} |")
    A(f"| Dominant cadence | {_duree(r.cadence_mode_s)} |")
    A(f"| Regularity | {r.regularite_pct:.0f} % of intervals at the dominant step |")
    A(f"| 95th percentile of gaps | {_duree(r.gap_p95_s)} |\n")

    A("## Three quality measures\n")
    A("| Measure | Value | Reading |")
    A("|---|---|---|")

    p = r.pct_pics
    lp = ("nothing notable" if p < 0.01 else
          "a few isolated outliers" if p < 0.05 else
          "**high rate, filter before analysis**")
    A(f"| Position spikes | {p:.3f} % | {lp} |")

    q = r.pct_positions_repetees
    lq = ("nothing notable" if q < 1 else
          "frequent repeats" if q < 5 else
          "**a major share of rows carries no new position**")
    A(f"| Repeated positions | {q:.2f} % | {lq} |")

    d, pm = r.decimales_lat, r.pas_min_m
    ld = ("precision preserved" if d >= 6 else
          "acceptable grain" if d == 5 else
          f"**coordinates truncated at export, grid of about {pm:.0f} m**")
    A(f"| Coordinate grain | {int(d)} decimals | {ld} |\n")

    A("## What this dataset does not support\n")
    lim = []
    if d <= 4:
        lim.append(f"Any analysis finer than **{pm:.0f} m**: the precision was "
                   "destroyed before publication and is not recoverable.")
    if q > 5:
        lim.append(f"Fix counts as a measure of effort: **{q:.0f} %** of rows "
                   "repeat the previous position exactly.")
    if p > 0.05:
        lim.append(f"Unfiltered path length: **{p:.2f} %** of triplets show an "
                   "out-and-back incompatible with that individual's own step.")
    if r.regularite_pct < 60:
        lim.append("Comparing distances between individuals without resampling: "
                   f"only **{r.regularite_pct:.0f} %** of intervals are at the "
                   "dominant step.")
    if not lim:
        lim.append("No limitation detected by this bench. That does not mean the "
                   "dataset is sound, only that it passes these three tests.")
    for x in lim:
        A(f"- {x}")

    A("\n## Method\n")
    A("Out-and-back detector, no scale and no species: over three consecutive "
      "positions A, B, C the excursion is `(AB + BC - AC) / 2`, compared to the "
      "95th percentile of **that individual's own** step. This avoids any "
      "species-dependent threshold. A fix is flagged past ten times its own "
      "yardstick.\n")
    v = valid["primary"]
    A(f"Validation: applied unchanged across the corpus, this detector recovers "
      f"the documented precision gap between Argos and GPS on its own, over the "
      f"{v['n_total']} datasets labelled as one or the other "
      f"(median {v['median_argos_pct']:.3f} % against "
      f"{v['median_gps_pct']:.3f} %, Mann-Whitney p = {v['p']:.1e}), without "
      "being told anything about the positioning system.\n")
    A("This bench judges neither the science nor the fieldwork. It measures "
      "what the published file carries, and what it does not.\n")
    A("A contested measurement is a useful one: if this result looks wrong to "
      "you, the author would rather know.\n")
    A("---\n")
    A("*ICHNOS Field Clause, non-binding. This bench is free to use. If it was "
      "useful to you, and you work somewhere where things move, you are "
      "invited, and never required, to invite its author to come and see it.*")
    return "\n".join(L)


def main():
    import json

    d = pd.read_parquet(OUT / "corpus_quality.parquet")
    lic = pd.read_parquet(OUT / "licences.parquet").set_index("uuid").licence
    valid = json.loads((OUT / "detector_validation.json").read_text())
    ok = d[d.statut == "ok"]
    dst = OUT / "quality_sheets"
    dst.mkdir(exist_ok=True)
    manquantes = 0
    for _, r in ok.iterrows():
        licence = lic.get(r.uuid)
        if not isinstance(licence, str) or not licence:
            licence, manquantes = "not declared", manquantes + 1
        (dst / f"{r.uuid[:8]}.md").write_text(fiche(r, licence, valid))
    nc = int(sum("NonCommercial" in str(lic.get(u, "")) for u in ok.uuid))
    print(f"{len(ok)} sheets written to {dst}")
    print(f"  of which {nc} derived from a non-commercial dataset, marked as such")
    if manquantes:
        print(f"  {manquantes} with no declared licence")


if __name__ == "__main__":
    main()
