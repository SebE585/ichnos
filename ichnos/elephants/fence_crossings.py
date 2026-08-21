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

It reads a pivot file and a boundary polygon, both named on the command line,
so the control is not tied to this deposit. Etosha is the default because it is
the only case in the repository that ships a boundary.

    python3 -m ichnos.elephants.fence_crossings
    python3 -m ichnos.elephants.fence_crossings --source kruger --polygon ...

Writes out/<source>_fence.json and out/<source>_fence_excursions.parquet.

Numpy only, like bench.py: the shapefile reader, the projection and the
point-in-polygon test come from there, so this script adds no dependency.
"""

from __future__ import annotations

import argparse
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

FENCE = DATA / "enp_fence" / "enp fence poly.shp"

# The projection of bench.py is the transverse Mercator of UTM zone 33S, which
# is the zone of the Etosha polygon. Another boundary in another zone needs its
# own central meridian, hence the option rather than a constant.
ZONE_CM_DEG = 15.0

# An excursion is scored against the fence itself and against a band around it.
# A flagged fix has a median error of 241 m, so an excursion that stays inside
# the band is not evidence either way: it is the fence line seen through the
# receiver's own scatter.
BAND_M = 500.0


def to_numpy_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Bring an arrow-backed frame back to plain numpy dtypes.

    The pivot files carry `bool[pyarrow]` and pandas string columns. Neither
    `cumsum` nor the OGR drivers accept them, and both fail late with a message
    about a dtype rather than about the data. Converted once, at the door.
    """
    for c in df.columns:
        d = str(df[c].dtype)
        if "bool" in d and d != "bool":
            df[c] = df[c].fillna(False).to_numpy(dtype=bool)
        elif d in ("string", "str") or "string" in d:
            df[c] = df[c].astype(object)
    return df


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
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--source", default="etosha",
                    help="pivot file to read, out/<source>_pivot.parquet")
    ap.add_argument("--polygon", default=str(FENCE),
                    help="boundary shapefile, projected")
    ap.add_argument("--zone-cm-deg", type=float, default=ZONE_CM_DEG,
                    help="central meridian of the polygon's UTM zone")
    ap.add_argument("--flags", default=None,
                    help="list of flagged keys; defaults to "
                         "out/<source>_flagged_fixes.csv")
    a = ap.parse_args()

    ring = max(read_shp_polygons(a.polygon), key=len)
    if not np.allclose(ring[0], ring[-1]):
        ring = np.vstack([ring, ring[:1]])

    pivot = OUT / f"{a.source}_pivot.parquet"
    if not pivot.exists():
        raise SystemExit(f"{pivot} is missing: run the adapter first")
    raw = to_numpy_dtypes(pd.read_parquet(pivot)).rename(
        columns={"device_id": "collar", "ts": "timestamp"})

    # A Movebank export ships the curators' own outliers and marks them
    # invisible. The repository interface hides them, a reader does not.
    # Counted here rather than dropped in silence: on Etosha two of the five
    # are the deepest excursions in the file and neither is a movement.
    if "x_movebank_visible" in raw.columns:
        keep = raw.x_movebank_visible.fillna(True)
        hidden, fx = raw[~keep], raw[keep].copy()
    else:
        hidden, fx = raw.iloc[:0], raw.copy()
    fx = fx.dropna(subset=["lon", "lat"]).sort_values(["collar", "timestamp"])

    flags = Path(a.flags) if a.flags else OUT / f"{a.source}_flagged_fixes.csv"
    if flags.exists():
        fg = pd.read_csv(flags, parse_dates=["discarded_fix_ts"])
        keys = set(zip(fg.device_id,
                       pd.to_datetime(fg.discarded_fix_ts, utc=True)))
        fx["flagged"] = [(c, t) in keys
                         for c, t in zip(fx.collar, fx.timestamp)]
    else:
        print(f"no flag list at {flags}: the control has nothing to compare")
        fx["flagged"] = False

    E, N = wgs84_to_utm(fx.lat.values, fx.lon.values,
                        zone_cm_deg=a.zone_cm_deg)
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
    (OUT / f"{a.source}_fence.json").write_text(
        json.dumps(res, indent=2, default=str))
    exc.to_parquet(OUT / f"{a.source}_fence_excursions.parquet", index=False)

    for k, v in res.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
