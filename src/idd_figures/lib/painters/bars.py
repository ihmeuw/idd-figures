"""Ranked within-group range bars comparing two snapshots (dispersion).

Each group gets a start-year and end-year bar: line = min->max, short tick =
mean, diamond = median, optional faint jittered dots = the detailed units.
Groups are ordered by end-year median. Indicator-generic: column names and the
colour-by key are parameters.

Data contract: ``stats_df`` is long with columns ``[group_col, "year_id", "lo",
"hi", "med", "mean"]`` and (optionally) ``"group_name"`` and the ``color_by``
column. ``values_df`` (optional) holds the detailed unit values with a
``value_col`` for the jittered dots.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

__all__ = ["range_bars_panel", "plot_range_bars"]


def _draw_bar(ax, xpos, lo, hi, med, mean, *, edgecolor, med_color, transform=None, lw=7, bw=0.38):
    if transform:
        lo, hi, med, mean = lo / transform, hi / transform, med / transform, mean / transform
    ax.plot([xpos, xpos], [lo, hi], color=edgecolor, solid_capstyle="round", lw=lw, zorder=2)
    ax.hlines(mean, xpos - bw / 2, xpos + bw / 2, color=edgecolor, lw=2.0, zorder=3)
    ax.scatter(xpos, med, marker="D", s=28, color=med_color, zorder=4)


def _draw_dots(ax, xpos, values, color, *, rng, transform=None, bw=0.38):
    v = np.asarray(values, dtype="float64")
    if transform:
        v = v / transform
    jitter = (rng.random(len(v)) - 0.5) * bw * 0.7
    ax.scatter(np.full(len(v), xpos) + jitter, v, s=3, color=color, alpha=0.15,
               edgecolors="none", zorder=1)


def range_bars_panel(
    ax,
    stats_df,
    *,
    group_col,
    years,
    color_by=None,
    colors=None,
    relative=False,
    values_df=None,
    value_col="value",
    grey="#BDBDBD",
    med_dark="#222222",
    med_light="#C8C8C8",
    bar_width=0.38,
    seed=0,
):
    """Draw ranked range bars onto ``ax`` and return ``ax``.

    ``years`` is ``(start, end)``. With ``relative=True`` everything is divided
    by that group-year's mean and the y-axis is log2 (vs the group mean).
    """
    colors = colors or {}
    y0, y1 = years
    wide = stats_df.pivot(index=group_col, columns="year_id", values=["lo", "hi", "med", "mean"])
    wide.columns = [f"{stat}_{yr}" for stat, yr in wide.columns]
    meta_cols = [c for c in ("group_name", color_by) if c]
    if meta_cols:
        meta = stats_df.drop_duplicates(group_col).set_index(group_col)[meta_cols]
        wide = wide.join(meta)
    wide = wide.sort_values(f"med_{y1}")

    x = np.arange(len(wide))
    off = bar_width / 2 + 0.02
    rng = np.random.default_rng(seed)
    dot_lookup = {}
    if values_df is not None:
        dot_lookup = {k: g[value_col].to_numpy() for k, g in values_df.groupby([group_col, "year_id"])}

    for i, (gid, row) in enumerate(wide.iterrows()):
        color = colors.get(row[color_by], grey) if color_by else "C0"
        x0, x1 = x[i] - off, x[i] + off
        m0 = row[f"mean_{y0}"] if relative else None
        m1 = row[f"mean_{y1}"] if relative else None
        if values_df is not None:
            _draw_dots(ax, x0, dot_lookup.get((gid, y0), []), grey, rng=rng, transform=m0, bw=bar_width)
            _draw_dots(ax, x1, dot_lookup.get((gid, y1), []), color, rng=rng, transform=m1, bw=bar_width)
        _draw_bar(ax, x0, row[f"lo_{y0}"], row[f"hi_{y0}"], row[f"med_{y0}"], row[f"mean_{y0}"],
                  edgecolor=grey, med_color=med_light, transform=m0, bw=bar_width)
        _draw_bar(ax, x1, row[f"lo_{y1}"], row[f"hi_{y1}"], row[f"med_{y1}"], row[f"mean_{y1}"],
                  edgecolor=color, med_color=med_dark, transform=m1, bw=bar_width)

    ax.set_xticks(x)
    labels = wide["group_name"] if "group_name" in wide else wide.index
    ax.set_xticklabels(labels, rotation=90, fontsize=8)
    ax.set_xlim(-0.7, len(wide) - 0.3)
    if relative:
        ax.set_yscale("log", base=2)
        ax.set_ylim(0.25, 4)
        ax.axhline(1, color="k", lw=0.8, ls="--")
        ax.set_ylabel("relative to group mean")
    else:
        ax.set_ylim(0, None)
    return ax


def plot_range_bars(stats_df, *, ax=None, figsize=(10, 6), **opts):
    """Standalone one-painter layout for range bars; returns the Axes."""
    if ax is None:
        _, ax = plt.subplots(figsize=figsize)
    return range_bars_panel(ax, stats_df, **opts)
