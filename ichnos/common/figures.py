"""
ICHNOS -- the figures of the paper.

No calculation is redone here: everything comes from the bench's own output
files, so a figure cannot drift from the number it illustrates. That is not a
convenience. Two of the failures recorded in the paper's section 7 were a
caption and a paragraph that had stopped agreeing.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import PathPatch, Rectangle
from matplotlib.path import Path as MPath

BASE = Path(__file__).resolve().parents[2]
OUT, FIGS = BASE / "out", BASE / "docs" / "article" / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

INK, INK2, INK3 = "#0b0b0b", "#52514e", "#8a8983"
GRID, S1, S2 = "#e5e4e0", "#2a78d6", "#eb6834"
SURF = "#ffffff"
RAMP = ["#f4f8fd", "#cfe0f6", "#94bced", "#5497df", "#2a78d6", "#1a4f8f"]

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
})


def frame(ax, ygrid=True):
    ax.set_facecolor(SURF)
    ax.figure.patch.set_facecolor(SURF)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0, labelsize=9)
    (ax.yaxis if ygrid else ax.xaxis).grid(True, color=GRID, linewidth=1)
    ax.set_axisbelow(True)


def px(ax, n=4):
    inv = ax.transData.inverted()
    (x0, y0), (x1, y1) = inv.transform((0, 0)), inv.transform((n, n))
    return abs(x1 - x0), abs(y1 - y0)


def vbar(ax, x, h, w, color):
    rx, ry = px(ax)
    rx, ry = min(rx, w / 2), min(ry, h / 2)
    l, r, t = x - w / 2, x + w / 2, h
    v = [(l, 0), (l, t - ry), (l, t), (l + rx, t), (r - rx, t),
         (r, t), (r, t - ry), (r, 0), (l, 0)]
    c = [MPath.MOVETO, MPath.LINETO, MPath.CURVE3, MPath.CURVE3, MPath.LINETO,
         MPath.CURVE3, MPath.CURVE3, MPath.LINETO, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(v, c), linewidth=0, facecolor=color, zorder=3))


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGS / f"{name}.png", facecolor=SURF, bbox_inches="tight",
                pad_inches=0.28, dpi=220)
    plt.close(fig)
    print("  ", name)


# --------------------------------------------------------------- figure 1
def fig_batch():
    """The seven sound collars sit at zero on a scale that runs to 17 %.

    A bar of zero width is invisible, so the blue series the legend promises
    did not appear at all. They are now marked explicitly at zero with their
    exact value: three of them are not null, they are at 0.0007 to 0.0021 %,
    and rounding to two decimals hid that too.
    """
    p = pd.read_parquet(OUT / "fleet_health.parquet")
    p["exact"] = 100 * p.n_flagged / p.n_pairs
    p = p.sort_values("exact")
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    frame(ax, ygrid=False)
    xmax = p.exact.max() * 1.28
    ax.set_xlim(-xmax * 0.012, xmax)
    ax.set_ylim(-0.8, len(p) - 0.2)
    threshold = xmax * 0.004
    for y, (dev, val, batch) in enumerate(zip(p.device_id, p.exact, p.batch)):
        col = S2 if batch.endswith("2008") else S1
        if val < threshold:
            # Zero marker: a visible tick on the axis plus the exact value.
            # Better than a one-pixel bar that nobody sees.
            ax.plot([0, 0], [y - 0.28, y + 0.28], color=col, linewidth=2.6,
                    solid_capstyle="round", zorder=4)
            lab = "0" if val == 0 else f"{val:.4f} %"
            ax.text(xmax * 0.012, y, lab, va="center", ha="left",
                    color=INK2, fontsize=9, fontweight="500")
        else:
            ax.add_patch(Rectangle((0, y - 0.3), val, 0.6, linewidth=0,
                                   facecolor=col, zorder=3))
            ax.text(val + xmax * 0.015, y, f"{val:.2f} %", va="center",
                    ha="left", color=INK, fontsize=9.5, fontweight="600")
    ax.set_yticks(range(len(p)))
    ax.set_yticklabels(p.device_id)
    ax.set_xticks(np.arange(0, xmax, 5))
    ax.set_xticklabels([f"{int(v)} %" for v in np.arange(0, xmax, 5)])
    ax.set_xlabel("physically impossible fix pairs", color=INK2, fontsize=9.5)
    for i, (lab, col) in enumerate((
            ("2008 batch, serials AG004-AG013", S2),
            ("2009 batch, serials AG189-AG195, four at exactly zero", S1))):
        y0 = 4.2 - i * 0.85
        ax.add_patch(Rectangle((xmax * 0.44, y0 - 0.12), xmax * 0.028, 0.26,
                               linewidth=0, facecolor=col, zorder=5))
        ax.text(xmax * 0.485, y0, lab, va="center", color=INK2, fontsize=9.5)
    save(fig, "fig1-batch-effect")


# --------------------------------------------------------------- figure 2
def fig_gait():
    spec = np.load(OUT / "gait_spectra.npy")
    freqs = np.load(OUT / "gait_freqs.npy")
    tab = pd.read_parquet(OUT / "gaits.parquet")
    ok = (tab.n_fenetres > 300) & (tab.v_centre > 0.25)
    tab, spec = tab[ok].reset_index(drop=True), spec[ok.values]
    m = freqs >= 1.0
    S = spec[:, m] / spec[:, m].max(axis=1, keepdims=True)

    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.set_facecolor(SURF)
    fig.patch.set_facecolor(SURF)
    im = ax.pcolormesh(np.append(tab.v_min.values, tab.v_max.values[-1]),
                       np.append(freqs[m], freqs[m][-1] + (freqs[1] - freqs[0])),
                       S.T, cmap=LinearSegmentedColormap.from_list("i", RAMP),
                       shading="flat", vmin=0, vmax=1, zorder=2)
    ax.plot(tab.v_centre, tab.f_foulee_hz, color=S2, linewidth=2.2, marker="o",
            markersize=5, markeredgecolor=SURF, markeredgewidth=1.5, zorder=5,
            label="dominant stride frequency")
    v_tr = np.sqrt(0.5 * 9.80665 * 0.40)
    ax.axvline(v_tr, color=INK, linewidth=1.4, linestyle=(0, (4, 3)), zorder=6)
    ax.text(0.15, freqs[m][-1] * 0.97,
            f"walk-run transition predicted\nby Froude 0.5 ({v_tr:.2f} m/s)",
            color=INK, fontsize=9, va="top", ha="left", linespacing=1.4)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, length=0, labelsize=9)
    ax.set_xlabel("Doppler speed (m/s), measured by the GNSS receiver",
                  color=INK2, fontsize=9.5)
    ax.set_ylabel("frequency (Hz), measured by the accelerometer",
                  color=INK2, fontsize=9.5)
    cb = fig.colorbar(im, ax=ax, pad=0.015, fraction=0.045)
    cb.set_label("spectral density, normalised per speed class", color=INK2,
                 fontsize=8.5)
    cb.ax.tick_params(colors=INK2, length=0, labelsize=8)
    cb.outline.set_visible(False)
    leg = ax.legend(loc="lower right", frameon=False, fontsize=9)
    for t in leg.get_texts():
        t.set_color(INK2)
    save(fig, "fig2-gait-froude")


# --------------------------------------------------------------- figure 3
def fig_wind():
    st = pd.read_parquet(OUT / "wind_structure.parquet")
    lab = ["under 2 km", "2-10 km", "10-50 km", "50-200 km", "over 200 km"]
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    frame(ax)
    ymax = float(st.median_disagreement_mps.max()) * 1.4
    ax.set_xlim(-0.6, len(st) - 0.4)
    ax.set_ylim(0, ymax)
    ax.set_yticks(np.arange(0, 4.1, 1))
    for i, r in st.reset_index(drop=True).iterrows():
        vbar(ax, i, r.median_disagreement_mps, 0.6, S1 if i == 0 else INK3)
        ax.text(i, r.median_disagreement_mps + ymax * 0.03, f"{r.median_disagreement_mps:.2f}",
                ha="center", va="bottom", color=INK, fontsize=10.5,
                fontweight="600")
        ax.text(i, r.median_disagreement_mps + ymax * 0.115,
                f"{int(r.n_pairs):,} pairs", ha="center", va="bottom",
                color=INK3, fontsize=8)
    floor = float(st.median_disagreement_mps.iloc[0])
    ax.axhline(floor, color=S1, linewidth=1.3, linestyle=(0, (4, 3)), zorder=4)
    # Do NOT plot floor/sqrt(2): adding variances applies to a variance, not to
    # a median, and the distribution is too skewed for one number to stand in
    # for it. The observable is what gets shown.
    ax.text(0.15, ymax * 0.95,
            f"co-located floor {floor:.2f} m/s\n"
            f"per-spiral error of order 1 to 1.4 m/s",
            ha="left", va="top", color=S1, fontsize=9, linespacing=1.4)
    ax.set_xticks(range(len(st)))
    ax.set_xticklabels(lab[:len(st)])
    ax.set_ylabel("disagreement between the two estimates (m/s)",
                  color=INK2, fontsize=9.5)
    ax.set_xlabel("distance between the two birds", color=INK2, fontsize=9.5)
    save(fig, "fig3-wind-structure")


# --------------------------------------------------------------- figure 4
def fig_cadence():
    """A single panel: the fence crossings.

    The path-length panel was removed. That subsampling shortens path length
    is long established in movement ecology, and illustrating it gave weight
    to the least novel part of the paper.
    """
    f = pd.read_parquet(OUT / "fence_crossings.parquet").sort_values("interval_s")
    L = {0: "native\n(burst)", 1200: "20 min", 3600: "1 h", 7200: "2 h",
         10800: "3 h", 21600: "6 h", 43200: "12 h", 86400: "24 h"}
    v = f.set_index("interval_s").franchissements_vus
    v = v.reindex([k for k in L if k in v.index])
    base = float(v.iloc[0])

    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    frame(ax)
    ax.set_xlim(-0.6, len(v) - 0.4)
    ax.set_ylim(0, base * 1.28)
    ax.set_yticks(np.arange(0, base * 1.02, 50))
    for i, (iv, val) in enumerate(v.items()):
        vbar(ax, i, val, 0.62, S1 if iv == 0 else S2 if iv == 3600 else INK3)
        ax.text(i, val + base * 0.03, f"{val:.0f}", ha="center", va="bottom",
                color=INK, fontsize=10.5, fontweight="600")
        ax.text(i, val + base * 0.115, f"{100*val/base:.0f} %", ha="center",
                va="bottom", color=INK3, fontsize=8)
    ax.set_xticks(range(len(v)))
    ax.set_xticklabels([L[k] for k in v.index], fontsize=8.5)
    ax.set_ylabel("fence crossings detected", color=INK2, fontsize=9.5)
    ax.set_xlabel("sampling cadence", color=INK2, fontsize=9.5)
    save(fig, "fig4-cadence-cost")


if __name__ == "__main__":
    print("figures de l'article :")
    fig_batch()
    fig_gait()
    fig_wind()
    fig_cadence()
