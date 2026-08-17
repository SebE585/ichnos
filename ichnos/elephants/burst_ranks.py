"""
ICHNOS -- where inside the burst the anomaly sits.

This script exists because its first version did not. The table of section 4.1
of the paper had been computed in a throwaway shell, never committed, so never
replayable and never checkable. It was wrong, and it stayed wrong until an
outside reader noticed that its margins did not add up to a figure published
elsewhere.

The guard is at the bottom of this file: the total of flagged pairs must
reproduce exactly the count that fleet_health.json derives by an independent
path. If the two disagree, this script raises rather than writing.

Same criterion as fleet_health: an intra-burst pair 5 to 60 s apart implying
more than 8 m/s, after removing the outliers the curators marked by hand.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "out"
R = 6371008.8
CEIL_MPS = 8.0
BURST_GAP_S = 60.0
WAKE_PERIOD_S = 1200.0   # measured, not assumed: strict mode at 1200 s


def hav(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = (
        np.sin((p2 - p1) / 2) ** 2
        + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    )
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def pairs_of():
    """One row per consecutive pair, with its rank inside the burst."""
    ref = pd.read_csv(BASE / "data/etosha_reference.csv")
    batch_of = {
        str(r["animal-id"]): ("batch 2008" if int(str(r["tag-id"])[2:]) < 100 else "batch 2009")
        for _, r in ref.iterrows()
    }

    df = pd.read_parquet(OUT / "etosha_pivot.parquet")
    df = df[~df.x_movebank_manual_outlier.fillna(False).astype(bool)]
    df = df.sort_values(["device_id", "ts"])

    dev = np.asarray(df.device_id.astype(object))
    t = df.ts.values.astype("datetime64[s]").astype(np.int64)
    same = np.asarray(dev[1:] == dev[:-1], dtype=bool)
    dt = np.diff(t).astype(float)
    d = hav(df.lat.values[:-1], df.lon.values[:-1], df.lat.values[1:], df.lon.values[1:])

    intra = same & (dt >= 5) & (dt <= 60)
    bad = np.nan_to_num(np.where(intra, d / np.maximum(dt, 1), np.nan)) > CEIL_MPS

    # A burst ends when the animal changes or a gap exceeds 60 s.
    new_burst = (~same) | (dt > BURST_GAP_S)
    bid = np.concatenate([[0], np.cumsum(new_burst)])
    s = pd.Series(bid)
    rank = s.groupby(s).cumcount().values
    size = s.map(s.value_counts()).values

    global d_all, rank_all, size_all
    d_all, rank_all, size_all = d, rank, size
    p = pd.DataFrame({
        "device_id": dev[:-1],
        "batch": [batch_of.get(x, "?") for x in dev[:-1]],
        "start_rank": rank[:-1],          # 0 = first fix of the burst
        "from_end": size[:-1] - 1 - rank[:-1],
        "burst_size": size[:-1],
        "intra": intra,
        "flagged": bad,
    })
    return df, p[p.intra].copy(), bid, t


def main():
    df, p, bid, t_all = pairs_of()

    by_rank = p.groupby("start_rank").agg(pairs=("flagged", "size"),
                                            flagged=("flagged", "sum"))
    by_rank["share_pct"] = (100 * by_rank.flagged / by_rank.pairs).round(3)

    by_end = p.groupby("from_end").agg(pairs=("flagged", "size"),
                                          flagged=("flagged", "sum"))
    by_end["share_pct"] = (100 * by_end.flagged / by_end.pairs).round(3)

    first_pairs = p[p.start_rank == 0]
    # Four decimals: the 2009 batch is not strictly zero everywhere, and two
    # decimals would suggest it is. See the note at the top of this file.
    by_batch = (first_pairs.pivot_table(index="batch", columns="burst_size",
                                   values="flagged", aggfunc="mean") * 100).round(4)
    by_batch_counts = first_pairs.pivot_table(index="batch", columns="burst_size",
                                    values="flagged", aggfunc="sum")

    by_rank.reset_index().to_parquet(OUT / "burst_ranks.parquet", index=False)
    by_end.reset_index().to_parquet(OUT / "burst_ranks_from_end.parquet", index=False)
    by_batch.reset_index().to_parquet(OUT / "burst_ranks_by_batch.parquet", index=False)
    by_batch_counts.reset_index().to_parquet(OUT / "burst_ranks_by_batch_counts.parquet", index=False)

    # Rate by year, over FIRST PAIRS: that is where the defect sits, and the
    # convention has to be stated. The table published in v3 reproduces under
    # no convention at all; it came from the same throwaway shell as the rank
    # table.
    year = pd.DatetimeIndex(df.ts.values[:-1]).year
    first_ext = first_pairs.copy()
    first_ext["year"] = year[first_pairs.index]
    by_year = first_ext.groupby(["year", "batch"]).agg(pairs=("flagged", "size"),
                                             flagged=("flagged", "sum"))
    by_year["share_pct"] = (100 * by_year.flagged / by_year.pairs).round(4)
    by_year.reset_index().to_parquet(OUT / "burst_ranks_by_year.parquet", index=False)

    # Does the collar wait for convergence before emitting? Test proposed by a
    # reviewer to separate two readings of burst length. The wake schedule is a
    # strict 1200 s grid, so the delay of the first fix against its expected
    # time (previous burst start + 1200) measures acquisition effort directly.
    # Result: zero everywhere, quartiles included.
    pr = first_pairs.copy()
    pr["t"] = t_all[first_pairs.index]
    pr = pr.sort_values(["device_id", "t"])
    pr["expected"] = pr.groupby("device_id").t.shift(1) + WAKE_PERIOD_S
    pr["delay"] = pr.t - pr.expected
    pr = pr[pr.delay.between(-120, 300)]
    delays = pr.groupby(["batch", "burst_size"]).delay.agg(
        n="size", median="median",
        q25=lambda x: x.quantile(0.25), q75=lambda x: x.quantile(0.75))
    delays.reset_index().to_parquet(OUT / "first_fix_delay.parquet", index=False)

    # The obvious objection to all of the above is that these data are analysed
    # at 1 or 20/30 minute intervals with speed and distance outliers filtered,
    # so a defect confined to a ten-second burst reaches no one. It is testable,
    # and it is the most useful result of this section.
    #
    # 1. Which fix of the burst does a subsample keep? A resample().first()
    #    keeps the first, which is precisely the one carrying the defect.
    # 2. Does a speed filter see it? At 20 min spacing, a 241 m error implies
    #    0.20 m/s. No plausible threshold cuts that.
    # 3. Which fix of a flagged pair is the wrong one? Measured as the distance
    #    to the centroid of the other fixes of the same burst.
    jump = d_all[first_pairs.index[first_pairs.flagged]]
    filter_counts = {f"above_{v}_mps": int((jump / WAKE_PERIOD_S > v).sum()) for v in (1, 2, 4, 8)}

    # "size" would collide with the DataFrame attribute of the same name:
    # q.size silently returns the element count, not the column.
    q = pd.DataFrame({"bid": bid, "rank": rank_all, "burst_size": size_all,
                      "lat": df.lat.values, "lon": df.lon.values})
    bad_bursts = set(bid[first_pairs.index[first_pairs.flagged]])
    q = q[(q.burst_size == 4) & q.bid.isin(bad_bursts)]
    piv = q.pivot(index="bid", columns="rank", values=["lat", "lon"]).dropna()
    la, lo = piv["lat"], piv["lon"]
    dist_fix1 = hav(la[0], lo[0], la[[1, 2, 3]].mean(axis=1), lo[[1, 2, 3]].mean(axis=1))
    dist_fix2 = hav(la[1], lo[1], la[[2, 3]].mean(axis=1), lo[[2, 3]].mean(axis=1))

    subsampling = {
        "samples_if_one_per_burst": int(pd.Series(bid).nunique()),
        "of_which_contaminated": int(first_pairs.flagged.sum()),
        "contaminated_share_pct": round(100 * first_pairs.flagged.sum() / pd.Series(bid).nunique(), 2),
        "position_error_m": {
            "median": round(float(np.median(jump))),
            "p90": round(float(np.quantile(jump, 0.9))),
            "max": round(float(jump.max())),
        },
        "implied_speed_at_20min_mps": {
            "median": round(float(np.median(jump)) / WAKE_PERIOD_S, 3),
            "p90": round(float(np.quantile(jump, 0.9)) / WAKE_PERIOD_S, 3),
        },
        "caught_by_speed_filter_at_20min": filter_counts,
        "n_four_fix_bursts_tested": int(len(piv)),
        "fix1_distance_to_centroid_m": round(float(np.median(dist_fix1)), 1),
        "fix2_distance_to_centroid_m": round(float(np.median(dist_fix2)), 1),
        "fix1_is_outlier_pct": round(100 * float((dist_fix1 > dist_fix2).mean()), 1),
    }

    n_fixes = len(df)
    n_bursts = int(pd.Series(bid).nunique())
    n_flag = int(p.flagged.sum())
    n_first = int(first_pairs.flagged.sum())

    res = {
        "n_fixes": n_fixes,
        "n_bursts": n_bursts,
        "n_intra_burst_pairs": int(len(p)),
        "n_flagged": n_flag,
        "n_flagged_first_pair": n_first,
        "first_pair_share_pct": round(100 * n_first / n_flag, 2),
        "residue_after_targeted_remedy": n_flag - n_first,
        "blanket_remedy_fixes": n_bursts,
        "blanket_remedy_pct": round(100 * n_bursts / n_fixes, 1),
        "targeted_remedy_fixes": n_first,
        "targeted_remedy_pct": round(100 * n_first / n_fixes, 2),
        "sound_positions_lost_if_blanket": n_bursts - n_first,
        "subsampling": subsampling,
    }

    # Guard: the total must reproduce an independently computed one.
    expected = json.loads((OUT / "fleet_health.json").read_text())["n_flagged"]
    if n_flag != expected:
        raise AssertionError(
            f"inconsistent total: {n_flag} here against {expected} in "
            "fleet_health.json. One of the two paths changed its criterion; "
            "publish nothing before finding out which."
        )
    res["cross_check_fleet_health"] = "ok"

    # The list of fixes to discard, by name, so the dataset's curators can apply
    # or reject the remedy without replaying anything. It is the ARRIVING fix
    # of the flagged pair, that is, the first fix of the burst.
    offenders = first_pairs[first_pairs.flagged][["device_id"]].copy()
    idx = first_pairs.index[first_pairs.flagged]
    offenders["discarded_fix_ts"] = df.ts.values[idx + 1]
    offenders["rank_in_burst"] = 1
    offenders["reason"] = f"first fix of burst, implied speed > {CEIL_MPS} m/s"
    offenders.sort_values(["device_id", "discarded_fix_ts"]).to_csv(
        OUT / "etosha_flagged_fixes.csv", index=False
    )
    res["flagged_fixes_list"] = f"etosha_flagged_fixes.csv ({len(offenders):,} rows)"

    (OUT / "burst_ranks.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    print("\nby start rank:\n", by_rank.to_string())
    print("\nby position from the end of the burst:\n", by_end.to_string())
    print("\nfirst-pair rate, by batch and burst size:\n", by_batch.to_string())


if __name__ == "__main__":
    main()
