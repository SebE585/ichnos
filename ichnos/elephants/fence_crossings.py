"""
ICHNOS -- do the elephants leave the reserve, or does the receiver?

A user of the bench built line trajectories from the Etosha deposit and saw
tracks crossing the park boundary. That is an ecological claim, animals moving
outside a fenced reserve, resting on positions the bench flags as an instrument
property: the first fix of a burst carries a median error of 241 m.

M4 in bench.py already measures how many crossings a given sampling interval
lets you see. This asks the other question: are the crossings the instrument?
It compares the outside rate of the flagged fixes with the outside rate of the
others, which is the control that a bare count cannot replace, since an animal
walking the fence line puts good fixes on both sides.

Writes out/etosha_fence.json and out/etosha_fence_excursions.parquet.

Numpy only, like bench.py: the shapefile reader, the projection and the
point-in-polygon test come from there, so this script adds no dependency.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# The scripts of this repository are standalone and are run from the root, so
# a sibling is imported by path rather than as a package.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bench import point_in_poly, read_shp_polygons, wgs84_to_utm  # noqa: E402

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "out"
DATA = BASE / "data"

FIXES = DATA / ("African elephants in Etosha National Park "
                "(data from Tsalyuk et al. 2018).csv")
FENCE = DATA / "enp_fence" / "enp fence poly.shp"
FLAGGED = OUT / "etosha_flagged_fixes.csv"

# An excursion is scored against the fence itself and against a band around it.
# A flagged fix has a median error of 241 m, so an excursion that stays inside
# the band is not evidence either way: it is the fence line seen through the
# receiver's own scatter.
BAND_M = 500.0


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((c - h) / d, (c + h) / d)


def dist_to_ring(x, y, ring):
    """Shortest distance from each point to a closed polyline, in metres."""
    ax, ay = ring[:-1, 0], ring[:-1, 1]
    bx, by = ring[1:, 0], ring[1:, 1]
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    L2[L2 == 0] = 1e-12

    out = np.empty(len(x))
    # Chunked: the full point-by-segment matrix would be several GB.
    for s in range(0, len(x), 20000):
        px = x[s:s + 20000, None]
        py = y[s:s + 20000, None]
        t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0.0, 1.0)
        cx, cy = ax + t * dx, ay + t * dy
        out[s:s + 20000] = np.sqrt((px - cx) ** 2 + (py - cy) ** 2).min(axis=1)
    return out


def main() -> None:
    ring = max(read_shp_polygons(FENCE), key=len)
    if not np.allclose(ring[0], ring[-1]):
        ring = np.vstack([ring, ring[:1]])

    raw = pd.read_csv(
        FIXES,
        usecols=["timestamp", "location-long", "location-lat", "visible",
                 "individual-local-identifier"],
        parse_dates=["timestamp"],
        low_memory=False,
    ).rename(columns={"location-long": "lon", "location-lat": "lat",
                      "individual-local-identifier": "collar"})

    # The deposit ships the curators' own outliers in the file and marks them
    # invisible. Movebank hides them, a CSV reader does not. Counted here
    # rather than dropped in silence: two of the five are the deepest
    # excursions in the file and neither is a movement.
    hidden = raw[raw.visible == False]  # noqa: E712
    fx = raw[raw.visible == True].copy()  # noqa: E712
    fx = fx.dropna(subset=["lon", "lat"]).sort_values(["collar", "timestamp"])

    fg = pd.read_csv(FLAGGED, parse_dates=["discarded_fix_ts"])
    flagged = set(zip(fg.device_id, fg.discarded_fix_ts))
    fx["flagged"] = [(c, t) in flagged
                     for c, t in zip(fx.collar, fx.timestamp)]

    E, N = wgs84_to_utm(fx.lat.values, fx.lon.values)
    fx["inside"] = point_in_poly(E, N, ring)

    fx["d_fence_m"] = np.nan
    out_mask = (~fx.inside).values
    fx.loc[out_mask, "d_fence_m"] = dist_to_ring(E[out_mask], N[out_mask], ring)

    n = len(fx)
    out_all = int(out_mask.sum())
    fl, un = fx[fx.flagged], fx[~fx.flagged]
    out_fl, out_un = int((~fl.inside).sum()), int((~un.inside).sum())

    # An excursion is a run of consecutive outside fixes within one collar.
    fx["run"] = ((fx.inside != fx.inside.shift()) |
                 (fx.collar != fx.collar.shift())).cumsum()
    exc = (fx[~fx.inside]
           .groupby("run")
           .agg(collar=("collar", "first"),
                start=("timestamp", "first"),
                end=("timestamp", "last"),
                n_fixes=("timestamp", "size"),
                n_flagged=("flagged", "sum"),
                max_d_m=("d_fence_m", "max"))
           .reset_index(drop=True))
    exc["deep"] = exc.max_d_m > BAND_M

    single = exc[exc.n_fixes == 1]
    by_collar = (exc[exc.deep].groupby("collar")
                 .agg(n=("n_fixes", "size"), fixes=("n_fixes", "sum"),
                      max_d_m=("max_d_m", "max")))

    res = {
        "n_rows_in_file": len(raw),
        "n_marked_invisible": len(hidden),
        "n_fixes": n,
        "n_flagged": int(fx.flagged.sum()),
        "n_outside": out_all,
        "outside_rate": out_all / n,
        "outside_rate_flagged": out_fl / len(fl),
        "outside_rate_flagged_ci": wilson(out_fl, len(fl)),
        "outside_rate_unflagged": out_un / len(un),
        "outside_rate_unflagged_ci": wilson(out_un, len(un)),
        "n_excursions": len(exc),
        "n_excursions_single_fix": len(single),
        "n_excursions_single_fix_flagged": int((single.n_flagged == 1).sum()),
        "band_m": BAND_M,
        "n_excursions_deep": int(exc.deep.sum()),
        "deep_by_collar": by_collar.reset_index().to_dict("records"),
        "q75_max_d_m": float(exc.max_d_m.quantile(0.75)),
        "top_collar_share_of_outside_fixes":
            float(exc.groupby("collar").n_fixes.sum().max() / exc.n_fixes.sum()),
        "collars_with_excursion": int(exc.collar.nunique()),
        "collars_total": int(fx.collar.nunique()),
    }

    OUT.mkdir(exist_ok=True)
    (OUT / "etosha_fence.json").write_text(json.dumps(res, indent=2,
                                                      default=str))
    exc.to_parquet(OUT / "etosha_fence_excursions.parquet", index=False)

    for k, v in res.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
