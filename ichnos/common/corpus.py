"""
ICHNOS -- the generic bench, run over the whole Movebank corpus.

The elephant criterion (an 8 m/s ceiling) does not transpose: the corpus runs
from a passerine to a whale. What is needed is a detector that knows neither
the species nor its order of magnitude.

**The out-and-back detector.** An isolated bad fix forces the track to leave
and come straight back. Over three consecutive positions A, B, C:

    excursion = (AB + BC - AC) / 2

A real displacement gives an excursion that is small against the usual step. A
position spike gives an enormous one. The quantity is **scale-free** and
**species-free**: it is compared to the individual's own habitual step,
measured by a robust quantile.

A vulture and a seal are each judged against their own yardstick, with no
species datasheet involved anywhere.

The rest of the bench is already generic: actual cadence against nominal
cadence, the structure of the gaps, repeated positions.
"""

from __future__ import annotations

import io
import json
import traceback
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
DATA, OUT = BASE / "data" / "corpus", BASE / "out"
API = "https://datarepository.movebank.org/server/api"
UA = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
R = 6371008.8

K_EXCURSION = 10.0        # multiple of the usual step past which it is a spike
IGNORE = ("readme", "reference-data", "license", "deployment")


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=120
            ) as r:
                return json.load(r)
        except Exception:
            if i == tries - 1:
                return None
    return None


# ---------------------------------------------------------------- fetching
def fichiers_de(uuid):
    d = get(f"{API}/core/items/{uuid}/bundles")
    if not d:
        return []
    out = []
    for b in d.get("_embedded", {}).get("bundles", []):
        if b.get("name") != "ORIGINAL":
            continue
        bs = get(b["_links"]["bitstreams"]["href"])
        if not bs:
            continue
        for x in bs.get("_embedded", {}).get("bitstreams", []):
            nom = x.get("name", "")
            if any(k in nom.lower() for k in IGNORE):
                continue
            if not nom.lower().endswith((".csv", ".csv.zip", ".zip")):
                continue
            out.append((nom, x["_links"]["content"]["href"], int(x.get("sizeBytes") or 0)))
    return out


def telecharge(uuid, titre):
    dst = DATA / uuid[:8]
    dst.mkdir(parents=True, exist_ok=True)
    got = []
    for nom, url, taille in fichiers_de(uuid):
        f = dst / nom.replace(" ", "_")
        if not (f.exists() and f.stat().st_size == taille):
            try:
                urllib.request.urlretrieve(url, f)
            except Exception:
                continue
        got.append(f)
    return got


# --------------------------------------------------------------- lecture
COLS = {
    "timestamp": "ts",
    "location-lat": "lat",
    "location-long": "lon",
    "individual-local-identifier": "dev",
}


class SansPosition(Exception):
    """The file carries no position column at all."""


def lit(f: Path) -> pd.DataFrame | None:
    """Read a Movebank export, csv or zip, keeping only the useful columns."""
    try:
        if f.suffix == ".zip":
            z = zipfile.ZipFile(f)
            noms = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not noms:
                return None
            fh = z.open(noms[0])
        else:
            fh = open(f, "rb")
        tete = pd.read_csv(io.BytesIO(fh.read(65536)), nrows=0, on_bad_lines="skip")
        if "location-lat" not in tete.columns or "location-long" not in tete.columns:
            # light-level geolocator, accelerometer only, or an attached analysis
            # file: no position, so out of scope rather than unreadable
            raise SansPosition
        manquantes = [c for c in COLS if c not in tete.columns]
        if manquantes:
            return None
        usecols = list(COLS)
        if "sensor-type" in tete.columns:
            usecols.append("sensor-type")
        if "argos:lc" in tete.columns:
            usecols.append("argos:lc")

        fh = (zipfile.ZipFile(f).open(noms[0]) if f.suffix == ".zip" else open(f, "rb"))
        df = pd.read_csv(fh, usecols=usecols, low_memory=False, on_bad_lines="skip")
    except SansPosition:
        raise
    except Exception:
        return None
    capteur = "inconnu"
    if "sensor-type" in df.columns:
        vc = df["sensor-type"].astype(str).str.lower().value_counts()
        if len(vc):
            capteur = vc.index[0]
    lc = None
    if "argos:lc" in df.columns:
        lc = df["argos:lc"].astype(str).value_counts(normalize=True).head(6).round(3).to_dict()
    df = df.rename(columns=COLS)[["ts", "lat", "lon", "dev"]].dropna()
    if len(df) < 200:
        return None
    df["ts"] = pd.to_datetime(df.ts, format="mixed", utc=True, errors="coerce")
    df = df.dropna(subset=["ts"]).sort_values(["dev", "ts"])
    df.attrs["capteur"] = capteur
    df.attrs["argos_lc"] = lc
    return df


