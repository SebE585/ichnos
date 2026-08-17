"""
ICHNOS -- e-obs collars (via Movebank) to the open pivot format.

e-obs collars are of a different class from the position-only collars of the
elephant case: they emit a full telemetry record, not just a position. Two
consequences follow, and both matter.

  - the `core` profile is **genuinely** satisfied, because `ground-speed` is a
    measured Doppler speed and not one derived from two positions;
  - the device exposes its own health: battery voltage, voltage at the moment
    of the fix, temperature, fix type, and above all the time it took to get
    the fix (`used-time-to-get-fix`), which is the classic ageing indicator of
    a GNSS receiver.

The accelerometer arrives on a separate stream, as bursts of interleaved XYZ
at 12 Hz. The pivot format handles multi-rate natively: nothing is merged, two
tables are published.

e-obs accelerations are **raw uncalibrated ADC counts**. So `ax_mps2` is NOT
filled with an invented conversion: the raw values are kept, and calibration
is done separately under the gravity constraint (`baboons/acc_calibrate.py`).
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from . import validate

CHUNK = 500_000

# colonnes e-obs -> colonnes Telemachus SPEC-01
GPS_MAP = {
    "timestamp": "ts",
    "location-lat": "lat",
    "location-long": "lon",
    "ground-speed": "speed_mps",              # Doppler, not derived
    "heading": "heading_deg",
    "height-above-ellipsoid": "altitude_gps_m",
    "eobs:horizontal-accuracy-estimate": "h_accuracy_m",
    "individual-local-identifier": "device_id",
}

# device telemetry, outside the spec: convention x_<source>_<field>
GPS_EXTRA = {
    "eobs:battery-voltage": "x_eobs_battery_mv",
    "eobs:fix-battery-voltage": "x_eobs_fix_battery_mv",
    "eobs:temperature": "x_eobs_temperature_c",
    "eobs:used-time-to-get-fix": "x_eobs_ttff_s",
    "eobs:type-of-fix": "x_eobs_type_of_fix",
    "eobs:status": "x_eobs_status",
    "eobs:speed-accuracy-estimate": "x_eobs_speed_accuracy_mps",
    "tag-local-identifier": "x_eobs_tag_id",
}


def _open_csv(path: Path):
    """Open a .csv, or the first member of a .zip, without unpacking to disk."""
    if path.suffix == ".zip":
        z = zipfile.ZipFile(path)
        return z.open(z.namelist()[0])
    return open(path, "rb")


def gps_to_pivot(paths, out_parquet: Path, source: str) -> dict:
    """Project the e-obs GPS files onto the pivot format, streamed in chunks."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    writer, n_rows = None, 0
    devices, tmin, tmax = set(), None, None

    for p in paths:
        with _open_csv(Path(p)) as fh:
            for chunk in pd.read_csv(fh, chunksize=CHUNK, low_memory=False):
                out = pd.DataFrame()
                out["ts"] = pd.to_datetime(
                    chunk["timestamp"], format="mixed", utc=True
                )
                out["lat"] = chunk["location-lat"].astype("float64")
                out["lon"] = chunk["location-long"].astype("float64")
                out["speed_mps"] = chunk["ground-speed"].astype("float32")
                out["heading_deg"] = chunk["heading"].astype("float32")
                out["altitude_gps_m"] = chunk["height-above-ellipsoid"].astype("float32")
                out["h_accuracy_m"] = chunk[
                    "eobs:horizontal-accuracy-estimate"
                ].astype("float32")
                out["device_id"] = chunk["individual-local-identifier"].astype(str)

                for src, dst in GPS_EXTRA.items():
                    if src in chunk.columns:
                        v = chunk[src]
                        out[dst] = (
                            pd.to_numeric(v, errors="coerce").astype("float32")
                            if dst.endswith(("_mv", "_c", "_s", "_mps"))
                            else v.astype(str)
                        )
                out["x_ichnos_source"] = source

                out = out.dropna(subset=["lat", "lon"])
                devices.update(out.device_id.unique().tolist())
                if len(out):
                    tmin = min(tmin, out.ts.min()) if tmin is not None else out.ts.min()
                    tmax = max(tmax, out.ts.max()) if tmax is not None else out.ts.max()

                tbl = pa.Table.from_pandas(out, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(out_parquet, tbl.schema, compression="zstd")
                writer.write_table(tbl)
                n_rows += len(out)
                print(f"    {n_rows:,} lignes", end="\r", flush=True)
    if writer:
        writer.close()
    print()

    # Writing is streamed, so validation happens afterwards, carrier by carrier
    # so that 19 M rows need not be held at once. It raises: a parquet that is
    # written but not conformant must not pass for conformant.
    cr = validate.verify_parquet(out_parquet, source)

    return {
        "source": source,
        "n_records": n_rows,
        "n_porteurs": len(devices),
        "periode": [str(tmin), str(tmax)],
        "conformance_verified": cr,
    }


def acc_bursts(paths, out_parquet: Path, source: str, max_bursts=None) -> dict:
    """Expand the acceleration bursts into one row per burst.

    Each burst is a string of interleaved ADC integers, X Y Z X Y Z... The raw
    vector is kept per axis, not an invented conversion.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    writer, n = None, 0
    for p in paths:
        with _open_csv(Path(p)) as fh:
            for chunk in pd.read_csv(fh, chunksize=50_000, low_memory=False):
                rows = []
                for _, r in chunk.iterrows():
                    raw = r.get("eobs:accelerations-raw")
                    if not isinstance(raw, str):
                        continue
                    v = np.fromstring(raw, sep=" ", dtype=np.float32)
                    k = (len(v) // 3) * 3
                    if k < 9:
                        continue
                    xyz = v[:k].reshape(-1, 3)
                    rows.append(
                        {
                            "ts": r["timestamp"],
                            "device_id": str(r["individual-local-identifier"]),
                            "n_ech": len(xyz),
                            "hz": float(
                                r.get("eobs:acceleration-sampling-frequency-per-axis", np.nan)
                            ),
                            "ax_raw_mean": float(xyz[:, 0].mean()),
                            "ay_raw_mean": float(xyz[:, 1].mean()),
                            "az_raw_mean": float(xyz[:, 2].mean()),
                            "ax_raw_std": float(xyz[:, 0].std()),
                            "ay_raw_std": float(xyz[:, 1].std()),
                            "az_raw_std": float(xyz[:, 2].std()),
                            # norm of the raw vector: used by the gravity calibration
                            "norm_raw_mean": float(
                                np.linalg.norm(xyz - xyz.mean(0), axis=1).mean()
                            ),
                            "norm_abs_mean": float(np.linalg.norm(xyz, axis=1).mean()),
                        }
                    )
                if not rows:
                    continue
                df = pd.DataFrame(rows)
                df["ts"] = pd.to_datetime(df.ts, format="mixed", utc=True)
                df["x_ichnos_source"] = source
                tbl = pa.Table.from_pandas(df, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(out_parquet, tbl.schema, compression="zstd")
                writer.write_table(tbl)
                n += len(df)
                print(f"    {n:,} rafales", end="\r", flush=True)
                if max_bursts and n >= max_bursts:
                    writer.close()
                    print()
                    return {"source": source, "n_bursts": n, "tronque": True}
    if writer:
        writer.close()
    print()
    return {"source": source, "n_bursts": n, "tronque": False}


def main():
    base = Path(__file__).resolve().parents[2]
    data, out = base / "data", base / "out"
    out.mkdir(exist_ok=True)
    res = {}

    bab = data / "baboons_collective"
    if bab.exists():
        print("[baboons] GPS at 1 Hz ...")
        res["baboons_gps"] = gps_to_pivot(
            sorted(bab.glob("*-gps-*.csv.zip")), out / "baboons_gps_pivot.parquet", "baboons"
        )
        print("[baboons] acceleration bursts ...")
        res["baboons_acc"] = acc_bursts(
            sorted(bab.glob("*-acc-*.csv.zip")), out / "baboons_acc_pivot.parquet",
            "baboons", max_bursts=1_500_000,
        )

    cig = data / "cigognes_vent"
    if cig.exists():
        print("[storks] GPS at 1 Hz ...")
        res["cigognes_gps"] = gps_to_pivot(
            sorted(cig.glob("*-gps.csv.zip")), out / "storks_gps_pivot.parquet", "cigognes"
        )

    lai = data / "laikipia_kenya"
    if lai.exists():
        print("[laikipia] GPS ...")
        res["laikipia_gps"] = gps_to_pivot(
            sorted(lai.glob("*part-gps.csv")), out / "laikipia_gps_pivot.parquet", "laikipia"
        )

    (out / "eobs_adapt.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
