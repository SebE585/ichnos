"""
ICHNOS -- conformance of the Movebank corpus to the open pivot format.

The corpus bench reads files with its own pandas reader. It therefore proves
nothing about the format: "this pivot is the right receptacle" stays an
assertion there.

This survey puts the same datasets through the **official** adapter of the
published version, then through its validator. It is the failures that write
the specification notebook, not our intuitions.

The mapping is built by introspection: a Movebank export does not always carry
the same columns, and that is precisely the point. A source that emits no
Doppler speed must not have one invented for it.
"""

from __future__ import annotations

import json
import tempfile
import warnings
import zipfile
from pathlib import Path

import pandas as pd

import telemachus as tele
from telemachus.adapters import csv_mapping
from telemachus.adapters.csv_mapping import MappingError


def instrument() -> dict:
    """Where the measuring library comes from, not only which version.

    This survey checks that datasets declare the provenance of their columns.
    It did not declare its own instrument's, which is the same defect: without
    an explicit PYTHONPATH, the import resolves to site-packages, that is, to
    the PUBLISHED WHEEL. An already merged fix appears absent there, and the
    result is plausible and stable rather than erratic, so invisible.

    The version does not settle it: the published wheel and the main branch
    both announce the same string until the next version is tagged. Only the
    path separates them.
    """
    racine = Path(tele.__file__).resolve().parent.parent
    marques = {}
    try:
        from telemachus.core.schemas import CONDITIONAL_CORE
        marques["conditional_core"] = sorted(CONDITIONAL_CORE)
    except ImportError:
        marques["conditional_core"] = None      # predates the fix
    return {
        "version": tele.__version__,
        "spec": getattr(tele, "__spec_version__", None),
        "chemin": str(racine),
        "depuis_site_packages": "site-packages" in str(racine),
        "marques": marques,
    }

BASE = Path(__file__).resolve().parents[2]
DATA, OUT = BASE / "data" / "corpus", BASE / "out"

# colonne Movebank -> (colonne Telemachus, unite)
CANON = {
    "timestamp": ("ts", "iso8601"),
    "location-lat": ("lat", "deg"),
    "location-long": ("lon", "deg"),
    "ground-speed": ("speed_mps", "m/s"),
    "heading": ("heading_deg", "deg"),
    # a unit is mandatory on any column that carries one: the first version
    # omitted this one and 122 datasets were refused because of the mapping,
    # not because of the format
    "height-above-ellipsoid": ("altitude_gps_m", "m"),
    "height-above-msl": ("altitude_gps_m", "m"),
    "gps:hdop": ("hdop", None),
    "gps:satellite-count": ("n_satellites", None),
    "eobs:horizontal-accuracy-estimate": ("h_accuracy_m", "m"),
    "individual-local-identifier": ("device_id", None),
}


def mapping_pour(colonnes) -> dict | None:
    """Build the mapping from the columns actually present."""
    cols, vus = {}, set()
    for src, (dst, unit) in CANON.items():
        if src not in colonnes or dst in vus:
            continue
        cols[dst] = {"column": src} | ({"unit": unit} if unit else {})
        vus.add(dst)
    if not {"ts", "lat", "lon"} <= vus:
        return None
    return {"dataset_id": "movebank", "read": {"sep": ","}, "columns": cols}


def csv_utilisables(dossier: Path, tmp: Path):
    """Return the readable CSV paths, unpacking zips where needed."""
    for f in sorted(dossier.glob("*")):
        if f.suffix == ".csv":
            yield f
        elif f.suffix == ".zip":
            try:
                z = zipfile.ZipFile(f)
            except Exception:
                continue
            for n in z.namelist():
                if not n.lower().endswith(".csv"):
                    continue
                try:
                    z.extract(n, tmp)
                except Exception:
                    # archive truncated on download: the CRC does not check out.
                    # That is a datum of the survey, not a crash.
                    yield ("archive corrompue", f.name)
                    return
                yield tmp / n
                return


