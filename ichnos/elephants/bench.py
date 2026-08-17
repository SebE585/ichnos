"""
ICHNOS -- burst features and fence crossings on the elephant collars.

Formalises the central result of the diagnosis: the collar's burst, read as
ONE measurement rather than as four positions, carries three quantities that
nobody extracts.

The fence work reprojects to UTM 33S. Read as lat/lon, the park polygon gives
zero crossings, which looks like a result and is a projection error.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "out"
R = 6371008.8


# ------------------------------------------------------------------ geodesie
def haversine_m(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = (
        np.sin((p2 - p1) / 2) ** 2
        + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def wgs84_to_utm(lat, lon, zone_cm_deg=15.0, southern=True):
    """Forward Transverse Mercator, WGS84 to UTM. Zone 33S by default."""
    a, f = 6378137.0, 1 / 298.257223563
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    k0, FE = 0.9996, 500000.0
    FN = 10000000.0 if southern else 0.0

    p = np.radians(lat)
    dl = np.radians(lon - zone_cm_deg)
    N = a / np.sqrt(1 - e2 * np.sin(p) ** 2)
    T = np.tan(p) ** 2
    C = ep2 * np.cos(p) ** 2
    A = np.cos(p) * dl

    M = a * (
        (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * p
        - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * np.sin(2 * p)
        + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * np.sin(4 * p)
        - (35 * e2**3 / 3072) * np.sin(6 * p)
    )

    E = FE + k0 * N * (
        A
        + (1 - T + C) * A**3 / 6
        + (5 - 18 * T + T**2 + 72 * C - 58 * ep2) * A**5 / 120
    )
    Nn = FN + k0 * (
        M
        + N
        * np.tan(p)
        * (
            A**2 / 2
            + (5 - T + 9 * C + 4 * C**2) * A**4 / 24
            + (61 - 58 * T + T**2 + 600 * C - 330 * ep2) * A**6 / 720
        )
    )
    return E, Nn


def read_shp_polygons(path):
    b = Path(path).read_bytes()
    polys, off = [], 100
    while off < len(b):
        _, clen = struct.unpack(">ii", b[off : off + 8])
        rec = b[off + 8 : off + 8 + clen * 2]
        off += 8 + clen * 2
        if struct.unpack("<i", rec[0:4])[0] != 5:
            continue
        nparts, npts = struct.unpack("<ii", rec[36:44])
        parts = struct.unpack(f"<{nparts}i", rec[44 : 44 + 4 * nparts])
        pts = np.frombuffer(
            rec[44 + 4 * nparts : 44 + 4 * nparts + 16 * npts], dtype="<f8"
        ).reshape(-1, 2)
        for i, s in enumerate(parts):
            e = parts[i + 1] if i + 1 < nparts else npts
            polys.append(pts[s:e])
    return polys


def point_in_poly(x, y, poly):
    px, py = poly[:, 0], poly[:, 1]
    inside = np.zeros(len(x), dtype=bool)
    j = len(px) - 1
    for i in range(len(px)):
        inside ^= ((py[i] > y) != (py[j] > y)) & (
            x < (px[j] - px[i]) * (y - py[i]) / (py[j] - py[i] + 1e-15) + px[i]
        )
        j = i
    return inside


# ------------------------------------------------- the burst as one measurement
def burst_features(df, max_intra_gap_s=60):
    """The burst read as ONE measurement.

    Returns, per burst: instantaneous speed (slope of the fit), residual
    dispersion, and tortuosity (departure from the chord).
    """
    rows = []
    for dev, g in df.groupby("device_id", observed=True):
        g = g.sort_values("ts")
        t = g["ts"].values.astype("datetime64[s]").astype(np.int64)
        b = np.cumsum(np.diff(t, prepend=t[0]) > max_intra_gap_s)
        gg = pd.DataFrame({"b": b, "t": t, "lat": g.lat.values, "lon": g.lon.values})
        gg = gg[gg.groupby("b").t.transform("size") >= 4]
        if gg.empty:
            continue
        for bid, bg in gg.groupby("b"):
            tt = bg.t.values.astype(float)
            span = float(np.ptp(tt))
            if span < 5:
                continue
            tc = tt - tt.mean()
            lat0, lon0 = bg.lat.mean(), bg.lon.mean()
            x = np.radians(bg.lon.values - lon0) * R * np.cos(np.radians(lat0))
            y = np.radians(bg.lat.values - lat0) * R
            n = len(tc)
            A = np.column_stack([np.ones(n), tc])
            cx = np.linalg.lstsq(A, x, rcond=None)[0]
            cy = np.linalg.lstsq(A, y, rcond=None)[0]
            rx, ry = x - A @ cx, y - A @ cy
            # path actually walked within the burst, against the chord
            step = np.hypot(np.diff(x), np.diff(y))
            chord = np.hypot(x[-1] - x[0], y[-1] - y[0])
            rows.append(
                {
                    "device_id": dev,
                    "ts": pd.Timestamp(int(bg.t.iloc[0]), unit="s", tz="UTC"),
                    "n_fixes": n,
                    "span_s": span,
                    "v_mps": float(np.hypot(cx[1], cy[1])),
                    "resid_m": float(np.sqrt((rx @ rx + ry @ ry) / (2 * max(n - 2, 1)))),
                    "path_m": float(step.sum()),
                    "chord_m": float(chord),
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------- main
def main():
    df = pd.read_parquet(OUT / "etosha_pivot.parquet")
    # nullable column: NA means unmarked, not unknown
    outlier = df.x_movebank_manual_outlier.fillna(False).astype(bool)
    print(f"excluding the {int(outlier.sum())} hand-marked fixes")
    df = df[~outlier].copy()
    res = {}

    # ---- rafales
    print("rafales ...")
    bf = burst_features(df)
    bf.to_parquet(OUT / "bursts.parquet", index=False)
    rest = bf[bf.v_mps < 0.15]
    move = bf[bf.v_mps > 0.6]
    res["rafale_comme_mesure"] = {
        "n_bursts": int(len(bf)),
        "duree_mediane_s": float(bf.span_s.median()),
        "resid_median_repos_m": round(float(rest.resid_m.median()), 3),
        "resid_median_marche_m": round(float(move.resid_m.median()), 2),
        "pct_rafales_au_repos": round(100 * float((bf.v_mps < 0.15).mean()), 1),
        "v_mediane_en_marche_mps": round(float(move.v_mps.median()), 3),
        "tortuosite_mediane_path_sur_chord": round(
            float((move.path_m / move.chord_m.clip(lower=1e-3)).median()), 3
        ),
    }
    print("  ", json.dumps(res["rafale_comme_mesure"], ensure_ascii=False))

    # ---- where do the flags fall?
    print("M3 ...")
    d = df.sort_values(["device_id", "ts"])
    t = d.ts.values.astype("datetime64[s]").astype(np.int64)
    same_dev = d.device_id.values[1:] == d.device_id.values[:-1]
    dt = np.diff(t).astype(float)
    dist = haversine_m(
        d.lat.values[:-1], d.lon.values[:-1], d.lat.values[1:], d.lon.values[1:]
    )
    ok = same_dev & (dt > 0)
    v = np.where(ok, dist / np.maximum(dt, 1), np.nan)
    flag = np.nan_to_num(v) > 7.0
    fl = pd.DataFrame({"dt_s": dt, "dist_m": dist, "v": v, "flag": flag})[ok]
    res["M3_porte_vitesse"] = {
        "seuil_mps": 7.0,
        "n_flags": int(fl.flag.sum()),
        "pct": round(100 * float(fl.flag.mean()), 3),
        "repartition_par_gap": fl[fl.flag]
        .dt_s.pipe(
            pd.cut,
            bins=[0, 15, 60, 300, 1800, 3600, 1e9],
            labels=["<=15s", "15-60s", "1-5min", "5-30min", "30-60min", ">1h"],
        )
        .value_counts()
        .sort_index()
        .to_dict(),
        "saut_median_m_pour_gap_10s": round(
            float(fl[(fl.flag) & (fl.dt_s <= 15)].dist_m.median()), 1
        ),
        "lecture": (
            "a flag at a 10 s gap is a position jump, not an elephant at "
            "25 km/h: it measures the receiver's tail noise"
        ),
    }
    print("  ", json.dumps(res["M3_porte_vitesse"], ensure_ascii=False, default=str))

    # ---- M4 corrige : cloture en UTM 33S
    print("M4 ...")
    poly = max(read_shp_polygons(BASE / "data/enp_fence/enp fence poly.shp"), key=len)
    E, N = wgs84_to_utm(df.lat.values, df.lon.values)
    df["E"], df["N"] = E, N
    ins_all = point_in_poly(E, N, poly)
    print(f"   inside the park: {100*ins_all.mean():.1f}% of fixes")

    rows = []
    for iv in [None, 1200, 3600, 7200, 10800, 21600, 43200, 86400]:
        tot, ndev = 0, 0
        for dev, g in df.groupby("device_id", observed=True):
            g = g.sort_values("ts").set_index("ts")
            s = g if iv is None else g.resample(f"{iv}s").first().dropna(subset=["E"])
            if len(s) < 3:
                continue
            ndev += 1
            ins = point_in_poly(s.E.values, s.N.values, poly)
            tot += int(np.count_nonzero(np.diff(ins.astype(np.int8)) != 0))
        rows.append({"interval_s": iv or 0, "franchissements_vus": tot, "n_porteurs": ndev})
    f = pd.DataFrame(rows)
    f.to_parquet(OUT / "fence_crossings.parquet", index=False)
    base = int(f.loc[f.interval_s == 0, "franchissements_vus"].iloc[0])
    f["pct_vus"] = (100 * f.franchissements_vus / max(base, 1)).round(1)
    res["M4_cloture"] = {
        "pct_fixes_dans_le_parc": round(100 * float(ins_all.mean()), 1),
        "table": f.to_dict("records"),
    }
    print(f.to_string(index=False))

    (OUT / "bench_results.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False, default=str)
    )
    print("\n-> out/bench_results.json")


if __name__ == "__main__":
    main()
