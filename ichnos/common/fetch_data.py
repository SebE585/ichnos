"""
ICHNOS -- download the case datasets from the Movebank Data Repository.

The repository exposes an open DSpace 7 API. Dryad sits behind a
proof-of-work anti-bot and cannot be scripted, which is why Movebank is the
single source here.
"""

from __future__ import annotations

import json
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://datarepository.movebank.org/server/api"
UA = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
DATA = Path(__file__).resolve().parents[2] / "data"

DATASETS = {
    "etosha": "f30fb6d4-803f-4b45-8313-716c3b21e087",
    "kruger": "b777279a-581d-43ce-b790-8e60304fb8b4",
}


def get(url):
    return json.load(
        urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120)
    )


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    for name, uuid in DATASETS.items():
        for b in get(f"{BASE}/core/items/{uuid}/bundles")["_embedded"]["bundles"]:
            if b["name"] != "ORIGINAL":
                continue
            for x in get(b["_links"]["bitstreams"]["href"])["_embedded"]["bitstreams"]:
                out = DATA / f"{name}_{x['name'].replace(' ', '_')}"
                if out.exists() and out.stat().st_size == x["sizeBytes"]:
                    continue
                print(f"  + {out.name} ({x['sizeBytes']/1e6:.0f} MB)", flush=True)
                urllib.request.urlretrieve(x["_links"]["content"]["href"], out)
                if out.suffix == ".zip":
                    with zipfile.ZipFile(out) as z:
                        z.extractall(DATA if "fence" not in out.name else DATA / "enp_fence")
        print(f"[{name}] done")


if __name__ == "__main__":
    main()
