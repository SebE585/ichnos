"""
ICHNOS -- GIS export of the Etosha deposit: points and line trajectories.

The bench publishes a list of keys, not positions. This script joins that list
back onto the deposit the user downloaded themselves and writes two layers a
GIS can open: the fixes as points, and the trajectories as lines.

Three things it does that a one-liner does not, each of which changes what the
map shows:

  - It drops the five rows the curators marked `visible = false`. They are in
    the CSV, Movebank hides them in its own interface, and two of them sit
    1418 km and 38 km outside the park. As points they are specks; as a line
    they are the whole map.
  - It splits a trajectory wherever the collar stops reporting for longer than
    GAP_H. A single line per collar draws a straight segment across a
    three-month silence, and that segment is not a movement.
  - It keeps the timestamp as an ISO text field, because the shapefile
    attribute table has no date-time type and truncates names to ten
    characters. The time of day is what a vegetation index compositing needs.

The `flagged` attribute marks the fixes the bench identifies as first-of-burst,
median error 241 m. On the line layer, `pct_flag` is the share of the segment
built from such fixes.

Run it from the repository root with the deposit CSV in data/. Writes
out/etosha_points.gpkg, out/etosha_tracks.gpkg, and the same two layers as
shapefiles under out/shp/ for software that needs them.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# The bench itself runs on pandas and numpy alone. This export is the one place
# that writes GIS files, so geopandas is optional and asked for here rather
# than at the top of requirements.txt.
try:
    import geopandas as gpd
    from shapely.geometry import LineString
except ImportError:  # pragma: no cover
    raise SystemExit("this script needs geopandas: pip install geopandas")

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "out"
DATA = BASE / "data"

FIXES = DATA / ("African elephants in Etosha National Park "
                "(data from Tsalyuk et al. 2018).csv")
FLAGGED = OUT / "etosha_flagged_fixes.csv"

# Nominal spacing in this deposit is one burst every twenty minutes. Six hours
# is eighteen missed bursts: past that, a straight line between two fixes says
# more about the gap than about the animal. Raise it to draw fewer, longer
# lines; lower it to be stricter about what counts as a continuous track.
GAP_H = 6.0

# Points go to GeoPackage only by default. The same layer as a shapefile is a
# 630 MB attribute table for 2.9 million fixes, against a 2 GB format limit,
# and the timestamp comes back as text either way. The line layers are small
# and are written in both formats.
POINTS_SHP = False

# One line per collar and per calendar day as well. Day paths are the layer
# that answers "where does this animal go in a day"; the segment layer answers
# "where has the collar been, continuously".
DAILY = True


def load() -> pd.DataFrame:
    fx = pd.read_csv(
        FIXES,
        usecols=["event-id", "timestamp", "location-long", "location-lat",
                 "visible", "individual-local-identifier"],
        parse_dates=["timestamp"],
        low_memory=False,
    ).rename(columns={"location-long": "lon", "location-lat": "lat",
                      "individual-local-identifier": "collar"})

    n_hidden = int((fx.visible == False).sum())  # noqa: E712
    fx = fx[fx.visible == True]  # noqa: E712
    fx = fx.dropna(subset=["lon", "lat"]).copy()
    print(f"{n_hidden} rows marked visible=false, dropped")

    fg = pd.read_csv(FLAGGED, parse_dates=["discarded_fix_ts"])
    flagged = set(zip(fg.device_id, fg.discarded_fix_ts))
    fx["flagged"] = [(c, t) in flagged
                     for c, t in zip(fx.collar, fx.timestamp)]

    # 1.14 million rows share their timestamp with another fix of the same
    # collar: the deposit stores whole seconds and a burst can put two fixes
    # inside one. They are distinct positions, a metre or two apart, and NOT
    # duplicates to be dropped. They do make a sort on timestamp alone
    # non-deterministic, so event-id breaks the tie and the vertex order of a
    # line is reproducible.
    return (fx.sort_values(["collar", "timestamp", "event-id"])
              .reset_index(drop=True))


def segments(fx: pd.DataFrame) -> pd.DataFrame:
    dt = fx.groupby("collar").timestamp.diff().dt.total_seconds() / 3600.0
    new = (dt.isna()) | (dt > GAP_H)
    fx = fx.assign(seg=new.cumsum())
    return fx


def lines(fx: pd.DataFrame, key: list[str], name: str) -> gpd.GeoDataFrame:
    rows = []
    for k, g in fx.groupby(key, sort=True):
        if len(g) < 2:
            continue
        k = k if isinstance(k, tuple) else (k,)
        rows.append({
            "collar": str(g.collar.iloc[0]),
            "seg": str(k[-1]),
            "start": g.timestamp.iloc[0].strftime("%Y-%m-%dT%H:%M:%S"),
            "end": g.timestamp.iloc[-1].strftime("%Y-%m-%dT%H:%M:%S"),
            "n_fix": len(g),
            "dur_h": round((g.timestamp.iloc[-1] - g.timestamp.iloc[0])
                           .total_seconds() / 3600.0, 2),
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
        if c != "geometry" and gdf[c].dtype.kind in "OU" or \
                str(gdf[c].dtype) == "string":
            gdf[c] = gdf[c].astype(object)

    gdf.to_file(OUT / f"{stem}.gpkg", layer=layer, driver="GPKG")
    if shapefile:
        shp = OUT / "shp"
        shp.mkdir(parents=True, exist_ok=True)
        gdf.to_file(shp / f"{stem}.shp", driver="ESRI Shapefile")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    fx = segments(load())

    pts = gpd.GeoDataFrame(
        {
            "collar": fx.collar.astype(str).astype(object),
            "ts": fx.timestamp.dt.strftime("%Y-%m-%dT%H:%M:%S")
                    .astype(str).astype(object),
            "lon": fx.lon.astype(float),
            "lat": fx.lat.astype(float),
            "flagged": fx.flagged,
            "seg": fx.seg.astype(int),
        },
        geometry=gpd.points_from_xy(fx.lon, fx.lat),
        crs="EPSG:4326",
    )
    print(f"points: {len(pts)}, of which {int(pts.flagged.sum())} flagged")
    write(pts, "etosha_points", "fixes", shapefile=POINTS_SHP)

    write(lines(fx, ["collar", "seg"], "tracks"), "etosha_tracks", "tracks")

    if DAILY:
        fx = fx.assign(day=fx.timestamp.dt.strftime("%Y-%m-%d"))
        write(lines(fx, ["collar", "day"], "day paths"),
              "etosha_daypaths", "daypaths")


if __name__ == "__main__":
    main()
