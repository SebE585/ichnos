"""
ICHNOS -- calibrating the accelerometer under the gravity constraint.

e-obs collars deliver **raw uncalibrated ADC counts**. No datasheet gives the
offset or the gain, and they differ from one unit to the next. It is the same
problem as on an off-the-shelf telematics device, and it is solved the same
way: no test bench, no disassembly, using the one reference available
everywhere and at all times, gravity.

The principle. When the animal is still, the accelerometer measures gravity
alone. The mean raw vector therefore has a constant norm, whatever the
posture. Across postures, the cloud of raw vectors describes a **sphere**: its
centre is the offset of the three axes, its radius the number of counts per g.

The sphere fit is a linear least squares:

    x**2 + y**2 + z**2 = 2ax + 2by + 2cz + d
    centre = (a, b, c)      radius = sqrt(d + a**2 + b**2 + c**2)

The residual of the fit says what the calibration is worth, and the spread
between units says whether pooling them is allowed at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "out"
G = 9.80665


def ajuste_sphere(x, y, z):
    """Linear least squares. Returns (centre, radius, relative residual)."""
    A = np.column_stack([2 * x, 2 * y, 2 * z, np.ones(len(x))])
    b = x**2 + y**2 + z**2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    a, bb, c, d = sol
    r = np.sqrt(max(d + a**2 + bb**2 + c**2, 1e-9))
    # distance of each point to the fitted sphere
    rho = np.sqrt((x - a) ** 2 + (y - bb) ** 2 + (z - c) ** 2)
    return (a, bb, c), r, float(np.std(rho) / r)


def main():
    acc = pd.read_parquet(OUT / "baboons_acc_pivot.parquet")
    print(f"{len(acc):,} rafales / {acc.device_id.nunique()} porteurs")
    print(f"declared rate: {acc.hz.dropna().unique()[:5]} Hz, "
          f"{acc.n_ech.median():.0f} samples per burst (median)")

    # at rest means low agitation on all three axes. The threshold is taken
    # from the distribution itself, not chosen a priori.
    agit = acc[["ax_raw_std", "ay_raw_std", "az_raw_std"]].max(axis=1)
    threshold = float(agit.quantile(0.25))
    repos = acc[agit <= threshold]
    print(f"stillness threshold: {threshold:.1f} counts (first quartile of agitation)")
    print(f"rafales au repos   : {len(repos):,} ({100*len(repos)/len(acc):.0f} %)")

    lignes = []
    for dev, g in repos.groupby("device_id", observed=True):
        if len(g) < 500:
            continue
        c, r, res = ajuste_sphere(
            g.ax_raw_mean.values, g.ay_raw_mean.values, g.az_raw_mean.values
        )
        lignes.append(
            {
                "device_id": dev,
                "n_rafales_repos": int(len(g)),
                "offset_x": round(c[0], 1),
                "offset_y": round(c[1], 1),
                "offset_z": round(c[2], 1),
                "comptes_par_g": round(r, 1),
                "residu_relatif_pct": round(100 * res, 2),
                "sensibilite_mg_par_compte": round(1000 / r, 2),
            }
        )
    cal = pd.DataFrame(lignes).sort_values("comptes_par_g")
    cal.to_parquet(OUT / "acc_calibration.parquet", index=False)
    print("\n=== calibration per unit ===")
    print(cal.to_string(index=False))

    ec = cal.comptes_par_g
    of = cal[["offset_x", "offset_y", "offset_z"]]
    res = {
        "n_bursts": int(len(acc)),
        "n_rafales_repos": int(len(repos)),
        "hz_declare": float(acc.hz.dropna().median()),
        "n_echantillons_median": float(acc.n_ech.median()),
        "n_colliers_calibres": int(len(cal)),
        "comptes_par_g": {
            "min": float(ec.min()), "median": float(ec.median()), "max": float(ec.max()),
            "dispersion_pct": round(float(100 * (ec.max() - ec.min()) / ec.median()), 1),
        },
        "offsets": {
            "etendue_x": round(float(of.offset_x.max() - of.offset_x.min()), 1),
            "etendue_y": round(float(of.offset_y.max() - of.offset_y.min()), 1),
            "etendue_z": round(float(of.offset_z.max() - of.offset_z.min()), 1),
        },
        "residu_relatif_median_pct": round(float(cal.residu_relatif_pct.median()), 2),
        "lecture": (
            "The gain spread between units is the error made by applying one "
            "calibration to the whole fleet. The range of offsets is the error "
            "made by assuming the offset sits at mid-scale."
        ),
    }

    # what a single fleet-wide calibration would cost
    med = float(ec.median())
    res["cout_calibration_unique"] = {
        "erreur_gain_max_pct": round(float(100 * (ec - med).abs().max() / med), 1),
        "erreur_gain_max_mg": round(
            float(1000 * (ec - med).abs().max() / med), 1
        ),
    }
    (OUT / "acc_calibration.json").write_text(
        json.dumps(res, indent=2, ensure_ascii=False)
    )
    print("\n" + json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
