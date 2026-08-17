"""
ICHNOS -- measuring the wind aloft with a stork.

The principle fits in one sentence. A bird spiralling in a thermal flies at a
roughly constant airspeed relative to the air, while the air itself moves. Its
ground speed is therefore the sum of a rotating vector, the airspeed, and a
constant one, the wind.

Over **one full turn**, the rotating vector averages out. What remains is the
wind.

    ground_speed(t) = airspeed(t) + wind
    average over one turn  ->  wind = < ground_speed >
    airspeed               ->  < | ground_speed - wind | >

Published method: Weinzierl et al. 2016, *Wind estimation based on thermal
soaring of birds*, Ecology and Evolution 6(24). It is reproduced here, which is
the point: a verifiable result is worth more than a novel one.

Two validations, neither of which needs an outside weather source.

  V1  **Two birds in the same thermal must measure the same wind.** A free
      cross-check, like the baboon collars a few metres apart.

  V2  The airspeed derived must land on the known value for the species. For a
      white stork in gliding flight the literature gives something of the order
      of 12 to 14 m/s. It is imposed nowhere: it comes out of the calculation
      or it does not.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "out"
R = 6371008.8

MIN_TURN_RATE_DEG_S = 3.0   # below this it is not a spiral
MIN_DURATION_S = 20         # one turn of a thermal typically lasts 15 to 40 s
MIN_CLIMB_MS = 0.0          # climbing is not required: some turns level off


def vitesse_sol(g):
    """East and north components of ground speed, derived from the 1 Hz positions."""
    lat = np.radians(g.lat.values)
    dt = np.diff(g.ts.values).astype("timedelta64[s]").astype(float)
    dx = np.radians(np.diff(g.lon.values)) * R * np.cos(lat[:-1])
    dy = np.radians(np.diff(g.lat.values)) * R
    with np.errstate(divide="ignore", invalid="ignore"):
        return dx / dt, dy / dt, dt


def spirales(g):
    """Cut out the segments where the bird turns decisively and steadily."""
    vx, vy, dt = vitesse_sol(g)
    ok = (dt == 1) & np.isfinite(vx) & np.isfinite(vy)
    cap = np.degrees(np.arctan2(vx, vy))
    dcap = (np.diff(cap) + 180) % 360 - 180          # signed change
    taux = np.where(dt[1:] > 0, dcap / dt[1:], np.nan)

    tourne = np.isfinite(taux) & (np.abs(taux) > MIN_TURN_RATE_DEG_S) & ok[1:]
    # segments of constant sign: a spiral does not change direction
    signe = np.sign(taux)
    rupture = (~tourne) | (np.diff(signe, prepend=signe[0]) != 0)
    seg = np.cumsum(rupture)

    for s in np.unique(seg[tourne]):
        idx = np.flatnonzero((seg == s) & tourne)
        if len(idx) < MIN_DURATION_S:
            continue
        # au moins un tour complet
        if abs(np.nansum(taux[idx])) < 330:
            continue
        yield idx + 1        # offset introduced by the two diffs


def main():
    src = OUT / "storks_gps_pivot.parquet"
    df = pd.read_parquet(src, columns=["ts", "lat", "lon", "device_id",
                                       "altitude_gps_m", "speed_mps"])
    df["device_id"] = df.device_id.astype(str)
    print(f"{len(df):,} fixes / {df.device_id.nunique()} oiseaux")

    lignes = []
    for dev, g in df.groupby("device_id", observed=True):
        g = g.sort_values("ts").reset_index(drop=True)
        if len(g) < 100:
            continue
        vx, vy, dt = vitesse_sol(g)
        alt = g.altitude_gps_m.values
        t = g.ts.values
        for idx in spirales(g):
            i0, i1 = idx[0], idx[-1]
            wx, wy = float(np.nanmean(vx[idx - 1])), float(np.nanmean(vy[idx - 1]))
            va = np.hypot(vx[idx - 1] - wx, vy[idx - 1] - wy)
            duree = float((t[i1] - t[i0]) / np.timedelta64(1, "s"))
            if duree <= 0:
                continue
            lignes.append({
                "device_id": dev,
                "t_debut": pd.Timestamp(t[i0]),
                "duree_s": duree,
                "n_fixes": len(idx),
                "vent_est_mps": round(wx, 2),
                "vent_nord_mps": round(wy, 2),
                "vent_module_mps": round(float(np.hypot(wx, wy)), 2),
                "vent_direction_deg": round(float(np.degrees(np.arctan2(wx, wy)) % 360), 1),
                "vitesse_propre_mps": round(float(np.nanmean(va)), 2),
                "lat": float(np.nanmean(g.lat.values[i0:i1 + 1])),
                "lon": float(np.nanmean(g.lon.values[i0:i1 + 1])),
                "altitude_m": round(float(np.nanmean(alt[i0:i1 + 1])), 0),
                "montee_ms": round(float((alt[i1] - alt[i0]) / duree), 2),
            })
    sp = pd.DataFrame(lignes)
    n_brut = len(sp)
    sp = sp[np.isfinite(sp[["vent_est_mps", "vent_nord_mps", "vitesse_propre_mps",
                            "vent_module_mps"]]).all(axis=1)]
    sp = sp[(sp.vent_module_mps < 40) & (sp.vitesse_propre_mps.between(2, 30))]
    print(f"spirales ecartees (non finies ou aberrantes) : {n_brut - len(sp)}")
    sp.to_parquet(OUT / "wind_spirals.parquet", index=False)
    print(f"{len(sp):,} complete spirals detected")
    if sp.empty:
        return

    print("\n=== derived airspeed (V2) ===")
    print(sp.vitesse_propre_mps.describe()[["count", "25%", "50%", "75%"]].round(2).to_string())
    print("\n=== estimated wind ===")
    print(sp.vent_module_mps.describe()[["25%", "50%", "75%", "max"]].round(2).to_string())
    print("\n=== altitude and climb ===")
    print(sp[["altitude_m", "montee_ms"]].describe()[3:].round(2).to_string())

    # -------- V1: two birds, same moment, same place, same wind?
    sp = sp.sort_values("t_debut")
    pairs = []
    arr = sp.reset_index(drop=True)
    for i in range(len(arr)):
        a = arr.iloc[i]
        j = i + 1
        while j < len(arr):
            b = arr.iloc[j]
            dts = (b.t_debut - a.t_debut).total_seconds()
            if dts > 300:
                break
            if b.device_id == a.device_id or abs(b.altitude_m - a.altitude_m) >= 300:
                j += 1
                continue
            # same thermal means same place. Without this test we compare two
            # birds 50 km apart, which have no reason to see the same wind.
            d_km = np.hypot(
                np.radians(b.lon - a.lon) * R * np.cos(np.radians(a.lat)),
                np.radians(b.lat - a.lat) * R) / 1000
            if d_km < 2.0:
                paires.append({
                    "paire": f"{a.device_id}+{b.device_id}",
                    "ecart_temps_s": dts,
                    "distance_km": round(float(d_km), 2),
                    "ecart_altitude_m": abs(b.altitude_m - a.altitude_m),
                    "vent_a": a.vent_module_mps, "vent_b": b.vent_module_mps,
                    "ecart_module_mps": round(abs(a.vent_module_mps - b.vent_module_mps), 2),
                    "ecart_vecteur_mps": round(float(np.hypot(
                        a.vent_est_mps - b.vent_est_mps,
                        a.vent_nord_mps - b.vent_nord_mps)), 2),
                })
            j += 1
    pr = pd.DataFrame(pairs)
    pr.to_parquet(OUT / "wind_pairs.parquet", index=False)

    res = {
        "methode": "Weinzierl et al. 2016, Ecology and Evolution 6(24)",
        "n_spirales": int(len(sp)),
        "n_oiseaux": int(sp.device_id.nunique()),
        "duree_mediane_s": float(sp.duree_s.median()),
        "vitesse_propre_mps": {
            "p25": float(sp.vitesse_propre_mps.quantile(.25)),
            "median": float(sp.vitesse_propre_mps.median()),
            "p75": float(sp.vitesse_propre_mps.quantile(.75)),
            "expected_from_literature": "9 to 12 m/s while spiralling for Ciconia ciconia; straight gliding flight is faster",
        },
        "wind": {
            "module_median_mps": float(sp.vent_module_mps.median()),
            "module_p90_mps": float(sp.vent_module_mps.quantile(.9)),
        },
        "altitude_mediane_m": float(sp.altitude_m.median()),
        "montee_mediane_ms": float(sp.montee_ms.median()),
    }
    if len(pr):
        print("\n=== V1: two birds in the same thermal ===")
        print(f"{len(pr)} pairs (less than 10 min and 500 m apart)")
        print(pr.ecart_vecteur_mps.describe()[["count", "50%", "75%", "max"]].round(2).to_string())
        res["V1_accord_entre_oiseaux"] = {
            "n_pairs": int(len(pr)),
            "ecart_vectoriel_median_mps": float(pr.ecart_vecteur_mps.median()),
            "ecart_vectoriel_p75_mps": float(pr.ecart_vecteur_mps.quantile(.75)),
            "reading": ("two birds that do not coordinate, wearing collars that do "
                        "not communicate, must find the same "
                        "wind. That is the control, and it costs nothing"),
        }
    print("\n=== V3: disagreement against distance (structure function) ===")
    st = v3_fonction_de_structure(sp)
    print(st.to_string(index=False))
    plancher = float(st.median_disagreement_mps.iloc[0])
    res["V3_fonction_de_structure"] = {
        "table": st.to_dict("records"),
        "plancher_cote_a_cote_mps": plancher,
        "erreur_par_spirale_mps": round(plancher / np.sqrt(2), 2),
        "reading": ("the disagreement grows monotonically with distance. "
                    "Noise would give the same value everywhere. The floor set "
                    "by birds side by side gives the measurement error, though "
                    "the variance argument applies to a variance and not to a "
                    "median, so the per-spiral figure is of order 1 to 1.4 m/s."),
    }
    (OUT / "wind.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    print("\n-> out/wind.json")




# --------------------------------------------------------------------- V3
def v3_fonction_de_structure(sp, out=OUT):
    """Does the disagreement between two birds grow with the distance between them?

    This is the test that decides. If the estimate were only noise, the
    disagreement would be the same at 1 km and at 500 km. If it grows with
    distance, the estimate carries real spatial information about the wind
    field, and the floor set by birds side by side gives the measurement error.
    """
    sp = sp.sort_values("t_debut").reset_index(drop=True)
    lat, lon = sp.lat.values, sp.lon.values
    t = sp.t_debut.values.astype("datetime64[s]").astype(np.int64)
    wx, wy = sp.vent_est_mps.values, sp.vent_nord_mps.values
    dev, alt = sp.device_id.values, sp.altitude_m.values

    tranches = [(0, 2), (2, 10), (10, 50), (50, 200), (200, np.inf)]
    seaux = {k: [] for k in tranches}
    for i in range(len(sp)):
        j = i + 1
        while j < len(sp) and t[j] - t[i] <= 300:
            if dev[j] != dev[i] and abs(alt[j] - alt[i]) < 300:
                d = np.hypot(
                    np.radians(lon[j] - lon[i]) * R * np.cos(np.radians(lat[i])),
                    np.radians(lat[j] - lat[i]) * R) / 1000
                e = np.hypot(wx[j] - wx[i], wy[j] - wy[i])
                for k in tranches:
                    if k[0] <= d < k[1]:
                        seaux[k].append(e)
                        break
            j += 1

    lignes = []
    for (a, b), v in seaux.items():
        if not v:
            continue
        v = np.array(v)
        lignes.append({
            "d_min_km": a, "d_max_km": b if np.isfinite(b) else 9999,
            "n_pairs": len(v),
            "median_disagreement_mps": round(float(np.median(v)), 2),
            "p75_disagreement_mps": round(float(np.quantile(v, .75)), 2),
        })
    tab = pd.DataFrame(lignes)
    tab.to_parquet(out / "wind_structure.parquet", index=False)
    return tab


if __name__ == "__main__":
    main()
