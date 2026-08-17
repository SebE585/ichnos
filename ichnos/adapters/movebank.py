"""
ICHNOS -- Movebank to an open pivot format, `core` profile.

A wildlife collar IS a tracking device: GNSS, clock, uplink. What differs from
a vehicle device is not the shape of a record, it is the *carrier* and the
energy budget. So the mapping follows the spec without inventing columns, and
the gap is reported in the capability descriptor rather than papered over.

Known gap against SPEC-01: `speed_mps` is mandatory in the `core` profile and
no wildlife collar emits it, Doppler costing energy. The column is present and
entirely NaN. It is never filled with zeros: a fabricated zero cannot be told
apart from a measured standstill.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import validate

# Movebank columns mapped onto the spec.
MAP = {
    "timestamp": "ts",
    "location-lat": "lat",
    "location-long": "lon",
    "individual-local-identifier": "device_id",
}

# Columns of the core profile, in the order the spec gives them.
CORE = ["ts", "lat", "lon", "speed_mps"]


def load_movebank(csv_path: str | Path, nrows: int | None = None) -> pd.DataFrame:
    """Read a raw Movebank export. No filtering, no interpretation."""
    usecols = [
        "timestamp",
        "location-lat",
        "location-long",
        "individual-local-identifier",
        "tag-local-identifier",
        "sensor-type",
    ]
    head = pd.read_csv(csv_path, nrows=0)
    for opt in ("external-temperature", "manually-marked-outlier", "visible"):
        if opt in head.columns:
            usecols.append(opt)

    df = pd.read_csv(csv_path, usecols=usecols, nrows=nrows, low_memory=False)
    return df


def to_pivot(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Project a Movebank export onto the pivot record."""
    out = pd.DataFrame()
    out["ts"] = pd.to_datetime(df["timestamp"], utc=True, format="mixed")
    out["lat"] = df["location-lat"].astype("float64")
    out["lon"] = df["location-long"].astype("float64")

    # Not emitted by the collar. NaN, never zero.
    out["speed_mps"] = np.float32(np.nan)

    out["device_id"] = df["individual-local-identifier"].astype("string")
    out["x_movebank_tag_id"] = df["tag-local-identifier"].astype("string")

    if "external-temperature" in df.columns:
        out["x_movebank_external_temp_c"] = df["external-temperature"].astype("float32")
    if "manually-marked-outlier" in df.columns:
        # Empty means unmarked. A human oracle, not a filter.
        out["x_movebank_manual_outlier"] = (
            df["manually-marked-outlier"].astype("string").str.lower().eq("true")
        )
    if "visible" in df.columns:
        out["x_movebank_visible"] = (
            df["visible"].astype("string").str.lower().eq("true")
        )

    out["x_ichnos_source"] = source
    out = out.sort_values(["device_id", "ts"], kind="stable").reset_index(drop=True)
    return out


def capabilities(df: pd.DataFrame, source: str, nominal_period_s: float | None) -> dict:
    """Capability descriptor: what the source actually delivers.

    Not what the datasheet promises. What is in the bytes.
    """
    present = {}
    for col in [
        "lat", "lon", "speed_mps", "heading_deg", "altitude_gps_m",
        "hdop", "h_accuracy_m", "n_satellites", "gnss_valid",
        "ax_mps2", "ay_mps2", "az_mps2",
        "gx_rad_s", "gy_rad_s", "gz_rad_s",
        "mx_uT", "my_uT", "mz_uT",
    ]:
        if col not in df.columns:
            present[col] = "absent"
        elif df[col].isna().all():
            present[col] = "empty column"
        else:
            present[col] = f"{100 * df[col].notna().mean():.1f}%"

    dt = (
        df.sort_values(["device_id", "ts"])
        .groupby("device_id", observed=True)["ts"]
        .diff()
        .dt.total_seconds()
        .dropna()
    )
    dt = dt[dt > 0]

    return {
        "source": source,
        "declared_profile": "core",
        "effective_profile": "sub-core, speed_mps absent from the sensor",
        "n_records": int(len(df)),
        "n_carriers": int(df["device_id"].nunique()),
        "period_covered": [str(df["ts"].min()), str(df["ts"].max())],
        "fields": present,
        "cadence": {
            "nominal_s": nominal_period_s,
            "median_s": float(dt.median()),
            "p05_s": float(dt.quantile(0.05)),
            "p95_s": float(dt.quantile(0.95)),
            "mode_s": float(dt.round(-1).mode().iloc[0]) if len(dt) else None,
        },
        "structural_gaps": [
            "no Doppler speed: any speed is derived from two positions",
            "no heading: heading is derived, so it carries the position error",
            "no fix quality indicator (hdop, satellite count, accuracy)",
            "no inertial data: nothing can be reconstructed between fixes",
            "no battery voltage or state: no wear diagnosis on the device",
        ],
    }


def run(csv_path, source, nominal_period_s, outdir, nrows=None):
    """Convert, VALIDATE, then write. The order matters."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    raw = load_movebank(csv_path, nrows=nrows)
    df = to_pivot(raw, source)

    # Validate BEFORE writing: a non-conformant file must not exist, or it ends
    # up read by a script that believes it is conformant.
    report = validate.verify(df, source)

    pq = outdir / f"{source}_pivot.parquet"
    df.to_parquet(pq, index=False)

    caps = capabilities(df, source, nominal_period_s)
    caps["conformance_verified"] = report
    (outdir / f"{source}_capabilities.json").write_text(
        json.dumps(caps, indent=2, ensure_ascii=False)
    )
    return df, caps


if __name__ == "__main__":
    import sys

    base = Path(__file__).resolve().parents[2]
    data = base / "data"
    out = base / "out"

    jobs = [
        (data / "kruger_2007.csv", "kruger", 1800.0),
        (
            data
            / "African elephants in Etosha National Park (data from Tsalyuk et al. 2018).csv",
            "etosha",
            None,
        ),
    ]
    for path, src, per in jobs:
        if not path.exists():
            print(f"SKIP {src}: {path} missing", file=sys.stderr)
            continue
        df, caps = run(path, src, per, out)
        print(f"[{src}] {len(df):,} records / {caps['n_carriers']} carriers "
              f"/ median cadence {caps['cadence']['median_s']:.0f}s")
