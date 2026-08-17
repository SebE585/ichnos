"""
ICHNOS -- inventory of the Movebank Data Repository.

Enumerates the 2008 items of the repository, collects the size of the
published files and the useful metadata (taxon, sensors, period), and ranks
candidates for the bench: large volume, recent, and where possible a fine
cadence or an on-board accelerometer.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

BASE = "https://datarepository.movebank.org/server/api"
UA = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
OUT = Path(__file__).resolve().parents[2] / "out"


def get(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(
                urllib.request.Request(url, headers=UA), timeout=60
            ) as r:
                return json.load(r)
        except Exception:
            if i == tries - 1:
                return None
    return None


def list_items():
    """Page through every item of the repository."""
    items, page = [], 0
    while True:
        d = get(f"{BASE}/discover/search/objects?dsoType=item&size=100&page={page}")
        if not d:
            break
        objs = d["_embedded"]["searchResult"]["_embedded"]["objects"]
        if not objs:
            break
        for o in objs:
            im = o["_embedded"]["indexableObject"]
            md = im.get("metadata", {})

            def one(k):
                v = md.get(k)
                return v[0]["value"] if v else None

            def many(k):
                return " | ".join(x["value"] for x in md.get(k, []))

            items.append(
                {
                    "uuid": im.get("uuid"),
                    "titre": one("dc.title"),
                    "date": one("dc.date.issued"),
                    "taxon": many("dwc:scientificName") or many("dc.subject"),
                    "description": (one("dc.description.abstract") or "")[:400],
                }
            )
        page += 1
        tp = d["_embedded"]["searchResult"]["page"]["totalPages"]
        print(f"  page {page}/{tp}", end="\r")
        if page >= tp:
            break
    print()
    return items


def sizes(uuid):
    """Total published bytes in the ORIGINAL bundle, and the file list."""
    d = get(f"{BASE}/core/items/{uuid}/bundles")
    if not d:
        return 0, ""
    total, names = 0, []
    for b in d.get("_embedded", {}).get("bundles", []):
        if b.get("name") != "ORIGINAL":
            continue
        bs = get(b["_links"]["bitstreams"]["href"])
        if not bs:
            continue
        for x in bs.get("_embedded", {}).get("bitstreams", []):
            total += int(x.get("sizeBytes") or 0)
            names.append(x.get("name", ""))
    return total, " | ".join(names[:6])


def main():
    print("enumerating items ...")
    items = list_items()
    print(f"  {len(items)} items")

    print("fetching sizes (12 concurrent) ...")
    with ThreadPoolExecutor(max_workers=12) as ex:
        res = list(ex.map(sizes, [i["uuid"] for i in items]))
    for it, (n, f) in zip(items, res):
        it["bytes_published"], it["fichiers"] = n, f

    df = pd.DataFrame(items)
    df["Mo"] = (df.bytes_published / 1e6).round(1)
    df["annee"] = pd.to_numeric(df.date.astype(str).str[:4], errors="coerce")
    df = df.sort_values("bytes_published", ascending=False)
    df.to_parquet(OUT / "movebank_inventory.parquet", index=False)

    print(f"\ntotal published: {df.bytes_published.sum()/1e9:.1f} GB over {len(df)} items")
    print(f"items with files: {(df.bytes_published > 0).sum()}")
    print("\n=== 25 plus gros ===")
    print(
        df.head(25)[["Mo", "annee", "titre"]]
        .assign(titre=lambda x: x.titre.str.slice(0, 78))
        .to_string(index=False)
    )
    print("\n=== 15 plus gros depuis 2020 ===")
    r = df[df.annee >= 2020].head(15)
    print(
        r[["Mo", "annee", "titre"]]
        .assign(titre=lambda x: x.titre.str.slice(0, 78))
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