def traite(dossier: Path) -> dict:
    res = {"uuid8": dossier.name}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for f in csv_utilisables(dossier, tmp):
            if isinstance(f, tuple):
                res.update(statut=f[0], detail=f[1][:100])
                continue
            try:
                tete = pd.read_csv(f, nrows=0)
            except Exception as e:
                res.update(statut="csv illisible", detail=str(e)[:100])
                continue
            m = mapping_pour(tete.columns)
            if m is None:
                res.update(statut="hors perimetre",
                           detail="neither ts nor lat nor lon among the columns")
                continue
            res["colonnes_mappees"] = sorted(m["columns"])
            res["a_speed_mps"] = "speed_mps" in m["columns"]
            res["a_device_id"] = "device_id" in m["columns"]
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    df = csv_mapping.load(f, mapping=m)
            except MappingError as e:
                return res | {"statut": "mapping refuse", "detail": str(e)[:160]}
            except Exception as e:
                return res | {"statut": "conversion echouee",
                              "detail": f"{type(e).__name__}: {e}"[:160]}
            try:
                r = tele.validate(df, level="full")
            except Exception as e:
                return res | {"statut": "validation plantee",
                              "detail": f"{type(e).__name__}: {e}"[:160]}
            return res | {
                "statut": "conforme" if r.ok else "non conforme",
                "n_lignes": int(len(df)),
                "profil": getattr(r, "profile", None),
                "n_erreurs": len(getattr(r, "errors", []) or []),
                "n_avertissements": len(getattr(r, "warnings", []) or []),
                "erreurs": " | ".join(str(x)[:110] for x in (getattr(r, "errors", []) or [])[:3]),
                "avertissements": " | ".join(str(x)[:110] for x in (getattr(r, "warnings", []) or [])[:3]),
            }
    return res | {"statut": res.get("statut", "aucun csv exploitable")}


def main():
    inst = instrument()
    print("INSTRUMENT DE MESURE")
    for k, v in inst.items():
        print(f"  {k:22s} {v}")
    if inst["depuis_site_packages"]:
        print("  !! measured with the PUBLISHED WHEEL, not a working copy")
    print()
    dossiers = sorted(d for d in DATA.iterdir() if d.is_dir())
    print(f"{len(dossiers)} jeux telecharges")
    lignes = []
    for i, d in enumerate(dossiers, 1):
        try:
            lignes.append(traite(d))
        except Exception as e:
            lignes.append({"uuid8": d.name, "statut": "plantage",
                           "detail": f"{type(e).__name__}: {e}"[:140]})
        if i % 25 == 0:
            c = sum(1 for x in lignes if x.get("statut") == "conforme")
            print(f"    {i}/{len(dossiers)} — {c} conformes", flush=True)

    df = pd.DataFrame(lignes)
    # the instrument travels with the measurement, or the measurement means nothing
    for k, v in inst.items():
        df[f"instrument_{k}"] = json.dumps(v) if isinstance(v, dict) else v
    df.to_parquet(OUT / "conformance.parquet", index=False)
    (OUT / "conformite_instrument.json").write_text(
        json.dumps(inst, indent=2, ensure_ascii=False))

    print("\n=== statuts ===")
    print(df.statut.value_counts().to_string())
    conf = df[df.statut.isin(["conforme", "non conforme"])]
    if len(conf):
        print(f"\nconvertis : {len(conf)} | lignes totales {int(conf.n_lignes.sum()):,}".replace(",", " "))
        print("profils :", conf.profil.value_counts().to_dict())
        print(f"with speed_mps: {int(conf.a_speed_mps.sum())} / {len(conf)}")
        print(f"with device_id: {int(conf.a_device_id.sum())} / {len(conf)}")
        print("\n=== most frequent warnings ===")
        w = conf[conf.n_avertissements > 0].avertissements.str.split(" | ", regex=False).explode()
        print(w.str.slice(0, 80).value_counts().head(10).to_string())
    ech = df[~df.statut.isin(["conforme", "non conforme"])]
    if len(ech):
        print("\n=== causes d'echec ===")
        print(ech.groupby("statut").detail.apply(
            lambda s: s.str.slice(0, 90).value_counts().head(3).to_dict()).to_string())


if __name__ == "__main__":
    main()
