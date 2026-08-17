"""
ICHNOS -- blind validation of the detector against an already documented gap.

This is the measurement that licenses everything else in the paper: the
detector, told nothing about the positioning system, must recover on its own
the known precision gap between Argos and GPS. If it does not, none of the
other measurements is worth anything, since the same detector produces them.

This script exists because that figure lived nowhere but hard-coded in an email
template. It was right, which excuses nothing: a number that licenses the rest
of a paper cannot be a string literal.

The convention is stated because it changes the third digit of p: the
comparison is the `gps` sensor label against `argos-doppler-shift`. The corpus
also carries a single item labelled `gnss`; including it gives p = 3.07e-07
instead of 3.45e-07, the same conclusion. It is excluded to keep to a single
label, and the script reports both.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from scipy.stats import mannwhitneyu

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "out"

ARGOS = "argos-doppler-shift"


def test(d: pd.DataFrame, gps_labels) -> dict:
    g = d[d.capteur.isin(gps_labels)].pct_pics.dropna()
    a = d[d.capteur == ARGOS].pct_pics.dropna()
    u, p = mannwhitneyu(a, g, alternative="greater")
    return {
        "gps_labels": list(gps_labels),
        "n_gps": int(len(g)),
        "n_argos": int(len(a)),
        "n_total": int(len(g) + len(a)),
        "median_gps_pct": round(float(g.median()), 4),
        "median_argos_pct": round(float(a.median()), 4),
        "U": float(u),
        "p": float(p),
    }


def main():
    d = pd.read_parquet(OUT / "corpus_quality.parquet")

    primary = test(d, ["gps"])
    sensitivity = test(d, ["gps", "gnss"])

    res = {
        "question": "does the detector recover the Argos/GPS gap on its own?",
        "measure": "pct_pics, share of positions the detector flags as a spike",
        "hypothesis": "Argos greater than GPS, one-sided",
        "primary": primary,
        "sensitivity_with_gnss": sensitivity,
        "conclusion_robust": primary["p"] < 1e-5 and sensitivity["p"] < 1e-5,
    }

    # Guard: the conclusion must not depend on a sensor label.
    if not res["conclusion_robust"]:
        raise AssertionError(
            "the Argos/GPS gap does not survive a change of sensor label; "
            "the detector validation must be redone before anything is published"
        )

    (OUT / "detector_validation.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
