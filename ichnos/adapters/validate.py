"""
ICHNOS -- validate OUR OWN output against the pivot format library.

This module exists because it was missing. The adapters announced a `core`
profile by hand-copying the spec's column list, and nothing checked that they
honoured it. Only the conformance survey imported the library, that is, the
tool that measures OTHER PEOPLE's data. The bench was demanding of others a
conformance it never checked on itself.

Two points of method, both learnt by wiring this check in:

1. Validation is PER CARRIER. A multi-animal file sorted by (device_id, ts) is
   not monotonic in ts globally, and the validator refuses it. Sorting globally
   by ts would make it pass, but that is contorting the data to satisfy the
   tool. One carrier is one time series, and that is what gets validated.

2. An empty column is never fabricated to satisfy a requirement. If `speed_mps`
   is absent from the sensor it is absent from the file, and the capability
   descriptor says so.

As in the conformance survey, the instrument's PATH is declared and not only
its version: two different trees return the same version string, and only the
path separates them.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import telemachus as tele


class NotConformant(Exception):
    """Raised when our own output fails the format it claims to follow."""


def instrument() -> dict:
    """Where the validating library comes from, not only which version."""
    root = Path(tele.__file__).resolve().parent.parent
    return {
        "version": tele.__version__,
        "path": str(root),
        "from_site_packages": "site-packages" in str(root),
    }


def _report(carriers, failures, warnings, level):
    return {
        "instrument": instrument(),
        "level": level,
        "n_carriers_valid": carriers - len(failures),
        "n_carriers_failed": len(failures),
        "warnings": warnings[:20],
    }


def verify(df: pd.DataFrame, source: str, level: str = "full") -> dict:
    """Validate the output carrier by carrier. Raise if a single one fails.

    Returns the report to attach to the capability descriptor, so that a
    declared conformance is a dated measurement rather than an assertion.
    """
    if "device_id" not in df.columns:
        raise NotConformant(f"{source}: no device_id, cannot validate per carrier")

    failures, warnings = [], []
    for carrier, g in df.groupby("device_id", observed=True):
        r = tele.validate(g.sort_values("ts").reset_index(drop=True), level=level)
        if not r.ok:
            failures.append({"carrier": str(carrier), "errors": list(r.errors)})
        if r.warnings:
            warnings.append({"carrier": str(carrier), "warnings": list(r.warnings)})

    report = _report(int(df.device_id.nunique()), failures, warnings, level)
    if failures:
        report["failures"] = failures[:20]
        raise NotConformant(
            f"{source}: {len(failures)} carrier(s) of {df.device_id.nunique()} "
            f"refused by telemachus {tele.__version__}. First: {failures[0]}"
        )
    return report


def verify_parquet(path, source: str, level: str = "full") -> dict:
    """Same check, for a parquet written as a stream.

    Read back carrier by carrier rather than in one block: the e-obs files run
    past ten million rows and have no business fitting in memory to be
    validated.
    """
    carriers = (
        pd.read_parquet(path, columns=["device_id"]).device_id.astype(str).unique().tolist()
    )
    failures, warnings = [], []
    for carrier in carriers:
        g = pd.read_parquet(path, filters=[("device_id", "==", carrier)])
        r = tele.validate(g.sort_values("ts").reset_index(drop=True), level=level)
        if not r.ok:
            failures.append({"carrier": carrier, "errors": list(r.errors)})
        if r.warnings:
            warnings.append({"carrier": carrier, "warnings": list(r.warnings)})

    report = _report(len(carriers), failures, warnings, level)
    if failures:
        report["failures"] = failures[:20]
        raise NotConformant(
            f"{source}: {len(failures)} carrier(s) of {len(carriers)} refused "
            f"by telemachus {tele.__version__}. First: {failures[0]}"
        )
    return report
