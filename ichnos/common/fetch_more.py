"""Download the further datasets identified by the repository inventory."""
import json, sys, urllib.request
from pathlib import Path

BASE = "https://datarepository.movebank.org/server/api"
UA = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
DATA = Path(__file__).resolve().parents[2] / "data"

DATASETS = {
    "baboons_collective": "82dd820c-de69-49b7-a792-c418c73153bf",
    "laikipia_kenya": "5f9fad19-3079-47c7-9b2d-151fd3d79d3b",
    # White storks, autumn 2014 migration: GPS plus acceleration.
    # Used by case 3, wind aloft estimated from thermal soaring.
    "cigognes_vent": "6cc937ff-be4a-4ba9-99c1-7364d928b2d9",
}


def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=120))


def main():
    for name, uuid in DATASETS.items():
        dst = DATA / name
        dst.mkdir(parents=True, exist_ok=True)
        for b in get(f"{BASE}/core/items/{uuid}/bundles")["_embedded"]["bundles"]:
            if b["name"] != "ORIGINAL":
                continue
            for x in get(b["_links"]["bitstreams"]["href"])["_embedded"]["bitstreams"]:
                out = dst / x["name"].replace(" ", "_")
                if out.exists() and out.stat().st_size == x["sizeBytes"]:
                    print(f"  = {out.name}")
                    continue
                print(f"  + {out.name} ({x['sizeBytes']/1e6:.0f} MB)", flush=True)
                urllib.request.urlretrieve(x["_links"]["content"]["href"], out)
        print(f"[{name}] done", flush=True)


# Sans cette garde, un simple `import` telechargeait 900 Mo. Un module qui agit
# a l'import est une bombe pour quiconque explore le depot, et c'est ce que
# faisait celui-ci.
if __name__ == "__main__":
    main()
