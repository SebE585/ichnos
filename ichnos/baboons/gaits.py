"""
ICHNOS -- stride spectrum, at sufficient resolution.

The first attempt failed, and the reason is worth writing down. Each
acceleration record is 12 samples over 1 second. Treated in isolation it gives
a spectrum whose only available frequencies are 0, 1, 2, 3, 4, 5 and 6 Hz: a
resolution of 1 Hz. The dominant frequency therefore came out at 2.0 Hz at
every speed, which was not a measurement but a quantisation floor.

But the records are not isolated. The gaps between them are most often 1 s, so
they run end to end, and **94.5 % of the useful signal lies in continuous
stretches of 8 seconds or more**, the longest reaching 1,024 seconds. The
stream is therefore nearly continuous at 12 Hz, punctuated by holes.

Splicing the continuous stretches and analysing in 8 s windows takes the
resolution from 1 Hz to 0.125 Hz. That is what it takes to tell a cadence of
2.5 Hz from one of 3.5 Hz.

The prediction tested is external to the data: the Froude number
Fr = v**2 / (g L). Alexander and Jayes (1983) place the walk-run transition at
Fr = 0.5, that is 1.40 m/s for a hip height of 0.40 m.

The two quantities confronted come from sensors that do not talk to each
other: speed is a Doppler shift, cadence is an acceleration.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
DATA, OUT = BASE / "data", BASE / "out"
G = 9.80665
L_HANCHE_M = 0.40
FE = 12.0
NWIN = 96          # 8 s -> resolution 0.125 Hz
NOVER = 48
BINS_V = np.array([0, .25, .5, .75, 1., 1.25, 1.5, 1.75, 2., 2.5, 3., 3.5, 4., 5., 7.])


def charge_calibration():
    cal = pd.read_parquet(OUT / "acc_calibration.parquet")
    return {str(r.device_id): (np.array([r.offset_x, r.offset_y, r.offset_z]),
                               float(r.comptes_par_g)) for r in cal.itertuples()}


def main():
    cal = charge_calibration()

    gps = pd.read_parquet(OUT / "baboons_gps_pivot.parquet",
                          columns=["ts", "device_id", "speed_mps"])
    gps["device_id"] = gps.device_id.astype(str)
    # Do NOT use .astype("int64") // 10**9: in pandas 3 the unit may be the
    # microsecond, which collapses a thousand seconds into one. Convert
    # explicitly instead.
    gps["tsec"] = gps.ts.dt.floor("1s").values.astype("datetime64[s]").astype("int64")
    vit = {}
    for dev, g in gps.groupby("device_id", observed=True):
        s = g.drop_duplicates("tsec").set_index("tsec").speed_mps
        vit[dev] = s
    print(f"Doppler speeds indexed for {len(vit)} carriers")

    freqs = np.fft.rfftfreq(NWIN, d=1 / FE)
    somme = np.zeros((len(BINS_V) - 1, len(freqs)))
    compte = np.zeros(len(BINS_V) - 1, dtype=np.int64)
    fen = np.hanning(NWIN)
    n_fenetres = 0

    for f in sorted((DATA / "baboons_collective").glob("*-acc-*.csv.zip")):
        print(f"  {f.name}")
        z = zipfile.ZipFile(f)
        with z.open(z.namelist()[0]) as fh:
            df = pd.read_csv(
                fh, low_memory=False,
                usecols=["timestamp", "eobs:accelerations-raw",
                         "individual-local-identifier"],
            )
        df["dev"] = df["individual-local-identifier"].astype(str)
        df = df[df.dev.isin(cal)]
        if df.empty:
            continue
        df["tsec"] = (pd.to_datetime(df.timestamp, format="mixed", utc=True)
                      .values.astype("datetime64[s]").astype("int64"))
        df = df.sort_values(["dev", "tsec"]).drop_duplicates(["dev", "tsec"])

        for dev, g in df.groupby("dev", observed=True):
            off, kpg = cal[dev]
            t = g.tsec.to_numpy()
            # plages continues : ecart d'exactement 1 s
            coupe = np.flatnonzero(np.diff(t) != 1) + 1
            sv = vit.get(dev)
            for bloc_t, bloc_raw in zip(np.split(t, coupe),
                                        np.split(g["eobs:accelerations-raw"].to_numpy(), coupe)):
                if len(bloc_t) * 12 < NWIN:
                    continue
                # rebuild the continuous signal of the stretch
                ech = []
                for raw in bloc_raw:
                    if not isinstance(raw, str):
                        ech = []
                        break
                    v = np.fromstring(raw, sep=" ", dtype=np.float64)
                    if len(v) < 36:
                        ech = []
                        break
                    ech.append(v[:36].reshape(-1, 3))
                if not ech:
                    continue
                xyz = (np.vstack(ech) - off) / kpg
                a = np.linalg.norm(xyz, axis=1)
                if len(a) < NWIN:
                    continue
                # Doppler speed second by second over the stretch
                vs = sv.reindex(bloc_t).to_numpy() if sv is not None else None
                if vs is None:
                    continue
                for i in range(0, len(a) - NWIN + 1, NWIN - NOVER):
                    seg = a[i:i + NWIN]
                    sec0, sec1 = i // 12, (i + NWIN) // 12
                    vw = vs[sec0:sec1]
                    if np.isnan(vw).all():
                        continue
                    v = float(np.nanmean(vw))
                    if not np.isfinite(v) or v >= BINS_V[-1]:
                        continue
                    seg = seg - seg.mean()
                    if seg.std() < 1e-6:
                        continue
                    p = np.abs(np.fft.rfft(seg * fen)) ** 2
                    p /= p.sum()
                    b = int(np.digitize(v, BINS_V) - 1)
                    somme[b] += p
                    compte[b] += 1
                    n_fenetres += 1
            print(f"    {n_fenetres:,} windows of 8 s", end="\r", flush=True)
    print()

    spec = somme / np.maximum(compte, 1)[:, None]
    centres = (BINS_V[:-1] + BINS_V[1:]) / 2
    utile = (freqs >= 0.8) & (freqs <= 5.5)      # plausible stride band
    f_dom = np.where(compte > 300,
                     freqs[utile][spec[:, utile].argmax(axis=1)], np.nan)

    tab = pd.DataFrame({
        "v_min": BINS_V[:-1], "v_max": BINS_V[1:], "v_centre": centres,
        "n_fenetres": compte, "f_foulee_hz": f_dom,
        "froude": centres**2 / (G * L_HANCHE_M),
    })
    # longueur de foulee deduite : v / f
    tab["longueur_foulee_m"] = (tab.v_centre / tab.f_foulee_hz).round(3)
    tab.to_parquet(OUT / "gaits.parquet", index=False)
    np.save(OUT / "gait_spectra.npy", spec)
    np.save(OUT / "gait_freqs.npy", freqs)
    print(tab.round(3).to_string(index=False))

    v_tr = float(np.sqrt(0.5 * G * L_HANCHE_M))
    res = {
        "correction_v1": (
            "the first version analysed each 1 s record in isolation, giving a "
            "resolution of 1 Hz. The dominant frequency came out at 2.0 Hz "
            "everywhere: a quantisation floor, not a measurement."
        ),
        "n_fenetres_8s": int(n_fenetres),
        "resolution_hz": round(float(freqs[1] - freqs[0]), 4),
        "nyquist_hz": FE / 2,
        "L_hanche_m": L_HANCHE_M,
        "vitesse_transition_predite_mps": round(v_tr, 2),
        "table": tab.round(3).replace({np.nan: None}).to_dict("records"),
    }
    (OUT / "gaits.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    print(f"\nresolution {freqs[1]-freqs[0]:.3f} Hz; predicted transition {v_tr:.2f} m/s")


if __name__ == "__main__":
    main()
