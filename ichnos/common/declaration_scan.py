"""
ICHNOS -- does the deposit declare what the bench measures?

The paper stated that none of the measured properties is declared. That
sentence was written from the item abstracts alone, which the inventory keeps
truncated at 400 characters: no README had ever been read. It was an assertion,
not a measurement, and it is the first sentence a repository maintainer will
test.

This script measures it. For every dataset the bench processed end to end it
pulls the full DSpace metadata record and the README bitstream published beside
the data, then searches for any wording that would tell a reader about repeated
positions, reduced coordinate precision or removed position spikes.

The control is the same search on the datasets that do NOT carry the property.
Without it a rate of mentions says nothing: it cannot distinguish a text that
tracks the data from a template that mentions everything everywhere.

High recall on purpose. A hit is not a declaration, it is a passage to read.
Writes out/declaration_scan.parquet and out/declaration_scan.json.
"""

from __future__ import annotations

import json
import math
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "out"
CACHE = BASE / "data" / "metadata"
API = "https://datarepository.movebank.org/server/api"
UA = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

# Same thresholds as the corpus table of the paper. Written out here rather
# than imported: if one of them moves, the two files must disagree loudly.
SEUIL_REPETITION = 5.0
SEUIL_PICS = 0.05
SEUIL_DECIMALES = 4

FAMILLES = {
    "repetition": re.compile(
        r"\b(duplicat\w*|repeated|repeating|repeats|stale|identical (?:position|location|fix|coordinate)\w*"
        r"|same (?:position|location|fix) (?:was |is )?(?:repeated|reported)|redundant)\b", re.I),
    "troncature": re.compile(
        r"\b(decimal\w*|round(?:ed|ing)|truncat\w*|coarsen\w*|generali[sz]\w*|obfuscat\w*|jitter\w*"
        r"|fuzz\w*|degrad\w*|reduced precision|lower(?:ed)? precision|mask(?:ed|ing)|randomi[sz]\w*"
        r"|rarefi\w*|aggregated to)\b", re.I),
    "pics": re.compile(
        r"\b(outlier\w*|spike\w*|erroneous|implausible|impossible|invalid (?:fix|location|position)"
        r"|screen(?:ed|ing)|filter(?:ed|ing)|removed (?:location|fix|position)\w*|speed filter)\b", re.I),
}


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=60
            ) as r:
                return r.read()
        except Exception:
            if i == tries - 1:
                return None
    return None


def get_json(url):
    b = get(url)
    return json.loads(b) if b else None


def texte_metadonnees(uuid: str) -> str:
    """Every metadata value of the item, concatenated. Not truncated."""
    d = get_json(f"{API}/core/items/{uuid}")
    if not d:
        return ""
    bouts = []
    for cle, vals in (d.get("metadata") or {}).items():
        for v in vals:
            val = v.get("value")
            if val:
                bouts.append(f"[{cle}] {val}")
    return "\n".join(bouts)


def texte_readme(uuid: str) -> tuple[str, int]:
    """The README-like bitstreams published in the ORIGINAL bundle."""
    d = get_json(f"{API}/core/items/{uuid}/bundles")
    if not d:
        return "", 0
    bouts, octets = [], 0
    for b in d.get("_embedded", {}).get("bundles", []):
        if b.get("name") != "ORIGINAL":
            continue
        bs = get_json(b["_links"]["bitstreams"]["href"])
        if not bs:
            continue
        for x in bs.get("_embedded", {}).get("bitstreams", []):
            nom = (x.get("name") or "").lower()
            taille = int(x.get("sizeBytes") or 0)
            # Documentation only. A data file is not a declaration, and the
            # reference-data table describes animals, not the file itself.
            if not (nom.endswith((".txt", ".md", ".rtf")) or "readme" in nom):
                continue
            if "reference-data" in nom or taille > 4_000_000:
                continue
            url = x["_links"]["content"]["href"]
            brut = get(url)
            if not brut:
                continue
            octets += taille
            bouts.append(brut.decode("utf-8", errors="replace"))
    return "\n".join(bouts), octets


# ------------------------------------------- the text that is about the data
# A Movebank README is two things. Text specific to the dataset, before the
# first horizontal rule, then an attribute dictionary that is the same from one
# deposit to the next. The dictionary carries "units: decimal degrees" and
# "manually marked outlier" in every single deposit, so searching it measures
# the repository template rather than the data. Only the abstract, the preamble
# and the "THIS DATASET:" notes say anything about THIS dataset, and they are
# the only places a declaration can live.
NOTE = re.compile(r"THIS DATASET:(.{0,600})", re.I | re.S)


