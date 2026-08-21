"""
ICHNOS -- GIS layers from any pivot file: points, tracks, day paths.

The bench publishes lists of keys, not positions. This turns one of its pivot
files into layers a GIS can open, with whatever quality column the source
actually carries, so that a map shows the measurement and not only the animal.

It reads `out/<source>_pivot.parquet`, so it works on every dataset an adapter
has converted, not on one hard-wired CSV. The first version of this script was
written for the Etosha deposit alone, at the request of the first outside user
of the bench; nothing in it was specific to elephants except the file name.

Three things it does that a group-by and a `LineString` do not, and each one
changes what the map shows:

  - It drops the rows the source itself marks hidden, `visible = false` in the
    Movebank export. The repository interface hides them, a CSV reader does
    not. On the Etosha deposit there are five, and two of them sit 38 km and
    1,419 km outside the park: specks as points, the longest line on the map.
  - It splits a trajectory wherever the carrier stops reporting for longer than
    the gap. A single line per carrier draws a straight segment across a
    three-month silence, and that segment is not a movement.
  - It keeps the timestamp as an ISO text field, because the shapefile
    attribute table has no date-time type and truncates names to ten
    characters. The time of day is what a vegetation index compositing needs.

Usage, from the repository root:

    python3 -m ichnos.common.export_gis                     # etosha
    python3 -m ichnos.common.export_gis --source storks_gps
    python3 -m ichnos.common.export_gis --list

Writes out/<source>_points.gpkg, _tracks.gpkg, _daypaths.gpkg, and the line
layers as shapefiles under out/shp/.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

# The bench itself runs on pandas and numpy alone. This export is the one place
# that writes GIS files, so geopandas is optional and asked for here rather
# than at the top of requirements.txt.
try:
    from shapely.geometry import LineString

    import geopandas as gpd
except ImportError:  # pragma: no cover
    raise SystemExit("this script needs geopandas: pip install geopandas")

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "out"

# Nominal spacing on the default source is one burst every twenty minutes. Six
# hours is eighteen missed bursts: past that, a straight line between two fixes
# says more about the gap than about the animal. A source with a different
# cadence wants a different value, hence the option.
GAP_H = 6.0

# The points layer is one feature per fix. Nineteen million of them is a
# multi-gigabyte file that no GIS opens comfortably, so above this the layer is
# skipped and the skip is announced. The line layers are written regardless.
MAX_POINTS = 5_000_000

# Quality columns worth carrying onto the map when the source has them. The
# rule is the one the capability descriptor follows: report what is there,
# invent nothing.
EXTRA = {
    "h_accuracy_m": "h_acc_m",
    "x_eobs_type_of_fix": "fix_type",
    "x_movebank_manual_outlier": "manual_out",
}


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


def sources() -> list[str]:
    return sorted(p.name[:-len("_pivot.parquet")]
                  for p in OUT.glob("*_pivot.parquet"))


def load(source: str, flags: Path | None) -> pd.DataFrame:
    pivot = OUT / f"{source}_pivot.parquet"
    if not pivot.exists():
        raise SystemExit(f"{pivot} is missing. Known sources: "
                         f"{', '.join(sources()) or 'none, run an adapter first'}")

    cols = ["ts", "lat", "lon", "device_id"] + list(EXTRA)
    have = pd.read_parquet(pivot, columns=None).columns
    df = pd.read_parquet(pivot, columns=[c for c in cols if c in have]
                         + (["x_movebank_visible"]
                            if "x_movebank_visible" in have else []))

    if "x_movebank_visible" in df.columns:
        hidden = int((~df.x_movebank_visible.fillna(True)).sum())
        if hidden:
            print(f"{hidden} rows marked visible=false, dropped")
        df = df[df.x_movebank_visible.fillna(True)]
        df = df.drop(columns=["x_movebank_visible"])

    df = to_numpy_dtypes(df).dropna(subset=["lat", "lon"])

    df["flagged"] = False
    if flags is not None and flags.exists():
        fg = pd.read_csv(flags, parse_dates=["discarded_fix_ts"])
        keys = set(zip(fg.device_id,
                       pd.to_datetime(fg.discarded_fix_ts, utc=True)))
        df["flagged"] = [(d, t) in keys
                         for d, t in zip(df.device_id, df.ts)]
        print(f"{int(df.flagged.sum())} fixes flagged from {flags.name}")
    elif flags is not None:
        print(f"no flag list at {flags}, the flagged column stays false")

    # Rows sharing a timestamp within one carrier are not duplicates: the
    # Etosha deposit stores whole seconds and a burst can put two fixes inside
    # one, a metre or two apart. They do make a sort on the timestamp alone
    # non-deterministic, so latitude breaks the tie and the vertex order of a
    # line is reproducible from one run to the next.
    return (df.sort_values(["device_id", "ts", "lat"], kind="stable")
              .reset_index(drop=True))


def segments(df: pd.DataFrame, gap_h: float) -> pd.DataFrame:
    dt = df.groupby("device_id", observed=True).ts.diff().dt.total_seconds()
    new = dt.isna() | (dt > gap_h * 3600.0)
    return df.assign(seg=new.cumsum())


def lines(df: pd.DataFrame, key: list[str], name: str) -> gpd.GeoDataFrame:
    rows = []
    for k, g in df.groupby(key, sort=True, observed=True):
        if len(g) < 2:
            continue
        k = k if isinstance(k, tuple) else (k,)
        rows.append({
            "carrier": str(g.device_id.iloc[0]),
            "seg": str(k[-1]),
            "start": g.ts.iloc[0].strftime("%Y-%m-%dT%H:%M:%S"),
            "end": g.ts.iloc[-1].strftime("%Y-%m-%dT%H:%M:%S"),
            "n_fix": len(g),
            "dur_h": round((g.ts.iloc[-1] - g.ts.iloc[0]).total_seconds()
                           / 3600.0, 2),
            "pct_flag": round(100.0 * g.flagged.mean(), 3),
            "geometry": LineString(zip(g.lon.values, g.lat.values)),
        })
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    print(f"{name}: {len(gdf)} lines")
    return gdf


def write(gdf: gpd.GeoDataFrame, stem: str, layer: str,
          shapefile: bool = True) -> None:
    # The OGR drivers want plain object columns; recent pandas hands them a
    # StringDtype and the write dies on schema inference.
    for c in gdf.columns:
        if c != "geometry" and (gdf[c].dtype.kind in "OU"
                                or str(gdf[c].dtype) == "string"):
            gdf[c] = gdf[c].astype(object)

    gdf.to_file(OUT / f"{stem}.gpkg", layer=layer, driver="GPKG")
    if shapefile:
        shp = OUT / "shp"
        shp.mkdir(parents=True, exist_ok=True)
        gdf.to_file(shp / f"{stem}.shp", driver="ESRI Shapefile")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--source", default="etosha",
                    help="pivot file to read, out/<source>_pivot.parquet")
    ap.add_argument("--flags", default=None,
                    help="list of flagged keys; defaults to "
                         "out/<source>_flagged_fixes.csv when it exists")
    ap.add_argument("--gap-h", type=float, default=GAP_H,
                    help=f"a track is cut on a silence longer than this "
                         f"(default {GAP_H} h)")
    ap.add_argument("--max-points", type=int, default=MAX_POINTS,
                    help="skip the points layer above this many fixes")
    ap.add_argument("--no-shapefile", action="store_true",
                    help="GeoPackage only")
    ap.add_argument("--list", action="store_true",
                    help="list the pivot files available and exit")
    a = ap.parse_args()

    if a.list:
        for s in sources():
            print(s)
        return

    flags = (Path(a.flags) if a.flags
             else OUT / f"{a.source}_flagged_fixes.csv")
    df = segments(load(a.source, flags), a.gap_h)
    shp = not a.no_shapefile

    if len(df) > a.max_points:
        print(f"points: {len(df):,} fixes, above the {a.max_points:,} limit, "
              f"layer skipped (raise --max-points to write it anyway)")
    else:
        cols = {"carrier": df.device_id.astype(str).astype(object),
                "ts": df.ts.dt.strftime("%Y-%m-%dT%H:%M:%S")
                        .astype(str).astype(object),
                "lon": df.lon.astype(float), "lat": df.lat.astype(float),
                "flagged": df.flagged, "seg": df.seg.astype(int)}
        for src, dst in EXTRA.items():
            if src in df.columns:
                cols[dst] = df[src]
        pts = gpd.GeoDataFrame(cols,
                               geometry=gpd.points_from_xy(df.lon, df.lat),
                               crs="EPSG:4326")
        print(f"points: {len(pts):,}, of which "
              f"{int(pts.flagged.sum()):,} flagged")
        write(pts, f"{a.source}_points", "fixes", shapefile=False)

    write(lines(df, ["device_id", "seg"], "tracks"),
          f"{a.source}_tracks", "tracks", shapefile=shp)

    df = df.assign(day=df.ts.dt.strftime("%Y-%m-%d"))
    write(lines(df, ["device_id", "day"], "day paths"),
          f"{a.source}_daypaths", "daypaths", shapefile=shp)


if __name__ == "__main__":
    main()
