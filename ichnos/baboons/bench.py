"""
ICHNOS -- bench on e-obs collars (GPS at 1 Hz, full device telemetry).

The elephant case left a question open and asserted that answering it needed a
field campaign: when the track becomes agitated, is that the animal or the
receiver? This dataset settles it with no hardware at all, thanks to two
properties the elephant collars did not have.

  1. Doppler speed is **measured**, independently of position. So the moments
     when the animal is genuinely at rest can be selected without using
     position, and any residual dispersion attributed to the receiver. That is
     not circular.

  2. The device declares its own horizontal accuracy at every fix. That
     declaration is, as far as we know, never checked.

Four measurements.

  M5  Position noise measured at rest, per collar.
  M6  Does the self-declared accuracy keep its promise?
  M7  Fix acquisition time and battery as wear indicators.
  M8  Agreement between collars: two animals of the same troop.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "out"
R = 6371008.8
V_STILL = 0.10          # m/s, Doppler threshold for stillness
WINDOW = "60s"          # aggregation window for the noise


def xy(lat, lon, lat0, lon0):
    x = np.radians(lon - lon0) * R * np.cos(np.radians(lat0))
    y = np.radians(lat - lat0) * R
    return x, y


# --------------------------------------------------------------------- M5
def m5_bruit_a_l_arret(df):
    """Position dispersion over windows where Doppler says "not moving".

    The animal is not moving, so what moves is the receiver.
    """
    d = df[df.speed_mps < V_STILL].copy()
    if d.empty:
        return pd.DataFrame(), pd.DataFrame()
    d["fen"] = d.ts.dt.floor(WINDOW)

    lat0 = d.lat.median()
    lon0 = d.lon.median()
    d["x"], d["y"] = xy(d.lat.values, d.lon.values, lat0, lon0)

    g = d.groupby(["device_id", "fen"], observed=True)
    agg = g.agg(
        n=("x", "size"),
        sx=("x", "std"),
        sy=("y", "std"),
        acc=("h_accuracy_m", "median"),
        vmax=("speed_mps", "max"),
        ttff=("x_eobs_ttff_s", "median"),
    ).reset_index()
    # at least 20 fixes within the minute, and genuinely still
    agg = agg[(agg.n >= 20) & (agg.vmax < V_STILL)].dropna(subset=["sx", "sy"])
    agg["sigma_m"] = np.sqrt((agg.sx**2 + agg.sy**2) / 2)

    par_dev = (
        agg.groupby("device_id")
        .agg(
            n_fenetres=("sigma_m", "size"),
            sigma_median_m=("sigma_m", "median"),
            sigma_p90_m=("sigma_m", lambda s: s.quantile(0.90)),
            acc_declaree_median_m=("acc", "median"),
        )
        .reset_index()
    )
    par_dev["ratio_mesure_sur_declare"] = (
        par_dev.sigma_median_m / par_dev.acc_declaree_median_m
    ).round(2)
    return agg, par_dev.round(2)


# --------------------------------------------------------------------- M6
def m6_declaration_vs_realite(fenetres):
    """Does the self-declared accuracy predict the dispersion actually observed?"""
    d = fenetres.dropna(subset=["acc", "sigma_m"])
    if d.empty:
        return pd.DataFrame(), {}
    bins = [0, 3, 5, 8, 12, 20, 40, 1e9]
    lab = ["<3", "3-5", "5-8", "8-12", "12-20", "20-40", ">40"]
    d = d.assign(classe=pd.cut(d.acc, bins=bins, labels=lab))
    t = (
        d.groupby("classe", observed=True)
        .agg(
            n=("sigma_m", "size"),
            acc_declaree_m=("acc", "median"),
            sigma_mesure_m=("sigma_m", "median"),
            sigma_p90_m=("sigma_m", lambda s: s.quantile(0.90)),
        )
        .reset_index()
    )
    t["ratio"] = (t.sigma_mesure_m / t.acc_declaree_m).round(2)
    # rank correlation: does the declaration order them correctly?
    rho = d[["acc", "sigma_m"]].corr(method="spearman").iloc[0, 1]
    return t.round(2), {"spearman_declare_vs_mesure": round(float(rho), 3)}


# --------------------------------------------------------------------- M7
def m7_usure(df):
    """Battery sag under GNSS load: is the device ageing?

    A trap avoided: `eobs:used-time-to-get-fix` looks like an acquisition time
    and is not one. Its distribution is uniform from 14 to 43,188 s; it is a
    counter that ramps over a session of about 12 h and then resets. Its median
    is mechanically the middle of the ramp, identical on every collar. Useless
    as a wear indicator.

    The indicator that holds is the gap between the resting voltage and the
    voltage during the fix. That sag measures the cell's internal resistance,
    which rises with age. It is an end-of-life predictor readable without
    opening the collar.
    """
    d = df.dropna(subset=["x_eobs_battery_mv", "x_eobs_fix_battery_mv"]).copy()
    if d.empty:
        return pd.DataFrame(), pd.DataFrame()
    d["sag_mv"] = d.x_eobs_battery_mv - d.x_eobs_fix_battery_mv
    d["jour"] = d.ts.dt.floor("1D")

    par_jour = (
        d.groupby(["device_id", "jour"], observed=True)
        .agg(
            sag_median_mv=("sag_mv", "median"),
            sag_p90_mv=("sag_mv", lambda s: s.quantile(0.90)),
            batt_repos_mv=("x_eobs_battery_mv", "median"),
            batt_fix_mv=("x_eobs_fix_battery_mv", "median"),
            acc_m=("h_accuracy_m", "median"),
            n=("ts", "size"),
        )
        .reset_index()
    )

    pentes = []
    for dev, g in par_jour.groupby("device_id"):
        if len(g) < 7:
            continue
        t = (g.jour - g.jour.min()).dt.total_seconds() / 86400
        pentes.append(
            {
                "device_id": dev,
                "n_jours": len(g),
                "sag_median_mv": round(float(g.sag_median_mv.median()), 1),
                "sag_pente_mv_par_jour": round(float(np.polyfit(t, g.sag_median_mv, 1)[0]), 2),
                "batt_repos_median_mv": round(float(g.batt_repos_mv.median()), 1),
                "batt_pente_mv_par_jour": round(float(np.polyfit(t, g.batt_repos_mv, 1)[0]), 2),
            }
        )
    return par_jour, pd.DataFrame(pentes).sort_values("sag_median_mv", ascending=False)


# --------------------------------------------------------------------- M8
def m8_coherence_inter_collier(df, n_pairs=60):
    """Two collars of the same troop, at the same instant.

    When both animals are at rest simultaneously, the reported distance between
    them should be stable. Its variation from one second to the next is
    instrument noise on TWO receivers at once.
    """
    d = df[df.speed_mps < V_STILL][
        ["ts", "device_id", "lat", "lon", "h_accuracy_m"]
    ].copy()
    if d.empty:
        return pd.DataFrame()
    d["tsec"] = d.ts.dt.floor("1s")
    d = d.drop_duplicates(["device_id", "tsec"])

    lat0, lon0 = d.lat.median(), d.lon.median()
    d["x"], d["y"] = xy(d.lat.values, d.lon.values, lat0, lon0)

    devs = sorted(d.device_id.unique())
    rows = []
    for i in range(len(devs)):
        for j in range(i + 1, len(devs)):
            a = d[d.device_id == devs[i]].set_index("tsec")[["x", "y"]]
            b = d[d.device_id == devs[j]].set_index("tsec")[["x", "y"]]
            m = a.join(b, how="inner", lsuffix="_a", rsuffix="_b")
            if len(m) < 5000:
                continue
            rx = (m.x_a - m.x_b).values
            ry = (m.y_a - m.y_b).values
            dist = np.hypot(rx, ry)
            proches = dist < 100  # same subgroup
            if proches.sum() < 5000:
                continue
            # second difference: cancels position and relative speed
            drx = np.diff(rx[proches], n=2)
            dry = np.diff(ry[proches], n=2)
            # var(diff2 d'un bruit blanc) = 6 sigma^2 ; deux recepteurs => x2
            sigma_rel = np.sqrt((drx.var() + dry.var()) / 2 / 6)
            rows.append(
                {
                    "paire": f"{devs[i]}+{devs[j]}",
                    "n_secondes": int(proches.sum()),
                    "dist_mediane_m": round(float(np.median(dist[proches])), 1),
                    "sigma_relatif_m": round(float(sigma_rel), 2),
                    "sigma_par_collier_m": round(float(sigma_rel / np.sqrt(2)), 2),
                }
            )
            if len(rows) >= n_pairs:
                return pd.DataFrame(rows)
    return pd.DataFrame(rows)


# -------------------------------------------------------------------- main
def main():
    src = OUT / "baboons_gps_pivot.parquet"
    print(f"lecture {src.name} ...")
    cols = [
        "ts", "lat", "lon", "speed_mps", "h_accuracy_m", "device_id",
        "x_eobs_ttff_s", "x_eobs_fix_battery_mv", "x_eobs_battery_mv",
        "x_eobs_type_of_fix", "x_eobs_status",
    ]
    df = pd.read_parquet(src, columns=cols)
    print(f"  {len(df):,} fixes / {df.device_id.nunique()} porteurs")
    res = {
        "n_fixes": int(len(df)),
        "n_porteurs": int(df.device_id.nunique()),
        "periode": [str(df.ts.min()), str(df.ts.max())],
    }

    print("M5 noise at rest ...")
    fen, par_dev = m5_bruit_a_l_arret(df)
    fen.to_parquet(OUT / "noise_windows.parquet", index=False)
    par_dev.to_parquet(OUT / "noise_by_collar.parquet", index=False)
    res["M5"] = {
        "n_fenetres": int(len(fen)),
        "sigma_median_global_m": round(float(fen.sigma_m.median()), 2),
        "sigma_p90_global_m": round(float(fen.sigma_m.quantile(0.9)), 2),
        "par_collier": par_dev.to_dict("records"),
    }
    print(par_dev.to_string(index=False))

    print("M6 declaration against reality ...")
    t6, s6 = m6_declaration_vs_realite(fen)
    t6.to_parquet(OUT / "declared_accuracy.parquet", index=False)
    res["M6"] = {"table": t6.to_dict("records"), **s6}
    print(t6.to_string(index=False))
    print(" ", s6)

    # quality fields the device declares: are they informative?
    const = {}
    for c in ("x_eobs_type_of_fix", "x_eobs_status"):
        if c in df.columns:
            u = df[c].astype(str).nunique()
            const[c] = {"valeurs_distinctes": int(u),
                        "constant_sur_tout_le_jeu": bool(u == 1)}
    res["champs_qualite_declares"] = const
    print("  champs qualite declares :", const)

    print("M7 usure ...")
    par_jour, pentes = m7_usure(df)
    par_jour.to_parquet(OUT / "battery_by_day.parquet", index=False)
    pentes.to_parquet(OUT / "battery_slopes.parquet", index=False)
    res["M7"] = {"pentes": pentes.to_dict("records")}
    print(pentes.to_string(index=False))

    print("M8 agreement between collars ...")
    t8 = m8_coherence_inter_collier(df)
    t8.to_parquet(OUT / "collar_pairs.parquet", index=False)
    res["M8"] = {
        "n_pairs": int(len(t8)),
        "sigma_par_collier_median_m": (
            round(float(t8.sigma_par_collier_m.median()), 2) if len(t8) else None
        ),
        "pairs": t8.head(20).to_dict("records"),
    }
    print(t8.head(20).to_string(index=False))

    (OUT / "bench.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False, default=str)
    )
    print("\n-> out/bench.json")


if __name__ == "__main__":
    main()