def texte_specifique(txt: str) -> str:
    """Abstract, README preamble and per-attribute dataset notes."""
    meta, _, readme = txt.partition("===README===\n")
    resume = "\n".join(l for l in meta.splitlines()
                       if l.startswith(("[dc.description", "[dc.title]", "[dc.subject]")))
    preambule = re.split(r"\n-{5,}", readme)[0] if readme else ""
    notes = "\n".join(m.group(1) for m in NOTE.finditer(readme))
    return "\n".join((resume, preambule, notes))


def extraits(txt: str, rx: re.Pattern, n=3) -> str:
    """The passages themselves, not just a count. A hit has to be readable."""
    vus = []
    for m in rx.finditer(txt):
        a, b = max(0, m.start() - 90), min(len(txt), m.end() + 90)
        vus.append(" ".join(txt[a:b].split()))
        if len(vus) >= n:
            break
    return " || ".join(vus)


def traite(ligne):
    uuid, titre = ligne.uuid, ligne.titre
    f = CACHE / f"{uuid}.txt"
    if f.exists():
        txt = f.read_text(encoding="utf-8", errors="replace")
    else:
        meta = texte_metadonnees(uuid)
        readme, _ = texte_readme(uuid)
        txt = meta + "\n\n===README===\n" + readme
        f.write_text(txt, encoding="utf-8")
    propre = texte_specifique(txt)
    r = {
        "uuid": uuid,
        "titre": titre,
        "n_car": len(txt),
        "n_car_propre": len(propre),
        "readme": "===README===\n" in txt and bool(txt.split("===README===\n")[-1].strip()),
        "note_this_dataset": "THIS DATASET" in txt,
        # what the bench measured on this dataset
        "a_repetition": bool(ligne.pct_positions_repetees > SEUIL_REPETITION),
        "a_troncature": bool(ligne.decimales_lat <= SEUIL_DECIMALES),
        "a_pics": bool(ligne.pct_pics > SEUIL_PICS),
    }
    for fam, rx in FAMILLES.items():
        ex = extraits(propre, rx)
        r[f"dit_{fam}"] = bool(ex)
        r[f"ex_{fam}"] = ex
        # For the record, the same search over the whole README, template
        # included. It is what the naive version of this scan would report.
        r[f"gabarit_{fam}"] = bool(rx.search(txt))
    return r


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson interval. The normal approximation returns zero width on a zero
    proportion, that is, it fails exactly where this scan needs it."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    centre = p + z * z / (2 * n)
    demi = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((centre - demi) / den, (centre + demi) / den)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    q = pd.read_parquet(OUT / "corpus_quality.parquet")
    lignes = list(q.itertuples())
    with ThreadPoolExecutor(max_workers=8) as ex:
        res = list(ex.map(traite, lignes))
    d = pd.DataFrame(res)
    d["a_une_propriete"] = d.a_repetition | d.a_troncature | d.a_pics
    d.to_parquet(OUT / "declaration_scan.parquet", index=False)

    resume = {
        "n_jeux": int(len(d)),
        "n_readme": int(d.readme.sum()),
        "n_avec_propriete": int(d.a_une_propriete.sum()),
    }
    for fam, col in (("repetition", "a_repetition"), ("troncature", "a_troncature"), ("pics", "a_pics")):
        sub = d[d[col]]
        temoin = d[~d[col]]
        k1, n1 = int(sub[f"dit_{fam}"].sum()), len(sub)
        k0, n0 = int(temoin[f"dit_{fam}"].sum()), len(temoin)
        lo1, hi1 = wilson(k1, n1)
        lo0, hi0 = wilson(k0, n0)
        resume[fam] = {
            "n_mesures": int(len(sub)),
            # The control: datasets that do NOT carry the property. Without
            # it, a rate of mentions does not say whether text tracks data.
            "taux_cas_pct": round(100 * k1 / n1, 1),
            "ic95_cas_pct": [round(100 * lo1, 1), round(100 * hi1, 1)],
            "taux_temoin_pct": round(100 * k0 / n0, 1),
            "ic95_temoin_pct": [round(100 * lo0, 1), round(100 * hi0, 1)],
            "n_temoin": n0,
            "n_dont_le_texte_propre_en_parle": int(sub[f"dit_{fam}"].sum()),
            "n_dont_le_readme_entier_en_parle": int(sub[f"gabarit_{fam}"].sum()),
            "n_readme": int(sub.readme.sum()),
            "n_note_this_dataset": int(sub.note_this_dataset.sum()),
        }
    (OUT / "declaration_scan.json").write_text(json.dumps(resume, indent=2))
    print(json.dumps(resume, indent=2))


if __name__ == "__main__":
    main()