# ----------------------------------------------------------------- mesures
def hav(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = (np.sin((p2 - p1) / 2) ** 2
         + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2)
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def mesure(df: pd.DataFrame) -> dict:
    n_pic = n_trip = n_pas = 0
    reps = 0
    gaps = []
    for dev, g in df.groupby("dev", observed=True):
        if len(g) < 50:
            continue
        lat, lon = g.lat.to_numpy(), g.lon.to_numpy()
        t = g.ts.values.astype("datetime64[s]").astype(np.int64)
        dt = np.diff(t)
        gaps.append(dt[dt > 0])

        pas = hav(lat[:-1], lon[:-1], lat[1:], lon[1:])
        n_pas += len(pas)
        reps += int(np.count_nonzero(pas == 0))
        if len(pas) < 20:
            continue
        # the individual's own yardstick, robust to outliers
        echelle = float(np.quantile(pas, 0.95))
        if echelle <= 0:
            continue
        ab, bc = pas[:-1], pas[1:]
        ac = hav(lat[:-2], lon[:-2], lat[2:], lon[2:])
        exc = (ab + bc - ac) / 2
        n_trip += len(exc)
        n_pic += int(np.count_nonzero(exc > K_EXCURSION * echelle))

    # Coordinate grain: separates a truncation at export from a copied fix.
    # Four decimals make a grid of about 11 m; a highly repetitive dataset on
    # fine coordinates has an entirely different problem.
    lat_all = df.lat.to_numpy()
    dl = np.abs(np.diff(lat_all))
    dl = dl[dl > 0]
    pas_min_m = float(np.min(dl) * 111320) if len(dl) else np.nan
    dec = int(pd.Series(df.lat.astype(str)).str.split(".").str[-1].str.len().median())

    if not gaps or n_trip == 0:
        return {}
    gap = np.concatenate(gaps)
    # Do NOT round to the nearest ten: that flattens any cadence below 10 s
    # (a 1 Hz stream came out with a mode of 0). Mode of the integer gaps.
    mode = float(pd.Series(gap).mode().iloc[0]) if len(gap) else np.nan
    return {
        "n_fixes": int(len(df)),
        "n_individus": int(df.dev.nunique()),
        "jours": round(float((df.ts.max() - df.ts.min()).total_seconds() / 86400), 1),
        "cadence_mediane_s": float(np.median(gap)),
        "cadence_mode_s": mode,
        "gap_p95_s": float(np.quantile(gap, 0.95)),
        "regularite_pct": round(100 * float(np.mean(np.abs(gap - mode) <= max(0.1 * mode, 1))), 1),
        "pct_positions_repetees": round(100 * reps / max(n_pas, 1), 3),
        "pct_pics": round(100 * n_pic / max(n_trip, 1), 3),
        "n_triplets": int(n_trip),
        "decimales_lat": dec,
        "pas_min_m": round(pas_min_m, 3) if pas_min_m == pas_min_m else None,
    }


# -------------------------------------------------------------------- main
def traite(ligne):
    uuid, titre, taxon = ligne
    try:
        fs = telecharge(uuid, titre)
        best, sans_pos, capteur, lc = {}, 0, None, None
        for f in fs:
            try:
                df = lit(f)
            except SansPosition:
                sans_pos += 1
                continue
            if df is None:
                continue
            capteur = df.attrs.get("capteur") or capteur
            lc = df.attrs.get("argos_lc") or lc
            m = mesure(df)
            if m and m.get("n_fixes", 0) > best.get("n_fixes", 0):
                best = m
        if not best:
            statut = "no position" if sans_pos and not fs[len(fs):] else "illisible"
            if sans_pos:
                statut = "no position"
            return {"uuid": uuid, "titre": titre, "taxon": taxon, "statut": statut}
        return {"uuid": uuid, "titre": titre, "taxon": taxon, "statut": "ok",
                "capteur": capteur, "argos_lc": json.dumps(lc) if lc else None, **best}
    except Exception as e:
        return {"uuid": uuid, "titre": titre, "taxon": taxon,
                "statut": "erreur", "detail": str(e)[:120]}


def main(max_mo=50.0, workers=8):
    DATA.mkdir(parents=True, exist_ok=True)
    inv = pd.read_parquet(OUT / "movebank_inventory.parquet")
    inv = inv[(inv.octets > 0) & (inv.Mo < max_mo)]
    print(f"{len(inv)} jeux sous {max_mo:.0f} Mo, {inv.octets.sum()/1e9:.1f} Go")

    lignes = list(zip(inv.uuid, inv.titre.fillna(""), inv.taxon.fillna("")))
    res = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, r in enumerate(ex.map(traite, lignes), 1):
            res.append(r)
            if i % 10 == 0:
                ok = sum(1 for x in res if x["statut"] == "ok")
                print(f"    {i}/{len(lignes)} processed, {ok} usable", flush=True)

    df = pd.DataFrame(res)
    df.to_parquet(OUT / "corpus_quality.parquet", index=False)
    ok = df[df.statut == "ok"]
    print(f"\n{len(ok)} usable datasets out of {len(df)}")
    print(f"total {int(ok.n_fixes.sum()):,} fixes / {int(ok.n_individus.sum())} individus")
    print("\n=== taux de pics de position ===")
    print(ok.pct_pics.describe()[["25%", "50%", "75%", "max"]].round(3).to_string())
    print("\n=== 15 most affected datasets ===")
    print(ok.nlargest(15, "pct_pics")[["pct_pics", "n_fixes", "cadence_mediane_s", "titre"]]
          .assign(titre=lambda x: x.titre.str.slice(0, 60)).to_string(index=False))


if __name__ == "__main__":
    import sys
    main(max_mo=float(sys.argv[1]) if len(sys.argv) > 1 else 50.0)
